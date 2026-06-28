#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超时源快速重测：使用 LegadoWebClient 正确处理 WebSocket 协议。

用法:
    python retest_timeout.py --timeout 60 --concurrency 20 --execute
    python retest_timeout.py --timeout 60 --concurrency 20 --execute --delete-dead
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


def parse_debug_logs(logs: List[str], source_type: str = "book") -> Dict[str, Any]:
    """解析WebSocket调试日志，提取阶段结果。"""
    result = {
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "search_count": 0,
        "toc_count": 0,
        "errors": [],
        "logs_summary": [],
    }

    for msg in logs:
        # 关键日志摘要
        if any(kw in msg for kw in [
            "列表大小", "搜索结果", "获取书名", "目录总数", "正文",
            "Exception", "错误", "列表为空", "获取成功", "调试结束",
            "403", "404", "500", "timeout", "UnknownHost", "SSL",
        ]):
            result["logs_summary"].append(msg[:300])

        # 阶段判定
        if "列表大小" in msg or "搜索结果" in msg:
            result["stages"]["search"] = True
            m = re.search(r"列表大小[：:](\d+)", msg)
            if m:
                result["search_count"] = int(m.group(1))

        if "获取书名" in msg or ("书名" in msg and "获取" in msg):
            result["stages"]["detail"] = True

        if "目录总数" in msg or "章节列表" in msg:
            result["stages"]["toc"] = True
            m = re.search(r"目录总数[：:](\d+)", msg)
            if m:
                result["toc_count"] = int(m.group(1))

        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            result["stages"]["content"] = True

        # RSS
        if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
            result["stages"]["search"] = True

        # 错误
        if "UnknownHostException" in msg:
            result["errors"].append("DNS")
        elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
            result["errors"].append("TIMEOUT")
        elif "403" in msg or "Forbidden" in msg:
            result["errors"].append("403")
        elif "CF" in msg and ("challenge" in msg.lower() or "盾" in msg):
            result["errors"].append("CF")
        elif "SSLException" in msg or "SSLHandshakeException" in msg:
            result["errors"].append("SSL")
        elif "JSONException" in msg or "JsonSyntaxException" in msg:
            result["errors"].append("JSON_PARSE")

    return result


async def debug_with_timeout(
    client: LegadoWebClient,
    source: Dict,
    key: str,
    source_type: str,
    timeout: float,
) -> Dict[str, Any]:
    """使用 LegadoWebClient 调试单个源，带超时保护。"""
    start = time.time()
    try:
        if source_type == "book":
            logs = await asyncio.wait_for(
                client.ws_debug_book_source(source, key),
                timeout=timeout,
            )
        else:
            logs = await asyncio.wait_for(
                client.ws_debug_rss_source(source),
                timeout=timeout,
            )
    except asyncio.TimeoutError:
        return {
            "source_url": source.get("bookSourceUrl" if source_type == "book" else "sourceUrl", ""),
            "source_name": source.get("bookSourceName" if source_type == "book" else "sourceName", "?"),
            "status": "timeout",
            "stages": {"search": False, "detail": False, "toc": False, "content": False},
            "search_count": 0, "toc_count": 0,
            "errors": ["WS_TIMEOUT"],
            "duration_ms": int((time.time() - start) * 1000),
        }
    except Exception as e:
        return {
            "source_url": source.get("bookSourceUrl" if source_type == "book" else "sourceUrl", ""),
            "source_name": source.get("bookSourceName" if source_type == "book" else "sourceName", "?"),
            "status": "error",
            "stages": {"search": False, "detail": False, "toc": False, "content": False},
            "search_count": 0, "toc_count": 0,
            "errors": [f"EXCEPTION:{str(e)[:60]}"],
            "duration_ms": int((time.time() - start) * 1000),
        }

    parsed = parse_debug_logs(logs, source_type)
    duration_ms = int((time.time() - start) * 1000)

    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    name_key = "bookSourceName" if source_type == "book" else "sourceName"

    stages_passed = sum(1 for v in parsed["stages"].values() if v)
    if source_type == "book":
        if stages_passed >= 4:
            status = "success"
        elif stages_passed > 0:
            status = "partial"
        else:
            status = "failed"
    else:
        status = "success" if parsed["stages"]["search"] else "failed"

    return {
        "source_url": source.get(url_key, ""),
        "source_name": source.get(name_key, "?"),
        "status": status,
        "stages": parsed["stages"],
        "search_count": parsed["search_count"],
        "toc_count": parsed["toc_count"],
        "errors": parsed["errors"],
        "logs_summary": parsed["logs_summary"],
        "duration_ms": duration_ms,
    }


async def main():
    parser = argparse.ArgumentParser(description="超时源快速重测")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--delete-dead", action="store_true", help="删除DNS/SSL死源")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    print("=" * 60)
    print(f" 超时源快速重测 (timeout={args.timeout}s, concurrency={args.concurrency})")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载超时源URL
    timeout_path = os.path.join(SCRIPTS_DIR, "reports", "timeout_sources.json")
    if not os.path.exists(timeout_path):
        print("错误: 找不到 reports/timeout_sources.json")
        return

    with open(timeout_path, "r") as f:
        timeout_urls = set(json.load(f))
    print(f" 超时源数: {len(timeout_urls)}")

    # 使用 LegadoWebClient
    client = LegadoWebClient(host="127.0.0.1", port=1122)

    # 获取真机源
    all_sources = await client.get_book_sources()
    print(f" 真机书源总数: {len(all_sources)}")

    # 匹配超时源
    test_sources = [s for s in all_sources if s.get("bookSourceUrl", "") in timeout_urls]
    print(f" 匹配到超时源: {len(test_sources)}")

    if not test_sources:
        print(" 无需测试")
        await client.close()
        return

    # 并发测试
    sem = asyncio.Semaphore(args.concurrency)
    progress = {"done": 0, "total": len(test_sources), "lock": asyncio.Lock()}
    stats = {"success": 0, "partial": 0, "failed": 0,
             "sea": 0, "det": 0, "toc": 0, "con": 0,
             "dns": 0, "timeout": 0, "ssl": 0}
    results = []

    async def _test(src: Dict) -> Dict:
        async with sem:
            r = await debug_with_timeout(client, src, "斗破苍穹", "book", args.timeout)
            async with progress["lock"]:
                progress["done"] += 1
                s = r["stages"]
                if s["search"]: stats["sea"] += 1
                if s["detail"]: stats["det"] += 1
                if s["toc"]: stats["toc"] += 1
                if s["content"]: stats["con"] += 1
                if r["status"] == "success": stats["success"] += 1
                elif r["status"] == "partial": stats["partial"] += 1
                else: stats["failed"] += 1
                for e in r["errors"]:
                    if e == "DNS": stats["dns"] += 1
                    elif "TIMEOUT" in e: stats["timeout"] += 1
                    elif e == "SSL": stats["ssl"] += 1
                if progress["done"] % 50 == 0 or progress["done"] == progress["total"]:
                    print(f"  [{progress['done']}/{progress['total']}] "
                          f"sea={stats['sea']} det={stats['det']} "
                          f"toc={stats['toc']} con={stats['con']} "
                          f"ok={stats['success']} part={stats['partial']} "
                          f"fail={stats['failed']} dns={stats['dns']} "
                          f"still_timeout={stats['timeout']}")
            results.append(r)
            return r

    # 分批处理，避免同时创建太多协程
    batch_size = 200
    for batch_start in range(0, len(test_sources), batch_size):
        batch = test_sources[batch_start:batch_start + batch_size]
        batch_tasks = [_test(src) for src in batch]
        await asyncio.gather(*batch_tasks, return_exceptions=True)
        print(f"  --- 批次 {batch_start // batch_size + 1}/{(len(test_sources) + batch_size - 1) // batch_size} 完成 ---")

    print(f"\n{'='*60}")
    print(f" 重测结果:")
    print(f"  成功: {stats['success']} ({stats['success']/len(test_sources)*100:.1f}%)")
    print(f"  部分成功: {stats['partial']} ({stats['partial']/len(test_sources)*100:.1f}%)")
    print(f"  仍然失败: {stats['failed']} ({stats['failed']/len(test_sources)*100:.1f}%)")
    print(f"  仍然超时: {stats['timeout']}")
    print(f"  DNS死站: {stats['dns']}")
    print(f"  SSL错误: {stats['ssl']}")

    # 删除DNS死源
    if args.delete_dead:
        dns_urls = [r["source_url"] for r in results if "DNS" in r.get("errors", [])]
        ssl_urls = [r["source_url"] for r in results if "SSL" in r.get("errors", [])]
        dead_urls = dns_urls + ssl_urls
        if dead_urls:
            # 构建 LegadoWebClient 需要的删除格式
            delete_payload = [{"bookSourceUrl": u} for u in dead_urls]
            ok = await client.delete_book_sources(delete_payload)
            print(f"\n删除DNS/SSL死源: {len(dead_urls)} 个, 结果: {ok}")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = args.output or os.path.join(
        SCRIPTS_DIR, "reports",
        f"retest-timeout-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {"timeout": args.timeout, "concurrency": args.concurrency},
        "stats": stats,
        "results": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
