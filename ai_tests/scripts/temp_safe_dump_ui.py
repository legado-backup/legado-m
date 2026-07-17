#!/usr/bin/env python3
"""脱敏 dump UI：只输出坐标和编号，不输出 text 内容（避免源名称泄露）"""
import subprocess
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

def adb(*args, timeout=10):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

# dump UI
adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
result = adb('shell', 'cat', '/sdcard/ui.xml')
xml = result.stdout.decode('utf-8', errors='replace')

# 解析所有带 text 的元素，但只输出坐标和 text 长度（不输出内容）
# 格式: <node ... text="xxx" ... bounds="[x1,y1][x2,y2]" ... clickable="true" />
pattern = r'<node[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*clickable="([^"]*)"'
# 也匹配 clickable 在 text 之前的情况
pattern2 = r'<node[^>]*clickable="([^"]*)"[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'

elements = []
for m in re.finditer(pattern, xml):
    text, x1, y1, x2, y2, clickable = m.groups()
    elements.append((text, int(x1), int(y1), int(x2), int(y2), clickable == 'true'))
for m in re.finditer(pattern2, xml):
    clickable, text, x1, y1, x2, y2 = m.groups()
    elements.append((text, int(x1), int(y1), int(x2), int(y2), clickable == 'true'))

# 去重
seen = set()
unique = []
for e in elements:
    key = (e[1], e[2], e[3], e[4])
    if key not in seen and e[0]:  # 只保留有 text 的
        seen.add(key)
        unique.append(e)

print(f'=== Elements with text: {len(unique)} ===')
for i, (text, x1, y1, x2, y2, clickable) in enumerate(unique):
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    # 只输出 text 长度和坐标，不输出内容
    text_type = 'unknown'
    t = text.strip()
    if not t:
        text_type = 'empty'
    elif t.isdigit():
        text_type = 'digit'
    elif len(t) <= 4:
        text_type = 'short'  # 可能是 tab 名称
    elif len(t) <= 20:
        text_type = 'medium'
    else:
        text_type = 'long'
    click_marker = '[clickable]' if clickable else ''
    print(f'  [{i}] center=({cx},{cy}) textLen={len(t)} type={text_type} {click_marker}')

# 也输出所有 clickable=true 的元素（即使没有 text）
click_pattern = r'<node[^>]*clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
clicks = list(re.finditer(click_pattern, xml))
print(f'\n=== All clickable elements: {len(clicks)} ===')
for i, m in enumerate(clicks[:30]):
    x1, y1, x2, y2 = m.groups()
    cx = (int(x1) + int(x2)) // 2
    cy = (int(y1) + int(y2)) // 2
    print(f'  [{i}] center=({cx},{cy}) size=({int(x2)-int(x1)}x{int(y2)-int(y1)})')
