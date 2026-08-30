# tasks.md — ai-test-system-refinement

> 五批次优化 ai_tests 体系：A 文档沉淀 / B 编排层接入 / C 用例解析修复 / D scripts 删除治理 / E 验证

## 0. 准备

- [x] 0.1 备份待删脚本清单到 bak/ai-test-refinement-20260830/ ✅（scripts_backup_20260830.zip 52 entries）
- [x] 0.2 生成删除候选精确清单并逐个 **import 级** Grep 核查 ✅（52/52 存在；15 个有引用全为文档级/同名函数级，0 import 阻塞；manifest 落 bak/deletion_manifest.txt）
- [x] 0.3 记录用例解析基线 ✅（CaseParser 直跑：total=340 / F-UI-THEME 59 / F-P1-8 0（实锤不可解析）/ dup_ids=10）
- [x] 0.4 并行会话协调 ✅（检查点1 用户裁决"本任务先行"；每次 Edit 前重新 Read，批次 A 子代理全程遵守）

## 1. 批次A 文档沉淀

- [x] 1.1 SOP 脚本表补登（16a-16g 七行：theme_sync/header_brightness/vl_header_analysis/highlight_toggle/rss_folder_cover_dialog/rss_folder_margin/video_ux_fixes）✅ L33-39
- [x] 1.2 SOP 铁律追加第 4/5 条：su -c 整串传参 + prefs value= 属性解析 ✅ L255-256
- [x] 1.3 SOP 新增「u2 交互陷阱」小节（6 条）✅ L258-267
- [x] 1.4 SOP 新增「像素亮度差判定」方法论小节 ✅ L269-271
- [x] 1.5 SOP 新增 L1/L2/L3 完成级别权威定义小节 ✅ L273-281
- [x] 1.6 known_issues.md 补 [已知-009]「验证空炮」条目 ✅ L112-119
- [x] 1.7 README.md 清理失效引用+V5 章节改归档说明+specs 链接修正（指向 archive 真实路径）+reports 结构如实描述+新增「脚本族索引」小节 ✅
- [x] 1.8 ai_e2e_testing_workflow.md 路径修复 ✅（实测 4 处非预估 3 处，全修）
- [x] 1.9 同 1.1（新增 3 脚本已含于补登清单）✅

## 2. 批次B 编排层接入

- [x] 2.1 run_e2e.py --feedback 接入 ✅（移除 L201-204 降级提示；主流程新增 [9.6] FeedbackLoop.process（report.json 落盘后，try/except 全隔离）；冒烟实证 [9.6] 触发+regression_history.md 追加）
- [x] 2.2 affected_modules 传 diff_result ✅（L359 提升函数级变量；L533 条件传递）
- [x] 2.3 test_run_e2e.py 断言核查 ✅（AOAdapt-2：实测断言仅校验返回 None 与新行为兼容，无需修改，295 全绿实证）
- [x] 2.4 冒烟五件套验证 ✅（report_20260830_145651：4 常规件落盘；affected_modules/feedback_suggestions 为条件产物按 AD-05 前提，生成函数单测覆盖×5）

## 3. 批次C 用例解析修复

- [x] 3.1 删除 case.md.seg2/.seg4 纯残留 ✅（穿透实测 TC-ID 100% 重叠；F-UI-THEME 59 条解析零回归）
- [x] 3.2 F-P1-8 TC 头修复 ✅（AOAdapt-1：第二层根因=缺冒号非层级；#### → ### ×16 + 补冒号 ×16；同型缺陷波及 P1-C4 文件 ×16 一并修复 + TC-ID 加模块前缀消跨文件冲突，dup 26→10）
- [x] 3.3 解析基线复跑 ✅（total 340→372，+32 条找回；F-UI-THEME 59 零回归）

## 4. 批次D scripts 删除治理

- [x] 4.1 删除 diag_* 13 个 ✅（用户检查点确认"全部删除"）
- [x] 4.2 删除 V5 残留 7 个 ✅
- [x] 4.3 删除站点一次性脚本 11 个 ✅
- [x] 4.4 删除重复版本链旧版 21 个 ✅（scripts/ 205→153）
- [x] 4.5 引用复核 ✅（0 文件残留；components-capability-inventory.md 20 处文档残留引用清理：删 2 节+17 行+改写 2 行+计数修正 4 处）

## 5. 批次E 验证

- [x] 5.1 pytest 全量 ✅（295 passed ×2 轮：批次 B/C 后+批次 D 后，删除零隐性依赖）
- [x] 5.2 run_e2e 冒烟 ✅（TC-F-P0-1-01 pass@confidence85 + [9.6] 经验回流触发 + 372 条解析生效）
- [x] 5.3 SOP/README/scripts 三方交叉核查 ✅（SOP 7 行补登实存；README 0 失效引用；components 文档 0 残留）
- [x] 5.4 F-UI-THEME 补「关联 Activity」评估 ✅（结论：65 条×逐条映射工作量大且用例为 VL 判定型走 ui_visual_verify 聚合，登记后续独立批次，不阻塞本任务验收）

## 6. 收尾

- [x] 6.1 INDEX/tasks/README 状态流转 ✅
- [x] 6.2 经验沉淀 ai_memory_main ✅（含 Grep 复核）
- [x] 6.3 检查点汇报 ✅（检查点 2/3 合并）

## AOAdapt 日志

### AOAdapt-1（3.2 第二层根因+F-P1-8 修复波及面扩大）
- Action: 按 design 预设将 #### TC 头改 ### 层级
- Observation: 解析数仍 0——第二层根因=TC_HEADER_RE 要求 `TC-ID：标题` 带冒号，该文件为空格分隔；全目录扫描发现同型缺陷波及 P1-C4 文件（16 条），且两文件 TC-ID 均为 TC-01 格式存在跨文件冲突
- Adapt: 补冒号 ×32 + TC-ID 加模块前缀（TC-F-P1-8-xx / TC-P1-C4-xx）消冲突（dup 26→10）；找回用例 +32 而非预估 +16

### AOAdapt-2（2.3 断言更新豁免）
- Action: 按 design 改动点 1.5 预备更新 test_handle_v3_feedback_warning 断言
- Observation: 该断言仅校验返回 None，与"移除警告块后仍返回 None"的新行为兼容
- Adapt: 无需修改断言；pytest 295 全绿实证；design 预估"必现红"过度保守已记录

### AOAdapt-3（4.x DeleteFile 超时但生效）
- Action: DeleteFile 工具一次删 52 文件
- Observation: 工具报 IDE 超时错误，但实际已删 29 个
- Adapt: PowerShell 补删剩余 23 个；存在性复核 0 残留（52/52 删净）

### AOAdapt-4（components-capability-inventory.md 额外残留）
- Action: 4.5 引用复核仅计划覆盖 SOP/README
- Observation: 扩大扫描发现 components-capability-inventory.md 有 20 处已删脚本引用（初盘点仅识别 README 13 处失效引用）
- Adapt: 纳入清理范围，子代理删 2 节+17 行+改写 2 行+计数修正 4 处

### AOAdapt-5（同文件并发 Edit 竞态复现）
- Action: 批次 A 子代理对 components 文档执行编辑
- Observation: 子代理自报同文件多 Edit 同批次 6 处修改被覆盖丢失（自愈补回）
- Adapt: 印证"同一文件 Edit 必须串行"铁律，沉淀提示后续编辑者
