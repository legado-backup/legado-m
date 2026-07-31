#!/usr/bin/env python3
"""端到端验证单个订阅源：点击源 → 加载文章列表 → 翻页 → 搜索 → 播放"""
import uiautomator2 as u2
import time
import re
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
REPORTS = r'f:\myself\github\WeAgentChat\temp\legado\ai_tests\reports'
os.makedirs(REPORTS, exist_ok=True)

# 要验证的源编号（0-based, 在订阅Tab中的位置）
# 从上一步知道：Source[2]是天籁精选
TARGET_SOURCE_INDEX = 2

d = u2.connect(HOST)

def screenshot(name):
    path = os.path.join(REPORTS, f'{name}.png')
    d.screenshot(path)
    print(f'[SS] {path}')

def dismiss_dialogs():
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
        btn = d(text=txt)
        if btn.exists:
            btn.click()
            print(f'[DIALOG] Closed: {txt}')
            time.sleep(1)

# === Step 1: 确保在订阅Tab ===
print("=" * 60)
print("RSS Source Detail E2E Verification")
print("=" * 60)

print("\n--- Step 1: Ensure on RSS tab ---")
dismiss_dialogs()
time.sleep(1)

# 点击订阅Tab
rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
if rss_tab.exists:
    rss_tab.click()
    print('[NAV] Clicked RSS tab')
    time.sleep(3)
else:
    print('[NAV] RSS tab not found, trying text')
    d(text='订阅').click()
    time.sleep(3)

# === Step 2: 点击目标源 ===
print(f"\n--- Step 2: Click source index {TARGET_SOURCE_INDEX} ---")
source_items = d(resourceId=f'{PKG}:id/tv_name')
if source_items.exists and source_items.count > TARGET_SOURCE_INDEX:
    name = source_items[TARGET_SOURCE_INDEX].get_text()
    print(f'[CLICK] Clicking source[{TARGET_SOURCE_INDEX}]: {name[:2]}***')
    source_items[TARGET_SOURCE_INDEX].click()
    time.sleep(8)  # 等待文章列表加载
    screenshot('source_articles')
else:
    print(f'[FAIL] Source index {TARGET_SOURCE_INDEX} not found')
    sys.exit(1)

# === Step 3: 验证文章列表 ===
print("\n--- Step 3: Verify article list ---")
# 检查当前Activity
cur = d.app_current()
print(f'Current Activity: {cur.get("activity", "?")}')

# 查找RecyclerView
rv = d(className='androidx.recyclerview.widget.RecyclerView')
article_count = 0
if rv.exists:
    try:
        article_count = rv.child().count
        print(f'[ARTICLES] RecyclerView children: {article_count}')
    except Exception as e:
        print(f'[ARTICLES] Cannot count: {e}')

# 备选：查找文章标题
article_titles = d(resourceId=f'{PKG}:id/tv_title')
if not article_titles.exists:
    article_titles = d(resourceId=f'{PKG}:id/tv_name')

if article_titles.exists:
    count = article_titles.count
    print(f'[ARTICLES] Title items: {count}')
    for i in range(min(count, 5)):
        try:
            title = article_titles[i].get_text()
            print(f'  Article[{i}]: {title[:3]}***')
        except Exception:
            pass
    article_count = max(article_count, count)
else:
    # dump看看有什么
    xml = d.dump_hierarchy()
    all_text = re.findall(r'text="([^"]*)"', xml)
    unique = [t for t in dict.fromkeys(all_text) if t]
    print(f'  Visible text: {unique[:25]}')

list_ok = article_count > 0
print(f'Article list: {"PASS" if list_ok else "FAIL"} ({article_count} items)')

# === Step 4: 验证翻页 ===
print("\n--- Step 4: Test pagination ---")
if list_ok:
    # 滑动到底部触发加载更多
    d.swipe(400, 600, 400, 200, duration=0.5)
    time.sleep(3)
    screenshot('source_articles_page2')

    # 检查是否有更多内容
    rv2 = d(className='androidx.recyclerview.widget.RecyclerView')
    if rv2.exists:
        try:
            new_count = rv2.child().count
            print(f'[PAGINATION] After swipe: {new_count} children')
            pagination_ok = new_count >= article_count
            print(f'Pagination: {"PASS" if pagination_ok else "UNCERTAIN"}')
        except Exception:
            print('[PAGINATION] Cannot verify')

    # 再滑一次
    d.swipe(400, 600, 400, 200, duration=0.5)
    time.sleep(3)
    screenshot('source_articles_page3')

# === Step 5: 点击第一篇文章进入播放 ===
print("\n--- Step 5: Click first article ---")
if list_ok:
    # 点击第一个文章
    # 在RecyclerView中点击第一项
    rv = d(className='androidx.recyclerview.widget.RecyclerView')
    if rv.exists:
        try:
            # 获取RecyclerView位置信息
            info = rv.info
            bounds = info.get('bounds', {})
            top = bounds.get('top', 100)
            left = bounds.get('left', 0)
            right = bounds.get('right', 720)
            cx = (left + right) // 2
            cy = top + 100  # 第一项大致位置
            print(f'[PLAY] Clicking article at ({cx}, {cy})')
            d.click(cx, cy)
            time.sleep(8)  # 等待加载
            screenshot('article_detail')

            # 检查当前Activity
            cur2 = d.app_current()
            print(f'Activity after click: {cur2.get("activity", "?")}')

            # 如果进入了视频播放页面
            if 'VideoPlay' in cur2.get('activity', ''):
                print('[PLAY] Entered video player')
                time.sleep(5)
                screenshot('video_playing')

                # 检查是否有播放控件
                player = d(resourceId=f'{PKG}:id/player')
                if not player.exists:
                    player = d(className='android.view.SurfaceView')
                if not player.exists:
                    player = d(resourceId=f'{PKG}:id/exo_player')

                if player.exists:
                    print('[PLAY] Video player found - PASS')
                else:
                    print('[PLAY] Video player not found - checking...')
                    xml = d.dump_hierarchy()
                    all_text = re.findall(r'text="([^"]*)"', xml)
                    unique = [t for t in dict.fromkeys(all_text) if t]
                    print(f'  Visible text: {unique[:15]}')
            elif 'ReadRss' in cur2.get('activity', ''):
                print('[PLAY] Entered RSS article page (type=2 video source may need different navigation)')
                time.sleep(5)
                screenshot('rss_article_detail')

                # 检查是否有视频内容
                xml = d.dump_hierarchy()
                all_text = re.findall(r'text="([^"]*)"', xml)
                unique = [t for t in dict.fromkeys(all_text) if t]
                print(f'  Visible text: {unique[:15]}')
            else:
                print(f'[PLAY] Unexpected activity: {cur2.get("activity", "?")}')
        except Exception as e:
            print(f'[PLAY] Error: {e}')

# === Step 6: 返回并验证搜索 ===
print("\n--- Step 6: Test search ---")
# 返回到订阅源列表
d.press('back')
time.sleep(2)
d.press('back')
time.sleep(2)

# 确认回到了订阅源列表
rss_tab2 = d(resourceId=f'{PKG}:id/menu_rss')
if rss_tab2.exists:
    print('[SEARCH] Back on RSS tab')

# 查找搜索入口
search_icon = d(resourceId=f'{PKG}:id/menu_search')
if not search_icon.exists:
    search_icon = d(description='搜索')
if not search_icon.exists:
    search_icon = d(text='搜索')

if search_icon.exists:
    search_icon.click()
    time.sleep(2)

    # 输入关键词
    edit = d(resourceId=f'{PKG}:id/search_src_text')
    if not edit.exists:
        edit = d(className='android.widget.EditText')
    if edit.exists:
        edit.set_text('HD')
        time.sleep(1)
        d.press('enter')
        time.sleep(10)

        screenshot('search_results')

        # 检查搜索结果
        rv = d(className='androidx.recyclerview.widget.RecyclerView')
        if rv.exists:
            try:
                count = rv.child().count
                print(f'[SEARCH] Results: {count} items')
                search_ok = count > 0
            except Exception:
                search_ok = False
        else:
            search_ok = False

        print(f'Search: {"PASS" if search_ok else "FAIL"}')
    else:
        print('[SEARCH] EditText not found')
else:
    print('[SEARCH] Search button not found')

# === Step 7: 检查无崩溃 ===
print("\n--- Step 7: Check crashes ---")
import subprocess
r = subprocess.run(
    f'"{ADB}" -s {HOST} shell "logcat -d -t 300 | grep -E "FATAL|AndroidRuntime" | grep io.legado"',
    shell=True, capture_output=True, text=True, timeout=15
)
if r.stdout.strip():
    print(f'[CRASH] Found crashes:')
    for line in r.stdout.strip().splitlines()[:5]:
        print(f'  {line[:150]}')
else:
    print('[CRASH] No crashes detected')

print("\n" + "=" * 60)
print("Verification Complete")
print("=" * 60)
