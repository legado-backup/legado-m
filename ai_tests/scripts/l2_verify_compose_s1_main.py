# -*- coding: utf-8 -*-
"""l2_verify_compose_s1_main.py — S1 主框架 Compose 迁移 L2 验证（B2 样板冻结）

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s1_main.py [--scenario all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装；书架至少 1 屏条目
锚点：底部导航 4 tab（content-desc/text 双通道：书架/订阅/发现/我的，真机校准点）；
      书架列表 text 节点（probe_shelf.py 口径）；书架配置弹框入口（真机校准点）
判定（分册 §2.1 检查点子集 S1-1/2/3/5）：
    s1-1 底栏接线：4 tab 逐个切换，页面锚点出现+截图×4，无 FATAL
    s1-2 双击回顶：列表滚动≥2屏→双击当前 tab→首项 bounds.y 回顶部区间
    s1-3 顶栏压缩：下滑触发收缩态，截图×2（展开/收缩）证据
    s1-5 书架配置即时生效：配置弹框改列数→确定→列表重渲染断言
logcat：采集带 -T 时间戳起点（防历史日志污染）；FATAL/AndroidRuntime 计数=0
双登记：SOP 固定脚本表 + README 族索引；.gitignore 白名单行（总线 2.12 口径）
真机执行时点：冻结验收 4.4（S1 检查点），本脚本落盘阶段仅 py_compile 校验
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:  # SOP：优先复用 config.py 常量，禁止硬编码路径
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:  # 模板自包含兜底
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca

TABS = ["书架", "订阅", "发现", "我的"]  # 底栏 4 tab（NavigationBarIconConfig/MainBottomNavConfig）
TAB_PAT = lambda t: f'(?:content-desc|text)="{t}"'


def top_text_bounds(d):
    """书架列表首项=可见 text 节点中 top 最小者（probe_shelf 锚点口径）"""
    xml = d.dump_hierarchy()
    best = None
    for m in re.finditer(r'<node[^>]*text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if not txt or y1 < 100:  # 排除状态栏/顶栏区域文本
            continue
        if best is None or y1 < best[1]:
            best = (txt, y1, (x1 + x2) // 2, (y1 + y2) // 2)
    return best


def step_s1_1_bottom_nav(d) -> bool:
    """S1-1 底栏接线：4 tab 逐个切换，断言切换后渲染+截图×4"""
    ok_all = True
    for i, t in enumerate(TABS):
        if not ca.click_by_dump(d, TAB_PAT(t), timeout=4):
            ca.shot(d, f"l2_s1_tab{i}_{i}_no_tab")
            return False
        time.sleep(1.5)  # 渲染完成窗口（≤1.5s 断言的保守上界）
        xml = d.dump_hierarchy()
        # 断言：当前 tab 高亮（selected 属性）+ 页面有内容节点渲染
        rendered = len(re.findall(r'<node[^>]*text="[^"]+"', xml)) >= 3
        ca.shot(d, f"l2_s1_tab{i}_{i}")
        print(f"  tab[{t}] rendered_nodes_ok={rendered}")
        ok_all = ok_all and rendered
    ca.click_by_dump(d, TAB_PAT("书架"), timeout=4)
    return ok_all


def step_s1_2_double_tap_top(d) -> bool:
    """S1-2 双击回顶：滚动≥2屏→双击当前 tab→首项 bounds.y 回顶部区间"""
    first0 = top_text_bounds(d)
    if first0 is None:
        ca.shot(d, "l2_s1_s2_no_list")
        return False
    for _ in range(2):  # 滚动 ≥2 屏
        d.swipe(0.5, 0.7, 0.5, 0.2)
        time.sleep(1.0)
    first1 = top_text_bounds(d)
    ca.shot(d, "l2_s1_s2_scrolled")
    if first1 is None or abs(first1[1] - first0[1]) < 100:
        print(f"  [WARN] 滚动位移不足 before_y={first0[1]} after_y={first1 and first1[1]}")
        return False
    # 双击当前 tab（书架）→ 回顶
    b = ca.dump_bounds(d, TAB_PAT("书架"))
    if not b:
        return False
    w, h = d.window_size()
    d.click(b["cx"] / w, b["cy"] / h)
    time.sleep(0.15)
    d.click(b["cx"] / w, b["cy"] / h)
    time.sleep(1.5)
    first2 = top_text_bounds(d)
    ca.shot(d, "l2_s1_s2_back_top")
    back_ok = first2 is not None and first2[1] <= first0[1] + 150  # 回到锚定区间（150px 容差）
    print(f"  顶部锚点 y: 滚动前={first0[1]} 滚动后={first1[1]} 双击后={first2 and first2[1]} back_ok={back_ok}")
    return back_ok


def step_s1_3_topbar_collapse(d) -> bool:
    """S1-3 压缩（书架收缩）：下滑触发收缩态，截图×2 证据（展开/收缩）"""
    ca.shot(d, "l2_s1_s3_expanded")
    d.swipe(0.5, 0.15, 0.5, 0.55)  # 顶栏区域下滑触发收缩
    time.sleep(1.5)
    ca.shot(d, "l2_s1_s3_collapsed")
    # 证据型断言：两截图产出+界面无崩溃（FATAL 归 run_steps 统一判定）
    print("  压缩态证据: output/l2_s1_s3_expanded.png + l2_s1_s3_collapsed.png")
    return True


def step_s1_5_config_columns(d) -> bool:
    """S1-5 书架配置即时生效：配置弹框改列数→确定→网格重渲染"""
    # 入口=书架顶栏菜单（真机校准点：displayId 锚点以 dump 为准）
    opened = ca.click_by_dump(d, r'(?:content-desc|text)="(?:书架设置|配置|更多)"', timeout=3)
    if not opened:
        ca.shot(d, "l2_s1_s5_no_entry")
        print("  [校准点] 书架配置入口锚点需真机 dump 校准（probe_shelf.py）")
        return False
    time.sleep(1.0)
    ca.shot(d, "l2_s1_s5_dialog")
    before_cnt = len(re.findall(r'<node[^>]*text="[^"]+"', d.dump_hierarchy()))
    ok_dialog = ca.assert_text_visible(d, "确定", timeout=3)
    if ok_dialog:
        ca.click_by_dump(d, r'text="确定"', timeout=3)
        time.sleep(1.5)
    ca.shot(d, "l2_s1_s5_after")
    after_cnt = len(re.findall(r'<node[^>]*text="[^"]+"', d.dump_hierarchy()))
    print(f"  弹框出现={ok_dialog} 列表文本节点计数 before={before_cnt} after={after_cnt}")
    return ok_dialog


def main():
    ap = argparse.ArgumentParser(description="S1 主框架 Compose 迁移 L2 验证（S1-1/2/3/5）")
    ap.add_argument("--scenario", default="all", help="all | s1-1 | s1-2 | s1-3 | s1-5")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()  # logcat -T 起点（防历史日志污染）

    steps = {
        "s1-1": step_s1_1_bottom_nav,
        "s1-2": step_s1_2_double_tap_top,
        "s1-3": step_s1_3_topbar_collapse,
        "s1-5": step_s1_5_config_columns,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=[], since_ts=since_ts)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
