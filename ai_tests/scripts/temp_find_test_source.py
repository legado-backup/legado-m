#!/usr/bin/env python3
"""查询本地 legado.db 找有 loginUrl 且 ruleArticles 非空的源（脱敏输出）"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB = r'f:\myself\github\WeAgentChat\temp\legado\temp\legado_check.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 查找有 loginUrl 且 ruleArticles 非空的源
print('--- sources with loginUrl AND ruleArticles ---')
cur.execute('''
    SELECT sourceUrl, loginUrl, enabledCookieJar,
           length(ruleArticles) as ruleArticlesLen,
           length(ruleNextPage) as ruleNextPageLen,
           length(sortUrl) as sortUrlLen
    FROM rssSources
    WHERE loginUrl IS NOT NULL AND loginUrl != ""
    AND ruleArticles IS NOT NULL AND length(ruleArticles) > 10
''')
rows = cur.fetchall()
print(f'   total: {len(rows)}')
for i, row in enumerate(rows):
    print(f'   [{i}] sourceUrl_len={len(row[0])}, loginUrl_len={len(row[1])}, '
          f'enabledCookieJar={row[2]}, ruleArticlesLen={row[3]}, '
          f'ruleNextPageLen={row[4] if row[4] else 0}, sortUrlLen={row[5] if row[5] else 0}')

# 也查找没有 loginUrl 但有 ruleArticles 的源（作为对照）
print('\n--- sources WITHOUT loginUrl but WITH ruleArticles (control) ---')
cur.execute('''
    SELECT COUNT(*)
    FROM rssSources
    WHERE (loginUrl IS NULL OR loginUrl = "")
    AND ruleArticles IS NOT NULL AND length(ruleArticles) > 10
''')
print(f'   total: {cur.fetchone()[0]}')

conn.close()
print('\nDone!')
