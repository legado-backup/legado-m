"""
V5.7 阶段1.2：深度提取13个启用源的缺字段
策略：对每个源访问首页+列表页+文章页，深度提取字段
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin

venv_site = Path("ai_tests/venv/Lib/site-packages")
if venv_site.exists():
    sys.path.insert(0, str(venv_site))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

JSON_PATH = Path("output/rss/optimized_v5_6_final.json")
OUTPUT_PATH = Path("output/rss/v5_7_field_suggestions_v2.json")
TIMEOUT = 20000

MISSING_IDX = [52, 81, 83, 131, 134, 174, 176, 177, 178, 180, 181, 182, 183]

UA_MOBILE = "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
UA_DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def absolute(url, base):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        p = urlparse(base)
        return f"{p.scheme}://{p.netloc}{url}"
    if url.startswith("http"):
        return url
    return urljoin(base, url)


def deep_extract(html, base_url, source_url, missing):
    """深度提取字段"""
    suggestions = {}

    # 1. sourceIcon: 从HTML的link rel="icon"提取，没找到则用/favicon.ico
    if "sourceIcon" in missing:
        patterns = [
            r'<link[^>]*rel=["\'](?:shortcut icon|icon|apple-touch-icon)["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut icon|icon|apple-touch-icon)["\']',
        ]
        icon_found = None
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                icon_found = m.group(1)
                break
        if icon_found:
            suggestions["sourceIcon"] = absolute(icon_found, base_url)
        else:
            p = urlparse(source_url)
            suggestions["sourceIcon"] = f"{p.scheme}://{p.netloc}/favicon.ico"

    # 2. ruleTitle: 尝试多种选择器
    if "ruleTitle" in missing:
        title_selectors = []
        # class含title/tit/name/heading/h-title/article-title
        for m in re.finditer(r'class=["\']([^"\']+)["\']', html):
            classes = m.group(1).split()
            for c in classes:
                cl = c.lower()
                if any(kw in cl for kw in ['title', 'tit', 'name', 'heading', 'h-title', 'article-title']):
                    if len(c) > 3 and c not in title_selectors:
                        title_selectors.append(c)
        if title_selectors:
            # 优先短的class名
            title_selectors.sort(key=len)
            suggestions["ruleTitle"] = f"class.{title_selectors[0]}@text"
        else:
            # 用h1/h2/h3
            for tag in ['h1', 'h2', 'h3', 'h4']:
                if f'<{tag}' in html:
                    suggestions["ruleTitle"] = f"{tag}@text"
                    break

    # 3. rulePubDate: 尝试多种时间选择器
    if "rulePubDate" in missing:
        date_selectors = []
        # class含time/date/pubtime/pubdate/created/updated/post-time/post-date
        for m in re.finditer(r'class=["\']([^"\']+)["\']', html):
            classes = m.group(1).split()
            for c in classes:
                cl = c.lower()
                if any(kw in cl for kw in ['time', 'date', 'pubtime', 'pubdate', 'created', 'updated', 'post-time', 'post-date', 'meta-time']):
                    if c not in date_selectors:
                        date_selectors.append(c)
        # 优先含time/date关键词的class
        date_selectors.sort(key=lambda c: (0 if 'time' in c.lower() or 'date' in c.lower() else 1, len(c)))
        if date_selectors:
            suggestions["rulePubDate"] = f"class.{date_selectors[0]}@text"
        else:
            # 用<time>标签
            if '<time' in html:
                suggestions["rulePubDate"] = "time@text"
            # 用js时间戳（如data-time="1234567890"）
            elif 'data-time' in html:
                suggestions["rulePubDate"] = "class.post@data-time"

    # 4. ruleImage: 尝试多种图片选择器
    if "ruleImage" in missing:
        # 优先用class含thumb/cover/poster/lazy/pic/img
        img_selectors = []
        for m in re.finditer(r'<img[^>]*class=["\']([^"\']+)["\']', html):
            classes = m.group(1).split()
            for c in classes:
                cl = c.lower()
                if any(kw in cl for kw in ['thumb', 'cover', 'poster', 'lazy', 'pic', 'img', 'avatar']):
                    if c not in img_selectors:
                        img_selectors.append(c)
        if img_selectors:
            img_selectors.sort(key=len)
            # 判断用 src 还是 data-original/data-src
            img_html = re.search(r'<img[^>]*class=["\'][^"\']*' + re.escape(img_selectors[0]) + r'[^"\']*["\'][^>]*>', html)
            attr = "src"
            if img_html:
                if 'data-original' in img_html.group(0):
                    attr = "data-original"
                elif 'data-src' in img_html.group(0):
                    attr = "data-src"
            suggestions["ruleImage"] = f"class.{img_selectors[0]}@{attr}"
        else:
            # 用 data-original 或 data-src 通用规则
            if 'data-original' in html:
                suggestions["ruleImage"] = "img@data-original"
            elif 'data-src' in html:
                suggestions["ruleImage"] = "img@data-src"
            else:
                suggestions["ruleImage"] = "img@src"

    # 5. ruleLink: 尝试链接选择器
    if "ruleLink" in missing:
        # 优先用class含title/article/post/item的a标签
        link_selectors = []
        for m in re.finditer(r'<a[^>]*class=["\']([^"\']+)["\']', html):
            classes = m.group(1).split()
            for c in classes:
                cl = c.lower()
                if any(kw in cl for kw in ['title', 'article', 'post', 'item', 'link']):
                    if c not in link_selectors:
                        link_selectors.append(c)
        if link_selectors:
            link_selectors.sort(key=len)
            suggestions["ruleLink"] = f"a.class.{link_selectors[0]}@href"
        else:
            suggestions["ruleLink"] = "a@href"

    # 6. ruleNextPage: 尝试下一页选择器
    if "ruleNextPage" in missing:
        next_selectors = []
        # class含next/page-next/nxt/pagination-next
        for m in re.finditer(r'<a[^>]*class=["\']([^"\']+)["\']', html):
            classes = m.group(1).split()
            for c in classes:
                cl = c.lower()
                if any(kw in cl for kw in ['next', 'nxt', 'page-next', 'pagination-next', 'page_nxt', 'pagenext']):
                    if c not in next_selectors:
                        next_selectors.append(c)
        if next_selectors:
            next_selectors.sort(key=len)
            suggestions["ruleNextPage"] = f"a.class.{next_selectors[0]}@href"
        else:
            # 找href含page参数的链接
            m = re.search(r'href=["\']([^"\']*[?&]page=)(\d+)([^"\']*)["\']', html, re.IGNORECASE)
            if m:
                suggestions["ruleNextPage"] = f"{m.group(1)}{{,page}}{m.group(3)}"
            else:
                # 找href含 p= 参数的链接
                m = re.search(r'href=["\']([^"\']*[?&]p=)(\d+)([^"\']*)["\']', html, re.IGNORECASE)
                if m:
                    suggestions["ruleNextPage"] = f"{m.group(1)}{{,page}}{m.group(3)}"

    return suggestions


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

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
                results[f"src_{idx}"] = {"error": "no sourceUrl", "missing": missing}
                continue

            # 同时用mobile和desktop UA各尝试一次
            for ua_name, ua in [("mobile", UA_MOBILE), ("desktop", UA_DESKTOP)]:
                context = browser.new_context(user_agent=ua, viewport={"width": 375 if "mobile" in ua_name else 1280, "height": 667 if "mobile" in ua_name else 800})
                page = context.new_page()
                try:
                    resp = page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
                    if resp is None or resp.status >= 400:
                        if ua_name == "desktop":
                            results[f"src_{idx}"] = {"error": f"http_{resp.status if resp else 'no_resp'}", "missing": missing}
                        page.close()
                        context.close()
                        continue

                    html = page.content()
                    suggestions = deep_extract(html, url, url, missing)

                    if suggestions:
                        results[f"src_{idx}"] = {
                            "missing": missing,
                            "suggestions": suggestions,
                            "html_len": len(html),
                            "ua": ua_name,
                        }
                        print(f"  源[{idx}] ua={ua_name} 缺{len(missing)}字段 -> 提取{len(suggestions)}建议")
                        page.close()
                        context.close()
                        break  # 成功就跳出UA循环
                    page.close()
                    context.close()
                except PlaywrightTimeout:
                    if ua_name == "desktop":
                        results[f"src_{idx}"] = {"error": "timeout", "missing": missing}
                        print(f"  源[{idx}] 超时")
                    page.close()
                    context.close()
                except Exception as e:
                    err_type = type(e).__name__
                    if ua_name == "desktop":
                        results[f"src_{idx}"] = {"error": err_type, "missing": missing}
                        print(f"  源[{idx}] {err_type}")
                    page.close()
                    context.close()

        browser.close()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== 结果保存到 {OUTPUT_PATH} ===")
    print(f"=== 处理 {len(results)} 个源 ===")
    success = sum(1 for v in results.values() if "suggestions" in v and v["suggestions"])
    print(f"=== 成功提取建议: {success}/{len(results)} ===")


if __name__ == "__main__":
    main()
