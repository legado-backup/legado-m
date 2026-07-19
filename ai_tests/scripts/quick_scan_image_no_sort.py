"""快速扫描 V3 中 type=1 且 sortUrl 为空的源"""
import json
import sys
from pathlib import Path

ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT = ROOT / "output" / "rss" / "optimized_v2_lite_final_v3.json"

with open(INPUT, 'r', encoding='utf-8') as f:
    d = json.load(f)

if isinstance(d, dict):
    sources = d.get('sources', d)
else:
    sources = d

print(f'total_sources={len(sources)}', flush=True)

img_no_sort = []
for i, x in enumerate(sources):
    if not isinstance(x, dict):
        continue
    t = x.get('type', 0)
    try:
        t = int(t)
    except (ValueError, TypeError):
        t = 0
    if t != 1:
        continue
    su = x.get('sortUrl', '') or ''
    if su.strip():
        continue
    img_no_sort.append((i, x))

print(f'image_type1_no_sortUrl={len(img_no_sort)}', flush=True)
print(f'idx_list={[x[0] for x in img_no_sort]}', flush=True)

# 统计 sourceUrl 可达性(只看是否有URL)
no_url = sum(1 for _, x in img_no_sort if not (x.get('sourceUrl','') or '').strip())
print(f'no_sourceUrl_count={no_url}', flush=True)

# 统计是否有自定义字段
has_js = sum(1 for _, x in img_no_sort if (x.get('jsLib') or '').strip())
print(f'has_jsLib={has_js}', flush=True)

# 输出前5个的来源域名(脱敏)
import re
URL_RE = re.compile(r"https?://([^/\s\"'<>]+)")
for i, (idx, x) in enumerate(img_no_sort[:5]):
    su = x.get('sourceUrl','') or ''
    m = URL_RE.match(su)
    host = m.group(1) if m else ''
    # 只输出host首字母
    host_mask = (host[0] + '***' + host[-3:]) if len(host) > 5 else '***'
    print(f'sample[{i}] idx={idx} host={host_mask}', flush=True)
