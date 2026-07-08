"""ai_tests/lib/ui_executor.py — M4 UI 执行器

职责：
- 封装 uiautomator2 操作（click/input/wait/scroll/back/sleep）
- 支持 4 种元素定位：resource-id / text / xpath / description
- execute_step：前置截图+XML → 动作 → 后置截图+XML
- 单步 30s 超时保护
- 自愈机制：失败重试 1 次 → 重启 atx-agent → 3 次失败标记步骤失败

依赖：uiautomator2>=3.2.0, M1 MemuController（用于自愈）
"""
import logging
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any

import uiautomator2 as u2

from ai_tests.config import (
    TIMEOUT_UI_OPERATION,
    TIMEOUT_UI_IMPLICIT_WAIT,
    OPERATION_DELAY_BEFORE,
    OPERATION_DELAY_AFTER,
    PACKAGE,
)
from ai_tests.lib.memu_controller import MemuController
from ai_tests.lib.case_parser import Step

logger = logging.getLogger(__name__)


class UiExecutor:
    """UI 执行器（封装 uiautomator2）

    通过 u2.Device 执行 UI 操作，每步前后自动收集截图+XML 证据
    """

    # target 解析：支持显式前缀 resource-id= / text= / xpath= / desc=
    TARGET_PATTERNS = [
        (re.compile(r'^resource-id\s*=\s*(.+)$', re.I), "resourceId"),
        (re.compile(r'^text\s*=\s*(.+)$', re.I), "text"),
        (re.compile(r'^xpath\s*=\s*(.+)$', re.I), "xpath"),
        (re.compile(r'^desc\s*=\s*(.+)$', re.I), "description"),
    ]

    # 已知阻塞屏幕（持续迭代层：基于实测扩展）
    # 元组结构：(name, detect_type, detect_value, dismiss_type, dismiss_value)
    # detect_type/dismiss_type: "text" 或 "resource-id"
    # 简化说明：硬编码检测/关闭方式 | 已知上限：仅覆盖已登记屏幕，未覆盖动态权限弹窗 | 升级路径：基于 UI XML 语义分析 + LLM 判定（V4）
    BLOCKING_DIALOGS = [
        ("隐私协议", "text", "用户隐私与协议", "text", "同意"),
        ("帮助文档", "resource-id", f"{PACKAGE}:id/menu_close", "resource-id", f"{PACKAGE}:id/menu_close"),
        ("设置本地密码", "text", "设置本地密码", "resource-id", "android:id/button2"),
    ]

    def __init__(
        self,
        device: u2.Device,
        memu: Optional[MemuController] = None,
    ):
        self.d = device
        self.memu = memu  # 用于自愈时重启 atx-agent
        self.failure_count = 0  # 连续失败计数

    # === 任务 6.2：元素定位 ===

    def dismiss_dialogs(self) -> bool:
        """关闭已知阻塞屏幕（隐私协议、帮助文档、设置本地密码等）

        在 execute_step 开头自动调用，避免阻塞屏幕阻塞主流程。
        检测失败或点击失败仅记录警告，不阻断。

        简化说明：短超时扫描固定阻塞屏幕列表 | 已知上限：仅覆盖已登记屏幕，未覆盖动态权限弹窗 | 升级路径：基于 UI XML 语义分析 + LLM 判定（V4）
        """
        dismissed = False
        for name, detect_type, detect_value, dismiss_type, dismiss_value in self.BLOCKING_DIALOGS:
            try:
                # 构造检测 selector
                if detect_type == "text":
                    if not self.d(text=detect_value).exists(timeout=0.5):
                        continue
                elif detect_type == "resource-id":
                    if not self.d(resourceId=detect_value).exists(timeout=0.5):
                        continue
                else:
                    continue

                logger.info(f"检测到阻塞屏幕: {name}")

                # 构造关闭 selector 并点击
                if dismiss_type == "text":
                    btn = self.d(text=dismiss_value)
                elif dismiss_type == "resource-id":
                    btn = self.d(resourceId=dismiss_value)
                else:
                    continue

                if btn.exists(timeout=1.0):
                    btn.click()
                    logger.info(f"已关闭阻塞屏幕: {name} (点击 {dismiss_type}={dismiss_value})")
                    time.sleep(1.0)  # 等待屏幕关闭+界面刷新
                    dismissed = True
                else:
                    logger.warning(f"阻塞屏幕 {name} 存在但未找到关闭按钮 ({dismiss_type}={dismiss_value})")
            except Exception as e:
                logger.warning(f"dismiss_dialogs 异常 ({name}): {e}")
        return dismissed

    def _resolve_selector(self, target: str) -> Dict[str, str]:
        """解析 target 字符串为 u2 selector kwargs

        支持格式：
        - "resource-id=xxx" / "text=xxx" / "xpath=xxx" / "desc=xxx" 显式前缀
        - 无前缀时启发式：含中文 → text，含 // → xpath，否则 resourceId
        """
        if not target:
            return {}

        for pattern, key in self.TARGET_PATTERNS:
            m = pattern.match(target.strip())
            if m:
                return {key: m.group(1).strip()}

        # 启发式：含中文 → text，含 // → xpath，否则 resourceId
        target = target.strip()
        if re.search(r'[\u4e00-\u9fff]', target):
            return {"text": target}
        if target.startswith("//"):
            return {"xpath": target}
        return {"resourceId": target}

    def _get_element(self, target: str, timeout: int = 10):
        """根据 target 获取元素（等待出现）"""
        kwargs = self._resolve_selector(target)
        if not kwargs:
            return None
        # xpath 用 d.xpath()
        if "xpath" in kwargs:
            el = self.d.xpath(kwargs["xpath"])
            if el.wait(timeout=timeout):
                return el
            return None
        # 其他用 d(**kwargs)
        el = self.d(**kwargs)
        if el.wait(timeout=timeout):
            return el
        return None

    # === 任务 6.2-6.6：基础操作 ===

    def click(self, target: str, timeout: int = 10) -> bool:
        """点击元素（4 种定位）

        Args:
            target: 元素描述（resource-id=xxx / text=xxx / xpath=xxx / desc=xxx / 启发式）
            timeout: 等待元素出现超时
        Returns: True 点击成功
        """
        try:
            el = self._get_element(target, timeout=timeout)
            if el is None:
                logger.warning(f"click: 元素未找到: {target}")
                return False
            el.click()
            logger.info(f"click: {target}")
            return True
        except Exception as e:
            logger.warning(f"click 异常: {target}: {e}")
            return False

    def input_text(self, target: str, value: str, timeout: int = 10) -> bool:
        """输入文本（先 click 聚焦再 set_text）"""
        try:
            el = self._get_element(target, timeout=timeout)
            if el is None:
                logger.warning(f"input_text: 元素未找到: {target}")
                return False
            # 清空已有内容
            el.clear_text() if hasattr(el, "clear_text") else None
            el.set_text(value)
            logger.info(f"input_text: {target} = {value[:50]}")
            return True
        except Exception as e:
            logger.warning(f"input_text 异常: {target}: {e}")
            return False

    def wait_element(self, target: str, timeout: int = 10) -> bool:
        """等待元素出现"""
        try:
            el = self._get_element(target, timeout=timeout)
            if el is not None:
                logger.info(f"wait_element: {target} 已出现")
                return True
            logger.warning(f"wait_element: 超时未出现: {target}")
            return False
        except Exception as e:
            logger.warning(f"wait_element 异常: {target}: {e}")
            return False

    def scroll(self, direction: str = "down") -> bool:
        """滑动（up/down/left/right）

        简化说明：使用 d.swipe_ext 实现 | 已知上限：仅支持 4 方向 | 升级路径：支持自定义手势（V4）
        """
        try:
            direction = direction.lower().strip()
            # 简化说明：swipe_ext 在 u2 3.x 提供方向滑动 | 已知上限：依赖设备分辨率 | 升级路径：基于坐标计算（V4）
            self.d.swipe_ext(direction, scale=0.5)
            logger.info(f"scroll: {direction}")
            return True
        except Exception as e:
            logger.warning(f"scroll 异常: {direction}: {e}")
            return False

    def press_back(self) -> bool:
        """按返回键"""
        try:
            self.d.press("back")
            logger.info("press_back")
            return True
        except Exception as e:
            logger.warning(f"press_back 异常: {e}")
            return False

    def sleep(self, seconds: float = 1.0) -> bool:
        """等待"""
        time.sleep(seconds)
        return True

    # === 任务 6.7：dump_hierarchy / screenshot ===

    def dump_hierarchy(self) -> str:
        """获取 UI XML 层级"""
        try:
            return self.d.dump_hierarchy()
        except Exception as e:
            logger.warning(f"dump_hierarchy 异常: {e}")
            return ""

    def screenshot(self) -> Optional[bytes]:
        """获取截图（bytes 格式）"""
        try:
            # 简化说明：u2 screenshot 返回 PIL Image，转 bytes | 已知上限：内存占用大 | 升级路径：直接写文件（V4）
            from io import BytesIO
            img = self.d.screenshot()
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logger.warning(f"screenshot 异常: {e}")
            return None

    # === 任务 6.8：execute_step 完整步骤执行 ===

    def execute_step(
        self,
        step: Step,
        screenshot_dir: Optional[Path] = None,
        xml_dir: Optional[Path] = None,
        step_index: int = 0,
    ) -> Dict[str, Any]:
        """执行单个步骤

        流程：
        1. 前置截图+XML（动作执行前）
        2. 执行动作（click/input/wait/scroll/back/assert）
        3. 后置截图+XML（动作执行后）
        4. 操作前后延迟（OPERATION_DELAY_BEFORE/AFTER）

        Args:
            step: Step 对象
            screenshot_dir: 截图保存目录（None 不保存）
            xml_dir: XML 保存目录（None 不保存）
            step_index: 步骤序号（用于文件命名）
        Returns: dict 含 action/target/success/before/after 证据
        """
        result: Dict[str, Any] = {
            "step_index": step_index,
            "action": step.action,
            "target": step.target,
            "value": step.value,
            "raw": step.raw,
            "success": False,
            "before_screenshot": None,
            "before_xml": None,
            "after_screenshot": None,
            "after_xml": None,
            "error": None,
        }

        # 关闭已知阻塞对话框（隐私协议等）
        self.dismiss_dialogs()

        # 前置延迟
        if OPERATION_DELAY_BEFORE > 0:
            time.sleep(OPERATION_DELAY_BEFORE)

        # 1. 前置截图+XML
        if screenshot_dir:
            result["before_screenshot"] = self._save_screenshot(
                screenshot_dir, f"step-{step_index:02d}-before.png"
            )
        if xml_dir:
            result["before_xml"] = self._save_xml(
                xml_dir, f"step-{step_index:02d}-before.xml"
            )

        # 2. 执行动作（任务 6.9：30s 超时保护）
        try:
            success = self._dispatch_action(step)
            result["success"] = success
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"步骤 {step_index} 执行异常: {e}")

        # 3. 后置截图+XML
        if screenshot_dir:
            result["after_screenshot"] = self._save_screenshot(
                screenshot_dir, f"step-{step_index:02d}-after.png"
            )
        if xml_dir:
            result["after_xml"] = self._save_xml(
                xml_dir, f"step-{step_index:02d}-after.xml"
            )

        # 后置延迟
        if OPERATION_DELAY_AFTER > 0:
            time.sleep(OPERATION_DELAY_AFTER)

        logger.info(
            f"步骤 {step_index} 完成: action={step.action}, success={result['success']}"
        )
        return result

    def _dispatch_action(self, step: Step) -> bool:
        """根据 step.action 分发到具体操作

        任务 6.9：单步 30s 超时保护（基于 u2 operation_timeout）
        """
        action = step.action
        target = step.target

        if action == "click":
            return self.click(target)
        elif action == "input":
            # input 步骤：先 click 目标，再 input value
            if not self.click(target):
                return False
            # 简化说明：input 步骤直接对当前焦点元素 set_text | 已知上限：若 click 未聚焦则失败 | 升级路径：定位到 EditText 再 set_text
            try:
                self.d(focused=True).set_text(step.value)
                return True
            except Exception:
                # 退而求其次：直接 send_keys
                try:
                    self.d.send_keys(step.value, clear=True)
                    return True
                except Exception as e:
                    logger.warning(f"input 失败: {e}")
                    return False
        elif action == "wait_element":
            return self.wait_element(target, timeout=TIMEOUT_UI_OPERATION)
        elif action == "scroll":
            return self.scroll(target or "down")
        elif action == "back":
            return self.press_back()
        elif action == "assert":
            # assert 动作：只观察不操作，自动成功
            logger.info(f"assert: {target}")
            return True
        elif action == "sleep":
            try:
                seconds = float(target) if target else 1.0
            except ValueError:
                seconds = 1.0
            return self.sleep(seconds)
        else:
            logger.warning(f"未知 action: {action}")
            return False

    def _save_screenshot(self, directory: Path, filename: str) -> Optional[str]:
        """保存截图到目录"""
        try:
            directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            img = self.d.screenshot()
            img.save(str(path))
            return str(path)
        except Exception as e:
            logger.warning(f"保存截图失败: {e}")
            return None

    def _save_xml(self, directory: Path, filename: str) -> Optional[str]:
        """保存 XML 到目录"""
        try:
            directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            xml = self.d.dump_hierarchy()
            path.write_text(xml, encoding="utf-8")
            return str(path)
        except Exception as e:
            logger.warning(f"保存 XML 失败: {e}")
            return None

    # === 任务 6.10：自愈机制 ===

    def _heal_atx_agent(self) -> bool:
        """自愈：重启 atx-agent

        流程：
        1. adb shell am force-stop com.github.uiautomator
        2. adb shell pkill atx-agent
        3. u2.connect 重新初始化
        """
        if self.memu is None:
            logger.warning("自愈需要 MemuController，但未提供")
            return False
        try:
            logger.info("自愈：重启 atx-agent...")
            self.memu.adb("shell", "am", "force-stop", "com.github.uiautomator")
            self.memu.adb("shell", "pkill", "atx-agent")
            time.sleep(2)
            # 重新初始化 u2 连接
            self.d = u2.connect()
            self.d.implicitly_wait(TIMEOUT_UI_IMPLICIT_WAIT)
            logger.info("自愈完成：atx-agent 已重启")
            return True
        except Exception as e:
            logger.error(f"自愈失败: {e}")
            return False

    def execute_step_with_heal(
        self,
        step: Step,
        screenshot_dir: Optional[Path] = None,
        xml_dir: Optional[Path] = None,
        step_index: int = 0,
    ) -> Dict[str, Any]:
        """带自愈机制的步骤执行

        失败重试 1 次 → 重启 atx-agent → 3 次失败标记步骤失败
        """
        max_retries = 3
        for attempt in range(max_retries):
            result = self.execute_step(step, screenshot_dir, xml_dir, step_index)
            if result["success"]:
                self.failure_count = 0  # 重置失败计数
                return result
            # 失败处理
            self.failure_count += 1
            logger.warning(
                f"步骤 {step_index} 失败（尝试 {attempt + 1}/{max_retries}）: {result.get('error', '')}"
            )
            if attempt < max_retries - 1:
                # 重试前自愈（第 2 次失败时重启 atx-agent）
                if attempt == 1 and self.memu is not None:
                    self._heal_atx_agent()
                time.sleep(1)
        # 3 次都失败
        logger.error(f"步骤 {step_index} 3 次重试均失败，标记为失败")
        return result
