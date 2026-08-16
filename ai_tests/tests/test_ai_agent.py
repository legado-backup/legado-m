"""ai_tests/tests/test_ai_agent.py — GuiAgent 单元测试

任务 3.4：mock device + LlmClient，验证混合定位三级 / 动作执行 / step 循环。
运行：
    python -m pytest ai_tests/tests/test_ai_agent.py -v
或：
    python -m ai_tests.tests.test_ai_agent
"""
import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from ai_tests.lib.ai_agent import GuiAgent
from ai_tests.lib.ai_experience import AiExperience


def _fake_device(shot_size=(800, 1280)):
    """u2 Device mock：screenshot 返回 PNG bytes，元素查找默认失败"""
    d = MagicMock()
    buf = io.BytesIO()
    Image.new("RGB", shot_size, (40, 50, 60)).save(buf, "PNG")
    d.screenshot.return_value = buf.getvalue()
    d.window_size.return_value = shot_size
    d.app_current.return_value = {"activity": "ui.main.MainActivity"}
    # 任意元素默认不存在（走 VL 兜底路径）
    sel = MagicMock()
    sel.exists.return_value = False
    d.return_value = sel
    # xpath 文本为空
    d.xpath.return_value.all.return_value = []
    return d


def _client(locate_reply=None, chat_json_replies=None):
    c = MagicMock()
    if locate_reply is not None:
        c.chat_with_images.return_value = locate_reply
    if chat_json_replies is not None:
        c.chat_json.side_effect = list(chat_json_replies)
    return c


def _agent(device=None, client=None, exp=None):
    tmp = Path(tempfile.mkdtemp())
    return GuiAgent(device=device or _fake_device(), client=client or _client(),
                    experience=exp or AiExperience(tmp / "exp.json"),
                    workdir=tmp)


# === 混合定位三级 ===

def test_locate_experience_hit():
    exp = AiExperience(Path(tempfile.mkdtemp()) / "e.json")
    exp.record_element("开关", "MainActivity:no_text", [300, 400, 500, 600])
    ag = _agent(exp=exp)
    pos = ag.locate("开关")
    assert pos == (400, 500)  # 经验中心


def test_locate_uiautomator_path():
    d = _fake_device()
    sel = MagicMock()
    sel.exists.return_value = True
    sel.center.return_value = (123, 456)
    d.return_value = sel
    ag = _agent(device=d)
    pos = ag.locate("番茄小说")
    assert pos == (123, 456)
    d.assert_called()  # 走了 uiautomator


def test_locate_vl_fallback_maps_coords():
    # 800x1280 降采样: 最长边1280→640，feed=(400,640)，系数 0.5
    c = _client(locate_reply="<box>[[200, 300, 400, 500]]</box>")
    ag = _agent(client=c)
    pos = ag.locate("开关")
    # 设备坐标: x = 200/0.5=400..400/0.5=800 → 中心 600; y = 300/0.5=600..500/0.5=1000 → 中心 800
    assert pos == (600, 800)
    # 回写经验
    assert ag.experience.lookup("开关", "MainActivity:no_text") is not None


def test_locate_vl_not_found():
    c = _client(locate_reply="NOT_FOUND")
    ag = _agent(client=c)
    assert ag.locate("不存在") is None


def test_heal_returns_position():
    d = _fake_device()
    sel = MagicMock()
    sel.exists.return_value = True
    sel.center.return_value = (10, 20)
    d.return_value = sel
    ag = _agent(device=d)
    assert ag.heal("返回") == (10, 20)


# === 动作执行 ===

def test_execute_tap_uses_locate_and_click():
    d = _fake_device()
    sel = MagicMock()
    sel.exists.return_value = True
    sel.center.return_value = (88, 99)
    d.return_value = sel
    ag = _agent(device=d)
    status = ag._execute({"action": "tap", "target": "菜单"})
    assert "tapped" in status
    d.click.assert_called_with(88, 99)


def test_execute_unknown_action():
    ag = _agent()
    assert "unknown action" in ag._execute({"action": "explode"})


def test_execute_swipe():
    d = _fake_device()
    ag = _agent(device=d)
    ag._execute({"action": "swipe", "direction": "up"})
    d.swipe.assert_called_once()


# === step 循环 ===

def test_step_done_loop():
    c = _client(locate_reply="<box>[[100,100,200,200]]</box>",
                chat_json_replies=[
                    {"action": "tap", "target": "开关", "reason": "点击"},
                    {"action": "done", "reason": "已生效"},
                ])
    d = _fake_device()
    sel = MagicMock()
    sel.exists.return_value = False
    d.return_value = sel
    ag = _agent(device=d, client=c)
    result = ag.step("打开番茄小说开关", max_iterations=5)
    assert result["success"] is True
    assert result["iterations"] == 2
    assert len(result["trace"]) == 2


def test_step_max_iterations():
    c = _client(locate_reply="NOT_FOUND",
                chat_json_replies=[
                    {"action": "tap", "target": "x", "reason": "r"}] * 3)
    ag = _agent(client=c)
    result = ag.step("任务", max_iterations=3)
    assert result["success"] is False
    assert result["iterations"] == 3
    assert "迭代上限" in result["error"]


if __name__ == "__main__":
    tests = [
        ("exp_hit", test_locate_experience_hit),
        ("uiauto", test_locate_uiautomator_path),
        ("vl_map", test_locate_vl_fallback_maps_coords),
        ("vl_nf", test_locate_vl_not_found),
        ("heal", test_heal_returns_position),
        ("tap", test_execute_tap_uses_locate_and_click),
        ("unknown", test_execute_unknown_action),
        ("swipe", test_execute_swipe),
        ("step_done", test_step_done_loop),
        ("step_max", test_step_max_iterations),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("全部通过")
