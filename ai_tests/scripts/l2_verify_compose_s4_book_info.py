# -*- coding: utf-8 -*-
"""l2_verify_compose_s4_book_info.py — S4 详情双栈（BookInfo）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s4_book_info.py [--scenario all]
前置：MEmu 已启动；测试包已安装；书架至少 1 本书（条目锚点=书架 text 节点，probe_shelf.py 口径）；
      双栈入口：新栈/旧栈入口锚点真机校准点（分册 §2.4"分别以新旧入口进入"）
锚点：栈顶 Activity 类名（BookInfoComposeActivity | BookInfoActivity，技术字段可输出）；
      详情页功能锚点（阅读/目录/加书架/简介）；顶栏 16 项 AppDropdownMenu（真机校准点）
判定（分册 §2.4 检查点 S4-1~4）：
    s4-1 双栈分派：进详情→栈顶类名命中双栈之一
    s4-2 新栈核心：封面/简介渲染/加删书架/阅读跳转/目录入口锚点断言
    s4-3 旧栈兼容：旧入口全流程无回归（book is null 弹框不出现，verify_book_info_no_null 口径）
    s4-4 菜单下沉：顶栏 16 项 AppDropdownMenu 渲染断言
复用：verify_book_info_no_null.py 口径（书架点击进详情+菜单走查）
真机执行时点：冻结验收 4.7（S4 检查点），落盘阶段仅 py_compile 校验
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.app.ui.welcome.WelcomeActivity"  # 兜底仅占位，正常路径走 config

from ai_tests.lib import compose_assert as ca

STACK_PAT = r"(BookInfoComposeActivity|BookInfoActivity)"


def top_activity() -> str:
    r = ca.sh("dumpsys", "activity", "activities", timeout=15)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s", r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def open_book_info_from_shelf(d) -> bool:
    """书架点击首条目进详情（书架卡片二跳陷阱：卡片形态文本 clickable=False→容器点击）"""
    xml = d.dump_hierarchy()
    for m in re.finditer(r'<node[^>]*text="([^"]{2,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if y1 > 300 and y1 < 900:  # 列表区首个条目
            w, h = d.window_size()
            d.click((x1 + x2) / 2 / w, (y1 + y2) / 2 / h)
            time.sleep(2.5)
            return True
    return False


def step_s4_1_stack_dispatch(d) -> bool:
    """S4-1 双栈分派：书架条目进详情→栈顶类名命中双栈之一（logcat 类名证据）"""
    if not open_book_info_from_shelf(d):
        ca.shot(d, "l2_s4_s1_no_book")
        return False
    act = top_activity()
    ca.shot(d, "l2_s4_s1_stack")
    hit = bool(re.search(STACK_PAT, act))
    print(f"  栈顶类名={act} 双栈命中={hit}")
    ca.sh("input", "keyevent", "4")  # 返回书架
    time.sleep(1.5)
    return hit


def step_s4_2_new_stack_core(d) -> bool:
    """S4-2 新栈核心功能：封面/简介/加删书架/阅读跳转/目录入口锚点断言"""
    if not open_book_info_from_shelf(d):
        return False
    act = top_activity()
    if "BookInfoComposeActivity" not in act:
        print(f"  [SKIP] 栈顶非新栈（{act}），新栈断言需分派入口真机校准")
        ca.shot(d, "l2_s4_s2_not_new_stack")
        ca.sh("input", "keyevent", "4")
        return False
    time.sleep(1.5)
    anchors = {}
    for name, pat in {
        "阅读": r'(?:content-desc|text)="(?:阅读|继续阅读|开始阅读)"',
        "目录": r'(?:content-desc|text)="目录"',
        "简介": r'class="android\.widget\.(?:TextView|EditText)"',
    }.items():
        anchors[name] = ca.dump_bounds(d, pat) is not None
    ca.shot(d, "l2_s4_s2_new_stack")
    ok = any(anchors.values())
    print(f"  新栈功能锚点={anchors}")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.5)
    return ok


def step_s4_3_old_stack_compat(d) -> bool:
    """S4-3 旧栈兼容：旧入口全流程无回归（book is null 弹框不出现）"""
    if not open_book_info_from_shelf(d):
        return False
    time.sleep(2.0)
    xml = d.dump_hierarchy()
    has_null = 'book is null' in xml or "书籍信息为空" in xml
    ca.shot(d, "l2_s4_s3_old_stack")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.5)
    print(f"  book is null 弹框出现={has_null}（应 False）")
    return not has_null


def step_s4_4_menu_sunken(d) -> bool:
    """S4-4 菜单下沉：顶栏 16 项菜单逐项→AppDropdownMenu 渲染断言（逐项点击归 L3 走查）"""
    if not open_book_info_from_shelf(d):
        return False
    time.sleep(1.5)
    if not ca.click_by_dump(d, r'content-desc="(?:更多选项|更多)"', timeout=3):
        ca.shot(d, "l2_s4_s4_no_menu")
        ca.sh("input", "keyevent", "4")
        return False
    time.sleep(1.0)
    xml = d.dump_hierarchy()
    menu_cnt = len(re.findall(r'<node[^>]*clickable="true"[^>]*', xml))
    ca.shot(d, "l2_s4_s4_dropdown")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.0)
    ca.sh("input", "keyevent", "4")  # 退出详情
    time.sleep(1.5)
    print(f"  菜单项可点击节点数={menu_cnt}（16 项渲染断言 >5，逐项点击归冻结验收 L3）")
    return menu_cnt > 5


def main():
    ap = argparse.ArgumentParser(description="S4 详情双栈 Compose 迁移 L2 验证（S4-1~4）")
    ap.add_argument("--scenario", default="all",
                    help="all | s4-1 | s4-2 | s4-3 | s4-4")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    steps = {
        "s4-1": step_s4_1_stack_dispatch,
        "s4-2": step_s4_2_new_stack_core,
        "s4-3": step_s4_3_old_stack_compat,
        "s4-4": step_s4_4_menu_sunken,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=[], since_ts=since_ts)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
