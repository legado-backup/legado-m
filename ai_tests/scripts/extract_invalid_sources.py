#!/usr/bin/env python3
"""extract_invalid_sources.py — 提取占位符源+不可达源idx列表（脱敏：只输出idx和技术分类）

策略：
1. 占位符源(sourceUrl非http开头)：尝试用sourceName作为搜索词，通过搜索引擎找到真实URL
   - 但这会输出源名称，违反脱敏原则
   - 替代策略：直接标记为"建议删除"，让用户决定
2. 不可达源：输出idx和错误类型，分类给出修复建议

输出：纯技术指标，禁止业务字段原文
"""
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'

with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    sources = json.load(f)

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def extract_base_url(source_url):
    if not source_url:
        return ''
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    return base.rstrip('/').rstrip(',') + '/'

def check_url_enhanced(url, timeout=15):
    if not url:
        return (0, 0, 'empty_url')
    try:
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return (resp.status, len(data), None)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'Name or service' in reason or 'getaddrinfo' in reason or 'nodename' in reason:
            return (0, 0, 'dns_fail')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, 0, 'timeout')
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            return (0, 0, 'ssl_error')
        if 'Connection refused' in reason or 'RemoteDisconnected' in reason:
            return (0, 0, 'connection_refused')
        return (0, 0, f'url_error')
    except socket.timeout:
        return (0, 0, 'timeout')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')

print('=' * 70)
print('占位符源 + 不可达源分类报告（脱敏：只输出idx和技术分类）')
print('=' * 70)

# 1. 占位符源清单
print('\n--- 占位符源清单（sourceUrl非http开头）---')
placeholder_indices = []
for i, s in enumerate(sources):
    source_url = s.get('sourceUrl', '')
    if not source_url.startswith('http'):
        placeholder_indices.append(i)
        print(f'  [idx={i}] source_url_len={len(source_url)} | 建议处理: 标记删除或重新提取真实URL')

print(f'\n  小计: {len(placeholder_indices)} 个占位符源')

# 2. 不可达源清单（http开头但HTTP验证失败）
print('\n--- 不可达源清单（http开头但HTTP验证失败）---')
unreachable = []
for i, s in enumerate(sources):
    source_url = s.get('sourceUrl', '')
    if not source_url.startswith('http'):
        continue
    base_url = extract_base_url(source_url)
    status, clen, err = check_url_enhanced(base_url, timeout=15)
    if status != 200 or clen < 1000:
        unreachable.append({
            'idx': i,
            'base_url_len': len(base_url),
            'status': status,
            'error': err,
        })
        print(f'  [idx={i}] base_url_len={len(base_url)} status={status} err={err}')

print(f'\n  小计: {len(unreachable)} 个不可达源')

# 3. 不可达源分类
print('\n--- 不可达源错误分类 ---')
err_counter = Counter()
for u in unreachable:
    err_counter[u['error']] += 1
for err, count in err_counter.most_common():
    print(f'  {err}: {count} 个')

# 4. 修复建议
print('\n--- 修复建议 ---')
print(f'占位符源（{len(placeholder_indices)}个）：')
print(f'  - 策略1: 用Playwright重访问站点提取真实URL（需要sourceName作为搜索词）')
print(f'  - 策略2: 直接标记为"建议删除"，让用户在App中手动删除')
print(f'  - 推荐: 策略2（这些源sourceUrl是中文字符串，无法通过技术手段自动恢复真实URL）')

print(f'\n不可达源（{len(unreachable)}个）：')
print(f'  - dns_fail: 域名已失效，建议删除')
print(f'  - timeout: 慢站，可延长timeout重试')
print(f'  - ssl_error: 证书问题，可降级到http或跳过SSL验证')
print(f'  - http_403: UA被拒，升级UA伪装或添加Cookie')
print(f'  - http_404: 路径不存在，可能站点已迁移')
print(f'  - http_500: 服务器错误，稍后重试')
print(f'  - connection_refused: 服务器拒绝连接，可能已下线')

# 5. @js加密源清单
print('\n--- @js加密源清单（需走Legado JS引擎验证）---')
js_sources = []
for i, s in enumerate(sources):
    search_url = s.get('searchUrl', '')
    sort_url = s.get('sortUrl', '')
    is_js_search = search_url.startswith('@js:') or search_url.startswith('<js>')
    is_js_sort = sort_url.startswith('@js:') or sort_url.startswith('<js>')
    if is_js_search or is_js_sort:
        js_sources.append({
            'idx': i,
            'search_is_js': is_js_search,
            'sort_is_js': is_js_sort,
        })
        print(f'  [idx={i}] search_is_js={is_js_search} sort_is_js={is_js_sort}')

print(f'\n  小计: {len(js_sources)} 个@js加密源')

# 保存完整报告
out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/invalid_sources_report.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({
        'placeholder_sources': placeholder_indices,
        'unreachable_sources': unreachable,
        'js_encrypted_sources': js_sources,
        'error_distribution': dict(err_counter),
        'summary': {
            'total': len(sources),
            'placeholder_count': len(placeholder_indices),
            'unreachable_count': len(unreachable),
            'js_encrypted_count': len(js_sources),
            'http_ok_count': len(sources) - len(placeholder_indices) - len(unreachable),
        },
    }, f, ensure_ascii=False, indent=2)
print(f'\n详细报告: {out_path}')

# 汇总
summary = {
    'total': len(sources),
    'placeholder': len(placeholder_indices),
    'unreachable': len(unreachable),
    'js_encrypted': len(js_sources),
    'http_ok': len(sources) - len(placeholder_indices) - len(unreachable),
}
print('\n' + '=' * 70)
print('汇总')
print('=' * 70)
print(f'  总源数: {summary["total"]}')
print(f'  占位符源: {summary["placeholder"]} (建议删除)')
print(f'  不可达源: {summary["unreachable"]} (需分类处理)')
print(f'  @js加密源: {summary["js_encrypted"]} (跳过HTTP验证)')
print(f'  HTTP可达: {summary["http_ok"]} ✅')
print(f'  真实可用率: {summary["http_ok"]}/{summary["total"]} = {summary["http_ok"]/summary["total"]*100:.1f}%')
print(f'  排除占位符+@js后可达率: {summary["http_ok"]}/{summary["total"]-summary["placeholder"]-summary["js_encrypted"]} = {summary["http_ok"]/(summary["total"]-summary["placeholder"]-summary["js_encrypted"])*100:.1f}%')
