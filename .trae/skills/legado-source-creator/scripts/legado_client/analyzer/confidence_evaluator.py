#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仿真器可信度评估器：根据规则类型和保真度限制评估测试结果可信度。

AD-14决策：采用"规则类型基础分+保真度限制扣减"的加权方案。
阈值0.85/0.65划分高/中/低三级。
"""
from __future__ import annotations

from typing import Dict, List


class ConfidenceEvaluator:
    """可信度评估器"""

    # 规则类型基础分
    RULE_TYPE_CONFIDENCE: Dict[str, float] = {
        "pure_css": 0.95,       # 纯CSS选择器，仿真器完全支持
        "contains_js": 0.75,    # 含JS规则，Rhino有限制
        "contains_encrypt": 0.50,  # 含加密，hutool版本差异
        "contains_ajax": 0.60,  # 含ajax，方向7已修复但仍有差异
    }

    # 保真度限制扣减
    FIDELITY_PENALTY: Dict[str, float] = {
        "getSubDomain": 0.10,      # 无PublicSuffixDatabase
        "evalJS_context": 0.15,    # Rhino不支持ES6+
        "ajax_delegate": 0.20,     # 方向7已修复但仍有差异
        "aes_encode": 0.10,        # hutool版本差异
    }

    def evaluate(self, source_json: dict, test_result: dict) -> dict:
        """评估测试结果可信度

        Args:
            source_json: 书源/订阅源JSON
            test_result: 测试结果

        Returns:
            dict: {
                score: float,       # 可信度评分(0-1)
                level: str,         # 高/中/低
                warnings: list,     # 警告信息
                suggest_real_device: bool,  # 是否建议真机验证
            }
        """
        rule_type = self._detect_rule_type(source_json)
        base_score = self.RULE_TYPE_CONFIDENCE.get(rule_type, 0.70)

        # 检测保真度限制
        penalties = self._detect_penalties(source_json)
        score = base_score
        for p in penalties:
            score -= self.FIDELITY_PENALTY.get(p, 0)
        score = max(0.0, min(1.0, score))

        # 确定等级
        if score >= 0.85:
            level = "高"
            suggest_real_device = False
        elif score >= 0.65:
            level = "中"
            suggest_real_device = True
        else:
            level = "低"
            suggest_real_device = True

        warnings: List[str] = []
        if suggest_real_device:
            warnings.append(f"可信度{level}（{score:.2f}），建议真机验证")
        for p in penalties:
            warnings.append(f"保真度限制: {p} (-{self.FIDELITY_PENALTY.get(p, 0):.2f})")

        return {
            "score": round(score, 2),
            "level": level,
            "warnings": warnings,
            "suggest_real_device": suggest_real_device,
        }

    def _detect_rule_type(self, source_json: dict) -> str:
        """检测规则类型"""
        json_str = str(source_json)
        has_js = "@js:" in json_str or "<js>" in json_str
        has_encrypt = "encrypt" in json_str.lower() or "decrypt" in json_str.lower() or "AES" in json_str or "DES" in json_str
        has_ajax = "ajax" in json_str.lower()

        if has_encrypt:
            return "contains_encrypt"
        if has_ajax:
            return "contains_ajax"
        if has_js:
            return "contains_js"
        return "pure_css"

    def _detect_penalties(self, source_json: dict) -> List[str]:
        """检测适用的保真度限制"""
        json_str = str(source_json)
        penalties: List[str] = []
        if "getSubDomain" in json_str or "cookie" in json_str.lower():
            penalties.append("getSubDomain")
        if "@js:" in json_str or "<js>" in json_str:
            penalties.append("evalJS_context")
        if "ajax" in json_str.lower():
            penalties.append("ajax_delegate")
        if "encrypt" in json_str.lower() or "decrypt" in json_str.lower():
            penalties.append("aes_encode")
        return penalties


# 简化说明：单例模式 | 已知上限：无 | 升级路径：如需动态配置，改为从JSON加载
_evaluator = ConfidenceEvaluator()


def evaluate_confidence(source_json: dict, test_result: dict) -> dict:
    """模块级便捷函数"""
    return _evaluator.evaluate(source_json, test_result)
