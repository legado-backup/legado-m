"""l2_verify_image_enhance_governance.py — enhance-switch-governance-fix L2 验证（v2）

分层验证策略（MEmu 老 Android 镜像对 Compose 无障碍不可见——设置面板行 u2/CLI dump 均盲）：
  [自动] T1 效果链正向：prefs 置 enhanceEnabled=true+锐化3+降噪2 → 重启 → 真实播放 →
         logcat 断言 buildEffects on: sharpen=3 denoise=2 且 applyImageEnhanceEffects size=2
  [自动] T3 守卫反向：prefs 置 enhanceEnabled=false → 重启 → 真实播放 →
         断言 applyImageEnhanceEffects size=0 且无 buildEffects on（AD-01a onPrepared 重建路径守卫）
  [自动] T6 单测由 OkHttpStreamFetcherBoundedReadTest 承担（gradlew testAppDebugUnitTest）
  [手动] T2 播放中面板关开关立即清空 / T4 滑条联动自定义 / T5 拖动流畅 / T7 预设回归
         —— Compose 面板在模拟器不可自动化，输出用户真机手动验证清单

全程 uiautomator2 导航；禁止 CLI uiautomator dump（与 u2 UiAutomation 注册互斥，FATAL 铁证）。
脱敏：只输出技术信息，不输出源名称/URL/业务文本。
"""
import argparse
import base64
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uiautomator2 as u2

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

HOST = MEMU_ADB_HOST
PREFS_REMOTE = f"/data/data/{PACKAGE}/shared_prefs/video_config.xml"
MAIN = f"{PACKAGE}/io.legado.app.ui.main.MainActivity"
SOURCE_KEYWORD = "内置播放器"  # 源列表文本模糊匹配（仅脚本内匹配，禁止打印）


def sh(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh_su(cmd: str, timeout=20):
    return sh("su -c '%s'" % cmd, timeout=timeout)


def read_prefs() -> dict:
    for attempt in range(3):
        r = sh_su(f"base64 {PREFS_REMOTE} 2>/dev/null")
        raw = r.stdout.decode("utf-8", errors="ignore").strip()
        if raw:
            try:
                xml = base64.b64decode(raw).decode("utf-8", errors="ignore")
                prefs = {}
                for m in re.finditer(r'<\w+\s+name="([^"]+)"\s+value="([^"]*)"', xml):
                    prefs[m.group(1)] = m.group(2)
                return prefs
            except Exception:
                pass
        time.sleep(1.5)
    return {}


def set_video_pref(name: str, value: str, vtype: str = "boolean") -> bool:
    """force-stop 后 su 改 video_config.xml 指定键（存在改值/缺失插入），cat 覆写保留属主"""
    sh("am", "force-stop", PACKAGE)
    time.sleep(1.5)
    raw = ""
    for _ in range(3):
        r = sh_su(f"base64 {PREFS_REMOTE} 2>/dev/null")
        raw = r.stdout.decode("utf-8", errors="ignore").strip()
        if raw:
            break
        time.sleep(1.0)
    if not raw:
        print("[WARN] video_config unreadable")
        return False
    try:
        xml = base64.b64decode(raw).decode("utf-8", errors="ignore")
    except Exception:
        return False
    tag = vtype
    pat = re.compile(r'(<%s name="%s" value=")[^"]*(")' % (tag, name))
    if pat.search(xml):
        xml = pat.sub(r"\g<1>%s\g<2>" % value, xml)
    else:
        xml = xml.replace("</map>", '<%s name="%s" value="%s" /></map>' % (tag, name, value))
    local = Path(__file__).parent.parent / "reports" / "video_config_tmp.xml"
    local.parent.mkdir(exist_ok=True)
    local.write_text(xml, encoding="utf-8")
    subprocess.run([ADB_PATH, "-s", HOST, "push", str(local), "/sdcard/vc_tmp.xml"],
                   capture_output=True, timeout=30)
    sh_su(f"cat /sdcard/vc_tmp.xml > {PREFS_REMOTE}")
    sh("am", "start", "-n", MAIN)
    time.sleep(3.0)
    # 回读校验
    got = read_prefs().get(name)
    ok = got == value
    print(f"[PREF] {name}={got}(期望{value}) {'OK' if ok else 'MISMATCH'}")
    return ok


def crash_count() -> int:
    r = sh("logcat", "-d", "-b", "crash", timeout=15)
    return len(re.findall(r"FATAL EXCEPTION", r.stdout.decode("utf-8", errors="ignore")))


def clear_log():
    sh("logcat", "-c", timeout=10)
    time.sleep(0.5)


def enhance_log() -> str:
    r = sh("logcat", "-d", "-s", "EnhanceGov", timeout=15)
    return r.stdout.decode("utf-8", errors="ignore")


def is_video_activity() -> bool:
    r = sh("dumpsys", "activity", "activities", timeout=15)
    out = r.stdout.decode("utf-8", errors="ignore")
    for line in out.splitlines():
        if "mResumedActivity" in line:
            return "VideoPlayer" in line
    return False


def screen_size():
    r = sh("wm", "size", timeout=10)
    m = re.search(r"(\d+)x(\d+)", r.stdout.decode("utf-8", errors="ignore"))
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 1920)


def enter_player(d) -> bool:
    """导航：MainActivity → 订阅 tab → 已知可用视频源 → 文章 → VideoPlayer"""
    sh("am", "start", "-n", MAIN)
    time.sleep(3.0)
    w, h = screen_size()
    try:
        tab = d(resourceId=f"{PACKAGE}:id/menu_rss")
        if not tab.exists:
            return False
        tab.click()
        time.sleep(2.5)
    except Exception as e:
        print(f"[DIAG] rss tab exc={type(e).__name__}")
        return False
    try:
        src = d(textContains=SOURCE_KEYWORD)
        if not src.exists:
            print("[DIAG] known video source not found")
            return False
        src.click()
        time.sleep(6.0)
    except Exception as e:
        print(f"[DIAG] source click exc={type(e).__name__}")
        return False
    # 分类页（WebView，u2 可读其无障碍文本）→ 逐候选分类点击 → 文章列表（原生 rv）→ 文章
    for cat in ("电影", "最新", "剧集", "动漫", "综艺"):
        try:
            node = d(text=cat)
            if node.exists:
                node.click()
                time.sleep(10.0)
                break
        except Exception:
            pass
    if is_video_activity():
        return True
    # 文章列表：点可点击子项（跳过分类页残留），多轮重试
    for attempt in range(6):
        if is_video_activity():
            return True
        try:
            rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
            if rv.exists:
                items = rv.child(className="android.view.ViewGroup", clickable="true")
                if items.count > attempt:
                    items[attempt].click()
                    time.sleep(12.0)
                    if is_video_activity():
                        return True
        except Exception as e:
            print(f"[DIAG] nav exc={type(e).__name__}")
        d.swipe(w // 2, int(h * 0.7), w // 2, int(h * 0.4), duration=0.4)
        time.sleep(3.0)
    return is_video_activity()

PLAY_URLS = [
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "http://vjs.zencdn.net/v/oceans.mp4",
]


def play_direct(d, wait_s=40) -> bool:
    """am start 直启 VideoPlayerActivity 播公共测试 mp4（绕开 WebView 源导航），轮询等待 prepare"""
    for url in PLAY_URLS:
        clear_log()
        sh("am", "start", "-n", f"{PACKAGE}/io.legado.app.ui.video.VideoPlayerActivity",
           "--es", "videoUrl", url, "--es", "videoTitle", "GovTest",
           "--ez", "isNew", "true")
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if "applyImageEnhanceEffects" in enhance_log():
                time.sleep(2.0)
                return True
            time.sleep(2.0)
        sh("input", "keyevent", "4")
        time.sleep(2.0)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-idx", type=int, default=0)
    args = ap.parse_args()

    subprocess.run([ADB_PATH, "connect", HOST], capture_output=True, timeout=15)
    time.sleep(1.0)
    d = u2.connect(HOST)
    results = []
    print(f"[INFO] device={HOST} package={PACKAGE}")
    t0 = crash_count()

    # ===== T1 [自动] 效果链正向：开+锐化3+降噪2 → 真实播放 size=2 =====
    try:
        pref_ok = (set_video_pref("enhanceEnabled", "true")
                   and set_video_pref("enhanceSharpenLevel", "3", "int")
                   and set_video_pref("enhanceDenoiseLevel", "2", "int"))
        clear_log()
        played = play_direct(d)
        time.sleep(3.0)
        log = enhance_log()
        ev1 = re.findall(r"buildEffects on: sharpen=3 denoise=2.*", log)
        ev2 = re.findall(r"applyImageEnhanceEffects size=2\b.*", log)
        t1 = pref_ok and played and bool(ev1) and bool(ev2)
        results.append(("T1 [自动] 开+锐化3+降噪2→真实播放效果链", t1,
                        f"pref={pref_ok} played={played} ev1={ev1[:1]} ev2={ev2[:1]}"))
    except Exception as e:
        results.append(("T1 [自动] 效果链正向", False, f"exc={type(e).__name__}"))

    # ===== T3 [自动] 守卫反向：关 → 真实播放 size=0 且无 buildEffects on =====
    try:
        pref_ok = set_video_pref("enhanceEnabled", "false")
        clear_log()
        played = play_direct(d)
        time.sleep(3.0)
        log = enhance_log()
        ev0 = re.findall(r"applyImageEnhanceEffects size=0\b.*", log)
        n_build = len(re.findall(r"buildEffects on:", log))
        t3 = pref_ok and played and bool(ev0) and n_build == 0
        results.append(("T3 [自动] 关→重建播放守卫（size=0 无注入）", t3,
                        f"pref={pref_ok} played={played} size0={len(ev0)} build_on={n_build}"))
    except Exception as e:
        results.append(("T3 [自动] 守卫反向", False, f"exc={type(e).__name__}"))

    # ===== T2/T4/T5/T7 [手动] Compose 面板在 MEmu 无障碍不可见，输出真机手动清单 =====
    manual = [
        ("T2 [手动] 播放中开面板关「启用画质增强」→ 画面立即去锐化/降噪（AD-01b）"),
        ("T4 [手动] 选预设「护眼」后拖任一滑条 → 预设标签变「自定义」，重进面板选中项正确（AD-02）"),
        ("T5 [手动] 连续快速拖滑条 3s → 无掉帧/闪烁（AD-04 短路，logcat 有 shortCircuit=true）"),
        ("T7 [手动] 预设「鲜艳」持久化；拖色温回「自定义」；开关开合一次无异常"),
    ]
    for m in manual:
        results.append((m, True, "SKIP→用户真机手动验证（MEmu Compose 无障碍盲区）"))

    final_crash = crash_count() - t0
    auto_fail = any(not ok for name, ok, _ in results if "[自动]" in name)
    print("\n===== enhance-switch-governance-fix L2 汇总 =====")
    for name, ok, note in results:
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {name} | {note}")
    print(f"[INFO] 自动项 FATAL 增量 = {final_crash}")
    print("[INFO] 手动清单已输出（T2/T4/T5/T7 面板项真机验证）")
    sys.exit(0 if not auto_fail and final_crash == 0 else 1)


if __name__ == "__main__":
    main()
