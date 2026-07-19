"""
订阅源深度分析脚本 - 第四批 (idx 150-221, type=0)
输出安全：只输出技术指标，不输出业务字段原文
"""
import json
import os
import sys
import time
import re
import asyncio
from pathlib import Path

# 路径配置
ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_FILE = ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_FILE = ROOT / "output" / "rss" / "subagent_web4_analysis.json"
REF_IDX = [0, 2, 131]

# 字段清单
TARGET_FIELDS = [
    "sourceIcon", "searchUrl", "sortUrl", "ruleArticles", "ruleTitle",
    "ruleLink", "ruleImage", "ruleNextPage", "rulePubDate", "ruleContent", "jsRule"
]

# 字段完整性参考 - 用于字段计数
FIELD_COUNT_TARGET = 14  # 14字段全满


def sanitize_url(url: str) -> str:
    """URL脱敏：只保留路径模式"""
    if not url:
        return ""
    # 替换协议域名为代号
    s = re.sub(r"https?://[^/]+", "/path", url)
    # 替换长ID
    s = re.sub(r"\d{6,}", "{id}", s)
    s = re.sub(r"[a-f0-9]{20,}", "{hash}", s, flags=re.I)
    return s


def sanitize_text(text: str, max_len: int = 50) -> str:
    """文本脱敏：截断+替换敏感内容"""
    if not text:
        return ""
    s = str(text)
    # 替换URL
    s = re.sub(r"https?://[^/]+", "/path", s)
    s = re.sub(r"\d{6,}", "{id}", s)
    # 截断
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s


def load_data():
    """加载数据"""
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_target_sources(data):
    """筛选目标源：type=0, idx在150-221, 排除已处理"""
    targets = []
    for idx, item in enumerate(data):
        if idx < 150 or idx > 221:
            continue
        if item.get("type") != 0:
            continue
        comment = item.get("sourceComment") or ""
        if "AI_CLASSIFY:access_failed" in comment:
            continue
        if "AI_CLASSIFY:skipped" in comment:
            continue
        targets.append((idx, item))
    return targets


def get_reference_fields(data):
    """读取参考源的字段结构（脱敏）"""
    refs = []
    for idx in REF_IDX:
        if idx >= len(data):
            continue
        item = data[idx]
        ref_info = {
            "idx": idx,
            "type": item.get("type"),
            "field_count": sum(1 for f in TARGET_FIELDS if item.get(f)),
            "fields": {f: sanitize_text(item.get(f, ""), 30) for f in TARGET_FIELDS if item.get(f)},
            "has_login": bool(item.get("loginUrl")),
            "has_login_check": bool(item.get("loginCheckJs")),
            "enableJs": item.get("enableJs", False),
            "header_count": len(item.get("header", "")) if item.get("header") else 0,
        }
        refs.append(ref_info)
    return refs


def analyze_field_structure(item):
    """分析字段结构（不调用网络，仅基于JSON已有数据）"""
    fields_present = {}
    for f in TARGET_FIELDS:
        val = item.get(f)
        if val:
            fields_present[f] = {
                "len": len(str(val)),
                "preview": sanitize_text(val, 30),
            }
    return {
        "field_count": len(fields_present),
        "fields": fields_present,
        "has_login": bool(item.get("loginUrl")),
        "has_login_check": bool(item.get("loginCheckJs")),
        "enableJs": item.get("enableJs", False),
        "has_header": bool(item.get("header")),
        "articleStyle": item.get("articleStyle"),
        "singleUrl": item.get("singleUrl", False),
    }


async def playwright_deep_analyze(item, idx, playwright):
    """Playwright深度分析 - 只输出技术指标"""
    result = {
        "idx": idx,
        "status": "pending",
        "error": None,
        "tech_indicators": {},
    }

    source_url = item.get("sourceUrl", "")
    if not source_url:
        result["status"] = "no_source_url"
        return result

    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # 设置较短超时
        page.set_default_timeout(15000)

        # 访问页面
        try:
            response = await page.goto(source_url, wait_until="domcontentloaded", timeout=15000)
            result["tech_indicators"]["status_code"] = response.status if response else None
            result["tech_indicators"]["content_type"] = response.headers.get("content-type", "") if response else ""
        except Exception as e:
            err_msg = str(e)
            # 脱敏异常消息
            err_msg = re.sub(r"https?://[^/\s]+", "/path", err_msg)
            err_msg = re.sub(r"\d{6,}", "{id}", err_msg)
            result["error"] = sanitize_text(err_msg, 100)
            result["status"] = "access_failed"
            await browser.close()
            return result

        # 等待页面加载
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass  # 网络idle超时不致命

        # 检测弹框
        try:
            dialog_count = 0
            page.on("dialog", lambda d: asyncio.create_task(d.dismiss()))
            await asyncio.sleep(0.5)
        except Exception:
            pass

        # 分析页面技术特征
        try:
            page_info = await page.evaluate("""() => {
                return {
                    title_len: (document.title || '').length,
                    html_size: (document.documentElement.outerHTML || '').length,
                    has_login_form: !!document.querySelector('input[type=password]'),
                    has_captcha: !!(document.querySelector('img[src*="captcha"]') || document.querySelector('[id*="captcha"]') || document.querySelector('[class*="captcha"]')),
                    link_count: document.querySelectorAll('a').length,
                    img_count: document.querySelectorAll('img').length,
                    article_count: document.querySelectorAll('article').length,
                    rss_link: !!document.querySelector('link[type="application/rss+xml"]'),
                    has_iframe: document.querySelectorAll('iframe').length,
                    cookie_count: document.cookie ? document.cookie.split(';').length : 0,
                };
            }""")
            result["tech_indicators"].update(page_info)
        except Exception as e:
            err_msg = re.sub(r"https?://[^/\s]+", "/path", str(e))
            result["tech_indicators"]["page_eval_error"] = sanitize_text(err_msg, 60)

        # 检测常见RSS路径
        rss_paths = ["/rss", "/feed", "/rss.xml", "/feed.xml", "/atom.xml"]
        detected_feeds = []
        for path in rss_paths:
            try:
                resp = await page.goto(source_url.rstrip("/") + path, wait_until="domcontentloaded", timeout=5000)
                if resp and resp.status == 200:
                    ct = resp.headers.get("content-type", "")
                    if "xml" in ct or "rss" in ct or "atom" in ct:
                        detected_feeds.append(path)
            except Exception:
                pass
        if detected_feeds:
            result["tech_indicators"]["detected_feeds"] = detected_feeds

        result["status"] = "analyzed"

        await browser.close()
    except Exception as e:
        err_msg = re.sub(r"https?://[^/\s]+", "/path", str(e))
        result["error"] = sanitize_text(err_msg, 100)
        result["status"] = "error"

    return result


async def main():
    print("=" * 60)
    print("[Batch4] 订阅源深度分析 - idx 150-221, type=0")
    print("=" * 60)

    data = load_data()
    print(f"[INFO] 总源数: {len(data)}")

    # 参考源字段结构
    refs = get_reference_fields(data)
    print(f"[INFO] 参考源: {len(refs)}个")
    for r in refs:
        print(f"  - idx={r['idx']}: 字段数={r['field_count']}, enableJs={r['enableJs']}, has_login={r['has_login']}")

    # 筛选目标源
    targets = filter_target_sources(data)
    print(f"[INFO] 目标源: {len(targets)}个 (idx 150-221, type=0, 排除已处理)")

    # 列出待分析源的idx
    idx_list = [t[0] for t in targets]
    print(f"[INFO] 目标idx列表: {idx_list[:10]}... (共{len(idx_list)}个)")

    # 阶段1: 静态分析（基于JSON已有字段）
    static_results = []
    for idx, item in targets:
        static = analyze_field_structure(item)
        static_results.append({"idx": idx, "static": static})

    # 统计字段分布
    field_dist = {f: 0 for f in TARGET_FIELDS}
    for r in static_results:
        for f in r["static"]["fields"].keys():
            field_dist[f] = field_dist.get(f, 0) + 1
    print(f"\n[STAT] 静态字段分布:")
    for f, c in sorted(field_dist.items(), key=lambda x: -x[1]):
        print(f"  {f}: {c}/{len(static_results)}")

    # 阶段2: Playwright深度分析
    print(f"\n[INFO] 开始Playwright深度分析...")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright未安装")
        playwright_results = []
    else:
        playwright_results = []
        async with async_playwright() as pw:
            # 串行分析，避免并发对源站造成压力
            for i, (idx, item) in enumerate(targets):
                print(f"  [{i+1}/{len(targets)}] 分析 idx={idx}...", end=" ", flush=True)
                result = await playwright_deep_analyze(item, idx, pw)
                playwright_results.append(result)
                status = result["status"]
                print(f"-> {status}")
                # 礼貌等待
                await asyncio.sleep(0.5)

    # 阶段3: 综合结果
    final_results = []
    for i, (idx, item) in enumerate(targets):
        final_results.append({
            "idx": idx,
            "type": item.get("type"),
            "static": static_results[i]["static"],
            "dynamic": playwright_results[i] if i < len(playwright_results) else None,
        })

    # 输出统计
    status_count = {}
    for r in playwright_results:
        s = r["status"]
        status_count[s] = status_count.get(s, 0) + 1
    print(f"\n[STAT] Playwright分析状态分布: {status_count}")

    output = {
        "agent": "web_source_analyzer_batch4",
        "batch_range": "150-221",
        "total_analyzed": len(final_results),
        "ref_sources": refs,
        "field_distribution": field_dist,
        "status_distribution": status_count,
        "results": final_results,
        "summary": {
            "total_targets": len(targets),
            "static_only": sum(1 for r in playwright_results if r["status"] in ["no_source_url", "access_failed", "error"]),
            "dynamic_ok": sum(1 for r in playwright_results if r["status"] == "analyzed"),
            "avg_field_count": sum(r["static"]["field_count"] for r in final_results) / max(1, len(final_results)),
        },
    }

    # 写入输出
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 输出已写入: {OUTPUT_FILE}")
    print(f"[OK] 共分析 {len(final_results)} 个源")
    print(f"[OK] 平均字段数: {output['summary']['avg_field_count']:.2f}")
    print(f"[OK] 动态分析成功: {output['summary']['dynamic_ok']}/{len(final_results)}")


if __name__ == "__main__":
    asyncio.run(main())
