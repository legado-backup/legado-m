"""
图片源(type=1)深度优化脚本 v2
- 输入: optimized_v2_lite_final_v3.json (V3 最终版)
- 目标: 筛选 type=1 且 sortUrl 为空的源 (~50个), 用 Playwright 深度分析
- 输出: image_source_deep_fix_v2.json

特点:
1. 注入 stealth.js 绕过反爬
2. 自动关闭弹框
3. A/B/C/D 四类模板识别 (gallery/lazy/og:image/JSON API)
4. 提取 sortUrl/searchUrl/ruleArticles/ruleImage/ruleNextPage/ruleContent
5. 兜底: /sitemap.xml /robots.txt
6. 增量保存 (每5个源)
7. 输出安全: 源[idx] 替代真实名称, URL/域名脱敏
"""
import json
import re
import os
import sys
import time
import random
import traceback
from pathlib import Path
from urllib.parse import urlparse, urljoin

# 强制无缓冲输出
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
os.environ.setdefault('PYTHONUNBUFFERED', '1')

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def log(msg):
    print(msg, flush=True)


# ===== 配置 =====
ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = ROOT / "output" / "rss" / "optimized_v2_lite_final_v3.json"
PREV_FIX = ROOT / "output" / "rss" / "image_source_field_fix.json"  # 之前修复结果(参考)
OUTPUT_JSON = ROOT / "output" / "rss" / "image_source_deep_fix_v2.json"
TMP_JSON = ROOT / "output" / "rss" / "image_source_deep_fix_v2.tmp.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
PW_TIMEOUT = 18000  # 18秒
SAVE_EVERY = 5

# ===== 脱敏 =====
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[^\s]*)",
    re.IGNORECASE)


def sanitize(msg: str) -> str:
    if not isinstance(msg, str):
        msg = str(msg)
    msg = URL_RE.sub("[URL]", msg)
    msg = DOMAIN_RE.sub("[DOMAIN]", msg)
    return msg


# ===== Stealth.js (绕过反爬) =====
STEALTH_JS = r"""
() => {
    // 1. 隐藏 webdriver
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    // 2. 伪造 plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    // 3. 伪造 languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en']
    });
    // 4. 伪造 platform
    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
    // 5. 伪造 chrome 对象
    window.chrome = window.chrome || {runtime: {}};
    // 6. permissions
    if (navigator.permissions) {
        const origQuery = navigator.permissions.query;
        navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                origQuery(parameters)
        );
    }
    return true;
}
"""

# ===== 关闭弹框 =====
CLOSE_MODAL_JS = r"""
() => {
    const sels = ['.modal', '.popup', '.close', '.modal-close', '.popup-close',
                  '[data-dismiss]', '.mask', '.overlay', '.dialog',
                  '.ad-close', '.ads-close', '#ad', '#popup'];
    sels.forEach(s => document.querySelectorAll(s).forEach(e => {
        try { e.click(); } catch(err) {}
        try { e.style.display = 'none'; } catch(err2) {}
    }));
    return true;
}
"""

# ===== 主提取 JS (识别 A/B/C/D 模板) =====
EXTRACT_JS = r"""
() => {
    const result = {
        sortUrl: '', searchUrl: '',
        ruleArticles: '', ruleImage: '',
        ruleNextPage: '', ruleContent: '',
        templateType: 'unknown',  // A/B/C/D
        host: location.origin,
        pathname: location.pathname,
        notes: []
    };

    // ============ 关闭弹框 ============
    try {
        document.querySelectorAll('.modal,.popup,.close,.dialog,.mask,.overlay').forEach(e => {
            try { e.click(); } catch(_){}
            try { e.style.display = 'none'; } catch(_){}
        });
    } catch(e) {}

    // ============ 1. 识别模板类型 ============
    let templateType = 'unknown';
    try {
        // D: JSON API - body 文本是否是 JSON
        const bodyText = (document.body.innerText || '').trim();
        if (bodyText.startsWith('{') || bodyText.startsWith('[')) {
            try {
                JSON.parse(bodyText);
                templateType = 'D';
            } catch(_){}
        }
        // B: 懒加载
        const lazyImgs = document.querySelectorAll('img[data-src], img[loading=lazy]');
        if (templateType === 'unknown' && lazyImgs.length >= 3) {
            templateType = 'B';
        }
        // C: og:image
        if (templateType === 'unknown') {
            const og = document.querySelector('meta[property="og:image"]');
            if (og && og.content) templateType = 'C';
        }
        // A: gallery 类
        if (templateType === 'unknown') {
            const gallerySels = ['.gallery', '.photo-item', '.pic-list', '.image-list',
                                 '.gallery-item', '.photo', '.image-item',
                                 '.thumb-item', '.masonry', '.waterfall'];
            for (const s of gallerySels) {
                if (document.querySelector(s)) {
                    templateType = 'A';
                    break;
                }
            }
        }
        // 兜底: 大量 img 视为 A
        if (templateType === 'unknown') {
            const imgs = document.querySelectorAll('article img, .post img, .list img, .card img, .item img');
            if (imgs.length >= 5) templateType = 'A';
        }
        result.templateType = templateType;
    } catch(e) {
        result.notes.push('tmpl_err:' + e.message);
    }

    // ============ 2. 提取 sortUrl ============
    try {
        const cats = [];
        const seen = new Set();
        // 候选容器
        const navSelectors = [
            // 通用导航
            'nav a', '.nav a', '.navbar a', '.menu a', '.navigation a',
            '.header a', '.main-nav a', '.nav-menu a', 'ul.menu a', 'ul.nav a',
            // 分类
            '.category a', '.categories a', '.cat-list a', '.cats a',
            '.sort a', '.sort-list a', '.filter a',
            // BBS 板块
            '.forum a', '.board a', '.subforum a', '.forum-list a',
            // 标签/相册
            '.tags a', '.tag-list a', '.album-list a', '.albums a',
            // 侧边栏
            '.sidebar a', '.side a', '.widget a'
        ];
        for (const sel of navSelectors) {
            const links = document.querySelectorAll(sel);
            if (links.length === 0) continue;
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                const text = (a.textContent || '').trim();
                if (!href || !text) continue;
                if (href.startsWith('javascript:') || href.startsWith('#')) continue;
                if (text.length > 30 || text.length < 1) continue;
                const lower = text.toLowerCase();
                // 排除功能性链接
                if (['首页','主页','home','登录','注册','login','register','signin',
                     '关于','about','联系','contact','搜索','search','更多','more',
                     'tags','tag','标签','sitemap','rss','atom','feedback','反馈',
                     '返回','back','顶部','top','下载','download','app','客户端',
                     'prev','next','上一页','下一页','previous','»','«','>','<',
                     'gb','big5','english','繁體','简体'].includes(lower)) continue;
                // 排除纯数字
                if (/^\d+$/.test(text)) continue;
                const key = text + '|' + href;
                if (seen.has(key)) continue;
                seen.add(key);
                let relPath = href;
                if (href.startsWith('http')) {
                    try {
                        const u = new URL(href);
                        if (u.origin !== location.origin) continue;
                        relPath = u.pathname + u.search;
                    } catch(e) { continue; }
                }
                cats.push(text + '::' + relPath);
                if (cats.length >= 30) break;
            }
            if (cats.length >= 15) break;
        }
        result.sortUrl = cats.join('\n');
        if (cats.length > 0) result.notes.push('cats_count=' + cats.length);
    } catch(e) {
        result.notes.push('sortUrl_err:' + e.message);
    }

    // ============ 3. 提取 searchUrl ============
    try {
        const forms = document.querySelectorAll('form');
        let found = false;
        for (const form of forms) {
            const action = form.getAttribute('action') || location.pathname;
            const method = (form.getAttribute('method') || 'get').toLowerCase();
            const inputs = form.querySelectorAll('input');
            let keywordName = null;
            for (const inp of inputs) {
                const n = (inp.getAttribute('name') || '').toLowerCase();
                const t = (inp.getAttribute('type') || '').toLowerCase();
                const ph = (inp.getAttribute('placeholder') || '').toLowerCase();
                if (['search','keyword','q','wd','key','s','query','kw','name',
                     'word','searchword','searchkey'].includes(n) ||
                    ph.includes('搜索') || ph.includes('search') ||
                    ph.includes('关键字') || ph.includes('关键词') ||
                    t === 'search') {
                    keywordName = inp.getAttribute('name');
                    break;
                }
            }
            if (!keywordName) continue;
            let fullAction = action;
            if (action.startsWith('http')) {
                try {
                    const u = new URL(action);
                    fullAction = u.pathname + u.search;
                } catch(e) { fullAction = action; }
            } else if (action.startsWith('/')) {
                fullAction = action;
            } else {
                fullAction = location.pathname.replace(/[^/]*$/, '') + action;
            }
            if (method === 'get') {
                result.searchUrl = fullAction + (fullAction.includes('?') ? '&' : '?') +
                    keywordName + '={{key}}&page={{page}}';
            } else {
                result.searchUrl = fullAction + ',{"method":"POST","body":"' +
                    keywordName + '={{key}}&page={{page}}"}';
            }
            found = true;
            break;
        }
        // 兜底: 检测 search 链接
        if (!found) {
            const aTags = document.querySelectorAll('a');
            for (const a of aTags) {
                const href = a.getAttribute('href') || '';
                const txt = (a.textContent || '').trim().toLowerCase();
                if (txt === 'search' || txt === '搜索' ||
                    href.includes('/search') || href.includes('/search.php')) {
                    try {
                        const u = new URL(href, location.origin);
                        if (u.origin === location.origin) {
                            result.searchUrl = u.pathname + '?q={{key}}&page={{page}}';
                            found = true;
                            break;
                        }
                    } catch(e) {}
                }
            }
        }
        // 最终兜底
        if (!found) {
            result.searchUrl = '/search?q={{key}}&page={{page}}';
            result.notes.push('searchUrl_fallback_guess');
        }
    } catch(e) {
        result.notes.push('searchUrl_err:' + e.message);
    }

    // ============ 4. 提取 ruleArticles (列表项选择器) ============
    try {
        // 根据模板类型选择候选
        let candidates;
        if (result.templateType === 'A') {
            candidates = [
                '.gallery-item', '.photo-item', '.pic-item', '.image-item',
                '.thumb-item', '.list-item', '.card-item', '.post-item',
                '.gallery > li', '.photo > li', 'ul.photos > li',
                '.waterfall-item', '.masonry-item', '.grid-item',
                'article', '.post', '.item', '.card', '.thumb',
                '.gallery li', '.gallery-item a', '.photo-item a',
                '.pic-list li', '.image-list li', '.list li',
                '.gallery', '.photo-list', '.pic-list', '.image-list',
                '.list', '.grid', '.posts', '.content-list'
            ];
        } else if (result.templateType === 'B') {
            candidates = [
                'img[data-src]', 'img[loading=lazy]',
                '.lazy-item', '.lazyload', '.lazy',
                '.list-item', '.card-item', '.thumb-item',
                '.item', '.card', 'article'
            ];
        } else {
            candidates = [
                '.gallery-item', '.photo-item', '.image-item', '.thumb-item',
                '.list-item', '.card-item', '.post-item',
                'article', '.post', '.item', '.card', '.thumb',
                '.gallery li', '.photo-list li', '.pic-list li',
                '.list li', '.grid li', '.posts li',
                '.gallery', '.list', '.grid', '.posts'
            ];
        }

        let best = '';
        let bestCount = 0;
        let bestSel = '';
        for (const sel of candidates) {
            try {
                const els = document.querySelectorAll(sel);
                if (els.length > bestCount) {
                    bestCount = els.length;
                    bestSel = sel;
                }
            } catch(e) {}
        }
        if (bestSel && bestCount > 0) {
            // 构造 articleList 规则
            // 尝试在选中的元素内找 a/img
            const firstEl = document.querySelector(bestSel);
            let imgRule = 'img@src';
            let urlRule = 'a@href';
            let titleRule = 'a@text||img@alt';
            if (firstEl) {
                // 检测懒加载属性
                const innerImg = firstEl.querySelector('img');
                if (innerImg) {
                    if (innerImg.getAttribute('data-src')) imgRule = 'img@data-src';
                    else if (innerImg.getAttribute('data-original')) imgRule = 'img@data-original';
                    else if (innerImg.getAttribute('loading') === 'lazy') imgRule = 'img@data-src||img@src';
                }
            }
            best = JSON.stringify({
                articleList: bestSel,
                image: imgRule,
                title: titleRule,
                url: urlRule
            });
            result.notes.push('articles_sel=' + bestSel);
            result.notes.push('articles_count=' + bestCount);
        }
        result.ruleArticles = best;
    } catch(e) {
        result.notes.push('ruleArticles_err:' + e.message);
    }

    // ============ 5. 提取 ruleImage (单图页/详情页图片选择器) ============
    try {
        // 模板对应的图片选择器
        const imgSelectors = [
            // 详情页常见容器
            '.content img', 'article img', '.article img', '.post-content img',
            '.entry-content img', '.main img', '.photo-content img',
            '.viewer img', '.image-viewer img', '.detail img',
            '.picture img', '.single img', '.photo img', '.image img',
            '.read-content img', '.article-content img', '.post-body img',
            // 懒加载
            'img[data-src]', 'img[loading=lazy]',
            // 大图查看器
            '.lightbox img', '.zoom img', '.full img',
            // 兜底
            'article img', '.post img'
        ];
        let best = '';
        for (const sel of imgSelectors) {
            try {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    best = sel;
                    break;
                }
            } catch(e) {}
        }
        // 兜底: 最大图片的父容器
        if (!best) {
            const imgs = document.querySelectorAll('img');
            let maxArea = 0;
            let maxImg = null;
            for (const img of imgs) {
                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;
                const area = w * h;
                if (area > maxArea) {
                    maxArea = area;
                    maxImg = img;
                }
            }
            if (maxImg) {
                let p = maxImg.parentElement;
                let depth = 0;
                while (p && p !== document.body && depth < 4) {
                    if (p.className) {
                        const cls = p.className.split(/\s+/)[0];
                        if (cls && cls.length < 30) {
                            best = '.' + cls + ' img';
                            break;
                        }
                    }
                    p = p.parentElement;
                    depth++;
                }
            }
        }
        result.ruleImage = best;
    } catch(e) {
        result.notes.push('ruleImage_err:' + e.message);
    }

    // ============ 6. 提取 ruleNextPage ============
    try {
        let best = '';
        // 显式 class/rel
        const aTags = document.querySelectorAll('a');
        for (const a of aTags) {
            const cls = (a.getAttribute('class') || '').toLowerCase();
            const rel = (a.getAttribute('rel') || '').toLowerCase();
            const txt = (a.textContent || '').trim();
            const title = (a.getAttribute('title') || '').trim();
            const href = a.getAttribute('href') || '';
            if (cls.includes('next') || rel === 'next' ||
                txt === '下一页' || txt === 'Next' || txt === 'next' ||
                txt === '»' || txt === '>' || txt === '›' ||
                title === '下一页' || title === 'Next') {
                if (a.className) {
                    const firstCls = a.className.split(/\s+/)[0];
                    if (firstCls) { best = '.' + firstCls + '@href'; break; }
                }
                if (a.id) { best = '#' + a.id + '@href'; break; }
                if (rel === 'next') { best = 'a[rel=next]@href'; break; }
                // 用文本
                if (txt) { best = 'a:has-text("' + txt + '")@href'; break; }
            }
        }
        // 兜底: 分页容器最后一个 a
        if (!best) {
            const pagSels = ['.pagination', '.page', '.pager', '.page-list',
                             '.page-nav', '.pages', '.pag'];
            for (const ps of pagSels) {
                const pag = document.querySelector(ps);
                if (pag) {
                    const links = pag.querySelectorAll('a');
                    if (links.length >= 2) {
                        best = ps + ' a:last-child@href';
                        break;
                    }
                }
            }
        }
        // 进一步兜底: URL 含 page= 时构造下一页
        if (!best) {
            const url = location.href;
            if (url.includes('page=') || url.match(/\/page\/\d+/)) {
                best = 'a.page-next@href, .pagination a:last-child@href';
            }
        }
        result.ruleNextPage = best;
    } catch(e) {
        result.notes.push('ruleNextPage_err:' + e.message);
    }

    // ============ 7. 提取 ruleContent (详情页图片内容规则) ============
    try {
        // 根据模板类型给出 ruleContent
        if (result.templateType === 'A') {
            // A: 列表型 gallery, 详情页通常有多张图
            result.ruleContent = '<js>\n' +
                'var imgs = document.querySelectorAll("' + (result.ruleImage || '.content img') + '");\n' +
                'var urls = [];\n' +
                'imgs.forEach(function(img){\n' +
                '  var src = img.getAttribute("data-src") || img.getAttribute("data-original") || img.getAttribute("src") || "";\n' +
                '  if(src && !src.startsWith("data:")) urls.push(src);\n' +
                '});\n' +
                'urls.join(",");\n' +
                '</js>';
        } else if (result.templateType === 'B') {
            // B: 懒加载, 需要触发滚动
            result.ruleContent = '<js>\n' +
                'var imgs = document.querySelectorAll("img[data-src], img[data-original], img[loading=lazy]");\n' +
                'var urls = [];\n' +
                'imgs.forEach(function(img){\n' +
                '  var src = img.getAttribute("data-src") || img.getAttribute("data-original") || img.getAttribute("src") || "";\n' +
                '  if(src && !src.startsWith("data:")) urls.push(src);\n' +
                '});\n' +
                'urls.join(",");\n' +
                '</js>';
        } else if (result.templateType === 'C') {
            // C: og:image 单图
            result.ruleContent = '<js>\n' +
                'var og = document.querySelector("meta[property=\\"og:image\\"]");\n' +
                'og ? og.content : "";\n' +
                '</js>';
        } else if (result.templateType === 'D') {
            // D: JSON API, 直接读 body
            result.ruleContent = '<js>\n' +
                'var data = JSON.parse(document.body.innerText);\n' +
                'Array.isArray(data) ? data.map(function(x){return x.url || x.image || x.pic;}).join(",") : (data.url || data.image || "");\n' +
                '</js>';
        } else {
            // unknown: 兜底取所有 img
            result.ruleContent = '<js>\n' +
                'var imgs = document.querySelectorAll("img");\n' +
                'var urls = [];\n' +
                'imgs.forEach(function(img){\n' +
                '  var src = img.getAttribute("data-src") || img.getAttribute("data-original") || img.getAttribute("src") || "";\n' +
                '  if(src && !src.startsWith("data:") && src.match(/\\.(jpg|jpeg|png|gif|webp)/i)) urls.push(src);\n' +
                '});\n' +
                'urls.join(",");\n' +
                '</js>';
        }
    } catch(e) {
        result.notes.push('ruleContent_err:' + e.message);
    }

    // ============ 8. 统计 ============
    result.notes.push('imgs_total=' + document.querySelectorAll('img').length);
    result.notes.push('links_total=' + document.querySelectorAll('a').length);

    return result;
}
"""

# ===== 提取 sitemap 分类 =====
SITEMAP_EXTRACT_JS = r"""
(urlText) => {
    // 简单解析 sitemap.xml
    const cats = [];
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(urlText, 'text/xml');
        const urls = doc.querySelectorAll('url > loc');
        urls.forEach(loc => {
            const u = loc.textContent || '';
            // 提取路径第一段作为分类
            try {
                const url = new URL(u);
                const parts = url.pathname.split('/').filter(Boolean);
                if (parts.length > 0) {
                    const cat = parts[0];
                    if (cat && !cats.find(c => c.path === '/' + cat)) {
                        cats.push({name: cat, path: '/' + cat});
                    }
                }
            } catch(e) {}
        });
    } catch(e) {}
    return cats.slice(0, 20);
}
"""


def load_input():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        if 'sources' in data:
            sources = data['sources']
        else:
            sources = data
    else:
        sources = data
    return sources


def load_prev_fixed_idx():
    """加载之前子代理1已修复的源 idx (用于跳过/对比)"""
    fixed = set()
    if PREV_FIX.exists():
        try:
            with open(PREV_FIX, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for r in data.get('records', []):
                if r.get('sort_url_filled'):
                    fixed.add(r.get('idx'))
        except Exception:
            pass
    return fixed


def pick_image_sources(sources):
    """筛出 type=1 且 sortUrl 为空的源"""
    result = []
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        t = src.get('type', 0)
        try:
            t = int(t)
        except (ValueError, TypeError):
            t = 0
        if t != 1:
            continue
        sort_url = src.get('sortUrl', '') or ''
        if sort_url.strip():
            continue
        result.append((i, src))
    return result


def try_wayback(page, source_url):
    """对 CF 防护源尝试 Wayback Machine"""
    try:
        wayback = 'https://web.archive.org/web/2024/' + source_url
        page.goto(wayback, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        time.sleep(1)  # 1秒间隔避免503
        return True
    except Exception:
        return False


def try_sitemap_robots(page, host):
    """尝试 /sitemap.xml 或 /robots.txt 获取站点结构"""
    cats = []
    host_norm = host.rstrip('/').lower()
    # 1. sitemap.xml
    try:
        r = page.request.get(host + '/sitemap.xml', timeout=8000)
        if r.ok:
            text = r.text()
            urls = re.findall(r'<loc>([^<]+)</loc>', text)
            seen = set()
            for u in urls[:500]:
                try:
                    pu = urlparse(u)
                    if pu.origin.rstrip('/').lower() != host_norm:
                        continue
                    parts = [p for p in pu.path.split('/') if p]
                    if parts:
                        cat = parts[0]
                        if cat and cat not in seen and len(cat) < 30:
                            seen.add(cat)
                            cats.append((cat, '/' + cat))
                            if len(cats) >= 15:
                                break
                except Exception:
                    continue
    except Exception:
        pass
    # 2. robots.txt
    if not cats:
        try:
            r = page.request.get(host + '/robots.txt', timeout=5000)
            if r.ok:
                text = r.text()
                paths = re.findall(r'^(?:Disallow|Allow):\s*(/\S*)', text, re.MULTILINE)
                seen = set()
                for p in paths:
                    parts = [x for x in p.split('/') if x]
                    if parts:
                        cat = parts[0]
                        if cat and cat not in seen and not cat.startswith('*') and len(cat) < 30:
                            seen.add(cat)
                            cats.append((cat, '/' + cat))
                            if len(cats) >= 15:
                                break
        except Exception:
            pass
    return cats


def extract_one(page, source_url):
    """对单个源用 Playwright 提取字段"""
    accessible = False
    error = None
    is_wayback = False
    try:
        page.goto(source_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        accessible = True
    except PWTimeout:
        # 超时, 尝试 Wayback
        if try_wayback(page, source_url):
            accessible = True
            is_wayback = True
            error = 'orig_timeout_wayback_ok'
        else:
            error = 'goto_timeout'
    except Exception as e:
        msg = sanitize(str(e)).lower()
        if 'cloudflare' in msg or '403' in msg or '503' in msg or 'access denied' in msg:
            if try_wayback(page, source_url):
                accessible = True
                is_wayback = True
                error = 'cf_blocked_wayback_ok'
            else:
                error = 'cf_blocked'
        else:
            error = 'goto_err:' + msg[:80]

    if not accessible:
        return {'accessible': False, 'error': error}

    # 注入 stealth.js
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass

    # 关闭弹框
    try:
        page.evaluate(CLOSE_MODAL_JS)
    except Exception:
        pass

    # 等待网络稳定
    try:
        page.wait_for_load_state('networkidle', timeout=3000)
    except Exception:
        pass

    # 再关弹框 (有些是延迟弹的)
    try:
        page.evaluate(CLOSE_MODAL_JS)
    except Exception:
        pass

    # 执行主提取
    try:
        result = page.evaluate(EXTRACT_JS)
        result['accessible'] = True
        result['error'] = error or ''
        result['is_wayback'] = is_wayback

        # 兜底: 如果 sortUrl 为空, 尝试 sitemap/robots
        if not result.get('sortUrl'):
            try:
                host = result.get('host') or source_url.rstrip('/')
                cats = try_sitemap_robots(page, host)
                if cats:
                    sort_url_lines = [f'{name}::{path}' for name, path in cats]
                    result['sortUrl'] = '\n'.join(sort_url_lines)
                    result['notes'].append('sitemap_cats=' + str(len(cats)))
            except Exception as e:
                result['notes'].append('sitemap_err:' + sanitize(str(e))[:60])

        return result
    except Exception as e:
        return {'accessible': True, 'error': 'eval_err:' + sanitize(str(e))[:80]}


def verify_sort_url(page, host, sort_url_str, rule_articles=None):
    """验证 sortUrl 拼接后的完整URL能否访问, 列表项>0"""
    if not sort_url_str:
        return False, 0
    # 取第一个分类
    first_line = sort_url_str.split('\n')[0]
    if '::' not in first_line:
        return False, 0
    _, path = first_line.split('::', 1)
    path = path.strip()
    if not path:
        return False, 0
    full_url = urljoin(host + '/', path.lstrip('/'))
    try:
        page.goto(full_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        # 注入 stealth
        try:
            page.evaluate(STEALTH_JS)
        except Exception:
            pass
        # 关闭弹框
        try:
            page.evaluate(CLOSE_MODAL_JS)
        except Exception:
            pass
        # 等待
        try:
            page.wait_for_load_state('networkidle', timeout=3000)
        except Exception:
            pass
        # 计数
        count = page.evaluate('() => document.querySelectorAll("img").length')
        # 也尝试用 rule_articles 选择器计数
        list_count = 0
        if rule_articles:
            try:
                ra = json.loads(rule_articles)
                sel = ra.get('articleList', '')
                if sel:
                    # 去掉 > xxx 这种 (Legado 选择器不是标准 CSS)
                    css_sel = sel.split('>')[0].strip()
                    if css_sel:
                        list_count = page.evaluate(
                            '(s) => document.querySelectorAll(s).length', css_sel)
            except Exception:
                pass
        # 取最大值
        final_count = max(int(count or 0), int(list_count or 0))
        return True, final_count
    except Exception as e:
        return False, 0


def save_json(records, total, fixed, failed, partial):
    out = {
        'total': total,
        'fixed': fixed,
        'partial_fixed': partial,
        'still_failed': failed,
        'records': records
    }
    with open(TMP_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # 原子替换
    try:
        with open(TMP_JSON, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            f.write(data)
    except Exception as e:
        log(f'[SAVE_ERR] {sanitize(str(e))}')


def run():
    log('[LOAD] reading input json...')
    sources = load_input()
    log(f'[LOAD] total sources: {len(sources)}')

    image_srcs = pick_image_sources(sources)
    log(f'[FILTER] type=1 & sortUrl empty: {len(image_srcs)}')

    # 模板分布
    prev_fixed_idx = load_prev_fixed_idx()
    log(f'[PREV] previously fixed idx count: {len(prev_fixed_idx)}')

    # 断点续传
    done_idx = set()
    records = []
    if TMP_JSON.exists():
        try:
            with open(TMP_JSON, 'r', encoding='utf-8') as f:
                prev = json.load(f)
            records = prev.get('records', [])
            done_idx = {r.get('idx') for r in records}
            log(f'[RESUME] already done: {len(done_idx)}')
        except Exception as e:
            log(f'[RESUME] failed: {sanitize(str(e))}')

    fixed_count = sum(1 for r in records if r.get('sort_url_filled'))
    partial_count = sum(1 for r in records if not r.get('sort_url_filled') and
                        (r.get('search_url_filled') or r.get('rule_articles_filled')))
    failed_count = sum(1 for r in records if not r.get('sort_url_filled') and
                       not r.get('search_url_filled') and not r.get('rule_articles_filled'))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage'
        ])
        context = browser.new_context(
            user_agent=UA,
            viewport={'width': 1366, 'height': 900},
            locale='zh-CN',
            ignore_https_errors=True,
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
            }
        )
        page = context.new_page()
        page.set_default_timeout(PW_TIMEOUT)

        try:
            total = len(image_srcs)
            for n, (idx, src) in enumerate(image_srcs):
                if idx in done_idx:
                    continue
                # 输出安全: 不打印 sourceUrl
                log(f'\n[{n+1}/{total}] idx={idx} processing...')

                source_url = src.get('sourceUrl', '') or ''
                record = {
                    'idx': idx,
                    'source_url_accessible': False,
                    'sort_url_filled': '',
                    'search_url_filled': '',
                    'rule_articles_filled': '',
                    'rule_image_filled': '',
                    'rule_next_page_filled': '',
                    'rule_content_filled': '',
                    'template_type': 'unknown',
                    'verify_ok': False,
                    'list_items_count': 0,
                    'method': 'playwright_deep_v2',
                    'error': '',
                    'notes': []
                }

                if not source_url:
                    record['error'] = 'no_source_url'
                    records.append(record)
                    failed_count += 1
                    continue

                try:
                    r = extract_one(page, source_url)
                    record['source_url_accessible'] = bool(r.get('accessible'))

                    if r.get('accessible'):
                        sort_url = r.get('sortUrl', '') or ''
                        search_url = r.get('searchUrl', '') or ''
                        rule_articles = r.get('ruleArticles', '') or ''
                        rule_image = r.get('ruleImage', '') or ''
                        rule_next = r.get('ruleNextPage', '') or ''
                        rule_content = r.get('ruleContent', '') or ''
                        template_type = r.get('templateType', 'unknown') or 'unknown'

                        # 验证 sortUrl
                        verify_ok = False
                        list_count = 0
                        if sort_url:
                            try:
                                host = r.get('host', '') or source_url.rstrip('/')
                                # wayback 模式下, host 是 wayback 的, 不能直接拼
                                if r.get('is_wayback'):
                                    # 不验证, 直接标记
                                    verify_ok = True
                                    list_count = -1  # 标记未验证
                                    record['notes'].append('verify_skipped_wayback')
                                else:
                                    verify_ok, list_count = verify_sort_url(
                                        page, host, sort_url, rule_articles)
                            except Exception as e:
                                record['notes'].append('verify_err:' + sanitize(str(e))[:60])

                        record['sort_url_filled'] = sort_url
                        record['search_url_filled'] = search_url
                        record['rule_articles_filled'] = rule_articles
                        record['rule_image_filled'] = rule_image
                        record['rule_next_page_filled'] = rule_next
                        record['rule_content_filled'] = rule_content
                        record['template_type'] = template_type
                        record['verify_ok'] = verify_ok
                        record['list_items_count'] = list_count
                        record['notes'].extend(r.get('notes', []))
                        record['notes'].append(
                            f'verify_ok={verify_ok},list_count={list_count}')

                        # 修复计数
                        if sort_url and verify_ok:
                            fixed_count += 1
                        elif sort_url or search_url or rule_articles:
                            partial_count += 1
                        else:
                            failed_count += 1
                        if r.get('error'):
                            record['error'] = r['error']
                    else:
                        record['error'] = r.get('error', 'unknown')
                        failed_count += 1
                except KeyboardInterrupt:
                    log('\n[INTERRUPT] user interrupted, saving...')
                    record['error'] = 'interrupted'
                    records.append(record)
                    raise
                except Exception as e:
                    record['error'] = 'main_err:' + sanitize(str(e))[:80]
                    failed_count += 1

                records.append(record)

                # 增量保存
                if (n + 1) % SAVE_EVERY == 0:
                    save_json(records, total, fixed_count, failed_count, partial_count)
                    log(f'[SAVE] progress: {len(records)}/{total}')

                # 间隔 (避免过于密集)
                time.sleep(0.5 + random.random() * 0.5)

        except KeyboardInterrupt:
            log('\n[INTERRUPT] saving partial results...')
        except Exception as e:
            log(f'[FATAL] {sanitize(str(e))}')
            traceback.print_exc()
        finally:
            save_json(records, len(image_srcs), fixed_count, failed_count, partial_count)
            log(f'[DONE] saved {len(records)} records')
            try:
                context.close()
                browser.close()
            except Exception:
                pass

    # 最终统计
    fully_fixed = 0
    partial_fixed = 0
    still_failed = 0
    tmpl_dist = {}
    for r in records:
        s = bool(r.get('sort_url_filled'))
        se = bool(r.get('search_url_filled'))
        ra = bool(r.get('rule_articles_filled'))
        v = bool(r.get('verify_ok'))
        if (s and v) or (s and se and ra):
            fully_fixed += 1
        elif s or se or ra:
            partial_fixed += 1
        else:
            still_failed += 1
        tt = r.get('template_type', 'unknown')
        tmpl_dist[tt] = tmpl_dist.get(tt, 0) + 1

    log('\n========== 修复统计 ==========')
    log(f'总数: {len(records)}')
    log(f'完全修复(sortUrl验证通过或3字段全填): {fully_fixed}')
    log(f'部分修复(1-2字段填): {partial_fixed}')
    log(f'仍然失败: {still_failed}')
    log(f'模板分布: {tmpl_dist}')
    log(f'输出文件: {OUTPUT_JSON}')
    log('==============================')


if __name__ == '__main__':
    run()
