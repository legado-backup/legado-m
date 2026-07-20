# -*- coding: utf-8 -*-
"""快速查看 V5 阶段输出文件的 sourceUrl_pattern 字段结构"""
import json
ROOT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss"
def load(name):
    with open(f"{ROOT}\\{name}", "r", encoding="utf-8") as f:
        return json.load(f)
def extract_list(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for k in ["sources", "data", "list", "items"]:
            if k in d and isinstance(d[k], list):
                return d[k]
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []
for fn in ["v5_video_deepfix.json", "v5_missing_fields_fix.json", "v5_hard_source_fix.json", "v5_cf_breakthrough.json"]:
    d = load(fn)
    lst = extract_list(d)
    print(f"\n{fn}: count={len(lst)}")
    if lst:
        # 输出前3个的 key 字段
        first = lst[0]
        # 列出关键字段名(不含业务数据)
        safe_keys = [k for k in first.keys() if k in ["source_index", "sourceUrl_pattern", "result_type", "success", "confidence", "difficulty_type", "missing_fields", "fields_updated", "strategy_applied"]]
        print(f"  safe keys: {safe_keys}")
        # 仅输出 sourceUrl_pattern 长度(不输出实际值)
        for s in lst[:3]:
            pat = s.get("sourceUrl_pattern", "")
            if isinstance(pat, str):
                print(f"  - sourceUrl_pattern len={len(pat)}, prefix={pat[:8]}...")
            else:
                print(f"  - sourceUrl_pattern type={type(pat).__name__}")
