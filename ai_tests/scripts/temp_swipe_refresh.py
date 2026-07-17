#!/usr/bin/env python3
"""下拉刷新并实时抓取日志"""
import subprocess
import sys
import time
import threading

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

# 1. 清空 logcat
print('--- clear logcat ---')
adb('logcat', '-c')

# 2. 启动 logcat 捕获（后台线程）
captured_logs = []
def capture():
    # logcat -d 在 swipe 后调用
    pass

# 3. 下拉刷新
print('--- swipe down to refresh ---')
adb('shell', 'input', 'swipe', '800', '500', '800', '900', '400')

# 4. 等待加载
print('--- wait 15s ---')
time.sleep(15)

# 5. 抓取所有日志
print('\n=== ALL logcat (last 8000 chars) ===')
r = adb('logcat', '-d', timeout=15)
all_logs = r.stdout.decode('utf-8', errors='replace')
print(all_logs[-8000:] if len(all_logs) > 8000 else all_logs)

print('\n=== Done ===')
