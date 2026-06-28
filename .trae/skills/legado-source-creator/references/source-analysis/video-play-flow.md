# 视频播放完整链路

> 验证日期：2026-06-02
> 源码文件：`ReadRss.kt`、`VideoPlay.kt`、`Exo2MediaPlayer.kt`、`ExoPlayerHelper.kt`

## 1. type 分流逻辑

> 源码：ReadRss.kt L25-73

| type 值 | 含义 | 处理方式 |
|---------|------|---------|
| 0 | 网页 | 打开 ReadRssActivity（WebView） |
| 1 | 图片 | 调用 readNoHtml → 用 ruleContent 解析图片 URL → PhotoDialog |
| 2 | 视频 | 直接跳转 VideoPlayerActivity，传 sourceKey + sourceType=rss + record=link |

## 2. type=2 视频播放完整链路

> ⚠️ 之前错误认为"type=2跳过ruleContent"，实际 VideoPlay.kt 会检查 ruleContent

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
VideoPlay.startPlay() [VideoPlay.kt:129-287]
  │ source is RssSource
  │ ├─ ruleContent 为空?
  │ │   └─ 直接用 rssArticle.link 作为视频URL
  │ │      AnalyzeUrl(link) → 解析headers → player.setUp(url)
  │ │
  │ └─ ruleContent 不为空?
  │     └─ Rss.getContent(rssArticle, ruleContent, rssSource)
  │         → AnalyzeUrl(rssArticle.link) → 请求网页
  │         → AnalyzeRule.getString(ruleContent) → 提取正文
  │         → 正文处理:
  │            ├─ 以"<"开头 → 当作MPD文本，写入临时.mpd文件 → file:// URI
  │            └─ 否则 → NetworkUtils.getAbsoluteURL() → 视频URL
  │        → AnalyzeUrl(mUrl) → 解析headers → player.setUp(url)
  │
  ▼
Exo2MediaPlayer → ExoPlayer.Builder().build()
  → ResolvingDataSource.Factory(ExoPlayerHelper.cacheDataSourceFactory)
     → URL中含"🚧"则拆分URL+Headers
     → CacheDataSource(100M LRU缓存) + OkHttpDataSource
  → ExoPlayer.prepare() + playWhenReady
```

## 3. 关键结论

1. **type=2 + ruleContent 是合法组合**：当视频链接需要从详情页提取时，设置 type=2 + ruleContent
2. **ruleContent 为空时**：直接用 rssArticle.link 作为视频URL（适用于link本身就是m3u8/mp4链接的场景）
3. **ruleContent 不为空时**：先用 Rss.getContent() 解析正文获取真实视频URL
4. **正文以"<"开头**：当作 DASH MPD 文本，写入临时文件后播放
5. **正文不以"<"开头**：当作视频链接URL，用 NetworkUtils.getAbsoluteURL() 处理相对路径
6. **ExoPlayer 缓存**：100M LRU缓存，通过 OkHttpDataSource 请求，支持自定义 Headers（URL+"🚧"+JSON(headers) 编码方式）
