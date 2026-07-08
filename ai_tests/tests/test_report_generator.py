"""ai_tests/tests/test_report_generator.py — M7 报告生成器单元测试

任务 9.9 验证：五件套渲染正确（report.md + report.json + manual_cases.md +
affected_modules.json + feedback_suggestions.md）

覆盖范围：
- 类骨架（1）
- _calc_summary（4：空/全 pass/混合/缺失 verdict）
- generate_markdown（3：基本/空/含 affected+feedback）
- generate_json（3：基本/evidence_collected/ai_prompt_path+track_source）
- generate_manual_cases（3：有 manual/无 manual/含 feedback_signal）
- generate_affected_modules（2：基本/空）
- generate_feedback_suggestions（2：含 3 类建议/空）
- generate_summary（2：基本/创建 case 目录）
- generate_all（2：五件套完整/无可选件）

运行：
    python ai_tests/tests/test_report_generator.py
"""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.report_generator import ReportGenerator


# === 工厂函数 ===

def _make_result(
    tc_id: str = "TC-TEST-01",
    title: str = "测试用例",
    module: str = "F-P0-1",
    verdict: str = "pass",
    confidence: int = 85,
    reason: str = "规则匹配通过",
    evidence: dict = None,
    ai_prompt_path: str = None,
    track_source: str = "md",
    feedback_signal: dict = None,
) -> dict:
    """构造单个测试结果"""
    return {
        "tc_id": tc_id,
        "title": title,
        "module": module,
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence or {
            "logcat": {"collected": True, "degraded": False, "anomalies": []},
            "ui_xml": {"collected": True, "degraded": False, "count": 2},
            "screenshot": {"collected": True, "degraded": False, "count": 2},
            "activity_stack": {"collected": True, "degraded": False},
            "db_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
            "prefs_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
            "web_api": {"collected": False, "degraded": True, "error": "web_api_unavailable"},
            "meminfo": {"collected": True, "degraded": False},
        },
        "ai_prompt_path": ai_prompt_path,
        "track_source": track_source,
        "feedback_signal": feedback_signal,
    }


def _make_results_mixed() -> list:
    """构造混合结果（pass/fail/manual 各一）"""
    return [
        _make_result(
            tc_id="TC-F-P0-1-01",
            title="进入我的页面",
            verdict="pass",
            confidence=85,
            reason="规则 3 匹配：no_crash + element_visible",
            track_source="md",
        ),
        _make_result(
            tc_id="TC-F-P0-2-01",
            title="书源管理崩溃测试",
            verdict="fail",
            confidence=95,
            reason="规则 1 匹配：FATAL EXCEPTION",
            track_source="md",
            feedback_signal={
                "tc_id": "TC-F-P0-2-01",
                "verdict": "fail",
                "failure_pattern": "FATAL|NullPointerException",
                "suggested_rule": "新增规则：BookSourceActivity NPE",
                "suggested_prompt": "增加书源管理 Activity 跳转断言",
            },
        ),
        _make_result(
            tc_id="TC-F-P0-3-01",
            title="封面画廊手动判定",
            verdict="manual",
            confidence=50,
            reason="证据不足，需 AI agent 介入",
            track_source="python",
            ai_prompt_path="reports/r1/manual_cases/TC-F-P0-3-01_ai-prompt.md",
            feedback_signal={
                "tc_id": "TC-F-P0-3-01",
                "verdict": "manual",
                "failure_pattern": "insufficient_evidence",
                "suggested_rule": "补充 db_state 查询 cover_gallery_groups",
                "suggested_prompt": "增加封面画廊数据库状态断言",
            },
        ),
    ]


def _make_affected_modules() -> dict:
    """构造受影响模块数据"""
    return {
        "changed_files": ["app/src/main/java/io/legado/app/ui/MainActivity.kt"],
        "affected_activities": ["MainActivity", "BookshelfActivity"],
        "related_tc_ids": ["TC-F-P0-1-01", "TC-F-P0-2-01"],
        "recommended_rerun": ["TC-F-P0-1-01", "TC-F-P0-2-01"],
    }


def _make_feedback_signals() -> list:
    """构造反馈信号列表"""
    return [
        {
            "tc_id": "TC-F-P0-2-01",
            "verdict": "fail",
            "failure_pattern": "FATAL|NullPointerException",
            "suggested_rule": "新增规则：BookSourceActivity NPE",
            "suggested_prompt": "增加书源管理 Activity 跳转断言",
        },
        {
            "tc_id": "TC-F-P0-3-01",
            "verdict": "manual",
            "failure_pattern": "insufficient_evidence",
            "suggested_rule": "补充 db_state 查询 cover_gallery_groups",
            "suggested_prompt": "增加封面画廊数据库状态断言",
        },
    ]


# === 9.1 类骨架 ===

def test_report_generator_instantiation():
    """正常用例：ReportGenerator 可实例化，report_dir 自动创建"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "test_report")
        assert rg.report_dir.exists()
        assert (Path(tmp) / "test_report").exists()
    print("[PASS] test_report_generator_instantiation")


# === _calc_summary ===

def test_calc_summary_empty():
    """边界用例：空 results → total=0, pass_rate=0"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        summary = rg._calc_summary([])
        assert summary["total"] == 0
        assert summary["pass"] == 0
        assert summary["fail"] == 0
        assert summary["warning"] == 0
        assert summary["manual"] == 0
        assert summary["pass_rate"] == 0
    print("[PASS] test_calc_summary_empty")


def test_calc_summary_all_pass():
    """正常用例：全 pass → pass_rate=100"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(tc_id="TC-01", verdict="pass"),
            _make_result(tc_id="TC-02", verdict="pass"),
        ]
        summary = rg._calc_summary(results)
        assert summary["total"] == 2
        assert summary["pass"] == 2
        assert summary["pass_rate"] == 100.0
    print("[PASS] test_calc_summary_all_pass")


def test_calc_summary_mixed():
    """正常用例：混合 verdict"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(tc_id="TC-01", verdict="pass"),
            _make_result(tc_id="TC-02", verdict="fail"),
            _make_result(tc_id="TC-03", verdict="warning"),
            _make_result(tc_id="TC-04", verdict="manual"),
        ]
        summary = rg._calc_summary(results)
        assert summary["total"] == 4
        assert summary["pass"] == 1
        assert summary["fail"] == 1
        assert summary["warning"] == 1
        assert summary["manual"] == 1
        assert summary["pass_rate"] == 25.0
    print("[PASS] test_calc_summary_mixed")


def test_calc_summary_missing_verdict():
    """异常用例：缺失 verdict 字段 → 默认 manual"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [{"tc_id": "TC-01", "title": "无 verdict"}]
        summary = rg._calc_summary(results)
        assert summary["manual"] == 1
        assert summary["pass"] == 0
    print("[PASS] test_calc_summary_missing_verdict")


# === generate_markdown ===

def test_generate_markdown_basic():
    """正常用例：生成 report.md 文件"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        env = {"device": "MEmu", "timestamp": "2026-07-08T10:00:00", "instance_id": 0}
        apk_info = {"name": "app-debug.apk", "size": "50MB"}
        content = rg.generate_markdown(results, env, apk_info)
        # 验证文件生成
        assert (rg.report_dir / "report.md").exists()
        # 验证内容包含关键节
        assert "# Legado E2E 测试报告" in content
        assert "## 执行环境" in content
        assert "## 汇总统计" in content
        assert "TC-F-P0-1-01" in content
        assert "TC-F-P0-2-01" in content
        # 验证失败用例置顶
        assert content.index("❌ 失败用例") < content.index("📋 全部用例")
        # 验证 manual 用例置顶
        assert content.index("🤖 Manual 用例") < content.index("📋 全部用例")
    print("[PASS] test_generate_markdown_basic")


def test_generate_markdown_empty():
    """边界用例：空 results → 不报错，生成空报告"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        content = rg.generate_markdown([], {}, {})
        assert "# Legado E2E 测试报告" in content
        assert (rg.report_dir / "report.md").exists()
    print("[PASS] test_generate_markdown_empty")


def test_generate_markdown_with_affected_feedback():
    """正常用例：含 affected_modules + feedback_signals 节"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        affected = _make_affected_modules()
        feedback = _make_feedback_signals()
        content = rg.generate_markdown(
            results, {"device": "MEmu"}, {"name": "app.apk"},
            affected_modules=affected, feedback_signals=feedback,
        )
        # 验证 V3 节存在
        assert "🔍 V3 受影响模块" in content
        assert "💡 V3 反馈建议" in content
        assert "MainActivity" in content
        assert "FATAL|NullPointerException" in content
    print("[PASS] test_generate_markdown_with_affected_feedback")


# === generate_json ===

def test_generate_json_basic():
    """正常用例：生成 report.json 文件"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        report = rg.generate_json(results, {"device": "MEmu"}, {"name": "app.apk"})
        # 验证文件生成
        assert (rg.report_dir / "report.json").exists()
        # 验证结构
        assert "env" in report
        assert "apk_info" in report
        assert "summary" in report
        assert "cases" in report
        assert len(report["cases"]) == 3
        assert report["summary"]["total"] == 3
    print("[PASS] test_generate_json_basic")


def test_generate_json_evidence_collected():
    """正常用例：evidence_collected 字段正确提取"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [_make_result()]
        report = rg.generate_json(results, {}, {})
        case = report["cases"][0]
        assert "evidence_collected" in case
        # 验证从 evidence 提取 collected 字段
        assert case["evidence_collected"]["logcat"] is True
        assert case["evidence_collected"]["db_state"] is False
    print("[PASS] test_generate_json_evidence_collected")


def test_generate_json_ai_prompt_path_track_source():
    """正常用例：ai_prompt_path + track_source + feedback_signal 字段"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(
                tc_id="TC-MANUAL-01",
                verdict="manual",
                ai_prompt_path="/path/to/ai-prompt.md",
                track_source="python",
                feedback_signal={"tc_id": "TC-MANUAL-01", "failure_pattern": "test"},
            )
        ]
        report = rg.generate_json(results, {}, {})
        case = report["cases"][0]
        assert case["ai_prompt_path"] == "/path/to/ai-prompt.md"
        assert case["track_source"] == "python"
        assert case["feedback_signal"]["failure_pattern"] == "test"
    print("[PASS] test_generate_json_ai_prompt_path_track_source")


# === generate_manual_cases ===

def test_generate_manual_cases_with_manual():
    """正常用例：有 manual 用例 → 生成清单"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        content = rg.generate_manual_cases(results)
        assert (rg.report_dir / "manual_cases.md").exists()
        assert "# Manual 用例清单" in content
        assert "## AI agent 接入流程" in content
        assert "TC-F-P0-3-01" in content
        assert "证据不足" in content
        # 验证 manual 数量标注
        assert "共 1 个" in content
    print("[PASS] test_generate_manual_cases_with_manual")


def test_generate_manual_cases_without_manual():
    """边界用例：无 manual 用例 → 显示"无 manual 用例" """
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(tc_id="TC-01", verdict="pass"),
            _make_result(tc_id="TC-02", verdict="fail"),
        ]
        content = rg.generate_manual_cases(results)
        assert "无 manual 用例" in content
        assert "共 0 个" in content
    print("[PASS] test_generate_manual_cases_without_manual")


def test_generate_manual_cases_with_feedback_signal():
    """正常用例：manual 含 feedback_signal → 显示失败模式"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(
                tc_id="TC-FAIL-01",
                verdict="manual",
                feedback_signal={
                    "failure_pattern": "insufficient_evidence",
                    "suggested_rule": "补充规则",
                },
            )
        ]
        content = rg.generate_manual_cases(results)
        assert "insufficient_evidence" in content
        assert "补充规则" in content
    print("[PASS] test_generate_manual_cases_with_feedback_signal")


# === generate_affected_modules ===

def test_generate_affected_modules_basic():
    """正常用例：生成 affected_modules.json，返回 JSON 字符串内容"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        affected = _make_affected_modules()
        result = rg.generate_affected_modules(affected)
        assert (rg.report_dir / "affected_modules.json").exists()
        # 验证返回值是 JSON 字符串内容（非文件路径）
        assert isinstance(result, str)
        loaded_from_return = json.loads(result)
        # 验证文件内容可解析为 JSON
        loaded = json.loads((rg.report_dir / "affected_modules.json").read_text(encoding="utf-8"))
        assert loaded["changed_files"] == affected["changed_files"]
        assert "MainActivity" in loaded["affected_activities"]
        # 返回值与文件内容一致
        assert loaded_from_return == loaded
    print("[PASS] test_generate_affected_modules_basic")


def test_generate_affected_modules_empty():
    """边界用例：空 dict"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        rg.generate_affected_modules({})
        assert (rg.report_dir / "affected_modules.json").exists()
    print("[PASS] test_generate_affected_modules_empty")


# === generate_feedback_suggestions ===

def test_generate_feedback_suggestions_basic():
    """正常用例：含 3 类建议"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        signals = _make_feedback_signals()
        content = rg.generate_feedback_suggestions(signals)
        assert (rg.report_dir / "feedback_suggestions.md").exists()
        assert "## 规则建议" in content
        assert "## 提示词建议" in content
        assert "## 陷阱库建议" in content
        assert "BookSourceActivity NPE" in content
        assert "增加书源管理 Activity 跳转断言" in content
        assert "FATAL|NullPointerException" in content
    print("[PASS] test_generate_feedback_suggestions_basic")


def test_generate_feedback_suggestions_empty():
    """边界用例：空 list → 显示"（无）" """
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        content = rg.generate_feedback_suggestions([])
        assert "共 0 条反馈信号" in content
        assert "（无）" in content
    print("[PASS] test_generate_feedback_suggestions_empty")


# === generate_summary ===

def test_generate_summary_basic():
    """正常用例：生成汇总统计文本"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        content = rg.generate_summary(results)
        assert "## 汇总统计" in content
        assert "总用例数: 3" in content
        assert "pass: 1" in content
        assert "fail: 1" in content
        assert "manual: 1" in content
    print("[PASS] test_generate_summary_basic")


def test_generate_summary_creates_case_dirs():
    """正常用例：创建 cases/{tc_id}/ 目录"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        rg.generate_summary(results)
        cases_dir = rg.report_dir / "cases"
        assert cases_dir.exists()
        assert (cases_dir / "TC-F-P0-1-01").exists()
        assert (cases_dir / "TC-F-P0-2-01").exists()
        assert (cases_dir / "TC-F-P0-3-01").exists()
    print("[PASS] test_generate_summary_creates_case_dirs")


# === generate_all ===

def test_generate_all_seven_pieces():
    """正常用例：七件套完整生成（含 affected + feedback 双版本 + summary.txt）"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        affected = _make_affected_modules()
        feedback = _make_feedback_signals()
        output = rg.generate_all(
            results,
            env={"device": "MEmu", "timestamp": "2026-07-08"},
            apk_info={"name": "app-debug.apk", "size": "50MB"},
            affected_modules=affected,
            feedback_signals=feedback,
        )
        # 验证七件套全部生成
        assert "markdown" in output
        assert "json" in output
        assert "manual_cases" in output
        assert "summary" in output
        assert "affected_modules" in output
        assert "feedback_suggestions" in output
        assert "feedback_suggestions_json" in output
        # 验证文件存在
        assert (rg.report_dir / "report.md").exists()
        assert (rg.report_dir / "report.json").exists()
        assert (rg.report_dir / "manual_cases.md").exists()
        assert (rg.report_dir / "summary.txt").exists()
        assert (rg.report_dir / "affected_modules.json").exists()
        assert (rg.report_dir / "feedback_suggestions.md").exists()
        assert (rg.report_dir / "feedback_suggestions.json").exists()
        # 验证 summary.txt 是一行摘要
        summary_content = (rg.report_dir / "summary.txt").read_text(encoding="utf-8")
        assert "pass:" in summary_content
        assert "fail:" in summary_content
        assert "pass_rate:" in summary_content
        assert len(summary_content.strip().splitlines()) == 1
        # 验证 JSON 可解析
        json.loads((rg.report_dir / "report.json").read_text(encoding="utf-8"))
        json.loads((rg.report_dir / "affected_modules.json").read_text(encoding="utf-8"))
        json.loads((rg.report_dir / "feedback_suggestions.json").read_text(encoding="utf-8"))
    print("[PASS] test_generate_all_seven_pieces")


def test_generate_all_without_optional():
    """边界用例：无 affected + feedback → 生成 4 件套（md/json/manual + summary.txt）"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        output = rg.generate_all(results)
        assert "markdown" in output
        assert "json" in output
        assert "manual_cases" in output
        assert "summary" in output  # summary.txt 始终生成
        assert "affected_modules" not in output
        assert "feedback_suggestions" not in output
        assert "feedback_suggestions_json" not in output
        # 验证文件存在/不存在
        assert (rg.report_dir / "summary.txt").exists()
        assert not (rg.report_dir / "affected_modules.json").exists()
        assert not (rg.report_dir / "feedback_suggestions.md").exists()
        assert not (rg.report_dir / "feedback_suggestions.json").exists()
    print("[PASS] test_generate_all_without_optional")


def test_generate_all_with_none_env():
    """边界用例：传 None env/apk_info → 使用默认值"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        output = rg.generate_all(results)  # env=None, apk_info=None
        # 验证默认值生效，不报错
        report_json = json.loads((rg.report_dir / "report.json").read_text(encoding="utf-8"))
        assert report_json["env"]["device"] == "MEmu"
        assert report_json["apk_info"]["name"] == "N/A"
        assert "timestamp" in report_json["env"]
    print("[PASS] test_generate_all_with_none_env")


def test_generate_json_evidence_non_dict():
    """异常用例：evidence 中 value 为 None 时不抛 AttributeError"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = [
            _make_result(
                tc_id="TC-BAD-EV-01",
                evidence={
                    "logcat": {"collected": True, "degraded": False},
                    "db_state": None,  # 非 dict
                    "web_api": "unavailable",  # 非 dict
                },
            )
        ]
        # 不应抛异常
        report = rg.generate_json(results, {}, {})
        case = report["cases"][0]
        assert case["evidence_collected"]["logcat"] is True
        assert case["evidence_collected"]["db_state"] is False
        assert case["evidence_collected"]["web_api"] is False
    print("[PASS] test_generate_json_evidence_non_dict")


def test_generate_feedback_suggestions_json_basic():
    """正常用例：生成 feedback_suggestions.json（机器读）"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        signals = _make_feedback_signals()
        result = rg.generate_feedback_suggestions_json(signals)
        assert (rg.report_dir / "feedback_suggestions.json").exists()
        # 验证返回值是 JSON 字符串
        assert isinstance(result, str)
        loaded = json.loads(result)
        assert len(loaded) == 2
        assert loaded[0]["tc_id"] == "TC-F-P0-2-01"
        # 验证文件内容一致
        file_loaded = json.loads((rg.report_dir / "feedback_suggestions.json").read_text(encoding="utf-8"))
        assert file_loaded == loaded
    print("[PASS] test_generate_feedback_suggestions_json_basic")


def test_generate_summary_creates_summary_txt():
    """正常用例：生成 summary.txt（一行摘要）"""
    with TemporaryDirectory() as tmp:
        rg = ReportGenerator(report_dir=Path(tmp) / "r1")
        results = _make_results_mixed()
        rg.generate_summary(results)
        summary_path = rg.report_dir / "summary.txt"
        assert summary_path.exists()
        content = summary_path.read_text(encoding="utf-8")
        # 验证是一行摘要
        assert "pass:1/3" in content
        assert "fail:1" in content
        assert "manual:1" in content
        assert "pass_rate:33.3%" in content
        assert len(content.strip().splitlines()) == 1
    print("[PASS] test_generate_summary_creates_summary_txt")


# === 主入口 ===

if __name__ == "__main__":
    print("=" * 60)
    print("M7 ReportGenerator 单元测试")
    print("=" * 60)
    print()

    test_report_generator_instantiation()
    test_calc_summary_empty()
    test_calc_summary_all_pass()
    test_calc_summary_mixed()
    test_calc_summary_missing_verdict()
    test_generate_markdown_basic()
    test_generate_markdown_empty()
    test_generate_markdown_with_affected_feedback()
    test_generate_json_basic()
    test_generate_json_evidence_collected()
    test_generate_json_ai_prompt_path_track_source()
    test_generate_json_evidence_non_dict()
    test_generate_manual_cases_with_manual()
    test_generate_manual_cases_without_manual()
    test_generate_manual_cases_with_feedback_signal()
    test_generate_affected_modules_basic()
    test_generate_affected_modules_empty()
    test_generate_feedback_suggestions_basic()
    test_generate_feedback_suggestions_empty()
    test_generate_feedback_suggestions_json_basic()
    test_generate_summary_basic()
    test_generate_summary_creates_case_dirs()
    test_generate_summary_creates_summary_txt()
    test_generate_all_seven_pieces()
    test_generate_all_without_optional()
    test_generate_all_with_none_env()

    print()
    print("=" * 60)
    print(f"总计 26 个测试全部 PASS")
    print("=" * 60)
