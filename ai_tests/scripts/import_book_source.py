#!/usr/bin/env python3
r"""import_book_source.py — 导入书源到legado.db（book_sources 表）

B2 冻结验收环境准备（compose-migration-status-audit tasks §4.4-4.8 数据依赖）。
与 import_rss_source.py 同通道（WAL 安全三件套），适配 book_sources 表结构：
    force-stop → pull 主DB+wal/shm → 本地删 wal/shm（防 malformed）→
    PRAGMA wal_checkpoint(TRUNCATE) → PRAGMA 动态列适配 → DELETE+INSERT →
    final checkpoint → push 回推 + chown app uid + chmod 660 + 删设备端 wal/shm

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_book_source.py <json_path>
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_book_source.py --count   # 仅查询当前计数

JSON 格式：纯列表 [...] / 单对象 {...} / {"sources":[...]}；书源对象以
bookSourceUrl 为唯一键（DELETE 旧记录后 INSERT）。

脱敏口径：只输出计数与 id 特征（len/hash），禁输出源名称/完整 URL。

落位口径（总线 2.12 双登记）：
    .gitignore 白名单 !/ai_tests/scripts/import_book_source.py；
    ai_tests/docs/fixed_test_workflow.md 工具表；ai_tests/README.md 族索引。
"""
import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE  # noqa: E402

DB_DEVICE_PATH = f"/data/data/{PACKAGE}/databases/legado.db"
DB_DIR = f"/data/data/{PACKAGE}/databases/"

# 必须存在的核心列（缺失即书源不可用，FAIL）
REQUIRED_COLS = ("bookSourceUrl", "bookSourceName", "searchUrl",
                 "ruleSearch", "ruleBookInfo", "ruleToc", "ruleContent")


def _pkg(db_device_path: str) -> str:
    return db_device_path.split("/data/data/")[1].split("/databases")[0]


def set_active_package(pkg: str):
    global DB_DEVICE_PATH, DB_DIR
    DB_DEVICE_PATH = f"/data/data/{pkg}/databases/legado.db"
    DB_DIR = f"/data/data/{pkg}/databases/"
    print(f"  目标包名: {pkg}")


def run_adb(cmd, timeout=30):
    full = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    return subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)


def sh_su(cmd: str, timeout=20):
    """整条命令单字符串传给 adb shell（SOP 陷阱#4：列表传参会拆散 su -c）"""
    return run_adb(f"shell su -c '{cmd}'", timeout=timeout)


def get_app_uid() -> str:
    r = sh_su(f"stat -c %U {DB_DIR}")
    name = (r.stdout or "").strip()
    if name and name != "?":
        return name
    r2 = sh_su(f"stat -c %u {DB_DIR}")
    uid = (r2.stdout or "").strip()
    if uid.isdigit() and int(uid) >= 10000:
        return f"u0_a{int(uid) - 10000}"
    return "u0_a72"


def pull_db(tmp_path: str) -> bool:
    run_adb(f"shell am force-stop {_pkg(DB_DEVICE_PATH)}")
    time.sleep(2)
    sh_su(f"mkdir -p {DB_DIR}")
    sh_su(f"cp {DB_DEVICE_PATH} /sdcard/ibs.db")
    sh_su("chmod 666 /sdcard/ibs.db")
    for ext in ("-wal", "-shm"):
        sh_su(f"cp {DB_DEVICE_PATH}{ext} /sdcard/ibs.db{ext} 2>/dev/null; true")
    r = run_adb(f"pull /sdcard/ibs.db {tmp_path}")
    if r.returncode != 0:
        print(f"❌ Pull主DB失败: {r.stderr}")
        return False
    for ext in ("-wal", "-shm"):
        p = tmp_path + ext
        if Path(p).exists():
            Path(p).unlink()
    print("✅ DB pulled（本地 wal/shm 已清理防 malformed）")
    return True


def push_db(tmp_path: str) -> bool:
    r = run_adb(f"push {tmp_path} /sdcard/ibs.db")
    if r.returncode != 0:
        print(f"❌ Push失败: {r.stderr}")
        return False
    pkg = _pkg(DB_DEVICE_PATH)
    sh_su(f"cp /sdcard/ibs.db {DB_DEVICE_PATH}")
    app_user = get_app_uid()
    sh_su(f"chown {app_user}:{app_user} {DB_DEVICE_PATH}")
    sh_su(f"chmod 660 {DB_DEVICE_PATH}")
    sh_su(f"rm -f {DB_DEVICE_PATH}-wal {DB_DEVICE_PATH}-shm")
    print(f"✅ DB pushed（WAL/SHM 已清理, owner={app_user}, pkg={pkg}）")
    return True


def load_sources(json_path: str):
    data = json.load(open(json_path, encoding="utf-8"))
    if isinstance(data, dict) and "sources" in data:
        sources = data["sources"]
    elif isinstance(data, list):
        sources = data
    else:
        sources = [data]
    out = [s for s in sources if isinstance(s, dict) and s.get("bookSourceUrl")]
    print(f"  JSON 包含 {len(out)} 个书源")
    return out


def insert_sources(db_path: str, sources) -> int:
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cur.execute("PRAGMA table_info(book_sources)")
        meta = cur.fetchall()
        cols = [r[1] for r in meta]
        missing = [k for k in REQUIRED_COLS if k not in cols]
        if missing:
            print(f"❌ book_sources 缺核心列: {missing}")
            return 0
        inserted = 0
        for src in sources:
            keys = [k for k in src.keys() if k in cols]
            vals = [json.dumps(src[k], ensure_ascii=False)
                    if isinstance(src[k], (dict, list)) else src[k] for k in keys]
            extra_cols, extra_vals = [], []
            for _, name, ctype, notnull, dflt, _pk in meta:
                if name in keys:
                    continue
                if dflt is not None:
                    extra_cols.append(name)
                    extra_vals.append(dflt.replace("'", "") if isinstance(dflt, str) else dflt)
                elif notnull:
                    extra_cols.append(name)
                    extra_vals.append(0 if "INT" in (ctype or "").upper() else "")
            all_cols, all_vals = keys + extra_cols, vals + extra_vals
            url = src["bookSourceUrl"]
            cur.execute("DELETE FROM book_sources WHERE bookSourceUrl = ?", (url,))
            cur.execute(
                f"INSERT INTO book_sources ({','.join(all_cols)}) "
                f"VALUES ({','.join(['?'] * len(all_cols))})", all_vals)
            cur.execute("SELECT COUNT(*) FROM book_sources WHERE bookSourceUrl = ?", (url,))
            if cur.fetchone()[0] >= 1:
                inserted += 1
                print(f"  [OK] 源 id(len={len(str(url))}, hash={hash(str(url)) % 100000}) 插入校验通过")
            else:
                print("  [FAIL] 插入校验失败")
        con.commit()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print(f"  Final WAL checkpoint OK")
        return inserted
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="导入书源到legado.db（book_sources 表）")
    ap.add_argument("json_path", nargs="?", help="书源 JSON 文件路径")
    ap.add_argument("--package", default=PACKAGE, help=f"目标包名（默认: {PACKAGE}）")
    ap.add_argument("--count", action="store_true", help="仅查询当前 book_sources 计数")
    args = ap.parse_args()

    set_active_package(args.package)

    if args.count:
        tmp = tempfile.mktemp(suffix=".db")
        if not pull_db(tmp):
            sys.exit(2)
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM book_sources")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM book_sources WHERE enabled = 1")
        enabled = cur.fetchone()[0]
        con.close()
        Path(tmp).unlink()
        print(f"book_sources 计数: total={total}, enabled={enabled}")
        sys.exit(0)

    if not args.json_path or not Path(args.json_path).exists():
        print("❌ JSON 文件不存在")
        sys.exit(1)

    print("=" * 60)
    print("Legado 书源导入工具（book_sources 表, WAL 安全三件套）")
    print("=" * 60)

    sources = load_sources(args.json_path)
    if not sources:
        print("❌ 无有效书源")
        sys.exit(1)

    tmp = tempfile.mktemp(suffix=".db")
    try:
        if not pull_db(tmp):
            sys.exit(2)
        n = insert_sources(tmp, sources)
        if n == 0:
            print("❌ 未导入任何书源")
            sys.exit(1)
        if not push_db(tmp):
            sys.exit(2)
        print(f"\n✅ 书源导入完成: {n}/{len(sources)} 个")
    finally:
        for suffix in ("", "-wal", "-shm"):
            p = tmp + suffix
            if Path(p).exists():
                Path(p).unlink()


if __name__ == "__main__":
    main()
