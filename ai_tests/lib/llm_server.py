"""ai_tests/lib/llm_server.py — LlmServerManager（AI-LLM-Testing 基建）

职责：本地 llama-server 子进程自动托管，脱离 LM Studio：
- ensure_online：探测端口已有 OpenAI 兼容服务则复用；否则 Popen 拉起 + 健康轮询
- stop：优雅终止本进程启动的服务器（不杀第三方占用进程）
- 失败抛 LlmUnavailableError，调用方降级（AD-01）

依赖：subprocess / urllib（标准库）
"""
import logging
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional

from ai_tests.config_ai import (
    LLAMA_SERVER_PATH, LLAMA_WORKDIR, AI_MODEL_GGUF, AI_MODEL_MMPROJ,
    AI_HOST, AI_PORT, AI_HEALTH_TIMEOUT, AI_START_TIMEOUT, AI_LLAMA_ARGS,
)

logger = logging.getLogger(__name__)


class LlmUnavailableError(RuntimeError):
    """模型服务器不可用（启动失败/超时/被占用无法接管）"""


class LlmServerManager:
    """llama-server 子进程托管

    用法：
        mgr = LlmServerManager()
        mgr.ensure_online()      # 复用或拉起，直到 /health 就绪
        ...
        mgr.stop()               # 只停自己启动的进程
    """

    def __init__(
        self,
        host: str = AI_HOST,
        port: int = AI_PORT,
        server_path: str = LLAMA_SERVER_PATH,
        workdir: str = LLAMA_WORKDIR,
        model: Path = AI_MODEL_GGUF,
        mmproj: Path = AI_MODEL_MMPROJ,
    ):
        self.host = host
        self.port = port
        self.server_path = server_path
        self.workdir = workdir
        self.model = model
        self.mmproj = mmproj
        self._proc: Optional[subprocess.Popen] = None

    # === 健康探测 ===

    def _health_url(self) -> str:
        return f"http://{self.host}:{self.port}/health"

    def is_healthy(self) -> bool:
        """llama-server /health：模型加载完成后返回 200"""
        try:
            with urllib.request.urlopen(self._health_url(), timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _is_port_open(self) -> bool:
        """端口是否有进程监听（不关心是否我们的服务）"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((self.host, self.port)) == 0

    # === 启动 ===

    def _build_cmd(self) -> list:
        if not Path(self.server_path).exists():
            raise LlmUnavailableError(f"llama-server 不存在: {self.server_path}")
        if not Path(self.model).exists():
            raise LlmUnavailableError(f"模型 GGUF 不存在: {self.model}")
        if not Path(self.mmproj).exists():
            raise LlmUnavailableError(f"mmproj 不存在: {self.mmproj}")
        return [
            self.server_path,
            "-m", str(self.model),
            "--mmproj", str(self.mmproj),
            "--host", self.host,
            "--port", str(self.port),
        ] + list(AI_LLAMA_ARGS)

    def _spawn(self) -> subprocess.Popen:
        cmd = self._build_cmd()
        logger.info("拉起 llama-server: %s", " ".join(cmd[:8]) + " ...")
        self._proc = subprocess.Popen(
            cmd,
            cwd=self.workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self._proc

    def ensure_online(self) -> dict:
        """确保模型服务在线。

        Returns: {"reused": bool, "pid": int|None}
        - 端口已有在线服务（任意 OpenAI 兼容，含 LM Studio）→ 直接复用，不拉起
        - 端口被非健康进程占用 → 视为启动窗口，轮询健康
        - 超时抛 LlmUnavailableError
        """
        # 1) 端口无监听 → 拉起
        if not self._is_port_open():
            self._spawn()
        # 2) 轮询健康（复用场景健康即为就绪；拉起场景等加载）
        deadline = time.time() + AI_HEALTH_TIMEOUT
        while time.time() < deadline:
            if self.is_healthy():
                reused = self._proc is None
                return {"reused": reused, "pid": self._proc.pid if self._proc else None}
            # 子进程已退出（启动失败）→ 立即报错
            if self._proc is not None and self._proc.poll() is not None:
                raise LlmUnavailableError(
                    f"llama-server 启动后退出 rc={self._proc.returncode}"
                )
            time.sleep(1)
        raise LlmUnavailableError(
            f"llama-server 健康超时 {AI_HEALTH_TIMEOUT}s（port={self.port}）"
        )

    # === 停止 ===

    def stop(self) -> None:
        """只终止本管理器拉起的子进程；第三方占用进程不动"""
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=10)
            except Exception as e:
                logger.warning("llama-server 停止异常: %s", e)
            finally:
                self._proc = None


# === 自检 ===
if __name__ == "__main__":
    mgr = LlmServerManager()
    try:
        info = mgr.ensure_online()
        print(f"[PASS] server online: {info}")
        mgr.stop()
    except LlmUnavailableError as e:
        print(f"[IMPORT OK] LlmUnavailableError 已定义: {e}")
