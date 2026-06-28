#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""异步 CRUD 仓储层：Source / Collection / DebugResult / DeviceConfig。

使用前需先调用 init_db() 完成数据库初始化。
所有方法通过 get_session_factory() 获取会话工厂。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import delete, func, select, update

from legado_client.storage.database import get_session_factory
from legado_client.storage.models import DebugResult, DeviceConfig, Source
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.repository")


def _extract_domain_key(url: str) -> str:
    """从 URL 提取标准化域名作为 domain_key。"""
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        return (parsed.hostname or url).lower()
    except Exception:
        return url.lower()


def _map_source_data(data: dict[str, Any]) -> dict[str, Any]:
    """将原始源 JSON 字段映射到 Source 列字段。

    同时计算 has_login 和 domain_key。
    """
    def _text(val: Any) -> Optional[str]:
        """确保 Text 列的值是字符串（dict/list 自动序列化）。"""
        if val is None:
            return None
        if isinstance(val, str):
            return val
        return json.dumps(val, ensure_ascii=False)

    def _bool(val: Any) -> bool:
        """确保布尔值：处理 "true"/"false" 字符串。"""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    source_type = data.get("source_type", "book")
    is_book = source_type == "book"

    # 通用字段映射
    mapping: dict[str, Any] = {
        "source_type": source_type,
        "source_url": data.get("bookSourceUrl" if is_book else "sourceUrl", ""),
        "source_name": data.get("bookSourceName" if is_book else "sourceName", ""),
        "source_group": data.get("bookSourceGroup" if is_book else "sourceGroup"),
        "enabled": _bool(data.get("enabled", True)),
        "enabled_explore": _bool(data.get("enabledExplore", True)) if is_book else None,
        "login_url": data.get("loginUrl"),
        "login_check_js": _text(data.get("loginCheckJs")),
        "login_ui": _text(data.get("loginUi")),
        "search_url": _text(data.get("searchUrl")),
        "rule_content": _text(data.get("ruleContent")),
        "source_json": json.dumps(data, ensure_ascii=False),
    }

    # has_login 计算：loginUrl 存在则为 True
    mapping["has_login"] = bool(mapping["login_url"])

    # domain_key 计算
    mapping["domain_key"] = _extract_domain_key(mapping["source_url"])

    # source_icon：BookSource 为 bookSourceIcon，RssSource 为 sourceIcon
    mapping["source_icon"] = data.get(
        "bookSourceIcon" if is_book else "sourceIcon"
    )

    if is_book:
        mapping.update({
            "book_source_type": data.get("bookSourceType", 0),
            "book_url_pattern": data.get("bookUrlPattern"),
            "explore_url": _text(data.get("exploreUrl")),
            "explore_screen": _text(data.get("exploreScreen")),
            "cover_decode_js": _text(data.get("coverDecodeJs")),
            "event_listener": _bool(data.get("eventListener")),
            "custom_button": _bool(data.get("customButton")),
            "rule_search": _text(data.get("ruleSearch")),
            "rule_toc": _text(data.get("ruleToc")),
            "rule_explore": _text(data.get("ruleExplore")),
            "rule_book_info": _text(data.get("ruleBookInfo")),
            "weight": data.get("weight"),
        })
    else:
        mapping.update({
            "rss_type": data.get("type", 0),
            "rule_articles": _text(data.get("ruleArticles")),
            "rule_title": _text(data.get("ruleTitle")),
            "rule_image": _text(data.get("ruleImage")),
            "rule_link": _text(data.get("ruleLink")),
            "rule_next_page": _text(data.get("ruleNextPage")),
            "rule_pub_date": _text(data.get("rulePubDate")),
            "rule_description": _text(data.get("ruleDescription")),
        })

    return mapping


def _require_session_factory():
    """获取会话工厂，未初始化时抛出异常。"""
    sf = get_session_factory()
    if sf is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return sf


async def find_by_domain(
    domain_key: str, source_type: str | None = None
) -> list[Source]:
    """按域名查找源。"""
    sf = _require_session_factory()
    async with sf() as session:
        stmt = select(Source).where(Source.domain_key == domain_key)
        if source_type:
            stmt = stmt.where(Source.source_type == source_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def upsert_source(source_data: dict[str, Any]) -> Source:
    """单条插入或更新源。按 source_url + source_type 唯一匹配。"""
    mapped = _map_source_data(source_data)
    source_url = mapped["source_url"]
    source_type = mapped["source_type"]

    sf = _require_session_factory()
    async with sf() as session:
        async with session.begin():
            stmt = select(Source).where(
                Source.source_url == source_url,
                Source.source_type == source_type,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                for key, value in mapped.items():
                    if key not in ("id", "created_at"):
                        setattr(existing, key, value)
                await session.flush()
                await session.refresh(existing)
                return existing
            else:
                source = Source(**mapped)
                session.add(source)
                await session.flush()
                await session.refresh(source)
                return source


async def bulk_upsert(sources: list[dict[str, Any]]) -> int:
    """批量插入/更新源，返回新增数量。

    高性能版本：先批量查已有 URL，再分批 insert/update，避免单事务过大。
    跳过 source_url 为空的源（无法按 URL 唯一匹配）。
    """
    if not sources:
        return 0

    # 1. 映射所有数据
    mapped_list = [_map_source_data(data) for data in sources]
    if not mapped_list:
        return 0

    # 过滤掉 source_url 为空的源
    mapped_list = [m for m in mapped_list if m.get("source_url")]
    if not mapped_list:
        return 0

    # 2. 提取所有 (source_url, source_type) 对
    url_type_pairs = [(m["source_url"], m["source_type"]) for m in mapped_list]

    sf = _require_session_factory()

    # 3. 批量查询已有源（单独事务，避免长事务锁定）
    existing_map: dict[tuple[str, str], Source] = {}
    async with sf() as session:
        batch_size = 500
        for i in range(0, len(url_type_pairs), batch_size):
            batch = url_type_pairs[i:i + batch_size]
            urls = [p[0] for p in batch]
            types = list(set(p[1] for p in batch))
            stmt = select(Source).where(
                Source.source_url.in_(urls),
                Source.source_type.in_(types),
            )
            result = await session.execute(stmt)
            for row in result.scalars().all():
                existing_map[(row.source_url, row.source_type)] = row

    # 4. 分批 insert/update，每 commit_batch 条提交一次
    commit_batch = 200
    new_count = 0
    error_count = 0
    for batch_start in range(0, len(mapped_list), commit_batch):
        batch = mapped_list[batch_start:batch_start + commit_batch]
        try:
            async with sf() as session:
                async with session.begin():
                    # 重新查询本批中已存在的源（获取托管实例）
                    batch_urls = [m["source_url"] for m in batch]
                    batch_types = list(set(m["source_type"] for m in batch))
                    stmt = select(Source).where(
                        Source.source_url.in_(batch_urls),
                        Source.source_type.in_(batch_types),
                    )
                    result = await session.execute(stmt)
                    batch_existing: dict[tuple[str, str], Source] = {}
                    for row in result.scalars().all():
                        batch_existing[(row.source_url, row.source_type)] = row

                    for mapped in batch:
                        key = (mapped["source_url"], mapped["source_type"])
                        existing = batch_existing.get(key)
                        if existing:
                            for k, v in mapped.items():
                                if k not in ("id", "created_at"):
                                    setattr(existing, k, v)
                        else:
                            source = Source(**mapped)
                            session.add(source)
                            new_count += 1

                    await session.flush()
        except Exception as e:
            # 单批失败不影响其他批次
            error_count += 1
            logger.warning("bulk_upsert 批次 %d-%d 失败: %s", batch_start, batch_start + len(batch), e)

    if error_count > 0:
        logger.warning("bulk_upsert 完成: 成功 %d 批, 失败 %d 批", 
                       len(mapped_list) // commit_batch + 1 - error_count, error_count)

    return new_count


async def update_debug_result(source_id: int, result: dict[str, Any]) -> None:
    """更新源的测试结果字段。"""
    sf = _require_session_factory()
    async with sf() as session:
        async with session.begin():
            stmt = select(Source).where(Source.id == source_id)
            res = await session.execute(stmt)
            source = res.scalar_one_or_none()
            if source is None:
                return

            now = datetime.now()
            if "status" in result:
                source.last_test_status = result["status"]
            if "stage" in result:
                source.last_test_stage = result["stage"]
            if "detail" in result:
                source.test_detail = result["detail"]
            if "respond_time" in result:
                source.respond_time = result["respond_time"]
            source.last_test_at = now

            debug = DebugResult(
                source_id=source_id,
                key=result.get("key"),
                trigger=result.get("trigger", "web"),
                stage=result.get("stage"),
                status=result.get("status", "error"),
                message=result.get("message"),
                search_status=result.get("search_status", "skip"),
                detail_status=result.get("detail_status", "skip"),
                toc_status=result.get("toc_status", "skip"),
                content_status=result.get("content_status", "skip"),
                confidence=result.get("confidence"),
                test_mode=result.get("test_mode", "jar"),
                device_jar_diff=result.get("device_jar_diff"),
                fix_applied=result.get("fix_applied"),
                started_at=result.get("started_at"),
                finished_at=now,
                duration_ms=result.get("duration_ms"),
            )
            session.add(debug)


async def find_by_group(
    group: str, source_type: str | None = None
) -> list[Source]:
    """按分组查找源（模糊匹配 source_group LIKE %group%）。"""
    sf = _require_session_factory()
    async with sf() as session:
        stmt = select(Source).where(Source.source_group.like(f"%{group}%"))
        if source_type:
            stmt = stmt.where(Source.source_type == source_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_source(source_id: int) -> Source | None:
    """按 ID 获取单个源。"""
    sf = _require_session_factory()
    async with sf() as session:
        return await session.get(Source, source_id)


async def list_sources(
    page: int = 1,
    page_size: int = 20,
    source_type: str | None = None,
    book_source_type: int | None = None,
    rss_type: int | None = None,
    test_result: str | None = None,
    group: str | None = None,
    has_login: bool | None = None,
    search: str | None = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> tuple[list[Source], int]:
    """分页查询源列表，返回 (记录列表, 总数)。"""
    sf = _require_session_factory()
    async with sf() as session:
        conditions = []
        if source_type:
            conditions.append(Source.source_type == source_type)
        if book_source_type is not None:
            conditions.append(Source.book_source_type == book_source_type)
        if rss_type is not None:
            conditions.append(Source.rss_type == rss_type)
        if test_result:
            conditions.append(Source.last_test_status == test_result)
        if group:
            conditions.append(Source.source_group.like(f"%{group}%"))
        if has_login is not None:
            conditions.append(Source.has_login == has_login)
        if search:
            conditions.append(
                Source.source_name.like(f"%{search}%")
                | Source.source_url.like(f"%{search}%")
            )

        # 总数
        count_stmt = select(func.count(Source.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await session.execute(count_stmt)).scalar_one()

        # 排序
        sort_col = getattr(Source, sort_by, Source.updated_at)
        if sort_order.lower() == "asc":
            sort_col = sort_col.asc()
        else:
            sort_col = sort_col.desc()

        # 分页
        stmt = select(Source).order_by(sort_col).offset((page - 1) * page_size).limit(page_size)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await session.execute(stmt)
        records = list(result.scalars().all())

        return records, total


async def toggle_enabled(source_id: int, enabled: bool) -> bool:
    """切换源启用/禁用状态，返回是否成功。"""
    sf = _require_session_factory()
    async with sf() as session:
        async with session.begin():
            stmt = update(Source).where(Source.id == source_id).values(enabled=enabled)
            result = await session.execute(stmt)
            return result.rowcount > 0


async def get_groups(source_type: str | None = None) -> list[str]:
    """获取已有分组列表（去重，按逗号拆分）。"""
    sf = _require_session_factory()
    async with sf() as session:
        stmt = select(Source.source_group)
        if source_type:
            stmt = stmt.where(Source.source_type == source_type)
        stmt = stmt.where(Source.source_group.isnot(None), Source.source_group != "")
        result = await session.execute(stmt)
        raw_groups = result.scalars().all()

        groups_set: set[str] = set()
        for g in raw_groups:
            for part in g.split(","):
                stripped = part.strip()
                if stripped:
                    groups_set.add(stripped)
        return sorted(groups_set)


async def delete_sources(ids: list[int]) -> int:
    """按 ID 列表删除源，返回删除数量。"""
    if not ids:
        return 0
    sf = _require_session_factory()
    async with sf() as session:
        async with session.begin():
            stmt = delete(Source).where(Source.id.in_(ids))
            result = await session.execute(stmt)
            return result.rowcount


async def get_default_device() -> DeviceConfig | None:
    """获取默认设备配置。"""
    sf = _require_session_factory()
    async with sf() as session:
        stmt = select(DeviceConfig).where(DeviceConfig.is_default.is_(True)).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_debug_history(
    source_id: int, limit: int = 20
) -> list[DebugResult]:
    """获取源的调试历史记录。"""
    sf = _require_session_factory()
    async with sf() as session:
        stmt = (
            select(DebugResult)
            .where(DebugResult.source_id == source_id)
            .order_by(DebugResult.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
