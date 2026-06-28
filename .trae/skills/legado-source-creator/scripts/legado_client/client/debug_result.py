#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试结果数据类：DebugResultData。

与 storage/models.py 的 DebugResult ORM 模型解耦，本模块为纯数据载体，
用于 debug_runner / DebugOrchestrator 等运行时传递，不依赖 SQLAlchemy。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DebugResultData:
    """调试结果数据类，贯穿 debug_runner → DebugOrchestrator → storage 全链路。"""

    source_url: str = ""
    source_name: str = ""
    source_type: str = ""  # "book" / "rss"
    status: str = "error"  # "pass" / "fail" / "timeout" / "error"
    stage: str = ""  # 失败阶段
    message: str = ""
    search_status: str = "skip"
    detail_status: str = "skip"
    toc_status: str = "skip"
    content_status: str = "skip"
    confidence: str = ""
    test_mode: str = "jar"  # "jar" / "device" / "compare"
    device_jar_diff: Optional[dict] = None
    fix_detail: Optional[dict] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    source_json: str = ""  # 完整源JSON

    def to_storage_dict(self) -> dict:
        """转换为 storage/repository.update_debug_result() 所需的字典格式。"""
        return {
            "status": self.status,
            "stage": self.stage,
            "message": self.message,
            "search_status": self.search_status,
            "detail_status": self.detail_status,
            "toc_status": self.toc_status,
            "content_status": self.content_status,
            "confidence": self.confidence,
            "test_mode": self.test_mode,
            "device_jar_diff": self.device_jar_diff,
            "fix_applied": self.fix_detail,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
        }


if __name__ == "__main__":
    # 自检：1正常 + 1边界 + 1异常
    # 正常用例：完整数据
    r = DebugResultData(
        source_url="https://example.com", source_name="测试源",
        source_type="book", status="pass", stage="content",
        message="全部通过", confidence="high", duration_ms=1500,
        started_at=datetime(2026, 1, 1), finished_at=datetime(2026, 1, 1),
    )
    d = r.to_storage_dict()
    assert d["status"] == "pass" and d["confidence"] == "high"
    print("✅ 正常用例通过")

    # 边界用例：默认值
    r2 = DebugResultData()
    d2 = r2.to_storage_dict()
    assert d2["status"] == "error" and d2["test_mode"] == "jar"
    assert d2["device_jar_diff"] is None
    print("✅ 边界用例通过")

    # 异常用例：source_json 为空字符串
    r3 = DebugResultData(source_json="")
    assert r3.source_json == ""
    print("✅ 异常用例通过")
