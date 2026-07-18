#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成功源质量审查：检查CF盾、验证码、登录拦截、假成功等问题。

对已标记为success/partial的源，深度分析调试日志中的可疑信号。
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


# CF盾检测关键词
CF_INDICATORS = [
    "cf-challenge", "CloudFlare", "cf-browser-verification",
    "chk_jschl", "jschl_vc", "cf_chl_opt", "challenge-platform",
    "Enable JavaScript", "Just a moment", "checking your browser",
    "ray ID", "cf-ray",
]

# 验证码检测关键词
CAPTCHA_INDICATORS = [
    "验证码", "captcha", "verify", "recaptcha", "hcaptcha",
    "geetest", "极验", "slideVerify", "请输入验证码",
    "请完成验证", "安全验证", "人机验证",
]

# 登录拦截检测关键词
LOGIN_INDICATORS = [
    "需要登录", "请先登录", "loginCheckJs", "请登录后",
    "登录后查看", "VIP", "会员", "付费章节",
    "本章未购买",
]

# 假成功检测：列表大小=0但标记为成功
EMPTY_RESULT_INDICATORS = [
    "列表大小:0", "列表为空", "TocEmptyException",
    "正文为空", "content is empty",
]


async def main():
    print("=" * 60)
    print(f" 成功源质量审查")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    client = LegadoWebClient(host="127.0.0.1", port=1122)

    # 加载全量测试报告
    report_path = os.path.join(SCRIPTS_DIR, "reports", "full-fix-20260628.json")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    book_results = report.get("results", {}).get("book", [])

    # 筛选成功和部分成功的源
    success_urls = set()
    partial_urls = set()
    for r in book_results:
        if r["status"] == "success":
            success_urls.add(r.get("source_url", ""))
        elif r["status"] == "partial":
            partial_urls.add(r.get("source_url", ""))

    print(f" 成功源: {len(success_urls)}")
    print(f" 部分成功源: {len(partial_urls)}")

    # 获取真机源
    all_sources = await client.get_book_sources()
    source_map = {s.get("bookSourceUrl", ""): s for s in all_sources}
    print(f" 真机书源总数: {len(all_sources)}")

    # 对成功+部分成功源做深度调试，检查CF/验证码/登录
    target_urls = list(success_urls | partial_urls)
    print(f" 待审查源: {len(target_urls)}")

    # 抽样测试（先测100个）
    import random
    sample_size = min(100, len(target_urls))
    sample_urls = random.sample(target_urls, sample_size) if len(target_urls) > sample_size else target_urls
    print(f" 抽样: {sample_size} 个")

    # 审查结果
    audit_results = {
        "cf_shield": [],      # CF盾拦截
        "captcha": [],        # 验证码
        "login_required": [], # 需要登录
        "empty_content": [],  # 假成功（空内容）
        "vip_only": [],       # VIP付费
        "clean": [],          # 真正正常
    }

    sem = asyncio.Semaphore(10)
    progress = {"done": 0, "lock": asyncio.Lock()}

    async def _audit(url: str):
        if url not in source_map:
            return
        source = source_map[url]
        async with sem:
            try:
                logs = await asyncio.wait_for(
                    client.ws_debug_book_source(source, "斗破苍穹"),
                    timeout=60,
                )
                all_logs = " ".join(logs).lower()
                name = source.get("bookSourceName", "?")

                # 检测各种问题
                issues = []

                # CF盾
                has_cf = any(ind.lower() in all_logs for ind in CF_INDICATORS)
                if has_cf:
                    issues.append("CF_SHIELD")
                    audit_results["cf_shield"].append({"url": url, "name": name})

                # 验证码
                has_captcha = any(ind.lower() in all_logs for ind in CAPTCHA_INDICATORS)
                if has_captcha:
                    issues.append("CAPTCHA")
                    audit_results["captcha"].append({"url": url, "name": name})

                # 登录
                has_login = any(ind.lower() in all_logs for ind in LOGIN_INDICATORS)
                if has_login:
                    issues.append("LOGIN")
                    audit_results["login_required"].append({"url": url, "name": name})

                # 空内容
                has_empty = any(ind.lower() in all_logs for ind in EMPTY_RESULT_INDICATORS)
                if has_empty:
                    issues.append("EMPTY")
                    audit_results["empty_content"].append({"url": url, "name": name})

                if not issues:
                    audit_results["clean"].append({"url": url, "name": name})

            except Exception as e:
                pass

            async with progress["lock"]:
                progress["done"] += 1
                if progress["done"] % 20 == 0 or progress["done"] == sample_size:
                    print(f"  [{progress['done']}/{sample_size}]")

    await asyncio.gather(*[_audit(url) for url in sample_urls])

    # 输出审查结果
    print(f"\n{'='*60}")
    print(f" 审查结果 (抽样 {sample_size} 个):")
    print(f"{'='*60}")
    print(f"  真正正常: {len(audit_results['clean'])} ({len(audit_results['clean'])/sample_size*100:.1f}%)")
    print(f"  CF盾拦截: {len(audit_results['cf_shield'])}")
    print(f"  验证码拦截: {len(audit_results['captcha'])}")
    print(f"  需要登录: {len(audit_results['login_required'])}")
    print(f"  假成功(空内容): {len(audit_results['empty_content'])}")
    print(f"  VIP/付费: {len(audit_results['vip_only'])}")

    # 输出有问题的源
    for category, items in audit_results.items():
        if category == "clean" or not items:
            continue
        print(f"\n  --- {category} ---")
        for item in items[:10]:
            print(f"    {item['name']} ({item['url'][:50]})")
        if len(items) > 10:
            print(f"    ... 还有 {len(items)-10} 个")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"audit-quality-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "sample_size": sample_size,
            "total_success_partial": len(target_urls),
            "audit_results": {k: len(v) for k, v in audit_results.items()},
            "details": audit_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {report_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
