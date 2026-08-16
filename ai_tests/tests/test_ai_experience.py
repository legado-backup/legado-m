"""ai_tests/tests/test_ai_experience.py — AiExperience 单元测试

任务 4.3：验证元素/判定样本持久化、签名隔离、上限裁剪。
运行：
    python -m pytest ai_tests/tests/test_ai_experience.py -v
或：
    python -m ai_tests.tests.test_ai_experience
"""
import tempfile
from pathlib import Path

from ai_tests.lib.ai_experience import AiExperience


def _exp():
    return AiExperience(Path(tempfile.mkdtemp()) / "e.json")


def test_lookup_miss_returns_none():
    assert _exp().lookup("任意", "Screen:x") is None


def test_record_and_lookup():
    exp = _exp()
    exp.record_element("开关", "Screen:番茄小说", [100, 200, 300, 400])
    assert exp.lookup("开关", "Screen:番茄小说") == [100, 200, 300, 400]


def test_screen_signature_isolation():
    exp = _exp()
    exp.record_element("开关", "ScreenA:x", [1, 2, 3, 4])
    assert exp.lookup("开关", "ScreenB:x") is None


def test_save_load_roundtrip():
    exp = _exp()
    exp.record_element("开关", "S:s", [1, 2, 3, 4])
    exp.add_verdict("TC-1", "h", "pass", 90, "n")
    exp.save()
    exp2 = AiExperience(exp.path)
    assert exp2.lookup("开关", "S:s") == [1, 2, 3, 4]
    assert exp2.stats()["verdicts"] == 1


def test_verdict_cap_200():
    exp = _exp()
    for i in range(250):
        exp.add_verdict(f"TC-{i}", f"h{i}", "manual", 50)
    assert exp.stats()["verdicts"] == 200


def test_stats():
    exp = _exp()
    exp.record_element("a", "S1:s", [0, 0, 1, 1])
    exp.record_element("b", "S1:s", [0, 0, 1, 1])
    exp.record_element("c", "S2:s", [0, 0, 1, 1])
    st = exp.stats()
    assert st["screens"] == 2 and st["elements"] == 3


if __name__ == "__main__":
    tests = [
        ("miss", test_lookup_miss_returns_none),
        ("record", test_record_and_lookup),
        ("isolate", test_screen_signature_isolation),
        ("roundtrip", test_save_load_roundtrip),
        ("cap", test_verdict_cap_200),
        ("stats", test_stats),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("全部通过")
