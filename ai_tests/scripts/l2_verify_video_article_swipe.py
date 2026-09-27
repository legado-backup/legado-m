#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""l2_verify_video_article_swipe.py — 订阅视频「播放器内上下滑切换文章」真机回测。

为什么需要本脚本
    这条能力长期**无有效回测**：旧判据链（`l2_verify_video_player.py --scenario
    swipe_article` 与 `swipe_test_log.py`）依赖**已从源码移除**的 `SwipeTest` /
    `VideoGesture` 临时日志 tag ⇒ `capture_log` 恒 0 行、场景恒「未触发」，于是
    2026-09-27 的回归静默漏过：
      · W1(`8d552b7`) 新增「订阅正文含视频 ⇒ 自动转内置播放器」路由，只传**单篇文章**；
      · W2(`e1f60f7`) 为修「进了播放器但不播」，在单一写入点兜底 `?: listOf(rssArticle)`
        ⇒ `VideoPlay.rssArticles` 退化为 **1 篇**；
      · 播放器侧判定要求 `size > 1`（`VideoFragment.isArticleMode`、
        `VideoPlayerActivity` 的 hasPrev/hasNext）⇒ 沉浸式上下滑 与 传统式上一部下一部
        **同时失效**。
    本脚本改回**现有正式诊断日志**作判据（`VideoRoutesDiag switchToArticle idx=N`），
    不再依赖任何临时埋点。

判据
    ① 前台 Activity 落在 `VideoPlayerActivity`（路由生效）；
    ② 上滑后出现 `switchToArticle idx>=1`（切到下一篇）；
    ③ 下滑后再次出现切换行（回落）；
    ④ FATAL 崩溃数为 0。

场景
    a    - 上滑切下一篇
    b    - 下滑回上一篇
    all  - 全部（默认；a/b 同会话串跑）

用法
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_article_swipe.py
    ... --scenario all --keep-probe      # 保留探针数据（默认验证后清除）
退出码：0=全部通过；1=存在 FAIL；2=环境/设备不可用。
"""
from __future__ import annotations

import argparse
import http.server
import re
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "l2" / "video-article-swipe"
PORT = 8899
BASE = f"http://127.0.0.1:{PORT}"
PROBE_PATH = "/sw/"
ARTICLE_COUNT = 3

DB_REMOTE = f"/data/data/{PACKAGE}/databases/legado.db"
TMP_REMOTE = "/data/local/tmp/l2_video_swipe.db"

READ_RSS_ACT = "io.legado.app.ui.rss.read.ReadRssActivity"
VIDEO_ACT = "io.legado.app.ui.video.VideoPlayerActivity"

# 正文填充：长度需 > MIN_VIDEO_SCAN_LEN(200)，文本中性（不含任何站点信息）
PAD = "正文填充文本用于满足最小扫描长度约束。" * 20


def adb(*args: str, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        [ADB_PATH, "-s", MEMU_ADB_HOST, *args],
        capture_output=True, timeout=timeout,
    )


def adb_text(*args: str) -> str:
    r = adb(*args)
    return (r.stdout or b"").decode("utf-8", "replace")


# ---------------------------------------------------------------- 本地内容服务

def _video_page(idx: int) -> str:
    return (
        "<html><head><title>l2swipe</title></head><body>"
        f'<div id="content"><p>{PAD}</p>'
        f'<video src="{BASE}/media/sw{idx}.mp4" controls></video></div>'
        "</body></html>"
    )


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        m = re.match(r"^/sw/paper(\d+)$", self.path)
        if not m:
            self.send_response(404)
            self.end_headers()
            return
        data = _video_page(int(m.group(1))).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:  # 静音访问日志（避免刷屏/泄路径）
        return


def start_server() -> http.server.ThreadingHTTPServer:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ 设备库种入

def pull_db(work: Path) -> bool:
    ok = False
    for suffix in ("", "-wal", "-shm"):
        r = adb("exec-out", "run-as", PACKAGE, "cat", DB_REMOTE + suffix)
        if r.returncode != 0:
            if suffix == "":
                return False
            continue
        if r.stdout:
            (work / ("legado.db" + suffix)).write_bytes(r.stdout)
            ok = True
    return ok


def push_db(work: Path) -> bool:
    local = work / "legado.db"
    for suffix in ("-wal", "-shm"):
        p = work / ("legado.db" + suffix)
        if p.exists():
            p.unlink()
    if adb("push", str(local), TMP_REMOTE).returncode != 0:
        return False
    if adb("shell", "chmod", "666", TMP_REMOTE).returncode != 0:
        return False
    inner = f"cat {TMP_REMOTE} > {DB_REMOTE}; rm -f {DB_REMOTE}-wal {DB_REMOTE}-shm"
    if adb("shell", f"run-as {PACKAGE} sh -c '{inner}'").returncode != 0:
        return False
    adb("shell", "rm", "-f", TMP_REMOTE)
    out = adb_text("shell", f"run-as {PACKAGE} ls -l {DB_REMOTE}")
    parts = out.split()
    if len(parts) < 5 or not parts[4].isdigit():
        return False
    return int(parts[4]) == local.stat().st_size


def seed(work: Path) -> int:
    """种入 1 个 type=0 源 + N 篇**同源同分类**含视频文章（上下滑切换的前置条件）。"""
    con = sqlite3.connect(work / "legado.db")
    cur = con.cursor()
    cols = cur.execute("PRAGMA table_info(rssSources)").fetchall()
    blank: dict[str, object] = {}
    for _, name, ctype, notnull, dflt, pk in cols:
        if pk or not notnull or dflt is not None:
            continue
        up = (ctype or "").upper()
        blank[name] = 0 if ("INT" in up or "BOOL" in up) else ""

    origin = BASE + PROBE_PATH
    values = dict(blank)
    values.update({
        "sourceUrl": origin,
        "sourceName": "l2swipe",
        "sourceIcon": "",
        "enabled": 1,
        "singleUrl": 0,
        "articleStyle": 0,
        "type": 0,
        "ruleArticles": "",
        "ruleContent": "id.content@html",
        "sortUrl": "",
    })
    names = ", ".join(f"`{k}`" for k in values)
    marks = ", ".join("?" for _ in values)
    cur.execute(f"INSERT OR REPLACE INTO rssSources ({names}) VALUES ({marks})", list(values.values()))

    cur.execute("DELETE FROM rssArticles WHERE origin = ?", (origin,))
    cur.execute("DELETE FROM rssReadRecords WHERE origin = ?", (origin,))
    for idx in range(1, ARTICLE_COUNT + 1):
        # description 必须为空串：非空会短路 loadContent（不走内容规则 ⇒ 视频检测不会执行）
        cur.execute(
            'INSERT OR REPLACE INTO rssArticles '
            '(origin, sort, link, title, pubDate, description, content, image, type, "order", "group", read, durPos) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 0, 0)",
            (
                origin, "", f"{BASE}{PROBE_PATH}paper{idx}", f"swipe{idx:02d}",
                "2026-09-27 12:00", "", "", "",
                (ARTICLE_COUNT - idx + 1) * 1000, "default",
            ),
        )
    con.commit()
    probe = cur.execute(
        "SELECT count(*) FROM rssArticles WHERE origin = ?", (origin,)
    ).fetchone()[0]
    con.close()
    print(f"  · 探针种入：同源文章数={probe}（期望 {ARTICLE_COUNT}）")
    return probe


def cleanup_probe(work: Path) -> None:
    con = sqlite3.connect(work / "legado.db")
    cur = con.cursor()
    for table, column in (
        ("rssArticles", "origin"),
        ("rssReadRecords", "origin"),
        ("rssStars", "origin"),
        ("rssSources", "sourceUrl"),
    ):
        cur.execute(f"DELETE FROM {table} WHERE {column} LIKE ?", (BASE + "%",))
    con.commit()
    con.close()
    print(f"  · 探针已清除：{push_db(work)}")


# ------------------------------------------------------------------ 运行与判据

def resumed_activity() -> str:
    out = adb_text("shell", "dumpsys", "activity", "activities")
    for line in out.splitlines():
        if "ResumedActivity" not in line:
            continue
        m = re.search(r"[A-Za-z0-9_.]+/([A-Za-z0-9_.$]+)", line)
        if m:
            return m.group(1)
    return ""


def switch_indices() -> list[int]:
    """抽取正式日志 `VideoRoutesDiag switchToArticle idx=N` 的 N 序列（不回显原始日志行）。"""
    out = adb_text("logcat", "-d", "-v", "brief")
    return [int(m) for m in re.findall(r"switchToArticle idx=(\d+)", out)]


def crash_count() -> int:
    out = adb_text("logcat", "-d", "-v", "brief")
    return sum(
        1 for line in out.splitlines()
        if "FATAL EXCEPTION" in line or ("AndroidRuntime" in line and "io.legado" in line)
    )


def shot(name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adb("shell", "screencap", "-p", "/sdcard/l2_video_swipe.png")
    adb("pull", "/sdcard/l2_video_swipe.png", str(OUT_DIR / f"{name}.png"))


def swipe(direction: str, times: int = 1, duration: int = 300) -> None:
    # 竖屏 720×1280：上滑=手指由下向上（切下一篇）；下滑反之
    for _ in range(times):
        if direction == "up":
            adb("shell", "input", "swipe", "360", "1000", "360", "300", str(duration))
        else:
            adb("shell", "input", "swipe", "360", "300", "360", "1000", str(duration))
        time.sleep(2.5)


def main() -> int:
    ap = argparse.ArgumentParser(description="订阅视频播放器内上下滑切换文章 真机回测")
    ap.add_argument("--scenario", default="all", choices=["a", "b", "all"],
                    help="a=上滑切下一篇；b=下滑回上一篇；all=两者串跑")
    ap.add_argument("--wait", type=float, default=6.0, help="启动阅读页后等待秒数")
    ap.add_argument("--keep-probe", action="store_true", help="保留探针数据（默认验证后清除）")
    args = ap.parse_args()

    work = ROOT / ".temp" / "video-swipe-probe"
    work.mkdir(parents=True, exist_ok=True)

    if adb("shell", "echo", "ok").returncode != 0:
        print("[FATAL] 设备不可用")
        return 2

    srv = start_server()
    adb("reverse", f"tcp:{PORT}", f"tcp:{PORT}")
    if f"tcp:{PORT}" not in adb_text("reverse", "--list"):
        print("[FATAL] adb reverse 未建立（设备不支持回环转发）")
        srv.shutdown()
        return 2
    print(f"  · 本地内容服务已启动 :{PORT}，adb reverse 已建立")

    adb("shell", "am", "force-stop", PACKAGE)
    if not pull_db(work):
        print("[FATAL] 设备库拉取失败（run-as 不可用？）")
        srv.shutdown()
        return 2
    if seed(work) != ARTICLE_COUNT:
        print("[FATAL] 探针写入不完整")
        srv.shutdown()
        return 2
    if not push_db(work):
        print("[FATAL] 探针回写失败")
        srv.shutdown()
        return 2

    # 从阅读页打开第 1 篇（正文含视频 ⇒ 自动转内置播放器）
    adb("shell", "am", "force-stop", PACKAGE)
    adb("logcat", "-c")
    adb(
        "shell", "am", "start", "-n", f"{PACKAGE}/{READ_RSS_ACT}",
        "--es", "origin", BASE + PROBE_PATH,
        "--es", "link", f"{BASE}{PROBE_PATH}paper1",
        "--es", "title", "swipe01",
    )
    time.sleep(args.wait)

    results: list[tuple[str, bool, str]] = []
    act = resumed_activity()
    routed = act.endswith(VIDEO_ACT)
    results.append(("路由", routed, f"前台={act.split('.')[-1] or '?'}"))
    if not routed:
        print(f"  [FAIL] 路由：前台={act.split('.')[-1] or '?'}（期望 VideoPlayerActivity）")
        if not args.keep_probe:
            cleanup_probe(work)
        srv.shutdown()
        return 1

    adb("logcat", "-c")
    before = switch_indices()
    swipe("up", times=2)
    after_up = switch_indices()
    up_ok = len(after_up) > len(before) or any(i >= 1 for i in after_up)
    results.append(("上滑切下一篇", up_ok, f"切换行={after_up}"))

    if args.scenario in ("b", "all"):
        adb("logcat", "-c")
        swipe("down", times=2)
        after_down = switch_indices()
        down_ok = len(after_down) > 0
        results.append(("下滑回上一篇", down_ok, f"切换行={after_down}"))

    crashes = crash_count()
    results.append(("崩溃", crashes == 0, f"FATAL={crashes}"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shot("final")

    print("\n" + "-" * 70)
    failed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{status}] {name}：{detail}")
    print("-" * 70)
    print(f"  结论：{'全部通过' if failed == 0 else f'{failed} 项未通过'}；图落盘 {OUT_DIR}")

    if not args.keep_probe:
        cleanup_probe(work)
    srv.shutdown()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())