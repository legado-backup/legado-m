# SA-5 视频播放模块深度分析

> 子代理：SA-5
> 对比范围：Archive（`temp/forks-comparison/legado-archive`）vs 本项目（当前仓库）
> 模块：视频播放器（GSYVideo + ExoPlayer + 弹幕 + UI + 视频 URL 提取）

## 1. 模块概述

### 1.1 模块定位

视频播放模块是 Legado 项目的核心扩展能力之一，承担三类业务：
- **书源视频**：通过 BookSource + WebBook 加载章节内容，播放视频 URL（含 DASH/MPD/HLS）
- **RSS 订阅源视频**：通过 RssSource + ruleContent 加载视频链接
- **单 URL 视频**：直接传入视频 URL 播放（如分享/外部唤起）

Archive README 自述："改进漫画和视频体验，强化漫画阅读控件、视频直达播放页和详情/目录信息展示"。

### 1.2 两边文件清单对比表（汇总）

| 类别 | Archive | 本项目 | 差异方向 |
|------|---------|--------|---------|
| ui/video 文件数 | 5 个 | 10 个 | 本项目多 5 个 |
| help/gsyVideo 文件数 | 10 个 | 10 个 | 文件数相同 |
| help/exoplayer 文件数 | 2 个 | 2 个 | 文件数相同 |
| help/video 文件数 | 0 个 | 1 个 | 本项目独有 |
| 视频模块总行数（不含 model/VideoPlay + Service） | 约 3563 行 | 约 7033 行 | 本项目多约 3470 行 |
| model/VideoPlay.kt | 626 行 | 1134 行 | 本项目多 508 行 |

### 1.3 核心差异一句话总结

**本项目视频模块已大幅领先 Archive**：本项目在 RSS 视频（多集多线路 + ViewPager2 文章切换 + 抖音风格沉浸式 + WebView 降级 + R5 多层 URL 嗅探 + 分页加载 + 预缓冲）、播放器稳定性（setMimeType 修复 3003 错误、SimpleCache 统一缓存）、控件交互（手势重构 + 设置面板）等方面做了系统性增强；Archive 仅在"视频书搜索结果预加载目录"这一处功能上独有，属于 Archive 唯一可借鉴点。

### 1.4 重要说明：本项目近期已对视频播放器做了大量优化

本项目已实现以下 video-* spec（Archive 均无）：
- **douyin-style-video-player**：抖音风格沉浸式竖屏视频播放器（VideoFragment 1317 行 + VideoPagerAdapter 46 行）
- **video-article-swipe-switch**：ViewPager2 + Fragment 切换文章（switchToArticle/loadMoreArticles/preloadNextArticleHtml 等）
- **video-control-visibility-enhancement**：控件显隐与缓冲条优化
- **video-gesture-overhaul**：手势交互重构（VideoPlayer.kt 中 requestDisallowInterceptTouchEvent 重写 + 静音切换 + 长按倍速等）
- **video-playback-issues-round1**：10 类视频问题修复（3003 错误/P3-1 ruleContent 校验/R5 多层降级等）
- **rss-video-player-enhancement**：R1 多集 + R3 多线路 + R5 自动嗅探（parseRssRoutes/parseRssEpisodes/VideoUrlExtractor）
- **app-stability-round2**：稳定性增强（SimpleCache 替代 GSY ProxyCacheManager + setMimeType + 嗅探超时缩短 + 正则严格过滤）

## 2. 文件清单对比

### 2.1 Archive 侧文件清单

| 文件路径 | 行数 | 用途 |
|---------|------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 973 | 视频播放主界面（无 ViewPager2） |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerViewModel.kt` | 94 | ViewModel（收藏/源刷新/按钮 JS） |
| `app/src/main/java/io/legado/app/ui/video/VideoBookPreloader.kt` | 90 | **Archive 独有**：搜索结果页预加载视频书目录 |
| `app/src/main/java/io/legado/app/ui/video/ChapterAdapter.kt` | 85 | 书源章节列表适配器 |
| `app/src/main/java/io/legado/app/ui/video/config/SettingsDialog.kt` | 161 | 设置对话框 |
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | 552 | GSY 视频播放器封装 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` | 74 | GSY 视频管理器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` | 277 | ExoPlayer 管理 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 131 | ExoPlayer → GSY MediaPlayer 桥接 |
| `app/src/main/java/io/legado/app/help/gsyVideo/FloatingPlayer.kt` | 170 | 悬浮播放器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/SwitchVideoAdapter.kt` | 24 | 切换视频适配器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | 73 | 倍速选择对话框 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceEpisodeDialog.kt` | 80 | 选集对话框 |
| `app/src/main/java/io/legado/app/help/gsyVideo/DanmakuAdapter.kt` | 77 | 弹幕适配器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/BiliDanmukuParser.kt` | 286 | B 站弹幕解析器 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 335 | ExoPlayer 工具类（SPLIT_TAG 拼接方案） |
| `app/src/main/java/io/legado/app/help/exoplayer/InputStreamDataSource.kt` | 81 | 输入流 DataSource |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 626 | 视频播放单例（无 RSS 多集/多线路/分页） |
| `app/src/main/java/io/legado/app/service/VideoPlayService.kt` | - | 视频播放前台服务 |

### 2.2 本项目侧文件清单

| 文件路径 | 行数 | 用途 |
|---------|------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 1513 | 视频播放主界面（ViewPager2 + 设置面板 + 多集多线路） |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerViewModel.kt` | 94 | ViewModel（与 Archive 完全相同） |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | 1317 | **本项目独有**：抖音风格视频 Fragment |
| `app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt` | 46 | **本项目独有**：ViewPager2 适配器 |
| `app/src/main/java/io/legado/app/ui/video/WebViewVideoPlayer.kt` | 269 | **本项目独有**：WebView 降级播放器 |
| `app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt` | 366 | **本项目独有**：综合设置面板 BottomSheet |
| `app/src/main/java/io/legado/app/ui/video/RssRouteAdapter.kt` | 82 | **本项目独有**：RSS 多线路选择器 |
| `app/src/main/java/io/legado/app/ui/video/RssEpisodeAdapter.kt` | 83 | **本项目独有**：RSS 多集选择器 |
| `app/src/main/java/io/legado/app/ui/video/ChapterAdapter.kt` | 83 | 书源章节列表适配器 |
| `app/src/main/java/io/legado/app/ui/video/config/SettingsDialog.kt` | 91 | 设置对话框（精简版） |
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | 802 | GSY 视频播放器封装（含 ViewPager2 兼容） |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` | 93 | GSY 视频管理器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` | 315 | ExoPlayer 管理 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 341 | ExoPlayer → GSY MediaPlayer 桥接 |
| `app/src/main/java/io/legado/app/help/gsyVideo/FloatingPlayer.kt` | 170 | 悬浮播放器（与 Archive 相同） |
| `app/src/main/java/io/legado/app/help/gsyVideo/SwitchVideoAdapter.kt` | 24 | 切换视频适配器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | 158 | 倍速选择对话框 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceEpisodeDialog.kt` | 80 | 选集对话框 |
| `app/src/main/java/io/legado/app/help/gsyVideo/DanmakuAdapter.kt` | 78 | 弹幕适配器 |
| `app/src/main/java/io/legado/app/help/gsyVideo/BiliDanmukuParser.kt` | 287 | B 站弹幕解析器（与 Archive 几乎相同） |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 261 | ExoPlayer 工具类（setMimeType 修复版） |
| `app/src/main/java/io/legado/app/help/exoplayer/InputStreamDataSource.kt` | 81 | 输入流 DataSource（与 Archive 相同） |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 399 | **本项目独有**：R5 视频 URL 嗅探器 |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 1134 | 视频播放单例（含 RSS 多集/多线路/分页/预缓冲） |
| `app/src/main/java/io/legado/app/service/VideoPlayService.kt` | - | 视频播放前台服务 |

### 2.3 独有/共有文件矩阵

| 文件 | Archive 有 | 本项目有 | 差异类型 |
|------|-----------|----------|---------|
| ui/video/VideoPlayerActivity.kt | ✅ | ✅ | 本项目重写（多 540 行） |
| ui/video/VideoPlayerViewModel.kt | ✅ | ✅ | 完全相同 |
| ui/video/ChapterAdapter.kt | ✅ | ✅ | 基本相同 |
| ui/video/config/SettingsDialog.kt | ✅ | ✅ | Archive 多 70 行（含本项目已迁移到 VideoSettingsPanel 的功能） |
| ui/video/VideoBookPreloader.kt | ✅ | ❌ | **Archive 独有** |
| ui/video/VideoFragment.kt | ❌ | ✅ | **本项目独有** |
| ui/video/VideoPagerAdapter.kt | ❌ | ✅ | **本项目独有** |
| ui/video/WebViewVideoPlayer.kt | ❌ | ✅ | **本项目独有** |
| ui/video/VideoSettingsPanel.kt | ❌ | ✅ | **本项目独有** |
| ui/video/RssRouteAdapter.kt | ❌ | ✅ | **本项目独有** |
| ui/video/RssEpisodeAdapter.kt | ❌ | ✅ | **本项目独有** |
| help/gsyVideo/VideoPlayer.kt | ✅ | ✅ | 本项目多 250 行（手势+静音+ViewPager2 兼容） |
| help/gsyVideo/ExoVideoManager.kt | ✅ | ✅ | 基本相同 |
| help/gsyVideo/ExoPlayerManager.kt | ✅ | ✅ | 本项目多 38 行 |
| help/gsyVideo/Exo2MediaPlayer.kt | ✅ | ✅ | 本项目多 210 行 |
| help/gsyVideo/FloatingPlayer.kt | ✅ | ✅ | 完全相同 |
| help/gsyVideo/SwitchVideoAdapter.kt | ✅ | ✅ | 完全相同 |
| help/gsyVideo/ChoiceSpeedDialog.kt | ✅ | ✅ | 本项目多 85 行 |
| help/gsyVideo/ChoiceEpisodeDialog.kt | ✅ | ✅ | 完全相同 |
| help/gsyVideo/DanmakuAdapter.kt | ✅ | ✅ | 基本相同 |
| help/gsyVideo/BiliDanmukuParser.kt | ✅ | ✅ | 基本相同（仅 1 行差异） |
| help/exoplayer/ExoPlayerHelper.kt | ✅ | ✅ | **重大差异**：本项目用 setMimeType 替代 SPLIT_TAG（行数反而少 74 行） |
| help/exoplayer/InputStreamDataSource.kt | ✅ | ✅ | 完全相同 |
| help/video/VideoUrlExtractor.kt | ❌ | ✅ | **本项目独有** |
| model/VideoPlay.kt | ✅ | ✅ | 本项目多 508 行（RSS 多集/多线路/分页/预缓冲/R5 降级） |
| service/VideoPlayService.kt | ✅ | ✅ | 基本相同 |

## 3. 核心文件深度对比

### 3.1 VideoPlay 实体对比（model/VideoPlay.kt）

#### 字段对比表

| 字段名 | Archive | 本项目 | 差异说明 |
|--------|---------|--------|---------|
| `videoPrefs`/`autoPlay`/`startFull`/`longPressSpeed`/`fullBottomProgressBar` | ✅ | ✅ | 基本配置相同 |
| `cachePlay` | ✅（boolean 开关） | ✅（@Deprecated 始终返回 false，ExoPlayer SimpleCache 接管） | **本项目废弃**：用 SimpleCache 替代 GSY ProxyCacheManager |
| `videoCacheSize` | ❌ | ✅ | **本项目独有**：视频缓存容量可配置（50/100/200/500MB） |
| `muteOnStart` | ❌ | ✅ | **本项目独有**：默认静音播放 |
| `videoSkipTime` | ❌ | ✅ | **本项目独有**：快进快退时间（秒，默认 60） |
| `danmakuSpeed`/`lockCurScreen`/`isPortraitVideo` | ✅ | ✅ | 相同 |
| `currentPlayHeaders` | ❌ | ✅ | **本项目独有**：当前播放 Headers，供 WebView 降级复用 |
| `playerType` | ❌ | ✅ | **本项目独有**：播放器类型选择（AUTO/EXO_PLAYER/WEB_VIEW） |
| `isResumeFromFloat` | ❌ | ✅ | **本项目独有**：从悬浮窗恢复标志 |
| `rssStar`/`rssRecord` | ✅ | ✅ | 相同 |
| `rssEpisodes`/`rssEpisodeIndex` | ❌ | ✅ | **本项目独有**：R1 多集选择播放 |
| `rssRoutes`/`rssRouteIndex` | ❌ | ✅ | **本项目独有**：R3 多线路支持 |
| `rssArticles`/`rssArticleIndex` | ❌ | ✅ | **本项目独有**：上下滑动切换文章 |
| `rssSortName`/`rssSortUrl`/`rssNextPageUrl`/`rssArticlePage`/`rssArticlesHasMore`/`isLoadingMoreArticles` | ❌ | ✅ | **本项目独有**：阶段8 分页加载 |
| `preloadedHtmls`/`preloadedArticles`/`lastPlayedArticleLink` | ❌ | ✅ | **本项目独有**：阶段8 预缓冲 |
| `chapterLinkCache`/`CachedPlayLink`/`preloadingKeys`/`preloadMutex` | ✅ | ❌ | **Archive 独有**：章节链接缓存（TTL 30 分钟） |

#### Archive 独有字段

- `chapterLinkCache: ConcurrentHashMap<String, CachedPlayLink>`：章节链接缓存
- `CachedPlayLink(playUrl, headers, mediaUrl, createdAt)`：缓存项数据类
- `preloadingKeys: ConcurrentHashMap.newKeySet<String>()`：预加载防重入集合
- `preloadMutex: Mutex`：预加载互斥锁
- `CHAPTER_LINK_CACHE_TTL = 30 * 60 * 1000L`：缓存 TTL 30 分钟

#### 本项目独有字段

- 视频 URL 提取与降级（`currentPlayHeaders`、`playerType`、`isResumeFromFloat`）
- RSS 多集多线路（`rssEpisodes`、`rssEpisodeIndex`、`rssRoutes`、`rssRouteIndex`）
- RSS 文章切换（`rssArticles`、`rssArticleIndex`）
- 分页加载（`rssSortName`、`rssSortUrl`、`rssNextPageUrl`、`rssArticlePage`、`rssArticlesHasMore`、`isLoadingMoreArticles`）
- 预缓冲（`preloadedHtmls`、`preloadedArticles`、`lastPlayedArticleLink`）
- 视频缓存配置（`videoCacheSize`、`muteOnStart`、`videoSkipTime`）

#### 方法对比

| 方法名 | Archive | 本项目 | 差异说明 |
|--------|---------|--------|---------|
| `startPlay` | ✅ 简单分支（singleUrl/Rss/Book） | ✅ 含 R5 多层降级 + 预缓冲 HTML 优先 + Referer 注入 + isStrictVideoUrl 校验 | **重大差异** |
| `parseRssEpisodes` | ❌ | ✅ | **本项目独有**：解析 ruleContent 为多集列表（JSON 数组/多行 URL） |
| `parseRssRoutes` | ❌ | ✅ | **本项目独有**：解析为多线路列表（嵌套 JSON） |
| `switchRssRoute` | ❌ | ✅ | **本项目独有**：切换线路 |
| `playRssEpisode` | ❌ | ✅ | **本项目独有**：播放指定集 |
| `upRssEpisodeIndex` | ❌ | ✅ | **本项目独有**：上一集/下一集 |
| `switchToArticle` | ❌ | ✅ | **本项目独有**：切换文章（上下滑动） |
| `loadMoreArticles` | ❌ | ✅ | **本项目独有**：分页加载下一页文章 |
| `preloadNextArticleHtml` | ❌ | ✅ | **本项目独有**：预缓冲下一文章 HTML |
| `clearPreloadCache` | ❌ | ✅ | **本项目独有**：清理预缓冲缓存 |
| `isValidVideoContentUrl` | ❌ | ✅ | **本项目独有**：ruleContent 返回 URL 有效性校验 |
| `buildChapterCacheKey` | ✅ | ❌ | **Archive 独有**：构建章节缓存键 |
| `preloadNextEpisode` | ✅ | ❌ | **Archive 独有**：预加载下一集链接 |
| `initSource` | 同步函数 | suspend + withContext(IO) | **本项目改造**：异步化避免主线程阻塞 |
| `saveRead` | ✅ 含 ReadRecentBook/ReadRecordWidgetStore | ❌ 无 ReadRecentBook/ReadRecordWidgetStore | **Archive 多**：最近阅读记录写入 |

### 3.2 GSYVideo 封装对比（help/gsyVideo/VideoPlayer.kt）

#### 关键类对比

| 项目 | Archive | 本项目 |
|------|---------|--------|
| 类定义 | `class VideoPlayer: StandardGSYVideoPlayer` | 同上 |
| 总行数 | 552 行 | 802 行 |
| 字段 `playSpeed` | `private` | `internal`（供 VideoFragment 访问） |
| 字段 `ivMute`/`isMuted` | ❌ | ✅ 静音图标和状态 |
| 字段 `isMutedPublic` | ❌ | ✅ 暴露静音状态 |
| 字段 `tipView`/`isChanging`/`isLongPressSpeed` | ✅ | ❌（本项目用其他方式实现） |
| `requestDisallowInterceptTouchEvent` 重写 | ❌ | ✅ 文章模式阻止 GSY 拦截，让 ViewPager2 检测垂直滑动 |
| `toggleMute` 方法 | ❌ | ✅ 切换静音状态+图标 |

#### 方法对比

- 本项目新增 `requestDisallowInterceptTouchEvent` 重写：解决 GSY 阻止 ViewPager2 垂直滑动冲突
- 本项目新增 `toggleMute`/`updateMuteIcon`：静音切换（与默认静音配置配套）
- 本项目 `playSpeed` 改为 `internal` 可见性，供 VideoFragment 长按倍速恢复原速
- Archive 保留 `tipView`/`isChanging`/`isLongPressSpeed` 字段，长按倍速实现路径不同

### 3.3 ExoPlayer 封装对比（help/exoplayer/ExoPlayerHelper.kt）

**这是重大差异点**：

| 项目 | Archive | 本项目 |
|------|---------|--------|
| `createMediaItem` 实现 | `url + SPLIT_TAG + GSON.toJson(headers)` 拼接到 URI | `setMimeType(getMimeType(url))` + headers 通过 `setDefaultHeaders` 注入 |
| 总行数 | 335 行 | 261 行 |
| 3003 错误（UnrecognizedInputFormatException） | 频发（SPLIT_TAG 拼接导致 ExoPlayer 误判类型） | 已修复（setMimeType 替代 SPLIT_TAG） |
| 缓存机制 | GSY ProxyCacheManager 代理缓存（对 m3u8/header 不兼容） | ExoPlayer SimpleCache（统一接管，含 CacheDataSource） |
| import | 含 `DataSpec`/`CacheWriter`/`ContentMetadata`/`MD5Utils`/`isJsonArray` | 含 `MimeTypes`/`NetworkUtils` |
| `MediaRequest` 类 | ✅ | ❌（本项目用 `setDefaultHeaders` 直接注入） |

#### 重大发现：3003 错误根因

Archive `ExoPlayerHelper.createMediaItem` 用 SPLIT_TAG（🚧）将 headers JSON 拼接到 URL 后缀，ExoPlayer 看到 URL 含 `.json` 后缀（headers JSON 内容含 `{` 等），误判为非视频文件，用 `ProgressiveExtractor` 解析 m3u8 抛出 `UnrecognizedInputFormatException`（错误码 3003）。本项目用 `setMimeType` 显式指定 MIME 类型，避免类型推断误判。

### 3.4 视频 UI 对比

#### VideoPlayerActivity 对比

| 项目 | Archive | 本项目 |
|------|---------|--------|
| 总行数 | 973 行 | 1513 行 |
| ViewPager2 集成 | ❌ | ✅（77 处相关引用） |
| VideoFragment 嵌入 | ❌ | ✅ |
| VideoPagerAdapter | ❌ | ✅ |
| WebViewVideoPlayer 降级 | ❌ | ✅ |
| VideoSettingsPanel（BottomSheet） | ❌ | ✅ |
| RssEpisode/RssRoute 多集多线路 UI | ❌ | ✅ |
| ArrayAdapter/AlertDialog 下拉选择 | ❌ | ✅ |
| PooledWebView 集成 | ✅ | ✅（两边都有） |
| SourceLoginActivity 集成 | ✅ | ✅ |
| BookInfoViewModel/ChangeBookSourceDialog | ✅ | ❌（本项目未集成换源） |

#### 播放界面差异

- **Archive**：单 Activity 嵌入单一 VideoPlayer，无滑动切换，无设置面板 BottomSheet
- **本项目**：ViewPager2 + VideoFragment 抖音风格沉浸式，多状态切换（PURE/NORMAL/FULLSCREEN），BottomSheet 综合设置面板

### 3.5 弹幕对比（BiliDanmukuParser.kt）

两边弹幕解析器几乎完全相同（286 行 vs 287 行，仅 1 行差异）。`DanmakuAdapter.kt` 也基本相同。Archive 没有弹幕相关的额外增强，本项目也没有改动弹幕解析逻辑。

## 4. Archive 视频增强功能详解

### 4.1 视频书搜索结果预加载（VideoBookPreloader.kt）

- **具体实现**：在搜索结果页/发现页加载书籍列表时，并发预加载视频书的目录到数据库
- **代码位置**：
  - `app/src/main/java/io/legado/app/ui/video/VideoBookPreloader.kt`（90 行）
  - 调用点1：`app/src/main/java/io/legado/app/ui/book/search/SearchViewModel.kt`（第 46 行 `onSearchSuccess` 回调）
  - 调用点2：`app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt`（第 3441 行发现页加载完成后）
- **技术方案**：
  - 使用 `Semaphore(4)` 限制最大并发预加载数（DEFAULT_MAX_PRELOAD=4）
  - 使用 `ConcurrentHashMap.newKeySet<String>()` 防止重复预加载（key=`origin|bookUrl`）
  - 预加载流程：
    1. 过滤非视频书（`source.bookSourceType != video && (searchBook.type and BookType.video) <= 0` 跳过）
    2. 检查目录是否已存在（已存在跳过）
    3. 如 `tocUrl` 为空，先调用 `WebBook.getBookInfoAwait` 获取书籍信息
    4. 调用 `WebBook.getChapterListAwait` 获取目录
    5. 写入数据库（`bookChapterDao.insert`）
    6. 未在书架的书自动打 `BookType.notShelf` 标记
  - 异常处理：`CancellationException` 重抛，其他 Throwable 记录日志
- **用户价值**：用户在搜索/发现页点击视频书进入播放页时，目录已就绪，无需等待网络请求，秒进选集列表

### 4.2 章节链接缓存与下一集预加载（VideoPlay.kt）

- **具体实现**：缓存书源视频章节的播放链接（playUrl + headers + mediaUrl），TTL 30 分钟；播放当前集时异步预加载下一集链接
- **代码位置**：`app/src/main/java/io/legado/app/model/VideoPlay.kt`（Archive 版本第 65-75 行字段定义 + 第 286-377 行 `preloadNextEpisode` 方法）
- **技术方案**：
  - `chapterLinkCache: ConcurrentHashMap<String, CachedPlayLink>`：缓存键为 `source.getKey()|book.bookUrl|chapter.url`
  - `preloadingKeys: ConcurrentHashMap.newKeySet<String>()`：防重入
  - `preloadMutex: Mutex`：预加载互斥锁
  - `CHAPTER_LINK_CACHE_TTL = 30 * 60 * 1000L`：30 分钟 TTL
  - 缓存命中时直接复用（跳过 WebBook.getContent 网络请求）
  - 当前集播放成功后，异步预加载下一集（`episodes?.getOrNull(chapterInVolumeIndex + 1)`）
- **用户价值**：换集时秒切（缓存命中），首集播放时后台预加载第二集链接

### 4.3 视频直达播放页

Archive README 提到"视频直达播放页"，但从代码分析看，本项目已通过 `VideoPlayerActivity` + `VideoPlayService` 实现等效能力（外部唤起 / RSS 文章点击 / 书架点击均直达播放页）。Archive 没有额外的"直达"实现，此项与本项目持平。

### 4.4 详情/目录信息展示

Archive README 提到"详情/目录信息展示"，对应 Archive `SettingsDialog.kt`（161 行 vs 本项目 91 行）多出的 70 行。Archive 把更多设置项放在 SettingsDialog 中，本项目则拆分到 `VideoSettingsPanel.kt`（366 行 BottomSheet）+ `SettingsDialog.kt`（91 行）。两边在功能上等价，本项目 UI 更现代化。

## 5. 本项目视频增强功能（Archive 没有的）

### 5.1 抖音风格沉浸式竖屏播放器

- **对应 spec**：douyin-style-video-player
- **代码位置**：
  - `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt`（1317 行）
  - `app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt`（46 行）
- **核心特性**：
  - ViewPager2 + FragmentStateAdapter 垂直滑动切换
  - 三种播放状态：PURE（纯净态）/ NORMAL（竖屏常态）/ FULLSCREEN（横屏全屏）
  - 双指拉伸触发全屏（scaleFactor > 1.2）
  - 横屏视频自动显示全屏按钮
  - 单击切换控件显隐

### 5.2 ViewPager2 文章切换 + 分页加载 + 预缓冲

- **对应 spec**：video-article-swipe-switch + 阶段8 分页加载
- **代码位置**：`VideoPlay.kt` 第 887-1018 行（`switchToArticle`/`loadMoreArticles`/`preloadNextArticleHtml`/`clearPreloadCache`）
- **核心特性**：
  - 上下滑动切换 RSS 文章（每个文章一个 VideoFragment）
  - 滑到最后一个文章自动触发分页加载（`Rss.getArticles` 复用）
  - 当前视频播放进度 > 80% 时预缓冲下一文章 HTML
  - 预缓冲 HTML 缓存跳过最大延迟部分（网络请求）

### 5.3 R1 多集 + R3 多线路 + R5 自动嗅探

- **对应 spec**：rss-video-player-enhancement
- **代码位置**：
  - `VideoPlay.kt` 第 739-857 行（`parseRssEpisodes`/`parseRssRoutes`/`switchRssRoute`）
  - `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`（399 行）
  - `app/src/main/java/io/legado/app/ui/video/RssRouteAdapter.kt`（82 行）
  - `app/src/main/java/io/legado/app/ui/video/RssEpisodeAdapter.kt`（83 行）
- **核心特性**：
  - ruleContent 返回 JSON 数组/多行 URL/嵌套 JSON 自动解析为多集/多线路
  - ruleContent 为空时启动 R5 多层嗅探：
    - 第一层：静态 HTML 解析（5 种方法：video/source 标签、OG/Meta、script JSON、JS 变量、正则）
    - 第二层：WebView 网络抓包（fetch/XHR/MediaSource hook）
    - 第三层：正则兜底（isStrictVideoUrl 严格过滤）
    - 第四层：回退文章链接交 ExoPlayer
  - Header 注入（Referer 防盗链）

### 5.4 手势交互重构 + 静音切换

- **对应 spec**：video-gesture-overhaul + video-control-visibility-enhancement
- **代码位置**：`help/gsyVideo/VideoPlayer.kt` 第 65-80 行（`requestDisallowInterceptTouchEvent` 重写 + `toggleMute`）
- **核心特性**：
  - 文章模式阻止 GSY 调用 `parent.requestDisallowInterceptTouchEvent(true)`，确保 ViewPager2 能检测垂直滑动
  - 静音切换方法 `toggleMute` + 图标更新
  - 长按倍速恢复原速（`playSpeed` 改为 internal 供 VideoFragment 访问）

### 5.5 10 类问题修复（3003 错误 / P3-1 ruleContent 校验 / 嗅探超时等）

- **对应 spec**：video-playback-issues-round1 + app-stability-round2
- **代码位置**：
  - `help/exoplayer/ExoPlayerHelper.kt`（setMimeType 替代 SPLIT_TAG）
  - `VideoPlay.kt` 第 784-788 行（`isValidVideoContentUrl` 校验）
  - `VideoPlay.kt` 第 95-105 行（`cachePlay` @Deprecated + SimpleCache 接管）
- **核心修复**：
  - 3003 错误：setMimeType 替代 SPLIT_TAG 拼接（避免 ExoPlayer 类型误判）
  - P3-1：ruleContent 返回 HTML 时校验长度/标签，降级 R5 嗅探
  - SimpleCache 替代 GSY ProxyCacheManager（对 m3u8/header 兼容）
  - 嗅探超时从 15s 缩短为 10s
  - 正则 isStrictVideoUrl 严格过滤（避免抓到 ?url= 参数页面）

### 5.6 WebView 降级播放器

- **对应 spec**：app-stability-round2 P0
- **代码位置**：`app/src/main/java/io/legado/app/ui/video/WebViewVideoPlayer.kt`（269 行）
- **核心特性**：
  - ExoPlayer 失败时（HLS SPS 错误/UnrecognizedInputFormatException/HlsPlaylistStuckException）降级到 WebView
  - 使用 assets/hls_video_player_template.html 模板（HLS.js + 进度条 + 倍速 + 全屏 + 横竖屏 + 上下集 + 错误重试）
  - 支持 Headers 注入（防盗链 Referer）
  - ViewPager2 兼容：pause()/resume()/release() 供 Fragment 生命周期调用
  - 垂直滑动检测（恢复 ViewPager2 上下切换文章能力）

### 5.7 综合设置面板 BottomSheet

- **代码位置**：`app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt`（366 行）
- **核心特性**：
  - 播放控制：快进快退 / 画面比例 / 音轨选择
  - 播放信息：播放地址展示+复制 / 视频简介
  - 功能菜单：悬浮窗 / 其他播放器 / 编辑源 / 登录 / 日志 / 调试
  - 播放设置：自动播放 / 直接全屏 / 底部进度条 / 静音 / 长按倍速 / 快进快退时间 / 缓存大小

## 6. 差异清单（编号化）

| # | 差异点 | Archive 实现 | 本项目实现 | 影响等级 |
|---|--------|------------|-----------|---------|
| VIDEO-001 | 视频书搜索结果预加载目录 | ✅ VideoBookPreloader（Semaphore 限流 + 异步预加载 + 数据库写入） | ❌ 无 | 中 |
| VIDEO-002 | 章节链接缓存（书源视频） | ✅ chapterLinkCache（TTL 30 分钟 + ConcurrentHashMap） | ❌ 无（仅有 RSS 文章 HTML 预缓冲） | 中 |
| VIDEO-003 | 下一集链接预加载（书源） | ✅ preloadNextEpisode（Mutex 保护 + WebBook.getContentAwait） | ❌ 无 | 中 |
| VIDEO-004 | ExoPlayer MediaItem headers 注入 | ❌ SPLIT_TAG 拼接到 URI（3003 错误根因） | ✅ setMimeType + setDefaultHeaders | 高 |
| VIDEO-005 | 视频缓存机制 | GSY ProxyCacheManager 代理缓存（对 m3u8 不兼容） | ExoPlayer SimpleCache（统一接管） | 高 |
| VIDEO-006 | RSS 多集选择播放 | ❌ | ✅ R1 parseRssEpisodes + RssEpisodeAdapter | 高 |
| VIDEO-007 | RSS 多线路支持 | ❌ | ✅ R3 parseRssRoutes + switchRssRoute + RssRouteAdapter | 高 |
| VIDEO-008 | RSS 自动视频链接嗅探 | ❌ | ✅ R5 VideoUrlExtractor（5 种方法 + 4 层降级） | 高 |
| VIDEO-009 | ViewPager2 文章切换 | ❌ | ✅ switchToArticle + VideoFragment + VideoPagerAdapter | 高 |
| VIDEO-010 | 分页加载下一页文章 | ❌ | ✅ loadMoreArticles（Rss.getArticles 复用） | 中 |
| VIDEO-011 | 预缓冲下一文章 HTML | ❌ | ✅ preloadNextArticleHtml（80% 进度触发） | 中 |
| VIDEO-012 | WebView 降级播放 | ❌ | ✅ WebViewVideoPlayer（HLS.js 模板） | 高 |
| VIDEO-013 | 抖音风格沉浸式 UI | ❌ | ✅ VideoFragment 三种状态 + 双指全屏 | 高 |
| VIDEO-014 | 综合设置面板 BottomSheet | ❌（仅 SettingsDialog） | ✅ VideoSettingsPanel（366 行 BottomSheet） | 中 |
| VIDEO-015 | 手势交互重构（ViewPager2 兼容） | ❌ | ✅ requestDisallowInterceptTouchEvent 重写 | 高 |
| VIDEO-016 | 静音切换 | ❌ | ✅ toggleMute + isMutedPublic + muteOnStart 配置 | 中 |
| VIDEO-017 | ruleContent 返回 URL 有效性校验 | ❌ | ✅ isValidVideoContentUrl（长度/标签/协议校验） | 高 |
| VIDEO-018 | Referer 防盗链注入 | ❌ | ✅ 自动注入 Referer（CDN 防盗链 404 修复） | 高 |
| VIDEO-019 | 播放器类型选择 | ❌ | ✅ playerType（AUTO/EXO_PLAYER/WEB_VIEW） | 中 |
| VIDEO-020 | 视频缓存容量可配置 | ❌ | ✅ videoCacheSize（50/100/200/500MB） | 低 |
| VIDEO-021 | 快进快退时间可配置 | ❌ | ✅ videoSkipTime（默认 60 秒） | 低 |
| VIDEO-022 | 悬浮窗恢复标志 | ❌ | ✅ isResumeFromFloat（Fragment.activatePlayer 据此决定 clonePlayState） | 中 |
| VIDEO-023 | 最近阅读记录写入 | ✅ ReadRecentBook + ReadRecordWidgetStore | ❌（saveRead 未写入最近阅读） | 低 |
| VIDEO-024 | initSource 异步化 | ❌ 同步函数（可能阻塞主线程） | ✅ suspend + withContext(IO) | 中 |
| VIDEO-025 | 倍速选择对话框 | 基础版（73 行） | 增强版（158 行，多 85 行） | 低 |
| VIDEO-026 | Exo2MediaPlayer 桥接 | 基础版（131 行） | 增强版（341 行，多 210 行） | 中 |
| VIDEO-027 | 换源对话框集成 | ✅ ChangeBookSourceDialog | ❌ 未集成 | 低 |
| VIDEO-028 | 弹幕解析器 | ✅ 286 行 | ✅ 287 行 | 无（基本相同） |

## 7. 借鉴决策（三态：借鉴/不借鉴/待评估）

### 7.1 建议借鉴（Borrow）

| # | 项目 | 收益评分(1-5) | 风险评分(1-5) | 实施复杂度 | 优先级 |
|---|------|-------------|-------------|-----------|--------|
| B-001 | VIDEO-001 视频书搜索结果预加载目录 | 4 | 1 | 低（90 行独立 object，调用点仅 2 处） | 中 |
| B-002 | VIDEO-002 + VIDEO-003 章节链接缓存 + 下一集预加载 | 4 | 2 | 中（需改造 VideoPlay.startPlay，加 ConcurrentHashMap + Mutex） | 中 |

**借鉴理由**：
- **B-001**：Archive 独有功能，本项目完全缺失。搜索视频书时秒进选集列表，用户体验提升明显。代码独立，无侵入风险。
- **B-002**：本项目有 RSS 文章 HTML 预缓冲，但书源视频章节链接缓存缺失。换集秒切是高价值场景。Archive 实现成熟（TTL 30 分钟 + Mutex 防重入 + ConcurrentHashMap 线程安全），可直接移植。

### 7.2 不建议借鉴（Skip）

| # | 项目 | 不借鉴理由 |
|---|------|-----------|
| S-001 | VIDEO-004 SPLIT_TAG 拼接方案 | 本项目已用 setMimeType 修复 3003 错误，Archive 方案是 Bug 根因 |
| S-002 | VIDEO-005 GSY ProxyCacheManager 代理缓存 | 本项目已用 SimpleCache 替代，Archive 方案对 m3u8/header 不兼容 |
| S-003 | VIDEO-023 最近阅读记录写入 | 本项目可能有其他机制处理最近阅读，需进一步核实（与 ReadRecentBook 实体是否已存在相关） |
| S-004 | VIDEO-027 换源对话框集成 | 视频换源场景低频，且本项目未实现 ChangeBookSourceDialog 集成，引入成本高 |

### 7.3 待评估（Evaluate）

| # | 项目 | 评估要点 |
|---|------|---------|
| E-001 | VIDEO-023 最近阅读记录 | 需核实本项目是否已有 ReadRecentBook/ReadRecordWidgetStore 实体；若已有，仅需在 VideoPlay.saveRead 中加 2 行调用即可，收益高成本低 |
| E-002 | VIDEO-025 倍速选择对话框增强 | 需对比两边 ChoiceSpeedDialog 具体差异（85 行差距），确认增强点是否对本项目有用 |
| E-003 | VIDEO-026 Exo2MediaPlayer 桥接增强 | 需对比两边 Exo2MediaPlayer 具体差异（210 行差距），可能含稳定性修复，价值待评估 |

## 8. 重大发现

### 8.1 本项目视频模块已大幅领先 Archive

本项目视频模块总行数 7033 行（不含 VideoPlay.kt 1134 行 + VideoPlayService.kt），Archive 仅 3563 行。本项目比 Archive 多约 3470 行代码，全部为本项目新增的 RSS 多集多线路、ViewPager2 文章切换、抖音风格沉浸式、WebView 降级、R5 多层嗅探、分页加载、预缓冲、手势重构、设置面板等系统性增强。Archive 在这些方面完全空白。

### 8.2 Archive 唯一可借鉴点是视频书预加载

Archive 在视频模块上唯一领先本项目的是 `VideoBookPreloader.kt`（搜索结果页预加载视频书目录）和 `VideoPlay.kt` 中的章节链接缓存机制（`chapterLinkCache` + `preloadNextEpisode`）。这两项都是"预加载提速"思路，与本项目已有的"RSS 文章 HTML 预缓冲"是同一设计哲学的不同应用场景。建议借鉴这两项，填补本项目"书源视频预加载"的空白。

### 8.3 Archive ExoPlayerHelper 存在已知 Bug

Archive `ExoPlayerHelper.createMediaItem` 用 SPLIT_TAG 拼接 headers JSON 到 URL 后缀，会导致 ExoPlayer 类型推断误判（看到 `.json` 后缀用 ProgressiveExtractor 解析 m3u8），抛出 3003 错误。本项目已用 `setMimeType` 修复。**若借鉴 Archive 其他视频功能，需注意避免引入 SPLIT_TAG 方案**。

### 8.4 弹幕模块两边完全等价

`BiliDanmukuParser.kt` 和 `DanmakuAdapter.kt` 两边几乎完全相同，无差异可借鉴。说明弹幕解析是 Legado 上游共享代码，两边都未做改动。

### 8.5 视频缓存机制代际差异

Archive 仍在使用 GSY ProxyCacheManager 代理缓存（已知对 m3u8/header URL 不兼容会导致播放失败），本项目已全面切换到 ExoPlayer SimpleCache（CacheDataSource + LeastRecentlyUsedCacheEvictor + 可配置容量）。这是代际差异，Archive 方案属于已废弃路径。

## 9. 引用源码位置

### 9.1 Archive 侧源码

- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\video\VideoBookPreloader.kt`（90 行，**Archive 独有**）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\video\VideoPlayerActivity.kt`（973 行）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\video\config\SettingsDialog.kt`（161 行）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\help\gsyVideo\VideoPlayer.kt`（552 行）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\help\exoplayer\ExoPlayerHelper.kt`（335 行，SPLIT_TAG 方案）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\VideoPlay.kt`（626 行，含 chapterLinkCache + preloadNextEpisode）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\search\SearchViewModel.kt`（第 46 行调用 VideoBookPreloader）
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\main\explore\ExploreFragment.kt`（第 3441 行调用 VideoBookPreloader）

### 9.2 本项目侧源码

- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\VideoFragment.kt`（1317 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\VideoPagerAdapter.kt`（46 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\WebViewVideoPlayer.kt`（269 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\VideoSettingsPanel.kt`（366 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\RssRouteAdapter.kt`（82 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\RssEpisodeAdapter.kt`（83 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\video\VideoPlayerActivity.kt`（1513 行）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\gsyVideo\VideoPlayer.kt`（802 行）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\exoplayer\ExoPlayerHelper.kt`（261 行，setMimeType 修复版）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\video\VideoUrlExtractor.kt`（399 行，**本项目独有**）
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\VideoPlay.kt`（1134 行，含 RSS 多集/多线路/分页/预缓冲/R5 降级）

### 9.3 关键方法位置

- Archive `preloadNextEpisode`：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/VideoPlay.kt:335-377`
- Archive `buildChapterCacheKey`：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/VideoPlay.kt:331-333`
- 本项目 `parseRssRoutes`：`app/src/main/java/io/legado/app/model/VideoPlay.kt:801-857`
- 本项目 `switchToArticle`：`app/src/main/java/io/legado/app/model/VideoPlay.kt:887-912`
- 本项目 `loadMoreArticles`：`app/src/main/java/io/legado/app/model/VideoPlay.kt:924-968`
- 本项目 `preloadNextArticleHtml`：`app/src/main/java/io/legado/app/model/VideoPlay.kt:982-1008`
- 本项目 `isValidVideoContentUrl`：`app/src/main/java/io/legado/app/model/VideoPlay.kt:784-788`
