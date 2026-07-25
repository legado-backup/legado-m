#!/usr/bin/env python3
"""固化网站结构分析脚本 - 支持 JVM/Python 双模式"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def _init_jvm_client(jar_path=None):
    """初始化 JVM 客户端（使用共享模块）"""
    try:
        tools_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from legado_client.utils.jvm_helpers import init_jvm_client
        return init_jvm_client(jar_path=jar_path)
    except ImportError:
        # 降级：jvm_helpers 不可用时使用 legado_client 包内的 rule_engine_client
        try:
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from legado_client.client.rule_engine_client import RuleEngineClient
            client = RuleEngineClient(jar_path=jar_path)
            client.start()
            return client, True
        except Exception as e:
            print(f"WARNING: JVM 不可用，降级到纯 Python 分析: {e}", file=sys.stderr)
            return None, False


def detect_site_type(html, url):
    """检测网站类型"""
    lower = html.lower()
    if 'wordpress' in lower or 'wp-content' in lower:
        if 'mirages' in lower or 'loadbanner' in lower:
            return "WordPress+Mirages"
        return "WordPress"
    if 'discuz' in lower or 'discuz!' in lower:
        return "Discuz"
    if 'phpwind' in lower:
        return "PHPWind"
    if '苹果cms' in lower or 'maccms' in lower or 'maccms' in lower:
        return "苹果CMS"
    return "Unknown"

def detect_encoding(resp, html):
    """检测编码"""
    ct = resp.headers.get('Content-Type', '')
    if 'charset=' in ct:
        return ct.split('charset=')[-1].strip().split(';')[0]
    match = re.search(r'charset=["\']?([^"\';\s>]+)', html[:2000], re.I)
    if match:
        return match.group(1)
    return "UTF-8"

def detect_encryption(html):
    """检测加密特征"""
    features = []
    if 'loadBannerDirect' in html:
        features.append("Mirages图片加密(loadBannerDirect)")
    if 'data-xkrkllgl' in html:
        features.append("Mirages详情页加密(data-xkrkllgl)")
    if 'decryptImage' in html:
        features.append("JS解密函数(decryptImage)")
    if re.search(r'AES|DES|encrypt|decrypt|CryptoJS', html, re.I):
        features.append("加密JS代码")
    return features

def detect_pjax(html):
    """检测 PJAX/SPA"""
    if 'data-pjax' in html or 'pjax-container' in html:
        return True
    if re.search(r'__NUXT__|__NEXT_DATA__|window\.__INITIAL_STATE__', html):
        return True
    return False

def detect_js_features_jvm(client, html):
    """JVM 路径 - 使用 Rhino 执行 JS 代码检测加密特征"""
    js_features = []

    # 检测 CryptoJS 是否可执行
    if 'CryptoJS' in html:
        test_js = """
        try {
            var hasCryptoJS = typeof CryptoJS !== 'undefined';
            hasCryptoJS ? 'CryptoJS_available' : 'CryptoJS_not_found';
        } catch(e) {
            'CryptoJS_error:' + e.message;
        }
        """
        result = client.eval_js(test_js, context=html[:5000])
        if result.get("ok"):
            js_features.append(f"JS引擎检测: {result.get('result', 'unknown')}")

    # 检测 loadBannerDirect 函数签名
    if 'loadBannerDirect' in html:
        test_js = """
        try {
            var fn = typeof loadBannerDirect;
            fn === 'function' ? 'loadBannerDirect_is_function' : 'loadBannerDirect_type:' + fn;
        } catch(e) {
            'loadBannerDirect_error:' + e.message;
        }
        """
        result = client.eval_js(test_js, context=html[:5000])
        if result.get("ok"):
            js_features.append(f"Mirages函数检测: {result.get('result', 'unknown')}")

    return js_features


# ── 网站结构智能分析函数 ──────────────────────────────────

# CMS 特征库: (cms名称, [特征正则列表])
_CMS_FEATURES = {
    'WordPress': [
        r'<meta[^>]+generator[^>]+wordpress',
        r'wp-content/',
        r'wp-includes/',
        r'wp-json/',
    ],
    'Typecho': [
        r'<meta[^>]+generator[^>]+typecho',
        r'/usr/themes/',
        r'/usr/plugins/',
    ],
    'Z-Blog': [
        r'<meta[^>]+generator[^>]+z-blog',
        r'zb_users/',
        r'zblogphp',
    ],
    '织梦DedeCMS': [
        r'<meta[^>]+generator[^>]+dedecms',
        r'/dede/',
        r'dedeajax',
    ],
    '帝国EmpireCMS': [
        r'<meta[^>]+generator[^>]+empire',
        r'/e/action/',
        r'empirecms',
    ],
    'PHPCMS': [
        r'<meta[^>]+generator[^>]+phpcms',
        r'/phpcms/',
    ],
    '苹果CMS': [
        r'<meta[^>]+generator[^>]+maccms',
        r'maccms',
        r'苹果cms',
        r'/static/js/playerconfig',
    ],
    'Discuz': [
        r'<meta[^>]+generator[^>]+discuz',
        r'discuz!',
        r'forum\.php\?mod=',
    ],
    'PHPWind': [
        r'<meta[^>]+generator[^>]+phpwind',
        r'phpwind',
    ],
}


def identify_cms(html):
    """识别 CMS 类型

    通过 meta generator 标签、特征 class、特征 JS 路径识别。
    支持: WordPress/Typecho/Z-Blog/织梦/帝国/PHPCMS/苹果CMS/Discuz/PHPWind

    Returns:
        dict: {cms, confidence, evidence}
    """
    lower = html.lower()

    # 优先检查 meta generator 标签
    gen_match = re.search(
        r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.I
    )
    if gen_match:
        gen_content = gen_match.group(1).lower()
        # meta generator 的 content 值通常直接包含 CMS 名称
        _GEN_KEYWORDS = {
            'wordpress': 'WordPress',
            'typecho': 'Typecho',
            'z-blog': 'Z-Blog',
            'dedecms': '织梦DedeCMS',
            'empirecms': '帝国EmpireCMS',
            'phpcms': 'PHPCMS',
            'maccms': '苹果CMS',
            'discuz': 'Discuz',
            'phpwind': 'PHPWind',
        }
        for keyword, cms_name in _GEN_KEYWORDS.items():
            if keyword in gen_content:
                return {
                    'cms': cms_name,
                    'confidence': 'high',
                    'evidence': f'meta generator: {gen_match.group(1)}',
                }

    # 特征匹配
    for cms, patterns in _CMS_FEATURES.items():
        hits = [p for p in patterns if re.search(p, lower)]
        if hits:
            return {
                'cms': cms,
                'confidence': 'medium' if len(hits) >= 2 else 'low',
                'evidence': hits,
            }

    return {'cms': 'Unknown', 'confidence': 'none', 'evidence': []}


def analyze_list_page(html):
    """分析列表页HTML结构，推荐 bookList 选择器

    检测 article/div/ul+li/table 等容器结构，推荐出现次数最多的选择器。

    Returns:
        dict: {page_type, candidates, recommended}
    """
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []

    # 1. article 标签
    articles = soup.find_all('article')
    if articles:
        candidates.append({
            'selector': 'article',
            'type': 'article',
            'count': len(articles),
            'confidence': 'high',
        })

    # 2. 带列表相关 class 的 div
    list_kw = re.compile(r'item|list|book|card|post|entry|article|novel|chapter', re.I)
    seen_classes = set()
    for div in soup.find_all('div', class_=True):
        for cls in div.get('class', []):
            if cls and list_kw.search(cls) and cls not in seen_classes:
                count = len(soup.find_all('div', class_=cls))
                if count >= 2:
                    seen_classes.add(cls)
                    candidates.append({
                        'selector': f'div.{cls}',
                        'type': 'div',
                        'count': count,
                        'confidence': 'high' if count >= 3 else 'medium',
                    })

    # 3. ul > li 结构
    for ul in soup.find_all('ul'):
        lis = ul.find_all('li', recursive=False)
        if len(lis) >= 3:
            cls = ul.get('class', [''])[0] if ul.get('class') else ''
            selector = f'ul.{cls} li' if cls else 'ul li'
            candidates.append({
                'selector': selector,
                'type': 'ul_li',
                'count': len(lis),
                'confidence': 'medium',
            })

    # 4. table > tr 结构
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) >= 3:
            candidates.append({
                'selector': 'table tr',
                'type': 'table',
                'count': len(rows),
                'confidence': 'medium',
            })

    # 排序: confidence > count
    conf_order = {'high': 3, 'medium': 2, 'low': 1}
    candidates.sort(
        key=lambda x: (conf_order.get(x['confidence'], 0), x['count']),
        reverse=True,
    )

    return {
        'page_type': 'list',
        'candidates': candidates,
        'recommended': candidates[0] if candidates else None,
    }


def analyze_detail_page(html):
    """分析详情页结构，推荐书名/作者/简介选择器

    Returns:
        dict: {page_type, title_selectors, author_selectors, intro_selectors}
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 书名选择器候选
    title_selectors = []
    for tag in ['h1', 'h2']:
        el = soup.find(tag)
        if el and el.get_text(strip=True):
            title_selectors.append({'selector': tag, 'confidence': 'high'})
    for el in soup.find_all(class_=re.compile(r'title|bookname|book-name|booktitle', re.I)):
        cls = el.get('class', [''])[0]
        if cls:
            title_selectors.append({'selector': f'.{cls}', 'confidence': 'medium'})

    # 作者选择器候选
    author_selectors = []
    for el in soup.find_all(class_=re.compile(r'author|writer', re.I)):
        cls = el.get('class', [''])[0]
        if cls:
            author_selectors.append({'selector': f'.{cls}', 'confidence': 'medium'})

    # 简介选择器候选
    intro_selectors = []
    for el in soup.find_all(class_=re.compile(r'intro|desc|summary|description|info', re.I)):
        cls = el.get('class', [''])[0]
        if cls:
            intro_selectors.append({'selector': f'.{cls}', 'confidence': 'medium'})

    return {
        'page_type': 'detail',
        'title_selectors': title_selectors[:3],
        'author_selectors': author_selectors[:3],
        'intro_selectors': intro_selectors[:3],
    }


def analyze_toc_page(html):
    """分析目录页结构，推荐章节选择器

    Returns:
        dict: {page_type, link_candidates, recommended}
    """
    soup = BeautifulSoup(html, 'html.parser')
    link_candidates = []

    # ul > a 结构
    for ul in soup.find_all('ul'):
        links = ul.find_all('a')
        if len(links) >= 5:
            cls = ul.get('class', [''])[0] if ul.get('class') else ''
            selector = f'ul.{cls} a' if cls else 'ul a'
            link_candidates.append({
                'selector': selector,
                'count': len(links),
                'confidence': 'high' if len(links) >= 10 else 'medium',
            })

    # dd > a 结构（常见于小说站）
    dd_links = soup.find_all('dd')
    if len(dd_links) >= 5:
        link_candidates.append({
            'selector': 'dd a',
            'count': len(dd_links),
            'confidence': 'medium',
        })

    # 带章节相关 class 的元素
    for el in soup.find_all(class_=re.compile(r'chapter|catalog|list', re.I)):
        cls = el.get('class', [''])[0]
        links = el.find_all('a')
        if len(links) >= 5:
            link_candidates.append({
                'selector': f'.{cls} a',
                'count': len(links),
                'confidence': 'high',
            })

    link_candidates.sort(
        key=lambda x: (x['confidence'] == 'high', x['count']),
        reverse=True,
    )

    return {
        'page_type': 'toc',
        'link_candidates': link_candidates,
        'recommended': link_candidates[0] if link_candidates else None,
    }


def analyze_content_page(html):
    """分析正文页结构，推荐正文选择器

    Returns:
        dict: {page_type, content_candidates, recommended}
    """
    soup = BeautifulSoup(html, 'html.parser')
    content_candidates = []

    # id 选择器
    for id_name in ['content', 'chaptercontent', 'booktxt', 'txt', 'nr1', 'nr', 'acontent']:
        el = soup.find(id=id_name)
        if el:
            text_len = len(el.get_text(strip=True))
            if text_len > 100:
                content_candidates.append({
                    'selector': f'#{id_name}',
                    'text_length': text_len,
                    'confidence': 'high',
                })

    # class 选择器
    for el in soup.find_all(class_=re.compile(r'content|read|text|chapter|novel|article-body', re.I)):
        cls = el.get('class', [''])[0]
        if not cls:
            continue
        text_len = len(el.get_text(strip=True))
        if text_len > 100:
            content_candidates.append({
                'selector': f'.{cls}',
                'text_length': text_len,
                'confidence': 'high' if text_len > 500 else 'medium',
            })

    content_candidates.sort(
        key=lambda x: (x['confidence'] == 'high', x['text_length']),
        reverse=True,
    )

    return {
        'page_type': 'content',
        'content_candidates': content_candidates[:5],
        'recommended': content_candidates[0] if content_candidates else None,
    }


def generate_rule_suggestions(template, list_page=None, detail_page=None,
                               toc_page=None, content_page=None):
    """生成规则建议清单

    Args:
        template: 规则模板 dict（含 bookList/bookName/author/intro 等字段）
        list_page/detail_page/toc_page/content_page: 各页面 HTML

    Returns:
        dict: 规则建议
    """
    suggestions = dict(template) if template else {}

    if list_page:
        list_result = analyze_list_page(list_page)
        if list_result['recommended']:
            suggestions['bookList'] = list_result['recommended']['selector']

    if detail_page:
        detail_result = analyze_detail_page(detail_page)
        if detail_result['title_selectors']:
            suggestions['name'] = detail_result['title_selectors'][0]['selector']
        if detail_result['author_selectors']:
            suggestions['author'] = detail_result['author_selectors'][0]['selector']
        if detail_result['intro_selectors']:
            suggestions['intro'] = detail_result['intro_selectors'][0]['selector']

    if toc_page:
        toc_result = analyze_toc_page(toc_page)
        if toc_result['recommended']:
            suggestions['chapterList'] = toc_result['recommended']['selector']

    if content_page:
        content_result = analyze_content_page(content_page)
        if content_result['recommended']:
            suggestions['content'] = content_result['recommended']['selector']

    return suggestions


def identify_pagination(html):
    """识别分页结构（下一页/页码/无限滚动）

    Returns:
        dict: {has_pagination, next_page_selector, page_number_selector, is_infinite_scroll}
    """
    soup = BeautifulSoup(html, 'html.parser')

    result = {
        'has_pagination': False,
        'next_page_selector': None,
        'page_number_selector': None,
        'is_infinite_scroll': False,
    }

    # 下一页：文本匹配
    for a in soup.find_all('a'):
        text = a.get_text(strip=True)
        if re.search(r'下一页|next\s*page|next\s*›|›|»|>>', text, re.I):
            cls = a.get('class', [''])[0] if a.get('class') else ''
            if cls:
                result['next_page_selector'] = f'a.{cls}'
            else:
                result['next_page_selector'] = f'a:contains({text})'
            result['has_pagination'] = True
            break

    # rel=next
    if not result['next_page_selector']:
        rel_next = soup.find('a', rel='next')
        if rel_next:
            cls = rel_next.get('class', [''])[0] if rel_next.get('class') else ''
            result['next_page_selector'] = f'a.{cls}' if cls else 'a[rel=next]'
            result['has_pagination'] = True

    # .next class
    if not result['next_page_selector']:
        next_el = soup.find(class_=re.compile(r'^next$', re.I))
        if next_el and next_el.name == 'a':
            cls = next_el.get('class', [''])[0]
            result['next_page_selector'] = f'a.{cls}'
            result['has_pagination'] = True

    # 页码
    page_el = soup.find(class_=re.compile(r'page|pagination|pager', re.I))
    if page_el:
        cls = page_el.get('class', [''])[0]
        result['page_number_selector'] = f'.{cls} a'
        result['has_pagination'] = True

    # 无限滚动
    if re.search(r'infinite.scroll|data-infinite|waypoint|autoload', html, re.I):
        result['is_infinite_scroll'] = True
        result['has_pagination'] = True

    return result


def identify_anti_crawl(html, response=None):
    """识别反爬策略（频率限制/IP封禁/UA检测/Referer检测等）

    Args:
        html: HTML 文本
        response: 可选，requests.Response 对象

    Returns:
        dict: {has_anti_crawl, strategies}
    """
    result = {
        'has_anti_crawl': False,
        'strategies': [],
    }

    lower = html.lower() if html else ''

    # Cloudflare
    if re.search(r'cf-browser-verification|cf_mitigated|__cf_bm|cdn-cgi/challenge|cf-challenge|just a moment|cf-ray', lower):
        result['strategies'].append('cloudflare')
        result['has_anti_crawl'] = True

    # 验证码
    if re.search(r'captcha|验证码|geetest|极验|recaptcha|hcaptcha|滑块', lower):
        result['strategies'].append('captcha')
        result['has_anti_crawl'] = True

    # 登录要求
    if html and re.search(r'<input[^>]+type=["\']password["\']', html):
        result['strategies'].append('login_required')
        result['has_anti_crawl'] = True

    # UA 检测
    if re.search(r'navigator\.useragent|user-agent.*check|禁止.*访问|block.*access', lower):
        result['strategies'].append('ua_check')
        result['has_anti_crawl'] = True

    # Referer 检测
    if re.search(r'document\.referrer|referer.*check|防盗链', lower):
        result['strategies'].append('referer_check')
        result['has_anti_crawl'] = True

    # 基于 response 的检测
    if response:
        status = getattr(response, 'status_code', None)
        if status == 429:
            result['strategies'].append('rate_limit')
            result['has_anti_crawl'] = True
        elif status == 403:
            result['strategies'].append('ip_ban')
            result['has_anti_crawl'] = True
        headers = getattr(response, 'headers', {})
        retry_after = headers.get('Retry-After') if headers else None
        if retry_after:
            result['strategies'].append(f'rate_limit(retry_after={retry_after})')
            result['has_anti_crawl'] = True

    return result


def analyze_site(url):
    """主函数：整合所有分析，输出完整规则建议

    Args:
        url: 目标网站 URL

    Returns:
        dict: 完整分析报告
    """
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else ""

    return {
        'ok': True,
        'url': url,
        'title': title,
        'cms': identify_cms(html),
        'list_page': analyze_list_page(html),
        'pagination': identify_pagination(html),
        'anti_crawl': identify_anti_crawl(html, resp),
        'encryption': detect_encryption(html),
        'is_pjax_spa': detect_pjax(html),
    }


def detect_site_structure_change(url, current_html):
    """对比历史分析结果，检测网站结构是否变化

    历史结果缓存在 ~/.legado_skill_cache/ 目录下。

    Args:
        url: 目标网站 URL
        current_html: 当前 HTML

    Returns:
        dict: {changed, changes, previous, current}
    """
    cache_dir = Path.home() / ".legado_skill_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    cache_path = cache_dir / f"site_{url_hash}.json"

    # 当前分析
    soup = BeautifulSoup(current_html, 'html.parser')
    title = soup.title.string.strip() if soup.title else None
    list_result = analyze_list_page(current_html)
    current = {
        'cms': identify_cms(current_html).get('cms'),
        'list_selector': list_result['recommended']['selector'] if list_result['recommended'] else None,
        'pagination': identify_pagination(current_html).get('has_pagination'),
        'title': title,
    }

    # 读取历史
    previous = None
    if cache_path.exists():
        try:
            previous = json.loads(cache_path.read_text(encoding='utf-8'))
        except Exception:
            previous = None

    # 对比
    changes = []
    if previous:
        for key in current:
            if current[key] != previous.get(key):
                changes.append({
                    'field': key,
                    'previous': previous.get(key),
                    'current': current[key],
                })
    else:
        changes.append({'field': 'all', 'previous': None, 'current': '首次分析'})

    # 保存当前结果
    cache_path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    return {
        'changed': len(changes) > 0,
        'changes': changes,
        'previous': previous,
        'current': current,
    }


def main():
    parser = argparse.ArgumentParser(description="Legado 网站结构分析工具")
    parser.add_argument("--url", required=True, help="目标 URL")
    parser.add_argument("--depth", type=int, default=1, help="分析深度")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'), default=True,
                        help="使用 JVM 分析 (默认 True，自动检测可用性)")
    parser.add_argument("--jar-path", default=None,
                        help="RuleEngineServer JAR 路径 (默认: 自动搜索)")
    args = parser.parse_args()

    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36"}

    # JVM 客户端初始化
    jvm_client = None
    jvm_available = False
    if args.jvm:
        jar_path = getattr(args, 'jar_path', None)
        jvm_client, jvm_available = _init_jvm_client(jar_path=jar_path)

    try:
        resp = requests.get(args.url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        soup = BeautifulSoup(html, 'html.parser')
        site_type = detect_site_type(html, args.url)
        encoding = detect_encoding(resp, html)
        encryption = detect_encryption(html)
        is_pjax = detect_pjax(html)

        # 提取基本信息
        title = soup.title.string.strip() if soup.title else ""
        articles = soup.select('article')
        links = soup.select('a[href]')

        # JVM 增强：JS 引擎检测
        js_features = []
        if jvm_available:
            js_features = detect_js_features_jvm(jvm_client, html)
            encryption.extend(js_features)

        analyze_method = "JVM+Python" if jvm_available else "Python"

        result = {
            "ok": True,
            "url": args.url,
            "status_code": resp.status_code,
            "site_type": site_type,
            "encoding": encoding,
            "title": title,
            "html_length": len(html),
            "article_count": len(articles),
            "link_count": len(links),
            "encryption_features": encryption,
            "is_pjax_spa": is_pjax,
            "content_completeness": "完整" if len(articles) > 0 else "可能不完整(需WebView)",
            "analyze_method": analyze_method,
            "confidence": "high" if jvm_available else "medium"
        }

        if args.output == "text":
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": str(e),
            "analyze_method": "JVM+Python" if jvm_available else "Python"
        }, ensure_ascii=False))
        sys.exit(1)
    finally:
        if jvm_client:
            jvm_client.shutdown()

if __name__ == "__main__":
    main()
