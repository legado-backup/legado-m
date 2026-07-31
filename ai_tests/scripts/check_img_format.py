#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查搜索返回JSON中img字段格式(只看URL结构,不输出业务内容)"""
import requests
import re
import json
import urllib.parse
import warnings
warnings.filterwarnings("ignore")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

ENTRY = "https://cc.tianlai48.cfd"

def get_domain(entry_url):
    resp = requests.get(entry_url, headers=HEADERS, timeout=15, allow_redirects=True, verify=False)
    html = resp.text
    m = re.search(r'href="(https?://xn--[^"]+)"', html)
    if not m:
        m = re.search(r'window\.location\.href="(https?://xn--[^"]+)"', html)
    if m:
        u = m.group(1)
        p = u.index("://")
        a = u[p+3:]
        s = a.find("/")
        return a[:s] if s > 0 else a
    return None

domain = get_domain(ENTRY)
print(f"[DOMAIN] len={len(domain)}")

# 搜索
search_url = f"https://{domain}/?m=searchall_async&api=sh&p=1&k=test&mod=jump"
resp = requests.get(search_url, headers=HEADERS, timeout=20, verify=False)
data = json.loads(resp.text)
lst = data.get("list", [])
print(f"[LIST LEN] {len(lst)}")

if lst:
    first = lst[0]
    img = first.get("img", "")
    # 只检查URL格式,不输出内容
    print(f"[IMG FIELD]")
    print(f"  len={len(img)}")
    print(f"  starts_with_http={img.startswith('http')}")
    print(f"  starts_with_slash={img.startswith('/')}")
    print(f"  starts_with_data={img.startswith('data:')}")
    if not img.startswith("http") and not img.startswith("data:"):
        print(f"  [RELATIVE PATH] 需要补全域名")
        print(f"  prefix={img[:20]}...")
    else:
        print(f"  [ABSOLUTE URL] 完整URL")
        # 测试图片是否可访问
        try:
            img_resp = requests.get(img, headers=HEADERS, timeout=10, verify=False)
            print(f"  [IMG STATUS] {img_resp.status_code}")
            print(f"  [IMG CONTENT-TYPE] {img_resp.headers.get('Content-Type', 'N/A')}")
            print(f"  [IMG SIZE] {len(img_resp.content)} bytes")
        except Exception as e:
            print(f"  [IMG ERROR] {type(e).__name__}: {str(e)[:80]}")
