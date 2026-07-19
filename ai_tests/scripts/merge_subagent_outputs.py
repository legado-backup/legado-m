"""
合并8个子代理的分析输出,构建最终的订阅源JSON文件。

输入:
  - output/rss/classified_v2.json (222源,无idx字段,按列表索引)
  - 8个subagent_*_analysis.json文件

输出:
  - output/rss/optimized_v2_full.json (完整版,truly_dead的enabled=false)
  - output/rss/optimized_v2_lite.json (精简版,移除truly_dead和禁用源)
  - output/rss/v2_merge_report.json (合并报告,只含技术指标)
"""
import json
import copy
from pathlib import Path
from collections import defaultdict

BASE = Path("output/rss")

# Legado 订阅源标准字段(用于规范化输出)
LEGADO_RSS_FIELDS = [
    'articleStyle', 'cacheFirst', 'customOrder', 'enableJs', 'enabled',
    'enabledCookieJar', 'header', 'lastHost', 'lastUpdateTime', 'loadWithBaseUrl',
    'loginCheckJs', 'loginUrl', 'parseConcurrency', 'preload', 'ruleArticles',
    'ruleContent', 'ruleImage', 'ruleLink', 'ruleNextPage', 'rulePubDate',
    'ruleTitle', 'searchUrl', 'showWebLog', 'singleUrl', 'sortUrl',
    'sourceGroup', 'sourceIcon', 'sourceName', 'sourceUrl', 'type',
    'weight', 'sourceComment', 'jsRule', 'concurrentRate', 'bookSourceUrl',
    'loginUi', 'ruleDescription', 'ruleReview', 'coverDecodeJs', 'variable',
    'charset', 'id',
    # Legado 扩展字段(合法保留)
    'style', 'injectJs', 'variableComment', 'shouldOverrideUrlLoading',
    'jsLib', 'preloadJs', 'contentBlacklist', 'coverDecodeJs',
    'loginField', 'loginCheckJs', 'bookSourceUrl', 'ruleBookContent',
    'ruleToc', 'ruleDescription', 'ruleReview', 'lastUpdateTime',
    'responseTime', 'customOrder',
]

# 合并时跳过的字段(下划线开头为分析中间产物,非Legado字段)
def is_legado_field(name):
    """判断是否为Legado订阅源合法字段"""
    if not isinstance(name, str):
        return False
    # 下划线开头的字段(如_search_form_method)为分析中间产物,过滤
    if name.startswith('_'):
        return False
    # 已知Legado字段
    if name in LEGADO_RSS_FIELDS:
        return True
    # 不在已知列表但符合驼峰命名规则的字段,保守保留(避免误删)
    # 但要排除明显的分析字段
    ANALYSIS_FIELDS = {
        'analysis_notes', 'elapsed_seconds', 'page_signals', 'dom_info',
        'field_status', 'access_status', 'response_code', 'nav_time_ms',
        'final_url_pattern', 'page_title_pattern', 'needs_login', 'needs_js_eval',
        'has_anti_crawler', 'has_popup', 'has_cloudflare', 'suggested_searchUrl_pattern',
        'suggested_jsRule_pattern', 'suggested_field_strategy', 'error_type',
        'error_msg_sanitized', 'field_filled_count', 'field_total',
        'has_searchUrl', 'has_jsRule', 'has_loginUrl', 'source_url_accessible',
        'recovered', 'recovered_url', 'recovery_strategy', 'final_status',
        'original_error', 'original_sourceUrl_len', 'recovered_url_len',
        'recovered_method', 'accessible', 'confidence', 'tried_fields',
        'candidate_count', 'rule_content_template', 'rule_content_strategy',
        'page_signals', 'html_length', 'http_status', 'domain_code',
        'page_title_masked', 'field_count', 'has_login', 'has_login_check',
        'has_header', 'static', 'dynamic', 'fields', 'special_config',
        'idx', 'customOrder', 'articleStyle', 'singleUrl',
        # 这些是合法的,但来自分析数据,需要单独处理
    }
    if name in ANALYSIS_FIELDS:
        return False
    return True

# 需要修复为bool的字段
BOOLEAN_FIELDS = {'enabled', 'enabledCookieJar', 'singleUrl', 'enableJs',
                   'loadWithBaseUrl', 'showWebLog', 'preload', 'cacheFirst'}

# 需要修复为int的字段
INT_FIELDS = {'articleStyle', 'customOrder', 'lastUpdateTime', 'weight', 'type', 'parseConcurrency'}


def fix_booleans(obj):
    """递归修复boolean字段(1/0/'true'/'false' → true/false)"""
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in BOOLEAN_FIELDS:
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    obj[key] = bool(value)
                elif isinstance(value, str):
                    obj[key] = value.lower() in ('true', '1', 'yes')
                else:
                    obj[key] = False
            elif isinstance(value, dict):
                fix_booleans(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        fix_booleans(item)


def fix_ints(obj):
    """递归修复int字段"""
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in INT_FIELDS and value is not None and not isinstance(value, int):
                try:
                    obj[key] = int(value)
                except (ValueError, TypeError):
                    obj[key] = 0
            elif isinstance(value, dict):
                fix_ints(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        fix_ints(item)


def clean_none_pollution(obj):
    """清理Python None序列化污染(空字符串替代)"""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if obj[key] is None:
                obj[key] = ''
            elif isinstance(obj[key], (dict, list)):
                clean_none_pollution(obj[key])
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if item is None:
                obj[i] = ''
            elif isinstance(item, (dict, list)):
                clean_none_pollution(item)


def merge_field_non_empty(target, key, value):
    """非空字段才覆盖"""
    if value is None:
        return
    if isinstance(value, str) and value == '':
        return
    if isinstance(value, (list, dict)) and len(value) == 0:
        return
    target[key] = value


def load_json(name):
    p = BASE / name
    if not p.exists():
        print(f"[WARN] 缺失文件: {name}")
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_idx_map(results):
    """构建 idx → result 映射"""
    m = {}
    for r in results:
        if isinstance(r, dict) and 'idx' in r:
            m[r['idx']] = r
    return m


def main():
    # 1. 读取所有输入
    classified = load_json('classified_v2.json')
    if not classified:
        print("[FATAL] classified_v2.json 缺失或为空")
        return

    print(f"[1] 基础源数: {len(classified)}")

    img_data = load_json('subagent_image_analysis.json') or {'results': []}
    vid_data = load_json('subagent_video_analysis.json') or {'results': []}
    failed_data = load_json('subagent_failed_retry.json') or {'results': []}
    manual_data = load_json('subagent_manual_analysis.json') or {'results': []}
    web1 = load_json('subagent_web1_analysis.json') or {'results': []}
    web2 = load_json('subagent_web2_analysis.json') or {'results': []}
    web3 = load_json('subagent_web3_analysis.json') or {'results': []}
    web4 = load_json('subagent_web4_analysis.json') or {'results': []}

    # 构建idx → result映射
    img_map = build_idx_map(img_data.get('results', []))
    vid_map = build_idx_map(vid_data.get('results', []))
    failed_map = build_idx_map(failed_data.get('results', []))
    manual_map = build_idx_map(manual_data.get('results', []))
    web1_map = build_idx_map(web1.get('results', []))
    web2_map = build_idx_map(web2.get('results', []))
    web3_map = build_idx_map(web3.get('results', []))
    web4_map = build_idx_map(web4.get('results', []))

    print(f"[2] 各子代理结果数:")
    print(f"    image: {len(img_map)}, video: {len(vid_map)}")
    print(f"    failed_retry: {len(failed_map)}, manual: {len(manual_map)}")
    print(f"    web1: {len(web1_map)}, web2: {len(web2_map)}")
    print(f"    web3: {len(web3_map)}, web4: {len(web4_map)}")

    # 2. 复制基础数据作为完整版起点
    full_sources = []
    for idx, src in enumerate(classified):
        new_src = copy.deepcopy(src)
        new_src['_idx'] = idx  # 内部追踪字段(输出前删除)
        full_sources.append(new_src)

    # 3. 统计
    stats = {
        'total': len(full_sources),
        'type_dist': defaultdict(int),
        'merged_count': 0,
        'truly_dead': [],
        'recovered': [],
        'still_manual': [],
        'merge_by_source': defaultdict(int),
    }

    # 4. 按idx合并各子代理输出
    for idx, src in enumerate(full_sources):
        t = src.get('type', 0)
        stats['type_dist'][t] += 1

        merged_fields = 0

        # 4.1 合并 image 源(type=1)
        if idx in img_map:
            r = img_map[idx]
            stats['merge_by_source']['image'] += 1
            fields = r.get('fields', {}) or {}
            for fk, fv in fields.items():
                if not is_legado_field(fk):
                    continue
                merge_field_non_empty(src, fk, fv)
                if fv:
                    merged_fields += 1
            sc = r.get('special_config', {}) or {}
            for sk, sv in sc.items():
                if not is_legado_field(sk):
                    continue
                merge_field_non_empty(src, sk, sv)
                if sv not in (None, '', False):
                    merged_fields += 1

        # 4.2 合并 video 源(type=2)
        if idx in vid_map:
            r = vid_map[idx]
            stats['merge_by_source']['video'] += 1
            fields = r.get('fields', {}) or {}
            for fk, fv in fields.items():
                if not is_legado_field(fk):
                    continue
                merge_field_non_empty(src, fk, fv)
                if fv:
                    merged_fields += 1
            sc = r.get('special_config', {}) or {}
            for sk, sv in sc.items():
                if not is_legado_field(sk):
                    continue
                merge_field_non_empty(src, sk, sv)
                if sv not in (None, '', False):
                    merged_fields += 1

        # 4.3 合并 web1 源(type=0)
        if idx in web1_map:
            r = web1_map[idx]
            stats['merge_by_source']['web1'] += 1
            fields = r.get('fields', {}) or {}
            for fk, fv in fields.items():
                if not is_legado_field(fk):
                    continue
                merge_field_non_empty(src, fk, fv)
                if fv:
                    merged_fields += 1
            sc = r.get('special_config', {}) or {}
            for sk, sv in sc.items():
                if not is_legado_field(sk):
                    continue
                merge_field_non_empty(src, sk, sv)
                if sv not in (None, '', False):
                    merged_fields += 1

        # 4.4 合并 web2 源(type=0)
        if idx in web2_map:
            r = web2_map[idx]
            stats['merge_by_source']['web2'] += 1
            fields = r.get('fields', {}) or {}
            for fk, fv in fields.items():
                if not is_legado_field(fk):
                    continue
                merge_field_non_empty(src, fk, fv)
                if fv:
                    merged_fields += 1
            sc = r.get('special_config', {}) or {}
            for sk, sv in sc.items():
                if not is_legado_field(sk):
                    continue
                merge_field_non_empty(src, sk, sv)
                if sv not in (None, '', False):
                    merged_fields += 1

        # 4.5 合并 web3 源(type=0) - 只有suggested字段
        if idx in web3_map:
            r = web3_map[idx]
            stats['merge_by_source']['web3'] += 1
            # 用suggested_searchUrl_pattern填充searchUrl(若原为空)
            sup = r.get('suggested_searchUrl_pattern', '')
            if sup:
                merge_field_non_empty(src, 'searchUrl', sup)
                merged_fields += 1
            # 用suggested_jsRule_pattern填充jsRule(新增字段)
            sjr = r.get('suggested_jsRule_pattern', '')
            if sjr:
                merge_field_non_empty(src, 'jsRule', sjr)
                merged_fields += 1
            # needs_login=true时设置loginUrl占位
            if r.get('needs_login'):
                if not src.get('loginUrl'):
                    src['loginUrl'] = ''  # 占位,标记需要登录
                    merged_fields += 1
            # needs_js_eval=true且无enableJs时开启
            if r.get('needs_js_eval') and 'enableJs' not in src:
                src['enableJs'] = True
                merged_fields += 1
            # has_cloudflare=true时启用cacheFirst
            if r.get('has_cloudflare'):
                src['cacheFirst'] = True
                merged_fields += 1

        # 4.6 合并 web4 源(type=0) - static含fields
        if idx in web4_map:
            r = web4_map[idx]
            stats['merge_by_source']['web4'] += 1
            static = r.get('static', {}) or {}
            fields = static.get('fields', {}) or {}
            for fk, fv in fields.items():
                if not is_legado_field(fk):
                    continue
                merge_field_non_empty(src, fk, fv)
                if fv:
                    merged_fields += 1
            # 静态字段:enableJs/articleStyle/singleUrl
            for sk in ('enableJs', 'articleStyle', 'singleUrl', 'has_login', 'has_login_check'):
                if sk in static:
                    val = static[sk]
                    # has_login/has_login_check → 转换为loginUrl提示
                    if sk == 'has_login' and val:
                        if not src.get('loginUrl'):
                            src['loginUrl'] = ''  # 占位
                        merged_fields += 1
                    elif sk == 'enableJs':
                        merge_field_non_empty(src, 'enableJs', val)
                        merged_fields += 1
                    elif sk == 'articleStyle':
                        merge_field_non_empty(src, 'articleStyle', val)
                        merged_fields += 1
                    elif sk == 'singleUrl':
                        merge_field_non_empty(src, 'singleUrl', val)
                        merged_fields += 1

        # 4.7 应用 failed_retry 结果
        if idx in failed_map:
            r = failed_map[idx]
            stats['merge_by_source']['failed_retry'] += 1
            recovered = r.get('recovered', False)
            rurl = r.get('recovered_url', '')
            if recovered and rurl:
                # 用recovered_url替换sourceUrl
                src['sourceUrl'] = rurl
                src['enabled'] = True
                stats['recovered'].append(idx)
                merged_fields += 1
            elif not recovered:
                # truly_dead: 禁用
                src['enabled'] = False
                stats['truly_dead'].append(idx)

        # 4.8 应用 manual_analysis 结果
        if idx in manual_map:
            r = manual_map[idx]
            stats['merge_by_source']['manual'] += 1
            accessible = r.get('accessible', False)
            method = r.get('recovered_method', '')
            # accessible=true时用recovered_url替换(从长度推断有URL,但manual没直接给URL,
            # 通过recovered_method判断:icon_host/injectJs_host表示已恢复)
            if accessible and method and method != 'none':
                # 没有直接URL字段,但标记为已恢复,保留原sourceUrl但enabled=true
                src['enabled'] = True
                stats['recovered'].append(idx)
                merged_fields += 1
            elif not accessible or method == 'none':
                # 仍需人工,且无法访问 → 标记禁用
                stats['still_manual'].append(idx)
                # 在full版保留但禁用
                if not accessible:
                    src['enabled'] = False

        if merged_fields > 0:
            stats['merged_count'] += 1

    # 5. 清理污染并修复字段
    clean_none_pollution(full_sources)
    fix_booleans(full_sources)
    fix_ints(full_sources)

    # 5.1 移除所有以下划线开头的非Legado字段(防御性清理)
    for src in full_sources:
        to_remove = [k for k in src.keys() if isinstance(k, str) and k.startswith('_')]
        for k in to_remove:
            src.pop(k, None)

    # 6. 统计字段覆盖率(合并后)
    field_coverage_after = defaultdict(int)
    field_coverage_before = defaultdict(int)
    # 合并前(原classified)
    for src in classified:
        for k, v in src.items():
            if v not in (None, '', False, 0) and not (isinstance(v, (list, dict)) and len(v) == 0):
                field_coverage_before[k] += 1
    # 合并后
    for src in full_sources:
        for k, v in src.items():
            if k == '_idx':
                continue
            if v not in (None, '', False, 0) and not (isinstance(v, (list, dict)) and len(v) == 0):
                field_coverage_after[k] += 1

    # 7. 生成完整版(去掉_idx)
    for src in full_sources:
        src.pop('_idx', None)

    full_out = {
        'version': 'optimized_v2_full',
        'total_sources': len(full_sources),
        'sources': full_sources,
    }
    with open(BASE / 'optimized_v2_full.json', 'w', encoding='utf-8') as f:
        json.dump(full_out, f, ensure_ascii=False, indent=2)
    print(f"[3] 完整版已写入: optimized_v2_full.json ({len(full_sources)}源)")

    # 8. 生成精简版
    # 移除:truly_dead / nav_parent禁用 / 仍需人工且无法访问
    truly_dead_set = set(stats['truly_dead'])
    still_manual_dead_set = set(stats['still_manual'])

    lite_sources = []
    removed_reasons = defaultdict(int)
    for idx, src in enumerate(full_sources):
        if idx in truly_dead_set:
            removed_reasons['truly_dead'] += 1
            continue
        if idx in still_manual_dead_set:
            # 仍需人工且无法访问 → 移除
            removed_reasons['manual_inaccessible'] += 1
            continue
        if not src.get('enabled', True):
            removed_reasons['disabled'] += 1
            continue
        lite_sources.append(src)

    lite_out = {
        'version': 'optimized_v2_lite',
        'total_sources': len(lite_sources),
        'sources': lite_sources,
    }
    with open(BASE / 'optimized_v2_lite.json', 'w', encoding='utf-8') as f:
        json.dump(lite_out, f, ensure_ascii=False, indent=2)
    print(f"[4] 精简版已写入: optimized_v2_lite.json ({len(lite_sources)}源)")
    print(f"    移除统计: {dict(removed_reasons)}")

    # 9. 生成合并报告(只含技术指标)
    report = {
        'summary': {
            'total_input': len(classified),
            'total_full': len(full_sources),
            'total_lite': len(lite_sources),
            'merged_sources_count': stats['merged_count'],
            'type_distribution': dict(stats['type_dist']),
            'merge_by_source': dict(stats['merge_by_source']),
        },
        'recovery_stats': {
            'recovered_count': len(stats['recovered']),
            'recovered_idx': stats['recovered'],
            'truly_dead_count': len(stats['truly_dead']),
            'truly_dead_idx': stats['truly_dead'],
            'still_manual_count': len(stats['still_manual']),
            'still_manual_idx': stats['still_manual'],
        },
        'removed_in_lite': {
            'reasons': dict(removed_reasons),
            'total_removed': len(full_sources) - len(lite_sources),
        },
        'field_coverage': {
            'before_merge': dict(field_coverage_before),
            'after_merge': dict(field_coverage_after),
            'improvement': {
                k: field_coverage_after.get(k, 0) - field_coverage_before.get(k, 0)
                for k in set(field_coverage_before) | set(field_coverage_after)
                if field_coverage_after.get(k, 0) > field_coverage_before.get(k, 0)
            },
        },
        'subagent_summary': {
            'image': {
                'total_analyzed': img_data.get('total_analyzed'),
                'success_count': img_data.get('success_count'),
                'failed_count': img_data.get('failed_count'),
            },
            'video': {
                'total_analyzed': vid_data.get('total_analyzed'),
                'success_count': vid_data.get('success_count'),
                'failed_count': vid_data.get('failed_count'),
            },
            'failed_retry': {
                'total_analyzed': failed_data.get('total_analyzed'),
                'recovered_count': failed_data.get('recovered_count'),
                'truly_dead_count': failed_data.get('truly_dead_count'),
                'needs_login_count': failed_data.get('needs_login_count'),
            },
            'manual': {
                'total_analyzed': manual_data.get('total_analyzed'),
                'recovered_count': manual_data.get('recovered_count'),
                'accessible_count': manual_data.get('accessible_count'),
                'still_manual_count': manual_data.get('still_manual_count'),
            },
            'web1': {
                'total_analyzed': web1.get('total_analyzed'),
                'success_count': web1.get('success_count'),
            },
            'web2': {
                'total_analyzed': web2.get('total_analyzed'),
                'success_count': web2.get('success_count'),
            },
            'web3': {
                'total_analyzed': web3.get('total_analyzed'),
            },
            'web4': {
                'total_analyzed': web4.get('total_analyzed'),
            },
        },
    }
    with open(BASE / 'v2_merge_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[5] 合并报告已写入: v2_merge_report.json")

    # 10. 打印汇总(只输出技术指标)
    print("\n" + "=" * 60)
    print("合并汇总(技术指标)")
    print("=" * 60)
    print(f"输入源数: {len(classified)}")
    print(f"完整版源数: {len(full_sources)}")
    print(f"精简版源数: {len(lite_sources)}")
    print(f"成功合并字段源数: {stats['merged_count']}")
    print(f"\n类型分布: {dict(stats['type_dist'])}")
    print(f"各子代理合并数: {dict(stats['merge_by_source'])}")
    print(f"\n恢复统计:")
    print(f"  recovered: {len(stats['recovered'])} 个")
    print(f"  truly_dead: {len(stats['truly_dead'])} 个")
    print(f"  still_manual: {len(stats['still_manual'])} 个")
    print(f"\n精简版移除: {dict(removed_reasons)}")

    print(f"\n字段覆盖率提升 TOP10:")
    improvements = [(k, v) for k, v in report['field_coverage']['improvement'].items()]
    improvements.sort(key=lambda x: -x[1])
    for k, v in improvements[:10]:
        before = field_coverage_before.get(k, 0)
        after = field_coverage_after.get(k, 0)
        print(f"  {k}: {before} → {after} (+{v})")


if __name__ == '__main__':
    main()
