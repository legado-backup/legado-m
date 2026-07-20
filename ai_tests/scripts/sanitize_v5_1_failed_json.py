#!/usr/bin/env python3
"""sanitize_v5_1_failed_json.py — 脱敏失败源JSON

将 source_name 替换为代号（src_xxx），将 source_url 替换为路径模式（站点A/path/{id}）。
禁止输出真实源名称/域名/URL。
"""
import json
import re
from pathlib import Path

FAILED_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_1_real_device_verify_failed_sources.json')
SUCCESS_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_1_real_device_verify_success_sources.json')


def sanitize_url(url, idx):
    """URL脱敏：https://example.com/path?query → 站点X/path模式"""
    if not url:
        return ''
    if not url.startswith(('http://', 'https://')):
        # 非http开头的占位符源：用"占位符"替代
        return f'placeholder_no_http_(len={len(url)})'
    # 提取协议+域名
    m = re.match(r'(https?)://([^/]+)(.*)', url)
    if not m:
        return f'http_url_(len={len(url)})'
    proto, domain, path = m.groups()
    # 域名用代号替代
    return f'{proto}://站点X{path[:30]}...(len={len(url)})'


def sanitize_source_name(name, idx):
    """源名称脱敏：替换为src_xxx"""
    if not name:
        return f'src_{idx:03d}'
    return f'src_{idx:03d}'  # 完全替换为代号，不保留任何原文


def sanitize_file(path):
    if not path.exists():
        print(f'  文件不存在: {path}')
        return
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 清理 failed_sources 列表
    if 'failed_sources' in data:
        for item in data['failed_sources']:
            idx = item.get('idx', 0)
            if 'source_name' in item:
                item['source_name'] = sanitize_source_name(item['source_name'], idx)
            if 'source_url' in item:
                item['source_url'] = sanitize_url(item['source_url'], idx)

    # 清理 success_sources 列表
    if 'success_sources' in data:
        for item in data['success_sources']:
            idx = item.get('idx', 0)
            if 'source_name' in item:
                item['source_name'] = sanitize_source_name(item['source_name'], idx)
            if 'source_url' in item:
                item['source_url'] = sanitize_url(item['source_url'], idx)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  ✅ 已脱敏: {path}')


def main():
    print('=== 脱敏失败/成功源JSON ===')
    sanitize_file(FAILED_JSON)
    sanitize_file(SUCCESS_JSON)
    print('=== 完成 ===')


if __name__ == '__main__':
    main()
