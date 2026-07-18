#!/usr/bin/env python3
"""write_hosts_mapping.py — 写hosts映射解决DNS解析失败

流程：
1. 在主机侧用socket.getaddrinfo解析7个域名得到IP
2. 在模拟器上 remount /system 为可写
3. 把 IP→域名 映射写入/system/etc/hosts
4. 重新测试7个源
"""
import json
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

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


def resolve_host_ips(sources):
    """在主机侧解析每个源的host得到IP列表"""
    print('\n--- 在主机侧解析host得到IP ---')
    host_ip_pairs = []  # [(host, ip), ...]
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        url = sources[idx].get('sourceUrl', '')
        if not url.startswith('http'):
            continue
        try:
            host = urlparse(url).hostname
            addrs = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ips = list(set([a[4][0] for a in addrs]))
            for ip in ips:
                host_ip_pairs.append((host, ip))
            print(f'  idx={idx} host={host[:20]}... ips_count={len(ips)} ip_type={"IPv4" if any("." in i for i in ips) else "IPv6"}')
        except Exception as e:
            print(f'  idx={idx} 解析异常: {type(e).__name__}')
    return host_ip_pairs


def write_hosts_file(host_ip_pairs):
    """把host IP映射写入模拟器/system/etc/hosts"""
    print('\n--- 写入模拟器/system/etc/hosts ---')

    # 1. 备份原hosts
    r = adb_shell('su -c "cat /system/etc/hosts"')
    backup = r.stdout.decode('utf-8', errors='ignore')
    print(f'  原hosts长度: {len(backup)}')

    # 2. remount /system为可写
    print('  remount /system...')
    r = adb_shell('su -c "mount -o rw,remount /system 2>&1"')
    out = r.stdout.decode('utf-8', errors='ignore').strip()
    err = r.stderr.decode('utf-8', errors='ignore').strip()
    if out or err:
        print(f'  mount输出: {out[:100]} | {err[:100]}')

    # 3. 构造新的hosts内容
    # 保留原内容 + 追加映射
    lines = backup.split('\n') if backup else ['127.0.0.1 localhost']
    # 去重
    existing_hosts = set()
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            existing_hosts.add(parts[1])

    added = 0
    for host, ip in host_ip_pairs:
        if host in existing_hosts:
            continue
        lines.append(f'{ip} {host}')
        existing_hosts.add(host)
        added += 1
    print(f'  新增映射: {added}条')

    # 4. 写入临时文件
    new_hosts = '\n'.join(lines)
    # 写入到sdcard
    r = adb_shell(f"su -c 'echo \"{new_hosts}\" > /sdcard/hosts_new'")
    # 复制到/system/etc/hosts
    r = adb_shell('su -c "cp /sdcard/hosts_new /system/etc/hosts && chmod 644 /system/etc/hosts"')
    print(f'  cp到/system/etc/hosts返回码: {r.returncode}')

    # 5. 验证
    r = adb_shell('su -c "cat /system/etc/hosts"')
    new_content = r.stdout.decode('utf-8', errors='ignore')
    print(f'  新hosts长度: {len(new_content)}')

    # 脱敏输出
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', new_content)
    safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}\b', '[DOMAIN]', safe, flags=re.IGNORECASE)
    print(f'  内容（脱敏）: {safe[:400]}')


def test_source(idx, source_url, wait_sec=15):
    """测试单个源"""
    print(f'\n=== idx={idx} ===')
    adb_shell('logcat -c')
    time.sleep(0.3)

    escaped = source_url.replace("'", "'\\''")
    adb_shell(f"am start -n {DEBUG_ACTIVITY} --es key '{escaped}'")
    time.sleep(wait_sec)

    # 截图
    remote = f'/sdcard/hosttest_{idx}.png'
    adb_shell(f'screencap -p {remote}')
    local = f'f:/myself/github/WeAgentChat/temp/legado/output/rss/each_source_test/hosttest_{idx}.png'
    subprocess.run([ADB, '-s', HOST, 'pull', remote, local], capture_output=True, timeout=10)

    # 拉取logcat
    r = adb_shell('logcat -d -t 1000')
    logcat = r.stdout.decode('utf-8', errors='ignore')

    safe_lines = []
    for line in logcat.split('\n'):
        if any(noise in line for noise in ['ProfileInstaller', 'ClassLoaderContext', 'app_process:', 'HostConnection']):
            continue
        if any(kw in line for kw in ['Exception', 'Error', 'network', 'RssSource', 'rssSource', 'sortUrls',
                                       'AnalyzeUrl', 'OkHttp', 'Cronet', 'ssl', 'SSL', 'timeout', 'reset',
                                       'connect', 'socket', 'http', 'resolve', 'host', 'EAI', 'getaddrinfo',
                                       'Cookie', 'Login', 'Legado']):
            safe = sanitize(line)
            safe = re.sub(r'sourceName=[^\s,]+', 'sourceName=[HIDDEN]', safe)
            safe = re.sub(r'cookie[:=][^\s,;]+', 'cookie=[HIDDEN]', safe, flags=re.IGNORECASE)
            safe = re.sub(r'sourceUrl=[^\s,]+', 'sourceUrl=[HIDDEN]', safe)
            safe_lines.append(safe[:200])

    seen = set()
    unique = []
    for line in safe_lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)

    print(f'  logcat({len(unique)}条):')
    for line in unique[:8]:
        print(f'    {line}')

    # 判定
    has_dns_err = any('resolve host' in line or 'EAI_NODATA' in line or 'getaddrinfo' in line for line in unique)
    has_network_disconnect = any('network is disconnect' in line.lower() for line in unique)
    has_ssl_err = any('ssl' in line.lower() or 'wrong_version' in line.lower() for line in unique)
    has_rss_loaded = any('rssSource' in line.lower() or 'sortUrls' in line for line in unique)
    has_403 = any(' 403 ' in line or 'Forbidden' in line for line in unique)

    if has_dns_err:
        status = 'dns_failed'
    elif has_rss_loaded and not has_network_disconnect:
        status = 'source_loaded'
    elif has_403:
        status = 'http_forbidden'
    elif has_ssl_err:
        status = 'ssl_error'
    elif has_network_disconnect:
        status = 'network_unreachable'
    else:
        status = 'unknown'

    print(f'  状态: {status}')
    return {'idx': idx, 'status': status, 'logcat_top': unique[:5]}


def main():
    print('=' * 70)
    print('hosts映射方案 + 重新测试7个源')
    print('=' * 70)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    # 1. 主机侧解析host得到IP
    host_ip_pairs = resolve_host_ips(sources)
    if not host_ip_pairs:
        print('\n❌ 没有解析到任何IP，退出')
        return

    # 2. 写入模拟器hosts
    write_hosts_file(host_ip_pairs)

    # 3. 重启App
    print('\n--- 重启App ---')
    adb_shell(f'am force-stop {PKG}')
    time.sleep(2)
    adb_shell(f'monkey -p {PKG} -c android.intent.category.LAUNCHER 1')
    time.sleep(5)

    # 4. 逐个测试
    results = []
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        url = sources[idx].get('sourceUrl', '')
        if not url.startswith('http'):
            results.append({'idx': idx, 'status': 'invalid_url'})
            continue
        try:
            r = test_source(idx, url)
            results.append(r)
        except Exception as e:
            print(f'  idx={idx} 异常: {type(e).__name__}')
            results.append({'idx': idx, 'status': 'test_error', 'exception': type(e).__name__})

    # 汇总
    print('\n' + '=' * 70)
    print('汇总（hosts映射后）')
    print('=' * 70)
    success = sum(1 for r in results if r['status'] == 'source_loaded')
    dns_fail = sum(1 for r in results if r['status'] == 'dns_failed')
    net_fail = sum(1 for r in results if r['status'] == 'network_unreachable')
    forbidden = sum(1 for r in results if r['status'] == 'http_forbidden')
    ssl_err = sum(1 for r in results if r['status'] == 'ssl_error')
    other = len(results) - success - dns_fail - net_fail - forbidden - ssl_err
    print(f'  成功加载: {success}/{len(results)}')
    print(f'  DNS失败: {dns_fail}/{len(results)}')
    print(f'  网络不可达: {net_fail}/{len(results)}')
    print(f'  HTTP 403: {forbidden}/{len(results)}')
    print(f'  SSL错误: {ssl_err}/{len(results)}')
    print(f'  其他: {other}/{len(results)}')

    print('\n--- 详情 ---')
    for r in results:
        print(f'  [idx={r.get("idx")}] {r.get("status")}')


if __name__ == '__main__':
    main()
