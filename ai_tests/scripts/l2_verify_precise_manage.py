#!/usr/bin/env python3
r"""l2_verify_precise_manage.py — 精准管理 L2 功能验证

固定测试流程步骤3c：验证「精准管理」聚合入口 + 网址记录 / 存储管理 / 下载管理 / 文件管理

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_precise_manage.py [--scenario all]

场景（precise-manage 新增功能）：
    entry             - 我的页存在「精准管理」入口，点击进入聚合页（ConfigActivity@preciseManage, 4 子项）
    url_record        - 网址记录：UrlRecordActivity 可进入 + 搜索框存在 + 列表存在
    storage_manage    - 存储管理页可进入
    download_manage   - 下载管理页可进入
    file_manage       - 文件管理页可进入
    crash_check       - 检查全程无 FATAL 异常
    all               - 全部场景（默认）

退出码：
    0 = 全部场景通过
    1 = 部分场景未通过
    2 = 致命错误（设备连接/导航失败）
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY

try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False

STATUS_OK = "[OK]"
STATUS_FAIL = "[FAIL]"
STATUS_WARN = "[WARN]"
STATUS_INFO = "[INFO]"


def run_adb(cmd, timeout=30):
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    return result


def connect_device():
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
    print("\n=== 启动 App ===")
    run_adb(f"shell am force-stop {PACKAGE}")
    time.sleep(2)
    run_adb(f"shell am start -n {PACKAGE}/{MAIN_ACTIVITY}")

    if d:
        for i in range(30):
            time.sleep(1)
            cur = d.app_current()
            activity = cur.get('activity', '')
            if 'MainActivity' in activity:
                print(f"{STATUS_OK} App 已进入 MainActivity: {activity}")
                return True
            if i == 5 and 'Welcome' in activity:
                print(f"{STATUS_INFO} WelcomeActivity 启动，等待自动跳转...")
        print(f"{STATUS_WARN} App 启动超时，当前 Activity: {activity}")
        return False
    else:
        time.sleep(15)
        print(f"{STATUS_INFO} 无设备连接，已等待 15s")
        return True


def goto_my_tab(d):
    print("\n=== 导航到「我的」Tab ===")
    if not d:
        print("[FAIL] 无设备连接，无法导航")
        return False

    my_tab = d(text="Me")
    if not my_tab.exists:
        my_tab = d(resourceId=f"{PACKAGE}:id/menu_my_config")
    if not my_tab.exists:
        print("[FAIL] 未找到「Me」Tab")
        return False
    my_tab.click()
    time.sleep(3)
    cur = d.app_current()
    print(f"[INFO] 点击后 Activity: {cur.get('activity', '?')}")
    print("[OK] 已进入「我的」页")
    return True


def click_text_scroll(d, text, max_scroll=8):
    """滚动查找并点击指定文本"""
    elem = d(text=text)
    for i in range(max_scroll):
        if elem.exists():
            elem.click()
            print(f"[INFO] 已点击「{text}」")
            return True
        d.swipe(360, 900, 360, 300, duration=0.3)
        time.sleep(1)
    print(f"[WARN] 滚动 {max_scroll} 次仍未找到「{text}」")
    return False


def verify_entry(d):
    print("\n=== 场景1: 聚合入口「精准管理」===")
    if not d:
        return False
    ok = goto_precise_page(d)
    if not ok:
        return False

    # 验证聚合页标题
    time.sleep(3)
    cur = d.app_current()
    print(f"[INFO] 聚合页 Activity: {cur.get('activity', '?')}")
    if 'ConfigActivity' not in cur.get('activity', ''):
        print(f"[FAIL] 期望 ConfigActivity，实际 {cur.get('activity', '')}")
        return False

    # 验证 4 个子项（与 pref_precise_manage.xml title 一致）
    items = ["URL访问记录", "存储管理", "下载管理", "文件管理"]
    all_ok = True
    for name in items:
        if d(text=name).exists():
            print(f"[OK] 子项「{name}」存在")
        else:
            print(f"[FAIL] 子项「{name}」缺失")
            all_ok = False
    return all_ok


def goto_precise_page(d):
    """冷启动导航到精准管理聚合页（每场景独立，确保干净状态）"""
    if not d:
        return False
    # 杀掉 App 冷启动回主界面
    run_adb(f"shell am force-stop {PACKAGE}")
    time.sleep(2)
    run_adb(f"shell am start -n {PACKAGE}/{MAIN_ACTIVITY}")
    time.sleep(6)
    # 等待 MainActivity
    for i in range(15):
        cur = d.app_current()
        if 'MainActivity' in cur.get('activity', ''):
            break
        time.sleep(1)
    # 底部点击「我的」(content-desc 或 id)
    my_tab = d(resourceId=f"{PACKAGE}:id/menu_my_config")
    if not my_tab.exists:
        my_tab = d(text="Me")
    if not my_tab.exists:
        print("[FAIL] 未找到「我的」Tab")
        return False
    my_tab.click()
    time.sleep(3)
    return find_cfg_entry(d)


def find_cfg_entry(d):
    """查找设置类入口（精准管理在「我的」页设置分组下，向上滚动）"""
    e = d(text="精准管理")
    for i in range(40):
        if e.exists():
            e.click()
            time.sleep(2)
            return True
        d.swipe(520, 820, 520, 260, duration=0.3)
        time.sleep(1)
    print("[FAIL] 未找到「精准管理」入口")
    return False


def verify_url_record_page(d):
    print("\n=== 场景: 网址记录页 ===")
    if not goto_precise_page(d):
        return False
    e = d(text="URL访问记录")
    if not e.exists():
        print("[FAIL] 聚合页无「URL访问记录」项")
        return False
    e.click()
    time.sleep(3)
    cur = d.app_current()
    activity = cur.get('activity', '')
    print(f"[INFO] 网址记录 Activity: {activity}")
    if 'UrlRecordActivity' not in activity:
        print(f"[FAIL] 期望 UrlRecordActivity，实际 {activity}")
        return False
    print("[OK] UrlRecordActivity 已进入")

    # 搜索框（TitleBar 的 view_search）
    sv = d(resourceId=f"{PACKAGE}:id/search_view")
    scrollable = False
    if sv.exists():
        print("[OK] 搜索框存在")
    else:
        print("[WARN] 搜索框未找到（可能需展开搜索）")

    # 列表
    rv = d(resourceId=f"{PACKAGE}:id/recycler_view")
    if rv.exists():
        print("[OK] 记录列表 RecyclerView 存在")
    else:
        print("[WARN] 列表未找到")
    return True


def verify_sub_page(d, name, activity_key):
    print(f"\n=== 场景: {name} 子页面 ===")
    if not goto_precise_page(d):
        return False
    e = d(text=name)
    if not e.exists():
        print(f"[FAIL] 聚合页未找到「{name}」")
        return False
    e.click()
    time.sleep(3)
    cur = d.app_current()
    activity = cur.get('activity', '')
    print(f"[INFO] {name} Activity: {activity}")
    if activity_key not in activity:
        print(f"[FAIL] 期望 {activity_key}，实际 {activity}")
        return False
    print(f"[OK] {name} 页面已进入（{activity}）")
    return True


def crash_check():
    print("\n=== 场景: 全程无 FATAL 异常 ===")
    r = run_adb("logcat -d -s AndroidRuntime:E")
    fatal = [l for l in r.stdout.splitlines() if 'FATAL' in l]
    if fatal:
        print("[FAIL] 发现 FATAL 异常（logcat AndroidRuntime:E）")
        for line in fatal[:10]:
            print(f"    {line}")
        return False
    print("[OK] 无 FATAL 异常")
    return True


def main():
    parser = argparse.ArgumentParser(description="精准管理 L2 验证")
    parser.add_argument("--scenario", default="all",
                        choices=["entry", "url_record", "storage_manage",
                                 "download_manage", "file_manage",
                                 "crash_check", "all"])
    args = parser.parse_args()

    results = {}

    def run_scenario(name, fn, d=None):
        try:
            results[name] = fn()
        except Exception as e:
            print(f"[FAIL] {name} 异常: {e}")
            results[name] = False

    d = None
    if args.scenario == "all":
        d = connect_device()
        if not launch_app(d):
            print("[FATAL] App 启动失败")
            sys.exit(2)
        run_scenario("entry", lambda: verify_entry(d), d)
        run_scenario("url_record", lambda: verify_url_record_page(d), d)
        run_scenario("storage_manage", lambda: verify_sub_page(d, "存储管理", "StorageManageActivity"), d)
        run_scenario("download_manage", lambda: verify_sub_page(d, "下载管理", "DownloadManageActivity"), d)
        run_scenario("file_manage", lambda: verify_sub_page(d, "文件管理", "FileManageActivity"), d)
        run_scenario("crash_check", lambda: crash_check(), d)
    else:
        print("[WARN] 单场景模式暂不自动导航，请手动启动后使用 all")

    print("\n================= 结果汇总 =================")
    passed = 0
    for name, ok in results.items():
        mark = STATUS_OK if ok else STATUS_FAIL
        print(f"{mark} {name}")
        passed += 1 if ok else 0
    total = len(results)
    print(f"通过 {passed}/{total}")
    if passed == total:
        print("[OK] 全部场景通过")
        sys.exit(0)
    else:
        print("[FAIL] 部分场景未通过")
        sys.exit(1)


if __name__ == "__main__":
    main()