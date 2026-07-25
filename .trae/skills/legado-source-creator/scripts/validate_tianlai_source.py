#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验站点A视频订阅源JSON"""
import sys
import os
import json

# 添加 skill scripts 路径
sys.path.insert(0, os.path.join(".trae", "skills", "legado-source-creator", "scripts"))

from legado_client.utils.file_utils import sanitize_source_json
from legado_client.validator import validate_source, format_validation_report


def main():
    source_path = "output/ai_source/rss/rssSource_video_tianlai_20260725.json"

    print(f"[1/3] 读取源JSON: {source_path}")
    with open(source_path, "r", encoding="utf-8") as f:
        sources = json.load(f)
    source = sources[0]
    print(f"    源名称: {source.get('sourceName')}")
    print(f"    源URL: {source.get('sourceUrl')}")

    print("[2/3] sanitize 清理 None 值")
    sanitized = sanitize_source_json(source)
    # 检查是否有 None 残留
    none_fields = [k for k, v in sanitized.items() if v is None]
    if none_fields:
        print(f"    WARNING: 仍有None字段: {none_fields}")
    else:
        print("    OK: 无None残留")

    print("[3/3] MandatoryFieldValidator 校验（strict_recommended=True）")
    result = validate_source(sanitized, source_type='rss', strict_recommended=True)
    report = format_validation_report(result)
    print(report)

    if result['passed']:
        print("\n✅ 校验通过")
        # 写回校验后的源
        with open(source_path, "w", encoding="utf-8") as f:
            json.dump([sanitized], f, ensure_ascii=False, indent=2)
        print(f"   已写回校验后的源到: {source_path}")
    else:
        print("\n❌ 校验失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
