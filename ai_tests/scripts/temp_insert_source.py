#!/usr/bin/env python3
"""临时脚本：导入站点A订阅源到数据库"""
import subprocess
import sqlite3
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

# 1. copy db to sdcard
print('1. copy db to sdcard...')
r = adb('shell', 'su', '-c', f'cp {DB_PATH} /sdcard/legado.db; chmod 666 /sdcard/legado.db')
print(f'   copy: rc={r.returncode}')

# 2. pull db
print('2. pull db...')
tmp = tempfile.mkdtemp()
tmp_db = os.path.join(tmp, 'legado.db')
r = adb('pull', '/sdcard/legado.db', tmp_db)
print(f'   pull: rc={r.returncode} {r.stderr[:100] if r.stderr else ""}')

# 3. open and insert
print('3. open db and insert...')
conn = sqlite3.connect(tmp_db)
cur = conn.cursor()

# checkpoint WAL
try:
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    print(f'   wal_checkpoint: {cur.fetchone()}')
except Exception as e:
    print(f'   wal_checkpoint failed: {e}')

# check existing
cur.execute('SELECT COUNT(*) FROM rssSources')
print(f'   rssSources count: {cur.fetchone()[0]}')

# get columns and NOT NULL info
cur.execute('PRAGMA table_info(rssSources)')
cols_info = cur.fetchall()
not_null_cols = [c[1] for c in cols_info if c[3] == 1 and c[4] is None]
print(f'   NOT NULL no-default cols: {not_null_cols}')

# insert test source (fill all NOT NULL no-default columns)
cur.execute('DELETE FROM rssSources WHERE sourceUrl = ?', ('https://mjv012.com',))
# build insert with all NOT NULL columns
source = {
    'sourceUrl': 'https://mjv012.com',
    'sourceName': 'test_a',
    'sourceComment': 'issue7',
    'enabledCookieJar': 1,
    'loginUrl': 'https://mjv012.com',
    'enabled': 1,
    'type': 0,
    'customOrder': 0,
    'sourceIcon': '',
    'singleUrl': 0,
}
all_cols = [c[1] for c in cols_info]
valid_keys = [k for k in source.keys() if k in all_cols]
placeholders = ', '.join(['?'] * len(valid_keys))
col_names = ', '.join(valid_keys)
values = [source[k] for k in valid_keys]
cur.execute(f'INSERT INTO rssSources ({col_names}) VALUES ({placeholders})', values)
conn.commit()
print('   inserted ok')

# verify
cur.execute('SELECT sourceUrl, enabledCookieJar, loginUrl FROM rssSources')
for row in cur.fetchall():
    print(f'   row: url={row[0]}, cookieJar={row[1]}, login={row[2]}')
conn.close()

# 4. push back
print('4. push db back...')
r = adb('push', tmp_db, '/sdcard/legado.db')
print(f'   push: rc={r.returncode}')
r = adb('shell', 'su', '-c', f'cp /sdcard/legado.db {DB_PATH}; chmod 660 {DB_PATH}')
print(f'   copy back: rc={r.returncode}')
r = adb('shell', 'su', '-c', f'rm -f {DB_PATH}-wal {DB_PATH}-shm')
print(f'   clean WAL: rc={r.returncode}')

print('Done!')
