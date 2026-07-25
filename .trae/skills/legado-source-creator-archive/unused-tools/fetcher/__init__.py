"""源文件获取与解析模块。

统一 fetch() 调度接口，支持四种渠道：
- yckceo: 从 yckceo.com 爬取书源/订阅源合集
- url: 从 URL 直接导入 JSON
- file: 从本地文件或目录导入
- legado: 从 Legado 真机拉取源数据
"""
from __future__ import annotations

from typing import Any

from legado_client.fetcher import yckceo_fetcher
from legado_client.fetcher import url_importer
from legado_client.fetcher import file_importer
from legado_client.fetcher import legado_sync

__all__ = [
    "fetch",
    "yckceo_fetcher",
    "url_importer",
    "file_importer",
    "legado_sync",
]


async def fetch(
    source_type: str = "book",
    channel: str = "yckceo",
    **kwargs: Any,
) -> dict:
    """统一获取调度接口。

    Args:
        source_type: "book" 或 "rss"
        channel: 获取渠道
            - "yckceo": yckceo.com 合集爬取
            - "url": URL 直接导入（需传 url 参数）
            - "file": 本地文件导入（需传 path 参数）
            - "legado": Legado 真机拉取（需传 host/port 参数）
        **kwargs: 各渠道的额外参数

    Returns:
        渠道特定的结果字典，通常包含 total/imported/errors 等字段

    Raises:
        ValueError: 未知渠道
    """
    if channel == "yckceo":
        return await yckceo_fetcher.fetch_all(source_type, **kwargs)
    elif channel == "url":
        url = kwargs.get("url")
        if not url:
            raise ValueError("url 渠道必须传入 url 参数")
        return await url_importer.import_from_url(url, source_type)
    elif channel == "file":
        path = kwargs.get("path")
        if not path:
            raise ValueError("file 渠道必须传入 path 参数")
        directory = kwargs.get("directory", False)
        if directory:
            return await file_importer.import_from_directory(path, source_type)
        return await file_importer.import_from_file(path, source_type)
    elif channel == "legado":
        return await legado_sync.pull_from_device(source_type, **kwargs)
    else:
        raise ValueError(f"未知渠道: {channel}")
