"""ai_tests/lib/llm_client.py — LlmClient（AI-LLM-Testing 基建）

职责：OpenAI 兼容 /v1/chat/completions 客户端（AD-03）：
- chat_with_images：文本 + 多图消息（发送前统一降采样归一化，AD-06）
- chat_json：要求结构化 JSON 输出并健壮解析（重试 2 次 + 超时）
- 图像工具：downscale_image 降采样；map_box_to_device 坐标逆向映射（已知系数精确还原）

依赖：urllib / json / PIL（已装 12.3.0）
"""
import base64
import io
import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from ai_tests.config_ai import (
    AI_BASE_URL, AI_MODEL_ID, AI_REQUEST_TIMEOUT, AI_MAX_RETRIES,
    AI_MAX_TOKENS, AI_TEMP, AI_IMAGE_MAX_DIM, AI_IMAGE_JPEG_QUALITY,
)

logger = logging.getLogger(__name__)


class LlmClient:
    """OpenAI 兼容多模态客户端（llama-server / 任意 OpenAI 兼容后端）"""

    def __init__(
        self,
        base_url: str = AI_BASE_URL,
        model: str = AI_MODEL_ID,
        timeout: int = AI_REQUEST_TIMEOUT,
        max_retries: int = AI_MAX_RETRIES,
        max_tokens: int = AI_MAX_TOKENS,
        temperature: float = AI_TEMP,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.temperature = temperature

    # === 底层调用 ===

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """原始 chat.completions 调用（重试 max_retries 次）。

        messages 支持 OpenAI 多模态结构：
        [{"role":"user","content":[{"type":"text","text":...},
                                    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}]
        """
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/v1/chat/completions",
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return content or ""
            except (urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as e:
                last_err = e
                logger.warning("LlmClient 第 %s 次调用失败: %s", attempt + 1, e)
        raise RuntimeError(f"LlmClient 调用失败（重试 {self.max_retries} 次仍失败）: {last_err}")

    # === 多模态/工具 ===

    def chat_with_images(
        self,
        system: str,
        user: str,
        image_paths: Optional[List[str]] = None,
    ) -> str:
        """文本 + 多图对话；图像发送前统一降采样归一化（AD-06）。"""
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        content: List[Dict[str, Any]] = [{"type": "text", "text": user}]
        for p in image_paths or []:
            b64 = downscale_image_b64(p)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        messages.append({"role": "user", "content": content})
        return self.chat(messages)

    def chat_json(
        self,
        system: str,
        user: str,
        image_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """要求 JSON 输出并健壮解析。

        解析策略：整段 JSON → 失败则提取首个 {...} 块 → 失败抛 ValueError。
        """
        for attempt in range(self.max_retries + 1):
            instruction = (
                user + "\n\n【输出要求】只输出一个合法 JSON 对象（不要 markdown 代码块、"
                "不要多余文字）。"
            )
            raw = self.chat_with_images(system, instruction, image_paths)
            parsed = parse_json(raw)
            if parsed is not None:
                return parsed
            logger.warning("chat_json 第 %s 次解析失败，raw=%s", attempt + 1, raw[:200])
        raise ValueError(f"chat_json 结构化输出解析失败: {raw[:300]}")


# === 图像工具（AD-06） ===

def downscale_image_b64(image_path: str, max_dim: int = AI_IMAGE_MAX_DIM) -> str:
    """读图 → 等比降采样到最长边 max_dim → JPEG base64。

    Returns: data URL 的 body（不含 data: 前缀），调用方拼接。
    """
    img = Image.open(image_path)
    img = img.convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > max_dim:
        scale = max_dim / longest
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=AI_IMAGE_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def image_feed_size(width: int, height: int, max_dim: int = AI_IMAGE_MAX_DIM) -> Tuple[int, int]:
    """计算图像降采样后的 feed 尺寸（与 downscale_image_b64 缩放一致）"""
    longest = max(width, height)
    if longest <= max_dim:
        return width, height
    scale = max_dim / longest
    return (max(1, round(width * scale)), max(1, round(height * scale)))


def map_box_to_device(
    box: List[float],
    feed_size: Tuple[int, int],
    device_size: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    """VL 返回 box（降采样图坐标）→ 设备原生坐标（已知系数精确还原，AD-06）。

    box: [x1, y1, x2, y2]（模型内部失真由校准经验层处理，此处只还原等比缩放）
    越界值钳制到设备尺寸内。
    """
    fx = feed_size[0] / device_size[0]
    fy = feed_size[1] / device_size[1]
    x1 = int(max(0, min(device_size[0], box[0] / fx if fx else box[0])))
    y1 = int(max(0, min(device_size[1], box[1] / fy if fy else box[1])))
    x2 = int(max(x1, min(device_size[0], box[2] / fx if fx else box[2])))
    y2 = int(max(y1, min(device_size[1], box[3] / fy if fy else box[3])))
    return (x1, y1, x2, y2)


def parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """健壮 JSON 解析：整段 → 提取首个 {...}。"""
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return None


# === 自检 ===
if __name__ == "__main__":
    empty = parse_json("```json\n{\"a\": 1}\n```")
    assert empty == {"a": 1}, f"parse_json 失败: {empty}"
    print("[PASS] parse_json")