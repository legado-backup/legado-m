#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mandatory_fields.py — 必填字段校验器（v4）

基于"优秀好用"标准（非"能用"标准）强制校验源 JSON 必填字段。

设计依据：
- 源码分析：docs/temp-analysis/legado_mandatory_fields.md
- 用户反馈：生成的源缺 sourceIcon/searchUrl/sortUrl = 不可用 = 用户要手动补 DB
- 优秀标准：不止能用，还要 UI 美观 + 功能完整 + 可管理

字段分类：
- CRITICAL：不填无法导入或核心功能崩溃
- MANDATORY：不填影响核心功能（搜索/列表/正文）
- RECOMMENDED：不填影响"优秀好用"标准（图标/分类/分组）
- OPTIONAL：高级功能，可选

校验失败行为：
- CRITICAL 缺失：拒绝输出，强制 AI 补全
- MANDATORY 缺失：拒绝输出，强制 AI 补全
- RECOMMENDED 缺失：警告，建议补全但不阻塞
- OPTIONAL 缺失：静默通过
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


# ==================== BookSource 必填字段清单 ====================

BOOK_SOURCE_FIELDS: Dict[str, Dict[str, Any]] = {
    # === CRITICAL（不填无法导入） ===
    "bookSourceUrl": {
        "level": "CRITICAL",
        "type": str,
        "description": "书源主键 URL，导入时非空校验",
        "empty_means": "无法导入，抛 NoStackTraceException",
    },

    # === MANDATORY（核心功能） ===
    "bookSourceName": {
        "level": "MANDATORY",
        "type": str,
        "description": "书源名称，UI 显示",
        "empty_means": "UI 显示混乱，管理困难",
    },
    "searchUrl": {
        "level": "MANDATORY",
        "type": str,
        "description": "搜索 URL，搜索功能必填",
        "empty_means": "搜索功能不可用（抛搜索url不能为空）",
    },
    "ruleSearch.bookList": {
        "level": "MANDATORY",
        "type": str,
        "description": "搜索结果列表规则",
        "empty_means": "搜索结果无法解析",
    },
    "ruleSearch.name": {
        "level": "MANDATORY",
        "type": str,
        "description": "搜索结果书名规则",
        "empty_means": "搜索结果无书名",
    },
    "ruleBookInfo.name": {
        "level": "MANDATORY",
        "type": str,
        "description": "详情页书名规则",
        "empty_means": "详情页无书名",
    },
    "ruleBookInfo.author": {
        "level": "MANDATORY",
        "type": str,
        "description": "详情页作者规则",
        "empty_means": "详情页无作者",
    },
    "ruleToc.chapterList": {
        "level": "MANDATORY",
        "type": str,
        "description": "章节列表规则",
        "empty_means": "无法获取章节目录",
    },
    "ruleContent.content": {
        "level": "MANDATORY",
        "type": str,
        "description": "正文规则",
        "empty_means": "无法获取正文",
    },

    # === RECOMMENDED（优秀好用） ===
    "bookSourceGroup": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "书源分组（如：测试/视频/小说）",
        "empty_means": "管理混乱，无法按分组筛选",
    },
    "bookSourceType": {
        "level": "RECOMMENDED",
        "type": int,
        "description": "书源类型 0文本/1音频/2图片/3文件/4视频",
        "empty_means": "默认 0（文本），视频源需显式设为 4",
    },
    "exploreUrl": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "发现页 URL",
        "empty_means": "无发现页功能",
    },
    "ruleBookInfo.coverImageUrl": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "详情页封面图规则",
        "empty_means": "无封面图，UI 不美观",
    },
    "ruleBookInfo.intro": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "详情页简介规则",
        "empty_means": "无简介，用户无法预判内容",
    },
}


# ==================== RssSource 必填字段清单 ====================

RSS_SOURCE_FIELDS: Dict[str, Dict[str, Any]] = {
    # === CRITICAL（不填无法导入） ===
    "sourceUrl": {
        "level": "CRITICAL",
        "type": str,
        "description": "订阅源主键 URL，导入时非空校验",
        "empty_means": "无法导入，抛 NoStackTraceException",
    },

    # === MANDATORY（核心功能） ===
    "sourceName": {
        "level": "MANDATORY",
        "type": str,
        "description": "订阅源名称，UI 显示",
        "empty_means": "UI 显示混乱",
    },
    "ruleArticles": {
        "level": "MANDATORY",
        "type": str,
        "description": "文章列表规则",
        "empty_means": "列表无法解析（fallback 到默认 RSS 解析器，自定义网页失效）",
    },
    "ruleTitle": {
        "level": "MANDATORY",
        "type": str,
        "description": "文章标题规则",
        "empty_means": "列表项无标题",
    },
    "ruleLink": {
        "level": "MANDATORY",
        "type": str,
        "description": "文章链接规则",
        "empty_means": "无法跳转详情",
    },
    "ruleContent": {
        "level": "OPTIONAL",
        "type": str,
        "description": "正文规则（视频源 sniff 模式可不填，自动嗅探）",
        "empty_means": "正文规则缺失，视频源自动降级到 sniff 嗅探模式（功能仍可用，显式规则更稳定）",
    },

    # === RECOMMENDED（优秀好用，用户明确要求） ===
    "sourceIcon": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "源图标 URL（用户明确要求必填）",
        "empty_means": "UI 无图标，不美观",
    },
    "searchUrl": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "搜索 URL（用户明确要求必填）",
        "empty_means": "搜索功能不可用",
    },
    "sortUrl": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "分类 URL（用户明确要求必填）",
        "empty_means": "无法切换分类，只能浏览默认分类",
    },
    "sourceGroup": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "源分组",
        "empty_means": "管理混乱",
    },
    "sourceComment": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "源注释（说明解析逻辑）",
        "empty_means": "无法理解源的设计",
    },
    "type": {
        "level": "RECOMMENDED",
        "type": int,
        "description": "源类型 0网页/1图片/2视频",
        "empty_means": "默认 0（网页），视频源需显式设为 2",
    },
    "ruleImage": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "文章图片规则",
        "empty_means": "列表无缩略图",
    },
    "ruleDescription": {
        "level": "OPTIONAL",
        "type": str,
        "description": "文章描述规则（播放数/观看数等，非所有站点都有）",
        "empty_means": "列表无摘要（很多站点不展示播放数，可不填）",
    },
    "ruleNextPage": {
        "level": "RECOMMENDED",
        "type": str,
        "description": "下一页规则",
        "empty_means": "无法分页加载",
    },
}


# ==================== 校验器 ====================

class MandatoryFieldValidator:
    """必填字段校验器。

    校验标准：优秀好用（非能用）
    校验层级：CRITICAL > MANDATORY > RECOMMENDED > OPTIONAL
    失败行为：
        - CRITICAL/MANDATORY 缺失：返回 missing_fields，调用方应拒绝输出
        - RECOMMENDED 缺失：返回 warning_fields，调用方应警告补全
    """

    def __init__(self, strict_recommended: bool = True):
        """
        Args:
            strict_recommended: True 时 RECOMMENDED 也视为缺失（用户"优秀好用"标准）
        """
        self.strict_recommended = strict_recommended

    def validate(self, source_dict: dict, source_type: str = "rss") -> dict:
        """校验源 JSON 必填字段。

        Args:
            source_dict: 源字典
            source_type: "book" 或 "rss"

        Returns:
            {
                "passed": bool,          # True=通过，False=有缺失
                "missing_critical": [],  # CRITICAL 缺失字段（必须补全）
                "missing_mandatory": [], # MANDATORY 缺失字段（必须补全）
                "warning_recommended": [], # RECOMMENDED 缺失字段（建议补全）
                "all_missing": [],       # 所有缺失字段汇总
                "details": [],           # 每个字段的校验详情
            }
        """
        fields = (BOOK_SOURCE_FIELDS if source_type == "book"
                  else RSS_SOURCE_FIELDS)

        missing_critical: List[str] = []
        missing_mandatory: List[str] = []
        warning_recommended: List[str] = []
        details: List[Dict[str, Any]] = []

        for field_path, spec in fields.items():
            value = self._get_nested(source_dict, field_path)
            is_empty = self._is_empty(value, spec.get("type", str))

            if is_empty:
                level = spec["level"]
                detail = {
                    "field": field_path,
                    "level": level,
                    "description": spec["description"],
                    "empty_means": spec["empty_means"],
                }
                details.append(detail)

                if level == "CRITICAL":
                    missing_critical.append(field_path)
                elif level == "MANDATORY":
                    missing_mandatory.append(field_path)
                elif level == "RECOMMENDED":
                    warning_recommended.append(field_path)

        all_missing = missing_critical + missing_mandatory
        if self.strict_recommended:
            all_missing = all_missing + warning_recommended

        passed = len(missing_critical) == 0 and len(missing_mandatory) == 0
        if self.strict_recommended:
            passed = passed and len(warning_recommended) == 0

        return {
            "passed": passed,
            "missing_critical": missing_critical,
            "missing_mandatory": missing_mandatory,
            "warning_recommended": warning_recommended,
            "all_missing": all_missing,
            "details": details,
        }

    def _get_nested(self, d: dict, path: str) -> Any:
        """按点分隔路径获取嵌套字段值。

        Args:
            d: 字典
            path: 如 "ruleSearch.bookList"

        Returns:
            字段值，不存在返回 None
        """
        keys = path.split(".")
        current: Any = d
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if current is None:
                return None
        return current

    def _is_empty(self, value: Any, expected_type: type) -> bool:
        """判断字段是否为空。

        None / "" / 0 (当期望非 0) / [] / {} 视为空。
        False 不视为空（是有效布尔值）。
        """
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False


# ==================== 便捷函数 ====================

def validate_source(source_dict: dict, source_type: str = "rss",
                    strict_recommended: bool = True) -> dict:
    """便捷校验函数。

    Args:
        source_dict: 源字典
        source_type: "book" 或 "rss"
        strict_recommended: True 时 RECOMMENDED 视为缺失

    Returns:
        校验结果字典（见 MandatoryFieldValidator.validate）
    """
    validator = MandatoryFieldValidator(strict_recommended=strict_recommended)
    return validator.validate(source_dict, source_type)


def format_validation_report(result: dict, source_name: str = "") -> str:
    """格式化校验结果为可读报告。

    Args:
        result: validate_source 返回的结果
        source_name: 源名称（用于报告标题）

    Returns:
        格式化的报告字符串
    """
    lines = []
    title = f"必填字段校验报告：{source_name}" if source_name else "必填字段校验报告"
    lines.append("=" * 60)
    lines.append(title)
    lines.append("=" * 60)

    if result["passed"]:
        lines.append("[PASS] 全部必填字段通过")
    else:
        lines.append(f"[FAIL] {len(result['all_missing'])} 个字段缺失")

    if result["missing_critical"]:
        lines.append(f"\n[CRITICAL] {len(result['missing_critical'])} 个必填字段缺失（必须补全）：")
        for field in result["missing_critical"]:
            detail = next((d for d in result["details"] if d["field"] == field), {})
            lines.append(f"  - {field}: {detail.get('description', '')}")
            lines.append(f"    不填后果: {detail.get('empty_means', '')}")

    if result["missing_mandatory"]:
        lines.append(f"\n[MANDATORY] {len(result['missing_mandatory'])} 个核心字段缺失（必须补全）：")
        for field in result["missing_mandatory"]:
            detail = next((d for d in result["details"] if d["field"] == field), {})
            lines.append(f"  - {field}: {detail.get('description', '')}")
            lines.append(f"    不填后果: {detail.get('empty_means', '')}")

    if result["warning_recommended"]:
        lines.append(f"\n[RECOMMENDED] {len(result['warning_recommended'])} 个推荐字段缺失（影响优秀好用）：")
        for field in result["warning_recommended"]:
            detail = next((d for d in result["details"] if d["field"] == field), {})
            lines.append(f"  - {field}: {detail.get('description', '')}")
            lines.append(f"    不填后果: {detail.get('empty_means', '')}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ==================== 自检 ====================

if __name__ == "__main__":
    # 自检：用 output/rss/rssSource_skill_v2_test.json 验证
    import json
    import os
    from pathlib import Path

    # 找到 skill v2 测试遗留文件
    # mandatory_fields.py 在 legado/.trae/skills/legado-source-creator/scripts/legado_client/validator/
    # 测试 JSON 在 legado/output/rss/
    # parents[0]=validator, [1]=legado_client, [2]=scripts, [3]=legado-source-creator,
    # [4]=skills, [5]=.trae, [6]=legado
    test_file = Path(__file__).resolve().parents[6] / "output" / "rss" / "rssSource_skill_v2_test.json"
    if test_file.exists():
        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            data = data[0] if data else {}

        print(f"\n校验文件: {test_file.name}")
        result = validate_source(data, source_type="rss", strict_recommended=True)
        print(format_validation_report(result, data.get("sourceName", "")))
    else:
        print(f"测试文件不存在: {test_file}")
