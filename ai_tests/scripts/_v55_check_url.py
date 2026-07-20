import json
data = json.load(open('output/rss/optimized_v5_4_final.json','r',encoding='utf-8'))
enabled = [s for s in data if s.get('enabled',False)]
# 检查源URL格式特征（不输出完整URL）
for i in [0, 1, 4, 5, 12, 16, 20, 8, 9]:
    s = enabled[i]
    url = s.get('sourceUrl', '')
    print(f'idx={i} len={len(url)} starts_http={str(url.startswith("http"))} has_comma={str("," in url)} starts_atjs={str(url.startswith("@js"))} has_jstag={str("<js>" in url)} prefix8={url[:8]}')
