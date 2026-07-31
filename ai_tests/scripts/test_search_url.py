#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证搜索URL是否能返回有效JSON
仅输出技术结论(状态码/内容类型/JSON字段)，不输出业务数据
"""
import requests
import re
import json
import urllib.parse
import sys

# 入口URL配置(从JSON读取)
ENTRY_CONFIG = [
    {"entry": "https://cc.tianlai48.cfd", "cache_key": "tianlai_v5"},
    {"entry": "https://aa.lusevip48.cfd", "cache_key": "lusevip_v5"},
    {"entry": "https://bb.qingse48.cfd", "cache_key": "qingse_v5"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

SEARCH_KEYWORD = "test"  # 测试关键词

def get_dynamic_domain(entry_url):
    """从安全检测页提取punycode域名"""
    try:
        resp = requests.get(entry_url, headers=HEADERS, timeout=15, allow_redirects=False, verify=False)
        html = resp.text
        # 匹配 href="https://xn--..." 或 window.location.href="https://xn--..."
        m = re.search(r'href="(https?://xn--[^"]+)"', html)
        if not m:
            m = re.search(r'window\.location\.href="(https?://xn--[^"]+)"', html)
        if m:
            u = m.group(1)
            p = u.index("://")
            a = u[p+3:]
            s = a.find("/")
            domain = a[:s] if s > 0 else a
            return domain
        return None
    except Exception as e:
        print(f"[ERROR] 获取域名失败: {type(e).__name__}: {e}")
        return None

def test_search_url(domain, keyword):
    """测试搜索URL"""
    search_url = f"https://{domain}/?m=searchall_async&api=sh&p=1&k={urllib.parse.quote(keyword)}&mod=jump"
    print(f"\n[SEARCH URL] /path?m=searchall_async&api=sh&p=1&k=***&mod=jump")
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=20, verify=False)
        print(f"[STATUS] {resp.status_code}")
        print(f"[CONTENT-TYPE] {resp.headers.get('Content-Type', 'N/A')}")
        body = resp.text
        print(f"[BODY LEN] {len(body)}")
        # 尝试解析JSON
        try:
            data = json.loads(body)
            print(f"[JSON] 解析成功")
            if isinstance(data, dict):
                print(f"[JSON KEYS] {list(data.keys())}")
                if "list" in data:
                    lst = data["list"]
                    print(f"[LIST LEN] {len(lst) if isinstance(lst, list) else 'not-list'}")
                    if isinstance(lst, list) and len(lst) > 0:
                        first = lst[0]
                        if isinstance(first, dict):
                            print(f"[FIRST ITEM KEYS] {list(first.keys())}")
                else:
                    print(f"[WARN] 无 list 字段")
            else:
                print(f"[JSON TYPE] {type(data).__name__}")
        except json.JSONDecodeError as e:
            print(f"[JSON] 解析失败: {e}")
            # 检查是否是HTML
            if "<html" in body[:500].lower() or "<!DOCTYPE" in body[:500]:
                print(f"[HTML] 响应为HTML页面")
            print(f"[BODY HEAD] {body[:200]}")
        return True
    except Exception as e:
        print(f"[ERROR] 请求失败: {type(e).__name__}: {e}")
        return False

def main():
    import warnings
    warnings.filterwarnings("ignore")
    
    for cfg in ENTRY_CONFIG[:1]:  # 只测第一个源
        entry = cfg["entry"]
        print(f"\n{'='*60}")
        print(f"[ENTRY] {entry}")
        domain = get_dynamic_domain(entry)
        if not domain:
            print(f"[FAIL] 无法获取动态域名")
            continue
        print(f"[DOMAIN] {domain[:30]}...(punycode)")
        # 测试搜索
        test_search_url(domain, SEARCH_KEYWORD)

if __name__ == "__main__":
    main()
