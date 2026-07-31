#!/usr/bin/env python3
"""详细分析RssSortActivity搜索流程：点击搜索→展开SearchView→输入→提交"""
import uiautomator2 as u2
import time
import re
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
    print(f'Current Activity: {act}')
    
    if 'RssSort' in act:
        # Step 1: Find search button
        search_btn = d(resourceId=f'{PKG}:id/menu_search')
        print(f'Search button exists: {search_btn.exists}')
        
        if search_btn.exists:
            search_btn.click()
            time.sleep(3)
            
            # Step 2: Check what changed
            act2 = d.app_current().get('activity', '?')
            print(f'Activity after search click: {act2}')
            
            # Dump the hierarchy to find search input
            xml = d.dump_hierarchy()
            
            # Find EditText
            edit_texts = re.findall(r'resource-id="([^"]*)"[^>]*class="android.widget.EditText"', xml)
            print(f'EditText resourceIds: {edit_texts}')
            
            # Find search-related elements
            search_ids = re.findall(r'resource-id="([^"]*search[^"]*)"', xml, re.IGNORECASE)
            print(f'All search resourceIds: {search_ids}')
            
            # Find search_src_text
            search_input = d(resourceId=f'{PKG}:id/search_src_text')
            print(f'search_src_text exists: {search_input.exists}')
            
            if search_input.exists:
                print(f'search_src_text info: {search_input.info}')
                search_input.set_text('HD')
                time.sleep(1)
                
                # Try pressing enter
                d.press('enter')
                time.sleep(10)
                
                act3 = d.app_current().get('activity', '?')
                print(f'Activity after search submit: {act3}')
                
                # Check results
                titles = d(resourceId=f'{PKG}:id/tv_title')
                print(f'Titles count: {titles.count if titles.exists else 0}')
            
            # Also try: maybe we need to click the search_button first
            search_button = d(resourceId=f'{PKG}:id/search_button')
            print(f'\nsearch_button exists: {search_button.exists}')
            if search_button.exists:
                search_button.click()
                time.sleep(2)
                
                act3 = d.app_current().get('activity', '?')
                print(f'Activity after search_button click: {act3}')
                
                # Try again to find input
                search_input = d(resourceId=f'{PKG}:id/search_src_text')
                if search_input.exists:
                    print(f'search_src_text now exists!')
                    search_input.set_text('HD')
                    time.sleep(1)
                    d.press('enter')
                    time.sleep(10)
                    
                    act4 = d.app_current().get('activity', '?')
                    print(f'Activity after 2nd submit: {act4}')
                    
                    titles = d(resourceId=f'{PKG}:id/tv_title')
                    print(f'Titles count: {titles.count if titles.exists else 0}')
            
            # Also try search_bar click
            search_bar = d(resourceId=f'{PKG}:id/search_bar')
            print(f'\nsearch_bar exists: {search_bar.exists}')
            if search_bar.exists:
                search_bar.click()
                time.sleep(2)
                act5 = d.app_current().get('activity', '?')
                print(f'Activity after search_bar click: {act5}')
    else:
        print(f'Not in RssSortActivity')
