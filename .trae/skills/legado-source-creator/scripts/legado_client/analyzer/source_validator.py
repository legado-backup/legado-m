#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源字段完整性预校验器。

在源进入仿真测试前，先校验必填字段是否完整、格式是否合法，
提前拦截明显配置错误，避免无效源浪费测试资源。

校验规则基于 Legado 源码核实：
- BookSource: bookSourceName/bookSourceUrl/bookSourceType 为 ERROR 级必填；
  searchUrl/ruleSearch.bookList 实际可空，降级为 WARN。
- RssSource: sourceName/sourceUrl/type 为 ERROR 级必填；
  ruleArticles 实际可空，降级为 WARN。
"""
from __future__ import annotations

from typing import Any, Dict, List


class SourceValidator:
    """源字段完整性预校验。"""

    # BookSource 字段校验规则：字段路径 -> (校验类型, 错误级别, 修复建议模板)
    # 校验类型: "non_empty" 非空 / "url" URL格式 / "enum" 枚举值 / "url_optional" 有值时校验URL / "json_optional" 有值时校验JSON
    BOOK_RULES: List[dict] = [
        # ERROR 级必填（3条）
        {"field": "bookSourceName", "check": "non_empty", "level": "ERROR",
         "advice": "缺少 bookSourceName，请补充书源名称"},
        {"field": "bookSourceUrl", "check": "url", "level": "ERROR",
         "advice": "缺少或非法 bookSourceUrl，请补充以 http:// 或 https:// 开头的书源URL"},
        {"field": "bookSourceType", "check": "enum", "allowed": [0, 1, 2, 3], "level": "ERROR",
         "advice": "bookSourceType 应为 0(文本)/1(音频)/2(图片)/3(文件)，请修正"},
        # WARN 级搜索相关（2条）
        {"field": "searchUrl", "check": "non_empty", "level": "WARN",
         "advice": "缺少 searchUrl，该源将无法使用搜索功能（如不需要搜索可忽略）"},
        {"field": "ruleSearch.bookList", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleSearch.bookList，搜索结果列表规则为空（如不需要搜索可忽略）"},
        # WARN 级详情页规则（2条）
        {"field": "ruleBookInfo.name", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleBookInfo.name，书名解析规则为空"},
        {"field": "ruleBookInfo.author", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleBookInfo.author，作者解析规则为空"},
        # WARN 级目录页规则（3条）
        {"field": "ruleToc.chapterList", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleToc.chapterList，章节列表规则为空"},
        {"field": "ruleToc.chapterName", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleToc.chapterName，章节名称规则为空"},
        {"field": "ruleToc.chapterUrl", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleToc.chapterUrl，章节URL规则为空"},
        # WARN 级正文规则（1条）
        {"field": "ruleContent.content", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleContent.content，正文解析规则为空"},
        # WARN 级发现页（1条）
        {"field": "exploreUrl", "check": "non_empty", "level": "WARN",
         "advice": "缺少 exploreUrl，发现页URL为空（如不需要发现页可忽略）"},
        # WARN 级可选格式校验（3条）
        {"field": "loginUrl", "check": "url_optional", "level": "WARN",
         "advice": "loginUrl 格式非法，应为 http:// 或 https:// 开头的URL"},
        {"field": "header", "check": "json_optional", "level": "WARN",
         "advice": "header 格式非法，应为合法JSON字符串（如 {\"User-Agent\":\"...\"}）"},
        {"field": "loginUi", "check": "json_optional", "level": "WARN",
         "advice": "loginUi 格式非法，应为合法JSON字符串"},
    ]

    # RssSource 字段校验规则
    RSS_RULES: List[dict] = [
        # ERROR 级必填（3条）
        {"field": "sourceName", "check": "non_empty", "level": "ERROR",
         "advice": "缺少 sourceName，请补充订阅源名称"},
        {"field": "sourceUrl", "check": "url", "level": "ERROR",
         "advice": "缺少或非法 sourceUrl，请补充以 http:// 或 https:// 开头的订阅源URL"},
        {"field": "type", "check": "enum", "allowed": [0, 1], "level": "ERROR",
         "advice": "type 应为 0(RSS)/1(自定义)，请修正"},
        # WARN 级文章规则（3条）
        {"field": "ruleArticles", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleArticles，文章列表规则为空（如不需要解析可忽略）"},
        {"field": "ruleTitle", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleTitle，文章标题规则为空"},
        {"field": "ruleLink", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleLink，文章链接规则为空"},
        # WARN 级内容规则（2条）
        {"field": "ruleContent", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleContent，文章内容规则为空"},
        {"field": "ruleNextPage", "check": "non_empty", "level": "WARN",
         "advice": "缺少 ruleNextPage，下一页规则为空（如无分页可忽略）"},
        # WARN 级可选格式校验（2条）
        {"field": "enableJs", "check": "enum_optional", "allowed": [0, 1], "level": "WARN",
         "advice": "enableJs 应为 0(禁用)/1(启用)"},
        {"field": "loadUrl", "check": "url_optional", "level": "WARN",
         "advice": "loadUrl 格式非法，应为 http:// 或 https:// 开头的URL"},
    ]

    def __init__(self, source_obj: dict, source_type: str):
        """
        Args:
            source_obj: 书源/订阅源 JSON 对象
            source_type: "book" 或 "rss"
        """
        self.source_obj = source_obj or {}
        self.source_type = source_type

    def validate(self) -> dict:
        """校验字段完整性。

        Returns:
            {
                "valid": bool,  # True=校验通过(无ERROR), False=有ERROR级错误
                "errors": [{"field": str, "message": str, "level": "ERROR"}],
                "warnings": [{"field": str, "message": str, "level": "WARN"}]
            }
        """
        rules = self.BOOK_RULES if self.source_type == "book" else self.RSS_RULES
        errors: List[dict] = []
        warnings: List[dict] = []

        for rule in rules:
            msg = self._check_rule(rule)
            if msg is None:
                continue
            issue = {"field": rule["field"], "message": msg, "level": rule["level"]}
            if rule["level"] == "ERROR":
                errors.append(issue)
            else:
                warnings.append(issue)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_rule(self, rule: dict) -> str | None:
        """执行单条校验规则，返回错误消息（None表示通过）。"""
        value = self._get_field(rule["field"])
        check = rule["check"]

        if check == "non_empty":
            if value is None or (isinstance(value, str) and not value.strip()):
                return rule["advice"]
            return None

        if check == "url":
            if not isinstance(value, str) or not value.strip():
                return rule["advice"]
            if not (value.startswith("http://") or value.startswith("https://")):
                return rule["advice"]
            return None

        if check == "url_optional":
            # 有值时校验URL格式，无值则通过
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            if not isinstance(value, str) or not (value.startswith("http://") or value.startswith("https://")):
                return rule["advice"]
            return None

        if check == "json_optional":
            # 有值时校验JSON格式，无值则通过
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            if isinstance(value, dict):
                return None  # 已是dict，无需校验
            if isinstance(value, str):
                try:
                    import json
                    json.loads(value)
                    return None
                except (json.JSONDecodeError, ValueError):
                    return rule["advice"]
            return rule["advice"]

        if check == "enum":
            if value not in rule["allowed"]:
                return rule["advice"]
            return None

        if check == "enum_optional":
            # 有值时校验枚举，无值则通过
            if value is None:
                return None
            if value not in rule["allowed"]:
                return rule["advice"]
            return None

        return None

    def _get_field(self, field_path: str) -> Any:
        """按点分路径获取嵌套字段值（如 ruleSearch.bookList）。"""
        current: Any = self.source_obj
        for part in field_path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current


# 简化说明：单例+便捷函数，与 error_diagnoser.py 风格一致 | 已知上限：无 | 升级路径：如需动态加载规则，改为从JSON配置读取
_validator_cache: Dict[str, SourceValidator] = {}


def validate_source(source_obj: dict, source_type: str) -> dict:
    """模块级便捷函数：校验源字段完整性。"""
    return SourceValidator(source_obj, source_type).validate()
