#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试正确的 Sway embed 路径 /s/{id}/embed 及其他变体。
"""
import re
import json
from urllib.parse import urlparse

import requests

SWAY_DOC_ID = "9fNLFiE39CvqVsBq"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15

MS_DOMAINS = (
    "microsoft.com", "microsoftonline.com", "microsoft.net", "microsoft365.com",
    "office.com", "office365.com", "office-int.com", "office-int.net",
    "office.net", "officeppe.com", "officeppe.net",
    "live.com", "live.net", "live-int.com",
    "msn.com", "bing.com", "bing.net", "bingapis.com",
    "sway.cloud.microsoft", "sway.com", "sway.office.com",
    "sway-cdn.com", "sway-edog.com", "sway-int.com",
    "azure.com", "azure.net", "azureedge.net", "azurefd.net",
    "azure-api.net", "azurewebsites.net", "cloudapp.net",
    "trafficmanager.net", "windows-ppe.net",
    "akamai.net", "akamaized.net",
    "skype.com", "xbox.com", "windows.net",
    "onmicrosoft.com", "sharepoint.com",
    "msecnd.net", "msftauth.net", "msauth.net",
    "trouter.io", "cloud.microsoft", "cloud-dev.microsoft",
    "1drv.ms", "onedrive.com", "aka.ms", "gfx.ms",
    "docs.com", "int-docs.com", "contentvalidation.com",
    "static.microsoft", "onenote.com", "linkedin.com",
)


def is_ms(host):
    host = host.lower().lstrip(".")
    for d in MS_DOMAINS:
        if host == d or host.endswith("." + d):
            return True
    return False


def safe_url(raw):
    try:
        p = urlparse(raw)
    except Exception:
        return None
    host = p.netloc.lower()
    if not host:
        return None
    parts = host.split(".")
    suffix = "." + ".".join(parts[-2:]) if len(parts) >= 2 else host
    path = p.path or "/"
    path = re.sub(r"/\d{3,}", "/{id}", path)
    path = re.sub(r"/[a-f0-9]{8,}", "/{hash}", path)
    path = re.sub(r"/[A-Z0-9]{10,}", "/{id}", path)
    return f"{suffix}{path}"


def scan_urls(text, label):
    """扫描文本中的URL，输出非MS的安全化URL。"""
    urls = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', text)
    non_ms = []
    for u in urls:
        try:
            h = urlparse(u).netloc.lower()
            if not is_ms(h):
                non_ms.append(safe_url(u))
        except Exception:
            pass
    print(f"  [{label}] URL总数={len(urls)} 非MS={len(non_ms)}")
    if non_ms:
        print(f"  [{label}] 非MS URL(安全化): {sorted(set(non_ms))}")
    return non_ms


# 测试变体URL
test_urls = [
    f"https://sway.cloud.microsoft/s/{SWAY_DOC_ID}/embed",
    f"https://sway.cloud.microsoft/s/{SWAY_DOC_ID}",
    f"https://sway.cloud.microsoft/s/{SWAY_DOC_ID}/print",
    f"https://sway.cloud.microsoft/s/{SWAY_DOC_ID}/read",
    f"https://sway.cloud.microsoft/s/{SWAY_DOC_ID}/view",
    # 直接尝试 fetch embed iframe 内容
    f"https://sway.cloud.microsoft/embed/{SWAY_DOC_ID}?e=...",
]

print("=== 测试 Sway 路径变体 ===\n")
for tu in test_urls:
    try:
        r = requests.get(tu, headers={"User-Agent": UA, "Accept": "text/html"}, timeout=TIMEOUT, allow_redirects=True)
        body = r.text or ""
        print(f"URL: {safe_url(tu)}")
        print(f"  status={r.status_code} size={len(body)} redirects={len(r.history)} final_url={safe_url(r.url) if r.url != tu else 'same'}")
        if r.status_code == 200 and len(body) < 100000:
            # 检查是否是SPA shell（含StoryPage相关JS）
            has_story = "StoryPage" in body or "sway" in body.lower()
            has_content = len(body) > 60000  # 真正的内容页通常更大
            print(f"  含StoryPage标识={has_story} 大小判定={'内容页' if has_content else 'SPA shell'}")
            # 扫描URL
            scan_urls(body, "URLs")
            # 检查内联script中的大数据块
            scripts = re.findall(r'<script(?![^>]+src=)[^>]*>(.*?)</script>', body, flags=re.DOTALL)
            big_scripts = [(i, s) for i, s in enumerate(scripts) if len(s.strip()) > 1000]
            if big_scripts:
                print(f"  内联script块数={len(scripts)} 大块(>1KB)={len(big_scripts)}")
                for i, s in big_scripts[:3]:
                    s_strip = s.strip()
                    print(f"    [块#{i}] 长度={len(s_strip)} 预览={s_strip[:100]!r}")
        elif r.status_code == 200:
            print(f"  200但响应过大({len(body)}字节)，可能是错误页")
        print()
    except Exception as e:
        print(f"URL: {safe_url(tu)}")
        print(f"  ERROR: {str(e)[:100]}\n")

# 尝试用 Google cache / web archive 获取渲染后的内容
print("=== 尝试 Web Archive 缓存 ===")
archive_urls = [
    f"https://web.archive.org/web/2025/https://sway.cloud.microsoft/{SWAY_DOC_ID}",
    f"https://web.archive.org/web/2025/https://sway.cloud.microsoft/s/{SWAY_DOC_ID}/embed",
]
for au in archive_urls:
    try:
        r = requests.get(au, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
        body = r.text or ""
        print(f"URL: {safe_url(au)}")
        print(f"  status={r.status_code} size={len(body)} final={safe_url(r.url)}")
        if r.status_code == 200:
            scan_urls(body, "archive")
        print()
    except Exception as e:
        print(f"URL: {safe_url(au)} ERROR: {str(e)[:100]}\n")

print("=== 完成 ===")
