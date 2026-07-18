#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库连接管理：异步 MySQL 会话、健康检测、降级策略。

基于 SQLAlchemy AsyncSession + aiomysql 连接池。
连接失败时不抛异常，标记 db_available=False 进入降级模式。
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from legado_client.utils.config import config

logger = logging.getLogger(__name__)

# 模块级引擎和会话工厂，由 init_db() 初始化
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db() -> bool:
    """初始化数据库引擎和连接池。

    Returns:
        True 表示连接成功并完成初始化，False 表示连接失败（降级模式）。
    """
    global _engine, _session_factory

    try:
        _engine = create_async_engine(
            config.db_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False,
        )
        # 验证连接可用
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        config.db_available = True
        logger.info("数据库初始化成功: %s:%d/%s", config.db_host, config.db_port, config.db_name)
        return True

    except Exception as e:
        config.db_available = False
        logger.warning("数据库连接失败，进入降级模式: %s", e)
        if _engine is not None:
            try:
                await _engine.dispose()
            except Exception:
                pass
            _engine = None
        _session_factory = None
        return False


def get_engine() -> Optional[AsyncEngine]:
    """获取当前引擎实例（供 repository 等模块使用）。"""
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """获取异步会话工厂（供 repository 等模块使用）。

    使用方式::

        sf = get_session_factory()
        async with sf() as session:
            result = await session.execute(...)
    """
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """获取异步数据库会话的上下文管理器。

    使用方式::
        async with get_session() as session:
            result = await session.execute(...)

    降级模式下 yield None，调用方应检查 config.db_available。
    """
    if _session_factory is None or not config.db_available:
        logger.debug("数据库不可用，返回 None 会话")
        yield None
        return

    session: AsyncSession = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_tables() -> None:
    """创建所有已注册的表（需要 Base metadata 已导入模型）。

    仅在 db_available=True 时执行。
    同时修正已有表中被截短的列为 MEDIUMTEXT。
    """
    if _engine is None or not config.db_available:
        logger.warning("数据库不可用，跳过建表")
        return

    from legado_client.storage.models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # 修正已有表的列类型（String → Text/MEDIUMTEXT）
        _alter_stmts = [
            "ALTER TABLE source MODIFY COLUMN source_url MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN source_name MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN source_icon MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN source_group MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN login_url MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN login_check_js MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN login_ui MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN book_url_pattern MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN explore_url MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN explore_screen MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN cover_decode_js MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_search MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_toc MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_explore MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_content MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_book_info MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_articles MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_title MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_image MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_link MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_next_page MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_pub_date MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN rule_description MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN domain_key MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN source_json MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN search_url MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN test_detail MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN device_jar_diff MEDIUMTEXT",
            "ALTER TABLE source MODIFY COLUMN notes MEDIUMTEXT",
        ]
        for stmt in _alter_stmts:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # 列已是目标类型时忽略

    logger.info("数据库表创建/验证完成")


class DatabaseHealthChecker:
    """数据库健康检测器：周期性探测连接状态，失败时标记降级。"""

    CHECK_INTERVAL: int = 30

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def start(self) -> None:
        """启动健康检测后台任务。"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("数据库健康检测已启动（间隔 %ds）", self.CHECK_INTERVAL)

    async def stop(self) -> None:
        """停止健康检测。"""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("数据库健康检测已停止")

    async def _check_loop(self) -> None:
        """周期性检测循环。"""
        while self._running:
            try:
                await self._check_once()
            except Exception as e:
                logger.error("健康检测异常: %s", e)

            for _ in range(self.CHECK_INTERVAL):
                if not self._running:
                    return
                await asyncio.sleep(1)

    async def _check_once(self) -> None:
        """执行一次连接检测。"""
        if _engine is None:
            config.db_available = False
            return

        try:
            async with _engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            if not config.db_available:
                logger.info("数据库连接恢复，退出降级模式")
            config.db_available = True
        except Exception as e:
            if config.db_available:
                logger.warning("数据库连接丢失，进入降级模式: %s", e)
            config.db_available = False


# 模块级健康检测器实例
health_checker = DatabaseHealthChecker()
