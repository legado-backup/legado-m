"""ai_tests/lib/rule_analyzer.py — M6 规则分析器（V3 反馈信号）

职责：
- 4 规则串联判定（fatal_crash → exception_warning → pass_with_evidence → manual_insufficient）
- 置信度强制规则：< 70 强制 manual
- 生成 ai-prompt.md 提示词（manual 用例供 AI agent 判定）
- V3 新增：失败/manual 时输出 feedback_signal（供 M16 反馈闭环消费）

不依赖任何 LLM SDK，纯规则匹配。
"""
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

from ai_tests.config import CRASH_PATTERNS
from ai_tests.lib.case_parser import TestCase, Expect

logger = logging.getLogger(__name__)


class RuleAnalyzer:
    """规则分析器（4 规则串联 + 置信度强制 + V3 反馈信号）

    判定流程：
    1. 规则 1 _rule_fatal_crash：logcat 异常含 FATAL/CRASH/ANR → fail (confidence=95)
    2. 规则 2 _rule_exception_warning：异常含 Exception/Error 但非 Fatal → warning (confidence=80)
    3. 规则 3 _rule_pass_with_evidence：无异常 + 证据匹配预期 → pass (confidence=85)
    4. 规则 4 _rule_manual_insufficient：证据不足 → manual (confidence=50)
    5. 置信度强制：< 70 → manual
    6. V3：fail/manual 时输出 feedback_signal
    """

    # 异常类型严重度分级
    FATAL_TYPES = {"FATAL", "ANR", "CRASH"}
    WARNING_TYPES = {"OOM", "ClassNotFound", "Other"}

    def __init__(self):
        pass

    # === 8.2 规则 1：FATAL/CRASH/ANR → fail ===

    def _rule_fatal_crash(self, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """规则 1：logcat 异常含 FATAL/CRASH/ANR → fail, confidence=95"""
        logcat = evidence.get("logcat", {})
        anomalies = logcat.get("anomalies", [])
        fatal_anomalies = [a for a in anomalies if a.get("type") in self.FATAL_TYPES]
        if not fatal_anomalies:
            return None
        return {
            "verdict": "fail",
            "confidence": 95,
            "reason": f"检测到 {len(fatal_anomalies)} 个致命异常（FATAL/CRASH/ANR）",
            "matched_anomalies": fatal_anomalies,
        }

    # === 8.3 规则 2：Exception/Error → warning ===

    def _rule_exception_warning(self, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """规则 2：异常含 Exception/Error（OOM/ClassNotFound/Other）但非 Fatal → warning, confidence=80"""
        logcat = evidence.get("logcat", {})
        anomalies = logcat.get("anomalies", [])
        warning_anomalies = [
            a for a in anomalies if a.get("type") in self.WARNING_TYPES
        ]
        if not warning_anomalies:
            return None
        return {
            "verdict": "warning",
            "confidence": 80,
            "reason": f"检测到 {len(warning_anomalies)} 个非致命异常（Exception/Error）",
            "matched_anomalies": warning_anomalies,
        }

    # === 8.4 规则 3：无异常 + 证据匹配 → pass ===

    def _rule_pass_with_evidence(
        self, test_case: TestCase, evidence: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """规则 3：无异常 + 8 种预期类型与证据匹配 → pass, confidence=85

        匹配逻辑：
        - manual 预期 → 不自动 pass（返回 None 走规则 4）
        - no_crash → logcat 无致命异常
        - log_clean → logcat 无任何异常
        - page_jump → activity_stack 已收集
        - element_visible / text_match → ui_xml 已收集
        - db_state / prefs_state / web_api → 证据已收集（降级也算匹配，因降级是环境限制非用例失败）
        """
        # 无 expects 时无法判定 pass
        if not test_case.expects:
            return None

        # 逐个检查预期是否匹配
        unmatched = []
        for expect in test_case.expects:
            if not self._check_expect_match(expect, evidence):
                unmatched.append(expect)
        if unmatched:
            return None

        return {
            "verdict": "pass",
            "confidence": 85,
            "reason": f"无异常 + {len(test_case.expects)} 个预期全部匹配",
            "matched_expects": len(test_case.expects),
        }

    def _check_expect_match(self, expect: Expect, evidence: Dict[str, Any]) -> bool:
        """检查单个预期是否与证据匹配

        简化说明：基于证据 collected/degraded 状态判定 | 已知上限：未深入解析 XML/文本内容 | 升级路径：LLM 语义判定（V4）
        """
        et = expect.expect_type
        if et == "manual":
            return False  # manual 预期无法自动 pass
        if et == "no_crash":
            return evidence.get("logcat", {}).get("anomaly_count", 0) == 0
        if et == "log_clean":
            anomalies = evidence.get("logcat", {}).get("anomalies", [])
            return len(anomalies) == 0
        if et == "page_jump":
            return evidence.get("activity_stack", {}).get("collected", False)
        if et in ("element_visible", "text_match"):
            return evidence.get("ui_xml", {}).get("collected", False)
        if et == "db_state":
            ev = evidence.get("db_state", {})
            return ev.get("collected", False) or ev.get("degraded", False)
        if et == "prefs_state":
            ev = evidence.get("prefs_state", {})
            return ev.get("collected", False) or ev.get("degraded", False)
        if et == "web_api":
            ev = evidence.get("web_api", {})
            return ev.get("collected", False) or ev.get("degraded", False)
        # 未知 expect_type → 不匹配
        return False

    # === 8.5 规则 4：证据不足 → manual ===

    def _rule_manual_insufficient(
        self, test_case: TestCase, evidence: Dict[str, Any], reason: str = "证据不足"
    ) -> Dict[str, Any]:
        """规则 4：证据不足 → manual, confidence=50"""
        return {
            "verdict": "manual",
            "confidence": 50,
            "reason": reason,
            "evidence_summary": self._summarize_evidence(evidence),
        }

    def _summarize_evidence(self, evidence: Dict[str, Any]) -> Dict[str, str]:
        """生成证据摘要（供 ai-prompt.md 使用）"""
        summary = {}
        for ev_type, ev in evidence.items():
            collected = ev.get("collected", False)
            degraded = ev.get("degraded", False)
            if collected:
                status = "collected"
            elif degraded:
                status = f"degraded({ev.get('degradation_reason', 'unknown')})"
            else:
                status = f"failed({ev.get('error', 'unknown')[:80]})"
            summary[ev_type] = status
        return summary

    # === 8.6 生成 ai-prompt.md 提示词 ===

    def _generate_ai_prompt(
        self, test_case: TestCase, evidence: Dict[str, Any], reason: str
    ) -> str:
        """生成 ai-prompt.md 内容（供 AI agent 判定 manual 用例）

        简化说明：固定模板渲染 | 已知上限：未含深度上下文 | 升级路径：Jinja2 模板（M7 report_generator 统一）
        """
        lines: List[str] = []
        lines.append(f"# AI 判定提示词 — {test_case.tc_id}")
        lines.append("")
        lines.append("## 用例信息")
        lines.append(f"- TC-ID: {test_case.tc_id}")
        lines.append(f"- 标题: {test_case.title}")
        lines.append(f"- 模块: {test_case.module or 'N/A'}")
        lines.append(f"- 用例类型: {test_case.case_type or 'N/A'}")
        lines.append("")

        lines.append("## 判定为 manual 的原因")
        lines.append(reason)
        lines.append("")

        lines.append("## 证据摘要")
        for ev_type in [
            "logcat", "ui_xml", "screenshot", "activity_stack",
            "db_state", "prefs_state", "web_api", "meminfo"
        ]:
            ev = evidence.get(ev_type, {})
            collected = ev.get("collected", False)
            degraded = ev.get("degraded", False)
            if collected:
                status = "✓ collected"
            elif degraded:
                status = f"⚠ degraded ({ev.get('degradation_reason', 'unknown')})"
            else:
                status = "✗ failed"
            lines.append(f"- **{ev_type}**: {status}")
            if ev_type == "logcat" and collected:
                lines.append(f"  - 异常数: {ev.get('anomaly_count', 0)}")
                anomalies = ev.get("anomalies", [])
                if anomalies:
                    lines.append("  - 异常详情（前 5 条）:")
                    for a in anomalies[:5]:
                        lines.append(f"    - [{a['type']}] {a['line'][:100]}")
            elif ev_type in ("ui_xml", "screenshot") and collected:
                lines.append(f"  - 文件数: {ev.get('count', 0)}")
            elif ev_type == "db_state" and collected:
                queries = ev.get("queries", {})
                lines.append(f"  - 查询数: {len(queries)}")
        lines.append("")

        lines.append("## 预期结果")
        if test_case.expects:
            for i, expect in enumerate(test_case.expects, 1):
                lines.append(f"{i}. [{expect.expect_type}] {expect.description}")
        else:
            lines.append("（无明确预期）")
        lines.append("")

        lines.append("## 测试步骤")
        if test_case.steps:
            for i, step in enumerate(test_case.steps, 1):
                lines.append(f"{i}. {step.raw}")
        else:
            lines.append("（无步骤）")
        lines.append("")

        lines.append("## 请判定")
        lines.append("基于以上证据，请判定本用例最终结果（pass / fail / manual），并说明理由。")
        lines.append("判定后请回填到 report.json 的 `ai_verdict` 字段。")
        lines.append("")
        return "\n".join(lines)

    # === 8.7 analyze 主入口 ===

    def analyze(self, test_case: TestCase, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """4 规则串联判定 + 置信度强制 + V3 反馈信号

        Returns: dict {verdict, confidence, reason, ai_prompt?, feedback_signal?, ...}
        """
        # 规则 1：FATAL/CRASH/ANR → fail
        result = self._rule_fatal_crash(evidence)
        if result:
            result = self._apply_confidence_rule(result, test_case, evidence)
            result["feedback_signal"] = self._emit_feedback_signal(
                result["verdict"], test_case, evidence
            )
            if result["ai_prompt"]:
                self._save_ai_prompt(test_case, result["ai_prompt"])
            logger.info(
                f"{test_case.tc_id}: verdict={result['verdict']}, "
                f"confidence={result['confidence']}"
            )
            return result

        # 规则 2：Exception/Error → warning
        result = self._rule_exception_warning(evidence)
        if result:
            result = self._apply_confidence_rule(result, test_case, evidence)
            # warning 不触发 feedback_signal（仅 fail/manual 触发）
            logger.info(
                f"{test_case.tc_id}: verdict={result['verdict']}, "
                f"confidence={result['confidence']}"
            )
            return result

        # 规则 3：无异常 + 证据匹配 → pass
        result = self._rule_pass_with_evidence(test_case, evidence)
        if result:
            result = self._apply_confidence_rule(result, test_case, evidence)
            logger.info(
                f"{test_case.tc_id}: verdict={result['verdict']}, "
                f"confidence={result['confidence']}"
            )
            return result

        # 规则 4：证据不足 → manual
        reason = "无规则匹配（证据不足或预期含 manual 类型）"
        result = self._rule_manual_insufficient(test_case, evidence, reason)
        result = self._apply_confidence_rule(result, test_case, evidence)
        result["ai_prompt"] = self._generate_ai_prompt(
            test_case, evidence, result["reason"]
        )
        result["feedback_signal"] = self._emit_feedback_signal(
            result["verdict"], test_case, evidence
        )
        logger.info(
            f"{test_case.tc_id}: verdict={result['verdict']}, "
            f"confidence={result['confidence']}"
        )
        return result

    def _apply_confidence_rule(
        self, result: Dict[str, Any], test_case: TestCase, evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """置信度强制规则：< 70 强制 manual

        简化说明：硬编码阈值 70 | 已知上限：未支持自定义阈值 | 升级路径：config.py 可配置（V4）
        """
        if result["confidence"] < 70:
            original_verdict = result["verdict"]
            original_confidence = result["confidence"]
            manual = self._rule_manual_insufficient(
                test_case, evidence,
                f"置信度 {original_confidence} < 70（原 verdict={original_verdict}），强制 manual"
            )
            manual["original_verdict"] = original_verdict
            manual["original_confidence"] = original_confidence
            manual["ai_prompt"] = self._generate_ai_prompt(
                test_case, evidence, manual["reason"]
            )
            return manual
        # 非 manual 结果无 ai_prompt
        if result["verdict"] != "manual":
            result["ai_prompt"] = None
        return result

    def _save_ai_prompt(self, test_case: TestCase, ai_prompt: str) -> None:
        """保存 ai-prompt.md 到用例目录

        简化说明：保存到 reports 目录下用例目录 | 已知上限：路径需调用方预先创建 | 升级路径：由 M7 report_generator 统一管理（V4）
        """
        try:
            from ai_tests.config import REPORTS_DIR
            prompt_dir = REPORTS_DIR / "manual_cases"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = prompt_dir / f"{test_case.tc_id}_ai-prompt.md"
            prompt_path.write_text(ai_prompt, encoding="utf-8")
            logger.info(f"ai-prompt.md 已保存: {prompt_path}")
        except Exception as e:
            logger.warning(f"保存 ai-prompt.md 失败: {e}")

    # === 8.8 V3 新增：反馈信号 ===

    def _emit_feedback_signal(
        self, verdict: str, test_case: TestCase, evidence: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """V3 新增：fail/manual 时输出 feedback_signal（供 M16 反馈闭环消费）

        Returns: dict {tc_id, verdict, failure_pattern, suggested_rule, suggested_prompt} or None
        """
        if verdict not in ("manual", "fail"):
            return None
        return {
            "tc_id": test_case.tc_id,
            "verdict": verdict,
            "failure_pattern": self._extract_failure_pattern(evidence),
            "suggested_rule": self._suggest_rule(evidence, test_case),
            "suggested_prompt": self._suggest_prompt(test_case, evidence),
        }

    def _extract_failure_pattern(self, evidence: Dict[str, Any]) -> str:
        """提取失败模式摘要（供 M16 规则扩展参考）

        简化说明：基于 logcat 异常类型 | 已知上限：未覆盖 UI/DB 层失败模式 | 升级路径：多维度特征提取（V4）
        """
        logcat = evidence.get("logcat", {})
        anomalies = logcat.get("anomalies", [])
        if not anomalies:
            return "no_anomaly_but_manual"
        types = {a["type"] for a in anomalies}
        return "|".join(sorted(types))

    def _suggest_rule(self, evidence: Dict[str, Any], test_case: TestCase) -> str:
        """建议规则扩展方向"""
        logcat = evidence.get("logcat", {})
        anomalies = logcat.get("anomalies", [])
        if anomalies:
            return f"扩展 CRASH_PATTERNS：{self._extract_failure_pattern(evidence)}"
        # 证据降级场景
        degraded = [
            k for k, v in evidence.items() if v.get("degraded", False)
        ]
        if degraded:
            return f"改进证据收集：{','.join(degraded)} 降级，需补充收集路径"
        return "补充预期匹配规则：当前规则未覆盖此场景"

    def _suggest_prompt(self, test_case: TestCase, evidence: Dict[str, Any]) -> str:
        """建议 AI 提示词改进方向"""
        if not test_case.expects:
            return "补充预期结果描述，当前用例无明确预期"
        manual_expects = [
            e for e in test_case.expects if e.expect_type == "manual"
        ]
        if manual_expects:
            return f"将 {len(manual_expects)} 个 manual 预期细化为具体类型（page_jump/element_visible 等）"
        return "预期已明确，建议补充证据判定逻辑"


# === 自检（任务 8.9 交付自查）===
# 正常用例：RuleAnalyzer 可实例化
# 边界用例：空证据时判定 manual
# 异常用例：test_case 无 expects 时判定 manual
if __name__ == "__main__":
    analyzer = RuleAnalyzer()
    # 边界用例：空证据
    empty_tc = TestCase(tc_id="TC-TEST", title="test")
    result = analyzer.analyze(empty_tc, {})
    assert result["verdict"] == "manual", f"空证据应为 manual，实际: {result['verdict']}"
    assert result["confidence"] == 50
    print("[IMPORT OK] rule_analyzer")
