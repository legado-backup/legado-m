#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通过 run-as + base64 读取数据库，找出 articleStyle=2 的图片源
只输出技术字段（sourceUrl 的 hash、type、articleStyle、规则长度）
"""
import subprocess
import sys
import os
import base64
import hashlib
import sqlite3
import tempfile

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
DB_PATH = f"/data/data/{PKG}/databases/legado.db"

def read_db_via_base64():
    """通过 run-as + base64 读取数据库文件"""
    # 用 base64 编码避免二进制损坏
    cmd = [ADB, "-s", DEVICE, "shell", f"run-as {PKG} base64 {DB_PATH}"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not result.stdout:
        return None
    try:
        db_bytes = base64.b64decode(result.stdout)
        return db_bytes
    except Exception as e:
        print(f"base64 decode failed: {e}")
        return None

def main():
    print("[Step 1] 通过 run-as + base64 读取数据库...")
    db_bytes = read_db_via_base64()
    if db_bytes is None or len(db_bytes) == 0:
        print("ERROR: 读取数据库失败")
        return 1
    print(f"  -> 数据库大小: {len(db_bytes)} bytes")

    # 写到临时文件
    tmp_db = os.path.join(tempfile.gettempdir(), "legado_query_v3.db")
    with open(tmp_db, "wb") as f:
        f.write(db_bytes)
    print(f"  -> 临时文件: {tmp_db}")

    print("\n[Step 2] 查询 articleStyle=2 的图片源...")
    conn = sqlite3.connect(tmp_db)
    try:
        cursor = conn.cursor()
        # 查询 articleStyle=2 的源
        cursor.execute("""
            SELECT sourceUrl, type, articleStyle,
                   length(ruleContent), length(ruleImage),
                   enabled, lastUpdateTime
            FROM rss_sources
            WHERE articleStyle=2
            LIMIT 10
        """)
        rows = cursor.fetchall()
        print(f"  -> 查询到 {len(rows)} 个 articleStyle=2 源")
        for i, row in enumerate(rows):
            source_url = row[0] or ""
            url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
            print(f"  [{i+1}] url_hash={url_hash}, type={row[1]}, style={row[2]}, "
                  f"ruleContent_len={row[3] or 0}, ruleImage_len={row[4] or 0}, "
                  f"enabled={row[5]}, lastUpdate={row[6]}")

        # 也查询所有源的 type 分布
        print("\n[Step 3] 查询所有源的 type/articleStyle 分布...")
        cursor.execute("""
            SELECT type, articleStyle, count(*)
            FROM rss_sources
            GROUP BY type, articleStyle
        """)
        for row in cursor.fetchall():
            print(f"  type={row[0]}, articleStyle={row[1]}, count={row[2]}")

        # 查询 rss_articles 表中 type=1 的文章（图片类型）
        print("\n[Step 4] 查询 rss_articles 中 type=1 的文章数量...")
        try:
            cursor.execute("""
                SELECT count(*) FROM rss_articles WHERE type=1
            """)
            count = cursor.fetchone()[0]
            print(f"  type=1 文章数: {count}")

            if count > 0:
                # 查询第一条 type=1 文章的 origin（源URL）
                cursor.execute("""
                    SELECT origin, link, title FROM rss_articles WHERE type=1 LIMIT 3
                """)
                for row in cursor.fetchall():
                    origin = row[0] or ""
                    origin_hash = hashlib.md5(origin.encode()).hexdigest()[:8]
                    print(f"  origin_hash={origin_hash}, link_len={len(row[1] or '')}, title_len={len(row[2] or '')}")
        except Exception as e:
            print(f"  ERROR: {e}")

        # 查询 rss_read_record 表
        print("\n[Step 5] 查询 rss_read_record 表...")
        try:
            cursor.execute("""
                SELECT count(*) FROM rss_read_record
            """)
            count = cursor.fetchone()[0]
            print(f"  阅读记录数: {count}")
        except Exception as e:
            print(f"  ERROR: {e}")

    finally:
        conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
