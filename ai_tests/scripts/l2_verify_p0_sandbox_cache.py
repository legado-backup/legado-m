#!/usr/bin/env python3
r"""l2_verify_p0_sandbox_cache.py — ng-p0-source-security-impl S1 沙箱 / S2 缓存命名空间 L2 真机验证

用途（覆盖 P0 T11-T14 + T22 的真机可验证子集，设计账本
docs/specs/ng-benchmark-analysis/migration-designs/P0-source-security-hardening.md §9.2）：
    S2 缓存场景（T11-T14 可验证核心，scenario=cache）：
        1) adb 写 prefs bookSourceCacheScoped=true → force-stop 重启（防内存态回写）
        2) 断言设置生效（prefs 回读）
        3) 查询 DB caches 表命名空间前缀计数：
           SELECT COUNT(*) FROM caches WHERE key LIKE 'book_source_cache_%'
           （key 形如 book_source_cache_{ns}:，ns=SHA-256("book\0"+sourceUrl) hex64；
            sqlite3 设备侧不可用则拉三件套 db/-wal/-shm 本地查，T11 前缀合规性本地校验）
        4) 输出基线计数 + 结论：无书源脚本触发数据时=环境就绪断言 + 手动触发清单
    S1 沙箱场景（T22 可验证核心，scenario=sandbox）：
        1) adb 写 prefs bookSourceFileSandbox=true → force-stop 重启
        2) prefs 回读断言
        3) 基线检查沙箱根目录 externalCache/source/ 存在性（存在则校验子目录名
           hex64 模式，只输出计数/布尔不输出目录名；未生成属预期=等待触发）
        4) 输出手动触发清单（真实书源 JS downloadFile/getFile 属交互场景）
    T14 删源清理：需 UI 删源交互，输出手动清单（scenario=both/cache 尾部输出）

前置：
    1. MEmu 模拟器已启动（MEMU_ADB_HOST 默认实例0）；测试包 io.legado.miss.app.debug 已安装
    2. su 可用（MEmu 默认 root，与 l2_verify_image_enhance_governance.py 同通道）
    3. 必须用 ai_tests\venv\Scripts\python.exe
    4. ⚠️ 编译/装机进行中禁跑本脚本（与 quick_build_install.py 互斥）；本脚本零编译零安装，
       仅只读 adb + prefs 写入 + DB 拉库

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_p0_sandbox_cache.py
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_p0_sandbox_cache.py --scenario cache
    --scenario cache|sandbox|both（默认 both）

双登记说明（落位口径总线 2.12 核定）：
    族命名 l2_verify_*；.gitignore 白名单 `!/ai_tests/scripts/l2_verify_p0_sandbox_cache.py`；
    双登记 = ai_tests/docs/fixed_test_workflow.md 脚本表 16k 行 + ai_tests/README.md 族索引。

脱敏：全程只输出计数/路径模式/开关布尔/校验布尔，禁输出源名称/完整 URL/业务文本。
退出码：0=环境就绪断言全部通过 1=断言未通过 2=致命错误（设备/环境不可用）
"""
import argparse
import base64
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

HOST = MEMU_ADB_HOST
MAIN = f"{PACKAGE}/io.legado.app.ui.main.MainActivity"
# 默认 SharedPreferences（ContextExtensions.getPrefBoolean → defaultSharedPreferences）
PREFS_DEFAULT = f"/data/data/{PACKAGE}/shared_prefs/{PACKAGE}_preferences.xml"
DB_REMOTE = f"/data/data/{PACKAGE}/databases/legado.db"
# 沙箱根目录 = context.externalCacheDir/source/（BookSourceFileAccessPolicy）
SANDBOX_ROOT = f"/storage/emulated/0/Android/data/{PACKAGE}/cache/source"
DB_TMP_PREFIX = "/data/local/tmp/p0chk"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

RESULTS = {}


def sh(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh_su(cmd: str, timeout=20):
    """整条命令作为单字符串传给 adb shell（SOP 陷阱#4：列表传参会拆散 su -c）"""
    return sh("su -c '%s'" % cmd, timeout=timeout)


def log(msg):
    print(msg)


def find_prefs_path() -> str:
    """默认 *_preferences.xml；缺失则按技术名匹配 shared_prefs 下首个 _preferences 文件"""
    if sh_su(f"test -f {PREFS_DEFAULT} && echo ok").stdout.strip() == b"ok":
        return PREFS_DEFAULT
    r = sh_su(f"ls /data/data/{PACKAGE}/shared_prefs/ | grep '_preferences' | head -n 1")
    name = r.stdout.decode("utf-8", errors="ignore").strip()
    return f"/data/data/{PACKAGE}/shared_prefs/{name}" if name else PREFS_DEFAULT


def read_prefs(retries=3, interval=1.0) -> dict:
    """su + base64 读 preferences xml → {key: value}（含轮询，apply 异步落盘）"""
    path = find_prefs_path()
    for _ in range(retries):
        r = sh_su(f"base64 {path} 2>/dev/null")
        raw = r.stdout.decode("utf-8", errors="ignore").strip()
        if raw:
            try:
                xml = base64.b64decode(raw).decode("utf-8", errors="ignore")
                prefs = {}
                for m in re.finditer(r'<(\w+)\s+name="([^"]+)"\s+value="([^"]*)"', xml):
                    prefs[m.group(2)] = m.group(3)
                return prefs
            except Exception:
                pass
        time.sleep(interval)
    return {}


def set_pref(name: str, value: str) -> bool:
    """force-stop 后 su 改 preferences 指定 boolean 键（存在改值/缺失插入）→ 重启 → 回读校验。
    照搬 l2_verify_image_enhance_governance.py 的 set_video_pref 模式。"""
    sh("am", "force-stop", PACKAGE)
    time.sleep(1.5)
    path = find_prefs_path()
    raw = ""
    for _ in range(3):
        r = sh_su(f"base64 {path} 2>/dev/null")
        raw = r.stdout.decode("utf-8", errors="ignore").strip()
        if raw:
            break
        time.sleep(1.0)
    if not raw:
        log("[WARN] preferences 文件不可读")
        return False
    try:
        xml = base64.b64decode(raw).decode("utf-8", errors="ignore")
    except Exception:
        return False
    pat = re.compile(r'(<boolean name="%s" value=")[^"]*(")' % name)
    if pat.search(xml):
        xml = pat.sub(r"\g<1>%s\g<2>" % value, xml)
    else:
        xml = xml.replace("</map>", '<boolean name="%s" value="%s" /></map>' % (name, value))
    local = Path(__file__).parent.parent / "reports" / "p0_prefs_tmp.xml"
    local.parent.mkdir(exist_ok=True)
    local.write_text(xml, encoding="utf-8")
    subprocess.run([ADB_PATH, "-s", HOST, "push", str(local), "/sdcard/p0_prefs_tmp.xml"],
                   capture_output=True, timeout=30)
    sh_su(f"cat /sdcard/p0_prefs_tmp.xml > {path}")
    sh("am", "start", "-n", MAIN)
    time.sleep(4.0)
    got = read_prefs().get(name)
    ok = got == value
    log(f"[PREF] {name}={got}(期望{value}) {'OK' if ok else 'MISMATCH'}")
    return ok


def pull_db_local() -> str:
    """拉三件套 db/-wal/-shm 到本地临时文件（保留 WAL 让 sqlite 恢复，probe_db_wal.py 同模式）"""
    base = tempfile.mktemp(suffix=".db")
    for suffix in ("", "-wal", "-shm"):
        sh_su(f"cp {DB_REMOTE}{suffix} {DB_TMP_PREFIX}{suffix}", timeout=30)
        sh_su(f"chmod 666 {DB_TMP_PREFIX}{suffix}", timeout=10)
        subprocess.run([ADB_PATH, "-s", HOST, "pull", f"{DB_TMP_PREFIX}{suffix}", base + suffix],
                       capture_output=True, timeout=60)
    return base


def cleanup_db_local(base: str):
    for suffix in ("", "-wal", "-shm"):
        for p in (base + suffix,):
            if os.path.exists(p):
                os.remove(p)
        sh_su(f"rm -f {DB_TMP_PREFIX}{suffix}", timeout=10)


def query_cache_namespace() -> dict:
    """DB caches 表命名空间前缀查询（全程只输出计数/布尔）：
    - total: caches 总行数
    - scoped: key LIKE 'book_source_cache_%' 计数（T11 前缀族）
    - distinct_ns / ns_hex64_ok: 不同 ns 去重计数 + 全部 hex64 合规布尔"""
    base = pull_db_local()
    info = {"query_ok": False, "total": -1, "scoped": -1, "distinct_ns": -1, "ns_hex64_ok": False}
    try:
        con = sqlite3.connect(base)
        info["total"] = con.execute("SELECT COUNT(*) FROM caches").fetchone()[0]
        info["scoped"] = con.execute(
            "SELECT COUNT(*) FROM caches WHERE key LIKE 'book_source_cache_%'").fetchone()[0]
        nss = [r[0] for r in con.execute(
            "SELECT DISTINCT substr(key, 19, 64) FROM caches WHERE key LIKE 'book_source_cache_%'")]
        info["distinct_ns"] = len(nss)
        info["ns_hex64_ok"] = bool(nss) and all(HEX64.match(ns) for ns in nss)
        info["query_ok"] = True
        con.close()
    except Exception as e:
        log(f"[FAIL] caches 表查询异常: {type(e).__name__}")
    finally:
        cleanup_db_local(base)
    return info


def crash_count() -> int:
    r = sh("logcat", "-d", "-b", "crash", timeout=15)
    return len(re.findall(r"FATAL EXCEPTION", r.stdout.decode("utf-8", errors="ignore")))


def clear_log():
    sh("logcat", "-c", timeout=10)


def check_sandbox_root() -> dict:
    """沙箱根目录基线检查：存在性 + 子目录 hex64 模式（只输出计数/布尔，不输出目录名）"""
    info = {"exists": False, "subdirs": -1, "hex64_ok": False}
    r = sh_su(f"test -d {SANDBOX_ROOT} && echo ok", timeout=15)
    if r.stdout.strip() != b"ok":
        return info  # 未生成属预期（等待书源 JS 触发）
    info["exists"] = True
    r = sh_su(f"ls {SANDBOX_ROOT}", timeout=15)
    entries = [e for e in r.stdout.decode("utf-8", errors="ignore").split() if e]
    dirs = []
    for e in entries:
        if sh_su(f"test -d {SANDBOX_ROOT}/{e} && echo ok", timeout=10).stdout.strip() == b"ok":
            dirs.append(e)
    info["subdirs"] = len(dirs)
    info["hex64_ok"] = bool(dirs) and all(HEX64.match(d) for d in dirs)
    return info


MANUAL_T11 = """T11 scopedKey 前缀（自动前置已就绪，触发后复核）：
    任一书源正文 JS 执行 java.cache.put("k","v") → 本脚本 --scenario cache 重跑，
    应见 scoped 计数 ≥1 且 ns_hex64_ok=true"""
MANUAL_T12 = """T12 跨源隔离（交互场景，需真实书源 JS）：
    两个不同书源各自脚本 cache.put 同名 key 不同值 → 各自 get 互不可见；
    DB 复核 distinct_ns ≥2"""
MANUAL_T13 = """T13 clear 单源清理（交互场景）：
    源A java.cache.clear() → 源A 前缀键清零、源B 前缀键保留（DB 按前缀对比计数）"""
MANUAL_T14 = """T14 删源清理（UI 交互场景）：
    书源管理 UI 删除已产生缓存的书源 → caches 表对应 book_source_cache_{ns}: 键清零
    （删源前先记录该源 ns 计数作对比基线）；logcat 无 SourceCache 失败日志"""
MANUAL_T22 = """T22 downloadFile 双参沙箱（交互场景）：
    书源 JS downloadFile(url, headers/opts 双参变体) → 产物落
    externalCache/source/{hex64}/ 且 getFile 返回相对路径可读回（同落沙箱）"""

MANUAL_LIST = f"""
==================== 真机手动触发清单 ====================
{MANUAL_T11}

{MANUAL_T12}

{MANUAL_T13}

{MANUAL_T14}

{MANUAL_T22}
==========================================================
"""


# ==================== 场景：S2 缓存命名空间（T11-T14 环境） ====================

def scenario_cache():
    log("\n=== S2 缓存命名空间场景（T11-T14 环境就绪断言） ===")
    clear_log()
    ok = set_pref("bookSourceCacheScoped", "true")
    log(f"  开关生效(bookSourceCacheScoped=true): {ok}")

    info = query_cache_namespace()
    if info["query_ok"]:
        log(f"  caches 表总行数: {info['total']}")
        log(f"  命名空间前缀键数(book_source_cache_%): {info['scoped']}")
        log(f"  不同 ns 去重数: {info['distinct_ns']} | 全部 hex64 合规: {info['ns_hex64_ok']}")
        if info["scoped"] == 0:
            log("  [基线] 无书源脚本触发数据 → 基线计数=0，环境就绪（触发项见手动清单）")
        else:
            log("  [基线] 已存在命名空间缓存数据 → 可直接复核 T12/T13（见手动清单）")
    else:
        ok = False

    cc = crash_count()
    log(f"  重启后 FATAL 计数(crash buffer): {cc}（应 0）")
    verdict = ok and cc == 0
    log(f"  场景cache判定: {'PASS' if verdict else 'FAIL'}（开关={ok}, 查询={info['query_ok']}, FATAL={cc}）")
    print(MANUAL_LIST)
    return verdict


# ==================== 场景：S1 文件沙箱（T22 环境） ====================

def scenario_sandbox():
    log("\n=== S1 文件沙箱场景（T22 环境就绪断言） ===")
    clear_log()
    ok = set_pref("bookSourceFileSandbox", "true")
    log(f"  开关生效(bookSourceFileSandbox=true): {ok}")

    info = check_sandbox_root()
    if info["exists"]:
        log(f"  沙箱根目录已存在: {info['exists']} | 子目录数: {info['subdirs']} | "
            f"子目录全部 hex64 命名空间: {info['hex64_ok']}")
        sandbox_ok = info["hex64_ok"]
        if info["subdirs"] == 0:
            log("  [基线] 沙箱根目录为空 → 基线存在性断言通过（触发项见手动清单）")
            sandbox_ok = True
    else:
        log("  [基线] 沙箱根目录未生成（书源 JS 文件操作前属预期）→ 基线断言通过")
        log(f"  预期路径模式: externalCache/source/{{ns}}/（ns=SHA-256('book\\0'+sourceUrl) hex64）")
        sandbox_ok = True

    cc = crash_count()
    log(f"  重启后 FATAL 计数(crash buffer): {cc}（应 0）")
    verdict = ok and sandbox_ok and cc == 0
    log(f"  场景sandbox判定: {'PASS' if verdict else 'FAIL'}（开关={ok}, 目录基线={sandbox_ok}, FATAL={cc}）")
    return verdict


# ==================== main ====================

def main():
    parser = argparse.ArgumentParser(description="P0 S1 沙箱/S2 缓存命名空间 L2 真机验证（T11-T14+T22 环境）")
    parser.add_argument("--scenario", choices=["cache", "sandbox", "both"], default="both")
    args = parser.parse_args()

    log("=" * 60)
    log("P0 沙箱/缓存命名空间 L2 真机验证（ng-p0-source-security-impl）")
    log(f"场景: {args.scenario} | 设备: {HOST} | 包: {PACKAGE}")
    log("=" * 60)

    probe = sh("get-state", timeout=10)
    if probe.returncode != 0:
        log("❌ 设备不可连接（MEmu 未启动或 ADB 未就绪）")
        sys.exit(2)
    if not sh_su("id -u").stdout.strip().endswith(b"0"):
        log("❌ su 不可用（MEmu 默认 root，请检查模拟器 root 开关）")
        sys.exit(2)

    run = [args.scenario] if args.scenario != "both" else ["cache", "sandbox"]
    if "cache" in run:
        RESULTS["S2_cache_namespace_env_T11_T14"] = scenario_cache()
    if "sandbox" in run:
        RESULTS["S1_file_sandbox_env_T22"] = scenario_sandbox()

    log("\n" + "=" * 60)
    log("L2 环境就绪断言结果汇总（手动触发项见上方清单）")
    log("=" * 60)
    for name, passed in RESULTS.items():
        log(f"  {name}: {'PASS' if passed else 'FAIL'}")
    sys.exit(0 if all(RESULTS.values()) else 1)


if __name__ == "__main__":
    main()
