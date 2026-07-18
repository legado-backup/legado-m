#!/usr/bin/env python3
"""analyze_rule_prefix.py — 分析 ruleNextPage 字段前缀分布（脱敏输出）"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

batch_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch.json'
with open(batch_path, 'r', encoding='utf-8') as f:
    sources = json.load(f)

print(f'total sources: {len(sources)}')

# ruleNextPage 前缀分析
print('\n--- ruleNextPage 前缀分析 ---')
prefix_counter = Counter()
empty_count = 0
samples = {}
for s in sources:
    v = s.get('ruleNextPage', '')
    if not v:
        empty_count += 1
        continue
    # 取前20字符作前缀样本
    if v.startswith('@CSS:'):
        prefix = '@CSS:'
    elif v.startswith('@XPath:'):
        prefix = '@XPath:'
    elif v.startswith('@js:'):
        prefix = '@js:'
    elif v.startswith('<js>'):
        prefix = '<js>'
    elif v.startswith('class.'):
        prefix = 'class.'
    elif v.startswith('.'):
        prefix = '.classname'
    elif v.startswith('#'):
        prefix = '#id'
    elif v.startswith('page'):
        prefix = 'page_N'
    else:
        prefix = f'other:{v[:15]}'
    prefix_counter[prefix] += 1
    if prefix not in samples:
        samples[prefix] = v[:50]  # 只保留前50字符做样本

print(f'  empty: {empty_count}')
for prefix, count in prefix_counter.most_common():
    print(f'  {prefix}: {count} 个')
    print(f'    样本: {samples[prefix]}')

# searchUrl 前缀分析
print('\n--- searchUrl 模板分析 ---')
search_counter = Counter()
search_samples = {}
empty = 0
for s in sources:
    v = s.get('searchUrl', '')
    if not v:
        empty += 1
        continue
    if '{{key}}' in v:
        if 'search?' in v.lower() or '?s=' in v:
            tag = 'has_{{key}}+search_param'
        elif 'q=' in v or 'keyword=' in v or 'wd=' in v:
            tag = 'has_{{key}}+q_param'
        else:
            tag = 'has_{{key}}+other'
    else:
        tag = 'no_{{key}}'
    search_counter[tag] += 1
    if tag not in search_samples:
        # 脱敏：只保留结构，移除域名
        sanitized = v
        # 移除 http(s)://domain
        import re
        sanitized = re.sub(r'https?://[^/]+', '<HOST>', sanitized)
        search_samples[tag] = sanitized[:60]
print(f'  empty: {empty}')
for tag, count in search_counter.most_common():
    print(f'  {tag}: {count} 个')
    print(f'    样本: {search_samples[tag]}')

# sortUrl 分析
print('\n--- sortUrl 分析 ---')
sort_counter = Counter()
sort_samples = {}
empty = 0
for s in sources:
    v = s.get('sortUrl', '')
    if not v:
        empty += 1
        continue
    line_count = v.count('\n') + 1
    has_delimiter = '::' in v
    if has_delimiter and line_count >= 2:
        tag = f'multi_category({line_count}lines,::delim)'
    elif has_delimiter:
        tag = 'single_category(::delim)'
    else:
        tag = 'no_delimiter'
    sort_counter[tag] += 1
    if tag not in sort_samples:
        import re
        sanitized = re.sub(r'https?://[^/]+', '<HOST>', v)
        sort_samples[tag] = sanitized[:80]
print(f'  empty: {empty}')
for tag, count in sort_counter.most_common():
    print(f'  {tag}: {count} 个')
    print(f'    样本: {sort_samples[tag]}')
