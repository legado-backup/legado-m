# ui-style-unify-deep-fix 需求规格

## Intent

用户任务开始时明确提出的核心问题——**子页面风格不统一（头部样式、弹框样式）+ 订阅源经典/新版切换结构性问题**——在上轮 ui-theme-gap-audit 中经静态分析（G1-G11）+ R1/R2/R3 多轮测试均未被发现，用户明确不满意（"我真的这么 low 么"）。

根因：上轮静态审计判据 C1-C6 只覆盖"硬编码色 / 硬编码圆角 / 硬编码字号 / View 直写色值 / 误用 MaterialTheme / 不订阅主题事件"六类**微观颜色维度**，无法发现"**同类页面/组件采用了不同实现组件**"的宏观风格分裂。G6 更将 38 个 BaseDialogFragment 旧 View 弹框直接"评估为合理存量保留"，完全避开了用户要的"弹框样式统一"。

**第二轮实锤复盘（H9，2026-08-27 用户补刀）**：用户实锤"精准管理页主页面样式与主页面不一致"。静态排查确认根因——精准管理页根容器用 `MaterialTheme.colorScheme.surface`（M3 派生色，lerp 偏移非 backgroundColor 直读）做页面背景，而主设置页全部用 `palette.settings.page = Color(context.backgroundColor)`（ThemeStore 直读）。**为何上轮仍漏**：C5"误用 MaterialTheme"判据未区分"M3 派生色"与"主题背景色直读"——凡写 `MaterialTheme.colorScheme.xxx` 一律判为"已随主题"，实际 M3 surface 是 bg 向 neutral 偏移 4-10% 的派生色，不随主题设置背景色变化。且 F-UI-THEME 用例集缺"所有管理页/设置页根容器背景一致"的断言维度。

本任务采用**组件级全盘盘点**（3 排查子代理已完成）+ **主代理逐文件根容器核实**，识别全部风格分裂实例，输出可执行问题清单，一次测全量 → 一次修复 → 复测，最终实现全 App UI 风格统一。

## Scope

### In Scope（本条）

1. **H 头部+菜单样式统一**：全 App Activity/Fragment 顶栏实现 + 三点菜单实现盘点与统一，消除 14 类问题（H1-H14）：
   - H1 管理页双体系形态差异（MainTopBarView 56dp vs AppManagementScaffold 48dp，已确认均纳管，登记）
   - H2 ConfigActivity 自绘顶栏注释与实现不符（已确认已纳管，仅注释）
   - H3 Compose 自绘顶栏未纳管孤例（AiChat 硬编码黑背景 / MyFeatureBooks 原生 M3 / 原生 Toolbar）
   - H4 旧 TitleBar 残留（ReadRecord/S3Container/LibraryContainer/AiImageProviderEdit）
   - H5 原生 M3 TopAppBar / 原生 Toolbar 孤例（并入 H3）
   - **H6 设置宿主页 ConfigActivity 头部黑色 + 三点菜单系统样式（用户实锤）**：ConfigTopBar 无 background + 隐藏 Toolbar+MenuProvider 系统菜单
   - **H7 其余可见系统菜单样式点**：漫画阅读菜单 / 发现页经典模式（系统 Toolbar 溢出菜单）+ 管理页 onCompatCreateOptionsMenu 残存清理
   - **H8 AppDropdownMenu（M3 原生）菜单体系 44 文件（原记 38，2026-08-27 复查修正）与主流 ModernActionPopup 不一致（用户实锤）**：替换规则编辑页/字典规则页等所有 Compose 次级页面；含替换净化/字典页头部不随顶栏管理
   - **H9 精准管理页背景色未纳管 + SettingsCard/SettingsClickRow 组件体系分裂（用户实锤）**：根容器用 M3 surface 派生色（非 backgroundColor 直读）；SettingsCard/SettingsClickRow 用 M3 派生色，与主设置页 appSettingPanelBackground 调色板体系不一致（同类使用点 5 文件 13 处）
   - **H10 列表项 M3 派生色归位**：DictRule/Highlight/Download 列表项 + ListCard 默认色（colorScheme.surface/onSurface）→ AppSettingPalette 直色（palette.settings.row），对齐管理页 AppManagementCard（H9 同源同批治理）
   - **H11 6 页列表项卡片 M3 surface 归位**（主代理 2026-08-27 修正原判"根背景"不实）：AutoTask/TxtTocRule/AllBookmark/Highlight/DictRule/RecycleBin **列表项卡片**（`Surface(color = MaterialTheme.colorScheme.surface)`）→ `palette.settings.row`（与 H10 同源合并治理；根背景 M3 surface 仅 PreciseManage 1 页归 `palette.settings.page`）
   - **H12 Debug 8 页 M3 TopAppBar 归位**：Debug 家族 7 页 + MyFeatureBooks 裸 M3（secondary 色脱离主色体系）→ GlassTopAppBar（primaryColor）+ LegadoBackgroundBox 兜底色改 page 直色
   - **H13 GlassTopAppBar 接入 TopBarConfig**（2026-08-27 用户裁决接入）：与 MainTopBarView 对齐，消费壁纸/背景色/圆角/透明度
   - **H14 角色系列 4 页底色硬编码**：BookCharacterManage/Edit/Card/Relation（page `if (night) md_grey_900 else white` + card/cardAlt/stroke 硬编码十六进制，不读主题背景色）→ palette 直读（page→settings.page、card/cardAlt→UiCorner.surfaceColor(themeUiPalette.cardColor)、stroke→palette.divider；矩阵逐页核实发现）
2. **D 弹框样式统一**：全 App 弹框实现盘点与收敛，消除 5 套视觉体系：
   - D1 BaseDialogFragment 旧 View 弹框 36 个（+BasePrefDialogFragment 2）→ 全部入迁移队列（撤销上轮 G6"存量保留"判定），分优先级迁移 ComposeDialogFragment
   - D2 系统 AlertDialog（alert{} DSL 71 文件 162 处 + 内联 9 处；主代理复核 `import lib.dialogs.alert` = 76 文件，实施前 grep 复核）→ 收敛到 ComposeConfirmDialog 族
   - D3 Import 系列 7 个 + M3 @Composable 5 组件（AppConfirm/AppEdit/AppText/SingleChoice/Confirm）material3 默认风格 → 对齐 AppDialogFrame
   - D4 散点弹框 13 个（raw Dialog/BottomSheet/ComponentDialog/AlertDialog+ViewBinding）→ 迁移或登记
3. **S 订阅页经典/新版切换结构修复**（6 个遗留）：
   - S1 updateRssSourceNameWidth layout 监听跨模式残留（无 guard）
   - S2 切换依赖 onResume 兜底、RssFragment 不监听 NOTIFY_MAIN 事件
   - S3 classic 运行时状态（currentGroup/currentType/selectedRssTag）切回后未重置
   - S4 rssTopOverlaySpace/rssTopOverlayEnabled 跨模式旧值
   - S5 classicHeaderReady 一次性标记永久驻留
   - S6 sortHostViewModel 跨模式保留旧源状态
4. **主题纳管判定**：对每个组件/弹框判定全部样式参数是否被"主题设置/界面设置"统一管理（✅已纳管/⚠️部分纳管/❌未纳管），禁止"豁免/存量"跳过未纳管项
5. 组件级一致性问题清单 + 同类页面一致性矩阵（页面类型 × 头部 × 弹框 × 菜单 × 主题联动）
6. 真机/模拟器全量复测（复用 F-UI-THEME 用例集 + 新增组件级一致性用例）

### Out of Scope（不在本条）

- **不做**：整体迁移 Archive UI、重新设计组件库、引入新 UI 框架
- **不做**：阅读器内核（ReadBookActivity/ReadMangaActivity 沉浸式）样式改造（S5 View 红线）
- **不做**：视频播放器手势交互体系改动（保留上下滑切视频+左右滑 seek+长按倍速+双击暂停）
- **不做**：功能逻辑 / 数据 / 网络层改动（仅样式与组件收敛）
- **不做**：G1-G11 已完成的微观 token 化回退（本任务在之上叠加宏观统一）

## Approach

### Selected Approach：组件级盘点 + 主题纳管判定 + 双基线收敛 + 状态机修复（四步法）

1. **组件级全盘盘点**（已完成）：3 排查子代理并行，按"类名→文件路径→实现方式→是否随主题"四维盘点头部/弹框/订阅切换，产出可执行改造清单。
2. **主题纳管判定（核心判据，替代上轮 C1-C6）**：对每个页面/组件/弹框，判定其全部样式参数（背景色/文字色/按钮色/圆角/字体/间距/状态色）**是否都能被"主题设置/界面设置"统一管理到**（管理面 = 主色体系 / 扩展表面色 / 顶栏管理 TopBarConfig / 圆角倍率 / 字号体系 / 夜间日间 / 墨水屏 E-Ink / 弹框族规范）：
   - ✅ **已纳管** = 全部样式参数均从主题体系读取 → 保留
   - ⚠️ **部分纳管** = 仅部分参数随主题（如仅背景色）→ 补齐缺口
   - ❌ **未纳管** = 硬编码 / 系统默认 / 不读主题 → 必须修复
   - **禁止以"豁免/合理存量"为由跳过未纳管项**；仅在"语义色（Danger 红等属于主题语义体系内）"、"媒体内容画布（非 UI 控件）"、"阅读器正文可配置色（阅读器独立配色体系，属于阅读设置管理面）"三类情形才可登记"主题体系外"，且必须说明该色由哪个设置项管理。
3. **双基线收敛**：确立两个主流目标风格——View 体系头部 = `MainTopBarView(SUB)`（已 24 子页 + 5 主 Tab，纳管最全含顶栏管理）；Compose 体系头部 = `GlassTopAppBar`（已 ~40 页面）；弹框 = `ComposeDialogFragment` + `AppDialogFrame`（已 49 个，全纳管）。所有孤例/分裂实例向就近基线对齐，**同类页面必须用同类组件**。
4. **订阅切换状态机修复**：为 6 个结构性遗留分别加 guard / 重置 / 事件监听 / ViewModel 隔离，确保切换即时生效、无跨模式残留。

### 判定依据说明（回应"凭什么判定不改"）

上轮 G6 将 38 个旧 View 弹框判定"已主题化 View 存量"保留——**该判定错误**：旧弹框仅 `view.setBackgroundColor(ThemeStore.backgroundColor())` 联动背景，按钮/列表/输入框/文字色均固定硬编码，**不能被主题设置统一纳管**，故必须迁移。本任务所有"保留"决策必须满足"已纳管"或"主题体系外（说明由哪个设置项管理）"，否则一律列入修复。

### Alternatives Considered

| 方案 | 否决/接受理由 |
|------|-------------|
| A. 全量迁移到 Compose 体系（一劳永逸） | **否决**：波及 98 Activity + 208 XML 布局，成本高、回归风险大；View 体系（MainTopBarView）已成熟且用户无"全 Compose"诉求 |
| B. 全量回退到 View 体系 | **否决**：Compose 化是既定方向（GlassTopAppBar 已 40 页），回退是倒退 |
| C. 双基线收敛（选定） | **接受**：View 页面用 MainTopBarView、Compose 页面用 GlassTopAppBar，同类页面统一到同基线，消灭孤例；成本可控、符合迁移方向 |
| D. 继续用 C1-C6 色值判据扫描 | **否决**：上轮已证伪——抓不到"同类页面用不同组件"的结构性分裂；必须组件级盘点 |
| E. 36 个旧弹框全量立即迁移 | **否决**：其中部分（WaitDialog/PhotoDialog/CodeDialog 等）被多页复用且场景特殊；先分优先级，高可见/高频优先迁移，低频评估 |

### Drawbacks（选定方案已知缺点 + 接受理由）

| 缺点 | 程度 | 接受理由 / 缓解 |
|------|------|---------------|
| 双基线并存（View/Compose 两套头部）本身仍是"两种风格" | 中 | 技术栈天然两分（View 页面无法用 Compose 组件）；目标不是"单一组件"而是"同类页面同组件"；用户痛点是不统一/无规律，非"必须单一样式" |
| 38 个旧弹框迁移面大，回归风险高 | 高 | 分优先级：P0 高可见（弹框家族一致性用例涉及）优先，P1/P2 分批；每批编译+真机复测；部分评估保留存量并登记理由 |
| alert{} DSL 60+ 处迁移工作量大 | 高 | 优先迁移用户可见高频弹框（确认/单选/多选/输入）；其余登记保留并统一视觉（若可行走 compose 风格 wrapper） |
| 订阅切换修复涉及运行时状态机 | 中 | 6 个遗留各自独立可测；修复后必须真机验证经典↔新版反复切换无残留 |

### Prior Art

- `docs/specs/ui-theme-gap-audit/` — 上轮 G1-G11（微观 token 化），本任务在之上做宏观统一
- `docs/project-flow/ui-standards/migration-registry.md` — Archive 对齐迁移登记表（弹框/列表迁移状态）
- `docs/project-rules/frontend-ui-standards.md` — 前端 UI 强制基线（S1-S6 骨架/组件六族/设计 Token）
- `ai_tests/cases/F-UI-THEME/case.md` — 既有 52 条样式用例（复用 + 新增组件级一致性用例）

## Requirements

### 功能需求

- **FR-1 组件级盘点清单**：头部/菜单/弹框/订阅切换全盘盘点，每项含类名+文件路径+实现方式+是否随主题，落盘 issue-list.md
- **FR-2 主题纳管判定**：对每个组件/弹框判定全部样式参数是否被主题设置统一管理（✅已纳管/⚠️部分纳管/❌未纳管）；禁止"豁免/存量"跳过未纳管项；"主题体系外"须说明由哪个设置项管理
- **FR-3 同类页面一致性矩阵**：页面类型 × 头部实现 × 弹框实现 × 菜单体系 × 主题联动五维矩阵，逐格标记"已统一/待统一/登记豁免"，交付覆盖率核对表
- **FR-4 头部统一**：未纳管孤例（ConfigActivity 无背景/AiChat 硬编码/MyFeatureBooks 原生 M3/原生 Toolbar/旧 TitleBar）全部修复，随主题+顶栏管理
- **FR-5 菜单统一**：四套菜单体系收敛到 ModernActionPopup 视觉基线——AppDropdownMenu 渲染层对齐（38 调用点零改动）、系统 Toolbar 菜单 4 处收敛、清理死代码
- **FR-6 弹框收敛**：36 旧 View 弹框（+BasePrefDialogFragment 2）全部入迁移队列迁移 ComposeDialogFragment；系统 AlertDialog（71 文件）收敛 ComposeConfirmDialog 族；M3 @Composable 5 组件 + Import 系列对齐 AppDialogFrame；散点 13 迁移或登记
- **FR-7 订阅切换状态机**：S1-S6 六个遗留全部修复——监听加 guard、状态重置、事件即时生效、ViewModel 隔离
- **FR-8 一次修复+复测**：按问题清单一次修复 → R1 全量复测（F-UI-THEME 52 条 + 新增组件级用例）→ R2 终测，fail=0
- **FR-9 组件单一来源治理**（用户二次质疑根治，四阶段路线图见 AD-08）：六类组件（顶栏/菜单/弹框/设置卡片/列表项/根背景）收敛到单一权威实现 + 单一取色来源（AppSettingPalette/AppDialogStyle/UiCorner 直读）；**禁止 Compose 页面级/卡片级用 M3 colorScheme 派生色做视觉取色**；ModernActionPopup 0 调用死代码版删除（消除同名双实现）；四阶段：取色源统一 → 根背景+顶栏收敛 → 弹框分批迁移 → 机制防回潮；新增代码门禁（Grep 检查 M3 surface 新增即拒）

### 非功能需求

- **NFR-1** 不破坏已完成的 G1-G11 token 化成果
- **NFR-2** 不破坏视频播放器手势交互体系（真机验证）
- **NFR-3** 不引入新依赖 / 新 UI 框架
- **NFR-4** 输出安全：问题清单/报告不输出源名称/域名/URL/cookie（遵守 output-safety.md）
- **NFR-5** 每批修复后编译通过 + 无调试日志残留

## Scenarios

- **S-1 头部一致**：任意子页面头部颜色/高度/返回箭头随"主题设置+顶栏管理"变化（含设置宿主页 ConfigActivity、替换净化、字典规则等此前不随的页面）
- **S-2 菜单一致**：任意页面右上角三点菜单打开后卡片/圆角/取色一致（主界面与 Compose 次级页均为同一 ModernActionPopup 视觉），随主题切换
- **S-3 弹框风格一致**：任意弹框（确认/单选/多选/输入/帮助/日志）打开后卡片/按钮/圆角/取色一致，均随主题切换
- **S-3b 页面背景一致**：任意管理页/设置页/精准管理页根容器背景 = `palette.settings.page`（ThemeStore 背景色直读），设置主题背景色后全部页面同步变化，无 M3 派生色偏色
- **S-3c 设置组件一致**：SettingsCard/SettingsClickRow 卡片/文字/标题色与主设置页 appSettingPanelBackground 体系一致（同调色板取色），5 文件 13 处全量回归
- **S-4 订阅切换无残留**：订阅页经典↔新版反复切换，标题宽度不被钳制、分组/类型筛选不残留、顶栏 overlay 正确
- **S-5 切换即时生效**：设置页改"订阅页模式"后返回订阅页立即切换（不依赖冷启动/onResume 偶然触发）
- **S-6 回归不破坏**：G1-G11 字号/圆角/主题联动成果、视频播放器手势全部保持

## 轮次协议

```
R0 前置：3 排查子代理盘点（已完成）→ 问题清单 issue-list.md
R1 一次修复：按 tasks.md §0 权威执行顺序表（S → Phase1 取色源 → Phase2 根背景+顶栏 → Phase3 弹框）逐项修复（主代理串行源码修改）
R2 全量复测：run_e2e --tc F-UI-THEME + 新增组件级一致性用例 → fail=0
R3 终测 + 回归：订阅切换专项 + 视频手势回归 + G1-G11 成果回归
验收：用户确认
```
