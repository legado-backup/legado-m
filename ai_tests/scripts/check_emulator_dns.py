#!/usr/bin/env python3
"""check_emulator_dns.py — 检查模拟器DNS配置+测试8.8.8.8能否解析"""
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'


def adb_shell(cmd, timeout=15):
    full = f'"{ADB}" -s {HOST} shell {cmd}'
    return subprocess.run(full, shell=True, capture_output=True, timeout=timeout, text=False)


def main():
    print('=' * 60)
    print('模拟器DNS配置检查')
    print('=' * 60)

    # 1. 检查当前DNS配置
    print('\n--- 当前DNS配置 ---')
    r = adb_shell('getprop net.dns1')
    print(f'  net.dns1: {r.stdout.decode("utf-8", errors="ignore").strip()}')
    r = adb_shell('getprop net.dns2')
    print(f'  net.dns2: {r.stdout.decode("utf-8", errors="ignore").strip()}')
    r = adb_shell('getprop dns.pdns1')
    print(f'  dns.pdns1: {r.stdout.decode("utf-8", errors="ignore").strip()}')

    # 2. 检查网络接口
    print('\n--- 网络接口DNS ---')
    r = adb_shell('ip addr show eth0 2>/dev/null || ifconfig eth0')
    out = r.stdout.decode('utf-8', errors='ignore')
    # 脱敏：替换IP
    import re
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', out)
    print(f'  eth0: {safe[:300]}')

    # 3. 检查resolve.conf
    print('\n--- /system/etc/resolv.conf ---')
    r = adb_shell('cat /system/etc/resolv.conf 2>/dev/null')
    out = r.stdout.decode('utf-8', errors='ignore')
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', out)
    print(f'  {safe[:200]}')

    # 4. 检查hosts
    print('\n--- /system/etc/hosts ---')
    r = adb_shell('cat /system/etc/hosts 2>/dev/null')
    out = r.stdout.decode('utf-8', errors='ignore')
    # 脱敏：替换IP和域名
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', out)
    safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}\b', '[DOMAIN]', safe, flags=re.IGNORECASE)
    print(f'  {safe[:300]}')

    # 5. 尝试设置DNS为8.8.8.8
    print('\n--- 尝试设置DNS为8.8.8.8/1.1.1.1 ---')
    r1 = adb_shell('setprop net.dns1 8.8.8.8')
    r2 = adb_shell('setprop net.dns2 1.1.1.1')
    print(f'  setprop net.dns1 rc={r1.returncode}')
    print(f'  setprop net.dns2 rc={r2.returncode}')

    # 验证
    r = adb_shell('getprop net.dns1')
    print(f'  验证 net.dns1: {r.stdout.decode("utf-8", errors="ignore").strip()}')

    # 6. 用nslookup测试（如果有）
    print('\n--- nslookup测试（如果可用） ---')
    r = adb_shell('which nslookup 2>/dev/null || ls /system/bin/nslookup 2>/dev/null')
    out = r.stdout.decode('utf-8', errors='ignore')
    if 'nslookup' in out:
        print(f'  nslookup可用')
    else:
        print(f'  nslookup不可用')

    # 7. ping测试（不输出域名，只看是否可达）
    print('\n--- ping 8.8.8.8测试 ---')
    r = adb_shell('ping -c 3 8.8.8.8 2>&1')
    out = r.stdout.decode('utf-8', errors='ignore')
    # 只输出统计信息
    safe = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', out)
    print(f'  ping结果: {safe[:500]}')


if __name__ == '__main__':
    main()
