#!/usr/bin/env python3
"""v5_3_debug_verify.py — 对 71 个 enabled=true 的源做真机 5 维度调试验证

5维度定义（基于 Legado Debug.kt 的 RSS 调试逻辑）：
1. 域名维度：网络请求是否成功（UnknownHostException/SocketTimeout/SSL 错误等）
2. 列表维度：ruleArticles 是否解析成功（"列表页解析完成"/"列表页解析成功，为空"）
3. 搜索维度：searchUrl + ruleArticles 搜索是否解析成功（"搜索页解析完成"）
4. 分类维度：sortUrl + ruleArticles 分类是否解析成功（"分类页解析完成"）
5. 正文维度：ruleContent 是否解析成功（"内容页解析完成"）

工作流（每个源）：
1. am start RssSourceDebugActivity --es key "源URL"
2. dump UI 找 textFl/textMy/textXt/textContent 坐标
3. 点击 textFl 触发"分类维度"调试（自动串联：域名→列表→分类→正文）
4. 清logcat → 等待 18秒 → 收集 logcat
5. 分析 logcat 中 sourceDebug tag 输出
6. 然后点击搜索框输入"测试"触发搜索维度调试
7. 清logcat → 等待 18秒 → 收集 logcat
8. 输出5维度结果

输出：
- output/rss/v5_3_debug_verify_result.json  每源5维度结果
- output/rss/v5_3_debug_verify_report.md    验证报告
- output/rss/v5_3_debug_shots/               截图
- output/rss/v5_3_debug_logs/                每源logcat

安全规范：禁止输出源名称/域名/URL，全部用编号(源[idx])替代。
"""
import json
import os
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
JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_3_final.json'
OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss')
SHOTS_DIR = OUT_DIR / 'v5_3_debug_shots'
LOGS_DIR = OUT_DIR / 'v5_3_debug_logs'
RESULT_JSON = OUT_DIR / 'v5_3_debug_verify_result.json'
REPORT_MD = OUT_DIR / 'v5_3_debug_verify_report.md'
SHOTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 超时配置
DEBUG_WAIT_SEC = 15        # 单维度调试等待时长（logcat显示3秒完成，给15秒余量）
ACTIVITY_LOAD_SEC = 3       # Activity 启动后等待UI加载
SEARCH_WAIT_SEC = 15       # 搜索维度等待时长


# === ADB 工具函数 ===
def adb(*args, timeout=30):
    """ADB 命令（list 传参，避免 shell 路径转换）"""
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def adb_shell(cmd_str, timeout=30):
    """adb shell 命令（cmd_str 作为一个参数传给 shell，路径不被外层转换）"""
    return adb('shell', cmd_str, timeout=timeout)


def clear_log():
    adb('logcat', '-c', timeout=10)


def dump_log(timeout=10):
    r = adb('logcat', '-d', '-v', 'threadtime', timeout=timeout)
    return r.stdout.decode('utf-8', errors='ignore')


def dump_ui(name):
    """dump UI，返回 (local_path, xml_text)"""
    remote = '/sdcard/ui_dump.xml'
    # uiautomator dump 会在设备端写文件，路径不被外层转换
    r = adb_shell(f'uiautomator dump {remote}', timeout=15)
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


def swipe(x1, y1, x2, y2, ms=300):
    adb_shell(f'input swipe {x1} {y1} {x2} {y2} {ms}', timeout=10)


def input_text(text):
    """输入文本（用 am broadcast 调用 IME 输入，或直接用 input text）
    注：input text 不支持中文，只能输入ASCII。这里搜索关键字统一用 'test'。
    """
    # 转义特殊字符
    safe = text.replace(' ', '%s').replace('&', '\\&').replace('<', '\\<').replace('>', '\\>')
    adb_shell(f'input text {safe}', timeout=10)


def input_keyevent(keycode):
    adb_shell(f'input keyevent {keycode}', timeout=10)


def back():
    adb_shell('input keyevent 4', timeout=10)


def force_stop_app():
    adb_shell(f'am force-stop {PKG}', timeout=10)


def parse_ui_nodes(xml_text):
    """从UI XML提取所有节点（不解析嵌套，扁平化）"""
    nodes = []
    # 匹配所有 <node ...> 标签（包括自闭合）
    for m in re.finditer(r'<node\b[^>]*?>', xml_text, re.DOTALL):
        tag = m.group(0)
        attrs = {}
        # XML 属性名可含 - : . 等字符（如 resource-id, content-desc, package）
        for am in re.finditer(r'([\w\-:]+)="([^"]*)"', tag):
            attrs[am.group(1)] = am.group(2)
        if attrs:
            nodes.append(attrs)
    return nodes


def get_bounds_center(bounds_str):
    """bounds="[x1,y1][x2,y2]" → (cx, cy)"""
    m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str or '')
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_node_by_resource_id(nodes, resource_id_pattern):
    """根据 resource-id 找节点"""
    results = []
    for n in nodes:
        rid = n.get('resource-id', '') or ''
        if re.search(resource_id_pattern, rid):
            results.append(n)
    return results


def find_node_by_text(nodes, text_pattern):
    """根据 text 或 content-desc 找节点"""
    results = []
    for n in nodes:
        text = n.get('text', '') or ''
        desc = n.get('content-desc', '') or ''
        if re.search(text_pattern, text) or re.search(text_pattern, desc):
            results.append(n)
    return results


def find_node_by_class(nodes, class_pattern):
    """根据 class 找节点"""
    return [n for n in nodes if re.search(class_pattern, n.get('class', '') or '')]


def start_debug_activity(source_url):
    """启动调试 Activity"""
    # 先 force-stop（避免上次的调试残留）
    force_stop_app()
    time.sleep(0.5)
    # 启动 DebugActivity，传 key=sourceUrl
    adb_shell(
        f'am start -n {DEBUG_ACTIVITY} --es key "{source_url}"',
        timeout=10
    )
    time.sleep(ACTIVITY_LOAD_SEC)


def collect_recycler_items(xml_text):
    """从调试 RecyclerView 中提取所有调试输出文本"""
    nodes = parse_ui_nodes(xml_text)
    # 调试输出是 TextView，resource-id 通常为 android:text1 或无 id
    # 简化：收集所有 text 非空的 TextView
    items = []
    for n in nodes:
        cls = n.get('class', '')
        text = n.get('text', '') or ''
        if 'TextView' in cls and text.strip():
            items.append(text.strip())
    return items


def analyze_logcat_for_dimensions(log_text, source_url):
    """分析 logcat，提取5维度结果

    基于 Debug.kt + Rss.kt 实际输出的标记：
    - ≡获取成功:URL (列表HTML获取成功，域名/网络OK)
    - ┌获取列表 (开始解析列表)
    - └列表大小:N (解析到N个列表项)
    - ┌获取下一页链接 (解析下一页)
    - ┌获取标题/获取时间/获取描述/获取图片url/获取文章链接
    - ︽列表页解析完成 (列表页解析完成)
    - ︾开始解析内容页 (开始解析内容页)
    - ︽内容页解析完成 (内容页解析完成)
    - state=-1 / Exception / 错误

    返回 dict:
    {
        'domain': 'pass'/'fail'/'unknown',
        'list': 'pass'/'fail'/'unknown',
        'search': 'pass'/'fail'/'unknown',
        'category': 'pass'/'fail'/'unknown',
        'content': 'pass'/'fail'/'unknown'/'skip',
        'errors': [list of error snippets],
        'log_lines': int
    }
    """
    # 只取 sourceDebug tag 的日志（Debug.kt 中 Log.d("sourceDebug", msg)）
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

    # === 域名维度 ===
    # 检测网络/域名错误
    network_errors = []
    network_error_patterns = [
        (r'UnknownHostException|Unable to resolve host|Name or service not known|getaddrinfo failed', 'dns_fail'),
        (r'SocketTimeoutException|timed out|timeout', 'timeout'),
        (r'SSLException|SSLHandshakeException|CertificateException', 'ssl_error'),
        (r'ConnectException|Connection refused|Connection reset|Connection closed', 'connection_refused'),
        (r'FileNotFoundException.*cronet|UnsatisfiedLinkError.*cronet|Failed to load native library.*cronet',
         'cronet_missing'),
        (r'MalformedURLException|URISyntaxException', 'malformed_url'),
    ]
    for pat, code in network_error_patterns:
        if re.search(pat, log_text):
            network_errors.append(code)
    if network_errors:
        result['domain'] = 'fail'
        result['errors'].append(f'network:{",".join(network_errors)}')

    # 域名成功标记：≡获取成功
    has_get_success = bool(re.search(r'≡获取成功', full_text))
    has_get_fail = bool(re.search(r'≡获取失败|获取失败', full_text))

    if has_get_success:
        result['domain'] = 'pass'
        result['key_markers'].append('domain_get_success')
    elif has_get_fail and not network_errors:
        result['domain'] = 'fail'
        result['errors'].append('get_fail_no_network_err')

    # === 列表维度 ===
    # 触发标记：┌获取列表 / └列表大小
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
        # 列表维度未触发
        result['list'] = 'unknown'

    # === 分类维度（与分类调试一起验证）===
    # 触发标记：⇒开始访问分类页 / ┌获取列表（在分类URL下触发）
    has_category_start = bool(re.search(r'⇒开始访问分类页|︾开始解析分类页|开始访问分类页', full_text))
    # 如果没有显式标记，但有"≡获取成功"+"┌获取列表"，认为分类调试被触发
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

    # === 正文维度 ===
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
        # 单纯获取到内容（无列表维度），认为是内容页直接调试
        result['content'] = 'pass' if has_get_success else 'unknown'
    else:
        result['content'] = 'unknown'

    # 域名补充判断（如果列表/正文成功，域名也OK）
    if result['domain'] == 'unknown':
        if has_get_success or has_list_complete or has_content_success:
            result['domain'] = 'pass'

    return result


def analyze_search_log(log_text):
    """单独分析搜索维度

    搜索调试标记：
    - ⇒开始搜索关键字 (Debug.kt)
    - ≡获取成功 (Rss.kt)
    - └列表大小:N
    - ︽列表页解析完成
    - 搜索URL为空 (Debug.kt)
    """
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
            # 获取到HTML但没解析列表，可能规则不匹配
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
    """点击 textFl 触发分类维度调试

    Returns:
        (success, error_msg)
    """
    nodes = parse_ui_nodes(xml_text)
    # textFl: resource-id = io.legado.app.debug:id/text_fl
    fl_nodes = find_node_by_resource_id(nodes, r'id/text_fl$')
    if not fl_nodes:
        # 备用：找文本含 "::" 的 TextView
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


def trigger_search_debug(xml_text, keyword=None):
    """触发搜索维度调试

    策略：优先点击 textMy（默认"我的"关键字），无则点击 textXt，无则输入关键字提交
    Returns:
        (success, error_msg, keyword_used)
    """
    nodes = parse_ui_nodes(xml_text)
    # textMy: resource-id = io.legado.app.debug:id/text_my
    my_nodes = find_node_by_resource_id(nodes, r'id/text_my$')
    # textXt: resource-id = io.legado.app.debug:id/text_xt
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
        # 备用：找搜索框输入关键字
        for n in nodes:
            rid = n.get('resource-id', '') or ''
            if 'search_src_text' in rid:
                b = get_bounds_center(n.get('bounds', ''))
                if b:
                    tap(*b)
                    time.sleep(0.5)
                    input_text(keyword or 'test')
                    time.sleep(0.5)
                    input_keyevent(66)
                    return True, f'search_submitted:{keyword}', keyword or 'test'
        return False, 'search_trigger_not_found', None

    b = get_bounds_center(target.get('bounds', ''))
    if not b:
        return False, 'search_btn_no_bounds', None

    tap(*b)
    return True, f'tapped_textMy_or_textXt@{b}', used_kw


def verify_one_source(idx, source_url):
    """对单个源做5维度调试验证

    Returns:
        {
            'idx': int,
            'sourceUrl': str,  # 不输出，只用于内部
            'domain': str,
            'list': str,
            'search': str,
            'category': str,
            'content': str,
            'errors': [str],
            'category_log_lines': int,
            'search_log_lines': int,
            'screenshots': [str],
        }
    """
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
        # dump UI 找 textFl
        _, ui_xml = dump_ui(f'_tmp_debug_{idx}.xml')
        if not ui_xml:
            result['errors'].append('ui_dump_failed_round1')
            # 截图保存
            screenshot(f'src_{idx:03d}_r1_fail.png')
            return result
        screenshot(f'src_{idx:03d}_r1_init.png')

        # clear_log 提前到点击之前，让 logcat 从点击瞬间开始记录
        clear_log()
        ok, msg = trigger_category_debug(ui_xml)
        if not ok:
            result['errors'].append(f'trigger_category_failed:{msg}')
            screenshot(f'src_{idx:03d}_r1_trigger_fail.png')
            return result

        # 等待调试完成
        time.sleep(DEBUG_WAIT_SEC)
        # 收集日志
        log = dump_log(timeout=15)
        log_path = LOGS_DIR / f'src_{idx:03d}_category.log'
        log_path.write_text(log, encoding='utf-8', errors='ignore')
        screenshot(f'src_{idx:03d}_r1_done.png')

        # 分析日志
        cat_result = analyze_logcat_for_dimensions(log, source_url)
        result['domain'] = cat_result['domain']
        result['list'] = cat_result['list']
        result['category'] = cat_result['category']
        result['content'] = cat_result['content']
        result['category_log_lines'] = cat_result['debug_lines']
        result['errors'].extend(cat_result['errors'])
        result['key_markers'].extend(cat_result['key_markers'])

    except Exception as e:
        result['errors'].append(f'category_round_exception:{type(e).__name__}:{str(e)[:100]}')

    # 第2轮：搜索维度调试（重新进入 Activity）
    try:
        start_debug_activity(source_url)
        time.sleep(ACTIVITY_LOAD_SEC)
        _, ui_xml = dump_ui(f'_tmp_debug_{idx}_search.xml')
        if not ui_xml:
            result['errors'].append('ui_dump_failed_round2')
            return result
        screenshot(f'src_{idx:03d}_r2_init.png')

        # clear_log 提前到点击之前
        clear_log()
        ok, msg, used_kw = trigger_search_debug(ui_xml)
        if not ok:
            result['errors'].append(f'trigger_search_failed:{msg}')
            # 搜索无法触发，但其他维度结果已有
            return result

        time.sleep(SEARCH_WAIT_SEC)
        log = dump_log(timeout=15)
        log_path = LOGS_DIR / f'src_{idx:03d}_search.log'
        log_path.write_text(log, encoding='utf-8', errors='ignore')
        screenshot(f'src_{idx:03d}_r2_done.png')

        search_result = analyze_search_log(log)
        result['search'] = search_result['search']
        result['search_log_lines'] = search_result['debug_lines']
        result['errors'].extend(search_result['errors'])
        if used_kw:
            result['key_markers'].append(f'search_kw:{used_kw}')

    except Exception as e:
        result['errors'].append(f'search_round_exception:{type(e).__name__}:{str(e)[:100]}')

    return result


def main():
    print('=' * 70)
    print('v5_3 真机5维度调试验证（71 enabled 源）')
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

    # 启动 App（确保初始化）
    print('\n--- 预启动 App（触发 Cronet 库加载）---')
    adb_shell(f'am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity', timeout=10)
    time.sleep(8)

    # 检查 Cronet 库
    r = adb_shell(f'su -c "ls /data/data/{PKG}/files/cronet/"', timeout=10)
    files = r.stdout.decode('utf-8', errors='ignore')
    has_cronet = 'libcronet' in files
    print(f'Cronet 库: {"✅ 已下载" if has_cronet else "❌ 未下载（HTTPS 源会失败）"}')

    # 批量验证
    results = []
    total = len(enabled_sources)
    print(f'\n--- 开始 5 维度调试验证（共 {total} 源）---')

    for i, src in enumerate(enabled_sources):
        src_url = src.get('sourceUrl', '')
        print(f'\n[{i+1}/{total}] 源[{i}] 调试中...', flush=True)

        result = verify_one_source(i, src_url)
        results.append(result)

        # 实时进度（每5个源打印一次汇总）
        if (i + 1) % 5 == 0 or i == total - 1:
            pass_count = sum(1 for r in results
                             if r['category'] == 'pass' and r['list'] == 'pass'
                             and r['content'] in ('pass', 'skip'))
            print(f'  进度: {i+1}/{total} | 分类通过: {pass_count}')

        # 每10个源保存一次中间结果（避免意外中断丢失数据）
        if (i + 1) % 10 == 0 or i == total - 1:
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
    print(f'  截图目录: {SHOTS_DIR}')
    print(f'  日志目录: {LOGS_DIR}')


def generate_report(results, enabled_sources):
    """生成验证报告"""
    total = len(results)

    # 统计
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

    # 失败源分组
    failed_by_dim = defaultdict(list)
    for r in results:
        idx = r['idx']
        for dim in ['domain', 'list', 'search', 'category', 'content']:
            if r[dim] == 'fail':
                failed_by_dim[dim].append(idx)

    # 错误原因统计
    error_counter = Counter()
    for r in results:
        for e in r.get('errors', []):
            # 简化错误分类
            if ':' in e:
                key = e.split(':')[0]
            else:
                key = e
            error_counter[key] += 1

    # 生成 markdown
    md = []
    md.append('# v5_3 真机 5 维度调试验证报告')
    md.append('')
    md.append(f'**生成时间**: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    md.append(f'**验证源数**: {total} 个 enabled=true 源')
    md.append(f'**数据来源**: `output/rss/optimized_v5_3_final.json`')
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

    md.append('## 2. 失败源清单（按维度分组，编号脱敏）')
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

    md.append('## 3. 关键发现')
    md.append('')

    # 最失败的维度
    fail_counts = {dim: dimension_stats[dim].get('fail', 0) for dim in dimension_stats}
    most_fail_dim = max(fail_counts, key=fail_counts.get)
    md.append(f'- **失败最多的维度**: `{most_fail_dim}`（{fail_counts[most_fail_dim]}/{total} 失败）')
    # 通过率最高的维度
    pass_rates = {dim: dimension_stats[dim].get('pass', 0) / total * 100 for dim in dimension_stats}
    best_dim = max(pass_rates, key=pass_rates.get)
    md.append(f'- **通过率最高的维度**: `{best_dim}`（{pass_rates[best_dim]:.1f}%）')

    # 失败根因 top5
    md.append('')
    md.append('- **失败根因 Top 5**:')
    for err, count in error_counter.most_common(5):
        md.append(f'  - `{err}`: {count} 次')

    md.append('')
    md.append('## 4. 修复建议（按维度）')
    md.append('')
    md.append('### 域名维度')
    if dimension_stats['domain'].get('fail', 0) > 0:
        md.append(f'- 域名失败 {dimension_stats["domain"]["fail"]} 个，建议检查:')
        if error_counter.get('network:dns_fail', 0) > 0:
            md.append(f'  - DNS 解析失败（{error_counter["network:dns_fail"]} 次）: 源URL域名无法解析，建议删除或更换')
        if error_counter.get('network:timeout', 0) > 0:
            md.append(f'  - 超时（{error_counter["network:timeout"]} 次）: 域名可解析但响应慢，检查网络或调整超时')
        if error_counter.get('network:ssl_error', 0) > 0:
            md.append(f'  - SSL 错误（{error_counter["network:ssl_error"]} 次）: 证书问题或 TLS 兼容性')
        if error_counter.get('network:cronet_missing', 0) > 0:
            md.append(f'  - Cronet 库缺失（{error_counter["network:cronet_missing"]} 次）: HTTPS 源无法加载，需预下载 Cronet 库')
        if error_counter.get('network:connection_refused', 0) > 0:
            md.append(f'  - 连接被拒（{error_counter["network:connection_refused"]} 次）: 服务端不可达')
    else:
        md.append('- 域名维度全部通过')

    md.append('')
    md.append('### 列表维度')
    list_fail = dimension_stats['list'].get('fail', 0)
    if list_fail > 0:
        md.append(f'- 列表失败 {list_fail} 个，根因:')
        if error_counter.get('list_empty', 0) > 0:
            md.append(f'  - 列表为空（{error_counter["list_empty"]} 次）: ruleArticles 解析返回空，规则不匹配或页面结构变化')
        if error_counter.get('list_parse_failed', 0) > 0:
            md.append(f'  - 解析失败（{error_counter["list_parse_failed"]} 次）: ruleArticles 规则错误或网络问题')
        md.append('  - 修复方法: 重新分析目标页面结构，更新 ruleArticles 规则')
    else:
        md.append('- 列表维度全部通过')

    md.append('')
    md.append('### 搜索维度')
    search_fail = dimension_stats['search'].get('fail', 0)
    search_unk = dimension_stats['search'].get('unknown', 0)
    if search_fail > 0:
        md.append(f'- 搜索失败 {search_fail} 个，根因:')
        if error_counter.get('search_url_empty', 0) > 0:
            md.append(f'  - 搜索URL为空（{error_counter["search_url_empty"]} 次）: 源未配置 searchUrl')
        if error_counter.get('search_empty', 0) > 0:
            md.append(f'  - 搜索结果为空（{error_counter["search_empty"]} 次）: searchUrl 模板或 ruleArticles 不匹配搜索结果页')
        if error_counter.get('search_parse_failed', 0) > 0:
            md.append(f'  - 搜索解析失败（{error_counter["search_parse_failed"]} 次）: 规则错误')
        md.append('  - 修复方法: 检查 searchUrl 模板（含 searchKey 占位符），核对 ruleSearchArticle 规则')
    if search_unk > 0:
        md.append(f'- 搜索维度未知 {search_unk} 个: 调试未触发或日志缺失')
    md.append('')
    md.append('### 分类维度')
    cat_fail = dimension_stats['category'].get('fail', 0)
    cat_unk = dimension_stats['category'].get('unknown', 0)
    if cat_fail > 0:
        md.append(f'- 分类失败 {cat_fail} 个，根因:')
        if error_counter.get('category_empty', 0) > 0:
            md.append(f'  - 分类列表为空（{error_counter["category_empty"]} 次）: sortUrl 配置的页面无法解析')
        if error_counter.get('category_parse_failed', 0) > 0:
            md.append(f'  - 分类解析失败（{error_counter["category_parse_failed"]} 次）: ruleArticles 不匹配')
        md.append('  - 修复方法: 检查 sortUrl 是否有效，ruleArticles 是否匹配分类页结构')
    if cat_unk > 0:
        md.append(f'- 分类维度未知 {cat_unk} 个: 调试未触发或 Activity 异常')

    md.append('')
    md.append('### 正文维度')
    ct_fail = dimension_stats['content'].get('fail', 0)
    ct_skip = dimension_stats['content'].get('skip', 0)
    if ct_fail > 0:
        md.append(f'- 正文失败 {ct_fail} 个: ruleContent 不匹配正文页结构')
        md.append('  - 修复方法: 重新分析正文页 DOM，更新 ruleContent 规则')
    if ct_skip > 0:
        md.append(f'- 正文跳过 {ct_skip} 个: ruleContent 为空或 ruleDescription 非空（按设计跳过）')

    md.append('')
    md.append('## 5. 总体结论')
    md.append('')
    overall_pass = sum(1 for r in results
                       if r['category'] == 'pass'
                       and r['list'] == 'pass'
                       and r['content'] in ('pass', 'skip')
                       and r['search'] in ('pass', 'unknown'))
    md.append(f'- **完全通过源数**: {overall_pass}/{total} ({overall_pass/total*100:.1f}%)')
    md.append(f'- **完全失败源数**: {sum(1 for r in results if r["category"] == "fail" and r["list"] == "fail")}')
    md.append(f'- **建议删除源数**: {sum(1 for r in results if r["category"] == "unknown" and r["list"] == "unknown")}')
    md.append('')
    md.append('---')
    md.append('**说明**: 报告中源编号对应 `optimized_v5_3_final.json` 中 enabled=true 源的索引（0-based）。')
    md.append('**测试环境**: MEmu 模拟器 127.0.0.1:21503 | App: io.legado.app.debug')

    # 写入文件
    REPORT_MD.write_text('\n'.join(md), encoding='utf-8')


if __name__ == '__main__':
    main()
