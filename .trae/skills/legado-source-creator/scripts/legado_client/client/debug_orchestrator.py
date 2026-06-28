#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DebugOrchestrator 编排器：组合 debug_runner + storage + auto_fixer + LegadoWebClient。

实现"查库→经验检索→测试→修复→重测→更新"完整闭环。

双路径（3.12）：
- Web 模式：LegadoWebClient 异步调用真机
- CLI 模式：run_and_return_v2 同步调用 JAR

mode 参数（3.17）：
- "auto"：真机优先→JAR 回退
- "device"：仅真机
- "jar"：仅 JAR 仿真
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from legado_client.client.debug_result import DebugResultData
from legado_client.experience.experience_manager import ExperienceManager
from legado_client.utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class _SimpleArgs:
    """简化参数对象，用于构造 debug_runner 所需的 args。"""
    key: str = "斗破苍穹"
    stage: str = ""
    timeout: int = 30
    max_iterations: int = 3
    no_experience: bool = False
    skip_db_lookup: bool = False
    db_only: bool = False
    source: str = ""
    output: str = ""


class DebugOrchestrator:
    """调试编排器：协调 storage / experience / debug_runner / LegadoWebClient。

    流程：
    1. 查数据库同域名源（3.11）
    2. 经验检索（3.13）
    3. 根据 mode 选择真机/JAR 测试（3.17）
    4. 失败则触发 auto_fixer
    5. 修复后重测
    6. 真机通过后自动触发 JAR 验证对比（3.18）
    7. 更新数据库
    """

    def __init__(
        self,
        storage=None,
        mode: str = "auto",
        web_client=None,
    ):
        """
        Args:
            storage: Repository 实例（可选，数据库不可用时降级）
            mode: 测试模式 "auto" / "device" / "jar"
            web_client: LegadoWebClient 实例（可选，真机模式需要）
        """
        self.storage = storage
        self.mode = mode
        self.web_client = web_client
        self._exp_mgr = ExperienceManager()

    # ==================== 主入口 ====================

    async def debug_source(
        self,
        source_url: str,
        source_type: str,
        key: str = "",
        source_json: str = "",
    ) -> DebugResultData:
        """完整调试闭环。

        Args:
            source_url: 源 URL
            source_type: "book" / "rss"
            key: 搜索关键词
            source_json: 完整源 JSON 字符串（可选）

        Returns:
            DebugResultData: 调试结果
        """
        if not source_json:
            source_json = await self._load_source_json(source_url, source_type)
        if not source_json:
            return DebugResultData(
                source_url=source_url, source_type=source_type,
                status="error", stage="load", message="源 JSON 未找到",
            )

        try:
            source_obj = json.loads(source_json)
        except json.JSONDecodeError as e:
            return DebugResultData(
                source_url=source_url, source_type=source_type,
                status="error", stage="parse", message=f"JSON 解析失败: {e}",
                source_json=source_json,
            )

        source_name = source_obj.get("bookSourceName") or source_obj.get("sourceName", "")

        # 3.13: 经验检索
        exp_context = self._search_experience(source_url, source_name)

        # 根据 mode 选择测试路径
        if self.mode in ("device", "auto"):
            device_result = await self._test_via_device(source_obj, source_type, key)
            if device_result.status == "pass":
                # 3.18: 真机通过后自动触发 JAR 验证对比
                jar_result = await self._test_via_jar(source_obj, source_type, key)
                if jar_result.status != "pass":
                    # 真机通过但 JAR 失败，记录差异
                    device_result.test_mode = "compare"
                    device_result.device_jar_diff = {
                        "device_status": device_result.status,
                        "jar_status": jar_result.status,
                        "jar_stage": jar_result.stage,
                        "jar_message": jar_result.message,
                    }
                else:
                    device_result.test_mode = "compare"
                # 更新数据库
                await self._update_storage(source_obj, source_type, device_result)
                return device_result

            # 真机失败
            if self.mode == "device":
                # 仅真机模式，触发修复
                fixed = await self._try_fix_and_retest(source_obj, source_type, key, device_result)
                await self._update_storage(source_obj, source_type, fixed)
                return fixed

        # JAR 模式 或 auto 回退
        jar_result = await self._test_via_jar(source_obj, source_type, key)
        if jar_result.status == "pass":
            await self._update_storage(source_obj, source_type, jar_result)
            return jar_result

        # JAR 失败，触发修复
        fixed = await self._try_fix_and_retest(source_obj, source_type, key, jar_result)
        await self._update_storage(source_obj, source_type, fixed)
        return fixed

    # ==================== 测试路径 ====================

    async def _test_via_device(
        self, source_obj: dict, source_type: str, key: str,
    ) -> DebugResultData:
        """Web 模式：通过 LegadoWebClient 真机测试（3.12）。"""
        if not self.web_client:
            return DebugResultData(
                source_url=source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", ""),
                source_type=source_type, status="error",
                stage="device", message="LegadoWebClient 未配置",
                test_mode="device",
            )

        started_at = datetime.now()
        source_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")
        source_name = source_obj.get("bookSourceName") or source_obj.get("sourceName", "")

        try:
            conn = await self.web_client.test_connection()
            if not conn["connected"]:
                return DebugResultData(
                    source_url=source_url, source_name=source_name,
                    source_type=source_type, status="error",
                    stage="device", message=f"真机连接失败: {conn['error']}",
                    test_mode="device", started_at=started_at,
                    finished_at=datetime.now(),
                )

            # 使用 WebSocket 调试
            if source_type == "book":
                logs = await self.web_client.ws_debug_book_source(source_obj, key or "斗破苍穹")
            else:
                logs = await self.web_client.ws_debug_rss_source(source_obj)

            # 解析调试日志判断结果
            success = any("成功" in line or "success" in line.lower() for line in logs[-5:])
            fail_stage = ""
            fail_msg = ""
            for line in logs:
                if "失败" in line or "error" in line.lower():
                    fail_msg = line[:200]
                    # 尝试提取失败阶段
                    for stage_name in ("搜索", "详情", "目录", "正文"):
                        if stage_name in line:
                            fail_stage = stage_name
                            break
                    break

            return DebugResultData(
                source_url=source_url, source_name=source_name,
                source_type=source_type,
                status="pass" if success else "fail",
                stage=fail_stage, message=fail_msg or ("通过" if success else "调试未返回明确结果"),
                confidence="high" if success else "low",
                test_mode="device",
                started_at=started_at, finished_at=datetime.now(),
                duration_ms=int((datetime.now() - started_at).total_seconds() * 1000),
                source_json=json.dumps(source_obj, ensure_ascii=False),
            )
        except Exception as e:
            logger.error("真机测试异常: %s", e)
            return DebugResultData(
                source_url=source_url, source_name=source_name,
                source_type=source_type, status="error",
                stage="device", message=str(e),
                test_mode="device", started_at=started_at,
                finished_at=datetime.now(),
            )

    async def _test_via_jar(
        self, source_obj: dict, source_type: str, key: str,
    ) -> DebugResultData:
        """CLI 模式：通过 run_and_return_v2 JAR 仿真测试（3.12）。"""
        try:
            from legado_client.client.debug_runner import run_and_return_v2
        except ImportError:
            return DebugResultData(
                source_url=source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", ""),
                source_type=source_type, status="error",
                stage="jar", message="debug_runner 模块导入失败",
                test_mode="jar",
            )

        args = _SimpleArgs(
            key=key or "斗破苍穹",
            timeout=30,
            max_iterations=1,
            no_experience=True,  # 经验检索已在编排层做
            skip_db_lookup=True,  # 数据库操作已在编排层做
        )

        try:
            result = await run_and_return_v2(args, source_obj, skip_db=True)
            result.test_mode = "jar"
            return result
        except Exception as e:
            logger.error("JAR 测试异常: %s", e)
            return DebugResultData(
                source_url=source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", ""),
                source_type=source_type, status="error",
                stage="jar", message=str(e),
                test_mode="jar",
            )

    # ==================== 修复流程 ====================

    async def _try_fix_and_retest(
        self,
        source_obj: dict,
        source_type: str,
        key: str,
        initial_result: DebugResultData,
    ) -> DebugResultData:
        """自动修复 + 重测闭环。"""
        from legado_client.analyzer.auto_fixer import auto_fix_error

        # 尝试自动修复
        error = {"msg": initial_result.message, "failedStage": initial_result.stage}
        source_json = json.dumps(source_obj, ensure_ascii=False)
        fix_result = auto_fix_error(error, source_json)

        if not fix_result.get("fixes_applied"):
            initial_result.fix_detail = {"attempted": True, "success": False, "fixes": []}
            return initial_result

        fixed_source = fix_result.get("fixed_source", source_obj)
        if not fixed_source:
            initial_result.fix_detail = {"attempted": True, "success": False, "fixes": fix_result.get("fixes_applied", [])}
            return initial_result

        # 修复后重测
        if self.mode == "device":
            retest_result = await self._test_via_device(fixed_source, source_type, key)
        else:
            retest_result = await self._test_via_jar(fixed_source, source_type, key)

        retest_result.fix_detail = {
            "attempted": True,
            "success": retest_result.status == "pass",
            "fixes": fix_result.get("fixes_applied", []),
        }
        if retest_result.status == "pass":
            retest_result.source_json = json.dumps(fixed_source, ensure_ascii=False)

        return retest_result

    # ==================== 辅助方法 ====================

    def _search_experience(self, source_url: str, source_name: str) -> str:
        """3.13: 经验检索。"""
        try:
            return self._exp_mgr.search(source_url, source_name)
        except Exception:
            return "无相似案例"

    async def _load_source_json(self, source_url: str, source_type: str) -> str:
        """从数据库加载源 JSON。"""
        if not self.storage:
            return ""

        try:
            from legado_client.storage.repository import find_by_domain
            from legado_client.storage.database import get_session_factory
            from urllib.parse import urlparse

            domain = ""
            try:
                parsed = urlparse(source_url if "://" in source_url else f"http://{source_url}")
                domain = (parsed.hostname or "").lower()
            except Exception:
                domain = source_url.lower()

            if not domain:
                return ""

            matches = await find_by_domain(domain, source_type)
            for m in matches:
                if m.source_url == source_url and m.source_json:
                    return m.source_json
        except Exception:
            pass

        return ""

    async def _update_storage(
        self, source_obj: dict, source_type: str, result: DebugResultData,
    ) -> None:
        """更新数据库。"""
        try:
            from legado_client.storage.repository import upsert_source, update_debug_result
            source_data = dict(source_obj)
            source_data["source_type"] = source_type
            source = await upsert_source(source_data)
            await update_debug_result(source.id, result.to_storage_dict())
        except Exception as e:
            logger.warning("更新数据库失败: %s", e)


if __name__ == "__main__":
    import asyncio

    # 自检：1正常 + 1边界 + 1异常
    # 正常用例：创建编排器
    orch = DebugOrchestrator(mode="jar")
    assert orch.mode == "jar"
    assert orch.storage is None
    print("✅ 正常用例：编排器创建正确")

    # 边界用例：经验检索
    exp = orch._search_experience("https://nonexistent.example.com", "测试源")
    assert isinstance(exp, str)
    print(f"✅ 边界用例：经验检索返回字符串: {exp[:30]}")

    # 异常用例：无 source_json 时 debug_source
    async def _test_no_json():
        result = await orch.debug_source("https://example.com", "book")
        assert result.status == "error"
        assert result.stage == "load"
        print("✅ 异常用例：无 source_json 返回 error")

    asyncio.run(_test_no_json())
