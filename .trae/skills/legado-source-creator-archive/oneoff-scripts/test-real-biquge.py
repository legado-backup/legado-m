#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单独测试real-biquge.json，查看完整日志"""
import json
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from legado_client.client.rule_engine_client import RuleEngineClient


def test():
    filepath = ".trae/skills/legado-source-creator/test-data/real-biquge.json"
    with open(filepath, "r", encoding="utf-8") as f:
        source_obj = json.loads(f.read())
    source_json = json.dumps(source_obj, ensure_ascii=False)

    with RuleEngineClient(timeout=60) as client:
        print(f"JVM已启动: {client.version}\n")

        all_logs = []
        def on_log(state, msg, html):
            all_logs.append(f"[state={state}] {msg}")
            print(f"LOG: [state={state}] {msg[:300] if msg else ''}")

        def on_error(msg, stack_trace, failed_stage):
            print(f"ERROR: {msg}")
            print(f"  阶段: {failed_stage}")
            if stack_trace:
                print(f"  堆栈: {stack_trace[:500]}")

        def on_result(success, summary):
            print(f"\nRESULT: success={success}")
            print(f"  summary: {summary}")

        print("发送 debugBookSource 命令...")
        result = client.debug_book_source(
            source_json, "测试",
            on_log=on_log,
            on_error=on_error,
            on_result=on_result
        )
        print(f"\n返回值: {result}")
        print(f"\n总日志数: {len(all_logs)}")


if __name__ == "__main__":
    test()
