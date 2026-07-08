"""ai_tests/lib/report_generator.py — M7 报告生成器（V3 affected + feedback）

职责：
- generate_markdown: 生成 report.md（失败置顶+manual置顶+全部用例表+执行环境+affected+feedback 节）
- generate_json: 生成 report.json（含 evidence_collected/ai_prompt_path/track_source 字段）
- generate_manual_cases: 生成 manual_cases.md（manual 用例清单+AI agent 接入流程）
- V3 generate_affected_modules: 生成 affected_modules.json
- V3 generate_feedback_suggestions: 生成 feedback_suggestions.md
- generate_all: 五件套统一入口

依赖：Jinja2（模板渲染）, json（标准库）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ai_tests.config import REPORTS_DIR

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器（五件套输出）

    五件套：
    1. report.md — Markdown 报告
    2. report.json — JSON 报告
    3. manual_cases.md — Manual 用例清单
    4. affected_modules.json — V3 受影响模块
    5. feedback_suggestions.md — V3 反馈建议
    """

    def __init__(self, report_dir: Optional[Path] = None):
        """初始化报告生成器

        Args:
            report_dir: 报告输出目录，默认 REPORTS_DIR/{timestamp}/
        """
        self.report_dir = Path(report_dir) if report_dir else (
            REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 环境
        templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # === 9.4 generate_markdown + generate_json ===

    def generate_markdown(
        self,
        results: List[Dict[str, Any]],
        env: Dict[str, Any],
        apk_info: Dict[str, Any],
        affected_modules: Optional[Dict[str, Any]] = None,
        feedback_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """生成 Markdown 报告

        简化说明：Jinja2 模板渲染 | 已知上限：模板固定不可动态调整 | 升级路径：支持自定义模板（V4）
        """
        summary = self._calc_summary(results)
        fail_cases = [r for r in results if r.get("verdict") == "fail"]
        manual_cases = [r for r in results if r.get("verdict") == "manual"]

        template = self.env.get_template("report.md.j2")
        content = template.render(
            env=env,
            apk_info=apk_info,
            summary=summary,
            fail_cases=fail_cases,
            manual_cases=manual_cases,
            cases=results,
            affected_modules=affected_modules,
            feedback_signals=feedback_signals,
        )

        save_path = self.report_dir / "report.md"
        save_path.write_text(content, encoding="utf-8")
        logger.info(f"Markdown 报告已生成: {save_path}")
        return content

    def generate_json(
        self,
        results: List[Dict[str, Any]],
        env: Dict[str, Any],
        apk_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成 JSON 报告（含 evidence_collected/ai_prompt_path/track_source 字段）"""
        summary = self._calc_summary(results)
        cases_json = []
        for r in results:
            evidence = r.get("evidence", {})
            evidence_collected = {
                k: v.get("collected", False) if isinstance(v, dict) else False
                for k, v in evidence.items()
            }
            cases_json.append({
                "tc_id": r.get("tc_id", ""),
                "title": r.get("title", ""),
                "module": r.get("module", ""),
                "case_type": r.get("case_type", ""),
                "verdict": r.get("verdict", ""),
                "confidence": r.get("confidence", 0),
                "reason": r.get("reason", ""),
                "evidence_collected": evidence_collected,
                "ai_prompt_path": r.get("ai_prompt_path"),
                "track_source": r.get("track_source", "md"),
                "feedback_signal": r.get("feedback_signal"),
            })

        report = {
            "env": env,
            "apk_info": apk_info,
            "summary": summary,
            "cases": cases_json,
            "generated_at": datetime.now().isoformat(),
        }

        save_path = self.report_dir / "report.json"
        save_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"JSON 报告已生成: {save_path}")
        return report

    # === 9.5 generate_manual_cases ===

    def generate_manual_cases(self, results: List[Dict[str, Any]]) -> str:
        """生成 manual_cases.md（含 manual 用例清单 + AI 提示词路径 + AI agent 接入流程）"""
        manual = [r for r in results if r.get("verdict") == "manual"]
        lines: List[str] = []
        lines.append("# Manual 用例清单")
        lines.append("")
        lines.append("## AI agent 接入流程")
        lines.append("")
        lines.append("1. 读取本文件获取 manual 用例清单")
        lines.append("2. 对每个用例，读取对应的 `ai-prompt.md` 文件")
        lines.append("3. 基于证据摘要和预期结果，给出判定（pass/fail/manual）")
        lines.append("4. 将判定结果回填到 `report.json` 的 `cases[].ai_verdict` 字段")
        lines.append("5. 对 fail 判定，分析 failure_pattern 并沉淀到 known_issues.md")
        lines.append("")
        lines.append(f"## Manual 用例列表（共 {len(manual)} 个）")
        lines.append("")

        if not manual:
            lines.append("无 manual 用例。")
        else:
            for case in manual:
                lines.append(f"### {case.get('tc_id', '')}: {case.get('title', '')}")
                lines.append(f"- 模块: {case.get('module', 'N/A')}")
                lines.append(f"- 原因: {case.get('reason', 'N/A')}")
                prompt_path = case.get("ai_prompt_path", "N/A")
                lines.append(f"- ai-prompt 路径: `{prompt_path}`")
                if case.get("feedback_signal"):
                    fs = case["feedback_signal"]
                    lines.append(f"- 失败模式: `{fs.get('failure_pattern', 'N/A')}`")
                    lines.append(f"- 规则建议: {fs.get('suggested_rule', 'N/A')}")
                lines.append("")

        content = "\n".join(lines)
        save_path = self.report_dir / "manual_cases.md"
        save_path.write_text(content, encoding="utf-8")
        logger.info(f"Manual 用例清单已生成: {save_path}（{len(manual)} 个）")
        return content

    # === 9.6 V3 generate_affected_modules ===

    def generate_affected_modules(self, affected: Dict[str, Any]) -> str:
        """V3 新增：生成 affected_modules.json

        简化说明：直接序列化 dict 为 JSON | 已知上限：无增量更新 | 升级路径：与 git diff 增量合并（V4）
        返回: JSON 字符串内容（与其他 generate_* 方法一致）
        """
        content = json.dumps(affected, ensure_ascii=False, indent=2, default=str)
        save_path = self.report_dir / "affected_modules.json"
        save_path.write_text(content, encoding="utf-8")
        logger.info(
            f"受影响模块报告已生成: {save_path}"
            f"（{len(affected.get('changed_files', []))} 改动, "
            f"{len(affected.get('affected_activities', []))} Activity）"
        )
        return content

    # === 9.7 V3 generate_feedback_suggestions ===

    def generate_feedback_suggestions(
        self, feedback_signals: List[Dict[str, Any]]
    ) -> str:
        """V3 新增：生成 feedback_suggestions.md（规则建议/提示词建议/陷阱库建议）"""
        lines: List[str] = []
        lines.append("# 反馈建议")
        lines.append("")
        lines.append(f"共 {len(feedback_signals)} 条反馈信号，供 AI agent 审阅并沉淀到 M16 反馈闭环。")
        lines.append("")

        # 按类型分组
        rule_suggestions = []
        prompt_suggestions = []
        known_issue_suggestions = []
        for fs in feedback_signals:
            if fs.get("suggested_rule"):
                rule_suggestions.append((fs["tc_id"], fs["suggested_rule"]))
            if fs.get("suggested_prompt"):
                prompt_suggestions.append((fs["tc_id"], fs["suggested_prompt"]))
            if fs.get("failure_pattern"):
                known_issue_suggestions.append(
                    (fs["tc_id"], fs["failure_pattern"], fs.get("verdict", ""))
                )

        lines.append("## 规则建议")
        lines.append("")
        if rule_suggestions:
            for tc_id, suggestion in rule_suggestions:
                lines.append(f"- [{tc_id}] {suggestion}")
        else:
            lines.append("（无）")
        lines.append("")

        lines.append("## 提示词建议")
        lines.append("")
        if prompt_suggestions:
            for tc_id, suggestion in prompt_suggestions:
                lines.append(f"- [{tc_id}] {suggestion}")
        else:
            lines.append("（无）")
        lines.append("")

        lines.append("## 陷阱库建议")
        lines.append("")
        if known_issue_suggestions:
            for tc_id, pattern, verdict in known_issue_suggestions:
                lines.append(f"- [{tc_id}] pattern=`{pattern}`, verdict={verdict}")
        else:
            lines.append("（无）")
        lines.append("")

        content = "\n".join(lines)
        save_path = self.report_dir / "feedback_suggestions.md"
        save_path.write_text(content, encoding="utf-8")
        logger.info(f"反馈建议已生成: {save_path}")
        return content

    def generate_feedback_suggestions_json(
        self, feedback_signals: List[Dict[str, Any]]
    ) -> str:
        """V3 新增：生成 feedback_suggestions.json（机器读，供 M16 回填）

        简化说明：直接序列化 list 为 JSON | 已知上限：无增量更新 | 升级路径：M16 反馈闭环增量合并（V4）
        返回: JSON 字符串内容
        """
        content = json.dumps(feedback_signals, ensure_ascii=False, indent=2, default=str)
        save_path = self.report_dir / "feedback_suggestions.json"
        save_path.write_text(content, encoding="utf-8")
        logger.info(f"反馈建议 JSON 已生成: {save_path}（{len(feedback_signals)} 条）")
        return content

    # === 9.8 generate_summary + summary.txt + 证据归档 ===

    def generate_summary(self, results: List[Dict[str, Any]]) -> str:
        """生成 summary.txt（一行摘要）+ 汇总统计文本 + 证据归档目录"""
        summary = self._calc_summary(results)

        # 生成 summary.txt（一行摘要，供 CLI 退出码判定和快速概览）
        summary_line = (
            f"pass:{summary['pass']}/{summary['total']} "
            f"fail:{summary['fail']} "
            f"manual:{summary['manual']} "
            f"pass_rate:{summary['pass_rate']}%"
        )
        (self.report_dir / "summary.txt").write_text(summary_line, encoding="utf-8")

        # 生成多行汇总统计文本
        lines: List[str] = []
        lines.append("## 汇总统计")
        lines.append(f"- 总用例数: {summary['total']}")
        lines.append(f"- pass: {summary['pass']}")
        lines.append(f"- fail: {summary['fail']}")
        lines.append(f"- warning: {summary['warning']}")
        lines.append(f"- manual: {summary['manual']}")
        lines.append(f"- pass 率: {summary['pass_rate']}%")
        content = "\n".join(lines)

        # 证据归档：每用例独立目录 cases/{tc_id}/
        # 简化说明：证据归档由 M5 collect_all 直接写入 cases/{tc_id}/，此处仅汇总 | 已知上限：未做证据完整性校验 | 升级路径：M5 归档后校验（V4）
        for r in results:
            tc_id = r.get("tc_id", "unknown")
            case_dir = self.report_dir / "cases" / tc_id
            case_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"证据归档目录已创建: {self.report_dir / 'cases'}")
        return content

    def _calc_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算汇总统计"""
        total = len(results)
        verdicts = [r.get("verdict", "manual") for r in results]
        pass_count = verdicts.count("pass")
        fail_count = verdicts.count("fail")
        warning_count = verdicts.count("warning")
        manual_count = verdicts.count("manual")
        pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0
        return {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "warning": warning_count,
            "manual": manual_count,
            "pass_rate": pass_rate,
        }

    # === generate_all 统一入口 ===

    def generate_all(
        self,
        results: List[Dict[str, Any]],
        env: Optional[Dict[str, Any]] = None,
        apk_info: Optional[Dict[str, Any]] = None,
        affected_modules: Optional[Dict[str, Any]] = None,
        feedback_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """生成完整报告套件（七件套）

        Returns: dict {file_type: file_path}
        套件: report.md + report.json + manual_cases.md + summary.txt +
              affected_modules.json + feedback_suggestions.md + feedback_suggestions.json
        可选件: affected_modules / feedback_signals 为 None 时跳过
        """
        env = env or {"device": "MEmu", "timestamp": datetime.now().isoformat()}
        apk_info = apk_info or {"name": "N/A", "size": "N/A"}

        output: Dict[str, str] = {}

        # 1. Markdown 报告
        self.generate_markdown(results, env, apk_info, affected_modules, feedback_signals)
        output["markdown"] = str(self.report_dir / "report.md")

        # 2. JSON 报告
        self.generate_json(results, env, apk_info)
        output["json"] = str(self.report_dir / "report.json")

        # 3. Manual 用例清单
        self.generate_manual_cases(results)
        output["manual_cases"] = str(self.report_dir / "manual_cases.md")

        # 4. V3 受影响模块（可选）
        if affected_modules:
            self.generate_affected_modules(affected_modules)
            output["affected_modules"] = str(self.report_dir / "affected_modules.json")

        # 5. V3 反馈建议（可选，双版本）
        if feedback_signals:
            self.generate_feedback_suggestions(feedback_signals)
            output["feedback_suggestions"] = str(
                self.report_dir / "feedback_suggestions.md"
            )
            self.generate_feedback_suggestions_json(feedback_signals)
            output["feedback_suggestions_json"] = str(
                self.report_dir / "feedback_suggestions.json"
            )

        # 6. 汇总 + summary.txt + 证据归档目录
        self.generate_summary(results)
        output["summary"] = str(self.report_dir / "summary.txt")

        logger.info(
            f"报告套件已生成: {len(output)} 个文件，目录: {self.report_dir}"
        )
        return output


# === 自检（任务 9.9 交付自查）===
# 正常用例：ReportGenerator 可实例化
# 边界用例：空 results 时汇总为 0
# 异常用例：模板不存在时 Jinja2 抛 TemplateNotFound
if __name__ == "__main__":
    rg = ReportGenerator()
    summary = rg._calc_summary([])
    assert summary["total"] == 0
    assert summary["pass_rate"] == 0
    print("[IMPORT OK] report_generator")
