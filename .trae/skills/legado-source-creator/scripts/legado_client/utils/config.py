#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理：JAR 路径、超时、缓存目录、数据库、Web、爬取、真机等集中配置。

路径基准：legado_client/utils/config.py
  parent        = legado_client/utils/
  parent.parent  = legado_client/
  parent.parent.parent = scripts/
  parent.parent.parent.parent = legado-source-creator/ (skill_root)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# 尝试加载 .env 文件（scripts/ 目录下）
_scripts_dir = Path(__file__).resolve().parent.parent.parent
_env_file = _scripts_dir / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        # python-dotenv 未安装时忽略，直接读环境变量
        pass


def _env(key: str, default: str = "") -> str:
    """读取环境变量。"""
    return os.environ.get(key, default)


def _env_int(key: str, default: int = 0) -> int:
    """读取环境变量并转为 int，转换失败返回默认值。"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    """读取环境变量并转为 float，转换失败返回默认值。"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


class Config:
    """全局配置单例，集中管理路径和超时参数。"""

    _instance: Optional["Config"] = None

    def __init__(self) -> None:
        # scripts/ 目录
        self.scripts_dir: Path = _scripts_dir
        # legado-source-creator/ 目录
        self.skill_root: Path = self.scripts_dir.parent
        # tools/ 目录（JAR 客户端原位置）
        self.tools_dir: Path = self.skill_root / "tools"
        # references/ 目录
        self.references_dir: Path = self.skill_root / "references"
        # output/ 目录（skill 根下，阶段0.3已从 skill_root.parent/output 移动到此）
        self.output_dir: Path = self.skill_root / "output"
        # 超时配置（秒）
        self.jvm_startup_timeout: int = 30
        self.page_load_timeout: int = 30
        self.script_timeout: int = 30
        # JAR 路径（延迟查找）
        self._jar_path: Optional[str] = None

        # ---- 数据库配置 ----
        self.db_host: str = _env("LEGADO_DB_HOST", "127.0.0.1")
        self.db_port: int = _env_int("LEGADO_DB_PORT", 3306)
        self.db_user: str = _env("LEGADO_DB_USER", "root")
        self.db_password: str = _env("LEGADO_DB_PASSWORD", "200868")
        self.db_name: str = _env("LEGADO_DB_NAME", "legado_sources")
        # 数据库可用标志，由 DatabaseHealthChecker 动态更新
        self.db_available: bool = False

        # ---- Web 服务配置 ----
        self.web_host: str = _env("LEGADO_WEB_HOST", "127.0.0.1")
        self.web_port: int = _env_int("LEGADO_WEB_PORT", 8080)

        # ---- 爬取配置 ----
        self.fetch_delay: float = _env_float("LEGADO_FETCH_DELAY", 1.0)
        self.fetch_timeout: int = _env_int("LEGADO_FETCH_TIMEOUT", 30)

        # ---- 真机配置 ----
        self.device_host: str = _env("LEGADO_DEVICE_HOST", "")
        self.device_port: int = _env_int("LEGADO_DEVICE_PORT", 1122)
        self.device_auth_token: str = _env("LEGADO_DEVICE_AUTH_TOKEN", "")

    @property
    def db_url(self) -> str:
        """异步数据库连接 URL（aiomysql 格式）。"""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    @classmethod
    def get_instance(cls) -> "Config":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def jar_path(self) -> str:
        """查找 JAR 文件，多路径回退。"""
        if self._jar_path is not None:
            return self._jar_path
        candidates = [
            self.tools_dir / "legado-jvm" / "build" / "libs" / "legado-jvm.jar",
            self.tools_dir / "legado-rule-engine-mvp4.jar",
            self.tools_dir / "legado-rule-engine-mvp3.jar",
            self.tools_dir / "legado-rule-engine-mvp2.jar",
            self.tools_dir / "legado-rule-engine-mvp1.jar",
        ]
        for path in candidates:
            if path.exists():
                self._jar_path = str(path)
                return self._jar_path
        # 返回默认路径（start() 会报 FileNotFoundError）
        self._jar_path = str(candidates[0])
        return self._jar_path

    @staticmethod
    def find_java() -> Optional[str]:
        """检测 JDK/JRE 可用性，返回 java 可执行文件路径。"""
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_bin = os.path.join(java_home, "bin", "java")
            if os.name == "nt":
                java_bin += ".exe"
            if os.path.isfile(java_bin):
                return java_bin
        import shutil
        java_in_path = shutil.which("java")
        if java_in_path:
            return java_in_path
        return None


# 简化说明：模块级单例 | 已知上限：无 | 升级路径：如需从环境变量加载，扩展 __init__
config = Config.get_instance()
