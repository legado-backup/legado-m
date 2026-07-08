# design.md — Legado AI 自动化测试基础设施（V3）

> **状态**：🔄 设计中（V3，基于用户深度反馈再次重构）
> **创建日期**：2026-07-07
> **V2 调整日期**：2026-07-07
> **V3 调整日期**：2026-07-07
> **核心调整**：新增 M8/M9 源码驱动模块、双轨用例、source_map.json、三阶段流程验证、固化/迭代层分类、反馈闭环、ADR-13~17

---

## 一、Technical Approach（技术方案）

### 1.1 V2 → V3 关键技术变更

| 维度 | V2（已采纳） | V3（再次升级） | 变更理由 |
|------|------------|---------------|---------|
| **模块数** | 7 个（M1-M7） | **9 个（M1-M9，新增 M8/M9）** | 用户要求基于源码深度定制 |
| **架构** | 三层 | **三层 + Layer 0 源码驱动层** | M8/M9 需独立层级 |
| **用例机制** | MD 单轨 | **双轨：MD + Python** | 复杂交互精准化 |
| **源码利用** | 不读源码 | **M8 影响分析 + M9 测试生成** | 非多模态下的精准化机会 |
| **流程验证** | 端到端跑通 | **三阶段（含流程注入验证）** | 流程本身需被验证 |
| **反馈机制** | 无 | **反馈闭环：规则库/陷阱库/提示词** | AI 越来越准 |
| **ADRs** | 12 条（AD-01~AD-12） | **17 条（新增 AD-13~AD-17）** | V3 决策记录 |

### 1.2 系统架构总览（V3 四层 + 源码驱动层）

```
┌──────────────────────────────────────────────────────────────────────┐
│  OpenSpec 工作流（步骤 5.5 强制嵌入，V3 含 8 子步骤）                    │
│  ↓ AI agent 触发 ↓                                                    │
│  python ai_tests/run_e2e.py --apk auto --tc all --diff HEAD~1       │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 3: 编排层（orchestrator）                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │ run_e2e.py: 参数解析 → 串联 9 模块 → 汇总报告 → 退出码       │     │
│  │ --apk auto|path, --tc all|P0|F-P0-1|TC-XXX, --keep-device   │     │
│  │ V3 新增: --diff, --gen-test, --update-source-map, --feedback│     │
│  └──────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 2: 用例与执行层（execution）                                    │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐            │
│  │ M3 用例解析器   │ │ M4 UI 执行器   │ │ M5 证据收集器   │            │
│  │ V3: 双轨调度    │ │ uiautomator2   │ │ 8 类证据        │            │
│  │ (MD+Python)     │ │ (openatx)      │ │ (ADB+u2+curl)   │            │
│  └────────────────┘ └────────────────┘ └────────────────┘            │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 1: 基础设施层（infrastructure）                                 │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐            │
│  │ M1 模拟器控制  │ │ M2 APK 部署    │ │ M6 规则分析器   │            │
│  │ memuc.exe      │ │ 自动发现+安装   │ │ 纯规则+manual   │            │
│  └────────────────┘ └────────────────┘ └────────────────┘            │
│  ┌──────────────────────────────────────────────────────┐             │
│  │ M7 报告生成器：Markdown + JSON + manual_cases.md       │             │
│  │ V3: + affected_modules.json + feedback_signal        │             │
│  └──────────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  V3 新增 Layer 0: 源码驱动层（source-driven）                          │
│  ┌────────────────────────────┐ ┌────────────────────────────────┐   │
│  │ M8 源码影响分析器          │ │ M9 源码→测试生成器              │   │
│  │ git diff → source_map.json │ │ Activity 源码 → Python 骨架    │   │
│  │ → affected_modules         │ │ → auto_{tc_id}.py             │   │
│  └────────────────────────────┘ └────────────────────────────────┘   │
│  输入：app/src/main/ + AndroidManifest.xml（只读）                    │
│  输出：source_map.json + auto_*.py + affected_modules.json            │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  外部依赖                                                              │
│  ┌────────────────┐ ┌────────────────┐                              │
│  │ MEmu 实例 0    │ │ Android 设备    │   ❌ 无 LLM 服务依赖          │
│  │ D:\...\MEmu    │ │ io.legado.app  │   ❌ 无多模态模型依赖          │
│  └────────────────┘ └────────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  输出 reports/{run_id}/                                                │
│  ├── report.md                 # 人读报告                             │
│  ├── report.json               # 机器可读（AI agent 接入）             │
│  ├── manual_cases.md           # manual 用例清单 + AI 分析提示词        │
│  ├── summary.txt               # 一行摘要（pass率/失败数/manual数）     │
│  ├── affected_modules.json     # V3: 源码影响分析结果（机器读）          │
│  ├── feedback_suggestions.md   # V3: 反馈闭环建议清单（人读，AI agent 审阅）│
│  ├── feedback_suggestions.json # V3: 反馈闭环建议清单（机器读，M16 回填） │
│  └── cases/{tc_id}/            # 每用例证据目录                        │
│      ├── step-XX-*.png|xml     # 截图+UI XML                          │
│      ├── log-slice.txt          # 日志切片                             │
│      ├── activity-stack.txt     # Activity 栈                         │
│      ├── db-state.json         # 数据库状态                            │
│      ├── prefs-state.json      # SharedPreferences                    │
│      ├── web-api-resp.json     # Web API 响应                        │
│      ├── meminfo.txt           # 内存状态                              │
│      └── ai-prompt.md          # AI agent 分析提示词（manual 时）      │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│  AI agent（Trae CN 对话）介入                                          │
│  - 读取 report.json + manual_cases.md + affected_modules.json          │
│  - 对每个 manual 用例：读取 ai-prompt.md + 证据目录                      │
│  - 通过对话能力判定 pass/fail，回填到最终报告                            │
│  - V3: 审核反馈闭环建议 → 沉淀规则库/陷阱库 → 调优提示词                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 模块详细设计

#### 1.3.1 M1 模拟器控制（memu_controller.py，V2 沿用）

**职责**：封装 `memuc.exe`，提供高级 API。

**核心 API**：

```python
class MemuController:
    def __init__(self, instance_id: int = 0, memuc_path: str = MEMUC_PATH):
        ...
    
    def start(self, timeout: int = 60) -> bool:
        """启动实例，已运行则跳过。失败重试 3 次（指数退避）。"""
    
    def stop(self, timeout: int = 30) -> bool:
        """关闭实例。"""
    
    def is_running(self) -> bool:
        """查询运行状态。"""
    
    def wait_for_adb(self, timeout: int = 60) -> str:
        """等待 ADB 就绪，返回设备 serial（127.0.0.1:21503）。"""
    
    def adb(self, *args: str) -> str:
        """执行 adb 命令（通过 memuc adb -i <id>）。"""
    
    def install_app(self, apk_path: str) -> bool:
        """通过 memuc installapp 安装 APK。"""
    
    def start_app(self, package: str, activity: str | None = None) -> bool:
        """启动 App。"""
    
    def stop_app(self, package: str) -> bool:
        """强制停止 App。"""
    
    def uninstall_app(self, package: str) -> bool:
        """卸载 App。"""
```

#### 1.3.2 M2 APK 部署（apk_deployer.py，V2 沿用）

**职责**：APK 自动发现 + 校验 + 安装 + 启动 + 等待首屏。

**核心 API**：

```python
class ApkDeployer:
    PACKAGE = "io.legado.app"
    MAIN_ACTIVITY = "io.legado.app.ui.MainActivity"
    APK_GLOB_DIR = "app/build/outputs/apk/app/debug"
    
    def discover_apk(self, apk_dir: str | None = None) -> str:
        """扫描 app/build/outputs/apk/app/debug/*.apk，按 mtime 取最新。"""
    
    def validate_apk(self, apk_path: str) -> bool:
        """校验 APK：存在 + 后缀 + 大小 > 1MB。"""
    
    def install(self, apk_path: str, reinstall: bool = True) -> bool:
        """安装 APK，优先 memuc installapp，失败降级 adb install -r -d。"""
    
    def wait_for_first_frame(self, timeout: int = 30) -> bool:
        """通过 logcat 抓 'Displayed io.legado.app' 判定首屏就绪。"""
```

#### 1.3.3 M3 用例解析器（case_parser.py，V3 双轨扩展）

**职责**：把 `docs/tests/*.md` 与 `ai_tests/cases/*/case.md` 解析为结构化步骤 JSON，**V3 新增双轨调度**。

**数据模型（V3 扩展）**：

```python
from dataclasses import dataclass, field
from typing import Literal

Action = Literal["click", "input", "wait_element", "scroll", "back", "sleep", "assert"]
PreconditionType = Literal["ai_self", "user_required", "shared"]
TrackSource = Literal["md", "python", "md_python_failed"]  # V3 新增

@dataclass
class Precondition:
    raw: str
    type: PreconditionType
    resource_path: str | None = None

@dataclass
class Step:
    index: int
    raw: str
    action: Action | None = None
    target: dict = field(default_factory=dict)
    value: str | None = None

@dataclass
class Expect:
    raw: str
    type: Literal[
        "display", "no_crash", "result_contains", "rule_match",
        "db_state", "prefs_state", "activity_state", "web_api", "process_state"
    ] = "display"

@dataclass
class TestCase:
    tc_id: str                     # 如 "TC-F-P0-1-01"
    title: str
    module: str                    # 来源文件名
    category: str = ""
    preconditions: list[Precondition] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    expects: list[Expect] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    # V3 新增字段
    related_source: str | None = None       # 关联源码（如 DebugActivity.kt）
    related_activity: str | None = None     # 关联 Activity（如 DebugActivity）
    python_track_path: str | None = None   # B 轨 Python 用例路径（如存在）
    track_source: TrackSource = "md"        # 实际执行轨道
```

**双轨调度算法（V3 新增）**：

```python
class CaseParser:
    def parse_directory(self, dir_path: str) -> list[TestCase]:
        """批量解析，含双轨调度。"""
        md_cases = self._parse_md_files(dir_path)
        python_cases = self._scan_python_files(dir_path)
        # 合并：同 TC-ID 时 Python 优先
        for tc in md_cases:
            py_path = self._find_python_track(tc.tc_id, python_cases)
            if py_path:
                tc.python_track_path = py_path
                tc.track_source = "python"  # 标记将优先执行 B 轨
        return md_cases
    
    def _find_python_track(self, tc_id: str, python_cases: dict) -> str | None:
        """V3 新增：扫描 ai_tests/cases/*/auto_{tc_id}.py"""
        return python_cases.get(tc_id)
    
    def _scan_python_files(self, dir_path: str) -> dict:
        """V3 新增：扫描 B 轨 Python 用例"""
        result = {}
        for path in glob.glob(f"{dir_path}/**/auto_*.py", recursive=True):
            # auto_TC-F-P0-1-01.py → TC-F-P0-1-01
            tc_id = self._extract_tc_id_from_filename(path)
            result[tc_id] = path
        return result
```

**解析算法（V2 沿用）**：正则 + 状态机，识别 `## TC-XXX`、`**前置资源**`、`**测试步骤**`、`**预期结果**`、`**关联源码**`、`**关联 Activity**` 段。

#### 1.3.4 M4 UI 执行器（ui_executor.py，V2 沿用）

**职责**：基于 `uiautomator2` 执行原子动作。**V3：被 B 轨 Python 用例直接调用**。

**核心 API**：沿用 V2，支持 6 类原子动作（click/input/wait_element/scroll/back/sleep/assert），含自愈机制（3 次失败重启 atx-agent）。

#### 1.3.5 M5 证据收集器（evidence_collector.py，V2 沿用）

**职责**：收集 8 类非多模态证据，全部可文本化存储。

**8 类证据**：logcat 日志 / UI XML / 截图 / Activity 栈 / 数据库 / SharedPreferences / Web API / 进程内存。

**核心 API**：沿用 V2，含 `collect_all(tc_id, ui_executor) -> dict`。

#### 1.3.6 M6 规则分析器（rule_analyzer.py，V2 沿用 + V3 扩展）

**职责**：规则匹配判定 + 生成 manual 提示词，**V3 新增反馈信号输出**。

**核心 API（V3 扩展）**：

```python
class RuleAnalyzer:
    # V3 新增：可扩展的规则库
    CRASH_PATTERNS = {
        "FATAL": [r'FATAL EXCEPTION:', r'AndroidRuntime: Process:'],
        "ANR": [r'ANR in \w+', r'ANR in io\.legado\.app'],
        "CRASH": [r'CRASH:', r'signal \d+ \(SIG\w+\)'],
        "OOM": [r'OutOfMemoryError', r'java\.lang\.OutOfMemory'],
        "ClassNotFound": [r'NoClassDefFoundError', r'ClassNotFoundException'],
        "Other": [r'Exception:', r'Error:']
    }
    
    def analyze(self, test_case: TestCase, evidence: dict) -> dict:
        """4 规则串联判定 + 置信度强制规则（< 70 强制 manual）"""
        # 返回 {verdict, confidence, evidence, feedback_signal?}
    
    def _generate_ai_prompt(self, test_case, evidence, reason) -> str:
        """生成 AI agent 分析提示词"""
    
    # V3 新增
    def _emit_feedback_signal(self, test_case, evidence, verdict) -> dict | None:
        """V3 新增：manual/fail 时输出反馈闭环触发信号"""
        if verdict in ("manual", "fail"):
            return {
                "tc_id": test_case.tc_id,
                "verdict": verdict,
                "root_cause": self._extract_root_cause(evidence),
                "rule_suggestion": self._suggest_rule(evidence),
                "known_issue_suggestion": self._suggest_known_issue(evidence),
            }
        return None
```

#### 1.3.7 M7 报告生成器（report_generator.py，V2 沿用 + V3 扩展）

**职责**：Markdown + JSON + manual 三件套，**V3 新增 affected_modules.json 和 feedback_suggestions.md/.json 双版本**。

**设计决策（ADR-AD-13）**：
- **feedback_suggestions 双版本**：`.md`（人读，供 AI agent 审阅）+ `.json`（机器读，供 M16 反馈闭环回填）。tasks.md 9.7 原只要求 `.md`，实现中补充 `.json` 以支持机器消费。
- **generate_affected_modules 返回类型**：返回 JSON 字符串内容（与其他 generate_* 方法一致），不返回文件路径。保持 API 返回类型一致性。
- **summary.txt 格式**：一行摘要 `pass:N/M fail:N manual:N pass_rate:X%`，供 CLI 退出码判定和快速概览。
- **generate_json evidence_collected 容错**：evidence 中 value 非 dict 时视为未收集（collected=False），不抛 AttributeError。

**核心 API（V3 扩展，完整签名）**：

```python
class ReportGenerator:
    def __init__(self, report_dir: Optional[Path] = None):
        """初始化，report_dir 默认 REPORTS_DIR/{timestamp}/"""

    def generate_markdown(
        self, results, env, apk_info,
        affected_modules=None, feedback_signals=None
    ) -> str:
        """生成 report.md（失败用例置顶+manual 置顶+全部用例表+执行环境+V3 affected/feedback 节）
        返回: Markdown 内容字符串"""

    def generate_json(self, results, env, apk_info) -> dict:
        """生成 report.json（含 evidence_collected/ai_prompt_path/track_source/feedback_signal 字段）
        返回: report dict（可 json.dumps）
        容错: evidence 中 value 非 dict 时 collected=False"""

    def generate_manual_cases(self, results) -> str:
        """生成 manual_cases.md（manual 用例清单+AI 提示词路径+AI agent 接入流程）
        返回: Markdown 内容字符串"""

    def generate_affected_modules(self, affected: dict) -> str:
        """V3 新增：生成 affected_modules.json
        返回: JSON 字符串内容（与其他方法一致，不返回文件路径）"""

    def generate_feedback_suggestions(self, feedback_signals: list) -> str:
        """V3 新增：生成 feedback_suggestions.md（规则建议/提示词建议/陷阱库建议）
        返回: Markdown 内容字符串"""

    def generate_feedback_suggestions_json(self, feedback_signals: list) -> str:
        """V3 新增：生成 feedback_suggestions.json（机器读，供 M16 回填）
        返回: JSON 字符串内容"""

    def generate_summary(self, results) -> str:
        """生成 summary.txt（一行摘要）+ 证据归档目录 cases/{tc_id}/
        返回: 汇总统计文本（多行）"""

    def generate_all(
        self, results, env=None, apk_info=None,
        affected_modules=None, feedback_signals=None
    ) -> dict[str, str]:
        """生成完整报告套件（七件套）
        返回: {file_type: file_path} dict
        套件: report.md + report.json + manual_cases.md + summary.txt +
              affected_modules.json + feedback_suggestions.md + feedback_suggestions.json
        可选件: affected_modules / feedback_signals 为 None 时跳过"""
```

#### 1.3.8 M8 源码影响分析器（source_impact_analyzer.py）⭐ V3 新增

**职责**：基于 git diff + source_map.json，反向追踪受影响 Activity，输出复测建议。

**核心 API**：

```python
class SourceImpactAnalyzer:
    SOURCE_ROOT = "app/src/main/java/io/legado/app/"
    SOURCE_MAP_PATH = "ai_tests/lib/source_map.json"
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
    
    def analyze_diff(self, git_ref: str = "HEAD~1") -> dict:
        """主入口：分析 git diff 输出受影响模块"""
        # 1. 解析 git diff
        changed_files = self._get_changed_files(git_ref)
        if not changed_files:
            return {"changed_files": [], "affected_activities": [], 
                    "suggested_retest_tc_ids": [], "note": "no_changes"}
        
        # 2. 加载 source_map.json（缺失则首次构建）
        source_map = self._load_or_build_source_map()
        
        # 3. 反向追踪
        affected_activities = self._reverse_trace(changed_files, source_map)
        
        # 4. 查关联 TC-ID
        suggested_tc_ids = self._lookup_related_tc_ids(affected_activities, source_map)
        
        return {
            "changed_files": changed_files,
            "affected_activities": affected_activities,
            "suggested_retest_tc_ids": suggested_tc_ids,
            "unknown_bindings": source_map.get("unknown_bindings", [])
        }
    
    def _get_changed_files(self, git_ref: str) -> list[str]:
        """调 git diff --name-only <git_ref>，过滤 .kt/.java"""
        result = subprocess.run(
            ["git", "diff", "--name-only", git_ref],
            cwd=self.repo_root, capture_output=True, text=True
        )
        all_files = result.stdout.strip().split("\n")
        return [f for f in all_files if f.endswith((".kt", ".java")) 
                and "app/src/main/" in f]
    
    def _load_or_build_source_map(self) -> dict:
        """加载或首次构建 source_map.json"""
        if os.path.exists(self.SOURCE_MAP_PATH):
            with open(self.SOURCE_MAP_PATH) as f:
                return json.load(f)
        return self.build_source_map()
    
    def build_source_map(self) -> dict:
        """V3 新增：首次构建源码→UI 映射表"""
        source_map = {
            "version": "1.0",
            "built_at": datetime.now().isoformat(),
            "mappings": {},        # 文件 → {callers, ui_components, tc_ids}
            "unknown_bindings": []  # 反射/动态加载场景
        }
        
        # 1. 扫描所有 Activity
        activities = self._scan_activities()
        
        # 2. 对每个 Activity，分析其依赖
        for activity_path in activities:
            callers = self._find_callers(activity_path)
            ui_components = self._extract_ui_components(activity_path)
            tc_ids = self._lookup_tc_ids_for_activity(activity_path)
            source_map["mappings"][activity_path] = {
                "callers": callers,
                "ui_components": ui_components,
                "tc_ids": tc_ids
            }
        
        # 3. 持久化
        with open(self.SOURCE_MAP_PATH, "w") as f:
            json.dump(source_map, f, indent=2, ensure_ascii=False)
        
        return source_map
    
    def _scan_activities(self) -> list[str]:
        """扫描 app/src/main/ 下所有 Activity"""
        activities = []
        for root, _, files in os.walk(self.SOURCE_ROOT):
            for f in files:
                if f.endswith(("Activity.kt", "Activity.java", "Fragment.kt")):
                    activities.append(os.path.join(root, f))
        return activities
    
    def _find_callers(self, activity_path: str) -> list[str]:
        """反向查找：哪些文件 import/调用了此 Activity"""
        # 简化实现：grep 文件名引用
        activity_name = os.path.basename(activity_path).rsplit(".", 1)[0]
        callers = []
        for root, _, files in os.walk(self.SOURCE_ROOT):
            for f in files:
                if f.endswith((".kt", ".java")):
                    full_path = os.path.join(root, f)
                    with open(full_path, encoding="utf-8") as fp:
                        content = fp.read()
                        if activity_name in content and full_path != activity_path:
                            callers.append(os.path.relpath(full_path, self.SOURCE_ROOT))
        return callers
    
    def _extract_ui_components(self, activity_path: str) -> list[str]:
        """提取 Activity 中的 UI 组件（resource-id）"""
        with open(activity_path, encoding="utf-8") as f:
            content = f.read()
        # 正则提取 R.id.xxx
        return re.findall(r'R\.id\.(\w+)', content)
    
    def _lookup_tc_ids_for_activity(self, activity_path: str) -> list[str]:
        """查 docs/tests/*.md 和 ai_tests/cases/*/case.md 中关联此 Activity 的 TC-ID"""
        activity_name = os.path.basename(activity_path).rsplit(".", 1)[0]
        tc_ids = []
        for md_path in glob.glob("docs/tests/*.md") + glob.glob("ai_tests/cases/*/case.md"):
            with open(md_path, encoding="utf-8") as f:
                content = f.read()
                if f"**关联 Activity**：{activity_name}" in content:
                    # 提取 TC-ID
                    match = re.search(r'^##\s+(TC-[A-Z0-9\-]+)', content, re.MULTILINE)
                    if match:
                        tc_ids.append(match.group(1))
        return tc_ids
    
    def _reverse_trace(self, changed_files: list[str], source_map: dict) -> list[str]:
        """反向追踪：改动文件 → 调用方 → Activity"""
        affected = set()
        for changed in changed_files:
            rel_path = changed.replace("app/src/main/java/io/legado/app/", "")
            # 直接是 Activity
            if rel_path in source_map["mappings"]:
                affected.add(os.path.basename(rel_path).rsplit(".", 1)[0])
            # 反向查找：谁调用了我
            for src, mapping in source_map["mappings"].items():
                if rel_path in mapping.get("callers", []):
                    affected.add(os.path.basename(src).rsplit(".", 1)[0])
        return list(affected)
```

**source_map.json 结构示例**：

```json
{
  "version": "1.0",
  "built_at": "2026-07-07T15:00:00",
  "mappings": {
    "ui/association/debug/DebugActivity.kt": {
      "callers": ["ui/MainActivity.kt", "ui/association/MainMenuActivity.kt"],
      "ui_components": ["btn_encode_convert", "btn_http_test", "tv_result"],
      "tc_ids": ["TC-F-P0-1-01", "TC-F-P0-1-02", "TC-F-P0-1-03"]
    },
    "data/dao/BookSourceDao.kt": {
      "callers": ["ui/book/source/BookSourceEditActivity.kt", 
                  "ui/book/source/BookSourceListActivity.kt",
                  "ui/book/source/BookSourceViewModel.kt"],
      "ui_components": [],
      "tc_ids": ["TC-F-P0-2-01", "TC-F-P0-2-02", "TC-F-P0-2-03"]
    }
  },
  "unknown_bindings": [
    {"file": "service/BookLoader.kt", "note": "uses reflection to load BookChapter"}
  ]
}
```

**设计决策（ADR-AD-16，阶段 12 实施补充）**：

- **输出字段命名调整**：实际实现用 `related_tc_ids`（设计文档原为 `suggested_retest_tc_ids`），更简洁且与 `_lookup_related_tc_ids` 方法名一致。run_e2e.py 步骤 5.5 已同步该字段引用。
- **TC_HEADER_RE 复用陷阱**：从 `case_parser` 复用 `TC_HEADER_RE`（`r'^#{2,3}\s+(TC-...)'`），但该正则**无 `re.MULTILINE` flag**，`^` 只匹配整个字符串开头。必须**逐行 `match`** 而非 `finditer(content)` 全文扫描，否则 TC-ID 提取数为 0。此陷阱已修复并写入测试用例。
- **source_map.json 结构扁平化**：实现版采用 `{activities: {name: {callers, ui_components, tc_ids, path}}}` 扁平结构（设计文档原为 `{mappings: {path: {...}}, unknown_bindings: []}`），以 Activity 名作 key 避免 path 重复，更易 JSONPath 查询。`unknown_bindings` 字段暂未实现（V4 再补，反射场景罕见）。
- **MAX_REVERSE_TRACE_DEPTH=2**：向上追溯 2 层（Activity → 直接调用方 → 间接调用方），平衡覆盖度与误报率。超过 2 层会引入大量噪声（如 `MainActivity` 被几乎所有 Activity 引用）。
- **build_source_map 自动持久化**：扫描后立即写入 `source_map.json`，避免每次启动重建（耗时约 5-10s，56 个 Activity × grep 全源码）。`--update-source-map` CLI 参数触发强制重建。
- **实测规模**：56 个 Activity，23 个唯一调用方，39 个关联 TC-ID。`analyze_diff(HEAD~1)` 实测：54 改动文件 → 9 受影响 Activity → 15 建议复测 TC-ID。
- **简化折中**：`--diff` 与 `--tc` 互斥时优先 `--diff`，未做冲突检测；`source_map.json` 可能过时（升级路径：V4 基于 git diff 自动检测源码变化触发重建）。

#### 1.3.9 M9 源码→测试生成器（source_test_generator.py）⭐ V3 新增

**职责**：基于 Activity 源码生成 Python 测试骨架（B 轨）。

**核心 API**：

```python
class SourceTestGenerator:
    SOURCE_ROOT = "app/src/main/java/io/legado/app/"
    MANIFEST_PATH = "app/src/main/AndroidManifest.xml"
    OUTPUT_DIR = "ai_tests/cases/{module}/"
    
    def generate(self, activity_name: str, module: str = "auto") -> str:
        """
        输入：Activity 名称（如 "ImportActivity"）
        输出：生成的 Python 测试骨架路径
        """
        # 1. 定位源码
        activity_path = self._locate_activity(activity_name)
        if not activity_path:
            raise FileNotFoundError(f"Activity {activity_name} not found")
        
        # 2. 解析源码
        source_info = self._parse_activity_source(activity_path)
        
        # 3. 解析 AndroidManifest.xml
        manifest_info = self._parse_manifest()
        
        # 4. 生成 Python 骨架
        skeleton = self._render_skeleton(activity_name, source_info, manifest_info, module)
        
        # 5. 写入文件
        output_path = self.OUTPUT_DIR.format(module=module) + f"auto_TC-{activity_name}-01.py"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(skeleton)
        
        return output_path
    
    def _locate_activity(self, activity_name: str) -> str | None:
        """在 app/src/main/ 中查找 Activity 文件"""
        for root, _, files in os.walk(self.SOURCE_ROOT):
            for f in files:
                if f == f"{activity_name}.kt" or f == f"{activity_name}.java":
                    return os.path.join(root, f)
        return None
    
    def _parse_activity_source(self, activity_path: str) -> dict:
        """V3 新增：解析 Activity 源码，提取 UI 元素和跳转"""
        with open(activity_path, encoding="utf-8") as f:
            content = f.read()
        
        # 1. 提取 setContentView
        layout_match = re.search(r'setContentView\s*\(\s*R\.layout\.(\w+)', content)
        layout = layout_match.group(1) if layout_match else None
        
        # 2. 提取 findViewById（Kotlin viewBinding 或传统方式）
        view_ids = re.findall(r'findViewById\s*<\w+>\s*\(\s*R\.id\.(\w+)\s*\)', content)
        # 也支持 viewBinding
        binding_ids = re.findall(r'binding\.(\w+)', content)
        
        # 3. 提取 R.id.xxx（点击事件绑定）
        click_targets = re.findall(
            r'(\w+)\.setOnClickListener\s*\{[^}]*startActivity[^}]*Intent\s*\(\s*this\s*,\s*(\w+)::class\.java',
            content, re.DOTALL
        )
        
        # 4. 提取所有 startActivity 跳转
        activity_jumps = re.findall(
            r'startActivity\s*\(\s*Intent\s*\(\s*this\s*,\s*(\w+)::class\.java', content
        )
        
        return {
            "layout": layout,
            "view_ids": view_ids,
            "binding_ids": binding_ids,
            "click_targets": click_targets,
            "activity_jumps": activity_jumps
        }
    
    def _parse_manifest(self) -> dict:
        """V3 新增：解析 AndroidManifest.xml"""
        with open(self.MANIFEST_PATH, encoding="utf-8") as f:
            content = f.read()
        # 提取所有注册的 Activity
        activities = re.findall(r'<activity\s+android:name="\.?(\w+)"', content)
        return {"registered_activities": activities}
    
    def _render_skeleton(self, activity_name, source_info, manifest_info, module) -> str:
        """V3 新增：渲染 Python 测试骨架"""
        # 模板示例（简化）
        lines = [
            f'"""自动生成测试骨架 - {activity_name}',
            f'生成时间：{datetime.now().isoformat()}',
            f'模块：{module}',
            f'源码：app/src/main/java/io/legado/app/.../{activity_name}.kt',
            'NOTE: 此为 M9 自动生成骨架，AI 需补全 TODO 部分',
            '"""',
            '',
            'from ai_tests.lib.ui_executor import UiExecutor',
            'from ai_tests.lib.evidence_collector import EvidenceCollector',
            '',
            f'class Test{activity_name}:',
            '    PACKAGE = "io.legado.app"',
            f'    TARGET_ACTIVITY = "{activity_name}"',
            '',
            '    def setup_method(self, device):',
            '        """初始化：启动目标 Activity"""',
            '        # TODO: AI 补全启动逻辑',
            '        pass',
            '',
            '    def test_basic_flow(self, device):',
            '        """基础流程测试（M9 自动生成）"""',
        ]
        # 自动填入元素操作
        for view_id in source_info["view_ids"][:5]:  # 仅前 5 个避免过长
            lines.append(f'        # 操作元素：{view_id}')
            lines.append(f'        # device(resourceId="io.legado.app:id/{view_id}").click()')
            lines.append(f'        # TODO: 补全 {view_id} 的业务逻辑')
            lines.append('')
        # 自动填入跳转断言
        for jump in source_info["activity_jumps"][:3]:
            lines.append(f'        # 跳转断言：{jump}')
            lines.append(f'        # assert device(activity="{jump}").exists, "应跳转到 {jump}"')
            lines.append(f'        # TODO: 补全 {jump} 跳转的业务逻辑')
            lines.append('')
        lines.extend([
            '    def teardown_method(self, device):',
            '        """清理：返回首页或退出"""',
            '        # TODO: AI 补全清理逻辑',
            '        pass',
            '',
            '# === 自动生成结束，AI 在此处之上补全业务逻辑 ===',
        ])
        return '\n'.join(lines)
```

**设计决策（ADR-AD-17，阶段 13 实施补充）**：

- **文件名格式对齐 M3 规则 1**：输出文件名用 `auto_{tc_id.lower().replace('-', '_')}.py`（如 `auto_tc_f_p0_1_auto_001.py`），确保 M3 `_find_python_track` 能通过文件名规则识别。设计文档原为 `auto_TC-{activity_name}-01.py`，实际实现改为对齐 M3 命名约定。
- **@tc_id 注释兜底**：模板生成 `# @tc_id: {tc_id}` 注释（在文件头 docstring 之后），作为 M3 规则 2 的兜底（文件名不规范时仍可通过扫描前 20 行注释识别）。
- **full_activity_class 完整类名**：`am start` 命令用完整类名（`io.legado.app.ui.debug.DebugToolsActivity`），不是相对路径（`.ui.debug.DebugToolsActivity`）。原因：applicationIdSuffix 会改变 applicationId（debug → io.legado.app.debug），但不改变 Activity 类名，用完整类名避免歧义。
- **module="auto" 降级策略**：source_map.json 中无关联 TC-ID 时，模块推断为 "auto"，输出到 `ai_tests/cases/auto/`。这类用例在 M3 中会被标记为 "python_only_skipped"（缺 MD 头部信息），需 AI 后续补充 case.md。
- **Manifest 缓存**：`_parse_manifest` 首次解析后缓存结果（`_manifest_cache`），避免每次 generate 都读 XML（63 个 Activity 的解析有性能开销）。
- **_allocate_tc_id 正则修复**：原正则用大写连字符格式（`TC-{module}-auto-`），但文件名是小写下划线格式（M3 规则 1），导致匹配不到。修复为 `f"TC-{module}-auto-".lower().replace('-', '_')` 后正确匹配。
- **Jinja2 模板渲染**：用 `FileSystemLoader` + `select_autoescape([])`（不启用自动转义，因为生成 Python 代码），`keep_trailing_newline=True` 保持模板末尾换行。
- **简化折中**：viewBinding 场景仅提取 `binding.xxx` 引用名，未关联到 R.id（升级路径：V4 解析布局 XML 反查 R.id）；Compose 场景输出降级说明，提示需手动定位元素。
- **实测规模**：BookshelfManageActivity 实测提取 14 个 R.id 常量 + 1 个跳转目标，DebugToolsActivity（Compose）实测 view_ids=0（输出降级说明）。M3 `_find_python_track` 两种规则均验证通过。

#### 1.3.10 双轨用例调度机制（V3 新增）

**调度规则**：

| TC-ID 状态 | 行为 | 报告字段 |
|-----------|------|---------|
| 仅 MD | 执行 MD | `track_source: "md"` |
| 仅 Python | 不执行（缺 MD 头部信息） | `track_source: "python_only_skipped"` |
| MD + Python | 优先执行 Python | `track_source: "python"` |
| MD + Python（Python 失败） | 降级执行 MD | `track_source: "md_python_failed"` |
| 两个 MD 同 TC-ID | 报错 | `track_source: "error_duplicate"` |

**实现要点**：
```python
def dispatch_test_case(test_case: TestCase, executor: UiExecutor):
    if test_case.python_track_path:
        try:
            result = execute_python_track(test_case.python_track_path, executor)
            result.track_source = "python"
            return result
        except ImportError as e:
            # 降级执行 MD
            result = execute_md_track(test_case, executor)
            result.track_source = "md_python_failed"
            result.python_error = str(e)
            return result
    else:
        return execute_md_track(test_case, executor)
```

#### 1.3.11 反馈闭环机制（V3 新增）

**触发时机**：步骤 5.5.8，测试报告生成后

**核心 API**：

```python
class FeedbackLoop:
    def process(self, report: dict) -> dict:
        """处理测试报告，输出反馈建议"""
        suggestions = {
            "rule_suggestions": [],
            "prompt_suggestions": [],
            "known_issue_suggestions": [],
            "regression_history_entry": None
        }
        
        for case in report["cases"]:
            if case["verdict"] in ("manual", "fail"):
                # 1. 提取根因
                root_cause = self._extract_root_cause(case)
                
                # 2. 规则库扩展建议
                rule_suggestion = self._suggest_rule_extension(case, root_cause)
                if rule_suggestion:
                    suggestions["rule_suggestions"].append(rule_suggestion)
                
                # 3. 提示词调优建议
                prompt_suggestion = self._suggest_prompt_tuning(case, root_cause)
                if prompt_suggestion:
                    suggestions["prompt_suggestions"].append(prompt_suggestion)
                
                # 4. 陷阱库沉淀建议
                known_issue = self._suggest_known_issue(case, root_cause)
                if known_issue:
                    suggestions["known_issue_suggestions"].append(known_issue)
        
        # 5. 回归历史记录
        suggestions["regression_history_entry"] = {
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(report["cases"]),
            "pass": sum(1 for c in report["cases"] if c["verdict"] == "pass"),
            "fail": sum(1 for c in report["cases"] if c["verdict"] == "fail"),
            "manual": sum(1 for c in report["cases"] if c["verdict"] == "manual"),
            "manual_ratio": ...  # manual 占比
        }
        
        # 6. 写入回归历史
        self._append_regression_history(suggestions["regression_history_entry"])
        
        return suggestions
    
    def _suggest_rule_extension(self, case, root_cause) -> dict | None:
        """规则库扩展建议（不直接入库，待 AI 审核）"""
        if root_cause["type"] == "exception":
            pattern = root_cause["pattern"]
            # 检查是否已在 CRASH_PATTERNS
            if not self._is_pattern_exists(pattern):
                return {
                    "action": "add_crash_pattern",
                    "category": root_cause["category"],
                    "pattern": pattern,
                    "reason": f"用例 {case['tc_id']} 失败，根因为 {pattern}",
                    "ai_review_required": True
                }
        return None
```

#### 1.3.12 M10 编排层（run_e2e.py，V3 扩展命令）

**职责**：Layer 3 编排器，串联 M1-M9 模块，端到端执行 E2E 测试。

**核心 API**：

```python
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析 CLI 参数（基础 7 + V3 新增 4）"""

def filter_cases(cases: list, tc_filter: str) -> list:
    """--tc 筛选：all/P0/P1/模块名/TC-ID"""

def handle_v3_reserved_args(args: argparse.Namespace) -> Optional[int]:
    """V3 预留参数降级处理（M8/M9/M16 未实现时）
    Returns: None=继续执行, int=提前退出码"""

def main(argv: Optional[List[str]] = None) -> int:
    """主流程：环境校验→V3 预留参数→模拟器→u2→APK→用例→日志→
    逐用例双轨执行→证据收集→规则判定→报告生成→退出码
    Returns: 0=全过, 1=部分失败, 2=致命错误"""
```

**设计决策（ADR-AD-14，深度自分析补充）**：

- **V3 预留参数降级策略**：`--diff` 降级为 `--tc all`（继续执行），`--gen-test` 退出码 0（仅提示），`--update-source-map`/`--feedback` 仅警告（继续执行）。设计原则是"未实现不阻塞"，给出明确降级路径提示。
- **双轨调度检查点**：逐用例执行前检查 `tc.track_source`，若为 `"python"` 且 `python_track_path` 存在则优先执行 B 轨。M9 未实现时降级为 MD 执行并 warn，**不阻塞主流程**。升级路径：M9 实现后调用 `_run_python_track()` 方法。
- **feedback_signals 自动提取**：报告生成前从 `results` 中提取所有 `feedback_signal` 字段（fail/manual 时 RuleAnalyzer 输出），传给 `generate_all(feedback_signals=...)`。**修复了原实现中 feedback_suggestions.md/.json 未生成的问题**（深度自分析发现）。
- **空用例场景报告完整性**：无可执行用例时，`generate_all([])` 仍生成完整 env（含 instance_id/adb_serial/timestamp）和 apk_info（含 path），避免空报告缺执行环境信息。
- **退出码语义**：`0=全过, 1=部分失败（含 manual）, 2=致命错误`。manual 计入"部分失败"以提醒用户介入处理。
- **UiExecutor 自愈依赖**（第二轮深度优化）：`UiExecutor(device=device, memu=memu)` 必须传入 memu 参数，否则 atx-agent 卡死时无法重启（自愈机制失效）。
- **错误信息可诊断性**（第二轮深度优化）：致命错误（退出码 2）必须包含可能原因 + 预期地址/路径，降低用户排查成本。如"ADB 连接失败"附加"可能原因：端口冲突/启动慢/ADB 服务异常"+"预期 ADB 地址: 127.0.0.1:21503"。
- **日志级别可配置**（第二轮深度优化）：`-v/--verbose` 参数启用 DEBUG 级别，默认 INFO。支持子模块详细输出调试，避免默认模式下日志噪音。
- **进度百分比显示**（第二轮深度优化）：`[i/total percent%]` 格式，便于长时间测试（如 208 用例）预估剩余时间。

### 1.4 固化层 vs 持续迭代层分类（V3 新增）

详见 [README.md 1.9 节](./README.md#19-固化层-vs-持续迭代层v3-新增)。

**关键约束**：
- 固化层（lib/ 下基础设施）AI 不应修改，除非通过 OpenSpec 流程
- 持续迭代层（cases/、docs/known_issues.md 等）AI 可自由追加
- AGENTS.md 添加固化层保护规则

### 1.5 三阶段流程验证（V3 新增）

| 阶段 | 内容 | 实施任务 |
|------|------|---------|
| **A 单元层验证** | 每模块独立 mock 数据测试 | 阶段 11.1-11.3 |
| **B 端到端验证** | 14 用例全跑通（≤ 30 分钟） | 阶段 11.4-11.8 |
| **C 流程注入验证** | 让另一个 AI agent 按 V3 流程跑 /openspec | 阶段 11.9-11.10 |

**阶段 C 验证清单（7 项）**：
1. 5.5.1 源码影响分析正确执行
2. 5.5.2 APK 自动发现 + MEmu 启动
3. 5.5.3 双轨用例调度正确（同 TC-ID 时 Python 优先）
4. 5.5.4 8 类证据收集
5. 5.5.5 规则判定
6. 5.5.6 manual 用例 AI agent 介入
7. 5.5.7 三件套报告生成
8. 5.5.8 反馈闭环触发

---

## 二、Architecture Decisions（架构决策）

### 2.1 ADR 列表（V3：17 条）

| ADR | 标题 | 状态 | V 版本 |
|-----|------|------|--------|
| AD-01 | uiautomator2 选型 | Accepted | V1 |
| AD-02 | MEmu 模拟器优先 | Accepted | V1 |
| AD-03 | Python 主语言 | Accepted | V1 |
| AD-04 | 三层架构 | Accepted | V1 |
| AD-05 | 不调 LLM API | Accepted | V2 |
| AD-06 | 8 类证据收集 | Accepted | V2 |
| AD-07 | 失败不阻断 | Accepted | V2 |
| AD-08 | manual 提示词机制 | Accepted | V2 |
| AD-09 | ai_tests/ 目录 | Accepted | V2 |
| AD-10 | 子规范文档 | Accepted | V2 |
| AD-11 | APK 自动发现 | Accepted | V2 |
| AD-12 | 前置资源分类 | Accepted | V2 |
| **AD-13 V3** | **源码驱动层（Layer 0）** | Accepted | V3 |
| **AD-14 V3** | **双轨用例机制** | Accepted | V3 |
| **AD-15 V3** | **流程注入验证** | Accepted | V3 |
| **AD-16 V3** | **反馈闭环机制** | Accepted | V3 |
| **AD-17 V3** | **固化层保护** | Accepted | V3 |

### 2.2 V3 新增 ADR 详情

#### AD-13 源码驱动层（Layer 0）

- **Context**：V2 不读源码，错失非多模态环境下的精准化机会
- **Decision**：新增 Layer 0 源码驱动层，含 M8（影响分析）和 M9（测试生成）
- **Alternatives**：字节码分析、IDE 集成、LLM 分析源码（均被否决）
- **Consequences**：
  - ✅ 正面：基于源码精准定位元素、自动选复测用例
  - ❌ 负面：静态分析覆盖率 80%，反射场景需手动补充
- **Y-Statement**："In the context of 非多模态环境需要精准自动化，we chose to 新增源码驱动层接受 80% 覆盖率风险，over 字节码分析/LLM 分析，to 平衡精准度与极简，accepting 反射场景需手动补充的代价。"

#### AD-14 双轨用例机制

- **Context**：V2 单一 MD 用例对所有场景一视同仁，复杂交互无法精准化
- **Decision**：双轨制（MD + Python），同 TC-ID 时 Python 优先
- **Alternatives**：仅 MD、仅 Python、MD + Java（均被否决）
- **Consequences**：
  - ✅ 正面：复杂场景精准化，简单场景可读化
  - ❌ 负面：双轨可能产生冲突（罕见）
- **Y-Statement**："In the context of 用例机制选择，we chose to 双轨制接受 5% 冲突风险，over 单轨方案，to 兼顾可读性与精准性，accepting 调度复杂度的代价。"

#### AD-15 流程注入验证

- **Context**：V2 仅端到端跑通不等于流程跑通
- **Decision**：新增阶段 C 流程注入验证，让另一个 AI agent 按 V3 流程跑一次 /openspec
- **Alternatives**：仅端到端验证、不做验证（均被否决）
- **Consequences**：
  - ✅ 正面：流程本身被验证，发现问题更早
  - ❌ 负面：一次性成本高（让另一个 AI agent 跑一遍）
- **Y-Statement**："In the context of 流程验证，we chose to 三阶段含流程注入验证接受一次性成本，over 仅端到端验证，to 验证流程本身可被 AI agent 正确执行，accepting 一次性投入的代价。"

#### AD-16 反馈闭环机制

- **Context**：V2 无反馈机制，AI 不会越来越准
- **Decision**：失败案例沉淀规则库/陷阱库/提示词，下一轮更准
- **Alternatives**：无反馈、纯人工扩展规则（均被否决）
- **Consequences**：
  - ✅ 正面：AI 越来越准，manual 占比持续降低
  - ❌ 负面：可能引入误报（缓解：规则库扩展需 AI 审核）
- **Y-Statement**："In the context of 让 AI 越来越准，we chose to 反馈闭环接受 5% 误报风险，over 无反馈机制，to 持续降低 manual 占比，accepting 规则库扩展需 AI 审核的代价。"

#### AD-17 固化层保护

- **Context**：基础设施代码若被随意修改，会破坏稳定性
- **Decision**：lib/ 下代码 AI 不应修改，除非通过 OpenSpec 流程
- **Alternatives**：无保护、完全自由（均被否决）
- **Consequences**：
  - ✅ 正面：基础设施稳定，AI 只迭代用例和规则
  - ❌ 负面：基础设施改进需走 OpenSpec 流程
- **Y-Statement**："In the context of 基础设施稳定性，we chose to 固化层保护接受改进需走 OpenSpec 流程，over 自由修改，to 保障测试系统稳定，accepting 改进成本略高的代价。"

---

## 三、Data Flow（数据流，V3 更新）

### 3.1 主流程数据流

```
1. AI agent 触发：
   python ai_tests/run_e2e.py --apk auto --tc all --diff HEAD~1

2. 参数解析与初始化
   → argparse 解析参数
   → 创建 run_id = timestamp
   → 创建 reports/{run_id}/ 目录

3. V3 新增：源码影响分析（5.5.1）
   → M8 SourceImpactAnalyzer.analyze_diff(HEAD~1)
   → 输出 affected_modules.json
   → 若有 suggested_retest_tc_ids 且 --tc all → 全量回归覆盖
   → 若 --tc P0 → 提示需补充复测

4. APK 自动发现与部署（5.5.2）
   → ApkDeployer.discover_apk()
   → MemuController.start() / is_running()
   → MemuController.wait_for_adb()
   → ApkDeployer.install() / start_app() / wait_for_first_frame()

5. uiautomator2 初始化
   → init_device.py（首次推送 atx-agent）

6. 用例解析与双轨调度（5.5.3）
   → CaseParser.parse_directory("docs/tests/")
   → V3: 检测 ai_tests/cases/*/auto_*.py
   → 同 TC-ID 标记 track_source

7. 启动 logcat 子进程（5.5.4）
   → EvidenceCollector.start_logcat()

8. 逐用例执行（5.5.3-5.5.6）：
   for tc in test_cases:
     → 记录 start_time
     → V3: dispatch_test_case(tc, executor)
       → if tc.python_track_path:
           execute_python_track(tc.python_track_path)
           → 失败降级 execute_md_track(tc)
       → else:
           execute_md_track(tc)
     → EvidenceCollector.collect_all(tc.tc_id, ui)  # 8 类证据
     → RuleAnalyzer.analyze(tc, evidence)  # 规则判定
     → V3: RuleAnalyzer._emit_feedback_signal(tc, evidence, verdict)
     → 记录 end_time
     → 生成用例报告 + manual 提示词（如需）

9. 停止 logcat
   → EvidenceCollector.stop_logcat()

10. 报告生成（5.5.7）
    → ReportGenerator.generate_markdown()
    → ReportGenerator.generate_json()
    → ReportGenerator.generate_manual_cases()
    → V3: ReportGenerator.generate_affected_modules()
    → V3: ReportGenerator.generate_feedback_suggestions()

11. V3 新增：反馈闭环（5.5.8）
    → FeedbackLoop.process(report)
    → 输出 rule_suggestions / prompt_suggestions / known_issue_suggestions
    → 写入 regression_history.md
    → 输出 feedback_suggestions.json（待 AI agent 审核）

12. 输出 reports/{run_id}/
    → exit code（0/1/2）
```

### 3.2 反馈闭环数据流（V3 新增）

```
本轮 report.json
  ↓
FeedbackLoop.process()
  ↓
提取 manual/fail 用例
  ↓
分析根因
  ↓
┌─────────────────┬──────────────────┬─────────────────────┐
↓                 ↓                 ↓                     ↓
rule_suggestions  prompt_suggestions known_issue_suggestions regression_history
  ↓                 ↓                 ↓                     ↓
（待 AI 审核）    （待 AI 审核）    （待 AI 审核）         （直接写入）
  ↓                 ↓                 ↓
feedback_suggestions.json
  ↓
AI agent 审核
  ↓
接受 → 入库（CRASH_PATTERNS 扩展 / 模板调优 / known_issues.md 追加）
拒绝 → 记录到 regression_history.md
```

---

## 四、File Changes（文件变更，V3 更新）

### 4.1 新增文件清单（V3 完整）

```
ai_tests/
├── README.md                       # 使用指南
├── requirements.txt                # 依赖
├── config.py                       # 路径常量、超时、CRASH_PATTERNS、DB_QUERIES
├── run_e2e.py                       # 编排入口
│
├── lib/                            # 🔒 固化层（V3 保护）
│   ├── memu_controller.py          # M1
│   ├── apk_deployer.py             # M2
│   ├── case_parser.py              # M3（V3: +双轨调度）
│   ├── ui_executor.py              # M4
│   ├── evidence_collector.py       # M5
│   ├── rule_analyzer.py            # M6（V3: +反馈信号）
│   ├── report_generator.py         # M7（V3: +affected+feedback）
│   ├── source_impact_analyzer.py   # M8 ⭐ V3 新增
│   ├── source_test_generator.py    # M9 ⭐ V3 新增
│   ├── feedback_loop.py            # V3 新增：反馈闭环
│   └── source_map.json             # V3 新增：源码→UI 映射表
│
├── scripts/
│   ├── verify_env.py               # 环境自检
│   └── init_device.py              # uiautomator2 初始化
│
├── templates/
│   ├── report.md.j2                # Markdown 报告模板
│   ├── ai_prompt_template.j2       # AI 提示词模板
│   └── auto_test_template.j2       # V3 新增：M9 生成的 Python 模板
│
├── cases/                          # 🔄 持续迭代层
│   └── {module}/
│       ├── case.md                 # A 轨 MD 用例
│       ├── auto_{tc_id}.py         # B 轨 Python 用例（V3 新增）
│       └── preconditions/          # 用户必供资源
│
├── reports/                        # 测试报告（gitignore）
│   └── {run_id}/
│       ├── report.md
│       ├── report.json
│       ├── manual_cases.md
│       ├── summary.txt
│       ├── affected_modules.json   # V3 新增
│       ├── feedback_suggestions.json # V3 新增
│       └── cases/{tc_id}/
│
├── tests/                         # 单元测试
│   ├── test_memu_controller.py
│   ├── test_apk_deployer.py
│   ├── test_case_parser.py
│   ├── test_ui_executor.py
│   ├── test_evidence_collector.py
│   ├── test_rule_analyzer.py
│   ├── test_report_generator.py
│   ├── test_source_impact_analyzer.py # V3 新增
│   └── test_source_test_generator.py  # V3 新增
│
├── docs/                          # 🔄 持续迭代层
│   ├── usage.md
│   ├── troubleshooting.md
│   ├── ai_collaboration_guide.md
│   ├── source_impact_guide.md     # V3 新增
│   ├── source_test_guide.md       # V3 新增
│   ├── known_issues.md            # V3 新增（陷阱库）
│   ├── regression_history.md      # V3 新增（回归历史）
│   └── module_matrix.md           # V3 新增（模块优先级矩阵）
│
└── venv/                          # Python 虚拟环境（gitignore）
```

### 4.2 修改文件清单（V3 完整）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `docs/INDEX.md` | 修改 | 添加 spec 索引 |
| `docs/project-flow/quick-reference.md` | 修改 | 添加测试命令速查（V3 含 --diff/--gen-test/--feedback） |
| `docs/project-rules/openspec-workflow.md` | 修改 | 嵌入步骤 5.5（V3 含 8 子步骤） |
| `docs/project-rules/ai_e2e_testing_workflow.md` | 新增 | 强制流程子规范 |
| `docs/project-rules/test-case-design-guide.md` | 新增 | 测试用例设计指南（V3 双轨） |
| `AGENTS.md` | 修改 | 添加"AI 自动测试"强制规则 + 固化层保护 |
| `.gitignore` | 修改 | 添加 `ai_tests/venv/`、`ai_tests/reports/`、`ai_tests/__pycache__/`、`ai_tests/cases/*/preconditions/` |

---

## 五、Verification Plan（验证计划，V3 三阶段）

### 5.1 阶段 A：单元层验证（V2 沿用 + V3 扩展）

| 验证项 | 模块 | 验证内容 | 验证方式 |
|--------|------|---------|---------|
| E1 | M1 | 模拟器控制全流程 | start/wait/stop ≤ 60s |
| E2 | M2 | APK 自动发现+部署+启动 | 30s 内首屏渲染 |
| E3 | M3 | 14 份用例全量解析 | 无 fatal 错误 |
| E4 | M4 | UI 执行器单步 | 截图+XML 正确归档 |
| E5 | M5 | 8 类证据收集 | TC-F-P0-1-01 完整跑通 |
| E6 | M6 | 规则判定 4 路径 | pass/warning/fail/manual 准确率 ≥ 90% |
| E7 | M7 | 报告生成 | Markdown+JSON+manual 三件套正确 |
| **E8 V3** | **M8** | **源码影响分析** | **git diff → affected_modules 正确** |
| **E9 V3** | **M9** | **源码→测试生成** | **生成 Python 骨架可执行** |
| **E10 V3** | **双轨调度** | **同 TC-ID Python 优先** | **track_source 字段正确** |
| **E11 V3** | **反馈闭环** | **失败案例提取根因+建议** | **feedback_suggestions.json 正确** |

### 5.2 阶段 B：端到端验证

| 验证项 | 内容 | 验证标准 |
|--------|------|---------|
| E12 | 单用例闭环（TC-F-P0-1-01） | 8 类证据齐全，规则判定准确 |
| E13 | 全量回归（14 用例） | ≤ 30 分钟完成 |
| E14 | `--no-rules` 对照模式 | 规则判定与无规则对照正确 |
| E15 | atx-agent 卡死自愈 | 自愈成功，用例继续 |
| E16 | 模拟器异常处理 | 失败重试正确 |

### 5.3 阶段 C：流程注入验证（V3 新增）⭐

| 验证项 | 内容 | 验证标准 |
|--------|------|---------|
| **E17** | **5.5.1 源码影响分析能执行** | git diff → affected_modules 输出正确 |
| **E18** | **5.5.2-5.5.7 全流程能执行** | 自动装机+测试+报告全流程通过 |
| **E19** | **5.5.3 双轨调度正确** | 同 TC-ID 时 Python 优先执行 |
| **E20** | **manual 用例 AI agent 介入** | AI agent 能读取 ai-prompt.md 给出判定 |
| **E21** | **affected_modules 触发复测** | AI agent 能基于 affected 提示补充复测 |
| **E22** | **5.5.8 反馈闭环触发** | 失败案例 → 规则库扩展建议 → AI 审核 |
| **E23** | **流程审计报告输出** | 7 项检查全 pass，每项打分 |

**阶段 C 实施方式**：
1. 让另一个 AI agent（如 legado-workflow-auditor 或新建的测试专用 agent）按 V3 流程做一次 /openspec
2. 设计一个简单新功能 spec（如"添加测试按钮"）
3. 实施代码（仅 mock 改动，如修改 DebugActivity.kt）
4. 触发步骤 5.5
5. 按 7 项检查清单验证
6. 输出流程审计报告（pass/fail，每项打分）

---

## 六、Risks & Mitigations（风险与缓解，V3 扩展）

| 风险 | 概率 | 影响 | V3 缓解 |
|------|------|------|---------|
| MEmu 启动失败 | 低 | 高 | 重试 3 次，指数退避 |
| ADB 连接不稳定 | 中 | 中 | 轮询 + 超时 |
| atx-agent 卡死 | 中 | 中 | 重启 + 自愈 |
| run-at 在 Android 9 不可用 | 中 | 中 | 跳过 DB 证据，标记降级 |
| Web API 8080 未启动 | 中 | 低 | 跳过 Web 证据，标记降级 |
| 用例解析格式不规范 | 中 | 低 | parse_warning，不阻断 |
| **V3: source_map.json 维护成本** | 中 | 中 | M8 自动构建 + AI 追加 |
| **V3: 反射场景漏检** | 高 | 低 | unknown_bindings 标记，AI 审核 |
| **V3: Compose 解析失败** | 中 | 低 | 正则兜底，tree-sitter 可选增强 |
| **V3: 双轨冲突** | 低 | 中 | track_source 字段标记，人工审核 |
| **V3: 反馈闭环误报** | 中 | 低 | 规则扩展需 AI 审核才入库 |
| **V3: 流程注入验证成本高** | 高 | 低 | 一次性投入，后续无需重复 |

---

## 七、Open Questions（待解决问题，V3）

1. **tree-sitter-java 是否引入？** V3 设计为可选增强，实施时评估引入成本
2. **source_map.json 的反射场景如何持续维护？** 通过 unknown_bindings 标记 + AI 审核
3. **双轨用例冲突时如何处理？** track_source 字段标记 + 人工审核
4. **反馈闭环建议被拒绝后如何记录？** 写入 regression_history.md，不阻断流程
5. **流程注入验证由哪个 AI agent 执行？** 推荐用 legado-workflow-auditor 或新建测试专用 agent

---

## 八、V3 与 V2 关键差异总结

| 维度 | V2 | V3 |
|------|-----|-----|
| 模块数 | 7 | 9（+M8/M9） |
| 层数 | 3 层 | 4 层（+Layer 0） |
| 用例机制 | 单轨 MD | 双轨（MD+Python） |
| 源码利用 | 不读 | M8 影响分析 + M9 测试生成 |
| 流程验证 | 端到端 | 三阶段（含流程注入验证） |
| 反馈机制 | 无 | 反馈闭环（规则库/陷阱库/提示词） |
| ADR 数 | 12 | 17（+5） |
| 任务阶段 | 17 | 22（+5） |
| 子任务数 | 128 | 165（+37） |
| 持续迭代机制 | 无 | 固化层 vs 迭代层分类 |
