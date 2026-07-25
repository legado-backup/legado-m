#!/usr/bin/env python3
r"""import_rss_source_v5.py — V5专用导入脚本（按 sourceUrl+sourceName 组合去重）

与 import_rss_source.py 的差异：
- DELETE 逻辑改为 WHERE sourceUrl=? AND sourceName=?
  原因：V5中聚合/导航拆分子源共享父站sourceUrl但sourceName不同（按分类区分），
  原脚本按sourceUrl单字段去重会损失47个子源。
- 组合去重保证：同URL不同sourceName的子源都保留，完全重复（URL+名称都相同）才替换。

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_rss_source_v5.py <json_path>
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
from config import ADB_PATH, MEMU_ADB_HOST as _CFG_ADB_HOST, PACKAGE

# 自动检测当前连接的ADB设备（覆盖config.py中的端口，因为MEmu不同实例端口不同）
def _detect_adb_host():
    try:
        r = subprocess.run(f'"{ADB_PATH}" devices', shell=True, capture_output=True, text=True, timeout=10)
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        for line in lines[1:]:  # 跳过 "List of devices attached"
            if '\tdevice' in line:
                return line.split('\t')[0]
    except Exception as e:
        print(f"  [WARN] auto-detect adb host failed: {e}")
    return _CFG_ADB_HOST

MEMU_ADB_HOST = _detect_adb_host()
print(f"[INFO] 使用ADB设备: {MEMU_ADB_HOST} (config默认: {_CFG_ADB_HOST})")

DB_DEVICE_PATH = f"/data/data/{PACKAGE}/databases/legado.db"
DB_DIR = f"/data/data/{PACKAGE}/databases/"


def run_adb(cmd, timeout=30):
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    print(f"  >>> {full_cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def pull_db(tmp_path):
    print("\n--- Pull legado.db (含WAL/SHM) ---")
    run_adb(f"shell su -c 'mkdir -p {DB_DIR}'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db'")
    run_adb(f"shell su -c 'chmod 666 /sdcard/legado.db'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-wal /sdcard/legado.db-wal 2>/dev/null; chmod 666 /sdcard/legado.db-wal 2>/dev/null; true'")
    run_adb(f"shell su -c 'cp {DB_DEVICE_PATH}-shm /sdcard/legado.db-shm 2>/dev/null; chmod 666 /sdcard/legado.db-shm 2>/dev/null; true'")
    result = run_adb(f"pull /sdcard/legado.db {tmp_path}")
    if result.returncode != 0:
        print(f"❌ Pull主DB失败: {result.stderr}")
        return False
    run_adb(f"pull /sdcard/legado.db-wal {tmp_path}-wal")
    run_adb(f"pull /sdcard/legado.db-shm {tmp_path}-shm")
    for ext in ['-wal', '-shm']:
        wal_path = f"{tmp_path}{ext}"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
            print(f"  清理本地{ext}文件（避免malformed）")
    print(f"✅ DB pulled to {tmp_path}")
    return True


def push_db(tmp_path):
    print("\n--- Push legado.db (清理WAL/SHM) ---")
    result = run_adb(f"push {tmp_path} /sdcard/legado.db")
    if result.returncode != 0:
        print(f"❌ Push失败: {result.stderr}")
        return False
    run_adb(f"shell su -c 'cp /sdcard/legado.db {DB_DEVICE_PATH}'")
    run_adb(f"shell su -c 'chmod 660 {DB_DEVICE_PATH}'")
    run_adb(f"shell su -c 'rm -f {DB_DEVICE_PATH}-wal {DB_DEVICE_PATH}-shm'")
    print(f"✅ DB pushed back (WAL/SHM已清理)")
    return True


def import_rss(json_path, db_path, clean_first=False):
    print(f"\n--- 导入订阅源(V5组合去重): {json_path} ---")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        if 'sources' in data:
            sources = data['sources']
            meta = {k: v for k, v in data.items() if k != 'sources'}
            print(f"  JSON元信息(部分): version={meta.get('version')}, total_sources={meta.get('total_sources')}")
            if 'merge_report' in meta:
                print(f"  merge_report: {meta['merge_report']}")
        else:
            sources = [data]
    elif isinstance(data, list):
        sources = data
    else:
        print(f"❌ 不支持的JSON格式: {type(data)}")
        return 0

    print(f"  JSON包含 {len(sources)} 个订阅源")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        checkpoint_result = cursor.fetchone()
        print(f"  WAL checkpoint: {checkpoint_result}")

        cursor.execute("PRAGMA table_info(rssSources)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"  rssSources 表列: {len(columns)} 列")

        # 导入前统计
        cursor.execute("SELECT COUNT(*) FROM rssSources")
        before_count = cursor.fetchone()[0]
        print(f"  导入前DB中rssSources记录数: {before_count}")

        # 如果指定 --clean，先清空表（避免主键冲突）
        if clean_first:
            print(f"  [CLEAN] 清空 rssSources 表...")
            cursor.execute("DELETE FROM rssSources")
            deleted = cursor.rowcount
            print(f"  [CLEAN] 已删除 {deleted} 条旧记录")
            conn.commit()

        imported = 0
        skipped = 0
        deduped = 0
        for source in sources:
            if not isinstance(source, dict):
                skipped += 1
                continue
            source_name = source.get('sourceName', 'unknown')
            source_url = source.get('sourceUrl', '')

            # V5组合去重：按 sourceUrl + sourceName 组合删除旧记录
            # 这样同URL不同sourceName的子源都能保留
            cursor.execute(
                "DELETE FROM rssSources WHERE sourceUrl = ? AND sourceName = ?",
                (source_url, source_name)
            )
            if cursor.rowcount > 0:
                deduped += 1

            valid_keys = [k for k in source.keys() if k in columns]
            if not valid_keys:
                print(f"  ⚠️ 跳过: sourceName存在（无匹配列）")
                skipped += 1
                continue
            placeholders = ', '.join(['?'] * len(valid_keys))
            col_names = ', '.join(valid_keys)
            values = [str(source[k]) if not isinstance(source[k], (int, float, bool)) else source[k]
                      for k in valid_keys]

            try:
                cursor.execute(
                    f"INSERT INTO rssSources ({col_names}) VALUES ({placeholders})",
                    values
                )
                imported += 1
            except sqlite3.IntegrityError as e:
                print(f"  ⚠️ INSERT失败(IntegrityError): {str(e)[:80]}")
                skipped += 1

        conn.commit()

        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print(f"  Final WAL checkpoint: {cursor.fetchone()}")

        # 导入后统计
        cursor.execute("SELECT COUNT(*) FROM rssSources")
        after_count = cursor.fetchone()[0]
        print(f"  导入后DB中rssSources记录数: {after_count}")

        print(f"  共导入 {imported} 个订阅源, 跳过 {skipped} 个, 替换旧记录 {deduped} 个")
        return imported
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("用法: python import_rss_source_v5.py <json_path> [--clean]")
        print("  --clean: 导入前清空 rssSources 表（避免主键冲突）")
        sys.exit(1)

    json_path = sys.argv[1]
    clean_first = '--clean' in sys.argv[2:]
    if not os.path.exists(json_path):
        print(f"❌ JSON文件不存在: {json_path}")
        sys.exit(1)

    print("=" * 60)
    print("Legado V5 订阅源导入工具 (组合去重版)")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        if not pull_db(tmp_db_path):
            sys.exit(1)

        count = import_rss(json_path, tmp_db_path, clean_first=clean_first)
        if count == 0:
            print("❌ 未导入任何订阅源")
            sys.exit(1)

        if not push_db(tmp_db_path):
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"✅ V5订阅源导入完成: {count} 个订阅源")
        print("=" * 60)

    finally:
        for suffix in ['', '-wal', '-shm']:
            path = tmp_db_path + suffix
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    main()
