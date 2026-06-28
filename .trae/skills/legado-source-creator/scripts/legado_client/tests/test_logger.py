#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logger 单元测试。

同时支持：
- `python test_logger.py` 独立运行
- `pytest test_logger.py` 运行

被测模块：utils/logger.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import get_logger, _loggers


# ========== 正常用例 ==========

def test_get_logger_returns_logger():
    """get_logger 返回 logging.Logger 实例。"""
    logger = get_logger("test_logger_basic")
    assert isinstance(logger, logging.Logger)


def test_get_logger_default_name():
    """get_logger 默认名称为 legado_client。"""
    logger = get_logger()
    assert logger.name == "legado_client"


def test_get_logger_has_handler():
    """get_logger 配置了 StreamHandler。"""
    logger = get_logger("test_with_handler")
    assert len(logger.handlers) > 0
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_get_logger_level_info():
    """get_logger 默认级别为 INFO。"""
    logger = get_logger("test_level_info")
    assert logger.level == logging.INFO


def test_get_logger_custom_level():
    """get_logger 支持自定义级别。"""
    logger = get_logger("test_custom_level", level=logging.DEBUG)
    assert logger.level == logging.DEBUG


# ========== 边界用例 ==========

def test_get_logger_cached():
    """get_logger 同名返回缓存实例（同一对象）。"""
    # 清除缓存以确保测试干净
    name = "test_cache_logger"
    if name in _loggers:
        del _loggers[name]
    logger1 = get_logger(name)
    logger2 = get_logger(name)
    assert logger1 is logger2


def test_get_logger_no_duplicate_handlers():
    """get_logger 不会重复添加 handler。"""
    name = "test_no_dup_handler"
    if name in _loggers:
        del _loggers[name]
    logger1 = get_logger(name)
    handler_count_1 = len(logger1.handlers)
    logger2 = get_logger(name)
    handler_count_2 = len(logger2.handlers)
    assert handler_count_1 == handler_count_2


def test_get_logger_propagate_false():
    """get_logger 设置 propagate=False 避免向上传播。"""
    logger = get_logger("test_propagate")
    assert logger.propagate is False


def test_get_logger_formatter_format():
    """get_logger 的 formatter 包含时间/名称/级别。"""
    logger = get_logger("test_formatter")
    handler = logger.handlers[0]
    fmt = handler.formatter
    assert fmt is not None
    assert "%(asctime)s" in fmt._fmt
    assert "%(name)s" in fmt._fmt
    assert "%(levelname)s" in fmt._fmt


# ========== 异常用例 ==========

def test_get_logger_empty_name():
    """get_logger 空字符串名称不报错。"""
    logger = get_logger("")
    assert isinstance(logger, logging.Logger)


def test_get_logger_unicode_name():
    """get_logger 支持中文 logger 名称。"""
    logger = get_logger("中文日志器")
    assert logger.name == "中文日志器"


def test_logger_can_emit_log():
    """logger 能正常输出日志不抛异常。"""
    logger = get_logger("test_emit")
    # 捕获日志不输出到 stderr
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    try:
        logger.info("测试信息日志")
        logger.warning("测试警告日志")
        logger.error("测试错误日志")
    finally:
        logger.removeHandler(handler)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
