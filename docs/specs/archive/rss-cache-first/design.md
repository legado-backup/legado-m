# RSS 阅读源缓存优先加载 - 技术设计文档

> 状态：🔄 设计中

## Technical Approach

### 总体方案

两处独立改动，互不依赖：

```
┌─────────────────────────────────────────────────────────────┐
│  改动 1：列表页 fullRefresh 逻辑调整                          │
│  RssArticlesFragment.kt                                       │
│  ─ fullRefresh 初始值 true → false                            │
│  ─ loadArticles() 拆分为带参版本，区分刷新路径                │
│  ─ 首次进入/后台刷新：fullRefresh=false（DiffUtil 增量）       │
│  ─ 下拉刷新/翻页：fullRefresh=true（全量替换）                 │
├─────────────────────────────────────────────────────────────┤
│  改动 2：webview cacheFirst 默认值                            │
│  RssSource.kt L113                                            │
│  ─ cacheFirst 默认值 false → true                             │
│  ─ ReadRssActivity.kt L421 逻辑不变（已依赖该字段）            │
│  ─ cacheFirst=true → LOAD_CACHE_ELSE_NETWORK（缓存优先）       │
└─────────────────────────────────────────────────────────────┘
```

### 改动 1：列表页 fullRefresh 逻辑

#### 现状分析（已核实源码）

`RssArticlesFragment.kt`：

- L73：`private var fullRefresh = true`
- L128-130：下拉刷新 → `loadArticles()`
- L149-163：`initView()` 在 `isPreload` 或 `RESUMED` 时 → `loadArticles()`
- L173：`if (!isResumed || fullRefresh || newList.isEmpty())` → `setItems` 全量替换；否则 DiffUtil
- L217-222：`loadArticles()` 设 `fullRefresh = true`
- L224-229：`loadArticles(targetPage)` 设 `fullRefresh = true`
- L248-252：`showPagePicker` 选页后设 `fullRefresh = true` 再 `loadArticles(targetPage)`
- L257：`scrollToBottom` 设 `fullRefresh = false`（加载更多走 append，不全量）
- L282：`readRss` 设 `fullRefresh = false`（阅读返回走 DiffUtil 更新已读状态）

#### 目标行为映射

| 调用点 | 当前 `fullRefresh` | 目标 `fullRefresh` | 说明 |
|--------|-------------------|-------------------|------|
| 初始值（L73） | true | **false** | 首次缓存发出即走 DiffUtil |
| `initView` 首次进入（L149-163） | 调用 loadArticles → true | 调用 loadArticles → **false** | 后台刷新，增量合并 |
| 下拉刷新（L128-130） | 调用 loadArticles → true | 调用 loadArticles → **true** | 保留全量替换 |
| 翻页 `loadArticles(targetPage)`（L224-229） | true | **true** | 保留全量替换 |
| `showPagePicker` 选页（L248-252） | true | **true** | 保留全量替换 |
| `scrollToBottom` 加载更多（L257） | false | **false** | 不变 |
| `readRss` 阅读返回（L282） | false | **false** | 不变 |

#### 实现方案

将 `loadArticles()` 与 `loadArticles(targetPage)` 改为带 `fullRefresh` 参数，默认 `false`；下拉刷新与翻页显式传 `true`。

```kotlin
// L73：初始值改为 false
private var fullRefresh = false

// L128-130：下拉刷新显式传 true
refreshLayout.setOnRefreshListener {
    loadArticles(fullRefresh = true)
}

// L149-163：首次进入用默认 false
//   isPreload 分支：loadArticles()
//   RESUMED 分支：loadArticles()
//   （均不传参，走默认 false）

// L217-222：带参版本
private fun loadArticles(fullRefresh: Boolean = false) {
    this.fullRefresh = fullRefresh
    activityViewModel.rssSource?.let {
        viewModel.loadArticles(it)
    }
}

// L224-229：翻页固定 true
private fun loadArticles(targetPage: Int) {
    fullRefresh = true
    activityViewModel.rssSource?.let {
        viewModel.loadArticles(it, targetPage)
    }
}
```

注意：`showPagePicker`（L248-252）已显式设 `fullRefresh = true` 再调用 `loadArticles(targetPage)`，保持不变即可。

### 改动 2：webview cacheFirst 默认值

#### 现状分析（已核实源码）

`RssSource.kt` L112-113：

```kotlin
/**是否优先加载缓存*/
@ColumnInfo(defaultValue = "0")
var cacheFirst: Boolean = false,
```

`ReadRssActivity.kt` L421：

```kotlin
cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT
```

#### 实现方案

仅改 `RssSource.kt` 默认值：

```kotlin
/**是否优先加载缓存*/
@ColumnInfo(defaultValue = "1")
var cacheFirst: Boolean = true,
```

`ReadRssActivity.kt` 无需改动（已依赖该字段）。

#### Room Schema 迁移考量

- `@ColumnInfo(defaultValue = "0")` → `"1"`：Room 在新增行且未显式赋值时使用默认值。
- 存量数据：已存在的行 `cacheFirst` 字段保持其当前值（不会因默认值变更而改写）。
- 是否需要提升 schema 版本 + 编写 `Migration`？
  - 仅改字段默认值不改变列类型或约束，Room 通常不强制要求 schema 版本提升。
  - 但为安全起见，若 `AppDatabase` 当前版本已有迁移链，建议核对 `app/schemas/` 下最新版本 JSON，确认是否生成新 schema 导出文件。
  - 本期决策：不改 schema 版本（仅默认值变更，存量数据不动）。若测试发现 Room 报 `IllegalStateException`，再补 `Migration`。

## Architecture Decisions

### ADR-1：列表页采用「缓存优先 + 网络后台刷新」而非「纯缓存」或「纯网络」

**Y-Statement：**

- **Context（背景）**：列表页已有 Room Flow 缓存机制（`flowByOriginSort`），但 `fullRefresh` 初始 `true` + `loadArticles()` 强制 `true`，导致网络回来后总是全量替换，丢失 DiffUtil 增量更新优势，首屏体感「每次都是新加载」。
- **Facing（面临关切）**：需要在「首屏速度」「数据新鲜度」「实现复杂度」三者间权衡。
- **We decided（决定）**：采用「缓存优先 + 网络后台刷新」——首次进入 `fullRefresh=false` 让缓存走 DiffUtil 显示，同时发起网络请求，写入数据库后 Flow 自动驱动二次增量合并。
- **And selected（选择选项）**：方案 B（Alternatives 表）。
- **Accepting that（接受权衡）**：
  - 实现需区分刷新路径（首次进入 vs 下拉刷新 vs 翻页），增加参数化复杂度。
  - 存在短暂双渲染（缓存→网络合并）。
- **Because（因为）**：
  - 复用现有 Flow + DiffUtil 机制，改动最小（仅 `fullRefresh` 标志传递）。
  - 兼顾首屏速度与数据新鲜度。
  - 不破坏现有防抖（`delay(200)`）与 ViewHolder 状态保护（切换标签仍可走全量，见 L177 注释）。
- **Neglecting（忽略的选项）**：
  - 方案 A（纯缓存）：数据不自动更新，违背预期。
  - 方案 C（仅改 webview）：不解决列表页核心痛点。

### ADR-2：webview 采用 `LOAD_CACHE_ELSE_NETWORK` 而非应用层混合策略

**Y-Statement：**

- **Context（背景）**：`RssSource.cacheFirst` 默认 `false`，webview 走 `LOAD_DEFAULT`（网络优先），无缓存命中优势。标准 `WebSettings` 缓存模式有 `LOAD_DEFAULT` / `LOAD_CACHE_ELSE_NETWORK` / `LOAD_NO_CACHE` / `LOAD_CACHE_ONLY`，无「先缓存秒开 + 后台静默网络刷新」的标准混合模式。
- **Facing（面临关切）**：在「实现成本」「缓存命中率」「内容新鲜度」间权衡。
- **We decided（决定）**：将 `cacheFirst` 默认值改为 `true`，webview 默认 `LOAD_CACHE_ELSE_NETWORK`；用户主动点击「刷新」菜单拉取最新。
- **And selected（选择选项）**：方案 B（改默认值 + 手动刷新补偿）。
- **Accepting that（接受权衡）**：
  - 缓存可能过期，用户看到的可能是旧正文（已知上限：缓存失效时长内）。
  - 存量源 `cacheFirst=false` 不自动迁移。
  - 依赖 POST 的源可能行为异常。
- **Because（因为）**：
  - 改动最小（仅 1 行默认值），`ReadRssActivity.kt` 无需改。
  - RSS 正文相对静态，缓存优先 + 手动刷新符合阅读场景。
  - 标准 `WebSettings` 无混合模式，自行实现 `shouldInterceptRequest` 拦截 + 缓存读取 + 二次刷新复杂度高、易引入线程/内存问题。
- **Neglecting（忽略的选项）**：
  - 方案 D（应用层混合策略）：体验最佳但复杂度过高，留作后续迭代。
  - `LOAD_CACHE_ONLY`：永不网络，无法获取新内容。

### ADR-3：不编写存量数据迁移脚本

**Y-Statement：**

- **Context（背景）**：改 `cacheFirst` 默认值后，已存在源的该字段保持原值（`false`），不会自动变为 `true`。
- **Facing（面临关切）**：「尊重用户既有配置」与「让所有用户享受缓存优先」的冲突。
- **We decided（决定）**：不编写迁移脚本，仅新默认值生效；存量用户可在源编辑页手动开启。
- **And selected（选择选项）**：仅改默认值，不动存量。
- **Accepting that（接受权衡）**：存量用户升级后 webview 仍走 `LOAD_DEFAULT`，直到手动开启。
- **Because（因为）**：
  - 尊重用户既有自定义配置，避免「升级后行为突变」。
  - 迁移脚本需判断「显式 false」还是「未设置」，逻辑复杂易错。
  - 源编辑页已有 `cacheFirst` 开关，用户可自助开启。
- **Neglecting（忽略的选项）**：
  - 一次性迁移 `cacheFirst IS NULL OR cacheFirst = 0` → `1`：影响面大，本期不做。

## Data Flow

### 列表页数据流（改动后）

```
用户进入列表页
       │
       ▼
initData() 启动 flowByOriginSort Flow ──► Room 查询缓存
       │                                      │
       │                                      ▼
       │                              Flow 发出缓存 List
       │                                      │
       │                              isResumed=true, fullRefresh=false, newList非空
       │                                      │
       │                                      ▼
       │                              DiffUtil 增量更新 → 缓存立即显示
       │
       ▼
initView() 调用 loadArticles() (fullRefresh=false)
       │
       ▼
viewModel.loadArticles() ──► Rss.getArticles() 网络请求
       │                              │
       │                       成功   │   失败
       │         ┌────────────────────┘    │
       │         ▼                         ▼
       │   appDb.rssArticleDao.insert   loadErrorLiveData.postValue(错误)
       │         │                         │
       │         ▼                         ▼
       │   Flow 再次发出新 List        错误提示（缓存保留）
       │         │
       │   fullRefresh=false
       │         │
       │         ▼
       │   DiffUtil 增量合并新条目
       │
       ▼
loadFinallyLiveData → 关闭刷新指示
```

### webview 数据流（改动后）

```
用户点击文章
       │
       ▼
ReadRssActivity.onActivityCreated
       │
       ▼
upWebviewSettings()
       │
       ▼
cacheFirst=true (新默认值)
       │
       ▼
cacheMode = LOAD_CACHE_ELSE_NETWORK
       │
       ▼
currentWebView.loadUrl / loadDataWithBaseURL
       │
       ├──► HTTP 缓存命中 ──► 秒开显示
       │
       └──► HTTP 缓存未命中 ──► 网络加载 ──► 显示 + 写入缓存

用户点击「刷新」菜单
       │
       ▼
refresh() → currentWebView.reload() ──► 强制网络拉取最新
```

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt` | 修改 | L73 `fullRefresh` 初始值 `true`→`false`；L128-130 下拉刷新传 `fullRefresh=true`；L217-222 `loadArticles()` 增加参数 `fullRefresh: Boolean = false` |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 修改 | L112-113 `cacheFirst` 默认值 `false`→`true`，`@ColumnInfo(defaultValue = "0")`→`"1"` |
| `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt` | 不变 | L421 逻辑已依赖 `cacheFirst` 字段，无需修改 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt` | 不变 | 网络加载逻辑无需修改 |
| `app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt` | 不变 | 缓存接口无需修改 |
| `app/src/main/assets/updateLog.md` | 修改 | 顶部追加日期条目，面向用户说明缓存优先体验 |

### 改动量评估

- 代码改动：约 5-8 行（`RssArticlesFragment.kt` 3 处 + `RssSource.kt` 1 处）
- 文档同步：`updateLog.md` 1 条
- 风险：低（改动局部，不涉及核心抓取/解析逻辑）

## 验证策略

| 验证项 | 方法 |
|--------|------|
| 列表页首次进入走 DiffUtil | 进入有缓存的源，观察无全量闪烁，新条目平滑插入 |
| 下拉刷新全量替换 | 下拉后列表按最新 `order` 重排 |
| 翻页全量替换 | `NumberPickerDialog` 切页后内容切换、滚动归零 |
| 阅读返回已读状态更新 | 点击文章返回，已读样式更新无闪烁 |
| 网络失败保留缓存 | 断网进入列表，缓存显示 + 错误提示 |
| webview 缓存秒开 | 二次打开文章，秒开；点击「刷新」拉取最新 |
| 存量源不受影响 | 已有 `cacheFirst=false` 源仍走 `LOAD_DEFAULT` |
