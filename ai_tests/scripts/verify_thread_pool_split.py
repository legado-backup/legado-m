#!/usr/bin/env python3
r"""verify_thread_pool_split.py — 线程池拆分配置 E2E 验证

固定测试流程：验证书源线程池拆分配置（searchThreadCount + updateCacheThreadCount）

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/verify_thread_pool_split.py [--adb-host HOST] [--package PACKAGE]

场景（thread-pool-split-config 新增功能）：
    ui_display       - 验证"其他设置"页显示两个新配置项，兼容字段隐藏
    set_search       - 调整搜索线程数为 8，验证 summary 实时更新
    set_update_cache - 调整更新和缓存线程数为 4，验证 summary 实时更新
    restore_default  - 恢复默认值（32/16），验证持久化
    all              - 全部场景（默认）

退出码：
    0 = 全部场景通过
    1 = 部分场景未通过
    2 = 致命错误（设备连接/导航失败）

注意：
    - 全程脱敏：不输出业务数据，只输出技术结论
    - 依赖 adb 命令（无需 uiautomator2）
    - 默认连接 127.0.0.1:21523（实例2），可用 --adb-host 指定
"""
import argparse
import re
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH

STATUS_OK = "[OK]"
STATUS_FAIL = "[FAIL]"
STATUS_WARN = "[WARN]"
STATUS_INFO = "[INFO]"

DEFAULT_ADB_HOST = "127.0.0.1:21523"
DEFAULT_PACKAGE = "io.legado.miss.app.debug"
CONFIG_ACTIVITY = "io.legado.app.ui.config.ConfigActivity"
MAIN_ACTIVITY = "io.legado.app.ui.main.MainActivity"


def run_adb(adb_host: str, cmd: str, timeout: int = 30) -> str:
    """执行 ADB 命令，返回 stdout"""
    full_cmd = f'"{ADB_PATH}" -s {adb_host} {cmd}'
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    return result.stdout or ""


def dump_ui(adb_host: str, local_path: str) -> str:
    """dump UI 到本地文件，返回文件内容"""
    run_adb(adb_host, "shell uiautomator dump /sdcard/verify_ui.xml")
    run_adb(adb_host, f'pull /sdcard/verify_ui.xml "{local_path}"')
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"{STATUS_FAIL} 读取 UI dump 失败: {e}")
        return ""


def start_config_activity(adb_host: str, package: str) -> bool:
    """启动 ConfigActivity 进入"其他设置"页"""
    out = run_adb(adb_host, f"shell am start -W -n {package}/{CONFIG_ACTIVITY} --es configTag otherConfig")
    if "Status: ok" in out or "Complete" in out:
        print(f"{STATUS_OK} 已启动 ConfigActivity (otherConfig)")
        return True
    print(f"{STATUS_FAIL} 启动 ConfigActivity 失败: {out.strip()}")
    return False


def scroll_to_thread_config(adb_host: str) -> bool:
    """滑动到线程池配置项位置（最多滑动 8 次）"""
    for i in range(8):
        content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "scroll_check.xml"))
        if "搜索线程数" in content and "更新和缓存线程数" in content:
            print(f"{STATUS_OK} 已定位到线程池配置项（滑动 {i} 次）")
            return True
        run_adb(adb_host, "shell input swipe 640 600 640 200 300")
        time.sleep(1)
    print(f"{STATUS_FAIL} 滑动 8 次仍未找到线程池配置项")
    return False


def find_preference_bounds(content: str, title: str) -> tuple:
    """查找指定 preference_title 的父 LinearLayout bounds，返回 (x, y) 中心点"""
    idx = content.find(title)
    if idx < 0:
        return None
    start = max(0, idx - 600)
    snippet = content[start:idx]
    bounds_list = re.findall(r'bounds="(\[(\d+),(\d+)\]\[(\d+),(\d+)\])"', snippet)
    if not bounds_list:
        return None
    # 取最后一个 bounds（最接近 title 的父节点）
    b = bounds_list[-1]
    x1, y1, x2, y2 = int(b[1]), int(b[2]), int(b[3]), int(b[4])
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def get_summary_value(content: str, title: str) -> str:
    """提取指定配置项的 summary 中的"当前 X"值"""
    # 找 title 后面的 desc
    idx = content.find(title)
    if idx < 0:
        return ""
    snippet = content[idx:idx + 500]
    m = re.search(r'当前\s*(\d+)', snippet)
    return m.group(1) if m else ""


def open_number_picker(adb_host: str, content: str, title: str) -> bool:
    """点击指定配置项打开 NumberPickerDialog"""
    bounds = find_preference_bounds(content, title)
    if not bounds:
        print(f"{STATUS_FAIL} 未找到 '{title}' 的 bounds")
        return False
    x, y = bounds
    run_adb(adb_host, f"shell input tap {x} {y}")
    time.sleep(2)
    print(f"{STATUS_OK} 已点击 '{title}' (x={x}, y={y})")
    return True


def set_number_picker_value(adb_host: str, value: int) -> bool:
    """在 NumberPickerDialog 中设置值并确认"""
    # 点击 EditText（中心位置）
    run_adb(adb_host, "shell input tap 639 410")
    time.sleep(1)
    # 清空并输入新值
    run_adb(adb_host, "shell input keyevent KEYCODE_MOVE_END")
    run_adb(adb_host, "shell input keyevent KEYCODE_DEL")
    run_adb(adb_host, "shell input keyevent KEYCODE_DEL")
    run_adb(adb_host, f"shell input text {value}")
    time.sleep(1)
    # 点击确认按钮
    run_adb(adb_host, "shell input tap 925 587")
    time.sleep(2)
    print(f"{STATUS_OK} 已设置值 {value} 并确认")
    return True


def verify_dialog_value(adb_host: str, expected: int) -> bool:
    """验证 NumberPickerDialog 当前值"""
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "dialog_verify.xml"))
    inputs = re.findall(r'text="([^"]*)"[^>]*resource-id="android:id/numberpicker_input"', content)
    if not inputs:
        inputs = re.findall(r'resource-id="android:id/numberpicker_input"[^>]*text="([^"]*)"', content)
    if not inputs:
        print(f"{STATUS_FAIL} 未找到 NumberPicker 当前值")
        return False
    actual = inputs[0]
    if actual == str(expected):
        print(f"{STATUS_OK} NumberPicker 当前值 = {actual}（预期 {expected}）")
        return True
    print(f"{STATUS_FAIL} NumberPicker 当前值 = {actual}（预期 {expected}）")
    return False


def scene_ui_display(adb_host: str, package: str) -> bool:
    """场景1：验证两个新配置项显示，兼容字段隐藏"""
    print(f"\n{STATUS_INFO} === 场景1: ui_display ===")
    if not start_config_activity(adb_host, package):
        return False
    if not scroll_to_thread_config(adb_host):
        return False
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "ui_display.xml"))
    # 验证两个新配置项显示
    has_search = "搜索线程数" in content
    has_update = "更新和缓存线程数" in content
    # 验证旧 threadCount 兼容字段隐藏（不应出现"更新和搜索线程数"这个旧标题）
    # 简化说明：旧 threadCount 的 title 是 threads_num_title（"更新和搜索线程数"），isPreferenceVisible=false 应隐藏
    # 已知上限：无法直接验证 isPreferenceVisible，但若隐藏则 UI dump 中不应出现旧标题
    # 升级路径：检查 SharedPreferences 中 threadCount 的可见性标志
    has_legacy_visible = "更新和搜索线程数" in content  # 旧标题字符串
    if has_search and has_update and not has_legacy_visible:
        print(f"{STATUS_OK} 两个新配置项显示正常，兼容字段已隐藏")
        return True
    print(f"{STATUS_FAIL} 配置项显示异常: search={has_search}, update={has_update}, legacy_visible={has_legacy_visible}")
    return False


def scene_set_search(adb_host: str) -> bool:
    """场景2：调整搜索线程数为 8，验证 summary"""
    print(f"\n{STATUS_INFO} === 场景2: set_search ===")
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "before_set_search.xml"))
    if not open_number_picker(adb_host, content, "搜索线程数"):
        return False
    if not verify_dialog_value(adb_host, 32):
        return False
    if not set_number_picker_value(adb_host, 8):
        return False
    # 验证 summary 更新
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "after_set_search.xml"))
    val = get_summary_value(content, "搜索线程数")
    if val == "8":
        print(f"{STATUS_OK} 搜索线程数 summary 已更新为 当前 8")
        return True
    print(f"{STATUS_FAIL} 搜索线程数 summary 未更新: 当前 {val}（预期 8）")
    return False


def scene_set_update_cache(adb_host: str) -> bool:
    """场景3：调整更新和缓存线程数为 4，验证 summary"""
    print(f"\n{STATUS_INFO} === 场景3: set_update_cache ===")
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "before_set_update.xml"))
    if not open_number_picker(adb_host, content, "更新和缓存线程数"):
        return False
    if not verify_dialog_value(adb_host, 16):
        return False
    if not set_number_picker_value(adb_host, 4):
        return False
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "after_set_update.xml"))
    val = get_summary_value(content, "更新和缓存线程数")
    if val == "4":
        print(f"{STATUS_OK} 更新和缓存线程数 summary 已更新为 当前 4")
        return True
    print(f"{STATUS_FAIL} 更新和缓存线程数 summary 未更新: 当前 {val}（预期 4）")
    return False


def scene_restore_default(adb_host: str) -> bool:
    """场景4：恢复默认值（32/16），验证持久化"""
    print(f"\n{STATUS_INFO} === 场景4: restore_default ===")
    # 恢复搜索线程数
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "before_restore_search.xml"))
    if not open_number_picker(adb_host, content, "搜索线程数"):
        return False
    if not set_number_picker_value(adb_host, 32):
        return False
    # 恢复更新和缓存线程数
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "before_restore_update.xml"))
    if not open_number_picker(adb_host, content, "更新和缓存线程数"):
        return False
    if not set_number_picker_value(adb_host, 16):
        return False
    # 验证恢复
    content = dump_ui(adb_host, str(Path(__file__).parent.parent.parent / "temp" / "after_restore.xml"))
    search_val = get_summary_value(content, "搜索线程数")
    update_val = get_summary_value(content, "更新和缓存线程数")
    if search_val == "32" and update_val == "16":
        print(f"{STATUS_OK} 已恢复默认值: search=32, updateCache=16")
        return True
    print(f"{STATUS_FAIL} 恢复默认值失败: search={search_val}, updateCache={update_val}")
    return False


def main():
    parser = argparse.ArgumentParser(description="线程池拆分配置 E2E 验证")
    parser.add_argument("--adb-host", default=DEFAULT_ADB_HOST, help=f"ADB 设备地址（默认 {DEFAULT_ADB_HOST}）")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help=f"包名（默认 {DEFAULT_PACKAGE}）")
    parser.add_argument("--scene", default="all", choices=["ui_display", "set_search", "set_update_cache", "restore_default", "all"], help="测试场景")
    args = parser.parse_args()

    print(f"{STATUS_INFO} ADB host: {args.adb_host}")
    print(f"{STATUS_INFO} Package: {args.package}")
    print(f"{STATUS_INFO} Scene: {args.scene}")

    # 确认设备连接
    out = run_adb(args.adb_host, "shell get-state")
    if "device" not in out:
        print(f"{STATUS_FAIL} 设备未连接: {out.strip()}")
        return 2
    print(f"{STATUS_OK} 设备已连接: {args.adb_host}")

    results = {}
    if args.scene in ("ui_display", "all"):
        results["ui_display"] = scene_ui_display(args.adb_host, args.package)
    if args.scene in ("set_search", "all"):
        results["set_search"] = scene_set_search(args.adb_host)
    if args.scene in ("set_update_cache", "all"):
        results["set_update_cache"] = scene_set_update_cache(args.adb_host)
    if args.scene in ("restore_default", "all"):
        results["restore_default"] = scene_restore_default(args.adb_host)

    # 汇总
    print(f"\n{STATUS_INFO} === 测试汇总 ===")
    all_pass = True
    for name, passed in results.items():
        status = STATUS_OK if passed else STATUS_FAIL
        print(f"  {status} {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n{STATUS_OK} 全部场景通过")
        return 0
    print(f"\n{STATUS_FAIL} 部分场景未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
