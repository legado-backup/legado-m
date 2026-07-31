#!/usr/bin/env python3
"""逐个验证7个AV聚合订阅源：进入源→分类页→源内搜索→播放
关键：搜索必须在源内进行，不是全局搜索！
"""
import uiautomator2 as u2
import time
import sys
import subprocess
import re

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

SOURCES = [
    {'name': '源[1]天籁', 'prefix': '天籁'},
    {'name': '源[2]撸色', 'prefix': '撸色'},
    {'name': '源[3]青涩', 'prefix': '青涩'},
    {'name': '源[4]窝窝', 'prefix': '窝窝'},
    {'name': '源[5]桃花', 'prefix': '桃花'},
    {'name': '源[6]秘密', 'prefix': '秘密'},
    {'name': '源[7]Papa', 'prefix': 'Papa'},
]

d = u2.connect(HOST)

def run_adb(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)
    return r

def get_current_activity():
    cur = d.app_current()
    return cur.get('activity', '?')

def go_back(times=1):
    for _ in range(times):
        d.press('back')
        time.sleep(1.5)

def go_back_to_main():
    for _ in range(6):
        act = get_current_activity()
        if 'MainActivity' in act:
            return True
        d.press('back')
        time.sleep(1.5)
    return False

def navigate_to_source(prefix):
    """从主界面导航到指定源的RssSortActivity"""
    # 确保在RSS tab
    rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(2)
    
    # 找到目标源
    source_items = d(resourceId=f'{PKG}:id/tv_name')
    if not source_items.exists:
        return False
    
    for i in range(source_items.count):
        try:
            txt = source_items[i].get_text()
            if prefix in txt:
                source_items[i].click()
                time.sleep(8)
                act = get_current_activity()
                if 'RssSortActivity' in act:
                    return True
                else:
                    go_back()
                    return False
        except Exception:
            continue
    return False

def test_search_in_source(prefix):
    """在源内搜索：在RssSortActivity点击搜索→输入关键词→验证结果"""
    print(f"\n  [SEARCH-IN-SOURCE] Testing search within source...")
    
    # 在RssSortActivity中找搜索按钮（实际resourceId: menu_search）
    search_btn = d(resourceId=f'{PKG}:id/menu_search')
    if not search_btn.exists:
        search_btn = d(description='Search')
    if not search_btn.exists:
        search_btn = d(resourceId=f'{PKG}:id/search_button')
    if not search_btn.exists:
        search_btn = d(resourceId=f'{PKG}:id/action_search')
    
    if not search_btn.exists:
        print(f"    [SEARCH-FAIL] No search button found")
        return {'search': 'FAIL', 'reason': 'no search button'}
    
    # 点击搜索按钮
    try:
        search_btn.click()
        time.sleep(2)
    except Exception:
        print(f"    [SEARCH-FAIL] Cannot click search button")
        return {'search': 'FAIL', 'reason': 'search button click failed'}
    
    # 检查是否进入了搜索界面
    act = get_current_activity()
    print(f"    Activity after search click: {act}")
    
    if 'RssSearchActivity' in act:
        # 在搜索输入框中输入关键词
        search_input = d(resourceId=f'{PKG}:id/search_src_text')
        if not search_input.exists:
            search_input = d(className='android.widget.EditText')
        
        if search_input.exists:
            search_input.set_text('HD')
            time.sleep(1)
            d.press('enter')
            time.sleep(15)
            
            # 检查搜索结果
            rv = d(className='androidx.recyclerview.widget.RecyclerView')
            result_count = 0
            if rv.exists:
                try:
                    result_count = rv.child().count
                except Exception:
                    pass
            
            titles = d(resourceId=f'{PKG}:id/tv_title')
            title_count = 0
            if titles.exists:
                title_count = titles.count
            
            actual_count = max(result_count, title_count)
            print(f"    RssSearchActivity: RV={result_count}, Titles={title_count}, Max={actual_count}")
            
            if actual_count > 0:
                print(f"    [SEARCH-OK] {actual_count} results in source search")
                return {'search': 'OK', 'count': actual_count}
            else:
                # 可能还在加载
                time.sleep(10)
                titles = d(resourceId=f'{PKG}:id/tv_title')
                if titles.exists:
                    title_count = titles.count
                if title_count > 0:
                    print(f"    [SEARCH-OK] {title_count} results (after wait)")
                    return {'search': 'OK', 'count': title_count}
                print(f"    [SEARCH-FAIL] No results in source search")
                return {'search': 'FAIL', 'count': 0}
        else:
            print(f"    [SEARCH-FAIL] No search input found")
            return {'search': 'FAIL', 'reason': 'no search input'}
    
    # 如果还在RssSortActivity，可能是SearchView展开
    if 'RssSortActivity' in act:
        # 查找search_bar中的EditText
        search_input = d(resourceId=f'{PKG}:id/search_src_text')
        if not search_input.exists:
            search_input = d(className='android.widget.EditText')
        
        if search_input.exists:
            search_input.set_text('HD')
            d.press('enter')
            time.sleep(15)
            
            # 搜索结果可能直接在RssSortActivity中显示
            titles = d(resourceId=f'{PKG}:id/tv_title')
            title_count = 0
            if titles.exists:
                title_count = titles.count
            
            if title_count > 0:
                print(f"    [SEARCH-OK] {title_count} results via SearchView in Sort")
                return {'search': 'OK', 'count': title_count}
            
            # 也检查是否跳转到了RssSearchActivity
            act2 = get_current_activity()
            if 'RssSearchActivity' in act2:
                time.sleep(5)
                titles = d(resourceId=f'{PKG}:id/tv_title')
                if titles.exists:
                    title_count = titles.count
                if title_count > 0:
                    print(f"    [SEARCH-OK] {title_count} results (navigated to RssSearch)")
                    return {'search': 'OK', 'count': title_count}
        
        print(f"    [SEARCH-FAIL] SearchView in Sort but no results")
        return {'search': 'FAIL', 'reason': 'no results in sort search'}
    
    print(f"    [SEARCH-FAIL] Unexpected activity: {act}")
    return {'search': 'FAIL', 'reason': f'unexpected activity: {act}'}

def test_play_in_source():
    """在当前源（RssSortActivity）点击第一个文章验证播放"""
    print(f"\n  [PLAY] Testing play...")
    
    # 点击第一个文章
    first_article = d(resourceId=f'{PKG}:id/tv_title')
    if not first_article.exists:
        print(f"    [PLAY-FAIL] No articles visible")
        return {'play': 'FAIL', 'reason': 'no articles'}
    
    try:
        first_article[0].click()
    except Exception:
        print(f"    [PLAY-FAIL] Cannot click first article")
        return {'play': 'FAIL', 'reason': 'click failed'}
    
    time.sleep(10)
    
    act = get_current_activity()
    print(f"    Activity after click: {act}")
    
    if 'VideoPlayerActivity' in act:
        print(f"    [PLAY-OK] VideoPlayerActivity reached!")
        time.sleep(3)
        # 检查是否崩溃
        act2 = get_current_activity()
        if 'VideoPlayerActivity' not in act2:
            print(f"    [PLAY-WARN] Activity changed to: {act2}")
            return {'play': 'WARN', 'reason': f'activity changed to {act2}'}
        return {'play': 'OK', 'activity': 'VideoPlayerActivity'}
    
    if 'RssReadActivity' in act:
        time.sleep(5)
        act3 = get_current_activity()
        if 'VideoPlayerActivity' in act3:
            print(f"    [PLAY-OK] VideoPlayerActivity (from RssRead)")
            return {'play': 'OK', 'activity': 'VideoPlayerActivity'}
        print(f"    [PLAY-FAIL] RssReadActivity but no player")
        return {'play': 'FAIL', 'reason': f'RssReadActivity no player'}
    
    print(f"    [PLAY-FAIL] Unexpected: {act}")
    return {'play': 'FAIL', 'reason': f'unexpected: {act}'}


# ==================== Main ====================
print("=" * 60)
print("7-Source RSS In-Source Search + Play Verification")
print("=" * 60)

# 清空logcat
run_adb('shell logcat -c')

# 重启App
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)

# 关闭弹窗
for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过']:
    btn = d(text=txt)
    if btn.exists:
        btn.click()
        time.sleep(1)

results = {}

for src in SOURCES:
    name = src['name']
    prefix = src['prefix']
    
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    # 1. 导航到源
    nav_ok = navigate_to_source(prefix)
    if not nav_ok:
        print(f"  [FAIL] Cannot navigate to source")
        results[name] = {'search': 'FAIL', 'play': 'FAIL', 'reason': 'nav failed'}
        go_back_to_main()
        time.sleep(2)
        continue
    
    print(f"  [NAV-OK] Entered RssSortActivity")
    
    # 2. 测试源内搜索
    search_result = test_search_in_source(prefix)
    go_back(2)  # 从搜索结果返回到RssSortActivity
    time.sleep(3)
    
    # 3. 重新进入源测试播放
    go_back_to_main()
    time.sleep(2)
    nav_ok2 = navigate_to_source(prefix)
    
    play_result = {'play': 'SKIP', 'reason': 'nav failed for play test'}
    if nav_ok2:
        play_result = test_play_in_source()
    
    go_back_to_main()
    time.sleep(2)
    
    results[name] = {
        'search': search_result.get('search', '?'),
        'search_count': search_result.get('count', 0),
        'search_detail': search_result.get('reason', ''),
        'play': play_result.get('play', '?'),
        'play_detail': play_result.get('reason', play_result.get('activity', ''))
    }

# Final Summary
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"{'Source':<12} {'Search':<8} {'Count':<6} {'Play':<8} {'Detail':<25}")
print("-" * 65)
all_pass = True
for name, r in results.items():
    search_ok = r['search'] == 'OK'
    play_ok = r['play'] == 'OK'
    status = 'PASS' if (search_ok and play_ok) else 'FAIL'
    if status == 'FAIL':
        all_pass = False
    detail = r.get('search_detail', '') or r.get('play_detail', '')
    print(f"{name:<12} {r['search']:<8} {r['search_count']:<6} {r['play']:<8} {detail:<25}")

print("-" * 65)
if all_pass:
    print("ALL 7 SOURCES PASSED!")
else:
    print("SOME SOURCES FAILED - NEED FIX")
print("=" * 60)
