"""
补丁脚本：重新验证 JSON 格式 ruleArticles 的源

V5.2 主脚本 v5_2_rule_verify.py 没解析 JSON 格式规则（{"articleList":"...",...}），
导致 47 个源全部标记为 unknown/fail。

本脚本：
1. 加载 v5_2_rule_verify_result.json
2. 找出所有 rule_articles_raw 以 '{' 开头且含 'articleList' 的源
3. 如果之前 html_len > 0：重新访问，提取 articleList 字段，应用 CSS 选择器
4. 如果之前 html_len = 0：保持原结果（网络问题，不重试）
5. 更新 result.json
"""
import json
import re
import time
from pathlib import Path
from typing import Optional, Tuple, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROJECT_ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v5_2_stable.json"
RESULT_JSON = PROJECT_ROOT / "output" / "rss" / "v5_2_rule_verify_result.json"
PATCH_LOG = PROJECT_ROOT / "output" / "rss" / "v5_2_rule_verify_patch_log.txt"

PAGE_TIMEOUT_MS = 15000
WAIT_AFTER_LOAD_SEC = 5.0
MOBILE_VIEWPORT = {"width": 375, "height": 667}
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 12; Pixel 5) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/101.0.4951.61 Mobile Safari/537.36")

COMMON_SELECTORS = [
    "article", ".article", ".item", ".post", ".card",
    ".list-item", ".news-item", ".vod-item", ".video-item",
    ".movie-item", ".article-item", ".feed", ".entry",
    "ul li", "ol li", ".list li",
    "table tr", ".main li", ".box li",
    ".content li", ".container li",
]


def extract_article_list_from_json_rule(rule: str) -> Tuple[Optional[str], str]:
    """
    从 JSON 格式规则中提取 articleList 字段。
    返回 (css_selector, note)
    """
    if not rule.startswith("{"):
        return None, "not_json"
    try:
        obj = json.loads(rule)
    except Exception as e:
        return None, f"json_parse_failed: {type(e).__name__}"
    article_list = obj.get("articleList") or obj.get("article_list") or obj.get("list")
    if not article_list:
        return None, "no_articleList_field"
    # articleList 可能是 "selector" 或 "selector@sub" 或 "@CSS:..."
    # 处理 @ 分隔的多段
    if article_list.startswith("@CSS:"):
        return article_list[5:].strip(), "ok"
    if article_list.startswith("@XPath:") or article_list.startswith("@JSON:"):
        return None, "xpath_or_json_not_supported"
    # 处理 class./id./tag. 前缀
    return convert_legado_selector_to_css(article_list), "ok"


def convert_legado_selector_to_css(sel: str) -> Optional[str]:
    """把 legado 选择器转换为标准 CSS。"""
    if not sel:
        return None
    sel = sel.strip()
    # 去掉索引 [!0:3]
    sel_no_idx = re.sub(r"\[[\!\d:\-\s,]*\]$", "", sel)
    # 处理 @ 分隔：取第一段（多段比较复杂，简化）
    if "@" in sel_no_idx:
        parts = sel_no_idx.split("@")
        css_list = []
        for p in parts:
            p = p.strip()
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
        return "." + cls.replace(".", ".") if cls else None
    if seg_no_idx.startswith("id."):
        idv = seg_no_idx[len("id."):]
        return "#" + idv.split(".")[0] if idv else None
    if seg_no_idx.startswith("tag."):
        tag = seg_no_idx[len("tag."):]
        return tag.split(".")[0] if tag else None
    if seg_no_idx.startswith("text."):
        return None
    # CSS 直接返回
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


def main():
    print("=" * 60)
    print("补丁: 重新验证 JSON 格式 ruleArticles 源")
    print("=" * 60)

    # 加载结果
    with open(RESULT_JSON, "r", encoding="utf-8") as f:
        result_data = json.load(f)
    results = result_data["results"]

    # 加载源数据
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # 找出 JSON 格式规则且之前 html_len > 0 的源（这些可以重新验证）
    json_indices = []
    for r in results:
        rule = r.get("rule_articles_raw", "")
        if rule.startswith("{") and "articleList" in rule:
            # 之前有 html 内容
            if r.get("page_html_length", 0) > 10000:
                json_indices.append(r["idx"])
            # 但如果原 rule_type 是 unknown 且 html_len == 0，跳过（网络问题）

    print(f"[INFO] 需要重新验证的 JSON 格式源: {len(json_indices)}")
    print(f"[INFO] JSON 格式源总览:")
    json_total = 0
    json_network_fail = 0
    for r in results:
        rule = r.get("rule_articles_raw", "")
        if rule.startswith("{") and "articleList" in rule:
            json_total += 1
            if r.get("page_html_length", 0) == 0:
                json_network_fail += 1
    print(f"  总数: {json_total}")
    print(f"  网络/异常失败(html_len=0): {json_network_fail}")
    print(f"  可重新验证(html_len>10000): {len(json_indices)}")

    if not json_indices:
        print("[INFO] 没有需要重新验证的源")
        return

    patch_log_lines = []

    with sync_playwright() as pw:
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

        for idx in json_indices:
            src = sources[idx]
            url = src.get("sourceUrl", "")
            rule = src.get("ruleArticles", "")
            css_sel, note = extract_article_list_from_json_rule(rule)
            log_line = (f"idx={idx}  note={note}  css={css_sel!r}  "
                        f"url_len={len(url)}")
            print(log_line)
            patch_log_lines.append(log_line)

            if not css_sel:
                # JSON 解析失败，保持原结果
                continue

            # 重新访问
            try:
                start = time.time()
                resp = page.goto(url, wait_until="domcontentloaded",
                                 timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(int(WAIT_AFTER_LOAD_SEC * 1000))
                title = page.title() or ""
                html = page.content() or ""
                elapsed = round(time.time() - start, 2)

                has_cf, has_login = detect_markers(html, title)
                soup = BeautifulSoup(html, "lxml")

                try:
                    elements = soup.select(css_sel)
                    match_count = len(elements)
                except Exception:
                    match_count = 0

                # 更新结果
                r = results[idx]
                r["css_converted"] = [css_sel]
                r["rule_type"] = "css_from_json"
                r["rule_match_count"] = match_count
                r["page_html_length"] = len(html)
                r["page_title_length"] = len(title)
                r["status_code"] = resp.status if resp else None
                r["elapsed_sec"] = elapsed
                r["error"] = ""

                if match_count >= 1:
                    r["status"] = "ok"
                    r["failure_reason"] = ""
                    r["common_selectors"] = []
                else:
                    common = find_common_selector(soup)
                    r["common_selectors"] = common
                    r["status"] = "fail"
                    network_ok = (resp is not None and 200 <= resp.status < 500)
                    if has_cf:
                        r["failure_reason"] = "cf_shield"
                    elif has_login:
                        r["failure_reason"] = "login_required"
                    elif network_ok and resp.status == 200:
                        if len(html) < 5000:
                            r["failure_reason"] = "empty_content"
                        elif common:
                            r["failure_reason"] = "rule_mismatch"
                        else:
                            r["failure_reason"] = "empty_content"
                    else:
                        r["failure_reason"] = "network_fail"

                pl = (f"  -> status={r['status']}  reason={r['failure_reason']}  "
                      f"match={match_count}  html_len={len(html)}  "
                      f"status_code={r['status_code']}  elapsed={elapsed}s")
                print(pl)
                patch_log_lines.append(pl)

            except PlaywrightTimeout:
                # 超时，保持原结果但更新 note
                results[idx]["error"] = "patch_timeout"
                patch_log_lines.append("  -> patch_timeout")
                print("  -> patch_timeout")
            except Exception as e:
                results[idx]["error"] = f"patch_failed: {type(e).__name__}: {str(e)[:100]}"
                patch_log_lines.append(f"  -> patch_failed: {type(e).__name__}")
                print(f"  -> patch_failed: {type(e).__name__}")

        try:
            page.close()
            ctx.close()
            browser.close()
        except Exception:
            pass

    # 保存更新后的 result.json
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    # 保存补丁日志
    with open(PATCH_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(patch_log_lines))

    # 统计补丁后结果
    ok = sum(1 for x in results if x.get("status") == "ok")
    fail = sum(1 for x in results if x.get("status") == "fail")
    from collections import Counter
    by_reason = Counter(x.get("failure_reason", "") for x in results if x.get("status") == "fail")
    print()
    print("=" * 60)
    print(f"[PATCH FINAL] 总计 {len(results)}  成功 {ok}  失败 {fail}")
    print(f"[PATCH FINAL] 失败原因: {dict(by_reason)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
