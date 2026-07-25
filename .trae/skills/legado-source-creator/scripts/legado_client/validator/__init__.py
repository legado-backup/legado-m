#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validator 模块：源字段校验器。

v4 新增模块，用于强制校验源 JSON 必填字段（基于"优秀好用"标准）。

子模块：
- mandatory_fields: 必填字段校验器（CRITICAL/MANDATORY/RECOMMENDED 三级）
"""
from legado_client.validator.mandatory_fields import (
    MandatoryFieldValidator,
    validate_source,
    format_validation_report,
    BOOK_SOURCE_FIELDS,
    RSS_SOURCE_FIELDS,
)

__all__ = [
    "MandatoryFieldValidator",
    "validate_source",
    "format_validation_report",
    "BOOK_SOURCE_FIELDS",
    "RSS_SOURCE_FIELDS",
]
