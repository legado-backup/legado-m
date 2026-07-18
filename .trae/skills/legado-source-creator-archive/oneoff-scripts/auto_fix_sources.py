#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高并发自动修复脚本：全量测试 → 分类 → 智能修复 → 反哺合并 → 同步真机。

修复策略（按优先级）：
1. 搜索失败 + 站点存活：
   a. 并发探测网站搜索接口变体（/search → /search.html, /s.php → /search.php 等）
   b. 同域名其他源的反哺（同域有搜索成功的源→复制其searchUrl模板）
   c. HTTP探测搜索页面，分析表单结构
2. 详情/目录/正文规则失败：
   a. 同域名其他源反哺规则
   b. 通用规则模板匹配
3. URL带#的清理：去掉分组标识
4. 超时源：提高超时重试

用法:
    python auto_fix_sources.py --test-all --fix --execute
    python auto_fix_sources.py --test-book 500 --fix --execute
    python auto_fix_sources.py --fix-from reports/xxx.json --execute
    python auto_fix_sources.py --test-all --timeout 90  # 提高超时重测
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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_HTTP_PORT = 1122
DEVICE_WS_PORT = 1123


# ==================== API ====================

async def api_get_sources(source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> List[Dict]:
    import httpx
    url = f"http://{host}:{port}/{'getBookSources' if source_type == 'book' else 'getRssSources'}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        r = await client.get(url)
        data = r.json()
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        elif isinstance(data, list):
            return data
        return []


async def api_get_source(url: str, source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> Optional[Dict]:
    """获取单个源的完整JSON。"""
    import httpx
    endpoint = "getBookSource" if source_type == "book" else "getRssSource"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            r = await client.get(f"http://{host}:{port}/{endpoint}", params={"url": url})
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            elif isinstance(data, dict) and data.get("isSuccess"):
                return data.get("data")
            return None
    except Exception:
        return None


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


# ==================== WebSocket 调试 ====================

async def debug_source_ws(
    source_url: str,
    source_type: str,
    key: str,
    ws_host: str = DEVICE_HOST,
    ws_port: int = DEVICE_WS_PORT,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """并发安全的WebSocket调试。"""
    import websockets

    result: Dict[str, Any] = {
        "source_url": source_url,
        "source_type": source_type,
        "status": "unknown",
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "search_count": 0,
        "toc_count": 0,
        "content_length": 0,
        "errors": [],
        "logs_summary": [],
        "duration_ms": 0,
    }

    path = "/bookSourceDebug" if source_type == "book" else "/rssSourceDebug"
    ws_url = f"ws://{ws_host}:{ws_port}{path}"

    start = time.time()
    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            req = {"tag": source_url, "key": key}
            await ws.send(json.dumps(req, ensure_ascii=False))

            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    if not msg:
                        continue

                    # 保留关键日志（不保存全部，节省内存）
                    if any(kw in msg for kw in [
                        "列表大小", "搜索结果", "获取书名", "目录总数", "正文",
                        "Exception", "错误", "列表为空", "获取成功", "调试结束",
                        "403", "404", "500", "timeout", "UnknownHost", "SSL",
                    ]):
                        result["logs_summary"].append(msg[:300])

                    # 阶段判定
                    if "列表大小" in msg or "搜索结果" in msg:
                        result["stages"]["search"] = True
                        m = re.search(r"列表大小[：:](\d+)", msg)
                        if m:
                            result["search_count"] = int(m.group(1))

                    if "获取书名" in msg or ("书名" in msg and "获取" in msg):
                        result["stages"]["detail"] = True

                    if "目录总数" in msg or "章节列表" in msg:
                        result["stages"]["toc"] = True
                        m = re.search(r"目录总数[：:](\d+)", msg)
                        if m:
                            result["toc_count"] = int(m.group(1))

                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
                        result["stages"]["content"] = True

                    # RSS
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
                        result["stages"]["search"] = True

                    # 错误
                    if "UnknownHostException" in msg:
                        result["errors"].append("DNS")
                    elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
                        result["errors"].append("TIMEOUT")
                    elif "403" in msg or "Forbidden" in msg:
                        result["errors"].append("403")
                    elif "CF" in msg and ("challenge" in msg.lower() or "盾" in msg):
                        result["errors"].append("CF")
                    elif "SSLException" in msg or "SSLHandshakeException" in msg:
                        result["errors"].append("SSL")
                    elif "JSONException" in msg or "JsonSyntaxException" in msg:
                        result["errors"].append("JSON_PARSE")

                    if "调试结束" in msg:
                        break

            except asyncio.TimeoutError:
                result["errors"].append("WS_TIMEOUT")

    except Exception as e:
        err_msg = str(e)
        if "1000" in err_msg and "调试结束" in err_msg:
            pass
        else:
            result["errors"].append(f"CONN_FAIL:{err_msg[:60]}")

    result["duration_ms"] = int((time.time() - start) * 1000)

    stages_passed = sum(1 for v in result["stages"].values() if v)
    if source_type == "book":
        if stages_passed >= 4:
            result["status"] = "success"
        elif stages_passed > 0:
            result["status"] = "partial"
        else:
            result["status"] = "failed"
    else:
        result["status"] = "success" if result["stages"]["search"] else "failed"

    return result


# ==================== 并发批量测试 ====================

async def batch_test(
    sources: List[Dict],
    source_type: str,
    concurrency: int = 10,
    timeout: float = 60.0,
    host: str = DEVICE_HOST,
    ws_port: int = DEVICE_WS_PORT,
) -> List[Dict]:
    """高并发批量WebSocket调试。"""
    sem = asyncio.Semaphore(concurrency)
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    name_key = "bookSourceName" if source_type == "book" else "sourceName"
    progress = {"done": 0, "total": len(sources), "lock": asyncio.Lock()}
    # 累计统计
    stats = {"sea": 0, "det": 0, "toc": 0, "con": 0, "fail": 0}

    async def _test(src: Dict) -> Dict:
        async with sem:
            url = src.get(url_key, "")
            r = await debug_source_ws(
                source_url=url,
                source_type=source_type,
                key="斗破苍穹" if source_type == "book" else "首页",
                ws_host=host,
                ws_port=ws_port,
                timeout=timeout,
            )
            r["source_name"] = src.get(name_key, "?")
            async with progress["lock"]:
                progress["done"] += 1
                s = r["stages"]
                if s["search"]: stats["sea"] += 1
                if s["detail"]: stats["det"] += 1
                if s["toc"]: stats["toc"] += 1
                if s["content"]: stats["con"] += 1
                if r["status"] == "failed": stats["fail"] += 1
                if progress["done"] % 50 == 0 or progress["done"] == progress["total"]:
                    print(f"  [{progress['done']}/{progress['total']}] "
                          f"sea={stats['sea']} det={stats['det']} "
                          f"toc={stats['toc']} con={stats['con']} "
                          f"fail={stats['fail']}")
            return r

    tasks = [_test(src) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤异常
    clean = []
    for r in results:
        if isinstance(r, Exception):
            clean.append({
                "source_url": "", "source_type": source_type,
                "status": "error", "stages": {"search": False, "detail": False, "toc": False, "content": False},
                "errors": [f"EXCEPTION:{str(r)[:60]}"], "duration_ms": 0,
            })
        else:
            clean.append(r)

    return clean


# ==================== 域名工具 ====================

def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        base_url = url.split("#")[0].strip()
        if "://" not in base_url:
            base_url = "http://" + base_url
        return (urlparse(base_url).hostname or "").lower().replace("www.", "")
    except Exception:
        return ""


def clean_url_hash(url: str) -> str:
    """清理URL中的#分组标识。"""
    if not url:
        return url
    base = url.split("#")[0].strip()
    # 保留scheme
    if "://" not in base and base:
        base = "http://" + base
    return base.rstrip("/") + "/"


# ==================== 搜索接口探测 ====================

async def probe_search_url(base_url: str, source: Dict, timeout: float = 10.0) -> Optional[str]:
    """并发探测网站的搜索接口变体，返回可能有效的searchUrl。"""
    import httpx

    base = base_url.rstrip("/")
    domain = extract_domain(base_url)

    # 生成候选searchUrl变体
    candidates = []

    # 1. 从源已有的searchUrl推断
    existing_search = source.get("searchUrl", "")
    if existing_search:
        # 已有searchUrl的变体
        if "/search" in existing_search:
            for path in ["/search", "/search.php", "/search.html",
                         "/s.php", "/so.php", "/search.aspx"]:
                for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}",
                              "?key={{key}}", "?s={{key}}", "?wd={{key}}"]:
                    candidates.append(f"{base}{path}{param}")
            # 如果原searchUrl是POST，也生成GET版本
            if "POST" in existing_search or "method" in existing_search:
                # 尝试GET版
                for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}"]:
                    candidates.append(f"{base}/search{param}")
        elif "/s.php" in existing_search:
            for path in ["/s.php", "/search.php", "/search"]:
                for param in ["?q={{key}}", "?keyword={{key}}"]:
                    candidates.append(f"{base}{path}{param}")
        elif "@js:" in existing_search:
            # JS脚本无法简单探测，跳过
            pass
        else:
            # 其他模式，尝试通用路径
            for path in ["/search", "/search.html", "/s.php"]:
                for param in ["?q={{key}}", "?keyword={{key}}"]:
                    candidates.append(f"{base}{path}{param}")
    else:
        # 无searchUrl，通用候选
        for path in ["/search", "/search.html", "/s.php", "/search.php",
                     "/so.php", "/search.aspx", "/s/"]:
            for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}"]:
                candidates.append(f"{base}{path}{param}")

    # 去重
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)
    candidates = unique_candidates[:20]  # 最多探测20个变体

    # 并发探测
    sem = asyncio.Semaphore(5)

    async def _probe(url: str) -> Optional[str]:
        async with sem:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout, connect=5.0),
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12) Chrome/120.0"}
                ) as client:
                    test_url = url.replace("{{key}}", "斗破苍穹").replace("{{page}}", "1")
                    r = await client.get(test_url)
                    if r.status_code == 200:
                        text = r.text
                        # 检查是否包含搜索结果特征
                        if any(kw in text for kw in [
                            "斗破苍穹", "搜索结果", "search-result", "book-list",
                            "novellist", "result-list", "item", "小说",
                        ]):
                            # 进一步验证：内容长度合理（至少1KB，不超过5MB）
                            if 1000 < len(text) < 5_000_000:
                                return url
            except Exception:
                pass
            return None

    tasks = [_probe(c) for c in candidates]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, str) and r:
            return r

    return None


# ==================== 同域反哺 ====================

def cross_feed_same_domain(
    source: Dict,
    same_domain_sources: List[Dict],
    source_type: str,
    test_results_map: Dict[str, Dict],
) -> Optional[Dict]:
    """从同域名其他源反哺修复。

    策略：
    1. 找同域名中搜索成功的源，复制其searchUrl模板
    2. 找同域名中详情/目录/正文成功的源，合并其规则
    3. 只合并保留源缺失的字段，不覆盖已有字段
    """
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    source_url = source.get(url_key, "")

    fixed = dict(source)
    changed = False

    if source_type == "book":
        # 找同域搜索成功的源
        search_ok_sources = []
        det_ok_sources = []
        toc_ok_sources = []
        con_ok_sources = []

        for other in same_domain_sources:
            other_url = other.get(url_key, "")
            if other_url == source_url:
                continue
            tr = test_results_map.get(other_url, {})
            stages = tr.get("stages", {})
            if stages.get("search"):
                search_ok_sources.append(other)
            if stages.get("detail"):
                det_ok_sources.append(other)
            if stages.get("toc"):
                toc_ok_sources.append(other)
            if stages.get("content"):
                con_ok_sources.append(other)

        # 1. 搜索修复：从搜索成功的源复制searchUrl
        tr = test_results_map.get(source_url, {})
        if not tr.get("stages", {}).get("search") and search_ok_sources:
            # 选择评分最高的搜索成功源
            best = max(search_ok_sources, key=lambda s: _score_source(s, source_type))
            if best.get("searchUrl") and not fixed.get("searchUrl"):
                fixed["searchUrl"] = best["searchUrl"]
                changed = True
            elif best.get("searchUrl") and fixed.get("searchUrl") != best["searchUrl"]:
                # 有searchUrl但搜索失败——尝试用成功源的searchUrl替换
                fixed["searchUrl"] = best["searchUrl"]
                changed = True

            # 同时合并搜索规则
            if not fixed.get("ruleSearch") or not isinstance(fixed.get("ruleSearch"), dict):
                fixed["ruleSearch"] = {}
            best_rule = best.get("ruleSearch", {})
            if isinstance(best_rule, dict):
                for field in ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind"]:
                    if not fixed["ruleSearch"].get(field) and best_rule.get(field):
                        fixed["ruleSearch"][field] = best_rule[field]
                        changed = True

        # 2. 详情/目录/正文规则修复
        for ok_sources, rule_key, fields in [
            (det_ok_sources, "ruleBookInfo", ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl"]),
            (toc_ok_sources, "ruleToc", ["chapterList", "chapterName", "chapterUrl", "nextTocUrl"]),
            (con_ok_sources, "ruleContent", ["content", "replaceRegex", "nextContentUrl"]),
        ]:
            if ok_sources:
                best = max(ok_sources, key=lambda s: _score_source(s, source_type))
                if not fixed.get(rule_key) or not isinstance(fixed.get(rule_key), dict):
                    fixed[rule_key] = {}
                best_rule = best.get(rule_key, {})
                if isinstance(best_rule, dict):
                    for field in fields:
                        if not fixed[rule_key].get(field) and best_rule.get(field):
                            fixed[rule_key][field] = best_rule[field]
                            changed = True

    return fixed if changed else None


def _score_source(source: Dict, source_type: str) -> int:
    """简单评分，用于选择最佳反哺源。"""
    score = 0
    if source_type == "book":
        if source.get("searchUrl"): score += 5
        rs = source.get("ruleSearch", {})
        if isinstance(rs, dict):
            score += sum(1 for f in ["bookList", "name", "bookUrl"] if rs.get(f))
        ri = source.get("ruleBookInfo", {})
        if isinstance(ri, dict):
            score += sum(1 for f in ["name", "author", "tocUrl"] if ri.get(f))
        rt = source.get("ruleToc", {})
        if isinstance(rt, dict):
            score += sum(1 for f in ["chapterList", "chapterName", "chapterUrl"] if rt.get(f))
        rc = source.get("ruleContent", {})
        if isinstance(rc, dict):
            score += 3 if rc.get("content") else 0
    return score


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="高并发自动修复书源/订阅源")
    parser.add_argument("--test-all", action="store_true", help="全量测试（所有源）")
    parser.add_argument("--test-book", type=int, default=0, help="测试N个书源")
    parser.add_argument("--test-rss", type=int, default=0, help="测试N个订阅源")
    parser.add_argument("--fix", action="store_true", help="修复失败的源")
    parser.add_argument("--fix-from", default="", help="从指定报告文件修复")
    parser.add_argument("--execute", action="store_true", help="执行修复（默认dry-run）")
    parser.add_argument("--concurrency", type=int, default=10, help="并发数")
    parser.add_argument("--timeout", type=float, default=60.0, help="单源调试超时(秒)")
    parser.add_argument("--host", default=DEVICE_HOST, help="真机地址")
    parser.add_argument("--http-port", type=int, default=DEVICE_HTTP_PORT, help="HTTP端口")
    parser.add_argument("--ws-port", type=int, default=DEVICE_WS_PORT, help="WebSocket端口")
    parser.add_argument("--probe-timeout", type=float, default=10.0, help="搜索接口探测超时(秒)")
    parser.add_argument("--no-probe", action="store_true", help="跳过Phase B搜索接口探测")
    parser.add_argument("--delete-dead", action="store_true", help="自动删除DNS/SSL死源")
    parser.add_argument("--output", default="", help="输出报告路径")
    args = parser.parse_args()

    if not any([args.test_all, args.test_book, args.test_rss, args.fix, args.fix_from]):
        args.test_book = 500
        args.fix = True

    print("=" * 60)
    print(" 高并发自动修复：测试 → 分类 → 智能修复 → 反哺合并 → 同步")
    print(f" 模式: {'执行' if args.execute else '仅分析(dry-run)'}")
    print(f" 并发: {args.concurrency}, 超时: {args.timeout}s")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_results = {}
    all_sources_cache = {}

    # ========== Step 1: 获取源列表 ==========
    print(f"\n[Step 1/5] 获取真机源列表")

    for st in ["book", "rss"]:
        test_n = args.test_book if st == "book" else args.test_rss
        if args.test_all or test_n > 0:
            sources = await api_get_sources(st, args.host, args.http_port)
            all_sources_cache[st] = sources
            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            name_key = "bookSourceName" if st == "book" else "sourceName"
            print(f"  {st}源: {len(sources)} 个")

    # ========== Step 2: 批量测试 ==========
    print(f"\n[Step 2/5] 批量WebSocket调试")

    for st in ["book", "rss"]:
        sources = all_sources_cache.get(st, [])
        if not sources:
            continue

        test_n = args.test_book if st == "book" else args.test_rss
        if args.test_all:
            test_sources = sources
        elif test_n > 0:
            # 按域名分层采样
            domain_groups: Dict[str, List[Dict]] = {}
            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            for s in sources:
                domain = extract_domain(s.get(url_key, ""))
                domain_groups.setdefault(domain, []).append(s)

            test_sources = []
            for domain, srcs in sorted(domain_groups.items(), key=lambda x: -len(x[1])):
                # 优先有searchUrl的
                if st == "book":
                    srcs.sort(key=lambda s: (0 if s.get("searchUrl") else 1, 0 if s.get("enabledExplore") else 1))
                test_sources.extend(srcs[:2])
                if len(test_sources) >= test_n:
                    break
            test_sources = test_sources[:test_n]
        else:
            continue

        label = "书源" if st == "book" else "订阅源"
        print(f"\n  {label}测试: {len(test_sources)} 个源, 并发 {args.concurrency}...")

        results = await batch_test(
            test_sources, st, args.concurrency, args.timeout,
            args.host, args.ws_port,
        )
        all_results[st] = results

        # 统计
        total = len(results)
        success = sum(1 for r in results if r["status"] == "success")
        partial = sum(1 for r in results if r["status"] == "partial")
        failed = sum(1 for r in results if r["status"] == "failed")

        # 阶段模式
        patterns = {}
        for r in results:
            s = r.get("stages", {})
            p = f"sea={'Y' if s.get('search') else 'N'} det={'Y' if s.get('detail') else 'N'} toc={'Y' if s.get('toc') else 'N'} con={'Y' if s.get('content') else 'N'}"
            patterns.setdefault(p, []).append(r)

        print(f"\n  {label}测试结果:")
        print(f"    成功: {success} ({success/total*100:.1f}%)")
        print(f"    部分: {partial} ({partial/total*100:.1f}%)")
        print(f"    失败: {failed} ({failed/total*100:.1f}%)")
        print(f"  阶段模式:")
        for p, items in sorted(patterns.items(), key=lambda x: -len(x[1])):
            print(f"    {p}: {len(items)}")

    # ========== Step 3: 分类 + 快速修复（反哺+清理） ==========
    if args.fix or args.fix_from:
        print(f"\n[Step 3/5] 智能修复")

        # 加载测试结果
        if args.fix_from:
            with open(args.fix_from, "r", encoding="utf-8") as f:
                report = json.load(f)
                if isinstance(report, dict):
                    for st in ["book", "rss"]:
                        if st in report:
                            all_results[st] = report[st]
                        elif "results" in report:
                            all_results[st] = [r for r in report["results"] if r.get("source_type") == st]

        all_fixed_sources = []  # 收集所有修复

        for st in ["book", "rss"]:
            results = all_results.get(st, [])
            sources = all_sources_cache.get(st, [])
            if not results or not sources:
                continue

            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            label = "书源" if st == "book" else "订阅源"

            # 建立索引
            source_map = {s.get(url_key, ""): s for s in sources}
            test_map = {r["source_url"]: r for r in results if r.get("source_url")}

            # 按域名分组
            domain_sources: Dict[str, List[Dict]] = {}
            for s in sources:
                domain = extract_domain(s.get(url_key, ""))
                domain_sources.setdefault(domain, []).append(s)

            # 筛选可修复的源（排除死站）
            fixable = []
            for r in results:
                if r["status"] == "success":
                    continue
                errors = r.get("errors", [])
                if "DNS" in errors or "SSL" in errors:
                    continue
                fixable.append(r)

            print(f"\n  {label}: {len(fixable)} 个可尝试修复")

            # === 阶段A: 快速修复（纯内存操作） ===
            print(f"\n  阶段A: 快速修复（同域反哺+URL清理+启用源）...")
            fixed_sources = []
            need_probe = []  # 需要搜索接口探测的源

            for r in fixable:
                source_url = r.get("source_url", "")
                source = source_map.get(source_url)
                if not source:
                    continue

                stages = r.get("stages", {})
                domain = extract_domain(source_url)
                same_domain = domain_sources.get(domain, [])

                fixed = dict(source)
                fix_reasons = []

                # 策略1: URL带#清理
                original_url = source.get(url_key, "")
                if "#" in original_url:
                    clean = original_url.split("#")[0].strip()
                    if not clean.endswith("/"):
                        clean += "/"
                    fixed[url_key] = clean
                    fix_reasons.append("清理URL#分组")

                # 策略2: 同域反哺
                if st == "book" and len(same_domain) > 1:
                    fed = cross_feed_same_domain(fixed, same_domain, st, test_map)
                    if fed:
                        fixed = fed
                        fix_reasons.append("同域反哺")

                # 策略3: 常见searchUrl模式修复
                if st == "book" and not stages.get("search") and fixed.get("searchUrl"):
                    su = fixed["searchUrl"]
                    if ".asp" in su and ".aspx" not in su and "/search" in su:
                        fixed["searchUrl"] = su.replace(".asp", ".aspx")
                        fix_reasons.append("asp→aspx")

                # 策略4: 启用被禁用的源
                if not fixed.get("enabled"):
                    fixed["enabled"] = True
                    fix_reasons.append("启用源")

                if fix_reasons:
                    fixed_sources.append((fixed, fix_reasons))

                # 收集需要搜索接口探测的源（sea=N det=Y）
                if st == "book" and not stages.get("search") and stages.get("detail"):
                    need_probe.append((fixed, source_url))

            print(f"  阶段A: {len(fixed_sources)} 个源可快速修复")
            print(f"  阶段A: {len(need_probe)} 个源需要搜索接口探测")

            # 执行快速修复
            if args.execute and fixed_sources:
                print(f"\n  执行快速修复 {len(fixed_sources)} 个源...")
                success_count = 0
                for i, (fixed, reasons) in enumerate(fixed_sources):
                    ok = await api_save_source(fixed, st, args.host, args.http_port)
                    if ok:
                        success_count += 1
                    if (i + 1) % 100 == 0:
                        print(f"    [{i+1}/{len(fixed_sources)}] 成功 {success_count}")
                print(f"  快速修复完成: {success_count}/{len(fixed_sources)} 成功")

            all_fixed_sources.extend(fixed_sources)

            # === 阶段B: 搜索接口探测（并发HTTP） ===
            if args.no_probe:
                print(f"\n  阶段B: 已跳过（--no-probe）")
            elif need_probe:
                print(f"\n  阶段B: 并发搜索接口探测 ({len(need_probe)} 个源)...")
                probe_sem = asyncio.Semaphore(5)  # 5个源同时探测
                probe_results = []
                progress_b = {"done": 0}

                async def _probe_source(fixed_src: Dict, src_url: str) -> Optional[Tuple[Dict, str]]:
                    async with probe_sem:
                        base_url = src_url.split("#")[0].strip()
                        probed_url = await probe_search_url(base_url, fixed_src, args.probe_timeout)
                        progress_b["done"] += 1
                        if progress_b["done"] % 20 == 0 or progress_b["done"] == len(need_probe):
                            print(f"    探测进度: {progress_b['done']}/{len(need_probe)}")
                        if probed_url:
                            return (fixed_src, probed_url)
                        return None

                probe_tasks = [_probe_source(f, u) for f, u in need_probe]
                probe_results_raw = await asyncio.gather(*probe_tasks, return_exceptions=True)

                probe_fixed = []
                for pr in probe_results_raw:
                    if isinstance(pr, tuple) and pr:
                        fixed_src, probed_url = pr
                        fixed_src["searchUrl"] = probed_url
                        probe_fixed.append((fixed_src, [f"探测到搜索接口: {probed_url[:60]}"]))

                print(f"  阶段B: 探测成功 {len(probe_fixed)} 个源")

                # 执行探测修复
                if args.execute and probe_fixed:
                    success_count = 0
                    for fixed, reasons in probe_fixed:
                        ok = await api_save_source(fixed, st, args.host, args.http_port)
                        if ok:
                            success_count += 1
                    print(f"  探测修复完成: {success_count}/{len(probe_fixed)} 成功")

                all_fixed_sources.extend(probe_fixed)

            # 输出修复摘要
            print(f"\n  {label}修复汇总:")
            reason_counts: Dict[str, int] = {}
            for fixed, reasons in all_fixed_sources:
                for r in reasons:
                    reason_counts[r] = reason_counts.get(r, 0) + 1
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                print(f"    {reason}: {count}")
            print(f"  总计: {len(all_fixed_sources)} 个源修复")

    # ========== Step 3.5: 删除死源（DNS/SSL失败） ==========
    if args.delete_dead and args.execute:
        print(f"\n[Step 3.5/5] 删除死源（DNS/SSL失败）")
        for st in ["book", "rss"]:
            results = all_results.get(st, [])
            if not results:
                continue
            label = "书源" if st == "book" else "订阅源"
            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            dead_urls = set()
            for r in results:
                errors = r.get("errors", [])
                if "DNS" in errors or "SSL" in errors:
                    url = r.get("source_url", "")
                    if url:
                        dead_urls.add(url)
            if dead_urls:
                print(f"  {label}死源: {len(dead_urls)} 个，正在删除...")
                deleted = await api_delete_sources(list(dead_urls), st, args.host, args.http_port)
                print(f"  {label}死源删除完成: {deleted} 个")
            else:
                print(f"  {label}无死源")

    # ========== Step 4: 验证修复结果 ==========
    if args.fix and args.execute and all_fixed_sources:
        print(f"\n[Step 4/5] 验证修复结果")

        for st in ["book", "rss"]:
            results = all_results.get(st, [])
            if not results:
                continue

            # 重新测试修复后的源
            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            fixed_urls = {f.get(url_key, "") for f, _ in all_fixed_sources}

            if not fixed_urls:
                continue

            # 获取修复后的源
            sources = await api_get_sources(st, args.host, args.http_port)
            to_retest = [s for s in sources if s.get(url_key, "") in fixed_urls]

            if to_retest:
                label = "书源" if st == "book" else "订阅源"
                print(f"\n  {label}: 重新测试 {len(to_retest)} 个修复后的源...")
                retest_results = await batch_test(
                    to_retest, st, args.concurrency, args.timeout,
                    args.host, args.ws_port,
                )

                # 对比修复前后
                orig_map = {r["source_url"]: r for r in results if r.get("source_url")}
                improved = 0
                for rr in retest_results:
                    orig = orig_map.get(rr.get("source_url", ""))
                    if orig:
                        orig_stages = sum(1 for v in orig.get("stages", {}).values() if v)
                        retest_stages = sum(1 for v in rr.get("stages", {}).values() if v)
                        if retest_stages > orig_stages:
                            improved += 1

                print(f"  {label}: {improved}/{len(retest_results)} 个源改善")

    # ========== Step 5: 保存报告 ==========
    print(f"\n[Step 5/5] 保存报告")

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "config": vars(args),
        "summary": {},
        "results": all_results,
    }

    for st in ["book", "rss"]:
        results = all_results.get(st, [])
        if results:
            total = len(results)
            success = sum(1 for r in results if r["status"] == "success")
            report_data["summary"][st] = {
                "total": total,
                "success": success,
                "success_rate": f"{success/total*100:.1f}%",
            }

    output_path = args.output
    if not output_path:
        os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
        output_path = os.path.join(
            SCRIPTS_DIR, "reports",
            f"auto-fix-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  报告已保存: {output_path}")

    # 最终统计
    print(f"\n{'='*60}")
    print(f" 自动修复完成汇总")
    print(f"{'='*60}")
    for st in ["book", "rss"]:
        results = all_results.get(st, [])
        if not results:
            continue
        label = "书源" if st == "book" else "订阅源"
        total = len(results)
        success = sum(1 for r in results if r["status"] == "success")
        partial = sum(1 for r in results if r["status"] == "partial")
        failed = sum(1 for r in results if r["status"] == "failed")
        print(f"  {label}: 测试{total}个, 成功{success}({success/total*100:.1f}%), "
              f"部分{partial}({partial/total*100:.1f}%), 失败{failed}({failed/total*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
