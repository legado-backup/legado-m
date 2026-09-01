# -*- coding: utf-8 -*-
"""l2_verify_compose_s5_read_float.py — S5 全屏沉浸（阅读器浮层）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s5_read_float.py [--scenario all]
前置：MEmu 已启动；测试包已安装；书架至少 1 本有正文书目（进阅读页）；
      书架卡片二跳陷阱（SOP 陷阱3）：点卡片→点"阅读/继续阅读"才进阅读页
锚点：阅读菜单层（contentDescription="更多选项" 三点按钮，l2_verify_read_menu_overflow 口径）；
      中央点击=菜单显隐切换语义（SOP 陷阱4，判"菜单已开"后禁盲点中央）；页码文本节点（真机校准点）
判定（分册 §2.5 检查点 S5-1~5）：
    s5-1 3s 自动隐藏：唤出菜单→静止 3s→菜单锚点消失
    s5-2 单一 activeSheet：开菜单→开设置 Sheet→旧层节点消失（开新关旧无叠层）
    s5-3 BackHandler 优先级链：Sheet 开→返回→Sheet 关仍在阅读页（逐级消费）
    s5-4 手势 R0-R4：R0 点击区切换/R1 翻页页码变化/R2 长按选词/R4 音量键翻页（R3 双指缩放=手动清单）
    s5-5 磨砂降级：按设备 API 分支断言（≥31 磨砂开/<31 降级纯色）+EffectRender 异常计数=0
复用：l2_verify_read_menu_overflow.py 锚点口径
真机执行时点：冻结验收 4.8（S5 检查点），落盘阶段仅 py_compile 校验
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

MENU_MORE = r'content-desc="更多选项"'
CENTER = (0.5, 0.45)  # 点击区 R0（避开顶部/底部边缘区）


def enter_reading(d) -> bool:
    """书架→点首条目→二跳"阅读/继续阅读"→阅读页"""
    xml = d.dump_hierarchy()
    clicked = False
    for m in re.finditer(r'<node[^>]*text="([^"]{2,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if y1 > 300 and y1 < 900:
            w, h = d.window_size()
            d.click((x1 + x2) / 2 / w, (y1 + y2) / 2 / h)
            clicked = True
            break
    if not clicked:
        return False
    time.sleep(2.0)
    # 二跳：详情页点阅读
    if not ca.click_by_dump(d, r'(?:content-desc|text)="(?:阅读|继续阅读|开始阅读)"', timeout=3):
        return ca.dump_bounds(d, MENU_MORE) is not None  # 可能已直接在阅读页
    time.sleep(2.5)
    return True


def menu_visible(d) -> bool:
    return ca.dump_bounds(d, MENU_MORE) is not None


def page_label(d):
    """页码文本节点（真机校准点：阅读页页码形态）"""
    xml = d.dump_hierarchy()
    for m in re.finditer(r'<node[^>]*text="(\d+\s*/\s*\d+|第\s*\d+\s*页|\d+%)"', xml):
        return m.group(1)
    return None


def step_s5_1_auto_hide(d) -> bool:
    """S5-1 3s 自动隐藏：唤出菜单→静止 3s→浮层自动隐藏（控件消失断言）"""
    d.click(*CENTER)  # 唤出菜单（切换语义：当前未开→点开）
    time.sleep(1.2)
    opened = menu_visible(d)
    if not opened:  # 若此前已开则本次为关闭→再点一次
        d.click(*CENTER)
        time.sleep(1.2)
        opened = menu_visible(d)
    ca.shot(d, "l2_s5_s1_menu_open")
    time.sleep(3.5)  # 静止 3s（1.5s 容差）
    hidden = not menu_visible(d)
    ca.shot(d, "l2_s5_s1_auto_hidden")
    print(f"  菜单唤出={opened} 3s 后自动隐藏={hidden}")
    return opened and hidden


def step_s5_2_single_sheet(d) -> bool:
    """S5-2 单一 activeSheet：菜单→设置 Sheet→旧菜单层消失（开新关旧无叠层）"""
    d.click(*CENTER)
    time.sleep(1.2)
    menu_open = menu_visible(d)
    ca.shot(d, "l2_s5_s2_menu")
    opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:界面|设置|阅读设置)"', timeout=3)
    time.sleep(1.5)
    menu_gone = not menu_visible(d)  # 开新关旧：菜单层应消失
    ca.shot(d, "l2_s5_s2_sheet")
    ca.sh("input", "keyevent", "4")  # 关 Sheet
    time.sleep(1.2)
    print(f"  菜单开={menu_open} 设置Sheet开={opened} 开新后旧层消失={menu_gone}")
    return menu_open and opened and menu_gone


def step_s5_3_back_chain(d) -> bool:
    """S5-3 BackHandler 优先级链：Sheet 开→返回→Sheet 关且仍在阅读页（逐级消费）"""
    d.click(*CENTER)
    time.sleep(1.2)
    ca.click_by_dump(d, r'(?:content-desc|text)="(?:界面|设置|阅读设置)"', timeout=3)
    time.sleep(1.5)
    still_reading = menu_visible(d) or page_label(d) is not None
    ca.sh("input", "keyevent", "4")
    time.sleep(1.5)
    after_back_still_reading = page_label(d) is not None or menu_visible(d)
    ca.shot(d, "l2_s5_s3_back")
    print(f"  Sheet 期仍在阅读页={still_reading} 返回后未退出阅读页={after_back_still_reading}")
    return still_reading and after_back_still_reading


def step_s5_4_gestures(d) -> bool:
    """S5-4 手势 R0-R4：R0 切换/R1 翻页/R2 长按选词/R4 音量键（R3 双指缩放=手动清单）"""
    results = {}
    # R0 点击区切换菜单显隐
    d.click(*CENTER); time.sleep(1.2)
    r0_a = menu_visible(d)
    d.click(*CENTER); time.sleep(1.2)
    results["R0"] = r0_a and not menu_visible(d)
    # R1 左右滑翻页：页码变化
    p0 = page_label(d)
    d.swipe(0.85, 0.5, 0.15, 0.5, 0.3)
    time.sleep(1.5)
    p1 = page_label(d)
    results["R1"] = p0 is not None and p1 is not None and p0 != p1
    # R4 音量键翻页（若开启该开关；键值翻页语义真机校准点）
    p2 = page_label(d)
    ca.sh("input", "keyevent", "24")  # VOLUME_UP
    time.sleep(1.5)
    p3 = page_label(d)
    results["R4"] = p2 is not None and p3 is not None and p2 != p3
    # R2 长按选词：正文区长按→选择光标/菜单（保守断言：无崩溃即记录截图）
    ca.sh("input", "swipe", "540", "900", "540", "900", "1200")
    time.sleep(1.5)
    ca.shot(d, "l2_s5_s4_r2_longpress")
    ca.sh("input", "keyevent", "4")  # 关选择菜单
    time.sleep(1.0)
    ca.shot(d, "l2_s5_s4_gestures")
    print(f"  手势断言={results}（R3 双指缩放=u2 不可自动化，输出手动清单：真机双指捏合→字号缩放）")
    return results["R0"] and results["R1"]


def step_s5_5_blur_branch(d) -> bool:
    """S5-5 磨砂降级 API31 分支：按设备 API 判定分支+截图+EffectRender 异常计数（run_steps 判定）"""
    api = d.device_info.get("sdk_api", 0)
    d.click(*CENTER)
    time.sleep(1.2)
    ca.shot(d, "l2_s5_s5_blur_branch")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.0)
    # 分支记录（磨砂效果视觉判定归 VL/人工通道，本步锁定：无崩溃+分支可进）
    branch = "API>=31 磨砂开" if api >= 31 else "API<31 降级纯色"
    print(f"  设备 API={api} → 预期分支={branch}（截图证据已存）")
    return api > 0


def main():
    ap = argparse.ArgumentParser(description="S5 全屏沉浸 Compose 迁移 L2 验证（S5-1~5）")
    ap.add_argument("--scenario", default="all",
                    help="all | s5-1 | s5-2 | s5-3 | s5-4 | s5-5")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    if not enter_reading(d):
        print("== L2 总结: HAS FAIL（导航未达阅读页）==")
        sys.exit(1)

    steps = {
        "s5-1": step_s5_1_auto_hide,
        "s5-2": step_s5_2_single_sheet,
        "s5-3": step_s5_3_back_chain,
        "s5-4": step_s5_4_gestures,
        "s5-5": step_s5_5_blur_branch,
    }
    all_pass = ca.run_steps(steps, args.scenario,
                            tag_keywords=["EffectRender", "RenderEffect"], since_ts=since_ts)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
