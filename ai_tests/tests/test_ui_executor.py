"""ai_tests/tests/test_ui_executor.py — M4 UI 执行器单元测试

任务 6.x：mock u2.Device，验证 dismiss_dialogs / execute_step 调用
覆盖 3 类用例：正常 / 边界 / 异常

运行：
    python -m pytest ai_tests/tests/test_ui_executor.py -v
或：
    python ai_tests/tests/test_ui_executor.py
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# mock uiautomator2，避免未安装时 import 失败（测试不依赖真实设备）
sys.modules['uiautomator2'] = MagicMock()

from ai_tests.lib.ui_executor import UiExecutor
from ai_tests.lib.case_parser import Step
from ai_tests.config import PACKAGE


def _make_selector(exists_return: bool, click_raises: Exception = None):
    """构造 mock selector"""
    sel = MagicMock()
    sel.exists.return_value = exists_return
    if click_raises:
        sel.click.side_effect = click_raises
    return sel


def _make_device(
    dialog_exists: bool = False,
    agree_exists: bool = False,
    agree_click_raises: Exception = None,
    help_close_exists: bool = False,
    password_dialog_exists: bool = False,
    password_cancel_exists: bool = False,
):
    """构造 mock u2.Device

    支持三个阻塞屏幕：
    - 隐私协议：text="用户隐私与协议" 检测 + text="同意" 点击
    - 帮助文档：resource-id="...:id/menu_close" 检测 + 同 resource-id 点击
    - 设置本地密码：text="设置本地密码" 检测 + resource-id="android:id/button2" 点击

    Args:
        dialog_exists: 隐私协议对话框是否存在
        agree_exists: 同意按钮是否存在
        agree_click_raises: 点击同意按钮是否抛异常
        help_close_exists: 帮助文档 menu_close 按钮是否存在
        password_dialog_exists: 设置本地密码对话框是否存在
        password_cancel_exists: 设置本地密码取消按钮是否存在
    """
    device = MagicMock()

    def d_call(*args, **kwargs):
        text = kwargs.get('text', '')
        resource_id = kwargs.get('resourceId', '')

        # 隐私协议对话框
        if text == '用户隐私与协议':
            return _make_selector(dialog_exists)
        if text == '同意':
            sel = _make_selector(agree_exists)
            if agree_click_raises:
                sel.click.side_effect = agree_click_raises
            return sel

        # 帮助文档页面（resource-id 包含 menu_close）
        if resource_id and 'menu_close' in resource_id:
            return _make_selector(help_close_exists)

        # 设置本地密码对话框
        if text == '设置本地密码':
            return _make_selector(password_dialog_exists)
        if resource_id == 'android:id/button2':
            return _make_selector(password_cancel_exists)

        return _make_selector(False)

    device.side_effect = d_call
    return device


# === dismiss_dialogs 测试：隐私协议 ===

def test_dismiss_dialogs_normal():
    """正常用例：检测到隐私协议对话框，点击'同意'成功 → 返回 True"""
    device = _make_device(dialog_exists=True, agree_exists=True)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is True
    # 验证调用了 d(text='用户隐私与协议') 和 d(text='同意')
    device.assert_any_call(text='用户隐私与协议')
    device.assert_any_call(text='同意')
    print("[PASS] test_dismiss_dialogs_normal")


def test_dismiss_dialogs_no_dialog():
    """边界用例：没有任何阻塞屏幕 → 返回 False（快速返回，不检测关闭按钮）"""
    device = _make_device()
    executor = UiExecutor(device)

    result = executor.dismiss_dialogs()

    assert result is False
    # 验证检测了隐私协议
    device.assert_any_call(text='用户隐私与协议')
    print("[PASS] test_dismiss_dialogs_no_dialog")


def test_dismiss_dialogs_exception():
    """异常用例：d(xxx) 抛异常 → 捕获不阻断，返回 False"""
    device = MagicMock()
    device.side_effect = RuntimeError("u2 connection lost")

    executor = UiExecutor(device)

    # 异常不应抛出，应被捕获
    result = executor.dismiss_dialogs()

    assert result is False
    print("[PASS] test_dismiss_dialogs_exception")


def test_dismiss_dialogs_agree_btn_missing():
    """边界用例：隐私协议对话框存在但同意按钮不存在 → 返回 False（仅警告不阻断）"""
    device = _make_device(dialog_exists=True, agree_exists=False)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is False
    print("[PASS] test_dismiss_dialogs_agree_btn_missing")


def test_dismiss_dialogs_click_exception():
    """异常用例：点击同意按钮抛异常 → 捕获不阻断，返回 False"""
    device = _make_device(
        dialog_exists=True,
        agree_exists=True,
        agree_click_raises=RuntimeError("click failed")
    )
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is False
    print("[PASS] test_dismiss_dialogs_click_exception")


# === dismiss_dialogs 测试：帮助文档页面 ===

def test_dismiss_dialogs_help_page():
    """正常用例：检测到帮助文档页面，点击 menu_close 成功 → 返回 True"""
    device = _make_device(help_close_exists=True)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is True
    # 验证调用了 d(resourceId='...:id/menu_close')
    expected_rid = f"{PACKAGE}:id/menu_close"
    device.assert_any_call(resourceId=expected_rid)
    print("[PASS] test_dismiss_dialogs_help_page")


# === dismiss_dialogs 测试：设置本地密码对话框 ===

def test_dismiss_dialogs_password_dialog():
    """正常用例：检测到设置本地密码对话框，点击'取消'(button2) 成功 → 返回 True"""
    device = _make_device(password_dialog_exists=True, password_cancel_exists=True)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is True
    # 验证调用了 d(text='设置本地密码') 和 d(resourceId='android:id/button2')
    device.assert_any_call(text='设置本地密码')
    device.assert_any_call(resourceId='android:id/button2')
    print("[PASS] test_dismiss_dialogs_password_dialog")


def test_dismiss_dialogs_password_cancel_missing():
    """边界用例：设置本地密码对话框存在但取消按钮不存在 → 返回 False"""
    device = _make_device(password_dialog_exists=True, password_cancel_exists=False)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is False
    print("[PASS] test_dismiss_dialogs_password_cancel_missing")


# === dismiss_dialogs 测试：多屏幕同时存在 ===

def test_dismiss_dialogs_multiple_screens():
    """正常用例：多个阻塞屏幕同时存在 → 全部关闭，返回 True"""
    device = _make_device(
        dialog_exists=True,
        agree_exists=True,
        help_close_exists=True,
        password_dialog_exists=True,
        password_cancel_exists=True,
    )
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is True
    print("[PASS] test_dismiss_dialogs_multiple_screens")


# === execute_step 调用 dismiss_dialogs 验证 ===

def test_execute_step_calls_dismiss_dialogs():
    """验证 execute_step 开头调用了 dismiss_dialogs"""
    device = MagicMock()
    executor = UiExecutor(device)

    with patch.object(executor, 'dismiss_dialogs', return_value=False) as mock_dismiss, \
         patch('ai_tests.lib.ui_executor.time.sleep'):
        # 用 sleep action，不依赖 UI 元素
        step = Step(action="sleep", target="0.01", raw="等待")
        executor.execute_step(step)

    mock_dismiss.assert_called_once()
    print("[PASS] test_execute_step_calls_dismiss_dialogs")


# === BLOCKING_DIALOGS 类常量验证 ===

def test_blocking_dialogs_constant():
    """验证 BLOCKING_DIALOGS 类常量包含三个阻塞屏幕（5 元组结构）"""
    assert hasattr(UiExecutor, 'BLOCKING_DIALOGS')
    # 验证隐私协议（text 检测 + text 关闭）
    assert ("隐私协议", "text", "用户隐私与协议", "text", "同意") in UiExecutor.BLOCKING_DIALOGS
    # 验证帮助文档（resource-id 检测 + resource-id 关闭）
    help_entry = ("帮助文档", "resource-id", f"{PACKAGE}:id/menu_close", "resource-id", f"{PACKAGE}:id/menu_close")
    assert help_entry in UiExecutor.BLOCKING_DIALOGS
    # 验证设置本地密码（text 检测 + resource-id 关闭）
    assert ("设置本地密码", "text", "设置本地密码", "resource-id", "android:id/button2") in UiExecutor.BLOCKING_DIALOGS
    print("[PASS] test_blocking_dialogs_constant")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M4 UiExecutor 单元测试")
    print("=" * 60)
    test_dismiss_dialogs_normal()
    test_dismiss_dialogs_no_dialog()
    test_dismiss_dialogs_exception()
    test_dismiss_dialogs_agree_btn_missing()
    test_dismiss_dialogs_click_exception()
    test_dismiss_dialogs_help_page()
    test_dismiss_dialogs_password_dialog()
    test_dismiss_dialogs_password_cancel_missing()
    test_dismiss_dialogs_multiple_screens()
    test_execute_step_calls_dismiss_dialogs()
    test_blocking_dialogs_constant()
    print("=" * 60)
    print(f"所有测试 PASS！共 {11} 个用例")


if __name__ == "__main__":
    main()
