# -*- coding: utf-8 -*-
"""
V5 视频源深度分析（Phase 2-A）
- 输入：V4源JSON + v5_classification.json(video索引)
- 按"字段完整度+enabled状态"分P0/P1/P2组
- P0：每个源Playwright深度分析（DOM探测+播放器检测+字段补全）
- P1：抽样10个验证
- P2：保留V4
- 输出：v5_video_deep.json（脱敏）

输出安全铁律：
- 不输出源名称/URL/分类名原文
- 用源[idx]替代，URL用[URL]/[DOMAIN]替代
- 异常消息必须脱敏
"""
import json
import os
import re
import sys
import random
import traceback
from datetime import datetime
from urllib.parse import urlparse, urljoin

INPUT_V4 = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v4.json"
INPUT_CLASS = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_classification.json"
OUTPUT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deep.json"
PROGRESS = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deep.progress.json"

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
    document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.advertising,.layermbox,.layui-layer').forEach(e=>e.remove());
    return true;
}
"""

# 单源总耗时上限：3页 × 20s = 60s
PAGE_TIMEOUT = 20000
NETWORK_IDLE_MS = 2000
SAVE_EVERY = 5
P1_SAMPLE = 10


def safe_log(msg):
    """脱敏日志：只输出技术信息"""
    print(msg, flush=True)


def mask_url(url):
    if not url:
        return ""
    try:
        p = urlparse(url)
        return f"[URL:{p.scheme}://{p.netloc}/...]"
    except Exception:
        return "[URL]"


def mask_err(msg, max_len=200):
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
    return [item["source_index"] for item in video_list if "source_index" in item]


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


def is_video_content_rule(src):
    rc = to_str_field(src, "ruleContent")
    rc_low = rc.lower()
    return ("m3u8" in rc_low) or (".mp4" in rc_low) or ("video" in rc_low) or ("hls" in rc_low)


def group_sources(sources, video_indices):
    """按字段完整度+enabled分P0/P1/P2"""
    p0, p1, p2 = [], [], []
    p0_reasons = {}
    for idx in video_indices:
        if idx >= len(sources):
            continue
        src = sources[idx]
        enabled = src.get("enabled", True)
        sort_url = to_str_field(src, "sortUrl")
        next_page = to_str_field(src, "ruleNextPage")
        search_url = to_str_field(src, "searchUrl")
        src_type = str(src.get("type", 0))
        has_video_content = is_video_content_rule(src)

        reasons = []
        is_p0 = False
        if not enabled:
            is_p0 = True
            reasons.append("disabled")
        if not sort_url:
            is_p0 = True
            reasons.append("no_sortUrl")
        if not next_page:
            is_p0 = True
            reasons.append("no_ruleNextPage")
        if not search_url:
            is_p0 = True
            reasons.append("no_searchUrl")
        if src_type == "1" and has_video_content:
            is_p0 = True
            reasons.append("type1_with_video_template")

        if is_p0:
            p0.append(idx)
            p0_reasons[idx] = reasons
        elif src_type == "2":
            p1.append(idx)
        else:
            p2.append(idx)
    return p0, p1, p2, p0_reasons


def try_launch_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ])
    return pw, browser


def new_mobile_context(browser):
    ctx = browser.new_context(
        user_agent=MOBILE_UA,
        viewport={"width": 375, "height": 667},
        locale="zh-CN",
        java_script_enabled=True,
    )
    ctx.add_init_script(STEALTH_JS)
    return ctx


def fetch_page(ctx, url, timeout=PAGE_TIMEOUT):
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


def detect_player(page):
    """检测播放器类型与视频特征"""
    try:
        info = page.evaluate("""() => {
            const v = document.querySelector('video');
            const scripts = Array.from(document.querySelectorAll('script')).map(s=>s.textContent||'').join('\\n');
            const iframes = document.querySelectorAll('iframe');
            let iframeHasPlayer = false;
            for (const f of iframes) {
                const src = (f.getAttribute('src')||'').toLowerCase();
                if (src.indexOf('player')>=0 || src.indexOf('video')>=0 || src.indexOf('play')>=0 || src.indexOf('m3u8')>=0) {
                    iframeHasPlayer = true; break;
                }
            }
            let videoSrc = null;
            if (v) {
                videoSrc = v.src || '';
                if (!videoSrc) {
                    const s = v.querySelector('source');
                    if (s) videoSrc = s.src || '';
                }
            }
            return {
                hasVideoTag: !!v,
                hasVideoSrc: !!videoSrc,
                m3u8InScripts: scripts.indexOf('m3u8') >= 0,
                mp4InScripts: scripts.indexOf('.mp4') >= 0,
                players: {
                    videojs: typeof window.videojs !== 'undefined',
                    jwplayer: typeof window.jwplayer !== 'undefined',
                    dplayer: typeof window.DPlayer !== 'undefined',
                    hls: typeof window.Hls !== 'undefined'
                },
                iframeCount: iframes.length,
                iframeHasPlayer: iframeHasPlayer,
                titleLen: (document.title||'').length
            };
        }""")
        return info
    except Exception:
        return None


def detect_player_type(player_info):
    """根据检测结果判定播放器类型 + 置信度"""
    if not player_info:
        return "none", 0.2
    players = player_info.get("players", {})
    if players.get("videojs"):
        return "videojs", 0.95
    if players.get("jwplayer"):
        return "jwplayer", 0.95
    if players.get("dplayer"):
        return "dplayer", 0.9
    if players.get("hls"):
        return "hls", 0.85
    if player_info.get("hasVideoTag") and player_info.get("hasVideoSrc"):
        return "video_tag", 0.8
    if player_info.get("iframeHasPlayer"):
        return "iframe", 0.75
    if player_info.get("m3u8InScripts") or player_info.get("mp4InScripts"):
        return "script_media", 0.7
    if player_info.get("hasVideoTag"):
        return "video_tag_nosrc", 0.6
    return "none", 0.3


def analyze_list_dom(page):
    """分析列表页DOM结构"""
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


def extract_host(url):
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return ""


def gen_sort_url(host, info):
    cats = info.get("categories", [])
    if not cats:
        return "最新::/\n全部::/"
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


def gen_search_url(host, info):
    if info.get("has_search_form"):
        action = info.get("search_action_pattern") or "/search"
        inp = info.get("search_input_name") or "q"
        if not action.startswith("/"):
            action = "/" + action
        return f"{host}{action}?{inp}={{{{key}}}}&page={{{{page}}}}"
    return f"{host}/search?q={{{{key}}}}&page={{{{page}}}}"


def gen_rule_articles(info):
    found = info.get("list_selectors_found", [])
    if found:
        best = max(found, key=lambda x: x.get("count", 0))
        return best["selector"]
    return ".vod-item"


def gen_rule_next_page(info):
    if info.get("next_page_selector"):
        return info["next_page_selector"]
    return "a.next:has-text('下一页')||a[rel=next]||.pagination a:last-child"


def gen_rule_content_by_player(player_type):
    """根据播放器类型生成 ruleContent"""
    if player_type in ("videojs", "jwplayer", "dplayer", "hls", "script_media", "video_tag", "video_tag_nosrc"):
        return ("@js:var s=result;var m=s.match(/https?:\\/\\/[^\"'\\s]+\\.m3u8[^\"'\\s]*/i)"
                "||s.match(/https?:\\/\\/[^\"'\\s]+\\.mp4[^\"'\\s]*/i);"
                "m?m[0]:''")
    elif player_type == "iframe":
        return "iframe@src||video@src"
    else:
        # 默认：尝试匹配m3u8/mp4
        return ("@js:var s=result;var m=s.match(/https?:\\/\\/[^\"'\\s]+\\.m3u8[^\"'\\s]*/i)"
                "||s.match(/https?:\\/\\/[^\"'\\s]+\\.mp4[^\"'\\s]*/i);"
                "m?m[0]:''")


def verify_sort_url(ctx, host, sort_url):
    if not sort_url:
        return False, 0
    paths = []
    for line in sort_url.split("\n"):
        if "::" in line:
            p = line.split("::", 1)[1].strip()
            if p:
                paths.append(p)
        elif line.strip():
            paths.append(line.strip())
    if not paths:
        return False, 0
    list_candidates = [
        ".movie-item",".video-item",".vod-item",".list-item",".module-item",
        ".stui-vodlist__box",".myui-vodlist__box","article","ul.list li",
        ".search-list li",".module-search-item"
    ]
    best = 0
    for path in paths[:3]:
        full = urljoin(host, path)
        page = None
        try:
            page, _ = fetch_page(ctx, full, timeout=8000)
            for sel in list_candidates:
                try:
                    c = page.evaluate(f"""() => {{ try {{ return document.querySelectorAll({json.dumps(sel)}).length; }} catch(e) {{ return 0; }} }}""")
                    if c and int(c) > best:
                        best = int(c)
                except Exception:
                    pass
            if best > 0:
                return True, best
        except Exception:
            pass
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
    return best > 0, best


def process_one_source(browser, src, gidx, p0_reasons):
    """处理单个P0源"""
    source_url = to_str_field(src, "sourceUrl")
    host = extract_host(source_url)
    result = {
        "source_index": gidx,
        "fix_type": "field_completion",
        "p0_reasons": p0_reasons,
        "detected_player": "none",
        "confidence": 0.0,
        "updated_fields": {},
        "verify_ok": False,
        "list_items_count": 0,
        "pages_visited": 0,
        "error": None,
    }
    if not source_url or not host:
        result["error"] = "no_source_url"
        return result, False
    ctx = None
    page = None
    try:
        ctx = new_mobile_context(browser)
        page, _ = fetch_page(ctx, source_url)
        result["pages_visited"] = 1
        # 检测播放器
        player_info = detect_player(page)
        player_type, conf = detect_player_type(player_info)
        result["detected_player"] = player_type
        result["confidence"] = conf
        # 分析列表DOM
        list_info = analyze_list_dom(page)
        # 如果首页无视频特征，尝试访问详情页
        if player_type in ("none",) and player_info and not (player_info.get("hasVideoTag") or player_info.get("m3u8InScripts") or player_info.get("mp4InScripts") or player_info.get("iframeHasPlayer")):
            try:
                # 点击列表第一个链接进入详情页
                detail_url = page.evaluate("""() => {
                    const sels = ['.movie-item a','.video-item a','.vod-item a','.module-item a','.stui-vodlist__box a','article a','.list-item a','ul.list li a'];
                    for (const sel of sels) {
                        const a = document.querySelector(sel);
                        if (a) {
                            const href = a.getAttribute('href') || '';
                            if (href) return href;
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
                    page, _ = fetch_page(ctx, detail_full)
                    result["pages_visited"] = 2
                    player_info2 = detect_player(page)
                    if player_info2:
                        pt2, conf2 = detect_player_type(player_info2)
                        if pt2 != "none":
                            player_type = pt2
                            conf = conf2
                            result["detected_player"] = player_type
                            result["confidence"] = conf
            except Exception:
                pass
        # 生成字段
        sort_url = gen_sort_url(host, list_info)
        search_url = gen_search_url(host, list_info)
        rule_articles = gen_rule_articles(list_info)
        rule_next_page = gen_rule_next_page(list_info)
        rule_content = gen_rule_content_by_player(player_type)
        # 修复类型
        if "disabled" in p0_reasons:
            result["fix_type"] = "disabled_recovery"
        elif "type1_with_video_template" in p0_reasons:
            result["fix_type"] = "player_detection"
        else:
            result["fix_type"] = "field_completion"
        result["updated_fields"] = {
            "sortUrl": sort_url,
            "searchUrl": search_url,
            "ruleArticles": rule_articles,
            "ruleImage": "img@data-original||img@data-src||img@src",
            "ruleNextPage": rule_next_page,
            "ruleContent": rule_content,
            "enabled": True,
            "type": 2,
        }
        # 关闭当前page
        try:
            page.close()
        except Exception:
            pass
        page = None
        # 验证sortUrl
        ok, count = verify_sort_url(ctx, host, sort_url)
        result["verify_ok"] = bool(ok)
        result["list_items_count"] = int(count)
        fixed = bool(sort_url and rule_articles and ok)
        return result, fixed
    except Exception as e:
        result["error"] = mask_err(e)
        return result, False
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass


def verify_p1_sample(browser, src, gidx):
    """P1抽样验证"""
    source_url = to_str_field(src, "sourceUrl")
    host = extract_host(source_url)
    result = {
        "source_index": gidx,
        "fix_type": "p1_sample_verify",
        "detected_player": "none",
        "confidence": 0.0,
        "updated_fields": {},
        "verify_ok": False,
        "list_items_count": 0,
        "pages_visited": 0,
        "error": None,
    }
    if not source_url or not host:
        result["error"] = "no_source_url"
        return result, False
    ctx = None
    page = None
    try:
        ctx = new_mobile_context(browser)
        page, _ = fetch_page(ctx, source_url)
        result["pages_visited"] = 1
        player_info = detect_player(page)
        player_type, conf = detect_player_type(player_info)
        result["detected_player"] = player_type
        result["confidence"] = conf
        list_info = analyze_list_dom(page)
        result["list_items_count"] = list_info.get("list_items_count", 0)
        # 验证现有sortUrl是否有效
        existing_sort = to_str_field(src, "sortUrl")
        ok, count = verify_sort_url(ctx, host, existing_sort)
        result["verify_ok"] = bool(ok)
        # 如果验证失败，补全字段
        if not ok:
            new_sort = gen_sort_url(host, list_info)
            result["updated_fields"] = {
                "sortUrl": new_sort,
                "searchUrl": gen_search_url(host, list_info),
                "ruleArticles": gen_rule_articles(list_info),
                "ruleImage": "img@data-original||img@data-src||img@src",
                "ruleNextPage": gen_rule_next_page(list_info),
                "ruleContent": gen_rule_content_by_player(player_type),
                "type": 2,
            }
            ok2, count2 = verify_sort_url(ctx, host, new_sort)
            result["verify_ok"] = bool(ok2)
            result["list_items_count"] = int(count2)
            return result, ok2
        return result, True
    except Exception as e:
        result["error"] = mask_err(e)
        return result, False
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass


def load_progress():
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
        json.dump({"records": records}, f, ensure_ascii=False, indent=2)


def main():
    safe_log("[INFO] 加载 V4 源...")
    sources = load_v4_sources()
    safe_log(f"[INFO] V4 源总数: {len(sources)}")
    video_indices = load_video_indices()
    safe_log(f"[INFO] 视频源总数: {len(video_indices)}")
    p0, p1, p2, p0_reasons = group_sources(sources, video_indices)
    safe_log(f"[INFO] 分组: P0={len(p0)}, P1={len(p1)}, P2={len(p2)}")
    # P1抽样
    random.seed(42)
    p1_sample = random.sample(p1, min(P1_SAMPLE, len(p1))) if p1 else []
    safe_log(f"[INFO] P1 抽样: {len(p1_sample)}")

    fixed_records = []
    failed_records = []
    player_dist = {"videojs":0,"jwplayer":0,"dplayer":0,"hls":0,"iframe":0,
                    "script_media":0,"video_tag":0,"video_tag_nosrc":0,"none":0}
    recovered_from_disabled = 0
    p0_analyzed = 0
    p1_sampled = 0
    consecutive_fail = 0

    # 断点续传
    existing = load_progress()
    safe_log(f"[INFO] 断点续传: 已处理 {len(existing)}")

    safe_log("[INFO] 启动 Playwright 浏览器...")
    pw, browser = try_launch_browser()

    try:
        # 处理 P0
        safe_log(f"[INFO] === P0 处理开始（{len(p0)}源）===")
        for i, gidx in enumerate(p0):
            if gidx in existing:
                r = existing[gidx]
                fixed_records.append(r) if r.get("verify_ok") else failed_records.append(r)
                pt = r.get("detected_player","none")
                if pt in player_dist: player_dist[pt] += 1
                if r.get("verify_ok") and "disabled" in (r.get("p0_reasons") or []):
                    recovered_from_disabled += 1
                p0_analyzed += 1
                continue
            safe_log(f"[P0 {i+1}/{len(p0)}] 处理源[{gidx}] 原因={p0_reasons.get(gidx)}")
            try:
                src = sources[gidx]
                result, fixed = process_one_source(browser, src, gidx, p0_reasons.get(gidx, []))
            except Exception as e:
                result = {
                    "source_index": gidx, "fix_type":"field_completion",
                    "detected_player":"none","confidence":0.0,"updated_fields":{},
                    "verify_ok":False,"list_items_count":0,"pages_visited":0,
                    "error": mask_err(e), "p0_reasons": p0_reasons.get(gidx, [])
                }
                fixed = False
            p0_analyzed += 1
            pt = result.get("detected_player","none")
            if pt in player_dist: player_dist[pt] += 1
            if fixed:
                fixed_records.append(result)
                consecutive_fail = 0
                if "disabled" in (result.get("p0_reasons") or []):
                    recovered_from_disabled += 1
                safe_log(f"  [OK] 修复 player={pt} conf={result['confidence']} items={result['list_items_count']}")
            else:
                failed_records.append(result)
                consecutive_fail += 1
                safe_log(f"  [FAIL] player={pt} err={(result.get('error') or '')[:80]}")
            # 增量保存
            if (i+1) % SAVE_EVERY == 0:
                save_progress(fixed_records + failed_records)
            # 失败率>30%停止批次
            total_done = len(fixed_records) + len(failed_records)
            if total_done >= 10 and consecutive_fail >= 5:
                fail_rate = consecutive_fail / total_done
                if fail_rate > 0.3:
                    safe_log(f"[WARN] 失败率>{fail_rate*100:.0f}%，停止P0批次")
                    break
        # 处理 P1 抽样
        safe_log(f"[INFO] === P1 抽样验证开始（{len(p1_sample)}源）===")
        for i, gidx in enumerate(p1_sample):
            if gidx in existing:
                r = existing[gidx]
                if r.get("verify_ok"):
                    fixed_records.append(r)
                else:
                    failed_records.append(r)
                p1_sampled += 1
                continue
            safe_log(f"[P1 {i+1}/{len(p1_sample)}] 抽样源[{gidx}]")
            try:
                src = sources[gidx]
                result, fixed = verify_p1_sample(browser, src, gidx)
            except Exception as e:
                result = {
                    "source_index": gidx, "fix_type":"p1_sample_verify",
                    "detected_player":"none","confidence":0.0,"updated_fields":{},
                    "verify_ok":False,"list_items_count":0,"pages_visited":0,
                    "error": mask_err(e)
                }
                fixed = False
            p1_sampled += 1
            pt = result.get("detected_player","none")
            if pt in player_dist: player_dist[pt] += 1
            if fixed:
                fixed_records.append(result)
                safe_log(f"  [OK] 验证通过 player={pt} items={result['list_items_count']}")
            else:
                failed_records.append(result)
                safe_log(f"  [FAIL] err={(result.get('error') or '')[:80]}")
            if (i+1) % SAVE_EVERY == 0:
                save_progress(fixed_records + failed_records)
    finally:
        try:
            browser.close()
            pw.stop()
        except Exception:
            pass

    # 输出最终结果
    out = {
        "analyzed_at": datetime.now().isoformat(),
        "total_video_sources": len(video_indices),
        "p0_analyzed": p0_analyzed,
        "p1_sampled": p1_sampled,
        "p2_preserved": len(p2),
        "fixed_sources": fixed_records,
        "failed_sources": [{"source_index": r["source_index"], "error": r.get("error","")} for r in failed_records],
        "stats": {
            "fixed_count": len(fixed_records),
            "player_distribution": player_dist,
            "recovered_from_disabled": recovered_from_disabled,
            "failed_count": len(failed_records),
        }
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    save_progress(fixed_records + failed_records)
    safe_log(f"[DONE] P0分析={p0_analyzed} P1抽样={p1_sampled} 修复={len(fixed_records)} 失败={len(failed_records)}")
    safe_log(f"[DIST] {player_dist}")


if __name__ == "__main__":
    main()
