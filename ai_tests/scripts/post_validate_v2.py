#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段6 字段合法性后置校验

职责：
1. 修复 ruleNextPage='page' 等无效值
2. 修复 searchUrl='None' 等无效值
3. 修复 Python None 序列化污染
4. 必填字段缺失兜底
5. 输出修复统计

输出安全铁律：
- 脚本输出禁止包含业务字段原文
- 只输出技术指标：idx, field, issue, action

输入：output/rss/optimized_v2.json（阶段5输出）
输出：
  - output/rss/post_validated_v2.json（校验后的JSON）
  - output/rss/v2_post_validate_report.json（校验报告）
"""

import json
import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "post_validated_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_post_validate_report.json"

# 无效值集合
INVALID_VALUES = {'page', 'None', 'null', 'undefined', 'NaN', 'false', 'true', '0', ''}

# 合法的 ruleNextPage 前缀
VALID_NEXT_PAGE_PREFIXES = (
    '@CSS:', '@XPath:', '@js:', '<js>', 'class.', '.', '#', 'text.',
    'li.', 'a.', 'link[', 'script@', '$.', 'div.', 'ul.', 'span.',
    'img.', 'input[', '@put:', '@get:', '(function', 'a@href',
)


def is_valid_rule_next_page(v: str) -> bool:
    """ruleNextPage 合法性校验"""
    if not v or v in INVALID_VALUES:
        return False
    if any(v.startswith(p) for p in VALID_NEXT_PAGE_PREFIXES):
        return True
    if '@href' in v or '<js>' in v:
        return True
    # CSS 选择器模式
    if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>]+', v):
        return True
    return False


def is_valid_url(v: str) -> bool:
    """URL 合法性校验"""
    if not v or v in INVALID_VALUES:
        return False
    return v.startswith(('http://', 'https://', '/'))


def is_valid_css_selector(v: str) -> bool:
    """CSS 选择器合法性校验"""
    if not v or v in INVALID_VALUES:
        return False
    return True  # 简化：非空即认为有效


def apply_mandatory_defaults(source: dict, idx: int, fixes: List[dict]) -> int:
    """必填字段缺失兜底"""
    defaults_applied = 0
    source_url = source.get("sourceUrl", "") or ""

    # sourceIcon 兜底
    if not is_valid_url(source.get("sourceIcon", "")):
        try:
            parsed = urlparse(source_url)
            if parsed.scheme and parsed.netloc:
                new_icon = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
                source["sourceIcon"] = new_icon
                fixes.append({"idx": idx, "field": "sourceIcon", "issue": "missing", "action": "default_favicon"})
                defaults_applied += 1
        except Exception:
            pass

    # searchUrl 兜底
    search = source.get("searchUrl", "") or ""
    if not search or search in INVALID_VALUES or "{{key}}" not in search:
        try:
            parsed = urlparse(source_url)
            if parsed.netloc:
                source["searchUrl"] = f"https://www.google.com/search?q={{key}}+site:{parsed.netloc}"
                fixes.append({"idx": idx, "field": "searchUrl", "issue": "missing_or_no_key", "action": "default_google"})
                defaults_applied += 1
        except Exception:
            pass

    # ruleArticles / ruleTitle / ruleLink / ruleImage 兜底
    for field, default_val in [
        ("ruleArticles", "ul li"),
        ("ruleTitle", "a"),
        ("ruleLink", "a@href"),
        ("ruleImage", "img@src"),
    ]:
        if not is_valid_css_selector(source.get(field, "")):
            source[field] = default_val
            fixes.append({"idx": idx, "field": field, "issue": "missing", "action": f"default_{default_val}"})
            defaults_applied += 1

    return defaults_applied


def main():
    print("=" * 80)
    print("RSS v2 阶段6 字段合法性后置校验")
    print("=" * 80)

    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        return

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {type(e).__name__}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    validated_sources: List[dict] = []
    fixes: List[dict] = []

    fix_stats = {
        'ruleNextPage_invalid': 0,
        'searchUrl_invalid': 0,
        'sortUrl_invalid': 0,
        'sourceIcon_invalid': 0,
        'ruleArticles_invalid': 0,
        'ruleTitle_invalid': 0,
        'ruleLink_invalid': 0,
        'ruleImage_invalid': 0,
        'None_pollution': 0,
        'mandatory_defaults': 0,
    }

    for idx, source in enumerate(sources):
        # 1. 修复 None 污染（Python None 序列化为字符串 "None"）
        for k, v in list(source.items()):
            if v == "None" or v == "null":
                source[k] = ""
                fix_stats['None_pollution'] += 1
                fixes.append({"idx": idx, "field": k, "issue": "none_pollution", "action": "cleared"})

        # 2. 修复 ruleNextPage 无效值
        rnp = source.get("ruleNextPage", "") or ""
        if rnp and not is_valid_rule_next_page(rnp):
            source["ruleNextPage"] = ""
            fix_stats['ruleNextPage_invalid'] += 1
            fixes.append({"idx": idx, "field": "ruleNextPage", "issue": "invalid_value", "action": "cleared"})

        # 3. 修复 searchUrl 无效值
        search = source.get("searchUrl", "") or ""
        if search and search in INVALID_VALUES:
            source["searchUrl"] = ""
            fix_stats['searchUrl_invalid'] += 1
            fixes.append({"idx": idx, "field": "searchUrl", "issue": "invalid_value", "action": "cleared"})

        # 4. 修复 sortUrl 无效值
        sort = source.get("sortUrl", "") or ""
        if sort and sort in INVALID_VALUES:
            source["sortUrl"] = ""
            fix_stats['sortUrl_invalid'] += 1
            fixes.append({"idx": idx, "field": "sortUrl", "issue": "invalid_value", "action": "cleared"})

        # 5. 必填字段缺失兜底
        defaults = apply_mandatory_defaults(source, idx, fixes)
        fix_stats['mandatory_defaults'] += defaults

        validated_sources.append(source)

    # 输出
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(validated_sources, f, ensure_ascii=False, indent=2)

    report = {
        "stage": "post_validate_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "fix_stats": fix_stats,
        "total_fixes": len(fixes),
        "records": fixes,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULT] 后置校验完成")
    print(f"  - 总源数:           {total}")
    print(f"  - 总修复数:         {len(fixes)}")
    print(f"\n[FIX] 修复统计:")
    for k, v in fix_stats.items():
        if v > 0:
            print(f"  - {k:25s}: {v}")
    print(f"\n[OUTPUT]")
    print(f"  - 校验后JSON:      {OUTPUT_JSON}")
    print(f"  - 校验报告:         {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
