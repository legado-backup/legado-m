#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析原订阅源中已有的字段获取思路
（用户说有些写得相当好，可以借鉴参考）
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_original_fields_analysis.json"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)
    
    # 字段覆盖率统计
    fields = ['sourceIcon', 'searchUrl', 'sortUrl', 'ruleArticles', 'ruleTitle',
              'ruleLink', 'ruleImage', 'ruleNextPage', 'rulePubDate', 'ruleContent',
              'loginUrl', 'enabledCookieJar', 'enableJs', 'header', 'jsRule']
    
    coverage = {}
    for field in fields:
        count = sum(1 for s in sources if s.get(field))
        coverage[field] = {
            'count': count,
            'percent': f"{count * 100 / len(sources):.1f}%"
        }
    
    # 按类型分组的字段覆盖率
    type_coverage = {}
    for t in [0, 1, 2]:
        type_sources = [s for s in sources if s.get('type') == t]
        if not type_sources:
            continue
        type_name = {0: 'web', 1: 'image', 2: 'video'}.get(t, f'type{t}')
        type_coverage[type_name] = {
            'total': len(type_sources),
            'fields': {}
        }
        for field in fields:
            count = sum(1 for s in type_sources if s.get(field))
            type_coverage[type_name]['fields'][field] = {
                'count': count,
                'percent': f"{count * 100 / len(type_sources):.1f}%"
            }
    
    # 收集写得好的源（字段完整）
    good_sources = []
    for idx, s in enumerate(sources):
        score = sum(1 for f in fields if s.get(f))
        if score >= 8:  # 至少8个字段有值
            good_sources.append({
                'idx': idx,
                'score': score,
                'type': s.get('type', 0),
                'fields_present': [f for f in fields if s.get(f)],
                # 注：不输出业务字段原文，只输出字段名清单
            })
    
    # 按类型分组，找出每种类型中字段最完整的源（作为参考模板）
    type_examples = {}
    for t in [0, 1, 2]:
        type_sources = [(idx, s) for idx, s in enumerate(sources) if s.get('type') == t]
        if not type_sources:
            continue
        type_name = {0: 'web', 1: 'image', 2: 'video'}.get(t, f'type{t}')
        # 按字段完整度排序
        type_sources.sort(key=lambda x: sum(1 for f in fields if x[1].get(f)), reverse=True)
        # 取前3个作为参考模板
        type_examples[type_name] = [{
            'idx': idx,
            'score': sum(1 for f in fields if s.get(f)),
            'fields_present': [f for f in fields if s.get(f)],
        } for idx, s in type_sources[:3]]
    
    report = {
        'stage': 'original_fields_analysis',
        'total_sources': len(sources),
        'field_coverage': coverage,
        'type_coverage': type_coverage,
        'good_sources_count': len(good_sources),
        'good_sources': good_sources[:20],  # 前20个
        'type_examples': type_examples,
    }
    
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印汇总（只输出技术指标，不输出业务字段）
    print(f"=== 原订阅源字段覆盖率分析 ===")
    print(f"总源数: {len(sources)}")
    print(f"\n--- 全局字段覆盖率 ---")
    for field, info in coverage.items():
        print(f"  {field:20s}: {info['count']:3d} / {len(sources)} ({info['percent']})")
    
    print(f"\n--- 各类型字段覆盖率 ---")
    for type_name, info in type_coverage.items():
        print(f"\n  [{type_name}] 共 {info['total']} 个源:")
        for field, finfo in info['fields'].items():
            print(f"    {field:20s}: {finfo['count']:3d} / {info['total']} ({finfo['percent']})")
    
    print(f"\n--- 字段完整的源（≥8个字段）---")
    print(f"共 {len(good_sources)} 个源字段较完整")
    print(f"\n--- 各类型参考模板（字段最完整的前3个）---")
    for type_name, examples in type_examples.items():
        print(f"\n  [{type_name}]")
        for ex in examples:
            print(f"    idx={ex['idx']:3d} score={ex['score']:2d} fields={ex['fields_present']}")
    
    print(f"\n输出: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
