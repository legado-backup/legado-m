#!/usr/bin/env python3
"""deep_optimize_failures.py — 深度优化失败源（脱敏输出）

对 v2 验证 scenario_1_list_load 失败的 10 个源：
1. 用多种策略访问 sourceUrl（Chrome UA + SSL跳过 + 长 timeout + Referer）
2. 提取 HTML 结构（favicon/searchForm/categoryLinks/pagination）
3. 生成修复后的字段值
4. 输出纯技术指标（禁止业务字段原文）

输出：idx + 修复策略 + 字段长度 + is_valid 校验
不输出：URL/源名称/域名/cookie内容
"""
import json
import re
import sys
import socket
import urllib.request
import urllib.error
import ssl
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 失败 idx 列表（scenario_1_list_load 失败）
FAILED_IDX = [1, 21, 24, 30, 36, 39, 46, 55, 58, 60]

INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'
OUTPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final_v3.json'

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def extract_base_url(source_url):
    """从 sourceUrl 提取 base_url（脚本内部用，不输出）"""
    if not source_url or not source_url.startswith('http'):
        return ''
    # 去掉 {{...}} 模板
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    # 提取协议+域名
    m = re.match(r'(https?://[^/]+)', base)
    return m.group(1) + '/' if m else ''


def fetch_html(url, timeout=20):
    """多种策略访问URL，返回 (status, html_len, strategy, err)
    
    策略顺序：
    1. Chrome UA + SSL跳过 + Referer
    2. HTTP降级
    3. 长 timeout 30s
    """
    if not url:
        return (0, 0, 'none', 'empty_url')
    
    strategies = [
        ('chrome_ssl_skip', lambda u: _fetch(u, timeout=timeout, ssl_skip=True, ua=CHROME_UA, referer=u)),
        ('http_downgrade', lambda u: _fetch(u.replace('https://', 'http://'), timeout=timeout, ssl_skip=True, ua=CHROME_UA, referer=u)),
        ('long_timeout', lambda u: _fetch(u, timeout=30, ssl_skip=True, ua=CHROME_UA, referer=u)),
    ]
    
    for strategy_name, fetcher in strategies:
        try:
            status, data, err = fetcher(url)
            if status == 200 and len(data) > 1000:
                return (status, len(data), strategy_name, None)
            elif status != 0:
                # 有HTTP响应但非200，继续试下一个策略
                continue
        except Exception:
            continue
    
    # 所有策略都失败，再试一次获取错误信息
    try:
        status, data, err = _fetch(url, timeout=timeout, ssl_skip=True, ua=CHROME_UA, referer=url)
        return (status, len(data) if data else 0, 'all_failed', err)
    except Exception as e:
        return (0, 0, 'all_failed', f'exception:{type(e).__name__}')


def _fetch(url, timeout=15, ssl_skip=False, ua=None, referer=None):
    """实际HTTP请求"""
    try:
        ctx = ssl.create_default_context()
        if ssl_skip:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        headers = {
            'User-Agent': ua or CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if referer:
            headers['Referer'] = referer
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            return (resp.status, data, None)
    except urllib.error.HTTPError as e:
        return (e.code, b'', f'http_{e.code}')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            return (0, b'', 'ssl_error')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, b'', 'timeout')
        if 'Connection refused' in reason or 'RemoteDisconnected' in reason:
            return (0, b'', 'connection_refused')
        return (0, b'', 'url_error')
    except socket.timeout:
        return (0, b'', 'timeout')
    except Exception as e:
        return (0, b'', f'exception:{type(e).__name__}')


def extract_fields_from_html(html_text, base_url):
    """从HTML提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）
    
    返回：dict，每个字段是提取出的值（脚本内部用，不输出原值）
    """
    if not html_text:
        return {}
    
    fields = {}
    
    # sourceIcon: favicon
    m = re.search(r'<link[^>]*rel=["\']?(?:shortcut )?icon["\']?[^>]*href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if m:
        icon = m.group(1)
        if icon.startswith('//'):
            icon = 'https:' + icon
        elif icon.startswith('/'):
            icon = base_url.rstrip('/') + icon
        fields['sourceIcon'] = icon
    
    # searchUrl: 找搜索表单
    m = re.search(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>(.*?)</form>', html_text, re.IGNORECASE | re.DOTALL)
    if m:
        action = m.group(1)
        form_html = m.group(2)
        # 找text/search input
        input_m = re.search(r'<input[^>]*type=["\'](?:text|search)["\'][^>]*name=["\']([^"\']+)["\']', form_html, re.IGNORECASE)
        if input_m:
            input_name = input_m.group(1)
            if action.startswith('/'):
                action = base_url.rstrip('/') + action
            sep = '&' if '?' in action else '?'
            fields['searchUrl'] = f"{action}{sep}{input_name}={{{{key}}}}"
    
    # sortUrl: 找分类链接
    # 找含"最新"/"热门"/"分类"的链接
    cat_links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(?:最新|热门|分类|全部)[^<]*</a>', html_text, re.IGNORECASE)
    if cat_links:
        sort_items = []
        for link in cat_links[:5]:
            if link.startswith('/'):
                link = base_url.rstrip('/') + link
            sort_items.append(f"分类::{link}")
        if sort_items:
            fields['sortUrl'] = '\n'.join(sort_items)
    
    # ruleNextPage: 找分页
    # 找 "下一页" 或 class="next" 或 rel="next"
    next_patterns = [
        (r'<a[^>]*class=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']', '@CSS:a.next@href'),
        (r'<a[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']', '@CSS:a[rel="next"]@href'),
        (r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*下一页\s*</a>', '@CSS:a:contains(下一页)@href'),
    ]
    for pattern, selector in next_patterns:
        if re.search(pattern, html_text, re.IGNORECASE):
            fields['ruleNextPage'] = selector
            break
    
    return fields


def is_valid_field(field, value):
    """校验字段值是否合法"""
    if not value or not isinstance(value, str):
        return False
    if value.strip() in ('None', 'null', 'undefined', 'NaN', 'page'):
        return False
    if field == 'ruleNextPage':
        if value.startswith(('@CSS:', '@XPath:', '@js:', '<js>')):
            return True
        if '@href' in value:
            return True
        if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>]+@?.*', value):
            return True
        return False
    if field in ('sourceIcon', 'searchUrl', 'sortUrl'):
        if not value.startswith(('http', '/', '@js:', '<js>')):
            return False
        return True
    return True


def main():
    print('=' * 70)
    print('深度优化失败源（脱敏输出：只输出idx+策略+字段长度+is_valid）')
    print('=' * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    
    print(f'\n总源数: {len(sources)}')
    print(f'待深度优化的失败源 idx: {FAILED_IDX}')
    
    optimized_count = 0
    no_change_count = 0
    detail_results = []
    
    for idx in FAILED_IDX:
        s = sources[idx]
        source_url = s.get('sourceUrl', '')
        base_url = extract_base_url(source_url)
        
        print(f'\n  [idx={idx}]')
        print(f'    base_url_len={len(base_url)} is_http_prefix={base_url.startswith("http")}')
        
        if not base_url:
            print(f'    跳过: sourceUrl非http开头（占位符源或JS双层加密）')
            detail_results.append({
                'idx': idx, 'strategy': 'skip_invalid_url',
                'status': 0, 'html_len': 0, 'fields_extracted': {},
                'optimization': 'no_change', 'reason': 'sourceUrl not http prefix'
            })
            no_change_count += 1
            continue
        
        # 访问站点
        status, html_len, strategy, err = fetch_html(base_url, timeout=20)
        print(f'    访问结果: status={status} html_len={html_len} strategy={strategy} err={err}')
        
        if status != 200 or html_len < 1000:
            print(f'    优化策略: 无法访问，保持原值')
            detail_results.append({
                'idx': idx, 'strategy': strategy,
                'status': status, 'html_len': html_len, 'fields_extracted': {},
                'optimization': 'no_change', 'reason': f'unreachable: {err}'
            })
            no_change_count += 1
            continue
        
        # 提取4字段
        # 重新拉取HTML（fetch_html返回的是长度，不是内容）
        # 修改：让 fetch_html 返回 html 内容
        # 这里重新访问一次（性能损失，但代码清晰）
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(base_url, headers={
                'User-Agent': CHROME_UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': base_url,
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'    重新访问失败: exception:{type(e).__name__}')
            detail_results.append({
                'idx': idx, 'strategy': strategy,
                'status': status, 'html_len': html_len, 'fields_extracted': {},
                'optimization': 'no_change', 'reason': f'refetch failed: {type(e).__name__}'
            })
            no_change_count += 1
            continue
        
        extracted = extract_fields_from_html(html_content, base_url)
        
        # 校验提取的字段
        valid_fields = {}
        for field, value in extracted.items():
            is_valid = is_valid_field(field, value)
            print(f'    提取 {field}: len={len(value) if value else 0} is_valid={is_valid}')
            if is_valid:
                valid_fields[field] = value
        
        # 对比当前值，只在新值有效且当前值无效/为空时替换
        changes = []
        for field, new_value in valid_fields.items():
            current_value = s.get(field, '')
            current_valid = is_valid_field(field, current_value)
            if not current_valid:
                # 当前值无效，用新值替换
                s[field] = new_value
                changes.append({
                    'field': field,
                    'before_len': len(current_value) if current_value else 0,
                    'after_len': len(new_value),
                    'before_valid': current_valid,
                    'after_valid': True,
                })
                print(f'    替换 {field}: before_len={len(current_value) if current_value else 0} after_len={len(new_value)}')
        
        if changes:
            optimized_count += 1
            detail_results.append({
                'idx': idx, 'strategy': strategy,
                'status': status, 'html_len': html_len,
                'fields_extracted': {f: len(v) if v else 0 for f, v in extracted.items()},
                'optimization': 'fields_updated',
                'changes': changes,
            })
        else:
            no_change_count += 1
            print(f'    无字段需要替换（当前值都有效或新值都无效）')
            detail_results.append({
                'idx': idx, 'strategy': strategy,
                'status': status, 'html_len': html_len,
                'fields_extracted': {f: len(v) if v else 0 for f, v in extracted.items()},
                'optimization': 'no_change', 'reason': 'no invalid fields to replace'
            })
    
    # 保存优化后的JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    
    print('\n' + '=' * 70)
    print('深度优化汇总')
    print('=' * 70)
    print(f'  总失败源数: {len(FAILED_IDX)}')
    print(f'  成功优化字段: {optimized_count} 个源')
    print(f'  无变化: {no_change_count} 个源')
    
    # 优化策略分布
    from collections import Counter
    strategy_counter = Counter(r['strategy'] for r in detail_results)
    print(f'\n--- 访问策略分布 ---')
    for strategy, count in strategy_counter.most_common():
        print(f'  {strategy}: {count} 个')
    
    # 字段替换统计
    field_changes = Counter()
    for r in detail_results:
        if r['optimization'] == 'fields_updated':
            for c in r.get('changes', []):
                field_changes[c['field']] += 1
    
    print(f'\n--- 字段替换统计 ---')
    for field, count in field_changes.most_common():
        print(f'  {field}: {count} 次替换')
    
    # 保存详细报告
    report_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/deep_optimization_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_failed': len(FAILED_IDX),
            'optimized_count': optimized_count,
            'no_change_count': no_change_count,
            'strategy_distribution': dict(strategy_counter),
            'field_changes': dict(field_changes),
            'detail': detail_results,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n优化后JSON: {OUTPUT_PATH}')
    print(f'详细报告: {report_path}')


if __name__ == '__main__':
    main()
