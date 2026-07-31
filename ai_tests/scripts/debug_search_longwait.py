#!/usr/bin/env python3
"""测试源内搜索：增加等待时间，用ADB input keyevent提交"""
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

# Restart app
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)

# Navigate to first AV source
d(resourceId=f'{PKG}:id/menu_rss').click()
time.sleep(2)
items = d(resourceId=f'{PKG}:id/tv_name')
if items.exists and items.count > 2:
    items[2].click()
    time.sleep(8)
    
    act = d.app_current().get('activity', '?')
    print(f'Activity: {act}')
    
    # Click search menu
    search_btn = d(resourceId=f'{PKG}:id/menu_search')
    search_btn.click()
    time.sleep(2)
    
    # Find search input and type
    search_input = d(resourceId=f'{PKG}:id/search_src_text')
    if search_input.exists:
        search_input.click()
        time.sleep(0.5)
        
        # Use ADB to input text (more reliable than u2 set_text)
        run_adb('shell input text "HD"')
        time.sleep(1)
        
        # Press ENTER via ADB
        run_adb('shell input keyevent 66')  # KEYCODE_ENTER
        print(f'Search submitted with ADB input')
        
        # Wait much longer (dynamic domain JS execution)
        for wait in range(6):
            time.sleep(10)
            act = d.app_current().get('activity', '?')
            titles = d(resourceId=f'{PKG}:id/tv_title')
            rv = d(className='androidx.recyclerview.widget.RecyclerView')
            rv_count = 0
            if rv.exists:
                try:
                    rv_count = rv.child().count
                except:
                    pass
            title_count = titles.count if titles.exists else 0
            print(f'  Wait {(wait+1)*10}s: Activity={act}, Titles={title_count}, RV={rv_count}')
            if title_count > 0 or rv_count > 0:
                print(f'  [OK] Search results found!')
                break
    else:
        print('search_src_text not found')
