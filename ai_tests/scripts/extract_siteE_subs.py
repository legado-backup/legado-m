#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从保存的HTML中提取站点E的子站URL（脱敏编号输出）
"""
import re
from urllib.parse import urlparse

MS_DOMAINS = {
    "microsoft.com", "microsoftonline.com", "live.com", "office.com",
    "office365.com", "sway.cloud.microsoft", "sway.office.com",
    "azureedge.net", "msftauth.net", "sharepoint.com", "docs.com",
    "skype.com", "bing.com", "msn.com", "windows.net", "xbox.com",
    "github.com", "linkedin.com", "twitter.com", "facebook.com",
    "youtube.com", "youtu.be", "vimeo.com", "soundcloud.com",
    "sketchfab.com", "pickit.com", "google.com", "googleapis.com",
    "gstatic.com", "cloudflare.com", "jsdelivr.net", "unpkg.com",
    "w3.org", "schema.org", "msft.net", "azure.com",
    "s-microsoft.com", "assets-perf.e ..."
}


def is_ms_domain(domain):
    domain = domain.lower()
    for ms in MS_DOMAINS:
        if domain == ms or domain.endswith("." + ms):
            return True
    return False


def main():
    with open("output/siteE_page.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 提取所有URL
    url_pattern = r'https?://[^\s<>"\'\\]+'
    all_urls = re.findall(url_pattern, html)

    # 去重并过滤微软域名
    seen = set()
    sub_sites = []
    for url in all_urls:
        url = url.rstrip(".,;:)】")
        if url in seen:
            continue
        seen.add(url)
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if is_ms_domain(domain):
                continue
            if not domain:
                continue
            sub_sites.append(url)
        except Exception:
            continue

    print(f"=== 子站URL清单（脱敏编号）===")
    print(f"过滤微软域名后，共找到 {len(sub_sites)} 个子站URL")
    print()
    for i, url in enumerate(sub_sites):
        parsed = urlparse(url)
        domain = parsed.netloc
        # 只输出域名后缀+路径模式，不输出完整域名
        domain_parts = domain.split(".")
        suffix = "." + domain_parts[-1] if len(domain_parts) > 1 else domain
        path = parsed.path[:40] if parsed.path else "/"
        print(f"  子站[{i+1}]: 域名后缀={suffix} | 路径={path} | 协议={parsed.scheme}")

    # 同时从页面文本中提取"资源X"分组信息
    print()
    print("=== 页面文本中的资源分组 ===")
    text_pattern = r'(资源[一二三四五六七八九十]+[：:][\s\S]*?)(?=资源[一二三四五六七八九十]+[：:]|$)'
    # 从HTML中提取body文本
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if body_match:
        # 去掉HTML标签
        body_text = re.sub(r'<[^>]+>', ' ', body_match.group(1))
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        # 替换URL为编号
        for i, url in enumerate(sub_sites):
            body_text = body_text.replace(url, f'[子站{i+1}]')
        # 查找资源分组
        groups = re.findall(text_pattern, body_text)
        for g in groups:
            g = g.strip()
            if len(g) > 200:
                g = g[:200] + "..."
            print(f"  {g}")
            print()

    # 保存子站URL到文件（供后续脚本使用）
    print("=== 保存子站URL到文件 ===")
    with open("output/siteE_subsites.json", "w", encoding="utf-8") as f:
        import json
        json.dump({"subsites": sub_sites}, f, ensure_ascii=False, indent=2)
    print(f"  已保存: output/siteE_subsites.json ({len(sub_sites)}个URL)")


if __name__ == "__main__":
    main()
