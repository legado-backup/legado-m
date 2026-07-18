"""
筛选 classified_v2.json 中 type=1 的图片源，并提取参考源(idx=50/60/76)的技术字段。
仅输出技术指标，不输出业务字段原文（sourceName/sourceComment/title/summary等）。
"""
import json
import os
import re
from urllib.parse import urlparse

INPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\classified_v2.json"
OUTPUT_FILE = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\image_sources_preview.json"

# 业务字段黑名单（不输出）
SENSITIVE_FIELDS = {"sourceName", "sourceComment", "sourceUrl", "searchUrl", "sortUrl"}


def sanitize_url(url):
    """脱敏URL：只保留路径模式，域名替换为[DOMAIN]"""
    if not isinstance(url, str) or not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path or ""
        # 保留查询参数的key，不保留value
        query_keys = []
        if parsed.query:
            for kv in parsed.query.split("&"):
                k = kv.split("=")[0]
                query_keys.append(k)
        query_str = "?" + "&".join(f"{k}={{{{}}}}" for k in query_keys) if query_keys else ""
        return f"[DOMAIN]{path}{query_str}"
    except Exception:
        return "[URL]"


def extract_technical_fields(source):
    """提取技术字段（非业务数据字段）"""
    return {
        "idx": source.get("customOrder", 0),
        "type": source.get("type", -1),
        "enableJs": source.get("enableJs", False),
        "enabledCookieJar": source.get("enabledCookieJar", False),
        "loadWithBaseUrl": source.get("loadWithBaseUrl", False),
        "lastHost": source.get("lastHost", ""),
        "sourceGroup": source.get("sourceGroup", ""),
        "articleStyle": source.get("articleStyle", 0),
        # 规则字段（技术字段）
        "ruleArticles": source.get("ruleArticles", ""),
        "ruleTitle": source.get("ruleTitle", ""),
        "ruleLink": source.get("ruleLink", ""),
        "ruleImage": source.get("ruleImage", ""),
        "ruleNextPage": source.get("ruleNextPage", ""),
        "rulePubDate": source.get("rulePubDate", ""),
        "ruleContent": source.get("ruleContent", ""),
        "sourceIcon_pattern": sanitize_url(source.get("sourceIcon", "")),
        "loginUrl_pattern": sanitize_url(source.get("loginUrl", "")),
        # 字段长度统计（不输出原文）
        "ruleContent_length": len(source.get("ruleContent", "") or ""),
        "ruleImage_length": len(source.get("ruleImage", "") or ""),
    }


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    print(f"[INFO] total sources: {len(sources)}")

    # 统计type分布
    type_dist = {}
    for s in sources:
        t = s.get("type", -1)
        type_dist[t] = type_dist.get(t, 0) + 1
    print(f"[INFO] type distribution: {type_dist}")

    # 筛选type=1
    image_sources = [s for s in sources if s.get("type", -1) == 1]
    print(f"[INFO] type=1 sources count: {len(image_sources)}")

    # 参考源 idx=50, 60, 76（按数组索引，不是customOrder）
    reference_idx = [50, 60, 76]
    references = []
    for i in reference_idx:
        if 0 <= i < len(sources):
            s = sources[i]
            ref = extract_technical_fields(s)
            ref["array_idx"] = i
            references.append(ref)
            print(f"\n[REF] array_idx={i} type={s.get('type')} ruleContent_len={ref['ruleContent_length']} ruleImage_len={ref['ruleImage_length']}")
            print(f"      ruleArticles: {ref['ruleArticles'][:80]}")
            print(f"      ruleImage: {ref['ruleImage'][:80]}")
            print(f"      ruleContent: {ref['ruleContent'][:120]}...")

    # 输出所有type=1源的idx和技术字段
    image_list = []
    for i, s in enumerate(sources):
        if s.get("type", -1) != 1:
            continue
        item = extract_technical_fields(s)
        item["array_idx"] = i
        # 脱敏的sourceUrl路径模式
        item["sourceUrl_pattern"] = sanitize_url(s.get("sourceUrl", ""))
        item["sourceIcon_pattern"] = sanitize_url(s.get("sourceIcon", ""))
        image_list.append(item)

    output = {
        "total_type1": len(image_list),
        "references": references,
        "image_sources": image_list,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] preview saved to: {OUTPUT_FILE}")
    print(f"[OK] type=1 count: {len(image_list)}")
    print("\n[List] type=1 sources idx list:")
    for item in image_list:
        print(f"  - array_idx={item['array_idx']} customOrder={item['idx']} lastHost={item['lastHost']} ruleContent_len={item['ruleContent_length']}")


if __name__ == "__main__":
    main()
