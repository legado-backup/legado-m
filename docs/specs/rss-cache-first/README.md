# RSS 阅读源缓存优先加载 - 功能说明

> 状态：✅ 已实施（待真机验证）
>
> 最后更新：2026-07-08

## 功能概述

针对用户反馈「每次进入阅读源列表页和 webview 页都像新加载网络资源、没有先读本地缓存」的问题，调整 RSS 子系统两处缓存策略，使界面进入时优先展示本地缓存，再后台刷新网络数据，提升首屏可见速度与体感流畅度。

## 问题根因（已源码核实）

### 列表页 `RssArticlesFragment.kt`

- L73：`private var fullRefresh = true`，初始即为「全量刷新」。
- L217-222 / L224-229：`loadArticles()` / `loadArticles(targetPage)` 内部强制 `fullRefresh = true`。
- L128-130：下拉刷新监听调用 `loadArticles()`。
- L149-163：`initView()` 在预加载或 `RESUMED` 时调用 `loadArticles()`，导致每次进入页面都触发网络加载并标记全量刷新。
- L173：`if (!isResumed || fullRefresh || newList.isEmpty())` 命中即 `adapter.setItems(newList)` 全量替换，跳过 DiffUtil 增量更新。

结果：即使数据库已有缓存（`flowByOriginSort` 已发出），网络回来后仍走全量替换，丢失增量更新体验。

### webview 页 `ReadRssActivity.kt`

- L421：`cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT`。
- `RssSource.kt` L112-113：`@ColumnInfo(defaultValue = "0") var cacheFirst: Boolean = false`，默认关闭缓存优先。

结果：webview 默认走 `LOAD_DEFAULT`（网络优先），无缓存命中优势。

## 核心能力

1. **列表页缓存优先 + 网络后台刷新**
   - 首次进入页面立即用本地缓存渲染（DiffUtil 增量更新）
   - 同时发起网络请求，数据回来后增量合并
   - 下拉刷新保留全量替换语义
   - 翻页（切换页码）保留全量替换语义
2. **webview 缓存优先**
   - `RssSource.cacheFirst` 默认值改为 `true`
   - webview 默认 `LOAD_CACHE_ELSE_NETWORK`，缓存命中时秒开
   - 保留「刷新」菜单（`menu_rss_refresh`）供用户主动拉取最新内容
3. **网络失败降级**
   - 列表页网络失败时保留已显示的缓存，仅提示错误（现有 `loadErrorLiveData` 机制）
   - webview 网络失败时由 `LOAD_CACHE_ELSE_NETWORK` 自动回退缓存
4. **保留手动刷新能力**
   - 列表页下拉刷新
   - webview 顶部菜单「刷新」

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明书：Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：Technical Approach / ADR Y-Statement / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 实施任务清单（`- [ ] X.Y` 格式） + AOAdapt 日志占位 |

## 关键文件

| 文件 | 角色 |
|------|------|
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt` | 列表页，`fullRefresh` 逻辑调整 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt` | 网络加载逻辑（无需改） |
| `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt` | webview 页，L421 `cacheMode`（无需改逻辑，依赖字段默认值） |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | L113 `cacheFirst` 默认值 |
| `app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt` | 本地缓存接口 `flowByOriginSort`（无需改） |

## 非目标

- 不改动 RSS 网络抓取与解析逻辑（`Rss.getArticles`、`ruleArticles` 等）
- 不引入新的缓存存储介质（沿用 Room `rssArticles` 表与 WebView HTTP 缓存）
- 不实现 webview「先缓存秒开 + 后台静默网络刷新」的混合策略（标准 WebView 缓存模式不直接支持，详见 design.md ADR-2）
