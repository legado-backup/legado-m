"""ai_tests/lib/apk_deployer.py — M2 APK 部署模块

职责：自动发现最新 APK + 安装 + 启动 + 等待首屏

🔒 固化层文件：AI 不应直接修改，必须通过 OpenSpec 流程

依赖：M1 MemuController
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional

from ai_tests.config import (
    APK_GLOB_DIR, PACKAGE, MAIN_ACTIVITY,
    TIMEOUT_APK_INSTALL, TIMEOUT_FIRST_FRAME,
)
from ai_tests.lib.memu_controller import MemuController

logger = logging.getLogger(__name__)


class ApkDeployer:
    """APK 部署器

    提供：
    - discover_apk：自动发现最新 APK（按 mtime）
    - validate_apk：校验 APK 文件有效性
    - install：安装 APK（memuc 优先，adb 降级）
    - uninstall / clear_data：清理旧版与数据
    - start_app：启动 App
    - wait_for_first_frame：等待首屏渲染
    """

    def __init__(
        self,
        memu: Optional[MemuController] = None,
        apk_glob_dir: Path = APK_GLOB_DIR,
    ):
        self.memu = memu if memu is not None else MemuController()
        self.apk_glob_dir = Path(apk_glob_dir)

    # === APK 发现与校验 ===

    def discover_apk(self, apk_dir: Optional[Path] = None) -> Optional[str]:
        """自动发现最新 APK（按 mtime 取最新）

        扫描 apk_dir 下的 *.apk 文件，返回最新修改的 APK 路径
        Returns: APK 文件路径，无 APK 时返回 None
        """
        search_dir = Path(apk_dir) if apk_dir else self.apk_glob_dir
        if not search_dir.exists():
            logger.warning(f"APK 目录不存在: {search_dir}")
            return None

        apks = list(search_dir.glob("*.apk"))
        if not apks:
            logger.warning(f"目录下无 APK 文件: {search_dir}")
            return None

        # 按 mtime 取最新
        latest = max(apks, key=lambda p: p.stat().st_mtime)
        logger.info(f"发现最新 APK: {latest.name} (mtime={time.ctime(latest.stat().st_mtime)})")
        return str(latest)

    def validate_apk(self, apk_path: str) -> bool:
        """校验 APK 文件有效性

        检查：文件存在 + .apk 后缀 + 大小 > 1MB
        """
        p = Path(apk_path)
        if not p.exists() or not p.is_file():
            logger.error(f"APK 文件不存在: {apk_path}")
            return False
        if p.suffix.lower() != ".apk":
            logger.error(f"非 APK 文件: {apk_path}")
            return False
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb < 1:
            logger.error(f"APK 文件过小 ({size_mb:.2f} MB): {apk_path}")
            return False
        logger.debug(f"APK 校验通过: {p.name} ({size_mb:.2f} MB)")
        return True

    # === 安装与卸载 ===

    def install(self, apk_path: str) -> bool:
        """安装 APK

        优先 memuc installapp，失败降级 adb install -r -d
        """
        if not self.validate_apk(apk_path):
            return False

        # 方案 1：memuc installapp
        if self.memu.install_app(apk_path):
            logger.info(f"APK 安装成功（memuc）: {Path(apk_path).name}")
            return True

        # 方案 2：降级 adb install -r -d
        logger.warning("memuc installapp 失败，降级 adb install -r -d")
        try:
            rc, stdout, stderr = self.memu.adb(
                "install", "-r", "-d", apk_path, timeout=TIMEOUT_APK_INSTALL
            )
            if rc == 0 and "Success" in stdout:
                logger.info(f"APK 安装成功（adb）: {Path(apk_path).name}")
                return True
            logger.error(f"adb install 失败: rc={rc}, stdout={stdout}, stderr={stderr}")
            return False
        except Exception as e:
            logger.error(f"adb install 异常: {e}")
            return False

    def uninstall(self, package: str = PACKAGE) -> bool:
        """卸载 App"""
        return self.memu.uninstall_app(package)

    def clear_data(self, package: str = PACKAGE) -> bool:
        """清除 App 数据（adb shell pm clear）"""
        try:
            rc, stdout, stderr = self.memu.adb("shell", "pm", "clear", package)
            if rc == 0 and "Success" in stdout:
                logger.info(f"App 数据已清除: {package}")
                return True
            logger.warning(f"清除数据失败: rc={rc}, stdout={stdout}")
            return False
        except Exception as e:
            logger.error(f"清除数据异常: {e}")
            return False

    # === 启动与等待 ===

    def start_app(
        self, package: str = PACKAGE, activity: str = MAIN_ACTIVITY
    ) -> bool:
        """启动 App"""
        return self.memu.start_app(package, activity)

    def wait_for_first_frame(self, timeout: int = TIMEOUT_FIRST_FRAME) -> bool:
        """等待 App 首屏渲染

        抓 logcat "Displayed io.legado.app" 关键字
        """
        # 先清空 logcat 缓冲
        self.memu.adb("logcat", "-c")

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                rc, stdout, stderr = self.memu.adb(
                    "logcat", "-d", "-v", "brief",
                    "ActivityManager:I", "*:S",
                    timeout=10,
                )
                if "Displayed " + PACKAGE in stdout:
                    logger.info("App 首屏已渲染")
                    return True
            except Exception:
                pass
            time.sleep(1)
        logger.error(f"等待首屏超时（{timeout}s）")
        return False

    # === 一键部署 ===

    def deploy(self, apk_path: Optional[str] = None) -> bool:
        """一键部署：发现+校验+安装+启动+等待首屏

        Args:
            apk_path: 指定 APK 路径，None 时自动发现
        Returns: True 部署成功
        """
        # 1. 发现 APK
        if apk_path is None:
            apk_path = self.discover_apk()
            if not apk_path:
                logger.error("未发现可用 APK")
                return False

        # 2. 校验
        if not self.validate_apk(apk_path):
            return False

        # 3. 安装
        if not self.install(apk_path):
            return False

        # 4. 启动
        if not self.start_app():
            return False

        # 5. 等待首屏
        if not self.wait_for_first_frame():
            logger.warning("首屏等待超时，但 App 可能已启动")
            # 不视为失败，仅警告

        logger.info(f"APK 部署完成: {Path(apk_path).name}")
        return True
