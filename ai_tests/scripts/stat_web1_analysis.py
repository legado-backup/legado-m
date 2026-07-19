"""
统计 subagent_web1_analysis.json 的结果，只输出技术指标。
不输出业务字段原文 (sourceName/sourceUrl/sourceComment)。
"""
import json
from collections import Counter
from pathlib import Path

INPUT = Path("output/rss/subagent_web1_analysis.json")

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print("网页源深度分析第一批 - 结果统计")
print("=" * 70)
print(f"agent: {data['agent']}")
print(f"batch_range: {data['batch_range']}")
print(f"total_analyzed: {data['total_analyzed']}")
print(f"success_count: {data['success_count']}")
print(f"failed_count: {data['failed_count']}")

# 字段补全统计
fields_to_check = [
    "sourceIcon", "searchUrl", "sortUrl",
    "ruleArticles", "ruleTitle", "ruleLink", "ruleImage",
    "ruleNextPage", "rulePubDate", "ruleContent"
]
sc_to_check = ["loginUrl", "enabledCookieJar", "enableJs", "loadWithBaseUrl", "jsRule"]

# 原始字段非空率 vs 分析后非空率
print("\n--- 字段非空统计 (分析后) ---")
field_filled = {k: 0 for k in fields_to_check + sc_to_check}
for r in data["results"]:
    for k in fields_to_check:
        if r["fields"].get(k):
            field_filled[k] += 1
    for k in sc_to_check:
        if r["special_config"].get(k):
            field_filled[k] += 1

for k in fields_to_check + sc_to_check:
    cnt = field_filled[k]
    pct = cnt * 100 / len(data["results"])
    print(f"  {k:25s}: {cnt:3d}/{len(data['results'])} ({pct:.1f}%)")

# searchUrl 补全情况
print("\n--- searchUrl 补全情况 ---")
search_url_inferred = 0
search_url_total = 0
for r in data["results"]:
    if "searchUrl inferred" in r.get("analysis_notes", ""):
        search_url_inferred += 1
    if r["fields"].get("searchUrl"):
        search_url_total += 1
print(f"  原有searchUrl: {search_url_total - search_url_inferred}")
print(f"  本次补全searchUrl: {search_url_inferred}")
print(f"  总searchUrl数: {search_url_total}/{len(data['results'])}")

# jsRule 补全情况
print("\n--- jsRule 补全情况 ---")
jsrule_inferred = 0
for r in data["results"]:
    if "jsRule inferred" in r.get("analysis_notes", ""):
        jsrule_inferred += 1
print(f"  本次补全jsRule: {jsrule_inferred}/{len(data['results'])}")

# 页面信号统计
print("\n--- 页面信号统计 ---")
popup_count = 0
cf_count = 0
search_form_count = 0
search_link_count = 0
best_list_count_dist = Counter()
paging_count = 0
login_link_count = 0

for r in data["results"]:
    sig = r.get("page_signals", {}) or {}
    if sig.get("popup_count", 0) > 0:
        popup_count += 1
    if sig.get("cloudflare", False):
        cf_count += 1
    if sig.get("search_form_count", 0) > 0:
        search_form_count += 1
    if sig.get("search_link_count", 0) > 0:
        search_link_count += 1
    if sig.get("best_list_selector"):
        best_list_count_dist[sig["best_list_selector"]] += 1
    if sig.get("paging_selector"):
        paging_count += 1
    if sig.get("login_link_count", 0) > 0:
        login_link_count += 1

print(f"  含弹框的源: {popup_count}")
print(f"  含Cloudflare盾的源: {cf_count}")
print(f"  含搜索表单的源: {search_form_count}")
print(f"  含搜索链接的源: {search_link_count}")
print(f"  含分页的源: {paging_count}")
print(f"  含登录链接的源: {login_link_count}")
print(f"  列表选择器分布: {dict(best_list_count_dist.most_common(10))}")

# 失败源列表
print("\n--- 失败源 (source_url_accessible=False) ---")
for r in data["results"]:
    if not r["source_url_accessible"]:
        notes = r.get("analysis_notes", "")[:120]
        print(f"  idx={r['idx']}: {notes}")

# 成功源列表 (简要)
print("\n--- 各源分析摘要 ---")
for r in data["results"]:
    accessible = r["source_url_accessible"]
    notes = r.get("analysis_notes", "").strip(" |")[:80]
    sig = r.get("page_signals", {}) or {}
    popup = sig.get("popup_count", 0)
    cf = "CF" if sig.get("cloudflare") else ""
    sf = sig.get("search_form_count", 0)
    bl = sig.get("best_list_selector", "") or "-"
    print(f"  idx={r['idx']:3d} acc={accessible} popup={popup} sf={sf} cf={cf:2s} list={bl:30s} notes={notes}")

print("\n--- 输出文件 ---")
print(f"  {INPUT}")
print(f"  文件大小: {INPUT.stat().st_size} bytes")
