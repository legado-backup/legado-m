#!/usr/bin/env python3
"""nav_helper.py — 视频播放器导航辅助（全程脱敏，只输出编号不输出文本）

安全规范：绝不输出RSS源/分类/文章的真实名称，只用编号，避免违禁词
用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/nav_helper.py [源编号]
    默认尝试源编号2（跳过第1个可能失效的源）
"""
import uiautomator2 as u2
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MEMU_ADB_HOST, PACKAGE

def main():
    source_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    d = u2.connect(MEMU_ADB_HOST)
    cur = d.app_current()
    print(f"[导航] 当前Activity: {cur.get('activity', '?')}")

    # 步骤1: 点击订阅Tab
    rss_tab = d(resourceId=f"{PACKAGE}:id/menu_rss")
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(3)
        print("[导航] 已点击订阅Tab")

    # 步骤2: 点击第N个源（通过坐标，不读名称）
    rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if not rv.exists:
        print("[导航] 错误: recycler_view不存在")
        return
    bounds = rv.info.get("bounds", {})
    # 每个源item大约高140px，从top开始
    item_h = 140
    cy = bounds.get("top", 120) + item_h * (source_idx - 1) + item_h // 2
    cx = (bounds.get("left", 0) + bounds.get("right", 720)) // 2
    print(f"[导航] 点击源[{source_idx}] 坐标({cx},{cy})")
    d.click(cx, cy)
    time.sleep(5)

    # 步骤3: 检查是否进入分类页（RssSortActivity）
    cur2 = d.app_current()
    print(f"[导航] 点击后Activity: {cur2.get('activity', '?')}")

    # 步骤4: 点击第一个分类（通过坐标，不读名称）
    rv2 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv2.exists:
        b2 = rv2.info.get("bounds", {})
        cy2 = b2.get("top", 256) + 100
        cx2 = (b2.get("left", 0) + b2.get("right", 720)) // 2
        print(f"[导航] 点击分类[1] 坐标({cx2},{cy2})")
        d.click(cx2, cy2)
        time.sleep(5)

    # 步骤5: 下拉刷新文章列表
    rv3 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv3.exists:
        b3 = rv3.info.get("bounds", {})
        print("[导航] 执行下拉刷新...")
        d.swipe(cx2, b3.get("top", 256) + 50, cx2, b3.get("top", 256) + 400, 0.5)
        time.sleep(12)

    # 步骤6: 点击第一篇文章进入视频播放器
    rv4 = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv4.exists:
        b4 = rv4.info.get("bounds", {})
        cy4 = b4.get("top", 256) + 150
        print(f"[导航] 点击文章[1] 坐标({cx2},{cy4})")
        d.click(cx2, cy4)
        time.sleep(12)

    cur3 = d.app_current()
    act = cur3.get("activity", "?")
    print(f"[导航] 最终Activity: {act}")
    if "VideoPlayer" in act or "VideoPlay" in act:
        print("[导航] ✅ 成功进入视频播放器")
    else:
        print("[导航] ⚠️ 未进入视频播放器")

if __name__ == "__main__":
    main()
