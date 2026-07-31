#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试入口URL返回内容(只输出技术信息,不输出业务数据)
"""
import requests
import warnings
warnings.filterwarnings("ignore")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

ENTRY_URLS = [
    "https://cc.tianlai48.cfd",
    "https://aa.lusevip48.cfd",
    "https://bb.qingse48.cfd",
    "https://ww.wowo47.cfd",
]

for url in ENTRY_URLS:
    print(f"\n{'='*50}")
    print(f"[URL] entry-1")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=False, verify=False)
        print(f"[STATUS] {resp.status_code}")
        print(f"[CONTENT-TYPE] {resp.headers.get('Content-Type', 'N/A')}")
        print(f"[LOCATION] {resp.headers.get('Location', 'N/A')[:60] if resp.headers.get('Location') else 'N/A'}")
        body = resp.text
        print(f"[BODY LEN] {len(body)}")
        # 只输出技术结构,不输出业务数据
        # 检查是否含xn--域名
        import re
        m1 = re.findall(r'(https?://xn--[a-z0-9-]+)', body)
        print(f"[XN DOMAINS] count={len(m1)}")
        if m1:
            for i, d in enumerate(m1[:3]):
                # 只输出域名长度和前缀,不输出完整域名
                print(f"  [DOMAIN {i}] len={len(d)} prefix=xn--{d[12:20]}...")
        # 检查是否有window.location
        if "window.location" in body:
            print(f"[JS REDIRECT] 含window.location")
        # 检查是否有href=
        if "href=" in body:
            print(f"[HTML] 含href属性")
        # 输出前200字符的技术结构(去除业务内容)
        # 只输出HTML标签结构
        tags = re.findall(r'<[^>]+>', body[:500])
        print(f"[HTML TAGS] {tags[:5]}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)[:100]}")
