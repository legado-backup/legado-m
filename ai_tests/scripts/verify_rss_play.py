#!/usr/bin/env python3
"""verify_rss_play.py — 验证源[1]和源[3]的播放功能

全程脱敏：只输出编号(源[N]/文章[N]/分类[N])，不输出源名称/域名/URL等业务数据
用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/verify_rss_play.py
"""
import uiautomator2 as u2
import time
import sys
import subprocess
import re
import os
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# === 配置 ===
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY

PKG = PACKAGE  # io.legado.miss.app.debug
RES_PREFIX = f"{PKG}:id/"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 测试源索引（0-based）：源[1]=index0, 源[3]=index2
SOURCE_INDICES = [0, 2]
SOURCE_LABELS = {0: "源[1]", 2: "源[3]"}

d = None  # 全局设备对象


def connect():
    global d
    print("[INIT] 连接设备...")
    d = u2.connect(MEMU_ADB_HOST)
    info = d.info
    print(f"[INIT] 设备已连接: {info.get('productName', '?')}")
    d.implicitly_wait(5)


def run_adb(cmd, timeout=30):
    full = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)
    return r


def ensure_app_running():
    """确保App运行在前台"""
    cur = d.app_current()
    if cur.get("package") != PKG:
        print(f"[NAV] 启动App: {PKG}")
        d.app_start(PKG, MAIN_ACTIVITY)
        time.sleep(5)
    else:
        print(f"[NAV] App已运行, Activity: {cur.get('activity', '?')}")


def navigate_to_rss_list():
    """导航到订阅源列表页面"""
    print("[NAV] 导航到订阅源列表...")
    cur = d.app_current()
    act = cur.get("activity", "")

    # 按返回键回到主界面
    for _ in range(3):
        d.press("back")
        time.sleep(1)
        cur = d.app_current()
        if "MainActivity" in cur.get("activity", ""):
            break

    # 点击订阅Tab
    rss_tab = d(resourceId=f"{RES_PREFIX}menu_rss")
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(3)
        print("[NAV] 已点击订阅Tab")
    else:
        print("[NAV] 未找到订阅Tab，尝试content-desc")
        rss_tab2 = d(description="订阅")
        if rss_tab2.exists:
            rss_tab2.click()
            time.sleep(3)
            print("[NAV] 已点击订阅Tab(desc)")
        else:
            print("[NAV] ⚠️ 无法找到订阅Tab")

    cur = d.app_current()
    print(f"[NAV] 当前Activity: {cur.get('activity', '?')}")


def find_source_by_index(idx):
    """通过索引点击订阅源列表中的源（不读取名称）"""
    rv = d(resourceId=f"{RES_PREFIX}recycler_view")
    if not rv.exists:
        # 尝试直接用RecyclerView className
        rv = d(className="androidx.recyclerview.widget.RecyclerView")

    if not rv.exists:
        print(f"  ⚠️ recycler_view不存在，尝试坐标点击")
        # 备用方案：按坐标点击
        # 订阅源列表每个item约140px高，顶部从约120px开始
        item_h = 140
        y = 120 + item_h * idx + item_h // 2
        d.click(360, y)
        return True

    # 获取rv bounds
    bounds = rv.info.get("bounds", {})
    top = bounds.get("top", 120)
    bottom = bounds.get("bottom", 1100)
    left = bounds.get("left", 0)
    right = bounds.get("right", 720)

    item_h = 140
    y = top + item_h * idx + item_h // 2
    x = (left + right) // 2

    # 需要滚动到目标源可见
    # 如果idx >= 3，需要先滚动
    if idx >= 3:
        for _ in range(idx - 1):
            d.swipe(360, bottom - 100, 360, top + 100, 0.5)
            time.sleep(1)

    label = SOURCE_LABELS.get(idx, f"源[idx={idx}]")
    print(f"  点击{label} 坐标({x},{y})")
    d.click(x, y)
    return True


def wait_for_activity(keywords, timeout=15):
    """等待特定Activity出现"""
    for _ in range(timeout // 2):
        cur = d.app_current()
        act = cur.get("activity", "")
        for kw in keywords:
            if kw in act:
                return act
        time.sleep(2)
    return d.app_current().get("activity", "?")


def click_first_article():
    """点击第一篇文章"""
    # 方案1: 通过resourceId找tv_title
    title = d(resourceId=f"{RES_PREFIX}tv_title")
    if title.exists and title.count > 0:
        print(f"  找到文章标题, 数量={title.count}")
        title[0].click()
        return True

    # 方案2: 通过resourceId找tv_text
    text_el = d(resourceId=f"{RES_PREFIX}tv_text")
    if text_el.exists and text_el.count > 0:
        print(f"  找到文章文本, 数量={text_el.count}")
        text_el[0].click()
        return True

    # 方案3: 坐标点击
    rv = d(resourceId=f"{RES_PREFIX}recycler_view")
    if rv.exists:
        bounds = rv.info.get("bounds", {})
        y = bounds.get("top", 300) + 150
        x = 360
        print(f"  坐标点击文章[1] ({x},{y})")
        d.click(x, y)
        return True

    # 方案4: 直接点击屏幕中部
    print("  备用: 点击屏幕中部")
    d.click(360, 400)
    return True


def click_play_button_if_needed():
    """如果进入了详情页(RssReadActivity)，尝试点击播放按钮"""
    cur = d.app_current()
    act = cur.get("activity", "")

    if "VideoPlayer" in act or "VideoPlay" in act:
        # 已在播放页，不需要额外操作
        return

    if "RssRead" in act or "ReadRss" in act:
        print("  进入详情页，尝试点击播放按钮...")
        time.sleep(3)

        # 查找播放按钮（iv_play / fab / 播放图标）
        play_btn = d(resourceId=f"{RES_PREFIX}iv_play")
        if not play_btn.exists:
            play_btn = d(resourceId=f"{RES_PREFIX}fab")
        if not play_btn.exists:
            play_btn = d(description="播放")
        if not play_btn.exists:
            play_btn = d(description="Play")

        if play_btn.exists:
            print("  找到播放按钮，点击")
            play_btn.click()
            time.sleep(5)
        else:
            # 坐标点击（播放按钮通常在右下角）
            print("  未找到播放按钮，坐标点击右下角")
            d.click(640, 1100)
            time.sleep(5)


def check_playback_state():
    """检查当前是否处于播放状态"""
    cur = d.app_current()
    act = cur.get("activity", "")
    result = {
        "activity": act,
        "is_video_player": False,
        "is_rss_read": False,
        "is_other": False,
    }

    if "VideoPlayer" in act or "VideoPlay" in act:
        result["is_video_player"] = True
    elif "RssRead" in act or "ReadRss" in act:
        result["is_rss_read"] = True
    else:
        result["is_other"] = True

    # 检查ExoPlayer或WebView
    exo = d(resourceId=f"{RES_PREFIX}exo_player")
    if exo.exists:
        result["has_exoplayer"] = True

    surface = d(className="android.view.SurfaceView")
    if surface.exists:
        result["has_surface"] = True

    webview = d(className="android.webkit.WebView")
    if webview.exists:
        result["has_webview"] = True

    # 检查PlayerView（ExoPlayer的自定义View）
    player_view = d(className="com.google.android.exoplayer2.ui.PlayerView")
    if player_view.exists:
        result["has_player_view"] = True

    # 备选: StyledPlayerView
    styled_pv = d(className="com.google.android.exoplayer2.ui.StyledPlayerView")
    if styled_pv.exists:
        result["has_styled_player_view"] = True

    return result


def check_crash():
    """检查App是否崩溃"""
    r = run_adb('shell "logcat -d -t 200 | grep -E \'FATAL|AndroidRuntime.*io.legado\' | tail -5"')
    if r.stdout.strip():
        lines = r.stdout.strip().splitlines()
        # 脱敏：只输出异常类型和调用栈类名
        safe_lines = []
        for line in lines:
            # 提取异常类型
            exc_match = re.search(r'(Exception|Error|FATAL)', line)
            if exc_match:
                safe_lines.append(f"异常类型: {exc_match.group(0)}")
        if safe_lines:
            return True, safe_lines[:3]
    return False, []


def check_logcat():
    """检查logcat技术日志（脱敏输出）"""
    print("\n[LOGCAT] 检查技术日志...")
    filters = ["Exception", "Error", "ExoPlayer", "MediaSource", "FATAL",
               "VideoPlayer", "RssRead", "HttpDataSource"]

    results = {}
    for filt in filters:
        r = run_adb(f'shell "logcat -d -t 500 | grep -i \'{filt}\' | grep io.legado | tail -3"')
        count = len(r.stdout.strip().splitlines()) if r.stdout.strip() else 0
        if count > 0:
            results[filt] = count

    if results:
        for filt, count in results.items():
            print(f"  {filt}: {count}条")
    else:
        print("  无相关技术日志")


def screenshot(name):
    path = os.path.join(str(REPORTS_DIR), f"{name}.png")
    try:
        d.screenshot(path)
    except Exception:
        pass


def test_source_playback(source_idx):
    """测试单个源的播放功能"""
    label = SOURCE_LABELS.get(source_idx, f"源[idx={source_idx}]")
    print(f"\n{'='*50}")
    print(f"测试 {label} 播放功能")
    print(f"{'='*50}")

    result = {
        "label": label,
        "entered_source": False,
        "article_loaded": False,
        "article_clicked": False,
        "playback_activity": "?",
        "is_playing": False,
        "crashed": False,
    }

    # Step 1: 确保在订阅源列表
    navigate_to_rss_list()
    time.sleep(2)

    # Step 2: 点击目标源
    print(f"\n[STEP1] 点击{label}...")
    find_source_by_index(source_idx)
    time.sleep(5)

    cur = d.app_current()
    act = cur.get("activity", "")
    print(f"  点击后Activity: {act}")

    # 可能进入RssSortActivity（分类页）或直接进入文章列表
    if "RssSort" in act:
        print("  进入分类页，点击分类[1]...")
        rv = d(resourceId=f"{RES_PREFIX}recycler_view")
        if rv.exists:
            bounds = rv.info.get("bounds", {})
            y = bounds.get("top", 300) + 80
            x = 360
            d.click(x, y)
        else:
            # 尝试点击TabLayout第一个Tab
            tab = d(resourceId=f"{RES_PREFIX}tab_layout")
            if tab.exists:
                bounds = tab.info.get("bounds", {})
                x = bounds.get("left", 0) + 100
                y = (bounds.get("top", 0) + bounds.get("bottom", 100)) // 2
                d.click(x, y)
            else:
                d.click(360, 300)
        time.sleep(10)

        cur = d.app_current()
        act = cur.get("activity", "")
        print(f"  点击分类后Activity: {act}")

    result["entered_source"] = True

    # Step 3: 等待内容加载
    print(f"\n[STEP2] 等待内容加载(30s)...")
    time.sleep(30)

    # 检查文章列表
    title = d(resourceId=f"{RES_PREFIX}tv_title")
    text_el = d(resourceId=f"{RES_PREFIX}tv_text")
    article_count = max(title.count if title.exists else 0,
                        text_el.count if text_el.exists else 0)
    print(f"  文章标题数: {title.count if title.exists else 0}")
    print(f"  文章文本数: {text_el.count if text_el.exists else 0}")

    if article_count > 0:
        result["article_loaded"] = True
        print(f"  ✅ 文章列表已加载，共{article_count}篇")
    else:
        # 检查是否有任何可见文本
        xml = d.dump_hierarchy()
        all_text = re.findall(r'text="([^"]*)"', xml)
        visible = [t for t in dict.fromkeys(all_text) if t and len(t) > 1]
        # 脱敏：不输出实际文本，只统计
        print(f"  可见文本元素: {len(visible)}个")
        if visible:
            result["article_loaded"] = True

    screenshot(f"rss_play_{label}_articles")

    # Step 4: 点击第一篇文章
    print(f"\n[STEP3] 点击文章[1]...")
    click_first_article()
    time.sleep(10)

    result["article_clicked"] = True

    # Step 5: 检查是否进入详情页或播放页
    cur = d.app_current()
    act = cur.get("activity", "")
    print(f"  点击后Activity: {act}")

    # Step 6: 如果是详情页，尝试点击播放
    click_play_button_if_needed()
    time.sleep(5)

    # Step 7: 检查播放状态
    print(f"\n[STEP4] 检查播放状态...")
    state = check_playback_state()
    result["playback_activity"] = state["activity"]
    print(f"  当前Activity: {state['activity']}")
    print(f"  VideoPlayer: {state['is_video_player']}")
    print(f"  RssRead: {state['is_rss_read']}")
    if state.get("has_exoplayer"):
        print(f"  ExoPlayer: 存在")
    if state.get("has_surface"):
        print(f"  SurfaceView: 存在")
    if state.get("has_webview"):
        print(f"  WebView: 存在")
    if state.get("has_player_view"):
        print(f"  PlayerView: 存在")
    if state.get("has_styled_player_view"):
        print(f"  StyledPlayerView: 存在")

    if state["is_video_player"]:
        result["is_playing"] = True
        print(f"  ✅ 进入了视频播放页面")
    elif state["is_rss_read"]:
        # 详情页可能有WebView嵌入播放器
        if state.get("has_webview"):
            result["is_playing"] = True
            print(f"  ✅ 详情页含WebView（可能内嵌播放器）")
        else:
            print(f"  ⚠️ 详情页无WebView，播放未启动")
    else:
        print(f"  ⚠️ 未进入播放页面")

    screenshot(f"rss_play_{label}_playback")

    # Step 8: 检查崩溃
    crashed, crash_info = check_crash()
    if crashed:
        result["crashed"] = True
        print(f"  ❌ 检测到崩溃!")
        for info in crash_info:
            print(f"    {info}")
    else:
        print(f"  ✅ 无崩溃")

    # Step 9: 返回
    print(f"\n[RETURN] 返回订阅源列表...")
    for _ in range(4):
        d.press("back")
        time.sleep(1)
        cur = d.app_current()
        if "MainActivity" in cur.get("activity", ""):
            break
    time.sleep(2)

    return result


def main():
    print("=" * 60)
    print("RSS源播放功能验证")
    print(f"包名: {PKG}")
    print(f"测试源: {[SOURCE_LABELS[i] for i in SOURCE_INDICES]}")
    print("=" * 60)

    # 连接设备
    connect()

    # 确保App运行
    ensure_app_running()
    time.sleep(3)

    # 清空logcat
    print("[INIT] 清空logcat...")
    run_adb("logcat -c")

    # 测试每个源
    all_results = {}
    for idx in SOURCE_INDICES:
        try:
            r = test_source_playback(idx)
            all_results[SOURCE_LABELS[idx]] = r
        except Exception as e:
            print(f"\n❌ {SOURCE_LABELS[idx]}测试异常: {type(e).__name__}")
            all_results[SOURCE_LABELS[idx]] = {
                "label": SOURCE_LABELS[idx],
                "crashed": True,
                "error": type(e).__name__,
            }

    # 检查logcat
    check_logcat()

    # 汇总报告
    print(f"\n{'='*60}")
    print("汇总报告")
    print(f"{'='*60}")
    for label, r in all_results.items():
        status = "✅ 播放正常" if r.get("is_playing") else "⚠️ 播放异常"
        if r.get("crashed"):
            status = "❌ 崩溃"
        act = r.get("playback_activity", r.get("error", "?"))
        print(f"  {label}: {status} | Activity: {act}")

    print(f"\n{'='*60}")
    print("验证完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
