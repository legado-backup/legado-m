#!/usr/bin/env python3
"""deep_ssl_diagnose.py — SSL错误深度诊断（脱敏输出）

针对idx=30/36/46三个SSL失败源，深度诊断SSL握手失败的真实原因
针对idx=39，从Wayback存档提取主页URL
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
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def deep_ssl_diagnose(url):
    """深度诊断SSL错误"""
    if not url:
        return {'error': 'empty_url'}
    m = re.match(r'https?://([^/:]+)(?::(\d+))?(.*)', url)
    if not m:
        return {'error': 'invalid_url'}
    host = m.group(1)
    port = int(m.group(2)) if m.group(2) else (443 if url.startswith('https') else 80)
    result = {'host_len': len(host), 'port': port}

    # 测试1: TCP连接
    try:
        sock = socket.create_connection((host, port), timeout=10)
        sock.close()
        result['tcp'] = 'ok'
    except Exception as e:
        result['tcp'] = f'fail:exception:{type(e).__name__}'
        return result

    # 测试2: SSL握手（详细错误）
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # 尝试多种协议
        ctx.minimum_version = ssl.TLSVersion.TLSv1
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                result['ssl_handshake'] = 'ok'
                result['ssl_version'] = ssock.version()
                result['ssl_cipher'] = ssock.cipher()[0] if ssock.cipher() else 'None'
    except ssl.SSLError as e:
        err_msg = str(e)
        # 脱敏
        err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg, flags=re.IGNORECASE)
        result['ssl_handshake'] = f'fail:ssl_error'
        result['ssl_err_type'] = type(e).__name__
        result['ssl_err_msg_safe'] = err_msg_safe[:200]
    except Exception as e:
        err_msg = str(e)
        err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg, flags=re.IGNORECASE)
        result['ssl_handshake'] = f'fail:exception:{type(e).__name__}'
        result['err_msg_safe'] = err_msg_safe[:200]

    # 测试3: HTTP请求（完整错误）
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            result['http_status'] = resp.status
            result['http_len'] = len(resp.read())
    except urllib.error.HTTPError as e:
        result['http_status'] = e.code
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            result['http_err'] = 'ssl_error'
            # 捕获更详细的SSL错误
            if 'SSLV3_ALERT_HANDSHAKE_FAILURE' in reason:
                result['ssl_detail'] = 'handshake_failure'
            elif 'TLSV1_ALERT_PROTOCOL_VERSION' in reason:
                result['ssl_detail'] = 'protocol_version'
            elif 'WRONG_VERSION_NUMBER' in reason:
                result['ssl_detail'] = 'wrong_version'
            elif 'UNEXPECTED_EOF' in reason:
                result['ssl_detail'] = 'unexpected_eof'
            else:
                result['ssl_detail'] = 'unknown_ssl'
        else:
            result['http_err'] = 'other_url_error'
    except Exception as e:
        result['http_err'] = f'exception:{type(e).__name__}'

    return result


def fetch_wayback_for_idx39(url):
    """从Wayback存档提取idx=39的主页URL"""
    if not url:
        return {'error': 'empty_url'}
    try:
        api_url = f'https://archive.org/wayback/available?url={urllib.parse.quote(url)}'
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(api_url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closest = data.get('archived_snapshots', {}).get('closest', {})
            if closest.get('available'):
                snap_url = closest.get('url', '')
                snap_ts = closest.get('timestamp', '')
                # 访问存档
                req2 = urllib.request.Request(snap_url, headers={'User-Agent': UA})
                with urllib.request.urlopen(req2, timeout=20, context=ctx) as resp2:
                    html = resp2.read().decode('utf-8', errors='ignore')
                    return {
                        'snap_ts': snap_ts,
                        'html_len': len(html),
                        # 检查存档页面里有哪些候选主页URL
                        'has_home_link': '<a' in html and 'home' in html.lower(),
                        'has_index_link': 'href="/"' in html or 'href="index' in html.lower(),
                        'has_wayback_redirect': 'id="redirect"' in html,
                    }
            return {'error': 'no_snapshot'}
    except Exception as e:
        return {'error': f'exception:{type(e).__name__}'}


def main():
    print('=' * 70)
    print('SSL深度诊断+idx=39 Wayback查询（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    # SSL诊断（idx=30/36/46）
    print('\n--- SSL深度诊断 ---')
    for idx in [30, 36, 46]:
        if idx >= len(sources):
            continue
        s = sources[idx]
        url = s.get('sourceUrl', '')
        print(f'\n  [idx={idx}]')
        r = deep_ssl_diagnose(url)
        for k, v in r.items():
            print(f'    {k}: {v}')

    # idx=39 Wayback查询
    print('\n--- idx=39 Wayback存档查询 ---')
    if 39 < len(sources):
        s = sources[39]
        url = s.get('sourceUrl', '')
        print(f'\n  [idx=39] sourceUrl_len={len(url)}')
        r = fetch_wayback_for_idx39(url)
        for k, v in r.items():
            print(f'    {k}: {v}')

    # idx=58 内容深度分析（len=17是什么？）
    print('\n--- idx=58 内容深度分析 ---')
    if 58 < len(sources):
        s = sources[58]
        url = s.get('sourceUrl', '')
        print(f'\n  [idx=58] sourceUrl_len={len(url)}')
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                content = resp.read()
                print(f'    status: {resp.status}')
                print(f'    content_len: {len(content)}')
                # 脱敏后输出内容类型（不输出原文）
                try:
                    text = content.decode('utf-8', errors='ignore')
                    # 只输出技术特征
                    has_forbidden = 'forbidden' in text.lower()
                    has_block = 'block' in text.lower()
                    has_cloudflare = 'cloudflare' in text.lower()
                    has_redirect = '<meta http-equiv="refresh"' in text.lower() or 'window.location' in text
                    has_body = '<body' in text.lower()
                    print(f'    content_type: text/html')
                    print(f'    has_forbidden_keyword: {has_forbidden}')
                    print(f'    has_block_keyword: {has_block}')
                    print(f'    has_cloudflare_keyword: {has_cloudflare}')
                    print(f'    has_redirect_meta: {has_redirect}')
                    print(f'    has_body_tag: {has_body}')
                    # 提取所有链接（脱敏：只输出数量）
                    links = re.findall(r'href=["\']([^"\']+)["\']', text)
                    print(f'    link_count: {len(links)}')
                    if links:
                        # 检查链接类型
                        http_links = [l for l in links if l.startswith('http')]
                        abs_links = [l for l in links if l.startswith('/')]
                        print(f'    http_links: {len(http_links)}')
                        print(f'    abs_links: {len(abs_links)}')
                except Exception as e:
                    print(f'    decode_error: exception:{type(e).__name__}')
        except Exception as e:
            err = str(e)
            err_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err, flags=re.IGNORECASE)
            print(f'    fetch_error: exception:{type(e).__name__} msg={err_safe[:200]}')


if __name__ == '__main__':
    main()
