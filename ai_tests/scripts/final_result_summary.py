"""最终结果分析"""
import json, collections
ROOT = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\image_source_deep_fix_v2.json'
with open(ROOT, 'r', encoding='utf-8') as f:
    d = json.load(f)

print(f'===== 最终结果汇总 =====')
print(f'total = {d["total"]}')
print(f'records = {len(d["records"])}')
print(f'fixed (元数据) = {d.get("fixed",0)}')
print(f'partial_fixed (元数据) = {d.get("partial_fixed",0)}')
print(f'still_failed (元数据) = {d.get("still_failed",0)}')

# 重新统计
fully = 0
partial = 0
failed = 0
for r in d['records']:
    s = bool(r.get('sort_url_filled'))
    se = bool(r.get('search_url_filled'))
    ra = bool(r.get('rule_articles_filled'))
    ri = bool(r.get('rule_image_filled'))
    rc = bool(r.get('rule_content_filled'))
    v = bool(r.get('verify_ok'))
    if (s and v):
        fully += 1
    elif s or se or ra:
        partial += 1
    else:
        failed += 1

print(f'\n===== 重新统计 =====')
print(f'完全修复 (sortUrl+verify): {fully}')
print(f'部分修复 (1-2字段): {partial}')
print(f'仍然失败: {failed}')

print(f'\n===== 字段填充率 =====')
print(f'sortUrl 填充: {sum(1 for r in d["records"] if r.get("sort_url_filled"))}/{len(d["records"])}')
print(f'searchUrl 填充: {sum(1 for r in d["records"] if r.get("search_url_filled"))}/{len(d["records"])}')
print(f'ruleArticles 填充: {sum(1 for r in d["records"] if r.get("rule_articles_filled"))}/{len(d["records"])}')
print(f'ruleImage 填充: {sum(1 for r in d["records"] if r.get("rule_image_filled"))}/{len(d["records"])}')
print(f'ruleNextPage 填充: {sum(1 for r in d["records"] if r.get("rule_next_page_filled"))}/{len(d["records"])}')
print(f'ruleContent 填充: {sum(1 for r in d["records"] if r.get("rule_content_filled"))}/{len(d["records"])}')
print(f'verify_ok: {sum(1 for r in d["records"] if r.get("verify_ok"))}/{len(d["records"])}')

print(f'\n===== 模板分布 =====')
c = collections.Counter(r.get('template_type','unknown') for r in d['records'])
for t, n in c.most_common():
    print(f'  {t}: {n}')

print(f'\n===== 仍然无 sortUrl 的源 =====')
for r in d['records']:
    if not r.get('sort_url_filled'):
        print(f'  idx={r["idx"]} tmpl={r.get("template_type","")} searchUrl={bool(r.get("search_url_filled"))} ruleArticles={bool(r.get("rule_articles_filled"))}')

print(f'\n===== 仍然无 searchUrl 的源 =====')
for r in d['records']:
    if not r.get('search_url_filled'):
        print(f'  idx={r["idx"]} error={r.get("error","")}')

print(f'\n===== 验证未通过的源 =====')
for r in d['records']:
    if r.get('sort_url_filled') and not r.get('verify_ok'):
        print(f'  idx={r["idx"]} sortUrl_lines={len(r.get("sort_url_filled","").split(chr(10)))} notes={r.get("notes",[])[-3:]}')

# 输出文件大小
import os
print(f'\n输出文件大小: {os.path.getsize(ROOT)} bytes')
