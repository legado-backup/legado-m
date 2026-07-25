#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试路由：对比测试、JAR 优化。

包含：
- 4.21 POST /api/debug/compare 调试对比（真机 vs JAR）
- 4.22 POST /api/debug/jar-optimize JAR 优化闭环
- 4.23 已移至 stats.py 的 GET /api/stats/test-mode
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from legado_client.analyzer.jar_optimizer import JarOptimizer
from legado_client.client.debug_result import DebugResultData
from legado_client.device.legado_web_client import LegadoWebClient
from legado_client.storage.database import get_session_factory
from legado_client.storage.models import DebugResult, Source
from legado_client.utils.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["调试"])


# ---- 请求模型 ----

class CompareRequest(BaseModel):
    """调试对比请求。"""
    source_id: int = Field(..., description="源 ID")
    source_type: str = Field("book", description="源类型：book 或 rss")
    search_key: str = Field("", description="搜索关键词（书源必填）")
    device_id: Optional[int] = Field(None, description="指定设备 ID")


class JarOptimizeRequest(BaseModel):
    """JAR 优化请求。"""
    source_id: int = Field(..., description="源 ID")
    source_type: str = Field("book", description="源类型：book 或 rss")


# ---- 4.21 调试对比 API ----

@router.post("/compare")
async def debug_compare(req: CompareRequest):
    """同时在真机和 JAR 上测试同一源，返回对比结果。"""
    if not config.db_available:
        raise HTTPException(status_code=503, detail="数据库不可用")

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="数据库会话不可用")

    # 获取源数据
    async with sf() as session:
        source = await session.get(Source, req.source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="源不存在")
        source_json = source.source_json

    source_data = json.loads(source_json) if isinstance(source_json, str) else source_json

    # 真机测试
    device_result = await _run_device_test(source_data, req.source_type, req.search_key, req.device_id)

    # JAR 测试
    jar_result = await _run_jar_test(source_data, req.source_type, req.search_key)

    # 对比
    compare_result = _compare_results(device_result, jar_result)

    # 存储结果
    if config.db_available:
        try:
            from legado_client.storage import repository
            await repository.update_debug_result(req.source_id, {
                **jar_result.to_storage_dict(),
                "test_mode": "compare",
                "device_jar_diff": compare_result,
                "key": f"compare_{req.source_id}",
            })
        except Exception as e:
            logger.warning("存储调试结果失败: %s", e)

    return {
        "ok": True,
        "device_result": _result_to_dict(device_result),
        "jar_result": _result_to_dict(jar_result),
        "compare": compare_result,
    }


# ---- 4.22 JAR 优化 API ----

@router.post("/jar-optimize")
async def jar_optimize(req: JarOptimizeRequest):
    """触发 JAR 优化闭环。"""
    if not config.db_available:
        raise HTTPException(status_code=503, detail="数据库不可用")

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="数据库会话不可用")

    # 获取源数据
    async with sf() as session:
        source = await session.get(Source, req.source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="源不存在")
        source_url = source.source_url

    # 获取最近一次 compare 模式的调试记录
    async with sf() as session:
        stmt = (
            select(DebugResult)
            .where(DebugResult.source_id == req.source_id, DebugResult.test_mode == "compare")
            .order_by(DebugResult.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        last_debug = result.scalar_one_or_none()

    if last_debug is None or not last_debug.device_jar_diff:
        raise HTTPException(
            status_code=400,
            detail="没有找到 compare 模式的调试记录，请先执行调试对比",
        )

    # 构造 DebugResultData 用于 JarOptimizer
    device_result = DebugResultData(
        source_url=source_url,
        source_type=req.source_type,
        status="pass" if last_debug.status == "pass" else "fail",
        search_status=last_debug.search_status,
        detail_status=last_debug.detail_status,
        toc_status=last_debug.toc_status,
        content_status=last_debug.content_status,
        message=last_debug.message or "",
    )

    jar_result = DebugResultData(
        source_url=source_url,
        source_type=req.source_type,
        status=last_debug.status,
        stage=last_debug.stage or "",
        message=last_debug.message or "",
        search_status=last_debug.search_status,
        detail_status=last_debug.detail_status,
        toc_status=last_debug.toc_status,
        content_status=last_debug.content_status,
        confidence=last_debug.confidence or "",
    )

    optimizer = JarOptimizer()
    optimize_result = await optimizer.optimize(
        source_url=source_url,
        source_type=req.source_type,
        device_result=device_result,
        jar_result=jar_result,
    )

    return {
        "ok": True,
        "optimize_result": optimize_result,
    }


# ---- 前端兼容端点 ----

@router.post("/start")
async def debug_start(body: dict):
    """启动调试任务（前端 startDebug 兼容端点）。"""
    source_url = body.get("source_url", "")
    if not source_url:
        raise HTTPException(status_code=400, detail="source_url 不能为空")

    # 根据 source_url 查找源
    if config.db_available:
        sf = get_session_factory()
        if sf is not None:
            async with sf() as session:
                stmt = select(Source).where(Source.source_url == source_url).limit(1)
                result = await session.execute(stmt)
                source = result.scalar_one_or_none()

            if source:
                # 使用 JAR 模式快速测试
                jar_result = await _run_jar_test(
                    json.loads(source.source_json) if isinstance(source.source_json, str) else source.source_json,
                    source.source_type,
                    body.get("book_url", ""),
                )
                # 存储结果
                try:
                    from legado_client.storage import repository
                    result_dict = jar_result.to_storage_dict() if hasattr(jar_result, 'to_storage_dict') else {}
                    result_dict.update({"test_mode": "jar", "key": f"start_{source.id}"})
                    await repository.update_debug_result(source.id, result_dict)
                except Exception:
                    pass
                return {"ok": True, "data": {"task_id": f"debug_{source.id}", "result": _result_to_dict(jar_result)}}

    return {"ok": False, "data": None, "error": {"code": 404, "message": f"源 {source_url} 不存在"}}


@router.post("/{task_id}/stop")
async def debug_stop(task_id: str):
    """停止调试任务（占位端点，前端兼容）。"""
    return {"ok": True, "data": {"task_id": task_id, "stopped": True}}


@router.get("/{task_id}/result")
async def debug_result(task_id: str):
    """获取调试结果（占位端点，前端兼容）。"""
    return {"ok": True, "data": {"task_id": task_id, "status": "completed"}, "error": None}


@router.get("/{task_id}/logs")
async def debug_logs(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """获取调试日志（占位端点，前端兼容）。"""
    return {"ok": True, "data": {"task_id": task_id, "logs": [], "offset": offset, "limit": limit}, "error": None}


@router.post("/batch-verify")
async def batch_verify(body: dict):
    """批量验证源（前端 batchVerify 兼容端点）。"""
    urls = body.get("urls", [])
    task_id = f"batch_{id(urls)}"

    if not urls or not config.db_available:
        return {"ok": True, "data": {"task_id": task_id, "total": len(urls), "verified": 0}, "error": None}

    sf = get_session_factory()
    verified = 0
    if sf is not None:
        async with sf() as session:
            stmt = select(Source).where(Source.source_url.in_(urls))
            result = await session.execute(stmt)
            sources = list(result.scalars().all())

        for source in sources:
            jar_result = await _run_jar_test(
                json.loads(source.source_json) if isinstance(source.source_json, str) else source.source_json,
                source.source_type,
                "",
            )
            try:
                from legado_client.storage import repository
                result_dict = jar_result.to_storage_dict() if hasattr(jar_result, 'to_storage_dict') else {}
                result_dict.update({"test_mode": "jar", "key": f"batch_{source.id}"})
                await repository.update_debug_result(source.id, result_dict)
            except Exception:
                pass
            verified += 1

    return {"ok": True, "data": {"task_id": task_id, "total": len(urls), "verified": verified}, "error": None}


@router.get("/batch-verify/{task_id}/progress")
async def batch_verify_progress(task_id: str):
    """获取批量验证进度（占位端点，前端兼容）。"""
    return {"ok": True, "data": {"task_id": task_id, "progress": 100, "status": "completed"}, "error": None}


# ---- 内部辅助函数 ----

async def _run_device_test(
    source_data: dict,
    source_type: str,
    search_key: str,
    device_id: Optional[int] = None,
) -> DebugResultData:
    """在真机上执行测试。"""
    device = await _get_device_for_test(device_id)
    if device is None:
        return DebugResultData(
            source_type=source_type,
            status="error",
            message="无可用真机设备",
            test_mode="device",
        )

    host = device.ip if hasattr(device, "ip") else config.device_host
    port = device.port if hasattr(device, "port") else config.device_port
    token = device.auth_token if hasattr(device, "auth_token") else config.device_auth_token

    async with LegadoWebClient(host=host, port=port, auth_token=token or "") as client:
        try:
            if source_type == "book":
                if not search_key:
                    return DebugResultData(
                        source_type=source_type,
                        status="error",
                        message="书源测试需要提供 search_key",
                        test_mode="device",
                    )
                logs = await client.ws_debug_book_source(source_data, search_key)
                has_error = any("[ERROR]" in log for log in logs)
                return DebugResultData(
                    source_type=source_type,
                    status="fail" if has_error else "pass",
                    message="\n".join(logs[-5:]) if logs else "",
                    test_mode="device",
                )
            else:
                logs = await client.ws_debug_rss_source(source_data)
                has_error = any("[ERROR]" in log for log in logs)
                return DebugResultData(
                    source_type=source_type,
                    status="fail" if has_error else "pass",
                    message="\n".join(logs[-5:]) if logs else "",
                    test_mode="device",
                )
        except Exception as e:
            return DebugResultData(
                source_type=source_type,
                status="error",
                message=f"真机测试异常: {e}",
                test_mode="device",
            )


async def _run_jar_test(
    source_data: dict,
    source_type: str,
    search_key: str,
) -> DebugResultData:
    """在 JAR 仿真器上执行测试。"""
    try:
        from legado_client.utils.jvm_helpers import init_jvm_client
        client, jvm_ok = init_jvm_client()
        if not jvm_ok or client is None:
            return DebugResultData(
                source_type=source_type,
                status="error",
                message="JVM 仿真器不可用",
                test_mode="jar",
            )
        # 调用 JAR 验证
        result = client.validate_source(source_data, source_type)
        return DebugResultData(
            source_type=source_type,
            status="pass" if result.get("valid", False) else "fail",
            message=result.get("message", ""),
            test_mode="jar",
            confidence=result.get("confidence", ""),
        )
    except Exception as e:
        return DebugResultData(
            source_type=source_type,
            status="error",
            message=f"JAR 测试异常: {e}",
            test_mode="jar",
        )


async def _get_device_for_test(device_id: Optional[int] = None):
    """获取设备配置用于测试。"""
    from legado_client.server.routes.legado_proxy import _get_device
    return await _get_device(device_id)


def _compare_results(
    device_result: DebugResultData, jar_result: DebugResultData,
) -> dict:
    """对比真机和 JAR 测试结果。"""
    diffs = {
        "status_match": device_result.status == jar_result.status,
        "device_status": device_result.status,
        "jar_status": jar_result.status,
        "stages": {},
    }

    for stage in ("search", "detail", "toc", "content"):
        dev_st = getattr(device_result, f"{stage}_status", "skip")
        jar_st = getattr(jar_result, f"{stage}_status", "skip")
        diffs["stages"][stage] = {
            "device": dev_st,
            "jar": jar_st,
            "match": dev_st == jar_st,
        }

    diffs["has_diff"] = (
        not diffs["status_match"]
        or any(not v["match"] for v in diffs["stages"].values())
    )

    if diffs["has_diff"]:
        diffs["device_error"] = device_result.message
        diffs["jar_error"] = jar_result.message

    return diffs


def _result_to_dict(result: DebugResultData) -> dict:
    """将 DebugResultData 转为前端可用的字典。"""
    return {
        "status": result.status,
        "stage": result.stage,
        "message": result.message,
        "confidence": result.confidence,
        "test_mode": result.test_mode,
        "search_status": result.search_status,
        "detail_status": result.detail_status,
        "toc_status": result.toc_status,
        "content_status": result.content_status,
        "duration_ms": result.duration_ms,
    }


# ---- 批量校验任务存储 ----

_batch_tasks: dict[str, dict] = {}


# ---- 批量校验请求模型 ----

class BatchValidateRequest(BaseModel):
    """批量校验请求。"""
    source_type: str = Field("book", description="源类型：book 或 rss")
    mode: str = Field("connectivity", description="校验模式：device/jar/connectivity")
    source_ids: Optional[list[int]] = Field(None, description="源 ID 列表，None=全部")
    device_id: Optional[int] = Field(None, description="mode=device 时必填")
    check_search: bool = Field(True, description="是否检查搜索功能")
    check_detail: bool = Field(True, description="是否检查详情")
    check_toc: bool = Field(True, description="是否检查目录")
    check_content: bool = Field(False, description="是否检查正文")
    timeout: int = Field(30, ge=5, le=300, description="单源超时秒数")
    max_concurrent: int = Field(3, ge=1, le=10, description="最大并发数")


# ---- 4.24 批量校验 API ----

@router.post("/batch-validate")
async def batch_validate_sources(req: BatchValidateRequest):
    """批量校验源连通性与搜索功能。

    支持三种模式:
    - device: 真机 WebSocket 调试
    - jar: JAR 仿真器调试
    - connectivity: 仅域名连通性检查（最快）
    """
    if not config.db_available:
        raise HTTPException(status_code=503, detail="数据库不可用")

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="数据库会话不可用")

    # 查询源列表
    async with sf() as session:
        stmt = select(Source).where(Source.source_type == req.source_type)
        if req.source_ids:
            stmt = stmt.where(Source.id.in_(req.source_ids))
        result = await session.execute(stmt)
        sources = list(result.scalars().all())

    if not sources:
        return {
            "ok": True,
            "task_id": None,
            "status": "completed",
            "total": 0,
            "completed": 0,
            "results": [],
            "summary": {
                "alive": 0, "dead": 0,
                "search_pass": 0, "detail_pass": 0,
                "toc_pass": 0, "content_pass": 0,
            },
        }

    task_id = f"bv_{uuid.uuid4().hex[:12]}"

    # 初始化任务状态
    _batch_tasks[task_id] = {
        "status": "running",
        "total": len(sources),
        "completed": 0,
        "results": [],
        "summary": {
            "alive": 0, "dead": 0,
            "search_pass": 0, "detail_pass": 0,
            "toc_pass": 0, "content_pass": 0,
        },
    }

    # 后台异步执行
    asyncio.create_task(
        _run_batch_validate(task_id, sources, req, sf)
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "running",
        "total": len(sources),
        "completed": 0,
        "results": [],
        "summary": _batch_tasks[task_id]["summary"],
    }


@router.get("/batch-validate/{task_id}")
async def batch_validate_status(task_id: str):
    """查询批量校验进度。"""
    task = _batch_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "ok": True,
        "task_id": task_id,
        **task,
    }


async def _run_batch_validate(
    task_id: str,
    sources: list,
    req: BatchValidateRequest,
    sf,
):
    """后台执行批量校验。"""
    task = _batch_tasks[task_id]
    semaphore = asyncio.Semaphore(req.max_concurrent)

    async def _validate_one(source):
        async with semaphore:
            result_item = {
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
            try:
                source_data = (
                    json.loads(source.source_json)
                    if isinstance(source.source_json, str)
                    else source.source_json
                )

                if req.mode == "connectivity":
                    alive = await _check_connectivity(source.source_url, req.timeout)
                    result_item["connectivity"] = "pass" if alive else "fail"
                    result_item["message"] = "域名可达" if alive else "域名不可达"

                elif req.mode == "jar":
                    jar_result = await _run_jar_test(
                        source_data, req.source_type, ""
                    )
                    result_item["connectivity"] = "pass" if jar_result.status == "pass" else "fail"
                    result_item["message"] = jar_result.message
                    if req.check_search:
                        result_item["search"] = jar_result.search_status
                    if req.check_detail:
                        result_item["detail"] = jar_result.detail_status
                    if req.check_toc:
                        result_item["toc"] = jar_result.toc_status
                    if req.check_content:
                        result_item["content"] = jar_result.content_status

                elif req.mode == "device":
                    search_key = ""  # 简化说明：批量模式无关键词 | 已知上限：搜索测试跳过 | 升级路径：支持配置默认搜索词
                    device_result = await _run_device_test(
                        source_data, req.source_type, search_key, req.device_id
                    )
                    result_item["connectivity"] = "pass" if device_result.status == "pass" else "fail"
                    result_item["message"] = device_result.message
                    if req.check_search:
                        result_item["search"] = device_result.search_status
                    if req.check_detail:
                        result_item["detail"] = device_result.detail_status
                    if req.check_toc:
                        result_item["toc"] = device_result.toc_status
                    if req.check_content:
                        result_item["content"] = device_result.content_status

            except Exception as e:
                result_item["connectivity"] = "fail"
                result_item["message"] = str(e)

            # 更新任务状态
            task["results"].append(result_item)
            task["completed"] += 1

            if result_item["connectivity"] == "pass":
                task["summary"]["alive"] += 1
            else:
                task["summary"]["dead"] += 1

            for stage in ("search", "detail", "toc", "content"):
                if result_item.get(stage) == "pass":
                    task["summary"][f"{stage}_pass"] += 1

            # 更新数据库中的源测试状态
            try:
                from legado_client.storage import repository
                await repository.update_debug_result(source.id, {
                    "status": "pass" if result_item["connectivity"] == "pass" else "fail",
                    "test_mode": req.mode,
                    "key": f"batch_{task_id}",
                    "message": result_item["message"],
                    "search_status": result_item.get("search", "skip"),
                    "detail_status": result_item.get("detail", "skip"),
                    "toc_status": result_item.get("toc", "skip"),
                    "content_status": result_item.get("content", "skip"),
                })
            except Exception:
                pass

    # 并发执行所有校验
    await asyncio.gather(
        *[_validate_one(s) for s in sources],
        return_exceptions=True,
    )

    task["status"] = "completed"

    # 清理过期任务（保留最近 20 个）
    if len(_batch_tasks) > 20:
        oldest_keys = list(_batch_tasks.keys())[:len(_batch_tasks) - 20]
        for k in oldest_keys:
            _batch_tasks.pop(k, None)


async def _check_connectivity(source_url: str, timeout: int) -> bool:
    """检查源 URL 的域名 DNS + TCP 连通性。"""
    try:
        parsed = urlparse(source_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        # DNS + TCP 连接检查
        _, _ = await asyncio.wait_for(
            asyncio.get_event_loop().getaddrinfo(host, None),
            timeout=timeout,
        )
        # TCP 连通性检查
        fut = asyncio.get_event_loop().sock_connect(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            (host, port),
        )
        await asyncio.wait_for(fut, timeout=timeout)
        return True
    except Exception:
        return False
