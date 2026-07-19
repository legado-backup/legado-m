"""
子代理3：网页类型(type=0)订阅源深度分析 - batch idx 100-149
- 输入: output/rss/classified_v2.json (list结构, 222源)
- 输出: output/rss/subagent_web3_analysis.json
- 安全铁律: 只输出技术指标, 业务字段脱敏(路径模式化/代号化)
"""
import asyncio
import json
import re
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

# 项目根目录
ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT = ROOT / "output" / "rss" / "subagent_web3_analysis.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# 范围
BATCH_START = 100
BATCH_END = 149
CONCURRENCY = 4          # 并发浏览器数量
NAV_TIMEOUT_MS = 18000   # 单页导航超时
TOTAL_TIMEOUT_S = 30     # 单源总超时


# ---------- 工具函数 ----------
def _sanitize_url(u: str) -> str:
    """URL脱敏: 只保留协议+路径模式, 隐藏域名"""
    if not u:
        return ""
    try:
        p = urlparse(u)
        host = p.netloc or ""
        # 域名用代号
        host_masked = "站点A" if host else ""
        path = p.path or "/"
        # 路径保留模式, 删除可能的id数字
        path = re.sub(r"\d{3,}", "{id}", path)
        return f"{p.scheme}://{host_masked}{path}"
    except Exception:
        return "<invalid_url>"


def _sanitize_msg(msg: str, max_len: int = 200) -> str:
    """异常消息脱敏: 隐藏URL/域名/IP/Cookie"""
    if not msg:
        return ""
    s = str(msg)
    # 隐藏URL
    s = re.sub(r"https?://[^\s'\"]+", "<URL>", s)
    # 隐藏IP
    s = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP>", s)
    # 隐藏cookie/token
    s = re.sub(r"(?i)(cookie|token|key|secret|auth)\s*[=:]\s*\S+", "<REDACTED>", s)
    if len(s) > max_len:
        s = s[:max_len] + "...<truncated>"
    return s


def _classify_rule_type(v: str) -> str:
    """识别规则字段类型(技术分类, 不输出值)"""
    if not v:
        return "empty"
    s = str(v).strip()
    if s.startswith("<js>") or s.startswith("@js:"):
        return "JS"
    if s.startswith("eval("):
        return "JS_eval"
    if "{{" in s and "}}" in s:
        return "Template"
    if s.startswith("$.") or s.startswith("()."):
        return "CSS"
    if s.startswith("/") and s.endswith("/"):
        return "XPath"
    if s.startswith("list.") or s.startswith("@"):
        return "JsonPath/CSS"
    if "Regex" in s or "re(" in s:
        return "Regex"
    if "::" in s:
        return "Mixed"
    return "Plain/Mixed"


def _has_keyword(comment: str, kw: str) -> bool:
    return kw in (comment or "")


# ---------- 主分析逻辑 ----------
async def analyze_one(browser, source: dict, idx: int) -> dict:
    """分析单个源, 返回技术指标字典"""
    result = {
        "idx": idx,
        "type": source.get("type"),
        "enabled": source.get("enabled"),
        "sort": source.get("sort"),
        "customOrder": source.get("customOrder"),
        "weight": source.get("weight"),
        # 字段填充状态(技术指标)
        "field_status": {},
        # 访问结果
        "access_status": "pending",
        "response_code": None,
        "nav_time_ms": None,
        "final_url_pattern": "",
        "page_title_pattern": "",
        # 特殊处理标记
        "needs_login": False,
        "needs_js_eval": False,
        "has_anti_crawler": False,
        "has_popup": False,
        "has_cloudflare": False,
        # 补全建议(脱敏)
        "suggested_searchUrl_pattern": "",
        "suggested_jsRule_pattern": "",
        "suggested_field_strategy": "",
        # 异常
        "error_type": "",
        "error_msg_sanitized": "",
    }

    # 字段状态评估(仅技术指标)
    tech_fields = [
        "sourceIcon", "searchUrl", "sortUrl",
        "ruleArticles", "ruleTitle", "ruleLink",
        "ruleImage", "ruleNextPage", "rulePubDate",
        "ruleContent", "jsRule",
        "loginUrl", "header", "enabledCookieJar", "enableJs", "loadWithBaseUrl",
    ]
    filled_count = 0
    for k in tech_fields:
        v = source.get(k)
        if v is None or v == "":
            result["field_status"][k] = {"filled": False, "type": "empty", "len": 0}
        else:
            rtype = _classify_rule_type(str(v))
            result["field_status"][k] = {"filled": True, "type": rtype, "len": len(str(v))}
            filled_count += 1
    result["field_filled_count"] = filled_count
    result["field_total"] = len(tech_fields)

    # 标记是否已有searchUrl/jsRule
    has_search = bool(source.get("searchUrl"))
    has_jsrule = bool(source.get("jsRule"))
    has_login = bool(source.get("loginUrl"))
    result["has_searchUrl"] = has_search
    result["has_jsRule"] = has_jsrule
    result["has_loginUrl"] = has_login
    if has_login:
        result["needs_login"] = True
    if result["field_status"].get("searchUrl", {}).get("type") in ("JS", "JS_eval"):
        result["needs_js_eval"] = True
    if result["field_status"].get("ruleArticles", {}).get("type") in ("JS", "JS_eval"):
        result["needs_js_eval"] = True
    if result["field_status"].get("ruleContent", {}).get("type") in ("JS", "JS_eval"):
        result["needs_js_eval"] = True

    # 获取sourceUrl(仅用于Playwright访问, 不输出原文)
    source_url = source.get("sourceUrl") or ""
    if not source_url:
        result["access_status"] = "no_sourceUrl"
        result["suggested_field_strategy"] = "manual: 无sourceUrl无法访问, 需人工补全"
        return result

    # Playwright访问
    page = None
    t0 = time.time()
    try:
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page.set_default_timeout(NAV_TIMEOUT_MS)

        # 监听响应, 捕获状态码
        captured_codes = []

        async def on_response(resp):
            try:
                if resp.url == source_url or resp.url.startswith(source_url.rstrip("/")):
                    captured_codes.append(resp.status)
            except Exception:
                pass

        page.on("response", on_response)

        # 导航
        try:
            resp = await page.goto(source_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            if resp:
                result["response_code"] = resp.status
                result["access_status"] = "ok" if resp.status < 400 else f"http_{resp.status}"
        except Exception as e:
            msg = _sanitize_msg(str(e))
            etype = type(e).__name__
            # 判定异常类别
            if "Timeout" in etype or "timeout" in msg.lower():
                result["access_status"] = "timeout"
            elif "net::ERR_NAME_NOT_RESOLVED" in msg or "ERR_CONNECTION" in msg:
                result["access_status"] = "dns_or_conn_failed"
            elif "ERR_ABORTED" in msg:
                result["access_status"] = "aborted"
            else:
                result["access_status"] = "exception"
            result["error_type"] = etype
            result["error_msg_sanitized"] = msg
            # 关页返回
            try:
                await page.close()
            except Exception:
                pass
            result["nav_time_ms"] = int((time.time() - t0) * 1000)
            return result

        result["nav_time_ms"] = int((time.time() - t0) * 1000)

        # 等待渲染
        await page.wait_for_timeout(2500)

        # 检测Cloudflare
        try:
            html_text = await page.content()
            html_lower = html_text.lower()
            if "cloudflare" in html_lower or "cf-browser-verification" in html_lower or "cf-challenge" in html_lower:
                result["has_cloudflare"] = True
                result["has_anti_crawler"] = True
            if "just a moment" in html_lower and "checking your browser" in html_lower:
                result["has_cloudflare"] = True
                result["has_anti_crawler"] = True
        except Exception:
            pass

        # 检测登录跳转/弹框
        try:
            final_url = page.url
            result["final_url_pattern"] = _sanitize_url(final_url)
            fl = final_url.lower()
            if "login" in fl or "signin" in fl or "auth" in fl:
                result["needs_login"] = True
        except Exception:
            pass

        try:
            title = await page.title()
            tl = (title or "").lower()
            # 标题模式化: 只保留长度+是否含关键词, 不输出原文
            title_indicator = []
            if "login" in tl or "登录" in tl:
                title_indicator.append("login")
                result["needs_login"] = True
            if "cloudflare" in tl:
                title_indicator.append("cloudflare")
            if "验证" in tl or "verify" in tl or "captcha" in tl:
                title_indicator.append("verify")
                result["has_anti_crawler"] = True
            result["page_title_pattern"] = "|".join(title_indicator) if title_indicator else "normal"
        except Exception:
            pass

        # 检测弹框(alert/confirm)
        try:
            popup_found = await page.evaluate("""() => {
                const ind = [];
                if (document.querySelector('div[role=\"dialog\"]')) ind.push('dialog');
                if (document.querySelector('.modal')) ind.push('modal');
                if (document.querySelector('.popup')) ind.push('popup');
                // 检测遮罩
                const overlay = document.querySelector('.overlay, .mask, .layui-layer-shade');
                if (overlay) ind.push('overlay');
                return ind;
            }""")
            if popup_found:
                result["has_popup"] = True
        except Exception:
            pass

        # DOM结构探查(用于建议字段策略, 不输出业务文本)
        try:
            dom_info = await page.evaluate("""() => {
                const info = {
                    article_selectors: [],
                    has_list: false,
                    has_pagination: false,
                    form_count: 0,
                    search_form: false,
                };
                // 常见列表选择器
                const listSelectors = ['.list', '.article-list', '.news-list', '.post-list', '.item-list', 'ul.list', '.search-list', '.movie-list', '.vod-list', '.myui-vodlist', '.stui-vodlist', '.module-vodlist', 'ul.search-list'];
                for (const s of listSelectors) {
                    if (document.querySelector(s)) {
                        info.article_selectors.push(s);
                        info.has_list = true;
                    }
                }
                // 翻页
                const pagSelectors = ['.pagination', '.page', '.pager', '.pagebar', '.nav-page', 'a.next', 'a[href*=\"page=\"]'];
                for (const s of pagSelectors) {
                    if (document.querySelector(s)) {
                        info.has_pagination = true;
                        break;
                    }
                }
                // 搜索表单
                info.form_count = document.querySelectorAll('form').length;
                if (document.querySelector('form[action*=\"search\"], form input[name=\"search\"], form input[name=\"wd\"], form input[name=\"keyword\"], form input[name=\"q\"]')) {
                    info.search_form = true;
                }
                return info;
            }""")
            result["dom_info"] = dom_info

            # 基于DOM结构建议字段策略
            strategy = []
            if dom_info.get("has_list") and dom_info.get("article_selectors"):
                strategy.append(f"ruleArticles候选选择器: {','.join(dom_info['article_selectors'][:3])}")
            if dom_info.get("has_pagination"):
                strategy.append("ruleNextPage: 检查a.next或.page a[href*='page=']")
            if dom_info.get("search_form"):
                strategy.append("searchUrl: 抓取form[action]+input[name]组装POST/GET")
            result["suggested_field_strategy"] = "; ".join(strategy) if strategy else "需手工分析DOM"
        except Exception as e:
            result["error_type"] = type(e).__name__
            result["error_msg_sanitized"] = _sanitize_msg(str(e))

        # 建议searchUrl模式
        if not has_search:
            if result["needs_js_eval"]:
                result["suggested_searchUrl_pattern"] = "<js>{{Get('url')}}/search/path/{{key}}/page/{{page}}.html</js>"
            else:
                result["suggested_searchUrl_pattern"] = "/search.php?q={{key}}&page={{page}} 或 /search/{{key}}_{{page}}.html"
        else:
            result["suggested_searchUrl_pattern"] = "已有, 类型=" + result["field_status"].get("searchUrl", {}).get("type", "unknown")

        # 建议jsRule模式
        if not has_jsrule:
            if result["has_anti_crawler"] or result["has_cloudflare"]:
                result["suggested_jsRule_pattern"] = "anti_crawler: 需js解密或cookie预处理"
            elif result["needs_js_eval"]:
                result["suggested_jsRule_pattern"] = "eval+Reload模式(参考idx=131)"
            else:
                result["suggested_jsRule_pattern"] = "无需jsRule(纯CSS/XPath可解析)"
        else:
            result["suggested_jsRule_pattern"] = "已有"

    except Exception as e:
        result["access_status"] = "fatal_exception"
        result["error_type"] = type(e).__name__
        result["error_msg_sanitized"] = _sanitize_msg(str(e))
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass

    return result


async def main():
    print(f"[INFO] loading input: {INPUT}")
    if not INPUT.exists():
        print(f"[ERR] input not found: {INPUT}")
        return
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print(f"[ERR] expected list, got {type(data).__name__}")
        return
    print(f"[INFO] total sources: {len(data)}")

    # 筛选: idx 100-149 且 type=0, 排除已处理
    targets = []
    for i, s in enumerate(data):
        if BATCH_START <= i <= BATCH_END and s.get("type") == 0:
            comment = s.get("sourceComment") or ""
            if _has_keyword(comment, "AI_CLASSIFY:access_failed"):
                continue
            if _has_keyword(comment, "AI_CLASSIFY:skipped"):
                continue
            targets.append((i, s))

    print(f"[INFO] batch {BATCH_START}-{BATCH_END}: type=0 candidates={sum(1 for i in range(BATCH_START, BATCH_END+1) if i < len(data) and data[i].get('type')==0)} to_analyze={len(targets)}")
    print(f"[INFO] target idx list: {[t[0] for t in targets]}")

    # 启动Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERR] playwright not installed in venv")
        return

    results = []
    failed_idx = []

    async with async_playwright() as p:
        # 启动chromium
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
        except Exception as e:
            print(f"[ERR] browser launch failed: {_sanitize_msg(str(e))}")
            return

        # 信号量控制并发
        sem = asyncio.Semaphore(CONCURRENCY)

        async def worker(idx, src):
            async with sem:
                print(f"[{idx}] start analyze...")
                try:
                    # 单源总超时
                    r = await asyncio.wait_for(analyze_one(browser, src, idx), timeout=TOTAL_TIMEOUT_S)
                    results.append(r)
                    print(f"[{idx}] done status={r['access_status']} filled={r['field_filled_count']}/{r['field_total']}")
                except asyncio.TimeoutError:
                    failed_idx.append(idx)
                    r = {
                        "idx": idx,
                        "access_status": "total_timeout",
                        "error_type": "TimeoutError",
                        "error_msg_sanitized": f"exceeded {TOTAL_TIMEOUT_S}s",
                        "field_filled_count": 0,
                        "field_total": 16,
                    }
                    results.append(r)
                    print(f"[{idx}] TIMEOUT")
                except Exception as e:
                    failed_idx.append(idx)
                    r = {
                        "idx": idx,
                        "access_status": "worker_exception",
                        "error_type": type(e).__name__,
                        "error_msg_sanitized": _sanitize_msg(str(e)),
                        "field_filled_count": 0,
                        "field_total": 16,
                    }
                    results.append(r)
                    print(f"[{idx}] EXCEPTION: {type(e).__name__}")

        # 所有任务并行(受信号量限制)
        tasks = [worker(idx, src) for idx, src in targets]
        await asyncio.gather(*tasks)

        await browser.close()

    # 按idx排序
    results.sort(key=lambda r: r.get("idx", 0))

    # 统计汇总
    summary = {
        "agent": "web_source_analyzer_batch3",
        "batch_range": f"{BATCH_START}-{BATCH_END}",
        "total_analyzed": len(results),
        "total_failed": len(failed_idx),
        "failed_idx_list": failed_idx,
        "access_status_distribution": {},
        "needs_login_count": 0,
        "needs_js_eval_count": 0,
        "has_anti_crawler_count": 0,
        "has_cloudflare_count": 0,
        "has_popup_count": 0,
        "field_fill_stats": {
            "searchUrl_filled": 0,
            "jsRule_filled": 0,
            "ruleArticles_filled": 0,
            "ruleContent_filled": 0,
            "avg_filled_count": 0,
        },
        "results": results,
    }
    for r in results:
        s = r.get("access_status", "unknown")
        summary["access_status_distribution"][s] = summary["access_status_distribution"].get(s, 0) + 1
        if r.get("needs_login"):
            summary["needs_login_count"] += 1
        if r.get("needs_js_eval"):
            summary["needs_js_eval_count"] += 1
        if r.get("has_anti_crawler"):
            summary["has_anti_crawler_count"] += 1
        if r.get("has_cloudflare"):
            summary["has_cloudflare_count"] += 1
        if r.get("has_popup"):
            summary["has_popup_count"] += 1
        fs = r.get("field_status", {})
        if fs.get("searchUrl", {}).get("filled"):
            summary["field_fill_stats"]["searchUrl_filled"] += 1
        if fs.get("jsRule", {}).get("filled"):
            summary["field_fill_stats"]["jsRule_filled"] += 1
        if fs.get("ruleArticles", {}).get("filled"):
            summary["field_fill_stats"]["ruleArticles_filled"] += 1
        if fs.get("ruleContent", {}).get("filled"):
            summary["field_fill_stats"]["ruleContent_filled"] += 1
    if results:
        summary["field_fill_stats"]["avg_filled_count"] = round(
            sum(r.get("field_filled_count", 0) for r in results) / len(results), 2
        )

    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("=" * 60)
    print(f"[DONE] analyzed={len(results)} failed={len(failed_idx)}")
    print(f"[OUTPUT] {OUTPUT}")
    print(f"[DIST] {summary['access_status_distribution']}")
    print(f"[NEEDS_LOGIN] {summary['needs_login_count']} [NEEDS_JS] {summary['needs_js_eval_count']}")
    print(f"[ANTI_CRAWLER] {summary['has_anti_crawler_count']} [CLOUDFLARE] {summary['has_cloudflare_count']} [POPUP] {summary['has_popup_count']}")
    print(f"[FIELD_FILL] {summary['field_fill_stats']}")


if __name__ == "__main__":
    asyncio.run(main())
