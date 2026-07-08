"""ai_tests/tests/test_rule_analyzer.py — M6 单元测试

任务 8.9 验证：4 种 verdict 路径 + manual 时 ai-prompt.md 生成 + V3 feedback_signal 输出

运行：
    python -m pytest ai_tests/tests/test_rule_analyzer.py -v
或：
    python ai_tests/tests/test_rule_analyzer.py
"""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.rule_analyzer import RuleAnalyzer
from ai_tests.lib.case_parser import TestCase, Expect, Step


def _make_tc(
    tc_id: str = "TC-TEST-01",
    title: str = "测试用例",
    expects: list = None,
    steps: list = None,
) -> TestCase:
    """构造测试用例"""
    return TestCase(
        tc_id=tc_id,
        title=title,
        module="F-P0-1",
        case_type="正常用例",
        expects=expects or [],
        steps=steps or [],
    )


def _make_evidence(
    logcat_anomalies: list = None,
    logcat_collected: bool = True,
    ui_xml_collected: bool = True,
    activity_stack_collected: bool = True,
    db_state_collected: bool = True,
    prefs_state_collected: bool = True,
    web_api_collected: bool = True,
    meminfo_collected: bool = True,
) -> dict:
    """构造测试证据"""
    anomalies = logcat_anomalies or []
    return {
        "logcat": {
            "collected": logcat_collected,
            "degraded": False,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
        },
        "ui_xml": {"collected": ui_xml_collected, "degraded": False, "count": 2, "files": []},
        "screenshot": {"collected": True, "degraded": False, "count": 2, "files": []},
        "activity_stack": {"collected": activity_stack_collected, "degraded": False, "path": ""},
        "db_state": {"collected": db_state_collected, "degraded": False, "queries": {}},
        "prefs_state": {"collected": prefs_state_collected, "degraded": False, "files": [], "count": 0},
        "web_api": {"collected": web_api_collected, "degraded": False, "endpoints": {}},
        "meminfo": {"collected": meminfo_collected, "degraded": False, "path": ""},
    }


# === 8.1 类骨架 ===

def test_rule_analyzer_instantiation():
    """正常用例：RuleAnalyzer 可实例化"""
    analyzer = RuleAnalyzer()
    assert analyzer.FATAL_TYPES == {"FATAL", "ANR", "CRASH"}
    assert analyzer.WARNING_TYPES == {"OOM", "ClassNotFound", "Other"}
    print("[PASS] test_rule_analyzer_instantiation")


# === 8.2 规则 1：FATAL/CRASH/ANR → fail ===

def test_rule_fatal_crash_fatal():
    """正常用例：FATAL 异常 → fail"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "FATAL", "match": r"FATAL EXCEPTION", "line": "FATAL EXCEPTION: main"}]
    )
    result = analyzer._rule_fatal_crash(evidence)
    assert result is not None
    assert result["verdict"] == "fail"
    assert result["confidence"] == 95
    print("[PASS] test_rule_fatal_crash_fatal")


def test_rule_fatal_crash_anr():
    """正常用例：ANR 异常 → fail"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "ANR", "match": r"ANR in", "line": "ANR in io.legado.app"}]
    )
    result = analyzer._rule_fatal_crash(evidence)
    assert result is not None
    assert result["verdict"] == "fail"
    print("[PASS] test_rule_fatal_crash_anr")


def test_rule_fatal_crash_no_anomaly():
    """边界用例：无致命异常 → None"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer._rule_fatal_crash(evidence)
    assert result is None
    print("[PASS] test_rule_fatal_crash_no_anomaly")


def test_rule_fatal_crash_only_warning():
    """边界用例：仅有 Exception（非 Fatal）→ None"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "Other", "match": r"Exception", "line": "NullPointerException"}]
    )
    result = analyzer._rule_fatal_crash(evidence)
    assert result is None
    print("[PASS] test_rule_fatal_crash_only_warning")


# === 8.3 规则 2：Exception/Error → warning ===

def test_rule_exception_warning_other():
    """正常用例：Other 异常 → warning"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "Other", "match": r"Exception", "line": "NullPointerException"}]
    )
    result = analyzer._rule_exception_warning(evidence)
    assert result is not None
    assert result["verdict"] == "warning"
    assert result["confidence"] == 80
    print("[PASS] test_rule_exception_warning_other")


def test_rule_exception_warning_oom():
    """正常用例：OOM 异常 → warning"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "OOM", "match": r"OutOfMemoryError", "line": "OutOfMemoryError"}]
    )
    result = analyzer._rule_exception_warning(evidence)
    assert result is not None
    assert result["verdict"] == "warning"
    print("[PASS] test_rule_exception_warning_oom")


def test_rule_exception_warning_no_anomaly():
    """边界用例：无异常 → None"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer._rule_exception_warning(evidence)
    assert result is None
    print("[PASS] test_rule_exception_warning_no_anomaly")


# === 8.4 规则 3：无异常 + 证据匹配 → pass ===

def test_rule_pass_with_evidence_success():
    """正常用例：无异常 + no_crash 预期匹配 → pass"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="no_crash", description="不崩溃")])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer._rule_pass_with_evidence(tc, evidence)
    assert result is not None
    assert result["verdict"] == "pass"
    assert result["confidence"] == 85
    print("[PASS] test_rule_pass_with_evidence_success")


def test_rule_pass_with_evidence_has_anomaly():
    """边界用例：有异常 → None（走规则 2/1）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="no_crash")])
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "Other", "match": "", "line": "Exception"}]
    )
    result = analyzer._rule_pass_with_evidence(tc, evidence)
    # _rule_pass_with_evidence 只检查 expect 匹配，不检查 anomaly
    # no_crash 预期在有异常时不匹配
    assert result is None
    print("[PASS] test_rule_pass_with_evidence_has_anomaly")


def test_rule_pass_with_evidence_manual_expect():
    """边界用例：manual 预期 → None（无法自动 pass）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="manual")])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer._rule_pass_with_evidence(tc, evidence)
    assert result is None
    print("[PASS] test_rule_pass_with_evidence_manual_expect")


def test_rule_pass_with_evidence_no_expects():
    """边界用例：无预期 → None"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer._rule_pass_with_evidence(tc, evidence)
    assert result is None
    print("[PASS] test_rule_pass_with_evidence_no_expects")


def test_rule_pass_with_evidence_degraded_ok():
    """正常用例：降级证据也算匹配（db_state/prefs_state/web_api）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[
        Expect(expect_type="db_state"),
        Expect(expect_type="prefs_state"),
        Expect(expect_type="web_api"),
    ])
    evidence = _make_evidence(
        db_state_collected=False,
        prefs_state_collected=False,
        web_api_collected=False,
    )
    # 设置降级标记
    evidence["db_state"]["degraded"] = True
    evidence["prefs_state"]["degraded"] = True
    evidence["web_api"]["degraded"] = True
    result = analyzer._rule_pass_with_evidence(tc, evidence)
    assert result is not None
    assert result["verdict"] == "pass"
    print("[PASS] test_rule_pass_with_evidence_degraded_ok")


# === _check_expect_match 全类型验证 ===

def test_check_expect_match_all_types():
    """正常用例：8 种 expect_type 匹配验证"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(logcat_anomalies=[])

    # no_crash: 无异常 → True
    assert analyzer._check_expect_match(Expect(expect_type="no_crash"), evidence) is True
    # log_clean: 无任何异常 → True
    assert analyzer._check_expect_match(Expect(expect_type="log_clean"), evidence) is True
    # page_jump: activity_stack collected → True
    assert analyzer._check_expect_match(Expect(expect_type="page_jump"), evidence) is True
    # element_visible: ui_xml collected → True
    assert analyzer._check_expect_match(Expect(expect_type="element_visible"), evidence) is True
    # text_match: ui_xml collected → True
    assert analyzer._check_expect_match(Expect(expect_type="text_match"), evidence) is True
    # db_state: collected → True
    assert analyzer._check_expect_match(Expect(expect_type="db_state"), evidence) is True
    # prefs_state: collected → True
    assert analyzer._check_expect_match(Expect(expect_type="prefs_state"), evidence) is True
    # web_api: collected → True
    assert analyzer._check_expect_match(Expect(expect_type="web_api"), evidence) is True
    # manual: → False
    assert analyzer._check_expect_match(Expect(expect_type="manual"), evidence) is False
    # 未知类型 → False
    assert analyzer._check_expect_match(Expect(expect_type="unknown"), evidence) is False
    print("[PASS] test_check_expect_match_all_types")


def test_check_expect_match_no_crash_with_anomaly():
    """边界用例：no_crash 预期但有异常 → False"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "FATAL", "match": "", "line": "FATAL"}]
    )
    assert analyzer._check_expect_match(Expect(expect_type="no_crash"), evidence) is False
    print("[PASS] test_check_expect_match_no_crash_with_anomaly")


# === 8.5 规则 4：证据不足 → manual ===

def test_rule_manual_insufficient():
    """正常用例：证据不足 → manual"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    result = analyzer._rule_manual_insufficient(tc, {}, "测试原因")
    assert result["verdict"] == "manual"
    assert result["confidence"] == 50
    assert result["reason"] == "测试原因"
    assert "evidence_summary" in result
    print("[PASS] test_rule_manual_insufficient")


# === 8.7 analyze 主入口（4 种 verdict 路径）===

def test_analyze_fatal_path():
    """正常用例：FATAL 异常 → fail 路径"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="no_crash")])
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "FATAL", "match": r"FATAL EXCEPTION", "line": "FATAL EXCEPTION: main"}]
    )
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "fail"
    assert result["confidence"] == 95
    assert result["feedback_signal"] is not None
    print("[PASS] test_analyze_fatal_path")


def test_analyze_warning_path():
    """正常用例：Exception 异常 → warning 路径"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="no_crash")])
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "Other", "match": r"Exception", "line": "NullPointerException"}]
    )
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "warning"
    assert result["confidence"] == 80
    # warning 不触发 feedback_signal
    assert result.get("feedback_signal") is None
    print("[PASS] test_analyze_warning_path")


def test_analyze_pass_path():
    """正常用例：无异常 + 预期匹配 → pass 路径"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="no_crash", description="不崩溃")])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "pass"
    assert result["confidence"] == 85
    # pass 不触发 feedback_signal
    assert result.get("feedback_signal") is None
    print("[PASS] test_analyze_pass_path")


def test_analyze_manual_path():
    """正常用例：证据不足 → manual 路径"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="manual")])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "manual"
    assert result["confidence"] == 50
    # manual 触发 feedback_signal
    assert result["feedback_signal"] is not None
    # manual 生成 ai_prompt
    assert result["ai_prompt"] is not None
    assert "AI 判定提示词" in result["ai_prompt"]
    print("[PASS] test_analyze_manual_path")


def test_analyze_empty_evidence():
    """边界用例：空证据 → manual"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    result = analyzer.analyze(tc, {})
    assert result["verdict"] == "manual"
    print("[PASS] test_analyze_empty_evidence")


def test_analyze_no_expects():
    """边界用例：无预期 → manual"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[])
    evidence = _make_evidence(logcat_anomalies=[])
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "manual"
    print("[PASS] test_analyze_no_expects")


def test_analyze_fatal_wins_over_warning():
    """边界用例：FATAL + Other 混合 → fail（规则 1 优先）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    evidence = _make_evidence(
        logcat_anomalies=[
            {"type": "FATAL", "match": r"FATAL", "line": "FATAL EXCEPTION"},
            {"type": "Other", "match": r"Exception", "line": "NullPointerException"},
        ]
    )
    result = analyzer.analyze(tc, evidence)
    assert result["verdict"] == "fail"
    assert result["confidence"] == 95
    print("[PASS] test_analyze_fatal_wins_over_warning")


# === 8.6 ai-prompt.md 生成 ===

def test_generate_ai_prompt_content():
    """正常用例：ai-prompt.md 内容正确"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(
        expects=[Expect(expect_type="page_jump", description="跳转到我的页面")],
        steps=[Step(raw="点击我的Tab", action="click", target="desc=我的")],
    )
    evidence = _make_evidence()
    prompt = analyzer._generate_ai_prompt(tc, evidence, "测试原因")
    assert "AI 判定提示词" in prompt
    assert "TC-TEST-01" in prompt
    assert "测试原因" in prompt
    assert "证据摘要" in prompt
    assert "logcat" in prompt
    assert "预期结果" in prompt
    assert "page_jump" in prompt
    assert "测试步骤" in prompt
    assert "点击我的Tab" in prompt
    print("[PASS] test_generate_ai_prompt_content")


def test_generate_ai_prompt_no_expects():
    """边界用例：无预期时 ai-prompt 仍生成"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[])
    evidence = _make_evidence()
    prompt = analyzer._generate_ai_prompt(tc, evidence, "无预期")
    assert "（无明确预期）" in prompt
    print("[PASS] test_generate_ai_prompt_no_expects")


# === 8.8 V3 反馈信号 ===

def test_emit_feedback_signal_fail():
    """正常用例：fail → feedback_signal"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "FATAL", "match": "", "line": "FATAL EXCEPTION"}]
    )
    signal = analyzer._emit_feedback_signal("fail", tc, evidence)
    assert signal is not None
    assert signal["tc_id"] == "TC-TEST-01"
    assert signal["verdict"] == "fail"
    assert "failure_pattern" in signal
    assert "suggested_rule" in signal
    assert "suggested_prompt" in signal
    assert "FATAL" in signal["failure_pattern"]
    print("[PASS] test_emit_feedback_signal_fail")


def test_emit_feedback_signal_manual():
    """正常用例：manual → feedback_signal"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[Expect(expect_type="manual")])
    evidence = _make_evidence(logcat_anomalies=[])
    signal = analyzer._emit_feedback_signal("manual", tc, evidence)
    assert signal is not None
    assert signal["verdict"] == "manual"
    print("[PASS] test_emit_feedback_signal_manual")


def test_emit_feedback_signal_pass():
    """边界用例：pass → None（不触发）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    signal = analyzer._emit_feedback_signal("pass", tc, {})
    assert signal is None
    print("[PASS] test_emit_feedback_signal_pass")


def test_emit_feedback_signal_warning():
    """边界用例：warning → None（不触发）"""
    analyzer = RuleAnalyzer()
    tc = _make_tc()
    signal = analyzer._emit_feedback_signal("warning", tc, {})
    assert signal is None
    print("[PASS] test_emit_feedback_signal_warning")


def test_extract_failure_pattern_with_anomaly():
    """正常用例：从异常提取 failure_pattern"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[
            {"type": "FATAL", "match": "", "line": ""},
            {"type": "Other", "match": "", "line": ""},
        ]
    )
    pattern = analyzer._extract_failure_pattern(evidence)
    assert "FATAL" in pattern
    assert "Other" in pattern
    print(f"[PASS] test_extract_failure_pattern_with_anomaly (pattern={pattern})")


def test_extract_failure_pattern_no_anomaly():
    """边界用例：无异常时 failure_pattern 为 no_anomaly_but_manual"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(logcat_anomalies=[])
    pattern = analyzer._extract_failure_pattern(evidence)
    assert pattern == "no_anomaly_but_manual"
    print("[PASS] test_extract_failure_pattern_no_anomaly")


def test_suggest_rule_with_anomaly():
    """正常用例：有异常时建议扩展 CRASH_PATTERNS"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(
        logcat_anomalies=[{"type": "FATAL", "match": "", "line": ""}]
    )
    tc = _make_tc()
    suggestion = analyzer._suggest_rule(evidence, tc)
    assert "CRASH_PATTERNS" in suggestion
    print("[PASS] test_suggest_rule_with_anomaly")


def test_suggest_rule_with_degraded():
    """正常用例：有降级时建议改进证据收集"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence(logcat_anomalies=[])
    evidence["db_state"]["collected"] = False
    evidence["db_state"]["degraded"] = True
    tc = _make_tc()
    suggestion = analyzer._suggest_rule(evidence, tc)
    assert "db_state" in suggestion
    print("[PASS] test_suggest_rule_with_degraded")


def test_suggest_prompt_manual_expects():
    """正常用例：有 manual 预期时建议细化"""
    analyzer = RuleAnalyzer()
    tc = _make_tc(expects=[
        Expect(expect_type="manual"),
        Expect(expect_type="manual"),
    ])
    evidence = _make_evidence()
    suggestion = analyzer._suggest_prompt(tc, evidence)
    assert "manual" in suggestion
    assert "2" in suggestion  # 2 个 manual 预期
    print("[PASS] test_suggest_prompt_manual_expects")


# === 置信度强制规则 ===

def test_confidence_force_manual():
    """边界用例：置信度 < 70 强制 manual"""
    analyzer = RuleAnalyzer()
    # 构造一个 confidence < 70 的 result（模拟）
    result = {"verdict": "warning", "confidence": 60, "reason": "test"}
    tc = _make_tc()
    evidence = _make_evidence()
    forced = analyzer._apply_confidence_rule(result, tc, evidence)
    assert forced["verdict"] == "manual"
    assert forced["original_verdict"] == "warning"
    assert forced["original_confidence"] == 60
    assert forced["ai_prompt"] is not None
    print("[PASS] test_confidence_force_manual")


def test_confidence_no_force():
    """边界用例：置信度 >= 70 不强制"""
    analyzer = RuleAnalyzer()
    result = {"verdict": "pass", "confidence": 85, "reason": "test"}
    tc = _make_tc()
    evidence = _make_evidence()
    not_forced = analyzer._apply_confidence_rule(result, tc, evidence)
    assert not_forced["verdict"] == "pass"
    assert not_forced["confidence"] == 85
    print("[PASS] test_confidence_no_force")


# === _summarize_evidence ===

def test_summarize_evidence():
    """正常用例：证据摘要生成"""
    analyzer = RuleAnalyzer()
    evidence = _make_evidence()
    evidence["db_state"]["collected"] = False
    evidence["db_state"]["degraded"] = True
    evidence["db_state"]["degradation_reason"] = "run_at_unavailable"
    summary = analyzer._summarize_evidence(evidence)
    assert summary["logcat"] == "collected"
    assert "degraded" in summary["db_state"]
    assert "run_at_unavailable" in summary["db_state"]
    print("[PASS] test_summarize_evidence")


# === analyze 准确率验证（任务 8.9 要求 ≥ 90%）===

def test_analyze_accuracy():
    """综合验证：4 种 verdict 路径准确率 ≥ 90%

    构造 10 个场景，验证 verdict 正确性。
    """
    analyzer = RuleAnalyzer()
    scenarios = [
        # (name, expects, anomalies, expected_verdict)
        ("FATAL 崩溃", [Expect(expect_type="no_crash")], [{"type": "FATAL", "match": "", "line": ""}], "fail"),
        ("ANR 无响应", [Expect(expect_type="no_crash")], [{"type": "ANR", "match": "", "line": ""}], "fail"),
        ("Exception 警告", [Expect(expect_type="no_crash")], [{"type": "Other", "match": "", "line": ""}], "warning"),
        ("OOM 警告", [Expect(expect_type="no_crash")], [{"type": "OOM", "match": "", "line": ""}], "warning"),
        ("无异常 pass", [Expect(expect_type="no_crash")], [], "pass"),
        ("page_jump pass", [Expect(expect_type="page_jump")], [], "pass"),
        ("manual 预期", [Expect(expect_type="manual")], [], "manual"),
        ("无预期", [], [], "manual"),
        ("混合 fatal+other", [Expect(expect_type="no_crash")], [{"type": "FATAL", "match": "", "line": ""}, {"type": "Other", "match": "", "line": ""}], "fail"),
        ("全部预期匹配", [Expect(expect_type="no_crash"), Expect(expect_type="page_jump"), Expect(expect_type="element_visible")], [], "pass"),
    ]
    correct = 0
    total = len(scenarios)
    for name, expects, anomalies, expected in scenarios:
        tc = _make_tc(expects=expects)
        evidence = _make_evidence(logcat_anomalies=anomalies)
        result = analyzer.analyze(tc, evidence)
        if result["verdict"] == expected:
            correct += 1
        else:
            print(f"  [MISMATCH] {name}: expected={expected}, got={result['verdict']}")
    accuracy = correct / total * 100
    assert accuracy >= 90, f"准确率 {accuracy}% < 90%"
    print(f"[PASS] test_analyze_accuracy (准确率 {accuracy}%，{correct}/{total})")


# === 主入口 ===

if __name__ == "__main__":
    test_rule_analyzer_instantiation()
    test_rule_fatal_crash_fatal()
    test_rule_fatal_crash_anr()
    test_rule_fatal_crash_no_anomaly()
    test_rule_fatal_crash_only_warning()
    test_rule_exception_warning_other()
    test_rule_exception_warning_oom()
    test_rule_exception_warning_no_anomaly()
    test_rule_pass_with_evidence_success()
    test_rule_pass_with_evidence_has_anomaly()
    test_rule_pass_with_evidence_manual_expect()
    test_rule_pass_with_evidence_no_expects()
    test_rule_pass_with_evidence_degraded_ok()
    test_check_expect_match_all_types()
    test_check_expect_match_no_crash_with_anomaly()
    test_rule_manual_insufficient()
    test_analyze_fatal_path()
    test_analyze_warning_path()
    test_analyze_pass_path()
    test_analyze_manual_path()
    test_analyze_empty_evidence()
    test_analyze_no_expects()
    test_analyze_fatal_wins_over_warning()
    test_generate_ai_prompt_content()
    test_generate_ai_prompt_no_expects()
    test_emit_feedback_signal_fail()
    test_emit_feedback_signal_manual()
    test_emit_feedback_signal_pass()
    test_emit_feedback_signal_warning()
    test_extract_failure_pattern_with_anomaly()
    test_extract_failure_pattern_no_anomaly()
    test_suggest_rule_with_anomaly()
    test_suggest_rule_with_degraded()
    test_suggest_prompt_manual_expects()
    test_confidence_force_manual()
    test_confidence_no_force()
    test_summarize_evidence()
    test_analyze_accuracy()
    print("\n" + "=" * 60)
    print("全部 38 个测试通过 ✅")
    print("=" * 60)
