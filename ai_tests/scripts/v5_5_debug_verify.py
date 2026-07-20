#!/usr/bin/env python3
r"""v5_5_debug_verify.py — 对 V5.5 最终 JSON 做 5 维度真机调试验证

复用 v5_4_debug_verify.py 的核心逻辑，仅修改：
- JSON_PATH 指向 optimized_v5_5_final.json
- 输出路径改为 v5_5_*
- 只验证修复后的源（enabled=true 的源）
- 增加进度日志和中间结果保存

输出：
- output/rss/v5_5_debug_verify_result.json
- output/rss/v5_5_debug_verify_report.md
- output/rss/v5_5_debug_shots/
- output/rss/v5_5_debug_logs/

安全规范：禁止输出源名称/URL/cookie，全部用编号(源[idx])。
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# === 配置 ===
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DEBUG_ACTIVITY = f'{PKG}/io.legado.app.ui.rss.source.debug.RssSourceDebugActivity'
JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_5_final.json'
OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss')
SHOTS_DIR = OUT_DIR / 'v5_5_debug_shots'
LOGS_DIR = OUT_DIR / 'v5_5_debug_logs'
RESULT_JSON = OUT_DIR / 'v5_5_debug_verify_result.json'
REPORT_MD = OUT_DIR / 'v5_5_debug_verify_report.md'
SHOTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 超时配置
DEBUG_WAIT_SEC = 15
ACTIVITY_LOAD_SEC = 3
SEARCH_WAIT_SEC = 15


def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def adb_shell(cmd_str, timeout=30):
    return adb('shell', cmd_str, timeout=timeout)


def clear_log():
    adb('logcat', '-c', timeout=10)


def dump_log(timeout=10):
    r = adb('logcat', '-d', '-v', 'threadtime', timeout=timeout)
    return r.stdout.decode('utf-8', errors='ignore')


def dump_ui(name):
    remote = '/sdcard/ui_dump.xml'
    adb_shell(f'uiautomator dump {remote}', timeout=15)
    local = OUT_DIR / name
    adb('pull', remote, str(local), timeout=15)
    if local.exists():
        return str(local), local.read_text(encoding='utf-8', errors='ignore')
    return '', ''


def screenshot(name):
    remote = '/sdcard/scr.png'
    adb_shell(f'screencap -p {remote}', timeout=10)
    local = SHOTS_DIR / name
    adb('pull', remote, str(local), timeout=15)
    return str(local)


def tap(x, y):
    adb_shell(f'input tap {x} {y}', timeout=10)


def force_stop_app():
    adb_shell(f'am force-stop {PKG}', timeout=10)


def parse_ui_nodes(xml_text):
    nodes = []
    for m in re.finditer(r'<node\b[^>]*?>', xml_text, re.DOTALL):
        tag = m.group(0)
        attrs = {}
        for am in re.finditer(r'([\w\-:]+)="([^"]*)"', tag):
            attrs[am.group(1)] = am.group(2)
        if attrs:
            nodes.append(attrs)
    return nodes


def get_bounds_center(bounds_str):
    m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str or '')
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_node_by_resource_id(nodes, resource_id_pattern):
    results = []
    for n in nodes:
        rid = n.get('resource-id', '') or ''
        if re.search(resource_id_pattern, rid):
            results.append(n)
    return results


def start_debug_activity(source_url):
    force_stop_app()
    time.sleep(0.5)
    # source_url 可能含特殊字符，需要正确转义
    # am start -es 不支持含双引号的值，需要用单引号包裹
    escaped_url = source_url.replace('\\', '\\\\').replace('"', '\\"')
    adb_shell(
        f'am start -n {DEBUG_ACTIVITY} --es key "{escaped_url}"',
        timeout=10
    )
    time.sleep(ACTIVITY_LOAD_SEC)


def analyze_logcat_for_dimensions(log_text):
    """分析 logcat，提取5维度结果"""
    debug_lines = []
    for line in log_text.splitlines():
        if re.search(r'\bD\s+sourceDebug\s*:', line):
            m = re.search(r'sourceDebug\s*:\s*(.*)$', line)
            if m:
                debug_lines.append(m.group(1).strip())

    result = {
        'domain': 'unknown',
        'list': 'unknown',
        'search': 'unknown',
        'category': 'unknown',
        'content': 'unknown',
        'errors': [],
        'debug_lines': len(debug_lines),
        'key_markers': [],
    }

    full_text = '\n'.join(debug_lines)

    # 域名维度
    network_errors = []
    network_error_patterns = [
        (r'UnknownHostException|Unable to resolve host|getaddrinfo failed', 'dns_fail'),
        (r'SocketTimeoutException|timed out|timeout', 'timeout'),
        (r'SSLException|SSLHandshakeException|CertificateException', 'ssl_error'),
        (r'ConnectException|Connection refused|Connection reset|Connection closed', 'connection_refused'),
        (r'MalformedURLException|URISyntaxException', 'malformed_url'),
    ]
    for pat, code in network_error_patterns:
        if re.search(pat, log_text):
            network_errors.append(code)
    if network_errors:
        result['domain'] = 'fail'
        result['errors'].append(f'network:{",".join(network_errors)}')

    has_get_success = bool(re.search(r'≡获取成功', full_text))
    has_get_fail = bool(re.search(r'≡获取失败|获取失败', full_text))

    if has_get_success:
        result['domain'] = 'pass'
        result['key_markers'].append('domain_get_success')
    elif has_get_fail and not network_errors:
        result['domain'] = 'fail'
        result['errors'].append('get_fail_no_network_err')

    # 列表维度
    has_list_parse_start = bool(re.search(r'┌获取列表|┌获取下一页链接|┌获取标题|┌获取文章链接', full_text))
    list_size_match = re.search(r'└列表大小:(\d+)', full_text)
    list_size = int(list_size_match.group(1)) if list_size_match else -1
    has_list_complete = bool(re.search(r'︽列表页解析完成', full_text))
    has_list_empty = bool(re.search(r'列表页解析成功，为空|列表大小:0', full_text))

    if has_list_parse_start or has_list_complete:
        if has_list_complete and list_size > 0:
            result['list'] = 'pass'
            result['key_markers'].append(f'list_size:{list_size}')
        elif has_list_complete and list_size == 0:
            result['list'] = 'fail'
            result['errors'].append('list_empty')
        elif has_list_empty:
            result['list'] = 'fail'
            result['errors'].append('list_empty')
        elif list_size > 0:
            result['list'] = 'pass'
            result['key_markers'].append(f'list_size:{list_size}')
        else:
            result['list'] = 'fail'
            result['errors'].append('list_parse_failed')
    else:
        result['list'] = 'unknown'

    # 分类维度
    has_category_start = bool(re.search(r'⇒开始访问分类页|︾开始解析分类页|开始访问分类页', full_text))
    if not has_category_start and has_get_success and has_list_parse_start:
        has_category_start = True

    if has_category_start:
        if result['list'] == 'pass':
            result['category'] = 'pass'
            result['key_markers'].append('category_ok')
        elif result['list'] == 'fail':
            result['category'] = 'fail'
            result['errors'].append('category_list_failed')
        else:
            result['category'] = 'fail'
            result['errors'].append('category_parse_failed')

    # 正文维度
    has_content_start = bool(re.search(r'︾开始解析内容页|开始解析内容页', full_text))
    has_content_success = bool(re.search(r'︽内容页解析完成', full_text))
    has_content_skip = bool(re.search(r'内容规则为空|存在描述规则，不解析内容页|内容规则为空，默认获取整个网页', full_text))

    if has_content_start:
        if has_content_success:
            result['content'] = 'pass'
            result['key_markers'].append('content_ok')
        else:
            result['content'] = 'fail'
            result['errors'].append('content_parse_failed')
    elif has_content_skip:
        result['content'] = 'skip'
        result['key_markers'].append('content_skipped')
    elif has_get_success and not has_list_parse_start:
        result['content'] = 'pass' if has_get_success else 'unknown'
    else:
        result['content'] = 'unknown'

    if result['domain'] == 'unknown':
        if has_get_success or has_list_complete or has_content_success:
            result['domain'] = 'pass'

    return result


def analyze_search_log(log_text):
    debug_lines = []
    for line in log_text.splitlines():
        if re.search(r'\bD\s+sourceDebug\s*:', line):
            m = re.search(r'sourceDebug\s*:\s*(.*)$', line)
            if m:
                debug_lines.append(m.group(1).strip())
    full_text = '\n'.join(debug_lines)

    result = 'unknown'
    errors = []
    has_search_start = bool(re.search(r'⇒开始搜索关键字|开始搜索关键字', full_text))
    has_get_success = bool(re.search(r'≡获取成功', full_text))
    has_list_complete = bool(re.search(r'︽列表页解析完成', full_text))
    has_list_empty = bool(re.search(r'列表大小:0|列表页解析成功，为空|未获取到', full_text))
    has_search_url_empty = bool(re.search(r'搜索URL为空', full_text))
    has_error = bool(re.search(r'stackTrace|Exception|Error.*source|失败', full_text))

    if has_search_url_empty:
        result = 'fail'
        errors.append('search_url_empty')
    elif has_search_start or has_get_success or has_list_complete:
        if has_list_complete and not has_list_empty:
            result = 'pass'
        elif has_list_empty:
            result = 'fail'
            errors.append('search_result_empty')
        elif has_get_success and not has_list_complete:
            result = 'fail'
            errors.append('search_list_parse_failed')
        elif has_error:
            result = 'fail'
            errors.append('search_error')
        else:
            result = 'unknown'
            errors.append('search_inconclusive')
    else:
        result = 'unknown'

    return {'search': result, 'errors': errors, 'debug_lines': len(debug_lines)}


def trigger_category_debug(xml_text):
    nodes = parse_ui_nodes(xml_text)
    fl_nodes = find_node_by_resource_id(nodes, r'id/text_fl$')
    if not fl_nodes:
        for n in nodes:
            t = n.get('text', '') or ''
            if '::' in t and 'TextView' in n.get('class', ''):
                fl_nodes.append(n)

    if not fl_nodes:
        return False, 'textFl_not_found'

    b = get_bounds_center(fl_nodes[0].get('bounds', ''))
    if not b:
        return False, 'textFl_no_bounds'

    tap(*b)
    return True, f'tapped@{b}'


def trigger_search_debug(xml_text):
    nodes = parse_ui_nodes(xml_text)
    my_nodes = find_node_by_resource_id(nodes, r'id/text_my$')
    xt_nodes = find_node_by_resource_id(nodes, r'id/text_xt$')

    target = None
    used_kw = None
    if my_nodes:
        target = my_nodes[0]
        used_kw = (my_nodes[0].get('text', '') or '我的').strip() or '我的'
    elif xt_nodes:
        target = xt_nodes[0]
        used_kw = (xt_nodes[0].get('text', '') or '系统').strip() or '系统'
    else:
        return False, 'search_trigger_not_found', None

    b = get_bounds_center(target.get('bounds', ''))
    if not b:
        return False, 'search_btn_no_bounds', None

    tap(*b)
    return True, f'tapped_textMy_or_textXt@{b}', used_kw


def verify_one_source(idx, source_url):
    result = {
        'idx': idx,
        'domain': 'unknown',
        'list': 'unknown',
        'search': 'unknown',
        'category': 'unknown',
        'content': 'unknown',
        'errors': [],
        'category_log_lines': 0,
        'search_log_lines': 0,
        'key_markers': [],
    }

    # 第1轮：分类维度调试
    try:
        start_debug_activity(source_url)
        _, ui_xml = dump_ui(f'_tmp_debug_v5_5_{idx}.xml')
        if not ui_xml:
            result['errors'].append('ui_dump_failed_round1')
            return result

        clear_log()
        ok, msg = trigger_category_debug(ui_xml)
        if not ok:
            result['errors'].append(f'trigger_category_failed:{msg}')
            return result

        time.sleep(DEBUG_WAIT_SEC)
        log = dump_log(timeout=15)
        log_path = LOGS_DIR / f'src_{idx:03d}_category.log'
        log_path.write_text(log, encoding='utf-8', errors='ignore')

        cat_result = analyze_logcat_for_dimensions(log)
        result['domain'] = cat_result['domain']
        result['list'] = cat_result['list']
        result['category'] = cat_result['category']
        result['content'] = cat_result['content']
        result['category_log_lines'] = cat_result['debug_lines']
        result['errors'].extend(cat_result['errors'])
        result['key_markers'].extend(cat_result['key_markers'])

    except Exception as e:
        result['errors'].append(f'category_round_exception:{type(e).__name__}:{str(e)[:100]}')

    # 第2轮：搜索维度调试
    try:
        start_debug_activity(source_url)
        time.sleep(ACTIVITY_LOAD_SEC)
        _, ui_xml = dump_ui(f'_tmp_debug_v5_5_{idx}_search.xml')
        if not ui_xml:
            result['errors'].append('ui_dump_failed_round2')
            return result

        clear_log()
        ok, msg, used_kw = trigger_search_debug(ui_xml)
        if not ok:
            result['errors'].append(f'trigger_search_failed:{msg}')
            return result

        time.sleep(SEARCH_WAIT_SEC)
        log = dump_log(timeout=15)
        log_path = LOGS_DIR / f'src_{idx:03d}_search.log'
        log_path.write_text(log, encoding='utf-8', errors='ignore')

        search_result = analyze_search_log(log)
        result['search'] = search_result['search']
        result['search_log_lines'] = search_result['debug_lines']
        result['errors'].extend(search_result['errors'])
        if used_kw:
            result['key_markers'].append(f'search_kw:{used_kw}')

    except Exception as e:
        result['errors'].append(f'search_round_exception:{type(e).__name__}:{str(e)[:100]}')

    return result


def generate_report(results, enabled_sources):
    total = len(results)

    dimension_stats = {
        'domain': Counter(),
        'list': Counter(),
        'search': Counter(),
        'category': Counter(),
        'content': Counter(),
    }
    for r in results:
        for dim in dimension_stats:
            dimension_stats[dim][r[dim]] += 1

    failed_by_dim = defaultdict(list)
    for r in results:
        idx = r['idx']
        for dim in ['domain', 'list', 'search', 'category', 'content']:
            if r[dim] == 'fail':
                failed_by_dim[dim].append(idx)

    error_counter = Counter()
    for r in results:
        for e in r.get('errors', []):
            key = e.split(':')[0] if ':' in e else e
            error_counter[key] += 1

    md = []
    md.append('# V5.5 真机 5 维度调试验证报告')
    md.append('')
    md.append(f'**生成时间**: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    md.append(f'**验证源数**: {total} 个 enabled=true 源')
    md.append(f'**数据来源**: `output/rss/optimized_v5_5_final.json`')
    md.append('')
    md.append('## 1. 调试统计')
    md.append('')
    md.append('| 维度 | pass | fail | skip | unknown | 通过率 |')
    md.append('|------|------|------|------|---------|--------|')
    for dim in ['domain', 'list', 'search', 'category', 'content']:
        s = dimension_stats[dim]
        pass_n = s.get('pass', 0)
        fail_n = s.get('fail', 0)
        skip_n = s.get('skip', 0)
        unk_n = s.get('unknown', 0)
        rate = pass_n / total * 100 if total else 0
        md.append(f'| {dim} | {pass_n} | {fail_n} | {skip_n} | {unk_n} | {rate:.1f}% |')
    md.append('')

    md.append('## 2. V5.4 vs V5.5 通过率对比')
    md.append('')
    md.append('| 维度 | V5.4通过率 | V5.5通过率 | 提升 |')
    md.append('|------|------------|------------|------|')
    # V5.4 基线数据
    v54_baseline = {
        'domain': 95.2, 'list': 42.9, 'search': 28.6,
        'category': 42.9, 'content': 9.5
    }
    for dim in ['domain', 'list', 'search', 'category', 'content']:
        s = dimension_stats[dim]
        pass_n = s.get('pass', 0)
        v55_rate = pass_n / total * 100 if total else 0
        v54_rate = v54_baseline[dim]
        diff = v55_rate - v54_rate
        diff_str = f'+{diff:.1f}%' if diff > 0 else f'{diff:.1f}%'
        md.append(f'| {dim} | {v54_rate:.1f}% | {v55_rate:.1f}% | {diff_str} |')
    md.append('')

    md.append('## 3. 完全通过源数')
    md.append('')
    full_pass = sum(1 for r in results if all(r[d] in ('pass', 'skip') for d in ['domain', 'list', 'search', 'category', 'content']))
    md.append(f'- V5.4: 2/21 (9.5%)')
    md.append(f'- V5.5: {full_pass}/{total} ({full_pass/total*100:.1f}%)')
    md.append('')

    md.append('## 4. 失败源清单（按维度分组，编号脱敏）')
    md.append('')
    for dim in ['domain', 'list', 'search', 'category', 'content']:
        fails = failed_by_dim.get(dim, [])
        md.append(f'### {dim} 维度失败（{len(fails)} 个）')
        if fails:
            md.append('')
            for idx in fails:
                r = next(x for x in results if x['idx'] == idx)
                err_str = '; '.join(r.get('errors', [])[:3])
                markers = ', '.join(r.get('key_markers', [])[:3])
                md.append(f'- 源[{idx}]: errors={err_str or "无"} | markers={markers or "无"}')
        else:
            md.append('')
            md.append('（无失败源）')
        md.append('')

    md.append('## 5. 关键发现')
    md.append('')
    fail_counts = {dim: dimension_stats[dim].get('fail', 0) for dim in dimension_stats}
    most_fail_dim = max(fail_counts, key=fail_counts.get)
    md.append(f'- **失败最多的维度**: `{most_fail_dim}`（{fail_counts[most_fail_dim]}/{total} 失败）')
    
    md.append('')
    md.append('## 6. 错误类型分布')
    md.append('')
    md.append('| 错误类型 | 出现次数 |')
    md.append('|----------|----------|')
    for err, cnt in error_counter.most_common():
        md.append(f'| {err} | {cnt} |')
    md.append('')

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))


def main():
    print('=' * 70)
    print('V5.5 真机5维度调试验证')
    print('=' * 70)

    # 加载 JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        all_sources = json.load(f)
    enabled_sources = [s for s in all_sources if s.get('enabled')]
    print(f'\n总源数: {len(all_sources)} | enabled: {len(enabled_sources)}')

    # 检查 ADB 连接
    r = adb('get-state', timeout=5)
    state = r.stdout.decode('utf-8', errors='ignore').strip()
    if state != 'device':
        print(f'❌ 设备状态异常: {state!r}')
        sys.exit(1)
    print(f'✅ 设备在线: {state}')

    # 启动 App
    print('\n--- 预启动 App（触发 Cronet 库加载）---')
    adb_shell(f'am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity', timeout=10)
    time.sleep(8)

    # 批量验证
    results = []
    total = len(enabled_sources)
    print(f'\n--- 开始 5 维度调试验证（共 {total} 源）---')

    for i, src in enumerate(enabled_sources):
        src_url = src.get('sourceUrl', '')
        print(f'\n[{i+1}/{total}] 源[{i}] 调试中...', flush=True)

        result = verify_one_source(i, src_url)
        results.append(result)

        # 实时进度
        if (i + 1) % 5 == 0 or i == total - 1:
            pass_count = sum(1 for r in results
                             if r['category'] == 'pass' and r['list'] == 'pass'
                             and r['content'] in ('pass', 'skip'))
            print(f'  进度: {i+1}/{total} | 分类+列表+正文通过: {pass_count}')

        # 每3个源保存一次中间结果
        if (i + 1) % 3 == 0 or i == total - 1:
            with open(RESULT_JSON, 'w', encoding='utf-8') as f:
                json.dump({
                    'total': len(results),
                    'results': results,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                }, f, ensure_ascii=False, indent=2)

    # 最终保存
    with open(RESULT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(results),
            'results': results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }, f, ensure_ascii=False, indent=2)

    # 生成报告
    generate_report(results, enabled_sources)

    print(f'\n✅ 验证完成')
    print(f'  结果JSON: {RESULT_JSON}')
    print(f'  报告MD: {REPORT_MD}')


if __name__ == '__main__':
    main()
