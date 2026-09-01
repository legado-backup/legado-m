#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""l2_verify_rss_folder_subtag.py — 订阅文件夹/标签样式交互真机走查（rss-folder-subtag-fix 3.2/3.3/3.4）

验证 renderRssSecondaryTags() 的 isTagMode 守卫（RssFragment.kt L1321-1325）：
    文件夹样式（sourceGroupStyle=2 + sourceGroupMode=1）下，二级源标签 tagsBar 与右侧向下箭头
    只允许出现在标签样式（sourceGroupMode=0）；文件夹目录与文件夹子列表均强制隐藏。

场景（--scenario）：
    folder    3.2+3.4 文件夹样式：主页目录无标签 → 进文件夹子列表头无标签 → 返回键回目录仍隐藏
    tag       3.3 标签样式：primaryBar 分组胶囊 + tagsBar 源标签正常展示
    all       全部（默认）

判定锚点（全程脱敏，源名用库内合成源安全文本"范围源"前缀匹配）：
    - 文件夹目录：内容区"全部"卡片可见 + 无 tagsBar 源标签文本
    - 文件夹子列表：分组源名（"范围源"前缀）标签节点不存在（守卫生效）
    - 标签样式：primaryBar 分组胶囊（"全部"+组名）+ tagsBar 源标签（"范围源"前缀）同时可见
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
OK, FAIL, INFO = "[OK]", "[FAIL]", "[INFO]"
SAFE_TAG_PREFIX = "范围源"  # 库内合成源名前缀（安全文本，见 testdata/rss_search_scope_test.json）


def adb(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh(cmd: str, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell", cmd],
                          capture_output=True, timeout=timeout)


def read_pref_int(key: str) -> int:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    m = re.search(rf'name="{key}" value="(-?\d+)"', out)
    return int(m.group(1)) if m else -1


def key_exists(key: str) -> bool:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    return f'name="{key}"' in out


def set_pref_int(key: str, value: int):
    cur = read_pref_int(key)
    if cur == value:
        return
    if cur < 0 and not key_exists(key):
        cmd = (f"su -c 'sed -i \"s|</map>|<int name=\\\"{key}\\\" value=\\\"{value}\\\" />"
               f"</map>|\" {PREFS}'")
    else:
        cmd = (f"su -c 'sed -i \"s/name=\\\"{key}\\\" value=\\\"[0-9-]*\\\"/"
               f"name=\\\"{key}\\\" value=\\\"{value}\\\"/\" {PREFS}'")
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


def goto_rss_tab(d):
    for _ in range(2):
        xml = d.dump_hierarchy()
        m = re.search(r'resource-id="[^"]*menu_rss[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            d.click((x1 + x2) // 2, (y1 + y2) // 2)
            time.sleep(2)
            print(f"{OK} 已切到订阅 tab")
            return True
        time.sleep(1)
    print(f"{FAIL} 未找到订阅 tab")
    return False


def node_texts(xml: str) -> list:
    return [m.group(1).strip() for m in
            re.finditer(r'<node[^>]*text="([^"]{1,40})"', xml) if m.group(1).strip()]


def has_folder_root(xml: str) -> bool:
    """文件夹目录态：内容区"全部"卡片（y>300）"""
    for m in re.finditer(r'<node[^>]*text="全部"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if int(m.group(2)) > 300:
            return True
    return False


def top_bar_height(xml: str) -> int:
    """@top_bar 高度：纯标题行≈131；primaryBar/tagsBar 扩展后显著增大"""
    m = re.search(r'resource-id="[^"]*top_bar[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    return (int(m.group(4)) - int(m.group(2))) if m else -1


def tag_nodes(xml: str) -> list:
    """tagsBar 源标签节点（合成源安全前缀匹配）。
    仅统计 top_bar 区域（y2<=300）节点——recycler_view 内列表项文本（@tv_name）也含源名，须排除"""
    return [m.group(1) for m in re.finditer(
        r'<node[^>]*text="([^"]*' + SAFE_TAG_PREFIX + r'[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if int(m.group(5)) <= 300]


def primary_bar_groups(xml: str) -> list:
    """primaryBar 分组胶囊（组名文本：全部/科技/娱乐/新闻——当前库合成源分组）"""
    found = []
    for m in re.finditer(r'<node[^>]*text="([^"]{1,10})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        t, y1 = m.group(1), int(m.group(3))
        if t in ("全部", "科技", "娱乐", "新闻", "未分组") and y1 < 400 and y1 > 100:
            found.append(t)
    return found


def scenario_folder(d) -> bool:
    """3.2+3.4：文件夹样式 主页目录无标签 → 子列表无标签 → 返回键回目录仍隐藏"""
    results = {}
    # STEP1 主页目录
    if not goto_rss_tab(d):
        return False
    time.sleep(1)
    xml = d.dump_hierarchy()
    results["3.2a-目录卡片可见"] = has_folder_root(xml)
    tags = tag_nodes(xml)
    results["3.2b-目录无源标签"] = len(tags) == 0
    print(f"{INFO} 主页目录: 目录卡片={'有' if results['3.2a-目录卡片可见'] else '无'} "
          f"源标签节点={len(tags)}")
    # STEP2 进文件夹（娱乐）
    m = None
    for mm in re.finditer(r'<node[^>]*text="娱乐"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, mm.groups())
        if y1 > 300:
            m = ((x1 + x2) // 2, (y1 + y2) // 2)
    if m is None:
        print(f"{FAIL} 娱乐文件夹卡片未找到")
        return False
    d.click(*m)
    time.sleep(2.5)
    xml = d.dump_hierarchy()
    tags = tag_nodes(xml)
    bar_h = top_bar_height(xml)
    # 守卫生效判定：top_bar 无扩展（≤150）且 top_bar 区域内无源标签文本
    results["3.2c-子列表无标签条"] = bar_h <= 150 and len(tags) == 0
    results["3.2d-子列表卡片存在"] = has_folder_root(xml) is False
    print(f"{INFO} 子列表: top_bar高度={bar_h} 标签条源标签={len(tags)}"
          f"（守卫{'生效' if bar_h <= 150 and len(tags) == 0 else '未生效'}）")
    # STEP3 返回键回目录
    adb("input", "keyevent", "4")
    time.sleep(2)
    xml = d.dump_hierarchy()
    results["3.4a-返回回目录"] = has_folder_root(xml)
    tags = tag_nodes(xml)
    results["3.4b-回目录仍无标签"] = len(tags) == 0
    print(f"{INFO} 返回后: 目录卡片={'有' if results['3.4a-返回回目录'] else '无'} 源标签节点={len(tags)}")
    ok = all(results.values())
    print("\n=== folder 场景汇总 ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    return ok


def scenario_tag(d) -> bool:
    """3.3：标签样式 primaryBar + tagsBar + 展示"""
    set_pref_int("sourceGroupMode", 0)  # 标签样式
    if not force_stop_and_start():
        return False
    if not goto_rss_tab(d):
        return False
    time.sleep(1.5)
    xml = d.dump_hierarchy()
    Path(__file__).parent.parent.joinpath("reports", "tag_mode_dump.xml").write_text(
        xml, encoding="utf-8")
    groups = primary_bar_groups(xml)
    bar_h = top_bar_height(xml)
    # 向下箭头 = filterToggleButton（ic_expand_more，content-desc="筛选"，ImageButton）
    arrow = None
    for mm in re.finditer(r'<node[^>]*content-desc="筛选"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, mm.groups())
        arrow = ((x1 + x2) // 2, (y1 + y2) // 2)
    results = {
        "3.3a-primaryBar分组胶囊": len(groups) > 0,
        "3.3c-topBar扩展展示": bar_h > 200,
    }
    if arrow is None:
        results["3.3d-向下箭头存在"] = False
        tags = []
    else:
        results["3.3d-向下箭头存在"] = True
        # 点击箭头展开 tagsBar → 判定源标签出现
        d.click(*arrow)
        time.sleep(1.5)
        xml2 = d.dump_hierarchy()
        tags = tag_nodes(xml2)
        Path(__file__).parent.parent.joinpath("reports", "tag_expanded_dump.xml").write_text(
            xml2, encoding="utf-8")
    results["3.3b-tagsBar源标签"] = len(tags) > 0
    print(f"{INFO} 标签样式: top_bar高度={bar_h} 分组胶囊节点={groups} 箭头={'有' if arrow else '无'} "
          f"展开后源标签节点={len(tags)}")
    # 恢复文件夹样式配置
    set_pref_int("sourceGroupMode", 1)
    ok = all(results.values())
    print("\n=== tag 场景汇总 ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    return ok


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"=== rss-folder-subtag-fix 真机走查 scenario={scenario} ===")
    # 前置：classic 形态 + 文件夹样式（3.2/3.4）
    set_pref_int("sourceGroupStyle", 2)
    set_pref_int("sourceGroupMode", 1)
    if not force_stop_and_start():
        return 2
    d = u2.connect(HOST)
    results = {}
    if scenario in ("folder", "all"):
        results["3.2+3.4-folder"] = scenario_folder(d)
    if scenario in ("tag", "all"):
        results["3.3-tag"] = scenario_tag(d)
    print("\n=== 结果汇总 ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    return 0 if results and all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
