"""ai_tests/lib/source_test_generator.py — M9 源码→测试生成器（V3 新增）⭐

职责：
- 基于 Activity 源码静态分析，生成 Python 测试骨架（B 轨）
- 提取 R.id.xxx / setContentView / startActivity 等元素
- 渲染 Jinja2 模板，输出到 ai_tests/cases/{module}/auto_{tc_id}.py
- TC-ID 自动分配：基于 module 前缀 + 现有最大编号 +1

输出示例：
    ai_tests/cases/F-P0-1/auto_TC-F-P0-1-auto-001.py

设计文档：docs/specs/e2e-automated-testing/design.md 1.3.9 节
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ai_tests.config import (
    PROJECT_ROOT, SOURCE_ROOT, ANDROID_MANIFEST, AI_TESTS_CASES_DIR, PACKAGE,
)

logger = logging.getLogger(__name__)

# 模板路径（config.py 未定义，此处复用 PROJECT_ROOT 拼接，不修改固化层）
TEMPLATES_DIR = PROJECT_ROOT / "ai_tests" / "templates"
AUTO_TEST_TEMPLATE = TEMPLATES_DIR / "auto_test_template.j2"


class SourceTestGenerator:
    """M9 源码→测试生成器

    基于 Activity 源码生成 Python 测试骨架（B 轨），供 M3 双轨调度识别。
    """

    def __init__(self, project_root: Optional[Path] = None):
        """初始化生成器

        Args:
            project_root: 项目根目录（默认 PROJECT_ROOT）
        """
        self.project_root = project_root or PROJECT_ROOT
        self.source_root = SOURCE_ROOT
        self.manifest_path = ANDROID_MANIFEST
        self.output_root = AI_TESTS_CASES_DIR
        self.template_path = AUTO_TEST_TEMPLATE
        # 懒加载 manifest 解析结果（避免每次 generate 都读 XML）
        self._manifest_cache: Optional[dict] = None

    # === 13.2 主入口 ===

    def generate(self, activity_name: str, module: str = "auto") -> str:
        """主入口：为指定 Activity 生成 Python 测试骨架

        Args:
            activity_name: Activity 类名（如 "DebugToolsActivity"）
            module: 模块名（"auto" 时自动推断，如 "F-P0-1"）

        Returns:
            生成的 Python 文件路径

        Raises:
            FileNotFoundError: Activity 源码未找到
            RuntimeError: 模板渲染失败
        """
        print(f"[M9] 开始为 {activity_name} 生成测试骨架（module={module}）")

        # 1. 定位源码
        activity_path = self._locate_activity(activity_name)
        if not activity_path:
            raise FileNotFoundError(
                f"Activity {activity_name} 未在 {self.source_root} 下找到"
            )
        print(f"    源码定位: {activity_path}")

        # 2. 解析源码
        source_info = self._parse_activity_source(activity_path)
        print(
            f"    源码解析: view_ids={len(source_info['view_ids'])}, "
            f"activity_jumps={len(source_info['activity_jumps'])}, "
            f"layout={source_info['layout']}"
        )

        # 3. 解析 AndroidManifest.xml
        manifest_info = self._parse_manifest()
        is_registered = activity_name in manifest_info.get("registered_activities", [])
        print(f"    Manifest 注册: {'是' if is_registered else '否'}")

        # 4. 模块自动推断
        if module == "auto":
            module = self._infer_module(activity_name)
            print(f"    模块推断: {module}")

        # 5. TC-ID 自动分配
        tc_id = self._allocate_tc_id(module)
        print(f"    TC-ID 分配: {tc_id}")

        # 6. 渲染骨架
        skeleton = self._render_skeleton(
            activity_name=activity_name,
            activity_path=activity_path,
            source_info=source_info,
            manifest_info=manifest_info,
            module=module,
            tc_id=tc_id,
        )

        # 7. 写入文件
        # 简化说明：文件名遵循 M3 _find_python_track 规则 1：auto_{tc_id_lower_with_underscores}.py | 已知上限：无 | 升级路径：无
        output_dir = self.output_root / module
        output_dir.mkdir(parents=True, exist_ok=True)
        # TC-F-P0-1-auto-002 → auto_tc_f_p0_1_auto_002.py（M3 规则 1 文件名匹配）
        file_name = f"auto_{tc_id.lower().replace('-', '_')}.py"
        output_file = output_dir / file_name
        output_file.write_text(skeleton, encoding="utf-8")
        print(f"    输出文件: {output_file}")

        return str(output_file)

    # === 13.3 定位源码 ===

    def _locate_activity(self, activity_name: str) -> Optional[Path]:
        """在 source_root 下递归查找 {activity_name}.kt 或 .java

        Args:
            activity_name: Activity 类名（不含扩展名）

        Returns:
            找到的文件 Path，未找到返回 None
        """
        # 简化说明：仅匹配文件名，不区分类全名 | 已知上限：同名 Activity 在不同包会命中第一个 | 升级路径：基于 package 声明精确匹配（V4）
        for candidate in self.source_root.rglob(f"{activity_name}.kt"):
            return candidate
        for candidate in self.source_root.rglob(f"{activity_name}.java"):
            return candidate
        return None

    # === 13.4 解析源码 ===

    def _parse_activity_source(self, activity_path: Path) -> dict:
        """解析 Activity 源码，提取 UI 元素和跳转

        提取内容：
        - layout: setContentView(R.layout.xxx)
        - view_ids: findViewById<R.id.xxx> 和 R.id.xxx
        - binding_ids: binding.xxx（viewBinding 模式）
        - click_targets: xxx.setOnClickListener { startActivity... }
        - activity_jumps: startActivity(Intent(this, XxxActivity::class.java))

        Args:
            activity_path: Activity 源码文件路径

        Returns:
            dict: {layout, view_ids, binding_ids, click_targets, activity_jumps}
        """
        content = activity_path.read_text(encoding="utf-8")

        # 1. 提取 setContentView(R.layout.xxx)
        layout_match = re.search(r'setContentView\s*\(\s*R\.layout\.(\w+)', content)
        layout = layout_match.group(1) if layout_match else None

        # 2. 提取 R.id.xxx（含 findViewById 和直接引用）
        # findViewById<R.id.xxx> 或 findViewById(R.id.xxx)
        view_ids_from_find = re.findall(
            r'findViewById\s*<\w+>\s*\(\s*R\.id\.(\w+)\s*\)', content
        )
        # 直接 R.id.xxx 引用（如 syncBtn.setOnClickListener）
        # 简化说明：提取所有 R.id.xxx 然后去重 | 已知上限：包含非点击事件的 id | 升级路径：基于上下文过滤（V4）
        view_ids_from_direct = re.findall(r'R\.id\.(\w+)', content)
        view_ids = list(dict.fromkeys(view_ids_from_find + view_ids_from_direct))  # 去重保序

        # 3. 提取 binding.xxx（viewBinding 模式）
        binding_ids = re.findall(r'binding\.(\w+)', content)
        binding_ids = list(dict.fromkeys(binding_ids))  # 去重保序

        # 4. 提取 click_targets（setOnClickListener + startActivity 组合）
        # 简化说明：跨行正则匹配 click→jump 组合 | 已知上限：复杂跳转逻辑可能漏匹配 | 升级路径：基于 AST 分析（V4）
        click_targets = re.findall(
            r'(\w+)\s*\.\s*setOnClickListener\s*\{[^}]*startActivity[^}]*Intent\s*\(\s*this\s*,\s*(\w+)::class\.java',
            content, re.DOTALL
        )
        # click_targets 格式：[(btn_name, TargetActivity), ...]

        # 5. 提取所有 startActivity 跳转
        activity_jumps = re.findall(
            r'startActivity\s*\(\s*Intent\s*\(\s*this\s*,\s*(\w+)::class\.java', content
        )
        # 也兼容 startActivity<XXXActivity> 形式
        activity_jumps += re.findall(r'startActivity\s*<\s*(\w+)\s*>', content)
        activity_jumps = list(dict.fromkeys(activity_jumps))  # 去重保序

        return {
            "layout": layout,
            "view_ids": view_ids,
            "binding_ids": binding_ids,
            "click_targets": click_targets,
            "activity_jumps": activity_jumps,
        }

    # === 13.5 解析 Manifest ===

    def _parse_manifest(self) -> dict:
        """解析 AndroidManifest.xml，提取所有注册的 Activity

        Returns:
            dict: {registered_activities: ["ActivityName", ...]}
        """
        if self._manifest_cache is not None:
            return self._manifest_cache

        if not self.manifest_path.exists():
            logger.warning(f"AndroidManifest.xml 不存在: {self.manifest_path}")
            return {"registered_activities": []}

        content = self.manifest_path.read_text(encoding="utf-8")
        # 提取 <activity android:name=".xxx.SubActivity" /> 和 android:name="xxx"
        # 简化说明：仅提取类名，不解析完整包路径 | 已知上限：alias Activity 不解析 | 升级路径：基于 XML 解析器（V4）
        activities = re.findall(
            r'<activity\s+[^>]*android:name="\.?([\w\.]+)"', content
        )
        # 取最后一段作为类名（.ui.book.BookshelfActivity → BookshelfActivity）
        registered = []
        for full_name in activities:
            class_name = full_name.split(".")[-1]
            registered.append(class_name)
        registered = list(dict.fromkeys(registered))  # 去重

        self._manifest_cache = {"registered_activities": registered}
        logger.info(f"Manifest 解析: {len(registered)} 个已注册 Activity")
        return self._manifest_cache

    # === 13.7 渲染骨架（Jinja2）===

    def _render_skeleton(
        self,
        activity_name: str,
        activity_path: Path,
        source_info: dict,
        manifest_info: dict,
        module: str,
        tc_id: str,
    ) -> str:
        """渲染 Python 测试骨架

        使用 Jinja2 模板 auto_test_template.j2 渲染。

        Args:
            activity_name: Activity 类名
            activity_path: 源码路径
            source_info: _parse_activity_source 输出
            manifest_info: _parse_manifest 输出
            module: 模块名
            tc_id: 分配的 TC-ID

        Returns:
            渲染后的 Python 代码字符串
        """
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError as e:
            raise RuntimeError(
                f"Jinja2 未安装，无法渲染模板: {e}\n"
                f"请运行: pip install jinja2"
            ) from e

        if not self.template_path.exists():
            raise RuntimeError(f"模板文件不存在: {self.template_path}")

        # 计算完整 Activity 类名（用于 am start 命令）
        # 简化说明：假设 source_root 是 io.legado.app/，所以前缀固定为 io.legado.app | 已知上限：source_root 改变时需同步 | 升级路径：从源码 package 声明动态提取（V4）
        relative_path = activity_path.relative_to(self.source_root)
        full_activity_class = (
            str(relative_path)
            .replace("\\", "/")
            .replace(".kt", "")
            .replace(".java", "")
            .replace("/", ".")
        )
        # 完整类名：io.legado.app.ui.debug.DebugToolsActivity
        full_activity_class = f"io.legado.app.{full_activity_class}"

        # 准备模板变量
        is_registered = activity_name in manifest_info.get("registered_activities", [])
        activity_count_hint = len(manifest_info.get("registered_activities", []))

        # Jinja2 环境（不启用自动转义，因为生成 Python 代码）
        env = Environment(
            loader=FileSystemLoader(str(self.template_path.parent)),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
            trim_blocks=False,
            lstrip_blocks=False,
        )
        template = env.get_template(self.template_path.name)

        rendered = template.render(
            activity_name=activity_name,
            generated_at=datetime.now().isoformat(),
            tc_id=tc_id,
            module=module,
            source_path=str(activity_path.relative_to(self.project_root)).replace("\\", "/"),
            package_name=PACKAGE,
            full_activity_class=full_activity_class,
            view_ids=source_info["view_ids"],
            binding_ids=source_info["binding_ids"],
            activity_jumps=source_info["activity_jumps"],
            layout=source_info["layout"],
            is_registered=is_registered,
            activity_count_hint=activity_count_hint,
        )

        return rendered

    # === 13.8 TC-ID 自动分配 ===

    def _allocate_tc_id(self, module: str) -> str:
        """基于 module 前缀 + 现有最大编号 +1 分配 TC-ID

        规则：
        - 扫描 ai_tests/cases/{module}/auto_tc_{module_lower}_auto_*.py
        - 提取现有最大编号
        - 新编号 = 最大编号 + 1
        - 格式：TC-{module}-auto-{NNN}（返回值用大写连字符，文件名用小写下划线）

        Args:
            module: 模块名（如 "F-P0-1"）

        Returns:
            新分配的 TC-ID（如 "TC-F-P0-1-auto-001"）
        """
        module_dir = self.output_root / module
        # 文件名格式：auto_{tc_id_lower_with_underscores}.py（M3 规则 1）
        # TC-F-P0-1-auto-XXX → auto_tc_f_p0_1_auto_XXX.py
        tc_id_prefix = f"TC-{module}-auto-".lower().replace('-', '_')
        pattern = re.compile(
            r'^auto_' + re.escape(tc_id_prefix) + r'(\d+)\.py$'
        )

        max_num = 0
        if module_dir.exists():
            for py_file in module_dir.glob("auto_*.py"):
                m = pattern.match(py_file.name)
                if m:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num

        new_num = max_num + 1
        return f"TC-{module}-auto-{new_num:03d}"

    # === 辅助：模块自动推断 ===

    def _infer_module(self, activity_name: str) -> str:
        """从 source_map.json 推断 Activity 所属模块

        规则：
        1. 加载 source_map.json
        2. 查找该 Activity 关联的 TC-ID
        3. 从 TC-ID 提取模块前缀（TC-F-P0-1-xx → F-P0-1）

        Args:
            activity_name: Activity 类名

        Returns:
            模块名（如 "F-P0-1"），无法推断时返回 "auto"
        """
        # 简化说明：依赖 M8 生成的 source_map.json | 已知上限：source_map 过时时会推断失败 | 升级路径：自动触发重建（V4）
        source_map_path = self.project_root / "ai_tests" / "lib" / "source_map.json"
        if not source_map_path.exists():
            logger.warning(
                f"source_map.json 不存在，模块推断降级为 'auto'。"
                f"请先运行: python ai_tests/run_e2e.py --update-source-map"
            )
            return "auto"

        import json
        try:
            source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"source_map.json 解析失败: {e}，模块推断降级为 'auto'")
            return "auto"

        activities = source_map.get("activities", {})
        activity_info = activities.get(activity_name, {})
        tc_ids = activity_info.get("tc_ids", [])

        if not tc_ids:
            logger.info(f"Activity {activity_name} 在 source_map 中无关联 TC-ID，模块推断为 'auto'")
            return "auto"

        # 从第一个 TC-ID 提取模块前缀
        # TC-F-P0-1-01 → F-P0-1
        # TC-P0-1-01 → P0-1
        first_tc = tc_ids[0]
        m = re.match(r'^TC-([FPA]-P[01]-\d+)', first_tc)
        if m:
            return m.group(1)

        logger.info(f"TC-ID {first_tc} 格式不匹配模块提取规则，模块推断为 'auto'")
        return "auto"


# === 自检入口 ===

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("M9 SourceTestGenerator 自检")
    print("=" * 70)
    print()

    gen = SourceTestGenerator()

    # 1. 模板存在性检查
    print(f"[1] 模板路径: {gen.template_path}")
    print(f"    存在: {'是' if gen.template_path.exists() else '否'}")
    print()

    # 2. Manifest 解析自检
    print("[2] Manifest 解析...")
    manifest = gen._parse_manifest()
    registered = manifest.get("registered_activities", [])
    print(f"    已注册 Activity 数: {len(registered)}")
    # 检查几个关键 Activity 是否注册
    for key_activity in ["MainActivity", "BookshelfActivity", "DebugToolsActivity", "WelcomeActivity"]:
        found = key_activity in registered
        print(f"    {key_activity}: {'已注册' if found else '未注册'}")
    print()

    # 3. 单 Activity 生成测试（命令行参数指定）
    if len(sys.argv) > 1:
        target_activity = sys.argv[1]
        module = sys.argv[2] if len(sys.argv) > 2 else "auto"
        print(f"[3] 生成测试骨架: {target_activity} (module={module})")
        try:
            output = gen.generate(target_activity, module=module)
            print(f"    生成成功: {output}")
            print()
            print("--- 生成内容预览 ---")
            print(Path(output).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    生成失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[3] 跳过生成测试（未传 Activity 名称）")
        print("    用法: python -m ai_tests.lib.source_test_generator DebugToolsActivity [module]")
        print()

    print()
    print("=" * 70)
    print("自检完成")
    print("=" * 70)
