#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点E子站订阅源JSON批量生成（脱敏输出）
为7个子站生成视频订阅源JSON，输出到output/ai_source/rss/
"""
import sys
import json
import re
import os
from urllib.parse import urlparse


def extract_u_value(html_path):
    """从HTML中提取搜索表单的u值"""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        # 搜索 name="u" value="xxx"
        match = re.search(r'name="u"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        # 搜索 value="xxx" name="u"
        match = re.search(r'value="([^"]+)"[^>]*name="u"', html)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def extract_title(html_path):
    """从HTML中提取页面标题"""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        match = re.search(r'<title>([^<]+)</title>', html)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def extract_favicon(html_path, base_url):
    """从HTML中提取favicon"""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        match = re.search(r'<link[^>]*rel="[^"]*icon[^"]*"[^>]*href="([^"]+)"', html, re.I)
        if match:
            href = match.group(1)
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                return base_url.rstrip("/") + href
            else:
                return base_url.rstrip("/") + "/" + href
    except Exception:
        pass
    return base_url.rstrip("/") + "/favicon.ico"


def main():
    print("=== 站点E子站订阅源JSON批量生成 ===")
    
    # 读取子站URL
    with open("output/siteE_subsites.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 读取分析结果
    with open("output/siteE_analysis.json", "r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # 筛选.cfd子站
    subsites = []
    for item in analysis:
        url = item["url"]
        parsed = urlparse(url)
        if parsed.netloc.endswith(".cfd") or parsed.netloc.endswith(".xyz") or parsed.netloc.endswith(".buzz"):
            subsites.append({"url": url, "analysis": item["analysis"]})
    
    print(f"共 {len(subsites)} 个子站")
    print()
    
    sources = []
    
    for i, sub in enumerate(subsites):
        idx = i + 1
        url = sub["url"]
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 从HTML提取u值和标题
        html_path = f"output/siteE_sub{idx}.html"
        u_value = extract_u_value(html_path)
        title = extract_title(html_path) or sub["analysis"].get("title", f"子站{idx}")
        favicon = extract_favicon(html_path, base_url)
        
        # 清理标题（去掉" - xxx"后缀）
        source_name = title.split(" - ")[0].split(" | ")[0].strip()
        
        if not u_value:
            print(f"  子站[{idx}] [WARN] 未找到u值，跳过")
            continue
        
        print(f"  子站[{idx}] 标题={source_name[:15]} | u值长度={len(u_value)} | 域名后缀=.{parsed.netloc.split('.')[-1]}")
        
        # 构造订阅源JSON
        source = {
            "sourceName": source_name,
            "sourceUrl": base_url + "/",
            "sourceIcon": favicon,
            "sourceGroup": "视频订阅",
            "sourceComment": f"[网站恢复]入口:站点E(avav2.lol)跳转Sway导航页获取子站地址 | 当前域名:{parsed.netloc} | 防迷路地址:avav1.lol/avav2.lol [技术]自定义CMS;搜索?m=search&u={u_value}&k=关键词;列表div.thumbnail.group;链接/?m=play&u={u_value}&k=视频ID;播放页iframe播放器API+hls.js加载m3u8;m3u8地址含.m3u8后缀;ruleContent用嗅探自动拦截m3u8",
            "enabled": True,
            "type": 1,
            "sortUrl": "",
            "searchUrl": f"/?m=search&u={u_value}&k={{key}}",
            "ruleArticles": "div.thumbnail.group",
            "ruleTitle": "img.thumb-img@alt",
            "ruleLink": "a@href",
            "ruleImage": "img.thumb-img@src",
            "ruleContent": "",
            "ruleNextPage": "",
            "ruleRoutes": "",
            "ruleEpisodes": "",
        }
        
        # sortUrl: 首页即最新列表
        source["sortUrl"] = f"最新::{base_url}/"
        
        sources.append(source)
    
    # 输出JSON
    output_path = "output/ai_source/rss/rssSource_video_siteE_subs_20260729.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 生成完成 ===")
    print(f"共生成 {len(sources)} 个订阅源")
    print(f"输出文件: {output_path}")
    
    # 输出脱敏摘要
    print(f"\n=== 订阅源摘要（脱敏）===")
    for i, s in enumerate(sources):
        parsed = urlparse(s["sourceUrl"])
        print(f"  源[{i+1}]: 名称={s['sourceName'][:12]} | 域名后缀=.{parsed.netloc.split('.')[-1]} | searchUrl有={bool(s['searchUrl'])} | ruleArticles={s['ruleArticles']}")


if __name__ == "__main__":
    main()
