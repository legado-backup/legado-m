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

sys.stdout.reconfigure(encoding='utf-8')

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
    """从设备pull legado.db（含WAL/SHM文件）

    重要：Room使用WAL模式，必须同时pull .db-wal/.db-shm文件。
    如果只pull主.db文件，WAL中的旧状态会在App启动时覆盖导入的新数据。
    详见 project_memory.md "Room WAL模式DB导入" 教训。
    """
    print("\n--- Pull legado.db (含WAL/SHM) ---")
    # 确保 databases 目录存在
    run_adb(f"shell su -c 'mkdir -p {DB_DIR}'")
    # 复制 db 及 WAL/SHM 到可访问路径
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db'")
    run_adb(f"shell su -c 'chmod 666 /sdcard/legado.db'")
    # WAL/SHM文件可能不存在（已checkpoint时），忽略错误
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-wal /sdcard/legado.db-wal 2>/dev/null; chmod 666 /sdcard/legado.db-wal 2>/dev/null; true'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-shm /sdcard/legado.db-shm 2>/dev/null; chmod 666 /sdcard/legado.db-shm 2>/dev/null; true'")
    # pull 主DB
    result = run_adb(f"pull /sdcard/legado.db {tmp_path}")
    if result.returncode != 0:
        print(f"❌ Pull主DB失败: {result.stderr}")
        return False
    # pull WAL/SHM（可能不存在，忽略失败）
    run_adb(f"pull /sdcard/legado.db-wal {tmp_path}-wal")
    run_adb(f"pull /sdcard/legado.db-shm {tmp_path}-shm")
    # 删除本地WAL/SHM文件，避免sqlite3打开时报"database disk image is malformed"
    # 原因：pull的WAL文件可能与主DB不匹配（App被force-stop时WAL可能处于不一致状态）
    # 安全性：App被force-stop后Room已将已提交事务checkpoint到主DB，WAL中数据已包含在主DB中
    for ext in ['-wal', '-shm']:
        wal_path = f"{tmp_path}{ext}"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
            print(f"  清理本地{ext}文件（避免malformed）")
    print(f"✅ DB pulled to {tmp_path} (主DB，WAL/SHM已清理避免malformed)")
    return True


def push_db(tmp_path):
    """Push legado.db回设备，并删除设备端WAL/SHM文件

    重要：必须删除设备端的.db-wal/.db-shm文件，否则App启动时Room会加载
    旧WAL数据覆盖新导入的数据。
    """
    print("\n--- Push legado.db (清理WAL/SHM) ---")
    # push
    result = run_adb(f"push {tmp_path} /sdcard/legado.db")
    if result.returncode != 0:
        print(f"❌ Push失败: {result.stderr}")
        return False
    # 复制回原位置
    run_adb(f"shell su -c 'cp /sdcard/legado.db {DB_DEVICE_PATH}'")
    run_adb(f"shell su -c 'chmod 660 {DB_DEVICE_PATH}'")
    # 删除设备端WAL/SHM文件（关键！否则旧WAL覆盖新数据）
    run_adb(f"shell su -c 'rm -f {DB_DEVICE_PATH}-wal {DB_DEVICE_PATH}-shm'")
    print(f"✅ DB pushed back (WAL/SHM已清理)")
    return True


def import_rss(json_path, db_path):
    """导入订阅源到数据库"""
    print(f"\n--- 导入订阅源: {json_path} ---")

    # 读取JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 兼容两种格式：
    # 1. 纯列表 [...]
    # 2. 字典 {"version":..., "sources":[...]}
    if isinstance(data, dict):
        if 'sources' in data:
            sources = data['sources']
            meta = {k: v for k, v in data.items() if k != 'sources'}
            print(f"  JSON元信息: {meta}")
        else:
            sources = [data]
    elif isinstance(data, list):
        sources = data
    else:
        print(f"❌ 不支持的JSON格式: {type(data)}")
        return 0

    print(f"  JSON包含 {len(sources)} 个订阅源")

    # 连接数据库（WAL文件在同目录时sqlite3会自动加载）
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # 关键：checkpoint WAL合并到主DB，避免WAL旧状态覆盖新数据
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        checkpoint_result = cursor.fetchone()
        print(f"  WAL checkpoint: {checkpoint_result}")

        # 获取 rssSources 表结构
        cursor.execute("PRAGMA table_info(rssSources)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"  rssSources 表列: {len(columns)} 列")

        imported = 0
        skipped = 0
        for source in sources:
            if not isinstance(source, dict):
                skipped += 1
                continue
            source_name = source.get('sourceName', 'unknown')
            source_url = source.get('sourceUrl', '')

            # 删除同 sourceUrl 的旧记录
            cursor.execute("DELETE FROM rssSources WHERE sourceUrl = ?", (source_url,))

            # 构建INSERT（只插入表中存在的列）
            valid_keys = [k for k in source.keys() if k in columns]
            if not valid_keys:
                print(f"  ⚠️ 跳过: {source_name}（无匹配列）")
                skipped += 1
                continue
            placeholders = ', '.join(['?'] * len(valid_keys))
            col_names = ', '.join(valid_keys)
            values = [str(source[k]) if not isinstance(source[k], (int, float, bool)) else source[k]
                      for k in valid_keys]

            cursor.execute(
                f"INSERT INTO rssSources ({col_names}) VALUES ({placeholders})",
                values
            )
            imported += 1

        conn.commit()

        # 最终checkpoint：确保导入的数据写入主DB文件（而非留在新WAL中）
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print(f"  Final WAL checkpoint: {cursor.fetchone()}")

        print(f"  共导入 {imported} 个订阅源, 跳过 {skipped} 个")
        return imported
    finally:
        conn.close()


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
        # 清理临时文件（含WAL/SHM）
        for suffix in ['', '-wal', '-shm']:
            path = tmp_db_path + suffix
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    main()
