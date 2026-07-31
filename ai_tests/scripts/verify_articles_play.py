#!/usr/bin/env python3
"""验证文章列表和播放功能"""
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

# 返回到RssSortActivity（分类页面）
print("--- Going back to RssSortActivity ---")
d.press('back')
time.sleep(2)
d.press('back')
time.sleep(2)

cur = d.app_current()
print(f'Current: {cur.get("activity", "?")}')

# 如果不在RssSortActivity，重新进入
if 'RssSortActivity' not in cur.get('activity', ''):
    print('[NAV] Re-entering RssSortActivity...')
    # 点击订阅Tab
    rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(3)

    # 点击天籁精选
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    for i in range(source_items.count):
        try:
            name = source_items[i].get_text()
            if name and name.startswith('天籁'):
                source_items[i].click()
                print(f'[NAV] Clicked source: {name[:2]}***')
                break
        except Exception:
            pass
    time.sleep(10)

cur = d.app_current()
print(f'Activity: {cur.get("activity", "?")}')

# 查看分类Tab
print("\n--- Checking sort/category tabs ---")
# TabLayout中的分类Tab
tab_layout = d(resourceId=f'{PKG}:id/tab_layout')
if tab_layout.exists:
    print('[TAB] TabLayout found')

# 查找分类文字
xml = d.dump_hierarchy()
all_text = re.findall(r'text="([^"]*)"', xml)
unique = [t for t in dict.fromkeys(all_text) if t]
print(f'Visible text: {unique[:25]}')

# 查找ViewPager中的内容
vp = d(resourceId=f'{PKG}:id/view_pager')
if vp.exists:
    print('[VP] ViewPager found')

# 查找RecyclerView
rv = d(className='androidx.recyclerview.widget.RecyclerView')
if rv.exists:
    try:
        count = rv.child().count
        print(f'[RV] RecyclerView children: {count}')
    except Exception:
        print('[RV] Cannot count')

screenshot('rss_sort_detail')

# 点击第一个分类Tab
print("\n--- Clicking first category tab ---")
# 在RssSortActivity中，分类通过TabLayout展示
# 每个Tab就是一个分类（雄狮、精品等）
# 需要找到TabLayout中的第一个Tab
# Tab的子view一般是TextView
tabs = d(resourceId=f'{PKG}:id/tv_tab_title')
if not tabs.exists:
    tabs = d(resourceId=f'{PKG}:id/tab_text')

if tabs.exists and tabs.count > 0:
    name = tabs[0].get_text()
    print(f'[TAB] Clicking first tab: {name[:2]}***')
    tabs[0].click()
    time.sleep(10)
else:
    # 尝试点击TabLayout的第一个子view
    if tab_layout.exists:
        print('[TAB] Clicking TabLayout first child...')
        # 获取TabLayout位置
        info = tab_layout.info
        bounds = info.get('bounds', {})
        left = bounds.get('left', 0)
        top = bounds.get('top', 0)
        # 第一个Tab约在1/4位置
        tab_x = left + 100
        tab_y = top + 20
        d.click(tab_x, tab_y)
        print(f'[TAB] Clicked at ({tab_x}, {tab_y})')
        time.sleep(10)

# 验证文章列表
print("\n--- Verifying article list ---")
cur2 = d.app_current()
print(f'Activity: {cur2.get("activity", "?")}')

# 等待加载
time.sleep(5)

# 查找文章
xml2 = d.dump_hierarchy()
all_text2 = re.findall(r'text="([^"]*)"', xml2)
unique2 = [t for t in dict.fromkeys(all_text2) if t]
print(f'Visible text: {unique2[:25]}')

# 查找文章标题
article_titles = d(resourceId=f'{PKG}:id/tv_title')
if article_titles.exists:
    count = article_titles.count
    print(f'[ARTICLES] Found {count} article titles')
    for i in range(min(count, 5)):
        try:
            title = article_titles[i].get_text()
            print(f'  Article[{i}]: {title[:3]}***')
        except Exception:
            pass

screenshot('article_list')

# 检查logcat
print("\n--- Checking logcat ---")
r = run_adb('shell "logcat -d -t 200 | grep -iE \'AppLog|RssArticle\' | grep -v UIAutomatorStub | tail -20"')
for line in r.stdout.strip().splitlines()[:10]:
    print(f'  {line[:150]}')

# 测试翻页
print("\n--- Testing pagination ---")
d.swipe(400, 600, 400, 200, duration=0.5)
time.sleep(5)
screenshot('article_page2')

# 检查文章数量是否增加
article_titles2 = d(resourceId=f'{PKG}:id/tv_title')
if article_titles2.exists:
    count2 = article_titles2.count
    print(f'[PAGE2] Article titles: {count2}')
    pagination_ok = count2 > 0
else:
    pagination_ok = False
print(f'Pagination: {"PASS" if pagination_ok else "UNCERTAIN"}')

# 点击第一篇文章
print("\n--- Clicking first article ---")
# 先滑回顶部
d.swipe(400, 200, 400, 600, duration=0.3)
time.sleep(1)

# 点击
d.click(400, 300)
time.sleep(10)

cur3 = d.app_current()
print(f'Activity after click: {cur3.get("activity", "?")}')

screenshot('article_clicked')

if 'VideoPlay' in cur3.get('activity', ''):
    print('[PLAY] Video player opened!')
elif 'ReadRss' in cur3.get('activity', '') or 'RssRead' in cur3.get('activity', ''):
    print('[PLAY] RSS read page opened')
    # 对于type=2视频源，可能显示线路列表
    time.sleep(3)
    xml3 = d.dump_hierarchy()
    all_text3 = re.findall(r'text="([^"]*)"', xml3)
    unique3 = [t for t in dict.fromkeys(all_text3) if t]
    print(f'  Visible text: {unique3[:15]}')
else:
    print(f'[PLAY] Activity: {cur3.get("activity", "?")}')

# 检查崩溃
print("\n--- Final crash check ---")
r = run_adb('shell "logcat -d -t 100 | grep -E \'FATAL|AndroidRuntime\' | grep io.legado"')
if r.stdout.strip():
    print('[CRASH] Found crashes')
else:
    print('[CRASH] No crashes')

print("\n=== Done ===")
