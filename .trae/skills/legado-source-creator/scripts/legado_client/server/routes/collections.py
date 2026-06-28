#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合集管理 API：列表、远程爬取、下载、全量/增量更新、删除。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import delete, func, select

from legado_client.storage.database import get_session_factory
from legado_client.storage.models import Collection
from legado_client.utils.config import config

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _db_check() -> dict[str, Any] | None:
    """数据库可用性检查，不可用返回 503 响应体，可用返回 None。"""
    if not config.db_available:
        return {"ok": False, "data": None, "error": {"code": 503, "message": "数据库不可用"}}
    return None


def _col_to_dict(col: Collection) -> dict[str, Any]:
    """ORM 对象转字典。"""
    return {
        "id": col.id,
        "source_type": col.source_type,
        "remote_id": col.remote_id,
        "title": col.title,
        "user_name": col.user_name,
        "source_count": col.source_count,
        "download_count": col.download_count,
        "date": col.date,
        "url": col.url,
        "status": col.status,
        "last_fetched_at": col.last_fetched_at.isoformat() if col.last_fetched_at else None,
        "created_at": col.created_at.isoformat() if col.created_at else None,
    }


@router.get("")
async def list_collections(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
    status: str | None = Query(None, description="状态过滤: pending/downloading/completed/failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """合集列表，支持分页和过滤。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        conditions = []
        if source_type:
            conditions.append(Collection.source_type == source_type)
        if status:
            conditions.append(Collection.status == status)

        count_stmt = select(func.count(Collection.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Collection)
            .order_by(Collection.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if conditions:
            stmt = stmt.where(*conditions)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

    return {"ok": True, "data": {"items": [_col_to_dict(r) for r in rows], "total": total}, "error": None}


@router.get("/remote")
async def fetch_remote_list(
    source_type: str = Query("book", description="源类型: book/rss"),
    max_pages: int = Query(0, ge=0, description="最大页数，0=全部"),
) -> dict[str, Any]:
    """从 yckceo 爬取远程合集列表（不入库，仅返回元数据）。"""
    from legado_client.fetcher.yckceo_fetcher import fetch_list

    try:
        items = await fetch_list(source_type=source_type, max_pages=max_pages, incremental=False)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"爬取失败: {e}"}}

    data = [
        {
            "remote_id": it.remote_id,
            "title": it.title,
            "user_name": it.user_name,
            "source_count": it.source_count,
            "download_count": it.download_count,
            "date": it.date,
            "detail_url": it.detail_url,
        }
        for it in items
    ]
    return {"ok": True, "data": {"items": data, "total": len(data)}, "error": None}


@router.post("")
async def create_collection(body: dict[str, Any]) -> dict[str, Any]:
    """创建合集（手动创建本地合集记录）。"""
    if err := _db_check():
        return err

    name = body.get("name", "")
    if not name:
        return {"ok": False, "data": None, "error": {"code": 400, "message": "合集名称不能为空"}}

    sf = get_session_factory()
    async with sf() as session:
        col = Collection(
            source_type=body.get("source_type", "book"),
            remote_id=body.get("remote_id", f"local_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            title=name,
            user_name=body.get("description", ""),
            url=body.get("url"),
            status="pending",
        )
        session.add(col)
        await session.flush()
        await session.refresh(col)

    return {"ok": True, "data": _col_to_dict(col), "error": None}


@router.post("/{collection_id}/download")
async def download_collection(collection_id: int) -> dict[str, Any]:
    """下载指定合集：根据已入库的合集记录下载 JSON 并入库源。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        col = await session.get(Collection, collection_id)
    if not col:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

    if not col.url:
        return {"ok": False, "data": None, "error": {"code": 400, "message": "合集无详情页 URL"}}

    # 更新状态为下载中
    from sqlalchemy import update as sa_update
    async with sf() as session:
        async with session.begin():
            await session.execute(
                sa_update(Collection).where(Collection.id == collection_id).values(status="downloading")
            )

    try:
        from legado_client.fetcher.yckceo_fetcher import CollectionItem, fetch_collection_json
        from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
        from legado_client.storage.repository import bulk_upsert

        item = CollectionItem(
            remote_id=col.remote_id,
            title=col.title,
            detail_url=col.url,
        )
        json_str = await fetch_collection_json(item, col.source_type)
        if not json_str:
            await _update_col_status(collection_id, "failed")
            return {"ok": False, "data": None, "error": {"code": 500, "message": "JSON 下载失败"}}

        parsed = parse_source_json(json_str, col.source_type)
        deduped = deduplicate_sources(parsed)
        imported = await bulk_upsert(deduped)
        await _update_col_status(collection_id, "completed")
    except Exception as e:
        await _update_col_status(collection_id, "failed")
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"下载入库失败: {e}"}}

    return {"ok": True, "data": {"imported": imported, "total": len(deduped)}, "error": None}


@router.post("/fetch-all")
async def fetch_all_collections(
    source_type: str = Query("book", description="源类型: book/rss"),
    max_pages: int = Query(0, ge=0),
    max_collections: int = Query(0, ge=0),
) -> dict[str, Any]:
    """全量获取：爬取列表 + 下载 JSON + 入库。"""
    if err := _db_check():
        return err

    from legado_client.fetcher.yckceo_fetcher import fetch_all

    try:
        result = await fetch_all(
            source_type=source_type,
            max_pages=max_pages,
            incremental=False,
            max_collections=max_collections,
        )
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"全量获取失败: {e}"}}

    return {"ok": True, "data": result, "error": None}


@router.post("/incremental")
async def incremental_update(
    source_type: str = Query("book", description="源类型: book/rss"),
    max_pages: int = Query(0, ge=0),
) -> dict[str, Any]:
    """增量更新：仅下载新增/更新的合集。"""
    if err := _db_check():
        return err

    from legado_client.fetcher.yckceo_fetcher import fetch_all

    try:
        result = await fetch_all(
            source_type=source_type,
            max_pages=max_pages,
            incremental=True,
        )
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"增量更新失败: {e}"}}

    return {"ok": True, "data": result, "error": None}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: int) -> dict[str, Any]:
    """删除指定合集记录。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            result = await session.execute(
                delete(Collection).where(Collection.id == collection_id)
            )
            deleted = result.rowcount > 0

    if not deleted:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

    return {"ok": True, "data": {"deleted": True}, "error": None}


@router.get("/{collection_id}")
async def get_collection(collection_id: int) -> dict[str, Any]:
    """获取单个合集详情。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        col = await session.get(Collection, collection_id)

    if not col:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

    return {"ok": True, "data": _col_to_dict(col), "error": None}


@router.put("/{collection_id}")
async def update_collection(collection_id: int, body: dict[str, Any]) -> dict[str, Any]:
    """更新合集信息。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            col = await session.get(Collection, collection_id)
            if not col:
                return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

            if "name" in body:
                col.title = body["name"]
            if "description" in body:
                col.user_name = body["description"]
            if "urls" in body:
                col.url = body["urls"][0] if body["urls"] else col.url
            await session.flush()
            await session.refresh(col)

    return {"ok": True, "data": _col_to_dict(col), "error": None}


@router.post("/{collection_id}/sources")
async def add_sources_to_collection(collection_id: int, body: dict[str, Any]) -> dict[str, Any]:
    """向合集添加源（下载并入库）。"""
    if err := _db_check():
        return err

    # 合集本身不维护子源列表，此接口触发下载入库
    from legado_client.fetcher.yckceo_fetcher import CollectionItem, fetch_collection_json
    from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
    from legado_client.storage.repository import bulk_upsert

    sf = get_session_factory()
    async with sf() as session:
        col = await session.get(Collection, collection_id)

    if not col:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

    # 如果传入了 urls，直接导入
    urls = body.get("urls", [])
    if urls:
        total_imported = 0
        for url in urls:
            try:
                from legado_client.fetcher.url_importer import import_from_url
                result = await import_from_url(url=url, source_type=col.source_type)
                total_imported += result.get("imported", 0)
            except Exception:
                pass
        return {"ok": True, "data": {"imported": total_imported}, "error": None}

    # 否则触发合集下载
    item = CollectionItem(remote_id=col.remote_id, title=col.title, detail_url=col.url)
    json_str = await fetch_collection_json(item, col.source_type)
    if not json_str:
        return {"ok": False, "data": None, "error": {"code": 500, "message": "JSON 下载失败"}}

    parsed = parse_source_json(json_str, col.source_type)
    deduped = deduplicate_sources(parsed)
    imported = await bulk_upsert(deduped)
    return {"ok": True, "data": {"imported": imported, "total": len(deduped)}, "error": None}


@router.post("/{collection_id}/sources/remove")
async def remove_sources_from_collection(collection_id: int, body: dict[str, Any]) -> dict[str, Any]:
    """从合集移除源（按 URL 删除入库的源记录）。"""
    if err := _db_check():
        return err

    from legado_client.storage.models import Source
    from sqlalchemy import delete as sa_delete

    urls = body.get("urls", [])
    if not urls:
        return {"ok": True, "data": {"removed": 0}, "error": None}

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            result = await session.execute(
                sa_delete(Source).where(Source.source_url.in_(urls))
            )
            removed = result.rowcount

    return {"ok": True, "data": {"removed": removed}, "error": None}


async def _update_col_status(col_id: int, status: str) -> None:
    """更新合集状态。"""
    from sqlalchemy import update as sa_update
    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            await session.execute(
                sa_update(Collection).where(Collection.id == col_id).values(status=status)
            )
