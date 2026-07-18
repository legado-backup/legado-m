#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pydantic 请求/响应模型：源管理、调试、设备、合集等 API 的数据契约。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================

class SourceListRequest(BaseModel):
    """源列表查询参数。"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=200, description="每页数量")
    source_type: Optional[str] = Field(None, description="源类型: book/rss")
    book_source_type: Optional[int] = Field(None, ge=0, le=4, description="书源类型: 0文本/1音频/2图片/3文件/4视频")
    rss_type: Optional[int] = Field(None, ge=0, le=2, description="订阅源类型: 0网页/1图片/2视频")
    test_result: Optional[str] = Field(None, description="测试结果: pass/fail/timeout/error/untested")
    group: Optional[str] = Field(None, description="分组筛选（模糊匹配）")
    has_login: Optional[bool] = Field(None, description="是否需要登录")
    search: Optional[str] = Field(None, description="搜索关键词（名称/URL模糊匹配）")
    sort_by: str = Field("updated_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向: asc/desc")


class SourceUpdateRequest(BaseModel):
    """更新源请求。"""
    source_json: str = Field(..., description="完整的源 JSON 字符串")
    source_name: Optional[str] = Field(None, description="覆盖源名称")
    source_url: Optional[str] = Field(None, description="覆盖源 URL")
    source_group: Optional[str] = Field(None, description="覆盖分组")


class DebugStartRequest(BaseModel):
    """启动调试请求。"""
    source_id: int = Field(..., description="源 ID")
    key: str = Field("", description="搜索关键词")
    mode: str = Field("auto", description="调试模式: auto/device/jar")


class BatchDebugRequest(BaseModel):
    """批量调试请求。"""
    source_ids: Optional[list[int]] = Field(None, description="指定源 ID 列表")
    source_type: Optional[str] = Field(None, description="按源类型筛选")
    test_result: Optional[str] = Field(None, description="按测试结果筛选")
    group: Optional[str] = Field(None, description="按分组筛选")
    mode: str = Field("auto", description="调试模式: auto/device/jar")


class ImportUrlRequest(BaseModel):
    """URL 导入请求。"""
    url: str = Field(..., description="导入地址")
    source_type: str = Field("book", description="源类型: book/rss")


class DeviceCreateRequest(BaseModel):
    """创建/更新设备请求。"""
    name: str = Field(..., description="设备名称")
    ip: str = Field(..., description="设备 IP")
    port: int = Field(1122, ge=1, le=65535, description="HTTP 端口")
    auth_token: Optional[str] = Field(None, description="认证令牌")
    is_default: bool = Field(False, description="是否设为默认设备")


class BatchActionRequest(BaseModel):
    """批量操作请求。"""
    source_ids: list[int] = Field(..., description="源 ID 列表")
    action: Optional[str] = Field(None, description="操作类型: enable/disable/delete/export")
    params: Optional[dict[str, Any]] = Field(None, description="操作附加参数")


# ============================================================
# 响应模型
# ============================================================

class SourceItem(BaseModel):
    """源列表项（不含完整 JSON）。"""
    id: int
    source_type: str
    source_url: str
    source_name: str
    source_group: Optional[str] = None
    book_source_type: Optional[int] = None
    rss_type: Optional[int] = None
    last_test_status: Optional[str] = None
    last_test_at: Optional[datetime] = None
    enabled: bool = True
    has_login: Optional[bool] = None
    domain_key: Optional[str] = None

    model_config = {"from_attributes": True}


class SourceDetail(SourceItem):
    """源详情（含完整 JSON 和所有规则字段）。"""
    source_json: str
    source_icon: Optional[str] = None
    login_url: Optional[str] = None
    login_check_js: Optional[str] = None
    search_url: Optional[str] = None
    explore_url: Optional[str] = None
    rule_search: Optional[str] = None
    rule_toc: Optional[str] = None
    rule_explore: Optional[str] = None
    rule_content: Optional[str] = None
    rule_book_info: Optional[str] = None
    rule_articles: Optional[str] = None
    last_test_stage: Optional[str] = None
    test_detail: Optional[dict[str, Any]] = None
    test_mode: Optional[str] = None
    respond_time: Optional[int] = None
    weight: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    """源列表分页响应。"""
    items: list[SourceItem]
    total: int
    page: int
    page_size: int


class CollectionItem(BaseModel):
    """合集信息。"""
    id: int
    source_type: str
    remote_id: str
    title: str
    source_count: int = 0
    download_count: int = 0
    status: str = "pending"

    model_config = {"from_attributes": True}


class DebugHistoryItem(BaseModel):
    """调试历史记录项。"""
    id: int
    source_id: int
    status: str
    stage: Optional[str] = None
    message: Optional[str] = None
    test_mode: str = "jar"
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeviceItem(BaseModel):
    """设备信息。"""
    id: int
    name: str
    ip: str
    port: int = 1122
    auth_token: Optional[str] = None
    is_default: bool = False
    status: str = "unknown"

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    """健康检查响应。"""
    ok: bool
    database: bool = False
    jvm: bool = False
    version: str = "3.0.0"


class ImportResult(BaseModel):
    """导入结果。"""
    total: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0


class DebugWSMessage(BaseModel):
    """调试 WebSocket 消息。"""
    type: str = Field(..., description="消息类型: log/error/result/progress/complete")
    task_id: str = Field(..., description="任务 ID")
    stage: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class ValidateResult(BaseModel):
    """JSON 验证结果。"""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None


# ============================================================
# 统一响应包装
# ============================================================

class ApiResponse(BaseModel):
    """统一 API 响应格式。"""
    ok: bool = True
    data: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
