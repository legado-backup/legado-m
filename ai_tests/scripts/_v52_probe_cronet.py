# -*- coding: utf-8 -*-
"""测试 ADB shell 命令转义 + Cronet 库检查"""
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

def adb_shell_v1(cmd_str, timeout=15):
    """v1: shell=True"""
    full = f'"{ADB}" -s {HOST} shell {cmd_str}'
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    return subprocess.run(full, shell=True, capture_output=True, timeout=timeout, text=False, env=env)

def adb_shell_v2(args, timeout=15):
    """v2: shell=False"""
    cmd = [ADB, '-s', HOST, 'shell'] + args
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False, env=env)

# 测试1: v1 su -c with single quote
print("--- Test1: v1 su -c '...' ---")
r = adb_shell_v1(f"su -c 'ls /data/data/{PKG}/app_cronet/arm64-v8a/ 2>/dev/null'")
print(f"  rc={r.returncode}")
print(f"  stdout={r.stdout.decode('utf-8', errors='replace')!r}")
print(f"  stderr={r.stderr.decode('utf-8', errors='replace')!r}")

# 测试2: v2 args list
print("\n--- Test2: v2 args list ---")
r = adb_shell_v2(['su', '-c', f'ls /data/data/{PKG}/app_cronet/arm64-v8a/ 2>/dev/null'])
print(f"  rc={r.returncode}")
print(f"  stdout={r.stdout.decode('utf-8', errors='replace')!r}")
print(f"  stderr={r.stderr.decode('utf-8', errors='replace')!r}")

# 测试3: 直接 ls 不带 2>/dev/null
print("\n--- Test3: v1 su -c 'ls ...' (no 2>/dev/null) ---")
r = adb_shell_v1(f"su -c 'ls /data/data/{PKG}/app_cronet/arm64-v8a/'")
print(f"  rc={r.returncode}")
print(f"  stdout={r.stdout.decode('utf-8', errors='replace')!r}")
print(f"  stderr={r.stderr.decode('utf-8', errors='replace')!r}")

# 测试4: 不用 su, 直接 ls
print("\n--- Test4: no su, direct ls ---")
r = adb_shell_v1(f"ls /data/data/{PKG}/app_cronet/arm64-v8a/")
print(f"  rc={r.returncode}")
print(f"  stdout={r.stdout.decode('utf-8', errors='replace')!r}")
print(f"  stderr={r.stderr.decode('utf-8', errors='replace')!r}")
