#!/usr/bin/env python3
"""
auto_fixer.py - 错误自动修复模块（7.6）

当 debug-source.py 检测到错误时（CSS选择器未匹配/URL返回空/字段解析错误/规则语法错误），
自动分析错误并尝试修复，最多重试3次。

修复流程：历史方案优先 → 分析错误 → 生成修复 → 应用 → 验证 → 记录

依赖：
- rule_engine_client.RuleEngineClient（verify_fix 验证用，JVM 不可用时降级为 unverifiable）
- basic-memory（可选，try-import，不可用时降级到本地缓存 tools/.fix-cache/）
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# basic-memory 可选依赖（try-import 降级）
# 简化说明：basic-memory 为 MCP 工具，本模块无法直接 import | 已知上限：无法直接读写 basic-memory | 升级路径：宿主集成 MCP 调用
try:
    import basic_memory  # noqa: F401
    _BASIC_MEMORY_AVAILABLE = True
except ImportError:
    _BASIC_MEMORY_AVAILABLE = False

# 路径常量（迁移自 tools/，通过相对路径回到 tools/ 目录以保持缓存位置不变）
_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tools"
_FIX_CACHE_DIR = _TOOLS_DIR / ".fix-cache"


# ==================== 辅助函数 ====================

def _ensure_cache_dir():
    """确保缓存目录存在"""
    _FIX_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(error_type):
    """获取错误类型对应的缓存文件路径"""
    _ensure_cache_dir()
    safe_name = re.sub(r'[^\w\-]', '_', error_type or 'unknown')
    return _FIX_CACHE_DIR / f"{safe_name}.json"


def _normalize_source(source_json):
    """规范化 source_json 参数，返回 dict。

    支持传入 JSON 字符串、dict 或 list（取首个元素）。
    """
    if isinstance(source_json, str):
        try:
            obj = json.loads(source_json)
            if isinstance(obj, list):
                return obj[0] if obj else {}
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(source_json, list):
        return source_json[0] if source_json else {}
    if isinstance(source_json, dict):
        return source_json
    return {}


def _parse_error(error):
    """解析 error 参数，返回标准化错误信息 dict。

    error 可以是 dict（来自 debug-source.py 的错误对象）或 str。
    """
    if isinstance(error, dict):
        msg = error.get('msg', '') or error.get('message', '')
        stack = error.get('stackTrace', '') or error.get('stack', '')
        stage = error.get('failedStage', '') or error.get('stage', '')
        suggestion = error.get('suggestion', {})
        error_type = ''
        if isinstance(suggestion, dict):
            error_type = suggestion.get('error_type', '')
        return {'msg': msg, 'stack': stack, 'stage': stage,
                'error_type': error_type, 'raw': error}
    msg = str(error)
    return {'msg': msg, 'stack': '', 'stage': '',
            'error_type': _infer_error_type(msg), 'raw': {'msg': msg}}


def _infer_error_type(msg):
    """从错误消息推断错误类型"""
    if not msg:
        return 'unknown'
    combined = msg.lower()
    # JS 执行错误（优先判断，避免被 network 等吞掉）
    if 'js' in combined and ('error' in combined or 'exception' in combined or '语法' in combined):
        return 'js_error'
    # 需要登录
    if any(kw in combined for kw in ['login', '登录', '请登录', 'need login']):
        return 'need_login'
    # 搜索结果为空（网站改版/SSR/CSS选择器失效）
    if any(kw in combined for kw in ['搜索结果为空', 'search empty', 'search result empty',
                                      '搜索结果0', 'search 0', 'no result', '无搜索结果',
                                      'booklist为空', 'booklist empty', '列表0', '0本书']):
        return 'search_empty'
    # Cloudflare 挑战
    if any(kw in combined for kw in ['cloudflare', 'cf challenge', '挑战', 'just a moment']):
        return 'cf_challenge'
    # HTTP 403 禁止访问
    if '403' in combined or 'forbidden' in combined or '禁止访问' in combined:
        return 'http_403'
    # JAR 超时（jar + timeout，先于通用 network 判断）
    if 'jar' in combined and any(kw in combined for kw in ['timeout', '超时']):
        return 'jar_timeout'
    # JAR 崩溃（jar + crash/崩溃，不含 timeout）
    if 'jar' in combined and any(kw in combined for kw in ['crash', '崩溃', 'jvm crash']):
        return 'jar_crash'
    # 行为不一致
    if any(kw in combined for kw in ['behavior', '行为不一致', 'mismatch']):
        return 'behavior_mismatch'
    # 字段缺失
    if any(kw in combined for kw in ['field', '字段缺失', 'missing field', '缺少字段']):
        return 'field_missing'
    # 相对路径未拼接
    if any(kw in combined for kw in ['relative', '相对路径', '相对 url']):
        return 'relative_url'
    # 语法错误
    if any(kw in combined for kw in ['syntax', '语法错误', 'syntaxerror']):
        return 'syntax_error'
    if 'typeerror' in combined or 'is not a function' in combined:
        return 'TypeError'
    if any(kw in combined for kw in ['timeout', 'sockettimeout', 'connectexception',
                                      'unknownhost', 'connection refused', '超时', '无法连接']):
        return 'network'
    if any(kw in combined for kw in ['css选择器', 'jsonpath', 'xpath', '选择器未匹配',
                                      '目录为空', '列表为空', '规则错误']):
        return 'rule_parse'
    if 'url' in combined and ('空' in combined or 'empty' in combined or '404' in combined):
        return 'url_empty'
    return 'unknown'


def _looks_like_css(rule):
    """判断规则是否像 CSS 选择器（排除 JSONPath/XPath/JS）"""
    if not rule:
        return False
    if rule.startswith('$.') or rule.startswith('@.'):
        return False
    if rule.startswith('//') or rule.startswith('@xpath'):
        return False
    if '@js:' in rule or '<js>' in rule:
        return False
    return True


def _get_rule_engine_client():
    """延迟导入 RuleEngineClient"""
    try:
        from legado_client.client.rule_engine_client import RuleEngineClient
        return RuleEngineClient
    except ImportError:
        return None


def _iter_rule_sections(source):
    """迭代源中的规则段（ruleSearch/ruleBookInfo/ruleToc/ruleContent/ruleArticle）"""
    for section in ['ruleSearch', 'ruleBookInfo', 'ruleToc', 'ruleContent', 'ruleArticle']:
        rules = source.get(section, {})
        if isinstance(rules, dict):
            yield section, rules


# ==================== 1. 历史方案加载 ====================

def load_fix_history(error_type):
    """从 basic-memory 加载历史修复方案，不可用时降级到本地缓存。

    Args:
        error_type: 错误类型（如 rule_parse/url_empty/css）

    Returns:
        list: 历史修复方案列表，每项 {solution, error_type, timestamp}
    """
    # basic-memory 优先（当前环境不可用，降级到本地缓存）
    path = _cache_path(error_type)
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


# ==================== 2. CSS 选择器修复 ====================

def fix_css_selector(error, source_json, html=None):
    """选择器匹配0元素时，分析页面结构修正选择器。

    常见修正：
    1. 有HTML时：用BeautifulSoup验证选择器是否匹配，不匹配则尝试常见替代选择器
    2. 无HTML时：不盲目修改选择器（驼峰转换/模糊匹配会破坏有效选择器）
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    # 无HTML时不盲目修改选择器（驼峰转换/模糊匹配会破坏有效选择器）
    if not html:
        manual.append('CSS选择器未匹配，需获取页面HTML后分析（禁止盲目驼峰转换/模糊匹配）')
        return source, fixes, manual

    # 有HTML时：用BeautifulSoup验证选择器
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
    except ImportError:
        manual.append('BeautifulSoup未安装，无法验证CSS选择器')
        return source, fixes, manual

    for section, rules in _iter_rule_sections(source):
        for field, val in list(rules.items()):
            if not isinstance(val, str) or not val or not _looks_like_css(val):
                continue

            # 提取CSS选择器部分（去掉@text/@href等属性提取器）
            css_part = val.split('@')[0] if '@' in val else val
            if not css_part or css_part.startswith('<js>'):
                continue

            # 验证选择器是否匹配元素
            try:
                matched = soup.select(css_part)
            except Exception:
                matched = []

            if not matched:
                # 选择器不匹配，尝试常见替代
                # 策略：查找页面中包含书籍关键词的重复结构
                candidates = []
                for tag in soup.find_all(['div', 'ul', 'li', 'tr', 'dl'], limit=200):
                    cls = tag.get('class', [])
                    cls_str = ' '.join(cls) if isinstance(cls, list) else str(cls)
                    # 检测书籍列表特征class名
                    if any(kw in cls_str.lower() for kw in ['book', 'novel', 'item', 'list', 'result', 'card']):
                        selector = '.' + '-'.join(cls[:2]) if isinstance(cls, list) and cls else tag.name
                        if selector and len(soup.select(selector)) >= 3:
                            candidates.append((selector, len(soup.select(selector))))

                if candidates:
                    # 选择匹配数最多的候选
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    best_selector, best_count = candidates[0]
                    new_val = best_selector + (val[len(css_part):] if len(val) > len(css_part) else '')
                    rules[field] = new_val
                    fixes.append(f'{section}.{field}: {val} → {new_val} (HTML验证匹配{best_count}个元素)')
                else:
                    manual.append(f'{section}.{field}: 选择器"{css_part}"在HTML中未匹配，且未找到替代结构')

    if not fixes:
        manual.append('CSS选择器在HTML中未匹配，需手动分析页面结构')

    return source, fixes, manual


# ==================== 3. URL 模板修复 ====================

def fix_url_template(error, source_json, html=None):
    """URL返回空时，分析URL结构修正参数。

    常见修正：
    1. 补全 searchUrl 缺失的 method/charset/headers
    2. POST 请求补全 body 配置
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    search_url = source.get('searchUrl', '')
    if not search_url:
        manual.append('无 searchUrl，需手动添加')
        return source, fixes, manual

    err = error if isinstance(error, dict) else {'msg': str(error)}
    msg_lower = err.get('msg', '').lower()

    # 检查是否已有配置块（Legado 格式：url,{method:POST,body:xxx,...}）
    if ',{' in search_url:
        parts = search_url.split(',{', 1)
        try:
            config = json.loads('{' + parts[1])
            changed = False
            if 'charset' not in config:
                config['charset'] = 'utf-8'
                changed = True
                fixes.append('searchUrl: 补全 charset=utf-8')
            if 'headers' not in config:
                config['headers'] = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6)'}
                changed = True
                fixes.append('searchUrl: 补全 headers')
            if changed:
                source['searchUrl'] = parts[0] + ',{' + json.dumps(config, ensure_ascii=False)[1:]
        except json.JSONDecodeError:
            manual.append('searchUrl 配置块 JSON 格式错误')
    elif 'post' in msg_lower or 'post' in search_url.lower():
        # 看起来是 POST 接口但缺配置块
        config = {
            'method': 'POST',
            'charset': 'utf-8',
            'headers': {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6)'}
        }
        source['searchUrl'] = search_url + ',{' + json.dumps(config, ensure_ascii=False)[1:]
        fixes.append('searchUrl: 补全 POST method/charset/headers')
    else:
        manual.append('searchUrl 无配置块，可能需要补全 method/charset/headers')

    return source, fixes, manual


# ==================== 4. 字段映射修复 ====================

def fix_field_mapping(error, source_json, html=None):
    """字段解析错误时，分析字段位置修正映射。

    常见修正：
    1. name → bookName（字段名修正）
    2. author → bookAuthor
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    # 常见错误字段名 → 正确字段名
    field_aliases = {
        'name': 'bookName',
        'author': 'bookAuthor',
        'title': 'bookName',
        'writer': 'bookAuthor',
    }

    for section in ['ruleSearch', 'ruleBookInfo']:
        rules = source.get(section, {})
        if not isinstance(rules, dict):
            continue
        for wrong, correct in field_aliases.items():
            if wrong in rules and correct not in rules:
                rules[correct] = rules[wrong]
                del rules[wrong]
                fixes.append(f'{section}.{wrong} → {correct}')

    if not fixes:
        manual.append('字段映射可能正确，需检查规则值')

    return source, fixes, manual


# ==================== 5. 规则语法修复 ====================

def fix_rule_syntax(error, source_json, html=None):
    """语法错误时，分析错误位置修正语法。

    常见修正：
    1. CSS选择器缺少 @text/@href 后缀
    2. JSONPath 缺少 $. 前缀（@.data.list → $.data.list）
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    # 需要补 @text 的字段
    text_fields = {'name', 'bookName', 'author', 'bookAuthor', 'title', 'intro', 'desc', 'kind'}
    # 需要补 @href 的字段
    href_fields = {'bookUrl', 'url', 'chapterUrl', 'nextUrl', 'tocUrl'}

    for section, rules in _iter_rule_sections(source):
        for field, val in list(rules.items()):
            if not isinstance(val, str) or not val:
                continue

            new_val = val
            changed = False

            # 修正1：JSONPath @. 前缀 → $. 前缀（@.data.list → $.data.list）
            if val.startswith('@.'):
                new_val = '$.' + val[2:]
                changed = True
                fixes.append(f'{section}.{field}: JSONPath 前缀 {val} → {new_val}')

            # 修正2：CSS选择器缺少 @text/@href 后缀
            elif _looks_like_css(val):
                check_val = val[5:] if val.startswith('@css:') else val
                if '@' not in check_val and re.match(r'^[.#]?[\w\-. >+~\[\]="\']+$', check_val.strip()):
                    if field in text_fields:
                        new_val = val + '@text'
                        changed = True
                        fixes.append(f'{section}.{field}: 补全 @text 后缀')
                    elif field in href_fields:
                        new_val = val + '@href'
                        changed = True
                        fixes.append(f'{section}.{field}: 补全 @href 后缀')

            if changed:
                rules[field] = new_val

    if not fixes:
        manual.append('规则语法可能需要手动检查')

    return source, fixes, manual


# ==================== 5.1 JS 语法修复 ====================

def _fix_brackets_and_quotes(code):
    """修复 JS 代码中未闭合的括号和引号，返回修复后的代码。

    策略：扫描代码维护括号栈和字符串状态，末尾补全未闭合项。
    """
    pairs = {')': '(', ']': '[', '}': '{'}
    closes = {'(': ')', '[': ']', '{': '}'}
    quotes = ("'", '"', '`')
    stack = []
    in_str = None  # 当前所在字符串的引号类型
    i = 0
    while i < len(code):
        ch = code[i]
        if in_str:
            if ch == '\\':
                i += 2  # 跳过转义字符
                continue
            if ch == in_str:
                in_str = None
        elif ch in quotes:
            in_str = ch
        elif ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if stack and stack[-1] == pairs[ch]:
                stack.pop()
        i += 1
    result = code
    if in_str:
        result += in_str  # 补全未闭合的引号
    for ch in reversed(stack):
        result += closes[ch]  # 补全未闭合的括号
    return result


def fix_js_syntax(error, source_json, html=None):
    """JS 执行错误时，检查括号/引号匹配，尝试修复简单语法错误。

    常见修正：
    1. 未闭合的括号（()、[]、{}）补全
    2. 未闭合的引号补全
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    for section, rules in _iter_rule_sections(source):
        for field, val in list(rules.items()):
            if not isinstance(val, str) or not val:
                continue
            # 仅处理含 JS 的规则
            if '@js:' not in val and '<js>' not in val:
                continue

            # 提取 JS 代码段
            if '@js:' in val:
                prefix, js_code = val.split('@js:', 1)
                tag = '@js:'
            else:
                start = val.find('<js>') + 4
                end = val.find('</js>', start)
                prefix = val[:start]
                js_code = val[start:end] if end > start else val[start:]
                tag = '<js>'

            new_js = _fix_brackets_and_quotes(js_code)
            if new_js != js_code:
                if tag == '@js:':
                    new_val = prefix + '@js:' + new_js
                else:
                    new_val = prefix + new_js + ('</js>' if end > start else '')
                rules[field] = new_val
                fixes.append(f'{section}.{field}: JS 语法修复（补全括号/引号）')

    if not fixes:
        manual.append('JS 语法错误可能较复杂，需手动检查')

    return source, fixes, manual


# ==================== 5.2 Header 修复 ====================

def fix_header(error, source_json, html=None):
    """HTTP 403 等错误时，添加默认 User-Agent 和 Header。

    常见修正：
    1. searchUrl 配置块补全/增强 headers
    2. 源级 header 字段补全默认 User-Agent
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    # 修正1：searchUrl 配置块补全/增强 headers
    search_url = source.get('searchUrl', '')
    if search_url and ',{' in search_url:
        parts = search_url.split(',{', 1)
        try:
            config = json.loads('{' + parts[1])
            headers = config.get('headers', {})
            if not isinstance(headers, dict):
                headers = {}
            changed = False
            for k, v in default_headers.items():
                if k not in headers:
                    headers[k] = v
                    changed = True
            if changed:
                config['headers'] = headers
                source['searchUrl'] = parts[0] + ',{' + json.dumps(config, ensure_ascii=False)[1:]
                fixes.append('searchUrl: headers 补全 User-Agent/Accept 等')
        except json.JSONDecodeError:
            manual.append('searchUrl 配置块 JSON 格式错误，无法补全 headers')

    # 修正2：源级 header 字段（Legado 书源用 header 字段）
    if 'header' not in source and 'headers' not in source:
        source['header'] = json.dumps(default_headers, ensure_ascii=False)
        fixes.append('源级 header: 补全默认 User-Agent')

    if not fixes:
        manual.append('无法自动补全 header，需手动添加 User-Agent')

    return source, fixes, manual


# ==================== 5.3 CF盾自动绕过 ====================

def _is_ssr_spa(html: str) -> bool:
    """检测SSR/SPA特征，判断是否需要WebView渲染。

    检测标记：
    - Nuxt.js: data-n-head-ssr, __NUXT__
    - Next.js: __NEXT_DATA__
    - Vue SSR: window.__INITIAL_STATE__
    - React SSR: data-react-helmet
    - Angular SSR: ng-server-context
    """
    if not html:
        return False
    ssr_markers = [
        'data-n-head-ssr', '__NUXT__', '__NEXT_DATA__',
        'window.__INITIAL_STATE__', 'data-react-helmet',
        'ng-server-context', 'data-server-rendered',
    ]
    return any(marker in html for marker in ssr_markers)


def _fetch_search_html(source: dict, keyword: str = "斗破苍穹") -> str:
    """获取搜索页HTML，用于网站改版重分析。

    Args:
        source: 书源/订阅源 dict
        keyword: 搜索关键词（默认用中文常见书名）

    Returns:
        str: 搜索页HTML，失败返回空字符串
    """
    import requests
    from urllib.parse import urljoin, quote

    base_url = source.get('bookSourceUrl') or source.get('sourceUrl') or ''
    search_url = source.get('searchUrl') or ''

    if not base_url or not search_url:
        return ''

    # 清理base_url中的注释标记（如 ##@遇知）
    base_url = re.sub(r'#.*$', '', base_url).strip()

    # 解析searchUrl：可能是相对路径或完整URL
    # Legado格式：/search?q={{key}} 或 https://xxx/search?q={{key}},{...}
    url_part = search_url.split(',{')[0]  # 去掉配置块
    url_part = url_part.replace('{{key}}', quote(keyword, safe=''))

    if url_part.startswith('http'):
        full_url = url_part
    else:
        full_url = urljoin(base_url, url_part)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': base_url,
    }

    try:
        resp = requests.get(full_url, headers=headers, timeout=15, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        return resp.text
    except Exception:
        return ''


def _identify_book_list(soup) -> dict:
    """用BeautifulSoup分析DOM结构，识别书籍列表元素并生成CSS选择器。

    策略：
    1. 找重复结构的容器（class出现3+次的div/li/article）
    2. 在容器内找标题（a/h1/h2/h3/h4带text）
    3. 在容器内找链接（a[href]）

    Returns:
        dict: {bookList, name, author, bookUrl} 或空 dict
    """
    from collections import Counter

    # 统计所有class出现次数
    class_counter = Counter()
    for el in soup.find_all(class_=True):
        for cls in el.get('class', []):
            class_counter[cls] += 1

    # 找出现3+次的class（可能是书籍列表项）
    candidates = [(cls, count) for cls, count in class_counter.items() if count >= 3]
    candidates.sort(key=lambda x: -x[1])

    for cls, count in candidates:
        # 跳过明显不是书籍列表的class
        skip_words = ['nav', 'menu', 'footer', 'header', 'sidebar', 'ad', 'banner',
                      'pagination', 'breadcrumb', 'comment', 'share', 'related']
        if any(sw in cls.lower() for sw in skip_words):
            continue

        # 找使用这个class的元素
        elements = soup.find_all(class_=cls)
        if len(elements) < 3:
            continue

        # 检查元素内是否有链接和文本（书籍特征）
        first_el = elements[0]
        links = first_el.find_all('a', href=True)
        texts = [t.get_text(strip=True) for t in first_el.find_all(['a', 'h1', 'h2', 'h3', 'h4', 'h5', 'p', 'span']) if t.get_text(strip=True)]

        if not links or not texts:
            continue

        # 生成CSS选择器
        # 优先用class选择器
        book_list_selector = f'.{cls}'

        # 找标题选择器
        name_selector = ''
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            title_el = first_el.find(tag)
            if title_el and title_el.get_text(strip=True):
                name_selector = f'{tag}@text'
                break
        if not name_selector:
            link_el = links[0]
            if link_el.get_text(strip=True):
                name_selector = 'a.0@text' if len(links) > 1 else 'a@text'

        # 找作者选择器
        author_selector = ''
        for tag in ['span', 'p', 'div']:
            for el in first_el.find_all(tag):
                text = el.get_text(strip=True)
                if text and ('作者' in text or '著' in text or 'Author' in text.lower()):
                    author_selector = f'{tag}@text'
                    break
            if author_selector:
                break

        # 找书籍URL选择器
        book_url_selector = 'a.0@href' if len(links) > 1 else 'a@href'

        return {
            'bookList': book_list_selector,
            'name': name_selector,
            'author': author_selector,
            'bookUrl': book_url_selector,
            'match_count': count,
        }

    return {}


def fix_cf_bypass(error, source_json, html=None):
    """CF盾自动绕过：loginUrl 设为普通首页 URL + UA增强 + Referer添加。

    策略（基于陷阱#54/#57源码核实，2026-07-17 v2 修正）：
    1. loginUrl 设为**普通首页 URL**（不可用 @js:java.webView(...)，源码锚定：
       WebViewLoginFragment.loadUrl() 不识别 @js: 形式）
    2. 用户需手动点击"登录"按钮触发 WebView 加载 → 自动通过 CF JS Challenge
    3. 补全真实浏览器headers（UA/Accept/Referer）到searchUrl配置块和源级header
    4. 禁止设置loginCheckJs（陷阱#57：会导致无限循环）

    常见修正：
    1. loginUrl 设为普通 URL（用户手动触发登录后 WebView 自动通过 CF）
    2. searchUrl配置块补全headers（含Referer）
    3. 源级header补全
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    base_url = source.get('bookSourceUrl') or source.get('sourceUrl') or ''
    # 清理base_url中的注释标记
    base_url_clean = re.sub(r'#.*$', '', base_url).strip()
    if base_url_clean:
        default_headers['Referer'] = base_url_clean

    # 1. loginUrl 设为普通首页 URL（v2 修正：禁止用 @js:java.webView(...) 形式）
    # 源码锚定：app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt 的 loadUrl 不识别 @js:
    # 用户需手动点击"登录"按钮触发 WebView 加载，WebView 自动执行 CF JS Challenge
    if base_url_clean:
        # loginUrl 设为普通 URL（用户手动触发登录后 WebView 自动通过 CF）
        existing_login = source.get('loginUrl', '')
        if existing_login != base_url_clean:
            source['loginUrl'] = base_url_clean
            fixes.append(f'CF绕过: loginUrl 设为普通 URL（用户需手动点击"登录"按钮触发 WebView 加载首页，自动通过 CF JS Challenge）')
        # 移除loginCheckJs（如果存在，防止无限循环）
        if 'loginCheckJs' in source:
            del source['loginCheckJs']
            fixes.append('CF绕过: 移除loginCheckJs（陷阱#57：CF站会导致无限循环）')
    else:
        manual.append('无sourceUrl/bookSourceUrl，无法配置WebView CF绕过')

    # 2. searchUrl配置块补全headers（移除js字段，避免Rhino语法错误）
    search_url = source.get('searchUrl', '')
    if search_url and ',{' in search_url:
        parts = search_url.split(',{', 1)
        try:
            config = json.loads('{' + parts[1])
            headers = config.get('headers', {})
            if not isinstance(headers, dict):
                headers = {}
            changed = False
            for k, v in default_headers.items():
                if k not in headers:
                    headers[k] = v
                    changed = True
            # 移除js字段（之前的BUG：java.ajax()在Rhino中语法错误）
            if 'js' in config:
                del config['js']
                changed = True
                fixes.append('CF绕过: 移除searchUrl中的js块（Rhino语法错误，改用loginUrl)')
            if changed:
                config['headers'] = headers
                source['searchUrl'] = parts[0] + ',{' + json.dumps(config, ensure_ascii=False)[1:]
                fixes.append('CF绕过: searchUrl headers补全UA/Accept/Referer')
        except json.JSONDecodeError:
            manual.append('searchUrl配置块JSON格式错误，无法补全headers')
    elif search_url:
        # 无配置块，创建headers配置（不加js块）
        config = {
            'method': 'GET',
            'charset': 'utf-8',
            'headers': default_headers,
        }
        source['searchUrl'] = search_url + ',{' + json.dumps(config, ensure_ascii=False)[1:]
        fixes.append('CF绕过: 创建searchUrl配置块（UA+Referer，无js块）')
    else:
        manual.append('无searchUrl，无法补全headers')

    # 3. 源级header补全
    if 'header' not in source and 'headers' not in source:
        source['header'] = json.dumps(default_headers, ensure_ascii=False)
        fixes.append('源级header: 补全默认UA+Referer')

    return source, fixes, manual


# ==================== 5.4 网站改版重分析 ====================

def fix_website_revamp(error, source_json, html=None):
    """网站改版重分析：获取HTML→分析DOM→生成新CSS选择器。

    当CSS选择器失效（搜索结果为空）时：
    1. 获取搜索页HTML
    2. 检测SSR/SPA（如果是SSR，标记需WebView降级）
    3. 用BeautifulSoup分析DOM结构
    4. 识别书籍列表元素并生成新CSS选择器
    5. 更新源规则

    常见修正：
    1. ruleSearch.bookList 更新为新选择器
    2. ruleSearch.name/author/bookUrl 更新
    3. SSR/SPA网站标记需WebView
    """
    source = _normalize_source(source_json)
    fixes = []
    manual = []

    # 获取HTML（优先用传入的html，否则主动获取）
    if not html:
        html = _fetch_search_html(source)

    if not html:
        manual.append('无法获取搜索页HTML，需手动分析网站结构')
        return source, fixes, manual

    # 检测SSR/SPA
    if _is_ssr_spa(html):
        # SSR/SPA网站需要 WebView 渲染动态内容
        # v2 修正（2026-07-17）：loginUrl 设为普通首页 URL，禁止用 @js:java.webView(...)
        # 源码锚定：WebViewLoginFragment.loadUrl() 不识别 @js: 形式
        base_url = source.get('bookSourceUrl') or source.get('sourceUrl') or ''
        base_url_clean = re.sub(r'#.*$', '', base_url).strip()
        if base_url_clean:
            # loginUrl 设为普通 URL，用户手动点击"登录"后 WebView 加载并渲染动态内容
            source['loginUrl'] = base_url_clean
            fixes.append('SSR/SPA降级: loginUrl 设为普通 URL（用户手动点击"登录"按钮后 WebView 加载并渲染动态内容，Nuxt.js/Next.js/Vue SSR）')
            # 移除loginCheckJs（防止无限循环）
            if 'loginCheckJs' in source:
                del source['loginCheckJs']
                fixes.append('SSR/SPA降级: 移除loginCheckJs（陷阱#57：防止无限循环）')
        else:
            manual.append('SSR/SPA网站（Nuxt.js/Next.js等），但无sourceUrl无法配置WebView，需手动配置')
        return source, fixes, manual

    # 用BeautifulSoup分析DOM结构
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
    except ImportError:
        manual.append('BeautifulSoup未安装，无法分析DOM结构')
        return source, fixes, manual

    # 识别书籍列表元素
    new_selectors = _identify_book_list(soup)
    if not new_selectors:
        manual.append('无法自动识别书籍列表元素，需手动分析HTML结构')
        return source, fixes, manual

    # 更新ruleSearch
    rule_search = source.get('ruleSearch', {})
    if not isinstance(rule_search, dict):
        rule_search = {}

    old_bookList = rule_search.get('bookList', '')
    if new_selectors.get('bookList') and new_selectors['bookList'] != old_bookList:
        rule_search['bookList'] = new_selectors['bookList']
        fixes.append(f'ruleSearch.bookList: {old_bookList} → {new_selectors["bookList"]} (匹配{new_selectors.get("match_count",0)}个元素)')

    if new_selectors.get('name'):
        rule_search['name'] = new_selectors['name']
        fixes.append(f'ruleSearch.name → {new_selectors["name"]}')
    if new_selectors.get('author'):
        rule_search['author'] = new_selectors['author']
        fixes.append(f'ruleSearch.author → {new_selectors["author"]}')
    if new_selectors.get('bookUrl'):
        rule_search['bookUrl'] = new_selectors['bookUrl']
        fixes.append(f'ruleSearch.bookUrl → {new_selectors["bookUrl"]}')

    source['ruleSearch'] = rule_search

    if not fixes:
        manual.append('DOM分析未找到合适的书籍列表元素，需手动分析')

    return source, fixes, manual


# ==================== 5.5 需用户介入标记 ====================

def _make_manual_fixer(error_type):
    """生成需用户介入的修复函数（不自动修复，仅返回建议）。

    适用于：need_login / cf_challenge / jar_crash / jar_timeout / behavior_mismatch
    """
    suggestions = {
        'need_login': '该网站需要登录，请在 Legado 中配置登录信息后重试',
        'cf_challenge': '遇到 Cloudflare 挑战，需手动处理（如配置代理或使用浏览器获取 cookie）',
        'jar_crash': 'JAR 崩溃，属环境问题，请检查 Java 版本和 JAR 完整性',
        'jar_timeout': 'JAR 超时，属环境问题，请检查 JVM 启动参数和网络',
        'behavior_mismatch': '行为不一致，需对照 Legado 源码深入分析规则逻辑',
    }
    suggestion = suggestions.get(error_type, '需用户介入处理')

    def _fixer(error, source_json, html=None):
        source = _normalize_source(source_json)
        return source, [], [suggestion]

    return _fixer


# ==================== 6. 修复验证 ====================

def verify_fix(source_json, error_stage):
    """修复后验证：调用 RuleEngineClient 执行实际规则验证。

    通过 debug_book_source/debug_rss_source 执行端到端调试，
    检查修复后的规则是否能正常工作。

    Args:
        source_json: 源 JSON（str 或 dict）
        error_stage: 失败阶段（search/detail/toc/content/sort）

    Returns:
        dict: {status: 'passed'|'failed'|'unverifiable', detail: str}
    """
    ClientCls = _get_rule_engine_client()
    if ClientCls is None:
        return {'status': 'unverifiable', 'detail': 'rule_engine_client 模块不可用'}

    source = _normalize_source(source_json)
    # 推断源类型：有 bookSourceUrl 为书源，有 sourceUrl+ruleArticles 为订阅源
    if 'bookSourceUrl' in source:
        source_type = 'book'
    elif 'sourceUrl' in source or 'ruleArticles' in source:
        source_type = 'rss'
    else:
        source_type = 'book'

    source_json_str = json.dumps(source, ensure_ascii=False) if isinstance(source, dict) else source_json

    try:
        with ClientCls(timeout=30) as client:
            ping = client.ping()
            if not ping.get('ok'):
                return {'status': 'unverifiable',
                        'detail': f'JVM ping 失败: {ping.get("error", "")}'}

            # 执行实际规则验证：调用端到端调试
            result = {}
            def _on_result(success, summary):
                result['success'] = success
                result['summary'] = summary

            def _on_error(msg, stack_trace, failed_stage):
                result['error'] = msg
                result['failed_stage'] = failed_stage

            if source_type == 'book':
                client.debug_book_source(
                    source_json_str, '验证',
                    on_error=_on_error,
                    on_result=_on_result
                )
            else:
                client.debug_rss_source(
                    source_json_str, '验证',
                    on_error=_on_error,
                    on_result=_on_result
                )

            if result.get('success'):
                return {'status': 'passed',
                        'detail': f'修复验证通过，{error_stage or "未知"}阶段规则正常'}
            else:
                err_msg = result.get('error', '调试未返回成功结果')
                return {'status': 'failed',
                        'detail': f'修复验证失败：{err_msg}'}
    except FileNotFoundError as e:
        return {'status': 'unverifiable', 'detail': f'JAR 缺失: {e}'}
    except RuntimeError as e:
        return {'status': 'unverifiable', 'detail': f'JVM 启动失败: {e}'}
    except Exception as e:
        return {'status': 'unverifiable', 'detail': f'验证异常: {e}'}


# ==================== 7. 修复历史记录 ====================

def record_fix_history(error_type, fix_solution):
    """记录修复历史到 basic-memory 和本地缓存。

    Args:
        error_type: 错误类型
        fix_solution: 修复方案描述（str 或 dict）
    """
    _ensure_cache_dir()
    path = _cache_path(error_type)

    # 读取现有历史
    history = []
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except (json.JSONDecodeError, IOError):
            history = []

    # 追加新记录
    entry = {
        'solution': fix_solution,
        'error_type': error_type,
        'timestamp': datetime.now().isoformat(),
    }
    history.append(entry)

    # 限制历史记录数量（最多 50 条）
    history = history[-50:]

    # 写回本地缓存
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

    # basic-memory 写入（当前环境不可用，降级到本地缓存已完成）
    # 简化说明：basic-memory 需 MCP 调用 | 已知上限：本模块无法直接写入 | 升级路径：宿主集成 MCP


# ==================== 8. 主函数 ====================

def auto_fix_error(error, source_json, html=None):
    """主函数：自动分析错误并尝试修复，最多重试3次。

    流程：历史方案优先 → 分析错误 → 生成修复 → 应用 → 验证 → 记录

    Args:
        error: 错误信息（dict 或 str）
        source_json: 源 JSON（str 或 dict）
        html: 可选的 HTML 内容（用于辅助修复）

    Returns:
        dict: {
            'success': bool,           # 是否修复成功
            'fixed_source': dict,      # 修复后的源
            'fixes_applied': list,     # 应用的修复列表
            'verify_result': dict,     # 验证结果
            'attempts': int,           # 尝试次数
            'remaining_errors': list,  # 剩余错误
            'fix_details': list,       # 修复详情列表（3.6）
        }
    """
    err = _parse_error(error)
    error_type = err['error_type'] or _infer_error_type(err['msg'])
    stage = err['stage']
    source = _normalize_source(source_json)

    # 1. 历史方案优先：加载历史修复方案作为参考
    history = load_fix_history(error_type)

    all_fixes = []
    all_fix_details = []  # 3.6: 结构化修复详情
    verify = {'status': 'unverifiable', 'detail': '未执行验证'}

    # 错误类型 → 修复函数列表
    fix_map = {
        # 自动修复类型
        'rule_parse': [fix_css_selector, fix_rule_syntax, fix_field_mapping],
        'css': [fix_css_selector, fix_rule_syntax],
        'url_empty': [fix_url_template],
        'network': [fix_url_template],
        'rule_empty': [fix_rule_syntax],
        'relative_url': [fix_url_template],
        'css_selector_empty': [fix_css_selector],
        'js_error': [fix_js_syntax],
        'http_403': [fix_header, fix_cf_bypass],
        'field_missing': [fix_field_mapping],
        'syntax_error': [fix_rule_syntax],
        # CF盾自动绕过（Cookie预热+UA增强+Referer添加）
        'cf_challenge': [fix_cf_bypass],
        # 网站改版重分析（获取HTML→分析DOM→生成新CSS选择器）
        'search_empty': [fix_website_revamp, fix_css_selector],
        # 需用户介入类型（不自动修复，仅返回建议）
        'need_login': [_make_manual_fixer('need_login')],
        'jar_crash': [_make_manual_fixer('jar_crash')],
        'jar_timeout': [_make_manual_fixer('jar_timeout')],
        'behavior_mismatch': [_make_manual_fixer('behavior_mismatch')],
    }
    fix_funcs = fix_map.get(
        error_type,
        [fix_css_selector, fix_rule_syntax, fix_field_mapping, fix_url_template]
    )

    # 需用户介入的错误类型：返回建议但不自动修复
    # cf_challenge 已改为自动修复（fix_cf_bypass），不再列入 manual_types
    manual_types = {'need_login', 'jar_crash', 'jar_timeout', 'behavior_mismatch'}
    if error_type in manual_types:
        manual_suggestions = []
        for fix_func in fix_funcs:
            _, _, manual = fix_func(err, source, html)
            manual_suggestions.extend(manual)
        return {
            'success': False,
            'fixed_source': source,
            'fixes_applied': [],
            'verify_result': {'status': 'manual', 'detail': '需用户介入，不自动修复'},
            'attempts': 0,
            'remaining_errors': manual_suggestions or [err['msg']],
            'fix_details': [{
                'fix_type': error_type,
                'stage': stage,
                'before': '',
                'after': '',
                'diff': '; '.join(manual_suggestions[:3]),
                'success': False,
            }],
        }

    attempt = 0
    source_before = json.dumps(source, ensure_ascii=False)  # 3.6: 修复前快照
    for attempt in range(1, 4):
        fixes_this_round = []

        # 2-3. 分析错误 + 生成修复
        for fix_func in fix_funcs:
            source_before_fix = json.dumps(source, ensure_ascii=False)
            fixed, fixes, _ = fix_func(err, source, html)
            if fixes:
                source_after_fix = json.dumps(fixed, ensure_ascii=False)
                # 3.6: 为每个修复生成 fix_detail
                for fix_desc in fixes:
                    all_fix_details.append({
                        'fix_type': error_type,
                        'stage': stage,
                        'before': source_before_fix[:200],
                        'after': source_after_fix[:200],
                        'diff': fix_desc,
                        'success': True,  # 应用成功（验证结果在 verify 中）
                    })
                source = fixed
                fixes_this_round.extend(fixes)

        if not fixes_this_round:
            # 无可修复项，停止重试
            break

        all_fixes.extend(fixes_this_round)

        # 4. 验证
        verify = verify_fix(source, stage)

        # 5. 记录
        for fix in fixes_this_round:
            record_fix_history(error_type, fix)

        # 验证通过或无法验证，结束重试
        if verify['status'] in ('passed', 'unverifiable'):
            break

        # 验证失败，更新错误信息用于下一轮
        err['msg'] = verify.get('detail', err['msg'])

    return {
        'success': verify['status'] == 'passed',
        'fixed_source': source,
        'fixes_applied': all_fixes,
        'verify_result': verify,
        'attempts': attempt,
        'remaining_errors': [] if verify['status'] == 'passed' else [err['msg']],
        'fix_details': all_fix_details,  # 3.6: 结构化修复详情
    }


if __name__ == '__main__':
    # 最小自检：1 正常用例 + 1 边界用例 + 1 异常用例
    print("auto_fixer.py 自检")
    print(f"basic-memory 可用: {_BASIC_MEMORY_AVAILABLE}")
    print(f"缓存目录: {_FIX_CACHE_DIR}")

    # 正常用例1：fix_css_selector 无HTML时不盲目修改（禁止驼峰转换/模糊匹配）
    s = {"ruleSearch": {"name": ".book-name@text"}}
    fixed, fixes, manual = fix_css_selector({'msg': '选择器未匹配'}, s)
    assert fixes == [], f"无HTML时不应修改选择器: {fixes}"
    assert manual, f"无HTML时应返回manual建议: {manual}"
    assert '.book-name' in fixed['ruleSearch']['name'], f"选择器不应被破坏: {fixed['ruleSearch']['name']}"

    # 正常用例2：fix_cf_bypass 生成loginUrl（普通URL，禁止@js:java.webView）
    s_cf = {"bookSourceUrl": "https://example.com", "searchUrl": "https://example.com/search?q={{key}}"}
    fixed_cf, fixes_cf, _ = fix_cf_bypass({'msg': 'CF挑战'}, s_cf)
    assert fixed_cf.get('loginUrl', '').startswith('http'), f"loginUrl应为普通URL(http开头): {fixed_cf.get('loginUrl')}"
    assert not fixed_cf.get('loginUrl', '').startswith('@js:'), f"loginUrl禁止用@js:java.webView形式: {fixed_cf.get('loginUrl')}"
    assert '<js>java.ajax' not in fixed_cf.get('searchUrl', ''), f"searchUrl不应含js块: {fixed_cf.get('searchUrl')}"
    assert 'loginCheckJs' not in fixed_cf, "不应设置loginCheckJs（陷阱#57）"

    # 正常用例3：fix_rule_syntax 补全后缀
    s2 = {"ruleBookInfo": {"name": "div.title", "bookUrl": "a.link"}}
    fixed2, fixes2, _ = fix_rule_syntax({'msg': '语法错误'}, s2)
    assert '@text' in fixed2['ruleBookInfo']['name'], f"@text 补全失败: {fixes2}"
    assert '@href' in fixed2['ruleBookInfo']['bookUrl'], f"@href 补全失败: {fixes2}"

    # 边界用例：空 source
    fixed3, fixes3, manual3 = fix_css_selector({'msg': ''}, {})
    assert fixes3 == [] and manual3, "空 source 应返回 manual"

    # 异常用例：fix_cf_bypass 无sourceUrl
    fixed4, fixes4, manual4 = fix_cf_bypass({'msg': 'CF'}, {"searchUrl": "test"})
    assert manual4, "无sourceUrl应返回manual建议"

    # 历史记录读写
    record_fix_history('_self_test', '自检方案')
    hist = load_fix_history('_self_test')
    assert hist and hist[-1]['solution'] == '自检方案', "历史记录读写失败"
    _cache_path('_self_test').unlink()  # 清理

    print("✅ 自检通过")
