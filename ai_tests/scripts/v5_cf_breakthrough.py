"""
V5 CF盾源4个破盾突破脚本
- 5大破盾技术：headful+反检测 / cookie注入 / 等待30s / google cache / httpx禁用TLS+HTTP降级
- 输出全部脱敏：URL->http://[DOMAIN_N]/path
"""
import json
import re
import sys
import os
import time
import traceback
from urllib.parse import urlparse, urlunparse

# 配置
V5_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_final.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_cf_breakthrough.json'
PROGRESS_FILE = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_cf_breakthrough.progress.json'
CF_INDICES = [0, 93, 95, 97]

# CF盾页特征关键词（用于检测破盾是否成功）
CF_TITLE_KEYWORDS = ['just a moment', 'cloudflare', '请稍候', 'attention required', 'ddos protection', 'cf-ray', 'cf-mitigated']
CF_HTML_MARKERS = ['cf-browser-verification', 'cf_chl_opt', 'cf-mitigated', 'cf-ray', '_cf_chl', 'challenge-platform']


def mask_url(url):
    """脱敏URL：只保留scheme和path，域名替换为[DOMAIN]"""
    if not url:
        return ''
    try:
        p = urlparse(url)
        if not p.netloc:
            return url  # 不是标准URL，原样返回（可能是JS规则）
        # 路径只保留前30字符
        path = p.path[:50]
        return f'{p.scheme}://[DOMAIN]{path}'
    except Exception:
        return '[INVALID_URL]'


def is_cf_page(title, html):
    """检测页面是否仍为CF盾页"""
    title_lower = (title or '').lower()
    for kw in CF_TITLE_KEYWORDS:
        if kw in title_lower:
            return True
    # 检查HTML中的CF标记
    html_lower = (html or '').lower()[:50000]  # 只看前50K
    for marker in CF_HTML_MARKERS:
        if marker in html_lower:
            return True
    return False


def extract_real_urls(src):
    """从sourceUrl, loginUrl, header中提取真实URL"""
    candidates = []
    fields = [
        src.get('sourceUrl', '') or '',
        src.get('loginUrl', '') or '',
        src.get('header', '') or '',
        src.get('bookSourceUrl', '') or '',
        src.get('exploreUrl', '') or '',
    ]
    for f in fields:
        if not f:
            continue
        # 反转义JSON转义
        unescaped = f.replace('\\/', '/').replace('\\"', '"')
        matches = re.findall(r'https?://[a-zA-Z0-9._-]+(?:\.[a-zA-Z]{2,})+[/\w\-.?=&%~]*', unescaped)
        for m in matches:
            # 排除明显非源站点（如w3.org/google/jsdelivr等）
            p = urlparse(m)
            host = p.netloc.lower()
            if any(x in host for x in ['w3.org', 'google.com', 'googleapis.com', 'jsdelivr.net', 'cdnjs.cloudflare.com', 'unpkg.com', 'microsoft.com', 'schema.org']):
                continue
            candidates.append(m)
    # 去重保留顺序
    seen = set()
    unique = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def check_page_normal(page):
    """检查页面是否正常（非CF盾）"""
    try:
        title = page.title() or ''
    except Exception:
        title = ''
    try:
        html = page.content() or ''
    except Exception:
        html = ''
    html_size = len(html)
    is_cf = is_cf_page(title, html)
    # 判断成功：title不含CF关键词 + html_size>5000 + HTML含正文标记
    has_content_marker = any(x in html.lower()[:30000] for x in ['<article', '<main', '<nav', '<div class="content"', 'rss', 'feed', 'rss', 'channel', 'item'])
    success = (not is_cf) and html_size > 5000
    return {
        'page_title': title[:80],
        'html_size': html_size,
        'title_no_cf': not is_cf,
        'has_content_marker': has_content_marker,
        'success': success
    }


# ==================== 5大破盾手段 ====================

def strategy1_headful(url, timeout_s=45):
    """手段1：headful模式+反自动化参数"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-infobars',
                    '--window-size=1920,1080'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            )
            # 反检测JS
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                window.chrome = {runtime: {}};
            """)
            page = context.new_page()
            try:
                page.goto(url, timeout=timeout_s * 1000, wait_until='domcontentloaded')
                page.wait_for_timeout(8000)  # 等待CF challenge自动完成
                result = check_page_normal(page)
                result['strategy'] = 'strategy1_headful'
                return result
            finally:
                browser.close()
    except Exception as e:
        return {
            'strategy': 'strategy1_headful',
            'error': f'{type(e).__name__}: {str(e)[:200]}',
            'success': False
        }


def strategy2_cookie(url, cookie_value=None, timeout_s=30):
    """手段2：cookie注入（无cookie则跳过）"""
    if not cookie_value:
        return {
            'strategy': 'strategy2_cookie',
            'result': 'no_cookie_provided',
            'success': False
        }
    try:
        from playwright.sync_api import sync_playwright
        p_url = urlparse(url)
        domain = p_url.netloc
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            context.add_cookies([{
                'name': 'cf_clearance',
                'value': cookie_value,
                'domain': domain,
                'path': '/',
                'secure': True,
                'httpOnly': True,
                'sameSite': 'Lax'
            }])
            page = context.new_page()
            try:
                page.goto(url, timeout=timeout_s * 1000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
                result = check_page_normal(page)
                result['strategy'] = 'strategy2_cookie'
                return result
            finally:
                browser.close()
    except Exception as e:
        return {
            'strategy': 'strategy2_cookie',
            'error': f'{type(e).__name__}: {str(e)[:200]}',
            'success': False
        }


def strategy3_wait_30s(url, timeout_s=60):
    """手段3：等待CF challenge自动完成（30s+10s）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            try:
                page.goto(url, timeout=timeout_s * 1000, wait_until='domcontentloaded')
                page.wait_for_timeout(30000)  # 等30s
                title = page.title() or ''
                if any(kw in title.lower() for kw in CF_TITLE_KEYWORDS):
                    page.wait_for_timeout(10000)  # 再等10s
                result = check_page_normal(page)
                result['strategy'] = 'strategy3_wait_30s'
                return result
            finally:
                browser.close()
    except Exception as e:
        return {
            'strategy': 'strategy3_wait_30s',
            'error': f'{type(e).__name__}: {str(e)[:200]}',
            'success': False
        }


def strategy4_google_cache(url, timeout_s=30):
    """手段4：Google cache方式"""
    try:
        from playwright.sync_api import sync_playwright
        cache_url = f'https://webcache.googleusercontent.com/search?q=cache:{url}'
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            try:
                resp = page.goto(cache_url, timeout=timeout_s * 1000, wait_until='domcontentloaded')
                status = resp.status if resp else 0
                page.wait_for_timeout(3000)
                title = page.title() or ''
                html = page.content() or ''
                html_size = len(html)
                # Google cache成功标志：状态200 + html_size>5000 + 不含"cache not found"
                cache_fail_markers = ['cache not found', 'not available', "doesn't have", 'did not match', '404. that']
                cache_failed = any(m in html.lower()[:20000] for m in cache_fail_markers)
                success = (status == 200) and html_size > 5000 and (not cache_failed)
                return {
                    'strategy': 'strategy4_google_cache',
                    'status_code': status,
                    'page_title': title[:80],
                    'html_size': html_size,
                    'cache_failed': cache_failed,
                    'success': success
                }
            finally:
                browser.close()
    except Exception as e:
        return {
            'strategy': 'strategy4_google_cache',
            'error': f'{type(e).__name__}: {str(e)[:200]}',
            'success': False
        }


def strategy5_httpx_tls(url, timeout_s=30):
    """手段5：禁用TLS验证+HTTP降级"""
    try:
        import httpx
        import urllib3
        urllib3.disable_warnings()
        # 先尝试HTTPS（禁用TLS验证）
        results = []
        client = httpx.Client(verify=False, follow_redirects=True, timeout=timeout_s)
        try:
            resp = client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'zh-CN,zh;q=0.9'
                }
            )
            title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text or '', re.IGNORECASE | re.DOTALL)
            title = (title_match.group(1).strip()[:80] if title_match else '')
            html_size = len(resp.text or '')
            is_cf = is_cf_page(title, resp.text or '')
            results.append({
                'variant': 'https_tls_disabled',
                'status_code': resp.status_code,
                'page_title': title,
                'html_size': html_size,
                'is_cf': is_cf,
                'success': (resp.status_code == 200) and (not is_cf) and html_size > 5000
            })
        except Exception as e:
            results.append({
                'variant': 'https_tls_disabled',
                'error': f'{type(e).__name__}: {str(e)[:150]}',
                'success': False
            })
        # 尝试HTTP降级
        if url.startswith('https://'):
            http_url = 'http://' + url[len('https://'):]
            try:
                resp = client.get(
                    http_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept-Language': 'zh-CN,zh;q=0.9'
                    }
                )
                title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text or '', re.IGNORECASE | re.DOTALL)
                title = (title_match.group(1).strip()[:80] if title_match else '')
                html_size = len(resp.text or '')
                is_cf = is_cf_page(title, resp.text or '')
                results.append({
                    'variant': 'http_downgrade',
                    'status_code': resp.status_code,
                    'page_title': title,
                    'html_size': html_size,
                    'is_cf': is_cf,
                    'success': (resp.status_code == 200) and (not is_cf) and html_size > 5000
                })
            except Exception as e:
                results.append({
                    'variant': 'http_downgrade',
                    'error': f'{type(e).__name__}: {str(e)[:150]}',
                    'success': False
                })
        client.close()
        # 任一变体成功则手段5成功
        any_success = any(r.get('success') for r in results)
        return {
            'strategy': 'strategy5_httpx_tls',
            'variants': results,
            'success': any_success
        }
    except Exception as e:
        return {
            'strategy': 'strategy5_httpx_tls',
            'error': f'{type(e).__name__}: {str(e)[:200]}',
            'success': False
        }


# ==================== 主流程 ====================

def load_sources():
    with open(V5_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('sources', [])


def process_source(idx, src):
    """对单个源执行5大破盾手段"""
    # 提取真实URL
    urls = extract_real_urls(src)
    if not urls:
        # 无URL，从sourceUrl尝试取（即使是非标准格式）
        surl = src.get('sourceUrl', '') or ''
        # 直接看是否有https?://
        m = re.search(r'https?://[a-zA-Z0-9._-]+(?:\.[a-zA-Z]{2,})+[/\w\-.?=&%]*', surl.replace('\\/', '/'))
        if m:
            urls = [m.group(0)]
    if not urls:
        return {
            'source_index': idx,
            'sourceUrl_pattern': '[NO_VALID_URL]',
            'success_strategy': None,
            'new_fields': {
                'enabled': src.get('enabled', True),
                'sourceComment': '// CF破盾失败(无URL)'
            },
            'evidence': {
                'error': 'no_real_url_found',
                'url_fields_scanned': ['sourceUrl', 'loginUrl', 'header']
            },
            'all_strategies': {},
            'success': False
        }
    
    real_url = urls[0]
    masked_url = mask_url(real_url)
    
    all_results = {}
    success_strategy = None
    success_evidence = None
    
    # 手段1：headful+反检测
    print(f'[idx={idx}] Try strategy1_headful ...', flush=True)
    r1 = strategy1_headful(real_url)
    all_results['strategy1_headful'] = {
        'page_title': r1.get('page_title', ''),
        'html_size': r1.get('html_size', 0),
        'title_no_cf': r1.get('title_no_cf', False),
        'success': r1.get('success', False),
        'error': r1.get('error', None),
        'result': r1.get('result', None)
    }
    if r1.get('success'):
        success_strategy = 'strategy1_headful'
        success_evidence = {k: v for k, v in r1.items() if k != 'strategy'}
    else:
        # 手段2：cookie注入（用户未提供cookie，跳过）
        print(f'[idx={idx}] Try strategy2_cookie ...', flush=True)
        r2 = strategy2_cookie(real_url, cookie_value=None)
        all_results['strategy2_cookie'] = {
            'result': r2.get('result', ''),
            'success': r2.get('success', False),
            'error': r2.get('error', None)
        }
        if r2.get('success'):
            success_strategy = 'strategy2_cookie'
            success_evidence = {k: v for k, v in r2.items() if k != 'strategy'}
        else:
            # 手段3：等待30s自动完成
            print(f'[idx={idx}] Try strategy3_wait_30s ...', flush=True)
            r3 = strategy3_wait_30s(real_url)
            all_results['strategy3_wait_30s'] = {
                'page_title': r3.get('page_title', ''),
                'html_size': r3.get('html_size', 0),
                'title_no_cf': r3.get('title_no_cf', False),
                'success': r3.get('success', False),
                'error': r3.get('error', None)
            }
            if r3.get('success'):
                success_strategy = 'strategy3_wait_30s'
                success_evidence = {k: v for k, v in r3.items() if k != 'strategy'}
            else:
                # 手段4：Google cache
                print(f'[idx={idx}] Try strategy4_google_cache ...', flush=True)
                r4 = strategy4_google_cache(real_url)
                all_results['strategy4_google_cache'] = {
                    'status_code': r4.get('status_code', 0),
                    'page_title': r4.get('page_title', ''),
                    'html_size': r4.get('html_size', 0),
                    'cache_failed': r4.get('cache_failed', False),
                    'success': r4.get('success', False),
                    'error': r4.get('error', None)
                }
                if r4.get('success'):
                    success_strategy = 'strategy4_google_cache'
                    success_evidence = {k: v for k, v in r4.items() if k != 'strategy'}
                else:
                    # 手段5：httpx禁用TLS+HTTP降级
                    print(f'[idx={idx}] Try strategy5_httpx_tls ...', flush=True)
                    r5 = strategy5_httpx_tls(real_url)
                    all_results['strategy5_httpx_tls'] = {
                        'variants': r5.get('variants', []),
                        'success': r5.get('success', False),
                        'error': r5.get('error', None)
                    }
                    if r5.get('success'):
                        success_strategy = 'strategy5_httpx_tls'
                        # 找到成功的变体
                        for v in r5.get('variants', []):
                            if v.get('success'):
                                success_evidence = v
                                break
    
    success = success_strategy is not None
    new_fields = {
        'enabled': src.get('enabled', True),
        'sourceComment': f'// CF破盾成功({success_strategy})' if success else '// CF破盾失败(5大手段均失败)'
    }
    
    return {
        'source_index': idx,
        'sourceUrl_pattern': masked_url,
        'success_strategy': success_strategy,
        'new_fields': new_fields,
        'evidence': success_evidence if success_evidence else {
            'all_strategies_tried': True,
            'best_result': 'all_failed'
        },
        'all_strategies': all_results,
        'success': success
    }


def main():
    print('=== V5 CF Breakthrough Start ===', flush=True)
    sources = load_sources()
    print(f'Loaded {len(sources)} sources', flush=True)
    
    fixes = []
    failed = []
    strategy_counts = {
        'strategy1_headful': 0,
        'strategy2_cookie': 0,
        'strategy3_wait_30s': 0,
        'strategy4_google_cache': 0,
        'strategy5_httpx_tls': 0
    }
    
    for idx in CF_INDICES:
        if idx >= len(sources):
            print(f'idx={idx} out of range, skip', flush=True)
            continue
        src = sources[idx]
        print(f'\n--- Processing idx={idx} ---', flush=True)
        try:
            result = process_source(idx, src)
        except Exception as e:
            traceback.print_exc()
            result = {
                'source_index': idx,
                'sourceUrl_pattern': '[ERROR]',
                'success_strategy': None,
                'new_fields': {'enabled': src.get('enabled', True), 'sourceComment': f'// CF破盾失败(脚本异常:{type(e).__name__})'},
                'evidence': {'error': str(e)[:200]},
                'all_strategies': {},
                'success': False
            }
        
        if result['success']:
            fixes.append(result)
            strategy_counts[result['success_strategy']] = strategy_counts.get(result['success_strategy'], 0) + 1
        else:
            failed.append(result)
        
        # 写进度文件
        progress = {
            'processed': CF_INDICES.index(idx) + 1,
            'total': len(CF_INDICES),
            'last_idx': idx,
            'last_success': result['success'],
            'fixes_so_far': len(fixes),
            'failed_so_far': len(failed)
        }
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    output = {
        'analyzed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_input': len(CF_INDICES),
        'success_count': len(fixes),
        'failed_count': len(failed),
        'by_strategy': strategy_counts,
        'fixes': fixes,
        'failed': failed
    }
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n=== Done ===', flush=True)
    print(f'Success: {len(fixes)}/{len(CF_INDICES)}', flush=True)
    print(f'Failed: {len(failed)}/{len(CF_INDICES)}', flush=True)
    print(f'By strategy: {strategy_counts}', flush=True)


if __name__ == '__main__':
    main()
