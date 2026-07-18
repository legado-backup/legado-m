#!/usr/bin/env python3
"""analyze_js_sources_structure.py — 分析@js加密源的技术结构（脱敏：只输出技术字段，不输出业务内容）

目的：搞清楚11个占位符源是不是"JS整块加密源"——sourceUrl是占位符但sourceComment/sortUrl中
含@js代码动态生成真实URL

输出：纯技术指标，不输出业务字段原文
"""
import json
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'

with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    sources = json.load(f)

print('=' * 70)
print('@js加密源技术结构分析')
print('=' * 70)

# 11个占位符源的idx（已知）
placeholder_indices = [4, 5, 7, 8, 9, 10, 11, 12, 15, 16, 59]

# 对每个占位符源，分析其字段的技术特征（不输出业务内容）
print('\n--- 占位符源字段技术特征 ---')
for idx in placeholder_indices:
    s = sources[idx]
    source_url = s.get('sourceUrl', '')
    source_comment = s.get('sourceComment', '')
    sort_url = s.get('sortUrl', '')
    search_url = s.get('searchUrl', '')

    # 技术特征分析（不输出业务内容）
    features = {
        'idx': idx,
        'source_url_type': 'placeholder' if not source_url.startswith('http') else 'http_url',
        'source_comment_len': len(source_comment),
        'source_comment_has_js': source_comment.startswith('@js:') or source_comment.startswith('<js>'),
        'source_comment_has_eval': 'eval(' in source_comment,
        'source_comment_has_source_url_var': 'source.sourceUrl' in source_comment or 'sourceUrl' in source_comment,
        'source_comment_has_host_var': 'host' in source_comment,
        'sort_url_len': len(sort_url),
        'sort_url_has_js': sort_url.startswith('@js:') or sort_url.startswith('<js>'),
        'sort_url_has_eval': 'eval(' in sort_url,
        'sort_url_has_source_comment': 'source.sourceComment' in sort_url,
        'sort_url_has_host': 'host' in sort_url and 'java.toast' in sort_url,
        'search_url_len': len(search_url),
        'search_url_has_js': search_url.startswith('@js:') or search_url.startswith('<js>'),
        'search_url_has_eval': 'eval(' in search_url,
        'search_url_has_source_comment': 'source.sourceComment' in search_url,
    }

    print(f'\n  [idx={idx}]')
    for k, v in features.items():
        if k != 'idx':
            print(f'    {k}: {v}')

# 判断这些源是不是"JS整块加密源"
print('\n--- 占位符源JS加密模式分析 ---')
js_pattern_count = 0
for idx in placeholder_indices:
    s = sources[idx]
    source_comment = s.get('sourceComment', '')
    sort_url = s.get('sortUrl', '')
    search_url = s.get('searchUrl', '')

    is_js_pattern = (
        (source_comment.startswith('@js:') or source_comment.startswith('<js>'))
        and 'eval(' in source_comment
        and ('source.sourceComment' in sort_url or 'source.sourceComment' in search_url)
    )
    if is_js_pattern:
        js_pattern_count += 1
    print(f'  [idx={idx}] is_js_pattern={is_js_pattern}')

print(f'\n  小计: {js_pattern_count}/{len(placeholder_indices)} 个占位符源是JS整块加密源')

# 这种源的典型结构总结
print('\n--- JS整块加密源典型结构 ---')
print('  sourceUrl: 占位符（中文字符串，非URL）')
print('  sourceComment: @js:eval(...) 或 <js>eval(...)</js>')
print('    - 内部定义 host 变量（真实URL）')
print('    - 通过 source.sourceComment 引用')
print('  sortUrl: @js:eval(source.sourceComment + ""); java.toast(...); let host = ...')
print('    - 执行 sourceComment JS 代码获取真实 host')
print('    - 然后用 host 拼接分类URL')
print('  searchUrl: 类似 sortUrl 模式')
print('')
print('  ⚠️ 这种源不能用HTTP直接验证 sourceUrl（占位符）')
print('  ⚠️ 必须走 Legado JS 引擎执行 sourceComment 才能获取真实URL')
print('  ⚠️ verify_rss_scenarios.py 应识别这种模式并跳过HTTP验证')
