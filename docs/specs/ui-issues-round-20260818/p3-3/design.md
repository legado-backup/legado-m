# design.md — P3-3 长尾页 Compose 化收尾（专项设计）

> 本文是 `ui-issues-round-20260818` 的 **P3-3 子 spec 专属设计文档**，聚焦「除阅读详情页外，剩余长尾页内容区由 View 迁移到 Compose Lazy*」的深入设计。承接主 spec [README](../README.md) 问题 3/9 与主 [tasks.md](../tasks.md) 4.3.7「P3 长尾页增量推进」。设计原则与红线继承主 spec（AD-02 正文引擎零改动、AD-21 组件复用强制、AD-06 只恢复不新增）。

---

## 1. 范围界定（Scope 细化）

### 1.1 本批次候选页面（源码逐一核实 2026-08-18，结论已确定无待办项）

> 依据 `docs/temp-analysis/compose-status-inventory.md` §5「迁移缺口 Top」+ §6.4 P3 长尾清单，结合对源码的**逐一 Read/Grep 核实**（下表"现状"均为本次源码核实确定结论）。**本批次无"待实施确认"项——已核实页面无一致性的存疑点。**

| 页面 | 壳路径 | 现状（本次源码核实确定） | 迁移工作量 | 优先级 | 备注 |
|------|--------|-----------------|-----------|--------|------|
| 搜索页 | `ui/book/search/SearchActivity.kt` | 仅 `composeTopBar.setContent`（SearchActivity.kt:121）；主体 `RecyclerView` + `SearchAdapter` + `HistoryKeyAdapter` + `BookAdapter` + `SearchScopeDialog` | 高 | 🥇 1 | 多 Adapter 混合，滑块筛选 |
| 全文搜索 | `ui/book/searchContent/SearchContentActivity.kt` | 仅 `composeTopBar.setContent`(:100)；主体 `RecyclerView` + `SearchContentAdapter` + `SearchResult` + DiffUtil(`notifyItemRangeChanged`) | 中 | 🥇 5 | 定位跳章逻辑在 Activity |
| 目录页 | `ui/book/toc/TocActivity.kt` + 3 Fragment | 仅 `composeTopBar.setContent`(:111)；三 Fragment `ChapterListFragment`/`BookmarkFragment`/`HighlightFragment` 仍用 XML 布局（fragment_chapter_list/fragment_bookmark）+ 各自 Adapter，ViewPager2 + TabRow | 高 | 🥇 7 | 三 Tab 三列表，最复杂 |
| 订阅源管理 | `ui/rss/source/manage/RssSourceActivity.kt` | 仅 `composeTopBar.setContent`(:153)；主体 `RecyclerView` + `RssSourceAdapter` + `SelectActionBar` + `DragSelectTouchHelper`(:458) + `ItemTouchHelper`(:463)，含多视图/滑选/拖拽；弹窗多为公共 `alert{}`+`AlertDialog`（IO 库公共包装），私有 dialog 为 `ImportRssSourceDialog`/`GroupManageDialog`/`CheckRssSourceConfig` + `SourceFolderAdapter.showConfigDialog`(:517) | 极高 | 8 | 手势复杂，滑选/拖拽拆独立任务 |
| RSS 文章列表 | `ui/rss/article/RssArticlesFragment.kt` | **纯 View（无 Compose 桥接）**｜`BaseRssArticlesAdapter` + `DiffUtil`(setItems) + `LoadMoreView` + OnScrollListener | 高 | 12 | 5 种样式，分页/预加载 |
| 替换规则 | `ui/replace/ReplaceRuleActivity.kt` | 仅 `composeTopBar.setContent`(:117)；`ReplaceRuleScreen.kt` 实为 **`ReplaceRuleTopBar`**（顶栏 composable，已 Compose）；主体 `RecyclerView` + `ReplaceRuleAdapter` + `ItemTouchHelper`(拖拽:175) + `DragSelectTouchHelper`(滑选:168) + `SelectActionBar` | 中 | 16 | 顶栏已 Compose 免动；主体列表待迁移，拖拽/滑选拆独立任务 |
| RSS 搜索 | `ui/rss/search/RssSearchActivity.kt` | 仅 `composeTopBar.setContent`(:111)；`RecyclerView` + `RssSearchAdapter` + 历史 `rvHistoryKey` + `RssSearchHistoryAdapter` + `SearchScopeDialog` | 中 | 19 | 与书搜索同构，双列表 |

### 1.2 明确不在本批次范围（Out of Scope）
- **阅读详情页**（`ui/book/read/page/` 29 文件）：AD-02 红线零改动。
- **纯 View 内核页**：漫画 `ReadMangaActivity`、视频 `VideoPlayerActivity`、WebView 池、代码编辑器、扫码、透明窗——AD-02/N 类不透传。
- **订阅源编辑页** `RssSourceEditActivity`：主体 XML 表单被用户认可，保留不迁移（主 spec E6 列 N）。
- **业务逻辑 / 数据层**：仅 UI 壳层迁移，ViewModel/DAO/规则引擎零改动。

---

## 2. 统一迁移模式（Technical Approach）

所有候选页采用**同一套双轨迁移范式**（对齐主 spec P3-3b 已交付的 `OtherConfig`/`BackupConfig` 及 ui-redesign-m3 已验证范式）：

```
Layer            Change
──────────────────────────────────────────────────────────────────
Activity/Fragment（壳）  保持继承 + 生命周期 + Intent 处理 + ViewModel 获取
                          仅将「内容区 setContentView/RecyclerView」替换为
                          binding.composeHost.setContent { LegadoTheme { XxxScreen(...) } }
                          副作用（权限/文件选择/Dialog 回调/startActivity）留在壳回调上抛

ComposeScreen（新增）    内容区全 Compose：
                          - 列表 → LazyColumn / LazyVerticalGrid
                          - Item → 公共组件或不间断 Composable
                          - 空态 → EmptyStatePlaceholder
                          - 加载更多 → LazyListState + derivedStateOf 触底检测
                          - State 提升到底层 Composable 参数 + 壳回调上抛
```

**红线（逐字平移，禁止重写）**：
- 探索/搜索的 **JS 双求值链**、`InfoMap LruCache`、`SourceLoginJsExtensions` 桥——迁移的是 UI 展示层，数据获取与规则评估代码不动。
- DiffUtil 语义 → Compose 由 `Lazy*` 的 `key` + `items` 天然差分替代；**不手写 Diff 逻辑**。
- `FastScrollRecyclerView`/`UpLinearLayoutManager` 增强滚动 → 复用已存在的 `VerticalScrollbar`/`LazyListFastScroller` 公共组件，不逐字搬 View 实现。

---

## 3. 逐页迁移规格

> 每页给出：① 数据源（沿用 ViewModel，不改）；② 列表映射；③ Item 组成；④ 交互=壳回调；⑤ 私有弹窗收敛；⑥ 风险点；⑦ 验收。

### 3.1 搜索页 SearchActivity（优先级最高）

- **数据源**：`SearchViewModel`（`ui/book/search/SearchViewModel.kt`）沿用，不改。
- **列表映射**：搜索结果 `SearchAdapter` → `LazyColumn`；搜索历史 `HistoryKeyAdapter`（Flexbox）→ `LazyVerticalGrid`/`FlowRow`；书籍分书源 `BookAdapter` → 分组 `LazyColumn`。
- **Item 组成**：三 adapter 对应三种 Composable，复用 `ListCard`/`CoverImageView` 等公共组件。
- **交互回调**：点击项/长按/滑选多选 → 统一回调到 Activity 壳现有 handler（不改壳内 startActivityForBook/加入书架等副作用逻辑）。
- **私有弹窗**：`SearchScopeDialog` → Dialog 族（`AppSelectDialog`）或 `AppModalBottomSheet`（底部多选范围），按语义三选一。
- **风险点**：搜索结果项与书源分组的滚动联动、滑选多选的手势在 Compose 下需 `combinedClickable`+拖拽检测；高频输入防抖在 Compose 侧用 `snapshotFlow`。
- **验收**：搜索→选书源→进详情全链路正常；历史词删除/清空生效；分组滚动不卡顿（≥200 项）。

### 3.2 全文搜索 SearchContentActivity

- **数据源**：`SearchContentViewModel` 沿用。
- **列表映射**：`SearchContentAdapter`+`SearchResult` → `LazyColumn`（`SearchResult` data class 为 Item 数据源）。
- **交互**：点击项跳阅读页定位；加载更多触底。
- **私有弹窗**：无（核对后若有关闭）。
- **风险点**：中——ListAdapter Diff 语义由 key 替代。
- **验收**：全文搜索词高亮/命中跳转正常。

### 3.3 目录页 TocActivity（含 3 Fragment）

- **数据源**：`TocViewModel`、`BookmarkAdapter`、`HighlightAdapter` 对应三 Tab 数据流沿用（Activity 已验证 `bookTocBookmarkSheet` 已 Compose，仅三列表主体迁移）。
- **列表映射**：
  - `ChapterListFragment` → `LazyColumn` 章节目录（高亮当前章、未读标识、前 an 列表语义）。
  - `BookmarkFragment` → `LazyColumn` 书签。
  - `HighlightFragment` → `LazyColumn` 高亮。
- **交互**：目录点击跳章节（Activity 结果回调 `TocActivityResult` 沿用）；书签/高亮点击跳阅读页；滑选多选删书签/高亮。
- **私有弹窗**：`TxtTocRuleDialog`/`TxtTocRuleEditDialog` → Dialog 族核对；`WaitDialog` 保留（公共）。
- **风险点**：三 Tab 在 ViewPager2 内的列表状态保持（ScrollableTabRow 已在壳，三个 LazyColumn 独立 ScrollState）；书签/高亮数量大时滚动流畅性。
- **验收**：目录快速跳章、书签/高亮增删、当前章高亮定位正确。

### 3.4 订阅源管理 RssSourceActivity（风险最高，建议最后实施）

- **数据源**：`RssSourceViewModel` 沿用。
- **列表映射**：`RssSourceAdapter`（多视图 Grid/List/Compact）→ `LazyVerticalGrid`/`LazyColumn` 按当前布局切换；`RssSourceAdapterCompact`/`Grid` 三态由 Compose 布局参数按 `sourceLayout` 切换。
- **交互**：`SelectActionBar` 多选批量（启用/禁用/分组/删除）→ 壳 `SelectActionBar` 保留（View 组件）或 Compose 底部栏；`DragSelectTouchHelper` 拖拽滑选 → Compose `combinedClickable` + 自定义拖拽。
- **私有弹窗**（已核实）：多为公共 `alert{}`/`AlertDialog`（`io.legado.app.lib.dialogs.alert` 公共包装，语义已合格）；私有 dialog-fragment `ImportRssSourceDialog`/`GroupManageDialog`/`CheckRssSourceConfig` + `SourceFolderAdapter.showConfigDialog` 规范归属公共族（GroupManageDialog 为书架复用组件，保持复用），无页面私有新增。
- **风险点**：多视图切换 + 滑选多选 + 拖拽排序的组合交互迁移难度最高；`DragSelectTouchHelper` 滑选在 Compose 需自定义 PointerInput。**建议拆分：先列表内容 Compose 化，滑选多选交互作为独立任务验证，避免一次性改动过大回归**。
- **验收**：三视图切换、批量启用/禁用/分组、拖拽滑选、分组管理（GroupManageDialog 复用）全部正常。

### 3.5 RSS 文章列表 RssArticlesFragment（纯 View，最独立）

- **数据源**：`RssArticlesViewModel` 沿用（含分页/预加载逻辑），不改。
- **列表映射**：`RssArticlesAdapter1-5` 五种样式 → `LazyVerticalGrid`/`LazyColumn` 按文章展示样式切换；`LoadMoreView` 预加载 → `LazyListState` 触底自动加载。
- **交互**：点击文章进阅读；长按收藏/删除；滑选多选。
- **私有弹窗**：`ReadRecordDialog` → Dialog 族核对。
- **风险点**：中——5 样式切换 + 预加载；但无 ViewPager/拖拽，主体单一列表。
- **验收**：文章流分页加载、样式切换、点击读文、收藏/删除正常。

### 3.6 替换规则（已核实：顶栏已 Compose，主体 View 内核保留）

- **已核实结论（源码 Read，ReplaceRuleActivity.kt:117/168/175）**：`composeTopBar.setContent { ReplaceRuleTopBar(...) }` 已接入顶栏与搜索；主体仍 `binding.recyclerView` + `ReplaceRuleAdapter` + `ItemTouchHelper`(拖拽:175) + `DragSelectTouchHelper`(滑选:168) + `SelectActionBar`(批量)。`ReplaceRuleScreen.kt` 实际文件名为 `ReplaceRuleTopBar`（顶栏 composable），**非孤立 Screen，无需关闭或替换**。
- **本页迁移范围收敛**：仅主体列表 Compose 化（`LazyColumn`，`ReplaceRuleViewModel` 沿用）；顶栏/搜索/菜单/GroupManageDialog 已 Compose 免动。
- **手势边界**：拖拽排序 + 滑选多选保留 View 层（AD-P33-04），作为独立任务，不阻塞主体列表迁移。
- **副作用**：`setResult(RESULT_OK)` 通知、`ContentProcessor.upReplaceRules()` 重建、导入/导出/扫码（registerForActivityResult）、枚举删除/启用/停用/置顶——全部留在 Activity 壳，Compsoe 列表仅回调上抛。
- **验收**：主体列表 Compose 化后仍支持过滤条件（启用/停用/无分组/分组:xx）与实时搜索结果，拖拽/滑选不回归（L2 起独立验证）。

### 3.7 RSS 搜索 RssSearchActivity

- **数据源**：`RssSearchViewModel` 沿用。
- **列表映射**：`RssSearchAdapter` + `RssSearchHistoryAdapter` → `LazyColumn`。
- **交互**：搜索/历史/进文章详情（`RssArticleInfoActivity`）沿用。
- **私有弹窗**：`ChangeRssArticleSourceDialog`/`SearchScopeDialog` → Dialog 族核对。
- **验收**：RSS 关键词搜索、历史、结果点击进详情正常。

---

## 4. Architecture Decisions（ADR Y-Statement）

### AD-P33-01: 长尾页迁移统一走「壳保持 + composeHost.setContent」双轨模板
- **Context**: 本批次 7 页均为「Activity/Fragment 壳 + View 主体」，且已有 `OtherConfig`/`BackupConfig` 双轨迁移先例（主 spec P3-3b 已交付）。
- **Concern**: 若逐页自定义栈的组织方式，会造成范式漂移、回退困难。
- **Decision**: 统一使用 `binding.composeHost.setContent { LegadoTheme { XxxScreen(...) } }` 双轨模板；壳仅保留生命周期/Intent/权限/文件选择/Dialog 宿主，副作用回调上抛。
- **Goal**: 迁移范式单一可复制，Code Review 体感一致，回退最小化。
- **Tradeoff**: 壳层 Activity 仍保留 View 绑定，未完全 Compose；但符合「主体内容区 Compose 化」目标且控制回归面。
- **Status**: Proposed

### AD-P33-02: 数据层读取沿用既有 XxxViewModel，零业务逻辑改动
- **Context**: 各页 ViewModel 已承载数据获取（Flow/协程链）、Diff 语义、规则评估（JS 双求值等）。
- **Concern**: 迁移 UI 时若重写 VM，会引入高概率回归且触碰内核。
- **Decision**: Screen 只消费 `XxxViewModel` 的状态（`collectAsStateWithLifecycle`），不新建 VM、不搬逻辑；Activity 壳保留 VM 获取。
- **Goal**: 业务零改动，UI 层隔离，回归最小。
- **Tradeoff**: Compose 侧某些原本 Holnder 内联的状态需改用 ViewModel LiveData/MutableState 桥接，属合理适配。
- **Status**: Proposed

### AD-P33-03: DiffUtil/ViewHolder Adapter → Lazy*/key 差分，不手写 Diff
- **Context**: 现有 Adapter 大量用 DiffUtil 做高效差分（搜索/目录/订阅源/RSS 文章）。
- **Concern**: Compose 下 DiffUtil 无直接等价物，但 `Lazy*` 用 `key` 物化 + 数据比较已达同样目的。
- **Decision**: 直接用 `items(items, key={it 唯一ID})`；不引入第三方 Diff 库，不把 DiffUtil 搬进 Compose。
- **Goal**: 保持滚动/增量更新性能，代码量下降。
- **Tradeoff**: 超大数据集（如万级目录）理论性能需 Verify；实施验证是否需分页/稳定 key。
- **Status**: Proposed

### AD-P33-04: 复杂交互（滑选多选/拖拽排序）首期保留 `AndroidView(RecyclerView)` 桥接或拆分为独立任务
- **Context**: 订阅源管理 `DragSelectTouchHelper` 滑选多选、替换规则拖拽排序均为成熟 View 手势实现；Compose 无现成等价（Reorderable 需额外依赖）。
- **Concern**: 强行一次性迁移复杂手势到 Compose 自研 PointerInput，风险高、易回归。
- **Decision**: **内容区列表先用 `Lazy*` Compose 化；滑选多选/拖拽排序作为独立验证任务**，需要时对 `AndroidView(RecyclerView)` 桥接保留手势层。不引入设计未确认的新 Compose 拖拽依赖。
- **Goal**: 分批规避高风险手势迁移，保证每步可编译可验收。
- **Tradeoff**: 页内存在"列表 Compose + 手势 View 桥"的半混合态，视觉一致但内层手势保留；待手势方案成熟后再统一。
- **Status**: Proposed
- **实施前置决策点（非偷懒项）**：替换规则/订阅源管理的拖拽排序是否引入 `sh.calvin.reorderable:reorderable`（Apache）或继续 `AndroidView(RecyclerView)` 桥，属**需经用户确认的依赖引入决策**，故不进 tasks 主路径，单列 `P3-3#6.2`/`#4.4` 独立任务，由主代理在实施该任务时用 AskUserQuestion 向用户确认后落地，前序主体列表迁移不阻塞。

### AD-P33-05: 私有弹框按语义三选一收敛公共族，禁止页面私有
- **Context**: 各页存在 `SearchScopeDialog`/`ChangeRssArticleSourceDialog`/`TxtTocRuleDialog` 等私有弹框。
- **Concern**: 主 spec AD-21 已强制组件复用；私有弹框违反 P3-3c 巡检门禁。
- **Decision**: 按「右上角=AppDropdownMenu / 底部=AppModalBottomSheet / 悬浮=AppEditDialog+AppSelectDialog+ConfirmDialog」三选一收敛；特殊业务弹框（如 TxtTocRule 内容编辑）核对是否已有公共等价，无则标注。
- **Goal**: P3-3c grep 巡检 0 私有弹框。
- **Tradeoff**: 个别业务弹框（URL 规则编辑）跨 View/Compose，收敛前需确认语义安全（对齐主 spec P3-2b 第④点的谨慎原则）。
- **Status**: Proposed

---

## 5. Data Flow（数据流）

### 5.1 通用壳→Screen 数据流
```
AndroidView 壳（生命周期/Intent）
   │  ViewModel 已由 by viewModels 持有；LiveData/Flow 由 collectAsStateWithLifecycle 收集
   ▼
ComposeScreen（新增，纯 UI）
   │─① 状态：val list by vm.xxx.collectAsStateWithLifecycle()
   │─② 列表：LazyColumn { items(list, key=it.id) { Item(...) } }
   │─③ 触底：rememberLazyListState() + derivedStateOf { lastVisibleIndex>=total- threshold } → 回调 vm.loadMore()
   │─④ 空态：list.isEmpty() → EmptyStatePlaceholder
   ▼
回调上抛 → 壳 handler（startActivity / DialogFragment / 单次副作用）
```

### 5.2 搜索页典型数据流（代表其余同构页）
```
输入防抖 → SearchViewModel.searchObservable (Flow) 
         → 分书源结果分组（InfoList/LruCache 内核不动）
         → SearchScreen collect 分组结果
         → LazyColumn(items=grouped, key=bookUrl) 渲染
         → 点击 → 回调壳 → startActivityForBook（阅读页）
         → 滑选多选 → 回调 → 壳 SelectActionBar 语义 → 批量操作
```

### 5.3 订阅源管理布局切换数据流
```
壳 menu → AppConfig.sourceLayout 变更（postEvent）
       → RssSourceViewModel 观察 → 暴露 currentLayout 状态
       → Screen 按 currentLayout 切换 LazyColumn ↔ LazyVerticalGrid
       → 复用 ListLayoutMenu（公共组件已存在）驱动
```

---

## 6. File Changes（文件变更）

| 文件 | 类型 | 变更内容 |
|------|------|---------|
| `ui/book/search/SearchActivity.kt` | 修改 | 内容区改 `composeHost.setContent`；新增 `SearchScreen` 引用；私有弹框收敛 |
| 新增 `ui/book/search/SearchScreen.kt` | 新增 | 搜索结果+历史+分组 Lazy 列表，State 提升到壳 |
| `ui/book/search/SearchAdapter.kt`/`HistoryKeyAdapter.kt`/`BookAdapter.kt` | 废弃候选 | 迁移后若无 View 调用可删（实施确认） |
| `ui/book/search/SearchScopeDialog.kt` | 修改 | 收敛公共弹框族 |
| `ui/book/searchContent/SearchContentActivity.kt` + `SearchContentScreen.kt`(新增) | 修改/新增 | 全文搜索 Lazy 化 |
| `ui/book/toc/TocActivity.kt` + `ChapterListFragment`/`BookmarkFragment`/`HighlightFragment` | 修改 | 三 Tab 列表改 Compose；Fragment 壳保留生命周期 |
| 新增 `ui/book/toc/ChapterListScreen.kt`/`BookmarkScreen.kt`/`HighlightScreen.kt` | 新增 | 三列表 Compose |
| `ui/rss/source/manage/RssSourceActivity.kt` + 新增 `RssSourceManageScreen.kt` | 修改/新增 | 多视图列表 Compose；滑选/拖拽独立任务 |
| `ui/rss/source/manage/RssSourceAdapter*` | 废弃候选 | 迁移后实施确认 |
| `ui/rss/article/RssArticlesFragment.kt` + 新增 `RssArticleListScreen.kt` | 修改/新增 | 5 样式列表 + 预加载 Compose 化 |
| `ui/rss/article/RssArticlesAdapter1-5` | 废弃候选 | 迁移后实施确认 |
| `ui/replace/ReplaceRuleActivity.kt` + 新增 `ReplaceRuleListScreen.kt` | 修改/新增 | 主体列表 `LazyColumn` Compose 化（`ReplaceRuleListScreen` 新增）；顶栏 `ReplaceRuleTopBar`/`ReplaceRuleScreen.kt` 已 Compose 免动；拖拽/滑选拆独立任务 |
| `ui/rss/search/RssSearchActivity.kt` + `RssSearchScreen.kt`(新增) | 修改/新增 | RSS 搜索 Lazy 化 |
| `app/src/main/res/values/strings.xml` | 修改 | 新增迁移所需字符串（禁止硬编码，逐页按需） |
| 回执登记 | — | 每页完成后在 §7 回执表登记（缺失=未完成，对齐主 spec P3-3c） |

---

## 7. 实施回执表（每页完成后登记）

> 回执缺失视为未完成（门禁）。实施中若与本节设计不符，按主 spec 要求：全面分析决策后反哺回执表新增「实施反哺」段。

| 页面 | 设计状态 | 实施完成级别 | 回执 |
|------|---------|-------------|------|
| 搜索页 | 已设计 | L1（待 L2 真机） | 已实施：`compose_host` + `SearchScreen.kt`；搜索结果 `LazyColumn`(key=bookUrl)；Item 复用 `ListCard`+封面 `AndroidView(CoverImageView)` 桥接（保留 Glide/loadOnlyWifi）+`TagChip` 类型标签；空态 `EmptyStatePlaceholder`；FastScroller；LazyListState+derivedStateOf 触底自动加载；书架归属实时重算（upAdapterLiveData→composeSearchBooks 重赋值触发重组）；顶栏/输入帮助区/FAB/跳转逻辑保留 · 实施反哺①搜索范围弹框「SearchScopeDialog」保留（走 AppDropdownMenu 菜单隐藏一级+Dialog 二级高级，壳 handler 沿用，非孤立私有粗暴收敛）②历史/书架 chip 列表保留 View（Flexbox+长按 ExplosionField 爆炸删除动画，Compose 无等价，按 AD-P33-04 拆独立任务，不阻塞搜索主体 LazyColumn 化）③搜索主体原 SearchAdapter 仅点击无长按/滑选，1.5 无迁移缺口 |
| 全文搜索 | 已设计 | L1（待 L2 真机） | 已实施：`composeHost` + `SearchContentScreen.kt`；LazyColumn+itemsIndexed(index 作 key)；Item 复用 `ListCard`；高亮复用 `getHtmlCompat`+TextView 桥；FastScroller 替代滚动条；顶栏/底部跳转栏/进度 View 保留 · 实施反哺①SearchResult 无稳定唯一 ID，key 退化为 position（结果顺序追加即去重）②Spanned 不能直接进 Compose Text，用 `AndroidView(AppCompatTextView)` 桥接保持高亮语义③原"触底加载更多"实为流式章节追加搜索，由 status 快照驱动，非分页触底 |
| 目录页 | 已设计 | — | 待填 |
| 订阅源管理 | 已设计（滑选拆独立） | — | 待填 |
| RSS 文章列表 | 已设计 | — | 待填 |
| 替换规则 | 已设计（顶栏已 Compose，仅主体迁移+滑选/拖拽拆独立） | — | 待填 |
| RSS 搜索 | 已设计 | — | 待填 |

> 完成级别：L1=代码完成+编译；L2=功能可运行；L3=真实场景回测。禁止混用（对齐主 spec 三级完成标准）。