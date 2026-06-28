#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错误诊断器：识别错误类型并生成可操作的修复建议。

替换 debug-source.py 中的 _generate_error_suggestion 函数。
8种错误类型（方向5），方向8新增3种，方向12新增1种（网站改版），最终12种。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional


class ErrorDiagnoser:
    """错误诊断器：根据错误消息+堆栈+失败阶段，识别错误类型并生成修复建议。"""

    # 8种错误类型，按匹配优先级排序
    ERROR_PATTERNS: Dict[str, dict] = {
        # 1. 相对路径问题（JVM仿真器未自动拼接相对路径）
        "relative_url": {
            "pattern": r"Expected URL scheme 'http' or 'https'",
            "category": "相对路径问题",
            "suggestion": (
                "JVM仿真器未自动拼接相对路径。\n"
                "修复方案：在URL规则中用JS补全绝对路径：\n"
                "  rule<js>result.indexOf('http')===0?result:'https://域名'+result</js>"
            ),
            "tips": [
                "检查URL规则是否返回相对路径（如 /book/123.html）",
                "在URL规则中用JS补全为绝对路径",
                "方向1已修复AnalyzeUrl传baseUrl，但JS中拼接仍需手动处理",
            ],
            "trigger_html_analysis": False,
        },
        # 2. 网站不可达（HTTP状态码）
        "site_down": {
            "pattern": r"\b(404|403|500|502|503)\b|Not Found|Forbidden|Internal Server Error",
            "category": "网站不可达",
            "suggestion": (
                "网站返回错误状态码，可能已挂或域名变更。\n"
                "修复方案：\n"
                "  1. curl验证网站存活\n"
                "  2. 检查域名301重定向\n"
                "  3. 更新sourceUrl"
            ),
            "tips": [
                "在浏览器中手动访问该URL确认状态",
                "检查域名是否已变更（whois查询）",
                "如果网站已关闭，需寻找替代源",
            ],
            "trigger_html_analysis": False,
        },
        # 3. 网络错误（超时/DNS/连接拒绝）
        "network_error": {
            "pattern": (
                r"timeout|timed out|SocketTimeoutException|ConnectException|"
                r"UnknownHostException|Connection refused|"
                r"不知道这样的主机|无法连接|连接超时|网络不可达"
            ),
            "category": "网络错误",
            "suggestion": (
                "网络请求失败，可能是超时、DNS解析失败或连接被拒绝。\n"
                "修复方案：\n"
                "  1. 检查书源URL是否正确\n"
                "  2. 尝试在浏览器中手动访问该URL\n"
                "  3. 检查网络代理设置"
            ),
            "tips": [],
            "trigger_html_analysis": False,
        },
        # 4. 规则不匹配（列表为空）
        "rule_empty": {
            "pattern": r"列表大小:0|文章列表为空|本页文章数:0|搜索结果为空|目录为空|正文为空|规则.*为空|bookList.*为空",
            "category": "规则不匹配",
            "suggestion": (
                "选择器未匹配到HTML元素。\n"
                "修复方案：\n"
                "  1. 查看下方HTML结构分析\n"
                "  2. 更新选择器\n"
                "  3. 注意标签名vs class：class.xxx匹配class='xxx'，xxx匹配<xxx>\n"
                "  4. 使用||回退选择器：选择器A||选择器B（A失败时自动尝试B）\n"
                "  5. 使用@CSS:前缀强制CSS解析：@css:.book-item"
            ),
            "tips": [
                "用浏览器F12检查HTML结构",
                "注意CSS选择器语法：class.xxx vs tag.xxx",
                "如果所有选择器都失效，可能是网站改版",
                "陷阱#46：||回退选择器可提高容错性",
                "陷阱#47：@CSS:前缀可强制使用CSS选择器解析",
            ],
            "trigger_html_analysis": True,
        },
        # 5. 规则解析错误（CSS/JSONPath/XPath语法错误）
        "rule_parse": {
            "pattern": r"CSS选择器|JSONPath|XPath|PatternSyntax|选择器未匹配|规则错误|Selector",
            "category": "规则解析错误",
            "suggestion": (
                "规则语法错误或选择器无效。\n"
                "修复方案：\n"
                "  1. 检查CSS选择器/JSONPath/XPath语法\n"
                "  2. 参考 references/rule-syntax/ 下的语法文档\n"
                "  3. 用浏览器F12验证选择器"
            ),
            "tips": [],
            "trigger_html_analysis": False,
        },
        # 6. JS执行错误（TypeError/ReferenceError/SyntaxError）
        "js_error": {
            "pattern": r"JavaScript Error|TypeError|ReferenceError|SyntaxError|is not a function",
            "category": "JS执行错误",
            "suggestion": (
                "JS执行出错。\n"
                "修复方案：\n"
                "  1. ES6改ES5：let→var、箭头函数→function\n"
                "  2. 检查变量是否定义\n"
                "  3. 检查java对象方法调用（参考JsExtensions.kt）"
            ),
            "tips": [
                "Rhino不支持ES6+语法（let/const/箭头函数/模板字符串）",
                "检查java.xxx方法名是否正确（参考JsExtensions.kt）",
                "如果函数确实不存在，标记为unverifiable并在手机端验证",
            ],
            "trigger_html_analysis": False,
        },
        # 7. 编码错误（URL编码错误，GBK编码由gbk_encoding_error处理）
        "encoding_error": {
            "pattern": r"400 Bad Request|Malformed URL|encoding|encodeURI",
            "category": "编码错误",
            "suggestion": (
                "URL中的中文可能需要URL编码，或页面编码为GBK。\n"
                "修复方案：\n"
                "  OkHttp通常自动编码，但某些场景需手动处理：\n"
                "  1. searchUrl中用{{key}}占位符（Legado自动编码）\n"
                "  2. GBK编码页面在ruleToc中设置charset=GBK"
            ),
            "tips": [
                "检查searchUrl中中文是否被正确编码",
                "检查页面是否为GBK编码（查看meta charset）",
            ],
            "trigger_html_analysis": False,
        },
        # 8. 搜索方法错误（GET搜索返回空，需改为POST）
        "search_method_error": {
            "pattern": r"search.*empty.*method|GET.*failed|method.*POST|搜索方法.*错误",
            "category": "搜索方法错误",
            "suggestion": (
                "GET搜索返回空结果，可能需要改为POST方法或调整URL。\n"
                "修复方案：\n"
                "  1. 检查searchUrl是否需要POST方法\n"
                "  2. 配置POST body：searchUrl: \"url,{\\\"method\\\":\\\"POST\\\",\\\"body\\\":\\\"keyword={{key}}\\\"}\"\n"
                "  3. 检查搜索URL是否包含正确的参数占位符"
            ),
            "tips": [
                "参考 known-fix-patterns/search-method.md",
                "OkHttp自动编码中文参数，但POST body需手动处理",
            ],
            "trigger_html_analysis": False,
        },
        # 9. GBK编码错误（GBK网站搜索关键词编码问题）
        "gbk_encoding_error": {
            "pattern": r"GBK|GB2312|charset.*gb|编码.*错误|乱码.*搜索",
            "category": "GBK编码错误",
            "suggestion": (
                "GBK编码网站的搜索关键词需要特殊处理。\n"
                "修复方案：\n"
                "  1. searchUrl中用{{key}}占位符（Legado自动编码）\n"
                "  2. 如果仍乱码，用JS手动GBK编码：java.encodeURI(key)\n"
                "  3. 检查页面meta charset是否为GBK"
            ),
            "tips": [
                "参考 known-fix-patterns/gbk-encoding.md",
                "OkHttp默认UTF-8，GBK网站需特殊处理",
            ],
            "trigger_html_analysis": False,
        },
        # 10. 功能失效vs网站不可达区分
        "function_vs_site_down": {
            "pattern": r"功能.*失效|feature.*disabled|not.*available|已下线|维护中",
            "category": "功能失效vs网站不可达",
            "suggestion": (
                "需要区分是网站整体不可达还是特定功能失效。\n"
                "判断方法：\n"
                "  1. 网站不可达：所有页面都返回404/超时\n"
                "  2. 功能失效：首页可访问但搜索/详情等功能返回空\n"
                "  3. 网站改版：页面结构变化导致选择器失效"
            ),
            "tips": [
                "先访问网站首页确认是否整体不可达",
                "如果首页可访问但功能失效，可能是网站改版",
                "检查网站公告是否有维护通知",
            ],
            "trigger_html_analysis": False,
        },
        # 11. 网站改版（方向12新增：所有选择器失效/HTTP 301/302永久重定向）
        "site_redesign": {
            "pattern": r"301|302|永久重定向|网站改版|页面结构.*变化|所有选择器.*失效",
            "category": "网站改版",
            "suggestion": (
                "网站可能已改版，导致页面结构变化。\n"
                "修复方案：\n"
                "  1. 用浏览器F12检查新的HTML结构\n"
                "  2. 更新所有选择器\n"
                "  3. 检查URL是否有301/302重定向"
            ),
            "tips": [
                "如果所有选择器都失效，很可能是网站改版",
                "检查网站是否有新版本（如www→m子域名切换）",
                "参考 known-fix-patterns/ranking-url.md",
            ],
            "trigger_html_analysis": True,
        },
        # 12. 未知错误（兜底）
        "unknown": {
            "pattern": r".",  # 匹配任意
            "category": "未知错误",
            "suggestion": "查看完整堆栈信息定位错误根因。",
            "tips": [
                "查看完整堆栈信息定位错误",
                "使用 evolution_trigger.py 分析根因",
            ],
            "trigger_html_analysis": False,
        },
    }

    # 阶段→规则名称映射
    STAGE_MAP: Dict[str, str] = {
        "search": "搜索规则",
        "detail": "详情规则",
        "toc": "目录规则",
        "content": "正文规则",
        "sort": "分类规则",
    }

    def diagnose(self, msg: str, stack_trace: Optional[str],
                 failed_stage: Optional[str]) -> dict:
        """诊断错误类型并生成修复建议。

        Args:
            msg: 错误消息
            stack_trace: 堆栈信息（可能为None）
            failed_stage: 失败阶段（search/detail/toc/content/sort）

        Returns:
            dict: {
                summary: str,           # 错误摘要
                tips: list[str],        # 修复建议列表
                error_type: str,        # 错误类型key
                category: str,          # 错误分类名称
                possible_cause: str,    # 可能原因（可选）
                rule_debug: str,        # 规则调试信息（可选）
                trigger_html_analysis: bool,  # 是否触发HTML分析
            }
        """
        combined = f"{msg} {stack_trace or ''}"

        for error_type, config in self.ERROR_PATTERNS.items():
            if re.search(config["pattern"], combined, re.IGNORECASE):
                return self._build_result(error_type, config, msg, stack_trace, failed_stage)

        # 兜底：unknown（理论上不会到达，因为unknown的pattern匹配任意）
        return self._build_result("unknown", self.ERROR_PATTERNS["unknown"], msg, stack_trace, failed_stage)

    def _build_result(self, error_type: str, config: dict, msg: str,
                      stack_trace: Optional[str], failed_stage: Optional[str]) -> dict:
        """构建诊断结果dict，与现有_generate_error_suggestion返回格式兼容。"""
        result: dict = {
            "summary": f"[{config['category']}] {msg[:200] if msg else '无错误消息'}",
            "tips": list(config.get("tips", [])),
            "error_type": error_type,
            "category": config["category"],
            "trigger_html_analysis": config["trigger_html_analysis"],
        }

        # 网络错误细分可能原因
        if error_type == "network_error":
            combined = f"{msg} {stack_trace or ''}"
            if re.search(r"timeout|超时", combined, re.IGNORECASE):
                result["possible_cause"] = "请求超时（网站响应慢或被限流）"
            elif re.search(r"unknownhost|不知道", combined, re.IGNORECASE):
                result["possible_cause"] = "DNS解析失败（域名不存在或网络问题）"
            elif re.search(r"connect|无法连接|不可达", combined, re.IGNORECASE):
                result["possible_cause"] = "连接被拒绝（网站可能已关闭或IP被封）"
            else:
                result["possible_cause"] = "网络请求失败"

        # JS错误提取函数名
        if error_type == "js_error":
            m = re.search(r"java\.(\w+)\s+is not a function", f"{msg} {stack_trace or ''}")
            if m:
                func_name = f"java.{m.group(1)}"
                result["summary"] = f"[JS执行错误] 函数不存在: {func_name}"
                result["tips"].insert(0, f"检查函数名 {func_name} 拼写是否正确（参考 JsExtensions.kt）")

        # 规则相关错误添加阶段信息
        if error_type in ("rule_empty", "rule_parse") and failed_stage:
            rule_debug = self.STAGE_MAP.get(failed_stage, f"{failed_stage}阶段规则")
            result["rule_debug"] = rule_debug
            result["tips"].insert(0, f"检查 {rule_debug} 是否正确匹配网站HTML结构")

        return result


# 简化说明：单例模式，避免重复实例化 | 已知上限：无 | 升级路径：如需动态扩展错误类型，改为从JSON配置加载
_diagnoser = ErrorDiagnoser()


def diagnose_error(msg: str, stack_trace: Optional[str], failed_stage: Optional[str]) -> dict:
    """模块级便捷函数，供debug-source.py直接调用替换_generate_error_suggestion。"""
    return _diagnoser.diagnose(msg, stack_trace, failed_stage)
