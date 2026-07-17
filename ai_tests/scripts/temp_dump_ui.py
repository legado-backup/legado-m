#!/usr/bin/env python3
"""dump UI 并解析关键元素"""
import subprocess
import sys
import re
import os

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

# dump UI
subprocess.run([ADB, '-s', HOST, 'shell', 'uiautomator', 'dump', '/sdcard/ui.xml'],
               capture_output=True, timeout=10)

# pull UI xml
result = subprocess.run([ADB, '-s', HOST, 'shell', 'cat', '/sdcard/ui.xml'],
                       capture_output=True, timeout=10)
xml = result.stdout.decode('utf-8', errors='replace')

# 解析所有 text 属性
texts = re.findall(r'text="([^"]+)"', xml)
bounds = re.findall(r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)

print('=== Visible texts (top 30) ===')
for i, t in enumerate(texts[:30]):
    if t:
        print(f'  [{i}] {t[:60]}')

print('\n=== Clickable elements with text ===')
for t, x1, y1, x2, y2 in bounds:
    if t and len(t) < 50:
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2
        print(f'  text="{t[:40]}" center=({cx},{cy})')

# 同时解析 clickable=true 的元素
clicks = re.findall(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*clickable="true"', xml)
clicks2 = re.findall(r'clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
all_clicks = clicks + clicks2
print(f'\n=== Clickable elements: {len(all_clicks)} ===')
for i, (x1, y1, x2, y2) in enumerate(all_clicks[:20]):
    cx = (int(x1) + int(x2)) // 2
    cy = (int(y1) + int(y2)) // 2
    print(f'  [{i}] center=({cx},{cy}) size=({int(x2)-int(x1)}x{int(y2)-int(y1)})')
