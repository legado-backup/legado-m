#!/usr/bin/env python3
"""retest_after_dns_change.py — DNS修改后重新测试7个源
设置多种DNS属性 + 触发dnschange + 重新测试"""
import json
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'
PKG = 'io.legado.app.debug'
DEBUG_ACTIVITY = f'{PKG}/.ui.rss.source.debug.RssSourceDebugActivity'

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
NEEDS_LOGIN_IDX = [21, 24, 30, 36, 39, 55, 58]


def adb_shell(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} shell {cmd}'
    return subprocess.run(full, shell=True, capture_output=True, timeout=timeout, text=False)


def sanitize(text):
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'https?://[^\s"\']+', '[URL]', s)
    s = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', s)
    s = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', s, flags=re.IGNORECASE)
    return s[:200]


def set_dns():
    """设置多种DNS属性 + 触发刷新"""
    print('--- 设置模拟器DNS为8.8.8.8/1.1.1.1 ---')
    # 设置所有可能的DNS属性
    dns_cmds = [
        'setprop net.dns1 8.8.8.8',
        'setprop net.dns2 1.1.1.1',
        'setprop net.pdns1 8.8.8.8',
        'setprop net.pdns2 1.1.1.1',
        'setprop dhcp.eth0.dns1 8.8.8.8',
        'setprop dhcp.eth0.dns2 1.1.1.1',
        # 触发DNS变化
        'setprop net.dnschange 1',
        # 私有DNS关闭
        'setprop net.private_dns_specifier ""',
    ]
    for cmd in dns_cmds:
        r = adb_shell(cmd)
        # 静默
    # 再次验证
    r = adb_shell('getprop net.dns1')
    dns1 = r.stdout.decode('utf-8', errors='ignore').strip()
    r = adb_shell('getprop net.dns2')
    dns2 = r.stdout.decode('utf-8', errors='ignore').strip()
    print(f'  net.dns1={dns1} net.dns2={dns2}')


def test_source_with_dns(idx, source_url, wait_sec=15):
    """测试单个源"""
    print(f'\n=== idx={idx} ===')

    # 清空logcat
    adb_shell('logcat -c')
    time.sleep(0.3)

    # 启动DebugActivity
    escaped = source_url.replace("'", "'\\''")
    cmd = f"am start -n {DEBUG_ACTIVITY} --es key '{escaped}'"
    adb_shell(cmd)

    # 等待加载
    time.sleep(wait_sec)

    # 截图
    remote = f'/sdcard/retest_{idx}.png'
    adb_shell(f'screencap -p {remote}')
    local = f'f:/myself/github/WeAgentChat/temp/legado/output/rss/each_source_test/retest_{idx}.png'
    subprocess.run([ADB, '-s', HOST, 'pull', remote, local], capture_output=True, timeout=10)

    # 拉取logcat
    r = adb_shell('logcat -d -t 1000')
    logcat = r.stdout.decode('utf-8', errors='ignore')

    # 过滤技术关键词
    safe_lines = []
    for line in logcat.split('\n'):
        if any(noise in line for noise in ['ProfileInstaller', 'ClassLoaderContext', 'app_process:', 'HostConnection']):
            continue
        if any(kw in line for kw in ['Exception', 'Error', 'network', 'RssSource', 'rssSource', 'sortUrls',
                                       'AnalyzeUrl', 'OkHttp', 'Cronet', 'ssl', 'SSL', 'timeout', 'reset',
                                       'connect', 'socket', 'http', 'resolve', 'host', 'EAI', 'getaddrinfo',
                                       'Cookie', 'Login']):
            safe = sanitize(line)
            safe = re.sub(r'sourceName=[^\s,]+', 'sourceName=[HIDDEN]', safe)
            safe = re.sub(r'cookie[:=][^\s,;]+', 'cookie=[HIDDEN]', safe, flags=re.IGNORECASE)
            safe = re.sub(r'sourceUrl=[^\s,]+', 'sourceUrl=[HIDDEN]', safe)
            safe_lines.append(safe[:200])

    # 去重
    seen = set()
    unique = []
    for line in safe_lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)

    print(f'  logcat({len(unique)}条):')
    for line in unique[:6]:
        print(f'    {line}')

    # 判定
    has_dns_err = any('resolve host' in line or 'EAI_NODATA' in line or 'getaddrinfo' in line for line in unique)
    has_network_disconnect = any('network is disconnect' in line.lower() for line in unique)
    has_exception = any(re.search(r'\w+Exception|\w+Error', line) for line in unique)
    has_rss_loaded = any('rssSource' in line.lower() or 'sortUrls' in line for line in unique)

    if has_dns_err:
        status = 'dns_failed'
    elif has_network_disconnect and not has_rss_loaded:
        status = 'network_unreachable'
    elif has_rss_loaded:
        status = 'source_loaded'
    elif has_exception:
        status = 'failed_with_exception'
    else:
        status = 'unknown'

    print(f'  状态: {status}')
    return {'idx': idx, 'status': status, 'logcat_top': unique[:5]}


def main():
    print('=' * 70)
    print('DNS修改后重新测试7个源（脱敏）')
    print('=' * 70)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    # 1. 设置DNS
    set_dns()

    # 2. 强制停止App（清除缓存）
    print('\n--- 重启App ---')
    adb_shell(f'am force-stop {PKG}')
    time.sleep(2)
    adb_shell(f'monkey -p {PKG} -c android.intent.category.LAUNCHER 1')
    time.sleep(5)

    # 3. 逐个测试
    results = []
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        source_url = sources[idx].get('sourceUrl', '')
        if not source_url.startswith('http'):
            results.append({'idx': idx, 'status': 'invalid_url'})
            continue
        try:
            r = test_source_with_dns(idx, source_url)
            results.append(r)
        except Exception as e:
            print(f'  idx={idx} 异常: {type(e).__name__}')
            results.append({'idx': idx, 'status': 'test_error', 'exception': type(e).__name__})

    # 汇总
    print('\n' + '=' * 70)
    print('汇总（DNS修改后）')
    print('=' * 70)
    success = sum(1 for r in results if r['status'] == 'source_loaded')
    dns_fail = sum(1 for r in results if r['status'] == 'dns_failed')
    net_fail = sum(1 for r in results if r['status'] == 'network_unreachable')
    other = len(results) - success - dns_fail - net_fail
    print(f'  成功加载: {success}/{len(results)}')
    print(f'  DNS失败: {dns_fail}/{len(results)}')
    print(f'  网络不可达: {net_fail}/{len(results)}')
    print(f'  其他: {other}/{len(results)}')

    print('\n--- 详情 ---')
    for r in results:
        print(f'  [idx={r.get("idx")}] {r.get("status")}')


if __name__ == '__main__':
    main()
