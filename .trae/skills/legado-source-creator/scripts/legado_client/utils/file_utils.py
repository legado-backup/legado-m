#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件工具：路径处理、JSON 读写。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional, Union


def ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在，不存在则创建。

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Union[str, Path], encoding: str = "utf-8") -> Any:
    """读取 JSON 文件。

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        解析后的 Python 对象

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 解析失败
    """
    with open(path, "r", encoding=encoding) as f:
        return json.load(f)


def write_json(path: Union[str, Path], data: Any, encoding: str = "utf-8",
               indent: int = 2, ensure_ascii: bool = False) -> None:
    """写入 JSON 文件。

    Args:
        path: 文件路径
        data: 要写入的数据
        encoding: 文件编码
        indent: 缩进格数
        ensure_ascii: 是否转义非 ASCII 字符
    """
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)


def read_text(path: Union[str, Path], encoding: str = "utf-8") -> str:
    """读取文本文件。

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容字符串
    """
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def write_text(path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
    """写入文本文件。

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 文件编码
    """
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


def load_source_object(source_json: str) -> dict:
    """从源 JSON 字符串加载为字典，处理数组形式。

    JVM 期望单个对象 JSON，若源文件为数组取首个元素。

    Args:
        source_json: 源 JSON 字符串

    Returns:
        源对象字典

    Raises:
        json.JSONDecodeError: JSON 解析失败
    """
    obj = json.loads(source_json)
    if isinstance(obj, list):
        obj = obj[0] if obj else {}
    return obj


def detect_source_type(source_json: str) -> str:
    """检测源类型: book 或 rss。

    Args:
        source_json: 源 JSON 字符串

    Returns:
        "book" 或 "rss"
    """
    obj = json.loads(source_json)
    if isinstance(obj, list):
        if not obj:
            return "book"
        obj = obj[0]
    if "ruleSearch" in obj or "bookSourceUrl" in obj:
        return "book"
    if "ruleArticles" in obj or "sourceUrl" in obj:
        return "rss"
    return "book"


def sanitize_source_json(obj: Any) -> Any:
    """递归过滤 None 值，避免序列化为字符串 "None" 触发 Rss.kt:64 ReferenceError。

    Bug 背景（2026-07-17 真机测试发现）：
        Python `json.dumps({"loginCheckJs": None})` 输出 `"loginCheckJs": null`，
        但若字段值被先 str() 再序列化则变成 `"loginCheckJs": "None"`，
        Legado `Rss.kt:64` 直接 eval 该字符串作为 JS 代码 → ReferenceError: None is not defined。

    处理规则：
        - None → 空字符串 ''（在 JS 中是 falsy，不会被当 JS 代码执行）
        - dict / list 递归处理
        - 保留 False / 0 / [] / {} 等有效 falsy 值（仅 None 被替换）

    Args:
        obj: 任意 Python 对象（dict / list / 标量）

    Returns:
        过滤后的对象，结构相同但所有 None 值替换为空字符串

    Examples:
        >>> sanitize_source_json({"a": None, "b": 1, "c": {"d": None}})
        {'a': '', 'b': 1, 'c': {'d': ''}}
        >>> sanitize_source_json([None, 1, {"x": None}])
        ['', 1, {'x': ''}]
        >>> sanitize_source_json(None)
        ''
    """
    if obj is None:
        return ''
    if isinstance(obj, dict):
        return {k: sanitize_source_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_source_json(item) for item in obj]
    return obj
