"""
V5.7 阶段1：智能补齐13个启用源缺字段
策略：用Playwright访问每个源首页，从DOM提取通用字段
- sourceIcon: <link rel="icon"> 或 /favicon.ico
- ruleNextPage: 找"下一页"链接选择器
- ruleTitle: 列表项标题选择器
- rulePubDate: 时间字段选择器
- ruleImage: 列表项图片选择器
- ruleLink: 列表项链接选择器

输出：建议字段值（用源[idx]代号，不输出真实URL/名称）
"""
import json
import re
import sys
import os
from pathlib import Path

# 添加 venv 路径
venv_site = Path("ai_tests/venv/Lib/site-packages")
if venv_site.exists():
    sys.path.insert(0, str(venv_site))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

JSON_PATH = Path("output/rss/optimized_v5_6_final.json")
OUTPUT_PATH = Path("output/rss/v5_7_field_suggestions.json")
TIMEOUT = 15000

# 需要补字段的13个启用源 idx
MISSING_IDX = [52, 81, 83, 131, 134, 174, 176, 177, 178, 180, 181, 182, 183]


def extract_favicon(html, source_url):
    """从HTML提取favicon"""
    # 1. <link rel="icon" href="...">
    m = re.search(r'<link[^>]*rel=["\'](?:shortcut icon|icon)["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        href = m.group(1)
        if href.startswith("//"):
            return "https:" + href
        elif href.startswith("/"):
            from urllib.parse import urlparse
            p = urlparse(source_url)
            return f"{p.scheme}://{p.netloc}{href}"
        elif href.startswith("http"):
            return href
        else:
            from urllib.parse import urlparse
            p = urlparse(source_url)
            return f"{p.scheme}://{p.netloc}/{href}"
    # 2. 默认 favicon.ico
    from urllib.parse import urlparse
    p = urlparse(source_url)
    return f"{p.scheme}://{p.netloc}/favicon.ico"


def extract_list_selectors(html):
    """从HTML分析列表选择器"""
    suggestions = {}

    # 找标题选择器 - 常见的标题class
    title_patterns = [
        r'class=["\'][^"\']*(?:title|tit|name|heading|h-title)[^"\']*["\']',
        r'<h[1-4][^>]*>([^<]+)</h[1-4]>',
    ]
    for pat in title_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            # 提取class名
            class_m = re.search(r'class=["\']([^"\']+)["\']', m.group(0) if m else "")
            if class_m:
                classes = class_m.group(1).split()
                for c in classes:
                    if any(kw in c.lower() for kw in ['title', 'tit', 'name', 'heading']):
                        suggestions['ruleTitle'] = f"class.{c}@text"
                        break
                if 'ruleTitle' in suggestions:
                    break

    # 找时间选择器
    time_patterns = [
        r'class=["\'][^"\']*(?:time|date|pubtime|pubdate|created|updated)[^"\']*["\']',
        r'<time[^>]*>([^<]+)</time>',
    ]
    for pat in time_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            class_m = re.search(r'class=["\']([^"\']+)["\']', m.group(0) if m else "")
            if class_m:
                classes = class_m.group(1).split()
                for c in classes:
                    if any(kw in c.lower() for kw in ['time', 'date', 'pubtime', 'pubdate', 'created', 'updated']):
                        suggestions['rulePubDate'] = f"class.{c}@text"
                        break
                if 'rulePubDate' in suggestions:
                    break

    # 找图片选择器
    img_patterns = [
        r'<img[^>]*class=["\'][^"\']*(?:thumb|cover|poster|lazy|pic|img)[^"\']*["\']',
        r'<img[^>]*data-original=["\']',
        r'<img[^>]*data-src=["\']',
    ]
    for pat in img_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            class_m = re.search(r'class=["\']([^"\']+)["\']', m.group(0) if m else "")
            if class_m:
                classes = class_m.group(1).split()
                for c in classes:
                    if any(kw in c.lower() for kw in ['thumb', 'cover', 'poster', 'lazy', 'pic', 'img']):
                        suggestions['ruleImage'] = f"class.{c}@src"
                        break
                if 'ruleImage' in suggestions:
                    break
    if 'ruleImage' not in suggestions:
        # 用 data-original 或 data-src
        if 'data-original' in html:
            suggestions['ruleImage'] = "img@data-original"
        elif 'data-src' in html:
            suggestions['ruleImage'] = "img@data-src"
        else:
            suggestions['ruleImage'] = "img@src"

    # 找链接选择器
    if 'ruleTitle' in suggestions:
        # 用标题元素的父级 a 标签
        suggestions['ruleLink'] = "a@href"
    else:
        suggestions['ruleLink'] = "a@href"

    # 找下一页选择器
    nextpage_patterns = [
        r'<a[^>]*class=["\'][^"\']*(?:next|page-next|pagination-next|nxt)[^"\']*["\']',
        r'<a[^>]*>(?:下一页|下页|next|Next|NEXT|»|›)[^<]*</a>',
        r'href=["\'][^"\']*[?&]page=\d+[^"\']*["\']',
    ]
    for pat in nextpage_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            class_m = re.search(r'class=["\']([^"\']+)["\']', m.group(0) if m else "")
            if class_m:
                classes = class_m.group(1).split()
                for c in classes:
                    if any(kw in c.lower() for kw in ['next', 'page-next', 'pagination-next', 'nxt']):
                        suggestions['ruleNextPage'] = f"class.{c}@href"
                        break
            if 'ruleNextPage' not in suggestions:
                # 用href中的page参数
                href_m = re.search(r'href=["\']([^"\']*[?&]page=)(\d+)([^"\']*)["\']', m.group(0) if m else "", re.IGNORECASE)
                if href_m:
                    suggestions['ruleNextPage'] = f"{href_m.group(1)}{{,page}}{href_m.group(3)}"
            if 'ruleNextPage' in suggestions:
                break

    return suggestions


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            viewport={"width": 375, "height": 667}
        )

        for idx in MISSING_IDX:
            if idx >= len(sources):
                continue
            s = sources[idx]
            if s.get("enabled") is not True:
                continue

            missing = []
            for field in ["sourceIcon", "ruleNextPage", "ruleTitle", "rulePubDate", "ruleImage", "ruleLink"]:
                val = s.get(field)
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    missing.append(field)

            if not missing:
                continue

            url = s.get("sourceUrl", "")
            if not url:
                results[f"src_{idx}"] = {"error": "no sourceUrl"}
                continue

            page = context.new_page()
            try:
                resp = page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
                if resp is None or resp.status >= 400:
                    results[f"src_{idx}"] = {"error": f"http_{resp.status if resp else 'no_resp'}", "missing": missing}
                    page.close()
                    continue

                html = page.content()

                suggestions = {}
                if "sourceIcon" in missing:
                    suggestions["sourceIcon"] = extract_favicon(html, url)
                if any(k in missing for k in ["ruleNextPage", "ruleTitle", "rulePubDate", "ruleImage", "ruleLink"]):
                    list_sugg = extract_list_selectors(html)
                    for k, v in list_sugg.items():
                        if k in missing:
                            suggestions[k] = v

                results[f"src_{idx}"] = {
                    "missing": missing,
                    "suggestions": suggestions,
                    "html_len": len(html),
                    "title_tag": re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE).group(1).strip()[:80] if re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE) else None,
                }
                print(f"  源[{idx}] 缺{len(missing)}字段 -> 提取{len(suggestions)}建议")
            except PlaywrightTimeout:
                results[f"src_{idx}"] = {"error": "timeout", "missing": missing}
                print(f"  源[{idx}] 超时")
            except Exception as e:
                err_type = type(e).__name__
                results[f"src_{idx}"] = {"error": err_type, "missing": missing}
                print(f"  源[{idx}] {err_type}")
            finally:
                page.close()

        browser.close()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== 结果保存到 {OUTPUT_PATH} ===")
    print(f"=== 处理 {len(results)} 个源 ===")
    success = sum(1 for v in results.values() if "suggestions" in v and v["suggestions"])
    print(f"=== 成功提取建议: {success}/{len(results)} ===")


if __name__ == "__main__":
    main()
