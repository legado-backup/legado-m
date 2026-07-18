#!/usr/bin/env python3
"""aggressive_deep_optimize.py — 激进深度优化7个源（脱敏）

对7个用户坚持认为可以解决的源做最激进的优化尝试：
- idx=21: requests+Session+cookie共享
- idx=24: Playwright真实渲染+Cookie
- idx=30: socket直连+多端口
- idx=36: Playwright+各种TLS配置
- idx=39: Wayback存档直接访问+提取主页
- idx=55: 60s超时+requests adapter
- idx=58: Playwright+各种反爬绕过

输出：idx + 技术指标，不输出业务字段
"""
import json
import os
import re
import sys
import socket
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse
import http.client
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v5.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v6.json'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1'


def sanitize(text):
    """脱敏：替换URL/域名/IP为代号"""
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'https?://[^\s"\']+', '[URL]', s)
    s = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', s)  # IP
    s = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', s, flags=re.IGNORECASE)
    return s[:200]


def fetch_with_requests_session(url, timeout=20, follow_redirect=True):
    """用requests+Session访问（自动处理cookie）"""
    import requests
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        # 先访问根域名拿cookie
        m = re.match(r'(https?://[^/]+)', url)
        if m:
            root = m.group(1) + '/'
            try:
                session.get(root, timeout=10, verify=False, allow_redirects=True)
            except Exception:
                pass
        # 再访问目标URL
        resp = session.get(url, timeout=timeout, verify=False, allow_redirects=follow_redirect)
        return (resp.status_code, len(resp.content), None, resp.url, dict(resp.cookies))
    except requests.exceptions.HTTPError as e:
        return (e.response.status_code if e.response else 0, 0, f'http_error', '', {})
    except requests.exceptions.ConnectionError as e:
        err = str(e)
        if 'SSLError' in err or 'ssl' in err.lower():
            return (0, 0, 'ssl_error', '', {})
        if 'ConnectionReset' in err:
            return (0, 0, 'connection_reset', '', {})
        if 'RemoteDisconnected' in err:
            return (0, 0, 'remote_disconnected', '', {})
        return (0, 0, 'connection_error', '', {})
    except requests.exceptions.Timeout:
        return (0, 0, 'timeout', '', {})
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}', '', {})


def fetch_with_playwright_real(url, wait_seconds=10):
    """用Playwright真实渲染（带等待+stealth）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
            ])
            context = browser.new_context(
                user_agent=UA,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                ignore_https_errors=True,
            )
            # 注入stealth脚本隐藏webdriver标识
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            """)
            page = context.new_page()
            try:
                resp = page.goto(url, wait_until='domcontentloaded', timeout=wait_seconds * 1000)
                # 等待额外渲染
                page.wait_for_timeout(3000)
                content = page.content()
                return (resp.status if resp else 0, len(content), None, page.url, content)
            except Exception as e:
                err = str(e)
                # 脱敏
                err = re.sub(r'https?://[^\s"\']+', '[URL]', err)
                err = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err, flags=re.IGNORECASE)
                return (0, 0, f'exception:{type(e).__name__}:{err[:100]}', '', '')
            finally:
                browser.close()
    except Exception as e:
        return (0, 0, f'playwright_init_error:{type(e).__name__}', '', '')


def extract_main_url_from_wayback(source_url):
    """从Wayback存档提取主页URL"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        api_url = f'https://archive.org/wayback/available?url={urllib.parse.quote(source_url)}'
        req = urllib.request.Request(api_url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closest = data.get('archived_snapshots', {}).get('closest', {})
            if closest.get('available'):
                snap_url = closest.get('url', '')
                snap_ts = closest.get('timestamp', '')
                return snap_url, snap_ts
        return None, None
    except Exception as e:
        return None, None


def fetch_url_with_timeout(url, timeout=60):
    """长timeout URL访问"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return (resp.status, len(resp.read()), None, resp.geturl())
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}', '')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}', '')


def try_idx21(source):
    """idx=21: HTTP 500 + 301重定向 - 用requests+Session"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=21] sourceUrl_len={len(source_url)}')

    # 测试1: requests+Session+cookie
    s1, l1, e1, final1, cookies1 = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s1} len={l1} err={e1} final_changed={final1 != source_url if final1 else False} cookie_count={len(cookies1)}')
    if s1 == 200 and l1 > 500:
        return {'new_url': final1 or source_url, 'strategy': 'requests_session'}

    # 测试2: HTTP降级
    if source_url.startswith('https://'):
        url2 = 'http://' + source_url[len('https://'):]
        s2, l2, e2, final2, _ = fetch_with_requests_session(url2, timeout=20)
        print(f'    [http_downgrade] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': final2 or url2, 'strategy': 'http_downgrade_session'}

    # 测试3: 根域名
    m = re.match(r'(https?://[^/]+)', source_url)
    if m:
        root = m.group(1) + '/'
        s3, l3, e3, final3, _ = fetch_with_requests_session(root, timeout=20)
        print(f'    [root_session] status={s3} len={l3} err={e3}')
        if s3 == 200 and l3 > 500:
            return {'new_url': final3 or root, 'strategy': 'root_session'}

    # 测试4: Playwright真实渲染
    s4, l4, e4, final4, _ = fetch_with_playwright_real(source_url, wait_seconds=15)
    print(f'    [playwright] status={s4} len={l4} err={e4}')
    if s4 == 200 and l4 > 500:
        return {'new_url': final4 or source_url, 'strategy': 'playwright'}

    return None


def try_idx24(source):
    """idx=24: HTTP 403反爬 - Playwright真实渲染"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=24] sourceUrl_len={len(source_url)}')

    # 测试1: requests+完整header
    s1, l1, e1, final1, _ = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': final1 or source_url, 'strategy': 'requests_session'}

    # 测试2: Playwright真实渲染（带等待）
    s2, l2, e2, final2, content2 = fetch_with_playwright_real(source_url, wait_seconds=20)
    print(f'    [playwright] status={s2} len={l2} err={e2}')
    if s2 == 200 and l2 > 500:
        return {'new_url': final2 or source_url, 'strategy': 'playwright'}

    # 测试3: 移动UA
    try:
        import requests
        session = requests.Session()
        session.headers.update({
            'User-Agent': MOBILE_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        resp = session.get(source_url, timeout=20, verify=False)
        print(f'    [mobile_ua] status={resp.status_code} len={len(resp.content)}')
        if resp.status_code == 200 and len(resp.content) > 500:
            return {'new_url': source_url, 'strategy': 'mobile_ua'}
    except Exception as e:
        print(f'    [mobile_ua] exception:{type(e).__name__}')

    return None


def try_idx30(source):
    """idx=30: 端口2666 - socket+多端口"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=30] sourceUrl_len={len(source_url)}')

    # 提取domain
    m = re.match(r'https?://([^/:]+)', source_url)
    if not m:
        return None
    domain = m.group(1)
    print(f'    domain_len={len(domain)}')

    # 测试1: requests+session
    s1, l1, e1, final1, _ = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': final1 or source_url, 'strategy': 'requests_session'}

    # 测试2: 各种端口组合
    for port in [80, 443, 8080, 8443]:
        for scheme in ['http', 'https']:
            url = f'{scheme}://{domain}:{port}/'
            try:
                ctx = ssl.create_default_context() if scheme == 'https' else None
                if ctx:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                    data = resp.read()
                    print(f'    [{scheme}://{domain}:{port}/] status={resp.status} len={len(data)}')
                    if resp.status == 200 and len(data) > 500:
                        return {'new_url': url, 'strategy': f'{scheme}_port_{port}'}
            except urllib.error.HTTPError as e:
                print(f'    [{scheme}://{domain}:{port}/] http_{e.code}')
            except Exception as e:
                err_type = type(e).__name__
                if err_type == 'TimeoutError':
                    print(f'    [{scheme}://{domain}:{port}/] timeout')
                elif 'ConnectionRefused' in str(e) or 'ConnectionRefusedError' in err_type:
                    print(f'    [{scheme}://{domain}:{port}/] refused')
                else:
                    print(f'    [{scheme}://{domain}:{port}/] {err_type}')

    # 测试3: Playwright
    s3, l3, e3, _, _ = fetch_with_playwright_real(source_url, wait_seconds=15)
    print(f'    [playwright] status={s3} len={l3} err={e3}')
    if s3 == 200 and l3 > 500:
        return {'new_url': source_url, 'strategy': 'playwright'}

    return None


def try_idx36(source):
    """idx=36: SSL wrong_version - Playwright真实渲染"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=36] sourceUrl_len={len(source_url)}')

    # 测试1: requests+session
    s1, l1, e1, final1, _ = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': final1 or source_url, 'strategy': 'requests_session'}

    # 测试2: HTTP降级
    if source_url.startswith('https://'):
        url2 = 'http://' + source_url[len('https://'):]
        s2, l2, e2, final2, _ = fetch_with_requests_session(url2, timeout=20)
        print(f'    [http_downgrade] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': final2 or url2, 'strategy': 'http_downgrade'}

    # 测试3: Playwright
    s3, l3, e3, final3, _ = fetch_with_playwright_real(source_url, wait_seconds=15)
    print(f'    [playwright] status={s3} len={l3} err={e3}')
    if s3 == 200 and l3 > 500:
        return {'new_url': final3 or source_url, 'strategy': 'playwright'}

    return None


def try_idx39(source):
    """idx=39: HTTP 206文件下载 - Wayback存档提取主页"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=39] sourceUrl_len={len(source_url)}')

    # 测试1: 提取domain查询Wayback
    m = re.match(r'https?://([^/:]+)', source_url)
    if m:
        domain = m.group(1)
        # 查询domain根目录的存档
        snap_url, snap_ts = extract_main_url_from_wayback(f'https://{domain}/')
        print(f'    [wayback_domain] snap_ts={snap_ts} snap_url_len={len(snap_url) if snap_url else 0}')
        if snap_url:
            # 直接访问存档URL
            s1, l1, e1, final1 = fetch_url_with_timeout(snap_url, timeout=30)
            print(f'    [wayback_content] status={s1} len={l1} err={e1}')
            if s1 == 200 and l1 > 500:
                # 尝试访问wayback的原始URL（去除wayback前缀）
                # wayback URL格式: https://web.archive.org/web/TIMESTAMP/URL
                # 提取原始URL
                m2 = re.match(r'https?://web\.archive\.org/web/\d+/(.+)$', snap_url)
                if m2:
                    orig_url = m2.group(1)
                    print(f'    [wayback_orig_url] orig_len={len(orig_url)}')
                    # 直接访问原始URL（可能现在已可用）
                    s2, l2, e2, _ = fetch_url_with_timeout(orig_url, timeout=20)
                    print(f'    [orig_url_test] status={s2} len={l2} err={e2}')
                    if s2 == 200 and l2 > 500:
                        return {'new_url': orig_url, 'strategy': 'wayback_orig_url'}
                    # 如果原始URL不可用，用wayback URL
                    return {'new_url': snap_url, 'strategy': 'wayback_snapshot'}

    # 测试2: requests+session
    s3, l3, e3, _, _ = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s3} len={l3} err={e3}')
    if s3 == 200 and l3 > 500:
        return {'new_url': source_url, 'strategy': 'requests_session'}

    # 测试3: 域名根
    m3 = re.match(r'(https?://[^/]+)', source_url)
    if m3:
        root = m3.group(1) + '/'
        s4, l4, e4, _, _ = fetch_with_requests_session(root, timeout=20)
        print(f'    [root_session] status={s4} len={l4} err={e4}')
        if s4 == 200 and l4 > 500:
            return {'new_url': root, 'strategy': 'root_session'}

    return None


def try_idx55(source):
    """idx=55: timeout - 60s超时+requests adapter"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=55] sourceUrl_len={len(source_url)}')

    # 测试1: 60s超时
    s1, l1, e1, _ = fetch_url_with_timeout(source_url, timeout=60)
    print(f'    [60s_timeout] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': source_url, 'strategy': '60s_timeout'}

    # 测试2: HTTP降级
    if source_url.startswith('https://'):
        url2 = 'http://' + source_url[len('https://'):]
        s2, l2, e2, _ = fetch_url_with_timeout(url2, timeout=60)
        print(f'    [60s_http] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': url2, 'strategy': 'http_downgrade_60s'}

    # 测试3: requests+长timeout
    try:
        import requests
        session = requests.Session()
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(max_retries=3)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        resp = session.get(source_url, timeout=60, verify=False, headers={'User-Agent': UA})
        print(f'    [requests_adapter] status={resp.status_code} len={len(resp.content)}')
        if resp.status_code == 200 and len(resp.content) > 500:
            return {'new_url': source_url, 'strategy': 'requests_adapter'}
    except Exception as e:
        print(f'    [requests_adapter] exception:{type(e).__name__}')

    # 测试4: Wayback存档
    snap_url, snap_ts = extract_main_url_from_wayback(source_url)
    print(f'    [wayback] snap_ts={snap_ts}')
    if snap_url:
        s4, l4, e4, _ = fetch_url_with_timeout(snap_url, timeout=30)
        print(f'    [wayback_content] status={s4} len={l4} err={e4}')
        if s4 == 200 and l4 > 500:
            return {'new_url': snap_url, 'strategy': 'wayback_snapshot'}

    return None


def try_idx58(source):
    """idx=58: 反爬页17字节 - Playwright真实渲染"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=58] sourceUrl_len={len(source_url)}')

    # 测试1: Playwright真实渲染
    s1, l1, e1, final1, _ = fetch_with_playwright_real(source_url, wait_seconds=20)
    print(f'    [playwright] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': final1 or source_url, 'strategy': 'playwright'}

    # 测试2: requests+session+各种header
    s2, l2, e2, final2, _ = fetch_with_requests_session(source_url, timeout=20)
    print(f'    [requests_session] status={s2} len={l2} err={e2}')
    if s2 == 200 and l2 > 500:
        return {'new_url': final2 or source_url, 'strategy': 'requests_session'}

    # 测试3: HTTP降级
    if source_url.startswith('https://'):
        url3 = 'http://' + source_url[len('https://'):]
        s3, l3, e3, final3, _ = fetch_with_requests_session(url3, timeout=20)
        print(f'    [http_downgrade] status={s3} len={l3} err={e3}')
        if s3 == 200 and l3 > 500:
            return {'new_url': final3 or url3, 'strategy': 'http_downgrade'}

    return None


def main():
    print('=' * 70)
    print('激进深度优化7个源（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    optimizers = {
        21: try_idx21,
        24: try_idx24,
        30: try_idx30,
        36: try_idx36,
        39: try_idx39,
        55: try_idx55,
        58: try_idx58,
    }

    results = {}
    for idx, fn in optimizers.items():
        print(f'\n--- 激进优化 idx={idx} ---')
        if idx >= len(sources):
            continue
        try:
            r = fn(sources[idx])
            if r:
                print(f'  ✅ 成功: strategy={r["strategy"]}')
                # 应用优化
                s = sources[idx]
                old_url = s.get('sourceUrl', '')
                new_url = r['new_url']
                if new_url != old_url:
                    s['sourceUrl'] = new_url
                    print(f'  sourceUrl已更新: old_len={len(old_url)} new_len={len(new_url)}')
                results[idx] = r
            else:
                print(f'  ❌ 仍然失败')
                results[idx] = None
        except Exception as e:
            print(f'  ❌ 优化异常: exception:{type(e).__name__}')
            results[idx] = None

    # 汇总
    print('\n' + '=' * 70)
    print('激进深度优化汇总')
    print('=' * 70)
    success = [(idx, r) for idx, r in results.items() if r]
    print(f'\n成功: {len(success)}/{len(results)}')
    for idx, r in success:
        print(f'  [idx={idx}] strategy={r["strategy"]}')

    # 保存
    print(f'\n--- 保存最终JSON ---')
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'  路径: {OUTPUT_JSON}')
    print(f'  源数: {len(sources)}')

    # 保存报告
    report_path = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\aggressive_optimization_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'success_count': len(success),
            'total': len(results),
            'results': {str(k): v for k, v in results.items()},
        }, f, ensure_ascii=False, indent=2)
    print(f'  报告: {report_path}')


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')  # 屏蔽InsecureRequestWarning
    main()
