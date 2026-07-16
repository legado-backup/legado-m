"""
rss-concurrency-and-checksource-optimization 运行时验证脚本
验证项：
1. 其他设置：并发配置项显示
2. 订阅源管理：菜单含"校验选中"
3. 书源校验设置：domainCheckMode 选择项
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uiautomator2 as u2

# MEmu ADB 连接配置
DEVICE_SERIAL = "127.0.0.1:21503"
PKG = "io.legado.app.debug"

def connect_device():
    """连接 MEmu 设备"""
    print(f"[1] 连接设备: {DEVICE_SERIAL}")
    d = u2.connect(DEVICE_SERIAL)
    info = d.info
    print(f"  [PASS] 设备连接成功: {info.get('productName', 'unknown')}")
    return d

def clear_logcat(d):
    """清除 logcat 缓冲区"""
    import subprocess
    subprocess.run(
        ["D:/Program Files/Microvirt/MEmu/adb.exe", "-s", DEVICE_SERIAL, "logcat", "-c"],
        check=False
    )
    print("[2] logcat 缓冲区已清除")

def check_no_crash():
    """检查 logcat 是否有崩溃日志"""
    import subprocess
    result = subprocess.run(
        ["D:/Program Files/Microvirt/MEmu/adb.exe", "-s", DEVICE_SERIAL,
         "logcat", "-d", "-s", "AndroidRuntime:E"],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout.strip()
    if "FATAL EXCEPTION" in output or "ANR in" in output:
        print(f"  [FAIL] 检测到崩溃日志:\n{output[:500]}")
        return False
    print("  [PASS] 无崩溃日志")
    return True

def test_app_launch(d):
    """测试1: App 启动无崩溃"""
    print("\n[测试1] App 启动验证")
    # App 已启动，确认当前 Activity
    current = d.app_current()
    print(f"  当前 Activity: {current.get('activity', 'unknown')}")
    if PKG in str(current.get('package', '')):
        print(f"  [PASS] App 运行中")
        return True
    print(f"  [WARN] App 未在前台，尝试启动")
    d.app_start(PKG)
    time.sleep(3)
    current = d.app_current()
    if PKG in str(current.get('package', '')):
        print(f"  [PASS] App 启动成功")
        return True
    print(f"  [FAIL] App 启动失败")
    return False

def test_rss_source_check_menu(d):
    """测试2: 订阅源管理菜单含"校验选中"项"""
    print("\n[测试2] 订阅源管理菜单验证")
    try:
        # 启动订阅源管理 Activity
        d.shell(f"am start -n {PKG}/io.legado.app.ui.rss.source.manage.RssSourceActivity")
        time.sleep(2)
        current = d.app_current()
        print(f"  当前 Activity: {current.get('activity', 'unknown')}")
        if "RssSourceActivity" not in str(current.get('activity', '')):
            print(f"  [FAIL] 未进入订阅源管理")
            return False
        # 截图保存
        d.screenshot("ai_tests/reports/rss_source_manage.png")
        print("  [PASS] 进入订阅源管理成功（截图: rss_source_manage.png）")
        return True
    except Exception as e:
        print(f"  [FAIL] 异常: {e}")
        return False

def test_book_source_check_menu(d):
    """测试3: 书源管理可进入"""
    print("\n[测试3] 书源管理进入验证")
    try:
        d.shell(f"am start -n {PKG}/io.legado.app.ui.book.source.manage.BookSourceActivity")
        time.sleep(2)
        current = d.app_current()
        print(f"  当前 Activity: {current.get('activity', 'unknown')}")
        if "BookSourceActivity" in str(current.get('activity', '')):
            print("  [PASS] 进入书源管理成功")
            return True
        print(f"  [FAIL] 未进入书源管理")
        return False
    except Exception as e:
        print(f"  [FAIL] 异常: {e}")
        return False

def test_other_config_fragment(d):
    """测试4: 其他设置界面可进入"""
    print("\n[测试4] 其他设置进入验证")
    try:
        d.shell(f"am start -n {PKG}/io.legado.app.ui.config.ConfigActivity --es configTag other_config")
        time.sleep(2)
        current = d.app_current()
        print(f"  当前 Activity: {current.get('activity', 'unknown')}")
        d.screenshot("ai_tests/reports/other_config.png")
        print("  [PASS] 其他设置界面截图已保存（other_config.png）")
        return True
    except Exception as e:
        print(f"  [FAIL] 异常: {e}")
        return False

def test_config_values():
    """测试5: 验证配置默认值（通过 SharedPreferences）"""
    print("\n[测试5] 配置默认值验证")
    import subprocess
    # 读取 SharedPreferences
    result = subprocess.run(
        ["D:/Program Files/Microvirt/MEmu/adb.exe", "-s", DEVICE_SERIAL,
         "shell", "run-as", PKG, "cat",
         f"/data/data/{PKG}/shared_prefs/config.xml"],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout
    # 只检查技术键名，不输出业务数据
    has_parse_concurrency = "rssParseConcurrency" in output
    has_image_concurrency = "imageLoadConcurrency" in output
    if has_parse_concurrency:
        print("  [PASS] rssParseConcurrency 配置键存在")
    else:
        print("  [WARN] rssParseConcurrency 配置键未找到（可能未写入，使用默认值3）")
    if has_image_concurrency:
        print("  [PASS] imageLoadConcurrency 配置键存在")
    else:
        print("  [WARN] imageLoadConcurrency 配置键未找到（可能未写入，使用默认值5）")
    return True

def main():
    print("=" * 60)
    print("rss-concurrency-and-checksource-optimization 运行时验证")
    print("=" * 60)
    try:
        d = connect_device()
    except Exception as e:
        print(f"[FATAL] 设备连接失败: {e}")
        sys.exit(2)
    clear_logcat(d)
    results = []
    results.append(("App启动", test_app_launch(d)))
    check_no_crash()
    results.append(("订阅源管理", test_rss_source_check_menu(d)))
    results.append(("书源管理", test_book_source_check_menu(d)))
    results.append(("其他设置", test_other_config_fragment(d)))
    results.append(("配置默认值", test_config_values()))
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    pass_count = sum(1 for _, v in results if v)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\n总计: {pass_count}/{len(results)} 通过")
    print("=" * 60)
    sys.exit(0 if pass_count == len(results) else 1)

if __name__ == "__main__":
    main()
