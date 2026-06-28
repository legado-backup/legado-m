#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断3个失败源：逐个调试，捕获stdout日志+stderr诊断日志"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# scripts -> legado-source-creator -> skills -> .trae -> project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR))))
_JAR_PATH = os.path.join(
    _PROJECT_ROOT,
    ".trae", "skills", "legado-source-creator", "tools", "legado-jvm",
    "build", "libs", "legado-jvm.jar"
)
_TEST_DATA = Path(_PROJECT_ROOT) / ".trae" / "skills" / "legado-source-creator" / "test-data"

# 3个失败源
FAIL_SOURCES = [
    ("normal-rss.json", "rss", "首页"),
    ("simple-rss.json", "rss", "首页"),
    ("js-rule.json", "book", "剑来"),
    ("paginated-novel.json", "book", "剑来"),
    ("jsonpath-rule.json", "book", "剑来"),
]


def diagnose_single(filename, source_type, key):
    """直接用JAR进程调试单个源，捕获stdout和stderr"""
    filepath = _TEST_DATA / filename
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        source_obj = json.loads(f.read())

    source_json = json.dumps(source_obj, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"诊断: {filename} (类型: {source_type}, 关键词: {key})")
    print(f"{'='*80}\n")

    # 构造JAR命令
    cmd_field = "debugRssSource" if source_type == "rss" else "debugBookSource"
    command = json.dumps({
        "cmd": cmd_field,
        "sourceJson": source_json,
        "key": key,
    }, ensure_ascii=False)

    # 启动JAR进程
    print(f"启动JAR: {_JAR_PATH}")
    proc = subprocess.Popen(
        ["java", "-jar", _JAR_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.path.dirname(_JAR_PATH),
    )

    # 读取启动信息
    startup_line = proc.stdout.readline()
    print(f"JAR启动: {startup_line.strip()[:100]}")

    # 发送调试命令
    print(f"发送命令: {cmd_field}")
    proc.stdin.write(command + "\n")
    proc.stdin.flush()

    # 读取响应（流式日志 + 最终结果）
    stdout_lines = []
    stderr_lines = []
    start_time = time.time()
    timeout = 60  # 60秒超时

    import threading

    def read_stderr():
        for line in proc.stderr:
            stderr_lines.append(line.rstrip())

    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()

    # 读取stdout
    result_received = False
    while time.time() - start_time < timeout:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        stdout_lines.append(line)

        try:
            msg = json.loads(line)
            msg_type = msg.get("type", "")

            if msg_type == "log":
                state = msg.get("state", 1)
                msg_text = msg.get("msg", "")
                if msg_text:
                    print(f"  [日志 state={state}] {msg_text[:200]}")
            elif msg_type == "error":
                print(f"  [错误] 阶段={msg.get('failedStage', '')} 错误={msg.get('msg', '')[:200]}")
                if msg.get("stackTrace"):
                    print(f"  [堆栈] {msg['stackTrace'][:300]}")
            elif msg_type == "result":
                success = msg.get("success", False)
                print(f"  [结果] {'成功' if success else '失败'}: {msg.get('msg', '')}")
                summary = msg.get("summary", {})
                if summary:
                    print(f"  [摘要] {json.dumps(summary, ensure_ascii=False)[:200]}")
                result_received = True
                break
        except json.JSONDecodeError:
            print(f"  [原始] {line[:200]}")

    elapsed = time.time() - start_time

    if not result_received:
        print(f"  [超时] {timeout}秒内未收到结果")

    # 等待stderr线程完成
    stderr_thread.join(timeout=2)

    # 打印stderr诊断日志
    print(f"\n--- stderr诊断日志 ({len(stderr_lines)}行) ---")
    for line in stderr_lines:
        if "[DIAG]" in line:
            print(f"  {line[:250]}")

    # 关闭进程
    try:
        proc.stdin.write(json.dumps({"cmd": "shutdown"}) + "\n")
        proc.stdin.flush()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    print(f"\n耗时: {elapsed:.2f}s")
    return result_received


def main():
    print(f"JAR路径: {_JAR_PATH}")
    print(f"测试数据: {_TEST_DATA}")

    if not os.path.exists(_JAR_PATH):
        print(f"错误: JAR文件不存在: {_JAR_PATH}")
        sys.exit(1)

    results = {}
    for filename, source_type, key in FAIL_SOURCES:
        success = diagnose_single(filename, source_type, key)
        results[filename] = success

    print(f"\n{'='*80}")
    print("诊断总结")
    print(f"{'='*80}")
    for filename, success in results.items():
        status = "✅成功" if success else "❌失败"
        print(f"  {status} {filename}")


if __name__ == "__main__":
    main()
