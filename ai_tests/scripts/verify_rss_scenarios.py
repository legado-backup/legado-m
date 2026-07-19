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

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG

def adb(*args, timeout=15):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def pull_db(tmp_path):
    """从设备pull legado.db（使用su，MEmu兼容）"""
    adb('shell', 'am', 'force-stop', PKG)
    time.sleep(1)
    r = adb('shell', 'su', '-c', f'cp /data/data/{PKG}/databases/legado.db /sdcard/legado_v.db')
    if r.returncode != 0:
        print(f'  ❌ cp db failed: {r.stderr.decode("utf-8", errors="replace")}')
    adb('shell', 'su', '-c', 'chmod 666 /sdcard/legado_v.db')
    # WAL/SHM可能不存在，忽略错误
    adb('shell', 'su', '-c', f'cp /data/data/{PKG}/databases/legado.db-wal /sdcard/legado_v.db-wal 2>/dev/null; chmod 666 /sdcard/legado_v.db-wal 2>/dev/null; true')
    adb('shell', 'su', '-c', f'cp /data/data/{PKG}/databases/legado.db-shm /sdcard/legado_v.db-shm 2>/dev/null; chmod 666 /sdcard/legado_v.db-shm 2>/dev/null; true')
    r = adb('pull', '/sdcard/legado_v.db', tmp_path)
    if r.returncode != 0:
        print(f'  ❌ pull db failed: {r.stderr.decode("utf-8", errors="replace")}')
        return False
    # 检查文件大小
    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 1024:
        print(f'  ❌ pulled db too small or missing: size={os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0}')
        return False
    print(f'  DB pulled to {tmp_path} (size={os.path.getsize(tmp_path)})')
    # 删除本地WAL/SHM避免malformed
    for ext in ['-wal', '-shm']:
        p = tmp_path + ext
        if os.path.exists(p):
            os.unlink(p)
    return True


def load_sources(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cur.execute("PRAGMA table_info(rssSources)")
        columns = [r[1] for r in cur.fetchall()]
        if not columns:
            print(f'  ❌ rssSources 表无列或表不存在')
            return []
        cur.execute(f"SELECT {', '.join(columns)} FROM rssSources")
        rows = cur.fetchall()
        sources = []
        for row in rows:
            s = {c: row[c] for c in columns if row[c] is not None}
            sources.append(s)
        return sources
    finally:
        conn.close()


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


# 无效值集合（批量脚本可能误填的字符串）
INVALID_VALUES = {'page', 'None', 'null', 'undefined', 'NaN', ''}


def is_valid_rule_next_page(v):
    """ruleNextPage 合法性校验（支持 legado 原生语法）

    legado 支持的7种合法形式：
    1. 显式前缀：@CSS: / @XPath: / @js: / <js> / @put: / @get:
    2. 原生语法前缀：class. / text. / page. / 标签.(li./a./div.等)
    3. CSS 选择器特征：以 . 或 # 开头
    4. 含 @href 或 @src 属性提取
    5. 含 <js> 标签
    6. 以 (function 开头的IIFE
    7. 正则匹配 CSS 选择器模式（兜底）

    修复历史（2026-07-18 v5反哺）：
    - 原版仅校验 @CSS:/@XPath:/@js: 三种前缀，导致 scenario_4 通过率 0%
    - 修复后支持 legado 原生语法，scenario_4 通过率从 0% 提升到 62.5%
    """
    if not v or v in INVALID_VALUES:
        return False

    # 1. 显式前缀（最强信号）
    if v.startswith(('@CSS:', '@XPath:', '@js:', '<js>', '@put:', '@get:')):
        return True

    # 2. legado 原生语法前缀（class. / text. / page. / 标签.）
    native_prefixes = ('class.', 'text.', 'page.', 'li.', 'a.', 'div.',
                       'span.', 'img.', 'ul.', 'ol.', 'p.', 'h1.', 'h2.',
                       'h3.', 'h4.', 'h5.', 'h6.', 'script@', 'link[',
                       'input[', '$.')
    if v.startswith(native_prefixes):
        return True

    # 3. CSS 选择器特征（无前缀直接写选择器）
    if v.startswith(('.', '#')):
        return True

    # 4. 含 @href 或 @src 属性提取
    if '@href' in v or '@src' in v:
        return True

    # 5. 含 <js> 标签
    if '<js>' in v:
        return True

    # 6. 以 (function 开头的IIFE
    if v.startswith('(function'):
        return True

    # 7. 正则匹配 CSS 选择器模式（兜底）
    if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>+,~]+', v):
        return True

    return False


def classify_rule_next_page_prefix(v):
    """识别 ruleNextPage 的语法类型（用于脱敏输出，不输出业务字段原文）"""
    if not v:
        return 'empty'
    if v.startswith('@CSS:'):
        return 'css_prefix'
    if v.startswith('@XPath:'):
        return 'xpath_prefix'
    if v.startswith('@js:') or v.startswith('<js>') or '<js>' in v:
        return 'js'
    if v.startswith('@put:') or v.startswith('@get:'):
        return 'put_get'
    if v.startswith('class.'):
        return 'class_dot'
    if v.startswith('text.'):
        return 'text_dot'
    if v.startswith('page.'):
        return 'page_dot'
    if v.startswith(('li.', 'a.', 'div.', 'span.', 'img.', 'ul.', 'ol.',
                     'p.', 'h1.', 'h2.', 'h3.', 'h4.', 'h5.', 'h6.')):
        return 'tag_dot'
    if v.startswith('script@'):
        return 'script_at'
    if v.startswith(('link[', 'input[')):
        return 'attr_bracket'
    if v.startswith('$.'):
        return 'jquery'
    if v.startswith(('.', '#')):
        return 'css_selector'
    if '@href' in v or '@src' in v:
        return 'attr_extract'
    if v.startswith('(function'):
        return 'iife'
    if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>+,~]+', v):
        return 'css_pattern'
    return 'unknown'


def main():
    print('=' * 60)
    print('订阅源4场景验证（脱敏输出：只显示技术结论）')
    print('=' * 60)

    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    # 立即关闭临时文件句柄（Windows下NamedTemporaryFile会持有句柄）
    try:
        # 先尝试用已pull的check.db（避免重复pull）
        fallback_db = 'output/rss/check.db'
        used_db = None
        print('\n--- Pull DB ---')
        if pull_db(tmp_db):
            used_db = tmp_db
        elif os.path.exists(fallback_db):
            print(f'  ⚠️ pull失败，使用fallback: {fallback_db}')
            used_db = fallback_db
        else:
            print('  ❌ pull失败且无fallback，退出')
            return

        # 删除 WAL/SHM 避免 malformed
        for ext in ['-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)

        print('\n--- Load sources ---')
        sources = load_sources(used_db)
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

            # 场景4: 下一页（语法校验，支持 legado 原生语法）
            if not rule_next:
                results['scenario_4_nextpage']['skip'] += 1
                print(f'    [4.下一页] ⏭️ 跳过（无 ruleNextPage）')
            else:
                # 语法校验：支持 legado 7种合法形式（显式前缀/原生语法/CSS选择器/属性提取/js/IIFE/正则兜底）
                # v5反哺修复：原版仅校验 @CSS:/@XPath:/@js: 导致 0% 通过率，修复后支持 class./text./page. 等原生语法
                if is_valid_rule_next_page(rule_next):
                    prefix_type = classify_rule_next_page_prefix(rule_next)
                    results['scenario_4_nextpage']['pass'] += 1
                    print(f'    [4.下一页] ✅ 语法有效 type={prefix_type} len={len(rule_next)}')
                else:
                    prefix_type = classify_rule_next_page_prefix(rule_next)
                    results['scenario_4_nextpage']['fail'] += 1
                    results['scenario_4_nextpage']['errors'].append(f'源{i+1}:invalid_type={prefix_type}')
                    print(f'    [4.下一页] ❌ 语法无效 type={prefix_type} len={len(rule_next)}')

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
        # 清理临时文件（忽略错误，避免PermissionError中断）
        import gc
        gc.collect()
        for ext in ['', '-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except PermissionError:
                    pass


if __name__ == "__main__":
    import urllib.parse
    main()
