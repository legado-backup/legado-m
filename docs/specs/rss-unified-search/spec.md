# 订阅源统一搜索 - 需求规格文档 (Spec)

## Intent (意图)

为订阅源（RSS源）栏目提供"统一搜索所有订阅源内容"的能力，对标书架顶部"搜索所有书源"功能。当前订阅源栏目（`RssFragment`）顶部搜索框仅用于按订阅源**名称**过滤订阅源列表，用户无法跨源搜索文章内容；用户必须先进入某个订阅源、再使用源内搜索（前提是该订阅源配置了 `searchUrl`）。

本次需求将搜索框行为扩展为"跨源内容搜索入口"，让用户在订阅源栏目直接输入关键词即可搜索所有支持搜索的订阅源内容，并将结果聚合展示。

## Scope (范围)

### In Scope（本次实现）

1. 新增 `RssSearchActivity` + `RssSearchViewModel` + `RssSearchModel` 三层架构（参考书源搜索）
2. 新增 `SearchRssArticle` 内存数据模型（含 `origins` 多源聚合字段）
3. 新增 `RssSearchAdapter` 列表展示搜索结果
4. 新增 `ChangeRssArticleSourceDialog` 文章换源对话框
5. 改造 `RssFragment` 顶部搜索框：`onQueryTextSubmit` 跳转 `RssSearchActivity`
6. 复用 `Rss.getArticlesAwait()` 进行单源搜索
7. 复用 `ReadRss.readRss()` 进入文章详情
8. 复用 `SearchKeyword` 表（新增 `type` 字段区分书源/订阅源搜索历史）
9. 支持搜索范围筛选（按订阅源分组/类型，参考 `SearchScope`）
10. 支持搜索进度反馈（已搜索 X/Y 个源）、停止/恢复搜索

### Out of Scope（不在本次实现）

1. 不修改 `RssSource` 数据模型（不新增字段）
2. 不修改 `RssArticle` 数据模型（不持久化搜索结果到 `rssArticles` 表）
3. 不修改单个订阅源内部搜索功能（`RssSortActivity` 菜单 `R.id.menu_search` 保持不变）
4. 不修改订阅源管理页（`RssSourceActivity`）的搜索框（保留按名称过滤）
5. 不修改书源搜索功能（`SearchActivity`）
6. 不实现文章相似度去重（仅用 `title + pubDate` 简单去重）
7. 不实现搜索结果分页加载（每个源仅取第 1 页结果聚合）
8. 不实现全文搜索（依赖订阅源自身的 searchUrl 规则）

## Approach (方案)

### Selected Approach（选定方案：新建 RssSearchActivity + 内存包装类）

**核心架构**：完全模仿书源搜索架构（`SearchActivity` + `SearchViewModel` + `SearchModel`），平移到订阅源场景。

**核心组件**：

1. **RssSearchActivity**（新增）：模仿 `SearchActivity` ([app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt))
   - 顶部 `SearchView` 输入关键词
   - `RecyclerView` 展示搜索结果
   - `FloatingActionButton` 控制开始/停止
   - 历史关键词布局（`FlexboxLayoutManager`）
   - 进度条 `RefreshProgressBar`

2. **RssSearchViewModel**（新增）：模仿 `SearchViewModel`
   - 持有 `RssSearchModel` 实例
   - `searchRssLiveData: ConflateLiveData<List<SearchRssArticle>>` 存储搜索结果
   - `isSearchLiveData`、`searchFinishLiveData`、`upAdapterLiveData` 三种 LiveData
   - `search(key)` 触发搜索、`stop()` 停止、`pause()/resume()` 暂停/恢复

3. **RssSearchModel**（新增）：模仿 `SearchModel` ([app/src/main/java/io/legado/app/model/webBook/SearchModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt))
   - `Executors.newFixedThreadPool(min(threadCount, MAX_THREAD)).asCoroutineDispatcher()` 创建固定线程池
   - `flow{}.mapParallelSafe(threadCount){}.onEach{}.onCompletion{}.catch{}.collect()` 流式处理
   - `withTimeout(30000L)` 30秒超时
   - 调用 `Rss.getArticlesAwait(sortName="搜索", sortUrl=rssSource.searchUrl, rssSource, page=1, key=searchKey)` 搜索每个订阅源
   - `mergeItems()` 按 `title + pubDate` 去重合并，`addOrigin(origin, article)` 添加来源

4. **SearchRssArticle**（新增内存包装类，不持久化）：
   - 包含 `RssArticle` 基础字段（title/link/image/description/pubDate/type）
   - `origins: LinkedHashSet<String>` 存储多源 sourceUrl（参考 `SearchBook.origins`）
   - `originArticles: HashMap<String, RssArticle>` 存储每个源对应的 `RssArticle` 实例（用于换源时取用）
   - `addOrigin(origin: String, article: RssArticle)` 添加来源
   - 不存储到 Room

5. **RssSearchAdapter**（新增）：模仿 `SearchAdapter`
   - 使用现有 `item_rss_article.xml` 布局
   - 显示标题、图片、描述、发布日期
   - `BadgeView` 显示源数量（参考 `bvOriginCount.setBadgeCount`）
   - 点击 item → 调用 `ReadRss.readRss()` 跳转详情

6. **ChangeRssArticleSourceDialog**（新增）：模仿 `ChangeBookSourceDialog`
   - 当文章 `origins.size > 1` 时，详情页菜单显示"换源"按钮
   - 弹出对话框列出所有来源（订阅源名称）
   - 选择新源后，从 `originArticles` 取出对应的 `RssArticle`，重新调用 `ReadRss.readRss()`

7. **入口改造（职责分离）**：
   - **`RssFragment`（首屏，[app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L199-L213](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L199-L213)）**：
     - `onQueryTextChange`：保留按名称过滤订阅源列表（实时过滤行为不变，辅助快速定位）
     - `onQueryTextSubmit`：从 `return false` 改为 `RssSearchActivity.start(context, query)` 跳转跨源搜索页
     - `queryHint`：从 `R.string.rss` 改为 `R.string.search_rss_key`（新增字符串"搜索订阅源内容"）
   - **`RssSourceActivity`（设置页，[app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt#L418-L435](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt#L418-L435)）**：
     - **不修改**，保持原"按订阅源相关信息搜索订阅源"功能不变

**理由**：
- 完整复用书源搜索的成熟并发调度机制（线程池、超时、暂停/恢复、进度反馈）
- 不污染数据库（搜索结果仅在内存中）
- 架构与书源搜索对齐，便于后续维护与功能扩展
- 入口改造采用"职责分离"：首屏承载跨源搜索入口（保留过滤辅助功能），设置页保持原功能不变
- 搜索结果展示融合 `item_rss_article.xml`（标题/日期/图片）和 `item_search.xml`（BadgeView 源数量）设计，完整呈现图片/名称/时间/描述/源数量字段

### Alternatives Considered（备选方案对比）

| 方案 | 描述 | 优点 | 否决理由 |
|------|------|------|---------|
| **A（推荐）** | 新建 `RssSearchActivity` + 内存包装类 `SearchRssArticle` | 架构清晰、复用书源搜索成熟机制、不污染数据库 | 新增类较多（约 5 个新文件） |
| B | 复用 `RssArticle` 持久化搜索结果到 `rssArticles` 表 | 复用现有 `RssArticlesAdapter` | 搜索结果与正常文章混在数据库，去重困难，污染订阅源文章列表 |
| C | 改造 `RssSortActivity` 支持多源搜索 | 复用现有文章列表页 | `RssSortActivity` 设计为单源展示，改造涉及大量分支逻辑，复杂度高 |
| D | 不新建 Activity，直接在 `RssFragment` 中切换视图模式（订阅源列表 ↔ 搜索结果） | 单页面切换 | `RssFragment` 职责变得不清晰（既是订阅源列表又是搜索页），UI 状态管理复杂 |
| E | 不新建 `SearchRssArticle`，直接用 `List<RssArticle>` + `Map<String, List<RssArticle>>` 多源映射 | 减少新增类 | Adapter 数据结构复杂，UI 展示需手写多源聚合逻辑，缺乏类型安全 |
| F | 复用 `RssSourceActivity` 顶部搜索框作为入口（而非 `RssFragment`） | 改动 `RssSourceActivity` 即可 | `RssSourceActivity` 是订阅源管理页，不是订阅源栏目；用户入口路径不对 |

### Drawbacks（选定方案的已知缺点）

1. **新增类较多**：约 5 个新文件（Activity/ViewModel/Model/Adapter/Entity）+ 1 个换源 Dialog
   - **接受理由**：架构清晰度 > 文件数量；后续维护成本更低
   - **缓解**：完全参考书源搜索的代码结构，复制粘贴 + 适配，开发工作量可控

2. **搜索结果不持久化**：退出 `RssSearchActivity` 后搜索结果丢失
   - **接受理由**：搜索结果本质是临时查询结果，不需要持久化；用户可重新搜索
   - **缓解**：搜索关键词持久化到 `SearchKeyword` 表，便于快速重新搜索

3. **去重策略简单**：仅按 `title + pubDate` 去重，可能误判（同标题不同内容）或漏判（同内容不同标题）
   - **接受理由**：参考书源的 `name + author` 策略，简单可用
   - **缓解**：保留 `origins` 列表，用户可通过"换源"查看不同源的版本

4. **每个源仅取第 1 页结果**：不支持搜索结果分页加载
   - **接受理由**：跨源搜索的分页加载复杂度极高（需要协调多个源的下一页 URL），且多数场景下第 1 页结果足够
   - **缓解**：后续可参考 `SearchModel.searchPage` 设计扩展

5. **入口双语义（首屏）**：`RssFragment` 搜索框 `onQueryTextChange` 按名称过滤、`onQueryTextSubmit` 跳转跨源搜索
   - **接受理由**：兼顾两种需求，用户既能快速过滤订阅源列表，又能跨源搜索内容；过滤是实时小操作，搜索是主动大动作，行为本身有差异
   - **缓解**：`queryHint` 提示"搜索订阅源内容"，引导用户使用提交行为；`RssSourceActivity` 设置页保留原按名过滤功能，用户需要纯过滤时可进入设置页

### Prior Art（参考工作）

- **书源搜索架构**：[SearchActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt) + [SearchViewModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchViewModel.kt) + [SearchModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt)
- **书源换源对话框**：[ChangeBookSourceDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/changesource/ChangeBookSourceDialog.kt)
- **订阅源单源搜索**：[RssSortActivity.kt#L280-L307](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt#L280-L307)（菜单 `R.id.menu_search`）
- **订阅源文章获取**：[Rss.getArticlesAwait()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt#L40)
- **文章详情阅读**：[ReadRss.readRss()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt#L52)

## Requirements (需求)

### 功能需求

#### FR-01: 跨源并发搜索
- **FR-01.1**：用户在 `RssSearchActivity` 输入关键词并提交后，系统并发调用所有"已启用且 `searchUrl` 非空"的订阅源进行搜索
- **FR-01.2**：并发数受 `AppConfig.threadCount` 控制（与书源搜索一致）
- **FR-01.3**：单个订阅源搜索超时 30 秒，超时后该源返回空结果，不影响其他源
- **FR-01.4**：搜索过程中通过 `RefreshProgressBar`（顶部进度条）显示搜索进行中状态，与 `SearchActivity` 一致（**不显示 X/Y 文本进度**，因为 `SearchModel.CallBack` 接口无进度回调，避免引入新接口）
- **FR-01.5**：用户可通过 `FloatingActionButton` 停止/恢复搜索

#### FR-02: 结果聚合去重
- **FR-02.1**：多源返回的文章按 `title + pubDate` 聚合去重
- **FR-02.2**：聚合后的 `SearchRssArticle` 包含 `origins: LinkedHashSet<String>` 字段记录所有来源的 `sourceUrl`
- **FR-02.3**：聚合后的 `SearchRssArticle` 包含 `originArticles: HashMap<String, RssArticle>` 字段记录每个源对应的 `RssArticle` 实例
- **FR-02.4**：结果排序：标题完全匹配 > 标题包含 > 其他（参考 `SearchModel.mergeItems`）

#### FR-03: 结果展示（参考单个订阅源文章列表 + 书源搜索 BadgeView）

- **FR-03.1**：搜索结果以列表形式展示，每个 item 显示字段：
  - **图片**（`ivCover`）：左上方 80dp×80dp 圆角图片，无图时显示默认占位图
  - **标题**（`tvTitle`）：图片右侧第 1 行，16sp 加粗，最多 2 行，超出省略
  - **描述**（`tvDescription`）：图片右侧第 2 行，12sp，最多 2 行，超出省略（参考 `RssArticle.description`）
  - **发布日期**（`tvPubDate`）：图片右侧第 3 行，12sp 斜体，单行（参考 `RssArticle.pubDate`）
  - **来源数量**（`bvOriginCount`）：右上角 `BadgeView`，显示 `origins.size`（≥2 时才显示，=1 时不显示）
- **FR-03.2**：item 布局新建 `item_rss_search.xml`，融合 `item_rss_article.xml`（标题/日期/图片风格）和 `item_search.xml`（BadgeView 来源数量）的设计
- **FR-03.3**：item 点击后调用 `ReadRss.readRss()` 跳转详情页（必须使用**新增的 Activity 重载方法** `readRss(activity: AppCompatActivity, rssArticle, ...)`，因为现有 `readRss(fragment: Fragment, ...)` 要求 Fragment 类型，RssSearchActivity 是 AppCompatActivity 不兼容）
- **FR-03.4**：默认使用 `origins.first()` 对应的 `RssArticle` 进入详情
- **FR-03.5**：已读/未读状态通过标题颜色区分（已读=灰色 `tv_text_summary`，未读=正常色 `primaryText`），参考 `RssArticlesAdapter.convert`
  - **已读状态查询逻辑**：搜索结果来自 `Rss.getArticlesAwait()` 网络返回，`RssArticle.read` 字段默认 `false`。在 `RssSearchModel.mergeItems` 完成后或 `RssSearchAdapter.convert` 中，根据 `article.link` 批量查询 `rssArticles` 表（按 `origin+link` 匹配）判断已读状态，避免全部显示为未读色
- **FR-03.6**：图片加载失败时隐藏 ImageView，仅显示文本（参考 `RssArticlesAdapter` 的 `onLoadFailed` 处理）
- **FR-03.7**：图片加载时必须传递 `origins.first()` 作为 `OkHttpModelLoader.sourceOriginOption`（参考 [RssArticlesAdapter.kt#L65-L67](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssArticlesAdapter.kt#L65-L67)），确保需要 cookie 的订阅源图片可正常加载

#### FR-03-EX: 重复内容判重与展现策略

- **FR-03-EX.1（判重 key）**：使用 `title + pubDate` 作为去重 key（参考书源 `name + author` 策略）
  - 同标题同发布日期 → 视为同一篇文章，聚合到同一个 `SearchRssArticle`
  - 同标题不同发布日期 → 视为不同文章，分别展示
  - 不同标题同发布日期 → 视为不同文章，分别展示
- **FR-03-EX.2（判重时机）**：在 `RssSearchModel.mergeItems()` 中进行去重，每收到一个源的搜索结果就合并一次
- **FR-03-EX.3（聚合数据结构）**：
  - `origins: LinkedHashSet<String>`：记录所有来源的 `sourceUrl`（保持插入顺序）
  - `originArticles: HashMap<String, RssArticle>`：每个 `sourceUrl` 对应的 `RssArticle` 实例
  - `addOrigin(origin, article)`：添加新源时，若 origin 已存在则覆盖（保留最新文章实例）
- **FR-03-EX.4（展现方式）**：
  - 单源结果（`origins.size == 1`）：正常展示，不显示 BadgeView
  - 多源结果（`origins.size >= 2`）：右上角 BadgeView 显示源数量，点击进入详情后可通过"换源"菜单切换不同源查看
- **FR-03-EX.5（默认展示字段）**：多源聚合时，标题/描述/图片/发布日期取第一个源的 `RssArticle` 字段（`origins.first()` 对应的文章）
- **FR-03-EX.6（排序策略）**：搜索结果排序参考书源 `SearchModel.mergeItems`：
  1. 标题完全匹配搜索关键词（`title == searchKey`）→ 按源数量降序
  2. 标题包含搜索关键词（`title.contains(searchKey)`）→ 按源数量降序
  3. 其他（源返回但标题不含关键词，常见于全文搜索）→ 按源数量降序
  4. 三组之间按上述顺序排列

#### FR-04: 多源切换换源
- **FR-04.1**：当 `SearchRssArticle.origins.size > 1` 时，详情页菜单显示"换源"按钮（需修改 `res/menu/rss_read.xml` 和 `res/menu/video_play.xml` 新增 `menu_change_source` 菜单项）
- **FR-04.2**：点击"换源"按钮弹出 `ChangeRssArticleSourceDialog`，列出所有来源（订阅源名称）
- **FR-04.3**：选择新源后，从 `originArticles` 取出对应的 `RssArticle`，重新调用 `ReadRss.readRss()` 进入详情
- **FR-04.4**：换源时保留当前阅读位置（若类型一致）
- **FR-04.5**：**视频文章换源限制** — 视频文章（`type == 2`）换源时 `rssArticles` 传 `null`，不支持上下滑动切换文章（因 `VideoPlay.rssArticles: List<RssArticle>?` 与搜索结果 `List<SearchRssArticle>` 结构不兼容，与 AD-07 "每个源仅取第 1 页结果" 简化原则一致）
- **FR-04.6**：**网页文章上下滑动限制** — 从搜索结果进入详情页（网页文章 `type == 0` 或视频文章 `type == 2`）均**不支持上下滑动切换文章**（因 `ReadRss.readRss` 重载方法在搜索场景传 `rssArticles = null`），与从单个订阅源文章列表进入详情页（支持上下滑动）行为不同，需在 UI 上无明显差异提示
- **FR-04.7**：**换源后当前源感知** — 换源成功后通过 `toastOnUi("已切换到：${sourceName}")` 提示用户当前源名称，避免用户多次换源后迷失

#### FR-05: 搜索历史
- **FR-05.1**：搜索关键词保存到 `SearchKeyword` 表（新增 `type` 字段区分书源/订阅源，0=书源，1=订阅源）
- **FR-05.2**：搜索界面展示历史关键词列表（`FlexboxLayoutManager`）
- **FR-05.3**：支持点击历史关键词快速搜索
- **FR-05.4**：支持删除单条历史、清空全部历史
- **FR-05.5**：**必须修改现有 `SearchViewModel.kt`** 的 `saveSearchKey/clearHistory/deleteHistory` 方法显式传 `type=0`（书源），避免新增 type 字段后书源搜索历史与订阅源搜索历史混在一起
- **FR-05.6**：`SearchKeywordDao` 新增按 `type` 查询/删除方法：`flowByTime(type)`、`flowSearch(type, key)`、`deleteAll(type)`、`delete(searchKeyword, type)`
- **FR-05.7**：RssSearchViewModel 中显式传 `type=1`（订阅源），与书源搜索历史隔离

#### FR-06: 搜索范围筛选

> **可行性已验证**：`RssSource` 有 `sourceGroup` 字段（[RssSource.kt#L23-L24](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt#L23-L24)），且有 `hasGroup(group)` 方法（[RssSource.kt#L220](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt#L220)）；`rssSourceDao.flowEnabledGroups()` 方法已存在（[RssSourceDao.kt#L198-L199](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt#L198-L199)），可直接复用获取订阅源分组列表。订阅源栏目首屏 `RssFragment` 已支持分组展示（[RssFragment.kt#L76-L95](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L76-L95)，`sourceGroupStyle`/`sourceGroupMode` 控制）。

- **FR-06.1**：支持"全部订阅源"搜索（默认）
- **FR-06.2**：支持按订阅源分组筛选搜索范围（多选，参考 `SearchActivity` 的 `onMenuOpened` 动态菜单机制 [SearchActivity.kt#L118-L156](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L118-L156)）
  - 已选分组显示在 `menu_group_1`（带勾选标记）
  - 可选分组显示在 `menu_group_2`（单选触发添加到已选）
  - "全部源"选项（`menu_1`）：清空已选分组
  - 分组数据来源：`appDb.rssSourceDao.flowEnabledGroups()`（已存在）
- **FR-06.3**：**不实现**按订阅源类型筛选（`type` 字段 0=网页/1=图片/2=视频）— 简化实现，与 AD-07 一致；用户可通过分组间接管理
- **FR-06.4**：搜索范围选择参考 `SearchActivity` 的动态菜单机制（不新建 `RssSearchScopeDialog`，直接在 `onMenuOpened` 中生成）
- **FR-06.5**：搜索范围状态管理参考 `SearchScope`（[SearchScope.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchScope.kt)），但新建 `RssSearchScope` 类（不复用 `SearchScope`，因后者有 `getBookSourceParts()` 书源特有方法）
- **FR-06.6**：搜索范围持久化到 `AppConfig`（参考 `SearchScope.save()` 的 `AppConfig.searchScope`/`AppConfig.searchGroup`，新增 `AppConfig.rssSearchScope`/`AppConfig.rssSearchGroup`）

#### FR-07: 入口改造（职责分离模式：首屏跨源搜索 + 设置页按名过滤）

> **设计原则**：订阅源栏目有两个搜索入口，本次改造明确两个入口的职责分离：
> - **`RssFragment`（订阅源栏目首屏）**：改造为"跨源内容搜索入口"，用户输入关键词后跳转 `RssSearchActivity` 进行跨源搜索
> - **`RssSourceActivity`（订阅源栏目设置页）**：保持原"按订阅源相关信息搜索订阅源"功能不变，不修改

- **FR-07.1（RssFragment 首屏搜索框 - 改造）**：
  - `onQueryTextSubmit(query)`：从 `return false` 改为跳转 `RssSearchActivity.start(requireContext(), query)`，跳转后清空搜索框并失焦
  - `onQueryTextChange(newText)`：**保留**按名称过滤订阅源列表的行为（实时过滤，辅助用户快速定位订阅源）
  - `queryHint`：从 `R.string.rss` 改为 `R.string.search_rss_key`（新增字符串"搜索订阅源内容"），引导用户使用提交行为
  - `isSubmitButtonEnabled = true`：保持不变，确保用户能看到搜索按钮

- **FR-07.2（RssSourceActivity 设置页搜索框 - 不修改）**：
  - 保持原 `onQueryTextChange` 调用 `upSourceFlow(newText)` 按名称过滤订阅源的行为不变
  - 保持原 `queryHint = R.string.search_rss_source`（"搜索订阅源"）不变
  - **本规范明确禁止修改 `RssSourceActivity.kt` 的 `initSearchView()` 方法**（参见 [RssSourceActivity.kt#L418-L435](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt#L418-L435)）

- **FR-07.3（双语义保留理由）**：
  - `onQueryTextChange` 保留按名称过滤：用户在首屏仍可快速定位订阅源（如输入"科"实时过滤出含"科"的订阅源），不影响新功能
  - `onQueryTextSubmit` 跳转跨源搜索：用户主动点击搜索按钮，意图是跨源搜索内容，跳转新页面承载完整搜索体验
  - 两种行为不冲突：过滤是实时小操作（输入即过滤），搜索是主动大动作（点击提交），用户行为本身有差异

#### FR-08: RssSearchActivity 交互细节（参考 SearchActivity 产品功能）

> **设计依据**：深度分析 [SearchActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt) 的产品交互细节，明确 RssSearchActivity 的差异化实现。

- **FR-08.1（布局差异 - 删除书架搜索区域）**：
  - `activity_rss_search.xml` **删除** `tv_book_show` 和 `rv_bookshelf_search`（书架已有书籍搜索，订阅源无此概念）
  - **保留** `tv_history` + `tv_clear_history` + `rv_history_key`（搜索历史关键词列表）
  - **保留** `ll_input_help` 容器（搜索框获得焦点时显示，搜索框失焦且有搜索结果时隐藏）
  - **保留** `RefreshProgressBar`（顶部进度条）
  - **保留** `FloatingActionButton`（`fb_start_stop`，右下角停止/继续按钮）
  - 参考布局差异：[activity_book_search.xml#L52-L64](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/activity_book_search.xml#L52-L64)（删除 `tv_book_show` + `rv_bookshelf_search`）

- **FR-08.2（onQueryTextChange 行为）**：
  - 与 `SearchActivity` 一致（[SearchActivity.kt#L203-L208](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L203-L208)）
  - 调用 `viewModel.stop()` 停止当前搜索
  - `binding.fbStartStop.invisible()` 隐藏 FAB
  - 调用 `upHistory(newText.trim())` 更新历史关键词列表（按 `type=1` 查询 `SearchKeyword` 表）
  - **空关键词校验**：`onQueryTextSubmit` 时若 `key.trim().isEmpty()` 则拒绝搜索（不跳转、不查询、不保存历史）

- **FR-08.3（搜索历史点击行为 - 简化）**：
  - **与 `SearchActivity` 差异**：`SearchActivity.searchHistory(key)` 检查书架是否有同名书（[SearchActivity.kt#L490-L506](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L490-L506)），有则只填入不提交
  - **RssSearchActivity 简化**：订阅源搜索无"书架"概念，直接 `searchView.setQuery(key, true)` 提交搜索
  - 长按历史关键词弹出删除菜单（参考 `HistoryKeyAdapter`）

- **FR-08.4（FloatingActionButton 状态 - 简化）**：
  - **搜索中**：`fbStartStop.setImageResource(R.drawable.ic_stop_black_24dp)` + `visible()`（与 `SearchActivity` 一致，[SearchActivity.kt#L414-L419](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L414-L419)）
  - **搜索完成后**：`fbStartStop.invisible()`（**与 `SearchActivity` 差异**：`SearchActivity` 在 `hasMore=true` 时显示播放图标，订阅源搜索不支持分页加载 AD-07，`hasMore` 始终 false，所以总是隐藏）
  - **点击 FAB**：搜索中点击 → 停止搜索；搜索完成后不显示 FAB，无需处理点击

- **FR-08.5（搜索结果为空的处理）**：
  - **与 `SearchActivity` 差异**：`SearchActivity` 弹出对话框提示"是否切换到全部分组？"（[SearchActivity.kt#L438-L459](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L438-L459)）
  - **RssSearchActivity 简化**：
    - 如果搜索范围是"全部"且结果为空 → 仅在列表区域显示"无搜索结果"提示（`DynamicFrameLayout` 的空状态），不弹对话框
    - 如果搜索范围是某分组且结果为空 → 弹出对话框提示"${displayScope}分组搜索结果为空，是否切换到全部分组？"
    - **不保留"精度搜索"提示**（订阅源无 kind 字段，不实现精度搜索）

- **FR-08.6（菜单结构 - 简化）**：
  - **保留**：`menu_search_scope`（搜索范围）、`menu_source_manage`（订阅源管理，跳转 `RssSourceActivity`）、`menu_log`（日志）
  - **不保留**：`menu_precision_search`（精度搜索，订阅源无 kind 字段）
  - **动态菜单**：`menu_group_1`（已选分组，带勾选）、`menu_group_2`（可选分组）、`menu_1`（全部源）
  - 菜单资源文件：新增 `res/menu/rss_search.xml`

- **FR-08.7（finish 特殊处理）**：
  - 与 `SearchActivity` 一致（[SearchActivity.kt#L534-L540](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L534-L540)）
  - 第一次按返回键：如果 `searchView.hasFocus()`，则 `searchView.clearFocus()` 并 return（不 finish）
  - 第二次按返回键：调用 `super.finish()` 真正退出 Activity

- **FR-08.8（滚动加载更多 - 不实现）**：
  - **与 `SearchActivity` 差异**：`SearchActivity` 支持滚动到底部加载下一页（[SearchActivity.kt#L249-L270](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L249-L270) + [SearchActivity.kt#L344-L357](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L344-L357)）
  - **RssSearchActivity 不实现**：与 AD-07 一致，每个源仅取第 1 页结果聚合
  - **不注册** `RecyclerView.OnScrollListener` 的 `scrollToBottom` 逻辑

- **FR-08.9（搜索框焦点变化监听）**：
  - 与 `SearchActivity` 一致（[SearchActivity.kt#L210-L217](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L210-L217)）
  - `searchView.setOnQueryTextFocusChangeListener`：搜索框获得焦点时显示 `ll_input_help`，失焦且有搜索结果时隐藏

### 非功能需求

#### NFR-01: 性能
- **单源搜索响应时间**：单个订阅源搜索 ≤ 30 秒（超时后该源返回空结果）
- **总耗时**：取决于源数量与 `threadCount`（默认 16），典型场景（≤20 源）≤ 35 秒；源数量 > `threadCount` 时总耗时 = `ceil(源数/threadCount) × 30s`（如 100 源最坏情况 ≈ 187.5 秒）
- 内存占用：搜索结果列表 ≤ 500 条时，内存占用增量 ≤ 50MB
- 并发安全：使用 `ConflateLiveData` 防抖，避免 UI 卡顿

#### NFR-02: 兼容性
- 不破坏现有订阅源栏目功能（按名称过滤、订阅源管理、订阅源阅读）
- 不破坏现有书源搜索功能
- 不修改数据库 schema（`rssSources`、`rssArticles` 表结构不变）
- 仅新增 `SearchKeyword.type` 字段（数据库 migration 必填默认值 0 表示书源）
- **数据库版本从 98 → 99**（当前 [AppDatabase.kt#L77](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt#L77) `version = 98`，不是 84；Migration 命名为 `MIGRATION_98_99`，表名为 `search_keywords` 带下划线）
- **必须修改现有 `SearchViewModel.kt`**：新增 type 字段后，现有书源搜索的 `saveSearchKey/clearHistory/deleteHistory` 必须显式传 `type=0`，否则书源搜索历史会与订阅源搜索历史混在一起（参见 FR-05.5）

#### NFR-03: 可维护性
- 代码结构与书源搜索保持一致，便于后续维护
- 关键决策记录在 ADR 中
- 关键方法添加注释说明设计意图

#### NFR-04: 错误处理
- 单个订阅源搜索失败不影响其他源（异常捕获 + 日志记录）
- 搜索结果为空时显示友好提示
- 网络异常时显示错误信息

## Scenarios (场景)

### Scenario 1: 基础搜索流程

**前置条件**：用户已启用 5 个订阅源，其中 3 个配置了 `searchUrl`

**步骤**：
1. 用户在订阅源栏目（`RssFragment`）顶部搜索框输入"AI"
2. 用户点击搜索按钮（或回车）
3. 系统跳转到 `RssSearchActivity`，自动发起搜索
4. 系统并发调用 3 个支持搜索的订阅源
5. 搜索结果实时填充到列表
6. 搜索完成后，进度条消失，`FloatingActionButton` 变为播放图标（可继续搜索下一页）
7. 用户点击列表中某篇文章
8. 系统跳转到详情页（`ReadRssActivity` 或 `VideoPlayerActivity`）

**后置条件**：搜索关键词保存到 `SearchKeyword` 表

### Scenario 2: 多源换源流程

**前置条件**：用户搜索"AI"，3 个订阅源都返回了标题为"AI 最新进展"的文章

**步骤**：
1. 搜索结果列表中显示该文章，BadgeView 显示源数量 "3"
2. 用户点击该文章
3. 系统使用 `origins.first()` 对应的 `RssArticle` 跳转详情页
4. 用户在详情页点击菜单"换源"
5. 系统弹出 `ChangeRssArticleSourceDialog`，列出 3 个订阅源名称
6. 用户选择第 2 个订阅源
7. 系统从 `originArticles` 取出对应的 `RssArticle`，重新调用 `ReadRss.readRss()` 进入详情

**后置条件**：详情页显示新源的文章内容

### Scenario 3: 搜索范围筛选

**前置条件**：用户订阅源栏目有"科技"和"娱乐"两个分组

**步骤**：
1. 用户进入 `RssSearchActivity`
2. 用户点击菜单"搜索范围"
3. 系统弹出 `SearchScopeDialog`，显示"全部"、"科技"、"娱乐"等选项
4. 用户选择"科技"分组
5. 用户输入"AI"并搜索
6. 系统仅搜索"科技"分组下配置了 `searchUrl` 的订阅源

**后置条件**：搜索结果仅包含"科技"分组订阅源的文章

### Scenario 4: 搜索失败容错

**前置条件**：3 个订阅源中 1 个网络不通

**步骤**：
1. 用户输入"AI"并搜索
2. 系统并发调用 3 个订阅源
3. 1 个订阅源 30 秒超时
4. 其他 2 个订阅源正常返回结果
5. 系统聚合 2 个正常源的结果展示
6. 日志记录超时源的异常信息

**后置条件**：用户看到部分搜索结果，无崩溃

### Scenario 5: 搜索历史复用

**前置条件**：用户之前搜索过"AI"、"机器学习"

**步骤**：
1. 用户进入 `RssSearchActivity`，未输入关键词
2. 系统显示历史关键词列表（"AI"、"机器学习"）
3. 用户点击"AI"
4. 系统自动填入搜索框并触发搜索

**后置条件**：搜索结果展示

### Scenario 6: 不支持搜索的订阅源被排除

**前置条件**：用户有 5 个订阅源，其中 2 个未配置 `searchUrl`

**步骤**：
1. 用户输入关键词搜索
2. 系统仅调用 3 个配置了 `searchUrl` 的订阅源
3. 2 个未配置 `searchUrl` 的订阅源被排除

**后置条件**：搜索过程不报错

### Scenario 7: 入口职责分离（首屏跨源搜索 + 设置页按名过滤）

**前置条件**：用户在订阅源栏目

**步骤**：
1. 用户在订阅源栏目首屏（`RssFragment`）搜索框输入"科"（未点击搜索按钮）
2. 系统实时过滤订阅源列表，显示名称含"科"的订阅源（onQueryTextChange 行为保留）
3. 用户点击搜索按钮（onQueryTextSubmit）
4. 系统跳转 `RssSearchActivity` 发起跨源搜索
5. 搜索完成后，用户返回 `RssFragment`，订阅源列表仍保持过滤状态（如有）
6. 用户点击菜单"订阅源管理"进入 `RssSourceActivity`
7. 用户在 `RssSourceActivity` 顶部搜索框输入"科"
8. 系统按名称过滤订阅源列表（保持原功能不变）

**后置条件**：
- 首屏搜索框支持两种行为：实时按名称过滤 + 提交跳转跨源搜索
- 设置页搜索框保持原按名称过滤功能不变
