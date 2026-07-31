#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量优化源[5]（fixed聚合源）的36个CMS API子源
在每个子源的sortUrl末尾追加搜索分类项
输出安全：只输出技术统计，不输出业务数据
"""
import json
import sys
import os
import time
import requests
from urllib.parse import urlparse, parse_qs, urlencode

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
TIMEOUT = 10  # 秒
MAX_CATEGORIES = 8  # 每个子源最多追加8个搜索分类

def get_categories(base_url):
    """访问 ?ac=list 获取分类列表"""
    try:
        # 构造API URL
        if '?' in base_url:
            api_url = base_url + '&ac=list'
        else:
            api_url = base_url + '?ac=list'

        resp = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            return None, f"HTTP_{resp.status_code}"

        # 解析JSON
        data = resp.json()
        # MacCMS API返回格式: {"class": [{"type_id": 1, "type_name": "xxx", "type_pid": 0}]}
        classes = data.get('class', [])
        if not classes:
            return None, "NO_CLASS"

        # 筛选一级分类（type_pid=0）
        categories = []
        for c in classes:
            type_id = c.get('type_id')
            type_name = c.get('type_name', '')
            type_pid = c.get('type_pid', 0)
            if type_id and type_name and type_pid == 0:
                categories.append({'id': type_id, 'name': type_name})

        return categories, f"OK_{len(categories)}"
    except requests.exceptions.Timeout:
        return None, "TIMEOUT"
    except requests.exceptions.ConnectionError:
        return None, "CONN_ERROR"
    except json.JSONDecodeError:
        return None, "JSON_ERROR"
    except Exception as e:
        return None, f"ERROR_{type(e).__name__}"

def build_search_sort_items(base_url, search_url_template, categories):
    """为CMS API子源构建搜索分类项"""
    items = []
    # 精选前MAX_CATEGORIES个分类
    for cat in categories[:MAX_CATEGORIES]:
        cat_id = cat['id']
        cat_name = cat['name']
        # 构建搜索URL: 在searchUrl基础上追加 &t={catId}
        # searchUrl模板通常是: {base}?ac=list&wd={{key}} 或 {base}?ac=list&wd={{key}}&pg={{page}}
        # 搜索分类项: 搜索{分类名}::{base}?ac=list&wd={{key}}&t={catId}
        if '?' in base_url:
            search_entry = f"{base_url}?ac=list&wd={{{{key}}}}&t={cat_id}"
        else:
            search_entry = f"{base_url}?ac=list&wd={{{{key}}}}&t={cat_id}"
        items.append(f"搜索{cat_name}::{search_entry}")
    return items

def optimize_source(source_file, output_file):
    """批量优化源[5]"""
    with open(source_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"=== 源[5]批量优化开始 ===")
    print(f"总子源数: {len(sources)}")
    print(f"最大搜索分类数/子源: {MAX_CATEGORIES}")
    print()

    stats = {
        'total': len(sources),
        'cms_optimized': 0,
        'cms_failed': 0,
        'path_skipped': 0,
        'other_skipped': 0,
        'total_cats_added': 0,
    }

    failed_list = []  # 记录失败的子源序号和原因

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
            continue

        # CMS API子源优化
        # 提取基础URL（去掉查询参数）
        parsed = urlparse(source_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # 获取分类列表
        categories, status = get_categories(base_url)

        if categories is None or len(categories) == 0:
            stats['cms_failed'] += 1
            failed_list.append((i, status))
            print(f"  子源[{i}]: 失败 - {status}")
            continue

        # 构建搜索分类项
        search_items = build_search_sort_items(base_url, search_url, categories)

        if not search_items:
            stats['cms_failed'] += 1
            failed_list.append((i, "NO_SEARCH_ITEMS"))
            print(f"  子源[{i}]: 失败 - 无搜索分类项")
            continue

        # 在sortUrl末尾追加搜索分类项
        # 注意：sortUrl中的换行符是 \\n（字面量），不是实际的换行符
        if sort_url and not sort_url.endswith('\\n'):
            new_sort_url = sort_url + '\\n' + '\\n'.join(search_items)
        elif sort_url:
            new_sort_url = sort_url + '\\n'.join(search_items)
        else:
            new_sort_url = '\\n'.join(search_items)

        src['sortUrl'] = new_sort_url
        stats['cms_optimized'] += 1
        stats['total_cats_added'] += len(search_items)
        print(f"  子源[{i}]: 成功 - 追加{len(search_items)}个搜索分类 ({status})")

        # 礼貌延迟，避免请求过快
        time.sleep(0.5)

    # 保存优化后的JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    print()
    print(f"=== 优化统计 ===")
    print(f"总子源数: {stats['total']}")
    print(f"CMS API优化成功: {stats['cms_optimized']}")
    print(f"CMS API失败: {stats['cms_failed']}")
    print(f"路径式跳过: {stats['path_skipped']}")
    print(f"其他跳过: {stats['other_skipped']}")
    print(f"追加搜索分类总数: {stats['total_cats_added']}")
    print()
    if failed_list:
        print(f"=== 失败子源清单 ===")
        for idx, reason in failed_list:
            print(f"  子源[{idx}]: {reason}")
    print()
    print(f"输出文件: {output_file}")

    return stats

if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    source_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260725.json'
    output_file = r'f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rssSource_video_fixed_20260729.json'

    if not os.path.exists(source_file):
        print(f"错误: 源文件不存在 {source_file}")
        sys.exit(1)

    optimize_source(source_file, output_file)
