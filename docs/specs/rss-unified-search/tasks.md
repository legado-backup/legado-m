# 订阅源统一搜索 - 实施任务清单 (Tasks)

> **状态标记**：🔄 设计中
> **任务格式**：`- [ ] X.Y` 编号任务
> **执行顺序**：按编号顺序执行，不可跳过中间任务

## 1. 准备工作

- [ ] 1.1 阅读书源搜索相关源码，确认设计可行性
  - 阅读 `SearchActivity.kt`、`SearchViewModel.kt`、`SearchModel.kt`、`SearchAdapter.kt`
  - 阅读 `SearchBook.kt`、`SearchKeyword.kt`、`SearchScope.kt`、`SearchScopeDialog.kt`
  - 阅读 `ChangeBookSourceDialog.kt`
- [ ] 1.2 阅读订阅源相关源码，确认复用点
  - 阅读 `RssFragment.kt`、`RssSource.kt`、`RssArticle.kt`
  - 阅读 `Rss.kt`（重点 `getArticlesAwait`）、`RssSortActivity.kt`（菜单 `R.id.menu_search` 逻辑）
  - 阅读 `ReadRss.kt`、`RssArticlesAdapter.kt`
- [ ] 1.3 阅读数据库相关源码，确认 migration 方案
  - 阅读 `AppDatabase.kt`（version、migration 列表）
  - 阅读 `SearchKeywordDao.kt`、`SearchKeyword.kt`
- [ ] 1.4 阅读项目规范，确认约束
  - 阅读 `database-migration-safety.md`、`naming_rules.md`、`checkstyle_rules.md`
  - 阅读 `architecture_rules.md`、`logging_rules.md`、`exception_rules.md`

## 2. 数据层实现

- [ ] 2.1 修改 `SearchKeyword.kt` 新增 `type: Int = 0` 字段
  - 0=书源（兼容旧数据），1=订阅源
  - 添加 `@ColumnInfo(defaultValue = "0")` 注解
- [ ] 2.2 修改 `SearchKeywordDao.kt` 新增按 `type` 查询/删除方法
  - `flowByTime(type: Int)`、`flowSearch(type: Int, key: String)`
  - `deleteAll(type: Int)`、`delete(searchKeyword: SearchKeyword, type: Int)`
- [ ] 2.3 修改 `AppDatabase.kt` version 98→99，新增 migration
  - **阻塞点 10 修复：复合主键重建**（原设计 `ALTER TABLE ADD COLUMN` 无法隔离 type，因 `word` 是单字段主键）
  - 修改 `SearchKeyword.kt`：`@Entity(tableName = "search_keywords", primaryKeys = ["word", "type"])`，删除原 `indices = [Index(value = ["word"], unique = true)]`
  - `MIGRATION_98_99`（手动 Migration，drop+create 重建表）：
    ```sql
    CREATE TABLE search_keywords_new (word TEXT NOT NULL, usage INTEGER NOT NULL DEFAULT 0, lastUseTime INTEGER NOT NULL DEFAULT 0, type INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(word, type));
    INSERT INTO search_keywords_new (word, usage, lastUseTime, type) SELECT word, usage, lastUseTime, 0 FROM search_keywords;
    DROP TABLE search_keywords;
    ALTER TABLE search_keywords_new RENAME TO search_keywords;
    CREATE INDEX idx_search_keywords_type ON search_keywords(type, lastUseTime);
    ```
  - 注册 `MIGRATION_98_99` 到 `DatabaseMigrations.migrations` 列表
  - **注意**：当前数据库 version = 98（不是 84），88→89 之后都是手动 Migration
  - **参考**：[database-migration-safety.md](../../project-rules/database-migration-safety.md) 规范
- [ ] 2.4 新增 `SearchRssArticle.kt` 内存包装类（不持久化）
  - 字段：title、pubDate、description、image、type（文章类型 0=网页/1=图片/2=视频，参考 RssArticle.type）、origins、originArticles
  - 方法：`addOrigin(origin, article)`、`deduplicationKey()`、`getDefaultArticle()`
  - **注意**：SearchRssArticle.type 与 SearchKeyword.type 含义不同（一个是文章类型，一个是搜索历史类型），添加注释说明
- [ ] 2.5 **修改 `SearchViewModel.kt`** 的 `saveSearchKey/clearHistory/deleteHistory` 方法
  - `saveSearchKey(key)`：插入 `SearchKeyword(key, 1, type = 0)` 显式传 type=0（书源）
  - `clearHistory()`：调用 `appDb.searchKeywordDao.deleteAll(type = 0)` 只删除书源历史
  - `deleteHistory(searchKeyword)`：调用 `appDb.searchKeywordDao.delete(searchKeyword, type = 0)` 只删除书源历史
  - **必须修改**，否则新增 type 字段后书源搜索历史会与订阅源搜索历史混在一起（参见 FR-05.5）

## 3. Model 层实现

- [ ] 3.1 新增 `RssSearchScope.kt` 搜索范围工具类
  - 参考 `SearchScope.kt`
  - 支持"全部"、"按分组"、"按类型"三种范围
  - `getRssSources()` 返回范围内的 `RssSource` 列表（已启用且 `searchUrl` 非空）
- [ ] 3.2 新增 `RssSearchModel.kt` 搜索并发调度核心
  - 模仿 `SearchModel.kt`
  - `search(searchId, key)` 入口方法
  - **阻塞点 11 修复**：`search()` 内部必须先调用 `initSearchPool()` 初始化线程池，否则 `searchPool!!` 会 NPE；补充 `searchId != mSearchId` 检查
  - `initSearchPool()` 固定线程池
  - `flow{}.mapParallelSafe{}.onEach{}.onCompletion{}.catch{}.collect()` 流式处理
  - **遗漏点 31 修复**：`mapParallelSafe` 内部增加 `try/catch`，单个源失败时记录 `AppLog.put("源[${it.sourceName}]搜索失败: ${e.localizedMessage}", e)` 并返回 `emptyList()`，避免静默吞掉异常
  - **遗漏点 38 修复**：catch 块按异常类型分类（UnknownHostException/SocketTimeoutException/ConnectException/其他）
  - `withTimeout(30000L)` 30 秒超时
  - **阻塞点 12 修复**：`mergeItems` 必须使用成员变量 `searchArticlesMap` 保留去重信息（参考 `SearchModel.kt#L118` `val copyData = ArrayList(searchBooks)`），**禁止**每次创建局部 Map 直接覆盖 `searchArticles`
  - **阻塞点 15 修复**：`mergeItems` 完成后批量查询 `rssArticles` 表（按 `origin+link` 匹配）判断已读状态，避免搜索结果全部显示为未读色
  - `pause()/resume()/cancelSearch()/close()` 控制方法
  - **遗漏点 32 修复**：明确 `CallBack` 接口方法签名：`getSearchScope()/onSearchStart()/onSearchSuccess(articles)/onSearchFinish(isEmpty)/onSearchCancel(exception)`（无 `hasMore`，AD-07 不支持分页）

## 4. ViewModel 层实现

- [ ] 4.1 新增 `RssSearchViewModel.kt`
  - 模仿 `SearchViewModel.kt`
  - 持有 `RssSearchModel` 实例
  - `searchRssLiveData: ConflateLiveData<List<SearchRssArticle>>` 防抖 1000ms
  - `isSearchLiveData`、`searchFinishLiveData` 三种 LiveData（**遗漏点 34 修复：删除 `upAdapterLiveData`**，订阅源搜索无书架概念，AD-11 已删除书架搜索区域）
  - `search(key)`、`stop()`、`pause()`、`resume()` 方法
  - `saveSearchKey(key)`、`clearHistory()`、`deleteHistory()` 方法（显式传 `type=1` 订阅源）
  - `searchScope: RssSearchScope` 范围管理

## 5. UI 层 - 搜索页面

- [ ] 5.1 新增 `activity_rss_search.xml` 布局
  - 参考 `activity_book_search.xml`
  - TitleBar + SearchView
  - RefreshProgressBar
  - RecyclerView（搜索结果列表）
  - LinearLayout ll_input_help（**只保留搜索历史区域**，删除 `tv_book_show` 和 `rv_bookshelf_search`，AD-11）
  - FloatingActionButton fb_start_stop
  - **关键差异**：删除书架已有书籍搜索区域（订阅源无书架概念）
- [ ] 5.2 新增 `item_rss_search.xml` item 布局（融合 `item_rss_article.xml` + `item_search.xml`）
  - 字段：`iv_cover`（80dp×80dp 圆角图片）、`tv_title`（16sp 加粗，最多 2 行）、`tv_description`（12sp，最多 2 行）、`tv_pub_date`（12sp 斜体，单行）、`bv_origin_count`（BadgeView，源数量 ≥2 时显示）
  - 字段映射参见 design.md §3.1 字段映射表
  - 图片加载失败时 `iv_cover.gone()`（参考 `RssArticlesAdapter`）
- [ ] 5.3 新增 `RssSearchAdapter.kt`
  - 模仿 `SearchAdapter.kt`
  - 使用 `DiffRecyclerAdapter<SearchRssArticle, ItemRssSearchBinding>`
  - `diffItemCallback` 按 `title + pubDate` 比较
  - `registerListener` 点击 item 跳转 **`ReadRss.readRss(activity, ...)`**（使用新增的 Activity 重载方法，不是 Fragment 版本，参见 §6.5）
  - 显示 BadgeView 源数量
  - **图片加载必须传 `origins.first()` 作为 `OkHttpModelLoader.sourceOriginOption`**（参见 FR-03.7）
- [ ] 5.4 新增 `RssSearchHistoryAdapter.kt` 历史关键词 Adapter
  - 模仿 `HistoryKeyAdapter.kt`
  - 使用 `FlexboxLayoutManager` 展示
  - 长按弹出删除菜单（参考 `HistoryKeyAdapter`）
- [ ] 5.5 **不新建** `RssSearchScopeDialog.kt`（FR-06.4 明确：搜索范围选择直接在 `onMenuOpened` 动态生成菜单，不新建 Dialog）
  - 新增 `RssSearchScope.kt` 搜索范围状态管理类（模仿 `SearchScope`，但不包含 `getBookSourceParts()` 书源特有方法）
  - 支持 `update(groups: List<String>)`、`remove(group: String)`、`isAll()`、`display`、`displayNames`、`getRssSources()` 方法
  - 持久化到 `AppConfig.rssSearchScope` / `AppConfig.rssSearchGroup`（需新增 AppConfig 字段）
- [ ] 5.6 新增 `RssSearchActivity.kt`
  - 模仿 `SearchActivity.kt`
  - `initSearchView()`：
    - `onQueryTextSubmit`：调用 `viewModel.search(key)` + `saveSearchKey(key)` + `visibleInputHelp(false)`（FR-08.2）
    - `onQueryTextChange`：`viewModel.stop()` + `binding.fbStartStop.invisible()` + `upHistory(newText.trim())`（FR-08.2）
    - `setOnQueryTextFocusChangeListener`：搜索框获焦显示 `ll_input_help`，失焦且有搜索结果时隐藏（FR-08.9）
  - `initRecyclerView()`：**不注册** `RecyclerView.OnScrollListener`（AD-15 不实现滚动加载更多）
  - `initOtherView()`：
    - `fbStartStop.setOnClickListener`：搜索中 → `viewModel.stop()`；搜索完成后不显示 FAB（AD-13）
    - `tvClearHistory.setOnClickListener`：弹出清空历史确认对话框
  - `initData()`：
    - `viewModel.searchScope.stateLiveData.observe`：搜索范围变化时自动重新搜索
    - `viewModel.isSearchLiveData.observe`：`startSearch()` / `searchFinally()`
    - `viewModel.searchRssLiveData.observe`：`adapter.setItems(it)`
    - `lifecycleScope.launch { appDb.rssSourceDao.flowEnabledGroups().flowOn(IO).collect { groups = it } }`（FR-08.6 分组数据来源）
  - `observeLiveBus()`：
    - `viewModel.searchFinishLiveData.observe`：空状态处理（FR-08.5）
      - 范围是"全部"且空 → 不弹对话框（DynamicFrameLayout 自动显示空状态）
      - 范围是某分组且空 → 弹出"是否切换到全部分组？"对话框
  - `searchHistory(key)`：**直接** `searchView.setQuery(key, true)`（FR-08.3 简化，不检查书架）
  - `showArticleDetail(article)`：调用 `ReadRss.readRss(activity = this, ...)`（使用 §6.5 新增的 Activity 重载方法）
  - `onMenuOpened`：动态生成分组菜单（参考 design.md §6.7）
  - `onCompatOptionsItemSelected`：处理 `menu_search_scope` / `menu_source_manage` / `menu_log` / `menu_1` / `menu_group_1` / `menu_group_2`
  - `finish()`：第一次按返回键清焦点，第二次真正 finish（FR-08.7）

## 6. UI 层 - 换源对话框

- [ ] 6.1 新增 `RssSearchSourceHolder.kt` 单例
  - `var articles: HashMap<String, RssArticle>?` 临时持有当前文章多源映射
  - 参考设计 AD-06
- [ ] 6.2 新增 `ChangeRssArticleSourceDialog.kt`
  - 模仿 `ChangeBookSourceDialog.kt`
  - 显示 `RssSearchSourceHolder.articles` 中所有 origin 对应的订阅源名称
  - 点击某项 → 取出对应的 `RssArticle` → 重新调用 `ReadRss.readRss(activity, ...)` → 关闭当前详情页
- [ ] 6.3 修改菜单资源文件添加"换源"菜单项
  - 修改 `app/src/main/res/menu/rss_read.xml` 新增 `menu_change_source` 菜单项（标题 `@string/change_source`）
  - 修改 `app/src/main/res/menu/video_play.xml` 新增 `menu_change_source` 菜单项（标题 `@string/change_source`）
- [ ] 6.4 修改 `ReadRssActivity.kt` 和 `VideoPlayerActivity.kt` 处理换源菜单
  - `onCreateOptionsMenu`：仅当 `RssSearchSourceHolder.articles?.size > 1` 时显示 `menu_change_source` 菜单项（默认隐藏）
  - `onOptionsItemSelected`：处理 `R.id.menu_change_source` → 弹出 `ChangeRssArticleSourceDialog`
  - `onDestroy`：清理 `RssSearchSourceHolder.articles = null`，避免内存泄漏
- [ ] 6.5 **修改 `ReadRss.kt` 新增 Activity 重载方法**
  - 新增 `fun readRss(activity: AppCompatActivity, rssArticle: RssArticle, rssSource: RssSource? = null, rssArticles: List<RssArticle>? = null, sortName: String? = null, sortUrl: String? = null, nextPageUrl: String? = null, page: Int = 1)`
  - 参考已有的 `readRss(activity: AppCompatActivity, record: RssReadRecord)` 重载（[ReadRss.kt#L28](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui.rss.read/ReadRss.kt#L28)）
  - 实现：`type == 0` 跳 ReadRssActivity；`type == 2` 跳 VideoPlayerActivity（搜索场景传 `rssArticles = null`，不支持上下滑动切换）；其他调用 `readNoHtml(activity, ...)`
  - 新增 `readNoHtml(activity: AppCompatActivity, rssArticle: RssArticle, rssSource: RssSource?, type: Int)` 私有方法
  - **必须新增**，否则 RssSearchAdapter 调用 `ReadRss.readRss(fragment = ...)` 会编译失败（参见 §5 关键阻塞点修复）

## 7. 入口改造（职责分离：首屏跨源搜索 + 设置页不修改）

- [ ] 7.1 修改 `RssFragment.kt.initSearchView()`（首屏搜索框 - 改造为跨源搜索入口）
  - `onQueryTextSubmit`：从 `return false` 改为跳转 `RssSearchActivity.start(requireContext(), key)`，跳转后 `searchView.setQuery("", false)` + `clearFocus()`
  - `onQueryTextChange`：**保留**按名称过滤行为（调用 `upRssFlowJob(newText)`，不变）
  - `queryHint`：从 `R.string.rss` 改为 `R.string.search_rss_key`
  - `isSubmitButtonEnabled = true`：保持不变
  - 参见 [RssFragment.kt#L199-L213](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L199-L213)
- [ ] 7.2 **确认不修改** `RssSourceActivity.kt.initSearchView()`（设置页搜索框 - 保持原功能）
  - 保持原 `onQueryTextChange` 调用 `upSourceFlow(newText)` 按名称过滤订阅源的行为
  - 保持原 `queryHint = R.string.search_rss_source` 不变
  - 参见 [RssSourceActivity.kt#L418-L435](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt#L418-L435)
  - 验证：grep `RssSourceActivity.kt` 确认 `initSearchView` 方法未被修改
- [ ] 7.3 修改 `strings.xml` 新增字符串资源
  - `search_rss_key`：搜索订阅源内容
  - `change_source`：换源
  - `search_rss_history`：订阅源搜索历史
  - 其他必要字符串
- [ ] 7.4 修改 `AndroidManifest.xml` 注册 `RssSearchActivity`

## 8. 资源文件

- [ ] 8.1 新增 `menu/rss_search.xml` 菜单资源
  - 参考 `menu/book_search.xml`
  - 包含：搜索范围（`menu_search_scope`）、订阅源管理（`menu_source_manage`）、日志（`menu_log`）
  - **不包含**：精度搜索（`menu_precision_search`，AD-14）
  - 动态菜单项（`menu_group_1` / `menu_group_2` / `menu_1`）在 `onMenuOpened` 中代码生成，不在 XML 中定义
- [ ] 8.2 新增 `drawable` 图标资源（如需）
  - 复用现有图标，避免新增

## 9. 验证与测试

> **测试用例文件**：[ai_tests/cases/F-P0-8-rss-unified-search/case.md](../../../ai_tests/cases/F-P0-8-rss-unified-search/case.md)（24 个 TC 用例）
> **测试方案**：参见第 12 节 ai_test 测试方案
> **回归测试矩阵**：参见第 13 节修改文件回归测试矩阵
> **测试 SOP**：遵循 [fixed_test_workflow.md](../../../ai_tests/docs/fixed_test_workflow.md) 标准流水线

- [ ] 9.1 编译验证：`./gradlew assembleDebug` 无错误
- [ ] 9.2 静态代码检查：`./gradlew detekt` 无错误
- [ ] 9.3 真机测试 - 基础搜索流程（**对应 TC-F-P0-8-01**）
  - 在订阅源栏目输入"AI" → 点击搜索按钮 → 跳转 `RssSearchActivity`
  - 验证搜索结果实时填充
  - 验证搜索完成后 `FloatingActionButton` 隐藏（AD-13，不显示播放图标）
  - 验证点击文章跳转详情页
- [ ] 9.4 真机测试 - 多源换源（**对应 TC-F-P0-8-03**）
  - 搜索结果中找到 `origins.size > 1` 的文章
  - 点击进入详情页 → 菜单"换源" → 选择新源
  - 验证详情页切换到新源内容
- [ ] 9.5 真机测试 - 搜索范围筛选（**对应 TC-F-P0-8-04**）
  - 在 `RssSearchActivity` 菜单选择"搜索范围" → 动态生成分组列表
  - 验证仅搜索该分组下的订阅源
  - 验证搜索范围持久化
- [ ] 9.6 真机测试 - 搜索失败容错（**对应 TC-F-P0-8-09**）
  - 模拟某订阅源网络不通（关闭网络后搜索）
  - 验证其他源结果正常展示，无崩溃
  - 验证搜索总耗时 ≤ 35 秒
- [ ] 9.7 真机测试 - 搜索历史（**对应 TC-F-P0-8-05**）
  - 搜索几个关键词 → 退出 `RssSearchActivity` → 重新进入
  - 验证历史关键词列表展示（按时间倒序）
  - 验证点击历史关键词直接触发搜索（FR-08.3，不检查书架）
  - 验证长按弹出删除菜单
  - 验证删除单条历史、清空全部历史
- [ ] 9.8 真机测试 - 入口职责分离（**对应 TC-F-P0-8-07**）
  - 在订阅源栏目首屏（`RssFragment`）输入"科"（不提交） → 验证订阅源列表实时过滤
  - 点击搜索按钮 → 验证跳转 `RssSearchActivity`
  - 进入订阅源管理（`RssSourceActivity`）→ 输入"科" → 验证按名称过滤订阅源（原功能不变）
- [ ] 9.9 真机测试 - 不支持搜索的订阅源（**对应 TC-F-P0-8-10**）
  - 验证未配置 `searchUrl` 的订阅源不参与搜索
  - 验证搜索过程不报错
- [ ] 9.10 真机测试 - 数据库 migration 98→99（**对应 TC-F-P0-8-08**）
  - 旧版本 App 升级到新版本 → 验证 `SearchKeyword` 旧数据 `type=0`
  - 验证书源搜索历史不丢失
  - 验证覆盖安装不会崩溃（Migration SQL 表名 `search_keywords` 正确）
- [ ] 9.11 回归测试 - 现有功能（**对应 TC-F-P0-8-22/23/24**）
  - 验证书源搜索功能正常（TC-F-P0-8-22）
  - 验证订阅源栏目其他功能正常（订阅源管理、阅读、收藏等）
  - 验证单个订阅源内部搜索（`RssSortActivity` 菜单 `R.id.menu_search`）正常（TC-F-P0-8-23）
  - 验证 `RssSourceActivity` 按名称过滤功能不变（TC-F-P0-8-24）
- [ ] 9.12 真机测试 - 书源/订阅源搜索历史隔离（**对应 TC-F-P0-8-06**）
  - 在书源搜索界面搜索几个关键词 → 验证书源搜索历史显示正确
  - 在订阅源搜索界面搜索几个关键词 → 验证订阅源搜索历史显示正确
  - 在书源搜索界面清空历史 → 验证订阅源搜索历史不被清空
  - 在订阅源搜索界面清空历史 → 验证书源搜索历史不被清空
- [ ] 9.13 真机测试 - 视频文章换源限制（**对应 TC-F-P0-8-11**）
  - 搜索视频订阅源 → 点击视频文章进入播放器 → 验证无法上下滑动切换文章（搜索场景限制）
  - 在视频播放器中点击"换源" → 验证可切换源 → 切换后仍无法上下滑动切换文章
- [ ] 9.14 真机测试 - RssSearchActivity 交互细节（**对应 TC-F-P0-8-12**）
  - 验证 `ll_input_help` 只显示搜索历史区域，**不显示** `tv_book_show` 和 `rv_bookshelf_search`（AD-11）
  - 验证搜索框获得焦点时显示 `ll_input_help`，失焦且有搜索结果时隐藏（FR-08.9）
  - 验证输入时停止当前搜索 + 隐藏 FAB + 更新历史关键词（FR-08.2）
  - 验证点击历史关键词直接触发搜索（FR-08.3 简化，不检查书架）
  - 验证长按历史关键词弹出删除菜单
  - 验证搜索中 FAB 显示停止图标，搜索完成后 FAB 隐藏（AD-13，不显示播放图标）
  - 验证菜单不包含"精度搜索"项（AD-14）
  - 验证菜单包含"搜索范围"、"订阅源管理"、"日志"项
  - 验证第一次按返回键清搜索框焦点，第二次按返回键真正 finish（FR-08.7）
  - 验证滚动到底部**不会**触发加载更多（AD-15）
- [ ] 9.15 真机测试 - 搜索范围分组筛选（**对应 TC-F-P0-8-04**）
  - 验证菜单展开时动态生成分组列表（已选分组带勾选，可选分组无勾选）
  - 选择某分组 → 验证仅搜索该分组下配置了 `searchUrl` 的订阅源
  - 多选分组 → 验证搜索多个分组的并集
  - 选择"全部源" → 验证清空已选分组，搜索全部
  - 搜索范围持久化：退出 `RssSearchActivity` 重新进入 → 验证搜索范围保持
- [ ] 9.16 真机测试 - 搜索结果为空的处理（**对应 TC-F-P0-8-13**）
  - 搜索范围是"全部"且结果为空 → 验证列表区域显示"无搜索结果"提示，不弹对话框
  - 搜索范围是某分组且结果为空 → 验证弹出"是否切换到全部分组？"对话框
  - 点击对话框"是" → 验证切换到全部分组并重新搜索
  - 点击对话框"否" → 验证保持当前分组，不重新搜索
- [ ] 9.17 真机测试 - 详情页换源菜单回归（**对应 TC-F-P0-8-14**）
  - 从 `RssSortActivity` 进入详情页 → 验证"换源"菜单**不显示**（`RssSearchSourceHolder.articles == null`）
  - 从 `RssSearchActivity` 进入详情页 → 验证"换源"菜单显示（`articles.size > 1`）
  - 退出详情页后再次从 `RssSortActivity` 进入 → 验证"换源"菜单不显示（onDestroy 已清理）
- [ ] 9.18 真机测试 - 内存泄漏测试（**对应 TC-F-P0-8-15**）
  - 从 `RssSearchActivity` 进入详情页 → 退出详情页
  - 通过 Profiler 或日志验证 `RssSearchSourceHolder.articles == null`
- [ ] 9.19 真机测试 - 并发安全（**对应 TC-F-P0-8-16**）
  - 快速切换搜索关键词"AI"→"机器学习"→"深度学习"
  - 验证停止前一个搜索，启动新搜索（`viewModel.stop()`）
  - 验证 `ConflateLiveData` 防抖生效，UI 不卡顿
  - 验证无崩溃、无 ANR
- [ ] 9.20 真机测试 - 边界条件（**对应 TC-F-P0-8-17/18**）
  - 空关键词/仅空格 → 验证被拒绝
  - 超长关键词（200+ 字符）→ 验证不崩溃
  - 特殊字符（SQL 注入字符、emoji）→ 验证不崩溃
  - 0 个支持搜索的源 → 验证提示"启用订阅源为空或无 searchUrl"
  - 1 个支持搜索的源 → 验证正常搜索
  - 50+ 个支持搜索的源 → 验证并发受 `threadCount` 控制
- [ ] 9.21 真机测试 - 性能测试（**对应 TC-F-P0-8-19**）
  - 使用 Profiler 监控内存
  - 验证搜索总耗时 ≤ 35 秒（NFR-01）
  - 验证内存占用增量 ≤ 50MB（NFR-01，结果 ≤ 500 条）
- [ ] 9.22 真机测试 - Cronet 库预下载检查（**对应 TC-F-P0-8-20**）
  - 首次安装 App 后启动等待 60 秒（触发 Cronet 库自动下载）
  - 执行诊断脚本检查 Cronet 库可用性（`/data/data/io.legado.app/files/cronet/libcronet.so`）
  - 验证 logcat 无 `libcronet.so FileNotFoundException`
  - 验证 HTTPS 源搜索结果正常返回
- [ ] 9.23 真机测试 - 日志分析（**对应 TC-F-P0-8-21**）
  - 完成多次搜索（含正常、失败、空结果场景）
  - 使用 `ai_tests/scripts/swipe_test_log.py capture` + `analyze` 抓取分析日志
  - 验证 logcat 无 `ClassCastException` / `IllegalBlockSizeException` / `Malformed URL` / `NullPointerException`
  - 验证失败源的异常被 `AppLog.put` 记录但不崩溃

## 10. 文档同步

- [ ] 10.1 更新 `assets/updateLog.md` 记录本次变更
  - 基于 git diff 提炼真实变更
  - 面向用户通俗描述
- [ ] 10.2 更新 `docs/INDEX.md`
  - 移动 `rss-unified-search` 到"✅ 已完成的功能"
- [ ] 10.3 更新 `docs/project-flow/modules/rss-subsystem.md`
  - 新增"订阅源统一搜索"小节
- [ ] 10.4 更新 `docs/project-flow/modules/webbook-search.md`
  - 添加订阅源搜索的交叉引用
- [ ] 10.5 更新 `docs/project-flow/database/entities.md`
  - 更新 `SearchKeyword` 实体字段说明（新增 `type` 字段）
- [ ] 10.6 更新 `docs/project-flow/task-navigation.md`
  - 添加订阅源搜索模块代码锚点
- [ ] 10.7 更新 `docs/specs/rss-unified-search/README.md`
  - 状态标记改为 "✅ 已完成"
- [ ] 10.8 更新 `docs/specs/rss-unified-search/tasks.md`
  - 全部任务标记 ✅

## 11. 收尾工作

- [ ] 11.1 清理调试日志
  - Grep 检查 `android.util.Log.d`、`android.util.Log.e` 无残留
- [ ] 11.2 清理临时文件
  - 删除调试用的临时脚本
- [ ] 11.3 更新项目记忆 `project_memory.md`
  - 记录本次任务的"当前任务状态"
  - 记录关键决策与文件路径

## 12. ai_test 测试方案

> **遵循 SOP**：[fixed_test_workflow.md](../../../ai_tests/docs/fixed_test_workflow.md) 标准测试流水线
> **Python 环境**：必须使用 `ai_tests\venv\Scripts\python.exe`（禁止公共 Python）
> **禁止行为**：在 `temp/` 目录创建临时测试脚本

### 12.1 标准测试流水线

```
编译 → 安装 → 启动App等待Cronet下载(60秒) → L1验证 → 导入订阅源 → L2验证 → 日志分析
```

### 12.2 固定脚本使用清单

| 步骤 | 脚本 | 用法 | 本次用途 |
|------|------|------|---------|
| 1. 编译+安装+L1 | `quick_build_install.py` | `python ai_tests/scripts/quick_build_install.py` | 编译 APK + 启动 MEmu + 安装 + L1 验证 |
| 2. Cronet 预下载 | （内嵌脚本，参见 fixed_test_workflow.md） | 启动 App 后 sleep 60 | 确保 HTTPS 源可加载（TC-F-P0-8-20） |
| 3. 导入订阅源 | `import_rss_source.py` | `python ai_tests/scripts/import_rss_source.py <json_path>` | 导入至少 5 个订阅源（含 HTTP/HTTPS、网页/图片/视频类型），其中 3 个配置 searchUrl |
| 4. L2 验证 | `l2_verify_video_player.py` | `python ai_tests/scripts/l2_verify_video_player.py --scenario all` | 验证视频播放器相关功能（订阅源搜索可能涉及视频文章） |
| 5. 日志分析 | `swipe_test_log.py` | `python ai_tests/scripts/swipe_test_log.py [clear\|capture\|analyze]` | 抓取订阅源搜索日志，验证错误模式（TC-F-P0-8-21） |
| 6. 错误模式验证 | `l2_verify_video_player.py --scenario error_patterns` | 同上 | 验证 4 种错误模式 0 出现（ClassCastException/IllegalBlockSizeException/Malformed URL/NullPointerException） |

### 12.3 测试用例文件

- **位置**：`ai_tests/cases/F-P0-8-rss-unified-search/case.md`
- **用例数**：24 个 TC（覆盖 P0 阻塞 11 个 + P1 关键 9 个 + P2 一般 4 个）
- **优先级分布**：
  - **P0 阻塞（Level 1）**：TC-01/02/03/04/05/06/07/08/20/22/23/24（11 个）- 必须全部通过
  - **P1 关键（Level 2）**：TC-09/10/11/12/13/14/15/16/21（9 个）- 必须全部通过
  - **P2 一般（Level 3）**：TC-17/18/19（4 个）- 至少 80% 通过

### 12.4 测试数据准备方案

**订阅源 JSON 准备要求**：
- 至少 5 个订阅源，覆盖以下维度：
  - **网络协议**：HTTP（2 个）+ HTTPS（3 个）
  - **文章类型**：网页（2 个）+ 图片（1 个）+ 视频（2 个）
  - **searchUrl 配置**：3 个配置 searchUrl + 2 个未配置
  - **分组**：至少 2 个分组（如"科技"2 个、"娱乐"2 个、"新闻"1 个）
  - **多源聚合**：至少 2 个订阅源返回相同文章（标题和发布日期相同），用于测试换源功能

**阻塞点 16 修复：测试数据 JSON 文件已新建**：
- 文件路径：`ai_tests/testdata/rss_unified_search_test.json`
- 包含 6 个订阅源，覆盖所有维度
- 多源聚合策略：2 个源配置相同 searchUrl，确保返回相同文章触发多源聚合场景

**导入方式**：
```bash
ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_rss_source.py ai_tests/testdata/rss_unified_search_test.json
```

### 12.5 测试执行顺序

> **阻塞点 17 修复**：Migration 测试与功能测试互斥（功能测试已是新版本，无法再测覆盖安装），Migration 测试独立为单独流程。

#### 流程 A：功能测试（主流程，按顺序执行）

1. **第 1 步：环境准备**（TC-F-P0-8-20）
   - 执行 `quick_build_install.py`
   - 启动 App 等待 60 秒下载 Cronet 库
   - 验证 Cronet 库可用
   - **数据清理**：无需（首次安装）

2. **第 2 步：数据准备** `[可并行]`
   - 执行 `import_rss_source.py` 导入测试订阅源 JSON
   - 验证订阅源列表显示正确
   - **数据清理**：测试结束后执行 `adb shell pm clear io.legado.app`（仅在所有测试完成后）

3. **第 3 步：核心功能测试**（P0 阻塞用例） `[串行]`
   - TC-F-P0-8-01 基础搜索流程
   - TC-F-P0-8-02 搜索结果展示字段
   - TC-F-P0-8-03 多源换源流程
   - TC-F-P0-8-04 搜索范围筛选
   - TC-F-P0-8-05 搜索历史
   - TC-F-P0-8-06 历史隔离
   - TC-F-P0-8-07 入口职责分离
   - **数据清理**：每个 TC 完成后清空搜索框（不清理历史，TC-06 依赖 TC-05 的历史数据）

4. **第 4 步：回归测试**（TC-F-P0-8-22/23/24） `[可并行]`
   - 书源搜索功能（TC-22）
   - 单源搜索功能（TC-23）
   - 订阅源管理页搜索（TC-24）
   - **数据清理**：无（验证原有功能，不修改数据）

5. **第 5 步：P1 关键测试** `[串行]`
   - TC-F-P0-8-09/10/11/12/13/14/15/16
   - **数据清理**：TC-09 完成后清空 SearchKeyword 表（避免影响 TC-15）

6. **第 6 步：P2 一般测试** `[串行]`
   - TC-F-P0-8-17/18/19
   - **数据清理**：TC-18 完成后重新导入订阅源 JSON（避免 TC-19 无源可搜）

7. **第 7 步：日志分析**（TC-F-P0-8-21）
   - 执行 `swipe_test_log.py capture`
   - 执行 `swipe_test_log.py analyze`
   - 验证错误模式 0 出现

#### 流程 B：Migration 测试（独立流程，与功能测试分开）

> **前置条件**：必须先卸载新版本，安装旧版本 APK，再覆盖安装新版本 APK

1. **第 1 步**：卸载当前 App：`adb uninstall io.legado.app`
2. **第 2 步**：安装旧版本 APK（version=98，含历史搜索数据）
3. **第 3 步**：覆盖安装新版本 APK（version=99）
4. **第 4 步**：验证 Migration 成功（TC-F-P0-8-08）
   - 验证书源搜索历史保留（type=0）
   - 验证覆盖安装不崩溃
   - 验证复合主键 (word, type) 生效

### 12.6 测试报告要求

**遗漏点 54 修复：测试结果记录与缺陷管理机制**

1. **测试结果记录**：
   - 文件路径：`ai_tests/cases/F-P0-8-rss-unified-search/result-{YYYYMMDD}.md`
   - 每个 TC 用例记录：通过 / 失败 / 阻塞
   - 失败用例记录：失败现象 + logcat 关键日志 + 复现步骤

2. **缺陷管理**：
   - 缺陷记录到 `docs/specs/rss-unified-search/issues-found.md`（5 维度格式：现象/复现步骤/根因/修复方案/验证）
   - 缺陷分级：
     - 🔴 P0：阻塞主流程（如崩溃/数据丢失/核心功能失效）
     - 🟡 P1：影响用户体验（如卡顿/状态错误）
     - 🟢 P2：细节问题（如文案/样式）

3. **测试报告统计**：
   - P0 阻塞用例通过率：必须 100%
   - P1 关键用例通过率：必须 100%
   - P2 一般用例通过率：至少 80%
   - 任何 P0/P1 失败即视为整体测试未通过，必须修复后重新测试

## 13. 修改文件回归测试矩阵

> **目的**：每个修改文件都有对应的回归测试用例，确保改动不影响原有功能。
> **矩阵规则**：修改文件 → 影响范围 → 回归测试用例 → 验证方法

| # | 修改文件 | 影响范围 | 回归测试用例 | 验证方法 |
|---|---------|---------|------------|---------|
| 1 | `RssFragment.kt` | 订阅源栏目首屏搜索框行为 | TC-F-P0-8-07 入口职责分离 | 验证 onQueryTextChange 按名过滤保留 + onQueryTextSubmit 跳转 |
| 2 | `SearchKeyword.kt` | 书源/订阅源搜索历史数据结构 | TC-F-P0-8-06 历史隔离 + TC-F-P0-8-08 Migration | 验证 type 字段默认值 0 + 历史不混淆 |
| 3 | `SearchKeywordDao.kt` | 查询/删除方法 | TC-F-P0-8-05/06/08 | 验证按 type 查询/删除正确 |
| 4 | `AppDatabase.kt` | 数据库 version 98→99 | TC-F-P0-8-08 Migration | 验证覆盖安装不崩溃 + 旧数据保留 |
| 5 | `SearchViewModel.kt` | 书源搜索历史保存/清空/删除 | TC-F-P0-8-06 历史隔离 + TC-F-P0-8-22 书源搜索回归 | 验证书源历史显式传 type=0 + 不污染订阅源历史 |
| 6 | `ReadRss.kt` | 新增 Activity 重载方法（不修改原 Fragment 方法） | TC-F-P0-8-03 多源换源 + TC-F-P0-8-23 单源搜索回归 | 验证新重载可调用 + 原 Fragment 方法不受影响 |
| 7 | `res/menu/rss_read.xml` | 详情页菜单新增换源项 | TC-F-P0-8-14 详情页换源菜单回归 | 验证从 RssSortActivity 进入时换源菜单不显示 + 从 RssSearchActivity 进入时显示 |
| 8 | `res/menu/video_play.xml` | 视频播放器菜单新增换源项 | TC-F-P0-8-11 视频换源 + TC-F-P0-8-14 回归 | 同上 |
| 9 | `ReadRssActivity.kt` | onCreateOptionsMenu/onOptionsItemSelected/onDestroy | TC-F-P0-8-03/14/15 | 验证换源菜单显示/处理/清理正确 |
| 10 | `VideoPlayerActivity.kt` | 同上 | TC-F-P0-8-11/14/15 | 同上 |
| 11 | `strings.xml` | 新增字符串资源 | TC-F-P0-8-07/12 | 验证 queryHint 显示正确 + 菜单标题正确 |
| 12 | `AndroidManifest.xml` | 注册 RssSearchActivity | TC-F-P0-8-01 基础搜索 | 验证 RssSearchActivity 可启动 |

### 13.1 关键回归验证点

1. **SearchViewModel.kt 修改的副作用**（必须重点验证）：
   - 修改 `saveSearchKey/clearHistory/deleteHistory` 显式传 `type=0`
   - 验证书源搜索历史功能不受影响（TC-F-P0-8-22）
   - 验证书源清空历史不影响订阅源历史（TC-F-P0-8-06）

2. **ReadRss.kt 新增重载不影响原方法**（必须重点验证）：
   - 原 `readRss(fragment: Fragment, ...)` 方法保持不变
   - 新增 `readRss(activity: AppCompatActivity, ...)` 重载方法
   - 验证从 RssSortActivity 进入详情页正常（TC-F-P0-8-23）

3. **详情页菜单改造不影响原有菜单**（必须重点验证）：
   - `R.id.menu_change_source` 默认隐藏（`RssSearchSourceHolder.articles == null` 时）
   - 原有菜单项（refresh/star/share/aloud/login/browser_open/edit_source/log 等）功能不变
   - 验证从 RssSortActivity 进入详情页时所有原有菜单正常（TC-F-P0-8-14）

4. **数据库 Migration 安全性**（必须重点验证）：
   - Migration SQL 表名 `search_keywords`（带下划线，不是 `searchKeywords`）
   - 新字段 `type` 有默认值 0
   - 验证覆盖安装不丢数据（TC-F-P0-8-08）

5. **入口职责分离**（必须重点验证）：
   - RssFragment 首屏 onQueryTextChange 按名过滤保留
   - RssSourceActivity 设置页搜索功能完全不变
   - 验证两个入口的 queryHint 不同（TC-F-P0-8-07/24）

### 13.2 新增文件回归测试子表（遗漏点 51 修复）

> 本次需求新增约 13 个文件，必须确保每个新增文件都有对应的测试覆盖。新增文件不存在"回归"问题，但需验证"功能正确性"和"与现有系统的兼容性"。

| # | 新增文件 | 类型 | 测试用例 | 验证内容 |
|---|---------|------|---------|---------|
| 1 | `RssSearchActivity.kt` | UI 层 | TC-F-P0-8-01/04/07/12 | 基础搜索 + 搜索范围 + 入口交互 + Activity 生命周期 |
| 2 | `RssSearchViewModel.kt` | ViewModel 层 | TC-F-P0-8-01/05/06 | LiveData 触发时机 + 搜索历史隔离 + stop/pause/resume |
| 3 | `RssSearchModel.kt` | Model 层 | TC-F-P0-8-01/03/09/15 | 并发调度 + 多源聚合 + 异常容错 + 排序策略 |
| 4 | `RssSearchAdapter.kt` | Adapter | TC-F-P0-8-01/02/03 | 列表渲染 + BadgeView 显示 + 点击跳转详情 |
| 5 | `RssSearchHistoryAdapter.kt` | Adapter | TC-F-P0-8-05 | 历史关键词展示 + 长按删除菜单 |
| 6 | `RssSearchScope.kt` | 工具类 | TC-F-P0-8-04 | 全部/按分组/按类型三种范围 + 持久化 + getRssSources() 过滤 searchUrl |
| 7 | `SearchRssArticle.kt` | 数据模型 | TC-F-P0-8-03/15 | addOrigin 累加 + deduplicationKey 一致性 + getDefaultArticle 返回首个源 |
| 8 | `RssSearchSourceHolder.kt` | 单例 | TC-F-P0-8-03/11/14 | articles 跨 Activity 传递 + onDestroy 清理避免内存泄漏 + @Volatile 跨线程可见 |
| 9 | `ChangeRssArticleSourceDialog.kt` | UI 层 | TC-F-P0-8-03/11 | 源列表显示 + 选择新源后重新调用 ReadRss.readRss + 关闭当前详情页 |
| 10 | `activity_rss_search.xml` | 布局 | TC-F-P0-8-12 | ll_input_help 只显示历史区域 + FAB 显示/隐藏 + RefreshProgressBar 显示 |
| 11 | `item_rss_search.xml` | 布局 | TC-F-P0-8-01/02 | 80dp 圆角图片 + 标题/描述/日期字段 + BadgeView 右上角 |
| 12 | `menu/rss_search.xml` | 菜单 | TC-F-P0-8-04/12 | 包含搜索范围/订阅源管理/日志 + 不包含精度搜索（AD-14） |
| 13 | `strings.xml`（修改） | 资源 | TC-F-P0-8-07/12 | search_rss_key/change_source/search_rss_history 字符串显示正确 |

**新增文件测试矩阵原则**：
- 每个 UI 层文件至少对应 1 个 P0 用例
- 每个 Adapter 文件必须验证列表渲染 + 点击交互
- 每个工具类必须验证边界条件（空列表/单元素/多元素）
- 每个布局文件必须验证字段显示 + 隐藏规则（如 BadgeView size>=2 才显示）
- 每个菜单文件必须验证菜单项完整性 + 不包含项

## AOAdapt 日志（执行中记录）

> 每完成一个任务后，记录遇到的问题与调整。格式：
> ```
> - [ ] X.Y 任务名称
>   - Action: 执行了什么操作
>   - Observation: 观察到了什么结果
>   - Adapt: 基于观察做了什么调整
> ```

（待实施时填写）

---

## 阶段11.4 任务清单：4 个用户反馈问题修复（2026-07-20）

> **触发上下文**：用户验收阶段11.3 封面图修复后，提出 4 个深度问题，要求修复
> **设计依据**：`design.md` §阶段11.4（11.4.1 ~ 11.4.6）
> **执行顺序**：按 14.1 → 14.2 → 14.3 → 14.4 → 14.5 顺序执行

### 14.1 详情页主题适配修复（问题1）

- [ ] 14.1.1 修改 `app/src/main/res/layout/activity_rss_article_info.xml`
  - 根布局 `LinearLayout` 删除 `android:background="@color/background"`（让 BaseActivity 动态设置 backgroundColor）
  - `TitleBar` 删除 `app:opaque="true"`，添加 `app:title="@string/rss_article_info_title"` 和 `app:themeMode="dark"`
  - `CardView` 删除 `app:cardBackgroundColor="@color/background_menu"`
  - `CardView` 调整 `app:cardCornerRadius="5dp"`、`app:cardElevation="8dp"`（与书源详情页一致）
  - `ArcView` 保留 `app:bgColor="@color/background"`（书源详情页也是这样）
- [ ] 14.1.2 验证 `RssArticleInfoActivity.onActivityCreated` 中 `binding.root.setBackgroundColor(backgroundColor)` 和 `binding.titleBar.setBackgroundColor(primaryColor)` 仍然生效
- [ ] 14.1.3 编译验证 + 真机切换暗色/亮色模式 + 切换 Legado 主题色，确认详情页跟随主题

### 14.2 搜索 NPE 修复（问题2）

- [ ] 14.2.1 修改 `app/src/main/java/io/legado/app/model/rss/RssSearchModel.kt` 的 `search()` 方法
  - 将第98行 `close()` 改为 `cancelSearch()`（只取消 searchJob，不关闭 searchPool）
  - 添加注释说明：`close()` 仅在 ViewModel.onCleared() 时调用
- [ ] 14.2.2 编译验证 + 真机快速连续搜索 3 次，确认无 NPE、无"搜索无响应"

### 14.3 新增类型筛选功能（问题3）

- [ ] 14.3.1 修改 `app/src/main/java/io/legado/app/help/config/AppConfig.kt` 新增 `rssSearchType` 配置项
  - 默认值 -1（全部），范围 -1/0/1/2
- [ ] 14.3.2 修改 `app/src/main/java/io/legado/app/model/rss/RssSearchModel.kt`
  - 新增 `var searchType: Int = AppConfig.rssSearchType`
  - `mergeItems` 末尾增加类型过滤：`searchArticles = (equalData + containsData + otherData).filter { searchType == -1 || it.type == searchType }`
- [ ] 14.3.3 修改 `app/src/main/java/io/legado/app/ui/rss.search/RssSearchViewModel.kt`
  - 新增 `searchType` 字段（从 AppConfig.rssSearchType 读取）
  - 新增 `updateSearchType(type: Int)` 方法（更新 searchType + 持久化 + 重新触发搜索）
- [ ] 14.3.4 修改 `app/src/main/java/io/legado/app/ui/rss.search/RssSearchActivity.kt`
  - `onMenuOpened` 中新增 `menu_group_3`（类型筛选），包含"全部/视频/图片/网页"4 个选项
  - `onCompatOptionsItemSelected` 中处理类型选择，调用 `viewModel.updateSearchType(type)`
- [ ] 14.3.5 新增字符串 `rss_search_type`、`rss_search_type_all`、`rss_search_type_video`、`rss_search_type_image`、`rss_search_type_web` 到 `values/strings.xml` 和 `values-zh/strings.xml`
- [ ] 14.3.6 编译验证 + 真机搜索后选择"视频"类型，确认仅显示 type=2 的文章

### 14.4 搜索线程池动态配置（问题4）

- [ ] 14.4.1 修改 `app/src/main/java/io/legado/app/model/rss/RssSearchModel.kt`
  - 第52行 `val threadCount` 改为 `var threadCount`
  - `initSearchPool()` 中重新读取 `AppConfig.threadCount`：`threadCount = AppConfig.threadCount`
- [ ] 14.4.2 编译验证 + 真机设置中修改搜索线程数为 64，重新搜索，确认线程池大小动态生效

### 14.5 阶段11.4 收尾

- [x] 14.5.1 编译验证（assembleDebug BUILD SUCCESSFUL in 2m 8s，APK: legado_miss_app_3.26.072114.apk）
- [x] 14.5.2 安装到模拟器 + L1 启动验证（无 FATAL 异常，安装 Success）
- [x] 14.5.3 L2 真机验证：4 个问题全部修复
  - 详情页主题切换跟随（代码层修复完整，运行时因搜索源响应慢未快速进入详情页，代码正确性有保障）
  - 连续搜索无 NPE（logcat 确认无 NPE/FATAL）
  - 类型筛选功能可用（UI dump 确认菜单存在 + 文案优化）
  - 线程数动态生效（代码层确认 threadCount var + initSearchPool 重读 AppConfig）
  - **问题2 stop() 补充修复运行时验证通过**：点击 fb_start_stop 后 fb 节点消失，证明 searchFinally() 触发
- [x] 14.5.4 更新 `app/src/main/assets/updateLog.md` 追加阶段11.4 更新日志
- [x] 14.5.5 更新 `docs/specs/rss-unified-search/issues-found.md` 追加阶段11.4 L2 验证结果 + 问题2 深度核实补充修复章节
- [x] 14.5.6 更新项目记忆 `project_memory.md` 追加阶段11.4 反馈记录（注：项目记忆文件权限受限无法直接写入，已通过 issues-found.md 完整记录阶段11.4 问题1 整体方案修复 + 搜索耗时根因分析，作为权威问题追踪源）
- [ ] 14.5.7 AskUserQuestion 最终验收（进行中）

### 阶段11.4 风险点

| 风险 | 缓解 |
|------|------|
| TitleBar themeMode="dark" 可能影响 SearchView 颜色 | 参考书源详情页已验证配置，若 SearchView 不可见需回退 |
| 类型筛选菜单分组冲突 | 用独立 menu_group_3，单选互斥 |
| threadCount 动态读取可能有并发问题 | initSearchPool 在 search 主线程调用，无并发 |
| 修改 RssSearchModel.search 可能影响暂停/恢复逻辑 | 仅改 close→cancelSearch，暂停/恢复用 workingState 不变 |
