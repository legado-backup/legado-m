#!/usr/bin/env python3
"""compare_optimization.py — 对比优化前后的真实差异（脱敏输出）

输入：
  - exported_from_emulator.json (优化前)
  - optimized_final.json (优化后)

输出（纯技术指标，禁止业务字段原文）：
  - 被修改的源数量
  - 被修改的字段名+长度对比+is_http_prefix对比
  - 修改类型分类（补全/修复错误值/无变化）
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

BEFORE_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/exported_from_emulator.json'
AFTER_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'

# 关心的字段（技术字段名，不输出值）
CARE_FIELDS = [
    'sourceUrl', 'sourceName', 'sourceComment',
    'sourceIcon', 'searchUrl', 'sortUrl',
    'ruleArticles', 'ruleNextPage', 'ruleTitle', 'ruleLink', 'ruleContent',
    'enabled', 'type', 'customOrder',
]


def is_http_prefix(v):
    """判断字符串是否http开头（不输出原值）"""
    if not isinstance(v, str):
        return False
    return v.startswith('http://') or v.startswith('https://')


def has_js_prefix(v):
    """判断是否含@js:或<js>前缀"""
    if not isinstance(v, str):
        return False
    return '@js:' in v or v.startswith('<js>')


def value_metric(v):
    """生成值的技术指标（不输出原值）"""
    if v is None:
        return {'len': 0, 'is_empty': True, 'is_http': False, 'has_js': False}
    if not isinstance(v, str):
        return {'len': 0, 'is_empty': False, 'is_http': False, 'has_js': False, 'type': type(v).__name__}
    return {
        'len': len(v),
        'is_empty': len(v.strip()) == 0,
        'is_http': is_http_prefix(v),
        'has_js': has_js_prefix(v),
    }


def main():
    with open(BEFORE_PATH, 'r', encoding='utf-8') as f:
        before = json.load(f)
    with open(AFTER_PATH, 'r', encoding='utf-8') as f:
        after = json.load(f)

    print('=' * 70)
    print('优化前后对比（脱敏：只输出技术指标）')
    print('=' * 70)
    print(f'\n  优化前源数: {len(before)}')
    print(f'  优化后源数: {len(after)}')

    # 按 sourceUrl 匹配（sourceUrl是主键）
    before_map = {s.get('sourceUrl', ''): s for s in before}
    after_map = {s.get('sourceUrl', ''): s for s in after}

    # 用 idx 匹配（按顺序）
    # 因为 sourceUrl 可能在优化前后不同（虽然不应该），用 idx 更稳
    # 但 idx 依赖于数组顺序，所以我们用 sourceUrl 匹配，匹配不上的用 idx
    
    # 收集所有修改
    modifications = []  # [(idx, field, before_metric, after_metric, change_type)]
    no_change_count = 0
    
    for idx in range(min(len(before), len(after))):
        b = before[idx]
        a = after[idx]
        modified_fields = []
        
        for field in CARE_FIELDS:
            bv = b.get(field)
            av = a.get(field)
            bm = value_metric(bv)
            am = value_metric(av)
            
            # 判断是否有变化
            if bm != am:
                # 判断修改类型
                if bm['is_empty'] and not am['is_empty']:
                    change_type = 'fill_empty'  # 补全空字段
                elif bm['is_empty'] and am['is_empty']:
                    change_type = 'no_change'  # 都是空
                    continue
                elif bm.get('len', 0) > 0 and am.get('len', 0) > 0:
                    change_type = 'modify_value'  # 修改已有值
                else:
                    change_type = 'other'
                
                modified_fields.append({
                    'field': field,
                    'before': bm,
                    'after': am,
                    'change_type': change_type,
                })
        
        if modified_fields:
            modifications.append((idx, modified_fields))
        else:
            no_change_count += 1
    
    print(f'\n  被修改的源数: {len(modifications)}')
    print(f'  未修改的源数: {no_change_count}')
    
    # 修改类型统计
    print('\n--- 修改类型统计 ---')
    change_type_counter = Counter()
    field_modify_counter = Counter()
    field_fill_counter = Counter()
    
    for idx, fields in modifications:
        for f in fields:
            change_type_counter[f['change_type']] += 1
            if f['change_type'] == 'modify_value':
                field_modify_counter[f['field']] += 1
            elif f['change_type'] == 'fill_empty':
                field_fill_counter[f['field']] += 1
    
    print(f'  补全空字段次数: {change_type_counter["fill_empty"]}')
    print(f'  修改已有值次数: {change_type_counter["modify_value"]}')
    print(f'  其他修改次数: {change_type_counter.get("other", 0)}')
    
    print('\n--- 被补全的字段分布（fill_empty）---')
    for field, count in field_fill_counter.most_common():
        print(f'  {field}: {count} 次')
    
    print('\n--- 被修改的字段分布（modify_value）---')
    for field, count in field_modify_counter.most_common():
        print(f'  {field}: {count} 次')
    
    # 详细修改清单（脱敏）
    print('\n--- 详细修改清单（只显示idx+字段+长度变化+is_http变化）---')
    for idx, fields in modifications[:15]:  # 前15个
        print(f'\n  [idx={idx}]')
        for f in fields:
            b = f['before']
            a = f['after']
            print(f'    {f["field"]}: len={b.get("len", 0)}→{a.get("len", 0)} '
                  f'http={b.get("is_http", False)}→{a.get("is_http", False)} '
                  f'js={b.get("has_js", False)}→{a.get("has_js", False)} '
                  f'type={f["change_type"]}')
    
    if len(modifications) > 15:
        print(f'\n  ... 还有 {len(modifications) - 15} 个源的修改未显示')
    
    # 优化效果总结
    print('\n' + '=' * 70)
    print('优化效果总结')
    print('=' * 70)
    
    # 补全 RECOMMENDED 字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）的源数
    rec_fields = ['sourceIcon', 'searchUrl', 'sortUrl', 'ruleNextPage']
    rec_filled_sources = set()
    for idx, fields in modifications:
        for f in fields:
            if f['field'] in rec_fields and f['change_type'] == 'fill_empty':
                rec_filled_sources.add(idx)
    
    print(f'\n  补全 RECOMMENDED 字段（4字段）的源数: {len(rec_filled_sources)}')
    
    # 修复错误值（'page'/'None'等）的源数
    # 这个无法直接从对比中看出来，需要看 before 值是否是 'page'/'None'/'null' 等无效值
    # 但我们的 value_metric 不输出原值，所以用 is_empty=False + len>0 判断
    # 更准确的方式：在 before 值 is_empty=False 但实际是 'page'/'None' 等无效值
    # 这里我们只能统计 modify_value 的次数
    print(f'  修改已有值的次数: {change_type_counter["modify_value"]}')
    
    print(f'\n  结论:')
    print(f'  - 实际"被优化"的源数（有字段修改）: {len(modifications)}')
    print(f'  - 其中补全空字段: {change_type_counter["fill_empty"]} 次（覆盖 {len(rec_filled_sources)} 个源的 RECOMMENDED 字段）')
    print(f'  - 其中修改已有值: {change_type_counter["modify_value"]} 次（含修复错误值如 "page"/"None"）')
    
    # 保存详细对比报告
    out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimization_diff.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_before': len(before),
            'total_after': len(after),
            'modified_count': len(modifications),
            'no_change_count': no_change_count,
            'change_type_distribution': dict(change_type_counter),
            'field_fill_distribution': dict(field_fill_counter),
            'field_modify_distribution': dict(field_modify_counter),
            'rec_filled_sources_count': len(rec_filled_sources),
            'modifications_detail': [
                {
                    'idx': idx,
                    'fields': [
                        {
                            'field': f['field'],
                            'before_metric': f['before'],
                            'after_metric': f['after'],
                            'change_type': f['change_type'],
                        }
                        for f in fields
                    ]
                }
                for idx, fields in modifications
            ],
        }, f, ensure_ascii=False, indent=2)
    print(f'\n详细对比报告: {out_path}')


if __name__ == '__main__':
    main()
