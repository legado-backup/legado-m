"""ai_tests/tests/test_case_parser.py — M3 用例解析器单元测试（V3 双轨调度）

任务 5.10：单元测试（含 V3 双轨调度场景）+ 实测验证

运行：
    python -m pytest ai_tests/tests/test_case_parser.py -v
或：
    python ai_tests/tests/test_case_parser.py
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.case_parser import (
    CaseParser, TestCase, Step, Expect, Precondition,
    TC_HEADER_RE, SECTION_RE, STEP_RE, EXPECT_RE, PRECOND_RE,
)


# === 正则测试 ===

def test_tc_header_re_chinese_colon():
    """正常用例：TC 头部正则匹配（中文冒号）"""
    line = "## TC-F-P0-1-01：编码转换工具（正常用例）"
    m = TC_HEADER_RE.match(line)
    assert m is not None
    assert m.group(1) == "TC-F-P0-1-01"
    assert "编码转换工具" in m.group(2)
    print("[PASS] test_tc_header_re_chinese_colon")


def test_tc_header_re_english_colon():
    """正常用例：TC 头部正则匹配（英文冒号）"""
    line = "### TC-01: Vite 构建成功"
    m = TC_HEADER_RE.match(line)
    assert m is not None
    assert m.group(1) == "TC-01"
    assert "Vite" in m.group(2)
    print("[PASS] test_tc_header_re_english_colon")


def test_section_re():
    """正常用例：段落标题正则匹配"""
    line = "**测试步骤**："
    m = SECTION_RE.match(line)
    assert m is not None
    assert "测试步骤" in m.group(1)
    print("[PASS] test_section_re")


def test_step_re():
    """正常用例：步骤行正则匹配"""
    line = "1. 进入\"我的→调试工具→编码转换\""
    m = STEP_RE.match(line)
    assert m is not None
    assert "进入" in m.group(1)
    print("[PASS] test_step_re")


def test_expect_re_with_emoji():
    """正常用例：预期行正则匹配（带 emoji）"""
    line = "- ✅ 正确显示 Base64 编码结果"
    m = EXPECT_RE.match(line)
    assert m is not None
    assert "Base64" in m.group(1)
    print("[PASS] test_expect_re_with_emoji")


def test_precond_re():
    """正常用例：前置资源标记正则匹配"""
    line = "[AI自备] 测试 URL: https://httpbin.org/get"
    m = PRECOND_RE.match(line)
    assert m is not None
    assert m.group(1) == "AI自备"
    assert "httpbin.org" in m.group(2)
    print("[PASS] test_precond_re")


# === CaseParser 类测试 ===

def test_parse_file_typical_format():
    """正常用例：解析典型格式 MD 文件"""
    md_content = """# F-P0-1 调试工具集 测试用例

## 功能概述

调试工具入口

## TC-F-P0-1-01：编码转换工具（正常用例）

**测试步骤**：
1. 进入"我的→调试工具→编码转换"
2. 输入"你好世界"
3. 点击"转换"

**预期结果**：
- ✅ 正确显示 Base64 编码结果
- ✅ 复制功能正常
- ✅ 不崩溃
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        f.flush()
        path = Path(f.name)

    try:
        parser = CaseParser()
        cases = parser.parse_file(path)
        assert len(cases) == 1, f"应解析 1 个用例，实际 {len(cases)}"
        tc = cases[0]
        assert tc.tc_id == "TC-F-P0-1-01"
        assert "编码转换工具" in tc.title
        assert tc.case_type == "正常用例"
        assert len(tc.steps) == 3
        assert tc.steps[0].action == "click"  # "进入" → click
        assert tc.steps[1].action == "input"  # "输入" → input
        assert tc.steps[1].value == "你好世界"
        assert tc.steps[2].action == "click"  # "点击" → click
        assert len(tc.expects) == 3
        # 不崩溃 → no_crash（优先级最高）
        assert any(e.expect_type == "no_crash" for e in tc.expects)
        # 正确显示 → element_visible
        assert any(e.expect_type == "element_visible" for e in tc.expects)
    finally:
        path.unlink(missing_ok=True)
    print("[PASS] test_parse_file_typical_format")


def test_parse_file_with_preconditions():
    """正常用例：解析含前置条件 + V3 前置资源标记"""
    md_content = """# P0 测试用例

### TC-P0-1-01：协程正常取消（正常用例）

**前置条件**：书架正在刷新书籍

**前置资源**：[AI自备] 测试书源 JSON

**测试步骤**：
1. 打开书架页面
2. 触发书架刷新

**预期结果**：
- ✅ 无 ANR 弹窗
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        f.flush()
        path = Path(f.name)

    try:
        parser = CaseParser()
        cases = parser.parse_file(path)
        assert len(cases) == 1
        tc = cases[0]
        assert tc.tc_id == "TC-P0-1-01"
        # 前置条件 + 前置资源 都应被识别
        assert len(tc.preconditions) == 2
        # 第一个是"前置条件"（旧格式，归为共享）
        assert tc.preconditions[0].resource_type == "共享"
        assert "书架正在刷新" in tc.preconditions[0].description
        # 第二个是"前置资源"（V3 标记）
        assert tc.preconditions[1].resource_type == "AI自备"
        assert "测试书源" in tc.preconditions[1].description
    finally:
        path.unlink(missing_ok=True)
    print("[PASS] test_parse_file_with_preconditions")


def test_parse_file_with_v3_source_activity():
    """正常用例：V3 关联源码 + 关联 Activity 字段"""
    md_content = """# F-P0-1 测试用例

## TC-F-P0-1-01：调试工具入口（正常用例）

**关联源码**：DebugToolsActivity.kt
**关联 Activity**：MyActivity

**测试步骤**：
1. 打开"我的"页面

**预期结果**：
- ✅ 调试工具入口可见
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        f.flush()
        path = Path(f.name)

    try:
        parser = CaseParser()
        cases = parser.parse_file(path)
        assert len(cases) == 1
        tc = cases[0]
        assert len(tc.related_source) == 1
        assert "DebugToolsActivity" in tc.related_source[0]
        assert len(tc.related_activity) == 1
        assert "MyActivity" in tc.related_activity[0]
    finally:
        path.unlink(missing_ok=True)
    print("[PASS] test_parse_file_with_v3_source_activity")


def test_parse_file_empty():
    """边界用例：空文件"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write("")
        f.flush()
        path = Path(f.name)

    try:
        parser = CaseParser()
        cases = parser.parse_file(path)
        assert len(cases) == 0
    finally:
        path.unlink(missing_ok=True)
    print("[PASS] test_parse_file_empty")


def test_parse_file_no_steps():
    """边界用例：用例无步骤（应记 parse_warnings）"""
    md_content = """# 测试

## TC-TEST-01：无步骤用例

**预期结果**：
- ✅ xxx
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        f.flush()
        path = Path(f.name)

    try:
        parser = CaseParser()
        cases = parser.parse_file(path)
        assert len(cases) == 1
        tc = cases[0]
        assert len(tc.steps) == 0
        assert any("无测试步骤" in w for w in tc.parse_warnings)
    finally:
        path.unlink(missing_ok=True)
    print("[PASS] test_parse_file_no_steps")


def test_parse_file_not_exist():
    """异常用例：文件不存在"""
    parser = CaseParser()
    cases = parser.parse_file(Path("/nonexistent/path.md"))
    assert len(cases) == 0
    print("[PASS] test_parse_file_not_exist")


def test_classify_action_input():
    """正常用例：步骤语义化 - input 动作"""
    parser = CaseParser()
    step = parser._classify_action('输入 `https://httpbin.org/get`')
    assert step.action == "input"
    assert step.value == "https://httpbin.org/get"
    print("[PASS] test_classify_action_input")


def test_classify_action_click():
    """正常用例：步骤语义化 - click 动作"""
    parser = CaseParser()
    step = parser._classify_action('点击"转换"按钮')
    assert step.action == "click"
    print("[PASS] test_classify_action_click")


def test_classify_expect_no_crash():
    """正常用例：预期类型识别 - no_crash"""
    parser = CaseParser()
    expect = parser._classify_expect("不崩溃")
    assert expect.expect_type == "no_crash"
    print("[PASS] test_classify_expect_no_crash")


def test_classify_expect_log_clean():
    """正常用例：预期类型识别 - log_clean"""
    parser = CaseParser()
    expect = parser._classify_expect("BUILD SUCCESSFUL")
    assert expect.expect_type == "log_clean"
    print("[PASS] test_classify_expect_log_clean")


# === V3 双轨调度测试 ===

def test_dispatch_md_only():
    """V3 双轨调度：仅有 MD 用例 → 返回 md"""
    tc = TestCase(tc_id="TC-TEST-01", title="test")
    tc.python_track_path = None
    parser = CaseParser()
    assert parser.dispatch_test_case(tc) == "md"
    assert tc.track_source == "md"
    print("[PASS] test_dispatch_md_only")


def test_dispatch_python_priority():
    """V3 双轨调度：Python 优先于 MD"""
    tc = TestCase(tc_id="TC-TEST-01", title="test")
    tc.python_track_path = "/path/to/auto_tc_test_01.py"
    parser = CaseParser()
    assert parser.dispatch_test_case(tc) == "python"
    print("[PASS] test_dispatch_python_priority")


def test_find_python_track_by_filename():
    """V3 _find_python_track：文件名匹配"""
    parser = CaseParser()
    # mock AI_TESTS_CASES_DIR 存在 + auto_tc_test_01.py 文件存在
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        module_dir = tmpdir / "F-P0-1"
        module_dir.mkdir()
        # 文件名匹配规则：auto_{tc_id_lower_with_underscores}.py
        py_file = module_dir / "auto_tc_f_p0_1_01.py"
        py_file.write_text("# test", encoding="utf-8")

        with patch("ai_tests.lib.case_parser.AI_TESTS_CASES_DIR", tmpdir):
            result = parser._find_python_track("TC-F-P0-1-01", "F-P0-1")
            assert result is not None
            assert "auto_tc_f_p0_1_01.py" in result
    print("[PASS] test_find_python_track_by_filename")


def test_find_python_track_by_header_comment():
    """V3 _find_python_track：文件头 @tc_id 注释匹配"""
    parser = CaseParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        module_dir = tmpdir / "F-P0-1"
        module_dir.mkdir()
        # 文件名不匹配，但文件头含 @tc_id
        py_file = module_dir / "auto_custom_name.py"
        py_file.write_text(
            '"""auto test\n@tc_id: TC-F-P0-1-01\n"""\n# code',
            encoding="utf-8",
        )

        with patch("ai_tests.lib.case_parser.AI_TESTS_CASES_DIR", tmpdir):
            result = parser._find_python_track("TC-F-P0-1-01", "F-P0-1")
            assert result is not None
            assert "auto_custom_name.py" in result
    print("[PASS] test_find_python_track_by_header_comment")


def test_find_python_track_not_found():
    """V3 _find_python_track：未找到 → None"""
    parser = CaseParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("ai_tests.lib.case_parser.AI_TESTS_CASES_DIR", Path(tmpdir)):
            result = parser._find_python_track("TC-XXX-99", "F-P0-99")
            assert result is None
    print("[PASS] test_find_python_track_not_found")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M3 CaseParser 单元测试")
    print("=" * 60)
    test_tc_header_re_chinese_colon()
    test_tc_header_re_english_colon()
    test_section_re()
    test_step_re()
    test_expect_re_with_emoji()
    test_precond_re()
    test_parse_file_typical_format()
    test_parse_file_with_preconditions()
    test_parse_file_with_v3_source_activity()
    test_parse_file_empty()
    test_parse_file_no_steps()
    test_parse_file_not_exist()
    test_classify_action_input()
    test_classify_action_click()
    test_classify_expect_no_crash()
    test_classify_expect_log_clean()
    test_dispatch_md_only()
    test_dispatch_python_priority()
    test_find_python_track_by_filename()
    test_find_python_track_by_header_comment()
    test_find_python_track_not_found()
    print("=" * 60)
    print("所有测试 PASS！")


if __name__ == "__main__":
    main()
