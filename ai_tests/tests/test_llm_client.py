"""ai_tests/tests/test_llm_client.py — LlmClient 单元测试

任务 1.4：mock 响应，验证 parse_json / map_box_to_device / downscale / chat 重试 / chat_json。
运行：
    python -m pytest ai_tests/tests/test_llm_client.py -v
或：
    python -m ai_tests.tests.test_llm_client
"""
import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_tests.lib.llm_client import (
    LlmClient, downscale_image_b64, map_box_to_device, parse_json,
)
from ai_tests.config_ai import AI_IMAGE_MAX_DIM


# === parse_json ===

def test_parse_json_plain():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_code_block():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_extra_text():
    obj = parse_json('好的，判定结果如下 {"verdict": "pass"} 结束')
    assert obj == {"verdict": "pass"}


def test_parse_json_invalid_returns_none():
    assert parse_json("完全不是 JSON") is None


# === map_box_to_device（AD-06 逆向映射） ===

def test_map_box_to_device_known_factor():
    # 设备 800x1280，降采样 640x1024 → 系数 0.8/0.8
    box = [100, 200, 300, 400]
    mapped = map_box_to_device(box, feed_size=(640, 1024), device_size=(800, 1280))
    assert mapped == (125, 250, 375, 500)


def test_map_box_to_device_clamps_out_of_bounds():
    box = [0, 0, 900, 1500]  # 越界
    mapped = map_box_to_device(box, feed_size=(640, 1024), device_size=(800, 1280))
    assert mapped == (0, 0, 800, 1280)


def test_map_box_to_device_nonuniform():
    # 设备 800x1280，输入 400x640 → x 系数 0.5，y 系数 0.5
    box = [10, 20, 30, 40]
    mapped = map_box_to_device(box, feed_size=(400, 640), device_size=(800, 1280))
    assert mapped == (20, 40, 60, 80)


# === downscale_image_b64（AD-06 降采样） ===

def _make_img(path, size=(1600, 2560)):
    from PIL import Image
    img = Image.new("RGB", size, (120, 130, 140))
    img.save(path, "PNG")
    return path


def test_downscale_image_b64(tmp_path):
    import base64
    p = _make_img(str(tmp_path / "big.png"))
    b64 = downscale_image_b64(p)
    raw = base64.b64decode(b64)
    assert raw[:2] == b"\xff\xd8", "应输出 JPEG"
    # 解码确认最长边 == AI_IMAGE_MAX_DIM
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as img:
        assert max(img.size) == AI_IMAGE_MAX_DIM


def test_downscale_image_b64_keeps_small(tmp_path):
    import base64
    p = _make_img(str(tmp_path / "small.png"), size=(400, 600))
    b64 = downscale_image_b64(p)
    from PIL import Image
    with Image.open(io.BytesIO(base64.b64decode(b64))) as img:
        assert img.size == (400, 600)


# === chat 重试与消息构造 ===

class _FakeHttpResp:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._content


def _ok_body(reply):
    return json.dumps({"choices": [{"message": {"content": reply}}]}).encode()


def test_chat_retries_then_succeeds():
    client = LlmClient(max_retries=2)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("first fail")
        return _FakeHttpResp(_ok_body("回复"))

    with patch("ai_tests.lib.llm_client.urllib.request.urlopen",
               side_effect=fake_urlopen):
        reply = client.chat([{"role": "user", "content": "hi"}])
    assert reply == "回复"
    assert calls["n"] == 2


def test_chat_exhausts_retries_raises():
    client = LlmClient(max_retries=2)
    with patch("ai_tests.lib.llm_client.urllib.request.urlopen",
               side_effect=TimeoutError):
        try:
            client.chat([{"role": "user", "content": "hi"}])
            assert False, "应抛 RuntimeError"
        except RuntimeError as e:
            assert "重试" in str(e)


def test_chat_with_images_builds_content(tmp_path):
    p = _make_img(str(tmp_path / "img.png"), size=(100, 100))
    client = LlmClient()
    with patch("ai_tests.lib.llm_client.urllib.request.urlopen") as urlopen:
        urlopen.return_value = _FakeHttpResp(_ok_body("ok"))
        client.chat_with_images("sys", "看图", [p])
    body = json.loads(urlopen.call_args.args[0].data)
    content = body["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "看图"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


# === chat_json ===

def test_chat_json_parses():
    client = LlmClient()
    with patch("ai_tests.lib.llm_client.urllib.request.urlopen") as urlopen:
        urlopen.return_value = _FakeHttpResp(_ok_body('{"verdict": "pass"}'))
        obj = client.chat_json("sys", "判定")
    assert obj == {"verdict": "pass"}


def test_chat_json_parse_failure_raises():
    client = LlmClient(max_retries=1)
    with patch("ai_tests.lib.llm_client.urllib.request.urlopen",
               side_effect=[_FakeHttpResp(_ok_body("不是JSON"))] * 2):
        try:
            client.chat_json("sys", "判定")
            assert False, "应抛 ValueError"
        except ValueError:
            pass


if __name__ == "__main__":
    import tempfile
    tmp = tempfile.mkdtemp()
    tests = [
        ("parse_json_plain", test_parse_json_plain),
        ("parse_json_code", test_parse_json_code_block),
        ("parse_json_extra", test_parse_json_extra_text),
        ("parse_json_invalid", test_parse_json_invalid_returns_none),
        ("map_known", test_map_box_to_device_known_factor),
        ("map_clamp", test_map_box_to_device_clamps_out_of_bounds),
        ("map_nonuniform", test_map_box_to_device_nonuniform),
        ("downscale_big", lambda: test_downscale_image_b64(Path(tmp))),
        ("downscale_small", lambda: test_downscale_image_b64_keeps_small(Path(tmp))),
        ("chat_retry", test_chat_retries_then_succeeds),
        ("chat_exhaust", test_chat_exhausts_retries_raises),
        ("chat_img", lambda: test_chat_with_images_builds_content(Path(tmp))),
        ("chat_json_ok", test_chat_json_parses),
        ("chat_json_fail", test_chat_json_parse_failure_raises),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("全部通过")
