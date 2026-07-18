#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子代理：深度分析 needs_manual (skipped) RSS 订阅源

职责：
1. 读取 classified_v2.json，筛选 sourceComment 含 "skipped" 的源（21个占位符源）
2. 深度分析所有字段，恢复候选 URL：
   - sourceUrl (若 http 开头且长度≥20)
   - sourceIcon (提取 host 拼接)
   - sortUrl (提取首个 URL 的 host)
   - loginUrl (提取首个 URL 的 host)
   - header (提取首个 URL 的 host)
   - sourceComment (提取 http URL 或纯域名)
3. 对恢复的候选 URL 用 Playwright 验证可达性
4. 对可达的源进行 DOM 类型识别（type 0/1/2）
5. 输出结果到 output/rss/subagent_manual_analysis.json

输出安全铁律（不可违背）：
- 脚本输出禁止包含业务字段原文（sourceName/sourceUrl/sourceComment 内容）
- 只输出技术指标：idx, recovered_url_len, recovered_method, accessible, type
- Playwright 异常消息必须脱敏（替换 URL/域名为 [URL]/[DOMAIN]）
- 不输出完整 URL，只保留 URL 长度和路径模式
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "subagent_manual_analysis.json"

# Playwright 配置
PAGE_TIMEOUT = 15000
NAV_WAIT_UNTIL = "domcontentloaded"
NAVIGATE_TIMEOUT = 20000

# stealth 脚本（避免被反爬识别）
STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
}
"""

# 纯域名模式（不带 http 前缀）
DOMAIN_PATTERN = re.compile(
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)"
    r"+(?:com|net|org|cn|info|xyz|online|site|top|vip|cc|tv|me|io|app|club|shop|store|world|news|fun|icu|us|uk|de|fr|jp|kr|ru|ca|au|in|br|mx)",
    re.IGNORECASE
)

# URL 提取正则
URL_EXTRACT_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


def sanitize_error(msg: str) -> str:
    """脱敏错误消息：替换 URL/域名为 [URL]/[DOMAIN]"""
    if not msg:
        return ""
    # 替换 http(s):// URL
    msg = URL_EXTRACT_PATTERN.sub("[URL]", msg)
    # 替换纯域名
    msg = DOMAIN_PATTERN.sub("[DOMAIN]", msg)
    # 替换 IP 地址
    msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]", msg)
    return msg


def recover_url(source: dict) -> Tuple[str, str, dict]:
    """从所有字段恢复候选 URL

    返回: (recovered_url, method, debug_info)
    method 取值: source_url_valid|icon_host|sort_url_host|login_url_host|header_url_host|comment_url|comment_domain|none
    """
    debug_info = {
        "tried_fields": [],
        "candidate_count": 0,
    }

    # 1. sourceUrl 本身（如果长度≥20 且 http 开头）
    src_url = source.get("sourceUrl", "") or ""
    debug_info["tried_fields"].append("sourceUrl")
    if src_url.startswith(("http://", "https://")) and len(src_url) >= 20:
        debug_info["candidate_count"] = 1
        return src_url, "source_url_valid", debug_info

    # 2. 从 sourceIcon 提取 host
    icon = source.get("sourceIcon", "") or ""
    if icon:
        debug_info["tried_fields"].append("sourceIcon")
        if icon.startswith(("http://", "https://")):
            try:
                p = urlparse(icon)
                if p.netloc and "." in p.netloc:
                    debug_info["candidate_count"] = 1
                    return f"{p.scheme}://{p.netloc}/", "icon_host", debug_info
            except Exception:
                pass

    # 3. 从 sortUrl 提取第一个 URL 的 host
    sort_url = source.get("sortUrl", "") or ""
    if sort_url:
        debug_info["tried_fields"].append("sortUrl")
        urls = URL_EXTRACT_PATTERN.findall(sort_url)
        if urls:
            try:
                p = urlparse(urls[0])
                if p.netloc and "." in p.netloc:
                    debug_info["candidate_count"] = len(urls)
                    return f"{p.scheme}://{p.netloc}/", "sort_url_host", debug_info
            except Exception:
                pass

    # 4. 从 loginUrl 提取 URL 的 host
    login_url = source.get("loginUrl", "") or ""
    if login_url:
        debug_info["tried_fields"].append("loginUrl")
        urls = URL_EXTRACT_PATTERN.findall(login_url)
        if urls:
            try:
                p = urlparse(urls[0])
                if p.netloc and "." in p.netloc:
                    debug_info["candidate_count"] = len(urls)
                    return f"{p.scheme}://{p.netloc}/", "login_url_host", debug_info
            except Exception:
                pass

    # 5. 从 header 提取 URL 的 host
    header = source.get("header", "") or ""
    if header:
        debug_info["tried_fields"].append("header")
        urls = URL_EXTRACT_PATTERN.findall(header)
        if urls:
            try:
                p = urlparse(urls[0])
                if p.netloc and "." in p.netloc:
                    debug_info["candidate_count"] = len(urls)
                    return f"{p.scheme}://{p.netloc}/", "header_url_host", debug_info
            except Exception:
                pass

    # 6. 从 sourceComment 提取 URL
    comment = source.get("sourceComment", "") or ""
    if comment:
        debug_info["tried_fields"].append("sourceComment")
        urls = URL_EXTRACT_PATTERN.findall(comment)
        if urls:
            debug_info["candidate_count"] = len(urls)
            return urls[0], "comment_url", debug_info
        # 7. 从 sourceComment 提取纯域名
        domains = DOMAIN_PATTERN.findall(comment)
        if domains:
            debug_info["candidate_count"] = len(domains)
            return f"https://{domains[0]}/", "comment_domain", debug_info

    debug_info["candidate_count"] = 0
    return "", "none", debug_info


def verify_and_classify(url: str) -> Tuple[bool, str, int, float, str]:
    """用 Playwright 验证 URL 可达性并执行 DOM 类型识别（同一会话）

    返回: (accessible, error_type, type, confidence, notes)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "no_playwright", 0, 0.0, "playwright_not_installed"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                # 注入 stealth 脚本
                context.add_init_script(STEALTH_JS)
                page = context.new_page()
                page.set_default_timeout(PAGE_TIMEOUT)

                # 阶段A: 访问验证
                try:
                    resp = page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAVIGATE_TIMEOUT)
                except Exception as e:
                    err_msg = sanitize_error(str(e))
                    if "ERR_NAME_NOT_RESOLVED" in err_msg or "ERR_CONNECTION_REFUSED" in err_msg:
                        return False, "dns_or_connect_fail", 0, 0.0, ""
                    elif "Timeout" in err_msg or "timeout" in err_msg.lower():
                        return False, "timeout", 0, 0.0, ""
                    elif "ERR_SSL_PROTOCOL_ERROR" in err_msg or "ERR_CERT" in err_msg:
                        return False, "ssl_error", 0, 0.0, ""
                    else:
                        return False, "nav_error", 0, 0.0, ""

                if resp is None:
                    return False, "no_response", 0, 0.0, ""

                status = resp.status
                if status == 404:
                    return False, "http_404", 0, 0.0, ""
                if not (200 <= status < 400 or status in (401, 403)):
                    return False, f"http_{status}", 0, 0.0, ""

                accessible = True
                error_type = f"ok_{status}" if 200 <= status < 400 else f"reachable_{status}"

                # 阶段B: DOM 类型识别（复用同一 page）
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

                try:
                    metrics = page.evaluate("""
                    () => {
                        const result = {img: 0, video: 0, article: 0, nav: 0, text: 0};
                        result.img = document.querySelectorAll('img').length;
                        result.video = document.querySelectorAll('video, source[type*="video"], .video-player, [class*="player"]').length;
                        result.article = document.querySelectorAll('article, .article, .post, .content, .news').length;
                        result.nav = document.querySelectorAll('nav, .nav, .menu, .category, .sort').length;
                        result.text = document.body ? document.body.innerText.length : 0;
                        return result;
                    }
                    """)
                except Exception:
                    return accessible, error_type, 0, 0.0, "dom_eval_fail"

                img = metrics.get("img", 0)
                video = metrics.get("video", 0)
                article = metrics.get("article", 0)
                text_len = metrics.get("text", 0)

                img_score = min(img / 20.0, 1.0)
                video_score = min(video / 3.0, 1.0)
                article_score = min(article / 10.0, 1.0)

                if video_score >= 0.5 and video_score >= img_score:
                    return accessible, error_type, 2, video_score, f"v={video},img={img},art={article}"
                if img_score >= 0.5 and img_score > article_score:
                    return accessible, error_type, 1, img_score, f"v={video},img={img},art={article}"
                return accessible, error_type, 0, article_score, f"v={video},img={img},art={article},text={text_len}"
            finally:
                try:
                    context.close()
                except Exception:
                    pass
    except Exception as e:
        err_msg = sanitize_error(str(e))
        return False, "playwright_init_fail", 0, 0.0, ""


def main():
    # 加载输入
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # 筛选 skipped 源
    skipped_items = []
    for idx, s in enumerate(sources):
        comment = s.get("sourceComment", "") or ""
        if "skipped" in comment.lower():
            skipped_items.append((idx, s))

    total = len(skipped_items)
    print(f"=== 子代理: 深度分析 {total} 个 skipped 源 ===\n")

    results = []
    recovered_count = 0
    accessible_count = 0
    still_manual_count = 0

    for idx, s in skipped_items:
        original_src_url = s.get("sourceUrl", "") or ""
        original_len = len(original_src_url)

        # 阶段1: 恢复 URL
        recovered_url, method, debug_info = recover_url(s)

        result = {
            "idx": idx,
            "original_sourceUrl_len": original_len,
            "recovered_url_len": len(recovered_url),
            "recovered_method": method,
            "accessible": False,
            "type": 0,
            "confidence": 0.0,
            "error_type": "",
            "analysis_notes": "",
            "tried_fields": debug_info["tried_fields"],
            "candidate_count": debug_info["candidate_count"],
        }

        if not recovered_url:
            result["error_type"] = "no_recoverable_url"
            result["analysis_notes"] = f"placeholder_url_len={original_len},no_url_in_any_field"
            results.append(result)
            still_manual_count += 1
            print(f"  [idx={idx:3d}] 无法恢复 (tried: {debug_info['tried_fields']})")
            continue

        recovered_count += 1
        print(f"  [idx={idx:3d}] 恢复: method={method}, url_len={len(recovered_url)}")

        # 阶段2+3: Playwright 验证可达性 + DOM 类型识别（同一会话）
        accessible, error_type, t, conf, notes = verify_and_classify(recovered_url)
        result["accessible"] = accessible
        result["error_type"] = error_type
        result["type"] = t
        result["confidence"] = round(conf, 3)
        result["analysis_notes"] = notes if accessible else f"unreachable: {error_type}"

        if accessible:
            accessible_count += 1
            print(f"           可达, type={t}, conf={conf:.2f}, notes={notes[:40]}")
        else:
            still_manual_count += 1
            print(f"           不可达: {error_type}")

        results.append(result)

    # 输出汇总
    output = {
        "agent": "manual_source_analyzer",
        "total_analyzed": total,
        "recovered_count": recovered_count,
        "accessible_count": accessible_count,
        "still_manual_count": still_manual_count,
        "method_distribution": {},
        "results": results,
    }

    # 方法分布
    from collections import Counter
    method_counter = Counter(r["recovered_method"] for r in results)
    output["method_distribution"] = dict(method_counter)

    # 类型分布
    type_counter = Counter(r["type"] for r in results if r["accessible"])
    output["accessible_type_distribution"] = dict(type_counter)

    # 写入文件
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== 汇总 ===")
    print(f"总分析: {total}")
    print(f"恢复URL: {recovered_count}")
    print(f"可达: {accessible_count}")
    print(f"仍需人工: {still_manual_count}")
    print(f"方法分布: {dict(method_counter)}")
    print(f"可达源类型分布: {dict(type_counter)}")
    print(f"\n输出: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
