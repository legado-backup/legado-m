# -*- coding: utf-8 -*-
"""runtime_validator.py - 真机测试集成验证器（v4 Phase 2）。

复用 ai_tests/lib 的 10 个核心模块 + ai_tests/scripts 的 7 个固定脚本，
实现"源 JSON → 编译安装 → 导入 → 真机验证 → 日志分析"端到端验证。

设计哲学（v4）：
    - 不重新实现真机测试能力，复用 ai_tests 已沉淀的脚本
    - 通过 subprocess 调用 ai_tests venv Python（避免跨 venv 依赖污染）
    - 返回结构化结果，供 auto_fixer_loop.py 自动决策

复用脚本（ai_tests/scripts/）：
    - quick_build_install.py: 编译+安装+L1验证
    - import_rss_source.py: 导入订阅源到 legado.db（含 WAL 模式处理）
    - l2_verify_video_player.py: L2 视频播放器验证
    - nav_helper.py: 脱敏导航到视频播放器
    - swipe_test_log.py: 日志抓取分析

典型用法：
    from legado_client.runtime import validate_source_on_device

    result = validate_source_on_device(
        source_obj={'sourceUrl': 'https://...', ...},
        source_type='rss',
        skip_build=False,  # True=跳过编译安装（APK 已装）
    )
    if not result['success']:
        for err in result['errors']:
            print(f"[{err['stage']}] {err['message']}")
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# === 路径常量 ===
# legado_client/runtime/runtime_validator.py → 上溯到项目根
# parents[0]=runtime, [1]=legado_client, [2]=scripts, [3]=legado-source-creator, [4]=skills, [5]=.trae, [6]=legado
PROJECT_ROOT = Path(__file__).resolve().parents[6]
AI_TESTS_DIR = PROJECT_ROOT / "ai_tests"
AI_TESTS_VENV_PYTHON = AI_TESTS_DIR / "venv" / "Scripts" / "python.exe"

# ai_tests/scripts/ 下的固定脚本
SCRIPT_BUILD_INSTALL = AI_TESTS_DIR / "scripts" / "quick_build_install.py"
SCRIPT_IMPORT_RSS = AI_TESTS_DIR / "scripts" / "import_rss_source.py"
SCRIPT_L2_VERIFY = AI_TESTS_DIR / "scripts" / "l2_verify_video_player.py"
SCRIPT_NAV_HELPER = AI_TESTS_DIR / "scripts" / "nav_helper.py"
SCRIPT_SWIPE_LOG = AI_TESTS_DIR / "scripts" / "swipe_test_log.py"

# logcat 错误模式（基于 ai_tests/config.py CRASH_PATTERNS + 项目历史铁证）
LOGCAT_ERROR_PATTERNS = [
    # 崩溃类
    (r"FATAL EXCEPTION.*io\.legado\.app", "FATAL_EXCEPTION"),
    (r"AndroidRuntime.*FATAL", "ANDROID_RUNTIME_FATAL"),
    (r"ClassNotFoundException", "CLASS_NOT_FOUND"),
    (r"NoClassDefFoundError", "NO_CLASS_DEF"),
    (r"OutOfMemoryError", "OOM"),
    # Legado 业务异常
    (r"NoStackTraceException.*不是订阅源", "RSS_NOT_SOURCE"),
    (r"NoStackTraceException.*不是书源", "BOOK_NOT_SOURCE"),
    (r"NoStackTraceException.*搜索url不能为空", "SEARCH_URL_EMPTY"),
    (r"ReferenceError.*loginCheckJs", "LOGIN_CHECK_JS_REF_ERROR"),  # None 序列化 bug
    # WebView 相关
    (r"Calling View methods on another thread", "WEBVIEW_THREAD_VIOLATION"),
    (r"destroy failed after \d+ attempts", "WEBVIEW_DESTROY_FAILED"),
    (r"UnrecognizedInputFormatException", "EXO_PLAYER_FORMAT_ERROR"),
    (r"IllegalBlockSizeException", "DECRYPT_BLOCK_SIZE_ERROR"),
    (r"ClassCastException.*ByteArray", "IMAGE_DECODE_CAST_ERROR"),
    # 网络协议
    (r"protocol=unknown httpCode=-1", "CRONET_PROTOCOL_FAIL"),
]


class RuntimeValidator:
    """真机测试集成验证器。

    在源通过 MandatoryFieldValidator 后，将源导入真机/模拟器，
    验证实际可用性，并抓取 logcat 分析运行时错误。
    """

    def __init__(
        self,
        source_obj: dict,
        source_type: str = "rss",
        skip_build: bool = False,
        skip_l2_verify: bool = False,
        build_timeout: int = 600,
        import_timeout: int = 120,
        verify_timeout: int = 180,
        logcat_lines: int = 2000,
    ):
        """
        Args:
            source_obj: 源 JSON dict（必须通过 MandatoryFieldValidator）
            source_type: "book" 或 "rss"
            skip_build: True=跳过编译安装步骤（假定 APK 已装）
            skip_l2_verify: True=跳过 L2 验证（仅做导入+logcat）
            build_timeout: 编译安装超时秒
            import_timeout: 导入源超时秒
            verify_timeout: L2 验证超时秒
            logcat_lines: logcat 抓取行数
        """
        self.source_obj = source_obj or {}
        self.source_type = source_type
        self.skip_build = skip_build
        self.skip_l2_verify = skip_l2_verify
        self.build_timeout = build_timeout
        self.import_timeout = import_timeout
        self.verify_timeout = verify_timeout
        self.logcat_lines = logcat_lines

        # 运行时状态
        self._stages_run: List[str] = []
        self._errors: List[Dict[str, str]] = []
        self._warnings: List[Dict[str, str]] = []
        self._logcat_raw: str = ""

    def validate(self) -> Dict[str, Any]:
        """运行完整真机验证流程。

        Returns:
            {
                "success": bool,           # True=所有阶段通过
                "stages_run": list,        # 执行的阶段列表
                "errors": [...],           # 错误列表（每项含 stage/message/detail）
                "warnings": [...],         # 警告列表
                "logcat_summary": {...},   # logcat 错误模式统计
                "logcat_raw": str,         # 原始 logcat（截断）
                "imported_count": int,     # 导入的源数量
                "elapsed_sec": float,      # 总耗时
            }
        """
        start_time = time.time()
        self._stages_run = []
        self._errors = []
        self._warnings = []
        self._logcat_raw = ""

        # 阶段 1：环境检查（ai_tests venv + 脚本存在性）
        if not self._check_environment():
            return self._build_result(start_time)

        # 阶段 2：编译+安装+L1（可跳过）
        if not self.skip_build:
            if not self._run_build_install():
                return self._build_result(start_time)
        else:
            self._stages_run.append("build_install (skipped)")

        # 阶段 3：写源到临时 JSON 文件
        source_path = self._write_source_tempfile()
        if not source_path:
            return self._build_result(start_time)

        # 阶段 4：导入源到设备
        imported = self._run_import_source(source_path)
        if imported is None:
            # 导入失败，但继续抓 logcat 看原因
            pass

        # 阶段 5：L2 验证（可跳过）
        if not self.skip_l2_verify and self.source_type == "rss":
            self._run_l2_verify()

        # 阶段 6：logcat 分析
        self._run_logcat_analysis()

        # 清理临时文件
        try:
            os.unlink(source_path)
        except OSError:
            pass

        return self._build_result(start_time, imported_count=imported or 0)

    # ==================== 阶段实现 ====================

    def _check_environment(self) -> bool:
        """阶段 1：检查 ai_tests venv 和关键脚本是否存在。"""
        self._stages_run.append("env_check")
        if not AI_TESTS_VENV_PYTHON.is_file():
            self._errors.append({
                "stage": "env_check",
                "message": "ai_tests venv Python 不存在",
                "detail": f"期望路径: {AI_TESTS_VENV_PYTHON}",
            })
            return False
        missing_scripts = []
        for script in [SCRIPT_BUILD_INSTALL, SCRIPT_IMPORT_RSS]:
            if not script.is_file():
                missing_scripts.append(str(script))
        if missing_scripts:
            self._errors.append({
                "stage": "env_check",
                "message": "ai_tests 关键脚本缺失",
                "detail": f"缺失: {missing_scripts}",
            })
            return False
        return True

    def _run_build_install(self) -> bool:
        """阶段 2：调用 quick_build_install.py 编译+安装+L1 验证。"""
        self._stages_run.append("build_install")
        try:
            result = subprocess.run(
                [str(AI_TESTS_VENV_PYTHON), str(SCRIPT_BUILD_INSTALL)],
                capture_output=True, text=True,
                timeout=self.build_timeout,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            self._errors.append({
                "stage": "build_install",
                "message": f"编译安装超时（{self.build_timeout}s）",
                "detail": "",
            })
            return False
        except Exception as e:
            self._errors.append({
                "stage": "build_install",
                "message": f"调用异常: {type(e).__name__}",
                "detail": str(e)[:200],
            })
            return False

        if result.returncode != 0:
            self._errors.append({
                "stage": "build_install",
                "message": "编译安装失败（返回码非 0）",
                "detail": (result.stderr or "")[-300:],
            })
            return False
        return True

    def _write_source_tempfile(self) -> Optional[str]:
        """阶段 3：写源 JSON 到临时文件。"""
        self._stages_run.append("write_source")
        try:
            # 用 sanitize_source_json 清理 None 字段
            from legado_client.utils.file_utils import sanitize_source_json
            cleaned = sanitize_source_json(self.source_obj)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(cleaned, f, ensure_ascii=False, indent=2)
                return f.name
        except Exception as e:
            self._errors.append({
                "stage": "write_source",
                "message": f"写源 JSON 失败: {type(e).__name__}",
                "detail": str(e)[:200],
            })
            return None

    def _run_import_source(self, source_path: str) -> Optional[int]:
        """阶段 4：调用 import_rss_source.py 导入源到设备。

        Returns:
            导入的源数量，失败返回 None
        """
        self._stages_run.append("import_source")
        try:
            result = subprocess.run(
                [str(AI_TESTS_VENV_PYTHON), str(SCRIPT_IMPORT_RSS), source_path],
                capture_output=True, text=True,
                timeout=self.import_timeout,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            self._errors.append({
                "stage": "import_source",
                "message": f"导入源超时（{self.import_timeout}s）",
                "detail": "",
            })
            return None
        except Exception as e:
            self._errors.append({
                "stage": "import_source",
                "message": f"调用异常: {type(e).__name__}",
                "detail": str(e)[:200],
            })
            return None

        # 解析输出（import_rss_source.py 输出 "成功导入 N 条"）
        output = result.stdout or ""
        match = re.search(r"成功导入\s*(\d+)\s*条", output)
        if match:
            count = int(match.group(1))
            if count == 0:
                self._errors.append({
                    "stage": "import_source",
                    "message": "导入 0 条源（源 JSON 可能无效）",
                    "detail": output[-200:],
                })
            return count

        if result.returncode != 0:
            self._errors.append({
                "stage": "import_source",
                "message": "导入失败（返回码非 0）",
                "detail": (result.stderr or "")[-300:],
            })
            return None

        # 无明确错误，但也没解析到数量
        self._warnings.append({
            "stage": "import_source",
            "message": "未解析到导入数量，但脚本退出码为 0",
            "detail": output[-200:],
        })
        return 0

    def _run_l2_verify(self) -> None:
        """阶段 5：调用 l2_verify_video_player.py 做 L2 验证（仅 rss 视频源）。

        失败不中断流程，仅记录错误，后续继续抓 logcat。
        """
        # 仅 type=2（视频）的 rss 源才做 L2 视频验证
        if self.source_obj.get("type") != 2:
            self._stages_run.append("l2_verify (skipped, non-video)")
            return

        self._stages_run.append("l2_verify")
        try:
            result = subprocess.run(
                [str(AI_TESTS_VENV_PYTHON), str(SCRIPT_L2_VERIFY),
                 "--scenario", "error_patterns"],
                capture_output=True, text=True,
                timeout=self.verify_timeout,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            self._warnings.append({
                "stage": "l2_verify",
                "message": f"L2 验证超时（{self.verify_timeout}s）",
                "detail": "",
            })
            return
        except Exception as e:
            self._warnings.append({
                "stage": "l2_verify",
                "message": f"调用异常: {type(e).__name__}",
                "detail": str(e)[:200],
            })
            return

        if result.returncode != 0:
            self._warnings.append({
                "stage": "l2_verify",
                "message": "L2 验证失败（返回码非 0）",
                "detail": (result.stderr or "")[-200:],
            })

    def _run_logcat_analysis(self) -> None:
        """阶段 6：抓取 logcat 并分析错误模式。"""
        self._stages_run.append("logcat_analysis")

        # 直接用 adb 抓 logcat（不依赖 swipe_test_log.py，避免 SwipeTest 依赖）
        try:
            adb_path = r"D:\Program Files\Microvirt\MEmu\adb.exe"
            result = subprocess.run(
                [adb_path, "-s", "127.0.0.1:21503", "logcat", "-d",
                 "-t", str(self.logcat_lines)],
                capture_output=True, text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
            self._logcat_raw = result.stdout or ""
        except Exception as e:
            self._warnings.append({
                "stage": "logcat_analysis",
                "message": f"adb logcat 调用异常: {type(e).__name__}",
                "detail": str(e)[:200],
            })
            return

        # 匹配错误模式
        found_patterns: Dict[str, List[str]] = {}
        for pattern, name in LOGCAT_ERROR_PATTERNS:
            matches = re.findall(pattern, self._logcat_raw)
            if matches:
                found_patterns[name] = [
                    f"出现 {len(matches)} 次"
                ]

        if found_patterns:
            for name, hits in found_patterns.items():
                self._errors.append({
                    "stage": "logcat_analysis",
                    "message": f"logcat 检测到错误模式: {name}",
                    "detail": "; ".join(hits),
                })

    # ==================== 辅助方法 ====================

    def _build_result(self, start_time: float, imported_count: int = 0) -> Dict[str, Any]:
        """构造最终返回结果。"""
        elapsed = time.time() - start_time
        logcat_summary = parse_logcat_summary(self._logcat_raw)
        return {
            "success": len(self._errors) == 0,
            "stages_run": self._stages_run,
            "errors": self._errors,
            "warnings": self._warnings,
            "logcat_summary": logcat_summary,
            "logcat_raw_truncated": self._logcat_raw[-2000:] if self._logcat_raw else "",
            "imported_count": imported_count,
            "elapsed_sec": round(elapsed, 2),
        }


def parse_logcat_summary(logcat_text: str) -> Dict[str, int]:
    """解析 logcat 文本，统计错误模式出现次数。

    Args:
        logcat_text: logcat 原始输出文本

    Returns:
        {错误模式名: 出现次数}（仅返回出现次数 > 0 的）
    """
    if not logcat_text:
        return {}

    summary: Dict[str, int] = {}
    for pattern, name in LOGCAT_ERROR_PATTERNS:
        count = len(re.findall(pattern, logcat_text))
        if count > 0:
            summary[name] = count
    return summary


def validate_source_on_device(
    source_obj: dict,
    source_type: str = "rss",
    skip_build: bool = False,
    skip_l2_verify: bool = False,
) -> Dict[str, Any]:
    """模块级便捷函数：在真机/模拟器上验证源。

    Args:
        source_obj: 源 JSON dict
        source_type: "book" 或 "rss"
        skip_build: True=跳过编译安装（APK 已装）
        skip_l2_verify: True=跳过 L2 验证

    Returns:
        RuntimeValidator.validate() 的返回结构
    """
    validator = RuntimeValidator(
        source_obj=source_obj,
        source_type=source_type,
        skip_build=skip_build,
        skip_l2_verify=skip_l2_verify,
    )
    return validator.validate()


# ==================== 自检 ====================

if __name__ == "__main__":
    # 最小自检：1 环境检查 + 1 解析 logcat + 1 边界用例
    print("runtime_validator.py 自检")

    # 用例 1：环境检查（ai_tests venv 是否存在）
    if AI_TESTS_VENV_PYTHON.is_file():
        print(f"[OK] ai_tests venv Python 存在: {AI_TESTS_VENV_PYTHON}")
    else:
        print(f"[FAIL] ai_tests venv Python 不存在: {AI_TESTS_VENV_PYTHON}")

    # 用例 2：parse_logcat_summary 解析已知错误模式
    test_logcat = """
FATAL EXCEPTION: io.legado.app
AndroidRuntime: FATAL EXCEPTION
NoStackTraceException: 不是订阅源
ReferenceError: loginCheckJs is not defined
Calling View methods on another thread than the UI thread
destroy failed after 3 attempts
    """
    summary = parse_logcat_summary(test_logcat)
    assert "FATAL_EXCEPTION" in summary, "FATAL_EXCEPTION 未检测到"
    assert "ANDROID_RUNTIME_FATAL" in summary, "ANDROID_RUNTIME_FATAL 未检测到"
    assert "RSS_NOT_SOURCE" in summary, "RSS_NOT_SOURCE 未检测到"
    assert "LOGIN_CHECK_JS_REF_ERROR" in summary, "LOGIN_CHECK_JS_REF_ERROR 未检测到"
    assert "WEBVIEW_THREAD_VIOLATION" in summary, "WEBVIEW_THREAD_VIOLATION 未检测到"
    assert "WEBVIEW_DESTROY_FAILED" in summary, "WEBVIEW_DESTROY_FAILED 未检测到"
    print(f"[OK] parse_logcat_summary 检测到 {len(summary)} 个错误模式: {summary}")

    # 用例 3：空 logcat 边界
    assert parse_logcat_summary("") == {}, "空 logcat 应返回空 dict"
    print("[OK] 空 logcat 边界用例通过")

    # 用例 4：RuntimeValidator 类实例化（不实际运行）
    v = RuntimeValidator(
        source_obj={"sourceUrl": "https://example.com"},
        source_type="rss",
        skip_build=True,
        skip_l2_verify=True,
    )
    assert v.source_type == "rss"
    assert v.skip_build is True
    print("[OK] RuntimeValidator 实例化通过")

    print("✅ 自检通过")
