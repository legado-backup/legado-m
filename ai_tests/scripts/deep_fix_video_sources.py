# -*- coding: utf-8 -*-
"""
深度优化视频源(type=2)中无sortUrl的源。
- 提取 type=2 且 sortUrl 为空的源
- 用 Playwright 逐源分析 DOM
- 识别 V1/V2/V3 模板，套用生成 sortUrl/searchUrl/ruleArticles/ruleImage/ruleNextPage/ruleContent
- 验证生成的 sortUrl
- 输出脱敏结果 JSON

输出安全铁律：
- 脚本输出禁止包含源名称/URL/分类名原文
- 用源[idx]替代真实名称，URL用[URL]替代，域名用站点A/B/C替代
- 异常消息必须脱敏
"""

import json
import os
import re
import sys
import traceback
from urllib.parse import urlparse, urljoin

INPUT_JSON = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v3.json"
OUTPUT_JSON = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\video_source_deep_fix.json"
PROGRESS_JSON = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\video_source_deep_fix.progress.json"

SAVE_EVERY = 5
TIMEOUT_MS = 15000

# stealth.js 简版
STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
    window.chrome = { runtime: {} };
}
"""


def safe_log(msg):
    """脱敏日志输出"""
    # 不输出任何URL/域名，只输出技术信息
    print(msg, flush=True)


def mask_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return f"[URL:{parsed.scheme}://{parsed.netloc}/...]"
    except Exception:
        return "[URL]"


def mask_text(text, max_len=20):
    if not text:
        return ""
    t = str(text).strip()
    if len(t) > max_len:
        return t[:max_len] + "..."
    return t


def load_sources():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 数据可能是 list 或 dict 含 list
    if isinstance(data, dict):
        # 常见 key: sources / rssSources / list
        for key in ("sources", "rssSources", "list", "data"):
            if key in data and isinstance(data[key], list):
                sources = data[key]
                break
        else:
            # 找第一个 list
            sources = next((v for v in data.values() if isinstance(v, list)), [])
    else:
        sources = data

    # 筛选 type=2 且 sortUrl 为空
    targets = []
    for idx, src in enumerate(sources):
        try:
            src_type = src.get("type", 0)
            sort_url = src.get("sortUrl", "") or ""
            # type 可能是 int 或 str
            if str(src_type) == "2" and not sort_url.strip():
                targets.append({"global_idx": idx, "source": src})
        except Exception:
            continue

    return sources, targets


def try_launch_browser():
    """启动 Playwright 浏览器"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ])
    return pw, browser


def new_context(browser):
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 900},
        java_script_enabled=True,
    )
    ctx.add_init_script(STEALTH_JS)
    return ctx


def fetch_page(ctx, url, timeout=10000):
    """访问页面，返回 page 对象。超时缩短到10秒防卡死。"""
    page = ctx.new_page()
    try:
        resp = page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        # 等渲染（缩短超时防卡死）
        try:
            page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            pass
        return page, resp
    except Exception as e:
        try:
            page.close()
        except Exception:
            pass
        raise e


def load_progress():
    """断点续传：读取已处理的idx"""
    if not os.path.exists(PROGRESS_JSON):
        return {}
    try:
        with open(PROGRESS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {r["idx"]: r for r in data.get("records", [])}
    except Exception:
        return {}


def extract_host(url):
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return ""


def analyze_dom(page, host):
    """分析 DOM，返回结构化信息（脱敏）"""
    info = {
        "title_len": 0,
        "has_search_form": False,
        "search_action_pattern": None,  # 模式化路径
        "search_input_name": None,
        "nav_links_count": 0,
        "categories": [],  # 用 编号 替代名称，仅保留路径模式
        "list_selectors_found": [],  # 命中的列表选择器
        "list_items_count": 0,
        "next_page_selector": None,
        "has_video_tag": False,
        "has_iframe_player": False,
        "iframe_player_pattern": None,
        "has_m3u8_mp4_in_scripts": False,
        "is_json_api": False,
        "json_keys": [],
    }

    try:
        title = page.title()
        info["title_len"] = len(title) if title else 0
    except Exception:
        pass

    # 检测 JSON API 响应
    try:
        content = page.content()
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        # JSON API: body 以 { 或 [ 开头
        stripped = body_text.strip()[:5]
        if stripped.startswith("{") or stripped.startswith("["):
            info["is_json_api"] = True
            try:
                j = json.loads(body_text)
                if isinstance(j, dict):
                    info["json_keys"] = list(j.keys())[:10]
                elif isinstance(j, list) and len(j) > 0 and isinstance(j[0], dict):
                    info["json_keys"] = list(j[0].keys())[:10]
            except Exception:
                pass
    except Exception:
        pass

    # 检测 script 中的 m3u8/mp4
    try:
        has_media = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const t = s.textContent || '';
                if (t.indexOf('m3u8') >= 0 || t.indexOf('.mp4') >= 0) return true;
            }
            return false;
        }""")
        info["has_m3u8_mp4_in_scripts"] = bool(has_media)
    except Exception:
        pass

    # 检测 video 标签
    try:
        info["has_video_tag"] = page.evaluate("() => document.querySelectorAll('video').length > 0")
    except Exception:
        pass

    # 检测 iframe 播放器
    try:
        iframe_info = page.evaluate("""() => {
            const iframes = document.querySelectorAll('iframe');
            for (const f of iframes) {
                const src = f.getAttribute('src') || '';
                if (src.indexOf('player') >= 0 || src.indexOf('video') >= 0 || src.indexOf('play') >= 0) {
                    return {found: true, pattern: src.indexOf('player') >= 0 ? 'player' : (src.indexOf('video') >= 0 ? 'video' : 'play')};
                }
            }
            return {found: false, pattern: null};
        }""")
        info["has_iframe_player"] = bool(iframe_info.get("found"))
        info["iframe_player_pattern"] = iframe_info.get("pattern")
    except Exception:
        pass

    # 搜索表单
    try:
        form_info = page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            for (const f of forms) {
                const action = f.getAttribute('action') || '';
                if (action.indexOf('search') >= 0 || action.indexOf('sou') >= 0 || action.indexOf('find') >= 0) {
                    const inputs = f.querySelectorAll('input');
                    let inputName = null;
                    for (const inp of inputs) {
                        const n = inp.getAttribute('name') || '';
                        const t = (inp.getAttribute('type') || '').toLowerCase();
                        if (n && t !== 'submit' && t !== 'button' && t !== 'hidden') {
                            inputName = n;
                            break;
                        }
                    }
                    return {found: true, action: action, inputName: inputName};
                }
            }
            return {found: false, action: null, inputName: null};
        }""")
        if form_info.get("found"):
            info["has_search_form"] = True
            # 模式化 action
            action = form_info.get("action") or ""
            if action:
                # 只保留路径模式
                try:
                    parsed = urlparse(action)
                    info["search_action_pattern"] = parsed.path or "/"
                except Exception:
                    info["search_action_pattern"] = "/search"
            info["search_input_name"] = form_info.get("inputName")
    except Exception:
        pass

    # 导航/分类链接
    try:
        nav_info = page.evaluate("""() => {
            const selectors = ['.nav', '.navbar', '.menu', '.category', '.sort', 'nav', '.nav-menu', '.main-menu', '.header-menu'];
            let links = [];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel + ' a');
                els.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = (a.textContent || '').trim();
                    if (href && text && text.length <= 10) {
                        links.push({href: href, text: text});
                    }
                });
                if (links.length > 0) break;
            }
            // 兜底：所有顶部导航
            if (links.length === 0) {
                const allLinks = document.querySelectorAll('header a, .header a, .nav a, nav a');
                allLinks.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = (a.textContent || '').trim();
                    if (href && text && text.length <= 8) {
                        links.push({href: href, text: text});
                    }
                });
            }
            return links.slice(0, 30);
        }""")
        info["nav_links_count"] = len(nav_info)
        # 脱敏：只保留路径模式，不保留分类名
        cats = []
        seen_paths = set()
        for link in nav_info:
            href = link.get("href", "")
            try:
                parsed = urlparse(href)
                path = parsed.path
                if path and path not in seen_paths and path != "/":
                    seen_paths.add(path)
                    cats.append({"path": path})
            except Exception:
                pass
        info["categories"] = cats[:15]
    except Exception:
        pass

    # 列表选择器探测
    list_candidates = [
        ".vod-item", ".video-item", ".movie-item", ".list-item",
        ".vod-list", ".video-list", ".movie-list", ".play-list",
        ".episode-list", ".stui-vodlist__item", ".stui-vodlist__box",
        ".module-items .module-item", ".module-vodlist .module-item",
        ".myui-vodlist .myui-vodlist__item", ".col-pd .list-item",
        "ul.vod-list li", "ul.video-list li", "ul.movielist li",
        ".search-list li", ".searchbox li", ".stui-pannel__item",
        ".module-search-item", ".search-list-item",
        "article", "ul.list li", ".thumbnail", ".item",
    ]
    for sel in list_candidates:
        try:
            count = page.evaluate(f"""() => {{
                try {{
                    return document.querySelectorAll({json.dumps(sel)}).length;
                }} catch(e) {{ return 0; }}
            }}""")
            if count and count > 0:
                info["list_selectors_found"].append({"selector": sel, "count": int(count)})
        except Exception:
            pass

    # 取最大列表项数量
    if info["list_selectors_found"]:
        info["list_items_count"] = max(x["count"] for x in info["list_selectors_found"])

    # 下一页选择器
    next_page_candidates = [
        "a.next", "a[rel=next]", ".pagination a:last-child",
        ".page-next a", ".next a", "a:has-text('下一页')", "a:has-text('下页')",
        ".pager-next a", ".pagebar a:last-child", ".pages a:last-child",
    ]
    for sel in next_page_candidates:
        try:
            count = page.evaluate(f"""() => {{
                try {{
                    return document.querySelectorAll({json.dumps(sel)}).length;
                }} catch(e) {{ return 0; }}
            }}""")
            if count and count > 0:
                info["next_page_selector"] = sel
                break
        except Exception:
            pass

    return info


def detect_template_type(info, source_url):
    """识别 V1/V2/V3 模板"""
    # V2: JSON API
    if info.get("is_json_api"):
        return "V2"
    # V1: script 含 m3u8/mp4
    if info.get("has_m3u8_mp4_in_scripts"):
        return "V1"
    # V3: iframe 嵌套播放器
    if info.get("has_iframe_player"):
        return "V3"
    # 默认 V1
    return "V1"


def gen_sort_url(host, info):
    """生成 sortUrl: 分类名::相对路径\n..."""
    cats = info.get("categories", [])
    if not cats:
        # 默认首页
        return f"最新::/\n全部::/"
    lines = []
    # 第一个用"最新"
    for i, cat in enumerate(cats[:10]):
        path = cat.get("path", "/")
        # 确保相对路径
        if path.startswith("http"):
            try:
                parsed = urlparse(path)
                path = parsed.path
            except Exception:
                path = "/"
        if not path.startswith("/"):
            path = "/" + path
        name = "最新" if i == 0 else f"分类{i+1}"
        lines.append(f"{name}::{path}")
    if not lines:
        lines.append("最新::/")
    return "\n".join(lines)


def gen_search_url(host, info, source_url):
    """生成 searchUrl"""
    # 优先用搜索表单
    if info.get("has_search_form"):
        action_path = info.get("search_action_pattern") or "/search"
        input_name = info.get("search_input_name") or "q"
        # 确保 action 是路径
        if not action_path.startswith("/"):
            action_path = "/" + action_path
        # 判断是否有 page 参数（多数视频站用 page/p 等参数）
        return f"{host}{action_path}?{input_name}={{{{key}}}}&page={{{{page}}}}"
    # 兜底：常用搜索路径
    # 检测常见 CMS
    return f"{host}/search?q={{{{key}}}}&page={{{{page}}}}"


def gen_rule_articles(info):
    """生成 ruleArticles"""
    # 选择 count 最大的列表选择器
    found = info.get("list_selectors_found", [])
    if found:
        # 选 count 最大的
        best = max(found, key=lambda x: x.get("count", 0))
        return best["selector"]
    # 默认
    return ".vod-item"


def gen_rule_image(info):
    """生成 ruleImage"""
    # 视频站图片常在 img@data-original / img@data-src / img@src
    return "img@data-original||img@data-src||img@src"


def gen_rule_next_page(info):
    """生成 ruleNextPage"""
    if info.get("next_page_selector"):
        return info["next_page_selector"]
    return "a.next:has-text('下一页')||a[rel=next]||.pagination a:last-child"


def gen_rule_content(template_type):
    """生成 ruleContent（视频内容规则）"""
    if template_type == "V1":
        # V1: script 含 m3u8/mp4，用 JS 提取
        return ("@js:var s=result;var m=s.match(/https?:\\/\\/[^\"'\\s]+\\.m3u8[^\"'\\s]*/i)"
                "||s.match(/https?:\\/\\/[^\"'\\s]+\\.mp4[^\"'\\s]*/i);"
                "m?m[0]:''")
    elif template_type == "V2":
        # V2: JSON API
        return ("@js:var j=JSON.parse(result);var url='';"
                "if(j.url){url=j.url}else if(j.data&&j.data.url){url=j.data.url}"
                "else if(j.list&&j.list[0]&&j.list[0].url){url=j.list[0].url};url")
    else:
        # V3: iframe 嵌套
        return "iframe@src||video@src"


def verify_sort_url(ctx, host, sort_url):
    """验证 sortUrl：遍历所有分类路径，任一有列表项即成功"""
    if not sort_url:
        return False, 0
    # 收集所有分类路径
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
        ".vod-item", ".video-item", ".movie-item", ".list-item",
        ".vod-list li", ".video-list li", ".module-item",
        "article", "ul.list li", ".search-list li",
        ".stui-vodlist__item", ".myui-vodlist__item", ".module-search-item",
    ]
    best_count = 0
    # 最多尝试前3个路径
    for path in paths[:3]:
        full_url = urljoin(host, path)
        page = None
        try:
            page, resp = fetch_page(ctx, full_url, timeout=8000)
            for sel in list_candidates:
                try:
                    count = page.evaluate(f"""() => {{
                        try {{ return document.querySelectorAll({json.dumps(sel)}).length; }}
                        catch(e) {{ return 0; }}
                    }}""")
                    if count and int(count) > best_count:
                        best_count = int(count)
                except Exception:
                    pass
            if best_count > 0:
                # 找到列表项，成功
                return True, best_count
        except Exception:
            pass
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
    return best_count > 0, best_count


def save_progress(records, total, fixed, still_failed):
    """增量保存"""
    out = {
        "total": total,
        "fixed": fixed,
        "still_failed": still_failed,
        "records": records,
    }
    with open(PROGRESS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def process_one_source(browser, rec):
    """处理单个源"""
    src = rec["source"]
    gidx = rec["global_idx"]
    source_url = src.get("sourceUrl", "") or ""
    host = extract_host(source_url)

    result = {
        "idx": gidx,
        "template_type": None,
        "sort_url_filled": "",
        "search_url_filled": "",
        "rule_articles_filled": "",
        "rule_image_filled": "",
        "rule_next_page_filled": "",
        "rule_content_filled": "",
        "verify_ok": False,
        "list_items_count": 0,
        "error": None,
    }

    if not source_url or not host:
        result["error"] = "no_source_url"
        return result, False

    ctx = None
    page = None
    try:
        ctx = new_context(browser)
        page, resp = fetch_page(ctx, source_url, timeout=10000)
        # 分析 DOM
        info = analyze_dom(page, host)
        # 识别模板
        template_type = detect_template_type(info, source_url)
        result["template_type"] = template_type

        # 生成字段
        sort_url = gen_sort_url(host, info)
        search_url = gen_search_url(host, info, source_url)
        rule_articles = gen_rule_articles(info)
        rule_image = gen_rule_image(info)
        rule_next_page = gen_rule_next_page(info)
        rule_content = gen_rule_content(template_type)

        result["sort_url_filled"] = sort_url
        result["search_url_filled"] = search_url
        result["rule_articles_filled"] = rule_articles
        result["rule_image_filled"] = rule_image
        result["rule_next_page_filled"] = rule_next_page
        result["rule_content_filled"] = rule_content

        # 关闭当前 page
        try:
            page.close()
        except Exception:
            pass
        page = None

        # 验证
        ok, count = verify_sort_url(ctx, host, sort_url)
        result["verify_ok"] = bool(ok)
        result["list_items_count"] = int(count)

        # 完全修复 = 有 sortUrl + ruleArticles + verify_ok
        fixed = bool(sort_url and rule_articles and ok)
        return result, fixed
    except Exception as e:
        # 脱敏异常
        err_msg = str(e)
        # 移除 URL/域名
        err_msg = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
        result["error"] = err_msg[:200]
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


def main():
    safe_log("[INFO] 加载源文件...")
    sources, targets = load_sources()
    safe_log(f"[INFO] 总源数: {len(sources)}, 无sortUrl的视频源: {len(targets)}")

    if not targets:
        safe_log("[WARN] 未找到无sortUrl的视频源")
        out = {"total": 0, "fixed": 0, "still_failed": 0, "records": []}
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return

    # 断点续传：读取已处理记录
    existing = load_progress()
    safe_log(f"[INFO] 断点续传: 已处理 {len(existing)} 个源")

    # 启动浏览器
    safe_log("[INFO] 启动 Playwright 浏览器...")
    pw, browser = try_launch_browser()

    records = []
    fixed_count = 0
    failed_count = 0
    processed_now = 0

    # 先合并已处理的记录
    for rec in targets:
        gidx = rec["global_idx"]
        if gidx in existing:
            r = existing[gidx]
            records.append(r)
            if r.get("verify_ok"):
                fixed_count += 1
            else:
                failed_count += 1

    try:
        for i, rec in enumerate(targets):
            gidx = rec["global_idx"]
            if gidx in existing:
                continue  # 跳过已处理
            processed_now += 1
            safe_log(f"[PROGRESS] {i+1}/{len(targets)} 处理源[{gidx}]...")
            try:
                result, fixed = process_one_source(browser, rec)
            except Exception as e:
                err_msg = str(e)
                err_msg = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                result = {
                    "idx": gidx, "template_type": None,
                    "sort_url_filled": "", "search_url_filled": "",
                    "rule_articles_filled": "", "rule_image_filled": "",
                    "rule_next_page_filled": "", "rule_content_filled": "",
                    "verify_ok": False, "list_items_count": 0,
                    "error": err_msg[:200],
                }
                fixed = False
            records.append(result)
            if fixed:
                fixed_count += 1
                safe_log(f"  [OK] 源[{gidx}] 模板={result['template_type']} "
                         f"列表项={result['list_items_count']} verify={result['verify_ok']}")
            else:
                failed_count += 1
                err = result.get("error") or "verify_failed"
                safe_log(f"  [FAIL] 源[{gidx}] 模板={result['template_type']} "
                         f"列表项={result['list_items_count']} err={err}")

            # 增量保存
            if processed_now % SAVE_EVERY == 0:
                save_progress(records, len(targets), fixed_count, failed_count)
                safe_log(f"  [SAVE] 进度已保存 (fixed={fixed_count}, failed={failed_count})")
    except KeyboardInterrupt:
        safe_log("[WARN] 收到中断信号，保存当前进度...")
    finally:
        save_progress(records, len(targets), fixed_count, failed_count)
        try:
            browser.close()
        except Exception:
            pass
        try:
            pw.stop()
        except Exception:
            pass

    # 最终输出
    total = len(targets)
    partial_count = sum(1 for r in records if r.get("sort_url_filled") and not r.get("verify_ok"))
    out = {
        "total": total,
        "fixed": fixed_count,
        "partial": partial_count,
        "still_failed": failed_count - partial_count,
        "records": records,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    safe_log("")
    safe_log("=" * 60)
    safe_log("[FINAL] 深度优化视频源结果:")
    safe_log(f"  总数: {total}")
    safe_log(f"  完全修复: {fixed_count}")
    safe_log(f"  部分修复: {partial_count}")
    safe_log(f"  仍然失败: {failed_count - partial_count}")
    safe_log(f"  输出文件: {OUTPUT_JSON}")
    safe_log("=" * 60)


if __name__ == "__main__":
    main()
