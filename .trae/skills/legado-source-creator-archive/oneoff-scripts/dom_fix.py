#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DOM分析修复：抓取页面HTML → 分析DOM结构 → 生成CSS选择器 → 修复源规则。

核心思路：
1. 搜索失败(sea=N)的源 → 抓取搜索页HTML → 找书籍列表结构 → 生成ruleSearch
2. 详情失败(det=N)的源 → 抓取详情页HTML → 找书籍信息结构 → 生成ruleBookInfo
3. 目录失败(toc=N)的源 → 抓取目录页HTML → 找章节列表结构 → 生成ruleToc
4. 正文失败(con=N)的源 → 抓取正文页HTML → 找正文内容结构 → 生成ruleContent

用法:
    python dom_fix.py --input reports/retest-timeout-xxx.json --execute
    python dom_fix.py --input reports/retest-timeout-xxx.json --execute --stage search
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


# ==================== HTML 抓取 ====================

async def fetch_html(url: str, timeout: float = 15.0) -> Optional[str]:
    """抓取页面HTML。"""
    import httpx
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        ) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return r.text
    except Exception:
        pass
    return None


# ==================== DOM 分析 ====================

def analyze_search_page(html: str, base_url: str) -> Optional[Dict]:
    """分析搜索页面HTML，提取书籍列表结构和CSS选择器。"""
    if not html or len(html) < 100:
        return None

    # 常见书籍列表容器class/id模式
    list_patterns = [
        # class模式
        (r'class="([^"]*(?:book-list|novellist|result-list|search-list|booklist|grid|list-group)[^"]*)"', 'class'),
        (r'id="([^"]*(?:book-list|novellist|result-list|search-list|booklist|grid)[^"]*)"', 'id'),
        # ul/ol/dl 列表
        (r'<(ul|ol|dl)\s+[^>]*class="[^"]*(?:list|items|books)[^"]*"', 'tag'),
        # div 重复结构
        (r'<div\s+class="([^"]*(?:item|card|book|entry|row)[^"]*)"', 'class'),
    ]

    # 书名链接模式
    name_link_patterns = [
        r'<a[^>]*href="([^"]*(?:book|novel|chapter|detail)[^"]*)"[^>]*>([^<]{1,50})</a>',
        r'<a[^>]*href="(/\d+/\d+/?)\s*"[^>]*>([^<]{1,50})</a>',
    ]

    # 作者模式
    author_patterns = [
        r'(?:作者|著|Author)[：:]\s*([^<\s]{1,30})',
        r'class="[^"]*(?:author|writer|authorName)[^"]*"[^>]*>([^<]{1,30})',
        r'<span[^>]*class="[^"]*author[^"]*"[^>]*>([^<]{1,30})</span>',
    ]

    result = {
        "bookList_selector": None,
        "name_selector": None,
        "author_selector": None,
        "bookUrl_selector": None,
        "coverUrl_selector": None,
        "searchUrl_template": None,
    }

    # 找书籍列表容器
    for pattern, ptype in list_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            if ptype == 'class':
                result["bookList_selector"] = f".{matches[0].split()[0]}"
            elif ptype == 'id':
                result["bookList_selector"] = f"#{matches[0]}"
            elif ptype == 'tag':
                result["bookList_selector"] = f"{matches[0]}.list"
            break

    # 如果没找到列表容器，尝试用重复div结构
    if not result["bookList_selector"]:
        # 找重复出现的div class
        div_classes = re.findall(r'<div\s+class="([^"]+)"', html)
        class_counts = {}
        for cls in div_classes:
            cls_first = cls.split()[0]
            class_counts[cls_first] = class_counts.get(cls_first, 0) + 1
        # 出现3次以上的可能是列表项
        repeated = [(c, n) for c, n in class_counts.items() if n >= 3]
        if repeated:
            repeated.sort(key=lambda x: -x[1])
            result["bookList_selector"] = f".{repeated[0][0]}"

    # 找书名和链接
    for pattern in name_link_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches and len(matches) >= 2:
            # 找到多个书名链接
            href, text = matches[0]
            # 生成bookUrl选择器 - 找包含书籍链接的a标签
            if "book" in href.lower() or "novel" in href.lower() or "detail" in href.lower():
                result["bookUrl_selector"] = "a@href"
                result["name_selector"] = "a@text"
            break

    # 如果还没找到，用更宽松的模式
    if not result["name_selector"]:
        # 找所有包含中文的链接文本
        cn_links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([\u4e00-\u9fff]{2,20})</a>', html)
        if len(cn_links) >= 2:
            result["name_selector"] = "a@text"
            result["bookUrl_selector"] = "a@href"

    # 找作者
    for pattern in author_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            # 找到作者模式，生成选择器
            if "author" in pattern.lower():
                result["author_selector"] = ".author@text"
            else:
                result["author_selector"] = "span.author@text"
            break

    # 生成searchUrl模板
    parsed = urlparse(base_url)
    domain_base = f"{parsed.scheme}://{parsed.hostname}"
    # 常见搜索URL模板
    result["searchUrl_template"] = f"{domain_base}/search?q={{key}}"

    return result if result["bookList_selector"] else None


def analyze_detail_page(html: str) -> Optional[Dict]:
    """分析详情页HTML，提取书籍信息结构和CSS选择器。"""
    if not html or len(html) < 100:
        return None

    result = {
        "name_selector": None,
        "author_selector": None,
        "intro_selector": None,
        "coverUrl_selector": None,
        "tocUrl_selector": None,
        "lastChapter_selector": None,
    }

    # 书名 - h1/h2 标签
    h1_match = re.search(r'<h[12][^>]*>([^<]{2,50})</h[12]>', html)
    if h1_match:
        result["name_selector"] = "h1@text"

    # 作者
    author_patterns = [
        r'(?:作者|著)[：:]\s*<[^>]*>([^<]{1,30})',
        r'class="[^"]*author[^"]*"[^>]*>([^<]{1,30})',
    ]
    for p in author_patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            result["author_selector"] = ".author@text"
            break

    # 简介
    intro_patterns = [
        r'class="[^"]*(?:intro|desc|summary|description)[^"]*"',
        r'(?:简介|介绍|内容简介)[：:]',
    ]
    for p in intro_patterns:
        if re.search(p, html, re.IGNORECASE):
            result["intro_selector"] = ".intro@text"
            break

    # 封面
    cover_match = re.search(r'<img[^>]*src="([^"]*(?:cover|pic|image|img)[^"]*)"', html, re.IGNORECASE)
    if cover_match:
        result["coverUrl_selector"] = "img.cover@src"

    # 目录链接
    toc_match = re.search(r'<a[^>]*href="([^"]*(?:chapter|catalog|list|mulu)[^"]*)"', html, re.IGNORECASE)
    if toc_match:
        result["tocUrl_selector"] = "a[href*=chapter]@href"

    return result if any(result.values()) else None


def analyze_toc_page(html: str) -> Optional[Dict]:
    """分析目录页HTML，提取章节列表结构和CSS选择器。"""
    if not html or len(html) < 100:
        return None

    result = {
        "chapterList_selector": None,
        "chapterName_selector": None,
        "chapterUrl_selector": None,
    }

    # 找章节列表容器
    list_patterns = [
        r'class="[^"]*(?:chapter-list|list-main|chapter_list|mulu)[^"]*"',
        r'id="[^"]*(?:chapter-list|list-main|chapter_list|mulu)[^"]*"',
    ]
    for p in list_patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            cls_match = re.search(r'class="([^"]*)"', m.group())
            if cls_match:
                result["chapterList_selector"] = f".{cls_match.group(1).split()[0]}"
            break

    # 如果没找到，用dd/li列表
    if not result["chapterList_selector"]:
        dd_count = html.count("<dd")
        li_count = html.count("<li")
        if dd_count >= 5:
            result["chapterList_selector"] = "dd"
        elif li_count >= 5:
            result["chapterList_selector"] = "li"

    # 章节名和链接
    chapter_links = re.findall(
        r'<a[^>]*href="([^"]*(?:chapter|/\d+)[^"]*)"[^>]*>([^<]{2,50})</a>',
        html, re.IGNORECASE
    )
    if len(chapter_links) >= 3:
        result["chapterName_selector"] = "a@text"
        result["chapterUrl_selector"] = "a@href"

    return result if result["chapterList_selector"] else None


def analyze_content_page(html: str) -> Optional[Dict]:
    """分析正文页HTML，提取正文内容结构和CSS选择器。"""
    if not html or len(html) < 100:
        return None

    result = {
        "content_selector": None,
    }

    # 正文容器
    content_patterns = [
        r'class="[^"]*(?:content|text|article|read|bookcontent|txt)[^"]*"',
        r'id="[^"]*(?:content|text|article|read|bookcontent)[^"]*"',
    ]
    for p in content_patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            cls_match = re.search(r'(?:class|id)="([^"]*)"', m.group())
            if cls_match:
                first_cls = cls_match.group(1).split()[0]
                if p.startswith("class"):
                    result["content_selector"] = f".{first_cls}@html"
                else:
                    result["content_selector"] = f"#{first_cls}@html"
            break

    # 如果没找到，尝试找包含大量中文文本的p/div标签
    if not result["content_selector"]:
        # 找含多个段落的div
        p_blocks = re.findall(r'<div[^>]*class="([^"]*)"[^>]*>(?:\s*<p>.*?</p>\s*){3,}', html, re.DOTALL)
        if p_blocks:
            result["content_selector"] = f".{p_blocks[0].split()[0]}@html"

    return result if result["content_selector"] else None


# ==================== 搜索URL探测 ====================

async def probe_search_url(source: Dict, timeout: float = 10.0) -> Optional[str]:
    """并发探测网站的搜索接口。"""
    import httpx

    base_url = source.get("bookSourceUrl", "").split("#")[0].strip().rstrip("/")
    if not base_url:
        return None

    candidates = []
    for path in ["/search", "/search.html", "/s.php", "/search.php",
                 "/so.php", "/search.aspx", "/s/"]:
        for param in ["?q={{key}}", "?keyword={{key}}", "?searchkey={{key}}", "?wd={{key}}"]:
            candidates.append(f"{base_url}{path}{param}")

    # 去重
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    candidates = unique[:15]

    sem = asyncio.Semaphore(5)
    search_keywords = ["斗破苍穹", "斗罗大陆", "遮天"]

    async def _probe(url_template: str) -> Optional[str]:
        async with sem:
            test_url = url_template.replace("{{key}}", quote(search_keywords[0]))
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout, connect=5.0),
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"},
                ) as client:
                    r = await client.get(test_url)
                    if r.status_code == 200 and len(r.text) > 500:
                        # 检查是否有搜索结果
                        text = r.text.lower()
                        if any(kw in text for kw in ["斗破", "搜索结果", "book-list", "novellist",
                                                      "搜索到", "找到", "result"]):
                            return url_template
            except Exception:
                pass
            return None

    results = await asyncio.gather(*[_probe(c) for c in candidates])
    for r in results:
        if r:
            return r
    return None


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="DOM分析修复")
    parser.add_argument("--input", type=str, required=True, help="重测报告JSON路径")
    parser.add_argument("--execute", action="store_true", help="执行保存到真机")
    parser.add_argument("--stage", type=str, default="all", help="只修复指定阶段: search/detail/toc/content/all")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    print("=" * 60)
    print(f" DOM分析修复 (stage={args.stage})")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载报告
    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)

    results = report.get("results", [])

    # 按失败阶段分类
    search_fail = []  # sea=N
    detail_fail = []  # det=N
    toc_fail = []     # toc=N
    content_fail = [] # con=N

    for r in results:
        if r["status"] == "success":
            continue
        if "WS_TIMEOUT" in r.get("errors", []):
            continue
        s = r["stages"]
        if not s["search"]:
            search_fail.append(r)
        if s["search"] and not s["detail"]:
            detail_fail.append(r)
        if s["detail"] and not s["toc"]:
            toc_fail.append(r)
        if s["toc"] and not s["content"]:
            content_fail.append(r)

    print(f" 搜索失败: {len(search_fail)}")
    print(f" 详情失败: {len(detail_fail)}")
    print(f" 目录失败: {len(toc_fail)}")
    print(f" 正文失败: {len(content_fail)}")

    # 获取真机源
    client = LegadoWebClient(host="127.0.0.1", port=1122)
    all_sources = await client.get_book_sources()
    source_map = {s.get("bookSourceUrl", ""): s for s in all_sources}
    print(f" 真机书源总数: {len(all_sources)}")

    fixed_sources = []
    fix_stats = {
        "search_probe": 0, "search_dom": 0,
        "detail_dom": 0, "toc_dom": 0, "content_dom": 0,
        "no_html": 0, "no_match": 0,
    }

    # Phase 1: 修复搜索失败 - 探测搜索URL
    if args.stage in ("all", "search") and search_fail:
        print(f"\n=== Phase 1: 搜索URL探测 ({len(search_fail)} 个源) ===")
        sem = asyncio.Semaphore(10)

        async def _fix_search(r):
            nonlocal fix_stats
            url = r.get("source_url", "")
            if url not in source_map:
                return
            source = source_map[url]
            if source.get("searchUrl"):
                return  # 已有searchUrl

            # 先探测搜索URL
            found = await probe_search_url(source, timeout=10)
            if found:
                source["searchUrl"] = found
                fixed_sources.append(source)
                fix_stats["search_probe"] += 1
                return

            # 探测失败，尝试抓取首页找搜索框
            base_url = source.get("bookSourceUrl", "").split("#")[0].strip()
            html = await fetch_html(base_url, timeout=10)
            if html:
                # 找搜索表单action
                form_match = re.search(r'<form[^>]*action="([^"]*)"[^>]*>', html, re.IGNORECASE)
                if form_match:
                    action = form_match.group(1)
                    if not action.startswith("http"):
                        action = urljoin(base_url, action)
                    # 找input name
                    input_match = re.search(r'<input[^>]*name="([^"]*)"', html, re.IGNORECASE)
                    param_name = input_match.group(1) if input_match else "q"
                    source["searchUrl"] = f"{action}?{param_name}={{key}}"
                    fixed_sources.append(source)
                    fix_stats["search_dom"] += 1
                    return

            fix_stats["no_match"] += 1

        tasks = [_fix_search(r) for r in search_fail]
        await asyncio.gather(*tasks)
        print(f"  搜索URL探测成功: {fix_stats['search_probe']}")
        print(f"  搜索表单发现: {fix_stats['search_dom']}")
        print(f"  未找到: {fix_stats['no_match']}")

    # Phase 2: 修复详情/目录/正文失败 - DOM分析
    if args.stage in ("all", "detail") and detail_fail:
        print(f"\n=== Phase 2: 详情页DOM分析 ({len(detail_fail)} 个源) ===")
        # 对详情失败的源，先通过搜索获取一个详情页URL
        # 这里比较复杂，先跳过，后续用真机调试获取详情页
        print("  (需要先获取详情页URL，暂跳过)")

    if args.stage in ("all", "toc") and toc_fail:
        print(f"\n=== Phase 3: 目录页DOM分析 ({len(toc_fail)} 个源) ===")
        for r in toc_fail[:50]:  # 只处理前50个
            url = r.get("source_url", "")
            if url not in source_map:
                continue
            source = source_map[url]
            toc_url = source.get("ruleBookInfo", {}).get("tocUrl", "")
            if not toc_url:
                continue
            # 尝试构建目录页URL
            base_url = source.get("bookSourceUrl", "").split("#")[0].strip()
            if toc_url.startswith("/"):
                full_toc = urljoin(base_url, toc_url)
            else:
                full_toc = toc_url

            html = await fetch_html(full_toc, timeout=10)
            if html:
                result = analyze_toc_page(html)
                if result:
                    rule_toc = source.get("ruleToc", {})
                    if not isinstance(rule_toc, dict):
                        rule_toc = {}
                    for k, v in result.items():
                        if v and not rule_toc.get(k.replace("_selector", "")):
                            rule_toc[k.replace("_selector", "")] = v
                    source["ruleToc"] = rule_toc
                    fixed_sources.append(source)
                    fix_stats["toc_dom"] += 1
            else:
                fix_stats["no_html"] += 1

        print(f"  目录DOM修复: {fix_stats['toc_dom']}")
        print(f"  无法获取HTML: {fix_stats['no_html']}")

    if args.stage in ("all", "content") and content_fail:
        print(f"\n=== Phase 4: 正文页DOM分析 ({len(content_fail)} 个源) ===")
        for r in content_fail[:50]:
            url = r.get("source_url", "")
            if url not in source_map:
                continue
            source = source_map[url]
            # 需要先获取一个章节URL
            print(f"  跳过 {r.get('source_name', '?')} (需要章节URL)")

    # 去重fixed_sources
    seen_urls = set()
    unique_fixed = []
    for s in fixed_sources:
        u = s.get("bookSourceUrl", "")
        if u not in seen_urls:
            seen_urls.add(u)
            unique_fixed.append(s)
    fixed_sources = unique_fixed

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
        print(f"保存到真机: {saved}/{len(fixed_sources)}")

        # 重试验证
        print(f"\n开始重试验证...")
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
                    parsed = _parse_logs(logs)
                    stages_passed = sum(1 for v in parsed["stages"].values() if v)
                    if stages_passed >= 4:
                        improved += 1
                    verified += 1
                    if verified % 20 == 0:
                        print(f"  验证: {verified}/{len(fixed_sources)}, 改善: {improved}")
                except Exception:
                    verified += 1

        await asyncio.gather(*[_verify(s) for s in fixed_sources])
        print(f"验证结果: {verified} 已验证, {improved} 有改善")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = args.output or os.path.join(
        SCRIPTS_DIR, "reports",
        f"dom-fix-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "fix_stats": fix_stats,
        "fixed_count": len(fixed_sources),
        "fixed_sources": [{"url": s.get("bookSourceUrl", ""), "name": s.get("bookSourceName", "?")}
                         for s in fixed_sources],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    await client.close()


def _parse_logs(logs):
    result = {"stages": {"search": False, "detail": False, "toc": False, "content": False}, "errors": []}
    for msg in logs:
        if "列表大小" in msg or "搜索结果" in msg:
            result["stages"]["search"] = True
        if "获取书名" in msg:
            result["stages"]["detail"] = True
        if "目录总数" in msg or "章节列表" in msg:
            result["stages"]["toc"] = True
        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            result["stages"]["content"] = True
        if "UnknownHostException" in msg:
            result["errors"].append("DNS")
    return result


if __name__ == "__main__":
    asyncio.run(main())
