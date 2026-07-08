"""ai_tests/tests/test_evidence_collector.py — M5 单元测试

任务 7.12 验证：8 类证据收集 + 并行 + 降级标记

运行：
    python -m pytest ai_tests/tests/test_evidence_collector.py -v
或：
    python ai_tests/tests/test_evidence_collector.py
"""
import sys
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.evidence_collector import EvidenceCollector
from ai_tests.lib.memu_controller import MemuController


def _make_memu(adb_returns=None):
    """构造 mock MemuController

    Args:
        adb_returns: list of (rc, stdout, stderr) 按调用顺序返回；None 时返回成功空结果
    """
    memu = MemuController()
    if adb_returns is None:
        memu.adb = MagicMock(return_value=(0, "", ""))
    else:
        memu.adb = MagicMock(side_effect=adb_returns)
    return memu


# === 7.1 类骨架 ===

def test_evidence_collector_instantiation():
    """正常用例：EvidenceCollector 可实例化"""
    ec = EvidenceCollector(_make_memu())
    assert ec.package.startswith("io.legado.app")
    assert ec._logcat_start is None
    print("[PASS] test_evidence_collector_instantiation")


def test_evidence_collector_none_memu():
    """异常用例：memu 为 None 抛 ValueError"""
    try:
        EvidenceCollector(None)
        raise AssertionError("应抛 ValueError")
    except ValueError:
        pass
    print("[PASS] test_evidence_collector_none_memu")


def test_evidence_collector_custom_package():
    """边界用例：自定义 package"""
    ec = EvidenceCollector(_make_memu(), package="com.test.app")
    assert ec.package == "com.test.app"
    print("[PASS] test_evidence_collector_custom_package")


# === 7.2/7.3 配置常量复用 ===

def test_config_constants_imported():
    """正常用例：CRASH_PATTERNS 和 DB_QUERIES 从 config 复用"""
    from ai_tests.config import CRASH_PATTERNS, DB_QUERIES
    assert "FATAL" in CRASH_PATTERNS
    assert "F-P0-2" in DB_QUERIES
    print("[PASS] test_config_constants_imported")


# === 7.4 证据 1：logcat ===

def test_start_logcat_success():
    """正常用例：start_logcat 清空成功"""
    memu = _make_memu([(0, "", "")])  # adb logcat -c 成功
    ec = EvidenceCollector(memu)
    assert ec.start_logcat() is True
    assert ec._logcat_start is not None
    # 验证调用了 logcat -c
    args = memu.adb.call_args[0]
    assert "logcat" in args
    assert "-c" in args
    print("[PASS] test_start_logcat_success")


def test_start_logcat_fail():
    """异常用例：start_logcat 清空失败"""
    memu = _make_memu([(1, "", "error")])  # adb logcat -c 失败
    ec = EvidenceCollector(memu)
    assert ec.start_logcat() is False
    assert ec._logcat_start is None
    print("[PASS] test_start_logcat_fail")


def test_stop_logcat_success():
    """正常用例：stop_logcat 成功返回文本"""
    memu = _make_memu([(0, "log line 1\nlog line 2", "")])
    ec = EvidenceCollector(memu)
    text = ec.stop_logcat()
    assert "log line 1" in text
    args = memu.adb.call_args[0]
    assert "-d" in args
    assert "time" in args
    print("[PASS] test_stop_logcat_success")


def test_stop_logcat_save_to_file():
    """正常用例：stop_logcat 保存到文件"""
    memu = _make_memu([(0, "log content", "")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        save_path = Path(tmp) / "logcat.txt"
        text = ec.stop_logcat(save_path)
        assert save_path.exists()
        assert save_path.read_text(encoding="utf-8") == "log content"
    print("[PASS] test_stop_logcat_save_to_file")


def test_stop_logcat_fail():
    """异常用例：stop_logcat 失败返回空字符串"""
    memu = _make_memu([(1, "", "adb error")])
    ec = EvidenceCollector(memu)
    assert ec.stop_logcat() == ""
    print("[PASS] test_stop_logcat_fail")


def test_slice_logcat_with_start():
    """正常用例：slice_logcat 按时间戳切片"""
    ec = EvidenceCollector(_make_memu())
    log_text = (
        "07-08 10:00:00 old line\n"
        "07-08 10:00:01 boundary line\n"
        "07-08 10:00:02 new line\n"
        "  continuation of new line\n"
    )
    sliced = ec.slice_logcat(log_text, start="07-08 10:00:01")
    assert "old line" not in sliced
    assert "boundary line" in sliced
    assert "new line" in sliced
    assert "continuation of new line" in sliced
    print("[PASS] test_slice_logcat_with_start")


def test_slice_logcat_no_start():
    """边界用例：无起始时间戳返回全部"""
    ec = EvidenceCollector(_make_memu())  # _logcat_start 为 None
    log_text = "07-08 10:00:00 line\n"
    assert ec.slice_logcat(log_text) == log_text
    print("[PASS] test_slice_logcat_no_start")


def test_slice_logcat_empty():
    """边界用例：空文本返回空"""
    ec = EvidenceCollector(_make_memu())
    assert ec.slice_logcat("") == ""
    print("[PASS] test_slice_logcat_empty")


def test_extract_anomalies_found():
    """正常用例：extract_anomalies 找到 FATAL 异常"""
    ec = EvidenceCollector(_make_memu())
    log_text = (
        "07-08 10:00:00 normal line\n"
        "07-08 10:00:01 E AndroidRuntime: FATAL EXCEPTION: main\n"
        "07-08 10:00:02 E AndroidRuntime: Process: io.legado.app.debug\n"
    )
    anomalies = ec.extract_anomalies(log_text)
    assert len(anomalies) >= 1
    assert anomalies[0]["type"] == "FATAL"
    assert "FATAL" in anomalies[0]["line"]
    print(f"[PASS] test_extract_anomalies_found (找到 {len(anomalies)} 个异常)")


def test_extract_anomalies_empty():
    """边界用例：空文本返回空列表"""
    ec = EvidenceCollector(_make_memu())
    assert ec.extract_anomalies("") == []
    print("[PASS] test_extract_anomalies_empty")


def test_extract_anomalies_multiple_types():
    """正常用例：extract_anomalies 识别多种异常类型"""
    ec = EvidenceCollector(_make_memu())
    log_text = (
        "07-08 10:00:01 FATAL EXCEPTION: main\n"
        "07-08 10:00:02 OutOfMemoryError\n"
        "07-08 10:00:03 NullPointerException\n"
    )
    anomalies = ec.extract_anomalies(log_text)
    types = {a["type"] for a in anomalies}
    assert "FATAL" in types
    assert "OOM" in types
    assert "Other" in types
    print(f"[PASS] test_extract_anomalies_multiple_types (类型: {types})")


# === 7.5 证据 2：ui_xml ===

def test_collect_ui_xml_success():
    """正常用例：collect_ui_xml 汇总 XML 文件"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        xml_dir = Path(tmp) / "xml"
        xml_dir.mkdir()
        (xml_dir / "step-01-before.xml").write_text("<root/>")
        (xml_dir / "step-01-after.xml").write_text("<root/>")
        result = ec.collect_ui_xml(tmp)
        assert result["collected"] is True
        assert result["count"] == 2
        assert len(result["files"]) == 2
    print("[PASS] test_collect_ui_xml_success")


def test_collect_ui_xml_no_dir():
    """异常用例：xml 目录不存在"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        result = ec.collect_ui_xml(tmp)
        assert result["collected"] is False
        assert "不存在" in result["error"]
    print("[PASS] test_collect_ui_xml_no_dir")


# === 7.6 证据 3：screenshot ===

def test_collect_screenshot_success():
    """正常用例：collect_screenshot 汇总截图"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        png_dir = Path(tmp) / "screenshot"
        png_dir.mkdir()
        (png_dir / "step-01-before.png").write_bytes(b"PNG")
        result = ec.collect_screenshot(tmp)
        assert result["collected"] is True
        assert result["count"] == 1
    print("[PASS] test_collect_screenshot_success")


def test_collect_screenshot_no_dir():
    """异常用例：screenshot 目录不存在"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        result = ec.collect_screenshot(tmp)
        assert result["collected"] is False
    print("[PASS] test_collect_screenshot_no_dir")


# === 7.7 证据 4：activity_stack ===

def test_collect_activity_stack_success():
    """正常用例：collect_activity_stack 成功"""
    memu = _make_memu([(0, "ACTIVITY MANAGER\nTASK stack", "")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_activity_stack(tmp)
        assert result["collected"] is True
        assert Path(result["path"]).exists()
        assert "ACTIVITY MANAGER" in Path(result["path"]).read_text(encoding="utf-8")
    print("[PASS] test_collect_activity_stack_success")


def test_collect_activity_stack_fail():
    """异常用例：dumpsys 失败"""
    memu = _make_memu([(1, "", "adb error")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_activity_stack(tmp)
        assert result["collected"] is False
        assert "dumpsys 失败" in result["error"]
    print("[PASS] test_collect_activity_stack_fail")


# === 7.8 证据 5：db_state ===

def test_collect_db_state_success():
    """正常用例：collect_db_state 成功收集 3 个模块"""
    # 3 个查询都成功
    adb_returns = [
        (0, "row1\nrow2", ""),  # F-P0-2
        (0, "row1", ""),        # F-P0-3
        (0, "row1\nrow2\nrow3", ""),  # F-P0-4
    ]
    memu = _make_memu(adb_returns)
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_db_state(tmp)
        assert result["collected"] is True
        assert "F-P0-2" in result["queries"]
        assert result["queries"]["F-P0-2"]["rows"] == 1  # 2个\n -> 1行... 实际是 count("\n")
        # 验证 db 目录下有文件
        db_dir = Path(tmp) / "db"
        assert (db_dir / "F-P0-2.txt").exists()
    print("[PASS] test_collect_db_state_success")


def test_collect_db_state_run_at_unavailable():
    """异常用例：run-at 不可用降级（not debuggable）"""
    memu = _make_memu([(1, "", "run-as: package is not debuggable")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_db_state(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "run_at_unavailable"
    print("[PASS] test_collect_db_state_run_at_unavailable")


def test_collect_db_state_run_at_not_found():
    """异常用例：run-at 命令不存在降级（MEmu 精简 Android，rc=127）"""
    memu = _make_memu([(127, "", "/system/bin/sh: run-at: not found")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_db_state(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "run_at_unavailable"
    print("[PASS] test_collect_db_state_run_at_not_found")


def test_collect_db_state_partial_fail():
    """边界用例：部分查询失败"""
    adb_returns = [
        (0, "row1", ""),        # F-P0-2 成功
        (1, "", "sqlite error"),  # F-P0-3 失败
        (0, "row1", ""),        # F-P0-4 成功
    ]
    memu = _make_memu(adb_returns)
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_db_state(tmp)
        assert result["collected"] is True  # 整体仍算收集成功
        assert "error" in result["queries"]["F-P0-3"]
    print("[PASS] test_collect_db_state_partial_fail")


# === 7.9 证据 6：prefs_state ===

def test_collect_prefs_state_success():
    """正常用例：collect_prefs_state 成功"""
    adb_returns = [
        (0, "config.xml\nbook.xml\n", ""),  # ls shared_prefs/
        (0, "<xml>config</xml>", ""),        # cat config.xml
        (0, "<xml>book</xml>", ""),          # cat book.xml
    ]
    memu = _make_memu(adb_returns)
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_prefs_state(tmp)
        assert result["collected"] is True
        assert result["count"] == 2
        prefs_dir = Path(tmp) / "prefs"
        assert (prefs_dir / "config.xml").exists()
    print("[PASS] test_collect_prefs_state_success")


def test_collect_prefs_state_run_at_unavailable():
    """异常用例：run-at 不可用降级（not debuggable）"""
    memu = _make_memu([(1, "", "not debuggable")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_prefs_state(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "run_at_unavailable"
    print("[PASS] test_collect_prefs_state_run_at_unavailable")


def test_collect_prefs_state_run_at_not_found():
    """异常用例：run-at 命令不存在降级（MEmu 精简 Android，rc=127）"""
    memu = _make_memu([(127, "", "/system/bin/sh: run-at: not found")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_prefs_state(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "run_at_unavailable"
    print("[PASS] test_collect_prefs_state_run_at_not_found")


def test_collect_prefs_state_no_xml_files():
    """边界用例：ls 成功但无 xml 文件"""
    memu = _make_memu([(0, "no xml here\n", "")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_prefs_state(tmp)
        assert result["collected"] is True
        assert result["count"] == 0
    print("[PASS] test_collect_prefs_state_no_xml_files")


# === 7.10 证据 7：web_api ===

@patch("ai_tests.lib.evidence_collector.subprocess.run")
def test_collect_web_api_success(mock_run):
    """正常用例：collect_web_api 成功"""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "response body\n---HTTP_CODE:200---"
    mock_run.return_value = mock_proc

    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        result = ec.collect_web_api(tmp, endpoints=["/books"])
        assert result["collected"] is True
        assert "/books" in result["endpoints"]
    print("[PASS] test_collect_web_api_success")


@patch("ai_tests.lib.evidence_collector.subprocess.run")
def test_collect_web_api_unavailable(mock_run):
    """异常用例：Web 服务未启动降级"""
    mock_proc = MagicMock()
    mock_proc.returncode = 7  # curl 连接失败
    mock_proc.stdout = "---HTTP_CODE:000---"
    mock_run.return_value = mock_proc

    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        result = ec.collect_web_api(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "web_api_unavailable"
    print("[PASS] test_collect_web_api_unavailable")


@patch("ai_tests.lib.evidence_collector.subprocess.run", side_effect=FileNotFoundError)
def test_collect_web_api_curl_missing(mock_run):
    """异常用例：curl 命令不存在降级"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        result = ec.collect_web_api(tmp)
        assert result["collected"] is False
        assert result["degraded"] is True
        assert result["degradation_reason"] == "curl_unavailable"
    print("[PASS] test_collect_web_api_curl_missing")


# === 7.11 证据 8：meminfo ===

def test_collect_meminfo_success():
    """正常用例：collect_meminfo 成功"""
    memu = _make_memu([(0, "TOTAL PSS: 100MB", "")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_meminfo(tmp)
        assert result["collected"] is True
        assert Path(result["path"]).exists()
    print("[PASS] test_collect_meminfo_success")


def test_collect_meminfo_fail():
    """异常用例：dumpsys meminfo 失败"""
    memu = _make_memu([(1, "", "error")])
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_meminfo(tmp)
        assert result["collected"] is False
    print("[PASS] test_collect_meminfo_fail")


# === 7.12 collect_all 并行收集 ===

def test_collect_all_no_logcat():
    """边界用例：未 start_logcat 时 logcat 证据为空"""
    # 5 个并行任务 + 0 个 logcat = 5 次 adb 调用
    # db_state(3 queries) + prefs_state(1 ls) + meminfo(1) + activity_stack(1) = 6 次 adb
    adb_returns = [
        # db_state: 3 queries
        (0, "row1", ""),
        (0, "row1", ""),
        (0, "row1", ""),
        # prefs_state: ls（无 xml）
        (0, "no xml\n", ""),
        # meminfo
        (0, "TOTAL PSS: 100MB", ""),
        # activity_stack
        (0, "ACTIVITY stack", ""),
    ]
    memu = _make_memu(adb_returns)
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        with patch("ai_tests.lib.evidence_collector.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 7
            mock_proc.stdout = "---HTTP_CODE:000---"
            mock_run.return_value = mock_proc
            result = ec.collect_all("TC-TEST-01", tmp)
        # logcat 未启动
        assert result["logcat"]["collected"] is False
        assert "未调用" in result["logcat"]["error"]
        # 其他证据应正常收集（web_api 降级）
        assert result["db_state"]["collected"] is True
        assert result["meminfo"]["collected"] is True
        assert result["activity_stack"]["collected"] is True
        assert result["web_api"]["degraded"] is True
        # ui_xml/screenshot 目录不存在
        assert result["ui_xml"]["collected"] is False
        assert result["screenshot"]["collected"] is False
        # 共 8 类证据
        assert len(result) == 8
    print("[PASS] test_collect_all_no_logcat")


def test_collect_all_with_logcat():
    """正常用例：collect_all 含 logcat（先 start_logcat）"""
    # start_logcat 1 次 + 5 并行任务
    adb_returns = [
        # start_logcat: adb logcat -c
        (0, "", ""),
        # db_state: 3 queries
        (0, "row1", ""),
        (0, "row1", ""),
        (0, "row1", ""),
        # prefs_state: ls（无 xml）
        (0, "no xml\n", ""),
        # meminfo
        (0, "TOTAL PSS", ""),
        # activity_stack
        (0, "ACTIVITY", ""),
        # stop_logcat: adb logcat -d（collect_all 末尾调用）
        (0, "07-08 10:00:00 FATAL EXCEPTION: main\n", ""),
    ]
    memu = _make_memu(adb_returns)
    ec = EvidenceCollector(memu)
    ec.start_logcat()
    with TemporaryDirectory() as tmp:
        with patch("ai_tests.lib.evidence_collector.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "200 OK\n---HTTP_CODE:200---"
            mock_run.return_value = mock_proc
            result = ec.collect_all("TC-TEST-02", tmp)
        # logcat 应已收集并提取异常
        assert result["logcat"]["collected"] is True
        assert result["logcat"]["anomaly_count"] >= 1
        # web_api 成功
        assert result["web_api"]["collected"] is True
    print("[PASS] test_collect_all_with_logcat")


def test_collect_all_parallel_exception_safe():
    """异常用例：并行任务异常不阻断 collect_all"""
    # 让 adb 抛异常
    memu = _make_memu()
    memu.adb = MagicMock(side_effect=RuntimeError("adb crashed"))
    ec = EvidenceCollector(memu)
    with TemporaryDirectory() as tmp:
        result = ec.collect_all("TC-TEST-03", tmp)
        # 所有 ADB 依赖证据都失败但不阻断
        assert result["db_state"]["collected"] is False
        assert result["meminfo"]["collected"] is False
        assert result["activity_stack"]["collected"] is False
        assert result["prefs_state"]["collected"] is False
        # ui_xml/screenshot 无 ADB 依赖，应正常执行（目录不存在）
        assert result["ui_xml"]["collected"] is False
        # 共 8 类证据
        assert len(result) == 8
    print("[PASS] test_collect_all_parallel_exception_safe")


def test_collect_all_evidence_types_complete():
    """正常用例：collect_all 返回 8 类证据类型齐全"""
    ec = EvidenceCollector(_make_memu())
    with TemporaryDirectory() as tmp:
        # mock 所有方法避免真实调用
        with patch.object(ec, "collect_db_state", return_value={"collected": True, "degraded": False}) as _, \
             patch.object(ec, "collect_prefs_state", return_value={"collected": True, "degraded": False}), \
             patch.object(ec, "collect_web_api", return_value={"collected": True, "degraded": False}), \
             patch.object(ec, "collect_meminfo", return_value={"collected": True, "degraded": False}), \
             patch.object(ec, "collect_activity_stack", return_value={"collected": True, "degraded": False}), \
             patch.object(ec, "collect_ui_xml", return_value={"collected": True, "degraded": False}), \
             patch.object(ec, "collect_screenshot", return_value={"collected": True, "degraded": False}):
            result = ec.collect_all("TC-TEST-04", tmp)
        expected_types = {
            "logcat", "ui_xml", "screenshot", "activity_stack",
            "db_state", "prefs_state", "web_api", "meminfo"
        }
        assert set(result.keys()) == expected_types
    print("[PASS] test_collect_all_evidence_types_complete")


# === _empty_evidence 辅助方法 ===

def test_empty_evidence_structure():
    """正常用例：_empty_evidence 返回结构正确"""
    ec = EvidenceCollector(_make_memu())
    empty = ec._empty_evidence("test_type", "test error")
    assert empty["type"] == "test_type"
    assert empty["collected"] is False
    assert empty["degraded"] is False
    assert empty["degradation_reason"] is None
    assert empty["path"] is None
    assert empty["error"] == "test error"
    print("[PASS] test_empty_evidence_structure")


# === 主入口 ===

if __name__ == "__main__":
    test_evidence_collector_instantiation()
    test_evidence_collector_none_memu()
    test_evidence_collector_custom_package()
    test_config_constants_imported()
    test_start_logcat_success()
    test_start_logcat_fail()
    test_stop_logcat_success()
    test_stop_logcat_save_to_file()
    test_stop_logcat_fail()
    test_slice_logcat_with_start()
    test_slice_logcat_no_start()
    test_slice_logcat_empty()
    test_extract_anomalies_found()
    test_extract_anomalies_empty()
    test_extract_anomalies_multiple_types()
    test_collect_ui_xml_success()
    test_collect_ui_xml_no_dir()
    test_collect_screenshot_success()
    test_collect_screenshot_no_dir()
    test_collect_activity_stack_success()
    test_collect_activity_stack_fail()
    test_collect_db_state_success()
    test_collect_db_state_run_at_unavailable()
    test_collect_db_state_run_at_not_found()
    test_collect_db_state_partial_fail()
    test_collect_prefs_state_success()
    test_collect_prefs_state_run_at_unavailable()
    test_collect_prefs_state_run_at_not_found()
    test_collect_prefs_state_no_xml_files()
    test_collect_web_api_success()
    test_collect_web_api_unavailable()
    test_collect_web_api_curl_missing()
    test_collect_meminfo_success()
    test_collect_meminfo_fail()
    test_collect_all_no_logcat()
    test_collect_all_with_logcat()
    test_collect_all_parallel_exception_safe()
    test_collect_all_evidence_types_complete()
    test_empty_evidence_structure()
    print("\n" + "=" * 60)
    print("全部 39 个测试通过 ✅")
    print("=" * 60)
