# -*- coding: utf-8 -*-
"""
V5.2 短期止损修复脚本

策略: 移除所有失效拆分子源(占位符+集成站拆分+导航站拆分), 字段完整性修复,
      V4 回填被改坏字段. 输出 optimized_v5_2_stable.json

输入:
  - output/rss/optimized_v2_lite_final_v4.json (V4原始229源, dict格式)
  - output/rss/optimized_v5_1_app_import_fixed.json (V5.1, 328源, list格式)

输出:
  - output/rss/optimized_v5_2_stable.json (纯数组, 可直接App导入)
  - output/rss/v5_2_fix_report.json (修复统计)
"""
import json
import sys
import os
import re
from collections import Counter

ROOT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss"
OUT_JSON = os.path.join(ROOT, "optimized_v5_2_stable.json")
OUT_REPORT = os.path.join(ROOT, "v5_2_fix_report.json")

# 4套集成站通用模板
AGG_TEMPLATES = [".entry-card", ".post,.article,.item", ".lazy", ".thumb"]
NAV_TEMPLATE = ".item,.post,.article,article,.news-item,.entry"

# 默认UA
DEFAULT_UA = ("Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

# Boolean 字段默认值 (按 RssSource.kt)
BOOL_DEFAULTS = {
    "enabled": True,
    "enabledCookieJar": True,
    "singleUrl": False,
    "enableJs": True,
    "loadWithBaseUrl": True,
    "showWebLog": False,
    "preload": False,
    "cacheFirst": True,
}

# Int 字段默认值
INT_DEFAULTS = {
    "articleStyle": 0,
    "customOrder": 0,
    "type": 0,
    "parseConcurrency": 0,
    "weight": 0,
    "lastUpdateTime": 0,
}

PLACEHOLDER_MARKERS = ["[DOMAIN]", "{DOMAIN}", "{{domain}}", "{{DOMAIN}}", "<DOMAIN>"]


def is_placeholder_url(url):
    if not isinstance(url, str) or not url:
        return True
    return any(m in url for m in PLACEHOLDER_MARKERS)


def is_template_rule_articles(ra):
    if not isinstance(ra, str):
        return False
    return ra in AGG_TEMPLATES or ra == NAV_TEMPLATE


def load_json(name):
    path = os.path.join(ROOT, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_sources(data):
    """从 dict/list 提取源列表"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "sources" in data and isinstance(data["sources"], list):
            return data["sources"]
        for k in ["data", "list", "items"]:
            if k in data and isinstance(data[k], list):
                return data[k]
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def classify_remove(src):
    """识别需要移除的源, 返回原因代码(None=保留)"""
    url = src.get("sourceUrl", "")
    ra = src.get("ruleArticles")
    header = src.get("header")
    ecj = src.get("enabledCookieJar")

    # 占位符源
    if is_placeholder_url(url):
        return "PLACEHOLDER_URL"

    # 导航站拆分: ruleArticles==NAV模板
    if ra == NAV_TEMPLATE:
        return "NAV_SPLIT_TEMPLATE"

    # 集成站拆分: header空字符串 + ecj=False + ruleArticles在4套模板中
    if (isinstance(ra, str) and ra in AGG_TEMPLATES
            and header == "" and ecj is False):
        return "AGG_SPLIT_TEMPLATE"

    return None


def fix_field_types(src):
    """字段类型修复 + Boolean null 填充默认值. 返回修复计数"""
    cnt = 0
    # Boolean 字段: null → 默认值; 字符串"0"/"1"/"true"/"false" → boolean
    for f, default in BOOL_DEFAULTS.items():
        v = src.get(f)
        if v is None:
            src[f] = default
            cnt += 1
        elif isinstance(v, str):
            if v.lower() in ("true", "1", "yes"):
                src[f] = True
                cnt += 1
            elif v.lower() in ("false", "0", "no", ""):
                src[f] = False
                cnt += 1
        elif isinstance(v, int) and not isinstance(v, bool):
            src[f] = bool(v)
            cnt += 1

    # Int 字段: 字符串 → int
    for f, default in INT_DEFAULTS.items():
        v = src.get(f)
        if v is None:
            src[f] = default
            cnt += 1
        elif isinstance(v, str):
            try:
                src[f] = int(v)
                cnt += 1
            except ValueError:
                src[f] = default
                cnt += 1
        elif isinstance(v, bool):
            # 误把bool当int
            src[f] = int(v)
            cnt += 1

    # singleUrl 必须是 boolean (不能是 0/1)
    su = src.get("singleUrl")
    if not isinstance(su, bool):
        src["singleUrl"] = bool(su) if su is not None else False
        cnt += 1

    return cnt


def fix_rule_articles_separator(src):
    """ruleArticles 逗号分隔 → || 分隔 (仅当形如 .a,.b,.c 的CSS选择器列表)"""
    cnt = 0
    ra = src.get("ruleArticles")
    if not isinstance(ra, str) or not ra:
        return 0
    # 仅当包含多个逗号分隔的 CSS 选择器, 且不含 @js/@XPath@ 等表达式
    if ra.startswith("@") or "@js:" in ra or "@XPath" in ra or "{{" in ra:
        return 0
    # 匹配 ".a,.b,.c" 形式: 多个简短 token 用逗号分隔
    if "," in ra and "||" not in ra and "%%" not in ra:
        # 检查每个 token 是否像 CSS 选择器 (以 . # 或字母开头)
        tokens = [t.strip() for t in ra.split(",") if t.strip()]
        if len(tokens) >= 2 and all(re.match(r"^[.#a-zA-Z\[<:]", t) for t in tokens):
            # 但要排除 "div,p" 这类标准 CSS (保留逗号即可, jsoup 支持)
            # 仅在模板列表中或长度<100时替换
            if ra in AGG_TEMPLATES or ra == NAV_TEMPLATE:
                # 这些是套模板的, 已经会被移除
                return 0
            # 一般情况: 不替换, 因为 Legado 也支持 CSS 逗号分隔
            # 仅替换明显的多规则: 多个完全独立的复杂表达式
    return cnt


def fix_header(src):
    """header 空/缺失 → 默认UA"""
    cnt = 0
    h = src.get("header")
    if h is None or (isinstance(h, str) and h.strip() == ""):
        src["header"] = json.dumps({"User-Agent": DEFAULT_UA}, ensure_ascii=False)
        cnt += 1
    return cnt


def fix_enabled_cookie_jar(src):
    """enabledCookieJar 缺失 → True (RssSource 默认值)"""
    cnt = 0
    v = src.get("enabledCookieJar")
    if v is None:
        src["enabledCookieJar"] = True
        cnt += 1
    elif not isinstance(v, bool):
        src["enabledCookieJar"] = bool(v)
        cnt += 1
    return cnt


def fix_disabled_sources(src):
    """本应禁用的源(enabled=true 但 sourceGroup 含'已废/失效/停更') → enabled=False"""
    cnt = 0
    g = src.get("sourceGroup") or ""
    if src.get("enabled") is True and any(m in g for m in ["已废", "失效", "停更"]):
        src["enabled"] = False
        cnt += 1
    return cnt


def v4_backfill(src, v4_map):
    """从 V4 回填 V5 改坏的字段 (cacheFirst/header/rulePubDate/ruleNextPage/ruleArticles).
       仅当 V5 字段为空或截短时回填"""
    cnt = 0
    url = src.get("sourceUrl", "")
    v4src = v4_map.get(url)
    if not v4src:
        return 0
    # 回填字段: V5 缺失或为空, V4 有值
    backfill_fields = ["cacheFirst", "header", "rulePubDate", "ruleNextPage",
                       "ruleArticles", "ruleTitle", "ruleLink", "ruleImage", "ruleContent"]
    for f in backfill_fields:
        v5v = src.get(f)
        v4v = v4src.get(f)
        # V5 缺失/空, V4 有值 → 回填
        v5_empty = (v5v is None) or (isinstance(v5v, str) and v5v.strip() == "")
        v4_has = (v4v is not None) and (isinstance(v4v, str) and v4v.strip() != "")
        if v5_empty and v4_has:
            src[f] = v4v
            cnt += 1
    return cnt


def main():
    print("[1/6] 加载 V4 原始 229 源...")
    v4_raw = load_json("optimized_v2_lite_final_v4.json")
    v4_sources = extract_sources(v4_raw)
    v4_map = {s.get("sourceUrl", ""): s for s in v4_sources}
    print(f"    V4 源数: {len(v4_sources)}")

    print("[2/6] 加载 V5.1 328 源...")
    v51 = load_json("optimized_v5_1_app_import_fixed.json")
    if isinstance(v51, dict):
        v51 = extract_sources(v51)
    print(f"    V5.1 源数: {len(v51)}")

    print("[3/6] 识别并移除失效拆分子源...")
    keep_list = []
    remove_list = []
    remove_reasons = Counter()
    for s in v51:
        reason = classify_remove(s)
        if reason:
            remove_list.append(s)
            remove_reasons[reason] += 1
        else:
            keep_list.append(s)
    print(f"    移除: {len(remove_list)} 源")
    for r, c in remove_reasons.most_common():
        print(f"      - {r}: {c}")
    print(f"    保留: {len(keep_list)} 源")

    print("[4/6] 字段完整性修复...")
    fix_counts = {
        "type_fix": 0,
        "header_ua": 0,
        "enabled_cookie_jar": 0,
        "disabled_sources": 0,
        "rule_articles_sep": 0,
        "v4_backfill": 0,
    }
    for s in keep_list:
        fix_counts["type_fix"] += fix_field_types(s)
        fix_counts["header_ua"] += fix_header(s)
        fix_counts["enabled_cookie_jar"] += fix_enabled_cookie_jar(s)
        fix_counts["disabled_sources"] += fix_disabled_sources(s)
        fix_counts["rule_articles_sep"] += fix_rule_articles_separator(s)
        fix_counts["v4_backfill"] += v4_backfill(s, v4_map)
    total_fixes = sum(fix_counts.values())
    print(f"    字段修复总数: {total_fixes}")
    for k, v in fix_counts.items():
        print(f"      - {k}: {v}")

    print("[5/6] 字段最终校验 + 去重...")
    # 校验所有源都有 sourceUrl + sourceName
    valid = []
    seen_urls = set()
    for s in keep_list:
        url = s.get("sourceUrl", "")
        if not url or not isinstance(url, str):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        # 确保 sourceName 非空
        if not s.get("sourceName"):
            s["sourceName"] = "src_" + str(len(valid))
        valid.append(s)
    print(f"    去重后有效源数: {len(valid)}")

    print("[6/6] 输出文件...")
    # 输出修复后 JSON (纯数组格式, App可直接导入)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(valid, f, ensure_ascii=False, indent=2)
    print(f"    输出: {OUT_JSON} ({len(valid)} 源)")

    # 输出修复统计报告
    report = {
        "input": {
            "v4_sources": len(v4_sources),
            "v5_1_sources": len(v51),
        },
        "removed": {
            "total": len(remove_list),
            "by_reason": dict(remove_reasons),
            "detail": {
                "PLACEHOLDER_URL": "sourceUrl含[DOMAIN]等占位符的源",
                "NAV_SPLIT_TEMPLATE": "导航站拆分子源(ruleArticles=nav模板)",
                "AGG_SPLIT_TEMPLATE": "集成站拆分子源(header空+ecj=False+模板RA)",
            },
        },
        "kept": len(valid),
        "field_fixes": {
            "total": total_fixes,
            "by_type": fix_counts,
            "detail": {
                "type_fix": "字段类型修复(Boolean null→默认值/字符串→int/singleUrl→bool)",
                "header_ua": "header空/缺失→默认UA",
                "enabled_cookie_jar": "enabledCookieJar缺失→True",
                "disabled_sources": "错误启用源(enabled=true但group含已废标记)→False",
                "rule_articles_sep": "ruleArticles逗号分隔→||分隔(实际未替换,jsoup原生支持)",
                "v4_backfill": "从V4回填V5改坏的字段(cacheFirst/header/rulePubDate/ruleNextPage等)",
            },
        },
        "output_json": OUT_JSON,
        "summary": {
            "original_v5_1": len(v51),
            "removed": len(remove_list),
            "kept": len(valid),
            "field_fixes_total": total_fixes,
            "vs_v5_1": f"+{len(valid) - len(v51)}",
        },
    }
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"    报告: {OUT_REPORT}")

    print("\n=== 修复完成 ===")
    print(f"原 V5.1: {len(v51)} 源")
    print(f"移除: {len(remove_list)} 源")
    print(f"保留: {len(valid)} 源")
    print(f"字段修复: {total_fixes} 处")


if __name__ == "__main__":
    main()
