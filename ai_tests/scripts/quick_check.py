#!/usr/bin/env python3
"""快速检查RssSearchActivity搜索结果"""
import uiautomator2 as u2
import time
import re
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

d = u2.connect('127.0.0.1:21503')

# 检查当前Activity
cur = d.app_current()
print(f'Activity: {cur.get("activity", "?")}')

# dump visible text
xml = d.dump_hierarchy()
all_text = re.findall(r'text="([^"]*)"', xml)
unique = [t for t in dict.fromkeys(all_text) if t]
print(f'Visible text ({len(unique)}): {unique[:25]}')

# check RecyclerView
rv = d(className='androidx.recyclerview.widget.RecyclerView')
if rv.exists:
    try:
        count = rv.child().count
        print(f'RecyclerView children: {count}')
    except Exception:
        print('RecyclerView found but cannot count')

d.screenshot(r'f:\myself\github\WeAgentChat\temp\legado\ai_tests\reports\rss_search_direct.png')
print('Screenshot saved')
