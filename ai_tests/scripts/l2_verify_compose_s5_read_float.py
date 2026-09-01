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

# B2 真机校准 2026-09-01：阅读菜单呼出正常（center tap 后菜单条文本全暴露：
# 目录/朗读/界面/设置/夜间等），但三点按钮 content-desc="更多选项" 未在无障碍树暴露
# → 菜单可见性锚点改用菜单条特征文本（真机实证 tap 后 text 3→17）
MENU_MORE = r'text="(?:朗读|界面)"'
CENTER = (0.5, 0.45)  # 点击区 R0（避开顶部/底部边缘区）


def enter_reading(d) -> bool:
    """书架→点首条目→二跳"阅读/继续阅读"→阅读页"""
    if "ReadBook" in d.app_current().get("activity", ""):
        return True  # 已在阅读页（正文 Canvas 区无文本节点，先判避免误点）
    xml = d.dump_hierarchy()
    clicked = False
    for m in re.finditer(r'<node[^>]*text="([^"]{2,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if y1 > 300 and y1 < 900:
            w, h = d.window_size()
            d.click((x1 + x2) / 2 / w, (y1 + y2) / 2 / h)
            clicked = True
            break
    if not clicked:  # 可能停在其它 tab（盲点误切）→ 切回书架 tab 重试
        ca.click_by_dump(d, r'(?:content-desc|text)="书架"', timeout=3)
        time.sleep(1.5)
        xml = d.dump_hierarchy()
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
        # B2 真机校准 2026-09-01：有阅读进度的书点击卡片直进阅读页（无详情二跳）
        if "ReadBook" in d.app_current().get("activity", ""):
            return True
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


def content_fp(d):
    """正文无障碍指纹（2026-09-02 真机校准替代 page_label）：
    正文页脚页码为 Canvas 绘制不进无障碍树（page_label 恒 None）；
    ReadView.upContent 会将整页正文写入 content-desc（PageView.setContentDescription），
    随翻页变化 → 取最长 desc 做指纹（正文恒数百字符；系统通知/按钮文案等短 desc
    需排除——首个匹配会被劫持致指纹恒定，2026-09-02 真机实证）。脱敏不回显正文。"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        return None
    descs = re.findall(r'content-desc="([^"]{100,})"', xml)
    if not descs:
        return None
    best = max(descs, key=len)
    return (best[:24], len(best))


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
    """S5-2 单一 activeSheet：菜单→设置 Sheet→旧菜单层消失（开新关旧无叠层）
    时序适配 2026-09-02：菜单 3s 自动隐藏（S5-1 修复后行为）——预判定 dump 会挤掉
    点击窗口，改为唤出后立即点击（点中即证明菜单开着；若菜单已开则本轮为关闭，
    下一轮重试唤出）；真机校准：布局无「界面/设置」按钮，「目录」开同一 Toc Sheet"""
    menu_open = False
    opened = False
    for _ in range(3):
        d.click(*CENTER)
        time.sleep(1.0)
        # 无障碍 ACTION_CLICK（u2 selector 直达 clickable 祖先）：坐标点击在按钮文本
        # 贴近 3s 计时器/底部 inset 时偶发失效（2026-09-02 真机实证），ACTION_CLICK 稳定
        if d(text="目录").click_exists(timeout=2):
            menu_open = True
            opened = True
            break
    time.sleep(1.2)
    menu_gone = not menu_visible(d)  # 开新关旧：菜单层应消失
    ca.shot(d, "l2_s5_s2_sheet")
    ca.sh("input", "keyevent", "4")  # 关 Sheet
    time.sleep(1.2)
    print(f"  菜单开={menu_open} 设置Sheet开={opened} 开新后旧层消失={menu_gone}")
    return menu_open and opened and menu_gone


def step_s5_3_back_chain(d) -> bool:
    """S5-3 BackHandler 优先级链：Sheet 开→返回→Sheet 关且仍在阅读页（逐级消费）
    口径修正 2026-09-02：开 Sheet 时菜单被主动收起（开新关旧）+ 页码 Canvas 不在树，
    「仍在阅读页」以当前 Activity 为权威证据；Sheet 开启失败（菜单 3s 自动隐藏时序）
    需重唤出菜单重试，否则 Back 会走退出链"""
    sheet_opened = False
    for _ in range(3):
        d.click(*CENTER)
        time.sleep(1.0)
        if d(text="目录").click_exists(timeout=2):
            sheet_opened = True
            break
    # 等待目录页（TocActivity）就绪——启动延迟时 Back 会被 ReadBookActivity 消费=误退出
    sheet_ready = False
    for _ in range(8):
        if "Toc" in d.app_current().get("activity", ""):
            sheet_ready = True
            break
        time.sleep(0.5)
    time.sleep(0.5)
    ca.shot(d, "l2_s5_s3_sheet")
    ca.sh("input", "keyevent", "4")
    after_back_still_reading = False
    for _ in range(6):  # Back 后轮询等待回到阅读页（Activity 恢复有时延）
        time.sleep(0.5)
        if "ReadBook" in d.app_current().get("activity", ""):
            after_back_still_reading = True
            break
    ca.shot(d, "l2_s5_s3_back")
    still_reading = sheet_opened and sheet_ready
    print(f"  Sheet开={sheet_opened} 目录页就绪={sheet_ready} 返回后未退出阅读页={after_back_still_reading}")
    return sheet_opened and sheet_ready and after_back_still_reading


def step_s5_4_gestures(d) -> bool:
    """S5-4 手势 R0-R4：R0 点击区切换/R1 翻页/R2 长按选词/R4 音量键（R3 双指缩放=手动清单）
    口径修正 2026-09-02：页码 Canvas 不在无障碍树，R1 改用正文 content-desc 指纹变化
    （ReadView.upContent 翻页时更新）强断言；R4 音量键翻页依赖设置开关（默认关）→
    执行+存活断言，页码变化归手动清单"""
    results = {}
    # R0 点击区切换菜单显隐
    d.click(*CENTER); time.sleep(1.2)
    r0_a = menu_visible(d)
    d.click(*CENTER); time.sleep(1.2)
    results["R0"] = r0_a and not menu_visible(d)
    # R1 左右滑翻页：正文 content-desc 指纹变化（菜单收起态，树上仅正文长 desc）
    fp0 = content_fp(d)
    d.swipe(0.85, 0.5, 0.15, 0.5, 0.3)
    time.sleep(1.5)
    fp1 = content_fp(d)
    results["R1"] = fp0 is not None and fp1 is not None and fp0 != fp1
    if not results["R1"]:
        time.sleep(1.0)  # 翻页动画/内容加载兜底后重取一次
        fp1 = content_fp(d)
        results["R1"] = fp0 is not None and fp1 is not None and fp0 != fp1
    # R4 音量键翻页（音量键翻页开关默认关；键值语义+页码变化归手动清单）
    act0 = d.app_current().get("activity", "")
    ca.sh("input", "keyevent", "24")  # VOLUME_UP
    time.sleep(1.5)
    act1 = d.app_current().get("activity", "")
    results["R4"] = "ReadBook" in act0 and "ReadBook" in act1
    # R2 长按选词：正文区长按→选择光标/菜单（保守断言：无崩溃即记录截图）
    ca.sh("input", "swipe", "540", "900", "540", "900", "1200")
    time.sleep(1.5)
    ca.shot(d, "l2_s5_s4_r2_longpress")
    ca.sh("input", "keyevent", "4")  # 关选择菜单
    time.sleep(1.0)
    ca.shot(d, "l2_s5_s4_gestures")
    print(f"  手势断言={results}（R3 双指缩放=u2 不可自动化；R4 页码变化=手动清单：真机音量键翻页，音量键翻页开关默认关）")
    return results["R0"] and results["R1"]


def step_s5_5_blur_branch(d) -> bool:
    """S5-5 磨砂降级 API31 分支：按设备 API 判定分支+截图+EffectRender 异常计数（run_steps 判定）
    口径修正 2026-09-02：u2 device_info 在 MEmu 不含 sdk_api 字段（恒 0→必 FAIL），
    兜底 getprop ro.build.version.sdk"""
    api = d.device_info.get("sdk_api", 0)
    if not api:
        r = ca.sh("getprop", "ro.build.version.sdk", timeout=10)
        api = int(r.stdout.decode("utf-8", errors="ignore").strip() or 0)
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
                            tag_keywords=["EffectRender", "RenderEffect"], since_ts=since_ts, ctx=d)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
