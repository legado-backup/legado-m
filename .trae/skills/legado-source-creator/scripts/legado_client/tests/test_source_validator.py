#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SourceValidator 单元测试。

同时支持：
- `python test_source_validator.py` 独立运行
- `pytest test_source_validator.py` 运行

被测模块：analyzer/source_validator.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzer.source_validator import SourceValidator, validate_source


# ========== 正常用例 ==========

def test_valid_book_source_complete():
    """完整合法书源通过校验（无 ERROR）。"""
    src = {
        "bookSourceName": "测试书源",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "searchUrl": "https://example.com/search?q={{key}}",
        "ruleSearch": {"bookList": ".book-item"},
        "ruleBookInfo": {"name": "h1.title", "author": ".author"},
        "ruleToc": {"chapterList": ".chap", "chapterName": "a", "chapterUrl": "a@href"},
        "ruleContent": {"content": "#content"},
        "exploreUrl": "https://example.com/explore",
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is True
    assert result["errors"] == []


def test_valid_rss_source_complete():
    """完整合法订阅源通过校验。"""
    src = {
        "sourceName": "测试订阅源",
        "sourceUrl": "https://example.com/rss",
        "type": 0,
        "ruleArticles": ".item",
        "ruleTitle": ".title",
        "ruleLink": "a@href",
        "ruleContent": ".content",
        "ruleNextPage": "a.next@href",
    }
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_source_function():
    """模块级便捷函数与类方法结果一致。"""
    src = {
        "bookSourceName": "便捷函数测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
    }
    r1 = validate_source(src, "book")
    r2 = SourceValidator(src, "book").validate()
    assert r1 == r2


# ========== 边界用例 ==========

def test_empty_source_object():
    """空对象：book 触发 3 个 ERROR（name/url/type）。"""
    result = SourceValidator({}, "book").validate()
    assert result["valid"] is False
    assert len(result["errors"]) == 3


def test_none_source_object():
    """None 对象：不抛异常，触发 ERROR。"""
    result = SourceValidator(None, "book").validate()
    assert result["valid"] is False
    assert len(result["errors"]) == 3


def test_empty_string_fields():
    """空字符串/纯空白字段视为缺失。"""
    src = {
        "bookSourceName": "   ",
        "bookSourceUrl": "",
        "bookSourceType": 0,
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is False
    fields = [e["field"] for e in result["errors"]]
    assert "bookSourceName" in fields
    assert "bookSourceUrl" in fields


def test_header_as_dict():
    """header 为 dict 时通过 json_optional 校验。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "header": {"User-Agent": "test"},
    }
    result = SourceValidator(src, "book").validate()
    header_warns = [w for w in result["warnings"] if w["field"] == "header"]
    assert header_warns == []


def test_header_as_json_string():
    """header 为合法 JSON 字符串时通过校验。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "header": '{"User-Agent": "test"}',
    }
    result = SourceValidator(src, "book").validate()
    header_warns = [w for w in result["warnings"] if w["field"] == "header"]
    assert header_warns == []


def test_optional_fields_empty_pass():
    """可选字段为空时通过校验（loginUrl/header/loginUi）。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "loginUrl": "",
        "header": "",
        "loginUi": "",
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is True


def test_rss_enableJs_optional_valid():
    """enableJs 有值且合法（1）。"""
    src = {
        "sourceName": "测试",
        "sourceUrl": "https://example.com",
        "type": 0,
        "enableJs": 1,
    }
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is True


def test_book_all_type_values_valid():
    """bookSourceType 四个合法枚举值 0/1/2/3 均通过。"""
    for t in [0, 1, 2, 3]:
        src = {
            "bookSourceName": "测试",
            "bookSourceUrl": "https://example.com",
            "bookSourceType": t,
        }
        result = SourceValidator(src, "book").validate()
        assert result["valid"] is True, f"type={t} 应通过"


# ========== 异常用例 ==========

def test_book_missing_name_error():
    """缺 bookSourceName 触发 ERROR。"""
    src = {"bookSourceUrl": "https://example.com", "bookSourceType": 0}
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is False
    assert any(e["field"] == "bookSourceName" for e in result["errors"])


def test_book_invalid_url_error():
    """bookSourceUrl 非法（不以 http:// 或 https:// 开头）。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "ftp://example.com",
        "bookSourceType": 0,
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is False
    assert any(e["field"] == "bookSourceUrl" for e in result["errors"])


def test_book_invalid_type_error():
    """bookSourceType 非法（不在 0/1/2/3）。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 5,
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is False
    assert any(e["field"] == "bookSourceType" for e in result["errors"])


def test_rss_missing_name_error():
    """缺 sourceName 触发 ERROR。"""
    src = {"sourceUrl": "https://example.com", "type": 0}
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is False
    assert any(e["field"] == "sourceName" for e in result["errors"])


def test_rss_invalid_url_error():
    """sourceUrl 非法。"""
    src = {"sourceName": "测试", "sourceUrl": "not-a-url", "type": 0}
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is False
    assert any(e["field"] == "sourceUrl" for e in result["errors"])


def test_rss_invalid_type_error():
    """type 非法（不在 0/1）。"""
    src = {"sourceName": "测试", "sourceUrl": "https://example.com", "type": 2}
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is False
    assert any(e["field"] == "type" for e in result["errors"])


def test_book_invalid_header_json():
    """header 为非法 JSON 字符串触发 WARN（不影响 valid）。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "header": "{not json}",
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is True
    assert any(w["field"] == "header" for w in result["warnings"])


def test_book_invalid_login_url():
    """loginUrl 非法 URL 触发 WARN。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "loginUrl": "not-a-url",
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is True
    assert any(w["field"] == "loginUrl" for w in result["warnings"])


def test_nested_field_missing():
    """嵌套字段缺失（ruleSearch.bookList）触发 WARN 而非崩溃。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": "https://example.com",
        "bookSourceType": 0,
        "ruleSearch": {},  # bookList 缺失
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is True
    assert any(w["field"] == "ruleSearch.bookList" for w in result["warnings"])


def test_rss_invalid_enableJs():
    """enableJs 非法值触发 WARN。"""
    src = {
        "sourceName": "测试",
        "sourceUrl": "https://example.com",
        "type": 0,
        "enableJs": 5,
    }
    result = SourceValidator(src, "rss").validate()
    assert result["valid"] is True
    assert any(w["field"] == "enableJs" for w in result["warnings"])


def test_invalid_source_type_uses_rss_rules():
    """未知 source_type 走 else 分支使用 RSS 规则。"""
    src = {"sourceName": "x", "sourceUrl": "https://e.com", "type": 0}
    result = SourceValidator(src, "unknown").validate()
    # RSS 规则 ERROR 字段为 sourceName/sourceUrl/type，全部合法
    assert result["valid"] is True


def test_book_url_not_string_error():
    """bookSourceUrl 类型错误（非字符串）触发 ERROR。"""
    src = {
        "bookSourceName": "测试",
        "bookSourceUrl": 12345,
        "bookSourceType": 0,
    }
    result = SourceValidator(src, "book").validate()
    assert result["valid"] is False
    assert any(e["field"] == "bookSourceUrl" for e in result["errors"])


# ========== main 入口 ==========

if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n总计: {len(tests)} | 通过: {passed} | 失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
