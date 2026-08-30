# Design: App Stability Round 2 修复

## Technical Approach

本轮修复遵循"最小侵入、源头规避"原则，针对 5 个残留问题分别采用针对性方案：

1. **Bug#5**：SQL 查询裁剪字段，从数据源头规避 CursorWindow 溢出
2. **Bug#3**：图片文件头前置检测，从入口规避误解密
3. **Bug#4**：显式 MIME 类型声明 + headers 预设，从创建源头规避类型识别失败
4. **P2-1**：Cronet 初始化排查，必要时降级 OkHttp
5. **P2-2**：生命周期主动 cancel + 超时缩短，规避协程残留

所有修复遵循项目编码规范：协程用 runCatching + CancellationException 重抛、日志用 AppLog.put / Log.d、错误处理有日志覆盖。

## Architecture Decisions

### AD-01: flowByOriginSort 查询去掉 description 字段

- Context: RssArticleDao.flowByOriginSort 查询返回 description 字段，部分订阅源 description 含大段 HTML/base64，单行超 CursorWindow 2MB 限制。R4.3 已去掉 content 字段，但 description 仍残留。原注释声称"列表使用 description"。
- Concern: SQLiteBlobTooBigException 导致订阅文章列表无法加载（22 次 Row too big requiredPos=4 totalRows=5 错误，RssArticleDao_Impl.java:417）
- Decision: 从 flowByOriginSort 查询中移除 description 字段。经核实 RssArticlesAdapter.convert（L54-97）仅使用 title/pubDate/image/read/origin，不使用 description，原注释为错误信息。
- Goal: 消除 SQLiteBlobTooBigException，列表流畅加载
- Tradeoff: flowByOriginSort 返回的 RssArticle 对象 description 字段为默认值（空）；详情页通过 get(origin, link, sort) 单独查询完整字段，不受影响
- Status: Proposed

### AD-02: 图片解密增加文件头检测

- Context: ImageUtils 两个 decode 方法存在校验缺陷。decode(ByteArray)（L24-51）块校验有漏洞（块对齐≠已加密），decode(InputStream)（L53-87）完全无校验。未加密图片（如 logo.png）被强制解密触发 IllegalBlockSizeException（32 次 DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH）。
- Concern: 未加密图片加载失败，日志污染严重
- Decision: 两个 decode 方法都增加图片文件头检测。读取前 4 字节匹配标准图片格式头（PNG:89 50 4E 47 / JPG:FF D8 FF / GIF:47 49 46 38 / WebP:52 49 46 46），匹配则跳过解密返回原数据。decode(InputStream) 用 mark/reset 读取前几字节后回退。
- Goal: 未加密图片不再触发 IllegalBlockSizeException，加密图片仍正常解密
- Tradeoff: 非标准头图片格式（AVIF/HEIF）无法识别仍会尝试解密；当前书源生态以 PNG/JPG/GIF/WebP 为主，可接受
- Status: Proposed

### AD-03: createMediaItem 不拼 SPLIT_TAG，改用 setMimeType

- Context: ExoPlayerHelper.createMediaItem（L50-54）将 SPLIT_TAG + headers JSON 拼接到 MediaItem.uri。DefaultMediaSourceFactory 在 ResolvingDataSource 之前根据 uri 后缀检测类型，看到带 SPLIT_TAG 后缀的 uri 误判 m3u8 为普通文件，用 ProgressiveExtractor 解析失败（3003 UnrecognizedInputFormatException）。
- Concern: m3u8/mpd 流媒体视频无法播放
- Decision: createMediaItem 不再拼接 SPLIT_TAG 到 uri，保持 uri 纯净。改为：(1) 根据 url 后缀显式 setMimeType（.m3u8→APPLICATION_M3U8 / .mpd→APPLICATION_MPD / .mp4→VIDEO_MP4 等）(2) headers 通过 setDefaultHeaders 注入（R5 已实现 L150-152）。保留 ResolvingDataSource 兼容旧调用，但主路径走新方案。
- Goal: m3u8/mpd 流媒体正常播放，不再触发 3003
- Tradeoff: 需维护 url 后缀→MIME 映射表；映射表小（m3u8/mpd/mp4/flv 等），维护成本低
- Status: Proposed

### AD-04: Cronet/DNS 高频失败排查

- Context: 日志显示 Cronet 请求失败 protocol=unknown httpCode=-1 error=System error，DNS negative cache hit，共 3287 次。根因待查，可能是 Cronet 未正确初始化。
- Concern: 大量网络请求失败，影响书源/订阅源加载
- Decision: 排查 Cronet 初始化逻辑。若 Cronet 不稳定，禁用 Cronet 直接用 OkHttp。
- Goal: 消除 protocol=unknown 错误，网络请求稳定
- Tradeoff: 禁用 Cronet 失去 HTTP/3/QUIC 性能优势；稳定性优先，OkHttp 已满足需求
- Status: Proposed

### AD-05: 协程取消异常优化

- Context: VideoPlayerActivity.onDestroy 时 VideoUrlExtractor Job 未主动 cancel，JobCancellationException 在 onDestroy:1475 抛出（60 次）。BackstageWebView 嗅探超时 15s 过长，TimeoutCancellationException 频发（BackstageWebView.kt:501）。
- Concern: 视频退出卡顿，日志污染
- Decision: (1) VideoPlayerActivity.onDestroy 主动 cancel VideoUrlExtractor Job (2) 嗅探超时从 15s 缩短为 8-10s
- Goal: 消除协程取消异常，视频退出流畅
- Tradeoff: 嗅探超时缩短可能导致部分慢源站嗅探失败；8-10s 仍足够，15s 太长
- Status: Proposed

### AD-06: 视频链接自动抓取流程优化（正则优先级后移）

- Context: 用户反馈"内置视频播放器用户不填写内容规则全部交给你去抓取时，正则抓出来的都是非视频链接，正则可以往后放一放"。经核实 `VideoUrlExtractor.kt`（L291-313）：`isVideoUrl`（L307-313）过滤条件过宽，包含 `?url=`/`&url=`/`?playurl=`/`&playurl=`，把任意带 url 参数的非视频页面链接（分享页/跳转页/广告）当视频链接；`extractByRegex`（L291-300）通过 `isVideoUrl` 过滤后抓到这些伪视频链接。`VideoPlay.kt`（L265-337）`extract` 命中（size≥1）→ 直接播放，不再触发更准确的 `extractWithWebView` 嗅探，播放器拿到非视频链接播放失败。
- Concern: 用户不填内容规则全交给 App 抓取时，视频播放失败（伪视频链接阻塞嗅探）
- Decision: (1) 收紧 `isVideoUrl`：去掉 `?url=`/`&url=`/`?playurl=`/`&playurl=` 过宽条件，只保留真实视频流特征（.m3u8/.mp4/format=m3u8/type=m3u8）。播放器页面 URL 由 `extractPlayerPageUrl` 在精确方法结果中解析（已有逻辑）。(2) `extract` 拆分：新增 `extractPrecise`（标签/Meta/JSON/JS变量，高可信度），`extractByRegex` 正则兜底独立。(3) VideoPlay 流程调整：extractPrecise 命中 → 播放（高可信度）；extractPrecise 未命中 → extractWithWebView 嗅探（动态抓包最准确）；嗅探失败 → extractByRegex 正则兜底（兜底的兜底）；正则兜底也失败 → 回退文章链接。
- Goal: 自动抓取到真实视频流链接，正则兜底不再阻塞嗅探
- Tradeoff: extractPrecise 未命中时必走嗅探（3-15s），首屏略慢于正则直接命中；但准确性大幅提升，且嗅探失败仍有正则兜底
- Status: Proposed

## Data Flow

### Bug#4 ExoPlayer 类型检测流程（修复后）

```
用户点击播放视频
        ↓
createMediaItem(url, headers) 被调用
        ↓
┌─────────────────────────────────────────┐
│ 1. 解析 url 后缀                        │
│ 2. setMimeType 根据后缀声明 MIME 类型    │
│    .m3u8 → APPLICATION_M3U8             │
│    .mpd  → APPLICATION_MPD              │
│    .mp4  → VIDEO_MP4                    │
│ 3. setUri(url)  ← 不拼 SPLIT_TAG        │
│ 4. setDefaultHeaders(headers) 注入 headers │
└─────────────────────────────────────────┘
        ↓
ExoPlayer.setMediaItem(mediaItem)
        ↓
DefaultMediaSourceFactory 根据 MIME 类型选择 MediaSource
        ↓
┌─────────────────────────────────────────┐
│ APPLICATION_M3U8 → HlsMediaSource       │
│ APPLICATION_MPD  → DashMediaSource       │
│ VIDEO_MP4        → ProgressiveMediaSource│
└─────────────────────────────────────────┘
        ↓
HlsMediaSource 通过 okhttpDataFactory 请求
        ↓
okhttpDataFactory 已预设 headers（setDefaultRequestProperties）
        ↓
视频正常播放
```

### Bug#3 图片解密判断流程（修复后）

```
Glide 加载图片
        ↓
ImageUtils.decode 被调用
        ↓
┌──────────────────────────────────────┐
│ 1. getRuleJs 获取解密规则             │
│ 2. 规则为空 → 返回原数据（不解密）    │
│ 3. 规则非空 → 进入文件头检测          │
└──────────────────────────────────────┘
        ↓
文件头检测
        ↓
┌──────────────────────────────────────────┐
│ 读取前 4 字节                            │
│ 89 50 4E 47 → PNG  → 跳过解密，返回原数据 │
│ FF D8 FF    → JPG  → 跳过解密，返回原数据 │
│ 47 49 46 38 → GIF  → 跳过解密，返回原数据 │
│ 52 49 46 46 → WebP → 跳过解密，返回原数据 │
│ 其他        → 进入解密路径                │
└──────────────────────────────────────────┘
        ↓
解密路径
        ↓
┌──────────────────────────────────────┐
│ evalJS 执行解密规则                   │
│ 成功 → 返回解密后数据                  │
│ 失败 → AppLog.put 记录，返回 null      │
│ CancellationException → 重抛          │
└──────────────────────────────────────┘
        ↓
Glide 显示图片
```

### Bug#5 订阅文章列表加载流程（修复后）

```
用户进入订阅源文章列表
        ↓
ReadRssViewModel.flowByOriginSort(origin, sort)
        ↓
RssArticleDao.flowByOriginSort 查询
        ↓
┌──────────────────────────────────────────┐
│ SELECT t1.link, t1.sort, t1.origin,      │
│        t1.`order`, t1.title,             │
│        t1.image, t1.`group`, t1.pubDate, │
│        t1.variable, t1.type, t1.durPos, │
│        ifNull(t2.read, 0) as read        │
│ FROM rssArticles t1                      │
│ LEFT JOIN rssReadRecords t2              │
│   ON t1.link = t2.record                 │
│ WHERE t1.origin = ? AND t1.sort = ?      │
│ ORDER BY `order` DESC                    │
│ ← 不查询 description 字段                │
└──────────────────────────────────────────┘
        ↓
单行数据 < 2MB，不超 CursorWindow 限制
        ↓
RssArticlesAdapter.convert 显示列表
        ↓
┌──────────────────────────────────────┐
│ tvTitle.text = item.title             │
│ tvPubDate.text = item.pubDate         │
│ imageView = item.image（Glide 加载）   │
│ ← 不使用 description                  │
└──────────────────────────────────────┘
        ↓
列表正常显示
```

### P1-4 视频链接自动抓取流程（修复后）

```
用户点击播放视频（ruleContent 为空）
        ↓
VideoPlay.kt 调用 extractPrecise(html, baseUrl)
        ↓
┌──────────────────────────────────────────────┐
│ extractPrecise（高可信度，4 种精确方法）       │
│ ① extractFromVideoTags（video/source 标签）  │
│ ② extractFromMeta（OG/Meta 标签）            │
│ ③ extractFromScriptJson（script JSON）       │
│ ④ extractFromJsVars（JS 变量）               │
│                                              │
│ isVideoUrl 已收紧：                          │
│   只保留 .m3u8/.mp4/format=m3u8/type=m3u8    │
│   去掉 ?url=/&url=/?playurl=/&playurl=       │
│                                              │
│ extractPlayerPageUrl 在结果中解析播放器页面 URL │
└──────────────────────────────────────────────┘
        ↓
   extractPrecise 命中？
        ↓
   ├─ 是（size≥1）→ 直接播放（高可信度，首屏快）
   │                  ↓
   │              player.setUp(url) + startPlayLogic
   │
   └─ 否（size=0）→ extractWithWebView 嗅探
                      ↓
                ┌──────────────────────────────────┐
                │ BackstageWebView 加载文章页面     │
                │ 5路 JS hook + shouldInterceptRequest │
                │ VIDEO_SOURCE_REGEX 匹配网络请求  │
                │ timeout=8-10s（P2-2 缩短后）     │
                └──────────────────────────────────┘
                      ↓
                 嗅探命中？
                      ↓
                 ├─ 是 → 播放（动态抓包最准确）
                 │       ↓
                 │   player.setUp(url) + startPlayLogic
                 │
                 └─ 否 → extractByRegex 正则兜底（兜底的兜底）
                          ↓
                    ┌──────────────────────────────────┐
                    │ VIDEO_URL_REGEX 匹配 HTML         │
                    │ isVideoUrl 已收紧（仅真实视频流）  │
                    └──────────────────────────────────┘
                          ↓
                    正则兜底命中？
                          ↓
                    ├─ 是 → 播放
                    │
                    └─ 否 → 回退文章链接交给 ExoPlayer
```

**关键变更**：
- 修复前：extract（5种方法混合）命中即播放 → 正则兜底误匹配阻塞嗅探
- 修复后：extractPrecise（前4种精确方法）命中才直接播放；未命中优先嗅探；嗅探失败才走正则兜底

## File Changes

| 文件路径 | 变更说明 |
|---------|---------|
| `app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt` | flowByOriginSort 查询去掉 description 字段，更新注释说明列表不使用 description |
| `app/src/main/java/io/legado/app/utils/ImageUtils.kt` | decode(ByteArray) 和 decode(InputStream) 增加图片文件头检测方法，已知格式跳过解密 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | createMediaItem 不拼 SPLIT_TAG，改用 setMimeType + setDefaultHeaders；新增 url 后缀→MIME 映射工具方法 |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | P1-4: 收紧 isVideoUrl（去掉 `?url=`/`&url=`/`?playurl=`/`&playurl=` 过宽条件，只保留 .m3u8/.mp4/format=m3u8/type=m3u8）；新增 extractPrecise（从 extract 拆分前4种精确方法：标签/Meta/JSON/JS变量）；extract 保留向后兼容（内部改为调用 extractPrecise + extractByRegex）。P2-2: 暴露 extractWithWebView 返回的 Job 引用或提供 cancel 方法，支持 onDestroy 外部 cancel |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | L265-337 抓取流程调整：extractPrecise 命中→播放；未命中→extractWithWebView 嗅探；嗅探失败→extractByRegex 正则兜底；正则兜底也失败→回退文章链接 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | onDestroy 主动 cancel VideoUrlExtractor Job |
| `app/src/main/java/io/legado/app/help/BackstageWebView.kt` | 嗅探超时从 15s 缩短为 8-10s |
| `app/src/main/java/io/legado/app/help/http/`（Cronet 初始化相关文件） | 排查 Cronet 初始化，必要时禁用改用 OkHttp |
| `app/src/main/assets/updateLog.md` | 追加本次修复的用户可感知变更说明（编译前更新） |

## 日志规范

按改造过程日志记录规范，每个修复点在关键路径添加日志：

| 修复点 | 永久日志 | 临时日志 |
|--------|---------|---------|
| Bug#5 | AppLog.put（查询失败 catch 块） | - |
| Bug#3 | AppLog.putDebug（解密错误，已有） | Log.d（文件头检测命中/未命中） |
| Bug#4 | Log.d（MediaItem 创建：MimeType + uri 后缀） | Log.d（headers 注入确认，已有 ExoHeader） |
| P1-4 | AppLog.putInfo（抓取流程各层命中/未命中节点：extractPrecise 命中/未命中、嗅探启动/命中/未命中、正则兜底命中/未命中） | Log.d（isVideoUrl 过滤前后候选数、extractPrecise 各子方法命中数） |
| P2-1 | AppLog.put（Cronet 初始化失败） | Log.d（Cronet 状态排查） |
| P2-2 | AppLog.put（Job cancel 节点） | Log.d（嗅探超时触发） |

临时日志验证通过后用 Grep 移除，重新编译确认。
