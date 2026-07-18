#!/usr/bin/env python3
"""final_optimize_3_sources.py — 最终优化3个可救源（脱敏）

- idx=46: HTTP降级成功，需要提取4字段
- idx=36: 跟随301重定向到最终URL
- idx=21: 跟随301重定向到最终URL
"""
import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v5.json'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def fetch_with_redirects(url, timeout=20):
    """跟随重定向访问URL，返回最终URL+HTML"""
    if not url:
        return None, 0, 0, 'empty_url'
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            return resp.geturl(), resp.status, len(data), None
    except urllib.error.HTTPError as e:
        return url, e.code, 0, f'http_{e.code}'
    except Exception as e:
        return url, 0, 0, f'exception:{type(e).__name__}'


def fetch_html(url, timeout=20):
    """获取HTML内容（不输出业务字段）"""
    if not url:
        return None
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None


def extract_fields(html, base_url):
    """从HTML提取4字段（脱敏：不输出业务字段原文）"""
    if not html:
        return {}
    fields = {}

    # sourceIcon: <link rel="icon" href="...">
    icon_match = re.search(r'<link[^>]*rel=["\']?(?:shortcut )?icon["\']?[^>]*href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if icon_match:
        icon = icon_match.group(1)
        if icon.startswith('http'):
            fields['sourceIcon'] = icon
        elif icon.startswith('/'):
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                fields['sourceIcon'] = m.group(1) + icon
        elif icon.startswith('./'):
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                fields['sourceIcon'] = m.group(1) + icon[1:]

    # searchUrl: form action
    form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if form_match:
        action = form_match.group(1)
        if action.startswith('http'):
            fields['searchUrl'] = action + ',{{key}}'
        elif action.startswith('/'):
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                fields['searchUrl'] = m.group(1) + action + ',{{key}}'

    # ruleNextPage: 找下一页链接
    next_patterns = [
        r'<a[^>]*class=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*下一页',
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*Next',
    ]
    for pattern in next_patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            next_url = match.group(1)
            if next_url.startswith('/'):
                m = re.match(r'(https?://[^/]+)', base_url)
                if m:
                    fields['ruleNextPage'] = m.group(1) + next_url + '@href'
            elif next_url.startswith('http'):
                fields['ruleNextPage'] = next_url + '@href'
            break

    return fields


def main():
    print('=' * 70)
    print('最终优化3个可救源（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    optimized = 0

    # idx=46: HTTP降级（https→http）
    print('\n--- idx=46: HTTP降级优化 ---')
    if 46 < len(sources):
        s = sources[46]
        old_url = s.get('sourceUrl', '')
        if old_url.startswith('https://'):
            new_url = 'http://' + old_url[len('https://'):]
            print(f'  原URL_len={len(old_url)} 新URL_len={len(new_url)}')
            final_url, status, length, err = fetch_with_redirects(new_url)
            print(f'  fetch: final_url_changed={final_url != new_url if final_url else "N/A"} status={status} len={length} err={err}')
            if status == 200 and length > 500:
                # 提取字段
                html = fetch_html(new_url)
                fields = extract_fields(html, new_url)
                print(f'  提取字段数: {len(fields)}')
                # 更新sourceUrl
                s['sourceUrl'] = new_url
                print(f'  更新sourceUrl: http降级')
                # 更新其他字段
                for k, v in fields.items():
                    if v and (not s.get(k) or len(str(s.get(k, ''))) < len(str(v))):
                        s[k] = v
                        print(f'  更新{ k}: len={len(str(v))}')
                optimized += 1

    # idx=36: 跟随重定向
    print('\n--- idx=36: 跟随重定向 ---')
    if 36 < len(sources):
        s = sources[36]
        old_url = s.get('sourceUrl', '')
        print(f'  原URL_len={len(old_url)}')
        final_url, status, length, err = fetch_with_redirects(old_url, timeout=25)
        print(f'  fetch: final_url_changed={final_url != old_url if final_url else "N/A"} status={status} len={length} err={err}')
        if status == 200 and length > 500:
            # 提取字段
            html = fetch_html(final_url)
            fields = extract_fields(html, final_url)
            print(f'  提取字段数: {len(fields)}')
            if final_url != old_url:
                s['sourceUrl'] = final_url
                print(f'  更新sourceUrl: 跟随重定向')
                optimized += 1
            for k, v in fields.items():
                if v and (not s.get(k) or len(str(s.get(k, ''))) < len(str(v))):
                    s[k] = v
                    print(f'  更新{ k}: len={len(str(v))}')

    # idx=21: 跟随重定向
    print('\n--- idx=21: 跟随重定向 ---')
    if 21 < len(sources):
        s = sources[21]
        old_url = s.get('sourceUrl', '')
        print(f'  原URL_len={len(old_url)}')
        final_url, status, length, err = fetch_with_redirects(old_url, timeout=25)
        print(f'  fetch: final_url_changed={final_url != old_url if final_url else "N/A"} status={status} len={length} err={err}')
        if status == 200 and length > 500:
            # 提取字段
            html = fetch_html(final_url)
            fields = extract_fields(html, final_url)
            print(f'  提取字段数: {len(fields)}')
            if final_url != old_url:
                s['sourceUrl'] = final_url
                print(f'  更新sourceUrl: 跟随重定向')
                optimized += 1
            for k, v in fields.items():
                if v and (not s.get(k) or len(str(s.get(k, ''))) < len(str(v))):
                    s[k] = v
                    print(f'  更新{ k}: len={len(str(v))}')

    # 保存
    print(f'\n--- 保存最终JSON ---')
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'  路径: {OUTPUT_JSON}')
    print(f'  优化数: {optimized}')


if __name__ == '__main__':
    main()
