#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则语法预检查器。

在源进入仿真测试前，先校验规则字段的语法合法性，
提前拦截明显的语法错误（括号不匹配、引号未闭合、JSONPath 格式错误等）。

规则类型识别基于 Legado 源码核实（AnalyzeRule.kt）：
- @CSS:  CSS 选择器（startsWith("@CSS:")，大小写敏感）
- @XPath: XPath 路径（startsWith("@XPath:")，大小写敏感）
- @Json:  JSONPath（startsWith("@Json:", true)，忽略大小写）
- <js>...</js>: JavaScript（JS_PATTERN 正则匹配）
- @js:   JavaScript（BaseSource.kt 中 startsWith 前缀）
- @put:/@get: 变量存取
- 无前缀: 默认 CSS（jsoup 语法）

注意：<regex> 前缀在源码中不存在，不做检查。
"""
from __future__ import annotations

from typing import Any, List, Optional


class RulePrecheck:
    """规则语法预检查。"""

    # BookSource 需校验的规则字段
    BOOK_RULE_FIELDS: List[str] = [
        "ruleSearch.bookList", "ruleSearch.name", "ruleSearch.author",
        "ruleSearch.bookUrl", "ruleSearch.intro", "ruleSearch.coverUrl",
        "ruleSearch.kind", "ruleSearch.lastChapter", "ruleSearch.wordCount",
        "ruleBookInfo.name", "ruleBookInfo.author", "ruleBookInfo.intro",
        "ruleBookInfo.coverUrl", "ruleBookInfo.tocUrl",
        "ruleToc.chapterList", "ruleToc.chapterName", "ruleToc.chapterUrl",
        "ruleContent.content",
    ]

    # RssSource 需校验的规则字段
    RSS_RULE_FIELDS: List[str] = [
        "ruleArticles", "ruleTitle", "ruleLink", "ruleContent", "ruleNextPage",
    ]

    def __init__(self, source_obj: dict, source_type: str):
        """
        Args:
            source_obj: 书源/订阅源 JSON 对象
            source_type: "book" 或 "rss"
        """
        self.source_obj = source_obj or {}
        self.source_type = source_type

    def precheck(self) -> dict:
        """校验规则语法。

        Returns:
            {
                "valid": bool,
                "errors": [{"field": str, "message": str, "level": "ERROR"}],
                "warnings": [{"field": str, "message": str, "level": "WARN"}]
            }
        """
        fields = self.BOOK_RULE_FIELDS if self.source_type == "book" else self.RSS_RULE_FIELDS
        errors: List[dict] = []
        warnings: List[dict] = []

        for field in fields:
            value = self._get_field(field)
            if not isinstance(value, str) or not value.strip():
                continue  # 空字段不检查语法（由 SourceValidator 负责）

            # 语法检查（ERROR 级）
            msg = self._check_rule_syntax(value)
            if msg is not None:
                errors.append({"field": field, "message": msg, "level": "ERROR"})

            # Rhino 兼容性检查（WARN 级，仅对 JS 规则）
            rule_type = self._identify_rule_type(value)
            if rule_type == "js":
                rhino_warns = self._check_rhino_compatibility(value)
                for w in rhino_warns:
                    warnings.append({"field": field, "message": w, "level": "WARN"})

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_rule_syntax(self, rule: str) -> Optional[str]:
        """识别规则类型并执行对应语法检查，返回错误消息（None表示通过）。"""
        rule = rule.strip()
        rule_type = self._identify_rule_type(rule)

        if rule_type == "css":
            return self._check_css(rule)
        if rule_type == "xpath":
            return self._check_xpath(rule)
        if rule_type == "json":
            return self._check_json(rule)
        if rule_type == "js":
            return self._check_js(rule)
        if rule_type == "var":
            return self._check_var(rule)
        return None

    def _identify_rule_type(self, rule: str) -> str:
        """识别规则前缀类型（基于 AnalyzeRule.kt 源码核实）。"""
        if rule.startswith("@CSS:"):
            return "css"
        if rule.startswith("@XPath:"):
            return "xpath"
        if rule.lower().startswith("@json:"):  # 源码 startsWith 第二参数 true，忽略大小写
            return "json"
        if rule.startswith("@js:"):
            return "js"
        if rule.startswith("<js>"):
            return "js"
        if rule.startswith("@put:") or rule.startswith("@get:"):
            return "var"
        return "css"  # 默认 CSS（jsoup 语法）

    def _check_css(self, rule: str) -> Optional[str]:
        """CSS 选择器语法检查：括号匹配 + 引号匹配。"""
        selector = rule[5:] if rule.startswith("@CSS:") else rule
        return self._check_brackets_quotes(selector, "CSS选择器")

    def _check_xpath(self, rule: str) -> Optional[str]:
        """XPath 语法检查：括号匹配 + 引号匹配。"""
        path = rule[7:] if rule.startswith("@XPath:") else rule
        return self._check_brackets_quotes(path, "XPath")

    def _check_json(self, rule: str) -> Optional[str]:
        """JSONPath 语法检查：$ 开头 + 括号匹配。"""
        path = rule[6:] if rule.lower().startswith("@json:") else rule
        if path and not path.startswith("$"):
            return f"JSONPath 应以 $ 开头，当前: {path[:30]}"
        return self._check_brackets_quotes(path, "JSONPath")

    def _check_js(self, rule: str) -> Optional[str]:
        """JavaScript 语法检查：括号匹配 + 引号匹配。"""
        if rule.startswith("@js:"):
            code = rule[4:]
        elif rule.startswith("<js>"):
            code = rule[4:]
            if code.endswith("</js>"):
                code = code[:-5]
        else:
            code = rule
        return self._check_brackets_quotes(code, "JS代码")

    def _check_rhino_compatibility(self, rule: str) -> List[str]:
        """Rhino 1.8.1 兼容性检测：检测 ES6+ 语法。

        Rhino 1.8.1 仅支持 ES5，以下 ES6+ 语法会导致运行时错误：
        - let/const 声明（Rhino 部分支持，但行为可能不一致）
        - async/await（不支持）
        - 箭头函数 =>（不支持）
        - 模板字符串 `...`（不支持）
        - fetch/Promise（浏览器API，Rhino无此对象）

        Args:
            rule: 规则字符串（含 @js: 或 <js> 前缀）

        Returns:
            List[str]: 兼容性警告消息列表（空列表表示无警告）
        """
        # 提取 JS 代码
        if rule.startswith("@js:"):
            code = rule[4:]
        elif rule.startswith("<js>"):
            code = rule[4:]
            if code.endswith("</js>"):
                code = code[:-5]
        else:
            code = rule

        warnings: List[str] = []

        # 检测 ES6 关键字（使用单词边界，避免误匹配）
        import re
        es6_keywords = {
            'let': 'let 声明（Rhino 1.8.1 部分支持，建议用 var 替代）',
            'const': 'const 声明（Rhino 1.8.1 部分支持，建议用 var 替代）',
            'async': 'async 关键字（Rhino 1.8.1 不支持 async/await）',
            'await': 'await 关键字（Rhino 1.8.1 不支持 async/await）',
        }
        for kw, desc in es6_keywords.items():
            if re.search(r'\b' + kw + r'\b', code):
                warnings.append(f"Rhino兼容性: 检测到 {desc}")

        # 检测浏览器API（fetch/Promise）
        browser_apis = {
            'fetch': 'fetch API（Rhino无此对象，需用 java.ajax 替代）',
            'Promise': 'Promise 对象（Rhino 1.8.1 不支持，需用回调替代）',
        }
        for api, desc in browser_apis.items():
            if re.search(r'\b' + api + r'\b', code):
                warnings.append(f"Rhino兼容性: 检测到 {desc}")

        # 检测箭头函数（=> 前面有括号或变量名）
        if re.search(r'(\)|\w)\s*=>', code):
            warnings.append("Rhino兼容性: 检测到箭头函数 =>（Rhino 1.8.1 不支持，需用 function 替代）")

        # 检测模板字符串（反引号）
        if '`' in code:
            warnings.append("Rhino兼容性: 检测到模板字符串 `（Rhino 1.8.1 不支持，需用字符串拼接替代）")

        return warnings

    def _check_var(self, rule: str) -> Optional[str]:
        """变量存取语法检查：括号匹配。"""
        return self._check_brackets_quotes(rule, "变量规则")

    def _check_brackets_quotes(self, s: str, label: str) -> Optional[str]:
        """通用括号+引号匹配检查。

        检查圆括号、方括号、花括号是否配对，引号是否闭合。
        仅报告明确的不匹配错误，控制误报率。
        """
        pairs = {"(": ")", "[": "]", "{": "}"}
        reverse = {v: k for k, v in pairs.items()}
        stack: List[str] = []
        in_string: Optional[str] = None  # 当前所在的引号类型
        escape = False

        for i, c in enumerate(s):
            if escape:
                escape = False
                continue
            if in_string:
                if c == "\\":
                    escape = True
                elif c == in_string:
                    in_string = None
                continue
            if c in ('"', "'"):
                in_string = c
            elif c in pairs:
                stack.append(c)
            elif c in reverse:
                if not stack or pairs[stack.pop()] != c:
                    return f"{label}括号不匹配：位置{i}处多余的 '{c}'"

        if in_string:
            return f"{label}引号未闭合：'{in_string}'"
        if stack:
            unclosed = ", ".join(f"'{pairs[b]}'" for b in stack)
            return f"{label}括号未闭合：缺少 {unclosed}"
        return None

    def _get_field(self, field_path: str) -> Any:
        """按点分路径获取嵌套字段值（如 ruleSearch.bookList）。"""
        current: Any = self.source_obj
        for part in field_path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current


# 简化说明：便捷函数，与 source_validator.py 风格一致 | 已知上限：无 | 升级路径：如需更精确校验，可选引入 soupsieve/lxml
def precheck_rules(source_obj: dict, source_type: str) -> dict:
    """模块级便捷函数：校验规则语法。"""
    return RulePrecheck(source_obj, source_type).precheck()
