#!/usr/bin/env python3
"""deep_retry_failed_sources.py — 深度重试10个失败源（脱敏输出）

10个失败源（idx）: 1, 21, 24, 30, 36, 39, 46, 55, 58, 60(已优化但再确认)

尝试7种技术手段：
1. 多种UA（Chrome/Mobile/Bot）
2. 多种HTTP方法（GET/HEAD）
3. Wayback Machine存档查询
4. HTTP/1.1强制（避免HTTP/2错误）
5. 跳过SSL+Chrome UA
6. 尝试根域名（去掉路径）
7. 域名whois/DNS查询

输出：idx + 技术指标（status/length/err/final_strategy），不输出业务字段
"""
import json
import os
import re
import sys
import socket
import ssl
import urllib.request
import urllib.error
import urllib.parse
import http.client
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'

FAILED_IDX = [1, 21, 24, 30, 36, 39, 46, 55, 58, 60]

# 多种UA
UA_LIST = {
    'chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'bot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'firefox': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
}


def check_url_multi(url, ua='chrome', method='GET', timeout=20, follow_redirect=True):
    """多种方式访问URL"""
    if not url:
        return (0, 0, 'empty_url', '')
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        headers = {
            'User-Agent': UA_LIST.get(ua, UA_LIST['chrome']),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
        req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            final_url = resp.geturl()
            return (resp.status, len(data), None, final_url)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}', '')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            return (0, 0, 'ssl_error', '')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, 0, 'timeout', '')
        if 'Connection refused' in reason or 'RemoteDisconnected' in reason:
            return (0, 0, 'connection_refused', '')
        if 'Name or service' in reason or 'getaddrinfo' in reason:
            return (0, 0, 'dns_fail', '')
        if 'HTTP2' in reason or 'PROTOCOL' in reason:
            return (0, 0, 'http2_error', '')
        return (0, 0, 'url_error', '')
    except socket.timeout:
        return (0, 0, 'timeout', '')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}', '')


def check_wayback(url):
    """查询Wayback Machine存档"""
    if not url:
        return (0, 0, 'empty_url', '')
    try:
        # Wayback API: http://archive.org/wayback/available?url=xxx
        api_url = f'https://archive.org/wayback/available?url={urllib.parse.quote(url)}'
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(api_url, headers={
            'User-Agent': UA_LIST['chrome'],
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            snapshots = data.get('archived_snapshots', {})
            closest = snapshots.get('closest', {})
            if closest and closest.get('available'):
                snap_url = closest.get('url', '')
                snap_ts = closest.get('timestamp', '')
                # 访问存档
                status, clen, err, _ = check_url_multi(snap_url, ua='chrome', timeout=20)
                return (status, clen, err, f'wayback_ts={snap_ts}')
            return (0, 0, 'no_snapshot', '')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}', '')


def check_root_domain(url):
    """访问域名根（去掉路径）"""
    if not url:
        return (0, 0, 'empty_url', '')
    m = re.match(r'(https?://[^/]+)', url)
    if not m:
        return (0, 0, 'invalid_url', '')
    root = m.group(1) + '/'
    return check_url_multi(root, ua='chrome', timeout=15)


def check_http_method(url, method='HEAD'):
    """尝试不同HTTP方法"""
    return check_url_multi(url, ua='chrome', method=method, timeout=15)


def analyze_source(idx, source):
    """对单个失败源尝试所有技术手段"""
    source_url = source.get('sourceUrl', '')
    print(f'\n  [idx={idx}] sourceUrl_len={len(source_url)} is_http={source_url.startswith("http")}')

    if not source_url.startswith('http'):
        print(f'    跳过: sourceUrl非http（占位符或JS双层加密）')
        return {'idx': idx, 'final_strategy': 'skip_non_http', 'best_status': 0}

    best = {'status': 0, 'length': 0, 'strategy': None, 'err': 'all_fail'}

    # 测试1: Chrome UA (基线)
    s1, l1, e1, _ = check_url_multi(source_url, ua='chrome', timeout=20)
    print(f'    [chrome_ua] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 1000:
        best = {'status': s1, 'length': l1, 'strategy': 'chrome_ua', 'err': None}

    # 测试2: Mobile UA
    s2, l2, e2, _ = check_url_multi(source_url, ua='mobile', timeout=20)
    print(f'    [mobile_ua] status={s2} len={l2} err={e2}')
    if s2 == 200 and l2 > 1000 and best['status'] == 0:
        best = {'status': s2, 'length': l2, 'strategy': 'mobile_ua', 'err': None}

    # 测试3: Bot UA
    s3, l3, e3, _ = check_url_multi(source_url, ua='bot', timeout=20)
    print(f'    [bot_ua] status={s3} len={l3} err={e3}')
    if s3 == 200 and l3 > 1000 and best['status'] == 0:
        best = {'status': s3, 'length': l3, 'strategy': 'bot_ua', 'err': None}

    # 测试4: Firefox UA
    s4, l4, e4, _ = check_url_multi(source_url, ua='firefox', timeout=20)
    print(f'    [firefox_ua] status={s4} len={l4} err={e4}')
    if s4 == 200 and l4 > 1000 and best['status'] == 0:
        best = {'status': s4, 'length': l4, 'strategy': 'firefox_ua', 'err': None}

    # 测试5: HEAD方法
    s5, l5, e5, _ = check_http_method(source_url, method='HEAD')
    print(f'    [head_method] status={s5} len={l5} err={e5}')
    if s5 in (200, 301, 302) and best['status'] == 0:
        best = {'status': s5, 'length': l5, 'strategy': 'head_method', 'err': None}

    # 测试6: 域名根
    s6, l6, e6, _ = check_root_domain(source_url)
    print(f'    [root_domain] status={s6} len={l6} err={e6}')
    if s6 == 200 and l6 > 1000 and best['status'] == 0:
        best = {'status': s6, 'length': l6, 'strategy': 'root_domain', 'err': None}

    # 测试7: Wayback Machine存档
    s7, l7, e7, info7 = check_wayback(source_url)
    print(f'    [wayback] status={s7} len={l7} err={e7} info={info7}')
    if s7 == 200 and l7 > 1000 and best['status'] == 0:
        best = {'status': s7, 'length': l7, 'strategy': 'wayback', 'err': None}

    return {
        'idx': idx,
        'chrome_ua': {'status': s1, 'err': e1},
        'mobile_ua': {'status': s2, 'err': e2},
        'bot_ua': {'status': s3, 'err': e3},
        'firefox_ua': {'status': s4, 'err': e4},
        'head_method': {'status': s5, 'err': e5},
        'root_domain': {'status': s6, 'err': e6},
        'wayback': {'status': s7, 'err': e7, 'info': info7},
        'best_status': best['status'],
        'best_length': best['length'],
        'best_strategy': best['strategy'],
        'best_err': best['err'],
        'final_strategy': best['strategy'] if best['status'] >= 200 else 'truly_dead',
    }


def main():
    print('=' * 70)
    print('深度重试10个失败源（脱敏：只输出技术指标）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    results = []
    for idx in FAILED_IDX:
        if idx >= len(sources):
            continue
        r = analyze_source(idx, sources[idx])
        results.append(r)

    # 汇总
    print('\n' + '=' * 70)
    print('深度重试汇总')
    print('=' * 70)
    success = [r for r in results if r.get('best_status', 0) >= 200]
    fail = [r for r in results if r.get('best_status', 0) < 200]
    print(f'\n  可救活: {len(success)}/{len(results)}')
    print(f'  真正失败: {len(fail)}/{len(results)}')

    if success:
        print('\n--- 可救活源（按策略）---')
        for r in success:
            print(f"  [idx={r['idx']}] strategy={r['best_strategy']} status={r['best_status']} len={r['best_length']}")

    if fail:
        print('\n--- 真正失败源（按失败原因）---')
        for r in fail:
            print(f"  [idx={r['idx']}] chrome_err={r.get('chrome_ua', {}).get('err')} root_err={r.get('root_domain', {}).get('err')}")

    # 保存报告
    out_path = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\deep_retry_report.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(results),
            'success_count': len(success),
            'fail_count': len(fail),
            'results': results,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n详细报告: {out_path}')


if __name__ == '__main__':
    main()
