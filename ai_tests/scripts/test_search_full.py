#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试搜索流程：获取动态域名 -> 测试搜索URL -> 验证JSON格式
仅输出技术结论
"""
import requests
import re
import json
import urllib.parse
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

def get_dynamic_domain(entry_url):
    """模拟JS的域名提取逻辑(跟随重定向)"""
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

def test_search(domain, keyword):
    """测试搜索URL"""
    search_url = f"https://{domain}/?m=searchall_async&api=sh&p=1&k={urllib.parse.quote(keyword)}&mod=jump"
    print(f"[SEARCH URL PATH] /?m=searchall_async&api=sh&p=1&k=***&mod=jump")
    resp = requests.get(search_url, headers=HEADERS, timeout=20, verify=False)
    print(f"[STATUS] {resp.status_code}")
    print(f"[CONTENT-TYPE] {resp.headers.get('Content-Type', 'N/A')}")
    body = resp.text
    print(f"[BODY LEN] {len(body)}")
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            print(f"[JSON KEYS] {list(data.keys())}")
            if "list" in data:
                lst = data["list"]
                if isinstance(lst, list):
                    print(f"[LIST LEN] {len(lst)}")
                    if lst:
                        first = lst[0]
                        if isinstance(first, dict):
                            print(f"[FIRST ITEM KEYS] {list(first.keys())}")
                            # 检查id/title/img字段
                            for k in ["id", "title", "img"]:
                                print(f"  has {k}: {k in first}")
                else:
                    print(f"[LIST TYPE] {type(lst).__name__}")
            else:
                print(f"[NO LIST FIELD] keys={list(data.keys())[:5]}")
        else:
            print(f"[JSON TYPE] {type(data).__name__}")
        return True
    except json.JSONDecodeError:
        if "<html" in body[:500].lower():
            print(f"[HTML RESPONSE] 搜索返回HTML不是JSON")
        else:
            print(f"[NOT JSON] body head={body[:200]}")
        return False

for entry in ENTRY_URLS:
    print(f"\n{'='*60}")
    print(f"[ENTRY] source-1")
    domain = get_dynamic_domain(entry)
    if not domain:
        print(f"[FAIL] 无法获取域名")
        continue
    print(f"[DOMAIN OK] len={len(domain)}")
    # 测试搜索
    ok = test_search(domain, "test")
    if ok:
        print(f"[RESULT] 搜索URL有效")
    else:
        print(f"[RESULT] 搜索URL无效")
