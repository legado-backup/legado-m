#!/usr/bin/env python3
"""临时脚本：查询 legado.db cookies 表（处理 WAL）"""
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

def adb(*args, check=True):
    r = subprocess.run([ADB, '-s', HOST] + list(args), capture_output=True, text=True, timeout=30)
    print(f'  >>> adb {args[0]} rc={r.returncode}')
    if check and r.returncode != 0 and r.stderr:
        print(f'      stderr: {r.stderr[:200]}')
    return r

# 1. 不 force-stop，直接复制（保持 WAL 一致性）
print('1. copy db files (with WAL)...')
# 先删除旧的临时文件
adb('shell', 'su', '-c', 'rm -f /sdcard/legado.db*')
# 复制所有三个文件
adb('shell', 'su', '-c', f'cp {DB_PATH} /sdcard/legado.db')
adb('shell', 'su', '-c', f'cp {DB_PATH}-wal /sdcard/legado.db-wal')
adb('shell', 'su', '-c', f'cp {DB_PATH}-shm /sdcard/legado.db-shm')
adb('shell', 'su', '-c', 'chmod 666 /sdcard/legado.db*')

# 2. pull 所有文件
print('2. pull db files...')
tmp = tempfile.mkdtemp()
tmp_db = os.path.join(tmp, 'legado.db')
r = adb('pull', '/sdcard/legado.db', tmp_db)
print(f'   pull db: rc={r.returncode}, size={os.path.getsize(tmp_db) if os.path.exists(tmp_db) else "N/A"}')

tmp_wal = tmp_db + '-wal'
r = adb('pull', '/sdcard/legado.db-wal', tmp_wal)
print(f'   pull wal: rc={r.returncode}, size={os.path.getsize(tmp_wal) if os.path.exists(tmp_wal) else "N/A"}')

tmp_shm = tmp_db + '-shm'
r = adb('pull', '/sdcard/legado.db-shm', tmp_shm)
print(f'   pull shm: rc={r.returncode}, size={os.path.getsize(tmp_shm) if os.path.exists(tmp_shm) else "N/A"}')

# 3. open and query (sqlite3 会自动加载 WAL)
print('3. open db...')
try:
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()

    # 尝试 checkpoint
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
