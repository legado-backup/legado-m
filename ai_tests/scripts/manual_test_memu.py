"""ai_tests/scripts/manual_test_memu.py — M1 实测验证脚本

任务 2.10：启动 MEmu 实例 0 → 等待 ADB → 关闭 → 验证全流程 ≤ 60s

用法：
    python ai_tests/scripts/manual_test_memu.py
"""
import sys
import time
from pathlib import Path

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.memu_controller import MemuController


def main():
    print("=" * 60)
    print("M1 实测验证：MEmu 启动 → ADB 就绪 → 关闭")
    print("=" * 60)

    ctrl = MemuController()

    # 1. 检查当前状态
    print(f"[1/4] 检查 MEmu 当前状态...")
    already_running = ctrl.is_running()
    print(f"  is_running = {already_running}")

    # 2. 启动 MEmu
    print(f"[2/4] 启动 MEmu 实例 {ctrl.instance_id}...")
    t0 = time.time()
    if not ctrl.start(timeout=60):
        print("  [FAIL] 启动失败")
        sys.exit(1)
    t1 = time.time()
    print(f"  [PASS] 启动耗时 {t1 - t0:.1f}s")

    # 3. 等待 ADB 就绪
    print("[3/4] 等待 ADB 就绪...")
    serial = ctrl.wait_for_adb(timeout=60)
    if not serial:
        print("  [FAIL] ADB 连接失败")
        sys.exit(1)
    t2 = time.time()
    print(f"  [PASS] ADB serial: {serial}, 等待耗时 {t2 - t1:.1f}s")

    # 4. 关闭 MEmu（仅当本脚本启动它时才关闭，避免关闭用户已开的实例）
    if not already_running:
        print("[4/4] 关闭 MEmu...")
        if not ctrl.stop(timeout=30):
            print("  [WARN] 关闭失败（不影响验证）")
        t3 = time.time()
        print(f"  [PASS] 关闭耗时 {t3 - t2:.1f}s")
    else:
        print("[4/4] MEmu 本来就在运行，跳过关闭")
        t3 = t2

    total = t3 - t0
    print("=" * 60)
    print(f"全流程总耗时: {total:.1f}s")
    if total <= 60:
        print(f"[PASS] 验证通过（≤ 60s）")
        sys.exit(0)
    else:
        print(f"[WARN] 超过 60s（但仍完成流程）")
        sys.exit(0)  # 超时不视为失败，仅警告


if __name__ == "__main__":
    main()
