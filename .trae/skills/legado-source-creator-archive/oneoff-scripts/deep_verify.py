#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真正可用源深度验证：对search_count>0的620个源做全阶段验证。

目标：
1. 验证搜索结果是否真实（不是CF盾/拦截页）
2. 验证详情页是否真正提取到书名/作者
3. 验证目录是否真正获取到章节
4. 验证正文是否真正可读
5. 识别CF盾/验证码/登录拦截
"""
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


# 可疑信号
SUSPECT_PATTERNS = {
    "cf_shield": [
        "cf-challenge", "cloudflare", "cf-browser-verification",
        "just a moment", "checking your browser", "challenge-platform",
        "cf_chl_opt", "cf-ray",
    ],
    "captcha": [
        "验证码", "captcha", "verify", "recaptcha", "hcaptcha",
        "geetest", "极验", "人机验证", "请完成验证",
    ],
    "login": [
        "需要登录", "请先登录", "loginCheckJs", "登录后查看",
        "请登录", "vip", "会员", "付费章节", "本章未购买",
    ],
    "empty": [
        "列表大小:0", "列表为空", "tocemptyexception",
        "正文为空", "content is empty",
    ],
    "block": [
        "403", "forbidden", "access denied", "ip被封",
        "请求过于频繁", "访问受限",
    ],
}


def analyze_logs(logs: List[str]) -> Dict:
    """深度分析调试日志。"""
    result = {
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "search_count": 0,
        "toc_count": 0,
        "content_length": 0,
        "suspects": [],
        "has_book_name": False,
        "has_author": False,
        "has_content_text": False,
    }

    all_text = " ".join(logs).lower()

    for msg in logs:
        # 阶段检测
        if "列表大小" in msg or "搜索结果" in msg:
            result["stages"]["search"] = True
            m = re.search(r"列表大小[：:](\d+)", msg)
            if m:
                result["search_count"] = int(m.group(1))

        if "获取书名" in msg or ("书名" in msg and "获取" in msg):
            result["stages"]["detail"] = True
            result["has_book_name"] = True

        if "获取作者" in msg or ("作者" in msg and "获取" in msg):
            result["has_author"] = True

        if "目录总数" in msg or "章节列表" in msg:
            result["stages"]["toc"] = True
            m = re.search(r"目录总数[：:](\d+)", msg)
            if m:
                result["toc_count"] = int(m.group(1))

        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            result["stages"]["content"] = True

        # 正文长度检测
        if "正文长度" in msg:
            m = re.search(r"正文长度[：:](\d+)", msg)
            if m:
                result["content_length"] = int(m.group(1))

    # 可疑信号检测
    for category, keywords in SUSPECT_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in all_text:
                result["suspects"].append(category)
                break

    return result


async def main():
    print("=" * 60)
    print(f" 真正可用源深度验证")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    # 加载全量测试报告
    with open(os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    book_results = report.get("results", {}).get("book", [])

    # 找真正可用的源（search_count > 0）
    usable_urls = []
    for r in book_results:
        if r["status"] in ("success", "partial") and r.get("search_count", 0) > 0:
            usable_urls.append(r.get("source_url", ""))

    print(f" 真正可用源: {len(usable_urls)}")

    # 获取真机源
    all_sources = await client.get_book_sources()
    source_map = {s.get("bookSourceUrl", ""): s for s in all_sources}
    print(f" 真机书源数: {len(all_sources)}")

    # 匹配
    test_sources = [source_map[u] for u in usable_urls if u in source_map]
    print(f" 匹配到: {len(test_sources)}")

    if not test_sources:
        print(" 无需测试")
        await client.close()
        return

    # 并发深度调试
    sem = asyncio.Semaphore(10)
    progress = {"done": 0, "total": len(test_sources), "lock": asyncio.Lock()}
    results = []

    async def _verify(source: Dict) -> Dict:
        async with sem:
            url = source.get("bookSourceUrl", "")
            name = source.get("bookSourceName", "?")
            start = time.time()
            try:
                logs = await asyncio.wait_for(
                    client.ws_debug_book_source(source, "斗破苍穹"),
                    timeout=90,
                )
                analysis = analyze_logs(logs)
                analysis["source_url"] = url
                analysis["source_name"] = name
                analysis["duration_ms"] = int((time.time() - start) * 1000)
                analysis["status"] = "ok"
                results.append(analysis)
            except asyncio.TimeoutError:
                results.append({
                    "source_url": url, "source_name": name,
                    "status": "timeout", "stages": {"search": False, "detail": False, "toc": False, "content": False},
                    "suspects": [], "search_count": 0, "toc_count": 0,
                })
            except Exception as e:
                results.append({
                    "source_url": url, "source_name": name,
                    "status": "error", "stages": {"search": False, "detail": False, "toc": False, "content": False},
                    "suspects": [f"EXCEPTION:{str(e)[:40]}"], "search_count": 0, "toc_count": 0,
                })

            async with progress["lock"]:
                progress["done"] += 1
                if progress["done"] % 50 == 0 or progress["done"] == progress["total"]:
                    print(f"  [{progress['done']}/{progress['total']}]")

    await asyncio.gather(*[_verify(s) for s in test_sources])

    # 汇总结果
    print(f"\n{'='*60}")
    print(f" 深度验证结果:")
    print(f"{'='*60}")

    # 全阶段通过
    full_pass = sum(1 for r in results if all(r.get("stages", {}).values()))
    search_ok = sum(1 for r in results if r.get("stages", {}).get("search"))
    detail_ok = sum(1 for r in results if r.get("stages", {}).get("detail"))
    toc_ok = sum(1 for r in results if r.get("stages", {}).get("toc"))
    content_ok = sum(1 for r in results if r.get("stages", {}).get("content"))

    print(f"  全4阶段通过: {full_pass} ({full_pass/len(results)*100:.1f}%)")
    print(f"  搜索OK: {search_ok}")
    print(f"  详情OK: {detail_ok}")
    print(f"  目录OK: {toc_ok}")
    print(f"  正文OK: {content_ok}")
    print(f"  超时: {sum(1 for r in results if r.get('status') == 'timeout')}")

    # 可疑信号
    suspect_counts = {}
    for r in results:
        for s in r.get("suspects", []):
            suspect_counts[s] = suspect_counts.get(s, 0) + 1

    if suspect_counts:
        print(f"\n  可疑信号:")
        for s, c in sorted(suspect_counts.items(), key=lambda x: -x[1]):
            print(f"    {s}: {c}")

    # 分类
    gold_sources = []  # 全阶段通过，无可疑
    silver_sources = []  # 部分通过，无可疑
    suspect_sources = []  # 有可疑信号
    broken_sources = []  # 超时/错误

    for r in results:
        if r.get("status") != "ok":
            broken_sources.append(r)
        elif r.get("suspects"):
            suspect_sources.append(r)
        elif all(r.get("stages", {}).values()):
            gold_sources.append(r)
        else:
            silver_sources.append(r)

    print(f"\n  金牌源(全通过+无嫌疑): {len(gold_sources)}")
    print(f"  银牌源(部分通过+无嫌疑): {len(silver_sources)}")
    print(f"  嫌疑源(有CF/验证码/登录): {len(suspect_sources)}")
    print(f"  损坏源(超时/错误): {len(broken_sources)}")

    # 嫌疑源详情
    if suspect_sources:
        print(f"\n  === 嫌疑源详情 ===")
        for r in suspect_sources[:20]:
            print(f"    {r.get('source_name','?')} | suspects={r.get('suspects',[])}")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"deep-verify-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tested": len(results),
            "gold": len(gold_sources),
            "silver": len(silver_sources),
            "suspect": len(suspect_sources),
            "broken": len(broken_sources),
            "suspect_counts": suspect_counts,
            "gold_sources": [{"url": r.get("source_url"), "name": r.get("source_name")} for r in gold_sources],
            "suspect_sources": [{"url": r.get("source_url"), "name": r.get("source_name"), "suspects": r.get("suspects")} for r in suspect_sources],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {report_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
