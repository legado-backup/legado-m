#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询 rssArticles NOT NULL 列"""
import sqlite3
import tempfile
import os

tmp_db = os.path.join(tempfile.gettempdir(), "legado_modify.db")
conn = sqlite3.connect(tmp_db)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(rssArticles)")
for row in cursor.fetchall():
    notnull = "NOT NULL" if row[3] else "NULLABLE"
    default = f"default={row[4]}" if row[4] is not None else ""
    print(f"  {row[1]} ({row[2]}) {notnull} {default}")
conn.close()
