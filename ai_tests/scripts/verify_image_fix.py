"""验证图片源字段修复结果"""
import json
import re
from collections import Counter

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[^\s]*)", re.IGNORECASE)


def sanitize(msg):
    if not isinstance(msg, str):
        msg = str(msg)
    msg = URL_RE.sub("[URL]", msg)
    msg = DOMAIN_RE.sub("[DOMAIN]", msg)
    return msg


p = 'output/rss/image_source_field_fix.json'
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)

print('===== 修复结果统计 =====')
print(f"total: {d.get('total')}")
print(f"fixed: {d.get('fixed')}")
print(f"still_failed: {d.get('still_failed')}")
print(f"records count: {len(d.get('records', []))}")
print()

records = d['records']
sort_filled = sum(1 for r in records if r.get('sort_url_filled'))
search_filled = sum(1 for r in records if r.get('search_url_filled'))
articles_filled = sum(1 for r in records if r.get('rule_articles_filled'))
image_filled = sum(1 for r in records if r.get('rule_image_filled'))
nextpage_filled = sum(1 for r in records if r.get('rule_next_page_filled'))
accessible = sum(1 for r in records if r.get('source_url_accessible'))

print('===== 字段填充统计 =====')
print(f"source_url_accessible: {accessible}/{len(records)}")
print(f"sort_url_filled:       {sort_filled}/{len(records)}")
print(f"search_url_filled:     {search_filled}/{len(records)}")
print(f"rule_articles_filled:  {articles_filled}/{len(records)}")
print(f"rule_image_filled:     {image_filled}/{len(records)}")
print(f"rule_next_page_filled: {nextpage_filled}/{len(records)}")
print()

# 修复分级
fully = 0
partial = 0
failed = 0
fully_idx = []
partial_idx = []
failed_idx = []
for r in records:
    s = bool(r.get('sort_url_filled'))
    se = bool(r.get('search_url_filled'))
    ra = bool(r.get('rule_articles_filled'))
    idx = r.get('idx')
    if s and se and ra:
        fully += 1
        fully_idx.append(idx)
    elif s or se or ra:
        partial += 1
        partial_idx.append(idx)
    else:
        failed += 1
        failed_idx.append(idx)

print('===== 修复分级 =====')
print(f"完全修复(3字段都填): {fully}")
print(f"  idx: {fully_idx}")
print(f"部分修复(1-2字段填): {partial}")
print(f"  idx: {partial_idx}")
print(f"仍然失败(0字段填):   {failed}")
print()

# error 分布(脱敏)
err_dist = Counter()
for r in records:
    e = r.get('error', '') or ''
    if e:
        key = sanitize(e)[:60]
        err_dist[key] += 1
print('===== 错误分布(top 15) =====')
for k, v in err_dist.most_common(15):
    print(f"  {v}x : {k}")
print()

# 验证 list_count > 0 的源
verify_ok_count = 0
for r in records:
    notes = r.get('notes', [])
    for n in notes:
        if isinstance(n, str) and 'verify_ok=True' in n:
            verify_ok_count += 1
            break
print(f"sortUrl拼接访问验证通过(列表项>0): {verify_ok_count}")
print()

# 输出完全修复的样例(脱敏)
print('===== 完全修复样例(脱敏) =====')
for r in records:
    if r.get('sort_url_filled') and r.get('search_url_filled') and r.get('rule_articles_filled'):
        print(f"idx={r.get('idx')}:")
        print(f"  accessible: {r.get('source_url_accessible')}")
        print(f"  sort_url_filled (first 80 chars): {sanitize(r.get('sort_url_filled',''))[:80]}")
        print(f"  search_url_filled: {sanitize(r.get('search_url_filled',''))[:80]}")
        print(f"  rule_articles_filled: {sanitize(r.get('rule_articles_filled',''))[:80]}")
        print(f"  rule_image_filled: {sanitize(r.get('rule_image_filled',''))[:80]}")
        print(f"  rule_next_page_filled: {sanitize(r.get('rule_next_page_filled',''))[:80]}")
        print(f"  notes: {r.get('notes',[])}")
        print()
        break
