#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段5 Playwright批量字段补全

职责：
1. 读取阶段4拆分后的JSON（含子源）
2. Playwright 访问每个源首页
3. 提取11字段：
   - 必填(6): sourceIcon/searchUrl/ruleArticles/ruleTitle/ruleLink/ruleImage
   - 推荐(5): sortUrl/ruleNextPage/rulePubDate/ruleContent
4. 字段补全策略矩阵（见 design.md §11）
5. 失败不中断，记录到报告

输出安全铁律（不可违背）：
- 脚本输出禁止包含业务字段原文
- 只输出技术指标：idx, fields_extracted_count, failed_count
- Playwright 异常消息必须脱敏

输入：output/rss/splitted_v2.json
输出：
  - output/rss/optimized_v2.json（含补全字段的JSON）
  - output/rss/v2_optimization_report.json（优化报告，仅技术指标）
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse, urljoin

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "splitted_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_optimization_report.json"

PAGE_TIMEOUT = 20000
MAX_RETRY = 2

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
}
"""

# 字段提取JS
EXTRACT_FIELDS_JS = """
() => {
    const result = {};
    
    // 1. sourceIcon
    const icon_link = document.querySelector('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
    result.sourceIcon = icon_link ? icon_link.href : '';
    
    // 2. searchUrl
    const search_form = document.querySelector('form[action*="search"], form#search, form.search, form[action*="Search"]');
    if (search_form) {
        const action = search_form.getAttribute('action') || '';
        const method = (search_form.getAttribute('method') || 'get').toLowerCase();
        const input = search_form.querySelector('input[name]:not([type="submit"]):not([type="button"]):not([type="reset"])');
        if (input && input.name) {
            const base_url = action.startsWith('http') ? action : 
                            action.startsWith('/') ? location.origin + action :
                            location.origin + location.pathname.replace(/[^/]*$/, '') + action;
            if (method === 'get') {
                result.searchUrl = base_url + (base_url.includes('?') ? '&' : '?') + input.name + '={{key}}';
            } else {
                result.searchUrl = base_url + ',' + method + ',' + input.name + '={{key}}';
            }
        }
    }
    
    // 3. ruleArticles - 自动识别文章列表容器
    const list_selectors = [
        '.post-list', '.article-list', '.news-list', '.blog-list', '.card-list',
        'ul.posts li', 'ul.news li', 'ul.articles li', 'ul.list li',
        '.list-item', '.item', '.card', '.post',
        '.videos-list .item', '.video-list .item', '.pic-list li',
        '.gallery-list .item', '.image-list .item'
    ];
    for (const sel of list_selectors) {
        const items = document.querySelectorAll(sel);
        if (items.length >= 3) {
            result.ruleArticles = sel;
            break;
        }
    }
    // 兜底：找第一个含有3个以上 a[href] 的 ul/ol/div
    if (!result.ruleArticles) {
        const containers = document.querySelectorAll('ul, ol, .list, .content, .main');
        for (const c of containers) {
            const links = c.querySelectorAll('li a[href], .item a[href], a[href]');
            if (links.length >= 3) {
                const cls = c.className ? c.className.split(' ')[0] : c.tagName.toLowerCase();
                result.ruleArticles = cls + (c.tagName === 'UL' || c.tagName === 'OL' ? ' li' : ' .item');
                break;
            }
        }
    }
    
    // 4. ruleTitle / ruleLink / ruleImage 基于ruleArticles上下文提取
    if (result.ruleArticles) {
        const first_item = document.querySelector(result.ruleArticles);
        if (first_item) {
            // ruleTitle
            const title_el = first_item.querySelector('h1, h2, h3, h4, .title, .post-title, .item-title, .name');
            if (title_el) {
                const tag = title_el.tagName.toLowerCase();
                const cls = title_el.className ? title_el.className.split(' ')[0] : '';
                result.ruleTitle = cls ? tag + '.' + cls : tag;
            } else {
                result.ruleTitle = 'a';
            }
            
            // ruleLink
            const link_el = first_item.querySelector('a[href]');
            result.ruleLink = 'a@href';
            
            // ruleImage
            const img_el = first_item.querySelector('img');
            if (img_el) {
                const src_attr = img_el.getAttribute('data-src') ? 'data-src' :
                                img_el.getAttribute('data-original') ? 'data-original' :
                                img_el.getAttribute('data-lazy-src') ? 'data-lazy-src' : 'src';
                result.ruleImage = 'img@' + src_attr;
            } else {
                result.ruleImage = '';
            }
        }
    }
    
    // 5. sortUrl - 提取分类导航链接
    const sort_links = [];
    const nav_links = document.querySelectorAll('.nav a, .category a, .sort a, .menu a, nav a, .sidebar a');
    nav_links.forEach(a => {
        const text = a.textContent.trim();
        if (text.length >= 2 && text.length <= 10 && a.href.includes(location.host)) {
            sort_links.push(text + ':' + a.href);
        }
    });
    result.sortUrl = sort_links.slice(0, 10).join('&&');
    
    // 6. ruleNextPage
    const next_link = document.querySelector('a.next, a[rel="next"], .pagination a:last-child, .page-next a, a:contains("下一页"), a:contains("Next")');
    if (next_link) {
        const href = next_link.getAttribute('href');
        if (href) {
            result.ruleNextPage = 'a.next@href';
        }
    }
    if (!result.ruleNextPage) {
        // 查找含"下一页"/"next"的链接
        const all_links = document.querySelectorAll('a');
        for (const a of all_links) {
            if (/下一页|next page|»|>/i.test(a.textContent) && a.getAttribute('href')) {
                result.ruleNextPage = 'a@href';
                break;
            }
        }
    }
    
    // 7. rulePubDate
    const date_el = first_item?.querySelector('.date, .time, .pub-date, time, .published');
    if (date_el) {
        result.rulePubDate = '.date@text||.time@text||time@datetime';
    }
    
    return result;
}
"""


def sanitize_exception(e: Exception) -> str:
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def extract_base_url(source_url: str) -> str:
    if "{{" in source_url:
        base = re.sub(r"\{\{.*?\}\}", "", source_url)
        base = base.rstrip("/?")
        if base.startswith(("http://", "https://")):
            return base
    return source_url


def apply_field_defaults(source: dict) -> int:
    """对未补全的必填字段应用兜底策略，返回兜底字段数"""
    defaults_applied = 0
    source_url = source.get("sourceUrl", "") or ""

    # sourceIcon 兜底：用 sourceUrl 拼接 /favicon.ico
    if not source.get("sourceIcon"):
        try:
            parsed = urlparse(source_url)
            if parsed.scheme and parsed.netloc:
                source["sourceIcon"] = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
                defaults_applied += 1
        except Exception:
            pass

    # searchUrl 兜底：Google site: 搜索
    if not source.get("searchUrl"):
        try:
            parsed = urlparse(source_url)
            if parsed.netloc:
                source["searchUrl"] = f"https://www.google.com/search?q={{key}}+site:{parsed.netloc}"
                defaults_applied += 1
        except Exception:
            pass

    # ruleArticles / ruleTitle / ruleLink / ruleImage 兜底：通用CSS选择器
    if not source.get("ruleArticles"):
        source["ruleArticles"] = "ul li"
        defaults_applied += 1
    if not source.get("ruleTitle"):
        source["ruleTitle"] = "a"
        defaults_applied += 1
    if not source.get("ruleLink"):
        source["ruleLink"] = "a@href"
        defaults_applied += 1
    if not source.get("ruleImage"):
        source["ruleImage"] = "img@src"
        defaults_applied += 1

    # sortUrl 兜底：用 sourceUrl 作为单一分类
    if not source.get("sortUrl"):
        source["sortUrl"] = "全部:" + source_url
        defaults_applied += 1

    return defaults_applied


def main():
    print("=" * 80)
    print("RSS v2 阶段5 Playwright批量字段补全")
    print("=" * 80)

    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        print(f"        请先运行阶段4导航站拆分脚本 split_navigation_source_v2.py")
        return

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {sanitize_exception(e)}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[FATAL] playwright 未安装")
        return

    optimized_sources: List[dict] = []
    report_records: List[dict] = []

    field_stats = {
        'sourceIcon': 0, 'searchUrl': 0, 'ruleArticles': 0,
        'ruleTitle': 0, 'ruleLink': 0, 'ruleImage': 0,
        'sortUrl': 0, 'ruleNextPage': 0, 'rulePubDate': 0,
    }

    success_count = 0
    failed_count = 0
    defaults_total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        for idx, source in enumerate(sources):
            source_url = source.get("sourceUrl", "") or ""

            # 跳过不可访问的源
            if not source_url.startswith(("http://", "https://")):
                comment = source.get("sourceComment", "") or ""
                if "[AI_PREPROCESS:needs_manual" in comment or "[AI_CLASSIFY:skipped" in comment:
                    # 应用兜底策略后跳过
                    defaults_applied = apply_field_defaults(source)
                    defaults_total += defaults_applied
                    optimized_sources.append(source)
                    report_records.append({
                        "idx": idx, "status": "skipped", "defaults_applied": defaults_applied
                    })
                    continue

            access_url = extract_base_url(source_url)

            page = None
            success = False
            fields_extracted = {}

            for attempt in range(MAX_RETRY + 1):
                try:
                    page = context.new_page()
                    page.add_init_script(STEALTH_JS)
                    page.goto(access_url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)  # 等待JS渲染

                    fields_extracted = page.evaluate(EXTRACT_FIELDS_JS)
                    success = True
                    break
                except Exception as e:
                    if attempt == MAX_RETRY:
                        err_msg = sanitize_exception(e)
                        if (idx + 1) % 10 == 0 or idx < 5:
                            print(f"  [FAIL] idx={idx} err={err_msg[:80]}")
                    else:
                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass
                finally:
                    if page:
                        try:
                            page.close()
                        except Exception:
                            pass

            if success and fields_extracted:
                # 只在原值为空时填充新值（不覆盖用户已有的值）
                for field, value in fields_extracted.items():
                    if value and not source.get(field):
                        source[field] = value
                        if field in field_stats:
                            field_stats[field] += 1

                # 应用兜底策略
                defaults_applied = apply_field_defaults(source)
                defaults_total += defaults_applied
                success_count += 1
            else:
                # 访问失败，应用兜底策略
                defaults_applied = apply_field_defaults(source)
                defaults_total += defaults_applied
                failed_count += 1

            optimized_sources.append(source)
            report_records.append({
                "idx": idx,
                "status": "success" if success else "failed",
                "defaults_applied": defaults_applied,
                "fields_extracted": len(fields_extracted) if success else 0,
            })

            if (idx + 1) % 20 == 0 or idx == total - 1:
                print(f"  [PROGRESS] {idx+1}/{total} ({(idx+1)*100//total}%) success={success_count} failed={failed_count}")

        browser.close()

    # 输出优化后的JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(optimized_sources, f, ensure_ascii=False, indent=2)

    # 输出优化报告
    report = {
        "stage": "batch_optimize_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "success_count": success_count,
        "failed_count": failed_count,
        "defaults_total_applied": defaults_total,
        "field_extraction_stats": field_stats,
        "records": report_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULT] 批量字段补全完成")
    print(f"  - 总源数:           {total}")
    print(f"  - 成功访问:         {success_count}")
    print(f"  - 访问失败:         {failed_count}")
    print(f"  - 兜底策略应用数:   {defaults_total}")
    print(f"\n[FIELD] 字段提取统计:")
    for field, count in field_stats.items():
        print(f"  - {field:15s}: {count}")
    print(f"\n[OUTPUT]")
    print(f"  - 优化后JSON:       {OUTPUT_JSON}")
    print(f"  - 优化报告:         {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
