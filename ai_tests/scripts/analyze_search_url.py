#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析源[5]的CMS API子源的searchUrl参数结构
输出安全：只输出技术参数模式，不输出完整URL
"""
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

def analyze_search_url_structure(source_file):
    """分析searchUrl的参数结构"""
    with open(source_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== CMS API子源searchUrl参数结构分析 ===")
    print()

    for i, src in enumerate(sources):
        search_url = src.get('searchUrl', '')
        sort_url = src.get('sortUrl', '')
        source_url = src.get('sourceUrl', '')

        # 判断是否CMS API
        is_cms_api = 'ac=list' in search_url or 'ac=list' in sort_url
        if not is_cms_api:
            continue

        # 分析sourceUrl的路径模式
        parsed_src = urlparse(source_url)
        src_path = parsed_src.path

        # 分析searchUrl的参数
        if '?' in search_url:
            search_base, search_query = search_url.split('?', 1)
            search_params = parse_qs(search_query)
        else:
            search_base = search_url
            search_params = {}

        # 分析sortUrl第1行
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        sort_first = sort_lines[0] if sort_lines else ''
        if '::' in sort_first:
            sort_name, sort_url_first = sort_first.split('::', 1)
            if '?' in sort_url_first:
                sort_base, sort_query = sort_url_first.split('?', 1)
                sort_params = parse_qs(sort_query)
            else:
                sort_params = {}
        else:
            sort_params = {}

        # 输出技术结构（不输出完整URL）
        print(f"子源[{i}]:")
        print(f"  sourceUrl路径: {src_path if src_path else '/'}")
        print(f"  searchUrl参数: {list(search_params.keys())}")
        print(f"  searchUrl有pg: {'pg' in search_params or 'page' in search_params}")
        print(f"  sortUrl参数: {list(sort_params.keys())}")
        print(f"  sortUrl有t: {'t' in sort_params}")
        if 't' in sort_params:
            print(f"  sortUrl的t值: {sort_params['t'][0]}")
        print()

if __name__ == '__main__':
    source_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260725.json'
    if not os.path.exists(source_file):
        print(f"错误: 文件不存在 {source_file}")
        sys.exit(1)
    analyze_search_url_structure(source_file)
