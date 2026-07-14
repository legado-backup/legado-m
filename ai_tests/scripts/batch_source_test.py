#!/usr/bin/env python3
"""batch_source_test.py — 批量遍历RSS源检测修复点覆盖

自动尝试多个源，检测R5网络抓包/降级路径/416等关键日志。
全程脱敏：只输出源编号和Activity名称，不输出任何源名称/域名/URL。
用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/batch_source_test.py [起始编号] [结束编号]
    默认: 5 15
"""
import uiautomator2 as u2
import time
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

def run_adb(cmd, timeout=30):
    full = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout,
                       encoding='utf-8', errors='replace')
    return r.stdout or ""

def check_logcat_for_fixes():
    """检查logcat中是否出现修复点相关日志"""
    log = run_adb("logcat -d")
    lines = log.splitlines()
    fixes_found = {}

    keywords = {
        "R5网络抓包": "R5网络抓包",
        "MPD误判": "<MPD",
        "FileUri跳过": "系统浏览器不支持本地",
        "HTTP_416重试": "HTTP 416",
        "清除视频缓存": "清除视频缓存",
        "PROTOCOL_ERROR": "PROTOCOL_ERROR",
        "Cronet回退": "回退到 OkHttp",
        "网络错误重试": "网络错误自动重试",
        "降级WebView": "降级",
        "播放失败": "onPlayerError",
        "BehindLiveWindow": "直播流追直播",
    }
    for name, kw in keywords.items():
        count = sum(1 for l in lines if kw in l)
        if count > 0:
            fixes_found[name] = count
    return fixes_found

def try_source(d, idx):
    """尝试导航到源idx并播放视频，返回(进入播放器, 修复点日志)"""
    # 返回主界面
    d.press("back")
    time.sleep(1)
    d.press("back")
    time.sleep(2)

    # 点击订阅Tab
    rss_tab = d(resourceId=f"{PACKAGE}:id/menu_rss")
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(2)

    # 点击源idx（支持滚动：idx>VISIBLE_ITEMS时先滚动列表使目标源可见）
    rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if not rv.exists:
        return False, {}
    # 先滚动到顶部
    for _ in range(5):
        d.swipe(360, 200, 360, 1000, 0.3)
    time.sleep(1)
    # 计算屏幕可见项数（约6个），需要滚动多少屏
    VISIBLE_ITEMS = 6
    screens_to_scroll = (idx - 1) // VISIBLE_ITEMS
    for _ in range(screens_to_scroll):
        d.swipe(360, 900, 360, 300, 0.5)
    time.sleep(1)
    # 计算在当前屏幕中的位置
    bounds = rv.info.get("bounds", {})
    item_h = 140
    pos_in_screen = (idx - 1) % VISIBLE_ITEMS
    cy = bounds.get("top", 120) + item_h * pos_in_screen + item_h // 2
    cx = (bounds.get("left", 0) + bounds.get("right", 720)) // 2
    d.click(cx, cy)
    time.sleep(4)

    # 点击分类1
    rv2 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv2.exists:
        b2 = rv2.info.get("bounds", {})
        cy2 = b2.get("top", 256) + 100
        d.click(cx, cy2)
        time.sleep(4)

    # 下拉刷新
    rv3 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv3.exists:
        b3 = rv3.info.get("bounds", {})
        d.swipe(cx, b3.get("top", 256) + 50, cx, b3.get("top", 256) + 400, 0.5)
        time.sleep(8)

    # 点击文章1
    rv4 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv4.exists:
        b4 = rv4.info.get("bounds", {})
        cy4 = b4.get("top", 256) + 150
        d.click(cx, cy4)
        time.sleep(12)

    cur = d.app_current()
    act = cur.get("activity", "?")
    in_player = "VideoPlayer" in act or "VideoPlay" in act

    # 如果进入播放器，等待播放+滑动
    if in_player:
        time.sleep(10)
        # 快速滑动2次
        d.swipe(360, 600, 360, 300, 0.3)
        time.sleep(5)
        d.swipe(360, 600, 360, 300, 0.3)
        time.sleep(5)

    fixes = check_logcat_for_fixes()
    return in_player, fixes

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    d = u2.connect(MEMU_ADB_HOST)
    print(f"批量遍历源[{start}]-[{end}]，检测修复点覆盖")
    print("=" * 60)

    # 清空logcat
    run_adb("logcat -c")

    all_fixes = {}
    for idx in range(start, end + 1):
        print(f"\n--- 尝试源[{idx}] ---")
        try:
            in_player, fixes = try_source(d, idx)
            print(f"  进入播放器: {'是' if in_player else '否'}")
            if fixes:
                print(f"  ★ 触发修复点日志:")
                for name, count in fixes.items():
                    print(f"    {name}: {count}次")
                    all_fixes[name] = all_fixes.get(name, 0) + count
            else:
                print(f"  无修复点日志触发")
        except Exception as e:
            print(f"  ⚠️ 异常: {str(e)[:80]}")

    print("\n" + "=" * 60)
    print("累计触发的修复点:")
    if all_fixes:
        for name, count in all_fixes.items():
            print(f"  ★ {name}: {count}次")
    else:
        print("  (无修复点被触发)")
    print(f"\n遍历完成: 源[{start}]-[{end}]")

if __name__ == "__main__":
    main()
