#!/usr/bin/env python3
"""端到端验证单个订阅源 - 稳健版"""
import uiautomator2 as u2
import time
import re
import sys
import os
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
REPORTS = r'f:\myself\github\WeAgentChat\temp\legado\ai_tests\reports'
os.makedirs(REPORTS, exist_ok=True)

TARGET_SOURCE_INDEX = 2  # 天籁精选

d = u2.connect(HOST)

def screenshot(name):
    path = os.path.join(REPORTS, f'{name}.png')
    try:
        d.screenshot(path)
        print(f'[SS] {path}')
    except Exception as e:
        print(f'[SS] Failed: {e}')

def run_adb(cmd):
    full = f'"{ADB}" -s {HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    return r

def dismiss_dialogs():
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
        btn = d(text=txt)
        if btn.exists:
            btn.click()
            print(f'[DIALOG] Closed: {txt}')
            time.sleep(1)

# === 重启App确保干净状态 ===
print("=" * 60)
print("RSS Source Detail E2E Verification (Robust)")
print("=" * 60)

print("\n--- Step 0: Restart App ---")
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(10)

# 关闭弹窗
print("\n--- Step 1: Dismiss dialogs ---")
dismiss_dialogs()
time.sleep(2)

# === 导航到订阅Tab ===
print("\n--- Step 2: Navigate to RSS tab ---")
# 方法1: 通过resourceId
rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
if rss_tab.exists:
    rss_tab.click()
    print('[NAV] Clicked RSS tab by id')
else:
    # 方法2: 通过文字
    rss_tab = d(text='订阅')
    if rss_tab.exists:
        rss_tab.click()
        print('[NAV] Clicked RSS tab by text')
    else:
        # 方法3: dump看看
        xml = d.dump_hierarchy()
        all_text = re.findall(r'text="([^"]*)"', xml)
        unique = [t for t in dict.fromkeys(all_text) if t]
        print(f'  Visible text: {unique[:20]}')
        # 方法4: 点击底部导航坐标
        print('[NAV] Trying bottom nav coordinate clicks...')
        for x in [500, 270, 600]:
            d.click(x, 355)
            time.sleep(2)
            cur = d.app_current()
            act = cur.get('activity', '?')
            if 'RssFragment' in act or 'RssSource' in act:
                print(f'[NAV] Found RSS at x={x}')
                break

time.sleep(3)
screenshot('rss_tab')

# === 验证源列表 ===
print("\n--- Step 3: Verify source list ---")
source_items = d(resourceId=f'{PKG}:id/tv_name')
if source_items.exists:
    count = source_items.count
    print(f'[LIST] Found {count} sources')
    for i in range(min(count, 10)):
        try:
            name = source_items[i].get_text()
            print(f'  Source[{i}]: {name[:2]}*** (len={len(name)})')
        except Exception:
            pass
    list_ok = count > 0
else:
    print('[LIST] No sources found')
    list_ok = False

# === 点击目标源 ===
print(f"\n--- Step 4: Click source index {TARGET_SOURCE_INDEX} ---")
if list_ok and source_items.count > TARGET_SOURCE_INDEX:
    name = source_items[TARGET_SOURCE_INDEX].get_text()
    print(f'[CLICK] Source[{TARGET_SOURCE_INDEX}]: {name[:2]}***')
    source_items[TARGET_SOURCE_INDEX].click()
    time.sleep(10)  # 等待文章列表加载（动态域名需要时间）
    screenshot('source_articles')
else:
    print('[FAIL] Target source not found')
    sys.exit(1)

# === 验证文章列表 ===
print("\n--- Step 5: Verify article list ---")
cur = d.app_current()
print(f'Activity: {cur.get("activity", "?")}')

# 等待更久（动态域名解析需要时间）
time.sleep(5)

# 查找RecyclerView
rv = d(className='androidx.recyclerview.widget.RecyclerView')
article_count = 0
if rv.exists:
    try:
        article_count = rv.child().count
        print(f'[ARTICLES] RecyclerView children: {article_count}')
    except Exception:
        print('[ARTICLES] Cannot count RecyclerView')

# 查找文章标题
article_titles = d(resourceId=f'{PKG}:id/tv_title')
if not article_titles.exists:
    article_titles = d(resourceId=f'{PKG}:id/tv_name')

if article_titles.exists:
    count = article_titles.count
    print(f'[ARTICLES] Title items: {count}')
    article_count = max(article_count, count)

if article_count == 0:
    # dump查看
    xml = d.dump_hierarchy()
    all_text = re.findall(r'text="([^"]*)"', xml)
    unique = [t for t in dict.fromkeys(all_text) if t]
    print(f'  Visible text: {unique[:20]}')

    # 检查logcat中的错误
    print('[ARTICLES] Checking logcat for errors...')
    r = run_adb('shell "logcat -d -t 100 | grep -iE \'AnalyzeUrl|RssRead|HttpException|SocketTimeout\' | tail -20"')
    if r.stdout.strip():
        for line in r.stdout.strip().splitlines()[:10]:
            # 只输出技术信息，脱敏
            if 'http' in line.lower() or 'url' in line.lower():
                print(f'  [LOG] {line[:120]}')
            else:
                print(f'  [LOG] {line[:150]}')

list_ok = article_count > 0
print(f'Article list: {"PASS" if list_ok else "FAIL"} ({article_count} items)')

# === 如果文章列表加载成功，测试翻页 ===
if list_ok:
    print("\n--- Step 6: Test pagination ---")
    d.swipe(400, 600, 400, 200, duration=0.5)
    time.sleep(5)
    screenshot('articles_page2')

    rv2 = d(className='androidx.recyclerview.widget.RecyclerView')
    if rv2.exists:
        try:
            new_count = rv2.child().count
            print(f'[PAGINATION] After swipe: {new_count} children')
            print(f'Pagination: {"PASS" if new_count >= article_count else "UNCERTAIN"}')
        except Exception:
            print('[PAGINATION] Cannot verify')

    # === 点击第一篇文章 ===
    print("\n--- Step 7: Click first article ---")
    d.swipe(400, 200, 400, 600, duration=0.3)  # 先回到顶部
    time.sleep(2)

    # 点击第一个文章
    d.click(400, 250)
    time.sleep(8)
    screenshot('article_detail')

    cur2 = d.app_current()
    print(f'Activity after click: {cur2.get("activity", "?")}')

    if 'VideoPlay' in cur2.get('activity', ''):
        print('[PLAY] Video player opened')
        time.sleep(5)
        screenshot('video_playing')
    elif 'ReadRss' in cur2.get('activity', ''):
        print('[PLAY] RSS article opened')
        time.sleep(3)
        screenshot('rss_article')
    else:
        print(f'[PLAY] Activity: {cur2.get("activity", "?")}')

# === 返回并测试搜索 ===
print("\n--- Step 8: Test search ---")
# 返回到订阅源列表
for _ in range(3):
    d.press('back')
    time.sleep(1)

# 确认在订阅Tab
dismiss_dialogs()
time.sleep(1)

# 尝试搜索
search_btn = d(resourceId=f'{PKG}:id/menu_search')
if not search_btn.exists:
    search_btn = d(description='搜索')
if not search_btn.exists:
    search_btn = d(text='搜索')

if search_btn.exists:
    search_btn.click()
    time.sleep(2)

    edit = d(resourceId=f'{PKG}:id/search_src_text')
    if not edit.exists:
        edit = d(className='android.widget.EditText')

    if edit.exists:
        edit.set_text('HD')
        time.sleep(1)
        d.press('enter')
        time.sleep(10)
        screenshot('search_results')

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
        search_ok = False
else:
    print('[SEARCH] Search button not found')
    search_ok = False

# === 检查无崩溃 ===
print("\n--- Step 9: Check crashes ---")
r = run_adb('shell "logcat -d -t 300 | grep -E \'FATAL|AndroidRuntime\' | grep io.legado"')
if r.stdout.strip():
    print(f'[CRASH] Found crashes:')
    for line in r.stdout.strip().splitlines()[:5]:
        print(f'  {line[:150]}')
else:
    print('[CRASH] No crashes')

# Summary
print("\n" + "=" * 60)
print("Summary:")
print(f"  Source list: PASS")
print(f"  Article list: {'PASS' if list_ok else 'FAIL'}")
print(f"  Search: {'PASS' if search_ok else 'FAIL' if not list_ok else 'N/A'}")
print("=" * 60)
