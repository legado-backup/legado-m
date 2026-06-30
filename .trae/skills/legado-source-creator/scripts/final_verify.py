#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终全量验证：对真机剩余的所有书源和RSS源做WebSocket调试，生成最终质量报告。"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


def parse_logs(logs, source_type="book"):
    stages = {"search": False, "detail": False, "toc": False, "content": False}
    search_count = 0
    toc_count = 0
    errors = []
    suspects = []

    all_text = " ".join(logs).lower()

    for msg in logs:
        if "列表大小" in msg or "搜索结果" in msg:
            stages["search"] = True
            m = re.search(r"列表大小[：:](\d+)", msg)
            if m:
                search_count = int(m.group(1))
        if "获取书名" in msg:
            stages["detail"] = True
        if "目录总数" in msg or "章节列表" in msg:
            stages["toc"] = True
            m = re.search(r"目录总数[：:](\d+)", msg)
            if m:
                toc_count = int(m.group(1))
        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            stages["content"] = True
        if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
            stages["search"] = True
        if "UnknownHostException" in msg:
            errors.append("DNS")
        elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
            errors.append("TIMEOUT")

    # 严格可疑检测
    strict_login = ['logincheckjs', '需要登录', '请先登录', '登录后查看', '本章未购买']
    cf_kw = ['cf-challenge', 'cloudflare', 'cf-browser', 'just a moment', 'challenge-platform']
    captcha_kw = ['验证码', 'captcha', 'recaptcha', 'geetest', '极验', '人机验证']

    for kw in strict_login:
        if kw in all_text:
            suspects.append("LOGIN")
            break
    for kw in cf_kw:
        if kw in all_text:
            suspects.append("CF")
            break
    for kw in captcha_kw:
        if kw in all_text:
            suspects.append("CAPTCHA")
            break

    return stages, search_count, toc_count, errors, suspects


async def main():
    print("=" * 60)
    print(f" 最终全量验证")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    book_sources = await client.get_book_sources()
    rss_sources = await client.get_rss_sources()
    print(f" 书源: {len(book_sources)}")
    print(f" RSS源: {len(rss_sources)}")

    results = {"book": [], "rss": []}
    sem = asyncio.Semaphore(15)

    # === 书源 ===
    print(f"\n=== 验证书源 ({len(book_sources)}) ===")
    progress = {"done": 0, "lock": asyncio.Lock()}

    async def _test_book(src):
        async with sem:
            url = src.get("bookSourceUrl", "")
            name = src.get("bookSourceName", "?")
            try:
                logs = await asyncio.wait_for(
                    client.ws_debug_book_source(src, "斗破苍穹"), timeout=90
                )
                stages, sc, tc, errs, suspects = parse_logs(logs, "book")
                sp = sum(1 for v in stages.values() if v)
                status = "success" if sp >= 4 else ("partial" if sp > 0 else "failed")
                results["book"].append({
                    "url": url, "name": name, "status": status,
                    "stages": stages, "search_count": sc, "toc_count": tc,
                    "errors": errs, "suspects": suspects,
                })
            except Exception as e:
                results["book"].append({
                    "url": url, "name": name, "status": "error",
                    "stages": {"search": False, "detail": False, "toc": False, "content": False},
                    "search_count": 0, "errors": [str(e)[:40]], "suspects": [],
                })
            async with progress["lock"]:
                progress["done"] += 1
                if progress["done"] % 100 == 0 or progress["done"] == len(book_sources):
                    print(f"  [{progress['done']}/{len(book_sources)}]")

    await asyncio.gather(*[_test_book(s) for s in book_sources])

    # === RSS源 ===
    print(f"\n=== 验证RSS源 ({len(rss_sources)}) ===")
    progress = {"done": 0, "lock": asyncio.Lock()}

    async def _test_rss(src):
        async with sem:
            url = src.get("sourceUrl", "")
            name = src.get("sourceName", "?")
            try:
                logs = await asyncio.wait_for(
                    client.ws_debug_rss_source(src), timeout=90
                )
                stages, sc, tc, errs, suspects = parse_logs(logs, "rss")
                status = "success" if stages["search"] else "failed"
                results["rss"].append({
                    "url": url, "name": name, "status": status,
                    "stages": stages, "errors": errs, "suspects": suspects,
                })
            except Exception as e:
                results["rss"].append({
                    "url": url, "name": name, "status": "error",
                    "stages": {"search": False, "detail": False, "toc": False, "content": False},
                    "errors": [str(e)[:40]], "suspects": [],
                })
            async with progress["lock"]:
                progress["done"] += 1
                if progress["done"] % 50 == 0 or progress["done"] == len(rss_sources):
                    print(f"  [{progress['done']}/{len(rss_sources)}]")

    await asyncio.gather(*[_test_rss(s) for s in rss_sources])

    # 汇总
    print(f"\n{'='*60}")
    print(f" 最终验证结果")
    print(f"{'='*60}")

    for stype in ["book", "rss"]:
        r = results[stype]
        total = len(r)
        success = sum(1 for x in r if x["status"] == "success")
        partial = sum(1 for x in r if x["status"] == "partial")
        failed = sum(1 for x in r if x["status"] in ("failed", "error"))
        with_results = sum(1 for x in r if x.get("search_count", 0) > 0)
        suspects_count = sum(1 for x in r if x.get("suspects"))
        suspect_types = {}
        for x in r:
            for s in x.get("suspects", []):
                suspect_types[s] = suspect_types.get(s, 0) + 1

        label = "书源" if stype == "book" else "RSS源"
        print(f"\n  {label}: {total}")
        print(f"    成功: {success} ({success/total*100:.1f}%)")
        print(f"    部分成功: {partial} ({partial/total*100:.1f}%)")
        print(f"    失败: {failed} ({failed/total*100:.1f}%)")
        print(f"    有搜索结果: {with_results}")
        print(f"    嫌疑(CF/验证码/登录): {suspects_count}")
        if suspect_types:
            for s, c in suspect_types.items():
                print(f"      {s}: {c}")

    # 保存
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"final-verify-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "book_count": len(book_sources),
            "rss_count": len(rss_sources),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {report_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
