# SA-4 RSS 订阅源与发现页深度对比分析

> 子代理任务 SA-4 输出。对比范围：RSS/订阅源/发现页相关文件 Archive vs 本项目。
> Archive 路径前缀：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/`
> 本项目路径前缀：`app/src/main/java/io/legado/app/`
> 严格遵守 output-safety 规范：所有源名称/URL/cookie 用代号替代。

## 1. 模块概述

| 维度 | Archive | 本项目 |
|------|---------|--------|
| model/rss 文件数 | 3（Rss + RssParserByRule + RssParserDefault） | 3（同名） |
| data/entities/Rss* 实体 | 4（RssSource/RssArticle/RssStar/RssReadRecord） | 6（多 RssRoute/RssEpisode 播客相关） |
| data/dao/Rss* Dao | 4（RssSourceDao/RssArticleDao/RssStarDao/RssReadRecordDao） | 4（同名） |
| ui/rss/ 总文件数 | 34（含 RssSearchActivity/RssSourceScreen/RuleSubScreen/RuleSubEditComposeDialog） | 36（含 RssSourceAdapterCompact/RssSourceSort/RssSourceAdapterGrid/RuleSubAdapter） |
| ui/main/explore/ 文件数 | 9（含 DiscoverySuite 系列 4 + ExploreModernListScreen + DiscoverTagAdapter） | 4（基础 4 件） |
| ui/main/rss/ 文件 | 3（RssFragment/RssViewModel/RssAdapter） | 3（同名，但实现差异大） |
| RssSource 实体字段 | 38 字段（无 parseConcurrency/weight/lastHost） | 41 字段（多 parseConcurrency/weight/lastHost） |
| 订阅源解析并发 | 串行 for 循环 | 并行 async+Semaphore 限流（P1-1 优化） |
| 订阅源预连接 | 无 | F-P1-F 预连接前 3 篇 |
| 发现页 UI 模式 | 传统列表 + Compose 双轨 + DiscoverySuite 套件 | 传统列表 + 文件夹/标签/类型三模式 |
| 统一源选择对话框 | 有（SourceSelectDialog.kt，泛型 `<T>`） | 无 |
| 订阅内容搜索 Activity | 有（RssSearchActivity.kt） | 无（仅 RssSortActivity 内嵌搜索） |
| 搜索结果合并工具 | 有（SearchBookMergeUtils.kt） | 无 |
| 发现套件系统 | 有（DiscoverySuite 系列 4 文件） | 无 |
| 现代列表/网格 Compose UI | 有（ExploreModernListScreen.kt） | 无 |

**核心差异一句话总结**：
Archive 在 RSS/发现页层面引入了"统一源选择 + 订阅内容搜索 + Compose 现代列表 + 发现套件系统"四大增强；本项目侧重"并行解析优化 + lastHost 回填 + 失效分组管理 + 文件夹/标签/类型三模式发现页"，两边走的是不同优化方向。

---

## 2. 文件清单对比

### 2.1 Archive 侧文件清单

| # | 文件路径（相对 Archive 根） | 大小 | 用途 |
|---|----------------------------|------|------|
| 1 | `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 160 行 | RSS 文章/正文获取入口（含 WebViewPool.Scope 参数） |
| 2 | `app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 140 行 | 按规则解析 RSS（**串行 for 循环**） |
| 3 | `app/src/main/java/io/legado/app/model/rss/RssParserDefault.kt` | 150 行 | 默认 XML 解析（与本项目完全一致） |
| 4 | `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 214 行 | RSS 源实体（38 字段，无 parseConcurrency/weight/lastHost） |
| 5 | `app/src/main/java/io/legado/app/data/entities/RssArticle.kt` | 同本项目 | RSS 文章实体 |
| 6 | `app/src/main/java/io/legado/app/data/entities/RssStar.kt` | 同本项目 | RSS 收藏实体 |
| 7 | `app/src/main/java/io/legado/app/data/entities/RssReadRecord.kt` | 同本项目 | RSS 阅读记录实体 |
| 8 | `app/src/main/java/io/legado/app/ui/rss.article/RssSearchActivity.kt` | 104 行 | **【Archive 独有】** 订阅内容搜索入口 Activity |
| 9 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceScreen.kt` | 80+ 行 | **【Archive 独有】** RSS 源 Compose 列表 Screen |
| 10 | `app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubScreen.kt` | - | **【Archive 独有】** 规则订阅 Compose Screen |
| 11 | `app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubEditComposeDialog.kt` | - | **【Archive 独有】** 规则订阅编辑 Compose 对话框 |
| 12 | `app/src/main/java/io/legado/app/ui.main.explore/ExploreFragment.kt` | 163 KB | 发现页 Fragment（**集成 DiscoverySuite ComposeView**） |
| 13 | `app/src/main/java/io/legado/app/ui.main.explore/ExploreModernListScreen.kt` | 396 行 | **【Archive 独有】** Compose 现代列表/网格 Screen |
| 14 | `app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteConfig.kt` | 228 行 | **【Archive 独有】** 发现套件数据模型 + DiscoverySuiteStore |
| 15 | `app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteHomeScreen.kt` | 51 KB | **【Archive 独有】** 发现套件 Compose 首页 |
| 16 | `app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteManageActivity.kt` | 77 KB | **【Archive 独有】** 发现套件管理 Activity |
| 17 | `app/src/main/java/io/legado/app/ui.main.explore/DiscoverTagAdapter.kt` | 466 行 | **【Archive 独有】** 发现标签 Adapter |
| 18 | `app/src/main/java/io/legado/app/ui.main.rss/RssFragment.kt` | 750+ 行 | 主界面订阅 Tab Fragment（**集成 SourceSelectDialog + RssSearchActivity**） |
| 19 | `app/src/main/java/io/legado/app/ui.widget/SourceSelectDialog.kt` | 268 行 | **【Archive 独有】** 统一源选择对话框（泛型 `<T>` + Compose） |
| 20 | `app/src/main/java/io/legado/app.utils/SearchBookMergeUtils.kt` | 91 行 | **【Archive 独有】** 搜索结果合并工具（appendReplacing/prependReplacing） |

### 2.2 本项目侧文件清单

| # | 文件路径（相对项目根） | 大小 | 用途 |
|---|----------------------|------|------|
| 1 | `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 180 行 | RSS 文章/正文获取入口（**含 lastHost 回填 + F-P1-F 预连接**） |
| 2 | `app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 179 行 | 按规则解析 RSS（**并行 async+Semaphore 限流**） |
| 3 | `app/src/main/java/io/legado/app/model/rss/RssParserDefault.kt` | 150 行 | 默认 XML 解析（与 Archive 完全一致） |
| 4 | `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 249 行 | RSS 源实体（**41 字段，多 parseConcurrency/weight/lastHost**） |
| 5 | `app/src/main/java/io/legado/app/data/entities/RssArticle.kt` | 同 Archive | RSS 文章实体 |
| 6 | `app/src/main/java/io/legado/app/data/entities/RssStar.kt` | 同 Archive | RSS 收藏实体 |
| 7 | `app/src/main/java/io/legado/app/data/entities/RssReadRecord.kt` | 同 Archive | RSS 阅读记录实体 |
| 8 | `app/src/main/java/io/legado/app/data/entities/RssRoute.kt` | - | **【本项目独有】** RSS 路由实体（播客相关） |
| 9 | `app/src/main/java/io/legado/app/data/entities/RssEpisode.kt` | - | **【本项目独有】** RSS 单集实体（播客相关） |
| 10 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterCompact.kt` | - | **【本项目独有】** RSS 源紧凑适配器 |
| 11 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceSort.kt` | - | **【本项目独有】** RSS 源排序 |
| 12 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterGrid.kt` | - | **【本项目独有】** RSS 源网格适配器 |
| 13 | `app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubAdapter.kt` | - | **【本项目独有】** 规则订阅 Adapter |
| 14 | `app/src/main/java/io/legado/app/ui.main.explore/ExploreFragment.kt` | 501 行 | 发现页 Fragment（**文件夹/标签/类型三模式**） |
| 15 | `app/src/main/java/io/legado/app/ui.main.rss/RssFragment.kt` | 较短 | 主界面订阅 Tab Fragment（无 SourceSelectDialog/RssSearchActivity） |

### 2.3 独有/共有文件矩阵

| 文件 / 模块 | Archive | 本项目 | 差异类型 |
|-------------|---------|--------|---------|
| `model/rss/Rss.kt` | ✅ | ✅ | 实现差异（参数/优化） |
| `model/rss/RssParserByRule.kt` | ✅ | ✅ | 实现差异（串行 vs 并行） |
| `model/rss/RssParserDefault.kt` | ✅ | ✅ | **完全一致** |
| `data/entities/RssSource.kt` | ✅ | ✅ | 字段差异（3 字段） |
| `data/entities/RssArticle.kt` | ✅ | ✅ | 一致 |
| `data/entities/RssStar.kt` | ✅ | ✅ | 一致 |
| `data/entities/RssReadRecord.kt` | ✅ | ✅ | 一致 |
| `data/entities/RssRoute.kt` | ❌ | ✅ | 本项目独有（播客） |
| `data/entities/RssEpisode.kt` | ❌ | ✅ | 本项目独有（播客） |
| `ui/rss/article/RssSearchActivity.kt` | ✅ | ❌ | **Archive 独有**（订阅内容搜索） |
| `ui/rss/source/manage/RssSourceScreen.kt` | ✅ | ❌ | Archive 独有（Compose） |
| `ui/rss/subscription/RuleSubScreen.kt` | ✅ | ❌ | Archive 独有（Compose） |
| `ui/rss/subscription/RuleSubEditComposeDialog.kt` | ✅ | ❌ | Archive 独有（Compose） |
| `ui/rss/source/manage/RssSourceAdapterCompact.kt` | ❌ | ✅ | 本项目独有 |
| `ui/rss/source/manage/RssSourceSort.kt` | ❌ | ✅ | 本项目独有 |
| `ui/rss/source/manage/RssSourceAdapterGrid.kt` | ❌ | ✅ | 本项目独有 |
| `ui/rss/subscription/RuleSubAdapter.kt` | ❌ | ✅ | 本项目独有 |
| `ui/main/explore/ExploreFragment.kt` | ✅ | ✅ | 实现差异（巨大） |
| `ui/main/explore/ExploreViewModel.kt` | ✅ | ✅ | 实现差异 |
| `ui/main/explore/ExploreAdapter.kt` | ✅ | ✅ | 实现差异 |
| `ui/main/explore/ExploreDiffItemCallBack.kt` | ✅ | ✅ | 一致 |
| `ui/main/explore/ExploreModernListScreen.kt` | ✅ | ❌ | **Archive 独有**（Compose 现代列表） |
| `ui/main/explore/DiscoverySuiteConfig.kt` | ✅ | ❌ | **Archive 独有**（发现套件数据模型） |
| `ui/main/explore/DiscoverySuiteHomeScreen.kt` | ✅ | ❌ | **Archive 独有**（Compose 套件首页） |
| `ui/main/explore/DiscoverySuiteManageActivity.kt` | ✅ | ❌ | **Archive 独有**（套件管理 Activity） |
| `ui/main/explore/DiscoverTagAdapter.kt` | ✅ | ❌ | **Archive 独有**（发现标签 Adapter） |
| `ui/main/rss/RssFragment.kt` | ✅ | ✅ | 实现差异（SourceSelectDialog/RssSearch 集成） |
| `ui/widget/SourceSelectDialog.kt` | ✅ | ❌ | **Archive 独有**（统一源选择） |
| `utils/SearchBookMergeUtils.kt` | ✅ | ❌ | **Archive 独有**（合并入口工具） |

**小结**：
- Archive 独有 11 个核心文件（含 4 个 DiscoverySuite + 4 个 RSS/订阅 Compose + SourceSelectDialog + SearchBookMergeUtils + RssSearchActivity）
- 本项目独有 7 个文件（2 个播客实体 + 3 个 RSS 源 Adapter 变体 + 2 个 RuleSub 适配器）
- 两边共有的核心 model/entities/dao 文件结构基本一致，差异集中在实现细节

---

## 3. 核心文件深度对比

### 3.1 RssSource 实体对比

**字段对比表**：

| 字段名 | Archive | 本项目 | 差异说明 |
|--------|---------|--------|---------|
| sourceUrl | ✅ | ✅ | 主键，一致 |
| sourceName | ✅ | ✅ | 一致 |
| sourceIcon | ✅ | ✅ | 一致 |
| sourceGroup | ✅ | ✅ | 一致 |
| sourceComment | ✅ | ✅ | 一致 |
| enabled | ✅ | ✅ | 一致 |
| variableComment | ✅ | ✅ | 一致 |
| jsLib | ✅ | ✅ | 一致 |
| enabledCookieJar | ✅ | ✅ | 一致 |
| concurrentRate | ✅ | ✅ | 一致（请求并发率） |
| header | ✅ | ✅ | 一致 |
| loginUrl | ✅ | ✅ | 一致 |
| loginUi | ✅ | ✅ | 一致 |
| loginCheckJs | ✅ | ✅ | 一致 |
| coverDecodeJs | ✅ | ✅ | 一致 |
| sortUrl | ✅ | ✅ | 一致 |
| singleUrl | ✅ | ✅ | 一致（"是否单 url 源"） |
| articleStyle | ✅ | ✅ | 一致 |
| ruleArticles/ruleNextPage/ruleTitle/rulePubDate/ruleDescription/ruleImage/ruleLink/ruleContent | ✅ | ✅ | 一致 |
| contentWhitelist/contentBlacklist | ✅ | ✅ | 一致 |
| shouldOverrideUrlLoading | ✅ | ✅ | 一致 |
| style | ✅ | ✅ | 一致 |
| enableJs/loadWithBaseUrl | ✅ | ✅ | 一致 |
| injectJs/preloadJs | ✅ | ✅ | 一致 |
| startHtml/startStyle/startJs | ✅ | ✅ | 一致 |
| showWebLog | ✅ | ✅ | 一致 |
| lastUpdateTime/customOrder | ✅ | ✅ | 一致 |
| type/preload | ✅ | ✅ | 一致 |
| **cacheFirst** | `false` | `true` | **默认值差异** |
| searchUrl | ✅ | ✅ | 一致（搜索 URL 模板，两边都有但本项目无 UI 入口使用） |
| **parseConcurrency** | ❌ | ✅ Int = 0 | **【本项目独有】** 解析并发数（0=用全局配置） |
| **weight** | ❌ | ✅ Int = 0 | **【本项目独有】** 权重值（校验后回填，用于排序） |
| **lastHost** | ❌ | ✅ String? = null | **【本项目独有】** AnalyzeUrl 解析后的真实域名，UI 分组优先用 |

**方法对比**：

| 方法 | Archive | 本项目 | 差异 |
|------|---------|--------|------|
| getTag/getKey | ✅ | ✅ | 一致 |
| equals/hashCode | ✅ | ✅ | 一致 |
| equal(source) | 不含 parseConcurrency/weight | 含 parseConcurrency/weight | 本项目扩展 |
| getDisplayNameGroup | ✅ | ✅ | 一致 |
| addGroup/removeGroup | ✅ | ✅ | 一致 |
| getDisplayVariableComment | ✅ | ✅ | 一致 |
| **hasGroup(group)** | ❌ | ✅ | **【本项目独有】** 判断是否包含指定分组 |
| **removeInvalidGroups()** | ❌ | ✅ | **【本项目独有】** 移除失效相关分组（"失效"/"校验超时"） |

**小结**：
- 两边 RssSource 字段几乎一致，**Archive 没有为"纯 URL 订阅源"添加新字段**——而是利用两边都有的 `singleUrl: Boolean = false` 字段，配合 RssSortActivity 的 `pureSearch` 参数实现"纯 URL 模式" UI 行为
- 本项目独有 3 字段（parseConcurrency/weight/lastHost）是为了支持并行解析优化和源校验/失效分组管理
- 本项目独有 `hasGroup` 和 `removeInvalidGroups` 方法，用于校验失效源后的分组清理

### 3.2 RssParser 对比

#### 3.2.1 RssParserByRule.kt 对比

**核心差异**：**串行（Archive） vs 并行（本项目）**

| 维度 | Archive（140 行） | 本项目（179 行） |
|------|------------------|----------------|
| 循环方式 | `for ((index, item) in collections.withIndex())` 串行 | `coroutineScope { collections.mapIndexed { async(Dispatchers.IO) { Semaphore.withPermit { ... } } }.awaitAll().filterNotNull().toMutableList() }` 并行 |
| AnalyzeRule 实例 | 单实例共享（循环外创建一次） | 每项独立实例（避免并发数据错乱） |
| 限流 | 无 | `Semaphore(parseConcurrency)` 限流（源级 > 0 优先，否则全局 `AppConfig.rssParseConcurrency` 默认 3） |
| 错误处理 | 抛出异常中断整个列表解析 | try-catch 单项失败返回 null，不影响整体 |
| articleList 构建 | for 循环内逐项 add | awaitAll 后 filterNotNull + 批量 forEach 设置 sort/origin |
| 失败日志 | 无 | `AppLog.put("RSS列表项解析失败 index=$index", e)` |
| 调试日志 | `Debug.log(sourceUrl, "└列表大小:${collections.size}")` | 额外 `Debug.log(sourceUrl, "┌并行解析列表项(共${collections.size}项,限流${parseConcurrency})")` 和 `"└并行解析完成(成功${articleList.size}/${collections.size}项)"` |
| 依赖 | 无并发库 | `kotlinx.coroutines.sync.Semaphore`、`kotlinx.coroutines.sync.withPermit`、`coroutineScope`、`async`、`awaitAll`、`Dispatchers.IO` |

**关键技术点**（本项目并行化硬性前提）：
1. **每 item 独立 AnalyzeRule 实例**：因为 `setRuleData`/`setContent` 修改实例状态，复用会并发数据错乱；`AnalyzeRule` 的 `evalJSCallCount++`/`topScopeRef`/`scriptCache` 非线程安全
2. **articleList 不在并行块内 add**：`mutableListOf` 非线程安全，awaitAll 后批量收集
3. **顺序保证**：`mapIndexed` + `awaitAll` 保持发起顺序，`filterNotNull` 保持顺序，与原 for 循环结果一致
4. **并发数策略**：源级 `parseConcurrency > 0` 优先，否则使用全局 `AppConfig.rssParseConcurrency`（默认 3）

**性能影响**：本项目并行化可显著减少大列表（如 50+ 项）的解析时间，但会增加内存开销（每项独立 AnalyzeRule 实例 + JS 上下文）。

#### 3.2.2 RssParserDefault.kt 对比

**完全一致**（两边 150 行代码逐字符相同）。该文件用 `XmlPullParser` 解析标准 RSS 2.0 XML，提取 item/title/link/thumbnail/enclosure/description/content:encoded/pubDate/time 字段。两边都没有任何修改。

### 3.3 Rss.kt 入口对比

| 维度 | Archive（160 行） | 本项目（180 行） |
|------|------------------|-----------------|
| `getArticles` 函数签名 | `(scope, sortName, sortUrl, rssSource, page, key, context, **webViewPoolScope: WebViewPool.Scope = GLOBAL**)` | `(scope, sortName, sortUrl, rssSource, page, key, context)` |
| `getArticlesAwait` 函数签名 | 同上含 `webViewPoolScope` | 同上不含 |
| **lastHost 回填** | ❌ 无 | ✅ `SourceLastHostHelper.fillBack(rssSource, analyzeUrl)` |
| **F-P1-F 预连接** | ❌ 无 | ✅ 列表加载完成后对前 3 篇文章域名发起 HEAD 预连接，减少点击延迟 300-1000ms |
| 预连接实现 | - | `kotlinx.coroutines.coroutineScope { articles.first.take(3).mapIndexed { async(Dispatchers.IO) { warmUpConnection(article.link) } }.awaitAll() }` |
| 预连接失败处理 | - | `kotlin.runCatching { ... }` 失败不影响列表显示 |
| 日志 | 用 `Debug.log` | 多 `AppLog.put("Rss 预连接: 第${index + 1}篇")` |
| 错误重定向检测 | ✅ `checkRedirect` | ✅ 同 |

**关键技术点**：
- **Archive 引入 WebViewPool.Scope 参数**：允许源指定使用全局 WebView 池还是发现页专用 WebView 池（`WebViewPool.Scope.DISCOVERY`），这是为发现页和订阅页 WebView 复用做的资源隔离
- **本项目引入 lastHost 回填 + 预连接**：是源校验流程和点击性能优化的基础设施

### 3.4 订阅源 UI 对比

#### 3.4.1 RssSearchActivity.kt（Archive 独有，订阅内容搜索）

**文件路径**：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss/article/RssSearchActivity.kt`

**核心实现**：
- 入口方法：`companion object { fun start(context, sourceUrl, key? = null) }`
- 接收 Intent：`sourceUrl` + 可选 `key`
- 流程：
  1. `viewModel.initData(intent)` 加载 RssSource（含 searchUrl）
  2. 校验 `source.searchUrl.isNullOrBlank()`，为空则 toast + finish
  3. `setupSearchView()` 配置搜索框，`queryHint = getString(R.string.rss_search_hint)`
  4. `submitSearch(key)` 用 `source.searchUrl` 作为搜索 URL 模板，replace 进 `RssArticlesFragment(getString(R.string.search), searchUrl, key)`
- 与 RssSortViewModel 协同：`viewModel.searchKey = key`、`viewModel.rssSource = source`

**关键意义**：本项目 RssSource 实体也有 `searchUrl` 字段（行 115），但**本项目没有 RssSearchActivity**，所以本项目的 searchUrl 字段没有任何 UI 入口使用！这是一个"数据模型已就绪但 UI 入口缺失"的状态。

#### 3.4.2 RssSourceScreen.kt（Archive 独有，RSS 源 Compose 列表）

**文件路径**：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceScreen.kt`

**核心实现**：
- `@Composable internal fun RssSourceScreen(sources, selectedUrls, isSelectMode, reorderEnabled, onReorder, onToggleSelect, onToggleEnabled, onEdit, sourceMenuActions)`
- 用 `AppManagementLazyColumn` + `AppManagementListRow` + `AppManagementMenuAction` 实现
- 集成 `sh.calvin.reorderable`（可拖拽排序）库
- `sourcesSignature` 字段计算源列表指纹（用 `\u001F` 和 `\u001E` 分隔），用于响应式更新
- `referentialEqualityPolicy()` 引用相等策略优化重组

**对比本项目**：本项目用 `RssSourceAdapter` + `RssSourceAdapterCompact` + `RssSourceAdapterGrid` 三个传统 RecyclerView Adapter，无 Compose 实现。

#### 3.4.3 RssFragment.kt（主界面订阅 Tab）对比

| 维度 | Archive | 本项目 |
|------|---------|--------|
| 行数 | 750+ 行 | 较短 |
| 引入 SourceSelectDialog | ✅ `import io.legado.app.ui.widget.SourceSelectDialog` | ❌ 无 |
| 引入 RssSearchActivity | ✅ `import io.legado.app.ui.rss.article.RssSearchActivity` | ❌ 无 |
| 引入 RoundedTagBarView | ✅ | ❌ |
| `showSourceSelector()` | ✅ 调用 `SourceSelectDialog.show()` 统一选择源 | ❌ 无 |
| `openRssSearch()` | ✅ 调用 `RssSearchActivity.start(requireContext(), source.sourceUrl)` | ❌ 无 |
| `openRssLegacy(rssSource)` | ✅ 检查 `rssSource.singleUrl` → `viewModel.getSingleUrl(rssSource) { url -> ... }` → `ReadRssActivity.start()` | ❌ 无 |
| `canRenderInModernPage()` | ✅ 判断源是否支持现代页面渲染 | ❌ 无 |

**关键技术点**（Archive 的 `showSourceSelector`，行 683-702）：
```kotlin
private fun showSourceSelector() {
    if (rssSources.isEmpty()) return
    SourceSelectDialog.show(
        context = requireContext(),
        title = getString(R.string.rss),
        items = rssSources,
        selectedKey = selectedRssSource?.sourceUrl,
        displayName = { it.getDisplayNameGroup() },
        searchTexts = { listOfNotNull(it.sourceName, it.sourceUrl, it.sourceGroup) },
        itemKey = { it.sourceUrl }
    ) {
        if (it.canRenderInModernPage()) {
            selectSource(it, reload = true)
        } else {
            openRssLegacy(it)
        }
    }
}
```

### 3.5 发现页 UI 对比

#### 3.5.1 ExploreFragment.kt 对比

| 维度 | Archive（163 KB） | 本项目（501 行） |
|------|------------------|----------------|
| 文件大小 | 163 KB | 21 KB |
| 整体架构 | 传统 Fragment + Compose ComposeView 双轨 | 纯传统 Fragment |
| 分组模式 | 集成 DiscoverySuite 套件系统 | 文件夹视图 + 标签 TabLayout + 类型分组三模式 |
| Compose 集成 | `binding.composeDiscoverySuite`（ComposeView） | ❌ 无 |
| DiscoverySuite 状态 | `composeSuiteConfig = mutableStateOf(DiscoverySuiteStore.load())` `composeSelectedSuiteId = mutableStateOf(DiscoverySuiteStore.selectedSuiteId())` | ❌ 无 |
| 快照保存恢复 | ✅ `DiscoverySuitePageSnapshotStore`（切换套件保留状态） | ❌ 无 |
| 统一源选择 | ✅ `SourceSelectDialog.show(items = discoverSources, ...)`（行 2057-2073） | ❌ 无 |
| 搜索结果合并 | ✅ `SearchBookMergeUtils.appendReplacing(emptyList/discoverBooks, newBooks)`（行 3411-3418） | ❌ 无 |
| 视图模式切换 | 传统/Compose 双轨切换 | 文件夹/列表/标签/类型多模式切换 |
| 返回键处理 | Compose 与 Fragment 协同 | 子目录返回文件夹列表 |
| WebView 池作用域 | `WebViewPool.Scope.DISCOVERY` | 无作用域区分 |
| 视频预加载 | ✅ `VideoBookPreloader` | ❌ 无（本项目无视频模块） |
| Glide 图片加载 | ✅ RequestOptions + Priority + DecodeFormat | ❌ 简单加载 |
| FlexboxLayout 标签栏 | ✅ | ❌（用 TabLayout 替代） |
| ModernActionPopup | ✅ | ❌ |
| RoundedTagBarView | ✅ | ❌ |
| Compose 对话框 | ✅ 6 种（ActionList/ChoiceList/MultiChoice/Confirm/TextInput/...） | ❌ |

**本项目独有的发现页能力**（500 行内的"小而精"实现）：
- **D1 标签模式**：`sourceGroupStyle != 0 && sourceGroupMode == 0` → TabLayout + 列表
- **D1 文件夹模式**：`sourceGroupStyle != 0 && sourceGroupMode == 1` → GridLayoutManager + 文件夹
- **D2 按类型分组**：`sourceGroupStyle == 1` → Tab 显示类型（文本/音频/图片/文件/视频）
- **D2-补丁2 子目录状态**：`inSubDirectory` 判定文件夹点击后的列表视图
- **F-01 修复**：用 `currentGroup` 解耦 searchView，避免回填 "group:xxx" 污染搜索框
- **6 分支组合查询**：currentType/currentGroup/searchKey 三维组合查询数据库

#### 3.5.2 ExploreModernListScreen.kt（Archive 独有，Compose 现代列表/网格）

**文件路径**：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/ExploreModernListScreen.kt`

**核心实现**：
- `@Composable fun ExploreModernListScreen(books, layoutMode, listItemStyle, topPaddingPx, scrollToTopSignal, isLoading, hasMore, isInBookshelf, onBookClick, onLoadMore, onCanScrollBackwardChanged, fragment, lifecycle, modifier)`
- 双布局：
  - `layoutMode == 3` → `ExploreModernGridScreen`（3 列 LazyVerticalGrid）
  - 其他 → LazyColumn 列表
- 加载更多：`derivedStateOf { lastVisible >= books.lastIndex - 3 }`（列表）或 `lastVisible >= books.lastIndex - 6`（网格）
- 滚动到顶部：`scrollToTopSignal` 信号 + E-Ink 模式适配（`isEInkMode` 用 `scrollToItem` 替代 `animateScrollToItem`）
- 搜索预览：`SearchBookPreviewState` + `SearchBookPreviewOverlay`（长按触发）
- 快速滚动条：`ComposeLazyListFastScroller`
- 加载页脚：`CircularProgressIndicator`（24dp, strokeWidth 2dp）
- 网格项：`ExploreGridBookItem`（封面 + 标题，combinedClickable 长按预览）
- 列表项：`ExploreBookListItem`（复用 `SearchBookListItem`）

#### 3.5.3 DiscoverySuite 系统详解（Archive 独有）

##### DiscoverySuiteConfig.kt（数据模型 + 持久化）

**核心数据类**：
- `DiscoverySuiteConfig(suites: List<DiscoverySuite>)` - 套件列表容器
- `DiscoverySuite(id, name, alias, opacityMultiplier, order, widgets)` - 单套件
  - `displayName`：alias 优先，回退 name
- `DiscoverySuiteWidget(id, type, title, targets, sourceUrls, tagUrls, displayLimit, order)` - 套件内组件
- `DiscoverySuiteWidgetTarget(sourceUrl, tagUrl, title)` - 组件目标
- `DiscoverySuiteWidgetType` 枚举（7 种组件类型）：
  - `RandomBooks("random_books")` - 随机书籍
  - `TagBar("tag_bar")` - 标签栏
  - `RankButtons("rank_buttons")` - 排行按钮
  - `BookList("book_list")` - 书籍列表
  - `HorizontalBooks("horizontal_books")` - 横向书籍
  - `RankedList("ranked_list")` - 排序列表
  - `WaterfallBooks("waterfall_books")` - 瀑布流
- `DiscoverySuiteStore`（持久化与校验）：
  - 存储位置：`SharedPreferences`（PreferKey.discoverySuiteConfig / selectedDiscoverySuiteId）
  - 容量限制：MAX_CONFIG_CHARS = 96KB / MAX_SUITES = 20 / MAX_WIDGETS_PER_SUITE = 50 / MAX_URLS_PER_WIDGET = 30 / MAX_TARGETS_PER_WIDGET = 30
  - 字符限制：MAX_NAME_CHARS = 40 / MAX_TITLE_CHARS = 60 / MAX_ID_CHARS = 64
  - `sanitize()` 方法：清洗 + 去重 + 排序 + 截断
  - `newSuite(name)` / `newBookWidget(title, type)`：工厂方法生成 UUID 前缀 ID

##### DiscoverySuiteHomeScreen.kt（Compose 套件首页）

**核心 Composable**：
- `DiscoverySuiteHomeScreen(selectedSuite, suites, selectedSuiteId, widgetBooks, rankedWidgetBooks, loadingWidgetIds, scrollToTopSignal, onSearchClick, onSuiteClick, onSuiteSelect, onBookClick, onBookPreviewOpen, onTagClick, onRefreshWidget, onHorizontalLoadMore, onRankedLoadMore, onCanScrollBackwardChanged, fragment, lifecycle, modifier)`
- 整体结构：`BoxWithConstraints > Column > DiscoverySuiteSearchBar + LazyColumn`
- 套件为空时显示 `DiscoverySuiteEmptyState`（标题 + 摘要 + 行动按钮 → 跳转管理）
- 每个组件用 `DiscoverySuiteAnimatedWidgetContainer` 包装（淡入动画 + Y 轴位移）
- 动画：`Animatable` + `CubicBezierEasing(0.20f, 0.00f, 0.00f, 1.00f)`（260ms tween）
- E-Ink 模式：直接 `snapTo(1f)` 无动画
- 透明度乘数：`opacityMultiplier = selectedSuite?.opacityMultiplier ?: 1f`（1-4 倍）
- 预览覆盖层：`SearchBookPreviewOverlay`
- 加载更多：`onHorizontalLoadMore` / `onRankedLoadMore` 回调

##### DiscoverySuiteManageActivity.kt（套件管理 Activity）

**核心结构**：
- `class DiscoverySuiteManageActivity : BaseActivity<ActivityThemeManageBinding>`
- `screenModeState: DiscoverySuiteManageMode`（sealed class 三态）：
  - `List` - 套件列表
  - `Detail(suiteId)` - 套件详情
  - `WidgetEditor(suiteId, widgetId?)` - 组件编辑
- 状态变量：`configState` / `selectedSuiteIdState` / `sourceTagOptionsState` / `loadingTagsState` / `loadingSourceTagUrlsState` / `loadedSourceTagUrlsState`
- 菜单：根据 screenModeState 显示不同菜单（List 显示"创建套件"，Detail 显示"添加组件"）
- ComposeView 嵌入：`binding.recyclerView` 被替换为 ComposeView
- 数据类：
  - `DiscoverySuiteSourceTagOptions(sourceUrl, tagOptions)` - 源标签选项
  - `DiscoverySuiteTagOption(tagUrl, title)` - 单个标签选项
- 拖拽排序：`rememberReorderableLazyListState`（sh.calvin.reorderable 库）
- UI 组件：`AppManagementListRow` / `AppManagementMoreActionButton` / `LegadoComposeTheme`

##### DiscoverTagAdapter.kt（发现标签 Adapter）

**核心数据类**：
- `DiscoverTagItem` - 发现标签项
- `Role` 枚举：`UrlTag` 等（标签角色，区分 URL 标签和其他类型）

---

## 4. Archive RSS/发现页增强功能详解

### 4.1 统一源选择

**具体实现**：泛型 `<T>` 单选对话框，可接受任意类型的源（书源/RSS 源）。

**代码位置**：
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/widget/SourceSelectDialog.kt`（268 行）

**技术方案**：
- 泛型 API：`fun <T> show(context, title, items, selectedKey, displayName: (T) -> String, searchTexts: (T) -> List<String>, itemKey: (T) -> String, showTitle, onSelect: (T) -> Unit)`
- 底层：`ComponentDialog` + `ComposeView`
- UI 组件：`LegadoMiuixCard` + `LegadoMiuixChoiceRow` + `OutlinedTextField`（搜索过滤）+ `LazyColumn`
- 高度自适应：基于屏幕高度 + IME 高度计算 `maxPanelHeight`（最大 420dp）和 `listMaxHeight`（72-260dp）
- 宽度：`minOf(windowWidth * 0.94f, 520.dpToPx())`
- key 稳定性：`stableSourceSelectKey(rawKey, index)` = `"$rawKey#$index"`

**使用场景**（两处）：
1. **ExploreFragment.kt 行 2057-2073**：`showDiscoverSourceMenu()` —— 发现页选择书源
   ```kotlin
   SourceSelectDialog.show(
       items = discoverSources,
       selectedKey = selectedDiscoverSourcePart?.bookSourceUrl,
       displayName = { it.getDisPlayNameGroup() },
       searchTexts = { listOfNotNull(it.bookSourceName, it.bookSourceUrl, it.bookSourceGroup) },
       itemKey = { it.bookSourceUrl },
       showTitle = false
   ) { selectDiscoverSource(it) }
   ```
2. **RssFragment.kt 行 683-702**：`showSourceSelector()` —— 订阅页选择 RSS 源
   ```kotlin
   SourceSelectDialog.show(
       items = rssSources,
       selectedKey = selectedRssSource?.sourceUrl,
       displayName = { it.getDisplayNameGroup() },
       searchTexts = { listOfNotNull(it.sourceName, it.sourceUrl, it.sourceGroup) },
       itemKey = { it.sourceUrl }
   ) {
       if (it.canRenderInModernPage()) selectSource(it, reload = true)
       else openRssLegacy(it)
   }
   ```

**关键意义**：
- 这是一个**通用组件**，统一了书源和 RSS 源的选择交互
- 替代了原本可能各自实现的弹窗，降低维护成本
- 支持 `searchTexts: (T) -> List<String>` 多字段搜索（如同时匹配名称/URL/分组）

### 4.2 订阅内容搜索

**具体实现**：独立的 `RssSearchActivity`，用 RSS 源的 `searchUrl` 字段作为搜索 URL 模板。

**代码位置**：
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss.article/RssSearchActivity.kt`（104 行）
- 入口：`RssFragment.kt` 行 733-737 `openRssSearch()`

**技术方案**：
- 入口：`companion object { fun start(context, sourceUrl, key? = null) }`
- 流程：
  1. `viewModel.initData(intent)` 加载 RssSource
  2. 校验 `source.searchUrl.isNullOrBlank()`，为空则 `toastOnUi(R.string.rss_source_empty)` + `finish()`
  3. 有初始 key 直接 `submitSearch(key)`，否则弹出输入法等待用户输入
  4. `submitSearch(key)`：`viewModel.searchKey = key` → `binding.titleBar.title = key` → `RssArticlesFragment(getString(R.string.search), searchUrl, key)` 替换 Fragment
- 复用现有 RssSortViewModel（两边一致，无需改造）
- 复用 RssArticlesFragment（与排序页同一 Fragment）

**关键意义**：
- 本项目 RssSource 也有 `searchUrl` 字段（行 115），但**没有任何 Activity 使用它**！这是"数据模型已就绪但 UI 入口缺失"
- Archive 通过新增 RssSearchActivity，激活了 searchUrl 字段的能力

### 4.3 纯 URL 订阅源

**具体实现**：通过 `RssSortActivity` 的 `pureSearch: Boolean` Intent 参数区分纯 URL 模式与规则模式。

**代码位置**：
- 入口签名：`RssSortActivity.kt` 行 510-525
  ```kotlin
  fun start(
      context: Context,
      sortUrl: String?,
      sourceUrl: String,
      key: String? = null,
      focusSearch: Boolean = false,
      pureSearch: Boolean = false   // Archive 独有参数
  )
  ```
- 状态字段：`RssSortActivity.kt` 行 57 `private var pureSearch = false`
- Intent 读取：行 217 `pureSearch = intent.getBooleanExtra("pureSearch", false)` 和 行 226

**pureSearch 模式行为**：
1. **返回键处理**（行 237-240）：直接 `finish()`，不进入搜索退出逻辑
2. **菜单显示**（行 286-297）：隐藏以下不适用纯 URL 源的菜单：
   - `R.id.menu_login` - 登录（纯 URL 源不需要登录）
   - `R.id.menu_refresh_sort` - 刷新分类
   - `R.id.menu_set_source_variable` - 设置源变量
   - `R.id.menu_edit_source` - 编辑源
   - 其他相关菜单项
3. **递归调用**（行 311）：再次启动时传递 `pureSearch = pureSearch` 保持状态

**"纯 URL 订阅源"识别**：
- 两边都使用 `RssSource.singleUrl: Boolean = false` 字段（两边 RssSource 实体行 51）
- `RssFragment.kt` 行 750-759 `openRssLegacy(rssSource)` 中检查 `if (rssSource.singleUrl)` → 调用 `viewModel.getSingleUrl(rssSource) { url -> ReadRssActivity.start(...) }` 直接进入阅读视图
- 当 singleUrl=true 时，源只有一个 URL，不需要规则解析，走 `RssParserDefault`（默认 XML 解析器）

**关键意义**：
- 两边都有 `singleUrl` 字段，但 Archive 在 RssSortActivity 中引入 `pureSearch` 参数提供了"纯 URL 模式"的 UI 行为定制
- 本项目没有 `pureSearch` 参数，所以纯 URL 源在 RssSortActivity 中显示与规则源完全一致的菜单，可能让用户看到不适用的选项（如"编辑源"对纯 URL 源无意义）

### 4.4 合并入口

**具体实现**：通过 `SearchBookMergeUtils` 工具类合并多个来源的 SearchBook 数据，去重并合并字段。

**代码位置**：
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/utils/SearchBookMergeUtils.kt`（91 行）
- 调用点：`ExploreFragment.kt` 行 3411-3418

**技术方案**：
- `appendReplacing(current, incoming)` - 追加合并：current 优先，incoming 替换同 key 项
- `prependReplacing(current, incoming)` - 前插合并：incoming 优先
- `mergeSearchBook(old, new)` - 合并两本书的字段（origin/name/author/coverUrl/intro/wordCount/latestChapterTitle/tocUrl/variable/chapterWordCountText/chapterWordCount/respondTime）
- `stableSearchBookKey()` - 稳定 key 计算（bookUrl 优先 → name+author → coverUrl → time 兜底）
- `origins` 合并：用 `linkedSetOf<String>` 收集两本书的所有 origin，合并到 merged.origins

**调用场景**（ExploreFragment.kt 行 3411-3418）：
```kotlin
val mergedBooks = if (reset) {
    SearchBookMergeUtils.appendReplacing(emptyList(), newBooks)
} else {
    SearchBookMergeUtils.appendReplacing(discoverBooks, newBooks)
}
val hasNewBooks = if (reset) mergedBooks.isNotEmpty() else mergedBooks.size > oldSize
discoverBooks.clear()
discoverBooks.addAll(mergedBooks)
```

**关键意义**：
- 解决了多源发现时同本书被重复展示的问题
- 同本书的不同源数据被合并（如 A 源有封面但无简介，B 源有简介但无封面，合并后两字段都有）
- 多个 origin 被收集到 `origins` 字段，便于后续多源切换

---

## 5. 差异清单（编号化）

| # | 差异点 | Archive 实现 | 本项目实现 | 影响等级 |
|---|--------|-------------|-----------|---------|
| RSS-001 | RssSource.parseConcurrency 字段 | ❌ 无 | ✅ Int = 0（解析并发数） | 中 |
| RSS-002 | RssSource.weight 字段 | ❌ 无 | ✅ Int = 0（权重排序） | 中 |
| RSS-003 | RssSource.lastHost 字段 | ❌ 无 | ✅ String?（域名回填，UI 分组） | 高 |
| RSS-004 | RssSource.hasGroup/removeInvalidGroups 方法 | ❌ 无 | ✅ 失效分组管理 | 中 |
| RSS-005 | RssSource.cacheFirst 默认值 | false | true | 低 |
| RSS-006 | RssParserByRule 解析方式 | 串行 for 循环 | 并行 async + Semaphore 限流 | 高 |
| RSS-007 | RssParserByRule 失败处理 | 抛异常中断 | try-catch 单项失败返回 null | 高 |
| RSS-008 | RssParserByRule AnalyzeRule 实例 | 单实例共享 | 每项独立实例（线程安全） | 高 |
| RSS-009 | Rss.getArticles 函数签名 | 含 webViewPoolScope | 不含 | 中 |
| RSS-010 | Rss lastHost 回填 | ❌ 无 | ✅ SourceLastHostHelper.fillBack | 高 |
| RSS-011 | Rss F-P1-F 预连接 | ❌ 无 | ✅ 前 3 篇 HEAD 预连接 | 高 |
| RSS-012 | RssParserDefault 实现 | 标准 XML 解析 | **完全一致**（150 行逐字符相同） | - |
| RSS-013 | RssSearchActivity（订阅内容搜索） | ✅ 独有 | ❌ 无 | 高 |
| RSS-014 | RssSourceScreen（Compose 列表） | ✅ 独有 | ❌ 无 | 中 |
| RSS-015 | RuleSubScreen/RuleSubEditComposeDialog | ✅ Compose | ❌ 用 RuleSubAdapter 传统 | 低 |
| RSS-016 | SourceSelectDialog（统一源选择） | ✅ 泛型 Compose | ❌ 无 | 高 |
| RSS-017 | SearchBookMergeUtils（合并入口） | ✅ 独有 | ❌ 无 | 高 |
| RSS-018 | ExploreFragment Compose 集成 | ✅ composeDiscoverySuite ComposeView | ❌ 纯传统 | 高 |
| RSS-019 | DiscoverySuite 系统套件 | ✅ 4 文件独有 | ❌ 无 | 高 |
| RSS-020 | DiscoverySuiteWidgetType 7 种组件 | ✅ RandomBooks/TagBar/RankButtons/BookList/HorizontalBooks/RankedList/WaterfallBooks | ❌ 无 | 高 |
| RSS-021 | ExploreModernListScreen（Compose 列表/网格） | ✅ 独有 | ❌ 无 | 中 |
| RSS-022 | DiscoverTagAdapter（发现标签 Adapter） | ✅ 独有 | ❌ 无 | 低 |
| RSS-023 | ExploreFragment 文件夹视图 | ❌ 无 | ✅ GridLayoutManager + SourceFolderAdapter | 中 |
| RSS-024 | ExploreFragment 标签 TabLayout | ❌ 无 | ✅ TabLayout + tabSelectedListener | 中 |
| RSS-025 | ExploreFragment 按类型分组 | ❌ 无 | ✅ sourceGroupStyle == 1（文本/音频/图片/文件/视频） | 中 |
| RSS-026 | ExploreFragment 6 分支组合查询 | ❌ 无 | ✅ currentType + currentGroup + searchKey | 中 |
| RSS-027 | RssSortActivity pureSearch 参数 | ✅ 独有 | ❌ 无 | 中 |
| RSS-028 | RssSortActivity focusSearch 参数 | ✅ 独有 | ❌ 无 | 低 |
| RSS-029 | RssFragment canRenderInModernPage 判断 | ✅ 独有 | ❌ 无 | 中 |
| RSS-030 | DiscoverySuiteStore 容量限制 | ✅ 96KB/20 suites/50 widgets | ❌ 无 | 低 |
| RSS-031 | DiscoverySuitePageSnapshotStore | ✅ 套件状态快照保存/恢复 | ❌ 无 | 中 |
| RSS-032 | WebViewPool.Scope.DISCOVERY | ✅ 发现页专用 WebView 池 | ❌ 无 | 低 |
| RSS-033 | RssRoute/RssEpisode 实体（播客） | ❌ 无 | ✅ 独有 | 中 |
| RSS-034 | ExploreFragment 视频预加载 VideoBookPreloader | ✅（依赖视频模块） | ❌ 无 | 低 |
| RSS-035 | ExploreFragment Glide 高级配置 | ✅ Priority + DecodeFormat + RequestOptions | ❌ 简单加载 | 低 |

---

## 6. 借鉴决策（三态：借鉴/不借鉴/待评估）

### 6.1 建议借鉴（Borrow）

| # | 项目 | 收益评分(1-5) | 风险评分(1-5) | 实施复杂度 | 优先级 | 源码依据 |
|---|------|-------------|-------------|-----------|--------|---------|
| BR-001 | RssSearchActivity（订阅内容搜索） | 5 | 2 | 低（仅新增 1 个 Activity，复用现有 RssSortViewModel + RssArticlesFragment） | P0 高 | RSS-013；本项目 RssSource.searchUrl 字段已就绪但无 UI 入口使用（行 115） |
| BR-002 | SourceSelectDialog（统一源选择对话框） | 5 | 3 | 中（需迁移 268 行 + LegadoMiuixCard/LegadoMiuixChoiceRow Compose 组件 + rememberAppDialogStyle） | P0 高 | RSS-016；Archive ui/widget/SourceSelectDialog.kt 全文；ExploreFragment 行 2057-2073 和 RssFragment 行 683-702 双调用点 |
| BR-003 | SearchBookMergeUtils（搜索结果合并） | 5 | 2 | 低（91 行独立工具类，仅依赖 SearchBook 实体） | P0 高 | RSS-017；utils/SearchBookMergeUtils.kt 全文；调用点 ExploreFragment 行 3411-3418 |
| BR-004 | RssSortActivity pureSearch 参数 | 4 | 2 | 低（仅需扩展 start 函数签名 + 增加 pureSearch 状态 + 菜单隐藏逻辑） | P1 中 | RSS-027；RssSortActivity.kt 行 57/217/226/237/286/311 |
| BR-005 | RssFragment openRssSearch() 入口 | 4 | 2 | 低（仅 5 行代码 + 菜单项配置） | P1 中 | RssFragment.kt 行 733-737 |
| BR-006 | ExploreModernListScreen（Compose 现代列表/网格） | 3 | 4 | 高（396 行 Compose 代码 + 依赖 BookshelfListRenderConfig + SearchBookPreviewOverlay + ComposeLazyListFastScroller + BookCoverImage） | P2 低 | RSS-021；ui.main.explore/ExploreModernListScreen.kt 全文 |

**BR-001~003 高优先级理由**：
- BR-001：本项目 RssSource 已有 `searchUrl` 字段（行 115）但无 UI 入口，这是已就绪能力被浪费，借鉴后立竿见影
- BR-002：解决书源/RSS 源选择体验割裂问题，统一交互范式
- BR-003：解决多源发现时同本书重复展示问题，提升数据质量

### 6.2 不建议借鉴（Skip）

| # | 项目 | 不借鉴理由 |
|---|------|-----------|
| SK-001 | DiscoverySuite 套件系统（4 文件，约 130KB） | 1. 体量过大（DiscoverySuiteManageActivity 77KB + HomeScreen 51KB）；2. 套件概念引入会改变用户使用习惯；3. 套件配置 96KB 上限对 SharedPreferences 不友好；4. 本项目"文件夹/标签/类型三模式"已能覆盖大部分发现页需求；5. 7 种 WidgetType 需要全部 UI 配套，工作量大；6. 与本项目"极简≠残缺"哲学冲突 |
| SK-002 | ExploreFragment 的 Compose 集成（composeDiscoverySuite ComposeView） | 1. 引入双轨 UI 增加维护成本；2. 本项目发现页 501 行已足够清晰；3. Archive ExploreFragment 163KB 体量过大，不易维护；4. Compose 与传统 View 混用容易引入状态同步 Bug |
| SK-003 | ExploreFragment 视频预加载（VideoBookPreloader） | 本项目无视频模块，借鉴后无用武之地 |
| SK-004 | Glide 高级配置（Priority + DecodeFormat + RequestOptions） | 本项目无视频/瀑布流场景，简单加载已足够 |
| SK-005 | WebViewPool.Scope.DISCOVERY 作用域 | 本项目 WebView 池设计不同，借鉴需先评估兼容性 |
| SK-006 | RssSourceScreen（Compose RSS 源列表） | 本项目已有 RssSourceAdapter/Grid/Compact 三种 Adapter 覆盖，无需 Compose 重写 |
| SK-007 | RuleSubScreen/RuleSubEditComposeDialog（Compose 规则订阅） | 规则订阅使用频率低，传统 Adapter 已足够，借鉴收益低 |
| SK-008 | DiscoverTagAdapter（发现标签 Adapter） | 仅 466 行，作用单一，与 DiscoverySuite 套件绑定，单独借鉴无意义 |

### 6.3 待评估（Evaluate）

| # | 项目 | 待评估理由 |
|---|------|-----------|
| EV-001 | DiscoverySuiteConfig 数据模型（仅模型，不含 UI） | 数据模型设计优秀（容量限制 + sanitize 校验），可借鉴用于其他需要 JSON 配置的场景；但需评估是否与本项目现有 SourceFolderAdapter 配置机制冲突 |
| EV-002 | Rss.kt 的 webViewPoolScope 参数 | Archive 引入 WebView 池作用域隔离发现页与订阅页，但本项目 WebView 池设计可能不同；需先调研本项目 WebViewPool 实现 |
| EV-003 | RssSortActivity focusSearch 参数 | 控制搜索框自动聚焦，对小屏设备体验有帮助；但本项目未引入，需评估是否与现有 RssSortViewModel 兼容 |
| EV-004 | ExploreFragment 的 FlexboxLayout 标签栏 | Archive 用 FlexboxLayout 实现流式标签，比 TabLayout 灵活；本项目用 TabLayout 已实现标签切换，需评估是否值得替换 |
| EV-005 | ExploreModernListScreen 的 SearchBookPreviewOverlay（长按预览） | 长按预览是良好交互，但需先评估本项目是否有同等 Compose 组件支撑 |
| EV-006 | RssSource.cacheFirst 默认值（false vs true） | 两边默认值不同，需评估哪个更符合本项目使用习惯；Archive 默认 false（每次都请求网络），本项目默认 true（优先缓存） |
| EV-007 | DiscoverySuitePageSnapshotStore（套件状态快照） | 切换套件时保留状态是良好体验，但本项目无套件系统，单独借鉴意义不大 |

---

## 7. 重大发现

### 7.1 数据模型已就绪但 UI 入口缺失（关键发现）

**发现**：本项目 RssSource 实体已经有 `searchUrl: String? = null` 字段（行 115），但**本项目没有任何 Activity/Fragment 使用这个字段**。

**对比**：
- Archive 通过新增 `RssSearchActivity.kt`（104 行）激活了 searchUrl 字段的能力
- Archive 的 RssFragment.kt 行 733-737 通过 `openRssSearch()` 调用 `RssSearchActivity.start(requireContext(), source.sourceUrl)`
- Archive 的 RssSortActivity.kt 行 280-298（本项目对应行 280-298）通过菜单 `menu_search` 触发搜索

**借鉴建议**：BR-001 + BR-005，**优先级 P0**。仅需新增 1 个 RssSearchActivity + RssFragment 5 行入口代码，即可激活已就绪能力，投入产出比极高。

### 7.2 两边走不同优化方向（架构哲学差异）

**发现**：Archive 与本项目在 RSS/发现页上走的是**完全不同的优化方向**。

| 方向 | Archive | 本项目 |
|------|---------|--------|
| **核心目标** | 提升"用户体验广度"（更多入口、更丰富 UI） | 提升"性能与稳定性"（更快、更稳） |
| **UI 策略** | Compose 现代化（DiscoverySuite + ExploreModernListScreen） | 传统 View + 多模式（文件夹/标签/类型） |
| **数据策略** | 单源解析串行（简单可靠） | 并行解析 + 限流（性能优先） |
| **网络策略** | WebView 池作用域隔离 | lastHost 回填 + 预连接（点击性能优化） |
| **校验策略** | 无 | weight + 失效分组管理（hasGroup/removeInvalidGroups） |
| **集成策略** | 统一选择对话框 + 合并入口（数据合并） | 6 分支组合查询（数据库侧过滤） |

**意义**：
- Archive 的 DiscoverySuite 系统（130KB+ 代码）虽然功能丰富，但与本项目"极简≠残缺"哲学冲突
- 本项目的并行解析 + lastHost 回填 + 失效分组管理等优化是 Archive 没有的，**这些是本项目的优势，不应丢失**
- 借鉴时应有选择性：**借鉴用户感知度高的功能（订阅搜索、统一选择、结果合并），不借鉴体量大但收益分散的功能（DiscoverySuite 系列）**

### 7.3 RssParserDefault 完全一致（成本最低的共识）

**发现**：两边 `RssParserDefault.kt` 150 行代码**逐字符完全相同**。

**意义**：
- 两边都保留了原版 RSS 2.0 XML 标准解析器作为兜底
- 当 `ruleArticles` 为空时，自动走 `RssParserDefault.parseXML()`（两边 RssParserByRule 行 41 一致）
- 这意味着**两边在 RSS 标准解析上有共识**，借鉴时无需考虑这部分

### 7.4 RssSortViewModel 完全一致（ViewModel 无需改造）

**发现**：两边 `RssSortViewModel.kt` 95 行代码**完全一致**。

**意义**：
- Archive 在引入 RssSearchActivity 时，**没有改造 RssSortViewModel**
- 仅通过新 Activity 调用现有 ViewModel 的 `initData` 和 `searchKey` 字段
- 这降低了 BR-001 的实施风险：**新增 Activity 不需要修改任何 ViewModel 代码**

---

## 8. 引用源码位置

### 8.1 Archive 侧

| 引用对象 | 文件路径 | 行号 |
|---------|---------|------|
| RssSource 实体 | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 16-116 |
| RssSource.equal 方法 | 同上 | 128-175 |
| RssParserByRule 串行实现 | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 74-83 |
| RssParserDefault | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/rss/RssParserDefault.kt` | 全文 |
| Rss.getArticles 签名（含 webViewPoolScope） | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/rss/Rss.kt` | 22-35 |
| RssSearchActivity | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss.article/RssSearchActivity.kt` | 全文 104 行 |
| SourceSelectDialog | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.widget/SourceSelectDialog.kt` | 全文 268 行 |
| SearchBookMergeUtils | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app.utils/SearchBookMergeUtils.kt` | 全文 91 行 |
| ExploreFragment 调用 SourceSelectDialog | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/ExploreFragment.kt` | 2057-2073 |
| ExploreFragment 调用 SearchBookMergeUtils | 同上 | 3411-3418 |
| ExploreFragment ComposeView 集成 | 同上 | 211-212, 311-330 |
| RssFragment 调用 SourceSelectDialog | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.rss/RssFragment.kt` | 683-702 |
| RssFragment 调用 RssSearchActivity | 同上 | 733-737 |
| RssFragment openRssLegacy（singleUrl 处理） | 同上 | 750-759 |
| RssSortActivity pureSearch 参数 | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.rss.article/RssSortActivity.kt` | 57, 217, 226, 237, 286-297, 311, 510-525 |
| DiscoverySuiteConfig | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteConfig.kt` | 全文 228 行 |
| DiscoverySuiteHomeScreen | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteHomeScreen.kt` | 81-217 |
| DiscoverySuiteManageActivity | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/DiscoverySuiteManageActivity.kt` | 105-200 |
| ExploreModernListScreen | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/ExploreModernListScreen.kt` | 全文 396 行 |
| DiscoverTagAdapter | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.main.explore/DiscoverTagAdapter.kt` | 5, 11-12 |
| RssSourceScreen | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceScreen.kt` | 32-80 |
| RuleSubScreen | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubScreen.kt` | 全文 |
| RuleSubEditComposeDialog | `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubEditComposeDialog.kt` | 全文 |

### 8.2 本项目侧

| 引用对象 | 文件路径 | 行号 |
|---------|---------|------|
| RssSource 实体（多 parseConcurrency/weight/lastHost） | `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 16-124 |
| RssSource.equal 方法（含 parseConcurrency/weight） | 同上 | 145-185 |
| RssSource.hasGroup/removeInvalidGroups | 同上 | 220-239 |
| RssParserByRule 并行实现 | `app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 82-121 |
| RssParserByRule 单项失败处理 | 同上 | 103-111 |
| Rss.getArticles 签名（无 webViewPoolScope） | `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 26-38 |
| Rss lastHost 回填 | 同上 | 59, 131 |
| Rss F-P1-F 预连接 | 同上 | 88-101 |
| RssSource.searchUrl 字段（无 UI 入口使用） | `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 115 |
| RssSortActivity.start（无 pureSearch/focusSearch） | `app/src/main/java/io/legado/app/ui.rss.article/RssSortActivity.kt` | 481-487 |
| ExploreFragment 文件夹/标签/类型三模式 | `app/src/main/java/io/legado/app/ui.main.explore/ExploreFragment.kt` | 74-93 |
| ExploreFragment 6 分支组合查询 | 同上 | 345-387 |
| ExploreFragment 标签 TabLayout | 同上 | 218-254 |
| ExploreFragment 文件夹视图 | 同上 | 208-216, 274-300 |
| ExploreFragment 子目录返回键 | 同上 | 134-156 |
| RssRoute 实体 | `app/src/main/java/io/legado/app/data/entities/RssRoute.kt` | 全文 |
| RssEpisode 实体 | `app/src/main/java/io/legado/app/data/entities/RssEpisode.kt` | 全文 |
| RssSourceAdapterCompact | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterCompact.kt` | 全文 |
| RssSourceSort | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceSort.kt` | 全文 |
| RssSourceAdapterGrid | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterGrid.kt` | 全文 |
| RuleSubAdapter | `app/src/main/java/io/legado/app/ui.rss.subscription/RuleSubAdapter.kt` | 全文 |
| RssFragment（无 SourceSelectDialog/RssSearchActivity 集成） | `app/src/main/java/io/legado/app/ui.main.rss/RssFragment.kt` | 全文 |
| RssSortViewModel（与 Archive 完全一致） | `app/src/main/java/io/legado/app/ui.rss.article/RssSortViewModel.kt` | 全文 95 行 |
| RssParserDefault（与 Archive 完全一致） | `app/src/main/java/io/legado/app/model/rss/RssParserDefault.kt` | 全文 150 行 |

---

## 9. 总结

### 9.1 核心结论

1. **两边走不同优化方向**：Archive 重视"用户体验广度"（订阅搜索、统一选择、合并入口、发现套件），本项目重视"性能与稳定性"（并行解析、lastHost 回填、预连接、失效分组管理）
2. **Archive 的 DiscoverySuite 系统体量过大**（130KB+），与本项目"极简≠残缺"哲学冲突，不建议整体借鉴
3. **Archive 的 BR-001/002/003 三项是高收益低风险借鉴**：本项目数据模型已就绪但 UI 入口缺失，激活后立竿见影
4. **两边 RssParserDefault 和 RssSortViewModel 完全一致**：借鉴时无需修改这部分
5. **本项目的并行解析是优势能力**：Archive 没有此优化，本项目应保持

### 9.2 借鉴决策汇总

- **建议借鉴（Borrow）**：6 项（BR-001~006）
  - P0 高优先级：3 项（BR-001 RssSearchActivity、BR-002 SourceSelectDialog、BR-003 SearchBookMergeUtils）
  - P1 中优先级：2 项（BR-004 pureSearch 参数、BR-005 RssFragment openRssSearch 入口）
  - P2 低优先级：1 项（BR-006 ExploreModernListScreen Compose 列表/网格）

- **不建议借鉴（Skip）**：8 项（SK-001~008）
  - 主要集中在 DiscoverySuite 系列、Compose 双轨集成、视频预加载等大体量或与本项目哲学冲突的功能

- **待评估（Evaluate）**：7 项（EV-001~007）
  - 主要集中在数据模型借鉴、WebView 池作用域、FlexboxLayout 替代等需要进一步调研的项目

### 9.3 风险提示

1. **BR-002 SourceSelectDialog 风险评估**：需要先迁移 LegadoMiuixCard、LegadoMiuixChoiceRow、rememberAppDialogStyle、toMiuixPalette 等 Compose 组件，依赖较深
2. **BR-003 SearchBookMergeUtils 风险评估**：需要 SearchBook 实体支持 `stableSearchBookKey()` 扩展函数，需评估与本项目 SearchBook 实体的兼容性
3. **BR-006 ExploreModernListScreen 风险评估**：依赖 BookshelfListRenderConfig、SearchBookPreviewOverlay、ComposeLazyListFastScroller、BookCoverImage 等 Compose 组件，需要先评估本项目 Compose 基础设施完备度
