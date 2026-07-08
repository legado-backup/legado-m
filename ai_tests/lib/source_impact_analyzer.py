"""ai_tests/lib/source_impact_analyzer.py — M8 源码影响分析器（V3 新增）

职责：
- 分析 git diff 改动文件，反向追溯到受影响 Activity
- 基于 source_map.json 静态调用图 + 关联 TC-ID
- 输出 recommended_rerun（建议复测的用例 ID 列表）

数据流：
    git diff --name-only <git_ref>
        → _reverse_trace() 向上追溯 2 层找到调用方 Activity
        → _lookup_related_tc_ids() 查 source_map 关联 TC-ID
        → 输出 {changed_files, affected_activities, related_tc_ids, recommended_rerun}

source_map.json 结构：
    {
      "version": "1.0",
      "generated_at": "2026-07-08T...",
      "activities": {
        "BookSourceActivity": {
          "path": "app/src/main/java/.../BookSourceActivity.kt",
          "callers": ["MainActivity", "ConfigActivity"],
          "ui_components": ["R.id.recycler_view", "R.id.fab"],
          "tc_ids": ["TC-F-P0-2-01", "TC-F-P0-2-02"]
        }
      }
    }

依赖：subprocess（git）、pathlib、re；不依赖 LLM SDK
"""
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ai_tests.config import (
    SOURCE_ROOT, SOURCE_MAP_PATH, PROJECT_ROOT,
    DOCS_TESTS_DIR, AI_TESTS_CASES_DIR,
)

logger = logging.getLogger(__name__)


# === 常量 ===

# Activity 类名正则（Kotlin 文件中 `class XxxActivity`）
ACTIVITY_CLASS_RE = re.compile(
    r'\bclass\s+([A-Z][A-Za-z0-9]*Activity)\b'
)

# UI 组件提取正则
# 简化说明：覆盖 R.id.xxx / findViewById / setContentView / Compose setContent 四种 UI 组件引用方式
# 已知上限：未覆盖 databinding 直接引用、DataBinding 自动生成的 Binding 类
# 升级路径：基于 Kotlin 语法树分析（需要 tree-sitter-java，V4）
R_ID_RE = re.compile(r'R\.id\.([A-Za-z_][A-Za-z0-9_]*)')
FIND_VIEW_BY_ID_RE = re.compile(
    r'findViewById\s*<[^>]+>\s*\(\s*R\.id\.([A-Za-z_][A-Za-z0-9_]*)\s*\)'
)
SET_CONTENT_VIEW_RE = re.compile(
    r'setContentView\s*\(\s*R\.layout\.([A-Za-z_][A-Za-z0-9_]*)\s*\)'
)
COMPOSE_SET_CONTENT_RE = re.compile(r'\bsetContent\s*\{')

# Activity 文件引用正则（用于 _find_callers：在所有 .kt 文件中 grep Activity 类名）
# 形如：startActivity< XxxActivity >(...) / startActivity(Intent(ctx, XxxActivity::class.java))
ACTIVITY_REFERENCE_RE_TEMPLATE = r'\b{class_name}\b'

# 向上追溯最大层数
MAX_REVERSE_TRACE_DEPTH = 2

# source_map.json 当前版本
SOURCE_MAP_VERSION = "1.0"


class SourceImpactAnalyzer:
    """源码影响分析器

    基于 git diff 反向追溯受影响 Activity，并查询 source_map.json 找关联 TC-ID。
    不依赖任何 LLM SDK，纯静态分析 + 文件扫描。

    用法：
        sia = SourceImpactAnalyzer()
        result = sia.analyze_diff("HEAD~1")
        # result = {"changed_files": [...], "affected_activities": [...],
        #           "related_tc_ids": [...], "recommended_rerun": [...]}
    """

    def __init__(
        self,
        source_root: Path = SOURCE_ROOT,
        source_map_path: Path = SOURCE_MAP_PATH,
        project_root: Path = PROJECT_ROOT,
        docs_tests_dir: Path = DOCS_TESTS_DIR,
        ai_tests_cases_dir: Path = AI_TESTS_CASES_DIR,
    ):
        self.source_root = Path(source_root)
        self.source_map_path = Path(source_map_path)
        self.project_root = Path(project_root)
        self.docs_tests_dir = Path(docs_tests_dir)
        self.ai_tests_cases_dir = Path(ai_tests_cases_dir)
        # 简化说明：source_map 懒加载 | 已知上限：并发场景下需加锁 | 升级路径：threading.Lock（V4）
        self._source_map: Optional[Dict] = None

    # === 12.2 公开入口：analyze_diff ===

    def analyze_diff(self, git_ref: str = "HEAD~1") -> Dict:
        """分析 git diff，输出受影响的 Activity 和建议复测的 TC-ID

        Args:
            git_ref: git 引用（如 HEAD~1、HEAD~5、分支名、commit hash）
        Returns:
            {
                "changed_files": [...],         # 改动文件相对路径列表
                "affected_activities": [...],   # 受影响 Activity 类名列表
                "related_tc_ids": [...],        # 关联 TC-ID 列表
                "recommended_rerun": [...],     # 建议复测 TC-ID（去重）
                "git_ref": str,                 # 输入的 git ref
                "analyzed_at": str,             # ISO 时间戳
            }
        """
        logger.info(f"开始分析 git diff: {git_ref}")

        # 1. git diff --name-only 取改动文件
        changed_files = self._git_diff_name_only(git_ref)
        if not changed_files:
            logger.warning(f"git diff {git_ref} 无改动文件")
            return {
                "changed_files": [],
                "affected_activities": [],
                "related_tc_ids": [],
                "recommended_rerun": [],
                "git_ref": git_ref,
                "analyzed_at": datetime.now().isoformat(),
            }
        logger.info(f"改动文件数: {len(changed_files)}")

        # 2. 加载/构建 source_map
        source_map = self._load_or_build_source_map()

        # 3. 反向追溯：改动文件 → 受影响 Activity
        affected_activities = self._reverse_trace(changed_files, source_map)
        logger.info(f"受影响 Activity 数: {len(affected_activities)}")

        # 4. 查关联 TC-ID
        related_tc_ids = self._lookup_related_tc_ids(affected_activities, source_map)
        logger.info(f"关联 TC-ID 数: {len(related_tc_ids)}")

        return {
            "changed_files": changed_files,
            "affected_activities": sorted(affected_activities),
            "related_tc_ids": sorted(related_tc_ids),
            "recommended_rerun": sorted(related_tc_ids),
            "git_ref": git_ref,
            "analyzed_at": datetime.now().isoformat(),
        }

    # === git diff 调用 ===

    def _git_diff_name_only(self, git_ref: str) -> List[str]:
        """执行 git diff --name-only <git_ref>

        Args:
            git_ref: git 引用
        Returns:
            改动文件相对路径列表（相对于项目根）
        Raises:
            RuntimeError: git 命令执行失败
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", git_ref],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                # git diff 可能因 ref 不存在返回非零，记录 stderr
                logger.error(
                    f"git diff --name-only {git_ref} 失败: "
                    f"returncode={result.returncode}, stderr={result.stderr.strip()}"
                )
                return []
            files = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]
            return files
        except FileNotFoundError:
            logger.error("git 命令未找到（PATH 中无 git）")
            return []
        except subprocess.TimeoutExpired:
            logger.error(f"git diff {git_ref} 超时")
            return []
        except Exception as e:
            logger.error(f"git diff {git_ref} 异常: {e}")
            return []

    # === 12.3 _load_or_build_source_map ===

    def _load_or_build_source_map(self) -> Dict:
        """加载或构建 source_map

        若 source_map.json 存在且非空则加载，否则调 build_source_map() 重建。

        Returns:
            source_map dict
        """
        if self._source_map is not None:
            return self._source_map

        if self.source_map_path.exists():
            try:
                with open(self.source_map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("activities"):
                    logger.info(
                        f"加载 source_map.json: {len(data['activities'])} 个 Activity"
                    )
                    self._source_map = data
                    return data
                logger.warning("source_map.json 为空或无 activities，重建...")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"source_map.json 加载失败: {e}，重建...")

        # 重建
        self._source_map = self.build_source_map()
        return self._source_map

    # === 12.4 build_source_map ===

    def build_source_map(self) -> Dict:
        """构建 source_map（扫描所有 Activity.kt + 关联 TC-ID）

        流程：
        1. 扫描 SOURCE_ROOT 下所有 *Activity.kt（排除 Base 类）
        2. 对每个 Activity：
           - _extract_ui_components 提取 UI 组件
           - _find_callers 找调用方
           - _scan_tc_ids_for_activity 找关联 TC-ID
        3. 持久化到 source_map.json

        Returns:
            source_map dict
        """
        logger.info(f"开始构建 source_map，扫描 {self.source_root}")

        activity_files = list(self.source_root.rglob("*Activity.kt"))
        # 排除抽象/基类：BaseActivity / VMBaseActivity 等
        activity_files = [
            f for f in activity_files
            if not f.name.startswith("Base") and not f.name.startswith("VMBase")
        ]
        logger.info(f"发现 Activity 文件: {len(activity_files)}")

        activities: Dict[str, Dict] = {}
        for activity_file in activity_files:
            class_name = activity_file.stem  # 文件名即类名（Kotlin 约定）
            try:
                content = activity_file.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning(f"读取 {activity_file} 失败: {e}")
                continue

            ui_components = self._extract_ui_components(content)
            callers = self._find_callers(class_name)
            tc_ids = self._scan_tc_ids_for_activity(class_name)

            activities[class_name] = {
                "path": str(activity_file.relative_to(self.project_root)),
                "callers": callers,
                "ui_components": ui_components,
                "tc_ids": tc_ids,
            }
            logger.debug(
                f"Activity {class_name}: callers={len(callers)}, "
                f"ui_components={len(ui_components)}, tc_ids={len(tc_ids)}"
            )

        source_map = {
            "version": SOURCE_MAP_VERSION,
            "generated_at": datetime.now().isoformat(),
            "activities": activities,
        }

        # 持久化
        try:
            self.source_map_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.source_map_path, "w", encoding="utf-8") as f:
                json.dump(source_map, f, ensure_ascii=False, indent=2)
            logger.info(
                f"source_map.json 已保存: {self.source_map_path} "
                f"({len(activities)} 个 Activity)"
            )
        except OSError as e:
            logger.error(f"source_map.json 保存失败: {e}")

        self._source_map = source_map
        return source_map

    # === 12.5 _find_callers ===

    def _find_callers(self, activity_class_name: str) -> List[str]:
        """grep 文件名引用，找调用方 Activity（粗粒度静态调用图）

        策略：在所有 .kt 文件中搜索 `activity_class_name` 字符串引用，
        然后对每个匹配文件，提取其所在文件的 Activity 类名作为调用方。

        Args:
            activity_class_name: Activity 类名（如 "BookSourceActivity"）
        Returns:
            调用方 Activity 类名列表（去重）
        """
        if not activity_class_name:
            return []

        pattern = re.compile(
            ACTIVITY_REFERENCE_RE_TEMPLATE.format(
                class_name=re.escape(activity_class_name)
            )
        )

        callers: Set[str] = set()
        # 在 SOURCE_ROOT 下扫描所有 .kt 文件
        for kt_file in self.source_root.rglob("*.kt"):
            try:
                content = kt_file.read_text(encoding="utf-8")
            except OSError:
                continue

            # 跳过自身
            if kt_file.stem == activity_class_name:
                continue

            # 简化说明：全文 grep 类名字符串 | 已知上限：会误报注释中的引用 | 升级路径：基于 AST 分析（V4）
            if not pattern.search(content):
                continue

            # 提取所在文件的 Activity 类名（如果该文件是 Activity）
            file_stem = kt_file.stem
            if file_stem.endswith("Activity") and not file_stem.startswith("Base"):
                callers.add(file_stem)

        return sorted(callers)

    # === 12.6 _extract_ui_components ===

    def _extract_ui_components(self, source_content: str) -> List[str]:
        """从 Activity 源码中提取 UI 组件引用

        覆盖：
        - R.id.xxx 资源 ID
        - findViewById(R.id.xxx)
        - setContentView(R.layout.xxx)
        - Compose setContent { ... }

        Args:
            source_content: Activity .kt 文件内容
        Returns:
            UI 组件引用列表（去重）
        """
        components: Set[str] = set()

        # R.id.xxx
        for m in R_ID_RE.finditer(source_content):
            components.add(f"R.id.{m.group(1)}")

        # findViewById(R.id.xxx) — 已被 R.id.xxx 覆盖，无需重复

        # setContentView(R.layout.xxx)
        for m in SET_CONTENT_VIEW_RE.finditer(source_content):
            components.add(f"R.layout.{m.group(1)}")

        # Compose setContent { }
        if COMPOSE_SET_CONTENT_RE.search(source_content):
            components.add("setContent{}")

        return sorted(components)

    # === 12.7 _reverse_trace ===

    def _reverse_trace(
        self,
        changed_files: List[str],
        source_map: Dict,
    ) -> List[str]:
        """改动文件 → 调用方 Activity（向上追溯 MAX_REVERSE_TRACE_DEPTH 层）

        策略：
        1. 改动文件直接匹配 Activity 类名 → 直接受影响
        2. 改动文件被某个 Activity 引用（在 source_map.callers 中） → 间接受影响
        3. 递归向上追溯 MAX_REVERSE_TRACE_DEPTH 层

        Args:
            changed_files: 改动文件相对路径列表
            source_map: source_map dict
        Returns:
            受影响 Activity 类名列表（去重）
        """
        activities_map = source_map.get("activities", {})

        # 构建 文件名 → Activity 类名 的映射
        # 简化说明：基于文件名 stem 匹配 | 已知上限：同名文件在不同包会冲突 | 升级路径：基于完整路径匹配（V4）
        file_to_activity: Dict[str, str] = {}
        for activity_name, info in activities_map.items():
            path = info.get("path", "")
            if path:
                file_stem = Path(path).stem
                file_to_activity[file_stem] = activity_name

        # 第一层：改动文件本身是 Activity
        affected: Set[str] = set()
        for changed_file in changed_files:
            file_stem = Path(changed_file).stem
            if file_stem in file_to_activity:
                affected.add(file_to_activity[file_stem])

        # 递归向上追溯调用方
        # 简化说明：BFS 遍历调用链 | 已知上限：MAX_REVERSE_TRACE_DEPTH=2 限制深度 | 升级路径：可配置深度（V4）
        current_layer = set(affected)
        for depth in range(MAX_REVERSE_TRACE_DEPTH):
            next_layer: Set[str] = set()
            for activity_name in current_layer:
                info = activities_map.get(activity_name, {})
                callers = info.get("callers", [])
                for caller in callers:
                    if caller not in affected:
                        next_layer.add(caller)
            if not next_layer:
                break
            affected.update(next_layer)
            current_layer = next_layer

        return sorted(affected)

    # === 12.8 _lookup_related_tc_ids ===

    def _lookup_related_tc_ids(
        self,
        affected_activities: List[str],
        source_map: Dict,
    ) -> List[str]:
        """受影响 Activity → 关联 TC-ID（从 source_map.activities[name].tc_ids）

        Args:
            affected_activities: 受影响 Activity 类名列表
            source_map: source_map dict
        Returns:
            关联 TC-ID 列表（去重）
        """
        activities_map = source_map.get("activities", {})
        tc_ids: Set[str] = set()

        for activity_name in affected_activities:
            info = activities_map.get(activity_name, {})
            activity_tc_ids = info.get("tc_ids", [])
            tc_ids.update(activity_tc_ids)

        return sorted(tc_ids)

    # === 辅助：扫描用例 md 找关联 Activity 的 TC-ID ===

    def _scan_tc_ids_for_activity(self, activity_class_name: str) -> List[str]:
        """扫描 docs/tests/*.md 找关联此 Activity 的 TC-ID

        匹配规则：
        1. md 中 "**关联 Activity**：xxxActivity" 段直接命中
        2. md 中 "**关联源码**：xxxActivity.kt" 段间接命中

        Args:
            activity_class_name: Activity 类名（如 "BookSourceActivity"）
        Returns:
            关联此 Activity 的 TC-ID 列表
        """
        if not activity_class_name:
            return []

        tc_ids: Set[str] = set()

        # 扫描 docs/tests/ 和 ai_tests/cases/ 下所有 .md
        search_dirs = [self.docs_tests_dir, self.ai_tests_cases_dir]
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for md_file in search_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except OSError:
                    continue

                # 检查是否提及此 Activity
                if activity_class_name not in content:
                    continue

                # 提取所有 TC-ID（## TC-XXX：标题 或 ### TC-XXX：标题）
                # 注意：TC_HEADER_RE 没有 re.MULTILINE flag，^ 只匹配字符串开头，
                # 必须逐行 match（与 case_parser 一致），不能用 findall/finditer 全文扫描
                from ai_tests.lib.case_parser import TC_HEADER_RE
                for line in content.splitlines():
                    m = TC_HEADER_RE.match(line)
                    if m:
                        tc_ids.add(m.group(1))

        return sorted(tc_ids)

    # === 工具方法 ===

    def get_source_map_summary(self) -> Dict:
        """获取 source_map 摘要（不重建）

        Returns:
            {"total_activities": N, "total_tc_ids": N, "total_callers": N, ...}
        """
        if self._source_map is None:
            if self.source_map_path.exists():
                try:
                    with open(self.source_map_path, "r", encoding="utf-8") as f:
                        self._source_map = json.load(f)
                except (json.JSONDecodeError, OSError):
                    return {"total_activities": 0, "error": "source_map.json 无效"}
            else:
                return {"total_activities": 0, "error": "source_map.json 不存在"}

        activities = self._source_map.get("activities", {})
        all_tc_ids: Set[str] = set()
        all_callers: Set[str] = set()
        for info in activities.values():
            all_tc_ids.update(info.get("tc_ids", []))
            all_callers.update(info.get("callers", []))

        return {
            "version": self._source_map.get("version", "?"),
            "generated_at": self._source_map.get("generated_at", "?"),
            "total_activities": len(activities),
            "total_tc_ids": len(all_tc_ids),
            "total_unique_callers": len(all_callers),
            "source_map_path": str(self.source_map_path),
        }


# === 模块自检 ===

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sia = SourceImpactAnalyzer()
    print("=" * 70)
    print("M8 SourceImpactAnalyzer 自检")
    print("=" * 70)

    # 1. 构建 source_map
    print("\n[1] 构建 source_map...")
    source_map = sia.build_source_map()
    summary = sia.get_source_map_summary()
    print(f"    总 Activity 数: {summary.get('total_activities', 0)}")
    print(f"    关联 TC-ID 总数: {summary.get('total_tc_ids', 0)}")
    print(f"    唯一调用方总数: {summary.get('total_unique_callers', 0)}")

    # 2. 测试 analyze_diff
    if len(sys.argv) > 1:
        git_ref = sys.argv[1]
        print(f"\n[2] analyze_diff({git_ref})...")
        result = sia.analyze_diff(git_ref)
        print(f"    改动文件数: {len(result['changed_files'])}")
        print(f"    受影响 Activity 数: {len(result['affected_activities'])}")
        print(f"    关联 TC-ID 数: {len(result['related_tc_ids'])}")
        print(f"    建议复测 TC-ID 数: {len(result['recommended_rerun'])}")
        if result['affected_activities']:
            print(f"    受影响 Activity: {result['affected_activities'][:5]}...")
        if result['recommended_rerun']:
            print(f"    建议复测: {result['recommended_rerun'][:5]}...")
    else:
        print("\n[2] 跳过 analyze_diff（未传 git_ref 参数）")
        print("    用法: python -m ai_tests.lib.source_impact_analyzer HEAD~1")
