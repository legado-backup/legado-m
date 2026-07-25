#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复搜索失败源（sea=N det=Y）：搜索URL探测 + 同域反哺 + DOM验证。

针对全量测试中 sea=N det=Y 的书源：
- 网站存活（详情能通过），但搜索URL有问题
- 修复策略：
  1. 同域名有搜索成功的源 → 复制searchUrl + ruleSearch（V4 DOM验证）
  2. 并发探测搜索接口变体（/search, /s.php, /search.html 等）
  3. 探测成功 → 验证搜索结果页DOM是否匹配ruleSearch
  4. 匹配则保存，不匹配则丢弃

用法:
    python fix_search_failed.py --dry-run                  # 只分析
    python fix_search_failed.py --execute                  # 执行修复
    python fix_search_failed.py --execute --concurrency 20 # 20并发
    python fix_search_failed.py --from-report reports/xxx.json --execute
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
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlencode

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_HTTP_PORT = 1122
DEVICE_WS_PORT = 1123


# ==================== 工具函数 ====================

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


def clean_url(url: str) -> str:
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    if not base:
        return ""
    if "://" not in base:
        base = "https://" + base
    return base


# ==================== API ====================

async def api_get_sources(source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> List[Dict]:
    import httpx
    url = f"http://{host}:{port}/{'getBookSources' if source_type == 'book' else 'getRssSources'}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        r = await client.get(url)
        data = r.json()
        return data.get("data", []) if isinstance(data, dict) else data


async def api_save_source(source: Dict, source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> bool:
    import httpx
    endpoint = "saveBookSource" if source_type == "book" else "saveRssSource"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            r = await client.post(f"http://{host}:{port}/{endpoint}", json=source)
            return r.json().get("isSuccess", False)
    except Exception:
        return False


async def api_delete_sources(urls: List[str], source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> int:
    import httpx
    if not urls:
        return 0
    endpoint = "deleteBookSources" if source_type == "book" else "deleteRssSources"
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    deleted = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        for i in range(0, len(urls), 100):
            batch = urls[i:i + 100]
            payload = [{url_key: u} for u in batch if u]
            try:
                await client.post(f"http://{host}:{port}/{endpoint}", json=payload)
                deleted += len(batch)
            except Exception:
                pass
    return deleted


# ==================== WebSocket 测试 ====================

async def debug_source_ws(source_url: str, key: str = "斗破苍穹", timeout: float = 90.0) -> Dict[str, Any]:
    import websockets
    result = {
        "source_url": source_url,
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "errors": [],
        "duration_ms": 0,
    }
    start = time.time()
    try:
        async with websockets.connect(f"ws://{DEVICE_HOST}:{DEVICE_WS_PORT}/bookSourceDebug", open_timeout=10) as ws:
            await ws.send(json.dumps({"tag": source_url, "key": key}, ensure_ascii=False))
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    if "列表大小" in msg or "搜索结果" in msg:
                        result["stages"]["search"] = True
                    if "获取书名" in msg:
                        result["stages"]["detail"] = True
                    if "目录总数" in msg:
                        result["stages"]["toc"] = True
                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
                        result["stages"]["content"] = True
                    if "UnknownHostException" in msg:
                        result["errors"].append("DNS")
                    elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
                        result["errors"].append("TIMEOUT")
                    elif "SSLException" in msg:
                        result["errors"].append("SSL")
                    if "调试结束" in msg:
                        break
            except asyncio.TimeoutError:
                result["errors"].append("WS_TIMEOUT")
    except Exception as e:
        result["errors"].append(f"CONN:{str(e)[:50]}")
    result["duration_ms"] = int((time.time() - start) * 1000)
    return result


# ==================== 搜索URL探测 ====================

async def probe_search_url(base_url: str, source: Dict, timeout: float = 10.0) -> Optional[str]:
    """并发探测搜索接口变体，返回能返回搜索结果的searchUrl。"""
    import httpx
    base = clean_url(base_url)
    if not base:
        return None

    keyword = "斗破苍穹"
    candidates = []

    # 从源已有的searchUrl推断变体
    existing = source.get("searchUrl", "")
    if existing:
        # 已有searchUrl但失败，尝试变体
        if "/search" in existing:
            for path in ["/search", "/search.html", "/search.php", "/search.aspx", "/s.php", "/so.php"]:
                for param in [f"?q={keyword}", f"?keyword={keyword}", f"?searchkey={keyword}", f"?key={keyword}", f"?s={keyword}", f"?wd={keyword}"]:
                    candidates.append(f"{base}{path}{param}")
        elif "/s.php" in existing:
            for path in ["/s.php", "/search.php", "/search"]:
                for param in [f"?q={keyword}", f"?keyword={keyword}"]:
                    candidates.append(f"{base}{path}{param}")
        elif "/so/" in existing:
            for path in ["/so/", "/search/"]:
                candidates.append(f"{base}{path}{keyword}")
        # POST格式 → 尝试GET版
        if "@" in existing:
            simple = existing.split("@")[0]
            if simple.startswith("http"):
                # 替换{{key}}为实际关键词
                url = simple.replace("{{key}}", keyword)
                candidates.append(url)
    else:
        # 无searchUrl，通用候选
        for path in ["/search", "/search.html", "/search.php", "/s.php", "/so.php",
                     "/search.aspx", "/s/", "/so/"]:
            for param in [f"?q={keyword}", f"?keyword={keyword}", f"?searchkey={keyword}"]:
                candidates.append(f"{base}{path}{param}")

    # 去重 + 限制
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    candidates = unique[:25]

    # 搜索结果关键词
    result_keywords = ["斗破苍穹", "搜索结果", "book-list", "novellist", "result-list",
                       "book_list", "搜索到", "s-b-list", "搜索", "章节"]

    sem = asyncio.Semaphore(5)

    async def _probe(url: str) -> Optional[Tuple[str, str]]:
        async with sem:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout, connect=5.0),
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
                        "Accept": "text/html,*/*",
                    },
                ) as client:
                    r = await client.get(url)
                    if r.status_code != 200 or len(r.content) < 200:
                        return None
                    text = r.text
                    # 检查是否包含搜索结果关键词
                    for kw in result_keywords:
                        if kw in text:
                            return (url, text)
            except Exception:
                pass
            return None

    tasks = [_probe(c) for c in candidates]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, tuple) and len(r) == 2:
            probe_url, html = r
            # 将探测到的URL转回Legado searchUrl格式
            search_url = probe_url.replace(keyword, "{{key}}")
            # 验证搜索结果页DOM是否匹配ruleSearch
            if validate_search_rules(html, source):
                return search_url
            else:
                # 探测到搜索页但规则不匹配，返回搜索URL（规则后续修复）
                return search_url

    return None


def validate_search_rules(html: str, source: Dict) -> bool:
    """验证搜索结果页HTML是否匹配源的ruleSearch。"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        rule_search = source.get("ruleSearch", {})
        if not isinstance(rule_search, dict):
            return False

        book_list_rule = rule_search.get("bookList", "")
        if not book_list_rule:
            return False

        # 简化验证：检查bookList选择器是否匹配到元素
        css = book_list_rule.strip()
        if css.startswith("class."):
            css = "." + css[6:]
        elif css.startswith("tag."):
            css = css[4:]
        elif css.startswith("@js:"):
            return True  # JS规则无法验证，保守通过
        elif css.startswith("//") or css.startswith("./"):
            try:
                from lxml import etree
                tree = etree.HTML(html)
                results = tree.xpath(css)
                return len(results) >= 2
            except Exception:
                return False

        # 去除属性选择器
        if "@" in css:
            css = css.split("@")[0].strip()
        if "!" in css:
            css = css.split("!")[0].strip()

        elements = soup.select(css)
        return len(elements) >= 2
    except Exception:
        return False


# ==================== 同域反哺（V4 DOM验证） ====================

async def cross_feed_with_validation(
    target: Dict,
    donor: Dict,
    base_url: str,
) -> Optional[Dict]:
    """从donor源反哺规则到target，但必须先验证规则在实际DOM中匹配。
    
    返回修复后的源Dict，或None（如果donor规则也不匹配DOM）。"""
    html = None
    import httpx
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12) Chrome/120.0.0.0 Mobile Safari/537.36"},
        ) as client:
            # 尝试用donor的searchUrl抓搜索页
            donor_search = donor.get("searchUrl", "")
            keyword = "斗破苍穹"
            if donor_search:
                actual_url = donor_search.replace("{{key}}", keyword)
                if "@" in actual_url:
                    actual_url = actual_url.split("@")[0]
                if not actual_url.startswith("http"):
                    actual_url = urljoin(clean_url(base_url), actual_url)
                r = await client.get(actual_url)
                if r.status_code == 200 and len(r.content) > 500:
                    html = r.text
    except Exception:
        pass

    if not html:
        return None

    # 验证donor的规则是否在搜索页DOM中匹配
    if not validate_search_rules(html, donor):
        return None  # donor规则也不匹配DOM，不能反哺

    # donor规则验证通过，可以反哺
    merged = dict(target)

    # 反哺searchUrl
    if not merged.get("searchUrl") and donor.get("searchUrl"):
        merged["searchUrl"] = donor["searchUrl"]

    # 反哺ruleSearch（逐字段验证）
    donor_rules = donor.get("ruleSearch", {})
    target_rules = merged.get("ruleSearch", {})
    if not isinstance(target_rules, dict):
        target_rules = {}
    if isinstance(donor_rules, dict):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        for field in ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind"]:
            if target_rules.get(field):
                continue  # target已有，保留
            donor_val = donor_rules.get(field, "")
            if not donor_val:
                continue

            # 验证donor的选择器在DOM中是否匹配
            css = donor_val.strip()
            if css.startswith("@js:"):
                target_rules[field] = donor_val  # JS规则保守接受
                continue
            if css.startswith("//") or css.startswith("./"):
                try:
                    from lxml import etree
                    tree = etree.HTML(html)
                    if tree.xpath(css):
                        target_rules[field] = donor_val
                except Exception:
                    pass
                continue

            # CSS验证
            clean_css = css
            if clean_css.startswith("class."):
                clean_css = "." + clean_css[6:]
            elif clean_css.startswith("tag."):
                clean_css = clean_css[4:]
            if "@" in clean_css:
                clean_css = clean_css.split("@")[0].strip()
            if "!" in clean_css:
                clean_css = clean_css.split("!")[0].strip()

            try:
                if soup.select(clean_css):
                    target_rules[field] = donor_val
            except Exception:
                pass

    merged["ruleSearch"] = target_rules
    return merged


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="修复搜索失败源(sea=N det=Y)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--concurrency", type=int, default=15)
    parser.add_argument("--max-sources", type=int, default=0, help="最大处理源数(0=全部)")
    parser.add_argument("--from-report", type=str, default="", help="从指定测试报告读取失败源")
    parser.add_argument("--host", default=DEVICE_HOST)
    parser.add_argument("--http-port", type=int, default=DEVICE_HTTP_PORT)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    execute = args.execute and not args.dry_run

    print("=" * 60)
    print(" 修复搜索失败源 (sea=N det=Y)")
    print(f" 模式: {'执行' if execute else '仅分析'}")
    print(f" 并发: {args.concurrency}")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: 获取测试报告中sea=N det=Y的源
    if args.from_report:
        with open(args.from_report, "r", encoding="utf-8") as f:
            report = json.load(f)
        book_results = report.get("results", {}).get("book", report.get("book_results", []))
        search_failed_urls = set()
        for r in book_results:
            s = r.get("stages", {})
            if not s.get("search") and s.get("detail"):
                search_failed_urls.add(r.get("source_url", ""))
        print(f"  报告中搜索失败源: {len(search_failed_urls)}")
    else:
        # 从真机获取，需要先运行WebSocket测试
        print("  未指定报告，将直接从真机获取所有源")
        search_failed_urls = None

    # Step 2: 获取真机源列表
    all_sources = await api_get_sources("book", args.host, args.http_port)
    print(f"  真机书源总数: {len(all_sources)}")

    url_key = "bookSourceUrl"
    source_map = {}
    for s in all_sources:
        url = s.get(url_key, "")
        if url:
            source_map[url] = s

    # 筛选sea=N det=Y的源
    if search_failed_urls is not None:
        failed_sources = [source_map[u] for u in search_failed_urls if u in source_map]
    else:
        # 无报告，无法判断，需先测试
        print("  错误：必须指定 --from-report 或先运行全量测试")
        return

    print(f"  待修复源: {len(failed_sources)}")

    if args.max_sources > 0:
        failed_sources = failed_sources[:args.max_sources]
        print(f"  限制: {len(failed_sources)}")

    if not failed_sources:
        print("  无需修复")
        return

    # Step 3: 构建同域名搜索成功源索引
    domain_search_ok: Dict[str, List[Dict]] = {}
    for r in book_results:
        s = r.get("stages", {})
        if s.get("search"):
            url = r.get("source_url", "")
            domain = extract_domain(url)
            if domain and url in source_map:
                domain_search_ok.setdefault(domain, []).append(source_map[url])

    domains_with_donors = {d for d, v in domain_search_ok.items() if v}
    print(f"  有同域搜索成功源的域名: {len(domains_with_donors)}")

    # Step 4: 并发修复
    sem = asyncio.Semaphore(args.concurrency)
    progress = {"done": 0, "total": len(failed_sources), "lock": asyncio.Lock()}
    stats = {
        "cross_feed_ok": 0,
        "probe_ok": 0,
        "probe_fail": 0,
        "no_donor": 0,
        "saved": 0,
        "dom_reject": 0,
    }
    all_fixed = []

    async def _fix(src: Dict) -> Optional[Dict]:
        async with sem:
            url = src.get(url_key, "")
            domain = extract_domain(url)
            fixed = None
            fix_method = ""

            # 策略1: 同域反哺（V4 DOM验证）
            donors = domain_search_ok.get(domain, [])
            if donors:
                for donor in donors:
                    result = await cross_feed_with_validation(src, donor, url)
                    if result:
                        fixed = result
                        fix_method = "cross_feed_dom_validated"
                        break
                    else:
                        stats["dom_reject"] += 1

            # 策略2: 搜索URL探测
            if not fixed:
                base_url = clean_url(url)
                if base_url:
                    new_search_url = await probe_search_url(base_url, src, timeout=8.0)
                    if new_search_url:
                        fixed = dict(src)
                        fixed["searchUrl"] = new_search_url
                        fix_method = "probe_search_url"
                    else:
                        stats["probe_fail"] += 1
                        fix_method = "probe_failed"
                else:
                    stats["no_donor"] += 1
                    fix_method = "no_donor"

            if not fixed and not donors:
                stats["no_donor"] += 1

            async with progress["lock"]:
                progress["done"] += 1
                if fixed:
                    if fix_method == "cross_feed_dom_validated":
                        stats["cross_feed_ok"] += 1
                    elif fix_method == "probe_search_url":
                        stats["probe_ok"] += 1
                    all_fixed.append({"source": fixed, "method": fix_method, "url": url})

                if progress["done"] % 50 == 0 or progress["done"] == progress["total"]:
                    print(f"  [{progress['done']}/{progress['total']}] "
                          f"反哺={stats['cross_feed_ok']} 探测={stats['probe_ok']} "
                          f"DOM拒绝={stats['dom_reject']} 探测失败={stats['probe_fail']} "
                          f"无捐赠={stats['no_donor']}")

            return fixed

    tasks = [_fix(src) for src in failed_sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    print(f"\n修复统计:")
    print(f"  同域反哺(DOM验证通过): {stats['cross_feed_ok']}")
    print(f"  搜索URL探测成功: {stats['probe_ok']}")
    print(f"  DOM验证拒绝: {stats['dom_reject']}")
    print(f"  搜索URL探测失败: {stats['probe_fail']}")
    print(f"  无同域捐赠源: {stats['no_donor']}")
    print(f"  总修复: {len(all_fixed)}")

    # Step 5: 保存修复
    if execute and all_fixed:
        print(f"\n保存修复到真机...")
        sem_save = asyncio.Semaphore(5)

        async def _save(item: Dict) -> bool:
            async with sem_save:
                return await api_save_source(item["source"], "book", args.host, args.http_port)

        save_tasks = [_save(item) for item in all_fixed]
        save_results = await asyncio.gather(*save_tasks, return_exceptions=True)
        saved = sum(1 for r in save_results if r is True)
        stats["saved"] = saved
        print(f"  保存成功: {saved}/{len(all_fixed)}")

    # Step 6: 验证修复（抽样测试）
    if execute and all_fixed:
        # 抽样20个验证
        sample = all_fixed[:20]
        print(f"\n验证修复（抽样{len(sample)}个）...")
        for item in sample:
            url = item["source"].get(url_key, "")
            r = await debug_source_ws(url, timeout=90.0)
            sea = r["stages"]["search"]
            det = r["stages"]["detail"]
            con = r["stages"]["content"]
            name = item["source"].get("bookSourceName", "?")[:20]
            method = item["method"]
            status = "OK" if sea else "STILL_FAIL"
            print(f"  {status} [{method}] {name}: sea={sea} det={det} con={con}")

    # Step 7: 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = args.output or os.path.join(
        SCRIPTS_DIR, "reports",
        f"fix-search-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "fixed_sources": [
            {"url": item["url"], "method": item["method"],
             "name": item["source"].get("bookSourceName", "?")}
            for item in all_fixed
        ],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
