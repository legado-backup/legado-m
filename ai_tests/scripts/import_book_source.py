#!/usr/bin/env python3
"""import_book_source.py — 导入书源到legado.db

从JSON文件导入书源到MEmu模拟器的legado.db，用于校验功能测试。
只导入少量书源（默认10个），避免校验时间过长。

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_book_source.py
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import os
from pathlib import Path

ADB_PATH = "D:/Program Files/Microvirt/MEmu/adb.exe"
MEMU_ADB_HOST = "127.0.0.1:21503"
PACKAGE = "io.legado.app.debug"
DB_DEVICE_PATH = f"/data/data/{PACKAGE}/databases/legado.db"

# 书源JSON文件目录
BOOK_SOURCE_DIR = "f:/myself/github/WeAgentChat/temp/legado/temp/output/book/groups"

# book_sources表的所有列（按PRAGMA顺序）
BOOK_SOURCE_COLUMNS = [
    "bookSourceUrl", "bookSourceName", "bookSourceGroup", "bookSourceType",
    "bookUrlPattern", "customOrder", "enabled", "enabledExplore", "jsLib",
    "enabledCookieJar", "concurrentRate", "header", "loginUrl", "loginUi",
    "loginCheckJs", "coverDecodeJs", "bookSourceComment", "variableComment",
    "lastUpdateTime", "respondTime", "weight", "exploreUrl", "exploreScreen",
    "ruleExplore", "searchUrl", "ruleSearch", "ruleBookInfo", "ruleToc",
    "ruleContent", "ruleReview", "eventListener", "customButton", "lastHost"
]

# 默认值（JSON中可能缺少的字段）
DEFAULT_VALUES = {
    "bookSourceType": 0,
    "customOrder": 0,
    "enabled": 1,
    "enabledExplore": 1,
    "enabledCookieJar": 0,
    "lastUpdateTime": 0,
    "respondTime": 180000,
    "weight": 0,
    "eventListener": 0,
    "customButton": 0,
    "lastHost": None,
}


def run_adb(cmd, timeout=30):
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def pull_db(tmp_path):
    print("\n--- Pull legado.db ---")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db'")
    run_adb(f"shell su -c 'chmod 666 /sdcard/legado.db'")
    result = run_adb(f"pull /sdcard/legado.db {tmp_path}")
    if result.returncode != 0:
        print(f"Pull失败: {result.stderr}")
        return False
    print(f"DB pulled to {tmp_path}")
    return True


def push_db(tmp_path):
    print("\n--- Push legado.db ---")
    run_adb(f"push {tmp_path} /sdcard/legado.db")
    run_adb(f"shell su -c 'cp /sdcard/legado.db {DB_DEVICE_PATH}'")
    run_adb(f"shell su -c 'chmod 660 {DB_DEVICE_PATH}'")
    # 删除WAL/SHM避免覆盖
    run_adb(f"shell su -c 'rm -f {DB_DEVICE_PATH}-wal {DB_DEVICE_PATH}-shm'")
    print("DB pushed & WAL/SHM cleared")


def load_book_sources(max_count=10):
    """从多个JSON文件加载书源，返回列表"""
    sources = []
    # 选择几个常规文件
    target_files = ["小说.json", "常用.json", "笔趣阁.json", "网络.json"]
    for fname in target_files:
        fpath = os.path.join(BOOK_SOURCE_DIR, fname)
        if not os.path.exists(fpath):
            continue
        try:
            data = json.load(open(fpath, encoding="utf-8"))
            if isinstance(data, list):
                for s in data:
                    if isinstance(s, dict) and s.get("bookSourceUrl"):
                        sources.append(s)
                        if len(sources) >= max_count:
                            return sources
            elif isinstance(data, dict) and data.get("bookSourceUrl"):
                sources.append(data)
                if len(sources) >= max_count:
                    return sources
        except Exception as e:
            print(f"读取{fname}失败: {e}")
    return sources


def insert_sources(db_path, sources):
    """插入书源到数据库"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    inserted = 0
    for s in sources:
        # 构建列值映射
        values = {}
        for col in BOOK_SOURCE_COLUMNS:
            if col in s:
                val = s[col]
                # dict/list序列化为JSON字符串（如searchUrl可能是dict）
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)
                values[col] = val
            elif col in DEFAULT_VALUES:
                values[col] = DEFAULT_VALUES[col]
            else:
                values[col] = None
        # INSERT OR REPLACE
        cols_str = ", ".join(BOOK_SOURCE_COLUMNS)
        placeholders = ", ".join(["?"] * len(BOOK_SOURCE_COLUMNS))
        sql = f"INSERT OR REPLACE INTO book_sources ({cols_str}) VALUES ({placeholders})"
        try:
            c.execute(sql, [values[col] for col in BOOK_SOURCE_COLUMNS])
            inserted += 1
        except Exception as e:
            print(f"插入失败: {e}")
    conn.commit()
    conn.close()
    print(f"成功插入 {inserted} 个书源")
    return inserted


def main():
    print("=== 导入书源到legado.db ===")

    # 1. 加载书源
    print("\n--- 加载书源JSON ---")
    sources = load_book_sources(max_count=10)
    print(f"加载到 {len(sources)} 个书源")

    if not sources:
        print("没有可导入的书源")
        return

    # 2. 停止App
    print("\n--- 停止App ---")
    run_adb(f"shell am force-stop {PACKAGE}")
    import time; time.sleep(2)

    # 3. Pull DB
    tmp_path = tempfile.mktemp(suffix=".db")
    if not pull_db(tmp_path):
        return

    # 4. 插入书源
    print("\n--- 插入书源到DB ---")
    insert_sources(tmp_path, sources)

    # 5. Push DB回设备
    push_db(tmp_path)

    # 6. 清理临时文件
    os.unlink(tmp_path)

    print("\n=== 导入完成 ===")
    print("请启动App验证书源显示")


if __name__ == "__main__":
    main()
