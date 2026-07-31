#!/usr/bin/env python3
"""批量验证7个订阅源：逐个点击源 → 检查分类页 → 点击分类 → 检查文章列表"""
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

d = u2.connect(HOST)

def screenshot(name):
    path = os.path.join(REPORTS, f'{name}.png')
    try:
        d.screenshot(path)
    except Exception:
        pass

def run_adb(cmd):
    full = f'"{ADB}" -s {HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    return r

def dismiss_dialogs():
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
        btn = d(text=txt)
        if btn.exists:
            btn.click()
            time.sleep(1)

# 重启App
print("=" * 60)
print("Batch RSS Source Verification")
print("=" * 60)

run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)
dismiss_dialogs()
time.sleep(2)

# 导航到订阅Tab
rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
if rss_tab.exists:
    rss_tab.click()
    time.sleep(3)
    print('[NAV] RSS tab clicked')
else:
    print('[FAIL] RSS tab not found')
    sys.exit(1)

# 获取所有源
source_items = d(resourceId=f'{PKG}:id/tv_name')
if not source_items.exists:
    print('[FAIL] No sources found')
    sys.exit(1)

total = source_items.count
print(f'[LIST] Found {total} sources')

# 逐个验证（从index 2开始是7个新源）
results = {}
for idx in range(total):
    try:
        name = source_items[idx].get_text()
    except Exception:
        continue

    # 脱敏输出
    print(f"\n--- Source[{idx}]: {name[:2]}*** ---")

    # 点击源
    try:
        source_items[idx].click()
    except Exception:
        print(f'  Cannot click source[{idx}]')
        continue

    time.sleep(10)  # 等待加载

    # 检查Activity
    cur = d.app_current()
    activity = cur.get('activity', '?')
    print(f'  Activity: {activity}')

    if 'RssSortActivity' not in activity:
        print(f'  [FAIL] Not in RssSortActivity')
        # 返回
        d.press('back')
        time.sleep(2)
        results[name[:2]] = 'FAIL: wrong activity'
        continue

    # 检查分类Tab
    xml = d.dump_hierarchy()
    all_text = re.findall(r'text="([^"]*)"', xml)
    unique = [t for t in dict.fromkeys(all_text) if t and len(t) > 1]
    # 找分类相关的文字（通常是2-4个字的分类名）
    cat_texts = [t for t in unique if len(t) <= 6 and t not in ['12', '13', '14', '15', '16', '17', '18', '19', '20'] and not t.startswith('http')]
    print(f'  Categories found: {len(cat_texts[:15])}')

    # 检查文章列表 - 查找RecyclerView中的内容
    rv = d(className='androidx.recyclerview.widget.RecyclerView')
    article_count = 0
    if rv.exists:
        try:
            article_count = rv.child().count
            print(f'  RecyclerView children: {article_count}')
        except Exception:
            pass

    # 查找文章标题
    article_titles = d(resourceId=f'{PKG}:id/tv_title')
    if article_titles.exists:
        count = article_titles.count
        print(f'  Article titles: {count}')
        article_count = max(article_count, count)

    if article_count > 0:
        results[name[:2]] = f'OK ({article_count} articles)'
        print(f'  [OK] Articles found: {article_count}')
    else:
        results[name[:2]] = 'FAIL: no articles'
        print(f'  [FAIL] No articles visible')
        # 检查logcat错误
        r = run_adb('shell "logcat -d -t 100 | grep -iE \'Exception|Error\' | grep io.legado | tail -5"')
        if r.stdout.strip():
            for line in r.stdout.strip().splitlines()[:3]:
                print(f'    [LOG] {line[:120]}')

    screenshot(f'source_{idx}')

    # 返回源列表
    d.press('back')
    time.sleep(3)

    # 重新获取source_items（返回后需要重新定位）
    source_items = d(resourceId=f'{PKG}:id/tv_name')

# Summary
print("\n" + "=" * 60)
print("Summary:")
for name, status in results.items():
    print(f"  {name}: {status}")
print("=" * 60)
