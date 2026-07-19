#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaccess_disabled_sources.py - 重新评估被禁用源和失败源（V4 激进重评估）

输入：
  - output/rss/optimized_v2_lite_final_v3.json (提取 enabled=false 的源)
  - output/rss/failed_source_retry_v2.json (提取 records 中 recovered=false 的源 idx)

10种激进策略：
  1. mobile context + UA + zh-CN
  2. Cookie预取 + Referer
  3. TLS禁用 + 长超时(30s)
  4. HTTP降级 + 重定向跟踪
  5. CORS代理 + Wayback
  6. 多UA轮换(Chrome/Firefox/Edge/Safari/Mobile)
  7. 接受所有Content-Type
  8. 禁用图片加载(route拦截)
  9. DNS-over-HTTPS (注释说明，Playwright不支持直接配置)
  10. WebSocket降级 (禁用WS)

输出安全铁律：
  - 脚本输出禁止包含源名称/URL/分类名原文
  - 用 源[idx] 替代真实名称
  - 异常消息必须脱敏
  - 只输出技术指标：idx, strategy, status_code, list_count, decision
"""
import asyncio
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_V3 = PROJECT_ROOT / "output" / "rss" / "optimized_v2_lite_final_v3.json"
INPUT_RETRY = PROJECT_ROOT / "output" / "rss" / "failed_source_retry_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "disabled_source_reaccess.json"

# 5种UA
UA_LIST = {
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
}

# CORS代理（备用方案）
CORS_PROXY = "https://corsproxy.io/?url="
WAYBACK_BASE = "https://web.archive.org/web/2024/"


def sanitize_text(text: str) -> str:
    """脱敏文本：替换URL/域名/敏感字段"""
    if not text:
        return ""
    s = str(text)
    s = re.sub(r"https?://[^\s\"'<>]+", "[URL]", s)
    s = re.sub(r"\b[a-z0-9\-]+\.(?:com|net|org|cc|io|me|tv|info|xyz|top|site|online|store|live|app|cloud|wiki|date|club|fun|shop|vip|biz|name|pro|tech|space|design|press|website|host|link|click|world|today|news|media|zone|center|academy|company|education|engineering|exchange|expert|finance|financial|foundation|healthcare|industries|institute|international|legal|limited|ltd|management|network|partners|properties|realty|solutions|systems|technology|university|ventures|agency|digital|direct|domains|email|enterprise|gallery|global|graphics|guru|icons|international|life|lighting|marketing|photography|pictures|plus|production|services|social|software|support|tips|tools|training|travel|university|vision|work|yoga)\b[^\s]*", "[DOMAIN]", s, flags=re.IGNORECASE)
    s = re.sub(r"(?i)(cookie|token|password|secret|api[_\-]?key|auth)[=:][^\s,;\"']+", "[REDACTED]", s)
    return s[:300]


def extract_main_url(source_url: str) -> str:
    """提取主域名URL（用于访问测试）"""
    if not source_url:
        return ""
    # 处理@js:,带搜索URL等
    s = str(source_url).strip()
    if s.startswith("@js:") or s.startswith("<js>"):
        # 从JS中提取第一个http(s) URL
        m = re.search(r"https?://[^\s\"'<>\\]+", s)
        return m.group(0).rstrip("',\"") if m else ""
    # 处理带逗号分隔的多URL，取第一个
    s = s.split(",")[0].strip()
    # 处理带搜索模板的URL
    m = re.match(r"https?://[^\s,{{]+", s)
    return m.group(0).rstrip("/") if m else s


def extract_root_url(url: str) -> str:
    """提取根域名URL"""
    if not url:
        return ""
    m = re.match(r"(https?://[^/]+)", url)
    return m.group(1) if m else url


# ============ 10种激进策略 ============

async def strategy_1_mobile_context(browser, url: str) -> Dict[str, Any]:
    """策略1: mobile context + Mobile UA + Accept-Language zh-CN"""
    ctx = await browser.new_context(
        viewport={"width": 375, "height": 667},
        user_agent=UA_LIST["mobile"],
        locale="zh-CN",
        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    )
    page = await ctx.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "mobile_context"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "mobile_context"}


async def strategy_2_cookie_referer(browser, url: str) -> Dict[str, Any]:
    """策略2: Cookie预取 + Referer组合"""
    root = extract_root_url(url)
    ctx = await browser.new_context(user_agent=UA_LIST["chrome"])
    page = await ctx.new_page()
    try:
        # 先访问首页获取Cookie
        try:
            await page.goto(root, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(800)
        except Exception:
            pass
        # 设置Referer后再访问目标
        await page.set_extra_http_headers({"Referer": root})
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "cookie_referer"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "cookie_referer"}


async def strategy_3_tls_disable_timeout(browser, url: str) -> Dict[str, Any]:
    """策略3: TLS禁用 + 长超时(30s)"""
    ctx = await browser.new_context(
        user_agent=UA_LIST["chrome"],
        ignore_https_errors=True,
    )
    page = await ctx.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "tls_disable_timeout"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "tls_disable_timeout"}


async def strategy_4_http_downgrade(browser, url: str) -> Dict[str, Any]:
    """策略4: HTTP降级 + 重定向跟踪"""
    if url.startswith("https://"):
        new_url = "http://" + url[len("https://"):]
    else:
        new_url = url
    ctx = await browser.new_context(user_agent=UA_LIST["chrome"])
    page = await ctx.new_page()
    try:
        resp = await page.goto(new_url, wait_until="domcontentloaded", timeout=25000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "http_downgrade"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "http_downgrade"}


async def strategy_5_cors_wayback(browser, url: str) -> Dict[str, Any]:
    """策略5: CORS代理 + Wayback组合"""
    # 先尝试CORS代理
    cors_url = CORS_PROXY + url
    ctx = await browser.new_context(user_agent=UA_LIST["chrome"])
    page = await ctx.new_page()
    try:
        resp = await page.goto(cors_url, wait_until="domcontentloaded", timeout=20000)
        status = resp.status if resp else 0
        if status == 200:
            content = await page.content()
            if len(content) > 1000:
                return {"ok": True, "status": status, "page": page, "ctx": ctx, "method": "cors_proxy"}
        # CORS失败，尝试Wayback
        await ctx.close()
        ctx2 = await browser.new_context(user_agent=UA_LIST["chrome"])
        page2 = await ctx2.new_page()
        wayback_url = WAYBACK_BASE + url
        try:
            resp2 = await page2.goto(wayback_url, wait_until="domcontentloaded", timeout=20000)
            status2 = resp2.status if resp2 else 0
            return {"ok": status2 == 200, "status": status2, "page": page2, "ctx": ctx2, "method": "wayback"}
        except Exception as e2:
            await ctx2.close()
            return {"ok": False, "status": 0, "error": sanitize_text(e2), "method": "wayback"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "cors_proxy"}


async def strategy_6_multi_ua(browser, url: str) -> Dict[str, Any]:
    """策略6: 多UA轮换（Chrome/Firefox/Edge/Safari/Mobile）"""
    for ua_name, ua_str in UA_LIST.items():
        ctx = await browser.new_context(user_agent=ua_str)
        page = await ctx.new_page()
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = resp.status if resp else 0
            if status == 200:
                return {"ok": True, "status": status, "page": page, "ctx": ctx, "method": f"ua_{ua_name}"}
            await ctx.close()
        except Exception:
            await ctx.close()
            continue
    return {"ok": False, "status": 0, "error": "all_ua_failed", "method": "multi_ua"}


async def strategy_7_accept_all_ctype(browser, url: str) -> Dict[str, Any]:
    """策略7: 接受所有Content-Type"""
    ctx = await browser.new_context(
        user_agent=UA_LIST["chrome"],
        extra_http_headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    page = await ctx.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "accept_all_ctype"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "accept_all_ctype"}


async def strategy_8_disable_images(browser, url: str) -> Dict[str, Any]:
    """策略8: 禁用图片加载（route拦截）"""
    ctx = await browser.new_context(user_agent=UA_LIST["chrome"])

    async def block_images(route):
        if route.request.resource_type in ("image", "media", "font"):
            await route.abort()
        else:
            await route.continue_()

    await ctx.route("**/*", block_images)
    page = await ctx.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "disable_images"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "disable_images"}


async def strategy_9_doh_note(browser, url: str) -> Dict[str, Any]:
    """策略9: DNS-over-HTTPS（Playwright不支持直接配置，跳过并标记）"""
    # Playwright不能直接配置DoH，这里跳过，留作记录
    return {"ok": False, "status": 0, "error": "doh_not_supported_in_playwright", "method": "doh_skip"}


async def strategy_10_no_ws(browser, url: str) -> Dict[str, Any]:
    """策略10: WebSocket降级（禁用WS减少反爬识别）"""
    ctx = await browser.new_context(user_agent=UA_LIST["chrome"])

    async def block_ws(route):
        req = route.request
        if req.resource_type == "websocket" or "ws://" in req.url or "wss://" in req.url:
            await route.abort()
        else:
            await route.continue_()

    await ctx.route("**/*", block_ws)
    page = await ctx.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = resp.status if resp else 0
        return {"ok": status == 200, "status": status, "page": page, "ctx": ctx, "method": "no_ws"}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "status": 0, "error": sanitize_text(e), "method": "no_ws"}


# ============ 内容验证 ============

# 扩展DOM选择器（覆盖各类视频站列表项）
LIST_SELECTORS = [
    "ul li", ".stui-vodlist__item", ".module-item", ".vodlist_item", ".stui-vodlist__box",
    ".myui-vodlist__item", ".module-items .module-item", ".tab-content .item",
    ".listing-item", ".article-item", ".post-item", ".entry",
    "tr.item", "tr.tr3", ".text-overflow", ".xing_vb4",
    ".vodlist li", ".list-item", ".video-item", ".card-item",
    ".movie-item", ".tv-item", ".anime-item", ".show-item",
    "[class*='vod']", "[class*='list']", "[class*='item']", "[class*='card']",
    "article", ".article", ".post", ".entry-post",
]

VIDEO_SELECTORS = ["video", "source", ".player", "#player", "[class*='play']", "iframe[src*='play']"]
IMAGE_SELECTORS = ["img", ".lazy", ".thumb", "[data-original]", "[data-src]"]


async def verify_content(page) -> Dict[str, Any]:
    """验证页面内容：列表项数量、视频元素、图片元素"""
    result = {"list_items": 0, "has_video": False, "has_image": False, "title_len": 0}
    try:
        # 等待页面稳定
        await page.wait_for_timeout(1500)
    except Exception:
        pass
    try:
        title = await page.title()
        result["title_len"] = len(title) if title else 0
    except Exception:
        pass
    # 列表项计数（取最大值）
    max_count = 0
    for sel in LIST_SELECTORS:
        try:
            cnt = await page.count(sel)
            if cnt > max_count:
                max_count = cnt
            if cnt >= 5:
                break
        except Exception:
            continue
    result["list_items"] = max_count
    # 视频元素
    for sel in VIDEO_SELECTORS:
        try:
            cnt = await page.count(sel)
            if cnt > 0:
                result["has_video"] = True
                break
        except Exception:
            continue
    # 图片元素
    for sel in IMAGE_SELECTORS:
        try:
            cnt = await page.count(sel)
            if cnt > 0:
                result["has_image"] = True
                break
        except Exception:
            continue
    return result


# ============ 主流程 ============

async def evaluate_one_source(browser, idx: int, source: Dict, original_reason: str) -> Dict[str, Any]:
    """评估单个源：依次尝试10种策略，第一个成功即返回
    单源总超时上限: 120秒（避免长阻塞）
    """
    main_url = extract_main_url(source.get("sourceUrl", ""))
    record = {
        "idx": idx,
        "original_reason": original_reason,
        "recovered_method": "",
        "enabled_decision": False,
        "list_items_count": 0,
        "has_video": False,
        "has_image": False,
        "status_code": 0,
        "notes": "",
    }
    if not main_url:
        record["notes"] = "empty_source_url"
        return record

    strategies = [
        strategy_1_mobile_context,
        strategy_2_cookie_referer,
        strategy_3_tls_disable_timeout,
        strategy_4_http_downgrade,
        strategy_5_cors_wayback,
        strategy_6_multi_ua,
        strategy_7_accept_all_ctype,
        strategy_8_disable_images,
        strategy_9_doh_note,
        strategy_10_no_ws,
    ]

    attempted_methods = []
    recovered = False
    t_start = time.time()
    for strat in strategies:
        # 单源总超时检查
        if time.time() - t_start > 120:
            attempted_methods.append({
                "method": "timeout_skip",
                "ok": False,
                "status": 0,
                "error": "single_source_timeout_120s",
            })
            break
        try:
            # 给单个策略加超时包装
            r = await asyncio.wait_for(strat(browser, main_url), timeout=60)
        except asyncio.TimeoutError:
            r = {"ok": False, "status": 0, "error": "strategy_timeout_60s", "method": strat.__name__.replace("strategy_", "").split("_", 1)[-1]}
        except Exception as e:
            r = {"ok": False, "status": 0, "error": sanitize_text(e), "method": strat.__name__}
        method = r.get("method", strat.__name__)
        attempted_methods.append({
            "method": method,
            "ok": bool(r.get("ok")),
            "status": r.get("status", 0),
            "error": r.get("error", "")[:120] if r.get("error") else "",
        })
        if r.get("ok"):
            record["recovered_method"] = method
            record["status_code"] = r.get("status", 0)
            # 验证内容
            page = r.get("page")
            if page:
                try:
                    content_info = await asyncio.wait_for(verify_content(page), timeout=15)
                    record["list_items_count"] = content_info["list_items"]
                    record["has_video"] = content_info["has_video"]
                    record["has_image"] = content_info["has_image"]
                except Exception as e:
                    record["notes"] = f"verify_failed:{sanitize_text(e)[:80]}"
            # 决策
            if record["list_items_count"] >= 3:
                record["enabled_decision"] = True
                record["notes"] = "recovered_full"
                recovered = True
            else:
                record["enabled_decision"] = True
                record["notes"] = "recovered_low_content"
                recovered = True
            # 关闭上下文
            ctx = r.get("ctx")
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass
            break
        else:
            # 关闭上下文
            ctx = r.get("ctx")
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass

    if not recovered:
        # 检查是否404（资源已下线）
        last_err = attempted_methods[-1]["error"] if attempted_methods else ""
        last_status = attempted_methods[-1]["status"] if attempted_methods else 0
        if last_status == 404 or "404" in last_err:
            record["notes"] = "dead_404"
        else:
            record["notes"] = "still_inaccessible"
        record["enabled_decision"] = False

    record["attempted_methods"] = attempted_methods
    return record


def save_incremental(records: List[Dict], stats: Dict, final: bool = False):
    """增量保存"""
    output = {
        "total": stats["total"],
        "recovered_full": stats["recovered_full"],
        "recovered_partial": stats["recovered_partial"],
        "still_disabled": stats["still_disabled"],
        "method_ranking": stats["method_ranking"],
        "records": records,
        "final": final,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')


async def main():
    print(f"[INFO] 加载V3源: {INPUT_V3}")
    v3_data = json.loads(INPUT_V3.read_text(encoding='utf-8'))
    sources = v3_data.get("sources", [])
    print(f"[INFO] V3源总数: {len(sources)}")

    print(f"[INFO] 加载失败源重试报告: {INPUT_RETRY}")
    retry_data = json.loads(INPUT_RETRY.read_text(encoding='utf-8'))
    retry_records = retry_data.get("records", [])
    still_failed_idx = [r["idx"] for r in retry_records if r.get("recovered") is False]
    print(f"[INFO] 仍失败源idx: {still_failed_idx}")

    # 提取所有 enabled=false 的源
    disabled_sources = []
    for i, src in enumerate(sources):
        if src.get("enabled") is False:
            idx = i + 1  # 1-indexed
            disabled_sources.append((idx, src))

    print(f"[INFO] enabled=false 源数: {len(disabled_sources)}")

    # 合并：disabled_sources + still_failed_idx（去重）
    # 已禁用的源直接评估，still_failed_idx中如果不在disabled_sources里，也加入
    disabled_idx_set = {idx for idx, _ in disabled_sources}
    extra_idx_to_eval = [i for i in still_failed_idx if i not in disabled_idx_set]
    print(f"[INFO] 额外需评估的失败源idx: {extra_idx_to_eval}")

    eval_list = list(disabled_sources)  # [(idx, source), ...]
    for idx in extra_idx_to_eval:
        if 1 <= idx <= len(sources):
            eval_list.append((idx, sources[idx - 1]))

    total = len(eval_list)
    print(f"[INFO] 待评估源总数: {total}")

    # 断点续传：读取已有records
    records = []
    completed_idx_set = set()
    if OUTPUT_JSON.exists():
        try:
            existing = json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))
            existing_records = existing.get("records", [])
            for r in existing_records:
                if "idx" in r and "notes" in r:
                    records.append(r)
                    completed_idx_set.add(r["idx"])
            print(f"[INFO] 断点续传: 已完成 {len(records)} 个源，跳过 idx={sorted(completed_idx_set)}")
        except Exception as e:
            print(f"[WARN] 读取已有输出失败，从头开始: {sanitize_text(e)}")

    # 过滤掉已完成的源
    pending_eval_list = [(idx, src) for idx, src in eval_list if idx not in completed_idx_set]
    print(f"[INFO] 待评估（去除已完成）: {len(pending_eval_list)}")

    # 统计（基于已有records + 新评估）
    stats = {
        "total": total,
        "recovered_full": 0,
        "recovered_partial": 0,
        "still_disabled": 0,
        "method_ranking": {},  # method -> {attempted, ok}
    }

    # 重新统计已完成records
    recovered_full = 0
    recovered_partial = 0
    still_disabled = 0
    for r in records:
        if r.get("enabled_decision") and r.get("list_items_count", 0) >= 3:
            recovered_full += 1
        elif r.get("enabled_decision"):
            recovered_partial += 1
        else:
            still_disabled += 1
        for am in r.get("attempted_methods", []):
            m = am["method"]
            if m not in stats["method_ranking"]:
                stats["method_ranking"][m] = {"attempted": 0, "ok": 0}
            stats["method_ranking"][m]["attempted"] += 1
            if am["ok"]:
                stats["method_ranking"][m]["ok"] += 1
    print(f"[INFO] 已完成统计: full={recovered_full} partial={recovered_partial} disabled={still_disabled}")

    # 启动Playwright
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            for i, (idx, src) in enumerate(pending_eval_list, len(records) + 1):
                # 确定原始原因
                comment = src.get("sourceComment", "")
                if "inaccessible" in comment:
                    original_reason = "v3_disabled_inaccessible"
                elif idx in still_failed_idx:
                    # 从retry_records找原始错误
                    rec = next((r for r in retry_records if r["idx"] == idx), None)
                    original_reason = rec.get("original_error", "retry_failed") if rec else "retry_failed"
                else:
                    original_reason = "manual_disabled"

                print(f"[{i}/{total}] 评估 源[{idx}] reason={original_reason}")
                t0 = time.time()
                try:
                    record = await evaluate_one_source(browser, idx, src, original_reason)
                except Exception as e:
                    record = {
                        "idx": idx,
                        "original_reason": original_reason,
                        "recovered_method": "",
                        "enabled_decision": False,
                        "list_items_count": 0,
                        "has_video": False,
                        "has_image": False,
                        "status_code": 0,
                        "notes": f"eval_exception:{sanitize_text(e)[:100]}",
                        "attempted_methods": [],
                    }
                elapsed = time.time() - t0
                records.append(record)

                # 统计
                if record["enabled_decision"] and record["list_items_count"] >= 3:
                    recovered_full += 1
                elif record["enabled_decision"]:
                    recovered_partial += 1
                else:
                    still_disabled += 1

                # 方法统计
                for am in record.get("attempted_methods", []):
                    m = am["method"]
                    if m not in stats["method_ranking"]:
                        stats["method_ranking"][m] = {"attempted": 0, "ok": 0}
                    stats["method_ranking"][m]["attempted"] += 1
                    if am["ok"]:
                        stats["method_ranking"][m]["ok"] += 1

                stats["recovered_full"] = recovered_full
                stats["recovered_partial"] = recovered_partial
                stats["still_disabled"] = still_disabled

                decision_str = "ENABLED" if record["enabled_decision"] else "DISABLED"
                print(f"   -> {decision_str} method={record['recovered_method']} list={record['list_items_count']} notes={record['notes']} ({elapsed:.1f}s)")

                # 增量保存每5个源
                if i % 5 == 0 or i == total:
                    save_incremental(records, stats, final=False)
                    print(f"[INFO] 增量保存 {i}/{total}")

        finally:
            await browser.close()

    # 最终保存
    save_incremental(records, stats, final=True)

    print("\n" + "=" * 60)
    print(f"[最终结果]")
    print(f"  总数: {total}")
    print(f"  完全恢复: {recovered_full}")
    print(f"  部分恢复: {recovered_partial}")
    print(f"  仍然禁用: {still_disabled}")
    print(f"\n[方法成功率]")
    for m, s in sorted(stats["method_ranking"].items(), key=lambda x: -x[1]["ok"]):
        rate = s["ok"] / s["attempted"] if s["attempted"] else 0
        print(f"  {m}: {s['ok']}/{s['attempted']} ({rate*100:.1f}%)")
    print(f"\n[输出文件] {OUTPUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
