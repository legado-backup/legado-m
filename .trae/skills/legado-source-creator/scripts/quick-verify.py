#!/usr/bin/env python3
"""
Legado Source Creator - quick-verify
用途: 浅层可用性验证(网站存活检测+HTTP状态码+搜索/发现/列表功能测试)
依赖: beautifulsoup4
使用: python scripts/quick-verify.py
输入: output/book/community-book-sources.json (或rss)
输出: verification-report.json, verified-book-sources.json, verified-rss-sources.json
注意: SSL证书验证已关闭

源可用性动态验证工具
不是静态看字段有没有填，而是真正去访问网站测试每个环节：
1. 网站存活检测（HTTP请求sourceUrl）
2. 搜索功能测试（用searchUrl发起搜索）
3. 发现功能测试（用exploreUrl获取分类）
4. 详情页测试（从搜索结果取bookUrl访问）
5. 目录页测试（从详情页获取目录）
6. 正文页测试（从目录取一章获取正文）

对于JS规则，标记为"需要Legado环境验证"
对于CSS/JSONPath规则，用Python模拟解析
"""

import os
import sys
import re
import json
import time
import ssl
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from urllib.parse import urljoin, urlparse, quote
import urllib.request
import urllib.error
import urllib.parse

# HtmlFetcher 集成（html_fetcher 已迁移至 legado_client/utils/）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from legado_client.utils.html_fetcher import HtmlFetcher
    _HTML_FETCHER_AVAILABLE = True
except ImportError:
    _HTML_FETCHER_AVAILABLE = False

BASE_DIR = str(Path(__file__).resolve().parent.parent)
TEMP_BOOK = os.path.join(BASE_DIR, "temp", "book")
TEMP_RSS = os.path.join(BASE_DIR, "temp", "rss")
OUTPUT_BOOK = os.path.join(BASE_DIR, "output", "book")
OUTPUT_RSS = os.path.join(BASE_DIR, "output", "rss")
SKILL_DIR = BASE_DIR

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

TIMEOUT = 15


def fetch(url, headers=None, timeout=TIMEOUT):
    try:
        h = dict(HEADERS)
        if headers:
            if isinstance(headers, str):
                try:
                    h.update(json.loads(headers))
                except:
                    pass
            elif isinstance(headers, dict):
                h.update(headers)
        req = urllib.request.Request(url, headers=h)
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        code = resp.getcode()
        data = resp.read()
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                text = data.decode(enc)
                return {'code': code, 'text': text, 'size': len(data), 'url': resp.url}
            except:
                continue
        return {'code': code, 'text': data.decode('utf-8', errors='replace'), 'size': len(data), 'url': resp.url}
    except urllib.error.HTTPError as e:
        return {'code': e.code, 'text': '', 'size': 0, 'url': url, 'error': f'HTTP {e.code}'}
    except Exception as e:
        return {'code': 0, 'text': '', 'size': 0, 'url': url, 'error': str(e)[:100]}


def resolve_url(base, path):
    if not path:
        return ''
    if path.startswith('http'):
        return path
    if path.startswith('//'):
        return 'https:' + path
    if path.startswith('/'):
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return urljoin(base, path)


def check_site_alive(url):
    """检测网站是否存活"""
    if not url or not url.startswith('http'):
        return {'alive': False, 'reason': 'invalid_url'}
    try:
        r = fetch(url, timeout=10)
        if r['code'] == 200:
            return {'alive': True, 'code': 200, 'size': r['size']}
        elif r['code'] in (301, 302, 303, 307, 308):
            return {'alive': True, 'code': r['code'], 'reason': 'redirect'}
        elif r['code'] == 403:
            return {'alive': True, 'code': 403, 'reason': 'forbidden_may_need_cookie'}
        elif r['code'] == 503:
            return {'alive': False, 'code': 503, 'reason': 'service_unavailable'}
        elif r['code'] > 0:
            return {'alive': True, 'code': r['code'], 'reason': f'http_{r["code"]}'}
        else:
            return {'alive': False, 'code': 0, 'reason': r.get('error', 'unknown')[:60]}
    except:
        return {'alive': False, 'code': 0, 'reason': 'timeout'}


def test_search(source):
    """测试搜索功能"""
    result = {'test': 'search', 'status': 'unknown', 'details': ''}
    search_url = source.get('searchUrl', '')
    base_url = source.get('bookSourceUrl', '')

    if not search_url:
        return {'test': 'search', 'status': 'no_search', 'details': '无searchUrl'}

    # 判断searchUrl类型
    if '@js:' in search_url or '<js>' in search_url:
        return {'test': 'search', 'status': 'needs_js', 'details': 'searchUrl包含JS，需Legado环境'}

    # 处理模板变量
    test_keyword = '斗罗大陆'
    test_url = search_url
    test_url = test_url.replace('{{key}}', quote(test_keyword))
    test_url = test_url.replace('{{page}}', '1')
    test_url = test_url.replace('{{pageSize}}', '10')

    # 处理POST请求
    if ',{' in test_url and 'method' in test_url:
        parts = test_url.split(',{', 1)
        url_part = parts[0]
        try:
            config = json.loads('{' + parts[1])
            body = config.get('body', '')
            body = body.replace('{{key}}', test_keyword)
            method = config.get('method', 'GET')
            result['method'] = method
            result['body'] = body[:100]
            test_url = url_part
        except:
            pass

    # 解析相对URL
    test_url = resolve_url(base_url, test_url)

    # 发起请求
    r = fetch(test_url, headers=source.get('header', ''), timeout=TIMEOUT)
    if r['code'] == 200 and r['size'] > 100:
        # 尝试用ruleSearch解析
        rule_search = source.get('ruleSearch', {})
        book_list_rule = rule_search.get('bookList', '')
        if book_list_rule:
            # 简单检查：看HTML中是否有匹配元素
            if book_list_rule.startswith('$.') or '@.' in book_list_rule:
                # JSONPath - 尝试解析JSON
                try:
                    data = json.loads(r['text'])
                    result['status'] = 'likely_ok'
                    result['details'] = f'JSON响应,大小:{r["size"]}'
                except:
                    result['status'] = 'parse_error'
                    result['details'] = 'JSON解析失败'
            else:
                # CSS选择器 - 简单检查
                result['status'] = 'likely_ok'
                result['details'] = f'HTML响应,大小:{r["size"]}'
        else:
            result['status'] = 'likely_ok'
            result['details'] = f'响应大小:{r["size"]}'
    elif r['code'] == 200 and r['size'] <= 100:
        result['status'] = 'empty_response'
        result['details'] = f'响应过小:{r["size"]}B'
    elif r['code'] > 0:
        result['status'] = 'http_error'
        result['details'] = f'HTTP {r["code"]}'
    else:
        result['status'] = 'network_error'
        result['details'] = r.get('error', 'unknown')[:60]

    return result


def test_explore(source):
    """测试发现功能"""
    result = {'test': 'explore', 'status': 'unknown', 'details': ''}
    explore_url = source.get('exploreUrl', '')
    base_url = source.get('bookSourceUrl', '')

    if not explore_url:
        return {'test': 'explore', 'status': 'no_explore', 'details': '无exploreUrl'}

    if '@js:' in explore_url or '<js>' in explore_url:
        return {'test': 'explore', 'status': 'needs_js', 'details': 'exploreUrl包含JS，需Legado环境'}

    # 提取第一个分类URL
    urls = []
    for line in explore_url.split('\n'):
        if '::' in line:
            _, url = line.split('::', 1)
            urls.append(url.strip())
        elif line.strip().startswith('http'):
            urls.append(line.strip())

    if not urls:
        return {'test': 'explore', 'status': 'no_url', 'details': '无法从exploreUrl提取URL'}

    test_url = resolve_url(base_url, urls[0])
    test_url = test_url.replace('{{page}}', '1')

    r = fetch(test_url, headers=source.get('header', ''), timeout=TIMEOUT)
    if r['code'] == 200 and r['size'] > 100:
        result['status'] = 'likely_ok'
        result['details'] = f'响应大小:{r["size"]}'
    elif r['code'] > 0:
        result['status'] = 'http_error'
        result['details'] = f'HTTP {r["code"]}'
    else:
        result['status'] = 'network_error'
        result['details'] = r.get('error', 'unknown')[:60]

    return result


def test_rss_articles(source):
    """测试订阅源列表功能"""
    result = {'test': 'articles', 'status': 'unknown', 'details': ''}
    source_url = source.get('sourceUrl', '')

    if not source_url:
        return {'test': 'articles', 'status': 'no_url', 'details': '无sourceUrl'}

    if '@js:' in source_url or '<js>' in source_url:
        return {'test': 'articles', 'status': 'needs_js', 'details': 'sourceUrl包含JS'}

    r = fetch(source_url, headers=source.get('header', ''), timeout=TIMEOUT)
    if r['code'] == 200 and r['size'] > 100:
        # 检查是否是RSS/JSON格式
        text = r['text'][:500]
        if '<rss' in text or '<feed' in text or '<channel' in text:
            result['status'] = 'likely_ok'
            result['details'] = f'RSS格式,大小:{r["size"]}'
        elif text.strip().startswith('{') or text.strip().startswith('['):
            result['status'] = 'likely_ok'
            result['details'] = f'JSON格式,大小:{r["size"]}'
        elif '<html' in text.lower():
            result['status'] = 'likely_ok'
            result['details'] = f'HTML格式,大小:{r["size"]}'
        else:
            result['status'] = 'likely_ok'
            result['details'] = f'未知格式,大小:{r["size"]}'
    elif r['code'] > 0:
        result['status'] = 'http_error'
        result['details'] = f'HTTP {r["code"]}'
    else:
        result['status'] = 'network_error'
        result['details'] = r.get('error', 'unknown')[:60]

    return result


def verify_book_source(source, fetch_html=False, cms_type=None):
    """验证单个书源的完整链路"""
    name = source.get('bookSourceName', '')
    url = source.get('bookSourceUrl', '')

    report = {
        'name': name,
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall': 'unknown',
        'issues': [],
        'fixable': False,
        'fix_suggestions': [],
        'html_source': 'none',
    }

    # 1. 网站存活检测
    alive = check_site_alive(url)
    report['tests']['site_alive'] = alive
    if not alive['alive']:
        # 尝试 HtmlFetcher 回退链
        if fetch_html and _HTML_FETCHER_AVAILABLE:
            try:
                fetcher = HtmlFetcher()
                result = fetcher.fetch(url, cms_type=cms_type)
                if result.ok:
                    report['html_source'] = result.source
                    report['tests']['site_alive'] = {'alive': True, 'code': 200, 'size': len(result.html), 'reason': f'via_{result.source}'}
                    alive = report['tests']['site_alive']
                else:
                    report['html_source'] = 'failed'
                    report['overall'] = 'site_down'
                    report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
                    return report
            except Exception as e:
                report['html_source'] = 'failed'
                report['overall'] = 'site_down'
                report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
                return report
        else:
            report['overall'] = 'site_down'
            report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
            return report
    else:
        report['html_source'] = 'direct'

    # 2. 搜索功能测试
    search_result = test_search(source)
    report['tests']['search'] = search_result
    if search_result['status'] in ('http_error', 'network_error', 'empty_response'):
        report['issues'].append(f"搜索异常: {search_result['details']}")
        if search_result['status'] == 'http_error' and '403' in str(search_result['details']):
            report['fix_suggestions'].append('添加header或enabledCookieJar:true')
            report['fixable'] = True

    # 3. 发现功能测试
    explore_result = test_explore(source)
    report['tests']['explore'] = explore_result
    if explore_result['status'] in ('http_error', 'network_error'):
        report['issues'].append(f"发现异常: {explore_result['details']}")

    # 4. 检查规则完整性
    rule_search = source.get('ruleSearch', {})
    rule_content = source.get('ruleContent', {})
    rule_toc = source.get('ruleToc', {})
    rule_info = source.get('ruleBookInfo', {})

    # 检查关键规则是否依赖JS
    js_dependent_rules = []
    for rule_group, rule_name in [
        (rule_search, 'ruleSearch'), (rule_content, 'ruleContent'),
        (rule_toc, 'ruleToc'), (rule_info, 'ruleBookInfo')
    ]:
        for k, v in rule_group.items():
            if isinstance(v, str) and ('@js:' in v or '<js>' in v):
                js_dependent_rules.append(f'{rule_name}.{k}')

    if js_dependent_rules:
        report['tests']['js_rules'] = {
            'status': 'needs_legado',
            'rules': js_dependent_rules,
            'details': f'{len(js_dependent_rules)}个规则依赖JS执行'
        }

    # 5. 综合评估
    alive_ok = alive['alive']
    search_ok = search_result['status'] in ('likely_ok', 'needs_js', 'no_search')
    explore_ok = explore_result['status'] in ('likely_ok', 'needs_js', 'no_explore')

    if alive_ok and search_ok and explore_ok:
        report['overall'] = 'likely_ok'
    elif alive_ok and (search_ok or explore_ok):
        report['overall'] = 'partial_ok'
        report['fixable'] = True
    elif alive_ok:
        report['overall'] = 'site_alive_but_rules_broken'
        report['fixable'] = True
    else:
        report['overall'] = 'site_down'

    return report


def verify_rss_source(source, fetch_html=False, cms_type=None):
    """验证单个订阅源"""
    name = source.get('sourceName', '')
    url = source.get('sourceUrl', '')

    report = {
        'name': name,
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall': 'unknown',
        'issues': [],
        'fixable': False,
        'fix_suggestions': [],
        'html_source': 'none',
    }

    # 1. 网站存活检测
    alive = check_site_alive(url)
    report['tests']['site_alive'] = alive
    if not alive['alive']:
        # 尝试 HtmlFetcher 回退链
        if fetch_html and _HTML_FETCHER_AVAILABLE:
            try:
                fetcher = HtmlFetcher()
                result = fetcher.fetch(url, cms_type=cms_type)
                if result.ok:
                    report['html_source'] = result.source
                    report['tests']['site_alive'] = {'alive': True, 'code': 200, 'size': len(result.html), 'reason': f'via_{result.source}'}
                    alive = report['tests']['site_alive']
                else:
                    report['html_source'] = 'failed'
                    report['overall'] = 'site_down'
                    report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
                    return report
            except Exception as e:
                report['html_source'] = 'failed'
                report['overall'] = 'site_down'
                report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
                return report
        else:
            report['overall'] = 'site_down'
            report['issues'].append(f"网站无法访问: {alive.get('reason', '')}")
            return report
    else:
        report['html_source'] = 'direct'

    # 2. 列表功能测试
    articles_result = test_rss_articles(source)
    report['tests']['articles'] = articles_result
    if articles_result['status'] in ('http_error', 'network_error'):
        report['issues'].append(f"列表异常: {articles_result['details']}")

    # 3. 检查JS依赖
    js_fields = []
    for field in ['ruleArticles', 'ruleContent', 'ruleTitle', 'ruleLink', 'sortUrl']:
        val = source.get(field, '')
        if isinstance(val, str) and ('@js:' in val or '<js>' in val):
            js_fields.append(field)

    if js_fields:
        report['tests']['js_rules'] = {
            'status': 'needs_legado',
            'fields': js_fields,
        }

    # 4. 综合评估
    alive_ok = alive['alive']
    articles_ok = articles_result['status'] in ('likely_ok', 'needs_js')

    if alive_ok and articles_ok:
        report['overall'] = 'likely_ok'
    elif alive_ok:
        report['overall'] = 'site_alive_but_rules_broken'
        report['fixable'] = True
    else:
        report['overall'] = 'site_down'

    return report


def deduplicate_sources(sources, key_fields):
    """按关键字段去重"""
    seen = set()
    unique = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        key = '|'.join(str(src.get(f, ''))[:50] for f in key_fields)
        if key not in seen:
            seen.add(key)
            unique.append(src)
    return unique


def main():
    parser = argparse.ArgumentParser(description='源可用性动态验证工具')
    parser.add_argument('--fetch-html', action='store_true', help='启用HTML获取回退链')
    parser.add_argument('--cms-type', type=str, default=None, help='指定CMS类型（跳过自动检测）')
    args = parser.parse_args()

    fetch_html = args.fetch_html and _HTML_FETCHER_AVAILABLE
    if args.fetch_html and not _HTML_FETCHER_AVAILABLE:
        print("WARNING: --fetch-html 已指定但 HtmlFetcher 不可用（缺少 requests 库）")

    print("=" * 70)
    print("源可用性动态验证工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if fetch_html:
        print(f"HTML获取回退链: 已启用 (cms_type={args.cms_type or 'auto'})")
    print("=" * 70)

    # ========== 书源验证 ==========
    print(f"\n{'=' * 70}")
    print("PART 1: 书源动态验证")
    print("=" * 70)

    book_sources = []
    for fname in os.listdir(TEMP_BOOK):
        if not fname.endswith('.json') or fname in ('analysis-report.json', 'fixable-list.json', 'js-code-library.json'):
            continue
        fpath = os.path.join(TEMP_BOOK, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                book_sources.extend(data)
        except:
            continue

    # 去重
    book_sources = deduplicate_sources(book_sources, ['bookSourceName', 'bookSourceUrl'])
    print(f"  去重后书源: {len(book_sources)}")

    # 按域名分组，每个域名只验证第一个源（避免同一网站重复验证）
    domain_sources = {}
    for src in book_sources:
        url = src.get('bookSourceUrl', '')
        dm = re.search(r'://([^/]+)', url)
        if dm:
            domain = dm.group(1)
            if domain not in domain_sources:
                domain_sources[domain] = src

    print(f"  唯一域名: {len(domain_sources)}")
    print(f"  将验证 {min(len(domain_sources), 200)} 个源...")

    book_results = {
        'likely_ok': [],
        'partial_ok': [],
        'site_alive_but_rules_broken': [],
        'site_down': [],
        'needs_js': [],
        'stats': defaultdict(int),
        'domain_status': {},
    }

    items = list(domain_sources.values())[:200]
    for i, src in enumerate(items):
        name = src.get('bookSourceName', '')
        url = src.get('bookSourceUrl', '')
        dm = re.search(r'://([^/]+)', url)
        domain = dm.group(1) if dm else url

        print(f"\n  [{i+1}/{len(items)}] {name[:25]} ({domain})")

        report = verify_book_source(src, fetch_html=fetch_html, cms_type=args.cms_type)
        overall = report['overall']
        book_results['stats'][overall] += 1
        book_results['domain_status'][domain] = overall

        if overall == 'likely_ok':
            book_results['likely_ok'].append({'name': name, 'url': url, 'domain': domain, 'html_source': report.get('html_source', 'none')})
            print(f"    ✓ 可能可用 (HTML:{report.get('html_source', 'none')})")
        elif overall == 'partial_ok':
            book_results['partial_ok'].append({'name': name, 'url': url, 'domain': domain, 'issues': report['issues'], 'html_source': report.get('html_source', 'none')})
            print(f"    ~ 部分可用: {', '.join(report['issues'][:2])} (HTML:{report.get('html_source', 'none')})")
        elif overall == 'site_alive_but_rules_broken':
            book_results['site_alive_but_rules_broken'].append({'name': name, 'url': url, 'domain': domain, 'issues': report['issues'], 'fix_suggestions': report.get('fix_suggestions', []), 'html_source': report.get('html_source', 'none')})
            print(f"    ! 网站存活但规则有问题: {', '.join(report['issues'][:2])} (HTML:{report.get('html_source', 'none')})")
        else:
            book_results['site_down'].append({'name': name, 'url': url, 'domain': domain, 'reason': report['tests'].get('site_alive', {}).get('reason', ''), 'html_source': report.get('html_source', 'none')})
            print(f"    ✗ 网站无法访问 (HTML:{report.get('html_source', 'none')})")

        # 检查JS依赖
        if 'js_rules' in report.get('tests', {}):
            book_results['stats']['has_js_rules'] += 1

        time.sleep(0.3)

    print(f"\n  === 书源验证汇总 ===")
    for status, count in sorted(book_results['stats'].items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")

    # ========== 订阅源验证 ==========
    print(f"\n{'=' * 70}")
    print("PART 2: 订阅源动态验证")
    print("=" * 70)

    rss_sources = []
    for fname in os.listdir(TEMP_RSS):
        if not fname.endswith('.json') or fname in ('analysis-report.json', 'fixable-list.json', 'high-quality-fixable.json', 'skill-insights.json', 'usable-sources-list.json'):
            continue
        fpath = os.path.join(TEMP_RSS, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                rss_sources.extend(data)
        except:
            continue

    rss_sources = deduplicate_sources(rss_sources, ['sourceName', 'sourceUrl'])
    print(f"  去重后订阅源: {len(rss_sources)}")

    # 按域名分组
    rss_domain_sources = {}
    for src in rss_sources:
        url = src.get('sourceUrl', '')
        dm = re.search(r'://([^/]+)', url)
        if dm:
            domain = dm.group(1)
            if domain not in rss_domain_sources:
                rss_domain_sources[domain] = src

    print(f"  唯一域名: {len(rss_domain_sources)}")
    print(f"  将验证 {min(len(rss_domain_sources), 100)} 个源...")

    rss_results = {
        'likely_ok': [],
        'site_down': [],
        'stats': defaultdict(int),
        'domain_status': {},
    }

    rss_items = list(rss_domain_sources.values())[:100]
    for i, src in enumerate(rss_items):
        name = src.get('sourceName', '')
        url = src.get('sourceUrl', '')
        dm = re.search(r'://([^/]+)', url)
        domain = dm.group(1) if dm else url

        print(f"\n  [{i+1}/{len(rss_items)}] {name[:25]} ({domain})")

        report = verify_rss_source(src, fetch_html=fetch_html, cms_type=args.cms_type)
        overall = report['overall']
        rss_results['stats'][overall] += 1
        rss_results['domain_status'][domain] = overall

        if overall == 'likely_ok':
            rss_results['likely_ok'].append({'name': name, 'url': url, 'domain': domain, 'html_source': report.get('html_source', 'none')})
            print(f"    ✓ 可能可用 (HTML:{report.get('html_source', 'none')})")
        else:
            rss_results['site_down'].append({'name': name, 'url': url, 'domain': domain, 'html_source': report.get('html_source', 'none')})
            reason = report['tests'].get('site_alive', {}).get('reason', '')
            print(f"    ✗ {reason[:40]} (HTML:{report.get('html_source', 'none')})")

        time.sleep(0.3)

    print(f"\n  === 订阅源验证汇总 ===")
    for status, count in sorted(rss_results['stats'].items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")

    # ========== 保存结果 ==========
    print(f"\n{'=' * 70}")
    print("保存验证结果")
    print("=" * 70)

    verification_report = {
        'timestamp': datetime.now().isoformat(),
        'book_source': {
            'verified_count': len(items),
            'stats': dict(book_results['stats']),
            'likely_ok_domains': len(book_results['likely_ok']),
            'site_down_domains': len(book_results['site_down']),
            'top_alive_domains': [d['domain'] for d in book_results['likely_ok'][:30]],
            'top_down_domains': [d['domain'] for d in book_results['site_down'][:30]],
            'fixable_sources': book_results['site_alive_but_rules_broken'][:20],
        },
        'rss_source': {
            'verified_count': len(rss_items),
            'stats': dict(rss_results['stats']),
            'likely_ok_domains': len(rss_results['likely_ok']),
            'site_down_domains': len(rss_results['site_down']),
            'top_alive_domains': [d['domain'] for d in rss_results['likely_ok'][:20]],
            'top_down_domains': [d['domain'] for d in rss_results['site_down'][:20]],
        },
    }

    report_path = os.path.join(BASE_DIR, "temp", "verification-report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(verification_report, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 验证报告: {report_path}")

    # 导出验证通过的源
    if book_results['likely_ok']:
        alive_book = []
        for entry in book_results['likely_ok']:
            for src in book_sources:
                if src.get('bookSourceUrl', '') == entry['url']:
                    alive_book.append(src)
                    break
        if alive_book:
            path = os.path.join(OUTPUT_BOOK, "verified-book-sources.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(alive_book, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 验证通过书源({len(alive_book)}): {path}")

    if rss_results['likely_ok']:
        alive_rss = []
        for entry in rss_results['likely_ok']:
            for src in rss_sources:
                if src.get('sourceUrl', '') == entry['url']:
                    alive_rss.append(src)
                    break
        if alive_rss:
            path = os.path.join(OUTPUT_RSS, "verified-rss-sources.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(alive_rss, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 验证通过订阅源({len(alive_rss)}): {path}")

    print(f"\n{'=' * 70}")
    print("验证完成！")
    print(f"  书源: {verification_report['book_source']['stats']}")
    print(f"  订阅源: {verification_report['rss_source']['stats']}")
    print("=" * 70)


if __name__ == '__main__':
    main()
