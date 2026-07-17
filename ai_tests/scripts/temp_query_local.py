#!/usr/bin/env python3
"""查询本地 legado.db cookies 表"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB = r'f:\myself\github\WeAgentChat\temp\legado\temp\legado_check.db'

print(f'Opening {DB}...')
conn = sqlite3.connect(DB)
cur = conn.cursor()

# query cookies table
print('\n--- cookies table ---')
try:
    cur.execute('SELECT url, length(cookie) as cookie_len FROM cookies')
    rows = cur.fetchall()
    print(f'   total cookies: {len(rows)}')
    for row in rows:
        url_prefix = row[0][:3] if row[0] else ''
        print(f'   url_prefix={url_prefix}, url_len={len(row[0])}, cookie_len={row[1]}')
except Exception as e:
    print(f'   Error: {e}')

# query rssSources with loginUrl
print('\n--- rssSources with loginUrl ---')
try:
    cur.execute('SELECT sourceUrl, loginUrl, enabledCookieJar FROM rssSources WHERE loginUrl IS NOT NULL AND loginUrl != ""')
    rows = cur.fetchall()
    print(f'   total: {len(rows)}')
    for row in rows:
        print(f'   sourceUrl_len={len(row[0])}, loginUrl_len={len(row[1])}, enabledCookieJar={row[2]}')
except Exception as e:
    print(f'   Error: {e}')

# query all rssSources count
print('\n--- rssSources count ---')
try:
    cur.execute('SELECT COUNT(*) FROM rssSources')
    print(f'   total: {cur.fetchone()[0]}')
except Exception as e:
    print(f'   Error: {e}')

conn.close()
print('\nDone!')
