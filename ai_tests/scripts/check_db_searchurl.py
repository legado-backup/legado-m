#!/usr/bin/env python3
"""检查数据库中的源是否有searchUrl"""
import sqlite3, subprocess, tempfile, os, time, sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.miss.app.release'

# Force stop
subprocess.run(f'"{ADB}" -s {HOST} shell am force-stop {PKG}', shell=True)
time.sleep(2)

# Pull db
tmp = os.path.join(tempfile.gettempdir(), 'check_rss.db')
subprocess.run(f'"{ADB}" -s {HOST} shell su -c "cp /data/data/{PKG}/databases/legado.db /sdcard/legado_check.db"', shell=True)
subprocess.run(f'"{ADB}" -s {HOST} shell su -c "chmod 666 /sdcard/legado_check.db"', shell=True)
subprocess.run(f'"{ADB}" -s {HOST} pull /sdcard/legado_check.db {tmp}', shell=True)

conn = sqlite3.connect(tmp)
cur = conn.cursor()

# Check rssSources
cur.execute('SELECT sourceUrl, sourceName, searchUrl FROM rssSources WHERE sourceGroup LIKE "%AV%" LIMIT 7')
rows = cur.fetchall()
for r in rows:
    url = r[0][:40] if r[0] else ''
    name = r[1][:8] if r[1] else ''
    search_url = r[2][:30] if r[2] else 'EMPTY'
    print(f'{name}: url={url} searchUrl={search_url}...')

conn.close()
os.unlink(tmp)
