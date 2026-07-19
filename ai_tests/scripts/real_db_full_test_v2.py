#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源真机DB全量验证脚本 v2

相比 v1 (real_db_sample_test.py) 的改进：
1. 大幅扩展DOM选择器（list/pagination/categories/search_form）
2. 新增通用列表检测：a标签数 > 20 说明有列表
3. 新增图片统计：img[src]:not([src*="data:"]) 排除base64
4. 新增视频元素：video / iframe[src*="player"] / iframe[src*="video"] / embed / .player
5. 对全部183条源做全量测试（每源5秒超时）
6. 增量保存：每20个源保存一次
7. KeyboardInterrupt 捕获，用户中断时保存已处理结果
8. sortUrl相对路径拼接 sourceUrl 的 host

输出安全铁律：
- 脚本输出禁止包含源名称/URL/分类名原文
- 用源[idx]替代真实名称，URL用[URL]替代，域名用站点A/B/C替代
- 异常消息必须脱敏
- 浏览器用通用UA
"""
import sqlite3
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "output" / "rss" / "legado_test.db"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_real_test_db_sample_v2.json"

# 单源5秒超时（任务要求）
PAGE_TIMEOUT = 5000
NAV_WAIT_UNTIL = "domcontentloaded"

# 通用UA
COMMON_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
}
"""

# 扩展的DOM特征检测JS
LIST_FEATURE_JS = r"""
() => {
    // 扩展列表选择器：覆盖文章/视频/图片/卡片/网格等多种站点结构
    const listSelector = [
        'article', '.item', '.post', '.list-item', 'li.item', '.card',
        '.article-item', '.news-item',
        // 视频/影视站点
        '.video-item', '.vod-item', '.movie-item', '.pic-item',
        '.image-item', '.photo-item', '.thumb-item',
        // 通用条目
        '.entry', '.post-item', '.story',
        // 列表结构
        'ul.list li', 'ul.videos li', 'ul.images li',
        // 网格/栅格（Bootstrap等）
        '.row > div', '.grid > div',
        '.col-md-3', '.col-md-4', '.col-sm-6'
    ].join(', ');
    const list_items = document.querySelectorAll(listSelector);

    // 分页选择器
    const paginationSelector = [
        '.pagination', '.page-nav', '.pager', '.next-page',
        'a.next', 'a[rel=next]', '.page-next', '.next',
        '.pagebar', '.pagelink', 'a.pagelink_a',
        '.page-numbers', '.nav-links', 'ul.page li'
    ].join(', ');
    const pagination = document.querySelectorAll(paginationSelector);
    // 文本匹配的下一页（通过JS遍历a标签文本）
    let next_by_text = 0;
    document.querySelectorAll('a').forEach(a => {
        const txt = (a.textContent || '').trim();
        if (txt === '下一页' || txt === 'Next' || txt === 'next' || txt === '»') {
            next_by_text++;
        }
    });

    // 分类选择器
    const categorySelector = [
        '.category', '.sort', '.nav-category', '.cat-item',
        '.tag-cloud a', '.nav-sort', '.type-list', '.filter-list a',
        '.breadcrumb a', '.sidebar a', 'nav a', '.menu a'
    ].join(', ');
    const categories = document.querySelectorAll(categorySelector);

    // 搜索表单
    const searchSelector = [
        'form[action*="search"]', 'form#search',
        'input[name="search"]', 'input[name="q"]',
        'input[name="wd"]', 'input[type="search"]',
        '#searchform', '.search-form'
    ].join(', ');
    const search_form = document.querySelectorAll(searchSelector);

    // 图片统计（排除base64）
    const imgs = document.querySelectorAll('img[src]:not([src*="data:"])');

    // 视频元素
    const videoSelector = [
        'video',
        'iframe[src*="player"]', 'iframe[src*="video"]',
        'embed', '.player'
    ].join(', ');
    const videos = document.querySelectorAll(videoSelector);

    // 全部a标签数量（通用列表检测）
    const all_links = document.querySelectorAll('a');

    return {
        list_items: list_items.length,
        pagination: pagination.length + next_by_text,
        categories: categories.length,
        has_search_form: search_form.length > 0,
        imgs: imgs.length,
        videos: videos.length,
        all_links: all_links.length,
        body_text_len: (document.body && document.body.innerText) ? document.body.innerText.length : 0
    };
}
"""


def sanitize_url(url: str) -> str:
    """脱敏URL：替换为路径模式"""
    if not url:
        return "[EMPTY]"
    s = re.sub(r"https?://[^/\"' ]+", "[URL]", url)
    s = re.sub(r"\{\{.*?\}\}", "{tpl}", s)
    return s


def sanitize_exception(e: Exception) -> str:
    """异常消息脱敏：URL→[URL]，域名→[DOMAIN]"""
    msg = str(e)[:300]
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg


def extract_host(source_url: str) -> str:
    """从sourceUrl提取协议+host，用于拼接相对路径的sortUrl"""
    try:
        parsed = urlparse(source_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return ""


def resolve_sort_url(sort_url: str, source_url: str) -> str:
    """处理sortUrl：
    - 模板替换 {{page}}→1, {{key}}→test
    - 相对路径拼接 sourceUrl 的 host
    """
    if not sort_url:
        return ""
    # 替换模板
    test_url = sort_url.replace("{{page}}", "1").replace("{{key}}", "test")
    test_url = re.sub(r"\{\{.*?\}\}", "1", test_url)
    # 相对路径拼接
    if test_url.startswith(("http://", "https://")):
        return test_url
    if test_url.startswith("//"):
        host = extract_host(source_url)
        return ("https:" + test_url) if host else ""
    if test_url.startswith("/"):
        host = extract_host(source_url)
        return (host + test_url) if host else ""
    if test_url.startswith("./") or not test_url.startswith(("{{", "<")):
        # 相对路径
        host = extract_host(source_url)
        base_path = source_url.rsplit("/", 1)[0] if "/" in source_url else host
        if host:
            return urljoin(source_url, test_url)
    return ""


def load_db_sources() -> List[Dict]:
    """从DB加载全部订阅源"""
    if not DB_PATH.exists():
        print(f"[FATAL] DB not found: {DB_PATH}")
        return []
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rssSources")
    total = c.fetchone()[0]
    print(f"[INFO] total sources in DB: {total}")
    c.execute("PRAGMA table_info(rssSources)")
    cols = [r[1] for r in c.fetchall()]
    # 按 customOrder 排序（与原脚本一致按 type, sortUrl 排序）
    c.execute("SELECT * FROM rssSources ORDER BY type, customOrder")
    rows = c.fetchall()
    sources = [dict(zip(cols, row)) for row in rows]
    conn.close()
    return sources


def test_source(idx: int, source: Dict, page) -> Dict:
    """测试单个源（输出脱敏后的技术结论）

    检测项：
    - source_url_accessible: sourceUrl 可访问
    - list_items: 列表元素数量
    - pagination: 分页元素数量（>0 即 True）
    - search_form: 搜索表单存在
    - videos: 视频元素数量
    - images: 图片数量（排除base64）
    - categories: 分类元素数量
    """
    result = {
        "idx": idx,
        "type": source.get("type", 0) or 0,
        "source_url_accessible": False,
        "list_items_count": 0,
        "has_pagination": False,
        "has_search_form": False,
        "videos_found": 0,
        "imgs_found": 0,
        "categories_count": 0,
        "all_links_count": 0,
        "body_text_len": 0,
        "error": None,
    }
    source_url = (source.get("sourceUrl") or "").strip()
    sort_url = (source.get("sortUrl") or "").strip()

    if not source_url.startswith(("http://", "https://")):
        result["error"] = "invalid_source_url"
        return result

    # 1. 测试 sourceUrl 可访问性（同时检测首页DOM特征）
    try:
        page.goto(source_url, timeout=PAGE_TIMEOUT, wait_until=NAV_WAIT_UNTIL)
        result["source_url_accessible"] = True
    except Exception as e:
        result["error"] = f"source_url_access_fail: {sanitize_exception(e)}"
        return result

    # 2. 测试 sortUrl（分类列表）—— sortUrl 是分类列表加载地址
    # 优先使用 sortUrl，相对路径需要拼接 host
    target_url = None
    if sort_url:
        target_url = resolve_sort_url(sort_url, source_url)
    if not target_url:
        # sortUrl 缺失或无法解析，直接对 sourceUrl 做DOM特征分析
        target_url = source_url

    try:
        if target_url != source_url:
            page.goto(target_url, timeout=PAGE_TIMEOUT, wait_until=NAV_WAIT_UNTIL)
        features = page.evaluate(LIST_FEATURE_JS)
        if features:
            # list_items_count：扩展选择器匹配数，或通用列表检测（a标签>20也算有列表）
            list_count = int(features.get("list_items", 0))
            all_links = int(features.get("all_links", 0))
            # 如果扩展选择器没匹配到，但a标签数>20，认为有列表（取一个估算值）
            if list_count == 0 and all_links > 20:
                list_count = all_links  # 用 a 标签数作为 fallback
            result["list_items_count"] = list_count
            result["has_pagination"] = features.get("pagination", 0) > 0
            result["has_search_form"] = bool(features.get("has_search_form", False))
            result["videos_found"] = int(features.get("videos", 0))
            result["imgs_found"] = int(features.get("imgs", 0))
            result["categories_count"] = int(features.get("categories", 0))
            result["all_links_count"] = all_links
            result["body_text_len"] = int(features.get("body_text_len", 0))
    except Exception as e:
        result["error"] = f"sort_url_access_fail: {sanitize_exception(e)}"

    return result


def classify_result(r: Dict) -> str:
    """根据验证标准分类源
    - 完全可用：accessible + list_items>0 + (pagination or search_form)
    - 部分可用：accessible + list_items>0
    - 可访问但内容少：accessible
    - 不可访问：失败
    """
    if not r.get("source_url_accessible"):
        return "inaccessible"
    if r.get("list_items_count", 0) > 0 and (r.get("has_pagination") or r.get("has_search_form")):
        return "fully_usable"
    if r.get("list_items_count", 0) > 0:
        return "partially_usable"
    return "sparse"


def save_report(records: List[Dict]) -> None:
    """保存报告（增量）"""
    summary = {
        "stage": "real_db_full_test_v2",
        "total_tested": len(records),
        "accessible": sum(1 for r in records if r.get("source_url_accessible")),
        "with_list": sum(1 for r in records if r.get("list_items_count", 0) > 0),
        "with_pagination": sum(1 for r in records if r.get("has_pagination")),
        "with_search": sum(1 for r in records if r.get("has_search_form")),
        "with_videos": sum(1 for r in records if r.get("videos_found", 0) > 0),
        "with_images": sum(1 for r in records if r.get("imgs_found", 0) > 0),
        "fully_usable": sum(1 for r in records if classify_result(r) == "fully_usable"),
        "partially_usable": sum(1 for r in records if classify_result(r) == "partially_usable"),
        "sparse": sum(1 for r in records if classify_result(r) == "sparse"),
        "inaccessible": sum(1 for r in records if classify_result(r) == "inaccessible"),
        "errors": sum(1 for r in records if r.get("error")),
        "records": records,
    }
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 80)
    print("RSS v2 真机DB全量验证（扩展DOM选择器）")
    print("=" * 80)
    sources = load_db_sources()
    if not sources:
        print("[FATAL] no sources in DB")
        return
    total = len(sources)
    print(f"[INFO] testing all {total} sources (5s timeout each)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[FATAL] playwright not installed")
        return

    records: List[Dict] = []
    start_time = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=COMMON_UA,
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            for i, source in enumerate(sources):
                idx = i
                src_type = source.get("type", 0) or 0
                print(f"[{i+1}/{total}] testing source[{idx}] type={src_type}", flush=True)
                page = context.new_page()
                page.add_init_script(STEALTH_JS)
                page.set_default_timeout(PAGE_TIMEOUT)
                try:
                    result = test_source(idx, source, page)
                    records.append(result)
                    classification = classify_result(result)
                    print(
                        f"  -> accessible={result['source_url_accessible']} "
                        f"list={result['list_items_count']} "
                        f"pagination={result['has_pagination']} "
                        f"search={result['has_search_form']} "
                        f"videos={result['videos_found']} "
                        f"imgs={result['imgs_found']} "
                        f"cats={result['categories_count']} "
                        f"class={classification}",
                        flush=True,
                    )
                    if result.get("error"):
                        print(f"  [ERR] {result['error'][:120]}", flush=True)
                except Exception as e:
                    err = sanitize_exception(e)
                    records.append({
                        "idx": idx, "type": src_type,
                        "source_url_accessible": False,
                        "list_items_count": 0,
                        "has_pagination": False,
                        "has_search_form": False,
                        "videos_found": 0,
                        "imgs_found": 0,
                        "categories_count": 0,
                        "all_links_count": 0,
                        "body_text_len": 0,
                        "error": f"unexpected: {err}",
                    })
                    print(f"  [EXC] {err[:120]}", flush=True)
                finally:
                    page.close()

                # 增量保存：每20个源保存一次
                if (i + 1) % 20 == 0 or (i + 1) == total:
                    save_report(records)
                    elapsed = time.time() - start_time
                    print(
                        f"[PROGRESS] saved {len(records)}/{total} "
                        f"({elapsed:.0f}s elapsed)",
                        flush=True,
                    )

            browser.close()
    except KeyboardInterrupt:
        print("\n[WARN] interrupted by user, saving partial results...", flush=True)
        save_report(records)

    # 最终报告
    save_report(records)
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"[DONE] Tested {len(records)} sources in {elapsed:.0f}s")
    fully = sum(1 for r in records if classify_result(r) == "fully_usable")
    partial = sum(1 for r in records if classify_result(r) == "partially_usable")
    sparse = sum(1 for r in records if classify_result(r) == "sparse")
    inacc = sum(1 for r in records if classify_result(r) == "inaccessible")
    print(f"  完全可用 (accessible+list+pagination/search): {fully}")
    print(f"  部分可用 (accessible+list):                   {partial}")
    print(f"  可访问但内容少 (accessible only):             {sparse}")
    print(f"  不可访问:                                     {inacc}")
    print(f"[OUTPUT] {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
