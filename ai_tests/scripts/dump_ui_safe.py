#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全 dump UI 结构（过滤 text 属性，避免输出业务数据）
只输出 resource-id、class、bounds、clickable，用于定位点击坐标
"""
import subprocess
import sys
import os
import xml.etree.ElementTree as ET

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"

def dump_ui():
    """dump 当前 UI 到本地 XML 文件"""
    remote = "/data/local/tmp/ui_dump.xml"
    subprocess.run([ADB, "-s", DEVICE, "shell", "uiautomator", "dump", remote],
                  capture_output=True, text=True, encoding="utf-8", errors="replace")
    local = os.path.join(os.environ.get("TEMP", "/tmp"), "ui_dump.xml")
    subprocess.run([ADB, "-s", DEVICE, "pull", remote, local],
                  capture_output=True, text=True, encoding="utf-8", errors="replace")
    return local

def parse_xml_safe(xml_path):
    """解析 XML，只输出安全字段（resource-id/class/bounds/clickable），过滤 text/content-desc"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = []
    for elem in root.iter("node"):
        rid = elem.get("resource-id", "")
        cls = elem.get("class", "")
        bounds = elem.get("bounds", "")
        clickable = elem.get("clickable", "false")
        # 只输出可点击元素或 RecyclerView/ListView 子项
        if clickable == "true" or "RecyclerView" in cls or "ListView" in cls or "TextView" in cls:
            # 简化 class 名
            short_cls = cls.split(".")[-1] if cls else ""
            # 提取 bounds 中心点
            center = ""
            if bounds:
                try:
                    # [x1,y1][x2,y2]
                    import re
                    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                    if m:
                        x1, y1, x2, y2 = map(int, m.groups())
                        cx, cy = (x1+x2)//2, (y1+y2)//2
                        center = f"center=({cx},{cy})"
                except:
                    pass
            # rid 只保留最后部分
            short_rid = rid.split(":id/")[-1] if ":id/" in rid else rid
            result.append(f"  cls={short_cls:<20} rid={short_rid:<30} clickable={clickable:<5} {center}")
    return result

def main():
    print("[Step 1] dump UI...")
    xml_path = dump_ui()
    if not os.path.exists(xml_path):
        print("ERROR: dump 失败")
        return 1
    print(f"  -> {xml_path}")

    print("\n[Step 2] 解析（已过滤 text/content-desc）...")
    lines = parse_xml_safe(xml_path)
    for line in lines:
        print(line)

    # 统计可点击元素数量
    clickable_count = sum(1 for l in lines if "clickable=true" in l)
    print(f"\n[统计] 可点击元素: {clickable_count} 个")

    return 0

if __name__ == "__main__":
    sys.exit(main())
