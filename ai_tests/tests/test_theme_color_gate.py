"""ai_tests/tests/test_theme_color_gate.py — Phase4 取色同源静态断言单测

覆盖：
- BAN_PATTERN 正向匹配（5 种 M3 派生色 + 常见调用形态）
- BAN_PATTERN 负向不误报（同源调色板/primary/outline 等合法取色）
- scan_diff：git diff 新增行解析（mock subprocess）
- scan_all：目录扫描（tmp_path + monkeypatch ROOT/SCAN_DIR）

运行：
    ai_tests\\venv\\Scripts\\python.exe -m pytest ai_tests/tests/test_theme_color_gate.py -q
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_tests.scripts.theme_color_gate import BAN_PATTERN, scan_all, scan_diff


# === BAN_PATTERN 正向匹配 ===

def test_pattern_matches_all_banned_colors():
    """1. 五种禁用 M3 派生色全部命中"""
    for color in ("surface", "surfaceVariant", "onSurface", "onSurfaceVariant", "background"):
        line = f"val c = MaterialTheme.colorScheme.{color}"
        assert BAN_PATTERN.search(line), f"colorScheme.{color} 应命中禁用模式"


def test_pattern_matches_common_usages():
    """2. 常见调用形态命中：赋值/传参/链式"""
    lines = [
        "color = MaterialTheme.colorScheme.surface",
        "Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant))",
        ".background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))",
    ]
    for line in lines:
        assert BAN_PATTERN.search(line), f"应命中: {line}"


# === BAN_PATTERN 负向不误报 ===

def test_pattern_ignores_legal_palette_sources():
    """3. 同源调色板与合法 M3 色不误报"""
    legal_lines = [
        "val palette = rememberAppSettingPalette()",
        "val style = rememberAppDialogStyle()",
        "color = palette.textPrimary",
        "color = MaterialTheme.colorScheme.primary",
        "color = MaterialTheme.colorScheme.outline",
        "color = MaterialTheme.colorScheme.error",
        "// MaterialTheme.colorScheme.surface 注释也不该误报? —— 会命中, 属预期(注释极少写)",
    ]
    for line in legal_lines[:-1]:
        assert not BAN_PATTERN.search(line), f"不应命中: {line}"


def test_pattern_word_boundary():
    """4. 词边界：surfaceContainer 等派生变体不在禁用名单则不命中 surface"""
    assert not BAN_PATTERN.search("MaterialTheme.colorScheme.surfaceContainer")
    assert not BAN_PATTERN.search("MaterialTheme.colorScheme.onSurfaceVar")  # 部分名不命中


# === scan_diff：diff 解析 ===

def _fake_diff_output() -> str:
    return """diff --git a/app/src/main/java/io/legado/app/ui/foo/Foo.kt b/app/src/main/java/io/legado/app/ui/foo/Foo.kt
index 111..222 100644
--- a/app/src/main/java/io/legado/app/ui/foo/Foo.kt
+++ b/app/src/main/java/io/legado/app/ui/foo/Foo.kt
@@ -10,0 +11,2 @@
+val ok = rememberAppSettingPalette()
+val bad = MaterialTheme.colorScheme.surface
@@ -20,1 +23,1 @@
-old val removed = MaterialTheme.colorScheme.onSurface
+val fixed = palette.textPrimary
"""


def test_scan_diff_parses_added_lines_only():
    """5. 只报新增行命中，删除行/合法行不报；行号取 + 起始行累加"""
    with patch("ai_tests.scripts.theme_color_gate.subprocess.run") as mock_run:
        mock_run.return_value.stdout = _fake_diff_output()
        findings = scan_diff()
    assert len(findings) == 1, f"应只命中 1 处新增行，实际: {findings}"
    assert "Foo.kt:12" in findings[0], f"行号应为 12（11+第2行），实际: {findings[0]}"
    assert "colorScheme.surface" in findings[0]


def test_scan_diff_empty():
    """6. 空 diff → 零命中"""
    with patch("ai_tests.scripts.theme_color_gate.subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        assert scan_diff() == []


# === scan_all：目录扫描 ===

def test_scan_all_scans_kt_files():
    """7. 全量扫描：tmp 目录构造 kt 文件，命中禁用色并输出 相对路径:行号"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ui_dir = root / "app/src/main/java/io/legado/app/ui/demo"
        ui_dir.mkdir(parents=True)
        kt = ui_dir / "Demo.kt"
        kt.write_text(
            "val a = 1\n"
            "val bad = MaterialTheme.colorScheme.background\n"
            "val good = rememberAppSettingPalette()\n",
            encoding="utf-8",
        )
        # 目录外文件不扫描
        out_dir = root / "other"
        out_dir.mkdir()
        (out_dir / "X.kt").write_text(
            "val bad = MaterialTheme.colorScheme.surface\n", encoding="utf-8"
        )

        import ai_tests.scripts.theme_color_gate as gate

        old_root, old_dir = gate.ROOT, gate.SCAN_DIR
        gate.ROOT = root
        gate.SCAN_DIR = "app/src/main/java/io/legado/app/ui"
        try:
            findings = scan_all()
        finally:
            gate.ROOT, gate.SCAN_DIR = old_root, old_dir

    assert len(findings) == 1, f"应只命中目录内 1 处，实际: {findings}"
    assert findings[0].startswith("app/src/main/java/io/legado/app/ui/demo/Demo.kt:2"), findings[0]


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
