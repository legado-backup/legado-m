"""ai_tests/tests/test_run_e2e.py — M10 编排层单元测试

任务 10.9 验证：CLI 参数解析 + --tc 筛选逻辑 + V3 预留参数降级处理 + 退出码逻辑

覆盖范围：
- parse_args（8：基础参数默认值/显式传参/--apk/--no-rules/--keep-device/--instance-id/--init-device/V3 参数）
- filter_cases（6：all/P0/P1/模块名/TC-ID 单用例/无匹配）
- handle_v3_reserved_args（5：无 V3/--diff 不降级/--gen-test 退出/--update-source-map 已实现/--feedback 警告）
- 退出码逻辑（2：parse_args 默认 instance_id/MEmu instance_id=0 边界）

运行：
    python ai_tests/tests/test_run_e2e.py
"""
import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.run_e2e import parse_args, filter_cases, handle_v3_reserved_args, _execute_steps_with_skip
from ai_tests.lib.case_parser import TestCase, Step


# === 工厂函数 ===

def _make_tc(tc_id: str, module: str = "", title: str = "测试用例") -> TestCase:
    """构造单个 TestCase 对象"""
    return TestCase(tc_id=tc_id, title=title, module=module)


def _make_cases_mixed() -> list:
    """构造混合用例列表（P0/P1/不同模块/不同 TC-ID）"""
    return [
        _make_tc("TC-F-P0-1-01", module="F-P0-1", title="进入我的页面"),
        _make_tc("TC-F-P0-1-02", module="F-P0-1", title="书架点击书籍"),
        _make_tc("TC-F-P0-2-01", module="F-P0-2", title="书源管理进入"),
        _make_tc("TC-F-P1-1-01", module="F-P1-1", title="阅读翻页"),
        _make_tc("TC-F-P1-2-01", module="F-P1-2", title="阅读菜单"),
    ]


# === parse_args 测试 ===

def test_parse_args_default():
    """1. 默认参数：--apk=auto, --tc=all, --no-rules=False, --instance-id=0"""
    args = parse_args([])
    assert args.apk == "auto", f"默认 apk 应为 auto，实际: {args.apk}"
    assert args.tc == "all", f"默认 tc 应为 all，实际: {args.tc}"
    assert args.report_dir is None, f"默认 report_dir 应为 None，实际: {args.report_dir}"
    assert args.no_rules is False, f"默认 no_rules 应为 False，实际: {args.no_rules}"
    assert args.keep_device is False, f"默认 keep_device 应为 False，实际: {args.keep_device}"
    assert args.init_device is False, f"默认 init_device 应为 False，实际: {args.init_device}"
    assert args.verbose is False, f"默认 verbose 应为 False，实际: {args.verbose}"
    # V3 参数默认值
    assert args.diff is None, f"默认 diff 应为 None，实际: {args.diff}"
    assert args.gen_test is None, f"默认 gen_test 应为 None，实际: {args.gen_test}"
    assert args.update_source_map is False, f"默认 update_source_map 应为 False，实际: {args.update_source_map}"
    assert args.feedback is False, f"默认 feedback 应为 False，实际: {args.feedback}"
    print("✅ test_parse_args_default")


def test_parse_args_explicit_basic():
    """2. 显式传基础参数"""
    args = parse_args([
        "--apk", "/path/to/app.apk",
        "--tc", "P0",
        "--report-dir", "/tmp/reports",
        "--no-rules",
        "--keep-device",
        "--instance-id", "1",
        "--init-device",
    ])
    assert args.apk == "/path/to/app.apk"
    assert args.tc == "P0"
    assert args.report_dir == "/tmp/reports"
    assert args.no_rules is True
    assert args.keep_device is True
    assert args.instance_id == 1
    assert args.init_device is True
    print("✅ test_parse_args_explicit_basic")


def test_parse_args_apk_auto():
    """3. --apk auto 显式传"""
    args = parse_args(["--apk", "auto"])
    assert args.apk == "auto"
    print("✅ test_parse_args_apk_auto")


def test_parse_args_no_rules_flag():
    """4. --no-rules flag"""
    args = parse_args(["--no-rules"])
    assert args.no_rules is True
    print("✅ test_parse_args_no_rules_flag")


def test_parse_args_keep_device_flag():
    """5. --keep-device flag"""
    args = parse_args(["--keep-device"])
    assert args.keep_device is True
    print("✅ test_parse_args_keep_device_flag")


def test_parse_args_instance_id():
    """6. --instance-id 0（边界值：instance_id=0 不能被识别为 falsy）"""
    args = parse_args(["--instance-id", "0"])
    assert args.instance_id == 0, f"instance_id=0 应保留为 0，实际: {args.instance_id}"
    print("✅ test_parse_args_instance_id")


def test_parse_args_init_device_flag():
    """7. --init-device flag"""
    args = parse_args(["--init-device"])
    assert args.init_device is True
    print("✅ test_parse_args_init_device_flag")


def test_parse_args_v3_diff():
    """8. V3 --diff HEAD~1"""
    args = parse_args(["--diff", "HEAD~1"])
    assert args.diff == "HEAD~1"
    print("✅ test_parse_args_v3_diff")


def test_parse_args_v3_gen_test():
    """9. V3 --gen-test BookshelfActivity"""
    args = parse_args(["--gen-test", "BookshelfActivity"])
    assert args.gen_test == "BookshelfActivity"
    print("✅ test_parse_args_v3_gen_test")


def test_parse_args_v3_update_source_map():
    """10. V3 --update-source-map flag"""
    args = parse_args(["--update-source-map"])
    assert args.update_source_map is True
    print("✅ test_parse_args_v3_update_source_map")


def test_parse_args_v3_feedback():
    """11. V3 --feedback flag"""
    args = parse_args(["--feedback"])
    assert args.feedback is True
    print("✅ test_parse_args_v3_feedback")


def test_parse_args_verbose():
    """12. -v/--verbose flag 启用 DEBUG 日志级别"""
    args = parse_args(["-v"])
    assert args.verbose is True
    args = parse_args(["--verbose"])
    assert args.verbose is True
    # 默认 False
    args = parse_args([])
    assert args.verbose is False
    print("✅ test_parse_args_verbose")


# === filter_cases 测试 ===

def test_filter_cases_all():
    """12. --tc all 返回全部"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "all")
    assert len(result) == 5, f"all 应返回 5 个，实际: {len(result)}"
    print("✅ test_filter_cases_all")


def test_filter_cases_p0():
    """13. --tc P0 按 TC-ID 中的 -P0- 筛选"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "P0")
    assert len(result) == 3, f"P0 应筛选出 3 个，实际: {len(result)}"
    for tc in result:
        assert "-P0-" in tc.tc_id, f"应仅含 P0 用例，实际含: {tc.tc_id}"
    print("✅ test_filter_cases_p0")


def test_filter_cases_p1():
    """14. --tc P1 按 TC-ID 中的 -P1- 筛选"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "P1")
    assert len(result) == 2, f"P1 应筛选出 2 个，实际: {len(result)}"
    for tc in result:
        assert "-P1-" in tc.tc_id, f"应仅含 P1 用例，实际含: {tc.tc_id}"
    print("✅ test_filter_cases_p1")


def test_filter_cases_module():
    """15. --tc F-P0-1 按模块名筛选"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "F-P0-1")
    assert len(result) == 2, f"F-P0-1 应筛选出 2 个，实际: {len(result)}"
    for tc in result:
        assert tc.module == "F-P0-1", f"应仅含 F-P0-1 模块，实际: {tc.module}"
    print("✅ test_filter_cases_module")


def test_filter_cases_single_tc_id():
    """16. --tc TC-F-P0-1-01 单用例 ID 筛选"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "TC-F-P0-1-01")
    assert len(result) == 1, f"单用例应筛选出 1 个，实际: {len(result)}"
    assert result[0].tc_id == "TC-F-P0-1-01"
    print("✅ test_filter_cases_single_tc_id")


def test_filter_cases_no_match():
    """17. --tc F-P9-9 无匹配返回空列表"""
    cases = _make_cases_mixed()
    result = filter_cases(cases, "F-P9-9")
    assert len(result) == 0, f"无匹配应返回空列表，实际: {len(result)}"
    print("✅ test_filter_cases_no_match")


def test_filter_cases_empty_input():
    """18. 空用例列表筛选 all 返回空"""
    result = filter_cases([], "all")
    assert len(result) == 0
    print("✅ test_filter_cases_empty_input")


# === handle_v3_reserved_args 测试 ===

def test_handle_v3_no_reserved_args():
    """19. 无 V3 参数时返回 None（继续执行）"""
    args = parse_args([])
    result = handle_v3_reserved_args(args)
    assert result is None, f"无 V3 参数应返回 None，实际: {result}"
    print("✅ test_handle_v3_no_reserved_args")


def test_handle_v3_diff_not_handled():
    """20. --diff HEAD~1 不在 handle_v3 范围（M8 由 main() 步骤 5.5 处理）"""
    args = parse_args(["--diff", "HEAD~1", "--tc", "P0"])
    original_tc = args.tc
    assert original_tc == "P0"
    result = handle_v3_reserved_args(args)
    assert result is None, f"--diff 应返回 None（继续执行），实际: {result}"
    assert args.tc == "P0", f"handle_v3 不应改动 --tc，实际: {args.tc}"
    print("✅ test_handle_v3_diff_not_handled")


def test_handle_v3_gen_test_early_exit():
    """21. --gen-test 退出码 0（仅提示，不视为错误）"""
    args = parse_args(["--gen-test", "BookshelfActivity"])
    result = handle_v3_reserved_args(args)
    assert result == 0, f"--gen-test 应返回 0，实际: {result}"
    print("✅ test_handle_v3_gen_test_early_exit")


def test_handle_v3_update_source_map_exec():
    """22. --update-source-map 已实现（M8），重建 source_map 后返回 0"""
    with patch("ai_tests.lib.source_impact_analyzer.SourceImpactAnalyzer") as mock_sia:
        mock_analyzer = MagicMock()
        mock_analyzer.build_source_map.return_value = {
            "activities": {
                "BookshelfActivity": {"tc_ids": ["TC-F-P0-1-01"]}
            }
        }
        mock_sia.return_value = mock_analyzer
        args = parse_args(["--update-source-map"])
        result = handle_v3_reserved_args(args)
    assert result == 0, f"--update-source-map 应返回 0，实际: {result}"
    print("✅ test_handle_v3_update_source_map_exec")


def test_handle_v3_feedback_warning():
    """23. --feedback 仅警告，返回 None（继续执行）"""
    args = parse_args(["--feedback"])
    result = handle_v3_reserved_args(args)
    assert result is None, f"--feedback 应返回 None，实际: {result}"
    print("✅ test_handle_v3_feedback_warning")


def test_handle_v3_multiple_reserved_args():
    """24. 多 V3 参数组合：--update-source-map 优先命中返回 0"""
    with patch("ai_tests.lib.source_impact_analyzer.SourceImpactAnalyzer") as mock_sia:
        mock_analyzer = MagicMock()
        mock_analyzer.build_source_map.return_value = {"activities": {}}
        mock_sia.return_value = mock_analyzer
        args = parse_args(["--diff", "HEAD~1", "--feedback", "--update-source-map"])
        result = handle_v3_reserved_args(args)
    assert result == 0, f"含 --update-source-map 应返回 0，实际: {result}"
    print("✅ test_handle_v3_multiple_reserved_args")


# === 主流程退出码逻辑（仅测试 handle_v3_reserved_args 的退出码）===

def test_exit_code_gen_test_zero():
    """25. --gen-test 早期退出码为 0（不视为错误）"""
    args = parse_args(["--gen-test", "MainActivity"])
    result = handle_v3_reserved_args(args)
    assert result == 0, f"--gen-test 退出码应为 0，实际: {result}"
    print("✅ test_exit_code_gen_test_zero")


def test_exit_code_normal_flow():
    """26. 正常流程（无 V3 参数）应继续执行（返回 None，主流程后续决定退出码）"""
    args = parse_args([])
    result = handle_v3_reserved_args(args)
    assert result is None, f"正常流程应返回 None，实际: {result}"
    print("✅ test_exit_code_normal_flow")


# === _execute_steps_with_skip 测试（OpenSpec e2e-ui-executor-hardening 3.6）===

def test_execute_steps_skip_on_failure():
    """正常用例（3.6）：步骤失败后后续步骤 SKIPPED"""
    ui = MagicMock()
    # 第1步失败，第2/3步应被跳过
    ui.execute_step_with_heal.return_value = {"success": False, "error": "not found"}
    steps = [Step(action="click", target="A"), Step(action="click", target="B"), Step(action="click", target="C")]

    results = _execute_steps_with_skip(ui, steps, None, None)

    # 验证：3 个结果，第1个失败，第2/3个 SKIPPED
    assert len(results) == 3, f"应返回 3 个结果，实际: {len(results)}"
    assert results[0]["success"] is False
    assert results[0]["error"] == "not found"
    assert results[1]["error"] == "SKIPPED", f"第2步应 SKIPPED，实际: {results[1]}"
    assert results[2]["error"] == "SKIPPED", f"第3步应 SKIPPED，实际: {results[2]}"
    # 验证 execute_step_with_heal 只被调用1次（第2/3步跳过）
    assert ui.execute_step_with_heal.call_count == 1, \
        f"应只调用 1 次 execute_step_with_heal，实际: {ui.execute_step_with_heal.call_count}"
    print("✅ test_execute_steps_skip_on_failure")


def test_execute_steps_no_skip_on_success():
    """边界用例（3.6）：所有步骤成功 → 不跳过任何步骤"""
    ui = MagicMock()
    ui.execute_step_with_heal.return_value = {"success": True}
    steps = [Step(action="click", target="A"), Step(action="click", target="B")]

    results = _execute_steps_with_skip(ui, steps, None, None)

    assert len(results) == 2
    assert all(r["success"] is True for r in results)
    assert ui.execute_step_with_heal.call_count == 2
    print("✅ test_execute_steps_no_skip_on_success")


def test_execute_steps_empty_list():
    """边界用例（3.6）：空步骤列表 → 返回空结果"""
    ui = MagicMock()
    results = _execute_steps_with_skip(ui, [], None, None)

    assert results == []
    assert ui.execute_step_with_heal.call_count == 0
    print("✅ test_execute_steps_empty_list")


# === 主入口 ===

def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("M10 run_e2e.py 单元测试（任务 10.9）")
    print("=" * 70)
    print()

    tests = [
        # parse_args 测试
        test_parse_args_default,
        test_parse_args_explicit_basic,
        test_parse_args_apk_auto,
        test_parse_args_no_rules_flag,
        test_parse_args_keep_device_flag,
        test_parse_args_instance_id,
        test_parse_args_init_device_flag,
        test_parse_args_v3_diff,
        test_parse_args_v3_gen_test,
        test_parse_args_v3_update_source_map,
        test_parse_args_v3_feedback,
        test_parse_args_verbose,
        # filter_cases 测试
        test_filter_cases_all,
        test_filter_cases_p0,
        test_filter_cases_p1,
        test_filter_cases_module,
        test_filter_cases_single_tc_id,
        test_filter_cases_no_match,
        test_filter_cases_empty_input,
        # handle_v3_reserved_args 测试
        test_handle_v3_no_reserved_args,
        test_handle_v3_diff_not_handled,
        test_handle_v3_gen_test_early_exit,
        test_handle_v3_update_source_map_exec,
        test_handle_v3_feedback_warning,
        test_handle_v3_multiple_reserved_args,
        # 退出码逻辑测试
        test_exit_code_gen_test_zero,
        test_exit_code_normal_flow,
        # _execute_steps_with_skip 测试（3.6）
        test_execute_steps_skip_on_failure,
        test_execute_steps_no_skip_on_success,
        test_execute_steps_empty_list,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} 失败: {e}")

    print()
    print("=" * 70)
    print(f"测试结果: {passed}/{passed + failed} 通过，{failed} 失败")
    print("=" * 70)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
