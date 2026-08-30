# spec.md — ai_tests 体系沉淀反思优化（ai-test-system-refinement）

> 用户需求原文："沉淀并反思优化 ai_test 体系，包括文档及脚本，以及测试用例，测试方法等"
> 关联前序：`docs/specs/archive/e2e-automated-testing`（体系建设）、`docs/specs/archive/ai-tests-deep-audit`（深度审计）

## Intent

ai_tests 自动化测试体系自建设以来经数月高频真机使用，SOP 立项初衷——"固定流程可复用"——正在被四类累积债务侵蚀：

1. **脚本失控**：`ai_tests/scripts/` 205 个 .py 平铺堆叠——153 个有 `__main__`（52 个没有）、仅 46 个有 argparse、仅 21 个 import config；6+ 条重复版本链（dump_ui_safe→v2、parse_ui→parse_ui2→parse_ui3→parse_ui_safe、query_image_source→v2→v3→v4→_safe、e2e_verify_rss_source→detail→robust→v3、check_db_searchurl→2、goto_settings/goto_settings2）；13 个 diag_* 诊断脚本；V5 时代残留（v5_cf_breakthrough、v5_classification_scan、v5_hard_source_fix、v5_missing_fields_fix、v5_spa_breakthrough、v5_video_breakthrough 及 import_rss_source_v5）；一次性站点分析链 11 个（analyze_site_e 族 6 + analyze_sway 族 3 + playwright_siteE/sway 2）。
2. **文档漂移**：SOP（`ai_tests/docs/fixed_test_workflow.md`）未登记 l2_* 家族与新增脚本；`ai_tests/README.md` 含 13 个已删脚本引用 + 失效 docs/specs 链接 + V5 过时章节；`docs/project-rules/ai_e2e_testing_workflow.md` :36/:56/:137 引用不存在的 `ai_tests/scripts/run_e2e.py`（实际在 `ai_tests/run_e2e.py`）；L1/L2/L3 完成级别无集中定义。
3. **用例解析丢失**：`ai_tests/lib/case_parser.py` 只认 `## / ### TC` 头（L37-39 `TC_HEADER_RE` 仅 `#{2,3}`）且只 glob `*.md`（L377），导致 `ai_tests/cases/F-UI-THEME/case.md.seg2`（16 条）、`case.md.seg4`（14 条）与 `docs/tests/F-P1-8-source-folder-view.md`（`#### TC` 头）整批用例资产游离于解析统计之外；另 F-UI-THEME 59 条仅"关联源码"无"关联 Activity"元数据。
4. **经验断层**：8 项真机调试经验（su -c 整串引号 / value= 属性定位 / 亮度差判定方法论 / StaleObject→坐标 tap / 弹框独立窗口 / sed 引号 / screencap 陈旧帧 / 验证空炮）未回流 SOP，后续任务会重复踩坑。

本任务对以上债务做一次系统性"沉淀—反思—优化"，让体系恢复到"新增脚本有登记、经验有回流、用例可解析、编排层承诺的功能真实可用"的健康态。

## Scope

### In Scope

| 批次 | 内容 | 对应需求 |
|------|------|---------|
| A 文档沉淀+经验回流 | SOP 登记全部 l2_* 家族 + 3 个新增脚本；铁律章节扩充覆盖 8 项经验缺口；README 清理失效引用与 V5 过时章节；ai_e2e_testing_workflow.md 路径修复；L1/L2/L3 集中定义 | R1/R2/R3/R8/R9/R10 |
| B 编排层接入 | run_e2e.py `--feedback` 从"M16 未实现"降级提示改为真实接入 `lib/feedback_loop.py`；affected_modules 从固定 None 改传 M8 analyze_diff 结果；报告产物五件套补齐 2 件 | R4 |
| C 用例解析修复 | seg 文件 30 条用例可解析；`#### TC` 头兼容（F-P1-8 整文件可解析）；登记 F-UI-THEME 59 条"关联 Activity"元数据缺口 | R5/R6 |
| D scripts 删除治理 | 每条重复链保留最新版，旧版 + diag_* + V5 残留 + 一次性站点链进删除清单；删除清单经用户确认后执行 | R7 |
| E 验证 | pytest 295 全过；run_e2e.py 冒烟；解析数量基线核对；文档零失效引用扫描 | R7/R8 及全量回归 |

### Out of Scope

- **lib/ 固化层重构**：分层架构质量已高，不做架构级重构（批次 C 仅允许对 `lib/case_parser.py` 做定点解析缺陷修复，不动模块边界）
- **B 轨 Python 执行 M9 接入**：run_e2e.py `--gen-test` 仍走降级提示，M9 属独立大任务，本任务仅登记后续
- **App 源码 app/**：本任务零改动
- **venv/ 依赖升级**：requirements 维持现状
- **reports/ 历史文件清理**：含问题定位证据价值，本任务仅在文档中登记清理建议，实施另开单独任务

## Approach

### Selected Approach

**文档先行 + 接入已有实现 + 解析修复 + 清单式删除治理**，按 A→B→C→D→E 批次推进：

1. **文档先行（批次 A）**：先修 SOP/README/workflow 三处漂移，让后续批次有权威文档可依；经验沉淀集中到 SOP 单一权威文档（章节式 + 锚点），避免多文档复制漂移。
2. **接入已有实现（批次 B）**：`lib/feedback_loop.py` 的 `FeedbackLoop.process`（L38-60）已实现且有 `tests/test_feedback_loop.py` 3 个单测——`--feedback` 接入是纯接线工作，收益最大、风险最小；同批把 affected_modules 接上 M8（`--diff` 时 `SourceImpactAnalyzer.analyze_diff` 已运行但结果未传递给报告）。
3. **解析修复（批次 C）**：`lib/case_parser.py` 两处定点修复（TC 头级别兼容 + glob 模式扩展或 seg 合并），恢复用例资产统计真实性。
4. **清单式删除治理（批次 D）**：采用"保留最新版 + 删除清单用户确认"模式——每条重复链只保留最新版本，diag_*/V5/站点链整体进清单；清单先经用户确认再删，防误删。

理由：
- feedback_loop 已实现未接入，接线即可兑现 README 承诺的 V3 能力，是全任务性价比最高项
- 删除治理最怕误删在用脚本，"清单确认 + git 历史兜底"是成本最低的安全模式
- 经验集中 SOP 单点沉淀，配合分节锚点，规避"经验散落 N 个文档各自过时"的老问题

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 全量重写 205 脚本规范化 | 统一 argparse/config/入口规范后重写全部脚本 | 工作量巨大；多数为一次性诊断/站点分析脚本，无重写价值，删除比重写更经济 |
| 引入脚本注册表/自动索引生成器 | 自动扫描 scripts/ 生成索引清单 | 增加一个需要持续维护的生成器；SOP 脚本表 + README 索引两处人工登记已足够 |
| reports/ 全量清理归档 | 本任务顺带清理历史报告 | 历史报告含问题定位证据价值，"顺手删"风险高；登记建议、单独任务处理 |
| M9 B 轨接入 | 顺带实现 --gen-test 的 M9 source_test_generator | scope 蔓延；M9 是独立设计-实施任务，本任务仅登记后续 |

### Drawbacks

- **删除脚本有误删风险**：205 个脚本中可能存在未被 SOP/README 登记但在用的脚本。缓解：删除清单逐条标注"最后引用点"并经用户确认；每条重复链保留最新版；git 历史可随时恢复。
- **feedback 接入改变报告产物结构**：五件套从 3 件变 5 件，旧报告目录对比断裂。缓解：README 登记"产物结构 v2 变更说明"。
- **SOP 集中沉淀可能过长**：铁律章节持续追加会使 SOP 膨胀。缓解：分节 + 锚点索引；超长内容外移 references 并在 SOP 留锚点链接。

### Prior Art

- `docs/specs/archive/config-needs-restart-fix`：文档与代码一致性治理先例（R8/R9 同模式）
- `docs/specs/archive/memory-mechanism-redesign`：沉淀机制设计先例（批次 A 经验回流同思路）
- SOP `ai_tests/docs/fixed_test_workflow.md` L243-247 "L2 观测通道与 adb 数据传输铁律（2026-08-30）"章节：章节式经验沉淀的既有先例，本任务沿用该模式扩充
- `docs/specs/archive/ai-tests-deep-audit`：前序审计已识别空壳模块与临时脚本，本任务是其治理落地

## Requirements

### R1：SOP 脚本登记补全
- SOP（`ai_tests/docs/fixed_test_workflow.md`）登记全部 l2_* 家族脚本 + 3 个新增脚本（以批次 A 盘点清单为准）
- 每条登记含：脚本名、用途、调用方式、前置条件
- README 脚本索引与 SOP 登记保持一致

### R2：SOP 铁律章节扩充（交互类陷阱）
- 在现有铁律章节（2026-08-30 铁律位于 L243-247）基础上新增小节：
  - su -c 整串引号陷阱（整串传参 vs 拆分传参差异）
  - value= 属性定位（UI dump 中属性定位的正确写法）
  - u2 交互陷阱：StaleObject→坐标 tap 兜底、弹框独立窗口处理

### R3：方法论与教训沉淀
- 亮度差判定方法论（屏幕亮度验证类用例的差值判定法）落入 SOP 对应用例章节
- "验证空炮"教训（验证步骤看似执行、实际未产生断言效果）落入 SOP 验证章节

### R4：--feedback 真实接入 + 五件套补齐
- 移除 run_e2e.py L201-204 的"M16 feedback_loop 未实现"降级提示，改为真实调用 `lib/feedback_loop.py` `FeedbackLoop.process`（已实现，L59-98，入参=report dict {cases:[...]}，出参=4 类建议 dict；穿透核实：run_e2e.py L524-535 已从 results 提取 feedback_signals 传 generate_all，--feedback 只需在其后追加 FeedbackLoop 调用——时序=用例执行完→FeedbackLoop.process→generate_all）
- affected_modules 由固定 None（run_e2e.py L534）改为传入 M8 `SourceImpactAnalyzer.analyze_diff` 结果 diff_result（--diff 场景；类型已对齐：generate_all 期望 Dict，diff_result 含 changed_files/affected_activities/related_tc_ids；L529 "需要 M8 实现"注释已过时）
- 报告产物五件套从现有 3 件补齐至 5 件（affected_modules.json + feedback_suggestions.md/json）
- feedback 环节异常不得阻塞主流程（try 包裹 + WARN + 退出码不变）
- **同步更新 tests/test_run_e2e.py 锁死旧警告行为的 2 处断言**（test_handle_v3_feedback_warning 等），全部单测回归通过

### R5：F-UI-THEME seg 残留清理（穿透修正）
- **穿透核实修正**：case.md.seg2（16 个 TC-ID）/case.md.seg4（19 个 TC-ID）与 case.md（65 条）**100% 重叠**——seg 是拆分过程旧残留而非"30 条用例丢失"，处理方式=直接删除 seg 文件（无需合并去重）
- 删除后 CaseParser 对 case.md 解析断言 ≥65 条（TC-F-UI-THEME-xxx 格式，## 层级可解析）
- 既有 ai_tests/cases 152 条解析结果零回归

### R6：#### TC 头兼容
- `lib/case_parser.py` `TC_HEADER_RE`（L37-39，当前仅 `#{2,3}`）扩展兼容 `#### TC`，或规范化 `docs/tests/F-P1-8-source-folder-view.md` 的 TC 头级别（二选一，design.md 定案）
- 修复后 F-P1-8 全部用例可解析

### R7：scripts 删除治理
- 删除脚本数 ≥40：diag_* 13 个 + V5 残留 6 个（v5_cf_breakthrough / v5_classification_scan / v5_hard_source_fix / v5_missing_fields_fix / v5_spa_breakthrough / v5_video_breakthrough 及 import_rss_source_v5，以删除清单盘点为准）+ 一次性站点链 11 个（analyze_site_e 族 6 + analyze_sway 族 3 + playwright_siteE/sway 2）+ 重复版本链旧版约 13 个
- 每条重复链仅保留最新版本（dump_ui_safe 链留 v2、parse_ui 链留 parse_ui_safe、query_image_source 链留 _safe、e2e_verify_rss_source 链留 v3、check_db_searchurl 链留 2、goto_settings 链留 goto_settings2）
- 删除清单先经用户确认（AskUserQuestion）再执行
- 引用核查必须含 **import 语句级**检查（被删脚本可能被保留脚本 import，如 parse_ui 族被 dump 脚本引用）+ tests/ 引用检查
- 删除后 pytest 295 个单测全过，且 run_e2e.py / SOP / README 无指向已删脚本的引用

### R8：README 零失效引用
- `ai_tests/README.md`：清除 13 个已删脚本引用、失效 docs/specs 链接、V5 过时章节
- 脚本索引反映删除后真实数量（205 − 删除数）
- 全文链接扫描零断链

### R9：workflow 文档路径修复
- `docs/project-rules/ai_e2e_testing_workflow.md` :36/:56/:137 的 `ai_tests/scripts/run_e2e.py` 修正为 `ai_tests/run_e2e.py`
- 全文扫描其他失效路径一并修复

### R10：L1/L2/L3 集中定义
- L1 代码完成 / L2 功能验证 / L3 场景验证在 SOP 或 README 建立唯一权威定义（含判定标准与示例）
- 其他文档引用该定义，禁止各自复制产生版本漂移

### R11：并行会话协调（穿透自审新增）
- 并行文档规整会话待实施项④"ai_tests SOP 脚本引用修复"与本任务批次 A 重叠（该会话曾重建 ai_memory_main 致本任务条目丢失，写竞态实锤）
- 实施批次 A 前必须经用户裁决协调（治理会话先完成④避让 / 本任务先行 / 合并处理），并在实施前重新 Read SOP 确认当前内容再 Edit（防覆盖其变更）
- 记忆条目写入后 Grep 复核存在性

## Scenarios

### 正常场景

**S1 新增脚本后 SOP 同步流程**
- Given 在 `ai_tests/scripts/` 新增一个固定流程脚本
- When 按 R1 登记流程操作
- Then SOP 脚本表与 README 索引同步新增条目，下次任务可直接按 SOP 引用该脚本

**S2 --feedback 生成五件套**
- Given run_e2e.py 带 `--feedback` 完成 L2 用例执行
- When 主流程进入报告生成阶段
- Then `FeedbackLoop.process` 被真实调用并产出反馈建议，五件套齐全，输出中无"M16 未实现"降级提示

**S3 用例解析数量提升**
- Given 批次 C 修复完成
- When 对 docs/tests（18 文件 234 条基线）+ ai_tests/cases（152 条基线）全量解析
- Then seg 30 条与 F-P1-8 全部用例被解析，总数较基线提升且既有用例解析结果零回归

### 异常场景

**S4 feedback 环节异常不阻塞**
- Given `FeedbackLoop.process` 执行中抛出异常
- When run_e2e.py 主流程执行到报告阶段
- Then 异常被 try 包裹、打印 WARN 日志，主流程退出码不受影响，其余报告产物正常生成

### 边界场景

**S5 删除清单脚本被 SOP 引用**
- Given 删除清单中某脚本仍被 SOP/README 引用
- When 执行批次 D
- Then 先更新 SOP/README 引用，再执行删除（顺序约束，禁止先删后改）

**S6 seg 文件与 case.md 内容重叠**
- Given `case.md.seg2`/`case.md.seg4` 内容与 `case.md` 存在重叠用例
- When 批次 C 选定合并方案
- Then 合并时按用例 ID 去重，保证解析总数 = 真实用例数，不出现重复计数
