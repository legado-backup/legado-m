"""ai_tests/tests/test_llm_server.py — LlmServerManager 单元测试

任务 1.4：mock 端口/子进程/健康接口，验证 ensure_online 复用/拉起/失败三路径。
运行：
    python -m pytest ai_tests/tests/test_llm_server.py -v
或：
    python -m ai_tests.tests.test_llm_server
"""
import io
from unittest.mock import patch, MagicMock

from ai_tests.config_ai import AI_PORT
from ai_tests.lib.llm_server import LlmServerManager, LlmUnavailableError


class _FakeResp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _healthy_response(*args, **kwargs):
    return _FakeResp(200)


def _patch_socket(open_result: int):
    """mock socket.socket().connect_ex -> open_result"""
    sock = MagicMock()
    sock.connect_ex.return_value = open_result
    ctx = MagicMock()
    ctx.__enter__.return_value = sock
    return patch(
        "ai_tests.lib.llm_server.socket.socket",
        return_value=ctx,
    )


def _make_proc(returncode=None):
    proc = MagicMock()
    proc.pid = 9999
    proc.poll.return_value = returncode
    return proc


# === 1 复用路径：端口有健康服务，不拉起 ===

def test_ensure_online_reuses_existing():
    mgr = LlmServerManager()
    with _patch_socket(0), \
         patch("ai_tests.lib.llm_server.urllib.request.urlopen",
               side_effect=_healthy_response), \
         patch("ai_tests.lib.llm_server.subprocess.Popen") as popen:
        info = mgr.ensure_online()
    assert info["reused"] is True
    assert info["pid"] is None
    popen.assert_not_called()


# === 2 拉起路径：端口无监听 → 拉起 → 健康 ===

def test_ensure_online_spawns():
    mgr = LlmServerManager()
    proc = _make_proc()
    with _patch_socket(1), \
         patch("ai_tests.lib.llm_server.urllib.request.urlopen",
               side_effect=_healthy_response), \
         patch("ai_tests.lib.llm_server.subprocess.Popen",
               return_value=proc) as popen:
        info = mgr.ensure_online()
    assert info["reused"] is False
    assert info["pid"] == 9999
    popen.assert_called_once()
    assert mgr._proc is proc


# === 3 启动失败：子进程退出 → LlmUnavailableError ===

def test_ensure_online_crash_raises():
    mgr = LlmServerManager()
    proc = _make_proc(returncode=1)
    with _patch_socket(1), \
         patch("ai_tests.lib.llm_server.urllib.request.urlopen",
               side_effect=TimeoutError), \
         patch("ai_tests.lib.llm_server.subprocess.Popen",
               return_value=proc):
        try:
            mgr.ensure_online()
            assert False, "应抛 LlmUnavailableError"
        except LlmUnavailableError as e:
            assert "退出" in str(e)


# === 4 健康超时：进程存活但不健康 → LlmUnavailableError ===

def test_ensure_online_health_timeout():
    mgr = LlmServerManager()
    proc = _make_proc()
    with _patch_socket(1), \
         patch("ai_tests.lib.llm_server.urllib.request.urlopen",
               side_effect=TimeoutError), \
         patch("ai_tests.lib.llm_server.subprocess.Popen",
               return_value=proc), \
         patch("ai_tests.lib.llm_server.AI_HEALTH_TIMEOUT", 1):
        try:
            mgr.ensure_online()
            assert False, "应抛 LlmUnavailableError"
        except LlmUnavailableError as e:
            assert "超时" in str(e)


# === 5 _build_cmd：模型路径与参数 ===

def test_build_cmd_contains_model_and_args():
    mgr = LlmServerManager()
    cmd = mgr._build_cmd()
    joined = " ".join(cmd)
    assert "-m" in cmd and "--mmproj" in cmd
    assert "--flash-attn" in joined and "q4_0" in joined
    assert str(AI_PORT) in cmd  # --port
    assert mgr.model.exists() and mgr.mmproj.exists()


# === 6 stop：只终止自有进程 ===

def test_stop_terminates_owned_proc():
    mgr = LlmServerManager()
    proc = _make_proc()
    mgr._proc = proc
    mgr.stop()
    proc.terminate.assert_called_once()
    assert mgr._proc is None


def test_stop_ignores_none():
    mgr = LlmServerManager()
    mgr.stop()  # 不抛异常即可


if __name__ == "__main__":
    tests = [
        ("reuse", test_ensure_online_reuses_existing),
        ("spawn", test_ensure_online_spawns),
        ("crash", test_ensure_online_crash_raises),
        ("timeout", test_ensure_online_health_timeout),
        ("build_cmd", test_build_cmd_contains_model_and_args),
        ("stop", test_stop_terminates_owned_proc),
        ("stop_none", test_stop_ignores_none),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("全部通过")
