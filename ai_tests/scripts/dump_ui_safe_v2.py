#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全 dump UI 结构 v2（支持指定设备）
只输出技术字段（resource-id/class/bounds/clickable），过滤 text/content-desc
用法: python dump_ui_safe_v2.py [device_id]
"""
import subprocess
import sys
import os
import xml.etree.ElementTree as ET

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
DEVICE = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:21513"
PKG = "io.legado.miss.app.debug"


def run_adb(cmd):
    r = subprocess.run([ADB, "-s", DEVICE] + cmd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    return r.stdout + r.stderr


def dump_ui():
    remote = "/sdcard/ui.xml"
    run_adb(["shell", "uiautomator", "dump", remote])
    local = os.path.join(os.path.dirname(__file__), "..", "..", "temp", "ui.xml")
    local = os.path.abspath(local)
    run_adb(["pull", remote, local])
    return local


def parse_safe(xml_path):
    """只输出技术字段，过滤 text/content-desc"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = []
    for e in root.iter("node"):
        rid = e.get("resource-id", "")
        cls = e.get("class", "").split(".")[-1]
        b = e.get("bounds", "")
        c = e.get("clickable", "false")
        # 提取中心点
        center = ""
        if b:
            import re
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                center = f"({cx},{cy})"
        # 只输出可点击元素或关键容器
        if c == "true" or "RecyclerView" in cls or "ImageView" in cls or "Tab" in cls:
            result.append(f"rid={rid[:60]}|cls={cls}|center={center}|click={c}")
    return result


if __name__ == "__main__":
    print(f"=== Device: {DEVICE} ===")
    xml_path = dump_ui()
    if not os.path.exists(xml_path):
        print(f"[ERROR] XML not found: {xml_path}")
        sys.exit(1)
    print(f"=== XML: {xml_path} (size={os.path.getsize(xml_path)}) ===")
    lines = parse_safe(xml_path)
    print(f"=== Nodes: {len(lines)} ===")
    for line in lines:
        print(line)
