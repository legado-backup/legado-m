#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量真机 WebSocket 调试脚本。

通过 WebSocket 1123 端口对真机上的书源/订阅源做端到端调试，
收集搜索/详情/目录/正文各阶段的通过情况，输出分析报告。

用法:
    python batch_device_debug.py --book-sample 30 --rss-sample 10
    python batch_device_debug.py --book-sample 50 --rss-sample 0 --output reports/batch-debug.json
    python batch_device_debug.py --urls "https://m.qidian.com,https://www.biqubo.com"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ==================== 真机 HTTP API ====================

async def get_device_sources(
    host: str = "127.0.0.1",
    port: int = 1122,
    source_type: str = "book",
    timeout: float = 300.0,
) -> List[Dict]:
    """从真机获取源列表。"""
    import httpx
    if source_type == "book":
        url = f"http://{host}:{port}/getBookSources"
    else:
        url = f"http://{host}:{port}/getRssSources"

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        r = await client.get(url)
        data = r.json()
        # Legado ReturnData 格式: {data: [...], isSuccess: true}
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        elif isinstance(data, list):
            return data
        return []


# ==================== WebSocket 调试 ====================

async def debug_source_ws(
    source_url: str,
    source_type: str,
    key: str,
    ws_host: str = "127.0.0.1",
    ws_port: int = 1123,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """通过 WebSocket 调试单个源，返回阶段结果。"""
    import websockets

    result: Dict[str, Any] = {
        "source_url": source_url,
        "source_type": source_type,
        "status": "unknown",
        "stages": {
            "search": False,
            "detail": False,
            "toc": False,
            "content": False,
        },
        "search_count": 0,
        "toc_count": 0,
        "content_length": 0,
        "errors": [],
        "logs": [],
        "duration_ms": 0,
    }

    path = "/bookSourceDebug" if source_type == "book" else "/rssSourceDebug"
    ws_url = f"ws://{ws_host}:{ws_port}{path}"

    start = time.time()
    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            # 发送调试请求
            req = {"tag": source_url, "key": key}
            await ws.send(json.dumps(req))

            # 接收日志流
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    if not msg:
                        continue

                    # 真机日志是纯文本格式: [MM:SS.mmm] 消息
                    result["logs"].append(msg[:500])

                    # 阶段判定（基于关键词匹配）
                    if "列表大小" in msg or "搜索结果" in msg:
                        result["stages"]["search"] = True
                        # 提取搜索数量
                        import re
                        m = re.search(r"列表大小[：:](\d+)", msg)
                        if m:
                            result["search_count"] = int(m.group(1))

                    if "获取书名" in msg or "书名" in msg:
                        result["stages"]["detail"] = True

                    if "目录总数" in msg or "章节列表" in msg:
                        result["stages"]["toc"] = True
                        import re
                        m = re.search(r"目录总数[：:](\d+)", msg)
                        if m:
                            result["toc_count"] = int(m.group(1))

                    if "获取正文" in msg and "成功" in msg:
                        result["stages"]["content"] = True

                    # RSS 特有
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
                        result["stages"]["search"] = True

                    # 错误检测
                    if "UnknownHostException" in msg:
                        result["errors"].append("DNS解析失败")
                    elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
                        result["errors"].append("连接超时")
                    elif "403" in msg or "Forbidden" in msg:
                        result["errors"].append("403禁止访问")
                    elif "CF" in msg and ("challenge" in msg.lower() or "盾" in msg):
                        result["errors"].append("CF拦截")
                    elif "loginCheckJs" in msg or "需要登录" in msg:
                        result["errors"].append("需要登录")

                    # 调试结束标志
                    if "调试结束" in msg:
                        break

            except asyncio.TimeoutError:
                result["errors"].append("调试超时")

    except Exception as e:
        err_msg = str(e)
        # WebSocket 1000 OK + 调试结束 是正常关闭，不是连接失败
        if "1000" in err_msg and "调试结束" in err_msg:
            pass  # 正常结束，不记录错误
        else:
            result["errors"].append(f"连接失败: {err_msg[:100]}")
        result["duration_ms"] = int((time.time() - start) * 1000)

    result["duration_ms"] = int((time.time() - start) * 1000)

    # 计算通过状态
    if source_type == "book":
        stages_passed = sum(1 for v in result["stages"].values() if v)
        if stages_passed >= 4:
            result["status"] = "success"
        elif stages_passed > 0:
            result["status"] = "partial"
        else:
            result["status"] = "failed"
    else:
        # RSS: search阶段即文章列表
        if result["stages"]["search"]:
            result["status"] = "success"
        else:
            result["status"] = "failed"

    return result


# ==================== 采样 ====================

def sample_sources(
    sources: List[Dict],
    sample_size: int,
    source_type: str = "book",
    per_domain: int = 2,
) -> List[Dict]:
    """按域名分层采样源。"""
    from urllib.parse import urlparse

    # 提取域名分组
    domain_groups: Dict[str, List[Dict]] = {}
    for s in sources:
        url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
        url = s.get(url_key, "")
        try:
            if "://" not in url:
                url = f"http://{url}"
            domain = urlparse(url).hostname or "unknown"
            domain = domain.lower().replace("www.", "")
        except Exception:
            domain = "unknown"
        domain_groups.setdefault(domain, []).append(s)

    # 每组采样
    sampled: List[Dict] = []
    for domain, srcs in sorted(domain_groups.items(), key=lambda x: -len(x[1])):
        # 优先有 searchUrl/exploreUrl 的
        if source_type == "book":
            srcs.sort(key=lambda s: (0 if s.get("searchUrl") else 1, 0 if s.get("enabledExplore") else 1))
        else:
            srcs.sort(key=lambda s: (0 if s.get("ruleArticles") else 1))
        picked = srcs[:per_domain]
        sampled.extend(picked)
        if len(sampled) >= sample_size:
            break

    return sampled[:sample_size]


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="批量真机 WebSocket 调试")
    parser.add_argument("--book-sample", type=int, default=30, help="书源采样数")
    parser.add_argument("--rss-sample", type=int, default=10, help="订阅源采样数")
    parser.add_argument("--host", default="127.0.0.1", help="真机 HTTP 地址")
    parser.add_argument("--http-port", type=int, default=1122, help="HTTP 端口")
    parser.add_argument("--ws-port", type=int, default=1123, help="WebSocket 端口")
    parser.add_argument("--timeout", type=float, default=60.0, help="单源调试超时（秒）")
    parser.add_argument("--output", default="", help="输出 JSON 文件路径")
    parser.add_argument("--urls", default="", help="指定调试的源URL（逗号分隔）")
    parser.add_argument("--per-domain", type=int, default=2, help="每域名采样数")
    args = parser.parse_args()

    print("=" * 60)
    print("批量真机 WebSocket 调试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取源列表
    all_book_sources = []
    all_rss_sources = []

    if args.book_sample > 0:
        print(f"\n[1/4] 获取书源列表...")
        all_book_sources = await get_device_sources(
            args.host, args.http_port, "book", timeout=300.0
        )
        print(f"  真机书源数: {len(all_book_sources)}")

    if args.rss_sample > 0:
        print(f"\n[1/4] 获取订阅源列表...")
        all_rss_sources = await get_device_sources(
            args.host, args.http_port, "rss", timeout=120.0
        )
        print(f"  真机订阅源数: {len(all_rss_sources)}")

    # 2. 采样
    book_sources = []
    rss_sources = []

    if args.urls:
        # 指定URL模式
        urls = [u.strip() for u in args.urls.split(",") if u.strip()]
        book_sources = [
            s for s in all_book_sources
            if s.get("bookSourceUrl", "") in urls
        ]
        rss_sources = [
            s for s in all_rss_sources
            if s.get("sourceUrl", "") in urls
        ]
        print(f"\n[2/4] 指定URL: {len(book_sources)} 书源 + {len(rss_sources)} 订阅源")
    else:
        if args.book_sample > 0 and all_book_sources:
            book_sources = sample_sources(
                all_book_sources, args.book_sample, "book", args.per_domain
            )
        if args.rss_sample > 0 and all_rss_sources:
            rss_sources = sample_sources(
                all_rss_sources, args.rss_sample, "rss", args.per_domain
            )
        print(f"\n[2/4] 采样: {len(book_sources)} 书源 + {len(rss_sources)} 订阅源")

    # 3. 批量调试
    results: List[Dict] = []

    # 书源调试
    if book_sources:
        print(f"\n[3/4] 调试 {len(book_sources)} 个书源...")
        for i, src in enumerate(book_sources):
            url = src.get("bookSourceUrl", "")
            name = src.get("bookSourceName", "?")
            print(f"  [{i+1}/{len(book_sources)}] {name[:30]} ({url[:50]})")

            r = await debug_source_ws(
                source_url=url,
                source_type="book",
                key="斗破苍穹",
                ws_host=args.host,
                ws_port=args.ws_port,
                timeout=args.timeout,
            )
            r["source_name"] = name
            results.append(r)

            stages_str = " ".join(
                f"{s[:3]}={'Y' if v else 'N'}"
                for s, v in r["stages"].items()
            )
            err_short = r["errors"][0][:50] if r["errors"] else ""
            print(f"    {stages_str} | {r['status']} | {r['duration_ms']}ms"
                  + (f" | {err_short}" if err_short else ""))

    # 订阅源调试
    if rss_sources:
        print(f"\n[3/4] 调试 {len(rss_sources)} 个订阅源...")
        for i, src in enumerate(rss_sources):
            url = src.get("sourceUrl", "")
            name = src.get("sourceName", "?")
            print(f"  [{i+1}/{len(rss_sources)}] {name[:30]} ({url[:50]})")

            r = await debug_source_ws(
                source_url=url,
                source_type="rss",
                key="首页",
                ws_host=args.host,
                ws_port=args.ws_port,
                timeout=args.timeout,
            )
            r["source_name"] = name
            results.append(r)

            stages_str = " ".join(
                f"{s[:3]}={'Y' if v else 'N'}"
                for s, v in r["stages"].items()
            )
            err_short = r["errors"][0][:50] if r["errors"] else ""
            print(f"    {stages_str} | {r['status']} | {r['duration_ms']}ms"
                  + (f" | {err_short}" if err_short else ""))

    # 4. 统计报告
    print(f"\n[4/4] 统计分析...")
    book_results = [r for r in results if r["source_type"] == "book"]
    rss_results = [r for r in results if r["source_type"] == "rss"]

    def _stats(items: List[Dict], label: str):
        if not items:
            return
        total = len(items)
        success = sum(1 for r in items if r["status"] == "success")
        partial = sum(1 for r in items if r["status"] == "partial")
        failed = sum(1 for r in items if r["status"] == "failed")
        error_items = sum(1 for r in items if r["status"] == "error")

        # 各阶段通过率
        stage_pass = {}
        for stage in ["search", "detail", "toc", "content"]:
            stage_pass[stage] = sum(1 for r in items if r["stages"].get(stage)) / total * 100

        # 错误分类
        error_counts: Dict[str, int] = {}
        for r in items:
            for e in r.get("errors", []):
                # 简化错误类型
                if "DNS" in e:
                    error_counts["DNS解析失败"] = error_counts.get("DNS解析失败", 0) + 1
                elif "超时" in e or "timeout" in e.lower():
                    error_counts["连接超时"] = error_counts.get("连接超时", 0) + 1
                elif "403" in e:
                    error_counts["403禁止访问"] = error_counts.get("403禁止访问", 0) + 1
                elif "CF" in e:
                    error_counts["CF拦截"] = error_counts.get("CF拦截", 0) + 1
                elif "登录" in e:
                    error_counts["需要登录"] = error_counts.get("需要登录", 0) + 1
                else:
                    error_counts[e[:30]] = error_counts.get(e[:30], 0) + 1

        print(f"\n{'='*50}")
        print(f" {label} 统计 (共 {total} 个)")
        print(f"{'='*50}")
        print(f"  完全通过: {success} ({success/total*100:.1f}%)")
        print(f"  部分通过: {partial} ({partial/total*100:.1f}%)")
        print(f"  全部失败: {failed} ({failed/total*100:.1f}%)")
        print(f"  连接错误: {error_items} ({error_items/total*100:.1f}%)")
        print(f"\n  阶段通过率:")
        for stage, pct in stage_pass.items():
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {stage:8s} {bar} {pct:.1f}%")
        if error_counts:
            print(f"\n  错误分类:")
            for err, cnt in sorted(error_counts.items(), key=lambda x: -x[1])[:8]:
                print(f"    {err}: {cnt}")

        # 成功源列表
        success_sources = [r for r in items if r["status"] == "success"]
        if success_sources:
            print(f"\n  ✅ 完全通过源:")
            for r in success_sources[:10]:
                print(f"    {r.get('source_name','?')[:30]} | {r['source_url'][:50]}")

        # 失败源列表（可修复候选）
        failed_sources = [r for r in items if r["status"] in ("failed", "partial")]
        if failed_sources:
            print(f"\n  ❌ 需修复源 (前10):")
            for r in failed_sources[:10]:
                stages = " ".join(f"{s[:3]}={'Y' if v else 'N'}" for s, v in r["stages"].items())
                err = r["errors"][0][:40] if r["errors"] else ""
                print(f"    {r.get('source_name','?')[:20]} | {stages} | {err}")

    _stats(book_results, "书源")
    _stats(rss_results, "订阅源")

    # 保存报告
    output_path = args.output
    if not output_path:
        os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
        output_path = os.path.join(
            SCRIPTS_DIR, "reports", f"batch-device-debug-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )

    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "book_sample": args.book_sample,
            "rss_sample": args.rss_sample,
            "timeout": args.timeout,
            "host": args.host,
        },
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {output_path}")

    # 输出可修复源 JSON（用于后续 Phase 2 修复）
    fixable = [
        r for r in results
        if r["status"] in ("failed", "partial") and "DNS" not in str(r.get("errors", []))
    ]
    if fixable:
        fixable_path = output_path.replace(".json", "-fixable.json")
        with open(fixable_path, "w", encoding="utf-8") as f:
            json.dump(fixable, f, ensure_ascii=False, indent=2)
        print(f"可修复源列表: {fixable_path} ({len(fixable)} 个)")


if __name__ == "__main__":
    asyncio.run(main())
