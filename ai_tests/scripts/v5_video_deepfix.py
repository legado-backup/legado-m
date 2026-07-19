# -*- coding: utf-8 -*-
"""
V5 视频源深度分析（Phase 2-A）- v5_video_deepfix
- 输入：V4源JSON(optimized_v2_lite_final_v4.json) + v5_classification.json(by_category.video 118索引)
- 按 source_index 顺序处理，每20个为一批
- 每个源Playwright深度分析：
  1. 访问sourceUrl(mobile_context, 30s超时)
  2. 注入去弹框JS，networkidle，滚动2次
  3. 检测CF盾/登录要求/弹框无法关闭
  4. 检测列表DOM命中的list/title/next选择器
  5. 访问详情页深度检测视频特征(video标签/m3u8/mp4/iframe/player_js)
  6. 基于检测结果设置ruleContent(禁止套模板)
  7. 补全缺失字段(sortUrl/searchUrl/ruleArticles/ruleNextPage等)
- 输出：v5_video_deepfix.json（脱敏，URL→http://[DOMAIN]/path）

输出安全铁律：
- 不输出源名称/URL/分类名原文
- 用源[idx]替代，URL用http://[DOMAIN]/path替代
- 异常消息必须脱敏
"""
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse, urljoin

INPUT_V4 = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v4.json"
INPUT_CLASS = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_classification.json"
OUTPUT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deepfix.json"
PROGRESS = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deepfix.progress.json"

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
}
"""

REMOVE_POPUP_JS = """
() => {
    document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.ad-popup,.vip-modal,.login-modal,.advertising,.layermbox,.layui-layer').forEach(e=>e.remove());
    return true;
}
"""

COUNT_POPUP_JS = """
() => {
    return document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.ad-popup,.vip-modal,.login-modal').length;
}
"""

# 单源总耗时上限：详情页 30s
PAGE_TIMEOUT = 30000
NETWORK_IDLE_MS = 3000
SAVE_EVERY = 5  # 每处理5个源保存一次进度
BATCH_SIZE = 20  # 每批20个源


def safe_log(msg):
    """脱敏日志：只输出技术信息"""
    print(msg, flush=True)


def mask_url(url):
    """URL脱敏：保留路径模式，替换域名为[DOMAIN]"""
    if not url:
        return ""
    try:
        p = urlparse(url)
        path = p.path or "/"
        if p.query:
            path += "?" + p.query
        return f"{p.scheme}://[DOMAIN]{path}"
    except Exception:
        return "[URL]"


def mask_err(msg, max_len=200):
    """异常脱敏"""
    if not msg:
        return ""
    s = str(msg)
    s = re.sub(r'https?://[^\s"\'<>]+', '[URL]', s)
    s = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', s)
    return s[:max_len]


def load_v4_sources():
    with open(INPUT_V4, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("sources", "rssSources", "list", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return next((v for v in data.values() if isinstance(v, list)), [])
    return data


def load_video_indices():
    with open(INPUT_CLASS, "r", encoding="utf-8") as f:
        data = json.load(f)
    video_list = data.get("by_category", {}).get("video", [])
    return sorted([item["source_index"] for item in video_list if "source_index" in item])


def to_str_field(src, key):
    """健壮字段转字符串（处理str/list/dict/None）"""
    v = src.get(key, "")
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "\n".join(str(x) for x in v if x).strip()
    if isinstance(v, dict):
        return "\n".join(f"{k}::{vl}" for k, vl in v.items() if vl).strip()
    return str(v).strip()


def extract_host(url):
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return ""


def try_launch_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-features=IsolateOrigins,site-per-process",
    ])
    return pw, browser


def new_mobile_context(browser):
    ctx = browser.new_context(
        user_agent=MOBILE_UA,
        viewport={"width": 375, "height": 667},
        locale="zh-CN",
        java_script_enabled=True,
        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    )
    ctx.add_init_script(STEALTH_JS)
    return ctx


def fetch_page(ctx, url, timeout=PAGE_TIMEOUT):
    """访问页面，去弹框，滚动2次"""
    page = ctx.new_page()
    try:
        resp = page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_MS)
        except Exception:
            pass
        # 去弹框
        try:
            page.evaluate(REMOVE_POPUP_JS)
        except Exception:
            pass
        # 滚动2次触发懒加载
        for _ in range(2):
            try:
                page.evaluate("() => window.scrollBy(0, 800)")
                page.wait_for_timeout(500)
            except Exception:
                break
        return page, resp
    except Exception as e:
        try:
            page.close()
        except Exception:
            pass
        raise e


def detect_cf_shield(page):
    """检测Cloudflare盾"""
    try:
        title = page.evaluate("() => document.title || ''")
        if not title:
            return False
        title_low = title.lower()
        if "just a moment" in title_low or "cloudflare" in title_low:
            return True
        # 检测 CF challenge 元素
        try:
            cf_elem = page.evaluate("""() => {
                const e = document.querySelector('#cf-challenge-running, .cf-browser-verification, #challenge-form, .cf-turnstile');
                return !!e;
            }""")
            if cf_elem:
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False


def detect_login_required(page):
    """检测登录要求"""
    try:
        info = page.evaluate("""() => {
            const hasPwd = !!document.querySelector('input[type=password]');
            const body = document.body ? document.body.innerText : '';
            const keywords = ['登录', '注册', '请先登录', 'login', 'sign in', 'sign up', '请登录'];
            let matched = [];
            const bodyLow = body.toLowerCase();
            for (const k of keywords) {
                if (bodyLow.indexOf(k.toLowerCase()) >= 0) {
                    matched.push(k);
                    if (matched.length >= 2) break;
                }
            }
            return {hasPwd: hasPwd, matchedKeywords: matched.slice(0,3)};
        }""")
        # 密码框 或 至少2个登录关键词命中
        if info.get("hasPwd"):
            return True
        if len(info.get("matchedKeywords", [])) >= 2:
            return True
        return False
    except Exception:
        return False


def detect_popup_unremovable(page):
    """检测弹框无法关闭：注入去弹框JS后还存在弹框元素"""
    try:
        # 先尝试移除
        try:
            page.evaluate(REMOVE_POPUP_JS)
        except Exception:
            pass
        # 再统计
        count = page.evaluate(COUNT_POPUP_JS)
        # 同时检测是否遮罩了主要内容
        if count and count > 0:
            # 检测是否有可见的遮罩（z-index高 + 占据视口）
            visible = page.evaluate("""() => {
                const sels = '.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.ad-popup,.vip-modal,.login-modal';
                const els = document.querySelectorAll(sels);
                let visibleCount = 0;
                for (const e of els) {
                    const style = window.getComputedStyle(e);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                        const r = e.getBoundingClientRect();
                        if (r.width > 100 && r.height > 100) visibleCount++;
                    }
                }
                return visibleCount;
            }""")
            return visible > 0
        return False
    except Exception:
        return False


def detect_list_dom(page):
    """分析列表页DOM结构，返回命中的list_selectors/title_selectors/next_selectors"""
    info = {
        "categories": [],
        "has_search_form": False,
        "search_action_pattern": None,
        "search_input_name": None,
        "list_selectors_found": [],
        "list_items_count": 0,
        "next_page_selector": None,
    }
    # 分类导航
    try:
        nav_links = page.evaluate("""() => {
            const selectors = ['.nav','nav','.navbar','.menu','.category','.sort','.main-menu','.header-menu','.nav-menu'];
            let links = [];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel + ' a');
                els.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = (a.textContent || '').trim();
                    if (href && text && text.length <= 12) links.push({href:href, text:text});
                });
                if (links.length > 0) break;
            }
            if (links.length === 0) {
                document.querySelectorAll('header a, .header a, .nav a, nav a').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = (a.textContent || '').trim();
                    if (href && text && text.length <= 8) links.push({href:href, text:text});
                });
            }
            return links.slice(0, 30);
        }""")
        seen = set()
        cats = []
        for link in nav_links:
            href = link.get("href", "")
            try:
                p = urlparse(href)
                path = p.path
                if path and path != "/" and path not in seen:
                    seen.add(path)
                    cats.append({"path": path})
            except Exception:
                pass
        info["categories"] = cats[:15]
    except Exception:
        pass
    # 搜索表单
    try:
        form_info = page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            for (const f of forms) {
                const action = f.getAttribute('action') || '';
                if (action.indexOf('search')>=0 || action.indexOf('sou')>=0 || action.indexOf('find')>=0) {
                    const inputs = f.querySelectorAll('input');
                    let inputName = null;
                    for (const inp of inputs) {
                        const n = inp.getAttribute('name') || '';
                        const t = (inp.getAttribute('type')||'').toLowerCase();
                        if (n && t !== 'submit' && t !== 'button' && t !== 'hidden') {
                            inputName = n; break;
                        }
                    }
                    return {found:true, action:action, inputName:inputName};
                }
            }
            return {found:false, action:null, inputName:null};
        }""")
        if form_info.get("found"):
            info["has_search_form"] = True
            action = form_info.get("action") or ""
            try:
                p = urlparse(action)
                info["search_action_pattern"] = p.path or "/search"
            except Exception:
                info["search_action_pattern"] = "/search"
            info["search_input_name"] = form_info.get("inputName") or "q"
    except Exception:
        pass
    # 列表选择器
    list_candidates = [
        ".movie-item",".video-item",".vodListItem",".stui-vodlist__box",
        ".module-items .module-item",".myui-vodlist__box",
        ".tab-content .item",".list-plays li",".playlist li",
        ".vod-item",".list-item",".vod-list li",".video-list li",
        ".module-vodlist .module-item",".myui-vodlist .myui-vodlist__item",
        ".search-list li",".searchbox li",".module-search-item",".search-list-item",
        "article","ul.list li",".thumbnail",".item"
    ]
    for sel in list_candidates:
        try:
            count = page.evaluate(f"""() => {{ try {{ return document.querySelectorAll({json.dumps(sel)}).length; }} catch(e) {{ return 0; }} }}""")
            if count and count > 0:
                info["list_selectors_found"].append({"selector": sel, "count": int(count)})
        except Exception:
            pass
    if info["list_selectors_found"]:
        info["list_items_count"] = max(x["count"] for x in info["list_selectors_found"])
    # 下一页
    next_candidates = [
        "a.next","a[rel=next]",".pagination a:last-child",
        ".page-next",".page-next a",".next a",".pager-next a",
        ".pagebar a:last-child",".pages a:last-child","a:has-text('下一页')","a:has-text('下页')"
    ]
    for sel in next_candidates:
        try:
            count = page.evaluate(f"""() => {{ try {{ return document.querySelectorAll({json.dumps(sel)}).length; }} catch(e) {{ return 0; }} }}""")
            if count and count > 0:
                info["next_page_selector"] = sel
                break
        except Exception:
            pass
    return info


def detect_video_features(page):
    """严格检测视频特征，返回evidence字典"""
    try:
        info = page.evaluate("""() => {
            const videos = Array.from(document.querySelectorAll('video'));
            const iframes = Array.from(document.querySelectorAll('iframe'));
            const scripts = Array.from(document.querySelectorAll('script'));
            const all_text = document.body ? document.body.innerHTML : '';

            return {
                video_tag_count: videos.length,
                video_src: videos.map(v=>v.src||((v.querySelector('source')||{}).src||'')).filter(Boolean),
                video_poster: videos.map(v=>v.poster).filter(Boolean),
                iframe_count: iframes.length,
                iframe_player: iframes.filter(i=>/player|video|m3u8|mp4|play/i.test(i.src||'')).map(i=>i.src||'').filter(Boolean),
                m3u8_in_html: (all_text.match(/https?:\\/\\/[^"' ]+\\.m3u8[^"' ]*/g)||[]).slice(0,3),
                mp4_in_html: (all_text.match(/https?:\\/\\/[^"' ]+\\.mp4[^"' ]*/g)||[]).slice(0,3),
                player_js: {
                    videojs: typeof window.videojs !== 'undefined',
                    jwplayer: typeof window.jwplayer !== 'undefined',
                    dplayer: typeof window.DPlayer !== 'undefined' || typeof window.dp !== 'undefined',
                    ckplayer: typeof window.ckplayer !== 'undefined',
                    flowplayer: typeof window.flowplayer !== 'undefined',
                    hls: typeof window.Hls !== 'undefined'
                },
                play_buttons: document.querySelectorAll('[class*=play],[id*=play],[onclick*=play]').length,
                api_calls: scripts.map(s=>s.textContent||'').filter(t=>/getPlayUrl|player|aaa\\.c|m3u8/i.test(t)).length
            };
        }""")
        return info
    except Exception:
        return None


def classify_result_type(evidence, cf_shield, login_required, popup_unremovable, network_error):
    """根据证据判定result_type"""
    if network_error:
        return "network_error"
    if cf_shield:
        return "cf_shield"
    if login_required:
        return "login_required"
    if popup_unremovable:
        return "popup_unremovable"
    if not evidence:
        return "no_video_evidence"
    # 优先级：video标签+src > m3u8 > iframe_player > mp4 > player_js > 无证据
    if evidence.get("video_tag_count", 0) > 0 and evidence.get("video_src"):
        return "video_found"
    if evidence.get("m3u8_in_html"):
        return "m3u8_found"
    if evidence.get("iframe_player"):
        return "iframe_player"
    # player_js 命中
    pj = evidence.get("player_js", {}) or {}
    if any(pj.values()):
        return "video_found"
    # mp4
    if evidence.get("mp4_in_html"):
        return "video_found"
    if evidence.get("video_tag_count", 0) > 0:
        return "video_found"
    return "no_video_evidence"


def gen_rule_content_by_evidence(result_type, evidence):
    """基于实际检测到的视频特征生成ruleContent，禁止套模板"""
    if result_type == "video_found":
        # 检测到 <video> 标签 + src
        if evidence and evidence.get("video_tag_count", 0) > 0 and evidence.get("video_src"):
            return "@js:var v=doc.selectFirst('video');result=v?(v.attr('src')||(v.selectFirst('source')?v.selectFirst('source').attr('src'):'')):''"
        # player_js 命中
        pj = (evidence or {}).get("player_js", {}) or {}
        if pj.get("videojs"):
            return "@js:try{result=videojs('video').src()||''}catch(e){result=''}"
        if pj.get("jwplayer"):
            return "@js:try{result=jwplayer().getPlaylistItem().file||''}catch(e){result=''}"
        if pj.get("dplayer"):
            return "@js:var m=String(document.body.innerHTML).match(/https?:\\/\\/[^\"' ]+\\.(m3u8|mp4)[^\"' ]*/);result=m?m[0]:''"
        if pj.get("hls"):
            return "@js:var m=String(document.body.innerHTML).match(/https?:\\/\\/[^\"' ]+\\.m3u8[^\"' ]*/);result=m?m[0]:''"
        if pj.get("ckplayer"):
            return "@js:var m=String(document.body.innerHTML).match(/https?:\\/\\/[^\"' ]+\\.(m3u8|mp4)[^\"' ]*/);result=m?m[0]:''"
        if pj.get("flowplayer"):
            return "@js:var m=String(document.body.innerHTML).match(/https?:\\/\\/[^\"' ]+\\.(m3u8|mp4)[^\"' ]*/);result=m?m[0]:''"
        # mp4
        if evidence and evidence.get("mp4_in_html"):
            return "@js:var m=String(doc.html()).match(/https?:\\/\\/[^\"' ]+\\.mp4[^\"' ]*/);result=m?m[0]:''"
        # 兜底：video标签
        if evidence and evidence.get("video_tag_count", 0) > 0:
            return "@js:var v=doc.selectFirst('video');result=v?(v.attr('src')||(v.selectFirst('source')?v.selectFirst('source').attr('src'):'')):''"
        # m3u8兜底
        return "@js:var m=String(doc.html()).match(/https?:\\/\\/[^\"' ]+\\.m3u8[^\"' ]*/);result=m?m[0]:''"
    if result_type == "m3u8_found":
        return "@js:var m=String(doc.html()).match(/https?:\\/\\/[^\"' ]+\\.m3u8[^\"' ]*/);result=m?m[0]:''"
    if result_type == "iframe_player":
        return "@js:var f=doc.selectFirst('iframe[class*=player]')||doc.selectFirst('iframe');result=f?f.attr('src')||'':''"
    # no_video_evidence / cf_shield / login_required / popup_unremovable / network_error
    # 保留原ruleContent（在调用方处理）
    return None


def gen_sort_url(host, info, original_sort_url):
    """补全sortUrl：如果原sortUrl存在且非空，保留；否则基于实际DOM命中生成"""
    if original_sort_url and original_sort_url.strip():
        return original_sort_url
    cats = info.get("categories", [])
    if not cats:
        # 用sourceUrl作为fallback
        return f"最新::/"
    lines = []
    for i, cat in enumerate(cats[:10]):
        path = cat.get("path", "/")
        if path.startswith("http"):
            try:
                p = urlparse(path)
                path = p.path
            except Exception:
                path = "/"
        if not path.startswith("/"):
            path = "/" + path
        name = "最新" if i == 0 else f"分类{i+1}"
        lines.append(f"{name}::{path}")
    if not lines:
        lines.append("最新::/")
    return "\n".join(lines)


def gen_search_url(host, info, original_search_url):
    if original_search_url and original_search_url.strip():
        return original_search_url
    if info.get("has_search_form"):
        action = info.get("search_action_pattern") or "/search"
        inp = info.get("search_input_name") or "q"
        if not action.startswith("/"):
            action = "/" + action
        return f"{host}{action}?{inp}={{{{key}}}}&page={{{{page}}}}"
    return f"{host}/search?q={{{{key}}}}&page={{{{page}}}}"


def gen_rule_articles(info, original_rule_articles):
    if original_rule_articles and original_rule_articles.strip():
        return original_rule_articles
    found = info.get("list_selectors_found", [])
    if found:
        best = max(found, key=lambda x: x.get("count", 0))
        return best["selector"]
    return ".vod-item"


def gen_rule_next_page(info, original_rule_next_page):
    if original_rule_next_page and original_rule_next_page.strip():
        return original_rule_next_page
    if info.get("next_page_selector"):
        return info["next_page_selector"]
    return "a.next:has-text('下一页')||a[rel=next]||.pagination a:last-child"


def gen_rule_image(original_rule_image):
    if original_rule_image and original_rule_image.strip():
        return original_rule_image
    return "img@data-original||img@data-src||img@src"


def mask_evidence_urls(evidence):
    """脱敏evidence中的所有URL"""
    if not evidence:
        return evidence
    e = dict(evidence)
    e["video_src"] = [mask_url(u) for u in (e.get("video_src") or [])]
    e["video_poster"] = [mask_url(u) for u in (e.get("video_poster") or [])]
    e["iframe_player"] = [mask_url(u) for u in (e.get("iframe_player") or [])]
    e["m3u8_in_html"] = [mask_url(u) for u in (e.get("m3u8_in_html") or [])]
    e["mp4_in_html"] = [mask_url(u) for u in (e.get("mp4_in_html") or [])]
    return e


def process_one_source(browser, src, gidx):
    """处理单个视频源：返回 (result_dict, success_bool)"""
    source_url = to_str_field(src, "sourceUrl")
    host = extract_host(source_url)
    original_sort_url = to_str_field(src, "sortUrl")
    original_search_url = to_str_field(src, "searchUrl")
    original_rule_articles = to_str_field(src, "ruleArticles")
    original_rule_next_page = to_str_field(src, "ruleNextPage")
    original_rule_image = to_str_field(src, "ruleImage")
    original_rule_content = to_str_field(src, "ruleContent")

    result = {
        "source_index": gidx,
        "sourceUrl_pattern": mask_url(source_url),
        "result_type": "no_video_evidence",
        "fields_updated": [],
        "new_fields": {},
        "evidence": {
            "video_tag_count": 0,
            "video_src": [],
            "video_poster": [],
            "iframe_count": 0,
            "iframe_player": [],
            "m3u8_in_html": [],
            "mp4_in_html": [],
            "player_js": {},
            "play_buttons": 0,
            "api_calls": 0,
        },
        "difficulties": [],
        "pages_visited": 0,
        "error": None,
    }

    if not source_url or not host:
        result["result_type"] = "network_error"
        result["error"] = "no_source_url"
        result["difficulties"].append("no_source_url")
        return result, False

    ctx = None
    page = None
    network_error = False
    try:
        ctx = new_mobile_context(browser)
        # 步骤2: 访问sourceUrl
        try:
            page, _ = fetch_page(ctx, source_url)
            result["pages_visited"] = 1
        except Exception as e:
            network_error = True
            result["result_type"] = "network_error"
            result["error"] = mask_err(e)
            result["difficulties"].append("network_error")
            return result, False

        # 步骤3+7: 检测CF盾/登录/弹框
        cf_shield = detect_cf_shield(page)
        if cf_shield:
            result["difficulties"].append("cf_shield")
            result["result_type"] = "cf_shield"
            # 关闭并返回
            try: page.close()
            except: pass
            page = None
            return result, False

        login_required = detect_login_required(page)
        if login_required:
            result["difficulties"].append("login_required")

        popup_unremovable = detect_popup_unremovable(page)
        if popup_unremovable:
            result["difficulties"].append("popup_unremovable")

        # 步骤3: 检测首页/列表页结构
        list_info = detect_list_dom(page)

        # 步骤4: 访问详情页深度分析视频特征
        evidence = None
        try:
            # 从列表页提取第1个详情页链接
            detail_url = page.evaluate("""() => {
                const sels = ['.movie-item a','.video-item a','.vod-item a','.module-item a','.stui-vodlist__box a','article a','.list-item a','ul.list li a','.vodListItem a','.myui-vodlist__box a','.search-list li a','.search-list-item a','.module-search-item a','.item a'];
                for (const sel of sels) {
                    const a = document.querySelector(sel);
                    if (a) {
                        const href = a.getAttribute('href') || '';
                        if (href && !href.startsWith('javascript:') && !href.startsWith('#')) return href;
                    }
                }
                // 兜底：任何指向详情的链接
                const all = document.querySelectorAll('a[href]');
                for (const a of all) {
                    const href = a.getAttribute('href') || '';
                    if (href && href.length > 5 && !href.startsWith('javascript:') && !href.startsWith('#') && !href.startsWith('http://') && !href.startsWith('https://')) {
                        return href;
                    }
                }
                return null;
            }""")
            if detail_url:
                detail_full = urljoin(source_url, detail_url)
                try:
                    page.close()
                except Exception:
                    pass
                page = None
                page, _ = fetch_page(ctx, detail_full, timeout=PAGE_TIMEOUT)
                result["pages_visited"] = 2
                # 等待 video 标签出现（5s）或 networkidle
                try:
                    page.wait_for_selector("video", timeout=5000)
                except Exception:
                    pass
                # 注入去弹框JS
                try:
                    page.evaluate(REMOVE_POPUP_JS)
                except Exception:
                    pass
                # 严格检测视频特征
                evidence = detect_video_features(page)
            else:
                # 首页就是详情页（罕见）或在首页检测
                evidence = detect_video_features(page)
        except Exception as e:
            result["error"] = mask_err(e)

        # 步骤5: 基于检测结果设置ruleContent
        result_type = classify_result_type(evidence, cf_shield, login_required, popup_unremovable, network_error)
        result["result_type"] = result_type
        result["evidence"] = mask_evidence_urls(evidence) if evidence else result["evidence"]

        # 生成新字段
        new_sort_url = gen_sort_url(host, list_info, original_sort_url)
        new_search_url = gen_search_url(host, list_info, original_search_url)
        new_rule_articles = gen_rule_articles(list_info, original_rule_articles)
        new_rule_next_page = gen_rule_next_page(list_info, original_rule_next_page)
        new_rule_image = gen_rule_image(original_rule_image)
        new_rule_content = gen_rule_content_by_evidence(result_type, evidence)
        # 如果生成失败（如cf/login/popup/network_error），保留原ruleContent
        if not new_rule_content:
            new_rule_content = original_rule_content

        # 记录字段变更
        fields_updated = []
        new_fields = {}
        if new_sort_url != original_sort_url:
            fields_updated.append("sortUrl")
            new_fields["sortUrl"] = new_sort_url
        if new_search_url != original_search_url:
            fields_updated.append("searchUrl")
            new_fields["searchUrl"] = new_search_url
        if new_rule_articles != original_rule_articles:
            fields_updated.append("ruleArticles")
            new_fields["ruleArticles"] = new_rule_articles
        if new_rule_next_page != original_rule_next_page:
            fields_updated.append("ruleNextPage")
            new_fields["ruleNextPage"] = new_rule_next_page
        if new_rule_image != original_rule_image:
            fields_updated.append("ruleImage")
            new_fields["ruleImage"] = new_rule_image
        if new_rule_content != original_rule_content:
            fields_updated.append("ruleContent")
            new_fields["ruleContent"] = new_rule_content
        # 始终输出新字段全集（任务要求 new_fields 包含所有字段）
        new_fields_full = {
            "ruleContent": new_rule_content,
            "ruleArticles": new_rule_articles,
            "sortUrl": new_sort_url,
            "searchUrl": new_search_url,
            "ruleNextPage": new_rule_next_page,
            "ruleImage": new_rule_image,
        }
        result["fields_updated"] = fields_updated
        result["new_fields"] = new_fields_full

        # 成功条件：检测到视频特征（result_type为正面类型）
        success_types = {"video_found", "m3u8_found", "iframe_player"}
        success = result_type in success_types
        return result, success

    except Exception as e:
        result["result_type"] = "network_error"
        result["error"] = mask_err(e)
        result["difficulties"].append("exception")
        return result, False
    finally:
        if page:
            try: page.close()
            except: pass
        if ctx:
            try: ctx.close()
            except: pass


def load_progress():
    """断点续传：加载已处理的源index"""
    if not os.path.exists(PROGRESS):
        return {}
    try:
        with open(PROGRESS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {r["source_index"]: r for r in data.get("records", [])}
    except Exception:
        return {}


def save_progress(records):
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump({"records": records, "saved_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def main():
    safe_log("[INFO] 加载 V4 源...")
    sources = load_v4_sources()
    safe_log(f"[INFO] V4 源总数: {len(sources)}")
    video_indices = load_video_indices()
    safe_log(f"[INFO] 视频源总数: {len(video_indices)}")
    safe_log(f"[INFO] 视频源索引(前10): {video_indices[:10]}")
    safe_log(f"[INFO] 视频源索引(后10): {video_indices[-10:]}")

    # 断点续传
    existing = load_progress()
    safe_log(f"[INFO] 断点续传: 已处理 {len(existing)}")

    fixes_records = []
    failed_records = []
    by_result = {
        "video_found": 0,
        "m3u8_found": 0,
        "iframe_player": 0,
        "no_video_evidence": 0,
        "cf_shield": 0,
        "login_required": 0,
        "popup_unremovable": 0,
        "network_error": 0,
    }

    safe_log("[INFO] 启动 Playwright 浏览器...")
    pw, browser = try_launch_browser()

    batch_num = 0
    processed_in_batch = 0
    total_processed = 0
    try:
        for i, gidx in enumerate(video_indices):
            # 断点续传
            if gidx in existing:
                r = existing[gidx]
                rt = r.get("result_type", "no_video_evidence")
                if rt in by_result:
                    by_result[rt] += 1
                else:
                    by_result["no_video_evidence"] += 1
                if r.get("result_type") in ("video_found", "m3u8_found", "iframe_player"):
                    fixes_records.append(r)
                else:
                    failed_records.append(r)
                total_processed += 1
                continue

            # 批次提示
            if processed_in_batch == 0:
                batch_num += 1
                start_idx = i
                end_idx = min(i + BATCH_SIZE - 1, len(video_indices) - 1)
                safe_log(f"[INFO] === 批次{batch_num} 处理源[{gidx}..源[{video_indices[end_idx]}]] ({min(BATCH_SIZE, len(video_indices)-i)}个) ===")

            safe_log(f"[{i+1}/{len(video_indices)}] 处理源[{gidx}]...")
            try:
                src = sources[gidx]
                result, success = process_one_source(browser, src, gidx)
            except Exception as e:
                result = {
                    "source_index": gidx,
                    "sourceUrl_pattern": "",
                    "result_type": "network_error",
                    "fields_updated": [],
                    "new_fields": {},
                    "evidence": {},
                    "difficulties": ["exception"],
                    "pages_visited": 0,
                    "error": mask_err(e),
                }
                success = False

            rt = result.get("result_type", "no_video_evidence")
            if rt in by_result:
                by_result[rt] += 1
            else:
                by_result["no_video_evidence"] += 1

            if success:
                fixes_records.append(result)
                safe_log(f"  [OK] result_type={rt} pages={result['pages_visited']} fields_updated={result['fields_updated']}")
            else:
                failed_records.append(result)
                err = (result.get("error") or "")[:80]
                safe_log(f"  [FAIL] result_type={rt} difficulties={result.get('difficulties')} err={err}")

            total_processed += 1
            processed_in_batch += 1

            # 增量保存
            if (i+1) % SAVE_EVERY == 0:
                save_progress(fixes_records + failed_records)
                safe_log(f"  [PROGRESS] 已保存 {total_processed}/{len(video_indices)}")

            # 批次结束提示
            if processed_in_batch >= BATCH_SIZE:
                safe_log(f"[INFO] 批次{batch_num} 完成, 已处理 {total_processed}/{len(video_indices)}, 成功 {len(fixes_records)}, 失败 {len(failed_records)}")
                processed_in_batch = 0
                # 批次间稍作休息
                time.sleep(1)

    finally:
        try:
            browser.close()
            pw.stop()
        except Exception:
            pass

    # 输出最终结果
    success_count = len(fixes_records)
    failed_count = len(failed_records)
    out = {
        "analyzed_at": datetime.now().isoformat(),
        "total_input": len(video_indices),
        "success_count": success_count,
        "failed_count": failed_count,
        "by_result": by_result,
        "fixes": fixes_records,
        "failed": failed_records,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    save_progress(fixes_records + failed_records)
    safe_log(f"[DONE] 处理={total_processed} 成功={success_count} 失败={failed_count}")
    safe_log(f"[DIST] {by_result}")


if __name__ == "__main__":
    main()
