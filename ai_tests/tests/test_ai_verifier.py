"""ai_tests/tests/test_ai_verifier.py — AiVerifier 单元测试

任务 2.4：mock LlmClient，验证判定归一化 / 回填 report.json / 降级。
运行：
    python -m pytest ai_tests/tests/test_ai_verifier.py -v
或：
    python -m ai_tests.tests.test_ai_verifier
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

from ai_tests.lib.ai_verifier import AiVerifier
from ai_tests.lib.llm_server import LlmUnavailableError


def _make_case(tc_dir: Path, prompt: str = "判定依据...", shots: int = 1):
    """构造含 ai-prompt.md 与截图的用例目录，返回 report.json case dict"""
    tc_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = tc_dir / "ai-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    if shots:
        shot_dir = tc_dir / "screenshot"
        shot_dir.mkdir(exist_ok=True)
        from PIL import Image
        for i in range(shots):
            Image.new("RGB", (100, 100), (10 * i, 20, 30)).save(shot_dir / f"s{i}.png")
    return {
        "tc_id": "TC-F-P0-6-01",
        "title": "测试用例",
        "module": "F-P0-6",
        "verdict": "manual",
        "confidence": 50,
        "reason": "证据不足",
        "ai_prompt_path": str(prompt_path),
    }


def _fake_client(reply=None, exc=None):
    c = MagicMock()
    if exc:
        c.chat_json.side_effect = exc
    else:
        c.chat_json.return_value = reply
    return c


# === verify_case 归一化 ===

def test_verify_case_pass(tmp_path):
    case = _make_case(tmp_path)
    verifier = AiVerifier(client=_fake_client(
        {"verdict": "pass", "confidence": 88, "reason": "截图确认已生效",
         "evidence_refs": ["s1.png"]}))
    av = verifier.verify_case(case)
    assert av["verdict"] == "pass"
    assert av["confidence"] == 88
    assert av["screenshots_used"] == 1
    assert av["model"] == "qwen3vl"


def test_verify_case_low_confidence_forces_manual(tmp_path):
    case = _make_case(tmp_path)
    verifier = AiVerifier(client=_fake_client(
        {"verdict": "fail", "confidence": 55, "reason": "不太确定", "evidence_refs": []}))
    av = verifier.verify_case(case)
    assert av["verdict"] == "manual"  # <70 强转
    assert av["confidence"] == 55


def test_verify_case_invalid_verdict(tmp_path):
    case = _make_case(tmp_path)
    verifier = AiVerifier(client=_fake_client(
        {"verdict": "uncertain", "confidence": 90, "reason": "x", "evidence_refs": []}))
    av = verifier.verify_case(case)
    assert av["verdict"] == "manual"


def test_verify_case_skipped_no_evidence(tmp_path):
    case = {
        "tc_id": "TC-X",
        "title": "x",
        "verdict": "manual",
        "ai_prompt_path": None,
    }
    verifier = AiVerifier(client=_fake_client({"verdict": "pass"}))
    av = verifier.verify_case(case)
    assert av.get("skipped") is True
    assert av["verdict"] == "manual"


def test_verify_case_max_screenshots(tmp_path):
    case = _make_case(tmp_path, shots=8)
    verifier = AiVerifier(client=_fake_client(
        {"verdict": "manual", "confidence": 50, "reason": "r", "evidence_refs": []}))
    av = verifier.verify_case(case)
    assert av["screenshots_used"] == 4  # 上限裁剪


# === verify_report 回填 ===

def test_verify_report_backfills(tmp_path):
    tc_dir = tmp_path / "TC-F-P0-6-01"
    case = _make_case(tc_dir)
    report = {
        "env": {"device": "MEmu"},
        "cases": [case, {"tc_id": "TC-OK", "verdict": "pass", "title": "ok"}],
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    verifier = AiVerifier(
        client=_fake_client({"verdict": "pass", "confidence": 90, "reason": "好",
                             "evidence_refs": ["s0.png"]}),
        report_dir=tmp_path)
    summary = verifier.verify_report(report_path)
    assert summary["manual_total"] == 1
    assert summary["ai_verified"] == 1

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["cases"][0]["ai_verdict"]["verdict"] == "pass"
    # 非 manual 用例不受影响
    assert "ai_verdict" not in data["cases"][1]
    assert (tmp_path / "ai_verdicts.md").exists()


def test_verify_report_unavailable_degrades(tmp_path):
    tc_dir = tmp_path / "TC-A"
    case = _make_case(tc_dir)
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(
        {"cases": [case]}, ensure_ascii=False), encoding="utf-8")
    verifier = AiVerifier(
        client=_fake_client(exc=LlmUnavailableError("no gpu")),
        report_dir=tmp_path)
    summary = verifier.verify_report(report_path)
    assert summary["ai_unavailable"] is True
    assert summary["ai_verified"] == 0
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert "ai_verdict" not in data["cases"][0]  # 降级不写回


def test_verify_report_no_manual(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(
        {"cases": [{"tc_id": "A", "verdict": "pass", "title": "a"}]},
        ensure_ascii=False), encoding="utf-8")
    verifier = AiVerifier(client=_fake_client(), report_dir=tmp_path)
    summary = verifier.verify_report(report_path)
    assert summary["manual_total"] == 0
    assert summary["ai_verified"] == 0


def test_verify_report_missing_file(tmp_path):
    verifier = AiVerifier(client=_fake_client(), report_dir=tmp_path)
    try:
        verifier.verify_report(tmp_path / "nope.json")
        assert False, "应抛 FileNotFoundError"
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    tests = [
        ("pass", lambda: test_verify_case_pass(tmp)),
        ("low_conf", lambda: test_verify_case_low_confidence_forces_manual(tmp)),
        ("invalid_verdict", lambda: test_verify_case_invalid_verdict(tmp)),
        ("skipped", lambda: test_verify_case_skipped_no_evidence(tmp)),
        ("max_shots", lambda: test_verify_case_max_screenshots(tmp)),
        ("backfill", lambda: test_verify_report_backfills(tmp)),
        ("degrade", lambda: test_verify_report_unavailable_degrades(tmp)),
        ("no_manual", lambda: test_verify_report_no_manual(tmp)),
        ("missing", lambda: test_verify_report_missing_file(tmp)),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("全部通过")
