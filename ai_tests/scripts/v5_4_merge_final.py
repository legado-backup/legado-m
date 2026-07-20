#!/usr/bin/env python3
r"""v5_4_merge_final.py — 合并 cleaned JSON + 修复后源，生成最终 JSON

输入：
- output/rss/optimized_v5_4_cleaned.json（184 源）
- output/rss/v5_4_fixed_sources.json（31 个修复后的源对象列表）

输出：
- output/rss/optimized_v5_4_final.json（184 源，31 个被修复源覆盖）

匹配方式：用 sourceUrl 作为唯一键，覆盖 cleaned JSON 中对应的源。

安全规范：禁止输出源名称/URL/cookie，全部用 idx 编号。
"""
import json
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
CLEANED_JSON = ROOT / "output" / "rss" / "optimized_v5_4_cleaned.json"
FIXED_SOURCES = ROOT / "output" / "rss" / "v5_4_fixed_sources.json"
OUT_JSON = ROOT / "output" / "rss" / "optimized_v5_4_final.json"
OUT_REPORT = ROOT / "output" / "rss" / "v5_4_merge_report.json"


def main():
    print("=" * 70)
    print("v5_4 合并 cleaned + fixed → 最终 JSON")
    print("=" * 70)

    # === 1. 加载 cleaned JSON ===
    print(f"\n[1/3] 加载 cleaned JSON: {CLEANED_JSON.name}")
    with open(CLEANED_JSON, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)
    print(f"     cleaned 源数: {len(cleaned)}")
    print(f"     enabled: {sum(1 for s in cleaned if s.get('enabled'))}")

    # === 2. 加载修复后源 ===
    print(f"\n[2/3] 加载修复后源: {FIXED_SOURCES.name}")
    with open(FIXED_SOURCES, 'r', encoding='utf-8') as f:
        fixed = json.load(f)
    print(f"     修复源数: {len(fixed)}")

    # 构建 sourceUrl → fixed_source 映射
    fixed_map = {}
    for fs in fixed:
        url = fs.get('sourceUrl', '')
        if url:
            fixed_map[url] = fs
    print(f"     修复源 URL 去重数: {len(fixed_map)}")

    # === 3. 合并：用修复源覆盖 cleaned 中对应的源 ===
    print(f"\n[3/3] 合并覆盖")
    final_sources = []
    stats = Counter()
    replaced_positions = []
    for i, src in enumerate(cleaned):
        url = src.get('sourceUrl', '')
        if url in fixed_map:
            # 用修复后的源覆盖
            final_sources.append(fixed_map[url])
            stats['replaced'] += 1
            replaced_positions.append(i)
        else:
            # 保留原源
            final_sources.append(src)
            stats['kept'] += 1

    # 统计最终 enabled/disabled
    final_enabled = sum(1 for s in final_sources if s.get('enabled'))
    final_disabled = len(final_sources) - final_enabled

    print(f"     合并结果: 替换={stats['replaced']} | 保留={stats['kept']}")
    print(f"     最终源数: {len(final_sources)}")
    print(f"     enabled: {final_enabled} | disabled: {final_disabled}")

    # 写入最终 JSON
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)
    print(f"     已输出: {OUT_JSON}")

    # 写入合并报告
    report = {
        'input_cleaned_count': len(cleaned),
        'input_fixed_count': len(fixed),
        'replaced_count': stats['replaced'],
        'kept_count': stats['kept'],
        'output_total': len(final_sources),
        'output_enabled': final_enabled,
        'output_disabled': final_disabled,
        'replaced_positions': replaced_positions,
        'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"     已输出报告: {OUT_REPORT}")

    print("\n✅ 合并完成")


if __name__ == '__main__':
    main()
