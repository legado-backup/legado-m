#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能整合V4：抓取实际页面 → 验证规则匹配 → 精准整合。

核心思路（vs V3硬代码复制）：
V3问题：同域名有多个源，直接复制其他源规则到保留源，不看实际页面DOM
V4改进：
  1. 抓取网站实际页面HTML（首页/搜索页）
  2. 用BeautifulSoup/lxml验证各源规则是否能在实际DOM中匹配到元素
  3. 只保留真正匹配DOM的规则，丢弃不匹配的
  4. 缺失字段从其他源中找"能在实际DOM中匹配到内容"的规则
  5. 仍缺失的字段，分析DOM结构自动生成选择器

流程：
  获取源列表 → 按域名分组 → 对每组：
    1. 抓取网站页面
    2. 逐源验证规则→真实匹配评分
    3. 选最高真实匹配度的源为base
    4. 从其他源补充"实际匹配"的缺失规则
    5. 对仍缺失字段，从DOM自动推断选择器
    6. 保存整合源，删除冗余

用法:
    python smart_merge_v4.py --dry-run                      # 只分析
    python smart_merge_v4.py --book --execute               # 执行书源整合
    python smart_merge_v4.py --all --execute                # 执行全部
    python smart_merge_v4.py --all --execute --concurrency 10  # 10并发
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
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlencode

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_HTTP_PORT = 1122
DEVICE_WS_PORT = 1123

# 聚合平台域名（合理多源，不整合）
AGGREGATOR_DOMAINS = {
    "game.erolabsshare.live", "erolabsshare.live",
    "lanzoux.com", "lanzous.com",
    "yckceo.com",
    "qk.lifves.com", "lifves.com",
    "api.huaban.com", "huaban.com",
    "github.com", "coolapk.com",
    "quark.sm.cn", "sm.cn", "baidu.com",
    "m.weibo.cn", "weibo.cn", "weibo.com",
    "runoob.com",
    "mp.weixin.qq.com", "weixin.qq.com",
    "data.newrank.cn", "newrank.cn",
    "cn.bing.com", "bing.com", "sogou.com",
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
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    if not base:
        return ""
    if "://" not in base:
        base = "https://" + base
    return base


# ==================== HTTP API ====================

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


# ==================== 页面抓取 ====================

async def fetch_page(url: str, timeout: float = 15.0) -> Optional[str]:
    """抓取页面HTML。"""
    import httpx
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        ) as client:
            r = await client.get(url)
            if r.status_code == 200 and len(r.content) > 500:
                return r.text
    except Exception:
        pass
    return None


async def fetch_search_page(source: Dict, source_type: str, timeout: float = 15.0) -> Optional[str]:
    """根据源的searchUrl抓取搜索结果页。"""
    if source_type == "book":
        search_url = source.get("searchUrl", "")
        base_url = source.get("bookSourceUrl", "")
    else:
        search_url = source.get("sourceUrl", "")
        base_url = source.get("sourceUrl", "")

    if not search_url and not base_url:
        return None

    # 如果有searchUrl，构造实际搜索URL
    if search_url and source_type == "book":
        # searchUrl格式: https://xxx/search?q={{key}} 或 POST方式
        keyword = "斗破苍穹"
        actual_url = search_url.replace("{{key}}", keyword)

        # 处理POST格式: URL@method=POST@body=xxx
        if "@js:" in actual_url:
            return None  # JS规则无法在这里处理

        if "@" in actual_url:
            # 复合格式，取URL部分
            parts = actual_url.split("@")
            actual_url = parts[0]

        # 处理相对路径
        if actual_url.startswith("http"):
            return await fetch_page(actual_url, timeout)
        elif base_url:
            full_url = urljoin(clean_url(base_url), actual_url)
            return await fetch_page(full_url, timeout)

    # 否则抓取首页
    return await fetch_page(clean_url(base_url), timeout)


# ==================== 规则验证（核心！） ====================

def validate_css_rule(html: str, selector: str) -> Dict:
    """验证CSS选择器是否能在HTML中匹配到元素。
    返回 {match: bool, count: int, samples: [str]} """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 处理Legado特殊语法
        # class.xxx → .xxx, tag.xxx → xxx
        css = selector.strip()
        if css.startswith("class."):
            css = "." + css[6:]
        elif css.startswith("tag."):
            css = css[4:]
        elif css.startswith("tag "):
            css = css[4:]

        # 处理@text, @href, @src 等属性选择器
        attr = None
        if "@" in css:
            parts = css.rsplit("@", 1)
            css = parts[0].strip()
            attr = parts[1].strip()

        # 处理 ! 排除语法
        if "!" in css:
            css = css.split("!")[0].strip()

        # 处理 %% 替换语法
        if "%%" in css:
            css = css.split("%%")[0].strip()

        if not css:
            return {"match": False, "count": 0, "samples": []}

        elements = soup.select(css)
        if not elements:
            return {"match": False, "count": 0, "samples": []}

        # 如果有属性选择器，进一步提取
        samples = []
        for el in elements[:3]:
            if attr == "text":
                text = el.get_text(strip=True)
                if text:
                    samples.append(text[:50])
            elif attr == "href":
                href = el.get("href", "")
                if href:
                    samples.append(href[:50])
            elif attr == "src":
                src = el.get("src", "")
                if src:
                    samples.append(src[:50])
            else:
                text = el.get_text(strip=True)
                if text:
                    samples.append(text[:50])
                else:
                    # 标签名也算匹配
                    samples.append(f"<{el.name}>")

        return {"match": True, "count": len(elements), "samples": samples}

    except Exception as e:
        return {"match": False, "count": 0, "samples": [], "error": str(e)[:50]}


def validate_xpath_rule(html: str, xpath: str) -> Dict:
    """验证XPath是否能在HTML中匹配到元素。"""
    try:
        from lxml import etree
        tree = etree.HTML(html)

        # 处理Legado特殊语法
        xp = xpath.strip()
        if "@text" in xp:
            xp = xp.replace("@text", "text()")
        if "@href" in xp:
            xp = xp.replace("@href", "@href")

        results = tree.xpath(xp)
        if not results:
            return {"match": False, "count": 0, "samples": []}

        samples = []
        for r in results[:3]:
            if isinstance(r, str):
                samples.append(r[:50])
            elif hasattr(r, "text"):
                samples.append((r.text or "")[:50])
            else:
                samples.append(str(r)[:50])

        return {"match": True, "count": len(results), "samples": samples}

    except Exception as e:
        return {"match": False, "count": 0, "samples": [], "error": str(e)[:50]}


def validate_rule(html: str, rule_value: str) -> Dict:
    """验证单条规则，自动识别CSS/XPath/JS类型。"""
    if not rule_value or not html:
        return {"match": False, "count": 0, "samples": [], "type": "empty"}

    v = str(rule_value).strip()

    # JS规则无法在Python中验证，标记为"需真机验证"
    if v.startswith("@js:"):
        return {"match": None, "count": 0, "samples": [], "type": "js", "note": "JS规则需真机验证"}

    # XPath: 以 // 或 ./ 开头
    if v.startswith("//") or v.startswith("./") or v.startswith("//*[@"):
        result = validate_xpath_rule(html, v)
        result["type"] = "xpath"
        return result

    # Regex: 以 ## 或正则特征开头
    if v.startswith("##") or v.startswith("%%"):
        return {"match": None, "count": 0, "samples": [], "type": "regex", "note": "正则规则需真机验证"}

    # 默认当CSS选择器处理
    result = validate_css_rule(html, v)
    result["type"] = "css"
    return result


def validate_source_rules(html: str, source: Dict, source_type: str) -> Dict:
    """验证源的所有规则对实际HTML的匹配度。
    返回 {field: {match, count, samples, type}, score, matched_fields, unmatched_fields} """
    result = {}
    matched = []
    unmatched = []

    if source_type == "book":
        rule_sections = {
            "ruleSearch": source.get("ruleSearch", {}),
            "ruleBookInfo": source.get("ruleBookInfo", {}),
            "ruleToc": source.get("ruleToc", {}),
            "ruleContent": source.get("ruleContent", {}),
        }
    else:
        rule_sections = {
            "ruleArticles": source.get("ruleArticles", {}),
            "ruleContent": source.get("ruleContent", {}),
        }

    for section_name, rules in rule_sections.items():
        if not isinstance(rules, dict):
            continue
        for field, value in rules.items():
            if not value:
                continue
            v = str(value).strip()
            # 跳过特殊字段
            if field in ("checkKeyWord", "bookUrl"):
                continue
            vr = validate_rule(html, v)
            result[f"{section_name}.{field}"] = vr
            if vr["match"] is True:
                matched.append(f"{section_name}.{field}")
            elif vr["match"] is False:
                unmatched.append(f"{section_name}.{field}")

    score = len(matched) * 10 - len(unmatched) * 2
    # JS/regex规则无法验证，不算负分
    js_count = sum(1 for v in result.values() if v.get("type") in ("js", "regex"))
    score += js_count * 3  # JS规则给予保守分（比纯猜测高，比验证通过低）

    return {
        "details": result,
        "score": score,
        "matched_fields": matched,
        "unmatched_fields": unmatched,
        "js_fields_count": js_count,
    }


# ==================== DOM分析 → 自动推断选择器 ====================

def auto_infer_selector(html: str, field_type: str) -> Optional[str]:
    """根据DOM结构推断可能的选择器。
    
    field_type: bookList, name, author, bookUrl, coverUrl, intro,
                chapterList, chapterName, chapterUrl, content,
                articleList, title, url, image
    """
    if not html:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None

    # 常见DOM模式映射
    patterns = {
        "bookList": [
            # 常见小说搜索结果容器
            {"selector": ".result-list .result-item", "min_count": 2},
            {"selector": ".book-list .book-item", "min_count": 2},
            {"selector": ".novellist li", "min_count": 2},
            {"selector": ".list-group .list-group-item", "min_count": 2},
            {"selector": ".s-b-list .s-b-item", "min_count": 2},
            {"selector": ".search-list li", "min_count": 2},
            {"selector": ".book_list li", "min_count": 2},
            {"selector": ".grid-3 li", "min_count": 2},
            {"selector": ".library li", "min_count": 2},
            {"selector": "#sitembox li", "min_count": 2},
            {"selector": ".bookbox", "min_count": 2},
            {"selector": ".book-li", "min_count": 2},
            # 通用：找包含多个链接的列表
            {"selector": "ul li", "min_count": 3},
            {"selector": ".item", "min_count": 2},
            {"selector": ".box", "min_count": 2},
        ],
        "name": [
            {"selector": ".bookname a", "min_count": 1},
            {"selector": ".sname a", "min_count": 1},
            {"selector": "h4 a", "min_count": 1},
            {"selector": "h3 a", "min_count": 1},
            {"selector": ".name a", "min_count": 1},
            {"selector": ".title a", "min_count": 1},
            {"selector": "a.bookname", "min_count": 1},
        ],
        "author": [
            {"selector": ".author", "min_count": 1},
            {"selector": ".s-author", "min_count": 1},
            {"selector": ".writer", "min_count": 1},
            {"selector": "span.author", "min_count": 1},
        ],
        "bookUrl": [
            {"selector": ".bookname a@href", "min_count": 1},
            {"selector": "h4 a@href", "min_count": 1},
            {"selector": "h3 a@href", "min_count": 1},
            {"selector": "a.bookname@href", "min_count": 1},
        ],
        "chapterList": [
            {"selector": ".listmain dd a", "min_count": 3},
            {"selector": "#list dd a", "min_count": 3},
            {"selector": ".chapter-list li a", "min_count": 3},
            {"selector": ".book_list li a", "min_count": 3},
            {"selector": ".mulu_list li a", "min_count": 3},
            {"selector": "dd a", "min_count": 3},
        ],
        "content": [
            {"selector": "#content", "min_count": 1},
            {"selector": "#chaptercontent", "min_count": 1},
            {"selector": ".read-content", "min_count": 1},
            {"selector": ".bookreadercontent", "min_count": 1},
            {"selector": ".content", "min_count": 1},
            {"selector": "#BookText", "min_count": 1},
            {"selector": ".txt-content", "min_count": 1},
            {"selector": ".article-content", "min_count": 1},
        ],
        "articleList": [
            {"selector": ".article-list li", "min_count": 2},
            {"selector": ".content-list li", "min_count": 2},
            {"selector": "ul.items li", "min_count": 2},
            {"selector": ".feed-list li", "min_count": 2},
        ],
        "title": [
            {"selector": "h2 a", "min_count": 1},
            {"selector": "h3 a", "min_count": 1},
            {"selector": ".title a", "min_count": 1},
        ],
    }

    candidates = patterns.get(field_type, [])
    for pattern in candidates:
        sel = pattern["selector"]
        min_count = pattern.get("min_count", 1)
        try:
            elements = soup.select(sel)
            if len(elements) >= min_count:
                # 验证提取内容不为空
                has_content = False
                for el in elements[:3]:
                    text = el.get_text(strip=True)
                    if text and len(text) > 0:
                        has_content = True
                        break
                if has_content:
                    return sel
        except Exception:
            continue

    return None


# ==================== 智能整合核心 ====================

async def smart_merge_group(
    domain: str,
    sources: List[Dict],
    source_type: str,
    host: str,
    http_port: int,
    execute: bool,
) -> Dict:
    """对一个域名组的源执行智能整合。
    
    返回 {domain, kept, deleted, merged_rules, auto_inferred, details} """
    url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"
    name_key = "bookSourceName" if source_type == "book" else "sourceName"

    result = {
        "domain": domain,
        "source_count": len(sources),
        "kept": 0,
        "deleted_urls": [],
        "merged_rules": 0,
        "auto_inferred": 0,
        "details": [],
    }

    if len(sources) < 2:
        return result

    # Step 1: 抓取网站页面
    print(f"    抓取 {domain} ...", end=" ", flush=True)
    html = None
    # 尝试抓取搜索页或首页
    for s in sources:
        html = await fetch_search_page(s, source_type, timeout=10)
        if html:
            break
    if not html:
        print("页面不可达，跳过")
        result["details"].append("页面不可达，无法验证规则，跳过整合")
        return result
    print(f"OK ({len(html)} bytes)")

    # Step 2: 逐源验证规则对实际HTML的匹配度
    validations = []
    for s in sources:
        v = validate_source_rules(html, s, source_type)
        name = s.get(name_key, "?")[:20]
        url = s.get(url_key, "")
        validations.append({
            "source": s,
            "name": name,
            "url": url,
            "validation": v,
        })
        match_count = len(v["matched_fields"])
        unmatch_count = len(v["unmatched_fields"])
        js_count = v["js_fields_count"]
        result["details"].append(
            f"  {name}: score={v['score']}, match={match_count}, unmatch={unmatch_count}, js={js_count}"
        )

    # Step 3: 选最高真实匹配度的源为base
    validations.sort(key=lambda x: x["validation"]["score"], reverse=True)
    best = validations[0]
    base_source = dict(best["source"])  # 浅拷贝

    best_name = best["name"]
    best_score = best["validation"]["score"]
    best_match = len(best["validation"]["matched_fields"])
    print(f"    保留: {best_name} (score={best_score}, match={best_match})")

    # Step 4: 从其他源补充"实际匹配DOM"的缺失规则
    if source_type == "book":
        rule_sections = {
            "ruleSearch": ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind", "wordCount"],
            "ruleBookInfo": ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind", "wordCount"],
            "ruleToc": ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"],
            "ruleContent": ["content", "replaceRegex", "nextContentUrl", "imageStyle"],
        }
    else:
        rule_sections = {
            "ruleArticles": ["articleList", "title", "url", "image", "content", "next"],
            "ruleContent": ["content", "nextContentUrl"],
        }

    merged_count = 0
    merged_details = []

    for section_name, fields in rule_sections.items():
        base_rules = base_source.get(section_name, {})
        if not isinstance(base_rules, dict):
            base_rules = {}
            base_source[section_name] = base_rules

        for field in fields:
            base_val = base_rules.get(field, "")

            # base已有值 → 检查是否真的匹配DOM
            if base_val:
                base_vr = validate_rule(html, base_val)
                if base_vr["match"] is True:
                    continue  # base规则匹配，保留
                # base规则不匹配DOM → 尝试从其他源找匹配的
                if base_vr["match"] is False:
                    # 看其他源是否有能匹配DOM的规则
                    found_better = False
                    for other_v in validations[1:]:
                        other_rules = other_v["source"].get(section_name, {})
                        if not isinstance(other_rules, dict):
                            continue
                        other_val = other_rules.get(field, "")
                        if not other_val:
                            continue
                        other_vr = validate_rule(html, other_val)
                        if other_vr["match"] is True:
                            base_rules[field] = other_val
                            merged_count += 1
                            merged_details.append(f"{section_name}.{field}(替换不匹配→匹配)")
                            found_better = True
                            break
                    if found_better:
                        continue
                    # 没有其他源匹配 → 保留原规则（可能对搜索页不对但对详情页对）
                # JS/regex规则无法验证 → 保留
                if base_vr["match"] is None:
                    continue

            # base缺失该字段 → 从其他源找匹配DOM的
            found = False
            for other_v in validations[1:]:
                other_rules = other_v["source"].get(section_name, {})
                if not isinstance(other_rules, dict):
                    continue
                other_val = other_rules.get(field, "")
                if not other_val:
                    continue
                other_vr = validate_rule(html, other_val)
                if other_vr["match"] is True:
                    base_rules[field] = other_val
                    merged_count += 1
                    merged_details.append(f"{section_name}.{field}(补充匹配)")
                    found = True
                    break
                elif other_vr["match"] is None and other_vr.get("type") in ("js", "regex"):
                    # JS/regex规则无法验证，但总比空好
                    base_rules[field] = other_val
                    merged_count += 1
                    merged_details.append(f"{section_name}.{field}(补充JS/正则)")
                    found = True
                    break

            base_source[section_name] = base_rules

    # Step 5: 对仍缺失的关键字段，从DOM自动推断选择器
    auto_inferred = 0
    for section_name, fields in rule_sections.items():
        base_rules = base_source.get(section_name, {})
        if not isinstance(base_rules, dict):
            base_rules = {}

        # 只推断关键字段
        key_fields_map = {
            "ruleSearch": ["bookList", "name"],
            "ruleBookInfo": ["name", "tocUrl"],
            "ruleToc": ["chapterList", "chapterName"],
            "ruleContent": ["content"],
            "ruleArticles": ["articleList", "title"],
        }
        key_fields = key_fields_map.get(section_name, [])

        for field in key_fields:
            if not base_rules.get(field):
                inferred = auto_infer_selector(html, field)
                if inferred:
                    base_rules[field] = inferred
                    auto_inferred += 1
                    merged_details.append(f"{section_name}.{field}(自动推断: {inferred})")

        base_source[section_name] = base_rules

    # 合并特色功能（这些不需要DOM验证，是URL/字符串）
    for feat_key in ["exploreUrl", "loginUrl", "loginCheckUrl", "searchUrl"]:
        if not base_source.get(feat_key):
            for other_v in validations[1:]:
                other_val = other_v["source"].get(feat_key, "")
                if other_val:
                    base_source[feat_key] = other_val
                    merged_count += 1
                    merged_details.append(f"{feat_key}(补充)")
                    break

    # 清理URL
    old_url = base_source.get(url_key, "")
    cleaned = clean_url(old_url)
    if cleaned and cleaned != old_url:
        base_source[url_key] = cleaned

    # Step 6: 保存/删除
    result["merged_rules"] = merged_count
    result["auto_inferred"] = auto_inferred

    if execute and (merged_count > 0 or auto_inferred > 0):
        ok = await api_save_source(base_source, source_type, host, http_port)
        if ok:
            result["kept"] = 1

    # 其他源标记删除
    for other_v in validations[1:]:
        url = other_v["url"]
        if url:
            result["deleted_urls"].append(url)

    if merged_details:
        for d in merged_details[:5]:
            result["details"].append(f"  整合: {d}")
        if len(merged_details) > 5:
            result["details"].append(f"  ...共{len(merged_details)}条")

    return result


# ==================== 真重复判断 ====================

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
        except Exception:
            paths.add(base)
    if len(paths) > 1:
        return False
    return True


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="智能整合V4：抓取实际页面→验证规则匹配→精准整合")
    parser.add_argument("--dry-run", action="store_true", help="只分析，不删除")
    parser.add_argument("--book", action="store_true", help="处理书源")
    parser.add_argument("--rss", action="store_true", help="处理订阅源")
    parser.add_argument("--all", action="store_true", help="处理全部")
    parser.add_argument("--execute", action="store_true", help="执行删除")
    parser.add_argument("--clean-hash", action="store_true", help="清理URL#重复")
    parser.add_argument("--concurrency", type=int, default=5, help="域名并发处理数")
    parser.add_argument("--max-groups", type=int, default=0, help="最大处理组数(0=全部)")
    parser.add_argument("--host", default=DEVICE_HOST, help="真机地址")
    parser.add_argument("--http-port", type=int, default=DEVICE_HTTP_PORT, help="HTTP端口")
    args = parser.parse_args()

    if args.all:
        args.book = True
        args.rss = True
    if not args.book and not args.rss:
        args.book = True
        args.rss = True

    execute = args.execute and not args.dry_run

    print("=" * 60)
    print(" 智能整合V4：抓取实际页面 → 验证规则匹配 → 精准整合")
    print(f" 模式: {'执行' if execute else '仅分析(dry-run)'}")
    print(f" 并发: {args.concurrency}")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_stats = {"deleted": 0, "merged_rules": 0, "auto_inferred": 0, "groups_processed": 0}

    for source_type in (["book", "rss"] if args.book and args.rss else
                        (["book"] if args.book else ["rss"])):
        label = "书源" if source_type == "book" else "订阅源"
        url_key = "bookSourceUrl" if source_type == "book" else "sourceUrl"

        print(f"\n{'='*50}")
        print(f" {label}智能整合")
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
                      if len(srcs) >= 2 and is_dup_fn(srcs)}

        sorted_groups = sorted(dup_groups.items(), key=lambda x: -len(x[1]))

        total_in_dup = sum(len(v) for v in sorted_groups)
        print(f"  真重复域名: {len(dup_groups)} 个, 涉及 {total_in_dup} 个源")

        if args.max_groups > 0:
            sorted_groups = sorted_groups[:args.max_groups]
            print(f"  限制处理: {len(sorted_groups)} 个组")

        if not sorted_groups:
            print(f"  无重复源需要整合")
            continue

        # Step 3: 并发处理每个域名组
        sem = asyncio.Semaphore(args.concurrency)
        all_results = []
        progress = {"done": 0, "lock": asyncio.Lock()}

        async def _process_group(domain_srcs):
            domain, srcs = domain_srcs
            async with sem:
                r = await smart_merge_group(
                    domain, srcs, source_type, args.host, args.http_port, execute
                )
                all_results.append(r)
                async with progress["lock"]:
                    progress["done"] += 1
                    if progress["done"] % 10 == 0 or progress["done"] == len(sorted_groups):
                        print(f"  整合进度: {progress['done']}/{len(sorted_groups)} 组")

        tasks = [_process_group(g) for g in sorted_groups]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Step 4: 汇总并批量删除
        all_to_delete = []
        total_merged_rules = 0
        total_auto_inferred = 0
        for r in all_results:
            all_to_delete.extend(r["deleted_urls"])
            total_merged_rules += r["merged_rules"]
            total_auto_inferred += r["auto_inferred"]

        if execute and all_to_delete:
            print(f"\n  批量删除冗余源: {len(all_to_delete)} 个...")
            deleted = await api_delete_sources(all_to_delete, source_type, args.host, args.http_port)
            total_stats["deleted"] += deleted
            print(f"  删除完成: {deleted} 个")

        total_stats["merged_rules"] += total_merged_rules
        total_stats["auto_inferred"] += total_auto_inferred
        total_stats["groups_processed"] += len(all_results)

        print(f"\n  {label}整合汇总:")
        print(f"    处理组数: {len(all_results)}")
        print(f"    待删除冗余: {len(all_to_delete)} 个")
        print(f"    规则整合(验证匹配): {total_merged_rules} 条")
        print(f"    自动推断选择器: {total_auto_inferred} 条")

        # 输出每个组的详细信息
        for r in all_results[:10]:
            if r["details"]:
                print(f"\n  [{r['domain']}] ({r['source_count']}个源)")
                for d in r["details"]:
                    print(f"    {d}")

    # Step 5: 清理URL#重复
    if args.clean_hash or execute:
        print(f"\n{'='*50}")
        print(f" URL#重复清理")
        print(f"{'='*50}")
        for st in (["book", "rss"] if args.book and args.rss else
                   (["book"] if args.book else ["rss"])):
            # 复用V3的清理逻辑
            ss = await api_get_sources(st, args.host, args.http_port)
            uk = "bookSourceUrl" if st == "book" else "sourceUrl"
            clean_map = {}
            for s in ss:
                url = s.get(uk, "")
                if not url:
                    continue
                c = clean_url(url)
                if c:
                    clean_map.setdefault(c, []).append(url)

            to_del = []
            for cv, urls in clean_map.items():
                if len(urls) <= 1:
                    continue
                hash_urls = [u for u in urls if "#" in u]
                no_hash = [u for u in urls if "#" not in u]
                if hash_urls and no_hash:
                    to_del.extend(hash_urls)
                elif hash_urls:
                    to_del.extend(hash_urls[1:])

            if to_del:
                lb = "书源" if st == "book" else "订阅源"
                print(f"  {lb}#重复: 删除 {len(to_del)} 个")
                d = await api_delete_sources(to_del, st, args.host, args.http_port)
                total_stats["deleted"] += d

    # 最终统计
    final_book = len(await api_get_sources("book", args.host, args.http_port))
    final_rss = len(await api_get_sources("rss", args.host, args.http_port))

    print(f"\n{'='*60}")
    print(f" 智能整合V4完成")
    print(f" 处理组数: {total_stats['groups_processed']}")
    print(f" 总删除: {total_stats['deleted']} 个")
    print(f" 规则整合(验证匹配): {total_stats['merged_rules']} 条")
    print(f" 自动推断选择器: {total_stats['auto_inferred']} 条")
    print(f" 最终: 书源 {final_book}, 订阅源 {final_rss}")
    print(f"{'='*60}")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(
        SCRIPTS_DIR, "reports",
        f"smart-merge-v4-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "V4",
        "approach": "fetch_page->validate_rules_against_dom->merge_only_matching->auto_infer",
        "stats": total_stats,
        "final_counts": {"book": final_book, "rss": final_rss},
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f" 报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
