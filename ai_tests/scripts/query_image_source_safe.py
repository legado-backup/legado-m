#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全查询图片类型订阅源（只输出技术字段，过滤业务字段）
避免触发违禁词
"""
import subprocess
import sys
import os
import sqlite3
import tempfile

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
DEVICE = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
DB_REMOTE = f"/data/data/{PKG}/databases/legado.db"


def pull_db():
    """pull db 到临时文件"""
    tmp = os.path.join(tempfile.gettempdir(), "legado_query.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    subprocess.run([ADB, "-s", DEVICE, "shell", "run-as", PKG, "cat", DB_REMOTE],
                   stdout=open(tmp, "wb"),
                   stderr=subprocess.DEVNULL,
                   timeout=30)
    # 同时 pull wal
    subprocess.run([ADB, "-s", DEVICE, "shell", "run-as", PKG, "cat", DB_REMOTE + "-wal"],
                   stdout=open(tmp + "-wal", "wb"),
                   stderr=subprocess.DEVNULL,
                   timeout=10)
    subprocess.run([ADB, "-s", DEVICE, "shell", "run-as", PKG, "cat", DB_REMOTE + "-shm"],
                   stdout=open(tmp + "-shm", "wb"),
                   stderr=subprocess.DEVNULL,
                   timeout=10)
    return tmp


def query_safe(db_path):
    """只查询技术字段"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # rss_source 表中的图片类型订阅源（articleStyle=2）
    print("=== rss_source 表中所有源（只输出技术字段）===")
    cur.execute("SELECT id, type, articleStyle, enabled, customOrder FROM rss_source ORDER BY id")
    rows = cur.fetchall()
    print(f"总源数: {len(rows)}")
    img_sources = []
    for r in rows:
        sid, stype, astyle, enabled, order = r
        marker = ""
        if astyle == 2:
            marker = " [图片类型]"
            img_sources.append(sid)
        print(f"  id={sid} type={stype} articleStyle={astyle} enabled={enabled} order={order}{marker}")
    print(f"\n图片类型源数: {len(img_sources)}")
    print(f"图片类型源ID列表: {img_sources}")
    conn.close()


if __name__ == "__main__":
    print(f"=== Device: {DEVICE} ===")
    db = pull_db()
    if not os.path.exists(db) or os.path.getsize(db) == 0:
        print("[ERROR] pull db failed")
        sys.exit(1)
    print(f"DB size: {os.path.getsize(db)} bytes")
    query_safe(db)
