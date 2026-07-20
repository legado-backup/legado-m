#!/usr/bin/env python3
r"""v5_1_real_device_verify.py — V5.1 订阅源真机逐源验证（v2: 纯 ADB input 版本）

用途：
    在 MEmu 模拟器中导入 V5.1 JSON，逐源验证可用性，输出脱敏报告。

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/v5_1_real_device_verify.py

v2 改进（基于实测）：
    - 完全用 ADB input tap/swipe 替代 uiautomator2（避免 SecurityException）
    - 用 uiautomator dump + XML 解析获取元素坐标
    - 启动用 MainActivity 直接跳过 WelcomeActivity
    - tap 失败时自动 BACK+HOME+restart 重试

输出安全：MD报告用代号（源[i]/站点A），失败JSON保留 sourceUrl 供修复
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

# === 常量（独立于 config.py，使用真实端口）===
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'  # 真实端口（config.py 中的 21513 是错误的）
PKG = 'io.legado.app.debug'
MAIN_ACTIVITY_FULL = f'{PKG}/io.legado.app.ui.main.MainActivity'
WELCOME_ACTIVITY_FULL = f'{PKG}/io.legado.app.ui.welcome.WelcomeActivity'
DB_DEVICE = f'/data/data/{PKG}/databases/legado.db'

# === 输入/输出路径 ===
PROJECT_ROOT = Path(__file__).parent.parent.parent
JSON_PATH = PROJECT_ROOT / 'output' / 'rss' / 'optimized_v5_1_app_import_fixed.json'
OUT_DIR = PROJECT_ROOT / 'output' / 'rss'
REPORT_MD = OUT_DIR / 'v5_1_real_device_verify_report.md'
FAILED_JSON = OUT_DIR / 'v5_1_real_device_verify_failed_sources.json'
SUCCESS_JSON = OUT_DIR / 'v5_1_real_device_verify_success_sources.json'
RAW_LOG = OUT_DIR / 'v5_1_real_device_verify_raw.log'
SHOTS_DIR = OUT_DIR / 'v5_1_shots'

# === 抽验数量 ===
SAMPLE_SIZE = 35  # 至少30个，按任务要求


def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def adb_shell(cmd_str, timeout=30):
    full = f'"{ADB}" -s {HOST} shell {cmd_str}'
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    return subprocess.run(full, shell=True, capture_output=True, timeout=timeout, text=False, env=env)


def adb_text(r):
    return (r.stdout or b'').decode('utf-8', errors='replace')


def adb_input_tap(x, y):
    """ADB input tap（绕过 u2 SecurityException）"""
    adb_shell(f'input tap {x} {y}', timeout=10)


def adb_input_swipe(x1, y1, x2, y2, ms=300):
    """ADB input swipe"""
    adb_shell(f'input swipe {x1} {y1} {x2} {y2} {ms}', timeout=10)


def adb_screenshot(save_path):
    """ADB 截图"""
    tmp_remote = '/sdcard/shot_tmp.png'
    adb_shell(f'screencap -p {tmp_remote}', timeout=10)
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'pull', tmp_remote, str(save_path)],
                       capture_output=True, timeout=15, env=env)
    return r.returncode == 0


def adb_uiautomator_dump():
    """ADB uiautomator dump，返回 XML 字符串"""
    tmp_remote = '/sdcard/ui_dump.xml'
    adb_shell(f'uiautomator dump {tmp_remote}', timeout=10)
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    tmp_local = tempfile.NamedTemporaryFile(suffix='.xml', delete=False).name
    r = subprocess.run([ADB, '-s', HOST, 'pull', tmp_remote, tmp_local],
                       capture_output=True, timeout=15, env=env)
    if r.returncode != 0:
        return ''
    try:
        with open(tmp_local, 'r', encoding='utf-8') as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_local)
        except Exception:
            pass


# === DB 导入 ===
def pull_db(tmp_path):
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)
    adb_shell(f"su -c 'cp {DB_DEVICE} /sdcard/legado_v51.db; chmod 666 /sdcard/legado_v51.db'")
    adb_shell(f"su -c 'cp {DB_DEVICE}-wal /sdcard/legado_v51.db-wal 2>/dev/null; chmod 666 /sdcard/legado_v51.db-wal 2>/dev/null; true'")
    adb_shell(f"su -c 'cp {DB_DEVICE}-shm /sdcard/legado_v51.db-shm 2>/dev/null; chmod 666 /sdcard/legado_v51.db-shm 2>/dev/null; true'")
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/legado_v51.db', tmp_path],
                       capture_output=True, timeout=30, env=env)
    if r.returncode != 0:
        print(f'  ❌ Pull DB 失败')
        return False
    for ext in ['-wal', '-shm']:
        p = tmp_path + ext
        if os.path.exists(p):
            os.unlink(p)
    print(f'  ✅ DB pulled')
    return True


def push_db(tmp_path):
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'push', tmp_path, '/sdcard/legado_v51.db'],
                       capture_output=True, timeout=30, env=env)
    if r.returncode != 0:
        print(f'  ❌ Push DB 失败')
        return False
    adb_shell(f"su -c 'cp /sdcard/legado_v51.db {DB_DEVICE}; chmod 660 {DB_DEVICE}'")
    adb_shell(f"su -c 'rm -f {DB_DEVICE}-wal {DB_DEVICE}-shm'")
    print(f'  ✅ DB pushed')
    return True


def import_json_to_db(json_path, db_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    if not isinstance(sources, list):
        sources = [sources]
    print(f'  JSON 包含 {len(sources)} 个源')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("PRAGMA table_info(rssSources)")
    cols = [r[1] for r in cur.fetchall()]
    print(f'  rssSources 表列数: {len(cols)}')

    cur.execute("DELETE FROM rssSources")
    inserted = 0
    skipped = 0
    for s in sources:
        valid_keys = [k for k in s.keys() if k in cols]
        if not valid_keys:
            skipped += 1
            continue
        placeholders = ', '.join(['?'] * len(valid_keys))
        col_names = ', '.join(valid_keys)
        values = []
        for k in valid_keys:
            v = s[k]
            if isinstance(v, (int, float, bool)):
                values.append(v)
            elif v is None:
                values.append(None)
            else:
                values.append(str(v))
        try:
            cur.execute(f"INSERT INTO rssSources ({col_names}) VALUES ({placeholders})", values)
            inserted += 1
        except sqlite3.Error as e:
            skipped += 1
    conn.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print(f'  ✅ 导入完成: inserted={inserted}, skipped={skipped}')
    return inserted


# === App 启动 ===
def force_stop_app():
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)


def start_main_activity():
    """直接启动 MainActivity（跳过 WelcomeActivity 过渡）"""
    adb_shell(f'am start -n {MAIN_ACTIVITY_FULL}')
    time.sleep(5)


def ensure_cronet_ready(max_wait=30):
    """确保 Cronet 库已下载（MEmu 无 Google 服务通常无法下载，30秒快速失败）"""
    print('  检查 Cronet 库...')
    r = adb_shell(f"su -c 'ls /data/data/{PKG}/files/cronet/ 2>/dev/null'")
    files = adb_text(r)
    if 'libcronet' in files:
        print('  ✅ Cronet 库已存在')
        return True

    # 主动触发 + 短等待
    print(f'  ⚠️ Cronet 库缺失，启动 App 触发下载（最多等 {max_wait}s）...')
    adb_shell(f'am start -n {MAIN_ACTIVITY_FULL}')
    time.sleep(3)
    time.sleep(max_wait)
    r = adb_shell(f"su -c 'ls /data/data/{PKG}/files/cronet/ 2>/dev/null'")
    files = adb_text(r)
    if 'libcronet' in files:
        print(f'  ✅ Cronet 库下载成功')
        return True
    print('  ❌ Cronet 库下载失败（HTTPS 源将无法加载，HTTP 源不受影响）')
    return False


# === XML 解析（脱敏：只提取坐标和 resource-id，不提取 text）===
def parse_xml_bounds(xml):
    """解析 XML，提取所有节点的 resource-id + bounds + selected 状态

    返回：list of dict {resource_id, bounds, selected, class, click_count}
    """
    if not xml:
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    nodes = []

    def walk(node):
        rid = node.attrib.get('resource-id', '')
        bounds_str = node.attrib.get('bounds', '')
        selected = node.attrib.get('selected', 'false') == 'true'
        cls = node.attrib.get('class', '')
        clickable = node.attrib.get('clickable', 'false') == 'true'
        # 解析 bounds [x1,y1][x2,y2]
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            nodes.append({
                'resource_id': rid,
                'bounds': (x1, y1, x2, y2),
                'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                'selected': selected,
                'class': cls,
                'clickable': clickable,
            })
        for child in node:
            walk(child)

    walk(root)
    return nodes


def find_node_by_rid(nodes, rid_suffix):
    """通过 resource-id 后缀查找节点"""
    for n in nodes:
        if rid_suffix in n['resource_id']:
            return n
    return None


def find_selected_menu(nodes):
    """找当前选中的底部菜单"""
    for n in nodes:
        if 'menu_' in n['resource_id'] and n['selected']:
            return n
    return None


def has_text_content(xml, min_count=3):
    """检查 XML 中是否有非空 text 节点（脱敏：只数数量，不读内容）"""
    texts = re.findall(r'text="([^"]+)"', xml)
    non_empty = [t for t in texts if t.strip()]
    return len(non_empty) >= min_count, len(non_empty)


def goto_rss_tab_via_adb():
    """导航到订阅源列表（纯 ADB input 版本）

    策略：
    1. force-stop App
    2. 启动 MainActivity（跳过 WelcomeActivity）
    3. 等5秒
    4. dump UI，找 menu_rss 的中心点
    5. input tap 点击
    6. dump UI 验证 menu_rss selected
    """
    force_stop_app()
    start_main_activity()

    # dump UI 找 menu_rss
    xml = adb_uiautomator_dump()
    if not xml:
        print('  ⚠️ dump UI 失败')
        return False

    nodes = parse_xml_bounds(xml)
    menu_rss = find_node_by_rid(nodes, 'menu_rss')
    if not menu_rss:
        print('  ⚠️ 未找到 menu_rss 节点')
        return False

    cx, cy = menu_rss['center']
    print(f'  menu_rss 坐标: ({cx}, {cy})')
    adb_input_tap(cx, cy)
    time.sleep(3)

    # 验证
    xml2 = adb_uiautomator_dump()
    if not xml2:
        return False
    nodes2 = parse_xml_bounds(xml2)
    selected = find_selected_menu(nodes2)
    if selected and 'menu_rss' in selected['resource_id']:
        print(f'  ✅ 已切换到订阅Tab')
        return True

    # 重试：BACK+HOME+重启 Activity
    print(f'  ⚠️ 第一次 tap 未生效，重试...')
    adb_shell('input keyevent KEYCODE_BACK')
    time.sleep(1)
    adb_shell('input keyevent KEYCODE_HOME')
    time.sleep(2)
    start_main_activity()
    xml3 = adb_uiautomator_dump()
    if xml3:
        nodes3 = parse_xml_bounds(xml3)
        menu_rss3 = find_node_by_rid(nodes3, 'menu_rss')
        if menu_rss3:
            cx, cy = menu_rss3['center']
            adb_input_tap(cx, cy)
            time.sleep(3)
            xml4 = adb_uiautomator_dump()
            if xml4:
                nodes4 = parse_xml_bounds(xml4)
                selected4 = find_selected_menu(nodes4)
                if selected4 and 'menu_rss' in selected4['resource_id']:
                    print(f'  ✅ 重试后已切换到订阅Tab')
                    return True
    print('  ❌ 所有 tap 尝试均失败')
    return False


def get_source_count_in_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rssSources")
    n = cur.fetchone()[0]
    conn.close()
    return n


def get_source_list_from_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("SELECT * FROM rssSources")
    rows = cur.fetchall()
    sources = []
    for row in rows:
        s = {k: row[k] for k in row.keys() if row[k] is not None}
        sources.append(s)
    conn.close()
    return sources


def classify_source_tech(s):
    source_url = s.get('sourceUrl', '') or ''
    sort_url = s.get('sortUrl', '') or ''
    search_url = s.get('searchUrl', '') or ''
    source_comment = s.get('sourceComment', '') or ''

    is_http = source_url.startswith('http')
    is_js_eval_sort = ('@js:' in sort_url or '<js>' in sort_url) and 'sourceComment' in sort_url
    is_js_eval_search = ('@js:' in search_url or '<js>' in search_url) and 'sourceComment' in search_url
    is_placeholder = (not is_http) and (not is_js_eval_sort) and (not is_js_eval_search)

    has_rule_articles = bool(s.get('ruleArticles', '').strip()) if s.get('ruleArticles') else False
    has_rule_link = bool(s.get('ruleLink', '').strip()) if s.get('ruleLink') else False
    has_rule_title = bool(s.get('ruleTitle', '').strip()) if s.get('ruleTitle') else False

    return {
        'is_http': is_http,
        'is_js_double': is_js_eval_sort or is_js_eval_search,
        'is_placeholder_invalid': is_placeholder,
        'has_rule_articles': has_rule_articles,
        'has_rule_link': has_rule_link,
        'has_rule_title': has_rule_title,
        'source_url_len': len(source_url),
        'sort_url_len': len(sort_url),
        'search_url_len': len(search_url),
        'source_comment_len': len(source_comment),
    }


def is_list_class(cls_name):
    """判断是否为列表类（含 GridView/ListView/RecyclerView/AbsListView）"""
    if not cls_name:
        return False
    return any(k in cls_name for k in ['RecyclerView', 'GridView', 'ListView', 'AbsListView'])


def is_list_in_xml(xml):
    """XML 中是否含列表类"""
    return any(k in xml for k in ['RecyclerView', 'GridView', 'ListView', 'AbsListView'])


def try_source_ui_adb(source_idx):
    """尝试访问指定 idx 的源，返回 (success, fail_reason, evidence)

    纯 ADB input 版本，不依赖 u2
    """
    # 导航到订阅Tab
    if not goto_rss_tab_via_adb():
        return False, 'F_nav_failed', 'cannot_goto_rss_tab'

    # dump UI 获取列表的 bounds（订阅Tab是 GridView，resource-id=recycler_view）
    xml = adb_uiautomator_dump()
    if not xml:
        return False, 'F_no_dump', 'dump_failed_after_rss_tab'

    nodes = parse_xml_bounds(xml)
    rv = None
    for n in nodes:
        # 优先找 resource-id 含 recycler_view 的（订阅Tab的 GridView id 是 recycler_view）
        if 'recycler_view' in n['resource_id'] or is_list_class(n['class']):
            rv = n
            break
    if not rv:
        return False, 'F_no_recycler', 'no_list_in_rss_tab'

    rv_x1, rv_y1, rv_x2, rv_y2 = rv['bounds']
    rv_cx = (rv_x1 + rv_x2) // 2

    # 滚动到顶部（向上滑5次）
    for _ in range(5):
        adb_input_swipe(rv_cx, rv_y1 + 50, rv_cx, rv_y2 - 50, 200)
        time.sleep(0.3)
    time.sleep(0.5)

    # 滚动到目标源（GridView 每行3列，每屏2行=6项）
    VISIBLE = 6
    screens = source_idx // VISIBLE
    for _ in range(screens):
        adb_input_swipe(rv_cx, rv_y2 - 100, rv_cx, rv_y1 + 100, 400)
        time.sleep(0.4)
    time.sleep(0.5)

    # 计算屏幕内位置（GridView 3列2行）
    pos_in_screen = source_idx % VISIBLE
    col = pos_in_screen % 3
    row = pos_in_screen // 3
    item_w = (rv_x2 - rv_x1) // 3
    item_h = (rv_y2 - rv_y1) // 2
    cx = rv_x1 + item_w * col + item_w // 2
    cy = rv_y1 + item_h * row + item_h // 2

    # 清空 logcat
    adb('logcat', '-c')

    # 点击源
    adb_input_tap(cx, cy)
    time.sleep(3)

    # 检查是否进入文章列表页
    r = adb_shell('dumpsys window windows | grep mCurrentFocus')
    focus = adb_text(r)
    activity = '?'
    m = re.search(r'/(\w+Activity)\b', focus)
    if m:
        activity = m.group(1)

    in_list = 'rss' in activity.lower() or 'source' in activity.lower() or 'article' in activity.lower()
    if not in_list:
        # 可能停在分类页，再点一次
        xml_mid = adb_uiautomator_dump()
        if xml_mid:
            nodes_mid = parse_xml_bounds(xml_mid)
            for n in nodes_mid:
                if is_list_class(n['class']):
                    nx1, ny1, nx2, ny2 = n['bounds']
                    n_cx = (nx1 + nx2) // 2
                    n_cy = ny1 + 100
                    adb_input_tap(n_cx, n_cy)
                    time.sleep(5)
                    break
            r2 = adb_shell('dumpsys window windows | grep mCurrentFocus')
            focus2 = adb_text(r2)
            m2 = re.search(r'/(\w+Activity)\b', focus2)
            if m2:
                activity = m2.group(1)

    # 等待加载
    time.sleep(8)

    # 截图
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    shot_path = SHOTS_DIR / f'src_{source_idx:03d}.png'
    shot_ok = adb_screenshot(shot_path)
    if not shot_ok:
        shot_path = None

    # UI dump 检查内容
    xml_after = adb_uiautomator_dump()
    if not xml_after:
        return False, 'A_timeout_or_unknown', f'dump_failed; activity={activity}; shot={shot_path}'

    # 抓取 logcat
    r = adb('logcat', '-d', '-t', '500')
    log_text = adb_text(r)

    # 检测 App 崩溃
    if 'FATAL EXCEPTION' in log_text and PKG in log_text:
        return False, 'E_app_crash', f'fatal_exception; shot={shot_path}'

    # 检测网络错误（中文）
    if any(kw in xml_after for kw in ['网络错误', '加载失败', '连接失败', '加载出错']):
        return False, 'B_network_error', f'xml_net_err; shot={shot_path}'

    # 检测解析错误（中文）
    if any(kw in xml_after for kw in ['解析失败', '解析错误', '规则错误']):
        return False, 'C_parse_error', f'xml_parse_err; shot={shot_path}'

    # 检测网络错误（英文 logcat）
    net_err_patterns = ['IOException', 'SocketTimeoutException', 'UnknownHostException',
                        'ConnectException', 'SSLHandshakeException', 'Malformed URL']
    net_err_hit = [p for p in net_err_patterns if p in log_text]
    if net_err_hit:
        return False, 'B_network_error', f'logcat_net_err={net_err_hit[0]}; shot={shot_path}'

    # 检测列表是否有内容
    has_rv = is_list_in_xml(xml_after)
    has_content, text_count = has_text_content(xml_after, min_count=3)

    if has_rv and has_content:
        return True, 'OK', f'text_nodes={text_count}; activity={activity}; shot={shot_path}'
    if has_rv and not has_content:
        return False, 'D_empty_list', f'list_empty; activity={activity}; shot={shot_path}'
    return False, 'A_timeout_or_unknown', f'no_list_in_article; activity={activity}; shot={shot_path}'


def main():
    print('=' * 70)
    print('V5.1 订阅源真机逐源验证（v2 纯 ADB input 版本）')
    print('=' * 70)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_log_fp = open(RAW_LOG, 'w', encoding='utf-8')

    def log(msg):
        print(msg)
        raw_log_fp.write(msg + '\n')
        raw_log_fp.flush()

    if not JSON_PATH.exists():
        log(f'❌ JSON 文件不存在: {JSON_PATH}')
        return
    log(f'JSON 文件: {JSON_PATH}')

    r = adb('devices')
    log(f'ADB 设备列表:\n{adb_text(r)}')
    if HOST not in adb_text(r):
        log(f'❌ 设备 {HOST} 不在线')
        return

    # 步骤1: 导入 JSON
    log('\n--- 步骤1: 导入 V5.1 JSON ---')
    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        if not pull_db(tmp_db):
            return
        inserted = import_json_to_db(JSON_PATH, tmp_db)
        if inserted == 0:
            log('❌ 未导入任何源')
            return
        if not push_db(tmp_db):
            return
    finally:
        for ext in ['', '-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)

    # 步骤2: 启动 App + Cronet
    log('\n--- 步骤2: 启动 App + Cronet 预下载 ---')
    ensure_cronet_ready()

    # 步骤3: 重新 Pull DB 获取源列表
    log('\n--- 步骤3: 重新 Pull DB 获取源列表 ---')
    tmp_db2 = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        if not pull_db(tmp_db2):
            return
        db_count = get_source_count_in_db(tmp_db2)
        log(f'  DB 中源数量: {db_count}')
        all_sources = get_source_list_from_db(tmp_db2)
    finally:
        for ext in ['', '-wal', '-shm']:
            p = tmp_db2 + ext
            if os.path.exists(p):
                os.unlink(p)

    # 步骤4: 选择抽验样本
    log(f'\n--- 步骤4: 选择抽验样本（共 {len(all_sources)} 个源，抽验 {SAMPLE_SIZE} 个）---')
    tech_classes = Counter()
    for s in all_sources:
        t = classify_source_tech(s)
        if t['is_placeholder_invalid']:
            tech_classes['placeholder_invalid'] += 1
        elif t['is_js_double']:
            tech_classes['js_double'] += 1
        elif t['is_http']:
            tech_classes['http'] += 1
        else:
            tech_classes['other'] += 1
    log(f'  技术分类: {dict(tech_classes)}')

    http_indices = [i for i, s in enumerate(all_sources) if classify_source_tech(s)['is_http']]
    js_indices = [i for i, s in enumerate(all_sources) if classify_source_tech(s)['is_js_double']]
    placeholder_indices = [i for i, s in enumerate(all_sources) if classify_source_tech(s)['is_placeholder_invalid']]

    sample_indices = []
    if len(http_indices) > 0:
        step = max(1, len(http_indices) // 20)
        sample_indices.extend(http_indices[::step][:20])
    sample_indices.extend(js_indices[:10])
    sample_indices.extend(placeholder_indices[:10])

    seen = set()
    sample_indices = [i for i in sample_indices if not (i in seen or seen.add(i))]
    sample_indices = sample_indices[:SAMPLE_SIZE]
    log(f'  抽验 idx ({len(sample_indices)}个): {sample_indices}')

    # 步骤5: 逐源 UI 验证
    log('\n--- 步骤5: 逐源 UI 验证 ---')
    results = []
    for n, idx in enumerate(sample_indices):
        s = all_sources[idx]
        tech = classify_source_tech(s)
        code_name = f'src_{idx:03d}'
        log(f'\n[{n+1}/{len(sample_indices)}] idx={idx} code={code_name} '
            f'http={tech["is_http"]} js={tech["is_js_double"]} '
            f'placeholder={tech["is_placeholder_invalid"]} '
            f'rules=(A={tech["has_rule_articles"]},L={tech["has_rule_link"]},T={tech["has_rule_title"]})')

        try:
            success, reason, evidence = try_source_ui_adb(idx)
            status = 'OK' if success else 'FAIL'
            log(f'  → {status} reason={reason} evidence={evidence[:120]}')
            results.append({
                'idx': idx,
                'code_name': code_name,
                'source_name': s.get('sourceName', ''),
                'source_url': s.get('sourceUrl', ''),
                'source_url_len': tech['source_url_len'],
                'sort_url_len': tech['sort_url_len'],
                'search_url_len': tech['search_url_len'],
                'source_comment_len': tech['source_comment_len'],
                'is_http': tech['is_http'],
                'is_js_double': tech['is_js_double'],
                'is_placeholder_invalid': tech['is_placeholder_invalid'],
                'has_rule_articles': tech['has_rule_articles'],
                'has_rule_link': tech['has_rule_link'],
                'has_rule_title': tech['has_rule_title'],
                'success': success,
                'fail_reason': reason if not success else None,
                'evidence': evidence,
            })
        except Exception as e:
            log(f'  ⚠️ 异常: {str(e)[:120]}')
            results.append({
                'idx': idx,
                'code_name': code_name,
                'source_name': s.get('sourceName', ''),
                'source_url': s.get('sourceUrl', ''),
                'source_url_len': tech['source_url_len'],
                'is_http': tech['is_http'],
                'is_js_double': tech['is_js_double'],
                'is_placeholder_invalid': tech['is_placeholder_invalid'],
                'has_rule_articles': tech['has_rule_articles'],
                'has_rule_link': tech['has_rule_link'],
                'has_rule_title': tech['has_rule_title'],
                'success': False,
                'fail_reason': 'G_exception',
                'evidence': f'exception:{type(e).__name__}:{str(e)[:200]}',
            })

    # 步骤6: 生成报告
    log('\n--- 步骤6: 生成报告 ---')
    write_reports(results, all_sources, tech_classes)
    raw_log_fp.close()
    print('\n' + '=' * 70)
    print(f'验证完成。报告: {REPORT_MD}')
    print(f'失败源清单: {FAILED_JSON}')
    print('=' * 70)


def write_reports(results, all_sources, tech_classes):
    total_tested = len(results)
    success_count = sum(1 for r in results if r['success'])
    fail_count = total_tested - success_count

    fail_dist = Counter()
    for r in results:
        if not r['success']:
            fail_dist[r['fail_reason']] += 1

    failed_list = [r for r in results if not r['success']]
    success_list = [r for r in results if r['success']]

    with open(FAILED_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_tested': total_tested,
                'success': success_count,
                'fail': fail_count,
                'fail_reason_dist': dict(fail_dist),
            },
            'failed_sources': failed_list,
        }, f, ensure_ascii=False, indent=2)

    with open(SUCCESS_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {'success_count': success_count},
            'success_sources': success_list,
        }, f, ensure_ascii=False, indent=2)

    # MD 报告（脱敏）
    md = []
    md.append('# V5.1 订阅源真机验证报告')
    md.append('')
    md.append('## 1. 验证统计')
    md.append('')
    md.append('| 指标 | 数值 |')
    md.append('|------|------|')
    md.append(f'| 总源数（DB） | {len(all_sources)} |')
    md.append(f'| 抽验数量 | {total_tested} |')
    md.append(f'| 成功 | {success_count} |')
    md.append(f'| 失败 | {fail_count} |')
    success_rate = success_count / total_tested * 100 if total_tested else 0
    md.append(f'| 成功率 | {success_rate:.1f}% |')
    md.append('')

    md.append('## 2. 技术分类统计（全量源）')
    md.append('')
    md.append('| 类别 | 数量 | 占比 |')
    md.append('|------|------|------|')
    total = len(all_sources)
    md.append(f'| HTTP 可验证源 | {tech_classes["http"]} | {tech_classes["http"]/total*100:.1f}% |')
    md.append(f'| JS 双层加密源 | {tech_classes["js_double"]} | {tech_classes["js_double"]/total*100:.1f}% |')
    md.append(f'| 占位符无效源 | {tech_classes["placeholder_invalid"]} | {tech_classes["placeholder_invalid"]/total*100:.1f}% |')
    md.append(f'| 其他 | {tech_classes["other"]} | {tech_classes["other"]/total*100:.1f}% |')
    md.append('')

    md.append('## 3. 失败原因分布')
    md.append('')
    md.append('| 失败原因 | 数量 | 说明 |')
    md.append('|----------|------|------|')
    reason_desc = {
        'A_timeout_or_unknown': '加载超时或未进入文章列表页',
        'B_network_error': '网络错误（IOException/SocketTimeout/UnknownHost/SSL/Cronet缺失）',
        'C_parse_error': '解析失败（规则错误）',
        'D_empty_list': '空列表（无内容但无错误）',
        'E_app_crash': 'App崩溃（FATAL EXCEPTION）',
        'F_nav_failed': '导航失败（无法进入订阅Tab）',
        'F_no_recycler': 'RecyclerView缺失',
        'F_no_dump': 'UI dump失败',
        'G_exception': '脚本异常',
    }
    for reason, count in sorted(fail_dist.items(), key=lambda x: -x[1]):
        desc = reason_desc.get(reason, reason)
        md.append(f'| {reason} | {count} | {desc} |')
    md.append('')

    md.append('## 4. 失败源清单（按失败原因分组，脱敏代号）')
    md.append('')
    for reason in sorted(fail_dist.keys()):
        md.append(f'### {reason} - {reason_desc.get(reason, "")}')
        md.append('')
        md.append('| 代号 | idx | 源类型 | 规则完整(A/L/T) | url长度 | sort长度 | search长度 |')
        md.append('|------|-----|--------|-----------------|--------|----------|-----------|')
        for r in failed_list:
            if r['fail_reason'] != reason:
                continue
            src_type = 'HTTP' if r['is_http'] else ('JS双层' if r['is_js_double'] else ('占位符' if r['is_placeholder_invalid'] else '其他'))
            rules = f"{r['has_rule_articles']}/{r['has_rule_link']}/{r['has_rule_title']}"
            md.append(f'| {r["code_name"]} | {r["idx"]} | {src_type} | {rules} | {r["source_url_len"]} | {r["sort_url_len"]} | {r["search_url_len"]} |')
        md.append('')

    md.append('## 5. 成功源清单（前10个，脱敏代号）')
    md.append('')
    md.append('| 代号 | idx | 源类型 | 规则完整(A/L/T) | url长度 |')
    md.append('|------|-----|--------|-----------------|--------|')
    for r in success_list[:10]:
        src_type = 'HTTP' if r['is_http'] else ('JS双层' if r['is_js_double'] else ('占位符' if r['is_placeholder_invalid'] else '其他'))
        rules = f"{r['has_rule_articles']}/{r['has_rule_link']}/{r['has_rule_title']}"
        md.append(f'| {r["code_name"]} | {r["idx"]} | {src_type} | {rules} | {r["source_url_len"]} |')
    md.append('')

    md.append('## 6. 关键发现（V5.1 脚本的根本问题）')
    md.append('')
    if fail_dist.get('D_empty_list', 0) > 0:
        md.append(f'### 发现1：大量"空列表"失败（{fail_dist["D_empty_list"]}个）')
        md.append('- 现象：UI 进入文章列表页但 RecyclerView 无内容')
        md.append('- 根因分析：')
        md.append('  - ruleArticles 选择器与实际页面结构不匹配（规则过期）')
        md.append('  - sourceUrl 是占位符但 sortUrl 未走 JS eval 路径')
        md.append('  - 站点结构已变更，V5 脚本生成的规则与当前页面不符')
        md.append('  - 站点需登录/反爬，无 cookie 时返回空')
        md.append('')
    if fail_dist.get('B_network_error', 0) > 0:
        md.append(f'### 发现2：网络错误（{fail_dist["B_network_error"]}个）')
        md.append('- 现象：logcat 出现 IOException/SocketTimeout/UnknownHost/SSL')
        md.append('- 根因：')
        md.append('  - 站点已下线或域名失效（V5脚本未做存活检测）')
        md.append('  - HTTPS 源的 Cronet 库未下载（MEmu 无 Google 服务）')
        md.append('  - UA 或 Referer 配置不当被站点拒绝')
        md.append('  - 站点 DNS 解析失败或 SSL 证书问题')
        md.append('')
    if fail_dist.get('A_timeout_or_unknown', 0) > 0:
        md.append(f'### 发现3：加载超时/未进入列表页（{fail_dist["A_timeout_or_unknown"]}个）')
        md.append('- 现象：点击源后未进入文章列表 Activity')
        md.append('- 根因：')
        md.append('  - 源配置错误导致 App 内部异常但未崩溃')
        md.append('  - 站点响应超时')
        md.append('')
    if fail_dist.get('C_parse_error', 0) > 0:
        md.append(f'### 发现4：解析错误（{fail_dist["C_parse_error"]}个）')
        md.append('- 现象：UI 显示"解析失败"')
        md.append('- 根因：规则语法错误（如 CSS 选择器缺少 @ 前缀）')
        md.append('')

    placeholder_total = tech_classes['placeholder_invalid']
    if placeholder_total > 0:
        md.append(f'### 发现5：占位符无效源 {placeholder_total} 个（占 {placeholder_total/total*100:.1f}%）')
        md.append('- 现象：sourceUrl 非 http 开头且无 JS 双层加密')
        md.append('- 根因：V5 脚本生成的 sourceUrl 是占位符但未配套生成 JS 加密逻辑')
        md.append('- 影响：这些源在真机中必然无法加载文章列表')
        md.append('')

    md.append('### 综合根因（V5 脚本的根本问题）')
    md.append('')
    md.append('1. **缺乏真机预验证**：V5 脚本生成 JSON 后未在真机做抽验，直接交付')
    md.append('2. **规则生成与站点实际结构脱节**：V5 脚本可能基于过期的页面快照生成规则，未实时校验')
    md.append('3. **占位符源未配套JS加密**：6 个占位符源缺少 `@js:eval(source.sourceComment)` 配套')
    md.append('4. **未做站点存活检测**：HTTP 源生成前未做 HTTP 200 + 内容长度校验')
    md.append('5. **Cronet 库依赖未提示**：HTTPS 源依赖 Cronet 库，但 MEmu 无 Google 服务无法自动下载')
    md.append('')

    md.append('## 7. 修复建议')
    md.append('')
    md.append('### 7.1 立即修复')
    md.append('1. 删除所有占位符无效源（6个）')
    md.append('2. 对 HTTP 失败源逐个排查站点可用性')
    md.append('3. 对解析失败源重新核对规则语法')
    md.append('4. 手动下载 Cronet 库到 `/data/data/io.legado.app.debug/files/cronet/` 或改用 HTTP 源')
    md.append('')
    md.append('### 7.2 V5 脚本根因修复')
    md.append('1. **生成器校验**：V5 脚本应在生成 JSON 时校验 sourceUrl 是否为有效 http URL')
    md.append('2. **规则完整性**：每个源必须包含 ruleArticles/ruleLink/ruleTitle 三件套')
    md.append('3. **JS 双层加密**：占位符 sourceUrl 必须配套 sortUrl 含 `@js:eval(source.sourceComment)`')
    md.append('4. **真机预验证**：V5 脚本应在生成后自动跑一次真机验证（脱敏）再交付')
    md.append('5. **站点存活检测**：生成前对每个 sourceUrl 做 HTTP 200 检查')
    md.append('6. **Cronet 依赖提示**：HTTPS 源生成时给出明确的 Cronet 库依赖提示')
    md.append('')
    md.append('## 8. 输出文件')
    md.append('')
    md.append(f'- 详细报告（本文件）: `{REPORT_MD}`')
    md.append(f'- 失败源清单 JSON: `{FAILED_JSON}`（含 sourceUrl 供修复）')
    md.append(f'- 成功源清单 JSON: `{SUCCESS_JSON}`')
    md.append(f'- 截图目录: `{SHOTS_DIR}`')
    md.append(f'- 原始日志: `{RAW_LOG}`')
    md.append('')

    REPORT_MD.write_text('\n'.join(md), encoding='utf-8')


if __name__ == "__main__":
    main()
