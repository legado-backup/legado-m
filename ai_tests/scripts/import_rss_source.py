#!/usr/bin/env python3
r"""import_rss_source.py — 导入订阅源到legado.db

固定测试流程步骤2：从JSON文件导入订阅源到MEmu模拟器的legado.db

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_rss_source.py <json_path>

示例：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_rss_source.py .trae/skills/legado-source-creator/output/rss/rssSource_xxx.json

原理：
    1. ADB pull legado.db 到本地临时文件
    2. Python sqlite3 读取 JSON → DELETE 旧记录 → INSERT 新记录
    3. ADB push 回设备
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
    print(f"  >>> {full_cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def pull_db(tmp_path):
    """从设备pull legado.db"""
    print("\n--- Pull legado.db ---")
    # 确保 databases 目录存在
    run_adb(f"shell su -c 'mkdir -p {DB_DIR}'")
    # 复制 db 到可访问路径
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db'")
    run_adb(f"shell su -c 'chmod 666 /sdcard/legado.db'")
    # pull
    result = run_adb(f"pull /sdcard/legado.db {tmp_path}")
    if result.returncode == 0:
        print(f"✅ DB pulled to {tmp_path}")
        return True
    else:
        print(f"❌ Pull失败: {result.stderr}")
        return False


def push_db(tmp_path):
    """Push legado.db回设备"""
    print("\n--- Push legado.db ---")
    # push
    result = run_adb(f"push {tmp_path} /sdcard/legado.db")
    if result.returncode != 0:
        print(f"❌ Push失败: {result.stderr}")
        return False
    # 复制回原位置
    run_adb(f"shell su -c 'cp /sdcard/legado.db {DB_DEVICE_PATH}'")
    run_adb(f"shell su -c 'chmod 660 {DB_DEVICE_PATH}'")
    print(f"✅ DB pushed back")
    return True


def import_rss(json_path, db_path):
    """导入订阅源到数据库"""
    print(f"\n--- 导入订阅源: {json_path} ---")

    # 读取JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    if not isinstance(sources, list):
        sources = [sources]

    print(f"  JSON包含 {len(sources)} 个订阅源")

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取 rssSources 表结构
    cursor.execute("PRAGMA table_info(rssSources)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"  rssSources 表列: {len(columns)} 列")

    imported = 0
    for source in sources:
        source_name = source.get('sourceName', 'unknown')
        source_url = source.get('sourceUrl', '')

        # 删除同 sourceUrl 的旧记录
        cursor.execute("DELETE FROM rssSources WHERE sourceUrl = ?", (source_url,))

        # 构建INSERT（只插入表中存在的列）
        valid_keys = [k for k in source.keys() if k in columns]
        placeholders = ', '.join(['?'] * len(valid_keys))
        col_names = ', '.join(valid_keys)
        values = [str(source[k]) if not isinstance(source[k], (int, float, bool)) else source[k]
                  for k in valid_keys]

        cursor.execute(
            f"INSERT INTO rssSources ({col_names}) VALUES ({placeholders})",
            values
        )
        imported += 1
        print(f"  ✅ 导入: {source_name} | {source_url}")

    conn.commit()
    conn.close()
    print(f"  共导入 {imported} 个订阅源")
    return imported


def main():
    if len(sys.argv) < 2:
        print("用法: python import_rss_source.py <json_path>")
        print("示例: python import_rss_source.py .trae/skills/legado-source-creator/output/rss/rssSource_xxx.json")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"❌ JSON文件不存在: {json_path}")
        sys.exit(1)

    print("=" * 60)
    print("Legado 订阅源导入工具")
    print("=" * 60)

    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        # 步骤1: Pull DB
        if not pull_db(tmp_db_path):
            sys.exit(1)

        # 步骤2: 导入订阅源
        count = import_rss(json_path, tmp_db_path)
        if count == 0:
            print("❌ 未导入任何订阅源")
            sys.exit(1)

        # 步骤3: Push DB
        if not push_db(tmp_db_path):
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"✅ 订阅源导入完成: {count} 个订阅源")
        print("=" * 60)

    finally:
        # 清理临时文件
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


if __name__ == "__main__":
    main()
