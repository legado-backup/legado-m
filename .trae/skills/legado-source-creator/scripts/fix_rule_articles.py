#!/usr/bin/env python3
# 简化说明: 批量修复 new_rss_01~50.json 的 ruleArticles 字段格式 | 已知上限: 仅处理 ruleArticles 为 JSON 对象的情况 | 升级路径: 无
import json
import os
import shutil
import sys

RSS_DIR = r"f:\myself\github\WeAgentChat\temp\legado\output\test-sources\rss"
BACKUP_DIR = os.path.join(RSS_DIR, "_backup_ruleArticles")


def fix_one(path):
    """修复单个文件，返回 (修改详情, 错误信息)。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)

    rule_search = data.get("ruleSearch", {})
    article_list = rule_search.get("articleList", "")
    search_content = rule_search.get("content", "")

    rule_articles = data.get("ruleArticles")
    # 仅当 ruleArticles 是 dict 时才需要修复
    if not isinstance(rule_articles, dict):
        return None, "ruleArticles 不是 JSON 对象，跳过"

    # 取原 ruleArticles.content，没有则回退到 ruleSearch.content
    articles_content = rule_articles.get("content") or search_content

    # 应用修复
    data["ruleArticles"] = article_list
    data["ruleContent"] = articles_content

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # 保持末尾换行

    return {
        "articleList": article_list,
        "ruleContent": articles_content,
    }, None


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    fixed = []
    skipped = []
    failed = []

    for i in range(1, 51):
        name = f"new_rss_{i:02d}.json"
        path = os.path.join(RSS_DIR, name)
        if not os.path.exists(path):
            failed.append((name, "文件不存在"))
            continue

        # 备份
        shutil.copy2(path, os.path.join(BACKUP_DIR, name))

        detail, err = fix_one(path)
        if err:
            skipped.append((name, err))
        else:
            fixed.append((name, detail))

    print("=" * 60)
    print(f"修复完成: {len(fixed)} 个文件")
    print(f"跳过: {len(skipped)} 个文件")
    print(f"失败: {len(failed)} 个文件")
    print("=" * 60)

    if skipped:
        print("\n--- 跳过的文件 ---")
        for name, err in skipped:
            print(f"  {name}: {err}")

    if failed:
        print("\n--- 失败的文件 ---")
        for name, err in failed:
            print(f"  {name}: {err}")

    # 验证
    print("\n--- 验证修复结果 ---")
    bad = 0
    for name, _ in fixed:
        path = os.path.join(RSS_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ra = data.get("ruleArticles")
        rc = data.get("ruleContent")
        if not isinstance(ra, str):
            print(f"  [ERROR] {name}: ruleArticles 不是字符串 -> {type(ra).__name__}")
            bad += 1
        elif not ra:
            print(f"  [WARN] {name}: ruleArticles 为空字符串")
        if not isinstance(rc, str) or not rc:
            print(f"  [ERROR] {name}: ruleContent 缺失或非字符串")
            bad += 1
    if bad == 0:
        print(f"  全部 {len(fixed)} 个文件验证通过: ruleArticles 为字符串, ruleContent 存在")
    else:
        print(f"  {bad} 项验证失败")

    return 0 if bad == 0 and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
