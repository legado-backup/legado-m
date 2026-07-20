#!/usr/bin/env python3
r"""v5_6_verify_patch.py — 验证修复后的URL可达性 + 提取单源JSON供导入

安全规范：禁止输出源名称/URL/cookie，全部用代号。
"""
import json
import re
import sys
import urllib.request
import urllib.error
import ssl
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Linux; Android 12; SM-G9910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"

PATCH_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_6_patch.json')
OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_targets')
IMPORT_DIR = OUT_DIR / 'import'
IMPORT_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        return resp.getcode(), resp.read().decode('utf-8', errors='ignore'), resp.geturl()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', errors='ignore')
        except Exception:
            body = ''
        return e.code, body, url
    except Exception as e:
        return -1, '', url, str(e) if False else ''


with open(PATCH_JSON, 'r', encoding='utf-8') as f:
    sources = json.load(f)

# === 提取源[1]和源[3]作为单独JSON ===
print("[EXTRACT] 提取源[1]和源[3]作为单独JSON供导入")
src1 = sources[1]
src3 = sources[3]

# 保存为单独JSON（数组格式，供 import_rss_source.py 导入）
import_json_path = IMPORT_DIR / 'v5_6_src_1_3.json'
with open(import_json_path, 'w', encoding='utf-8') as f:
    json.dump([src1, src3], f, ensure_ascii=False, indent=2)
print(f"  saved: {import_json_path}")

# === 验证源[1]修复后URL可达性 ===
print("\n" + "=" * 80)
print("[VERIFY] 源[1] (list_empty) 修复后URL可达性")
print("=" * 80)
print(f"  sourceUrl_host={src1['sourceUrl'].split('//')[1].split('/')[0]}")

# 提取 sortUrl 中的第一个 https URL
sort_url = src1.get('sortUrl', '')
sort_urls = re.findall(r'https?://[^\s\'"\\]+\.html', sort_url)
if sort_urls:
    test_sort_url = sort_urls[0]
    test_sort_url_host = test_sort_url.split('//')[1].split('/')[0]
    print(f"  sortUrl_test_host={test_sort_url_host}")
    result = fetch(test_sort_url)
    if isinstance(result, tuple):
        if len(result) == 3:
            code, html, final_url = result
        else:
            code, html, final_url, err = result
        print(f"  sortUrl_fetch: code={code} html_len={len(html)} final_host={final_url.split('//')[1].split('/')[0] if '//' in final_url else 'N/A'}")
        if code == 200 and html:
            # 简单HTML结构检测
            li_count = len(re.findall(r'<li\b', html))
            container_match = re.search(r'<(?:div|ul|section)[^>]*class="[^"]*container[^"]*"', html)
            stui_vodlist = 'stui-vodlist' in html
            myui_vodlist = 'myui-vodlist' in html
            module_vodlist = 'module-vodlist' in html
            print(f"    li_count={li_count} has_container={bool(container_match)} stui={stui_vodlist} myui={myui_vodlist} module={module_vodlist}")
            # 保存HTML
            html_path = OUT_DIR / 'src_A_sort_after_patch.html'
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(f'<!-- url: {test_sort_url} -->\n')
                f.write(html)
            print(f"    saved: {html_path}")

# 测试 searchUrl
search_url = src1.get('searchUrl', '')
search_urls = re.findall(r"https?://[^\s'\"\\]+\.html", search_url)
if search_urls:
    test_search_url = search_urls[0]
    test_search_url_host = test_search_url.split('//')[1].split('/')[0]
    print(f"  searchUrl_test_host={test_search_url_host}")
    result = fetch(test_search_url)
    if isinstance(result, tuple):
        if len(result) == 3:
            code, html, final_url = result
        else:
            code, html, final_url, err = result
        print(f"  searchUrl_fetch: code={code} html_len={len(html)}")

# === 验证源[3]修复后URL可达性 ===
print("\n" + "=" * 80)
print("[VERIFY] 源[3] (search_malformed_url) 修复后URL可达性")
print("=" * 80)
print(f"  sourceUrl_protocol={src3['sourceUrl'].split(':')[0]}")
print(f"  sourceUrl_host={src3['sourceUrl'].split('//')[1].split('/')[0]}")

result = fetch(src3['sourceUrl'])
if isinstance(result, tuple):
    if len(result) == 3:
        code, html, final_url = result
    else:
        code, html, final_url, err = result
    print(f"  sourceUrl_fetch: code={code} html_len={len(html)}")
    if code == 200 and html:
        # 检测 CMS 模板
        has_stui = 'stui-vodlist' in html
        has_myui = 'myui-vodlist' in html
        has_video_item = 'video-item' in html
        has_mac_player = 'MacPlayer' in html or 'player_aaaa' in html
        li_count = len(re.findall(r'<li\b', html))
        a_count = len(re.findall(r'<a\b[^>]*href=', html))
        img_count = len(re.findall(r'<img\b', html))
        print(f"    stui={has_stui} myui={has_myui} video_item={has_video_item} mac_player={has_mac_player}")
        print(f"    li_count={li_count} a_count={a_count} img_count={img_count}")
        # 保存HTML
        html_path = OUT_DIR / 'src_C_source_after_patch.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(f'<!-- url: {src3["sourceUrl"]} -->\n')
            f.write(html)
        print(f"    saved: {html_path}")
        # 找出列表项容器
        patterns = [
            (r'class="[^"]*video-item', 'video_item'),
            (r'class="[^"]*vodlist', 'vodlist'),
            (r'class="[^"]*stui-vodlist', 'stui_vodlist'),
            (r'class="[^"]*module-vodlist', 'module_vodlist'),
            (r'class="[^"]*myui-vodlist', 'myui_vodlist'),
            (r'<ul[^>]*class="[^"]*list', 'ul_list'),
            (r'<div[^>]*class="[^"]*list', 'div_list'),
        ]
        for pat, name in patterns:
            m = re.search(pat, html)
            if m:
                print(f"    matched: {name} -> {m.group(0)[:80]}")

print("\n[DONE]")
