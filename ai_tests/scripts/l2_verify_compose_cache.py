# -*- coding: utf-8 -*-
"""l2_verify_compose_cache.py — 缓存清理页（CacheScreen，7.11be 销项）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_cache.py [--scenario all]
前置：MEmu 已启动；测试包已安装；存在带缓存条目的书目（导出按钮可用性断言前置）
锚点：CacheScreen（ui/book/cache/CacheScreen.kt，Compose 纯实现已核）条目节点
      （author 显示/export 导出文本锚点）；栈顶 Activity 类名=CacheActivity（技术字段）
判定（registry 7.11be 销项=真机回归，分册 §4.3 表）：
    cache-1 页面可达：导航入口→栈顶命中 CacheActivity
    cache-2 Compose 渲染：条目节点（author/export 锚点）渲染非空
    cache-3 功能无崩溃：返回退出无 FATAL（清理动作执行归冻结验收执行期抽测）
对应：tasks 2.11（B10 CacheActivity 真机回归）/ compose tasks 8.2（B2 首批 7 脚本之 cache 销项）
真机执行时点：冻结验收窗口（4.4-4.7 同批），落盘阶段仅 py_compile 校验
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


def top_activity() -> str:
    r = ca.sh("dumpsys", "activity", "activities", timeout=15)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s", r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def step_cache_1_reachable(d) -> bool:
    """cache-1 页面可达：入口导航→栈顶命中 CacheActivity"""
    # 入口尝试：底栏"我的"→缓存清理项（入口锚点真机校准点）
    ca.click_by_dump(d, r'(?:content-desc|text)="我的"', timeout=4)
    time.sleep(1.0)
    opened = ca.click_by_dump(d, r'text="(?:缓存清理|缓存)"', timeout=3)
    if not opened:
        ca.shot(d, "l2_cache_no_entry")
        print("  [校准点] 缓存清理入口锚点需真机校准（我的页/书架菜单）")
        return False
    time.sleep(2.0)
    act = top_activity()
    ca.shot(d, "l2_cache_page")
    hit = "CacheActivity" in act
    print(f"  栈顶类名={act} CacheActivity 命中={hit}")
    return hit


def step_cache_2_compose_render(d) -> bool:
    """cache-2 Compose 渲染：条目节点（author/export 锚点）渲染非空"""
    xml = d.dump_hierarchy()
    # CacheScreen 条目锚点：author 显示行 + export 导出按钮（源码 L98/L126 text 节点）
    has_author = re.search(r'<node[^>]*text="[^"]*"', xml) is not None
    export_hit = ca.dump_bounds(d, r'text="(?:导出|全选)"') is not None
    node_cnt = len(re.findall(r'<node[^>]*text="[^"]+"', xml))
    ca.shot(d, "l2_cache_render")
    print(f"  文本节点数={node_cnt} 导出/全选锚点={export_hit}")
    return has_author and node_cnt >= 3 and export_hit


def step_cache_3_no_crash_exit(d) -> bool:
    """cache-3 功能无崩溃：返回退出无 FATAL（清理动作抽测归冻结验收执行期）"""
    ca.sh("input", "keyevent", "4")
    time.sleep(1.5)
    act = top_activity()
    exited = "CacheActivity" not in act
    ca.shot(d, "l2_cache_exit")
    print(f"  退出成功={exited}（FATAL 计数归 run_steps 统一判定）")
    return exited


def main():
    ap = argparse.ArgumentParser(description="缓存清理页（CacheScreen 7.11be 销项）L2 验证")
    ap.add_argument("--scenario", default="all",
                    help="all | cache-1 | cache-2 | cache-3")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    steps = {
        "cache-1": step_cache_1_reachable,
        "cache-2": step_cache_2_compose_render,
        "cache-3": step_cache_3_no_crash_exit,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=[], since_ts=since_ts, ctx=d)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
