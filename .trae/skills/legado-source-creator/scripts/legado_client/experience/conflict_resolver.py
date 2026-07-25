#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""经验冲突解决器：从 experience_manager.py 提取的冲突解决逻辑。

按置信度0.5+时效性0.3+覆盖度0.2评分选优。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List


class ConflictResolver:
    """经验冲突解决器：多经验冲突时选最优。"""

    # 权重配置
    WEIGHT_CONFIDENCE: float = 0.5
    WEIGHT_RECENCY: float = 0.3
    WEIGHT_COVERAGE: float = 0.2

    def resolve(self, exp1: dict, exp2: dict) -> dict:
        """解决两个经验之间的冲突，返回评分更高的经验。

        Args:
            exp1: 经验1（含confidence/date/coverage字段）
            exp2: 经验2

        Returns:
            dict: 评分更高的经验
        """
        return exp1 if self._score(exp1) >= self._score(exp2) else exp2

    def resolve_all(self, experiences: List[dict]) -> dict:
        """从多个经验中选出最优。

        Args:
            experiences: 经验列表

        Returns:
            dict: 评分最高的经验，空列表时返回空字典
        """
        if not experiences:
            return {}
        best = experiences[0]
        for exp in experiences[1:]:
            best = self.resolve(best, exp)
        return best

    def _score(self, exp: dict) -> float:
        """计算经验评分：置信度*0.5 + 时效性*0.3 + 覆盖度*0.2。

        Args:
            exp: 经验字典

        Returns:
            float: 评分(0-1)
        """
        confidence: float = exp.get("confidence", 0.5)
        date_str: str = exp.get("date", "")
        coverage: float = exp.get("coverage", 0.5)
        # 时效性：基于日期衰减计算，1年内从1.0衰减到0.0
        recency = self._calculate_recency(date_str)
        return confidence * self.WEIGHT_CONFIDENCE + recency * self.WEIGHT_RECENCY + coverage * self.WEIGHT_COVERAGE

    @staticmethod
    def _calculate_recency(date_str: str) -> float:
        """计算时效性评分：越新评分越高，1年内衰减到0。

        Args:
            date_str: ISO格式日期字符串

        Returns:
            float: 时效性评分(0-1)
        """
        if not date_str:
            return 0.0
        try:
            exp_date = datetime.fromisoformat(date_str)
            days_ago = (datetime.now() - exp_date).days
            return max(0.0, 1.0 - days_ago / 365)
        except Exception:
            return 0.0


# 简化说明：单例模式 | 已知上限：无 | 升级路径：如需动态权重，改为从JSON加载
_resolver = ConflictResolver()


def resolve_conflict(exp1: dict, exp2: dict) -> dict:
    """模块级便捷函数：解决两个经验之间的冲突。"""
    return _resolver.resolve(exp1, exp2)


def resolve_all_conflicts(experiences: List[dict]) -> dict:
    """模块级便捷函数：从多个经验中选出最优。"""
    return _resolver.resolve_all(experiences)


if __name__ == "__main__":
    # 最小自检：1 正常用例 + 1 边界用例
    # 正常用例：高置信度+近期日期 胜出
    exp1 = {"confidence": 0.9, "date": "2026-06-20T00:00:00", "coverage": 0.8}
    exp2 = {"confidence": 0.5, "date": "2025-01-01T00:00:00", "coverage": 0.3}
    winner = resolve_conflict(exp1, exp2)
    assert winner is exp1, f"正常用例失败: 高置信度+近期应胜出, got {winner}"
    print(f"✅ 正常用例: confidence=0.9 + 近期日期 胜出")

    # 边界用例：空列表
    result = resolve_all_conflicts([])
    assert result == {}, f"边界用例失败: 空列表应返回空字典, got {result}"
    print(f"✅ 边界用例: 空列表 → {{}}")

    print("\n所有自检通过 (2/2)")
