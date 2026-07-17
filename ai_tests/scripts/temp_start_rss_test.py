#!/usr/bin/env python3
"""启动 RssSortActivity 并抓取日志（脱敏：不输出 sourceUrl 内容，直接传递给 am start）"""
import subprocess
import sys
import os
import sqlite3
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DB = r'f:\myself\github\WeAgentChat\temp\legado\temp\query_db.db'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

def sanitize(line):
    """脱敏：移除完整 URL，截断长行（但保留 DecompressDebug/CookieDebug 完整行）"""
    line = re.sub(r'https?://[^\s,]+', '[URL]', line)
    # DecompressDebug/CookieDebug 行不截断（需要完整信息分析）
    if 'DecompressDebug' in line or 'CookieDebug' in line:
        return line
    if len(line) > 250:
        return line[:120] + f'...[truncated {len(line)-120} chars]'
    return line

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
print('\n=== All AppLog (Legado tag) ===')
r = adb('logcat', '-d', '-s', 'Legado:I', timeout=15)
logs = r.stdout.decode('utf-8', errors='replace')
for line in logs.split('\n'):
    if any(kw in line for kw in ['CronetDebug', 'CookieDebug', 'DecompressDebug', 'Cronet 协议错误', 'Cronet 请求失败', 'Cronet install failed']):
        print(sanitize(line))

print('\n=== sourceDebug logcat (last 30 lines, sanitized) ===')
r = adb('logcat', '-d', '-s', 'sourceDebug:D', timeout=15)
logs = r.stdout.decode('utf-8', errors='replace')
safe_lines = [sanitize(line) for line in logs.split('\n')]
print('\n'.join(safe_lines[-30:]))

print('\n=== Done ===')
