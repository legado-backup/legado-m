#!/usr/bin/env python3
"""启动 RssSortActivity 并抓取日志（脱敏：不输出 sourceUrl 内容，直接传递给 am start）"""
import subprocess
import sys
import os
import sqlite3
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DB = r'f:\myself\github\WeAgentChat\temp\legado\temp\query_db.db'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

# 1. 从数据库查询第一个有 loginUrl 的源的 sourceUrl
print('--- query sourceUrl from DB ---')
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT sourceUrl FROM rssSources
        WHERE loginUrl IS NOT NULL AND loginUrl != ''
        AND length(sourceUrl) > 10
        LIMIT 1
    ''')
    row = cur.fetchone()
    conn.close()
    if not row:
        print('ERROR: no source with loginUrl found')
        sys.exit(1)
    source_url = row[0]
    # 不输出 sourceUrl 内容，只输出长度
    print(f'  found source: sourceUrl_len={len(source_url)}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# 2. 启动 App（确保 App 在运行）
print('--- start App ---')
adb('shell', 'am', 'start', '-n', PKG + '/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(3)

# 3. 启动 RssSortActivity（不输出 sourceUrl 内容）
print('--- start RssSortActivity ---')
r = adb('shell', 'am', 'start',
        '-n', PKG + '/io.legado.app.ui.rss.article.RssSortActivity',
        '--es', 'sourceUrl', source_url)
print(f'  am start result: {r.returncode}')

# 4. 等待加载
print('--- wait 5s for load ---')
time.sleep(5)

# 5. 清空 logcat
print('--- clear logcat ---')
adb('logcat', '-c')

# 6. 下拉刷新
print('--- swipe down to refresh ---')
adb('shell', 'input', 'swipe', '800', '500', '800', '900', '400')

# 7. 等待加载
print('--- wait 15s ---')
time.sleep(15)

# 8. 抓取日志（只过滤技术 tag，不输出完整 URL）
print('\n=== CronetDebug logcat ===')
r = adb('logcat', '-d', '-s', 'Legado:I', timeout=15)
logs = r.stdout.decode('utf-8', errors='replace')
# 过滤包含 CronetDebug 或 CookieDebug 的行
for line in logs.split('\n'):
    if 'CronetDebug' in line or 'CookieDebug' in line or 'Cronet 协议错误' in line or 'Cronet 请求失败' in line:
        # 脱敏：移除完整 URL，只保留路径片段
        import re
        # 移除 http:// 或 https:// 开头的 URL
        safe_line = re.sub(r'https?://[^\s,]+', '[URL]', line)
        print(safe_line)

print('\n=== sourceDebug logcat (last 3000 chars) ===')
r = adb('logcat', '-d', '-s', 'sourceDebug:D', timeout=15)
logs = r.stdout.decode('utf-8', errors='replace')
# 脱敏：移除完整 URL
import re
safe_logs = re.sub(r'https?://[^\s,]+', '[URL]', logs)
# 截断长行（避免输出大量乱码）
safe_lines = []
for line in safe_logs.split('\n'):
    if len(line) > 200:
        safe_lines.append(line[:100] + f'...[truncated {len(line)-100} chars]')
    else:
        safe_lines.append(line)
print('\n'.join(safe_lines[-30:]))

print('\n=== Done ===')
