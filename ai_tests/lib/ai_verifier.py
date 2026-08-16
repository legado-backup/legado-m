"""ai_tests/lib/ai_verifier.py — AiVerifier（AI-LLM-Testing 判定器）

职责（AD-04）：仅处理 verdict=manual 的用例——
读取 ai-prompt.md（含用例信息/证据摘要/预期/步骤）+ 截图图像，
调用本地 VL 模型（Qwen3VL）结构化判定，回填 report.json 的 cases[].ai_verdict。

数据流：report.json → 逐 manual 用例 → chat_json(system, ai_prompt, screenshots)
        → {verdict, confidence, reason, evidence_refs} → 回填 report.json
        → 生成 ai_verdicts.md 汇总。

模型不可用时抛 LlmUnavailableError（调用方优雅降级 rules-only，R6）。
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_tests.config import REPORTS_DIR
from ai_tests.config_ai import AI_MODEL_ID
from ai_tests.lib.llm_client import LlmClient
from ai_tests.lib.llm_server import LlmUnavailableError

logger = logging.getLogger(__name__)

# 单用例最多送 VL 的截图数（降采样后 ~640px，控制上下文/耗时）
MAX_SCREENSHOTS_PER_CASE = 4

SYSTEM_PROMPT = (
    "你是 Android 应用自动化测试的资深判定员。你会收到一个测试用例的说明、"
    "预期结果、证据摘要以及真实界面截图。请基于证据（尤其截图呈现的实际界面状态）"
    "判定该用例最终结果。证据不足时判 manual，不要臆测。"
)

SCHEMA_HINT = (
    "\n\n【输出要求】只输出一个合法 JSON 对象，schema：\n"
    '{"verdict": "pass|fail|manual", "confidence": 0~100 的整数, '
    '"reason": "简要中文判定理由", "evidence_refs": ["引用的证据/截图文件名"]}\n'
    "verdict 为 manual 仅当证据确实不足以判定。confidence<70 时自动视为 manual。"
)


class AiVerifier:
    """manual 用例视觉判定器（回填 report.json ai_verdict）"""

    def __init__(
        self,
        client: Optional[LlmClient] = None,
        report_dir: Optional[Path] = None,
    ):
        self.client = client or LlmClient()
        self.report_dir = Path(report_dir) if report_dir else REPORTS_DIR

    # === 单用例判定 ===

    def verify_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """判定单个 manual 用例，返回 ai_verdict 结构。

        Args:
            case: report.json 中的用例 dict（需含 ai_prompt_path）
        Returns:
            {"verdict", "confidence", "reason", "evidence_refs", "verified_at", "model"}
        """
        tc_dir, ai_prompt, screenshots = self._collect_inputs(case)
        if ai_prompt is None and not screenshots:
            return {
                "verdict": "manual",
                "confidence": 0,
                "reason": "无 ai-prompt 与截图证据，VL 判定跳过",
                "evidence_refs": [],
                "verified_at": datetime.now().isoformat(timespec="seconds"),
                "model": AI_MODEL_ID,
                "skipped": True,
            }
        user = (ai_prompt or "（无 ai-prompt，仅依据截图）") + SCHEMA_HINT
        try:
            obj = self.client.chat_json(SYSTEM_PROMPT, user, screenshots)
        except LlmUnavailableError:
            raise
        return self._normalize(obj, screenshots)

    def _collect_inputs(
        self, case: Dict[str, Any]
    ) -> tuple:
        """提取 (tc_dir, ai_prompt 文本, 截图绝对路径列表)"""
        prompt_path = case.get("ai_prompt_path")
        ai_prompt = None
        tc_dir: Optional[Path] = None
        if prompt_path and Path(prompt_path).exists():
            tc_dir = Path(prompt_path).parent
            ai_prompt = Path(prompt_path).read_text(encoding="utf-8")
        elif tc_dir is None:
            # 兜底：从 ai_prompt 或 evidence 目录推断
            return None, None, []

        screenshots: List[str] = []
        if tc_dir is not None:
            shot_dir = tc_dir / "screenshot"
            if shot_dir.exists():
                files = sorted(shot_dir.glob("*.png"))
                screenshots = [str(f) for f in files[:MAX_SCREENSHOTS_PER_CASE]]
        return tc_dir, ai_prompt, screenshots

    def _normalize(
        self, obj: Dict[str, Any], screenshots: List[str]
    ) -> Dict[str, Any]:
        """规范化为 ai_verdict（校验 verdict/confidence，<70 强转 manual）"""
        verdict = str(obj.get("verdict", "manual")).strip().lower()
        if verdict not in ("pass", "fail", "manual"):
            verdict = "manual"
        try:
            confidence = int(obj.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0
        if confidence < 70 and verdict != "manual":
            verdict = "manual"
        refs = obj.get("evidence_refs", [])
        if not isinstance(refs, list):
            refs = [str(refs)]
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reason": str(obj.get("reason", "")),
            "evidence_refs": refs,
            "screenshots_used": len(screenshots),
            "verified_at": datetime.now().isoformat(timespec="seconds"),
            "model": AI_MODEL_ID,
        }

    # === report.json 批量判定 ===

    def verify_report(
        self,
        report_path: Optional[Path] = None,
        tc_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """读取 report.json → 判定全部（或指定 tc）manual 用例 → 回填保存。

        Returns:
            {"report_path", "manual_total", "ai_verified", "skipped", "ai_unavailable"}
        """
        report_path = Path(report_path) if report_path else self.report_dir / "report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"report.json 不存在: {report_path}")

        data = json.loads(report_path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        manual_cases = [
            c for c in cases
            if c.get("verdict") == "manual"
            and (tc_filter is None or c.get("tc_id") == tc_filter)
        ]
        summary = {
            "report_path": str(report_path),
            "manual_total": len(manual_cases),
            "ai_verified": 0,
            "skipped": 0,
            "ai_unavailable": False,
        }
        if not manual_cases:
            self._save_summary(data, summary)
            return summary

        for case in manual_cases:
            try:
                av = self.verify_case(case)
            except LlmUnavailableError as e:
                logger.warning("VL 不可用，判定器降级 rules-only: %s", e)
                summary["ai_unavailable"] = True
                break
            except Exception as e:
                logger.error("用例 %s 判定异常: %s", case.get("tc_id"), e)
                av = {
                    "verdict": "manual",
                    "confidence": 0,
                    "reason": f"判定异常: {type(e).__name__}: {e}",
                    "evidence_refs": [],
                    "verified_at": datetime.now().isoformat(timespec="seconds"),
                    "model": AI_MODEL_ID,
                }
            case["ai_verdict"] = av
            if av.get("skipped"):
                summary["skipped"] += 1
            else:
                summary["ai_verified"] += 1

        report_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._save_summary(data, summary)
        logger.info(
            "AI 判定完成: manual=%d verified=%d skipped=%d",
            summary["manual_total"], summary["ai_verified"], summary["skipped"],
        )
        return summary

    # === 汇总 ===

    def _save_summary(self, data: Dict[str, Any], summary: Dict[str, Any]) -> None:
        """生成 ai_verdicts.md 汇总（不动固化层 manual_cases.md）"""
        out = [f"# AI 判定汇总（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）", ""]
        out.append(f"- manual 用例数: {summary['manual_total']}")
        out.append(f"- AI 已判定: {summary['ai_verified']}")
        out.append(f"- 跳过（证据不足）: {summary['skipped']}")
        out.append(f"- VL 不可用: {summary['ai_unavailable']}")
        out.append("")
        if summary.get("ai_unavailable"):
            out.append("> 模型服务不可用，判定器已降级（规则判定结果保持不变）。")
            out.append("")
        for case in data.get("cases", []):
            av = case.get("ai_verdict")
            if av:
                out.append(f"### {case.get('tc_id')}: {case.get('title')}")
                out.append(f"- 规则判定: {case.get('verdict')} (conf={case.get('confidence')})")
                out.append(f"- AI 判定: **{av.get('verdict')}** (conf={av.get('confidence')})")
                out.append(f"- 理由: {av.get('reason', '')}")
                out.append(f"- 引用证据: {', '.join(av.get('evidence_refs', []))}")
                out.append("")
        save_path = self.report_dir / "ai_verdicts.md"
        save_path.write_text("\n".join(out), encoding="utf-8")
        summary["ai_verdicts_md"] = str(save_path)


# === 自检 ===
if __name__ == "__main__":
    print("[IMPORT OK] ai_verifier")
