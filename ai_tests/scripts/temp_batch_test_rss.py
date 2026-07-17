#!/usr/bin/env python3
"""批量测试所有有 loginUrl 的源，找出列表为空的源（脱敏：不输出源名称/URL内容）"""
import subprocess
import sys
import sqlite3
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
DB = r'f:\myself\github\WeAgentChat\temp\legado\temp\query_db.db'

def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)

def sanitize(line):
    """脱敏：移除完整 URL"""
    return re.sub(r'https?://[^\s,]+', '[URL]', line)

# 1. 查询所有有 loginUrl 的源
print('--- query sources with loginUrl ---')
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('''
    SELECT sourceUrl, length(sourceUrl) as url_len
    FROM rssSources
    WHERE loginUrl IS NOT NULL AND loginUrl != ''
    AND length(sourceUrl) > 10
    ORDER BY url_len
''')
sources = cur.fetchall()
conn.close()
print(f'  found {len(sources)} sources with loginUrl')

results = []

for idx, (source_url, url_len) in enumerate(sources):
    print(f'\n--- [{idx+1}/{len(sources)}] testing source (url_len={url_len}) ---')

    # 启动 RssSortActivity
    adb('shell', 'am', 'start', '-n',
        PKG + '/io.legado.app.ui.rss.article.RssSortActivity',
        '--es', 'sourceUrl', source_url)
    time.sleep(2)

    # 清空 logcat
    adb('logcat', '-c')

    # 下拉刷新
    adb('shell', 'input', 'swipe', '800', '500', '800', '900', '400')
    time.sleep(10)

    # 抓取 sourceDebug 日志
    r = adb('logcat', '-d', '-s', 'sourceDebug:D', timeout=10)
    logs = r.stdout.decode('utf-8', errors='replace')

    # 解析列表大小
    list_size = -1
    has_error = False
    error_msg = ''
    body_preview = ''
    for line in logs.split('\n'):
        if '列表大小' in line:
            m = re.search(r'列表大小:(\d+)', line)
            if m:
                list_size = int(m.group(1))
        if '获取成功' in line:
            # 提取路径片段（脱敏）
            m = re.search(r'获取成功:(.{0,40})', line)
            if m:
                body_preview = m.group(1)[:30]
        if 'RSS列表项解析失败' in line or 'error' in line.lower():
            has_error = True
            error_msg = sanitize(line)[:100]

    # 抓取 AppLog 中的错误
    r2 = adb('logcat', '-d', '-s', 'Legado:I', timeout=10)
    app_logs = r2.stdout.decode('utf-8', errors='replace')
    parse_fail_count = app_logs.count('RSS列表项解析失败')
    decompress_warn = 'unknown encoding' in app_logs

    status = 'OK' if list_size > 0 else ('EMPTY' if list_size == 0 else 'UNKNOWN')
    results.append((idx, url_len, status, list_size, parse_fail_count, decompress_warn, body_preview))
    print(f'  status={status}, listSize={list_size}, parseFail={parse_fail_count}, decompressWarn={decompress_warn}')

    # 返回桌面（避免堆积 Activity）
    adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
    time.sleep(1)
    adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
    time.sleep(1)

# 汇总
print('\n' + '='*60)
print('=== SUMMARY ===')
print('='*60)
for idx, url_len, status, list_size, parse_fail, decompress_warn, _ in results:
    print(f'  [{idx}] url_len={url_len}, status={status}, listSize={list_size}, parseFail={parse_fail}, decompressWarn={decompress_warn}')

# 找出空列表的源
empty_sources = [r for r in results if r[2] == 'EMPTY']
print(f'\n=== EMPTY sources: {len(empty_sources)} ===')
for idx, url_len, _, list_size, parse_fail, decompress_warn, _ in empty_sources:
    print(f'  [{idx}] url_len={url_len}, listSize={list_size}, parseFail={parse_fail}, decompressWarn={decompress_warn}')

print('\n=== Done ===')
