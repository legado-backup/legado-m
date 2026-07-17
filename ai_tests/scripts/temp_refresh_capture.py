#!/usr/bin/env python3
"""刷新文章列表并抓取完整 logcat 日志"""
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

# 1. 清空 logcat
print('--- clear logcat ---')
adb('logcat', '-c')

# 2. 下拉刷新（从 400 到 800 模拟下拉）
print('--- swipe down to refresh ---')
adb('shell', 'input', 'swipe', '800', '400', '800', '800', '300')

# 3. 等待加载完成
print('--- wait 8s for loading ---')
time.sleep(8)

# 4. 抓取 logcat
print('--- capture logcat ---')
result = adb('logcat', '-d', '-s', 'Legado:*', timeout=30)
logs = result.stdout.decode('utf-8', errors='replace')

# 输出所有日志（不过滤）
print(f'\n=== Full Legado logcat ({len(logs)} chars) ===')
for line in logs.split('\n'):
    if line.strip():
        print(line)

# 5. 抓取所有错误日志
print('\n=== Error logs ===')
result2 = adb('logcat', '-d', '-s', 'AndroidRuntime:E', timeout=10)
err_logs = result2.stdout.decode('utf-8', errors='replace')
for line in err_logs.split('\n'):
    if line.strip():
        print(line)

# 6. 抓取所有 AppLog（含 IOException）
print('\n=== All logs containing "io.legado" ===')
result3 = adb('logcat', '-d', timeout=30)
all_logs = result3.stdout.decode('utf-8', errors='replace')
count = 0
for line in all_logs.split('\n'):
    if 'io.legado' in line and ('Exception' in line or 'Error' in line or '失败' in line or '获取' in line or 'fail' in line.lower()):
        print(line[:300])
        count += 1
        if count > 50:
            break

print(f'\n=== Done. Found {count} relevant lines. ===')
