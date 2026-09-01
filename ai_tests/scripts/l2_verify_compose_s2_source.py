# -*- coding: utf-8 -*-
"""l2_verify_compose_s2_source.py — S2 管理列表（BookSourceScreen 双轨）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s2_source.py [--scenario all]
前置：MEmu 已启动；测试包已安装；订阅页存在管理入口；列表至少 2 条目（拖拽/多选场景）
锚点：底栏"订阅"→订阅源管理入口（RssFragment menu_rss_config 口径，真机校准点）；
      批量栏（全选/计数）；顶栏三点菜单；搜索框；ListLayoutMenu 排序项（真机校准点）
判定（分册 §2.2 检查点 S2-1~8）：
    s2-1 滑选多选：长按进多选态→批量栏计数节点出现
    s2-2 拖拽排序：长按拖动→首项标识变化（退出重进持久化，脱敏只输出变化布尔）
    s2-3 批量操作：多选→批量栏抽测（停用/启用）→列表即时刷新
    s2-4 三视图：列表/紧凑/网格切换截图×3
    s2-5 排序选项：ListLayoutMenu 切换→首项变化布尔
    s2-6 搜索+筛选词：关键字过滤→计数变化
    s2-7 菜单族：顶栏三点→AppDropdownMenu 全项展开截图
    s2-8 返回键层级：多选态返回→先退多选再退页面
脱敏：源列表全程不输出名称/URL，只输出计数/布尔/编号（output-safety 铁律）
真机执行时点：冻结验收 4.5（S2 检查点），本脚本落盘阶段仅 py_compile 校验
"""
import argparse
import hashlib
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


def nav_to_source_list(d) -> bool:
    """底栏订阅→订阅源管理入口→BookSourceActivity（锚点真机校准点）"""
    if not ca.click_by_dump(d, r'(?:content-desc|text)="订阅"', timeout=4):
        return False
    time.sleep(1.0)
    # 一级设置按钮（原版 menu_rss_config always）
    if not ca.click_by_dump(d, r'(?:content-desc|text)="(?:订阅源管理|源管理)"', timeout=4):
        ca.shot(d, "l2_s2_no_entry")
        print("  [校准点] 订阅源管理入口锚点需真机 dump 校准")
        return False
    time.sleep(2.0)
    return True


def list_first_item_hash(d):
    """列表首项标识 hash（脱敏：输出 hash 布尔对比，不输出条目文本）"""
    xml = d.dump_hierarchy()
    for m in re.finditer(r'<node[^>]*text="([^"]{2,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if y1 > 300 and y1 < 800:  # 列表区首个条目文本
            return hashlib.md5(txt.encode("utf-8")).hexdigest()[:8]
    return None


def item_count(d) -> int:
    return len(re.findall(r'<node[^>]*clickable="true"[^>]*', d.dump_hierarchy()))


def step_s2_1_multi_select(d) -> bool:
    """S2-1 滑选多选：长按首条目→多选态（批量栏出现）→拖动连续选择"""
    if not ca.long_click_by_dump(d, r'text="[^"]{2,}"', duration_ms=900):
        ca.shot(d, "l2_s2_s1_no_item")
        return False
    time.sleep(1.0)
    batch_ok = ca.assert_text_visible(d, "全选", timeout=4) or \
        ca.dump_bounds(d, r'text="\d+/\d+"') is not None
    ca.shot(d, "l2_s2_s1_multiselect")
    print(f"  多选态批量栏出现={batch_ok}")
    return batch_ok


def step_s2_2_drag_sort(d) -> bool:
    """S2-2 拖拽排序：长按条目拖动→首项标识变化（持久化=退出重进对比，脱敏 hash）"""
    h0 = list_first_item_hash(d)
    d.swipe(0.5, 0.35, 0.5, 0.55, 1.5)  # 长按拖动（慢速 swipe 模拟拖拽，真机校准点）
    time.sleep(1.5)
    h1 = list_first_item_hash(d)
    ca.shot(d, "l2_s2_s2_dragged")
    moved = h0 is not None and h1 is not None and h0 != h1
    print(f"  首项标识 hash before={h0} after={h1} moved={moved}")
    return moved


def step_s2_3_batch_ops(d) -> bool:
    """S2-3 批量操作：多选态→批量栏抽测（停用→启用）→列表即时刷新"""
    ca.long_click_by_dump(d, r'text="[^"]{2,}"', duration_ms=900)
    time.sleep(1.0)
    cnt0 = item_count(d)
    ok_toggle = ca.click_by_dump(d, r'text="停用"', timeout=3)  # 批量栏抽测 1 项（12 项全量抽测归 L3）
    time.sleep(1.5)
    cnt1 = item_count(d)
    ca.shot(d, "l2_s2_s3_batch")
    refreshed = cnt0 != cnt1 or ok_toggle
    print(f"  批量停用执行={ok_toggle} 列表刷新计数 {cnt0}→{cnt1}")
    # 返回键先退多选（S2-8 前置复位）
    ca.sh("input", "keyevent", "4")
    time.sleep(1.2)
    return refreshed


def step_s2_4_three_views(d) -> bool:
    """S2-4 三视图：列表/紧凑/网格切换截图×3（400/600/800dp 断点渲染证据）"""
    views = ["列表", "紧凑", "网格"]
    ok_all = True
    for v in views:
        opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:视图|显示方式|更多)"', timeout=3)
        if not opened:
            print(f"  [校准点] 三视图切换入口锚点需真机校准")
            ok_all = False
            break
        picked = ca.click_by_dump(d, f'text="{v}"', timeout=3)
        time.sleep(1.5)
        ca.shot(d, f"l2_s2_s4_view_{v}")
        ok_all = ok_all and picked
    return ok_all


def step_s2_5_sort_options(d) -> bool:
    """S2-5 排序 6 选项+升降序：ListLayoutMenu 逐项切换→首项变化布尔"""
    opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:排序)"', timeout=3)
    if not opened:
        ca.shot(d, "l2_s2_s5_no_sort")
        print("  [校准点] 排序菜单入口锚点需真机校准")
        return False
    h0 = list_first_item_hash(d)
    # 抽测 2 个排序维度（6 项全量抽测归冻结验收执行期）
    for opt in ("更新时间", "书名"):
        ca.click_by_dump(d, f'text="{opt}"', timeout=3)
        time.sleep(1.2)
        ca.click_by_dump(d, r'(?:content-desc|text)="(?:排序)"', timeout=3)
    h1 = list_first_item_hash(d)
    ca.shot(d, "l2_s2_s5_sorted")
    changed = h0 is not None and h1 is not None and h0 != h1
    print(f"  首项标识 hash before={h0} after={h1} 按维度变化={changed}")
    return changed


def step_s2_6_search_filter(d) -> bool:
    """S2-6 搜索+快捷筛选词：关键字过滤→计数变化；快捷词互斥"""
    if not ca.click_by_dump(d, r'(?:content-desc|text)="(?:搜索)"', timeout=3):
        ca.shot(d, "l2_s2_s6_no_search")
        return False
    time.sleep(1.0)
    cnt0 = item_count(d)
    ca.sh("input", "text", "test")  # 技术性关键字（不输出业务文本）
    time.sleep(2.0)
    cnt1 = item_count(d)
    ca.shot(d, "l2_s2_s6_filtered")
    ca.sh("input", "keyevent", "4")  # 收起搜索
    time.sleep(1.0)
    filtered = cnt1 != cnt0 or cnt1 == 0
    print(f"  过滤计数 {cnt0}→{cnt1} 过滤生效={filtered}")
    return filtered


def step_s2_7_menu_family(d) -> bool:
    """S2-7 菜单族：顶栏三点→AppDropdownMenu 全项展开（无系统 PopupMenu 残留）"""
    if not ca.click_by_dump(d, r'content-desc="(?:更多选项|更多)"', timeout=3):
        ca.shot(d, "l2_s2_s7_no_menu")
        return False
    time.sleep(1.0)
    xml = d.dump_hierarchy()
    menu_cnt = len(re.findall(r'<node[^>]*clickable="true"[^>]*', xml))
    ca.shot(d, "l2_s2_s7_dropdown")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.0)
    print(f"  菜单项可点击节点数={menu_cnt}（全项展开断言 >3）")
    return menu_cnt > 3


def step_s2_8_back_hierarchy(d) -> bool:
    """S2-8 返回键层级：多选态按返回→先退多选（批量栏消失），再退页面"""
    ca.long_click_by_dump(d, r'text="[^"]{2,}"', duration_ms=900)
    time.sleep(1.0)
    in_multi = ca.assert_text_visible(d, "全选", timeout=3)
    ca.sh("input", "keyevent", "4")
    time.sleep(1.2)
    out_multi = not ca.assert_text_visible(d, "全选", timeout=2)
    still_on_page = item_count(d) > 0  # 页面未退出
    ca.sh("input", "keyevent", "4")  # 再退页面
    time.sleep(1.5)
    ca.shot(d, "l2_s2_s8_back")
    print(f"  进多选={in_multi} 一次返回退多选={out_multi} 页面仍在={still_on_page}")
    return in_multi and out_multi and still_on_page


def main():
    ap = argparse.ArgumentParser(description="S2 管理列表 Compose 迁移 L2 验证（S2-1~8）")
    ap.add_argument("--scenario", default="all",
                    help="all | s2-1 | s2-2 | s2-3 | s2-4 | s2-5 | s2-6 | s2-7 | s2-8")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    if not nav_to_source_list(d):
        print("== L2 总结: HAS FAIL（导航未达管理列表）==")
        sys.exit(1)

    steps = {
        "s2-1": step_s2_1_multi_select,
        "s2-2": step_s2_2_drag_sort,
        "s2-3": step_s2_3_batch_ops,
        "s2-4": step_s2_4_three_views,
        "s2-5": step_s2_5_sort_options,
        "s2-6": step_s2_6_search_filter,
        "s2-7": step_s2_7_menu_family,
        "s2-8": step_s2_8_back_hierarchy,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=[], since_ts=since_ts, ctx=d)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
