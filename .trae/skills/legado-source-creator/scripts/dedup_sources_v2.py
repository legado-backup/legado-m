#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能去重脚本 V2：分析+反哺+并发测试+清理#后缀。

核心改进（vs V1）：
1. 每组重复源先并发WebSocket测试验证，以实测结果为依据
2. 分析每个源的特色规则，从被删源提取有价值规则反哺保留源
3. URL带#的源，#后缀统一清理（仅保留干净的base URL）
4. 使用10并发WebSocket测试，大幅提速

流程：
1. 获取源列表 → 按域名分组（忽略#后缀）
2. 对重复组：并发测试所有源 → 分析配置质量+实测结果
3. 选最佳源（实测>配置质量>完整性） → 从其他源反哺优质规则
4. 清理保留源的URL（去掉#后缀） → 保存 → 删除其余源
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_HTTP_PORT = 1122
DEVICE_WS_PORT = 1123

# 聚合平台域名（合理多源，不去重）
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


# ==================== 工具函数 ====================

def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        base = url.split("#")[0].strip()
        if "://" not in base: base = "http://" + base
        return (urlparse(base).hostname or "").lower().replace("www.", "")
    except:
        return ""


def clean_url(url: str) -> str:
    """清理URL：去掉#后缀，统一格式。"""
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    if "://" not in base:
        base = "https://" + base
    return base


def is_true_duplicate_book(sources: List[dict]) -> bool:
    if len(sources) <= 1: return False
    has_search = sum(1 for s in sources if s.get("searchUrl"))
    has_explore = sum(1 for s in sources if s.get("exploreUrl"))
    if has_search > len(sources) * 0.5: return True
    if has_explore > 0 and has_search == 0: return False
    if has_search == 0 and has_explore == 0: return True
    return has_search > 0


def is_true_duplicate_rss(sources: List[dict]) -> bool:
    if len(sources) <= 1: return False
    for s in sources:
        domain = extract_domain(s.get("sourceUrl", ""))
        if domain in AGGREGATOR_DOMAINS: return False
    paths = set()
    for s in sources:
        url = s.get("sourceUrl", "")
        base = url.split("#")[0].strip()
        try: paths.add(urlparse(base).path.rstrip("/"))
        except: paths.add(base)
    if len(paths) > 1: return False
    return True


# ==================== 并发WebSocket测试 ====================

async def debug_source_ws(
    source_url: str, source_type: str, key: str,
    ws_host: str = DEVICE_HOST, ws_port: int = DEVICE_WS_PORT,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """WebSocket调试单个源。"""
    import websockets
    result = {
        "source_url": source_url, "source_type": source_type,
        "status": "unknown",
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "errors": [], "duration_ms": 0,
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
                    if not msg: continue
                    if "列表大小" in msg or "搜索结果" in msg: result["stages"]["search"] = True
                    if "获取书名" in msg or "书名" in msg: result["stages"]["detail"] = True
                    if "目录总数" in msg or "章节列表" in msg: result["stages"]["toc"] = True
                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg: result["stages"]["content"] = True
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg): result["stages"]["search"] = True
                    if "UnknownHostException" in msg: result["errors"].append("DNS")
                    elif "403" in msg or "Forbidden" in msg: result["errors"].append("403")
                    if "调试结束" in msg: break
            except asyncio.TimeoutError: result["errors"].append("WS_TIMEOUT")
    except Exception as e:
        err = str(e)
        if "1000" in err and "调试结束" in err: pass
        else: result["errors"].append(f"CONN:{err[:60]}")
    result["duration_ms"] = int((time.time() - start) * 1000)
    if source_type == "book":
        n = sum(1 for v in result["stages"].values() if v)
        result["status"] = "success" if n >= 4 else ("partial" if n > 0 else "failed")
    else:
        result["status"] = "success" if result["stages"]["search"] else "failed"
    return result


async def batch_debug(
    source_urls: List[str], source_type: str, key: str,
    concurrency: int = 10, timeout: float = 45.0,
) -> Dict[str, Dict]:
    """并发WebSocket测试多个源，返回 {url: test_result}。"""
    sem = asyncio.Semaphore(concurrency)
    results = {}

    async def _test(url):
        async with sem:
            r = await debug_source_ws(url, source_type, key, timeout=timeout)
            results[url] = r

    tasks = [_test(u) for u in source_urls]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results


# ==================== 配置分析+评分 ====================

def analyze_source_quality(source: dict, source_type: str) -> Dict:
    """深度分析源的配置质量，返回分析结果。"""
    analysis = {
        "field_completeness": 0,  # 字段完整度 (0-100)
        "rule_quality": 0,        # 规则质量 (0-100)
        "special_features": [],   # 特色功能
        "novel_patterns": [],     # 新颖写法
    }

    if source_type == "book":
        # 字段完整度
        total_fields = 0
        filled_fields = 0
        for key in ["bookSourceName", "bookSourceUrl", "bookSourceGroup",
                     "bookSourceComment", "sourceIcon"]:
            total_fields += 1
            if source.get(key): filled_fields += 1

        # 规则字段
        rule_sections = {
            "searchUrl": source.get("searchUrl", ""),
            "ruleSearch": source.get("ruleSearch", {}),
            "ruleBookInfo": source.get("ruleBookInfo", {}),
            "ruleToc": source.get("ruleToc", {}),
            "ruleContent": source.get("ruleContent", {}),
        }

        for name, rules in rule_sections.items():
            if isinstance(rules, str):
                total_fields += 1
                if rules: filled_fields += 1
            elif isinstance(rules, dict):
                for k, v in rules.items():
                    total_fields += 1
                    if v: filled_fields += 1

        analysis["field_completeness"] = int(filled_fields / max(total_fields, 1) * 100)

        # 规则质量：搜索分页、目录分页、正文分页、净化规则
        quality_score = 0
        search_url = source.get("searchUrl", "")
        if "{{page}}" in search_url or "page" in search_url.lower():
            quality_score += 15  # 支持搜索分页

        rule_search = source.get("ruleSearch", {})
        if isinstance(rule_search, dict):
            if rule_search.get("bookList"): quality_score += 10
            if rule_search.get("name"): quality_score += 5
            if rule_search.get("bookUrl"): quality_score += 5
            if rule_search.get("coverUrl"): quality_score += 5
            if rule_search.get("kind"): quality_score += 5

        rule_toc = source.get("ruleToc", {})
        if isinstance(rule_toc, dict):
            if rule_toc.get("nextTocUrl"): quality_score += 10  # 目录分页
            if rule_toc.get("isVip"): quality_score += 5

        rule_content = source.get("ruleContent", {})
        if isinstance(rule_content, dict):
            if rule_content.get("content"): quality_score += 15
            if rule_content.get("replaceRegex"): quality_score += 10  # 净化
            if rule_content.get("nextContentUrl"): quality_score += 10  # 正文分页
            if rule_content.get("imageStyle"): quality_score += 5

        analysis["rule_quality"] = min(quality_score, 100)

        # 特色功能
        if source.get("exploreUrl"): analysis["special_features"].append("发现")
        if source.get("loginUrl"): analysis["special_features"].append("登录")
        if source.get("loginCheckUrl"): analysis["special_features"].append("登录检查")
        if source.get("respondTime"): analysis["special_features"].append("响应时间")
        if source.get("bookUrlPattern"): analysis["special_features"].append("URL匹配")

        # 新颖写法检测
        all_rules_str = json.dumps(rule_sections, ensure_ascii=False)
        if "@js:" in all_rules_str: analysis["novel_patterns"].append("JS规则")
        if "java.ajax" in all_rules_str: analysis["novel_patterns"].append("AJAX")
        if "java.createSymmetricCrypto" in all_rules_str: analysis["novel_patterns"].append("加密")
        if "webView" in all_rules_str: analysis["novel_patterns"].append("WebView")
        if "replaceRegex" in all_rules_str: analysis["novel_patterns"].append("正则净化")
        if "{{page}}" in search_url: analysis["novel_patterns"].append("分页搜索")

    else:  # RSS
        # 简化分析
        ra = source.get("ruleArticles", {})
        rc = source.get("ruleContent", {})
        total = 8
        filled = 0
        for f in ["articleList", "title", "url", "image", "content", "next"]:
            if isinstance(ra, dict) and ra.get(f): filled += 1
        if isinstance(rc, dict) and rc.get("content"): filled += 1
        if source.get("sourceIcon"): filled += 1
        analysis["field_completeness"] = int(filled / total * 100)
        analysis["rule_quality"] = analysis["field_completeness"]

    return analysis


def compute_source_score(
    source: dict, source_type: str, test_result: Optional[Dict] = None
) -> Tuple[int, str]:
    """综合评分：实测结果 > 配置质量 > 完整度。
    返回 (分数, 评分理由)。"""
    analysis = analyze_source_quality(source, source_type)
    score = 0
    reasons = []

    # 实测权重最高
    if test_result:
        stages = test_result.get("stages", {})
        if source_type == "book":
            if stages.get("search"): score += 30; reasons.append("搜索通过")
            if stages.get("detail"): score += 15; reasons.append("详情通过")
            if stages.get("toc"): score += 25; reasons.append("目录通过")
            if stages.get("content"): score += 30; reasons.append("正文通过")
        else:
            if stages.get("search"): score += 100; reasons.append("列表通过")
    else:
        # 无实测结果，用配置质量替代
        score += int(analysis["field_completeness"] * 0.3)
        score += int(analysis["rule_quality"] * 0.5)
        reasons.append("配置评分(未测试)")

    # 特色功能加分
    for feat in analysis["special_features"]:
        score += 2
        reasons.append(f"+{feat}")

    # 新颖写法加分
    for pattern in analysis["novel_patterns"]:
        score += 3
        reasons.append(f"+{pattern}")

    return score, ", ".join(reasons[:5])


# ==================== 反哺合并 ====================

def reverse_feed_book(keep: dict, others: List[dict], test_results: Dict[str, Dict]) -> dict:
    """从被删源反哺优质规则到保留源。
    
    策略：
    1. 保留源缺失的字段，从其他源补充（优先从测试更好的源取）
    2. 保留源质量差的规则（如content只写了简单CSS），从其他源取更好的（如JS规则）
    3. 合并exploreUrl、loginUrl等特色功能
    """
    merged = dict(keep)  # 浅拷贝

    # 按测试结果排序其他源（测试更好的优先提供反哺）
    def _test_score(url):
        r = test_results.get(url, {})
        if not r: return 0
        return sum(1 for v in r.get("stages", {}).values() if v)

    sorted_others = sorted(others, key=lambda s: _test_score(s.get("bookSourceUrl", "")), reverse=True)

    # 需要反哺的规则字段
    rule_fields = {
        "ruleSearch": ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind", "wordCount", "lastChapter"],
        "ruleBookInfo": ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind", "wordCount"],
        "ruleToc": ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"],
        "ruleContent": ["content", "replaceRegex", "nextContentUrl", "imageStyle"],
    }

    feed_count = 0
    for other in sorted_others:
        for rule_key, fields in rule_fields.items():
            keep_rule = merged.get(rule_key, {})
            other_rule = other.get(rule_key, {})
            if not isinstance(keep_rule, dict): keep_rule = {}
            if not isinstance(other_rule, dict): continue

            for field in fields:
                keep_val = keep_rule.get(field, "")
                other_val = other_rule.get(field, "")

                # 保留源缺失此字段 → 反哺
                if not keep_val and other_val:
                    keep_rule[field] = other_val
                    feed_count += 1
                # 保留源规则简单(纯CSS <30字符) vs 其他源规则丰富(JS >50字符) → 替换
                elif keep_val and other_val and len(other_val) > len(keep_val) * 2:
                    # 其他规则显著更丰富，考虑替换
                    if other_val.startswith("@js:") and not keep_val.startswith("@js:"):
                        keep_rule[field] = other_val
                        feed_count += 1

            merged[rule_key] = keep_rule

    # 合并exploreUrl
    if not merged.get("exploreUrl"):
        for other in sorted_others:
            if other.get("exploreUrl"):
                merged["exploreUrl"] = other["exploreUrl"]
                feed_count += 1
                break

    # 合并loginUrl
    if not merged.get("loginUrl"):
        for other in sorted_others:
            if other.get("loginUrl"):
                merged["loginUrl"] = other["loginUrl"]
                feed_count += 1
                break

    # 合并loginCheckUrl
    if not merged.get("loginCheckUrl"):
        for other in sorted_others:
            if other.get("loginCheckUrl"):
                merged["loginCheckUrl"] = other["loginCheckUrl"]
                feed_count += 1
                break

    # 清理URL（去掉#后缀）
    old_url = merged.get("bookSourceUrl", "")
    merged["bookSourceUrl"] = clean_url(old_url)

    return merged, feed_count


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="智能去重V2：分析+反哺+并发测试")
    parser.add_argument("--dry-run", action="store_true", help="只分析，不删除")
    parser.add_argument("--book", action="store_true", help="处理书源")
    parser.add_argument("--rss", action="store_true", help="处理订阅源")
    parser.add_argument("--all", action="store_true", help="处理全部")
    parser.add_argument("--execute", action="store_true", help="执行删除")
    parser.add_argument("--concurrency", type=int, default=10, help="WebSocket并发数")
    parser.add_argument("--timeout", type=float, default=45.0, help="单源超时(秒)")
    parser.add_argument("--max-groups", type=int, default=0, help="最大处理组数(0=全部)")
    args = parser.parse_args()

    if args.all:
        args.book = True
        args.rss = True
    if not args.book and not args.rss:
        args.book = True
        args.rss = True

    execute = args.execute and not args.dry_run

    print("=" * 60)
    print(" 智能去重V2：分析+反哺+并发测试+清理#后缀")
    print(f" 模式: {'执行' if execute else '仅分析(dry-run)'}")
    print(f" 并发: {args.concurrency}")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    import httpx

    for source_type in (["book", "rss"] if args.book and args.rss else (["book"] if args.book else ["rss"])):
        label = "书源" if source_type == "book" else "订阅源"
        url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
        name_key = "bookSourceName" if source_type == "book" else "sourceName"

        print(f"\n{'='*50}")
        print(f" {label}去重")
        print(f"{'='*50}")

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            endpoint = "getBookSources" if source_type == "book" else "getRssSources"
            r = await client.get(f"http://{DEVICE_HOST}:{DEVICE_HTTP_PORT}/{endpoint}")
            sources = r.json().get("data", [])

        print(f"  总数: {len(sources)}")

        # 按域名分组（忽略#后缀）
        domain_groups: Dict[str, List[dict]] = {}
        for s in sources:
            domain = extract_domain(s.get(url_key, ""))
            if domain:
                domain_groups.setdefault(domain, []).append(s)

        # 筛选真重复
        is_dup_fn = is_true_duplicate_book if source_type == "book" else is_true_duplicate_rss
        dup_groups = {d: srcs for d, srcs in domain_groups.items() if len(srcs) >= 2 and is_dup_fn(srcs)}
        print(f"  真重复域名: {len(dup_groups)} 个")

        if args.max_groups > 0:
            dup_groups = dict(list(dup_groups.items())[:args.max_groups])
            print(f"  限制处理: {len(dup_groups)} 个组")

        # 对每组重复源：并发测试 → 分析评分 → 反哺合并 → 删除
        total_to_delete = []
        total_merged = 0
        total_feed_rules = 0

        for i, (domain, srcs) in enumerate(sorted(dup_groups.items(), key=lambda x: -len(x[1]))):
            print(f"\n  [{i+1}/{len(dup_groups)}] {domain} ({len(srcs)}个源)")

            # Step 1: 并发测试所有源
            urls = [s.get(url_key, "") for s in srcs]
            key = "斗破苍穹" if source_type == "book" else "首页"
            print(f"    并发测试 {len(urls)} 个源...")
            test_results = await batch_debug(urls, source_type, key, args.concurrency, args.timeout)

            # Step 2: 综合评分
            scored = []
            for s in srcs:
                url = s.get(url_key, "")
                score, reason = compute_source_score(s, source_type, test_results.get(url))
                scored.append((score, reason, s))
            scored.sort(key=lambda x: -x[0])

            best_score, best_reason, best_source = scored[0]
            others = [s for _, _, s in scored[1:]]

            # 输出评分
            best_name = best_source.get(name_key, "?").encode('ascii', 'replace').decode()[:20]
            print(f"    KEEP: {best_name} (score:{best_score}, {best_reason})")
            for sc, reason, s in scored[1:3]:
                n = s.get(name_key, "?").encode('ascii', 'replace').decode()[:15]
                print(f"    DEL: {n} (score:{sc}, {reason})")

            # Step 3: 反哺合并
            if source_type == "book":
                merged, feed_count = reverse_feed_book(best_source, others, test_results)
                if feed_count > 0:
                    total_feed_rules += feed_count
                    print(f"    反哺: {feed_count} 条规则")
                    if execute:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            ep = "saveBookSource" if source_type == "book" else "saveRssSource"
                            r = await client.post(f"http://{DEVICE_HOST}:{DEVICE_HTTP_PORT}/{ep}", json=merged)
                            ok = r.json().get("isSuccess", False)
                            if ok:
                                total_merged += 1
                                print(f"    保存合并源: OK")
            else:
                # RSS也清理URL
                merged = dict(best_source)
                merged["sourceUrl"] = clean_url(merged.get("sourceUrl", ""))

            # Step 4: 收集待删除URL
            for other in others:
                total_to_delete.append(other.get(url_key, ""))

        # 批量删除
        if execute and total_to_delete:
            print(f"\n  删除 {len(total_to_delete)} 个冗余源...")
            batch_size = 500
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
                ep = "deleteBookSources" if source_type == "book" else "deleteRssSources"
                for i in range(0, len(total_to_delete), batch_size):
                    batch = total_to_delete[i:i+batch_size]
                    payload = [{url_key: u} for u in batch if u]
                    try:
                        r = await client.post(f"http://{DEVICE_HOST}:{DEVICE_HTTP_PORT}/{ep}", json=payload)
                        print(f"    删除: {min(i+batch_size, len(total_to_delete))}/{len(total_to_delete)}")
                    except Exception as e:
                        print(f"    删除失败: {e}")

        print(f"\n  {label}去重汇总:")
        print(f"    待删除: {len(total_to_delete)} 个")
        print(f"    已合并: {total_merged} 个")
        print(f"    反哺规则: {total_feed_rules} 条")

    # 验证最终数量
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        r = await client.get(f"http://{DEVICE_HOST}:{DEVICE_HTTP_PORT}/getBookSources")
        final_book = len(r.json().get("data", []))
        r = await client.get(f"http://{DEVICE_HOST}:{DEVICE_HTTP_PORT}/getRssSources")
        final_rss = len(r.json().get("data", []))

    print(f"\n{'='*60}")
    print(f" 去重V2完成")
    print(f" 最终: 书源 {final_book}, 订阅源 {final_rss}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
