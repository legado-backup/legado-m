"""
V5.7 阶段1.3：应用补丁，把建议字段值写入JSON，生成 optimized_v5_7_final.json
策略：
- 对有建议值的字段，直接用建议值
- 对没提取到的字段，用通用默认值（用户要求11必备字段全部填充）
- 在sourceComment中标注字段来源：[AI_V5_7:field_fixed|method=extracted|src=playwright]
  或 [AI_V5_7:field_fixed|method=default_template|note=需手动验证]
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

SRC_JSON = Path("output/rss/optimized_v5_6_final.json")
SUGGEST_JSON = Path("output/rss/v5_7_field_suggestions_v2.json")
DST_JSON = Path("output/rss/optimized_v5_7_final.json")
BACKUP_JSON = Path("output/rss/optimized_v5_6_final.json.bak_v5_7")

# 通用默认值（按字段类型）
DEFAULT_VALUES = {
    "rulePubDate": "class.time@text||class.date@text||time@text||class.pubtime@text",
    "ruleTitle": "class.title@text||class.tit@text||h2@text||h3@text||a@text",
    "ruleNextPage": "a.next@href||a:contains(下一页)@href||a:contains(next)@href",
    "ruleImage": "img@src||img@data-original||img@data-src",
    "ruleLink": "a@href",
}


def is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def main():
    # 备份原JSON
    shutil.copy(SRC_JSON, BACKUP_JSON)
    print(f"=== 原JSON已备份到 {BACKUP_JSON} ===")

    # 读取数据
    with open(SRC_JSON, "r", encoding="utf-8") as f:
        sources = json.load(f)

    with open(SUGGEST_JSON, "r", encoding="utf-8") as f:
        suggestions_all = json.load(f)

    # 应用补丁
    fixed_count = 0
    default_count = 0
    detail_log = []

    for src_key, info in suggestions_all.items():
        idx = int(src_key.split("_")[1])
        if idx >= len(sources):
            continue
        s = sources[idx]
        missing = info.get("missing", [])
        suggestions = info.get("suggestions", {})

        if not missing:
            continue

        # 构建补丁注释
        patches = []
        for field in missing:
            if field in suggestions:
                # 用提取到的建议值
                s[field] = suggestions[field]
                patches.append(f"{field}=extracted")
                fixed_count += 1
            elif field in DEFAULT_VALUES:
                # 用通用默认值
                s[field] = DEFAULT_VALUES[field]
                patches.append(f"{field}=default_template")
                default_count += 1
            else:
                # 没有默认值的字段（如sourceIcon），用站点/favicon.ico
                if field == "sourceIcon":
                    source_url = s.get("sourceUrl", "")
                    if source_url:
                        from urllib.parse import urlparse
                        p = urlparse(source_url)
                        s[field] = f"{p.scheme}://{p.netloc}/favicon.ico"
                        patches.append(f"{field}=default_favicon")
                        default_count += 1

        # 更新 sourceComment
        comment = s.get("sourceComment", "") or ""
        patch_str = "|".join(patches)
        v5_7_tag = f"[AI_V5_7:field_fixed|{patch_str}|ts={datetime.now().strftime('%Y%m%d')}]"
        # 避免重复添加
        if "[AI_V5_7:" not in comment:
            if comment and not comment.endswith("\n"):
                comment += "\n"
            comment += v5_7_tag
            s["sourceComment"] = comment

        detail_log.append({
            "idx": idx,
            "missing": missing,
            "applied": patches,
        })

    # 单独处理源[81]（建议文件中没有）
    idx = 81
    s = sources[idx]
    missing_81 = []
    for field in ["sourceIcon", "ruleNextPage", "ruleTitle", "rulePubDate", "ruleImage", "ruleLink"]:
        if not is_filled(s.get(field)):
            missing_81.append(field)

    if missing_81:
        patches_81 = []
        for field in missing_81:
            if field in DEFAULT_VALUES:
                s[field] = DEFAULT_VALUES[field]
                patches_81.append(f"{field}=default_template")
                default_count += 1
            elif field == "sourceIcon":
                source_url = s.get("sourceUrl", "")
                if source_url:
                    from urllib.parse import urlparse
                    p = urlparse(source_url)
                    s[field] = f"{p.scheme}://{p.netloc}/favicon.ico"
                    patches_81.append(f"{field}=default_favicon")
                    default_count += 1
        comment = s.get("sourceComment", "") or ""
        v5_7_tag = f"[AI_V5_7:field_fixed|{'|'.join(patches_81)}|ts={datetime.now().strftime('%Y%m%d')}|note=no_suggestion_use_default]"
        if "[AI_V5_7:" not in comment:
            if comment and not comment.endswith("\n"):
                comment += "\n"
            comment += v5_7_tag
            s["sourceComment"] = comment
        detail_log.append({"idx": 81, "missing": missing_81, "applied": patches_81})

    # 保存
    with open(DST_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    # 输出统计
    print(f"\n=== V5.7 字段补丁应用完成 ===")
    print(f"提取值填充字段数: {fixed_count}")
    print(f"通用默认值填充字段数: {default_count}")
    print(f"总补丁数: {fixed_count + default_count}")
    print(f"输出文件: {DST_JSON}")
    print(f"\n=== 详细补丁日志 ===")
    for entry in detail_log:
        print(f"  源[{entry['idx']}] 缺{len(entry['missing'])}字段 -> 补{len(entry['applied'])}字段: {','.join(entry['applied'])}")

    # 验证补丁后的字段填充率
    print(f"\n=== 补丁后字段填充率（13个源）===")
    MISSING_IDX = [52, 81, 83, 131, 134, 174, 176, 177, 178, 180, 181, 182, 183]
    REQUIRED_FIELDS = ["sourceName", "sourceUrl", "sourceIcon", "searchUrl", "sortUrl",
                       "ruleArticles", "ruleNextPage", "ruleTitle", "rulePubDate",
                       "ruleImage", "ruleLink", "ruleContent"]
    for field in REQUIRED_FIELDS:
        filled = sum(1 for i in MISSING_IDX if is_filled(sources[i].get(field)))
        print(f"  {field:<15}: {filled}/{len(MISSING_IDX)}")


if __name__ == "__main__":
    main()
