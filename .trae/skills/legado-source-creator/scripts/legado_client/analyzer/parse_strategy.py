#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_strategy.py - 解析方式自动选择器

根据网站分析结果自动选择最佳解析方式（CSS/JSONPath/XPath/正则/JS）。
方向14核心模块：Phase 2规则构建指导。

用法:
    from legado_client.analyzer.parse_strategy import select_parse_strategy
    strategy = select_parse_strategy({"is_api": True})  # → "jsonpath"
"""
from __future__ import annotations

import re
from typing import Dict


class ParseStrategySelector:
    """根据网站分析结果选择最佳解析方式

    决策树优先级：
        1. API响应 → JSONPath
        2. 加密内容 → JS+加密
        3. 动态渲染 → JS
        4. 复杂HTML → XPath
        5. 纯文本 → 正则
        6. 默认 → CSS
    """

    # 简化说明：决策树基于网站特征自动选择 | 已知上限：复杂网站可能需要多种方式组合 | 升级路径：ML自动选择
    DECISION_TREE: Dict[str, str] = {
        "api_response": "jsonpath",
        "simple_html": "css",
        "complex_html": "xpath",
        "text_extract": "regex",
        "dynamic_render": "js",
        "encrypted_content": "js+encrypt",
    }

    def select(self, site_analysis: dict) -> str:
        """根据网站分析结果选择解析方式

        Args:
            site_analysis: 网站分析结果，可包含：
                - is_api: bool, 是否为API响应（JSON格式）
                - has_encryption: bool, 是否有加密内容
                - is_dynamic: bool, 是否需要动态渲染
                - html_complexity: str, HTML复杂度 ("high"/"medium"/"low")
                - is_text_only: bool, 是否为纯文本提取

        Returns:
            解析方式字符串: "jsonpath"/"css"/"xpath"/"regex"/"js"/"js+encrypt"
        """
        if site_analysis.get("is_api"):
            return "jsonpath"
        if site_analysis.get("has_encryption"):
            return "js+encrypt"
        if site_analysis.get("is_dynamic"):
            return "js"
        if site_analysis.get("html_complexity") == "high":
            return "xpath"
        if site_analysis.get("is_text_only"):
            return "regex"
        return "css"

    def select_from_html(self, html: str, content_type: str = "") -> str:
        """从HTML内容推断解析方式

        Args:
            html: HTML/JSON响应内容
            content_type: HTTP Content-Type头

        Returns:
            解析方式字符串
        """
        if not html:
            return "css"

        # JSON响应 → JSONPath
        stripped = html.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "jsonpath"

        # Content-Type包含json
        if "json" in content_type.lower():
            return "jsonpath"

        # 加密特征：大量base64编码或eval调用
        if re.search(r'eval\s*\(|atob\s*\(|decrypt\s*\(', html):
            return "js+encrypt"

        # 动态渲染特征：SPA框架标记
        if re.search(r'<div\s+id="app"|<div\s+id="root"|data-v-|__nuxt', html):
            return "js"

        # 复杂HTML：深层嵌套或命名空间
        if html.count("<") > 500 and html.count("xmlns") > 0:
            return "xpath"

        # 默认CSS
        return "css"


# 模块级便捷函数
def select_parse_strategy(site_analysis: dict) -> str:
    """选择解析方式（模块级便捷函数）"""
    return ParseStrategySelector().select(site_analysis)


if __name__ == "__main__":
    # 自检：1正常用例 + 1边界用例
    selector = ParseStrategySelector()

    # 正常用例：API响应
    result = selector.select({"is_api": True})
    assert result == "jsonpath", f"API用例失败: {result}"
    print(f"✅ 正常用例: is_api=True → {result}")

    # 边界用例：空字典（默认CSS）
    result = selector.select({})
    assert result == "css", f"边界用例失败: {result}"
    print(f"✅ 边界用例: 空字典 → {result}")

    # HTML推断用例
    result = selector.select_from_html('{"data": [1,2,3]}')
    assert result == "jsonpath", f"JSON推断失败: {result}"
    print(f"✅ HTML推断: JSON → {result}")

    result = selector.select_from_html('<html><body>Hello</body></html>')
    assert result == "css", f"HTML推断失败: {result}"
    print(f"✅ HTML推断: HTML → {result}")

    print("\n所有自检通过 (4/4)")
