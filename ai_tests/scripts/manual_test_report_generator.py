"""ai_tests/scripts/manual_test_report_generator.py — M7 实测验证脚本

任务 9.9 实测验证：mock 一组结果数据（含 pass/fail/manual 各一 + V3 含 affected + feedback）
→ 验证五件套渲染正确（report.md + report.json + manual_cases.md +
   affected_modules.json + feedback_suggestions.md）

运行：
    python ai_tests/scripts/manual_test_report_generator.py
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.report_generator import ReportGenerator


def make_mock_results() -> list:
    """构造 mock 结果数据（pass/fail/manual 各一）"""
    return [
        # 1. pass 用例
        {
            "tc_id": "TC-F-P0-1-01",
            "title": "进入我的页面",
            "module": "F-P0-1",
            "case_type": "正常用例",
            "verdict": "pass",
            "confidence": 85,
            "reason": "规则 3 匹配：no_crash + element_visible",
            "evidence": {
                "logcat": {"collected": True, "degraded": False, "anomalies": [], "anomaly_count": 0},
                "ui_xml": {"collected": True, "degraded": False, "count": 3, "files": ["step-01.xml", "step-02.xml", "step-03.xml"]},
                "screenshot": {"collected": True, "degraded": False, "count": 3, "files": ["step-01.png", "step-02.png", "step-03.png"]},
                "activity_stack": {"collected": True, "degraded": False, "path": "activity-stack.txt"},
                "db_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "prefs_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "web_api": {"collected": False, "degraded": True, "error": "web_api_unavailable"},
                "meminfo": {"collected": True, "degraded": False, "path": "meminfo.txt"},
            },
            "ai_prompt_path": None,
            "track_source": "md",
            "feedback_signal": None,
        },
        # 2. fail 用例
        {
            "tc_id": "TC-F-P0-2-01",
            "title": "书源管理崩溃测试",
            "module": "F-P0-2",
            "case_type": "异常用例",
            "verdict": "fail",
            "confidence": 95,
            "reason": "规则 1 匹配：FATAL EXCEPTION: NullPointerException",
            "evidence": {
                "logcat": {
                    "collected": True,
                    "degraded": False,
                    "anomalies": [
                        {"type": "FATAL", "line": "FATAL EXCEPTION: NullPointerException", "count": 1},
                        {"type": "Other", "line": "java.lang.NullPointerException", "count": 2},
                    ],
                    "anomaly_count": 2,
                },
                "ui_xml": {"collected": True, "degraded": False, "count": 1, "files": ["step-01.xml"]},
                "screenshot": {"collected": True, "degraded": False, "count": 1, "files": ["step-01.png"]},
                "activity_stack": {"collected": True, "degraded": False, "path": "activity-stack.txt"},
                "db_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "prefs_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "web_api": {"collected": False, "degraded": True, "error": "web_api_unavailable"},
                "meminfo": {"collected": True, "degraded": False, "path": "meminfo.txt"},
            },
            "ai_prompt_path": None,
            "track_source": "md",
            "feedback_signal": {
                "tc_id": "TC-F-P0-2-01",
                "verdict": "fail",
                "failure_pattern": "FATAL|NullPointerException",
                "suggested_rule": "新增规则：BookSourceActivity 加载时 NPE → fail",
                "suggested_prompt": "增加书源管理 Activity 跳转断言 + 空数据保护",
            },
        },
        # 3. manual 用例
        {
            "tc_id": "TC-F-P0-3-01",
            "title": "封面画廊手动判定",
            "module": "F-P0-3",
            "case_type": "正常用例",
            "verdict": "manual",
            "confidence": 50,
            "reason": "证据不足：db_state 降级（run_at_unavailable），无法验证封面画廊数据",
            "evidence": {
                "logcat": {"collected": True, "degraded": False, "anomalies": [], "anomaly_count": 0},
                "ui_xml": {"collected": True, "degraded": False, "count": 2, "files": ["step-01.xml", "step-02.xml"]},
                "screenshot": {"collected": True, "degraded": False, "count": 2, "files": ["step-01.png", "step-02.png"]},
                "activity_stack": {"collected": True, "degraded": False, "path": "activity-stack.txt"},
                "db_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "prefs_state": {"collected": False, "degraded": True, "error": "run_at_unavailable"},
                "web_api": {"collected": False, "degraded": True, "error": "web_api_unavailable"},
                "meminfo": {"collected": True, "degraded": False, "path": "meminfo.txt"},
            },
            "ai_prompt_path": "reports/manual_cases/TC-F-P0-3-01_ai-prompt.md",
            "track_source": "python",
            "feedback_signal": {
                "tc_id": "TC-F-P0-3-01",
                "verdict": "manual",
                "failure_pattern": "insufficient_evidence",
                "suggested_rule": "补充 db_state 查询 cover_gallery_groups 表",
                "suggested_prompt": "增加封面画廊数据库状态断言 + 空数据保护",
            },
        },
    ]


def make_mock_affected_modules() -> dict:
    """构造 mock 受影响模块数据"""
    return {
        "git_ref": "HEAD~1",
        "changed_files": [
            "app/src/main/java/io/legado/app/ui/MainActivity.kt",
            "app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt",
        ],
        "affected_activities": ["MainActivity", "BookshelfActivity", "BookSourceActivity"],
        "related_tc_ids": ["TC-F-P0-1-01", "TC-F-P0-2-01"],
        "recommended_rerun": ["TC-F-P0-1-01", "TC-F-P0-2-01"],
    }


def make_mock_feedback_signals() -> list:
    """构造 mock 反馈信号列表"""
    return [
        {
            "tc_id": "TC-F-P0-2-01",
            "verdict": "fail",
            "failure_pattern": "FATAL|NullPointerException",
            "suggested_rule": "新增规则：BookSourceActivity 加载时 NPE → fail",
            "suggested_prompt": "增加书源管理 Activity 跳转断言 + 空数据保护",
        },
        {
            "tc_id": "TC-F-P0-3-01",
            "verdict": "manual",
            "failure_pattern": "insufficient_evidence",
            "suggested_rule": "补充 db_state 查询 cover_gallery_groups 表",
            "suggested_prompt": "增加封面画廊数据库状态断言 + 空数据保护",
        },
    ]


def main():
    print("=" * 70)
    print("M7 ReportGenerator 实测验证（任务 9.9）")
    print("=" * 70)
    print()

    # 准备 mock 数据
    results = make_mock_results()
    affected = make_mock_affected_modules()
    feedback = make_mock_feedback_signals()
    env = {
        "device": "MEmu",
        "timestamp": datetime.now().isoformat(),
        "instance_id": 0,
        "adb_serial": "127.0.0.1:21503",
    }
    apk_info = {
        "name": "app-debug.apk",
        "size": "50.2MB",
        "path": "app/build/outputs/apk/app/debug/app-debug.apk",
        "build_type": "debug",
    }

    print(f"[1] Mock 数据准备完成：")
    print(f"    - 用例数: {len(results)}（pass={sum(1 for r in results if r['verdict']=='pass')}, "
          f"fail={sum(1 for r in results if r['verdict']=='fail')}, "
          f"manual={sum(1 for r in results if r['verdict']=='manual')})")
    print(f"    - affected_modules: {len(affected['affected_activities'])} Activity")
    print(f"    - feedback_signals: {len(feedback)} 条")
    print()

    # 生成报告
    rg = ReportGenerator()
    print(f"[2] 报告目录: {rg.report_dir}")
    print()

    output = rg.generate_all(
        results,
        env=env,
        apk_info=apk_info,
        affected_modules=affected,
        feedback_signals=feedback,
    )

    # 验证七件套
    print("[3] 七件套验证：")
    print()

    expected_files = {
        "report.md": "markdown",
        "report.json": "json",
        "manual_cases.md": "manual_cases",
        "summary.txt": "summary",
        "affected_modules.json": "affected_modules",
        "feedback_suggestions.md": "feedback_suggestions",
        "feedback_suggestions.json": "feedback_suggestions_json",
    }

    all_pass = True
    for filename, key in expected_files.items():
        file_path = rg.report_dir / filename
        exists = file_path.exists()
        in_output = key in output
        status = "✅" if (exists and in_output) else "❌"
        if not (exists and in_output):
            all_pass = False
        print(f"    {status} {filename} (exists={exists}, in_output={in_output})")

    print()

    # 验证 report.md 内容
    print("[4] report.md 内容验证：")
    report_md = (rg.report_dir / "report.md").read_text(encoding="utf-8")
    md_checks = [
        ("标题", "# Legado E2E 测试报告" in report_md),
        ("执行环境节", "## 执行环境" in report_md),
        ("汇总统计节", "## 汇总统计" in report_md),
        ("失败用例置顶", "❌ 失败用例" in report_md),
        ("Manual 用例置顶", "🤖 Manual 用例" in report_md),
        ("全部用例表", "📋 全部用例" in report_md),
        ("V3 受影响模块节", "🔍 V3 受影响模块" in report_md),
        ("V3 反馈建议节", "💡 V3 反馈建议" in report_md),
        ("pass 用例", "TC-F-P0-1-01" in report_md),
        ("fail 用例", "TC-F-P0-2-01" in report_md),
        ("manual 用例", "TC-F-P0-3-01" in report_md),
        ("失败置顶顺序", report_md.index("❌ 失败用例") < report_md.index("📋 全部用例")),
        ("manual 置顶顺序", report_md.index("🤖 Manual 用例") < report_md.index("📋 全部用例")),
    ]
    for name, ok in md_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 验证 report.json
    print("[5] report.json 验证：")
    report_json = json.loads((rg.report_dir / "report.json").read_text(encoding="utf-8"))
    json_checks = [
        ("env 字段", "env" in report_json),
        ("apk_info 字段", "apk_info" in report_json),
        ("summary 字段", "summary" in report_json),
        ("cases 字段", "cases" in report_json),
        ("generated_at 字段", "generated_at" in report_json),
        ("cases 数量=3", len(report_json["cases"]) == 3),
        ("summary.total=3", report_json["summary"]["total"] == 3),
        ("summary.pass=1", report_json["summary"]["pass"] == 1),
        ("summary.fail=1", report_json["summary"]["fail"] == 1),
        ("summary.manual=1", report_json["summary"]["manual"] == 1),
    ]
    for name, ok in json_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")

    # 验证 cases 的 evidence_collected 字段
    case0 = report_json["cases"][0]
    ev_checks = [
        ("evidence_collected 字段", "evidence_collected" in case0),
        ("logcat collected=True", case0.get("evidence_collected", {}).get("logcat") is True),
        ("db_state collected=False", case0.get("evidence_collected", {}).get("db_state") is False),
        ("ai_prompt_path 字段", "ai_prompt_path" in case0),
        ("track_source 字段", "track_source" in case0),
        ("feedback_signal 字段", "feedback_signal" in case0),
    ]
    for name, ok in ev_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 验证 manual_cases.md
    print("[6] manual_cases.md 验证：")
    manual_md = (rg.report_dir / "manual_cases.md").read_text(encoding="utf-8")
    mc_checks = [
        ("标题", "# Manual 用例清单" in manual_md),
        ("AI agent 接入流程", "## AI agent 接入流程" in manual_md),
        ("manual 用例数量=1", "共 1 个" in manual_md),
        ("manual 用例 TC-ID", "TC-F-P0-3-01" in manual_md),
        ("失败模式", "insufficient_evidence" in manual_md),
        ("规则建议", "补充 db_state" in manual_md),
    ]
    for name, ok in mc_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 验证 affected_modules.json
    print("[7] affected_modules.json 验证：")
    affected_json = json.loads((rg.report_dir / "affected_modules.json").read_text(encoding="utf-8"))
    af_checks = [
        ("changed_files 字段", "changed_files" in affected_json),
        ("affected_activities 字段", "affected_activities" in affected_json),
        ("related_tc_ids 字段", "related_tc_ids" in affected_json),
        ("recommended_rerun 字段", "recommended_rerun" in affected_json),
        ("Activity 数量=3", len(affected_json["affected_activities"]) == 3),
        ("包含 MainActivity", "MainActivity" in affected_json["affected_activities"]),
    ]
    for name, ok in af_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 验证 feedback_suggestions.md
    print("[8] feedback_suggestions.md 验证：")
    feedback_md = (rg.report_dir / "feedback_suggestions.md").read_text(encoding="utf-8")
    fs_checks = [
        ("标题", "# 反馈建议" in feedback_md),
        ("反馈信号数=2", "共 2 条反馈信号" in feedback_md),
        ("规则建议节", "## 规则建议" in feedback_md),
        ("提示词建议节", "## 提示词建议" in feedback_md),
        ("陷阱库建议节", "## 陷阱库建议" in feedback_md),
        ("规则建议内容", "BookSourceActivity" in feedback_md),
        ("陷阱库 pattern", "FATAL|NullPointerException" in feedback_md),
    ]
    for name, ok in fs_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 验证 cases 目录
    print("[9] 证据归档目录验证：")
    cases_dir = rg.report_dir / "cases"
    case_checks = []
    for tc_id in ["TC-F-P0-1-01", "TC-F-P0-2-01", "TC-F-P0-3-01"]:
        ok = (cases_dir / tc_id).exists()
        case_checks.append((f"cases/{tc_id}/", ok))
        if not ok:
            all_pass = False
    for name, ok in case_checks:
        status = "✅" if ok else "❌"
        print(f"    {status} {name}")
    print()

    # 验证 summary.txt（一行摘要）
    print("[10] summary.txt 验证：")
    summary_path = rg.report_dir / "summary.txt"
    summary_exists = summary_path.exists()
    summary_content = summary_path.read_text(encoding="utf-8") if summary_exists else ""
    sum_checks = [
        ("文件存在", summary_exists),
        ("一行摘要", len(summary_content.strip().splitlines()) == 1 if summary_exists else False),
        ("含 pass:", "pass:" in summary_content),
        ("含 fail:", "fail:" in summary_content),
        ("含 manual:", "manual:" in summary_content),
        ("含 pass_rate:", "pass_rate:" in summary_content),
        ("pass=1/3", "pass:1/3" in summary_content),
        ("fail=1", "fail:1" in summary_content),
        ("manual=1", "manual:1" in summary_content),
        ("pass_rate=33.3%", "pass_rate:33.3%" in summary_content),
    ]
    for name, ok in sum_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    if summary_exists:
        print(f"    内容: {summary_content.strip()}")
    print()

    # 验证 feedback_suggestions.json（机器读）
    print("[11] feedback_suggestions.json 验证：")
    fs_json_path = rg.report_dir / "feedback_suggestions.json"
    fs_json_exists = fs_json_path.exists()
    fs_json = json.loads(fs_json_path.read_text(encoding="utf-8")) if fs_json_exists else []
    fsj_checks = [
        ("文件存在", fs_json_exists),
        ("可解析为 JSON", fs_json_exists),
        ("数量=2", len(fs_json) == 2),
        ("第1条 tc_id", fs_json[0].get("tc_id") == "TC-F-P0-2-01" if len(fs_json) >= 1 else False),
        ("第1条 failure_pattern", fs_json[0].get("failure_pattern") == "FATAL|NullPointerException" if len(fs_json) >= 1 else False),
        ("第2条 tc_id", fs_json[1].get("tc_id") == "TC-F-P0-3-01" if len(fs_json) >= 2 else False),
    ]
    for name, ok in fsj_checks:
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"    {status} {name}")
    print()

    # 汇总
    print("=" * 70)
    if all_pass:
        print("✅ M7 报告生成器实测验证全部通过！")
        print(f"   报告目录: {rg.report_dir}")
        print(f"   七件套: report.md + report.json + manual_cases.md + summary.txt +")
        print(f"          affected_modules.json + feedback_suggestions.md + feedback_suggestions.json")
    else:
        print("❌ M7 报告生成器实测验证存在失败项！")
    print("=" * 70)

    # 打印 report.md 预览
    print()
    print("=" * 70)
    print("report.md 预览（前 50 行）：")
    print("=" * 70)
    for i, line in enumerate(report_md.splitlines()[:50], 1):
        print(f"{i:3d}| {line}")
    if len(report_md.splitlines()) > 50:
        print(f"... (共 {len(report_md.splitlines())} 行)")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
