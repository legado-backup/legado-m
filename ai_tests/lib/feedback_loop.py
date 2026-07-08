"""ai_tests/lib/feedback_loop.py — M16 反馈闭环（V3 新增）

职责（任务 16.1-16.6）：
- process(report): 消费测试报告，输出 4 类反馈建议
- _extract_root_cause(case): 提取根因（type/category/pattern/covered/detail）
- _suggest_rule_extension: 规则库扩展建议（仅对未被 CRASH_PATTERNS 覆盖的新异常）
- _suggest_prompt_tuning: 提示词调优建议（仅 manual 用例）
- _suggest_known_issue: 陷阱库沉淀建议（追加到 known_issues.md）
- _build_regression_entry + _append_regression_history: 回归历史记录（追加到 regression_history.md）

依赖：config.CRASH_PATTERNS（只读）, config.PROJECT_ROOT（路径拼接）

设计决策（ADR-AD-16）：
- process(report) 单参数，遵循 design.md 1.3.11。feedback_signal 已内嵌 report.cases[]，
  无需单独传入（tasks.md 16.2 双参数签名已收敛为单参数）。
- 根因提取两阶段：先精确匹配 CRASH_PATTERNS（covered=True），再用通用异常正则
  \\w+(Exception|Error) 捕获新异常（covered=False），仅对未覆盖的新异常建议扩展规则库。
- 陷阱库/回归历史文件不存在时自动创建带表头初始模板，阶段 20 再补充首批陷阱与分类说明。
"""
import re
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ai_tests import config

logger = logging.getLogger(__name__)

# 通用异常捕获正则（捕获新异常类名，如 TimeoutException、CustomError）
# 简化说明：仅匹配 XxxException/XxxError 形态 | 已知上限：无法捕获非英文异常名 | 升级路径：V4 接入 LLM 语义分析
_GENERIC_EXCEPTION_RE = re.compile(r"(\w+(?:Exception|Error))")


class FeedbackLoop:
    """反馈闭环处理器（M16）

    消费 M6/M7 输出的 feedback_signal，生成 4 类反馈建议供 AI 审阅沉淀：
    1. rule_suggestions — 规则库扩展建议（写入 config.CRASH_PATTERNS，需 AI 审核）
    2. prompt_suggestions — 提示词调优建议（调优 ai_prompt_template.j2，需 AI 审核）
    3. known_issue_suggestions — 陷阱库沉淀（直接追加到 known_issues.md）
    4. regression_history_entry — 回归历史记录（直接追加到 regression_history.md）
    """

    def __init__(
        self,
        known_issues_path: Optional[Path] = None,
        regression_history_path: Optional[Path] = None,
    ):
        self.known_issues_path = known_issues_path or (
            config.PROJECT_ROOT / "ai_tests" / "docs" / "known_issues.md"
        )
        self.regression_history_path = regression_history_path or (
            config.PROJECT_ROOT / "ai_tests" / "docs" / "regression_history.md"
        )

    def process(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """处理测试报告，输出 4 类反馈建议

        Args:
            report: report.json 结构 {cases: [{tc_id, verdict, reason, feedback_signal}], ...}
        Returns:
            {rule_suggestions, prompt_suggestions, known_issue_suggestions, regression_history_entry}
        """
        cases = report.get("cases", [])
        rule_suggestions: List[Dict] = []
        prompt_suggestions: List[Dict] = []
        known_issue_suggestions: List[Dict] = []

        for case in cases:
            if case.get("verdict") not in ("manual", "fail"):
                continue
            root_cause = self._extract_root_cause(case)

            rule_s = self._suggest_rule_extension(case, root_cause)
            if rule_s:
                rule_suggestions.append(rule_s)

            prompt_s = self._suggest_prompt_tuning(case, root_cause)
            if prompt_s:
                prompt_suggestions.append(prompt_s)

            known = self._suggest_known_issue(case, root_cause)
            if known:
                known_issue_suggestions.append(known)
                self._append_known_issue(known)

        entry = self._build_regression_entry(report)
        self._append_regression_history(entry)

        return {
            "rule_suggestions": rule_suggestions,
            "prompt_suggestions": prompt_suggestions,
            "known_issue_suggestions": known_issue_suggestions,
            "regression_history_entry": entry,
        }

    def _extract_root_cause(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """提取根因（type/category/pattern/covered/detail）

        简化说明：基于文本模式匹配 | 已知上限：不接入 LLM 语义分析 | 升级路径：V4 接入 LLM
        两阶段：1) 精确匹配 CRASH_PATTERNS（covered=True） 2) 通用异常正则捕获新异常（covered=False）
        """
        fs = case.get("feedback_signal") or {}
        detail = fs.get("failure_pattern") or case.get("reason") or ""

        # 阶段 1：精确匹配 CRASH_PATTERNS
        for category, regexes in config.CRASH_PATTERNS.items():
            for rx in regexes:
                if re.search(rx, detail, re.IGNORECASE):
                    return {
                        "type": "exception",
                        "category": category,
                        "pattern": rx,
                        "covered": True,
                        "detail": detail,
                    }

        # 阶段 2：通用异常正则捕获新异常
        m = _GENERIC_EXCEPTION_RE.search(detail)
        if m:
            return {
                "type": "exception",
                "category": "Other",
                "pattern": m.group(1),
                "covered": False,
                "detail": detail,
            }

        # 阶段 3：非异常（断言/超时/未知）
        low = detail.lower()
        if "assert" in low:
            rc_type = "assertion"
        elif "timeout" in low or "超时" in detail:
            rc_type = "timeout"
        else:
            rc_type = "unknown"
        return {
            "type": rc_type,
            "category": "unknown",
            "pattern": "",
            "covered": False,
            "detail": detail,
        }

    def _suggest_rule_extension(
        self, case: Dict[str, Any], root_cause: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """规则库扩展建议（仅对未被 CRASH_PATTERNS 覆盖的新异常）"""
        if root_cause["type"] != "exception":
            return None
        if root_cause.get("covered"):
            return None
        if self._is_pattern_exists(root_cause["pattern"]):
            return None
        return {
            "action": "add_crash_pattern",
            "category": root_cause["category"],
            "pattern": root_cause["pattern"],
            "tc_id": case.get("tc_id", ""),
            "reason": f"用例 {case.get('tc_id', '')} 失败，根因为 {root_cause['detail'][:80]}",
            "ai_review_required": True,
        }

    def _suggest_prompt_tuning(
        self, case: Dict[str, Any], root_cause: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """提示词调优建议（仅 manual 用例，因 manual 表示 AI 无法自动判定）"""
        if case.get("verdict") != "manual":
            return None
        fs = case.get("feedback_signal") or {}
        suggested = fs.get("suggested_prompt", "")
        return {
            "action": "tune_ai_prompt",
            "tc_id": case.get("tc_id", ""),
            "current_prompt_hint": suggested or "manual 用例未给出明确判定",
            "reason": case.get("reason", "")[:80],
            "ai_review_required": True,
        }

    def _suggest_known_issue(
        self, case: Dict[str, Any], root_cause: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """陷阱库沉淀建议"""
        return {
            "tc_id": case.get("tc_id", ""),
            "title": case.get("title", ""),
            "category": root_cause["category"],
            "scenario": case.get("reason", "")[:120],
            "root_cause": root_cause["detail"][:200],
            "workaround": "待 AI 审阅补充",
            "verdict": case.get("verdict", ""),
        }

    def _is_pattern_exists(self, pattern: str) -> bool:
        """检查模式是否已在 CRASH_PATTERNS 中（字符串相等）"""
        for regexes in config.CRASH_PATTERNS.values():
            if pattern in regexes:
                return True
        return False

    def _build_regression_entry(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """构建回归历史条目"""
        cases = report.get("cases", [])
        total = len(cases)
        pass_n = sum(1 for c in cases if c.get("verdict") == "pass")
        fail_n = sum(1 for c in cases if c.get("verdict") == "fail")
        manual_n = sum(1 for c in cases if c.get("verdict") == "manual")
        manual_ratio = round(manual_n / total * 100, 1) if total else 0.0
        pass_rate = round(pass_n / total * 100, 1) if total else 0.0

        patterns: Dict[str, int] = {}
        for c in cases:
            if c.get("verdict") in ("fail", "manual"):
                fs = c.get("feedback_signal") or {}
                p = fs.get("failure_pattern") or c.get("reason", "unknown")[:30]
                patterns[p] = patterns.get(p, 0) + 1
        top3 = [p for p, _ in sorted(patterns.items(), key=lambda x: -x[1])[:3]]

        return {
            "timestamp": datetime.now().isoformat(),
            "apk_info": report.get("apk_info", {}),
            "total_cases": total,
            "pass": pass_n,
            "fail": fail_n,
            "manual": manual_n,
            "pass_rate": pass_rate,
            "manual_ratio": manual_ratio,
            "failure_patterns_top3": top3,
        }

    def _append_regression_history(self, entry: Dict[str, Any]) -> None:
        """追加回归历史到 regression_history.md（不存在则创建初始表头）"""
        path = self.regression_history_path
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# 回归历史\n\n"
                "> 由 M16 反馈闭环自动追加，AI 审阅后可补充分析\n\n"
                "| 时间 | APK 版本 | 用例数 | pass | fail | manual | pass率 | manual率 | 失败模式Top3 |\n"
                "|------|---------|-------|------|------|--------|-------|---------|-------------|\n",
                encoding="utf-8",
            )
        apk_ver = entry.get("apk_info", {}).get("name", "N/A")
        ts = entry.get("timestamp", "")[:19]
        top3 = ", ".join(entry.get("failure_patterns_top3", [])) or "无"
        line = (
            f"| {ts} | {apk_ver} | {entry['total_cases']} | {entry['pass']} | "
            f"{entry['fail']} | {entry['manual']} | {entry['pass_rate']}% | "
            f"{entry['manual_ratio']}% | {top3} |\n"
        )
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
        logger.info(f"回归历史已追加: {path}")

    def _append_known_issue(self, issue: Dict[str, Any]) -> None:
        """追加陷阱到 known_issues.md（不存在则创建初始表头）"""
        path = self.known_issues_path
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# 已知问题与陷阱库\n\n"
                "> 由 M16 反馈闭环自动追加，AI 审阅后补充规避方式\n\n"
                "## 分类\n"
                "- 环境类\n- 兼容类\n- 源码类\n- 规则类\n- 提示词类\n\n"
                "## 陷阱列表\n\n",
                encoding="utf-8",
            )
        block = (
            f"### [{issue['tc_id']}] {issue['title']}\n"
            f"- **分类**：{issue['category']}\n"
            f"- **场景描述**：{issue['scenario']}\n"
            f"- **根因**：{issue['root_cause']}\n"
            f"- **规避方式**：{issue['workaround']}\n"
            f"- **关联 TC-ID**：{issue['tc_id']}\n"
            f"- **verdict**：{issue['verdict']}\n\n"
        )
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
        logger.info(f"陷阱已追加: {path}")


def main():
    parser = argparse.ArgumentParser(description="M16 反馈闭环处理（任务 16）")
    parser.add_argument("--report", type=str, help="report.json 路径")
    parser.add_argument("-o", "--output", type=str, help="输出 suggestions JSON 路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="启用 DEBUG 日志")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检后退出")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.self_test:
        _run_self_test()
        return

    if not args.report:
        print("ERROR: 需要 --report 参数指定 report.json 路径", file=sys.stderr)
        sys.exit(2)

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: 报告不存在: {report_path}", file=sys.stderr)
        sys.exit(2)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fl = FeedbackLoop()
    result = fl.process(report)
    out = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"反馈建议已写入: {args.output}")
    else:
        print(out)


def _run_self_test():
    """内置自检程序（原生 assert，3 类用例：正常/边界/异常）

    覆盖：
    - 正常用例：mock report 含 1 fail（新异常）+ 1 manual，验证 4 类输出 + 文件追加
    - 边界用例：空 cases，验证 regression_history_entry total=0 且文件创建
    - 异常用例：case 缺 feedback_signal/reason，验证不崩溃
    """
    import tempfile
    import shutil

    tmp = Path(tempfile.mkdtemp(prefix="feedback_loop_test_"))
    try:
        ki = tmp / "known_issues.md"
        rh = tmp / "regression_history.md"
        fl = FeedbackLoop(known_issues_path=ki, regression_history_path=rh)

        # --- 正常用例 ---
        report = {
            "apk_info": {"name": "legado-debug-1.0.apk"},
            "cases": [
                {
                    "tc_id": "TC-FAIL-01",
                    "title": "新异常用例",
                    "verdict": "fail",
                    "reason": "抛出 CustomTimeoutException 等待元素超时",
                    "feedback_signal": {
                        "failure_pattern": "CustomTimeoutException 等待元素超时",
                    },
                },
                {
                    "tc_id": "TC-MANUAL-01",
                    "title": "需人工判定",
                    "verdict": "manual",
                    "reason": "截图无法自动判定 UI 正确性",
                    "feedback_signal": {
                        "failure_pattern": "manual: 截图判定",
                        "suggested_prompt": "增加 UI 元素断言提示",
                    },
                },
            ],
        }
        result = fl.process(report)
        # 1. rule_suggestions：新异常 CustomTimeoutException 应建议扩展
        assert len(result["rule_suggestions"]) == 1, (
            f"期望 1 条规则建议，实际 {len(result['rule_suggestions'])}"
        )
        assert result["rule_suggestions"][0]["pattern"] == "CustomTimeoutException"
        assert result["rule_suggestions"][0]["action"] == "add_crash_pattern"
        # 2. prompt_suggestions：仅 manual 用例
        assert len(result["prompt_suggestions"]) == 1
        assert result["prompt_suggestions"][0]["tc_id"] == "TC-MANUAL-01"
        # 3. known_issue_suggestions：fail + manual 各一
        assert len(result["known_issue_suggestions"]) == 2
        # 4. regression_history_entry
        entry = result["regression_history_entry"]
        assert entry["total_cases"] == 2
        assert entry["fail"] == 1
        assert entry["manual"] == 1
        assert entry["pass"] == 0
        # 文件追加验证
        assert ki.exists(), "known_issues.md 应被创建"
        ki_content = ki.read_text(encoding="utf-8")
        assert "TC-FAIL-01" in ki_content
        assert "TC-MANUAL-01" in ki_content
        assert rh.exists(), "regression_history.md 应被创建"
        rh_content = rh.read_text(encoding="utf-8")
        assert "legado-debug-1.0.apk" in rh_content
        assert "| 2 |" in rh_content  # total_cases=2

        # --- 边界用例：空 cases ---
        fl2 = FeedbackLoop(
            known_issues_path=tmp / "ki2.md",
            regression_history_path=tmp / "rh2.md",
        )
        result2 = fl2.process({"cases": [], "apk_info": {}})
        assert result2["regression_history_entry"]["total_cases"] == 0
        assert result2["rule_suggestions"] == []
        assert result2["prompt_suggestions"] == []
        assert result2["known_issue_suggestions"] == []
        assert tmp.joinpath("rh2.md").exists(), "空报告也应创建 regression_history.md"
        # _is_pattern_exists 边界
        assert fl2._is_pattern_exists("FATAL EXCEPTION") is True
        assert fl2._is_pattern_exists("NotExist") is False

        # --- 异常用例：case 缺字段 ---
        fl3 = FeedbackLoop(
            known_issues_path=tmp / "ki3.md",
            regression_history_path=tmp / "rh3.md",
        )
        result3 = fl3.process({
            "cases": [{"tc_id": "TC-X", "verdict": "fail"}],  # 无 reason/feedback_signal
        })
        rc = fl3._extract_root_cause({"tc_id": "TC-X", "verdict": "fail"})
        assert rc["type"] == "unknown"
        assert rc["pattern"] == ""
        assert rc["covered"] is False
        # 缺字段不应崩溃，known_issue 仍应追加
        assert len(result3["known_issue_suggestions"]) == 1

        print("✅ feedback_loop.py 自检全部通过（3/3 用例）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
