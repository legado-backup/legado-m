#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l2_verify_fix_0906.py — video-regression-fix-0906 专项 L2 验证
S1 书源沉浸式上滑=集内下一集（无队列降级）/ S2 下滑=上一集 / S3 LogActivity 四Tab可达
用法：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_fix_0906.py [--scenario all|s1|s3]
证据：ai_tests/reports/ui_batch_fix_0905/（复用目录）
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uiautomator2 as u2

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "ui_batch_fix_0905"
MAIN = f"{PACKAGE}/io.legado.app.ui.main.MainActivity"


def sh(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", MEMU_ADB_HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def crash_count() -> int:
    r = sh("logcat", "-d", "-b", "crash", timeout=15)
    return len(re.findall(r"FATAL EXCEPTION", r.stdout.decode("utf-8", "ignore")))


def screenshot(d, name: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    remote = f"/sdcard/{name}.png"
    local = REPORT_DIR / f"{name}.png"
    sh("screencap", "-p", remote, timeout=20)
    subprocess.run([ADB_PATH, "-s", MEMU_ADB_HOST, "pull", remote, str(local)],
                   capture_output=True, timeout=30)
    sh("rm", remote)
    return local


def _set_video_layout_mode(mode: int):
    """0 沉浸式 / 1 传统（force-stop 后写入并回读）"""
    import base64
    VIDEO_PREFS = f"/data/data/{PACKAGE}/shared_prefs/video_config.xml"
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)
    r = sh("su -c 'base64 %s 2>/dev/null'" % VIDEO_PREFS)
    raw = r.stdout.decode("utf-8", "ignore").strip()
    if raw:
        xml = base64.b64decode(raw).decode("utf-8", "ignore")
        if 'name="layoutMode"' in xml:
            xml = re.sub(r'(<int\s+name="layoutMode"\s+value=")\d+(")',
                         r'\g<1>%d\g<2>' % mode, xml)
        else:
            xml = xml.replace("</map>", f'<int name="layoutMode" value="{mode}" /></map>')
    else:
        xml = ("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>"
               f"<map><int name=\"layoutMode\" value=\"{mode}\" /></map>")
    b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    sh("su -c 'echo %s | base64 -d > %s'" % (b64, VIDEO_PREFS), timeout=30)


def pick_video_book():
    import sqlite3
    import tempfile
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "legado.db")
        subprocess.run([ADB_PATH, "-s", MEMU_ADB_HOST, "pull",
                        f"/data/data/{PACKAGE}/databases/legado.db", db],
                       capture_output=True, timeout=60)
        con = sqlite3.connect(db)
        cur = con.cursor()
        row = cur.execute(
            """select b.name, b.bookUrl, b.origin from books b
            join book_sources s on b.origin=s.bookSourceUrl
            where s.bookSourceType=4 and b.bookUrl in
            (select bookUrl from chapters group by bookUrl having count(*)>2)
            order by (select count(*) from chapters c3 where c3.bookUrl=b.bookUrl) desc limit 1"""
        ).fetchone()
        con.close()
        return row


def launch_player(book_url: str, origin: str):
    # URL 含 & 必须整体单引号（铁证：远端截断 intent extra）
    cmd = ("am start -n %s/io.legado.app.ui.video.VideoPlayerActivity "
           "--es sourceKey '%s' --es bookUrl '%s' --ei sourceType 0"
           % (PACKAGE, origin.replace("'", "'\\''"), book_url.replace("'", "'\\''")))
    sh(cmd)
    time.sleep(14.0)


def read_title(d) -> str:
    xml = d.dump_hierarchy()
    # 沉浸式 tv_video_title / 传统 顶部 第N集
    m = re.search(r'resource-id="%s:id/tv_video_title"[^>]*text="([^"]*)"' % re.escape(PACKAGE), xml)
    if not m:
        m = re.search(r'text="([^"]*)"[^>]*resource-id="%s:id/tv_video_title"' % re.escape(PACKAGE), xml)
    if m:
        return m.group(1)
    # 传统布局顶部 300px 内第N集
    for mm in re.finditer(r'text="(第[^"]{1,4}集)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if int(mm.group(3)) < 300:
            return mm.group(1)
    return ""


def s1_s2_fling_switch(d) -> bool:
    """书源沉浸式上滑=集内下一集 / 下滑=上一集（无队列降级路径）"""
    ok = True
    row = pick_video_book()
    if not row:
        print("[S1][SKIP] 库内无可测视频书")
        return True
    name, book_url, origin = row
    _set_video_layout_mode(0)
    sh("am", "start", "-n", MAIN)
    time.sleep(3.0)
    launch_player(book_url, origin)
    sh("input", "tap", "360", "300")  # 唤出控件
    time.sleep(1.5)
    t0 = read_title(d)
    # 上滑（velocityY<0）= 下一集
    sh("input", "swipe", "360", "620", "360", "180", "120")
    time.sleep(12.0)
    sh("input", "tap", "360", "300")
    time.sleep(1.5)
    t1 = read_title(d)
    # 下滑 = 上一集（切回）
    sh("input", "swipe", "360", "220", "360", "660", "120")
    time.sleep(12.0)
    sh("input", "tap", "360", "300")
    time.sleep(1.5)
    t2 = read_title(d)
    print(f"[S1] 标题: {t0 or '(空)'} -> {t1 or '(空)'} -> {t2 or '(空)'}")
    if not t1 or (t0 and t1 == t0):
        print("[S1][FAIL] 上滑未切换到下一集")
        ok = False
    if not t2 or (t1 and t2 == t1):
        print("[S2][FAIL] 下滑未切回上一集")
        ok = False
    screenshot(d, "s1_fling_switch")
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[S1][FAIL] FATAL={n_fatal}")
        ok = False
    sh("input", "keyevent", "BACK")
    time.sleep(2.0)
    print(f"[S1/S2] {'PASS' if ok else 'FAIL'} (FATAL={n_fatal})")
    return ok


def s3_log_activity(d) -> bool:
    """日志管理中心四 Tab 可达（log-system-upgrade L2 抽样）"""
    ok = True
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)
    act = f"{PACKAGE}/io.legado.app.ui.log.LogActivity"
    r = sh("am", "start", "-n", act)
    out = r.stdout.decode("utf-8", "ignore")
    if "Error" in out:
        print(f"[S3][FAIL] LogActivity 启动失败: {out.strip()[:120]}")
        return False
    time.sleep(3.5)
    xml = d.dump_hierarchy()
    texts = set(t for t in re.findall(r'text="([^"]+)"', xml) if t.strip())
    # 四 Tab 断言（关键词宽松匹配）
    tabs = [k for k in ("应用日志", "崩溃日志", "文件日志", "堆转储") if any(k in t for t in texts)]
    print(f"[S3] activity={act}, 命中Tab={tabs}, texts样本={sorted(list(texts))[:14]}")
    screenshot(d, "s3_log_activity")
    if len(tabs) < 4:
        print("[S3][FAIL] 四 Tab 未全部命中")
        ok = False
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[S3][FAIL] FATAL={n_fatal}")
        ok = False
    sh("input", "keyevent", "BACK")
    print(f"[S3] {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", choices=["all", "s1", "s3"])
    args = ap.parse_args()
    d = u2.connect(MEMU_ADB_HOST)
    sh("logcat", "-c")
    time.sleep(1.0)
    results = []
    if args.scenario in ("all", "s1"):
        results.append(("S1/S2 书源上滑集内切换", s1_s2_fling_switch(d)))
    if args.scenario in ("all", "s3"):
        results.append(("S3 日志管理中心", s3_log_activity(d)))
    print("=== 结果汇总 ===")
    all_pass = True
    for name, passed in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        all_pass = all_pass and passed
    print(f"=== 总判定: {'PASS' if all_pass else 'FAIL'} ===")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
