#!/usr/bin/env python3
"""UI-GATE 代码层门禁（ui-subpage-optimization A5.1）

对 app/src/main/java/io/legado/app/ui 做静态断言，防 Compose 化过程中踩项目铁律：
1. `R.layout.*` 引用 —— 全面 Compose 化方向禁止新增 View 布局页（architecture.md 铁律 3）
2. 裸 AlertDialog / alert{} DSL —— 弹框族必须走 ComposeDialogFragment（dialog-shell.md）
3. 硬编码色号 `Color(0x..)` / `Color.BLACK` / `Color.WHITE` / `R.color.md_*`（architecture.md 铁律 1）
4. `SnapshotStateList` 直接下标写入 —— 本项目上下文不落地致界面定格（architecture_rules.md 强制写回）

两种模式（对齐 `theme_color_gate.py` 契约）：
- 默认 `--diff`：只检查 git diff 新增行（防回潮门禁，新增命中即 fail）
- `--all`：全量扫描（存量盘点用；存量命中属历史遗留，由迁移批次消化）
- `--selftest`：内置违规样例自检（A5.1 验收：应命中的全命中、应豁免的零命中）

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/ui_gate.py [--all]
退出码：0=通过（fail=0），1=存在命中
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = "app/src/main/java/io/legado/app/ui"

# 登记豁免（architecture.md 铁律 1 自带豁免类 + 语义色单源）：
# 键 = 相对仓库根的路径，值 = 允许命中的门禁类别集合（"*" = 全部）
# 说明：取色/语义色的**单源定义点**必须能写具体色值，否则门禁与铁律自相矛盾；
#       任何新增豁免都必须在此登记并在提交信息中说明理由。
EXEMPT: dict[str, set[str]] = {
    # 语义色单源（AD-14 danger / 后续 A3.3 token 门面）：本文件是色值的唯一落地点
    "app/src/main/java/io/legado/app/ui/widget/compose/AppUiTokens.kt": {"HARDCODE_COLOR"},
}

# 词边界：避免命中 `showAlertDialog` / `AppAlertDialog` / `MyAlertDialog(` 等自定义符号
RE_VIEW_LAYOUT = re.compile(r"(?<![\w.])R\.layout\.\w+")
RE_RAW_DIALOG = re.compile(
    r"android\.app\.AlertDialog|androidx\.appcompat\.app\.AlertDialog"
    r"|(?<![\w.])AlertDialog\.Builder|(?<![\w.])AlertDialog\s*\("
    r"|(?<![\w.])alert\s*\{"
)
RE_HARDCODE_COLOR = re.compile(
    r"(?<![\w.])Color\(0x|(?<![\w.])Color\.BLACK\b|(?<![\w.])Color\.WHITE\b|R\.color\.md_"
)

# SnapshotStateList 变量名收集（同文件内有效）
RE_SSL_DECL = re.compile(
    r"(?:val|var)\s+(\w+)\s*:\s*(?:androidx\.compose\.runtime\.snapshots\.)?SnapshotStateList"
)
RE_SSL_PARAM = re.compile(
    r"(\w+)\s*:\s*(?:androidx\.compose\.runtime\.snapshots\.)?SnapshotStateList"
)
RE_SSL_ASSIGN = re.compile(
    r"(?:val|var)\s+(\w+)\s*=[^\n;]*mutableStateListOf\s*<"
)


def _ssl_names(text: str) -> set[str]:
    """收集文件内被判定为 SnapshotStateList 的标识符名。"""
    names: set[str] = set()
    for rx in (RE_SSL_DECL, RE_SSL_PARAM, RE_SSL_ASSIGN):
        names.update(m.group(1) for m in rx.finditer(text))
    names.discard("it")
    return names


def _ssl_violations(lines: list[str]) -> list[tuple[int, str]]:
    """返回 (行号, 行内容) —— 命中 SnapshotStateList 下标写 / .set() 写。"""
    text = "\n".join(lines)
    names = _ssl_names(text)
    if not names:
        return []
    hits: list[tuple[int, str]] = []
    for name in names:
        rx_set = re.compile(rf"(?<![\w.]){re.escape(name)}\.set\s*\(")
        rx_idx = re.compile(rf"(?<![\w.]){re.escape(name)}\s*\[[^\]]*\]\s*=")
        for idx, line in enumerate(lines, 1):
            if line.lstrip().startswith(("*", "//")):
                continue
            if rx_set.search(line) or rx_idx.search(line):
                hits.append((idx, line))
    return hits


def _line_hits(lines: list[str]) -> list[tuple[int, str, str]]:
    """返回 (行号, 门禁名, 行内容)。"""
    out: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("*", "//")):
            continue
        if RE_VIEW_LAYOUT.search(line):
            out.append((idx, "NEW_VIEW_LAYOUT", line))
        if RE_RAW_DIALOG.search(line):
            out.append((idx, "RAW_DIALOG", line))
        if RE_HARDCODE_COLOR.search(line):
            out.append((idx, "HARDCODE_COLOR", line))
    return out


def _is_exempt(rel: str, category: str) -> bool:
    """该文件该类门禁是否已登记豁免。"""
    cats = EXEMPT.get(rel)
    return bool(cats) and ("*" in cats or category in cats)


def scan_all() -> list[str]:
    findings: list[str] = []
    base = ROOT / SCAN_DIR
    for kt in sorted(base.rglob("*.kt")):
        rel = kt.relative_to(ROOT).as_posix()
        try:
            lines = kt.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, name, line in _line_hits(lines):
            if _is_exempt(rel, name):
                continue
            findings.append(f"{rel}:{idx}: {name} | {line.strip()[:110]}")
        if not _is_exempt(rel, "SNAPSHOT_WRITE"):
            for idx, line in _ssl_violations(lines):
                findings.append(f"{rel}:{idx}: SNAPSHOT_WRITE | {line.strip()[:110]}")
    return findings


def scan_diff() -> list[str]:
    """只检查 git diff（工作区 vs HEAD）中 ui/ 目录的新增行。"""
    out = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", "--", SCAN_DIR],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="ignore",
    ).stdout
    added: dict[str, list[tuple[int, str]]] = {}
    cur_file = ""
    cur_line = 0
    for raw in out.splitlines():
        if raw.startswith("+++ b/"):
            cur_file = raw[6:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            cur_line = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            added.setdefault(cur_file, []).append((cur_line, raw[1:]))
            cur_line += 1

    findings: list[str] = []
    for rel, items in added.items():
        lines = [t for _, t in items]
        ln_of = {idx: ln for idx, (ln, _) in enumerate(items, 1)}
        for i, name, line in _line_hits(lines):
            if _is_exempt(rel, name):
                continue
            findings.append(f"{rel}:{ln_of[i - 1]}: {name} | {line.strip()[:110]}")
        if not _is_exempt(rel, "SNAPSHOT_WRITE"):
            for i, line in _ssl_violations(lines):
                findings.append(f"{rel}:{ln_of[i - 1]}: SNAPSHOT_WRITE | {line.strip()[:110]}")
    return findings


SELFTEST_SAMPLES = [
    ("setContentView(R.layout.activity_x)", True),
    ("AlertDialog.Builder(this).show()", True),
    ("androidx.appcompat.app.AlertDialog.Builder(this)", True),
    ("android.app.AlertDialog.Builder(requireContext())", True),
    ('alert { title = "x" }', True),
    ("val c = Color(0xFF123456)", True),
    ("val c2 = Color.WHITE", True),
    ("val c3 = Color.BLACK", True),
    ("val t = R.color.md_red_500", True),
    # 声明行本身不是违例，仅用于让门禁识别出 SnapshotStateList 变量名
    ("val rows = remember { mutableStateListOf<Int>() }", False),
    ("rows[0] = 1", True),
    ("rows.set(1, 2)", True),
]


def selftest() -> int:
    """内置违规样例自检：应命中的全部命中、不应命中的零命中（A5.1 验收项）。"""
    lines = [code for code, _ in SELFTEST_SAMPLES]
    expect = [want for _, want in SELFTEST_SAMPLES]
    line_hits = _line_hits(lines)
    ssl_hits = _ssl_violations(lines)
    caught = {idx for idx, _, _ in line_hits} | {idx for idx, _ in ssl_hits}
    total = sum(1 for w in expect if w)
    print(f"[UI-GATE selftest] 样例 {len(lines)} 条（应命中 {total} 条），命中 {len(caught)} 条")
    for idx, name, line in sorted(line_hits):
        print(f"  ✓ {idx}: {name} | {line.strip()[:90]}")
    for idx, line in sorted(ssl_hits):
        print(f"  ✓ {idx}: SNAPSHOT_WRITE | {line.strip()[:90]}")
    missed = [i for i, want in enumerate(expect, 1) if want and i not in caught]
    false_pos = [i for i, want in enumerate(expect, 1) if not want and i in caught]
    if missed or false_pos:
        for i in missed:
            print(f"  ✗ 漏报 {i}: {lines[i - 1]}")
        for i in false_pos:
            print(f"  ✗ 误报 {i}: {lines[i - 1]}")
        print(f"[FAIL] 漏报 {len(missed)} / 误报 {len(false_pos)}")
        return 1
    print("[PASS] 违规样例全部被拦下，无漏报无误报")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    diff_mode = "--all" not in sys.argv
    findings = scan_diff() if diff_mode else scan_all()
    mode = "git diff 新增行" if diff_mode else "全量存量"
    print(f"[UI-GATE] 代码层门禁（{mode}）：命中 {len(findings)} 处")
    if findings:
        by_cat: dict[str, int] = {}
        for f in findings:
            cat = f.split(": ", 1)[1].split(" | ", 1)[0] if ": " in f else "?"
            by_cat[cat] = by_cat.get(cat, 0) + 1
        print("分类：" + " / ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))
        only = None
        for i, a in enumerate(sys.argv):
            if a == "--category" and i + 1 < len(sys.argv):
                only = sys.argv[i + 1]
        shown = [f for f in findings if only is None or f" {only} " in f]
        for f in shown[:60]:
            print(f"  - {f}")
        if len(shown) > 60:
            print(f"  ... 共 {len(shown)} 处")
        print("处置：")
        print("  1. NEW_VIEW_LAYOUT  → 禁止新增 View 布局页，改 Compose 直载")
        print("  2. RAW_DIALOG       → 走 ComposeDialogFragment + AppDialogFrame/AppDialogStyle")
        print("  3. HARDCODE_COLOR   → 取色唯一基线 palette.settings.* / rememberAppSettingPalette()")
        print("  4. SNAPSHOT_WRITE   → 改 SnapshotListUpdates.replaceAt/replaceByIndex（写回不落地铁律）")
        return 1
    print("[PASS] fail=0，新增代码未触碰门禁项")
    return 0


if __name__ == "__main__":
    sys.exit(main())
