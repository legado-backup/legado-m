# tasks.md — Legado AI 自动化测试基础设施（V3）

> **状态**：🔄 设计中（V3，基于用户深度反馈再次重构）
> **创建日期**：2026-07-07
> **V2 调整日期**：2026-07-07
> **V3 调整日期**：2026-07-07
> **执行原则**：按阶段顺序执行，每子任务完成后验证并标记 ⚠️（代码完成）/ ✅（验证通过）
> **V3 核心调整**：新增 M8 源码影响分析器、M9 源码→测试生成器、双轨用例、流程注入验证（阶段 C）、反馈闭环五大能力

---

## 任务总览（V3）

| 阶段 | 模块 | 任务数 | V3 变化 |
|------|------|--------|---------|
| 1. 环境准备 | - | 7 | +tree-sitter-java 可选依赖 |
| 2. M1 模拟器控制 | memu_controller.py | 10 | V2 沿用 |
| 3. M2 APK 部署 | apk_deployer.py | 8 | V2 沿用 |
| 4. uiautomator2 初始化 | init_device.py | 6 | V2 沿用 |
| 5. M3 用例解析器 | case_parser.py | 10 | V3 +双轨调度+源码溯源字段 |
| 6. M4 UI 执行器 | ui_executor.py | 11 | V2 沿用 |
| 7. M5 证据收集器 | evidence_collector.py | 12 | V2 沿用 |
| 8. M6 规则分析器 | rule_analyzer.py | 9 | V3 +反馈信号 emit |
| 9. M7 报告生成器 | report_generator.py | 9 | V3 +affected_modules+feedback |
| 10. 编排层 | run_e2e.py | 10 | V3 +--diff/--gen-test/--feedback |
| 11. 端到端验证 A+B | - | 10 | V2 沿用（阶段 A+B） |
| 12. M8 源码影响分析器 ⭐ | source_impact_analyzer.py | 9 | **V3 新增** |
| 13. M9 源码→测试生成器 ⭐ | source_test_generator.py | 9 | **V3 新增** |
| 14. 双轨用例与三波覆盖 ⭐ | - | 5 | **V3 新增** |
| 15. 流程注入验证（阶段 C） ⭐ | - | 6 | **V3 新增** |
| 16. 反馈闭环 ⭐ | feedback_loop.py | 7 | **V3 新增** |
| 17. 子规范 S13 | ai_e2e_testing_workflow.md | 5 | V3 扩展（5.5.1/5.5.8） |
| 18. 子规范 S14 | test-case-design-guide.md | 6 | V3 扩展（双轨+源码溯源） |
| 19. V3 子规范 S18/S19 | source_impact_guide.md + source_test_guide.md | 4 | **V3 新增** |
| 20. V3 子规范 S20/S21 | known_issues.md + regression_history.md | 3 | **V3 新增** |
| 21. 修改 OpenSpec + AGENTS.md | - | 7 | V3 +固化层保护规则 |
| 22. AI 协作指南 + 文档同步 | - | 5 | V3 +反馈闭环说明 |
| **合计** | - | **165** | - |

---

## 1. 环境准备与依赖管理

- [ ] 1.1 创建 `ai_tests/` 目录结构（lib/、templates/、scripts/、tests/、docs/、cases/、cases/*/preconditions/）
- [ ] 1.2 创建 `ai_tests/requirements.txt`（uiautomator2≥3.2.0、adbutils、Jinja2、loguru、pydantic；可选：tree-sitter-java≥0.20）
- [ ] 1.3 创建 Python 虚拟环境 `ai_tests/venv/`（Python 3.12）+ 安装依赖
- [ ] 1.4 编写 `ai_tests/scripts/verify_env.py`：自检 MEmu 路径、ADB、Python 版本、磁盘空间、APK 打包目录、源码根
- [ ] 1.5 运行 `verify_env.py` 验证环境就绪 → **验证：所有检查项 PASS**
- [ ] 1.6 在项目根 `.gitignore` 追加：`ai_tests/venv/`、`ai_tests/reports/`、`ai_tests/__pycache__/`、`ai_tests/cases/*/preconditions/`、`ai_tests/lib/source_map.json.bak`
- [ ] 1.7 编写 `ai_tests/config.py`：路径常量（MEMUC_PATH、ADB_PATH、PACKAGE、MAIN_ACTIVITY、APK_GLOB_DIR、SOURCE_ROOT、SOURCE_MAP_PATH）、超时、CRASH_PATTERNS、DB_QUERIES

## 2. M1 模拟器控制模块

- [ ] 2.1 编写 `ai_tests/lib/memu_controller.py`：MemuController 类骨架
- [ ] 2.2 实现 `start(timeout=60)`：调 `memuc start -i 0`，重试 3 次指数退避
- [ ] 2.3 实现 `stop(timeout=30)`：调 `memuc stop -i 0`
- [ ] 2.4 实现 `is_running()` → bool：调 `memuc isvmrunning -i 0`，解析输出
- [ ] 2.5 实现 `wait_for_adb(timeout=60)` → str：轮询 `memuc adb -i 0 get-state`，返回 serial
- [ ] 2.6 实现 `adb(*args)` → str：通用 ADB 命令封装
- [ ] 2.7 实现 `install_app(apk_path)` → bool：调 `memuc installapp -i 0 <apk>`
- [ ] 2.8 实现 `start_app(package, activity)` / `stop_app(package)` / `uninstall_app(package)`
- [ ] 2.9 编写单元测试 `ai_tests/tests/test_memu_controller.py`：mock subprocess，验证命令构造正确
- [ ] 2.10 实测验证：启动 MEmu 实例 0 → 等待 ADB → 关闭 → **验证：全流程 ≤ 60s**

## 3. M2 APK 部署模块

- [ ] 3.1 编写 `ai_tests/lib/apk_deployer.py`：ApkDeployer 类骨架（含 APK_GLOB_DIR 常量）
- [ ] 3.2 实现 `discover_apk(apk_dir=None)` → str：扫描 `app/build/outputs/apk/app/debug/*.apk` 按 mtime 取最新
- [ ] 3.3 实现 `validate_apk(apk_path)` → bool：文件存在 + `.apk` 后缀 + 大小 > 1MB
- [ ] 3.4 实现 `install(apk_path)`：优先 `memuc installapp`，失败降级 `adb install -r -d`
- [ ] 3.5 实现 `uninstall()` / `clear_data()`：清理旧版与数据
- [ ] 3.6 实现 `start_app()`：调 `memuc startapp -i 0 io.legado.app/.ui.MainActivity`
- [ ] 3.7 实现 `wait_for_first_frame(timeout=30)` → bool：抓 logcat `Displayed io.legado.app`
- [ ] 3.8 实测验证：用 `--apk auto` 自动发现最新 APK 完整部署 → **验证：App 首屏 30s 内渲染**

## 4. uiautomator2 设备初始化

- [ ] 4.1 编写 `ai_tests/scripts/init_device.py`：首次推送 atx-agent + uiautomator2-test.apk
- [ ] 4.2 实测 `u2.connect("127.0.0.1:21503")`，验证 MEmu x86_64 兼容性
- [ ] 4.3 实现 `init_uiautomator2(memu)` 工具函数：返回 device 对象
- [ ] 4.4 配置 device 参数：`implicitly_wait(10)`、`operation_timeout=30`、`operation_delay=(0.5, 0.5)`
- [ ] 4.5 实现 `is_uiautomator2_ready(memu)` → bool：检测 atx-agent 是否运行
- [ ] 4.6 实测验证：dump_hierarchy + screenshot 基本功能可用 → **验证：返回有效 XML + PNG**

## 5. M3 用例解析器（V3 扩展双轨调度）

- [ ] 5.1 编写 `ai_tests/lib/case_parser.py`：CaseParser 类 + 数据模型（TestCase/Step/Expect/Precondition，V3 新增 `python_track_path`/`track_source`/`related_source`/`related_activity` 字段）
- [ ] 5.2 编写正则：TC_HEADER_RE / SECTION_RE（含"前置资源"+"关联源码"+"关联 Activity"段）/ STEP_RE / EXPECT_RE / PRECOND_RE
- [ ] 5.3 实现 `parse_file(path)` → list[TestCase]：单文件解析（状态机扫描行）
- [ ] 5.4 实现 `parse_directory(dir_path)` → list[TestCase]：批量解析（合并 `docs/tests/` + `ai_tests/cases/`）
- [ ] 5.5 实现步骤语义化：关键词映射到 Action（点击→click、输入→input、等待→wait_element、滑动→scroll、返回→back、观察→assert）
- [ ] 5.6 实现前置资源识别（`[AI自备]` / `[用户必供]` / `[共享]` 三类）+ 预期类型识别（8 种）
- [ ] 5.7 V3 新增：实现 `_find_python_track(tc_id, module)` → str|None：扫描 `ai_tests/cases/{module}/auto_*.py` 寻找同 TC-ID 的 B 轨用例
- [ ] 5.8 V3 新增：实现双轨调度 `dispatch_test_case(tc)` → str：同 TC-ID 时 Python 优先于 MD，返回实际执行轨道（"python"/"md"）
- [ ] 5.9 实现容错：格式不规范时 `parse_warnings`，不阻断；前置资源缺失时 `missing_precondition`，跳过用例
- [ ] 5.10 编写 `ai_tests/tests/test_case_parser.py`：单元测试（含 V3 双轨调度场景）+ 实测验证：解析 `docs/tests/` 全部 14 份文件 → **验证：TC-ID 正确，双轨调度正确，无 fatal**

## 6. M4 UI 执行器

- [ ] 6.1 编写 `ai_tests/lib/ui_executor.py`：UiExecutor 类骨架
- [ ] 6.2 实现 `click(target)`：支持 resource-id/text/xpath/description 四种定位
- [ ] 6.3 实现 `input_text(target, value)`：clear + input
- [ ] 6.4 实现 `wait_element(target, timeout)`：等待元素出现
- [ ] 6.5 实现 `scroll(direction)`：上下左右四方向
- [ ] 6.6 实现 `press_back()` / `sleep(seconds)`
- [ ] 6.7 实现 `dump_hierarchy()` → str / `screenshot()` → bytes
- [ ] 6.8 实现 `execute_step(step, screenshot_dir, xml_dir)` → dict：完整步骤执行（前置截图+XML → 动作 → 后置截图+XML）
- [ ] 6.9 实现超时保护：单步 30s 超时
- [ ] 6.10 实现自愈机制：失败重试 1 次 → 重启 atx-agent → 3 次失败标记步骤失败
- [ ] 6.11 实测验证：执行 TC-F-P0-1-01 第 1 步"进入我的" → **验证：截图+XML 正确归档**

## 7. M5 证据收集器（8 类证据）

- [ ] 7.1 编写 `ai_tests/lib/evidence_collector.py`：EvidenceCollector 类骨架
- [ ] 7.2 定义 `CRASH_PATTERNS`：FATAL/ANR/CRASH/OOM/ClassNotFound/Other 六类
- [ ] 7.3 定义 `DB_QUERIES` 模板：按用例模块映射 SQL（F-P0-2 查 book_sources、F-P0-3 查 cover_gallery_groups 等）
- [ ] 7.4 实现证据 1：`start_logcat()` / `stop_logcat()` / `slice_logcat(start, end)` / `extract_anomalies(log_text)`
- [ ] 7.5 实现证据 2：`collect_ui_xml(tc_dir, ui)` 汇总 UI XML
- [ ] 7.6 实现证据 3：`collect_screenshot(tc_dir, ui)` 截图（每步自动收集，此处汇总）
- [ ] 7.7 实现证据 4：`collect_activity_stack(tc_dir)` 调 `dumpsys activity top`
- [ ] 7.8 实现证据 5：`collect_db_state(tc_dir, queries)` 调 `run-at io.legado.app sqlite3`
- [ ] 7.9 实现证据 6：`collect_prefs_state(tc_dir)` 调 `cat shared_prefs/*.xml`
- [ ] 7.10 实现证据 7：`collect_web_api(tc_dir, endpoints)` 调 `curl localhost:8080`
- [ ] 7.11 实现证据 8：`collect_meminfo(tc_dir)` 调 `dumpsys meminfo io.legado.app`
- [ ] 7.12 实现 `collect_all(tc_id, ui)` → dict：8 类证据并行收集（5/6/7 并发），含降级标记（run_at_unavailable / web_api_unavailable）

## 8. M6 规则分析器（V3 扩展反馈信号）

- [ ] 8.1 编写 `ai_tests/lib/rule_analyzer.py`：RuleAnalyzer 类骨架（不依赖任何 LLM SDK）
- [ ] 8.2 实现 `_rule_fatal_crash(log_slice, anomalies)` → dict|None：规则 1，FATAL/CRASH/ANR → fail, confidence=95
- [ ] 8.3 实现 `_rule_exception_warning(log_slice, anomalies)` → dict|None：规则 2，Exception/Error → warning, confidence=80
- [ ] 8.4 实现 `_rule_pass_with_evidence(test_case, evidence)` → dict|None：规则 3，基于 8 类证据判定 8 种预期类型匹配 → pass, confidence=85
- [ ] 8.5 实现 `_rule_manual_insufficient(test_case, evidence)` → dict：规则 4，证据不足 → manual, confidence=50
- [ ] 8.6 实现 `_generate_ai_prompt(test_case, evidence, reason)` → str：生成 `ai-prompt.md` 提示词（含证据摘要+判定引导）
- [ ] 8.7 实现 `analyze(test_case, evidence)` → dict：4 规则串联判定 + 置信度强制规则（< 70 强制 manual）
- [ ] 8.8 V3 新增：实现 `_emit_feedback_signal(verdict, test_case, evidence)` → dict：失败/manual 时输出 `feedback_signal`（含 failure_pattern / suggested_rule / suggested_prompt），供 M16 反馈闭环消费
- [ ] 8.9 编写 `ai_tests/tests/test_rule_analyzer.py` + 实测验证：4 种 verdict 路径 + manual 时 ai-prompt.md 生成 + V3 失败时 feedback_signal 输出 → **验证：verdict 准确率 ≥ 90%**

## 9. M7 报告生成器（V3 扩展 affected + feedback）

- [ ] 9.1 编写 `ai_tests/lib/report_generator.py`：ReportGenerator 类骨架
- [ ] 9.2 编写 `ai_tests/templates/report.md.j2`：Markdown 报告 Jinja2 模板（含失败用例置顶+manual 用例置顶+全部用例表+执行环境+V3 affected_modules 节）
- [ ] 9.3 编写 `ai_tests/templates/ai_prompt_template.j2`：AI 提示词 Jinja2 模板
- [ ] 9.4 实现 `generate_markdown(results, env, apk_info)` → str + `generate_json(results, env, apk_info)` → dict（含 evidence_collected/ai_prompt_path/track_source 字段）
- [ ] 9.5 实现 `generate_manual_cases(results)` → str：生成 manual_cases.md（含 manual 用例清单 + AI 提示词路径 + AI agent 接入流程）
- [ ] 9.6 V3 新增：实现 `generate_affected_modules(affected)` → str：生成 `affected_modules.json`（含 changed_files/affected_activities/related_tc_ids/recommended_rerun 字段）
- [ ] 9.7 V3 新增：实现 `generate_feedback_suggestions(feedback_signals)` → str：生成 `feedback_suggestions.md`（含规则建议/提示词建议/陷阱库建议，供 AI agent 审阅并沉淀到 M16）
- [ ] 9.8 实现 `generate_summary(results)` → str + 证据归档：每用例独立目录 `cases/{tc_id}/`，8 类证据全归档
- [ ] 9.9 实测验证：mock 一组结果数据（含 pass/fail/manual 各一 + V3 含 affected + feedback）→ **验证：Markdown + JSON + manual_cases.md + affected_modules.json + feedback_suggestions.md 五件套渲染正确**

## 10. 编排层（run_e2e.py，V3 扩展命令）

- [ ] 10.1 编写 `ai_tests/run_e2e.py`：CLI 参数解析（argparse）
- [ ] 10.2 实现参数：`--apk`（默认 auto）、`--tc`（默认 all）、`--report-dir`、`--no-rules`、`--keep-device`、`--instance-id`、`--init-device`
- [ ] 10.3 V3 新增：实现参数 `--diff <git_ref>`（默认 HEAD~1）：触发 M8 源码影响分析，自动选复测用例（与 `--tc` 互斥时优先 `--diff`）
- [ ] 10.4 V3 新增：实现参数 `--gen-test <Activity>`：触发 M9 为指定 Activity 生成 Python 测试骨架
- [ ] 10.5 V3 新增：实现参数 `--update-source-map`：触发 M8 重建 `source_map.json` + `--feedback`：触发 M16 反馈闭环处理
- [ ] 10.6 实现 `--tc` 筛选逻辑：`all` / `P0` / `P1` / `F-P0-1`（模块名）/ `TC-XXX`（单用例 ID）+ V3 双轨调度（Python 优先）
- [ ] 10.7 实现合并 `docs/tests/` + `ai_tests/cases/` 用例 + 前置资源检查（user_required 缺失则跳过）
- [ ] 10.8 实现主流程：环境校验 → V3 源码影响分析（如 `--diff`）→ 自动发现 APK → 启动模拟器 → init u2 → 部署 APK → 解析用例 → 启动日志 → 逐用例双轨执行（8 类证据+规则判定+反馈信号）→ 停止日志 → 生成报告（五件套）→ V3 反馈闭环（如 `--feedback`）
- [ ] 10.9 实现失败不阻断 + 退出码：全过=0，部分失败=1，致命错误=2
- [ ] 10.10 编写 `ai_tests/README.md`：使用指南（5 分钟上手，含 `--apk auto --tc all` + V3 `--diff HEAD~1` + `--gen-test` + `--feedback` 示例）

## 11. 端到端验证（阶段 A 单元层 + 阶段 B 端到端）

- [ ] 11.1 E1 验证：单步模拟器控制（start/wait/stop）→ **验证：≤ 60s 全流程**
- [ ] 11.2 E2 验证：APK 自动发现+部署+启动 → **验证：自动发现最新 APK，App 首屏 30s 内渲染**
- [ ] 11.3 E3 验证：14 份用例全量解析（含前置资源+8 种预期类型+V3 双轨调度）→ **验证：无 fatal 错误**
- [ ] 11.4 E4 验证：单用例执行 + 8 类证据收集 → **验证：TC-F-P0-1-01 完整跑通，8 类证据齐全（或降级标记正确）**
- [ ] 11.5 E5 验证：全量回归（14 用例）→ **验证：≤ 30 分钟完成**
- [ ] 11.6 E6 验证：`--no-rules` 对照模式 → **验证：规则判定与无规则对照正确**
- [ ] 11.7 E7 验证：模拟 atx-agent 卡死 → **验证：自愈成功，用例继续**
- [ ] 11.8 E8 验证：报告生成 → **验证：Markdown + JSON + manual_cases.md + affected_modules.json + feedback_suggestions.md 五件套正确**
- [ ] 11.9 E9 验证：manual 用例 AI agent 介入 → **验证：构造 manual 用例，AI agent 能读取 ai-prompt.md 给出判定**
- [ ] 11.10 E10 验证：子规范审计 → **验证：S13/S14 子规范被 AGENTS.md 引用，AI agent 能按规范执行**

## 12. M8 源码影响分析器（V3 新增）⭐

- [ ] 12.1 编写 `ai_tests/lib/source_impact_analyzer.py`：SourceImpactAnalyzer 类骨架（含 SOURCE_ROOT、SOURCE_MAP_PATH 常量）
- [ ] 12.2 实现 `analyze_diff(git_ref="HEAD~1")` → dict：1) `git diff --name-only` 取改动文件 → 2) `_load_or_build_source_map()` → 3) `_reverse_trace()` → 4) `_lookup_related_tc_ids()`，输出 `{changed_files, affected_activities, related_tc_ids, recommended_rerun}`
- [ ] 12.3 实现 `_load_or_build_source_map()` → dict：若 `source_map.json` 存在则加载，否则调 `build_source_map()` 重建
- [ ] 12.4 实现 `build_source_map()` → dict：扫描 `app/src/main/java/io/legado/app/**/*Activity.kt`，对每个 Activity 调 `_find_callers` / `_extract_ui_components` / `_lookup_related_tc_ids`，持久化到 `source_map.json`
- [ ] 12.5 实现 `_find_callers(activity_path)` → list[str]：grep 文件名引用（粗粒度静态调用图）
- [ ] 12.6 实现 `_extract_ui_components(activity_path)` → list[str]：正则提取 `R.id.xxx` / `findViewById` / `setContentView` / Compose setContent
- [ ] 12.7 实现 `_reverse_trace(changed_files, source_map)` → list[str]：改动文件 → 调用方 Activity（向上追溯 2 层）
- [ ] 12.8 实现 `_lookup_related_tc_ids(affected_activities, source_map)` → list[str]：受影响 Activity → 关联 TC-ID（从 source_map.mappings[activity].tc_ids）
- [ ] 12.9 编写 `ai_tests/tests/test_source_impact_analyzer.py` + 实测验证：mock 一个改动（如改 `BookshelfActivity.kt`）→ **验证：affected_activities 正确包含 BookshelfActivity 及其调用方，related_tc_ids 正确**

## 13. M9 源码→测试生成器（V3 新增）⭐

- [ ] 13.1 编写 `ai_tests/lib/source_test_generator.py`：SourceTestGenerator 类骨架
- [ ] 13.2 实现 `generate(activity_name, module="auto")` → str：1) `_locate_activity()` → 2) `_parse_activity_source()` → 3) `_parse_manifest()` → 4) `_render_skeleton()`，输出 Python 测试骨架路径
- [ ] 13.3 实现 `_locate_activity(activity_name)` → str：在 SOURCE_ROOT 下递归查找 `{activity_name}.kt`
- [ ] 13.4 实现 `_parse_activity_source(activity_path)` → dict：正则提取 `setContentView(R.layout.xxx)` / `findViewById<R.id.xxx>` / `startActivity<XXXActivity>` / `onClick { ... }` 跳转目标
- [ ] 13.5 实现 `_parse_manifest()` → dict：解析 `AndroidManifest.xml` 提取 Activity 声明与 intent-filter
- [ ] 13.6 编写 `ai_tests/templates/auto_test_template.j2`：Python 测试骨架 Jinja2 模板（含 TC-ID/关联源码/关联 Activity 头部 + TODO 标记的步骤骨架 + resource-id 常量 + 跳转链断言）
- [ ] 13.7 实现 `_render_skeleton(parsed, manifest)` → str：渲染 Jinja2 模板，输出到 `ai_tests/cases/{module}/auto_{tc_id}.py`
- [ ] 13.8 实现 TC-ID 自动分配：基于 module 前缀 + 现有最大编号 +1（如 `TC-F-P0-4-auto-001`）
- [ ] 13.9 编写 `ai_tests/tests/test_source_test_generator.py` + 实测验证：对 `BookshelfActivity.kt` 生成骨架 → **验证：生成的 auto_*.py 可被 M3 双轨调度识别，resource-id 常量正确**

## 14. 双轨用例与三波覆盖（V3 新增）⭐

- [ ] 14.1 编写 `ai_tests/cases/_index.md`：用例库总索引，记录三波覆盖进度（第一波 14 份存量 / 第二波核心模块矩阵 / 第三波 Bug 反向补充）
- [ ] 14.2 实现第一波覆盖：14 份存量用例全部补全 `**关联源码**` + `**关联 Activity**` 头部字段（V3 源码溯源字段强制）
- [ ] 14.3 启动第二波覆盖：按核心模块优先级矩阵编写 P0 模块用例（调试工具 5 + 书架 8 + 书源管理 10 + 阅读 12 = 35 份）
- [ ] 14.4 实现 `ai_tests/scripts/gen_module_matrix.py`：自动生成核心模块矩阵报告（按模块统计用例数、覆盖率、缺失项）
- [ ] 14.5 建立 `ai_tests/docs/module_matrix.md`：核心模块优先级矩阵表（持续维护，AI 每个 sprint 更新）

## 15. 流程注入验证（阶段 C，V3 新增）⭐

- [ ] 15.1 准备流程注入验证环境：选一个简单的 OpenSpec 任务（如"添加一个设置开关"）作为验证对象
- [ ] 15.2 让另一个 AI agent 按 V3 流程执行 `/openspec`：从 spec → design → tasks → 实施 → 步骤 5.5（自动测试）
- [ ] 15.3 验证 AI agent 能正确执行步骤 5.5.1：触发 `run_e2e.py --diff HEAD~1` → **验证：affected_modules.json 生成且包含改动 Activity**
- [ ] 15.4 验证 AI agent 能正确执行步骤 5.5.2-5.5.7：触发自动装机+测试+报告 → **验证：五件套报告生成且 manual 用例有 ai-prompt.md**
- [ ] 15.5 验证 AI agent 能被另一个 AI 读取并判定 manual 用例：构造 manual 用例 → 第二个 AI agent 读取 ai-prompt.md → 给出 ai_verdict 回填 → **验证：ai_verdict 字段正确回填到 report.json**
- [ ] 15.6 输出流程审计报告 `ai_tests/docs/flow_audit_report.md`：7 项检查清单（5.5.1/5.5.2-5.5.7/manual 介入/复测/5.5.8 反馈闭环）逐项 pass/fail 打分 → **验证：7 项全 pass**

## 16. 反馈闭环（V3 新增）⭐

- [ ] 16.1 编写 `ai_tests/lib/feedback_loop.py`：FeedbackLoop 类骨架（消费 M6 输出的 feedback_signal）
- [ ] 16.2 实现 `process(feedback_signals, report)` → dict：分析失败/manual 案例的 failure_pattern → 输出 `{rule_suggestions, prompt_suggestions, known_issue_suggestions, regression_history_entry}`
- [ ] 16.3 实现规则建议生成：基于 failure_pattern 提取关键字 → 建议扩展 `CRASH_PATTERNS` 或新增规则 → 输出 `rule_suggestions`（AI 审阅后写入 config.py）
- [ ] 16.4 实现提示词调优建议：基于 manual 用例的 ai-prompt.md 反馈 → 建议调优 `ai_prompt_template.j2` → 输出 `prompt_suggestions`
- [ ] 16.5 实现陷阱库沉淀：将新发现的陷阱追加到 `ai_tests/docs/known_issues.md`（含场景描述/根因/规避方式/关联 TC-ID）
- [ ] 16.6 实现回归历史记录：将本轮回归结果追加到 `ai_tests/docs/regression_history.md`（含时间/用例数/pass率/manual率/失败模式 Top3）
- [ ] 16.7 编写 `ai_tests/tests/test_feedback_loop.py` + 实测验证：mock 一组 feedback_signal（含 fail/manual 各一）→ **验证：4 类输出全部生成且 known_issues.md / regression_history.md 正确追加**

## 17. 子规范 S13：AI 自动测试工作流（V3 扩展 5.5.1/5.5.8）

- [ ] 17.1 新建 `docs/project-rules/ai_e2e_testing_workflow.md`：定义 OpenSpec 步骤 5.5 强制流程（5.5.1~5.5.8 八个子步骤）
- [ ] 17.2 V3 详细定义 5.5.1：源码影响分析触发条件（`run_e2e.py --diff HEAD~1`）+ 输出消费方式（affected_modules.json → 自动选复测 TC-ID）
- [ ] 17.3 V3 详细定义 5.5.8：反馈闭环触发条件（`run_e2e.py --feedback`）+ 输出消费方式（feedback_suggestions.md → AI 审阅 → 沉淀到 known_issues.md / config.py / ai_prompt_template.j2）
- [ ] 17.4 定义 AI agent 接入接口：读取 report.json + manual_cases.md + affected_modules.json + feedback_suggestions.md 的流程
- [ ] 17.5 定义 manual 用例处理流程 + 失败用例处理流程 + 引用关系（本子规范被 AGENTS.md 强制规则引用）

## 18. 子规范 S14：测试用例设计指南（V3 扩展双轨+源码溯源）

- [ ] 18.1 新建 `docs/project-rules/test-case-design-guide.md`：定义测试用例 MD 模板（TC-ID/标题/前置资源/V3 关联源码/V3 关联 Activity/步骤/预期 七段）
- [ ] 18.2 定义步骤语义化关键词：6 类原子动作（click/input/wait_element/scroll/back/sleep/assert）的中文关键词映射
- [ ] 18.3 定义预期类型枚举：8 种预期类型（display/no_crash/result_contains/rule_match/db_state/prefs_state/activity_state/web_api/process_state）的关键词
- [ ] 18.4 V3 新增：定义双轨制规则：A 轨 MD 用例（可读性）+ B 轨 Python 用例（精准性），同 TC-ID 时 Python 优先；B 轨 Python 用例命名规范 `auto_{tc_id}.py`
- [ ] 18.5 V3 新增：定义源码溯源字段：`**关联源码**`（如 `BookshelfActivity.kt`）+ `**关联 Activity**`（如 `.ui.BookshelfActivity`）为强制字段
- [ ] 18.6 提供 3 个完整示例：正常用例（编码转换）+ 边界用例（HTTP 工具空 URL）+ 异常用例（断网场景），均含 V3 源码溯源字段

## 19. V3 子规范 S18/S19：源码影响分析指南 + 源码→测试生成指南

- [ ] 19.1 新建 `ai_tests/docs/source_impact_guide.md`：教 AI 维护 `source_map.json`（新增 Activity 时如何更新 mappings + unknown_bindings）
- [ ] 19.2 新建 `ai_tests/docs/source_test_guide.md`：教 AI 用 M9 生成 B 轨 Python 用例（`run_e2e.py --gen-test BookshelfActivity`）+ 补全业务逻辑的规范
- [ ] 19.3 定义 source_map.json 维护流程：1) 新增 Activity → `--update-source-map` → 2) AI 审阅 unknown_bindings → 3) 手动补充映射关系
- [ ] 19.4 定义 B 轨 Python 用例补全规范：生成的骨架含 TODO 标记，AI 必须补全步骤/断言/证据收集点后才能纳入回归

## 20. V3 子规范 S20/S21：已知问题与陷阱库 + 回归历史

- [ ] 20.1 新建 `ai_tests/docs/known_issues.md`：陷阱库初始模板（含分类：环境类/兼容类/源码类/规则类/提示词类）+ 首批 5 个已知陷阱（MEmu 启动慢/atx-agent 卡死/run-at 不可用/Web API 8080 未启动/source_map.json 过期）
- [ ] 20.2 新建 `ai_tests/docs/regression_history.md`：回归历史初始模板（含字段：时间/APK 版本/用例数/pass 率/manual 率/失败模式 Top3/反馈闭环触发次数）
- [ ] 20.3 定义陷阱库沉淀流程：M16 反馈闭环输出的 `known_issue_suggestions` → AI 审阅 → 追加到 known_issues.md（含场景/根因/规避方式/关联 TC-ID）

## 21. 修改 OpenSpec 工作流 + AGENTS.md（V3 含固化层保护）

- [ ] 21.1 修改 `docs/project-rules/openspec-workflow.md`：在步骤 5 与 6 之间嵌入步骤 5.5（V3 含 5.5.1 源码影响分析 + 5.5.8 反馈闭环八个子步骤）
- [ ] 21.2 更新工作流图 + 强制检查点说明：检查点 2 引用步骤 5.5 自动测试报告（含 V3 五件套）
- [ ] 21.3 更新 AI Agent OpenSpec 检查清单：添加"是否执行步骤 5.5 AI 自动端到端测试？是否触发源码影响分析？是否触发反馈闭环？"
- [ ] 21.4 在 `AGENTS.md` 强制规则区添加"🔴🔴 强制规则：AI 自动端到端测试"条目，引用 S13/S14 子规范
- [ ] 21.5 V3 新增：在 `AGENTS.md` 添加"🔴 固化层保护规则"：列出 lib/ 下 9 个模块文件（M1-M9）AI 不应直接修改，必须通过 OpenSpec 流程
- [ ] 21.6 添加反模式说明："❌ 跳过步骤 5.5 直接审核"、"❌ 不按子规范设计测试用例"、"❌ 不读取 manual_cases.md 就标记任务完成"、"❌ V3 不触发源码影响分析"、"❌ V3 不沉淀失败案例到反馈闭环"
- [ ] 21.7 V3 新增：在 `AGENTS.md` 添加"持续迭代层"清单：列出 cases/、source_map.json、known_issues.md、regression_history.md、CRASH_PATTERNS、ai_prompt_template.j2 等 AI 可持续迭代的文件

## 22. AI 协作指南 + 文档同步

- [ ] 22.1 新建 `ai_tests/docs/ai_collaboration_guide.md`：定义 AI agent 接入流程（OpenSpec 步骤 5.5 触发 → 执行 run_e2e.py → 读取 report.json + 五件套）
- [ ] 22.2 V3 扩展：定义 manual 用例处理流程 + 失败用例处理流程 + V3 反馈闭环处理流程（读取 feedback_suggestions.md → 审阅 → 沉淀到 known_issues.md / config.py / ai_prompt_template.j2）
- [ ] 22.3 更新 `docs/INDEX.md` + `docs/project-flow/quick-reference.md`：e2e-automated-testing 条目状态描述更新为 V3 定位 + 添加"AI 自动测试"命令速查节（含 V3 `--diff`/`--gen-test`/`--feedback` 命令）
- [ ] 22.4 编写 `ai_tests/docs/usage.md` + `ai_tests/docs/troubleshooting.md`：详细使用文档（环境准备+首次初始化+日常使用+V3 源码影响分析+V3 反馈闭环+故障排查）
- [ ] 22.5 文档同步检查：对照 `docs/project-flow/` 相关文档是否需要补充测试系统说明（如 task-navigation.md 新增"AI 测试"任务导航）+ `assets/updateLog.md` 评估（开发者可感知非终端用户可感知，需斟酌）

---

## AOAdapt 日志（遇到问题时记录）

> **格式**：
> ```markdown
> - [ ] X.Y 任务名
>   - Action: [执行了什么操作]
>   - Observation: [观察到了什么结果]
>   - Adapt: [基于观察做了什么调整]
> ```

（执行过程中按需填写）

---

## 任务依赖关系（V3 更新）

```
1. 环境准备
  ↓
2. M1 模拟器控制 ←───── 4. u2 初始化（依赖 M1）
  ↓                       ↓
3. M2 APK 部署           ↓
  ↓                       ↓
5. M3 用例解析（V3 双轨）──→ 6. M4 UI 执行 ──→ 7. M5 证据收集器
                                          ↓
                                       8. M6 规则分析器（V3 +反馈信号）
                                          ↓
                                       9. M7 报告生成器（V3 +affected+feedback）
                                          ↓
                                      10. 编排层（V3 +--diff/--gen-test/--feedback）
                                          ↓
                                      11. 端到端验证 A+B
                                          ↓
                ┌─────────────────────────┴─────────────────────────┐
                ↓                                                   ↓
   12. M8 源码影响分析器 ⭐                          13. M9 源码→测试生成器 ⭐
                ↓                                                   ↓
                └─────────────────────────┬─────────────────────────┘
                                          ↓
                              14. 双轨用例与三波覆盖 ⭐
                                          ↓
                              15. 流程注入验证（阶段 C） ⭐
                                          ↓
                              16. 反馈闭环 ⭐
                                          ↓
                          ┌───────────────┼───────────────┐
                          ↓               ↓               ↓
                  17. S13 工作流   18. S14 设计指南   19. S18/S19 源码指南
                          ↓               ↓               ↓
                          └───────────────┼───────────────┘
                                          ↓
                              20. S20/S21 陷阱库+回归历史
                                          ↓
                              21. 修改 OpenSpec + AGENTS.md
                                          ↓
                              22. AI 协作指南 + 文档同步
```

**关键依赖**：
- 阶段 12-13（M8/M9）依赖阶段 10（编排层）通过后再编写，因为 V3 命令需要 M8/M9 支持
- 阶段 14（双轨用例）依赖阶段 12-13 完成（B 轨 Python 用例由 M9 生成）
- 阶段 15（流程注入验证）依赖阶段 14 完成（需要双轨用例库）
- 阶段 16（反馈闭环）依赖阶段 8（M6 输出 feedback_signal）+ 阶段 9（M7 输出 feedback_suggestions.md）
- 阶段 17-21（子规范）依赖阶段 15 通过后再编写，确保规范与实现一致
- 阶段 21（修改 OpenSpec）必须先于阶段 22（AI 协作指南），因为协作指南引用子规范

---

## 三级完成标准（禁止混用）

| 级别 | 标准 | 标记 |
|------|------|------|
| **Level 1 - 代码完成** | 文件存在 + Python import 通过 | ⚠️ |
| **Level 2 - 功能验证** | 模块功能可运行 + 输出正确 | ⚠️→✅ |
| **Level 3 - 场景验证** | 真实 APK 端到端通过 + 子规范被 AGENTS.md 引用 | ✅ |

---

## 关键里程碑（V3 更新）

| 里程碑 | 完成任务 | 价值 |
|--------|---------|------|
| **MVP-1** | 1+2+3+4+10 | 能自动发现 APK 并装到模拟器启动 |
| **MVP-2** | +5+6 | 能解析用例并执行单步操作（V3 含双轨调度） |
| **MVP-3** | +7+8+9 | 完整单用例闭环（8 类证据+规则判定+V3 反馈信号+五件套报告） |
| **MVP-4** | +11 | 14 用例全量回归通过（≤ 30 分钟） |
| **V3-1** | +12+13 | M8 源码影响分析 + M9 源码→测试生成器可用 |
| **V3-2** | +14 | 双轨用例 + 三波覆盖第二波启动 |
| **V3-3** | +15 | 流程注入验证（阶段 C）7 项全 pass |
| **V3-4** | +16 | 反馈闭环可用，失败案例自动沉淀 |
| **Spec-1** | +17+18 | 子规范 S13/S14 编写完成（V3 含双轨+源码溯源） |
| **Spec-2** | +19+20 | V3 子规范 S18/S19/S20/S21 编写完成 |
| **Spec-3** | +21 | OpenSpec 工作流 + AGENTS.md 修改完成（V3 含固化层保护） |
| **Release** | +22 | AI 协作指南 + 文档完整，可移交后续 AI agent 使用 |

---

## 风险与缓解（V3 更新）

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| uiautomator2 在 MEmu x86_64 不兼容 | 中 | 高 | 预先实测（任务 4.2），失败则降级裸 ADB + 坐标定位 |
| 用例解析格式不规范（现有 14 份无前置资源段） | 高 | 中 | 容错策略 + parse_warning 不阻断；V3 阶段 14.2 逐步补充源码溯源字段 |
| atx-agent 频繁卡死 | 中 | 中 | 自愈机制（任务 6.10） |
| run-at 在 Android 9 不可用 | 中 | 中 | 证据 5/6 降级标记 run_at_unavailable，不阻断（任务 7.12） |
| Web API 8080 端口未启动 | 高 | 低 | 证据 7 降级标记 web_api_unavailable，不阻断（任务 7.12） |
| 8 类证据收集耗时超 30 分钟 | 低 | 中 | 并行收集（5/6/7 并发）+ 总耗时监控 |
| MEmu 启动慢（>60s） | 低 | 中 | 等待 60s + 重试 3 次 |
| 磁盘空间不足 | 低 | 高 | 启动前检查 + 定期清理脚本 |
| 子规范与实现不一致 | 中 | 中 | 阶段 17-21 在阶段 15 通过后编写，确保规范与实现一致 |
| AGENTS.md 修改破坏现有规则结构 | 低 | 高 | 严格遵循 AGENTS.md 现有格式（🔴🔴 强制规则区），最小化改动 |
| **V3：M8 静态调用图分析覆盖率不足** | 中 | 中 | 正则提取覆盖 80%+ 场景，剩余 20% 通过 unknown_bindings 标记 + AI 手动补充 |
| **V3：M9 生成的 Python 骨架业务逻辑缺失** | 高 | 中 | 骨架含 TODO 标记，AI 必须补全后才能纳入回归（任务 19.4） |
| **V3：source_map.json 过期** | 中 | 中 | `--update-source-map` 命令重建 + 新增 Activity 时强制更新（任务 19.3） |
| **V3：双轨调度 Python 失败时降级 MD 不完整** | 中 | 低 | Python 失败时记录降级原因到 report.json，仍执行 MD 作为兜底 |
| **V3：流程注入验证（阶段 C）AI agent 无法执行** | 中 | 高 | 选简单 OpenSpec 任务作为验证对象 + 提供 ai_collaboration_guide.md 详细引导 |
| **V3：反馈闭环误判（误沉淀规则）** | 中 | 中 | feedback_suggestions.md 必须 AI 审阅后才能写入 config.py / known_issues.md（不自动写入） |
| **V3：固化层被 AI 误修改** | 低 | 高 | AGENTS.md 添加固化层保护规则 + lib/ 下文件标记"🔒 固化层"注释 |

---

## V3 调整记录

### 2026-07-07 V3 调整（基于用户深度反馈再次重构）

**用户反馈核心**（V2 审核意见）：

> "你还需要思考一个问题呀，现在整个流程既然整理下来了，那你如何去构建持续迭代的测试用例呢？并且基于现在的源码呀，源码是你的根，你优化的功能也有源码呀，你，作为ai，你通过openspec现在设计了一个新功能，功能有改动了，影响了哪些源码？源码动了之后可能会对哪些前端页面造成影响，需要进行复测，并且这个复测的手段是可以基于源码去做一些深度定制脚本的呀，毕竟没有多模态，你只能基于源码的xml去自动模拟触发模拟器内apk的流程性东西呀，还有就是现在存量的全量的测试用例你打算怎么搞？？并且现在这个流程规划完毕之后，你打算如何验证？并且后续持续迭代这个流程呢？哪些是固化的，哪些是需要持续迭代的呀"

**6 项 V3 关键调整**：

1. ❌ V2 仅 MD 单轨用例 → ✅ V3 双轨制（MD + Python 源码生成）：阶段 5 扩展双轨调度 + 阶段 14 三波覆盖
2. ❌ V2 不读源码 → ✅ V3 M8 源码影响分析 + M9 源码→测试生成器：阶段 12-13 新增
3. ❌ V2 无影响范围分析 → ✅ V3 git diff → source_map.json → 自动选复测用例：阶段 12 实现
4. ❌ V2 仅 14 份存量用例 → ✅ V3 三波覆盖（存量→核心模块→Bug 反向补充）：阶段 14 实现
5. ❌ V2 仅端到端验证 → ✅ V3 三阶段（单元+端到端+流程注入验证）：阶段 15 新增阶段 C
6. ❌ V2 无反馈闭环 → ✅ V3 失败 → 沉淀规则库 → 调优提示词 → 下一轮更准：阶段 16 实现

**V3 任务数变化**：
- V2：17 阶段 128 子任务
- V3：22 阶段 165 子任务（+37 子任务，主要为 M8/M9/双轨/流程注入验证/反馈闭环 + V3 子规范扩展）

### V3 保留项（V2 合理部分）

- ✅ V2 全部 8 项调整（V1→V2 的修正全部保留）
- ✅ 9 模块中 M1-M7 全部保留，V3 仅扩展 M8/M9
- ✅ 8 类非多模态验证手段
- ✅ 三层架构（编排/执行/基础设施）+ V3 新增 Layer 0 源码驱动层
- ✅ 失败不阻断 + 证据归档
- ✅ Markdown + JSON + manual 三件套报告（V3 扩展为五件套：+ affected_modules.json + feedback_suggestions.md）
