# -*- coding: utf-8 -*-
"""探测 V4/V5.1 JSON 结构, 输出技术统计(脱敏)"""
import json
import sys
from collections import Counter

ROOT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss"

def load(name):
    with open(f"{ROOT}\\{name}", "r", encoding="utf-8") as f:
        return json.load(f)

def is_placeholder(url):
    if not isinstance(url, str):
        return False
    markers = ["[DOMAIN]", "{DOMAIN}", "{{domain}}", "{{DOMAIN}}", "<DOMAIN>"]
    return any(m in url for m in markers)

# 4套通用模板
TEMPLATES_ARTICLES = [
    ".entry-card",
    ".post,.article,.item",
    ".lazy",
    ".thumb",
]
NAV_TEMPLATE_ARTICLES = ".item,.post,.article,article,.news-item,.entry"

def is_template_rule_articles(ra):
    if not isinstance(ra, str):
        return False
    return ra in TEMPLATES_ARTICLES or ra == NAV_TEMPLATE_ARTICLES

def extract_list(data):
    """从 dict/list 中提取源列表"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # 尝试常见 key
        for k in ["sources", "data", "list", "items", "rssSources"]:
            if k in data and isinstance(data[k], list):
                return data[k]
        # 否则取第一个 list value
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        # 全是 dict 但没有 list? 那直接返回空
        print(f"WARN: dict keys: {list(data.keys())[:10]}")
    return []

def main():
    v4_raw = load("optimized_v2_lite_final_v4.json")
    v51_raw = load("optimized_v5_1_app_import_fixed.json")

    print(f"V4 raw type: {type(v4_raw).__name__}")
    if isinstance(v4_raw, dict):
        print(f"V4 top keys: {list(v4_raw.keys())[:20]}")
        for k, v in v4_raw.items():
            print(f"  key={k} type={type(v).__name__} len={(len(v) if hasattr(v, '__len__') else 'n/a')}")
    print(f"V5.1 raw type: {type(v51_raw).__name__}")

    v4 = extract_list(v4_raw)
    v51 = extract_list(v51_raw)
    print(f"\nV4 src count: {len(v4)}")
    print(f"V5.1 src count: {len(v51)}")

    if not v4 or not v51:
        print("ERROR: 提取源列表失败")
        return

    print(f"V4 first item keys count: {len(v4[0].keys())}")
    print(f"V4 first item keys: {list(v4[0].keys())}")
    print(f"V5.1 first item keys count: {len(v51[0].keys())}")
    print(f"V5.1 first item keys: {list(v51[0].keys())}")

    # 占位符源
    v51_placeholder = [s for s in v51 if is_placeholder(s.get("sourceUrl", ""))]
    print(f"\nV5.1 placeholder sourceUrl count: {len(v51_placeholder)}")

    # 通用模板
    v51_template_ra = [s for s in v51 if is_template_rule_articles(s.get("ruleArticles"))]
    print(f"V5.1 template ruleArticles count: {len(v51_template_ra)}")

    # V5.1 enabled 分布
    v51_en = Counter([s.get("enabled") for s in v51])
    print(f"\nV5.1 enabled dist: {dict(v51_en)}")

    # V5.1 中 enabled=true 但 sourceGroup 含"已废/失效/停更"
    bad_enabled = []
    for s in v51:
        g = s.get("sourceGroup") or ""
        if s.get("enabled") is True and any(m in g for m in ["已废", "失效", "停更"]):
            bad_enabled.append(s)
    print(f"V5.1 错误启用(enabled=true但group含已废标记)源数: {len(bad_enabled)}")

    # 8个 Boolean 字段 null
    bool_fields = ["enabled", "enabledCookieJar", "singleUrl", "enableJs", "loadWithBaseUrl",
                   "showWebLog", "preload", "cacheFirst"]
    null_bool_src = []
    for s in v51:
        for f in bool_fields:
            v = s.get(f)
            if v is None:
                null_bool_src.append((s.get("sourceUrl", ""), f))
                break
    print(f"V5.1 Boolean=null 源数: {len(null_bool_src)}")

    # 集成站拆分子源识别：header为空字符串 + enabledCookieJar=False + ruleArticles 在4套模板中
    agg_split = []
    for s in v51:
        ra = s.get("ruleArticles")
        header = s.get("header")
        ecj = s.get("enabledCookieJar")
        if isinstance(ra, str) and ra in TEMPLATES_ARTICLES and header == "" and ecj is False:
            agg_split.append(s)
    print(f"V5.1 集成站拆分子源(header空+ecj=False+模板RA): {len(agg_split)}")

    # 导航站拆分子源识别：sourceUrl 含 [DOMAIN] 或 ruleArticles == NAV_TEMPLATE
    nav_split = []
    for s in v51:
        ra = s.get("ruleArticles")
        if is_placeholder(s.get("sourceUrl", "")) or (ra == NAV_TEMPLATE_ARTICLES):
            nav_split.append(s)
    print(f"V5.1 导航站拆分子源(占位符url或nav模板): {len(nav_split)}")

    # 所有需要移除的源
    remove_urls = set()
    for s in v51_placeholder:
        remove_urls.add(s.get("sourceUrl", ""))
    for s in agg_split:
        remove_urls.add(s.get("sourceUrl", ""))
    for s in nav_split:
        remove_urls.add(s.get("sourceUrl", ""))
    print(f"\n需要移除的源(占位符+集成拆分+导航拆分)总数: {len(remove_urls)}")

    # 保留的源数 = V5.1 总数 - 移除数
    print(f"V5.1 移除后剩余: {len(v51) - len(remove_urls)}")
    print(f"V4 原始: {len(v4)}")

if __name__ == "__main__":
    main()
