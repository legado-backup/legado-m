# -*- coding: utf-8 -*-
"""
重试访问失败的 RSS 订阅源。
- 读取真机 DB 所有 183 条源
- 用 Playwright 逐个访问 sourceUrl 识别所有失败源
- 对每个失败源用 14 种技术手段依次重试
- 输出脱敏后的 JSON 报告

输出安全铁律：
- 脚本输出禁止包含源名称 / URL / 分类名原文
- 异常消息必须正则脱敏（URL→[URL]，域名→[DOMAIN]，IP→[IP]）
- 用 源[idx] 替代真实名称
"""
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

# ============ 路径配置 ============
DB_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\legado_test.db"
OUTPUT_DIR = Path(r"f:\myself\github\WeAgentChat\temp\legado\output\rss")
OUTPUT_FILE = OUTPUT_DIR / "failed_source_retry_v2.json"
INCREMENT_FILE = OUTPUT_DIR / "failed_source_retry_v2.inc.json"
FAILED_LIST_FILE = OUTPUT_DIR / "failed_sources_list.json"
LOG_FILE = OUTPUT_DIR / "retry_run.log"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============ 5 种 UA ============
USER_AGENTS = {
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
}

# ============ 脱敏函数 ============
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b[a-z0-9\-]+\.[a-z]{2,}(?:[^\s]*)?", re.IGNORECASE)
IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def sanitize(msg):
    """脱敏：URL / 域名 / IP / 邮箱"""
    if not msg:
        return ""
    s = str(msg)
    s = URL_RE.sub("[URL]", s)
    s = EMAIL_RE.sub("[EMAIL]", s)
    s = IP_RE.sub("[IP]", s)
    # 域名替换放在 URL 之后，避免重复匹配
    s = DOMAIN_RE.sub("[DOMAIN]", s)
    return s


def log(msg, level="INFO"):
    """统一日志（脱敏后写入文件 + 控制台）"""
    safe = sanitize(msg)
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {safe}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ============ Stage 1: 读取 DB 所有源 ============
def load_all_sources():
    """读取 DB 所有 183 条源，仅返回脱敏字段"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT sourceUrl, customOrder, type FROM rssSources ORDER BY customOrder ASC")
    rows = cur.fetchall()
    conn.close()
    sources = []
    for i, (url, order, type_) in enumerate(rows):
        sources.append({
            "idx": i + 1,
            "source_url": url or "",
            "custom_order": order,
            "type": type_,
        })
    return sources


# ============ Stage 2: 访问检查 ============
def classify_error(err_msg):
    """根据错误消息归类错误类型"""
    m = (err_msg or "").lower()
    if "ssl" in m or "cert" in m or "ERR_CERT" in err_msg or "ERR_SSL" in err_msg:
        return "ssl_protocol_error"
    if "tunnel" in m or "proxy" in m:
        return "tunnel_connection_failed"
    if "name_not_resolved" in m or "ns_error_unknown_host" in m or "dns" in m or "ERR_NAME_NOT_RESOLVED" in err_msg:
        return "dns_error"
    if "connection_refused" in m or "ERR_CONNECTION_REFUSED" in err_msg:
        return "connection_refused"
    if "timeout" in m or "timed out" in m:
        return "timeout"
    if "aborted" in m:
        return "aborted"
    return "other_error"


def count_list_items(page):
    """简单探测列表条目数"""
    max_items = 0
    selectors = ["article", "[class*='item']", "[class*='article']", "li", ".post", ".entry", ".list-item", "item"]
    for sel in selectors:
        try:
            items = page.query_selector_all(sel)
            n = len(items) if items else 0
            if n > max_items:
                max_items = n
            if max_items > 3:
                break
        except Exception:
            pass
    return max_items


def check_url(browser, url, timeout=15000, wait_until="domcontentloaded",
              extra_headers=None, ignore_https_errors=False, is_mobile=False,
              viewport=None, ua=None, stealth=False):
    """
    统一访问检查。返回 dict:
    {accessible, error_type, error_raw, status_code, list_items, final_url}
    """
    result = {"accessible": False, "error_type": "unknown", "error_raw": "",
              "status_code": 0, "list_items": 0, "final_url": ""}
    if not url or not url.strip():
        result["error_type"] = "empty_url"
        return result

    ctx_opts = {
        "ignore_https_errors": ignore_https_errors,
        "user_agent": ua or USER_AGENTS["chrome"],
        "viewport": viewport or {"width": 1280, "height": 800},
        "is_mobile": is_mobile,
        "extra_http_headers": extra_headers or {},
    }
    ctx = None
    page = None
    try:
        ctx = browser.new_context(**ctx_opts)
        page = ctx.new_page()
        if stealth:
            try:
                page.add_init_script(STEALTH_JS)
            except Exception:
                pass
        resp = page.goto(url, wait_until=wait_until, timeout=timeout)
        status = resp.status if resp else 0
        result["status_code"] = status
        if status >= 400:
            result["error_type"] = f"http_{status}"
            result["error_raw"] = f"HTTP {status}"
            return result
        try:
            result["final_url"] = page.url or ""
        except Exception:
            pass
        result["list_items"] = count_list_items(page)
        result["accessible"] = True
        result["error_type"] = "ok"
        return result
    except PlaywrightTimeoutError as e:
        result["error_type"] = "timeout"
        result["error_raw"] = str(e)
        return result
    except PlaywrightError as e:
        result["error_type"] = classify_error(str(e))
        result["error_raw"] = str(e)
        return result
    except Exception as e:
        result["error_type"] = classify_error(str(e))
        result["error_raw"] = str(e)
        return result
    finally:
        try:
            if page:
                page.close()
        except Exception:
            pass
        try:
            if ctx:
                ctx.close()
        except Exception:
            pass


STEALTH_JS = r"""
() => {
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
    window.chrome = {runtime: {}};
}
"""


# ============ Stage 3: 识别所有失败源 ============
def scan_all_sources(sources, browser, max_test=None):
    """扫描所有源，返回 (failed_list, ok_count)
    failed_list: [{idx, source_url, original_error, original_status}]
    """
    failed = []
    ok_count = 0
    total = len(sources) if max_test is None else min(max_test, len(sources))
    log(f"开始扫描全部 {total} 条源（默认UA+15s超时）")
    for i, src in enumerate(sources[:total] if max_test else sources):
        idx = src["idx"]
        url = src["source_url"]
        if not url:
            log(f"源[{idx}] 空URL，跳过（标记失败）")
            failed.append({"idx": idx, "source_url": url, "original_error": "empty_url",
                           "original_status": 0, "custom_order": src.get("custom_order"),
                           "type": src.get("type")})
            continue
        r = check_url(browser, url, timeout=15000)
        if r["accessible"]:
            ok_count += 1
            log(f"源[{idx}] OK status={r['status_code']} items={r['list_items']}")
        else:
            failed.append({"idx": idx, "source_url": url,
                           "original_error": r["error_type"],
                           "original_status": r["status_code"],
                           "custom_order": src.get("custom_order"),
                           "type": src.get("type")})
            log(f"源[{idx}] FAIL type={r['error_type']} status={r['status_code']}")
        # 保存失败列表增量
        if (i + 1) % 5 == 0:
            save_json(FAILED_LIST_FILE, {"total_scanned": i + 1, "failed_count": len(failed),
                                          "failed": failed})
    save_json(FAILED_LIST_FILE, {"total_scanned": total, "failed_count": len(failed),
                                  "failed": failed})
    log(f"扫描完成：总{total} 成功{ok_count} 失败{len(failed)}")
    return failed, ok_count


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存文件失败 {path}: {e}", "ERROR")


# ============ Stage 4: 14 种手段重试 ============
# 每个方法返回 dict: {method_name, ok(bool), accessible(bool), list_items, status_code,
#                    error_type, error_raw, final_url, notes}

def m01_http_downgrade(browser, url):
    if url.startswith("https://"):
        new_url = "http://" + url[len("https://"):]
        r = check_url(browser, new_url, timeout=15000, ignore_https_errors=False)
        return {"method_name": "http_downgrade", "ok": r["accessible"], "accessible": r["accessible"],
                "list_items": r["list_items"], "status_code": r["status_code"],
                "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
                "notes": "https→http"}
    return {"method_name": "http_downgrade", "ok": False, "accessible": False, "list_items": 0,
            "status_code": 0, "error_type": "skip", "error_raw": "url非https，跳过",
            "final_url": "", "notes": "url非https"}


def m02_wayback(browser, url):
    new_url = f"https://web.archive.org/web/2024/{url}"
    r = check_url(browser, new_url, timeout=25000)  # Wayback 较慢
    return {"method_name": "wayback", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "web.archive.org/web/2024"}


def m03_google_cache(browser, url):
    new_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
    r = check_url(browser, new_url, timeout=20000)
    return {"method_name": "google_cache", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "webcache.googleusercontent.com"}


def m04_common_crawl(browser, url):
    """Common Crawl：访问索引 API，如果命中则尝试获取实际快照"""
    index_url = f"https://index.commoncrawl.org/CC-MAIN-2024-10-index?url={url}&output=json"
    # 先获取索引
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(index_url, headers={"User-Agent": USER_AGENTS["chrome"]})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        if not body.strip():
            return {"method_name": "common_crawl", "ok": False, "accessible": False, "list_items": 0,
                    "status_code": 0, "error_type": "no_index", "error_raw": "empty body",
                    "final_url": "", "notes": "CC索引返回空"}
        # 解析每行 JSON
        lines = [l for l in body.splitlines() if l.strip()]
        if not lines:
            return {"method_name": "common_crawl", "ok": False, "accessible": False, "list_items": 0,
                    "status_code": 0, "error_type": "no_index", "error_raw": "no lines",
                    "final_url": "", "notes": "CC索引无行"}
        first = json.loads(lines[0])
        if "url" not in first:
            return {"method_name": "common_crawl", "ok": False, "accessible": False, "list_items": 0,
                    "status_code": 0, "error_type": "no_snapshot", "error_raw": "无url字段",
                    "final_url": "", "notes": "CC索引无快照"}
        # 访问快照
        snapshot_url = first["url"]
        r = check_url(browser, snapshot_url, timeout=20000)
        return {"method_name": "common_crawl", "ok": r["accessible"], "accessible": r["accessible"],
                "list_items": r["list_items"], "status_code": r["status_code"],
                "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
                "notes": "CC快照访问"}
    except urllib.error.HTTPError as e:
        return {"method_name": "common_crawl", "ok": False, "accessible": False, "list_items": 0,
                "status_code": e.code, "error_type": f"http_{e.code}", "error_raw": str(e),
                "final_url": "", "notes": "CC索引HTTP错误"}
    except Exception as e:
        return {"method_name": "common_crawl", "ok": False, "accessible": False, "list_items": 0,
                "status_code": 0, "error_type": classify_error(str(e)), "error_raw": str(e),
                "final_url": "", "notes": "CC索引异常"}


def m05_ua_chrome(browser, url):
    r = check_url(browser, url, timeout=15000, ua=USER_AGENTS["chrome"])
    return {"method_name": "ua_chrome", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "UA=Chrome/120"}


def m06_ua_firefox(browser, url):
    r = check_url(browser, url, timeout=15000, ua=USER_AGENTS["firefox"])
    return {"method_name": "ua_firefox", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "UA=Firefox/120"}


def m07_ua_edge(browser, url):
    r = check_url(browser, url, timeout=15000, ua=USER_AGENTS["edge"])
    return {"method_name": "ua_edge", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "UA=Edge/120"}


def m08_ua_safari(browser, url):
    r = check_url(browser, url, timeout=15000, ua=USER_AGENTS["safari"])
    return {"method_name": "ua_safari", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "UA=Safari/17"}


def m09_ua_mobile(browser, url):
    r = check_url(browser, url, timeout=15000, ua=USER_AGENTS["mobile"],
                  viewport={"width": 375, "height": 667}, is_mobile=True)
    return {"method_name": "ua_mobile", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "UA=Mobile"}


def m10_referer(browser, url):
    r = check_url(browser, url, timeout=15000,
                  extra_headers={"Referer": "https://www.google.com/"})
    return {"method_name": "referer", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "Referer=google"}


def m11_prefetch_cookie(browser, url):
    """预取 cookie：先访问首页再访问目标URL"""
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        home = f"{p.scheme}://{p.netloc}/"
    except Exception:
        home = url
    ctx = None
    page = None
    try:
        ctx = browser.new_context(user_agent=USER_AGENTS["chrome"],
                                   viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        try:
            page.goto(home, wait_until="domcontentloaded", timeout=12000)
        except Exception:
            pass  # 首页失败也继续
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = resp.status if resp else 0
            if status >= 400:
                return {"method_name": "prefetch_cookie", "ok": False, "accessible": False,
                        "list_items": 0, "status_code": status, "error_type": f"http_{status}",
                        "error_raw": f"HTTP {status}", "final_url": page.url or "", "notes": "预取cookie后访问"}
            items = count_list_items(page)
            return {"method_name": "prefetch_cookie", "ok": True, "accessible": True,
                    "list_items": items, "status_code": status, "error_type": "ok",
                    "error_raw": "", "final_url": page.url or "", "notes": "预取cookie后访问"}
        except Exception as e:
            return {"method_name": "prefetch_cookie", "ok": False, "accessible": False,
                    "list_items": 0, "status_code": 0, "error_type": classify_error(str(e)),
                    "error_raw": str(e), "final_url": "", "notes": "预取cookie异常"}
    except Exception as e:
        return {"method_name": "prefetch_cookie", "ok": False, "accessible": False,
                "list_items": 0, "status_code": 0, "error_type": classify_error(str(e)),
                "error_raw": str(e), "final_url": "", "notes": "ctx创建失败"}
    finally:
        try:
            if page: page.close()
        except Exception: pass
        try:
            if ctx: ctx.close()
        except Exception: pass


def m12_disable_tls(browser, url):
    r = check_url(browser, url, timeout=15000, ignore_https_errors=True)
    return {"method_name": "disable_tls", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "ignore_https_errors=True"}


def m13_proxy_7890(browser, url):
    """代理 127.0.0.1:7890（Clash）"""
    # 需要在 browser.launch 时配置，这里用新 browser
    # 实际通过 launch 重开
    result = {"method_name": "proxy_7890", "ok": False, "accessible": False, "list_items": 0,
              "status_code": 0, "error_type": "skip", "error_raw": "无代理browser",
              "final_url": "", "notes": "需要独立browser"}
    try:
        with sync_playwright() as pw:
            try:
                br = pw.chromium.launch(headless=True, proxy={"server": "http://127.0.0.1:7890"})
            except Exception as e:
                result["error_type"] = "proxy_launch_fail"
                result["error_raw"] = str(e)
                return result
            try:
                r = check_url(br, url, timeout=15000)
                result.update({"ok": r["accessible"], "accessible": r["accessible"],
                               "list_items": r["list_items"], "status_code": r["status_code"],
                               "error_type": r["error_type"], "error_raw": r["error_raw"],
                               "final_url": r["final_url"], "notes": "proxy=127.0.0.1:7890"})
            finally:
                try: br.close()
                except Exception: pass
    except Exception as e:
        result["error_type"] = classify_error(str(e))
        result["error_raw"] = str(e)
    return result


def m14_mobile_context(browser, url):
    r = check_url(browser, url, timeout=15000, is_mobile=True,
                  viewport={"width": 375, "height": 667}, ua=USER_AGENTS["mobile"])
    return {"method_name": "mobile_context", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "mobile context 375x667"}


def m15_long_timeout(browser, url):
    r = check_url(browser, url, timeout=30000, wait_until="networkidle")
    return {"method_name": "long_timeout", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "30s+networkidle"}


def m16_stealth_js(browser, url):
    r = check_url(browser, url, timeout=15000, stealth=True)
    return {"method_name": "stealth_js", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "stealth.js注入"}


def m17_accept_encoding(browser, url):
    r = check_url(browser, url, timeout=15000,
                  extra_headers={"Accept-Encoding": "gzip, deflate",
                                  "Accept-Language": "zh-CN,zh;q=0.9"})
    return {"method_name": "accept_encoding", "ok": r["accessible"], "accessible": r["accessible"],
            "list_items": r["list_items"], "status_code": r["status_code"],
            "error_type": r["error_type"], "error_raw": r["error_raw"], "final_url": r["final_url"],
            "notes": "Accept-Encoding+zh-CN"}


def m18_doh_marker(browser, url):
    """DNS-over-HTTPS 标记手段（Playwright 不能直接配置，仅做标记）"""
    return {"method_name": "doh_marker", "ok": False, "accessible": False, "list_items": 0,
            "status_code": 0, "error_type": "skip", "error_raw": "DoH在Playwright层无法实现",
            "final_url": "", "notes": "DNS-over-HTTPS标记用，无实际效果"}


# 14 种手段的执行顺序（合并5种UA为"UA伪装"一组，编号按任务要求）
RETRY_METHODS = [
    m01_http_downgrade,   # (1) HTTPS降级到HTTP
    m02_wayback,          # (2) Wayback Machine
    m03_google_cache,     # (3) Google缓存
    m04_common_crawl,     # (4) Common Crawl
    m05_ua_chrome,        # (5) UA Chrome
    m06_ua_firefox,       # (5) UA Firefox
    m07_ua_edge,          # (5) UA Edge
    m08_ua_safari,        # (5) UA Safari
    m09_ua_mobile,        # (5) UA Mobile
    m10_referer,          # (6) 添加Referer
    m11_prefetch_cookie,  # (7) 预取cookie
    m12_disable_tls,      # (8) 禁用TLS验证
    m13_proxy_7890,       # (9) 代理
    m14_mobile_context,   # (10) mobile context
    m15_long_timeout,     # (11) 长超时+networkidle
    m16_stealth_js,       # (12) stealth.js
    m17_accept_encoding,  # (13) Accept-Encoding
    m18_doh_marker,       # (14) DoH标记
]


def retry_one_source(browser, src):
    """对一个失败源依次尝试所有手段，返回记录"""
    idx = src["idx"]
    url = src["source_url"]
    record = {
        "idx": idx,
        "original_error": src.get("original_error", "unknown"),
        "original_status": src.get("original_status", 0),
        "recovered": False,
        "recovered_method": "",
        "recovered_with_content": False,
        "final_url_accessible": False,
        "list_items": 0,
        "notes": "",
        "attempted_methods": [],
    }
    for m_func in RETRY_METHODS:
        m_name = m_func.__name__
        try:
            r = m_func(browser, url)
        except Exception as e:
            r = {"method_name": m_name.replace("m", "", 1) if m_name.startswith("m") else m_name,
                 "ok": False, "accessible": False, "list_items": 0, "status_code": 0,
                 "error_type": classify_error(str(e)), "error_raw": str(e), "final_url": "",
                 "notes": "method异常"}
        attempt = {
            "method": r.get("method_name", m_name),
            "ok": bool(r.get("ok")),
            "accessible": bool(r.get("accessible")),
            "status_code": r.get("status_code", 0),
            "list_items": r.get("list_items", 0),
            "error_type": r.get("error_type", ""),
            "notes": r.get("notes", ""),
        }
        # 错误消息脱敏后再记录
        attempt["error_raw"] = sanitize(r.get("error_raw", ""))
        record["attempted_methods"].append(attempt)
        log(f"  源[{idx}] 尝试 {attempt['method']}: ok={attempt['ok']} items={attempt['list_items']} status={attempt['status_code']}")
        if r.get("accessible"):
            record["recovered"] = True
            record["recovered_method"] = r.get("method_name", m_name)
            record["final_url_accessible"] = True
            record["list_items"] = r.get("list_items", 0)
            if r.get("list_items", 0) > 0:
                record["recovered_with_content"] = True
                record["notes"] = f"手段[{r.get('method_name')}]成功且有内容"
            else:
                record["notes"] = f"手段[{r.get('method_name')}]成功但无内容"
            break  # 成功则不再尝试后续手段
        # 单手段失败不阻塞，继续下一个
    return record


# ============ Stage 5: 主流程 ============
def main():
    log("=" * 60)
    log("重试失败RSS订阅源 任务开始")
    log("=" * 60)

    # 加载所有源
    sources = load_all_sources()
    log(f"DB读取完成：共 {len(sources)} 条源")

    # 检查是否有已保存的失败列表（避免重复扫描）
    failed = []
    if FAILED_LIST_FILE.exists():
        try:
            with open(FAILED_LIST_FILE, "r", encoding="utf-8") as f:
                fl = json.load(f)
            failed = fl.get("failed", [])
            log(f"复用已保存的失败列表：{len(failed)} 条失败源（避免重复扫描）")
        except Exception as e:
            log(f"读取失败列表出错：{e}，将重新扫描", "WARN")
            failed = []

    records = []
    # 加载增量结果
    if INCREMENT_FILE.exists():
        try:
            with open(INCREMENT_FILE, "r", encoding="utf-8") as f:
                inc = json.load(f)
            records = inc.get("records", [])
            log(f"加载增量结果：已完成 {len(records)} 条")
        except Exception:
            records = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                # 若无失败列表，先扫描
                if not failed:
                    failed, ok_count = scan_all_sources(sources, browser)
                else:
                    ok_count = len(sources) - len(failed)
                log(f"待重试失败源数：{len(failed)}")

                # 增量处理：跳过已完成的 idx
                done_idx = {r["idx"] for r in records}
                pending = [s for s in failed if s["idx"] not in done_idx]
                log(f"待处理：{len(pending)}（已完成 {len(done_idx)}）")

                for i, src in enumerate(pending):
                    try:
                        rec = retry_one_source(browser, src)
                        records.append(rec)
                        log(f"源[{src['idx']}] 处理完成: recovered={rec['recovered']} method={rec['recovered_method']}")
                    except KeyboardInterrupt:
                        log("用户中断（KeyboardInterrupt），保存已处理结果", "WARN")
                        raise
                    except Exception as e:
                        log(f"源[{src['idx']}] 处理异常: {sanitize(str(e))}", "ERROR")
                        records.append({
                            "idx": src["idx"], "original_error": src.get("original_error", ""),
                            "recovered": False, "recovered_method": "",
                            "final_url_accessible": False, "list_items": 0,
                            "notes": f"处理异常: {sanitize(str(e))}",
                            "attempted_methods": [],
                        })
                    # 增量保存（每5个）
                    if (i + 1) % 5 == 0:
                        save_json(INCREMENT_FILE, {"records": records,
                                                    "saved_at": datetime.now().isoformat()})
                        log(f"  增量保存：已处理 {len(records)} 条")
            finally:
                try: browser.close()
                except Exception: pass
    except KeyboardInterrupt:
        log("用户中断，保存当前结果", "WARN")
    except Exception as e:
        log(f"主流程异常: {sanitize(str(e))}", "ERROR")
        log(traceback.format_exc(), "ERROR")

    # 最终统计
    total_failed = len(failed)
    recovered_with_content = sum(1 for r in records if r.get("recovered") and r.get("recovered_with_content"))
    recovered_only_access = sum(1 for r in records if r.get("recovered") and not r.get("recovered_with_content"))
    still_failed = sum(1 for r in records if not r.get("recovered"))

    # 各手段成功率
    method_stats = {}
    for r in records:
        for a in r.get("attempted_methods", []):
            m = a.get("method", "unknown")
            if m not in method_stats:
                method_stats[m] = {"attempted": 0, "ok": 0, "with_content": 0}
            method_stats[m]["attempted"] += 1
            if a.get("accessible"):
                method_stats[m]["ok"] += 1
            if a.get("list_items", 0) > 0:
                method_stats[m]["with_content"] += 1

    method_ranking = sorted(
        [{"method": m, "attempted": v["attempted"], "ok": v["ok"],
          "with_content": v["with_content"],
          "ok_rate": round(v["ok"] / v["attempted"], 3) if v["attempted"] else 0}
         for m, v in method_stats.items()],
        key=lambda x: (x["ok"], x["with_content"]), reverse=True
    )

    final_report = {
        "total_failed": total_failed,
        "recovered_with_content": recovered_with_content,
        "recovered_only_access": recovered_only_access,
        "recovered_total": recovered_with_content + recovered_only_access,
        "still_failed": still_failed,
        "method_ranking": method_ranking,
        "records": records,
        "generated_at": datetime.now().isoformat(),
    }
    save_json(OUTPUT_FILE, final_report)
    log("=" * 60)
    log(f"任务完成：总失败 {total_failed} | 有内容恢复 {recovered_with_content} | "
        f"仅可访问 {recovered_only_access} | 仍失败 {still_failed}")
    log(f"报告输出: {OUTPUT_FILE}")
    log("=" * 60)
    # 输出排名
    log("手段成功率排名：")
    for r in method_ranking:
        log(f"  {r['method']}: ok={r['ok']}/{r['attempted']} rate={r['ok_rate']}")


if __name__ == "__main__":
    main()
