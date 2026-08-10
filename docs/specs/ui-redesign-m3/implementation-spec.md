# 实现细化规格 Implementation Spec（补齐开发支撑）

> 本文件是「全部补齐再开工」的实现级规格：组件签名、文件锚点、主题映射、PR 粒度任务+验 KPI。
> 所有内容经真实代码探针（文件:行号）核实，**不臆测**。
> 前置文档：[frontend-synthesis.md](./frontend-synthesis.md)（五支柱+不裁剪）+ [design.md](./design.md)（ADR-01~18）。

## 一、真实代码基境（探针结论）

| 项 | 现状 | 精确锚点 |
|----|------|---------|
| Compose 主题 | `LegadoTheme.kt` 已把 ThemeStore→M3，但 surface 族用 `lerp(bg, White/Black, 0.04/0.10)` 特判 | `ui/theme/LegadoTheme.kt:40-42` |
| 底部导航 | XML `BottomNavigationView` + `viewPagerMain`（ViewPager2），菜单项 idExplore/idRss/idMy/…，`addBadgeView(0)` 红点 | `MainActivity.kt:18/72/155/361/395/441`；`res/layout/activity_main.xml` |
| 我的页 | `MyFragment`（`BaseFragment`）内嵌 `MyPreferenceFragment`（PreferenceFragment），替换进 `R.id.pre_fragment`；帧主片段更换入口写死 `position` | `ui/main/my/MyFragment.kt:45/55/57-64/79`；`res/layout/fragment_my_config.xml`（`pre_fragment`） |
| 主题配置 | `assets/defaultData/themeConfig.json`：14 套主题，暗夜紫在第 12 条（`#7B1FA2`/bg `#1E1E32`）；entry 字段为 `primaryColor/backgroundColor` 整数色（**非 34 槽位**） | `assets/defaultData/themeConfig.json:91-96` |
| 公共组件库 | **不存在** `ui/widget/components/` 目录（tools 探测 0 文件）→ 全新创建 | — |
| 阅读浮层 | `activity_book_read.xml:8` `read_view` 为核心；浮层用 Dialog 形态（非 BottomSheet） | `res/layout/activity_book_read.xml` |

> ⚠️ 重要修正（不裁剪红线落地）：`themeConfig.json` 的 entry 结构是 `primaryColor/backgroundColor/textColor` 等**完整历史字段**，**不可改写为 34 槽位格式**，否则用户旧存档 + 全部历史主题失效。正确做法：**读取时推导**（`ThemeSpec.toColorScheme()` 运行时扩展槽位），**写入仍保持旧格式**。此点封死 AD-18 的落地方式。

## 二、组件签名规格（`ui/widget/components/` 全新建仓，17 组件）

> 全部 `@Composable`，位于 `app/src/main/java/io/legado/app/ui/widget/components/`。签名遵循本仓 Compose 风格（朴素顶层函数、无 DI）。

### 2.1 导航组件
```kotlin
// PillNavigationBar.kt（MoRealm 改造版：剥离 LocalMoRealmColors，指示点用 M3 token）
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PillNavigationBar(
    selectedTab: Int,
    onTabSelect: (Int) -> Unit,
    tabs: List<PillNavTab>,          // data class PillNavTab(icon: ImageVector, selectedIcon: ImageVector, label: String, badgeCount: Int = 0)
    modifier: Modifier = Modifier,
    showLabels: Boolean = true
)
```

### 2.2 设置组件族（三模板，对应 AD-15）
```kotlin
// SettingsSection.kt — 分组标题卡
@Composable
fun SettingsSection(
    title: String,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit
)

// SettingsCard.kt — 卡片容器（extra 插槽）
@Composable
fun SettingsCard(
    modifier: Modifier = Modifier,
    extraSlot: @Composable (RowScope.() -> Unit)? = null,   // MoRealm 卡片 extra 插槽
    content: @Composable ColumnScope.() -> Unit
)

// SettingsClickRow.kt — 点击行（36dp RowIcon 图标块）
@Composable
fun SettingsClickRow(
    icon: ImageVector?,
    title: String,
    subtitle: String? = null,
    value: String? = null,          // 尾值
    onClick: () -> Unit,
    trailingIcon: ImageVector = Icons.Default.ChevronRight
)

// SettingsToggleRow.kt — 开关行
@Composable
fun SettingsToggleRow(
    icon: ImageVector?,
    title: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    subtitle: String? = null,
    enabled: Boolean = true
)

// RowIcon.kt — 统一 36dp 图标块
@Composable
fun RowIcon(
    icon: ImageVector,
    tint: Color = MaterialTheme.colorScheme.primary,
    modifier: Modifier = Modifier
)
```

### 2.3 卡片/列表
```kotlin
// AppModalBottomSheet.kt（双引擎容器：Sheet vs Dialog 回退）
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppModalBottomSheet(
    onDismiss: () -> Unit,
    sheetState: SheetState = rememberModalBottomSheetState(),
    content: @Composable ColumnScope.() -> Unit
)

// SplicedColumnGroup.kt（连体圆角组）
@Composable
fun SplicedColumnGroup(
    items: List<@Composable () -> Unit>,
    modifier: Modifier = Modifier
)

// SwipeActionContainer.kt
@Composable
fun SwipeActionContainer(
    actionContent: @Composable RowScope.() -> Unit,   // 露出操作（删除/置顶）
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
)
```

### 2.4 进度/骨架/反馈
```kotlin
// VerticalScrollbar.kt
@Composable
fun VerticalScrollbar(
    scrollState: ScrollState,
    modifier: Modifier = Modifier
)

// ShelfGridSkeleton.kt（书架骨架屏）
@Composable
fun ShelfGridSkeleton(
    columns: Int = 3,
    itemCount: Int = 9,
    modifier: Modifier = Modifier
)

// ThemedSnackbarHost.kt（跟随配色）
@Composable
fun ThemedSnackbarHost(
    hostState: SnackbarHostState,
    modifier: Modifier = Modifier
)

// BadgeDot.kt（6dp 圆点，替代 BadgedBox 计数）
@Composable
fun BadgeDot(
    count: Int,                       // 0=隐藏, -1=无数字圆点
    contentColor: Color = MaterialTheme.colorScheme.error,
    modifier: Modifier = Modifier
)
```

### 2.5 页级骨架
```kotlin
// GlassTopAppBar.kt（磨砂顶栏）
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GlassTopAppBar(
    title: String,
    navIcon: ImageVector? = null,
    onNavClick: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {}
)

// SettingsSearchBar.kt（我的页顶部搜索）
@Composable
fun SettingsSearchBar(
    query: String,
    onQueryChange: (String) -> Unit,
    modifier: Modifier = Modifier
)

// MetricGrid.kt（统计卡行）
@Composable
fun MetricGrid(
    metrics: List<MetricItem>,        // data class MetricItem(label: String, value: String, icon: ImageVector)
    columns: Int = 2,
    modifier: Modifier = Modifier
)

// SummaryCard.kt（带 BookStackView 的书籍卡片）
@Composable
fun SummaryCard(
    cover: Any?,                      // String url / Bitmap / Drawable
    title: String,
    onClick: () -> Unit
)
```

### 2.6 阅读浮层
```kotlin
// BookTocBookmarkSheet.kt（目录/书签双 Tab 底部面板，MoRealm ChapterBookmarkPanel 改 M3）
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookTocBookmarkSheet(
    book: Book,
    onDismiss: () -> Unit,
    onChapterClick: (Int) -> Unit    // 定位跳转
)
```

### 2.7 主题推导
```kotlin
// ThemeSpec.kt — data class + 5色→34槽位推导
data class ThemeSpec(
    val primary: Color?, val secondary: Color?, val accent: Color?,
    val background: Color?, val textPrimary: Color?, val textSecondary: Color?
)
fun ThemeSpec.toM3Scheme(isLight: Boolean): ColorScheme   // Color.mix + hueShift(60°) tertiary + contrastOn，无 animateColor
```

## 三、主题实现映射（AD-18 代码级落地）

**改造文件**：`ui/theme/LegadoTheme.kt`
- **现状**：`:40-42` 三条 `lerp` 特判生成 surface/surfaceVariant/outline；`:45-85` 手写 light/dark ColorScheme 17 字段。
- **改造后**：将 `:40-43` 的 lerp 块整体替换为调用 `ThemeSpec.toM3Scheme(isLight)`；`ThemeSpec` 由 `ThemeStore` 5 色（primary/secondary/accent/background/textPrimary/textSecondary）构造；ColorScheme 全部 34 槽位由公式产出。
- **保留**：`:33` `ColorUtils.isColorLight` 判断、`:26` `AppConfig.isNightTheme`、error 色（暗 `#FF5252`/亮 `#E53935`，`:62/82`）。
- **关键封口**：推导只发生在运行时内存；`themeConfig.json` 与 SharedPreferences 旧格式**一字不改**。

## 四、文件变更锚点（Phase 0~4 逐文件）

| Phase | 改动文件 | 动作 | 说明 |
|-------|---------|------|------|
| P0 | `ui/widget/components/`（17 个新 .kt） | 新建 | 上节 2.1~2.6 组件签名全部落盘 |
| P1 | `ui/theme/LegadoTheme.kt` | 改造 | `:40-43` lerp → `toM3Scheme`；新增 `ui/theme/ThemeSpec.kt` |
| P1 | `ui/theme/ComposeActivitySupport.kt` | 不动 | 已是 Compose Activity 基座 |
| P2 | `ui/main/my/MyFragment.kt` | 改造 | `:55` binding 前缀改为 Compose；`:57-64` `replace(R.id.pre_fragment)` 仍保留但内容换 `ProfileScreen3Level()`；`MyPreferenceFragment` 收敛为列表数据源（不删任何入口） |
| P2 | `ui/main/bookshelf/style1/BookshelfFragment1.kt` | 可选重写 | `:78` `tabLayout.setupWithViewPager` 保留；列表可先不动 |
| P2 | `assets/defaultData/themeConfig.json` | **不写** | 保持旧格式 |
| P3 | `ui/book/read/` 浮层类（Dialog） | 改造 | Dialog → `AppModalBottomSheet` 容器；新增 `BookTocBookmarkSheet` |
| P4 | 全 App 巡检 | 审计 | 组件验收矩阵跑水平 |

## 五、PR 粒度任务 + 每 Phase KPI

### Phase 0 — 组件库建仓（独立可验证）
- **PR-0.1** `components/` 目录 + ThemeSpec + BadgeDot + ThemedSnackbarHost
- **PR-0.2** 设置三模板（Section/Card/ClickRow/ToggleRow/RowIcon）
- **PR-0.3** PillNavigationBar + SplicedColumnGroup + AppModalBottomSheet
- **PR-0.4** SwipeActionContainer + VerticalScrollbar + ShelfGridSkeleton + GlassTopAppBar + SettingsSearchBar + MetricGrid + SummaryCard + BookTocBookmarkSheet
- **KPI**：`./gradlew assembleAppDebug` 通过；`grep -r "Icons.Default.ChevronRight" app/src/main/java/io/legado/app/ui/widget/components` 应 >0（证明立体引用）；真机 L1 冒烟不崩。

### Phase 1 — 主题 34 槽位推导
- **PR-1.1** ThemeSpec.toM3Scheme（5 色→34 槽位，mix/hueShift/contrastOn）
- **PR-1.2** LegadoTheme.kt `:40-43` 替换；`themeConfig.json` 只读
- **KPI**：现有 16 个暗色/浅色主题在 Compose 页面渲染后**无花色错乱**；暗夜紫三槽位（surface/primaryContainer/tertiary）目检正确；回归 `./gradlew test` 通过。

### Phase 2 — 我的页/书架 Compose
- **PR-2.1** MyFragment 内容区换 `ProfileScreen3Level()`（用户卡/统计卡/高频卡/低频列表/搜索），实体入口零删除
- **PR-2.2** (可选) 书架骨架屏接入、style1 列表改 Grid Cache
- **KPI**：4 组高频入口（备份/主题/书源/Web服务）≤2 步可达；pref_main 死代码清理后 4 入口回归通过；真机 P4 页截图比对。

### Phase 3 — 阅读浮层 Sheet 化
- **PR-3.1** 目录→`BookTocBookmarkSheet`，书签→合并双 Tab
- **PR-3.2** 高亮选色等次要浮层 BatchDialog→BottomSheet
- **KPI**：`activity_book_read.xml:8` read_view 下浮层不遮挡正文；正文读翻页性能无回归；真机手势冒烟。

### Phase 4 — 一致性巡检
- **PR-4.1** 组件验收矩阵（对齐 NG_COMPONENT_ACCEPTANCE_CHECKLIST）全 App 扫码
- **PR-4.2** 对齐调色板/圆角/间距复核（SplicedColumnGroup 段落半径、RowIcon 36dp）
- **KPI**：0 处页面私有重复组件实现；公共 token 命中率 100%。

## 六、风险与封口（新增）

1. **themeConfig 格式不可改**（见上 ⚠️）——覆盖用户的 14 套历史主题与旧存档。
2. **MyFragment 需保 position 参数**（`:47-51`）——MainActivity 按 position 定位 Tab，改造时 `position` 逻辑不可删。
3. **PillNavigationBar 是 Compose，MainActivity 是 View 壳**——需 `AndroidView` 桥或整页 Compose；**建议 Phase 3 之后再做**（低风险序），先保证不破坏 `onNavigationItemSelected:155` 选中同步。
4. 阅读浮层改 Sheet 时保持 `ReadBookConfig` 每书独立配色不受影响（红线最后一道）。