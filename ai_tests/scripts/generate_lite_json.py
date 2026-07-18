#!/usr/bin/env python3
"""generate_lite_json.py — 生成精简版JSON（去掉8个truly_dead源）

输入: optimized_final_v5.json (65源)
输出: optimized_final_lite.json (57源，去掉8个truly_dead)
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v5.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_lite.json'


def main():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    # 过滤掉truly_dead源（sourceComment含truly_diag:truly_dead）
    kept_sources = []
    removed_idx = []
    for i, s in enumerate(sources):
        comment = s.get('sourceComment', '') or ''
        # 检查是否含truly_dead诊断
        is_truly_dead = 'AI_FINAL_DIAG:truly_dead' in comment
        if is_truly_dead:
            removed_idx.append(i)
        else:
            # 移除诊断标记，保留干净源
            cleaned_comment = re.sub(r'\[AI_FINAL_DIAG:[^\]]+\]', '', comment).strip()
            cleaned_comment = re.sub(r'\[AI_DIAGNOSIS:[^\]]+\]', '', cleaned_comment).strip()
            if cleaned_comment != comment:
                s['sourceComment'] = cleaned_comment
            kept_sources.append(s)

    print(f'\n保留源数: {len(kept_sources)}')
    print(f'移除源数: {len(removed_idx)}')
    print(f'移除idx: {removed_idx}')

    # 检查保留源的诊断分布
    from collections import Counter
    diag_counter = Counter()
    for s in kept_sources:
        comment = s.get('sourceComment', '') or ''
        if 'unstable_http_downgrade' in comment:
            diag_counter['unstable_http_downgrade'] += 1
        elif 'already_optimized' in comment:
            diag_counter['already_optimized'] += 1
        else:
            diag_counter['normal'] += 1

    print(f'\n保留源诊断分布:')
    for k, v in diag_counter.most_common():
        print(f'  {k}: {v}')

    # 保存精简版JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(kept_sources, f, ensure_ascii=False, indent=2)
    print(f'\n精简版JSON: {OUTPUT_JSON}')
    print(f'源数: {len(kept_sources)}')


if __name__ == '__main__':
    main()
