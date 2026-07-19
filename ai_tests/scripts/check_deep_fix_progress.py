"""检查中间结果"""
import json, collections
ROOT = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\image_source_deep_fix_v2.json'
with open(ROOT, 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'total={d["total"]}')
print(f'records={len(d["records"])}')
print(f'fixed={d.get("fixed",0)}')
print(f'partial_fixed={d.get("partial_fixed",0)}')
print(f'still_failed={d.get("still_failed",0)}')
print(f'done_idx={[r.get("idx") for r in d["records"]]}')
print(f'verify_ok_count={sum(1 for r in d["records"] if r.get("verify_ok"))}')
print(f'have_sortUrl={sum(1 for r in d["records"] if r.get("sort_url_filled"))}')
print(f'have_searchUrl={sum(1 for r in d["records"] if r.get("search_url_filled"))}')
print(f'have_ruleArticles={sum(1 for r in d["records"] if r.get("rule_articles_filled"))}')
c = collections.Counter(r.get('template_type','unknown') for r in d['records'])
print(f'template_dist={dict(c)}')
# 错误统计
errs = collections.Counter(r.get('error','').split(':')[0] for r in d['records'] if r.get('error'))
print(f'error_dist={dict(errs)}')
