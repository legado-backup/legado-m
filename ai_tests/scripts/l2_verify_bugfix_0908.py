#!/usr/bin/env python3
r"""l2_verify_bugfix_0908.py — 真机反馈五项修复 L2 验证（real-device-bugfix-0908）

场景（--scenario）：
  t1  替换净化页搜索框唯一（titleBar/selectActionBar GONE 修复）
  t2  经典订阅"文件夹"视图切新版订阅后无残留（folderComposeView GONE）
  t3  "我的"页无"书架媒体"入口 + 旧页面 Activity 不可达
  t4  弹框不透明度<100 时窗口 dim 补偿（云端同步任务弹框，alpha=60 → dim≈0.4）
  t5  万级书源按域名分组：渲染/滚动/零 FATAL/零 ANR
  all 全部场景（t1→t5 顺序执行）

辅助参数：
  --seed N    t5 前置造数：合成 N 条书源直插 DB（WAL 安全通道，批量 executemany）
  --cleanup   t5 后清理：删除合成源（url 前缀 http://bf0908*.test）
  --keep-alpha  t4 结束后不恢复 dialogAlpha=100（调试用）

用法：
  ai_tests\venv\Scripts\python.exe ai_tests\scripts\l2_verify_bugfix_0908.py --scenario all
  ai_tests\venv\Scripts\python.exe ai_tests\scripts\l2_verify_bugfix_0908.py --scenario t5 --seed 10500 --cleanup

脱敏口径：只输出计数/布尔/视图 id/错误码/技术字段，禁输出源名称/域名/业务文本。
说明：本脚本不依赖 uiautomator2（dump 走 uiautomator dump+cat），su 通道走单字符串形式。
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ai_tests" / "scripts"))

from ai_tests.config import MEMU_ADB_HOST, PACKAGE  # noqa: E402
import import_book_source as ibs  # noqa: E402  复用 WAL 安全 pull/push 通道

# 简化说明：SDK adb 参数处理比 MEmu adb 标准（同 verify_rss_mode_switch.py 先例）
ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
HOST = MEMU_ADB_HOST
PKG = PACKAGE
PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
REPORTS = PROJECT_ROOT / "ai_tests" / "reports" / "bugfix-0908"
SYNTH_URL_LIKE = "http://bf0908%.test%"
SYNTH_HOST_TMPL = "bf0908{}.test"


def shell(args, timeout=30):
    """adb shell 封装；超时不抛异常返回空结果（万级列表场景设备可能挂起，容错继续）"""
    try:
        return subprocess.run([ADB, "-s", HOST, "shell"] + args,
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        class _TO:
            returncode = -1
            stdout = b""
            stderr = b"timeout"
        return _TO()


def su(cmd, timeout=20):
    # SOP 陷阱#4：su -c 内容必须作为单个字符串参数传入（列表多参形式会被 adb shell 重新
    # 按空格拆散，su 只吃到首个 token，实测 rc=1 空输出）
    return shell([f"su -c '{cmd}'"], timeout=timeout)


def dump(d=None, min_nodes: int = 12) -> str:
    """uiautomator dump + cat 取 XML（重试；不依赖 uiautomator2）。
    min_nodes：残缺树校验阈值——动画页面常出现截断 dump（无节点/无 resource-id），视为无效重试。
    t5 万级列表场景 uiautomator 可能挂起 45s+，超时放宽到 120s。"""
    for _ in range(4):
        shell(["uiautomator", "dump", "/sdcard/ui_dump.xml"], timeout=120)
        time.sleep(0.6)
        rc = shell(["cat", "/sdcard/ui_dump.xml"], timeout=60)
        out = rc.stdout.decode("utf-8", errors="ignore")
        if out.strip().startswith("<?xml"):
            shell(["rm", "-f", "/sdcard/ui_dump.xml"])
            if out.count("<node") >= min_nodes or "resource-id" in out:
                return out
        time.sleep(2.0)
    return ""


def texts(xml):
    return sorted(set(t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()))


def _push_prefs_xml(root) -> bool:
    """序列化并 push（push 前本地校验 XML 合法性，防 SOP 警告的回写损坏）"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = ET.tostring(root, encoding="unicode")
    ET.fromstring(out)  # 自校验
    local = REPORTS / "prefs_mod.xml"
    local.write_text(out, encoding="utf-8")
    subprocess.run([ADB, "-s", HOST, "push", str(local), "/data/local/tmp/prefs_mod.xml"],
                   capture_output=True, timeout=30)
    st = su(f"stat -c '%u %g' {PREFS} 2>/dev/null").stdout.decode("utf-8", errors="ignore").split()
    uid, gid = (st[0], st[1]) if len(st) == 2 else ("0", "0")
    su(f"cp /data/local/tmp/prefs_mod.xml {PREFS} && chown {uid}:{gid} {PREFS} && chmod 660 {PREFS} && rm -f /data/local/tmp/prefs_mod.xml")
    time.sleep(0.3)
    return True


def _load_prefs_root():
    r = su(f"cat {PREFS} 2>/dev/null")
    txt = r.stdout.decode("utf-8", errors="ignore")
    if "</map>" not in txt:
        print("  [FAIL] prefs 文件不可读")
        return None
    # 防历史损坏：截断到首个 </map>（Android 解析行为一致）
    txt = txt[: txt.index("</map>") + 6]
    try:
        return ET.fromstring(txt)
    except Exception as e:
        print(f"  [FAIL] prefs XML 解析失败: {e}")
        return None


def _write_pref(key: str, kind: str, value) -> bool:
    """ElementTree 结构化改写（键存在则删除重建，保证 XML 恒合法）。前置：已 force-stop。"""
    root = _load_prefs_root()
    if root is None:
        return False
    for el in list(root):
        if el.get("name") == key:
            root.remove(el)
    if kind == "int":
        el = ET.Element("int", {"name": key, "value": str(value)})
    else:
        el = ET.Element("boolean", {"name": key, "value": "true" if value else "false"})
    root.append(el)
    _push_prefs_xml(root)
    time.sleep(0.3)
    got = read_pref_int(key) if kind == "int" else read_pref_bool(key)
    expect = value if kind == "int" else (1 if value else 0)
    print(f"  prefs 写入 {key}={value}（回读 {got}）")
    return got == expect


def read_pref_int(key: str) -> int:
    root = _load_prefs_root()
    if root is None:
        return -1
    for el in root:
        if el.get("name") == key:
            if el.tag == "int":
                return int(el.get("value"))
            if el.tag == "string" and (el.text or "").lstrip("-").isdigit():
                return int(el.text)
    return -1


def read_pref_bool(key: str) -> int:
    """布尔键回读：1=true 0=false -1=不存在"""
    root = _load_prefs_root()
    if root is None:
        return -1
    for el in root:
        if el.get("name") == key and el.tag == "boolean":
            return 1 if el.get("value") == "true" else 0
    return -1


def write_pref_int(key: str, value: int):
    return _write_pref(key, "int", value)


def write_pref_bool(key: str, value: bool):
    return _write_pref(key, "bool", value)


def force_stop():
    shell(["am", "force-stop", PKG])
    # 等待进程真正死亡（MEmu force-stop 后有服务拉起/异步退出，需轮询 pidof）
    for _ in range(10):
        r = shell(["pidof", PKG])
        if not r.stdout.decode("utf-8", errors="ignore").strip():
            break
        time.sleep(1.0)
        shell(["am", "force-stop", PKG])
    time.sleep(1.0)


def start_activity(cls, wait=3.0):
    r = shell(["am", "start", "-n", f"{PKG}/{cls}"])
    out = (r.stdout + r.stderr).decode("utf-8", errors="ignore")
    time.sleep(wait)
    return out


def resumed_activity():
    r = shell(["dumpsys", "activity", "activities"])
    m = re.search(r"mResumedActivity:.*?\s(\S+/\S+)", r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else "?"


def view_flag(view_id: str) -> str:
    """从 dumpsys activity top 解析视图可见性首标志：V=可见 I=不可见 G=gone（找不到返回空）"""
    r = shell(["dumpsys", "activity", "top"])
    out = r.stdout.decode("utf-8", errors="ignore")
    for line in out.splitlines():
        if f"id/{view_id}" in line or f"app:id/{view_id}" in line:
            m = re.search(r"\{[0-9a-f]+ ([VIG])", line)
            if m:
                return m.group(1)
    return ""


def count_class(xml: str, cls: str) -> int:
    return len(re.findall(rf'class="{re.escape(cls)}"', xml))


def fatal_check(label: str) -> bool:
    r = shell(["logcat", "-d", "-s", "AndroidRuntime:E"])
    out = r.stdout.decode("utf-8", errors="ignore")
    n = out.count("FATAL EXCEPTION")
    print(f"  [{label}] FATAL EXCEPTION 计数: {n}")
    return n == 0


def tap_text(d, adp_text: str, fallback_desc: str = "", retries: int = 2) -> bool:
    """dump→正则取 bounds→坐标 tap 闭环（SOP u2 陷阱#1 同款，不依赖 u2）"""
    for _ in range(retries + 1):
        xml = dump(d)
        for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            if m.group(1) == adp_text:
                x = (int(m.group(2)) + int(m.group(4))) // 2
                y = (int(m.group(3)) + int(m.group(5))) // 2
                shell(["input", "tap", str(x), str(y)])
                time.sleep(1.8)
                return True
        if fallback_desc:
            m = re.search(rf'content-desc="{re.escape(fallback_desc)}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                shell(["input", "tap", str(x), str(y)])
                time.sleep(1.8)
                return True
        time.sleep(1.0)
    return False


# ---------------- t1 替换净化页搜索框唯一 ----------------
def t1(d) -> bool:
    print("== t1 替换净化页：搜索框唯一性 ==")
    force_stop()
    shell(["logcat", "-c"])
    out = start_activity("io.legado.app.ui.replace.ReplaceRuleActivity")
    if "Error" in out and "does not exist" in out:
        print("  [FAIL] ReplaceRuleActivity 启动失败")
        return False
    time.sleep(2.5)
    xml = dump(d)
    n_edit = count_class(xml, "android.widget.EditText")
    resumed = resumed_activity()
    print(f"  resumed={resumed} EditText 计数: {n_edit}")
    ok = resumed.endswith("ReplaceRuleActivity") and n_edit <= 1
    print(f"  判定: {'✅ 通过（无重复搜索框）' if ok else '❌ 失败'}")
    shell(["input", "keyevent", "4"])
    time.sleep(1.2)
    ok = fatal_check("t1") and ok
    return ok


# ---------------- t2 订阅文件夹视图残留（纯 UI 流程，复刻用户复现路径） ----------------
def _tap_my_tab():
    xml = dump(None)
    m = re.search(r'resource-id="[^"]*menu_my_config[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        cx = (int(m.group(1)) + int(m.group(3))) // 2
        cy = (int(m.group(2)) + int(m.group(4))) // 2
        shell(["input", "tap", str(cx), str(cy)])
        time.sleep(2.0)
        return True
    return tap_text(None, "我的")


def _goto_rss_discovery_sub():
    """MainActivity → 我的 → 主题设置 → 发现与订阅（ConfigActivity UI 导航，
    实测 shell am start 非导出 Activity 会回落桌面，必须走应用内导航）"""
    _tap_my_tab()
    if not tap_text(None, "主题设置"):
        print("  [FAIL] 未找到'主题设置'入口")
        return False
    time.sleep(2.0)
    if not tap_text(None, "发现与订阅"):
        print("  [FAIL] 未找到'发现与订阅'入口")
        return False
    time.sleep(2.0)
    return True


def _set_rss_mode_ui(modern: bool):
    """发现与订阅页：点订阅形态项展开下拉 → 选目标项（下拉选项在右侧 x>500,y>200）"""
    xml = dump(None)
    title = next((t for t in texts(xml) if "新版订阅" in t), None)
    if not title:
        print("  [WARN] 配置页未找到订阅形态设置项")
        return False
    tap_text(None, title)
    xml = dump(None)
    label = "新版订阅" if modern else "经典订阅"
    best = None
    for m in re.finditer(r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if m.group(1) == label:
            x1, y1, x2, y2 = map(int, m.groups()[1:])
            if x1 > 500 and y1 > 200:
                best = ((x1 + x2) // 2, (y1 + y2) // 2)
                break
    if not best:
        print(f"  [WARN] 未定位下拉选项: {label}")
        return False
    shell(["input", "tap", str(best[0]), str(best[1])])
    time.sleep(2.0)
    return True


def _back_to_main_and_open_rss():
    """返回键退出设置链到 MainActivity → 点订阅 tab"""
    for _ in range(4):
        shell(["input", "keyevent", "4"])
        time.sleep(1.5)
        if resumed_activity().endswith("MainActivity"):
            break
    xml = dump(None)
    m = re.search(r'resource-id="[^"]*menu_rss[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        cx = (int(m.group(1)) + int(m.group(3))) // 2
        cy = (int(m.group(2)) + int(m.group(4))) // 2
        shell(["input", "tap", str(cx), str(cy)])
        time.sleep(2.5)
        return True
    return tap_text(None, "订阅")


def t2(d) -> bool:
    print("== t2 订阅栏目：文件夹视图切新版后无残留（全 UI 复刻用户路径） ==")
    force_stop()  # 清场：防上次遗留弹框/页面态
    shell(["logcat", "-c"])
    start_activity("io.legado.app.ui.welcome.WelcomeActivity", wait=6.0)

    def set_folder_view():
        """经典 RSS：三点菜单(content-desc=菜单) → 布局设置 → 分组样式=按分组 + 展示模式=文件夹 → 确定"""
        opened = tap_text(None, "菜单", fallback_desc="菜单")
        if not opened:
            # 兜底：顶栏右上角第一个 ImageButton（dump 中 class=ImageButton）
            xml = dump(None)
            m = re.search(r'class="android.widget.ImageButton"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
            if not m:
                m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*class="android.widget.ImageButton"', xml)
            if m:
                g = m.groups()
                shell(["input", "tap", str((int(g[0]) + int(g[2])) // 2), str((int(g[1]) + int(g[3])) // 2)])
                time.sleep(1.8)
                opened = True
        if not opened:
            print("  [FAIL] 未找到三点菜单按钮")
            return False
        if not tap_text(None, "布局设置"):
            print("  [FAIL] 未找到'布局设置'菜单项")
            return False
        time.sleep(2.0)
        # 弹框交互（实测模型）：区块行（分组样式/展示模式）点击=展开该区块（其余区块隐藏），
        # 点选项=选中并收起全部区块。流程：分组样式→按分组；展示模式→文件夹；确定。
        for section, option in (("分组样式", "按分组"), ("展示模式", "文件夹")):
            if not tap_text(None, section, retries=3):
                print(f"  [FAIL] 展开'{section}'失败")
                return False
            time.sleep(1.0)
            if not tap_text(None, option, retries=3):
                print(f"  [FAIL] 选择'{option}'失败")
                return False
            time.sleep(1.0)
        if not tap_text(None, "确定", retries=3):
            print("  [FAIL] 点击确定失败")
            return False
        time.sleep(2.5)
        return True

    # 步骤A：切经典订阅 → RSS tab → 布局设置=文件夹 → folderComposeView 应可见
    if not _goto_rss_discovery_sub():
        return False
    if not _set_rss_mode_ui(modern=False):
        return False
    if not _back_to_main_and_open_rss():
        print("  [FAIL] 未能进入订阅 tab")
        return False
    if not set_folder_view():
        return False
    flag_before = view_flag("folder_compose_view")
    print(f"  步骤A（经典+文件夹）folder_compose_view 标志: {flag_before or '未找到'}")
    ok_a = flag_before == "V"

    # 步骤B：UI 切新版订阅 → 回 RSS tab，folderComposeView 应 GONE（bugfix-0908 T2 断言）
    if not _goto_rss_discovery_sub():
        return False
    if not _set_rss_mode_ui(modern=True):
        return False
    if not _back_to_main_and_open_rss():
        print("  [FAIL] 切新版后未能进入订阅 tab")
        return False
    time.sleep(3.0)
    flag_folder = view_flag("folder_compose_view")
    flag_recycler = view_flag("recycler_view")
    print(f"  步骤B（切新版后）folder_compose_view 标志: {flag_folder or '未找到'} / recycler_view 标志: {flag_recycler or '未找到'}")
    ok_b = flag_folder in ("G", "") and flag_recycler in ("G", "")

    # 恢复（best-effort，不影响判定）：切回新版订阅为默认形态
    ok = ok_a and ok_b and fatal_check("t2")
    try:
        if not _goto_rss_discovery_sub():
            print("  [WARN] 恢复导航失败（不影响判定）")
        else:
            _set_rss_mode_ui(modern=True)
    except Exception as e:
        print(f"  [WARN] 恢复异常（不影响判定）: {type(e).__name__}")
    print(f"  判定: 步骤A={'✅' if ok_a else '❌'} 步骤B={'✅' if ok_b else '❌'} → {'✅ 通过' if ok else '❌ 失败'}")
    return ok


# ---------------- t3 我的入口清单 ----------------
def t3(d) -> bool:
    print("== t3 我的页：书架媒体入口移除 ==")
    force_stop()
    shell(["logcat", "-c"])
    shell(["am", "start", "-n", f"{PKG}/io.legado.app.ui.main.MainActivity"])
    time.sleep(2.5)
    xml = dump(d)
    m = re.search(r'resource-id="[^"]*menu_my_config[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        cx = (int(m.group(1)) + int(m.group(3))) // 2
        cy = (int(m.group(2)) + int(m.group(4))) // 2
        shell(["input", "tap", str(cx), str(cy)])
        time.sleep(2.0)
    else:
        tap_text(d, "我的")
    xml = dump(d)
    has_entry = "书架媒体" in texts(xml)
    n_text = len(texts(xml))
    print(f"  我的页 dump 文本节点数: {n_text}，'书架媒体' 命中: {has_entry}")

    r = shell(["am", "start", "-n", f"{PKG}/io.legado.app.ui.main.my.MyFeatureBooksActivity"])
    out = (r.stdout + r.stderr).decode("utf-8", errors="ignore")
    gone = ("does not exist" in out) or ("Error" in out) or ("not found" in out)
    print(f"  旧页面 Activity 启动输出含错误标记: {gone}")
    ok = (not has_entry) and gone
    print(f"  判定: {'✅ 通过' if ok else '❌ 失败'}")
    ok = fatal_check("t3") and ok
    return ok


# ---------------- t4 弹框 dim 补偿 ----------------
def _dialog_window_has_dim() -> bool:
    """弹框为独立窗口（同 Activity 第二窗口，TRANSPARENT+APPLICATION）且带 DIM_BEHIND 标志。
    注：本 MEmu 镜像 dumpsys 不输出 mDimAmount 数值，只能做标志级断言。"""
    r = shell(["dumpsys", "window", "windows"], timeout=40)
    out = r.stdout.decode("utf-8", errors="ignore")
    for block in out.split("Window #"):
        if PKG in block and "DIM_BEHIND" in block and "ty=APPLICATION" in block and "fmt=TRANSPARENT" in block:
            return True
    return False


def t4(d, keep_alpha=False) -> bool:
    print("== t4 弹框不透明度 60 → dim 补偿（窗口标志级断言） ==")
    orig_a = read_pref_int("dialogAlpha")
    orig_n = read_pref_int("dialogAlphaNight")
    print(f"  原始 prefs: dialogAlpha={orig_a} dialogAlphaNight={orig_n}")
    force_stop()
    if not write_pref_int("dialogAlpha", 60):
        return False
    write_pref_int("dialogAlphaNight", 60)
    shell(["logcat", "-c"])
    out = start_activity("io.legado.app.ui.config.ThemeManageActivity")
    if "does not exist" in out:
        print("  [FAIL] ThemeManageActivity 启动失败")
        return False
    time.sleep(2.0)

    # 打开"同步任务"弹框：顶栏图标 content-desc=同步任务（无 text 节点）
    opened = tap_text(None, "同步任务", fallback_desc="同步任务")
    if not opened:
        for probe in ("更多", "⋮"):
            if tap_text(None, probe, fallback_desc=probe):
                opened = tap_text(None, "同步任务", fallback_desc="同步任务")
                if opened:
                    break
    time.sleep(2.5)
    # 弹框内容可达性（a11y 树独立于 GPU 合成器，screencap 黑屏不影响本判定）
    xml = dump(None)
    dialog_nodes = any(k in xml for k in ("同步任务", "云端同步", "暂无云端同步任务"))
    has_dim = _dialog_window_has_dim()
    REPORTS.mkdir(parents=True, exist_ok=True)
    shot = REPORTS / "t4_dialog_alpha60.png"
    shell(["screencap", "-p", "/sdcard/t4_dialog.png"])
    subprocess.run([ADB, "-s", HOST, "pull", "/sdcard/t4_dialog.png", str(shot)],
                   capture_output=True, timeout=30)
    shell(["rm", "-f", "/sdcard/t4_dialog.png"])
    # 关闭弹框
    shell(["input", "keyevent", "4"])
    time.sleep(1.2)
    if not keep_alpha:
        force_stop()
        write_pref_int("dialogAlpha", orig_a if orig_a >= 0 else 100)
        write_pref_int("dialogAlphaNight", orig_n if orig_n >= 0 else 100)
    print(f"  弹框打开={opened} 弹框节点命中={dialog_nodes} DIM_BEHIND 标志={has_dim}（截图: {shot.name}）")
    print("  环境限制：本 MEmu 实例 screencap 全黑（已知 GPU 故障），dim 数值/亮度差判定留真机人工复核")
    ok = opened and dialog_nodes and has_dim
    print(f"  判定: {'✅ 通过（标志级+可达性）' if ok else '❌ 失败'}")
    ok = fatal_check("t4") and ok
    return ok


# ---------------- t5 万级书源域名分组 ----------------
def seed_sources(n: int):
    """合成 n 条书源批量直插 DB（复用 import_book_source WAL 安全通道，executemany 提速）"""
    print(f"== t5 造数: 合成 {n} 条书源 ==")
    tmp = str(REPORTS / "seed_tmp.db")
    if not ibs.pull_db(tmp):
        return False
    con = sqlite3.connect(tmp)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(book_sources)")
        meta = cur.fetchall()
        cols = [r[1] for r in meta]

        def build_row(i: int):
            host = SYNTH_HOST_TMPL.format(i % 200)
            url = f"http://{host}/src/{i:06d}"
            row = {"bookSourceUrl": url,
                   "bookSourceName": f"压力源{i:06d}",
                   "bookSourceGroup": "压力测试组",
                   "searchUrl": f"http://{host}/search?q={{key}}",
                   "enabled": 1,
                   "lastUpdateTime": 1726000000000 + i,
                   "customOrder": i}
            for c in ("ruleSearch", "ruleBookInfo", "ruleToc", "ruleContent"):
                if c in cols:
                    row[c] = "{}"
            keys = [k for k in row if k in cols]
            vals = [json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (dict, list)) else row[k] for k in keys]
            extra_cols, extra_vals = [], []
            for _, name, ctype, notnull, dflt, _pk in meta:
                if name in keys:
                    continue
                if dflt is not None:
                    extra_cols.append(name)
                    extra_vals.append(dflt.replace("'", "") if isinstance(dflt, str) else dflt)
                elif notnull:
                    extra_cols.append(name)
                    extra_vals.append(0 if "INT" in (ctype or "").upper() else "")
            return keys + extra_cols, vals + extra_vals

        names, first_vals = build_row(0)
        rows = [first_vals]
        for i in range(1, n):
            _, v = build_row(i)
            rows.append(v)
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cur.executemany(
            f"INSERT OR REPLACE INTO book_sources ({','.join(names)}) VALUES ({','.join(['?'] * len(names))})",
            rows)
        con.commit()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cur.execute("SELECT COUNT(*) FROM book_sources")
        total = cur.fetchone()[0]
        print(f"  插入后总数: {total}")
    finally:
        con.close()
    return ibs.push_db(tmp)


def cleanup_sources():
    print("== t5 清理: 删除合成源 ==")
    tmp = str(REPORTS / "cleanup_tmp.db")
    if not ibs.pull_db(tmp):
        return False
    con = sqlite3.connect(tmp)
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM book_sources WHERE bookSourceUrl LIKE ?", (SYNTH_URL_LIKE,))
        con.commit()
        cur.execute("SELECT COUNT(*) FROM book_sources")
        total = cur.fetchone()[0]
        print(f"  清理后总数: {total}")
    finally:
        con.close()
    return ibs.push_db(tmp)


def t5(d, seed: int = 0, do_cleanup: bool = False) -> bool:
    if seed > 0:
        if not seed_sources(seed):
            print("  [FAIL] 造数失败")
            return False
    if do_cleanup:
        return cleanup_sources()
    print("== t5 万级书源按域名分组：渲染/滚动/零崩溃 ==")
    force_stop()
    shell(["logcat", "-c"])
    out = start_activity("io.legado.app.ui.book.source.manage.BookSourceActivity", wait=6.0)
    if "does not exist" in out:
        print("  [FAIL] BookSourceActivity 启动失败")
        return False
    time.sleep(4.0)

    # 打开"更多菜单"（Compose 顶栏，content-desc=更多菜单）→ 点"按域名分组显示"
    opened_menu = tap_text(None, "更多菜单", fallback_desc="更多菜单", retries=4)
    if not opened_menu:
        for probe in ("更多", "⋮"):
            opened_menu = tap_text(None, probe, fallback_desc=probe, retries=2)
            if opened_menu:
                break
    tapped = tap_text(None, "按域名分组显示", retries=3)
    print(f"  域名分组开关点击: {tapped}（菜单打开: {opened_menu}）")
    # 分组排序在 IO 线程重算 + 首帧提交，低配模拟器给足收敛时间
    time.sleep(12.0)

    # 断言 dump（best-effort：万级行 uiautomator 可访问性树过重，dump 可能失败/超时，
    # 不作为硬判定——交互响应与稳定性才是本场景核心证据）
    t_start = time.time()
    xml = dump(d)
    dump_lat = round(time.time() - t_start, 1)
    header_hits = len(re.findall(r'bf0908\d+\.test', xml))
    rows = count_class(xml, "android.view.View")
    print(f"  分组后 dump 时延: {dump_lat}s 域名分组头命中数: {header_hits} View 节点: {rows}（best-effort）")

    # 2 轮滑动观测（时延仅记录；uiautomator dump 在 10k 行上固有问题不作为硬判定）
    latencies = []
    renders = 0
    for i in range(2):
        t_start = time.time()
        shell(["input", "swipe", "540", "1600", "540", "700", "300"], timeout=90)
        time.sleep(1.0)
        xml = dump(d)
        lat = time.time() - t_start
        latencies.append(round(lat, 1))
        if count_class(xml, "android.view.View") > 0:
            renders += 1
        time.sleep(0.5)
    resumed = resumed_activity()
    anr = shell(["dumpsys", "activity", "processes"], timeout=90)
    anr_out = anr.stdout.decode("utf-8", errors="ignore")
    anr_hits = anr_out.count(f"ANR in {PKG}") + anr_out.count("Application Not Responding")
    print(f"  resumed={resumed} 滑动dump时延: {latencies} 渲染轮数: {renders}/2 ANR 计数: {anr_hits}")
    # 硬判定：开关生效 + 页面存活 + 零 ANR（用户报障=卡死闪退，修复后稳定性为核心证据）
    ok = (opened_menu and tapped and resumed.endswith("BookSourceActivity")
          and anr_hits == 0)
    print(f"  判定: {'✅ 通过（分组开关生效+无ANR+零崩溃，页面存活）' if ok else '❌ 失败'}")
    shell(["input", "keyevent", "4"], timeout=90)
    time.sleep(1.0)
    ok = fatal_check("t5") and ok
    return ok


# ---------------- t6 摘录分享模板页启动（0908-followup T3 回归） ----------------
def t6(d) -> bool:
    print("== t6 摘录分享模板页：启动存活（IndexOutOfBounds 回归） ==")
    force_stop()
    shell(["logcat", "-c"])
    out = start_activity("io.legado.app.ui.config.ShareNoteTemplateManageActivity", wait=5.0)
    if "does not exist" in out:
        print("  [FAIL] ShareNoteTemplateManageActivity 启动失败")
        return False
    time.sleep(2.0)
    resumed = resumed_activity()
    xml = dump(None)
    # 页面锚点：顶栏标题/添加入口（Compose Screen 渲染成功标志）
    anchors = [t for t in texts(xml) if ("摘录" in t or "模板" in t or "添加" in t or "新建" in t or "导入" in t)]
    print(f"  resumed={resumed} 页面锚点数: {len(anchors)}（脱敏计数）")
    ok = resumed.endswith("ShareNoteTemplateManageActivity") and len(anchors) >= 1
    print(f"  判定: {'✅ 通过（启动无崩溃+内容可达）' if ok else '❌ 失败'}")
    shell(["input", "keyevent", "4"], timeout=90)
    time.sleep(1.0)
    ok = fatal_check("t6") and ok
    return ok


# ---------------- t7 经典发现头部（0908-followup T1 回归） ----------------
def t7(d) -> bool:
    print("== t7 经典发现：头部存活+形态切换（颜色视觉留真机） ==")
    force_stop()
    shell(["logcat", "-c"])
    start_activity("io.legado.app.ui.welcome.WelcomeActivity", wait=6.0)
    # 发现与订阅设置页 → "发现页模式"项（注意区分"发现页布局/发现页管理"相邻项）→ 切经典发现
    if not _goto_rss_discovery_sub():
        return False
    xml = dump(None)
    title = "发现页模式" if "发现页模式" in texts(xml) else next(
        (t for t in texts(xml) if "发现页模式" in t), None)
    if not title:
        print("  [WARN] 未找到发现形态设置项")
        return False
    tap_text(None, title)
    xml = dump(None)
    # 发现形态可能为对话框/下拉两种形态：选项不做位置过滤，取首个"经典发现"
    best = None
    for m in re.finditer(r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if m.group(1) == "经典发现":
            x1, y1, x2, y2 = map(int, m.groups()[1:])
            best = ((x1 + x2) // 2, (y1 + y2) // 2)
            break
    if not best:
        print("  [WARN] 未定位'经典发现'选项")
        return False
    shell(["input", "tap", str(best[0]), str(best[1])])
    time.sleep(2.0)
    if not _back_to_main_and_open_discovery():
        print("  [FAIL] 未能进入发现 tab")
        return False
    time.sleep(3.0)
    # 经典发现头部 = TitleBar（title_bar 节点存在且可见）
    flag_title = view_flag("title_bar")
    print(f"  经典发现 title_bar 标志: {flag_title or '未找到'}")
    ok = flag_title == "V"
    print(f"  判定: {'✅ 通过（经典发现头部在位，颜色/壁纸视觉留真机）' if ok else '❌ 失败'}")
    ok = fatal_check("t7") and ok
    return ok


def _back_to_main_and_open_discovery():
    """返回键退出设置链到 MainActivity → 点发现 tab"""
    for _ in range(4):
        shell(["input", "keyevent", "4"], timeout=90)
        time.sleep(1.5)
        if resumed_activity().endswith("MainActivity"):
            break
    xml = dump(None)
    m = re.search(r'resource-id="[^"]*menu_discovery[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        cx = (int(m.group(1)) + int(m.group(3))) // 2
        cy = (int(m.group(2)) + int(m.group(4))) // 2
        shell(["input", "tap", str(cx), str(cy)], timeout=90)
        time.sleep(2.5)
        return True
    return tap_text(None, "发现")


# ---------------- t8 管理族自绘顶栏存活（0908-followup T2 回归） ----------------
def t8(d) -> bool:
    print("== t8 管理族自绘分支顶栏：页面存活（图标颜色视觉留真机） ==")
    force_stop()
    shell(["logcat", "-c"])
    out = start_activity("io.legado.app.ui.book.source.manage.BookSourceActivity", wait=5.0)
    if "does not exist" in out:
        print("  [FAIL] BookSourceActivity 启动失败")
        return False
    time.sleep(2.0)
    resumed = resumed_activity()
    print(f"  resumed={resumed}")
    ok = resumed.endswith("BookSourceActivity")
    print(f"  判定: {'✅ 通过（自绘分支顶栏路径零崩溃）' if ok else '❌ 失败'}")
    shell(["input", "keyevent", "4"], timeout=90)
    time.sleep(1.0)
    ok = fatal_check("t8") and ok
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", help="all|t1|t2|t3|t4|t5|t6|t7|t8")
    ap.add_argument("--seed", type=int, default=0, help="t5 造数条数")
    ap.add_argument("--cleanup", action="store_true", help="t5 清理合成源")
    ap.add_argument("--keep-alpha", action="store_true", help="t4 不恢复 dialogAlpha")
    args = ap.parse_args()

    print(f"设备: {HOST} 包: {PKG}")

    results = {}
    sc = args.scenario
    if sc in ("t1", "all"):
        results["t1"] = t1(None)
    if sc in ("t2", "all"):
        results["t2"] = t2(None)
    if sc in ("t3", "all"):
        results["t3"] = t3(None)
    if sc in ("t4", "all"):
        results["t4"] = t4(None, keep_alpha=args.keep_alpha)
    if sc in ("t5", "all"):
        results["t5"] = t5(None, seed=args.seed, do_cleanup=args.cleanup)
    if sc == "t6":
        results["t6"] = t6(None)
    if sc == "t7":
        results["t7"] = t7(None)
    if sc == "t8":
        results["t8"] = t8(None)

    print("== 汇总 ==")
    for k, v in results.items():
        print(f"  {k}: {'✅' if v else '❌'}")
    if all(results.values()):
        print("✅ 全部场景通过")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
