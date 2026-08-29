#!/usr/bin/env python
"""ai_tests/run_e2e.py — 编排层（V3 扩展命令）

串联 M1-M9 模块，端到端执行 E2E 测试。

用法：
    python ai_tests/run_e2e.py --apk auto --tc all
    python ai_tests/run_e2e.py --tc P0
    python ai_tests/run_e2e.py --tc TC-F-P0-1-01
    python ai_tests/run_e2e.py --diff HEAD~1          # V3（M8 未实现时降级）
    python ai_tests/run_e2e.py --gen-test BookshelfActivity  # V3（M9 未实现时提示）
    python ai_tests/run_e2e.py --feedback              # V3（M16 未实现时提示）

退出码：
    0 = 全部通过
    1 = 部分失败（有 fail 或 manual）
    2 = 致命错误（环境/APK/模拟器故障）
"""
import argparse
import logging
import re
import sys
import time  # noqa: F401（用例前置重置 sleep）
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_tests.config import (
    PACKAGE, MAIN_ACTIVITY, DOCS_TESTS_DIR, AI_TESTS_CASES_DIR,
    REPORTS_DIR, MEMU_INSTANCE_ID, MEMU_ADB_HOST, MEMUC_PATH,
)

logger = logging.getLogger(__name__)


# === 路径式步骤拆分（编排层预处理，非固化层 M3/M4）===

# 路径分隔符：→（U+2192）、>、>>、→→
_PATH_SEP_RE = re.compile(r'[→>]+')

# 需要清理的首尾字符：中英文引号、反引号、书名号、空格
_PATH_STRIP_CHARS = ' \t"\'`「」《》'


def _expand_path_steps(cases: list) -> int:
    """将含路径分隔符的 click 步骤拆成多个原子 click 步骤

    测试用例常写为 ``1. 进入"我的→调试工具→编码转换"``，case_parser 会解析成
    单个 Step(action=click, target="我的→调试工具→编码转换")，ui_executor 直接
    搜索整个字符串必然失败。本函数在编排层做预处理，把路径式步骤拆成多个
    原子 click（我的 / 调试工具 / 编码转换），使 ui_executor 能逐步导航。

    Returns:
        拆分的步骤数（0 表示无需拆分）
    """
    from ai_tests.lib.case_parser import Step

    expand_count = 0
    for tc in cases:
        new_steps = []
        for step in tc.steps:
            # 仅对含路径分隔符的 click 步骤拆分
            if step.action == "click" and _PATH_SEP_RE.search(step.target):
                segments = _PATH_SEP_RE.split(step.target)
                expanded = False
                for seg in segments:
                    seg = seg.strip().strip(_PATH_STRIP_CHARS)
                    if seg:
                        new_steps.append(Step(
                            action="click",
                            target=seg,
                            raw=f"{step.raw} ⟶ {seg}",
                        ))
                        expanded = True
                if expanded:
                    expand_count += 1
                else:
                    # 拆分后全部为空，保留原步骤
                    new_steps.append(step)
            else:
                new_steps.append(step)
        tc.steps = new_steps
    return expand_count


# === 10.1 CLI 参数解析 ===

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Legado E2E 自动化测试编排器（V3）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python ai_tests/run_e2e.py --apk auto --tc all        # 全量测试
  python ai_tests/run_e2e.py --tc P0                     # 仅 P0 优先级
  python ai_tests/run_e2e.py --tc F-P0-1                  # 指定模块
  python ai_tests/run_e2e.py --tc TC-F-P0-1-01            # 单用例
  python ai_tests/run_e2e.py --diff HEAD~1                # V3 源码影响分析
  python ai_tests/run_e2e.py --feedback                   # V3 反馈闭环
""",
    )
    # 基础参数
    parser.add_argument("--apk", default="auto",
                        help="APK 路径（auto=自动发现，默认 auto）")
    parser.add_argument("--tc", default="all",
                        help="用例筛选（all/P0/P1/模块名/TC-ID，默认 all）")
    parser.add_argument("--report-dir", default=None,
                        help="报告输出目录（默认自动生成时间戳目录）")
    parser.add_argument("--no-rules", action="store_true",
                        help="禁用规则判定（仅收集证据，不判定 verdict）")
    parser.add_argument("--keep-device", action="store_true",
                        help="测试完成后保留模拟器运行（默认关闭 App）")
    parser.add_argument("--instance-id", type=int, default=MEMU_INSTANCE_ID,
                        help=f"MEmu 实例 ID（默认 {MEMU_INSTANCE_ID}）")
    parser.add_argument("--init-device", action="store_true",
                        help="强制重新初始化 uiautomator2（首次使用时加）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细日志模式（DEBUG 级别，含子模块详细输出）")

    # V3 新增参数（M8/M9/M16 未实现时降级处理）
    parser.add_argument("--diff", default=None,
                        help="V3: git ref 触发源码影响分析（如 HEAD~1）")
    parser.add_argument("--gen-test", default=None,
                        help="V3: 为指定 Activity 生成 Python 测试骨架")
    parser.add_argument("--update-source-map", action="store_true",
                        help="V3: 重建 source_map.json")
    parser.add_argument("--feedback", action="store_true",
                        help="V3: 触发反馈闭环处理")
    parser.add_argument("--ai-verify", action="store_true",
                        help="AI-LLM-Testing: 报告生成后自动拉起 VL 模型判定 manual 用例并回填 ai_verdict")

    return parser.parse_args(argv)


# === 10.6 --tc 筛选逻辑 ===

def filter_cases(cases: list, tc_filter: str) -> list:
    """根据 --tc 参数筛选用例

    支持：
    - all: 全部用例
    - P0/P1: 按优先级筛选（TC-ID 中含 -P0- / -P1-）
    - F-P0-1: 按模块名筛选（case.module == tc_filter）
    - TC-XXX: 单用例 ID（case.tc_id == tc_filter）
    """
    if tc_filter == "all":
        return cases

    if tc_filter in ("P0", "P1"):
        return [c for c in cases if f"-{tc_filter}-" in c.tc_id]

    if tc_filter.startswith("TC-"):
        return [c for c in cases if c.tc_id == tc_filter]

    # 模块名（如 F-P0-1）
    return [c for c in cases if c.module == tc_filter]


# === V3 预留参数降级处理 ===

def handle_v3_reserved_args(args: argparse.Namespace) -> Optional[int]:
    """处理 V3 预留参数（M8 已实现，M9/M16 未实现时降级）

    Returns: int 退出码（None 表示继续执行）

    说明：
    - --diff：M8 已实现，不在降级处理范围，由 main() 中步骤 5.5 处理
    - --update-source-map：M8 已实现，调用 build_source_map 后退出
    - --gen-test：M9 未实现，仅提示并退出码 0
    - --feedback：M16 未实现，仅警告
    """
    # --update-source-map：M8 已实现，重建 source_map.json 后退出
    if args.update_source_map:
        try:
            from ai_tests.lib.source_impact_analyzer import SourceImpactAnalyzer
            print(f"[V3] 重建 source_map.json...")
            sia = SourceImpactAnalyzer()
            source_map = sia.build_source_map()
            activities = source_map.get("activities", {})
            all_tc_ids = set()
            for info in activities.values():
                all_tc_ids.update(info.get("tc_ids", []))
            print(f"    完成：{len(activities)} 个 Activity，{len(all_tc_ids)} 个关联 TC-ID")
            return 0
        except Exception as e:
            print(f"[FATAL] 重建 source_map 失败: {e}")
            return 2

    # --gen-test：M9 未实现（阶段 13）
    if args.gen_test:
        print("[WARN] M9 source_test_generator 未实现（阶段 13），--gen-test 暂不支持")
        print(f"       请求的 Activity: {args.gen_test}")
        print("       降级路径：手动编写 ai_tests/cases/{module}/auto_{tc_id}.py")
        return 0  # 仅提示，不视为错误

    # --feedback：M16 未实现（阶段 16）
    if args.feedback:
        print("[WARN] M16 feedback_loop 未实现（阶段 16），--feedback 暂不支持")
        print("       降级路径：手动审阅 reports/*/feedback_suggestions.md")

    return None


# === 10.8 主流程 ===

def _execute_steps_with_skip(ui, steps, screenshot_dir, xml_dir):
    """执行步骤列表，失败后跳过后续步骤（OpenSpec e2e-ui-executor-hardening R3）

    步骤失败后后续步骤标记 SKIPPED，避免在错误页面执行。
    提取为独立函数以支持单元测试（3.6）。

    Args:
        ui: UiExecutor 实例
        steps: Step 列表
        screenshot_dir: 截图目录
        xml_dir: XML 目录
    Returns:
        list[dict]: 每个步骤的结果（SKIPPED 步骤含 success=False, error="SKIPPED"）
    """
    results = []
    skip_remaining = False
    for step_idx, step in enumerate(steps, 1):
        if skip_remaining:
            logger.info(f"步骤 {step_idx} SKIPPED（前序步骤失败）")
            results.append({"success": False, "error": "SKIPPED", "step_index": step_idx})
            continue
        result = ui.execute_step_with_heal(
            step,
            screenshot_dir=screenshot_dir,
            xml_dir=xml_dir,
            step_index=step_idx,
        )
        if not result.get("success", False):
            logger.warning(
                f"步骤 {step_idx} 失败，跳过后续 {len(steps) - step_idx} 个步骤"
            )
            skip_remaining = True
        results.append(result)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    """主流程入口

    流程：环境校验 → V3 预留参数处理 → 启动模拟器 → init u2 →
          部署 APK → 解析用例 → 启动日志 → 逐用例执行 →
          停止日志 → 生成报告 → 清理 → 退出码
    """
    args = parse_args(argv)

    # 配置日志（--verbose 时启用 DEBUG 级别）
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("Legado E2E 自动化测试（V3）")
    print("=" * 70)
    print()

    # V3 预留参数降级处理
    early_exit = handle_v3_reserved_args(args)
    if early_exit is not None:
        return early_exit

    # 延迟导入（避免模块导入失败时 CLI 参数解析也失败）
    try:
        from ai_tests.lib.memu_controller import MemuController
        from ai_tests.lib.apk_deployer import ApkDeployer
        from ai_tests.lib.case_parser import CaseParser
        from ai_tests.lib.evidence_collector import EvidenceCollector
        from ai_tests.lib.rule_analyzer import RuleAnalyzer
        from ai_tests.lib.report_generator import ReportGenerator
        from ai_tests.scripts.init_device import init_uiautomator2, is_uiautomator2_ready
    except ImportError as e:
        print(f"[FATAL] 模块导入失败: {e}")
        print("        请确认 ai_tests/lib/ 下所有模块已实现")
        return 2

    # 1. 创建报告目录（先创建，以便证据归档）
    report_dir = Path(args.report_dir) if args.report_dir else None
    rg = ReportGenerator(report_dir=report_dir)
    print(f"[1] 报告目录: {rg.report_dir}")

    # 2. 启动模拟器
    print(f"[2] 启动 MEmu 实例 {args.instance_id}...")
    memu = MemuController(instance_id=args.instance_id)
    if not memu.is_running():
        if not memu.start():
            print(f"[FATAL] 模拟器启动失败（实例 {args.instance_id}）")
            print("        可能原因：MEmu 未安装/路径错误/实例已锁定")
            print(f"        MEmu 路径: {MEMUC_PATH}")
            return 2
    serial = memu.wait_for_adb()
    if not serial:
        print("[FATAL] ADB 连接失败（模拟器已启动但 ADB 未就绪）")
        print("        可能原因：ADB 端口冲突/模拟器启动慢/ADB 服务异常")
        print(f"        预期 ADB 地址: {MEMU_ADB_HOST}")
        return 2
    print(f"    ADB 就绪: {serial}")

    # 3. 初始化 uiautomator2
    print("[3] 初始化 uiautomator2...")
    try:
        if args.init_device or not is_uiautomator2_ready(memu):
            device = init_uiautomator2(memu)
        else:
            import uiautomator2 as u2
            device = u2.connect(MEMU_ADB_HOST)
        print(f"    uiautomator2 就绪")
    except Exception as e:
        print(f"[FATAL] uiautomator2 初始化失败: {e}")
        print("        尝试添加 --init-device 参数强制初始化")
        return 2

    # 4. 部署 APK
    print("[4] 部署 APK...")
    deployer = ApkDeployer(memu=memu)
    apk_path = args.apk
    if apk_path == "auto":
        apk_path = deployer.discover_apk()
        if not apk_path:
            print("[FATAL] 未发现 APK，请先构建或指定 --apk <path>")
            return 2
    if not deployer.validate_apk(apk_path):
        print(f"[FATAL] APK 校验失败: {apk_path}")
        return 2
    print(f"    APK: {apk_path}")
    deployer.install(apk_path)
    deployer.start_app()
    if not deployer.wait_for_first_frame():
        print("[WARN] App 首屏未在超时内渲染，继续执行...")
    print("    App 已启动")

    # 5. 解析用例
    print("[5] 解析用例...")
    parser = CaseParser()
    cases = parser.parse_directory(str(DOCS_TESTS_DIR))
    # 修复：遍历 ai_tests/cases/{module}/*.md（原 parse_directory 只扫顶层 *.md，漏掉全部模块子目录，含 F-UI-THEME 与既有 F-P0-*）
    if AI_TESTS_CASES_DIR.exists():
        for _case_dir in sorted(AI_TESTS_CASES_DIR.iterdir()):
            if _case_dir.is_dir() and not _case_dir.name.startswith("__"):
                cases += parser.parse_directory(str(_case_dir))
    print(f"    解析到 {len(cases)} 个用例")

    # 路径式步骤拆分（编排层预处理，非固化层 M3/M4）
    expand_count = _expand_path_steps(cases)
    if expand_count:
        print(f"    路径式步骤拆分: {expand_count} 个步骤已展开为原子点击")

    # 5.5 V3 --diff 源码影响分析（M8）
    # 简化说明：--diff 与 --tc 互斥时优先 --diff | 已知上限：source_map.json 可能过时 | 升级路径：自动检测源码变化触发重建（V4）
    diff_tc_ids = None
    if args.diff:
        from ai_tests.lib.source_impact_analyzer import SourceImpactAnalyzer
        print(f"[5.5] V3 源码影响分析: --diff {args.diff}")
        sia = SourceImpactAnalyzer()
        diff_result = sia.analyze_diff(args.diff)
        diff_tc_ids = set(diff_result.get("related_tc_ids", []))
        print(
            f"    改动文件: {len(diff_result['changed_files'])}, "
            f"受影响 Activity: {len(diff_result['affected_activities'])}, "
            f"关联 TC-ID: {len(diff_tc_ids)}"
        )
        if not diff_tc_ids:
            print("    [WARN] 无关联 TC-ID，降级为 --tc all")
            args.tc = "all"

    # 6. 用例筛选（--diff 优先于 --tc）
    if diff_tc_ids:
        cases = [c for c in cases if c.tc_id in diff_tc_ids]
        print(f"    筛选后 {len(cases)} 个用例（--diff 模式）")
    else:
        cases = filter_cases(cases, args.tc)
        print(f"    筛选后 {len(cases)} 个用例（filter={args.tc}）")

    # 7. 前置资源检查（user_required 缺失则跳过）
    skipped = [c for c in cases if c.missing_precondition]
    cases = [c for c in cases if not c.missing_precondition]
    if skipped:
        print(f"    跳过 {len(skipped)} 个缺失前置资源的用例")

    if not cases:
        print("[WARN] 无可执行用例")
        rg.generate_all(
            [],
            env={
                "device": "MEmu",
                "timestamp": datetime.now().isoformat(),
                "instance_id": args.instance_id,
                "adb_serial": serial,
            },
            apk_info={"name": Path(apk_path).name, "path": apk_path},
        )
        if not args.keep_device:
            memu.stop_app(PACKAGE)
        return 0

    # 8. 启动日志
    print("[6] 启动 logcat 收集...")
    ec = EvidenceCollector(memu=memu, package=PACKAGE)
    ec.start_logcat()

    # 9. 逐用例执行（失败不阻断）
    from ai_tests.lib.ui_executor import UiExecutor
    ui = UiExecutor(device=device, memu=memu)
    analyzer = RuleAnalyzer()

    results = []
    total = len(cases)
    print(f"[7] 逐用例执行（共 {total} 个）...")
    for i, tc in enumerate(cases, 1):
        progress = f"{i*100//total}%" if total > 0 else "0%"
        print(f"  [{i}/{total} {progress}] {tc.tc_id}: {tc.title}", end="")
        try:
            # 创建用例证据目录
            tc_dir = rg.report_dir / "cases" / tc.tc_id
            tc_dir.mkdir(parents=True, exist_ok=True)

            # V3 双轨调度：track_source="python" 时优先执行 B 轨 Python 用例
            # 简化说明：M9 sourceTestGenerator 未实现，B 轨 Python 用例暂无法自动生成 | 已知上限：仅 MD 轨可执行 | 升级路径：M9 实现后调用 auto_*.py
            if tc.track_source == "python" and tc.python_track_path:
                if Path(tc.python_track_path).exists():
                    print(f" → [B轨] python={tc.python_track_path}", end="")
                    # M9 未实现：暂降级为 MD 执行（后续实现 _run_python_track 方法）
                    logger.warning(f"Python 轨道未实现，降级为 MD 执行: {tc.python_track_path}")
                else:
                    logger.warning(f"Python 轨道文件不存在，降级为 MD 执行: {tc.python_track_path}")

            # 执行步骤（MD 轨或 B 轨降级，带自愈机制 + 失败跳过）
            # 简化说明：execute_step_with_heal 区分元素未找到 vs App崩溃 | 已知上限：不检测 ANR/卡死 | 升级路径：多维度健康检查（V4）
            # 失败跳过（OpenSpec e2e-ui-executor-hardening R3）：步骤失败后后续标记 SKIPPED，避免在错误页面执行
            # 截图/XML 保存到子目录，与 evidence_collector.collect_screenshot/collect_ui_xml 期望路径一致
            screenshot_dir = tc_dir / "screenshot"
            xml_dir = tc_dir / "xml"
            # 每用例前置：冷启动回主界面（隔离用例间状态；页面无关用例依赖主 Tab 导航）
            try:
                memu.adb("shell", "am", "force-stop", PACKAGE, timeout=20)
                time.sleep(1)
                memu.adb("shell", "am", "start", "-n",
                         f"{PACKAGE}/io.legado.app.ui.main.MainActivity", timeout=20)
                # 等待主界面 Tab 就绪（App 冷启动可能 5-10s）
                for _ in range(20):
                    try:
                        if device(description="我的").exists(timeout=1.0):
                            break
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(1)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"用例前置重置失败，继续执行: {e}")
            _execute_steps_with_skip(ui, tc.steps, screenshot_dir, xml_dir)

            # 8 类证据收集
            evidence = ec.collect_all(tc.tc_id, tc_dir)

            # 规则判定（--no-rules 时跳过）
            if args.no_rules:
                result = {
                    "verdict": "manual",
                    "confidence": 0,
                    "reason": "--no-rules 模式，未执行规则判定",
                    "evidence": evidence,
                }
            else:
                result = analyzer.analyze(tc, evidence)

            # 合并用例元信息
            result["tc_id"] = tc.tc_id
            result["title"] = tc.title
            result["module"] = tc.module
            result["case_type"] = tc.case_type
            result["track_source"] = tc.track_source
            result["evidence"] = evidence

            # 保存 ai-prompt（manual 时）
            if result.get("ai_prompt"):
                prompt_path = tc_dir / "ai-prompt.md"
                prompt_path.write_text(result["ai_prompt"], encoding="utf-8")
                result["ai_prompt_path"] = str(prompt_path)

            results.append(result)
            verdict = result.get("verdict", "unknown")
            print(f" → {verdict}")

        except Exception as e:
            print(f" → ERROR: {e}")
            logger.error(f"用例执行异常 {tc.tc_id}: {e}\n{traceback.format_exc()}")
            results.append({
                "tc_id": tc.tc_id,
                "title": tc.title,
                "module": tc.module,
                "case_type": tc.case_type,
                "verdict": "fail",
                "confidence": 0,
                "reason": f"执行异常: {type(e).__name__}: {e}",
                "evidence": {},
                "track_source": tc.track_source,
            })

    # 10. 停止日志
    print("[8] 停止 logcat...")
    ec.stop_logcat()

    # 11. 生成报告（七件套）
    print("[9] 生成报告...")
    env = {
        "device": "MEmu",
        "timestamp": datetime.now().isoformat(),
        "instance_id": args.instance_id,
        "adb_serial": serial,
    }
    apk_info = {
        "name": Path(apk_path).name,
        "path": apk_path,
    }
    # V3 从 results 中提取 feedback_signals（fail/manual 时 RuleAnalyzer 输出）
    feedback_signals = [
        r["feedback_signal"] for r in results
        if r.get("feedback_signal")
    ]
    # V3 affected_modules 需要 M8 实现（暂为 None）
    rg.generate_all(
        results,
        env=env,
        apk_info=apk_info,
        affected_modules=None,
        feedback_signals=feedback_signals if feedback_signals else None,
    )

    # 11.5 AI-LLM-Testing：--ai-verify 自动判定 manual 用例并回填 ai_verdict
    if args.ai_verify:
        print("[9.5] AI 判定器: 拉起 VL 模型判定 manual 用例...")
        from ai_tests.lib.llm_server import LlmServerManager, LlmUnavailableError
        from ai_tests.lib.ai_verifier import AiVerifier
        mgr = LlmServerManager()
        try:
            info = mgr.ensure_online()
            print(f"    模型服务在线: {info}")
            verifier = AiVerifier(report_dir=rg.report_dir)
            summary = verifier.verify_report(rg.report_dir / "report.json")
            print(
                f"    AI 判定: manual={summary['manual_total']} "
                f"ai_verified={summary['ai_verified']} "
                f"skipped={summary['skipped']} unavailable={summary['ai_unavailable']}"
            )
        except LlmUnavailableError as e:
            print(f"    [WARN] 模型不可用，判定器降级（规则判定保持不变）: {e}")
        finally:
            mgr.stop()

    # 12. 清理
    if not args.keep_device:
        print("[10] 停止 App...")
        memu.stop_app(PACKAGE)

    # 13. 退出码
    summary = rg._calc_summary(results)
    print()
    print("=" * 70)
    print(f"汇总: total={summary['total']} pass={summary['pass']} "
          f"fail={summary['fail']} warning={summary['warning']} "
          f"manual={summary['manual']} pass_rate={summary['pass_rate']}%")
    print(f"报告: {rg.report_dir}")
    print("=" * 70)

    if summary["fail"] == 0 and summary["manual"] == 0:
        return 0  # 全部通过
    else:
        return 1  # 部分失败


if __name__ == "__main__":
    sys.exit(main())
