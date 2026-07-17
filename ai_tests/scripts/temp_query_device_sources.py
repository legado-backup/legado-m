#!/usr/bin/env python3
"""从模拟器拉取 legado.db 并查询有 loginUrl 的源（脱敏输出，只输出长度和技术字段）"""
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
print('--- force-stop App to flush WAL ---')
subprocess.run([ADB, '-s', HOST, 'shell', 'am', 'force-stop', PKG], check=False)
import time; time.sleep(1)

# 2. 复制 DB 到 /sdcard 用 su 0 cat
print('--- copy DB via su ---')
tmp_db = os.path.join(tempfile.gettempdir(), 'legado_check.db')
if os.path.exists(tmp_db):
    os.remove(tmp_db)

# 使用 run-as（debug 应用可读自己的数据）
cmd = f'run-as {PKG} cat databases/legado.db'
with open(tmp_db, 'wb') as f:
    result = subprocess.run([ADB, '-s', HOST, 'shell', cmd], capture_output=True, timeout=30)
    if result.returncode == 0 and result.stdout:
        f.write(result.stdout)
    else:
        print(f'!!! run-as cat failed: {result.stderr.decode("utf-8", errors="replace")[:200]}')
        # 降级：尝试 su 0 cat
        cmd2 = f'su 0 cat /data/data/{PKG}/databases/legado.db'
        result2 = subprocess.run([ADB, '-s', HOST, 'shell', cmd2], capture_output=True, timeout=30)
        if result2.stdout:
            f.write(result2.stdout)
        else:
            print(f'!!! su cat also failed: {result2.stderr.decode("utf-8", errors="replace")[:200]}')
            sys.exit(1)

print(f'   DB copied: {os.path.getsize(tmp_db)} bytes')

# 3. 查询
conn = sqlite3.connect(tmp_db)
cur = conn.cursor()

print('\n=== rssSources with loginUrl AND ruleArticles ===')
cur.execute('''
    SELECT sourceUrl, loginUrl, enabledCookieJar,
           length(ruleArticles) as ruleArticlesLen
    FROM rssSources
    WHERE loginUrl IS NOT NULL AND loginUrl != ""
    AND ruleArticles IS NOT NULL AND length(ruleArticles) > 10
''')
rows = cur.fetchall()
print(f'   total: {len(rows)}')
for i, row in enumerate(rows):
    src_url_len = len(row[0]) if row[0] else 0
    login_url_len = len(row[1]) if row[1] else 0
    print(f'   [{i}] sourceUrl_len={src_url_len}, loginUrl_len={login_url_len}, '
          f'enabledCookieJar={row[2]}, ruleArticlesLen={row[3]}')

# 查询 cookies 表
print('\n=== cookies table ===')
cur.execute('SELECT COUNT(*), SUM(length(cookie)) FROM cookies')
r = cur.fetchone()
print(f'   rows={r[0]}, totalCookieLen={r[1]}')

cur.execute('SELECT domain, length(cookie) FROM cookies LIMIT 20')
for row in cur.fetchall():
    domain_prefix = (row[0] or '')[:3]
    print(f'   domainPrefix={domain_prefix}, domainLen={len(row[0]) if row[0] else 0}, cookieLen={row[1]}')

conn.close()
print('\nDone!')
