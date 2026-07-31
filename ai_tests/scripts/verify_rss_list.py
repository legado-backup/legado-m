#!/usr/bin/env python3
"""快速验证订阅源：导航到订阅Tab → 点击源 → 验证列表加载"""
import uiautomator2 as u2
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
d = u2.connect('127.0.0.1:21503')

print("=== Step 1: Find and click RSS tab ===")

# 尝试多种方式找到订阅Tab
found = False

# 方式1: 通过文字
for tab_name in ['订阅', 'RSS']:
    el = d(text=tab_name)
    if el.exists:
        print(f"Found tab by text: {tab_name}")
        el.click()
        found = True
        break

# 方式2: 通过resourceId
if not found:
    for rid in ['menu_rss', 'nav_rss']:
        el = d(resourceId=f'{PKG}:id/{rid}')
        if el.exists:
            print(f"Found tab by id: {rid}")
            el.click()
            found = True
            break

# 方式3: 通过description
if not found:
    el = d(description='订阅')
    if el.exists:
        print("Found tab by description")
        el.click()
        found = True

if not found:
    # dump hierarchy 看看有什么
    print("Tab not found, dumping UI hierarchy...")
    xml = d.dump_hierarchy()
    # 找包含"订阅"或"rss"的node
    import re
    matches = re.findall(r'(<node[^>]*(?:订阅|rss|RSS)[^>]*>)', xml, re.IGNORECASE)
    for m in matches[:10]:
        print(f"  Match: {m[:200]}")

    # 也看看所有可点击的文本
    all_text = re.findall(r'text="([^"]*)"', xml)
    unique_text = list(set(all_text))
    print(f"  All visible text ({len(unique_text)}): {unique_text[:30]}")
    sys.exit(1)

time.sleep(3)

# 截图
screenshot_path = 'f:/myself/github/WeAgentChat/temp/legado/ai_tests/reports/rss_tab.png'
d.screenshot(screenshot_path)
print(f"Screenshot saved: {screenshot_path}")

cur = d.app_current()
print(f"Current activity: {cur.get('activity', '?')}")

# Step 2: 查看订阅源列表
print("\n=== Step 2: Check RSS source list ===")

# 查找RecyclerView或ListView
rv = d(resourceId=f'{PKG}:id/recycler_view')
if not rv.exists:
    rv = d(resourceId=f'{PKG}:id/rv_rss_source')
if not rv.exists:
    rv = d(className='androidx.recyclerview.widget.RecyclerView')

if rv.exists:
    # 尝试获取子项数量
    try:
        count = rv.child().count
        print(f"RecyclerView has {count} children")
    except Exception:
        print("RecyclerView found but cannot count children")
else:
    print("RecyclerView not found")

# 列出所有可见的源名称（脱敏：只输出前3个字符+编号）
print("\n=== Visible source items ===")
for i, item in enumerate(d(resourceId=f'{PKG}:id/tv_name')):
    if i >= 10:
        print(f"  ... and more (total checked: {i})")
        break
    name = item.get_text()
    if name:
        # 脱敏：只显示前2个字符+编号
        print(f"  Source[{i}]: {name[:2]}*** (len={len(name)})")

print("\n=== Done ===")
