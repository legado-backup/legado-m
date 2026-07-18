#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI 应用入口：中间件、日志配置、异常处理、生命周期、路由挂载。

包含：
- 4.13 数据库降级中间件（MySQL 不可用时 /api/* 返回 503）
- 4.14 /api/health 健康检查
- 4.16 请求日志中间件
- 4.17 RotatingFileHandler 日志轮转
- 4.18 日志级别环境变量控制
- 4.19 请求体大小限制（10MB）
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from legado_client.server.jvm_pool import JvmPool
from legado_client.utils.config import config

# ---- 4.18 日志级别环境变量控制 ----
_log_level_name = os.environ.get("LEGADO_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)

# 配置 legado_client 根 logger
_logger = logging.getLogger("legado_client")
_logger.setLevel(_log_level)

# 第三方库日志降级
for _noise in ("uvicorn.access", "httpx", "sqlalchemy.engine", "httpcore"):
    logging.getLogger(_noise).setLevel(logging.WARNING)

# ---- 4.17 RotatingFileHandler 日志轮转 ----
_log_dir = config.output_dir
_log_dir.mkdir(parents=True, exist_ok=True)
_file_handler = RotatingFileHandler(
    _log_dir / "server.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setLevel(_log_level)
_file_formatter = logging.Formatter(
    "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_file_handler.setFormatter(_file_formatter)
_logger.addHandler(_file_handler)

# 控制台输出
_console_handler = logging.StreamHandler()
_console_handler.setLevel(_log_level)
_console_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
_console_handler.setFormatter(_console_formatter)
_logger.addHandler(_console_handler)

logger = _logger


# ---- 4.19 请求体大小限制中间件 ----
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体大小，超过 max_body_size 返回 413。"""

    def __init__(self, app, max_body_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={"ok": False, "error": {"code": "PAYLOAD_TOO_LARGE", "message": f"请求体超过 {self.max_body_size // (1024*1024)}MB 限制"}},
                    )
            except ValueError:
                pass
        return await call_next(request)


# ---- 4.13 数据库降级中间件 ----
class DatabaseDegradationMiddleware(BaseHTTPMiddleware):
    """MySQL 不可用时，/api/* 路由返回 503（健康检查和静态资源除外）。"""

    # 不受降级影响的路径前缀
    _EXEMPT_PREFIXES = ("/api/health", "/assets", "/docs", "/openapi.json", "/redoc")

    async def dispatch(self, request: Request, call_next):
        if not config.db_available and request.url.path.startswith("/api/"):
            if any(request.url.path.startswith(p) for p in self._EXEMPT_PREFIXES):
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "error": {
                        "code": "DATABASE_UNAVAILABLE",
                        "message": "数据库不可用，服务处于降级模式",
                    },
                },
            )
        return await call_next(request)


# ---- 4.16 请求日志中间件 ----
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录 API 请求方法/路径/状态码/耗时（跳过 /ws 和 /assets）。"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        path = request.url.path
        if not path.startswith(("/ws", "/assets")):
            logger.info(
                "%s %s -> %d (%.1fms)",
                request.method,
                path,
                response.status_code,
                duration * 1000,
            )
        return response


# ---- Lifespan ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化资源，关闭时清理。"""
    # ---- 启动 ----
    from legado_client.storage.database import init_db, create_tables, health_checker

    db_ok = await init_db()
    if db_ok:
        await create_tables()
        await health_checker.start()
        logger.info("数据库已就绪，健康检测已启动")
    else:
        logger.warning("数据库不可用，服务以降级模式运行")

    # 预留：JVM 池启动（暂不启动真实 JVM）
    # await JvmPool.start()

    yield

    # ---- 关闭 ----
    await health_checker.stop()
    await JvmPool.stop()
    logger.info("服务已关闭，资源已释放")


# ---- 创建 FastAPI 应用 ----
app = FastAPI(
    title="Legado Client",
    version="3.0.0",
    description="Legado 书源/订阅源管理 Web 服务",
    lifespan=lifespan,
)

# ---- 中间件注册（注意顺序：后注册的先执行） ----

# CORS 中间件：允许前端开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4.16 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 4.13 数据库降级中间件
app.add_middleware(DatabaseDegradationMiddleware)

# 4.19 请求体大小限制中间件
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)


# ---- 全局异常处理 ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常统一返回 {ok: false, error: {code, message}}。"""
    logger.error("未处理异常 [%s %s]: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {"code": "INTERNAL_ERROR", "message": "服务内部错误"},
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """参数校验错误。"""
    return JSONResponse(
        status_code=400,
        content={
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": str(exc)},
        },
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """运行时错误（如数据库未初始化）。"""
    return JSONResponse(
        status_code=503,
        content={
            "ok": False,
            "error": {"code": "SERVICE_UNAVAILABLE", "message": str(exc)},
        },
    )


# ---- 注册路由 ----
from legado_client.server.routes.sources import router as sources_router  # noqa: E402
from legado_client.server.routes.stats import router as stats_router  # noqa: E402
from legado_client.server.routes.device import router as device_router  # noqa: E402
from legado_client.server.routes.collections import router as collections_router  # noqa: E402
from legado_client.server.routes.import_export import router as import_export_router  # noqa: E402
from legado_client.server.routes.legado_proxy import router as legado_proxy_router  # noqa: E402
from legado_client.server.routes.debug import router as debug_router  # noqa: E402

app.include_router(sources_router)
app.include_router(stats_router)
app.include_router(device_router)
app.include_router(collections_router)
app.include_router(import_export_router)
app.include_router(legado_proxy_router)
app.include_router(debug_router)


# ---- 4.14 健康检查 ----
@app.get("/api/health", tags=["系统"])
async def health_check():
    """服务健康检查：数据库状态、JVM 状态、版本。"""
    from legado_client.server.schemas import HealthResponse

    db_ok = config.db_available
    jvm_ok = JvmPool.is_available()
    resp = HealthResponse(
        ok=db_ok or jvm_ok,  # 至少一个可用就算健康
        database=db_ok,
        jvm=jvm_ok,
    )
    return {"ok": resp.ok, "data": resp.model_dump()}


# ---- 导出端点（前端 exportSources 调用 /api/export）----
@app.post("/api/export", tags=["导入导出"])
async def export_sources(body: dict):
    """导出源 JSON：按 URL 列表导出指定源的 JSON 数据。"""
    if not config.db_available:
        return {"ok": False, "data": None, "error": {"code": 503, "message": "数据库不可用"}}

    import json
    from sqlalchemy import select
    from legado_client.storage.models import Source
    from legado_client.storage.database import get_session_factory

    urls = body.get("urls", [])
    fmt = body.get("format", "json")
    sf = get_session_factory()

    exported: list[dict] = []
    async with sf() as session:
        if urls:
            stmt = select(Source).where(Source.source_url.in_(urls))
        else:
            stmt = select(Source).limit(1000)
        result = await session.execute(stmt)
        sources = list(result.scalars().all())

        for s in sources:
            if s.source_json:
                try:
                    exported.append(json.loads(s.source_json))
                except json.JSONDecodeError:
                    pass

    if fmt == "txt":
        from fastapi.responses import PlainTextResponse
        text = "\n\n".join(json.dumps(item, ensure_ascii=False, indent=2) for item in exported)
        return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")

    return {"ok": True, "data": {"items": exported, "count": len(exported)}, "error": None}


# ---- 静态文件挂载（SPA 回退，必须放在所有路由之后）----
import pathlib as _pl

_web_dist = _pl.Path(__file__).resolve().parent.parent / "web" / "dist"
if _web_dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_web_dist), html=True), name="static")
