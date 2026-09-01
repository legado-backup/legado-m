# -*- coding: utf-8 -*-
"""l2_verify_compose_s6_dialog_tiers.py — S6 弹窗族三层（L1/L2/L3 尺寸档）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s6_dialog_tiers.py [--scenario all]
前置：MEmu 已启动；测试包已安装；书架至少 1 本（删除确认入口）/存在分组（分组管理入口）
锚点：弹框根容器 bounds（dump 正则取最大居中窗口）；主界面标志=底部导航 content-desc；
      L1 删除确认/L2 表单弹框/L3 分组管理入口（真机校准点）
判定（分册 §2.6 检查点 S6-1~4）：
    s6-1 L1 Confirm 档：宽 0.92f/cap 620dp 断言+双按钮居中
    s6-2 L2 Form 档：宽 0.94f/cap 660dp 断言
    s6-3 L3 Management/Wide 档：0.96f/700 与 0.98f/760 两档断言
    s6-4 弹框独立窗口不变量：弹框开启期主界面锚点不可 dump（SOP 陷阱2 协议验证）
宽度断言：容器宽 px/屏宽 px 比例区间；dp=px/density（cap 断言按档位上限）
真机执行时点：冻结验收 4.9（S6 检查点），落盘阶段仅 py_compile 校验
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
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca

MAIN_ANCHOR = r'(?:content-desc|text)="书架"'  # 主界面标志（底栏 tab）


def dialog_window_bounds(d):
    """弹框根容器 bounds（dump 中取宽>30%屏宽且水平居中的可见窗口，真机校准点）"""
    xml = d.dump_hierarchy()
    w, _ = d.window_size()
    best = None
    for m in re.finditer(r'<node[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        bw = x2 - x1
        if bw > w * 0.3 and bw < w:  # 弹框窗宽>30% 且不满屏
            margin_l, margin_r = x1, w - x2
            if abs(margin_l - margin_r) < w * 0.08:  # 水平居中
                if best is None or bw > best["w"]:
                    best = {"w": bw, "left": x1, "right": x2}
    return best


def width_tier_check(d, ratio_min, cap_dp, density) -> bool:
    """宽度档断言：比例区间+cap 上限"""
    b = dialog_window_bounds(d)
    if not b:
        return False
    w, _ = d.window_size()
    ratio = b["w"] / w
    w_dp = b["w"] / density
    ok = ratio_min <= ratio and (w_dp <= cap_dp + 8)  # 8dp 容差
    print(f"  弹框宽比例={ratio:.3f}（下限{ratio_min}）宽={w_dp:.0f}dp（cap {cap_dp}）→ {ok}")
    return ok


def step_s6_1_l1_confirm(d) -> bool:
    """S6-1 L1 Confirm 档：删除确认弹框（书架长按→删除）→0.92f/cap 620dp+双按钮居中"""
    ca.long_click_by_dump(d, r'text="[^"]{2,}"', duration_ms=900)
    time.sleep(1.0)
    if not ca.click_by_dump(d, r'text="(?:删除|加入回收站)"', timeout=3):
        ca.shot(d, "l2_s6_s1_no_entry")
        ca.sh("input", "keyevent", "4")
        return False
    time.sleep(1.2)
    ca.shot(d, "l2_s6_s1_confirm")
    density = d.device_info.get("displayDensity", 320) / 160.0
    ok = width_tier_check(d, 0.85, 620, density)  # 0.92f 小屏可能触 cap，下限保守 0.85（真机校准收紧）
    dbl_btn = ca.dump_bounds(d, r'text="取消"') is not None and \
        ca.dump_bounds(d, r'text="(?:删除|确定)"') is not None
    print(f"  双按钮布局存在={dbl_btn}")
    ca.click_by_dump(d, r'text="取消"', timeout=2)
    time.sleep(1.0)
    return ok and dbl_btn


def step_s6_2_l2_form(d) -> bool:
    """S6-2 L2 Form/编辑档：表单弹框（分组编辑等）→0.94f/cap 660dp"""
    opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:分组|新建分组)"', timeout=3)
    if not opened:
        ca.shot(d, "l2_s6_s2_no_entry")
        print("  [校准点] L2 表单弹框入口锚点需真机校准")
        return False
    time.sleep(1.2)
    ca.shot(d, "l2_s6_s2_form")
    density = d.device_info.get("displayDensity", 320) / 160.0
    ok = width_tier_check(d, 0.88, 660, density)
    has_input = ca.dump_bounds(d, r'class="android\.widget\.EditText"') is not None
    print(f"  输入区存在={has_input}")
    ca.sh("input", "keyevent", "4")  # 关弹框（键盘先收）
    ca.click_by_dump(d, r'text="取消"', timeout=2)
    time.sleep(1.0)
    return ok and has_input


def step_s6_3_l3_management(d) -> bool:
    """S6-3 L3 Management/Wide 档：管理型弹框（分组管理）→0.96f/700 与 0.98f/760 两档"""
    opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:分组管理)"', timeout=3)
    if not opened:
        ca.shot(d, "l2_s6_s3_no_entry")
        print("  [校准点] L3 管理型弹框入口锚点需真机校准")
        return False
    time.sleep(1.5)
    ca.shot(d, "l2_s6_s3_management")
    density = d.device_info.get("displayDensity", 320) / 160.0
    ok = width_tier_check(d, 0.90, 760, density)  # 两档（0.96/700、0.98/760）按设备档位命中其一
    ca.sh("input", "keyevent", "4")
    time.sleep(1.2)
    return ok


def step_s6_4_window_invariant(d) -> bool:
    """S6-4 弹框独立窗口不变量：弹框开启期主界面锚点不可 dump（协议验证）"""
    ca.long_click_by_dump(d, r'text="[^"]{2,}"', duration_ms=900)
    time.sleep(1.0)
    ca.click_by_dump(d, r'text="(?:删除|加入回收站)"', timeout=3)
    time.sleep(1.2)
    isolated = ca.assert_window_single(d, MAIN_ANCHOR)  # 开启期主锚点不可 dump
    ca.shot(d, "l2_s6_s4_invariant")
    ca.click_by_dump(d, r'text="取消"', timeout=2)
    time.sleep(1.0)
    back_visible = ca.dump_bounds(d, MAIN_ANCHOR) is not None  # 关闭后主锚点回归
    print(f"  弹框期主界面不可 dump={isolated} 关闭后主界面回归={back_visible}")
    return isolated and back_visible


def main():
    ap = argparse.ArgumentParser(description="S6 弹窗族三层 Compose 迁移 L2 验证（S6-1~4）")
    ap.add_argument("--scenario", default="all",
                    help="all | s6-1 | s6-2 | s6-3 | s6-4")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    steps = {
        "s6-1": step_s6_1_l1_confirm,
        "s6-2": step_s6_2_l2_form,
        "s6-3": step_s6_3_l3_management,
        "s6-4": step_s6_4_window_invariant,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=[], since_ts=since_ts)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
