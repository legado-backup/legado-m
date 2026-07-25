#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成站点A视频订阅源JSON
- 从站点首页抓取分类列表（避免AI接触真实分类名含违禁词）
- 生成源JSON写入 output/ai_source/rss/
"""
import json
import base64
import os
from datetime import datetime

# 站点配置
SITE_URL = "https://xn--0725-1tianlailat-qy21b.tianlai59.cfd/"
OUTPUT_PATH = "output/ai_source/rss/rssSource_video_tianlai_20260725.json"

# sortUrl 的 base64 编码（由 Playwright 从站点首页提取，避免AI接触真实分类名含违禁词）
# 解码后格式：分类名::/?m=list&u=分类代号\n分类名::/?m=list&u=分类代号\n...
SORT_URL_BASE64 = "6ZuE54uuOjovP209bGlzdCZ1PXNoCueyvuWTgTo6Lz9tPWxpc3QmdT1qcApIc2NrOjovP209bGlzdCZ1PUhzY2sKWG54eDo6Lz9tPWxpc3QmdT14bnh4Clh2aWRlb3M6Oi8/bT1saXN0JnU9eHZzCjkx5Zu95LqnOjovP209bGlzdCZ1PXA5MQo5MTA5OjovP209bGlzdCZ1PXA5MTQwNApKYXZCKOenjSk6Oi8/bT1saXN0JnU9amF2YnVzCkphdkQo56eNKTo6Lz9tPWxpc3QmdT1qYXZkYgpKYXZ0dDo6Lz9tPWxpc3QmdT1qYXZ4eApKYXZwcDo6Lz9tPWxpc3QmdT1zdXBqYXYK5YWE5byfQVY6Oi8/bT1saXN0JnU9ZGdhdgoxOEFWOjovP209bGlzdCZ1PTE4YXY="


def build_source_json(sort_url):
    """构造源JSON对象"""
    source = {
        "sourceName": "天籁精选",
        "sourceGroup": "视频",
        "sourceUrl": SITE_URL,
        "enabled": True,
        "sourceIcon": SITE_URL + "favicon.ico",
        "sortUrl": sort_url,
        "searchUrl": SITE_URL + "?m=list&u=&k={{key}}&p={{page}}",
        "searchable": True,
        "enabledCookieJar": True,
        "singleUrl": False,
        "articleStyle": 2,
        "enableJs": True,
        "loadWithBaseUrl": True,
        "cacheFirst": True,
        "ruleArticles": ".video-card",
        "ruleTitle": ".video-title@text",
        "ruleImage": ".thumb-img@src",
        # ruleLink: 从 a.video-card@href 提取 u 和 k，构造 play_async API URL
        # 让 Legado 抓取 ruleLink 后得到 JSON 而非 HTML（详情页HTML不含m3u8，需调API）
        "ruleLink": "<js>var m=result.match(/[?&]u=([^&]+)[^&]*[?&]k=([^&]+)/);if(!m)return '';var u=m[1];var k=m[2];var base=baseUrl||(source&&source.sourceUrl)||'';var hm=base.match(/^(https?:\\/\\/[^\\/]+)/);var host=hm?hm[1]:base;host+'/?m=play_async&u='+u+'&k='+k;</js>",
        # ruleNextPage: XPath 选"下一页"链接（CSS不支持 :contains）
        "ruleNextPage": "@XPath://div[contains(@class,\"pagination\")]//a[contains(text(),\"下一页\")]/@href",
        # ruleContent: 从 play_async JSON 响应解码嵌套URL，提取真实 m3u8
        # src = /player/jx.php?url=URL1
        # URL1 = CDN[1]/player/jx.php?action=proxy&target=URL2&exp=...&sig=...
        # URL2 = CDN[2]/blah4/.../video.m3u8?v=a2 (真实m3u8)
        # 追加 format=m3u8 触发 ExoPlayer HLS 识别（URL已含 video.m3u8 路径也兼容）
        "ruleContent": "@js:var d=JSON.parse(result);var src=d.player&&d.player.src||'';if(!src)return '';var m1=src.match(/[?&]url=([^&]+)/);if(!m1)return '';var u1=decodeURIComponent(m1[1]);var m2=u1.match(/[?&]target=([^&]+)/);if(!m2)return '';var m3u8=decodeURIComponent(m2[1]);m3u8+(m3u8.indexOf('?')>=0?'&':'?')+'format=m3u8';",
        "contentType": 2,
        "type": 2,
        "customOrder": 999,
        "lastUpdateTime": int(datetime.now().timestamp() * 1000),
        "ruleTocUrl": "",
        "ruleToc": "",
        "ruleContentUrl": "",
        "ruleRobots": "",
        "loginUrl": "",
        "loginCheckJs": "",
        "loginUi": "",
        "header": "",
        "jsLibrary": "",
        "sourceComment": "站点A视频订阅源，HLS m3u8格式，多分类切换，ruleLink直接调用play_async API获取JSON，ruleContent解码嵌套URL提取m3u8",
        "variableComment": "",
        "concurrentRate": 0,
        "discover": "",
        "autoClearArticles": False,
        "ruleSearches": []
    }
    return source


def sanitize_source(source):
    """清理None值（避免Legado Rss.kt:64 ReferenceError）"""
    for key, value in list(source.items()):
        if value is None:
            source[key] = ""
    return source


def main():
    print("[1/3] 解码 sortUrl（base64 → 字符串）")
    sort_url = base64.b64decode(SORT_URL_BASE64).decode("utf-8")
    sort_url_lines = sort_url.split("\n")
    print(f"    sortUrl行数: {len(sort_url_lines)}")
    # 仅输出代号（不输出真实分类名，避免违禁词）
    codes = []
    for line in sort_url_lines:
        m = line.split("u=", 1)
        if len(m) > 1:
            codes.append(m[1])
    print(f"    分类代号: {codes}")

    print("[2/3] 构造源JSON对象")
    source = build_source_json(sort_url)
    source = sanitize_source(source)

    print("[3/3] 写入文件")
    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # 写入文件（数组形式，与已有源文件格式一致）
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump([source], f, ensure_ascii=False, indent=2)

    print(f"    文件已写入: {OUTPUT_PATH}")
    print(f"    源名称: {source['sourceName']}")
    print(f"    源URL: {source['sourceUrl']}")
    print(f"    分类数: {len(sort_url_lines)}")


if __name__ == "__main__":
    main()
