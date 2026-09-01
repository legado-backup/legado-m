#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""l2_verify_rss_search_regression.py — fix-rss-search-scope 3.4 回归验证

三项回归（--scenario）：
    modern   现代形态源内搜索：modernRssPage=true → 订阅页选合成源A(科技) → 顶栏搜索
             → 范围=源分组"科技" → appLog 源数量=2（科技组合成源A/B）
    my       设置页订阅搜索入口（MySettingsData L286 RssSearchActivity.start(this, null)）
             → scope=AppConfig.rssSearchScope（持久化，本环境为空=全部）→ 源数量=6
    book     书源搜索（SearchActivity，书源 SearchScope 不受影响）：am start --es key 回归样本读物
             → 结果列表含合成书锚点
    all      全部（默认）

脱敏：合成源名/合成书名为安全测试文本。
"""
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY  # noqa: E402

import uiautomator2 as u2  # noqa: E402

HOST = MEMU_ADB_HOST
PKG = PACKAGE
PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
LOG_DIR = f"/storage/emulated/0/Android/data/{PKG}/cache/logs"
SEARCH_ACT = f"{PKG}/io.legado.app.ui.book.search.SearchActivity"
BOOK_PREFIX = "回归样本读物"
OK, FAIL, INFO = "[OK]", "[FAIL]", "[INFO]"


def adb(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh(cmd: str, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell", cmd],
                          capture_output=True, timeout=timeout)


def read_pref_bool(key: str) -> bool:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    m = re.search(rf'name="{key}" value="(true|false)"', out)
    return m.group(1) == "true" if m else False


def set_pref_bool(key: str, value: bool):
    if read_pref_bool(key) == value:
        return
    lit = "true" if value else "false"
    other = "false" if value else "true"
    cmd = (f"su -c 'sed -i \"s/name=\\\"{key}\\\" value=\\\"{other}\\\"/"
           f"name=\\\"{key}\\\" value=\\\"{lit}\\\"/\" {PREFS}'")
    r = sh(cmd)
    print(f"{INFO} prefs set {key}={value} exit={r.returncode}")
    if r.returncode == 0:
        sh(f"su -c 'chown u0_a75:u0_a75 {PREFS}; chmod 660 {PREFS}'")


def force_stop_and_start():
    adb("am", "force-stop", PKG)
    time.sleep(2)
    adb("am", "start", "-n", f"{PKG}/{MAIN_ACTIVITY}")
    for _ in range(30):
        time.sleep(1)
        out = adb("dumpsys", "activity", "activities").stdout.decode("utf-8", errors="ignore")
        if "MainActivity" in out:
            time.sleep(2)
            print(f"{OK} App 已进入 MainActivity")
            return True
    print(f"{FAIL} App 启动超时")
    return False


def goto_tab(d, rid_suffix: str) -> bool:
    for _ in range(2):
        xml = d.dump_hierarchy()
        m = re.search(rf'resource-id="[^"]*{rid_suffix}[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            d.click((x1 + x2) // 2, (y1 + y2) // 2)
            time.sleep(2)
            return True
        time.sleep(1)
    print(f"{FAIL} tab 未找到: {rid_suffix}")
    return False


def tap_desc_or_text(d, value: str, use_desc=True) -> bool:
    xml = d.dump_hierarchy()
    attr = "content-desc" if use_desc else "text"
    for m in re.finditer(rf'<node[^>]*{attr}="{re.escape(value)}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        d.click((x1 + x2) // 2, (y1 + y2) // 2)
        time.sleep(2)
        return True
    return False


def search_in_page(d, keyword: str):
    """当前搜索页输入关键词提交"""
    xml = d.dump_hierarchy()
    box = None
    for m in re.finditer(r'<node[^>]*class="android.widget.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if y2 < 500:
            box = ((x1 + x2) // 2, (y1 + y2) // 2)
            break
    if box is None:
        box = (360, 170)
    d.click(*box)
    time.sleep(1)
    adb("input", "text", keyword)
    time.sleep(1)
    adb("input", "keyevent", "66")
    time.sleep(8)


def read_latest_search_count() -> int:
    r = sh(f"su -c 'ls -t {LOG_DIR} | head -3'")
    names = [n for n in r.stdout.decode("utf-8", errors="ignore").split() if n.startswith("appLog-")]
    rows = []
    for name in names[:3]:
        r = sh(f"su -c 'grep -h RSS {LOG_DIR}/{name}'")
        for l in r.stdout.decode("utf-8", errors="ignore").splitlines():
            m = re.search(r"启动RSS搜索 源数量=(\d+)", l)
            ts = re.match(r"(\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)", l.strip())
            if m and ts:
                rows.append((ts.group(1), int(m.group(1))))
    rows.sort(key=lambda t: t[0])
    return rows[-1][1] if rows else -1


def scenario_modern(d) -> bool:
    print("\n--- 回归1: 现代形态源内搜索 ---")
    set_pref_bool("modernRssPage", True)
    if not force_stop_and_start():
        return False
    if not goto_tab(d, "menu_rss"):
        return False
    # 等待 modern 源胶囊条渲染（重试 3 次）
    time.sleep(2)
    found = False
    for _ in range(3):
        if tap_desc_or_text(d, "范围源A-科技-网页", use_desc=False):
            found = True
            break
        time.sleep(2)
    if not found:
        print(f"{FAIL} 源列表未见合成源A（modern 源选择）")
        return False
    time.sleep(3)  # WebView 渲染
    # 顶栏搜索按钮（modern: searchButton→openRssSearch）
    if not tap_desc_or_text(d, "搜索", use_desc=True):
        print(f"{FAIL} 顶栏搜索按钮未找到")
        return False
    search_in_page(d, "test")
    n = read_latest_search_count()
    # 科技分组 = 合成源A/B（真实源已禁用）
    ok = n == 2
    print(f"{OK if ok else FAIL} [modern] 源内搜索源数量: 期望=2(科技组) 实际={n}")
    # 清理：返回并恢复 classic
    adb("input", "keyevent", "4")
    time.sleep(1)
    set_pref_bool("modernRssPage", False)
    return ok


def scenario_my(d) -> bool:
    print("\n--- 回归2: 设置页订阅搜索入口 ---")
    if not force_stop_and_start():
        return False
    if not goto_tab(d, "menu_my_config"):
        return False
    time.sleep(1.5)
    # 我的页面找"订阅源全局搜索"入口（R.string.rss_search，滚动查找最多 4 次）
    found = False
    for _ in range(4):
        if tap_desc_or_text(d, "订阅源全局搜索", use_desc=False) or tap_desc_or_text(d, "订阅源全局搜索", use_desc=True):
            found = True
            break
        adb("input", "swipe", "360", "900", "360", "400")
        time.sleep(1)
    if not found:
        print(f"{FAIL} 未找到'订阅源搜索'入口")
        return False
    time.sleep(1.5)
    search_in_page(d, "test")
    n = read_latest_search_count()
    ok = n == 6
    print(f"{OK if ok else FAIL} [my] 全局搜索源数量: 期望=6 实际={n}")
    adb("input", "keyevent", "4")
    time.sleep(1)
    return ok


def scenario_book(d) -> bool:
    print("\n--- 回归3: 书源搜索（SearchScope 不受影响） ---")
    if not force_stop_and_start():
        return False
    # 确定性入口直达书源搜索（seed_b2_bookshelf 同款）
    adb("am", "start", "-n", SEARCH_ACT, "--es", "key", BOOK_PREFIX)
    time.sleep(10)
    xml = d.dump_hierarchy()
    hits = len(re.findall(r'text="[^"]*' + BOOK_PREFIX, xml))
    ok = hits > 0
    print(f"{OK if ok else FAIL} [book] 书源搜索结果含合成书锚点: 命中={hits}")
    adb("input", "keyevent", "4")
    time.sleep(1)
    return ok


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"=== fix-rss-search-scope 3.4 回归 scenario={scenario} ===")
    d = u2.connect(HOST)
    results = {}
    if scenario in ("modern", "all"):
        results["回归1-modern源内搜索"] = scenario_modern(d)
    if scenario in ("my", "all"):
        results["回归2-我的页入口"] = scenario_my(d)
    if scenario in ("book", "all"):
        results["回归3-书源搜索"] = scenario_book(d)
    print("\n=== 结果汇总 ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    return 0 if results and all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
