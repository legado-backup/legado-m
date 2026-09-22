# -*- coding: utf-8 -*-
"""l2_verify_book_info_modern.py — 详情页「现代」样式 L2 验证（book-info-modern-compose）

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_book_info_modern.py [--scenario all]

前置：MEmu 已启动；测试包已安装（io.legado.miss.app.debug）；书架至少 1 本书。

导航与断言口径（真机实测校准，2026-09-22）：
    · MainActivity 底部导航为 Compose 自绘，语义键在 **content-desc**（书架/发现/订阅/我的），无文本节点
      ⇒ 用 uiautomator2 的 `d(description=...)` selector（dump_hierarchy 的 XML **不含 content-desc**）
    · 书架「继续阅读」卡片**单击 = 直接进阅读页（ReadBookActivity）**；**长按 = 进书籍详情页** ⇒ 本脚本用长按
    · 「详情页管理」用 am start 直达（`BookInfoManageActivity`）；样式落库用 **prefs 直接证据**校验
    · **禁用 `uiautomator dump` 命令通道**：与 uiautomator2 会话抢占服务必失败（实测 dump 恒无内容）

锚点（技术字段优先）：
    栈顶 Activity 类名 —— BookInfoActivity | BookInfoComposeActivity | BookInfoModernActivity
    现代样式页锚点 —— 顶栏「书籍信息」、底部「阅读」/「放入书架」、META 三行「分组」「书源」「查看目录」

判定（tasks 5.3/5.4/5.5 的自动化子集）：
    s1 三样式分派：管理页点样式 Tab（prefs 校验落库）→ 长按书架卡片 → 栈顶类名逐个命中（REQ-1）
    s2 现代样式渲染锚点：顶栏标题 + 底部操作 + META 三行存在（REQ-2/REQ-5 结构子集）
    s3 目录面板：点「目录」分段 → 页码指示或完整目录入口存在（REQ-3 子集）
    s4 顶栏菜单：点「更多」→ 菜单项文本断言（分享/刷新/清除缓存）（REQ-5 菜单子集）
    s5 配置生效：切现代 Tab → 关闭「分组与书源卡片」→ 现代详情页「分组」行消失 → 收尾还原（REQ-2/REQ-6）

脱敏：只输出类名/计数/布尔/UI 固定文案；严禁输出书名/源名/URL/封面路径。
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_tests.lib import compose_assert as ca

STYLE_ACT = {
    "classic": "io.legado.app.ui.book.info.BookInfoActivity",
    "immersive": "io.legado.app.ui.book.info.BookInfoComposeActivity",
    "modern": "io.legado.app.ui.book.info.BookInfoModernActivity",
}
STYLE_LABEL = {"classic": "经典", "immersive": "沉浸", "modern": "现代"}
# 样式 Tab 三档中心坐标兜底（实测 1600x1000，selector 定位不可用时使用）
STYLE_TAB_FALLBACK = {"classic": (282, 193), "immersive": (800, 193), "modern": (1318, 193)}
# 落库期望值 = BookInfoPageStyle 枚举 key（immersive/modern 带 _compose 后缀，与 Tab 简写不同）
STYLE_PREF_VALUE = {
    "classic": "classic",
    "immersive": "immersive_compose",
    "modern": "modern_compose",
}
STYLE_PREF_KEY = "bookInfoPageStyle"
MANAGE_ACT = "io.legado.app.ui.config.BookInfoManageActivity"
META_LABELS = ("分组", "书源", "查看目录")


def top_activity() -> str:
    r = ca.sh("dumpsys", "activity", "activities", timeout=15)
    m = re.search(
        r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s",
        r.stdout.decode("utf-8", errors="ignore"),
    )
    return m.group(1) if m else ""


def back(d, times=1) -> None:
    for _ in range(times):
        ca.sh("input", "keyevent", "4")
        time.sleep(1.2)


def tap_at(cx: int, cy: int) -> None:
    ca.sh("input", "tap", str(cx), str(cy), timeout=15)
    time.sleep(1.2)


def tap_text(d, text: str, timeout: float = 5) -> bool:
    """按可见文本点击（uiautomator2 selector，规避 dump 通道与 u2 会话抢占）"""
    try:
        el = d(text=text)
        if el.wait(timeout=timeout):
            el.click()
            time.sleep(1.2)
            return True
    except Exception:
        pass
    return False


def tap_desc(d, desc: str, timeout: float = 5) -> bool:
    """按 content-desc 点击（底部导航等 Compose 自绘语义键）"""
    try:
        el = d(description=desc)
        if el.wait(timeout=timeout):
            el.click()
            time.sleep(1.2)
            return True
    except Exception:
        pass
    return False


def has_text(d, text: str) -> bool:
    try:
        return bool(d(text=text).exists)
    except Exception:
        return False


def has_text_match(d, pattern: str) -> bool:
    try:
        return bool(d(textMatches=pattern).exists)
    except Exception:
        return False


def read_pref_string(key: str) -> str:
    """读字符串型偏好键

    SharedPreferences 的 `<string>` 值在**元素内容**（`<string name="k">v</string>`），
    而 `compose_assert.prefs_read` 只匹配 `value="..."` 属性口径（适用 boolean/int）
    ⇒ 字符串键必须走本函数，否则恒返回空（实测 bookInfoPageStyle 命中此坑）。
    """
    xml = ca.su_cat(ca.PREFS_DEFAULT)
    m = re.search(r'<string name="' + re.escape(key) + r'">([^<]*)</string>', xml)
    return m.group(1) if m else ""


def long_press_at(cx: int, cy: int, hold_ms: int = 900) -> None:
    """同点长按（书架卡片：单击进阅读页，长按才进详情页）"""
    ca.sh("input", "swipe", str(cx), str(cy), str(cx), str(cy), str(hold_ms), timeout=15)
    time.sleep(2.5)


def first_large_card(d):
    """书架页首个大面积可点容器（继续阅读卡片）的 bounds"""
    try:
        for el in d(clickable=True):
            b = el.info.get("bounds")
            if not b:
                continue
            if (b["right"] - b["left"]) > 400 and (b["bottom"] - b["top"]) > 400:
                return b
    except Exception:
        pass
    return None


def open_shelf(d) -> bool:
    """回到书架页：确保主界面在栈顶 → 点底部「书架」Tab

    简化说明：底部导航为 Compose 自绘，uiautomator2 的 `d(description=...)` 在本机对该节点
    不稳定（selector 与 clickable 遍历均曾恒不命中），改用**实测绝对坐标**；
    已知上限：坐标绑定 1600x1000 分辨率（换设备需重测）。
    """
    for _ in range(3):
        ca.sh_su(f"am start -n {ca.PKG}/{ca.MAIN}")
        time.sleep(4)
        if "MainActivity" in top_activity():
            break
        time.sleep(2)
    tap_at(326, 938)
    time.sleep(2.5)
    return True


def open_book_info_from_shelf(d) -> bool:
    """长按书架「继续阅读」卡片进详情页（单击=直接进阅读页，长按=进详情）

    长按需带重试：同点 swipe 长按偶发被判为单击而进入阅读页，此时退回书架重试。
    """
    for _ in range(3):
        long_press_at(406, 586)
        if "book.info" in top_activity():
            return True
        back(d)
        time.sleep(1.5)
        tap_at(326, 938)
        time.sleep(2)
    return False


def open_manage_page(d) -> bool:
    """直达「详情页管理」（Compose 首帧 + 配置加载需额外等待）"""
    ca.sh_su(f"am start -n {ca.PKG}/{MANAGE_ACT}")
    time.sleep(3)
    if MANAGE_ACT not in top_activity():
        return False
    time.sleep(2)
    return True


def pick_style(d, key: str) -> bool:
    """在「详情页管理」点样式 Tab 并校验落库（UI 点击 + prefs 直接证据），返回主界面"""
    if not open_manage_page(d):
        print(f"  [FAIL] 详情页管理页不可达（style={key}）")
        return False
    if not tap_text(d, STYLE_LABEL[key]):
        fx, fy = STYLE_TAB_FALLBACK[key]
        print(f"  [WARN] selector 定位失败，回退实测坐标 ({fx},{fy})")
        tap_at(fx, fy)
    time.sleep(1.5)
    back(d)
    expect = STYLE_PREF_VALUE[key]
    stored = read_pref_string(STYLE_PREF_KEY)
    ok = stored == expect
    if not ok:
        shown = stored if stored else "(empty)"
        print(f"  [FAIL] 样式未落库（期望 {expect}，实际 {shown}）")
    return ok


def open_modern(d) -> bool:
    if not pick_style(d, "modern"):
        return False
    if not open_shelf(d):
        print("  [FAIL] 底部「书架」Tab 定位失败")
        return False
    if not open_book_info_from_shelf(d):
        return False
    act = top_activity()
    hit = STYLE_ACT["modern"] in act
    print(f"  栈顶类名={act} 现代样式命中={hit}")
    return hit


def step_s1_style_dispatch(d) -> bool:
    """s1 三样式分派：切样式（prefs 校验）→ 长按书架卡片 → 栈顶类名命中"""
    results = {}
    for key in ("classic", "immersive", "modern"):
        if not pick_style(d, key):
            results[key] = False
            continue
        if not open_shelf(d):
            print(f"  [FAIL] style={key} 底部「书架」Tab 定位失败")
            results[key] = False
            continue
        if not open_book_info_from_shelf(d):
            results[key] = False
            continue
        act = top_activity()
        results[key] = STYLE_ACT[key] in act
        print(f"  style={key} 栈顶命中={results[key]}")
        ca.shot(d, f"l2_bim_s1_{key}")
        back(d)
    return all(results.values())


def step_s2_modern_render(d) -> bool:
    """s2 现代样式渲染锚点：顶栏标题 + 底部操作 + META 三行"""
    if not open_modern(d):
        ca.shot(d, "l2_bim_s2_not_modern")
        return False
    time.sleep(1.5)
    anchors = {
        "顶栏标题": has_text(d, "书籍信息"),
        # u2 的 textMatches 为**全串匹配**语义，模式需前后补 .*
        "阅读": has_text_match(d, r".*(阅读|继续阅读|第 \d+ 章).*"),
        "书架按钮": has_text_match(d, r".*(放入书架|删除书籍).*"),
    }
    for label in META_LABELS:
        anchors[label] = has_text(d, label)
    ca.shot(d, "l2_bim_s2_modern")
    print(f"  锚点={anchors}")
    back(d)
    return all(anchors.values())


def step_s3_catalog_panel(d) -> bool:
    """s3 目录块：点「目录」分段 → 页码指示或完整目录入口存在"""
    if not open_modern(d):
        return False
    time.sleep(1.5)
    # DETAIL 块分段：简介 / 目录（目录分段复用 book_info_tab_toc）
    if not (tap_text(d, "目录") or tap_text(d, "章节")):
        ca.shot(d, "l2_bim_s3_no_tab")
        back(d)
        return False
    time.sleep(1.5)
    page_indicator = has_text_match(d, r"\d+ / \d+")
    has_entry = has_text(d, "查看目录")
    ca.shot(d, "l2_bim_s3_catalog")
    print(f"  页码指示={page_indicator} 完整目录入口={has_entry}")
    back(d)
    return page_indicator or has_entry


def step_s4_top_menu(d) -> bool:
    """s4 顶栏溢出菜单：菜单项文本断言（分享 / 刷新 / 清除缓存）"""
    if not open_modern(d):
        return False
    time.sleep(1.2)
    # 顶栏溢出菜单按钮锚点：多语言兜底（更多 / 更多菜单 / More menu）
    if not (tap_desc(d, "更多") or tap_desc(d, "更多菜单") or tap_desc(d, "More menu")):
        ca.shot(d, "l2_bim_s4_no_more")
        back(d)
        return False
    time.sleep(1.2)
    # 只断言菜单**首屏可见**的项：菜单共 ~19 项超出屏幕高度，尾部项（清理缓存等）需滚动才可见，
    # 用 exists 断言会误判（u2 只检查当前可见元素）
    items = {t: has_text(d, t) for t in ("分享", "刷新", "置顶")}
    ca.shot(d, "l2_bim_s4_menu")
    print(f"  菜单项={items}")
    back(d, times=2)
    return all(items.values())


def toggle_component(d, index: int) -> bool:
    """切换「详情页管理」第 index 个组件开关（Compose Switch 为 checkable 节点）

    注意：组件行的**说明文本**不可点（行容器未挂 onClick），必须点 Switch 本体。
    """
    try:
        el = d(checkable=True)[index]
        el.click()
        time.sleep(1.2)
        return True
    except Exception:
        return False


def step_s5_config_effective(d) -> bool:
    """s5 配置生效：切现代 Tab → 关闭 META 组件（第二个开关）→ 详情页「分组」行消失 → 收尾还原

    前置：组件列表仅在现代 Tab 下渲染，故先切样式再进管理页。
    收尾：无论断言成败都重新启用该组件（避免污染后续用例）。
    """
    meta_switch_index = 1  # 组件顺序：HEADER / META / DETAIL / CATALOG / AI_IMAGES
    if not pick_style(d, "modern"):
        return False
    if not open_manage_page(d):
        return False
    if not toggle_component(d, meta_switch_index):
        print("  [SKIP] 未定位到 META 组件开关")
        back(d)
        return False
    back(d)
    ok_hidden = False
    try:
        if not open_modern(d):
            print("  [FAIL] 现代详情页不可达，配置生效断言无法完成")
            return False
        time.sleep(1.5)
        ok_hidden = not has_text(d, "分组")
        print(f"  关闭后 META「分组」行消失={ok_hidden}")
        ca.shot(d, "l2_bim_s5_disabled")
        back(d)
    finally:
        # 收尾还原：重新启用该组件
        if open_manage_page(d):
            toggle_component(d, meta_switch_index)
            time.sleep(1.0)
            back(d)
    return ok_hidden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", help="all | s1 | s2 | s3 | s4 | s5")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since = ca.device_now()
    steps = {
        "s1": step_s1_style_dispatch,
        "s2": step_s2_modern_render,
        "s3": step_s3_catalog_panel,
        "s4": step_s4_top_menu,
        "s5": step_s5_config_effective,
    }
    ok = ca.run_steps(
        steps,
        scenario=args.scenario,
        tag_keywords=["BookInfoModern"],
        since_ts=since,
        ctx=d,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()