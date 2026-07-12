# 视频播放完整链路

> 验证日期：2026-07-12（R3 多线路 + R5 自动抓取已更新）
> 源码文件：`ReadRss.kt`、`VideoPlay.kt`、`Exo2MediaPlayer.kt`、`ExoPlayerHelper.kt`、`VideoUrlExtractor.kt`
> 内置播放器内容规则编写指南：[../special-scenarios/video-audio.md](../special-scenarios/video-audio.md) 5.6 节

## 1. type 分流逻辑

> 源码：ReadRss.kt L25-73

| type 值 | 含义 | 处理方式 |
|---------|------|---------|
| 0 | 网页 | 打开 ReadRssActivity（WebView） |
| 1 | 图片 | 调用 readNoHtml → 用 ruleContent 解析图片 URL → PhotoDialog |
| 2 | 视频 | 直接跳转 VideoPlayerActivity，传 sourceKey + sourceType=rss + record=link |

## 2. type=2 视频播放完整链路

> ⚠️ 之前错误认为"type=2跳过ruleContent"，实际 VideoPlay.kt 会检查 ruleContent
> R5 增强：ruleContent 为空时不再直接用 link，而是自动抓取文章页面 HTML 提取视频 URL
> R3 增强：ruleContent 返回嵌套 JSON 时支持多线路解析

```
用户点击 type=2 的 RssArticle
  │
  ▼
ReadRss.readRss() [ReadRss.kt:63-70]
  │ type==2 → startActivity<VideoPlayerActivity>
  │   putExtra("sourceKey", rssArticle.origin)
  │   putExtra("sourceType", SourceType.rss)  // =1
  │   putExtra("record", rssArticle.link)
  │
  ▼
VideoPlayerActivity.onActivityCreated()
  │ VideoPlay.initSource(sourceKey, sourceType, bookUrl, record)
  │   → 从 DB 加载 RssSource
  │   → 从 DB 加载 rssStar / rssRecord
  │ VideoPlay.startPlay(playerView)
  │
  ▼
VideoPlay.startPlay() [VideoPlay.kt]
  │ source is RssSource
  │ ├─ ruleContent 为空?  → R5 自动抓取分支
  │ │   └─ VideoUrlExtractor.extract(html, rssArticle.link)
  │ │      先请求 rssArticle.link 获取页面 HTML
  │ │      五种方法按精确度提取视频URL：
  │ │        ① <video>/<source> 标签 src（jsoup，最精确）
  │ │        ② OG/Meta 标签 og:video
  │ │        ③ <script> 内 JSON 中的视频 URL
  │ │        ④ JS 变量赋值 var url="...m3u8"
  │ │        ⑤ 正则兜底匹配 .m3u8/.mp4 结尾 URL
  │ │      播放器页面 URL 自动解析（/player/?url=...m3u8 → 实际视频流）
  │ │      ├─ 单 URL → 注入 Referer → player.setUp(url)
  │ │      └─ 多 URL → 自动构建多集列表
  │ │
  │ └─ ruleContent 不为空?  → 规则解析分支
  │     └─ Rss.getContent(rssArticle, ruleContent, rssSource)
  │         → AnalyzeUrl(rssArticle.link) → 请求网页
  │         → AnalyzeRule.getString(ruleContent) → 提取正文 content
  │         → 正文处理（按优先级）:
  │            ├─ parseRssRoutes(content)  // R3 多线路（优先判定）
  │            │   嵌套 JSON [{"name":"线路1","episodes":[...]}] → List<RssRoute>
  │            │   判定：JSON数组首元素含 episodes 字段
  │            ├─ parseRssEpisodes(content)  // R1 多集
  │            │   ├─ JSON数组 [{"url":"...","title":"..."}] → List<RssEpisode>
  │            │   └─ 多行URL（每行 http/https/相对路径）→ List<RssEpisode>
  │            ├─ 以"<"开头 → 当作MPD文本，写入临时.mpd文件 → file:// URI
  │            └─ 单URL → NetworkUtils.getAbsoluteURL() → 视频URL
  │        → AnalyzeUrl(mUrl) → 解析headers → player.setUp(url)
  │
  ▼
Exo2MediaPlayer → ExoPlayer.Builder().build()
  → ResolvingDataSource.Factory(ExoPlayerHelper.cacheDataSourceFactory){ it }  // no-op resolver，不处理"🚧"
     → CacheDataSource(100M LRU缓存) + OkHttpDataSource
     → Header 通过 ExoPlayerHelper.setDefaultHeaders 注入到 okhttpDataFactory（ExoPlayerManager.initVideoPlayer 调用）
  → ExoPlayer.prepare() + playWhenReady
```

## 3. 关键结论

1. **type=2 + ruleContent 是合法组合**：当视频链接需要从详情页提取时，设置 type=2 + ruleContent
2. **ruleContent 为空时（R5 自动抓取）**：不再直接用 rssArticle.link，而是请求文章页面 HTML，用 VideoUrlExtractor 五种方法自动提取视频 URL（适用于视频 URL 嵌入在 HTML 中的场景）
3. **ruleContent 不为空时**：先用 Rss.getContent() 解析正文，再按优先级判定格式
4. **多线路格式（R3）**：ruleContent 返回嵌套 JSON `[{"name":"线路1","episodes":[...]}]` → 解析为 List<RssRoute>，左下角线路选择器切换
5. **多集格式（R1）**：ruleContent 返回 JSON 数组 `[{"url":"...","title":"..."}]` 或多行 URL → 解析为 List<RssEpisode>，左下角集数选择器切换
6. **正文以"<"开头**：当作 DASH MPD 文本，写入临时文件后播放
7. **单URL（向后兼容）**：不匹配上述格式时当作单个视频链接 URL，用 NetworkUtils.getAbsoluteURL() 处理相对路径
8. **ExoPlayer 缓存与 Header 注入**：100M LRU缓存，通过 OkHttpDataSource 请求。Header 注入有两种方式：①`ExoPlayerHelper.setDefaultHeaders(headers)` → `okhttpDataFactory.setDefaultRequestProperties(headers)`（ExoPlayerManager.initVideoPlayer 调用，**type=2 实际使用的方式**）；②"🚧"编码方式（ExoPlayerHelper.createMediaItem 生成 `url+"🚧"+JSON(headers)`，由 resolvingDataSource 拆分，但 Exo2MediaPlayer 使用 no-op resolver 不处理，**实际不生效**）。详见 [../special-scenarios/video-audio.md](../special-scenarios/video-audio.md) 5.6 节"常见问题"
9. **R5 Referer 注入**：自动抓取分支会注入 Referer（文章页面 URL），模拟 WebView 行为解决 CDN 防盗链 404

> **源作者编写指南**：ruleContent 四种格式（单URL/多行URL/JSON数组/嵌套JSON多线路）的完整说明详见 [../special-scenarios/video-audio.md](../special-scenarios/video-audio.md) 5.6 节
