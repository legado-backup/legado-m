#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试脚本：只测试关键的书源和RSS源文件"""
import json
import os
import sys
import time
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from legado_client.client.rule_engine_client import RuleEngineClient

# 要测试的源文件（按顺序，避免JVM崩溃）
# RSS源放前面，避免JVM连续测试后状态异常
TEST_FILES = [
    "normal-rss.json",
    "simple-rss.json",
    "normal-book.json",
    "simple-biquge.json",
    "css-rule.json",
    "xpath-rule.json",
    "mixed-rule.json",
    "regex-rule.json",
    "new-site.json",
    "encrypted-novel.json",
    "login-required.json",
    "cf-protected.json",
    "cookie-site.json",
    "encrypted-rss.json",
    "paginated-novel.json",
    "jsonpath-rule.json",
    "js-rule.json",
]

# 特殊场景源（预期失败）
SPECIAL_TESTS = {
    "login-required.json", "cf-protected.json", "cookie-site.json",
    "encrypted-novel.json", "encrypted-rss.json",
}


def detect_type(source_obj):
    if "bookSourceUrl" in source_obj:
        return "book"
    if "sourceUrl" in source_obj:
        return "rss"
    return "book"


def get_test_key(source_obj, source_type):
    if source_type == "book":
        return "剑来"
    sort_url = source_obj.get("sortUrl", "")
    if sort_url and "::" in sort_url:
        return sort_url.split("::")[0].split("\n")[0].strip()
    return "test"


def run_single_test(client, filepath, timeout=30):
    filename = os.path.basename(filepath)
    result = {
        "filename": filename,
        "sourceName": "",
        "sourceType": "",
        "success": False,
        "errorStage": "",
        "errorMessage": "",
        "isSpecialTest": filename in SPECIAL_TESTS,
        "elapsed": 0,
        "logs": [],
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        result["errorMessage"] = f"读取文件失败: {e}"
        return result

    try:
        source_obj = json.loads(raw)
        if isinstance(source_obj, list):
            source_obj = source_obj[0] if source_obj else {}
    except json.JSONDecodeError as e:
        result["errorMessage"] = f"JSON解析失败: {e}"
        return result

    source_type = detect_type(source_obj)
    source_name = (source_obj.get("bookSourceName") or source_obj.get("sourceName") or filename)
    key = get_test_key(source_obj, source_type)
    source_json = json.dumps(source_obj, ensure_ascii=False)

    result["sourceName"] = source_name
    result["sourceType"] = source_type

    start_time = time.time()
    logs = []
    test_done = [False]  # 用列表实现可变闭包变量

    def on_log(state, msg, html):
        logs.append({"state": state, "msg": (msg or "")[:300]})

    def on_error(msg, stack_trace, failed_stage):
        result["errorMessage"] = (msg or "")[:500]
        result["errorStage"] = failed_stage or ""

    def on_result(success, summary):
        result["success"] = success

    def do_test():
        try:
            if source_type == "book":
                client.debug_book_source(source_json, key, on_log=on_log, on_error=on_error, on_result=on_result)
            else:
                client.debug_rss_source(source_json, key, on_log=on_log, on_error=on_error, on_result=on_result)
        except Exception as e:
            result["errorMessage"] = f"客户端异常: {e}"
        finally:
            test_done[0] = True

    import threading
    t = threading.Thread(target=do_test, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if not test_done[0]:
        result["errorMessage"] = f"测试超时（{timeout}秒）"
        result["errorStage"] = "timeout"

    result["elapsed"] = round(time.time() - start_time, 2)
    result["logs"] = logs[:15]
    return result


def main():
    test_data_dir = Path(".trae/skills/legado-source-creator/test-data")
    
    print(f"快速测试: 共 {len(TEST_FILES)} 个源文件")
    print(f"{'='*80}\n")

    all_results = []
    start_time = time.time()

    client = RuleEngineClient(timeout=60)
    client.start()

    try:
        ping = client.ping()
        if not ping.get("ok"):
            print(f"错误: JVM ping 失败: {ping}")
            sys.exit(3)
        print(f"JVM 服务端已启动\n")

        for i, filename in enumerate(TEST_FILES, 1):
            filepath = test_data_dir / filename
            if not filepath.exists():
                print(f"[{i}/{len(TEST_FILES)}] {filename} - 文件不存在")
                continue

            print(f"[{i}/{len(TEST_FILES)}] 测试: {filename}")

            # 检测 JVM 进程是否存活
            if not client.is_alive():
                print(f"  ⚠️ JVM 崩溃，重启...")
                try:
                    client.shutdown()
                except Exception:
                    pass
                client = RuleEngineClient(timeout=60)
                client.start()
                ping = client.ping()
                if not ping.get("ok"):
                    print(f"  ❌ JVM 重启失败")
                    continue
                print(f"  ✅ JVM 重启成功")

            result = run_single_test(client, str(filepath))

            # 测试超时后重启JVM，避免后续测试受影响
            if result["errorStage"] == "timeout":
                print(f"  ⚠️ 测试超时，重启JVM...")
                try:
                    client.shutdown()
                except Exception:
                    pass
                client = RuleEngineClient(timeout=60)
                client.start()
                ping = client.ping()
                if not ping.get("ok"):
                    print(f"  ❌ JVM 重启失败")
                    continue
                print(f"  ✅ JVM 重启成功")

            if result["success"]:
                status = "✅ 成功"
            elif result["isSpecialTest"]:
                status = "⚠️ 预期失败"
            else:
                status = "❌ 失败"

            print(f"  {status} | 耗时: {result['elapsed']}s")
            if not result["success"] and result["errorMessage"]:
                print(f"  阶段: {result['errorStage']} | 错误: {result['errorMessage'][:200]}")
            
            # 打印关键日志
            for log in result["logs"][:8]:
                if log["msg"]:
                    print(f"    {log['msg'][:150]}")
            print()

            all_results.append(result)

    except Exception as e:
        print(f"测试错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client.shutdown()
        except Exception:
            pass

    elapsed = round(time.time() - start_time, 2)

    # 统计
    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    special_total = sum(1 for r in all_results if r["isSpecialTest"])
    special_failed = sum(1 for r in all_results if r["isSpecialTest"] and not r["success"])
    positive_total = total - special_total
    positive_success = sum(1 for r in all_results if r["success"] and not r["isSpecialTest"])

    print(f"\n{'='*80}")
    print(f"快速测试报告")
    print(f"{'='*80}")
    print(f"总数: {total}")
    print(f"总耗时: {elapsed}s")
    print(f"\n成功统计:")
    print(f"  总成功: {success}/{total} ({success/total*100:.1f}%)")
    print(f"  正向测试成功: {positive_success}/{positive_total} ({positive_success/positive_total*100 if positive_total else 0:.1f}%)")
    print(f"  特殊场景预期失败: {special_failed}/{special_total} ({special_failed/special_total*100 if special_total else 0:.1f}%)")

    print(f"\n详细结果:")
    for r in all_results:
        if r["success"]:
            status = "✅"
        elif r["isSpecialTest"]:
            status = "⚠️"
        else:
            status = "❌"
        print(f"  {status} {r['filename']} ({r['sourceType']}) - {r['sourceName']}")
        if not r["success"] and r["errorMessage"]:
            print(f"      阶段: {r['errorStage']} | 错误: {r['errorMessage'][:120]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
