"""ai_tests/lib/ai_agent.py — GuiAgent（AI-LLM-Testing GUI Agent 执行器）

职责：视觉驱动屏幕操作——截图 → VL 决策/定位 → 动作执行 → 再观察循环。

能力（AD-02 混合定位）：
- locate(target)：经验 → uiautomator 精确 bounds → VL 视觉 box（降采样坐标逆向映射）三级定位
- tap/swipe/input/back/wait/verify：动作原语（tap 走混合定位）
- heal(target)：UiExecutor 定位失败时的视觉兜底入口（同构接口，供外部调用）
- step(goal)：自主代理循环（观察→决策→动作→再观察，max_iterations 封顶）

定位顺序：确定性/低成本优先，VL 仅兜底；验证成功回写经验层（AD-05）。
"""
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_tests.config import ADB_PATH
from ai_tests.config_ai import AI_IMAGE_MAX_DIM
from ai_tests.lib.ai_experience import AiExperience
from ai_tests.lib.llm_client import (
    LlmClient, image_feed_size, map_box_to_device,
)
from ai_tests.lib.llm_server import LlmUnavailableError

logger = logging.getLogger(__name__)

BOX_RE = re.compile(r"<box>\s*\[\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]\s*\]\s*</box>", re.IGNORECASE)

SYSTEM_AGENT = (
    "你是手机端 UI 自动化代理。你会看到一张当前界面截图与界面文字摘要。"
    "你的任务是执行少量精确动作完成目标。每一步只输出一个 JSON 动作，"
    "不要发散做多余操作。截图最长边已被缩放到640像素，坐标标注在图像上。"
)

ACTION_SCHEMA = (
    "\n\n【输出要求】只输出一个合法 JSON 对象，schema：\n"
    '{"action": "tap|swipe|input|back|wait|done", '
    '"target": "要点击元素的文字描述（供定位，如 番茄小说 的开关）", '
    '"direction": "up|down|left|right（swipe 用）", '
    '"text": "要输入的文本（input 用）", '
    '"seconds": 等待秒数（wait 用，默认1）, '
    '"reason": "这一步的原因（简短）"}\n'
    "当目标已达成或无法在界面中找到所需元素时输出 {\"action\": \"done\"}。"
)

LOCATE_PROMPT = (
    "在这张手机截图（最长边640像素）中定位元素「{target}」（文字或图标）。"
    "用 <box>[[x1,y1,x2,y2]]</box> 输出它在图像上的坐标框。"
    "如果截图中不存在该元素，只输出 NOT_FOUND。"
)


class GuiAgent:
    """GUI Agent 执行器"""

    def __init__(
        self,
        device: Any = None,
        client: Optional[LlmClient] = None,
        experience: Optional[AiExperience] = None,
        adb_path: str = ADB_PATH,
        workdir: Optional[Path] = None,
    ):
        """device: uiautomator2 Device（用于精确 bounds/点击）；
        adb_path: adb 可执行（坐标 tap 兜底）。"""
        self.device = device
        self.client = client or LlmClient()
        self.experience = experience or AiExperience()
        self.adb_path = adb_path
        self.workdir = workdir or (Path(__file__).parent.parent / "tmp_agent")
        self.workdir.mkdir(parents=True, exist_ok=True)

    # === 观察 ===

    def _screenshot(self) -> Optional[Tuple[Path, Tuple[int, int]]]:
        """截图保存到临时目录，返回 (路径, 设备尺寸(w,h))。失败返回 None。"""
        try:
            if self.device is not None:
                img_bytes = self.device.screenshot()
                if img_bytes is None:
                    return None
                from PIL import Image
                import io as _io
                img = Image.open(_io.BytesIO(img_bytes))
                w, h = img.size
                path = self.workdir / f"agent_{uuid.uuid4().hex[:8]}.png"
                img.save(path, "PNG")
                return path, (w, h)
        except Exception as e:
            logger.warning("截图失败: %s", e)
        return None

    def _screen_signature(self, texts: List[str]) -> str:
        """屏幕签名（Activity + 首个可见文本）用于经验隔离"""
        act = "unknown"
        try:
            if self.device is not None:
                act = str(self.device.app_current()["activity"]).rsplit(".", 1)[-1]
        except Exception:
            pass
        key = texts[0][:20] if texts else "no_text"
        return f"{act}:{key}"

    def _dump_texts(self) -> List[str]:
        """uiautomator dump 提取可见文本（前 N 条，供签名/上下文）"""
        try:
            if self.device is None:
                return []
            texts = []
            for el in self.device.xpath("//*[@text!='']").all():
                t = el.attrib.get("text", "")
                if t:
                    texts.append(t[:50])
            return texts[:40]
        except Exception:
            return []

    # === 混合定位（AD-02） ===

    def locate(self, target: str) -> Optional[Tuple[int, int]]:
        """返回目标中心点设备坐标 (x, y)；找不到返回 None。

        顺序：1 经验命中 → 2 uiautomator 精确 bounds → 3 VL 视觉 box。
        """
        texts = self._dump_texts()
        sig = self._screen_signature(texts)

        # 1. 经验层
        box = self.experience.lookup(target, sig)
        if box:
            logger.info("经验命中: %s", target)
            return self._center(box)

        # 2. uiautomator 精确 bounds
        pos = self._uiautomator_locate(target, texts)
        if pos:
            return pos

        # 3. VL 视觉兜底
        pos = self._vl_locate(target)
        if pos:
            self.experience.record_element(target, sig, self._box_from_center(pos))
            return pos
        return None

    def _uiautomator_locate(self, target: str, texts: List[str]) -> Optional[Tuple[int, int]]:
        if self.device is None:
            return None
        for kwargs in self._selector_candidates(target):
            try:
                sel = self.device(**kwargs)
                if sel.exists(timeout=0.8):
                    cx, cy = sel.center()
                    return (int(cx), int(cy))
            except Exception:
                continue
        return None

    def _selector_candidates(self, target: str) -> List[Dict[str, str]]:
        cands: List[Dict[str, str]] = []
        if re.search(r"[\u4e00-\u9fff]", target):
            cands.append({"text": target})
            cands.append({"description": target})
        else:
            cands.append({"text": target})
            cands.append({"resourceId": target})
        return cands

    def _vl_locate(self, target: str) -> Optional[Tuple[int, int]]:
        shot = self._screenshot()
        if shot is None:
            return None
        path, (dev_w, dev_h) = shot
        feed_w, feed_h = image_feed_size(dev_w, dev_h)
        raw = self.client.chat_with_images(
            None, LOCATE_PROMPT.format(target=target), [str(path)]
        )
        m = BOX_RE.search(raw)
        if not m:
            logger.info("VL 未找到元素: %s (raw=%s)", target, raw[:80])
            return None
        x1, y1, x2, y2 = map(float, m.groups())
        box_dev = map_box_to_device([x1, y1, x2, y2],
                                    feed_size=(feed_w, feed_h),
                                    device_size=(dev_w, dev_h))
        return self._center(box_dev)

    @staticmethod
    def _center(box: List[int]) -> Tuple[int, int]:
        return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)

    @staticmethod
    def _box_from_center(center: Tuple[int, int]) -> List[int]:
        x, y = center
        return [x - 30, y - 15, x + 30, y + 15]

    # === 动作原语 ===

    def _execute(self, action: Dict[str, Any]) -> str:
        """执行单个动作，返回状态描述"""
        kind = action.get("action")
        if kind == "tap":
            t = action.get("target", "")
            pos = self.locate(t) if t else None
            if pos:
                self._tap(pos)
                return f"tapped {t} @ {pos}"
            return f"tap_failed: 无法定位 {t}"
        if kind == "swipe":
            direction = action.get("direction", "down")
            self._swipe(direction)
            return f"swiped {direction}"
        if kind == "input":
            self._input(action.get("text", ""))
            return "input done"
        if kind == "back":
            self.device.press("back")
            return "back pressed"
        if kind == "wait":
            time.sleep(float(action.get("seconds", 1)))
            return "waited"
        if kind == "done":
            return "done"
        return f"unknown action {kind}"

    def _tap(self, pos: Tuple[int, int]) -> None:
        try:
            if self.device is not None:
                self.device.click(*pos)
                return
        except Exception as e:
            logger.debug("device.click 失败，改用 adb: %s", e)
        import subprocess
        subprocess.run([self.adb_path, "shell", "input", "tap",
                        str(pos[0]), str(pos[1])], capture_output=True)

    def _swipe(self, direction: str) -> None:
        if self.device is None:
            return
        w, h = self.device.window_size()
        mid_x, mid_y = w // 2, h // 2
        off = int(h * 0.3)
        m = {
            "up": (mid_x, mid_y + off, mid_x, mid_y - off),
            "down": (mid_x, mid_y - off, mid_x, mid_y + off),
            "left": (mid_x + off, mid_y, mid_x - off, mid_y),
            "right": (mid_x - off, mid_y, mid_x + off, mid_y),
        }.get(direction)
        if m:
            self.device.swipe(*m, duration=0.3)

    def _input(self, text: str) -> None:
        if self.device is not None:
            self.device.send_keys(text)

    # === 对外接口 ===

    def heal(self, target: str) -> Optional[Tuple[int, int]]:
        """UiExecutor 定位失败后的视觉兜底（同构接口）"""
        return self.locate(target)

    def step(self, goal: str, max_iterations: int = 8,
             timeout_per_step: int = 300) -> Dict[str, Any]:
        """自主代理循环：观察→决策→动作→再观察

        Returns: {"success", "iterations", "trace", "error?"}
        """
        trace: List[str] = []
        shot = self._screenshot()
        if shot is None:
            return {"success": False, "iterations": 0, "trace": trace,
                    "error": "无法截图"}
        texts = self._dump_texts()
        for i in range(1, max_iterations + 1):
            user = self._build_step_prompt(goal, texts, i)
            try:
                decision = self.client.chat_json(SYSTEM_AGENT, user, shot and [shot[0]])
            except (LlmUnavailableError, Exception) as e:
                return {"success": False, "iterations": i, "trace": trace,
                        "error": f"决策失败: {e}"}
            act = decision.get("action")
            if act == "done":
                trace.append(f"[{i}] done: {decision.get('reason', '')}")
                return {"success": True, "iterations": i, "trace": trace}
            try:
                status = self._execute({**decision, "action": act})
            except Exception as e:
                status = f"execute_error: {e}"
            trace.append(f"[{i}] {status}")
            # 动作后重新观察（保留最近截图）
            shot = self._screenshot()
            if shot is None:
                break
            texts = self._dump_texts()
            time.sleep(0.8)
        return {"success": False, "iterations": max_iterations, "trace": trace,
                "error": "迭代上限未达成目标"}

    def _build_step_prompt(self, goal: str, texts: List[str], step: int) -> str:
        lines = [f"目标：{goal}", f"（第 {step} 步）", "", "当前界面文字摘要："]
        lines.extend(f"- {t}" for t in texts[:25]) if texts else lines.append("（无）")
        lines.append("")
        lines.append("请决定下一步动作。")
        return "\n".join(lines) + ACTION_SCHEMA


# === 自检 ===
if __name__ == "__main__":
    print("[IMPORT OK] ai_agent")