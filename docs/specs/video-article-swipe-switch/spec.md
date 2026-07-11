# spec.md — 视频播放器上下滑动切换文章列表

## 1. Intent（意图）

订阅源内置视频播放器当前只支持播放单个文章的视频。用户在文章列表中点击视频文章进入播放器后，如果想看列表中下一个视频文章，必须返回列表重新选择。

**用户原文**：
> "还记得我之前给你提的需求不？订阅源内置视频播放器支持上下滑动，主要是滑动后切换加载当前资源列表对应上下的视频资源进行播放"

**用户选择**：
> "两者结合"——上下滑动切换文章(rssArticles)，文章内集数通过其他手势或选择器切换

**目标**：上下滑动切换文章列表中的视频文章，文章内多集通过左下角集数选择器切换。

### 阶段8扩展（用户反馈 2026-07-11 22:30）

**用户原文**：
> "有没有思考另外几个问题，就是如果当前正在播放的视频列表被我下拉放完到最后一个了呢？你会不会异步去请求下一页列表数据呢？还有就是如果当前正在播放的视频已经快被我看完了？你会不会在后台帮我去缓冲下一个视频呢？还有就是如果我下一个下一个这么播放，但是中途退出返回到列表，你会帮我牟定到我退出正在看的视频列表所在位置吗？"

**阶段8目标**：
1. 分页加载：视频列表滑到最后一个时异步请求下一页
2. 预缓冲：当前视频快看完时后台预加载下一个视频URL
3. 位置记忆：退出返回列表时定位到正在看的视频位置

## 2. Scope（范围）

### In Scope

| # | 需求 | 说明 |
|---|------|------|
| F1 | VideoPlay 新增 rssArticles 列表字段 | 存储文章列表 + 当前文章索引 |
| F2 | ReadRss 传递 rssArticles 列表 | RssArticlesFragment → ReadRss → VideoPlayerActivity |
| F3 | VideoPagerAdapter 基于 rssArticles 创建 Fragment | 每个 Fragment 对应一个文章 |
| F4 | VideoFragment 异步加载文章视频信息 | 切换文章后调用 VideoPlay.switchToArticle 加载 |
| F5 | 集数选择器适配 | 切换文章后更新集数列表；切换集数时 Fragment 内部切换 URL |
| F6 | 线路选择器适配 | 切换文章后更新线路列表 |
| F7 | 标题更新 | 切换文章后更新左下角标题 + Toolbar 标题 |
| F8 | 向后兼容 | 从历史记录启动（无文章列表）→ 单 Fragment 旧逻辑；书源/单URL不受影响 |
| F9 | 分页加载（阶段8） | 视频列表滑到最后一个时异步请求下一页，追加到 rssArticles 并通知 ViewPager2 |
| F10 | 预缓冲（阶段8） | 当前视频播放进度超 80% 时后台预加载下一个文章的视频 URL，切换时直接使用缓存 |
| F11 | 位置记忆（阶段8） | 退出播放器返回文章列表时，列表滚动到退出时正在看的视频文章位置 |

### Out of Scope

| # | 排除项 | 原因 |
|---|--------|------|
| O1 | 书源模式文章切换 | 书源有自己的章节体系（toc/episodes），不涉及 rssArticles |
| O2 | 单URL模式文章切换 | singleUrl 只有一个视频链接，无需切换 |
| O3 | 跨订阅源切换 | 仅限当前文章列表内切换，不跨源 |
| O5 | R3 控件显隐逻辑变更 | 本 spec 不修改 R3 已实现的控件显隐/手势逻辑 |
| O6 | 预缓冲完整视频流缓冲（阶段8） | 仅预加载视频 URL（轻量级），不预缓冲完整视频流（避免多播放器实例管理复杂度） |

## 3. Approach（方案）

### 核心方案：VideoPlay 单例 + rssArticles 列表 + switchToArticle 方法

**数据流变更**：

```
当前数据流（R3）：
RssArticlesFragment → ReadRss.readRss(单个rssArticle) 
  → VideoPlayerActivity → VideoPlay.initSource(加载单个文章)
  → ViewPager2 基于 rssEpisodes.size 创建 Fragment
  → 上下滑动切换集数

目标数据流（本 spec）：
RssArticlesFragment → ReadRss.readRss(rssArticle + rssArticles列表)
  → VideoPlayerActivity → VideoPlay.initSource + rssArticles 存入单例
  → ViewPager2 基于 rssArticles.size 创建 Fragment
  → 上下滑动切换文章
  → 每个Fragment activatePlayer → VideoPlay.switchToArticle(index) 异步加载
  → 集数通过左下角选择器切换
```

### Alternatives Considered（备选方案）

#### 方案A：VideoPlay 单例 + rssArticles 列表（✅ 采用）

每个 Fragment 对应一个文章，切换文章时调用 `VideoPlay.switchToArticle(index)` 重新加载该文章的视频信息（复用 startPlay 中的 RssSource 分支逻辑）。

**优点**：
- 复用现有 startPlay 逻辑（ruleContent/R5 自动抓取/多线路解析）
- VideoPlay 单例状态管理一致
- 改动最小化

**缺点**：
- 切换文章是异步操作，需要事件通知 UI 更新
- VideoPlay 单例状态在切换文章时被重置

#### 方案B：每个 Fragment 持有独立播放状态

每个 Fragment 持有自己的 videoUrl/rssEpisodes/rssRoutes 等状态，不依赖 VideoPlay 单例。

**优点**：
- Fragment 状态隔离，切换不互相影响

**缺点**：
- 改动巨大，VideoPlay 单例深度耦合于整个播放链路
- 悬浮窗/全屏切换/设置面板都依赖 VideoPlay 单例
- 违反 YAGNI，过度工程化

#### 方案C：Intent extra 传递 rssArticles 列表

通过 Intent extra 传递文章列表。

**优点**：
- 无需修改 VideoPlay 单例

**缺点**：
- Intent 有大小限制（约 1MB），文章列表可能超限
- RssArticle 含 content 字段可能很大
- 不适合大列表

### Drawbacks（ drawbacks）

| # | 缺陷 | 缓解措施 |
|---|------|---------|
| D1 | VideoPlay 单例状态在切换文章时被重置 | switchToArticle 方法中保存/恢复必要状态 |
| D2 | 切换文章异步加载有延迟 | 显示加载提示（VIDEO_SUB_TITLE 事件） |
| D3 | rssArticles 列表可能很大（分页加载后） | 列表存储在 VideoPlay 单例（内存），退出播放器清理；分页加载有 hasMore 标记防无限加载 |
| D4 | 从历史记录启动无 rssArticles | 兼容旧逻辑：rssArticles=null 时单 Fragment |
| D5 | 分页加载失败不影响当前播放 | 加载失败时 AppLog 记录 + toast 提示，不影响当前视频播放 |
| D6 | 预缓冲的URL可能失效（网络错误等） | 预缓冲失败时不缓存，切换时正常走异步加载流程 |
| D7 | 位置记忆在文章不在当前列表页时无法定位 | index<0 时不滚动（用户可手动下拉加载更多），仅清除标记 |

### 阶段8扩展方案

#### F9: 分页加载方案

**核心思路**：VideoPlay 保存分页上下文（sortName/sortUrl/nextPageUrl/page/hasMore），onPageSelected 检测到最后一个时异步加载下一页。

**数据流**：
```
VideoPlayerActivity.onPageSelected(position)
  │
  │ position == rssArticles.size - 1（滑到最后一个）
  ▼
VideoPlay.loadMoreArticles()
  │
  ├── 检查 isLoadingMoreArticles / rssArticlesHasMore（防重复/防无更多）
  ├── isLoadingMoreArticles = true
  ├── Rss.getArticles(sortName, nextPageUrl, source, page+1, searchKey)
  │     └── 返回 (articles, newNextPageUrl)
  ├── 新文章追加到 rssArticles（mutableList.add）
  ├── 更新 nextPageUrl / page / hasMore
  ├── isLoadingMoreArticles = false
  └── postEvent(ARTICLES_LOADED, oldSize to newSize)  ← 通知 Activity
        │
        ▼
  VideoPlayerActivity 接收事件
        │
        └── videoPagerAdapter.notifyItemRangeInserted(oldSize, newSize)
              └── ViewPager2 自动创建新位置的 Fragment
```

**关键设计**：
1. VideoPlay 新增分页上下文字段：`rssSortName`/`rssSortUrl`/`rssNextPageUrl`/`rssArticlePage`/`rssArticlesHasMore`/`isLoadingMoreArticles`
2. ReadRss.readRss 中传递 sortName/sortUrl/nextPageUrl/page 给 VideoPlay
3. VideoPlay.loadMoreArticles() 复用 Rss.getArticles 逻辑
4. 通知方式：EventBus 事件 `ARTICLES_LOADED`，Activity 接收后调用 adapter.notifyItemRangeInserted

#### F10: 预缓冲方案

**核心思路**：VideoFragment 监听播放进度，进度超 80% 时预加载下一个文章的视频 URL，缓存到 VideoPlay，切换时直接使用。

**数据流**：
```
VideoFragment（当前视频播放中）
  │
  │ 定时轮询 player.currentTime / player.duration（每 5 秒）
  ▼
进度 > 80% && 下一个文章未预加载？
  │
  ├── 是 → 触发预加载
  │     ├── 获取 rssArticles[position+1]
  │     ├── 异步加载视频 URL（R5 抓取或 ruleContent 解析）
  │     ├── 缓存到 VideoPlay.preloadedVideoUrls[article.link] = videoUrl
  │     └── 标记已预加载 preloadedArticles.add(article.link)
  │
  └── 否 → 继续轮询
```

**切换时使用缓存**：
```
VideoPlay.switchToArticle(index, player)
  │
  ├── 检查 preloadedVideoUrls[article.link]
  │     ├── 有缓存 → 直接使用缓存的 videoUrl，跳过异步抓取
  │     │     └── player.setUp(cachedUrl) + startPlayLogic()
  │     └── 无缓存 → 正常异步加载（现有逻辑）
  └── 清理旧缓存（保留当前+下一个）
```

**关键设计**：
1. VideoPlay 新增 `preloadedVideoUrls: MutableMap<String, String>`（key=article.link, value=videoUrl）
2. VideoPlay 新增 `preloadedArticles: MutableSet<String>`（已预加载的文章link集合）
3. VideoFragment 新增进度监听 Coroutine（lifecycleScope，每 5 秒轮询）
4. 预加载复用 R5 VideoUrlExtractor.extract 或 Rss.getContent 逻辑
5. 缓存清理：switchToArticle 中清除非当前和非下一个的缓存

#### F11: 位置记忆方案

**核心思路**：VideoPlay 保存退出时的文章 link，RssArticlesFragment.onResume 检查并滚动到对应位置。

**数据流**：
```
VideoPlayerActivity.finish()
  │
  ├── VideoPlay.lastPlayedArticleLink = rssArticles?.getOrNull(rssArticleIndex)?.link
  └── super.finish()
  
  ↓（用户返回文章列表）

RssArticlesFragment.onResume()
  │
  ├── VideoPlay.lastPlayedArticleLink?.let { link ->
  │     ├── val articles = adapter.getItems()
  │     ├── val index = articles.indexOfFirst { it.link == link }
  │     ├── if (index >= 0) recyclerView.scrollToPosition(index)
  │     └── VideoPlay.lastPlayedArticleLink = null  ← 清除标记，避免每次onResume滚动
  └── （无标记则不滚动）
```

**关键设计**：
1. VideoPlay 新增 `lastPlayedArticleLink: String?` 字段
2. VideoPlayerActivity.finish() 中保存当前文章 link
3. RssArticlesFragment.onResume() 中检查并滚动
4. 滚动后清除标记（一次性，避免每次 onResume 都滚动）
5. 文章不在当前列表时（index<0）不滚动，仅清除标记

## 4. Requirements（需求）

### REQ-1：VideoPlay 新增字段

```kotlin
/** 订阅源文章列表（上下滑动切换文章，从 RssArticlesFragment 传入） **/
var rssArticles: List<RssArticle>? = null
/** 当前订阅源文章索引（上下滑动切换文章） **/
var rssArticleIndex: Int = 0
```

### REQ-2：VideoPlay 新增 switchToArticle 方法

```kotlin
fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    val articles = rssArticles ?: return false
    val article = articles.getOrNull(index) ?: return false
    rssArticleIndex = index
    // 更新 rssStar/rssRecord 以匹配新文章
    rssStar = appDb.rssStarDao.get(article.origin, article.link)
    if (rssStar == null) {
        rssRecord = appDb.rssReadRecordDao.getRecord(article.link, article.origin)
    }
    // 重置集数状态
    rssEpisodes = null
    rssRoutes = null
    rssEpisodeIndex = 0
    rssRouteIndex = 0
    videoTitle = article.title
    // 重新加载该文章的视频信息（复用 startPlay 的 RssSource 分支）
    startPlay(player)
    return true
}
```

### REQ-3：ReadRss.readRss 新增 rssArticles 参数

```kotlin
fun readRss(
    fragment: Fragment,
    rssArticle: RssArticle,
    rssSource: RssSource? = null,
    rssArticles: List<RssArticle>? = null  // 新增
)
```

在 type==2（视频播放）分支中，将 rssArticles 存入 VideoPlay 单例（通过 Intent extra 传递标记，initSource 后设置）。

### REQ-4：RssArticlesFragment 传递文章列表

`readRss(rssArticle)` 回调中，从 adapter 获取当前文章列表，传给 ReadRss.readRss。

### REQ-5：VideoPagerAdapter 基于 rssArticles 创建 Fragment

```kotlin
override fun getItemCount(): Int {
    val book = VideoPlay.book
    if (book != null) return 1
    if (VideoPlay.singleUrl) return 1
    // 新需求：优先基于 rssArticles 创建 Fragment
    val articles = VideoPlay.rssArticles
    return if (articles.isNullOrEmpty()) {
        // 兼容旧逻辑：无文章列表时基于 rssEpisodes
        val episodes = VideoPlay.rssEpisodes
        if (episodes.isNullOrEmpty()) 1 else episodes.size
    } else {
        articles.size
    }
}
```

### REQ-6：VideoFragment activatePlayer 适配

```kotlin
fun activatePlayer() {
    if (isActivated) return
    val pv = _playerView ?: return
    isActivated = true
    // ... setVideoAllCallBack ...
    if (VideoPlay.isResumeFromFloat) {
        // 悬浮窗恢复
    } else {
        val book = VideoPlay.book
        if (book != null) {
            VideoPlay.startPlay(pv)
        } else if (VideoPlay.rssArticles != null && !VideoPlay.rssArticles!!.isEmpty()) {
            // 新需求：基于文章列表切换文章
            VideoPlay.switchToArticle(articleIndex, pv)
        } else {
            // 旧逻辑：基于 rssEpisodes 切换集数
            val episodes = VideoPlay.rssEpisodes
            val episode = episodes?.getOrNull(articleIndex)
            if (episode != null) {
                VideoPlay.playRssEpisode(pv, episode)
            } else {
                VideoPlay.startPlay(pv)
            }
        }
    }
}
```

### REQ-7：VideoPlayerActivity onPageSelected 适配

```kotlin
override fun onPageSelected(position: Int) {
    super.onPageSelected(position)
    currentFragment?.deactivatePlayer()
    // 新需求：更新文章索引
    if (VideoPlay.rssArticles != null) {
        VideoPlay.rssArticleIndex = position
    } else {
        VideoPlay.rssEpisodeIndex = position
    }
    val fragment = getVideoFragment(position)
    currentFragment = fragment
    if (fragment?.playerView != null) {
        fragment.activatePlayer()
    }
    // 标题更新
    binding.titleBarNew.title = if (VideoPlay.rssArticles != null) {
        VideoPlay.rssArticles?.getOrNull(position)?.title ?: ""
    } else {
        VideoPlay.rssEpisodes?.getOrNull(position)?.title ?: VideoPlay.videoTitle ?: ""
    }
}
```

### REQ-8：集数选择器适配

切换文章后，VideoPlay.rssEpisodes 会更新为新文章的集数列表。VideoFragment 需要监听 `UP_VIDEO_INFO` 事件更新集数选择器。

### REQ-9：分页加载（阶段8）

**VideoPlay 新增字段**：
```kotlin
var rssSortName: String? = null           // 分类名称（分页加载用）
var rssSortUrl: String? = null            // 分类URL（分页加载用）
var rssNextPageUrl: String? = null        // 下一页URL（Rss.getArticles返回）
var rssArticlePage: Int = 1               // 当前页码
var rssArticlesHasMore: Boolean = true    // 是否还有更多文章
var isLoadingMoreArticles: Boolean = false // 防重复加载
```

**VideoPlay 新增方法**：
```kotlin
fun loadMoreArticles(): Boolean {
    if (isLoadingMoreArticles || !rssArticlesHasMore) return false
    val source = source as? RssSource ?: return false
    val pageUrl = rssNextPageUrl ?: return false
    val sortName = rssSortName ?: return false
    isLoadingMoreArticles = true
    Coroutine.async(loadScope, IO) {
        rssArticlePage++
        Rss.getArticles(loadScope, sortName, pageUrl, source, rssArticlePage, null)
            .onSuccess(IO) { (articles, newNextPageUrl) ->
                val oldSize = rssArticles?.size ?: 0
                (rssArticles as? MutableList)?.addAll(articles)
                    ?: run { rssArticles = (rssArticles ?: emptyList()) + articles }
                rssNextPageUrl = newNextPageUrl
                rssArticlesHasMore = articles.isNotEmpty() && !newNextPageUrl.isNullOrBlank()
                isLoadingMoreArticles = false
                val newSize = rssArticles?.size ?: 0
                postEvent(EventBus.ARTICLES_LOADED, oldSize to newSize)
            }.onError {
                isLoadingMoreArticles = false
                rssArticlePage--
                AppLog.put("分页加载文章失败", it, true)
            }
    }
    return true
}
```

**ReadRss.readRss 传递分页上下文**：
```kotlin
// RssArticlesFragment.readRss 中传递 sortName/sortUrl
VideoPlay.rssSortName = sortName
VideoPlay.rssSortUrl = sortUrl
VideoPlay.rssNextPageUrl = nextPageUrl  // 从 ViewModel 获取
VideoPlay.rssArticlePage = page          // 从 ViewModel 获取
```

**VideoPlayerActivity.onPageSelected 触发分页加载**：
```kotlin
override fun onPageSelected(position: Int) {
    // ...（现有逻辑）...
    // 阶段8：滑到最后一个时触发分页加载
    val articles = VideoPlay.rssArticles
    if (!articles.isNullOrEmpty() && position >= articles.size - 1) {
        VideoPlay.loadMoreArticles()
    }
}
```

**EventBus 新增事件**：`ARTICLES_LOADED`（key: `"artICLES_loaded"`）

**VideoPlayerActivity 接收事件**：
```kotlin
observeEvent(EventBus.ARTICLES_LOADED) { pair ->
    val (oldSize, newSize) = pair as Pair<Int, Int>
    videoPagerAdapter?.notifyItemRangeInserted(oldSize, newSize - oldSize)
}
```

### REQ-10：预缓冲（阶段8）

**VideoPlay 新增字段**：
```kotlin
/** 预加载的视频URL缓存（key=article.link, value=videoUrl） **/
val preloadedVideoUrls: MutableMap<String, String> = mutableMapOf()
/** 已预加载的文章link集合（避免重复预加载） **/
val preloadedArticles: MutableSet<String> = mutableSetOf()
```

**VideoPlay 新增方法**：
```kotlin
fun preloadNextArticleVideo(currentIndex: Int) {
    val articles = rssArticles ?: return
    val nextArticle = articles.getOrNull(currentIndex + 1) ?: return
    if (nextArticle.link in preloadedArticles) return
    val source = source as? RssSource ?: return
    preloadedArticles.add(nextArticle.link)
    Coroutine.async(loadScope, IO) {
        try {
            val videoUrl = extractVideoUrl(nextArticle, source)
            if (videoUrl != null) {
                preloadedVideoUrls[nextArticle.link] = videoUrl
            }
        } catch (e: Exception) {
            AppLog.put("预缓冲下一个视频失败", e)
            preloadedArticles.remove(nextArticle.link) // 失败时移除标记，允许重试
        }
    }.onError {
        preloadedArticles.remove(nextArticle.link)
    }
}

fun getCachedVideoUrl(articleLink: String): String? = preloadedVideoUrls[articleLink]
```

**VideoFragment 进度监听**：
```kotlin
private var progressMonitorJob: Job? = null

private fun startProgressMonitor() {
    progressMonitorJob?.cancel()
    progressMonitorJob = viewLifecycleOwner.lifecycleScope.launch {
        while (isActive) {
            delay(5000) // 每5秒检查一次
            val player = _playerView ?: continue
            val duration = player.duration
            val current = player.currentTime
            if (duration > 0 && current > 0) {
                val progress = current.toFloat() / duration.toFloat()
                if (progress >= 0.8f) {
                    // 进度超80%，触发预缓冲
                    VideoPlay.preloadNextArticleVideo(episodeIndex)
                    break // 已触发，停止监听
                }
            }
        }
    }
}

// 在 onPrepared 回调中启动监听
// 在 onDestroyView 中取消监听
```

**switchToArticle 使用缓存**：
```kotlin
fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean {
    // ...（现有逻辑）...
    val article = articles.getOrNull(index) ?: return false
    // 阶段8：检查预缓冲缓存
    val cachedUrl = preloadedVideoUrls[article.link]
    if (cachedUrl != null) {
        // 有缓存，直接使用
        videoUrl = cachedUrl
        videoTitle = article.title
        Coroutine.async(loadScope, Main) {
            player.setUp(cachedUrl, cachePlay, File(appCtx.externalCache, "exoplayer"), article.title)
            postEvent(EventBus.VIDEO_SUB_TITLE, article.title)
            if (autoPlay) player.startPlayLogic()
        }
        return true
    }
    // 无缓存，走正常异步加载（现有逻辑）
    // ...
}
```

### REQ-11：位置记忆（阶段8）

**VideoPlay 新增字段**：
```kotlin
/** 退出播放器时正在看的文章link（用于返回列表时定位） **/
var lastPlayedArticleLink: String? = null
```

**VideoPlayerActivity.finish() 保存位置**：
```kotlin
override fun finish() {
    // 阶段8：保存当前文章link用于位置记忆
    VideoPlay.lastPlayedArticleLink = VideoPlay.rssArticles
        ?.getOrNull(VideoPlay.rssArticleIndex)?.link
    // ...（现有清理逻辑）...
    super.finish()
}
```

**RssArticlesFragment.onResume() 滚动到位置**：
```kotlin
override fun onResume() {
    super.onResume()
    isResumed = true
    adapter.upResumed(isResumed)
    // 阶段8：位置记忆——从播放器返回时滚动到正在看的文章
    VideoPlay.lastPlayedArticleLink?.let { link ->
        VideoPlay.lastPlayedArticleLink = null // 清除标记，避免每次onResume滚动
        val articles = adapter.getItems()
        val index = articles.indexOfFirst { it.link == link }
        if (index >= 0) {
            binding.recyclerView.post {
                binding.recyclerView.smoothScrollToPosition(index)
            }
        }
    }
}
```

## 5. Scenarios（场景）

### 场景1：从文章列表启动播放器，上下滑动切换文章

```
前置：订阅源文章列表有 3 个视频文章 [A, B, C]
1. 用户点击文章 B → 进入播放器
2. 播放器加载文章 B 的视频（第一集）
3. 用户上滑 → ViewPager2 切换到文章 C
4. 文章 C 的视频自动加载播放
5. 用户下滑 → 切换回文章 B
```

### 场景2：文章内多集，通过集数选择器切换

```
前置：文章 A 有 3 集 [第1集, 第2集, 第3集]
1. 用户在播放器中观看文章 A 的第1集
2. 用户点击左下角集数选择器 → 选择第2集
3. 播放器切换到第2集（不触发 ViewPager2 滑动）
4. 用户上下滑动 → 切换到文章 B（不是切换集数）
```

### 场景3：文章内多线路，通过线路选择器切换

```
前置：文章 A 有 2 条线路 [线路1, 线路2]，每条线路有 3 集
1. 用户在播放器中观看文章 A 线路1 的第1集
2. 用户点击左下角线路选择器 → 选择线路2
3. 集数列表更新为线路2的集数
4. 播放器切换到线路2的第1集
```

### 场景4：从历史记录启动（无文章列表）

```
前置：用户从订阅源历史记录点击一个视频
1. ReadRss.readRss(activity, record) 启动播放器
2. rssArticles = null（无文章列表）
3. VideoPagerAdapter 走旧逻辑：单 Fragment 或基于 rssEpisodes
4. 上下滑动不切换文章（单 Fragment）或切换集数（rssEpisodes）
```

### 场景5：书源模式（不受影响）

```
前置：用户从书架打开一本视频书
1. VideoPlay.book != null
2. VideoPagerAdapter 返回 1（单 Fragment）
3. ViewPager2 禁用滑动
4. 本 spec 不影响书源模式
```

### 场景6：单URL模式（不受影响）

```
前置：用户通过 videoUrl 直接启动播放器
1. VideoPlay.singleUrl = true
2. VideoPagerAdapter 返回 1（单 Fragment）
3. ViewPager2 禁用滑动
4. 本 spec 不影响单URL模式
```

### 场景7：分页加载（阶段8）

```
前置：订阅源文章列表有 10 个视频文章（第一页），ruleNextPage 配置了分页规则
1. 用户在播放器中上下滑动，从文章 1 滑到文章 10（最后一个）
2. onPageSelected(9) 检测到 position >= rssArticles.size - 1
3. VideoPlay.loadMoreArticles() 异步请求第二页
4. 第二页返回 10 个新文章，追加到 rssArticles（现在有 20 个）
5. VideoPagerAdapter.notifyItemRangeInserted(10, 10)
6. 用户继续下滑，可以滑到文章 11-20
7. 如果第二页是最后一页（hasMore=false），滑到文章 20 不再触发加载
```

### 场景8：预缓冲（阶段8）

```
前置：用户正在观看文章 1 的视频，文章 2 是下一个视频
1. 视频开始播放，VideoFragment 启动进度监听（每5秒轮询）
2. 用户观看到视频 80% 处
3. 进度监听检测到 progress >= 0.8f
4. VideoPlay.preloadNextArticleVideo(0) 异步加载文章 2 的视频 URL
5. 视频 URL 加载完成，缓存到 preloadedVideoUrls["article2.link"]
6. 用户上滑切换到文章 2
7. switchToArticle(1) 检查缓存，发现 preloadedVideoUrls["article2.link"] 有值
8. 直接使用缓存的 URL 播放，无需异步等待
```

### 场景9：位置记忆（阶段8）

```
前置：用户在文章列表中点击文章 3 进入播放器，然后上下滑到文章 7
1. 用户在播放器中观看文章 7，按返回键退出
2. VideoPlayerActivity.finish() 保存 lastPlayedArticleLink = "article7.link"
3. 用户返回到 RssArticlesFragment
4. RssArticlesFragment.onResume() 检查 lastPlayedArticleLink
5. 在 adapter.getItems() 中查找 "article7.link"，找到索引 6
6. recyclerView.smoothScrollToPosition(6)
7. 清除 lastPlayedArticleLink = null
8. 用户看到列表滚动到文章 7 的位置
```
