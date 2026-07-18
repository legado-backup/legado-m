#!/usr/bin/env python3
"""ping_test_in_emulator.py — 在模拟器内ping域名验证DNS解析
不依赖/system可写，用ping看DNS能否解析"""
import json
import re
import subprocess
import sys
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
NEEDS_LOGIN_IDX = [21, 24, 30, 36, 39, 55, 58]


def adb_shell(cmd, timeout=15):
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


def main():
    print('=' * 60)
    print('模拟器内DNS解析验证')
    print('=' * 60)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    # 1. 先ping 8.8.8.8确认网络通
    print('\n--- ping 8.8.8.8 确认网络通 ---')
    r = adb_shell('ping -c 2 8.8.8.8')
    out = r.stdout.decode('utf-8', errors='ignore')
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', out)
    # 只输出统计
    for line in safe.split('\n'):
        if 'packet loss' in line or 'PING' in line:
            print(f'  {line.strip()}')

    # 2. 逐个测试域名解析（ping -c 1 看是否能解析出IP）
    print('\n--- 模拟器内DNS解析测试 ---')
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        url = sources[idx].get('sourceUrl', '')
        if not url.startswith('http'):
            continue
        try:
            host = urlparse(url).hostname
            # ping -c 1 host 看是否能解析
            r = adb_shell(f'ping -c 1 -W 3 {host}')
            out = r.stdout.decode('utf-8', errors='ignore')
            # 检查是否解析成功
            has_ip = bool(re.search(r'PING\s+\S+\s+\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', out))
            has_failed = 'unknown host' in out.lower() or 'bad address' in out.lower() or 'not known' in out.lower()
            has_timeout = '100% packet loss' in out

            if has_ip and not has_failed:
                # 提取解析出的IP（脱敏）
                m = re.search(r'PING\s+\S+\s+\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', out)
                resolved_ip = m.group(1) if m else ''
                # ping结果
                if has_timeout:
                    status = 'dns_ok_ping_timeout'
                else:
                    status = 'dns_ok_ping_ok'
                print(f'  idx={idx} host_len={len(host)} status={status}')
            else:
                status = 'dns_failed'
                # 输出错误信息（脱敏）
                safe_out = sanitize(out)
                # 提取关键错误行
                err_lines = [l for l in safe_out.split('\n') if 'unknown' in l.lower() or 'bad address' in l.lower() or 'not known' in l.lower()]
                err_msg = err_lines[0][:100] if err_lines else 'unknown error'
                print(f'  idx={idx} host_len={len(host)} status={status} err={err_msg}')

        except Exception as e:
            print(f'  idx={idx} 异常: {type(e).__name__}')

    # 3. 检查DNS缓存（如果有）
    print('\n--- 检查是否有DNS缓存服务 ---')
    r = adb_shell('ps | grep -i dns')
    out = r.stdout.decode('utf-8', errors='ignore')
    print(f'  DNS相关进程: {out[:200] if out else "无"}')

    # 4. 检查netd服务
    print('\n--- netd服务状态 ---')
    r = adb_shell('ps | grep netd')
    out = r.stdout.decode('utf-8', errors='ignore')
    print(f'  netd进程: {out[:200] if out else "无"}')


if __name__ == '__main__':
    main()
