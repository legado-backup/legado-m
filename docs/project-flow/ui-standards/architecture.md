# UI 设计架构体系（总纲）— AI 前端开发必读

> 目录：`docs/project-flow/ui-standards/architecture.md`
> 更新：2026-08-27（基于 ui-style-unify-deep-fix 深度审计：125 页逐页矩阵 + 118 弹框家族核实 + AD-07/AD-08 单一来源治理）
> **本文件是 AI 做本 App 前端 UI 改造的必读总纲**。新增/修改任何 UI 前必须先读本文件与下表文档，禁止私自拉新组件、私有样式、硬编码色号、脱离主题设置体系。

## 一、定位与铁律

出现问题根因：历史上多次"深度分析发现问题 → 修复 → 不沉淀规范"，导致新代码继续引入同类分裂（同类页面不同组件/不同取色/弹框各搞一套）。**本目录文档即防回潮机制（AD-08 Phase4）的常驻部分**。

三条铁律（违反 = 代码审查不通过）：

1. **禁止硬编码色号**：UI 代码禁止直接写 `Color(0xFF...)` / `Color.BLACK` / `Color.WHITE` / `R.color.md_*`（豁免类：语义 Danger 红、媒体画布、阅读正文可配置色、视频控制层——均须在所登记的"主题体系外"清单说明由哪个设置项管理）。
2. **禁止绕过取色基线**：新组件/新页面必须从下述**取色唯一基线**取色，禁止 `MaterialTheme.colorScheme.surface/surfaceVariant/onSurface` 做页面级/卡片级视觉取色（M3 派生色是 lerp 偏移色，不随主题背景色直读——H9/H11 教训）。
3. **禁止自造组件形态**：同类组件必须复用下述**四大组件族基线**，禁止新造同名/同语义组件（顶栏自绘 Row、菜单自绘、弹框 XML/alert{} DSL、列表 M3 卡片均为违例）。

## 二、应用主题体系全景

| 层 | 说明 | 关键文件 |
|----|------|---------|
| 设置入口 | 「设置-界面-主题」themeMode 切换日/夜/跟随系统；「界面设置」面靠色 key 组；「顶栏管理」TopBarConfig | `ui/theme/LegadoTheme.kt`、`ui/dialog/LegadoDialog.kt` 等 |
| 状态源 | `AppConfig` + `ThemeStore`（`Colors`/`TopBarConfig`/背景色） | `data/appConfig/AppConfig.kt`、`base/BaseActivity.kt` |
| View 取色 | `ThemeStore.themeColors()` 直读 | `lib/theme/ThemeStore.kt` |
| Compose 调色板 | `ThemeUiPalette`（卡片/弱化/搜索框/Tab/书架/分隔线 6 面） | `lib/theme/ThemeUiPalette.kt` |
| 设置/管理调色板 | `AppSettingPalette`（page/row/文字/强调/danger/border/圆角/字体）+ `rememberAppSettingPalette()` | `ui/widget/compose/AppSettingComponents.kt` |
| 弹框/菜单面板 | `AppDialogStyle`（`rememberAppDialogStyle()`）+ `AppDialogFrame` + `UiCorner`（panelRadius/actionRadius/透明度/面板背景图） | `ui/widget/compose/AppComposeDialogs.kt`、`lib/theme/UiCorner.kt` |
| 圆角/字体 Token | `ComposePanelRadius`/`composeActionRadius`、`uiTypeface`/`titleTypeface` | `lib/theme/ComposeUiCorner.kt`、`lib/theme/UiTypography.kt` |

### 取色链路（权威）

```
主题设置 key（themeCardColor/themeMutedColor/cPrimary...）
  → AppConfig / ThemeStore（ThemeStore.themeColors()）
  → ① rememberAppSettingPalette()   → 页面/行/文字/强调（palette.settings.page = context.backgroundColor 直读）
    ② rememberAppDialogStyle()      → 弹框/菜单面板（AppDialogStyle + AppDialogFrame）
    ③ UiCorner                      → 圆角/透明度/面板背景图/边框
  → 组件渲染
```

**页面根背景唯一取色**：`palette.settings.page`（= `Color(context.backgroundColor)` = ThemeStore 直读）。**禁止** `MaterialTheme.colorScheme.surface`（M3 surface = lerp(bg, neutral, 4~10%)，主题改背景色后偏色——H9/H11 实测）。自定义 `Color` 主题色一律从「主题设置/界面设置」暴露为 key，禁止代码内固定色值。

## 三、四大组件族体系（View/Compose 双栈基线）

> 双栈并存是既定事实（View 存量 + Compose 演进方向），但**取色来源必须统一**；同类页面必须用同类组件。

### 1. 顶栏族（8 形态 → 3 基线）

| 基线组件 | 技术栈 | 适用 | 取色 |
|---------|--------|------|------|
| `MainTopBarView`（`ui/widget/MainTopBarView.kt`） | View | 主界面 5 Tab + 高阶子页（SUB 模式 56dp） | 完整消费 `TopBarConfig`（壁纸/圆角/背景色）+ ThemeStore |
| `GlassTopAppBar`（`ui/widget/components/GlassTopAppBar.kt`） | Compose | 功能页/子页（~40 页） | `containerColor ?: Color(context.primaryColor)` + barElevation；**H13 已实施（2026-08-27）：STYLE_REGULAR 顶栏包启用时消费 TopBarConfig 壁纸/圆角/背景色（对齐 MainTopBarView）** |
| `AppManagementTopBar`（`AppManagementScaffold.kt` 内私有） | Compose | 列表管理页（书源/订阅源/替换/规则等 5 页，48dp） | `AppSettingPalette` + themeUiPalette + UiCorner |

**已查明的待治理形态**（不得新增）：
- 自绘私有 Row 顶栏（AiChat/S3/Library/AiProvider/AiWorldBook/Relay/Toc 等 ~8 处碎片，互不共享）→ 并 AppManagementScaffold 或对齐视觉参数（H3/H4）
- M3 原生 `TopAppBar`（Debug 8 页 secondary 色 + MyFeatureBooks）→ GlassTopAppBar primaryColor（H12）
- 原生 Toolbar 溢出（OpenUrlConfirm/VerificationCode）→ 项目头部（H5）
- 旧 `TitleBar` 残留（ReadRecord/S3Container/LibraryContainer/AiImageProviderEdit）→ 双基线（H4）
- `ConfigTopBar`（ConfigActivity 私有）缺背景 → 补背景随顶栏管理（H6）——**H6 已完成（2026-08-27）：ConfigTopBar 已带背景（TopBarConfig/壁纸/透明度），菜单已改 AppDropdownMenu（渲染层对齐基线）**
- ReadRecordActivity 壳层自绘脱离体系（登记 Phase2 收敛）
- 播放器/漫画沉浸页（ReadBook/ReadManga/Video/Audio）：**播放器手势红线，不改造**

**主 Tab 头部搜索入口形态（topbar-search-entry-align，2026-08-28）**：四主 Tab（书架/发现/订阅/我的）统一"标题区（titleSelect）+ 搜索按钮 → 新搜索页"，宿主一律 `setSearchEntryVisible(false)` 关闭 searchEntry 胶囊（regular 风格下胶囊与 titleSelect 互斥，关胶囊后源选择入口自动回归）；搜索框底色统一 `ThemeUiPalette.searchFieldBackgroundColor` + alpha 对齐 View 侧（详见 `project-rules/frontend-ui-standards.md` §3.1）。

### 2. 菜单族（4 体系 → 1 视觉基线）

| 体系 | 现状 | 处置 |
|------|------|------|
| `ModernActionPopup`（`ui/widget/ModernActionPopup.kt`，View） | 在用 23 文件，主界面主流，**统一视觉基线** | 保留 |
| `AppDropdownMenu`（`ui/widget/components/AppDropdownMenu.kt`，M3 DropdownMenu） | 38 文件（实测 44，Compose 次级页），视觉与基线不符（H8 用户实锤） | **H8 已完成（2026-08-27）：渲染层已对齐基线**（条目 → 自绘 Surface+点击行，调用点零改动） |
| 系统 Toolbar 菜单（MenuProvider/menuInflater） | 可见 4 处（Config 宿主 2/漫画/发现经典）+ 残存 7 处死代码 | 可见 → ModernActionPopup（H6/H7）；残存 → 清死代码 |
| `components/ModernActionPopup.kt`（Compose 版） | **0 调用死代码** | 删除（消除同名双实现） |

**禁止**：新建系统溢出菜单/menuInflater；新建 PopupMenu；自绘菜单浮层。

### 3. 弹框族（5 家族 → ComposeDialogFragment 基线）

| 家族 | 数量 | 状态 | 处置 |
|------|------|------|------|
| A 新 Compose（`ComposeDialogFragment` + `AppDialogFrame`/`AppDialogStyle`，含 9 工厂 40 子类） | 49 文件 | ✅ 全纳管 | **基线** |
| B 旧 View（`base/BaseDialogFragment` 子类，仅 `setBackgroundColor(ThemeStore)` 联动背景） | **36**（+pref 2） | ⚠️ 仅背景色 | **D1 全部入迁移队列**（撤销 G6 存量判定） |
| C 系统弹框（`alert{}` DSL 71 文件 162 处 + 内联 9 处） | 71 文件 | ❌ 不随主题 | D2 收敛 `ComposeConfirmDialog` 族 |
| D M3 @Composable（`AppConfirmDialog`/`AppEditDialog`/`AppTextDialog`/`SingleChoiceDialog`/`ConfirmDialog`） | 5 | ✅ material3 默认 | D3 对齐 `AppDialogStyle`（补面板背景/圆角/透明度） |
| E 散点（raw Dialog/BottomSheet/ComponentDialog/AlertDialog+ViewBinding） | 13 | ⚠️ 部分 | D4 迁移或登记 |

**禁止**：新建 `BaseDialogFragment` 子类；新建 `alert{}` DSL；弹框系统原生样式。

### 4. 卡片 / 列表 / 根背景族（3 套 → 直色基线）

| 族 | 现状 | 基线 |
|----|------|------|
| 设置面板/行 `appSettingPanelBackground` + `appSettingRowDecoration` | 10 设置系（AppSettingPalette 直色，支持面板背景图/圆角倍率/透明度） | **基线 A** |
| `SettingsCard`/`SettingsClickRow`/`SettingsToggleRow`（M3 surfaceVariant/onSurface 派生色） | 6 文件（H9 用户实锤） | **H9 已完成（2026-08-27）：取色已归位直色**（containerColor → Color(palette.row)、文字 → primaryText/secondaryText、标题 → accent） |
| `AppManagementCard`/`AppManagementListRow`（palette.settings.row + panelImageDrawable） | 21 管理页 | **基线 B**（列表管理页） |
| `ListCard` 及 Dict/Highlight/Download 内联列表项（M3 surface） | H10 | **已完成（2026-08-27）**：归位 `palette.settings.row` |

**根背景规则**：页面根容器一律 `palette.settings.page`（或 View 层 ThemeStore backgroundColor）；列表项/卡片一律 `palette.settings.row`。**禁止** `colorScheme.surface/surfaceVariant` 做根背景或列表项卡片取色。**实施状态（2026-08-27 实况核查）**：PreciseManage 根背景已归 page ✅；6 页列表项卡片已归位 5/6 ✅（仅剩 TxtTocRuleScreen）——权威源 = `docs/specs/ui-style-unify-deep-fix/issue-list.md`/`tasks.md`。

## 四、新组件 / 新页面开发门禁（Checklist）

> 新增/修改 UI 完成后逐项自检，全部通过才算完成；**具体写法/真签名/样板页见 `how-to.md`（写码前先翻它，禁止凭记忆猜 API）**：

- [ ] 0. 顶栏图标行为语义（topbar-icon-semantics-fix 置顶条款，2026-08-28）：**图标功能有效性**——每个顶栏/菜单图标必须挂真实 onClick，禁止死按钮/空实现/占位图标；**图标语义保留**——迁移/重构 TopBar 时原一级功能图标（原版 menu XML `showAsAction="always"`）禁止静默收拢进溢出菜单，必须映射为一级图标（ConfigTopBar 系用 `MenuAction.alwaysShow=true`；GlassTopAppBar 系 actions 槽直写；MainTopBarView 系走 `addActionButton`）；新增一级图标按组件系接入取色权威源（updateIconColors / actionIconContentColor / contrastOn(bgColor) / titleTextColor），**禁止硬编码图标 tint**；迁移登记见 migration-registry.md"原 showAsAction 处置"必填列
- [ ] 1. 顶栏：从三基线选一（MainTopBarView / GlassTopAppBar / AppManagementTopBar），未自绘 Row、未用 M3 TopAppBar、未用原生 Toolbar 溢出
- [ ] 2. 菜单：ModernActionPopup 视觉（AppDropdownMenu 渲染层）/ 行内 action 图标，非系统菜单
- [ ] 3. 弹框：`ComposeDialogFragment` + `AppDialogFrame`/`AppDialogStyle`（AppComposeDialogs 工厂），非 BaseDialogFragment / alert{} DSL / M3 组件
- [ ] 4. 根背景：`palette.settings.page`（ThemeStore 直读），非 `colorScheme.surface`
- [ ] 5. 取色：走 `rememberAppSettingPalette()` / `rememberAppDialogStyle()` / `UiCorner`；无硬编码色号（Grep `#(?:[0-9A-Fa-f]{6,8})|Color\.` 自查）
- [ ] 6. 列表/卡片：AppManagementCard/AppManagementListRow 或 appSettingPanelBackground，非 SettingsCard/ListCard M3 默认
- [ ] 7. 同屏一致性：新建页与同类既有页（头部/背景/弹框）视觉一致
- [ ] 8. 更新记录：ui-standards（components.md/color.md）+ migration-registry.md 同步

### MaterialSurface 双栈豁免（总线登记 2026-08-31，master-track AD-04）

MaterialSurface 体系（ng P5 视觉设计：MaterialSurface(Compose) 与 MaterialSurfaceStyle(View)）属"语义单源、实现双栈"——同一语义角色在 View 侧与 Compose 侧各有一实现，桥接自同一 MaterialRole 参数表。该双实现**不适用**"miuix 与 M3 双体系扩散禁令"（二者性质不同：双栈=同语义两实现；双体系=两套设计语言）。判定口径：新增组件若存在 View/Compose 同语义双实现且共享同一 Role/Token 参数源，登记为本豁免范围；除此之外仍严格执行单一组件来源门禁。

## 五、文档索引与状态

| 文档 | 内容 | 状态 |
|------|------|------|
| `architecture.md`（本文件） | UI 设计架构体系总纲（铁律/主题全景/取色基线/四组件族/门禁） | 基线 |
| `color.md` | 取色规范（ThemeUiPalette/R.color 兜底 + 设置类主取色链 + M3 派生色禁令） | 基线 |
| `components.md` | 组件目录（含状态标注：基线/待对齐/弃用） | 基线 |
| `spacing-corner-typography.md` | 间距/圆角/字体 Token | 基线 |
| `page-skeleton.md` | 页面骨架（管理壳/设置壳 + 根背景规则） | 基线 |
| `dialog-shell.md` | 弹框壳（5 家族 + 迁移队列） | 基线 |
| `migration-registry.md` | 迁移登记（含 ui-style-unify-deep-fix 批次 H/D/S） | 跟踪中 |

> 迁移状态权威源：`docs/specs/ui-style-unify-deep-fix/issue-list.md`（H1-H14/D1-D4/S1-S6）+ `tasks.md`；本文档为「常驻规范 + 禁止项」，改迁移状态时必须同步两处。