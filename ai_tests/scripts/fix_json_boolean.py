#!/usr/bin/env python3
"""fix_json_boolean.py — 修复JSON中boolean字段为数字类型的问题

问题：Gson解析期望boolean是true/false，但JSON中写成了1/0
修复：把所有boolean字段从1/0改为true/false
"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
LITE_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_lite_v2.json'

# 必须转换的boolean字段（来自RssSource.kt）
BOOLEAN_FIELDS = {
    'enabled',
    'enabledCookieJar',
    'singleUrl',
    'enableJs',
    'loadWithBaseUrl',
    'showWebLog',
    'preload',
    'cacheFirst',
}


def fix_booleans(obj):
    """递归修复boolean字段"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in BOOLEAN_FIELDS:
                if value == 1:
                    obj[key] = True
                elif value == 0:
                    obj[key] = False
            elif isinstance(value, (dict, list)):
                fix_booleans(value)
    elif isinstance(obj, list):
        for item in obj:
            fix_booleans(item)


def main():
    print('=' * 60)
    print('修复JSON boolean字段（1/0 → true/false）')
    print('=' * 60)

    # 修复完整版
    print('\n--- 修复完整版 ---')
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fix_booleans(data)

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已修复: {JSON_PATH}')

    # 修复精简版
    print('\n--- 修复精简版 ---')
    with open(LITE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fix_booleans(data)

    with open(LITE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已修复: {LITE_PATH}')

    # 验证
    print('\n--- 验证 ---')
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 检查第一个源的boolean字段
    first = data[0]
    for field in BOOLEAN_FIELDS:
        val = first.get(field)
        if val is not None:
            print(f'  {field}: {val} (type={type(val).__name__})')

    print('\n✅ 修复完成！')


if __name__ == '__main__':
    main()
