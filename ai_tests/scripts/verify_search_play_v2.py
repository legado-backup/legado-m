#!/usr/bin/env python3
"""正确的源内搜索测试：先进入源→点击搜索按钮→输入→用search_go_btn提交"""
import uiautomator2 as u2
import time
import sys
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
d = u2.connect(HOST)

def run_adb(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} {cmd}'
    return subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)

def go_back_to_main():
    for _ in range(6):
        act = d.app_current().get('activity', '?')
        if 'MainActivity' in act:
            return True
        d.press('back')
        time.sleep(1.5)
    return False

SOURCES = [
    {'name': '源[1]天籁', 'prefix': '天籁'},
    {'name': '源[2]撸色', 'prefix': '撸色'},
    {'name': '源[3]青涩', 'prefix': '青涩'},
    {'name': '源[4]窝窝', 'prefix': '窝窝'},
    {'name': '源[5]桃花', 'prefix': '桃花'},
    {'name': '源[6]秘密', 'prefix': '秘密'},
    {'name': '源[7]Papa', 'prefix': 'Papa'},
]

# Start app
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)

# Dismiss dialogs
for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
    btn = d(text=txt)
    if btn.exists:
        btn.click()
        time.sleep(1)

results = {}

for src in SOURCES:
    name = src['name']
    prefix = src['prefix']
    
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"{'='*50}")
    
    # 1. Navigate to RSS tab
    rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(2)
    
    # 2. Find and click the source
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    clicked = False
    if source_items.exists:
        for i in range(source_items.count):
            try:
                txt = source_items[i].get_text()
                if prefix in txt:
                    source_items[i].click()
                    clicked = True
                    break
            except:
                continue
    
    if not clicked:
        print(f"  [FAIL] Source not found")
        results[name] = {'search': 'FAIL', 'play': 'SKIP'}
        go_back_to_main()
        continue
    
    time.sleep(8)
    act = d.app_current().get('activity', '?')
    if 'RssSortActivity' not in act:
        print(f"  [FAIL] Not in RssSortActivity: {act}")
        results[name] = {'search': 'FAIL', 'play': 'SKIP'}
        go_back_to_main()
        continue
    
    print(f"  [OK] Entered RssSortActivity")
    
    # 3. Click search menu button
    search_btn = d(resourceId=f'{PKG}:id/menu_search')
    if not search_btn.exists:
        print(f"  [SEARCH-FAIL] No search button")
        results[name] = {'search': 'FAIL', 'play': 'SKIP'}
        go_back_to_main()
        continue
    
    search_btn.click()
    time.sleep(2)
    
    # 4. Type search query and submit via search_go_btn
    search_input = d(resourceId=f'{PKG}:id/search_src_text')
    if not search_input.exists:
        print(f"  [SEARCH-FAIL] No search input")
        results[name] = {'search': 'FAIL', 'play': 'SKIP'}
        go_back_to_main()
        continue
    
    # Clear any existing text
    search_input.clear_text()
    time.sleep(0.5)
    search_input.set_text('HD')
    time.sleep(1)
    
    # Click the submit button (search_go_btn)
    go_btn = d(resourceId=f'{PKG}:id/search_go_btn')
    if go_btn.exists:
        go_btn.click()
        print(f"  Search submitted via go_btn")
    else:
        # Fallback: press enter via ADB
        run_adb('shell input keyevent 66')
        print(f"  Search submitted via keyevent")
    
    # 5. Wait for search results (longer wait for JS execution)
    found = False
    for wait_round in range(8):
        time.sleep(10)
        act = d.app_current().get('activity', '?')
        titles = d(resourceId=f'{PKG}:id/tv_title')
        title_count = titles.count if titles.exists else 0
        rv = d(className='androidx.recyclerview.widget.RecyclerView')
        rv_count = 0
        if rv.exists:
            try:
                rv_count = rv.child().count
            except:
                pass
        
        print(f"  Wait {(wait_round+1)*10}s: Act={act[-30:]}, Titles={title_count}, RV={rv_count}")
        
        if title_count > 0 or rv_count > 2:
            print(f"  [SEARCH-OK] {max(title_count, rv_count)} results!")
            results[name] = {'search': 'OK', 'count': max(title_count, rv_count)}
            found = True
            break
    
    if not found:
        print(f"  [SEARCH-FAIL] No results after 80s")
        results[name] = {'search': 'FAIL', 'count': 0}
    
    # 6. Go back and test play
    go_back_to_main()
    time.sleep(2)
    
    # Navigate to source again for play test
    rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(2)
    
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    play_ok = 'SKIP'
    if source_items.exists:
        for i in range(source_items.count):
            try:
                txt = source_items[i].get_text()
                if prefix in txt:
                    source_items[i].click()
                    time.sleep(8)
                    break
            except:
                continue
        
        # Click first article
        first_article = d(resourceId=f'{PKG}:id/tv_title')
        if first_article.exists:
            try:
                first_article[0].click()
                time.sleep(10)
                act = d.app_current().get('activity', '?')
                if 'VideoPlayerActivity' in act:
                    play_ok = 'OK'
                    print(f"  [PLAY-OK] VideoPlayerActivity")
                else:
                    play_ok = f'FAIL:{act[-30:]}'
                    print(f"  [PLAY-{play_ok}]")
            except:
                play_ok = 'FAIL:click'
                print(f"  [PLAY-FAIL] Cannot click")
        else:
            play_ok = 'FAIL:no articles'
            print(f"  [PLAY-FAIL] No articles")
    
    results[name]['play'] = play_ok
    go_back_to_main()
    time.sleep(2)

# Summary
print(f"\n{'='*50}")
print("FINAL SUMMARY")
print(f"{'='*50}")
all_pass = True
for name, r in results.items():
    search_ok = r['search'] == 'OK'
    play_ok = r.get('play', '') == 'OK'
    status = 'PASS' if (search_ok and play_ok) else 'FAIL'
    if not (search_ok and play_ok):
        all_pass = False
    print(f"  {name}: Search={r['search']}({r.get('count',0)}) Play={r.get('play','?')} => {status}")

if all_pass:
    print("\nALL 7 SOURCES PASSED!")
else:
    print("\nSOME SOURCES NEED FIX")
