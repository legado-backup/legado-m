#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析源[5]（fixed聚合源）的技术结构
输出安全：只输出技术信息（子源序号/类型/searchUrl模式/sortUrl分类数），不输出业务数据
"""
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

def analyze_source(source_file):
    """分析源JSON文件的技术结构"""
    with open(source_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== 源[5]技术结构分析 ===")
    print(f"总子源数: {len(sources)}")
    print()

    cms_api_sources = []
    path_sources = []
    other_sources = []

    for i, src in enumerate(sources):
        # 提取技术字段（不输出业务数据）
        search_url = src.get('searchUrl', '')
        sort_url = src.get('sortUrl', '')
        source_url = src.get('sourceUrl', '')
        source_type = src.get('type', 0)

        # 判断子源类型
        is_cms_api = 'ac=list' in search_url or 'ac=list' in sort_url
        is_path_search = '/search/' in search_url or '/vodsearch/' in search_url or '/index.php/vod/search' in search_url

        # 统计sortUrl中的分类数量
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        sort_count = len(sort_lines)

        # 提取searchUrl的技术模式（不输出完整URL）
        if 'ac=list' in search_url:
            search_mode = 'CMS_API_list'
        elif 'ac=detail' in search_url:
            search_mode = 'CMS_API_detail'
        elif '/search/' in search_url or '/vodsearch/' in search_url:
            search_mode = 'PATH_search'
        elif '/index.php/vod/search' in search_url:
            search_mode = 'Maccms_vod_search'
        elif not search_url:
            search_mode = 'EMPTY'
        else:
            search_mode = 'OTHER'

        # 提取sourceUrl的域名模式（只输出域名，不输出完整路径）
        try:
            parsed = urlparse(source_url)
            domain = parsed.netloc if parsed.netloc else 'NO_DOMAIN'
            # 脱敏：只保留域名结构，不输出具体域名
            domain_pattern = f"DOMAIN_{len(domain)}chars"
        except:
            domain_pattern = 'PARSE_ERROR'

        info = {
            'index': i,
            'type': source_type,
            'search_mode': search_mode,
            'sort_count': sort_count,
            'domain_pattern': domain_pattern,
            'has_sortUrl': bool(sort_url),
            'has_searchUrl': bool(search_url),
        }

        if is_cms_api or search_mode in ('CMS_API_list', 'CMS_API_detail'):
            cms_api_sources.append(info)
        elif is_path_search or search_mode in ('PATH_search', 'Maccms_vod_search'):
            path_sources.append(info)
        else:
            other_sources.append(info)

    print(f"=== 分类统计 ===")
    print(f"CMS API子源: {len(cms_api_sources)}")
    print(f"路径式搜索子源: {len(path_sources)}")
    print(f"其他/无搜索子源: {len(other_sources)}")
    print()

    print(f"=== CMS API子源清单（待优化）===")
    for s in cms_api_sources:
        print(f"  子源[{s['index']}]: type={s['type']} search={s['search_mode']} sortLines={s['sort_count']} {s['domain_pattern']}")
    print()

    print(f"=== 路径式搜索子源清单 ===")
    for s in path_sources:
        print(f"  子源[{s['index']}]: type={s['type']} search={s['search_mode']} sortLines={s['sort_count']} {s['domain_pattern']}")
    print()

    print(f"=== 其他/无搜索子源清单 ===")
    for s in other_sources:
        print(f"  子源[{s['index']}]: type={s['type']} search={s['search_mode']} sortLines={s['sort_count']} {s['domain_pattern']} sortUrl={'有' if s['has_sortUrl'] else '无'} searchUrl={'有' if s['has_searchUrl'] else '无'}")
    print()

    # 输出CMS API子源的sortUrl分类结构样本（第1个）
    if cms_api_sources:
        first_idx = cms_api_sources[0]['index']
        src = sources[first_idx]
        sort_url = src.get('sortUrl', '')
        sort_lines = [line.strip() for line in sort_url.split('\\n') if line.strip()]
        print(f"=== CMS API子源[{first_idx}] sortUrl结构样本（前5行）===")
        for j, line in enumerate(sort_lines[:5]):
            # 只输出分类名称和URL模式，不输出完整URL
            if '::' in line:
                cat_name, cat_url = line.split('::', 1)
                # 提取URL参数模式
                parsed = urlparse(cat_url)
                query = parse_qs(parsed.query)
                if 't' in query:
                    param_info = f"t={query['t'][0]}"
                else:
                    param_info = f"path={parsed.path}"
                print(f"  分类[{j}]: 名称长度={len(cat_name)} 参数={param_info}")
            else:
                print(f"  分类[{j}]: {line[:50]}...")
        print()

    return cms_api_sources, path_sources, other_sources

if __name__ == '__main__':
    source_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260725.json'
    if not os.path.exists(source_file):
        print(f"错误: 文件不存在 {source_file}")
        sys.exit(1)
    analyze_source(source_file)
