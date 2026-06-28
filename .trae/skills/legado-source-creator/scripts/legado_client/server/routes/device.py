#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真机推送 API：设备 CRUD、连接测试、推送/拉取源。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update

from legado_client.storage.database import get_session_factory
from legado_client.storage.models import DeviceConfig, Source
from legado_client.utils.config import config

router = APIRouter(prefix="/api/devices", tags=["devices"])


def _db_check() -> dict[str, Any] | None:
    """数据库可用性检查。"""
    if not config.db_available:
        return {"ok": False, "data": None, "error": {"code": 503, "message": "数据库不可用"}}
    return None


def _device_to_dict(dev: DeviceConfig) -> dict[str, Any]:
    """ORM 对象转字典。"""
    return {
        "id": dev.id,
        "name": dev.name,
        "address": f"{dev.ip}:{dev.port}",
        "ip": dev.ip,
        "port": dev.port,
        "auth_token": "***" if dev.auth_token else None,  # 不暴露 token
        "is_default": dev.is_default,
        "last_connected_at": dev.last_connected_at.isoformat() if dev.last_connected_at else None,
        "status": dev.status,
        "online": dev.status == "online",
        "last_seen": dev.last_connected_at.isoformat() if dev.last_connected_at else None,
        "created_at": dev.created_at.isoformat() if dev.created_at else None,
    }


# ----------- 请求体 -----------

class DeviceCreateRequest(BaseModel):
    name: str
    address: str = ""  # 前端传入 "host:port" 格式
    ip: str = ""
    port: int = 1122
    auth_token: str | None = None
    is_default: bool = False

    def resolve_address(self) -> tuple[str, int]:
        """从 address 解析 ip 和 port，address 优先。"""
        if self.address and not self.ip:
            parts = self.address.rsplit(":", 1)
            ip = parts[0]
            port = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1122
            return ip, port
        return self.ip or "127.0.0.1", self.port

class DeviceUpdateRequest(BaseModel):
    name: str | None = None
    address: str | None = None  # 前端传入 "host:port" 格式
    ip: str | None = None
    port: int | None = None
    auth_token: str | None = None
    is_default: bool | None = None

class DevicePushRequest(BaseModel):
    source_ids: list[int] | None = None  # None=全部
    source_type: str = "book"

class DevicePullRequest(BaseModel):
    source_type: str = "book"

class CleanDeadRequest(BaseModel):
    """清理死源请求。"""
    source_type: str = "book"
    dry_run: bool = True
    mark_db: bool = True
    timeout: int = 300

class DeviceBatchValidateRequest(BaseModel):
    """真机批量校验请求。"""
    source_type: str = "book"
    source_ids: list[int] | None = None
    checks: list[str] = ["connectivity"]
    timeout: int = 30


# ----------- API 端点 -----------

@router.get("")
async def list_devices() -> dict[str, Any]:
    """设备列表。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        stmt = select(DeviceConfig).order_by(DeviceConfig.is_default.desc(), DeviceConfig.created_at.asc())
        result = await session.execute(stmt)
        devices = list(result.scalars().all())

    return {"ok": True, "data": [_device_to_dict(d) for d in devices], "error": None}


@router.post("")
async def add_device(req: DeviceCreateRequest) -> dict[str, Any]:
    """添加设备。"""
    if err := _db_check():
        return err

    ip, port = req.resolve_address()

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            # 如果设为默认，先清除其他默认
            if req.is_default:
                await session.execute(
                    update(DeviceConfig).where(DeviceConfig.is_default.is_(True)).values(is_default=False)
                )

            device = DeviceConfig(
                name=req.name,
                ip=ip,
                port=port,
                auth_token=req.auth_token,
                is_default=req.is_default,
            )
            session.add(device)
            await session.flush()
            await session.refresh(device)

    return {"ok": True, "data": _device_to_dict(device), "error": None}


@router.put("/{device_id}")
async def update_device(device_id: int, req: DeviceUpdateRequest) -> dict[str, Any]:
    """编辑设备。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            device = await session.get(DeviceConfig, device_id)
            if not device:
                return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

            # 如果设为默认，先清除其他默认
            if req.is_default:
                await session.execute(
                    update(DeviceConfig).where(DeviceConfig.is_default.is_(True)).values(is_default=False)
                )

            # 处理 address 字段：解析为 ip + port
            updates = req.model_dump(exclude_unset=True)
            if "address" in updates:
                addr = updates.pop("address")
                if addr:
                    parts = addr.rsplit(":", 1)
                    updates["ip"] = parts[0]
                    updates["port"] = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1122

            for key, value in updates.items():
                setattr(device, key, value)

            await session.flush()
            await session.refresh(device)

    return {"ok": True, "data": _device_to_dict(device), "error": None}


@router.delete("/{device_id}")
async def delete_device(device_id: int) -> dict[str, Any]:
    """删除设备。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            result = await session.execute(
                delete(DeviceConfig).where(DeviceConfig.id == device_id)
            )
            deleted = result.rowcount > 0

    if not deleted:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    return {"ok": True, "data": {"deleted": True}, "error": None}


@router.post("/{device_id}/test-connection")
@router.post("/{device_id}/test")
async def test_connection(device_id: int) -> dict[str, Any]:
    """测试设备连接。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        device = await session.get(DeviceConfig, device_id)
    if not device:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    from legado_client.device.legado_web_client import LegadoWebClient

    client = LegadoWebClient(
        host=device.ip, port=device.port, auth_token=device.auth_token or "",
    )
    try:
        result = await client.test_connection()
    except Exception as e:
        result = {"connected": False, "error": str(e)}
    finally:
        await client.close()

    # 更新设备状态
    new_status = "online" if result.get("connected") else "offline"
    sf = get_session_factory()
    async with sf() as session:
        async with session.begin():
            await session.execute(
                update(DeviceConfig)
                .where(DeviceConfig.id == device_id)
                .values(status=new_status, last_connected_at=datetime.now() if new_status == "online" else None)
            )

    return {"ok": True, "data": result, "error": None}


@router.post("/{device_id}/push")
async def push_sources(device_id: int, req: DevicePushRequest) -> dict[str, Any]:
    """推送源到设备。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        device = await session.get(DeviceConfig, device_id)
    if not device:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    # 从数据库获取要推送的源
    async with sf() as session:
        stmt = select(Source).where(Source.source_type == req.source_type)
        if req.source_ids:
            stmt = stmt.where(Source.id.in_(req.source_ids))
        result = await session.execute(stmt)
        sources = list(result.scalars().all())

    if not sources:
        return {"ok": True, "data": {"pushed": 0, "message": "无源可推送"}, "error": None}

    # 解析 source_json 并推送
    import json
    from legado_client.device.legado_web_client import LegadoWebClient

    client = LegadoWebClient(
        host=device.ip, port=device.port, auth_token=device.auth_token or "",
    )
    try:
        source_list = []
        for s in sources:
            try:
                source_list.append(json.loads(s.source_json))
            except (json.JSONDecodeError, TypeError):
                continue

        if not source_list:
            return {"ok": False, "data": None, "error": {"code": 500, "message": "源 JSON 解析失败"}}

        if req.source_type == "book":
            success = await client.save_book_sources(source_list)
        else:
            success = await client.save_rss_sources(source_list)

        pushed = len(source_list) if success else 0
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"推送失败: {e}"}}
    finally:
        await client.close()

    return {"ok": True, "data": {"pushed": pushed}, "error": None}


@router.post("/{device_id}/pull")
async def pull_sources(device_id: int, req: DevicePullRequest) -> dict[str, Any]:
    """从设备拉取源。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        device = await session.get(DeviceConfig, device_id)
    if not device:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    from legado_client.fetcher.legado_sync import pull_from_device

    try:
        result = await pull_from_device(
            source_type=req.source_type,
            host=device.ip,
            port=device.port,
            auth_token=device.auth_token,
        )
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"拉取失败: {e}"}}

    return {"ok": True, "data": result, "error": None}


@router.post("/{device_id}/clean-dead")
async def clean_dead_sources(device_id: int, req: CleanDeadRequest) -> dict[str, Any]:
    """清理真机上的死源。

    请求体:
    {
        "source_type": "book" | "rss",
        "dry_run": true,  // 只检查不删除
        "mark_db": true   // 同时标记数据库
    }
    """
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        device = await session.get(DeviceConfig, device_id)
    if not device:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    # 获取设备上的源列表
    import json
    from legado_client.device.legado_web_client import LegadoWebClient

    client = LegadoWebClient(
        host=device.ip, port=device.port, auth_token=device.auth_token or "",
    )
    try:
        if req.source_type == "book":
            device_sources = await client.get_book_sources()
        else:
            device_sources = await client.get_rss_sources()
    except Exception as e:
        await client.close()
        return {"ok": False, "data": None, "error": {"code": 500, "message": f"获取设备源列表失败: {e}"}}

    # 连通性检查（分批并发，避免打爆事件循环）
    dead_list = []
    alive_list = []

    from urllib.parse import urlparse
    import asyncio

    _DNS_BATCH = 200  # 每批并发数

    async def _check_one(src: dict):
        url = src.get("bookSourceUrl") or src.get("sourceUrl") or ""
        name = src.get("sourceName") or src.get("sourceName") or ""
        if not url:
            dead_list.append({"name": name, "url": url, "reason": "无URL"})
            return
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if not host:
                dead_list.append({"name": name, "url": url, "reason": "无效域名"})
                return
            await asyncio.wait_for(
                asyncio.get_event_loop().getaddrinfo(host, None),
                timeout=5.0,
            )
            alive_list.append(src)
        except Exception:
            dead_list.append({"name": name, "url": url, "reason": "域名不可达"})

    # 分批执行，每批 200 个并发
    for i in range(0, len(device_sources), _DNS_BATCH):
        batch = device_sources[i:i + _DNS_BATCH]
        await asyncio.gather(*[_check_one(s) for s in batch], return_exceptions=True)

    result_data: dict[str, Any] = {
        "total": len(device_sources),
        "alive": len(alive_list),
        "dead": len(dead_list),
        "dead_list": dead_list,
        "dry_run": req.dry_run,
    }

    # 非试运行模式：删除真机上的死源
    if not req.dry_run and dead_list:
        dead_urls = [d["url"] for d in dead_list if d.get("url")]
        # Legado API 需要源对象列表 [{"bookSourceUrl": url}] 而非 URL 列表
        if req.source_type == "book":
            dead_source_objs = [{"bookSourceUrl": u} for u in dead_urls]
        else:
            dead_source_objs = [{"sourceUrl": u} for u in dead_urls]
        try:
            if req.source_type == "book":
                await client.delete_book_sources(dead_source_objs)
            else:
                await client.delete_rss_sources(dead_source_objs)
            result_data["deleted"] = len(dead_urls)
        except Exception as e:
            result_data["delete_error"] = str(e)
            result_data["deleted"] = 0

    # 标记数据库
    if req.mark_db and dead_list:
        dead_urls = [d["url"] for d in dead_list if d.get("url")]
        if dead_urls:
            # 分批标记，避免 SQL IN 列表过长
            _MARK_BATCH = 500
            for i in range(0, len(dead_urls), _MARK_BATCH):
                batch = dead_urls[i:i + _MARK_BATCH]
                async with sf() as session:
                    async with session.begin():
                        await session.execute(
                            update(Source)
                            .where(Source.source_url.in_(batch))
                            .where(Source.source_type == req.source_type)
                            .values(
                                enabled=False,
                                last_test_status="fail",
                                last_test_stage="domain_dead",
                                last_test_at=datetime.now(),
                            )
                        )

    await client.close()

    return {"ok": True, "data": result_data, "error": None}


@router.post("/{device_id}/batch-validate")
async def device_batch_validate(device_id: int, req: DeviceBatchValidateRequest) -> dict[str, Any]:
    """真机批量校验源。

    请求体:
    {
        "source_type": "book" | "rss",
        "source_ids": [1,2,3] 或 null,
        "checks": ["connectivity", "search", "detail", "toc", "content"],
        "timeout": 30
    }
    """
    if err := _db_check():
        return err

    sf = get_session_factory()

    # 获取设备
    async with sf() as session:
        device = await session.get(DeviceConfig, device_id)
    if not device:
        return {"ok": False, "data": None, "error": {"code": 404, "message": "设备不存在"}}

    # 获取源列表
    async with sf() as session:
        stmt = select(Source).where(Source.source_type == req.source_type)
        if req.source_ids:
            stmt = stmt.where(Source.id.in_(req.source_ids))
        result = await session.execute(stmt)
        sources = list(result.scalars().all())

    if not sources:
        return {"ok": True, "data": {"total": 0, "results": [], "summary": {}}, "error": None}

    import json as _json
    from legado_client.device.legado_web_client import LegadoWebClient

    client = LegadoWebClient(
        host=device.ip, port=device.port, auth_token=device.auth_token or "",
    )

    results = []
    summary = {"alive": 0, "dead": 0, "search_pass": 0, "detail_pass": 0, "toc_pass": 0, "content_pass": 0}

    try:
        for source in sources:
            item = {
                "source_id": source.id,
                "source_name": source.source_name,
                "source_url": source.source_url,
                "connectivity": "unknown",
                "search": "skip",
                "detail": "skip",
                "toc": "skip",
                "content": "skip",
                "message": "",
            }
            source_data = _json.loads(source.source_json) if isinstance(source.source_json, str) else source.source_json

            try:
                if "connectivity" in req.checks or not req.checks:
                    if req.source_type == "book":
                        logs = await client.ws_debug_book_source(source_data, "")
                    else:
                        logs = await client.ws_debug_rss_source(source_data)
                    has_error = any("[ERROR]" in log for log in logs)
                    item["connectivity"] = "pass" if not has_error else "fail"
                    item["message"] = "\n".join(logs[-3:]) if logs else ""
            except Exception as e:
                item["connectivity"] = "fail"
                item["message"] = str(e)

            if item["connectivity"] == "pass":
                summary["alive"] += 1
            else:
                summary["dead"] += 1
            for stage in ("search", "detail", "toc", "content"):
                if item.get(stage) == "pass":
                    summary[f"{stage}_pass"] += 1
            results.append(item)
    finally:
        await client.close()

    return {
        "ok": True,
        "data": {
            "total": len(sources),
            "results": results,
            "summary": summary,
        },
        "error": None,
    }
