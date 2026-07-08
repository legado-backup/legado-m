"""ai_tests/tests/test_memu_controller.py — M1 单元测试

任务 2.9：mock subprocess，验证命令构造正确

运行：
    python -m pytest ai_tests/tests/test_memu_controller.py -v
或：
    python ai_tests/tests/test_memu_controller.py
"""
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.memu_controller import MemuController


def test_memu_controller_instantiation():
    """正常用例：MemuController 可实例化"""
    ctrl = MemuController(instance_id=0)
    assert ctrl.instance_id == 0
    assert ctrl.memuc_path is not None
    assert ctrl.adb_path is not None
    print("[PASS] test_memu_controller_instantiation")


def test_memu_controller_custom_instance():
    """边界用例：自定义实例 ID"""
    ctrl = MemuController(instance_id=1)
    assert ctrl.instance_id == 1
    print("[PASS] test_memu_controller_custom_instance")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_start_success(mock_run):
    """正常用例：start 成功"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    ctrl = MemuController()
    # 由于 is_running 也会被调用，先 mock 它
    with patch.object(ctrl, "is_running", return_value=False):
        result = ctrl.start(timeout=5)
    assert result is True
    # 验证命令包含 start -i 0
    called_cmd = mock_run.call_args[0][0]
    assert "start" in called_cmd
    assert "-i" in called_cmd
    assert "0" in called_cmd
    print("[PASS] test_start_success")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_is_running_true(mock_run):
    """正常用例：is_running 返回 True"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "running"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    ctrl = MemuController()
    assert ctrl.is_running() is True
    print("[PASS] test_is_running_true")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_is_running_false(mock_run):
    """边界用例：is_running 返回 False"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "not running"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    ctrl = MemuController()
    assert ctrl.is_running() is False
    print("[PASS] test_is_running_false")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_is_running_timeout(mock_run):
    """异常用例：is_running 超时返回 False"""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="memuc", timeout=10)

    ctrl = MemuController()
    assert ctrl.is_running() is False
    print("[PASS] test_is_running_timeout")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_adb_command(mock_run):
    """正常用例：adb 命令构造正确"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    ctrl = MemuController()
    rc, stdout, stderr = ctrl.adb("shell", "ls")
    assert rc == 0
    assert stdout == "success"
    called_cmd = mock_run.call_args[0][0]
    assert "shell" in called_cmd
    assert "ls" in called_cmd
    print("[PASS] test_adb_command")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_install_app_success(mock_run):
    """正常用例：install_app 成功"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    ctrl = MemuController()
    # mock is_running 避免误调
    with patch.object(ctrl, "is_running", return_value=True):
        # mock apk 文件存在
        with patch.object(Path, "exists", return_value=True):
            result = ctrl.install_app("/fake/path/app.apk")
    assert result is True
    print("[PASS] test_install_app_success")


@patch("ai_tests.lib.memu_controller.subprocess.run")
def test_install_app_not_exist(mock_run):
    """异常用例：APK 不存在时返回 False"""
    ctrl = MemuController()
    # 不调用 mock_run，直接测试路径不存在
    result = ctrl.install_app("/nonexistent/path.apk")
    assert result is False
    mock_run.assert_not_called()
    print("[PASS] test_install_app_not_exist")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M1 MemuController 单元测试")
    print("=" * 60)
    test_memu_controller_instantiation()
    test_memu_controller_custom_instance()
    test_start_success()
    test_is_running_true()
    test_is_running_false()
    test_is_running_timeout()
    test_adb_command()
    test_install_app_success()
    test_install_app_not_exist()
    print("=" * 60)
    print("所有测试 PASS！")


if __name__ == "__main__":
    main()
