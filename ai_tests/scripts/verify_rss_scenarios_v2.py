#!/usr/bin/env python3
"""verify_rss_scenarios_v2.py — 升级版4场景验证（v2 2026-07-18）

v2改进（基于深度诊断）：
1. 识别"JS双层加密源"模式（sortUrl/searchUrl都含@js:eval(source.sourceComment)）
   → 这种源跳过HTTP验证，标记 "需真机JS引擎验证"
2. 识别"占位符sourceUrl+无JS加密"模式（如idx 59）
   → 这种源是真实无效，标记 "建议删除"
3. 增强HTTP验证：Chrome UA + Referer + 15秒timeout
4. 输出纯技术指标，禁止业务字段原文

输出：编号 + 场景 + 状态 + 技术原因，不输出域名/URL/源名称
"""
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
import urllib.parse
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'
PKG = 'io.legado.app.debug'

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def adb(*args, timeout=15):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def adb_shell(cmd_str, timeout=15):
    """执行 adb shell 'cmd_str'（用字符串方式传给shell解析，保留引号）"""
    full_cmd = f'"{ADB}" -s {HOST} shell {cmd_str}'
    return subprocess.run(full_cmd, shell=True, capture_output=True, timeout=timeout, text=False)


def pull_db(tmp_path):
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)
    adb_shell('rm -f /sdcard/legado_v2.db /sdcard/legado_v2.db-wal /sdcard/legado_v2.db-shm')
    adb_shell(f"su -c 'cp /data/data/{PKG}/databases/legado.db /sdcard/legado_v2.db'")
    adb_shell(f"su -c 'cp /data/data/{PKG}/databases/legado.db-wal /sdcard/legado_v2.db-wal 2>/dev/null; true'")
    adb_shell(f"su -c 'cp /data/data/{PKG}/databases/legado.db-shm /sdcard/legado_v2.db-shm 2>/dev/null; true'")
    adb_shell("su -c 'chmod 666 /sdcard/legado_v2.db /sdcard/legado_v2.db-wal /sdcard/legado_v2.db-shm 2>/dev/null; true'")
    # pull 用 list 方式（路径含空格安全）
    subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/legado_v2.db', tmp_path], capture_output=True, timeout=30)
    subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/legado_v2.db-wal', tmp_path + '-wal'], capture_output=True, timeout=30)
    subprocess.run([ADB, '-s', HOST, 'pull', '/sdcard/legado_v2.db-shm', tmp_path + '-shm'], capture_output=True, timeout=30)


def load_sources(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("PRAGMA table_info(rssSources)")
    columns = [r[1] for r in cur.fetchall()]
    cur.execute(f"SELECT {', '.join(columns)} FROM rssSources")
    rows = cur.fetchall()
    sources = []
    for row in rows:
        s = {c: row[c] for c in columns if row[c] is not None}
        sources.append(s)
    conn.close()
    return sources


def is_js_double_encrypted(s):
    """识别JS双层加密源：
    sourceUrl是占位符 + sortUrl/searchUrl含@js:eval(source.sourceComment)
    注意：sourceComment本身不需要@js前缀（是普通文本JS代码）
    """
    source_url = s.get('sourceUrl', '')
    sort_url = s.get('sortUrl', '')
    search_url = s.get('searchUrl', '')

    # sourceUrl 必须是占位符（非http开头）
    if source_url.startswith('http'):
        return False

    # sortUrl 或 searchUrl 含 @js: 或 <js> 且引用 source.sourceComment
    sort_has_js_eval = ('@js:' in sort_url or sort_url.startswith('<js>')) and 'source.sourceComment' in sort_url
    search_has_js_eval = ('@js:' in search_url or search_url.startswith('<js>')) and 'source.sourceComment' in search_url
    return sort_has_js_eval or search_has_js_eval


def is_placeholder_invalid(s):
    """识别无效占位符源（非http开头且无JS加密）"""
    source_url = s.get('sourceUrl', '')
    if source_url.startswith('http'):
        return False
    return not is_js_double_encrypted(s)


def extract_base_url(source_url):
    if not source_url:
        return ''
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    return base.rstrip('/').rstrip(',') + '/'


def normalize_url(url, base_url):
    if not url:
        return ''
    if url.startswith('http'):
        return url
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        m = re.match(r'(https?://[^/]+)', base_url)
        if m:
            return m.group(1) + url
        return ''
    return base_url.rstrip('/') + '/' + url


def replace_key(url, key='test'):
    if not url:
        return ''
    return url.replace('{{key}}', urllib.parse.quote(key))


def check_url_enhanced(url, timeout=15):
    """增强URL检查：Chrome UA + Referer + 长 timeout"""
    if not url:
        return (0, 0, 'empty_url')
    try:
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return (resp.status, len(data), None)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'Name or service' in reason or 'getaddrinfo' in reason or 'nodename' in reason:
            return (0, 0, 'dns_fail')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, 0, 'timeout')
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            return (0, 0, 'ssl_error')
        if 'Connection refused' in reason or 'RemoteDisconnected' in reason:
            return (0, 0, 'connection_refused')
        return (0, 0, 'url_error')
    except socket.timeout:
        return (0, 0, 'timeout')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')


def is_valid_rule_next_page(v):
    """ruleNextPage 合法性校验（升级版：识别无前缀CSS选择器）"""
    if not v or v in ('page', 'None', 'null', 'undefined', 'NaN'):
        return False
    if v.startswith(('@CSS:', '@XPath:', '@js:', '<js>')):
        return True
    if '@href' in v:
        return True
    # CSS 选择器特征：含 .class 或 #id 或 tag@href
    if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>]+@?.*', v):
        return True
    if v.startswith('(function'):
        return True
    return False


def main():
    print('=' * 70)
    print('订阅源4场景验证 v2（脱敏输出+JS双层识别）')
    print('=' * 70)

    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        print('\n--- Pull DB ---')
        pull_db(tmp_db)
        for ext in ['-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)

        print('\n--- Load sources ---')
        sources = load_sources(tmp_db)
        print(f'  total: {len(sources)} sources')

        # 识别三类源
        js_double_sources = [s for s in sources if is_js_double_encrypted(s)]
        placeholder_invalid = [s for s in sources if is_placeholder_invalid(s)]
        http_sources = [s for s in sources if s.get('sourceUrl', '').startswith('http')]

        print(f'\n--- 源分类 ---')
        print(f'  JS双层加密源（跳过HTTP验证）: {len(js_double_sources)} 个')
        print(f'  无效占位符源（建议删除）: {len(placeholder_invalid)} 个')
        print(f'  HTTP可验证源: {len(http_sources)} 个')

        # 4场景验证（仅对HTTP可验证源）
        results = {
            'scenario_1_list_load': {'pass': 0, 'fail': 0, 'skip_js': 0, 'skip_invalid': 0, 'errors': []},
            'scenario_2_search': {'pass': 0, 'fail': 0, 'skip_js': 0, 'skip_invalid': 0, 'skip_empty': 0, 'errors': []},
            'scenario_3_category': {'pass': 0, 'fail': 0, 'skip_js': 0, 'skip_invalid': 0, 'skip_empty': 0, 'errors': []},
            'scenario_4_nextpage': {'pass': 0, 'fail': 0, 'skip_js': 0, 'skip_invalid': 0, 'skip_empty': 0, 'errors': []},
        }

        for i, s in enumerate(sources):
            source_url = s.get('sourceUrl', '')
            search_url = s.get('searchUrl', '')
            sort_url = s.get('sortUrl', '')
            rule_next = s.get('ruleNextPage', '')

            # 跳过JS双层加密源（标记需真机验证）
            if is_js_double_encrypted(s):
                results['scenario_1_list_load']['skip_js'] += 1
                results['scenario_2_search']['skip_js'] += 1
                results['scenario_3_category']['skip_js'] += 1
                results['scenario_4_nextpage']['skip_js'] += 1
                continue

            # 跳过无效占位符源（标记建议删除）
            if is_placeholder_invalid(s):
                results['scenario_1_list_load']['skip_invalid'] += 1
                results['scenario_2_search']['skip_invalid'] += 1
                results['scenario_3_category']['skip_invalid'] += 1
                results['scenario_4_nextpage']['skip_invalid'] += 1
                continue

            base_url = extract_base_url(source_url)

            # 场景1: 列表加载
            list_url = re.sub(r'\{\{.*\}\}', '', source_url).rstrip(',')
            if not list_url:
                list_url = base_url
            status, clen, err = check_url_enhanced(list_url)
            if status == 200 and clen > 1000:
                results['scenario_1_list_load']['pass'] += 1
            else:
                results['scenario_1_list_load']['fail'] += 1
                results['scenario_1_list_load']['errors'].append(f'idx{i}:status={status},err={err}')

            # 场景2: 搜索功能
            if not search_url:
                results['scenario_2_search']['skip_empty'] += 1
            elif search_url.startswith('@js:') or search_url.startswith('<js>'):
                results['scenario_2_search']['skip_js'] += 1
            else:
                surl = normalize_url(replace_key(search_url), base_url)
                status, clen, err = check_url_enhanced(surl)
                if status == 200 and clen > 500:
                    results['scenario_2_search']['pass'] += 1
                else:
                    results['scenario_2_search']['fail'] += 1
                    results['scenario_2_search']['errors'].append(f'idx{i}:status={status},err={err}')

            # 场景3: 分类切换
            if not sort_url:
                results['scenario_3_category']['skip_empty'] += 1
            elif sort_url.startswith('@js:') or sort_url.startswith('<js>'):
                results['scenario_3_category']['skip_js'] += 1
            else:
                lines = [l.strip() for l in sort_url.split('\n') if '::' in l]
                if not lines:
                    results['scenario_3_category']['skip_empty'] += 1
                else:
                    first = lines[0].split('::', 1)[1]
                    curl = normalize_url(first, base_url)
                    status, clen, err = check_url_enhanced(curl)
                    if status == 200 and clen > 500:
                        results['scenario_3_category']['pass'] += 1
                    else:
                        results['scenario_3_category']['fail'] += 1
                        results['scenario_3_category']['errors'].append(f'idx{i}:status={status},err={err}')

            # 场景4: 下一页
            if not rule_next:
                results['scenario_4_nextpage']['skip_empty'] += 1
            else:
                if is_valid_rule_next_page(rule_next):
                    results['scenario_4_nextpage']['pass'] += 1
                else:
                    results['scenario_4_nextpage']['fail'] += 1
                    results['scenario_4_nextpage']['errors'].append(f'idx{i}:invalid_prefix')

        # 汇总
        print('\n' + '=' * 70)
        print('v2 验证汇总')
        print('=' * 70)
        for scenario, r in results.items():
            total = len(sources)
            print(f"\n  {scenario}:")
            print(f"    pass={r['pass']}/{total}")
            print(f"    fail={r['fail']}")
            print(f"    skip_js={r.get('skip_js', 0)} (需真机JS引擎验证)")
            print(f"    skip_invalid={r.get('skip_invalid', 0)} (无效占位符源)")
            print(f"    skip_empty={r.get('skip_empty', 0)} (字段为空)")
            if r['errors']:
                print(f"    errors (前5个):")
                for e in r['errors'][:5]:
                    print(f"      {e}")

        # 真实可用率计算
        total = len(sources)
        js_count = len(js_double_sources)
        invalid_count = len(placeholder_invalid)
        http_count = len(http_sources)

        print(f'\n--- 真实可用率（v2修正） ---')
        print(f'  总源数: {total}')
        print(f'  JS双层加密源（跳过HTTP验证）: {js_count} → 需真机JS引擎验证')
        print(f'  无效占位符源（建议删除）: {invalid_count} → 真实无效')
        print(f'  HTTP可验证源: {http_count}')
        list_pass_rate = results['scenario_1_list_load']['pass'] / http_count * 100 if http_count else 0
        print(f'  列表加载通过率: {results["scenario_1_list_load"]["pass"]}/{http_count} = {list_pass_rate:.1f}%')

        # 保存详细结果
        out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/scenario_verification_v2.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump({
                'results': results,
                'source_classification': {
                    'js_double_encrypted': js_count,
                    'placeholder_invalid': invalid_count,
                    'http_verifiable': http_count,
                    'total': total,
                },
            }, f, ensure_ascii=False, indent=2)
        print(f'\n详细结果: {out_path}')

    finally:
        for ext in ['', '-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    main()
