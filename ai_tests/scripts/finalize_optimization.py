#!/usr/bin/env python3
"""finalize_optimization.py — 最终优化收尾（脱敏输出）

3项任务：
1. 标记剩余7个失败源 idx=1/21/30/36/46/55/58 为 truly_dead
2. 尝试优化 idx=24（Navigation interrupted - 可能重定向）
3. 尝试优化 idx=39（Download is starting - sourceUrl可能指向文件）

输出：只输出idx + 技术指标，不输出业务字段原文
"""
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
import ssl
from urllib.parse import urlparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 输入/输出路径
INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v3.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 已确认失败的7个源（网络层/反爬，自动无法优化）
TRULY_DEAD_IDX = [1, 21, 30, 36, 46, 55, 58]
# 需尝试优化的2个源
RETRY_IDX = [24, 39]


def sanitize(text):
    """脱敏：替换URL/域名为代号"""
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'https?://[^\s"\']+', '[URL]', s)
    s = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', s, flags=re.IGNORECASE)
    return s[:200]


def check_url(url, timeout=20, allow_redirect=True):
    """URL检查（跳过SSL，允许重定向跟踪）"""
    if not url:
        return (0, 0, 'empty_url', '')
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
        })
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
        return (0, 0, 'url_error', '')
    except socket.timeout:
        return (0, 0, 'timeout', '')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}', '')


def extract_domains_from_html(html_text):
    """从HTML中提取候选域名（脱敏：只返回域名数量）"""
    # 匹配"备用域名：xxx"和"最新域名获取地址：URL"
    domain_pattern = r'(?:备用域名|备用地址|新地址|新域名)[：:\s]*([a-zA-Z0-9\-\.]+(?:\.[a-zA-Z]{2,})+)'
    url_pattern = r'(?:最新域名获取地址|最新地址|获取地址|域名发布页)[：:\s]*(https?://[^\s<"\'<>]+)'
    domains = re.findall(domain_pattern, html_text, flags=re.IGNORECASE)
    urls = re.findall(url_pattern, html_text, flags=re.IGNORECASE)
    return domains, urls


def extract_fields_from_html(html_text, base_url):
    """从HTML提取searchUrl/sortUrl/sourceIcon等技术字段（脱敏）"""
    fields = {}
    # sourceIcon: <link rel="icon" href="..."> 或 <link rel="shortcut icon" href="...">
    icon_match = re.search(r'<link[^>]*rel=["\']?(?:shortcut )?icon["\']?[^>]*href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)
    if icon_match:
        icon = icon_match.group(1)
        if icon.startswith('http'):
            fields['sourceIcon'] = icon
        elif icon.startswith('/'):
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                fields['sourceIcon'] = m.group(1) + icon
    # searchUrl: form action
    form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)
    if form_match:
        action = form_match.group(1)
        if action.startswith('http'):
            fields['searchUrl'] = action + ',{{key}}'
        elif action.startswith('/'):
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                fields['searchUrl'] = m.group(1) + action + ',{{key}}'
    return fields


def try_optimize_idx24(source):
    """idx=24: Navigation interrupted - 尝试跟随重定向"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=24] sourceUrl_len={len(source_url)}')

    # 测试原始URL
    status, clen, err, final_url = check_url(source_url, timeout=20)
    print(f'    测试原URL: status={status} len={clen} err={err} final_changed={final_url != source_url if final_url else False}')

    if status == 200 and clen > 1000:
        print(f'    原URL可达，提取字段')
        try:
            resp_data = urllib.request.urlopen(
                urllib.request.Request(source_url, headers={'User-Agent': CHROME_UA}),
                timeout=20, context=ssl._create_unverified_context()
            ).read().decode('utf-8', errors='ignore')
            fields = extract_fields_from_html(resp_data, source_url)
            print(f'    提取字段数: {len(fields)}')
            return fields
        except Exception as e:
            print(f'    提取异常: exception:{type(e).__name__}')
            return {}
    elif final_url and final_url != source_url:
        # 重定向到新URL
        print(f'    检测到重定向，测试最终URL')
        status2, clen2, err2, _ = check_url(final_url, timeout=20)
        print(f'    最终URL测试: status={status2} len={clen2} err={err2}')
        if status2 == 200 and clen2 > 1000:
            try:
                resp_data = urllib.request.urlopen(
                    urllib.request.Request(final_url, headers={'User-Agent': CHROME_UA}),
                    timeout=20, context=ssl._create_unverified_context()
                ).read().decode('utf-8', errors='ignore')
                fields = extract_fields_from_html(resp_data, final_url)
                if fields:
                    fields['_new_sourceUrl'] = final_url
                    print(f'    提取字段数: {len(fields)} (含新sourceUrl)')
                    return fields
            except Exception as e:
                print(f'    提取异常: exception:{type(e).__name__}')
    return {}


def try_optimize_idx39(source):
    """idx=39: Download is starting - sourceUrl可能指向文件，尝试访问域名根"""
    source_url = source.get('sourceUrl', '')
    print(f'  [idx=39] sourceUrl_len={len(source_url)}')

    # 测试原始URL
    status, clen, err, _ = check_url(source_url, timeout=20)
    print(f'    测试原URL: status={status} len={clen} err={err}')

    # 尝试访问域名根（去掉路径）
    m = re.match(r'(https?://[^/]+)', source_url)
    if m:
        root_url = m.group(1) + '/'
        print(f'    尝试域名根: root_len={len(root_url)}')
        status2, clen2, err2, _ = check_url(root_url, timeout=20)
        print(f'    域名根测试: status={status2} len={clen2} err={err2}')
        if status2 == 200 and clen2 > 1000:
            try:
                resp_data = urllib.request.urlopen(
                    urllib.request.Request(root_url, headers={'User-Agent': CHROME_UA}),
                    timeout=20, context=ssl._create_unverified_context()
                ).read().decode('utf-8', errors='ignore')
                fields = extract_fields_from_html(resp_data, root_url)
                if fields:
                    fields['_new_sourceUrl'] = root_url
                    print(f'    提取字段数: {len(fields)} (含新sourceUrl=域名根)')
                    return fields
                else:
                    print(f'    提取字段数: 0')
            except Exception as e:
                print(f'    提取异常: exception:{type(e).__name__}')
    return {}


def mark_truly_dead(sources):
    """标记7个失败源为truly_dead"""
    print('\n--- 任务1: 标记7个失败源为truly_dead ---')
    marked = 0
    for idx in TRULY_DEAD_IDX:
        if idx >= len(sources):
            continue
        s = sources[idx]
        # 检查是否已标记
        comment = s.get('sourceComment', '') or ''
        if 'AI_DIAGNOSIS:truly_dead' in comment:
            print(f'  [idx={idx}] 已标记，跳过')
            continue
        # 追加诊断标记
        diagnosis = '[AI_DIAGNOSIS:truly_dead|建议删除-网络层不可达或反爬拦截]'
        new_comment = (comment + '\n' + diagnosis) if comment else diagnosis
        s['sourceComment'] = new_comment
        print(f'  [idx={idx}] 已追加诊断标记')
        marked += 1
    print(f'  共标记: {marked} 个')
    return marked


def main():
    print('=' * 70)
    print('最终优化收尾（脱敏输出）')
    print('=' * 70)

    # 加载JSON
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'\n加载源数: {len(sources)}')

    # 任务1: 标记truly_dead
    marked_count = mark_truly_dead(sources)

    # 任务2+3: 尝试优化idx=24/39
    print('\n--- 任务2: 尝试优化 idx=24 ---')
    if 24 < len(sources):
        new_fields_24 = try_optimize_idx24(sources[24])
        if new_fields_24:
            new_url = new_fields_24.pop('_new_sourceUrl', None)
            if new_url:
                sources[24]['sourceUrl'] = new_url
                print(f'    更新sourceUrl: new_len={len(new_url)}')
            for k, v in new_fields_24.items():
                if v and (not sources[24].get(k) or len(sources[24].get(k, '')) < len(v)):
                    sources[24][k] = v
                    print(f'    更新{ k}: new_len={len(v)}')

    print('\n--- 任务3: 尝试优化 idx=39 ---')
    if 39 < len(sources):
        new_fields_39 = try_optimize_idx39(sources[39])
        if new_fields_39:
            new_url = new_fields_39.pop('_new_sourceUrl', None)
            if new_url:
                sources[39]['sourceUrl'] = new_url
                print(f'    更新sourceUrl: new_len={len(new_url)}')
            for k, v in new_fields_39.items():
                if v and (not sources[39].get(k) or len(sources[39].get(k, '')) < len(v)):
                    sources[39][k] = v
                    print(f'    更新{ k}: new_len={len(v)}')

    # 保存最终JSON
    print(f'\n--- 保存最终JSON ---')
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'  路径: {OUTPUT_JSON}')
    print(f'  源数: {len(sources)}')

    # 汇总
    print('\n' + '=' * 70)
    print('汇总')
    print('=' * 70)
    print(f'  标记truly_dead: {marked_count} 个')
    print(f'  idx=24优化: {"成功" if new_fields_24 else "失败-保留原状"}')
    print(f'  idx=39优化: {"成功" if new_fields_39 else "失败-保留原状"}')
    print(f'  最终JSON: {OUTPUT_JSON}')


if __name__ == "__main__":
    main()
