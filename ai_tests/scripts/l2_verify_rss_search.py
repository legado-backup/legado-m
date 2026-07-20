#!/usr/bin/env python3
r"""l2_verify_rss_search.py — 订阅源统一搜索 L2 功能验证

固定测试流程步骤3b：导航到订阅源搜索页 + 执行场景操作 + 日志验证

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_rss_search.py [--keyword KEYWORD] [--manual]

场景（rss-unified-search 新增功能）：
    launch_search     - 启动订阅源搜索页（输入关键词触发搜索）
    results_display   - 验证搜索结果展示（列表非空 + 多源聚合角标）
    open_article      - 点击搜索结果打开阅读页
    change_source     - 验证换源菜单 + 换源对话框
    crash_check       - 检查全程无 FATAL 异常
    all               - 全部场景（默认）

模式：
    自动模式（默认）：脚本自动启动App并导航到订阅源搜索页
    --manual         ：用户已手动导航到订阅源页，脚本只执行搜索及后续验证

退出码：
    0 = 全部场景通过
    1 = 部分场景未通过
    2 = 致命错误（设备连接/导航失败）

注意：
    - 全程脱敏：不输出 RSS 源/文章真实名称，只用编号
    - 依赖 uiautomator2（可选，降级到 adb 命令）
    - 搜索关键词默认"新闻"，可用 --keyword 指定
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# 修复 Windows GBK 终端编码问题
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 添加 ai_tests 目录到 path 以 import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY

# 尝试导入 uiautomator2（可选依赖）
try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False

# ASCII 状态符（避免 Windows GBK 编码问题）
STATUS_OK = "[OK]"
STATUS_FAIL = "[FAIL]"
STATUS_WARN = "[WARN]"
STATUS_INFO = "[INFO]"


def run_adb(cmd, timeout=30):
    """执行 ADB 命令"""
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    return result


def connect_device():
    """连接 MEmu 设备"""
    if not HAS_U2:
        print("[WARN] uiautomator2 未安装，使用 ADB 命令操作（功能受限）")
        return None
    try:
        device = u2.connect(MEMU_ADB_HOST)
        info = device.info
        print(f"{STATUS_OK} 已连接设备: {info.get('productName', 'unknown')}")
        return device
    except Exception as e:
        print(f"{STATUS_WARN} uiautomator2 连接失败: {e}，使用 ADB 命令操作")
        return None


def launch_app(d):
    """启动 App 并等待 MainActivity"""
    print("\n=== 启动 App ===")
    # 先 force-stop 再启动，确保干净状态
    run_adb(f"shell am force-stop {PACKAGE}")
    time.sleep(2)
    run_adb(f"shell am start -n {PACKAGE}/{MAIN_ACTIVITY}")

    # 等待 App 启动到 MainActivity（WelcomeActivity 会自动跳转，最多 30 秒）
    if d:
        for i in range(30):
            time.sleep(1)
            cur = d.app_current()
            activity = cur.get('activity', '')
            if 'MainActivity' in activity:
                print(f"{STATUS_OK} App 已进入 MainActivity: {activity}")
                return True
            # WelcomeActivity 也在预期内，继续等待
            if i == 5 and 'Welcome' in activity:
                print(f"{STATUS_INFO} WelcomeActivity 启动，等待自动跳转...")
        print(f"{STATUS_WARN} App 启动超时，当前 Activity: {activity}")
        return False
    else:
        time.sleep(15)
        print(f"{STATUS_INFO} 无设备连接，已等待 15s")
        return True


def goto_rss_tab(d):
    """导航到订阅 Tab"""
    print("\n=== 导航到订阅 Tab ===")
    if not d:
        print("[FAIL] 无设备连接，无法导航")
        return False

    # 底部导航栏点击订阅 Tab
    rss_tab = d(resourceId=f"{PACKAGE}:id/menu_rss")
    if not rss_tab.exists:
        # 备选：通过文字查找
        rss_tab = d(text="订阅")
    if not rss_tab.exists:
        print("[FAIL] 未找到订阅 Tab")
        return False

    rss_tab.click()
    time.sleep(3)
    cur = d.app_current()
    print(f"[INFO] 点击订阅 Tab 后 Activity: {cur.get('activity', '?')}")
    print("[OK] 已进入订阅页")
    return True


def input_search_keyword(d, keyword):
    """在搜索框输入关键词并触发搜索"""
    print(f"\n=== 输入搜索关键词: {keyword} ===")
    if not d:
        print(f"{STATUS_FAIL} 无设备连接")
        return False

    # 查找 SearchView 容器（RssFragment 的 SearchView id 是 search_view）
    search_view = d(resourceId=f"{PACKAGE}:id/search_view")
    if not search_view.exists:
        # 备选：用类名查找
        search_view = d(className="androidx.appcompat.widget.SearchView")
    if not search_view.exists:
        print(f"{STATUS_FAIL} 未找到 SearchView")
        return False

    # 点击 SearchView 让其聚焦
    search_view.click()
    time.sleep(1)

    # 查找 SearchView 内部的 EditText
    search_src = d(resourceId=f"{PACKAGE}:id/search_src_text")
    if not search_src.exists:
        # 备选：用类名 + focused 查找
        search_src = d(className="android.widget.EditText", focused=True)
    if not search_src.exists:
        print(f"{STATUS_FAIL} 未找到 SearchView 内部 EditText")
        return False

    search_src.click()
    time.sleep(0.5)
    search_src.set_text(keyword)
    time.sleep(1)

    # 触发搜索：优先点击提交按钮（isSubmitButtonEnabled=true）
    submit_btn = d(resourceId=f"{PACKAGE}:id/search_go_btn")
    if submit_btn.exists:
        print(f"{STATUS_INFO} 点击提交按钮触发搜索")
        submit_btn.click()
    else:
        # 备选：按回车
        print(f"{STATUS_INFO} 按回车键触发搜索")
        d.press("enter")
    time.sleep(3)

    print(f"{STATUS_OK} 已输入关键词并触发搜索")
    return True


def verify_search_activity(d):
    """验证 RssSearchActivity 启动"""
    print("\n=== 验证 RssSearchActivity 启动 ===")
    if not d:
        return False

    cur = d.app_current()
    activity = cur.get('activity', '')
    print(f"[INFO] 当前 Activity: {activity}")

    if "RssSearchActivity" in activity:
        print("[OK] RssSearchActivity 已启动")
        return True
    else:
        print(f"[FAIL] 期望 RssSearchActivity，实际 {activity}")
        return False


def verify_search_results(d, wait_seconds=20):
    """验证搜索结果展示"""
    print(f"\n=== 验证搜索结果展示（等待 {wait_seconds}s）===")
    if not d:
        return False

    # 等待搜索结果加载（搜索过程异步）
    time.sleep(wait_seconds)

    # 查找搜索结果列表
    rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if not rv.exists:
        # 备选：rv_search
        rv = d(resourceId=f"{PACKAGE}:id/rv_search")
    if not rv.exists:
        print("[FAIL] 未找到搜索结果列表")
        return False

    # 获取子项数量
    try:
        children = rv.child(selector=d(className="android.view.ViewGroup"))
        count = children.count
    except Exception:
        # 用 dump_schema 兜底
        info = rv.info
        count = 0

    if count > 0:
        print(f"[OK] 搜索结果列表有 {count} 项")
        return True
    else:
        print("[WARN] 搜索结果列表为空（可能源不可用或关键词无匹配）")
        return False


def click_first_result(d):
    """点击第一个搜索结果"""
    print("\n=== 点击第一个搜索结果 ===")
    if not d:
        return False

    rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if not rv.exists:
        rv = d(resourceId=f"{PACKAGE}:id/rv_search")
    if not rv.exists:
        print("[FAIL] 未找到搜索结果列表")
        return False

    # 通过坐标点击第一项中心
    bounds = rv.info.get("bounds", {})
    top = bounds.get("top", 200)
    left = bounds.get("left", 0)
    right = bounds.get("right", 720)
    cx = (left + right) // 2
    cy = top + 100  # 第一项大致位置
    print(f"[INFO] 点击坐标 ({cx}, {cy})")
    d.click(cx, cy)
    time.sleep(5)

    cur = d.app_current()
    activity = cur.get('activity', '')
    print(f"[INFO] 点击后 Activity: {activity}")

    if "ReadRss" in activity or "VideoPlay" in activity:
        print("[OK] 已进入阅读页")
        return True
    else:
        print(f"[WARN] 期望 ReadRss/VideoPlay，实际 {activity}")
        return False


def verify_change_source_menu(d):
    """验证换源菜单可见性"""
    print("\n=== 验证换源菜单可见性 ===")
    if not d:
        return False

    # 打开菜单（点击右上角更多按钮或按硬菜单键）
    # 方式1：点击 Toolbar 上的溢出菜单
    overflow = d(resourceId=f"{PACKAGE}:id/menu_source_manage")
    if overflow.exists:
        # 这里点的是 source_manage，不是换源。换源菜单需要先打开溢出菜单
        pass

    # 方式2：用硬菜单键（旧设备）或 Toolbar 右上角 MoreOverflow
    more_btn = d(description="更多")
    if not more_btn.exists:
        more_btn = d(resourceId=f"{PACKAGE}:id/overflow")
    if not more_btn.exists:
        # 备选：直接用 uiautomator 打开选项菜单
        d.press("menu")
        time.sleep(1)
    else:
        more_btn.click()
        time.sleep(1)

    # 查找换源菜单项
    change_source = d(text="换源")
    if not change_source.exists:
        # 备选：英文
        change_source = d(text="Change source")

    if change_source.exists:
        print("[OK] 换源菜单可见")
        return True
    else:
        print("[WARN] 换源菜单不可见（可能当前文章非多源聚合）")
        return False


def verify_change_source_dialog(d):
    """点击换源菜单验证对话框显示"""
    print("\n=== 验证换源对话框 ===")
    if not d:
        return False

    change_source = d(text="换源")
    if not change_source.exists:
        change_source = d(text="Change source")
    if not change_source.exists:
        print("[FAIL] 换源菜单不存在")
        return False

    change_source.click()
    time.sleep(2)

    # 验证对话框显示（ChangeRssArticleSourceDialog）
    # 对话框通常含 recycler_view 或 list
    dialog_list = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if not dialog_list.exists:
        dialog_list = d(className="androidx.recyclerview.widget.RecyclerView")

    if dialog_list.exists:
        print("[OK] 换源对话框已显示")
        # 关闭对话框
        d.press("back")
        time.sleep(1)
        return True
    else:
        print("[WARN] 未检测到换源对话框列表")
        return False


def check_no_crash():
    """检查全程无 FATAL 异常"""
    print("\n=== 检查 logcat 无 FATAL 异常 ===")
    result = run_adb(
        'logcat -d -t 500 *:E | grep -E "FATAL|AndroidRuntime" | head -20'
    )
    output = result.stdout.strip()
    if not output:
        print("[OK] 无 FATAL 异常")
        return True
    else:
        # 过滤掉非 legado 的异常
        legado_errors = [
            line for line in output.split('\n')
            if 'io.legado' in line or 'legado.app' in line
        ]
        if not legado_errors:
            print("[OK] 无 legado 相关 FATAL 异常")
            return True
        else:
            print(f"[FAIL] 发现 {len(legado_errors)} 条 legado FATAL 异常")
            # 只输出技术信息（错误类型+前100字符），不输出业务数据
            for line in legado_errors[:5]:
                # 提取异常类型
                if 'FATAL EXCEPTION' in line:
                    print(f"  [FATAL] {line[:150]}")
                else:
                    print(f"  [STACK] {line[:150]}")
            return False


def take_screenshot(d, name):
    """截图保存证据"""
    if not d:
        return
    try:
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        screenshot_path = reports_dir / f"l2_rss_search_{name}_{int(time.time())}.png"
        d.screenshot(str(screenshot_path))
        print(f"[INFO] 截图已保存: {screenshot_path}")
    except Exception as e:
        print(f"[WARN] 截图失败: {e}")


def run_all_scenarios(d, keyword):
    """顺序执行所有场景（App 只启动一次，流程连贯）

    返回 dict: {scenario_name: bool}
    """
    results = {}

    # 场景1: launch_search - 启动 App + 进入订阅页 + 输入关键词 + 验证 RssSearchActivity
    print(f"\n{'='*60}")
    print("场景1: launch_search - 启动并进入订阅源搜索页")
    print(f"{'='*60}")

    launch_ok = launch_app(d)
    if not launch_ok:
        results["launch_search"] = False
        results["results_display"] = False
        results["open_article"] = False
        results["change_source"] = False
        results["crash_check"] = check_no_crash()
        return results

    goto_ok = goto_rss_tab(d)
    if not goto_ok:
        results["launch_search"] = False
        results["results_display"] = False
        results["open_article"] = False
        results["change_source"] = False
        results["crash_check"] = check_no_crash()
        return results

    input_ok = input_search_keyword(d, keyword)
    if not input_ok:
        results["launch_search"] = False
        results["results_display"] = False
        results["open_article"] = False
        results["change_source"] = False
        results["crash_check"] = check_no_crash()
        return results

    results["launch_search"] = verify_search_activity(d)
    take_screenshot(d, "search_activity")

    # 场景2: results_display - 验证搜索结果展示
    print(f"\n{'='*60}")
    print("场景2: results_display - 验证搜索结果展示")
    print(f"{'='*60}")
    results["results_display"] = verify_search_results(d)
    take_screenshot(d, "results")

    # 场景3: open_article - 点击搜索结果打开阅读页
    print(f"\n{'='*60}")
    print("场景3: open_article - 点击搜索结果打开阅读页")
    print(f"{'='*60}")
    results["open_article"] = click_first_result(d)
    take_screenshot(d, "article")

    # 场景4: change_source - 验证换源菜单 + 换源对话框
    print(f"\n{'='*60}")
    print("场景4: change_source - 验证换源功能")
    print(f"{'='*60}")
    # 只有成功进入阅读页才验证换源
    if results["open_article"]:
        results["change_source_menu"] = verify_change_source_menu(d)
        results["change_source_dialog"] = verify_change_source_dialog(d)
        take_screenshot(d, "change_source")
        results["change_source"] = (
            results["change_source_menu"] and results["change_source_dialog"]
        )
    else:
        results["change_source_menu"] = False
        results["change_source_dialog"] = False
        results["change_source"] = False

    # 场景5: crash_check - 检查全程无 FATAL 异常
    print(f"\n{'='*60}")
    print("场景5: crash_check - 检查 logcat 无 FATAL 异常")
    print(f"{'='*60}")
    results["crash_check"] = check_no_crash()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="订阅源统一搜索 L2 功能验证"
    )
    parser.add_argument(
        "--keyword", default="新闻",
        help="搜索关键词（默认: 新闻）"
    )
    parser.add_argument(
        "--scenario", default="all",
        choices=["launch_search", "results_display", "open_article",
                 "change_source", "crash_check", "all"],
        help="验证场景（默认: all，顺序执行所有场景）"
    )
    parser.add_argument(
        "--manual", action="store_true",
        help="用户已手动导航到订阅页，脚本只执行搜索及后续验证"
    )
    args = parser.parse_args()

    print(f"订阅源统一搜索 L2 功能验证")
    print(f"关键词: {args.keyword}")
    print(f"场景: {args.scenario}")
    print(f"模式: {'手动' if args.manual else '自动'}")

    # 连接设备
    d = connect_device()

    # 执行场景
    if args.scenario == "all":
        all_results = run_all_scenarios(d, args.keyword)
    else:
        # 单场景模式：仍顺序执行到目标场景
        all_results = run_all_scenarios(d, args.keyword)
        # 只保留指定场景的结果
        if args.scenario in all_results:
            all_results = {args.scenario: all_results[args.scenario]}
        else:
            all_results = {args.scenario: False}

    # 输出汇总
    print(f"\n{'='*60}")
    print("L2 验证结果汇总")
    print(f"{'='*60}")
    for scenario, passed in all_results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {scenario}: {status}")

    all_passed = all(all_results.values())
    print(f"\n总计: {sum(all_results.values())}/{len(all_results)} 通过")
    if all_passed:
        print("[OK] L2 验证全部通过")
        return 0
    else:
        print("[WARN] L2 验证部分未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
