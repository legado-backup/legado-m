#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚焦分析：oembed v1.0 响应字段细节 + 主HTML中 CommonSettings 的 API 端点。
输出安全：不输出真实域名/URL/业务数据，只输出技术字段。
"""
import re
import json
from urllib.parse import urlparse

import requests

SWAY_DOC_ID = "9fNLFiE39CvqVsBq"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15

MS_DOMAINS = (
    "microsoft.com", "microsoftonline.com", "microsoft.net",
    "microsoft365.com", "microsoft-ppe.com",
    "office.com", "office365.com", "office-int.com", "office-int.net",
    "office.net", "officeppe.com", "officeppe.net",
    "live.com", "live.net", "live-int.com",
    "msn.com", "msn.net", "bing.com", "bing.net", "bingapis.com",
    "sway.cloud.microsoft", "sway.com", "sway.office.com",
    "sway-cdn.com", "sway-edog.com", "sway-int.com",
    "azure.com", "azure.net", "azureedge.net", "azurefd.net",
    "azure-api.net", "azurewebsites.net", "cloudapp.net",
    "trafficmanager.net", "windows-ppe.net",
    "akamai.net", "akamaized.net",
    "skype.com", "xbox.com", "windows.net",
    "onmicrosoft.com", "sharepoint.com",
    "msecnd.net", "msftauth.net", "msauth.net",
    "trouter.io", "trouter.skype.com",
    "cloud.microsoft", "cloud-dev.microsoft",
    "1drv.ms", "onedrive.com",
    "aka.ms", "gfx.ms",
    "docs.com", "int-docs.com", "contentvalidation.com",
    "static.microsoft",
    "onenote.com",
    "linkedin.com",
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
    qkeys = ""
    if p.query:
        ks = [kv.split("=")[0] for kv in p.query.split("&") if kv]
        qkeys = "?" + ",".join(sorted(set(ks))) if ks else ""
    return f"{suffix}{path}{qkeys}"


def main():
    print("=== oembed v1.0 字段细节 ===")
    url = f"https://sway.cloud.microsoft/api/v1.0/oembed?url=https%3a%2f%2fsway.cloud.microsoft%2f{SWAY_DOC_ID}&format=json"
    r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=TIMEOUT)
    print(f"status={r.status_code} size={len(r.text)}")
    oj = r.json()

    # title: 只输出长度和字符类型（不输出内容）
    title = oj.get("title", "")
    print(f"\ntitle: 长度={len(title)} 字符类型={'纯数字' if title.isdigit() else '含字母' if any(c.isalpha() for c in title) else '其他'}")

    # provider_url
    pu = oj.get("provider_url", "")
    print(f"provider_url: 长度={len(pu)} 安全化={safe_url(pu)} 是否MS域={is_ms(urlparse(pu).netloc)}")

    # thumbnail_url: 关键 - 可能指向子站
    tu = oj.get("thumbnail_url", "")
    print(f"thumbnail_url: 长度={len(tu)}")
    if tu:
        try:
            tp = urlparse(tu)
            host = tp.netloc.lower()
            print(f"  host={host} 是否MS域={is_ms(host)}")
            print(f"  安全化={safe_url(tu)}")
            # 检查路径模式
            print(f"  路径模式={re.sub(r'\\d+', '{n}', tp.path)}")
        except Exception as e:
            print(f"  解析失败: {e}")

    # html 字段：通常是 iframe embed 代码
    html_field = oj.get("html", "")
    print(f"\nhtml字段: 长度={len(html_field)}")
    if html_field:
        # 提取 iframe src
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_field)
        print(f"  iframe数: {len(iframes)}")
        for iu in iframes:
            print(f"  iframe src安全化: {safe_url(iu)}")
            try:
                ih = urlparse(iu).netloc.lower()
                print(f"    host={ih} 是否MS域={is_ms(ih)}")
            except Exception:
                pass
        # 提取所有URL
        all_urls = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', html_field)
        print(f"  URL总数: {len(all_urls)}")
        non_ms = []
        for u in all_urls:
            try:
                h = urlparse(u).netloc.lower()
                if not is_ms(h):
                    non_ms.append(safe_url(u))
            except Exception:
                pass
        print(f"  非MS URL: {sorted(set(non_ms))}")

    print("\n=== 主HTML CommonSettings 分析 ===")
    with open("ai_tests/output/sway_main.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 提取 CommonSettings JSON
    m = re.search(r'var\s+CommonSettings\s*=\s*(\{.*?\});\s*', html, flags=re.DOTALL)
    if m:
        cs_raw = m.group(1)
        print(f"CommonSettings 原始长度: {len(cs_raw)}")
        try:
            cs = json.loads(cs_raw)
            print(f"字段数: {len(cs)}")
            print(f"字段名: {sorted(cs.keys())}")
            # 寻找 URL/endpoint 相关字段
            for k, v in cs.items():
                if isinstance(v, str) and ("http" in v.lower() or "api" in k.lower() or "endpoint" in k.lower() or "url" in k.lower()):
                    # 安全化
                    if v.startswith("http"):
                        s = safe_url(v)
                        try:
                            h = urlparse(v).netloc.lower()
                            ms = is_ms(h)
                        except Exception:
                            ms = True
                        print(f"  {k}: 长度={len(v)} 是否MS域={ms} 安全化={s}")
                    else:
                        print(f"  {k}: 长度={len(v)} 值={v[:50] if len(v)<50 else v[:50]+'...'}")
                elif isinstance(v, (int, float, bool)):
                    if "api" in k.lower() or "endpoint" in k.lower() or "url" in k.lower() or "version" in k.lower() or "build" in k.lower():
                        print(f"  {k}: {v}")
        except json.JSONDecodeError as e:
            print(f"  JSON解析失败: {e}")
            # 尝试修复常见问题（未引用的键）
            cs_fixed = re.sub(r'([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', cs_raw)
            try:
                cs = json.loads(cs_fixed)
                print(f"  修复后字段数: {len(cs)}")
                print(f"  修复后字段名: {sorted(cs.keys())[:30]}")
            except Exception as e2:
                print(f"  修复后仍失败: {e2}")
                # 最后手段：正则搜索所有 URL 字符串
                urls_in_cs = re.findall(r'["\'](https?://[^"\']+)["\']', cs_raw)
                print(f"  CommonSettings中URL数: {len(urls_in_cs)}")
                non_ms = []
                for u in urls_in_cs:
                    try:
                        h = urlparse(u).netloc.lower()
                        if not is_ms(h):
                            non_ms.append(safe_url(u))
                    except Exception:
                        pass
                print(f"  CommonSettings中非MS URL: {sorted(set(non_ms))}")
                # 输出所有URL安全化形式
                all_safe = sorted(set(safe_url(u) or u[:40] for u in urls_in_cs))
                print(f"  CommonSettings中所有URL(安全化):")
                for s in all_safe[:30]:
                    print(f"    {s}")

    # 提取 PreloadUrls
    print("\n=== PreloadUrls 分析 ===")
    m2 = re.search(r'window\.PreloadUrls\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    if m2:
        pu_raw = m2.group(1)
        try:
            pu_list = json.loads(pu_raw)
            print(f"PreloadUrls 数量: {len(pu_list)}")
            # 安全化
            for u in pu_list[:10]:
                try:
                    h = urlparse(u).netloc.lower()
                    print(f"  {safe_url(u)} 是否MS={is_ms(h)}")
                except Exception:
                    pass
        except Exception as e:
            print(f"  解析失败: {e}")
            urls = re.findall(r'"(https?://[^"]+)"', pu_raw)
            print(f"  PreloadUrls中URL数: {len(urls)}")
            for u in urls[:10]:
                try:
                    h = urlparse(u).netloc.lower()
                    print(f"  {safe_url(u)} 是否MS={is_ms(h)}")
                except Exception:
                    pass

    # 搜索整个HTML中的所有URL（最终检查）
    print("\n=== 全HTML URL扫描（最终）===")
    all_urls = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', html)
    print(f"URL总数: {len(all_urls)}")
    non_ms_safe = []
    for u in all_urls:
        try:
            h = urlparse(u).netloc.lower()
            if not is_ms(h):
                non_ms_safe.append(safe_url(u))
        except Exception:
            pass
    print(f"非MS URL数: {len(non_ms_safe)}")
    print(f"非MS URL(安全化去重): {sorted(set(non_ms_safe))}")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
