"""临时查询DB weight"""
import sqlite3
conn = sqlite3.connect('ai_tests/reports/feature_test/db_pull/legado.db')
cur = conn.cursor()
results = []
try:
    cur.execute('SELECT COUNT(*) FROM book_sources')
    results.append(f'book_sources count: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM book_sources WHERE weight > 0')
    results.append(f'book_sources weight>0: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM book_sources WHERE weight = 0')
    results.append(f'book_sources weight=0: {cur.fetchone()[0]}')
    cur.execute('SELECT MIN(weight), MAX(weight), AVG(weight) FROM book_sources')
    min_w, max_w, avg_w = cur.fetchone()
    results.append(f'book_sources weight range: min={min_w}, max={max_w}, avg={avg_w}')
except Exception as e:
    results.append(f'book_sources error: {e}')
try:
    cur.execute('SELECT COUNT(*) FROM rss_sources')
    results.append(f'rss_sources count: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM rss_sources WHERE weight > 0')
    results.append(f'rss_sources weight>0: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM rss_sources WHERE weight = 0')
    results.append(f'rss_sources weight=0: {cur.fetchone()[0]}')
except Exception as e:
    results.append(f'rss_sources error: {e}')
conn.close()

with open('ai_tests/reports/feature_test/db_pull/query_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
print('\n'.join(results))
