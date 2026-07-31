#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跟随重定向后调试入口URL返回内容(模拟java.ajax行为)
"""
import requests
import re
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
    print(f"[URL] entry")
    try:
        # 跟随重定向(模拟java.ajax默认行为)
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True, verify=False)
        print(f"[FINAL STATUS] {resp.status_code}")
        print(f"[FINAL URL] len={len(resp.url)}")
        print(f"[CONTENT-TYPE] {resp.headers.get('Content-Type', 'N/A')}")
        body = resp.text
        print(f"[BODY LEN] {len(body)}")
        # 检查是否含xn--域名(在href中)
        m1 = re.findall(r'href="(https?://xn--[^"]+)"', body)
        print(f"[HREF XN DOMAINS] count={len(m1)}")
        # 检查window.location.href
        m2 = re.findall(r'window\.location\.href="(https?://xn--[^"]+)"', body)
        print(f"[WINDOW.LOCATION XN] count={len(m2)}")
        # 如果都没匹配到，输出body前300字符看结构
        if not m1 and not m2:
            print(f"[BODY HEAD 300] {body[:300]}")
        else:
            if m1:
                d = m1[0]
                p = d.index("://")
                a = d[p+3:]
                s = a.find("/")
                domain = a[:s] if s > 0 else a
                print(f"[EXTRACTED DOMAIN] len={len(domain)}")
            if m2:
                d = m2[0]
                p = d.index("://")
                a = d[p+3:]
                s = a.find("/")
                domain = a[:s] if s > 0 else a
                print(f"[EXTRACTED DOMAIN2] len={len(domain)}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)[:150]}")
