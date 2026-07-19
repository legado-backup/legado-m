"""
subagent_analyze_web2.py
深度分析type=0网页源第二批（idx 50-99），重点补全searchUrl和jsRule。
输出脱敏JSON，不包含业务字段原文。

参考源字段模式：
- IDX=0: 复杂searchUrl（验证码js+POST）、超长ruleContent（51611字符）
- IDX=2: 简单POST searchUrl、sortUrl多分类（67行）
- IDX=131: JS模板searchUrl、长ruleArticles（2009字符）
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[FATAL] playwright not installed")
    sys.exit(1)

INPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\classified_v2.json"
OUTPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\subagent_web2_analysis.json"

# 超时配置
NAV_TIMEOUT = 20000  # 20s
WAIT_AFTER_LOAD = 2500  # 加载后等待2.5s

# ========== 通用 ruleContent 模板（type=0网页源，文本为主） ==========
# 模板W1：标准文章正文提取
RULE_CONTENT_TEMPLATE_W1 = """<js>
// 模板W1：标准文章正文提取（type=0网页源）
var dom = org.jsoup.Jsoup.parse(src);
var content = dom.selectFirst('.article-content, .entry-content, .post-content, .content, .article-body, .read-content, .text, #content, #article');
if (content) {
    content.select('script,style,.ad,.adsense,.share,.related,.comment,.sidebar,iframe').remove();
    result = content.html();
} else {
    var body = dom.selectFirst('body');
    if (body) {
        body.select('script,style,nav,header,footer,.sidebar,.comment,.ad').remove();
        result = body.html();
    } else {
        result = '';
    }
}
</js>"""

# 模板W2：JSON API返回的文章内容
RULE_CONTENT_TEMPLATE_W2 = """<js>
// 模板W2：JSON API返回内容提取
try {
    var data = JSON.parse(src);
    if (data.content) result = data.content;
    else if (data.data && data.data.content) result = data.data.content;
    else if (data.data && data.data.length > 0 && data.data[0].content) result = data.data[0].content;
    else if (data.article && data.article.content) result = data.article.content;
    else result = JSON.stringify(data);
} catch(e) {
    result = src;
}
</js>"""

# 模板W3：移动端H5文章提取
RULE_CONTENT_TEMPLATE_W3 = """<js>
// 模板W3：移动端H5文章提取
var dom = org.jsoup.Jsoup.parse(src);
var content = dom.selectFirst('.article, .post, .entry, .content, .main-content, .read-content, .article-content, .post-content, .entry-content');
if (content) {
    content.select('script,style,nav,footer,iframe,.ad,.banner,.recommend,.related').remove();
    var paragraphs = content.select('p');
    if (paragraphs.size() > 0) {
        var texts = [];
        for (var i = 0; i < paragraphs.size(); i++) {
            var t = paragraphs.get(i).text();
            if (t && t.length > 0) texts.push(t);
        }
        result = texts.join('\\n\\n');
    } else {
        result = content.text();
    }
} else {
    result = '';
}
</js>"""

# ========== jsRule 模板（自动关闭弹框） ==========
JS_RULE_POPUP_CLOSE = """// 自动关闭弹框/广告/遮罩
(function(){
    var popups = document.querySelectorAll('.modal,.popup,.dialog,.mask,.overlay,.ad-mask,.ads-box,.ad-box,.float-ad,.float-box');
    popups.forEach(function(e){ e.style.display='none'; });
    // 关闭蒙层
    document.body.style.overflow = 'auto';
    // 移除可能的固定定位广告
    var fixedAds = document.querySelectorAll('div[style*="fixed"],div[style*="sticky"]');
    fixedAds.forEach(function(e){
        if (e.offsetWidth > window.innerWidth * 0.8 && e.offsetHeight > window.innerHeight * 0.5) {
            e.style.display = 'none';
        }
    });
})();"""

JS_RULE_ANTI_CRAWL = """// 反爬处理：等待动态内容加载
(function(){
    // 标记页面已就绪
    window.__page_ready = true;
    // 移除可能的反爬弹框
    var blocks = document.querySelectorAll('.verify-box,.captcha-box,.check-box,[class*="verify"],[id*="captcha"]');
    blocks.forEach(function(e){ e.style.display = 'none'; });
})();"""


# ========== 脱敏工具 ==========
def mask_url(url: str) -> str:
    """URL脱敏：只保留路径模式，域名替换为[DOMAIN]"""
    if not url or not isinstance(url, str):
        return ""
    masked = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', url)
    masked = re.sub(r'/\d{4,}', '/{id}', masked)
    masked = re.sub(r'(token|key|sign|auth|password|secret|cookie)=[^&\s"\'<>]+', r'\1=***', masked, flags=re.IGNORECASE)
    return masked


def mask_text(text: str, max_len: int = 100) -> str:
    """文本脱敏：截断+替换URL/敏感词"""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', text)
    text = re.sub(r'(token|cookie|password|key|secret|auth)=[^&\s"\'<>]+', r'\1=***', text, flags=re.IGNORECASE)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def sanitize_error(err_msg: str, max_len: int = 200) -> str:
    """脱敏错误消息"""
    if not err_msg:
        return ""
    masked = re.sub(r'https?://[a-zA-Z0-9\-\.]+', '[DOMAIN]', err_msg)
    masked = re.sub(r'(token|cookie|password|key|secret|auth)=[^&\s"\'<>]+', r'\1=***', masked, flags=re.IGNORECASE)
    if len(masked) > max_len:
        masked = masked[:max_len] + "..."
    return masked


# ========== Playwright 字段提取 ==========
def extract_page_fields(page, source_url: str) -> dict:
    """从已加载的Playwright page提取所有技术字段"""
    fields = {}

    # ===== sourceIcon =====
    try:
        icon = page.evaluate("""() => {
            const selectors = ['link[rel*="icon"]', 'link[rel="shortcut icon"]', 'link[rel="apple-touch-icon"]', 'meta[property="og:image"]'];
            for (const s of selectors) {
                const el = document.querySelector(s);
                if (el) return el.href || el.content || '';
            }
            const logo = document.querySelector('img.logo, .header img, .site-logo img, .brand img');
            if (logo) return logo.src || logo.getAttribute('data-src') || '';
            return '';
        }""")
        fields["sourceIcon"] = icon or ""
    except Exception:
        fields["sourceIcon"] = ""

    # ===== searchUrl（重点） =====
    try:
        search_info = page.evaluate("""() => {
            // 查找搜索表单
            const forms = document.querySelectorAll('form');
            let best = null;
            for (const form of forms) {
                const action = (form.action || form.getAttribute('action') || '').trim();
                const method = (form.method || 'get').toLowerCase();
                const inputs = form.querySelectorAll('input[type="text"], input[type="search"], input:not([type])');
                if (action && action.indexOf('javascript:') < 0 && action !== '#' && inputs.length > 0) {
                    // 优先选择含 search/wd/q/key 的表单
                    const actionLower = action.toLowerCase();
                    const inputName = inputs[0].name || '';
                    const score = (actionLower.indexOf('search') >= 0 ? 3 : 0) +
                                  (inputName.toLowerCase().indexOf('wd') >= 0 || inputName.toLowerCase().indexOf('key') >= 0 || inputName.toLowerCase().indexOf('q') >= 0 || inputName.toLowerCase().indexOf('search') >= 0 ? 2 : 0) +
                                  (inputs.length > 0 ? 1 : 0);
                    if (!best || score > best.score) {
                        best = {action: action, method: method, inputName: inputName || 'q', score: score};
                    }
                }
            }
            // 退而求其次：找搜索链接
            if (!best) {
                const searchLinks = document.querySelectorAll('a[href*="search"], a[href*="Search"], a[href*="检索"]');
                for (const a of searchLinks) {
                    if (a.href && a.href.indexOf('javascript:') < 0) {
                        best = {action: a.href, method: 'get', inputName: 'q', score: 1, is_link: true};
                        break;
                    }
                }
            }
            return best;
        }""")
        if search_info and search_info.get("action"):
            action = search_info["action"]
            input_name = search_info.get("inputName", "q")
            method = search_info.get("method", "get").lower()
            # 构造searchUrl（脱敏后保留模式）
            if method == "post":
                masked_action = mask_url(action)
                fields["searchUrl"] = f"{masked_action},{{\"method\":\"POST\",\"body\":\"{input_name}={{{{key}}}}\"}}"
            else:
                masked_action = mask_url(action)
                # 检查是否需要分页
                fields["searchUrl"] = f"{masked_action}?{input_name}={{{{key}}}}&page={{{{page}}}}"
            fields["_search_form_method"] = method
        else:
            fields["searchUrl"] = ""
            fields["_search_form_method"] = "none"
    except Exception as e:
        fields["searchUrl"] = ""
        fields["_search_form_method"] = f"error:{sanitize_error(str(e), 60)}"
    try:
        # ===== sortUrl（导航分类） =====
        sort_urls = page.evaluate("""() => {
            const result = [];
            // 优先导航菜单
            const navSelectors = [
                'nav a', '.nav a', '.menu a', '.navbar a',
                '.header-menu a', '.main-nav a', '.main-menu a',
                '.category a', '.categories a', '.cat-item a',
                '.sidebar .cat-item a', '#nav a', '.top-nav a',
                '.navi a', '.navigation a', '.menu-list a'
            ];
            const seen = new Set();
            for (const sel of navSelectors) {
                const links = document.querySelectorAll(sel);
                for (const a of links) {
                    const href = a.href || '';
                    const text = (a.textContent || '').trim();
                    if (href && text && !seen.has(href) &&
                        href.startsWith('http') &&
                        href.indexOf('javascript:') < 0 &&
                        href.indexOf('#') < 0 &&
                        href !== window.location.href &&
                        text.length < 20 && text.length > 0) {
                        // 排除明显的非分类链接
                        const skipKeywords = ['登录','注册','搜索','关于','联系','首页','home','login','register','search','about','contact'];
                        let skip = false;
                        for (const kw of skipKeywords) {
                            if (text === kw || text.toLowerCase() === kw) { skip = true; break; }
                        }
                        if (!skip) {
                            seen.add(href);
                            result.push(text + '::' + href);
                        }
                    }
                }
                if (result.length >= 15) break;
            }
            return result.slice(0, 15);
        }""")
        if sort_urls:
            # 脱敏后输出
            masked_lines = []
            for line in sort_urls:
                # line格式: 名称::URL
                parts = line.split('::', 1)
                if len(parts) == 2:
                    masked_url = mask_url(parts[1])
                    masked_lines.append(f"{parts[0]}::{masked_url}")
                else:
                    masked_lines.append(line)
            fields["sortUrl"] = "\n".join(masked_lines)
        else:
            fields["sortUrl"] = ""
    except Exception:
        fields["sortUrl"] = ""

    # ===== ruleArticles（列表项选择器） =====
    try:
        articles_selector = page.evaluate("""() => {
            // 探测列表项容器
            const candidates = [
                '.post-list .post, .article-list .article, .entry-list .entry',
                '.list li, .posts li, ul.article li, .news-list li',
                '.card, .entry-card, .post-card',
                '.item, .list-item, .article-item, .news-item',
                '.excerpt, .post-excerpt, .news-excerpt',
                'article, .post, .entry',
                '.thumbnail a, .thumb a, .pic-list li',
                '.blog-list li, .blog-list .item, .news li',
                '.waterfall .item, .grid li, .grid .item',
                'ul li a:has(img), .grid li, .list-box .item'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 3 && els.length < 500) {
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

    # ===== ruleTitle =====
    try:
        title_selector = page.evaluate("""() => {
            const candidates = [
                'h2 a, h3 a, h2.title a, h3.title a',
                '.title a, .post-title a, .entry-title a',
                '.card-title a, .item-title a, .news-title a',
                'a.title, a.post-title, a.news-title',
                '.article-title a, .entry-title a',
                '.item h2 a, .item h3 a, .card h3 a'
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

    # ===== ruleLink =====
    try:
        link_selector = page.evaluate("""() => {
            const candidates = [
                'h2 a, h3 a, h2.title a, h3.title a',
                '.title a, .post-title a, .entry-title a',
                '.card-title a, .item-title a, .news-title a',
                'a.title, a.post-title, a.news-title',
                '.thumb a, .thumbnail a, .pic a',
                '.article-title a, .entry-title a',
                '.item h2 a, .item h3 a, .card h3 a'
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

    # ===== ruleImage =====
    try:
        image_selector = page.evaluate("""() => {
            const candidates = [
                'img[data-src]', 'img[data-original]', 'img[data-lazy-src]',
                '.thumb img, .thumbnail img, .pic img',
                '.post-thumb img, .entry-thumb img, .article-thumb img',
                '.card img, .entry-card img, .news-thumb img',
                '.item img, .list-item img, .article-item img',
                'article img, .post img, .entry img',
                '.excerpt img, .post-excerpt img'
            ];
            for (const sel of candidates) {
                try {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 1) {
                        const first = els[0];
                        const src = first.src || first.getAttribute('data-src') || first.getAttribute('data-original');
                        if (src) return sel;
                    }
                } catch(e) {}
            }
            const allImgs = document.querySelectorAll('img[src]');
            if (allImgs.length >= 3) return 'img';
            return '';
        }""")
        if image_selector:
            # 探测属性
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

    # ===== ruleNextPage =====
    try:
        next_page = page.evaluate("""() => {
            const candidates = [
                'a.next', 'a.nextpage', '.next a', '.pagination .next a',
                'a[rel="next"]', '.pager a:last-child', '.page-next a',
                '.nav-links .next a', '.page-nav a.next',
                '.pagination a:last-child', '.pagebar a:last-child'
            ];
            for (const sel of candidates) {
                try {
                    const el = document.querySelector(sel);
                    if (el && el.href) return sel + '@href';
                } catch(e) {}
            }
            // 中文/英文文本兜底
            const textCandidates = [
                'a:contains("下一页")', 'a:contains("下页")', 'a:contains("Next")',
                'a:contains("next")', 'a:contains("更多")', 'a:contains("more")'
            ];
            for (const sel of textCandidates) {
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

    # ===== rulePubDate =====
    try:
        pubdate = page.evaluate("""() => {
            const candidates = [
                'time', '.date', '.post-date', '.entry-date', '.news-date',
                '.time', '.published', '.post-time', '.article-date',
                'meta[property="article:published_time"]',
                '.meta .date', '.info .date', '.info time',
                '.post-meta time', '.entry-meta time'
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


def detect_rule_content_template(page) -> tuple:
    """访问详情页后，根据DOM特征自动选择ruleContent模板"""
    template = "W1"
    template_code = RULE_CONTENT_TEMPLATE_W1
    notes = []

    try:
        features = page.evaluate("""() => {
            const result = {
                has_content_div: false,
                has_article_content: false,
                has_post_content: false,
                has_entry_content: false,
                is_json_response: false,
                content_p_count: 0,
                article_count: 0,
                body_text_length: 0
            };
            // 标准内容容器
            const contentDivs = document.querySelectorAll(
                '.article-content, .entry-content, .post-content, .content, .article-body, .read-content, .text, #content, #article'
            );
            result.has_content_div = contentDivs.length > 0;

            const articleContents = document.querySelectorAll('.article-content');
            result.has_article_content = articleContents.length > 0;

            const postContents = document.querySelectorAll('.post-content, .entry-content');
            result.has_post_content = postContents.length > 0;

            // 段落数量
            const allP = document.querySelectorAll('p');
            result.content_p_count = allP.length;
            result.article_count = document.querySelectorAll('article').length;

            // body 文本长度
            result.body_text_length = document.body ? document.body.innerText.length : 0;

            // JSON 响应检测
            try {
                const ct = document.contentType || '';
                if (ct.indexOf('json') >= 0) result.is_json_response = true;
            } catch(e) {}

            return result;
        }""")

        if features.get("has_article_content") or features.get("has_post_content") or features.get("has_entry_content"):
            template = "W1"
            template_code = RULE_CONTENT_TEMPLATE_W1
            notes.append(f"content_div_found,p_count={features.get('content_p_count')}")
        elif features.get("is_json_response"):
            template = "W2"
            template_code = RULE_CONTENT_TEMPLATE_W2
            notes.append("json_response_detected")
        elif features.get("content_p_count", 0) >= 5:
            template = "W3"
            template_code = RULE_CONTENT_TEMPLATE_W3
            notes.append(f"p_count={features.get('content_p_count')}")
        elif features.get("body_text_length", 0) > 500:
            template = "W3"
            template_code = RULE_CONTENT_TEMPLATE_W3
            notes.append(f"body_text_len={features.get('body_text_length')}")
        else:
            template = "W1"
            template_code = RULE_CONTENT_TEMPLATE_W1
            notes.append("fallback_to_W1")
    except Exception as e:
        notes.append(f"detect_error:{sanitize_error(str(e), 100)}")
        template = "W1"
        template_code = RULE_CONTENT_TEMPLATE_W1

    return template, template_code, notes


def detect_popup_and_anti_crawl(page) -> dict:
    """检测弹框/反爬/Cloudflare"""
    info = {
        "has_popup": False,
        "popup_count": 0,
        "cf_challenge": False,
        "login_required": False,
        "captcha_required": False,
    }

    try:
        content = page.content()
        # Cloudflare 检测
        if ("Just a moment" in content or "Checking your browser" in content or
            "cf-browser-verification" in content or "challenge-platform" in content):
            info["cf_challenge"] = True
    except Exception:
        pass

    try:
        popup_info = page.evaluate("""() => {
            const popups = document.querySelectorAll(
                '.popup, .modal, .dialog, .mask, .overlay, .ad-mask, .ad-box, .ads-box, .float-ad, .float-box, ' +
                '.modal-box, .dialog-box, .popup-box, .ad-layer, .ad-popup, .ad-dialog, ' +
                '[class*="popup"][style*="block"], [class*="modal"][style*="block"], [class*="dialog"][style*="block"]'
            );
            const visiblePopups = [];
            popups.forEach(p => {
                const style = window.getComputedStyle(p);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    visiblePopups.push(p.className || p.id || 'popup');
                }
            });
            return {
                total: popups.length,
                visible: visiblePopups.length,
                classes: visiblePopups.slice(0, 5)
            };
        }""")
        if popup_info.get("visible", 0) > 0:
            info["has_popup"] = True
            info["popup_count"] = popup_info["visible"]
    except Exception:
        pass

    try:
        # 登录/验证码检测
        login_info = page.evaluate("""() => {
            const loginForms = document.querySelectorAll('form[action*="login"], form[action*="signin"], #login-form, .login-form');
            const captchaImgs = document.querySelectorAll('img[src*="captcha"], img[src*="verify"], img[src*="code"], .captcha, #captcha');
            const verifyText = document.body ? (document.body.innerText.match(/请登录|请先登录|登录后查看|Please login|Please sign in/) || []) : [];
            return {
                login_forms: loginForms.length,
                captcha_imgs: captchaImgs.length,
                login_text_count: verifyText.length
            };
        }""")
        if login_info.get("login_forms", 0) > 0 or login_info.get("login_text_count", 0) > 0:
            info["login_required"] = True
        if login_info.get("captcha_imgs", 0) > 0:
            info["captcha_required"] = True
    except Exception:
        pass

    return info


def find_detail_page_url(page, source_url: str) -> str:
    """从列表页找一个详情页URL用于分析"""
    try:
        detail_url = page.evaluate("""() => {
            const candidates = document.querySelectorAll(
                '.post a[href], .article a[href], .entry a[href], ' +
                '.card a[href], .entry-card a[href], .post-card a[href], ' +
                'article a[href], .item a[href], .list-item a[href], ' +
                'h2 a[href], h3 a[href], .title a[href], .post-title a[href], ' +
                '.article-title a[href], .entry-title a[href]'
            );
            for (const a of candidates) {
                const href = a.href;
                if (href && href.startsWith('http') &&
                    href.indexOf('javascript:') < 0 &&
                    href.indexOf('#') < 0 &&
                    href !== window.location.href) {
                    return href;
                }
            }
            return '';
        }""")
        return detail_url
    except Exception:
        return ""


def build_js_rule(popup_info: dict) -> str:
    """根据弹框检测结果构建jsRule"""
    if popup_info.get("has_popup"):
        return JS_RULE_POPUP_CLOSE
    if popup_info.get("captcha_required") or popup_info.get("cf_challenge"):
        return JS_RULE_ANTI_CRAWL
    return ""


def analyze_source(playwright, source, array_idx: int) -> dict:
    """分析单个源"""
    result = {
        "idx": array_idx,
        "customOrder": source.get("customOrder", 0),
        "type": 0,
        "source_url_accessible": False,
        "http_status": 0,
        "html_length": 0,
        "fields": {},
        "special_config": {
            "loginUrl": "",
            "enabledCookieJar": bool(source.get("enabledCookieJar", False)),
            "enableJs": bool(source.get("enableJs", True)),
            "loadWithBaseUrl": bool(source.get("loadWithBaseUrl", False)),
            "jsRule": ""
        },
        "rule_content_template": "W1",
        "page_signals": {
            "has_popup": False,
            "popup_count": 0,
            "cf_challenge": False,
            "login_required": False,
            "captcha_required": False,
            "detail_page_accessible": False,
        },
        "analysis_notes": []
    }

    source_url = source.get("sourceUrl", "")
    if not source_url:
        result["analysis_notes"].append("empty_source_url")
        return result

    # 保留原有反爬配置
    existing_login_url = source.get("loginUrl", "") or ""
    if existing_login_url:
        # 不输出原URL，用占位符
        result["special_config"]["loginUrl"] = "@js:java.startBrowserAwait(source.sourceUrl,'verify');"
        result["special_config"]["enabledCookieJar"] = True
        result["analysis_notes"].append("has_existing_loginUrl")

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
            user_agent="Mozilla/5.0 (Linux; Android 12; SM-G9910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            viewport={'width': 412, 'height': 915},
            ignore_https_errors=True,
            locale="zh-CN",
        )
        # 注入反检测
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT)
        page.set_default_navigation_timeout(NAV_TIMEOUT + 5000)

        # 访问首页
        try:
            response = page.goto(source_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            if response:
                result["http_status"] = response.status
                if response.status < 500:
                    result["source_url_accessible"] = True
                    result["analysis_notes"].append(f"status={response.status}")
                else:
                    result["analysis_notes"].append(f"bad_status={response.status}")
        except PlaywrightTimeout:
            result["analysis_notes"].append("error:Timeout")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        except Exception as e:
            err = sanitize_error(str(e), 150)
            result["analysis_notes"].append(f"error:{err}")
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

            # html 长度
            try:
                content = page.content()
                result["html_length"] = len(content)
            except Exception:
                pass

            # 检测弹框/反爬
            try:
                popup_info = detect_popup_and_anti_crawl(page)
                result["page_signals"].update({
                    "has_popup": popup_info["has_popup"],
                    "popup_count": popup_info["popup_count"],
                    "cf_challenge": popup_info["cf_challenge"],
                    "login_required": popup_info["login_required"],
                    "captcha_required": popup_info["captcha_required"],
                })
                if popup_info["cf_challenge"]:
                    result["analysis_notes"].append("cf_block_detected")
                    # 等待 CF
                    try:
                        page.wait_for_timeout(8000)
                        new_content = page.content()
                        if "Just a moment" not in new_content:
                            result["analysis_notes"].append("cf_passed")
                        else:
                            result["analysis_notes"].append("cf_still_blocked")
                    except Exception:
                        pass
                if popup_info["has_popup"]:
                    result["analysis_notes"].append(f"popup_detected:{popup_info['popup_count']}")
                if popup_info["login_required"]:
                    result["analysis_notes"].append("login_required")
                    if not result["special_config"]["loginUrl"]:
                        result["special_config"]["loginUrl"] = "@js:java.startBrowserAwait(source.sourceUrl,'verify');"
                    result["special_config"]["enabledCookieJar"] = True
                if popup_info["captcha_required"]:
                    result["analysis_notes"].append("captcha_required")
            except Exception as e:
                result["analysis_notes"].append(f"popup_detect_error:{sanitize_error(str(e), 60)}")

            # 构建 jsRule（重点）
            result["special_config"]["jsRule"] = build_js_rule(popup_info) if popup_info else ""
            if result["special_config"]["jsRule"]:
                result["analysis_notes"].append("jsRule_configured")

            # 提取首页字段
            try:
                fields = extract_page_fields(page, source_url)
                result["fields"].update(fields)
            except Exception as e:
                result["analysis_notes"].append(f"extract_error:{sanitize_error(str(e), 100)}")

            # 访问详情页分析 ruleContent
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
                            result["page_signals"]["detail_page_accessible"] = True
                            # 详情页也检测弹框（覆盖更全面）
                            try:
                                detail_popup = detect_popup_and_anti_crawl(detail_page)
                                if detail_popup["has_popup"] and not result["special_config"]["jsRule"]:
                                    result["special_config"]["jsRule"] = build_js_rule(detail_popup)
                                    result["analysis_notes"].append("jsRule_from_detail_page")
                            except Exception:
                                pass
                        else:
                            result["analysis_notes"].append("detail_page_bad_status")
                            result["fields"]["ruleContent"] = RULE_CONTENT_TEMPLATE_W1
                            result["rule_content_template"] = "W1"
                        detail_page.close()
                    except Exception as e:
                        result["analysis_notes"].append(f"detail_page_error:{sanitize_error(str(e), 100)}")
                        result["fields"]["ruleContent"] = RULE_CONTENT_TEMPLATE_W1
                        result["rule_content_template"] = "W1"
                else:
                    result["analysis_notes"].append("no_detail_page_found")
                    result["fields"]["ruleContent"] = RULE_CONTENT_TEMPLATE_W1
                    result["rule_content_template"] = "W1"
            except Exception as e:
                result["analysis_notes"].append(f"detail_find_error:{sanitize_error(str(e), 100)}")
                result["fields"]["ruleContent"] = RULE_CONTENT_TEMPLATE_W1
                result["rule_content_template"] = "W1"

            # 保留原有规则字段（如果新提取为空）
            keep_fields = ['sourceIcon', 'searchUrl', 'sortUrl', 'ruleArticles',
                          'ruleTitle', 'ruleLink', 'ruleImage', 'ruleNextPage',
                          'rulePubDate', 'ruleContent']
            for k in keep_fields:
                existing = source.get(k, "") or ""
                if existing and not result["fields"].get(k):
                    # 脱敏后保留
                    if k in ('searchUrl', 'sortUrl', 'sourceIcon'):
                        result["fields"][k] = mask_url(existing) if k == 'sourceIcon' else (
                            self_mask_search_url(existing) if k == 'searchUrl' else existing
                        )
                    else:
                        result["fields"][k] = existing
                    result["analysis_notes"].append(f"keep_existing_{k}")
                elif existing and len(existing) > 1000 and k == 'ruleContent':
                    # 参考源的超长ruleContent保留
                    result["fields"][k] = existing
                    result["rule_content_template"] = "existing"
                    result["analysis_notes"].append(f"keep_existing_long_{k}_len={len(existing)}")

    except Exception as e:
        result["analysis_notes"].append(f"fatal_error:{sanitize_error(str(e), 200)}")
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


def self_mask_search_url(s: str) -> str:
    """脱敏searchUrl，保留结构"""
    if not s:
        return ""
    masked = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', s)
    masked = re.sub(r'/\d{4,}', '/{id}', masked)
    return masked


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[FATAL] input not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # 筛选 type=0 + idx 50-99
    target_indices = []
    for i, s in enumerate(sources):
        if 50 <= i <= 99 and s.get("type") == 0:
            comment = s.get("sourceComment", "") or ""
            if "AI_CLASSIFY:access_failed" in comment or "AI_CLASSIFY:skipped" in comment:
                continue
            target_indices.append(i)

    print(f"[INFO] target sources: {len(target_indices)}")
    print(f"[INFO] indices: {target_indices}")

    results = []
    success_count = 0
    failed_count = 0

    with sync_playwright() as playwright:
        for i, idx in enumerate(target_indices):
            print(f"\n[PROGRESS {i+1}/{len(target_indices)}] idx={idx}...")
            source = sources[idx]
            start = time.time()
            try:
                result = analyze_source(playwright, source, idx)
                elapsed = time.time() - start
                result["elapsed_seconds"] = round(elapsed, 2)
                if result["source_url_accessible"]:
                    success_count += 1
                    print(f"  [OK] template={result['rule_content_template']}, "
                          f"popup={result['page_signals']['has_popup']}, "
                          f"jsRule={'Y' if result['special_config']['jsRule'] else 'N'}, "
                          f"elapsed={elapsed:.1f}s")
                else:
                    failed_count += 1
                    print(f"  [FAIL] notes={result['analysis_notes'][:3]}, elapsed={elapsed:.1f}s")
                results.append(result)
            except Exception as e:
                failed_count += 1
                err = sanitize_error(str(e), 200)
                print(f"  [EXCEPTION] {err}")
                results.append({
                    "idx": idx,
                    "customOrder": source.get("customOrder", 0),
                    "type": 0,
                    "source_url_accessible": False,
                    "http_status": 0,
                    "html_length": 0,
                    "fields": {},
                    "special_config": {
                        "loginUrl": "",
                        "enabledCookieJar": bool(source.get("enabledCookieJar", False)),
                        "enableJs": bool(source.get("enableJs", True)),
                        "loadWithBaseUrl": bool(source.get("loadWithBaseUrl", False)),
                        "jsRule": ""
                    },
                    "rule_content_template": "W1",
                    "page_signals": {},
                    "analysis_notes": [f"exception:{err}"],
                    "elapsed_seconds": round(time.time() - start, 2)
                })

            # 立即写入中间结果（防崩溃）
            try:
                os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "agent": "web_source_analyzer_batch2",
                        "batch_range": "50-99",
                        "total_analyzed": len(results),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "results": results,
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  [WARN] save intermediate failed: {sanitize_error(str(e), 100)}")

    # 统计
    template_dist = {}
    jsRule_count = 0
    searchUrl_count = 0
    popup_count = 0
    cf_count = 0
    login_count = 0
    for r in results:
        t = r.get("rule_content_template", "unknown")
        template_dist[t] = template_dist.get(t, 0) + 1
        if r.get("special_config", {}).get("jsRule"):
            jsRule_count += 1
        if r.get("fields", {}).get("searchUrl"):
            searchUrl_count += 1
        ps = r.get("page_signals", {})
        if ps.get("has_popup"):
            popup_count += 1
        if ps.get("cf_challenge"):
            cf_count += 1
        if ps.get("login_required") or r.get("special_config", {}).get("loginUrl"):
            login_count += 1

    print(f"\n[FINAL] total={len(results)} success={success_count} failed={failed_count}")
    print(f"[FINAL] template_distribution: {template_dist}")
    print(f"[FINAL] jsRule_configured: {jsRule_count}")
    print(f"[FINAL] searchUrl_extracted: {searchUrl_count}")
    print(f"[FINAL] popup_detected: {popup_count}, cf_challenge: {cf_count}, login_required: {login_count}")
    print(f"[OUTPUT] {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
