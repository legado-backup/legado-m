#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理不可用RSS源：超时、DNS、SSL、403。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


async def main():
    print("=" * 60)
    print(f" 清理不可用RSS源")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    with open(os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    rss_results = report.get("results", {}).get("rss", [])

    # 找不可用的RSS源
    delete_urls = []
    for r in rss_results:
        if r["status"] == "success":
            continue
        errors = r.get("errors", [])
        if any(e in errors for e in ["TIMEOUT", "WS_TIMEOUT", "DNS", "SSL", "403", "CF"]):
            delete_urls.append(r.get("source_url", ""))

    print(f" 不可用RSS源: {len(delete_urls)}")

    all_rss = await client.get_rss_sources()
    device_urls = set(s.get("sourceUrl", "") for s in all_rss)
    print(f" 真机RSS源数: {len(all_rss)}")

    to_delete = [u for u in delete_urls if u in device_urls]
    print(f" 真机中存在: {len(to_delete)}")

    if to_delete:
        for i in range(0, len(to_delete), 100):
            batch = to_delete[i:i + 100]
            payload = [{"sourceUrl": u} for u in batch]
            await client.delete_rss_sources(payload)
            print(f"  删除进度: {min(i + 100, len(to_delete))}/{len(to_delete)}")

    remaining = await client.get_rss_sources()
    print(f"\n删除后真机RSS源数: {len(remaining)}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
