#!/usr/bin/env python3
"""完整测试流程：启动App→进入订阅源→抓取日志"""
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)
    return r

# 1. 启动 App
print('--- start App ---')
adb('shell', 'am', 'start', '-n', 'io.legado.app.debug/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(4)

# 2. 进入订阅 tab
print('--- tap subscription tab ---')
adb('shell', 'input', 'tap', '958', '947')
time.sleep(2)

# 3. 清空 logcat
print('--- clear logcat ---')
adb('logcat', '-c')

# 4. 点击源[2]（之前测试过的位置）
print('--- tap source ---')
adb('shell', 'input', 'tap', '600', '413')

# 5. 等待加载
print('--- wait 12s for loading ---')
time.sleep(12)

# 6. 抓取 Legado tag 日志
print('\n=== Legado tag logs ===')
r = adb('logcat', '-d', '-s', 'Legado:*', timeout=10)
logs = r.stdout.decode('utf-8', errors='replace')
print(logs[-5000:] if len(logs) > 5000 else logs)

# 7. 抓取 sourceDebug tag 日志
print('\n=== sourceDebug tag logs ===')
r2 = adb('logcat', '-d', '-s', 'sourceDebug:*', timeout=10)
logs2 = r2.stdout.decode('utf-8', errors='replace')
print(logs2[-3000:] if len(logs2) > 3000 else logs2)

# 8. 抓取所有 AppLog 相关日志
print('\n=== All logs with AppLog/Cookie/获取 ===')
r3 = adb('logcat', '-d', timeout=15)
all_logs = r3.stdout.decode('utf-8', errors='replace')
for line in all_logs.split('\n'):
    if any(k in line for k in ['AppLog', 'CookieDebug', '获取', '失败', 'Exception', 'Cronet', 'OkHttp']):
        if 'io.legado' in line or 'Legado' in line:
            print(line[:300])

print('\n=== Done ===')
