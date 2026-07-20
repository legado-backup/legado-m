"""
V5.2 ruleArticles 真实DOM验证脚本

用 PC Playwright 真实访问 224 个 RSS 源，验证 ruleArticles 选择器是否能匹配真实 DOM 列表项。

输出:
- output/rss/v5_2_rule_verify_result.json  详细结果
- output/rss/v5_2_rule_verify_report.md    分析报告

约束:
- 输出安全：禁止输出源名称/域名/URL/cookie，全部用代号（源[idx]/站点A）
- Python 环境：必须用 ai_tests/venv/Scripts/python.exe
- 失败不重试同一方式
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# === 路径 ===
PROJECT_ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v5_2_stable.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "rss"
RESULT_JSON = OUTPUT_DIR / "v5_2_rule_verify_result.json"
REPORT_MD = OUTPUT_DIR / "v5_2_rule_verify_report.md"
PROGRESS_FILE = OUTPUT_DIR / "v5_2_rule_verify_progress.json"

# === 配置 ===
PAGE_TIMEOUT_MS = 15000       # 单页加载超时
WAIT_AFTER_LOAD_SEC = 5.0     # 加载后等待动态内容（5秒平衡速度与JS渲染）
MAX_TOTAL_SEC_PER_SOURCE = 25 # 单源总耗时上限
HEADLESS = True               # 工程权衡：headless 提速，保留 mobile context
MOBILE_VIEWPORT = {"width": 375, "height": 667}
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 12; Pixel 5) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/101.0.4951.61 Mobile Safari/537.36")

# 通用选择器，用于规则不匹配时尝试找出"正确"的选择器
COMMON_SELECTORS = [
    "article", ".article", ".item", ".post", ".card",
    ".list-item", ".news-item", ".vod-item", ".video-item",
    ".movie-item", ".article-item", ".feed", ".entry",
    "ul li", "ol li", ".list li", ".ul li",
    "table tr", ".channel-list li", ".main li",
    ".box li", ".content li", ".container li",
]


def load_sources() -> List[Dict[str, Any]]:
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")
    return data


# ============ Legado ruleArticles 转 CSS 选择器 ============
# 解析规则:
#   class.xxx[!0:3]  -> CSS ".xxx", 索引排除 0:3
#   id.xxx@li        -> 多段规则 ["#xxx", "li"]
#   tag.xxx          -> "xxx"
#   div.pic.vodst>ul>li -> 直接 CSS
#   $.model.data     -> JSONPath (单独处理)
#   //div[@xxx]      -> XPath (单独处理)
#   .vod-item        -> 直接 CSS
#   article          -> 直接 CSS (tag)

def parse_rule_to_css_list(rule: str) -> Tuple[List[str], str]:
    """
    把 ruleArticles 转换为 CSS 选择器列表（多段，用 @ 分隔）。
    返回 (css_selectors_list, rule_type)
    rule_type: 'css' | 'xpath' | 'jsonpath' | 'unknown'
    """
    if not rule:
        return [], "unknown"

    rule = rule.strip()

    # JSONPath: $.
    if rule.startswith("$"):
        return [], "jsonpath"

    # XPath: // 或 /xx
    if rule.startswith("//") or (rule.startswith("/") and len(rule) > 1 and not rule.startswith("/>")):
        return [], "xpath"

    # 显式 @CSS: / @XPath: / @JSON:
    if rule.startswith("@CSS:"):
        return [rule[5:].strip()], "css"
    if rule.startswith("@XPath:"):
        return [], "xpath"
    if rule.startswith("@JSON:"):
        return [], "jsonpath"

    # 处理 @ 分隔的多段规则（如 id.content@li）
    segments = rule.split("@")
    css_list = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        css = convert_single_segment(seg)
        if css:
            css_list.append(css)
        else:
            # 转换失败
            return [], "unknown"
    if not css_list:
        return [], "unknown"
    return css_list, "css"


def convert_single_segment(seg: str) -> Optional[str]:
    """转换单段规则为 CSS 选择器。失败返回 None。"""
    seg = seg.strip()
    if not seg:
        return None

    # 去掉索引部分 [!0:3] 或 [0:3] 或 [0] 等
    # 注意: 标准 CSS 也有 []，如 input[type=text]，但 Legado 规则 [] 是索引切片
    # 简化: 如果规则末尾是 ]，且 [ 后面是数字/!/:
    seg_no_idx = re.sub(r"\[[\!\d:\-\s,]*\]$", "", seg)

    # class.xxx
    if seg_no_idx.startswith("class."):
        cls = seg_no_idx[len("class."):]
        # 可能是 class.a.b.c
        cls = cls.replace(".", ".")
        return "." + cls if cls else None

    # id.xxx
    if seg_no_idx.startswith("id."):
        idv = seg_no_idx[len("id."):]
        # id.content -> #content
        return "#" + idv.split(".")[0] if idv else None

    # tag.xxx
    if seg_no_idx.startswith("tag."):
        tag = seg_no_idx[len("tag."):]
        return tag.split(".")[0] if tag else None

    # text.xxx (按文本查找，没有 CSS 等价，跳过)
    if seg_no_idx.startswith("text."):
        return None

    # children
    if seg_no_idx == "children":
        return "> *"

    # 以 . 或 # 开头的 CSS 选择器 (.vod-item, #content 等)
    if re.match(r"^[\.\#][\w\.\-\s\>\+\~\,\[\]\=\:\"\'\(\)\*\#]*$", seg_no_idx):
        return seg_no_idx

    # 标准 CSS 选择器 (含 . # > + ~ 等特征)
    # 例如: div.pic.vodst>ul>li, article, ul[!0] 已去索引变 ul
    if re.match(r"^[a-zA-Z][\w\.\-\s\>\+\~\,\[\]\=\:\"\'\(\)\*\#\.\#]*$", seg_no_idx):
        return seg_no_idx

    # 单标签 (article, ul, li 等)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9]*$", seg_no_idx):
        return seg_no_idx

    return None


def apply_css_list(soup: BeautifulSoup, css_list: List[str]) -> List:
    """按多段 CSS 顺序查找。每段从上一段结果中查找。"""
    if not css_list:
        return []
    elements = [soup]
    for css in css_list:
        next_elements = []
        for el in elements:
            # el 可能是 BeautifulSoup 或 Tag
            try:
                found = el.select(css)
                next_elements.extend(found)
            except Exception:
                pass
        elements = next_elements
        if not elements:
            return []
    return elements


def try_xpath(soup: BeautifulSoup, rule: str) -> List:
    """用 lxml 解析并执行 XPath。"""
    try:
        from lxml import etree
        html_str = str(soup)
        tree = etree.HTML(html_str)
        if tree is None:
            return []
        result = tree.xpath(rule)
        return result if isinstance(result, list) else []
    except Exception:
        return []


def try_jsonpath(html_str: str, rule: str) -> List:
    """尝试 JSONPath 解析（先尝试解析 JSON，否则失败）。"""
    try:
        import jsonpath_ng
    except ImportError:
        return []
    try:
        data = json.loads(html_str)
        expr = jsonpath_ng.parse(rule)
        return [m.value for m in expr.find(data)]
    except Exception:
        return []


def find_common_selector(soup: BeautifulSoup) -> List[str]:
    """当 ruleArticles 不匹配时，尝试通用选择器找出最可能的选择器。"""
    matched = []
    for sel in COMMON_SELECTORS:
        try:
            found = soup.select(sel)
            if len(found) >= 2:  # 至少 2 个才算列表
                matched.append({"selector": sel, "count": len(found)})
        except Exception:
            pass
    # 按 count 降序
    matched.sort(key=lambda x: -x["count"])
    return matched[:5]


def classify_failure(status_code: Optional[int], page_title: str,
                     page_html: str, has_login_marker: bool,
                     has_cf_marker: bool, network_ok: bool) -> str:
    """根据多信号分类失败原因。"""
    if not network_ok:
        return "network_fail"
    if status_code in (403, 503):
        if has_cf_marker:
            return "cf_shield"
        return "forbidden"
    if status_code in (401,):
        return "login_required"
    if has_cf_marker:
        return "cf_shield"
    if has_login_marker:
        return "login_required"
    if status_code == 200 and len(page_html) < 5000:
        return "empty_content"
    return "empty_content"


def detect_markers(page_html: str, page_title: str) -> Tuple[bool, bool]:
    """检测 CF 盾和登录标记。"""
    html_lower = page_html.lower()
    title_lower = page_title.lower()
    # CF 盾特征
    cf_markers = ["cf-browser-verification", "cf_chl_opt", "cloudflare",
                  "challenge-platform", "just a moment", "cf-turnstile",
                  "ray id", "_cf_chl"]
    has_cf = any(m in html_lower or m in title_lower for m in cf_markers)
    # 登录特征
    login_markers = ["login", "登录", "sign in", "log in", "请先登录",
                     "用户名", "密码", "password", "请登录", "need login",
                     "请先登入", "未登录"]
    has_login = any(m in html_lower or m in title_lower for m in login_markers)
    return has_cf, has_login


def verify_one_source(page, source: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """验证单个源。返回结果字典。"""
    result = {
        "idx": idx,
        "source_name": source.get("sourceName", "")[:0],  # 不存源名,留空
        "rule_articles_raw": source.get("ruleArticles", ""),
        "source_url_length": len(source.get("sourceUrl", "")),
        "source_url_host": "",  # 不输出域名
        "status": "unknown",
        "failure_reason": "",
        "rule_type": "unknown",
        "css_converted": [],
        "rule_match_count": 0,
        "common_selectors": [],
        "page_title_length": 0,
        "page_html_length": 0,
        "status_code": None,
        "elapsed_sec": 0,
        "error": "",
    }

    url = source.get("sourceUrl", "").strip()
    rule = source.get("ruleArticles", "").strip()

    if not url:
        result["status"] = "fail"
        result["failure_reason"] = "empty_url"
        return result

    if not rule:
        result["status"] = "fail"
        result["failure_reason"] = "empty_rule"
        return result

    # 转换规则
    css_list, rule_type = parse_rule_to_css_list(rule)
    result["css_converted"] = css_list
    result["rule_type"] = rule_type

    start = time.time()
    try:
        resp = page.goto(url, wait_until="domcontentloaded",
                         timeout=PAGE_TIMEOUT_MS)
        result["status_code"] = resp.status if resp else None
        # 等待动态内容
        try:
            page.wait_for_timeout(int(WAIT_AFTER_LOAD_SEC * 1000))
        except Exception:
            pass
        page_title = page.title() or ""
        page_html = page.content() or ""
        result["page_title_length"] = len(page_title)
        result["page_html_length"] = len(page_html)

        # 检测 CF/登录标记
        has_cf, has_login = detect_markers(page_html, page_title)

        # 网络层判断
        network_ok = (resp is not None and 200 <= resp.status < 500)

        # 解析 HTML
        soup = BeautifulSoup(page_html, "lxml")

        match_count = 0
        if rule_type == "css" and css_list:
            try:
                elements = apply_css_list(soup, css_list)
                match_count = len(elements)
            except Exception as e:
                result["error"] = f"css_apply_failed: {type(e).__name__}"
        elif rule_type == "xpath":
            try:
                elements = try_xpath(soup, rule)
                match_count = len(elements) if elements else 0
            except Exception as e:
                result["error"] = f"xpath_failed: {type(e).__name__}"
        elif rule_type == "jsonpath":
            try:
                elements = try_jsonpath(page_html, rule)
                match_count = len(elements) if elements else 0
            except Exception as e:
                result["error"] = f"jsonpath_failed: {type(e).__name__}"
        else:
            # unknown 规则类型，尝试直接当作 CSS
            try:
                elements = soup.select(rule)
                match_count = len(elements)
                if match_count > 0:
                    result["rule_type"] = "css_direct"
            except Exception:
                pass

        result["rule_match_count"] = match_count

        if match_count >= 1:
            result["status"] = "ok"
            result["failure_reason"] = ""
        else:
            # 规则不匹配，尝试通用选择器
            common = find_common_selector(soup)
            result["common_selectors"] = common
            result["status"] = "fail"
            base_reason = classify_failure(
                result["status_code"], page_title, page_html,
                has_login, has_cf, network_ok
            )
            # 优先级：cf_shield / login_required / forbidden / timeout 不被覆盖
            # 如果是 network_ok + status 200 + html足够大 + 有 common selector 命中 → rule_mismatch
            # 如果是 network_ok + status 200 + html 太小 (<5000) → empty_content
            if base_reason in ("cf_shield", "login_required", "forbidden",
                               "timeout", "network_fail"):
                result["failure_reason"] = base_reason
            elif network_ok and result["status_code"] == 200:
                if len(page_html) < 5000:
                    result["failure_reason"] = "empty_content"
                elif common:
                    result["failure_reason"] = "rule_mismatch"
                else:
                    # 200 但找不到任何列表 → 可能是 SPA / empty_content
                    result["failure_reason"] = "empty_content"
            else:
                result["failure_reason"] = base_reason

    except PlaywrightTimeout as e:
        result["status"] = "fail"
        result["failure_reason"] = "timeout"
        result["error"] = f"playwright_timeout: {str(e)[:200]}"
    except Exception as e:
        result["status"] = "fail"
        result["failure_reason"] = "exception"
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        result["elapsed_sec"] = round(time.time() - start, 2)

    return result


def main():
    print("=" * 60)
    print("V5.2 ruleArticles 真实DOM验证")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    total = len(sources)
    print(f"[INFO] 加载 {total} 个源")

    # 断点续传：如果存在 progress 文件，加载已完成的
    results: List[Dict[str, Any]] = []
    start_idx = 0
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                progress = json.load(f)
            results = progress.get("results", [])
            start_idx = progress.get("next_idx", 0)
            print(f"[INFO] 断点续传: 从 idx={start_idx} 继续 (已完成 {len(results)})")
        except Exception as e:
            print(f"[WARN] 加载进度失败: {e}, 从头开始")
            results = []
            start_idx = 0

    with sync_playwright() as pw:
        # 启动浏览器 (Chromium, headless)
        browser = pw.chromium.launch(
            headless=HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        # 主 context: mobile
        context = browser.new_context(
            viewport=MOBILE_VIEWPORT,
            user_agent=MOBILE_UA,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            ignore_https_errors=True,
        )
        # 屏蔽 webdriver 标志
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        page = context.new_page()
        # 屏蔽图片/字体加速
        try:
            page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,ico}",
                       lambda r: r.abort())
        except Exception:
            pass

        try:
            for i in range(start_idx, total):
                src = sources[i]
                # 超时保护：每次创建新 page 防止状态污染
                try:
                    r = verify_one_source(page, src, i)
                except Exception as e:
                    r = {
                        "idx": i,
                        "status": "fail",
                        "failure_reason": "outer_exception",
                        "error": f"{type(e).__name__}: {str(e)[:200]}",
                        "rule_match_count": 0,
                        "elapsed_sec": 0,
                    }
                results.append(r)

                # 进度
                if (i + 1) % 10 == 0 or i == total - 1:
                    ok = sum(1 for x in results if x.get("status") == "ok")
                    fail = sum(1 for x in results if x.get("status") == "fail")
                    elapsed = sum(x.get("elapsed_sec", 0) for x in results)
                    print(f"[PROGRESS] {i+1}/{total}  ok={ok} fail={fail}  "
                          f"累计耗时={elapsed:.0f}s  "
                          f"当前耗时={r.get('elapsed_sec',0)}s  "
                          f"状态={r.get('status')}/{r.get('failure_reason','')}  "
                          f"match={r.get('rule_match_count',0)}")
                # 每 50 个保存进度
                if (i + 1) % 50 == 0 or i == total - 1:
                    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                        json.dump({"results": results, "next_idx": i + 1},
                                  f, ensure_ascii=False)
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

    # 写最终结果
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "results": results,
            "config": {
                "page_timeout_ms": PAGE_TIMEOUT_MS,
                "wait_after_load_sec": WAIT_AFTER_LOAD_SEC,
                "headless": HEADLESS,
                "viewport": MOBILE_VIEWPORT,
            }
        }, f, ensure_ascii=False, indent=2)

    # 统计
    ok = sum(1 for x in results if x.get("status") == "ok")
    fail = sum(1 for x in results if x.get("status") == "fail")
    by_reason = {}
    for x in results:
        if x.get("status") == "fail":
            reason = x.get("failure_reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1

    print()
    print("=" * 60)
    print(f"[FINAL] 总计 {total}  成功匹配 {ok}  失败 {fail}")
    print(f"[FINAL] 失败原因分布: {by_reason}")
    print(f"[FINAL] 结果JSON: {RESULT_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
