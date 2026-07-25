#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4 源码导航工具

将仿真器错误类型映射到真机源码文件和行号，辅助定位差异。

简化说明: 仅覆盖已知的 6 类错误映射 | 已知上限: 新增错误类型需手动补充映射 | 升级路径: 扩展 ERROR_TO_SOURCE 字典
"""
from __future__ import annotations

from typing import Dict


class SourceNavigation:
    """错误类型 → 真机源码定位映射表"""

    ERROR_TO_SOURCE: Dict[str, dict] = {
        "relative_url": {
            "jvm_file": "AnalyzeUrl.kt",
            "jvm_line": "81 (baseUrl默认空字符串)",
            "real_file": "AnalyzeUrl.kt (真机)",
            "real_line": "同位置，但真机有NetworkUtils.getAbsoluteURL自动拼接",
            "note": "方向1已修复：BookSourceDebugger/RssSourceDebugger传baseUrl"
        },
        "js_error": {
            "jvm_file": "RuleEngineServer.kt",
            "jvm_line": "evalJS方法 (约130行)",
            "real_file": "AnalyzeRule.kt (真机)",
            "real_line": "evalJS方法",
            "note": "方向9已注入java/cookie/cache/baseUrl上下文"
        },
        "rule_empty": {
            "jvm_file": "BookSourceDebugger.kt / RssSourceDebugger.kt",
            "jvm_line": "搜索/详情/目录/正文阶段",
            "real_file": "Debug.kt (真机)",
            "real_line": "对应阶段",
            "note": "方向2已集成HtmlStructureAnalyzer自动分析"
        },
        "network_error": {
            "jvm_file": "AnalyzeUrl.kt",
            "jvm_line": "getStrResponse方法",
            "real_file": "AnalyzeUrl.kt (真机)",
            "real_line": "同位置",
            "note": "网络错误通常是网站问题，非仿真器问题"
        },
        "cookie_domain": {
            "jvm_file": "NetworkUtilsStub.kt",
            "jvm_line": "getSubDomain方法 (183行)",
            "real_file": "NetworkUtils.kt (真机)",
            "real_line": "getSubDomain方法 (212行)",
            "note": "方向7已修复：剥离www前缀"
        },
        "ajax_delegate": {
            "jvm_file": "AnalyzeUrl.kt",
            "jvm_line": "ajax override方法 (123行)",
            "real_file": "AnalyzeUrl.kt (真机)",
            "real_line": "ajax方法",
            "note": "方向7已修复：委托AnalyzeUrl自身构造请求"
        },
    }

    def navigate(self, error_type: str) -> dict:
        """根据错误类型返回源码定位信息"""
        return self.ERROR_TO_SOURCE.get(error_type, {
            "jvm_file": "未知",
            "jvm_line": "未知",
            "real_file": "未知",
            "real_line": "未知",
            "note": "无映射信息"
        })


def navigate_to_source(error_type: str) -> dict:
    """模块级便捷函数：根据错误类型返回源码定位信息"""
    return SourceNavigation().navigate(error_type)


if __name__ == "__main__":
    # 最小自检：1 正常用例 + 1 边界用例
    result = navigate_to_source("relative_url")
    assert "jvm_file" in result and result["jvm_file"] == "AnalyzeUrl.kt", "正常用例失败"

    unknown = navigate_to_source("not_exist_error")
    assert unknown["jvm_file"] == "未知", "边界用例失败"

    print("自检通过")
    for k in SourceNavigation.ERROR_TO_SOURCE:
        info = navigate_to_source(k)
        print(f"  {k}: {info['jvm_file']} → {info['real_file']}")
