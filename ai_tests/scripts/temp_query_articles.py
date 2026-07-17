#!/usr/bin/env python3
"""查询 rssArticles 表确认是否有文章被插入（处理 WAL）"""
import subprocess
import sqlite3
import sys
import os
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

# 1. force-stop App（让 Room checkpoint WAL）
print('--- force-stop App ---')
subprocess.run([ADB, '-s', HOST, 'shell', 'am', 'force-stop', PKG], capture_output=True, timeout=10)
import time; time.sleep(2)

# 2. 用 run-as 复制 DB（处理 WAL）
tmp_db = os.path.join(tempfile.gettempdir(), 'legado_check2.db')
if os.path.exists(tmp_db):
    os.remove(tmp_db)

# 复制主 DB
result = subprocess.run([ADB, '-s', HOST, 'shell', f'run-as {PKG} cat databases/legado.db'],
                       capture_output=True, timeout=30)
with open(tmp_db, 'wb') as f:
    f.write(result.stdout)
print(f'   DB size: {os.path.getsize(tmp_db)} bytes')

# 复制 WAL 文件
result_wal = subprocess.run([ADB, '-s', HOST, 'shell', f'run-as {PKG} cat databases/legado.db-wal'],
                           capture_output=True, timeout=30)
wal_path = tmp_db + '-wal'
with open(wal_path, 'wb') as f:
    f.write(result_wal.stdout)
print(f'   WAL size: {os.path.getsize(wal_path)} bytes')

# 复制 SHM 文件
result_shm = subprocess.run([ADB, '-s', HOST, 'shell', f'run-as {PKG} cat databases/legado.db-shm'],
                           capture_output=True, timeout=30)
shm_path = tmp_db + '-shm'
with open(shm_path, 'wb') as f:
    f.write(result_shm.stdout)
print(f'   SHM size: {os.path.getsize(shm_path)} bytes')

# 3. 查询
try:
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()

    # rssArticles 表
    print('\n=== rssArticles count ===')
    cur.execute('SELECT COUNT(*) FROM rssArticles')
    print(f'   total: {cur.fetchone()[0]}')

    # 最近的 5 条
    print('\n=== rssArticles recent 5 (脱敏) ===')
    cur.execute('SELECT origin, sort, title, link, read FROM rssArticles ORDER BY rowid DESC LIMIT 5')
    for row in cur.fetchall():
        origin_len = len(row[0]) if row[0] else 0
        sort_len = len(row[1]) if row[1] else 0
        title_len = len(row[2]) if row[2] else 0
        link_len = len(row[3]) if row[3] else 0
        print(f'   originLen={origin_len}, sortLen={sort_len}, titleLen={title_len}, linkLen={link_len}, read={row[4]}')

    # rssSources 表
    print('\n=== rssSources count ===')
    cur.execute('SELECT COUNT(*) FROM rssSources')
    print(f'   total: {cur.fetchone()[0]}')

    # cookies 表
    print('\n=== cookies count ===')
    cur.execute('SELECT COUNT(*) FROM cookies')
    print(f'   total: {cur.fetchone()[0]}')

    cur.execute('SELECT domain, length(cookie) FROM cookies')
    for row in cur.fetchall():
        domain_prefix = (row[0] or '')[:3]
        domain_len = len(row[0]) if row[0] else 0
        print(f'   domainPrefix={domain_prefix}, domainLen={domain_len}, cookieLen={row[1]}')

    conn.close()
except Exception as e:
    print(f'!!! Error: {e}')

# 清理 WAL/SHM 文件
for p in [wal_path, shm_path]:
    if os.path.exists(p):
        os.remove(p)

print('\nDone!')
