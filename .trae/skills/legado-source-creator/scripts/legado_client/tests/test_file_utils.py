#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""file_utils 单元测试。

同时支持：
- `python test_file_utils.py` 独立运行
- `pytest test_file_utils.py` 运行

被测模块：utils/file_utils.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.file_utils import (
    ensure_dir, read_json, write_json, read_text, write_text,
    load_source_object, detect_source_type, sanitize_source_json,
)


# ========== ensure_dir ==========

def test_ensure_dir_creates_nested():
    """ensure_dir 创建嵌套目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "a" / "b" / "c"
        result = ensure_dir(target)
        assert result.exists()
        assert result.is_dir()
        assert isinstance(result, Path)


def test_ensure_dir_idempotent():
    """ensure_dir 对已存在目录不报错。"""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "exists"
        target.mkdir()
        result = ensure_dir(target)
        assert result.exists()


def test_ensure_dir_accepts_string():
    """ensure_dir 接受字符串路径。"""
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "str_path")
        result = ensure_dir(target)
        assert result.exists()


# ========== read_json / write_json ==========

def test_write_then_read_json():
    """write_json 后 read_json 往返一致。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "data.json"
        data = {"name": "测试", "list": [1, 2, 3], "nested": {"a": True}}
        write_json(path, data)
        loaded = read_json(path)
        assert loaded == data


def test_write_json_creates_parent_dir():
    """write_json 自动创建父目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "dir" / "data.json"
        write_json(path, {"k": "v"})
        assert path.exists()


def test_write_json_chinese_not_escaped():
    """write_json 默认不转义中文字符。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cn.json"
        write_json(path, {"name": "中文测试"})
        content = read_text(path)
        assert "中文测试" in content
        assert "\\u" not in content


def test_read_json_file_not_found():
    """read_json 文件不存在抛 FileNotFoundError。"""
    try:
        read_json("/nonexistent/path/file.json")
        assert False, "应抛出 FileNotFoundError"
    except FileNotFoundError:
        pass


def test_read_json_invalid_json():
    """read_json 无效 JSON 抛 json.JSONDecodeError。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"
        write_text(path, "{invalid json content")
        try:
            read_json(path)
            assert False, "应抛出 JSONDecodeError"
        except json.JSONDecodeError:
            pass


# ========== read_text / write_text ==========

def test_write_then_read_text():
    """write_text 后 read_text 往返一致。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "text.txt"
        content = "Hello 世界\n第二行"
        write_text(path, content)
        assert read_text(path) == content


def test_write_text_creates_parent_dir():
    """write_text 自动创建父目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "deep" / "path" / "text.txt"
        write_text(path, "content")
        assert path.exists()


# ========== load_source_object ==========

def test_load_source_object_dict():
    """load_source_object 字典 JSON 原样返回。"""
    src = '{"bookSourceName": "test", "bookSourceUrl": "https://x.com"}'
    obj = load_source_object(src)
    assert obj["bookSourceName"] == "test"


def test_load_source_object_array_takes_first():
    """load_source_object 数组取首个元素。"""
    src = '[{"name": "first"}, {"name": "second"}]'
    obj = load_source_object(src)
    assert obj["name"] == "first"


def test_load_source_object_empty_array_returns_dict():
    """load_source_object 空数组返回空字典。"""
    src = '[]'
    obj = load_source_object(src)
    assert obj == {}


def test_load_source_object_invalid_json():
    """load_source_object 无效 JSON 抛 JSONDecodeError。"""
    try:
        load_source_object("{invalid")
        assert False, "应抛出 JSONDecodeError"
    except json.JSONDecodeError:
        pass


# ========== detect_source_type ==========

def test_detect_source_type_book_with_ruleSearch():
    """detect_source_type 含 ruleSearch 判定为 book。"""
    src = '{"ruleSearch": {"bookList": ".item"}}'
    assert detect_source_type(src) == "book"


def test_detect_source_type_book_with_bookSourceUrl():
    """detect_source_type 含 bookSourceUrl 判定为 book。"""
    src = '{"bookSourceUrl": "https://x.com"}'
    assert detect_source_type(src) == "book"


def test_detect_source_type_rss_with_ruleArticles():
    """detect_source_type 含 ruleArticles 判定为 rss。"""
    src = '{"ruleArticles": ".item"}'
    assert detect_source_type(src) == "rss"


def test_detect_source_type_rss_with_sourceUrl():
    """detect_source_type 含 sourceUrl 判定为 rss。"""
    src = '{"sourceUrl": "https://x.com/rss"}'
    assert detect_source_type(src) == "rss"


def test_detect_source_type_empty_array_defaults_book():
    """detect_source_type 空数组默认 book。"""
    assert detect_source_type("[]") == "book"


def test_detect_source_type_no_markers_defaults_book():
    """detect_source_type 无任何标记默认 book。"""
    src = '{"name": "unknown"}'
    assert detect_source_type(src) == "book"


def test_detect_source_type_array_takes_first():
    """detect_source_type 数组取首个元素判断。"""
    src = '[{"sourceUrl": "https://x.com/rss"}, {"bookSourceUrl": "https://y.com"}]'
    assert detect_source_type(src) == "rss"


# ========== sanitize_source_json (None 序列化 bug 修复) ==========

def test_sanitize_dict_top_level_none():
    """dict 顶层 None 值替换为空字符串。"""
    result = sanitize_source_json({"a": None, "b": 1})
    assert result == {"a": "", "b": 1}


def test_sanitize_nested_dict_none():
    """嵌套 dict 中 None 值递归替换。"""
    result = sanitize_source_json({"outer": {"inner": None, "keep": 2}})
    assert result == {"outer": {"inner": "", "keep": 2}}


def test_sanitize_list_none():
    """list 中 None 值替换为空字符串。"""
    result = sanitize_source_json([None, 1, "text"])
    assert result == ["", 1, "text"]


def test_sanitize_list_of_dict_none():
    """list 中 dict 的 None 值递归替换。"""
    result = sanitize_source_json([{"x": None}, {"y": None}])
    assert result == [{"x": ""}, {"y": ""}]


def test_sanitize_none_input_returns_empty_string():
    """顶层 None 输入返回空字符串。"""
    assert sanitize_source_json(None) == ""


def test_sanitize_preserves_falsy_values():
    """falsy 但非 None 的值不被替换（False / 0 / [] / {}）。"""
    result = sanitize_source_json({
        "f": False, "z": 0, "empty_list": [], "empty_dict": {}, "none_val": None
    })
    assert result == {
        "f": False, "z": 0, "empty_list": [], "empty_dict": {}, "none_val": ""
    }


def test_sanitize_preserves_string_values():
    """非 None 字符串原样保留（包括空字符串）。"""
    result = sanitize_source_json({"name": "test", "empty": "", "none": None})
    assert result == {"name": "test", "empty": "", "none": ""}


def test_sanitize_deeply_nested():
    """深层嵌套结构递归处理。"""
    data = {"a": {"b": {"c": {"d": None, "e": [None, 1, {"f": None}]}}}}
    result = sanitize_source_json(data)
    assert result == {"a": {"b": {"c": {"d": "", "e": ["", 1, {"f": ""}]}}}}


def test_sanitize_json_dumps_no_none_string():
    """端到端验证：sanitize 后 json.dumps 输出不含字符串 'None'。

    这是 bug 修复的核心断言：Python None 不应被序列化为 "None" 字符串，
    否则 Legado Rss.kt:64 会将其作为 JS 代码执行触发 ReferenceError。
    """
    source_obj = {
        "sourceUrl": "https://example.com",
        "loginCheckJs": None,
        "ruleArticles": None,
        "header": None,
    }
    sanitized = sanitize_source_json(source_obj)
    json_str = json.dumps(sanitized, ensure_ascii=False)
    assert "None" not in json_str
    assert "null" not in json_str  # 空字符串而非 null


def test_sanitize_simulates_real_source_object():
    """模拟真实源对象：混合 None 与有效值。"""
    real_source = {
        "bookSourceName": "测试源",
        "bookSourceUrl": "https://example.com",
        "loginUrl": None,
        "loginCheckJs": None,
        "customOrder": 0,
        "enabled": True,
        "ruleSearch": {"bookList": ".item", "name": ".title"},
        "ruleContent": None,
    }
    result = sanitize_source_json(real_source)
    assert result["bookSourceName"] == "测试源"
    assert result["loginUrl"] == ""
    assert result["loginCheckJs"] == ""
    assert result["customOrder"] == 0
    assert result["enabled"] is True
    assert result["ruleSearch"]["bookList"] == ".item"
    assert result["ruleContent"] == ""


def test_sanitize_idempotent():
    """sanitize 幂等性：对已 sanitize 的对象再次 sanitize 结果不变。"""
    data = {"a": None, "b": 1}
    once = sanitize_source_json(data)
    twice = sanitize_source_json(once)
    assert once == twice


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
