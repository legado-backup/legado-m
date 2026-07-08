"""ai_tests/tests/test_feedback_loop.py — M16 反馈闭环单元测试（任务 16.7）

原生 assert 实现，开箱即可运行：
    python ai_tests/tests/test_feedback_loop.py

覆盖：
- mock feedback_signal（fail/manual 各一）→ 4 类输出全部生成
- known_issues.md / regression_history.md 正确追加
- _is_pattern_exists 边界
- 复用 feedback_loop.py 内置 _run_self_test（3 类用例：正常/边界/异常）
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_tests.lib.feedback_loop import FeedbackLoop, _run_self_test  # noqa: E402
from ai_tests import config  # noqa: E402


def test_is_pattern_exists():
    """_is_pattern_exists 边界：已存在模式返回 True，不存在返回 False"""
    fl = FeedbackLoop(
        known_issues_path=Path("/tmp/_ki_test.md"),
        regression_history_path=Path("/tmp/_rh_test.md"),
    )
    # CRASH_PATTERNS 中存在的模式
    assert fl._is_pattern_exists("FATAL EXCEPTION") is True
    assert fl._is_pattern_exists("OutOfMemoryError") is True
    assert fl._is_pattern_exists("ClassNotFoundException") is True
    # 不存在的模式
    assert fl._is_pattern_exists("SomeNewException") is False
    assert fl._is_pattern_exists("") is False


def test_extract_root_cause_categories():
    """_extract_root_cause 各分类命中"""
    fl = FeedbackLoop(
        known_issues_path=Path("/tmp/_ki_test2.md"),
        regression_history_path=Path("/tmp/_rh_test2.md"),
    )
    # FATAL（已覆盖）
    rc = fl._extract_root_cause({
        "reason": "FATAL EXCEPTION: main",
        "feedback_signal": {},
    })
    assert rc["type"] == "exception" and rc["covered"] is True
    assert rc["category"] == "FATAL"
    # 新异常（未覆盖）
    rc2 = fl._extract_root_cause({
        "reason": "抛出 SocketTimeoutException 等待超时",
    })
    assert rc2["type"] == "exception" and rc2["covered"] is False
    assert rc2["pattern"] == "SocketTimeoutException"
    # 非异常
    rc3 = fl._extract_root_cause({"reason": "assert 失败"})
    assert rc3["type"] == "assertion"
    rc4 = fl._extract_root_cause({"reason": "请求 timeout 超时"})
    assert rc4["type"] == "timeout"
    rc5 = fl._extract_root_cause({"reason": "未知错误"})
    assert rc5["type"] == "unknown"


def test_run_self_test():
    """复用 feedback_loop.py 内置自检（3 类用例：正常/边界/异常）"""
    _run_self_test()


if __name__ == "__main__":
    test_run_self_test()
    test_is_pattern_exists()
    test_extract_root_cause_categories()
    print("✅ test_feedback_loop.py 全部通过")
