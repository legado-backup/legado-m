#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证模拟器DB中的订阅源数量"""
import sqlite3, tempfile, subprocess, os

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
HOST = "127.0.0.1:21513"
PKG = "io.legado.miss.app.debug"

# Pull DB
tmp = os.path.join(tempfile.gettempdir(), 'verify_db.db')
if os.path.exists(tmp):
    os.remove(tmp)

subprocess.run([ADB, '-s', HOST, 'shell', 'su', '-c', f'cp /data/data/{PKG}/databases/legado.db /sdcard/verify.db'], capture_output=True)
subprocess.run([ADB, '-s', HOST, 'shell', 'su', '-c', 'chmod 666 /sdcard/verify.db'], capture_output=True)
r = subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/verify.db', tmp], capture_output=True, text=True)
print(f"Pull: {r.stdout.strip()}")

conn = sqlite3.connect(tmp)
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM rssSources')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=0')
web = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=1')
img = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=2')
vid = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE enabled=1')
en = c.fetchone()[0]
print(f'Total: {total}, type0_web: {web}, type1_image: {img}, type2_video: {vid}, enabled: {en}')
conn.close()
