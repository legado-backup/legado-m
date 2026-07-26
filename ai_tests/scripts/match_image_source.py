#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
匹配 UI 中的图片源分类（不输出业务文本，只输出位置+长度+是否图片源）
"""
import subprocess
import sys
import os
import sqlite3
import tempfile
import re
import xml.etree.ElementTree as ET

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
DEVICE = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"


def pull_db():
    tmp = os.path.join(tempfile.gettempdir(), "legado_match.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    subprocess.run([ADB, "-s", DEVICE, "shell",
                    f"su -c 'cp /data/data/{PKG}/databases/legado.db /sdcard/legado_m.db; chmod 666 /sdcard/legado_m.db'"],
                   capture_output=True, timeout=15)
    subprocess.run([ADB, "-s", DEVICE, "pull", "/sdcard/legado_m.db", tmp],
                   capture_output=True, timeout=15)
    return tmp


def parse_image_sources(db_path):
    """返回 articleStyle=2 的源的 sortUrl 中所有分类名长度列表"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT sourceUrl, sortUrl, articleStyle, length(sourceName)
        FROM rssSources
        WHERE enabled=1 AND articleStyle=2
    """)
    rows = cur.fetchall()
    result = []
    for r in rows:
        surl, sort_url, astyle, name_len = r
        # 解析 sortUrl 中的分类名
        # 格式: "分类名1::url1\n分类名2::url2" 或 "分类名1::url1,分类名2::url2"
        categories = []
        if sort_url:
            # 用换行或逗号分隔
            for line in re.split(r'[\n,]', sort_url):
                if '::' in line:
                    cat_name = line.split('::')[0]
                    categories.append(len(cat_name))
        result.append({
            'url_len': len(surl) if surl else 0,
            'name_len': name_len or 0,
            'sort_url_len': len(sort_url) if sort_url else 0,
            'category_count': len(categories),
            'category_name_lens': categories
        })
    conn.close()
    return result


def parse_ui_categories(xml_path):
    """解析 UI 中 RecyclerView 的所有分类项"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    categories = []
    for e in root.iter("node"):
        rid = e.get("resource-id", "")
        if rid.endswith("tv_title") or rid == "tv_title":
            text = e.get("text", "")
            b = e.get("bounds", "")
            center = ""
            if b:
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    center = f"{cx},{cy}"
            categories.append({
                'text_len': len(text),
                'center': center
            })
    return categories


def match(img_sources, ui_cats):
    """匹配图片源分类与 UI 分类（按 textlen 匹配）"""
    print("\n=== 匹配结果 ===")
    for i, src in enumerate(img_sources):
        print(f"\n图片源[{i}]: nameLen={src['name_len']}, urlLen={src['url_len']}, "
              f"sortUrlLen={src['sort_url_len']}, categoryCount={src['category_count']}")
        print(f"  分类名长度列表: {src['category_name_lens']}")
        # 在 UI 中找 textlen 匹配的分类
        for cat_len in src['category_name_lens']:
            matched = [c for c in ui_cats if c['text_len'] == cat_len]
            if matched:
                for m in matched:
                    print(f"  -> UI匹配: textlen={cat_len}, center=({m['center']}), 建议点击此位置")


if __name__ == "__main__":
    print(f"=== Device: {DEVICE} ===")
    db = pull_db()
    if not os.path.exists(db) or os.path.getsize(db) == 0:
        print("[ERROR] pull db failed")
        sys.exit(1)

    img_sources = parse_image_sources(db)
    print(f"图片源数: {len(img_sources)}")

    xml_path = "f:/myself/github/WeAgentChat/temp/legado/temp/ui.xml"
    if not os.path.exists(xml_path):
        print(f"[ERROR] ui.xml not found: {xml_path}")
        sys.exit(1)
    ui_cats = parse_ui_categories(xml_path)
    print(f"UI分类数: {len(ui_cats)}")
    for i, c in enumerate(ui_cats):
        print(f"  UI[{i}]: textlen={c['text_len']}, center=({c['center']})")

    match(img_sources, ui_cats)
