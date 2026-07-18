#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段2 预处理脚本

职责：
1. 识别占位符源（sourceUrl长度<20 或 非http开头），从 sourceComment 提取候选 URL
2. 识别模板源（sourceUrl 含 {{}}），提取 base_url
3. 输出预处理后的 JSON + 预处理报告

输出安全铁律（不可违背）：
- 脚本输出禁止包含业务字段原文（sourceName/sourceUrl/sourceComment 内容）
- 只输出技术指标：idx, length, classification, is_http_prefix, has_template, extracted_url_len
- 异常消息必须脱敏（替换 URL/域名为 [URL]/[DOMAIN]）

输入：temp/rss/rssSource_202607131357/rssSource_202607182145..json（222源）
输出：
  - output/rss/preprocessed_v2.json（预处理后的JSON，结构完整）
  - output/rss/v2_preprocess_report.json（预处理报告，仅技术指标）
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent  # ai_tests/scripts/../.. → legado/
INPUT_JSON = PROJECT_ROOT / "temp" / "rss" / "rssSource_202607131357" / "rssSource_202607182145..json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "rss"
OUTPUT_JSON = OUTPUT_DIR / "preprocessed_v2.json"
OUTPUT_REPORT = OUTPUT_DIR / "v2_preprocess_report.json"

# 占位符源判定：sourceUrl 长度 < 20 或 非http开头
PLACEHOLDER_MIN_LEN = 20

# 模板源判定：含 {{...}}
TEMPLATE_PATTERN = re.compile(r"\{\{.*?\}\}")

# URL 提取正则
URL_EXTRACT_PATTERN = re.compile(r"https?://[^\s\"'<>]+")

# sourceComment 中的候选域名提示关键词
DOMAIN_HINT_KEYWORDS = [
    "永久入口", "最新域名", "备用域名", "发布页", "新地址",
    "新域名", "域名获取", "获取地址", "网址发布", "官网"
]


def is_placeholder_source(source_url: str) -> bool:
    """判定占位符源：长度<20 或 非http开头"""
    if not source_url:
        return True
    if len(source_url) < PLACEHOLDER_MIN_LEN:
        return True
    if not source_url.startswith(("http://", "https://")):
        return True
    return False


def is_template_source(source_url: str) -> bool:
    """判定模板源：含 {{...}}"""
    return bool(TEMPLATE_PATTERN.search(source_url))


def extract_base_url(source_url: str) -> Optional[str]:
    """从模板URL提取base_url：去除 {{...}} 部分"""
    base = TEMPLATE_PATTERN.sub("", source_url)
    # 清理末尾的斜杠和问号
    base = base.rstrip("/?")
    if base.startswith(("http://", "https://")):
        return base
    return None


def extract_url_from_comment(source_comment: str) -> Tuple[Optional[str], str]:
    """从 sourceComment 提取候选URL

    返回: (候选URL, 提取方式)
    """
    if not source_comment:
        return None, "no_comment"

    # 优先匹配关键词后的URL（永久入口:/最新域名:等）
    for keyword in DOMAIN_HINT_KEYWORDS:
        pattern = rf"{keyword}[：:\s]*(https?://[^\s\"'<>]+)"
        m = re.search(pattern, source_comment, re.IGNORECASE)
        if m:
            return m.group(1), f"hint:{keyword}"

    # 兜底：提取所有 http(s):// URL
    urls = URL_EXTRACT_PATTERN.findall(source_comment)
    if urls:
        return urls[0], "first_url"

    return None, "no_url_in_comment"


def sanitize_exception(e: Exception) -> str:
    """脱敏异常消息：替换URL/域名为代号"""
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def classify_source(source: dict) -> Tuple[str, dict]:
    """分类单个源

    返回: (classification, meta)
    classification: 'normal' / 'placeholder' / 'template' / 'placeholder_with_hint'
    meta: 技术指标（不含业务字段）
    """
    source_url = source.get("sourceUrl", "") or ""

    # 占位符源
    if is_placeholder_source(source_url):
        # 尝试从 sourceComment 提取候选URL
        comment = source.get("sourceComment", "") or ""
        candidate_url, extract_method = extract_url_from_comment(comment)

        if candidate_url:
            # 用候选URL替换sourceUrl
            source["sourceUrl"] = candidate_url
            source["sourceComment"] = (
                source.get("sourceComment", "") or ""
            ) + f"\n[AI_PREPROCESS:placeholder_recovered|method={extract_method}]"

            return "placeholder_with_hint", {
                "original_url_len": len(source_url),
                "extracted_url_len": len(candidate_url),
                "extract_method": extract_method,
                "is_http_prefix": candidate_url.startswith("http"),
            }
        else:
            # 无法恢复，标记为 needs_manual
            source["sourceComment"] = (
                source.get("sourceComment", "") or ""
            ) + "\n[AI_PREPROCESS:needs_manual|reason=placeholder_no_hint]"

            return "placeholder", {
                "original_url_len": len(source_url),
                "is_http_prefix": source_url.startswith("http"),
                "needs_manual": True,
            }

    # 模板源
    if is_template_source(source_url):
        base_url = extract_base_url(source_url)
        if base_url:
            # 保留原sourceUrl（含模板），但记录base_url到sourceComment供后续使用
            source["sourceComment"] = (
                source.get("sourceComment", "") or ""
            ) + f"\n[AI_PREPROCESS:template_base_url|base={base_url[:50]}***]"

            return "template", {
                "original_url_len": len(source_url),
                "has_template": True,
                "base_url_len": len(base_url),
                "base_url_is_http": base_url.startswith("http"),
            }
        else:
            return "template_invalid", {
                "original_url_len": len(source_url),
                "has_template": True,
                "base_url_extracted": False,
            }

    # 正常源
    return "normal", {
        "original_url_len": len(source_url),
        "is_http_prefix": source_url.startswith("http"),
    }


def main():
    print("=" * 80)
    print("RSS v2 阶段2 预处理脚本")
    print("=" * 80)

    # 1. 读取输入JSON
    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        return

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {sanitize_exception(e)}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    # 2. 分类处理
    classified_sources: List[dict] = []
    report_records: List[dict] = []

    classification_stats = {
        "normal": 0,
        "placeholder": 0,
        "placeholder_with_hint": 0,
        "template": 0,
        "template_invalid": 0,
    }

    for idx, source in enumerate(sources):
        try:
            classification, meta = classify_source(source)
            classified_sources.append(source)

            classification_stats[classification] = classification_stats.get(classification, 0) + 1

            # 记录报告（仅技术指标，不含业务字段）
            report_records.append({
                "idx": idx,
                "classification": classification,
                **meta,
            })

        except Exception as e:
            # 异常时保留原源，标记 needs_manual
            source["sourceComment"] = (
                source.get("sourceComment", "") or ""
            ) + f"\n[AI_PREPROCESS:exception|msg={sanitize_exception(e)}]"
            classified_sources.append(source)

            report_records.append({
                "idx": idx,
                "classification": "exception",
                "error_type": type(e).__name__,
            })

    # 3. 输出预处理后的JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(classified_sources, f, ensure_ascii=False, indent=2)

    # 4. 输出预处理报告
    report = {
        "stage": "preprocess_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "classification_stats": classification_stats,
        "recovered_count": classification_stats.get("placeholder_with_hint", 0),
        "needs_manual_count": classification_stats.get("placeholder", 0),
        "template_count": classification_stats.get("template", 0),
        "template_invalid_count": classification_stats.get("template_invalid", 0),
        "normal_count": classification_stats.get("normal", 0),
        "records": report_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 5. 打印汇总（仅技术指标）
    print(f"\n[RESULT] 预处理完成")
    print(f"  - 输入源总数:        {total}")
    print(f"  - 正常源:            {classification_stats['normal']}")
    print(f"  - 占位符源(可恢复):  {classification_stats['placeholder_with_hint']}")
    print(f"  - 占位符源(待人工):  {classification_stats['placeholder']}")
    print(f"  - 模板源(已提取):    {classification_stats['template']}")
    print(f"  - 模板源(无效):      {classification_stats['template_invalid']}")
    print(f"\n[OUTPUT]")
    print(f"  - 预处理后JSON:     {OUTPUT_JSON}")
    print(f"  - 预处理报告:        {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
