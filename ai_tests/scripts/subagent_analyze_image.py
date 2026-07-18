"""
深度分析type=1图片源，使用Playwright访问sourceUrl，提取技术字段并设计ruleContent。
输出安全：脱敏URL/域名，只输出技术指标。
"""
import json
import os
import re
import sys
import time
import traceback
from urllib.parse import urlparse, urljoin

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[FATAL] playwright not installed. run: pip install playwright && playwright install chromium")
    sys.exit(1)

INPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\classified_v2.json"
OUTPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\subagent_image_analysis.json"

# 超时配置
NAV_TIMEOUT = 20000  # 20s
WAIT_AFTER_LOAD = 2000  # 加载后等待2s

# 参考源ruleContent模板（取自idx=50，简化版PhotoDialog适配）
PHOTO_DIALOG_TEMPLATE_A = """<js>
// 模板A：详情页主图提取（PhotoDialog适配）
var imgs = [];
var dom = org.jsoup.Jsoup.parse(src);
var mainImg = dom.selectFirst('.content img, .main img, .article img, .entry-content img, .post-content img');
if (mainImg) {
    var src = mainImg.attr('src') || mainImg.attr('data-src') || mainImg.attr('data-original');
    if (src) imgs.push(src);
}
var allImgs = dom.select('.content img, .main img, .article img, .entry-content img, .post-content img, .gallery img');
for (var i = 0; i < allImgs.size(); i++) {
    var s = allImgs.get(i).attr('src') || allImgs.get(i).attr('data-src') || allImgs.get(i).attr('data-original');
    if (s && imgs.indexOf(s) < 0) imgs.push(s);
}
result = imgs.join('\\n');
</js>"""

PHOTO_DIALOG_TEMPLATE_B = """<js>
// 模板B：懒加载图片提取（data-src/data-original）
var imgs = [];
var dom = org.jsoup.Jsoup.parse(src);
var lazyImgs = dom.select('img[data-src], img[data-original], img[data-lazy-src]');
for (var i = 0; i < lazyImgs.size(); i++) {
    var s = lazyImgs.get(i).attr('data-src') || lazyImgs.get(i).attr('data-original') || lazyImgs.get(i).attr('data-lazy-src');
    if (s) imgs.push(s);
}
if (imgs.length === 0) {
    var normalImgs = dom.select('.content img, .article img, .entry-content img');
    for (var j = 0; j < normalImgs.size(); j++) {
        var s2 = normalImgs.get(j).attr('src');
        if (s2) imgs.push(s2);
    }
}
result = imgs.join('\\n');
</js>"""

PHOTO_DIALOG_TEMPLATE_C = """<js>
// 模板C：og:image meta标签提取
var dom = org.jsoup.Jsoup.parse(src);
var ogImg = dom.selectFirst('meta[property=og:image]');
if (ogImg) {
    result = ogImg.attr('content');
} else {
    var twitterImg = dom.selectFirst('meta[name=twitter:image]');
    if (twitterImg) {
        result = twitterImg.attr('content');
    } else {
        var firstImg = dom.selectFirst('.content img, .article img, .entry-content img');
        result = firstImg ? (firstImg.attr('src') || firstImg.attr('data-src')) : '';
    }
}
</js>"""

PHOTO_DIALOG_TEMPLATE_D = """<js>
// 模板D：JSON API返回图片URL
var jsonStr = src;
try {
    var data = JSON.parse(jsonStr);
    var imgs = [];
    if (Array.isArray(data)) {
        for (var i = 0; i < data.length; i++) {
            if (data[i].url) imgs.push(data[i].url);
            else if (data[i].image) imgs.push(data[i].image);
            else if (data[i].src) imgs.push(data[i].src);
        }
    } else {
        if (data.url) imgs.push(data.url);
        if (data.image) imgs.push(data.image);
        if (data.images && Array.isArray(data.images)) {
            for (var j = 0; j < data.images.length; j++) imgs.push(data.images[j]);
        }
        if (data.data && Array.isArray(data.data)) {
            for (var k = 0; k < data.data.length; k++) {
                if (data.data[k].url) imgs.push(data.data[k].url);
                if (data.data[k].image) imgs.push(data.data[k].image);
            }
        }
    }
    result = imgs.join('\\n');
} catch(e) {
    result = '';
}
</js>"""


def sanitize_url(url):
    """脱敏URL"""
    if not isinstance(url, str) or not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path or ""
        return f"[DOMAIN]{path}"
    except Exception:
        return "[URL]"


def sanitize_error(err_msg):
    """脱敏错误消息中的URL/域名"""
    if not err_msg:
        return ""
    # 替换http(s)://xxx.yyy/...
    err_msg = re.sub(r'https?://[a-zA-Z0-9\-\.]+', '[DOMAIN]', err_msg)
    return err_msg


def extract_page_fields(page, source_url):
    """从已加载的Playwright page提取技术字段"""
    fields = {}

    try:
        # sourceIcon：favicon或logo
        icon = page.evaluate("""() => {
            const icon = document.querySelector('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
            if (icon) return icon.href;
            const logo = document.querySelector('img.logo, .header img, .site-logo img');
            if (logo) return logo.src || logo.getAttribute('data-src') || '';
            return '';
        }""")
        fields["sourceIcon"] = icon or ""
    except Exception as e:
        fields["sourceIcon"] = ""

    try:
        # searchUrl：搜索表单
        search_info = page.evaluate("""() => {
            const form = document.querySelector('form[action*="search"], form#searchform, form.search-form, form[action*="search"]');
            if (form) {
                const action = form.action || '';
                const method = form.method || 'get';
                const input = form.querySelector('input[type="text"], input[type="search"], input[name*="search"], input[name*="wd"], input[name*="q"], input[name*="key"]');
                const inputName = input ? (input.name || 'q') : 'q';
                return {action, method, inputName};
            }
            return null;
        }""")
        if search_info and search_info.get("action"):
            # 构造searchUrl（脱敏后保留模式）
            action = search_info["action"]
            input_name = search_info["inputName"]
            method = (search_info.get("method") or "get").lower()
            if method == "post":
                fields["searchUrl"] = f"{action},{{\"method\":\"POST\",\"body\":\"{input_name}={{key}}\"}}"
            else:
                fields["searchUrl"] = f"{action}?{input_name}={{key}}"
        else:
            fields["searchUrl"] = ""
    except Exception:
        fields["searchUrl"] = ""

    try:
        # sortUrl：分类导航菜单
        sort_urls = page.evaluate("""() => {
            const result = [];
            // 常见分类选择器
            const navLinks = document.querySelectorAll(
                'nav a, .nav a, .menu a, .navbar a, .header-menu a, ' +
                '.category a, .categories a, .cat-item a, ' +
                '.sidebar .cat-item a, #nav a, .main-nav a'
            );
            const seen = new Set();
            for (const a of navLinks) {
                const href = a.href;
                const text = (a.textContent || '').trim();
                if (href && text && !seen.has(href) && href.startsWith('http') &&
                    !href.includes('javascript:') && !href.includes('#') &&
                    text.length < 20) {
                    seen.add(href);
                    result.push(text + '::' + href);
                }
            }
            return result.slice(0, 15);
        }""")
        if sort_urls:
            fields["sortUrl"] = "\n".join(sort_urls)
        else:
            fields["sortUrl"] = ""
    except Exception:
        fields["sortUrl"] = ""

    try:
        # ruleArticles：列表项CSS选择器探测
        articles_selector = page.evaluate("""() => {
            // 探测可能的列表项容器
            const candidates = [
                '.post-list .post, .article-list .article, .entry-list .entry',
                '.list li, .posts li, ul.article li',
                '.card, .entry-card, .post-card',
                '.item, .list-item, .article-item',
                '.excerpt, .post-excerpt',
                'article, .post, .entry',
                '.thumbnail a, .thumb a',
                'ul li a:has(img), .grid li'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 3 && els.length < 200) {
                        return sel;
                    }
                } catch(e) {}
            }
            // 兜底：找包含多个img的ul
            const uls = document.querySelectorAll('ul');
            for (const ul of uls) {
                const imgs = ul.querySelectorAll('img');
                const lis = ul.querySelectorAll('li');
                if (lis.length >= 3 && imgs.length >= 3) {
                    return 'ul li';
                }
            }
            return '';
        }""")
        fields["ruleArticles"] = articles_selector or ""
    except Exception:
        fields["ruleArticles"] = ""

    try:
        # ruleImage：图片选择器（必填）
        image_selector = page.evaluate("""() => {
            // 探测列表中的图片
            const candidates = [
                'img[data-src]', 'img[data-original]', 'img[data-lazy-src]',
                '.thumb img, .thumbnail img, .pic img',
                '.post-thumb img, .entry-thumb img',
                '.card img, .entry-card img',
                '.item img, .list-item img',
                'article img, .post img'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 1) {
                        // 检查是否能拿到src或data-src
                        const first = els[0];
                        const src = first.src || first.getAttribute('data-src') || first.getAttribute('data-original');
                        if (src) return sel;
                    }
                } catch(e) {}
            }
            // 兜底
            const allImgs = document.querySelectorAll('img[src]');
            if (allImgs.length >= 3) return 'img';
            return '';
        }""")
        if image_selector:
            # 判断属性
            attr = page.evaluate(f"""() => {{
                const el = document.querySelector("{image_selector}");
                if (!el) return 'src';
                if (el.getAttribute('data-src')) return 'data-src';
                if (el.getAttribute('data-original')) return 'data-original';
                if (el.getAttribute('data-lazy-src')) return 'data-lazy-src';
                return 'src';
            }}""")
            fields["ruleImage"] = f"{image_selector}@{attr}||{image_selector}@src"
        else:
            fields["ruleImage"] = ""
    except Exception:
        fields["ruleImage"] = ""

    try:
        # ruleTitle：标题选择器
        title_selector = page.evaluate("""() => {
            const candidates = [
                'h2 a, h3 a, h2.title a, h3.title a',
                '.title a, .post-title a, .entry-title a',
                '.card-title a, .item-title a',
                'a.title, a.post-title'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 1) return sel + '@text';
                } catch(e) {}
            }
            return '';
        }""")
        fields["ruleTitle"] = title_selector or ""
    except Exception:
        fields["ruleTitle"] = ""

    try:
        # ruleLink：链接选择器
        link_selector = page.evaluate("""() => {
            const candidates = [
                'h2 a, h3 a, h2.title a, h3.title a',
                '.title a, .post-title a, .entry-title a',
                '.card-title a, .item-title a',
                'a.title, a.post-title',
                '.thumb a, .thumbnail a, .pic a'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 1) return sel + '@href';
                } catch(e) {}
            }
            return '';
        }""")
        fields["ruleLink"] = link_selector or ""
    except Exception:
        fields["ruleLink"] = ""

    try:
        # ruleNextPage：下一页
        next_page = page.evaluate("""() => {
            const candidates = [
                'a.next', 'a.nextpage', '.next a', '.pagination .next a',
                'a[rel="next"]', '.pager a:last-child',
                '.nav-links .next a', '.page-nav a.next',
                'a:contains("下一页")', 'a:contains("Next")'
            ];
            for (const sel of candidates) {
                try {
                    const el = document.querySelector(sel);
                    if (el && el.href) return sel + '@href';
                } catch(e) {}
            }
            return '';
        }""")
        fields["ruleNextPage"] = next_page or ""
    except Exception:
        fields["ruleNextPage"] = ""

    try:
        # rulePubDate：发布日期
        pubdate = page.evaluate("""() => {
            const candidates = [
                'time', '.date', '.post-date', '.entry-date',
                '.time', '.published', '.post-time',
                'meta[property="article:published_time"]'
            ];
            for (const sel of candidates) {
                try {
                    const el = document.querySelector(sel);
                    if (el) {
                        if (el.tagName === 'META') return sel + '@content';
                        return sel + '@text';
                    }
                } catch(e) {}
            }
            return '';
        }""")
        fields["rulePubDate"] = pubdate or ""
    except Exception:
        fields["rulePubDate"] = ""

    return fields


def detect_rule_content_template(page):
    """访问详情页后，根据DOM特征自动选择ruleContent模板"""
    template = "A"
    template_code = PHOTO_DIALOG_TEMPLATE_A
    notes = []

    try:
        # 检查DOM特征
        features = page.evaluate("""() => {
            const result = {
                has_content_img: false,
                has_lazy_img: false,
                has_og_image: false,
                is_json_response: false,
                content_img_count: 0,
                lazy_img_count: 0
            };
            // 检查.content img等
            const contentImgs = document.querySelectorAll('.content img, .main img, .article img, .entry-content img, .post-content img');
            result.content_img_count = contentImgs.length;
            result.has_content_img = contentImgs.length > 0;

            // 检查懒加载
            const lazyImgs = document.querySelectorAll('img[data-src], img[data-original], img[data-lazy-src]');
            result.lazy_img_count = lazyImgs.length;
            result.has_lazy_img = lazyImgs.length > 0;

            // 检查og:image
            const ogImg = document.querySelector('meta[property="og:image"]');
            result.has_og_image = !!ogImg;

            return result;
        }""")

        if features.get("has_content_img") and features.get("content_img_count", 0) >= 2:
            template = "A"
            template_code = PHOTO_DIALOG_TEMPLATE_A
            notes.append(f"content_img_count={features['content_img_count']}")
        elif features.get("has_lazy_img"):
            template = "B"
            template_code = PHOTO_DIALOG_TEMPLATE_B
            notes.append(f"lazy_img_count={features['lazy_img_count']}")
        elif features.get("has_og_image"):
            template = "C"
            template_code = PHOTO_DIALOG_TEMPLATE_C
            notes.append("og:image meta present")
        else:
            template = "A"
            template_code = PHOTO_DIALOG_TEMPLATE_A
            notes.append("fallback to A")
    except Exception as e:
        notes.append(f"detect_error: {sanitize_error(str(e))}")
        template = "A"
        template_code = PHOTO_DIALOG_TEMPLATE_A

    return template, template_code, notes


def find_detail_page_url(page, source_url):
    """从列表页找一个详情页URL用于分析"""
    try:
        detail_url = page.evaluate("""() => {
            // 优先找文章链接
            const candidates = document.querySelectorAll(
                '.post a[href], .article a[href], .entry a[href], ' +
                '.card a[href], .entry-card a[href], ' +
                'article a[href], .item a[href], ' +
                'h2 a[href], h3 a[href], .title a[href]'
            );
            for (const a of candidates) {
                const href = a.href;
                if (href && href.startsWith('http') &&
                    !href.includes('javascript:') &&
                    !href.includes('#') &&
                    href !== window.location.href) {
                    return href;
                }
            }
            return '';
        }""")
        return detail_url
    except Exception:
        return ""


def analyze_source(playwright, source, array_idx):
    """分析单个源"""
    result = {
        "idx": array_idx,
        "customOrder": source.get("customOrder", 0),
        "type": 1,
        "source_url_accessible": False,
        "fields": {},
        "special_config": {
            "loginUrl": "",
            "enabledCookieJar": source.get("enabledCookieJar", False),
            "enableJs": True,
            "loadWithBaseUrl": True,
            "jsRule": ""
        },
        "rule_content_template": "A",
        "analysis_notes": []
    }

    source_url = source.get("sourceUrl", "")
    if not source_url:
        result["analysis_notes"].append("empty sourceUrl")
        return result

    # 检测反爬配置（参考源中已有的）
    existing_login_url = source.get("loginUrl", "")
    if existing_login_url:
        # 保留原有loginUrl的脱敏形式
        result["special_config"]["loginUrl"] = "@js:java.startBrowserAwait(source.sourceUrl,'verify');"
        result["special_config"]["enabledCookieJar"] = True
        result["analysis_notes"].append("has existing loginUrl (anti-crawl)")

    browser = None
    page = None
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 9; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Mobile Safari/537.36",
            viewport={'width': 412, 'height': 732},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT)

        try:
            response = page.goto(source_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            if response and response.status < 500:
                result["source_url_accessible"] = True
                result["analysis_notes"].append(f"status={response.status}")
            else:
                result["analysis_notes"].append(f"bad_status={response.status if response else 'no_response'}")
        except PlaywrightTimeout:
            result["analysis_notes"].append("error:Timeout")
            # 超时也尝试继续分析当前页面
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        except Exception as e:
            err = sanitize_error(str(e))
            result["analysis_notes"].append(f"error:{err[:200]}")
            # 检测CF/反爬
            if "ERR_NAME_NOT_RESOLVED" in str(e):
                result["analysis_notes"].append("dns_fail")
            elif "ERR_CONNECTION_REFUSED" in str(e):
                result["analysis_notes"].append("conn_refused")
            elif "ERR_SSL_PROTOCOL_ERROR" in str(e) or "ERR_CERT" in str(e):
                result["analysis_notes"].append("ssl_error")

        if result["source_url_accessible"]:
            try:
                page.wait_for_timeout(WAIT_AFTER_LOAD)
            except Exception:
                pass

            # 检测CF盾
            try:
                page_content = page.content()
                if "Just a moment" in page_content or "Checking your browser" in page_content or "cf-browser-verification" in page_content:
                    result["analysis_notes"].append("cf_block_detected")
                    result["special_config"]["loginUrl"] = "@js:java.startBrowserAwait(source.sourceUrl,'CloudFlare verify');"
                    result["special_config"]["enabledCookieJar"] = True
                    # 等待CF通过
                    try:
                        page.wait_for_timeout(8000)
                        page_content = page.content()
                        if "Just a moment" not in page_content:
                            result["analysis_notes"].append("cf_passed_after_wait")
                        else:
                            result["analysis_notes"].append("cf_still_blocked")
                    except Exception:
                        pass
            except Exception:
                pass

            # 检测弹框
            try:
                has_popup = page.evaluate("""() => {
                    const popups = document.querySelectorAll('.popup, .modal, .dialog, .mask, .overlay');
                    return popups.length;
                }""")
                if has_popup > 0:
                    result["analysis_notes"].append(f"popup_detected:{has_popup}")
                    result["special_config"]["jsRule"] = "// auto close popup\\ndocument.querySelectorAll('.popup,.modal,.dialog,.mask,.overlay').forEach(e=>e.style.display='none');"
            except Exception:
                pass

            # 提取字段
            try:
                fields = extract_page_fields(page, source_url)
                result["fields"].update(fields)
            except Exception as e:
                result["analysis_notes"].append(f"extract_error:{sanitize_error(str(e))[:200]}")

            # 找详情页并分析ruleContent
            try:
                detail_url = find_detail_page_url(page, source_url)
                if detail_url:
                    result["analysis_notes"].append("detail_page_found")
                    try:
                        detail_page = context.new_page()
                        detail_page.set_default_timeout(NAV_TIMEOUT)
                        detail_resp = detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                        if detail_resp and detail_resp.status < 500:
                            detail_page.wait_for_timeout(WAIT_AFTER_LOAD)
                            template, template_code, notes = detect_rule_content_template(detail_page)
                            result["rule_content_template"] = template
                            result["fields"]["ruleContent"] = template_code
                            result["analysis_notes"].extend(notes)
                        else:
                            result["analysis_notes"].append("detail_page_bad_status")
                            # 兜底用模板A
                            result["fields"]["ruleContent"] = PHOTO_DIALOG_TEMPLATE_A
                            result["rule_content_template"] = "A"
                        detail_page.close()
                    except Exception as e:
                        result["analysis_notes"].append(f"detail_page_error:{sanitize_error(str(e))[:200]}")
                        result["fields"]["ruleContent"] = PHOTO_DIALOG_TEMPLATE_A
                        result["rule_content_template"] = "A"
                else:
                    result["analysis_notes"].append("no_detail_page_found")
                    # 兜底用模板A
                    result["fields"]["ruleContent"] = PHOTO_DIALOG_TEMPLATE_A
                    result["rule_content_template"] = "A"
            except Exception as e:
                result["analysis_notes"].append(f"detail_find_error:{sanitize_error(str(e))[:200]}")
                result["fields"]["ruleContent"] = PHOTO_DIALOG_TEMPLATE_A
                result["rule_content_template"] = "A"

            # 如果原有ruleContent已经存在且较长（参考源），保留
            existing_rc = source.get("ruleContent", "") or ""
            if len(existing_rc) > 1000:
                result["fields"]["ruleContent"] = existing_rc
                result["analysis_notes"].append(f"keep_existing_ruleContent_len={len(existing_rc)}")
                result["rule_content_template"] = "existing"

            # 如果原有ruleImage已经存在，保留
            existing_ri = source.get("ruleImage", "") or ""
            if existing_ri and not result["fields"].get("ruleImage"):
                result["fields"]["ruleImage"] = existing_ri
                result["analysis_notes"].append("keep_existing_ruleImage")

            # 如果原有ruleArticles已经存在，保留
            existing_ra = source.get("ruleArticles", "") or ""
            if existing_ra and not result["fields"].get("ruleArticles"):
                result["fields"]["ruleArticles"] = existing_ra
                result["analysis_notes"].append("keep_existing_ruleArticles")

            # 保留原有searchUrl/sortUrl如果存在
            existing_su = source.get("searchUrl", "") or ""
            if existing_su and not result["fields"].get("searchUrl"):
                result["fields"]["searchUrl"] = existing_su
                result["analysis_notes"].append("keep_existing_searchUrl")

            existing_sort = source.get("sortUrl", "") or ""
            if existing_sort and not result["fields"].get("sortUrl"):
                result["fields"]["sortUrl"] = existing_sort
                result["analysis_notes"].append("keep_existing_sortUrl")

            # 保留原有sourceIcon如果存在
            existing_icon = source.get("sourceIcon", "") or ""
            if existing_icon and not result["fields"].get("sourceIcon"):
                result["fields"]["sourceIcon"] = existing_icon
                result["analysis_notes"].append("keep_existing_sourceIcon")

    except Exception as e:
        result["analysis_notes"].append(f"fatal_error:{sanitize_error(str(e))[:300]}")
    finally:
        try:
            if page:
                page.close()
        except Exception:
            pass
        try:
            if browser:
                browser.close()
        except Exception:
            pass

    return result


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[FATAL] input not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # 筛选type=1
    image_indices = [i for i, s in enumerate(sources) if s.get("type", -1) == 1]
    print(f"[INFO] type=1 sources: {len(image_indices)}")
    print(f"[INFO] indices: {image_indices}")

    results = []
    success_count = 0
    failed_count = 0

    with sync_playwright() as playwright:
        for i, idx in enumerate(image_indices):
            print(f"\n[PROGRESS {i+1}/{len(image_indices)}] analyzing array_idx={idx}...")
            source = sources[idx]
            start = time.time()
            try:
                result = analyze_source(playwright, source, idx)
                elapsed = time.time() - start
                result["elapsed_seconds"] = round(elapsed, 2)
                if result["source_url_accessible"]:
                    success_count += 1
                    print(f"  [OK] accessible, template={result['rule_content_template']}, elapsed={elapsed:.1f}s")
                else:
                    failed_count += 1
                    print(f"  [FAIL] not accessible, notes={result['analysis_notes'][:3]}, elapsed={elapsed:.1f}s")
                results.append(result)
            except Exception as e:
                failed_count += 1
                err = sanitize_error(str(e))
                print(f"  [EXCEPTION] {err[:200]}")
                results.append({
                    "idx": idx,
                    "customOrder": source.get("customOrder", 0),
                    "type": 1,
                    "source_url_accessible": False,
                    "fields": {},
                    "special_config": {"loginUrl": "", "enabledCookieJar": False, "enableJs": True, "loadWithBaseUrl": True, "jsRule": ""},
                    "rule_content_template": "A",
                    "analysis_notes": [f"exception:{err[:300]}"],
                    "elapsed_seconds": round(time.time() - start, 2)
                })

            # 立即写入（避免崩溃丢失进度）
            try:
                os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "agent": "image_source_analyzer",
                        "total_analyzed": len(results),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "results": results,
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  [WARN] failed to save intermediate: {sanitize_error(str(e))[:100]}")

    # 模板分布统计
    template_dist = {}
    for r in results:
        t = r.get("rule_content_template", "unknown")
        template_dist[t] = template_dist.get(t, 0) + 1

    print(f"\n[FINAL] total={len(results)} success={success_count} failed={failed_count}")
    print(f"[FINAL] template distribution: {template_dist}")
    print(f"[OUTPUT] {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
