# spec.md — 遗留列表 Compose 化收尾（CacheActivity + ExploreFragment 瀑布列表）

## Intent

archive 迁移后本项目 UI 已确立「Compose 优先」基线（见 `docs/project-rules/frontend-ui-standards.md`）。但还有两处**主列表**仍残留传统 `RecyclerView` + `Adapter`：

- **遗留项 7.11ai**：`CacheActivity`（书缓存列表页）主列表用 `binding.recyclerView`（`initRecyclerView()` 设 `LinearLayoutManager`）+ `CacheAdapter`（`DiffRecyclerAdapter<Book, ItemDownloadBinding>`）。
- **遗留项 7.11aj**：`ExploreFragment`（探索）**现代模式瀑布分支**用 `rvDiscoverBooks` + `ExploreShowWaterfallAdapter`（`StaggeredGridLayoutManager`）；同页 `composeDiscoverBooks`（`ComposeView`）已 Compose 化（`ExploreModernListScreen`）。

用户明确要求：将这两处列表 Compose 化，消除存量的 View 列表与 Adapter，统一走本项目已验证的 Compose 数据流与状态模型，并补齐设计文档（`docs/specs/list-residue-compose/`）。目标为与既有 Compose 页面（`UrlRecordScreen` / `PreciseManageScreen`）一致的纯 Compose 实现。

## Scope

### In-Scope（本次实现）

**A. `CacheActivity` 缓存列表页整页迁移**
- `binding.recyclerView` + `CacheAdapter` → `LazyColumn` + @Composable item（进入 `CacheScreen.kt`）。
- `CacheAdapter` 7 个 item 字段迁移为 @Composable item 状态：`tvName` / `tvAuthor` / `tvDownload`（下载进度/本地标记）/ `ivDownload`（播放/停止）/ `tvExport`（导出）/ `tvMsg`（导出消息）/ `progressExport`（导出进度条）。
- 点击回调迁移：`ivDownload` → `onDownloadToggle(book)`；`tvExport` → `onExport(book)`；条目本体无点击。
- 局部刷新迁移：`notifyItemChanged(bookUrl)`（`upAdapterLiveData` / `EXPORT_BOOK` / `UP_DOWNLOAD` 事件）→ 按 `bookUrl` 的 Compose 状态/Diff 局部重组。
- `upDownloadIv`（isLocal 隐藏 + 运行/停止图标切换）、`upExportInfo`（exportMsg / exportProgress）迁移到 Compose 状态。
- `initBookData()` 数据流 → `mutableStateListOf<Book>`；菜单中 `adapter.getItems()` / `getItem(position)` → 访问 Compose 列表状态。
- 顶栏已 Compose（`binding.composeTopBar.setContent { GlassTopAppBar }`，含 `composeTitle` / `composeSubtitle` / `menuExpanded` / `downloadMenuExpanded` / `groupMenuExpanded` / `downloadRunning` 等 `mutableStateOf`），**保留不动**；菜单全量 `AppDropdownMenu`（`buildDownloadMenuActions` / `buildGroupMenuActions` / `buildMenuActions`）保留。

**B. `ExploreFragment` 现代模式瀑布分支迁移**
- `rvDiscoverBooks`（仅 `AppConfig.discoveryPageLayout == 2` 时启用）瀑布分支 → `LazyVerticalStaggeredGrid`。
- `ExploreShowWaterfallAdapter` → 封面瀑布 item @Composable（承载 `setImageSizeRatio` 封面宽高比字段）。
- 瀑布点击复用 `showBookInfo(book)`。
- 瀑布滚动到底加载更多 → Compose 滚动状态检测（替代 `onScrollListener { onScrolled loadDiscoverBooks(false) }`）。
- `currentDiscoverScrollTarget()` 的 `rvDiscoverBooks` 分支、`updateModernTopBarOverlay()`（padding / clipToPadding / swipeRefresh offset）、`applyDiscoverBookContainerMargins()` → `composeDiscoverTopPadding` 等 Compose 状态统一接管。
- `classic` / `suite` 两级模式与 `ExploreModernListScreen` 现有能力保留，仅替换瀑布分支实现方式。

**C. 通用数据流统一**
- `adapter.setItems()` → `mutableStateListOf` 就地更新；`notifyItemChanged(bookUrl)` → 按 `bookUrl` 维度 Diff 局部重组。
- 列表状态与回调收口为 Screen 闭包（Activity/Fragment 管状态与数据源，Screen 纯 Compose 收 `items` + `onXxx`），遵循 `UrlRecordScreen` 壳层范式。

**D. 设计文档与登记**
- 生成 `docs/specs/list-residue-compose/{README,spec,design,tasks}.md`。
- 更新 `docs/project-flow/ui-standards/migration-registry.md`。
- 编译前更新 `app/src/main/assets/updateLog.md`。

### Out-of-Scope（本次不实现）

- **`CacheActivity` 顶栏 Compose**：已 Compose，不重做。
- **`ExploreFragment` 经典/套件模式**：`classic`（`rvFind`）与 `suite`（`composeDiscoverySuite`）分支不在本次替换范围。
- **`ExploreModernListScreen` 现代列表分支**（`layoutMode != 2`）：已 Compose，关联处仅作状态协同改动，不作为主体迁移对象。
- **视频播放/书源加载等业务逻辑**：`SearchBookOpenHelper.open`、`loadDiscoverBooks` 网络分页逻辑保持，仅改 UI 呈现层。
- 不引入新依赖、不改数据库 schema、不改 `Book` / `SearchBook` 数据模型。

## Approach

### Selected Approach：按「UrlRecordScreen 纯 Compose 壳层」范式，两处列表各走「列表段迁移」

统一采用本项目已验证的壳层范式：**宿主（Activity / Fragment）负责状态、数据源、回调闭包；Screen 纯 Compose 接收 `items` + `onXxx` 并自绘列表**。缓存页整页迁移，探索页瀑布段替换：

1. **缓存页（7.11ai）**：新建 `CacheScreen.kt`（纯 Compose，`LazyColumn` + `itemsIndexed(key = { it.bookUrl })`），承载 7 字段 item 与本地/运行切换、导出进度条；`CacheActivity` 保留顶栏 Compose 与菜单构建，移除 `initRecyclerView()` / `setContentView` 的 RecyclerView 分支，数据流改 `mutableStateListOf<Book>`；`CacheAdapter.kt` 删除（转换为 Compose item）。
2. **探索瀑布段（7.11aj）**：在现有 `ExploreModernListScreen`（`layoutMode != 2`）基础上，新增瀑布布局变体（`LazyVerticalStaggeredGrid`），瀑布 item 复用 `showBookInfo` 点击、滚动状态检测加载更多；`ExploreFragment` 的 `rvDiscoverBooks` 分支替换为 Compose 状态驱动，`upDiscoverTopPadding` 等偏移由 Compose 状态接管；`ExploreShowWaterfallAdapter.kt` 删除（转为 Compose item）。
3. **增量交付**：缓存页先落地（独立页面、回归面小），探索瀑布段后落地（与现有 Compose 列表协同）；每步编译 + 真机回归。

理由：复用已验证壳层范式与 `ExploreModernListScreen`，无新增依赖；两处均为纯 UI 呈现层替换，业务数据流（DAO flow、网络分页）保持，风险收敛为「列表重组 + 状态接线」。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 保留 RecyclerView + Adapter，仅修观感 | 不动列表容器，只做样式调整 | 违背「Compose 优先」基线；遗留工具类不退役，后续每处列表维护仍 View/Compose 双实现 |
| 用通用 Compose LazyColumn 直接替换缓存列表，但保留 Adapter 过渡 | 新增 LazyColumn 同时保留 CacheAdapter 兜底 | item 逻辑（本地切换/导出进度/运行图标）被拆到 View 与 Compose 双份，状态分叉、易失同步；违背单数据流 |
| 探索瀑布独立建成单独 Compose 区块（与 ExploreModernListScreen 平级） | 瀑布列表独立 `@Composable` 区块，按 layoutMode 切换 | 与 `ExploreModernListScreen` 存在大量共享（加载/HasMore/滚动到底/顶栏 overlay/空态），独立区块重复状态与回调接线，维护成本高 |
| 两处列表都用「过渡期 View+Compose 共存」 | 先加 Compose 壳，内部仍包 RecyclerView | 叠加后无实际收益，状态仍需透传，且 Compose 内嵌 View 列表性能与重组语义差 |

### Drawbacks

- **item 7 字段/点击回调迁移工作量大**：缓存 item 含下载进度、本地标记、播放/停止切换、导出进度条，状态维度多，需逐一迁移并保证事件驱动局部刷新语义不丢（`UP_DOWNLOAD` / `EXPORT_BOOK`）。
- **瀑布 item 封面宽高比依赖**：`ExploreShowWaterfallAdapter` 依赖 `setImageSizeRatio` 宽度比字段设置 item 高度，Compsoe 侧需等价计算 `aspectRatio`，否则瀑布错位。
- **滚动到底加载更多的信号语义**：View `onScrollListener` 的阈值/去重逻辑需在 Compose `derivedStateOf` / `LaunchedEffect` 中等价复刻，避免重复加载。
- **`ExploreModernListScreen` 结构需小幅改动**：为引入瀑布变体，需调整其参数签名（增加瀑布分支状态），存在号状态协同小回归面。

接受上述缺点，换取存量列表/适配器类退役、UI 栈收敛为单 Compose、数据流统一，且复用已验证组件、无新增依赖。

### Prior Art

- 纯 Compose 壳层范式：`UrlRecordScreen`（[UrlRecordScreen.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/urlrecord/UrlRecordScreen.kt)）——Activity 管状态/数据源/回调闭包，Screen 纯 Compose 收 `items` + `onXxx`，`LazyColumn` + `itemsIndexed(key={it.id})`，列表项 private @Composable，顶栏 `GlassTopAppBar` + `AppDropdownMenu`。
- Activity 壳 + 纯 Compose Screen：`PreciseManageScreen`（[app/src/main/java/io/legado/app/ui/config/](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/config/)）。
- 现代列表已有 Compose 实现：`ExploreModernListScreen`（[ExploreModernListScreen.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/explore/ExploreModernListScreen.kt)）。
- 组件库与壳层框架：`app/src/main/java/io/legado/app/ui/widget/components/`、`ui/widget/compose/`（`ComposeDialogFragment` / `AppManagementScaffold` 等）。
- 迁移基线：`docs/project-rules/frontend-ui-standards.md`（强制基线）、`docs/project-flow/ui-standards/`（`migration-registry.md`）、既有迁移登记（如 `docs/specs/subpage-topbar-unify/tasks.md` 的豁免/迁移结论模式）。

## Requirements

### A. 缓存列表页（7.11ai）

- **FR-A1** `binding.recyclerView` / `CacheAdapter` 移除，主列表为 `LazyColumn`。
- **FR-A2** item 7 字段全部迁移为 @Composable：`tvName` / `tvAuthor` / `tvDownload`（下载进度/本地标记）/ `ivDownload`（播放/停止）/ `tvExport`（导出）/ `tvMsg`（导出消息）/ `progressExport`（导出进度条）。
- **FR-A3** 点击行为等价迁移：`ivDownload` → `onDownloadToggle(book)`；`tvExport` → `onExport(book)`；条目本体无点击。
- **FR-A4** `upDownloadIv`：isLocal 隐藏 + 运行/停止图标切换，语义保留。
- **FR-A5** `upExportInfo`：`exportMsg` / `exportProgress` 语义保留。
- **FR-A6** 局部刷新：`notifyItemChanged(bookUrl)`（`upAdapterLiveData` / `EXPORT_BOOK` / `UP_DOWNLOAD`）→ 按 `bookUrl` Compose 状态/Diff 局部重组。
- **FR-A7** `initBookData()` 数据流（DAO → 过滤 → 排序）→ `mutableStateListOf<Book>`。
- **FR-A8** 菜单中 `adapter.getItems()` / `getItem(position)` → Compose 列表状态取值。
- **FR-A9** 顶栏（`GlassTopAppBar` + `AppDropdownMenu` 三类菜单）行为不丢，仅解耦 adapter 依赖。

### B. 探索瀑布段（7.11aj）

- **FR-B1** `rvDiscoverBooks` + `ExploreShowWaterfallAdapter` 移除，瀑布为 `LazyVerticalStaggeredGrid`。
- **FR-B2** 封面瀑布 item @Composable，承载 `setImageSizeRatio` 宽高比（`aspectRatio`）字段。
- **FR-B3** 瀑布点击复用 `showBookInfo(book)`。
- **FR-B4** 滚动到底加载更多由 Compose 滚动状态检测接管（等价 `loadDiscoverBooks(false)` 触发）。
- **FR-B5** `currentDiscoverScrollTarget()` 的 `rvDiscoverBooks` 分支 → Compose 状态。
- **FR-B6** `updateModernTopBarOverlay()`（padding / clipToPadding / swipeRefresh offset）→ `composeDiscoverTopPadding` 统一接管。
- **FR-B7** `applyDiscoverBookContainerMargins()` → Compose `modifier` padding。
- **FR-B8** `classic` / `suite` / 现代列表（`layoutMode != 2`）能力与 `ExploreModernListScreen` 不受破坏。

### C. 非功能需求（NFR）

- **N1** 不引入新依赖、不改数据库 schema、不改 `Book` / `SearchBook` 模型。
- **N2** 列表滚动性能等价或优于原 RealcyclerView（`LazyVerticalStaggeredGrid`/`LazyColumn` 具备 item 复用能力）；无残留调试日志（Grep `Log.d|Log.e` = 0）。
- **N3** updateLog 同步更新（编译前）。
- **N4** 迁移不改变原有业务逻辑——`SearchBookOpenHelper.open`、`CacheBook.remove`/`CacheBook.start`、网络分页、DAK 数据流仅 UI 呈现层变换。
- **N5** `CacheAdapter.kt` / `ExploreShowWaterfallAdapter.kt` 删除或转为 Compose item 文件后，无残留引用。

## Scenarios

### 正常场景

1. 用户进入「缓存」页：列表为 `LazyColumn`，7 字段 item 完整呈现（书名/作者/下载进度/本地标记/播放或停止图标/导出/导出消息与进度条），观感与迁移前等价。
2. 用户点播放/停止图标 → 触发 `onDownloadToggle(book)`，对应 item 图标/进度随 `UP_DOWNLOAD` 局部更新（不整表刷新）。
3. 用户点导出 → `onExport(book)`，导出消息/进度条随 `EXPORT_BOOK` 局部更新。
4. 用户点缓存页顶栏「更多」等菜单项（导出全部/净化/字符集等）→ 菜单行为与迁移前一致，取值自 Compose 列表状态。
5. 用户在探索页将布局设为瀑布（`discoveryPageLayout==2`）：瀑布 `LazyVerticalStaggeredGrid` 展示封面瀑布，封面宽高比不塌陷；滚动到底自动加载更多。
6. 用户点瀑布某一封面 → 复用 `showBookInfo(book)` 进入详情。
7. 用户在探索页切换 `classic` / `modern` / `suite` 模式 → 瀑布与既有 `ExploreModernListScreen` / 套件分支正常切换，顶栏 overlay / padding 正确。

### 边界/异常场景

1. **分组切换/排序变更**（缓存页）：`flowByGroup(groupId)` 变更后列表正确重组，`getItem(position)` 取值不越界。
2. **空列表**：缓存为空或瀑布无数据时，空态显示正常、无崩溃。
3. **滚动到底高频触发**：瀑布加载更多去重，不重复请求，`HasMore=false` 正常停止。
4. **夜间/主题切换**：顶栏 overlay padding 与 `composeDiscoverTopPadding` 随主题/顶栏样式刷新，无硬编码颜色残留（`updateModernTopBarOverlay` 迁移后不丢 clipToPadding/padding）。
5. **旧包覆盖安装**：删除 adapter 类后无残留 `setContentView`/`findViewById` 引用导致的崩溃。
6. **封面加载失败/无封面**：瀑布 item `aspectRatio` 回退默认比例，不塌陷、不闪跳。