# -*- coding: utf-8 -*-
"""u2 底部导航探针：仅输出 resource-id/content-desc 技术字段（不输出业务文本）
video-sniff-403-and-rss-classic-fix 6.7 固化辅助：l2_verify_video_player 导航选择器适配排查
"""
import re
import sys

import uiautomator2 as u2


def main():
    d = u2.connect()
    print("device:", d.serial)
    xml = d.dump_hierarchy()
    ids = sorted(set(re.findall(r'resource-id="([^"]*(?:rss|menu|tab|nav)[^"]*)"', xml, re.I)))
    descs = sorted({x[:24] for x in re.findall(r'content-desc="([^"]+)"', xml)})
    texts = sorted({x[:16] for x in re.findall(r'text="([^"]{1,16})"', xml)})
    print("IDS(", len(ids), "):", ids)
    print("DESCS(", len(descs), "):", descs[:40])
    print("TEXTS(", len(texts), "):", texts[:40])
    # 底部导航栏区域（屏高下 15%）节点 id/desc 概览
    m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    print("activity:", d.app_current().get("activity", "?"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
