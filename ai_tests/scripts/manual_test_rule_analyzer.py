"""ai_tests/scripts/manual_test_rule_analyzer.py — M6 集成实测验证脚本

验证 M5 证据收集 + M6 规则分析的端到端流程。

用法：
    python ai_tests/scripts/manual_test_rule_analyzer.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.config import REPORTS_DIR, PACKAGE
from ai_tests.lib.memu_controller import MemuController
from ai_tests.lib.evidence_collector import EvidenceCollector
from ai_tests.lib.rule_analyzer import RuleAnalyzer
from ai_tests.lib.case_parser import TestCase, Expect, Step


def main() -> int:
    print("=" * 60)
    print("M6 集成实测验证：M5 证据 + M6 规则分析 端到端")
    print("=" * 60)

    memu = MemuController()

    # 1. 确保模拟器运行
    if not memu.is_running():
        print("[1] 启动 MEmu...")
        if not memu.start():
            print("[FAIL] MEmu 启动失败")
            return 1

    # 2. 创建收集器和分析器
    ec = EvidenceCollector(memu)
    analyzer = RuleAnalyzer()

    # 3. 创建测试目录
    tc_id = "TC-M6-INTEGRATION-01"
    tc_dir = REPORTS_DIR / f"m6_test_{time.strftime('%Y%m%d_%H%M%S')}" / "cases" / tc_id
    tc_dir.mkdir(parents=True, exist_ok=True)
    print(f"[2] 测试目录: {tc_dir}")

    # 4. 创建模拟用例（no_crash 预期）
    test_case = TestCase(
        tc_id=tc_id,
        title="M5+M6 集成验证用例",
        module="F-P0-1",
        case_type="正常用例",
        expects=[Expect(expect_type="no_crash", description="App 不崩溃")],
        steps=[Step(raw="等待 App 运行", action="sleep", target="3")],
    )

    # 5. 创建模拟 ui_xml/screenshot（模拟 M4 产物）
    xml_dir = tc_dir / "xml"
    xml_dir.mkdir(exist_ok=True)
    (xml_dir / "step-01-before.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><hierarchy/>', encoding="utf-8"
    )
    png_dir = tc_dir / "screenshot"
    png_dir.mkdir(exist_ok=True)
    (png_dir / "step-01-before.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

    # 6. 启动 logcat + 收集证据
    print("[3] 启动 logcat...")
    ec.start_logcat()
    time.sleep(2)

    print("[4] collect_all 并行收集 8 类证据...")
    evidence = ec.collect_all(tc_id, tc_dir)

    # 7. 规则分析
    print("\n[5] 规则分析...")
    result = analyzer.analyze(test_case, evidence)

    # 8. 打印结果
    print("\n" + "=" * 60)
    print("规则分析结果：")
    print("=" * 60)
    print(f"  verdict: {result['verdict']}")
    print(f"  confidence: {result['confidence']}")
    print(f"  reason: {result['reason']}")

    if result.get("feedback_signal"):
        fs = result["feedback_signal"]
        print(f"\n  feedback_signal:")
        print(f"    tc_id: {fs['tc_id']}")
        print(f"    verdict: {fs['verdict']}")
        print(f"    failure_pattern: {fs['failure_pattern']}")
        print(f"    suggested_rule: {fs['suggested_rule']}")
        print(f"    suggested_prompt: {fs['suggested_prompt']}")

    if result.get("ai_prompt"):
        print(f"\n  ai_prompt 长度: {len(result['ai_prompt'])} 字符")
        # 验证 ai-prompt.md 已保存
        manual_dir = REPORTS_DIR / "manual_cases"
        if manual_dir.exists():
            prompt_files = list(manual_dir.glob(f"{tc_id}*ai-prompt.md"))
            if prompt_files:
                print(f"  ai-prompt.md 已保存: {prompt_files[0]}")

    # 9. 验证判定合理性
    print("\n" + "=" * 60)
    print("判定合理性验证：")
    print("=" * 60)

    # 场景 1：no_crash 预期 + 无异常 → 应该 pass
    logcat = evidence.get("logcat", {})
    anomaly_count = logcat.get("anomaly_count", 0)
    if anomaly_count == 0:
        if result["verdict"] == "pass":
            print("  [PASS] 无异常 + no_crash 预期 → pass（符合预期）")
        else:
            print(f"  [WARN] 无异常但 verdict={result['verdict']}（可能因降级证据影响）")

    # 场景 2：构造一个 FATAL 异常场景
    print("\n  构造 FATAL 异常场景验证...")
    fatal_evidence = dict(evidence)
    fatal_evidence["logcat"] = {
        "collected": True,
        "degraded": False,
        "anomalies": [{"type": "FATAL", "match": r"FATAL EXCEPTION", "line": "FATAL EXCEPTION: main"}],
        "anomaly_count": 1,
    }
    fatal_result = analyzer.analyze(test_case, fatal_evidence)
    if fatal_result["verdict"] == "fail":
        print(f"  [PASS] FATAL 异常 → fail (confidence={fatal_result['confidence']})")
    else:
        print(f"  [FAIL] FATAL 异常应判定 fail，实际: {fatal_result['verdict']}")

    # 场景 3：构造 manual 预期场景
    print("\n  构造 manual 预期场景验证...")
    manual_tc = TestCase(
        tc_id="TC-M6-MANUAL-TEST",
        title="manual 预期测试",
        expects=[Expect(expect_type="manual", description="需人工判定")],
    )
    manual_result = analyzer.analyze(manual_tc, evidence)
    if manual_result["verdict"] == "manual":
        print(f"  [PASS] manual 预期 → manual (confidence={manual_result['confidence']})")
        if manual_result.get("ai_prompt"):
            print(f"  [PASS] ai_prompt 已生成（{len(manual_result['ai_prompt'])} 字符）")
        if manual_result.get("feedback_signal"):
            print(f"  [PASS] feedback_signal 已生成")
    else:
        print(f"  [FAIL] manual 预期应判定 manual，实际: {manual_result['verdict']}")

    # 10. 总结
    print("\n" + "=" * 60)
    all_pass = (
        result["verdict"] in ("pass", "warning", "manual")
        and fatal_result["verdict"] == "fail"
        and manual_result["verdict"] == "manual"
    )
    if all_pass:
        print("[PASS] M6 集成实测验证通过")
        return 0
    else:
        print("[FAIL] M6 集成实测验证未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
