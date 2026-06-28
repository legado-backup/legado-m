#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能去重V3：深度分析+反哺合并+高并发+统一批处理流程。

核心改进（vs V2）：
1. 深度规则质量分析：不仅看字段是否填充，还分析写法是否标准/新颖
   - JS规则 > CSS选择器 > XPath > 正则（按复杂度和能力排序）
   - 有分页/净化/图片样式等高级特性的源评分更高
2. 反哺合并策略升级：
   - 保留源缺失字段：从测试最好的源取
   - 保留源弱规则（纯CSS <30字符）被其他源强规则（JS >50字符）替换
   - 特色功能（exploreUrl/loginUrl/loginCheckUrl）合并
   - searchUrl从测试通过的源复制
3. 高并发：20并发WebSocket测试 + 并发保存/删除
4. 整合批处理：死源清理(可选) → 去重 → 同步真机
5. URL #清理：去掉分组标识后缀

流程：
1. 获取源列表 → 按域名分组（忽略#后缀）
2. 对重复组：20并发WebSocket测试 → 深度分析配置质量+实测结果
3. 选最佳源（实测权重60% + 配置质量30% + 特色功能10%）
4. 从被删源反哺优质规则到保留源
5. 清理保留源的URL（去掉#后缀） → 保存 → 删除其余源
6. 清理因saveBookSource产生的URL#重复条目

用法:
    python smart_dedup_v3.py --all --execute                   # 全部去重（执行）
    python smart_dedup_v3.py --book --execute                   # 只处理书源
    python smart_dedup_v3.py --dry-run                          # 只分析不删除
    python smart_dedup_v3.py --all --execute --clean-hash       # 额外清理URL#重复
    python smart_dedup_v3.py --all --execute --concurrency 20   # 20并发测试
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
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
        if "://" not in base:
            base = "http://" + base
        return (urlparse(base).hostname or "").lower().replace("www.", "")
    except Exception:
        return ""


def clean_url(url: str) -> str:
    """清理URL：去掉#后缀，统一格式。"""
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    if not base:
        return ""
    if "://" not in base:
        base = "https://" + base
    return base


def extract_base_url(url: str) -> str:
    """提取基础URL用于去重判断（去掉#、统一scheme和www）。"""
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    if "://" not in base:
        base = "http://" + base
    parsed = urlparse(base)
    domain = parsed.hostname or ""
    if domain.startswith("www."):
        domain = domain[4:]
    scheme = parsed.scheme or "https"
    path = parsed.path.rstrip("/")
    return f"{scheme}://{domain}{path}" if path else f"{scheme}://{domain}"


# ==================== HTTP API ====================

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
    source_url: str, source_type: str, key: str,
    ws_host: str = DEVICE_HOST, ws_port: int = DEVICE_WS_PORT,
    timeout: float = 45.0,
) -> Dict[str, Any]:
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
                    if not msg:
                        continue
                    if "列表大小" in msg or "搜索结果" in msg:
                        result["stages"]["search"] = True
                    if "获取书名" in msg or ("书名" in msg and "获取" in msg):
                        result["stages"]["detail"] = True
                    if "目录总数" in msg or "章节列表" in msg:
                        result["stages"]["toc"] = True
                    if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
                        result["stages"]["content"] = True
                    if source_type == "rss" and ("文章列表" in msg or "articleList" in msg):
                        result["stages"]["search"] = True
                    if "UnknownHostException" in msg:
                        result["errors"].append("DNS")
                    elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
                        result["errors"].append("TIMEOUT")
                    elif "403" in msg or "Forbidden" in msg:
                        result["errors"].append("403")
                    elif "SSLException" in msg or "SSLHandshakeException" in msg:
                        result["errors"].append("SSL")
                    if "调试结束" in msg:
                        break
            except asyncio.TimeoutError:
                result["errors"].append("WS_TIMEOUT")
    except Exception as e:
        err = str(e)
        if "1000" in err and "调试结束" in err:
            pass
        else:
            result["errors"].append(f"CONN:{err[:60]}")
    result["duration_ms"] = int((time.time() - start) * 1000)
    if source_type == "book":
        n = sum(1 for v in result["stages"].values() if v)
        result["status"] = "success" if n >= 4 else ("partial" if n > 0 else "failed")
    else:
        result["status"] = "success" if result["stages"]["search"] else "failed"
    return result


async def batch_debug(
    source_urls: List[str], source_type: str, key: str,
    concurrency: int = 20, timeout: float = 45.0,
    host: str = DEVICE_HOST, ws_port: int = DEVICE_WS_PORT,
) -> Dict[str, Dict]:
    """高并发WebSocket测试多个源，返回 {url: test_result}。"""
    sem = asyncio.Semaphore(concurrency)
    results = {}
    progress = {"done": 0, "total": len(source_urls), "lock": asyncio.Lock()}

    async def _test(url):
        async with sem:
            r = await debug_source_ws(url, source_type, key, host, ws_port, timeout)
            results[url] = r
            async with progress["lock"]:
                progress["done"] += 1
                if progress["done"] % 20 == 0 or progress["done"] == progress["total"]:
                    print(f"    测试进度: {progress['done']}/{progress['total']}")

    tasks = [_test(u) for u in source_urls]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results


# ==================== 深度质量分析 ====================

def rule_complexity(value: str) -> int:
    """评估单条规则的复杂度和能力级别。
    JS规则(100) > XPath(80) > CSS+伪类(60) > 纯CSS(40) > 正则(30) > 简单文本(10)
    """
    if not value:
        return 0
    v = str(value).strip()
    if v.startswith("@js:"):
        return 100
    if v.startswith("//") or v.startswith("//*[@") or v.startswith("./"):
        return 80
    if ":" in v and ("nth-child" in v or "nth-of-type" in v or "not(" in v):
        return 60
    if v.startswith("@") or v.startswith("class.") or v.startswith("tag."):
        return 50
    if v.startswith("##") or v.startswith("%%"):
        return 40
    if v.startswith("<") and v.endswith(">"):
        return 30
    if len(v) < 10:
        return 10
    return 20


def analyze_source_deep(source: dict, source_type: str) -> Dict:
    """深度分析源配置质量，返回详细分析结果。"""
    analysis = {
        "field_completeness": 0,   # 字段完整度 (0-100)
        "rule_quality": 0,          # 规则质量 (0-100)
        "avg_complexity": 0,        # 平均规则复杂度
        "special_features": [],     # 特色功能
        "novel_patterns": [],       # 新颖写法
        "missing_critical": [],     # 缺失关键字段
    }

    if source_type == "book":
        # === 字段完整度 ===
        total_fields = 0
        filled_fields = 0
        critical_fields = {
            "searchUrl": source.get("searchUrl", ""),
        }
        rule_sections = {
            "ruleSearch": source.get("ruleSearch", {}),
            "ruleBookInfo": source.get("ruleBookInfo", {}),
            "ruleToc": source.get("ruleToc", {}),
            "ruleContent": source.get("ruleContent", {}),
        }

        for key in ["bookSourceName", "bookSourceUrl", "bookSourceGroup", "bookSourceComment"]:
            total_fields += 1
            if source.get(key):
                filled_fields += 1

        for name, rules in rule_sections.items():
            if isinstance(rules, str):
                total_fields += 1
                if rules:
                    filled_fields += 1
            elif isinstance(rules, dict):
                for k, v in rules.items():
                    total_fields += 1
                    if v:
                        filled_fields += 1

        analysis["field_completeness"] = int(filled_fields / max(total_fields, 1) * 100)

        # === 规则质量 + 复杂度 ===
        quality_score = 0
        complexity_scores = []

        # 搜索URL质量
        search_url = source.get("searchUrl", "")
        if search_url:
            quality_score += 10
        if "{{page}}" in search_url or "page" in search_url.lower():
            quality_score += 8  # 支持搜索分页

        # 搜索规则
        rs = rule_sections.get("ruleSearch", {})
        if isinstance(rs, dict):
            for f, w in [("bookList", 10), ("name", 6), ("author", 3),
                         ("bookUrl", 8), ("coverUrl", 3), ("intro", 2), ("kind", 2)]:
                val = rs.get(f, "")
                if val:
                    quality_score += w
                    complexity_scores.append(rule_complexity(val))

        # 详情规则
        ri = rule_sections.get("ruleBookInfo", {})
        if isinstance(ri, dict):
            for f, w in [("name", 4), ("author", 2), ("intro", 3),
                         ("coverUrl", 2), ("lastChapter", 2), ("tocUrl", 4)]:
                val = ri.get(f, "")
                if val:
                    quality_score += w
                    complexity_scores.append(rule_complexity(val))

        # 目录规则
        rt = rule_sections.get("ruleToc", {})
        if isinstance(rt, dict):
            for f, w in [("chapterList", 12), ("chapterName", 4), ("chapterUrl", 4),
                         ("nextTocUrl", 6), ("isVip", 2), ("isPay", 2)]:
                val = rt.get(f, "")
                if val:
                    quality_score += w
                    complexity_scores.append(rule_complexity(val))

        # 正文规则
        rc = rule_sections.get("ruleContent", {})
        if isinstance(rc, dict):
            for f, w in [("content", 15), ("replaceRegex", 6), ("nextContentUrl", 6), ("imageStyle", 3)]:
                val = rc.get(f, "")
                if val:
                    quality_score += w
                    complexity_scores.append(rule_complexity(val))

        analysis["rule_quality"] = min(quality_score, 100)
        analysis["avg_complexity"] = sum(complexity_scores) / max(len(complexity_scores), 1)

        # === 特色功能 ===
        if source.get("exploreUrl"):
            analysis["special_features"].append("发现")
        if source.get("loginUrl"):
            analysis["special_features"].append("登录")
        if source.get("loginCheckUrl"):
            analysis["special_features"].append("登录检查")
        if source.get("bookUrlPattern"):
            analysis["special_features"].append("URL匹配")

        # === 新颖写法检测 ===
        all_rules_str = json.dumps(rule_sections, ensure_ascii=False)
        if "@js:" in all_rules_str:
            analysis["novel_patterns"].append("JS规则")
        if "java.ajax" in all_rules_str:
            analysis["novel_patterns"].append("AJAX")
        if "java.createSymmetricCrypto" in all_rules_str:
            analysis["novel_patterns"].append("加密")
        if "webView" in all_rules_str:
            analysis["novel_patterns"].append("WebView")
        if "replaceRegex" in all_rules_str:
            analysis["novel_patterns"].append("正则净化")
        if "{{page}}" in search_url:
            analysis["novel_patterns"].append("分页搜索")

        # === 缺失关键字段 ===
        if not search_url and not source.get("exploreUrl"):
            analysis["missing_critical"].append("searchUrl")
        if isinstance(rc, dict) and not rc.get("content"):
            analysis["missing_critical"].append("ruleContent.content")
        if isinstance(rt, dict) and not rt.get("chapterList"):
            analysis["missing_critical"].append("ruleToc.chapterList")
        if isinstance(rs, dict) and not rs.get("bookList"):
            analysis["missing_critical"].append("ruleSearch.bookList")

    else:  # RSS
        ra = source.get("ruleArticles", {})
        rc = source.get("ruleContent", {})
        total = 8
        filled = 0
        for f in ["articleList", "title", "url", "image", "content", "next"]:
            if isinstance(ra, dict) and ra.get(f):
                filled += 1
        if isinstance(rc, dict) and rc.get("content"):
            filled += 1
        if source.get("sourceIcon"):
            filled += 1
        analysis["field_completeness"] = int(filled / total * 100)
        analysis["rule_quality"] = analysis["field_completeness"]

    return analysis


def compute_source_score_v3(
    source: dict, source_type: str, test_result: Optional[Dict] = None
) -> Tuple[int, str]:
    """V3综合评分：实测权重60% + 配置质量30% + 特色功能10%。
    返回 (分数, 评分理由)。"""
    analysis = analyze_source_deep(source, source_type)
    score = 0
    reasons = []

    # 实测权重 60%
    if test_result:
        stages = test_result.get("stages", {})
        if source_type == "book":
            if stages.get("search"):
                score += 18
                reasons.append("搜索OK")
            if stages.get("detail"):
                score += 9
                reasons.append("详情OK")
            if stages.get("toc"):
                score += 15
                reasons.append("目录OK")
            if stages.get("content"):
                score += 18
                reasons.append("正文OK")
        else:
            if stages.get("search"):
                score += 60
                reasons.append("列表OK")
    else:
        # 无实测结果，用配置质量替代
        score += int(analysis["field_completeness"] * 0.2)
        reasons.append("未测试")

    # 配置质量 30%
    score += int(analysis["rule_quality"] * 0.3)

    # 规则复杂度加分（JS/XPath等高级写法）
    if analysis["avg_complexity"] >= 80:
        score += 5
        reasons.append("高级规则")
    elif analysis["avg_complexity"] >= 50:
        score += 3
        reasons.append("中等规则")

    # 特色功能 10%
    for feat in analysis["special_features"]:
        score += 3
        reasons.append(f"+{feat}")

    for pattern in analysis["novel_patterns"]:
        score += 2
        reasons.append(f"+{pattern}")

    return score, ", ".join(reasons[:5])


# ==================== 真重复判断 ====================

def is_true_duplicate_book(sources: List[dict]) -> bool:
    """判断一组书源是否为"真重复"。
    
    判定标准：
    - 同域名多个源
    - 大部分有searchUrl（同一类型的搜索源）
    - 都只有exploreUrl没有searchUrl → 可能是不同分类（合理多源）
    """
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
        except Exception:
            paths.add(base)
    if len(paths) > 1:
        return False
    return True


# ==================== 反哺合并 ====================

def reverse_feed_book_v3(
    keep: dict, others: List[dict], test_results: Dict[str, Dict]
) -> Tuple[dict, int, List[str]]:
    """V3反哺合并：从被删源提取优质规则反哺保留源。
    
    策略：
    1. 保留源缺失的字段 → 从测试最好的源取
    2. 保留源弱规则（简单CSS <30字符）被其他源强规则（JS >50字符）替换
    3. 特色功能（exploreUrl/loginUrl/loginCheckUrl）合并
    4. searchUrl从测试通过的源复制
    
    返回 (合并后的源, 反哺规则数, 反哺详情列表)
    """
    merged = dict(keep)
    url_key = "bookSourceUrl"
    feed_count = 0
    feed_details = []

    # 按测试结果排序其他源（测试更好的优先提供反哺）
    def _test_stages(url):
        r = test_results.get(url, {})
        if not r:
            return 0
        return sum(1 for v in r.get("stages", {}).values() if v)

    sorted_others = sorted(
        others,
        key=lambda s: _test_stages(s.get(url_key, "")),
        reverse=True
    )

    # 需要反哺的规则字段及权重
    rule_fields = {
        "ruleSearch": {
            "fields": ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind", "wordCount", "lastChapter"],
            "critical": ["bookList", "name", "bookUrl"],  # 关键字段，缺失时必须从其他源补
        },
        "ruleBookInfo": {
            "fields": ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind", "wordCount"],
            "critical": ["name", "tocUrl"],
        },
        "ruleToc": {
            "fields": ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"],
            "critical": ["chapterList", "chapterName", "chapterUrl"],
        },
        "ruleContent": {
            "fields": ["content", "replaceRegex", "nextContentUrl", "imageStyle"],
            "critical": ["content"],
        },
    }

    for other in sorted_others:
        for rule_key, config in rule_fields.items():
            keep_rule = merged.get(rule_key, {})
            other_rule = other.get(rule_key, {})
            if not isinstance(keep_rule, dict):
                keep_rule = {}
            if not isinstance(other_rule, dict):
                continue

            for field in config["fields"]:
                keep_val = keep_rule.get(field, "")
                other_val = other_rule.get(field, "")

                if not keep_val and other_val:
                    # 保留源缺失此字段 → 反哺
                    keep_rule[field] = other_val
                    feed_count += 1
                    feed_details.append(f"{rule_key}.{field}")
                elif keep_val and other_val:
                    keep_complex = rule_complexity(keep_val)
                    other_complex = rule_complexity(other_val)
                    # 其他规则显著更强（复杂度差>=40且长度>=2倍）→ 替换
                    if other_complex >= keep_complex + 40 and len(other_val) >= len(keep_val) * 2:
                        keep_rule[field] = other_val
                        feed_count += 1
                        feed_details.append(f"{rule_key}.{field}(升级)")
                    # 特殊：其他源是JS规则，保留源是简单CSS → 替换
                    elif other_val.startswith("@js:") and not keep_val.startswith("@js:"):
                        keep_rule[field] = other_val
                        feed_count += 1
                        feed_details.append(f"{rule_key}.{field}(→JS)")

            merged[rule_key] = keep_rule

    # 合并searchUrl（从测试通过的源取）
    keep_test = test_results.get(keep.get(url_key, ""), {})
    if not keep_test.get("stages", {}).get("search"):
        for other in sorted_others:
            other_url = other.get(url_key, "")
            other_test = test_results.get(other_url, {})
            if other_test.get("stages", {}).get("search") and other.get("searchUrl"):
                merged["searchUrl"] = other["searchUrl"]
                # 同时补搜索规则
                if not merged.get("ruleSearch") or not isinstance(merged.get("ruleSearch"), dict):
                    merged["ruleSearch"] = {}
                other_rs = other.get("ruleSearch", {})
                if isinstance(other_rs, dict):
                    for f in rule_fields["ruleSearch"]["fields"]:
                        if not merged["ruleSearch"].get(f) and other_rs.get(f):
                            merged["ruleSearch"][f] = other_rs[f]
                            feed_count += 1
                            feed_details.append(f"ruleSearch.{f}(搜索修复)")
                feed_details.append("searchUrl(搜索修复)")
                break

    # 合并特色功能
    for feat_key in ["exploreUrl", "loginUrl", "loginCheckUrl"]:
        if not merged.get(feat_key):
            for other in sorted_others:
                if other.get(feat_key):
                    merged[feat_key] = other[feat_key]
                    feed_count += 1
                    feed_details.append(feat_key)
                    break

    # 清理URL（去掉#后缀）
    old_url = merged.get(url_key, "")
    cleaned = clean_url(old_url)
    if cleaned and cleaned != old_url:
        merged[url_key] = cleaned

    return merged, feed_count, feed_details


def reverse_feed_rss_v3(
    keep: dict, others: List[dict], test_results: Dict[str, Dict]
) -> Tuple[dict, int, List[str]]:
    """RSS源反哺合并。"""
    merged = dict(keep)
    feed_count = 0
    feed_details = []

    # RSS规则字段
    ra = merged.get("ruleArticles", {})
    if not isinstance(ra, dict):
        ra = {}
        merged["ruleArticles"] = ra

    rc = merged.get("ruleContent", {})
    if not isinstance(rc, dict):
        rc = {}
        merged["ruleContent"] = rc

    for other in others:
        other_ra = other.get("ruleArticles", {})
        other_rc = other.get("ruleContent", {})
        if isinstance(other_ra, dict):
            for f in ["articleList", "title", "url", "image", "content", "next"]:
                if not ra.get(f) and other_ra.get(f):
                    ra[f] = other_ra[f]
                    feed_count += 1
                    feed_details.append(f"ruleArticles.{f}")
        if isinstance(other_rc, dict):
            for f in ["content", "nextContentUrl"]:
                if not rc.get(f) and other_rc.get(f):
                    rc[f] = other_rc[f]
                    feed_count += 1
                    feed_details.append(f"ruleContent.{f}")

    # 清理URL
    old_url = merged.get("sourceUrl", "")
    cleaned = clean_url(old_url)
    if cleaned and cleaned != old_url:
        merged["sourceUrl"] = cleaned

    return merged, feed_count, feed_details


# ==================== URL#重复清理 ====================

async def clean_hash_duplicates(source_type: str, host: str, port: int) -> int:
    """清理因saveBookSource/saveRssSource产生的URL#重复条目。
    
    原因：saveBookSource(清理#后的URL) 会创建新条目，旧#URL仍存在。
    方案：找出带#的URL，检查其clean版本是否已存在，如果存在则删除带#的。
    """
    sources = await api_get_sources(source_type, host, port)
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"

    # 按clean URL分组
    clean_to_urls: Dict[str, List[str]] = {}
    for s in sources:
        url = s.get(url_key, "")
        if not url:
            continue
        cleaned = clean_url(url)
        if cleaned:
            clean_to_urls.setdefault(cleaned, []).append(url)

    # 找重复：同一clean URL有多个条目
    to_delete = []
    for clean_url_val, urls in clean_to_urls.items():
        if len(urls) <= 1:
            continue
        # 优先保留不带#的URL，删除带#的
        hash_urls = [u for u in urls if "#" in u]
        no_hash_urls = [u for u in urls if "#" not in u]
        if hash_urls and no_hash_urls:
            # 有clean版本了，删除带#的
            to_delete.extend(hash_urls)
        elif hash_urls and not no_hash_urls:
            # 全是带#的，保留第一个，删除其余
            to_delete.extend(hash_urls[1:])

    if to_delete:
        label = "书源" if source_type == "book" else "订阅源"
        print(f"  {label}URL#重复清理: 删除 {len(to_delete)} 个重复条目")
        deleted = await api_delete_sources(to_delete, source_type, host, port)
        return deleted
    return 0


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="智能去重V3：深度分析+反哺合并+高并发")
    parser.add_argument("--dry-run", action="store_true", help="只分析，不删除")
    parser.add_argument("--book", action="store_true", help="处理书源")
    parser.add_argument("--rss", action="store_true", help="处理订阅源")
    parser.add_argument("--all", action="store_true", help="处理全部")
    parser.add_argument("--execute", action="store_true", help="执行删除")
    parser.add_argument("--clean-hash", action="store_true", help="额外清理URL#重复条目")
    parser.add_argument("--concurrency", type=int, default=20, help="WebSocket并发数")
    parser.add_argument("--timeout", type=float, default=45.0, help="单源超时(秒)")
    parser.add_argument("--max-groups", type=int, default=0, help="最大处理组数(0=全部)")
    parser.add_argument("--min-group-size", type=int, default=2, help="最小重复组大小")
    parser.add_argument("--host", default=DEVICE_HOST, help="真机地址")
    parser.add_argument("--http-port", type=int, default=DEVICE_HTTP_PORT, help="HTTP端口")
    parser.add_argument("--ws-port", type=int, default=DEVICE_WS_PORT, help="WebSocket端口")
    args = parser.parse_args()

    if args.all:
        args.book = True
        args.rss = True
    if not args.book and not args.rss:
        args.book = True
        args.rss = True

    execute = args.execute and not args.dry_run

    print("=" * 60)
    print(" 智能去重V3：深度分析+反哺合并+高并发")
    print(f" 模式: {'执行' if execute else '仅分析(dry-run)'}")
    print(f" 并发: {args.concurrency}")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_stats = {"deleted": 0, "merged": 0, "feed_rules": 0, "feed_details": []}

    for source_type in (["book", "rss"] if args.book and args.rss else
                        (["book"] if args.book else ["rss"])):
        label = "书源" if source_type == "book" else "订阅源"
        url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
        name_key = "bookSourceName" if source_type == "book" else "sourceName"

        print(f"\n{'='*50}")
        print(f" {label}去重")
        print(f"{'='*50}")

        # Step 1: 获取源列表
        sources = await api_get_sources(source_type, args.host, args.http_port)
        print(f"  总数: {len(sources)}")

        # Step 2: 按域名分组（忽略#后缀）
        domain_groups: Dict[str, List[dict]] = {}
        for s in sources:
            domain = extract_domain(s.get(url_key, ""))
            if domain:
                domain_groups.setdefault(domain, []).append(s)

        # 筛选真重复
        is_dup_fn = is_true_duplicate_book if source_type == "book" else is_true_duplicate_rss
        dup_groups = {d: srcs for d, srcs in domain_groups.items()
                      if len(srcs) >= args.min_group_size and is_dup_fn(srcs)}

        # 按组大小排序（大组优先，减少数量最明显）
        sorted_groups = sorted(dup_groups.items(), key=lambda x: -len(x[1]))

        total_in_dup = sum(len(v) for v in sorted_groups)
        print(f"  真重复域名: {len(dup_groups)} 个, 涉及 {total_in_dup} 个源")

        if args.max_groups > 0:
            sorted_groups = sorted_groups[:args.max_groups]
            print(f"  限制处理: {len(sorted_groups)} 个组")

        if not sorted_groups:
            print(f"  无重复源需要处理")
            continue

        # Step 3: 批量并发测试所有重复源（一次并发，而非每组单独测试）
        print(f"\n  批量测试所有重复源...")
        all_dup_urls = []
        for domain, srcs in sorted_groups:
            for s in srcs:
                url = s.get(url_key, "")
                if url:
                    all_dup_urls.append(url)

        key = "斗破苍穹" if source_type == "book" else "首页"
        test_results = await batch_debug(
            all_dup_urls, source_type, key,
            args.concurrency, args.timeout,
            args.host, args.ws_port,
        )

        # Step 4: 逐组分析评分 → 反哺合并 → 保存/删除
        total_to_delete = []
        total_merged = 0
        total_feed_rules = 0
        all_feed_details = []

        for i, (domain, srcs) in enumerate(sorted_groups):
            if len(srcs) < 2:
                continue

            # 综合评分
            scored = []
            for s in srcs:
                url = s.get(url_key, "")
                score, reason = compute_source_score_v3(s, source_type, test_results.get(url))
                scored.append((score, reason, s))
            scored.sort(key=lambda x: -x[0])

            best_score, best_reason, best_source = scored[0]
            others = [s for _, _, s in scored[1:]]

            # 输出评分摘要
            best_name = best_source.get(name_key, "?")[:20]
            n_delete = len(others)
            if i < 20 or (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(sorted_groups)}] {domain} ({len(srcs)}个) "
                      f"→ KEEP:{best_name}(score:{best_score}) DEL:{n_delete}")

            # 反哺合并
            if source_type == "book":
                merged, feed_count, feed_details = reverse_feed_book_v3(
                    best_source, others, test_results
                )
            else:
                merged, feed_count, feed_details = reverse_feed_rss_v3(
                    best_source, others, test_results
                )

            if feed_count > 0:
                total_feed_rules += feed_count
                all_feed_details.extend(feed_details[:3])  # 保留前3条详情
                if i < 20 or (i + 1) % 50 == 0:
                    print(f"    反哺: {feed_count} 条规则 ({', '.join(feed_details[:3])})")

            # 执行保存合并源
            if execute:
                ok = await api_save_source(merged, source_type, args.host, args.http_port)
                if ok:
                    total_merged += 1

            # 收集待删除URL
            for other in others:
                other_url = other.get(url_key, "")
                if other_url:
                    total_to_delete.append(other_url)

        # 批量删除
        if execute and total_to_delete:
            print(f"\n  批量删除 {len(total_to_delete)} 个冗余源...")
            deleted = await api_delete_sources(total_to_delete, source_type, args.host, args.http_port)
            total_stats["deleted"] += deleted
            print(f"  删除完成: {deleted} 个")

        total_stats["merged"] += total_merged
        total_stats["feed_rules"] += total_feed_rules
        total_stats["feed_details"].extend(all_feed_details[:10])

        print(f"\n  {label}去重汇总:")
        print(f"    待删除: {len(total_to_delete)} 个")
        print(f"    已合并: {total_merged} 个")
        print(f"    反哺规则: {total_feed_rules} 条")
        if all_feed_details:
            detail_counts = Counter(all_feed_details)
            print(f"    反哺详情(Top5): {dict(list(detail_counts.most_common(5)))}")

    # Step 5: 清理URL#重复
    if args.clean_hash or execute:
        print(f"\n{'='*50}")
        print(f" URL#重复清理")
        print(f"{'='*50}")
        for st in (["book", "rss"] if args.book and args.rss else
                   (["book"] if args.book else ["rss"])):
            deleted = await clean_hash_duplicates(st, args.host, args.http_port)
            total_stats["deleted"] += deleted

    # 最终统计
    final_book = len(await api_get_sources("book", args.host, args.http_port))
    final_rss = len(await api_get_sources("rss", args.host, args.http_port))

    print(f"\n{'='*60}")
    print(f" 智能去重V3完成")
    print(f" 总删除: {total_stats['deleted']} 个")
    print(f" 总合并: {total_stats['merged']} 个")
    print(f" 总反哺规则: {total_stats['feed_rules']} 条")
    print(f" 最终: 书源 {final_book}, 订阅源 {final_rss}")
    print(f"{'='*60}")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"dedup-v3-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": total_stats,
        "final_counts": {"book": final_book, "rss": final_rss},
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f" 报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
