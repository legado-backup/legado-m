#!/usr/bin/env python3
"""quick_dns_check.py — 快速DNS可达性对比测试

对比7个失败源在脚本侧 vs 真机侧的DNS解析状态
输出技术指标（不输出业务字段）
"""
import json
import re
import socket
import ssl
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
NEEDS_LOGIN_IDX = [21, 24, 30, 36, 39, 55, 58]


def sanitize(text):
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'https?://[^\s"\']+', '[URL]', s)
    s = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', s)
    s = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', s, flags=re.IGNORECASE)
    return s[:200]


def check_dns(url):
    """检查URL的DNS解析"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        # DNS解析
        try:
            addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            addr_list = list(set([a[4][0] for a in addrs]))
            return {
                'dns_status': 'resolved',
                'addr_count': len(addr_list),
                'addr_type': 'IPv4' if any('.' in a for a in addr_list) else 'IPv6',
            }
        except socket.gaierror as e:
            return {
                'dns_status': 'failed',
                'error': f'gaierror:{e.errno}',
                'error_msg': sanitize(str(e)),
            }
    except Exception as e:
        return {
            'dns_status': 'error',
            'error': type(e).__name__,
            'error_msg': sanitize(str(e)),
        }


def check_http(url, timeout=15):
    """检查HTTP可达性"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read(2048)
            return {
                'http_status': resp.status,
                'content_len': len(content),
                'content_type': resp.headers.get('Content-Type', '')[:50],
            }
    except urllib.error.HTTPError as e:
        return {
            'http_status': e.code,
            'error': f'HTTPError:{e.code}',
        }
    except urllib.error.URLError as e:
        reason = str(e.reason)
        return {
            'http_status': -1,
            'error': type(e).__name__,
            'error_msg': sanitize(reason)[:100],
        }
    except Exception as e:
        return {
            'http_status': -1,
            'error': type(e).__name__,
            'error_msg': sanitize(str(e))[:100],
        }


def main():
    print('=' * 70)
    print('DNS+HTTP可达性对比测试（脱敏）')
    print('=' * 70)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f'JSON源数: {len(sources)}')
    print()

    results = []
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        source_url = sources[idx].get('sourceUrl', '')
        url_len = len(source_url)
        is_http = source_url.startswith('http')

        print(f'--- idx={idx} url_len={url_len} is_http={is_http} ---')

        if not is_http:
            print(f'  跳过：非http URL')
            results.append({'idx': idx, 'status': 'invalid_url'})
            continue

        # 1. DNS解析
        dns = check_dns(source_url)
        print(f'  DNS: {dns}')

        # 2. HTTP可达性
        http = check_http(source_url, timeout=10)
        print(f'  HTTP: {http}')

        # 判定
        if dns.get('dns_status') == 'failed':
            status = 'dns_failed'
        elif http.get('http_status') == 200 and http.get('content_len', 0) > 1000:
            status = 'http_ok'
        elif http.get('http_status') in (403, 401):
            status = 'http_forbidden'
        elif http.get('http_status') >= 500:
            status = 'http_server_error'
        elif http.get('http_status') == 206:
            status = 'http_file_download'
        else:
            status = 'http_failed'

        results.append({
            'idx': idx,
            'url_len': url_len,
            'dns': dns,
            'http': http,
            'status': status,
        })
        print(f'  状态: {status}')
        print()

    # 汇总
    print('=' * 70)
    print('汇总')
    print('=' * 70)
    for r in results:
        idx = r.get('idx', -1)
        status = r.get('status', 'unknown')
        dns_s = r.get('dns', {}).get('dns_status', 'unknown')
        http_s = r.get('http', {}).get('http_status', 'unknown')
        print(f'  [idx={idx}] status={status} dns={dns_s} http={http_s}')


if __name__ == '__main__':
    main()
