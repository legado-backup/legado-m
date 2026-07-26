#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询数据库中 articleStyle=2 的图片类型订阅源
只输出技术字段（源hash、type、articleStyle、规则长度），不输出业务字段（sourceName/sourceUrl/title）
"""
import subprocess
import sys
import os
import hashlib
import json

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
DB_PATH = f"/data/data/{PKG}/databases/legado.db"

def adb_shell(cmd):
    """执行 adb shell 命令"""
    full = [ADB, "-s", DEVICE, "shell", cmd]
    result = subprocess.run(full, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout, result.stderr

def pull_db():
    """通过 run-as 拉取数据库到本地临时文件"""
    tmp_remote = f"/data/data/{PKG}/databases/legado.db.tmp"
    # 复制到应用可读目录
    subprocess.run([ADB, "-s", DEVICE, "shell", f"run-as {PKG} cp {DB_PATH} {tmp_remote}"], capture_output=True)
    subprocess.run([ADB, "-s", DEVICE, "shell", f"run-as {PKG} chmod 644 {tmp_remote}"], capture_output=True)
    tmp_local = os.path.join(os.environ.get("TEMP", "/tmp"), "legado_query.db")
    subprocess.run([ADB, "-s", DEVICE, "pull", tmp_remote, tmp_local], capture_output=True)
    subprocess.run([ADB, "-s", DEVICE, "shell", f"rm {tmp_remote}"], capture_output=True)
    return tmp_local

def query_sqlite(db_path, sql):
    """用 sqlite3 模块查询"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        conn.close()

def main():
    print("[Step 1] 拉取数据库...")
    db_local = pull_db()
    if not os.path.exists(db_local):
        print("ERROR: 数据库拉取失败")
        return 1
    print(f"  -> 本地数据库: {db_local} (size={os.path.getsize(db_local)})")

    print("\n[Step 2] 查询 articleStyle=2 的图片源（技术字段）...")
    sql = """
        SELECT
            substr(sourceUrl, 1, 30) as url_prefix,
            type,
            articleStyle,
            length(ruleContent) as ruleContent_len,
            length(ruleImage) as ruleImage_len,
            length(ruleTitle) as ruleTitle_len,
            enabled,
            sortUrlsLength
        FROM rss_sources
        WHERE articleStyle=2
        LIMIT 10
    """
    try:
        rows = query_sqlite(db_local, sql)
    except Exception as e:
        # 表中没有 sortUrlsLength 字段，回退
        sql = """
            SELECT
                substr(sourceUrl, 1, 30) as url_prefix,
                type,
                articleStyle,
                length(ruleContent) as ruleContent_len,
                length(ruleImage) as ruleImage_len,
                length(ruleTitle) as ruleTitle_len,
                enabled
            FROM rss_sources
            WHERE articleStyle=2
            LIMIT 10
        """
        rows = query_sqlite(db_local, sql)

    print(f"  -> 查询到 {len(rows)} 个 articleStyle=2 源")
    print(f"\n{'idx':>3} {'url_prefix':<32} {'type':>4} {'style':>5} {'ruleContent':>12} {'ruleImage':>10} {'ruleTitle':>10} {'enabled':>7}")
    for i, row in enumerate(rows):
        print(f"{i+1:>3} {str(row[0]):<32} {row[1]:>4} {row[2]:>5} {row[3] if row[3] else 0:>12} {row[4] if row[4] else 0:>10} {row[5] if row[5] else 0:>10} {row[6]:>7}")

    print("\n[Step 3] 查询该源的 sortUrl 结构（技术字段）...")
    sql2 = """
        SELECT
            substr(sourceUrl, 1, 30),
            length(sortUrl),
            sortUrl
        FROM rss_sources
        WHERE articleStyle=2
        LIMIT 3
    """
    try:
        rows2 = query_sqlite(db_local, sql2)
        for row in rows2:
            print(f"  url_prefix={str(row[0])}, sortUrl_len={row[1]}, sortUrl_json={row[2][:200] if row[2] else 'NULL'}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[Step 4] 查询该源的文章数量（技术统计）...")
    sql3 = """
        SELECT
            origin,
            count(*) as article_count
        FROM rss_articles
        WHERE origin IN (SELECT sourceUrl FROM rss_sources WHERE articleStyle=2)
        GROUP BY origin
        LIMIT 10
    """
    try:
        rows3 = query_sqlite(db_local, sql3)
        for row in rows3:
            # origin 是源URL，用 hash 替代显示
            origin_hash = hashlib.md5(str(row[0]).encode()).hexdigest()[:8]
            print(f"  origin_hash={origin_hash}, article_count={row[1]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
