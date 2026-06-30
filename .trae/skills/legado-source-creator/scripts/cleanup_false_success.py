#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理假成功源：搜索返回0结果的源从真机删除。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


async def main():
    print("=" * 60)
    print(f" 清理假成功源（搜索0结果）")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    with open(os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    book_results = report.get("results", {}).get("book", [])

    false_success_urls = []
    for r in book_results:
        if r["status"] not in ("success", "partial"):
            continue
        s = r.get("stages", {})
        sc = r.get("search_count", 0)
        if s.get("search") and sc == 0:
            false_success_urls.append(r.get("source_url", ""))

    print(f" 假成功源(搜索0结果): {len(false_success_urls)}")

    all_sources = await client.get_book_sources()
    device_urls = set(s.get("bookSourceUrl", "") for s in all_sources)
    print(f" 真机书源数: {len(all_sources)}")

    to_delete = [u for u in false_success_urls if u in device_urls]
    print(f" 真机中存在: {len(to_delete)}")

    if to_delete:
        deleted = 0
        for i in range(0, len(to_delete), 100):
            batch = to_delete[i:i + 100]
            payload = [{"bookSourceUrl": u} for u in batch]
            ok = await client.delete_book_sources(payload)
            deleted += len(batch)
            print(f"  删除进度: {min(i + 100, len(to_delete))}/{len(to_delete)}")
        print(f"\n真机删除: {deleted} 个假成功源")

    remaining = await client.get_book_sources()
    print(f"删除后真机书源数: {len(remaining)}")

    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"cleanup-false-success-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "deleted_from_device": len(to_delete),
            "device_count_before": len(all_sources),
            "device_count_after": len(remaining),
            "false_success_urls": false_success_urls,
        }, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
