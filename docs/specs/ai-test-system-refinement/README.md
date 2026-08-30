# OpenSpec 变更：ai-test-system-refinement

> **状态：✅ 已完成（2026-08-30：五批次全部实施——SOP 沉淀 6 处/编排层 feedback 接线冒烟实证/用例 +32 条找回/scripts 205→153 删 52 个/pytest 295×2 全绿+冒烟 pass；检查点 2/3 待用户合并验收）**

## 功能概述

### 背景

用户需求：**"沉淀并反思优化 ai_test 体系，包括文档及脚本，以及测试用例，测试方法等"**。

经 3 个探索子代理并行盘点，`ai_tests/` 体系在长期快速迭代中积累了 8 类问题（P1~P8），已从"能跑"滑向"难维护、难追溯"：

- **P1 scripts/ 重灾区**：205 个平铺脚本，91% 硬编码路径、78% 无 argparse、52 个无 `__main__` 入口；同名 v2/v3/v4 重复版本链 6+ 条（dump_ui_safe/v2、parse_ui×4、query_image_source×5、e2e_verify_rss×4 等）；13 个 diag_* 应删未删；6 个 V5 残留；一次性站点分析脚本使命结束残留。
- **P2 README.md 过时**：13 个已删脚本引用；docs/specs 失效链接；reports/ 结构描述与实际不符（宣称 report_{timestamp}/ 七件套，实际 ~190 个散落文件）。
- **P3 代码-文档脱节**：`run_e2e.py` L201-204 的 `--feedback` 仍打印"M16 未实现"降级提示，但 `lib/feedback_loop.py` 已实现且有 3 个单测，编排层未接入；`report_generator` 收 `affected_modules=None`（run_e2e.py L534 固定传 None）→ 报告五件套长期缺 `affected_modules.json` 和 `feedback_suggestions.md` 2 件。
- **P4 用例解析缺陷（穿透修正）**：`ai_tests/cases/F-UI-THEME/case.md.seg2`（16 条）与 `case.md.seg4`（14 条）后缀非 `.md` 不被 CaseParser 解析——**穿透实测其 TC-ID 与 case.md（65 条）100% 重叠，属纯冗余残留而非用例丢失**；`docs/tests/F-P1-8-source-folder-view.md` 用 #### 四级标题写 TC 头（16 处），`TC_HEADER_RE` 仅匹配 `#{2,3}` → 整文件用例不可解析（这是真正的丢失面）。
- **P5 经验沉淀断层**：8 项散落代码注释层的实战经验未回流文档——① adb shell 列表传参拆散 su -c（必须整串）；② prefs 值在 `value="` 属性；③ 像素亮度差判定方法论；④ u2 StaleObjectException→dump+坐标 tap；⑤ 弹框独立窗口 dump 限制；⑥ toybox sed 经 su 引号坑；⑦ 模拟器 screencap 陈旧帧；⑧ "验证空炮"教训（全新安装读不到脏数据）。
- **P6 SOP 双向失守**：本次新增 3 脚本（l2_verify_theme_rss_header_sync / l2_verify_header_brightness / l2_vl_header_analysis）未登记 SOP 脚本表（违反 SOP 自身"新增脚本必须更新 SOP"规则）；`docs/project-rules/ai_e2e_testing_workflow.md` 3 处 run_e2e.py 路径漂移（引用 `ai_tests/scripts/run_e2e.py`，实际在 `ai_tests/run_e2e.py`）。
- **P7 L1/L2/L3 完成级别无集中权威定义**（散落 SOP 步骤表与 components-capability-inventory.md）。
- **P8 F-UI-THEME 59 条用例缺"关联 Activity"溯源字段**（SOP 要求双字段）。

### 目标

1. **文档沉淀**：SOP 补齐 + 经验回流 + 权威定义收敛，消除 P2/P5/P6/P7。
2. **编排层修正**：`--feedback` 真正生效、五件套报告补齐，消除 P3。
3. **用例完整性**：清理 seg 冗余残留 + 修复 F-P1-8 不可解析用例（16 条找回）+ 补溯源字段评估，消除 P4/P8。
4. **脚本治理**：删除清单驱动的一次性/重复/残留脚本清理，缓解 P1。
5. **全量验证**：pytest 全绿 + 冒烟 + SOP 交叉核查，确保不引入回归。

## 核心能力（五批次修复范围）

| 批次 | 名称 | 修复内容 | 对应问题 |
|------|------|----------|----------|
| A | 文档沉淀 | SOP 补登 3 个新脚本 + 铁律追加（su -c 整串 / value= 属性）+「u2 交互陷阱」小节（StaleObject / 弹框窗口 / sed 引号 / tab 顺序 / screencap 陈旧帧）+ 亮度判定方法论 + 空炮教训入 known_issues.md；`ai_e2e_testing_workflow.md` 路径修复；L1/L2/L3 权威定义落 SOP | P5、P6、P7 |
| B | 编排层接入 | run_e2e.py 接入 feedback_loop（`--feedback` 生效）+ affected_modules 传 M8 分析结果（有 `--diff` 时）→ 报告五件套补齐 | P3 |
| C | 用例解析修复 | seg 纯残留文件删除（穿透实测与 case.md 100% 重叠）；F-P1-8 TC 头层级修正；F-UI-THEME 补关联 Activity 字段（P2 可选） | P4、P8 |
| D | scripts 治理 | 删除清单（diag_* 13 / V5 残留 6 / 站点一次性 / 重复版本链保留最新版）+ README 失效引用清理；删除执行前需用户确认清单 | P1、P2 |
| E | 验证 | pytest 全量 + run_e2e --diff 冒烟 + SOP 交叉核查 | 全部 |

## 文档索引

| 文档 | 说明 | 链接 |
|------|------|------|
| spec.md | 需求规格（What & Why） | [spec.md](./spec.md) |
| design.md | 技术设计（How） | [design.md](./design.md) |
| tasks.md | 实施任务清单 | [tasks.md](./tasks.md) |

> 以上三份文档按 OpenSpec 流程随设计阶段推进依次产出。

## 影响范围

- **主战场**：`ai_tests/` 目录
  - `ai_tests/run_e2e.py`（批次 B：编排层接入）
  - `ai_tests/scripts/`（批次 D：脚本治理）
  - `ai_tests/cases/`（批次 C：用例修复）
  - `ai_tests/README.md`（批次 D：失效引用清理）
  - `ai_tests/lib/`（批次 B 仅复用 feedback_loop，不改其逻辑）
- **文档域**：`docs/project-rules/ai_e2e_testing_workflow.md`（批次 A：路径修复 + SOP 补登）、`ai_tests/docs/known_issues.md`
- **明确不碰**：App 源码 `app/` 目录零改动（纯测试体系治理）。

## 验证计划摘要

1. **单测全量**：`pytest` 跑 ai_tests 全部单测（含 feedback_loop 既有 3 个），全绿为准。
2. **编排冒烟**：`python ai_tests/run_e2e.py --diff` 冒烟，确认五件套报告产出完整（含 `affected_modules.json` 与 `feedback_suggestions.md`）。
3. **SOP 交叉核查**：逐条核对批次 A 修改后的 SOP 与脚本实际行为一致（脚本表、路径、L1/L2/L3 定义三处交叉）。
4. **解析回归**：批次 C 修复后 F-P1-8 用例 +16 条可解析（seg 为纯残留删除不增数），F-UI-THEME case.md ≥65 条零回归。
5. **删除清单门禁**：批次 D 删除执行前输出完整清单交用户确认，删除后 pytest 全量复跑确认无隐性依赖。
