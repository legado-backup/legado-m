#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JVM 实例池管理：单实例 + asyncio.to_thread + Semaphore 并发控制。

暂不实现真实 JVM 启动（依赖现有 debug_runner），只提供接口框架。
后续集成 debug_runner 后，execute() 将在线程池中执行同步 JVM 调用。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class JvmPool:
    """JVM 实例池：单实例 + 信号量控制并发。

    设计要点：
    - 单 JVM 进程，通过 Semaphore 控制同一时刻仅一个调用进入
    - 同步 JVM 调用通过 asyncio.to_thread 桥接到异步
    - 预留 start/stop 生命周期，后续对接 debug_runner
    """

    _instance: Optional["JvmPool"] = None
    _semaphore: asyncio.Semaphore = asyncio.Semaphore(1)
    _started: bool = False

    @classmethod
    def get_instance(cls) -> "JvmPool":
        """获取单例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    async def start(cls) -> bool:
        """启动 JVM 实例。

        Returns:
            True 表示启动成功或已启动，False 表示启动失败。
        """
        if cls._started:
            return True

        try:
            # TODO: 后续对接 debug_runner 的 JAR 启动逻辑
            # from legado_client.utils.jvm_helpers import ...
            # await asyncio.to_thread(start_jvm, ...)
            logger.info("JVM 池启动（暂为空壳，等待对接 debug_runner）")
            cls._started = True
            return True
        except Exception as e:
            logger.error("JVM 启动失败: %s", e)
            return False

    @classmethod
    async def stop(cls) -> None:
        """停止 JVM 实例并释放资源。"""
        if not cls._started:
            return

        try:
            # TODO: 后续对接 JVM 关闭逻辑
            logger.info("JVM 池停止（暂为空壳）")
        except Exception as e:
            logger.error("JVM 停止异常: %s", e)
        finally:
            cls._started = False

    @classmethod
    def is_available(cls) -> bool:
        """JVM 是否可用。"""
        return cls._started

    @classmethod
    async def execute(cls, func: Callable[..., Any], *args: Any) -> Any:
        """在线程池中执行同步 JVM 调用。

        通过 Semaphore 保证同一时刻仅一个 JVM 调用执行，
        asyncio.to_thread 将同步调用桥接到异步事件循环。

        Args:
            func: 同步函数（JVM 调用）
            *args: 函数参数

        Returns:
            函数返回值

        Raises:
            RuntimeError: JVM 未启动时调用
        """
        if not cls._started:
            raise RuntimeError("JVM 未启动，请先调用 JvmPool.start()")

        async with cls._semaphore:
            return await asyncio.to_thread(func, *args)
