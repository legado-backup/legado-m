#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析分类页面UI XML"""
import xml.etree.ElementTree as ET

tree = ET.parse(r"f:\myself\github\WeAgentChat\temp\legado\output\ui_category.xml")
root = tree.getroot()

ctrl_types = {}
texts = []
for node in root.iter():
    tag = node.attrib.get("class", "").split(".")[-1]
    ctrl_types[tag] = ctrl_types.get(tag, 0) + 1
    t = node.attrib.get("text", "")
    d = node.attrib.get("content-desc", "")
    if t and len(t.strip()) > 0:
        texts.append(("text", t[:40]))
    if d and len(d.strip()) > 0:
        texts.append(("desc", d[:40]))

print("[CTRL TYPES]", ctrl_types)
print(f"[TEXT COUNT] {len(texts)}")
# 只输出前20个,过滤敏感内容
for i, (kind, val) in enumerate(texts[:20]):
    print(f"  [{i}] {kind}: {val}")
