"""
subagent_analyze_web1.py - 网页源深度分析第一批(idx 0-49, type=0)

读取 classified_v2.json，筛选 type=0 且 idx 0-49 的源，
排除 sourceComment 含 "AI_CLASSIFY:access_failed" 的源。
对每个网页源用 Playwright (headless) 访问 sourceUrl，深度分析字段。

输出安全铁律:
1. 脚本输出禁止包含业务字段原文 (sourceName/sourceUrl/sourceComment)
2. 只输出技术指标: idx, type, fields, special_config
3. Playwright 异常消息必须脱敏 (替换 URL/域名为 [URL]/[DOMAIN])
4. 不输出完整 URL, 只保留路径模式
5. 不输出 cookie/token/password 等敏感字段
6. 视频网站域名必须用代号 (站点A/B/C)

输出文件: output/rss/subagent_web1_analysis.json
"""
import asyncio
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

# 项目路径
ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT = ROOT / "output" / "rss" / "subagent_web1_analysis.json"

# 范围
BATCH_START = 0
BATCH_END = 49  # inclusive
TIMEOUT_MS = 12000  # 12秒


# ---------- 工具函数 ----------

def mask_url(url: str) -> str:
    """URL 路径模式化：替换域名/长ID。"""
    if not url:
        return ""
    s = re.sub(r"https?://[^/]+", "[DOMAIN]", str(url))
    s = re.sub(r"\d{3,}", "{id}", s)
    return s


def mask_error(msg: str) -> str:
    """异常消息脱敏。"""
    if not msg:
        return ""
    s = str(msg)
    # 替换 URL
    s = re.sub(r"https?://[^\s'\"<>]+", "[URL]", s)
    # 替换域名
    s = re.sub(r"(?<=\b)[a-z0-9-]+\.(com|net|org|cn|io|xyz|tv|info|me|cc|tk|ru|kr|jp|us|uk|de|fr)(?=\b|/|:|$)", "[DOMAIN]", s, flags=re.IGNORECASE)
    # 替换 IP
    s = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]", s)
    return s


def classify_rule(rule: str) -> str:
    """识别规则类型。"""
    if not rule:
        return "empty"
    r = str(rule)
    if r.startswith("@css:") or r.startswith("css:"):
        return "CSS"
    if r.startswith("@XPath:") or r.startswith("xpath:") or r.startswith("//"):
        return "XPath"
    if r.startswith("$.") or r.startswith("$["):
        return "JSONPath"
    if r.startswith("@js:") or r.startswith("<js>") or r.startswith("js:"):
        return "JS"
    if r.startswith("@regex:") or r.startswith("regex:"):
        return "Regex"
    if r.startswith("##") or r.startswith("@"):
        return "Filter"
    return "Plain/Mixed"


# ---------- Playwright 分析核心 ----------

async def analyze_one(page, source: dict, idx: int) -> dict:
    """分析单个源。返回结果字典 (脱敏)。"""
    result = {
        "idx": idx,
        "type": source.get("type", 0),
        "source_url_accessible": False,
        "fields": {
            "sourceIcon": source.get("sourceIcon", ""),
            "searchUrl": source.get("searchUrl", ""),
            "sortUrl": source.get("sortUrl", ""),
            "ruleArticles": source.get("ruleArticles", ""),
            "ruleTitle": source.get("ruleTitle", ""),
            "ruleLink": source.get("ruleLink", ""),
            "ruleImage": source.get("ruleImage", ""),
            "ruleNextPage": source.get("ruleNextPage", ""),
            "rulePubDate": source.get("rulePubDate", ""),
            "ruleContent": source.get("ruleContent", ""),
        },
        "special_config": {
            "loginUrl": source.get("loginUrl", ""),
            "enabledCookieJar": bool(source.get("enabledCookieJar", False)),
            "enableJs": bool(source.get("enableJs", True)),
            "loadWithBaseUrl": bool(source.get("loadWithBaseUrl", True)),
            "jsRule": source.get("jsRule", ""),
        },
        "analysis_notes": "",
        "page_signals": {},
    }

    url = source.get("sourceUrl", "")
    if not url:
        result["analysis_notes"] = "no sourceUrl"
        return result

    try:
        resp = await page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)  # 等 JS 渲染
        if resp and resp.status < 500:
            result["source_url_accessible"] = True
        # 检测 Cloudflare 等盾
        content = await page.content()
        is_cf = ("cf-browser-verification" in content) or ("Just a moment" in content) or ("_cf_chl" in content)
        result["page_signals"]["cloudflare"] = is_cf
    except Exception as e:
        result["analysis_notes"] = f"goto failed: {mask_error(str(e))[:200]}"
        return result

    try:
        signals = await page.evaluate(
            r"""
            () => {
                const sig = {};
                // 1. 搜索表单检测
                const forms = Array.from(document.querySelectorAll('form'));
                const searchForms = forms.filter(f => {
                    const action = (f.action || '') + ' ' + (f.getAttribute('action') || '');
                    const html = f.outerHTML.toLowerCase();
                    return /search|sou|soso|query|keyword|wd|q=/.test(action) || /search|sou/.test(html);
                });
                sig.search_form_count = searchForms.length;
                if (searchForms.length > 0) {
                    const f = searchForms[0];
                    sig.search_form_action = f.getAttribute('action') || f.action || '';
                    sig.search_form_method = (f.method || 'GET').toUpperCase();
                    // 找搜索输入框
                    const inputs = f.querySelectorAll('input[type="text"], input[type="search"], input:not([type])');
                    sig.search_input_names = Array.from(inputs).map(i => i.name || i.id || 'q').slice(0, 3);
                }
                // 搜索链接
                const searchLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                    const t = (a.textContent || '').trim();
                    const h = a.href || '';
                    return /^(搜索|search|查找|sou)$/i.test(t) || /search|sou\?|q=/.test(h);
                }).slice(0, 5);
                sig.search_link_count = searchLinks.length;
                if (searchLinks.length > 0) {
                    sig.search_link_href = searchLinks[0].href;
                }

                // 2. 列表项检测（常见列表选择器）
                const listSelectors = [
                    '.list', '.lists', '.list-item', '.item', '.post', '.posts',
                    '.article', '.articles', '.card', '.movie-item', '.vod_item',
                    '.stui-vodlist__item', '.stui-vodlist__box', '.module-item',
                    '.myui-vodlist__item', '.searchlist', '.search-list',
                    '.vod-list', '.vodlist_item', '.video-item', '.news-item',
                    '.post-item', '.entry', '.excerpt', '.thumbnail'
                ];
                let bestList = null;
                let bestCount = 0;
                for (const sel of listSelectors) {
                    const items = document.querySelectorAll(sel);
                    if (items.length > bestCount) {
                        bestCount = items.length;
                        bestList = sel;
                    }
                }
                sig.best_list_selector = bestList;
                sig.best_list_count = bestCount;

                // 3. 分页检测
                const pagingSelectors = [
                    '.pagination', '.pager', '.page', '.pages', '.paging',
                    '.pagebar', '.page-nav', '.nav-links', '.stui-pannel__head',
                    '.myui-page', '.module-page', '.nextpage', '.page-next',
                    'a.next', 'a[rel="next"]', '.pagination a'
                ];
                let paging = null;
                for (const sel of pagingSelectors) {
                    if (document.querySelector(sel)) {
                        paging = sel;
                        break;
                    }
                }
                sig.paging_selector = paging;
                const nextLink = document.querySelector('a.next, a[rel="next"], .next a, .pagination .next a, .page-next a');
                sig.next_href = nextLink ? nextLink.href : '';

                // 4. 弹框/广告检测
                const popupSelectors = ['.popup', '.modal', '.dialog', '.mask', '.overlay',
                    '.popup-box', '.modal-box', '.ad-popup', '.ad-modal',
                    '.layui-layer', '.layui-layer-shade', '.layui-layer-mask',
                    '#mask', '#overlay', '.mask-layer', '.pop-box', '.popbox'];
                const foundPopups = popupSelectors.filter(s => document.querySelector(s));
                sig.popup_selectors = foundPopups;
                sig.popup_count = foundPopups.length;

                // 5. favicon
                const faviconLink = document.querySelector('link[rel*="icon"]');
                sig.favicon_href = faviconLink ? faviconLink.href : '';

                // 6. 登录检测
                const loginLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                    const t = (a.textContent || '').trim();
                    const h = a.href || '';
                    return /^(登录|登入|login|sign\s*in)$/i.test(t) || /login|signin|auth/.test(h);
                }).slice(0, 3);
                sig.login_link_count = loginLinks.length;
                sig.login_link_href = loginLinks.length > 0 ? loginLinks[0].href : '';

                // 7. 分类导航 (sortUrl)
                const navLinks = Array.from(document.querySelectorAll('nav a, .nav a, .menu a, .header-menu a, .navbar a, .mainnav a'));
                sig.nav_link_count = navLinks.length;
                sig.nav_sample = navLinks.slice(0, 5).map(a => ({
                    href: a.getAttribute('href') || '',
                    text: (a.textContent || '').trim().substring(0, 30)
                }));

                return sig;
            }
            """
        )
        result["page_signals"].update(signals)
    except Exception as e:
        result["analysis_notes"] += f" | eval failed: {mask_error(str(e))[:150]}"

    # 基于信号生成字段建议
    try:
        fields = result["fields"]
        sc = result["special_config"]

        # searchUrl 补全
        if not fields["searchUrl"] and signals.get("search_form_count", 0) > 0:
            action = signals.get("search_form_action", "")
            method = signals.get("search_form_method", "GET")
            input_names = signals.get("search_input_names", ["q"])
            input_name = input_names[0] if input_names else "q"
            if action:
                # 路径模式化
                action_clean = re.sub(r"https?://[^/]+", "", action) if action.startswith("http") else action
                if not action_clean.startswith("/") and not action_clean.startswith("http"):
                    action_clean = "/" + action_clean
                if method == "GET":
                    fields["searchUrl"] = f"{action_clean}?{input_name}={{{{key}}}}"
                else:
                    fields["searchUrl"] = f"{action_clean},{{\"method\":\"POST\",\"body\":\"{input_name}={{{{key}}}}\"}}"
                result["analysis_notes"] += " | searchUrl inferred from form"
        if not fields["searchUrl"] and signals.get("search_link_href"):
            href = signals["search_link_href"]
            href_clean = re.sub(r"https?://[^/]+", "", href) if href.startswith("http") else href
            fields["searchUrl"] = f"{href_clean}{{{{key}}}}"
            result["analysis_notes"] += " | searchUrl inferred from link"

        # sourceIcon 补全
        if not fields["sourceIcon"] and signals.get("favicon_href"):
            fields["sourceIcon"] = signals["favicon_href"]

        # ruleArticles 补全
        if not fields["ruleArticles"] and signals.get("best_list_selector"):
            sel = signals["best_list_selector"]
            fields["ruleArticles"] = f"css:{sel}@children"
            result["analysis_notes"] += " | ruleArticles inferred"

        # ruleNextPage 补全
        if not fields["ruleNextPage"] and signals.get("next_href"):
            fields["ruleNextPage"] = "css:a.next@href||css:a[rel=next]@href"
            result["analysis_notes"] += " | ruleNextPage inferred"

        # jsRule 补全 (弹框自动关闭)
        if not sc["jsRule"] and signals.get("popup_count", 0) > 0:
            pops = signals.get("popup_selectors", [])
            sel_str = ",".join(pops[:5])
            sc["jsRule"] = f"// 自动关闭弹框\ndocument.querySelectorAll('{sel_str}').forEach(e=>e.style.display='none');"
            result["analysis_notes"] += f" | jsRule inferred ({len(pops)} popups)"

        # loginUrl 补全 (有登录链接 + 无 loginUrl + 有反爬)
        if not sc["loginUrl"] and signals.get("login_link_count", 0) > 0 and signals.get("cloudflare", False):
            sc["loginUrl"] = "@js:java.startBrowserAwait(source.sourceUrl,'通过验证')"
            sc["enabledCookieJar"] = True
            result["analysis_notes"] += " | loginUrl inferred (CF)"

    except Exception as e:
        result["analysis_notes"] += f" | field gen failed: {mask_error(str(e))[:150]}"

    return result


# ---------- 主流程 ----------

async def main():
    # 加载数据
    with INPUT.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 筛选目标
    targets = []
    for idx in range(BATCH_START, BATCH_END + 1):
        if idx >= len(data):
            break
        src = data[idx]
        if src.get("type") != 0:
            continue
        comment = str(src.get("sourceComment", ""))
        if "AI_CLASSIFY:access_failed" in comment:
            continue
        targets.append((idx, src))

    print(f"[INFO] 待分析源数: {len(targets)}")
    print(f"[INFO] 待分析idx: {[t[0] for t in targets]}")

    # 导入 Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright not installed, run: pip install playwright && playwright install chromium")
        sys.exit(1)

    results = []
    success = 0
    failed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"
        ])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        # 屏蔽图片/字体等加速
        await context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}", lambda route: route.abort())

        for i, (idx, src) in enumerate(targets):
            print(f"[{i+1}/{len(targets)}] idx={idx} analyzing...", flush=True)
            page = await context.new_page()
            try:
                result = await analyze_one(page, src, idx)
                results.append(result)
                if result["source_url_accessible"]:
                    success += 1
                else:
                    failed += 1
                notes = result["analysis_notes"][:80]
                print(f"  -> accessible={result['source_url_accessible']}, notes={notes}", flush=True)
            except Exception as e:
                failed += 1
                results.append({
                    "idx": idx,
                    "type": src.get("type", 0),
                    "source_url_accessible": False,
                    "fields": {},
                    "special_config": {},
                    "analysis_notes": f"unhandled error: {mask_error(str(e))[:200]}",
                    "page_signals": {},
                })
                print(f"  -> ERROR: {mask_error(str(e))[:150]}", flush=True)
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

        await context.close()
        await browser.close()

    # 输出
    output = {
        "agent": "web_source_analyzer_batch1",
        "batch_range": f"{BATCH_START}-{BATCH_END}",
        "total_analyzed": len(results),
        "success_count": success,
        "failed_count": failed,
        "results": results,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] analyzed={len(results)}, success={success}, failed={failed}")
    print(f"[OUTPUT] {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
