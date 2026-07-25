# -*- coding: utf-8 -*-
"""auto_fixer_loop.py - 自动修复循环（v4 Phase 3）。

整合 MandatoryFieldValidator + RuntimeValidator + auto_fix_error，
实现"生成→测试→诊断→修复→重测"端到端自动修复循环。

设计哲学（v4）：
    - 闭环：每轮修复后自动重测，验证修复是否真的解决问题
    - 渐进：CRITICAL 失败直接返回，MANDATORY 失败尝试修复，RECOMMENDED 缺失警告
    - 可观测：每轮记录 fix_history，最终返回完整修复轨迹

流程：
    1. MandatoryFieldValidator 校验必填字段
       - CRITICAL 缺失 → 直接返回失败（无法修复）
       - MANDATORY 缺失 → 加入 error list
       - RECOMMENDED 缺失 → 加入 warning list
    2. sanitize_source_json 清理 None 字段
    3. RuntimeValidator 真机测试
    4. 如果失败，根据 logcat_summary + errors 生成 error dict
    5. 调用 auto_fix_error(error, source) 修复
    6. 重测（回到步骤 3），最多 max_attempts 轮
    7. 返回最终结果 + 修复轨迹

典型用法：
    from legado_client.runtime import auto_fixer_loop

    result = auto_fixer_loop(
        source_obj={'sourceUrl': 'https://...', ...},
        source_type='rss',
        max_attempts=3,
        skip_build=False,
    )
    if result['success']:
        print(f"修复成功，最终源: {result['final_source']}")
    else:
        print(f"修复失败，剩余错误: {result['remaining_errors']}")
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional

from legado_client.analyzer.auto_fixer import auto_fix_error
from legado_client.runtime.runtime_validator import (
    RuntimeValidator,
    parse_logcat_summary,
)
from legado_client.utils.file_utils import sanitize_source_json
from legado_client.validator import (
    MandatoryFieldValidator,
    format_validation_report,
)


# 错误模式 → auto_fixer error_type 映射
# 基于 ai_tests/config.py CRASH_PATTERNS + 项目历史铁证
LOGCAT_PATTERN_TO_FIX_TYPE = {
    "FATAL_EXCEPTION": "rule_parse",          # 通用规则错误
    "ANDROID_RUNTIME_FATAL": "rule_parse",
    "CLASS_NOT_FOUND": "rule_parse",
    "NO_CLASS_DEF": "rule_parse",
    "OOM": "rule_parse",
    "RSS_NOT_SOURCE": "field_missing",        # 字段缺失
    "BOOK_NOT_SOURCE": "field_missing",
    "SEARCH_URL_EMPTY": "url_empty",          # 搜索 URL 空
    "LOGIN_CHECK_JS_REF_ERROR": "js_error",   # JS 错误
    "WEBVIEW_THREAD_VIOLATION": "rule_parse",
    "WEBVIEW_DESTROY_FAILED": "rule_parse",
    "EXO_PLAYER_FORMAT_ERROR": "url_empty",   # 视频 URL 格式错误
    "DECRYPT_BLOCK_SIZE_ERROR": "js_error",   # 解密错误
    "IMAGE_DECODE_CAST_ERROR": "js_error",
    "CRONET_PROTOCOL_FAIL": "network",         # 网络协议失败
}


def auto_fixer_loop(
    source_obj: Dict[str, Any],
    source_type: str = "rss",
    max_attempts: int = 3,
    skip_build: bool = False,
    skip_l2_verify: bool = False,
    strict_recommended: bool = False,
) -> Dict[str, Any]:
    """自动修复循环：生成→测试→诊断→修复→重测。

    Args:
        source_obj: 源 JSON dict
        source_type: "book" 或 "rss"
        max_attempts: 最大修复尝试次数（默认 3）
        skip_build: True=跳过编译安装（APK 已装）
        skip_l2_verify: True=跳过 L2 验证
        strict_recommended: True=RECOMMENDED 字段缺失视为失败

    Returns:
        {
            "success": bool,            # True=最终通过校验
            "final_source": dict,       # 修复后的源
            "attempts": int,            # 实际尝试次数
            "fix_history": [...],       # 每轮修复轨迹
            "initial_validation": dict, # 初始校验结果
            "final_validation": dict,   # 最终校验结果
            "runtime_result": dict,    # 最后一轮真机测试结果
            "remaining_errors": list,   # 剩余未修复错误
            "missing_fields": list,    # 仍缺失的字段
        }
    """
    # 深拷贝避免修改入参
    current_source = copy.deepcopy(source_obj)

    fix_history: List[Dict[str, Any]] = []

    # 步骤 1：初始必填字段校验
    validator = MandatoryFieldValidator(strict_recommended=strict_recommended)
    initial_validation = validator.validate(current_source, source_type=source_type)

    # CRITICAL 字段缺失：无法修复，直接返回
    if initial_validation.get("missing_critical"):
        return {
            "success": False,
            "final_source": current_source,
            "attempts": 0,
            "fix_history": [],
            "initial_validation": initial_validation,
            "final_validation": initial_validation,
            "runtime_result": None,
            "remaining_errors": [
                f"CRITICAL 字段缺失: {f}"
                for f in initial_validation["missing_critical"]
            ],
            "missing_fields": initial_validation["all_missing"],
            "validation_report": format_validation_report(initial_validation),
        }

    # 步骤 2：sanitize 清理 None 字段
    current_source = sanitize_source_json(current_source)

    # 步骤 3-6：循环测试+修复
    runtime_result = None
    final_validation = initial_validation
    remaining_errors: List[str] = []

    for attempt in range(1, max_attempts + 1):
        # 步骤 3：真机测试
        runtime_validator = RuntimeValidator(
            source_obj=current_source,
            source_type=source_type,
            skip_build=skip_build,
            skip_l2_verify=skip_l2_verify,
        )
        runtime_result = runtime_validator.validate()

        # 如果真机测试通过，结束循环
        if runtime_result["success"]:
            fix_history.append({
                "attempt": attempt,
                "stage": "runtime_test",
                "status": "passed",
                "errors": [],
            })
            break

        # 步骤 4：诊断错误
        runtime_errors = runtime_result.get("errors", [])
        logcat_summary = runtime_result.get("logcat_summary", {})

        # 把 logcat 错误模式转换为 error_type
        error_types = set()
        for pattern_name in logcat_summary.keys():
            fix_type = LOGCAT_PATTERN_TO_FIX_TYPE.get(pattern_name)
            if fix_type:
                error_types.add(fix_type)

        # 把 runtime errors 也转换为 error_type（基于 stage）
        for err in runtime_errors:
            stage = err.get("stage", "")
            if stage == "import_source":
                error_types.add("field_missing")
            elif stage == "build_install":
                error_types.add("network")
            elif stage == "l2_verify":
                error_types.add("rule_parse")

        # 如果没有识别到错误类型，默认 rule_parse
        if not error_types:
            error_types.add("rule_parse")

        # 步骤 5：调用 auto_fix_error 修复
        # 构造 error dict（auto_fix_error 接受 str 或 dict）
        error_msg = "; ".join([e.get("message", "") for e in runtime_errors[:3]])
        error_obj = {
            "msg": error_msg or "runtime test failed",
            "suggestion": {"error_type": list(error_types)[0]},
        }

        fix_result = auto_fix_error(error_obj, current_source)

        fix_history.append({
            "attempt": attempt,
            "stage": "auto_fix",
            "status": "applied" if fix_result.get("fixes_applied") else "no_fix",
            "error_types": list(error_types),
            "fixes_applied": fix_result.get("fixes_applied", []),
            "missing_fields": fix_result.get("missing_fields", []),
            "runtime_errors_count": len(runtime_errors),
            "logcat_patterns": logcat_summary,
        })

        # 更新 current_source 为修复后的源
        if fix_result.get("fixed_source"):
            current_source = fix_result["fixed_source"]

        # 如果没有应用任何修复，说明无法修复，结束循环
        if not fix_result.get("fixes_applied"):
            remaining_errors = [error_msg] if error_msg else ["无法识别错误模式"]
            break

        # 步骤 6：重测（回到循环开始）
        # 注意：重测时跳过 build（APK 已装）
        skip_build = True

    # 步骤 7：最终校验
    final_validation = validator.validate(current_source, source_type=source_type)

    success = (
        runtime_result is not None
        and runtime_result["success"]
        and len(final_validation.get("missing_critical", [])) == 0
    )

    if not success and not remaining_errors:
        remaining_errors = [
            f"仍有 {len(final_validation.get('all_missing', []))} 个字段缺失"
            if final_validation.get("all_missing")
            else "真机测试未通过"
        ]

    return {
        "success": success,
        "final_source": current_source,
        "attempts": len(fix_history),
        "fix_history": fix_history,
        "initial_validation": initial_validation,
        "final_validation": final_validation,
        "runtime_result": runtime_result,
        "remaining_errors": remaining_errors,
        "missing_fields": final_validation.get("all_missing", []),
        "validation_report": format_validation_report(final_validation),
    }


# ==================== 自检 ====================

if __name__ == "__main__":
    print("auto_fixer_loop.py 自检")

    # 用例 1：CRITICAL 字段缺失 → 直接返回失败
    bad_source = {"sourceName": "test"}  # 缺 sourceUrl
    result = auto_fixer_loop(
        source_obj=bad_source,
        source_type="rss",
        skip_build=True,  # 不实际跑 build
        skip_l2_verify=True,
        max_attempts=1,
    )
    assert not result["success"], "CRITICAL 缺失应直接失败"
    assert result["attempts"] == 0, "CRITICAL 缺失不应进入修复循环"
    assert "sourceUrl" in result["remaining_errors"][0], "应提示 sourceUrl 缺失"
    print("[OK] 用例1: CRITICAL 字段缺失直接返回失败")

    # 用例 2：必填字段齐全但无运行时（skip_build+skip_l2_verify，模拟环境）
    # 这里只验证流程能走完，不验证真机测试结果
    good_source = {
        "sourceName": "test",
        "sourceUrl": "https://example.com",
        "sourceIcon": "https://example.com/icon.png",
        "sourceGroup": "测试",
        "sourceComment": "测试源 - 验证完整源通过校验",
        "searchUrl": "https://example.com/search?q={{key}}",
        "sortUrl": "分类1::https://example.com/cat1",
        "type": 2,
        "ruleArticles": "@CSS:.item",
        "ruleTitle": "@CSS:.title",
        "ruleLink": "@CSS:a@href",
        "ruleContent": "@CSS:.content",
        "ruleImage": "@CSS:img@src",
        "ruleDescription": "@CSS:.desc",
        "ruleNextPage": "@CSS:a.next@href",
    }
    # 不实际跑真机，仅验证流程结构
    # 用 mock 替代：直接调用 MandatoryFieldValidator 验证流程能跑
    v = MandatoryFieldValidator(strict_recommended=True)
    val_result = v.validate(good_source, source_type="rss")
    assert val_result["passed"], f"完整源应通过校验: {val_result}"
    print(f"[OK] 用例2: 完整源通过 MandatoryFieldValidator（{len(good_source)} 字段）")

    # 用例 3：max_attempts=0 边界（不实际修复，仅校验）
    # 改为 max_attempts=1 但 skip_build=True 避免编译
    result = auto_fixer_loop(
        source_obj=good_source,
        source_type="rss",
        skip_build=True,
        skip_l2_verify=True,
        max_attempts=1,
    )
    # 不验证 success（因为没真机），仅验证结构
    assert "fix_history" in result
    assert "final_source" in result
    assert "initial_validation" in result
    assert "final_validation" in result
    print(f"[OK] 用例3: 流程结构完整（attempts={result['attempts']}）")

    print("✅ 自检通过")
