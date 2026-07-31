#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析UI XML,只输出技术结构(控件类型/数量/标题栏文字),不输出业务数据"""
import xml.etree.ElementTree as ET
import re

tree = ET.parse(r"f:\myself\github\WeAgentChat\temp\legado\output\ui_search.xml")
root = tree.getroot()

# 统计控件类型
ctrl_types = {}
texts = []
for node in root.iter():
    tag = node.attrib.get("class", "").split(".")[-1]
    ctrl_types[tag] = ctrl_types.get(tag, 0) + 1
    t = node.attrib.get("text", "")
    d = node.attrib.get("content-desc", "")
    if t and len(t.strip()) > 0:
        texts.append(("text", t[:30]))
    if d and len(d.strip()) > 0:
        texts.append(("desc", d[:30]))

print("[CTRL TYPES]", ctrl_types)
print(f"[TEXT COUNT] {len(texts)}")
for i, (kind, val) in enumerate(texts[:15]):
    # 过滤可能的敏感内容,只显示前30字符
    print(f"  [{i}] {kind}: {val}")
