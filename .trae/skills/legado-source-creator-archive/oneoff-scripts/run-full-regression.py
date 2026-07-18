#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量回归测试脚本：遍历 test-data/ 目录所有源，运行 JAR 仿真测试。

用法:
    python run-full-regression.py [--timeout 60] [--output report.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 添加 scripts/ 目录到路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from legado_client.client.rule_engine_client import RuleEngineClient
from legado_client.utils.config import config


# 负面测试源（预期失败）
NEGATIVE_TESTS = {
    "broken-field.json", "broken-jsonpath.json", "broken-selector.json",
    "broken-syntax.json", "broken-url.json",
    "broken-decrypt.json", "broken-rule-toc.json",
    "empty-rules.json", "invalid-json.json", "missing-fields.json",
}

# 特殊场景源（预期需要用户介入或WebView）
SPECIAL_TESTS = {
    "login-required.json", "cf-protected.json", "cookie-site.json",
    "encrypted-novel.json", "encrypted-rss.json",
}


def detect_type(source_obj: dict) -> str:
    """检测源类型"""
    if "bookSourceUrl" in source_obj:
        return "book"
    if "sourceUrl" in source_obj and "ruleArticles" in source_obj:
        return "rss"
    if "sourceUrl" in source_obj:
        return "rss"
    if "ruleSearch" in source_obj:
        return "book"
    return "book"


def get_test_key(source_obj: dict, source_type: str, filename: str) -> str:
    """获取测试关键词"""
    if source_type == "book":
        return "测试"
    # RSS 源：从 sortUrl 中提取第一个分类名
    sort_url = source_obj.get("sortUrl", "")
    if sort_url and "::" in sort_url:
        return sort_url.split("::")[0].split("\n")[0].strip()
    return "test"


def classify_failure(result: dict, source_name: str, filename: str,
                     error_msg: str, error_stage: str) -> str:
    """分类失败原因

    Returns:
        'simulator' - 仿真端问题（JAR bug）
        'source_rule' - 源规则问题
        'website' - 网站问题（域名失效/反爬）
        'expected' - 预期失败（负面测试）
        'network' - 网络问题（虚假域名）
    """
    # 负面测试源预期失败
    if filename in NEGATIVE_TESTS:
        return "expected"

    combined = f"{error_msg} {error_stage}".lower()

    # 网络问题（虚假域名/DNS失败/连接失败）
    if any(kw in combined for kw in ('unknownhostexception', 'unknown host',
                                       'connectexception', 'connection refused',
                                       'sockettimeoutexception', 'timeout',
                                       'connect timed out', 'unreachable',
                                       'dns', 'name resolution',
                                       'cannot assign requested address',
                                       'bindexception', 'failed to connect',
                                       '网络请求')):
        return "network"

    # 仿真端问题特征
    if any(kw in combined for kw in ('nullpointerexception', 'classcastexception',
                                       'illegalargumentexception', 'illegalstateexception',
                                       'nosuchmethod', 'nosuchfield',
                                       'jsonparse', 'jsonsyntax',
                                       'unsupportedoperation', 'notimplemented',
                                       'undefined', 'is not a function')):
        return "simulator"

    # 源规则问题特征
    if any(kw in combined for kw in ('rule', 'selector', 'xpath', 'jsonpath',
                                       'css', 'parse', 'empty', 'not found',
                                       'no match', '规则', '选择器',
                                       'http 404', 'http 403', 'http 500')):
        return "source_rule"

    # 网站问题
    if any(kw in combined for kw in ('cloudflare', 'captcha', 'login',
                                       'redirect', '登录', '验证码')):
        return "website"

    # 如果有日志但无错误信息，且rawResult显示stages，可能是仿真端问题（如内容为空）
    if not error_msg and result.get("rawResult"):
        raw = result["rawResult"]
        if isinstance(raw, dict):
            content_length = raw.get("contentLength", -1)
            if content_length == 0:
                return "simulator"  # 内容为空可能是仿真端解析问题

    return "unknown"


def run_single_test(client: RuleEngineClient, filepath: str,
                    timeout: int) -> dict:
    """运行单个源的测试

    Returns:
        dict: 测试结果
    """
    filename = os.path.basename(filepath)
    result = {
        "filename": filename,
        "filepath": filepath,
        "sourceName": "",
        "sourceType": "",
        "success": False,
        "needsWebView": False,
        "needsUserIntervention": False,
        "errorStage": "",
        "errorMessage": "",
        "errorClass": "",
        "failureCategory": "",
        "isNegativeTest": filename in NEGATIVE_TESTS,
        "isSpecialTest": filename in SPECIAL_TESTS,
        "elapsed": 0,
        "logs": [],
        "rawResult": None,
    }

    # 读取源文件
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        result["errorMessage"] = f"读取文件失败: {e}"
        result["failureCategory"] = "simulator"
        return result

    # 解析 JSON
    try:
        source_obj = json.loads(raw)
        if isinstance(source_obj, list):
            source_obj = source_obj[0] if source_obj else {}
    except json.JSONDecodeError as e:
        # invalid-json.json 预期会到这里
        result["errorMessage"] = f"JSON解析失败: {e}"
        result["failureCategory"] = "expected" if filename == "invalid-json.json" else "source_rule"
        result["elapsed"] = 0
        return result

    source_type = detect_type(source_obj)
    source_name = (source_obj.get("bookSourceName") or source_obj.get("sourceName")
                   or filename)
    key = get_test_key(source_obj, source_type, filename)
    source_json = json.dumps(source_obj, ensure_ascii=False)

    result["sourceName"] = source_name
    result["sourceType"] = source_type

    # 运行测试
    start_time = time.time()
    logs = []

    def on_log(state, msg, html):
        logs.append({"state": state, "msg": msg[:500] if msg else ""})

    def on_error(msg, stack_trace, failed_stage):
        result["errorMessage"] = (msg or "")[:1000]
        result["errorStage"] = failed_stage or ""
        if stack_trace:
            # 提取错误类名
            lines = stack_trace.split("\n")
            for line in lines:
                if "Exception" in line or "Error" in line:
                    result["errorClass"] = line.strip()[:200]
                    break

    def on_result(success, summary):
        result["success"] = success
        result["rawResult"] = summary

    # 使用线程实现超时控制
    test_exception = [None]
    test_return_value = [None]

    def run_test():
        try:
            if source_type == "book":
                ret = client.debug_book_source(
                    source_json, key,
                    on_log=on_log,
                    on_error=on_error,
                    on_result=on_result
                )
                test_return_value[0] = ret
            else:
                ret = client.debug_rss_source(
                    source_json, key,
                    on_log=on_log,
                    on_error=on_error,
                    on_result=on_result
                )
                test_return_value[0] = ret
        except OSError as e:
            test_exception[0] = e
        except Exception as e:
            test_exception[0] = e

    test_thread = threading.Thread(target=run_test, daemon=True)
    test_thread.start()
    # 单测试超时：使用 args.timeout 的 0.8 倍，留出余量
    test_timeout = max(30, int(timeout * 0.8))
    test_thread.join(timeout=test_timeout)

    if test_thread.is_alive():
        # 测试超时，JVM 可能卡在 HTTP 请求上
        result["errorMessage"] = f"测试超时(>{test_timeout}s)，JVM 可能卡在网络请求"
        result["errorStage"] = "timeout"
        result["errorClass"] = "TimeoutError"
        # 注意：线程仍在运行（daemon），JVM 进程可能需要重启
    elif test_exception[0] is not None:
        e = test_exception[0]
        if isinstance(e, OSError):
            result["errorMessage"] = f"管道异常(JVM可能崩溃): {e}"
            result["errorClass"] = e.__class__.__name__
            result["errorStage"] = "client"
        else:
            result["errorMessage"] = f"客户端异常: {e}"
            result["errorClass"] = e.__class__.__name__
    else:
        # 检查返回值，如果返回了错误dict但没有触发回调，记录错误
        ret = test_return_value[0]
        if isinstance(ret, dict) and ret.get("ok") is False and not result["errorMessage"]:
            result["errorMessage"] = f"JVM返回错误: {ret.get('error', 'unknown')}"
            result["errorStage"] = "client"
            result["errorClass"] = "ServerError"

    result["elapsed"] = round(time.time() - start_time, 2)
    result["logs"] = logs[:20]  # 限制日志数量

    # 分类失败原因
    if not result["success"]:
        result["failureCategory"] = classify_failure(
            result, source_name, filename,
            result["errorMessage"], result["errorStage"]
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="全量回归测试")
    parser.add_argument("--timeout", type=int, default=60,
                        help="JVM 服务端超时秒数（默认: 60）")
    parser.add_argument("--output", default="output/test-sources/regression-report.json",
                        help="报告输出路径")
    parser.add_argument("--test-data-dir",
                        default=".trae/skills/legado-source-creator/test-data",
                        help="测试数据目录")
    args = parser.parse_args()

    test_data_dir = Path(args.test_data_dir)
    if not test_data_dir.exists():
        print(f"错误: 测试数据目录不存在: {test_data_dir}")
        sys.exit(2)

    # 收集所有 JSON 文件
    source_files = sorted(test_data_dir.glob("*.json"))
    # 包含 negative-test 子目录
    neg_dir = test_data_dir / "negative-test"
    if neg_dir.exists():
        source_files.extend(sorted(neg_dir.glob("*.json")))

    print(f"全量回归测试: 共 {len(source_files)} 个源文件")
    print(f"超时: {args.timeout}s")
    print(f"{'='*80}\n")

    all_results = []
    start_time = time.time()

    # 使用 context manager 管理 JVM 生命周期，但需要在崩溃时重启
    client = RuleEngineClient(timeout=args.timeout)
    client.start()

    try:
        # 验证 ping
        ping = client.ping()
        if not ping.get("ok"):
            print(f"错误: JVM ping 失败: {ping}")
            sys.exit(3)
        print(f"JVM 服务端已启动: version={client.version}, modules={client.modules}\n")

        for i, filepath in enumerate(source_files, 1):
            filename = filepath.name
            print(f"[{i}/{len(source_files)}] 测试: {filename}")

            # 检测 JVM 进程是否存活，不存活则重启
            if not client.is_alive():
                print(f"  ⚠️ JVM 进程已崩溃，尝试重启...")
                try:
                    client.shutdown()
                except Exception:
                    pass
                try:
                    client = RuleEngineClient(timeout=args.timeout)
                    client.start()
                    ping = client.ping()
                    if not ping.get("ok"):
                        print(f"  ❌ JVM 重启失败: {ping}")
                        result = {
                            "filename": filename,
                            "filepath": str(filepath),
                            "sourceName": filename,
                            "sourceType": "",
                            "success": False,
                            "errorMessage": "JVM 重启失败",
                            "failureCategory": "simulator",
                            "isNegativeTest": filename in NEGATIVE_TESTS,
                            "isSpecialTest": filename in SPECIAL_TESTS,
                            "elapsed": 0,
                            "logs": [],
                        }
                        all_results.append(result)
                        continue
                    print(f"  ✅ JVM 重启成功")
                except Exception as e:
                    print(f"  ❌ JVM 重启异常: {e}")
                    result = {
                        "filename": filename,
                        "filepath": str(filepath),
                        "sourceName": filename,
                        "sourceType": "",
                        "success": False,
                        "errorMessage": f"JVM 重启异常: {e}",
                        "failureCategory": "simulator",
                        "isNegativeTest": filename in NEGATIVE_TESTS,
                        "isSpecialTest": filename in SPECIAL_TESTS,
                        "elapsed": 0,
                        "logs": [],
                    }
                    all_results.append(result)
                    continue

            result = run_single_test(client, str(filepath), args.timeout)

            # 检测测试是否超时，超时后强制重启 JVM
            if result.get("errorStage") == "timeout":
                print(f"  ⚠️ 测试超时，强制重启 JVM 进程...")
                try:
                    client.shutdown()
                except Exception:
                    pass
                try:
                    client = RuleEngineClient(timeout=args.timeout)
                    client.start()
                    ping = client.ping()
                    if ping.get("ok"):
                        print(f"  ✅ JVM 重启成功")
                    else:
                        print(f"  ❌ JVM 重启失败: {ping}")
                except Exception as e:
                    print(f"  ❌ JVM 重启异常: {e}")

            # 标记状态
            if result["success"]:
                status = "✅ 成功"
            elif result["isNegativeTest"]:
                status = "⚠️ 预期失败"
            elif result["failureCategory"] == "network":
                status = "🌐 网络问题"
            elif result["failureCategory"] == "simulator":
                status = "🔧 仿真端问题"
            elif result["failureCategory"] == "source_rule":
                status = "📝 源规则问题"
            elif result["failureCategory"] == "website":
                status = "🔒 网站问题"
            else:
                status = "❌ 失败"

            print(f"  {status} | 耗时: {result['elapsed']}s | 分类: {result['failureCategory']}")
            if not result["success"] and result["errorMessage"]:
                err = result["errorMessage"][:200]
                print(f"  错误: {err}")
            if result["errorStage"]:
                print(f"  阶段: {result['errorStage']}")
            print()

            all_results.append(result)

    except FileNotFoundError as e:
        print(f"[JAR 不可用] {e}")
        sys.exit(3)
    except Exception as e:
        print(f"测试错误: {e}")
        traceback.print_exc()
    finally:
        try:
            client.shutdown()
        except Exception:
            pass

    elapsed = round(time.time() - start_time, 2)

    # 生成统计报告
    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    negative_total = sum(1 for r in all_results if r["isNegativeTest"])
    negative_failed = sum(1 for r in all_results if r["isNegativeTest"] and not r["success"])
    positive_total = total - negative_total
    positive_success = sum(1 for r in all_results if r["success"] and not r["isNegativeTest"])

    # 失败分类统计
    failure_categories = {}
    for r in all_results:
        if not r["success"]:
            cat = r["failureCategory"]
            failure_categories[cat] = failure_categories.get(cat, 0) + 1

    print(f"\n{'='*80}")
    print(f"全量回归测试报告")
    print(f"{'='*80}")
    print(f"总数: {total}")
    print(f"总耗时: {elapsed}s")
    print(f"\n成功统计:")
    print(f"  总成功: {success}/{total} ({success/total*100:.1f}%)")
    print(f"  正向测试成功: {positive_success}/{positive_total} ({positive_success/positive_total*100 if positive_total else 0:.1f}%)")
    print(f"  负面测试预期失败: {negative_failed}/{negative_total} ({negative_failed/negative_total*100 if negative_total else 0:.1f}%)")

    print(f"\n失败分类统计:")
    for cat, count in sorted(failure_categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print(f"\n详细结果:")
    for r in all_results:
        if r["success"]:
            status = "✅"
        elif r["isNegativeTest"]:
            status = "⚠️"
        else:
            status = "❌"
        print(f"  {status} {r['filename']} ({r['sourceType']}) - {r['failureCategory'] or 'success'}")
        if not r["success"] and r["errorMessage"]:
            print(f"      阶段: {r['errorStage']} | 错误: {r['errorMessage'][:150]}")

    # 保存详细报告
    report = {
        "total": total,
        "success": success,
        "negative_total": negative_total,
        "negative_failed": negative_failed,
        "positive_total": positive_total,
        "positive_success": positive_success,
        "failure_categories": failure_categories,
        "elapsed_seconds": elapsed,
        "results": all_results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {output_path}")

    # 退出码
    sys.exit(0 if success == total else 1)


if __name__ == "__main__":
    main()
