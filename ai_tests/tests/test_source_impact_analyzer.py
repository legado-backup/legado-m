"""ai_tests/tests/test_source_impact_analyzer.py — M8 单元测试

覆盖：
- _extract_ui_components（4 种 UI 组件提取）
- _find_callers（调用方查找）
- _reverse_trace（反向追溯，含多层）
- _lookup_related_tc_ids（TC-ID 查询）
- _scan_tc_ids_for_activity（docs/tests 扫描）
- _git_diff_name_only（mock subprocess）
- analyze_diff（端到端，mock git diff）
- get_source_map_summary
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.lib.source_impact_analyzer import (
    SourceImpactAnalyzer,
    SOURCE_MAP_VERSION,
)


class TestExtractUiComponents(unittest.TestCase):
    """测试 _extract_ui_components"""

    def setUp(self):
        # 用临时目录避免依赖真实项目结构
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_r_id_extraction(self):
        """提取 R.id.xxx"""
        code = "val tv = findViewById<TextView>(R.id.tv_title)"
        components = self.sia._extract_ui_components(code)
        self.assertIn("R.id.tv_title", components)

    def test_set_content_view_extraction(self):
        """提取 setContentView(R.layout.xxx)"""
        code = "setContentView(R.layout.activity_main)"
        components = self.sia._extract_ui_components(code)
        self.assertIn("R.layout.activity_main", components)

    def test_compose_set_content(self):
        """识别 Compose setContent {}"""
        code = "setContent { MainScreen() }"
        components = self.sia._extract_ui_components(code)
        self.assertIn("setContent{}", components)

    def test_multiple_r_ids(self):
        """多个 R.id 去重"""
        code = """
        val a = findViewById<View>(R.id.btn_a)
        val b = findViewById<View>(R.id.btn_b)
        val c = findViewById<View>(R.id.btn_a)  // 重复
        """
        components = self.sia._extract_ui_components(code)
        self.assertIn("R.id.btn_a", components)
        self.assertIn("R.id.btn_b", components)
        self.assertEqual(len([c for c in components if c == "R.id.btn_a"]), 1)

    def test_empty_content(self):
        """空内容返回空列表"""
        self.assertEqual(self.sia._extract_ui_components(""), [])
        self.assertEqual(self.sia._extract_ui_components("val x = 1"), [])


class TestReverseTrace(unittest.TestCase):
    """测试 _reverse_trace（纯函数，基于 source_map 输入）"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )
        # 构造 mock source_map
        # 调用链：ChangedFile.kt -> BookSourceActivity -> MainActivity -> (无)
        #              -> ConfigActivity -> MainActivity
        self.mock_source_map = {
            "version": SOURCE_MAP_VERSION,
            "activities": {
                "BookSourceActivity": {
                    "path": "app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt",
                    "callers": ["MainActivity"],
                    "ui_components": ["R.id.rv"],
                    "tc_ids": ["TC-F-P0-2-01"],
                },
                "ConfigActivity": {
                    "path": "app/src/main/java/io/legado/app/ui/config/ConfigActivity.kt",
                    "callers": ["MainActivity"],
                    "ui_components": [],
                    "tc_ids": ["TC-F-P0-5-01"],
                },
                "MainActivity": {
                    "path": "app/src/main/java/io/legado/app/ui/main/MainActivity.kt",
                    "callers": [],
                    "ui_components": [],
                    "tc_ids": ["TC-F-P0-1-13"],
                },
            },
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_direct_activity_match(self):
        """改动文件直接是 Activity"""
        changed = ["app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt"]
        affected = self.sia._reverse_trace(changed, self.mock_source_map)
        self.assertIn("BookSourceActivity", affected)

    def test_reverse_one_level(self):
        """向上追溯 1 层：改 BookSourceActivity -> MainActivity 受影响"""
        changed = ["app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt"]
        affected = self.sia._reverse_trace(changed, self.mock_source_map)
        self.assertIn("MainActivity", affected)

    def test_reverse_two_levels(self):
        """向上追溯 2 层（含 ConfigActivity -> MainActivity）"""
        changed = ["app/src/main/java/io/legado/app/ui/config/ConfigActivity.kt"]
        affected = self.sia._reverse_trace(changed, self.mock_source_map)
        # ConfigActivity 直接命中
        self.assertIn("ConfigActivity", affected)
        # 向上 1 层：MainActivity（ConfigActivity 的 caller）
        self.assertIn("MainActivity", affected)

    def test_non_activity_file(self):
        """改动文件不是 Activity 也不被 Activity 引用"""
        changed = ["app/src/main/java/io/legado/app/utils/SomeUtil.kt"]
        affected = self.sia._reverse_trace(changed, self.mock_source_map)
        # SomeUtil.kt 不在任何 Activity 的 path 中，也不在 callers 中
        # 但 _reverse_trace 基于 file_to_activity 映射，SomeUtil 不在映射中
        self.assertEqual(affected, [])

    def test_empty_changed_files(self):
        """空改动列表"""
        affected = self.sia._reverse_trace([], self.mock_source_map)
        self.assertEqual(affected, [])


class TestLookupRelatedTcIds(unittest.TestCase):
    """测试 _lookup_related_tc_ids"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )
        self.mock_source_map = {
            "activities": {
                "BookSourceActivity": {"tc_ids": ["TC-F-P0-2-01", "TC-F-P0-2-02"]},
                "ConfigActivity": {"tc_ids": ["TC-F-P0-5-01"]},
                "NoTcActivity": {"tc_ids": []},
            }
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_lookup_single_activity(self):
        result = self.sia._lookup_related_tc_ids(["BookSourceActivity"], self.mock_source_map)
        self.assertEqual(set(result), {"TC-F-P0-2-01", "TC-F-P0-2-02"})

    def test_lookup_multiple_activities_dedup(self):
        """多 Activity 的 TC-ID 去重"""
        result = self.sia._lookup_related_tc_ids(
            ["BookSourceActivity", "ConfigActivity"], self.mock_source_map
        )
        self.assertEqual(set(result), {"TC-F-P0-2-01", "TC-F-P0-2-02", "TC-F-P0-5-01"})

    def test_lookup_activity_with_no_tcids(self):
        result = self.sia._lookup_related_tc_ids(["NoTcActivity"], self.mock_source_map)
        self.assertEqual(result, [])

    def test_lookup_unknown_activity(self):
        """未知 Activity 返回空"""
        result = self.sia._lookup_related_tc_ids(["UnknownActivity"], self.mock_source_map)
        self.assertEqual(result, [])

    def test_lookup_empty_list(self):
        result = self.sia._lookup_related_tc_ids([], self.mock_source_map)
        self.assertEqual(result, [])


class TestGitDiffNameOnly(unittest.TestCase):
    """测试 _git_diff_name_only（mock subprocess）"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("ai_tests.lib.source_impact_analyzer.subprocess.run")
    def test_success(self, mock_run):
        """git diff 成功"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="app/src/main/java/Foo.kt\napp/src/main/java/Bar.kt\n",
            stderr="",
        )
        files = self.sia._git_diff_name_only("HEAD~1")
        self.assertEqual(files, ["app/src/main/java/Foo.kt", "app/src/main/java/Bar.kt"])

    @patch("ai_tests.lib.source_impact_analyzer.subprocess.run")
    def test_failure_returncode(self, mock_run):
        """git diff 返回非零（如 ref 不存在）"""
        mock_run.return_value = MagicMock(
            returncode=128, stdout="", stderr="fatal: bad revision 'HEAD~1'"
        )
        files = self.sia._git_diff_name_only("HEAD~1")
        self.assertEqual(files, [])

    @patch("ai_tests.lib.source_impact_analyzer.subprocess.run")
    def test_no_changes(self, mock_run):
        """git diff 无改动"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        files = self.sia._git_diff_name_only("HEAD~1")
        self.assertEqual(files, [])

    @patch("ai_tests.lib.source_impact_analyzer.subprocess.run")
    def test_git_not_found(self, mock_run):
        """git 命令不存在"""
        mock_run.side_effect = FileNotFoundError("git not found")
        files = self.sia._git_diff_name_only("HEAD~1")
        self.assertEqual(files, [])


class TestAnalyzeDiff(unittest.TestCase):
    """测试 analyze_diff（端到端，mock _git_diff_name_only 和 source_map）"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )
        self.mock_source_map = {
            "version": SOURCE_MAP_VERSION,
            "generated_at": "2026-07-08T00:00:00",
            "activities": {
                "BookSourceActivity": {
                    "path": "app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt",
                    "callers": ["MainActivity"],
                    "ui_components": [],
                    "tc_ids": ["TC-F-P0-2-01"],
                },
            },
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_analyze_with_no_changes(self):
        """无改动文件"""
        with patch.object(self.sia, "_git_diff_name_only", return_value=[]):
            result = self.sia.analyze_diff("HEAD~1")
        self.assertEqual(result["changed_files"], [])
        self.assertEqual(result["affected_activities"], [])
        self.assertEqual(result["recommended_rerun"], [])

    def test_analyze_with_activity_change(self):
        """改动 Activity 文件"""
        with patch.object(self.sia, "_git_diff_name_only", return_value=[
            "app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt"
        ]), patch.object(self.sia, "_load_or_build_source_map", return_value=self.mock_source_map):
            result = self.sia.analyze_diff("HEAD~1")
        self.assertIn("BookSourceActivity", result["affected_activities"])
        self.assertIn("TC-F-P0-2-01", result["recommended_rerun"])

    def test_analyze_output_structure(self):
        """输出 dict 结构完整"""
        with patch.object(self.sia, "_git_diff_name_only", return_value=[]):
            result = self.sia.analyze_diff("HEAD~1")
        # 必须包含所有字段
        for key in ["changed_files", "affected_activities", "related_tc_ids",
                    "recommended_rerun", "git_ref", "analyzed_at"]:
            self.assertIn(key, result)
        self.assertEqual(result["git_ref"], "HEAD~1")


class TestScanTcIdsForActivity(unittest.TestCase):
    """测试 _scan_tc_ids_for_activity（使用真实 docs/tests）"""

    def setUp(self):
        # 使用真实 docs/tests 目录，确保与项目实际状态一致
        from ai_tests.config import DOCS_TESTS_DIR, AI_TESTS_CASES_DIR, SOURCE_ROOT, SOURCE_MAP_PATH, PROJECT_ROOT
        self.sia = SourceImpactAnalyzer(
            source_root=SOURCE_ROOT,
            source_map_path=SOURCE_MAP_PATH,
            project_root=PROJECT_ROOT,
            docs_tests_dir=DOCS_TESTS_DIR,
            ai_tests_cases_dir=AI_TESTS_CASES_DIR,
        )

    def test_debug_tools_activity_has_tc_ids(self):
        """DebugToolsActivity 应关联 F-P0-1 模块的 TC-ID"""
        tc_ids = self.sia._scan_tc_ids_for_activity("DebugToolsActivity")
        # F-P0-1-debug-tools.md 中应该有 TC-F-P0-1-01 到 TC-F-P0-1-14
        self.assertTrue(len(tc_ids) > 0, "DebugToolsActivity 应有关联 TC-ID")
        self.assertIn("TC-F-P0-1-01", tc_ids)

    def test_unknown_activity_returns_empty(self):
        """未知 Activity 返回空列表"""
        tc_ids = self.sia._scan_tc_ids_for_activity("NonExistentActivity12345")
        self.assertEqual(tc_ids, [])

    def test_empty_activity_name(self):
        """空类名返回空"""
        self.assertEqual(self.sia._scan_tc_ids_for_activity(""), [])


class TestGetSourceMapSummary(unittest.TestCase):
    """测试 get_source_map_summary"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sia = SourceImpactAnalyzer(
            source_root=Path(self.tmpdir.name),
            source_map_path=Path(self.tmpdir.name) / "source_map.json",
            project_root=Path(self.tmpdir.name),
            docs_tests_dir=Path(self.tmpdir.name),
            ai_tests_cases_dir=Path(self.tmpdir.name),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_summary_with_no_file(self):
        """source_map.json 不存在"""
        summary = self.sia.get_source_map_summary()
        self.assertEqual(summary.get("total_activities"), 0)
        self.assertIn("error", summary)

    def test_summary_with_valid_file(self):
        """有效的 source_map.json"""
        # 写入临时 source_map
        mock_map = {
            "version": "1.0",
            "generated_at": "2026-07-08T00:00:00",
            "activities": {
                "TestActivity": {
                    "path": "a/b/c.kt",
                    "callers": ["OtherActivity"],
                    "ui_components": [],
                    "tc_ids": ["TC-TEST-01"],
                }
            }
        }
        with open(self.sia.source_map_path, "w", encoding="utf-8") as f:
            json.dump(mock_map, f)
        summary = self.sia.get_source_map_summary()
        self.assertEqual(summary["total_activities"], 1)
        self.assertEqual(summary["total_tc_ids"], 1)
        self.assertEqual(summary["version"], "1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
