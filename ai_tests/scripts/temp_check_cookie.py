#!/usr/bin/env python3
"""临时脚本：查询 legado.db cookies 表和 CacheManager 内存缓存状态"""
import sqlite3
import subprocess
import tempfile
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DB_PATH = f'/data/data/{PKG}/databases/legado.db'

def adb(*args):
    r = subprocess.run([ADB, '-s', HOST] + list(args), capture_output=True, text=True, timeout=30)
    return r

# 1. force-stop App 确保数据已落盘
print('1. force-stop App...')
adb('shell', 'am', 'force-stop', PKG)

# 2. copy db to sdcard
print('2. copy db to sdcard...')
adb('shell', 'su', '-c', f'cp {DB_PATH} /sdcard/legado.db; chmod 666 /sdcard/legado.db')
adb('shell', 'su', '-c', f'cp {DB_PATH}-wal /sdcard/legado.db-wal 2>/dev/null; chmod 666 /sdcard/legado.db-wal 2>/dev/null; true')
adb('shell', 'su', '-c', f'cp {DB_PATH}-shm /sdcard/legado.db-shm 2>/dev/null; chmod 666 /sdcard/legado.db-shm 2>/dev/null; true')

# 3. pull db
print('3. pull db...')
tmp = tempfile.mkdtemp()
tmp_db = os.path.join(tmp, 'legado.db')
adb('pull', '/sdcard/legado.db', tmp_db)
adb('pull', '/sdcard/legado.db-wal', tmp_db + '-wal')
adb('pull', '/sdcard/legado.db-shm', tmp_db + '-shm')

# 4. open and query
print('4. query cookies...')
conn = sqlite3.connect(tmp_db)
cur = conn.cursor()

# checkpoint WAL
try:
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    print(f'   wal_checkpoint: {cur.fetchone()}')
except Exception as e:
    print(f'   wal_checkpoint failed: {e}')

# query cookies table
print('\n--- cookies table ---')
cur.execute('SELECT url, length(cookie) as cookie_len FROM cookies')
rows = cur.fetchall()
print(f'   total cookies: {len(rows)}')
for row in rows:
    # 脱敏：只输出 url 前缀和长度
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
