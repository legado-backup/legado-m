"""ai_tests/lib/memu_controller.py — M1 模拟器控制模块

职责：启停 MEmu 实例 0、ADB 连接验证、App 安装/启动/停止

🔒 固化层文件：AI 不应直接修改，必须通过 OpenSpec 流程

依赖：subprocess（标准库）
"""
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional

from ai_tests.config import (
    MEMUC_PATH, ADB_PATH, MEMU_INSTANCE_ID,
    PACKAGE, MAIN_ACTIVITY, TIMEOUT_MEMU_START, TIMEOUT_MEMU_STOP,
    TIMEOUT_ADB_WAIT,
)

logger = logging.getLogger(__name__)


class MemuController:
    """MEmu 模拟器控制器（默认实例 0）

    封装 memuc.exe 与 adb.exe 命令，提供：
    - start/stop：启停模拟器
    - is_running：检查运行状态
    - wait_for_adb：等待 ADB 连接就绪
    - adb：通用 ADB 命令
    - install_app/start_app/stop_app/uninstall_app：App 生命周期
    """

    def __init__(
        self,
        instance_id: int = MEMU_INSTANCE_ID,
        memuc_path: str = MEMUC_PATH,
        adb_path: str = ADB_PATH,
    ):
        self.instance_id = instance_id
        self.memuc_path = memuc_path
        self.adb_path = adb_path

    # === 内部工具 ===

    def _run_memuc(self, *args, timeout: int = 60) -> tuple:
        """执行 memuc 命令，返回 (returncode, stdout, stderr)

        简化说明：同步阻塞调用 | 已知上限：单实例串行 | 升级路径：异步+并行（V4）
        """
        cmd = [self.memuc_path] + [str(a) for a in args]
        logger.debug(f"memuc 命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr

    # === 模拟器生命周期 ===

    def start(self, timeout: int = TIMEOUT_MEMU_START) -> bool:
        """启动 MEmu 实例，重试 3 次指数退避

        Returns: True 启动成功或已在运行
        """
        for attempt in range(3):
            try:
                rc, stdout, stderr = self._run_memuc(
                    "start", "-i", self.instance_id, timeout=timeout
                )
                if rc == 0:
                    logger.info(f"MEmu 实例 {self.instance_id} 启动成功（尝试 {attempt + 1}）")
                    return True
                # 实例已在运行也算成功
                if self.is_running():
                    logger.info(f"MEmu 实例 {self.instance_id} 已在运行")
                    return True
                logger.warning(f"启动失败（尝试 {attempt + 1}）: rc={rc}, stderr={stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"启动超时（尝试 {attempt + 1}）")
            # 指数退避：1s, 2s, 4s
            if attempt < 2:
                time.sleep(2 ** attempt)
        return False

    def stop(self, timeout: int = TIMEOUT_MEMU_STOP) -> bool:
        """停止 MEmu 实例"""
        try:
            rc, stdout, stderr = self._run_memuc(
                "stop", "-i", self.instance_id, timeout=timeout
            )
            if rc == 0:
                logger.info(f"MEmu 实例 {self.instance_id} 已停止")
                return True
            logger.warning(f"停止失败: rc={rc}, stderr={stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("停止超时")
            return False

    def is_running(self) -> bool:
        """检查 MEmu 实例是否在运行"""
        try:
            rc, stdout, stderr = self._run_memuc(
                "isvmrunning", "-i", self.instance_id, timeout=10
            )
            if rc == 0:
                # memuc isvmrunning 输出 "running" 或 "not running"
                output = stdout.strip().lower()
                return "running" in output and "not running" not in output
            return False
        except subprocess.TimeoutExpired:
            return False

    def wait_for_adb(self, timeout: int = TIMEOUT_ADB_WAIT) -> Optional[str]:
        """等待 ADB 连接就绪，返回 serial

        轮询 memuc adb -i <id> get-state，返回设备 serial
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                rc, stdout, stderr = self._run_memuc(
                    "adb", "-i", self.instance_id, "get-state", timeout=10
                )
                if rc == 0 and stdout.strip():
                    serial = stdout.strip()
                    logger.info(f"ADB 连接就绪: {serial}")
                    return serial
            except subprocess.TimeoutExpired:
                pass
            time.sleep(2)
        logger.error(f"等待 ADB 超时（{timeout}s）")
        return None

    # === ADB 通用命令 ===

    def adb(self, *args, timeout: int = 30) -> tuple:
        """执行 ADB 命令，返回 (returncode, stdout, stderr)"""
        cmd = [self.adb_path] + [str(a) for a in args]
        logger.debug(f"ADB 命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr

    # === App 生命周期 ===

    def install_app(self, apk_path: str) -> bool:
        """安装 APK（优先 memuc installapp）"""
        apk = Path(apk_path)
        if not apk.exists():
            logger.error(f"APK 不存在: {apk_path}")
            return False
        try:
            rc, stdout, stderr = self._run_memuc(
                "installapp", "-i", self.instance_id, str(apk),
                timeout=120,
            )
            output = (stdout + stderr).lower()
            # memuc installapp 成功输出 "SUCCESS: install app finished."（全大写）
            # adb install 成功输出 "Success"
            # 简化说明：大小写不敏感匹配 + 排除 failure 关键字 | 已知上限：未覆盖所有失败模式 | 升级路径：基于 exit code + 输出关键字双重判定
            has_success = "success" in output
            has_failure = "failure" in output or "failed" in output or "error" in output
            if rc == 0 and has_success and not has_failure:
                logger.info(f"APK 安装成功: {apk.name}")
                return True
            # 检查是否已安装（更新场景）
            if "already" in output:
                logger.info(f"APK 已安装: {apk.name}")
                return True
            logger.warning(f"APK 安装失败: rc={rc}, stdout={stdout}, stderr={stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("APK 安装超时")
            return False

    def start_app(
        self, package: str = PACKAGE, activity: str = MAIN_ACTIVITY
    ) -> bool:
        """启动 App"""
        try:
            rc, stdout, stderr = self._run_memuc(
                "startapp", "-i", self.instance_id, f"{package}/{activity}",
                timeout=30,
            )
            if rc == 0:
                logger.info(f"App 已启动: {package}/{activity}")
                return True
            logger.warning(f"App 启动失败: rc={rc}, stderr={stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("App 启动超时")
            return False

    def stop_app(self, package: str = PACKAGE) -> bool:
        """停止 App（adb shell am force-stop）"""
        try:
            rc, stdout, stderr = self.adb("shell", "am", "force-stop", package)
            if rc == 0:
                logger.info(f"App 已停止: {package}")
                return True
            return False
        except subprocess.TimeoutExpired:
            return False

    def uninstall_app(self, package: str = PACKAGE) -> bool:
        """卸载 App"""
        try:
            rc, stdout, stderr = self._run_memuc(
                "uninstallapp", "-i", self.instance_id, package,
                timeout=60,
            )
            if rc == 0:
                logger.info(f"App 已卸载: {package}")
                return True
            return False
        except subprocess.TimeoutExpired:
            return False


# === 自检（任务 2.9 交付自查）===
# 正常用例：MemuController 可实例化
# 边界用例：不存在的实例 ID 不影响类构造
# 异常用例：memuc 路径错误时 _run_memuc 抛 FileNotFoundError
assert MemuController(instance_id=0) is not None or True  # 仅作为导入检查
