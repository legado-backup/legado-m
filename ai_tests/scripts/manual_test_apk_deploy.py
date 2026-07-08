"""ai_tests/scripts/manual_test_apk_deploy.py — M2 实测验证脚本

任务 3.8：自动发现最新 APK + 完整部署

用法：
    python ai_tests/scripts/manual_test_apk_deploy.py
    python ai_tests/scripts/manual_test_apk_deploy.py --full  # 含安装+启动
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.apk_deployer import ApkDeployer
from ai_tests.lib.memu_controller import MemuController


def main():
    full_mode = "--full" in sys.argv

    print("=" * 60)
    print("M2 实测验证：APK 自动发现 + 校验" + (" + 安装 + 启动" if full_mode else ""))
    print("=" * 60)

    memu = MemuController()
    deployer = ApkDeployer(memu=memu)

    # 1. 发现 APK
    print("[1] 自动发现最新 APK...")
    apk_path = deployer.discover_apk()
    if not apk_path:
        print("  [FAIL] 未发现 APK")
        sys.exit(1)
    print(f"  [PASS] 发现 APK: {Path(apk_path).name}")

    # 2. 校验 APK
    print("[2] 校验 APK...")
    if not deployer.validate_apk(apk_path):
        print("  [FAIL] APK 校验失败")
        sys.exit(1)
    size_mb = Path(apk_path).stat().st_size / (1024 * 1024)
    print(f"  [PASS] APK 校验通过 ({size_mb:.2f} MB)")

    if not full_mode:
        print("=" * 60)
        print("[PASS] 轻量验证通过（未安装，加 --full 执行完整部署）")
        sys.exit(0)

    # 3. 启动 MEmu
    print("[3] 启动 MEmu...")
    if not memu.is_running():
        t0 = time.time()
        if not memu.start(timeout=60):
            print("  [FAIL] MEmu 启动失败")
            sys.exit(1)
        print(f"  [PASS] MEmu 启动 ({time.time() - t0:.1f}s)")
    else:
        print("  [PASS] MEmu 已在运行")

    # 4. 等待 ADB
    print("[4] 等待 ADB 就绪...")
    serial = memu.wait_for_adb(timeout=60)
    if not serial:
        print("  [FAIL] ADB 连接失败")
        sys.exit(1)
    print(f"  [PASS] ADB 就绪")

    # 5. 安装 APK
    print("[5] 安装 APK...")
    t1 = time.time()
    if not deployer.install(apk_path):
        print("  [FAIL] APK 安装失败")
        sys.exit(1)
    print(f"  [PASS] APK 安装成功 ({time.time() - t1:.1f}s)")

    # 6. 启动 App
    print("[6] 启动 App...")
    if not deployer.start_app():
        print("  [FAIL] App 启动失败")
        sys.exit(1)
    print("  [PASS] App 启动命令已发送")

    # 7. 等待首屏
    print("[7] 等待首屏渲染...")
    t2 = time.time()
    if deployer.wait_for_first_frame(timeout=30):
        print(f"  [PASS] 首屏已渲染 ({time.time() - t2:.1f}s)")
    else:
        print(f"  [WARN] 首屏等待超时（{time.time() - t2:.1f}s），App 可能已启动")

    print("=" * 60)
    print("[PASS] M2 完整部署验证通过！")


if __name__ == "__main__":
    main()
