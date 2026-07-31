#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查优化后的搜索分类项URL格式
输出安全：只输出技术结论，不输出完整URL
"""
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

def check_search_items(output_file):
    """检查搜索分类项的URL格式"""
    with open(output_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== 搜索分类项URL格式检查 ===")
    print()

    # 检查第1个有搜索分类的子源
    for i, src in enumerate(sources):
        sort_url = src.get('sortUrl', '')
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        search_items = [line for line in sort_lines if line.startswith('搜索')]

        if not search_items:
            continue

        print(f"子源[{i}] 搜索分类项数: {len(search_items)}")
        for j, item in enumerate(search_items[:3]):
            if '::' in item:
                name, url = item.split('::', 1)
                # 分析URL参数
                if '?' in url:
                    base, query = url.split('?', 1)
                    params = parse_qs(query, keep_blank_values=True)
                    print(f"  [{j}] 参数列表: {list(params.keys())}")
                    if 'ac' in params:
                        print(f"      ac值: '{params['ac'][0]}'")
                    if 'wd' in params:
                        print(f"      wd值: '{params['wd'][0]}'")
                    if 't' in params:
                        print(f"      t值: '{params['t'][0]}'")
                    # 检查URL中是否包含 ac=list
                    print(f"      URL包含ac=list: {'ac=list' in url}")
                    print(f"      URL前30字符: ...{url[-30:]}")
                else:
                    print(f"  [{j}] URL无查询参数")
        break

if __name__ == '__main__':
    output_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260729.json'
    check_search_items(output_file)
