#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量优化脚本：测试 → 分类 → 修复 → 去重 → 同步。

完整工作流：
1. 死源清理：DNS检查 + 真机删除 + DB标记
2. 智能去重：域名分组 → 评分 → 合并优质规则 → 删除冗余
3. 批量测试：WebSocket调试 → 收集搜索/详情/目录/正文阶段结果
4. 失败分类：DNS失败/403/搜索失败/正文失败/超时/CF拦截
5. 自动修复：常见问题模式自动修复（searchUrl格式/ruleContent缺失等）
6. 同步：修复后的源推送回真机 + DB更新

用法:
    python batch_optimize.py --all                    # 完整流程
    python batch_optimize.py --test-only              # 只测试
    python batch_optimize.py --fix-only               # 只修复（需先有测试报告）
    python batch_optimize.py --dedup-only             # 只去重
    python batch_optimize.py --test-sample 200        # 测试200个样本
    python batch_optimize.py --fix-from reports/xxx.json  # 从指定报告修复
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
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_HTTP_PORT = 1122
DEVICE_WS_PORT = 1123

# 已知的聚合平台域名（合理多源，不去重）
AGGREGATOR_DOMAINS = {
    "game.erolabsshare.live", "erolabsshare.live",
    "lanzoux.com", "lanzous.com",
    "yckceo.com",
    "qk.lifves.com", "lifves.com",
    "api.huaban.com", "huaban.com",
    "github.com",
    "coolapk.com",
    "quark.sm.cn", "sm.cn",
    "baidu.com",
    "m.weibo.cn", "weibo.cn", "weibo.com",
    "runoob.com",
    "mp.weixin.qq.com", "weixin.qq.com",
    "data.newrank.cn", "newrank.cn",
    "cn.bing.com", "bing.com",
    "sogou.com",
}


# ==================== HTTP API ====================

async def api_get_sources(source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> List[Dict]:
    """从真机获取源列表。"""
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


async def api_delete_sources(urls: List[str], source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> int:
    """批量删除源。"""
    import httpx
    if not urls:
        return 0
    endpoint = "deleteBookSources" if source_type == "book" else "deleteRssSources"
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    deleted = 0
    batch_size = 100
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            payload = [{url_key: u} for u in batch if u]
            try:
                r = await client.post(f"http://{host}:{port}/{endpoint}", json=payload)
                deleted += len(batch)
            except Exception as e:
                print(f"  删除失败(批次{i//batch_size+1}): {e}")
    return deleted


async def api_save_source(source: Dict, source_type: str = "book", host: str = DEVICE_HOST, port: int = DEVICE_HTTP_PORT) -> bool:
    """保存/更新单个源。"""
    import httpx
    endpoint = "saveBookSource" if source_type == "book" else "saveRssSource"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        try:
            r = await client.post(f"http://{host}:{port}/{endpoint}", json=source)
            return r.json().get("isSuccess", False)
        except Exception:
            return False


# ==================== DNS 检查 ====================

async def check_dns(domain: str, timeout: float = 5.0) -> bool:
    """检查域名DNS是否可解析。"""
    import socket
    try:
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.getaddrinfo(domain, None),
            timeout=timeout,
        )
        return True
    except Exception:
        return False


# ==================== WebSocket 调试 ====================

async def debug_source_ws(
    source_url: str,
    source_type: str,
    key: str,
    ws_host: str = DEVICE_HOST,
    ws_port: int = DEVICE_WS_PORT,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """通过 WebSocket 调试单个源。"""
    import websockets

    result: Dict[str, Any] = {
        "source_url": source_url,
        "source_type": source_type,
        "status": "unknown",
        "stages": {
            "search": False,
            "detail": False,
            "toc": False,
            "content": False,
        },
        "search_count": 0,
        "toc_count": 0,
        "errors": [],
        "duration_ms": 0,
    }

    path = "/bookSourceDebug" if source_type == "book" else "/rssSourceDebug"
    ws_url = f"ws://{ws_host}:{ws_port}{path}"

    start = time.time()
    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            # 处理emoji: tag必须精确匹配bookSourceUrl
            req = {"tag": source_url, "key": key}
            await ws.send(json.dumps(req, ensure_ascii=False))

            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    if not msg:
                        continue

                    # 阶段判定
                    if "列表大小" in msg or "搜索结果" in msg:
                        result["stages"]["search"] = True
                        m = re.search(r"列表大小[：:](\d+)", msg)
                        if m:
                            result["search_count"] = int(m.group(1))

                    if "获取书名" in msg or "书名" in msg:
                        result["stages"]["detail"] = True

                    if "目录总数" in msg or "章节列表" in msg:
                        result["stages"]["toc"] = True
                        m = re.search(r"目录总数[：:](\d+)", msg)
                        if m:
                            result["toc_count"] = int(m.group(1))

                    # 正文成功检测（多关键词）
                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
                        result["stages"]["content"] = True

                    # RSS 特有
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
                        result["stages"]["search"] = True

                    # 错误检测
                    if "UnknownHostException" in msg:
                        result["errors"].append("DNS")
                    elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
                        result["errors"].append("TIMEOUT")
                    elif "403" in msg or "Forbidden" in msg:
                        result["errors"].append("403")
                    elif "CF" in msg and ("challenge" in msg.lower() or "盾" in msg):
                        result["errors"].append("CF")
                    elif "loginCheckJs" in msg or "需要登录" in msg:
                        result["errors"].append("LOGIN")
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
            pass  # 正常关闭
        else:
            result["errors"].append(f"CONN_FAIL:{err_msg[:60]}")

    result["duration_ms"] = int((time.time() - start) * 1000)

    # 状态判定
    if source_type == "book":
        stages_passed = sum(1 for v in result["stages"].values() if v)
        if stages_passed >= 4:
            result["status"] = "success"
        elif stages_passed > 0:
            result["status"] = "partial"
        else:
            result["status"] = "failed"
    else:
        result["status"] = "success" if result["stages"]["search"] else "failed"

    return result


# ==================== 域名提取 ====================

def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        base_url = url.split("#")[0].strip()
        if "://" not in base_url:
            base_url = "http://" + base_url
        domain = urlparse(base_url).hostname or ""
        return domain.lower().replace("www.", "")
    except Exception:
        return ""


# ==================== 评分 ====================

def score_book_source(source: dict) -> int:
    score = 0
    if source.get("bookSourceName"): score += 1
    if source.get("bookSourceUrl"): score += 1

    search_url = source.get("searchUrl", "")
    if search_url: score += 5
    if "page" in search_url or "{{page}}" in search_url: score += 2

    rule_search = source.get("ruleSearch", {})
    if isinstance(rule_search, dict):
        for f, p in [("bookList", 3), ("name", 2), ("author", 1), ("bookUrl", 2), ("coverUrl", 1), ("intro", 1), ("kind", 1)]:
            if rule_search.get(f): score += p

    rule_info = source.get("ruleBookInfo", {})
    if isinstance(rule_info, dict):
        for f in ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl"]:
            if rule_info.get(f): score += 1

    rule_toc = source.get("ruleToc", {})
    if isinstance(rule_toc, dict):
        for f, p in [("chapterList", 5), ("chapterName", 2), ("chapterUrl", 2), ("nextTocUrl", 2)]:
            if rule_toc.get(f): score += p

    rule_content = source.get("ruleContent", {})
    if isinstance(rule_content, dict):
        for f, p in [("content", 8), ("replaceRegex", 3), ("nextContentUrl", 2), ("imageStyle", 1)]:
            if rule_content.get(f): score += p

    if source.get("exploreUrl"): score += 3
    if source.get("loginUrl"): score += 1
    if source.get("enabled"): score += 1
    if source.get("enabledExplore"): score += 1

    return score


def score_rss_source(source: dict) -> int:
    score = 0
    if source.get("sourceName"): score += 1
    if source.get("sourceUrl"): score += 1

    rule_articles = source.get("ruleArticles", {})
    if isinstance(rule_articles, dict):
        for f, p in [("articleList", 5), ("title", 3), ("url", 2), ("image", 2), ("content", 2)]:
            if rule_articles.get(f): score += p

    rule_content = source.get("ruleContent", {})
    if isinstance(rule_content, dict):
        if rule_content.get("content"): score += 5

    if source.get("enabled"): score += 1
    return score


# ==================== 去重 ====================

def is_true_duplicate_book(sources: List[dict]) -> bool:
    if len(sources) <= 1:
        return False
    has_search = sum(1 for s in sources if s.get("searchUrl"))
    has_explore = sum(1 for s in sources if s.get("exploreUrl"))
    if has_search > len(sources) * 0.5:
        return True
    if has_explore > 0 and has_search == 0:
        return False
    if has_search == 0 and has_explore == 0:
        return True
    return has_search > 0


def is_true_duplicate_rss(sources: List[dict]) -> bool:
    if len(sources) <= 1:
        return False
    for s in sources:
        domain = extract_domain(s.get("sourceUrl", ""))
        if domain in AGGREGATOR_DOMAINS:
            return False
    paths = set()
    for s in sources:
        url = s.get("sourceUrl", "")
        base = url.split("#")[0].strip()
        try:
            paths.add(urlparse(base).path.rstrip("/"))
        except:
            paths.add(base)
    if len(paths) > 1:
        return False
    return True


def merge_book_rules(keep: dict, others: List[dict]) -> dict:
    merged = dict(keep)
    rule_fields = {
        "ruleSearch": ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind", "wordCount"],
        "ruleBookInfo": ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind", "wordCount"],
        "ruleToc": ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"],
        "ruleContent": ["content", "replaceRegex", "nextContentUrl", "imageStyle"],
    }
    for other in others:
        for rule_key, fields in rule_fields.items():
            keep_rule = merged.get(rule_key, {})
            other_rule = other.get(rule_key, {})
            if not isinstance(keep_rule, dict): keep_rule = {}
            if not isinstance(other_rule, dict): continue
            for field in fields:
                if not keep_rule.get(field) and other_rule.get(field):
                    keep_rule[field] = other_rule[field]
            merged[rule_key] = keep_rule
    if not merged.get("exploreUrl"):
        for other in others:
            if other.get("exploreUrl"):
                merged["exploreUrl"] = other["exploreUrl"]
                break
    return merged


async def run_dedup(source_type: str, host: str, port: int, execute: bool) -> Dict:
    """执行去重。返回 {deleted: int, merged: int}。"""
    print(f"\n{'='*50}")
    print(f" {'书源' if source_type == 'book' else '订阅源'}去重")
    print(f"{'='*50}")

    sources = await api_get_sources(source_type, host, port)
    print(f"  总数: {len(sources)}")

    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    domain_groups: Dict[str, List[dict]] = {}
    for s in sources:
        domain = extract_domain(s.get(url_key, ""))
        if domain:
            domain_groups.setdefault(domain, []).append(s)

    is_dup_fn = is_true_duplicate_book if source_type == "book" else is_true_duplicate_rss
    dup_groups = {d: srcs for d, srcs in domain_groups.items() if len(srcs) >= 2 and is_dup_fn(srcs)}
    print(f"  真重复域名: {len(dup_groups)} 个")

    urls_to_delete = []
    sources_to_merge = []

    for domain, srcs in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
        if source_type == "book":
            scored = sorted([(score_book_source(s), s) for s in srcs], key=lambda x: -x[0])
            best = scored[0][1]
            others = [s for _, s in scored[1:]]
            merged = merge_book_rules(best, others)
            if merged != best:
                sources_to_merge.append(merged)
        else:
            scored = sorted([(score_rss_source(s), s) for s in srcs], key=lambda x: -x[0])
            best = scored[0][1]
            others = [s for _, s in scored[1:]]

        for other in others:
            urls_to_delete.append(other.get(url_key, ""))

    if execute and urls_to_delete:
        # 保存合并后的源
        for merged_src in sources_to_merge:
            await api_save_source(merged_src, source_type, host, port)
        # 删除冗余源
        deleted = await api_delete_sources(urls_to_delete, source_type, host, port)
        print(f"  已删除: {deleted} 个, 已合并: {len(sources_to_merge)} 个")
    elif urls_to_delete:
        print(f"  [dry-run] 将删除: {len(urls_to_delete)} 个, 将合并: {len(sources_to_merge)} 个")

    return {"deleted": len(urls_to_delete), "merged": len(sources_to_merge)}


# ==================== 死源清理 ====================

async def run_dead_cleanup(source_type: str, host: str, port: int, execute: bool) -> Dict:
    """DNS检查 + 删除死源。"""
    print(f"\n{'='*50}")
    print(f" {'书源' if source_type == 'book' else '订阅源'}死源清理")
    print(f"{'='*50}")

    sources = await api_get_sources(source_type, host, port)
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    print(f"  总数: {len(sources)}")

    # 提取域名并检查DNS
    domains = {}
    for s in sources:
        domain = extract_domain(s.get(url_key, ""))
        if domain:
            domains.setdefault(domain, []).append(s.get(url_key, ""))

    print(f"  唯一域名: {len(domains)} 个")

    # 并发DNS检查
    dead_domains = []
    sem = asyncio.Semaphore(50)

    async def _check(d):
        async with sem:
            ok = await check_dns(d, timeout=5.0)
            return d, ok

    tasks = [_check(d) for d in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            continue
        domain, ok = r
        if not ok:
            dead_domains.append(domain)

    # 收集死源URL
    dead_urls = []
    for d in dead_domains:
        dead_urls.extend(domains[d])

    print(f"  死域名: {len(dead_domains)} 个, 死源: {len(dead_urls)} 个")

    if execute and dead_urls:
        deleted = await api_delete_sources(dead_urls, source_type, host, port)
        print(f"  已删除: {deleted} 个")
    elif dead_urls:
        print(f"  [dry-run] 将删除: {len(dead_urls)} 个")

    return {"dead_domains": len(dead_domains), "dead_urls": len(dead_urls)}


# ==================== 批量测试 ====================

async def run_batch_test(
    source_type: str,
    sample_size: int,
    host: str,
    http_port: int,
    ws_port: int,
    per_domain: int = 2,
    timeout: float = 60.0,
) -> List[Dict]:
    """批量WebSocket调试测试。"""
    sources = await api_get_sources(source_type, host, http_port)
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    name_key = "bookSourceName" if source_type == "book" else "sourceName"
    print(f"  {source_type}源总数: {len(sources)}")

    # 按域名分层采样
    domain_groups: Dict[str, List[Dict]] = {}
    for s in sources:
        domain = extract_domain(s.get(url_key, ""))
        domain_groups.setdefault(domain, []).append(s)

    sampled = []
    for domain, srcs in sorted(domain_groups.items(), key=lambda x: -len(x[1])):
        # 优先有searchUrl/exploreUrl的
        if source_type == "book":
            srcs.sort(key=lambda s: (0 if s.get("searchUrl") else 1, 0 if s.get("enabledExplore") else 1))
        else:
            srcs.sort(key=lambda s: (0 if s.get("ruleArticles") else 1))
        sampled.extend(srcs[:per_domain])
        if len(sampled) >= sample_size:
            break

    sampled = sampled[:sample_size]
    print(f"  采样: {len(sampled)} 个源")

    results = []
    for i, src in enumerate(sampled):
        url = src.get(url_key, "")
        name = src.get(name_key, "?")
        safe_name = name.encode('ascii', 'replace').decode()[:30]
        safe_url = url.encode('ascii', 'replace').decode()[:50]
        print(f"  [{i+1}/{len(sampled)}] {safe_name} ({safe_url})", end="", flush=True)

        r = await debug_source_ws(
            source_url=url,
            source_type=source_type,
            key="斗破苍穹" if source_type == "book" else "首页",
            ws_host=host,
            ws_port=ws_port,
            timeout=timeout,
        )
        r["source_name"] = name

        stages_str = " ".join(f"{s[:3]}={'Y' if v else 'N'}" for s, v in r["stages"].items())
        err_short = r["errors"][0][:30] if r["errors"] else ""
        print(f" → {stages_str} | {r['status']} | {r['duration_ms']}ms"
              + (f" | {err_short}" if err_short else ""))
        results.append(r)

    return results


# ==================== 失败分类 ====================

def classify_failures(results: List[Dict], source_type: str) -> Dict[str, List[Dict]]:
    """将测试结果按失败类型分类。"""
    categories = {
        "dns_fail": [],      # DNS解析失败
        "timeout": [],       # 连接超时
        "forbidden": [],     # 403/CF
        "ssl_error": [],     # SSL错误
        "search_fail": [],   # 搜索失败（网络通但搜索规则问题）
        "content_fail": [],  # 正文失败（搜索/目录通但正文规则问题）
        "partial": [],       # 部分通过
        "success": [],       # 完全通过
    }

    for r in results:
        errors = r.get("errors", [])
        stages = r.get("stages", {})

        if r["status"] == "success":
            categories["success"].append(r)
        elif "DNS" in errors:
            categories["dns_fail"].append(r)
        elif "TIMEOUT" in errors or "WS_TIMEOUT" in errors:
            categories["timeout"].append(r)
        elif "403" in errors or "CF" in errors:
            categories["forbidden"].append(r)
        elif "SSL" in errors:
            categories["ssl_error"].append(r)
        elif not stages.get("search") and not stages.get("detail"):
            categories["search_fail"].append(r)
        elif stages.get("search") and not stages.get("content"):
            categories["content_fail"].append(r)
        elif r["status"] == "partial":
            categories["partial"].append(r)
        else:
            categories["search_fail"].append(r)

    return categories


def print_categories(categories: Dict[str, List[Dict]], label: str):
    """打印分类统计。"""
    print(f"\n{'='*50}")
    print(f" {label} 失败分类")
    print(f"{'='*50}")
    total = sum(len(v) for v in categories.values())
    for cat, items in categories.items():
        if items:
            pct = len(items) / total * 100 if total else 0
            print(f"  {cat:16s}: {len(items):4d} ({pct:5.1f}%)")
            # 显示前3个例子
            for item in items[:3]:
                name = item.get("source_name", "?").encode('ascii', 'replace').decode()[:25]
                url = item["source_url"].encode('ascii', 'replace').decode()[:40]
                print(f"    - {name} | {url}")


# ==================== 自动修复 ====================

# 常见 searchUrl 过时模式及其修复
SEARCH_URL_FIXES = [
    # .asp → .aspx 迁移
    (r"keyword=([^&]+)\.asp\b", r"keyword=\1.aspx"),
    # qd 参数名变更
    (r"keyword=", "qd="),  # 仅当原keyword参数不再工作时
    # 缺少页码参数
    (r"(searchUrl.*?)(\{\{key\}\})$", r"\1\2&page=1"),
]


async def auto_fix_source(
    source: Dict,
    source_type: str,
    test_result: Dict,
    host: str,
    port: int,
) -> Optional[Dict]:
    """尝试自动修复单个源。返回修复后的源，或 None 表示无法自动修复。"""

    fixed = dict(source)
    changed = False
    errors = test_result.get("errors", [])
    stages = test_result.get("stages", {})

    if source_type == "book":
        # 1. 搜索失败 + searchUrl有.asp → 尝试.aspx
        if not stages.get("search") and fixed.get("searchUrl"):
            search_url = fixed["searchUrl"]
            if ".asp" in search_url and ".aspx" not in search_url:
                fixed["searchUrl"] = search_url.replace(".asp", ".aspx")
                changed = True

        # 2. 搜索失败 + searchUrl缺少page参数
        if not stages.get("search") and fixed.get("searchUrl"):
            search_url = fixed["searchUrl"]
            if "{{key}}" in search_url and "page" not in search_url.lower():
                # 添加page参数
                if "?" in search_url:
                    fixed["searchUrl"] = search_url + ",{'page': '{{page}}'}"
                else:
                    fixed["searchUrl"] = search_url + ",{'page': '{{page}}'}"
                changed = True

        # 3. 正文失败 + ruleContent缺失 → 标记需手动修复
        if stages.get("toc") and not stages.get("content"):
            rule_content = fixed.get("ruleContent", {})
            if not isinstance(rule_content, dict) or not rule_content.get("content"):
                # 无法自动修复，需要分析网站
                return None

        # 4. 目录失败 + ruleToc缺失
        if stages.get("detail") and not stages.get("toc"):
            rule_toc = fixed.get("ruleToc", {})
            if not isinstance(rule_toc, dict) or not rule_toc.get("chapterList"):
                return None

    else:  # RSS
        # RSS源文章列表失败
        if not stages.get("search"):
            rule_articles = fixed.get("ruleArticles", {})
            if not isinstance(rule_articles, dict) or not rule_articles.get("articleList"):
                return None

    if not changed:
        return None

    return fixed


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="批量优化书源/订阅源（测试→分类→修复→去重→同步）")
    parser.add_argument("--all", action="store_true", help="执行完整流程")
    parser.add_argument("--test-only", action="store_true", help="只测试")
    parser.add_argument("--fix-only", action="store_true", help="只修复")
    parser.add_argument("--dedup-only", action="store_true", help="只去重")
    parser.add_argument("--dead-only", action="store_true", help="只清理死源")
    parser.add_argument("--test-sample", type=int, default=100, help="测试采样数")
    parser.add_argument("--book-sample", type=int, default=0, help="书源采样数(覆盖test-sample)")
    parser.add_argument("--rss-sample", type=int, default=0, help="订阅源采样数(覆盖test-sample)")
    parser.add_argument("--execute", action="store_true", help="执行删除/修复（默认dry-run）")
    parser.add_argument("--host", default=DEVICE_HOST, help="真机地址")
    parser.add_argument("--http-port", type=int, default=DEVICE_HTTP_PORT, help="HTTP端口")
    parser.add_argument("--ws-port", type=int, default=DEVICE_WS_PORT, help="WebSocket端口")
    parser.add_argument("--timeout", type=float, default=60.0, help="单源调试超时(秒)")
    parser.add_argument("--fix-from", default="", help="从指定报告文件修复")
    parser.add_argument("--per-domain", type=int, default=2, help="每域名采样数")
    parser.add_argument("--output", default="", help="输出报告路径")
    args = parser.parse_args()

    if not any([args.all, args.test_only, args.fix_only, args.dedup_only, args.dead_only]):
        args.all = True

    # 默认采样数
    if args.book_sample == 0:
        args.book_sample = args.test_sample
    if args.rss_sample == 0:
        args.rss_sample = max(20, args.test_sample // 5)

    execute = args.execute

    print("=" * 60)
    print(" 批量优化：测试→分类→修复→去重→同步")
    print(f" 模式: {'执行' if execute else '仅分析(dry-run)'}")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_results = {"book": [], "rss": []}

    # ========== Step 1: 死源清理 ==========
    if args.all or args.dead_only:
        print(f"\n[Step 1/5] 死源清理（DNS检查）")
        for st in ["book", "rss"]:
            await run_dead_cleanup(st, args.host, args.http_port, execute)

    # ========== Step 2: 智能去重 ==========
    if args.all or args.dedup_only:
        print(f"\n[Step 2/5] 智能去重")
        for st in ["book", "rss"]:
            await run_dedup(st, args.host, args.http_port, execute)

    # ========== Step 3: 批量测试 ==========
    if args.all or args.test_only:
        print(f"\n[Step 3/5] 批量WebSocket调试测试")
        if args.book_sample > 0:
            print(f"\n  书源测试 (采样 {args.book_sample})...")
            all_results["book"] = await run_batch_test(
                "book", args.book_sample, args.host, args.http_port, args.ws_port,
                args.per_domain, args.timeout,
            )
        if args.rss_sample > 0:
            print(f"\n  订阅源测试 (采样 {args.rss_sample})...")
            all_results["rss"] = await run_batch_test(
                "rss", args.rss_sample, args.host, args.http_port, args.ws_port,
                args.per_domain, args.timeout,
            )

        # 分类
        for st in ["book", "rss"]:
            if all_results[st]:
                categories = classify_failures(all_results[st], st)
                print_categories(categories, "书源" if st == "book" else "订阅源")

    # ========== Step 4: 自动修复 ==========
    if args.all or args.fix_only:
        print(f"\n[Step 4/5] 自动修复")

        # 加载测试结果
        fix_results = all_results
        if args.fix_from:
            with open(args.fix_from, "r", encoding="utf-8") as f:
                report = json.load(f)
                fix_results = report.get("results", [])

        for st in ["book", "rss"]:
            results = fix_results.get(st, fix_results) if isinstance(fix_results, dict) else fix_results
            if not results:
                continue

            # 筛选可修复的源（失败/部分通过，非DNS/超时）
            fixable = [
                r for r in (results if isinstance(results, list) else results.values())
                if isinstance(r, dict)
                and r.get("status") in ("failed", "partial")
                and "DNS" not in str(r.get("errors", []))
                and "TIMEOUT" not in str(r.get("errors", []))
                and "CONN_FAIL" not in str(r.get("errors", []))
            ]

            if not fixable:
                print(f"  {st}: 无可自动修复的源")
                continue

            print(f"  {st}: {len(fixable)} 个可尝试修复")

            # 获取源列表
            sources = await api_get_sources(st, args.host, args.http_port)
            url_key = "bookSourceUrl" if st == "book" else "sourceUrl"
            source_map = {s.get(url_key, ""): s for s in sources}

            fixed_count = 0
            for r in fixable:
                source = source_map.get(r["source_url"])
                if not source:
                    continue

                fixed_source = await auto_fix_source(source, st, r, args.host, args.http_port)
                if fixed_source:
                    if execute:
                        ok = await api_save_source(fixed_source, st, args.host, args.http_port)
                        if ok:
                            fixed_count += 1
                            name = fixed_source.get("bookSourceName" if st == "book" else "sourceName", "?")
                            print(f"    ✅ 已修复: {name[:30].encode('ascii','replace').decode()}")
                    else:
                        fixed_count += 1

            print(f"  {st}: 修复完成 {fixed_count} 个")

    # ========== Step 5: 同步数据库 ==========
    if args.all and execute:
        print(f"\n[Step 5/5] 同步数据库")
        try:
            from legado_client.storage.database import get_session_factory
            from legado_client.storage.models import Source
            from sqlalchemy import update

            sf = get_session_factory()
            if sf:
                async with sf() as session:
                    async with session.begin():
                        # 标记测试结果
                        for st in ["book", "rss"]:
                            for r in all_results.get(st, []):
                                status = "pass" if r["status"] == "success" else "fail"
                                try:
                                    await session.execute(
                                        update(Source)
                                        .where(Source.source_url == r["source_url"])
                                        .values(
                                            last_test_status=status,
                                            last_test_stage=",".join(
                                                s for s, v in r["stages"].items() if v
                                            ) or "none",
                                        )
                                    )
                                except Exception:
                                    pass
                print("  数据库同步完成 ✅")
            else:
                print("  数据库不可用，跳过")
        except Exception as e:
            print(f"  数据库同步失败: {e}")

    # ========== 保存报告 ==========
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "config": vars(args),
        "results": {
            "book": all_results.get("book", []),
            "rss": all_results.get("rss", []),
        },
    }

    output_path = args.output
    if not output_path:
        os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
        output_path = os.path.join(
            SCRIPTS_DIR, "reports",
            f"batch-optimize-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {output_path}")

    # ========== 最终统计 ==========
    print(f"\n{'='*60}")
    print(f" 批量优化完成汇总")
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
