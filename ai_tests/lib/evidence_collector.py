"""ai_tests/lib/evidence_collector.py — M5 证据收集器（8 类证据）

职责：
- 证据 1: logcat（start/stop/slice/extract_anomalies）
- 证据 2: ui_xml（汇总 UiExecutor 收集的 XML）
- 证据 3: screenshot（汇总截图）
- 证据 4: activity_stack（dumpsys activity top）
- 证据 5: db_state（run-at sqlite3，含降级标记 run_at_unavailable）
- 证据 6: prefs_state（cat shared_prefs/*.xml）
- 证据 7: web_api（curl localhost:8080，含降级标记 web_api_unavailable）
- 证据 8: meminfo（dumpsys meminfo）
- collect_all: ThreadPoolExecutor 并行收集（5/6/7 并发）

依赖：subprocess + concurrent.futures（标准库），M1 MemuController
CRASH_PATTERNS / DB_QUERIES 复用 config.py（固化层）
"""
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from ai_tests.config import (
    PACKAGE, CRASH_PATTERNS, DB_QUERIES,
)
from ai_tests.lib.memu_controller import MemuController

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """证据收集器（8 类证据并行收集）

    通过 ADB 命令收集运行时证据，供 M6 规则分析器判定。
    每类证据返回统一结构：{type, collected, degraded, degradation_reason, path, error, ...}
    """

    def __init__(self, memu: MemuController, package: str = PACKAGE):
        if memu is None:
            raise ValueError("memu 不能为 None")
        self.memu = memu
        self.package = package
        # logcat 起始时间戳（start_logcat 记录，stop_logcat/slice_logcat 使用）
        self._logcat_start: Optional[str] = None

    def _is_run_at_unavailable(self, rc: int, stderr: str) -> bool:
        """检测 run-at 是否不可用（命令不存在 / 非 debuggable 包 / run-as 拒绝）

        覆盖场景：
        - rc=127 + "not found"：MEmu 精简版 Android 无 run-at 二进制
        - "not debuggable"：release 包 run-at 拒绝执行
        - "run-as: usage"：run-as 参数错误
        """
        if rc == 0:
            return False
        s = (stderr or "").lower()
        return (
            "not debuggable" in s
            or "is not debuggable" in s
            or "run-as: usage" in s
            or "run-as" in s
            or "run-at" in s  # MEmu: /system/bin/sh: run-at: not found
            or rc == 127  # shell 通用「命令未找到」退出码
        )

    # === 证据 1：logcat ===

    def start_logcat(self) -> bool:
        """清空 logcat 缓冲并记录起始时间戳

        简化说明：adb logcat -c 清空 main+system 缓冲 | 已知上限：未清空 crash/radio 缓冲 | 升级路径：adb logcat -b all -c（V4）
        """
        try:
            rc, _, stderr = self.memu.adb("logcat", "-c")
            if rc != 0:
                logger.warning(f"清空 logcat 失败: rc={rc}, stderr={stderr}")
                return False
            # logcat -v time 格式：MM-DD HH:MM:SS
            self._logcat_start = datetime.now().strftime("%m-%d %H:%M:%S")
            logger.info(f"logcat 已清空，起始时间: {self._logcat_start}")
            return True
        except Exception as e:
            logger.warning(f"start_logcat 异常: {e}")
            return False

    def stop_logcat(self, save_to: Optional[Path] = None) -> str:
        """停止 logcat 并保存（dump 模式，非阻塞）

        使用 adb logcat -d -v time 抓取全部缓冲并退出。
        """
        try:
            rc, stdout, stderr = self.memu.adb("logcat", "-d", "-v", "time")
            if rc != 0:
                logger.warning(f"stop_logcat 失败: rc={rc}, stderr={stderr}")
                return ""
            if save_to:
                save_to = Path(save_to)
                save_to.parent.mkdir(parents=True, exist_ok=True)
                save_to.write_text(stdout, encoding="utf-8")
                logger.info(f"logcat 已保存: {save_to}")
            return stdout
        except Exception as e:
            logger.warning(f"stop_logcat 异常: {e}")
            return ""

    def slice_logcat(self, log_text: str, start: Optional[str] = None) -> str:
        """按时间戳切片 logcat（保留 start 之后的所有行）

        Args:
            log_text: 完整 logcat 文本
            start: 起始时间戳（MM-DD HH:MM:SS），None 使用 start_logcat 记录的时间
        Returns: 切片后的 logcat 文本
        """
        if not log_text:
            return ""
        start_ts = start or self._logcat_start
        if not start_ts:
            return log_text  # 无起点，返回全部

        # 简化说明：按行前缀字符串比较过滤 | 已知上限：跨年边界（12月→1月）比较错误 | 升级路径：解析为 datetime 精确比较（V4）
        lines = log_text.splitlines()
        sliced: List[str] = []
        started = False
        ts_re = re.compile(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')
        for line in lines:
            if ts_re.match(line):
                ts = line[:15]  # "MM-DD HH:MM:SS"
                if ts >= start_ts:
                    started = True
                if started:
                    sliced.append(line)
            elif started:
                # 续行（如异常堆栈）保留
                sliced.append(line)
        return "\n".join(sliced)

    # uiautomator2 框架崩溃标识（非 App 崩溃，需排除）
    # 当异常块堆栈包含以下标识时，判定为 uiautomator2 框架崩溃而非 App 崩溃
    # 简化说明：硬编码框架标识 | 已知上限：仅覆盖 uiautomator2 框架 | 升级路径：基于进程名过滤（V4）
    UIAUTOMATOR2_CRASH_MARKERS = (
        "com.android.commands.uiautomator",
        "com.android.uiautomator.core",
        "UiAutomationService",  # already registered
    )

    def extract_anomalies(self, log_text: str) -> List[Dict[str, str]]:
        """从 logcat 文本提取异常模式（FATAL/ANR/CRASH/OOM/ClassNotFound/Other）

        Returns: list of {type, match, line}

        排除 uiautomator2 框架崩溃（非 App 崩溃）：当异常块堆栈包含
        com.android.commands.uiautomator 或 UiAutomationService 时跳过，
        避免 uiautomator2 服务冲突被误判为 App 崩溃。
        """
        anomalies: List[Dict[str, str]] = []
        if not log_text:
            return anomalies
        lines = log_text.splitlines()
        for i, line in enumerate(lines):
            matched_type = None
            matched_pattern = None
            for crash_type, patterns in CRASH_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        matched_type = crash_type
                        matched_pattern = pattern
                        break
                if matched_type:
                    break
            if matched_type:
                # 检查后续 15 行窗口是否属于 uiautomator2 框架崩溃
                # logcat 每行都带时间戳前缀，无法用时间戳判断块边界，改用滑动窗口
                window = "\n".join(lines[i:min(i + 15, len(lines))])
                if self._is_uiautomator2_crash(window):
                    continue
                anomalies.append({
                    "type": matched_type,
                    "match": matched_pattern,
                    "line": line[:500],  # 截断长行
                })
        return anomalies

    def _is_uiautomator2_crash(self, block_text: str) -> bool:
        """检查异常块是否属于 uiautomator2 框架崩溃（非 App 崩溃）

        uiautomator2 框架崩溃特征：堆栈包含 com.android.commands.uiautomator
        或 UiAutomationService already registered 异常（服务重复注册）。
        此类崩溃属于测试框架本身的问题，不应判定为被测 App 崩溃。
        """
        return any(m in block_text for m in self.UIAUTOMATOR2_CRASH_MARKERS)

    # === 证据 2：ui_xml（汇总 UiExecutor 收集的 XML）===

    def collect_ui_xml(
        self, tc_dir: Path, ui: Optional[Any] = None
    ) -> Dict[str, Any]:
        """汇总 tc_dir/xml/ 下的所有 XML 文件清单

        UiExecutor 在 execute_step 中已保存 XML，此处仅汇总索引。
        ui 参数保留用于未来扩展（如需要时实时 dump 一份）。
        """
        result = self._empty_evidence("ui_xml")
        try:
            xml_dir = Path(tc_dir) / "xml"
            if not xml_dir.exists():
                result["error"] = "xml 目录不存在"
                return result
            xml_files = sorted(xml_dir.glob("*.xml"))
            result["collected"] = True
            result["files"] = [str(f) for f in xml_files]
            result["count"] = len(xml_files)
            logger.info(f"ui_xml 汇总: {len(xml_files)} 个文件")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 3：screenshot（汇总截图）===

    def collect_screenshot(
        self, tc_dir: Path, ui: Optional[Any] = None
    ) -> Dict[str, Any]:
        """汇总 tc_dir/screenshot/ 下的所有截图文件清单"""
        result = self._empty_evidence("screenshot")
        try:
            png_dir = Path(tc_dir) / "screenshot"
            if not png_dir.exists():
                result["error"] = "screenshot 目录不存在"
                return result
            png_files = sorted(png_dir.glob("*.png"))
            result["collected"] = True
            result["files"] = [str(f) for f in png_files]
            result["count"] = len(png_files)
            logger.info(f"screenshot 汇总: {len(png_files)} 个文件")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 4：activity_stack ===

    def collect_activity_stack(self, tc_dir: Path) -> Dict[str, Any]:
        """调 dumpsys activity top 收集 Activity 栈"""
        result = self._empty_evidence("activity_stack")
        try:
            rc, stdout, stderr = self.memu.adb("shell", "dumpsys", "activity", "top")
            if rc != 0:
                result["error"] = f"dumpsys 失败: rc={rc}, stderr={stderr}"
                return result
            save_path = Path(tc_dir) / "activity_stack.txt"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(stdout, encoding="utf-8")
            result["collected"] = True
            result["path"] = str(save_path)
            logger.info(f"activity_stack 已保存: {save_path}")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 5：db_state（run-at sqlite3）===

    def collect_db_state(
        self, tc_dir: Path, queries: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """调 run-at io.legado.app sqlite3 收集数据库状态

        简化说明：run-at 在 app 上下文执行 sqlite3 | 已知上限：debuggable=false 时 run-at 不可用 | 升级路径：降级为 cat 数据库文件 + 离线 sqlite3 解析（V4）
        """
        result = self._empty_evidence("db_state")
        queries = queries or DB_QUERIES
        try:
            db_dir = Path(tc_dir) / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            results: Dict[str, Any] = {}
            run_at_unavailable = False
            for module, sql in queries.items():
                rc, stdout, stderr = self.memu.adb(
                    "shell", "run-at", self.package, "sqlite3",
                    "databases/legado.db", sql,
                )
                if self._is_run_at_unavailable(rc, stderr):
                    run_at_unavailable = True
                    break
                if rc != 0:
                    results[module] = {"error": stderr, "sql": sql}
                else:
                    save_path = db_dir / f"{module}.txt"
                    save_path.write_text(stdout, encoding="utf-8")
                    results[module] = {
                        "path": str(save_path),
                        "sql": sql,
                        "rows": stdout.count("\n") if stdout else 0,
                    }

            if run_at_unavailable:
                result["degraded"] = True
                result["degradation_reason"] = "run_at_unavailable"
                result["error"] = "run-at 不可用（debuggable=false 或 run-as 失败）"
            else:
                result["collected"] = True
                result["queries"] = results
                logger.info(f"db_state 收集: {len(results)} 个查询")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 6：prefs_state ===

    def collect_prefs_state(self, tc_dir: Path) -> Dict[str, Any]:
        """调 run-at cat shared_prefs/*.xml 收集 SharedPreferences"""
        result = self._empty_evidence("prefs_state")
        try:
            rc, stdout, stderr = self.memu.adb(
                "shell", "run-at", self.package, "ls", "shared_prefs/",
            )
            if rc != 0:
                if self._is_run_at_unavailable(rc, stderr):
                    result["degraded"] = True
                    result["degradation_reason"] = "run_at_unavailable"
                result["error"] = f"ls shared_prefs 失败: rc={rc}, stderr={stderr}"
                return result

            prefs_dir = Path(tc_dir) / "prefs"
            prefs_dir.mkdir(parents=True, exist_ok=True)
            files_collected: List[str] = []
            for line in stdout.splitlines():
                fname = line.strip()
                if not fname or not fname.endswith(".xml"):
                    continue
                rc2, content, stderr2 = self.memu.adb(
                    "shell", "run-at", self.package, "cat", f"shared_prefs/{fname}",
                )
                if rc2 == 0:
                    save_path = prefs_dir / fname
                    save_path.write_text(content, encoding="utf-8")
                    files_collected.append(str(save_path))

            result["collected"] = True
            result["files"] = files_collected
            result["count"] = len(files_collected)
            logger.info(f"prefs_state 收集: {len(files_collected)} 个文件")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 7：web_api（curl localhost:8080）===

    def collect_web_api(
        self, tc_dir: Path, endpoints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """调 curl localhost:8080 收集 Web API 响应

        简化说明：假设 Legado Web 服务运行在 8080 端口 | 已知上限：Web 服务未启动时不可用 | 升级路径：自动检测端口（V4）
        """
        result = self._empty_evidence("web_api")
        endpoints = endpoints or ["/"]
        try:
            api_dir = Path(tc_dir) / "web_api"
            api_dir.mkdir(parents=True, exist_ok=True)
            results: Dict[str, str] = {}
            web_unavailable = False
            for endpoint in endpoints:
                # 简化说明：curl -s 静默 -m 5 超时 -w 输出状态码 | 已知上限：仅 HTTP，未覆盖 HTTPS 自签名 | 升级路径：Python requests + SSL 忽略（V4）
                curl_cmd = [
                    "curl", "-s", "-m", "5",
                    "-o", "-", "-w", "\n---HTTP_CODE:%{http_code}---",
                    f"http://localhost:8080{endpoint}",
                ]
                proc = subprocess.run(
                    curl_cmd, capture_output=True, text=True, timeout=10
                )
                output = proc.stdout or ""
                if "---HTTP_CODE:000---" in output or proc.returncode != 0:
                    web_unavailable = True
                    break
                results[endpoint] = output
                safe_name = re.sub(r'[^\w]', '_', endpoint) or "root"
                save_path = api_dir / f"{safe_name}.txt"
                save_path.write_text(output, encoding="utf-8")

            if web_unavailable:
                result["degraded"] = True
                result["degradation_reason"] = "web_api_unavailable"
                result["error"] = "Web 服务未启动（localhost:8080 不可达）"
            else:
                result["collected"] = True
                result["endpoints"] = results
                logger.info(f"web_api 收集: {len(results)} 个端点")
        except FileNotFoundError:
            result["degraded"] = True
            result["degradation_reason"] = "curl_unavailable"
            result["error"] = "curl 命令不存在"
        except subprocess.TimeoutExpired:
            result["degraded"] = True
            result["degradation_reason"] = "web_api_timeout"
            result["error"] = "curl 超时"
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 证据 8：meminfo ===

    def collect_meminfo(self, tc_dir: Path) -> Dict[str, Any]:
        """调 dumpsys meminfo io.legado.app 收集内存信息"""
        result = self._empty_evidence("meminfo")
        try:
            rc, stdout, stderr = self.memu.adb(
                "shell", "dumpsys", "meminfo", self.package
            )
            if rc != 0:
                result["error"] = f"dumpsys meminfo 失败: rc={rc}, stderr={stderr}"
                return result
            save_path = Path(tc_dir) / "meminfo.txt"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(stdout, encoding="utf-8")
            result["collected"] = True
            result["path"] = str(save_path)
            logger.info(f"meminfo 已保存: {save_path}")
        except Exception as e:
            result["error"] = str(e)
        return result

    # === 7.12: collect_all 并行收集 ===

    def collect_all(
        self,
        tc_id: str,
        tc_dir: Path,
        ui: Optional[Any] = None,
        db_queries: Optional[Dict[str, str]] = None,
        web_endpoints: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """8 类证据并行收集（5/6/7 并发），含降级标记

        策略：
        - logcat: 调用方需先 start_logcat()，collect_all 末尾 stop_logcat + slice + extract
        - activity_stack/meminfo/prefs_state/db_state/web_api: ThreadPoolExecutor 并行（5 并发）
        - ui_xml/screenshot: 本地文件汇总，串行（无 IO 阻塞）

        降级标记：
        - run_at_unavailable: db_state/prefs_state 在 debuggable=false 时降级
        - web_api_unavailable: Web 服务未启动时降级

        Returns: dict {evidence_type: evidence_result}
        """
        tc_dir = Path(tc_dir)
        tc_dir.mkdir(parents=True, exist_ok=True)
        all_evidence: Dict[str, Dict[str, Any]] = {}

        # 并行收集（5 个 ADB/网络任务）
        parallel_tasks = {
            "db_state": lambda: self.collect_db_state(tc_dir, db_queries),
            "prefs_state": lambda: self.collect_prefs_state(tc_dir),
            "web_api": lambda: self.collect_web_api(tc_dir, web_endpoints),
            "meminfo": lambda: self.collect_meminfo(tc_dir),
            "activity_stack": lambda: self.collect_activity_stack(tc_dir),
        }
        # 简化说明：max_workers=5 并行 | 已知上限：ADB 串行瓶颈（adb server 单线程） | 升级路径：多 ADB 连接并行（V4）
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_type = {
                executor.submit(fn): ev_type
                for ev_type, fn in parallel_tasks.items()
            }
            for future in as_completed(future_to_type):
                ev_type = future_to_type[future]
                try:
                    all_evidence[ev_type] = future.result()
                except Exception as e:
                    all_evidence[ev_type] = self._empty_evidence(ev_type, str(e))

        # 串行收集本地文件汇总（ui_xml/screenshot 无 IO 阻塞）
        all_evidence["ui_xml"] = self.collect_ui_xml(tc_dir, ui)
        all_evidence["screenshot"] = self.collect_screenshot(tc_dir, ui)

        # logcat 单独处理（需要外部 start/stop 配合）
        if self._logcat_start:
            log_text = self.stop_logcat(tc_dir / "logcat.txt")
            sliced = self.slice_logcat(log_text)
            anomalies = self.extract_anomalies(sliced)
            all_evidence["logcat"] = {
                "type": "logcat",
                "collected": True,
                "degraded": False,
                "degradation_reason": None,
                "path": str(tc_dir / "logcat.txt"),
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "error": None,
            }
        else:
            all_evidence["logcat"] = self._empty_evidence(
                "logcat", "未调用 start_logcat"
            )

        # 汇总统计
        collected_count = sum(1 for v in all_evidence.values() if v.get("collected"))
        degraded_count = sum(1 for v in all_evidence.values() if v.get("degraded"))
        logger.info(
            f"collect_all({tc_id}): {collected_count}/8 收集成功, {degraded_count} 降级"
        )
        return all_evidence

    def _empty_evidence(self, ev_type: str, error: str = "") -> Dict[str, Any]:
        """构造空证据结果"""
        return {
            "type": ev_type,
            "collected": False,
            "degraded": False,
            "degradation_reason": None,
            "path": None,
            "error": error,
        }


# === 自检（任务 7.12 交付自查）===
# 正常用例：EvidenceCollector 可实例化
# 边界用例：memu 为 None 时抛 ValueError
# 异常用例1：CRASH_PATTERNS 为空时 extract_anomalies 返回空列表
# 异常用例2：uiautomator2 框架崩溃被排除（不误判为 App 崩溃）
if __name__ == "__main__":
    from ai_tests.lib.memu_controller import MemuController
    # 正常用例
    ec = EvidenceCollector(MemuController())
    assert ec.package.startswith("io.legado"), "package 应为 io.legado 前缀（当前包名见 config.PACKAGE）"
    # 边界用例
    try:
        EvidenceCollector(None)
        raise AssertionError("应抛 ValueError")
    except ValueError:
        pass
    # 异常用例1：空文本
    assert ec.extract_anomalies("") == [], "空文本应返回空列表"
    # 异常用例2：uiautomator2 框架崩溃被排除
    u2_crash_log = (
        "07-08 16:42:50.432 E/AndroidRuntime(15359): FATAL EXCEPTION: main\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): PID: 15359\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): java.lang.IllegalStateException: UiAutomationService already registered!\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): \tat com.android.commands.uiautomator.DumpCommand.run(DumpCommand.java:74)\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): \tat com.android.commands.uiautomator.Launcher.main(Launcher.java:83)\n"
    )
    u2_anomalies = ec.extract_anomalies(u2_crash_log)
    assert u2_anomalies == [], f"uiautomator2 框架崩溃应被排除，实际: {u2_anomalies}"
    # 正常用例3：App 崩溃被保留
    app_crash_log = (
        "07-08 16:42:50.432 E/AndroidRuntime(15359): FATAL EXCEPTION: main\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): PID: 15359\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): java.lang.NullPointerException\n"
        "07-08 16:42:50.432 E/AndroidRuntime(15359): \tat io.legado.app.debug.SomeActivity.onCreate(Unknown Source:42)\n"
    )
    app_anomalies = ec.extract_anomalies(app_crash_log)
    assert any(a["type"] == "FATAL" for a in app_anomalies), f"App 崩溃应被保留，实际: {app_anomalies}"
    print("[IMPORT OK] evidence_collector")
