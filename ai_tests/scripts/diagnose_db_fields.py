#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断DB中订阅源sortUrl/searchUrl/ruleNextPage字段填充情况"""
import sqlite3
import json
from pathlib import Path
from collections import Counter

DB = Path(__file__).parent.parent.parent / "output" / "rss" / "legado_v4.db"
OUT = Path(__file__).parent.parent.parent / "output" / "rss" / "db_field_diagnose_v4.json"

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("SELECT sourceUrl, sortUrl, searchUrl, ruleNextPage, ruleArticles, type, enabled FROM rssSources")
rows = c.fetchall()
conn.close()

total = len(rows)
print(f"Total: {total}")
# 字段填充率统计
sort_url_filled = sum(1 for r in rows if r[1] and r[1].strip())
search_url_filled = sum(1 for r in rows if r[2] and r[2].strip())
rule_next_page_filled = sum(1 for r in rows if r[3] and r[3].strip())
rule_articles_filled = sum(1 for r in rows if r[4] and r[4].strip())

print(f"sortUrl filled: {sort_url_filled}/{total} ({sort_url_filled*100//total}%)")
print(f"searchUrl filled: {search_url_filled}/{total} ({search_url_filled*100//total}%)")
print(f"ruleNextPage filled: {rule_next_page_filled}/{total} ({rule_next_page_filled*100//total}%)")
print(f"ruleArticles filled: {rule_articles_filled}/{total} ({rule_articles_filled*100//total}%)")

# 按type分组统计
by_type = {}
for r in rows:
    t = r[5] or 0
    by_type.setdefault(t, {"total": 0, "sort_url": 0, "search_url": 0, "rule_next_page": 0, "rule_articles": 0})
    by_type[t]["total"] += 1
    if r[1] and r[1].strip():
        by_type[t]["sort_url"] += 1
    if r[2] and r[2].strip():
        by_type[t]["search_url"] += 1
    if r[3] and r[3].strip():
        by_type[t]["rule_next_page"] += 1
    if r[4] and r[4].strip():
        by_type[t]["rule_articles"] += 1

print("\nBy type:")
for t in sorted(by_type.keys()):
    s = by_type[t]
    print(f"  type={t}: total={s['total']}, sortUrl={s['sort_url']}, searchUrl={s['search_url']}, ruleNextPage={s['rule_next_page']}, ruleArticles={s['rule_articles']}")

# 看几个非空样本的字段内容（脱敏后只看前100字符的模板结构）
import re
def mask(s):
    if not s:
        return "[EMPTY]"
    s = re.sub(r"https?://[^/\"' ]+", "[URL]", s)
    s = re.sub(r"\{\{.*?\}\}", "{tpl}", s)
    return s[:200]

print("\n=== 非空样本（前5个） ===")
non_empty = [r for r in rows if r[1] and r[1].strip()][:5]
for i, r in enumerate(non_empty):
    print(f"\n[样本{i+1}] type={r[5]} enabled={r[6]}")
    print(f"  sortUrl: {mask(r[1])}")
    print(f"  searchUrl: {mask(r[2])}")
    print(f"  ruleNextPage: {mask(r[3])}")
    print(f"  ruleArticles: {mask(r[4])}")

# 空sortUrl的源数量按type
print("\n=== sortUrl为空的源按type统计 ===")
empty_sort = [r for r in rows if not r[1] or not r[1].strip()]
empty_by_type = Counter(r[5] or 0 for r in empty_sort)
print(f"  empty total: {len(empty_sort)}")
for t, n in sorted(empty_by_type.items()):
    print(f"  type={t}: {n}")

report = {
    "total": total,
    "filled": {
        "sortUrl": sort_url_filled,
        "searchUrl": search_url_filled,
        "ruleNextPage": rule_next_page_filled,
        "ruleArticles": rule_articles_filled,
    },
    "by_type": {str(k): v for k, v in by_type.items()},
    "empty_sort_by_type": dict(empty_by_type),
}
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n[OUTPUT] {OUT}")
