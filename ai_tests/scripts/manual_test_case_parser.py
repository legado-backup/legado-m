"""ai_tests/scripts/manual_test_case_parser.py — M3 实测验证脚本

任务 5.10：实测验证 - 解析 docs/tests/ 全部 14 份文件

验证项：
1. 解析全部 14 份用例文件无 fatal 错误
2. TC-ID 正确提取
3. 双轨调度正确（默认 md，因为暂无 B 轨 Python 用例）
4. 步骤+预期+前置资源识别正确
5. parse_warnings 统计

用法：
    python ai_tests/scripts/manual_test_case_parser.py
"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.config import DOCS_TESTS_DIR
from ai_tests.lib.case_parser import CaseParser


def main() -> int:
    print("=" * 60)
    print("M3 实测验证：解析 docs/tests/ 全部用例")
    print("=" * 60)

    if not DOCS_TESTS_DIR.exists():
        print(f"[FAIL] docs/tests/ 目录不存在: {DOCS_TESTS_DIR}")
        return 1

    parser = CaseParser()
    cases = parser.parse_directory(DOCS_TESTS_DIR)

    if not cases:
        print("[FAIL] 未解析到任何用例")
        return 1

    # 1. 总体统计
    print(f"\n[1] 总体统计:")
    print(f"    总用例数: {len(cases)}")
    md_count = sum(1 for c in cases if c.track_source == "md")
    py_count = sum(1 for c in cases if c.track_source == "python")
    print(f"    A 轨 MD 用例: {md_count}")
    print(f"    B 轨 Python 用例: {py_count}")

    # 2. 按模块分组
    print(f"\n[2] 按模块分组:")
    module_counter = Counter(c.module for c in cases if c.module)
    for module, count in sorted(module_counter.items()):
        print(f"    {module}: {count} 个用例")

    # 3. 按用例类型分组
    print(f"\n[3] 按用例类型分组:")
    type_counter = Counter(c.case_type for c in cases if c.case_type)
    for case_type, count in sorted(type_counter.items()):
        print(f"    {case_type}: {count} 个用例")

    # 4. 步骤/预期/前置资源统计
    total_steps = sum(len(c.steps) for c in cases)
    total_expects = sum(len(c.expects) for c in cases)
    total_preconds = sum(len(c.preconditions) for c in cases)
    total_related_source = sum(len(c.related_source) for c in cases)
    total_related_activity = sum(len(c.related_activity) for c in cases)

    print(f"\n[4] 字段统计:")
    print(f"    总步骤数:        {total_steps}")
    print(f"    总预期数:        {total_expects}")
    print(f"    总前置资源数:    {total_preconds}")
    print(f"    V3 关联源码:     {total_related_source} 个用例")
    print(f"    V3 关联 Activity: {total_related_activity} 个用例")

    # 5. 步骤动作分布
    print(f"\n[5] 步骤动作分布:")
    action_counter = Counter()
    for c in cases:
        for s in c.steps:
            action_counter[s.action] += 1
    for action, count in sorted(action_counter.items(), key=lambda x: -x[1]):
        print(f"    {action}: {count}")

    # 6. 预期类型分布
    print(f"\n[6] 预期类型分布:")
    expect_type_counter = Counter()
    for c in cases:
        for e in c.expects:
            expect_type_counter[e.expect_type] += 1
    for et, count in sorted(expect_type_counter.items(), key=lambda x: -x[1]):
        print(f"    {et}: {count}")

    # 7. TC-ID 列表（前 20 个）
    print(f"\n[7] TC-ID 列表（前 20 个）:")
    for c in cases[:20]:
        track_mark = "[MD]" if c.track_source == "md" else "[PY]"
        warning_mark = " ⚠️" if c.parse_warnings else ""
        print(f"    {track_mark} {c.tc_id}: {c.title[:40]}{warning_mark}")
    if len(cases) > 20:
        print(f"    ... (还有 {len(cases) - 20} 个)")

    # 8. 容错检查
    print(f"\n[8] 容错检查:")
    cases_with_warnings = [c for c in cases if c.parse_warnings]
    if cases_with_warnings:
        print(f"    有 parse_warnings 的用例: {len(cases_with_warnings)}")
        for c in cases_with_warnings[:5]:
            print(f"    - {c.tc_id}: {c.parse_warnings}")
    else:
        print(f"    所有用例格式规范，无 parse_warnings")

    # 9. 致命错误检查
    fatal_errors = []
    for c in cases:
        if not c.tc_id:
            fatal_errors.append(f"用例缺少 TC-ID: {c.source_file}")
        if not c.title:
            fatal_errors.append(f"{c.tc_id}: 缺少标题")
    if fatal_errors:
        print(f"\n[FAIL] 发现 {len(fatal_errors)} 个致命错误:")
        for err in fatal_errors:
            print(f"    - {err}")
        return 1

    print(f"\n[9] 致命错误检查: 无致命错误")

    print("=" * 60)
    print("[PASS] M3 实测验证通过：全部用例解析无 fatal 错误")
    return 0


if __name__ == "__main__":
    sys.exit(main())
