#!/usr/bin/env python3
r"""v5_3_final_fix.py — V5.3 最终修复脚本

基于 V5.2 + PC Playwright 真实验证结果，对224源做最终修复：
1. 修复6个规则问题源（idx 1/107/215 改 ruleArticles；idx 9/13/34 标 enabled=false）
2. 标记137个网络层失败源 enabled=false（exception/network_fail/部分timeout）
3. 标记15个 CF 盾源 enabled=false
4. 保留 empty_content(13) / login_required(5) / rule_match(63) 共81源 enabled=true
5. 字段完整性修复（enabledCookieJar null→True，Boolean 字段默认值）

输出：
- output/rss/optimized_v5_3_final.json（纯数组格式）
- output/rss/v5_3_fix_report.json（修复统计）

安全规范：禁止输出源名称/URL/cookie，只输出 idx 与技术结论。
"""
import json
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
V52_JSON = ROOT / "output" / "rss" / "optimized_v5_2_stable.json"
VERIFY_JSON = ROOT / "output" / "rss" / "v5_2_rule_verify_result.json"
OUT_JSON = ROOT / "output" / "rss" / "optimized_v5_3_final.json"
OUT_REPORT = ROOT / "output" / "rss" / "v5_3_fix_report.json"


# ===== 步骤1：加载输入 =====
def load_inputs():
    print(f"[1/5] 加载 V5.2 JSON: {V52_JSON.name}")
    with open(V52_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f"     源总数: {len(sources)}")

    print(f"[2/5] 加载验证结果: {VERIFY_JSON.name}")
    with open(VERIFY_JSON, 'r', encoding='utf-8') as f:
        verify = json.load(f)
    verify_map = {r['idx']: r for r in verify['results']}
    print(f"     验证结果数: {len(verify_map)}")

    # 统计 failure_reason 分布（技术统计，不含业务字段）
    reason_counter = Counter(r.get('failure_reason', 'unknown') for r in verify['results'])
    status_counter = Counter(r.get('status', 'unknown') for r in verify['results'])
    print(f"     status 分布: {dict(status_counter)}")
    print(f"     failure_reason 分布: {dict(reason_counter)}")
    return sources, verify_map


# ===== 步骤2：规则修复映射表 =====
# idx → 新 ruleArticles（仅3个源需要修改规则）
RULE_FIX_MAP = {
    1: ".container li",
    107: "article",
    215: '{"articleList":".item","title":".title","link":"a@href","image":"img@src","date":"","desc":""}',
}

# idx → 标记 enabled=false（ruleArticles 空，无法补规则）
EMPTY_RULE_DISABLED = {9, 13, 34}


# ===== 步骤3：判定每个源的处理策略 =====
# 网络层失败原因集合 → 标记 enabled=false
NETWORK_FAILURE_REASONS = {
    "exception",      # NAV_INTERRUPTED/SSL/INVALID_URL/TUNNEL/ABORTED 等
    "network_fail",   # 网络失败
}

# CF 盾
CF_SHIELD_REASON = "cf_shield"

# timeout 单独处理：仅标记 enabled=false（视为网络层问题）
TIMEOUT_REASON = "timeout"

# 保留 enabled=true 的失败原因
KEEP_ENABLED_REASONS = {
    "empty_content",    # 13个，可能只是当前无内容
    "login_required",   # 5个，用户可手动登录
    "rule_match",       # 63个，已验证可用（实际是成功源）
}

# 成功状态
SUCCESS_STATUS = "success"


def classify_action(idx, verify_item):
    """返回 (action, reason_code)：
    action ∈ {fix_rule, disable_network, disable_cf, disable_empty_rule, keep_success, keep_maybe_valid}
    reason_code 用于 sourceComment 标注
    """
    if verify_item is None:
        return ("keep_maybe_valid", "no_verify_data")

    status = verify_item.get('status', '')
    reason = verify_item.get('failure_reason', '')

    # A. 6个规则问题源
    if idx in RULE_FIX_MAP:
        return ("fix_rule", "rule_fixed_by_v5_3")
    if idx in EMPTY_RULE_DISABLED:
        return ("disable_empty_rule", "empty_rule_unfixable")

    # B. 网络层失败
    if reason in NETWORK_FAILURE_REASONS:
        return ("disable_network", f"network_exception:{reason}")

    # C. CF 盾
    if reason == CF_SHIELD_REASON:
        return ("disable_cf", "cf_shield")

    # D. timeout（网络层问题）
    if reason == TIMEOUT_REASON:
        return ("disable_network", "network_exception:timeout")

    # E. 成功
    if status == SUCCESS_STATUS or reason == "rule_match":
        return ("keep_success", "verified_ok")

    # F. empty_content / login_required 保留
    if reason in KEEP_ENABLED_REASONS:
        return ("keep_maybe_valid", f"keep_{reason}")

    # 兜底：未知状态保守保留
    return ("keep_maybe_valid", f"unknown_reason_{reason}")


# ===== 步骤4：字段完整性修复 =====
def fix_field_completeness(src):
    """按 RssSource.kt 字段类型修复 null/缺失字段"""
    # Boolean 字段默认值
    bool_defaults = {
        "enabled": True,           # 由分类逻辑决定，不在此处统一改
        "enabledCookieJar": True,  # V5.2 未完成的部分
        "enableJs": False,
        "loadWithBaseUrl": False,
        "cacheFirst": False,
        "preload": False,
        "showWebLog": False,
        "singleUrl": False,
    }
    for field, default in bool_defaults.items():
        if field == "enabled":
            continue  # enabled 由 action 决定
        if field not in src or src[field] is None:
            src[field] = default

    # Int 字段默认值
    int_defaults = {
        "articleStyle": 0,
        "customOrder": 0,
        "parseConcurrency": 0,
        "type": 2,        # RSS源 type=2（订阅源）
        "weight": 0,
    }
    for field, default in int_defaults.items():
        if field not in src or src[field] is None:
            src[field] = default

    # String 字段空值兜底（非 null）
    str_fields = ["header", "lastHost", "loginUrl", "loginUi", "concurrentRate",
                  "ruleArticles", "ruleContent", "ruleDescription", "ruleImage",
                  "ruleLink", "ruleNextPage", "rulePubDate", "ruleTitle",
                  "searchUrl", "sortUrl", "sourceComment", "sourceGroup",
                  "sourceIcon", "sourceName", "sourceUrl", "variable"]
    for field in str_fields:
        if field not in src:
            src[field] = ""
        elif src[field] is None:
            src[field] = ""

    # lastUpdateTime 默认 0
    if src.get("lastUpdateTime") is None:
        src["lastUpdateTime"] = 0

    return src


# ===== 步骤5：执行修复 =====
def apply_fixes(sources, verify_map):
    print("\n[3/5] 执行修复（按 idx 处理）...")
    stats = Counter()
    disabled_idx_list = []
    enabled_idx_list = []
    fix_rule_idx_list = []
    action_log = []

    for idx, src in enumerate(sources):
        verify_item = verify_map.get(idx)
        action, reason_code = classify_action(idx, verify_item)

        # A. 规则修复
        if action == "fix_rule":
            old_rule = src.get("ruleArticles", "")
            new_rule = RULE_FIX_MAP[idx]
            src["ruleArticles"] = new_rule
            src["enabled"] = True
            stats["fix_rule"] += 1
            fix_rule_idx_list.append(idx)
            action_log.append({"idx": idx, "action": "fix_rule",
                               "old_rule_length": len(old_rule) if old_rule else 0,
                               "new_rule_length": len(new_rule),
                               "reason_code": reason_code})

        # B/C/D. enabled=false 标记
        elif action in ("disable_network", "disable_cf", "disable_empty_rule"):
            src["enabled"] = False
            stats[action] += 1
            disabled_idx_list.append(idx)
            # 添加 sourceComment 标注（仅追加技术原因，不删除原注释）
            existing_comment = src.get("sourceComment", "") or ""
            tag = f"[AI_V5_3:{reason_code}]"
            if tag not in existing_comment:
                # 在现有注释末尾追加
                src["sourceComment"] = (existing_comment + "\n" + tag).strip()
            action_log.append({"idx": idx, "action": action, "reason_code": reason_code})

        # E/F. 保留 enabled=true
        else:
            # 仅在源原本 enabled=true 或验证通过时保留
            # 若原本 enabled=false 则保持 false（避免重新激活已禁用源）
            original_enabled = src.get("enabled", True)
            if action == "keep_success":
                src["enabled"] = True
            else:  # keep_maybe_valid
                # 保留原状态（可能 false 也可能 true）
                src["enabled"] = bool(original_enabled) if original_enabled is not None else True
            stats[action] += 1
            enabled_idx_list.append(idx)
            action_log.append({"idx": idx, "action": action, "reason_code": reason_code})

        # 字段完整性修复（所有源统一处理）
        src = fix_field_completeness(src)
        sources[idx] = src

    print(f"     fix_rule: {stats['fix_rule']} 源")
    print(f"     disable_network: {stats['disable_network']} 源")
    print(f"     disable_cf: {stats['disable_cf']} 源")
    print(f"     disable_empty_rule: {stats['disable_empty_rule']} 源")
    print(f"     keep_success: {stats['keep_success']} 源")
    print(f"     keep_maybe_valid: {stats['keep_maybe_valid']} 源")
    print(f"     规则修复 idx: {fix_rule_idx_list}")
    print(f"     空规则禁用 idx: {sorted(EMPTY_RULE_DISABLED)}")
    print(f"     禁用源总数: {len(disabled_idx_list)}")
    print(f"     保留源总数: {len(enabled_idx_list)}")

    return sources, stats, {
        "fix_rule_idx": fix_rule_idx_list,
        "disabled_idx": disabled_idx_list,
        "enabled_idx": enabled_idx_list,
        "action_log": action_log,
    }


# ===== 步骤6：输出 JSON 与统计报告 =====
def write_outputs(sources, stats, detail):
    print(f"\n[4/5] 写出最终 JSON: {OUT_JSON.name}")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, separators=(',', ':'))
    print(f"     写入 {len(sources)} 源，文件大小: {OUT_JSON.stat().st_size} 字节")

    print(f"\n[5/5] 写出统计报告: {OUT_REPORT.name}")
    enabled_count = sum(1 for s in sources if s.get("enabled") is True)
    disabled_count = sum(1 for s in sources if s.get("enabled") is False)

    report = {
        "version": "v5_3_final",
        "input_total": len(sources),
        "actions": dict(stats),
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "fix_rule_idx": detail["fix_rule_idx"],
        "disable_empty_rule_idx": sorted(EMPTY_RULE_DISABLED),
        "disabled_idx_count": len(detail["disabled_idx"]),
        "enabled_idx_count": len(detail["enabled_idx"]),
        "output_json": str(OUT_JSON),
        "summary": (
            f"V5.3最终修复: 输入{len(sources)}源 / "
            f"规则修复{stats['fix_rule']}源 / "
            f"禁用{disabled_count}源(enabled=false) / "
            f"保留{enabled_count}源(enabled=true)"
        ),
    }
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"     报告写入完成: {OUT_REPORT}")
    print(f"\n===== 修复摘要 =====")
    print(f"  输入源总数: {len(sources)}")
    print(f"  规则修复: {stats['fix_rule']} 源")
    print(f"  禁用(enabled=false): {disabled_count} 源")
    print(f"  保留(enabled=true): {enabled_count} 源")
    print(f"  输出JSON: {OUT_JSON}")
    print(f"  统计报告: {OUT_REPORT}")
    return report


def main():
    print("=" * 60)
    print("V5.3 最终修复脚本")
    print("=" * 60)
    sources, verify_map = load_inputs()
    sources, stats, detail = apply_fixes(sources, verify_map)
    report = write_outputs(sources, stats, detail)
    print("\n✅ V5.3 最终修复完成")
    return report


if __name__ == "__main__":
    main()
