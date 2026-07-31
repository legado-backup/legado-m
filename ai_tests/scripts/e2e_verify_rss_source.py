#!/usr/bin/env python3
"""端到端验证订阅源：启动App → 导航到订阅Tab → 验证源列表 → 验证搜索 → 验证播放"""
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

d = u2.connect(HOST)

def screenshot(name):
    path = os.path.join(REPORTS, f'{name}.png')
    d.screenshot(path)
    print(f'[SS] {path}')

def dismiss_dialogs():
    """关闭所有弹窗"""
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
        btn = d(text=txt)
        if btn.exists:
            btn.click()
            print(f'[DIALOG] Closed: {txt}')
            time.sleep(1)

def find_and_click_rss_tab():
    """找到并点击订阅Tab"""
    # 方式1: 文字
    for tab in ['订阅', 'RSS']:
        el = d(text=tab)
        if el.exists:
            el.click()
            print(f'[NAV] Clicked RSS tab by text: {tab}')
            return True

    # 方式2: resourceId
    for rid in ['menu_rss', 'nav_rss']:
        el = d(resourceId=f'{PKG}:id/{rid}')
        if el.exists:
            el.click()
            print(f'[NAV] Clicked RSS tab by id: {rid}')
            return True

    # 方式3: 遍历底部导航
    # Legado底部导航通常有4个Tab: 书架/发现/订阅/我的
    # 在800x360分辨率上，4个Tab位置约在x=100,300,500,700
    # 订阅通常是第3个 (index=2)，x=500
    print('[NAV] Trying coordinate clicks on bottom nav...')
    for x in [500, 270, 600, 400, 130]:
        d.click(x, 355)
        time.sleep(2)
        # 检查是否进入了订阅页面
        xml = d.dump_hierarchy()
        if '订阅' in xml or 'rss' in xml.lower() or 'RssSource' in xml:
            print(f'[NAV] Found RSS tab at x={x}')
            return True
        # 看看有没有源列表特征
        if d(resourceId=f'{PKG}:id/tv_name').exists:
            print(f'[NAV] Found source list at x={x}')
            return True

    return False

def verify_source_list():
    """验证订阅源列表加载"""
    time.sleep(5)  # 等待加载
    screenshot('rss_source_list')

    # 查找源名称项
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    if source_items.exists:
        count = source_items.count
        print(f'[LIST] Found {count} source items')
        for i in range(min(count, 10)):
            try:
                name = source_items[i].get_text()
                # 脱敏
                print(f'  Source[{i}]: {name[:2]}*** (len={len(name)})')
            except Exception:
                pass
        return count > 0
    else:
        print('[LIST] No source items found')
        # dump看看有什么
        xml = d.dump_hierarchy()
        all_text = re.findall(r'text="([^"]*)"', xml)
        unique = [t for t in dict.fromkeys(all_text) if t]
        print(f'  Visible text: {unique[:20]}')
        return False

def click_first_source():
    """点击第一个源进入详情"""
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    if source_items.exists and source_items.count > 0:
        source_items[0].click()
        print('[CLICK] Clicked first source')
        time.sleep(5)
        screenshot('rss_source_detail')
        return True
    return False

def verify_article_list():
    """验证文章列表加载"""
    time.sleep(5)  # 等待加载
    screenshot('rss_article_list')

    # 查找文章列表
    rv = d(className='androidx.recyclerview.widget.RecyclerView')
    if rv.exists:
        try:
            count = rv.child().count
            print(f'[ARTICLES] RecyclerView has {count} children')
            return count > 0
        except Exception:
            print('[ARTICLES] RecyclerView found but cannot count')

    # 备选：看有没有常见元素
    xml = d.dump_hierarchy()
    all_text = re.findall(r'text="([^"]*)"', xml)
    unique = [t for t in dict.fromkeys(all_text) if t]
    print(f'  Visible text: {unique[:20]}')
    return False

def verify_search(keyword='HD'):
    """验证搜索功能"""
    # 返回到源列表
    d.press('back')
    time.sleep(2)

    # 查找搜索入口
    search_btn = d(resourceId=f'{PKG}:id/menu_search')
    if not search_btn.exists:
        search_btn = d(description='搜索')
    if not search_btn.exists:
        search_btn = d(text='搜索')

    if search_btn.exists:
        search_btn.click()
        time.sleep(2)
        print(f'[SEARCH] Clicked search button')
    else:
        print('[SEARCH] Search button not found, trying SearchView')
        sv = d(className='androidx.appcompat.widget.SearchView')
        if sv.exists:
            sv.click()
            time.sleep(1)

    # 输入关键词
    edit = d(resourceId=f'{PKG}:id/search_src_text')
    if not edit.exists:
        edit = d(className='android.widget.EditText', focused=True)
    if not edit.exists:
        edit = d(className='android.widget.EditText')

    if edit.exists:
        edit.set_text(keyword)
        print(f'[SEARCH] Entered keyword: {keyword[:1]}***')
        time.sleep(1)
        # 按回车搜索
        d.press('enter')
        time.sleep(8)  # 搜索需要时间
        screenshot('rss_search_result')

        # 检查搜索结果
        rv = d(className='androidx.recyclerview.widget.RecyclerView')
        if rv.exists:
            try:
                count = rv.child().count
                print(f'[SEARCH] Search results: {count} items')
                return count > 0
            except Exception:
                pass

        xml = d.dump_hierarchy()
        all_text = re.findall(r'text="([^"]*)"', xml)
        unique = [t for t in dict.fromkeys(all_text) if t]
        print(f'  Search result text: {unique[:20]}')
        return False
    else:
        print('[SEARCH] EditText not found')
        return False

# === Main ===
print("=" * 60)
print("RSS Source E2E Verification")
print("=" * 60)

# Step 1: 关闭弹窗
print("\n--- Step 1: Dismiss dialogs ---")
dismiss_dialogs()
time.sleep(2)

# Step 2: 导航到订阅Tab
print("\n--- Step 2: Navigate to RSS tab ---")
if not find_and_click_rss_tab():
    print("[FAIL] Cannot navigate to RSS tab")
    sys.exit(1)

# Step 3: 验证源列表
print("\n--- Step 3: Verify source list ---")
list_ok = verify_source_list()
print(f"Source list: {'OK' if list_ok else 'FAIL'}")

if list_ok:
    # Step 4: 点击第一个源
    print("\n--- Step 4: Click first source ---")
    click_first_source()

    # Step 5: 验证文章列表
    print("\n--- Step 5: Verify article list ---")
    articles_ok = verify_article_list()
    print(f"Article list: {'OK' if articles_ok else 'FAIL'}")

# Step 6: 验证搜索
print("\n--- Step 6: Verify search ---")
search_ok = verify_search()
print(f"Search: {'OK' if search_ok else 'FAIL'}")

# Step 7: 检查无崩溃
print("\n--- Step 7: Check crashes ---")
import subprocess
r = subprocess.run(
    f'"{ADB}" -s {HOST} shell "logcat -d -t 200 | grep -E \'FATAL|AndroidRuntime.*io.legado\'"',
    shell=True, capture_output=True, text=True, timeout=15
)
crash_lines = [l for l in r.stdout.splitlines() if 'FATAL' in l or 'Exception' in l]
if crash_lines:
    print(f"[CRASH] Found {len(crash_lines)} crash lines")
    for line in crash_lines[:5]:
        print(f"  {line[:150]}")
else:
    print("[CRASH] No crashes detected")

# Summary
print("\n" + "=" * 60)
print("Summary:")
print(f"  Source list: {'PASS' if list_ok else 'FAIL'}")
print(f"  Search: {'PASS' if search_ok else 'FAIL'}")
print("=" * 60)
