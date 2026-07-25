#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_error_diagnoser.py - 错误诊断器测试

覆盖 ErrorDiagnoser 的 12 种错误类型诊断。
同时支持 `python test_error_diagnoser.py` 独立运行和 `pytest test_error_diagnoser.py` 运行。

任务要求覆盖的 12 种错误类型（语义类别）与模块实际错误类型 key 的映射：
  js_error       → js_error
  css_error      → rule_parse (CSS选择器错误归入 rule_parse)
  xpath_error    → rule_parse (XPath 错误归入 rule_parse)
  jsonpath_error → rule_parse (JSONPath 错误归入 rule_parse)
  regex_error    → rule_parse (PatternSyntax 正则错误归入 rule_parse)
  url_error      → relative_url (URL scheme 错误)
  encoding_error → encoding_error / gbk_encoding_error
  timeout_error  → network_error (超时归入网络错误)
  parse_error    → rule_empty (列表/正文为空)
  network_error  → network_error
  auth_error     → site_down (403 Forbidden 归入网站不可达)
  captcha_error  → unknown (无直接对应，验证码类错误归入兜底)
"""
import os
import sys
from pathlib import Path

# 确保能 import 被测模块（从 tests/ 向上回溯到 legado_client/）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyzer.error_diagnoser import ErrorDiagnoser, diagnose_error


# ==================== 12 种错误类型测试（每种 1 正常 + 1 边界） ====================

def test_relative_url():
    """1. relative_url (对应 url_error): URL scheme 错误。"""
    # 正常用例：正确分类
    result = diagnose_error("Expected URL scheme 'http' or 'https'", None, "search")
    assert result['error_type'] == 'relative_url', f"应识别为 relative_url: {result['error_type']}"
    assert '相对路径' in result['category'], f"分类名称应含相对路径: {result['category']}"
    assert isinstance(result['tips'], list) and len(result['tips']) > 0
    assert result['trigger_html_analysis'] is False

    # 边界用例：错误消息为空，但堆栈含特征
    result2 = diagnose_error("", "stack: Expected URL scheme 'http' or 'https' end", None)
    assert result2['error_type'] == 'relative_url', f"堆栈匹配应识别为 relative_url: {result2['error_type']}"


def test_site_down():
    """2. site_down (对应 auth_error via 403): 网站不可达。"""
    # 正常用例：404
    result = diagnose_error("HTTP 404 Not Found", None, None)
    assert result['error_type'] == 'site_down', f"应识别为 site_down: {result['error_type']}"
    assert '不可达' in result['category']

    # 边界用例：503 在堆栈中
    result2 = diagnose_error("Service Unavailable", "HTTP 503", None)
    assert result2['error_type'] == 'site_down', f"503 应识别为 site_down: {result2['error_type']}"


def test_network_error():
    """3. network_error (对应 timeout_error / network_error): 网络错误。"""
    # 正常用例：超时 → possible_cause 应包含超时
    result = diagnose_error("SocketTimeoutException: timeout", None, None)
    assert result['error_type'] == 'network_error', f"应识别为 network_error: {result['error_type']}"
    assert '超时' in result.get('possible_cause', ''), f"应识别超时原因: {result.get('possible_cause')}"

    # 边界用例：DNS 解析失败
    result2 = diagnose_error("UnknownHostException: 不知道这样的主机", None, None)
    assert result2['error_type'] == 'network_error'
    assert 'DNS' in result2.get('possible_cause', ''), f"应识别 DNS 原因: {result2.get('possible_cause')}"


def test_rule_empty():
    """4. rule_empty (对应 parse_error): 规则不匹配，列表为空。"""
    # 正常用例：搜索阶段列表为空，应触发 HTML 分析
    result = diagnose_error("列表大小:0", None, "search")
    assert result['error_type'] == 'rule_empty', f"应识别为 rule_empty: {result['error_type']}"
    assert result['trigger_html_analysis'] is True
    assert 'rule_debug' in result, "应包含 rule_debug"
    assert result['rule_debug'] == '搜索规则'

    # 边界用例：正文为空
    result2 = diagnose_error("正文为空", None, "content")
    assert result2['error_type'] == 'rule_empty'
    assert result2['rule_debug'] == '正文规则'


def test_rule_parse():
    """5. rule_parse (对应 css_error / xpath_error / jsonpath_error / regex_error): 规则解析错误。"""
    # 正常用例：CSS 选择器错误
    result = diagnose_error("CSS选择器语法错误", None, None)
    assert result['error_type'] == 'rule_parse', f"应识别为 rule_parse: {result['error_type']}"

    # 边界用例：JSONPath 错误（含阶段信息，应添加 rule_debug）
    result2 = diagnose_error("JSONPath invalid", "stack", "toc")
    assert result2['error_type'] == 'rule_parse'
    assert result2.get('rule_debug') == '目录规则', f"应含 rule_debug: {result2.get('rule_debug')}"


def test_js_error():
    """6. js_error (对应 js_error): JS 执行错误。"""
    # 正常用例：函数不存在，应提取函数名
    result = diagnose_error("java.ajax is not a function", None, None)
    assert result['error_type'] == 'js_error', f"应识别为 js_error: {result['error_type']}"
    assert 'java.ajax' in result['summary'], f"summary 应含函数名: {result['summary']}"

    # 边界用例：ReferenceError 无函数名提取
    result2 = diagnose_error("ReferenceError: x is not defined", None, None)
    assert result2['error_type'] == 'js_error'


def test_encoding_error():
    """7. encoding_error (对应 encoding_error): 编码错误。"""
    # 正常用例：400 Bad Request
    result = diagnose_error("400 Bad Request", None, None)
    assert result['error_type'] == 'encoding_error', f"应识别为 encoding_error: {result['error_type']}"

    # 边界用例：Malformed URL
    result2 = diagnose_error("Malformed URL", None, None)
    assert result2['error_type'] == 'encoding_error'


def test_search_method_error():
    """8. search_method_error: 搜索方法错误。"""
    # 正常用例：GET 搜索失败
    result = diagnose_error("search empty method GET failed", None, None)
    assert result['error_type'] == 'search_method_error', f"应识别为 search_method_error: {result['error_type']}"

    # 边界用例：中文搜索方法错误
    result2 = diagnose_error("搜索方法错误", None, None)
    assert result2['error_type'] == 'search_method_error'


def test_gbk_encoding_error():
    """9. gbk_encoding_error: GBK 编码错误。"""
    # 正常用例：GBK 编码
    result = diagnose_error("GBK编码错误", None, None)
    assert result['error_type'] == 'gbk_encoding_error', f"应识别为 gbk_encoding_error: {result['error_type']}"

    # 边界用例：charset=gb2312
    result2 = diagnose_error("charset=gb2312 乱码搜索", None, None)
    assert result2['error_type'] == 'gbk_encoding_error'


def test_function_vs_site_down():
    """10. function_vs_site_down: 功能失效 vs 网站不可达。"""
    # 正常用例：功能失效
    result = diagnose_error("功能失效", None, None)
    assert result['error_type'] == 'function_vs_site_down', f"应识别为 function_vs_site_down: {result['error_type']}"

    # 边界用例：feature disabled
    result2 = diagnose_error("feature disabled", None, None)
    assert result2['error_type'] == 'function_vs_site_down'


def test_site_redesign():
    """11. site_redesign: 网站改版。"""
    # 正常用例：301 永久重定向
    result = diagnose_error("301 永久重定向", None, None)
    assert result['error_type'] == 'site_redesign', f"应识别为 site_redesign: {result['error_type']}"
    assert result['trigger_html_analysis'] is True

    # 边界用例：所有选择器失效
    result2 = diagnose_error("所有选择器失效", None, None)
    assert result2['error_type'] == 'site_redesign'


def test_unknown():
    """12. unknown (对应 captcha_error 兜底): 未知错误。"""
    # 正常用例：无法识别的错误
    result = diagnose_error("一些无法识别的错误xyz123", None, None)
    assert result['error_type'] == 'unknown', f"应识别为 unknown: {result['error_type']}"

    # 边界用例：空消息 + 空堆栈
    result2 = diagnose_error("", None, None)
    assert result2['error_type'] == 'unknown'
    assert '无错误消息' in result2['summary'], f"空消息 summary 应含提示: {result2['summary']}"


# ==================== 优先级与结构测试 ====================

def test_priority_order():
    """测试错误类型匹配优先级（按 ERROR_PATTERNS 顺序，前面的优先）。"""
    # network_error 在 js_error 之前，"TypeError: timeout" 含 timeout，应匹配 network_error
    result = diagnose_error("TypeError: timeout", None, None)
    assert result['error_type'] == 'network_error', f"network_error 应优先于 js_error: {result['error_type']}"


def test_diagnose_error_module_function():
    """测试模块级便捷函数 diagnose_error 返回结构。"""
    result = diagnose_error("timeout", "stack", "search")
    assert isinstance(result, dict)
    for key in ('error_type', 'category', 'summary', 'tips', 'trigger_html_analysis'):
        assert key in result, f"缺少必需字段: {key}"
    assert isinstance(result['tips'], list)
    assert isinstance(result['trigger_html_analysis'], bool)


def test_class_directly():
    """测试直接使用 ErrorDiagnoser 类。"""
    diagnoser = ErrorDiagnoser()
    result = diagnoser.diagnose("404", None, None)
    assert result['error_type'] == 'site_down'
    # 验证 ERROR_PATTERNS 含 12 种类型
    assert len(ErrorDiagnoser.ERROR_PATTERNS) >= 12, f"ERROR_PATTERNS 应含 12 种: {len(ErrorDiagnoser.ERROR_PATTERNS)}"


def test_stage_map():
    """测试 STAGE_MAP 阶段映射。"""
    assert ErrorDiagnoser.STAGE_MAP['search'] == '搜索规则'
    assert ErrorDiagnoser.STAGE_MAP['detail'] == '详情规则'
    assert ErrorDiagnoser.STAGE_MAP['toc'] == '目录规则'
    assert ErrorDiagnoser.STAGE_MAP['content'] == '正文规则'
    assert ErrorDiagnoser.STAGE_MAP['sort'] == '分类规则'


if __name__ == '__main__':
    # 独立运行模式：手动收集并执行所有 test_ 函数
    test_funcs = [
        ('test_relative_url', test_relative_url),
        ('test_site_down', test_site_down),
        ('test_network_error', test_network_error),
        ('test_rule_empty', test_rule_empty),
        ('test_rule_parse', test_rule_parse),
        ('test_js_error', test_js_error),
        ('test_encoding_error', test_encoding_error),
        ('test_search_method_error', test_search_method_error),
        ('test_gbk_encoding_error', test_gbk_encoding_error),
        ('test_function_vs_site_down', test_function_vs_site_down),
        ('test_site_redesign', test_site_redesign),
        ('test_unknown', test_unknown),
        ('test_priority_order', test_priority_order),
        ('test_diagnose_error_module_function', test_diagnose_error_module_function),
        ('test_class_directly', test_class_directly),
        ('test_stage_map', test_stage_map),
    ]

    passed = 0
    failed = 0
    for name, func in test_funcs:
        try:
            func()
            passed += 1
            print(f"  PASS {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {name}: {type(e).__name__}: {e}")

    print(f"\n总计: {passed} 通过, {failed} 失败")
    sys.exit(0 if failed == 0 else 1)
