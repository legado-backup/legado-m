#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询 rssArticles 表结构"""
import sqlite3
import tempfile
import os

tmp_db = os.path.join(tempfile.gettempdir(), "legado_modify.db")
if not os.path.exists(tmp_db):
    print("数据库不存在")
    exit(1)

conn = sqlite3.connect(tmp_db)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(rssArticles)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")
conn.close()
