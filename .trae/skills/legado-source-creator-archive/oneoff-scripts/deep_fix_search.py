#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度调试修复：对sea=N det=Y的源做深度调试，分析搜索失败原因，精准修复searchUrl。

策略：
1. 从全量测试报告中提取sea=N det=Y的源（搜索失败但详情OK）
2. 用LegadoWebClient深度调试，获取完整日志
3. 分析搜索失败原因：
   a. searchUrl格式错误 → 修searchUrl
   b. searchUrl缺失 → 探测/生成searchUrl
   c. 搜索规则错误 → 从同域反哺
4. 修复后重试验证

用法:
    python deep_fix_search.py --input reports/full-fix-20260628.json --execute
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, quote

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        base = url.split("#")[0].strip()
        if "://" not in base:
            base = "http://" + base
        return (urlparse(base).hostname or "").lower().replace("www.", "")
    except Exception:
        return ""


async def probe_search_url(base_url: str, source: Dict, timeout: float = 10.0) -> Optional[str]:
    """并发探测搜索URL。"""
    import httpx

    base = base_url.rstrip("/")
    candidates = []

    existing = source.get("searchUrl", "")
    # 从现有searchUrl提取路径模式
    if existing:
        # 提取路径部分
        try:
            parsed = urlparse(existing.split("@js:")[0].split(",")[0].split("##")[0].strip())
            path = parsed.path
            if path and path != "/":
                # 用相同路径但不同参数
                for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}",
                              "?key={{key}}", "?s={{key}}", "?wd={{key}}"]:
                    candidates.append(f"{base}{path}{param}")
        except Exception:
            pass

    # 通用搜索路径
    for path in ["/search", "/search.html", "/s.php", "/search.php",
                 "/so.php", "/search.aspx", "/s/"]:
        for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}", "?wd={{key}}"]:
            candidates.append(f"{base}{path}{param}")

    # 去重
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    candidates = unique[:20]

    sem = asyncio.Semaphore(5)

    async def _probe(url_template: str) -> Optional[str]:
        async with sem:
            test_url = url_template.replace("{{key}}", quote("斗破苍穹"))
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout, connect=5.0),
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                ) as client:
                    r = await client.get(test_url)
                    if r.status_code == 200 and len(r.text) > 500:
                        text = r.text.lower()
                        # 检查是否有搜索结果
                        if any(kw in text for kw in [
                            "斗破", "搜索结果", "book-list", "novellist",
                            "搜索到", "找到", "result", "搜索",
                            "booklist", "item", "card",
                        ]):
                            return url_template
            except Exception:
                pass
            return None

    results = await asyncio.gather(*[_probe(c) for c in candidates])
    for r in results:
        if r:
            return r
    return None


async def main():
    parser = argparse.ArgumentParser(description="深度调试修复搜索失败源")
    parser.add_argument("--input", type=str, required=True, help="全量测试报告JSON")
    parser.add_argument("--execute", action="store_true", help="执行保存到真机")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    print("=" * 60)
    print(f" 深度调试修复: sea=N det=Y 的源")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载全量报告
    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)

    # 提取sea=N det=Y的源
    book_results = report.get("results", {}).get("book", report.get("results", []))
    sea_n_det_y = []
    for r in book_results:
        s = r.get("stages", {})
        if not s.get("search") and s.get("detail") and r.get("status") != "success":
            sea_n_det_y.append(r)

    print(f" sea=N det=Y 的源: {len(sea_n_det_y)}")

    if not sea_n_det_y:
        print(" 无需修复")
        return

    # 获取真机源
    client = LegadoWebClient(host="127.0.0.1", port=1122)
    all_sources = await client.get_book_sources()
    source_map = {s.get("bookSourceUrl", ""): s for s in all_sources}
    print(f" 真机书源总数: {len(all_sources)}")

    # 按域名分组（用于同域反哺）
    domain_groups: Dict[str, List[dict]] = {}
    for s in all_sources:
        domain = extract_domain(s.get("bookSourceUrl", ""))
        if domain:
            domain_groups.setdefault(domain, []).append(s)

    # 分三类处理
    no_search_url = []  # 完全没有searchUrl
    bad_search_url = []  # searchUrl存在但失败
    has_js_search = []  # searchUrl用JS（难修）

    for r in sea_n_det_y:
        url = r.get("source_url", "")
        if url not in source_map:
            continue
        source = source_map[url]
        search_url = source.get("searchUrl", "")

        if not search_url:
            no_search_url.append((r, source))
        elif "@js:" in search_url or "javascript:" in search_url.lower():
            has_js_search.append((r, source))
        else:
            bad_search_url.append((r, source))

    print(f"\n分类:")
    print(f"  无searchUrl: {len(no_search_url)}")
    print(f"  searchUrl存在但失败: {len(bad_search_url)}")
    print(f"  JS脚本searchUrl: {len(has_js_search)}")

    fixed_sources = []
    fix_stats = {
        "no_url_probe": 0,
        "no_url_form": 0,
        "bad_url_probe": 0,
        "bad_url_fix": 0,
        "cross_feed": 0,
        "enable": 0,
        "no_fix": 0,
    }

    # Phase 1: 修复无searchUrl的源 - 探测+表单分析
    if no_search_url:
        print(f"\n=== Phase 1: 修复无searchUrl ({len(no_search_url)}) ===")
        sem = asyncio.Semaphore(10)

        async def _fix_no_url(item):
            r, source = item
            base_url = source.get("bookSourceUrl", "").split("#")[0].strip()
            if not base_url:
                fix_stats["no_fix"] += 1
                return

            # 先探测
            found = await probe_search_url(base_url, source, timeout=10)
            if found:
                source["searchUrl"] = found
                fixed_sources.append(source)
                fix_stats["no_url_probe"] += 1
                return

            # 探测失败，抓首页找搜索表单
            import httpx
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(10, connect=5),
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"},
                ) as hclient:
                    resp = await hclient.get(base_url)
                    if resp.status_code == 200:
                        html = resp.text
                        form = re.search(r'<form[^>]*action="([^"]*)"[^>]*>', html, re.IGNORECASE)
                        if form:
                            action = form.group(1)
                            if not action.startswith("http"):
                                action = urljoin(base_url, action)
                            inp = re.search(r'<input[^>]*name="([^"]*)"', html, re.IGNORECASE)
                            param = inp.group(1) if inp else "q"
                            # 检测method
                            method_match = re.search(r'method="([^"]*)"', form.group(), re.IGNORECASE)
                            method = method_match.group(1).upper() if method_match else "GET"
                            if method == "POST":
                                source["searchUrl"] = f"{action},{param}={{key}}"
                            else:
                                source["searchUrl"] = f"{action}?{param}={{key}}"
                            fixed_sources.append(source)
                            fix_stats["no_url_form"] += 1
                            return
            except Exception:
                pass

            # 同域反哺searchUrl
            domain = extract_domain(base_url)
            same_domain = domain_groups.get(domain, [])
            for donor in same_domain:
                if donor.get("bookSourceUrl") == source.get("bookSourceUrl"):
                    continue
                if donor.get("searchUrl") and "@js:" not in donor.get("searchUrl", ""):
                    source["searchUrl"] = donor["searchUrl"]
                    fixed_sources.append(source)
                    fix_stats["cross_feed"] += 1
                    return

            fix_stats["no_fix"] += 1

        tasks = [_fix_no_url(item) for item in no_search_url]
        await asyncio.gather(*tasks)
        print(f"  探测成功: {fix_stats['no_url_probe']}")
        print(f"  表单发现: {fix_stats['no_url_form']}")
        print(f"  同域反哺: {fix_stats['cross_feed']}")
        print(f"  未修复: {fix_stats['no_fix']}")

    # Phase 2: 修searchUrl存在但失败的源
    if bad_search_url:
        print(f"\n=== Phase 2: 修searchUrl失败 ({len(bad_search_url)}) ===")
        for r, source in bad_search_url:
            search_url = source.get("searchUrl", "")
            base_url = source.get("bookSourceUrl", "").split("#")[0].strip()
            domain = extract_domain(base_url)

            # 常见问题修复
            modified = False

            # 1. searchUrl域名与bookSourceUrl不一致
            if search_url and domain not in search_url.lower():
                # 替换域名
                try:
                    old_domain = extract_domain(search_url)
                    if old_domain and old_domain != domain:
                        source["searchUrl"] = search_url.replace(old_domain, domain)
                        modified = True
                        fix_stats["bad_url_fix"] += 1
                except Exception:
                    pass

            # 2. POST搜索格式问题
            if search_url and ",{" in search_url:
                # 检查POST格式是否正确
                pass  # 暂不处理

            # 3. 探测新URL
            if not modified:
                found = await probe_search_url(base_url, source, timeout=10)
                if found:
                    source["searchUrl"] = found
                    modified = True
                    fix_stats["bad_url_probe"] += 1

            # 4. 同域反哺
            if not modified:
                same_domain = domain_groups.get(domain, [])
                for donor in same_domain:
                    if donor.get("bookSourceUrl") == source.get("bookSourceUrl"):
                        continue
                    if donor.get("searchUrl") and "@js:" not in donor.get("searchUrl", ""):
                        source["searchUrl"] = donor["searchUrl"]
                        modified = True
                        fix_stats["cross_feed"] += 1
                        break

            if not modified:
                fix_stats["no_fix"] += 1
            else:
                fixed_sources.append(source)

        print(f"  searchUrl域名修复: {fix_stats['bad_url_fix']}")
        print(f"  探测成功: {fix_stats['bad_url_probe']}")
        print(f"  同域反哺: {fix_stats['cross_feed']}")
        print(f"  未修复: {fix_stats['no_fix']}")

    # 去重
    seen = set()
    unique = []
    for s in fixed_sources:
        u = s.get("bookSourceUrl", "")
        if u not in seen:
            seen.add(u)
            unique.append(s)
    fixed_sources = unique

    print(f"\n总修复源数: {len(fixed_sources)}")

    # 保存到真机
    if args.execute and fixed_sources:
        saved = 0
        for i in range(0, len(fixed_sources), 50):
            batch = fixed_sources[i:i + 50]
            ok = await client.save_book_sources(batch)
            if ok:
                saved += len(batch)
            else:
                for src in batch:
                    ok2 = await client.save_book_source(src)
                    if ok2:
                        saved += 1
            print(f"  保存: {min(i + 50, len(fixed_sources))}/{len(fixed_sources)}")
        print(f"保存到真机: {saved}/{len(fixed_sources)}")

        # 重试验证
        print(f"\n重试验证 (取前100个)...")
        verified = 0
        improved = 0
        sem = asyncio.Semaphore(10)

        async def _verify(src):
            nonlocal verified, improved
            async with sem:
                try:
                    logs = await asyncio.wait_for(
                        client.ws_debug_book_source(src, "斗破苍穹"),
                        timeout=60,
                    )
                    stages = _parse_stages(logs)
                    if stages["search"]:
                        improved += 1
                    verified += 1
                    if verified % 20 == 0:
                        print(f"  验证: {verified}, 搜索改善: {improved}")
                except Exception:
                    verified += 1

        test_sample = fixed_sources[:100]
        await asyncio.gather(*[_verify(s) for s in test_sample])
        print(f"验证: {verified} 已验证, {improved} 搜索改善")

    # 报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = args.output or os.path.join(
        SCRIPTS_DIR, "reports",
        f"deep-fix-search-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "fix_stats": fix_stats,
        "fixed_count": len(fixed_sources),
        "fixed_sources": [{"url": s.get("bookSourceUrl", ""), "name": s.get("bookSourceName", "?"),
                          "searchUrl": s.get("searchUrl", "")} for s in fixed_sources],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    await client.close()


def _parse_stages(logs):
    stages = {"search": False, "detail": False, "toc": False, "content": False}
    for msg in logs:
        if "列表大小" in msg or "搜索结果" in msg:
            stages["search"] = True
        if "获取书名" in msg:
            stages["detail"] = True
        if "目录总数" in msg or "章节列表" in msg:
            stages["toc"] = True
        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            stages["content"] = True
    return stages


if __name__ == "__main__":
    asyncio.run(main())
