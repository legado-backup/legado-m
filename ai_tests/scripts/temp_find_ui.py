#!/usr/bin/env python3
"""临时脚本：查找 UI 元素坐标"""
import subprocess
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

# dump UI
subprocess.run([ADB, '-s', HOST, 'shell', 'uiautomator', 'dump', '/data/local/tmp/ui.xml'],
               capture_output=True)
r = subprocess.run([ADB, '-s', HOST, 'shell', 'cat', '/data/local/tmp/ui.xml'],
                  capture_output=True, text=True, encoding='utf-8', errors='replace')
xml = r.stdout or ''

# find all nodes with bounds and text/content-desc
pattern = r'<node[^>]*(?:text="([^"]*)"|content-desc="([^"]*)")[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
matches = re.findall(pattern, xml)

print('UI elements with text/content-desc:')
for text, desc, x1, y1, x2, y2 in matches:
    label = text or desc
    if label:
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2
        print(f'  {label}: center=({cx},{cy}) bounds=[{x1},{y1}][{x2},{y2}]')
