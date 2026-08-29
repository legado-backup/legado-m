#!/usr/bin/env python3
"""双包（debug/release）无崩溃验证脚本（no-crash 固化，2026-08-29）。

场景背景：正式包 3.26.082918 因 R8 混淆致 Gson 泛型失效，进入发现页读缓存时
ClassCastException 崩溃。本脚本验证禁混淆后双包：安装→启动→进入发现页→
二轮重启复现缓存读取→logcat 崩溃模式分析。

用法:
    python ai_tests/scripts/verify_no_crash.py --type debug
    python ai_tests/scripts/verify_no_crash.py --type release
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import ADB_PATH, MEMU_ADB_HOST, BUILD_TYPE, PACKAGE, MAIN_ACTIVITY
from lib.memu_controller import MemuController

CRASH_PATTERNS = [
    ("FATAL_EXCEPTION", r"FATAL EXCEPTION"),
    ("ANDROID_RUNTIME", r"AndroidRuntime: .*Exception"),
    ("CLASS_CAST", r"ClassCastException"),
]

DISCOVERY_TAB_TEXT = "发现"
SETTLE_SECONDS = 8


def latest_apk(build_type: str) -> Path:
    if build_type == "release":
        d = Path(__file__).parent.parent.parent / "app" / "build" / "outputs" / "apk" / "app" / "release"
    else:
        d = Path(__file__).parent.parent.parent / "app" / "build" / "outputs" / "apk" / "app" / "debug"
    apks = sorted(d.glob("legado_miss_app_*.apk"), key=lambda p: p.stat().st_mtime)
    if not apks:
        raise SystemExit(f"[FAIL] no apk found in {d}")
    return apks[-1]


def sh(ctrl: MemuController, *args: str, timeout: int = 60) -> str:
    _rc, out, _err = ctrl.adb(*args, timeout=timeout)
    return out if isinstance(out, str) else out.decode("utf-8", errors="ignore")


def dump(ctrl: MemuController) -> str:
    sh(ctrl, "shell", "uiautomator", "dump", "/data/local/tmp/verify_no_crash_ui.xml", timeout=30)
    return sh(ctrl, "shell", "cat", "/data/local/tmp/verify_no_crash_ui.xml", timeout=30)


def tap_node(ctrl: MemuController, xml: str, attr_pattern: str) -> bool:
    m = re.search(attr_pattern + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        return False
    x = (int(m.group(1)) + int(m.group(3))) // 2
    y = (int(m.group(2)) + int(m.group(4))) // 2
    sh(ctrl, "shell", "input", "tap", str(x), str(y))
    return True


def tap_text(ctrl: MemuController, xml: str, text: str) -> bool:
    return tap_node(ctrl, xml, r'text="' + re.escape(text) + r'"')


def tap_discovery_tab(ctrl: MemuController, xml: str) -> bool:
    # 底部导航"发现"tab：content-desc 形态（menu_discovery）
    if tap_node(ctrl, xml, r'content-desc="发现"'):
        return True
    return tap_node(ctrl, xml, r'resource-id="[^"]*:id/menu_discovery"')


def launch_and_open_discovery(ctrl: MemuController, pkg: str, act: str, round_no: int) -> bool:
    sh(ctrl, "shell", "am", "start", "-n", f"{pkg}/{act}")
    time.sleep(SETTLE_SECONDS)
    xml = dump(ctrl)
    # 检查更新弹框（正式包首启会弹，404 提示属已知遗留问题）先关闭再导航
    if tap_text(ctrl, xml, "关闭"):
        print(f"  R{round_no}: 已关闭检查更新弹框")
        time.sleep(2)
        xml = dump(ctrl)
    if not tap_discovery_tab(ctrl, xml):
        print(f"  R{round_no}: 发现 tab 未找到（可能已在其他页），尝试返回后重试")
        sh(ctrl, "shell", "input", "keyevent", "4")
        time.sleep(2)
        xml = dump(ctrl)
        if not tap_discovery_tab(ctrl, xml):
            return False
    time.sleep(5)
    print(f"  R{round_no}: 已点击发现 tab 并等待加载")
    return True


def crash_report(ctrl: MemuController) -> dict:
    log = sh(ctrl, "logcat", "-d", "-t", "3000", timeout=60)
    result = {}
    for name, pat in CRASH_PATTERNS:
        result[name] = len(re.findall(pat, log))
    return result


def taint_discovery_cache(ctrl: MemuController, pkg: str) -> int:
    """注入脏缓存模拟旧混淆版写入（顶层字段名混淆化+books 指向非法结构），验证加固后自愈不崩"""
    import json
    import sqlite3
    db_remote = f"/data/data/{pkg}/databases/legado.db"
    db_local = Path(__file__).parent.parent / "reports" / "verify_no_crash_cache.db"
    db_local.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        f = Path(str(db_local) + suffix)
        if f.exists():
            f.unlink()
    sh(ctrl, "pull", db_remote, str(db_local), timeout=60)
    if not db_local.exists():
        print("  [taint] DB pull 失败，跳过注入")
        return 0
    con = sqlite3.connect(str(db_local))
    n = 0
    try:
        rows = con.execute(
            "select key, value from caches where key like 'discovery_modern_result_%'"
        ).fetchall()
        if not rows:
            print("  [taint] 未发现发现页缓存行（App 未写入），跳过注入")
            return 0
        for key, value in rows:
            try:
                data = json.loads(value)
            except Exception:
                data = {}
            # 模拟旧混淆版脏数据：顶层字段名替换为单字母别名；books 注入非法元素结构
            tainted = {"a": data.get("sourceUrl", ""), "b": data.get("tagUrl", ""),
                       "books": [{"evil": 1}, {"evil": 2}], "e": 2, "f": True, "g": 0}
            con.execute("update cache set value=? where key=?", (json.dumps(tainted), key))
            n += 1
        con.commit()
        print(f"  [taint] 已注入脏缓存 {n} 行")
    finally:
        con.close()
    sh(ctrl, "shell", "am", "force-stop", pkg)
    time.sleep(1)
    sh(ctrl, "push", str(db_local), db_remote, timeout=60)
    for suffix in ("-wal", "-shm"):
        sh(ctrl, "shell", "rm", "-f", db_remote + suffix)
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["debug", "release"], default=BUILD_TYPE)
    parser.add_argument("--taint", action="store_true", help="注入脏缓存复现旧数据场景")
    args = parser.parse_args()

    pkg = f"io.legado.miss.app.{args.type}"
    apk = latest_apk(args.type)
    print(f"== verify_no_crash: type={args.type} pkg={pkg}")
    print(f"   apk={apk.name}")

    ctrl = MemuController()
    if not ctrl.is_running():
        ctrl.start()
    host = ctrl.wait_for_adb() or MEMU_ADB_HOST
    print(f"   adb host={host}")

    print("== 1. 覆盖安装")
    if not ctrl.install_app(str(apk)):
        print("[FAIL] 安装失败")
        return 1

    print("== 2. 清 logcat + 启动")
    sh(ctrl, "logcat", "-c")
    ok1 = launch_and_open_discovery(ctrl, pkg, MAIN_ACTIVITY, 1)

    print("== 3. 二轮重启（复现发现页缓存读取场景）")
    sh(ctrl, "shell", "am", "force-stop", pkg)
    time.sleep(2)
    ok2 = launch_and_open_discovery(ctrl, pkg, MAIN_ACTIVITY, 2)

    ok3 = True
    if args.taint:
        print("== 3b. 脏缓存注入（模拟旧混淆版数据）+ 三轮读取验证自愈")
        n = taint_discovery_cache(ctrl, pkg)
        if n > 0:
            sh(ctrl, "logcat", "-c")
            ok3 = launch_and_open_discovery(ctrl, pkg, MAIN_ACTIVITY, 3)
            counts_extra = crash_report(ctrl)
            for name, c in counts_extra.items():
                print(f"   taint-{name}: {c}")
            ok3 = ok3 and all(c == 0 for c in counts_extra.values())

    print("== 4. logcat 崩溃模式分析（3 轮全量窗口）")
    counts = crash_report(ctrl)
    for name, c in counts.items():
        print(f"   {name}: {c}")

    nav_ok = ok1 and ok2 and ok3
    crash_ok = all(c == 0 for c in counts.values())
    verdict = "PASS" if (nav_ok and crash_ok) else "FAIL"
    print(f"== 判定: {verdict} (导航={nav_ok}, 崩溃模式全零={crash_ok})")
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
