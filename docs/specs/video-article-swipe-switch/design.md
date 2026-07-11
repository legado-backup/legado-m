# design.md — 视频播放器上下滑动切换文章列表

## 1. Technical Approach（技术方案）

### 1.1 整体架构

```
RssArticlesFragment（文章列表）
  │
  │ readRss(rssArticle, rssSource, rssArticles)
  ▼
ReadRss（启动播放器 + 传递文章列表）
  │
  │ startActivity<VideoPlayerActivity> + Intent extras
  ▼
VideoPlayerActivity.onActivityCreated
  │
  ├── VideoPlay.initSource(sourceKey, sourceType, bookUrl, record)
  │     └── 加载点击的文章（rssStar/rssRecord）
  │
  └── switchToViewPagerMode()
        │
        ├── VideoPlay.rssArticles = intent extra 传递的文章列表
        ├── VideoPlay.rssArticleIndex = 点击的文章索引
        │
        ▼
  VideoPagerAdapter（基于 rssArticles.size 创建 Fragment）
        │
        │ createFragment(position) → VideoFragment.newInstance(position)
        ▼
  VideoFragment.activatePlayer()
        │
        ├── VideoPlay.rssArticles != null → VideoPlay.switchToArticle(position, player)
        │     └── 异步加载文章视频信息（ruleContent/R5自动抓取）
        │     └── postEvent(UP_VIDEO_INFO) 通知 UI 更新
        │
        └── VideoPlay.rssArticles == null → 旧逻辑（playRssEpisode）
```

### 1.2 文章列表传递机制

**问题**：RssArticle 含 content 字段可能很大，Intent extra 有约 1MB 大小限制。

**方案**：两层传递
1. **Intent extra 传递文章列表**（JSON 序列化）：适用于小列表
2. **VideoPlay 单例存储**（兜底）：大列表场景

**实际实现**：
- ReadRss.readRss 中将 rssArticles 通过 `VideoPlay.rssArticles` 直接设置（不通过 Intent）
- 因为 ReadRss 和 VideoPlay 都在同一个 App 进程，单例直接共享
- VideoPlayerActivity 启动后从 `VideoPlay.rssArticles` 读取

**注意**：VideoPlay 是全局单例，rssArticles 在进入播放器前设置，退出播放器后清理（防止内存泄漏）。

### 1.3 文章切换异步加载机制

```
VideoFragment.activatePlayer()
  │
  │ VideoPlay.switchToArticle(index, player)
  ▼
VideoPlay.switchToArticle
  │
  ├── 更新 rssArticleIndex
  ├── 更新 rssStar/rssRecord（匹配新文章）
  ├── 重置 rssEpisodes/rssRoutes/rssEpisodeIndex/rssRouteIndex
  ├── videoTitle = article.title
  └── startPlay(player)  ← 复用现有逻辑
        │
        ├── ruleContent 为空 → R5 自动抓取（VideoUrlExtractor.extract）
        │     └── 单URL / 多URL / 未找到 三个分支
        │
        └── ruleContent 不为空 → Rss.getContent + parseRssRoutes
              └── 多线路 / 单URL 分支
        │
        ▼
  postEvent(VIDEO_SUB_TITLE, title)  ← 标题更新
  postEvent(UP_VIDEO_INFO, arrayListOf(...))  ← 集数列表更新
  player.setUp(url, ...) + startPlayLogic()  ← 播放
```

### 1.4 集数选择器更新机制

切换文章后，VideoPlay.rssEpisodes 会更新为新文章的集数列表。VideoFragment 需要监听 `UP_VIDEO_INFO` 事件更新集数选择器。

**VideoPlayerActivity 中的事件监听**（已有，需适配）：
```kotlin
// 已有：observeEvent(UP_VIDEO_INFO) 更新多集列表
// 需适配：通知 currentFragment 更新集数选择器
```

**VideoFragment 新增方法**：
```kotlin
fun updateEpisodeSelector() {
    val episodes = VideoPlay.rssEpisodes
    if (episodes == null || episodes.isEmpty()) {
        rvEpisodes?.gone()
        return
    }
    rvEpisodes?.visible()
    updateEpisodeList()
    // 更新线路选择器
    updateRouteSelectorText()
    initRouteSelector()  // 重新初始化线路选择器
}
```

### 1.5 首次启动处理

从 RssArticlesFragment 点击文章 B（索引 1）进入播放器：
1. ReadRss.readRss 设置 `VideoPlay.rssArticles = [A, B, C]`
2. ReadRss.readRss 设置 `VideoPlay.rssArticleIndex = 1`（文章 B 的索引）
3. VideoPlayerActivity 启动 → initSource 加载文章 B（通过 record=article.link）
4. switchToViewPagerMode → ViewPager2.setCurrentItem(1, false)（定位到文章 B）
5. 第一个 Fragment（position=1）activatePlayer → switchToArticle(1, player)

**关键**：ViewPager2 初始位置需要设置为点击的文章索引，而非默认的 0。

### 1.6 分页加载机制（阶段8）

**问题**：VideoPlay.rssArticles 是内存快照，不会自动更新。滑到最后一个时需要异步加载下一页。

**方案**：VideoPlay 保存分页上下文，onPageSelected 触发加载，EventBus 通知 adapter 更新。

```
RssArticlesViewModel.loadMore 逻辑（现有）：
  Rss.getArticles(scope, sortName, pageUrl, source, page, searchKey)
    → (articles, nextPageUrl)
    → appDb.rssArticleDao.append(...)

VideoPlay.loadMoreArticles 逻辑（阶段8新增）：
  Rss.getArticles(loadScope, sortName, pageUrl, source, page, null)
    → (articles, newNextPageUrl)
    → rssArticles 追加 articles（内存操作，不写数据库）
    → postEvent(ARTICLES_LOADED, oldSize to newSize)
```

**关键区别**：
- RssArticlesViewModel.loadMore：文章存入数据库，通过 Flow 通知 UI
- VideoPlay.loadMoreArticles：文章追加到内存列表，通过 EventBus 通知 adapter

**adapter 更新方式**：
```kotlin
// FragmentStateAdapter 支持 notifyItemRangeInserted
videoPagerAdapter?.notifyItemRangeInserted(oldSize, newSize - oldSize)
// ViewPager2 自动创建新位置的 Fragment
```

**防重复加载**：
- `isLoadingMoreArticles` 标记：加载中时拒绝新请求
- `rssArticlesHasMore` 标记：无更多时拒绝请求
- `rssNextPageUrl` 为空时拒绝请求

### 1.7 预缓冲机制（阶段8）

**问题**：切换文章时需要异步加载视频 URL，有延迟。希望在当前视频快看完时预加载下一个。

**方案**：VideoFragment 进度监听 + VideoPlay 预加载缓存。

```
VideoFragment（播放中）
  │
  │ onPrepared → startProgressMonitor()
  ▼
进度监听 Coroutine（每5秒轮询）
  │
  │ progress = currentTime / duration
  ▼
progress >= 0.8f ?
  │
  ├── 是 → VideoPlay.preloadNextArticleVideo(currentIndex)
  │     │
  │     ├── 获取 rssArticles[currentIndex + 1]
  │     ├── 异步加载视频 URL（R5 VideoUrlExtractor.extract）
  │     └── 缓存到 preloadedVideoUrls[article.link]
  │
  └── 否 → 继续轮询

切换文章时：
  switchToArticle(index) 
    → 检查 preloadedVideoUrls[article.link]
    → 有缓存：直接 player.setUp(cachedUrl) + startPlayLogic()
    → 无缓存：正常异步加载（现有逻辑）
```

**预加载 URL 提取逻辑**：
- ruleContent 为空：使用 R5 VideoUrlExtractor.extract（获取文章页面 HTML → 提取视频 URL）
- ruleContent 不为空：使用 Rss.getContent（解析 ruleContent 获取视频 URL）

**缓存管理**：
- 预加载成功：preloadedVideoUrls[link] = url
- 预加载失败：preloadedArticles.remove(link)（允许重试）
- 切换文章后：清理非当前和非下一个的缓存（避免内存泄漏）

### 1.8 位置记忆机制（阶段8）

**问题**：用户在播放器中滑到文章 7 后退出，返回列表时列表仍在文章 3 的位置（点击进入时的位置）。

**方案**：VideoPlay 保存退出时的文章 link，RssArticlesFragment.onResume 检查并滚动。

```
VideoPlayerActivity.finish()
  │
  └── VideoPlay.lastPlayedArticleLink = rssArticles?.getOrNull(rssArticleIndex)?.link

用户返回 RssArticlesFragment
  │
  └── onResume()
        │
        ├── VideoPlay.lastPlayedArticleLink?.let { link ->
        │     ├── 在 adapter.getItems() 中查找 link
        │     ├── 找到：smoothScrollToPosition(index)
        │     └── 未找到：不滚动（文章可能在下一页，用户可手动下拉）
        │
        └── VideoPlay.lastPlayedArticleLink = null  ← 清除标记
```

**设计考量**：
- 一次性标记：滚动后清除 lastPlayedArticleLink，避免每次 onResume 都滚动
- 文章不在列表中：index<0 时不滚动（可能分页加载后才有），仅清除标记
- 使用 smoothScrollToPosition：平滑滚动，用户体验更好

## 2. Architecture Decisions（架构决策）

### ADR-1：VideoPlay 单例存储 rssArticles

**Y-Statement**：
- **Context**（上下文）：需要将文章列表从 RssArticlesFragment 传递到 VideoPlayerActivity/VideoFragment
- **Decision**（决策）：使用 VideoPlay 全局单例存储 rssArticles 列表
- **Consequences**（后果）：
  - 正面：无需 Intent 序列化大列表，避免大小限制；所有组件直接访问
  - 负面：VideoPlay 单例状态增加，退出播放器需清理 rssArticles 防止内存泄漏

### ADR-2：switchToArticle 复用 startPlay 逻辑

**Y-Statement**：
- **Context**：切换文章后需要加载该文章的视频信息
- **Decision**：新增 switchToArticle 方法，内部调用 startPlay 复用 RssSource 分支逻辑
- **Consequences**：
  - 正面：复用现有 ruleContent/R5/多线路解析逻辑，改动最小
  - 负面：startPlay 依赖 rssStar/rssRecord 获取 rssArticle，switchToArticle 需先更新这些字段

### ADR-3：VideoPagerAdapter 优先基于 rssArticles 创建 Fragment

**Y-Statement**：
- **Context**：ViewPager2 数据源需要从 rssEpisodes 切换为 rssArticles
- **Decision**：getItemCount 优先检查 rssArticles，为空时回退到 rssEpisodes（兼容旧逻辑）
- **Consequences**：
  - 正面：从历史记录启动（无 rssArticles）走旧逻辑，向后兼容
  - 负面：两套数据源逻辑增加复杂度，需文档清晰

### ADR-4：VideoFragment episodeIndex 语义变更

**Y-Statement**：
- **Context**：VideoFragment 的 episodeIndex 参数需支持文章索引
- **Decision**：保留 episodeIndex 参数名（避免破坏 newInstance 接口），语义上表示"当前 Fragment 在 ViewPager2 中的位置"
- **Consequences**：
  - 正面：newInstance 接口不变，VideoPagerAdapter 不需改
  - 负面：变量名 episodeIndex 在文章模式下表示文章索引，语义不完全准确

### ADR-5：ViewPager2 初始位置设置为点击的文章索引

**Y-Statement**：
- **Context**：用户点击文章列表中第 N 个文章进入播放器，ViewPager2 应定位到第 N 页
- **Decision**：switchToViewPagerMode 中 `binding.viewPager.setCurrentItem(VideoPlay.rssArticleIndex, false)`
- **Consequences**：
  - 正面：用户看到的是点击的文章，体验自然
  - 负面：ViewPager2 创建 Fragment 时会预创建相邻 Fragment（offscreenPageLimit=1）

### ADR-6：退出播放器清理 rssArticles

**Y-Statement**：
- **Context**（上下文）：VideoPlay.rssArticles 存储文章列表，退出播放器后不清理会导致内存泄漏
- **Decision**（决策）：VideoPlayerActivity.finish() 中清理 `VideoPlay.rssArticles = null`
- **Consequences**（后果）：
  - 正面：防止内存泄漏
  - 负面：从悬浮窗恢复时 rssArticles 已清空，无法上下滑动切换文章（可接受，悬浮窗模式不涉及文章切换）

### ADR-7：分页加载在 VideoPlay 中保存分页上下文（阶段8）

**Y-Statement**：
- **Context**（上下文）：视频播放器中滑到最后一个文章时需要加载下一页，但 VideoPlay.rssArticles 是内存快照，没有分页上下文
- **Decision**（决策）：VideoPlay 新增分页上下文字段（rssSortName/rssSortUrl/rssNextPageUrl/rssArticlePage/rssArticlesHasMore），loadMoreArticles 方法复用 Rss.getArticles 逻辑
- **Consequences**（后果）：
  - 正面：分页加载逻辑自包含在 VideoPlay 中，不依赖 RssArticlesViewModel
  - 负面：VideoPlay 单例状态增加（6个新字段）；分页上下文需要在 ReadRss.readRss 中从 ViewModel 传递

### ADR-8：预缓冲仅预加载 URL（阶段8）

**Y-Statement**：
- **Context**（上下文）：切换文章时异步加载视频 URL 有延迟，希望在当前视频快看完时预加载下一个
- **Decision**（决策）：仅预加载视频 URL（轻量级），不预缓冲完整视频流（避免多播放器实例管理复杂度）
- **Consequences**（后果）：
  - 正面：实现简单，不需要管理多个播放器实例；内存占用低（仅缓存 URL 字符串）
  - 负面：切换文章时仍需要 player.setUp + prepareAsync，但跳过了 URL 抓取的异步等待（节省最大延迟部分）

### ADR-9：位置记忆通过 VideoPlay 单例传递（阶段8）

**Y-Statement**：
- **Context**（上下文）：用户在播放器中滑到文章 7 后退出，返回列表时列表仍在点击时的位置（文章 3），需要滚动到文章 7
- **Decision**（决策）：VideoPlay 新增 lastPlayedArticleLink 字段，finish() 时保存，RssArticlesFragment.onResume() 检查并滚动
- **Consequences**（后果）：
  - 正面：利用已有 VideoPlay 单例，无需 Intent extra 或 EventBus；一次性标记避免每次 onResume 滚动
  - 负面：文章不在当前列表页时无法定位（index<0），需用户手动下拉加载更多（可接受，分页加载需求 F9 解决此问题）

## 3. Data Flow（数据流）

### 3.1 启动数据流

```
RssArticlesFragment.readRss(rssArticle)
  │
  │ 从 adapter 获取文章列表 rssArticles
  │ 找到 rssArticle 在列表中的索引
  ▼
ReadRss.readRss(fragment, rssArticle, rssSource, rssArticles)
  │
  │ VideoPlay.rssArticles = rssArticles
  │ VideoPlay.rssArticleIndex = index
  │ startActivity<VideoPlayerActivity> { putExtra("sourceKey", ...) ... }
  ▼
VideoPlayerActivity.onActivityCreated
  │
  │ VideoPlay.initSource(sourceKey, sourceType, bookUrl, record)
  │   └── 通过 record 加载点击的文章（rssStar/rssRecord）
  │
  │ switchToViewPagerMode()
  │   ├── VideoPagerAdapter(this)  ← getItemCount 基于 rssArticles.size
  │   ├── viewPager.setCurrentItem(VideoPlay.rssArticleIndex, false)
  │   └── 首个 Fragment activatePlayer → switchToArticle(articleIndex, player)
  ▼
VideoPlay.switchToArticle(articleIndex, player)
  │
  └── startPlay(player)  ← 异步加载文章视频信息
```

### 3.2 切换文章数据流

```
用户上下滑动 ViewPager2
  │
  ▼
VideoPlayerActivity.onPageSelected(newPosition)
  │
  ├── currentFragment.deactivatePlayer()  ← 暂停旧 Fragment
  ├── VideoPlay.rssArticleIndex = newPosition
  ├── currentFragment = getVideoFragment(newPosition)
  └── currentFragment.activatePlayer()
        │
        └── VideoPlay.switchToArticle(newPosition, player)
              │
              ├── 更新 rssStar/rssRecord
              ├── 重置 rssEpisodes/rssRoutes
              └── startPlay(player)  ← 异步加载
                    │
                    └── postEvent(UP_VIDEO_INFO)  ← 通知 UI 更新集数选择器
```

### 3.3 切换集数数据流（文章内）

```
用户点击左下角集数选择器 → 选择第 N 集
  │
  ▼
VideoFragment.updateEpisodeList() 回调
  │
  ├── VideoPlay.rssEpisodeIndex = N
  ├── VideoPlay.playRssEpisode(player, episodes[N])
  │     └── player.setUp(url) + startPlayLogic()
  └── 更新集数选择器选中状态
  （不触发 ViewPager2 滑动）
```

## 4. File Changes（文件变更清单）

### 4.1 核心修改文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 新增 rssArticles/rssArticleIndex 字段 + switchToArticle 方法 | P0 |
| `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` | readRss 新增 rssArticles 参数 + 设置到 VideoPlay 单例 | P0 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt` | readRss 回调传递文章列表 | P0 |
| `app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt` | getItemCount 优先基于 rssArticles | P0 |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | activatePlayer 适配 + updateEpisodeSelector 方法 | P0 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | onPageSelected 适配 + setCurrentItem + finish 清理 | P0 |

### 4.2 兼容性文件（可能需微调）

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `app/src/main/java/io/legado/app/ui/rss/article/BaseRssArticlesAdapter.kt` | 确认 getItems() 方法可用（获取文章列表） | P1 |

### 4.3 文档同步文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `app/src/main/assets/updateLog.md` | 追加用户可感知的变更说明 | P0 |
| `docs/specs/video-article-swipe-switch/tasks.md` | 任务清单 + AOAdapt 日志 | P0 |
| `docs/INDEX.md` | 添加本 spec 条目 | P1 |

### 4.4 各文件详细变更

#### VideoPlay.kt

```kotlin
// 新增字段（在 rssRoutes/rssRouteIndex 之后）
/** 订阅源文章列表（上下滑动切换文章，从 RssArticlesFragment 传入） **/
var rssArticles: List<RssArticle>? = null
/** 当前订阅源文章索引（上下滑动切换文章） **/
var rssArticleIndex: Int = 0

// 新增方法（在 switchRssRoute 方法附近）
/**
 * 切换到指定文章（上下滑动切换文章列表）
 * 更新 rssStar/rssRecord 匹配新文章，重置集数状态，复用 startPlay 加载视频信息
 *
 * @param index 文章在 rssArticles 中的索引
 * @param player 播放器实例
 * @return true 切换成功，false 切换失败（无文章列表或索引越界）
 */
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

#### ReadRss.kt

```kotlin
// 修改 readRss(fragment, rssArticle, rssSource) 方法签名
fun readRss(
    fragment: Fragment,
    rssArticle: RssArticle,
    rssSource: RssSource? = null,
    rssArticles: List<RssArticle>? = null  // 新增
) {
    val rssReadRecord = rssArticle.toRecord()
    fragment.viewLifecycleOwner.lifecycleScope.launch(IO) {
        appDb.rssReadRecordDao.insertRecord(rssReadRecord)
    }
    val type = rssArticle.type
    if (type == 0) {
        // web网页（不变）
        ...
        return
    }
    if (type == 2) {
        // 视频播放：设置文章列表到 VideoPlay 单例
        VideoPlay.rssArticles = rssArticles
        VideoPlay.rssArticleIndex = rssArticles?.indexOfFirst { it.link == rssArticle.link } ?: 0
        fragment.startActivity<VideoPlayerActivity> {
            putExtra("sourceKey", rssArticle.origin)
            putExtra("sourceType", SourceType.rss)
            putExtra("record", rssArticle.link)
            putExtra("videoTitle", rssArticle.title)
        }
        return
    }
    readNoHtml(fragment, rssArticle, rssSource, type)
}
```

#### RssArticlesFragment.kt

```kotlin
override fun readRss(rssArticle: RssArticle) {
    fullRefresh = false
    // 新需求：传递文章列表给播放器，支持上下滑动切换文章
    val rssArticles = (adapter as? RecyclerAdapter<RssArticle, *>)?.getItems() ?: emptyList()
    ReadRss.readRss(this, rssArticle, activityViewModel.rssSource, rssArticles)
}
```

#### VideoPagerAdapter.kt

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

#### VideoFragment.kt

```kotlin
// activatePlayer 适配
fun activatePlayer() {
    if (isActivated) return
    val pv = _playerView ?: return
    isActivated = true
    // ... setVideoAllCallBack（不变）...
    if (VideoPlay.isResumeFromFloat) {
        // 悬浮窗恢复（不变）
    } else {
        val book = VideoPlay.book
        when {
            book != null -> VideoPlay.startPlay(pv)
            // 新需求：基于文章列表切换文章
            !VideoPlay.rssArticles.isNullOrEmpty() -> {
                VideoPlay.switchToArticle(articleIndex, pv)
            }
            // 旧逻辑：基于 rssEpisodes 切换集数
            else -> {
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
}

// episodeIndex 语义变更注释
/** 当前 Fragment 在 ViewPager2 中的位置索引
 *  - 文章模式（rssArticles != null）：表示文章索引
 *  - 集数模式（rssEpisodes != null）：表示集数索引
 *  - 书源/单URL模式：固定为 0
 */
private val articleIndex: Int by lazy {
    arguments?.getInt(ARG_EPISODE_INDEX, 0) ?: 0
}

// 新增：更新集数选择器（文章加载完成后调用）
fun updateEpisodeSelector() {
    val episodes = VideoPlay.rssEpisodes
    if (episodes == null || episodes.isEmpty()) {
        rvEpisodes?.gone()
    } else {
        rvEpisodes?.visible()
        updateEpisodeList()
    }
    // 更新线路选择器
    val routes = VideoPlay.rssRoutes
    if (routes == null || routes.size <= 1) {
        tvRouteSelector?.gone()
    } else {
        tvRouteSelector?.visible()
        updateRouteSelectorText()
    }
    // 更新标题
    tvVideoTitle?.text = VideoPlay.videoTitle ?: ""
}
```

#### VideoPlayerActivity.kt

```kotlin
// switchToViewPagerMode 中添加 setCurrentItem
private fun switchToViewPagerMode() {
    // ...（不变）...
    binding.viewPager.apply {
        // ...（配置不变）...
        registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                currentFragment?.deactivatePlayer()
                // 新需求：根据数据源更新索引
                if (!VideoPlay.rssArticles.isNullOrEmpty()) {
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
                binding.titleBarNew.title = if (!VideoPlay.rssArticles.isNullOrEmpty()) {
                    VideoPlay.rssArticles?.getOrNull(position)?.title ?: ""
                } else {
                    VideoPlay.rssEpisodes?.getOrNull(position)?.title
                        ?: VideoPlay.videoTitle ?: ""
                }
            }
        })
    }
    // 新需求：定位到点击的文章
    if (!VideoPlay.rssArticles.isNullOrEmpty() && VideoPlay.rssArticleIndex > 0) {
        binding.viewPager.setCurrentItem(VideoPlay.rssArticleIndex, false)
    }
    // 标题
    binding.titleBarNew.title = VideoPlay.videoTitle ?: ""
}

// UP_VIDEO_INFO 事件监听适配（通知 currentFragment 更新集数选择器）
// 已有 observeEvent(EventBus.UP_VIDEO_INFO) { ... }
// 需在其中调用 currentFragment?.updateEpisodeSelector()

// finish 中清理 rssArticles
override fun finish() {
    // ...（现有逻辑）...
    // 新需求：清理文章列表防止内存泄漏
    if (VideoPlay.book == null && !VideoPlay.singleUrl) {
        VideoPlay.rssArticles = null
        VideoPlay.rssArticleIndex = 0
    }
    super.finish()
}
```

### 4.5 阶段8新增文件变更（分页加载 + 预缓冲 + 位置记忆）

| 文件 | 修改内容 | 需求 | 优先级 |
|------|---------|------|--------|
| `VideoPlay.kt` | 新增分页上下文字段(6个) + preloadedVideoUrls/preloadedArticles + lastPlayedArticleLink + loadMoreArticles() + preloadNextArticleVideo() + getCachedVideoUrl() | F9/F10/F11 | P0 |
| `ReadRss.kt` | readRss 传递 sortName/sortUrl/nextPageUrl/page 给 VideoPlay | F9 | P0 |
| `RssArticlesFragment.kt` | readRss 回调传递分页上下文 + onResume 位置记忆滚动 | F9/F11 | P0 |
| `VideoPlayerActivity.kt` | onPageSelected 触发分页加载 + ARTICLES_LOADED 事件监听 + finish 保存 lastPlayedArticleLink | F9/F11 | P0 |
| `VideoFragment.kt` | 进度监听 Coroutine + onPrepared 启动监听 + onDestroyView 取消监听 | F10 | P0 |
| `EventBus.kt` | 新增 ARTICLES_LOADED 事件常量 | F9 | P0 |
| `VideoPagerAdapter.kt` | （无需修改，notifyItemRangeInserted 由 Activity 调用） | - | - |

**阶段8 VideoPlay.kt 详细变更**：

```kotlin
// ==================== 阶段8：分页加载 + 预缓冲 + 位置记忆 ====================

// 分页加载上下文
var rssSortName: String? = null
var rssSortUrl: String? = null
var rssNextPageUrl: String? = null
var rssArticlePage: Int = 1
var rssArticlesHasMore: Boolean = true
var isLoadingMoreArticles: Boolean = false

// 预缓冲缓存
val preloadedVideoUrls: MutableMap<String, String> = mutableMapOf()
val preloadedArticles: MutableSet<String> = mutableSetOf()

// 位置记忆
var lastPlayedArticleLink: String? = null

// 分页加载方法
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
                val mutableList = rssArticles?.toMutableList() ?: mutableListOf()
                mutableList.addAll(articles)
                rssArticles = mutableList
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

// 预缓冲方法
fun preloadNextArticleVideo(currentIndex: Int) {
    val articles = rssArticles ?: return
    val nextArticle = articles.getOrNull(currentIndex + 1) ?: return
    if (nextArticle.link in preloadedArticles) return
    val source = source as? RssSource ?: return
    preloadedArticles.add(nextArticle.link)
    Coroutine.async(loadScope, IO) {
        try {
            val ruleContent = source.ruleContent
            val videoUrl = if (ruleContent.isNullOrBlank()) {
                // R5 抓取
                val pageAnalyzeUrl = AnalyzeUrl(nextArticle.link, source = source, ruleData = nextArticle)
                val res = pageAnalyzeUrl.getStrResponseAwait()
                val html = res.body ?: ""
                VideoUrlExtractor.extract(html, nextArticle.link).firstOrNull()
            } else {
                // ruleContent 解析
                Rss.getContent(loadScope, nextArticle, ruleContent, source)
                    .await()?.let { parseRssRoutes(it, nextArticle.link)?.firstOrNull()?.episodes?.firstOrNull()?.url }
            }
            if (videoUrl != null) {
                preloadedVideoUrls[nextArticle.link] = videoUrl
            }
        } catch (e: Exception) {
            AppLog.put("预缓冲下一个视频失败", e)
            preloadedArticles.remove(nextArticle.link)
        }
    }.onError {
        preloadedArticles.remove(nextArticle.link)
    }
}

fun getCachedVideoUrl(articleLink: String): String? = preloadedVideoUrls[articleLink]

// 清理预缓冲缓存（退出播放器时调用）
fun clearPreloadCache() {
    preloadedVideoUrls.clear()
    preloadedArticles.clear()
}
```

**阶段8 finish() 修改**：
```kotlin
override fun finish() {
    // 阶段8：保存位置记忆
    VideoPlay.lastPlayedArticleLink = VideoPlay.rssArticles
        ?.getOrNull(VideoPlay.rssArticleIndex)?.link
    // 阶段8：清理预缓冲缓存
    VideoPlay.clearPreloadCache()
    // 阶段8：清理分页上下文
    VideoPlay.rssSortName = null
    VideoPlay.rssSortUrl = null
    VideoPlay.rssNextPageUrl = null
    VideoPlay.rssArticlePage = 1
    VideoPlay.rssArticlesHasMore = true
    VideoPlay.isLoadingMoreArticles = false
    // 现有清理
    if (VideoPlay.book == null && !VideoPlay.singleUrl) {
        VideoPlay.rssArticles = null
        VideoPlay.rssArticleIndex = 0
    }
    super.finish()
}
```

## 5. 风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| VideoPlay 单例状态在切换文章时被重置导致旧 Fragment 播放异常 | 中 | 高 | deactivatePlayer 先暂停旧 Fragment，再 switchToArticle |
| 切换文章异步加载延迟导致用户看到空白画面 | 中 | 中 | 显示加载提示（VIDEO_SUB_TITLE 事件传递"正在加载..."） |
| rssArticles 列表很大导致内存压力 | 低 | 中 | 列表仅含 RssArticle 基本字段（不含 content），或过滤只传 type==2 的文章 |
| 从历史记录启动时 rssArticles=null 导致回退逻辑异常 | 低 | 高 | VideoPagerAdapter 兼容旧逻辑，无 rssArticles 时走 rssEpisodes |
| ViewPager2 预创建相邻 Fragment 导致异步加载冲突 | 中 | 中 | offscreenPageLimit=1，仅预创建1个；activatePlayer 中 isActivated 防重入 |
