# UI 风格统一深度修复（ui-style-unify-deep-fix）

> 状态：🔄 设计中（2026-08-27）

## 功能概述

用户对 ui-theme-gap-audit 本轮测试+修复不满意——任务开始时明确提出的"**子页面风格不统一（头部样式、弹框样式）+ 订阅源经典/新版切换结构性问题**"，经静态分析+多轮测试均未发现。根因：上一轮 G1-G11 只从"硬编码色/字号/圆角"微观视角处置，**没有做组件级盘点**，未触及"同类页面用了不同组件/不同视觉体系"的结构性不统一；且上轮 G6 将 38 个旧 View 弹框"评估为存量保留"、G7 只清 View 体系 PopupMenu 未覆盖 Compose 菜单体系，均绕开了用户要的"风格统一"。

本任务基于组件级全盘盘点 + 用户实锤回填，聚焦三大真实问题域，一次测全量 → 一次修复 → 复测：

| 问题域 | 现状 | 目标 |
|--------|------|------|
| **H 头部+菜单统一** | 顶栏 8 种 + 菜单 3 活跃（ModernActionPopup 23 / AppDropdownMenu **44 文件**=39 import+5 同包 / 系统 Toolbar 可见 4 + 残存 7）+ 头部未纳管孤例（ConfigActivity 无背景黑色、AiChat 硬编码黑、MyFeatureBooks 原生 M3、Debug 8 页 M3 secondary 色、旧 TitleBar 残留）+ M3 派生色（根背景 1 页 PreciseManage + 列表项卡片 6 页 AutoTask/TxtToc/AllBookmark/Highlight/DictRule/RecycleBin） | 统一到 ModernActionPopup 视觉基线；头部全量随主题+顶栏管理；根背景/列表项卡片全量 palette 直色 |
| **D 弹框样式统一** | 5 家族并存（A 新 Compose 49 文件 / B 旧 View BaseDialogFragment 36(+pref2) / alert{}DSL 71 文件 162 处 / M3 @Composable 5 / D 散点 13） | 弹框收敛到 ComposeDialog 家族 + AppDialogFrame 风格，全部主题纳管 |
| **S 订阅切换结构修复** | 经典/新版切换存在 6 个结构性遗留（监听跨模式残留/状态未重置/事件兜底） | 切换无残留、状态正确重置、事件即时生效 |

## 核心能力

- **主题纳管判定（核心判据）**：对每个组件/弹框判定全部样式参数是否被"主题设置/界面设置"统一管理（✅已纳管/⚠️部分纳管/❌未纳管）；**禁止以"豁免/合理存量"跳过未纳管项**（撤销上轮 G6 对旧 View 弹框的错误判定）
- **组件级全盘盘点**：头部/弹框/订阅切换 + **菜单承载方式/组件体系**三维度盘点（已发现四套菜单体系），产出可执行改造清单
- **菜单统一基线**：ModernActionPopup（自绘圆角卡片 + LegadoMiuixChoiceRow + AppDialogStyle，全主题纳管）为统一目标；AppDropdownMenu（M3 原生）渲染层对齐（38 调用点零改动）；系统 Toolbar 菜单可见 4 处收敛 + 残存 7 处清理
- **头部收敛基线**：View 体系 = MainTopBarView(SUB)；Compose 体系 = GlassTopAppBar；管理页 = AppManagementScaffold（已纳管）；消灭 ConfigActivity 无背景/自绘/原生/旧 TitleBar 孤例
- **弹框收敛基线**：ComposeDialogFragment + AppDialogFrame/AppDialogStyle（随主题联动主流风格）
- **组件单一来源治理（FR-9/AD-07）**：六类组件（顶栏/菜单/弹框/设置卡片/列表项/根背景）收敛到单一权威实现 + 单一取色来源（AppSettingPalette/AppDialogStyle/UiCorner 直读）；禁止 Compose 页面级/卡片级用 M3 派生色；ModernActionPopup 0 调用死代码版删除（消除同名双实现）；新增代码门禁防回潮
- **彻底统一四阶段路线图（AD-08）**：①取色源统一（M3 派生组件归位直色 + AppDropdownMenu 渲染层对齐）②根背景+顶栏收敛（根背景 M3 surface：PreciseManage 1 页归 page + 列表项卡片 6 页归 row + Debug 顶栏 + ConfigTopBar 背景 + 角色系底色）③弹框分批迁移（36 旧 View+pref2 + alert 71 文件 + M3 5 组件收口 + 散点 13）④机制防回潮（Grep 门禁 + 取色同源断言 + 矩阵常驻）
- **组件体系实现树 + 页面完整性矩阵**：落盘 docs/temp-analysis/（顶栏 8 种/菜单 3 活跃/弹框 5 家族/卡片三族 + **125 页五维矩阵** + 弹框家族归属表），FR-3 交付依据
- **订阅切换状态机修复**：监听 guard + 状态重置 + 事件即时生效 + ViewModel 隔离
- **一次测全量 → 一次修复 → 复测**：承接 ai_tests F-UI-THEME 用例集，新增组件级一致性断言

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach 含 Alternatives + Drawbacks / Requirements / Scenarios）
- [design.md](./design.md) — 技术设计（组件盘点结论 / 主题纳管判定 / 菜单体系 / ADR / 文件变更）
- [tasks.md](./tasks.md) — 任务清单（`- [ ] X.Y` 格式）
- [issue-list.md](./issue-list.md) — **问题清单**（H1-H14 头部+菜单+背景+列表项+角色系 / D1-D4 弹框 / S1-S6 订阅切换，含源码定位+修复方案+优先级）

## 状态标记

- [x] 需求分析（组件级盘点 + 用户实锤回填 H6/H8/H9 + 四套菜单体系识别 + AD-06 取色基线）
- [x] 全页面矩阵交付（125 页逐页 Read 核实 + 118 弹框家族归属，FR-3）✅
- [x] 四文档生成 + 问题清单（含源码定位 + 修复方案 + 优先级 + 主题纳管判定）
- [x] 检查点 1：用户审查通过（2026-08-27，含 H11 修正/D1 补漏/H14 扩展）→ **设计+规范双文档深度审查通过（2026-08-27 14:03，文档进度标注 ↔ 源码实况一次性对齐回填）**
- [x] 一次修复（已完成：S 批 S1-S6 + Phase 1 全量（H8 渲染层/H9 组件/H10/死代码清理）+ Phase 2 部分（H6/H9 根背景/H11 5 页/H13/H14））
- [ ] 一次修复剩余：H12（Debug 7 页）/ H7（漫画/发现经典菜单）/ H3（AiChat）/ H5 / H4 / H11 剩 TxtTocRule / H1/H2 + D1-D4 弹框分批
- [ ] R1 全量复测 → R2 终测
- [ ] 用户最终验收
