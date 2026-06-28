#!/usr/bin/env python3
"""并发批量WebSocket测试 - 快速评估源质量。

使用10并发WebSocket，快速测试大量源。
输出分类统计和详细报告。
"""
import asyncio, json, os, re, sys, time
from collections import Counter
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

HOST = "127.0.0.1"
HTTP_PORT = 1122
WS_PORT = 1123


async def debug_one(url: str, source_type: str, key: str, sem: asyncio.Semaphore, timeout: float):
    """测试单个源。"""
    import websockets
    async with sem:
        result = {
            "url": url, "type": source_type,
            "stages": {"search": False, "detail": False, "toc": False, "content": False},
            "errors": [], "ms": 0,
        }
        path = "/bookSourceDebug" if source_type == "book" else "/rssSourceDebug"
        start = time.time()
        try:
            async with websockets.connect(f"ws://{HOST}:{WS_PORT}{path}", open_timeout=8) as ws:
                await ws.send(json.dumps({"tag": url, "key": key}, ensure_ascii=False))
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    if "列表大小" in msg or "搜索结果" in msg: result["stages"]["search"] = True
                    if "获取书名" in msg: result["stages"]["detail"] = True
                    if "目录总数" in msg: result["stages"]["toc"] = True
                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg: result["stages"]["content"] = True
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg): result["stages"]["search"] = True
                    if "UnknownHostException" in msg: result["errors"].append("DNS")
                    elif "403" in msg: result["errors"].append("403")
                    elif "CF" in msg and "盾" in msg: result["errors"].append("CF")
                    if "调试结束" in msg: break
        except asyncio.TimeoutError:
            result["errors"].append("TIMEOUT")
        except Exception as e:
            err = str(e)
            if "1000" in err and "调试结束" in err: pass
            else: result["errors"].append(f"CONN:{err[:40]}")
        result["ms"] = int((time.time() - start) * 1000)
        return result


async def main():
    import argparse, httpx
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-sample", type=int, default=500)
    parser.add_argument("--rss-sample", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--per-domain", type=int, default=1)
    args = parser.parse_args()

    print(f"并发测试: 书源{args.book_sample} + 订阅源{args.rss_sample} | 并发{args.concurrency}")
    sem = asyncio.Semaphore(args.concurrency)

    for st in ["book", "rss"]:
        sample_size = args.book_sample if st == "book" else args.rss_sample
        if sample_size <= 0: continue

        url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
        name_key = "bookSourceName" if st == "book" else "sourceName"
        key = "斗破苍穹" if st == "book" else "首页"
        label = "书源" if st == "book" else "订阅源"

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            ep = "getBookSources" if st == "book" else "getRssSources"
            r = await client.get(f"http://{HOST}:{HTTP_PORT}/{ep}")
            sources = r.json().get("data", [])

        print(f"\n{label}总数: {len(sources)}")

        # 按域名分层采样
        domain_groups: Dict[str, List] = {}
        for s in sources:
            url = s.get(url_key, "")
            try:
                base = url.split("#")[0].strip()
                if "://" not in base: base = "http://" + base
                domain = urlparse(base).hostname or ""
                domain = domain.lower().replace("www.", "")
                domain_groups.setdefault(domain, []).append(s)
            except: pass

        sampled = []
        for domain, srcs in sorted(domain_groups.items(), key=lambda x: -len(x[1])):
            # 优先有searchUrl的
            srcs.sort(key=lambda s: (0 if s.get("searchUrl") else 1, 0 if s.get("enabledExplore") else 1))
            sampled.extend(srcs[:args.per_domain])
            if len(sampled) >= sample_size: break
        sampled = sampled[:sample_size]

        print(f"采样: {len(sampled)} 个源, 开始测试...")

        # 并发测试
        tasks = [debug_one(s.get(url_key, ""), st, key, sem, args.timeout) for s in sampled]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计
        valid = [r for r in results if isinstance(r, dict)]
        total = len(valid)

        # Stage模式分布
        patterns = Counter()
        for r in valid:
            p = f"sea={'Y' if r['stages']['search'] else 'N'} det={'Y' if r['stages']['detail'] else 'N'} toc={'Y' if r['stages']['toc'] else 'N'} con={'Y' if r['stages']['content'] else 'N'}"
            patterns[p] += 1

        # 通过率
        full_pass = sum(1 for r in valid if all(r["stages"].values()))
        has_search = sum(1 for r in valid if r["stages"]["search"])
        has_content = sum(1 for r in valid if r["stages"]["content"])

        print(f"\n{'='*50}")
        print(f" {label}测试结果 ({total}个)")
        print(f"{'='*50}")
        print(f"  全部通过: {full_pass} ({full_pass/total*100:.1f}%)")
        print(f"  搜索通过: {has_search} ({has_search/total*100:.1f}%)")
        print(f"  正文通过: {has_content} ({has_content/total*100:.1f}%)")

        print(f"\n  Stage模式分布:")
        for p, c in patterns.most_common(10):
            print(f"    {p}: {c} ({c/total*100:.1f}%)")

        # 错误分类
        error_counts = Counter()
        for r in valid:
            for e in r.get("errors", []):
                error_counts[e[:20]] += 1
        if error_counts:
            print(f"\n  错误分类:")
            for e, c in error_counts.most_common():
                print(f"    {e}: {c}")

        # 保存报告
        os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
        out = os.path.join(SCRIPTS_DIR, "reports", f"concurrent-test-{st}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        report = {
            "timestamp": datetime.now().isoformat(),
            "sample_size": sample_size,
            "total_tested": total,
            "full_pass": full_pass,
            "search_pass": has_search,
            "content_pass": has_content,
            "stage_patterns": dict(patterns),
            "results": valid,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告: {out}")


if __name__ == "__main__":
    asyncio.run(main())
