#!/usr/bin/env python3
"""baseline_shots.py — UI 组件渲染基线截图（ui-subpage-optimization A2.1.1）

目的：为 A2.2「组件收敛」（确认弹框 4→1 入口、卡片 3 套划界）与 A3「主题链收敛」
提供**改动前对照基线**。覆盖 = 四族代表页面 × 明暗 × accent 三色系。

⚠️ 重采样约定：A3 主题链（danger 色 / token 门面 / 撞色阈值）会改变弹框与文字观感，
A3 完成后必须重跑本脚本一次（`--out output/ui-baseline/after-a3`），原基线仅作「A3 前」存档。

⚠️ 不用 `@Preview`：`AppConfig.kt` 为 `object`，属性初始化器直调 splitties `appCtx.getPref*`；
Layoutlib 不实例化 ContentProvider → `@Preview` 渲染即崩（第四批实证）。故走真机截图。

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/baseline_shots.py [选项]
选项：
    --install            先跑 quick_build_install.py 装包（否则要求已装）
    --themes  day,night  明暗矩阵（默认 day,night）
    --accents default,purple,teal   accent 色系矩阵（默认 default,purple,teal）
    --pages   topbar,list,settings,theme  四族代表页（默认全跑）
    --tap     route:desc=更多        路由追加点击（可多次；弹框/菜单族需要）
    --out     output/ui-baseline     截图落盘根目录
    --dry-run            只打印矩阵与路由，不碰设备/prefs
退出码：0=全部截图成功，1=存在失败或设备不可用
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import uiautomator2 as u2

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREFS = f"/data/data/{PACKAGE}/shared_prefs/{PACKAGE}_preferences.xml"
TMP_REMOTE = "/data/local/tmp/prefs_baseline.xml"

# prefs 键（源码核实：PreferKey.kt:7 themeMode / :273 cPrimary / :274 cAccent / :281 cNPrimary / :282 cNAccent）
# ⚠️ 类型口径（源码核实）：`themeMode` 走 `getPrefString`（值 "0"跟随系统/"1"日/"2"夜/"3"墨水屏）→ **string**；
#    四个颜色键走 `getPrefInt`（ARGB int）→ **int**。类型写错会静默回落默认值。
K_THEME_MODE = ("themeMode", "string")
K_DAY_PRIMARY = ("colorPrimary", "int")
K_DAY_ACCENT = ("colorAccent", "int")
K_NIGHT_PRIMARY = ("colorPrimaryNight", "int")
K_NIGHT_ACCENT = ("colorAccentNight", "int")
PREF_KEYS = (K_THEME_MODE, K_DAY_PRIMARY, K_DAY_ACCENT, K_NIGHT_PRIMARY, K_NIGHT_ACCENT)
KIND_OF = {key: kind for key, kind in PREF_KEYS}
COLOR_KEYS = (K_DAY_PRIMARY, K_DAY_ACCENT, K_NIGHT_PRIMARY, K_NIGHT_ACCENT)

# 四族代表页面（Activity 类名经 AndroidManifest 核实存在）
# ⚠️ 必须用**全限定类名**：`am start -n <applicationId>/.ui.X` 的相对形式会以 applicationId 为基准解析
#    成 `io.legado.miss.app.debug.ui.X`（不存在）；Java 包名恒为 `io.legado.app`，不受 applicationIdSuffix 影响。
ROUTES: dict[str, dict[str, str]] = {
    "topbar": {
        "family": "顶栏族（GlassTopAppBar 管理族分支）",
        "activity": "io.legado.app.ui.book.source.manage.BookSourceActivity",
    },
    "list": {
        "family": "卡片/列表/根背景族（Compose 直载列表）",
        "activity": "io.legado.app.ui.book.cache.CacheActivity",
    },
    "settings": {
        "family": "设置族（配置中心）",
        "activity": "io.legado.app.ui.config.ConfigActivity",
    },
    "theme": {
        "family": "弹框族（主题管理，可触发确认弹框）",
        "activity": "io.legado.app.ui.config.ThemeManageActivity",
    },
}

# accent 色系矩阵：日/夜各 (primary, accent) 十六进制；default = 不改写 prefs（沿用现有）
ACCENTS: dict[str, dict[str, tuple[str, str]]] = {
    "default": {},
    "purple": {"day": ("#6A1B9A", "#AB47BC"), "night": ("#B39DDB", "#CE93D8")},
    "teal": {"day": ("#00695C", "#26A69A"), "night": ("#80CBC4", "#4DB6AC")},
}
THEME_MODE = {"day": "1", "night": "2"}


def adb(*args: str, timeout: int = 30, binary: bool = False):
    return subprocess.run(
        [ADB_PATH, "-s", MEMU_ADB_HOST, *args],
        capture_output=True, timeout=timeout,
        **({} if binary else {"text": True, "encoding": "utf-8", "errors": "ignore"}),
    )


def device_online() -> bool:
    out = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True).stdout
    return MEMU_ADB_HOST in out and "device" in out


def pid_alive() -> bool:
    r = adb("shell", f"pidof {PACKAGE}")
    return bool((r.stdout or "").strip())


def force_stop_and_wait(timeout: float = 12.0) -> bool:
    """force-stop 后轮询确认进程已死（SOP 陷阱 7①：进程可能被自动拉起并回写 prefs 快照）。"""
    adb("shell", "am", "force-stop", PACKAGE)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not pid_alive():
            return True
        adb("shell", "am", "force-stop", PACKAGE)
        time.sleep(0.6)
    return False


def read_prefs() -> str:
    r = adb("exec-out", "cat", PREFS)
    xml = r.stdout or ""
    if not xml.strip():
        raise RuntimeError(f"无法读取 prefs：{PREFS}")
    idx = xml.rfind("</map>")
    if idx != -1:
        xml = xml[: idx + len("</map>")]
    return xml


def _re_int(key: str) -> re.Pattern[str]:
    return re.compile(rf'<int name="{re.escape(key)}" value="-?\d+"\s*/>')


def _re_str(key: str) -> re.Pattern[str]:
    return re.compile(rf'<string name="{re.escape(key)}">.*?</string>')


def get_pref(xml: str, key: str) -> str | None:
    m = re.search(rf'<int name="{re.escape(key)}" value="(-?\d+)"\s*/>', xml) or re.search(
        rf'<string name="{re.escape(key)}">(.*?)</string>', xml
    )
    return m.group(1) if m else None


def set_pref(xml: str, key: str, value: str, kind: str) -> str:
    """写 prefs：**先清空该键所有节点**（防同键 int/string 双节点，读侧行为未定义）再插入单节点。

    注：替换一律走「函数式替换」而非字符串直接替换（SOP 陷阱 7③：替换串中的反斜杠会被转义处理），
    本处值为整数/纯数字虽无反斜杠，仍统一走函数式以固化纪律。
    """
    xml = _re_int(key).sub("", xml)
    xml = _re_str(key).sub("", xml)
    node = (
        f'<int name="{key}" value="{value}" />'
        if kind == "int"
        else f'<string name="{key}">{value}</string>'
    )
    return xml.replace("</map>", f"    {node}\n</map>")


def write_prefs(xml: str) -> bool:
    """回写 prefs 并回读校验（SOP：改 prefs 必须回读）。

    通道：本地写文件 → `adb push` → 设备端**单参数** `cat X > Y`（SOP 陷阱 8：多参数会被按空格
    拆散致 `> file` 把目标截断为 0 字节）。push/cat 的 stderr 一律回显，防静默失败。
    """
    local = ROOT / "ai_tests" / "reports" / "prefs_baseline.xml"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(xml, encoding="utf-8")
    r_push = adb("push", str(local), TMP_REMOTE)
    r_cat = adb("shell", f"cat {TMP_REMOTE} > {PREFS}")
    err = ((r_push.stderr or "") + (r_cat.stderr or "")).strip()
    if err:
        print(f"  !! prefs 写入通道告警：{err[:200]}")
    back = adb("exec-out", "cat", PREFS).stdout or ""
    return back.rstrip().endswith("</map>") and len(back) >= len(xml) * 0.9


def hex_to_argb_int(hex_color: str) -> int:
    """#RRGGBB → 带不透明 alpha 的有符号 int32（prefs 存 ARGB int）。"""
    v = int(hex_color.lstrip("#"), 16) | 0xFF000000
    return v - (1 << 32) if v >= (1 << 31) else v


def apply_matrix_prefs(theme: str, accent: str, snapshot: dict[str, str]) -> bool:
    """按 (明暗, accent) 改写 prefs；返回是否成功。"""
    xml = read_prefs()
    xml = set_pref(xml, K_THEME_MODE[0], str(THEME_MODE[theme]), K_THEME_MODE[1])
    preset = ACCENTS[accent]
    if preset:
        values = {
            K_DAY_PRIMARY: preset["day"][0],
            K_DAY_ACCENT: preset["day"][1],
            K_NIGHT_PRIMARY: preset["night"][0],
            K_NIGHT_ACCENT: preset["night"][1],
        }
        for (key, kind), hex_color in values.items():
            xml = set_pref(xml, key, str(hex_to_argb_int(hex_color)), kind)
    else:
        # default 色系 = 沿用现有配色：只还原**颜色键**，不得回写 themeMode
        # （否则会把本函数刚设置的明暗值覆盖回快照值，导致明暗矩阵静默失效）
        for key, kind in COLOR_KEYS:
            val = snapshot.get(key)
            if val is not None:
                xml = set_pref(xml, key, val, kind)
    if not write_prefs(xml):
        print(f"  !! prefs 回写校验失败（theme={theme} accent={accent}）")
        return False
    # 回读关键键（SOP：改 prefs 必须回读确认，防「写了没进去」与「启动被回写覆盖」两类静默失败）
    back = read_prefs()
    got_mode = get_pref(back, K_THEME_MODE[0])
    if got_mode != str(THEME_MODE[theme]):
        print(f"  !! themeMode 回读不符：期望 {THEME_MODE[theme]} 实得 {got_mode}")
        return False
    return True


def snapshot_prefs() -> dict[str, str]:
    xml = read_prefs()
    return {key: get_pref(xml, key) for key, _ in PREF_KEYS}


def restore_prefs(snapshot: dict[str, str]) -> None:
    try:
        xml = read_prefs()
        for key, kind in PREF_KEYS:
            v = snapshot[key]
            if v is not None:
                xml = set_pref(xml, key, v, kind)
        force_stop_and_wait()
        write_prefs(xml)
        print("已还原 prefs 快照")
    except Exception as e:  # noqa: BLE001
        print(f"!! prefs 还原失败（需人工检查）：{e}")


def launch(activity: str) -> bool:
    """启动目标 Activity（严格判定：必须出现 `Starting:` 且无 Error/does not exist）。"""
    r = adb("shell", "am", "start", "-n", f"{PACKAGE}/{activity}")
    out = (r.stdout or "").strip()
    if "Starting:" not in out or "Error" in out or "does not exist" in out:
        print(f"  !! am start 失败：{out[:160]}")
        return False
    return True


def current_activity() -> str:
    """当前前台 Activity（多口径兜底，适配不同 Android 版本）。"""
    r = adb("shell", "dumpsys activity activities")
    out = r.stdout or ""
    for pat in (r"mResumedActivity[^\n]*?([\w.]+/[\w.$]+)", r"mFocusedActivity[^\n]*?([\w.]+/[\w.$]+)"):
        m = re.search(pat, out)
        if m:
            return m.group(1)
    r2 = adb("shell", "dumpsys window")
    m = re.search(r"mCurrentFocus[^\n]*?([\w.]+/[\w.$]+)", r2.stdout or "")
    return m.group(1) if m else ""


def wait_foreground(activity: str, timeout: float = 20.0) -> bool:
    """等待目标 Activity 真正到前台（防「App 未起完就截图」截到桌面/启动页）。"""
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = current_activity()
        if activity.split("/")[-1] in last:
            time.sleep(1.5)  # 首帧后留出渲染时间
            return True
        time.sleep(0.8)
    print(f"  !! 等待前台超时，当前={last or '未知'}（期望 {activity}）")
    return False


def tap_selector(selector: str) -> bool:
    """selector 形态：desc=更多 / text=日志。走 dump_hierarchy 正则取 bounds 后坐标点击。"""
    kind, _, value = selector.partition("=")
    attr = {"desc": "content-desc", "text": "text"}.get(kind)
    if not attr:
        print(f"  !! 不支持的 selector：{selector}")
        return False
    r = adb("shell", "uiautomator", "dump", "/sdcard/_ui.xml")
    if "dumped" not in (r.stdout or ""):
        return False
    xml = adb("exec-out", "cat", "/sdcard/_ui.xml").stdout or ""
    m = re.search(
        rf'<node[^>]*{attr}="{re.escape(value)}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        xml,
    )
    if not m:
        print(f"  !! 未找到节点：{selector}")
        return False
    x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
    return True


_DEV = None


def device():
    """u2 设备句柄（懒连接）。"""
    global _DEV
    if _DEV is None:
        _DEV = u2.connect(MEMU_ADB_HOST)
    return _DEV


def _grab_u2() -> bytes | None:
    """u2（atx-agent）通道取帧。"""
    try:
        img = device().screenshot()
    except Exception as e:  # noqa: BLE001
        print(f"  !! 截图异常：{e}")
        return None
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _grab_screencap() -> bytes | None:
    """`adb exec-out screencap -p` 兜底通道（A5.8 新增）。

    二进制安全：必须经 subprocess 管道读 stdout；**禁用 PowerShell `>` 重定向**
    （会按文本编码写坏 PNG → 「Unknown image format」）。
    存在意义：u2 通道在 MEmu 上偶发持续黑帧/陈旧帧（AD-25 渲染管线故障）时提供第二通道。
    """
    try:
        out = subprocess.run(
            [ADB_PATH, "-s", MEMU_ADB_HOST, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=30
        ).stdout
        return out or None
    except Exception as e:  # noqa: BLE001
        print(f"  !! screencap 异常：{e}")
        return None


def shoot(path: Path, seen: set[bytes] | None = None, retries: int = 6) -> bool:
    """截图：u2 主通道 + `screencap` 兜底，连拍取稳定帧。

    MEmu 上两通道各有失效场景：u2 偶发持续黑帧/陈旧帧（AD-25），
    `adb exec-out screencap` 亦曾被记录返回陈旧帧（实测两主题同 731441 字节）。
    故双通道轮换 + 三重校验：①字节 ≥20000（黑帧特征值，SOP u2 陷阱 7）
    ②**不与本次运行任何已落盘截图重复**（防截到桌面/上一页的陈旧帧，假基线主因）
    ③连续两帧字节一致（画面已稳定）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    prev: bytes | None = None
    for attempt in range(retries):
        data = _grab_u2() if attempt % 2 == 0 else _grab_screencap()
        if data is None:
            time.sleep(1.0)
            continue
        if len(data) < 20000:  # 黑帧特征值（SOP u2 陷阱 7）
            print(f"  !! 疑似黑帧（{len(data)} 字节，通道={'u2' if attempt % 2 == 0 else 'screencap'}），重试")
            time.sleep(1.2)
            continue
        if seen is not None and data in seen:
            print(f"  !! 与本次运行已有截图重复（陈旧帧），重试")
            time.sleep(1.5)
            continue
        if prev is not None and prev == data:
            path.write_bytes(data)
            if seen is not None:
                seen.add(data)
            return True
        prev = data
        time.sleep(1.0)
    if prev is not None and (seen is None or prev not in seen):
        print("  !! 未取得稳定双帧，落盘最后一帧")
        path.write_bytes(prev)
        seen.add(prev) if seen is not None else None
        return True
    print("  !! 截图失败：始终为黑帧或陈旧帧")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--themes", default="day,night")
    ap.add_argument("--accents", default="default,purple,teal")
    ap.add_argument("--pages", default="topbar,list,settings,theme")
    ap.add_argument("--tap", action="append", default=[], help="route:selector，如 theme:desc=更多")
    ap.add_argument("--out", default="output/ui-baseline")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    themes = [t for t in args.themes.split(",") if t]
    accents = [a for a in args.accents.split(",") if a]
    pages = [p for p in args.pages.split(",") if p]
    unknown = [p for p in pages if p not in ROUTES] + [a for a in accents if a not in ACCENTS]
    if unknown:
        print(f"!! 未知页/色系：{unknown}")
        return 1

    taps: dict[str, list[str]] = {}
    for spec in args.tap:
        route, _, selector = spec.partition(":")
        taps.setdefault(route, []).append(selector)

    print(f"[矩阵] 页 {pages} × 明暗 {themes} × accent {accents} = {len(pages) * len(themes) * len(accents)} 张")
    for p in pages:
        print(f"  - {p}: {ROUTES[p]['family']} → {ROUTES[p]['activity']}")
    if args.dry_run:
        return 0

    if not device_online():
        print(f"!! 设备不可用（{MEMU_ADB_HOST}）。按 AD-25：必须视觉判读项阻塞等待设备恢复，不得跳过")
        return 1
    if args.install:
        print("== 装包（quick_build_install.py）==")
        rc = subprocess.run(
            [sys.executable, str(ROOT / "ai_tests" / "scripts" / "quick_build_install.py")],
            cwd=ROOT,
        ).returncode
        if rc != 0:
            print("!! 装包失败")
            return 1

    snapshot = snapshot_prefs()
    print(f"[快照] {snapshot}")
    out_root = ROOT / args.out
    fails: list[str] = []
    seen: set[bytes] = set()

    try:
        for theme in themes:
            for accent in accents:
                if not force_stop_and_wait():
                    print(f"!! 进程未能停止，跳过 theme={theme} accent={accent}")
                    fails.append(f"{theme}/{accent}:进程未停")
                    continue
                if not apply_matrix_prefs(theme, accent, snapshot):
                    fails.append(f"{theme}/{accent}:prefs")
                    continue
                for page in pages:
                    activity = ROUTES[page]["activity"]
                    if not launch(activity):
                        fails.append(f"{theme}/{accent}/{page}:启动失败")
                        continue
                    if not wait_foreground(activity):
                        fails.append(f"{theme}/{accent}/{page}:未到前台（可能截到桌面）")
                        continue
                    # 启动后回读：检测「进程启动时被回写覆盖 prefs」类静默失败
                    mode_now = get_pref(read_prefs(), K_THEME_MODE[0])
                    if mode_now != str(THEME_MODE[theme]):
                        print(f"  !! 启动后 themeMode 被改为 {mode_now}（期望 {THEME_MODE[theme]}）")
                        fails.append(f"{theme}/{accent}/{page}:启动后 themeMode 被覆盖为 {mode_now}")
                        continue
                    for selector in taps.get(page, []):
                        tap_selector(selector)
                        time.sleep(1.5)
                    dest = out_root / theme / accent / f"{page}.png"
                    if shoot(dest, seen):
                        print(f"  ✓ {theme}/{accent}/{page} → {dest.relative_to(ROOT)}")
                    else:
                        fails.append(f"{theme}/{accent}/{page}:截图")
                    adb("shell", "am", "force-stop", PACKAGE)
    finally:
        restore_prefs(snapshot)

    # 跨主题自检（防「截到同一帧」假基线）：同一页各明暗截图字节全同 ⇒ 主题未生效或截图陈旧
    for page in pages:
        shots = {
            (t, a): out_root / t / a / f"{page}.png"
            for t in themes for a in accents
        }
        present = {k: p.read_bytes() for k, p in shots.items() if p.exists()}
        if len(present) >= 2 and len(set(present.values())) == 1:
            fails.append(f"{page}:明暗/accent 截图字节全同（主题未生效或截图陈旧）")

    print(f"\n[{'FAIL' if fails else 'PASS'}] 失败 {len(fails)} 项")
    for f in fails:
        print(f"  - {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
