#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legado Web 服务代理路由：19 个 HTTP 代理端点 + 3 个 WebSocket 代理端点。

所有 /legado/* 请求转发到真机 Legado Web 服务。
支持动态设备选择（通过 query param device_id）。
HTTP 代理：使用 httpx 转发。
WebSocket 代理：使用 websockets 库双向转发。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse

from legado_client.storage.database import get_session_factory
from legado_client.storage.models import DeviceConfig
from legado_client.utils.config import config

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Legado 代理"])

# HTTP 客户端池（复用连接）
_http_client: httpx.AsyncClient | None = None


async def _get_http_client() -> httpx.AsyncClient:
    """获取或创建 HTTP 客户端。"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def _get_device(device_id: Optional[int] = None) -> DeviceConfig | None:
    """获取设备配置，优先按 device_id，其次按默认设备，最后用 config 中的配置。"""
    sf = get_session_factory()
    if sf is not None and config.db_available:
        try:
            async with sf() as session:
                if device_id is not None:
                    device = await session.get(DeviceConfig, device_id)
                    if device:
                        return device
                # 回退到默认设备
                from sqlalchemy import select
                stmt = select(DeviceConfig).where(DeviceConfig.is_default.is_(True)).limit(1)
                result = await session.execute(stmt)
                device = result.scalar_one_or_none()
                if device:
                    return device
        except Exception as e:
            logger.warning("从数据库获取设备配置失败: %s", e)

    # 回退到 config 中的静态配置
    if config.device_host:
        return DeviceConfig(
            id=0,
            name="config默认设备",
            ip=config.device_host,
            port=config.device_port,
            auth_token=config.device_auth_token or None,
        )
    return None


# ==================== HTTP 代理 ====================

@router.api_route(
    "/legado/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    summary="Legado HTTP 代理",
    name="legado_http_proxy",
)
async def legado_http_proxy(
    path: str,
    request: Request,
    device_id: Optional[int] = Query(None, description="设备 ID"),
):
    """将 HTTP 请求代理到真机 Legado Web 服务。"""
    device = await _get_device(device_id)
    if not device:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": {"code": "NO_DEVICE", "message": "未配置真机设备"},
            },
        )

    target_url = f"http://{device.ip}:{device.port}/{path}"

    # 构建转发 headers（去掉 host）
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    if device.auth_token:
        headers["Authorization"] = f"Bearer {device.auth_token}"

    # 获取请求体
    body = await request.body()

    client = await _get_http_client()
    try:
        resp = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
            params=dict(request.query_params),
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "error": {"code": "DEVICE_UNREACHABLE", "message": f"无法连接设备 {device.ip}:{device.port}"},
            },
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "ok": False,
                "error": {"code": "DEVICE_TIMEOUT", "message": "设备响应超时"},
            },
        )

    # 判断响应类型：二进制图片 vs JSON/文本
    content_type = resp.headers.get("content-type", "")
    if "image" in content_type:
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=content_type,
        )

    # JSON 或文本响应
    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")
    }
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
    )


# ==================== WebSocket 代理 ====================

@router.websocket("/ws/legado/{path:path}")
async def legado_ws_proxy(
    websocket: WebSocket,
    path: str,
    device_id: Optional[int] = None,
):
    """双向 WebSocket 代理：客户端 <-> 服务端 <-> Legado 真机。

    支持的路径（与 Legado Web 服务对齐）：
    - searchBook: 搜索书籍
    - debugBookSource: 调试书源
    - debugRssSource: 调试订阅源
    """
    await websocket.accept()

    device = await _get_device(device_id)
    if not device:
        await websocket.send_json({
            "ok": False,
            "error": {"code": "NO_DEVICE", "message": "未配置真机设备"},
        })
        await websocket.close()
        return

    ws_port = device.port + 1  # WebSocket 端口 = HTTP + 1
    target_url = f"ws://{device.ip}:{ws_port}/{path}"

    # 附加 query 参数（除 device_id 外全部转发）
    query_params = dict(websocket.query_params)
    query_params.pop("device_id", None)
    if query_params:
        from urllib.parse import urlencode
        target_url += "?" + urlencode(query_params)

    try:
        import websockets
    except ImportError:
        await websocket.send_json({
            "ok": False,
            "error": {"code": "MISSING_DEP", "message": "websockets 库未安装"},
        })
        await websocket.close()
        return

    try:
        async with websockets.connect(target_url) as remote_ws:
            # 双向转发
            async def client_to_remote():
                """客户端 → Legado 真机。"""
                try:
                    while True:
                        data = await websocket.receive_text()
                        await remote_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.debug("客户端→真机异常: %s", e)

            async def remote_to_client():
                """Legado 真机 → 客户端。"""
                try:
                    async for message in remote_ws:
                        text = message if isinstance(message, str) else message.decode("utf-8")
                        await websocket.send_text(text)
                except Exception as e:
                    logger.debug("真机→客户端异常: %s", e)

            # 并行双向转发
            await asyncio.gather(
                client_to_remote(),
                remote_to_client(),
                return_exceptions=True,
            )
    except Exception as e:
        logger.error("WebSocket 代理连接失败: %s", e)
        try:
            await websocket.send_text(f"[ERROR] 连接真机失败: {e}")
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
