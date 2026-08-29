# ui-theme-gap-audit 任务清单

> 执行说明：本任务只做"阶段 1 静态审计 + 阶段 2 测试用例设计"，不修改 `app/src` 源码。
> 子代理使用：分析阶段（Grep/Read 探索）🟡 推荐子代理；文档产出主代理 Write；遇问题记录 AOAdapt 日志。

## 1. 准备与技术基线

- [x] 1.1 管理面设置项提取 → `management-surface.md`（52 个 key：主色/扩展表面色/顶栏/主框架）✅ 2026-08-26
- [x] 1.2 审计判据矩阵 C1-C6 Grep 模式集（design §2 + issue-list-v0 固化，可重复执行）✅
- [x] 1.3 合理例外清单（封面占位色/正文可配置色/视频控制层品牌色/语义红绿蓝/Logo）✅
- [x] 1.4 task-navigation 14 模块锚点 + ui/widget 组件清单确认 ✅
- [x] 1.5 功能清单（features-inventory v1：F1-F31 + P1-P14 流程 + S-P1~P5 场景）+ 页面清单（pages-inventory v2 分层 L1-L6）✅
- [x] 1.6 处置全集 A1-A8 与预期生效面确认（design §2.5）✅
- [x] 1.7 流程/场景级清点（P1-P14 环节链+处置+脱节风险点 + 场景组合 + 流程×页面交叉）✅

## 2. 静态审计（判据扫描 + 核验，逐页不落）

- [x] 2.0 分层清点覆盖源（L1-L6 全量）—— ⚠️ 逐页覆盖状态随用例设计推进填写
- [x] 2.1 C1/C2 硬编码颜色：Kotlin 116 处/36 文件 + XML 640 处/100 文件（剔除 370 调色板后 ~210 处布局/drawable）✅ → G3/G9/G10/G11
- [x] 2.2 C3 硬编码圆角：`RoundedCornerShape` 321 处/84 文件 → 直接魔数 **47 处** ✅ → G2
- [x] 2.3 C4 硬编码字号：`fontSize = N.sp` **678 处/96 文件** ✅ → G1
- [x] 2.4 头部审计：MainTopBarView 三模式覆盖多数子页；**BookSourceEdit/BookSourceDebug 头仍旧 TitleBar+PopupMenu** ✅ → G8
- [x] 2.5 菜单/弹框族：**ModernActionPopup 8 处 vs PopupMenu 残留 9 处**；**BaseDialogFragment 残留 ~20 个** vs ComposeDialog 家族 ✅ → G6/G7
- [x] 2.6 底部弹层/搜索框/卡片：AppModalBottomSheet 族 + popup_ XML 5 + 搜索框 18dp（bugfix ② 已统一，登记核查）✅
- [x] 2.7 主题联动：ThemeSync.bump 为主 + RECREATE 为辅；盲区=**调试工具 7 页（AppCompatActivity）** + **View 型弹窗 9 个未包 LegadoTheme** + 沉浸豁免阅读子页 ✅ → G4/G5
- [x] 2.8 4 子代理核验（圆角/字号/联动/布局色）+ 主代理归并 → **问题清单 v0**（11 条：P0×3 / P1×6 / P2×2，含源码定位+修复方案）✅ 落盘 `issue-list-v0.md`

## 3. 测试用例设计（ai_tests + VL，逐页不落）

- [x] 3.0 页面覆盖矩阵→用例映射（L1-L6 ↔ 用例表在 case.md 附录，"无法触达页面"登记机制建立）✅
- [x] 3.1 `ai_tests/cases/F-UI-THEME/case.md` 骨架（TC-F-UI-THEME-xxx + 验证法 [UI]/[VL]/[联动]）✅ 2026-08-26
- [x] 3.2 逐页样式呈现用例组：主框架/书架/书源/订阅/发现/RSS/播放器/下载/设置/AI/调试/主题页（020-100）✅
- [x] 3.3 **处置前后联动用例组 A1-A8**（before/after 对账 + prefs 断言）✅ 001-008
- [x] 3.4 经典/新版切换用例组：TC-007（无残留 + 结构性问题核）✅
- [x] 3.5 VL 判定协议落地：`ai_tests/lib/ui_visual_prompt.py`（SYSTEM_PROMPT + chat_json Schema + 三图采样 + 校准标准）✅
- [x] 3.6 `ai_tests/scripts/ui_visual_verify.py`（证据扫描→送审→issues 聚合→与 v0 对账入口）✅
- [x] 3.7 **流程全链穿行用例组 P1-P14**（TC-110~123）✅
- [x] 3.8 **场景组合用例组 S-P1~P5**（TC-130~134）+ 流程×页面交叉 ✅

## 4. 验收与门禁

- [x] 4.1 🛑 检查点 1（AskUserQuestion）：用户审查四文档（设计方案/替代方案/已知缺点），确认后 README 状态 → "✅ 设计完成"（2026-08-26 通过）
- [x] 4.2 更新 `docs/INDEX.md`（活跃 Specs 登记，🔄 设计中 → 按进度换标记）
- [x] 4.3 验证：`run_e2e.py --help`/`case_parser` 单测跑通新模块解析（不连真机）；确认无 `app/src` 变更
- [x] 4.4 文档同步：`docs/project-flow/ui-standards/migration-registry.md` 登记审计产出；`updateLog.md` 按规则登记（如涉及）
- [x] 4.5 🛑 检查点 2（AskUserQuestion）：用户审核问题清单 v0 + 用例集（三选项：通过 / 需调整 / 拒绝回退）（2026-08-26 通过）
- [x] 4.6 本次阶段完成存档：经验沉淀（spec-sedimentation-mechanism）

## 后续轮次（阶段 3，2026-08-26 已执行 ✅）

- [x] 5.1 R1 全量执行 `--tc F-UI-THEME`（report_20260826_154627）→ 问题清单 v1（R1-01 CursorWindow 溢出 → 已修复；R1-04/05/06 复核关闭；R1-02 锚点已校准）✅
- [x] 5.2 修复轮（G1-G11）：G1 字号/G2 圆角/G4 调试主题联动/G5 弹窗包主题/G7 菜单/G8 书源编辑调试头 全部修复；G3 并 video-player-theme-unify（已完成）；G6/G9/G10/G11 评估=合理存量/豁免登记 → issue-list v2 ✅
- [x] 5.3 R2 全量复测（report_20260826_204811，52 条）：fail=0 / warning=0 / VL 无新候选 ✅
- [x] 5.4 R3 修复面专项（TC-071/041/081 步骤全过）+ case.md 锚点校准 + logcat 计数=0 → issue-list v2 闭环 ✅

---

## AOAdapt 日志

- [ ] 2.8 (AOAdapt) Action: 生成 case.md 初版（134 条标注，含"一行断言"精简格式） | Observation: `CaseParser.parse_file` 实测仅解析出 13 条 TC，且仅 1 条含步骤（STEP_RE 按行匹配，精简/合并行格式无法解析）| Adapt: 重构 case.md 为 parser 兼容格式（每条含 关联源码/前置资源/测试步骤(逐行)/预期结果(逐行) 四段），页面呈现改为批量覆盖组（55 条结构 TC 覆盖 001-134 编号空间），实测解析 55 条全部四段齐全（前置仅 AI自备/共享）→ 结论沉淀：**测试用例文档必须用真实解析器验证可执行性，禁止只做文档自洽**
- [ ] 2.8 (AOAdapt) Action: 自查阶段 2 交付 | Observation: 0 用户指出"再给你一次自查机会"；自查发现 4 缺陷（可执行性/三映射/种子预案/校准闭环）且首轮修补后仍未验证 parser 兼容 | Adapt: 二轮自查补"真实解析验证 + 种子脚本 Glob 确认 + G5/G7 触发路径逐一化（弹框/菜单家族核不再抽查）"，全部落盘后复验通过