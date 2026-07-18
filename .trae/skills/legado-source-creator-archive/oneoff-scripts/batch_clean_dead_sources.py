#!/usr/bin/env python3
"""批量清理真机死源：域名不可达→真机删除→数据库标记废弃。

用法:
  # 仅检查（不删除不标记）
  python batch_clean_dead_sources.py

  # 检查 + 真机删除死源
  python batch_clean_dead_sources.py --delete

  # 检查 + 真机删除 + 数据库标记
  python batch_clean_dead_sources.py --delete --mark-db

  # 只清理书源
  python batch_clean_dead_sources.py --book --no-rss --delete

  # 自定义超时和并发
  python batch_clean_dead_sources.py --timeout 5.0 --workers 50 --delete
"""
import asyncio
import json
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

HTTP_BASE = "http://127.0.0.1:1122"
DEAD_REPORT = os.path.join(SCRIPTS_DIR, "reports", "dead-sources-report.json")


def check_domain_alive(url: str, timeout: float = 3.0) -> bool:
    """DNS + TCP 80/443 可达性检查。"""
    try:
        if "://" not in url:
            url = f"http://{url}"
        domain = urlparse(url).hostname
        if not domain:
            return False
        ip = socket.getaddrinfo(domain, None, socket.AF_INET)[0][4][0]
        for port in (443, 80):
            try:
                sock = socket.create_connection((ip, port), timeout=timeout)
                sock.close()
                return True
            except (OSError, socket.timeout):
                continue
        return False
    except (socket.gaierror, OSError, UnicodeError, ValueError):
        return False


async def get_all_sources(source_type: str) -> List[Dict]:
    """从真机获取全部源。"""
    import httpx

    api = (
        f"{HTTP_BASE}/getBookSources"
        if source_type == "book"
        else f"{HTTP_BASE}/getRssSources"
    )
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.get(api)
        data = resp.json()
        # Legado ReturnData 格式: {isSuccess, errorMsg, data}
        if isinstance(data, dict) and "data" in data:
            return data["data"] if isinstance(data["data"], list) else []
        return data if isinstance(data, list) else []


async def delete_sources_from_device(
    dead_source_objects: List[Dict], source_type: str
) -> bool:
    """从真机删除源。

    Legado API deleteBookSources/deleteRssSources 接受完整源对象列表，
    非 URL 列表。参考 LegadoWebClient.delete_book_sources。
    """
    import httpx

    api = (
        f"{HTTP_BASE}/deleteBookSources"
        if source_type == "book"
        else f"{HTTP_BASE}/deleteRssSources"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(api, json=dead_source_objects)
        if resp.status_code != 200:
            return False
        try:
            result = resp.json()
            if isinstance(result, dict):
                return result.get("isSuccess", True)
            return True
        except (json.JSONDecodeError, ValueError):
            return resp.status_code == 200


async def mark_dead_in_db(dead_urls: Set[str], source_type: str) -> int:
    """在数据库中标记死源。"""
    from datetime import datetime

    from legado_client.storage.database import get_session_factory, init_db
    from legado_client.storage.models import Source
    from sqlalchemy import update

    db_ok = await init_db()
    if not db_ok:
        print("  ⚠ 数据库不可用，跳过标记")
        return 0

    sf = get_session_factory()
    if sf is None:
        print("  ⚠ 数据库会话工厂为空，跳过标记")
        return 0

    async with sf() as session:
        stmt = (
            update(Source)
            .where(Source.source_url.in_(dead_urls))
            .where(Source.source_type == source_type)
            .values(
                enabled=False,
                last_test_status="error",
                last_test_stage="domain_dead",
                last_test_at=datetime.utcnow(),
                test_detail={
                    "reason": "domain_unreachable",
                    "cleaned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="批量清理真机死源")
    parser.add_argument("--book", action="store_true", default=True, help="清理书源")
    parser.add_argument("--no-book", dest="book", action="store_false", help="不清理书源")
    parser.add_argument("--rss", action="store_true", default=True, help="清理订阅源")
    parser.add_argument("--no-rss", dest="rss", action="store_false", help="不清理订阅源")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="真机删除死源（默认只检查不删除）",
    )
    parser.add_argument(
        "--mark-db", action="store_true", help="标记数据库中死源"
    )
    parser.add_argument(
        "--timeout", type=float, default=3.0, help="域名检查超时秒数"
    )
    parser.add_argument(
        "--workers", type=int, default=100, help="并发检查线程数"
    )
    args = parser.parse_args()

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "delete_from_device": args.delete,
            "mark_db": args.mark_db,
            "timeout": args.timeout,
            "workers": args.workers,
        },
        "book": {},
        "rss": {},
    }

    source_types = (["book"] if args.book else []) + (["rss"] if args.rss else [])
    if not source_types:
        print("未指定任何源类型，退出")
        return

    for source_type in source_types:
        print(f"\n{'=' * 60}")
        print(f"处理 {source_type} 源")
        print(f"{'=' * 60}")

        # 1. 获取全部源
        print(f"[1/4] 获取真机 {source_type} 源列表...")
        sources = await get_all_sources(source_type)
        url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
        name_key = "bookSourceName" if source_type == "book" else "sourceName"
        total = len(sources)
        print(f"  共 {total} 个源")

        if total == 0:
            print("  无源可检查，跳过")
            report[source_type] = {"total": 0, "alive": 0, "dead": 0, "dead_rate": "0.0%", "dead_urls": []}
            continue

        # 2. 域名可达性检查
        print(
            f"[2/4] 域名可达性检查 ({args.workers} 线程, {args.timeout}s 超时)..."
        )
        alive_urls: Set[str] = set()
        dead_urls: Set[str] = set()
        # 保留 URL -> 源对象映射，用于后续删除
        url_to_source: Dict[str, Dict] = {}

        def check(s):
            url = s.get(url_key, "")
            return url, check_domain_alive(url, args.timeout)

        for s in sources:
            url = s.get(url_key, "")
            if url:
                url_to_source[url] = s

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(check, s): s
                for s in sources
                if s.get(url_key)
            }
            done = 0
            total_to_check = len(futures)
            for future in as_completed(futures):
                done += 1
                url, is_alive = future.result()
                if is_alive:
                    alive_urls.add(url)
                else:
                    dead_urls.add(url)
                if done % 2000 == 0 or done == total_to_check:
                    print(
                        f"  {done}/{total_to_check} 已检查, "
                        f"存活: {len(alive_urls)}, 死亡: {len(dead_urls)}"
                    )

        dead_pct = len(dead_urls) / total * 100 if total else 0
        print(f"  结果: {len(alive_urls)} 存活, {len(dead_urls)} 死亡 ({dead_pct:.1f}%)")

        # 3. 真机删除
        if args.delete and dead_urls:
            dead_source_objects = [
                url_to_source[url] for url in dead_urls if url in url_to_source
            ]
            print(f"[3/4] 从真机删除 {len(dead_source_objects)} 个死源...")
            success = await delete_sources_from_device(dead_source_objects, source_type)
            print(f"  {'✅ 成功' if success else '❌ 失败'}")
        else:
            reason = "无死源" if not dead_urls else "使用 --delete 启用"
            print(f"[3/4] 跳过真机删除（{reason}）")

        # 4. 数据库标记
        if args.mark_db and dead_urls:
            print(f"[4/4] 在数据库标记 {len(dead_urls)} 个死源...")
            count = await mark_dead_in_db(dead_urls, source_type)
            print(f"  标记了 {count} 条记录")
        else:
            reason = "使用 --mark-db 启用" if dead_urls else "无死源"
            print(f"[4/4] 跳过数据库标记（{reason}）")

        report[source_type] = {
            "total": total,
            "alive": len(alive_urls),
            "dead": len(dead_urls),
            "dead_rate": f"{dead_pct:.1f}%",
            "dead_urls": sorted(dead_urls)[:100],  # 只存前100个避免报告过大
        }

    # 保存报告
    os.makedirs(os.path.dirname(DEAD_REPORT), exist_ok=True)
    with open(DEAD_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {DEAD_REPORT}")


if __name__ == "__main__":
    asyncio.run(main())
