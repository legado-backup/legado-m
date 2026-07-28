# ai_tests 组件能力清单（Components Capability Inventory）

> **生成时间**：2026-07-26
> **范围**：`f:\myself\github\WeAgentChat\temp\legado\ai_tests\` 目录下全部脚本与组件
> **目的**：归纳总结通用组件能力，供 AI agent 与开发者复用
> **约束**：仅输出技术字段（类名/函数名/路径常量/退出码/异常类型），URL 路径模式化为 `/path/{id}`，不引用业务字段（sourceName/sourceUrl/title 等）

---

## 一、目录结构总览

```
ai_tests/
├── README.md                    # 入口文档（5 分钟上手 + V3 双轨调度说明）
├── config.py                    # 全局配置常量（路径/超时/崩溃模式/DB 查询模板）
├── run_e2e.py                   # 编排层主入口（端到端测试流程）
├── requirements.txt             # Python 依赖清单
├── lib/                         # 核心库（10 个模块，固化层）
│   ├── memu_controller.py       # M1 模拟器控制
│   ├── apk_deployer.py          # M2 APK 部署
│   ├── case_parser.py           # M3 用例解析（V3 双轨调度）
│   ├── ui_executor.py           # M4 UI 执行器
│   ├── evidence_collector.py    # M5 证据收集器（8 类证据并行）
│   ├── rule_analyzer.py         # M6 规则分析器（4 规则串联）
│   ├── report_generator.py      # M7 报告生成器（七件套）
│   ├── source_impact_analyzer.py # M8 源码影响分析器（V3）
│   ├── source_test_generator.py # M9 源码→测试生成器（V3）
│   ├── feedback_loop.py         # M16 反馈闭环（V3）
│   └── source_map.json          # Activity 静态调用图（M8 输出）
├── scripts/                     # 操作脚本（34 个，按用途分类）
├── cases/                       # V3 双轨用例（MD + auto_*.py）
├── templates/                   # Jinja2 模板（report.md.j2 等）
├── testdata/                    # 测试数据（RSS 搜索/登录测试 JSON）
├── tests/                       # 单元测试（test_*.py，10 个）
└── docs/                        # 文档目录（known_issues/regression_history 等）
```

### 架构分层

```
Layer 3: 编排层（run_e2e.py）
  ↓
Layer 2: 用例与执行层
  M3 CaseParser → M4 UiExecutor → M5 EvidenceCollector
  ↓
Layer 1: 基础设施层
  M1 MemuController → M2 ApkDeployer → M6 RuleAnalyzer → M7 ReportGenerator
  ↓
Layer 0: 源码驱动层（V3）
  M8 SourceImpactAnalyzer → M9 SourceTestGenerator → M16 FeedbackLoop
```

---

## 二、全局配置层（config.py）

**职责**：定义全局常量，所有组件复用，禁止硬编码。

| 类别 | 字段 | 默认值 | 用途 |
|------|------|--------|------|
| **模拟器** | `MEMUC_PATH` | `D:\Program Files\Microvirt\MEmu\memuc.exe` | MEmu 控制台路径 |
|  | `ADB_PATH` | `D:\Program Files\Microvirt\MEmu\adb.exe` | ADB 工具路径 |
|  | `MEMU_INSTANCE_ID` | `0` | MEmu 实例 ID |
|  | `MEMU_ADB_HOST` | `127.0.0.1:21503`（支持环境变量覆盖） | ADB 连接地址 |
| **应用** | `BUILD_TYPE` | `debug` | 构建类型（debug/release） |
|  | `PACKAGE` | `io.legado.miss.app.debug` | 包名（基于 BUILD_TYPE 自动拼接） |
|  | `MAIN_ACTIVITY` | `io.legado.app.ui.welcome.WelcomeActivity` | 主入口 Activity |
| **路径** | `APK_GLOB_DIR` | `app/build/outputs/apk/app/debug` | APK 自动发现目录 |
|  | `SOURCE_ROOT` | `app/src/main/java/io/legado/app` | 源码根（M8/M9 输入） |
|  | `ANDROID_MANIFEST` | `app/src/main/AndroidManifest.xml` | 清单文件 |
|  | `SOURCE_MAP_PATH` | `ai_tests/lib/source_map.json` | 静态调用图持久化 |
|  | `REPORTS_DIR` | `ai_tests/reports` | 报告输出根 |
| **超时** | `TIMEOUT_MEMU_START` | `60s` | 模拟器启动超时 |
|  | `TIMEOUT_APK_INSTALL` | `120s` | APK 安装超时 |
|  | `TIMEOUT_UI_OPERATION` | `30s` | UI 操作超时 |
|  | `TIMEOUT_FIRST_FRAME` | `30s` | 首屏渲染超时 |
|  | `SCROLL_SEARCH_MAX` | `5` | 滚动查找最大次数 |
| **崩溃模式** | `CRASH_PATTERNS` | 6 类（FATAL/ANR/CRASH/OOM/ClassNotFound/Other） | logcat 异常识别正则 |
| **DB 查询** | `DB_QUERIES` | 3 模块（F-P0-2/F-P0-3/F-P0-4） | 数据库状态查询 SQL |
| **证据类型** | `EVIDENCE_TYPES` | 8 类 | logcat/ui_xml/screenshot/activity_stack/db_state/prefs_state/web_api/meminfo |
| **V3 配置** | `DUAL_TRACK_PYTHON_PRIORITY` | `True` | 双轨调度 Python 优先 |
|  | `DUAL_TRACK_FALLBACK_TO_MD` | `True` | Python 失败降级 MD |

**安全约束**：固化层文件，AI 不应直接修改，必须通过 OpenSpec 流程。

---

## 三、编排层（run_e2e.py）

**职责**：端到端测试编排，串联 M1-M16 全部模块。

**核心流程**：
1. 解析 CLI 参数（`--apk` / `--tc` / `--diff` / `--gen-test` / `--feedback`）
2. V3 参数处理（降级模式：未实现模块仅提示）
3. 初始化模拟器（M1）+ 部署 APK（M2）
4. 初始化 uiautomator2（atx-agent 自动推送）
5. 解析用例（M3 双轨调度：Python 优先 MD）
6. 执行测试（M4 UI 执行 + M5 证据收集，带自愈机制）
7. 规则判定（M6 4 规则串联 + 置信度强制）
8. 报告生成（M7 七件套）

**退出码**：
- `0`：全部通过
- `1`：部分失败（有 fail 或 manual）
- `2`：致命错误（环境/APK/模拟器故障）

---

## 四、lib/ 核心库详解（10 个模块）

### M1 MemuController（模拟器控制）

**文件**：`lib/memu_controller.py`
**职责**：MEmu 实例生命周期 + ADB 命令封装 + App 生命周期
**依赖**：`subprocess`（标准库）+ `config.py`

| API | 功能 | 返回 |
|-----|------|------|
| `start(timeout)` | 启动 MEmu 实例（重试 3 次指数退避） | `bool` |
| `stop(timeout)` | 停止 MEmu 实例 | `bool` |
| `is_running()` | 检查运行状态 | `bool` |
| `wait_for_adb(timeout)` | 等待 ADB 连接就绪 | `Optional[str]` (serial) |
| `adb(*args, timeout)` | 通用 ADB 命令 | `(rc, stdout, stderr)` |
| `install_app(apk_path)` | 安装 APK（memuc 优先） | `bool` |
| `start_app(package, activity)` | 启动 App | `bool` |
| `stop_app(package)` | 停止 App（`am force-stop`） | `bool` |
| `uninstall_app(package)` | 卸载 App | `bool` |

**自检**：正常用例（实例化）+ 边界用例（不存在实例 ID）+ 异常用例（memuc 路径错误抛 `FileNotFoundError`）。

### M2 ApkDeployer（APK 部署）

**文件**：`lib/apk_deployer.py`
**职责**：APK 自动发现 + 校验 + 安装 + 启动 + 等待首屏
**依赖**：M1 MemuController

| API | 功能 | 返回 |
|-----|------|------|
| `discover_apk(apk_dir)` | 自动发现最新 APK（按 mtime） | `Optional[str]` |
| `validate_apk(apk_path)` | 校验 APK（存在 + .apk + >1MB） | `bool` |
| `install(apk_path)` | 安装（memuc 优先，失败降级 `adb install -r -d`） | `bool` |
| `uninstall(package)` | 卸载 | `bool` |
| `clear_data(package)` | 清除数据（`pm clear`） | `bool` |
| `start_app(package, activity)` | 启动 App | `bool` |
| `wait_for_first_frame(timeout)` | 等待首屏（logcat "Displayed" 关键字） | `bool` |
| `deploy(apk_path)` | 一键部署（发现+校验+安装+启动+等待） | `bool` |

### M3 CaseParser（用例解析器，V3 双轨调度）

**文件**：`lib/case_parser.py`
**职责**：解析 MD 用例为结构化 TestCase + V3 双轨调度（Python 优先 MD）
**支持格式**：`## TC-XXX：标题` / `### TC-XXX：标题`（中英文冒号兼容）

**数据模型**：
- `Step`：`action`（click/input/wait_element/scroll/back/sleep/assert）+ `target` + `value`
- `Expect`：`expect_type`（8 种：page_jump/element_visible/text_match/no_crash/log_clean/db_state/prefs_state/web_api/manual）
- `Precondition`：`resource_type`（AI自备/用户必供/共享）+ `description`
- `TestCase`：含 V3 字段 `related_source` / `related_activity` / `python_track_path` / `track_source`

| API | 功能 | 返回 |
|-----|------|------|
| `parse_file(path)` | 解析单个 MD 文件 | `List[TestCase]` |
| `parse_directory(dir_path)` | 批量解析目录 | `List[TestCase]` |
| `parse_all()` | 合并解析 `docs/tests/` + `ai_tests/cases/` | `List[TestCase]` |
| `_find_python_track(tc_id, module)` | V3 查找 B 轨 Python 用例（文件名匹配 + `@tc_id` 注释匹配） | `Optional[str]` |
| `dispatch_test_case(tc)` | V3 双轨调度（Python 优先 MD） | `"python"` / `"md"` |

**容错**：`parse_warnings` 记录格式不规范但不阻断。

### M4 UiExecutor（UI 执行器）

**文件**：`lib/ui_executor.py`
**职责**：封装 uiautomator2 操作 + 4 种元素定位 + 自愈机制
**依赖**：`uiautomator2>=3.2.0` + M1 MemuController + M3 Step

**4 种元素定位**（支持显式前缀 + 启发式）：
- `resource-id=xxx` / `text=xxx` / `xpath=xxx` / `desc=xxx`
- 启发式：含中文 → text（回退 desc），含 `//` → xpath，纯英文 → text（回退 resourceId）

| API | 功能 | 返回 |
|-----|------|------|
| `click(target, timeout, scroll_search)` | 点击（含滚动查找） | `bool` |
| `input_text(target, value, timeout)` | 输入文本（先 click 聚焦再 set_text） | `bool` |
| `wait_element(target, timeout)` | 等待元素出现 | `bool` |
| `scroll(direction)` | 滑动（up/down/left/right） | `bool` |
| `press_back()` | 返回键 | `bool` |
| `sleep(seconds)` | 等待 | `bool` |
| `dump_hierarchy()` | 获取 UI XML | `str` |
| `screenshot()` | 截图 | `Optional[bytes]` |
| `execute_step(step, screenshot_dir, xml_dir, step_index)` | 完整步骤执行（前置证据→动作→后置证据） | `Dict[str, Any]` |
| `execute_step_with_heal(step, ...)` | 带自愈机制（3 次重试 + App 重启） | `Dict[str, Any]` |

**自愈机制**：
- 失败后检测 App 状态（`_detect_app_state`）：normal/crashed/not_running
- App 正常 → 元素未找到，直接重试
- App 崩溃 → `_restart_app()` 重启后重试
- 最多 3 次尝试，3 次失败标记步骤失败

**阻塞屏幕处理**（`dismiss_dialogs`）：隐私协议 / 帮助文档 / 设置本地密码 / 权限请求，循环最多 5 次避免死循环。Preference 条目误判排除（`_is_preference_item`）。

### M5 EvidenceCollector（证据收集器，8 类并行）

**文件**：`lib/evidence_collector.py`
**职责**：8 类证据并行收集 + 降级标记 + 异常提取
**依赖**：`subprocess` + `concurrent.futures` + M1 MemuController + `config.CRASH_PATTERNS`

| 证据类型 | API | 收集方式 | 降级标记 |
|---------|-----|---------|---------|
| logcat | `start_logcat` / `stop_logcat` / `slice_logcat` / `extract_anomalies` | `adb logcat -d -v time` 切片 | - |
| ui_xml | `collect_ui_xml` | 汇总 UiExecutor 已保存的 XML | - |
| screenshot | `collect_screenshot` | 汇总截图文件 | - |
| activity_stack | `collect_activity_stack` | `dumpsys activity top` | - |
| db_state | `collect_db_state` | `run-at sqlite3` 查询 DB_QUERIES | `run_at_unavailable`（debuggable=false） |
| prefs_state | `collect_prefs_state` | `run-at cat shared_prefs/*.xml` | `run_at_unavailable` |
| web_api | `collect_web_api` | `curl localhost:8080` | `web_api_unavailable` / `curl_unavailable` / `web_api_timeout` |
| meminfo | `collect_meminfo` | `dumpsys meminfo {package}` | - |
| **统一入口** | `collect_all(tc_id, tc_dir, ...)` | ThreadPoolExecutor 5 并发 | 汇总降级统计 |

**异常提取**（`extract_anomalies`）：识别 6 类异常（FATAL/ANR/CRASH/OOM/ClassNotFound/Other），**排除 uiautomator2 框架崩溃**（`UiAutomationService already registered` 等不误判为 App 崩溃）。

### M6 RuleAnalyzer（规则分析器，4 规则串联）

**文件**：`lib/rule_analyzer.py`
**职责**：4 规则串联判定 + 置信度强制 + V3 反馈信号生成
**依赖**：`config.CRASH_PATTERNS` + M3 TestCase/Expect

**判定流程**：
1. 规则 1 `_rule_fatal_crash`：logcat 异常含 FATAL/CRASH/ANR → `fail`（confidence=95）
2. 规则 2 `_rule_exception_warning`：异常含 Exception/Error 但非 Fatal → `warning`（confidence=80）
3. 规则 3 `_rule_pass_with_evidence`：无异常 + 8 种预期与证据匹配 → `pass`（confidence=85）
4. 规则 4 `_rule_manual_insufficient`：证据不足 → `manual`（confidence=50）
5. **置信度强制**：`< 70` 强制 `manual`（保留 `original_verdict`）
6. V3：`fail`/`manual` 时输出 `feedback_signal`（供 M16 消费）

**预期匹配规则**（`_check_expect_match`）：
- `manual` → 不自动 pass
- `no_crash` → logcat 无致命异常
- `log_clean` → logcat 无任何异常
- `page_jump` → activity_stack 已收集
- `element_visible` / `text_match` → ui_xml 已收集
- `db_state` / `prefs_state` / `web_api` → 证据已收集（降级也算匹配）

**输出**：含 `ai_prompt`（manual 用例的 AI 判定提示词，保存到 `reports/manual_cases/{tc_id}_ai-prompt.md`）。

### M7 ReportGenerator（报告生成器，七件套）

**文件**：`lib/report_generator.py`
**职责**：Jinja2 模板渲染 + 七件套统一入口
**依赖**：`Jinja2` + `json`（标准库）

| API | 功能 | 输出文件 |
|-----|------|---------|
| `generate_markdown(results, env, apk_info, ...)` | Markdown 报告（失败置顶 + manual 置顶 + 全部用例表 + V3 affected/feedback 节） | `report.md` |
| `generate_json(results, env, apk_info)` | JSON 报告（含 evidence_collected/ai_prompt_path/track_source 字段） | `report.json` |
| `generate_manual_cases(results)` | Manual 用例清单 + AI agent 接入流程 | `manual_cases.md` |
| `generate_affected_modules(affected)` | V3 受影响模块 | `affected_modules.json` |
| `generate_feedback_suggestions(feedback_signals)` | V3 反馈建议（人读） | `feedback_suggestions.md` |
| `generate_feedback_suggestions_json(feedback_signals)` | V3 反馈建议（机器读，M16 回填） | `feedback_suggestions.json` |
| `generate_summary(results)` | 一行摘要 + 汇总统计 + 证据归档目录 | `summary.txt` |
| `generate_all(results, env, apk_info, ...)` | **统一入口**（七件套） | dict[file_type, file_path] |

**模板路径**：`ai_tests/templates/report.md.j2`（Jinja2，`trim_blocks=True` + `lstrip_blocks=True`）。

### M8 SourceImpactAnalyzer（源码影响分析器，V3 新增）

**文件**：`lib/source_impact_analyzer.py`
**职责**：git diff 反向追溯受影响 Activity + 查关联 TC-ID + 输出建议复测
**依赖**：`subprocess`（git）+ `pathlib` + `re` + `source_map.json`（静态调用图）

| API | 功能 | 返回 |
|-----|------|------|
| `analyze_diff(git_ref)` | 主入口（git diff → 受影响 Activity → 关联 TC-ID） | `Dict` |
| `build_source_map()` | 构建 source_map（扫描所有 *Activity.kt + 关联 TC-ID） | `Dict` |
| `_load_or_build_source_map()` | 加载或重建 source_map | `Dict` |
| `_find_callers(activity_class_name)` | grep 文件名引用找调用方（粗粒度静态调用图） | `List[str]` |
| `_extract_ui_components(source_content)` | 提取 UI 组件（R.id.xxx / setContentView / Compose setContent） | `List[str]` |
| `_reverse_trace(changed_files, source_map)` | 改动文件 → 调用方 Activity（向上追溯 MAX_REVERSE_TRACE_DEPTH=2 层） | `List[str]` |
| `_lookup_related_tc_ids(affected_activities, source_map)` | 受影响 Activity → 关联 TC-ID | `List[str]` |
| `_scan_tc_ids_for_activity(activity_class_name)` | 扫描用例 MD 找关联此 Activity 的 TC-ID | `List[str]` |
| `get_source_map_summary()` | 获取 source_map 摘要（不重建） | `Dict` |

**数据流**：`git diff --name-only <git_ref>` → `_reverse_trace` 向上追溯 2 层 → `_lookup_related_tc_ids` 查 source_map → 输出 `recommended_rerun`。

**输出**：`{changed_files, affected_activities, related_tc_ids, recommended_rerun, git_ref, analyzed_at}`。

### M9 SourceTestGenerator（源码→测试生成器，V3 新增）

**文件**：`lib/source_test_generator.py`
**职责**：基于 Activity 源码静态分析，生成 Python 测试骨架（B 轨）
**依赖**：`Jinja2` + `re` + `config.py`（SOURCE_ROOT / ANDROID_MANIFEST / AI_TESTS_CASES_DIR）

| API | 功能 | 返回 |
|-----|------|------|
| `generate(activity_name, module)` | 主入口（为 Activity 生成 Python 测试骨架） | `str`（输出文件路径） |
| `_locate_activity(activity_name)` | 在 source_root 下递归查找 .kt / .java | `Optional[Path]` |
| `_parse_activity_source(activity_path)` | 解析源码（layout / view_ids / binding_ids / click_targets / activity_jumps） | `dict` |
| `_parse_manifest()` | 解析 AndroidManifest.xml 提取已注册 Activity（懒加载缓存） | `dict` |
| `_render_skeleton(...)` | Jinja2 模板渲染（auto_test_template.j2） | `str` |
| `_allocate_tc_id(module)` | TC-ID 自动分配（基于现有最大编号 +1，格式 `TC-{module}-auto-{NNN}`） | `str` |
| `_infer_module(activity_name)` | 从 source_map.json 推断 Activity 所属模块 | `str` |

**输出路径**：`ai_tests/cases/{module}/auto_{tc_id_lower_with_underscores}.py`（遵循 M3 `_find_python_track` 规则 1）。

### M16 FeedbackLoop（反馈闭环，V3 新增）

**文件**：`lib/feedback_loop.py`
**职责**：消费测试报告，输出 4 类反馈建议 + 自动追加陷阱库/回归历史
**依赖**：`config.CRASH_PATTERNS`（只读）+ `config.PROJECT_ROOT`

| API | 功能 | 返回 |
|-----|------|------|
| `process(report)` | 主入口（消费 report.json） | `Dict` 含 4 类建议 |
| `_extract_root_cause(case)` | 提取根因（两阶段：精确匹配 CRASH_PATTERNS → 通用异常正则 `\w+(Exception|Error)`） | `Dict` |
| `_suggest_rule_extension(case, root_cause)` | 规则库扩展建议（仅未被覆盖的新异常） | `Optional[Dict]` |
| `_suggest_prompt_tuning(case, root_cause)` | 提示词调优建议（仅 manual 用例） | `Optional[Dict]` |
| `_suggest_known_issue(case, root_cause)` | 陷阱库沉淀建议 | `Dict` |
| `_build_regression_entry(report)` | 构建回归历史条目（含失败模式 Top3） | `Dict` |
| `_append_regression_history(entry)` | 追加到 `regression_history.md`（不存在则创建表头） | `None` |
| `_append_known_issue(issue)` | 追加到 `known_issues.md`（不存在则创建表头） | `None` |

**4 类反馈建议**：
1. `rule_suggestions` — 规则库扩展（写入 CRASH_PATTERNS，需 AI 审核）
2. `prompt_suggestions` — 提示词调优（调优 ai_prompt_template.j2，需 AI 审核）
3. `known_issue_suggestions` — 陷阱库沉淀（直接追加到 known_issues.md）
4. `regression_history_entry` — 回归历史（直接追加到 regression_history.md）

**设计决策（ADR-AD-16）**：`process(report)` 单参数，`feedback_signal` 已内嵌 `report.cases[]`。

---

## 五、scripts/ 脚本分类（34 个）

### 5.1 设备管理类（4 个）

| 脚本 | 功能 | 用法 | 退出码 |
|------|------|------|--------|
| `init_device.py` | uiautomator2 设备初始化（atx-agent 自动推送 + 参数配置 + 检测运行） | 提供 `init_uiautomator2(memu, serial, retry)` 工具函数 | - |
| `verify_env.py` | 环境自检（MEmu/ADB/Python/磁盘空间/APK 目录/源码根） | `python ai_tests/scripts/verify_env.py` | 0=PASS / 1=FAIL |
| `quick_dns_check.py` | DNS 可达性对比测试（脚本侧 vs 真机侧，7 个失败源） | `python ai_tests/scripts/quick_dns_check.py` | - |
| `quick_build_install.py` | 快速编译 + 安装 + L1 验证（步骤1编译→步骤2启动MEmu→步骤3安装→L1验证） | `python ai_tests/scripts/quick_build_install.py` | 0/1/2 |

### 5.2 UI 自动化类（7 个）

| 脚本 | 功能 | 安全约束 |
|------|------|---------|
| `dump_ui_safe.py` | 安全 dump UI 结构（过滤 text 属性，只输出 resource-id/class/bounds/clickable） | 不输出业务文本 |
| `dump_ui_safe_v2.py` | v2（支持指定设备，过滤 text/content-desc） | 同上 |
| `parse_ui_safe.py` | 解析 UI XML（源名替换为源[N]，只输出技术字段+中心点坐标） | 源名→源[N] |
| `ui_explorer.py` | UI 探索辅助（解析 XML，输出 text/desc/rid/bounds/class） | 用于导航探索 |
| `nav_helper.py` | 视频播放器导航辅助（全程脱敏，只输出编号） | 源名→编号 |
| `l2_verify_video_player.py` | 视频播放器 L2 验证（8 场景：swipe_article/pagination/preload/position_memory/backward_compat/buffer_progress/control_visibility/error_patterns/all） | 推荐 error_patterns 场景（永久日志验证 4 个修复点 0 错误） |
| `l2_verify_rss_search.py` | 订阅源统一搜索 L2 验证（5 场景：launch_search/results_display/open_article/change_source/crash_check/all） | 全程脱敏，源用编号 |

### 5.3 测试用例管理类（2 个）

| 脚本 | 功能 | 输出 |
|------|------|------|
| `gen_module_matrix.py` | 核心模块矩阵报告生成器（扫描用例 + 复用 CaseParser + 按模块统计覆盖率） | `ai_tests/docs/module_matrix.md` |
| `swipe_test_log.py` | SwipeTest + VideoGesture 临时日志抓取分析（clear/capture/analyze 三子命令） | `tmp_swipetest_log.txt` |

**`gen_module_matrix.py` 关键能力**：
- 扫描 `docs/tests/*.md` + `ai_tests/cases/*/*.md`（跳过 README.md / _index.md）
- 复用 CaseParser 解析（不重复造轮子）
- 按模块统计：用例数 / 关联源码覆盖率 / 关联 Activity 覆盖率 / 缺失项清单
- 退出码：0=全覆盖 / 1=部分缺失 / 2=无用例
- 内置自检程序（`--self-test`，3 类用例：正常/边界/异常）

### 5.4 数据注入类（3 个）

| 脚本 | 功能 | 去重逻辑 | WAL 处理 |
|------|------|---------|---------|
| `import_book_source.py` | 导入书源（默认 10 个，避免校验时间过长） | `INSERT OR REPLACE`（按 bookSourceUrl） | 删除 WAL/SHM 避免覆盖 |
| `import_rss_source.py` | 导入订阅源（基础版，按 sourceUrl 单字段去重） | `DELETE WHERE sourceUrl=?` | 拉取+清理+回写 |
| `import_rss_source_v5.py` | V5 专用（按 sourceUrl + sourceName 组合去重，保留同 URL 不同名称的子源） | `DELETE WHERE sourceUrl=? AND sourceName=?` | 同上 + 自动检测 ADB 设备 |

**关键陷阱**（项目记忆铁证）：
- `import_rss_source.py` chown 硬编码 `u0_a0:u0_a0` 是 BUG，正式包 uid=10065(u0_a65) / 测试包 uid=10064(u0_a64) / 共存包 uid 不同，导入后必须手动 chown 到目标包实际 uid 否则抛 `SQLiteCantOpenDatabaseException`
- V5 组合去重原因：聚合/导航拆分子源共享父站 sourceUrl 但 sourceName 不同（按分类区分），原脚本按 sourceUrl 单字段去重会损失 47 个子源

### 5.5 数据库查询类（8 个）

| 脚本 | 功能 | 技术字段 | 业务字段过滤 |
|------|------|---------|-------------|
| `query_image_source.py` | 查询 articleStyle=2 图片源（pull DB + sqlite3 查询） | url_prefix(前30字符) / type / articleStyle / ruleContent_len / ruleImage_len / ruleTitle_len / enabled | ✅ |
| `query_image_source_safe.py` | 安全查询图片源（run-as cat，避免 shell 转义） | 同上 | ✅ |
| `query_image_source_v2.py` | v2（stdin 传 SQL 给 sqlite3，避免 shell 转义） | 同上 | ✅ |
| `query_image_source_v3.py` | v3（run-as + base64 读取 DB，sourceUrl 用 hash 替代显示） | sourceUrl_hash / type / articleStyle / 规则长度 | ✅ |
| `query_image_source_v4.py` | v4（查询表结构 + 读取 WAL 文件，支持环境变量 DEVICE） | 表结构 + WAL 内容 | ✅ |
| `query_notnull.py` | 查询 rssArticles NOT NULL 列（PRAGMA table_info） | 列名 / 类型 / NOT NULL / default | - |
| `query_schema.py` | 查询 rssArticles 表结构 | 列名 / 类型 | - |
| `verify_db.py` | 验证模拟器 DB 中订阅源数量（按 type 分组统计） | total / web / img / vid / enabled 计数 | ✅ |

### 5.6 图片源诊断类（3 个）

| 脚本 | 功能 | 输出 |
|------|------|------|
| `find_image_source.py` | 查询图片类型订阅源（articleStyle=2）的位置索引 | 源[N] 位置 |
| `inject_image_source.py` | 修改 DB：把第一个源改成 articleStyle=2 + 插入 rssArticles 记录 + push 回设备 | - |
| `match_image_source.py` | 匹配 UI 中的图片源分类（不输出业务文本，只输出位置+长度+是否图片源） | UI 位置 + 长度 |

### 5.7 V5 订阅源批量优化类（6 个）

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `v5_classification_scan.py` | V4 订阅源分类扫描（229 源） | optimized_v2_lite_final_v4.json | v5_classification.json（脱敏分类结果） |
| `v5_cf_breakthrough.py` | V5 CF 盾源 4 个破盾突破（5 大技术：headful+反检测 / cookie 注入 / 等待 30s / google cache / httpx 禁用 TLS+HTTP 降级） | optimized_v5_final.json | v5_cf_breakthrough.json |
| `v5_video_breakthrough.py` | V5 视频源 88 个深度突破（6 大突破手段，Playwright sync_api） | optimized_v5_final.json | v5_video_breakthrough.json |
| `v5_spa_breakthrough.py` | V5 SPA 站点外链提取突破（3 个 SPA 站点，5 大技术：滚动触发懒加载 / Vue/React props 提取 / 扫描 window 对象 / 扫描 script JSON / 提取可见链接） | optimized_v5_final.json | v5_spa_breakthrough.json |
| `v5_hard_source_fix.py` | 67 个难点源深度处理（CF 盾 / 登录源 / 弹框源 / enabled=false 恢复） | optimized_v2_lite_final_v4.json + v5_classification.json | v5_hard_source_fix.json |
| `v5_missing_fields_fix.py` | 135 个缺字段源深度补全（Playwright mobile_context + 去弹框 JS + DOM 结构检测） | 同上 | v5_missing_fields_fix.json |

**统一脱敏规范**：
- URL → `http://[DOMAIN]/path`（路径前 30-50 字符）
- 业务名 → `源[idx]`
- IP → `[IP]`
- cookie/token → `***`

### 5.8 验证类（2 个）

| 脚本 | 功能 | 场景 |
|------|------|------|
| `verify_thread_pool_split.py` | 线程池拆分配置 E2E 验证（书源线程池：searchThreadCount + updateCacheThreadCount） | ui_display / set_search / set_update_cache / restore_default / all |
| `verify_db.py` | 验证模拟器 DB 中订阅源数量（按 type 分组：web/img/vid） | - |

---

## 六、组件依赖关系图

### 6.1 lib/ 内部依赖

```
M1 MemuController（基础，无依赖）
  ↓
M2 ApkDeployer（依赖 M1）
  ↓
M4 UiExecutor（依赖 M1 + M3 Step）
  ↓
M5 EvidenceCollector（依赖 M1 + config.CRASH_PATTERNS）

M3 CaseParser（依赖 config）
  ↓
M6 RuleAnalyzer（依赖 M3 TestCase/Expect + config.CRASH_PATTERNS）
  ↓
M7 ReportGenerator（依赖 Jinja2）

M8 SourceImpactAnalyzer（依赖 source_map.json + M3 TC_HEADER_RE）
  ↓
M9 SourceTestGenerator（依赖 M8 source_map.json + Jinja2 + config）

M16 FeedbackLoop（依赖 config.CRASH_PATTERNS + config.PROJECT_ROOT）
```

### 6.2 scripts/ 对 lib/ 的依赖

| 脚本 | 依赖的 lib 模块 |
|------|----------------|
| `init_device.py` | M1 MemuController + config |
| `quick_build_install.py` | config（直接 import） |
| `l2_verify_video_player.py` | swipe_test_log + config + uiautomator2（可选） |
| `l2_verify_rss_search.py` | config + uiautomator2（可选） |
| `gen_module_matrix.py` | M3 CaseParser + config |
| `verify_env.py` | config |
| `verify_thread_pool_split.py` | config + adb |
| `import_*` 系列 | config（部分直接硬编码 ADB_PATH） |
| `query_image_source_v3/v4.py` | 直接硬编码 ADB_PATH |
| `nav_helper.py` | config + uiautomator2 |
| V5 系列 | Playwright sync_api（独立运行，不依赖 lib） |

### 6.3 数据流

```
用户执行 run_e2e.py
  ↓
M1 启动模拟器 → M2 部署 APK → init_device.py 初始化 uiautomator2
  ↓
M3 解析用例（docs/tests/*.md + ai_tests/cases/*/*.md）
  ↓ V3 双轨调度
M4 执行步骤（带自愈） → M5 并行收集 8 类证据
  ↓
M6 规则判定（4 规则串联 + 置信度强制）
  ↓
M7 生成七件套报告
  ↓
M16 反馈闭环（消费 report.json → 4 类建议 + 陷阱库/回归历史追加）
```

---

## 七、通用组件能力清单（按类别归纳）

### 7.1 设备管理能力

| 能力 | 提供者 | API/脚本 |
|------|--------|---------|
| MEmu 启停 | M1 | `start` / `stop` / `is_running` |
| ADB 命令执行 | M1 | `adb(*args, timeout)` |
| ADB 连接等待 | M1 | `wait_for_adb(timeout)` |
| App 生命周期 | M1 | `install_app` / `start_app` / `stop_app` / `uninstall_app` |
| APK 自动发现 | M2 | `discover_apk(apk_dir)` |
| APK 校验 | M2 | `validate_apk(apk_path)` |
| 一键部署 | M2 | `deploy(apk_path)` |
| 环境自检 | scripts | `verify_env.py` |
| uiautomator2 初始化 | scripts | `init_device.py` 的 `init_uiautomator2(memu, serial, retry)` |
| DNS 可达性测试 | scripts | `quick_dns_check.py` |

### 7.2 UI 自动化能力

| 能力 | 提供者 | API/脚本 |
|------|--------|---------|
| 4 种元素定位 | M4 | resource-id / text / xpath / desc（含启发式） |
| 点击（含滚动查找） | M4 | `click(target, timeout, scroll_search)` |
| 文本输入 | M4 | `input_text(target, value, timeout)` |
| 等待元素 | M4 | `wait_element(target, timeout)` |
| 滑动 | M4 | `scroll(direction)` |
| 返回键 | M4 | `press_back()` |
| UI XML dump | M4 / scripts | `dump_hierarchy()` / `dump_ui_safe*.py` |
| 截图 | M4 | `screenshot()` |
| 步骤执行（前置证据→动作→后置证据） | M4 | `execute_step(step, screenshot_dir, xml_dir, step_index)` |
| 自愈机制（3 次重试 + App 重启） | M4 | `execute_step_with_heal(...)` |
| 阻塞屏幕关闭 | M4 | `dismiss_dialogs()`（隐私协议/帮助文档/设置本地密码/权限请求） |
| 安全 UI dump（过滤业务文本） | scripts | `dump_ui_safe.py` / `dump_ui_safe_v2.py` / `parse_ui_safe.py` |
| UI 探索辅助 | scripts | `ui_explorer.py` |
| 视频播放器导航 | scripts | `nav_helper.py` |

### 7.3 测试用例管理能力

| 能力 | 提供者 | API/脚本 |
|------|--------|---------|
| MD 用例解析（V3 双轨调度） | M3 | `parse_file` / `parse_directory` / `parse_all` |
| V3 双轨调度（Python 优先 MD） | M3 | `dispatch_test_case(tc)` → `"python"` / `"md"` |
| V3 关联源码/Activity 解析 | M3 | `related_source` / `related_activity` 字段 |
| 步骤语义化（关键词→Action） | M3 | `_classify_action(step_text)` |
| 预期类型识别（8 种） | M3 | `_classify_expect(expect_text)` |
| 模块矩阵报告 | scripts | `gen_module_matrix.py` |
| SwipeTest 日志抓取分析 | scripts | `swipe_test_log.py`（clear/capture/analyze） |

### 7.4 数据注入能力

| 能力 | 提供者 | API/脚本 | 去重逻辑 |
|------|--------|---------|---------|
| 书源导入 | scripts | `import_book_source.py` | INSERT OR REPLACE（按 bookSourceUrl） |
| 订阅源导入（基础） | scripts | `import_rss_source.py` | DELETE WHERE sourceUrl=? |
| 订阅源导入（V5 组合去重） | scripts | `import_rss_source_v5.py` | DELETE WHERE sourceUrl=? AND sourceName=? |
| DB 修改+回写 | scripts | `inject_image_source.py` | - |

### 7.5 数据库查询能力

| 能力 | 提供者 | API/脚本 | 安全约束 |
|------|--------|---------|---------|
| 拉取 DB（含 WAL） | scripts | `pull_db()` | 清理本地 WAL/SHM 避免 malformed |
| 回写 DB（清理 WAL/SHM） | scripts | `push_db()` | 删除设备 WAL/SHM 避免覆盖 |
| articleStyle=2 图片源查询 | scripts | `query_image_source*.py`（5 个版本） | 只输出技术字段 |
| 表结构查询 | scripts | `query_schema.py` / `query_notnull.py` | - |
| DB 计数验证 | scripts | `verify_db.py` | 按 type 分组统计 |

### 7.6 证据收集能力

| 能力 | 提供者 | API | 降级标记 |
|------|--------|-----|---------|
| logcat 启停+切片+异常提取 | M5 | `start_logcat` / `stop_logcat` / `slice_logcat` / `extract_anomalies` | - |
| ui_xml 汇总 | M5 | `collect_ui_xml(tc_dir, ui)` | - |
| screenshot 汇总 | M5 | `collect_screenshot(tc_dir, ui)` | - |
| activity_stack 收集 | M5 | `collect_activity_stack(tc_dir)` | - |
| db_state 收集（run-at sqlite3） | M5 | `collect_db_state(tc_dir, queries)` | `run_at_unavailable` |
| prefs_state 收集（run-at cat） | M5 | `collect_prefs_state(tc_dir)` | `run_at_unavailable` |
| web_api 收集（curl localhost:8080） | M5 | `collect_web_api(tc_dir, endpoints)` | `web_api_unavailable` / `curl_unavailable` / `web_api_timeout` |
| meminfo 收集 | M5 | `collect_meminfo(tc_dir)` | - |
| 8 类并行收集 | M5 | `collect_all(tc_id, tc_dir, ...)` | ThreadPoolExecutor 5 并发 |
| uiautomator2 框架崩溃排除 | M5 | `_is_uiautomator2_crash(block_text)` | 不误判为 App 崩溃 |

### 7.7 验证能力

| 能力 | 提供者 | 场景 |
|------|--------|------|
| L1 基础验证（App 启动） | scripts | `quick_build_install.py` |
| L2 视频播放器验证 | scripts | `l2_verify_video_player.py`（8 场景，推荐 error_patterns） |
| L2 订阅源搜索验证 | scripts | `l2_verify_rss_search.py`（5 场景） |
| 线程池拆分配置验证 | scripts | `verify_thread_pool_split.py`（4 场景） |
| 环境自检 | scripts | `verify_env.py` |
| DB 验证 | scripts | `verify_db.py` |

### 7.8 报告生成能力

| 能力 | 提供者 | 输出文件 |
|------|--------|---------|
| Markdown 报告 | M7 | `report.md` |
| JSON 报告（含 evidence_collected/ai_prompt_path/track_source） | M7 | `report.json` |
| Manual 用例清单 + AI agent 接入流程 | M7 | `manual_cases.md` |
| V3 受影响模块 | M7 | `affected_modules.json` |
| V3 反馈建议（人读） | M7 | `feedback_suggestions.md` |
| V3 反馈建议（机器读，M16 回填） | M7 | `feedback_suggestions.json` |
| 一行摘要 + 证据归档目录 | M7 | `summary.txt` |
| 七件套统一入口 | M7 | `generate_all(results, env, apk_info, ...)` |

### 7.9 源码分析能力

| 能力 | 提供者 | API |
|------|--------|-----|
| git diff 改动文件分析 | M8 | `_git_diff_name_only(git_ref)` |
| Activity 静态调用图构建 | M8 | `build_source_map()` |
| 调用方查找（grep 类名引用） | M8 | `_find_callers(activity_class_name)` |
| UI 组件提取（R.id/setContentView/Compose） | M8 | `_extract_ui_components(source_content)` |
| 反向追溯（改动文件→受影响 Activity，2 层） | M8 | `_reverse_trace(changed_files, source_map)` |
| 关联 TC-ID 查询 | M8 | `_lookup_related_tc_ids(affected_activities, source_map)` |
| 主入口（git diff → 受影响 Activity → 关联 TC-ID） | M8 | `analyze_diff(git_ref)` |

### 7.10 测试生成能力

| 能力 | 提供者 | API |
|------|--------|-----|
| Activity 源码定位 | M9 | `_locate_activity(activity_name)` |
| 源码解析（layout/view_ids/binding_ids/click_targets/activity_jumps） | M9 | `_parse_activity_source(activity_path)` |
| AndroidManifest 解析 | M9 | `_parse_manifest()` |
| Python 测试骨架渲染（Jinja2） | M9 | `_render_skeleton(...)` |
| TC-ID 自动分配（基于现有最大编号 +1） | M9 | `_allocate_tc_id(module)` |
| 模块自动推断（基于 source_map） | M9 | `_infer_module(activity_name)` |
| 主入口（为 Activity 生成 Python 测试骨架） | M9 | `generate(activity_name, module)` |

### 7.11 反馈闭环能力

| 能力 | 提供者 | API |
|------|--------|-----|
| 报告消费（4 类反馈建议） | M16 | `process(report)` |
| 根因提取（两阶段：精确匹配 CRASH_PATTERNS → 通用异常正则） | M16 | `_extract_root_cause(case)` |
| 规则库扩展建议（仅未覆盖的新异常） | M16 | `_suggest_rule_extension(case, root_cause)` |
| 提示词调优建议（仅 manual 用例） | M16 | `_suggest_prompt_tuning(case, root_cause)` |
| 陷阱库沉淀建议 | M16 | `_suggest_known_issue(case, root_cause)` |
| 回归历史条目构建 | M16 | `_build_regression_entry(report)` |
| 陷阱库自动追加（known_issues.md） | M16 | `_append_known_issue(issue)` |
| 回归历史自动追加（regression_history.md） | M16 | `_append_regression_history(entry)` |

### 7.12 V5 订阅源批量优化能力

| 能力 | 提供者 | 脚本 |
|------|--------|------|
| 订阅源分类扫描（229 源） | scripts | `v5_classification_scan.py` |
| CF 盾破盾（5 大技术） | scripts | `v5_cf_breakthrough.py` |
| 视频源深度突破（6 大手段） | scripts | `v5_video_breakthrough.py` |
| SPA 站点外链提取（5 大技术） | scripts | `v5_spa_breakthrough.py` |
| 难点源处理（CF 盾/登录/弹框/enabled 恢复） | scripts | `v5_hard_source_fix.py` |
| 缺字段源补全（Playwright + 去弹框 JS + DOM 检测） | scripts | `v5_missing_fields_fix.py` |

---

## 八、使用规范与约束

### 8.1 执行环境

- **Python**：3.12 + 虚拟环境 `ai_tests/venv/`（禁止公共 Python）
- **模拟器**：MEmu（`D:\Program Files\Microvirt\MEmu\`）
- **ADB 设备**：默认 `127.0.0.1:21503`（实例 0），支持环境变量 `MEMU_ADB_HOST` 覆盖
- **包名规范**：
  - 测试包：`io.legado.miss.app.debug`（代码优化开发真机测试必用）
  - 正式包：`io.legado.miss.app.release`（Skill 真机测试必用）
  - 共存包：`io.legado.app.debug`（与原版共存场景）

### 8.2 输出安全约束

| 约束 | 处理方式 |
|------|---------|
| 源名称 | 替换为 `源[N]` |
| 域名 | 替换为 `站点A/B/C` 或 `[DOMAIN]` |
| URL | 路径模式化为 `http://[DOMAIN]/path` |
| cookie/token/password/key/secret/auth | 完全隐藏 `***` |
| 设备 ID/用户 ID/IP/邮箱/手机号 | 脱敏 |
| IP | 替换为 `[IP]` |
| 业务字段（sourceName/sourceUrl/title/name/summary/description） | 禁止 Grep 搜索，改搜技术字段（id/type/ruleImage/函数名） |
| logcat 原始日志 | 只输出错误码/异常类型/调用栈，不输出含域名/cookie 的原始行 |

### 8.3 固化层约束

**固化层文件**（AI 不应直接修改，必须通过 OpenSpec 流程）：
- `config.py`
- `lib/memu_controller.py`
- `lib/apk_deployer.py`
- `lib/case_parser.py`
- `lib/ui_executor.py`
- `lib/evidence_collector.py`

**持续迭代层**（AI 可扩展）：
- `config.CRASH_PATTERNS`：基于失败案例扩展
- `config.DB_QUERIES`：基于源码 Dao 扩展

### 8.4 Grep 搜索规范

| 禁止搜索（业务字段） | 允许搜索（技术字段） |
|---------------------|---------------------|
| sourceName / sourceUrl / sortUrl / sourceComment | ruleImage / coverDecodeJs / ruleReview |
| title / name / summary / description | id / type / sort / customOrder / enabled |
| （源 JSON/DB 中） | 函数名 / 类名 / 字段名 |

### 8.5 logcat 处理规范

- 用 Grep 过滤技术关键词（自定义 tag 如 SwipeTest/HighlightRefresh、Exception/Error/FATAL），`head_limit<=20`
- 只输出技术结论（错误码/异常类型/调用栈/数量统计）
- 禁止输出含域名/cookie/源名称/分类名称的原始日志行
- cookie 只记录长度和是否成功，不引用内容

---

## 九、自检与验证机制

### 9.1 模块自检（`if __name__ == "__main__"`）

每个 lib 模块均含自检程序，覆盖 3 类用例（正常/边界/异常）：

| 模块 | 自检覆盖 |
|------|---------|
| M5 EvidenceCollector | 正常（实例化）+ 边界（memu=None 抛 ValueError）+ 异常1（空文本返回空列表）+ 异常2（uiautomator2 框架崩溃被排除）+ 正常3（App 崩溃被保留） |
| M6 RuleAnalyzer | 边界（空证据判定 manual） |
| M7 ReportGenerator | 边界（空 results 时汇总为 0） |
| M8 SourceImpactAnalyzer | 1.构建 source_map + 2.analyze_diff（命令行参数） |
| M9 SourceTestGenerator | 1.模板存在性 + 2.Manifest 解析 + 3.单 Activity 生成 |
| M16 FeedbackLoop | 正常（mock report）+ 边界（空 cases）+ 异常（缺字段不崩溃） |
| `gen_module_matrix.py` | 正常/边界/异常 3 类用例 |

### 9.2 单元测试（`tests/` 目录，10 个）

| 测试文件 | 覆盖模块 |
|---------|---------|
| `test_case_parser.py` | M3 |
| `test_evidence_collector.py` | M5 |
| `test_feedback_loop.py` | M16 |
| `test_memu_controller.py` | M1 |
| `test_report_generator.py` | M7 |
| `test_rule_analyzer.py` | M6 |
| `test_run_e2e.py` | run_e2e.py |
| `test_source_impact_analyzer.py` | M8 |
| `test_source_test_generator.py` | M9 |
| `test_ui_executor.py` | M4 |

### 9.3 退出码规范

| 退出码 | 含义 | 适用脚本 |
|--------|------|---------|
| `0` | 全部通过 / 全覆盖 | run_e2e.py / verify_env.py / gen_module_matrix.py / quick_build_install.py |
| `1` | 部分失败 / 部分缺失 | 同上 + l2_verify_*.py |
| `2` | 致命错误 / 无用例 | run_e2e.py / verify_env.py / gen_module_matrix.py / l2_verify_*.py |

---

## 十、文档维护

- **更新触发**：新增组件 / 修改 API / 新增脚本时必须同步更新本文档
- **更新方式**：基于真实代码分析（不基于记忆），禁止仅文字合并已有条目
- **版本同步**：与 `README.md` / `INDEX.md` 保持一致
- **关联文档**：
  - 设计文档：`docs/specs/e2e-automated-testing/design.md`
  - 任务清单：`docs/specs/e2e-automated-testing/tasks.md`
  - 固定测试流程 SOP：`ai_tests/docs/fixed_test_workflow.md`
  - 已知问题陷阱库：`ai_tests/docs/known_issues.md`
  - 回归历史：`ai_tests/docs/regression_history.md`
  - 模块矩阵：`ai_tests/docs/module_matrix.md`

---

**文档结束**
