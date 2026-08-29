# §9.3 间距 / 圆角 / 字体规范

> 本项目的间距、圆角、字体采用「XML 资源 + 业务方 scale Transform」的混合实现。
> 核心文件：
> - `app/src/main/java/io/legado/app/lib/theme/ComposeUiCorner.kt`（Compose 圆角桥接）
> - `app/src/main/java/io/legado/app/lib/theme/UiCorner.kt`（View 层圆角 / 面板绘制）
> - `app/src/main/java/io/legado/app/lib/theme/UiTypography.kt`（字体）
> - `app/src/main/java/io/legado/app/ui/widget/compose/AppUiTokens.kt`（spacing / 对话框宽度 Token）

## 一、间距（Spacing）Token

`app/src/main/java/io/legado/app/ui/widget/compose/AppUiTokens.kt`：

| 层级 | Dp 值 | 场景 |
|------|-------|------|
| `AppListSpacing.Compact` | `6.dp` | 紧凑列表项间距 |
| `AppListSpacing.Normal` | `8.dp` | 常规列表项间距（列表默认 `verticalArrangement`） |
| `AppListSpacing.Section` | `12.dp` | 大段/分组间距 |

- 管理壳列表默认使用 `Normal` 档位作为行间距（见 `AppManagementLazyColumn` 默认 `Arrangement.spacedBy(AppListSpacing.Normal)`）。
- 卡片内边距常用 `PaddingValues(horizontal = 14.dp, vertical = 10.dp)`（`AppManagementCard` 默认）。

## 二、圆角（Corner）规范

### 1. 运行时基础规格 `ui/widget/compose/ComposeUiCorner.kt`

将 View 层的 `UiCorner.panelRadius` / `actionRadius`（px，已乘 UI 圆角缩放 `scale()`）转为 Composable 的 `Dp` 与 `RoundedCornerShape`：

| 函数 | 返回 | 说明 |
|------|------|------|
| `Context.composePanelRadius()` | `Dp` | 面板圆角半径（`panelRadius / density`） |
| `Context.composeActionRadius()` | `Dp` | 动作/按钮圆角半径（`actionRadius / density`） |
| `Context.composePanelShape()` | `RoundedCornerShape` | 面板形状 |
| `Context.composeActionShape()` | `RoundedCornerShape` | 动作按钮形状 |

### 2. View 层实现 `UiCorner.kt`（`io.legado.app.lib.theme`）

`object UiCorner` 是圆角/面板绘制的核心：

- `scale()`：UI 圆角全局缩放（`AppConfig.uiCornerScale`，钳制 0..3）。
- `panelRadius(context)` / `actionRadius(context)`：`R.dimen.ui_panel_radius` / `R.dimen.ui_action_radius` 乘 `scale()`。
- `scaledDp(value)`：dp→px 后再乘 scale。
- `searchRadius(value)` / `replyRadius(value)`：搜索框/回评圆角，默认不跟随缩放，`AppConfig.uiCornerSearchFollow/ReplyFollow` 开启后跟随 `scaledDp`。
- `layoutAlpha()`：布局透明度（`uiLayoutAlpha` 0..100 → 0..1），面板底/按压态叠加透明度。
- 面板背景图：`panelImageDrawable`（可叠加自定义面板背景图 + 圆角裁剪），`effectMode()` 固定 `"solid"`。
- 边框：`panelBorderColor` / `panelBorderAlpha`，画 stroke。
- 形变 `rounded` / `opaqueRounded` / `roundedStroke` / `strokeOnly` / `actionSelector` 等：生成 `GradientDrawable` / `StateListDrawable`。

### 3. 内部外观组件圆角

`LegadoMiuixPalette` 持有 `panelRadius` / `actionRadius`（来自 `AppManagementPalette`），供 `LegadoMiuixCard` 等统一外观组件使用。

## 三、字体（Typography）规范

`UiTypography.kt`（`io.legado.app.lib.theme`）：

- **双字体通道**：
  - `Context.uiTypeface()`：正文/UI 字体，取 `AppConfig.uiFontPath`（空则回退系统字体 `baseSystemTypeface`）。
  - `Context.titleTypeface()`：标题/强调字体，取 `AppConfig.titleFontPath`。
- `baseSystemTypeface()`：`AppConfig.systemTypefaces` 1=Serif / 2=Monospace / 其余=SansSerif。
- 字体缓存 `UiTypefaceCache`：`LinkedHashMap`，容量 8，支持 `content://` / 文件路径加载。
- **递归应用扩展**：
  - `View.applyUiTypefaceDeep`：对整棵子树应用正文字体（含标题）。
  - `View.applyUiBodyTypefaceDeep`：排除 `TitleBar` 与标记为标题角色（`R.id.ui_title_typeface_role=true`）的递归应用。
  - `TextView.applyUiTitleTypeface`：设标题字体 + 标题色（角色标记 true）。
  - `TextView.applyUiMenuItemTypeface` / `View.applyUiMenuTypefaceDeep`：菜单项字体（角色 false）。
- **内置样式**（`TextView` 扩展，字号写死）：
  - `applyUiLabelStyle`：14sp。
  - `applyUiSectionTitleStyle`：标题字体 + 15sp + 标题色。
  - `applyUiSubtleButtonStyle`：14sp + minHeight 40dp。
  - `applyUiInputStyle(minLines)`：15sp，minLines=1 → minHeight 44dp、maxLines 2；minLines>1 → minHeight 92dp、maxLines 8；内边距 (12, 8/10)。

### 顶栏标题排版基线（2026-08-28 全顶栏普查沉淀，AD-19 既有基线）

**全 App 顶栏标题统一 `LegadoTypography.titleLarge` = 20sp / Medium(500)**。禁止在顶栏组件内覆写 fontSize/fontWeight。豁免：阅读器/视频播放器顶栏（T7）、欢迎页 49sp 品牌大字、弹框/卡片标题。

普查终版（书架 24sp / ConfigTopBar SemiBold / AppManagementScaffold 19sp+SemiBold 三处漂移已由 spec `bookshelf-refresh-and-title-font` 修复归位）：

| 顶栏组件 | 覆盖页面 | 标题来源 |
|---------|---------|---------|
| `MainTopBarView` | 主 Tab（书架/订阅/我的/阅读记录/发现） | View 端 20sp 硬编码（勿再分 Mode 特判） |
| `GlassTopAppBar` | 一般 Compose 子页 | `MaterialTheme.typography.titleLarge` |
| `ConfigTopBar`（ConfigActivity） | 全部设置子页 | `MaterialTheme.typography.titleLarge` |
| `AppManagementScaffold` | 书源/订阅源/替换规则/订阅规则/书架分组 5 管理页 | `MaterialTheme.typography.titleLarge` |
| `TitleBar`（View 子页） | 传统子页 | MaterialToolbar 默认 ToolbarTitle 20sp，勿覆写 textAppearance |

### 顶栏右侧图标按钮基线（2026-08-28 普查沉淀，用户裁决"统一 20dp"）

**图标绘制尺寸统一 20dp 档**；IconButton 容器随顶栏行高弹性（热区不受图标缩小影响）。豁免：主 Tab `MainTopBarView` 图标按钮（`dimen/bookshelf_action_button_size` = 34dp 容器 + 8dp padding ≈ 18dp 图标，Archive 对齐既定值）。

| 顶栏组件 | 按钮容器 | 图标绘制 |
|---------|---------|---------|
| `GlassTopAppBar` / `ConfigTopBar` | M3 IconButton 48dp | **`Modifier.size(20.dp)`**（新基准，禁省略回落 M3 默认 24dp） |
| `AppManagementIconAction` | 36dp | 20dp |
| `MainTopBarView.actionButton` | 34dp（豁免） | ~18dp（豁免） |

**已知差异（登记专项）**：图标"粗细"= 资产描边差异（自绘 ic_*.xml 描边宽度各异 vs M3 Icons 标准描边），统一需全量梳理图标资产，属独立专项（见 issue-list），新增自绘图标时描边宽度对齐 M3 视觉重量。

## 四、对话框宽度档位（补充）

`AppDialogSize`（AppUiTokens.kt）：`Confirm`(0.92/620dp)、`Form`(0.94/660dp)、`Management`(0.96/700dp)、`Wide`(0.98/760dp)，内容类型决定宽度档位，手机宽度比例 + 平板上限（详见 dialog-shell.md）。