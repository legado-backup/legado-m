#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 v2_type_classification_report.json 重建 classified_v2.json
（阶段3已跑完，只是保存逻辑有bug，用report重建）
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_PREPROCESSED = PROJECT_ROOT / "output" / "rss" / "preprocessed_v2.json"
REPORT_FILE = PROJECT_ROOT / "output" / "rss" / "v2_type_classification_report.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"

def main():
    # 读取预处理后的源（含sourceUrl等完整数据）
    with open(INPUT_PREPROCESSED, "r", encoding="utf-8") as f:
        sources = json.load(f)
    
    # 读取报告
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    records_by_idx = {r['idx']: r for r in report.get('records', []) if 'idx' in r}
    
    # 重建
    final_sources = []
    for idx, source in enumerate(sources):
        if idx not in records_by_idx:
            continue
        rec = records_by_idx[idx]
        src = dict(source)
        src['type'] = rec.get('type', 0)
        method = rec.get('method', 'unknown')
        is_nav = rec.get('is_navigation', False)
        conf = rec.get('confidence', 0.0)
        
        if method == 'skipped':
            tag = 'skipped'
            extra = f"[AI_CLASSIFY:{tag}|reason=needs_manual]"
        elif is_nav:
            tag = 'nav'
            extra = f"[AI_CLASSIFY:{tag}|conf={conf}|method={method}]"
        elif method == 'failed':
            tag = 'access_failed'
            extra = f"[AI_CLASSIFY:{tag}|stage7_retry]"
        else:
            tag = f"type{rec.get('type', 0)}"
            extra = f"[AI_CLASSIFY:{tag}|conf={conf}|method={method}]"
        
        orig_comment = src.get('sourceComment', '') or ''
        if 'AI_CLASSIFY:' not in orig_comment:
            src['sourceComment'] = orig_comment + '\n' + extra if orig_comment else extra
        
        final_sources.append(src)
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)
    
    print(f"重建完成: {len(final_sources)} 个源")
    print(f"输出: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
