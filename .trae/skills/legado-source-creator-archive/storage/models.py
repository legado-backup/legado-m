#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 模型：Source / Collection / DebugResult / DeviceConfig。

统一存储 BookSource 和 RssSource，通过 source_type 区分。
BookSource 特有字段在 source_type=rss 时为 NULL，反之亦然。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """声明式基类。"""
    pass


class Source(Base):
    """源表：统一存储 BookSource / RssSource。"""
    __tablename__ = "source"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Enum("book", "rss"), nullable=False)

    # 关键字段独立列（高频查询）
    source_url = Column(Text, nullable=False)
    source_name = Column(Text)
    source_icon = Column(Text)
    source_group = Column(Text)
    enabled = Column(Boolean, default=True)
    enabled_explore = Column(Boolean)  # BookSource 特有，RssSource 为 NULL
    has_login = Column(Boolean, default=False)
    login_url = Column(Text)
    login_check_js = Column(Text)
    login_ui = Column(Text)

    # BookSource 特有字段
    book_source_type = Column(Integer, default=0)  # 0文本/1音频/2图片/3文件/4视频
    book_url_pattern = Column(Text)
    search_url = Column(Text)  # MEDIUMTEXT via post-create ALTER
    explore_url = Column(Text)
    explore_screen = Column(Text)
    cover_decode_js = Column(Text)
    event_listener = Column(Boolean)  # RssSource 为 NULL
    custom_button = Column(Boolean)  # RssSource 为 NULL

    # BookSource 规则字段（JSON字符串）
    rule_search = Column(Text)
    rule_toc = Column(Text)
    rule_explore = Column(Text)

    # 通用规则字段
    rule_content = Column(Text)
    rule_book_info = Column(Text)  # BookSource 特有

    # RssSource 特有字段
    rss_type = Column(Integer)  # 0网页/1图片/2视频，BookSource 为 NULL
    rule_articles = Column(Text)
    rule_title = Column(Text)
    rule_image = Column(Text)
    rule_link = Column(Text)
    rule_next_page = Column(Text)
    rule_pub_date = Column(Text)
    rule_description = Column(Text)

    # 计算字段
    domain_key = Column(Text)

    # 测试结果
    last_test_at = Column(DateTime)
    last_test_status = Column(
        Enum("pass", "fail", "timeout", "error", "untested"), default="untested"
    )
    last_test_stage = Column(String(20))
    test_detail = Column(JSON)
    last_fix_detail = Column(JSON)
    respond_time = Column(Integer)
    weight = Column(Integer)  # BookSource 特有

    # 测试模式
    test_mode = Column(Enum("jar", "device", "compare"), default="jar")
    device_jar_diff = Column(JSON)
    jar_optimization_count = Column(Integer, default=0)
    last_jar_diff = Column(DateTime)

    # 完整 JSON
    source_json = Column(Text, nullable=False)

    # AI 闭环修复经验
    notes = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    debug_results = relationship(
        "DebugResult", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_source_url", "source_url"),
        Index("idx_domain_key", "domain_key"),
        Index("idx_test_status", "last_test_status"),
        Index("idx_source_type", "source_type"),
        Index("idx_enabled", "enabled"),
        Index("idx_book_source_type", "book_source_type"),
        Index("idx_rss_type", "rss_type"),
        Index("idx_last_test_at", "last_test_at"),
        Index("idx_source_group", "source_group", mysql_length=100),
        Index("idx_domain_type", "domain_key", "source_type"),
    )


class Collection(Base):
    """合集表：记录从 yckceo 等平台下载的源合集。"""
    __tablename__ = "collection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Enum("book", "rss"), nullable=False)
    remote_id = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    user_name = Column(String(100))
    source_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    date = Column(String(20))
    url = Column(Text)
    status = Column(
        Enum("pending", "downloading", "completed", "failed"), default="pending"
    )
    last_fetched_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_collection_remote_id", "remote_id", "source_type", unique=True),
        Index("idx_collection_status", "status"),
    )


class DebugResult(Base):
    """调试结果表：记录每次源调试的详细信息。"""
    __tablename__ = "debug_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False
    )
    key = Column(String(200))
    trigger = Column(Enum("ai", "web", "cli"), default="web")
    stage = Column(String(20))
    status = Column(Enum("pass", "fail", "timeout", "error"), nullable=False)
    message = Column(Text)
    search_status = Column(Enum("pass", "fail", "skip"), default="skip")
    detail_status = Column(Enum("pass", "fail", "skip"), default="skip")
    toc_status = Column(Enum("pass", "fail", "skip"), default="skip")
    content_status = Column(Enum("pass", "fail", "skip"), default="skip")
    confidence = Column(String(20))
    test_mode = Column(Enum("jar", "device", "compare"), default="jar")
    device_jar_diff = Column(JSON)
    fix_applied = Column(JSON)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    # 关系
    source = relationship("Source", back_populates="debug_results")

    __table_args__ = (
        Index("idx_debug_source_id", "source_id"),
        Index("idx_debug_status", "status"),
        Index("idx_debug_created_at", "created_at"),
    )


class DeviceConfig(Base):
    """设备配置表：管理 Legado 真机连接信息。"""
    __tablename__ = "device_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    ip = Column(String(50), nullable=False)
    port = Column(Integer, default=1122)  # HTTP端口，WebSocket端口=HTTP+1
    auth_token = Column(String(200))  # 预留字段
    is_default = Column(Boolean, default=False)
    last_connected_at = Column(DateTime)
    status = Column(Enum("online", "offline", "unknown"), default="unknown")
    created_at = Column(DateTime, default=func.now())
