"""URL 直接导入 + GitHub 仓库 URL 导入。

支持：
- 直接 JSON 文件 URL（如 raw.githubusercontent.com）
- GitHub 仓库 URL（自动拼接 raw 路径）
- 普通 HTTP URL（下载后解析）
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from legado_client.fetcher.http_client import shared_client
from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
from legado_client.storage.repository import bulk_upsert
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.url_importer")


async def import_from_url(
    url: str,
    source_type: str = "book",
) -> dict:
    """从 URL 下载并导入源 JSON。

    Args:
        url: JSON 文件 URL 或 GitHub 仓库 URL
        source_type: "book" 或 "rss"

    Returns:
        {"total": 总数, "imported": 新增数, "errors": 错误数}
    """
    # GitHub 仓库 URL 转换
    actual_url = _resolve_github_url(url)

    try:
        content = await shared_client.get_text(actual_url)
    except Exception as e:
        logger.error("URL 下载失败 %s: %s", actual_url, e)
        return {"total": 0, "imported": 0, "errors": 1}

    return await _import_json(content, source_type, url=actual_url)


async def import_from_urls(
    urls: list[str],
    source_type: str = "book",
) -> dict:
    """批量 URL 导入。

    Returns:
        {"total": 总数, "imported": 新增数, "errors": 错误数}
    """
    result = {"total": 0, "imported": 0, "errors": 0}
    for url in urls:
        sub = await import_from_url(url, source_type)
        result["total"] += sub["total"]
        result["imported"] += sub["imported"]
        result["errors"] += sub["errors"]
    return result


# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------

async def _import_json(
    raw_json: str,
    source_type: str,
    url: str = "",
) -> dict:
    """解析 JSON 字符串并入库。"""
    try:
        parsed = parse_source_json(raw_json, source_type)
    except Exception as e:
        logger.error("JSON 解析失败 %s: %s", url, e)
        return {"total": 0, "imported": 0, "errors": 1}

    if not parsed:
        logger.warning("URL %s 解析结果为空", url)
        return {"total": 0, "imported": 0, "errors": 0}

    deduped = deduplicate_sources(parsed)
    try:
        imported = await bulk_upsert(deduped)
    except Exception as e:
        logger.error("入库失败 %s: %s", url, e)
        return {"total": len(deduped), "imported": 0, "errors": 1}

    logger.info("URL %s: 解析 %d 个源，去重 %d，新增 %d",
                url, len(parsed), len(deduped), imported)
    return {"total": len(deduped), "imported": imported, "errors": 0}


def _resolve_github_url(url: str) -> str:
    """GitHub 仓库 URL 转换为 raw 文件 URL。

    支持格式：
    - https://github.com/{owner}/{repo}/blob/{branch}/{path}
    - https://github.com/{owner}/{repo}/tree/{branch}/{path}（目录，不转换）
    - https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}（已转换，原样返回）

    转换规则：github.com → raw.githubusercontent.com，blob/ 去掉
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""

    # 已经是 raw URL，直接返回
    if host == "raw.githubusercontent.com":
        return url

    # 非 github.com，原样返回
    if host != "github.com":
        return url

    path = parsed.path
    # /{owner}/{repo}/blob/{branch}/{path} → /{owner}/{repo}/{branch}/{path}
    match = re.match(r"^/([^/]+)/([^/]+)/blob/(.+)$", path)
    if match:
        owner, repo, rest = match.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"

    # tree/ 开头的是目录，无法直接下载
    if "/tree/" in path:
        logger.warning("GitHub 目录 URL 无法直接下载: %s", url)

    return url
