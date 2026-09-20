# -*- coding: utf-8 -*-
"""l2_verify_b1_tts_casting.py — B1.4/B1.5 真机补验：语音选角模板管理

覆盖（ui-subpage-optimization B1 批次）：
  t1 B1.4-F78：管理弹框列表内**使用中模板**标识（`tts_casting_active_tag` = 「使用中」）
  t2 B1.5-F76：模板编辑器内**添加规则**入口（`tts_casting_add_rule` = 「＋ 添加规则」）
  t3 B1.5-F77：规则行**置顶**入口（`tts_casting_move_top` = 「置顶」，index>0 时出现）
  t4 全程 FATAL=0（run_steps 统一判定）

入口链（4 层 DialogFragment，`am start` 不可直达，须逐层点开）：
  阅读页 `ReadBookActivity` →（呼出菜单）→ 朗读 → 朗读面板/对话框
  →「设置」→ `ReadAloudConfigDialog` → 选角入口 → `TtsCastingPickerDialog`
  →「管理模板」→ `TtsCastingManageFragment`（列表 / 编辑器）

⚠️ 每层均打印 dump 命中情况，任一层断链即输出断点位置（便于区分「产品缺陷」与「导航问题」）。

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_b1_tts_casting.py [--scenario all|t1..t3]
前置：MEmu 已启动；测试包已安装；设备侧有至少 1 本可读的书
"""
import argparse
import re
import subprocess
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import uiautomator2 as u2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca  # noqa: E402

ACT_READ = "io.legado.app.ui.book.read.ReadBookActivity"

# 文案锚点（strings.xml 实际值）
S_MANAGE_TITLE = "选角模板管理"     # tts_casting_manage_title
S_ACTIVE_TAG = "使用中"             # tts_casting_active_tag（B1.4-F78）
S_MANAGE_ENTRY = "管理模板"         # tts_casting_manage_entry
S_ADD_RULE = "＋ 添加规则"          # tts_casting_add_rule（B1.5-F76）
S_MOVE_TOP = "置顶"                 # tts_casting_move_top（B1.5-F77）
S_SETTING = "设置"
S_ADD_TMPL = "新增模板"

# 阅读页朗读入口候选（content-desc / text）
READ_ALOUD_KEYS = ("朗读", "read_aloud", "ReadAloud")


def sh(*args, timeout=45):
    try:
        return ca.sh(*args, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
        time.sleep(3)
        return ca.sh(*args, timeout=timeout)


def connect_robust(retries=3):
    subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
    time.sleep(1.5)
    for i in range(retries):
        try:
            r = ca.sh("echo", "device_ok", timeout=20)
            if b"device_ok" not in (r.stdout or b""):
                raise RuntimeError("echo 探针无响应")
            su = ca.sh("su -c 'id -u'", timeout=25)
            if not (su.stdout or b"").strip().endswith(b"0"):
                raise RuntimeError("su 不可用")
            return u2.connect(HOST)
        except Exception as e:
            print(f"[warn] connect 失败({i + 1}/{retries}): {type(e).__name__} {e}")
            subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
            time.sleep(5)
    raise RuntimeError("设备连接失败")


def reset_app():
    sh("am", "force-stop", PKG)
    time.sleep(1.5)


def dump_xml(d) -> str:
    for _ in range(2):
        try:
            return d.dump_hierarchy()
        except Exception:
            time.sleep(1.5)
    return ""


def text_bounds(d, pattern: str):
    """dump→正则取节点 bounds（StaleObject 兜底）"""
    return ca.dump_bounds(d, pattern)


def tap_text(d, text: str, contains: bool = False, timeout=6) -> bool:
    """文本点击（contains=True 用包含匹配，应对「＋ 添加规则」这类带符号文案）"""
    try:
        node = d(textContains=text) if contains else d(text=text)
        if node.wait(timeout=timeout):
            node.click()
            time.sleep(1.5)
            return True
    except Exception:
        pass
    pat = (f'text="[^"]*{re.escape(text)}[^"]*"' if contains
           else f'text="{re.escape(text)}"')
    return ca.click_by_dump(d, pat, timeout=2)


def tap_by_desc_or_text(d, keys) -> bool:
    """按多个候选关键词（content-desc 优先）点击任一命中节点"""
    for k in keys:
        b = text_bounds(d, f'content-desc="[^"]*{re.escape(k)}[^"]*"')
        if b:
            w, h = d.window_size()
            d.click(b["cx"] / w, b["cy"] / h)
            time.sleep(1.5)
            return True
    for k in keys:
        if tap_text(d, k, contains=True, timeout=2):
            return True
    return False


def first_book_url() -> str:
    sh("am", "force-stop", PKG)
    time.sleep(2)
    ca.sh_su(f"cp /data/data/{PKG}/databases/legado.db /sdcard/b1.db")
    tmp = str(Path(tempfile.mkdtemp(prefix="b1_")) / "db")
    subprocess.run([ADB, "-s", HOST, "pull", "/sdcard/b1.db", tmp],
                   capture_output=True, timeout=60)
    try:
        con = sqlite3.connect(tmp)
        try:
            cur = con.cursor()
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            row = cur.execute(
                "SELECT bookUrl FROM books WHERE type = 0 AND totalChapterNum > 0 "
                "AND bookUrl NOT LIKE 'l2://%' AND bookUrl NOT LIKE 'AIProbe%' "
                "ORDER BY totalChapterNum DESC LIMIT 1"
            ).fetchone()
            if not row:
                row = cur.execute(
                    "SELECT bookUrl FROM books WHERE type = 0 "
                    "AND bookUrl NOT LIKE 'l2://%' LIMIT 1"
                ).fetchone()
            if not row:
                row = cur.execute("SELECT bookUrl FROM books LIMIT 1").fetchone()
            return row[0] if row else ""
        finally:
            con.close()
    except Exception:
        return ""


def open_reading(d, book_url: str) -> bool:
    """进入阅读页（本地书免网络）"""
    reset_app()
    sh("am", "start", "-n", f"{PKG}/{ACT_READ}", "--es", "bookUrl", book_url)
    time.sleep(5)
    act = ca.sh("dumpsys", "activity", "activities", timeout=30).stdout.decode("utf-8", "ignore")
    ok = "ReadBookActivity" in act
    print(f"  [nav] 阅读页={ok}")
    return ok


def open_read_menu(d) -> bool:
    """点击屏幕中央呼出阅读菜单（SOP 陷阱 4：中央点击是显隐切换）"""
    xml = dump_xml(d)
    if any(k in xml for k in READ_ALOUD_KEYS):
        return True
    w, h = d.window_size()
    d.click(w * 0.5, h * 0.45)
    time.sleep(1.8)
    return True


def reach_casting_manage(d) -> bool:
    """逐层点到「选角模板管理」弹框（返回是否到达）"""
    # 1) 阅读页 → 朗读
    if not open_reading(d, reach_casting_manage.book_url):
        return False
    open_read_menu(d)
    if not tap_by_desc_or_text(d, READ_ALOUD_KEYS):
        print("  [nav-BREAK] 阅读菜单未找到「朗读」入口")
        return False
    time.sleep(3.5)

    # 2) 朗读面板/对话框 → 设置
    if not tap_by_desc_or_text(d, (S_SETTING, "ic_settings")):
        print("  [nav-BREAK] 朗读面板未找到「设置」入口")
        return False
    time.sleep(3.0)

    # 3) ReadAloudConfigDialog → 选角入口
    xml = dump_xml(d)
    if not any(k in xml for k in ("选角", "分镜", "模板")):
        print("  [nav-BREAK] 朗读设置弹框未见选角/模板相关项")
        return False
    if not tap_by_desc_or_text(d, ("选角", "模板", "分镜")):
        print("  [nav-BREAK] 朗读设置弹框未点到选角入口")
        return False
    time.sleep(3.0)

    # 4) TtsCastingPickerDialog → 管理模板
    if not tap_text(d, S_MANAGE_ENTRY, timeout=6):
        print(f"  [nav-BREAK] 选角弹框未找到「{S_MANAGE_ENTRY}」")
        return False
    time.sleep(3.0)
    return S_MANAGE_TITLE in dump_xml(d)


reach_casting_manage.book_url = ""


def t1_active_tag(d) -> bool:
    """B1.4-F78：管理弹框内「使用中」标识"""
    reach_casting_manage.book_url = first_book_url()
    if not reach_casting_manage.book_url:
        print("  [t1] 设备无可读书")
        return False
    if not reach_casting_manage(d):
        print("  [t1][BLOCKED] 导航未达「选角模板管理」（详见上方 nav-BREAK）")
        ca.shot(d, "b1_casting_nav_break")
        return False
    xml = dump_xml(d)
    active = S_ACTIVE_TAG in xml
    ok = active
    print(f"  [t1] 「{S_ACTIVE_TAG}」标识={active}（「启用」≠「使用中」）")
    ca.shot(d, "b1_casting_list")
    return ok


def open_first_template_editor(d) -> bool:
    """在管理列表内点开任一模板的「编辑」（进入编辑器）"""
    if not tap_by_desc_or_text(d, ("编辑", "tts_casting_edit")):
        # 退而点列表首行（部分实现点击行即编辑）
        b = text_bounds(d, 'class="android.widget.TextView"')
        if not b:
            return False
        w, h = d.window_size()
        d.click(b["cx"] / w, b["cy"] / h)
        time.sleep(2.0)
    time.sleep(2.5)
    return True


def t2_add_rule(d) -> bool:
    """B1.5-F76：编辑器内「＋ 添加规则」入口"""
    if not reach_casting_manage(d):
        print("  [t2][BLOCKED] 导航未达管理弹框")
        return False
    if not open_first_template_editor(d):
        print("  [t2][BLOCKED] 未进入模板编辑器")
        return False
    xml = dump_xml(d)
    ok = S_ADD_RULE in xml
    print(f"  [t2] 「{S_ADD_RULE}」入口={ok}")
    ca.shot(d, "b1_casting_editor")
    return ok


def t3_move_top(d) -> bool:
    """B1.5-F77：规则行「置顶」入口（index>0 时出现）"""
    if not reach_casting_manage(d):
        print("  [t3][BLOCKED] 导航未达管理弹框")
        return False
    if not open_first_template_editor(d):
        print("  [t3][BLOCKED] 未进入模板编辑器")
        return False
    xml = dump_xml(d)
    ok = S_MOVE_TOP in xml
    print(f"  [t3] 「{S_MOVE_TOP}」入口={ok}（仅第 2 条起出现，若模板只有 1 条规则则不显示＝符合设计）")
    ca.shot(d, "b1_casting_move_top")
    return ok


STEPS = {"t1": t1_active_tag, "t2": t2_add_rule, "t3": t3_move_top}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()

    d = connect_robust()
    since = ca.device_now()
    ok = True
    scen = (args.scenario or "all").strip()
    targets = ["all"] if scen == "all" else [s.strip() for s in scen.split(",") if s.strip()]
    for sid in targets:
        ca.sh("echo", "alive", timeout=30)
        ok = ca.run_steps(STEPS, scenario=sid,
                          tag_keywords=["AndroidRuntime"], since_ts=since, ctx=d) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())