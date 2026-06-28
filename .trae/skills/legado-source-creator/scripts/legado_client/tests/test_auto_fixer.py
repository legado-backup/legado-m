#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_auto_fixer.py - 错误自动修复模块测试

覆盖关键修复函数：fix_cf_bypass / fix_website_revamp / fix_css_selector /
fix_url_template / fix_field_mapping / fix_rule_syntax / auto_fix_error。
同时支持 `python test_auto_fixer.py` 独立运行和 `pytest test_auto_fixer.py` 运行。

特别测试三处 BUG 修复：
  ① fix_cf_bypass 生成的 loginUrl 应以 `@js:java.webView` 开头，
     searchUrl 不应含 `<js>java.ajax` 块，不应设置 loginCheckJs
  ② fix_website_revamp SSR/SPA 检测后应配置 loginUrl+WebView（非空字符串）
  ③ fix_css_selector 无 HTML 时不应修改选择器（不驼峰转换/不模糊匹配）
"""
import json
import os
import sys
from pathlib import Path

# 确保能 import 被测模块（从 tests/ 向上回溯到 legado_client/）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyzer.auto_fixer import (
    auto_fix_error,
    fix_cf_bypass,
    fix_css_selector,
    fix_field_mapping,
    fix_rule_syntax,
    fix_url_template,
    fix_website_revamp,
    load_fix_history,
    record_fix_history,
    _normalize_source,
    _parse_error,
    _infer_error_type,
    _is_ssr_spa,
    _looks_like_css,
    _cache_path,
)


# ==================== 辅助函数 ====================

def _bs4_available():
    """检测 BeautifulSoup + lxml 是否可用。"""
    try:
        from bs4 import BeautifulSoup
        BeautifulSoup('<div></div>', 'lxml')
        return True
    except Exception:
        return False


# ==================== ① fix_cf_bypass 测试（CF 盾绕过） ====================

def test_fix_cf_bypass_bug1_webview_login():
    """BUG①: loginUrl 应以 @js:java.webView 开头，searchUrl 不应含 <js>java.ajax 块，不应设置 loginCheckJs。"""
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": 'https://example.com/search?q={{key}},{"method":"GET","js":"<js>java.ajax()</js>"}',
        "loginCheckJs": "old_check",
    }
    fixed, fixes, manual = fix_cf_bypass({'msg': 'CF挑战'}, source)

    # loginUrl 应以 @js:java.webView 开头
    assert fixed['loginUrl'].startswith('@js:java.webView'), \
        f"loginUrl 应以 @js:java.webView 开头: {fixed['loginUrl']}"
    # searchUrl 不应含 <js>java.ajax 块
    assert '<js>java.ajax' not in fixed['searchUrl'], \
        f"searchUrl 不应含 <js>java.ajax: {fixed['searchUrl']}"
    # 不应设置 loginCheckJs
    assert 'loginCheckJs' not in fixed, \
        f"不应设置 loginCheckJs（陷阱#57）: {fixed.get('loginCheckJs')}"


def test_fix_cf_bypass_normal():
    """正常用例：CF 绕过配置 WebView + headers。"""
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
    }
    fixed, fixes, manual = fix_cf_bypass({'msg': 'CF挑战'}, source)

    assert fixed['loginUrl'].startswith('@js:java.webView'), f"loginUrl 应配置 WebView: {fixed['loginUrl']}"
    assert 'example.com' in fixed['loginUrl'], f"loginUrl 应含 base_url: {fixed['loginUrl']}"
    assert len(fixes) > 0, "应产生修复项"
    # searchUrl 应补全 headers（含 Referer）
    assert 'Referer' in fixed.get('searchUrl', '') or 'Referer' in fixed.get('header', ''), \
        "应补全 Referer"
    # 源级 header 应被补全
    assert 'header' in fixed or 'headers' in fixed, "应补全源级 header"


def test_fix_cf_bypass_create_config_block():
    """正常用例：searchUrl 无配置块时创建配置块（不加 js 块）。"""
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
    }
    fixed, fixes, manual = fix_cf_bypass({'msg': 'CF'}, source)
    # 应创建配置块
    assert ',{' in fixed['searchUrl'], f"应创建配置块: {fixed['searchUrl']}"
    # 不应含 js 块
    assert '"js"' not in fixed['searchUrl'], f"配置块不应含 js 字段: {fixed['searchUrl']}"


def test_fix_cf_bypass_no_source_url():
    """异常用例：无 sourceUrl 无法配置 WebView。"""
    source = {"searchUrl": "test"}
    fixed, fixes, manual = fix_cf_bypass({'msg': 'CF'}, source)
    assert manual, "无 sourceUrl 应返回 manual 建议"
    # 无 sourceUrl 时不应配置 loginUrl
    assert not fixed.get('loginUrl', '').startswith('@js:java.webView'), \
        "无 sourceUrl 不应配置 WebView loginUrl"


def test_fix_cf_bypass_remove_login_check_js():
    """边界用例：已有 loginCheckJs 应被移除。"""
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
        "loginCheckJs": "java.ajax()",
    }
    fixed, fixes, manual = fix_cf_bypass({'msg': 'CF'}, source)
    assert 'loginCheckJs' not in fixed, "loginCheckJs 应被移除"
    assert any('loginCheckJs' in f for f in fixes), "应记录移除 loginCheckJs"


# ==================== ② fix_website_revamp 测试（网站改版重分析） ====================

def test_fix_website_revamp_bug2_ssr_webview():
    """BUG②: SSR/SPA 检测后应配置 loginUrl+WebView（非空字符串）。"""
    # 构造 SSR HTML（含 __NEXT_DATA__ 标记）
    ssr_html = '<html><head><script>window.__NEXT_DATA__={}</script></head><body></body></html>'
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
    }
    fixed, fixes, manual = fix_website_revamp({'msg': '搜索结果为空'}, source, html=ssr_html)

    # SSR/SPA 检测后应配置 loginUrl+WebView（非空字符串）
    assert fixed.get('loginUrl', ''), "SSR/SPA 应配置 loginUrl（非空）"
    assert fixed['loginUrl'].startswith('@js:java.webView'), \
        f"loginUrl 应为 WebView: {fixed['loginUrl']}"
    # 不应设置 loginCheckJs
    assert 'loginCheckJs' not in fixed, "不应设置 loginCheckJs"
    assert any('SSR' in f or 'SPA' in f for f in fixes), f"应记录 SSR/SPA 降级: {fixes}"


def test_fix_website_revamp_ssr_various_markers():
    """边界用例：多种 SSR 标记都能识别。"""
    markers = ['__NUXT__', 'data-n-head-ssr', 'window.__INITIAL_STATE__',
               'data-react-helmet', 'ng-server-context', 'data-server-rendered']
    for marker in markers:
        html = f'<html><body><script>{marker}</script></body></html>'
        assert _is_ssr_spa(html), f"应识别 SSR 标记: {marker}"
    assert not _is_ssr_spa(''), "空 HTML 不应识别为 SSR"
    assert not _is_ssr_spa('<html><body>普通页面</body></html>'), "普通页面不应识别为 SSR"


def test_fix_website_revamp_dom_analysis():
    """正常用例：非 SSR 网站用 DOM 分析生成新选择器。"""
    if not _bs4_available():
        # bs4 不可用时，验证降级行为
        html = '<html><body><div class="book-item">x</div></body></html>'
        source = {"bookSourceUrl": "https://example.com", "searchUrl": "/search"}
        fixed, fixes, manual = fix_website_revamp({'msg': '搜索结果为空'}, source, html=html)
        assert manual, "bs4 不可用时应返回 manual"
        return

    html = '''
    <html><body>
    <div class="book-item"><a href="/book/1">书名1</a><span>作者1著</span></div>
    <div class="book-item"><a href="/book/2">书名2</a><span>作者2著</span></div>
    <div class="book-item"><a href="/book/3">书名3</a><span>作者3著</span></div>
    </body></html>
    '''
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
        "ruleSearch": {"bookList": ".old-selector"},
    }
    fixed, fixes, manual = fix_website_revamp({'msg': '搜索结果为空'}, source, html=html)
    # 应更新 bookList（DOM 分析识别到 .book-item）
    assert fixed['ruleSearch'].get('bookList') == '.book-item', \
        f"应更新 bookList: {fixed['ruleSearch'].get('bookList')}"
    assert len(fixes) > 0, "应产生修复项"


def test_fix_website_revamp_no_html_no_source():
    """异常用例：无 HTML 且无 sourceUrl 无法获取。"""
    source = {"searchUrl": "test"}
    fixed, fixes, manual = fix_website_revamp({'msg': '搜索结果为空'}, source, html=None)
    assert manual, "无 HTML 应返回 manual"
    # 无 sourceUrl 时 _fetch_search_html 返回空，不应产生 fixes
    assert fixes == [], "无 HTML 不应产生自动修复"


def test_fix_website_revamp_empty_html_string():
    """边界用例：传入空字符串 HTML 触发主动获取（无 sourceUrl 时返回空）。"""
    source = {"searchUrl": "test"}  # 无 bookSourceUrl/sourceUrl
    fixed, fixes, manual = fix_website_revamp({'msg': '搜索结果为空'}, source, html="")
    assert manual, "无 HTML 可获取时应返回 manual"


# ==================== ③ fix_css_selector 测试（CSS 选择器修复） ====================

def test_fix_css_selector_bug3_no_html():
    """BUG③: 无 HTML 时不应修改选择器（不驼峰转换/不模糊匹配）。"""
    source = {
        "ruleSearch": {"name": ".book-name@text"},
        "ruleBookInfo": {"bookName": ".title"},
    }
    fixed, fixes, manual = fix_css_selector({'msg': '选择器未匹配'}, source, html=None)

    # 无 HTML 时不应修改选择器
    assert fixes == [], f"无 HTML 时不应修改选择器: {fixes}"
    assert manual, f"无 HTML 时应返回 manual 建议: {manual}"
    # 选择器应保持原样（不驼峰转换/不模糊匹配）
    assert fixed['ruleSearch']['name'] == '.book-name@text', \
        f"选择器不应被破坏: {fixed['ruleSearch']['name']}"
    assert fixed['ruleBookInfo']['bookName'] == '.title', \
        f"选择器不应被破坏: {fixed['ruleBookInfo']['bookName']}"


def test_fix_css_selector_with_html_match():
    """正常用例：有 HTML 时验证选择器匹配（已匹配则不修改）。"""
    if not _bs4_available():
        source = {"ruleSearch": {"name": ".book-name@text"}}
        fixed, fixes, manual = fix_css_selector({'msg': ''}, source, html='<html></html>')
        assert manual, "bs4 不可用时应返回 manual"
        return

    html = '''
    <html><body>
    <div class="book-name">书名</div>
    </body></html>
    '''
    source = {"ruleSearch": {"name": ".book-name@text"}}
    fixed, fixes, manual = fix_css_selector({'msg': '选择器未匹配'}, source, html=html)
    # 选择器已匹配，不应修改
    assert fixed['ruleSearch']['name'] == '.book-name@text', \
        f"已匹配的选择器不应被修改: {fixed['ruleSearch']['name']}"


def test_fix_css_selector_with_html_no_match():
    """正常用例：有 HTML 时选择器不匹配，尝试替代或返回 manual。"""
    if not _bs4_available():
        source = {"ruleSearch": {"bookList": ".nonexistent"}}
        fixed, fixes, manual = fix_css_selector({'msg': ''}, source, html='<html></html>')
        assert manual, "bs4 不可用时应返回 manual"
        return

    html = '''
    <html><body>
    <div class="book-item"><a href="/book/1">书名1</a></div>
    <div class="book-item"><a href="/book/2">书名2</a></div>
    <div class="book-item"><a href="/book/3">书名3</a></div>
    </body></html>
    '''
    source = {"ruleSearch": {"bookList": ".nonexistent-selector"}}
    fixed, fixes, manual = fix_css_selector({'msg': '选择器未匹配'}, source, html=html)
    # 选择器不匹配，应尝试替代或返回 manual
    # 原选择器不应保留（要么被替代，要么返回 manual）
    assert fixed['ruleSearch']['bookList'] != '.nonexistent-selector' or manual, \
        "不匹配的选择器应被替代或返回 manual"


def test_fix_css_selector_empty_source():
    """异常用例：空 source。"""
    fixed, fixes, manual = fix_css_selector({'msg': ''}, {}, html=None)
    assert fixes == []
    assert manual


def test_fix_css_selector_skip_non_css():
    """边界用例：JSONPath/XPath/JS 规则不应被当作 CSS 处理。"""
    source = {
        "ruleSearch": {
            "name": "$.data.name",       # JSONPath
            "author": "//div[@class='author']",  # XPath
            "intro": "@js:result",       # JS
        }
    }
    fixed, fixes, manual = fix_css_selector({'msg': ''}, source, html=None)
    # 这些规则不应被修改
    assert fixed['ruleSearch']['name'] == '$.data.name'
    assert fixed['ruleSearch']['author'] == "//div[@class='author']"
    assert fixed['ruleSearch']['intro'] == '@js:result'


# ==================== fix_url_template 测试 ====================

def test_fix_url_template_post():
    """正常用例：POST 接口补全配置块。"""
    source = {"searchUrl": "https://example.com/search"}
    fixed, fixes, manual = fix_url_template({'msg': 'need POST method'}, source)
    assert ',{' in fixed['searchUrl'], "应补全配置块"
    assert 'POST' in fixed['searchUrl'], "应含 POST method"
    assert len(fixes) > 0


def test_fix_url_template_existing_config():
    """正常用例：已有配置块补全 charset/headers。"""
    source = {"searchUrl": 'https://example.com/search,{"method":"POST"}'}
    fixed, fixes, manual = fix_url_template({'msg': ''}, source)
    assert 'charset' in fixed['searchUrl'], "应补全 charset"
    assert 'headers' in fixed['searchUrl'], "应补全 headers"


def test_fix_url_template_no_searchurl():
    """异常用例：无 searchUrl。"""
    fixed, fixes, manual = fix_url_template({'msg': ''}, {})
    assert manual, "无 searchUrl 应返回 manual"
    assert fixes == []


def test_fix_url_template_invalid_json():
    """边界用例：配置块 JSON 格式错误。"""
    source = {"searchUrl": "https://example.com/search,{invalid json}"}
    fixed, fixes, manual = fix_url_template({'msg': ''}, source)
    assert manual, "JSON 格式错误应返回 manual"


# ==================== fix_field_mapping 测试 ====================

def test_fix_field_mapping_name_to_bookname():
    """正常用例：name → bookName。"""
    source = {"ruleSearch": {"name": ".title@text"}}
    fixed, fixes, manual = fix_field_mapping({'msg': ''}, source)
    assert 'bookName' in fixed['ruleSearch'], "应添加 bookName"
    assert 'name' not in fixed['ruleSearch'], "应删除 name"
    assert any('name' in f and 'bookName' in f for f in fixes), f"应记录修复: {fixes}"


def test_fix_field_mapping_author_to_bookauthor():
    """正常用例：author → bookAuthor。"""
    source = {"ruleBookInfo": {"author": ".author@text"}}
    fixed, fixes, manual = fix_field_mapping({'msg': ''}, source)
    assert 'bookAuthor' in fixed['ruleBookInfo']
    assert 'author' not in fixed['ruleBookInfo']


def test_fix_field_mapping_no_change():
    """边界用例：字段已正确，无需修改。"""
    source = {"ruleSearch": {"bookName": ".title@text"}}
    fixed, fixes, manual = fix_field_mapping({'msg': ''}, source)
    assert fixes == [], "字段已正确不应修改"
    assert manual, "应返回 manual 提示"


def test_fix_field_mapping_empty():
    """异常用例：空 source。"""
    fixed, fixes, manual = fix_field_mapping({'msg': ''}, {})
    assert manual


# ==================== fix_rule_syntax 测试 ====================

def test_fix_rule_syntax_jsonpath_prefix():
    """正常用例：JSONPath @. 前缀 → $. 前缀。"""
    source = {"ruleSearch": {"name": "@.data.list"}}
    fixed, fixes, manual = fix_rule_syntax({'msg': ''}, source)
    assert fixed['ruleSearch']['name'] == '$.data.list', \
        f"JSONPath 前缀修正失败: {fixed['ruleSearch']['name']}"
    assert len(fixes) > 0


def test_fix_rule_syntax_add_text_suffix():
    """正常用例：CSS 选择器补全 @text 后缀。"""
    source = {"ruleBookInfo": {"name": "div.title"}}
    fixed, fixes, manual = fix_rule_syntax({'msg': ''}, source)
    assert '@text' in fixed['ruleBookInfo']['name'], \
        f"@text 补全失败: {fixed['ruleBookInfo']['name']}"


def test_fix_rule_syntax_add_href_suffix():
    """正常用例：CSS 选择器补全 @href 后缀。"""
    source = {"ruleBookInfo": {"bookUrl": "a.link"}}
    fixed, fixes, manual = fix_rule_syntax({'msg': ''}, source)
    assert '@href' in fixed['ruleBookInfo']['bookUrl'], \
        f"@href 补全失败: {fixed['ruleBookInfo']['bookUrl']}"


def test_fix_rule_syntax_no_change():
    """边界用例：规则已正确，无需修改。"""
    source = {"ruleBookInfo": {"name": "div.title@text"}}
    fixed, fixes, manual = fix_rule_syntax({'msg': ''}, source)
    assert fixes == [], "规则已正确不应修改"
    assert manual


def test_fix_rule_syntax_empty():
    """异常用例：空 source。"""
    fixed, fixes, manual = fix_rule_syntax({'msg': ''}, {})
    assert manual


# ==================== auto_fix_error 主函数测试 ====================

def test_auto_fix_error_rule_parse():
    """正常用例：rule_parse 错误自动修复。"""
    source = {"ruleSearch": {"name": "@.data.list"}}
    result = auto_fix_error(
        {'msg': 'CSS选择器错误', 'suggestion': {'error_type': 'rule_parse'}},
        source
    )
    assert isinstance(result, dict)
    for key in ('success', 'fixed_source', 'fixes_applied', 'verify_result', 'attempts'):
        assert key in result, f"缺少返回字段: {key}"
    # rule_parse 应触发 fix_rule_syntax，修正 JSONPath 前缀
    assert len(result['fixes_applied']) > 0, "应产生修复项"


def test_auto_fix_error_need_login_manual():
    """正常用例：need_login 需用户介入，不自动修复。"""
    source = {"bookSourceUrl": "https://example.com"}
    result = auto_fix_error(
        {'msg': 'need login', 'suggestion': {'error_type': 'need_login'}},
        source
    )
    assert result['success'] is False, "need_login 不应自动修复成功"
    assert result['verify_result']['status'] == 'manual', "应标记为 manual"
    assert result['fixes_applied'] == [], "不应自动修复"


def test_auto_fix_error_cf_challenge():
    """正常用例：cf_challenge 触发 fix_cf_bypass。"""
    source = {
        "bookSourceUrl": "https://example.com",
        "searchUrl": "https://example.com/search?q={{key}}",
    }
    result = auto_fix_error(
        {'msg': 'cloudflare challenge', 'suggestion': {'error_type': 'cf_challenge'}},
        source
    )
    assert isinstance(result, dict)
    # cf_challenge 应触发 fix_cf_bypass，配置 loginUrl
    assert result['fixed_source'].get('loginUrl', '').startswith('@js:java.webView'), \
        f"应配置 WebView loginUrl: {result['fixed_source'].get('loginUrl')}"


def test_auto_fix_error_empty_source():
    """异常用例：空 source。"""
    result = auto_fix_error({'msg': 'unknown error'}, {})
    assert isinstance(result, dict)
    assert 'fixed_source' in result


def test_auto_fix_error_string_error():
    """边界用例：字符串错误信息。"""
    result = auto_fix_error('timeout error', {"searchUrl": "test"})
    assert isinstance(result, dict)
    assert 'error_type' in result.get('verify_result', {}) or 'status' in result.get('verify_result', {})


# ==================== 辅助函数测试 ====================

def test_normalize_source_dict():
    """测试 _normalize_source 处理 dict。"""
    source = {"a": 1}
    assert _normalize_source(source) == source


def test_normalize_source_json_string():
    """测试 _normalize_source 处理 JSON 字符串。"""
    assert _normalize_source('{"a": 1}') == {"a": 1}


def test_normalize_source_json_list():
    """测试 _normalize_source 处理 JSON 列表。"""
    assert _normalize_source('[{"a": 1}]') == {"a": 1}
    assert _normalize_source('[]') == {}


def test_normalize_source_invalid():
    """测试 _normalize_source 处理非法输入。"""
    assert _normalize_source('invalid json') == {}
    assert _normalize_source(None) == {}
    assert _normalize_source(123) == {}


def test_infer_error_type():
    """测试 _infer_error_type 错误类型推断。"""
    assert _infer_error_type('JS error exception') == 'js_error'
    assert _infer_error_type('need login') == 'need_login'
    assert _infer_error_type('搜索结果为空') == 'search_empty'
    assert _infer_error_type('cloudflare challenge') == 'cf_challenge'
    assert _infer_error_type('HTTP 403 forbidden') == 'http_403'
    assert _infer_error_type('jar timeout') == 'jar_timeout'
    assert _infer_error_type('jar crash') == 'jar_crash'
    assert _infer_error_type('') == 'unknown'
    assert _infer_error_type('unrecognized xyz') == 'unknown'


def test_looks_like_css():
    """测试 _looks_like_css 判断。"""
    assert _looks_like_css('.book-name') is True
    assert _looks_like_css('div.title') is True
    assert _looks_like_css('$.data.list') is False  # JSONPath
    assert _looks_like_css('//div[@class="x"]') is False  # XPath
    assert _looks_like_css('@xpath://div') is False
    assert _looks_like_css('@js:result') is False
    assert _looks_like_css('<js>code</js>') is False
    assert _looks_like_css('') is False
    assert _looks_like_css(None) is False


def test_parse_error_dict():
    """测试 _parse_error 处理 dict。"""
    err = {'msg': 'test', 'stackTrace': 'stack', 'failedStage': 'search',
           'suggestion': {'error_type': 'rule_parse'}}
    result = _parse_error(err)
    assert result['msg'] == 'test'
    assert result['stack'] == 'stack'
    assert result['stage'] == 'search'
    assert result['error_type'] == 'rule_parse'


def test_parse_error_string():
    """测试 _parse_error 处理字符串。"""
    result = _parse_error('timeout error')
    assert result['msg'] == 'timeout error'
    assert result['error_type'] == 'network'


# ==================== 历史记录测试 ====================

def test_record_and_load_fix_history():
    """测试修复历史记录读写。"""
    error_type = '_test_auto_fixer_unit'
    record_fix_history(error_type, '测试修复方案')
    history = load_fix_history(error_type)
    assert history, "历史记录应非空"
    assert history[-1]['solution'] == '测试修复方案'
    assert history[-1]['error_type'] == error_type
    # 清理
    cache_file = _cache_path(error_type)
    if cache_file.exists():
        cache_file.unlink()


def test_load_fix_history_nonexistent():
    """测试加载不存在的历史记录。"""
    history = load_fix_history('_nonexistent_error_type_xyz')
    assert history == [], "不存在的历史记录应返回空列表"


if __name__ == '__main__':
    # 独立运行模式：手动收集并执行所有 test_ 函数
    test_funcs = [
        # fix_cf_bypass
        ('test_fix_cf_bypass_bug1_webview_login', test_fix_cf_bypass_bug1_webview_login),
        ('test_fix_cf_bypass_normal', test_fix_cf_bypass_normal),
        ('test_fix_cf_bypass_create_config_block', test_fix_cf_bypass_create_config_block),
        ('test_fix_cf_bypass_no_source_url', test_fix_cf_bypass_no_source_url),
        ('test_fix_cf_bypass_remove_login_check_js', test_fix_cf_bypass_remove_login_check_js),
        # fix_website_revamp
        ('test_fix_website_revamp_bug2_ssr_webview', test_fix_website_revamp_bug2_ssr_webview),
        ('test_fix_website_revamp_ssr_various_markers', test_fix_website_revamp_ssr_various_markers),
        ('test_fix_website_revamp_dom_analysis', test_fix_website_revamp_dom_analysis),
        ('test_fix_website_revamp_no_html_no_source', test_fix_website_revamp_no_html_no_source),
        ('test_fix_website_revamp_empty_html_string', test_fix_website_revamp_empty_html_string),
        # fix_css_selector
        ('test_fix_css_selector_bug3_no_html', test_fix_css_selector_bug3_no_html),
        ('test_fix_css_selector_with_html_match', test_fix_css_selector_with_html_match),
        ('test_fix_css_selector_with_html_no_match', test_fix_css_selector_with_html_no_match),
        ('test_fix_css_selector_empty_source', test_fix_css_selector_empty_source),
        ('test_fix_css_selector_skip_non_css', test_fix_css_selector_skip_non_css),
        # fix_url_template
        ('test_fix_url_template_post', test_fix_url_template_post),
        ('test_fix_url_template_existing_config', test_fix_url_template_existing_config),
        ('test_fix_url_template_no_searchurl', test_fix_url_template_no_searchurl),
        ('test_fix_url_template_invalid_json', test_fix_url_template_invalid_json),
        # fix_field_mapping
        ('test_fix_field_mapping_name_to_bookname', test_fix_field_mapping_name_to_bookname),
        ('test_fix_field_mapping_author_to_bookauthor', test_fix_field_mapping_author_to_bookauthor),
        ('test_fix_field_mapping_no_change', test_fix_field_mapping_no_change),
        ('test_fix_field_mapping_empty', test_fix_field_mapping_empty),
        # fix_rule_syntax
        ('test_fix_rule_syntax_jsonpath_prefix', test_fix_rule_syntax_jsonpath_prefix),
        ('test_fix_rule_syntax_add_text_suffix', test_fix_rule_syntax_add_text_suffix),
        ('test_fix_rule_syntax_add_href_suffix', test_fix_rule_syntax_add_href_suffix),
        ('test_fix_rule_syntax_no_change', test_fix_rule_syntax_no_change),
        ('test_fix_rule_syntax_empty', test_fix_rule_syntax_empty),
        # auto_fix_error
        ('test_auto_fix_error_rule_parse', test_auto_fix_error_rule_parse),
        ('test_auto_fix_error_need_login_manual', test_auto_fix_error_need_login_manual),
        ('test_auto_fix_error_cf_challenge', test_auto_fix_error_cf_challenge),
        ('test_auto_fix_error_empty_source', test_auto_fix_error_empty_source),
        ('test_auto_fix_error_string_error', test_auto_fix_error_string_error),
        # 辅助函数
        ('test_normalize_source_dict', test_normalize_source_dict),
        ('test_normalize_source_json_string', test_normalize_source_json_string),
        ('test_normalize_source_json_list', test_normalize_source_json_list),
        ('test_normalize_source_invalid', test_normalize_source_invalid),
        ('test_infer_error_type', test_infer_error_type),
        ('test_looks_like_css', test_looks_like_css),
        ('test_parse_error_dict', test_parse_error_dict),
        ('test_parse_error_string', test_parse_error_string),
        # 历史记录
        ('test_record_and_load_fix_history', test_record_and_load_fix_history),
        ('test_load_fix_history_nonexistent', test_load_fix_history_nonexistent),
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
