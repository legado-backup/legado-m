#!/usr/bin/env python3
"""端到端验证订阅源完整流程 v3：
1. 进入订阅Tab
2. 点击目标源进入分类页面
3. 从分类页面搜索
4. 点击分类进入文章列表
5. 验证文章列表加载
6. 点击文章进入播放
7. 验证翻页
"""
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

results = {}

# === Step 0: 重启App ===
print("=" * 60)
print("RSS Source Full E2E Verification v3")
print("=" * 60)

print("\n--- Step 0: Restart App ---")
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)
dismiss_dialogs()
time.sleep(2)

# === Step 1: 导航到订阅Tab ===
print("\n--- Step 1: Navigate to RSS tab ---")
rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
if rss_tab.exists:
    rss_tab.click()
    print('[NAV] Clicked RSS tab')
    time.sleep(3)
else:
    print('[NAV] RSS tab not found')
    sys.exit(1)

# === Step 2: 验证源列表 ===
print("\n--- Step 2: Verify source list ---")
source_items = d(resourceId=f'{PKG}:id/tv_name')
if source_items.exists:
    count = source_items.count
    print(f'[LIST] {count} sources found')
    for i in range(min(count, 10)):
        try:
            name = source_items[i].get_text()
            print(f'  Source[{i}]: {name[:2]}***')
        except Exception:
            pass
    results['source_list'] = count > 0
else:
    print('[LIST] No sources found')
    results['source_list'] = False

screenshot('step2_source_list')

# === Step 3: 点击目标源 ===
print(f"\n--- Step 3: Click source index {TARGET_SOURCE_INDEX} ---")
if source_items.count > TARGET_SOURCE_INDEX:
    source_items[TARGET_SOURCE_INDEX].click()
    time.sleep(10)  # 动态域名需要时间
    screenshot('step3_sort_page')
    results['sort_page'] = True
else:
    print('[FAIL] Target source not found')
    results['sort_page'] = False

# === Step 4: 验证分类页面 ===
print("\n--- Step 4: Verify sort/category page ---")
cur = d.app_current()
print(f'Activity: {cur.get("activity", "?")}')

if 'RssSortActivity' in cur.get('activity', ''):
    print('[SORT] In RssSortActivity - sort page loaded')
    # 查找分类Tab
    tab_layout = d(resourceId=f'{PKG}:id/tab_layout')
    if tab_layout.exists:
        print('[SORT] Tab layout found')
    # 查找分类文字
    sort_items = d(resourceId=f'{PKG}:id/tv_name')
    if sort_items.exists:
        count = sort_items.count
        print(f'[SORT] {count} categories found')
        for i in range(min(count, 5)):
            try:
                name = sort_items[i].get_text()
                print(f'  Cat[{i}]: {name[:2]}***')
            except Exception:
                pass
    results['sort_page'] = True
else:
    print(f'[SORT] Unexpected activity: {cur.get("activity", "?")}')
    results['sort_page'] = False

# === Step 5: 从分类页面搜索 ===
print("\n--- Step 5: Search from sort page ---")
# RssSortActivity有SearchView在toolbar中
search_view = d(className='androidx.appcompat.widget.SearchView')
if not search_view.exists:
    search_view = d(resourceId=f'{PKG}:id/menu_search')

if search_view.exists:
    print('[SEARCH] Found SearchView in sort page')
    search_view.click()
    time.sleep(1)

    # 输入关键词
    edit = d(resourceId=f'{PKG}:id/search_src_text')
    if not edit.exists:
        edit = d(className='android.widget.EditText', focused=True)
    if not edit.exists:
        edit = d(className='android.widget.EditText')

    if edit.exists:
        edit.set_text('HD')
        time.sleep(0.5)

        # 点击提交按钮
        submit_btn = d(resourceId=f'{PKG}:id/search_go_btn')
        if submit_btn.exists:
            submit_btn.click()
            print('[SEARCH] Clicked submit button')
        else:
            d.press('enter')
            print('[SEARCH] Pressed enter')

        time.sleep(15)  # 搜索需要时间（动态域名+网络请求）
        screenshot('step5_search_result')

        # 检查Activity
        cur2 = d.app_current()
        print(f'Activity after search: {cur2.get("activity", "?")}')

        if 'RssSearchActivity' in cur2.get('activity', ''):
            print('[SEARCH] RssSearchActivity launched')
            time.sleep(5)  # 等待搜索结果

            # 检查搜索结果
            rv = d(className='androidx.recyclerview.widget.RecyclerView')
            if rv.exists:
                try:
                    count = rv.child().count
                    print(f'[SEARCH] Results: {count} items')
                    results['search'] = count > 0
                except Exception:
                    results['search'] = False
            else:
                print('[SEARCH] No RecyclerView found')
                results['search'] = False
        else:
            print(f'[SEARCH] Unexpected activity: {cur2.get("activity", "?")}')
            results['search'] = False
    else:
        print('[SEARCH] EditText not found')
        results['search'] = False
else:
    print('[SEARCH] SearchView not found in sort page')
    # 可能searchUrl为空导致搜索不可见
    print('[SEARCH] This may indicate searchUrl is empty or not working')
    results['search'] = False

# === Step 6: 返回分类页面，点击分类进入文章列表 ===
print("\n--- Step 6: Click category to view articles ---")
# 返回到分类页面
d.press('back')
time.sleep(2)

# 确认在RssSortActivity
cur3 = d.app_current()
print(f'Activity: {cur3.get("activity", "?")}')

if 'RssSortActivity' in cur3.get('activity', ''):
    # 点击第一个分类Tab
    # 在RssSortActivity中，分类是通过TabLayout展示的
    # ViewPager中的第一个Tab就是第一个分类
    # 点击第一个分类的文字
    first_cat = d(resourceId=f'{PKG}:id/tv_name')
    if first_cat.exists and first_cat.count > 0:
        first_cat[0].click()
        print('[CAT] Clicked first category')
        time.sleep(10)  # 等待文章列表加载
        screenshot('step6_articles')

        # 验证文章列表
        rv = d(className='androidx.recyclerview.widget.RecyclerView')
        article_count = 0
        if rv.exists:
            try:
                article_count = rv.child().count
                print(f'[ARTICLES] RecyclerView children: {article_count}')
            except Exception:
                pass

        # 查找文章标题
        article_titles = d(resourceId=f'{PKG}:id/tv_title')
        if article_titles.exists:
            count = article_titles.count
            print(f'[ARTICLES] Title items: {count}')
            article_count = max(article_count, count)

        results['article_list'] = article_count > 0
        print(f'Article list: {"PASS" if results["article_list"] else "FAIL"} ({article_count} items)')

        # === Step 7: 测试翻页 ===
        if results['article_list']:
            print("\n--- Step 7: Test pagination ---")
            d.swipe(400, 600, 400, 200, duration=0.5)
            time.sleep(5)
            screenshot('step7_page2')

            rv2 = d(className='androidx.recyclerview.widget.RecyclerView')
            if rv2.exists:
                try:
                    new_count = rv2.child().count
                    print(f'[PAGE2] RecyclerView children: {new_count}')
                    results['pagination'] = new_count >= article_count
                except Exception:
                    results['pagination'] = False
            else:
                results['pagination'] = False

            print(f'Pagination: {"PASS" if results.get("pagination") else "FAIL"}')

            # === Step 8: 点击文章进入播放 ===
            print("\n--- Step 8: Click article to play ---")
            # 先回到顶部
            d.swipe(400, 200, 400, 600, duration=0.3)
            time.sleep(1)

            # 点击第一个文章
            d.click(400, 250)
            time.sleep(10)
            screenshot('step8_article_detail')

            cur4 = d.app_current()
            print(f'Activity after click: {cur4.get("activity", "?")}')

            if 'VideoPlay' in cur4.get('activity', ''):
                print('[PLAY] Video player opened')
                results['play'] = True
            elif 'ReadRss' in cur4.get('activity', ''):
                print('[PLAY] RSS article opened (type=2 video source)')
                # 对于type=2的视频源，可能需要进一步操作
                results['play'] = True
            elif 'RssRead' in cur4.get('activity', ''):
                print('[PLAY] RSS read page opened')
                results['play'] = True
            else:
                print(f'[PLAY] Activity: {cur4.get("activity", "?")}')
                results['play'] = False
        else:
            results['pagination'] = False
            results['play'] = False
    else:
        print('[CAT] No categories found')
        results['article_list'] = False
        results['pagination'] = False
        results['play'] = False
else:
    print(f'[CAT] Not in RssSortActivity')
    results['article_list'] = False
    results['pagination'] = False
    results['play'] = False

# === Step 9: 检查无崩溃 ===
print("\n--- Step 9: Check crashes ---")
r = run_adb('shell "logcat -d -t 300 | grep -E \'FATAL|AndroidRuntime\' | grep io.legado"')
if r.stdout.strip():
    print(f'[CRASH] Found crashes:')
    for line in r.stdout.strip().splitlines()[:5]:
        print(f'  {line[:150]}')
    results['crash'] = False
else:
    print('[CRASH] No crashes')
    results['crash'] = True

# === Summary ===
print("\n" + "=" * 60)
print("Summary:")
for key, value in results.items():
    status = 'PASS' if value else 'FAIL'
    print(f'  {key}: {status}')
print("=" * 60)
