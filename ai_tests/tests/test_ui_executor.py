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
    """构造 mock selector

    info 设为非 Preference 条目（resourceName 为空），避免 _is_preference_item 误判。
    若 MagicMock 默认 info，rid.endswith() 返回 truthy MagicMock → 误判为 Preference 条目。
    """
    sel = MagicMock()
    sel.exists.return_value = exists_return
    sel.info = {"resourceName": ""}  # 非 Preference 条目
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
    permission_dialog_exists: bool = False,
    permission_allow_exists: bool = False,
):
    """构造 mock u2.Device

    支持四个阻塞屏幕：
    - 隐私协议：text="用户隐私与协议" 检测 + text="同意" 点击
    - 帮助文档：resource-id="...:id/menu_close" 检测 + 同 resource-id 点击
    - 设置本地密码：text="设置本地密码" 检测 + resource-id="android:id/button2" 点击
    - 权限请求：resource-id="...:id/permission_message" 检测 + resource-id="...:id/permission_allow_button" 点击

    Args:
        dialog_exists: 隐私协议对话框是否存在
        agree_exists: 同意按钮是否存在
        agree_click_raises: 点击同意按钮是否抛异常
        help_close_exists: 帮助文档 menu_close 按钮是否存在
        password_dialog_exists: 设置本地密码对话框是否存在
        password_cancel_exists: 设置本地密码取消按钮是否存在
        permission_dialog_exists: 权限请求对话框是否存在
        permission_allow_exists: 权限允许按钮是否存在
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

        # Android 权限请求对话框
        if resource_id == 'com.android.packageinstaller:id/permission_message':
            return _make_selector(permission_dialog_exists)
        if resource_id == 'com.android.packageinstaller:id/permission_allow_button':
            return _make_selector(permission_allow_exists)

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


# === dismiss_dialogs 测试：Android 权限请求对话框 ===

def test_dismiss_dialogs_permission_dialog():
    """正常用例：检测到权限请求对话框，点击'允许'按钮成功 → 返回 True"""
    device = _make_device(permission_dialog_exists=True, permission_allow_exists=True)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is True
    # 验证调用了 d(resourceId='...:id/permission_message') 和 d(resourceId='...:id/permission_allow_button')
    device.assert_any_call(resourceId='com.android.packageinstaller:id/permission_message')
    device.assert_any_call(resourceId='com.android.packageinstaller:id/permission_allow_button')
    print("[PASS] test_dismiss_dialogs_permission_dialog")


def test_dismiss_dialogs_permission_allow_missing():
    """边界用例：权限请求对话框存在但允许按钮不存在 → 返回 False"""
    device = _make_device(permission_dialog_exists=True, permission_allow_exists=False)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor.dismiss_dialogs()

    assert result is False
    print("[PASS] test_dismiss_dialogs_permission_allow_missing")


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


def test_execute_step_loops_dismiss_dialogs():
    """验证 execute_step 循环调用 dismiss_dialogs（多个顺序阻塞屏幕被逐一关闭）

    模拟 dismiss_dialogs 前两次返回 True（关闭了 2 个阻塞屏幕），
    第三次返回 False（无更多阻塞屏幕）→ 退出循环
    """
    device = MagicMock()
    executor = UiExecutor(device)

    with patch.object(executor, 'dismiss_dialogs', side_effect=[True, True, False]) as mock_dismiss, \
         patch('ai_tests.lib.ui_executor.time.sleep'):
        step = Step(action="sleep", target="0.01", raw="等待")
        executor.execute_step(step)

    # 验证 dismiss_dialogs 被调用 3 次（前两次 True，第三次 False 退出）
    assert mock_dismiss.call_count == 3
    print("[PASS] test_execute_step_loops_dismiss_dialogs")


# === BLOCKING_DIALOGS 类常量验证 ===

def test_blocking_dialogs_constant():
    """验证 BLOCKING_DIALOGS 类常量包含四个阻塞屏幕（5 元组结构）"""
    assert hasattr(UiExecutor, 'BLOCKING_DIALOGS')
    # 验证隐私协议（text 检测 + text 关闭）
    assert ("隐私协议", "text", "用户隐私与协议", "text", "同意") in UiExecutor.BLOCKING_DIALOGS
    # 验证帮助文档（resource-id 检测 + resource-id 关闭）
    help_entry = ("帮助文档", "resource-id", f"{PACKAGE}:id/menu_close", "resource-id", f"{PACKAGE}:id/menu_close")
    assert help_entry in UiExecutor.BLOCKING_DIALOGS
    # 验证设置本地密码（text 检测 + resource-id 关闭）
    assert ("设置本地密码", "text", "设置本地密码", "resource-id", "android:id/button2") in UiExecutor.BLOCKING_DIALOGS
    # 验证权限请求（resource-id 检测 + resource-id 关闭）
    assert ("权限请求", "resource-id", "com.android.packageinstaller:id/permission_message", "resource-id", "com.android.packageinstaller:id/permission_allow_button") in UiExecutor.BLOCKING_DIALOGS
    print("[PASS] test_blocking_dialogs_constant")


# === _scroll_find 测试（OpenSpec e2e-ui-executor-hardening 1.5/1.6）===

def _make_scroll_device(exists_return: bool = False, wait_return: bool = False):
    """构造支持 _scroll_find 的 mock device

    device(text=xxx)/device(description=xxx) 返回同一 selector，
    selector.exists(timeout=0.5) 返回 exists_return，selector.wait(timeout) 返回 wait_return。
    window_size() 返回 (720, 1280)，shell() 模拟 ADB input swipe。

    Args:
        exists_return: exists() 是否返回 True（True=滚动1次后找到，False=永远找不到）
        wait_return: wait() 是否返回 True（False=元素未找到，触发 _scroll_find 分支）
    """
    device = MagicMock()
    device.window_size.return_value = (720, 1280)
    device.shell.return_value = None

    sel = MagicMock()
    sel.exists.return_value = exists_return
    sel.wait.return_value = wait_return
    sel.info = {"resourceName": ""}  # 非 Preference 条目
    device.side_effect = lambda *args, **kwargs: sel
    return device


def test_scroll_find_finds_element():
    """正常用例（1.5）：滚动1次后找到元素 → 返回 selector"""
    device = _make_scroll_device(exists_return=True)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor._scroll_find("测试元素", max_scrolls=3)

    assert result is not None, "滚动后应找到元素"
    # 验证调用了 shell（ADB input swipe）
    device.shell.assert_called()
    shell_cmd = device.shell.call_args[0][0]
    assert "input swipe" in shell_cmd, f"应调用 ADB input swipe，实际: {shell_cmd}"
    print("[PASS] test_scroll_find_finds_element")


def test_scroll_find_not_found():
    """边界用例（1.6）：滚动 max_scrolls 次后未找到 → 返回 None"""
    device = _make_scroll_device(exists_return=False)
    executor = UiExecutor(device)

    with patch('ai_tests.lib.ui_executor.time.sleep'):
        result = executor._scroll_find("测试元素", max_scrolls=3)

    assert result is None, "未找到元素应返回 None"
    # 验证滚动了 3 次
    assert device.shell.call_count == 3, f"应滚动 3 次，实际: {device.shell.call_count}"
    print("[PASS] test_scroll_find_not_found")


def test_scroll_find_max_zero():
    """边界用例（1.6）：max_scrolls=0 时不滚动，直接返回 None"""
    device = _make_scroll_device(exists_return=True)
    executor = UiExecutor(device)

    result = executor._scroll_find("测试元素", max_scrolls=0)

    assert result is None, "max_scrolls=0 应返回 None"
    # 验证没有调用 shell（没有滚动）
    device.shell.assert_not_called()
    print("[PASS] test_scroll_find_max_zero")


def test_click_scroll_search_true_calls_scroll_find():
    """正常用例（1.5）：scroll_search=True 时 _get_element 调用 _scroll_find"""
    # exists/wait 都返回 False → 元素未找到 → 走 _scroll_find 分支
    device = _make_scroll_device(exists_return=False, wait_return=False)
    executor = UiExecutor(device)

    mock_el = MagicMock()
    with patch.object(executor, '_scroll_find', return_value=mock_el) as mock_sf:
        result = executor._get_element("测试元素", timeout=1, scroll_search=True)

    assert result is mock_el, "scroll_search=True 时应返回 _scroll_find 的结果"
    mock_sf.assert_called_once_with("测试元素")
    print("[PASS] test_click_scroll_search_true_calls_scroll_find")


def test_click_scroll_search_false_no_scroll_find():
    """边界用例（1.6）：scroll_search=False 时不调用 _scroll_find"""
    device = _make_scroll_device(exists_return=False, wait_return=False)
    executor = UiExecutor(device)

    with patch.object(executor, '_scroll_find') as mock_sf:
        result = executor._get_element("测试元素", timeout=1, scroll_search=False)

    assert result is None, "scroll_search=False 且元素未找到应返回 None"
    mock_sf.assert_not_called()
    print("[PASS] test_click_scroll_search_false_no_scroll_find")


# === _detect_app_state 测试（OpenSpec e2e-ui-executor-hardening 2.4/2.5）===

def test_detect_app_state_normal():
    """正常用例（2.4）：app_current 返回 package=PACKAGE → normal"""
    device = MagicMock()
    device.app_current.return_value = {
        "package": PACKAGE,
        "activity": "io.legado.app.ui.MainActivity"
    }
    executor = UiExecutor(device)

    result = executor._detect_app_state()

    assert result == "normal", f"App 在前台应返回 normal，实际: {result}"
    print("[PASS] test_detect_app_state_normal")


def test_detect_app_state_crashed():
    """边界用例（2.4）：app_current 返回 launcher → crashed"""
    device = MagicMock()
    device.app_current.return_value = {
        "package": "com.microvirt.launcher2",
        "activity": ""
    }
    executor = UiExecutor(device)

    result = executor._detect_app_state()

    assert result == "crashed", f"App 不在前台应返回 crashed，实际: {result}"
    print("[PASS] test_detect_app_state_crashed")


def test_detect_app_state_exception():
    """异常用例（2.5）：app_current 抛异常 → not_running"""
    device = MagicMock()
    device.app_current.side_effect = RuntimeError("u2 connection lost")
    executor = UiExecutor(device)

    result = executor._detect_app_state()

    assert result == "not_running", f"app_current 异常应返回 not_running，实际: {result}"
    print("[PASS] test_detect_app_state_exception")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M4 UiExecutor 单元测试")
    print("=" * 60)
    # dismiss_dialogs 测试
    test_dismiss_dialogs_normal()
    test_dismiss_dialogs_no_dialog()
    test_dismiss_dialogs_exception()
    test_dismiss_dialogs_agree_btn_missing()
    test_dismiss_dialogs_click_exception()
    test_dismiss_dialogs_help_page()
    test_dismiss_dialogs_password_dialog()
    test_dismiss_dialogs_password_cancel_missing()
    test_dismiss_dialogs_permission_dialog()
    test_dismiss_dialogs_permission_allow_missing()
    test_dismiss_dialogs_multiple_screens()
    # execute_step 测试
    test_execute_step_calls_dismiss_dialogs()
    test_execute_step_loops_dismiss_dialogs()
    # 常量验证
    test_blocking_dialogs_constant()
    # _scroll_find 测试（1.5/1.6）
    test_scroll_find_finds_element()
    test_scroll_find_not_found()
    test_scroll_find_max_zero()
    test_click_scroll_search_true_calls_scroll_find()
    test_click_scroll_search_false_no_scroll_find()
    # _detect_app_state 测试（2.4/2.5）
    test_detect_app_state_normal()
    test_detect_app_state_crashed()
    test_detect_app_state_exception()
    print("=" * 60)
    print(f"所有测试 PASS！共 {22} 个用例")


if __name__ == "__main__":
    main()
