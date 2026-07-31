#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证优化后的源[5] JSON文件结构
输出安全：只输出技术统计，不输出业务数据
"""
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

def verify_optimized(output_file):
    """验证优化后的JSON文件"""
    with open(output_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== 源[5]优化后验证 ===")
    print(f"文件: {output_file}")
    print(f"总子源数: {len(sources)}")
    print(f"JSON格式: 有效")
    print()

    # 统计
    stats = {
        'with_search_items': 0,
        'without_search_items': 0,
        'total_sort_lines': 0,
        'total_search_items': 0,
        'field_check': {'sourceName': 0, 'sourceUrl': 0, 'sortUrl': 0, 'searchUrl': 0, 'ruleArticles': 0, 'ruleTitle': 0, 'ruleLink': 0},
    }

    for i, src in enumerate(sources):
        # 必填字段检查
        for field in stats['field_check']:
            if src.get(field):
                stats['field_check'][field] += 1

        sort_url = src.get('sortUrl', '')
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]

        # 统计搜索分类项（以"搜索"开头的行）
        search_items = [line for line in sort_lines if line.startswith('搜索')]

        if search_items:
            stats['with_search_items'] += 1
            stats['total_search_items'] += len(search_items)
        else:
            stats['without_search_items'] += 1

        stats['total_sort_lines'] += len(sort_lines)

    print(f"=== 必填字段检查 ===")
    for field, count in stats['field_check'].items():
        status = "✓" if count == len(sources) else f"✗({count}/{len(sources)})"
        print(f"  {field}: {status}")
    print()

    print(f"=== 搜索分类统计 ===")
    print(f"有搜索分类的子源: {stats['with_search_items']}")
    print(f"无搜索分类的子源: {stats['without_search_items']}")
    print(f"搜索分类总数: {stats['total_search_items']}")
    print(f"平均每子源: {stats['total_search_items']/stats['with_search_items'] if stats['with_search_items'] else 0:.1f}")
    print()

    # 检查搜索分类项的URL格式
    print(f"=== 搜索分类项URL格式检查（前3个子源样本）===")
    checked = 0
    for i, src in enumerate(sources):
        sort_url = src.get('sortUrl', '')
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        search_items = [line for line in sort_lines if line.startswith('搜索')]

        if not search_items:
            continue

        print(f"子源[{i}] ({len(search_items)}个搜索分类):")
        for j, item in enumerate(search_items[:3]):  # 只检查前3个
            if '::' in item:
                name, url = item.split('::', 1)
                # 检查URL是否包含ac=list和wd={{key}}和t=
                has_ac = 'ac=list' in url
                has_wd = 'wd={{key}}' in url or 'wd={{{{key}}}}' in url
                has_t = 't=' in url
                has_pg = 'pg=' in url
                print(f"  [{j}] 名称长度={len(name)} ac={'✓' if has_ac else '✗'} wd={'✓' if has_wd else '✗'} t={'✓' if has_t else '✗'} pg={'✓' if has_pg else '✗'}")
        checked += 1
        if checked >= 3:
            break

    print()
    print(f"=== 验证结果 ===")
    all_fields_ok = all(v == len(sources) for v in stats['field_check'].values())
    print(f"必填字段: {'✓ 全部完整' if all_fields_ok else '✗ 有缺失'}")
    print(f"搜索分类: {'✓ 已追加' if stats['total_search_items'] > 0 else '✗ 未追加'}")
    print(f"JSON格式: ✓ 有效")

    return all_fields_ok and stats['total_search_items'] > 0

if __name__ == '__main__':
    output_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260729.json'
    if not os.path.exists(output_file):
        print(f"错误: 文件不存在 {output_file}")
        sys.exit(1)
    success = verify_optimized(output_file)
    sys.exit(0 if success else 1)
