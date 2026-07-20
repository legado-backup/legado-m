# -*- coding: utf-8 -*-
"""输出 V5.2 中字段完整的源 idx 清单(技术信息)"""
import json
ROOT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss"
def load(name):
    with open(f"{ROOT}\\{name}", "r", encoding="utf-8") as f:
        return json.load(f)
v52 = load("optimized_v5_2_stable.json")
print(f"V5.2 总源数: {len(v52)}")

# 加载 V5 修复记录
def load_v5_patterns(name):
    d = load(name)
    if isinstance(d, dict):
        for k in ["sources", "data", "list", "items"]:
            if k in d and isinstance(d[k], list):
                d = d[k]
                break
        else:
            for v in d.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    d = v
                    break
    pats = []
    for item in d:
        pat = item.get("sourceUrl_pattern", "")
        if isinstance(pat, str) and pat:
            pats.append(pat)
    return pats

video_pats = set(load_v5_patterns("v5_video_deepfix.json"))
missing_pats = set(load_v5_patterns("v5_missing_fields_fix.json"))
hard_pats = set(load_v5_patterns("v5_hard_source_fix.json"))
all_v5 = video_pats | missing_pats | hard_pats
print(f"video={len(video_pats)}, missing={len(missing_pats)}, hard={len(hard_pats)}, total={len(all_v5)}")

# 按类别+字段完整性统计
cat_field_full = {"video": [], "missing": [], "hard": [], "v4_unchanged": []}
for i, s in enumerate(v52):
    url = s.get("sourceUrl", "")
    ra = (s.get("ruleArticles") or "").strip()
    rl = (s.get("ruleLink") or "").strip()
    rt = (s.get("ruleTitle") or "").strip()
    field_full = bool(ra) and bool(rl) and bool(rt)
    if not field_full:
        continue
    # 分类
    if url in video_pats:
        cat_field_full["video"].append(i)
    elif url in missing_pats:
        cat_field_full["missing"].append(i)
    elif url in hard_pats:
        cat_field_full["hard"].append(i)
    else:
        cat_field_full["v4_unchanged"].append(i)

for cat, lst in cat_field_full.items():
    print(f"  {cat}: field_full count={len(lst)}, idx(前10)={lst[:10]}")

# 看下匹配情况
total_v5_in_v52 = sum(len(v) for k, v in cat_field_full.items() if k != "v4_unchanged")
print(f"\nV5.2 中匹配到 V5 修复记录的源数: {total_v5_in_v52} (期望: video9+missing104+hard38=151)")
