"""详细分析结果"""
import json
ROOT = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\image_source_deep_fix_v2.json'
with open(ROOT, 'r', encoding='utf-8') as f:
    d = json.load(f)

# 失败的源
print('===== 失败源(完全无字段填充) =====')
for r in d['records']:
    if not r.get('sort_url_filled') and not r.get('search_url_filled') and not r.get('rule_articles_filled'):
        print(f"idx={r['idx']} error={r.get('error','')}")
        print(f"  notes={r.get('notes',[])}")

# 部分修复的源(只有searchUrl/ruleArticles没sortUrl)
print('\n===== 部分修复(无sortUrl但有其他字段) =====')
no_sort = []
for r in d['records']:
    if not r.get('sort_url_filled') and (r.get('search_url_filled') or r.get('rule_articles_filled')):
        no_sort.append(r)
        print(f"idx={r['idx']} tmpl={r.get('template_type','')} searchUrl={bool(r.get('search_url_filled'))} ruleArticles={bool(r.get('rule_articles_filled'))} notes={r.get('notes',[])[:3]}")
print(f'\n部分修复(无sortUrl)总数: {len(no_sort)}')

# 完全修复的源
print('\n===== 完全修复(有sortUrl且验证通过) =====')
ok = []
for r in d['records']:
    if r.get('sort_url_filled') and r.get('verify_ok'):
        ok.append(r)
        print(f"idx={r['idx']} tmpl={r.get('template_type','')} list_count={r.get('list_items_count',0)} sortUrl_lines={len(r.get('sort_url_filled','').split(chr(10)))}")
print(f'\n完全修复总数: {len(ok)}')

# 验证未通过但生成了sortUrl的源
print('\n===== 有sortUrl但验证未通过 =====')
sort_no_verify = []
for r in d['records']:
    if r.get('sort_url_filled') and not r.get('verify_ok'):
        sort_no_verify.append(r)
        print(f"idx={r['idx']} tmpl={r.get('template_type','')} notes={r.get('notes',[])[:3]}")
print(f'\n有sortUrl但验证未通过: {len(sort_no_verify)}')
