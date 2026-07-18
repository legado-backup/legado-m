#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JarOptimizer：真机通过但 JAR 失败时的优化闭环。

优化流程：
1. 差异分析：对比真机 vs JAR 结果
2. 源码定位：根据失败阶段映射到 Legado 源码类
3. JAR 代码修改建议
4. 回归测试（重新构建 JAR 后测试）

映射关系：
- search → BookList/BookSourceManager
- detail → BookInfo
- toc → BookContent/BookChapterList
- content → BookContent/BookContentDelegate
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from legado_client.client.debug_result import DebugResultData

logger = logging.getLogger(__name__)

# 失败阶段 → Legado 源码类映射
_STAGE_SOURCE_MAP: dict[str, dict[str, str]] = {
    "search": {
        "jvm_file": "BookList.java",
        "jvm_line": "约100-200行",
        "real_file": "BookSourceManager.kt",
        "real_line": "约300-400行",
        "note": "搜索结果解析逻辑，JAR 使用 jsoup，真机使用 AnalyzeRule",
    },
    "detail": {
        "jvm_file": "BookInfo.java",
        "jvm_line": "约50-150行",
        "real_file": "BookInfo.kt",
        "real_line": "约200-300行",
        "note": "详情页解析，CSS 选择器 + 字段映射",
    },
    "toc": {
        "jvm_file": "BookChapterList.java",
        "jvm_line": "约80-180行",
        "real_file": "BookContent.kt",
        "real_line": "约400-500行",
        "note": "目录解析，分页逻辑差异常见",
    },
    "content": {
        "jvm_file": "BookContentDelegate.java",
        "jvm_line": "约100-250行",
        "real_file": "BookContent.kt",
        "real_line": "约500-700行",
        "note": "正文解析，WebView/JS 执行差异最大",
    },
    "sort": {
        "jvm_file": "RssSort.java",
        "jvm_line": "约50-120行",
        "real_file": "RssSource.kt",
        "real_line": "约200-300行",
        "note": "订阅源分类解析",
    },
}

# 已知 JAR 差异模式
_KNOWN_DIFF_PATTERNS: list[dict[str, str]] = [
    {
        "pattern": "js执行差异",
        "symptom": "真机JS返回正确结果，JAR的Rhino执行报错或返回不同",
        "cause": "Rhino 1.8.1 vs V8/Android JS 引擎差异",
        "fix_suggestion": "检查JS代码是否使用了ES6+语法（箭头函数/模板字符串/解构赋值等），Rhino仅支持ES5",
    },
    {
        "pattern": "CSS选择器差异",
        "symptom": "真机能匹配元素，JAR的jsoup选择器返回空",
        "cause": "jsoup 1.16.2 不支持部分伪选择器(:has/:not复杂组合)",
        "fix_suggestion": "简化CSS选择器，避免伪类，用tag.class替代复杂选择器",
    },
    {
        "pattern": "网络请求差异",
        "symptom": "真机能获取页面，JAR返回403/503",
        "cause": "JAR的HTTP请求缺少WebView的Cookie/User-Agent",
        "fix_suggestion": "在searchUrl配置块中补全headers（UA/Cookie/Referer）",
    },
    {
        "pattern": "编码差异",
        "symptom": "真机正确显示中文，JAR返回乱码",
        "cause": "JAR默认UTF-8解码，部分GBK站点需显式指定charset",
        "fix_suggestion": "searchUrl配置块中添加 charset:gbk",
    },
    {
        "pattern": "WebView依赖",
        "symptom": "真机通过WebView渲染后能获取内容，JAR无法获取",
        "cause": "JAR不支持BackstageWebView，JS渲染的内容无法获取",
        "fix_suggestion": "标记源为需WebView渲染，配置loginUrl触发WebView（CF盾绕过模式）",
    },
]


class JarOptimizer:
    """JAR 优化器：真机通过但 JAR 失败时触发优化闭环。"""

    async def optimize(
        self,
        source_url: str,
        source_type: str,
        device_result: DebugResultData,
        jar_result: DebugResultData,
    ) -> dict[str, Any]:
        """优化闭环。

        Args:
            source_url: 源 URL
            source_type: "book" / "rss"
            device_result: 真机测试结果
            jar_result: JAR 测试结果

        Returns:
            {
                "diff_found": bool,
                "diff_detail": dict,
                "source_files": list,
                "fix_suggestion": str,
                "jar_fix_detail": dict,
                "regression_passed": bool,
            }
        """
        # 1. 差异分析
        diff_detail = self._analyze_diff(device_result, jar_result)
        diff_found = diff_detail.get("has_diff", False)

        if not diff_found:
            return {
                "diff_found": False,
                "diff_detail": diff_detail,
                "source_files": [],
                "fix_suggestion": "",
                "jar_fix_detail": {},
                "regression_passed": True,
            }

        # 2. 源码定位
        source_files = self._locate_source(jar_result.stage)

        # 3. 修复建议
        fix_suggestion = self._generate_fix_suggestion(jar_result, diff_detail)

        # 4. JAR 修改建议
        jar_fix_detail = self._generate_jar_fix(jar_result, diff_detail, source_files)

        # 5. 回归测试（标记为待执行，需要重建 JAR）
        regression_passed = False  # 需要重建 JAR 后才能验证

        return {
            "diff_found": True,
            "diff_detail": diff_detail,
            "source_files": source_files,
            "fix_suggestion": fix_suggestion,
            "jar_fix_detail": jar_fix_detail,
            "regression_passed": regression_passed,
        }

    # ==================== 差异分析 ====================

    def _analyze_diff(
        self, device_result: DebugResultData, jar_result: DebugResultData,
    ) -> dict[str, Any]:
        """对比真机 vs JAR 结果。"""
        diffs: dict[str, Any] = {
            "has_diff": False,
            "status_diff": device_result.status != jar_result.status,
            "stage_diff": device_result.stage != jar_result.stage,
            "confidence_diff": device_result.confidence != jar_result.confidence,
            "device_stages": {
                "search": device_result.search_status,
                "detail": device_result.detail_status,
                "toc": device_result.toc_status,
                "content": device_result.content_status,
            },
            "jar_stages": {
                "search": jar_result.search_status,
                "detail": jar_result.detail_status,
                "toc": jar_result.toc_status,
                "content": jar_result.content_status,
            },
        }

        # 找出差异阶段
        diff_stages = []
        for stage in ("search", "detail", "toc", "content"):
            dev_st = diffs["device_stages"][stage]
            jar_st = diffs["jar_stages"][stage]
            if dev_st != jar_st:
                diff_stages.append({"stage": stage, "device": dev_st, "jar": jar_st})

        diffs["diff_stages"] = diff_stages
        diffs["has_diff"] = (
            diffs["status_diff"]
            or bool(diff_stages)
            or jar_result.status != "pass"
        )
        diffs["jar_error"] = jar_result.message

        # 匹配已知差异模式
        diffs["matched_patterns"] = self._match_known_patterns(jar_result)

        return diffs

    def _match_known_patterns(self, jar_result: DebugResultData) -> list[dict[str, str]]:
        """匹配已知 JAR 差异模式。"""
        msg = (jar_result.message or "").lower()
        stage = jar_result.stage or ""
        matched = []

        for pattern in _KNOWN_DIFF_PATTERNS:
            # 基于错误消息和阶段匹配
            if pattern["pattern"] == "js执行差异" and (
                "js" in msg or "rhino" in msg or "script" in msg
            ):
                matched.append(pattern)
            elif pattern["pattern"] == "CSS选择器差异" and (
                "css" in msg or "选择器" in msg or "selector" in msg
            ):
                matched.append(pattern)
            elif pattern["pattern"] == "网络请求差异" and (
                "403" in msg or "503" in msg or "forbidden" in msg
            ):
                matched.append(pattern)
            elif pattern["pattern"] == "编码差异" and (
                "charset" in msg or "编码" in msg or "乱码" in msg
            ):
                matched.append(pattern)
            elif pattern["pattern"] == "WebView依赖" and (
                "webview" in msg or "渲染" in msg or stage == "content"
            ):
                matched.append(pattern)

        return matched

    # ==================== 源码定位 ====================

    def _locate_source(self, failed_stage: str) -> list[dict[str, str]]:
        """根据失败阶段映射到 Legado 源码类。"""
        if not failed_stage:
            return []

        info = _STAGE_SOURCE_MAP.get(failed_stage)
        if info:
            return [info]

        # 尝试模糊匹配
        for key, info in _STAGE_SOURCE_MAP.items():
            if key in failed_stage:
                return [info]

        return [{
            "jvm_file": "未知",
            "jvm_line": "未知",
            "real_file": "未知",
            "real_line": "未知",
            "note": f"无法映射阶段: {failed_stage}",
        }]

    # ==================== 修复建议 ====================

    def _generate_fix_suggestion(
        self, jar_result: DebugResultData, diff_detail: dict,
    ) -> str:
        """生成修复建议。"""
        suggestions = []

        matched = diff_detail.get("matched_patterns", [])
        if matched:
            for p in matched[:3]:
                suggestions.append(f"[{p['pattern']}] {p['fix_suggestion']}")

        # 通用建议
        if jar_result.stage == "content":
            suggestions.append("正文页差异常见于WebView渲染需求，建议配置loginUrl触发WebView")
        if jar_result.stage == "search":
            suggestions.append("搜索页差异常见于HTTP请求头，建议在searchUrl配置块补全headers")

        return "; ".join(suggestions) if suggestions else "需深入分析真机与JAR行为差异"

    # ==================== JAR 修改建议 ====================

    def _generate_jar_fix(
        self,
        jar_result: DebugResultData,
        diff_detail: dict,
        source_files: list[dict[str, str]],
    ) -> dict[str, Any]:
        """生成 JAR 代码修改建议。"""
        return {
            "target_files": [f["jvm_file"] for f in source_files],
            "modification_type": self._infer_modification_type(jar_result, diff_detail),
            "priority": "high" if jar_result.stage in ("search", "content") else "medium",
            "description": (
                f"JAR在{jar_result.stage or '未知'}阶段失败: {jar_result.message[:200]}"
                if jar_result.message else f"JAR在{jar_result.stage or '未知'}阶段失败"
            ),
        }

    def _infer_modification_type(
        self, jar_result: DebugResultData, diff_detail: dict,
    ) -> str:
        """推断 JAR 修改类型。"""
        msg = (jar_result.message or "").lower()
        if "js" in msg or "rhino" in msg:
            return "rhino_compat_fix"
        if "css" in msg or "selector" in msg:
            return "jsoup_compat_fix"
        if "403" in msg or "forbidden" in msg:
            return "http_header_fix"
        if "webview" in msg:
            return "webview_stub_fix"
        return "unknown"


if __name__ == "__main__":
    import asyncio

    # 自检：1正常 + 1边界 + 1异常
    optimizer = JarOptimizer()

    # 正常用例：真机通过+JAR失败
    async def _test_normal():
        device = DebugResultData(
            source_url="https://example.com", source_type="book",
            status="pass", confidence="high",
            search_status="pass", detail_status="pass",
            toc_status="pass", content_status="pass",
        )
        jar = DebugResultData(
            source_url="https://example.com", source_type="book",
            status="fail", stage="content",
            message="JS执行错误: ReferenceError",
            confidence="low",
            search_status="pass", detail_status="pass",
            toc_status="pass", content_status="fail",
        )
        result = await optimizer.optimize("https://example.com", "book", device, jar)
        assert result["diff_found"] is True
        assert len(result["source_files"]) > 0
        assert "rhino_compat_fix" in result["jar_fix_detail"]["modification_type"]
        print("✅ 正常用例：真机通过+JAR失败→差异检测+修复建议")

    asyncio.run(_test_normal())

    # 边界用例：真机和JAR都通过
    async def _test_both_pass():
        device = DebugResultData(status="pass", confidence="high")
        jar = DebugResultData(status="pass", confidence="high")
        result = await optimizer.optimize("https://example.com", "book", device, jar)
        assert result["diff_found"] is False
        print("✅ 边界用例：都通过→无差异")

    asyncio.run(_test_both_pass())

    # 异常用例：空结果
    async def _test_empty():
        device = DebugResultData()
        jar = DebugResultData()
        result = await optimizer.optimize("", "book", device, jar)
        assert isinstance(result, dict)
        print("✅ 异常用例：空结果→正常处理")

    asyncio.run(_test_empty())
