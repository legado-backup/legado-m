#!/usr/bin/env python3
r"""export_rss_sources.py — 从 legado.db 导出全部订阅源到JSON

固定测试流程辅助脚本：从MEmu模拟器的legado.db导出全部订阅源为JSON文件

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/export_rss_sources.py [output_path]

示例：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/export_rss_sources.py
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/export_rss_sources.py output/rss/exported.json

原理：
    1. ADB pull legado.db 到本地临时文件
    2. Python sqlite3 读取 rssSources 表全部记录
    3. 转换为 JSON 数组输出（保留所有字段）
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

# legado.db 路径（设备端）
DB_DEVICE_PATH = f"/data/data/{PACKAGE}/databases/legado.db"
DB_DIR = f"/data/data/{PACKAGE}/databases/"


def run_adb(cmd, timeout=30):
    """执行ADB命令"""
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def pull_db(tmp_path):
    """从设备pull legado.db（含WAL/SHM文件）"""
    print("--- Pull legado.db ---")
    # force-stop App（避免 WAL 问题）
    run_adb(f"shell am force-stop {PACKAGE}")
    import time
    time.sleep(1)

    # 确保 databases 目录存在
    run_adb(f"shell su -c 'mkdir -p {DB_DIR}'")
    # 复制 db 及 WAL/SHM 到可访问路径
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db'")
    run_adb(f"shell su -c 'chmod 666 /sdcard/legado.db'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-wal /sdcard/legado.db-wal 2>/dev/null; chmod 666 /sdcard/legado.db-wal 2>/dev/null; true'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-shm /sdcard/legado.db-shm 2>/dev/null; chmod 666 /sdcard/legado.db-shm 2>/dev/null; true'")
    # pull 主DB
    result = run_adb(f"pull /sdcard/legado.db {tmp_path}")
    if result.returncode != 0:
        print(f"Pull主DB失败: {result.stderr}")
        return False
    # pull WAL/SHM
    run_adb(f"pull /sdcard/legado.db-wal {tmp_path}-wal")
    run_adb(f"pull /sdcard/legado.db-shm {tmp_path}-shm")
    # 删除本地WAL/SHM文件，避免sqlite3打开时报malformed
    for ext in ['-wal', '-shm']:
        wal_path = f"{tmp_path}{ext}"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
    print(f"DB pulled to {tmp_path}")
    return True


def export_rss(db_path):
    """从数据库导出全部订阅源"""
    print("--- Export rssSources ---")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # checkpoint WAL
    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # 获取 rssSources 表结构
    cursor.execute("PRAGMA table_info(rssSources)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"rssSources 表列: {len(columns)} 列")

    # 查询全部记录
    cursor.execute(f"SELECT {', '.join(columns)} FROM rssSources")
    rows = cursor.fetchall()
    print(f"总订阅源数: {len(rows)}")

    # 转换为 dict 列表
    sources = []
    for row in rows:
        source = {col: row[col] for col in columns if row[col] is not None}
        sources.append(source)

    conn.close()
    return sources


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else 'output/rss/exported_from_emulator.json'

    print("=" * 60)
    print("Legado 订阅源导出工具")
    print("=" * 60)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        # 步骤1: Pull DB
        if not pull_db(tmp_db_path):
            sys.exit(1)

        # 步骤2: 导出订阅源
        sources = export_rss(tmp_db_path)
        if not sources:
            print("未导出任何订阅源")
            sys.exit(1)

        # 步骤3: 写入JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sources, f, ensure_ascii=False, indent=2)
        print(f"\n导出完成: {len(sources)} 个订阅源 → {output_path}")

    finally:
        # 清理临时文件
        for suffix in ['', '-wal', '-shm']:
            path = tmp_db_path + suffix
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    main()
