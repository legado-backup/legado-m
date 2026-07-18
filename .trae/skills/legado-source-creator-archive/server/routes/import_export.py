#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入导出 API：URL 导入、文件上传导入、GitHub 导入、真机拉取。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from legado_client.utils.config import config

router = APIRouter(prefix="/api/import", tags=["import"])


def _db_check() -> dict[str, Any] | None:
    """数据库可用性检查。"""
    if not config.db_available:
        return {"ok": False, "data": None, "error": {"code": 503, "message": "数据库不可用"}}
    return None


class UrlImportRequest(BaseModel):
    url: str
    source_type: str = "book"


class GithubImportRequest(BaseModel):
    url: str
    source_type: str = "book"


class LegadoPullRequest(BaseModel):
    source_type: str = "book"
    host: str | None = None
    port: int | None = None
    auth_token: str | None = None


@router.post("/url")
async def import_from_url(req: UrlImportRequest) -> dict[str, Any]:
    """URL 导入：从 JSON URL 下载并入库。"""
    if err := _db_check():
        return err

    from legado_client.fetcher.url_importer import import_from_url as _import

    try:
        result = await _import(url=req.url, source_type=req.source_type)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"导入失败: {e}"}}

    return {"ok": True, "data": result, "error": None}


@router.post("/file")
async def import_from_file(
    file: UploadFile = File(..., description="源 JSON 文件"),
    source_type: str = Form("book"),
) -> dict[str, Any]:
    """文件上传导入：接收上传的 JSON 文件并入库。"""
    if err := _db_check():
        return err

    try:
        content = await file.read()
        raw_json = content.decode("utf-8")
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 400, "message": f"文件读取失败: {e}"}}

    from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
    from legado_client.storage.repository import bulk_upsert

    try:
        parsed = parse_source_json(raw_json, source_type)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 400, "message": f"JSON 解析失败: {e}"}}

    if not parsed:
        return {"ok": True, "data": {"total": 0, "imported": 0, "errors": 0}, "error": None}

    deduped = deduplicate_sources(parsed)
    try:
        imported = await bulk_upsert(deduped)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"入库失败: {e}"}}

    return {"ok": True, "data": {"total": len(deduped), "imported": imported, "errors": 0}, "error": None}


@router.post("/github")
async def import_from_github(req: GithubImportRequest) -> dict[str, Any]:
    """GitHub 导入：自动转换 GitHub 仓库 URL 为 raw URL 后下载入库。"""
    if err := _db_check():
        return err

    from legado_client.fetcher.url_importer import import_from_url as _import

    try:
        result = await _import(url=req.url, source_type=req.source_type)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"GitHub 导入失败: {e}"}}

    return {"ok": True, "data": result, "error": None}


@router.post("/json")
async def import_from_json(body: dict[str, Any]) -> dict[str, Any]:
    """从 JSON 文本导入源。"""
    if err := _db_check():
        return err

    raw_json = body.get("json", "")
    source_type = body.get("source_type", "book")
    if not raw_json:
        return {"ok": False, "data": None, "error": {"code": 400, "message": "json 字段不能为空"}}

    from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
    from legado_client.storage.repository import bulk_upsert

    try:
        parsed = parse_source_json(raw_json, source_type)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 400, "message": f"JSON 解析失败: {e}"}}

    if not parsed:
        return {"ok": True, "data": {"total": 0, "imported": 0, "errors": 0}, "error": None}

    deduped = deduplicate_sources(parsed)
    try:
        imported = await bulk_upsert(deduped)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"入库失败: {e}"}}

    return {"ok": True, "data": {"total": len(deduped), "imported": imported, "errors": 0}, "error": None}


@router.post("/yckceo")
async def import_from_yckceo(body: dict[str, Any]) -> dict[str, Any]:
    """从 yckceo 平台导入源（通过合集 ID 下载并入库）。"""
    if err := _db_check():
        return err

    collection_id = body.get("collection_id")
    if not collection_id:
        return {"ok": False, "data": None, "error": {"code": 400, "message": "collection_id 不能为空"}}

    from legado_client.fetcher.yckceo_fetcher import CollectionItem, fetch_collection_json
    from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
    from legado_client.storage.repository import bulk_upsert
    from legado_client.storage.database import get_session_factory
    from legado_client.storage.models import Collection

    sf = get_session_factory()
    async with sf() as session:
        col = await session.get(Collection, int(collection_id))

    if not col:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "合集不存在"}}

    item = CollectionItem(remote_id=col.remote_id, title=col.title, detail_url=col.url)
    json_str = await fetch_collection_json(item, col.source_type)
    if not json_str:
        return {"ok": False, "data": None, "error": {"code": 500, "message": "JSON 下载失败"}}

    parsed = parse_source_json(json_str, col.source_type)
    deduped = deduplicate_sources(parsed)
    imported = await bulk_upsert(deduped)
    return {"ok": True, "data": {"total": len(deduped), "imported": imported}, "error": None}


@router.get("/progress/{task_id}")
async def import_progress(task_id: str) -> dict[str, Any]:
    """获取导入进度（占位端点，前端兼容）。"""
    return {"ok": True, "data": {"task_id": task_id, "status": "completed", "progress": 100}, "error": None}


@router.post("/legado-pull")
async def legado_pull(req: LegadoPullRequest) -> dict[str, Any]:
    """真机拉取：从 Legado App 拉取源数据。"""
    if err := _db_check():
        return err

    from legado_client.fetcher.legado_sync import pull_from_device

    try:
        result = await pull_from_device(
            source_type=req.source_type,
            host=req.host,
            port=req.port,
            auth_token=req.auth_token,
        )
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"真机拉取失败: {e}"}}

    return {"ok": True, "data": result, "error": None}
