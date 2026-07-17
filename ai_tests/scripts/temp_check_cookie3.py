#!/usr/bin/env python3
"""临时脚本：查询 legado.db cookies 表（force-stop 后 WAL 自动合并）"""
import sqlite3
import subprocess
import tempfile
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DB_PATH = f'/data/data/{PKG}/databases/legado.db'

def adb(*args):
    r = subprocess.run([ADB, '-s', HOST] + list(args), capture_output=True, text=True, timeout=30)
    return r

# 1. force-stop App（Room 会在 onDestroy 时 checkpoint WAL）
print('1. force-stop App...')
adb('shell', 'am', 'force-stop', PKG)
time.sleep(2)

# 2. 直接复制主 DB（force-stop 后 WAL 应已合并）
print('2. copy db...')
# 用 cat 而不是 cp，避免 su -c 的参数问题
r = adb('shell', 'su', '-c', f'cat {DB_PATH} > /sdcard/legado.db')
print(f'   cat: rc={r.returncode}')
adb('shell', 'chmod', '666', '/sdcard/legado.db')

# 3. pull
print('3. pull db...')
tmp = tempfile.mkdtemp()
tmp_db = os.path.join(tmp, 'legado.db')
r = adb('pull', '/sdcard/legado.db', tmp_db)
print(f'   pull: rc={r.returncode}, size={os.path.getsize(tmp_db) if os.path.exists(tmp_db) else "N/A"}')

# 4. open and query
print('4. open db...')
try:
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()

    # query cookies table
    print('\n--- cookies table ---')
    cur.execute('SELECT url, length(cookie) as cookie_len FROM cookies')
    rows = cur.fetchall()
    print(f'   total cookies: {len(rows)}')
    for row in rows:
        url_prefix = row[0][:3] if row[0] else ''
        print(f'   url_prefix={url_prefix}, url_len={len(row[0])}, cookie_len={row[1]}')

    # query rssSources with loginUrl
    print('\n--- rssSources with loginUrl ---')
    cur.execute('SELECT sourceUrl, loginUrl, enabledCookieJar FROM rssSources WHERE loginUrl IS NOT NULL AND loginUrl != ""')
    rows = cur.fetchall()
    print(f'   total: {len(rows)}')
    for row in rows:
        print(f'   sourceUrl_len={len(row[0])}, loginUrl_len={len(row[1])}, enabledCookieJar={row[2]}')

    conn.close()
    print('\nDone!')
except Exception as e:
    print(f'Error: {e}')
