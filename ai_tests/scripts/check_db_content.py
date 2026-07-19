#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'output/rss/check_db2.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM rssSources')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=0')
web = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=1')
img = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE type=2')
vid = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM rssSources WHERE enabled=1')
en = c.fetchone()[0]
print(f'Total: {total}, type0_web: {web}, type1_image: {img}, type2_video: {vid}, enabled: {en}')
conn.close()
