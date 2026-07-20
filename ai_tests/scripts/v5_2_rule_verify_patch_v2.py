"""
V2 补丁：每个源用全新 browser 实例，避免内存累积导致崩溃
"""
import json
import re
import time
import gc
from pathlib import Path
from typing import Optional, Tuple, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROJECT_ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v5_2_stable.json"
RESULT_JSON = PROJECT_ROOT / "output" / "rss" / "v5_2_rule_verify_result.json"
PATCH_LOG = PROJECT_ROOT / "output" / "rss" / "v5_2_rule_verify_patch_v2_log.txt"

PAGE_TIMEOUT_MS = 15000
WAIT_AFTER_LOAD_SEC = 5.0
MOBILE_VIEWPORT = {"width": 375, "height": 667}
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 12; Pixel 5) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/101.0.4951.61 Mobile Safari/537.36")

COMMON_SELECTORS = [
    "article", ".article", ".item", ".post", ".card",
    ".list-item", ".news-item", ".vod-item", ".video-item",
    "ul li", "ol li", ".list li",
    "table tr", ".main li", ".box li",
    ".content li", ".container li",
]


def extract_article_list_from_json_rule(rule: str) -> Tuple[Optional[str], str]:
    if not rule.startswith("{"):
        return None, "not_json"
    try:
        obj = json.loads(rule)
    except Exception as e:
        return None, f"json_parse_failed: {type(e).__name__}"
    article_list = obj.get("articleList") or obj.get("article_list") or obj.get("list")
    if not article_list:
        return None, "no_articleList_field"
    if article_list.startswith("@CSS:"):
        return article_list[5:].strip(), "ok"
    if article_list.startswith("@XPath:") or article_list.startswith("@JSON:"):
        return None, "xpath_or_json_not_supported"
    return convert_legado_selector_to_css(article_list), "ok"


def convert_legado_selector_to_css(sel: str) -> Optional[str]:
    if not sel:
        return None
    sel = sel.strip()
    sel_no_idx = re.sub(r"\[[\!\d:\-\s,]*\]$", "", sel)
    if "@" in sel_no_idx:
        parts = sel_no_idx.split("@")
        css_list = []
        for p in parts:
            c = convert_single(p)
            if c:
                css_list.append(c)
            else:
                return None
        return " ".join(css_list)
    return convert_single(sel_no_idx)


def convert_single(seg: str) -> Optional[str]:
    if not seg:
        return None
    seg = seg.strip()
    seg_no_idx = re.sub(r"\[[\!\d:\-\s,]*\]$", "", seg)
    if seg_no_idx.startswith("class."):
        cls = seg_no_idx[len("class."):]
        return "." + cls if cls else None
    if seg_no_idx.startswith("id."):
        idv = seg_no_idx[len("id."):]
        return "#" + idv.split(".")[0] if idv else None
    if seg_no_idx.startswith("tag."):
        tag = seg_no_idx[len("tag."):]
        return tag.split(".")[0] if tag else None
    if seg_no_idx.startswith("text."):
        return None
    if re.match(r"^[\.\#]?[a-zA-Z][\w\.\-\s\>\+\~\,\[\]\=\:\"\'\(\)\*\#]*$", seg_no_idx):
        return seg_no_idx
    if re.match(r"^[a-zA-Z][a-zA-Z0-9]*$", seg_no_idx):
        return seg_no_idx
    return None


def find_common_selector(soup: BeautifulSoup) -> List[dict]:
    matched = []
    for sel in COMMON_SELECTORS:
        try:
            found = soup.select(sel)
            if len(found) >= 2:
                matched.append({"selector": sel, "count": len(found)})
        except Exception:
            pass
    matched.sort(key=lambda x: -x["count"])
    return matched[:5]


def detect_markers(html: str, title: str) -> Tuple[bool, bool]:
    hl = html.lower()
    tl = title.lower()
    cf_markers = ["cf-browser-verification", "cf_chl_opt", "cloudflare",
                  "challenge-platform", "just a moment", "cf-turnstile",
                  "ray id", "_cf_chl"]
    login_markers = ["login", "登录", "sign in", "log in", "请先登录",
                     "用户名", "密码", "password", "请登录", "need login"]
    return (any(m in hl or m in tl for m in cf_markers),
            any(m in hl or m in tl for m in login_markers))


def verify_one_with_fresh_browser(pw, url: str, css_sel: str) -> dict:
    """用全新 browser 实例验证一个源。"""
    out = {"status": "fail", "failure_reason": "exception", "error": "",
           "rule_match_count": 0, "page_html_length": 0, "page_title_length": 0,
           "status_code": None, "common_selectors": [], "elapsed_sec": 0}
    browser = None
    try:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport=MOBILE_VIEWPORT,
            user_agent=MOBILE_UA,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            ignore_https_errors=True,
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = ctx.new_page()
        try:
            page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,ico}",
                       lambda r: r.abort())
        except Exception:
            pass

        start = time.time()
        try:
            resp = page.goto(url, wait_until="domcontentloaded",
                             timeout=PAGE_TIMEOUT_MS)
            page.wait_for_timeout(int(WAIT_AFTER_LOAD_SEC * 1000))
            title = page.title() or ""
            html = page.content() or ""
            elapsed = round(time.time() - start, 2)

            out["status_code"] = resp.status if resp else None
            out["page_html_length"] = len(html)
            out["page_title_length"] = len(title)
            out["elapsed_sec"] = elapsed

            has_cf, has_login = detect_markers(html, title)
            soup = BeautifulSoup(html, "lxml")

            try:
                elements = soup.select(css_sel)
                match_count = len(elements)
            except Exception:
                match_count = 0

            out["rule_match_count"] = match_count

            if match_count >= 1:
                out["status"] = "ok"
                out["failure_reason"] = ""
            else:
                common = find_common_selector(soup)
                out["common_selectors"] = common
                network_ok = (resp is not None and 200 <= resp.status < 500)
                if has_cf:
                    out["failure_reason"] = "cf_shield"
                elif has_login:
                    out["failure_reason"] = "login_required"
                elif network_ok and resp.status == 200:
                    if len(html) < 5000:
                        out["failure_reason"] = "empty_content"
                    elif common:
                        out["failure_reason"] = "rule_mismatch"
                    else:
                        out["failure_reason"] = "empty_content"
                else:
                    out["failure_reason"] = "network_fail"
        except PlaywrightTimeout:
            out["failure_reason"] = "timeout"
            out["error"] = "patch_v2_timeout"
        except Exception as e:
            out["failure_reason"] = "exception"
            out["error"] = f"{type(e).__name__}: {str(e)[:150]}"
        try:
            page.close()
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass
    except Exception as e:
        out["error"] = f"browser_launch_failed: {type(e).__name__}: {str(e)[:150]}"
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        gc.collect()
    return out


def main():
    print("=" * 60)
    print("V2 补丁: 重新验证 JSON 格式 ruleArticles 源（独立 browser）")
    print("=" * 60)

    with open(RESULT_JSON, "r", encoding="utf-8") as f:
        result_data = json.load(f)
    results = result_data["results"]

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # 找出之前 patch_failed 的源 + 所有 JSON 格式 + html_len > 0 的源
    targets = []
    for r in results:
        rule = r.get("rule_articles_raw", "")
        if rule.startswith("{") and "articleList" in rule:
            # 之前 patch_failed 或仍是 unknown 且 html_len > 0
            prev_html = r.get("page_html_length", 0)
            if r.get("rule_type") == "unknown" and prev_html > 10000:
                targets.append(r["idx"])
            elif "patch_failed" in r.get("error", ""):
                targets.append(r["idx"])

    print(f"[INFO] 待重新验证源数: {len(targets)}")
    if not targets:
        print("[INFO] 无需重新验证")
        return

    log_lines = []

    with sync_playwright() as pw:
        for idx in targets:
            src = sources[idx]
            url = src.get("sourceUrl", "")
            rule = src.get("ruleArticles", "")
            css_sel, note = extract_article_list_from_json_rule(rule)

            line = f"idx={idx}  css={css_sel!r}  note={note}  url_len={len(url)}"
            print(line)
            log_lines.append(line)

            if not css_sel:
                log_lines.append("  -> skip (no css)")
                continue

            out = verify_one_with_fresh_browser(pw, url, css_sel)

            r = results[idx]
            r["css_converted"] = [css_sel]
            r["rule_type"] = "css_from_json"
            r["rule_match_count"] = out["rule_match_count"]
            r["page_html_length"] = out["page_html_length"]
            r["page_title_length"] = out["page_title_length"]
            r["status_code"] = out["status_code"]
            r["elapsed_sec"] = out["elapsed_sec"]
            r["error"] = out["error"]
            r["common_selectors"] = out["common_selectors"]
            r["status"] = out["status"]
            r["failure_reason"] = out["failure_reason"]

            pl = (f"  -> status={r['status']}  reason={r['failure_reason']}  "
                  f"match={r['rule_match_count']}  html_len={r['page_html_length']}  "
                  f"status_code={r['status_code']}  elapsed={r['elapsed_sec']}s")
            print(pl)
            log_lines.append(pl)

    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    with open(PATCH_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    ok = sum(1 for x in results if x.get("status") == "ok")
    fail = sum(1 for x in results if x.get("status") == "fail")
    from collections import Counter
    by_reason = Counter(x.get("failure_reason", "") for x in results if x.get("status") == "fail")
    print()
    print("=" * 60)
    print(f"[PATCH V2 FINAL] 总计 {len(results)}  成功 {ok}  失败 {fail}")
    print(f"[PATCH V2 FINAL] 失败原因: {dict(by_reason)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
