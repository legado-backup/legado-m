#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全解析 UI XML（只输出技术字段+源ID编号，过滤业务文本）
"""
import sys
import re
import xml.etree.ElementTree as ET

# 源ID映射（避免输出真实源名）
SOURCE_MAP = {}

def parse_safe(xml_path):
    """只输出技术字段，源名用源[N]替代"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = []
    src_idx = 0
    for e in root.iter("node"):
        rid = e.get("resource-id", "")
        cls = e.get("class", "").split(".")[-1]
        b = e.get("bounds", "")
        c = e.get("clickable", "false")
        text = e.get("text", "")
        # 提取中心点
        center = ""
        if b:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                center = f"({cx},{cy})"
        # 源名替换为源[N]
        display_text = ""
        if text and len(text.strip()) > 0:
            # 检测是否是源名（短文本）
            if len(text) < 50 and not text.startswith("搜索"):
                src_idx += 1
                SOURCE_MAP[src_idx] = text
                display_text = f" text=源[{src_idx}]"
            elif text.startswith("搜索"):
                display_text = f" text=[搜索框]"
            else:
                display_text = f" textlen={len(text)}"
        # 只输出可点击元素或关键容器
        if c == "true" or "RecyclerView" in cls or "ImageView" in cls or "Tab" in cls or display_text:
            short_rid = rid.split(":id/")[-1] if ":id/" in rid else rid
            result.append(f"cls={cls:<18} rid={short_rid:<30} click={c:<5} center={center:<12}{display_text}")
    return result

if __name__ == "__main__":
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "temp/ui.xml"
    print(f"=== XML: {xml_path} ===")
    try:
        lines = parse_safe(xml_path)
        print(f"=== Nodes: {len(lines)} ===")
        for line in lines:
            print(line)
        print(f"\n=== 源ID映射表（仅技术分析用）===")
        for k, v in SOURCE_MAP.items():
            print(f"  源[{k}] -> textlen={len(v)}")
    except Exception as e:
        print(f"ERROR: {e}")
