"""
检查subagent_image_analysis.json，输出每个源的字段完整度统计。
仅输出技术指标（idx, 字段长度, 是否有特殊配置），不输出业务字段原文。
"""
import json
import os

INPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\subagent_image_analysis.json"

REQUIRED_FIELDS = ["sourceIcon", "searchUrl", "sortUrl", "ruleArticles", "ruleTitle",
                   "ruleLink", "ruleImage", "ruleNextPage", "rulePubDate", "ruleContent"]


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"=== Summary ===")
    print(f"agent: {data.get('agent')}")
    print(f"total_analyzed: {data.get('total_analyzed')}")
    print(f"success_count: {data.get('success_count')}")
    print(f"failed_count: {data.get('failed_count')}")

    print(f"\n=== Per-source Field Stats ===")
    print(f"{'idx':>4} {'tpl':>8} {'accessible':>10} {'fields_count':>12} {'rc_len':>7} {'ri_len':>7} {'notes_count':>11} {'loginUrl':>8} {'cf_block':>8} {'popup':>5}")

    for r in data.get("results", []):
        idx = r.get("idx", -1)
        tpl = r.get("rule_content_template", "unknown")
        accessible = r.get("source_url_accessible", False)
        fields = r.get("fields", {})
        rc_len = len(fields.get("ruleContent", "") or "")
        ri_len = len(fields.get("ruleImage", "") or "")
        notes_count = len(r.get("analysis_notes", []))
        has_login = bool(r.get("special_config", {}).get("loginUrl", ""))
        notes_str = " | ".join(r.get("analysis_notes", []))
        cf_block = "Y" if "cf_block" in notes_str or "cf_block_detected" in notes_str else "N"
        popup = "Y" if "popup_detected" in notes_str else "N"

        # 计算字段完整度
        fields_count = sum(1 for k in REQUIRED_FIELDS if fields.get(k))

        print(f"{idx:>4} {tpl:>8} {str(accessible):>10} {fields_count:>12}/{len(REQUIRED_FIELDS)} {rc_len:>7} {ri_len:>7} {notes_count:>11} {'Y' if has_login else 'N':>8} {cf_block:>8} {popup:>5}")

    print(f"\n=== Field Completeness Distribution ===")
    complete_dist = {}
    for r in data.get("results", []):
        fields = r.get("fields", {})
        cnt = sum(1 for k in REQUIRED_FIELDS if fields.get(k))
        complete_dist[cnt] = complete_dist.get(cnt, 0) + 1
    print(f"fields_count_distribution (out of {len(REQUIRED_FIELDS)}): {complete_dist}")

    print(f"\n=== Template Distribution ===")
    tpl_dist = {}
    for r in data.get("results", []):
        t = r.get("rule_content_template", "unknown")
        tpl_dist[t] = tpl_dist.get(t, 0) + 1
    print(f"template_distribution: {tpl_dist}")

    print(f"\n=== Sources Missing ruleImage (critical) ===")
    for r in data.get("results", []):
        ri = r.get("fields", {}).get("ruleImage", "")
        if not ri:
            print(f"  idx={r.get('idx')} - ruleImage EMPTY")

    print(f"\n=== Sources Missing ruleContent (critical) ===")
    for r in data.get("results", []):
        rc = r.get("fields", {}).get("ruleContent", "")
        if not rc:
            print(f"  idx={r.get('idx')} - ruleContent EMPTY")

    print(f"\n=== Special Config Summary ===")
    for r in data.get("results", []):
        sc = r.get("special_config", {})
        if sc.get("loginUrl") or sc.get("jsRule"):
            print(f"  idx={r.get('idx')}: loginUrl={'Y' if sc.get('loginUrl') else 'N'} jsRule={'Y' if sc.get('jsRule') else 'N'} cookieJar={sc.get('enabledCookieJar')}")

    # 输出每个源的详细notes（已脱敏）
    print(f"\n=== Detailed Analysis Notes (sanitized) ===")
    for r in data.get("results", []):
        idx = r.get("idx", -1)
        notes = r.get("analysis_notes", [])
        print(f"\n[idx={idx}] template={r.get('rule_content_template')}")
        for n in notes:
            # 脱敏：替换可能的URL
            n_safe = n.replace("http://", "[PROTO]//").replace("https://", "[PROTO]//")
            print(f"  - {n_safe[:200]}")


if __name__ == "__main__":
    main()
