#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批处理运行器：从 debug-source.py 提取的批处理逻辑。

JSON去重：读取源文件时解析一次 obj，后续传递对象。
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from typing import List

from legado_client.client.rule_engine_client import RuleEngineClient
from legado_client.client.debug_result import DebugResultData
from legado_client.utils.config import config
from legado_client.utils.file_utils import load_source_object


def _detect_type_from_obj(source_obj: dict) -> str:
    """从源对象字典检测源类型（JSON去重：不再 json.loads）。

    检测优先级：
    1. bookSourceUrl（书源特有字段）→ book
    2. sourceUrl + ruleArticles（订阅源特有组合）→ rss
    3. sourceUrl（订阅源特有字段）→ rss
    4. ruleSearch（两者都有，但书源更常见）→ book
    修复: 新订阅源同时有 ruleSearch 和 sourceUrl，先检查 sourceUrl 避免误判为书源
    """
    if "bookSourceUrl" in source_obj:
        return "book"
    if "sourceUrl" in source_obj and "ruleArticles" in source_obj:
        return "rss"
    if "sourceUrl" in source_obj:
        return "rss"
    if "ruleSearch" in source_obj:
        return "book"
    return "book"


def run_batch(args) -> None:
    """批处理模式：一次处理多个源文件。

    JSON去重：读取源文件时解析一次 obj，后续传递对象。
    """
    # 展开 glob 模式或读取目录
    if os.path.isdir(args.batch):
        pattern = os.path.join(args.batch, "*.json")
        source_files = sorted(glob.glob(pattern))
    else:
        source_files = sorted(glob.glob(args.batch))

    if not source_files:
        print(f"错误: 未找到匹配的源文件: {args.batch}")
        sys.exit(2)

    print(f"批处理模式: 共 {len(source_files)} 个源文件")

    # 读取所有源文件，组装 batch 命令
    sources: List[dict] = []
    for filepath in source_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
            # JSON去重：解析一次 obj
            obj = load_source_object(raw)
            source_json = json.dumps(obj, ensure_ascii=False)

            # 检测源类型（JSON去重：直接用 obj）
            source_type = _detect_type_from_obj(obj)

            # 提取默认 key
            if source_type == "book":
                key = obj.get("bookSourceName", "")
            else:
                # RSS 源：从 sortUrl 中提取第一个分类名作为 key
                sort_url = obj.get("sortUrl", "")
                key = ""
                if sort_url and "::" in sort_url:
                    key = sort_url.split("::")[0].split("\n")[0].strip()
                if not key:
                    key = obj.get("sourceName", "test")

            sources.append({
                "sourceJson": source_json,
                "key": key,
                "sourceName": obj.get("sourceName") or obj.get("bookSourceName") or os.path.basename(filepath),
                "sourceType": source_type,
                "filePath": filepath
            })
        except Exception as e:
            print(f"  跳过 {filepath}: {e}")

    if not sources:
        print("错误: 没有有效的源文件")
        sys.exit(2)

    # 检测所有源是否同类型（batch 命令需要统一的 sourceType）
    source_types = set(s["sourceType"] for s in sources)
    if len(source_types) > 1:
        print(f"警告: 源类型不一致 ({source_types})，将分批处理")

    print(f"\n{'='*60}")
    print(f"开始批处理调试（{len(sources)} 个源）")
    print(f"{'='*60}\n")

    start_time = time.time()

    try:
        with RuleEngineClient(timeout=args.timeout) as client:
            # 按源类型分组处理
            results_all: List[dict] = []
            for st in source_types:
                batch_sources = [s for s in sources if s["sourceType"] == st]
                batch_data = [{"sourceJson": s["sourceJson"], "key": s["key"]} for s in batch_sources]

                print(f"\n--- {st} 源 ({len(batch_sources)} 个) ---\n")

                def on_progress(current, total, source_name, result):
                    success = result.get("success", False)
                    needs_webview = result.get("needsWebView", False)
                    needs_intervention = result.get("needsUserIntervention", False)
                    if success:
                        tag = "✅"
                    elif needs_webview:
                        tag = "🌐"
                    elif needs_intervention:
                        tag = "🔐"
                    else:
                        tag = "❌"
                    print(f"  [{current}/{total}] {source_name} {tag}")

                def on_complete(results, success_count, total_count):
                    print(f"\n  完成: {success_count}/{total_count} 成功")

                result = client.batch_debug(
                    batch_data,
                    source_type=st,
                    on_progress=on_progress,
                    on_complete=on_complete,
                    webview_handler=None  # 3.5: 传递webview_handler参数
                )

                if result:
                    for i, r in enumerate(result.get("results", [])):
                        if i < len(batch_sources):
                            r["sourceName"] = batch_sources[i]["sourceName"]
                            r["filePath"] = batch_sources[i]["filePath"]
                    results_all.extend(result.get("results", []))

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"批处理完成（总耗时: {elapsed:.2f}s）")
        print(f"{'='*60}\n")

        # 生成汇总报告
        success_count = sum(1 for r in results_all if r.get("success"))
        needs_webview_count = sum(1 for r in results_all if r.get("needsWebView"))
        needs_intervention_count = sum(1 for r in results_all if r.get("needsUserIntervention"))
        fail_count = len(results_all) - success_count - needs_webview_count - needs_intervention_count
        if fail_count < 0:
            fail_count = len(results_all) - success_count

        print(f"汇总报告:")
        print(f"  总数: {len(results_all)}")
        print(f"  成功: {success_count}")
        print(f"  需WebView: {needs_webview_count}")
        print(f"  需用户介入: {needs_intervention_count}")
        print(f"  失败: {fail_count}")
        print(f"  耗时: {elapsed:.2f}s")
        print()

        for r in results_all:
            if r.get("success"):
                status = "✅"
            elif r.get("needsWebView"):
                status = "🌐"
            elif r.get("needsUserIntervention"):
                status = "🔐"
            else:
                status = "❌"
            name = r.get("sourceName", "unknown")
            print(f"  {status} {name}")
            if status == "❌":
                err_stage = r.get("errorStage") or r.get("failedStage") or r.get("stage") or "unknown"
                # 尝试多个可能的错误字段
                err_msg = (r.get("errorMsg") or r.get("error") or r.get("msg")
                           or r.get("message") or r.get("summary") or "")
                # 如果顶层没有错误信息，尝试从 errors 列表提取
                if not err_msg and r.get("errors"):
                    errs = r.get("errors")
                    if isinstance(errs, list) and errs:
                        err_msg = errs[0].get("msg") or errs[0].get("summary") or str(errs[0])
                # 截断过长的错误信息
                if len(err_msg) > 200:
                    err_msg = err_msg[:200] + "..."
                print(f"      阶段: {err_stage} | 错误: {err_msg}")

        # 保存详细结果到文件
        report_path = r"f:\myself\github\WeAgentChat\temp\legado\output\test-sources\batch-test-report-rss.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({
                    "total": len(results_all),
                    "success": success_count,
                    "needs_webview": needs_webview_count,
                    "needs_intervention": needs_intervention_count,
                    "fail": fail_count,
                    "elapsed_seconds": round(elapsed, 2),
                    "results": results_all
                }, f, ensure_ascii=False, indent=2)
            print(f"\n  详细结果已保存: {report_path}")
        except Exception as e:
            print(f"\n  保存详细结果失败: {e}")

        # 退出码
        sys.exit(0 if fail_count == 0 else 1)

    except FileNotFoundError as e:
        print(f"[JVM 不可用] {e}")
        sys.exit(3)
    except Exception as e:
        print(f"批处理错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


# ==================== 返回值模式（3.14） ====================

async def run_batch_and_return(
    source_type: str = "book",
    source_ids: list[int] | None = None,
    group: str | None = None,
    page: int = 1,
    page_size: int = 100,
    key: str = "",
) -> list[DebugResultData]:
    """批处理返回值模式：从数据库查询源列表，逐个测试并返回 DebugResultData 列表。

    替代文件扫描模式，直接从数据库获取源列表。

    Args:
        source_type: "book" / "rss"
        source_ids: 指定源 ID 列表（可选，优先级最高）
        group: 按分组筛选（可选）
        page: 分页页码
        page_size: 每页大小
        key: 测试关键词

    Returns:
        list[DebugResultData]: 每个源的测试结果
    """
    from legado_client.client.debug_orchestrator import DebugOrchestrator, _SimpleArgs
    from legado_client.client.debug_runner import run_and_return_v2

    # 从数据库查询源列表
    sources = await _query_sources_from_db(source_type, source_ids, group, page, page_size)
    if not sources:
        print("数据库中未找到符合条件的源")
        return []

    print(f"批处理模式（数据库）: 共 {len(sources)} 个源")

    results: list[DebugResultData] = []
    for i, source in enumerate(sources):
        source_json = source.source_json if hasattr(source, "source_json") else ""
        source_url = source.source_url if hasattr(source, "source_url") else ""
        source_name = source.source_name if hasattr(source, "source_name") else f"源{i+1}"

        if not source_json:
            results.append(DebugResultData(
                source_url=source_url, source_name=source_name,
                source_type=source_type, status="error",
                stage="load", message="源 JSON 为空",
            ))
            continue

        try:
            source_obj = json.loads(source_json)
        except json.JSONDecodeError as e:
            results.append(DebugResultData(
                source_url=source_url, source_name=source_name,
                source_type=source_type, status="error",
                stage="parse", message=f"JSON 解析失败: {e}",
                source_json=source_json,
            ))
            continue

        # 使用 JAR 模式逐个测试
        test_key = key or source_obj.get("bookSourceName") or source_name
        args = _SimpleArgs(key=test_key, timeout=30, max_iterations=1, no_experience=True, skip_db_lookup=True)

        try:
            result = await run_and_return_v2(args, source_obj, skip_db=True)
            results.append(result)
            status_tag = "✅" if result.status == "pass" else "❌"
            print(f"  [{i+1}/{len(sources)}] {source_name} {status_tag}")
        except Exception as e:
            results.append(DebugResultData(
                source_url=source_url, source_name=source_name,
                source_type=source_type, status="error",
                message=str(e), source_json=source_json,
            ))
            print(f"  [{i+1}/{len(sources)}] {source_name} ❌ {e}")

    # 汇总
    pass_count = sum(1 for r in results if r.status == "pass")
    fail_count = len(results) - pass_count
    print(f"\n批处理完成: {pass_count} 通过, {fail_count} 失败, 共 {len(results)} 个")

    return results


async def _query_sources_from_db(
    source_type: str,
    source_ids: list[int] | None,
    group: str | None,
    page: int,
    page_size: int,
) -> list:
    """从数据库查询源列表。"""
    try:
        from legado_client.storage.database import init_db, create_tables
        if not config.db_available:
            ok = await init_db()
            if ok:
                await create_tables()
            else:
                return []

        from legado_client.storage.repository import list_sources, get_source

        if source_ids:
            # 按 ID 查询
            sources = []
            for sid in source_ids:
                s = await get_source(sid)
                if s:
                    sources.append(s)
            return sources

        # 分页查询
        records, _ = await list_sources(
            page=page, page_size=page_size,
            source_type=source_type,
            group=group,
        )
        return records
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []
