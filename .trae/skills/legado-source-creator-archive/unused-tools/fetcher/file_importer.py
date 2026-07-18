"""本地文件导入 + 目录扫描导入。

支持：
- 单个 JSON 文件导入
- 目录递归扫描导入
- 使用 source_parser 解析后入库
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
from legado_client.storage.repository import bulk_upsert
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.file_importer")


async def import_from_file(
    path: str | Path,
    source_type: str = "book",
) -> dict:
    """从本地 JSON 文件导入源。

    Args:
        path: JSON 文件路径
        source_type: "book" 或 "rss"

    Returns:
        {"total": 总数, "imported": 新增数, "errors": 错误数}
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.error("文件不存在: %s", file_path)
        return {"total": 0, "imported": 0, "errors": 1}

    if not file_path.is_file():
        logger.error("路径不是文件: %s", file_path)
        return {"total": 0, "imported": 0, "errors": 1}

    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("文件读取失败 %s: %s", file_path, e)
        return {"total": 0, "imported": 0, "errors": 1}

    return await _import_json(raw, source_type, source=str(file_path))


async def import_from_directory(
    directory: str | Path,
    source_type: str = "book",
    pattern: str = "*.json",
    recursive: bool = True,
) -> dict:
    """从目录扫描并导入 JSON 文件。

    Args:
        directory: 目录路径
        source_type: "book" 或 "rss"
        pattern: 文件名匹配模式
        recursive: 是否递归子目录

    Returns:
        {"total": 总数, "imported": 新增数, "errors": 错误数, "files": 文件数}
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error("目录不存在: %s", dir_path)
        return {"total": 0, "imported": 0, "errors": 1, "files": 0}

    if not dir_path.is_dir():
        logger.error("路径不是目录: %s", dir_path)
        return {"total": 0, "imported": 0, "errors": 1, "files": 0}

    # 收集文件
    if recursive:
        files = list(dir_path.rglob(pattern))
    else:
        files = list(dir_path.glob(pattern))

    # 过滤隐藏文件
    files = [f for f in files if not f.name.startswith(".")]

    if not files:
        logger.info("目录 %s 中无匹配文件 (%s)", dir_path, pattern)
        return {"total": 0, "imported": 0, "errors": 0, "files": 0}

    logger.info("目录 %s: 找到 %d 个文件", dir_path, len(files))

    result = {"total": 0, "imported": 0, "errors": 0, "files": len(files)}
    for file_path in files:
        sub = await import_from_file(file_path, source_type)
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
    source: str = "",
) -> dict:
    """解析 JSON 字符串并入库。"""
    try:
        parsed = parse_source_json(raw_json, source_type)
    except Exception as e:
        logger.error("JSON 解析失败 %s: %s", source, e)
        return {"total": 0, "imported": 0, "errors": 1}

    if not parsed:
        logger.warning("文件 %s 解析结果为空", source)
        return {"total": 0, "imported": 0, "errors": 0}

    deduped = deduplicate_sources(parsed)
    try:
        imported = await bulk_upsert(deduped)
    except Exception as e:
        logger.error("入库失败 %s: %s", source, e)
        return {"total": len(deduped), "imported": 0, "errors": 1}

    logger.info("文件 %s: 解析 %d 个源，去重 %d，新增 %d",
                source, len(parsed), len(deduped), imported)
    return {"total": len(deduped), "imported": imported, "errors": 0}
