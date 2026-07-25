#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询 rssSources 表结构"""
import sqlite3
import tempfile
import subprocess
import os

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
HOST = "127.0.0.1:21513"
PKG = "io.legado.miss.app.release"

def run_adb(cmd):
    full = f'"{ADB}" -s {HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    return r

# Pull DB
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
    tmp_path = tmp.name

run_adb(f"shell su -c 'cp /data/data/{PKG}/databases/legado.db /sdcard/legado.db; chmod 666 /sdcard/legado.db'")
run_adb(f"pull /sdcard/legado.db {tmp_path}")

conn = sqlite3.connect(tmp_path)
cursor = conn.cursor()

# 查询 rssSources 表的列信息
cursor.execute("PRAGMA table_info(rssSources)")
columns = cursor.fetchall()
print(f"rssSources 表共 {len(columns)} 列:")
print("=" * 80)
print(f"{'cid':<4} {'name':<25} {'type':<15} {'notnull':<8} {'default':<20}")
print("-" * 80)
for col in columns:
    cid, name, ctype, notnull, default, pk = col
    print(f"{cid:<4} {name:<25} {ctype:<15} {notnull:<8} {str(default):<20}")

# 查询 NOT NULL 且无默认值的字段
print("\n" + "=" * 80)
print("NOT NULL 且无默认值的字段（必须填充）:")
print("=" * 80)
cursor.execute("PRAGMA table_info(rssSources)")
for col in cursor.fetchall():
    cid, name, ctype, notnull, default, pk = col
    if notnull and default is None and pk == 0:
        print(f"  - {name} ({ctype})")

# 查询已有的源记录（看现有源的字段填充模式）
print("\n" + "=" * 80)
print("已有源记录的字段填充模式（取1条）:")
print("=" * 80)
cursor.execute("SELECT * FROM rssSources LIMIT 1")
row = cursor.fetchone()
if row:
    col_names = [d[0] for d in cursor.description]
    for i, val in enumerate(row):
        val_str = str(val)
        if len(val_str) > 60:
            val_str = val_str[:60] + "..."
        print(f"  {col_names[i]}: {val_str}")

conn.close()
os.unlink(tmp_path)
