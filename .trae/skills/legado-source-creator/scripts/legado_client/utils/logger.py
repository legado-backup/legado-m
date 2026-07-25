#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志管理：统一的 get_logger() 函数。"""
from __future__ import annotations

import logging
import sys
from typing import Optional

# 模块级缓存，避免重复添加 handler
_loggers: dict = {}


def get_logger(name: str = "legado_client", level: int = logging.INFO) -> logging.Logger:
    """获取统一配置的 logger。

    Args:
        name: logger 名称
        level: 日志级别

    Returns:
        配置好的 logging.Logger 实例
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加 handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    _loggers[name] = logger
    return logger
