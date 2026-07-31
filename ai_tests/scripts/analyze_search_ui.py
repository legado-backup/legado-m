#!/usr/bin/env python3
"""分析RssSortActivity的搜索入口UI元素"""
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

# Navigate to a source
d(resourceId=f'{PKG}:id/menu_rss').click()
time.sleep(2)
items = d(resourceId=f'{PKG}:id/tv_name')
if items.exists and items.count > 2:
    items[2].click()  # Click first AV source
    time.sleep(5)
    
    act = d.app_current().get('activity', '?')
    print(f'Current Activity: {act}')
    
    if 'RssSort' in act:
        xml = d.dump_hierarchy()
        
        # Find search-related elements
        search_ids = re.findall(r'resource-id="([^"]*search[^"]*)"', xml, re.IGNORECASE)
        print(f'Search resourceIds: {search_ids[:10]}')
        
        search_descs = re.findall(r'content-desc="([^"]*search[^"]*)"', xml, re.IGNORECASE)
        print(f'Search content-descs: {search_descs[:10]}')
        
        search_texts = re.findall(r'text="([^"]*搜索[^"]*)"', xml, re.IGNORECASE)
        print(f'Search texts: {search_texts[:10]}')
        
        menu_ids = re.findall(r'resource-id="([^"]*menu[^"]*)"', xml, re.IGNORECASE)
        print(f'Menu resourceIds: {menu_ids[:10]}')
        
        # Find all clickable elements with content-desc
        clickable_descs = re.findall(r'clickable="true"[^>]*content-desc="([^"]*)"', xml)
        print(f'Clickable with content-desc: {clickable_descs[:15]}')
        
        # Find action bar items
        action_ids = re.findall(r'resource-id="([^"]*action[^"]*)"', xml, re.IGNORECASE)
        print(f'Action resourceIds: {action_ids[:10]}')
        
        # Also dump a small portion of toolbar area
        toolbar = re.findall(r'resource-id="([^"]*toolbar[^"]*)"', xml, re.IGNORECASE)
        print(f'Toolbar resourceIds: {toolbar[:10]}')
    else:
        print(f'Not in RssSortActivity, got: {act}')
else:
    print('No sources found')
