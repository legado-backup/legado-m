#!/usr/bin/env python3
"""targeted_retry.py — 针对性优化（脱敏输出）

针对SSL诊断发现的特定问题：
- idx=30: 端口2666非标准，尝试 https://domain/ 和 http://domain:2666/
- idx=36: SSL握手成功但HTTP失败，强制HTTP/1.1
- idx=46: 端口443连接重置，尝试 http:// (降级)
- idx=39: 直接用Wayback API重试
"""
import json
import os
import re
import sys
import socket
import ssl
import http.client
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def http11_get(url, timeout=15):
    """强制HTTP/1.1 GET请求"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == 'https':
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout, context=ctx)
    else:
        conn = http.client.HTTPConnection(parsed.netloc, timeout=timeout)
    try:
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        conn.request('GET', path, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        resp = conn.getresponse()
        data = resp.read()
        return (resp.status, len(data), None)
    except Exception as e:
        err = str(e)
        err_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err, flags=re.IGNORECASE)
        return (0, 0, f'exception:{type(e).__name__}:{err_safe[:100]}')
    finally:
        conn.close()


def try_idx30(source):
    """idx=30: 端口2666，尝试改用80/443"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=30] sourceUrl_len={len(source_url)}')

    # 提取domain
    m = re.match(r'https?://([^/:]+)', source_url)
    if not m:
        print(f'    无法提取domain')
        return None
    domain = m.group(1)

    # 尝试https://domain/ (标准443端口)
    url1 = f'https://{domain}/'
    s1, l1, e1 = http11_get(url1, timeout=15)
    print(f'    [https://domain/] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': url1, 'strategy': 'https_443'}

    # 尝试http://domain/ (80端口)
    url2 = f'http://{domain}/'
    s2, l2, e2 = http11_get(url2, timeout=15)
    print(f'    [http://domain/] status={s2} len={l2} err={e2}')
    if s2 == 200 and l2 > 500:
        return {'new_url': url2, 'strategy': 'http_80'}

    # 尝试http://domain:2666/ (原端口但HTTP)
    url3 = f'http://{domain}:2666/'
    s3, l3, e3 = http11_get(url3, timeout=15)
    print(f'    [http://domain:2666/] status={s3} len={l3} err={e3}')
    if s3 == 200 and l3 > 500:
        return {'new_url': url3, 'strategy': 'http_2666'}

    return None


def try_idx36(source):
    """idx=36: 强制HTTP/1.1"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=36] sourceUrl_len={len(source_url)}')

    # 强制HTTP/1.1
    s1, l1, e1 = http11_get(source_url, timeout=20)
    print(f'    [http11_get] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': source_url, 'strategy': 'http11'}

    # 尝试http降级
    if source_url.startswith('https://'):
        url2 = 'http://' + source_url[len('https://'):]
        s2, l2, e2 = http11_get(url2, timeout=15)
        print(f'    [http_downgrade] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': url2, 'strategy': 'http_downgrade'}

    return None


def try_idx46(source):
    """idx=46: 端口443重置，尝试HTTP降级+其他端口"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=46] sourceUrl_len={len(source_url)}')

    # HTTP降级
    if source_url.startswith('https://'):
        url1 = 'http://' + source_url[len('https://'):]
        s1, l1, e1 = http11_get(url1, timeout=15)
        print(f'    [http_downgrade] status={s1} len={l1} err={e1}')
        if s1 == 200 and l1 > 500:
            return {'new_url': url1, 'strategy': 'http_downgrade'}

    # 尝试根域名
    m = re.match(r'(https?://[^/]+)', source_url)
    if m:
        root_url = m.group(1) + '/'
        s2, l2, e2 = http11_get(root_url, timeout=15)
        print(f'    [root_domain] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': root_url, 'strategy': 'root_domain'}

    return None


def try_idx39(source):
    """idx=39: Wayback存档查询主页URL"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=39] sourceUrl_len={len(source_url)}')

    # 提取domain，查询Wayback是否有存档
    m = re.match(r'https?://([^/:]+)', source_url)
    if not m:
        return None
    domain = m.group(1)

    # 尝试查询domain根目录的存档
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        api_url = f'https://archive.org/wayback/available?url={domain}'
        req = urllib.request.Request(api_url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closest = data.get('archived_snapshots', {}).get('closest', {})
            if closest.get('available'):
                snap_url = closest.get('url', '')
                snap_ts = closest.get('timestamp', '')
                print(f'    [wayback] snap_ts={snap_ts}')
                # 访问存档
                s2, l2, e2 = http11_get(snap_url, timeout=20)
                print(f'    [snap_content] status={s2} len={l2} err={e2}')
                if s2 == 200 and l2 > 500:
                    return {'new_url': source_url, 'strategy': 'wayback_verified', 'snap_ts': snap_ts}
            else:
                print(f'    [wayback] no_snapshot')
    except Exception as e:
        err = str(e)
        err_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err, flags=re.IGNORECASE)
        print(f'    [wayback_error] exception:{type(e).__name__} msg={err_safe[:100]}')

    return None


def try_idx1(source):
    """idx=1: RemoteDisconnected，重试+HTTP降级"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=1] sourceUrl_len={len(source_url)}')

    # 重试3次
    for i in range(3):
        s, l, e = http11_get(source_url, timeout=20)
        print(f'    [retry{i+1}] status={s} len={l} err={e}')
        if s == 200 and l > 500:
            return {'new_url': source_url, 'strategy': f'retry_success_{i+1}'}
        # HTTP降级
        if source_url.startswith('https://'):
            url2 = 'http://' + source_url[len('https://'):]
            s2, l2, e2 = http11_get(url2, timeout=20)
            print(f'    [retry{i+1}_http] status={s2} len={l2} err={e2}')
            if s2 == 200 and l2 > 500:
                return {'new_url': url2, 'strategy': 'http_downgrade'}

    return None


def try_idx21(source):
    """idx=21: HTTP 500，尝试URL参数变化"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=21] sourceUrl_len={len(source_url)}')

    # HTTP降级
    if source_url.startswith('https://'):
        url1 = 'http://' + source_url[len('https://'):]
        s1, l1, e1 = http11_get(url1, timeout=15)
        print(f'    [http_downgrade] status={s1} len={l1} err={e1}')
        if s1 == 200 and l1 > 500:
            return {'new_url': url1, 'strategy': 'http_downgrade'}

    # 根域名
    m = re.match(r'(https?://[^/]+)', source_url)
    if m:
        root_url = m.group(1) + '/'
        s2, l2, e2 = http11_get(root_url, timeout=15)
        print(f'    [root_domain] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': root_url, 'strategy': 'root_domain'}

    return None


def try_idx55(source):
    """idx=55: timeout，长timeout重试"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=55] sourceUrl_len={len(source_url)}')

    # 长timeout
    s1, l1, e1 = http11_get(source_url, timeout=40)
    print(f'    [40s_timeout] status={s1} len={l1} err={e1}')
    if s1 == 200 and l1 > 500:
        return {'new_url': source_url, 'strategy': 'long_timeout'}

    # HTTP降级
    if source_url.startswith('https://'):
        url2 = 'http://' + source_url[len('https://'):]
        s2, l2, e2 = http11_get(url2, timeout=40)
        print(f'    [40s_http] status={s2} len={l2} err={e2}')
        if s2 == 200 and l2 > 500:
            return {'new_url': url2, 'strategy': 'http_downgrade'}

    return None


def try_idx24(source):
    """idx=24: HTTP 403，尝试多种UA+Referer"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=24] sourceUrl_len={len(source_url)}')

    # 多种UA组合
    ua_list = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    ]
    for i, ua in enumerate(ua_list):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(source_url, headers={
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': source_url,
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
                print(f'    [ua{i+1}] status={resp.status} len={len(data)}')
                if resp.status == 200 and len(data) > 500:
                    return {'new_url': source_url, 'strategy': f'ua_{i+1}'}
        except Exception as e:
            print(f'    [ua{i+1}] exception:{type(e).__name__}')

    return None


def main():
    print('=' * 70)
    print('针对性优化（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    optimizers = {
        1: try_idx1,
        21: try_idx21,
        24: try_idx24,
        30: try_idx30,
        36: try_idx36,
        39: try_idx39,
        46: try_idx46,
        55: try_idx55,
    }

    results = {}
    for idx, fn in optimizers.items():
        print(f'\n--- 优化 idx={idx} ---')
        if idx >= len(sources):
            continue
        r = fn(sources[idx])
        if r:
            print(f'  ✅ 成功: strategy={r["strategy"]}')
            results[idx] = r
        else:
            print(f'  ❌ 失败')
            results[idx] = None

    # 汇总
    print('\n' + '=' * 70)
    print('针对性优化汇总')
    print('=' * 70)
    success = [(idx, r) for idx, r in results.items() if r]
    print(f'\n成功: {len(success)}/{len(results)}')
    for idx, r in success:
        print(f'  [idx={idx}] strategy={r["strategy"]}')

    # 保存结果
    out_path = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\targeted_retry_report.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'success_count': len(success),
            'total': len(results),
            'results': {str(k): v for k, v in results.items()},
        }, f, ensure_ascii=False, indent=2)
    print(f'\n详细报告: {out_path}')


if __name__ == '__main__':
    main()
