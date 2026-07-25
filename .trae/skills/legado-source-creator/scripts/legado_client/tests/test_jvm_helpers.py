#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jvm_helpers 单元测试。

同时支持：
- `python test_jvm_helpers.py` 独立运行
- `pytest test_jvm_helpers.py` 运行

被测模块：utils/jvm_helpers.py
"""
import argparse
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.jvm_helpers import add_jvm_args, init_jvm_client, assess_confidence


# ========== add_jvm_args ==========

def test_add_jvm_args_adds_jvm_option():
    """add_jvm_args 添加 --jvm 参数。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args(["--jvm", "true"])
    assert args.jvm is True


def test_add_jvm_args_jvm_false():
    """--jvm false 解析为 False。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args(["--jvm", "false"])
    assert args.jvm is False


def test_add_jvm_args_jvm_no():
    """--jvm no 解析为 False。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args(["--jvm", "no"])
    assert args.jvm is False


def test_add_jvm_args_jvm_0():
    """--jvm 0 解析为 False。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args(["--jvm", "0"])
    assert args.jvm is False


def test_add_jvm_args_default_true():
    """--jvm 默认为 True。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args([])
    assert args.jvm is True


def test_add_jvm_args_jar_path():
    """add_jvm_args 添加 --jar-path 参数。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args(["--jar-path", "/custom/path.jar"])
    assert args.jar_path == "/custom/path.jar"


def test_add_jvm_args_jar_path_default_none():
    """--jar-path 默认为 None。"""
    parser = argparse.ArgumentParser()
    add_jvm_args(parser)
    args = parser.parse_args([])
    assert args.jar_path is None


# ========== init_jvm_client ==========

def test_init_jvm_client_file_not_found():
    """init_jvm_client JAR 不存在时降级返回 (None, False)。"""
    with patch("legado_client.client.rule_engine_client.RuleEngineClient") as MockClient:
        MockClient.return_value.start.side_effect = FileNotFoundError("JAR not found")
        client, available = init_jvm_client(jar_path="/nonexistent.jar")
        assert client is None
        assert available is False


def test_init_jvm_client_java_not_found():
    """init_jvm_client Java 未安装时降级返回 (None, False)。"""
    with patch("legado_client.client.rule_engine_client.RuleEngineClient") as MockClient:
        MockClient.return_value.start.side_effect = RuntimeError("Java not found in PATH")
        client, available = init_jvm_client()
        assert client is None
        assert available is False


def test_init_jvm_client_runtime_error():
    """init_jvm_client 其他 RuntimeError 时降级返回 (None, False)。"""
    with patch("legado_client.client.rule_engine_client.RuleEngineClient") as MockClient:
        MockClient.return_value.start.side_effect = RuntimeError("JVM startup failed")
        client, available = init_jvm_client()
        assert client is None
        assert available is False


def test_init_jvm_client_generic_exception():
    """init_jvm_client 通用异常时降级返回 (None, False)。"""
    with patch("legado_client.client.rule_engine_client.RuleEngineClient") as MockClient:
        MockClient.return_value.start.side_effect = Exception("Unexpected error")
        client, available = init_jvm_client()
        assert client is None
        assert available is False


def test_init_jvm_client_success():
    """init_jvm_client 成功时返回 (client, True)。"""
    with patch("legado_client.client.rule_engine_client.RuleEngineClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        client, available = init_jvm_client(jar_path="/fake/path.jar")
        assert client is mock_instance
        assert available is True
        mock_instance.start.assert_called_once()


# ========== assess_confidence ==========

def test_assess_confidence_css_jvm_high():
    """CSS 规则 + JVM 验证 = high。"""
    conf, note = assess_confidence("css", True)
    assert conf == "high"
    assert "JVM" in note


def test_assess_confidence_regex_jvm_high():
    """regex 规则 + JVM 验证 = high。"""
    conf, _ = assess_confidence("regex", True)
    assert conf == "high"


def test_assess_confidence_jsonpath_jvm_high():
    """jsonpath 规则 + JVM 验证 = high。"""
    conf, _ = assess_confidence("jsonpath", True)
    assert conf == "high"


def test_assess_confidence_xpath_jvm_high():
    """xpath 规则 + JVM 验证 = high。"""
    conf, _ = assess_confidence("xpath", True)
    assert conf == "high"


def test_assess_confidence_decrypt_jvm_high():
    """decrypt 规则 + JVM 验证 = high。"""
    conf, note = assess_confidence("decrypt", True)
    assert conf == "high"
    assert "hutool" in note


def test_assess_confidence_encrypt_jvm_high():
    """encrypt 规则 + JVM 验证 = high。"""
    conf, _ = assess_confidence("encrypt", True)
    assert conf == "high"


def test_assess_confidence_css_python_medium():
    """CSS 规则 + Python 仿真 = medium。"""
    conf, note = assess_confidence("css", False)
    assert conf == "medium"
    assert "Python" in note


def test_assess_confidence_js_python_low():
    """JS 规则 + Python 仿真 = low。"""
    conf, _ = assess_confidence("js", False)
    assert conf == "low"


def test_assess_confidence_decrypt_python_low():
    """decrypt 规则 + Python 仿真 = low。"""
    conf, _ = assess_confidence("decrypt", False)
    assert conf == "low"


def test_assess_confidence_js_jvm_pure_logic_high():
    """纯逻辑 JS + JVM 验证 = high。"""
    conf, note = assess_confidence("js", True, "var x = 1 + 2; result = x;")
    assert conf == "high"


def test_assess_confidence_js_es6_let_low():
    """JS 含 let 关键字 = low（ES6 不支持）。"""
    conf, note = assess_confidence("js", True, "let x = 1;")
    assert conf == "low"
    assert "ES6" in note


def test_assess_confidence_js_es6_const_low():
    """JS 含 const 关键字 = low。"""
    conf, _ = assess_confidence("js", True, "const x = 1;")
    assert conf == "low"


def test_assess_confidence_js_es6_arrow_low():
    """JS 含箭头函数 = low。"""
    conf, _ = assess_confidence("js", True, "var f = () => 1;")
    assert conf == "low"


def test_assess_confidence_js_es6_template_string_low():
    """JS 含模板字符串 = low。"""
    conf, _ = assess_confidence("js", True, "var s = `hello`;")
    assert conf == "low"


def test_assess_confidence_js_webview_unverifiable():
    """JS 含 webview = unverifiable。"""
    conf, note = assess_confidence("js", True, "java.webView(...)")
    assert conf == "unverifiable"
    assert "WebView" in note


def test_assess_confidence_js_ajax_medium():
    """JS 含 ajax = medium。"""
    conf, _ = assess_confidence("js", True, "java.ajax('url')")
    assert conf == "medium"


def test_assess_confidence_js_ajax_cookie_low():
    """JS 含 ajax + cookie = low。"""
    conf, _ = assess_confidence("js", True, "java.ajax('url', {cookie: 'x'})")
    assert conf == "low"


def test_assess_confidence_analyze_rule_pure_high():
    """analyze_rule 纯规则 = high。"""
    conf, _ = assess_confidence("analyze_rule", True, ".book-item@text")
    assert conf == "high"


def test_assess_confidence_analyze_rule_js_medium():
    """analyze_rule 含 JS = medium。"""
    conf, _ = assess_confidence("analyze_rule", True, "@js: result = 1;")
    assert conf == "medium"


def test_assess_confidence_analyze_rule_webview_unverifiable():
    """analyze_rule 含 webview = unverifiable。"""
    conf, _ = assess_confidence("analyze_rule", True, "java.webView(...)")
    assert conf == "unverifiable"


def test_assess_confidence_unknown_type_medium():
    """未知规则类型 = medium。"""
    conf, _ = assess_confidence("unknown_type", True)
    assert conf == "medium"


def test_assess_confidence_unknown_type_python_low():
    """未知规则类型 + Python = low。"""
    conf, _ = assess_confidence("unknown_type", False)
    assert conf == "low"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
