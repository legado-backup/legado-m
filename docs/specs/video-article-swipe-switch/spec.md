# spec.md — 视频播放器上下滑动切换文章列表

## 1. Intent（意图）

订阅源内置视频播放器当前只支持播放单个文章的视频。用户在文章列表中点击视频文章进入播放器后，如果想看列表中下一个视频文章，必须返回列表重新选择。

**用户原文**：
> "还记得我之前给你提的需求不？订阅源内置视频播放器支持上下滑动，主要是滑动后切换加载当前资源列表对应上下的视频资源进行播放"

**用户选择**：
> "两者结合"——上下滑动切换文章(rssArticles)，文章内集数通过其他手势或选择器切换

**目标**：上下滑动切换文章列表中的视频文章，文章内多集通过左下角集数选择器切换。

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

### Out of Scope

| # | 排除项 | 原因 |
|---|--------|------|
| O1 | 书源模式文章切换 | 书源有自己的章节体系（toc/episodes），不涉及 rssArticles |
| O2 | 单URL模式文章切换 | singleUrl 只有一个视频链接，无需切换 |
| O3 | 跨订阅源切换 | 仅限当前文章列表内切换，不跨源 |
| O4 | 文章列表分页加载 | 仅传递已加载的文章列表，不在播放器内分页 |
| O5 | R3 控件显隐逻辑变更 | 本 spec 不修改 R3 已实现的控件显隐/手势逻辑 |

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
| D3 | rssArticles 列表可能很大（分页加载后） | 列表存储在 VideoPlay 单例（内存），不持久化 |
| D4 | 从历史记录启动无 rssArticles | 兼容旧逻辑：rssArticles=null 时单 Fragment |

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
