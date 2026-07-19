"""merge_final_v2.py - 订阅源最终合并脚本

任务：合并基础源(222) + 视频源重新识别 + 导航站拆分子源(70) → 最终完整版(292) + 精简版 + 报告

输出安全：报告只输出技术指标，不输出业务字段原文、URL、源名称
"""
import json
import os
import re
import collections
from datetime import datetime

# 输入文件
BASE_FILE = 'output/rss/optimized_v2_full.json'
VIDEO_FILE = 'output/rss/subagent_video_reidentify.json'
NAV_FILE = 'output/rss/subagent_navigation_split.json'

# 输出文件
OUT_FULL = 'output/rss/optimized_v2_full_final.json'
OUT_LITE = 'output/rss/optimized_v2_lite_final.json'
OUT_REPORT = 'output/rss/v2_final_merge_report.json'


def fix_bool(value):
    """修复boolean字段：1/0/'true'/'false'/None → bool"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        if value.lower() in ('true', '1', 'yes'):
            return True
        if value.lower() in ('false', '0', 'no', ''):
            return False
    return bool(value)


def fix_none(value, default=''):
    """修复Python None污染"""
    if value is None:
        return default
    return value


def sanitize_source(src):
    """清洗单个源：修复bool/None字段"""
    bool_fields = ['enabled', 'enableJs', 'enabledCookieJar', 'singleUrl',
                   'showWebLog', 'loadWithBaseUrl', 'cacheFirst', 'preload']
    str_fields = ['sourceName', 'sourceUrl', 'sourceComment', 'sourceGroup',
                  'sourceIcon', 'searchUrl', 'sortUrl', 'header', 'lastHost',
                  'loginUrl', 'loginCheckJs', 'ruleArticles', 'ruleContent',
                  'ruleImage', 'ruleLink', 'ruleNextPage', 'rulePubDate',
                  'ruleTitle', 'lastUpdateTime']
    int_fields = ['type', 'articleStyle', 'customOrder', 'weight', 'parseConcurrency']

    out = dict(src)  # 浅拷贝
    for f in bool_fields:
        if f in out:
            out[f] = fix_bool(out[f])
    for f in str_fields:
        if f in out:
            out[f] = fix_none(out[f], '')
    for f in int_fields:
        if f in out:
            v = out[f]
            if v is None:
                out[f] = 0
            else:
                try:
                    out[f] = int(v)
                except (ValueError, TypeError):
                    out[f] = 0
    return out


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print('=' * 60)
    print('订阅源最终合并 v2')
    print('=' * 60)

    # 1. 加载基础源
    base = load_json(BASE_FILE)
    sources = [sanitize_source(s) for s in base['sources']]
    base_total = len(sources)
    print(f'[1] 基础源加载: {base_total} 个')

    # 基础type统计
    base_type_counts = collections.Counter(s.get('type', 0) for s in sources)
    print(f'    基础type分布: {dict(base_type_counts)}')

    # 2. 应用视频源重新识别
    video = load_json(VIDEO_FILE)
    video_results = video.get('results', [])
    print(f'[2] 视频源重新识别结果: {len(video_results)} 条')

    video_applied_high = 0   # confidence>=0.7 → type=2
    video_applied_possible = 0  # 0.4-0.7 → 标记
    video_applied_skipped = 0

    for r in video_results:
        idx = r.get('idx')
        if idx is None or idx < 0 or idx >= len(sources):
            video_applied_skipped += 1
            continue

        conf = r.get('confidence', 0)
        src = sources[idx]

        if conf >= 0.7:
            # 高置信度：更新type=2
            src['type'] = 2
            # 应用ruleContent策略
            strategy = r.get('rule_content_strategy', '')
            rule_designed = r.get('rule_content_designed', '')
            if rule_designed:
                src['ruleContent'] = rule_designed
            # 启用JS
            if r.get('enable_js'):
                src['enableJs'] = True
            # 追加标记到sourceComment（不覆盖原有内容）
            marker = f'[AI_REIDENTIFY:video|conf={conf:.2f}|strategy={strategy}]'
            sc = src.get('sourceComment', '') or ''
            if 'AI_REIDENTIFY:video' not in sc:
                src['sourceComment'] = (sc + ' ' + marker).strip() if sc else marker
            video_applied_high += 1
        elif 0.4 <= conf < 0.7:
            # 可能视频源：保留type，标记sourceComment
            marker = f'[AI_REIDENTIFY:possible_video|conf={conf:.2f}]'
            sc = src.get('sourceComment', '') or ''
            if 'AI_REIDENTIFY:possible_video' not in sc:
                src['sourceComment'] = (sc + ' ' + marker).strip() if sc else marker
            video_applied_possible += 1
        else:
            video_applied_skipped += 1

    print(f'    高置信度视频源(type=2): {video_applied_high}')
    print(f'    可能视频源(标记): {video_applied_possible}')
    print(f'    跳过(低置信度/无效idx): {video_applied_skipped}')

    # 3. 标记导航站父源 + 追加拆分子源
    nav = load_json(NAV_FILE)
    nav_results = nav.get('results', [])
    nav_sub_sources = nav.get('sub_sources', [])
    print(f'[3] 导航站拆分: {len(nav_results)} 父源, {len(nav_sub_sources)} 子源')

    nav_parent_indices = set()
    nav_parent_marked = 0
    for r in nav_results:
        pidx = r.get('parent_idx')
        if pidx is None or pidx < 0 or pidx >= len(sources):
            continue
        src = sources[pidx]
        src['nav_parent'] = True
        src['enabled'] = False  # 父源禁用
        nav_parent_indices.add(pidx)
        # 追加标记
        marker = '[NAV_PARENT:split_to_sub_sources]'
        sc = src.get('sourceComment', '') or ''
        if 'NAV_PARENT' not in sc:
            src['sourceComment'] = (sc + ' ' + marker).strip() if sc else marker
        nav_parent_marked += 1

    print(f'    父源标记nav_parent+enabled=false: {nav_parent_marked}')

    # 追加拆分子源（清洗后）
    sub_sources_added = 0
    for sub in nav_sub_sources:
        clean = sanitize_source(sub)
        # 确保子源标记
        clean['nav_sub_source'] = True
        # 子源默认启用
        if 'enabled' not in clean:
            clean['enabled'] = True
        sources.append(clean)
        sub_sources_added += 1

    print(f'    子源追加: {sub_sources_added}')

    full_total = len(sources)
    print(f'[4] 完整版总数: {full_total} (原{base_total} + 子源{sub_sources_added})')

    # 4. 生成完整版JSON
    full_data = {
        'version': 'optimized_v2_full_final',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_sources': full_total,
        'base_sources': base_total,
        'sub_sources_added': sub_sources_added,
        'sources': sources
    }
    save_json(OUT_FULL, full_data)
    print(f'[5] 完整版已保存: {OUT_FULL}')

    # 5. 生成精简版
    # 移除规则：
    # - truly_dead: enabled=false AND sourceComment含access_failed AND NOT nav_parent
    # - nav_parent且enabled=false（30个父源）
    # - 仍需人工且无法访问: enabled=false AND sourceComment含skipped
    # 保留：所有拆分子源（nav_sub_source=true）

    truly_dead_indices = set()
    nav_parent_disabled_indices = set()
    manual_inaccessible_indices = set()

    for i, src in enumerate(sources):
        is_nav_sub = src.get('nav_sub_source', False)
        if is_nav_sub:
            continue  # 子源全部保留

        is_nav_parent = src.get('nav_parent', False)
        enabled = src.get('enabled', True)
        sc = str(src.get('sourceComment', ''))

        if is_nav_parent and not enabled:
            nav_parent_disabled_indices.add(i)
            continue

        if not enabled and 'access_failed' in sc:
            truly_dead_indices.add(i)
            continue

        if not enabled and 'skipped' in sc.lower():
            manual_inaccessible_indices.add(i)
            continue

    removed_truly_dead = len(truly_dead_indices)
    removed_nav_parent = len(nav_parent_disabled_indices)
    removed_manual = len(manual_inaccessible_indices)
    total_removed = removed_truly_dead + removed_nav_parent + removed_manual

    print(f'[6] 精简版移除统计:')
    print(f'    truly_dead(access_failed+disabled): {removed_truly_dead}')
    print(f'    nav_parent disabled: {removed_nav_parent}')
    print(f'    manual inaccessible: {removed_manual}')
    print(f'    总移除: {total_removed}')

    # 构建精简版
    removed_set = truly_dead_indices | nav_parent_disabled_indices | manual_inaccessible_indices
    lite_sources = [src for i, src in enumerate(sources) if i not in removed_set]
    lite_total = len(lite_sources)
    print(f'    精简版总数: {lite_total}')

    lite_data = {
        'version': 'optimized_v2_lite_final',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_sources': lite_total,
        'removed_count': total_removed,
        'removed_breakdown': {
            'truly_dead': removed_truly_dead,
            'nav_parent_disabled': removed_nav_parent,
            'manual_inaccessible': removed_manual
        },
        'sources': lite_sources
    }
    save_json(OUT_LITE, lite_data)
    print(f'[7] 精简版已保存: {OUT_LITE}')

    # 6. 生成合并报告
    # 完整版type统计
    full_type_counts = collections.Counter(s.get('type', 0) for s in sources)
    lite_type_counts = collections.Counter(s.get('type', 0) for s in lite_sources)

    # 字段覆盖率统计（完整版）
    key_fields = ['sourceName', 'sourceUrl', 'sourceComment', 'sourceIcon',
                  'searchUrl', 'sortUrl', 'ruleArticles', 'ruleContent', 'ruleImage',
                  'ruleLink', 'ruleNextPage', 'rulePubDate', 'ruleTitle',
                  'enableJs', 'enabled', 'header', 'loginUrl', 'type']
    field_coverage_full = {}
    for f in key_fields:
        non_empty = sum(1 for s in sources if s.get(f) not in (None, '', False, 0))
        field_coverage_full[f] = {
            'non_empty': non_empty,
            'total': full_total,
            'coverage': round(non_empty / full_total * 100, 2) if full_total else 0
        }

    # 父源禁用统计
    nav_parent_count = sum(1 for s in sources if s.get('nav_parent', False))
    nav_sub_count = sum(1 for s in sources if s.get('nav_sub_source', False))

    # 视频源识别策略统计
    strategy_counts = collections.Counter()
    for r in video_results:
        if r.get('confidence', 0) >= 0.7:
            strategy_counts[r.get('rule_content_strategy', 'unknown')] += 1

    report = {
        'report_version': 'v2_final_merge',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'inputs': {
            'base_file': BASE_FILE,
            'video_reidentify_file': VIDEO_FILE,
            'nav_split_file': NAV_FILE
        },
        'outputs': {
            'full_final': OUT_FULL,
            'lite_final': OUT_LITE
        },
        'base_stats': {
            'total_sources': base_total,
            'type_distribution': {str(k): v for k, v in base_type_counts.items()}
        },
        'video_reidentify_stats': {
            'total_results': len(video_results),
            'high_confidence_applied': video_applied_high,
            'possible_video_marked': video_applied_possible,
            'skipped': video_applied_skipped,
            'strategy_distribution': dict(strategy_counts)
        },
        'nav_split_stats': {
            'total_parent_sources': len(nav_results),
            'parent_marked_disabled': nav_parent_marked,
            'sub_sources_added': sub_sources_added
        },
        'full_final_stats': {
            'total_sources': full_total,
            'type_distribution': {str(k): v for k, v in full_type_counts.items()},
            'nav_parent_count': nav_parent_count,
            'nav_sub_source_count': nav_sub_count
        },
        'lite_final_stats': {
            'total_sources': lite_total,
            'type_distribution': {str(k): v for k, v in lite_type_counts.items()},
            'removed': {
                'total': total_removed,
                'truly_dead': removed_truly_dead,
                'nav_parent_disabled': removed_nav_parent,
                'manual_inaccessible': removed_manual
            }
        },
        'field_coverage_full': field_coverage_full
    }

    save_json(OUT_REPORT, report)
    print(f'[8] 合并报告已保存: {OUT_REPORT}')

    # 7. 打印汇总（仅技术指标）
    print('=' * 60)
    print('合并完成汇总')
    print('=' * 60)
    print(f'基础源: {base_total}')
    print(f'  type分布: {dict(base_type_counts)}')
    print(f'视频源识别应用: 高置信度={video_applied_high}, 可能={video_applied_possible}, 跳过={video_applied_skipped}')
    print(f'导航站拆分: 父源禁用={nav_parent_marked}, 子源追加={sub_sources_added}')
    print(f'完整版: {full_total} 源')
    print(f'  type分布: {dict(full_type_counts)}')
    print(f'精简版: {lite_total} 源 (移除{total_removed})')
    print(f'  type分布: {dict(lite_type_counts)}')
    print(f'  移除明细: truly_dead={removed_truly_dead}, nav_parent_disabled={removed_nav_parent}, manual={removed_manual}')
    print(f'字段覆盖率(完整版, 非空%):')
    for f in ['sourceUrl', 'ruleContent', 'ruleArticles', 'ruleImage', 'searchUrl', 'sortUrl', 'enableJs']:
        if f in field_coverage_full:
            print(f'  {f}: {field_coverage_full[f]["coverage"]}% ({field_coverage_full[f]["non_empty"]}/{full_total})')
    print('=' * 60)

    # 返回摘要供调用方使用
    return {
        'base_total': base_total,
        'full_total': full_total,
        'lite_total': lite_total,
        'video_high': video_applied_high,
        'video_possible': video_applied_possible,
        'nav_parent_marked': nav_parent_marked,
        'sub_sources_added': sub_sources_added,
        'removed_truly_dead': removed_truly_dead,
        'removed_nav_parent': removed_nav_parent,
        'removed_manual': removed_manual,
        'full_type_dist': dict(full_type_counts),
        'lite_type_dist': dict(lite_type_counts)
    }


if __name__ == '__main__':
    result = main()
    print('\n返回摘要:', json.dumps(result, ensure_ascii=False))
