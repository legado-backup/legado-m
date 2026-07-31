#!/usr/bin/env python3
"""测试源内搜索：用search_go_btn提交搜索，而不是enter键"""
import uiautomator2 as u2
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
d = u2.connect('127.0.0.1:21503')

# Navigate to first AV source
d(resourceId=f'{PKG}:id/menu_rss').click()
time.sleep(2)
items = d(resourceId=f'{PKG}:id/tv_name')
if items.exists and items.count > 2:
    items[2].click()
    time.sleep(5)
    
    act = d.app_current().get('activity', '?')
    print(f'Activity: {act}')
    
    # Step 1: Click search menu button
    search_btn = d(resourceId=f'{PKG}:id/menu_search')
    search_btn.click()
    time.sleep(2)
    
    # Step 2: Type in search input
    search_input = d(resourceId=f'{PKG}:id/search_src_text')
    if search_input.exists:
        search_input.click()
        time.sleep(0.5)
        search_input.set_text('HD')
        time.sleep(1)
        
        # Method 1: Try search_go_btn
        go_btn = d(resourceId=f'{PKG}:id/search_go_btn')
        print(f'search_go_btn exists: {go_btn.exists}')
        if go_btn.exists:
            go_btn.click()
            time.sleep(15)
            act2 = d.app_current().get('activity', '?')
            print(f'After go_btn: {act2}')
            titles = d(resourceId=f'{PKG}:id/tv_title')
            print(f'Titles: {titles.count if titles.exists else 0}')
        
        # If still no results, try IME action
        if d(resourceId=f'{PKG}:id/tv_title').count == 0:
            # Clear and retype
            search_input.set_text('HD')
            time.sleep(0.5)
            # Use d.set_fastinput_ime(True) and then send Enter via IME
            d.set_fastinput_ime(True)
            search_input.send_keys('HD')
            d.press('enter')
            time.sleep(15)
            act3 = d.app_current().get('activity', '?')
            print(f'After IME enter: {act3}')
            titles = d(resourceId=f'{PKG}:id/tv_title')
            print(f'Titles after IME: {titles.count if titles.exists else 0}')
            d.set_fastinput_ime(False)
        
        # If still no results, try direct ADB input
        if d(resourceId=f'{PKG}:id/tv_title').count == 0:
            import subprocess
            adb = r'D:\Program Files\Microvirt\MEmu\adb.exe'
            # Use ADB to input text and press enter
            subprocess.run(f'"{adb}" -s 127.0.0.1:21503 shell input text "HD"', shell=True)
            time.sleep(1)
            subprocess.run(f'"{adb}" -s 127.0.0.1:21503 shell input keyevent 66', shell=True)  # KEYCODE_ENTER
            time.sleep(15)
            act4 = d.app_current().get('activity', '?')
            print(f'After ADB enter: {act4}')
            titles = d(resourceId=f'{PKG}:id/tv_title')
            print(f'Titles after ADB: {titles.count if titles.exists else 0}')
