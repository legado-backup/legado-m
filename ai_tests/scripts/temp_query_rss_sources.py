#!/usr/bin/env python3
"""查询设备上的订阅源列表（脱敏：只输出编号和 sourceUrl 长度，不输出完整 URL）"""
import subprocess
import sys
import os
import sqlite3
import shutil
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

def adb(*args, timeout=15):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

# 1. force-stop App（避免 WAL 问题）
adb('shell', 'am', 'force-stop', PKG)
import time
time.sleep(1)

# 2. 复制数据库到 /sdcard（用 run-as 在 debug 包内访问）
print('--- copying DB ---')
# 先删除旧的
adb('shell', 'rm', '/sdcard/legado_query.db', '/sdcard/legado_query.db-wal', '/sdcard/legado_query.db-shm')

# 用 run-as 复制
r = adb('shell', 'run-as', PKG, 'cp', '/data/data/' + PKG + '/databases/legado.db', '/data/data/' + PKG + '/files/temp_query.db')
print(f'  run-as cp result: {r.returncode}')
# 复制 WAL/SHM（如果存在）
adb('shell', 'run-as', PKG, 'cp', '/data/data/' + PKG + '/databases/legado.db-wal', '/data/data/' + PKG + '/files/temp_query.db-wal')
adb('shell', 'run-as', PKG, 'cp', '/data/data/' + PKG + '/databases/legado.db-shm', '/data/data/' + PKG + '/files/temp_query.db-shm')

# 改权限让外部可读
adb('shell', 'run-as', PKG, 'chmod', '644', '/data/data/' + PKG + '/files/temp_query.db')
adb('shell', 'run-as', PKG, 'chmod', '644', '/data/data/' + PKG + '/files/temp_query.db-wal')
adb('shell', 'run-as', PKG, 'chmod', '644', '/data/data/' + PKG + '/files/temp_query.db-shm')

# cat 到 /sdcard
r = adb('shell', 'cat', '/data/data/' + PKG + '/files/temp_query.db', '>', '/sdcard/legado_query.db')
print(f'  cat db result: {r.returncode}')
adb('shell', 'cat', '/data/data/' + PKG + '/files/temp_query.db-wal', '>', '/sdcard/legado_query.db-wal')
adb('shell', 'cat', '/data/data/' + PKG + '/files/temp_query.db-shm', '>', '/sdcard/legado_query.db-shm')

# 3. pull 到本地
local_db = r'f:\myself\github\WeAgentChat\temp\legado\temp\query_db.db'
os.makedirs(os.path.dirname(local_db), exist_ok=True)
if os.path.exists(local_db):
    os.remove(local_db)
for ext in ['', '-wal', '-shm']:
    p = local_db + ext
    if os.path.exists(p):
        os.remove(p)

adb('pull', '/sdcard/legado_query.db', local_db)
adb('pull', '/sdcard/legado_query.db-wal', local_db + '-wal')
adb('pull', '/sdcard/legado_query.db-shm', local_db + '-shm')

# 4. 查询
print('\n--- querying rssSources ---')
try:
    conn = sqlite3.connect(local_db)
    cur = conn.cursor()
    # 查询有 loginUrl 的订阅源（脱敏：只输出编号、sourceUrl 长度、enabledCookieJar、loginUrl 是否非空）
    cur.execute('''
        SELECT sourceUrl, loginUrl, enabledCookieJar
        FROM rssSources
        WHERE loginUrl IS NOT NULL AND loginUrl != ''
        LIMIT 10
    ''')
    rows = cur.fetchall()
    print(f'sources with loginUrl: {len(rows)}')
    for i, row in enumerate(rows):
        source_url = row[0] or ''
        login_url = row[1] or ''
        cookie_jar = row[2]
        # 只输出长度和技术字段，不输出完整 URL
        print(f'  [{i}] sourceUrl_len={len(source_url)}, loginUrl_len={len(login_url)}, enabledCookieJar={cookie_jar}')
        # 输出 sourceUrl 的协议+域名前缀（用于识别，不完整输出）
        if '://' in source_url:
            prefix = source_url.split('://')[0] + '://' + source_url.split('://')[1].split('/')[0]
            print(f'       domain_prefix={prefix[:30]}...')

    # 也查询所有订阅源（对照组）
    cur.execute('SELECT COUNT(*) FROM rssSources')
    total = cur.fetchone()[0]
    print(f'\ntotal rssSources: {total}')

    conn.close()
except Exception as e:
    print(f'ERROR: {e}')
