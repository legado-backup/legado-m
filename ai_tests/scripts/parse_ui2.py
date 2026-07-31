#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析共存包UI XML"""
import xml.etree.ElementTree as ET

tree = ET.parse(r"f:\myself\github\WeAgentChat\temp\legado\output\ui_coexist.xml")
root = tree.getroot()

ctrl_types = {}
texts = []
for node in root.iter():
    tag = node.attrib.get("class", "").split(".")[-1]
    ctrl_types[tag] = ctrl_types.get(tag, 0) + 1
    t = node.attrib.get("text", "")
    d = node.attrib.get("content-desc", "")
    if t and len(t.strip()) > 0:
        texts.append(("text", t[:50]))
    if d and len(d.strip()) > 0:
        texts.append(("desc", d[:50]))

print("[CTRL TYPES]", ctrl_types)
print(f"[TEXT COUNT] {len(texts)}")
for i, (kind, val) in enumerate(texts):
    print(f"  [{i}] {kind}: {val}")
