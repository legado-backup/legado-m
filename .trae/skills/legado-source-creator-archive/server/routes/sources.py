#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源管理 API 路由：CRUD、批量操作、分组、导出、验证。

重要：FastAPI 按注册顺序匹配路由，所有静态路径（/by-domain, /groups, /batch-action 等）
必须在参数路径（/{source_id}）之前注册，否则会被参数路径拦截。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Query

from legado_client.server.schemas import (
    ApiResponse,
    BatchActionRequest,
    SourceDetail,
    SourceItem,
    SourceListResponse,
    SourceUpdateRequest,
    ValidateResult,
)
from legado_client.storage import repository
from legado_client.utils.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["源管理"])


def _db_unavailable() -> ApiResponse:
    """数据库不可用时的统一 503 响应。"""
    return ApiResponse(
        ok=False,
        error={"code": "SERVICE_UNAVAILABLE", "message": "数据库不可用，服务处于降级模式"},
    )


def _source_to_item(source: Any) -> SourceItem:
    """ORM Source → SourceItem（列表项）。"""
    return SourceItem.model_validate(source)


def _source_to_detail(source: Any) -> SourceDetail:
    """ORM Source → SourceDetail（详情）。"""
    return SourceDetail.model_validate(source)


# ============================================================
# 静态路径路由（必须在 /{source_id} 之前注册）
# ============================================================


@router.post("", response_model=ApiResponse)
async def create_source(body: SourceUpdateRequest):
    """创建/更新源：解析 source_json 后 upsert。"""
    if not config.db_available:
        return _db_unavailable()

    try:
        source_data = json.loads(body.source_json)
    except json.JSONDecodeError as e:
        return ApiResponse(
            ok=False,
            error={"code": "INVALID_JSON", "message": f"JSON 解析失败: {e}"},
        )

    if body.source_name:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceName" if is_book else "sourceName"] = body.source_name
    if body.source_url:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceUrl" if is_book else "sourceUrl"] = body.source_url
    if body.source_group:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceGroup" if is_book else "sourceGroup"] = body.source_group

    try:
        created = await repository.upsert_source(source_data)
    except Exception as e:
        return ApiResponse(
            ok=False,
            error={"code": "DB_ERROR", "message": f"入库失败: {e}"},
        )

    return ApiResponse(ok=True, data=_source_to_detail(created).model_dump())


@router.get("", response_model=ApiResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    source_type: str | None = Query(None),
    book_source_type: int | None = Query(None),
    rss_type: int | None = Query(None),
    test_result: str | None = Query(None),
    group: str | None = Query(None),
    has_login: bool | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
):
    """源列表：分页、筛选、搜索、排序。"""
    if not config.db_available:
        return _db_unavailable()

    records, total = await repository.list_sources(
        page=page,
        page_size=page_size,
        source_type=source_type,
        book_source_type=book_source_type,
        rss_type=rss_type,
        test_result=test_result,
        group=group,
        has_login=has_login,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items = [_source_to_item(r) for r in records]
    data = SourceListResponse(
        items=items, total=total, page=page, page_size=page_size
    )
    return ApiResponse(ok=True, data=data.model_dump())


@router.get("/by-domain", response_model=ApiResponse)
async def get_by_domain(
    domain_key: str = Query(..., description="域名关键词"),
    source_type: str | None = Query(None),
):
    """按域名关键词查询源列表。"""
    if not config.db_available:
        return _db_unavailable()

    sources = await repository.find_by_domain(domain_key, source_type)
    items = [_source_to_detail(s) for s in sources]
    return ApiResponse(ok=True, data=items)


@router.get("/groups", response_model=ApiResponse)
async def get_groups(source_type: str | None = Query(None)):
    """获取所有分组（去重、按字母排序）。"""
    if not config.db_available:
        return _db_unavailable()

    groups = await repository.get_groups(source_type)
    return ApiResponse(ok=True, data=groups)


@router.get("/stats", response_model=ApiResponse)
async def source_stats():
    """源统计：总数、书源/订阅源数、通过率。"""
    if not config.db_available:
        return _db_unavailable()

    from sqlalchemy import func, select
    from legado_client.storage.models import Source
    from legado_client.storage.database import get_session_factory

    sf = get_session_factory()
    async with sf() as session:
        total = (await session.execute(select(func.count(Source.id)))).scalar_one()
        book_count = (await session.execute(
            select(func.count(Source.id)).where(Source.source_type == "book")
        )).scalar_one()
        rss_count = (await session.execute(
            select(func.count(Source.id)).where(Source.source_type == "rss")
        )).scalar_one()
        pass_count = (await session.execute(
            select(func.count(Source.id)).where(Source.last_test_status == "pass")
        )).scalar_one()
        pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0.0

    return ApiResponse(ok=True, data={
        "total": total,
        "book_count": book_count,
        "rss_count": rss_count,
        "pass_count": pass_count,
        "pass_rate": pass_rate,
    })


@router.post("/batch-delete", response_model=ApiResponse)
async def batch_delete(body: dict[str, Any]):
    """批量删除源（前端传入 urls 列表）。"""
    if not config.db_available:
        return _db_unavailable()

    urls = body.get("urls", [])
    if not urls:
        return ApiResponse(ok=True, data={"deleted": 0})

    from sqlalchemy import select, delete as sa_delete
    from legado_client.storage.models import Source
    from legado_client.storage.database import get_session_factory

    sf = get_session_factory()
    deleted = 0
    async with sf() as session:
        async with session.begin():
            result = await session.execute(
                sa_delete(Source).where(Source.source_url.in_(urls))
            )
            deleted = result.rowcount

    return ApiResponse(ok=True, data={"deleted": deleted})


@router.post("/batch-action", response_model=ApiResponse)
async def batch_action(body: BatchActionRequest):
    """批量操作：enable/disable/delete/export。"""
    if not config.db_available:
        return _db_unavailable()

    if not body.source_ids:
        return ApiResponse(
            ok=False,
            error={"code": "BAD_REQUEST", "message": "source_ids 不能为空"},
        )

    if not body.action:
        return ApiResponse(
            ok=False,
            error={"code": "BAD_REQUEST", "message": "action 不能为空"},
        )

    result: dict[str, Any] = {"action": body.action}

    if body.action == "delete":
        deleted = await repository.delete_sources(body.source_ids)
        result["affected"] = deleted
    elif body.action in ("enable", "disable"):
        enabled = body.action == "enable"
        affected = 0
        for sid in body.source_ids:
            ok = await repository.toggle_enabled(sid, enabled)
            if ok:
                affected += 1
        result["affected"] = affected
    elif body.action == "export":
        exported: list[dict[str, Any]] = []
        for sid in body.source_ids:
            source = await repository.get_source(sid)
            if source and source.source_json:
                try:
                    exported.append(json.loads(source.source_json))
                except json.JSONDecodeError:
                    pass
        result["items"] = exported
        result["count"] = len(exported)
    else:
        return ApiResponse(
            ok=False,
            error={"code": "BAD_REQUEST", "message": f"不支持的操作: {body.action}"},
        )

    return ApiResponse(ok=True, data=result)


@router.post("/batch-export", response_model=ApiResponse)
async def batch_export(body: BatchActionRequest):
    """批量导出源 JSON 数组。"""
    if not config.db_available:
        return _db_unavailable()

    if not body.source_ids:
        return ApiResponse(
            ok=False,
            error={"code": "BAD_REQUEST", "message": "source_ids 不能为空"},
        )

    exported: list[dict[str, Any]] = []
    for sid in body.source_ids:
        source = await repository.get_source(sid)
        if source and source.source_json:
            try:
                exported.append(json.loads(source.source_json))
            except json.JSONDecodeError:
                pass

    return ApiResponse(ok=True, data={"items": exported, "count": len(exported)})


@router.post("/validate", response_model=ApiResponse)
async def validate_source_json(body: SourceUpdateRequest):
    """验证源 JSON 格式是否合法。"""
    errors: list[str] = []
    source_type: str | None = None
    source_name: str | None = None
    source_url: str | None = None

    try:
        data = json.loads(body.source_json)
    except json.JSONDecodeError as e:
        return ApiResponse(
            ok=True,
            data=ValidateResult(
                valid=False, errors=[f"JSON 语法错误: {e}"]
            ).model_dump(),
        )

    if not isinstance(data, dict):
        errors.append("JSON 必须是对象（非数组/字符串）")

    if isinstance(data, dict):
        if "bookSourceUrl" in data or "bookSourceName" in data:
            source_type = "book"
        elif "sourceUrl" in data or "sourceName" in data:
            source_type = "rss"
        else:
            errors.append("无法识别源类型：缺少 bookSourceUrl/sourceUrl 字段")

        if source_type == "book":
            source_url = data.get("bookSourceUrl")
            source_name = data.get("bookSourceName")
        elif source_type == "rss":
            source_url = data.get("sourceUrl")
            source_name = data.get("sourceName")

        if not source_url:
            errors.append(f"源 URL 缺失（{'bookSourceUrl' if source_type == 'book' else 'sourceUrl'}）")
        if not source_name:
            errors.append(f"源名称缺失（{'bookSourceName' if source_type == 'book' else 'sourceName'}）")

    result = ValidateResult(
        valid=len(errors) == 0,
        errors=errors,
        source_type=source_type,
        source_name=source_name,
        source_url=source_url,
    )
    return ApiResponse(ok=True, data=result.model_dump())


# ============================================================
# 参数路径路由（/{source_id} 及其子路径）
# ============================================================


@router.get("/{source_id}", response_model=ApiResponse)
async def get_source(source_id: int):
    """获取源详情（含完整 JSON 和规则字段）。"""
    if not config.db_available:
        return _db_unavailable()

    source = await repository.get_source(source_id)
    if source is None:
        return ApiResponse(
            ok=False,
            error={"code": "NOT_FOUND", "message": f"源 ID={source_id} 不存在"},
        )
    return ApiResponse(ok=True, data=_source_to_detail(source).model_dump())


@router.put("/{source_id}", response_model=ApiResponse)
async def update_source(source_id: int, body: SourceUpdateRequest):
    """更新源：解析 source_json 后 upsert。"""
    if not config.db_available:
        return _db_unavailable()

    try:
        source_data = json.loads(body.source_json)
    except json.JSONDecodeError as e:
        return ApiResponse(
            ok=False,
            error={"code": "INVALID_JSON", "message": f"JSON 解析失败: {e}"},
        )

    if body.source_name:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceName" if is_book else "sourceName"] = body.source_name
    if body.source_url:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceUrl" if is_book else "sourceUrl"] = body.source_url
    if body.source_group:
        is_book = source_data.get("source_type", "book") == "book"
        source_data["bookSourceGroup" if is_book else "sourceGroup"] = body.source_group

    existing = await repository.get_source(source_id)
    if existing is None:
        return ApiResponse(
            ok=False,
            error={"code": "NOT_FOUND", "message": f"源 ID={source_id} 不存在"},
        )

    updated = await repository.upsert_source(source_data)
    return ApiResponse(ok=True, data=_source_to_detail(updated).model_dump())


@router.delete("/{source_id}", response_model=ApiResponse)
async def delete_source(source_id: int):
    """删除单个源。"""
    if not config.db_available:
        return _db_unavailable()

    deleted = await repository.delete_sources([source_id])
    if deleted == 0:
        return ApiResponse(
            ok=False,
            error={"code": "NOT_FOUND", "message": f"源 ID={source_id} 不存在"},
        )
    return ApiResponse(ok=True, data={"deleted": deleted})


@router.patch("/{source_id}/toggle", response_model=ApiResponse)
async def toggle_source(source_id: int, enabled: bool = Query(...)):
    """切换源启用/禁用状态。"""
    if not config.db_available:
        return _db_unavailable()

    success = await repository.toggle_enabled(source_id, enabled)
    if not success:
        return ApiResponse(
            ok=False,
            error={"code": "NOT_FOUND", "message": f"源 ID={source_id} 不存在"},
        )
    return ApiResponse(ok=True, data={"id": source_id, "enabled": enabled})


@router.post("/{source_id}/export", response_model=ApiResponse)
async def export_source(source_id: int):
    """导出单个源的完整 JSON。"""
    if not config.db_available:
        return _db_unavailable()

    source = await repository.get_source(source_id)
    if source is None:
        return ApiResponse(
            ok=False,
            error={"code": "NOT_FOUND", "message": f"源 ID={source_id} 不存在"},
        )

    try:
        source_data = json.loads(source.source_json)
    except json.JSONDecodeError:
        source_data = {"raw": source.source_json}

    return ApiResponse(ok=True, data=source_data)
