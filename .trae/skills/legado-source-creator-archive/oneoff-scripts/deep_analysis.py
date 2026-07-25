import json
from collections import Counter, defaultdict

with open('reports/full-fix-20260628.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

book = data['results']['book']

# 成功/部分成功源的搜索质量
true_success = 0
false_success = 0

for r in book:
    s = r.get('stages', {})
    search_count = r.get('search_count', 0)
    
    if r['status'] in ('success', 'partial'):
        if s.get('search'):
            if search_count > 0:
                true_success += 1
            else:
                false_success += 1

print('=== 成功/部分成功源搜索质量 ===')
total = true_success + false_success
print(f'有搜索结果(count>0): {true_success} ({true_success/total*100:.1f}%)')
print(f'假成功(count=0): {false_success} ({false_success/total*100:.1f}%)')

# CF盾特征
cf_kw = ['just a moment', 'checking your browser', 'cf-challenge', 'challenge-platform', 'cf_chl_opt']
cf_like = []
for r in book:
    logs_text = ' '.join(r.get('logs_summary', [])).lower()
    for kw in cf_kw:
        if kw in logs_text:
            cf_like.append((r.get('source_name', '?'), r.get('source_url', '')[:60], kw, r['status']))
            break

print(f'\n=== CF盾特征源: {len(cf_like)} ===')
for name, url, kw, status in cf_like[:15]:
    print(f'  [{status}] {name} | {kw}')

# 失败源中CF
cf_in_fail = sum(1 for name, url, kw, st in cf_like if st == 'failed')
cf_in_success = sum(1 for name, url, kw, st in cf_like if st in ('success', 'partial'))
print(f'\nCF在失败源中: {cf_in_fail}')
print(f'CF在成功源中: {cf_in_success}')

# 按状态统计
status_count = Counter(r['status'] for r in book)
print(f'\n=== 整体状态分布 ===')
for st, c in status_count.most_common():
    print(f'  {st}: {c}')

# 超时统计
timeout_count = sum(1 for r in book if 'TIMEOUT' in str(r.get('errors', [])) or 'WS_TIMEOUT' in str(r.get('errors', [])))
dns_count = sum(1 for r in book if 'DNS' in str(r.get('errors', [])))
ssl_count = sum(1 for r in book if 'SSL' in str(r.get('errors', [])))
print(f'\n超时: {timeout_count}, DNS死站: {dns_count}, SSL错误: {ssl_count}')

# 真正可用的源 = search_count > 0 的成功/部分成功源
real_usable = sum(1 for r in book if r['status'] in ('success', 'partial') and r.get('search_count', 0) > 0)
print(f'\n真正可用源(搜索有结果): {real_usable}')
print(f'占书源总数比例: {real_usable/len(book)*100:.1f}%')
