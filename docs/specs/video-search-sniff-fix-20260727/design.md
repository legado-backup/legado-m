# 技术设计：视频播放器嗅探失败 & 搜索聚合默认勾选修复

> **Spec ID**：video-search-sniff-fix-20260727
> **关联**：[README.md](./README.md) | [spec.md](./spec.md) | [tasks.md](./tasks.md)

---

## 一、技术架构

### 1.1 视频播放链路（问题一相关）

```
用户点击视频
  ├─ VideoPlayerActivity.onActivityCreated
  │   └─ VideoPlay.initSource(sourceKey, ...)  // 加载 source
  ├─ VideoFragment.activatePlayer
  │   └─ VideoPlay.startPlay(player) 或 VideoPlay.switchToArticle(index, player)
  ├─ VideoPlay.startPlay
  │   ├─ HttpHelper.executeStrRequest  // 获取页面内容
  │   ├─ ContentProcess 解析 ruleContent  // 提取视频流 URL
  │   ├─ sniffVideoType  // 嗅探视频流类型（HLS/MP4）
  │   └─ ExoPlayer 播放
  │       ├─ ExoFallback.tryPlay  // fallback 链路
  │       │   ├─ 首次：sniffedContentType
  │       │   ├─ BUFFERING 超时 → fallback
  │       │   └─ ❌ 当前：切换到不兼容 contentType → 解析失败
  │       │   └─ ✅ 修复后：保持 contentType，切换 DataSource 配置
  │       └─ onPlayerError / first frame rendered
```

### 1.2 搜索聚合跳转链路（问题二相关）

```
RssSearchActivity（搜索聚合）
  ├─ RssSearchModel.mergeItems  // 多源合并
  │   └─ SearchRssArticle.origins（LinkedHashSet）+ originArticles（HashMap）
  ├─ showArticleInfo(article)
  │   ├─ RssSearchSourceHolder.searchArticle = article
  │   ├─ RssSearchSourceHolder.articles = article.originArticles  // HashMap
  │   └─ RssSearchSourceHolder.rssArticles = adapter.getItems().mapNotNull { it.getDefaultArticle() }
  │       └─ getDefaultArticle() = origins.firstOrNull()?.let { originArticles[it] }  // origins 顺序
  └─ startActivity<RssArticleInfoActivity>

RssArticleInfoActivity（详情页）
  ├─ loadData 行 215
  │   └─ ❌ 当前：selectedOrigin = articlesMap.keys.firstOrNull()  // HashMap 顺序
  │       └─ ✅ 修复后：selectedOrigin = searchArticle?.origins?.firstOrNull()
  ├─ tvRead.onClick → getSelectedArticle() → startRead(rssArticle)
  └─ startActivity<VideoPlayerActivity> (sourceKey = rssArticle.origin)

VideoPlayerActivity → VideoPlay.initSource(sourceKey)  // source = 用户选的源
  └─ VideoFragment.activatePlayer → VideoPlay.switchToArticle(0)
      ├─ ❌ 当前：加载 rssArticles[0]，但不更新 source
      │   └─ source（用户选的源）≠ rssArticles[0].origin → ruleContent 解析失败
      └─ ✅ 修复后：同步更新 source = rssArticles[0].origin 对应的源
```

---

## 二、问题一根因分析 + 修复方案

### 2.1 根因分析：ExoFallback 错误 contentType 切换

**证据链**（HLS 案例，`appLog-26-07-27_09-32-03.789.txt` 行 432-469）：

```
行 432: HttpHelper intercept 入口 path=/path/{id}/index.m3u8
行 434: sniffVideoType: success, contentType=2, mimeType=application/x-mpegURL  // 嗅探识别为 HLS
行 435: ExoPlayer state: BUFFERING
行 436: ExoFallback: try contentType=2 (#1/3)  // 首次尝试 contentType=2
行 442: ExoPlayer BUFFERING timeout (12s), trigger fallback  // 12 秒后超时
行 443: ExoFallback: switch to next MediaSource (2/3)
行 444: ExoFallback: try contentType=4 (#2/3)  // ❌ 错误切换到 contentType=4（MP4）
行 445: ExoPlayer onPlayerError: errorCode=3003(ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED)
行 454: UnrecognizedInputFormatException: None of the available extractors could read the stream
```

**证据链**（MP4 案例，`appLog-26-07-27_17-09-35.928.txt` 行 170-204）：

```
行 171: sniffVideoType: success, contentType=4, mimeType=video/mp4, moov=FRONT  // 嗅探识别为 MP4
行 173: ExoFallback: try contentType=4 (#1/3)
行 177: ExoPlayer BUFFERING timeout (12s), trigger fallback  // 12 秒后超时
行 179: ExoFallback: try contentType=2 (#2/3)  // ❌ 错误切换到 contentType=2（HLS）
行 180: ExoFallback: unrecoverable error: code=3002(ERROR_CODE_PARSING_MANIFEST_MALFORMED)
行 188: ParserException: Input does not start with the #EXTM3U header  // HLS 解析器无法解析 MP4
```

**根因结论**：
- `sniffVideoType` 已通过 magic bytes + mimeType 正确识别视频流类型（contentType=2 HLS 或 contentType=4 MP4）
- ExoPlayer 在 BUFFERING 状态超过 12s 后，ExoFallback 逻辑会切换到**下一个 contentType**，fallback 列表为 `[嗅探结果, 另一个contentType, contentType=0]`
- 切换到不兼容的 contentType 后，HLS 解析器（HlsPlaylistParser）试图解析 MP4 流，或 MP4 extractor 试图解析 HLS 流，必然失败
- **本质 bug**：BUFFERING 超时本应通过重试同 contentType（调整 DataSource 缓冲、更换 Referer/UA）解决，而不是切换到不兼容的 contentType

**为什么浏览器能播放**：WebView 直接根据 HTTP Response 的 `Content-Type: application/x-mpegURL` 或 `video/mp4` 选择对应解码器，不经过 ExoPlayer 的 fallback 切换链路。

### 2.2 "第一个视频必失败"形成链路

```
首次播放请求
  ├─ DoH DNS 全部失败（延迟 +N 秒）
  ├─ CDN 冷启动（首字节延迟 +N 秒）
  ├─ FirstFramePreloader 缓存已被清理（无预热）
  ├─ 累积延迟 > 12s
  └─ 触发 BUFFERING 12s 超时
       └─ ExoFallback 错误切换 contentType
            └─ 解析器不匹配 → ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED
                 └─ 播放失败

用户下拉/切换第二个视频
  ├─ DoH 已禁用，系统 DNS 已缓存（延迟低）
  ├─ CDN 已缓存首帧（延迟低）
  ├─ 首帧 < 12s
  └─ BUFFERING 不超时
       └─ 保持原 contentType
            └─ 播放成功
```

### 2.3 修复方案

#### 修复方案 1.1：ExoFallback 保持 contentType（P0）

**位置**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（fallback 逻辑实际所在文件，`ExoFallback.kt` 不存在）

> **当前实现状态（源码核实）**：项目无独立 `ExoFallback.kt` 文件，fallback 链路逻辑内聚在 `Exo2MediaPlayer.kt` 的 `prepareAsyncInternal` 及其内部回调中。本修复在 `Exo2MediaPlayer.kt` 内新增 `ExoFallback` 内部类或顶层私有类承载新设计，不新建文件，避免文件爆炸。

**当前逻辑（错误）**：
```kotlin
// fallback 列表包含不兼容的 contentType
fallbackTypes = [sniffedContentType, otherContentType, ContentType.OTHER]
```

**修复后逻辑**：
```kotlin
// fallback 列表保持相同 contentType，仅切换 DataSource 配置
fallbackTypes = [sniffedContentType, sniffedContentType(withAltDataSource), sniffedContentType(withRetry)]
```

**设计要点**：
- fallback 列表前 2 项全部使用 `sniffedContentType`，仅切换 DataSource 配置：
  - 第 1 次：默认 DataSource（Cronet）
  - 第 2 次：备用 DataSource（OkHttp）+ 不同 Referer/UA
- **第 3 项允许切换到兼容 contentType**（同 contentType 重试 2 次失败后的兜底）：
  - 兼容规则：HLS↔DASH 互转允许（均为流式清单格式）；**禁止 HLS→Progressive 或 MP4→HLS**（格式不兼容）
  - 切换前必须调用 magic bytes 校验（修复方案 1.6）
  - sniff 返回 UNKNOWN 时保留现有 URL 后缀启发式逻辑（`buildFallbackTypes` 行 198-217 的 UNKNOWN 分支）
- 切换 DataSource 配置时输出日志（DataSource 类型 + Referer/UA 变更）

#### 修复方案 1.2：延长首次 BUFFERING 超时（P0）

**位置**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（BUFFERING 超时检测在同文件的 `bufferingTimeoutHandler`）

**当前逻辑**：
```kotlin
val BUFFERING_TIMEOUT_MS = 12_000  // 固定 12s
```

**修复后逻辑**：
```kotlin
val isFirstPlay = ...  // 判断是否首次播放（如 VideoPlay.rssArticleIndex == 0 且未成功播放过）
val BUFFERING_TIMEOUT_MS = if (isFirstPlay) 25_000 else 12_000
```

**设计要点**：
- 首次播放（CDN 冷启动场景）超时 25s
- 后续播放保持 12s
- 超时触发时输出日志：`BUFFERING timeout (${timeoutMs}ms), isFirstPlay=${isFirstPlay}`
- **isFirstPlay 字段实现**（源码核实：VideoPlay 当前无此字段，需新增）：
  - 在 `VideoPlay.kt` 新增 `@Volatile var hasPlayedSuccessfully: Boolean = false`
  - **重置时机**：`initSource`（行 665-719）入口处重置为 `false`（即 `isFirstPlay = !hasPlayedSuccessfully`，新源加载视为首次）
  - **置 true 时机**：`startPlay` 首帧渲染成功回调（ExoPlayer `onPlayerStateChanged` state==READY 时）置 `hasPlayedSuccessfully = true`
  - Exo2MediaPlayer 通过参数或接口获取 isFirstPlay 值，不直接访问 VideoPlay 字段

#### 修复方案 1.3：FirstFramePreloader 缓存延迟清理（P1）

**位置**：`app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt`

> **当前实现状态（源码核实）**：`FirstFramePreloader.kt` 行 139 仅有 `fun clearCache()`（立即清理，无延迟），**无 `delayedClearCache` 方法**。`clearCache()` 仅清理 `preloadCache`（`ConcurrentHashMap<String, Long>`，URL→时间戳映射，行 34），**不清理预加载数据本身**。预加载数据实际写入 ExoPlayer `SimpleCache`（行 112-117 `preloadUrl` 方法）。**因此延迟清理的对象应区分**：
> - `preloadCache`（URL→时间戳）：延迟清理意义不大（仅存时间戳，不占内存）
> - **ExoPlayer SimpleCache（预加载分片）**：延迟清理才有意义（避免快速切回时重新预热）
>
> **clearCache 调用方（源码核实，共 3 处）**：
> 1. `VideoPlay.kt:155`（onPause）— 主要清理点，应改为延迟清理
> 2. `VideoPlayerActivity.kt:342`（onDestroy）— Activity 销毁，应保持立即清理
> 3. `VideoPlayService.kt:45`（onDestroy）— Service 销毁，应保持立即清理

**当前逻辑（源码行 139-142）**：
```kotlin
fun clearCache() {
    preloadCache.clear()
    AppLog.putDebug("FirstFramePreloader: cache cleared")
}
```

**修复后逻辑**：
```kotlin
// 新增延迟清理方法（仅清理 preloadCache 时间戳映射）
fun delayedClearCache(delayMs: Long = 30_000) {
    handler.removeCallbacksAndMessages(null)
    handler.postDelayed({ clearCache() }, delayMs)
    AppLog.putDebug("FirstFramePreloader: delayed clear scheduled, delayMs=${delayMs}")
}

// 新增取消延迟清理（Activity onResume 时调用）
fun cancelDelayedClear() {
    handler.removeCallbacksAndMessages(null)
    AppLog.putDebug("FirstFramePreloader: delayed clear cancelled")
}

// clearCache 保持不变（立即清理 preloadCache）
```

**调用方修改（3 处）**：
- `VideoPlay.kt:155`（onPause）：`FirstFramePreloader.clearCache()` → `FirstFramePreloader.delayedClearCache()`
- `VideoPlayerActivity.kt:342`（onDestroy）：保持 `FirstFramePreloader.clearCache()`（立即清理，避免泄漏）
- `VideoPlayService.kt:45`（onDestroy）：保持 `FirstFramePreloader.clearCache()`（立即清理，避免泄漏）
- **新增**：VideoPlayerActivity onResume 调用 `FirstFramePreloader.cancelDelayedClear()`（若缓存仍有效则取消延迟清理）

**关于 ExoPlayer SimpleCache**：本期不修改 ExoPlayer SimpleCache 的清理时机（由 `ExoPlayerHelper.kt:892-903` 的 `cache` 字段管理，Activity onDestroy 时由 ExoPlayer release 自动释放）。延迟清理 SimpleCache 涉及 ExoPlayer 生命周期管理，风险较高，推迟到独立 spec。

#### 修复方案 1.4：DoH DNS 冷启动 30s 熔断（P1，已实现，验证即可）

**位置**：`app/src/main/java/io/legado/app/help/http/DohDns.kt`

> **当前实现状态（源码核实，2026-07-27 已交付）**：DohDns.kt 已实现冷启动 30s 熔断机制：
> - 行 79：`COLD_START_DISABLE_MS = 30_000L`（冷启动熔断 30s）
> - 行 111：`@Volatile private var isColdStart = true`（冷启动标志位）
> - 行 201-209：冷启动场景首次失败立即熔断 30s + 异步预热
> - 行 229-246：`asyncPreheatDoh()` 30s 后异步探测恢复
>
> **本任务无需重复实施**，仅在 Phase C 真机测试中验证：
> - 日志检查：冷启动场景首次 DoH 失败输出 `DohDns: cold start DoH failure, disable DoH 30s, async preheat`
> - 日志检查：30s 后输出 `DohDns: asyncPreheat success, DoH recovered` 或 `DohDns: asyncPreheat failed, DoH still unreachable`
> - 行为验证：首个视频播放首帧延迟 < 25s（原 6-9s DNS 累计延迟消除）

**常规熔断逻辑（非冷启动场景，保持不变，本任务不修改）**：
```kotlin
val DISABLE_DURATION_MS = 5 * 60 * 1000  // 常规熔断 5 分钟（连续 3 次失败触发）
```

> **本任务范围说明**：冷启动 30s 熔断已实现（2026-07-27 交付），**常规熔断 5min 保持不变**（连续 3 次失败触发，`GLOBAL_FAIL_THRESHOLD=3` 行 63）。分析报告 005 中出现的"disable DoH 5min"日志属于常规熔断场景（非冷启动），本期不修改。如需优化常规熔断时间，应独立 spec 评估（缩短至 1min 可能导致 DoH 频繁重试增加网络请求）。

#### 修复方案 1.5：首个视频预热机制（P1）

**位置**：`VideoPlay.kt` 或新增 `VideoPreloader.kt`

> **与 FirstFramePreloader 的关系（源码核实）**：`FirstFramePreloader.kt` 行 30 `PRELOAD_BYTES=1048575`（≈1MB），行 31 `MAX_CACHE_SIZE=10`（最多 10 个视频）。预热机制应**复用 FirstFramePreloader.preloadUrl**（行 112-117），将预加载的数据写入 ExoPlayer SimpleCache，而非自建缓存。spec.md F1.7 说的"前 64KB"是 moov 头识别的最小量，实际预热应使用 FirstFramePreloader 的 1MB（覆盖 moov 头 + 部分首帧数据）。

**设计要点**：
- **预热触发时机**：用户在视频列表页（RssArticleInfoActivity 或搜索结果页）点击视频项时，在跳转 VideoPlayerActivity 之前（或 onActivityCreated 中 startPlay 之前）异步触发预热
- **预热实现**：调用 `FirstFramePreloader.preloadUrl(videoUrl)`，预加载 1MB 数据到 ExoPlayer SimpleCache
- **videoUrl 获取**：在 RssArticleInfoActivity 中，通过 `searchArticle.origins.firstOrNull()` 获取默认源的 `ruleVideo` 或 `ruleContent` 解析出的视频 URL（若规则为嗅探型，则用文章 link 作为预热 URL）
- **实际播放时**：ExoPlayer 优先从 SimpleCache 命中预热数据，减少首帧延迟
- **取消机制**：用户快速切回或离开列表页时，取消未完成的预热（避免浪费网络请求）
- **预热日志**：`VideoPreloader: preload started, urlPath=/path/{id}` / `VideoPreloader: preload completed, bytes=***, cacheHit=true/false`

#### 修复方案 1.6：fallback 前 contentType 兼容性校验（P2）

**位置**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（与修复方案 1.1 同文件）

**设计要点**：
- 切换 contentType 前，先读取流头部 magic bytes
- 校验 magic bytes 是否匹配目标 extractor（如 `#EXTM3U` 匹配 HLS，`ftyp` 匹配 MP4）
- 不匹配则跳过该 fallback 项

#### 修复方案 1.7：fallback 决策日志（P2）

**位置**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（与修复方案 1.1 同文件）

**日志格式**：
```
ExoFallback: trigger reason=BUFFERING_TIMEOUT, timeoutMs=25000, isFirstPlay=true
ExoFallback: before contentType=2, after contentType=2 (保持不变)
ExoFallback: dataSource changed: Cronet -> OkHttp, referer=***, ua=***
```

---

## 三、问题二根因分析 + 修复方案

### 3.1 根因分析：HashMap 顺序不保证 + switchToArticle 不更新 source

**根因一**：`RssArticleInfoActivity.kt` 行 215 默认选中源使用 `HashMap.keys.firstOrNull()`

```kotlin
// RssArticleInfoActivity.kt 行 215
selectedOrigin = articlesMap.keys.firstOrNull()  // HashMap.keys 顺序不保证！
```

`articlesMap` 是 `HashMap<String, RssArticle>`（来自 `SearchRssArticle.originArticles`），keys 顺序由哈希值决定，**不保证与 `origins`（LinkedHashSet）的插入顺序一致**。

而 `rssArticles` 列表是用 `getDefaultArticle()` 生成的，每个聚合项取 `origins.firstOrNull()` 对应的文章。

**当 `articlesMap.keys.firstOrNull()` 不等于 `origins.firstOrNull()` 时**：
- 默认选中的源 ≠ rssArticles[0] 的源
- 用户点击"阅读"按钮传递的 `rssArticle` 与 `rssArticles[0]` 不是同一篇文章
- `VideoPlay.rssArticleIndex` 被设置为 0（`indexOfFirst` 找不到，`?: 0` 兜底）
- `VideoPlay.switchToArticle(0)` 加载 `rssArticles[0]`，但 `source` 是默认选中源
- **source 与 rssArticle 不匹配** → `ruleContent` 解析失败 → 播放失败

**根因二**：`VideoPlay.kt` 行 967-992 `switchToArticle` 不更新 source 字段

```kotlin
// VideoPlay.kt 行 967-992
fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    val article = articles.getOrNull(index)  // rssArticles[index]
    Coroutine.async(loadScope, IO) {
        rssStar = appDb.rssStarDao.get(article.origin, article.link)
        if (rssStar == null) {
            rssRecord = appDb.rssReadRecordDao.getRecord(article.link, article.origin)
        }
        // ❌ 缺失：source 字段未更新！source 仍是 initSource 中加载的（用户选的源）
        withContext(Main) {
            startPlay(player)
        }
    }
}
```

`switchToArticle` 更新了 `rssStar`/`rssRecord`（基于 `article.origin`），但**没有更新 `source` 字段**。`source` 字段在 `initSource` 中通过 Intent `sourceKey` 加载（用户选的源），`switchToArticle` 加载的 `rssArticles[index]` 可能是另一个源的文章。

`startPlay` 行 247-252 用 `source.ruleContent` 解析 `rssArticle.link`：
- 如果 `source` 与 `rssArticle` 不匹配（不同源的页面结构不同），`ruleContent` 解析失败

### 3.2 触发条件矩阵

| 场景 | selectedOrigin | rssArticles[0] 的源 | source（Intent） | 是否匹配 | 修复前 | 修复后 |
|------|----------------|---------------------|------------------|----------|--------|--------|
| 默认点击"阅读"（HashMap 顺序与 origins 一致） | origins[0] | origins[0] | origins[0] | ✅ | 成功 | 成功 |
| 默认点击"阅读"（HashMap 顺序与 origins 不一致） | origins[N] | origins[0] | origins[N] | ❌ | **失败** | 成功（方案 1+2） |
| 点击源列表第一项（origins[0]） | origins[0] | origins[0] | origins[0] | ✅ | 成功 | 成功 |
| 点击源列表第 N 项 | origins[N] | origins[0] | origins[N] | ❌ | **失败** | 成功（方案 2） |

### 3.3 修复方案

#### 修复方案 2.1：统一默认选中源（P0，快速修复）

**位置**：`app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt` 行 215

**当前代码**：
```kotlin
selectedOrigin = articlesMap.keys.firstOrNull()
```

**修复后代码**：
```kotlin
val searchArticle = RssSearchSourceHolder.searchArticle
// 使用 origins（LinkedHashSet）的第一个，与 rssArticles 列表的 getDefaultArticle() 一致
selectedOrigin = searchArticle?.origins?.firstOrNull() ?: articlesMap.keys.firstOrNull()
```

**效果**：确保默认选中源与 `rssArticles[0]` 的源一致，解决默认点击"阅读"按钮失败的问题。

**局限**：用户主动选择非第一个源时，仍然会失败（需配合方案 2.2）。

#### 修复方案 2.2：switchToArticle 同步更新 source（P0，根本修复）

**位置**：`app/src/main/java/io/legado/app/model/VideoPlay.kt` 行 967-992

**当前代码**：
```kotlin
fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    val articles = rssArticles ?: return false
    val article = articles.getOrNull(index) ?: return false
    rssArticleIndex = index
    rssEpisodes = null
    rssRoutes = null
    rssEpisodeIndex = 0
    rssRouteIndex = 0
    videoTitle = article.title
    Coroutine.async(loadScope, IO) {
        rssStar = appDb.rssStarDao.get(article.origin, article.link)
        if (rssStar == null) {
            rssRecord = appDb.rssReadRecordDao.getRecord(article.link, article.origin)
        }
        // ❌ 缺失：source 字段未更新
        withContext(Main) {
            startPlay(player)
        }
    }.onError { ... }
    return true
}
```

**修复后代码**：
```kotlin
// VideoPlay.kt 行 152：source 字段需加 @Volatile（IO 线程写、Main 线程读的可见性保护）
@Volatile var source: BaseSource? = null

fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    val articles = rssArticles ?: return false
    val article = articles.getOrNull(index) ?: return false
    rssArticleIndex = index
    rssEpisodes = null
    rssRoutes = null
    rssEpisodeIndex = 0
    rssRouteIndex = 0
    videoTitle = article.title
    Coroutine.async(loadScope, IO) {
        // ✅ 修复：同步更新 source 以匹配 article.origin
        val currentRssSource = source as? RssSource
        if (currentRssSource == null || currentRssSource.sourceUrl != article.origin) {
            val newSource = appDb.rssSourceDao.getByKey(article.origin)
            if (newSource == null) {
                // ✅ null 处理：source 不存在时输出 ERROR 日志并停止播放（避免 startPlay 用 null source 崩溃）
                AppLog.put("switchToArticle: source not found, origin=${article.origin.take(2)}***", isError = true)
                return@async
            }
            source = newSource
            AppLog.put("switchToArticle: source 更新为 ${article.origin.take(2)}***")
        }
        rssStar = appDb.rssStarDao.get(article.origin, article.link)
        if (rssStar == null) {
            rssRecord = appDb.rssReadRecordDao.getRecord(article.link, article.origin)
        }
        withContext(Main) {
            startPlay(player)
        }
    }.onError {
        AppLog.put("切换文章加载视频信息失败", it, true)
    }
    return true
}
```

**效果**：无论 `rssArticles[index]` 是哪个源的文章，`source` 都会同步更新为对应的源，确保 `ruleContent` 解析时 source 与 rssArticle 匹配。

**安全要点**：
- 日志输出 `article.origin.take(2) + "***"`，仅显示前 2 字符，避免泄露完整源 URL
- 仅在 `source` 不匹配时才更新，避免不必要的数据库查询

#### 修复方案 2.3：ReadRss.readRss 增加 source 兜底校验（P1，增强修复）

**位置**：`app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` 行 58-104

**当前代码**：
```kotlin
if (type == 2) {
    VideoPlay.rssArticles = rssArticles
    VideoPlay.rssArticleIndex = rssArticles?.indexOfFirst { it.link == rssArticle.link } ?: 0
    ...
}
```

**修复后代码**：
```kotlin
if (type == 2) {
    VideoPlay.rssArticles = rssArticles
    val index = rssArticles?.indexOfFirst { it.link == rssArticle.link } ?: -1
    if (index == -1) {
        // 兜底校验：rssArticle 不在 rssArticles 中（用户选了非默认源），输出 WARN 日志
        AppLog.put("ReadRss: source mismatch WARN, rssArticle.origin=${rssArticle.origin.take(2)}***, rssArticles[0].origin=${rssArticles?.firstOrNull()?.origin?.take(2)}***")
    }
    VideoPlay.rssArticleIndex = if (index == -1) 0 else index
    ...
}
```

**效果**：即使用户选的源的文章不在 `rssArticles` 列表中，也输出 WARN 日志便于排查，`rssArticleIndex` 兜底为 0（配合方案 2.2 的 source 同步更新，仍能播放 `rssArticles[0]`）。

**不改变 `rssArticles` 列表语义**：不插入用户选的源的文章到列表头，避免影响上下滑动切换文章的体验。

---

## 四、关键接口设计

### 4.1 ExoFallback 接口

```kotlin
/**
 * ExoFallback - 视频流播放 fallback 链路
 *
 * 修复要点：
 * 1. fallback 列表保持相同 contentType，仅切换 DataSource 配置
 * 2. 首次 BUFFERING 超时 25s，后续 12s
 * 3. fallback 决策日志完整
 */
class ExoFallback(
    private val sniffedContentType: Int,  // 嗅探识别的 contentType（2=HLS, 4=MP4）
    private val isFirstPlay: Boolean,      // 是否首次播放
) {
    /**
     * 构建 fallback 列表
     *
     * @return List<FallbackItem> 每个 FallbackItem 包含 contentType + DataSource 配置
     */
    fun buildFallbackList(): List<FallbackItem> {
        val timeoutMs = if (isFirstPlay) 25_000 else 12_000
        return listOf(
            FallbackItem(sniffedContentType, DataSourceConfig.Cronet, timeoutMs),
            FallbackItem(sniffedContentType, DataSourceConfig.OkHttp(altReferer = true), timeoutMs),
            FallbackItem(sniffedContentType, DataSourceConfig.Cronet(altUA = true), timeoutMs),
        )
    }

    /**
     * 记录 fallback 决策日志
     */
    fun logFallbackDecision(reason: FallbackReason, before: FallbackItem, after: FallbackItem) {
        AppLog.put(
            "ExoFallback: trigger reason=${reason.name}, timeoutMs=${before.timeoutMs}, isFirstPlay=${isFirstPlay}\n" +
            "ExoFallback: before contentType=${before.contentType}, after contentType=${after.contentType}\n" +
            "ExoFallback: dataSource changed: ${before.dataSourceConfig} -> ${after.dataSourceConfig}"
        )
    }
}

data class FallbackItem(
    val contentType: Int,
    val dataSourceConfig: DataSourceConfig,
    val timeoutMs: Long,
)

sealed class DataSourceConfig {
    object Cronet : DataSourceConfig()
    data class OkHttp(val altReferer: Boolean = false) : DataSourceConfig()
    data class Cronet(val altUA: Boolean = false) : DataSourceConfig()
}

enum class FallbackReason {
    BUFFERING_TIMEOUT,
    PARSING_ERROR,
    PLAYER_ERROR,
}
```

### 4.2 VideoPlay.switchToArticle 接口（修复后）

```kotlin
/**
 * 切换到指定索引的文章并播放
 *
 * 修复要点：
 * 1. 同步更新 source 字段为 article.origin 对应的源
 * 2. source 字段加 @Volatile（IO 线程写、Main 线程读的可见性保护）
 * 3. getByKey 返回 null 时输出 ERROR 日志并停止播放（避免 startPlay 崩溃）
 * 4. 输出 source 更新日志（前 2 字符 + ***）
 *
 * @param index 文章索引
 * @param player 播放器实例
 * @return 是否成功开始切换
 */
// VideoPlay.kt 行 152：source 字段需加 @Volatile
@Volatile var source: BaseSource? = null

fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    val articles = rssArticles ?: return false
    val article = articles.getOrNull(index) ?: return false
    rssArticleIndex = index
    rssEpisodes = null
    rssRoutes = null
    rssEpisodeIndex = 0
    rssRouteIndex = 0
    videoTitle = article.title
    Coroutine.async(loadScope, IO) {
        // 修复：同步更新 source 以匹配 article.origin
        val currentRssSource = source as? RssSource
        if (currentRssSource == null || currentRssSource.sourceUrl != article.origin) {
            val newSource = appDb.rssSourceDao.getByKey(article.origin)
            if (newSource == null) {
                // null 处理：source 不存在时输出 ERROR 日志并停止播放
                AppLog.put("switchToArticle: source not found, origin=${article.origin.take(2)}***", isError = true)
                return@async
            }
            source = newSource
            AppLog.put("switchToArticle: source 更新为 ${article.origin.take(2)}***")
        }
        rssStar = appDb.rssStarDao.get(article.origin, article.link)
        if (rssStar == null) {
            rssRecord = appDb.rssReadRecordDao.getRecord(article.link, article.origin)
        }
        withContext(Main) {
            startPlay(player)
        }
    }.onError {
        AppLog.put("切换文章加载视频信息失败", it, true)
    }
    return true
}
```

### 4.3 RssArticleInfoActivity.loadData 接口（修复后）

```kotlin
/**
 * 加载详情页数据
 *
 * 修复要点：
 * 1. 默认选中源使用 searchArticle.origins.firstOrNull()（LinkedHashSet 顺序）
 * 2. 与 rssArticles[0] 的源保持一致
 */
private fun loadData() {
    val articlesMap = RssSearchSourceHolder.articles ?: return
    val searchArticle = RssSearchSourceHolder.searchArticle

    // 修复：使用 origins（LinkedHashSet）的第一个，与 rssArticles 列表的 getDefaultArticle() 一致
    selectedOrigin = searchArticle?.origins?.firstOrNull() ?: articlesMap.keys.firstOrNull()

    // ... 其余逻辑不变
}
```

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| R1：ExoFallback 保持 contentType 后，某些站点确实需要切换 contentType（如嗅探识别错误） | 嗅探识别错误时无法通过 fallback 恢复 | 增加 fallback 前 contentType 兼容性校验（magic bytes 比对）；同 contentType 重试 1-2 次仍失败后，允许切换 contentType（但需校验兼容性） |
| R2：首次 BUFFERING 25s 用户感知卡顿 | 用户体验下降 | 25s 内显示加载进度条 + "CDN 冷启动中" 提示；首帧渲染后立即隐藏 |
| R3：switchToArticle 频繁更新 source 导致数据库查询增加 | 性能下降 | 仅在 `currentRssSource.sourceUrl != article.origin` 时才查询数据库；添加 source 缓存（LruCache） |
| R4：FirstFramePreloader 延迟清理导致内存占用增加 | OOM 风险 | 预热缓存大小由源码常量限制（源码核实：`MAX_CACHE_SIZE=10` 行 31 + `PRELOAD_BYTES=1048575`≈1MB 行 30，实际最多 10 个视频 × 1MB = 10MB；预加载数据写入 ExoPlayer SimpleCache 磁盘缓存，非 JVM 堆内存）；Activity/Service onDestroy 时立即清理（VideoPlayerActivity.kt:342 + VideoPlayService.kt:45 保持 clearCache()） |
| R5：DoH DNS 禁用时间缩短导致频繁重试 DoH | 网络请求增加 | 重试间隔 30s，且仅在网络空闲时重试；重试失败 3 次后延长禁用时间至 5min |
| R6：方案 2.1 修改默认选中源，可能影响已选中源的 UI 显示 | UI 显示异常 | `selectedOrigin` 改变后立即刷新源列表 UI 高亮状态 |
| R7：方案 2.2 switchToArticle 更新 source，可能影响 source 相关的其他逻辑（如 source.bookUrl） | 播放链路异常 | source 更新后，同步更新 bookUrl 等关联字段（如有）；增加 source 更新后的完整性校验 |
| R8：场景 E 修复后播放的是 origins[0] 的文章，而非用户选的 origins[N] 的文章 | 用户体验与预期不符 | 本期接受此限制（非目标 NG4）；后续可考虑改变 rssArticles 列表语义（但需独立 spec） |

---

## 六、日志设计

### 6.1 问题一日志设计

| 日志关键字 | 级别 | 触发时机 | 内容 |
|------------|------|----------|------|
| `ExoFallback: trigger reason=` | DEBUG | fallback 触发 | reason + timeoutMs + isFirstPlay |
| `ExoFallback: before contentType=` | DEBUG | fallback 决策 | before contentType + after contentType |
| `ExoFallback: dataSource changed:` | DEBUG | DataSource 切换 | before dataSourceConfig + after dataSourceConfig |
| `BUFFERING timeout` | WARN | BUFFERING 超时 | timeoutMs + isFirstPlay + urlPath（路径模式化） |
| `ExoPlayer first frame rendered:` | INFO | 首帧渲染成功 | latency + urlPath（路径模式化） |
| `FirstFramePreloader: cache cleared` | DEBUG | 缓存清理 | trigger（onPause/onStop/manual）+ delayMs |
| `DohDns: disable DoH` | WARN | DoH 禁用 | disableMs + reason |
| `switchToArticle: source 更新为` | DEBUG | source 更新 | sourceKey 前 2 字符 + *** |

### 6.2 问题二日志设计

| 日志关键字 | 级别 | 触发时机 | 内容 |
|------------|------|----------|------|
| `switchToArticle: source 更新为` | DEBUG | switchToArticle 更新 source | article.origin 前 2 字符 + *** |
| `ReadRss: source mismatch WARN` | WARN | rssArticle 不在 rssArticles 中 | rssArticle.origin 前 2 字符 + *** + rssArticles[0].origin 前 2 字符 + *** |
| `selectedOrigin =` | DEBUG | 默认选中源设置 | origin 前 2 字符 + *** + source（origins/HashMap） |

### 6.3 日志安全要求

- 所有日志中的 URL 必须路径模式化（`/path/{id}`）
- 所有日志中的域名必须代号化（`站点A/B/C` 或 `***`）
- 所有日志中的源名称必须代号化（`源[N]`）
- 所有日志中的 cookie/token 必须隐藏为 `***`
- sourceKey/sourceUrl 仅显示前 2 字符 + `***`

---

## 七、输出安全声明

本文档所有 URL 已路径模式化（`/path/{id}`），所有域名已代号化（`站点A/B/C` 或 `***`），所有源名称已代号化（`源[N]`），所有 cookie/token 内容已隐藏为 `***`。文档仅输出技术结论（错误码/异常类型/调用栈/根因/修复方案）。
