# -*- coding: utf-8 -*-
"""
合并4个深度优化子代理修复成果到V4最终版订阅源JSON。

输入:
  - output/rss/optimized_v2_lite_final_v3.json (V3基础数据229源)
  - output/rss/video_source_deep_fix.json
  - output/rss/image_source_deep_fix_v2.json
  - output/rss/web_source_deep_fix.json
  - output/rss/disabled_source_reaccess.json

输出:
  - output/rss/optimized_v2_lite_final_v4.json
  - output/rss/v4_merge_report.json

输出安全: 不输出任何源名称/URL/分类名, 仅用源[idx]引用, 异常消息脱敏。
"""
import json
import os
import sys
import copy
from datetime import datetime
from collections import Counter

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RSS_DIR = os.path.join(BASE, "output", "rss")

V3_PATH = os.path.join(RSS_DIR, "optimized_v2_lite_final_v3.json")
VIDEO_PATH = os.path.join(RSS_DIR, "video_source_deep_fix.json")
IMAGE_PATH = os.path.join(RSS_DIR, "image_source_deep_fix_v2.json")
WEB_PATH = os.path.join(RSS_DIR, "web_source_deep_fix.json")
DISABLED_PATH = os.path.join(RSS_DIR, "disabled_source_reaccess.json")

V4_PATH = os.path.join(RSS_DIR, "optimized_v2_lite_final_v4.json")
REPORT_PATH = os.path.join(RSS_DIR, "v4_merge_report.json")


def is_blank(v):
    """空判定: None / 空串 / 仅空白"""
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def safe_get(rec, key):
    """安全取字段, 不抛异常"""
    try:
        return rec.get(key)
    except Exception:
        return None


def append_comment(src, marker):
    """在sourceComment末尾追加标记, 不破坏原内容"""
    cur = src.get("sourceComment") or ""
    if cur and not cur.endswith(" ") and not cur.endswith("\n"):
        cur = cur + " "
    src["sourceComment"] = (cur + marker).strip()


def fill_fields(src, rec, field_pairs, log_filled, log_skipped):
    """
    通用字段填充: 仅当原字段为空时, 用rec对应字段填充。
    field_pairs: list of (src_key, rec_key)
    返回: 填充的字段数
    """
    filled = 0
    for src_key, rec_key in field_pairs:
        if is_blank(src.get(src_key)):
            val = safe_get(rec, rec_key)
            if not is_blank(val):
                src[src_key] = val
                filled += 1
                log_filled.append((src_key,))
            else:
                log_skipped.append((src_key, "rec_value_blank"))
        else:
            log_skipped.append((src_key, "src_already_has_value"))
    return filled


def main():
    # Step1: 加载V3
    print("[INFO] loading V3 base data...")
    with open(V3_PATH, "r", encoding="utf-8") as f:
        v3 = json.load(f)
    sources = v3.get("sources", [])
    total = len(sources)
    print(f"[INFO] V3 sources loaded: {total}")

    # 复制一份做V4 (深拷贝, 避免污染V3)
    v4_sources = copy.deepcopy(sources)
    v3_enabled_count = sum(1 for s in sources if s.get("enabled"))
    v3_disabled_count = total - v3_enabled_count
    print(f"[INFO] V3 enabled={v3_enabled_count} disabled={v3_disabled_count}")

    # 统计计数器
    video_applied = 0
    image_applied = 0
    web_applied = 0
    disabled_recovered = 0
    still_disabled_after_reaccess = 0

    # 调试用: 字段填充数 / 跳过数
    fill_log = {"video": [], "image": [], "web": []}

    # Step2: 应用视频源修复
    print("[INFO] applying video_source_deep_fix...")
    with open(VIDEO_PATH, "r", encoding="utf-8") as f:
        video_data = json.load(f)
    video_recs = video_data.get("records", [])
    for rec in video_recs:
        idx = rec.get("idx")
        if idx is None or idx < 0 or idx >= total:
            print(f"[WARN] video rec idx out of range: {idx}")
            continue
        src = v4_sources[idx]
        # 填充6个字段
        pairs = [
            ("sortUrl", "sort_url_filled"),
            ("searchUrl", "search_url_filled"),
            ("ruleArticles", "rule_articles_filled"),
            ("ruleImage", "rule_image_filled"),
            ("ruleNextPage", "rule_next_page_filled"),
            ("ruleContent", "rule_content_filled"),
        ]
        fill_fields(src, rec, pairs, fill_log["video"], [])
        # sourceComment追加: method字段视频源里没有, 用template_type替代
        method = rec.get("method") or rec.get("template_type") or "unknown"
        verify_ok = rec.get("verify_ok")
        items = rec.get("list_items_count")
        marker = f"[AI_V4:video_deep_fix|method={method}|verify={verify_ok}|items={items}]"
        append_comment(src, marker)
        video_applied += 1
    print(f"[INFO] video fix applied to {video_applied} sources")

    # Step3: 应用图片源修复
    print("[INFO] applying image_source_deep_fix_v2...")
    with open(IMAGE_PATH, "r", encoding="utf-8") as f:
        image_data = json.load(f)
    image_recs = image_data.get("records", [])
    for rec in image_recs:
        idx = rec.get("idx")
        if idx is None or idx < 0 or idx >= total:
            print(f"[WARN] image rec idx out of range: {idx}")
            continue
        src = v4_sources[idx]
        pairs = [
            ("sortUrl", "sort_url_filled"),
            ("searchUrl", "search_url_filled"),
            ("ruleArticles", "rule_articles_filled"),
            ("ruleImage", "rule_image_filled"),
            ("ruleNextPage", "rule_next_page_filled"),
            ("ruleContent", "rule_content_filled"),
        ]
        fill_fields(src, rec, pairs, fill_log["image"], [])
        template_type = rec.get("template_type") or "unknown"
        verify_ok = rec.get("verify_ok")
        items = rec.get("list_items_count")
        marker = f"[AI_V4:image_deep_fix|template={template_type}|verify={verify_ok}|items={items}]"
        append_comment(src, marker)
        image_applied += 1
    print(f"[INFO] image fix applied to {image_applied} sources")

    # Step4: 应用网页源修复
    print("[INFO] applying web_source_deep_fix...")
    with open(WEB_PATH, "r", encoding="utf-8") as f:
        web_data = json.load(f)
    web_recs = web_data.get("records", [])
    for rec in web_recs:
        idx = rec.get("idx")
        if idx is None or idx < 0 or idx >= total:
            print(f"[WARN] web rec idx out of range: {idx}")
            continue
        src = v4_sources[idx]
        # 网页源record有rule_title_filled/rule_pub_date_filled, 任务未列出, 仅填充6字段
        pairs = [
            ("sortUrl", "sort_url_filled"),
            ("searchUrl", "search_url_filled"),
            ("ruleArticles", "rule_articles_filled"),
            ("ruleImage", "rule_image_filled"),
            ("ruleNextPage", "rule_next_page_filled"),
            ("ruleContent", "rule_content_filled"),
        ]
        fill_fields(src, rec, pairs, fill_log["web"], [])
        site_type = rec.get("site_type") or "unknown"
        verify_ok = rec.get("verify_ok")
        items = rec.get("list_items_count")
        marker = f"[AI_V4:web_deep_fix|site_type={site_type}|verify={verify_ok}|items={items}]"
        append_comment(src, marker)
        web_applied += 1
    print(f"[INFO] web fix applied to {web_applied} sources")

    # Step5: 应用禁用源重新评估
    print("[INFO] applying disabled_source_reaccess...")
    with open(DISABLED_PATH, "r", encoding="utf-8") as f:
        disabled_data = json.load(f)
    dis_recs = disabled_data.get("records", [])
    for rec in dis_recs:
        idx = rec.get("idx")
        if idx is None or idx < 0 or idx >= total:
            print(f"[WARN] disabled rec idx out of range: {idx}")
            continue
        src = v4_sources[idx]
        rm = rec.get("recovered_method") or ""
        notes = rec.get("notes") or ""
        ed = rec.get("enabled_decision")

        # 优先级: recovered_method判定 -> notes判定
        if rm == "mobile_context":
            src["enabled"] = True
            append_comment(src, "[AI_V4:recovered_by_mobile|ua=mobile|viewport=375x667]")
            disabled_recovered += 1
        elif rm == "tls_disable_timeout":
            src["enabled"] = True
            append_comment(src, "[AI_V4:recovered_by_tls_disable]")
            disabled_recovered += 1
        elif notes == "dead_404":
            src["enabled"] = False
            append_comment(src, "[AI_V4:dead_404]")
            still_disabled_after_reaccess += 1
        elif notes == "still_inaccessible":
            src["enabled"] = False
            append_comment(src, "[AI_V4:still_inaccessible]")
            still_disabled_after_reaccess += 1
        elif notes == "recovered_low_content" and ed is True:
            # 兜底: 已恢复但method未填, 用enabled_decision=True决定
            src["enabled"] = True
            append_comment(src, "[AI_V4:recovered_low_content]")
            disabled_recovered += 1
        else:
            # 其他情况保持原enabled状态, 仅追加备注
            append_comment(src, f"[AI_V4:reaccess_skip|notes={notes}]")
    print(f"[INFO] disabled reaccess: recovered={disabled_recovered} still_disabled={still_disabled_after_reaccess}")

    # Step6: 输出V4最终JSON
    print("[INFO] writing V4 final JSON...")
    v4 = {
        "version": "optimized_v2_lite_final_v4",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_sources": total,
        "merge_sources": v3.get("merge_sources", []),
        "merge_stats": v3.get("merge_stats", {}),
        "removed_count": v3.get("removed_count", 0),
        "removed_breakdown": v3.get("removed_breakdown", {}),
        "sources": v4_sources,
    }
    with open(V4_PATH, "w", encoding="utf-8") as f:
        json.dump(v4, f, ensure_ascii=False, indent=2)
    print(f"[INFO] V4 written: {V4_PATH}")

    # 统计报告
    en_count = sum(1 for s in v4_sources if s.get("enabled"))
    dis_count = total - en_count
    type_cnt = Counter([s.get("type") for s in v4_sources])

    def fill_rate(key):
        filled = sum(1 for s in v4_sources if not is_blank(s.get(key)))
        return f"{round(filled * 100 / total, 1)}%"

    report = {
        "total": total,
        "video_fix_applied": video_applied,
        "image_fix_applied": image_applied,
        "web_fix_applied": web_applied,
        "disabled_recovered": disabled_recovered,
        "still_disabled": still_disabled_after_reaccess,
        "enabled_count": en_count,
        "disabled_count": dis_count,
        "type_stats": {f"type{k}": v for k, v in sorted(type_cnt.items())},
        "field_fill_rate": {
            "sortUrl": fill_rate("sortUrl"),
            "searchUrl": fill_rate("searchUrl"),
            "ruleArticles": fill_rate("ruleArticles"),
            "ruleNextPage": fill_rate("ruleNextPage"),
            "ruleContent": fill_rate("ruleContent"),
        },
        "v3_comparison": {
            "v3_enabled": v3_enabled_count,
            "v3_disabled": v3_disabled_count,
            "v4_enabled": en_count,
            "v4_disabled": dis_count,
            "enabled_delta": en_count - v3_enabled_count,
        },
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[INFO] report written: {REPORT_PATH}")

    # 控制台摘要(脱敏: 仅输出技术统计数字, 不输出源名称/URL)
    print("=" * 60)
    print("[V4 MERGE SUMMARY]")
    print(f"  total_sources: {total}")
    print(f"  video_fix_applied: {video_applied}")
    print(f"  image_fix_applied: {image_applied}")
    print(f"  web_fix_applied: {web_applied}")
    print(f"  disabled_recovered: {disabled_recovered}")
    print(f"  still_disabled_after_reaccess: {still_disabled_after_reaccess}")
    print(f"  enabled_count: {en_count} (V3={v3_enabled_count}, delta=+{en_count - v3_enabled_count})")
    print(f"  disabled_count: {dis_count} (V3={v3_disabled_count}, delta={dis_count - v3_disabled_count})")
    print(f"  type_stats: {dict(report['type_stats'])}")
    print(f"  field_fill_rate: {report['field_fill_rate']}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 异常消息脱敏: 只输出异常类型, 不输出可能含URL/路径的原始消息
        print(f"[FATAL] {type(e).__name__}: <sanitized>")
        sys.exit(1)
