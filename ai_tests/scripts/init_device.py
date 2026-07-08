"""ai_tests/scripts/init_device.py — uiautomator2 设备初始化（任务 4.1-4.6）

职责：
- 首次连接时 u2.connect 自动推送 atx-agent + uiautomator2-test.apk
- 配置 device 参数（implicitly_wait / operation_timeout / operation_delay）
- 检测 atx-agent 是否运行
- 提供 init_uiautomator2(memu) 工具函数供 M4-M5 复用

依赖：M1 MemuController, uiautomator2>=3.2.0
"""
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uiautomator2 as u2

from ai_tests.config import (
    MEMU_ADB_HOST,
    TIMEOUT_UI_IMPLICIT_WAIT,
    TIMEOUT_UI_OPERATION,
    OPERATION_DELAY_BEFORE,
    OPERATION_DELAY_AFTER,
)
from ai_tests.lib.memu_controller import MemuController

logger = logging.getLogger(__name__)


# === 任务 4.5：检测 atx-agent 是否运行 ===
def is_uiautomator2_ready(memu: MemuController) -> bool:
    """检测 atx-agent 是否在设备上运行

    通过 `adb shell pgrep atx-agent` 检查进程
    Returns: True 表示 atx-agent 已运行，u2.connect 可直接连接
    """
    try:
        rc, stdout, stderr = memu.adb("shell", "pgrep", "atx-agent")
        if rc == 0 and stdout.strip():
            logger.debug(f"atx-agent 进程: {stdout.strip()}")
            return True
        return False
    except Exception as e:
        logger.warning(f"检测 atx-agent 异常: {e}")
        return False


# === 任务 4.3 + 4.4：初始化 uiautomator2 工具函数 ===
def init_uiautomator2(
    memu: MemuController,
    serial: str = MEMU_ADB_HOST,
    retry: int = 3,
) -> Optional[u2.Device]:
    """初始化 uiautomator2，返回 Device 对象

    首次连接时 u2.connect 会自动安装 atx-agent + uiautomator2-test.apk 到设备
    重试机制：首次连接失败时重启 atx-agent 后重试

    Args:
        memu: MemuController 实例（用于检测/重启 atx-agent）
        serial: ADB serial，默认 127.0.0.1:21503
        retry: 重试次数（默认 3）
    Returns: u2.Device 对象，失败返回 None
    """
    for attempt in range(retry):
        try:
            if is_uiautomator2_ready(memu):
                logger.info(f"atx-agent 已运行（尝试 {attempt + 1}），直接连接")
            else:
                logger.info(f"atx-agent 未运行（尝试 {attempt + 1}），首次连接将自动初始化")

            # 任务 4.2：u2.connect 自动初始化 atx-agent
            device = u2.connect(serial)

            # 任务 4.4：配置 device 参数
            device.implicitly_wait(TIMEOUT_UI_IMPLICIT_WAIT)
            # 简化说明：operation_timeout/operation_delay 在 u2 3.x 通过属性设置 | 已知上限：部分版本无 operation_timeout 属性 | 升级路径：基于 settings() 配置（V4）
            try:
                device.operation_timeout = TIMEOUT_UI_OPERATION
            except (AttributeError, TypeError):
                logger.debug("device.operation_timeout 设置跳过（版本不支持）")
            try:
                device.operation_delay = (OPERATION_DELAY_BEFORE, OPERATION_DELAY_AFTER)
            except (AttributeError, TypeError):
                logger.debug("device.operation_delay 设置跳过（版本不支持）")

            logger.info(f"uiautomator2 设备已就绪: {serial}")
            return device
        except Exception as e:
            logger.warning(f"u2.connect 失败（尝试 {attempt + 1}）: {e}")
            # 重试时尝试重启 atx-agent
            if attempt < retry - 1:
                logger.info("尝试重启 atx-agent 后重试...")
                try:
                    # 通过 adb 停止 atx-agent，让 u2 重新启动
                    memu.adb("shell", "am", "force-stop", "com.github.uiautomator")
                    memu.adb("shell", "pkill", "atx-agent")
                except Exception:
                    pass
    logger.error(f"uiautomator2 初始化失败（重试 {retry} 次）")
    return None


# === 任务 4.6：实测验证入口 ===
def main() -> int:
    """命令行入口：初始化并验证 uiautomator2 基本功能

    验证项：
    1. u2.connect 成功（首次自动安装 atx-agent）
    2. device.info 返回设备基本信息
    3. dump_hierarchy 返回有效 XML
    4. screenshot 返回有效 PNG
    """
    import argparse
    import time

    parser = argparse.ArgumentParser(description="初始化 uiautomator2 设备")
    parser.add_argument("--serial", default=MEMU_ADB_HOST, help="ADB serial")
    parser.add_argument(
        "--no-start-memu", action="store_true",
        help="不启动 MEmu（假设已运行）",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    memu = MemuController()

    # 确保 MEmu 运行 + ADB 就绪
    if not args.no_start_memu:
        if not memu.is_running():
            logger.info("启动 MEmu...")
            if not memu.start():
                logger.error("MEmu 启动失败")
                return 1
        if not memu.wait_for_adb():
            logger.error("ADB 就绪超时")
            return 1
    else:
        logger.info("跳过 MEmu 启动（--no-start-memu）")

    # 初始化 uiautomator2
    start = time.time()
    device = init_uiautomator2(memu, args.serial)
    init_duration = time.time() - start
    if device is None:
        logger.error("uiautomator2 初始化失败")
        return 1

    # === 验证基本功能 ===
    print("=" * 60)
    print("uiautomator2 设备初始化验证")
    print("=" * 60)

    # 1. 设备信息
    try:
        info = device.info
        print(f"[1] 初始化耗时: {init_duration:.1f}s")
        print(f"[2] 设备信息:")
        print(f"    displayWidth:  {info.get('displayWidth')}")
        print(f"    displayHeight: {info.get('displayHeight')}")
        print(f"    sdkInt:        {info.get('sdkInt')}")
        print(f"    productName:   {info.get('productName')}")
    except Exception as e:
        print(f"[FAIL] 获取设备信息失败: {e}")
        return 1

    # 2. dump_hierarchy
    try:
        xml = device.dump_hierarchy()
        xml_ok = len(xml) > 100 and "<hierarchy" in xml
        status = "PASS" if xml_ok else "FAIL"
        print(f"[3] dump_hierarchy: [{status}]")
        print(f"    XML 长度: {len(xml)} 字符")
        if xml_ok:
            print(f"    含 <hierarchy> 标签: 是")
        else:
            print(f"    前 200 字符: {xml[:200]}")
            return 1
    except Exception as e:
        print(f"[FAIL] dump_hierarchy 异常: {e}")
        return 1

    # 3. screenshot
    try:
        img = device.screenshot()
        img_ok = img.size[0] > 0 and img.size[1] > 0
        status = "PASS" if img_ok else "FAIL"
        print(f"[4] screenshot:    [{status}]")
        print(f"    图片格式: {img.format}")
        print(f"    图片大小: {img.size}")
        if not img_ok:
            return 1
    except Exception as e:
        print(f"[FAIL] screenshot 异常: {e}")
        return 1

    print("=" * 60)
    print("[PASS] uiautomator2 设备初始化验证通过")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
