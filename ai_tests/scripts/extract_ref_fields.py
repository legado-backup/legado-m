"""
提取参考源idx=0,2,131的字段写法模式（不输出业务字段原文）。
仅输出字段名+字段值的写法模式（如CSS/XPath/JSONPath类型），用于借鉴。
"""
import json
import re
from pathlib import Path

INPUT = Path("output/rss/classified_v2.json")
REF_IDX = [0, 2, 131]


def mask_url(url: str) -> str:
    """路径模式化：只保留路径模式，隐藏域名。"""
    if not url:
        return ""
    # 替换域名为 [DOMAIN]
    s = re.sub(r"https?://[^/]+", "[DOMAIN]", url)
    # 替换数字ID为 {id}
    s = re.sub(r"\d{3,}", "{id}", s)
    return s


def classify_rule(rule: str) -> str:
    """识别规则类型（CSS/XPath/JSONPath/正则/JS）。"""
    if not rule:
        return "empty"
    if rule.startswith("@css:") or rule.startswith("css:"):
        return "CSS"
    if rule.startswith("@XPath:") or rule.startswith("xpath:") or rule.startswith("//"):
        return "XPath"
    if rule.startswith("$.") or rule.startswith("$[") or rule.startswith("$."):
        return "JSONPath"
    if rule.startswith("@js:") or rule.startswith("<js>"):
        return "JS"
    if rule.startswith("@regex:") or rule.startswith("regex:"):
        return "Regex"
    if rule.startswith("##") or rule.startswith("@"):
        return "Filter"
    return "Plain/Mixed"


def main():
    with INPUT.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 60)
    print(f"参考源字段写法分析（共{len(REF_IDX)}个参考源）")
    print("=" * 60)

    for idx in REF_IDX:
        if idx >= len(data):
            print(f"\n[idx={idx}] 超出范围")
            continue
        src = data[idx]
        print(f"\n--- idx={idx} (type={src.get('type', 'N/A')}) ---")

        # 只输出字段名+规则类型，不输出业务字段原文
        fields = [
            "sourceIcon", "searchUrl", "sortUrl",
            "ruleArticles", "ruleTitle", "ruleLink", "ruleImage",
            "ruleNextPage", "rulePubDate", "ruleContent",
            "jsRule", "loginUrl", "enabledCookieJar", "enableJs"
        ]

        for k in fields:
            v = src.get(k, "")
            if v:
                if k in ("sourceIcon", "searchUrl", "sortUrl", "loginUrl"):
                    # URL类字段：路径模式化
                    print(f"  {k}: {mask_url(str(v))}")
                elif k in ("enabledCookieJar", "enableJs"):
                    print(f"  {k}: {v}")
                else:
                    # 规则字段：只输出规则类型+长度
                    print(f"  {k}: type={classify_rule(str(v))}, len={len(str(v))}")
            else:
                print(f"  {k}: empty")

        # 字段总数统计
        total = sum(1 for k in fields if src.get(k))
        print(f"  --> 字段填充数: {total}/{len(fields)}")

    # 统计idx 0-49范围内type=0的源
    print("\n" + "=" * 60)
    print("idx 0-49 范围内 type=0 源统计")
    print("=" * 60)

    target_sources = []
    for idx in range(0, 50):
        if idx >= len(data):
            break
        src = data[idx]
        if src.get("type") == 0:
            comment = str(src.get("sourceComment", ""))
            is_failed = "AI_CLASSIFY:access_failed" in comment
            target_sources.append({
                "idx": idx,
                "is_access_failed": is_failed,
                "has_searchUrl": bool(src.get("searchUrl")),
                "has_jsRule": bool(src.get("jsRule")),
                "field_count": sum(1 for k in fields if src.get(k))
            })

    print(f"总type=0源数: {len(target_sources)}")
    print(f"其中access_failed: {sum(1 for s in target_sources if s['is_access_failed'])}")
    print(f"待深度分析: {sum(1 for s in target_sources if not s['is_access_failed'])}")
    print(f"已有searchUrl: {sum(1 for s in target_sources if s['has_searchUrl'])}")
    print(f"已有jsRule: {sum(1 for s in target_sources if s['has_jsRule'])}")

    # 输出待分析源idx列表
    to_analyze = [s["idx"] for s in target_sources if not s["is_access_failed"]]
    print(f"\n待分析idx列表({len(to_analyze)}个): {to_analyze}")


if __name__ == "__main__":
    main()
