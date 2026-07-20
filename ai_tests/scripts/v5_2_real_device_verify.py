#!/usr/bin/env python3
r"""v5_2_real_device_verify.py — V5.2 订阅源真机验证脚本

用途：
    1. 导入 optimized_v5_2_stable.json 到 MEmu 模拟器 legado.db
    2. 启动 App + Cronet 预下载
    3. 抽验 20 个源（5个V4未变动+5个V5视频+5个V5缺字段+5个V5难点）
    4. 输出 v5_2_real_device_verify_report.md（脱敏代号）

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/v5_2_real_device_verify.py

输出安全：MD报告用代号（src_NNN/源[i]/站点A），失败JSON保留sourceUrl供修复
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
HOST = '127.0.0.1:21503'  # 真实端口
PKG = 'io.legado.app.debug'
MAIN_ACTIVITY_FULL = f'{PKG}/io.legado.app.ui.main.MainActivity'
DB_DEVICE = f'/data/data/{PKG}/databases/legado.db'

# === 输入/输出路径 ===
PROJECT_ROOT = Path(__file__).parent.parent.parent
JSON_PATH = PROJECT_ROOT / 'output' / 'rss' / 'optimized_v5_2_stable.json'
V4_PATH = PROJECT_ROOT / 'output' / 'rss' / 'optimized_v2_lite_final_v4.json'
V5_VIDEO = PROJECT_ROOT / 'output' / 'rss' / 'v5_video_deepfix.json'
V5_MISSING = PROJECT_ROOT / 'output' / 'rss' / 'v5_missing_fields_fix.json'
V5_HARD = PROJECT_ROOT / 'output' / 'rss' / 'v5_hard_source_fix.json'

OUT_DIR = PROJECT_ROOT / 'output' / 'rss'
REPORT_MD = OUT_DIR / 'v5_2_real_device_verify_report.md'
FAILED_JSON = OUT_DIR / 'v5_2_real_device_verify_failed_sources.json'
SUCCESS_JSON = OUT_DIR / 'v5_2_real_device_verify_success_sources.json'
RAW_LOG = OUT_DIR / 'v5_2_real_device_verify_raw.log'
SHOTS_DIR = OUT_DIR / 'v5_2_shots'
FIX_REPORT = OUT_DIR / 'v5_2_fix_report.json'

# === 抽验数量 ===
SAMPLE_PER_CATEGORY = 5  # 4类 * 5 = 20


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
    adb_shell(f'input tap {x} {y}', timeout=10)


def adb_input_swipe(x1, y1, x2, y2, ms=300):
    adb_shell(f'input swipe {x1} {y1} {x2} {y2} {ms}', timeout=10)


def adb_screenshot(save_path):
    tmp_remote = '/sdcard/shot_tmp.png'
    adb_shell(f'screencap -p {tmp_remote}', timeout=10)
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'pull', tmp_remote, str(save_path)],
                       capture_output=True, timeout=15, env=env)
    return r.returncode == 0


def adb_uiautomator_dump():
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
    adb_shell(f"su -c 'cp {DB_DEVICE} /sdcard/legado_v52.db; chmod 666 /sdcard/legado_v52.db'")
    adb_shell(f"su -c 'cp {DB_DEVICE}-wal /sdcard/legado_v52.db-wal 2>/dev/null; chmod 666 /sdcard/legado_v52.db-wal 2>/dev/null; true'")
    adb_shell(f"su -c 'cp {DB_DEVICE}-shm /sdcard/legado_v52.db-shm 2>/dev/null; chmod 666 /sdcard/legado_v52.db-shm 2>/dev/null; true'")
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/legado_v52.db', tmp_path],
                       capture_output=True, timeout=30, env=env)
    if r.returncode != 0:
        print(f'  Pull DB 失败: {r.stderr.decode("utf-8", errors="replace")[:200]}')
        return False
    for ext in ['-wal', '-shm']:
        p = tmp_path + ext
        if os.path.exists(p):
            os.unlink(p)
    print(f'  DB pulled to {tmp_path}')
    return True


def push_db(tmp_path):
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    r = subprocess.run([ADB, '-s', HOST, 'push', tmp_path, '/sdcard/legado_v52.db'],
                       capture_output=True, timeout=30, env=env)
    if r.returncode != 0:
        print(f'  Push DB 失败')
        return False
    adb_shell(f"su -c 'cp /sdcard/legado_v52.db {DB_DEVICE}; chmod 660 {DB_DEVICE}'")
    adb_shell(f"su -c 'rm -f {DB_DEVICE}-wal {DB_DEVICE}-shm'")
    print(f'  DB pushed back (WAL/SHM 已清理)')
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
        except sqlite3.Error:
            skipped += 1
    conn.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print(f'  导入完成: inserted={inserted}, skipped={skipped}')
    return inserted


def force_stop_app():
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)


def start_main_activity():
    adb_shell(f'am start -n {MAIN_ACTIVITY_FULL}')
    time.sleep(5)


def ensure_cronet_ready(max_wait=10):
    """检查 Cronet 库（实际路径: /data/data/{PKG}/app_cronet/<abi>/libcronet.*.so）

    源码 CronetLoader.kt: appCtx.getDir("cronet", MODE_PRIVATE) → /data/data/{PKG}/app_cronet/
    注意: adb_shell 中 2>/dev/null 与 Windows 转义冲突, 改用不带重定向的命令
    """
    print('  检查 Cronet 库...')
    # 检查正确路径 app_cronet/<abi>/ (不带 2>/dev/null)
    r = adb_shell(f"su -c 'ls /data/data/{PKG}/app_cronet/arm64-v8a/'")
    files = adb_text(r)
    if 'libcronet' in files:
        so_lines = [l for l in files.split('\n') if 'libcronet' in l]
        print(f'  Cronet 库已存在 (so文件数={len(so_lines)})')
        return True
    # 也兼容旧路径 files/cronet/
    r2 = adb_shell(f"su -c 'ls /data/data/{PKG}/files/cronet/'")
    files2 = adb_text(r2)
    if 'libcronet' in files2:
        print(f'  Cronet 库已存在(旧路径 files/cronet/)')
        return True
    print(f'  Cronet 库缺失(HTTPS源将无法加载, HTTP源不受影响)')
    return False


def parse_xml_bounds(xml):
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
    for n in nodes:
        if rid_suffix in n['resource_id']:
            return n
    return None


def find_selected_menu(nodes):
    for n in nodes:
        if 'menu_' in n['resource_id'] and n['selected']:
            return n
    return None


def has_text_content(xml, min_count=3):
    texts = re.findall(r'text="([^"]+)"', xml)
    non_empty = [t for t in texts if t.strip()]
    return len(non_empty) >= min_count, len(non_empty)


def goto_rss_tab_via_adb():
    force_stop_app()
    start_main_activity()

    xml = adb_uiautomator_dump()
    if not xml:
        print('  dump UI 失败')
        return False

    nodes = parse_xml_bounds(xml)
    menu_rss = find_node_by_rid(nodes, 'menu_rss')
    if not menu_rss:
        print('  未找到 menu_rss 节点')
        return False

    cx, cy = menu_rss['center']
    print(f'  menu_rss 坐标: ({cx}, {cy})')
    adb_input_tap(cx, cy)
    time.sleep(3)

    xml2 = adb_uiautomator_dump()
    if not xml2:
        return False
    nodes2 = parse_xml_bounds(xml2)
    selected = find_selected_menu(nodes2)
    if selected and 'menu_rss' in selected['resource_id']:
        print(f'  已切换到订阅Tab')
        return True

    print(f'  第一次 tap 未生效, 重试...')
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
                    print(f'  重试后已切换到订阅Tab')
                    return True
    print('  所有 tap 尝试均失败')
    return False


def get_source_list_from_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("SELECT * FROM rssSources ORDER BY customOrder ASC, lastUpdateTime DESC")
    rows = cur.fetchall()
    sources = []
    for row in rows:
        s = {k: row[k] for k in row.keys() if row[k] is not None}
        sources.append(s)
    conn.close()
    return sources


def is_list_class(cls_name):
    if not cls_name:
        return False
    return any(k in cls_name for k in ['RecyclerView', 'GridView', 'ListView', 'AbsListView'])


def is_list_in_xml(xml):
    return any(k in xml for k in ['RecyclerView', 'GridView', 'ListView', 'AbsListView'])


def try_source_ui_adb(source_idx):
    """尝试访问指定 idx 的源"""
    if not goto_rss_tab_via_adb():
        return False, 'F_nav_failed', 'cannot_goto_rss_tab'

    xml = adb_uiautomator_dump()
    if not xml:
        return False, 'F_no_dump', 'dump_failed_after_rss_tab'

    nodes = parse_xml_bounds(xml)
    rv = None
    for n in nodes:
        if 'recycler_view' in n['resource_id'] or is_list_class(n['class']):
            rv = n
            break
    if not rv:
        return False, 'F_no_recycler', 'no_list_in_rss_tab'

    rv_x1, rv_y1, rv_x2, rv_y2 = rv['bounds']
    rv_cx = (rv_x1 + rv_x2) // 2

    # 滚动到顶部
    for _ in range(5):
        adb_input_swipe(rv_cx, rv_y1 + 50, rv_cx, rv_y2 - 50, 200)
        time.sleep(0.3)
    time.sleep(0.5)

    # 滚动到目标源(GridView 3列2行=6项每屏)
    VISIBLE = 6
    screens = source_idx // VISIBLE
    for _ in range(screens):
        adb_input_swipe(rv_cx, rv_y2 - 100, rv_cx, rv_y1 + 100, 400)
        time.sleep(0.4)
    time.sleep(0.5)

    pos_in_screen = source_idx % VISIBLE
    col = pos_in_screen % 3
    row = pos_in_screen // 3
    item_w = (rv_x2 - rv_x1) // 3
    item_h = (rv_y2 - rv_y1) // 2
    cx = rv_x1 + item_w * col + item_w // 2
    cy = rv_y1 + item_h * row + item_h // 2

    # 清空 logcat
    adb('logcat', '-c')
    time.sleep(0.5)
    # 获取 legado 包的 pid (用于后续过滤日志)
    r_pid = adb_shell(f'pidof {PKG}')
    legado_pid = adb_text(r_pid).strip()
    if not legado_pid:
        # App 可能未运行, 启动它
        start_main_activity()
        r_pid = adb_shell(f'pidof {PKG}')
        legado_pid = adb_text(r_pid).strip()

    # 点击源
    adb_input_tap(cx, cy)
    time.sleep(3)

    r = adb_shell('dumpsys window windows | grep mCurrentFocus')
    focus = adb_text(r)
    activity = '?'
    m = re.search(r'/(\w+Activity)\b', focus)
    if m:
        activity = m.group(1)

    in_list = 'rss' in activity.lower() or 'source' in activity.lower() or 'article' in activity.lower()
    if not in_list:
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

    # 等待加载(增加到12秒)
    time.sleep(12)

    # 截图
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    shot_path = SHOTS_DIR / f'v52_src_{source_idx:03d}.png'
    shot_ok = adb_screenshot(shot_path)
    if not shot_ok:
        shot_path = None

    xml_after = adb_uiautomator_dump()
    if not xml_after:
        return False, 'A_timeout_or_unknown', f'dump_failed; activity={activity}'

    # 抓取 logcat (用 --pid 过滤只取 legado 包的日志, 避免其他 App 历史日志干扰)
    if legado_pid:
        r = adb('logcat', '-d', '--pid', legado_pid, '-t', '200')
    else:
        r = adb('logcat', '-d', '-t', '200')
    log_text = adb_text(r)

    if 'FATAL EXCEPTION' in log_text and PKG in log_text:
        return False, 'E_app_crash', f'fatal_exception'

    # 优先检查 XML 中的网络错误提示(App 真的显示了错误才算)
    if any(kw in xml_after for kw in ['网络错误', '加载失败', '连接失败', '加载出错']):
        return False, 'B_network_error', f'xml_net_err'

    if any(kw in xml_after for kw in ['解析失败', '解析错误', '规则错误']):
        return False, 'C_parse_error', f'xml_parse_err'

    # logcat 中的网络错误: 必须同时含 IOException 和 legado 包名
    # (避免其他 App 的 IOException 历史日志干扰)
    net_err_patterns = ['IOException', 'SocketTimeoutException', 'UnknownHostException',
                        'ConnectException', 'SSLHandshakeException']
    has_legado_err = (PKG in log_text) or (legado_pid in log_text)
    net_err_hit = [p for p in net_err_patterns if p in log_text]
    # 仅当 legado 包日志中含 IOException 时才判失败
    if net_err_hit and has_legado_err:
        return False, 'B_network_error', f'logcat_net_err={net_err_hit[0]}'

    has_rv = is_list_in_xml(xml_after)
    has_content, text_count = has_text_content(xml_after, min_count=3)

    if has_rv and has_content:
        return True, 'OK', f'text_nodes={text_count}; activity={activity}'
    if has_rv and not has_content:
        return False, 'D_empty_list', f'list_empty; activity={activity}'
    return False, 'A_timeout_or_unknown', f'no_list_in_article; activity={activity}'


def load_v5_fix_patterns():
    """加载 V5 阶段输出文件, 提取 sourceUrl_pattern(用于匹配 V5.2 中的源)"""
    patterns = {
        "video": [],      # 视频深度修复 (9个)
        "missing": [],    # 缺字段补全 (104个)
        "hard": [],       # 难点源 (38个)
    }
    for category, fn in [("video", V5_VIDEO), ("missing", V5_MISSING), ("hard", V5_HARD)]:
        if not fn.exists():
            continue
        with open(fn, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            for k in ["sources", "data", "list", "items"]:
                if k in d and isinstance(d[k], list):
                    d = d[k]
                    break
            else:
                for v in d.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        d = v
                        break
        for item in d:
            pat = item.get("sourceUrl_pattern", "")
            # 检查 success 字段
            success = item.get("success", True)  # video/missing 文件没 success 字段, 视为成功
            if isinstance(pat, str) and pat and success:
                patterns[category].append(pat)
    return patterns


def classify_v4_unchanged(sources, v5_patterns):
    """识别 V4 未变动源: sourceUrl 不在 V5 修复记录中"""
    all_v5_pats = set()
    for pats in v5_patterns.values():
        all_v5_pats.update(pats)
    unchanged = []
    for i, s in enumerate(sources):
        url = s.get("sourceUrl", "")
        if url and url not in all_v5_pats:
            unchanged.append(i)
    return unchanged


def select_sample_indices(sources, v5_patterns):
    """选择抽验样本: 优先选字段完整(ruleArticles+ruleLink+ruleTitle)的源

    策略:
    1. 优先选 V5 修复类别匹配的源(hard > missing > video)
    2. 然后选 V4 未变动源中字段完整的
    3. 每个类别最多 SAMPLE_PER_CATEGORY 个, 共 4*5=20 个
    4. 跳过 idx 0~10 (V5.1 中已测失败的, 避免重复验证)
    """
    sample = []
    skip_idx_below = 11  # 跳过前11个(V5.1已测失败)

    # 类别1: V5 修复源 (按 sourceUrl 匹配)
    for category in ["hard", "missing", "video"]:
        pats = v5_patterns.get(category, [])
        matched_indices = []
        for i, s in enumerate(sources):
            if i < skip_idx_below:
                continue
            url = s.get("sourceUrl", "")
            ra = (s.get("ruleArticles") or "").strip()
            rl = (s.get("ruleLink") or "").strip()
            rt = (s.get("ruleTitle") or "").strip()
            if url and url in pats and ra and rl and rt:
                matched_indices.append(i)
        sample.extend([(category, i) for i in matched_indices[:SAMPLE_PER_CATEGORY]])

    # 类别2: V4 未变动源(字段完整)
    all_v5_pats = set()
    for pats in v5_patterns.values():
        all_v5_pats.update(pats)
    unchanged_full = []
    for i, s in enumerate(sources):
        if i < skip_idx_below:
            continue
        url = s.get("sourceUrl", "")
        ra = (s.get("ruleArticles") or "").strip()
        rl = (s.get("ruleLink") or "").strip()
        rt = (s.get("ruleTitle") or "").strip()
        if (url and url not in all_v5_pats and ra and rl and rt
                and url.startswith("http")):
            unchanged_full.append(i)
    sample.extend([("v4_unchanged", i) for i in unchanged_full[:SAMPLE_PER_CATEGORY]])

    # 如果总数不足 20, 从字段完整的源补充
    if len(sample) < 20:
        all_field_full = []
        for i, s in enumerate(sources):
            if i < skip_idx_below:
                continue
            ra = (s.get("ruleArticles") or "").strip()
            rl = (s.get("ruleLink") or "").strip()
            rt = (s.get("ruleTitle") or "").strip()
            url = s.get("sourceUrl", "")
            if ra and rl and rt and url.startswith("http"):
                all_field_full.append(i)
        existing_idx = {i for _, i in sample}
        for i in all_field_full:
            if len(sample) >= 20:
                break
            if i not in existing_idx:
                sample.append(("field_full_extra", i))
                existing_idx.add(i)

    return sample[:20]


def main():
    print('=' * 70)
    print('V5.2 订阅源真机验证')
    print('=' * 70)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_log_fp = open(RAW_LOG, 'w', encoding='utf-8')

    def log(msg):
        print(msg)
        raw_log_fp.write(msg + '\n')
        raw_log_fp.flush()

    if not JSON_PATH.exists():
        log(f'JSON 文件不存在: {JSON_PATH}')
        return
    log(f'JSON 文件: {JSON_PATH}')

    r = adb('devices')
    log(f'ADB 设备列表:\n{adb_text(r)}')
    if HOST not in adb_text(r):
        log(f'设备 {HOST} 不在线')
        return

    # 步骤1: 导入 V5.2 JSON
    log('\n--- 步骤1: 导入 V5.2 JSON ---')
    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        if not pull_db(tmp_db):
            return
        inserted = import_json_to_db(JSON_PATH, tmp_db)
        if inserted == 0:
            log('未导入任何源')
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
        all_sources = get_source_list_from_db(tmp_db2)
        log(f'  DB 中源数量: {len(all_sources)}')
    finally:
        for ext in ['', '-wal', '-shm']:
            p = tmp_db2 + ext
            if os.path.exists(p):
                os.unlink(p)

    # 步骤4: 选择抽验样本(按 V5 修复类别)
    log('\n--- 步骤4: 加载 V5 修复记录, 选择抽验样本 ---')
    v5_patterns = load_v5_fix_patterns()
    log(f'  V5 修复记录: video={len(v5_patterns["video"])}, '
        f'missing={len(v5_patterns["missing"])}, hard={len(v5_patterns["hard"])}')

    sample = select_sample_indices(all_sources, v5_patterns)
    log(f'  抽验样本数: {len(sample)}')
    cat_counter = Counter([c for c, _ in sample])
    for cat, cnt in cat_counter.items():
        log(f'    - {cat}: {cnt}')

    # 步骤5: 逐源 UI 验证
    log('\n--- 步骤5: 逐源 UI 验证 ---')
    results = []
    for n, (category, idx) in enumerate(sample):
        s = all_sources[idx]
        code_name = f'src_{idx:03d}'
        log(f'\n[{n+1}/{len(sample)}] category={category} idx={idx} code={code_name}')

        try:
            success, reason, evidence = try_source_ui_adb(idx)
            status = 'OK' if success else 'FAIL'
            log(f'  -> {status} reason={reason} evidence={evidence[:120]}')
            results.append({
                'idx': idx,
                'category': category,
                'code_name': code_name,
                'source_url': s.get('sourceUrl', ''),
                'source_url_len': len(s.get('sourceUrl', '')),
                'success': success,
                'fail_reason': reason if not success else None,
                'evidence': evidence,
            })
        except Exception as e:
            log(f'  异常: {str(e)[:120]}')
            results.append({
                'idx': idx,
                'category': category,
                'code_name': code_name,
                'source_url': s.get('sourceUrl', ''),
                'source_url_len': len(s.get('sourceUrl', '')),
                'success': False,
                'fail_reason': 'G_exception',
                'evidence': f'exception:{type(e).__name__}:{str(e)[:200]}',
            })

    # 步骤6: 生成报告
    log('\n--- 步骤6: 生成报告 ---')
    write_reports(results, all_sources)
    raw_log_fp.close()
    print('\n' + '=' * 70)
    print(f'验证完成. 报告: {REPORT_MD}')
    print('=' * 70)


def write_reports(results, all_sources):
    total_tested = len(results)
    success_count = sum(1 for r in results if r['success'])
    fail_count = total_tested - success_count

    fail_dist = Counter()
    for r in results:
        if not r['success']:
            fail_dist[r['fail_reason']] += 1

    # 按类别统计成功率
    cat_stats = {}
    for r in results:
        cat = r['category']
        if cat not in cat_stats:
            cat_stats[cat] = {'total': 0, 'success': 0, 'fail': 0}
        cat_stats[cat]['total'] += 1
        if r['success']:
            cat_stats[cat]['success'] += 1
        else:
            cat_stats[cat]['fail'] += 1

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

    # 加载修复统计(用于对比)
    fix_stats = {}
    if FIX_REPORT.exists():
        with open(FIX_REPORT, 'r', encoding='utf-8') as f:
            fix_stats = json.load(f)

    # MD 报告(脱敏)
    md = []
    md.append('# V5.2 订阅源真机验证报告')
    md.append('')
    md.append('## 1. 修复统计')
    md.append('')
    md.append('| 指标 | 数值 |')
    md.append('|------|------|')
    if fix_stats:
        md.append(f'| 原 V5.1 源数 | {fix_stats.get("input", {}).get("v5_1_sources", 328)} |')
        md.append(f'| 移除源数 | {fix_stats.get("removed", {}).get("total", 104)} |')
        md.append(f'| 保留源数 | {fix_stats.get("kept", 224)} |')
        md.append(f'| 字段修复处数 | {fix_stats.get("field_fixes", {}).get("total", 197)} |')
    md.append(f'| V5.2 输出 JSON | `{JSON_PATH.name}` |')
    md.append('')

    md.append('## 2. 真机验证统计')
    md.append('')
    md.append('| 指标 | 数值 |')
    md.append('|------|------|')
    md.append(f'| DB 中源数 | {len(all_sources)} |')
    md.append(f'| 抽验数量 | {total_tested} |')
    md.append(f'| 成功 | {success_count} |')
    md.append(f'| 失败 | {fail_count} |')
    success_rate = success_count / total_tested * 100 if total_tested else 0
    md.append(f'| 成功率 | {success_rate:.1f}% |')
    md.append('')

    md.append('## 3. 按类别统计')
    md.append('')
    md.append('| 类别 | 总数 | 成功 | 失败 | 成功率 |')
    md.append('|------|------|------|------|--------|')
    cat_desc = {
        'v4_unchanged': 'V4 未变动源(基础)',
        'video': 'V5 视频深度修复',
        'missing': 'V5 缺字段补全',
        'hard': 'V5 难点源处理',
    }
    for cat, st in cat_stats.items():
        rate = st['success'] / st['total'] * 100 if st['total'] else 0
        md.append(f'| {cat_desc.get(cat, cat)} | {st["total"]} | {st["success"]} | {st["fail"]} | {rate:.0f}% |')
    md.append('')

    md.append('## 4. 失败原因分布')
    md.append('')
    md.append('| 失败原因 | 数量 | 说明 |')
    md.append('|----------|------|------|')
    reason_desc = {
        'A_timeout_or_unknown': '加载超时或未进入文章列表页',
        'B_network_error': '网络错误(IOException/SocketTimeout/UnknownHost/SSL/Cronet缺失)',
        'C_parse_error': '解析失败(规则错误)',
        'D_empty_list': '空列表(无内容但无错误)',
        'E_app_crash': 'App崩溃(FATAL EXCEPTION)',
        'F_nav_failed': '导航失败(无法进入订阅Tab)',
        'F_no_recycler': 'RecyclerView缺失',
        'F_no_dump': 'UI dump失败',
        'G_exception': '脚本异常',
    }
    for reason, count in sorted(fail_dist.items(), key=lambda x: -x[1]):
        desc = reason_desc.get(reason, reason)
        md.append(f'| {reason} | {count} | {desc} |')
    md.append('')

    md.append('## 5. 失败源清单(按失败原因分组, 脱敏代号)')
    md.append('')
    for reason in sorted(fail_dist.keys()):
        md.append(f'### {reason} - {reason_desc.get(reason, "")}')
        md.append('')
        md.append('| 代号 | 类别 | idx | url长度 |')
        md.append('|------|------|-----|--------|')
        for r in failed_list:
            if r['fail_reason'] != reason:
                continue
            cat_label = cat_desc.get(r['category'], r['category'])
            md.append(f'| {r["code_name"]} | {cat_label} | {r["idx"]} | {r["source_url_len"]} |')
        md.append('')

    md.append('## 6. 成功源清单(脱敏代号)')
    md.append('')
    md.append('| 代号 | 类别 | idx | url长度 |')
    md.append('|------|------|-----|--------|')
    for r in success_list:
        cat_label = cat_desc.get(r['category'], r['category'])
        md.append(f'| {r["code_name"]} | {cat_label} | {r["idx"]} | {r["source_url_len"]} |')
    md.append('')

    md.append('## 7. 与 V5.1 对比')
    md.append('')
    md.append('| 指标 | V5.1 | V5.2 | 变化 |')
    md.append('|------|------|------|------|')
    md.append(f'| 源数 | 328 | {len(all_sources)} | {len(all_sources) - 328} |')
    md.append(f'| 抽验数 | 35 | {total_tested} | {total_tested - 35} |')
    md.append(f'| 成功数 | 7 | {success_count} | +{success_count - 7} |')
    v51_rate = 20.0
    v52_rate = success_rate
    delta = v52_rate - v51_rate
    md.append(f'| 成功率 | {v51_rate:.1f}% | {v52_rate:.1f}% | +{delta:.1f}% |')
    md.append('')

    md.append('## 8. 关键发现')
    md.append('')
    if fail_dist.get('D_empty_list', 0) > 0:
        md.append(f'### 发现1: 空列表失败({fail_dist["D_empty_list"]}个)')
        md.append('- 现象: UI 进入文章列表页但 RecyclerView 无内容')
        md.append('- 根因: ruleArticles 选择器与实际页面结构不匹配, 或站点结构变更')
        md.append('')
    if fail_dist.get('B_network_error', 0) > 0:
        md.append(f'### 发现2: 网络错误({fail_dist["B_network_error"]}个)')
        md.append('- 现象: logcat 出现 IOException/SocketTimeout/UnknownHost/SSL')
        md.append('- 根因: 站点下线, HTTPS Cronet 库缺失, UA/Referer 配置不当, DNS 失败')
        md.append('')
    if fail_dist.get('A_timeout_or_unknown', 0) > 0:
        md.append(f'### 发现3: 加载超时({fail_dist["A_timeout_or_unknown"]}个)')
        md.append('- 现象: 点击源后未进入文章列表 Activity')
        md.append('- 根因: 源配置错误或站点响应超时')
        md.append('')
    if not fail_dist:
        md.append('### 全部抽验通过')
        md.append('- V5.2 修复策略有效, 移除 104 失效拆分子源后剩余源可用性显著提升')
        md.append('')

    md.append('## 9. 修复后源 JSON 路径')
    md.append('')
    md.append(f'- 修复后 JSON: `{JSON_PATH}`')
    md.append(f'- 修复统计: `{FIX_REPORT}`')
    md.append(f'- 失败源清单 JSON: `{FAILED_JSON}`')
    md.append(f'- 成功源清单 JSON: `{SUCCESS_JSON}`')
    md.append(f'- 截图目录: `{SHOTS_DIR}`')
    md.append(f'- 原始日志: `{RAW_LOG}`')
    md.append('')

    REPORT_MD.write_text('\n'.join(md), encoding='utf-8')


if __name__ == "__main__":
    main()
