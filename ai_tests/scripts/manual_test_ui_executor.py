"""ai_tests/scripts/manual_test_ui_executor.py — M4 实测验证脚本

任务 6.11：执行 TC-F-P0-1-01 第 1 步"进入我的" → 验证：截图+XML 正确归档

用法：
    python ai_tests/scripts/manual_test_ui_executor.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.config import REPORTS_DIR, PACKAGE
from ai_tests.lib.memu_controller import MemuController
from ai_tests.lib.ui_executor import UiExecutor
from ai_tests.lib.case_parser import Step
from ai_tests.scripts.init_device import init_uiautomator2


def main() -> int:
    print("=" * 60)
    print("M4 实测验证：UI 执行器 - 执行'进入我的'步骤")
    print("=" * 60)

    memu = MemuController()

    # 1. 确保 MEmu 运行
    if not memu.is_running():
        print("[1] 启动 MEmu...")
        if not memu.start():
            print("[FAIL] MEmu 启动失败")
            return 1
    else:
        print("[1] MEmu 已在运行")

    # 2. 等待 ADB 就绪
    if not memu.wait_for_adb():
        print("[FAIL] ADB 就绪超时")
        return 1
    print("[2] ADB 就绪")

    # 3. 初始化 u2
    print("[3] 初始化 uiautomator2...")
    device = init_uiautomator2(memu)
    if device is None:
        print("[FAIL] uiautomator2 初始化失败")
        return 1

    # 4. 检查 App 是否在运行
    rc, stdout, _ = memu.adb("shell", "ps | grep", PACKAGE)
    if rc != 0 or not stdout.strip():
        print("[4] App 未运行，启动 App...")
        if not memu.start_app():
            print("[FAIL] App 启动失败")
            return 1
        time.sleep(3)
    else:
        print("[4] App 已在运行")

    # 5. 创建证据目录
    run_id = time.strftime("%Y%m%d_%H%M%S")
    evidence_dir = REPORTS_DIR / f"m4_test_{run_id}" / "cases" / "TC-F-P0-1-01"
    screenshot_dir = evidence_dir / "screenshots"
    xml_dir = evidence_dir / "xml"
    print(f"[5] 证据目录: {evidence_dir}")

    # 6. 构造步骤：进入"我的"
    # 步骤原文："进入\"我的→调试工具→编码转换\""
    # 我们只验证"进入我的"部分：点击底部 Tab "我的"
    # 注意：底部导航 Tab 用 content-desc 标识，不是 text
    step = Step(
        action="click",
        target="desc=我的",
        raw='进入"我的"页面',
    )

    # 7. 创建 UiExecutor
    executor = UiExecutor(device, memu=memu)

    # 8. 执行步骤（带自愈机制）
    print("\n[6] 执行步骤：进入'我的'页面")
    print(f"    action: {step.action}")
    print(f"    target: {step.target}")
    result = executor.execute_step_with_heal(
        step,
        screenshot_dir=screenshot_dir,
        xml_dir=xml_dir,
        step_index=1,
    )

    # 9. 验证结果
    print("\n[7] 执行结果:")
    print(f"    success: {result['success']}")
    if result.get("error"):
        print(f"    error: {result['error']}")

    print("\n[8] 证据收集:")
    print(f"    before_screenshot: {result['before_screenshot']}")
    print(f"    before_xml:        {result['before_xml']}")
    print(f"    after_screenshot:  {result['after_screenshot']}")
    print(f"    after_xml:         {result['after_xml']}")

    # 10. 验证文件已生成
    print("\n[9] 文件验证:")
    all_pass = True

    for label, path in [
        ("before_screenshot", result["before_screenshot"]),
        ("before_xml", result["before_xml"]),
        ("after_screenshot", result["after_screenshot"]),
        ("after_xml", result["after_xml"]),
    ]:
        if path and Path(path).exists():
            size = Path(path).stat().st_size
            print(f"    [{label}] PASS: {Path(path).name} ({size} bytes)")
        else:
            print(f"    [{label}] FAIL: 文件不存在或为 None")
            all_pass = False

    # 11. 验证"我的"页面切换（Fragment 切换，Activity 仍为 MainActivity）
    print("\n[10] '我的'页面切换验证:")
    time.sleep(1)  # 等待 Fragment 切换
    # "我的"是 MainActivity 内的 Fragment，不切换 Activity
    # 通过检查 after_xml 是否包含"我的"页面特征文本来验证
    after_xml_path = result.get("after_xml")
    if after_xml_path and Path(after_xml_path).exists():
        xml_content = Path(after_xml_path).read_text(encoding="utf-8")
        if "书源管理" in xml_content or "备份与恢复" in xml_content:
            print("    [PASS] 已切换到'我的'页面（检测到书源管理/备份与恢复）")
        else:
            print("    [WARN] 未检测到'我的'页面特征文本")
    else:
        print("    [WARN] after_xml 不存在，无法验证页面切换")

    print("\n" + "=" * 60)
    if all_pass and result["success"]:
        print("[PASS] M4 实测验证通过：截图+XML 正确归档")
        return 0
    else:
        print("[FAIL] M4 实测验证失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
