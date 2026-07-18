#!/usr/bin/env python3
"""mark_needs_manual.py — 标记idx=24/39为needs_manual_intervention

idx=24: HTTP 403反爬，需手动Cookie/UA
idx=39: HTTP 206文件下载，sourceUrl是下载链接非主页，需手动找主页URL
"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'

with open(INPUT_JSON, 'r', encoding='utf-8') as f:
    sources = json.load(f)

print(f'加载源数: {len(sources)}')

NEEDS_MANUAL = {
    24: 'needs_manual|反爬拦截HTTP_403-需手动Cookie或UA',
    39: 'needs_manual|sourceUrl是文件下载链接HTTP_206-需手动找主页URL',
}

marked = 0
for idx, reason in NEEDS_MANUAL.items():
    if idx >= len(sources):
        continue
    s = sources[idx]
    comment = s.get('sourceComment', '') or ''
    diagnosis = f'[AI_DIAGNOSIS:{reason}]'
    if 'AI_DIAGNOSIS' in comment:
        # 已有诊断，跳过
        print(f'  [idx={idx}] 已有诊断标记，跳过')
        continue
    new_comment = (comment + '\n' + diagnosis) if comment else diagnosis
    s['sourceComment'] = new_comment
    print(f'  [idx={idx}] 已追加诊断: {diagnosis[:80]}')
    marked += 1

print(f'\n共标记: {marked} 个')

# 保存（覆盖v4）
with open(INPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(sources, f, ensure_ascii=False, indent=2)
print(f'已保存: {INPUT_JSON}')

# 统计诊断分布
from collections import Counter
diag_counter = Counter()
for s in sources:
    comment = s.get('sourceComment', '') or ''
    if 'truly_dead' in comment:
        diag_counter['truly_dead'] += 1
    elif 'needs_manual' in comment:
        diag_counter['needs_manual'] += 1
    elif 'AI_DIAGNOSIS' in comment:
        diag_counter['other_ai_diag'] += 1
    else:
        diag_counter['no_diag'] += 1

print(f'\n诊断分布:')
for k, v in diag_counter.most_common():
    print(f'  {k}: {v}')
