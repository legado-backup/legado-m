#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DebugRunner 测试套件。

覆盖完整调试流程：预校验 → JVM调试 → 错误诊断 → 自动修复 → 验证 → 经验写入。

测试分层：
1. 单元测试：辅助函数 + DebugCollector（不需要 JAR）
2. 经验管理测试：ExperienceManager 的 extract/write_to_basic_memory
3. 完整流程测试：run() 主流程（mock JAR，验证全链路输出结构化 JSON + 经验 MCP 指令）
4. JAR 集成测试：JAR 可用时真实测试，不可用时优雅降级

同时支持 `python test_debug_runner.py` 独立运行和 `pytest test_debug_runner.py` 运行。
"""
import io
import contextlib
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# 添加 legado_client 父目录到 sys.path（从 tests/ 向上回溯到 scripts/）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legado_client.client.debug_runner import (
    run, DebugCollector, apply_auto_fix, iterative_repair_loop,
    _detect_type_from_obj, _detect_obstacle_type, _extract_js_from_source,
    STAGE_NAMES, STATE_TO_STAGE,
)
from legado_client.experience.experience_manager import ExperienceManager
from legado_client.utils.config import config


# ==================== 辅助函数 ====================

class _MockArgs:
    """模拟 argparse.Namespace，提供 run() 所需的全部属性。"""

    def __init__(self, **kwargs):
        self.key = kwargs.get("key", "test")
        self.stage = kwargs.get("stage", "all")
        self.timeout = kwargs.get("timeout", 30)
        self.max_iterations = kwargs.get("max_iterations", 1)
        self.output = kwargs.get("output", None)
        self.no_experience = kwargs.get("no_experience", False)
        self.source = kwargs.get("source", "test.json")
        self.import_cookies = kwargs.get("import_cookies", None)
        self.proxy = kwargs.get("proxy", None)
        self.ua = kwargs.get("ua", None)
        self.skip_db_lookup = kwargs.get("skip_db_lookup", True)   # 3.7: 测试默认跳过数据库
        self.db_only = kwargs.get("db_only", False)               # 3.8: 仅查数据库不测试


def _jar_available() -> bool:
    """检测 JAR 文件是否真实存在。"""
    try:
        candidates = [
            config.tools_dir / "legado-jvm" / "build" / "libs" / "legado-jvm.jar",
            config.tools_dir / "legado-rule-engine-mvp4.jar",
            config.tools_dir / "legado-rule-engine-mvp3.jar",
            config.tools_dir / "legado-rule-engine-mvp2.jar",
            config.tools_dir / "legado-rule-engine-mvp1.jar",
        ]
        return any(p.exists() for p in candidates)
    except Exception:
        return False


def _java_available() -> bool:
    """检测 Java 是否可用。"""
    return config.find_java() is not None


def _make_valid_book_source() -> dict:
    """构造一个通过预校验的合法书源对象。"""
    return {
        "bookSourceName": "测试书源",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "searchUrl": "https://example.com/search?q={{key}}",
        "ruleSearch": {"bookList": "class.book-item"},
        "ruleBookInfo": {"name": "class.title", "author": "class.author"},
        "ruleToc": {
            "chapterList": "class.chapter",
            "chapterName": "tag.a@text",
            "chapterUrl": "tag.a@href",
        },
        "ruleContent": {"content": "class.content"},
    }


def _make_valid_rss_source() -> dict:
    """构造一个通过预校验的合法订阅源对象。"""
    return {
        "sourceName": "测试订阅源",
        "sourceUrl": "https://rss.example.com",
        "type": 0,
        "ruleArticles": "class.article",
        "ruleTitle": "tag.a@text",
        "ruleLink": "tag.a@href",
    }


def _make_mock_client_success(source_type: str = "book") -> MagicMock:
    """构造一个 mock 的 RuleEngineClient，模拟调试成功。

    Args:
        source_type: 'book' 或 'rss'，决定 mock 哪个 debug 方法

    Returns:
        MagicMock 实例，ping 返回 ok，debug 方法触发成功回调
    """
    mock_client = MagicMock()
    mock_client.ping.return_value = {"ok": True}

    def _mock_debug(source_json, key, on_log=None, on_error=None, on_result=None):
        if on_log:
            on_log(10, "搜索页日志", "<html>search</html>")
            on_log(20, "详情页日志", None)
        if on_result:
            stages = "search→detail→toc→content" if source_type == "book" else "sort→content"
            on_result(True, {"stages": stages})
        return {"type": "result", "success": True, "summary": {"stages": stages}}

    if source_type == "book":
        mock_client.debug_book_source.side_effect = _mock_debug
    else:
        mock_client.debug_rss_source.side_effect = _mock_debug

    return mock_client


# ==================== 单元测试：辅助函数 ====================

def test_detect_type_book():
    """测试书源类型检测（含 bookSourceUrl）。"""
    source_obj = {"bookSourceUrl": "https://example.com"}
    assert _detect_type_from_obj(source_obj) == "book"


def test_detect_type_rss_with_ruleArticles():
    """测试订阅源类型检测（sourceUrl + ruleArticles）。"""
    source_obj = {"sourceUrl": "https://example.com", "ruleArticles": "class.x"}
    assert _detect_type_from_obj(source_obj) == "rss"


def test_detect_type_rss_only_sourceUrl():
    """测试订阅源类型检测（仅 sourceUrl）。"""
    source_obj = {"sourceUrl": "https://example.com"}
    assert _detect_type_from_obj(source_obj) == "rss"


def test_detect_type_book_with_ruleSearch():
    """测试书源类型检测（仅 ruleSearch，回退为 book）。"""
    source_obj = {"ruleSearch": {"bookList": "class.x"}}
    assert _detect_type_from_obj(source_obj) == "book"


def test_detect_type_empty_defaults_book():
    """测试空对象默认为书源。"""
    assert _detect_type_from_obj({}) == "book"


def test_detect_obstacle_login():
    """测试登录障碍检测。"""
    assert _detect_obstacle_type("需要登录", None) == "login"
    assert _detect_obstacle_type("please login first", None) == "login"
    assert _detect_obstacle_type("unauthorized", "401") == "login"


def test_detect_obstacle_cf():
    """测试 Cloudflare 障碍检测。"""
    assert _detect_obstacle_type("cloudflare challenge", None) == "cf"
    assert _detect_obstacle_type("just a moment", None) == "cf"
    assert _detect_obstacle_type("cf_browser", None) == "cf"


def test_detect_obstacle_captcha():
    """测试验证码障碍检测。"""
    assert _detect_obstacle_type("验证码错误", None) == "captcha"
    assert _detect_obstacle_type("captcha required", None) == "captcha"
    assert _detect_obstacle_type("geetest", None) == "captcha"


def test_detect_obstacle_none():
    """测试无障碍类型返回 None。"""
    assert _detect_obstacle_type("普通解析错误", None) is None
    assert _detect_obstacle_type("rule not found", "stack") is None


def test_extract_js_inline():
    """测试提取 @js: 内联 JS 代码。"""
    source_obj = {"ruleContent": {"content": "@js:result + 1"}}
    js = _extract_js_from_source(source_obj)
    assert "result + 1" in js


def test_extract_js_tag():
    """测试提取 <js> 标签 JS 代码。"""
    source_obj = {"ruleContent": {"content": "<js>var x = 1;</js>"}}
    js = _extract_js_from_source(source_obj)
    assert "var x = 1;" in js


def test_extract_js_none():
    """测试无 JS 代码时返回空字符串。"""
    source_obj = {"ruleContent": {"content": "class.article@text"}}
    js = _extract_js_from_source(source_obj)
    assert js == ""


def test_extract_js_nested():
    """测试嵌套结构中的 JS 提取。"""
    source_obj = {
        "ruleSearch": {"bookList": "@js:search()"},
        "ruleBookInfo": {"name": "<js>name()</js>"},
    }
    js = _extract_js_from_source(source_obj)
    assert "search()" in js
    assert "name()" in js


def test_stage_names_constant():
    """测试 STAGE_NAMES 常量包含 4 个阶段。"""
    assert "search" in STAGE_NAMES
    assert "detail" in STAGE_NAMES
    assert "toc" in STAGE_NAMES
    assert "content" in STAGE_NAMES
    assert len(STAGE_NAMES) == 4


def test_state_to_stage_mapping():
    """测试 STATE_TO_STAGE 整数到字符串映射。"""
    assert STATE_TO_STAGE[10] == "search"
    assert STATE_TO_STAGE[20] == "detail"
    assert STATE_TO_STAGE[30] == "toc"
    assert STATE_TO_STAGE[40] == "content"


# ==================== 单元测试：DebugCollector ====================

def test_collector_on_log_collects_html():
    """测试 on_log 收集 HTML 源码。"""
    collector = DebugCollector()
    collector.on_log(10, "搜索页日志", "<html>search</html>")
    assert len(collector.logs) == 1
    assert collector.logs[0]["state"] == 10
    assert "search" in collector.html_sources
    assert collector.html_sources["search"] == "<html>search</html>"


def test_collector_on_log_unknown_state():
    """测试 on_log 处理未知 state（不收集 HTML）。"""
    collector = DebugCollector()
    collector.on_log(99, "未知阶段", "<html>x</html>")
    assert len(collector.logs) == 1
    assert len(collector.html_sources) == 0  # 未知 state 不收集


def test_collector_on_error_collects():
    """测试 on_error 收集错误信息。"""
    collector = DebugCollector()
    collector.on_error("解析失败", "stack trace", "search")
    assert len(collector.errors) == 1
    assert collector.errors[0]["msg"] == "解析失败"
    assert "search" in collector.stages_failed


def test_collector_on_error_with_source_obj():
    """测试 on_error 带源对象时触发交互请求。"""
    source_obj = _make_valid_book_source()
    collector = DebugCollector(source_obj=source_obj)
    collector.on_error("rule_empty: 规则为空", None, "search")
    assert len(collector.errors) == 1


def test_collector_on_result_success():
    """测试 on_result 成功回调。"""
    collector = DebugCollector()
    collector.on_result(True, {"stages": "search→detail→toc→content"})
    assert collector.result["success"] is True
    assert "search" in collector.stages_passed
    assert "detail" in collector.stages_passed
    assert "toc" in collector.stages_passed
    assert "content" in collector.stages_passed


def test_collector_on_result_failed():
    """测试 on_result 失败回调。"""
    collector = DebugCollector()
    collector.on_result(False, {"stages": ""})
    assert collector.result["success"] is False
    assert len(collector.stages_passed) == 0


def test_collector_on_result_arrow_separator():
    """测试 on_result 支持 -> 分隔符。"""
    collector = DebugCollector()
    collector.on_result(True, {"stages": "search->detail->toc"})
    assert "search" in collector.stages_passed
    assert "detail" in collector.stages_passed
    assert "toc" in collector.stages_passed


def test_collector_generate_report_high_confidence():
    """测试成功调试生成高可信报告。"""
    collector = DebugCollector()
    collector.on_result(True, {"stages": "search→detail→toc→content"})
    confidence = collector.generate_report()
    assert confidence == "high"


def test_collector_generate_report_low_confidence():
    """测试失败调试生成低可信报告。"""
    collector = DebugCollector()
    collector.on_result(False, {"stages": ""})
    confidence = collector.generate_report()
    assert confidence == "low"


def test_collector_generate_report_with_source_obj():
    """测试带源对象的报告生成（使用 evaluate_confidence）。"""
    source_obj = _make_valid_book_source()
    collector = DebugCollector(source_obj=source_obj)
    collector.on_result(True, {"stages": "search→detail→toc→content"})
    confidence = collector.generate_report()
    assert confidence in ("high", "medium", "low")


def test_collector_generate_report_no_result():
    """测试无结果时生成 unknown 报告。"""
    collector = DebugCollector()
    confidence = collector.generate_report()
    assert confidence == "unknown"


# ==================== 单元测试：apply_auto_fix ====================

def test_apply_auto_fix_no_errors():
    """测试无错误时不执行修复。"""
    collector = DebugCollector()
    result = apply_auto_fix({}, collector)
    assert result is None


def test_apply_auto_fix_with_error():
    """测试有错误时尝试修复（可能返回 None 或修复后的源）。"""
    source_obj = _make_valid_book_source()
    collector = DebugCollector(source_obj=source_obj)
    collector.on_error("rule_empty: 规则为空", None, "search")
    # auto_fix_error 可能返回修复结果或 None（取决于错误类型）
    result = apply_auto_fix(source_obj, collector)
    # 不强制要求修复成功，只要不抛异常即可
    assert result is None or isinstance(result, dict)


# ==================== 经验管理测试 ====================

def test_experience_extract_success():
    """测试 ExperienceManager.extract 提取经验要素。"""
    source_obj = _make_valid_book_source()
    debug_result = {
        "success": True,
        "error_type": None,
        "fix_method": None,
        "fix_applied": False,
    }
    exp_mgr = ExperienceManager()
    draft = exp_mgr.extract(source_obj, debug_result, "high")
    assert isinstance(draft, dict)
    assert "website_feature" in draft
    assert "rule_pattern" in draft
    assert "confidence" in draft
    assert draft["confidence"] == "high"
    assert draft["source_url"] == "https://example.com"
    assert draft["source_name"] == "测试书源"


def test_experience_extract_with_error():
    """测试调试失败时提取错误类型。"""
    source_obj = _make_valid_book_source()
    debug_result = {
        "success": False,
        "error_type": "rule_empty",
        "fix_method": "auto_fix",
        "fix_applied": True,
    }
    exp_mgr = ExperienceManager()
    draft = exp_mgr.extract(source_obj, debug_result, "low")
    assert draft["error_type"] == "rule_empty"
    assert draft["fix_method"] == "auto_fix"


def test_experience_write_to_basic_memory_format():
    """测试 write_to_basic_memory 返回 MCP 指令格式。"""
    experience_draft = {
        "website_feature": "example.com (WordPress)",
        "rule_pattern": "CSS选择器",
        "confidence": "high",
        "source_url": "https://example.com",
        "source_name": "测试源",
        "timestamp": "2026-01-01T00:00:00",
        "error_type": None,
        "fix_method": None,
    }
    exp_mgr = ExperienceManager()
    mcp_instruction = exp_mgr.write_to_basic_memory(experience_draft)
    assert isinstance(mcp_instruction, dict)
    assert mcp_instruction["tool"] == "mcp_basic-memory_write_note"
    assert mcp_instruction["args"]["project"] == "legado"
    assert "content" in mcp_instruction["args"]
    assert "title" in mcp_instruction["args"]


# ==================== 完整流程测试：run() ====================

def test_run_precheck_failed_book():
    """测试书源预校验失败（缺少必填字段）时 sys.exit(1)。"""
    source_obj = {}  # 空对象，缺少 bookSourceName/bookSourceUrl/bookSourceType
    args = _MockArgs()

    captured = io.StringIO()
    exit_code = None
    with contextlib.redirect_stdout(captured):
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    assert exit_code == 1, f"期望退出码 1，实际 {exit_code}"
    assert "预校验失败" in output or "PRECHECK_FAILED" in output


def test_run_precheck_failed_rss():
    """测试订阅源预校验失败（缺少必填字段）时 sys.exit(1)。"""
    source_obj = {"sourceUrl": "not-a-url"}  # 缺少 sourceName，URL 非法
    args = _MockArgs()

    captured = io.StringIO()
    exit_code = None
    with contextlib.redirect_stdout(captured):
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    assert exit_code == 1
    assert "预校验失败" in output or "PRECHECK_FAILED" in output


def test_run_book_success_with_mock():
    """测试书源完整流程成功（mock JAR）。

    覆盖：预校验 → JVM调试 → 结果收集 → 报告生成 → 经验写入
    """
    source_obj = _make_valid_book_source()
    args = _MockArgs(key="测试关键词", no_experience=False)

    mock_client = _make_mock_client_success("book")

    captured = io.StringIO()
    exit_code = None
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         patch("legado_client.client.debug_runner.ExperienceManager") as mock_exp_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_exp.extract.return_value = {
            "website_feature": "example.com",
            "rule_pattern": "CSS选择器",
            "confidence": "high",
        }
        mock_exp.write_to_basic_memory.return_value = {
            "tool": "mcp_basic-memory_write_note",
            "args": {"title": "经验: example.com", "project": "legado"},
        }
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    assert exit_code == 0, f"期望退出码 0，实际 {exit_code}"
    assert "源类型: 书源" in output
    assert "调试结果" in output
    # 验证经验 MCP 指令输出到 stdout
    assert "[EXPERIENCE_PENDING]" in output
    # 验证 mock_client 被正确调用
    mock_client.ping.assert_called_once()
    mock_client.debug_book_source.assert_called_once()


def test_run_rss_success_with_mock():
    """测试订阅源完整流程成功（mock JAR）。"""
    source_obj = _make_valid_rss_source()
    args = _MockArgs(key="https://rss.example.com/article/1", no_experience=True)

    mock_client = _make_mock_client_success("rss")

    captured = io.StringIO()
    exit_code = None
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    assert exit_code == 0, f"期望退出码 0，实际 {exit_code}"
    assert "源类型: 订阅源" in output
    assert "调试结果" in output
    # no_experience=True 时不输出经验 MCP 指令
    assert "[EXPERIENCE_PENDING]" not in output
    mock_client.debug_rss_source.assert_called_once()


def test_run_book_with_json_output():
    """测试书源完整流程带 JSON 报告输出。

    验证全链路输出结构化 JSON。
    """
    source_obj = _make_valid_book_source()
    output_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    output_file.close()
    args = _MockArgs(key="test", no_experience=True, output=output_file.name)

    mock_client = _make_mock_client_success("book")

    captured = io.StringIO()
    exit_code = None
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    try:
        assert exit_code == 0
        # 验证 JSON 报告文件已生成且结构正确
        assert os.path.exists(output_file.name), "JSON 报告文件未生成"
        with open(output_file.name, "r", encoding="utf-8") as f:
            report = json.load(f)
        assert isinstance(report, dict)
        assert "source_name" in report
        assert "source_url" in report
        assert "success" in report
        assert "stages_passed" in report
        assert "confidence" in report
        assert report["success"] is True
        assert report["source_url"] == "https://example.com"
    finally:
        if os.path.exists(output_file.name):
            os.unlink(output_file.name)


def test_run_no_experience_flag():
    """测试 no_experience=True 时跳过经验写入。"""
    source_obj = _make_valid_book_source()
    args = _MockArgs(key="test", no_experience=True)

    mock_client = _make_mock_client_success("book")

    captured = io.StringIO()
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        try:
            run(args, source_obj)
        except SystemExit:
            pass

    output = captured.getvalue()
    assert "[EXPERIENCE_PENDING]" not in output


def test_run_ping_failure_with_mock():
    """测试 JVM ping 失败时触发降级（mock 场景）。

    ping 失败会抛 RuntimeError，run() 捕获后降级到 verify-source.py，
    退出码取决于降级脚本返回值，故仅验证降级行为被触发。
    """
    source_obj = _make_valid_book_source()
    args = _MockArgs(key="test", no_experience=True)

    mock_client = MagicMock()
    mock_client.ping.return_value = {"ok": False, "error": "JVM not ready"}

    captured = io.StringIO()
    exit_code = None
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    # ping 失败触发降级到 Python 模式或严重错误退出
    assert exit_code in (0, 1, 2, 3), f"异常退出码: {exit_code}"
    assert "降级" in output or "严重错误" in output


def test_run_debug_failure_with_mock():
    """测试调试失败时退出码为 1（部分失败）。"""
    source_obj = _make_valid_book_source()
    args = _MockArgs(key="test", no_experience=True, max_iterations=1)

    mock_client = MagicMock()
    mock_client.ping.return_value = {"ok": True}

    def _mock_debug_fail(source_json, key, on_log=None, on_error=None, on_result=None):
        if on_error:
            on_error("rule_empty: 规则为空", None, "search")
        if on_result:
            on_result(False, {"stages": ""})
        return {"type": "result", "success": False, "summary": {"stages": ""}}

    mock_client.debug_book_source.side_effect = _mock_debug_fail

    captured = io.StringIO()
    exit_code = None
    with patch("legado_client.client.debug_runner.RuleEngineClient") as mock_cls, \
         contextlib.redirect_stdout(captured):
        mock_cls.return_value.__enter__.return_value = mock_client
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    # 调试失败 + 有 errors → sys.exit(1)
    assert exit_code == 1, f"期望退出码 1，实际 {exit_code}"


# ==================== JAR 集成测试（优雅降级） ====================

def test_run_with_real_jar():
    """JAR 可用时测试真实调试流程。JAR 不可用时跳过。

    使用简单 mock 源 JSON，不依赖真实网站访问。
    """
    if not (_jar_available() and _java_available()):
        print("  [SKIP] JAR 或 Java 不可用，跳过真实 JAR 集成测试")
        return

    source_obj = _make_valid_book_source()
    args = _MockArgs(key="test", no_experience=True, timeout=30)

    captured = io.StringIO()
    exit_code = None
    with contextlib.redirect_stdout(captured):
        try:
            run(args, source_obj)
        except SystemExit as e:
            exit_code = e.code

    output = captured.getvalue()
    # 真实 JAR 调试可能成功或失败（取决于网络），只要不崩溃即可
    assert exit_code in (0, 1, 2, 3), f"异常退出码: {exit_code}"
    assert "源类型: 书源" in output


# ==================== 独立运行支持 ====================

def _run_all_tests():
    """收集并运行所有 test_ 开头的函数。"""
    test_funcs = [
        (name, obj) for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, func in test_funcs:
        try:
            func()
            print(f"  [PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 项")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    print("DebugRunner 测试套件")
    print(f"{'='*60}\n")
    success = _run_all_tests()
    sys.exit(0 if success else 1)
