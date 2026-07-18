#!/usr/bin/env python3
"""analyze_input_structure.py — 分析输入JSON的结构（只输出技术指标，不输出业务字段）"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

INPUT_PATH = r'f:\myself\github\WeAgentChat\temp\legado\temp\rss\rssSource_202607131357\rssSource_202607182145..json'

# 必填字段（CRITICAL）
CRITICAL_FIELDS = {'sourceUrl', 'sourceName'}
# 强烈推荐字段（MANDATORY）
MANDATORY_FIELDS = {'sourceIcon', 'sortUrl', 'searchUrl', 'ruleArticles', 'ruleTitle', 'ruleLink'}
# 推荐字段（RECOMMENDED）
RECOMMENDED_FIELDS = {'ruleNextPage', 'rulePubDate', 'ruleDescription', 'ruleImage', 'ruleContent',
                       'header', 'loginUrl', 'enabledCookieJar', 'concurrentRate',
                       'articleStyle', 'enableJs', 'loadWithBaseUrl', 'type'}


def main():
    print('=' * 60)
    print('输入JSON结构分析（仅技术指标）')
    print('=' * 60)

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    total = len(sources)
    print(f'\n总源数: {total}')

    # 字段覆盖率统计
    print('\n--- 字段覆盖率 ---')
    all_fields = CRITICAL_FIELDS | MANDATORY_FIELDS | RECOMMENDED_FIELDS
    field_coverage = {}
    for field in all_fields:
        count = sum(1 for s in sources if s.get(field) not in (None, '', [], {}))
        field_coverage[field] = count
        pct = count * 100 / total if total > 0 else 0
        category = 'CRITICAL' if field in CRITICAL_FIELDS else \
                   'MANDATORY' if field in MANDATORY_FIELDS else 'RECOMMENDED'
        print(f'  [{category}] {field}: {count}/{total} ({pct:.1f}%)')

    # 缺失字段统计
    print('\n--- 缺失字段统计（top 5）---')
    missing_count = Counter()
    for s in sources:
        for field in all_fields:
            if s.get(field) in (None, '', [], {}):
                missing_count[field] += 1
    for field, cnt in missing_count.most_common(10):
        print(f'  {field}: 缺失{cnt}/{total}')

    # sourceUrl 类型分析（不输出值）
    print('\n--- sourceUrl类型分析 ---')
    url_starts_http = sum(1 for s in sources if str(s.get('sourceUrl', '')).startswith('http'))
    url_is_template = sum(1 for s in sources if '{{' in str(s.get('sourceUrl', '')))
    url_is_short = sum(1 for s in sources if len(str(s.get('sourceUrl', ''))) < 20)
    print(f'  http开头: {url_starts_http}/{total}')
    print(f'  含模板{{}}: {url_is_template}/{total}')
    print(f'  长度<20: {url_is_short}/{total}')

    # enabled状态统计
    enabled_true = sum(1 for s in sources if s.get('enabled') in (True, 1, '1'))
    print(f'\n--- enabled状态 ---')
    print(f'  enabled=True: {enabled_true}/{total}')

    # type字段统计
    type_count = Counter(s.get('type', 0) for s in sources)
    print(f'\n--- type字段 ---')
    for t, cnt in type_count.most_common():
        print(f'  type={t}: {cnt}个')

    # 字段总数
    if sources:
        first = sources[0]
        print(f'\n--- 字段总数 ---')
        print(f'  第一个源字段数: {len(first)}')

    # 是否已有loginUrl配置
    has_login = sum(1 for s in sources if s.get('loginUrl'))
    print(f'\n--- loginUrl配置 ---')
    print(f'  已配置loginUrl: {has_login}/{total}')

    # 总体评分
    critical_ok = sum(1 for s in sources
                       if all(s.get(f) for f in CRITICAL_FIELDS))
    mandatory_ok = sum(1 for s in sources
                        if all(s.get(f) for f in MANDATORY_FIELDS))
    recommended_ok = sum(1 for s in sources
                          if all(s.get(f) for f in RECOMMENDED_FIELDS))
    print(f'\n--- 总体评分 ---')
    print(f'  CRITICAL完整: {critical_ok}/{total} ({critical_ok*100/total:.1f}%)')
    print(f'  MANDATORY完整: {mandatory_ok}/{total} ({mandatory_ok*100/total:.1f}%)')
    print(f'  RECOMMENDED完整: {recommended_ok}/{total} ({recommended_ok*100/total:.1f}%)')


if __name__ == '__main__':
    main()
