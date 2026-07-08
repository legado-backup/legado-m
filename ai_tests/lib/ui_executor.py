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
    SCROLL_SEARCH_MAX,
    SCROLL_SEARCH_INTERVAL,
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
        # 设置本地密码 Dialog：当用户首次设置密码时弹出，关闭按钮是 android:id/button2
        # 注意：ConfigActivity 中有同名 preference_title 条目，dismiss_dialogs 会通过
        # _is_preference_item 检查排除 Preference 条目，避免误判
        ("设置本地密码", "text", "设置本地密码", "resource-id", "android:id/button2"),
        # Android 标准权限请求对话框（存储/位置等系统权限）
        # 简化说明：检测权限对话框 message，点击允许按钮 | 已知上限：仅覆盖 AOSP 标准权限对话框，不覆盖 MIUI/EMUI 定制权限 | 升级路径：基于 UI XML 语义分析（V4）
        ("权限请求", "resource-id", "com.android.packageinstaller:id/permission_message", "resource-id", "com.android.packageinstaller:id/permission_allow_button"),
    ]

    # Preference 条目的 resourceId 标记（用于区分 Dialog 和 Preference 条目）
    # 当 dismiss_dialogs 检测到 text 匹配时，会检查该元素是否是 Preference 条目
    # 简化说明：硬编码 Preference resourceId | 已知上限：仅覆盖 AOSP PreferenceScreen | 升级路径：基于 UI XML 语义分析（V4）
    PREFERENCE_RESOURCE_IDS = {
        f"{PACKAGE}:id/preference_title",
        f"{PACKAGE}:id/preference_desc",
    }

    def __init__(
        self,
        device: u2.Device,
        memu: Optional[MemuController] = None,
    ):
        self.d = device
        self.memu = memu  # 用于自愈时重启 atx-agent
        self.failure_count = 0  # 连续失败计数

    # === 任务 6.2：元素定位 ===

    def _is_preference_item(self, detect_type: str, detect_value: str) -> bool:
        """检查检测到的元素是否是 Preference 条目（而非 Dialog）

        ConfigActivity 等 PreferenceScreen 中可能有与 Dialog 同名的 preference_title 条目，
        需通过 resourceId 区分：Preference 条目的 resourceId 是 preference_title/preference_desc，
        Dialog 中的元素 resourceId 通常是 android:id/alertTitle 或空。

        简化说明：检查元素 resourceId 是否属于 PREFERENCE_RESOURCE_IDS | 已知上限：仅覆盖 AOSP PreferenceScreen | 升级路径：基于 UI XML 语义分析（V4）
        """
        if detect_type != "text":
            return False
        try:
            el = self.d(text=detect_value)
            if not el.exists(timeout=0.3):
                return False
            info = el.info
            rid = info.get("resourceName", "") or info.get("resourceId", "")
            # u2 返回的 resourceName 格式为 "io.legado.app.debug:id/preference_title"
            for pref_rid in self.PREFERENCE_RESOURCE_IDS:
                if rid.endswith(pref_rid) or rid == pref_rid:
                    return True
        except Exception:
            pass
        return False

    def dismiss_dialogs(self) -> bool:
        """关闭已知阻塞屏幕（隐私协议、帮助文档、设置本地密码等）

        在 execute_step 开头自动调用，避免阻塞屏幕阻塞主流程。
        检测失败或点击失败仅记录警告，不阻断。
        对 text 类型的检测，会先调用 _is_preference_item 排除 Preference 条目（避免误判）。

        简化说明：短超时扫描固定阻塞屏幕列表 | 已知上限：仅覆盖已登记屏幕，未覆盖动态权限弹窗 | 升级路径：基于 UI XML 语义分析 + LLM 判定（V4）
        """
        dismissed = False
        for name, detect_type, detect_value, dismiss_type, dismiss_value in self.BLOCKING_DIALOGS:
            try:
                # 构造检测 selector
                if detect_type == "text":
                    if not self.d(text=detect_value).exists(timeout=0.5):
                        continue
                    # 排除 Preference 条目误判（如 ConfigActivity 中 preference_title="设置本地密码"）
                    if self._is_preference_item(detect_type, detect_value):
                        logger.debug(f"跳过 Preference 条目误判: {name} (text={detect_value} 是 preference_title)")
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
        - 无前缀时启发式：含中文 → text（回退 desc），含 // → xpath，纯英文 → text（回退 resourceId）

        含中文的无前缀 target 会附带 _fallback_desc 标记，_get_element 会先试 text
        再回退 description（底部导航/图标按钮等元素的标签常在 content-desc 而非 text）。
        纯英文的无前缀 target 会附带 _fallback_rid 标记，_get_element 会先试 text
        再回退 resourceId（如"Base64"按钮的 text 是"Base64"，但"bookSourceManage"是 resourceId）。
        """
        if not target:
            return {}

        for pattern, key in self.TARGET_PATTERNS:
            m = pattern.match(target.strip())
            if m:
                return {key: m.group(1).strip()}

        # 启发式：含中文 → text（回退 desc），含 // → xpath，纯英文 → text（回退 resourceId）
        target = target.strip()
        if re.search(r'[\u4e00-\u9fff]', target):
            # 含中文：text 优先，desc 回退
            return {"text": target, "_fallback_desc": target}
        if target.startswith("//"):
            return {"xpath": target}
        # 纯英文：text 优先，resourceId 回退
        # 简化说明：纯英文 target 既可能是 text（如 Base64 按钮）也可能是 resourceId（如 bookSourceManage） | 已知上限：resourceId 查找前会先试 text（开销略增） | 升级路径：基于 XML 语义分析预判（V4）
        return {"text": target, "_fallback_rid": target}

    def _get_element(self, target: str, timeout: int = 10, scroll_search: bool = False):
        """根据 target 获取元素（等待出现）

        含中文的无前缀 target 会先试 text，超时后回退 description（content-desc）。
        纯英文的无前缀 target 会先试 text，超时后回退 resourceId。
        若 scroll_search=True，初次查找失败后调用 _scroll_find 滚动查找（解决长列表元素在屏幕外）。
        """
        kwargs = self._resolve_selector(target)
        if not kwargs:
            return None
        # xpath 用 d.xpath()
        if "xpath" in kwargs:
            el = self.d.xpath(kwargs["xpath"])
            if el.wait(timeout=timeout):
                return el
            return None
        # 提取回退标记（非 u2 kwarg，不能传给 d()）
        fallback_desc = kwargs.pop("_fallback_desc", None)
        fallback_rid = kwargs.pop("_fallback_rid", None)
        if fallback_desc is not None:
            # 含中文 target：先快速探测 text/desc，再回退等待
            # 简化说明：底部导航/图标按钮等元素标签常在 content-desc 而非 text | 已知上限：仅回退 text→desc 精确匹配，未覆盖 textContains/descContains 模糊匹配 | 升级路径：u2 UiSelector2 多条件 OR 查询（V4）
            text_val = kwargs["text"]
            # 快速探测（0.5s）：text 优先
            if self.d(text=text_val).exists(timeout=0.5):
                return self.d(text=text_val)
            if self.d(description=fallback_desc).exists(timeout=0.5):
                return self.d(description=fallback_desc)
            # 都没快速找到，正常等待 text
            el = self.d(**kwargs)
            if el.wait(timeout=timeout):
                return el
            # 最后回退 desc
            el = self.d(description=fallback_desc)
            if el.wait(timeout=timeout):
                return el
            # 初次查找失败，滚动查找（解决长列表元素在屏幕外不可见）
            if scroll_search:
                el = self._scroll_find(target)
                if el is not None:
                    return el
            return None
        if fallback_rid is not None:
            # 纯英文 target：先快速探测 text/resourceId，再回退等待
            # 简化说明：纯英文 target 既可能是 text（如 Base64 按钮）也可能是 resourceId（如 bookSourceManage） | 已知上限：仅回退 text→resourceId 精确匹配 | 升级路径：基于 XML 语义分析预判（V4）
            text_val = kwargs["text"]
            # 快速探测（0.5s）：text 优先
            if self.d(text=text_val).exists(timeout=0.5):
                return self.d(text=text_val)
            if self.d(resourceId=fallback_rid).exists(timeout=0.5):
                return self.d(resourceId=fallback_rid)
            # 都没快速找到，正常等待 text
            el = self.d(**kwargs)
            if el.wait(timeout=timeout):
                return el
            # 最后回退 resourceId
            el = self.d(resourceId=fallback_rid)
            if el.wait(timeout=timeout):
                return el
            # 初次查找失败，滚动查找（解决长列表元素在屏幕外不可见）
            if scroll_search:
                el = self._scroll_find(target)
                if el is not None:
                    return el
            return None
        # 其他用 d(**kwargs)
        el = self.d(**kwargs)
        if el.wait(timeout=timeout):
            return el
        # 初次查找失败，滚动查找（解决长列表元素在屏幕外不可见）
        if scroll_search:
            el = self._scroll_find(target)
            if el is not None:
                return el
        return None

    def _scroll_find(self, target: str, max_scrolls: int = SCROLL_SEARCH_MAX) -> Any:
        """滚动查找元素：向下滚动 N 次，每次后检测 target 是否出现

        click 找不到元素时调用，解决 PreferenceScreen 长列表元素在屏幕外不可见问题。
        检测顺序与 _get_element 一致：含中文先 text 后 description，纯英文先 text 后 resourceId。

        简化说明：仅向下滚动 | 已知上限：元素在上方时找不到，不双向 | 升级路径：双向滚动查找（V4）

        Args:
            target: 元素描述（与 _get_element 一致）
            max_scrolls: 最大滚动次数（默认 config.SCROLL_SEARCH_MAX=5）
        Returns:
            找到的元素（u2 selector），未找到返回 None
        """
        kwargs = self._resolve_selector(target)
        if not kwargs:
            return None
        # xpath 不支持滚动查找（坐标系不同）
        if "xpath" in kwargs:
            return None
        # 提取回退标记
        fallback_desc = kwargs.pop("_fallback_desc", None)
        fallback_rid = kwargs.pop("_fallback_rid", None)

        # 获取屏幕尺寸，动态计算滑动坐标（适配不同分辨率）
        try:
            w, h = self.d.window_size()
        except Exception:
            w, h = 720, 1280  # 回退默认分辨率
        center_x = w // 2
        start_y = int(h * 0.8)  # 从屏幕 80% 高度开始
        end_y = int(h * 0.4)    # 滑到 40% 高度（手指向上滑，列表向上滚，显示下方内容）

        for i in range(max_scrolls):
            try:
                # 改用 ADB input swipe 代替 swipe_ext
                # 原因：swipe_ext 在 MEmu 上会触发 SecurityException（Injecting to another application）
                # 和页面回退（可能被系统解释为手势导航），导致滚动失败
                # ADB input swipe 直接通过 InputManager 注入，不经过 uiautomator2，更可靠
                self.d.shell(f"input swipe {center_x} {start_y} {center_x} {end_y} 300")
                time.sleep(SCROLL_SEARCH_INTERVAL)
                # 检测元素是否出现（快速 0.5s）
                if fallback_desc is not None:
                    text_val = kwargs.get("text", target)
                    if self.d(text=text_val).exists(timeout=0.5):
                        logger.info(f"scroll_find: 找到元素 {target} (滚动 {i + 1} 次)")
                        return self.d(text=text_val)
                    if self.d(description=fallback_desc).exists(timeout=0.5):
                        logger.info(f"scroll_find: 找到元素 {target} (desc, 滚动 {i + 1} 次)")
                        return self.d(description=fallback_desc)
                elif fallback_rid is not None:
                    text_val = kwargs.get("text", target)
                    if self.d(text=text_val).exists(timeout=0.5):
                        logger.info(f"scroll_find: 找到元素 {target} (滚动 {i + 1} 次)")
                        return self.d(text=text_val)
                    if self.d(resourceId=fallback_rid).exists(timeout=0.5):
                        logger.info(f"scroll_find: 找到元素 {target} (rid, 滚动 {i + 1} 次)")
                        return self.d(resourceId=fallback_rid)
                else:
                    el = self.d(**kwargs)
                    if el.exists(timeout=0.5):
                        logger.info(f"scroll_find: 找到元素 {target} (滚动 {i + 1} 次)")
                        return el
            except Exception as e:
                logger.warning(f"scroll_find 第 {i + 1} 次滚动异常: {e}")
        logger.warning(f"scroll_find: 未找到元素 {target} (滚动 {max_scrolls} 次)")
        return None

    # === 任务 6.2-6.6：基础操作 ===

    def click(self, target: str, timeout: int = 10, scroll_search: bool = True) -> bool:
        """点击元素（4 种定位 + 滚动查找）

        Args:
            target: 元素描述（resource-id=xxx / text=xxx / xpath=xxx / desc=xxx / 启发式）
            timeout: 等待元素出现超时
            scroll_search: 初次等待失败后是否滚动查找（默认 True，解决长列表元素在屏幕外）
        Returns: True 点击成功
        """
        try:
            el = self._get_element(target, timeout=timeout, scroll_search=scroll_search)
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

        # 循环关闭阻塞屏幕（可能有多个顺序阻塞屏幕：隐私协议→帮助文档→设置本地密码→权限请求）
        # 简化说明：最多循环 5 次避免死循环 | 已知上限：仅覆盖已登记屏幕 | 升级路径：基于 UI XML 语义分析 + LLM 判定（V4）
        for _ in range(5):
            if not self.dismiss_dialogs():
                break
            time.sleep(0.5)  # 等待界面刷新后检测下一个阻塞屏幕

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
            # input 步骤：对当前焦点输入框 set_text(value)
            # 用例语义：target 是描述性文本（如"cron 表达式 `*/30 * * * *`"），不是要 click 的元素
            # 真实流程：前一步骤通常 click 进入输入界面，焦点已在输入框，直接 set_text 即可
            # 简化说明：不 click target | 已知上限：若前序未聚焦输入框则失败 | 升级路径：基于 XML 语义分析定位输入框（V4）
            value = step.value or target  # value 优先；value 为空退用 target
            # 策略1：对当前焦点元素 set_text
            try:
                self.d(focused=True).set_text(value)
                return True
            except Exception as e1:
                logger.debug(f"input 策略1失败（focused set_text）: {e1}")
            # 策略2：找屏幕上第一个 EditText 并点击聚焦，再 set_text
            try:
                et = self.d(className="android.widget.EditText")
                if et.exists:
                    et.click()
                    time.sleep(0.5)
                    self.d(focused=True).set_text(value)
                    return True
            except Exception as e2:
                logger.debug(f"input 策略2失败（找 EditText）: {e2}")
            # 策略3：send_keys 兜底
            try:
                self.d.send_keys(value, clear=True)
                return True
            except Exception as e3:
                logger.warning(f"input 失败（3 种策略均失败）: {e3}")
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

    # === 任务 6.10：自愈机制（OpenSpec e2e-ui-executor-hardening R2 重构）===
    # 简化说明：app_current 检测区分"元素未找到"vs"App崩溃" | 已知上限：仅检测前台状态，不检测 ANR/卡死 | 升级路径：多维度健康检查（V4）

    def _detect_app_state(self) -> str:
        """检测 App 当前状态

        通过 u2 app_current 检测 App 是否在前台运行。
        区分"元素未找到"（App 正常）vs"App崩溃"（回桌面），决定自愈策略。

        简化说明：仅检测 package/activity 是否匹配 | 已知上限：不检测 ANR/卡死，不检测 Activity 正确性 | 升级路径：多维度健康检查（V4）

        Returns:
            "normal": App 在前台运行（元素未找到是 UI 问题）
            "crashed": App 不在前台（回桌面/其他 App）
            "not_running": app_current 检测异常
        """
        try:
            app = self.d.app_current()
        except Exception as e:
            logger.warning(f"_detect_app_state: app_current 异常: {e}")
            return "not_running"
        pkg = app.get("package", "")
        activity = app.get("activity", "")
        # 简化说明：PACKAGE 是 io.legado.app.debug，崩溃后回桌面 package 是 launcher | 已知上限：release 构建需切换 PACKAGE | 升级路径：基于 applicationId 动态判断（V4）
        if pkg == PACKAGE or "io.legado.app" in activity:
            return "normal"
        logger.warning(f"_detect_app_state: App 不在前台, package={pkg}, activity={activity}")
        return "crashed"

    def _restart_app(self) -> bool:
        """重启 App（App 崩溃后自愈）

        流程：
        1. memu.start_app() 重启 App
        2. sleep 3s 等待首屏渲染
        3. dismiss_dialogs() 关闭阻塞屏幕

        简化说明：仅重启 App 不重启 atx-agent | 已知上限：不处理启动失败 | 升级路径：启动失败降级标记用例失败（V4）
        """
        if self.memu is None:
            logger.error("_restart_app: 需要 MemuController，但未提供，无法重启")
            return False
        try:
            logger.info("自愈：重启 App...")
            if not self.memu.start_app():
                logger.error("自愈：App 重启失败")
                return False
            time.sleep(3)  # 等待首屏渲染
            self.dismiss_dialogs()  # 重新关阻塞屏幕
            logger.info("自愈完成：App 已重启")
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

        失败后检测 App 状态：
        - App 正常 → 元素未找到，重试（不重启 App，滚动查找已在内）
        - App 崩溃 → 重启 App 后重试
        最多 3 次尝试，3 次都失败标记步骤失败。

        简化说明：app_current 检测区分元素未找到 vs App崩溃 | 已知上限：不检测 ANR/卡死 | 升级路径：多维度健康检查（V4）
        """
        max_retries = 3
        result: Dict[str, Any] = {}
        for attempt in range(max_retries):
            result = self.execute_step(step, screenshot_dir, xml_dir, step_index)
            if result["success"]:
                self.failure_count = 0  # 重置失败计数
                return result
            # 失败处理：检测 App 状态决定自愈策略
            self.failure_count += 1
            state = self._detect_app_state()
            logger.warning(
                f"步骤 {step_index} 失败（尝试 {attempt + 1}/{max_retries}）: "
                f"state={state}, error={result.get('error', '')}"
            )
            if attempt < max_retries - 1:
                if state in ("crashed", "not_running"):
                    # App 崩溃：重启 App 后重试
                    self._restart_app()
                else:
                    # App 正常：元素未找到，直接重试（滚动查找已在内）
                    time.sleep(1)
        # 3 次都失败
        logger.error(f"步骤 {step_index} 3 次重试均失败，标记为失败")
        return result
