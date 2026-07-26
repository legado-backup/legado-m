#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询数据库表结构 + 读取 WAL 文件
"""
import subprocess
import sys
import os
import base64
import hashlib
import sqlite3
import tempfile

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = os.environ.get("DEVICE", "127.0.0.1:21503")
PKG = "io.legado.miss.app.debug"
DB_PATH = f"/data/data/{PKG}/databases/legado.db"

def read_file_via_base64(remote_path):
    """通过 run-as + base64 读取文件"""
    cmd = [ADB, "-s", DEVICE, "shell", f"run-as {PKG} base64 {remote_path}"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not result.stdout:
        return None
    try:
        return base64.b64decode(result.stdout)
    except Exception:
        return None

def main():
    tmp_dir = tempfile.gettempdir()

    print("[Step 1] 读取主数据库 + WAL + SHM 文件...")
    files_to_read = [
        (DB_PATH, "legado.db"),
        (DB_PATH + "-wal", "legado.db-wal"),
        (DB_PATH + "-shm", "legado.db-shm"),
    ]
    for remote, local_name in files_to_read:
        local_path = os.path.join(tmp_dir, local_name)
        data = read_file_via_base64(remote)
        if data is None:
            print(f"  {local_name}: 读取失败或不存在")
            continue
        with open(local_path, "wb") as f:
            f.write(data)
        print(f"  {local_name}: {len(data)} bytes")

    db_path = os.path.join(tmp_dir, "legado.db")
    if not os.path.exists(db_path):
        print("ERROR: 主数据库不存在")
        return 1

    print(f"\n[Step 2] 打开数据库（含WAL）查询所有表...")
    conn = sqlite3.connect(db_path)
    try:
        # 先 checkpoint WAL
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA wal_checkpoint(FULL)")
        except:
            pass

        # 查询所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  表数量: {len(tables)}")
        for t in tables:
            print(f"    - {t[0]}")

        # 查询 rssSources 表
        print("\n[Step 3] 查询 rssSources 表...")
        try:
            cursor.execute("SELECT count(*) FROM rssSources")
            count = cursor.fetchone()[0]
            print(f"  rssSources 记录数: {count}")

            if count > 0:
                # 查询 articleStyle=2 的源
                cursor.execute("""
                    SELECT sourceUrl, type, articleStyle,
                           length(ruleContent), length(ruleImage),
                           enabled
                    FROM rssSources
                    WHERE articleStyle=2
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                print(f"  articleStyle=2 源数量: {len(rows)}")
                for i, row in enumerate(rows):
                    source_url = row[0] or ""
                    url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
                    print(f"    [{i+1}] url_hash={url_hash}, type={row[1]}, style={row[2]}, "
                          f"ruleContent_len={row[3] or 0}, ruleImage_len={row[4] or 0}, "
                          f"enabled={row[5]}")

                # 查询所有源的 type/articleStyle 分布
                print("\n  type/articleStyle 分布:")
                cursor.execute("""
                    SELECT type, articleStyle, count(*)
                    FROM rssSources
                    GROUP BY type, articleStyle
                """)
                for row in cursor.fetchall():
                    print(f"    type={row[0]}, articleStyle={row[1]}, count={row[2]}")

                # 查询第一个 articleStyle=2 源的完整信息（用于 am start）
                print("\n  第一个 articleStyle=2 源的完整信息:")
                cursor.execute("""
                    SELECT sourceUrl, sortUrl
                    FROM rssSources
                    WHERE articleStyle=2
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    print(f"    sourceUrl_len={len(row[0] or '')}")
                    print(f"    sortUrl_len={len(row[1] or '')}")
                    # 输出 sourceUrl 用于 am start（不显示，存到文件）
                    with open(os.path.join(tmp_dir, "image_source_url.txt"), "w") as f:
                        f.write(row[0] or "")
                        if row[1]:
                            f.write(f"\n{row[1]}")
                    print(f"    sourceUrl 已写入: {tmp_dir}\\image_source_url.txt")
        except Exception as e:
            print(f"  ERROR: {e}")

        # 查询 rssArticles 表
        print("\n[Step 4] 查询 rssArticles 表...")
        try:
            cursor.execute("SELECT count(*) FROM rssArticles")
            count = cursor.fetchone()[0]
            print(f"  rssArticles 记录数: {count}")

            if count > 0:
                # 查询 type 分布
                cursor.execute("SELECT type, count(*) FROM rssArticles GROUP BY type")
                for row in cursor.fetchall():
                    print(f"    type={row[0]}, count={row[1]}")

                # 查询第一条 type=1 文章
                cursor.execute("""
                    SELECT origin, link, type FROM rssArticles WHERE type=1 LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    origin = row[0] or ""
                    origin_hash = hashlib.md5(origin.encode()).hexdigest()[:8]
                    print(f"  第一条 type=1 文章: origin_hash={origin_hash}, link_len={len(row[1] or '')}")
        except Exception as e:
            print(f"  ERROR: {e}")

    finally:
        conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
