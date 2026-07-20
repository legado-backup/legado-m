# -*- coding: utf-8 -*-
"""快速看 V5 阶段输出文件结构"""
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
    print(f"{fn}: raw={type(d).__name__}, list_len={len(lst)}")
    if lst:
        print(f"  first item keys: {list(lst[0].keys())[:20]}")
        # 看是否有 success/status 字段
        first = lst[0]
        for k in ["success", "status", "fixed", "result", "_status", "_ok"]:
            if k in first:
                print(f"  has status field: {k}={first[k]}")
