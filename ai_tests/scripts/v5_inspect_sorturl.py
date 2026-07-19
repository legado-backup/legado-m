#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v5_inspect_sorturl.py — 检查14个集成站sortUrl的URL路径模式（脱敏）

输出：每个父源的sortUrl条目数、URL路径模式分布、首条结构
不输出：真实URL/域名/源名称/分类名
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v2_lite_final_v4.json"

AGGREGATOR_INDICES = [27, 32, 41, 87, 110, 117, 120, 121, 123, 128, 131, 147, 150, 151]


def parse_sort_url(sort_url):
    """返回 [(脱敏路径模式, 是否@js)]"""
    if not sort_url:
        return []
    if sort_url.lstrip().startswith('@js'):
        urls = re.findall(r"https?://[^\s\"'\\,)]+", sort_url)
        return [('@js_extracted', True) for _ in urls]
    items = []
    for line in sort_url.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '::' in line:
            cat_url = line.split('::', 1)[1].strip()
        else:
            cat_url = line
        if cat_url and cat_url.startswith('http'):
            items.append((cat_url, False))
    return items


def path_pattern(url):
    """将URL转为路径模式，去除值"""
    try:
        p = urlparse(url)
        path = p.path or '/'
        # 将数字ID替换为 {id}
        path = re.sub(r'/\d+', '/{id}', path)
        # 将 query 中的值替换
        if p.query:
            q = re.sub(r'=\S+', '=[V]', p.query)
            path += '?' + q
        return path
    except Exception:
        return '[PARSE_ERR]'


def main():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    sources = data['sources']

    print("=" * 80)
    print("14个集成站 sortUrl 路径模式分析（脱敏）")
    print("=" * 80)

    for idx in AGGREGATOR_INDICES:
        if idx >= len(sources):
            print(f"\n[idx={idx}] 越界")
            continue
        sort_url = sources[idx].get('sortUrl', '') or ''
        items = parse_sort_url(sort_url)

        if not items:
            print(f"\n[idx={idx}] sortUrl无URL, length={len(sort_url)}")
            continue

        # 第一个条目是否@js
        is_js = items[0][1] if items else False

        # 统计路径模式
        patterns = Counter()
        for url, _ in items:
            patterns[path_pattern(url)] += 1

        print(f"\n[idx={idx}] 条目数={len(items)} is_js={is_js} sortUrl长度={len(sort_url)}")
        print(f"  路径模式分布（前5）:")
        for pat, cnt in patterns.most_common(5):
            print(f"    {pat}  x{cnt}")

        # 输出第一条URL的脱敏结构
        if items:
            first_url = items[0][0]
            p = urlparse(first_url)
            print(f"  首条: scheme={p.scheme} host=[DOMAIN] path={p.path or '/'} query_len={len(p.query)}")


if __name__ == '__main__':
    main()
