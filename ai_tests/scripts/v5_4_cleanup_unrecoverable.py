#!/usr/bin/env python3
r"""v5_4_cleanup_unrecoverable.py — 清理 40 个不可恢复源

输入：
- output/rss/optimized_v5_3_final.json（224 源，71 enabled + 153 disabled）
- output/rss/v5_3_debug_verify_result.json（71 enabled 源的 5 维度验证结果）

清理目标（40 个不可恢复）：
- 38 个 DNS 失败（站点已下线，errors 含 network:dns_fail）
- 2 个 URL 格式错误（errors 含 network:malformed_url）

输出：
- output/rss/optimized_v5_4_cleaned.json（184 源，含 31 个待修复源）
- output/rss/v5_4_cleanup_report.json（清理统计 + 移除源 idx 清单）

安全规范：禁止输出源名称/URL/cookie，全部用 idx 编号。
"""
import json
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
SRC_JSON = ROOT / "output" / "rss" / "optimized_v5_3_final.json"
VERIFY_JSON = ROOT / "output" / "rss" / "v5_3_debug_verify_result.json"
OUT_JSON = ROOT / "output" / "rss" / "optimized_v5_4_cleaned.json"
OUT_REPORT = ROOT / "output" / "rss" / "v5_4_cleanup_report.json"

# 不可恢复的错误标记
UNRECOVERABLE_ERROR_MARKERS = {
    "network:dns_fail",        # DNS 解析失败（站点已下线）
    "network:malformed_url",   # URL 格式错误
}


def main():
    print("=" * 70)
    print("v5_4 清理 40 个不可恢复源")
    print("=" * 70)

    # === 1. 加载 V5.3 最终 JSON ===
    print(f"\n[1/4] 加载 V5.3 JSON: {SRC_JSON.name}")
    with open(SRC_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f"     源总数: {len(sources)}")
    enabled_count = sum(1 for s in sources if s.get('enabled'))
    disabled_count = len(sources) - enabled_count
    print(f"     enabled: {enabled_count} | disabled: {disabled_count}")

    # === 2. 加载 V5.3 验证结果 ===
    print(f"\n[2/4] 加载验证结果: {VERIFY_JSON.name}")
    with open(VERIFY_JSON, 'r', encoding='utf-8') as f:
        verify = json.load(f)
    print(f"     验证源数: {verify.get('total', 0)}")

    # === 3. 映射 verify idx → 原始 JSON 位置 ===
    # verify idx 对应 enabled_sources 数组的索引（按 enabled 顺序）
    enabled_positions = [i for i, s in enumerate(sources) if s.get('enabled')]
    print(f"     enabled 源在 JSON 中的位置数: {len(enabled_positions)}")

    # 找出所有不可恢复源的 verify idx
    unrecoverable_verify_idxs = []
    unrecoverable_reasons = {}  # verify_idx -> [reasons]
    for r in verify.get('results', []):
        vidx = r.get('idx')
        errors = r.get('errors', [])
        matched = [e for e in errors if e in UNRECOVERABLE_ERROR_MARKERS]
        if matched:
            unrecoverable_verify_idxs.append(vidx)
            unrecoverable_reasons[vidx] = matched

    print(f"\n[3/4] 识别不可恢复源")
    print(f"     不可恢复 verify_idx 数: {len(unrecoverable_verify_idxs)}")

    # 按错误类型统计
    reason_counter = Counter()
    for vidx, reasons in unrecoverable_reasons.items():
        for r in reasons:
            reason_counter[r] += 1
    for reason, cnt in reason_counter.most_common():
        print(f"     {reason}: {cnt} 个")

    # 映射到原始 JSON 位置
    unrecoverable_json_positions = set()
    for vidx in unrecoverable_verify_idxs:
        if vidx < len(enabled_positions):
            json_pos = enabled_positions[vidx]
            unrecoverable_json_positions.add(json_pos)

    print(f"     不可恢复源在原 JSON 中位置数: {len(unrecoverable_json_positions)}")

    # === 4. 移除不可恢复源 ===
    print(f"\n[4/4] 移除不可恢复源，输出 cleaned JSON")
    cleaned_sources = []
    removed_log = []  # [{json_pos, verify_idx, reasons}]
    for i, src in enumerate(sources):
        if i in unrecoverable_json_positions:
            # 找到对应的 verify_idx
            vidx = None
            for vi, jp in enumerate(enabled_positions):
                if jp == i:
                    vidx = vi
                    break
            removed_log.append({
                'json_pos': i,
                'verify_idx': vidx,
                'reasons': unrecoverable_reasons.get(vidx, []),
            })
        else:
            cleaned_sources.append(src)

    print(f"     移除源数: {len(removed_log)}")
    print(f"     保留源数: {len(cleaned_sources)}")

    # 写入 cleaned JSON
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(cleaned_sources, f, ensure_ascii=False, indent=2)
    print(f"     已输出: {OUT_JSON}")

    # 写入清理报告
    report = {
        'input_total': len(sources),
        'input_enabled': enabled_count,
        'input_disabled': disabled_count,
        'removed_count': len(removed_log),
        'removed_by_reason': dict(reason_counter),
        'output_total': len(cleaned_sources),
        'output_enabled': sum(1 for s in cleaned_sources if s.get('enabled')),
        'output_disabled': sum(1 for s in cleaned_sources if not s.get('enabled')),
        'removed_log': removed_log,
        'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"     已输出报告: {OUT_REPORT}")

    print("\n✅ 清理完成")
    print(f"   输入: {len(sources)} 源 → 输出: {len(cleaned_sources)} 源")
    print(f"   移除: {len(removed_log)} 源（DNS失败+URL格式错误）")


if __name__ == '__main__':
    main()
