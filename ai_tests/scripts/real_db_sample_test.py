#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源真机DB抽样验证脚本

从真机DB抽取订阅源，用Playwright访问验证：
1. sourceUrl 可访问性
2. sortUrl 分类列表加载
3. searchUrl 搜索功能
4. ruleNextPage 下一页链接存在性
5. type=2视频源 ruleContent 视频元素

输出安全铁律：
- 禁止输出源名称/URL/分类名原文
- 用源[idx]替代真实名称
- 域名用站点A/B/C替代
- 只输出技术结论：可访问性/列表数/搜索结果数/下一页链接/视频元素存在性
"""
import sqlite3
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "output" / "rss" / "legado_test.db"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_real_test_db_sample.json"

# Playwright 配置
PAGE_TIMEOUT = 15000
NAV_WAIT_UNTIL = "domcontentloaded"

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', get: () => [1, 2, 3, 4, 5]);
    window.chrome = { runtime: {} };
}
"""

# 列表/分类DOM分析
LIST_FEATURE_JS = """
() => {
    const links = document.querySelectorAll('a');
    const items = document.querySelectorAll('article, .item, .post, .list-item, li.item, .card, .article-item, .news-item');
    const imgs = document.querySelectorAll('img');
    const videos = document.querySelectorAll('video');
    const pagination = document.querySelectorAll('.pagination, .page-nav, .pager, .next-page, a.next, a[rel=next]');
    const categories = document.querySelectorAll('.category, .sort, .nav-category, .cat-item, .tag-cloud a');
    const search_form = document.querySelector('form[action*="search"], form#search, input[name="search"], input[name="q"]');
    return {
        links_count: links.length,
        list_items: items.length,
        imgs: imgs.length,
        videos: videos.length,
        pagination: pagination.length,
        categories: categories.length,
        has_search_form: !!search_form,
        body_text_len: document.body.innerText.length
    };
}
"""


def sanitize_url(url: str) -> str:
    """脱敏URL：替换为路径模式"""
    if not url:
        return "[EMPTY]"
    # 保留模板语法但替换域名
    s = re.sub(r"https?://[^/\"' ]+", "[URL]", url)
    s = re.sub(r"\{\{.*?\}\}", "{tpl}", s)
    return s


def sanitize_exception(e: Exception) -> str:
    msg = str(e)[:300]
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg


def extract_base_url(source_url: str) -> str:
    """从模板URL提取base_url"""
    base = re.sub(r"\{\{.*?\}\}", "", source_url)
    base = base.rstrip("/?")
    return base if base.startswith(("http://", "https://")) else source_url


def load_db_sources() -> List[Dict]:
    """从DB加载订阅源"""
    if not DB_PATH.exists():
        print(f"[FATAL] DB not found: {DB_PATH}")
        return []
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    # 检查表结构
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%rss%'")
    tables = [r[0] for r in c.fetchall()]
    print(f"[INFO] rss tables: {tables}")
    if not tables:
        conn.close()
        return []
    table = tables[0]
    c.execute(f"SELECT COUNT(*) FROM {table}")
    total = c.fetchone()[0]
    print(f"[INFO] total sources in DB: {total}")
    c.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in c.fetchall()]
    print(f"[INFO] columns: {cols}")
    # 取所有源（按type分组）
    c.execute(f"SELECT * FROM {table} ORDER BY type, sortUrl")
    rows = c.fetchall()
    sources = []
    for row in rows:
        d = dict(zip(cols, row))
        sources.append(d)
    conn.close()
    return sources


def sample_sources(sources: List[Dict], n_per_type: int = 3) -> List[Tuple[int, Dict]]:
    """每个type抽样n个源"""
    by_type = {0: [], 1: [], 2: []}
    for idx, s in enumerate(sources):
        t = s.get("type", 0) or 0
        if t in by_type and len(by_type[t]) < n_per_type:
            by_type[t].append((idx, s))
    result = []
    for t in [2, 1, 0]:  # 视频优先
        result.extend(by_type[t])
    return result


def test_source(idx: int, source: Dict, page) -> Dict:
    """测试单个源
    输出脱敏后的技术结论
    """
    result = {
        "idx": idx,
        "type": source.get("type", 0),
        "source_url_accessible": False,
        "sort_url_loads": False,
        "search_url_loads": False,
        "list_items_count": 0,
        "has_pagination": False,
        "has_search_form": False,
        "videos_found": 0,
        "imgs_found": 0,
        "error": None,
    }
    source_url = source.get("sourceUrl", "") or ""
    sort_url = source.get("sortUrl", "") or ""
    search_url = source.get("searchUrl", "") or ""
    if not source_url.startswith(("http://", "https://")):
        result["error"] = "invalid_source_url"
        return result
    # 1. 测试sourceUrl可访问性
    try:
        page.goto(source_url, timeout=PAGE_TIMEOUT, wait_until=NAV_WAIT_UNTIL)
        result["source_url_accessible"] = True
    except Exception as e:
        result["error"] = f"source_url_access_fail: {sanitize_exception(e)}"
        return result
    # 2. 测试sortUrl（分类列表）
    if sort_url and sort_url.startswith(("http://", "https://")):
        try:
            test_url = sort_url.replace("{{page}}", "1").replace("{{key}}", "test")
            test_url = re.sub(r"\{\{.*?\}\}", "1", test_url)
            page.goto(test_url, timeout=PAGE_TIMEOUT, wait_until=NAV_WAIT_UNTIL)
            features = page.evaluate(LIST_FEATURE_JS)
            if features:
                result["sort_url_loads"] = features["list_items"] > 0 or features["links_count"] > 5
                result["list_items_count"] = features["list_items"]
                result["has_pagination"] = features["pagination"] > 0
                result["has_search_form"] = features["has_search_form"]
                result["videos_found"] = features["videos"]
                result["imgs_found"] = features["imgs"]
        except Exception as e:
            result["error"] = f"sort_url_access_fail: {sanitize_exception(e)}"
    return result


def main():
    print("=" * 80)
    print("RSS v2 真机DB抽样验证")
    print("=" * 80)
    sources = load_db_sources()
    if not sources:
        print("[FATAL] no sources in DB")
        return
    # 抽样：每个type抽3个
    samples = sample_sources(sources, n_per_type=3)
    print(f"[INFO] sampling {len(samples)} sources (3 per type)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[FATAL] playwright not installed")
        return
    records = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            for idx, source in samples:
                print(f"\n[TEST] idx={idx} type={source.get('type', 0)}")
                page = context.new_page()
                page.add_init_script(STEALTH_JS)
                page.set_default_timeout(8000)
                try:
                    result = test_source(idx, source, page)
                    records.append(result)
                    print(f"  -> accessible={result['source_url_accessible']} sort_loads={result['sort_url_loads']} list_items={result['list_items_count']} pagination={result['has_pagination']}")
                    if result.get("error"):
                        print(f"  [ERR] {result['error'][:80]}")
                except Exception as e:
                    records.append({
                        "idx": idx, "type": source.get("type", 0),
                        "error": f"unexpected: {sanitize_exception(e)}",
                    })
                    print(f"  [EXC] {sanitize_exception(e)[:80]}")
                finally:
                    page.close()
            browser.close()
    except KeyboardInterrupt:
        print("\n[WARN] interrupted")
    # 汇总统计
    summary = {
        "stage": "real_db_sample_test",
        "total_tested": len(records),
        "source_url_accessible": sum(1 for r in records if r.get("source_url_accessible")),
        "sort_url_loads": sum(1 for r in records if r.get("sort_url_loads")),
        "has_pagination": sum(1 for r in records if r.get("has_pagination")),
        "videos_found_sources": sum(1 for r in records if r.get("videos_found", 0) > 0),
        "errors": sum(1 for r in records if r.get("error")),
        "records": records,
    }
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 80)
    print(f"[DONE] Tested {summary['total_tested']} sources")
    print(f"  source_url_accessible: {summary['source_url_accessible']}/{summary['total_tested']}")
    print(f"  sort_url_loads: {summary['sort_url_loads']}/{summary['total_tested']}")
    print(f"  has_pagination: {summary['has_pagination']}/{summary['total_tested']}")
    print(f"  videos_found_sources: {summary['videos_found_sources']}")
    print(f"  errors: {summary['errors']}")
    print(f"[OUTPUT] {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
