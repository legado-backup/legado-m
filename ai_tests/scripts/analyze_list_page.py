#!/usr/bin/env python3
"""分析站点D列表页HTML结构（输出安全：只输出技术结构，不显示域名/URL/标题内容）"""
import re
import sys
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8')

ENTRY_URL = "https://qd.18j12m.xyz/rise/"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 步骤1: 获取入口域名HTML，解析实际域名
print("=== 步骤1: 获取入口域名HTML ===")
try:
    req = urllib.request.Request(ENTRY_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        entry_html = resp.read().decode('utf-8', errors='ignore')
    print(f"入口HTML长度: {len(entry_html)}")
except Exception as e:
    print(f"获取入口HTML失败: {e}")
    sys.exit(1)

# 步骤2: 解析域名基础+生成今日域名
domain_match = re.search(r'getRandomWord\(\)\s*\+\s*"\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', entry_html)
if not domain_match:
    print("未匹配到getRandomWord域名模式")
    sys.exit(1)
domain_base = domain_match.group(1)
print(f"域名基础: {domain_base}")

import math
import datetime

def seeded_random(seed):
    x = math.sin(seed) * 10000
    return x - math.floor(x)

d = datetime.datetime.now()
seed = d.year * 10000 + d.month * 100 + d.day
letters = 'abcdefgijlmnoqrstwz'

def generate_word(s, length):
    word = ''
    for i in range(length):
        idx = int(seeded_random(s + i) * len(letters))
        word += letters[idx]
    return word

words = []
i = 0
while len(words) < 2:
    length = 3 + int(seeded_random(seed + i) * 3)
    w = generate_word(seed + i * 10, length)
    if w not in words:
        words.append(w)
    i += 1

# 步骤3: 测试候选域名可用性
real_domain = None
for w in words:
    candidate = w + '.' + domain_base
    test_url = f'https://{candidate}/vodtype/1/'
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            test_html = resp.read().decode('utf-8', errors='ignore')
        if len(test_html) > 1000:
            real_domain = candidate
            break
    except Exception as e:
        pass

if not real_domain:
    real_domain = words[0] + '.' + domain_base

print(f"实际域名: 域名#1 (长度={len(real_domain)})")

# 步骤4: 获取列表页HTML
print(f"\n=== 步骤4: 获取列表页HTML ===")
list_url = f'https://{real_domain}/vodtype/1/'
try:
    req = urllib.request.Request(list_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        list_html = resp.read().decode('utf-8', errors='ignore')
    print(f"列表页HTML长度: {len(list_html)}")
except Exception as e:
    print(f"获取列表页失败: {e}")
    sys.exit(1)

# 步骤5: 分析ruleArticles选择器 li.col-25
print(f"\n=== 步骤5: 分析ruleArticles选择器 li.col-25 ===")
li_matches = re.findall(r'<li[^>]*class="[^"]*col-25[^"]*"[^>]*>[\s\S]{0,2000}?</li>', list_html)
print(f"li.col-25匹配数量: {len(li_matches)}")
if li_matches:
    print(f"\n第一个li.col-25内容（前1500字符）:")
    print(li_matches[0][:1500])
else:
    # 尝试其他可能的class
    print("\nli.col-25未匹配，尝试其他class...")
    # 搜索所有li标签
    all_li = re.findall(r'<li[^>]*class="([^"]*)"', list_html)
    print(f"所有li的class: {set(all_li)}")
    # 搜索col-相关的class
    col_classes = [c for c in set(all_li) if 'col' in c.lower()]
    print(f"含col的class: {col_classes}")

# 步骤6: 分析a.img-box选择器
print(f"\n=== 步骤6: 分析a.img-box选择器 ===")
a_matches = re.findall(r'<a[^>]*class="[^"]*img-box[^"]*"[^>]*>[\s\S]{0,500}?</a>', list_html)
print(f"a.img-box匹配数量: {len(a_matches)}")
if a_matches:
    print(f"\n第一个a.img-box内容:")
    print(a_matches[0][:500])
else:
    print("\na.img-box未匹配，尝试其他class...")
    all_a = re.findall(r'<a[^>]*class="([^"]*)"', list_html)
    img_classes = [c for c in set(all_a) if 'img' in c.lower() or 'box' in c.lower()]
    print(f"含img或box的class: {img_classes}")

# 步骤7: 分析img.lazy-image选择器
print(f"\n=== 步骤7: 分析img.lazy-image选择器 ===")
img_matches = re.findall(r'<img[^>]*class="[^"]*lazy-image[^"]*"[^>]*>', list_html)
print(f"img.lazy-image匹配数量: {len(img_matches)}")
if img_matches:
    print(f"\n第一个img.lazy-image内容:")
    print(img_matches[0][:300])
else:
    print("\nimg.lazy-image未匹配，尝试其他class...")
    all_img = re.findall(r'<img[^>]*class="([^"]*)"', list_html)
    lazy_classes = [c for c in set(all_img) if 'lazy' in c.lower()]
    print(f"含lazy的class: {lazy_classes}")

# 步骤8: 分析item整体结构
print(f"\n=== 步骤8: 分析item整体结构 ===")
if li_matches:
    item = li_matches[0]
    # 提取a标签
    a_tags = re.findall(r'<a[^>]*>[\s\S]*?</a>', item)
    print(f"item内a标签数量: {len(a_tags)}")
    for i, a in enumerate(a_tags[:3]):
        print(f"\na标签#{i+1}:")
        print(a[:300])
    # 提取img标签
    img_tags = re.findall(r'<img[^>]*>', item)
    print(f"\nitem内img标签数量: {len(img_tags)}")
    for i, img in enumerate(img_tags[:3]):
        print(f"img标签#{i+1}: {img[:200]}")
    # 提取title相关属性
    title_attrs = re.findall(r'title="([^"]*)"', item)
    print(f"\ntitle属性数量: {len(title_attrs)}")
    for i, t in enumerate(title_attrs[:3]):
        print(f"title#{i+1}长度: {len(t)}")
    # 提取href属性
    href_attrs = re.findall(r'href="([^"]*)"', item)
    print(f"\nhref属性数量: {len(href_attrs)}")
    for i, h in enumerate(href_attrs[:3]):
        print(f"href#{i+1}模式: {h[:80]}")
