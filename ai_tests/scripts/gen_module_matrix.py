"""ai_tests/scripts/gen_module_matrix.py — 核心模块矩阵报告生成器

职责（任务 14.4）：
- 扫描 docs/tests/*.md + ai_tests/cases/*/*.md 全部用例
- 复用 CaseParser（M3）解析结构化 TestCase（不重复造轮子）
- 按模块统计：用例数、关联源码覆盖率、关联 Activity 覆盖率、缺失项清单
- 输出 Markdown 报告到 ai_tests/docs/module_matrix.md

依赖：CaseParser（M3，复用不新增）
退出码：0=全覆盖，1=部分缺失，2=无用例
"""
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

# 项目根加入 sys.path（脚本可独立运行）
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_tests import config
from ai_tests.lib.case_parser import CaseParser, TestCase

logger = logging.getLogger(__name__)


class ModuleMatrixGenerator:
    """核心模块矩阵报告生成器

    复用 CaseParser 解析用例，按模块统计源码溯源字段覆盖情况
    """

    def __init__(self):
        self.parser = CaseParser()
        self.cases: List[TestCase] = []
        self._scanned: bool = False  # 是否已调用过 scan_cases

    def scan_cases(
        self,
        docs_dir: Path = None,
        cases_dir: Path = None,
    ) -> List[TestCase]:
        """扫描 docs/tests/*.md + ai_tests/cases/*/*.md 所有用例

        跳过 README.md / _index.md（非用例）
        运行时从 config 模块读取路径常量，支持测试时覆盖
        """
        docs_dir = docs_dir or config.DOCS_TESTS_DIR
        cases_dir = cases_dir or config.AI_TESTS_CASES_DIR
        cases: List[TestCase] = []
        # 1. docs/tests/*.md（存量用例，第一波覆盖）
        if docs_dir.exists():
            for md in docs_dir.glob("*.md"):
                if md.name in ("README.md", "_index.md"):
                    continue
                try:
                    cases.extend(self.parser.parse_file(md))
                except Exception as e:
                    logger.error(f"解析 {md} 失败: {e}")
        # 2. ai_tests/cases/*/*.md（V3 双轨，第二波覆盖）
        if cases_dir.exists():
            for md in cases_dir.rglob("*.md"):
                if md.name in ("README.md", "_index.md"):
                    continue
                try:
                    cases.extend(self.parser.parse_file(md))
                except Exception as e:
                    logger.error(f"解析 {md} 失败: {e}")
        self.cases = cases
        self._scanned = True
        return cases

    def compute_matrix(self) -> Dict[str, Dict[str, Any]]:
        """按模块统计用例数、覆盖率、缺失项

        Returns:
            {module: {total, with_source, with_activity,
                      missing_source: [tc_id], missing_activity: [tc_id], cases: [tc_id]}}
        """
        matrix: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "with_source": 0,
            "with_activity": 0,
            "missing_source": [],
            "missing_activity": [],
            "cases": [],
        })
        for tc in self.cases:
            mod = tc.module or "未分类"
            entry = matrix[mod]
            entry["total"] += 1
            entry["cases"].append(tc.tc_id)
            if tc.related_source:
                entry["with_source"] += 1
            else:
                entry["missing_source"].append(tc.tc_id)
            if tc.related_activity:
                entry["with_activity"] += 1
            else:
                entry["missing_activity"].append(tc.tc_id)
        return dict(matrix)

    @staticmethod
    def _rate(numer: int, denom: int) -> str:
        """安全计算覆盖率字符串"""
        if denom == 0:
            return "N/A"
        return f"{numer}/{denom} ({numer / denom * 100:.1f}%)"

    def generate_markdown(self) -> str:
        """生成 module_matrix.md 内容

        若未调用过 scan_cases，自动扫描默认路径；否则复用已扫描结果
        """
        if not self._scanned:
            self.scan_cases()
        matrix = self.compute_matrix()
        total_cases = len(self.cases)
        total_modules = len(matrix)
        total_with_source = sum(m["with_source"] for m in matrix.values())
        total_with_activity = sum(m["with_activity"] for m in matrix.values())
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines: List[str] = [
            "# 核心模块矩阵报告",
            "",
            f"> **生成时间**：{ts}",
            f"> **用例总数**：{total_cases}",
            f"> **模块总数**：{total_modules}",
            f"> **关联源码覆盖率**：{self._rate(total_with_source, total_cases)}",
            f"> **关联 Activity 覆盖率**：{self._rate(total_with_activity, total_cases)}",
            "",
            "## 模块矩阵",
            "",
            "| 模块 | 用例数 | 源码覆盖率 | Activity 覆盖率 | 缺失源码 | 缺失 Activity |",
            "|------|-------|----------|---------------|---------|--------------|",
        ]
        for mod in sorted(matrix.keys()):
            entry = matrix[mod]
            total = entry["total"]
            src_rate = self._rate(entry["with_source"], total)
            act_rate = self._rate(entry["with_activity"], total)
            miss_src = "、".join(entry["missing_source"][:3])
            if len(entry["missing_source"]) > 3:
                miss_src += f" 等{len(entry['missing_source'])}项"
            miss_src = miss_src or "✅ 完整"
            miss_act = "、".join(entry["missing_activity"][:3])
            if len(entry["missing_activity"]) > 3:
                miss_act += f" 等{len(entry['missing_activity'])}项"
            miss_act = miss_act or "✅ 完整"
            lines.append(
                f"| {mod} | {total} | {src_rate} | {act_rate} | {miss_src} | {miss_act} |"
            )

        lines.extend(["", "## 缺失明细", ""])
        has_missing = False
        for mod in sorted(matrix.keys()):
            entry = matrix[mod]
            if not (entry["missing_source"] or entry["missing_activity"]):
                continue
            has_missing = True
            lines.append(f"### {mod}")
            lines.append("")
            if entry["missing_source"]:
                lines.append(
                    f"**缺失关联源码**（{len(entry['missing_source'])}/{entry['total']}）："
                )
                lines.append("")
                for tc_id in entry["missing_source"]:
                    lines.append(f"- {tc_id}")
                lines.append("")
            if entry["missing_activity"]:
                lines.append(
                    f"**缺失关联 Activity**（{len(entry['missing_activity'])}/{entry['total']}）："
                )
                lines.append("")
                for tc_id in entry["missing_activity"]:
                    lines.append(f"- {tc_id}")
                lines.append("")
        if not has_missing:
            lines.append("✅ 所有用例均已补全关联源码与关联 Activity 字段。")
            lines.append("")

        # 覆盖率判定
        lines.extend(["---", "", "## 覆盖率判定", ""])
        if total_cases == 0:
            lines.append("⚠️ 未扫描到任何用例，请检查 docs/tests/ 与 ai_tests/cases/ 目录。")
        elif total_with_source == total_cases and total_with_activity == total_cases:
            lines.append("✅ 全覆盖：所有用例已补全 V3 源码溯源字段。")
        else:
            lines.append(
                f"⚠️ 部分覆盖：源码 {total_with_source}/{total_cases}，"
                f"Activity {total_with_activity}/{total_cases}，需补全缺失项。"
            )
        return "\n".join(lines)

    def generate(self, output_path: Path = None) -> str:
        """主入口：生成并写入 module_matrix.md

        Args:
            output_path: 输出路径，默认 ai_tests/docs/module_matrix.md
        Returns:
            Markdown 内容字符串
        """
        content = self.generate_markdown()
        out = output_path or (PROJECT_ROOT / "ai_tests" / "docs" / "module_matrix.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        logger.info(f"模块矩阵报告已生成: {out}")
        return content


def main():
    parser = argparse.ArgumentParser(
        description="生成核心模块矩阵报告（任务 14.4）"
    )
    parser.add_argument(
        "-o", "--output", type=str,
        help="输出文件路径（默认 ai_tests/docs/module_matrix.md）"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="启用 DEBUG 日志"
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="运行内置自检程序后退出"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.self_test:
        _run_self_test()
        return

    gen = ModuleMatrixGenerator()
    content = gen.generate(Path(args.output) if args.output else None)
    print(content)

    # 退出码判定
    matrix = gen.compute_matrix()
    total = sum(m["total"] for m in matrix.values())
    ws = sum(m["with_source"] for m in matrix.values())
    if total == 0:
        print("WARNING: 未扫描到任何用例", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if ws == total else 1)


def _run_self_test():
    """内置自检程序（原生 assert，3 类用例：正常/边界/异常）

    覆盖：
    - 正常用例：1 个含完整 V3 字段的 MD
    - 边界用例：空目录
    - 异常用例：缺失关联源码/Activity 字段的 MD
    """
    import tempfile
    import shutil

    def _setup_temp(tmp: Path):
        """构造临时用例目录"""
        (tmp / "docs" / "tests").mkdir(parents=True)
        (tmp / "ai_tests" / "cases").mkdir(parents=True)

    def _test_normal(tmp: Path):
        """正常用例：1 个含完整字段的 MD"""
        docs_dir = tmp / "docs" / "tests"
        cases_dir = tmp / "ai_tests" / "cases"
        md = docs_dir / "F-P0-1-test.md"
        md.write_text(
            "## TC-F-P0-1-01：正常用例\n\n"
            "**关联源码**：TestActivity.kt\n\n"
            "**关联 Activity**：TestActivity\n\n"
            "**测试步骤**：\n1. 进入页面\n\n"
            "**预期结果**：\n- ✅ 显示\n",
            encoding="utf-8",
        )
        gen = ModuleMatrixGenerator()
        cases = gen.scan_cases(docs_dir=docs_dir, cases_dir=cases_dir)
        assert len(cases) == 1, f"期望 1 用例，实际 {len(cases)}"
        assert cases[0].tc_id == "TC-F-P0-1-01"
        assert cases[0].related_source == ["TestActivity.kt"]
        assert cases[0].related_activity == ["TestActivity"]
        matrix = gen.compute_matrix()
        assert "F-P0-1" in matrix
        assert matrix["F-P0-1"]["total"] == 1
        assert matrix["F-P0-1"]["with_source"] == 1
        assert matrix["F-P0-1"]["with_activity"] == 1
        assert matrix["F-P0-1"]["missing_source"] == []
        content = gen.generate_markdown()
        assert "全覆盖" in content

    def _test_boundary(tmp: Path):
        """边界用例：空目录"""
        gen = ModuleMatrixGenerator()
        cases = gen.scan_cases(
            docs_dir=tmp / "empty1", cases_dir=tmp / "empty2"
        )
        assert cases == [], "空目录应返回空列表"
        content = gen.generate_markdown()
        assert "未扫描到任何用例" in content
        # _rate 边界
        assert gen._rate(0, 0) == "N/A"
        assert gen._rate(5, 10) == "5/10 (50.0%)"

    def _test_exception(tmp: Path):
        """异常用例：缺失字段的用例"""
        docs_dir = tmp / "docs" / "tests"
        cases_dir = tmp / "ai_tests" / "cases"
        md = docs_dir / "F-P0-2-test.md"
        md.write_text(
            "## TC-F-P0-2-01：缺字段\n\n"
            "**测试步骤**：\n1. 进入页面\n\n"
            "**预期结果**：\n- ✅ 显示\n",
            encoding="utf-8",
        )
        gen = ModuleMatrixGenerator()
        cases = gen.scan_cases(docs_dir=docs_dir, cases_dir=cases_dir)
        assert len(cases) == 1
        assert cases[0].related_source == []
        assert cases[0].related_activity == []
        matrix = gen.compute_matrix()
        assert matrix["F-P0-2"]["missing_source"] == ["TC-F-P0-2-01"]
        assert matrix["F-P0-2"]["missing_activity"] == ["TC-F-P0-2-01"]
        content = gen.generate_markdown()
        assert "部分覆盖" in content
        # 退出码
        total = sum(m["total"] for m in matrix.values())
        ws = sum(m["with_source"] for m in matrix.values())
        assert total == 1 and ws == 0

    tmp = Path(tempfile.mkdtemp(prefix="gen_matrix_test_"))
    try:
        _setup_temp(tmp)
        _test_normal(tmp)
        # 正常用例修改了 tmp 内容，重建用于边界测试
        shutil.rmtree(tmp)
        tmp.mkdir()
        _test_boundary(tmp)
        # 重建用于异常测试
        shutil.rmtree(tmp)
        tmp.mkdir()
        (tmp / "docs" / "tests").mkdir(parents=True)
        (tmp / "ai_tests" / "cases").mkdir(parents=True)
        _test_exception(tmp)
        print("✅ gen_module_matrix.py 自检全部通过（3/3 用例）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
