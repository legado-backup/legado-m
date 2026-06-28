"""扫描 output/ 目录，解析并导入已有源文件。

递归扫描 output/book/ 和 output/rss/ 下的 .json 文件，
使用 source_parser 解析后通过 storage.repository 入库。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from legado_client.utils.config import config
from legado_client.utils.logger import get_logger
from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
from legado_client.storage.database import init_db, create_tables
from legado_client.storage.repository import bulk_upsert

logger = get_logger("legado_client.scanner")


async def scan_and_import(
    base_dir: Optional[Path] = None,
) -> dict[str, int]:
    """扫描 output/ 目录下的源文件并导入数据库。

    Args:
        base_dir: 基准目录，默认为 config.output_dir

    Returns:
        {"book": 导入数量, "rss": 导入数量}
    """
    output_dir = base_dir or config.output_dir
    if not output_dir.exists():
        logger.warning("output 目录不存在: %s", output_dir)
        return {"book": 0, "rss": 0}

    # 确保数据库已初始化
    ok = await init_db()
    if ok:
        await create_tables()
    else:
        logger.warning("数据库不可用，跳过导入")
        return {"book": 0, "rss": 0}

    all_sources: list[dict] = []

    # 扫描 book/ 目录
    book_dir = output_dir / "book"
    if book_dir.exists():
        book_sources = _scan_directory(book_dir, "book")
        all_sources.extend(book_sources)
        logger.info("扫描 book/ 目录: %d 个源", len(book_sources))

    # 扫描 rss/ 目录
    rss_dir = output_dir / "rss"
    if rss_dir.exists():
        rss_sources = _scan_directory(rss_dir, "rss")
        all_sources.extend(rss_sources)
        logger.info("扫描 rss/ 目录: %d 个源", len(rss_sources))

    if not all_sources:
        logger.info("未发现源文件")
        return {"book": 0, "rss": 0}

    # 去重后入库
    deduped = deduplicate_sources(all_sources)
    logger.info("去重后: %d 个源（原始 %d）", len(deduped), len(all_sources))

    new_count = await bulk_upsert(deduped)
    # 统计类型分布
    book_count = sum(1 for s in deduped if s.get("source_type") == "book")
    rss_count = len(deduped) - book_count
    logger.info("入库完成: 书源 %d, 订阅源 %d, 新增 %d", book_count, rss_count, new_count)
    return {"book": book_count, "rss": rss_count}


def _scan_directory(directory: Path, source_type: str) -> list[dict]:
    """递归扫描目录下的 .json 文件，解析返回标准化源字典列表。"""
    results: list[dict] = []
    for json_file in directory.rglob("*.json"):
        # 跳过 .gitkeep 等非源文件
        if json_file.name.startswith("."):
            continue
        try:
            raw = json_file.read_text(encoding="utf-8")
            parsed = parse_source_json(raw, source_type)
            if parsed:
                results.extend(parsed)
                logger.debug("解析文件: %s -> %d 个源", json_file.name, len(parsed))
            else:
                logger.warning("文件无有效源: %s", json_file)
        except Exception as e:
            logger.warning("解析文件失败 %s: %s", json_file, e)
    return results


def scan_and_import_sync(base_dir: Optional[Path] = None) -> dict[str, int]:
    """同步封装：扫描并导入。"""
    return asyncio.run(scan_and_import(base_dir))
