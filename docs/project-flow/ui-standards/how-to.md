# UI 实操指南（How-to）— AI 新增/修改 UI 的即查手册

> 目录：`docs/project-flow/ui-standards/how-to.md`
> 更新：2026-08-28 | **配套**：先读 `architecture.md`（体系/铁律/四组件族），本文件给"具体怎么写"的真签名与骨架。
> 本文件的函数签名均**源码核验**（2026-08-27），改源码后若签名变化请同步本文，禁止杜撰。

## 〇、使用流程（30 秒决策）

```
我要改/新增 UI
 ├─ 是"弹框"类 → §1（先选语义→工厂→show 入口）
 ├─ 是"右三点下拉菜单" → §2（AppDropdownMenu/MenuAction）
 ├─ 是"整页 Compose" → §3（顶栏三选一 + 根背景 + 内容）
 ├─ 是"列表管理页" → §4（AppManagementScaffold 骨架）
 ├─ 是"View 页顶栏" → §5（MainTopBarView 布局）
 ├─ 只是"取色/圆角/文字" → §6（禁止硬编码，走调色板）
 └─ 完事后 → §7 自检清单 + §8 严禁项
```

## 一、新增弹框（Dialog）

### 1.1 先按语义选对工厂（AppComposeDialogs.kt，均为 `ComposeDialogFragment()` 子类）

| 我要的弹框 | 工厂（`companion fun create(...)`） | 便捷入口（Fragment/Activity 版均有） |
|-----------|------------------------------------|--------------------------------------|
| 确认（OK/取消，可 danger） | `ComposeConfirmDialog` | `showComposeConfirmDialog` |
| 动作列表（点选执行） | `ComposeActionListDialog` | `showComposeActionListDialog` |
| 单选 | `ComposeSingleChoiceDialog` | `showComposeSingleChoiceDialog` |
| 多选 | `ComposeMultiChoiceDialog` | `showComposeMultiChoiceDialog` |
| 单行文本输入/密码 | `ComposeTextInputDialog` / `ComposeSuggestionTextInputDialog` | `showComposeTextInputDialog` / `showComposeSuggestionTextInputDialog` |
| 多字段表单 | `ComposeTextFormDialog` | `showComposeTextFormDialog` / `showComposeTextFormDialogWithChecks` |
| 数字选择 | `ComposeNumberPickerDialog` | `showComposeNumberPickerDialog` |
| 选择列表（ChoiceList） | `ComposeChoiceListDialog` | `showComposeChoiceListDialog` |
| 异步取数模型 | `ComposeFetchedModelDialog` | （自定义） |

### 1.2 标准写法（在 Fragment 内）

```kotlin
// 确认弹框（签名来源于 ComposeDialogAdapters.Fragment.showComposeConfirmDialog）
showComposeConfirmDialog(
    title = "删除分组",
    message = "确定删除该分组？组内项目不删除。",
    positiveText = "删除",
    dangerPositive = true,
    onPositive = { viewModel.delete(group) }
)
```

```kotlin
// 文本输入弹框（回调 onPositive: (String) -> Unit）
showComposeTextInputDialog(
    title = "重命名",
    hint = "输入新名称",                             // 占位提示
    initialValue = oldName,                          // 预填值
    validateInput = { it.isNotBlank() },             // 可选：输入校验
    onPositive = { newName -> viewModel.rename(newName) }
)
```

```kotlin
// 单选（labels + selectedIndex，回调 onPositive: (Int) -> Unit）
showComposeSingleChoiceDialog(
    title = "选择分组",
    labels = groupNames,
    selectedIndex = currentIndex,
    onPositive = { index -> selectGroup(index) }
)
```

```kotlin
// 多选（checkedIndices 预勾选，回调 onPositive: (BooleanArray) -> Unit）
showComposeMultiChoiceDialog(
    title = "批量导出",
    labels = bookNames,
    checkedIndices = selectedIndices,
    onPositive = { checkedArr -> export(checkedArr) }
)
```

### 1.3 Activity 里调用
`AppCompatActivity` 同样有全套 `showCompose*` 扩展（`ComposeDialogAdapters.kt`）。Fragment 内直接调用即可（内部 `showDialogFragment`）。

### 1.4 复杂弹框（需要自定义 Compose 内容）
继承 `ComposeDialogFragment`，`onCreateView` 返回 `ComposeView { setContent { ... } }`，内部用 `rememberAppDialogStyle()` + `AppDialogFrame(title, message, content = {...}, actions = {...})` 搭壳。参考样板：`ChatOrderDialog`/`TopBarEditDialog`/`DictRuleEditDialog`（均已 ComposeDialogFragment 化）。

**滚动嵌套自查（30 秒，触犯 = 点开即闪退）**：`AppDialogFrame` 默认 `scrollContent = true`（外层已 `verticalScroll`），此时 content 内**禁止**再放无高度约束的垂直滚动组件（`LazyColumn` / 自带 `verticalScroll` 的组件）。二选一：①整体滚动 → 内层组件禁自带滚动（可复用组件加 `scrollable` 形参，见 `HighlightStyleSheet`）；②列表自滚 → `scrollContent = false` + `LazyColumn` 加 `heightIn(max = 420.dp)`。详见 `dialog-shell.md` §二「AppDialogFrame 滚动嵌套契约」。

## 二、右三点下拉菜单（Menu）

### 2.1 数据驱动 `MenuAction`

```kotlin
data class MenuAction(
    val icon: ImageVector,
    val title: String,
    val tint: Color? = null,
    val checked: Boolean? = null,
    val header: Boolean = false,
    val alwaysShow: Boolean = false,   // topbar-icon-semantics-fix：true=顶栏一级图标直出（不进溢出），
                                       // false=溢出菜单（默认向后兼容）。仅 ConfigTopBar 分级渲染与
                                       // GlassTopAppBar 系页面分级槽消费；AppMenuSheet/AppDropdownMenu 忽略。
                                       // header=true 是溢出内分组标签，禁止与 alwaysShow=true 组合
    val onClick: () -> Unit
)
```

### 2.2 Compose 页（当前主流，待 H8 渲染层对齐基线的入口不变）

```kotlin
var menuExpanded by remember { mutableStateOf(false) }
Box {
    IconButton(onClick = { menuExpanded = true }) { Icon(Icons.Default.MoreVert, "更多") }
    AppDropdownMenu(                       // ui/widget/components/AppDropdownMenu.kt
        expanded = menuExpanded,
        onDismiss = { menuExpanded = false },
        actions = listOf(
            MenuAction(Icons.Default.Add, "新增", onClick = { ... }),
            MenuAction(Icons.Default.Delete, "删除全部", tint = palette.danger, onClick = { ... }),
            MenuAction(Icons.Default.Check, "显示勾选态", checked = true, onClick = { ... })
        )
    )
}
```

### 2.2.1 actions 分级标准（topbar-icon-semantics-fix，对齐 Archive 原版 always/never 语义）

- **一级图标准入**：高频核心动作 ≤3 个（如 保存/代码编辑/调试/新增/刷新/帮助），对应原版 `showAsAction="always"`；其余一律进溢出下拉（原版 `never`）。
- **分级写法**：
  - ConfigTopBar 系（设置宿主页 Fragment）：上报 `MenuAction(..., alwaysShow = true)`，渲染层自动直出一级 IconButton（tint 由渲染层 `contrastOn(bgColor)` 统一处理，调用方禁自传 tint）；样板 `BackupConfigFragment`。
  - GlassTopAppBar 系页面：actions 槽内 `menuActions.filter { it.alwaysShow }` 直出 IconButton + 其余进 MoreVert 下拉；IconButton **禁止自传 tint**（继承 `actionIconContentColor` 对比度推导）；样板 `TxtTocRuleScreen` / `RssSourceEditActivity`。
  - MainTopBarView 系（View）：`addActionButton(iconRes, contentDescRes) { onClick }` 走 actionsBar 插槽（updateIconColors 统一染色 + styleActionSlotButtons 两风格适配，禁硬编码 tint）；样板 `MyFragment` / `RssFragment`。
  - View TitleBar 系：`MainTopBarView.addActionButton`（图标色走 titleTextColor 链）；弹出菜单中重复项在 `prepare` 里 `isVisible = false` 隐藏；样板 `BookSourceEditActivity`。
- **迁移对照**：TopBar 迁移/重构时逐项对照原版 menu XML 的 `showAsAction`——always→一级、never→下拉，处置登记到 `migration-registry.md`"原 showAsAction 处置"必填列（见 §8 更新记录与 migration-registry）。

> 顶栏"更多"菜单更常用 `AppManagementAction(text, iconRes?, ...)` + `AppManagementScaffold.topActions`（见 §4），由 `AppManagementMoreActionButton` 走 `ModernActionPopup`。

## 三、新增 Compose 全页面

```kotlin
// 顶层：必须 LegadoComposeTheme 包裹 + 根背景 palette.settings.page（禁止 colorScheme.surface）
setContent {
    LegadoComposeTheme {
        val palette = rememberAppManagementPalette()
        Box(Modifier.fillMaxSize().background(palette.settings.page)) { // ← 根背景直色
            Column(Modifier.fillMaxSize()) {
                GlassTopAppBar(          // Compose 顶栏基线（ui/widget/components/GlassTopAppBar.kt）
                    title = "我的新页面",
                    // navigationIcon 默认返回箭头；可传 containerColor 覆盖（特殊页）
                    actions = { /* IconButton/AppDropdownMenu（§2）或 AppManagementMoreActionButton */ }
                )
                // 内容区……
            }
        }
    }
}
```

要点：
- 顶栏三选一：普通功能页 `GlassTopAppBar`；纯列表管理页 `AppManagementScaffold`（§4）；View 骨架页 `MainTopBarView(SUB)`（§5）。**H13 已实施（2026-08-27）：GlassTopAppBar 已接入顶栏管理 TopBarConfig（STYLE_REGULAR 时消费壁纸/圆角/背景色）**——勿再按"仅主色"理解其取色。
- 列表项/卡片：`AppManagementLazyColumn` + `AppManagementCard`/`AppManagementListRow`（直色）；设置类用 `appSettingPanelBackground`/`appSettingRowDecoration` + `AppSettingSectionTitle`。
- 空态：`EmptyStatePlaceholder`；骨架屏：`ShelfGridSkeleton/ShelfListSkeleton`。

## 四、新增列表管理页（AppManagementScaffold 骨架）

```kotlin
setContent {
    AppManagementScaffold(
        title = "我的列表页",
        selectedCount = selectedCount,
        totalCount = items.size,
        searchQuery = query, onSearchChange = { ... },            // 需要搜索就传
        topActions = listOf(AppManagementAction("新增", R.drawable.ic_add) { ... }),
        bottomActions = /* 多选批量动作 */,
        onSelectAll = { ... }, onInvertSelection = { ... },
        onBack = { finish() }
    ) { palette ->
        AppManagementLazyColumn(items, ...) // AppManagementCard(item) { ... }
    }
}
```

> 完整签名见 `page-skeleton.md` §一。样板页：`BookSourceActivity`/`ReplaceRuleActivity`/`RuleSubActivity`（已全 Compose 接管）。

## 五、View 页顶栏（MainTopBarView）

- 布局 XML 引入：`<io.legado.app.ui.widget.MainTopBarView android:id="@+id/topBar" .../>`，代码构造 `MainTopBarView(this, Mode.SUB)` 或复用 `ActivityThemeManageBinding` 布局（`TopBarManageActivity`/`ReadMenuButtonManageActivity` 等样板）。
- 三点菜单：`ModernActionPopup.showFromMenu(this, menuRes/actions, anchor)`（样板 `BookSourceEditActivity`/`BookSourceDebugActivity`）。
- **不要**用 `onCompatCreateOptionsMenu` 系统菜单（残存均待清理，H7）。

## 六、取色 / 圆角 / 字体（禁止硬编码）

| 我要的 | 正确写法 | 禁止 |
|--------|---------|------|
| 页面根背景 | `palette.settings.page` 或 `Color(context.backgroundColor)` | `MaterialTheme.colorScheme.surface/background` |
| 卡片/行底 | `UiCorner.surfaceColor(themeUiPalette.cardColor)` / `palette.settings.row` | `colorScheme.surfaceVariant` |
| 正文字 | `palette.primaryText` | `colorScheme.onSurface` |
| 次要文字 | `palette.secondaryText` | `colorScheme.onSurfaceVariant` |
| 强调/主操作 | `palette.accent` | 自定十六进制 |
| 危险红 | `palette.danger` | `Color(0xFF...)` |
| 圆角 | `UiCorner.panelRadius/actionRadius` 或 `composePanelRadius()` | 自定 dp 值（需圆角缩放联动） |
| 字体 | `uiTypeface()/titleTypeface()`/`applyUi*Style` | 写死 fontFamily |

> View 层取色对照同表（`ThemeStore.themeColors().*` + `UiCorner.kt` 形变）。夜间变体 key 用 `*N` 后缀。
> 特殊语义（Danger 红在阅读色板、媒体画布、封面打底、视频控制层）属"主题体系外"豁免，按 `color.md` §五登记。

## 七、完成后自检（30 秒）

```bash
# 1) 无硬编码色（应仅命中豁免类：语义Danger/媒体画布/视频层/ThemeSpec定义源）
Grep 新增文件: "#(?:[0-9A-Fa-f]{6,8})|Color\.(BLACK|WHITE|RED|GRAY)"
# 2) 无 M3 派生色做页面/卡片背景（命中即拒）
Grep : "colorScheme\.(surface|background)" → 仅允许中性灰浮层/多选遮罩等登记场景
# 3) 无弹框违规
Grep : "BaseDialogFragment|alert\s*\{" → 新代码命中即拒
# 4) 无系统菜单违规
Grep : "onCompatCreateOptionsMenu|menuInflater"
# 5) 无滚动嵌套（弹框 content 内）：scrollContent=true 时禁 LazyColumn / 根级 verticalScroll 组件；
#    可复用滚动组件必须 heightIn 前置或 scrollable 参数化（详见 dialog-shell.md §二契约）
# 6) 图标行为走查（topbar-icon-semantics-fix 审计维度，2026-08-28）：
#    a. Grep : "onClick = \{\}" / "onClick = \{ \$" → 顶栏/菜单图标命中即拒（死按钮）
#    b. 每个新增/改动顶栏图标必须真机点击验证行为（弹帮助/保存/跳转…），不仅看存在性
#    c. TopBar 迁移时逐项对照原版 menu XML showAsAction：always→一级（alwaysShow/一级 IconButton/
#       addActionButton）、never→下拉；处置登记 migration-registry.md"原 showAsAction 处置"
#    d. 一级图标 tint 核验：走组件系权威源（updateIconColors/actionIconContentColor/contrastOn/
#       titleTextColor），禁自传固定色
```

- 编译门禁：`./gradlew :app:compileAppDebugKotlin`
- 同步文档：ui-standards（components.md 新组件）/ migration-registry.md（若属迁移项）/ updateLog（用户可见变更）
- 真机/模拟器验证：与同类页面对比视觉一致（参考 `ui-page-matrix.md` 125 页判定）+ **顶栏图标逐个点击走查（行为有效性，防静默降级/死按钮）**

## 八、严禁清单（触犯 = 代码审查驳回）

1. 硬编码色号 / `Color.BLACK/WHITE` 做 UI 底
2. `MaterialTheme.colorScheme.surface/surfaceVariant/onSurface` 做页面级/卡片级视觉取色
3. 新建 `BaseDialogFragment` 子类 / 新建 `alert{}` DSL / 弹框走系统样式
4. 新建系统下拉菜单（MenuProvider/onCompatCreateOptionsMenu/menuInflater）
5. 页面根背景用 `colorScheme.background/surface` 而非 palette.page
6. 自绘顶栏 Row（必须三基线选一）/ 新造同名组件
7. `app:topBarMode` 之外搞私有 TitleBar 残留
8. 改动后不更新 ui-standards / migration-registry / updateLog
9. `AppDialogFrame(scrollContent=true)` content 内放无高度约束的垂直滚动组件（LazyColumn / 根级 verticalScroll 组件）→ 点开即闪退（铁证 2026-08-28 高亮规则编辑/预设弹框）；可复用滚动组件根级裸 `verticalScroll` 无 `heightIn` 前置钳制亦同罪
10. 静默收拢原一级功能图标：TopBar 迁移/重构时把原 `showAsAction="always"` 图标（问号帮助/保存/代码等）未声明即塞进溢出菜单（铁证 2026-08-28 备份页问号变竖点，18 页回归）——必须按 §2.2.1 分级标准映射 alwaysShow/一级图标
11. 空 onClick 占位图标：顶栏/菜单图标挂 `onClick = {}` 或漏传点击回调（如 `AppManagementAction.onClick` 默认 `{}` 漏传）→ 死按钮；每个图标必须接真实业务回调
12. 硬编码图标 tint：新增顶栏一级图标自传固定颜色（绕过 updateIconColors / actionIconContentColor / contrastOn / titleTextColor 权威源）→ 换肤/夜间/深色壁纸下颜色错乱
13. Compose 渲染层配置快照：在 @Composable 屏内用 `remember { AppConfig.xxx }` / 裸读 `AppConfig.xxx` 作为展示配置源（铁证 2026-08-28 书架 BookshelfScreen 布局/书名/边距设置需重启才生效，订阅页顶栏跨模式残留）——配置必须由宿主 Fragment 经 mutableStateOf 受控传入，并在 `*_REFRESH`（数据类）/`*_STRUCTURE_CHANGED`（结构类）事件回调重读 AppConfig 后写入；配置变更分类：布局/结构 → 结构重建事件，间距/开关 → 数据刷新事件，禁止全部走单一事件
14. 跨模式/跨状态 flow collector 泄漏：模式切换时旧 collector 不无条件取消，依赖后续路径间接取消（铁证 2026-08-28 RssFragment modern collector 在文件夹视图路径存活，RESUMED 重发覆盖经典顶栏）——切换入口处必须先 cancel 并置 null 所有模式私有 Job

## 九、样板页索引（"照抄即可"的现成实现）

| 我想做 | 照抄页面 | 亮点 |
|--------|---------|------|
| Compose 功能页（顶栏+列表+弹框全走主题） | `StorageManageActivity` / `RssSourceEditActivity` | 顶栏 GlassTopAppBar + palette 直色 + Compose 弹框 |
| 列表管理页 | `ReplaceRuleActivity` / `BookSourceActivity` | AppManagementScaffold 全量 |
| 搜索列表页 | `SearchContentActivity` / `RssSearchActivity` | GlassTopAppBar + SettingsSearchBar + AppDropdownMenu |
| 设置类子页（分区卡片） | `ComposeSettingFragment` 系列 / `PreciseManageFragment` | SettingSpecScreen 声明式 |
| 复杂自定义弹框 | `TopBarEditDialog` / `DictRuleEditDialog` | ComposeDialogFragment + AppDialogFrame |
| View 子页顶栏 | `BookSourceEditActivity` / `TopBarManageActivity` | MainTopBarView(SUB) + ModernActionPopup |