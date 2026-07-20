#!/usr/bin/env python3
r"""v5_6_extract_targets.py — 从 optimized_v5_5_final.json 提取3个失败源配置

安全规范：禁止输出源名称/URL/cookie内容，全部用代号(源[idx]/站点[A/B/C])。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SRC = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_5_final.json')
OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_targets')
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(SRC, 'r', encoding='utf-8') as f:
    sources = json.load(f)

print(f"[INFO] total sources: {len(sources)}")
print(f"[INFO] enabled count: {sum(1 for s in sources if s.get('enabled'))}")

# 目标源 idx（基于 V5.5 验证结果选择3个不同失败类型）
TARGETS = [
    {'idx': 1, 'fail_type': 'list_empty', 'alias': 'A',
     'reason': 'domain pass / list-search-category 全失败 / content unknown'},
    {'idx': 2, 'fail_type': 'content_parse_failed', 'alias': 'B',
     'reason': 'list-search-category 全 pass / content fail'},
    {'idx': 3, 'fail_type': 'search_malformed_url', 'alias': 'C',
     'reason': 'list-category pass / search malformed_url / content fail'},
]

summary_lines = []
for t in TARGETS:
    idx = t['idx']
    if idx >= len(sources):
        print(f"[WARN] idx={idx} out of range")
        continue
    src = sources[idx]
    # 提取关键字段（脱敏：不打印源名称/URL，只打印长度和类型）
    fields_keys = ['sourceUrl', 'sourceName', 'enabled', 'type', 'lastHost',
                   'ruleArticles', 'ruleTitle', 'ruleLink', 'ruleImage', 'rulePubDate',
                   'ruleNextPage', 'ruleContent', 'searchUrl', 'sortUrl',
                   'loginUrl', 'loginUi', 'header', 'enabledCookieJar',
                   'articleStyle', 'singleUrl', 'enableJs', 'loadWithBaseUrl',
                   'sourceGroup', 'sourceComment']
    extracted = {k: src.get(k) for k in fields_keys}
    # 保存到独立文件（保留原值用于分析，仅本地，不输出到对话）
    out_file = OUT_DIR / f'src_{idx}_{t["fail_type"]}.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)
    # 输出脱敏摘要
    url_len = len(extracted.get('sourceUrl') or '')
    name_len = len(extracted.get('sourceName') or '')
    sort_url_present = bool(extracted.get('sortUrl'))
    search_url_present = bool(extracted.get('searchUrl'))
    rule_articles_present = bool(extracted.get('ruleArticles'))
    rule_content_len = len(extracted.get('ruleContent') or '')
    rule_image_present = bool(extracted.get('ruleImage'))
    rule_pubdate_present = bool(extracted.get('rulePubDate'))
    login_url_present = bool(extracted.get('loginUrl'))
    header_present = bool(extracted.get('header'))
    src_type = extracted.get('type')
    enabled = extracted.get('enabled')
    line = (f"[TARGET] idx={idx} alias=源[{t['alias']}] type={src_type} enabled={enabled} "
            f"url_len={url_len} name_len={name_len} "
            f"sortUrl={sort_url_present} searchUrl={search_url_present} "
            f"ruleArticles={rule_articles_present} ruleContent_len={rule_content_len} "
            f"ruleImage={rule_image_present} rulePubDate={rule_pubdate_present} "
            f"loginUrl={login_url_present} header={header_present} "
            f"fail_type={t['fail_type']}")
    print(line)
    summary_lines.append(line)
    print(f"  -> saved: {out_file}")

# 保存摘要
summary_file = OUT_DIR / 'extract_summary.txt'
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(summary_lines))
print(f"[DONE] summary saved: {summary_file}")
