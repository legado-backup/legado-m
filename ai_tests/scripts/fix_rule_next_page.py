#!/usr/bin/env python3
"""fix_rule_next_page.py — 修复批量优化脚本导致的 ruleNextPage 错误值

问题：批量优化脚本把50个源的 ruleNextPage 错误填为 "page"（无效值）
修复策略：
1. 读取 optimized_batch.json 和 exported_from_emulator.json
2. 对每个 ruleNextPage=="page" 或 "None" 的源，用原导出值覆盖
3. 如果原值也是空，保持空（ruleNextPage 是 RECOMMENDED，可为空）
4. 重新校验并重新导入回模拟器
"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch.json'
ORIGINAL_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/exported_from_emulator.json'
FIXED_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'

# 加载数据
with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    batch_sources = json.load(f)
with open(ORIGINAL_PATH, 'r', encoding='utf-8') as f:
    original_sources = json.load(f)

# 原始源以 sourceUrl 为 key
orig_map = {}
for s in original_sources:
    url = s.get('sourceUrl', '')
    if url:
        orig_map[url] = s

# 有效前缀列表
VALID_PREFIXES = (
    '@CSS:', '@XPath:', '@js:', '<js>', 'class.', '.',
    '#', 'text.', 'li.', 'a.', 'link[', 'script@',
    '$.', 'div.', 'ul.', 'span.', 'img.', 'input[',
    '@put:', '@get:',
)

def is_valid_rule_next_page(v):
    if not v or v in ('page', 'None', 'null', 'undefined'):
        return False
    # 直接是合法选择器
    if v.startswith(VALID_PREFIXES):
        return True
    # 含 @href
    if '@href' in v:
        return True
    # 含 <js>
    if '<js>' in v:
        return True
    # IIFE 或表达式
    if v.startswith('(function'):
        return True
    return False

# 修复统计
fix_stats = {
    'restored_from_original': 0,
    'cleared_invalid': 0,
    'already_valid': 0,
    'no_original': 0,
}

print('=' * 60)
print('修复 ruleNextPage 错误值')
print('=' * 60)
print(f'批量优化源数: {len(batch_sources)}')
print(f'原始导出源数: {len(original_sources)}')

for i, s in enumerate(batch_sources):
    url = s.get('sourceUrl', '')
    curr = s.get('ruleNextPage', '')

    if is_valid_rule_next_page(curr):
        fix_stats['already_valid'] += 1
        continue

    # 当前值无效，尝试用原值
    orig = orig_map.get(url, {})
    orig_val = orig.get('ruleNextPage', '')

    if is_valid_rule_next_page(orig_val):
        s['ruleNextPage'] = orig_val
        fix_stats['restored_from_original'] += 1
    else:
        # 原值也无效，清空
        s['ruleNextPage'] = ''
        fix_stats['cleared_invalid'] += 1
        if not orig:
            fix_stats['no_original'] += 1

# 保存修复后的文件
with open(FIXED_PATH, 'w', encoding='utf-8') as f:
    json.dump(batch_sources, f, ensure_ascii=False, indent=2)

print(f'\n修复统计:')
for k, v in fix_stats.items():
    print(f'  {k}: {v}')

# 校验修复后的 ruleNextPage 前缀分布
print('\n--- 修复后 ruleNextPage 前缀分布 ---')
from collections import Counter
prefix_counter = Counter()
empty_count = 0
for s in batch_sources:
    v = s.get('ruleNextPage', '')
    if not v:
        empty_count += 1
        continue
    if v.startswith(VALID_PREFIXES):
        prefix = v.split(':')[0] + ':' if ':' in v else v.split('.')[0] + '.'
    elif '@href' in v:
        prefix = 'selector@href'
    elif '<js>' in v:
        prefix = '<js>'
    else:
        prefix = 'other'
    prefix_counter[prefix] += 1

print(f'  empty: {empty_count}')
for prefix, count in prefix_counter.most_common():
    print(f'  {prefix}: {count} 个')

print(f'\n✅ 修复后文件已保存: {FIXED_PATH}')

# 同时修复其他字段的无效值
print('\n--- 修复其他字段无效值 ---')
INVALID_VALUES = {'page', 'None', 'null', 'undefined', 'NaN'}
fields_to_fix = ['sourceIcon', 'searchUrl', 'sortUrl', 'sourceComment', 'ruleArticles', 'ruleTitle', 'ruleLink']
for field in fields_to_fix:
    invalid_count = 0
    for s in batch_sources:
        v = s.get(field, '')
        if v in INVALID_VALUES:
            # 用原值覆盖
            url = s.get('sourceUrl', '')
            orig = orig_map.get(url, {})
            orig_val = orig.get(field, '')
            if orig_val and orig_val not in INVALID_VALUES:
                s[field] = orig_val
            else:
                s[field] = ''
            invalid_count += 1
    if invalid_count > 0:
        print(f'  ✅ {field}: 修复 {invalid_count} 个无效值')

# 重新保存
with open(FIXED_PATH, 'w', encoding='utf-8') as f:
    json.dump(batch_sources, f, ensure_ascii=False, indent=2)
print(f'\n✅ 最终修复文件: {FIXED_PATH}')
