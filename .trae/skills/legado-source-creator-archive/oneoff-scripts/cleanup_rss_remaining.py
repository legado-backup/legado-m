#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理剩余失败RSS源（非超时/DNS/SSL，但规则过时/返回格式错误）。"""
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
    print(f" 清理剩余失败RSS源")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    with open(os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    rss_results = report.get("results", {}).get("rss", [])

    # 所有失败的RSS源（除了已删的超时/DNS/SSL/403/CF）
    failed_urls = []
    for r in rss_results:
        if r["status"] == "success":
            continue
        failed_urls.append(r.get("source_url", ""))

    print(f" 所有失败RSS源: {len(failed_urls)}")

    all_rss = await client.get_rss_sources()
    device_urls = set(s.get("sourceUrl", "") for s in all_rss)
    print(f" 真机RSS源数: {len(all_rss)}")

    to_delete = [u for u in failed_urls if u in device_urls]
    print(f" 真机中存在: {len(to_delete)}")

    if to_delete:
        for i in range(0, len(to_delete), 100):
            batch = to_delete[i:i + 100]
            payload = [{"sourceUrl": u} for u in batch]
            await client.delete_rss_sources(payload)
            print(f"  删除进度: {min(i + 100, len(to_delete))}/{len(to_delete)}")

    remaining = await client.get_rss_sources()
    print(f"\n删除后真机RSS源数: {len(remaining)}")
    print(f"RSS源成功率: {len(remaining) - (len(to_delete) - (len(failed_urls) - len(to_delete)))}/{len(remaining)}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
