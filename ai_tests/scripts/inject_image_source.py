#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修改数据库：把第一个源改成 articleStyle=2，并插入一条 rssArticles 记录
然后 push 回设备
"""
import subprocess
import sys
import os
import base64
import sqlite3
import tempfile
import time

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
DB_PATH = f"/data/data/{PKG}/databases/legado.db"

def read_file_via_base64(remote_path):
    cmd = [ADB, "-s", DEVICE, "shell", f"run-as {PKG} base64 {remote_path}"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not result.stdout:
        return None
    try:
        return base64.b64decode(result.stdout)
    except Exception:
        return None

def push_file_via_runas(local_path, remote_path):
    """通过 adb push + run-as cp 方式 push 文件"""
    # 1. 先 adb push 到 /data/local/tmp
    tmp_remote = "/data/local/tmp/legado_update.db"
    result = subprocess.run([ADB, "-s", DEVICE, "push", local_path, tmp_remote],
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  adb push 失败: {result.stderr}")
        return False

    # 2. run-as cp 到应用目录
    result = subprocess.run([ADB, "-s", DEVICE, "shell",
                           f"run-as {PKG} cp {tmp_remote} {remote_path}.new"],
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  run-as cp 失败: {result.stderr}")
        return False

    # 3. 替换原文件
    result = subprocess.run([ADB, "-s", DEVICE, "shell",
                           f"run-as {PKG} mv {remote_path}.new {remote_path}"],
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  mv 失败: {result.stderr}")
        return False

    # 4. 清理临时文件
    subprocess.run([ADB, "-s", DEVICE, "shell", f"rm {tmp_remote}"], capture_output=True)

    return True

def main():
    tmp_dir = tempfile.gettempdir()

    print("[Step 1] 读取数据库...")
    db_data = read_file_via_base64(DB_PATH)
    if db_data is None:
        print("ERROR: 读取数据库失败")
        return 1
    local_db = os.path.join(tmp_dir, "legado_modify.db")
    with open(local_db, "wb") as f:
        f.write(db_data)
    print(f"  -> {local_db} ({len(db_data)} bytes)")

    # 同时读取 WAL 文件
    wal_data = read_file_via_base64(DB_PATH + "-wal")
    if wal_data:
        with open(local_db + "-wal", "wb") as f:
            f.write(wal_data)
        print(f"  -> {local_db}-wal ({len(wal_data)} bytes)")

    shm_data = read_file_via_base64(DB_PATH + "-shm")
    if shm_data:
        with open(local_db + "-shm", "wb") as f:
            f.write(shm_data)
        print(f"  -> {local_db}-shm ({len(shm_data)} bytes)")

    print("\n[Step 2] 修改数据库...")
    conn = sqlite3.connect(local_db)
    try:
        cursor = conn.cursor()
        # checkpoint WAL
        cursor.execute("PRAGMA wal_checkpoint(FULL)")

        # 查询当前所有源
        cursor.execute("SELECT sourceUrl, sourceName, type, articleStyle FROM rssSources LIMIT 5")
        sources = cursor.fetchall()
        if not sources:
            print("  ERROR: 没有订阅源")
            return 1

        print(f"  当前源数量: {len(sources)}")
        # 选第一个源改成 articleStyle=2
        first_source_url = sources[0][0]
        first_source_name = sources[0][1]
        print(f"  修改第一个源: sourceName_len={len(first_source_name or '')}, articleStyle=0→2")

        # 更新 articleStyle=2
        cursor.execute("UPDATE rssSources SET articleStyle=2 WHERE sourceUrl=?", (first_source_url,))

        # 插入一条测试文章（type=1 图片类型）
        test_link = "https://example.com/test-image-article"
        test_title = "测试图片文章"
        test_origin = first_source_url
        cursor.execute("""
            INSERT OR REPLACE INTO rssArticles (origin, sort, link, title, type, "order", "group", "read")
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """, (test_origin, "test_sort", test_link, test_title, int(time.time()), "默认分组", 0))

        conn.commit()
        print(f"  已修改 articleStyle=2 并插入测试文章")

        # 验证
        cursor.execute("SELECT count(*) FROM rssSources WHERE articleStyle=2")
        count = cursor.fetchone()[0]
        print(f"  验证: articleStyle=2 源数量={count}")

        cursor.execute("SELECT count(*) FROM rssArticles WHERE type=1")
        count = cursor.fetchone()[0]
        print(f"  验证: type=1 文章数量={count}")

    finally:
        conn.close()

    # 删除 WAL 和 SHM 文件（让 SQLite 重新创建）
    for ext in ["-wal", "-shm"]:
        path = local_db + ext
        if os.path.exists(path):
            os.remove(path)
            print(f"  删除 {ext} 文件")

    print("\n[Step 3] 停止应用...")
    subprocess.run([ADB, "-s", DEVICE, "shell", f"am force-stop {PKG}"], capture_output=True)
    time.sleep(2)

    print("\n[Step 4] push 数据库回设备...")
    success = push_file_via_runas(local_db, DB_PATH)
    if not success:
        print("ERROR: push 失败")
        return 1
    print("  -> push 成功")

    # 验证 push 成功
    print("\n[Step 5] 验证 push...")
    db_data2 = read_file_via_base64(DB_PATH)
    if db_data2:
        print(f"  数据库大小: {len(db_data2)} bytes")
        # 重新查询验证
        verify_db = os.path.join(tmp_dir, "legado_verify.db")
        with open(verify_db, "wb") as f:
            f.write(db_data2)
        conn = sqlite3.connect(verify_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM rssSources WHERE articleStyle=2")
            count = cursor.fetchone()[0]
            print(f"  验证: articleStyle=2 源数量={count}")
            cursor.execute("SELECT count(*) FROM rssArticles WHERE type=1")
            count = cursor.fetchone()[0]
            print(f"  验证: type=1 文章数量={count}")
        finally:
            conn.close()

    print("\n[Step 6] 启动应用...")
    subprocess.run([ADB, "-s", DEVICE, "shell", f"monkey -p {PKG} -c android.intent.category.LAUNCHER 1"],
                  capture_output=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
