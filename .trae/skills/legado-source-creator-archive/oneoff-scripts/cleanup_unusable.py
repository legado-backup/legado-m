#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理不可用源：真机删除 + 数据库标记。

策略：
1. 删除45秒超时的源（3357个）- 真机删除
2. 删除DNS死站（40个）- 真机删除
3. 删除SSL错误（117个）- 真机删除
4. 假成功（搜索结果为空）暂不删，需进一步分析
5. 数据库标记（如果可用）
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


async def main():
    print("=" * 60)
    print(f" 清理不可用源")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    # 加载全量测试报告
    with open(os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    book_results = report.get("results", {}).get("book", [])

    # 分类
    timeout_urls = []
    dns_urls = []
    ssl_urls = []
    false_success_urls = []  # 假成功

    for r in book_results:
        url = r.get("source_url", "")
        errors = r.get("errors", [])
        status = r.get("status", "")

        if "TIMEOUT" in errors or "WS_TIMEOUT" in errors:
            timeout_urls.append(url)
        elif "DNS" in errors:
            dns_urls.append(url)
        elif "SSL" in errors:
            ssl_urls.append(url)

        # 假成功：标记为success/partial但搜索结果为空
        if status in ("success", "partial"):
            s = r.get("stages", {})
            search_count = r.get("search_count", 0)
            if s.get("search") and search_count == 0:
                false_success_urls.append(url)

    print(f"\n分类:")
    print(f"  超时(45s): {len(timeout_urls)}")
    print(f"  DNS死站: {len(dns_urls)}")
    print(f"  SSL错误: {len(ssl_urls)}")
    print(f"  假成功(搜索空): {len(false_success_urls)}")

    # 获取真机源确认
    all_sources = await client.get_book_sources()
    device_urls = set(s.get("bookSourceUrl", "") for s in all_sources)
    print(f"\n真机书源数: {len(all_sources)}")

    # 要删除的URL：超时 + DNS + SSL
    to_delete = set()
    for url in timeout_urls:
        if url in device_urls:
            to_delete.add(url)
    for url in dns_urls:
        if url in device_urls:
            to_delete.add(url)
    for url in ssl_urls:
        if url in device_urls:
            to_delete.add(url)

    print(f"真机中存在需删除的: {len(to_delete)}")

    # 分批删除
    if to_delete:
        deleted = 0
        batch_size = 100
        to_delete_list = list(to_delete)
        for i in range(0, len(to_delete_list), batch_size):
            batch = to_delete_list[i:i + batch_size]
            payload = [{"bookSourceUrl": u} for u in batch]
            ok = await client.delete_book_sources(payload)
            deleted += len(batch)
            print(f"  删除进度: {min(i + batch_size, len(to_delete_list))}/{len(to_delete_list)}")
        print(f"\n真机删除: {deleted} 个不可用源")

    # 验证删除结果
    remaining = await client.get_book_sources()
    print(f"删除后真机书源数: {len(remaining)}")

    # 保存删除清单（供数据库标记用）
    delete_report = {
        "timestamp": datetime.now().isoformat(),
        "deleted_from_device": len(to_delete),
        "device_count_before": len(all_sources),
        "device_count_after": len(remaining),
        "timeout_urls": timeout_urls,
        "dns_urls": dns_urls,
        "ssl_urls": ssl_urls,
        "false_success_urls": false_success_urls,
    }

    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"cleanup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(delete_report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    # 尝试数据库标记
    try:
        from legado_client.storage.database import get_session
        from legado_client.storage.models import Source

        session = get_session()
        marked = 0
        for url in to_delete:
            source = session.query(Source).filter(Source.url == url).first()
            if source:
                source.last_test_status = "timeout_deleted"
                marked += 1
        session.commit()
        session.close()
        print(f"数据库标记: {marked} 个源")
    except Exception as e:
        print(f"数据库不可用，跳过标记: {e}")
        # 保存待标记列表
        with open(os.path.join(SCRIPTS_DIR, "reports", "pending_db_mark.json"), "w", encoding="utf-8") as f:
            json.dump(list(to_delete), f, ensure_ascii=False)
        print(f"待标记URL已保存到 reports/pending_db_mark.json")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
