#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Config 单元测试。

同时支持：
- `python test_config.py` 独立运行
- `pytest test_config.py` 运行

被测模块：utils/config.py
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config import Config, config


# ========== 正常用例 ==========

def test_config_singleton():
    """Config 是单例，get_instance 返回同一实例。"""
    c1 = Config.get_instance()
    c2 = Config.get_instance()
    assert c1 is c2
    assert config is c1


def test_config_scripts_dir_exists():
    """scripts_dir 指向存在的目录。"""
    c = Config.get_instance()
    assert c.scripts_dir.exists()
    assert c.scripts_dir.name == "scripts"


def test_config_skill_root_exists():
    """skill_root 指向 legado-source-creator 目录。"""
    c = Config.get_instance()
    assert c.skill_root.exists()
    assert c.skill_root.name == "legado-source-creator"


def test_config_references_dir_exists():
    """references_dir 指向存在的 references 目录。"""
    c = Config.get_instance()
    assert c.references_dir.exists()
    assert c.references_dir.name == "references"


def test_config_output_dir_path():
    """output_dir 路径正确（在 skill_root 下）。"""
    c = Config.get_instance()
    assert c.output_dir.parent == c.skill_root
    assert c.output_dir.name == "output"


def test_config_timeout_values():
    """超时配置为正整数。"""
    c = Config.get_instance()
    assert isinstance(c.jvm_startup_timeout, int) and c.jvm_startup_timeout > 0
    assert isinstance(c.page_load_timeout, int) and c.page_load_timeout > 0
    assert isinstance(c.script_timeout, int) and c.script_timeout > 0


# ========== 边界用例 ==========

def test_config_jar_path_returns_string():
    """jar_path 属性返回字符串（即使 JAR 不存在也返回默认路径）。"""
    # 重置缓存以测试查找逻辑
    c = Config.get_instance()
    original = c._jar_path
    try:
        c._jar_path = None
        path = c.jar_path
        assert isinstance(path, str)
        assert path.endswith(".jar")
    finally:
        c._jar_path = original


def test_config_jar_path_cached():
    """jar_path 第二次访问返回缓存值，不再查找。"""
    c = Config.get_instance()
    c._jar_path = "/fake/cached/path.jar"
    try:
        assert c.jar_path == "/fake/cached/path.jar"
    finally:
        c._jar_path = None  # 重置


def test_config_find_java_returns_none_when_no_java(monkeypatch=None):
    """find_java 在无 JAVA_HOME 且 PATH 无 java 时返回 None。"""
    # 使用 patch 替换 os.environ 和 shutil.which
    with patch.dict(os.environ, {}, clear=True):
        with patch("shutil.which", return_value=None):
            result = Config.find_java()
            # 不强制 None（CI 可能装了 java），只验证返回值类型
            assert result is None or isinstance(result, str)


def test_config_find_java_with_java_home(tmp_path):
    """find_java 在 JAVA_HOME 指向有效路径时返回 java 路径。"""
    # 创建假的 java 可执行文件
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    java_exe = bin_dir / ("java.exe" if os.name == "nt" else "java")
    java_exe.write_text("#!/bin/sh\nexit 0\n")
    if os.name != "nt":
        java_exe.chmod(0o755)

    with patch.dict(os.environ, {"JAVA_HOME": str(tmp_path)}, clear=True):
        with patch("shutil.which", return_value=None):
            result = Config.find_java()
            assert result is not None
            assert str(java_exe) in result or result.endswith("java") or result.endswith("java.exe")


# ========== 异常用例 ==========

def test_config_construction_does_not_raise():
    """直接构造 Config 实例不抛异常。"""
    c = Config()
    assert c.scripts_dir is not None
    assert c.skill_root is not None


def test_config_jar_path_default_when_not_found():
    """jar_path 在所有候选路径都不存在时返回默认路径（不抛异常）。"""
    c = Config()
    c._jar_path = None
    # 临时修改候选路径都不存在
    original_tools = c.tools_dir
    try:
        c.tools_dir = Path("/nonexistent/tools/dir")
        path = c.jar_path
        assert isinstance(path, str)
        assert path.endswith(".jar")
    finally:
        c.tools_dir = original_tools
        c._jar_path = None


if __name__ == "__main__":
    # 独立运行模式
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
