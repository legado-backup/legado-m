#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 API：概览、测试结果分布、内容类型分布、分组分布。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from legado_client.storage.database import get_session_factory
from legado_client.storage.models import Source
from legado_client.utils.config import config

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _db_check() -> dict[str, Any] | None:
    """数据库可用性检查。"""
    if not config.db_available:
        return {"ok": False, "data": None, "error": {"code": 503, "message": "数据库不可用"}}
    return None


@router.get("")
async def stats_index() -> dict[str, Any]:
    """统计概览（同 /overview，为前端 fetchStats 提供兼容端点）。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        type_stmt = select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)
        type_result = await session.execute(type_stmt)
        type_counts = {row[0]: row[1] for row in type_result.all()}

        status_stmt = select(Source.last_test_status, func.count(Source.id)).group_by(Source.last_test_status)
        status_result = await session.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        total = sum(type_counts.values())
        pass_count = status_counts.get("pass", 0)
        pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0.0

    data = {
        "total": total,
        "book_count": type_counts.get("book", 0),
        "rss_count": type_counts.get("rss", 0),
        "pass_count": pass_count,
        "fail_count": status_counts.get("fail", 0),
        "pass_rate": pass_rate,
    }
    return {"ok": True, "data": data, "error": None}


@router.get("/overview")
async def stats_overview() -> dict[str, Any]:
    """概览统计：源总数、通过率、书源数、订阅源数。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        # 按类型计数
        type_stmt = select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)
        type_result = await session.execute(type_stmt)
        type_counts = {row[0]: row[1] for row in type_result.all()}

        # 按测试状态计数
        status_stmt = select(Source.last_test_status, func.count(Source.id)).group_by(Source.last_test_status)
        status_result = await session.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        total = sum(type_counts.values())
        pass_count = status_counts.get("pass", 0)
        pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0.0

    data = {
        "total": total,
        "book_count": type_counts.get("book", 0),
        "rss_count": type_counts.get("rss", 0),
        "pass_count": pass_count,
        "fail_count": status_counts.get("fail", 0),
        "timeout_count": status_counts.get("timeout", 0),
        "error_count": status_counts.get("error", 0),
        "untested_count": status_counts.get("untested", 0),
        "pass_rate": pass_rate,
    }
    return {"ok": True, "data": data, "error": None}


@router.get("/test-result")
async def stats_test_result(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
) -> dict[str, Any]:
    """测试结果分布。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        stmt = select(Source.last_test_status, func.count(Source.id)).group_by(Source.last_test_status)
        if source_type:
            stmt = stmt.where(Source.source_type == source_type)
        result = await session.execute(stmt)
        distribution = {row[0]: row[1] for row in result.all()}

    return {"ok": True, "data": distribution, "error": None}


@router.get("/content-type")
async def stats_content_type(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
) -> dict[str, Any]:
    """内容类型分布（bookSourceType / rssType）。"""
    if err := _db_check():
        return err

    sf = get_session_factory()
    async with sf() as session:
        if source_type == "book" or source_type is None:
            # 书源类型分布：0文本/1音频/2图片/3文件/4视频
            book_stmt = select(Source.book_source_type, func.count(Source.id)).where(
                Source.source_type == "book"
            ).group_by(Source.book_source_type)
            book_result = await session.execute(book_stmt)
            book_dist = {str(row[0]): row[1] for row in book_result.all()}
        else:
            book_dist = {}

        if source_type == "rss" or source_type is None:
            # 订阅源类型分布：0网页/1图片/2视频
            rss_stmt = select(Source.rss_type, func.count(Source.id)).where(
                Source.source_type == "rss"
            ).group_by(Source.rss_type)
            rss_result = await session.execute(rss_stmt)
            rss_dist = {str(row[0]): row[1] for row in rss_result.all()}
        else:
            rss_dist = {}

    data = {"book_source_type": book_dist, "rss_type": rss_dist}
    return {"ok": True, "data": data, "error": None}


@router.get("/group")
async def stats_group(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
) -> dict[str, Any]:
    """分组分布：统计各分组下的源数量。"""
    if err := _db_check():
        return err

    from legado_client.storage.repository import get_groups

    try:
        groups = await get_groups(source_type)
    except Exception as e:
        return {"ok": False, "data": None, "error": {"code": 500, "message": str(e)}}

    # 统计每个分组的源数量
    sf = get_session_factory()
    group_counts: dict[str, int] = {}
    async with sf() as session:
        for group in groups:
            stmt = select(func.count(Source.id)).where(
                Source.source_group.like(f"%{group}%")
            )
            if source_type:
                stmt = stmt.where(Source.source_type == source_type)
            count = (await session.execute(stmt)).scalar_one()
            group_counts[group] = count

    # 按数量降序
    sorted_groups = dict(sorted(group_counts.items(), key=lambda x: x[1], reverse=True))

    return {"ok": True, "data": sorted_groups, "error": None}


@router.get("/group-distribution")
async def stats_group_distribution(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
) -> dict[str, Any]:
    """分组分布（/group 的别名，前端 fetchGroupDistribution 兼容端点）。"""
    return await stats_group(source_type)


@router.get("/type-distribution")
async def stats_type_distribution(
    source_type: str | None = Query(None, description="源类型过滤: book/rss"),
) -> dict[str, Any]:
    """类型分布（/content-type 的别名，前端 fetchTypeDistribution 兼容端点）。"""
    return await stats_content_type(source_type)


@router.get("/pass-rate-trend")
async def stats_pass_rate_trend(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
) -> dict[str, Any]:
    """通过率趋势（基于 last_test_at 按天统计）。"""
    if err := _db_check():
        return err

    from datetime import timedelta
    from sqlalchemy import cast, Date

    sf = get_session_factory()
    async with sf() as session:
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(
                cast(Source.last_test_at, Date).label("date"),
                Source.last_test_status,
                func.count(Source.id),
            )
            .where(Source.last_test_at >= since)
            .group_by("date", Source.last_test_status)
            .order_by("date")
        )
        result = await session.execute(stmt)
        rows = result.all()

    # 按日期聚合
    daily: dict[str, dict[str, int]] = {}
    for row in rows:
        date_str = str(row[0])
        status = row[1] or "untested"
        count = row[2]
        if date_str not in daily:
            daily[date_str] = {}
        daily[date_str][status] = count

    trend = []
    for date_str, status_counts in sorted(daily.items()):
        total = sum(status_counts.values())
        pass_count = status_counts.get("pass", 0)
        trend.append({
            "date": date_str,
            "total": total,
            "pass": pass_count,
            "pass_rate": round(pass_count / total * 100, 1) if total > 0 else 0.0,
        })

    return {"ok": True, "data": trend, "error": None}


@router.get("/test-mode")
async def stats_test_mode() -> dict[str, Any]:
    """真机 vs JAR 测试结果对比统计（4.23）。

    按测试模式(jar/device/compare)统计源数量、调试记录状态分布、
    真机与JAR差异数量、JAR优化统计。
    """
    if err := _db_check():
        return err

    from legado_client.storage.models import DebugResult

    sf = get_session_factory()
    async with sf() as session:
        # 按测试模式统计源数量
        mode_stats = {}
        for mode in ("jar", "device", "compare"):
            stmt = select(func.count(Source.id)).where(Source.test_mode == mode)
            result = await session.execute(stmt)
            mode_stats[mode] = result.scalar_one()

        # 按测试模式 + 状态统计调试记录
        debug_stats = {}
        for mode in ("jar", "device", "compare"):
            mode_debug = {}
            for status in ("pass", "fail", "timeout", "error"):
                stmt = select(func.count(DebugResult.id)).where(
                    DebugResult.test_mode == mode,
                    DebugResult.status == status,
                )
                result = await session.execute(stmt)
                mode_debug[status] = result.scalar_one()
            debug_stats[mode] = mode_debug

        # 真机 vs JAR 差异统计
        diff_count_stmt = select(func.count(Source.id)).where(
            Source.device_jar_diff.isnot(None),
        )
        diff_result = await session.execute(diff_count_stmt)
        diff_count = diff_result.scalar_one()

        # JAR 优化次数统计
        opt_stmt = select(
            func.count(Source.id),
            func.avg(Source.jar_optimization_count),
        ).where(Source.jar_optimization_count > 0)
        opt_result = await session.execute(opt_stmt)
        opt_row = opt_result.one()
        optimized_sources = opt_row[0] or 0
        avg_opt_count = float(opt_row[1] or 0)

        # 按源类型统计
        type_stats = {}
        for source_type in ("book", "rss"):
            stmt = select(func.count(Source.id)).where(Source.source_type == source_type)
            result = await session.execute(stmt)
            type_stats[source_type] = result.scalar_one()

    data = {
        "source_mode_stats": mode_stats,
        "debug_result_stats": debug_stats,
        "device_jar_diff_count": diff_count,
        "jar_optimization": {
            "optimized_sources": optimized_sources,
            "avg_optimization_count": round(avg_opt_count, 2),
        },
        "source_type_stats": type_stats,
    }
    return {"ok": True, "data": data, "error": None}
