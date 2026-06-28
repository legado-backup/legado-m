#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_html 单元测试。

同时支持：
- `python test_fetch_html.py` 独立运行
- `pytest test_fetch_html.py` 运行

被测模块：utils/fetch_html.py（Playwright HTML 获取脚本）

注意：Playwright 是可选依赖，测试通过 mock 模拟，不依赖真实浏览器。
"""
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.fetch_html import (
    check_playwright, detect_cf_challenge, wait_cf_challenge,
    export_cookies, fetch_html,
)


# ========== check_playwright ==========

def test_check_playwright_not_installed():
    """Playwright 未安装时返回 False。"""
    with patch.dict(sys.modules, {"playwright.sync_api": None}):
        with patch("builtins.__import__", side_effect=ImportError):
            result = check_playwright()
            assert result is False


def test_check_playwright_installed_and_working():
    """Playwright 已安装且 Chromium 可用时返回 True。"""
    mock_sync_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser
    mock_sync_playwright.return_value.__enter__.return_value = mock_p

    with patch("playwright.sync_api.sync_playwright", mock_sync_playwright):
        result = check_playwright()
        assert result is True
        mock_browser.close.assert_called_once()


def test_check_playwright_installed_but_chromium_missing():
    """Playwright 已安装但 Chromium 不可用时返回 False。"""
    mock_sync_playwright = MagicMock()
    mock_p = MagicMock()
    mock_p.chromium.launch.side_effect = Exception("Chromium not found")
    mock_sync_playwright.return_value.__enter__.return_value = mock_p

    with patch("playwright.sync_api.sync_playwright", mock_sync_playwright):
        result = check_playwright()
        assert result is False


# ========== detect_cf_challenge ==========

def test_detect_cf_challenge_title_just_moment():
    """页面标题含 'Just a moment' 检测为 CF。"""
    page = MagicMock()
    page.title.return_value = "Just a moment..."
    page.evaluate.return_value = False
    assert detect_cf_challenge(page) is True


def test_detect_cf_challenge_title_cloudflare():
    """页面标题含 'Cloudflare' 检测为 CF。"""
    page = MagicMock()
    page.title.return_value = "Cloudflare | Verify"
    page.evaluate.return_value = False
    assert detect_cf_challenge(page) is True


def test_detect_cf_challenge_cf_var():
    """cf_chl_opt 变量存在检测为 CF。"""
    page = MagicMock()
    page.title.side_effect = Exception("no title")
    # 第一次 evaluate 是 cf_chl_opt 检测
    page.evaluate.side_effect = [True, False, False]
    assert detect_cf_challenge(page) is True


def test_detect_cf_challenge_cf_script():
    """challenge-platform 脚本存在检测为 CF。"""
    page = MagicMock()
    page.title.side_effect = Exception("no title")
    page.evaluate.side_effect = [False, True, False]
    assert detect_cf_challenge(page) is True


def test_detect_cf_challenge_turnstile():
    """Turnstile iframe 检测返回 'turnstile'。"""
    page = MagicMock()
    page.title.side_effect = Exception("no title")
    page.evaluate.side_effect = [False, False, True]
    assert detect_cf_challenge(page) == "turnstile"


def test_detect_cf_challenge_no_cf():
    """无 CF 特征返回 False。"""
    page = MagicMock()
    page.title.return_value = "正常页面"
    page.evaluate.return_value = False
    assert detect_cf_challenge(page) is False


def test_detect_cf_challenge_all_exceptions():
    """所有检测都异常时返回 False。"""
    page = MagicMock()
    page.title.side_effect = Exception("err")
    page.evaluate.side_effect = [Exception("err"), Exception("err"), Exception("err")]
    assert detect_cf_challenge(page) is False


# ========== wait_cf_challenge ==========

def test_wait_cf_challenge_immediate_pass():
    """无 CF 挑战时立即返回 True。"""
    page = MagicMock()
    # time.time() 会被多次调用：start=0, while判断=1, elapsed=2
    time_values = iter([0, 1, 2])
    with patch("utils.fetch_html.detect_cf_challenge", return_value=False):
        with patch("utils.fetch_html.time.time", side_effect=lambda: next(time_values)):
            result = wait_cf_challenge(page, timeout=30)
            assert result is True


def test_wait_cf_challenge_turnstile():
    """检测到 Turnstile 返回 'turnstile'。"""
    page = MagicMock()
    with patch("utils.fetch_html.detect_cf_challenge", return_value="turnstile"):
        result = wait_cf_challenge(page, timeout=5)
        assert result == "turnstile"


def test_wait_cf_challenge_timeout():
    """CF 验证超时返回 False。"""
    page = MagicMock()
    # 模拟时间递增超过 timeout
    time_counter = [0]
    def mock_time():
        time_counter[0] += 1
        return time_counter[0]
    with patch("utils.fetch_html.detect_cf_challenge", return_value=True):
        with patch("utils.fetch_html.time.time", side_effect=mock_time):
            with patch("utils.fetch_html.time.sleep"):
                result = wait_cf_challenge(page, timeout=5)
                assert result is False


def test_wait_cf_challenge_pass_after_delay():
    """CF 验证延迟通过返回 True。"""
    page = MagicMock()
    # 第一次检测 CF=True，第二次通过=False
    cf_results = iter([True, False])
    # time.time: start=0, while=1, sleep后while=2, elapsed=3
    time_values = iter([0, 1, 2, 3])
    with patch("utils.fetch_html.detect_cf_challenge", side_effect=lambda *args, **kwargs: next(cf_results)):
        with patch("utils.fetch_html.time.time", side_effect=lambda: next(time_values)):
            with patch("utils.fetch_html.time.sleep"):
                result = wait_cf_challenge(page, timeout=30)
                assert result is True


# ========== export_cookies ==========

def test_export_cookies_writes_json():
    """export_cookies 写入 JSON 文件。"""
    context = MagicMock()
    context.cookies.return_value = [
        {"name": "session", "value": "abc", "domain": ".example.com", "path": "/",
         "expires": 1234, "httpOnly": True, "secure": True, "sameSite": "Strict"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "cookies.json")
        export_cookies(context, out_path)
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "session"
        assert data[0]["value"] == "abc"


def test_export_cookies_empty():
    """export_cookies 空 Cookie 列表。"""
    context = MagicMock()
    context.cookies.return_value = []
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "empty.json")
        export_cookies(context, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == []


def test_export_cookies_missing_fields():
    """export_cookies 缺失字段使用默认值。"""
    context = MagicMock()
    context.cookies.return_value = [{"name": "x"}]  # 只有 name
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "partial.json")
        export_cookies(context, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["value"] == ""
        assert data[0]["path"] == "/"
        assert data[0]["httpOnly"] is False


# ========== fetch_html 主函数 ==========

def test_fetch_html_playwright_not_available():
    """Playwright 不可用时 sys.exit(1)。"""
    with patch("utils.fetch_html.check_playwright", return_value=False):
        try:
            fetch_html("http://x.com", "/tmp/out.html")
            assert False, "应调用 sys.exit"
        except SystemExit as e:
            assert e.code == 1


def test_fetch_html_success():
    """fetch_html 成功获取并保存 HTML。"""
    mock_page = MagicMock()
    mock_page.content.return_value = "<html>rendered</html>"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_sync = MagicMock()
    mock_sync.return_value.__enter__.return_value = mock_p

    with patch("utils.fetch_html.check_playwright", return_value=True):
        with patch("playwright.sync_api.sync_playwright", mock_sync):
            with tempfile.TemporaryDirectory() as tmp:
                out_path = os.path.join(tmp, "out.html")
                fetch_html("http://x.com", out_path)
                assert os.path.exists(out_path)
                with open(out_path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert content == "<html>rendered</html>"


def test_fetch_html_with_wait_cf():
    """fetch_html 带 --wait-cf 参数调用 wait_cf_challenge。"""
    mock_page = MagicMock()
    mock_page.content.return_value = "<html>after cf</html>"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_sync = MagicMock()
    mock_sync.return_value.__enter__.return_value = mock_p

    with patch("utils.fetch_html.check_playwright", return_value=True):
        with patch("playwright.sync_api.sync_playwright", mock_sync):
            with patch("utils.fetch_html.wait_cf_challenge", return_value=True) as mock_wait:
                with tempfile.TemporaryDirectory() as tmp:
                    out_path = os.path.join(tmp, "out.html")
                    fetch_html("http://x.com", out_path, wait_cf=True)
                    mock_wait.assert_called_once()


def test_fetch_html_navigation_error():
    """fetch_html 导航异常时 sys.exit(1)。"""
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("net::ERR_CONNECTION_REFUSED")
    mock_page.content.return_value = ""  # 回退也失败
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_sync = MagicMock()
    mock_sync.return_value.__enter__.return_value = mock_p

    with patch("utils.fetch_html.check_playwright", return_value=True):
        with patch("playwright.sync_api.sync_playwright", mock_sync):
            try:
                fetch_html("http://x.com", "/tmp/err.html")
                assert False, "应调用 sys.exit"
            except SystemExit as e:
                assert e.code == 1


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
