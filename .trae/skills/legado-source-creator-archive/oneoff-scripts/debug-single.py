#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细调试单个源文件，打印所有日志"""
import json
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from legado_client.client.rule_engine_client import RuleEngineClient


def main():
    if len(sys.argv) < 2:
        print("用法: python debug-single.py <源文件名>")
        sys.exit(1)

    filename = sys.argv[1]
    test_data_dir = Path(".trae/skills/legado-source-creator/test-data")
    filepath = test_data_dir / filename

    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        source_obj = json.loads(f.read())

    source_type = "book" if "bookSourceUrl" in source_obj else "rss"
    key = "剑来" if source_type == "book" else "首页"
    if source_type == "rss":
        sort_url = source_obj.get("sortUrl", "")
        if "::" in sort_url:
            key = sort_url.split("::")[0].split("\n")[0].strip()

    source_json = json.dumps(source_obj, ensure_ascii=False)
    print(f"调试: {filename} (类型: {source_type}, 关键词: {key})")
    print(f"{'='*80}\n")

    client = RuleEngineClient(timeout=60)
    client.start()

    try:
        ping = client.ping()
        if not ping.get("ok"):
            print(f"JVM ping 失败: {ping}")
            sys.exit(3)
        print("JVM 服务端已启动\n")

        all_logs = []

        def on_log(state, msg, html):
            all_logs.append({"state": state, "msg": msg or "", "html_len": len(html) if html else 0})
            print(f"[{state}] {msg or ''}")

        def on_error(msg, stack_trace, failed_stage):
            print(f"\n❌ 错误阶段: {failed_stage}")
            print(f"错误信息: {msg}")
            if stack_trace:
                print(f"堆栈: {stack_trace[:500]}")

        def on_result(success, summary):
            print(f"\n{'✅ 成功' if success else '❌ 失败'}: {summary}")

        if source_type == "book":
            client.debug_book_source(source_json, key, on_log=on_log, on_error=on_error, on_result=on_result)
        else:
            client.debug_rss_source(source_json, key, on_log=on_log, on_error=on_error, on_result=on_result)

        print(f"\n{'='*80}")
        print(f"总日志数: {len(all_logs)}")

    finally:
        try:
            client.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
