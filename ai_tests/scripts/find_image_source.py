#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询图片类型订阅源（articleStyle=2）的位置索引
只输出技术字段，源名用源[N]替代
"""
import subprocess
import sys
import os
import sqlite3
import tempfile
import re

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
DEVICE = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"


def pull_db():
    """pull db via su"""
    tmp = os.path.join(tempfile.gettempdir(), "legado_query2.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    # 用 su 复制到 /sdcard/
    subprocess.run([ADB, "-s", DEVICE, "shell",
                    f"su -c 'cp /data/data/{PKG}/databases/legado.db /sdcard/legado_q.db; chmod 666 /sdcard/legado_q.db'"],
                   capture_output=True, timeout=15)
    # pull
    subprocess.run([ADB, "-s", DEVICE, "pull", "/sdcard/legado_q.db", tmp],
                   capture_output=True, timeout=15)
    return tmp


def query(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # 只查询技术字段+源名长度（不输出源名内容）
    print("=== rssSources 表所有源（按 customOrder 排序）===")
    cur.execute("""
        SELECT type, articleStyle, enabled, customOrder,
               length(sourceName) as name_len,
               length(sourceUrl) as url_len,
               length(ruleContent) as content_len,
               length(ruleImage) as image_rule_len,
               length(sortUrl) as sorturl_len,
               length(sourceGroup) as group_len
        FROM rssSources
        WHERE enabled=1
        ORDER BY customOrder ASC
    """)
    rows = cur.fetchall()
    print(f"启用源总数: {len(rows)}")
    img_sources = []
    for i, r in enumerate(rows):
        stype, astyle, enabled, order, name_len, url_len, content_len, image_rule_len, sorturl_len, group_len = r
        marker = ""
        if astyle == 2:
            marker = " *** [图片类型-候选]"
            img_sources.append(i)
        print(f"  idx={i} type={stype} articleStyle={astyle} order={order}"
              f" nameLen={name_len} urlLen={url_len} contentLen={content_len}"
              f" imgRuleLen={image_rule_len} sorturlLen={sorturl_len} groupLen={group_len}{marker}")
    print(f"\n图片类型源数: {len(img_sources)}")
    if img_sources:
        print(f"图片类型源 idx 列表: {img_sources}")
    conn.close()


if __name__ == "__main__":
    print(f"=== Device: {DEVICE} ===")
    db = pull_db()
    if not os.path.exists(db) or os.path.getsize(db) == 0:
        print("[ERROR] pull db failed")
        sys.exit(1)
    print(f"DB size: {os.path.getsize(db)} bytes")
    query(db)
