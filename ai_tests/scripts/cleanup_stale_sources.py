#!/usr/bin/env python3
"""cleanup_stale_sources.py — 清理残留的旧源

导入脚本 DELETE 用新 sourceUrl，但部分源 sourceUrl 变了（如域名迁移），
导致旧源残留。本脚本删除 optimized_final_v3.json 中不存在的源。

流程：
1. pull db
2. 读取 optimized_final_v3.json 的所有 sourceUrl（脚本内部，不输出）
3. DELETE FROM rssSources WHERE sourceUrl NOT IN (...)
4. push db

输出：删除数量 + 剩余数量
不输出：sourceUrl/源名称
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'
PKG = 'io.legado.app.debug'
INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final_v3.json'


def run_adb(cmd, timeout=30):
    full_cmd = f'"{ADB}" -s {HOST} {cmd}'
    return subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def main():
    print('=' * 70)
    print('清理残留旧源（脱敏输出）')
    print('=' * 70)
    
    # 读取 optimized_final_v3.json 的所有 sourceUrl
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    valid_source_urls = [s.get('sourceUrl', '') for s in sources if s.get('sourceUrl')]
    print(f'\n  JSON 中源数: {len(sources)}')
    print(f'  JSON 中有效 sourceUrl 数: {len(valid_source_urls)}')
    
    # pull db
    tmp_path = tempfile.mktemp(suffix='.db')
    print(f'\n--- Pull DB ---')
    run_adb(f'shell am force-stop {PKG}')
    import time
    time.sleep(1)
    run_adb('shell rm -f /sdcard/legado_cleanup.db')
    run_adb(f"shell su -c 'cp /data/data/{PKG}/databases/legado.db /sdcard/legado_cleanup.db'")
    run_adb("shell su -c 'chmod 666 /sdcard/legado_cleanup.db'")
    run_adb(f'pull /sdcard/legado_cleanup.db {tmp_path}')
    
    # 清理 WAL
    for ext in ['-wal', '-shm']:
        p = tmp_path + ext
        if os.path.exists(p):
            os.unlink(p)
    
    # 操作 DB
    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 查询当前源数
    cur.execute('SELECT COUNT(*) FROM rssSources')
    before_count = cur.fetchone()[0]
    print(f'\n  清理前 DB 中源数: {before_count}')
    
    # 查询哪些 sourceUrl 不在 valid_source_urls 中
    placeholders = ', '.join(['?'] * len(valid_source_urls))
    cur.execute(f'SELECT sourceUrl FROM rssSources WHERE sourceUrl NOT IN ({placeholders})', valid_source_urls)
    stale_rows = cur.fetchall()
    stale_count = len(stale_rows)
    print(f'  残留旧源数: {stale_count}')
    
    # 删除残留
    if stale_count > 0:
        cur.execute(f'DELETE FROM rssSources WHERE sourceUrl NOT IN ({placeholders})', valid_source_urls)
        conn.commit()
        print(f'  ✅ 已删除 {stale_count} 个残留源')
    else:
        print(f'  无残留源，无需清理')
    
    # 查询清理后源数
    cur.execute('SELECT COUNT(*) FROM rssSources')
    after_count = cur.fetchone()[0]
    print(f'  清理后 DB 中源数: {after_count}')
    
    conn.close()
    
    # push db
    print(f'\n--- Push DB ---')
    run_adb(f'push {tmp_path} /sdcard/legado_cleanup.db')
    run_adb("shell su -c 'chmod 666 /sdcard/legado_cleanup.db'")
    run_adb(f"shell su -c 'cp /sdcard/legado_cleanup.db /data/data/{PKG}/databases/legado.db'")
    run_adb(f"shell su -c 'chmod 660 /data/data/{PKG}/databases/legado.db'")
    run_adb(f"shell su -c 'rm -f /data/data/{PKG}/databases/legado.db-wal /data/data/{PKG}/databases/legado.db-shm'")
    run_adb('shell rm -f /sdcard/legado_cleanup.db')
    
    # 清理临时文件
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
    
    print(f'\n✅ 清理完成: 删除 {stale_count} 个残留源，剩余 {after_count} 个')


if __name__ == '__main__':
    main()
