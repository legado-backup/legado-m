#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量优化源[5]（fixed聚合源）的35个标准CMS API子源
方案：从sortUrl第1行提取URL模板，替换t值构建多个搜索分类项
输出安全：只输出技术统计，不输出业务数据
"""
import json
import sys
import os
import re
from urllib.parse import urlparse, parse_qs, urlencode

# MacCMS通用分类（ID: 名称）
COMMON_CATEGORIES = [
    (1, '电影'),
    (2, '剧集'),
    (3, '综艺'),
    (4, '动漫'),
    (6, '动作'),
    (20, '短剧'),
]

def extract_url_template(sort_url_first_line):
    """从sortUrl第1行提取URL模板
    格式: 分类名::URL?ac=list&t=1&pg={{page}}
    返回: (base_url_with_path, params_dict) 或 None
    """
    if '::' not in sort_url_first_line:
        return None
    cat_name, url = sort_url_first_line.split('::', 1)
    url = url.strip()

    # 分离URL和查询参数
    if '?' in url:
        base, query = url.split('?', 1)
        params = parse_qs(query)
        return base, params, cat_name
    else:
        return url, {}, cat_name

def build_search_items(base_url, params, current_t):
    """构建搜索分类项
    强制使用 ac=list（搜索接口），不用 ac=detail（详情接口）
    保留pg参数，替换t值为不同分类
    """
    items = []
    for cat_id, cat_name in COMMON_CATEGORIES:
        if cat_id == current_t:
            continue  # 跳过已存在的分类

        # 构建URL参数
        # 强制 ac=list（搜索接口），不用 ac=detail（详情接口）
        query_parts = ['ac=list']
        query_parts.append(f"wd={{{{key}}}}")
        query_parts.append(f"t={cat_id}")
        if 'pg' in params:
            query_parts.append(f"pg={{{{page}}}}")

        search_url = f"{base_url}?{'&'.join(query_parts)}"
        items.append(f"搜索{cat_name}::{search_url}")

    return items

def optimize_source(source_file, output_file):
    """批量优化源[5]"""
    with open(source_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== 源[5]批量优化（通用分类方案）===")
    print(f"总子源数: {len(sources)}")
    print(f"通用分类: {[(c[0], c[1]) for c in COMMON_CATEGORIES]}")
    print()

    stats = {
        'total': len(sources),
        'cms_optimized': 0,
        'cms_skipped_nonstandard': 0,
        'path_skipped': 0,
        'other_skipped': 0,
        'total_cats_added': 0,
    }

    skipped_list = []

    for i, src in enumerate(sources):
        search_url = src.get('searchUrl', '')
        sort_url = src.get('sortUrl', '')
        source_url = src.get('sourceUrl', '')

        # 判断子源类型
        is_cms_api = 'ac=list' in search_url or 'ac=list' in sort_url
        is_path_search = '/search/' in search_url or '/vodsearch/' in search_url or '/index.php/vod/search' in search_url

        if not is_cms_api and not is_path_search:
            stats['other_skipped'] += 1
            continue

        if is_path_search and not is_cms_api:
            stats['path_skipped'] += 1
            skipped_list.append((i, 'PATH_SEARCH'))
            continue

        # CMS API子源优化
        # 提取sortUrl第1行
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        if not sort_lines:
            stats['cms_skipped_nonstandard'] += 1
            skipped_list.append((i, 'NO_SORT_URL'))
            continue

        sort_first = sort_lines[0]
        result = extract_url_template(sort_first)

        if result is None:
            stats['cms_skipped_nonstandard'] += 1
            skipped_list.append((i, 'NO_TEMPLATE'))
            continue

        base_url, params, current_cat_name = result

        # 检查是否有t参数
        if 't' not in params:
            # 子源[0]类型：sortUrl无t参数，不是标准CMS分类结构
            # 用sourceUrl构建搜索项
            # 从searchUrl提取参数模式
            if 'ac=list' in search_url:
                # searchUrl格式: {sourceUrl}?ac=list&wd={{key}}&pg={{page}}
                # 构建搜索分类项
                base = source_url.rstrip('/')
                for cat_id, cat_name in COMMON_CATEGORIES:
                    search_entry = f"{base}?ac=list&wd={{{{key}}}}&t={cat_id}"
                    if 'pg' in search_url:
                        search_entry += "&pg={{page}}"
                    sort_url += f"\\n搜索{cat_name}::{search_entry}"

                src['sortUrl'] = sort_url
                stats['cms_optimized'] += 1
                stats['total_cats_added'] += len(COMMON_CATEGORIES)
                print(f"  子源[{i}]: 成功(无t参数方案) - 追加{len(COMMON_CATEGORIES)}个搜索分类")
                continue
            else:
                stats['cms_skipped_nonstandard'] += 1
                skipped_list.append((i, 'NONSTANDARD_API'))
                continue

        current_t = int(params['t'][0])

        # 构建搜索分类项
        search_items = build_search_items(base_url, params, current_t)

        if not search_items:
            stats['cms_skipped_nonstandard'] += 1
            skipped_list.append((i, 'NO_SEARCH_ITEMS'))
            continue

        # 在sortUrl末尾追加搜索分类项
        if sort_url and not sort_url.endswith('\\n'):
            new_sort_url = sort_url + '\\n' + '\\n'.join(search_items)
        elif sort_url:
            new_sort_url = sort_url + '\\n'.join(search_items)
        else:
            new_sort_url = '\\n'.join(search_items)

        src['sortUrl'] = new_sort_url
        stats['cms_optimized'] += 1
        stats['total_cats_added'] += len(search_items)
        print(f"  子源[{i}]: 成功 - 当前分类t={current_t}({current_cat_name}) 追加{len(search_items)}个搜索分类")

    # 保存优化后的JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    print()
    print(f"=== 优化统计 ===")
    print(f"总子源数: {stats['total']}")
    print(f"CMS API优化成功: {stats['cms_optimized']}")
    print(f"CMS API跳过(非标准): {stats['cms_skipped_nonstandard']}")
    print(f"路径式跳过: {stats['path_skipped']}")
    print(f"其他跳过: {stats['other_skipped']}")
    print(f"追加搜索分类总数: {stats['total_cats_added']}")
    print()
    if skipped_list:
        print(f"=== 跳过子源清单 ===")
        for idx, reason in skipped_list:
            print(f"  子源[{idx}]: {reason}")
    print()
    print(f"输出文件: {output_file}")

    return stats

if __name__ == '__main__':
    source_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260725.json'
    output_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260729.json'

    if not os.path.exists(source_file):
        print(f"错误: 源文件不存在 {source_file}")
        sys.exit(1)
    optimize_source(source_file, output_file)
