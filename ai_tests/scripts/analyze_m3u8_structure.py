#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 m3u8 链接技术结构（输出安全：只输出技术字段，不输出域名/URL/内容）

输出内容：
1. HTTP 状态码 / Content-Type / 是否支持 Range
2. m3u8 结构：#EXT 标签类型统计 / TS 分段数 / 加密方式
3. 重定向链（只输出路径模式，不输出域名）

禁止输出：完整 URL / 域名 / cookie / 业务内容文本
"""
import sys
import re

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import requests
except ImportError:
    print("ERROR: requests not installed, run: pip install requests")
    sys.exit(1)

# 目标链接（脚本内部使用，输出时脱敏为路径模式）
TARGET_URL = "https://ehapp2.dd.bcdfga.com/cshort/Vfg2aveSDps.m3u8"

# 模拟 Chrome 移动版 UA
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": "https://ehapp2.dd.bcdfga.com/",
}


def sanitize_url(url):
    """URL 脱敏：只保留路径模式，隐藏域名"""
    # 提取 path 部分
    m = re.match(r'https?://[^/]+(/.*)', url)
    return m.group(1) if m else "/{path}"


def analyze():
    print("=" * 60)
    print("m3u8 Technical Structure Analysis")
    print("=" * 60)
    print(f"Target path: {sanitize_url(TARGET_URL)}")
    print()

    # 请求 m3u8
    try:
        r = requests.get(TARGET_URL, headers=HEADERS, timeout=15, allow_redirects=True)
    except requests.exceptions.SSLError as e:
        print(f"[SSL] SSL handshake failed: {type(e).__name__}")
        print(f"[SSL] This confirms CDN TLS fingerprinting blocks requests library")
        return
    except Exception as e:
        print(f"[ERROR] Request failed: {type(e).__name__}: {e}")
        return

    print(f"HTTP status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
    print(f"Accept-Ranges: {r.headers.get('Accept-Ranges', 'N/A')}")
    print(f"Final path (after redirect): {sanitize_url(r.url)}")
    print(f"Redirect count: {len(r.history)}")
    for i, h in enumerate(r.history):
        print(f"  redirect[{i}]: {h.status_code} -> {sanitize_url(h.url)}")
    print()

    if r.status_code != 200:
        print(f"[ERROR] HTTP {r.status_code}, body length: {len(r.text)}")
        return

    content = r.text
    lines = content.split('\n')

    # 统计 #EXT 标签
    ext_tags = {}
    for line in lines:
        if line.startswith('#EXT'):
            tag_name = line.split(':')[0] if ':' in line else line
            ext_tags[tag_name] = ext_tags.get(tag_name, 0) + 1

    print("--- m3u8 Structure ---")
    print(f"Total lines: {len(lines)}")
    print(f"EXT tag types: {len(ext_tags)}")
    for tag, count in sorted(ext_tags.items()):
        print(f"  {tag}: {count}")
    print()

    # TS 分段统计
    ts_count = sum(1 for l in lines if l and not l.startswith('#'))
    print(f"TS segments: {ts_count}")
    print()

    # 加密信息（只输出方法，不输出 URI）
    key_lines = [l for l in lines if l.startswith('#EXT-X-KEY')]
    print(f"Encryption: {'YES' if key_lines else 'NO'}")
    for k in key_lines:
        # 解析 METHOD= 和 KEYFORMAT= 等字段，不输出 URI
        fields = {}
        # 简单解析：按逗号分割，再按等号分割
        parts = k.split(':')[-1]  # 去掉 #EXT-X-KEY:
        for part in parts.split(','):
            if '=' in part:
                k_name, k_val = part.split('=', 1)
                if k_name.upper() != 'URI':  # 不输出 URI
                    fields[k_name] = k_val.strip('"')
        print(f"  Key fields: {fields}")
    print()

    # TS 分段路径模式（只输出前3个的路径模式，不输出完整URL）
    ts_urls = [l for l in lines if l and not l.startswith('#')]
    if ts_urls:
        print("--- TS segment path patterns (first 3) ---")
        for ts in ts_urls[:3]:
            print(f"  {sanitize_url(ts)}")
        if len(ts_urls) > 3:
            print(f"  ... ({len(ts_urls) - 3} more)")
    print()

    # 检查是否为 master playlist（多码率）
    stream_lines = [l for l in lines if l.startswith('#EXT-X-STREAM-INF')]
    if stream_lines:
        print(f"Master playlist: YES ({len(stream_lines)} variants)")
        for s in stream_lines:
            # 输出 BANDWIDTH 等技术字段
            bandwidth = re.search(r'BANDWIDTH=(\d+)', s)
            resolution = re.search(r'RESOLUTION=(\d+x\d+)', s)
            print(f"  Variant: BW={bandwidth.group(1) if bandwidth else 'N/A'} "
                  f"RES={resolution.group(1) if resolution else 'N/A'}")
    else:
        print("Master playlist: NO (media playlist)")
    print()

    print("=" * 60)
    print("Analysis complete (technical fields only, no domain/URL/content)")


if __name__ == '__main__':
    analyze()
