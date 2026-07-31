#!/usr/bin/env python3
"""检查数据库中的源searchUrl - 不force-stop"""
import sqlite3, subprocess, tempfile, os, sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.miss.app.release'

# Pull db directly (no force-stop)
tmp = os.path.join(tempfile.gettempdir(), 'check_rss2.db')
subprocess.run(f'"{ADB}" -s {HOST} shell su -c "cp /data/data/{PKG}/databases/legado.db /sdcard/legado_check2.db && chmod 666 /sdcard/legado_check2.db"', shell=True)
subprocess.run(f'"{ADB}" -s {HOST} pull /sdcard/legado_check2.db {tmp}', shell=True)

if not os.path.exists(tmp):
    print("DB pull failed")
    sys.exit(1)

conn = sqlite3.connect(tmp)
cur = conn.cursor()

# Check all AV聚合 sources
cur.execute("SELECT sourceUrl, sourceName, searchUrl FROM rssSources WHERE sourceGroup LIKE '%聚合%'")
rows = cur.fetchall()
print(f"Found {len(rows)} sources in AV聚合 group:")
for r in rows:
    name = r[1][:8] if r[1] else '?'
    has_search = 'YES' if r[2] and len(r[2]) > 10 else 'NO'
    search_preview = r[2][:50] if r[2] else 'EMPTY'
    print(f"  {name}: searchUrl={has_search} ({search_preview}...)")

conn.close()
