#!/usr/bin/env python3
r"""ui_explorer.py — UI 探索辅助工具

用于解析 UI dump XML，提取文本、resource-id、bounds 等信息。
不是测试脚本，仅用于 UI 导航探索。

用法：
    ai_tests\venv\Scripts\python.exe ai_tests\scripts\ui_explorer.py [xml_file]
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_ui(xml_path):
    """解析 UI dump XML，输出所有有文本/desc/resource-id 的节点"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    print(f"{'text':30s} {'content-desc':20s} {'resource-id':45s} {'bounds':25s} {'class'}")
    print("-" * 150)
    for node in root.iter('node'):
        text = node.get('text', '')
        desc = node.get('content-desc', '')
        rid = node.get('resource-id', '')
        bounds = node.get('bounds', '')
        cls = node.get('class', '')
        # 只显示有内容的节点
        if text or desc or (rid and 'io.legado' in rid):
            short_cls = cls.split('.')[-1] if cls else ''
            print(f"{text[:30]:30s} {desc[:20]:20s} {rid[:45]:45s} {bounds:25s} {short_cls}")


def main():
    xml_file = sys.argv[1] if len(sys.argv) > 1 else r'f:\myself\github\WeAgentChat\temp\legado\temp\ui_dump2.xml'
    if not Path(xml_file).exists():
        print(f"文件不存在: {xml_file}")
        sys.exit(1)
    parse_ui(xml_file)


if __name__ == "__main__":
    main()
