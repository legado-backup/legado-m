#!/usr/bin/env python3
"""verify_rss_scenarios.py — 验证订阅源4场景（脱敏：只输出技术结论）

验证场景：
1. 列表加载：sourceUrl 可访问，返回 HTML
2. 搜索功能：searchUrl 模板替换 {{key}} 后可访问
3. 分类切换：sortUrl 中各分类 URL 可访问
4. 下一页：ruleNextPage 是否存在（语法校验，不实际翻页）

输出：编号 + HTTP状态码 + 响应长度 + 字段是否存在，不输出域名/URL/源名称
"""
import json
import re
import sqlite3
import subprocess
import sys
import os
import tempfile
import time
from pathlib import Path
import urllib.request
import urllib.error
import socket

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

def adb(*args, timeout=15):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def pull_db(tmp_path):
    adb('shell', 'am', 'force-stop', PKG)
    time.sleep(1)
    adb('shell', 'rm', '/sdcard/legado_v.db', '/sdcard/legado_v.db-wal', '/sdcard/legado_v.db-shm')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db', f'/data/data/{PKG}/files/v.db')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db-wal', f'/data/data/{PKG}/files/v.db-wal')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db-shm', f'/data/data/{PKG}/files/v.db-shm')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/v.db')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/v.db-wal')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/v.db-shm')
    adb('shell', 'cat', f'/data/data/{PKG}/files/v.db', '>', '/sdcard/legado_v.db')
    adb('shell', 'cat', f'/data/data/{PKG}/files/v.db-wal', '>', '/sdcard/legado_v.db-wal')
    adb('shell', 'cat', f'/data/data/{PKG}/files/v.db-shm', '>', '/sdcard/legado_v.db-shm')
    adb('pull', '/sdcard/legado_v.db', tmp_path)
    adb('pull', '/sdcard/legado_v.db-wal', tmp_path + '-wal')
    adb('pull', '/sdcard/legado_v.db-shm', tmp_path + '-shm')


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


def extract_base_url(source_url):
    """从 sourceUrl 模板提取首页 URL"""
    if not source_url:
        return ''
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    return base.rstrip('/') + '/'


def normalize_url(url, base_url):
    """URL 规范化：相对 URL 转 absolute"""
    if not url:
        return ''
    if url.startswith('http'):
        return url
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        # 从 base_url 提取 domain
        m = re.match(r'(https?://[^/]+)', base_url)
        if m:
            return m.group(1) + url
        return ''
    return base_url.rstrip('/') + '/' + url


def replace_key(url, key='test'):
    """替换 {{key}} 为搜索词"""
    if not url:
        return ''
    return url.replace('{{key}}', urllib.parse.quote(key))


def check_url(url, timeout=8):
    """检查 URL 可访问性，返回 (status_code, content_length, error)"""
    if not url:
        return (0, 0, 'empty_url')
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return (resp.status, len(data), None)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_error')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'Name or service not known' in reason or 'getaddrinfo' in reason:
            return (0, 0, 'dns_fail')
        if 'timed out' in reason:
            return (0, 0, 'timeout')
        return (0, 0, 'url_error')
    except socket.timeout:
        return (0, 0, 'timeout')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')


def main():
    print('=' * 60)
    print('订阅源4场景验证（脱敏输出：只显示技术结论）')
    print('=' * 60)

    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        print('\n--- Pull DB ---')
        pull_db(tmp_db)
        # 删除 WAL/SHM 避免 malformed
        for ext in ['-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)

        print('\n--- Load sources ---')
        sources = load_sources(tmp_db)
        print(f'  total: {len(sources)} sources')

        # 统计4场景字段情况
        has_source_url = sum(1 for s in sources if s.get('sourceUrl'))
        has_search_url = sum(1 for s in sources if s.get('searchUrl'))
        has_sort_url = sum(1 for s in sources if s.get('sortUrl'))
        has_rule_next = sum(1 for s in sources if s.get('ruleNextPage'))
        has_source_icon = sum(1 for s in sources if s.get('sourceIcon'))

        print(f'\n--- 字段统计 ---')
        print(f'  sourceUrl 非空: {has_source_url}/{len(sources)}')
        print(f'  sourceIcon 非空: {has_source_icon}/{len(sources)}')
        print(f'  searchUrl 非空: {has_search_url}/{len(sources)}')
        print(f'  sortUrl 非空: {has_sort_url}/{len(sources)}')
        print(f'  ruleNextPage 非空: {has_rule_next}/{len(sources)}')

        # 抽样测试：随机选5个有 sourceUrl 的源做完整4场景测试
        # 避免测试所有65个（耗时太久 + 易触发反爬）
        import random
        random.seed(42)
        candidates = [s for s in sources if s.get('sourceUrl')]
        sample_size = min(8, len(candidates))
        sample = random.sample(candidates, sample_size)
        print(f'\n--- 抽样测试 {sample_size} 个源 4场景 ---')

        results = {
            'scenario_1_list_load': {'pass': 0, 'fail': 0, 'errors': []},
            'scenario_2_search': {'pass': 0, 'fail': 0, 'skip': 0, 'errors': []},
            'scenario_3_category': {'pass': 0, 'fail': 0, 'skip': 0, 'errors': []},
            'scenario_4_nextpage': {'pass': 0, 'fail': 0, 'skip': 0, 'errors': []},
        }

        for i, s in enumerate(sample):
            source_url = s.get('sourceUrl', '')
            search_url = s.get('searchUrl', '')
            sort_url = s.get('sortUrl', '')
            rule_next = s.get('ruleNextPage', '')
            base_url = extract_base_url(source_url)

            print(f'\n  [源{i+1}] base_len={len(base_url)}')

            # 场景1: 列表加载 - 访问 sourceUrl（去掉 {{...}} 模板）
            list_url = re.sub(r'\{\{.*\}\}', '', source_url).rstrip(',')  # 移除末尾多余逗号
            if not list_url:
                list_url = base_url
            status, clen, err = check_url(list_url)
            ok = status == 200 and clen > 1000
            if ok:
                results['scenario_1_list_load']['pass'] += 1
                print(f'    [1.列表] ✅ status={status} len={clen}')
            else:
                results['scenario_1_list_load']['fail'] += 1
                results['scenario_1_list_load']['errors'].append(f'源{i+1}:status={status},err={err}')
                print(f'    [1.列表] ❌ status={status} len={clen} err={err}')

            # 场景2: 搜索功能
            if not search_url:
                results['scenario_2_search']['skip'] += 1
                print(f'    [2.搜索] ⏭️ 跳过（无 searchUrl）')
            else:
                surl = replace_key(search_url)
                surl = normalize_url(surl, base_url)
                status, clen, err = check_url(surl)
                ok = status == 200 and clen > 500
                if ok:
                    results['scenario_2_search']['pass'] += 1
                    print(f'    [2.搜索] ✅ status={status} len={clen}')
                else:
                    results['scenario_2_search']['fail'] += 1
                    results['scenario_2_search']['errors'].append(f'源{i+1}:status={status},err={err}')
                    print(f'    [2.搜索] ❌ status={status} len={clen} err={err}')

            # 场景3: 分类切换（取 sortUrl 第一个分类）
            if not sort_url:
                results['scenario_3_category']['skip'] += 1
                print(f'    [3.分类] ⏭️ 跳过（无 sortUrl）')
            else:
                # sortUrl 格式: 分类名::URL\n分类名::URL
                lines = [l.strip() for l in sort_url.split('\n') if '::' in l]
                if not lines:
                    results['scenario_3_category']['skip'] += 1
                    print(f'    [3.分类] ⏭️ 跳过（sortUrl 无 :: 分隔）')
                else:
                    first = lines[0].split('::', 1)[1]
                    curl = normalize_url(first, base_url)
                    status, clen, err = check_url(curl)
                    ok = status == 200 and clen > 500
                    if ok:
                        results['scenario_3_category']['pass'] += 1
                        print(f'    [3.分类] ✅ status={status} len={clen}')
                    else:
                        results['scenario_3_category']['fail'] += 1
                        results['scenario_3_category']['errors'].append(f'源{i+1}:status={status},err={err}')
                        print(f'    [3.分类] ❌ status={status} len={clen} err={err}')

            # 场景4: 下一页（语法校验）
            if not rule_next:
                results['scenario_4_nextpage']['skip'] += 1
                print(f'    [4.下一页] ⏭️ 跳过（无 ruleNextPage）')
            else:
                # 语法校验：必须是 @CSS:xxx@href 或 @XPath:xxx 或 regex 形式
                valid_prefix = rule_next.startswith('@CSS:') or rule_next.startswith('@XPath:') or rule_next.startswith('@js:')
                if valid_prefix:
                    results['scenario_4_nextpage']['pass'] += 1
                    print(f'    [4.下一页] ✅ 语法有效 prefix={rule_next.split(":")[0]}')
                else:
                    results['scenario_4_nextpage']['fail'] += 1
                    results['scenario_4_nextpage']['errors'].append(f'源{i+1}:prefix_invalid')
                    print(f'    [4.下一页] ❌ 语法无效 prefix={rule_next[:20]}')

        # 汇总
        print('\n' + '=' * 60)
        print('验证汇总')
        print('=' * 60)
        for scenario, r in results.items():
            total = r['pass'] + r['fail'] + r.get('skip', 0)
            print(f"  {scenario}:")
            print(f"    pass={r['pass']}/{total}  fail={r['fail']}  skip={r.get('skip', 0)}")
            if r['errors']:
                for e in r['errors'][:3]:
                    print(f"    err: {e}")

        # 保存详细结果
        out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/scenario_verification.json'
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存: {out_path}")

    finally:
        for ext in ['', '-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    import urllib.parse
    main()
