# -*- coding: utf-8 -*-
"""runtime 包：真机测试集成（v4 Phase 2/3）。

复用 ai_tests/lib 的 10 个核心模块 + ai_tests/scripts 的 7 个固定脚本，
实现"生成源 → 编译安装 → 导入 → 真机验证 → 日志分析 → 自动修复 → 重测"端到端闭环。

组件：
- runtime_validator.py: 真机测试集成验证器（Phase 2）
- auto_fixer_loop.py: 自动修复循环（Phase 3）
"""
from legado_client.runtime.runtime_validator import (
    RuntimeValidator,
    validate_source_on_device,
    parse_logcat_summary,
)
from legado_client.runtime.auto_fixer_loop import auto_fixer_loop

__all__ = [
    "RuntimeValidator",
    "validate_source_on_device",
    "parse_logcat_summary",
    "auto_fixer_loop",
]
