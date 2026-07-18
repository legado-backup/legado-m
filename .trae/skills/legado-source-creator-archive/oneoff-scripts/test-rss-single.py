#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单独测试RSS源，查看原始响应"""
import json
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from legado_client.client.rule_engine_client import RuleEngineClient


def test_rss(filepath: str, key: str = "最新"):
    """测试单个RSS源"""
    print(f"\n{'='*60}")
    print(f"测试: {filepath}")
    print(f"Key: {key}")
    print(f"{'='*60}")

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    source_obj = json.loads(raw)
    source_json = json.dumps(source_obj, ensure_ascii=False)

    with RuleEngineClient(timeout=30) as client:
        print(f"JVM已启动: {client.version}")

        logs = []
        def on_log(state, msg, html):
            logs.append(f"[state={state}] {msg}")
            print(f"LOG: [state={state}] {msg[:200] if msg else ''}")

        def on_error(msg, stack_trace, failed_stage):
            print(f"ERROR: {msg}")
            print(f"  阶段: {failed_stage}")
            if stack_trace:
                print(f"  堆栈: {stack_trace[:300]}")

        def on_result(success, summary):
            print(f"RESULT: success={success}")
            print(f"  summary: {summary}")

        print(f"发送 debugRssSource 命令...")
        result = client.debug_rss_source(
            source_json, key,
            on_log=on_log,
            on_error=on_error,
            on_result=on_result
        )
        print(f"\n返回值: {result}")
        print(f"日志数: {len(logs)}")


if __name__ == "__main__":
    test_data_dir = ".trae/skills/legado-source-creator/test-data"
    # 测试 normal-rss.json
    test_rss(os.path.join(test_data_dir, "normal-rss.json"), "最新")
    # 测试 simple-rss.json
    test_rss(os.path.join(test_data_dir, "simple-rss.json"), "首页")
