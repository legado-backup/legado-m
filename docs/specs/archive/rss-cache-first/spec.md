# RSS 阅读源缓存优先加载 - 规格说明书

> 状态：🔄 设计中

## Intent

让用户进入 RSS 订阅源列表页与阅读 webview 页时，**优先使用本地缓存秒开**，同时在后台请求网络数据并增量合并，消除「每次进入都像全新加载」的卡顿体感，并保留用户主动刷新获取最新内容的能力。

核心价值：

- **首屏可见速度提升**：列表页用 Room Flow 缓存 + DiffUtil 增量更新；webview 用 `LOAD_CACHE_ELSE_NETWORK`。
- **数据最终一致**：缓存先展示，网络回来后增量更新（列表页）或由用户手动刷新（webview 页）。
- **降级可靠**：网络失败不清空已显示缓存。

## Scope

### In Scope

| 模块 | 功能 |
|------|------|
| **列表页 fullRefresh 逻辑调整** | `RssArticlesFragment` 区分「首次进入/后台刷新」与「下拉刷新/翻页」两种路径，前者 `fullRefresh=false` 走 DiffUtil 增量更新，后者 `fullRefresh=true` 走全量替换 |
| **webview cacheFirst 默认值** | `RssSource.cacheFirst` 默认值 `false` → `true`，使 webview 默认 `LOAD_CACHE_ELSE_NETWORK` |
| **网络失败降级** | 列表页网络失败保留缓存（沿用 `loadErrorLiveData`）；webview 网络失败由缓存模式自动回退 |
| **手动刷新保留** | 列表页下拉刷新、webview 顶部「刷新」菜单均保持原语义 |

### Out of Scope

- RSS 抓取/解析规则改动（`Rss.getArticles`、`ruleArticles`、`ruleNextPage` 等不变）
- 引入新缓存存储（不新增表/字段，沿用 `rssArticles` 表与 WebView HTTP 缓存）
- webview「先缓存秒开 + 后台静默网络刷新」混合策略（标准 `WebSettings` 缓存模式不直接支持，详见 ADR-2）
- 已有 `cacheFirst=false` 存量数据的迁移（仅改默认值，存量源按其显式值保留；详见 Drawbacks）
- 书源（BookSource）列表页同等待遇（本期仅 RSS）

## Approach

采用「缓存优先 + 网络后台刷新」组合：

1. **列表页**：进入页面时 `fullRefresh=false`，让 `flowByOriginSort` 发出的缓存走 DiffUtil 增量更新；同时仍调用 `loadArticles()` 拉取网络数据，写入数据库后 Flow 自动再次发出，同样走 DiffUtil 合并。下拉刷新与翻页仍 `fullRefresh=true` 全量替换。
2. **webview 页**：将 `RssSource.cacheFirst` 默认值改为 `true`，webview 默认 `LOAD_CACHE_ELSE_NETWORK`，缓存命中即秒开；用户点击「刷新」菜单 `reload()` 拉取最新。

### Alternatives Considered

| 方案 | 描述 | 优点 | 缺点 | 结论 |
|------|------|------|------|------|
| **A. 纯缓存优先（只显示缓存，不自动网络刷新）** | 列表页仅读缓存，不主动请求网络；webview 用 `LOAD_CACHE_ONLY` | 省流量、首屏最快 | 数据永远不更新，除非用户手动刷新；违背「内容应该是最新的」预期 | ❌ 不采用 |
| **B. 缓存优先 + 网络后台刷新（推荐）** | 列表页缓存先显示 + 同时网络请求 + DiffUtil 合并；webview 缓存优先 + 手动刷新 | 兼顾速度与新鲜度；复用现有 Flow + DiffUtil 机制 | 实现需区分刷新路径；网络回来仍有全量替换风险需控制 `fullRefresh` 标志 | ✅ 采用 |
| **C. 仅改 webview 默认值（不动列表页）** | 仅将 `cacheFirst` 默认值改 `true`，列表页逻辑不动 | 改动最小 | 不解决列表页「每次进入全量替换」的核心痛点 | ❌ 不采用 |
| **D. 列表页缓存优先 + webview 应用层混合策略** | 列表页同 B；webview 自定义 `shouldInterceptRequest` 实现「先返回缓存 Response，再异步网络刷新」 | webview 体验最佳 | 标准 WebView 无「先缓存后网络」标准模式，需自行实现请求拦截+缓存读取+二次刷新，复杂度高、易引入内存/线程问题 | ❌ 不采用（可作为后续迭代） |

### Drawbacks

- **存量数据不自动迁移**：仅改 `cacheFirst` 默认值，已存在源的 `cacheFirst` 字段若显式为 `false` 则保持 `false`。用户需手动在源编辑页开启或重新导入。升级路径：可在首次启动时执行一次性「`cacheFirst IS NULL` 或为旧默认值时更新为 `true`」的迁移脚本，但本期不实现，避免影响存量用户自定义配置。
- **webview 缓存可能过期**：`LOAD_CACHE_ELSE_NETWORK` 只要缓存有就用，即使过期也不主动网络更新。用户看到的可能是旧正文。已知上限：缓存失效时长内显示旧内容。升级路径：用户手动「刷新」或后续采用方案 D。
- **列表页短暂双渲染**：缓存先显示，网络回来后 DiffUtil 再合并，存在视觉轻微变化（如新条目插入、已读状态更新）。已知上限：取决于网络耗时，通常 < 2s。升级路径：可加 loading 指示但不阻塞缓存显示。
- **`LOAD_CACHE_ELSE_NETWORK` 对 POST/动态内容不友好**：依赖 POST 的源可能行为异常。已知上限：少数交互型 RSS 源。升级路径：源编辑页可单独关闭 `cacheFirst`。

## Requirements

### 功能需求

| ID | 需求 | 优先级 |
|----|------|--------|
| REQ-1 | 首次进入列表页时，若数据库已有缓存，立即用 DiffUtil 增量更新显示缓存，不强制全量替换 | P0 |
| REQ-2 | 首次进入列表页时，同时发起网络请求获取最新数据，写入数据库后由 Flow 自动驱动增量合并 | P0 |
| REQ-3 | 下拉刷新时 `fullRefresh=true`，全量替换列表内容 | P0 |
| REQ-4 | 翻页（切换页码）时 `fullRefresh=true`，全量替换并滚动到顶部 | P0 |
| REQ-5 | 点击文章进入阅读后返回列表，`fullRefresh=false`，走 DiffUtil 更新已读状态 | P0 |
| REQ-6 | 网络加载失败时，不清空已显示的缓存列表，仅通过 `loadErrorLiveData` 提示错误 | P0 |
| REQ-7 | `RssSource.cacheFirst` 默认值改为 `true` | P0 |
| REQ-8 | webview 在 `cacheFirst=true` 时使用 `LOAD_CACHE_ELSE_NETWORK`，缓存命中即显示 | P0 |
| REQ-9 | webview 顶部「刷新」菜单保留，用户可主动 `reload()` 拉取最新 | P0 |
| REQ-10 | 源编辑页仍可手动关闭 `cacheFirst`（已有字段开关，不删除） | P1 |

### 非功能需求

| ID | 需求 |
|----|------|
| NFR-1 | 不破坏现有 DiffUtil 防抖逻辑（`delay(200)`）与切换标签ViewHolder 状态保护（注释 L177 保留语义） |
| NFR-2 | 不引入新依赖、不新增数据库表/字段（仅改字段默认值） |
| NFR-3 | 改动控制在 2 个文件内（`RssArticlesFragment.kt`、`RssSource.kt`），`ReadRssActivity.kt` 无需改逻辑 |
| NFR-4 | 数据库 schema 版本若需迁移，遵循 Room `Migration` 规范 |

## Scenarios

### 场景 1：首次进入列表页（有缓存）

1. 用户进入某订阅源分类页
2. `initData()` 启动 `flowByOriginSort` Flow
3. Flow 立即发出数据库缓存列表
4. `isResumed` 已为 true、`fullRefresh=false`（新初始值）、`newList` 非空 → 走 DiffUtil 增量更新，缓存立即显示
5. 同时 `loadArticles()` 发起网络请求
6. 网络返回，`insert` 写入数据库，Flow 再次发出
7. `fullRefresh` 仍为 false → 走 DiffUtil 增量合并新条目

**验证**：首屏无白屏；新条目平滑插入；无闪烁全量替换。

### 场景 2：首次进入列表页（无缓存）

1. 用户首次进入新订阅源，数据库无缓存
2. Flow 发出空列表，`newList.isEmpty()` → `setItems(空)`（不显示内容）
3. `loadArticles()` 网络请求中，`refreshLayout.isRefreshing = true` 显示加载指示
4. 网络返回，`insert` 写入，Flow 发出非空列表
5. 此时 `fullRefresh=false` 但 `newList` 之前为空、`isResumed=true` → 走 DiffUtil 增量更新（从空到非空）

**验证**：加载指示正常；数据到来后正常显示。

### 场景 3：下拉刷新

1. 用户下拉触发 `setOnRefreshListener`
2. `loadArticles(fullRefresh = true)` 设置 `fullRefresh=true` 并发起网络请求
3. 网络返回，Flow 发出新列表
4. `fullRefresh=true` → 走 `setItems` 全量替换

**验证**：列表全量刷新；排序按最新 `order` 重排。

### 场景 4：翻页（切换页码）

1. 用户通过 `NumberPickerDialog` 选择新页码
2. `loadArticles(targetPage)` 设 `fullRefresh=true`，滚动到顶部
3. 网络返回，Flow 发出该页数据
4. `fullRefresh=true` → 全量替换

**验证**：列表切换到新页内容；滚动位置归零。

### 场景 5：阅读返回后列表已读状态更新

1. 用户点击文章进入 `ReadRssActivity`，`readRss()` 设 `fullRefresh=false`
2. 返回列表，`onResume` 设 `isResumed=true`
3. 阅读记录写入 `rssReadRecords`，Flow 发出更新（`read` 字段变化）
4. `fullRefresh=false` → DiffUtil 用 `getChangePayload` 仅更新「read」标记

**验证**：已读条目样式更新，无全量闪烁。

### 场景 6：网络失败

1. 列表页缓存已显示，网络请求失败
2. `onError` 回调：`loadFinallyLiveData.postValue(false)`、`loadErrorLiveData.postValue(错误信息)`
3. `loadFinallyLiveData` 观察者关闭刷新指示，`loadErrorLiveData` 观察者显示错误
4. 已显示的缓存不被清空

**验证**：缓存保留；错误提示可见；刷新指示关闭。

### 场景 7：webview 缓存优先打开

1. 用户点击文章进入 `ReadRssActivity`
2. `upWebviewSettings` 读取 `cacheFirst=true`（新默认值）
3. `cacheMode = LOAD_CACHE_ELSE_NETWORK`
4. webview 命中 HTTP 缓存，秒开正文
5. 用户点击「刷新」菜单 → `reload()` 强制网络拉取最新

**验证**：缓存命中时秒开；刷新后内容更新。

### 场景 8：webview 无缓存

1. 首次打开某文章，无 HTTP 缓存
2. `LOAD_CACHE_ELSE_NETWORK` 无缓存可用 → 走网络加载
3. 加载完成后缓存写入，下次打开可秒开

**验证**：首次正常网络加载；二次进入秒开。

### 场景 9：存量源 `cacheFirst=false`

1. 用户已有源 `cacheFirst` 字段显式为 `false`（旧默认值）
2. 升级后该字段仍为 `false`，webview 走 `LOAD_DEFAULT`（网络优先）
3. 用户若想开启，需在源编辑页手动切换

**验证**：存量配置不被破坏；用户可手动开启。
