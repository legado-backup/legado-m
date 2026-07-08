"""ai_tests/tests/test_source_test_generator.py — M9 单元测试

覆盖 SourceTestGenerator 的 7 个核心方法：
- _locate_activity：源码定位
- _parse_activity_source：源码解析（R.id/setContentView/startActivity/Compose/viewBinding）
- _parse_manifest：Manifest 解析
- _allocate_tc_id：TC-ID 自动分配
- _infer_module：模块自动推断
- _render_skeleton：模板渲染
- generate：端到端流程

测试原则：
- 不依赖模拟器/真实设备
- 使用 tmp_path 隔离文件系统副作用
- mock source_map.json 避免依赖 M8 输出
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根到 path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_tests.lib.source_test_generator import SourceTestGenerator


# === 辅助：创建临时 Activity 源码 ===

KT_R_ID_CONTENT = """package io.legado.app.ui.test

class TestActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_test)
        val btnSubmit = findViewById<Button>(R.id.btn_submit)
        val etInput = findViewById<EditText>(R.id.et_input)
        btnSubmit.setOnClickListener {
            startActivity(Intent(this, ResultActivity::class.java))
        }
    }
}
"""

KT_COMPOSE_CONTENT = """package io.legado.app.ui.debug

class DebugActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        initLegadoComposeTheme()
        super.onCreate(savedInstanceState)
        setLegadoContent {
            DebugScreen(onBackClick = { finish() })
        }
    }
}
"""

KT_VIEW_BINDING_CONTENT = """package io.legado.app.ui.book

class BookActivity : AppCompatActivity() {
    private lateinit var binding: ActivityBookBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.btnRead.setOnClickListener {
            startActivity(Intent(this, ReadActivity::class.java))
        }
    }
}
"""

KT_MULTI_JUMP_CONTENT = """package io.legado.app.ui.main

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        findViewById<Button>(R.id.btn_a).setOnClickListener {
            startActivity(Intent(this, ActivityA::class.java))
        }
        findViewById<Button>(R.id.btn_b).setOnClickListener {
            startActivity(Intent(this, ActivityB::class.java))
        }
        startActivity<ActivityC>()
    }
}
"""


class TestLocateActivity:
    """_locate_activity 测试"""

    def test_find_existing_activity(self, tmp_path):
        """找到存在的 Activity 文件"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        source_root.mkdir(parents=True)
        (source_root / "ui" / "test").mkdir(parents=True)
        target = source_root / "ui" / "test" / "TestActivity.kt"
        target.write_text(KT_R_ID_CONTENT, encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = source_root
        result = gen._locate_activity("TestActivity")
        assert result is not None
        assert result.name == "TestActivity.kt"

    def test_find_activity_in_subdirectory(self, tmp_path):
        """在深层子目录中查找 Activity"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        source_root.mkdir(parents=True)
        deep_dir = source_root / "ui" / "association" / "debug" / "deep"
        deep_dir.mkdir(parents=True)
        (deep_dir / "DeepActivity.kt").write_text("// empty", encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = source_root
        result = gen._locate_activity("DeepActivity")
        assert result is not None
        assert "deep" in str(result)

    def test_not_found_returns_none(self, tmp_path):
        """未找到 Activity 返回 None"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        source_root.mkdir(parents=True)

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = source_root
        result = gen._locate_activity("NonExistentActivity")
        assert result is None

    def test_find_java_activity(self, tmp_path):
        """查找 .java 文件（兼容旧项目）"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        source_root.mkdir(parents=True)
        (source_root / "LegacyActivity.java").write_text("// legacy", encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = source_root
        result = gen._locate_activity("LegacyActivity")
        assert result is not None
        assert result.suffix == ".java"


class TestParseActivitySource:
    """_parse_activity_source 测试"""

    def test_extract_r_id_and_setcontentview(self, tmp_path):
        """提取 R.id.xxx 和 setContentView(R.layout.xxx)"""
        kt_file = tmp_path / "TestActivity.kt"
        kt_file.write_text(KT_R_ID_CONTENT, encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        result = gen._parse_activity_source(kt_file)

        assert result["layout"] == "activity_test"
        assert "btn_submit" in result["view_ids"]
        assert "et_input" in result["view_ids"]
        assert "ResultActivity" in result["activity_jumps"]

    def test_compose_no_r_id(self, tmp_path):
        """Compose Activity 无 R.id.xxx"""
        kt_file = tmp_path / "DebugActivity.kt"
        kt_file.write_text(KT_COMPOSE_CONTENT, encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        result = gen._parse_activity_source(kt_file)

        assert result["layout"] is None
        assert len(result["view_ids"]) == 0

    def test_view_binding_ids(self, tmp_path):
        """viewBinding 模式提取 binding.xxx"""
        kt_file = tmp_path / "BookActivity.kt"
        kt_file.write_text(KT_VIEW_BINDING_CONTENT, encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        result = gen._parse_activity_source(kt_file)

        assert "btnRead" in result["binding_ids"]
        assert "root" in result["binding_ids"]
        assert "ReadActivity" in result["activity_jumps"]

    def test_multiple_activity_jumps_dedup(self, tmp_path):
        """多个 startActivity 跳转去重"""
        kt_file = tmp_path / "MainActivity.kt"
        kt_file.write_text(KT_MULTI_JUMP_CONTENT, encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        result = gen._parse_activity_source(kt_file)

        assert "ActivityA" in result["activity_jumps"]
        assert "ActivityB" in result["activity_jumps"]
        assert "ActivityC" in result["activity_jumps"]
        # 去重后数量正确
        assert len(result["activity_jumps"]) == 3

    def test_empty_content_returns_empty(self, tmp_path):
        """空内容返回空列表"""
        kt_file = tmp_path / "EmptyActivity.kt"
        kt_file.write_text("// empty file", encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        result = gen._parse_activity_source(kt_file)

        assert result["layout"] is None
        assert len(result["view_ids"]) == 0
        assert len(result["activity_jumps"]) == 0


class TestParseManifest:
    """_parse_manifest 测试"""

    def test_parse_registered_activities(self, tmp_path):
        """正常解析 AndroidManifest.xml"""
        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <application>\n'
            '        <activity android:name=".ui.MainActivity" />\n'
            '        <activity android:name=".ui.book.BookshelfActivity" />\n'
            '        <activity android:name="io.legado.app.ui.debug.DebugToolsActivity" />\n'
            '    </application>\n'
            '</manifest>\n',
            encoding="utf-8",
        )

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.manifest_path = manifest
        result = gen._parse_manifest()

        registered = result["registered_activities"]
        assert "MainActivity" in registered
        assert "BookshelfActivity" in registered
        assert "DebugToolsActivity" in registered

    def test_manifest_not_exists_returns_empty(self, tmp_path):
        """Manifest 不存在返回空列表"""
        gen = SourceTestGenerator(project_root=tmp_path)
        gen.manifest_path = tmp_path / "NonExistent.xml"
        result = gen._parse_manifest()

        assert result["registered_activities"] == []

    def test_manifest_cache_reused(self, tmp_path):
        """_parse_manifest 缓存结果"""
        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest><application>'
            '<activity android:name=".TestActivity" />'
            '</application></manifest>',
            encoding="utf-8",
        )

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.manifest_path = manifest
        # 第一次调用解析
        result1 = gen._parse_manifest()
        # 删除文件模拟后续不可用
        manifest.unlink()
        # 第二次调用应使用缓存
        result2 = gen._parse_manifest()

        assert result1 == result2
        assert "TestActivity" in result2["registered_activities"]


class TestAllocateTcId:
    """_allocate_tc_id 测试"""

    def test_empty_directory_returns_001(self, tmp_path):
        """空目录分配 001"""
        gen = SourceTestGenerator(project_root=tmp_path)
        gen.output_root = tmp_path / "cases"
        tc_id = gen._allocate_tc_id("F-P0-1")
        assert tc_id == "TC-F-P0-1-auto-001"

    def test_module_dir_not_exists_returns_001(self, tmp_path):
        """模块目录不存在时分配 001"""
        gen = SourceTestGenerator(project_root=tmp_path)
        gen.output_root = tmp_path / "cases"
        (gen.output_root / "OtherModule").mkdir(parents=True)
        tc_id = gen._allocate_tc_id("F-P0-1")
        assert tc_id == "TC-F-P0-1-auto-001"

    def test_increment_from_existing(self, tmp_path):
        """已有文件时递增编号"""
        gen = SourceTestGenerator(project_root=tmp_path)
        gen.output_root = tmp_path / "cases"
        module_dir = gen.output_root / "F-P0-1"
        module_dir.mkdir(parents=True)
        # 文件名用小写下划线格式（M3 规则 1）
        (module_dir / "auto_tc_f_p0_1_auto_001.py").write_text("# test", encoding="utf-8")
        (module_dir / "auto_tc_f_p0_1_auto_002.py").write_text("# test", encoding="utf-8")

        tc_id = gen._allocate_tc_id("F-P0-1")
        assert tc_id == "TC-F-P0-1-auto-003"

    def test_skip_non_matching_files(self, tmp_path):
        """跳过不匹配命名规则的文件"""
        gen = SourceTestGenerator(project_root=tmp_path)
        gen.output_root = tmp_path / "cases"
        module_dir = gen.output_root / "F-P0-1"
        module_dir.mkdir(parents=True)
        # 文件名用小写下划线格式（M3 规则 1）
        (module_dir / "auto_tc_f_p0_1_auto_005.py").write_text("# test", encoding="utf-8")
        (module_dir / "other_file.py").write_text("# test", encoding="utf-8")
        (module_dir / "auto_invalid.py").write_text("# test", encoding="utf-8")

        tc_id = gen._allocate_tc_id("F-P0-1")
        # 005 + 1 = 006
        assert tc_id == "TC-F-P0-1-auto-006"


class TestInferModule:
    """_infer_module 测试"""

    def test_infer_from_source_map(self, tmp_path):
        """从 source_map.json 推断模块"""
        source_map = {
            "activities": {
                "DebugToolsActivity": {
                    "tc_ids": ["TC-F-P0-1-01", "TC-F-P0-1-02"],
                    "callers": [],
                    "ui_components": [],
                }
            }
        }
        source_map_path = tmp_path / "ai_tests" / "lib" / "source_map.json"
        source_map_path.parent.mkdir(parents=True)
        source_map_path.write_text(json.dumps(source_map), encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        module = gen._infer_module("DebugToolsActivity")
        assert module == "F-P0-1"

    def test_infer_no_matching_activity(self, tmp_path):
        """Activity 不在 source_map 中返回 auto"""
        source_map = {"activities": {"OtherActivity": {"tc_ids": ["TC-F-P0-1-01"]}}}
        source_map_path = tmp_path / "ai_tests" / "lib" / "source_map.json"
        source_map_path.parent.mkdir(parents=True)
        source_map_path.write_text(json.dumps(source_map), encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        module = gen._infer_module("UnknownActivity")
        assert module == "auto"

    def test_infer_no_source_map_returns_auto(self, tmp_path):
        """source_map.json 不存在返回 auto"""
        gen = SourceTestGenerator(project_root=tmp_path)
        module = gen._infer_module("DebugToolsActivity")
        assert module == "auto"

    def test_infer_no_tc_ids_returns_auto(self, tmp_path):
        """Activity 在 source_map 中但无 TC-ID 返回 auto"""
        source_map = {
            "activities": {
                "UnknownActivity": {"tc_ids": [], "callers": [], "ui_components": []}
            }
        }
        source_map_path = tmp_path / "ai_tests" / "lib" / "source_map.json"
        source_map_path.parent.mkdir(parents=True)
        source_map_path.write_text(json.dumps(source_map), encoding="utf-8")

        gen = SourceTestGenerator(project_root=tmp_path)
        module = gen._infer_module("UnknownActivity")
        assert module == "auto"


class TestRenderSkeleton:
    """_render_skeleton 测试"""

    def test_render_contains_key_fields(self, tmp_path):
        """渲染输出包含关键字段"""
        # 准备 Activity 源码
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app" / "ui" / "test"
        source_root.mkdir(parents=True)
        activity_path = source_root / "TestActivity.kt"
        activity_path.write_text(KT_R_ID_CONTENT, encoding="utf-8")

        # 准备 Manifest
        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest><application>'
            '<activity android:name=".ui.test.TestActivity" />'
            '</application></manifest>',
            encoding="utf-8",
        )

        # 准备模板（使用真实模板）
        templates_dir = PROJECT_ROOT / "ai_tests" / "templates"

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        gen.manifest_path = manifest
        gen.template_path = templates_dir / "auto_test_template.j2"

        source_info = gen._parse_activity_source(activity_path)
        manifest_info = gen._parse_manifest()

        rendered = gen._render_skeleton(
            activity_name="TestActivity",
            activity_path=activity_path,
            source_info=source_info,
            manifest_info=manifest_info,
            module="F-P0-1",
            tc_id="TC-F-P0-1-auto-001",
        )

        # 验证关键字段
        assert "TestActivity" in rendered
        assert "TC-F-P0-1-auto-001" in rendered
        assert "F-P0-1" in rendered
        assert "BTN_SUBMIT_ID" in rendered  # R.id 常量（大写）
        assert "ResultActivity" in rendered  # 跳转目标
        assert "io.legado.app.ui.test.TestActivity" in rendered  # 完整类名
        assert "@tc_id" in rendered  # M3 规则 2 兜底注释

    def test_render_compose_activity(self, tmp_path):
        """Compose Activity 渲染（无 R.id）"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app" / "ui" / "debug"
        source_root.mkdir(parents=True)
        activity_path = source_root / "DebugActivity.kt"
        activity_path.write_text(KT_COMPOSE_CONTENT, encoding="utf-8")

        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest><application>'
            '<activity android:name=".ui.debug.DebugActivity" />'
            '</application></manifest>',
            encoding="utf-8",
        )

        templates_dir = PROJECT_ROOT / "ai_tests" / "templates"

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        gen.manifest_path = manifest
        gen.template_path = templates_dir / "auto_test_template.j2"

        source_info = gen._parse_activity_source(activity_path)
        manifest_info = gen._parse_manifest()

        rendered = gen._render_skeleton(
            activity_name="DebugActivity",
            activity_path=activity_path,
            source_info=source_info,
            manifest_info=manifest_info,
            module="auto",
            tc_id="TC-auto-auto-001",
        )

        # Compose 场景的简化说明
        assert "未提取到 R.id.xxx" in rendered
        assert "Compose" in rendered


class TestGenerate:
    """generate 端到端测试"""

    def test_generate_full_flow(self, tmp_path):
        """完整生成流程"""
        # 准备源码
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app" / "ui" / "test"
        source_root.mkdir(parents=True)
        activity_path = source_root / "TestActivity.kt"
        activity_path.write_text(KT_R_ID_CONTENT, encoding="utf-8")

        # 准备 Manifest
        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest><application>'
            '<activity android:name=".ui.test.TestActivity" />'
            '</application></manifest>',
            encoding="utf-8",
        )

        # 准备 source_map.json（用于模块推断）
        source_map = {
            "activities": {
                "TestActivity": {
                    "tc_ids": ["TC-F-P0-1-01"],
                    "callers": [],
                    "ui_components": [],
                }
            }
        }
        source_map_path = tmp_path / "ai_tests" / "lib" / "source_map.json"
        source_map_path.parent.mkdir(parents=True)
        source_map_path.write_text(json.dumps(source_map), encoding="utf-8")

        # 准备输出目录
        cases_dir = tmp_path / "ai_tests" / "cases"

        # 准备模板
        templates_dir = PROJECT_ROOT / "ai_tests" / "templates"

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        gen.manifest_path = manifest
        gen.output_root = cases_dir
        gen.template_path = templates_dir / "auto_test_template.j2"

        # 执行生成
        output = gen.generate("TestActivity", module="auto")

        # 验证输出
        output_path = Path(output)
        assert output_path.exists()
        assert output_path.name == "auto_tc_f_p0_1_auto_001.py"
        assert output_path.parent.name == "F-P0-1"  # 模块推断正确

        # 验证文件内容
        content = output_path.read_text(encoding="utf-8")
        assert "TestActivity" in content
        assert "TC-F-P0-1-auto-001" in content
        assert "@tc_id" in content

    def test_generate_activity_not_found(self, tmp_path):
        """Activity 未找到抛出 FileNotFoundError"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        source_root.mkdir(parents=True)

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = source_root

        try:
            gen.generate("NonExistentActivity", module="auto")
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError as e:
            assert "NonExistentActivity" in str(e)

    def test_generate_explicit_module(self, tmp_path):
        """显式指定 module 跳过推断"""
        source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app" / "ui" / "test"
        source_root.mkdir(parents=True)
        activity_path = source_root / "TestActivity.kt"
        activity_path.write_text(KT_R_ID_CONTENT, encoding="utf-8")

        manifest = tmp_path / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest><application>'
            '<activity android:name=".ui.test.TestActivity" />'
            '</application></manifest>',
            encoding="utf-8",
        )

        cases_dir = tmp_path / "ai_tests" / "cases"
        templates_dir = PROJECT_ROOT / "ai_tests" / "templates"

        gen = SourceTestGenerator(project_root=tmp_path)
        gen.source_root = tmp_path / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
        gen.manifest_path = manifest
        gen.output_root = cases_dir
        gen.template_path = templates_dir / "auto_test_template.j2"

        output = gen.generate("TestActivity", module="F-P0-2")

        output_path = Path(output)
        assert output_path.parent.name == "F-P0-2"
        # 文件名是小写下划线格式（M3 规则 1）：auto_tc_f_p0_2_auto_001.py
        assert "auto_tc_f_p0_2_auto_001" in output_path.name


class TestM3Integration:
    """M3 双轨调度集成测试（验证 13.9 要求：可被 M3 识别）"""

    def test_m3_find_python_track_filename_match(self, tmp_path):
        """M3 _find_python_track 通过文件名规则识别 auto_*.py"""
        # 准备生成的文件
        cases_dir = tmp_path / "ai_tests" / "cases"
        module_dir = cases_dir / "F-P0-1"
        module_dir.mkdir(parents=True)
        target_file = module_dir / "auto_tc_f_p0_1_auto_001.py"
        target_file.write_text(
            '"""test"""\n# @tc_id: TC-F-P0-1-auto-001\n',
            encoding="utf-8",
        )

        # Mock config 中的 AI_TESTS_CASES_DIR
        with patch("ai_tests.lib.case_parser.AI_TESTS_CASES_DIR", cases_dir):
            from ai_tests.lib.case_parser import CaseParser
            parser = CaseParser()
            result = parser._find_python_track("TC-F-P0-1-auto-001", "F-P0-1")

        assert result is not None
        assert "auto_tc_f_p0_1_auto_001.py" in result

    def test_m3_find_python_track_tc_id_comment(self, tmp_path):
        """M3 _find_python_track 通过 @tc_id 注释规则识别"""
        cases_dir = tmp_path / "ai_tests" / "cases"
        module_dir = cases_dir / "F-P0-1"
        module_dir.mkdir(parents=True)
        # 文件名不匹配规则 1，但文件头有 @tc_id 注释
        target_file = module_dir / "auto_custom_name.py"
        target_file.write_text(
            '"""test"""\n# @tc_id: TC-F-P0-1-CUSTOM\n# @module: F-P0-1\n',
            encoding="utf-8",
        )

        with patch("ai_tests.lib.case_parser.AI_TESTS_CASES_DIR", cases_dir):
            from ai_tests.lib.case_parser import CaseParser
            parser = CaseParser()
            result = parser._find_python_track("TC-F-P0-1-CUSTOM", "F-P0-1")

        assert result is not None
        assert "auto_custom_name.py" in result


if __name__ == "__main__":
    # 直接运行模式：用 unittest 风格手动执行（不依赖 pytest）
    import traceback

    test_classes = [
        TestLocateActivity,
        TestParseActivitySource,
        TestParseManifest,
        TestAllocateTcId,
        TestInferModule,
        TestRenderSkeleton,
        TestGenerate,
        TestM3Integration,
    ]

    total = 0
    passed = 0
    failed = 0

    for test_class in test_classes:
        for method_name in dir(test_class):
            if not method_name.startswith("test_"):
                continue
            total += 1
            instance = test_class()
            # 创建 tmp_path
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                try:
                    # 注入 tmp_path 参数（test 方法签名需要 tmp_path）
                    method = getattr(instance, method_name)
                    # 检查方法签名是否接受 tmp_path
                    import inspect
                    sig = inspect.signature(method)
                    if "tmp_path" in sig.parameters:
                        method(tmp_path=tmp_path)
                    else:
                        method()
                    passed += 1
                    print(f"ok {test_class.__name__}.{method_name}")
                except Exception as e:
                    failed += 1
                    print(f"FAIL {test_class.__name__}.{method_name}: {e}")
                    traceback.print_exc()

    print(f"\n{'=' * 70}")
    print(f"M9 SourceTestGenerator 测试结果: {passed}/{total} PASS, {failed} FAIL")
    print(f"{'=' * 70}")
    sys.exit(0 if failed == 0 else 1)
