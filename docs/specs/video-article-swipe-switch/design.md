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
- **Context**：VideoPlay.rssArticles 存储文章列表，退出播放器后不清理会导致内存泄漏
- **Decision**：VideoPlayerActivity.finish() 中清理 `VideoPlay.rssArticles = null`
- **Consequences**：
  - 正面：防止内存泄漏
  - 负面：从悬浮窗恢复时 rssArticles 已清空，无法上下滑动切换文章（可接受，悬浮窗模式不涉及文章切换）

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

## 5. 风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| VideoPlay 单例状态在切换文章时被重置导致旧 Fragment 播放异常 | 中 | 高 | deactivatePlayer 先暂停旧 Fragment，再 switchToArticle |
| 切换文章异步加载延迟导致用户看到空白画面 | 中 | 中 | 显示加载提示（VIDEO_SUB_TITLE 事件传递"正在加载..."） |
| rssArticles 列表很大导致内存压力 | 低 | 中 | 列表仅含 RssArticle 基本字段（不含 content），或过滤只传 type==2 的文章 |
| 从历史记录启动时 rssArticles=null 导致回退逻辑异常 | 低 | 高 | VideoPagerAdapter 兼容旧逻辑，无 rssArticles 时走 rssEpisodes |
| ViewPager2 预创建相邻 Fragment 导致异步加载冲突 | 中 | 中 | offscreenPageLimit=1，仅预创建1个；activatePlayer 中 isActivated 防重入 |
