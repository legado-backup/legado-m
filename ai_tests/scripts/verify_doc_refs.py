#!/usr/bin/env python3
"""蓝图质量校验工具（ui-subpage-optimization A5.4 + A5.7a/b）

对 `docs/UI/` 123 页蓝图做**只读**校验与清单产出，三种模式：

- `refs`（默认）：引用校验 —— 抓 `Xxx.kt:123` 形态引用，校验 ①文件是否存在 ②行号是否越界
  （行数口径 = .NET `ReadAllLines().Count`，用 `splitlines()` 对齐，**不要**用会漏计空行的
  `Measure-Object -Line`）③输出**格式不统一清单**（真痛点：`Xxx.kt:123` / `Xxx.kt` 无行号 /
  `:123` 省略类名 / 零引用），并统计「优化项明细节内零引用」的页（A5.5 下沉依据）
- `sections`：`interaction.md` 每页**实际章节清单**（A5.7b：全文「六节」为伪结构，实为 8–13 节）
- `proto`：`interactions-optimized.html` 覆盖清单（A5.7a：41 页缺失）

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/verify_doc_refs.py [--mode refs|sections|proto]
        [--page main/bookshelf] [--limit 5] [--out <报告路径>]
退出码：0=全部通过（无缺失文件 / 无越界），1=存在硬失败
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "docs" / "UI"
SRC_ROOT = ROOT / "app" / "src" / "main"

FILE_RX = re.compile(r"[A-Za-z_][\w./]*\.(?:kt|java|xml)")
LINE_SUFFIX_RX = re.compile(r":(\d+)")
BARE_LINE_RX = re.compile(r"`:(\d+)`")
DETAIL_HEAD_RX = re.compile(r"^###\s*优化")


def _index_sources() -> dict[str, list[Path]]:
    """basename → 源文件路径列表（同名多文件时标歧义）。"""
    idx: dict[str, list[Path]] = {}
    for p in SRC_ROOT.rglob("*"):
        if p.suffix in (".kt", ".java", ".xml") and p.is_file():
            idx.setdefault(p.name, []).append(p)
    return idx


def _pages() -> list[Path]:
    """123 页目录（含 OPTIMIZATION.md，排除 docs/UI 根）。"""
    out = []
    for md in UI_DIR.rglob("OPTIMIZATION.md"):
        if md.parent != UI_DIR:
            out.append(md.parent)
    return sorted(out)


def _refs_in(text: str) -> tuple[list[tuple[str, int]], list[str]]:
    """返回 (带行号引用列表, 无行号引用列表)。"""
    with_line: list[tuple[str, int]] = []
    without_line: list[str] = []
    for m in FILE_RX.finditer(text):
        name = m.group(0).rsplit("/", 1)[-1]
        suffix = LINE_SUFFIX_RX.match(text, m.end())
        if suffix:
            with_line.append((name, int(suffix.group(1))))
        else:
            without_line.append(name)
    return with_line, without_line


def mode_refs(pages: list[Path], src_idx: dict[str, list[Path]]) -> tuple[int, list[str]]:
    lines: list[str] = []
    hard_fail = 0
    no_ref_pages: list[str] = []
    fmt_issues: list[str] = []
    total_refs = 0
    missing: list[str] = []
    overflow: list[str] = []
    ambiguous: list[str] = []

    for page in pages:
        rel = page.relative_to(UI_DIR).as_posix()
        text = (page / "OPTIMIZATION.md").read_text(encoding="utf-8", errors="ignore")
        all_refs, no_line = _refs_in(text)
        total_refs += len(all_refs)

        # 优化项明细块的引用计数（A5.5 下沉依据）
        blocks = re.split(r"^(?=###\s)", text, flags=re.M)
        detail = [b for b in blocks if DETAIL_HEAD_RX.match(b)]
        detail_zero = [b.splitlines()[0][:50] for b in detail if not _refs_in(b)[0]]

        if detail and len(detail_zero) == len(detail):
            no_ref_pages.append(rel)

        if no_line:
            fmt_issues.append(f"{rel}: 无行号引用 {len(no_line)} 处（例：{no_line[0]}）")
        bare = BARE_LINE_RX.findall(text)
        if bare:
            fmt_issues.append(f"{rel}: 省略类名写法 `:N` {len(bare)} 处（例：`:{bare[0]}`）")
        if detail_zero:
            fmt_issues.append(f"{rel}: 优化项明细零引用 {len(detail_zero)}/{len(detail)} 块")

        # 存在性 + 行号校验（去重）
        for name, ln in sorted(set(all_refs)):
            paths = src_idx.get(name)
            if not paths:
                missing.append(f"{rel}: {name}:{ln}（源文件不存在）")
                continue
            if len(paths) > 1:
                ambiguous.append(f"{rel}: {name}:{ln}（同名 {len(paths)} 个文件）")
                continue
            try:
                count = len(paths[0].read_text(encoding="utf-8", errors="ignore").splitlines())
            except OSError:
                continue
            if ln > count:
                overflow.append(
                    f"{rel}: {name}:{ln}（文件仅 {count} 行）"
                )

    hard_fail = len(missing) + len(overflow)
    lines.append(f"# 蓝图引用校验报告（refs）")
    lines.append("")
    lines.append(f"- 扫描页数：{len(pages)}")
    lines.append(f"- 带行号引用总数：{total_refs}")
    lines.append(f"- 源文件不存在：{len(missing)}")
    lines.append(f"- 行号越界：{len(overflow)}")
    lines.append(f"- 同名歧义（未判越界）：{len(ambiguous)}")
    lines.append(f"- 「优化项明细全块零引用」页数：{len(no_ref_pages)}")
    lines.append("")
    lines.append("## 格式不统一清单（A5.5 依据）")
    lines.extend(f"- {x}" for x in fmt_issues) or lines.append("- （无）")
    lines.append("")
    lines.append("## 优化项明细零引用页清单（证据需下沉至明细节）")
    lines.extend(f"- {x}" for x in no_ref_pages) or lines.append("- （无）")
    if missing:
        lines.append("")
        lines.append("## 源文件不存在（硬失败）")
        lines.extend(f"- {x}" for x in missing)
    if overflow:
        lines.append("")
        lines.append("## 行号越界（硬失败）")
        lines.extend(f"- {x}" for x in overflow)
    if ambiguous:
        lines.append("")
        lines.append("## 同名歧义（需人工确认）")
        lines.extend(f"- {x}" for x in ambiguous)
    return hard_fail, lines


def mode_sections(pages: list[Path]) -> tuple[int, list[str]]:
    lines = ["# interaction.md 实际章节清单（A5.7b）", ""]
    lines.append(f"- 页数：{len(pages)}")
    dist: dict[int, int] = {}
    missing_key: list[str] = []
    for page in pages:
        rel = page.relative_to(UI_DIR).as_posix()
        f = page / "interaction.md"
        if not f.exists():
            lines.append(f"- {rel}: interaction.md 缺失")
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        heads = re.findall(r"^##\s+(.+)$", text, flags=re.M)
        dist[len(heads)] = dist.get(len(heads), 0) + 1
        lines.append(f"- {rel}: {len(heads)} 节 | {' / '.join(h.strip() for h in heads)}")
        if not any("对话框" in h for h in heads) or not any("主题" in h for h in heads):
            missing_key.append(rel)
    lines.append("")
    lines.append("## 章节数分布")
    lines.extend(f"- {k} 节：{v} 页" for k, v in sorted(dist.items()))
    lines.append("")
    lines.append(f"## 缺关键节（对话框清单 / 主题适配）的页：{len(missing_key)}")
    lines.extend(f"- {x}" for x in missing_key)
    return 0, lines


def mode_proto(pages: list[Path]) -> tuple[int, list[str]]:
    lines = ["# interactions-optimized.html 覆盖清单（A5.7a）", ""]
    miss: list[str] = []
    for page in pages:
        rel = page.relative_to(UI_DIR).as_posix()
        if not (page / "interactions-optimized.html").exists():
            miss.append(rel)
    lines.append(f"- 页数：{len(pages)}，缺失 {len(miss)} 页")
    lines.append("")
    lines.append("## 缺失页清单（处置：①补原型 ②标注「交互项无原型承载，暂不验收」）")
    lines.extend(f"- [ ] {x}" for x in miss) or lines.append("- （无）")
    return 0, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="refs", choices=["refs", "sections", "proto"])
    ap.add_argument("--page", default=None, help="只跑单页（相对 docs/UI 的路径，如 main/bookshelf）")
    ap.add_argument("--limit", type=int, default=0, help="抽验前 N 页（批次入口抽验用，0=全量）")
    ap.add_argument("--out", default=None, help="报告落盘路径")
    args = ap.parse_args()

    pages = _pages()
    if args.page:
        pages = [p for p in pages if p.relative_to(UI_DIR).as_posix() == args.page]
        if not pages:
            print(f"!! 未找到页：{args.page}")
            return 1
    elif args.limit > 0:
        pages = pages[: args.limit]

    if args.mode == "refs":
        hard_fail, lines = mode_refs(pages, _index_sources())
    elif args.mode == "sections":
        hard_fail, lines = mode_sections(pages)
    else:
        hard_fail, lines = mode_proto(pages)

    report = "\n".join(lines)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        print(f"报告已写入：{out}")
    head = lines[:8]
    print("\n".join(head))
    print(f"... （完整 {len(lines)} 行{'，已落盘' if args.out else ''}）")
    print(f"[{'FAIL' if hard_fail else 'PASS'}] 硬失败 {hard_fail} 项")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
