#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RuleEngineClient 测试套件。

覆盖 7 个核心命令的请求/响应格式：
- ping: 存活检测（可独立测试，不需要真实书源）
- eval (evalJS): JS 代码执行
- extract (evalCSS/analyzeRule/analyzeElements): 内容提取
- debug_book (debugBookSource): 书源端到端调试
- debug_rss (debugRssSource): 订阅源端到端调试
- decrypt/encrypt: 加解密（补充覆盖）
- analyze_url (analyzeUrl): URL 解析（补充覆盖）

注：任务描述中的 validate_book/validate_rss 在 RuleEngineClient 中无直接对应方法，
字段校验由 SourceValidator（legado_client.analyzer.source_validator）负责，不在本测试范围。

同时支持 `python test_rule_engine_client.py` 独立运行和 `pytest test_rule_engine_client.py` 运行。
JAR 不可用时自动跳过真实集成测试，仅测试请求/响应格式。
"""
import os
import sys
from typing import List

# 添加 legado_client 父目录到 sys.path（从 tests/ 向上回溯到 scripts/）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legado_client.client.rule_engine_client import RuleEngineClient
from legado_client.utils.config import config


# ==================== 辅助函数 ====================

def _jar_available() -> bool:
    """检测 JAR 文件是否真实存在（非默认回退路径）。"""
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


def _make_mock_client(captured: List[dict], response: dict = None) -> RuleEngineClient:
    """构造一个 mock 客户端，拦截 _send 调用并记录命令字典。

    Args:
        captured: 用于记录捕获的命令字典的列表
        response: mock 响应字典，默认 {"ok": True, "status": "ok"}

    Returns:
        RuleEngineClient 实例（未启动，_send 已被替换）
    """
    client = RuleEngineClient()
    _response = response or {"ok": True, "status": "ok"}

    def _mock_send(cmd_dict: dict) -> dict:
        captured.append(cmd_dict)
        return _response

    client._send = _mock_send
    return client


# ==================== 命令格式测试（不需要 JAR） ====================

def test_ping_command_format():
    """测试 ping 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    result = client.ping()
    assert captured == [{"cmd": "ping"}], f"ping 命令格式错误: {captured}"
    assert result.get("ok") is True


def test_eval_js_command_format():
    """测试 evalJS (eval) 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    client.eval_js("1 + 1", context="test_ctx")
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd["cmd"] == "evalJS"
    assert cmd["code"] == "1 + 1"
    assert cmd["context"] == "test_ctx"


def test_eval_js_default_context():
    """测试 eval_js 默认 context 为空字符串。"""
    captured = []
    client = _make_mock_client(captured)
    client.eval_js("java.get('x')")
    assert captured[0]["context"] == ""


def test_eval_css_command_format():
    """测试 evalCSS (extract) 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    html = '<html><body><div class="article">Hello</div></body></html>'
    client.eval_css(html, "div.article")
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd["cmd"] == "evalCSS"
    assert cmd["html"] == html
    assert cmd["selector"] == "div.article"


def test_analyze_rule_command_format():
    """测试 analyzeRule (extract) 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    content = '<html><body><div>text</div></body></html>'
    client.analyze_rule(content, "tag.div.0@text", base_url="https://example.com")
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd["cmd"] == "analyzeRule"
    assert cmd["content"] == content
    assert cmd["rule"] == "tag.div.0@text"
    assert cmd["baseUrl"] == "https://example.com"


def test_analyze_rule_no_base_url():
    """测试 analyze_rule 不传 base_url 时不包含该字段。"""
    captured = []
    client = _make_mock_client(captured)
    client.analyze_rule("content", "rule")
    assert "baseUrl" not in captured[0]


def test_analyze_elements_command_format():
    """测试 analyzeElements (extract) 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    client.analyze_elements("content", "class.article@tag.p", base_url="https://ex.com")
    cmd = captured[0]
    assert cmd["cmd"] == "analyzeElements"
    assert cmd["content"] == "content"
    assert cmd["rule"] == "class.article@tag.p"
    assert cmd["baseUrl"] == "https://ex.com"


def test_decrypt_command_format():
    """测试 decrypt 命令请求格式（含 IV）。"""
    captured = []
    client = _make_mock_client(captured)
    client.decrypt(
        algo="AES/CBC/PKCS5Padding",
        key="1234567890123456",
        data="ciphertext",
        iv="97b60394abc2fbe1"
    )
    cmd = captured[0]
    assert cmd["cmd"] == "decrypt"
    assert cmd["algo"] == "AES/CBC/PKCS5Padding"
    assert cmd["key"] == "1234567890123456"
    assert cmd["data"] == "ciphertext"
    assert cmd["iv"] == "97b60394abc2fbe1"
    assert cmd["keyEncoding"] == "utf8"
    assert cmd["ivEncoding"] == "utf8"
    assert cmd["dataEncoding"] == "base64"


def test_decrypt_ecb_no_iv():
    """测试 decrypt ECB 模式不传 IV。"""
    captured = []
    client = _make_mock_client(captured)
    client.decrypt(algo="AES/ECB/PKCS5Padding", key="k", data="d")
    assert "iv" not in captured[0]


def test_encrypt_command_format():
    """测试 encrypt 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    client.encrypt(
        algo="AES/CBC/PKCS5Padding",
        key="key123",
        data="plaintext",
        iv="iv123"
    )
    cmd = captured[0]
    assert cmd["cmd"] == "encrypt"
    assert cmd["algo"] == "AES/CBC/PKCS5Padding"
    assert cmd["dataEncoding"] == "utf8"  # encrypt 默认 utf8


def test_analyze_url_command_format():
    """测试 analyzeUrl 命令请求格式。"""
    captured = []
    client = _make_mock_client(captured)
    client.analyze_url(
        url="https://example.com/search?q={{key}}",
        key="test",
        page=1,
        source_json='{"bookSourceUrl":"https://example.com"}',
        base_url="https://example.com"
    )
    cmd = captured[0]
    assert cmd["cmd"] == "analyzeUrl"
    assert cmd["url"] == "https://example.com/search?q={{key}}"
    assert cmd["key"] == "test"
    assert cmd["page"] == 1
    assert cmd["sourceJson"] == '{"bookSourceUrl":"https://example.com"}'
    assert cmd["baseUrl"] == "https://example.com"


def test_analyze_url_minimal():
    """测试 analyze_url 最小参数（仅 url）。"""
    captured = []
    client = _make_mock_client(captured)
    client.analyze_url("https://example.com")
    cmd = captured[0]
    assert cmd["cmd"] == "analyzeUrl"
    assert cmd["url"] == "https://example.com"
    assert "key" not in cmd
    assert "page" not in cmd
    assert "sourceJson" not in cmd
    assert "baseUrl" not in cmd


# ==================== 流式命令格式测试 ====================

def test_debug_book_source_command_format():
    """测试 debugBookSource (debug_book) 命令请求格式。"""
    captured_stream = []
    client = RuleEngineClient()

    def _mock_send_streaming(cmd_dict, on_log=None, on_error=None, on_result=None):
        captured_stream.append(cmd_dict)
        return {"type": "result", "success": True,
                "summary": {"stages": "search→detail→toc→content"}}

    client._send_streaming = _mock_send_streaming

    source_json = '{"bookSourceName":"测试源","bookSourceUrl":"https://example.com"}'
    client.debug_book_source(source_json, "test_key")
    assert len(captured_stream) == 1
    cmd = captured_stream[0]
    assert cmd["cmd"] == "debugBookSource"
    assert cmd["sourceJson"] == source_json
    assert cmd["key"] == "test_key"


def test_debug_rss_source_command_format():
    """测试 debugRssSource (debug_rss) 命令请求格式。"""
    captured_stream = []
    client = RuleEngineClient()

    def _mock_send_streaming(cmd_dict, on_log=None, on_error=None, on_result=None):
        captured_stream.append(cmd_dict)
        return {"type": "result", "success": True,
                "summary": {"stages": "sort→content"}}

    client._send_streaming = _mock_send_streaming

    source_json = '{"sourceName":"测试RSS","sourceUrl":"https://rss.example.com"}'
    client.debug_rss_source(source_json, "keyword")
    assert len(captured_stream) == 1
    cmd = captured_stream[0]
    assert cmd["cmd"] == "debugRssSource"
    assert cmd["sourceJson"] == source_json
    assert cmd["key"] == "keyword"


def test_debug_book_source_callbacks():
    """测试 debug_book_source 的回调机制。"""
    client = RuleEngineClient()
    logs = []
    errors = []
    results = []

    def _mock_send_streaming(cmd_dict, on_log=None, on_error=None, on_result=None):
        if on_log:
            on_log(10, "搜索页日志", "<html>search</html>")
        if on_result:
            on_result(True, {"stages": "search→detail→toc→content"})
        return {"type": "result", "success": True,
                "summary": {"stages": "search→detail→toc→content"}}

    client._send_streaming = _mock_send_streaming

    result = client.debug_book_source(
        '{"bookSourceUrl":"https://x.com"}', "key",
        on_log=lambda s, m, h: logs.append((s, m, h)),
        on_error=lambda m, st, fs: errors.append((m, st, fs)),
        on_result=lambda suc, summ: results.append((suc, summ))
    )
    assert len(logs) == 1
    assert logs[0][0] == 10
    assert logs[0][1] == "搜索页日志"
    assert len(results) == 1
    assert results[0][0] is True
    assert result["success"] is True


# ==================== 响应解析测试 ====================

def test_send_server_not_running():
    """测试服务未启动时 _send 返回错误。"""
    client = RuleEngineClient()
    result = client._send({"cmd": "ping"})
    assert result["ok"] is False
    assert "not running" in result["error"].lower()


def test_send_streaming_server_not_running():
    """测试服务未启动时流式命令返回错误。"""
    client = RuleEngineClient()
    result = client._send_streaming({"cmd": "debugBookSource"})
    assert result["ok"] is False
    assert "not running" in result["error"].lower()


def test_is_alive_not_started():
    """测试未启动时 is_alive 返回 False。"""
    client = RuleEngineClient()
    assert client.is_alive() is False


def test_shutdown_without_start():
    """测试未启动时 shutdown 不报错。"""
    client = RuleEngineClient()
    client.shutdown()  # 不应抛异常


# ==================== 构造函数测试 ====================

def test_init_default_jar_path():
    """测试构造函数默认 jar_path 来自 config。"""
    client = RuleEngineClient()
    assert client.jar_path == config.jar_path
    assert client.timeout == 30
    assert client.process is None
    assert client.modules == []
    assert client.version == "unknown"


def test_init_custom_params():
    """测试构造函数自定义参数。"""
    client = RuleEngineClient(jar_path="/custom/path.jar", timeout=60)
    assert client.jar_path == "/custom/path.jar"
    assert client.timeout == 60


def test_find_jar_delegates_to_config():
    """测试 _find_jar 委托给 config。"""
    assert RuleEngineClient._find_jar() == config.jar_path


def test_find_java():
    """测试 _find_java 返回值类型正确。"""
    result = RuleEngineClient._find_java()
    assert result is None or isinstance(result, str)


# ==================== JAR 集成测试（优雅降级） ====================

def test_ping_with_jar():
    """JAR 可用时测试 ping 真实响应。JAR 不可用时跳过。"""
    if not (_jar_available() and _java_available()):
        print("  [SKIP] JAR 或 Java 不可用，跳过 ping 集成测试")
        return
    client = RuleEngineClient()
    try:
        client.start()
        result = client.ping()
        assert isinstance(result, dict)
        assert result.get("ok") is True, f"ping 失败: {result}"
    finally:
        client.shutdown()


def test_eval_js_with_jar():
    """JAR 可用时测试 eval_js 真实响应。JAR 不可用时跳过。"""
    if not (_jar_available() and _java_available()):
        print("  [SKIP] JAR 或 Java 不可用，跳过 eval_js 集成测试")
        return
    client = RuleEngineClient()
    try:
        client.start()
        result = client.eval_js("1 + 1")
        assert isinstance(result, dict)
        assert result.get("ok") is True or result.get("status") == "ok"
    finally:
        client.shutdown()


def test_start_jar_not_found():
    """测试 JAR 不存在时 start() 抛出 FileNotFoundError。"""
    client = RuleEngineClient(jar_path="/nonexistent/path.jar")
    try:
        client.start()
        assert False, "应抛出 FileNotFoundError 或 RuntimeError"
    except FileNotFoundError as e:
        assert "JAR not found" in str(e)
    except RuntimeError as e:
        # Java 不可用时会抛 RuntimeError
        assert "Java not found" in str(e) or "JAR" in str(e)


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
    print("RuleEngineClient 测试套件")
    print(f"{'='*60}\n")
    success = _run_all_tests()
    sys.exit(0 if success else 1)
