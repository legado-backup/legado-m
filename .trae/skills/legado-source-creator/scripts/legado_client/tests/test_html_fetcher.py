#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_fetcher 单元测试。

同时支持：
- `python test_html_fetcher.py` 独立运行
- `pytest test_html_fetcher.py` 运行

被测模块：utils/html_fetcher.py
"""
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.html_fetcher import FetchResult, HtmlFetcher


# ========== FetchResult ==========

def test_fetch_result_ok_true():
    """FetchResult html 非空时 ok=True。"""
    r = FetchResult(html="<html></html>", source="direct")
    assert r.ok is True


def test_fetch_result_ok_false():
    """FetchResult html 为 None 时 ok=False。"""
    r = FetchResult(html=None, source="failed")
    assert r.ok is False


def test_fetch_result_to_dict():
    """FetchResult.to_dict 返回正确字段。"""
    r = FetchResult(html="<html>", source="direct", cms_type="maccms", snapshot_date="2024-01-01", log=["log1"])
    d = r.to_dict()
    assert d["ok"] is True
    assert d["source"] == "direct"
    assert d["cms_type"] == "maccms"
    assert d["snapshot_date"] == "2024-01-01"
    assert d["html_length"] == 6
    assert d["log"] == ["log1"]


def test_fetch_result_to_json():
    """FetchResult.to_json 返回有效 JSON 字符串。"""
    r = FetchResult(html="<html>", source="direct")
    s = r.to_json()
    data = json.loads(s)
    assert data["ok"] is True
    assert data["html"] == "<html>"


def test_fetch_result_default_log_empty():
    """FetchResult 默认 log 为空列表。"""
    r = FetchResult(html="x", source="direct")
    assert r.log == []


# ========== HtmlFetcher 初始化 ==========

def test_html_fetcher_init_default():
    """HtmlFetcher 默认初始化。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        assert fetcher.ua is not None
        assert fetcher.timeout == 15
        assert fetcher._cache == {}


def test_html_fetcher_init_custom():
    """HtmlFetcher 自定义参数。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher(ua="CustomUA", headers={"X-Test": "1"}, timeout=30)
        assert fetcher.ua == "CustomUA"
        assert fetcher.timeout == 30
        assert fetcher._headers == {"X-Test": "1"}


def test_html_fetcher_no_requests_raises():
    """HtmlFetcher 在 requests=None 时抛 ImportError。"""
    with patch("utils.html_fetcher.requests", None):
        try:
            HtmlFetcher()
            assert False, "应抛出 ImportError"
        except ImportError:
            pass


# ========== _is_cf_challenge ==========

def test_is_cf_challenge_just_moment():
    """检测 'Just a moment' CF 特征。"""
    assert HtmlFetcher._is_cf_challenge("<html>Just a moment...</html>") is True


def test_is_cf_challenge_cf_chl_opt():
    """检测 cf_chl_opt 特征。"""
    assert HtmlFetcher._is_cf_challenge("<script>cf_chl_opt={}</script>") is True


def test_is_cf_challenge_challenge_platform():
    """检测 challenge-platform 特征。"""
    assert HtmlFetcher._is_cf_challenge('<script src="challenge-platform/js"></script>') is True


def test_is_cf_challenge_normal_html():
    """正常 HTML 不被误判为 CF。"""
    assert HtmlFetcher._is_cf_challenge("<html><body>正常内容</body></html>") is False


def test_is_cf_challenge_empty():
    """空字符串不是 CF。"""
    assert HtmlFetcher._is_cf_challenge("") is False


def test_is_cf_challenge_none():
    """None 不是 CF。"""
    assert HtmlFetcher._is_cf_challenge(None) is False


def test_is_cf_challenge_ray_id():
    """检测 Ray ID 特征。"""
    assert HtmlFetcher._is_cf_challenge("<div>Ray ID: abc123</div>") is True


# ========== _clean_wayback_toolbar ==========

def test_clean_wayback_toolbar_removes_insert():
    """清理 Wayback 工具栏插入代码。"""
    html = '<html><!-- BEGIN WAYBACK TOOLBAR INSERT --><div>toolbar</div><!-- END WAYBACK TOOLBAR INSERT --><body>content</body></html>'
    cleaned = HtmlFetcher._clean_wayback_toolbar(html)
    assert "WAYBACK TOOLBAR" not in cleaned
    assert "content" in cleaned


def test_clean_wayback_toolbar_removes_static():
    """清理 /web/_static/ 路径。"""
    html = '<script src="/web/_static/js/toolbar.js"></script><link href="/web/_static/css/style.css">'
    cleaned = HtmlFetcher._clean_wayback_toolbar(html)
    assert "/web/_static/" not in cleaned


def test_clean_wayback_toolbar_removes_timestamp():
    """清理 Wayback 时间戳前缀。"""
    html = '<a href="/web/20240101000000/https://example.com">link</a>'
    cleaned = HtmlFetcher._clean_wayback_toolbar(html)
    assert "/web/20240101000000/" not in cleaned
    assert "https://example.com" in cleaned


def test_clean_wayback_toolbar_empty():
    """空字符串清理后仍为空。"""
    assert HtmlFetcher._clean_wayback_toolbar("") == ""


def test_clean_wayback_toolbar_none():
    """None 清理后仍为 None。"""
    assert HtmlFetcher._clean_wayback_toolbar(None) is None


# ========== _clean_google_cache_header ==========

def test_clean_google_cache_header_removes_header():
    """清理 Google Cache 头部。"""
    html = '<div class="cache-header">Google Cache 提示</div><html>content</html>'
    cleaned = HtmlFetcher._clean_google_cache_header(html)
    assert "cache-header" not in cleaned
    assert "content" in cleaned


def test_clean_google_cache_header_empty():
    """空字符串清理后仍为空。"""
    assert HtmlFetcher._clean_google_cache_header("") == ""


# ========== 缓存测试 ==========

def test_cache_set_and_get():
    """缓存设置和获取。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        fetcher._set_cache("http://x.com", "direct", "<html>")
        result = fetcher._get_cache("http://x.com", "direct")
        assert result == "<html>"


def test_cache_get_miss():
    """缓存未命中返回 None。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        assert fetcher._get_cache("http://x.com", "direct") is None


def test_cache_expired():
    """缓存过期返回 None。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        # direct TTL = 5 分钟，模拟过期
        import time
        fetcher._set_cache("http://x.com", "direct", "<html>")
        # 手动修改时间戳为 10 分钟前
        key = ("http://x.com", "direct")
        html, _ = fetcher._cache[key]
        fetcher._cache[key] = (html, time.time() - 400)  # 400 秒前 > 300 秒 TTL
        assert fetcher._get_cache("http://x.com", "direct") is None


def test_cache_cms_sample_never_expires():
    """cms_sample 缓存永不过期。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        import time
        fetcher._set_cache("http://x.com", "cms_sample", "<html>")
        key = ("http://x.com", "cms_sample")
        html, _ = fetcher._cache[key]
        # 即使是很久以前设置的，cms_sample 也不过期
        fetcher._cache[key] = (html, time.time() - 999999)
        assert fetcher._get_cache("http://x.com", "cms_sample") == "<html>"


# ========== _resolve_cms_sample_path ==========

def test_resolve_cms_sample_path():
    """_resolve_cms_sample_path 返回正确路径。"""
    path = HtmlFetcher._resolve_cms_sample_path("maccms-v10")
    assert "maccms-v10" in path
    assert "cms-samples" in path
    assert path.endswith("list.html")


# ========== _detect_cms ==========

def test_detect_cms_maccms_url_path():
    """通过 URL 路径检测 maccms-v10。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        log = []
        result = fetcher._detect_cms("https://example.com/api.php/provide/vod/", log)
        assert result == "maccms-v10"


def test_detect_cms_wordpress_url_path():
    """通过 URL 路径检测 wordpress。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        result = fetcher._detect_cms("https://example.com/wp-content/themes/x")
        assert result == "wordpress"


def test_detect_cms_discuz_url_path():
    """通过 URL 路径检测 discuz。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        result = fetcher._detect_cms("https://example.com/forum.php")
        assert result == "discuz"


def test_detect_cms_dedecms_url_path():
    """通过 URL 路径检测 dedecms。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        result = fetcher._detect_cms("https://example.com/plus/view.php")
        assert result == "dedecms"


def test_detect_cms_no_match_returns_none():
    """无匹配 CMS 返回 None。"""
    with patch("utils.html_fetcher.requests", MagicMock()) as mock_req:
        mock_req.get.return_value.ok = False
        fetcher = HtmlFetcher()
        result = fetcher._detect_cms("https://example.com/unknown/path")
        assert result is None


# ========== fetch 主流程（mock 各步骤） ==========

def test_fetch_direct_success():
    """fetch direct 成功时直接返回。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        expected = FetchResult(html="<html>direct</html>", source="direct")
        with patch.object(fetcher, "_step_direct", return_value=expected) as mock_direct:
            result = fetcher.fetch("http://x.com")
            assert result.ok is True
            assert result.source == "direct"
            mock_direct.assert_called_once()


def test_fetch_fallback_to_wayback():
    """direct 失败时回退到 wayback。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        direct_result = FetchResult(html=None, source="direct")
        wayback_result = FetchResult(html="<html>wayback</html>", source="wayback")
        with patch.object(fetcher, "_step_direct", return_value=direct_result):
            with patch.object(fetcher, "_step_wayback", return_value=wayback_result) as mock_wayback:
                result = fetcher.fetch("http://x.com")
                assert result.source == "wayback"
                mock_wayback.assert_called_once()


def test_fetch_all_failed():
    """所有步骤失败返回 failed。"""
    with patch("utils.html_fetcher.requests", MagicMock()):
        fetcher = HtmlFetcher()
        fail = FetchResult(html=None, source="x")
        with patch.object(fetcher, "_step_direct", return_value=fail):
            with patch.object(fetcher, "_step_wayback", return_value=fail):
                with patch.object(fetcher, "_step_cms_sample", return_value=fail):
                    with patch.object(fetcher, "_step_google_cache", return_value=fail):
                        with patch.object(fetcher, "_step_playwright", return_value=fail):
                            result = fetcher.fetch("http://x.com")
                            assert result.ok is False
                            assert result.source == "failed"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
