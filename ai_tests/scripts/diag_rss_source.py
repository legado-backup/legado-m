#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断：进入一个订阅源后dump UI层次，分析tab项的resourceId
"""

import uiautomator2 as u2
import time
import os

PACKAGE = "io.legado.miss.app.debug"
ID_PREFIX = "io.legado.miss.app.debug:id/"
SCREENSHOT_DIR = "ai_tests/output/screenshots/rss_v5_diag"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

d = u2.connect()
print(f"[INFO] 设备: {d.info.get('productName', 'unknown')}")

current = d.app_current()
if current.get("package") != PACKAGE:
    d.app_start(PACKAGE)
    time.sleep(3)

# 进入订阅tab
sub_tab = d(description="订阅")
if sub_tab.exists(timeout=5):
    sub_tab.click()
    time.sleep(3)
    print("[INFO] 已进入订阅页面")
else:
    print("[ERROR] 未找到订阅tab")
    exit(1)

# 找到第一个源并点击
src_name = "天籁精选"
src_elem = d(text=src_name)
if not src_elem.exists(timeout=3):
    for _ in range(10):
        d.swipe(500, 1500, 500, 500, duration=300)
        time.sleep(1)
        if d(text=src_name).exists(timeout=2):
            break

if d(text=src_name).exists(timeout=2):
    d(text=src_name).click()
    print(f"[INFO] 已点击源[1]")
    time.sleep(5)

    # 等待分类容器
    for i in range(30):
        tc = d(resourceId=f"{ID_PREFIX}tabs_container")
        if tc.exists(timeout=1):
            print(f"[INFO] tabs_container 存在 (等待{i+1}秒)")
            break
        time.sleep(1)
    
    # 额外等待15秒让sortUrl JS执行
    print("[INFO] 额外等待15秒让sortUrl JS执行完成...")
    time.sleep(15)

    # 截图
    d.screenshot(os.path.join(SCREENSHOT_DIR, "source_1_after_wait.png"))
    print("[INFO] 截图已保存")

    # dump XML
    xml = d.dump_hierarchy()
    xml_path = os.path.join(SCREENSHOT_DIR, "source_1_hierarchy.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"[INFO] UI层次已保存 ({len(xml)} bytes)")

    # 搜索所有包含 "tab" 的 resourceId
    import re
    tab_ids = set(re.findall(r'resource-id="([^"]*tab[^"]*)"', xml))
    print(f"[INFO] 包含'tab'的resourceId: {tab_ids}")

    # 搜索所有包含 "item" 的 resourceId  
    item_ids = set(re.findall(r'resource-id="([^"]*item[^"]*)"', xml))
    print(f"[INFO] 包含'item'的resourceId: {item_ids}")

    # 搜索 tabs_container 内的子元素
    # 用另一种方式：查找所有TextView（tab通常是TextView）
    tv_count = d(className="android.widget.TextView").count
    print(f"[INFO] TextView总数: {tv_count}")

    # 查找 item_tab 数量
    item_tab_count = d(resourceId=f"{ID_PREFIX}item_tab").count
    print(f"[INFO] item_tab数量: {item_tab_count}")

    # 尝试其他可能的tab resourceId
    possible_tab_ids = [
        f"{ID_PREFIX}item_tab",
        f"{ID_PREFIX}tab_item",
        f"{ID_PREFIX}tab",
        f"{ID_PREFIX}mTabLayout",
        f"{ID_PREFIX}tabLayout",
    ]
    for tid in possible_tab_ids:
        cnt = d(resourceId=tid).count
        if cnt > 0:
            print(f"[INFO] {tid}: count={cnt}")

    # 检查是否有 RecyclerView 或 ViewPager（文章列表容器）
    rv_count = d(resourceId=f"{ID_PREFIX}recycle_view").count
    print(f"[INFO] recycle_view数量: {rv_count}")

    rv2 = d(resourceId=f"{ID_PREFIX}rv_book_source").count
    print(f"[INFO] rv_book_source数量: {rv2}")

    # 查找所有 RecyclerView
    rv_all = d(className="androidx.recyclerview.widget.RecyclerView").count
    print(f"[INFO] RecyclerView总数: {rv_all}")

    # 查找 tv_title
    tv_title_count = d(resourceId=f"{ID_PREFIX}tv_title").count
    print(f"[INFO] tv_title数量: {tv_title_count}")

    # 查找所有包含 "title" 的 resourceId
    title_ids = set(re.findall(r'resource-id="([^"]*title[^"]*)"', xml))
    print(f"[INFO] 包含'title'的resourceId: {title_ids}")

    # 返回
    d.press("back")
    time.sleep(2)
else:
    print("[ERROR] 未找到源[1]")
