#!/usr/bin/env python3
"""generate_final_report.py — 生成最终优化报告

策略：
1. 不删除任何源（让用户决定是否删除）
2. 在 sourceComment 中追加标记（仅对truly_dead源）：
   "[AI_DIAGNOSIS:truly_dead|建议删除]"
3. 输出完整优化报告（脱敏：只输出技术指标）
4. 重新导入回模拟器
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'
DIAGNOSIS_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/unreachable_diagnosis.json'
FINAL_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'

# 加载
with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    sources = json.load(f)
with open(DIAGNOSIS_PATH, 'r', encoding='utf-8') as f:
    diagnosis = json.load(f)

# 对truly_dead源在sourceComment末尾追加标记
truly_dead_idx = diagnosis['strategy_groups'].get('truly_dead', [])
marked_count = 0
for idx in truly_dead_idx:
    s = sources[idx]
    comment = s.get('sourceComment', '')
    mark = '[AI_DIAGNOSIS:truly_dead|建议删除]'
    if mark not in comment:
        s['sourceComment'] = (comment + '\n' + mark).strip()
        marked_count += 1

print(f'已标记 {marked_count} 个 truly_dead 源（在sourceComment追加标记）')

# 保存最终JSON
with open(FINAL_PATH, 'w', encoding='utf-8') as f:
    json.dump(sources, f, ensure_ascii=False, indent=2)
print(f'最终JSON: {FINAL_PATH}')

# 生成完整优化报告
print('\n' + '=' * 70)
print('批量优化最终报告（脱敏：只输出技术指标）')
print('=' * 70)

# 源分类统计
total = len(sources)
js_double_count = 0
placeholder_invalid_count = 0
http_verifiable_count = 0
truly_dead_marked_count = 0

for i, s in enumerate(sources):
    source_url = s.get('sourceUrl', '')
    sort_url = s.get('sortUrl', '')
    search_url = s.get('searchUrl', '')
    comment = s.get('sourceComment', '')

    if not source_url.startswith('http'):
        if ('@js:' in sort_url or sort_url.startswith('<js>')) and 'source.sourceComment' in sort_url:
            js_double_count += 1
        elif ('@js:' in search_url or search_url.startswith('<js>')) and 'source.sourceComment' in search_url:
            js_double_count += 1
        else:
            placeholder_invalid_count += 1
    else:
        http_verifiable_count += 1

    if '[AI_DIAGNOSIS:truly_dead' in comment:
        truly_dead_marked_count += 1

print(f'\n--- 源分类 ---')
print(f'  总源数: {total}')
print(f'  JS双层加密源（sourceUrl占位符+sortUrl/searchUrl用@js:eval动态生成）: {js_double_count} 个')
print(f'  无效占位符源（非http开头且无JS加密）: {placeholder_invalid_count} 个')
print(f'  HTTP可验证源: {http_verifiable_count} 个')
print(f'  已标记 truly_dead: {truly_dead_marked_count} 个')

# 修复策略分布
print(f'\n--- 不可达源修复策略分布（共{sum(len(v) for v in diagnosis["strategy_groups"].values())}个）---')
for strategy, idxs in diagnosis['strategy_groups'].items():
    print(f'  {strategy}: {len(idxs)} 个 | idx: {idxs}')

# 最终真实可用率
print(f'\n--- 最终真实可用率 ---')
http_ok_count = http_verifiable_count - sum(len(v) for v in diagnosis['strategy_groups'].values())
print(f'  HTTP可验证源中真实可达: {http_ok_count}/{http_verifiable_count} = {http_ok_count/http_verifiable_count*100:.1f}%')
print(f'  加上JS双层加密源（需真机JS引擎验证）: {http_ok_count + js_double_count}/{total} = {(http_ok_count + js_double_count)/total*100:.1f}%')
print(f'  减去truly_dead源（建议删除）: {total - truly_dead_marked_count}/{total} = {(total - truly_dead_marked_count)/total*100:.1f}%')

# 优化建议
print(f'\n--- 优化建议 ---')
print(f'  1. JS双层加密源（{js_double_count}个）: 需要在App中通过真机JS引擎验证，不能通过HTTP直接验证')
print(f'  2. 无效占位符源（{placeholder_invalid_count}个）: 建议在App中删除（sourceUrl不是有效URL）')
print(f'  3. truly_dead源（{truly_dead_marked_count}个）: 已在sourceComment中标记[AI_DIAGNOSIS:truly_dead|建议删除]，建议在App中删除')
print(f'  4. server_error/long_timeout/server_slow_or_down源（3个）: 可在App中重试访问')
print(f'  5. ua_or_cookie源（1个）: 需要在App中手动访问触发Cookie同步')

# 保存完整报告
REPORT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/final_optimization_report.json'
report = {
    'summary': {
        'total_sources': total,
        'js_double_encrypted': js_double_count,
        'placeholder_invalid': placeholder_invalid_count,
        'http_verifiable': http_verifiable_count,
        'truly_dead_marked': truly_dead_marked_count,
        'http_ok_count': http_ok_count,
    },
    'strategy_distribution': diagnosis['strategy_distribution'],
    'strategy_groups': diagnosis['strategy_groups'],
    'real_availability_rate': {
        'http_verifiable_pass_rate': f'{http_ok_count}/{http_verifiable_count} = {http_ok_count/http_verifiable_count*100:.1f}%',
        'with_js_double': f'{http_ok_count + js_double_count}/{total} = {(http_ok_count + js_double_count)/total*100:.1f}%',
        'exclude_truly_dead': f'{total - truly_dead_marked_count}/{total} = {(total - truly_dead_marked_count)/total*100:.1f}%',
    },
    'optimization_suggestions': [
        f'JS双层加密源（{js_double_count}个）需真机JS引擎验证',
        f'无效占位符源（{placeholder_invalid_count}个）建议App中删除',
        f'truly_dead源（{truly_dead_marked_count}个）已在sourceComment标记，建议App中删除',
        f'server_error/long_timeout/server_slow_or_down源（3个）可在App中重试',
        f'ua_or_cookie源（1个）需在App中手动访问触发Cookie同步',
    ],
}
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'\n报告JSON: {REPORT_PATH}')
