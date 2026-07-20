#!/usr/bin/env python3
r"""v5_5_fix_cronet_mismatch.py — V5.5 用真机Curl模拟Cronet行为修复19个失败源

核心认知（V5.5 修正）：
- Cronet 是网络库（QUIC+HTTP2+Brotli），不执行 JavaScript
- PC Playwright 默认执行 JS，真机 Cronet 不执行 → 同一 URL 返回不同 DOM
- PC Playwright 禁用JS后无法访问这些站点（网络/反爬问题）
- 真机本身有 curl 命令，可以用 curl 拿到与 Cronet 相同的原始HTML（不执行JS）
- 用 ADB shell 在真机上 curl + ADB pull 到 PC + BS4 分析

修复4类失败源（共19个，idx 3双重失败）：
1. list_empty (11个 idx 1,4,5,6,7,12,14,15,16,18,20)
2. content_parse_failed (5个 idx 2,3,11,13,19)
3. malformed_url (2个 idx 3,10)
4. ruleSearchArticle 不匹配 (2个 idx 9,17)

输出安全规范：禁止输出源名称/URL/cookie，全部用编号(源[idx])。
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

sys.stdout.reconfigure(encoding='utf-8')

from bs4 import BeautifulSoup

# === 配置 ===
CRONET_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PROJECT_ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
V54_JSON = PROJECT_ROOT / "output/rss/optimized_v5_4_final.json"
V55_JSON = PROJECT_ROOT / "output/rss/optimized_v5_5_final.json"
V55_FIX_RESULT = PROJECT_ROOT / "output/rss/v5_5_fix_result.json"
HTML_DIR = PROJECT_ROOT / "output/rss/v5_5_html"
HTML_DIR.mkdir(parents=True, exist_ok=True)

# 失败源分类
LIST_EMPTY_IDX = [1, 4, 5, 6, 7, 12, 14, 15, 16, 18, 20]
CONTENT_FAIL_IDX = [2, 3, 11, 13, 19]
MALFORMED_URL_IDX = [3, 10]
SEARCH_RULE_FAIL_IDX = [9, 17]


def adb_shell(cmd_str, timeout=60):
    cmd = [ADB, '-s', HOST, 'shell', cmd_str]
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def adb(*args, timeout=60):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def fetch_html_via_device(url, idx, label='list'):
    """通过真机curl获取HTML（模拟Cronet行为）"""
    if not url or not url.startswith('http'):
        return None, 'invalid_url'
    
    remote_path = f'/sdcard/_v55_html_{idx}_{label}.html'
    # 用 curl 拿HTML，设置 Cronet UA，禁用JS（curl本身不执行JS）
    # --compressed 自动解压gzip/br
    # -L 跟随重定向
    # -k 跳过SSL校验（模拟unsafeSSL）
    # --max-time 30 超时
    ua_escaped = CRONET_UA.replace('"', '\\"')
    curl_cmd = (
        f'curl -sL -k --compressed --max-time 30 '
        f'-A "{ua_escaped}" '
        f'-H "Accept-Language: zh-CN,zh;q=0.9" '
        f'-H "Cache-Control: no-cache" '
        f'-o {remote_path} '
        f'"{url}"'
    )
    try:
        r = adb_shell(curl_cmd, timeout=45)
        # 检查文件是否生成
        r2 = adb_shell(f'ls -la {remote_path}', timeout=10)
        ls_out = r2.stdout.decode('utf-8', errors='ignore')
        if remote_path not in ls_out:
            return None, f'curl_no_output:{ls_out.strip()[:50]}'
        # 检查文件大小
        size_match = re.search(r'\s+(\d+)\s+\S+$', ls_out.strip())
        if size_match:
            size = int(size_match.group(1))
            if size < 100:
                return None, f'html_too_small:{size}'
        # pull 到本地
        local_path = HTML_DIR / f'src_{idx:03d}_{label}.html'
        adb('pull', remote_path, str(local_path), timeout=30)
        if not local_path.exists() or local_path.stat().st_size < 100:
            return None, 'pull_failed_or_empty'
        # 读取HTML
        with open(local_path, 'rb') as f:
            raw = f.read()
        # 检测编码
        encoding = 'utf-8'
        try:
            raw.decode('utf-8')
        except UnicodeDecodeError:
            try:
                raw.decode('gbk')
                encoding = 'gbk'
            except:
                encoding = 'utf-8'
        html = raw.decode(encoding, errors='ignore')
        # 清理远程文件
        adb_shell(f'rm {remote_path}', timeout=5)
        return html, 'ok'
    except subprocess.TimeoutExpired:
        return None, 'curl_timeout'
    except Exception as e:
        return None, f'exception:{type(e).__name__}'


def find_best_list_selector(soup, min_count=3):
    """从BS4 soup中找最佳的列表选择器"""
    candidates = [
        # 优先：语义化标签
        'article',
        '.post',
        '.article',
        '.entry',
        '.item',
        '.card',
        '.article-item',
        '.list-item',
        '.news-item',
        # 常见列表容器
        '.article-list li',
        '.article-list .item',
        '.post-list .post',
        '.post-list .item',
        '.news-list li',
        '.news-list .item',
        '.list li',
        'ul.posts li',
        'ul.article-list li',
        'ul.news-list li',
        # 链接列表（最通用）
        'ul li a[href]',
        '.list a[href]',
        '.content a[href]',
        # 含特定关键词的链接
        'a[href*="article"]',
        'a[href*="detail"]',
        'a[href*="post"]',
        'a[href*="news"]',
        'a[href*="/p/"]',
        'a[href*="/n/"]',
        'a[href*="/a/"]',
        # div容器
        'div.article',
        'div.post',
        'div.item',
        'div.entry',
        # WordPress 标准模板
        '.post-archive .post',
        '.posts .post',
        'main article',
        '#main article',
        '#content article',
        # 通用 li
        'ul > li',
        'ol > li',
    ]
    
    best = None
    best_count = 0
    for sel in candidates:
        try:
            items = soup.select(sel)
            if len(items) >= min_count and len(items) > best_count:
                best = (sel, items)
                best_count = len(items)
        except Exception:
            continue
    return best


def detect_spa_html(soup):
    """检测是否是SPA（JS渲染的页面）"""
    scripts = soup.find_all('script')
    spa_markers = [
        '__NUXT__',
        '__INITIAL_STATE__',
        'window.__data',
        '__NEXT_DATA__',
        '__APOLLO_STATE__',
        'window.__INITIAL_STATE__',
        'data-reactroot',
    ]
    for sc in scripts:
        text = sc.string or sc.text or ''
        for marker in spa_markers:
            if marker in text:
                return True, marker
    body = soup.find('body')
    if body:
        body_text = body.get_text(strip=True)
        if len(body_text) < 100:
            return True, 'empty_body'
    return False, None


def find_article_detail_url(soup, list_url):
    """从列表页找一个文章详情页URL"""
    candidates = [
        'article a[href]',
        '.post a[href]',
        '.article a[href]',
        '.item a[href]',
        '.entry a[href]',
        '.article-list a[href]',
        '.post-list a[href]',
        '.news-list a[href]',
        '.list-item a[href]',
        'h2 a[href]',
        'h3 a[href]',
        'a[href*="article"]',
        'a[href*="detail"]',
        'a[href*="post"]',
        'a[href*="news"]',
        'a[href*="/p/"]',
        'ul li a[href]',
    ]
    
    for sel in candidates:
        links = soup.select(sel)
        for link in links:
            href = link.get('href', '')
            if href and not href.startswith('javascript:') and not href.startswith('#') and not href.startswith('mailto:'):
                if href.startswith('//'):
                    p = urlparse(list_url)
                    href = f"{p.scheme}:{href}"
                elif href.startswith('/'):
                    p = urlparse(list_url)
                    href = f"{p.scheme}://{p.netloc}{href}"
                elif not href.startswith('http'):
                    href = urljoin(list_url, href)
                return href
    return None


def find_best_content_selector(soup, min_len=100):
    """从BS4 soup中找最佳正文选择器"""
    candidates = [
        'article',
        '.content',
        '.article-content',
        '.entry-content',
        '.article-body',
        '.post-content',
        '.main-content',
        '.detail-content',
        '.news-content',
        '.article-text',
        '.text-content',
        '.article-detail',
        '.content-body',
        '.post-body',
        '.entry-body',
        'div.content',
        'div.article',
        'div.text',
        '#content',
        '#article',
        '#article-content',
        '.text',
        '.article',
        '#main-content',
        '.read-content',
        '.read-body',
    ]
    
    best = None
    best_len = 0
    for sel in candidates:
        try:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if len(text) > best_len:
                    best = (sel, el, text)
                    best_len = len(text)
        except Exception:
            continue
    if best and best_len >= min_len:
        return best
    return None


def fix_list_empty_source(idx, source):
    """修复list_empty源：用真机curl获取HTML，重写ruleArticles"""
    url = source.get('sourceUrl', '')
    if not url.startswith('http'):
        # 尝试从 sortUrl 提取
        sort_url = source.get('sortUrl', '')
        if sort_url:
            first_line = sort_url.split('\n')[0]
            if '::' in first_line:
                url = first_line.split('::', 1)[1].strip()
    
    if not url or not url.startswith('http'):
        return {'fixed': False, 'reason': 'no_valid_url'}
    
    print(f"  [fetch] url_len={len(url)}")
    html, status = fetch_html_via_device(url, idx, 'list')
    if not html:
        return {'fixed': False, 'reason': f'fetch_failed:{status}'}
    
    print(f"  [parse] html_len={len(html)}")
    soup = BeautifulSoup(html, 'html.parser')
    
    # 检测SPA
    is_spa, spa_marker = detect_spa_html(soup)
    if is_spa:
        return {
            'fixed': False,
            'reason': 'spa_needs_js',
            'marker': spa_marker,
            'needs_disable': True
        }
    
    # 找最佳列表选择器
    best = find_best_list_selector(soup, min_count=3)
    if not best:
        best = find_best_list_selector(soup, min_count=2)
    
    if not best:
        # 最后兜底：找所有a[href]
        all_links = soup.select('a[href]')
        if len(all_links) >= 5:
            # 用通用选择器
            return {
                'fixed': True,
                'old_rule': source.get('ruleArticles', ''),
                'new_rule': 'a[href]',
                'matched_count': len(all_links),
                'selector': 'a[href]',
                'fallback': True
            }
        return {'fixed': False, 'reason': 'no_list_in_raw_html', 'html_len': len(html)}
    
    sel, items = best
    sample_count = len(items)
    sample_titles = []
    for item in items[:3]:
        text = item.get_text(strip=True)
        if text:
            sample_titles.append(text[:30])
    
    return {
        'fixed': True,
        'old_rule': source.get('ruleArticles', ''),
        'new_rule': sel,
        'matched_count': sample_count,
        'selector': sel,
        'samples': sample_titles
    }


def fix_content_fail_source(idx, source):
    """修复content失败源：用真机curl获取文章详情页HTML，重写ruleContent"""
    list_url = source.get('sourceUrl', '')
    if not list_url.startswith('http'):
        return {'fixed': False, 'reason': 'no_list_url'}
    
    print(f"  [fetch_list] url_len={len(list_url)}")
    list_html, status = fetch_html_via_device(list_url, idx, 'list_for_content')
    if not list_html:
        return {'fixed': False, 'reason': f'list_fetch_failed:{status}'}
    
    list_soup = BeautifulSoup(list_html, 'html.parser')
    is_spa, _ = detect_spa_html(list_soup)
    if is_spa:
        return {'fixed': False, 'reason': 'list_is_spa'}
    
    # 找文章详情页URL
    article_url = find_article_detail_url(list_soup, list_url)
    if not article_url:
        return {'fixed': False, 'reason': 'no_article_link'}
    
    print(f"  [fetch_article] article_url_len={len(article_url)}")
    article_html, status = fetch_html_via_device(article_url, idx, 'article')
    if not article_html:
        return {'fixed': False, 'reason': f'article_fetch_failed:{status}'}
    
    article_soup = BeautifulSoup(article_html, 'html.parser')
    is_spa, _ = detect_spa_html(article_soup)
    if is_spa:
        return {'fixed': False, 'reason': 'article_is_spa'}
    
    # 找正文选择器
    best = find_best_content_selector(article_soup, min_len=100)
    if not best:
        # 降低阈值
        best = find_best_content_selector(article_soup, min_len=50)
    
    if not best:
        return {'fixed': False, 'reason': 'no_content_found', 'article_html_len': len(article_html)}
    
    sel, el, text = best
    new_rule_content = sel
    
    return {
        'fixed': True,
        'old_rule_len': len(source.get('ruleContent', '')),
        'new_rule': new_rule_content,
        'content_len': len(text),
        'selector': sel,
        'sample_text': text[:60] + '...' if len(text) > 60 else text
    }


def fix_malformed_url_source(idx, source):
    """修复malformed_url源：分析HTML搜索表单修复searchUrl"""
    list_url = source.get('sourceUrl', '')
    if not list_url.startswith('http'):
        return {'fixed': False, 'reason': 'no_list_url'}
    
    print(f"  [fetch] url_len={len(list_url)}")
    html, status = fetch_html_via_device(list_url, idx, 'list_for_search')
    if not html:
        return {'fixed': False, 'reason': f'fetch_failed:{status}'}
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 找搜索表单
    forms = soup.find_all('form')
    best_form = None
    best_input = None
    for form in forms:
        action = form.get('action', '')
        method = (form.get('method') or 'get').lower()
        inputs = form.find_all('input')
        for inp in inputs:
            t = (inp.get('type') or 'text').lower()
            if t in ('text', 'search', ''):
                best_form = form
                best_input = inp
                break
        if best_form:
            break
    
    if not best_form or not best_input:
        # 没有表单，检查现有searchUrl
        old_search = source.get('searchUrl', '')
        if '{{key}}' not in old_search:
            # 没有占位符，用通用GET格式
            p = urlparse(list_url)
            base = f"{p.scheme}://{p.netloc}"
            # 推断搜索路径
            return {
                'fixed': True,
                'old_rule': old_search,
                'new_rule': f'{base}/?s={{{{key}}}}',
                'method': 'get',
                'fallback': True
            }
        return {'fixed': False, 'reason': 'no_form_and_has_key_placeholder'}
    
    action = best_form.get('action', '')
    method = (best_form.get('method') or 'get').lower()
    name = best_input.get('name', 'q')
    
    if not action:
        action = list_url
    elif not action.startswith('http'):
        action = urljoin(list_url, action)
    
    if method == 'post':
        new_search_url = f'{action},{{"method":"POST","body":"{name}={{{{key}}}}"}}'
    else:
        sep = '&' if '?' in action else '?'
        new_search_url = f'{action}{sep}{name}={{{{key}}}}'
    
    return {
        'fixed': True,
        'old_rule': source.get('searchUrl', ''),
        'new_rule': new_search_url,
        'method': method,
        'form_field': name
    }


def fix_search_rule_source(idx, source):
    """修复ruleSearchArticle不匹配源：用真机curl访问搜索结果页，重写ruleSearchArticle"""
    search_url = source.get('searchUrl', '')
    
    if search_url.startswith('@js:') or search_url.startswith('<js>'):
        return {'fixed': False, 'reason': 'js_search_url_not_supported'}
    
    if ',' in search_url and search_url.startswith('http'):
        url = search_url.split(',', 1)[0]
    elif search_url.startswith('http'):
        url = search_url
    else:
        return {'fixed': False, 'reason': 'searchUrl_format_invalid'}
    
    # 替换占位符为测试关键词
    test_url = url.replace('{{key}}', 'test').replace('{{page}}', '1')
    
    print(f"  [fetch_search] url_len={len(test_url)}")
    html, status = fetch_html_via_device(test_url, idx, 'search')
    if not html:
        return {'fixed': False, 'reason': f'search_fetch_failed:{status}'}
    
    soup = BeautifulSoup(html, 'html.parser')
    is_spa, _ = detect_spa_html(soup)
    if is_spa:
        return {'fixed': False, 'reason': 'search_result_is_spa'}
    
    # 找搜索结果选择器
    best = find_best_list_selector(soup, min_count=2)
    if not best:
        search_candidates = [
            '.search-item',
            '.search-result',
            '.result-item',
            '.search-list li',
            '.search-list .item',
            '.search-results li',
            '.search-results .item',
        ]
        for sel in search_candidates:
            items = soup.select(sel)
            if len(items) >= 1:
                best = (sel, items)
                break
    
    if not best:
        # 兜底：用通用 a[href]
        all_links = soup.select('a[href]')
        if len(all_links) >= 3:
            return {
                'fixed': True,
                'old_rule_len': len(source.get('ruleSearchArticle', '')),
                'new_rule': 'a[href]',
                'matched_count': len(all_links),
                'selector': 'a[href]',
                'fallback': True
            }
        return {'fixed': False, 'reason': 'no_search_result_in_raw_html'}
    
    sel, items = best
    return {
        'fixed': True,
        'old_rule_len': len(source.get('ruleSearchArticle', '')),
        'new_rule': sel,
        'matched_count': len(items),
        'selector': sel
    }


def main():
    print("=== V5.5 Cronet Mismatch Fix (via device curl) ===")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查ADB连接
    r = adb('get-state', timeout=5)
    state = r.stdout.decode('utf-8', errors='ignore').strip()
    if state != 'device':
        print(f"❌ device not ready: {state!r}")
        return
    print(f"✅ device online: {state}")
    
    # 加载V5.4最终JSON
    sources = json.load(open(V54_JSON, 'r', encoding='utf-8'))
    enabled_sources = [s for s in sources if s.get('enabled', False)]
    print(f"Loaded {len(enabled_sources)} enabled sources from V5.4")
    
    fix_results = {
        'list_empty': [],
        'content_fail': [],
        'malformed_url': [],
        'search_rule_fail': [],
    }
    
    stats = {
        'total_processed': 0,
        'total_fixed': 0,
        'total_disabled': 0,
        'total_failed': 0,
    }
    
    # === Phase 1: 修复11个list_empty源 ===
    print("\n--- Phase 1: Fix 11 list_empty sources ---")
    for idx in LIST_EMPTY_IDX:
        if idx >= len(enabled_sources):
            continue
        source = enabled_sources[idx]
        print(f"\n[list_empty] idx={idx}")
        stats['total_processed'] += 1
        try:
            result = fix_list_empty_source(idx, source)
            result['idx'] = idx
            fix_results['list_empty'].append(result)
            if result.get('fixed'):
                print(f"  ✅ fixed selector={result['selector']} count={result['matched_count']}")
                source['ruleArticles'] = result['new_rule']
                stats['total_fixed'] += 1
            else:
                print(f"  ❌ failed reason={result['reason']}")
                stats['total_failed'] += 1
                if result.get('needs_disable'):
                    source['enabled'] = False
                    source['_v55_disabled_reason'] = f"spa_needs_js:{result.get('marker','unknown')}"
                    print(f"  ⚠️ disabled (SPA needs JS, Cronet can't render)")
                    stats['total_disabled'] += 1
        except Exception as e:
            err = type(e).__name__
            print(f"  ❌ exception: {err}: {str(e)[:80]}")
            fix_results['list_empty'].append({'idx': idx, 'fixed': False, 'reason': f'exception:{err}'})
            stats['total_failed'] += 1
    
    # === Phase 2: 修复5个content失败源 ===
    print("\n--- Phase 2: Fix 5 content_fail sources ---")
    for idx in CONTENT_FAIL_IDX:
        if idx >= len(enabled_sources):
            continue
        source = enabled_sources[idx]
        if not source.get('enabled', True):
            print(f"\n[content_fail] idx={idx} skipped (disabled)")
            continue
        print(f"\n[content_fail] idx={idx}")
        stats['total_processed'] += 1
        try:
            result = fix_content_fail_source(idx, source)
            result['idx'] = idx
            fix_results['content_fail'].append(result)
            if result.get('fixed'):
                print(f"  ✅ fixed selector={result['selector']} content_len={result['content_len']}")
                source['ruleContent'] = result['new_rule']
                stats['total_fixed'] += 1
            else:
                print(f"  ❌ failed reason={result['reason']}")
                stats['total_failed'] += 1
        except Exception as e:
            err = type(e).__name__
            print(f"  ❌ exception: {err}")
            fix_results['content_fail'].append({'idx': idx, 'fixed': False, 'reason': f'exception:{err}'})
            stats['total_failed'] += 1
    
    # === Phase 3: 修复2个malformed_url源 ===
    print("\n--- Phase 3: Fix 2 malformed_url sources ---")
    for idx in MALFORMED_URL_IDX:
        if idx >= len(enabled_sources):
            continue
        source = enabled_sources[idx]
        if not source.get('enabled', True):
            print(f"\n[malformed_url] idx={idx} skipped (disabled)")
            continue
        print(f"\n[malformed_url] idx={idx}")
        stats['total_processed'] += 1
        try:
            result = fix_malformed_url_source(idx, source)
            result['idx'] = idx
            fix_results['malformed_url'].append(result)
            if result.get('fixed'):
                print(f"  ✅ fixed method={result['method']}")
                source['searchUrl'] = result['new_rule']
                stats['total_fixed'] += 1
            else:
                print(f"  ❌ failed reason={result['reason']}")
                stats['total_failed'] += 1
        except Exception as e:
            err = type(e).__name__
            print(f"  ❌ exception: {err}")
            fix_results['malformed_url'].append({'idx': idx, 'fixed': False, 'reason': f'exception:{err}'})
            stats['total_failed'] += 1
    
    # === Phase 4: 修复2个ruleSearchArticle不匹配源 ===
    print("\n--- Phase 4: Fix 2 ruleSearchArticle sources ---")
    for idx in SEARCH_RULE_FAIL_IDX:
        if idx >= len(enabled_sources):
            continue
        source = enabled_sources[idx]
        if not source.get('enabled', True):
            print(f"\n[search_rule] idx={idx} skipped (disabled)")
            continue
        print(f"\n[search_rule] idx={idx}")
        stats['total_processed'] += 1
        try:
            result = fix_search_rule_source(idx, source)
            result['idx'] = idx
            fix_results['search_rule_fail'].append(result)
            if result.get('fixed'):
                print(f"  ✅ fixed selector={result['selector']} count={result['matched_count']}")
                source['ruleSearchArticle'] = result['new_rule']
                stats['total_fixed'] += 1
            else:
                print(f"  ❌ failed reason={result['reason']}")
                stats['total_failed'] += 1
        except Exception as e:
            err = type(e).__name__
            print(f"  ❌ exception: {err}")
            fix_results['search_rule_fail'].append({'idx': idx, 'fixed': False, 'reason': f'exception:{err}'})
            stats['total_failed'] += 1
    
    # 清理 _v55_disabled_reason 字段
    for s in sources:
        if '_v55_disabled_reason' in s:
            reason = s.pop('_v55_disabled_reason')
            old_comment = s.get('sourceComment', '')
            s['sourceComment'] = f"{old_comment}|v5.5_disabled:{reason}" if old_comment else f"v5.5_disabled:{reason}"
    
    # 保存修复后的JSON
    with open(V55_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f"\n=== Saved fixed JSON to {V55_JSON} ===")
    
    # 保存修复结果
    fix_results['_stats'] = stats
    fix_results['_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(V55_FIX_RESULT, 'w', encoding='utf-8') as f:
        json.dump(fix_results, f, ensure_ascii=False, indent=2)
    print(f"=== Saved fix result to {V55_FIX_RESULT} ===")
    
    print(f"\n=== Summary ===")
    print(f"Total processed: {stats['total_processed']}")
    print(f"Fixed: {stats['total_fixed']}")
    print(f"Disabled (SPA): {stats['total_disabled']}")
    print(f"Failed: {stats['total_failed']}")
    
    for cat, results in fix_results.items():
        if cat.startswith('_'):
            continue
        fixed = sum(1 for r in results if r.get('fixed'))
        print(f"  {cat}: {fixed}/{len(results)} fixed")


if __name__ == '__main__':
    main()
