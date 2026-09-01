#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""l2_verify_rss_search_scope.py — 经典形态订阅页搜索范围 token 真机验证（fix-rss-search-scope 3.3/3.5 判定）

前置数据（自动准备）：
    - 合成源 6 个（127.0.0.1:18093 本地 RSS feed，adb reverse），真实源 enabled=0
    - prefs：modernRssPage=false / sourceGroupStyle=2 / sourceGroupMode=1（文件夹视图）/ recordLog=true

场景（--scenario）：
    group    S1 文件夹进"娱乐"分组→搜索→源数量=1（仅源C，标题 SC- 前缀）
    nogroup  S2 文件夹进"未分组"→搜索→源数量=1（仅源G，标题 SG- 前缀）
    all      S4 根目录全部→搜索→源数量=6（SA..SG 全出现）
    type     S3 类型胶囊"图片"→搜索→源数量=1（仅源B，标题 SB-；需重启切 sourceGroupStyle=1+mode=0）
    display  S5 搜索页范围友好文案显示 + 手动切换"全部源"重搜
    all      全部场景顺序执行

判定通道：
    A（权威）appLog "启动RSS搜索 源数量=N"（RssSearchModel.startSearch INFO 日志，recordLog 落盘）
    B（佐证）搜索结果页合成标题前缀集合（SA-/SB-/SC-/SD-/SE-/SG-，安全文本）

脱敏：输出仅含判定结论/计数/合成标题/固定 UI 文案；appLog 中"源[xxx]搜索失败"行替换为 源[编号]。
防死循环：锚点等待超时即 FAIL 退出，不无限重试。
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
SRV_PORT = 18093
KEYWORD = "test"
OK, FAIL, INFO = "[OK]", "[FAIL]", "[INFO]"

# 合成标题前缀 → 源编号
PREFIX_MAP = {"SA-": "源A(科技/网页)", "SB-": "源B(科技/图片)", "SC-": "源C(娱乐/视频)",
              "SD-": "源D(新闻/网页)", "SE-": "源E(新闻/网页)", "SG-": "源G(未分组)"}


def adb(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh(cmd: str, timeout=30):
    """整条命令作为单个字符串传给 adb shell（su -c 单 token 铁律）"""
    return subprocess.run([ADB_PATH, "-s", HOST, "shell", cmd],
                          capture_output=True, timeout=timeout)


def read_pref_int(key: str) -> int:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    m = re.search(rf'name="{key}" value="(-?\d+)"', out)
    return int(m.group(1)) if m else -1


def read_pref_bool(key: str) -> bool:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    m = re.search(rf'name="{key}" value="(true|false)"', out)
    return m.group(1) == "true" if m else False


def key_exists(key: str) -> bool:
    out = sh(f"su -c 'cat {PREFS}'").stdout.decode("utf-8", errors="ignore")
    return f'name="{key}"' in out


def set_pref_int(key: str, value: int):
    cur = read_pref_int(key)
    if cur == value:
        return
    if cur < 0 and not key_exists(key):  # 键不存在：借 </map> 行尾插入（sed 表达式内层双引号防 su 内层 sh 重定向解析）
        cmd = (f"su -c 'sed -i \"s|</map>|<int name=\\\"{key}\\\" value=\\\"{value}\\\" />"
               f"</map>|\" {PREFS}'")
    else:
        cmd = (f"su -c 'sed -i \"s/name=\\\"{key}\\\" value=\\\"[0-9-]*\\\"/"
               f"name=\\\"{key}\\\" value=\\\"{value}\\\"/\" {PREFS}'")
    r = sh(cmd)
    err = (r.stderr or b"").decode("utf-8", errors="ignore")[:150]
    print(f"{INFO} prefs set {key}={value} exit={r.returncode} err={err or '(无)'}")
    if r.returncode != 0:
        return
    _fix_owner()


def _fix_owner():
    """sed -i rename 后文件 owner 变 root，必须还原 App 属主（SQLITE/prefs 读取防护）"""
    sh(f"su -c 'chown u0_a75:u0_a75 {PREFS}; chmod 660 {PREFS}'")


def set_pref_bool(key: str, value: bool):
    if read_pref_bool(key) == value:
        return
    if not key_exists(key):
        lit = "true" if value else "false"
        cmd = (f"su -c 'sed -i \"s|</map>|<boolean name=\\\"{key}\\\" value=\\\"{lit}\\\" />"
               f"</map>|\" {PREFS}'")
    else:
        other = "false" if value else "true"
        cmd = (f"su -c 'sed -i \"s/name=\\\"{key}\\\" value=\\\"{other}\\\"/"
               f"name=\\\"{key}\\\" value=\\\"{value}\\\"/\" {PREFS}'")
    r = sh(cmd)
    err = (r.stderr or b"").decode("utf-8", errors="ignore")[:150]
    print(f"{INFO} prefs set {key}={value} exit={r.returncode} err={err or '(无)'}")
    if r.returncode != 0:
        return
    _fix_owner()


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
    """底部导航（Compose 绘制）→ 用 content-desc 定位订阅 tab"""
    for attempt in range(2):
        xml = d.dump_hierarchy()
        # 底部导航 desc 通常为"订阅"（R.string.rss）
        for m in re.finditer(r'<node[^>]*content-desc="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            desc, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
            if desc in ("订阅", "rss", "Rss") and y1 > 1200:
                d.click((x1 + x2) // 2, (y1 + y2) // 2)
                time.sleep(2)
                print(f"{OK} 已切到订阅 tab（desc={desc}）")
                return True
        # 兜底：resource-id menu_rss
        m = re.search(r'resource-id="[^"]*menu_rss[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            d.click((x1 + x2) // 2, (y1 + y2) // 2)
            time.sleep(2)
            print(f"{OK} 已切到订阅 tab（resource-id=menu_rss）")
            return True
        time.sleep(1)
    print(f"{FAIL} 未找到订阅 tab 锚点（已重试 2 次）")
    return False


def tap_folder(d, text: str) -> bool:
    """文件夹目录点击指定卡片（取 y1 最大者=内容区卡片，避开顶栏同名标签）"""
    xml = d.dump_hierarchy()
    best = None
    for m in re.finditer(r'<node[^>]*text="' + text + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if best is None or y1 > best["y1"]:
            best = {"cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2, "y1": y1}
    if best is None:
        print(f"{FAIL} 文件夹锚点未找到: {text}")
        return False
    d.click(best["cx"], best["cy"])
    time.sleep(2)
    print(f"{OK} 已点击文件夹: {text}")
    return True


def tap_topbar_search(d) -> bool:
    """顶栏搜索按钮（content-desc=搜索）"""
    for attempt in range(2):
        xml = d.dump_hierarchy()
        for m in re.finditer(r'<node[^>]*content-desc="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            desc = m.group(1)
            if desc in ("搜索", "search"):
                x1, y1, x2, y2 = map(int, m.groups()[1:])
                d.click((x1 + x2) // 2, (y1 + y2) // 2)
                time.sleep(2)
                return True
        time.sleep(1)
    print(f"{FAIL} 顶栏搜索按钮未找到")
    return False


def search_keyword(d, keyword: str):
    """搜索页输入关键词并提交（u2 send_keys 依赖 ADBKeyBoard，MEmu 无 → adb input text）"""
    xml = d.dump_hierarchy()
    box = None
    for m in re.finditer(r'<node[^>]*class="android.widget.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if y2 < 600:  # 顶栏搜索框
            box = {"cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
            break
    if box is None:
        # Compose SettingsSearchBar 非 EditText 类：顶栏按钮行(y≈88)下方固定区域
        size = d.window_size()
        box = {"cx": size[0] // 2, "cy": 170}
    d.click(box["cx"], box["cy"])
    time.sleep(1)
    adb("input", "text", keyword)  # ASCII 关键词，input text 支持
    time.sleep(1)
    adb("input", "keyevent", "66")  # ENTER → IME search action
    time.sleep(8)


def read_search_counts() -> dict:
    """读 appLog 最新文件，提取 RSS 搜索判定行（脱敏：源[名称]→源[编号]）。
    grep 多文件按参数顺序输出（非时间序），必须按行首时间戳排序后取最新"""
    r = sh(f"su -c 'ls -t {LOG_DIR} | head -3'")
    names = [n for n in r.stdout.decode("utf-8", errors="ignore").split() if n.startswith("appLog-")]
    if not names:
        return {"error": "appLog 文件不存在（recordLog 未开启？）"}
    out = ""
    for name in names[:3]:
        r = sh(f"su -c 'grep -hE \"启动RSS搜索|RSS搜索结果合并完成\" {LOG_DIR}/{name}'")
        out += r.stdout.decode("utf-8", errors="ignore")
    # 脱敏：源[xxx] → 源[N]
    counter = {"n": 0}

    def _mask(mo):
        counter["n"] += 1
        return f"源[{counter['n']}]"

    out = re.sub(r"源\[[^\]]*\]", _mask, out)
    rows = []
    for l in out.splitlines():
        m = re.match(r"(\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d+): (Rss .+)$", l.strip())
        if m and ("启动RSS搜索" in l or "RSS搜索结果合并完成" in l):
            rows.append((m.group(1), m.group(2)))
    rows.sort(key=lambda t: t[0])  # 时间戳字符串同格式可直接排序
    starts = [msg for _, msg in rows if "启动RSS搜索" in msg][-3:]
    merged = [msg for _, msg in rows if "合并完成" in msg][-3:]
    return {"starts": starts, "merged": merged}


def result_source_prefixes(d) -> set:
    """搜索结果页合成标题前缀集合（安全文本）"""
    xml = d.dump_hierarchy()
    found = set()
    for prefix in PREFIX_MAP:
        if re.search(r'text="' + prefix, xml):
            found.add(prefix)
    return found


def check(scenario: str, expect_sources: int, expect_prefixes: set) -> bool:
    info = read_search_counts()
    if "error" in info:
        print(f"{FAIL} appLog 读取失败: {info['error']}")
        return False
    last = info["starts"][-1] if info["starts"] else "(无)"
    m = re.search(r"源数量=(\d+)", last)
    actual = int(m.group(1)) if m else -1
    ok_log = actual == expect_sources
    print(f"{OK if ok_log else FAIL} [{scenario}] appLog 源数量: 期望={expect_sources} 实际={actual}（{last}）")
    return ok_log


def ensure_root_folder_view(d) -> bool:
    """确保处于订阅页文件夹目录（根目录）。若在子列表按返回键回目录。
    锚点=内容区"全部"卡片（真机 diag 证实文本为'全部'，y>300 避开顶栏）"""
    for _ in range(3):
        xml = d.dump_hierarchy()
        for m in re.finditer(r'<node[^>]*text="全部"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            y1 = int(m.group(2))
            if y1 > 300:
                return True
        adb("input", "keyevent", "4")
        time.sleep(1.5)
    xml = d.dump_hierarchy()
    return bool(re.search(r'<node[^>]*text="全部"[^>]*bounds="\[\d+,([3-9]\d{2,})\]', xml))


def run_scenario(d, name: str, folder: str = None, expect: int = 0, prefixes: set = None,
                 style: int = None, mode: int = None, tag: str = None) -> bool:
    """统一场景执行：可选重启(样式变更)→订阅tab→(文件夹或胶囊)→搜索→判定"""
    if style is not None:
        set_pref_int("sourceGroupStyle", style)
        set_pref_int("sourceGroupMode", mode)
        if not force_stop_and_start():
            return False
    if not goto_rss_tab(d):
        return False
    if folder:
        if not ensure_root_folder_view(d):
            print(f"{FAIL} [{name}] 未回到文件夹目录")
            return False
        if not tap_folder(d, folder):
            return False
    elif tag:
        # 类型胶囊（TabLayout 文本节点）
        if not tap_folder(d, tag):  # 同款文本点击（取 y1 最大者可能错位，胶囊在顶部）
            return False
    if not tap_topbar_search(d):
        return False
    search_keyword(d, KEYWORD)
    ok = check(name, expect, prefixes)
    # UI 佐证：结果页前缀集合
    found = result_source_prefixes(d)
    print(f"{INFO} [{name}] 结果页合成标题前缀: {sorted(found) if found else '(无)'}")
    # 清理：返回订阅页（搜索页 back）
    adb("input", "keyevent", "4")
    time.sleep(1)
    adb("input", "keyevent", "4")
    time.sleep(1.5)
    return ok


def scenario_display(d) -> bool:
    """S5：搜索页范围友好文案显示 + 手动切换全部源"""
    if not goto_rss_tab(d):
        return False
    if not ensure_root_folder_view(d):
        print(f"{FAIL} [display] 未回到文件夹目录")
        return False
    if not tap_folder(d, "娱乐"):
        return False
    if not tap_topbar_search(d):
        return False
    search_keyword(d, KEYWORD)
    # 打开更多菜单：RssSearchActivity 的 MoreVert contentDescription=null（源码 L122）→ 右上角固定坐标
    w, h = d.window_size()
    d.click(w - 60, 88)
    time.sleep(1.5)
    xml = d.dump_hierarchy()
    # 友好文案判定：范围=娱乐（组名直接显示）+ 固定文案"全部源"；token 原文（@type:/@no_group）不应出现
    friendly = "全部源" in xml and "娱乐" in xml
    token_leak = ("@type:" in xml) or ("@no_group" in xml)
    print(f"{OK if friendly and not token_leak else FAIL} [display] 菜单范围显示: "
          f"友好文案={'有' if friendly else '无'} token泄漏={'有' if token_leak else '无'}")
    # 手动切换"全部源"→重新搜索
    m = re.search(r'<node[^>]*text="全部源"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        d.click((x1 + x2) // 2, (y1 + y2) // 2)
        time.sleep(1)
        # 菜单关闭后若有搜索词自动 reSearch（initData stateLiveData observer）；保险再提交一次
        search_keyword(d, KEYWORD)
        ok2 = check("display-switch-all", 6, None)
        adb("input", "keyevent", "4")
        time.sleep(1)
        adb("input", "keyevent", "4")
        time.sleep(1.5)
        return ok2
    print(f"{FAIL} [display] 菜单中未找到'全部源'项")
    adb("input", "keyevent", "4")
    return False


def scenario_diag(d) -> bool:
    """诊断：输出当前界面节点摘要（短文本/desc，脱敏截断）"""
    xml = d.dump_hierarchy()
    count = 0
    for m in re.finditer(r'<node[^>]*?(?:text|content-desc)="([^"]{1,20})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        t = m.group(1).strip()
        if not t:
            continue
        x1, y1, x2, y2 = map(int, m.groups()[1:])
        print(f"  node[{count}] ({(x1+x2)//2},{(y1+y2)//2}) {t}")
        count += 1
        if count >= 40:
            break
    print(f"{INFO} diag 节点总数={count}")
    return True


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"=== fix-rss-search-scope 真机验证 scenario={scenario} ===")
    # 前置 prefs：classic + 文件夹视图 + recordLog
    set_pref_bool("modernRssPage", False)
    set_pref_int("sourceGroupStyle", 2)
    set_pref_int("sourceGroupMode", 1)
    set_pref_bool("recordLog", True)
    if not force_stop_and_start():
        return 2
    d = u2.connect(HOST)
    if scenario == "diag":
        goto_rss_tab(d)
        return scenario_diag(d)
    results = {}
    if scenario in ("group", "all"):
        results["S1-group"] = run_scenario(d, "S1-group", folder="娱乐", expect=1, prefixes={"SC-"})
    if scenario in ("nogroup", "all"):
        results["S2-nogroup"] = run_scenario(d, "S2-nogroup", folder="未分组", expect=1, prefixes={"SG-"})
    if scenario in ("type", "all"):
        results["S3-type"] = run_scenario(d, "S3-type", tag="图片", expect=1, prefixes={"SB-"},
                                          style=1, mode=0)
        # 恢复文件夹视图配置供后续/其他场景
        set_pref_int("sourceGroupStyle", 2)
        set_pref_int("sourceGroupMode", 1)
    if scenario in ("allscope", "all"):
        results["S4-allscope"] = run_scenario(d, "S4-allscope", folder=None, expect=6)
    if scenario in ("display", "all"):
        results["S5-display"] = scenario_display(d)
    print("\n=== 结果汇总 ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    return 0 if results and all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
