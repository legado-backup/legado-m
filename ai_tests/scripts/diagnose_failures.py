#!/usr/bin/env python3
"""diagnose_failures.py — 深度诊断失败源真实根因（脱敏输出）

针对批量优化后的65个源，分类诊断每个源的真实可达性：
1. sourceUrl是否http开头（无效URL识别）
2. searchUrl/sortUrl是否@js加密（需走Legado JS引擎，不能直接HTTP验证）
3. 真实HTTP可达性（用Chrome UA + 长timeout）
4. 站点是否需要Referer/Cookie

输出：编号 + 诊断类别 + 技术细节，不输出域名/URL/源名称
"""
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
import urllib.parse
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'

with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    sources = json.load(f)

print(f'总源数: {len(sources)}')
print('=' * 70)

# 诊断分类
diagnosis = {
    'category_1_invalid_sourceurl': [],    # sourceUrl 非 http 开头
    'category_2_js_encrypted_search': [],  # searchUrl 含 @js
    'category_3_js_encrypted_sort': [],    # sortUrl 含 @js 或 <js>
    'category_4_template_url': [],          # sourceUrl 含 {{...}} 模板
    'category_5_http_unreachable': [],     # 真实HTTP不可达
    'category_6_http_ok': [],              # HTTP可达
    'category_7_timeout': [],              # timeout
    'category_8_ua_rejected': [],          # UA被拒
}

# Chrome UA + Referer 伪装
CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def is_invalid_sourceurl(url):
    """sourceUrl 是否无效（非 http 开头，是占位符）"""
    if not url:
        return True
    return not url.startswith('http')

def has_template(url):
    """sourceUrl 是否含 {{...}} 模板"""
    if not url:
        return False
    return '{{' in url and '}}' in url

def is_js_encrypted(url):
    """URL 是否是 @js / <js> 加密形式"""
    if not url:
        return False
    return url.startswith('@js:') or url.startswith('<js>') or '@js:' in url[:20]

def extract_base_url(source_url):
    """从 sourceUrl 模板提取真实首页 URL"""
    if not source_url:
        return ''
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    return base.rstrip('/').rstrip(',') + '/'

def check_url_enhanced(url, timeout=15):
    """增强的URL检查：Chrome UA + Referer + 长 timeout"""
    if not url:
        return (0, 0, 'empty_url')
    try:
        # 从URL提取域名作为Referer
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': referer,
            'Connection': 'keep-alive',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            # 检测是否被CF挡
            content_type = resp.headers.get('Content-Type', '')
            if resp.status == 403:
                return (403, 0, 'forbidden')
            return (resp.status, len(data), None)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'Name or service' in reason or 'getaddrinfo' in reason or 'nodename' in reason:
            return (0, 0, 'dns_fail')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, 0, 'timeout')
        if 'Forbidden' in reason or '403' in reason:
            return (403, 0, 'forbidden')
        return (0, 0, f'url_error:{reason[:30]}')
    except socket.timeout:
        return (0, 0, 'timeout')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')


# 逐个诊断
print('\n--- 逐源深度诊断 ---')
for i, s in enumerate(sources):
    source_url = s.get('sourceUrl', '')
    search_url = s.get('searchUrl', '')
    sort_url = s.get('sortUrl', '')

    # 类别1: 无效 sourceUrl
    if is_invalid_sourceurl(source_url):
        diagnosis['category_1_invalid_sourceurl'].append({
            'idx': i, 'source_url_len': len(source_url),
            'is_http_prefix': source_url.startswith('http') if source_url else False,
            # 不输出 source_url 内容（可能是源名称含敏感词）
            'classification': 'placeholder' if not source_url.startswith('http') else 'empty',
        })
        continue

    # 类别2: @js 加密 searchUrl
    if is_js_encrypted(search_url):
        diagnosis['category_2_js_encrypted_search'].append({
            'idx': i, 'search_url_prefix': '@js:'
        })

    # 类别3: @js 加密 sortUrl
    if is_js_encrypted(sort_url) or sort_url.startswith('<js>'):
        diagnosis['category_3_js_encrypted_sort'].append({
            'idx': i, 'sort_url_prefix': '@js:'
        })

    # 类别4: sourceUrl 含 {{...}} 模板
    if has_template(source_url):
        diagnosis['category_4_template_url'].append({
            'idx': i
        })

# 真实HTTP可达性测试：对所有 http 开头的 sourceUrl 做HTTP检查
print(f'\n--- HTTP可达性测试（{sum(1 for s in sources if s.get("sourceUrl","").startswith("http"))} 个源） ---')
http_test_results = []
for i, s in enumerate(sources):
    source_url = s.get('sourceUrl', '')
    if not source_url.startswith('http'):
        continue
    # 提取base_url（去除模板）
    base_url = extract_base_url(source_url)
    status, clen, err = check_url_enhanced(base_url, timeout=15)

    result = {
        'idx': i,
        'base_url_len': len(base_url),
        'status': status,
        'content_len': clen,
        'error': err,
    }
    http_test_results.append(result)

    # 分类
    if err == 'timeout':
        diagnosis['category_7_timeout'].append(result)
    elif status == 403 or err == 'forbidden':
        diagnosis['category_8_ua_rejected'].append(result)
    elif status == 200 and clen > 1000:
        diagnosis['category_6_http_ok'].append(result)
    elif status == 0:
        diagnosis['category_5_http_unreachable'].append(result)
    else:
        diagnosis['category_5_http_unreachable'].append(result)

    if (i + 1) % 10 == 0:
        print(f'  进度: {i+1}/{len(sources)}')

# 汇总
print('\n' + '=' * 70)
print('深度诊断汇总')
print('=' * 70)
for cat, items in diagnosis.items():
    print(f'\n{cat}: {len(items)} 个')
    if items:
        # 抽样3个
        for item in items[:3]:
            print(f'  样本: {item}')

# 真实失败原因分布
print('\n' + '=' * 70)
print('HTTP可达性真实分布')
print('=' * 70)
status_counter = Counter()
for r in http_test_results:
    if r['status'] == 200:
        status_counter['200_ok'] += 1
    elif r['status'] == 403:
        status_counter['403_forbidden'] += 1
    elif r['status'] == 404:
        status_counter['404_not_found'] += 1
    elif r['status'] == 0:
        status_counter[f'error_{r["error"]}'] += 1
    else:
        status_counter[f'http_{r["status"]}'] += 1

for status, count in status_counter.most_common():
    print(f'  {status}: {count} 个')

# 保存完整诊断结果
out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/diagnosis_report.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({
        'diagnosis_categories': {k: len(v) for k, v in diagnosis.items()},
        'http_test_results': http_test_results,
        'status_distribution': dict(status_counter),
    }, f, ensure_ascii=False, indent=2)
print(f'\n详细诊断报告: {out_path}')

# 优化空间分析
print('\n' + '=' * 70)
print('优化空间分析')
print('=' * 70)
total = len(sources)
invalid_url = len(diagnosis['category_1_invalid_sourceurl'])
js_search = len(diagnosis['category_2_js_encrypted_search'])
js_sort = len(diagnosis['category_3_js_encrypted_sort'])
template_url = len(diagnosis['category_4_template_url'])
http_ok = len(diagnosis['category_6_http_ok'])
http_fail = len(diagnosis['category_5_http_unreachable']) + len(diagnosis['category_7_timeout']) + len(diagnosis['category_8_ua_rejected'])

print(f'  无效 sourceUrl (占位符): {invalid_url} 个 → 优化: Playwright 重提取真实URL 或 标记删除')
print(f'  @js 加密 searchUrl: {js_search} 个 → 优化: 保留原值，verify脚本跳过JS加密源')
print(f'  @js 加密 sortUrl: {js_sort} 个 → 优化: 保留原值，verify脚本跳过JS加密源')
print(f'  sourceUrl 含模板: {template_url} 个 → 优化: 用 extract_base_url 提取真实URL')
print(f'  HTTP 可达: {http_ok} 个 → ✅ 已可用')
print(f'  HTTP 不可达/超时/UA拒绝: {http_fail} 个 → 优化: 进一步分析（真实失效 vs 反爬）')

# 真实优化率（排除JS加密和无效URL后的可达率）
testable_total = total - invalid_url - js_search - js_sort
if testable_total > 0:
    real_pass_rate = http_ok / testable_total * 100
    print(f'\n  真实可达率（排除JS加密和无效URL）: {http_ok}/{testable_total} = {real_pass_rate:.1f}%')
