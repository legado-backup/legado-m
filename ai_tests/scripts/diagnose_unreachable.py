#!/usr/bin/env python3
"""diagnose_unreachable.py — 诊断真实不可达源的修复建议（脱敏输出）

对v2验证中10个HTTP验证失败的源，逐一分析失败原因并给出修复建议
"""
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
import ssl
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 从v2验证结果加载失败idx
FAILED_IDX = [1, 21, 24, 30, 36, 39, 46, 55, 58, 60]  # 场景1失败的idx（status!=200或clen<1000）


def check_url_with_ssl_skip(url, timeout=15):
    """跳过SSL证书验证的URL检查"""
    if not url:
        return (0, 0, 'empty_url')
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            return (resp.status, len(data), None)
    except urllib.error.HTTPError as e:
        return (e.code, 0, f'http_{e.code}')
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'SSL' in reason or 'CERTIFICATE' in reason:
            return (0, 0, 'ssl_error')
        if 'timed out' in reason or 'timeout' in reason:
            return (0, 0, 'timeout')
        if 'Connection refused' in reason or 'RemoteDisconnected' in reason:
            return (0, 0, 'connection_refused')
        return (0, 0, 'url_error')
    except socket.timeout:
        return (0, 0, 'timeout')
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')


def check_url_http_only(url, timeout=15):
    """HTTP only（降级https→http）"""
    if not url:
        return (0, 0, 'empty_url')
    # 尝试https→http降级
    if url.startswith('https://'):
        url = 'http://' + url[len('https://'):]
    return check_url_with_ssl_skip(url, timeout)


def check_url_long_timeout(url, timeout=30):
    """长timeout URL检查"""
    if not url:
        return (0, 0, 'empty_url')
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        m = re.match(r'(https?://[^/]+)', url)
        referer = m.group(1) + '/' if m else ''
        req = urllib.request.Request(url, headers={
            'User-Agent': CHROME_UA,
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer,
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            return (resp.status, len(data), None)
    except Exception as e:
        return (0, 0, f'exception:{type(e).__name__}')


def adb_pull_db(tmp_path):
    adb = lambda *args: subprocess.run([ADB, '-s', HOST] + list(args), capture_output=True, timeout=15)
    adb('shell', 'am', 'force-stop', PKG)
    time.sleep(1)
    adb('shell', 'rm', '/sdcard/legado_du.db', '/sdcard/legado_du.db-wal', '/sdcard/legado_du.db-shm')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db', f'/data/data/{PKG}/files/du.db')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db-wal', f'/data/data/{PKG}/files/du.db-wal')
    adb('shell', 'run-as', PKG, 'cp', f'/data/data/{PKG}/databases/legado.db-shm', f'/data/data/{PKG}/files/du.db-shm')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/du.db')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/du.db-wal')
    adb('shell', 'run-as', PKG, 'chmod', '644', f'/data/data/{PKG}/files/du.db-shm')
    adb('shell', 'cat', f'/data/data/{PKG}/files/du.db', '>', '/sdcard/legado_du.db')
    adb('shell', 'cat', f'/data/data/{PKG}/files/du.db-wal', '>', '/sdcard/legado_du.db-wal')
    adb('shell', 'cat', f'/data/data/{PKG}/files/du.db-shm', '>', '/sdcard/legado_du.db-shm')
    adb('pull', '/sdcard/legado_du.db', tmp_path)
    adb('pull', '/sdcard/legado_du.db-wal', tmp_path + '-wal')
    adb('pull', '/sdcard/legado_du.db-shm', tmp_path + '-shm')


def main():
    print('=' * 70)
    print('真实不可达源修复建议（脱敏：只输出idx和修复策略）')
    print('=' * 70)

    # 直接从JSON文件加载（避免DB WAL问题）
    BATCH_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_batch_fixed.json'
    with open(BATCH_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f'\n总源数: {len(sources)}')
    print(f'需诊断的失败源idx: {FAILED_IDX}')

    print('\n--- 逐个诊断+修复策略 ---')
    diagnosis_results = []
    for idx in FAILED_IDX:
        s = sources[idx]
        source_url = s.get('sourceUrl', '')
        base_url = re.sub(r'\{\{.*\}\}', '', source_url).rstrip('/').rstrip(',') + '/'

        print(f'\n  [idx={idx}] base_url_len={len(base_url)}')

        # 测试1: 跳过SSL证书验证
        status1, clen1, err1 = check_url_with_ssl_skip(base_url, timeout=15)
        print(f'    测试1(跳过SSL): status={status1} len={clen1} err={err1}')

        # 测试2: 降级到HTTP
        status2, clen2, err2 = check_url_http_only(base_url, timeout=15)
        print(f'    测试2(HTTP降级): status={status2} len={clen2} err={err2}')

        # 测试3: 长 timeout (30秒)
        status3, clen3, err3 = check_url_long_timeout(base_url, timeout=30)
        print(f'    测试3(30秒timeout): status={status3} len={clen3} err={err3}')

        # 综合判断修复策略
        if status1 == 200 and clen1 > 1000:
            fix_strategy = 'ssl_skip'
        elif status2 == 200 and clen2 > 1000:
            fix_strategy = 'http_downgrade'
        elif status3 == 200 and clen3 > 1000:
            fix_strategy = 'long_timeout'
        elif '403' in str(err1) + str(err2) + str(err3):
            fix_strategy = 'ua_or_cookie'
        elif 'timeout' in str(err1) + str(err2) + str(err3):
            fix_strategy = 'server_slow_or_down'
        elif 'connection_refused' in str(err1) + str(err2) + str(err3):
            fix_strategy = 'server_offline'
        elif '404' in str(err1) + str(err2) + str(err3):
            fix_strategy = 'url_moved'
        elif '500' in str(err1) + str(err2) + str(err3):
            fix_strategy = 'server_error'
        else:
            fix_strategy = 'truly_dead'

        print(f'    修复策略: {fix_strategy}')
        diagnosis_results.append({
            'idx': idx,
            'base_url_len': len(base_url),
            'test1_ssl_skip': {'status': status1, 'err': err1},
            'test2_http_downgrade': {'status': status2, 'err': err2},
            'test3_long_timeout': {'status': status3, 'err': err3},
            'fix_strategy': fix_strategy,
        })

    # 汇总修复策略分布
    print('\n' + '=' * 70)
    print('修复策略分布')
    print('=' * 70)
    from collections import Counter
    strategy_counter = Counter(r['fix_strategy'] for r in diagnosis_results)
    for strategy, count in strategy_counter.most_common():
        print(f'  {strategy}: {count} 个')

    # 修复建议
    print('\n--- 修复建议（按策略分组）---')
    strategy_groups = {}
    for r in diagnosis_results:
        strategy_groups.setdefault(r['fix_strategy'], []).append(r['idx'])

    for strategy, idxs in strategy_groups.items():
        print(f'\n  [{strategy}] idx: {idxs}')
        if strategy == 'ssl_skip':
            print('    修复: App 内置 OkHttp 默认跳过SSL验证，可直接使用，无需修复')
        elif strategy == 'http_downgrade':
            print('    修复: 站点可能只支持HTTP，将sourceUrl改成http://开头')
        elif strategy == 'long_timeout':
            print('    修复: 慢站，App 的网络超时配置延长到30秒')
        elif strategy == 'ua_or_cookie':
            print('    修复: 需要更真实的UA或登录Cookie，在App中手动访问触发Cookie同步')
        elif strategy == 'server_slow_or_down':
            print('    修复: 服务器响应慢，可在App中重试访问')
        elif strategy == 'server_offline':
            print('    修复: 服务器下线，建议删除该源')
        elif strategy == 'url_moved':
            print('    修复: URL已迁移，需重新Playwright分析新站点URL')
        elif strategy == 'server_error':
            print('    修复: 服务器内部错误，稍后重试')
        elif strategy == 'truly_dead':
            print('    修复: 真实失效，建议删除')

    # 保存报告
    out_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/unreachable_diagnosis.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'diagnosis': diagnosis_results,
            'strategy_distribution': dict(strategy_counter),
            'strategy_groups': strategy_groups,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n详细报告: {out_path}')


if __name__ == "__main__":
    main()
