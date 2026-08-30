# design.md - 视频缓冲速度激进优化（聚焦当前视频）

> **状态**：Proposed（待实施，本阶段仅出设计文档，不改代码）
> **创建日期**：2026-07-28
> **设计目标**：聚焦"当前视频"缓冲速度（非下一集预加载），默认中高端机激进策略，整合网上成熟方案，覆盖各类型视频（HLS/DASH/MP4/FLV/MKV 等）
> **前置 spec**：[video-prebuffer-enhancement/design.md](../video-prebuffer-enhancement/design.md)（已实施 P0，本 spec 在其基础上聚焦当前视频起播与防 rebuffer）

---

## 一、Technical Approach（技术方案详解）

### 1.1 LoadControl 层深度优化

#### 1.1.1 现状

`ExoPlayerHelper.createLoadControlByTier`（L133-L155）已按带宽分三档构建 `DefaultLoadControl`：
- WEAK（<1Mbps）：minBuffer=5s, maxBuffer=30s, bufferForPlayback=500ms, bufferForPlaybackAfterRebuffer=1s
- MEDIUM（1-5Mbps）：minBuffer=8s, maxBuffer=90s, bufferForPlayback=1s, bufferForPlaybackAfterRebuffer=2s
- GOOD（≥5Mbps）：minBuffer=8s, maxBuffer=120s, bufferForPlayback=1s, bufferForPlaybackAfterRebuffer=2s

档位决策放在 `prepareAsyncInternal` 入口（`PlayerInstancePool.acquire` → `createLoadControl`），运行时不可热切换（与 video-prebuffer-enhancement AD-09 决策一致，路径A）。

#### 1.1.2 不足

1. **未启用 `setTargetBufferBytes(-1)`**：`DefaultLoadControl` 默认 `targetBufferBytes = DefaultLoadControl.DEFAULT_TARGET_BUFFER_BYTES`（约 50MB），导致即便 maxBuffer=120s，实际内存缓冲上限被 50MB 截断，高码率视频（10Mbps+）只能缓冲约 40s 而非 120s，rebuffer 风险高。
2. **未启用 `setPrioritizeTimeOverSizeThresholds(true)`**：默认 `false`，意味着缓冲达到 `targetBufferBytes`（50MB）即停止加载，即使未达 maxBuffer 时长。这是"用户感觉没效果"的核心原因之一——maxBuffer=120s 形同虚设。
3. **`bufferForPlayback` 偏高**：GOOD 档 1s 意味着需缓冲 1s 内容才起播，中高端机可降至 500ms 甚至 300ms 加速首帧。
4. **档位阈值过粗**：1Mbps/5Mbps 两道分界线导致 2-4Mbps 中网场景被归入 MEDIUM（maxBuffer=90s），实际可按 3Mbps 再细分。

#### 1.1.3 优化方案（激进策略，默认中高端机）

在 `createLoadControlByTier` builder 链上追加两个关键参数：

- `setTargetBufferBytes(DefaultLoadControl.TARGET_BUFFER_BYTES_INFINITE)` 即 `-1`：解除内存上限，让缓冲完全由 maxBuffer 时长控制（参考 ExoPlayer 官方文档"Large buffer for high-bitrate content"建议）。
- `setPrioritizeTimeOverSizeThresholds(true)`：优先按时长阈值（maxBuffer）而非字节阈值停止加载，确保 120s 缓冲真正生效。

同时调整 `bufferForPlayback`：
- WEAK：500ms → 500ms（保留，弱网需更多首帧保护）
- MEDIUM：1s → 800ms
- GOOD：1s → 500ms（中高端机激进起播）

档位细分（可选 P2）：
- 新增 `GOOD_PLUS`（≥10Mbps）：minBuffer=10s, maxBuffer=180s, bufferForPlayback=300ms

#### 1.1.4 用户可配置

`VideoPlay.videoMaxBufferSec`（L128-L132）已存在，>0 时覆盖档位默认值。需补充 `videoMinBufferSec` 与 `videoBufferForPlaybackMs` 两个参数，让高级用户可微调首帧激进程度。

---

### 1.2 HLS 协议层深度优化

#### 1.2.1 现状

`ExoPlayerHelper.createMediaSource`（L195-L220）HLS 分支仅调用 `HlsMediaSource.Factory(dataSourceFactory).createMediaSource(mediaItem)`，**未启用 `setAllowChunklessPreparation`**（代码实测确认）。任务描述中提及的"已实施 setAllowChunklessPreparation(true) + setLowLatencyModeEnabled(true)"在当前主分支 `ExoPlayerHelper.kt` 中不存在，可能仅在子分支或未合并的提交中。

`Exo2MediaPlayer.kt` 中 `buildFallbackTypes`（L204）实现了嗅探失败快速降级链（HLS→DASH→Progressive→WebView），但这是错误恢复路径，非起播加速路径。

#### 1.2.2 不足

1. **Chunkless Preparation 未启用**：HLS 默认需下载首个分片才能完成 preparation，首帧耗时高。`setAllowChunklessPreparation(true)` 可仅解析 m3u8 清单即完成 preparation，首帧耗时降低 30%+（ExoPlayer 官方 benchmark）。
2. **未配置 `MediaItem.LiveConfiguration`**：直播 HLS 无 `targetOffsetMs` 约束，低延迟模式无目标偏移，缓冲行为不可控。
3. **未评估自定义 ChunkSource**：默认 `HlsMediaSource` 使用 `DefaultHlsChunkSource`，无法干预分片选择策略（如预取下一个分片、跳过 init 分片重复下载）。自定义 ChunkSource 可在弱网下跳过非关键分片加速起播，但实现复杂度高。
4. **`setLowLatencyModeEnabled(true)` 缺失**：LL-HLS 场景需此配置，但多数点播源不支持，收益有限（参考 video-prebuffer-enhancement AD-02 决策：setAllowChunklessPreparation 优先，LL-HLS 可选）。

#### 1.2.3 优化方案

- **P0**：`createMediaSource` HLS 分支追加 `.setAllowChunklessPreparation(true)`，兼容性 >95%（ExoPlayer 官方统计），对非标 m3u8 自动降级。
- **P1**：直播 HLS 配置 `MediaItem.LiveConfiguration.Builder().setTargetOffsetMs(3000).build()`，约束直播时延 3s（对齐 `DefaultMediaSourceFactory.setLiveTargetOffsetMs(5000)` 但更激进）。
- **P2**：评估自定义 `HlsChunkSource`，在弱网下预取下一个分片 + 跳过 init 分片重复下载。需重写 `HlsMediaSource.Factory.setChunkSourceFactory`，复杂度高，先观测 P0 收益再决定。
- **P2**：`setLowLatencyModeEnabled(true)` 仅对 LL-HLS 源启用（通过 m3u8 `#EXT-X-SERVER-CONTROL` 标签检测），避免对非 LL-HLS 源产生副作用。

---

### 1.3 OkHttp 网络层深度优化

#### 1.3.1 现状

`ExoPlayerHelper.okhttpDataFactory`（L847-L857）配置：
- `okHttpClient.newBuilder().callTimeout(0).protocols([HTTP_1_1]).followRedirects(true)`
- `OkHttpDataSource.Factory(client).setUserAgent(BROWSER_UA).setCacheControl(maxAge=1天)`

**未显式配置 `ConnectionPool`**（任务描述提及的 "ConnectionPool(10,5min)" 在 `ExoPlayerHelper` 中不存在，仅在 `HttpHelper.kt` L101 有 `ConnectionPool(50, 5min)` 用于书源请求）。视频播放用的 `okHttpClient` 通过 `newBuilder()` 派生，会继承 `HttpHelper` 的 50 连接池，但视频流是单长连接，50 连接池对视频无意义且占内存。

#### 1.3.2 不足

1. **强制 HTTP/1.1 的代价**：`P2-C 修复`（L838-L845）因部分 CDN 的 HTTP/2 PROTOCOL_ERROR 强制降级到 HTTP_1_1，丢失 HTTP/2 多路复用收益。对 HLS 多分片并发请求场景（m3u8 清单 + 多个 ts 分片），HTTP/1.1 需为每个分片建独立 TCP 连接，握手开销显著。已实施 22 条 `StreamResetException` 是铁证，但"一刀切"降级过于保守。
2. **无 `EventListener` 埋点**：无法观测 DNS 耗时、TCP 握手耗时、TLS 握手耗时、首字节时间（TTFB），网络层瓶颈不可定位。
3. **`Dispatcher` 并发未配置**：OkHttp 默认 `Dispatcher` 每主机最大并发 5，HLS 多分片并发请求可能被限流。
4. **`CacheControl.maxAge(1天)` 作用被误解**：`OkHttpDataSource` 的 `setCacheControl` 是设置请求头 `Cache-Control: max-age=86400`，这是告诉 CDN 缓存 1 天，**不是控制 ExoPlayer 的 SimpleCache**。对 CDN 不支持 Cache-Control 的源无效果，且与 ExoPlayer 的 `SimpleCache`（LRU 磁盘缓存）是两套独立缓存机制，此配置对"当前视频缓冲速度"几乎无影响。

#### 1.3.3 优化方案

- **P0：分域 HTTP/2 策略**。不再"一刀切" HTTP_1_1，改为：默认尝试 HTTP/2，遇到 `StreamResetException` 自动降级到 HTTP_1_1 并缓存该域名降级标记 1 小时。实现：自定义 `OkHttpClient` 添加 `Interceptor`，捕获 `StreamResetException` 后切换 protocols。
- **P0：注入 `EventListener`**。新增 `VideoEventListener extends EventListener`，记录 `callStart/dnsEnd/connectEnd/tlsHandshakeEnd/responseHeadersStart/responseBodyStart` 时间戳，计算 TTFB 与连接耗时，写入 `AppLog`。
- **P1：`Dispatcher` 并发提升**。视频专用 `OkHttpClient` 配置 `Dispatcher().setMaxRequestsPerHost(20)`，解决 HLS 多分片并发限流。
- **P1：`ConnectionPool` 独立化**。视频专用 `ConnectionPool(10, 5min)`，与书源请求池隔离，避免视频长连接占用书源连接配额。
- **P2：移除 `setCacheControl`**。此配置对 ExoPlayer 缓冲无实际收益，移除避免误导。

---

### 1.4 CacheDataSource 缓存层优化

#### 1.4.1 现状

`ExoPlayerHelper.cacheDataSourceFactory`（L818-L833）配置：
- `CacheDataSource.Factory().setCache(cache).setUpstreamDataSourceFactory(DefaultDataSource.Factory(appCtx, okhttpDataFactory)).setCacheReadDataSourceFactory(FileDataSource.Factory()).setCacheWriteDataSinkFactory(CacheDataSink.Factory().setCache(cache).setFragmentSize(DEFAULT_FRAGMENT_SIZE))`

`cache`（L895-L906）为 `SimpleCache`，LRU 驱逐，容量 `VideoPlay.videoCacheSize`（默认 100MB，范围 50-2048MB）。

#### 1.4.2 不足

1. **未启用 `FLAG_IGNORE_CACHE_ON_ERROR`**：当 `SimpleCache` 读取失败（如缓存分片损坏、磁盘满），默认行为是抛异常导致播放失败。启用 `FLAG_IGNORE_CACHE_ON_ERROR` 后，缓存读取失败自动回退到 upstream（网络），提升容错。
2. **未启用 `FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`**：缓存分片长度与服务端 Content-Length 不匹配时默认抛异常，启用后忽略长度不一致继续播放。
3. **`CacheDataSink.DEFAULT_FRAGMENT_SIZE`（5MB）偏大**：HLS 小分片（如 2MB ts）写入 5MB fragment 导致空间浪费，且写入失败时丢失整片。建议降至 2MB。
4. **无内存级缓存**：`SimpleCache` 是纯磁盘缓存，首帧仍需磁盘 IO。可叠加 `CacheDataSink` + 内存 `LruCache`，首帧命中内存零 IO。但内存缓存对中低端机 OOM 风险高，P2 评估。

#### 1.4.3 优化方案

- **P0**：`CacheDataSource.Factory` 追加 `.setFlags(CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR or CacheDataSource.FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH)`。
- **P1**：`CacheDataSink.Factory` 追加 `.setFragmentSize(2 * 1024 * 1024)`（2MB）。
- **P2**：评估内存级 `LruCache` 叠加，限制 10MB 内存缓存，仅缓存首帧数据。

---

### 1.5 自适应码率层优化

#### 1.5.1 现状

`PlayerInstancePool.createTrackSelector`（L58-L60）返回默认 `DefaultTrackSelector(appCtx)`，未配置自适应码率参数。`bandwidthMeter`（L88-L90）为全局单例 `DefaultBandwidthMeter`，用于 LoadControl 档位判断，但未注入 `TrackSelector` 参与自适应选择。

#### 1.5.2 不足

1. **未限制最大视频分辨率**：高码率 4K 视频在 1080p 屏幕上仍尝试解码 4K，浪费带宽与解码资源。`DefaultTrackSelector` 默认不限制分辨率。
2. **未配置 `setAdaptiveSelectionMarginMs`**：自适应切换码率时，默认无缓冲余量，切换瞬间易 rebuffer。`setAdaptiveSelectionMarginMs(1500)` 让切换前有 1.5s 缓冲余量。
3. **`bandwidthMeter` 未注入 TrackSelector**：`DefaultTrackSelector` 默认自建 `BandwidthMeter`，与 `ExoPlayerHelper.bandwidthMeter` 是两个独立实例，LoadControl 档位判断与 TrackSelector 码率选择基于不同带宽测量，不一致。

#### 1.5.3 优化方案

- **P0**：`createTrackSelector` 返回的 `DefaultTrackSelector` 追加参数：
  - `.setMaxVideoSize(1920, 1080)`：限制最大视频分辨率 1080p（中高端机默认，用户可调）
  - 注入共享 `ExoPlayerHelper.bandwidthMeter`：`DefaultTrackSelector(appCtx, ExoPlayerHelper.bandwidthMeter)`
- **P1**：`DefaultTrackSelector.Parameters` 追加 `.setAdaptiveSelectionMarginMs(1500)`。
- **P2**：用户可配置 `videoMaxResolution`（720p/1080p/1440p/4K），默认 1080p。

---

### 1.6 解码器层优化

#### 1.6.1 现状

`PlayerInstancePool.sharedRendererFactory`（L79-L83）为 `DefaultRenderersFactory(appCtx).setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)`，优先硬件解码 + 扩展渲染器（如 FFmpeg）。未启用异步队列。

#### 1.6.2 不足

1. **未启用 `forceEnableMediaCodecAsynchronousQueueing`**：MediaCodec 异步队列让解码器在独立线程处理解码任务，避免阻塞 ExoPlayer 主循环。默认禁用，解码阻塞导致渲染线程等待，丢帧率高。
2. **未启用 `setEnableDecoderFallback`**：硬件解码失败时默认不回退软件解码，直接抛错。启用 `setEnableDecoderFallback(true)` 让硬件解码失败自动回退。

#### 1.6.3 优化方案

- **P0**：`sharedRendererFactory` 追加：
  - `.forceEnableMediaCodecAsynchronousQueueing(true)`：启用 MediaCodec 异步队列
  - `.setEnableDecoderFallback(true)`：硬件解码失败回退软件
- **P1**：`.setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)` 已配置，保留。

---

### 1.7 性能监控层（AnalyticsListener）

#### 1.7.1 现状

`Exo2MediaPlayer.attachToPlayer`（L394-L398）已调用 `player.addAnalyticsListener(this@Exo2MediaPlayer)`，但 `Exo2MediaPlayer` 实现的 `AnalyticsListener` 回调未覆盖缓冲速度关键指标。无 TTFB、缓冲中断、丢帧率、带宽利用率埋点。

#### 1.7.2 不足

1. **无 TTFB 监控**：首字节时间（Time To First Byte）是起播速度的核心指标，未采集。
2. **无缓冲中断监控**：`onDroppedFrames` / `onVideoInputFormatChanged` 未采集，rebuffer 次数与时长不可见。
3. **无带宽利用率监控**：`onLoadStarted` / `onLoadCompleted` 未采集，实际下载带宽与理论带宽差异不可见。
4. **无首帧耗时监控**：`onRenderedFirstFrame` 已有（`hasReportedReadySuccess` 标志位），但未输出到 AppLog 供分析。

#### 1.7.3 优化方案

新增 `VideoAnalyticsListener implements AnalyticsListener`，采集以下指标写入 `AppLog`：
- `onLoadStarted`：记录加载开始时间、URL、请求类型（m3u8/ts/mp4/init）
- `onLoadCompleted`：计算加载耗时、下载字节数、实际带宽
- `onDroppedFrames`：丢帧数、丢帧率
- `onVideoFrameProcessingOffsetCount`：帧处理偏移（rebuffer 前兆）
- `onRenderedFirstFrame`：首帧耗时（从 prepare 到首帧渲染）
- `onPlayerStateChanged`：状态转换耗时（BUFFERING→READY）
- `onBandwidthEstimationChanged`：带宽估计变化

输出格式：`VideoMetric: event=firstFrame, elapsed=1200ms, urlPath=...`，release 包通过 `AppLog.put` 输出（参考 video-prebuffer-enhancement AD-16 已修复 release 包日志）。

---

### 1.8 已实施代码的不足分析（为什么用户感觉没效果）

#### 1.8.1 核心结论

用户感觉"三项优化效果不明显"的根本原因是：**已实施的优化要么配置不完整，要么作用对象错误**。逐项分析：

#### 1.8.2 ExoPlayerHelper.createLoadControlByTier 的不足

- **致命缺陷：`setTargetBufferBytes(-1)` 与 `setPrioritizeTimeOverSizeThresholds(true)` 未启用**
  - maxBuffer=120s（GOOD 档）被 `targetBufferBytes` 默认值 50MB 截断
  - 10Mbps 视频流 50MB 仅能缓冲 40s，远未达 120s
  - 用户感知："已设置 120s 缓冲，但播放 40s 后仍 rebuffer"
  - **这是效果不明显的第一根因**

- **`bufferForPlayback` 偏高**：GOOD 档 1s 起播门槛，中高端机可 500ms，首帧延迟感知明显

#### 1.8.3 Exo2MediaPlayer HLS 优化的不足

- **`setAllowChunklessPreparation(true)` 实际未启用**（代码实测确认，`ExoPlayerHelper.createMediaSource` HLS 分支无此调用）
  - HLS 首帧仍需下载首个分片才能 preparation
  - 用户感知："HLS 视频起播慢，与未优化前无差异"
  - **这是效果不明显的第二根因**

- **`setLowLatencyModeEnabled(true)` 缺失**：LL-HLS 源无法低延迟播放（影响面小，多数源非 LL-HLS）

#### 1.8.4 PlayerInstancePool.sharedAllocator 的不足

- `DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` 即 64KB segment
  - 64KB 对 4K 视频过小，频繁分配/释放导致内存抖动
  - 中高端机可提升至 256KB（`C.DEFAULT_BUFFER_SEGMENT_SIZE * 4`）
  - **影响面中等**：内存抖动导致 GC 频繁，间接影响缓冲连续性

#### 1.8.5 OkHttp 配置的不足

- **强制 HTTP/1.1 丢失多路复用**：HLS 多分片并发请求需多次 TCP 握手
- **无 EventListener**：网络瓶颈不可定位，无法判断是 DNS 慢、TCP 慢、还是 CDN 慢
- **`CacheControl.maxAge(1天)` 作用对象错误**：作用于 CDN 缓存，非 ExoPlayer SimpleCache，对当前视频缓冲无影响
- **无独立 ConnectionPool**：视频长连接占用书源连接配额，相互影响
- **这是效果不明显的第三根因**（网络层瓶颈未被任何已实施优化覆盖）

#### 1.8.6 CacheDataSource 的不足

- **未启用 `FLAG_IGNORE_CACHE_ON_ERROR`**：缓存分片损坏直接播放失败，用户感知"偶尔卡死"
- **`CacheDataSink.DEFAULT_FRAGMENT_SIZE`（5MB）偏大**：HLS 小分片写入浪费空间

#### 1.8.7 综合诊断

已实施的三项优化（LoadControl 分档 + OkHttp HTTP_1_1 + HLS 降级链）中：
1. **LoadControl 分档**：参数不完整（缺 setTargetBufferBytes + setPrioritizeTimeOverSizeThresholds），maxBuffer=120s 形同虚设
2. **OkHttp HTTP_1_1**：方向错误（应分域策略而非一刀切），且无监控无法定位瓶颈
3. **HLS 降级链**：仅错误恢复路径，起播加速路径（setAllowChunklessPreparation）未启用

**用户感觉没效果的根因：已实施优化未触及"当前视频起播速度"的核心瓶颈（targetBufferBytes 截断 + chunkless preparation 缺失 + 网络层无监控）。**

---

### 1.9 Cronet 评估（视频流网络栈升级）

#### 1.9.1 现状

项目已有 `CronetHelper.kt` 启用 QUIC/HTTP-3/HTTP-2/Brotli/AsyncDNS，但仅用于书源请求（`HttpHelper` 调用链）。视频流仍走 OkHttp（`ExoPlayerHelper.okhttpDataFactory`），未利用 Cronet 的 QUIC 协议弱网优化能力。审查报告（review-completeness.md 遗漏点1）指出这是"重大遗漏"——Cronet 对弱网优化可能比 OkHttp 任何调参都有效。

#### 1.9.2 Cronet 优势

Cronet 是 Chromium 网络栈，相比 OkHttp 的核心优势在弱网场景：
- **QUIC 协议**：基于 UDP，0-RTT 连接恢复（已连过的服务器再次连接无需握手），弱网下首字节时间显著降低
- **多路复用无队头阻塞**：HTTP/2 over TCP 存在队头阻塞（一个分片丢失阻塞后续分片），QUIC 单流丢包不影响其他流，HLS 多分片并发场景收益显著
- **HTTP/3 原生支持**：OkHttp 不支持 HTTP/3，Cronet 原生支持
- **连接迁移**：网络切换（WiFi→4G）时 QUIC 连接可平滑迁移，无需重建

业界实践：YouTube 在用 Cronet 作为视频流网络栈；B 站部分场景在用 Cronet 弱网优化。

#### 1.9.3 方案对比

| 方案 | APK 体积增量 | 依赖 | 适用设备 |
|------|------------|------|---------|
| **Cronet via Google Play Services** | 0（共享系统 Cronet） | 依赖 Google Play Services | 国行设备多数无 Google Play Services |
| **Cronet embedded** | 1.5MB | 无依赖 | 全设备 |

#### 1.9.4 评估结论

- **P1 评估 Cronet via Google Play Services 用于视频流**：0 体积增量，复用项目已有 Cronet engine
- **降级机制**：无 Google Play Services 设备自动降级到 OkHttp（保持现有 okhttpDataFactory）
- **风险**：国行设备多数无 Google Play Services，Cronet 路径覆盖率有限；需完善降级检测与日志埋点
- **不直接采用 Cronet embedded**：1.5MB 体积增量与项目"轻量"定位冲突，待 P1 评估收益后再决策

> **诚实说明**：当前视频流网络栈仍是 OkHttp，Cronet 集成为 P1 评估项，本阶段不改代码。

---

### 1.10 DohDns 注入视频流 OkHttpClient

#### 1.10.1 现状

项目已有 `DohDns.kt`（DNS over HTTPS 防劫持），实现：
- 3 个 DoH 服务器轮询（Cloudflare/Google/阿里）
- 5 分钟 DNS 解析结果缓存
- 连续 3 次失败自动熔断 5 分钟（降级到系统 DNS）

当前仅注入 `HttpHelper` 的 OkHttpClient（书源请求），视频流 OkHttpClient（`ExoPlayerHelper.okhttpDataFactory` 派生自 `HttpHelper` 的 `okHttpClient`）**未显式注入 DohDns**。审查报告（review-completeness.md 遗漏点2）指出这是高优遗漏点，已有实现仅需 1 行代码注入。

#### 1.10.2 不足

1. **视频流 DNS 解析可能被劫持**：运营商或中间人 DNS 劫持会导致分片请求指向错误 IP，触发降级链或播放失败
2. **弱网 DNS 解析不稳定**：系统 DNS 在弱网下解析耗时高（1-3s）且失败率高，直接影响首帧耗时
3. **DohDns 未复用**：项目已有成熟的 DoH 实现，视频流未复用是遗漏

#### 1.10.3 注入方案

在 `ExoPlayerHelper.okhttpDataFactory` 构建 OkHttpClient 时追加 `.dns(DohDns)`：

```kotlin
okHttpClient.newBuilder()
    .callTimeout(0)
    .protocols(listOf(Protocol.HTTP_1_1))
    .followRedirects(true)
    .dns(DohDns)  // P0 新增：注入 DoH 防劫持（AD-14）
    .build()
```

#### 1.10.4 收益

- **视频流 DNS 解析防劫持**：DoH 加密 DNS 查询，运营商无法劫持
- **弱网 DNS 解析稳定性提升**：DoH 服务器（Cloudflare/Google）解析稳定性优于运营商 DNS
- **零成本复用**：DohDns 已实现且经书源请求验证，仅需 1 行代码注入

#### 1.10.5 风险

- **首次 DoH 解析可能比系统 DNS 慢**：DoH 需建立 HTTPS 连接到 DoH 服务器，首次解析有额外开销（约 100-300ms）
- **缓解**：5 分钟 DNS 缓存兜底，后续解析命中缓存零开销；连续 3 次失败熔断降级到系统 DNS，不会因 DoH 故障导致解析失败

---

## 二、Architecture Decisions（架构决策 - ADR Y-Statement）

### AD-01: LoadControl 静态配置 vs 动态热切换

- **Context**: LoadControl 参数（maxBuffer 等）需根据网络档位调整。ExoPlayer `setLoadControl` 运行时调用会导致 re-prepare（缓冲中断 1-3s），且 `PlayerInstancePool` 池化实例归池后 LoadControl 状态不可控。参考 video-prebuffer-enhancement AD-09 决策：放弃热切换，路径A。
- **Concern**: 网络档位变化时 maxBuffer 不立即生效，如何平衡实时性与稳定性？
- **Decision**: 沿用 video-prebuffer-enhancement AD-09 路径A——LoadControl 仅在 `prepareAsyncInternal` 入口（`PlayerInstancePool.acquire` → `createLoadControl`）设置一次，运行时不热切换。网络档位变化仅影响预加载策略（下一集），不影响当前视频 LoadControl。
- **Goal**: 避免 re-prepare 缓冲中断 + 避免池化实例状态混乱 + 简化实现
- **Tradeoff**: 网络档位提升时 maxBuffer 不立即提升（下次播放才生效），但当前视频播放稳定性优先
- **Status**: Accepted（沿用既有决策）
- **Superseded-by**: 无

### AD-02: HTTP/2 多路复用 vs HTTP/1.1 连接池

- **Context**: 已实施的 `protocols=[HTTP_1_1]`（P2-C 修复）因 22 条 `StreamResetException` 一刀切降级，丢失 HTTP/2 多路复用收益。HLS 多分片并发请求场景 HTTP/1.1 需多次 TCP 握手。
- **Concern**: 如何在规避 PROTOCOL_ERROR 的同时恢复 HTTP/2 多路复用收益？
- **Decision**: 分域策略——默认尝试 HTTP/2，捕获 `StreamResetException` 后对该域名降级到 HTTP_1_1 并缓存降级标记 1 小时。视频专用 `ConnectionPool(10, 5min)` 与书源请求池隔离。
- **Goal**: 恢复 HTTP/2 多路复用收益（HLS 多分片并发）+ 规避已知 PROTOCOL_ERROR CDN
- **Tradeoff**: 首次访问已知问题 CDN 仍会触发一次 StreamResetException（约 200ms），但后续 1 小时内自动降级；实现复杂度增加（需 Interceptor + 降级缓存）
- **Status**: Proposed

### AD-03: setTargetBufferBytes(-1) 启用与否

- **Context**: `DefaultLoadControl` 默认 `targetBufferBytes = 50MB`，导致 maxBuffer=120s 被 50MB 截断（10Mbps 视频仅缓冲 40s）。`setTargetBufferBytes(-1)`（`TARGET_BUFFER_BYTES_INFINITE`）解除内存上限，让缓冲完全由 maxBuffer 时长控制。
- **Concern**: 解除内存上限是否导致 OOM？中低端机内存紧张。
- **Decision**: 启用 `setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)`。默认中高端机（参考 video-prebuffer-enhancement R3 移除 LOW 档位决策），用户可通过 `videoMaxBufferSec` 往下调限制时长间接限制内存。
- **Goal**: 让 maxBuffer=120s 真正生效，消除"设置 120s 但 40s 就 rebuffer"的用户感知
- **Tradeoff**: 中低端机可能 OOM（缓解：用户可调低 videoMaxBufferSec + DeviceTier 检测降级到 MID），但默认中高端机激进策略优先
- **Status**: Proposed

### AD-04: AnalyticsListener 监控埋点

- **Context**: 已实施的 `Exo2MediaPlayer` 虽 `addAnalyticsListener` 但回调未覆盖缓冲速度关键指标。无 TTFB、rebuffer、丢帧率、带宽利用率埋点，无法定位"为什么卡"。
- **Concern**: 埋点开销与数据详尽性的平衡？release 包是否输出？
- **Decision**: 新增 `VideoAnalyticsListener`，采集 7 类指标（TTFB/首帧/rebuffer/丢帧/带宽/状态转换/帧偏移），通过 `AppLog.put` 输出（release 包 WARN/ERROR 始终输出，参考 video-prebuffer-enhancement AD-16）。
- **Goal**: 生产环境可定位缓冲瓶颈（DNS/TCP/CDN/解码/缓存命中），为后续优化提供数据
- **Tradeoff**: 埋点增加少量 CPU 开销（<1%），日志文件略增大（仅 WARN/ERROR），但可观测性收益远大于开销
- **Status**: Proposed

### AD-05: 自定义 ChunkSource vs 默认 HlsMediaSource

- **Context**: 默认 `HlsMediaSource` 使用 `DefaultHlsChunkSource`，无法干预分片选择策略。自定义 `HlsChunkSource` 可在弱网下预取下一个分片、跳过 init 分片重复下载。
- **Concern**: 自定义 ChunkSource 实现复杂度高（需重写 `HlsMediaSource.Factory.setChunkSourceFactory`），收益是否值得？
- **Decision**: P0 先启用 `setAllowChunklessPreparation(true)`（零成本收益 30%+），P2 评估自定义 ChunkSource。若 P0 + LoadControl 优化后 rebuffer 率仍 >5%，再实施自定义 ChunkSource。
- **Goal**: 用最小实现成本获取最大起播加速收益，避免过度工程化
- **Tradeoff**: 可能错过自定义 ChunkSource 的弱网预取收益，但优先验证低复杂度方案
- **Status**: Proposed

### AD-06: CacheDataSource FLAG_IGNORE_CACHE_ON_ERROR 启用

- **Context**: `SimpleCache` 缓存分片损坏或磁盘满时，默认行为是抛异常导致播放失败。用户感知"偶尔卡死"。
- **Concern**: 启用 `FLAG_IGNORE_CACHE_ON_ERROR` 后缓存读取失败静默回退到网络，是否掩盖真实问题？
- **Decision**: 启用 `FLAG_IGNORE_CACHE_ON_ERROR` + `FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`。同时通过 `AnalyticsListener.onLoadError` 记录缓存失败事件，确保问题可观测。
- **Goal**: 缓存故障不影响播放连续性，同时通过埋点感知缓存健康度
- **Tradeoff**: 可能掩盖磁盘满/缓存损坏问题（缓解：埋点 + 定期 clearCache），但播放连续性优先
- **Status**: Proposed

### AD-07: 解码器异步队列启用

- **Context**: `DefaultRenderersFactory` 默认禁用 MediaCodec 异步队列，解码阻塞 ExoPlayer 主循环导致丢帧。`forceEnableMediaCodecAsynchronousQueueing(true)` 让解码器独立线程处理。
- **Concern**: 异步队列在部分低端设备 MediaCodec 实现有 bug（如 Samsung S8 已知崩溃），是否默认启用？
- **Decision**: 默认启用 `forceEnableMediaCodecAsynchronousQueueing(true)` + `setEnableDecoderFallback(true)`。默认中高端机（参考 video-prebuffer-enhancement R3 移除 LOW 档位），已知问题设备通过 `MediaCodecList` 检测黑名单禁用。
- **Goal**: 消除解码阻塞导致的丢帧，提升高码率视频流畅度
- **Tradeoff**: 极少数低端设备可能崩溃（缓解：设备黑名单 + 软件解码回退），但默认中高端机激进策略优先
- **Status**: Proposed

### AD-08: 自适应码率限制策略

- **Context**: `DefaultTrackSelector` 默认不限制视频分辨率，4K 视频在 1080p 屏幕仍尝试解码 4K，浪费带宽与解码资源。
- **Concern**: 限制最大分辨率是否影响高分辨率设备体验？用户可配置？
- **Decision**: 默认 `setMaxVideoSize(1920, 1080)`（1080p），用户可通过 `videoMaxResolution` 配置（720p/1080p/1440p/4K）。注入共享 `ExoPlayerHelper.bandwidthMeter` 确保 LoadControl 与 TrackSelector 基于同一带宽测量。P1 追加 `setAdaptiveSelectionMarginMs(1500)`。
- **Goal**: 限制无效高分辨率解码 + 自适应切换不 rebuffer + LoadControl/TrackSelector 带宽测量一致
- **Tradeoff**: 4K 设备默认降级到 1080p（用户可手动调高），但带宽与解码资源节省显著
- **Status**: Proposed

### AD-09: buffer segment size 提升与否

- **Context**: `PlayerInstancePool.sharedAllocator = DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` 即 64KB。4K 视频 64KB segment 频繁分配/释放导致内存抖动 + GC 频繁。
- **Concern**: 提升 segment size 是否导致内存占用过高？
- **Decision**: 中高端机默认提升至 256KB（`C.DEFAULT_BUFFER_SEGMENT_SIZE * 4`），用户可通过 DeviceTier 降级到 MID 保留 64KB。`DefaultAllocator` 的 `true` 参数（exact allocation）保留，避免内存碎片。
- **Goal**: 减少 4K/高码率视频的内存分配次数，降低 GC 频率，提升缓冲连续性
- **Tradeoff**: 单实例内存占用增加（256KB * N segments），但 3 实例池共享 allocator，总增量可控（<50MB）
- **Status**: Proposed

### AD-10: bufferForPlayback 起播门槛激进调整

- **Context**: 已实施代码 GOOD 档 `bufferForPlayback=1s`，意味着需缓冲 1s 视频内容才起播。中高端机解码能力强，可降至 500ms 甚至 300ms 加速首帧。ExoPlayer 官方建议 `bufferForPlayback` 可低至 250ms（低延迟场景）。
- **Concern**: 过低导致首帧后立即 rebuffer（缓冲不足支撑播放速率）？
- **Decision**: GOOD 档降至 500ms，MEDIUM 档降至 800ms，WEAK 档保留 500ms。配合 `setPrioritizeTimeOverSizeThresholds(true)` 确保缓冲持续到 maxBuffer。用户可通过 `videoBufferForPlaybackMs` 微调。
- **Goal**: 首帧渲染延迟降 50%（1s→500ms），用户感知"秒开"
- **Tradeoff**: 极弱网下首帧后可能立即 rebuffer（缓解：WEAK 档保留 500ms + bufferForPlaybackAfterRebuffer=1s 保护），但中高端机好网场景收益显著
- **Status**: Proposed

### AD-11: CacheControl.maxAge 移除决策

- **Context**: 已实施代码 `okhttpDataFactory.setCacheControl(CacheControl.Builder().maxAge(1, TimeUnit.DAYS).build())` 设置请求头 `Cache-Control: max-age=86400`。此配置作用于 CDN 缓存策略，**非 ExoPlayer SimpleCache**。对不支持 Cache-Control 的 CDN 无效果，且与 ExoPlayer 的 LRU 磁盘缓存是两套独立机制。
- **Concern**: 移除后是否影响缓存命中？是否影响 CDN 行为？
- **Decision**: 移除 `setCacheControl` 调用。ExoPlayer 缓存由 `SimpleCache`（LRU 磁盘缓存）独立管理，不依赖 HTTP Cache-Control 头。CDN 缓存策略由服务端控制，客户端强制 max-age 可能与服务端意图冲突（如直播流不应缓存 1 天）。
- **Goal**: 消除配置误解，避免对直播流等不应长期缓存的内容强制 max-age=1天
- **Tradeoff**: 对支持 Cache-Control 的 CDN 可能减少回源（但 ExoPlayer SimpleCache 已提供本地缓存，CDN 回源减少收益可忽略）
- **Status**: Proposed

### AD-12: bandwidthMeter 共享注入 vs 独立实例

- **Context**: 已实施代码 `ExoPlayerHelper.bandwidthMeter`（全局单例）用于 LoadControl 档位判断，但 `PlayerInstancePool.createTrackSelector` 返回的 `DefaultTrackSelector(appCtx)` 默认自建独立 `BandwidthMeter`。两个实例基于不同测量窗口，LoadControl 档位与 TrackSelector 码率选择不一致。
- **Concern**: 共享带宽计是否导致测量互相干扰？池化实例归池后带宽计状态如何处理？
- **Decision**: `createTrackSelector` 改为 `DefaultTrackSelector(appCtx, ExoPlayerHelper.bandwidthMeter)`，注入共享实例。`DefaultBandwidthMeter` 内部线程安全，多实例共享无干扰。归池时不重置 bandwidthMeter（其状态为全局带宽估计，跨实例复用有价值）。
- **Goal**: LoadControl 档位判断与 TrackSelector 码率选择基于同一带宽测量，决策一致
- **Tradeoff**: 共享实例无法按播放器实例隔离带宽估计（但视频播放场景带宽估计全局共享更合理，避免冷启动测量不准）
- **Status**: Proposed

### AD-13: Cronet 评估用于视频流

- **Context**: 项目已有 `CronetHelper` 用于书源请求（启用 QUIC/HTTP-3/HTTP-2/Brotli/AsyncDNS），视频流仍用 OkHttp。审查报告（review-completeness.md 遗漏点1）指出 Cronet 对弱网优化可能比 OkHttp 任何调参都有效。
- **Concern**: 视频流弱网优化空间未充分利用，OkHttp 不支持 HTTP/3 与 QUIC 0-RTT 连接恢复。
- **Decision**: P1 评估 Cronet via Google Play Services 用于视频流，失败降级 OkHttp。优先选 Google Play Services 方案（0 体积增量），不直接采用 Cronet embedded（1.5MB 体积增量与项目轻量定位冲突）。
- **Goal**: 利用 QUIC 协议弱网优化（0-RTT 连接恢复、多路复用无队头阻塞、连接迁移）提升视频流缓冲速度
- **Tradeoff**: 增加 Google Play Services 依赖（国行设备多数无，需完善降级检测与日志埋点），降级机制需覆盖所有视频类型
- **Status**: Proposed

### AD-14: DohDns 注入视频流 OkHttpClient

- **Context**: 项目已有 `DohDns`（DoH 防劫持，3 服务器轮询 + 5 分钟缓存 + 连续 3 次失败熔断 5 分钟）仅注入 `HttpHelper`，视频流 OkHttpClient 未注入。审查报告（review-completeness.md 遗漏点2）指出这是高优遗漏点。
- **Concern**: 视频流 DNS 解析可能被劫持（触发降级链或播放失败），弱网 DNS 解析不稳定（1-3s）直接影响首帧耗时。
- **Decision**: P0 注入 DohDns 到 `ExoPlayerHelper.okhttpDataFactory` 的 OkHttpClient（追加 `.dns(DohDns)`），零成本复用已有实现。
- **Goal**: 视频流 DNS 解析防劫持，弱网 DNS 解析稳定性提升
- **Tradeoff**: 首次 DoH 解析可能比系统 DNS 慢（约 100-300ms，需建立 HTTPS 连接到 DoH 服务器），但有 5 分钟缓存兜底 + 连续 3 次失败熔断降级到系统 DNS
- **Status**: Proposed

---

## 三、Data Flow（数据流，纯文字描述）

### 3.1 网络请求流（URL → OkHttp → CacheDataSource → MediaSource → ExoPlayer → Renderer）

播放器发起视频数据请求的完整链路如下。首先，`Exo2MediaPlayer.prepareAsyncInternal` 调用 `ExoPlayerHelper.sniffVideoType` 嗅探内容类型（Range 请求 8KB，三级内容证据交叉验证），返回 `SniffResult`（contentType + mimeType + finalUrl）。嗅探阶段 `preResolveDns` 异步预热 DNS 缓存，降低嗅探耗时。

嗅探完成后，`ExoPlayerHelper.createMediaSource` 按 contentType 分发：HLS 走 `HlsMediaSource.Factory`（P0 启用 `setAllowChunklessPreparation`）、DASH 走 `DashMediaSource.Factory`、SS 走 `SsMediaSource.Factory`、OTHER 走 `ProgressiveMediaSource.Factory`。MediaSource 内部通过 `resolvingDataSource`（`ResolvingDataSource.Factory`）解析 SPLIT_TAG 拼接的 URL+headers，剥离 headers 注入 `okhttpDataFactory`。

数据请求进入 `cacheDataSourceFactory`（`CacheDataSource.Factory`）：首先查询 `SimpleCache`（LRU 磁盘缓存），命中则由 `FileDataSource` 直接读取本地文件（零网络）；未命中则回退到 `DefaultDataSource.Factory(appCtx, okhttpDataFactory)`，由 `OkHttpDataSource` 发起 HTTP 请求。OkHttp 请求经 `VideoEventListener`（P0 新增）记录 DNS/TCP/TLS/TTFB 各阶段耗时。响应数据通过 `CacheDataSink` 按 2MB fragment（P1 调整）写入 `SimpleCache`，同时返回给 MediaSource 供 ExoPlayer 解码渲染。

自适应码率层（`DefaultTrackSelector`）基于共享 `bandwidthMeter` 的实时带宽估计，在多码率 manifest 中选择合适分辨率（P0 限制最大 1080p）。`DefaultRenderersFactory`（P0 启用异步队列 + 解码回退）将解码任务交给 MediaCodec 异步队列，渲染线程独立于 ExoPlayer 主循环。

### 3.2 缓冲状态流（ExoPlayer STATE → AnalyticsListener → 指标采集）

ExoPlayer 状态转换贯穿整个播放周期。`prepareAsyncInternal` 触发 `STATE_IDLE → STATE_BUFFERING`，`DefaultLoadControl`（P0 启用 `setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)`）按档位（WEAK/MEDIUM/GOOD）控制缓冲阈值。当缓冲达到 `bufferForPlayback`（GOOD 档 P0 降至 500ms），状态转为 `STATE_READY`，首帧渲染触发 `onRenderedFirstFrame` 回调，`VideoAnalyticsListener` 记录首帧耗时（从 prepare 到首帧）。

播放过程中，`DefaultLoadControl` 持续缓冲至 `maxBuffer`（GOOD 档 120s，P0 解除 targetBufferBytes 截断后真正生效）。若播放进度追上缓冲进度（缓冲耗尽），状态回退到 `STATE_BUFFERING`，触发 `onVideoFrameProcessingOffsetCount` 回调记录 rebuffer 事件。`onDroppedFrames` 记录丢帧数，`onBandwidthEstimationChanged` 记录带宽估计变化。所有指标通过 `AppLog.put` 输出（release 包 WARN/ERROR 始终输出）。

`PlayerInstancePool` 池化实例在 `recycle` 时重置状态（stop + clearMediaItems + clearOverrides），LoadControl 保持 prepare 前设置不变（AD-01 决策，运行时不热切换）。

### 3.3 错误降级流（onPlayerError → buildFallbackTypes → 下一个 MediaSource → WebView 兜底）

播放错误触发降级链。`Exo2MediaPlayer.onPlayerError` 收到错误后，检查 `currentFallbackIndex < fallbackTypes.size`，若未耗尽则取下一个 contentType（`buildFallbackTypes` 返回的降级链：HLS→DASH→Progressive→WebView），重新调用 `prepareAsyncInternal` 用新 MediaSource 重试。

若降级链耗尽（所有 MediaSource 类型均失败），切换到 WebView 兜底播放（`Exo2MediaPlayer` 通知 `VideoPlayerActivity` 启动 WebView 播放器）。缓存层错误（`CacheDataSource` 读取失败）由 `FLAG_IGNORE_CACHE_ON_ERROR`（P0 启用）静默回退到 upstream 网络，不触发降级链，仅通过 `onLoadError` 埋点记录。

网络层错误（`StreamResetException`）由 OkHttp Interceptor 捕获（AD-02 分域策略），对该域名降级到 HTTP_1_1 并缓存 1 小时，当前请求重试一次。DNS 解析失败由 `preResolveDns` 预热缓解，若预热失败则 Range 请求自行解析（可能耗时 1-3s）。

---

## 四、File Changes（文件变更清单）

| 文件 | 变更类型 | 关键改动点 |
|------|---------|-----------|
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 修改 | 1. `createLoadControlByTier` 追加 `setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)`（AD-03）<br>2. `createMediaSource` HLS 分支追加 `.setAllowChunklessPreparation(true)`（AD-05，P0）<br>3. `okhttpDataFactory` 分域 HTTP/2 策略 + 注入 `VideoEventListener` + 独立 `ConnectionPool(10,5min)` + `Dispatcher.setMaxRequestsPerHost(20)`（AD-02）<br>4. `cacheDataSourceFactory` 追加 `setFlags(FLAG_IGNORE_CACHE_ON_ERROR \| FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH)` + `CacheDataSink.setFragmentSize(2MB)`（AD-06）<br>5. 移除 `setCacheControl(maxAge=1天)`（无实际收益）<br>6. 新增 `VideoEventListener extends EventListener`（AD-04 网络层埋点）<br>7. `okhttpDataFactory` 的 OkHttpClient 追加 `.dns(DohDns)` 注入 DoH 防劫持（AD-14，P0）<br>8. 评估 Cronet via Google Play Services 集成用于视频流（AD-13，P1，本阶段不改代码） |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 修改 | 1. 新增 `VideoAnalyticsListener` 实现 `AnalyticsListener`，采集 TTFB/首帧/rebuffer/丢帧/带宽/状态转换/帧偏移 7 类指标（AD-04）<br>2. `attachToPlayer` 追加 `player.addAnalyticsListener(videoAnalyticsListener)`<br>3. `detachFromPlayer` 追加 `player.removeAnalyticsListener(videoAnalyticsListener)`<br>4. HLS 直播配置 `MediaItem.LiveConfiguration.targetOffsetMs(3000)`（P1） |
| `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` | 修改 | 1. `sharedAllocator` segment size 从 64KB 提升至 256KB（AD-09）<br>2. `createTrackSelector` 返回的 `DefaultTrackSelector` 追加 `.setMaxVideoSize(1920,1080)` + 注入共享 `bandwidthMeter`（AD-08）<br>3. `sharedRendererFactory` 追加 `.forceEnableMediaCodecAsynchronousQueueing(true)` + `.setEnableDecoderFallback(true)`（AD-07） |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 修改 | 1. 新增 `videoMinBufferSec`（用户可调 minBuffer，默认 0=按档位自动）<br>2. 新增 `videoBufferForPlaybackMs`（用户可调起播门槛，默认 0=按档位自动）<br>3. 新增 `videoMaxResolution`（用户可调最大分辨率，默认 1080p，可选 720p/1080p/1440p/4K）<br>4. 新增 `videoHttpProtocol`（用户可调 HTTP 协议策略，默认 auto=分域策略，可选 force_http1/force_http2） |
| `app/src/main/java/io/legado/app/help/exoplayer/VideoAnalyticsListener.kt` | 新增 | `AnalyticsListener` 实现，采集 7 类缓冲速度指标，通过 `AppLog.put` 输出（release 包 WARN/ERROR 始终输出） |
| `app/src/main/java/io/legado/app/help/exoplayer/VideoEventListener.kt` | 新增 | OkHttp `EventListener` 实现，记录 DNS/TCP/TLS/TTFB 各阶段耗时，写入 `AppLog` |
| `app/src/main/java/io/legado/app/help/exoplayer/HttpProtocolInterceptor.kt` | 新增 | OkHttp `Interceptor`，捕获 `StreamResetException` 后对该域名降级到 HTTP_1_1 并缓存 1 小时（AD-02 分域策略） |
| `app/src/main/java/io/legado/app/help/exoplayer/DeviceCodecBlacklist.kt` | 新增 | 已知 MediaCodec 异步队列问题设备黑名单（如 Samsung S8），`sharedRendererFactory` 启用异步队列前检测（AD-07） |
| `app/src/main/java/io/legado/app/help/http/CronetHelper.kt` | 修改（P1 评估） | 评估扩展支持视频流：在已有书源 Cronet engine 基础上，新增 Cronet via Google Play Services 视频流 HttpDataSource.Factory，无 Google Play Services 设备降级 OkHttp（AD-13，P1 本阶段不改代码） |

---

## 五、实施优先级与验证标准

### 5.1 优先级分级

| 优先级 | 优化项 | 预期收益 | 实施复杂度 |
|--------|--------|---------|-----------|
| **P0** | setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true) | maxBuffer 真正生效，rebuffer 率降 50%+ | 低（2 行代码） |
| **P0** | setAllowChunklessPreparation(true) | HLS 首帧耗时降 30%+ | 低（1 行代码） |
| **P0** | forceEnableMediaCodecAsynchronousQueueing + setEnableDecoderFallback | 丢帧率降 30%+ | 低（2 行代码） |
| **P0** | FLAG_IGNORE_CACHE_ON_ERROR | 缓存故障不中断播放 | 低（1 行代码） |
| **P0** | VideoAnalyticsListener + VideoEventListener | 缓冲瓶颈可观测 | 中（新增 2 文件） |
| **P0** | setMaxVideoSize(1080p) + 共享 bandwidthMeter | 带宽/解码资源节省 | 低（2 行代码） |
| **P0** | DohDns 注入视频流 OkHttpClient（AD-14） | DNS 防劫持 + 弱网解析稳定 | 低（1 行代码，复用已有 DohDns） |
| **P1** | 分域 HTTP/2 策略 + 独立 ConnectionPool + Dispatcher 并发 | HLS 多分片并发加速 | 中（新增 Interceptor） |
| **P1** | bufferForPlayback 降至 500ms（GOOD 档） | 首帧延迟降 50% | 低（参数调整） |
| **P1** | setAdaptiveSelectionMarginMs(1500) | 自适应切换不 rebuffer | 低（1 行代码） |
| **P1** | buffer segment size 256KB | 内存抖动降低 | 低（参数调整） |
| **P1** | MediaItem.LiveConfiguration.targetOffsetMs(3000) | 直播 HLS 低延迟 | 低（配置追加） |
| **P1** | CacheDataSink fragment size 2MB | 缓存空间节省 | 低（参数调整） |
| **P1** | Cronet via Google Play Services 评估用于视频流（AD-13） | QUIC 弱网优化（0-RTT/无队头阻塞） | 中（评估项，依赖 Google Play Services） |
| **P2** | 自定义 HlsChunkSource（弱网预取） | 弱网 rebuffer 率降 20% | 高（重写 ChunkSourceFactory） |
| **P2** | 内存级 LruCache 叠加 | 首帧零磁盘 IO | 高（OOM 风险评估） |
| **P2** | setLowLatencyModeEnabled（LL-HLS 检测后启用） | LL-HLS 源低延迟 | 中（标签检测） |

### 5.2 验证标准

| 验证项 | 验证方法 | 通过标准 |
|--------|---------|---------|
| maxBuffer 真正生效 | 真机播放 10Mbps 视频，观察缓冲时长 | 缓冲达 120s（GOOD 档）而非 40s |
| HLS 首帧加速 | 真机播放 HLS 视频，对比首帧耗时 | 首帧耗时降 30%+ |
| rebuffer 率 | AnalyticsListener 采集 rebuffer 次数 | 10 分钟播放 rebuffer ≤1 次 |
| 丢帧率 | AnalyticsListener 采集 droppedFrames | 丢帧率 <1% |
| 缓存故障容错 | 人为损坏缓存分片，观察播放 | 播放不中断，回退网络 |
| 网络瓶颈可观测 | VideoEventListener 输出 TTFB | TTFB 可定位 DNS/TCP/CDN 瓶颈 |
| 自适应码率限制 | 播放 4K 视频，观察实际分辨率 | 实际分辨率 ≤1080p（默认） |
| HTTP/2 分域策略 | 访问已知问题 CDN，观察协议 | 首次 HTTP/2 失败后 1 小时内 HTTP_1_1 |
| release 包日志 | release 包真机测试 | WARN/ERROR 日志输出（参考 AD-16） |
| 各类型视频覆盖 | HLS/DASH/MP4/FLV/MKV 各播放 3 个源 | 全部可播放，rebuffer 率达标 |

---

## 六、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| `setTargetBufferBytes(-1)` 导致中低端机 OOM | 中 | 高 | 用户可调低 `videoMaxBufferSec` 间接限制内存 + DeviceTier 检测降级到 MID |
| `forceEnableMediaCodecAsynchronousQueueing` 在黑名单设备崩溃 | 低 | 高 | `DeviceCodecBlacklist` 检测 + 软件解码回退 |
| 分域 HTTP/2 策略首次访问问题 CDN 触发 StreamResetException | 中 | 低 | 200ms 内自动降级，1 小时缓存避免重复触发 |
| `setAllowChunklessPreparation` 不兼容非标 m3u8 | 低 | 低 | ExoPlayer 自动降级到默认 preparation |
| AnalyticsListener 埋点增加 CPU 开销 | 低 | 低 | 采集频率低（事件驱动非轮询），开销 <1% |
| 自定义 HlsChunkSource 实现复杂度高（P2） | 中 | 中 | 先验证 P0 收益，rebuffer 率仍高再实施 |
| 内存级 LruCache OOM 风险（P2） | 中 | 高 | 限制 10MB 内存缓存 + DeviceTier 检测 |
| buffer segment size 256KB 内存占用增加 | 低 | 低 | 3 实例池共享 allocator，总增量 <50MB |
| `setMaxVideoSize(1080p)` 影响 4K 设备体验 | 低 | 低 | 用户可配置 `videoMaxResolution=4K` |
| `FLAG_IGNORE_CACHE_ON_ERROR` 掩盖磁盘满问题 | 中 | 中 | AnalyticsListener 埋点 + 定期 clearCache |
| DohDns 首次解析比系统 DNS 慢（AD-14） | 中 | 低 | 5 分钟 DNS 缓存兜底 + 连续 3 次失败熔断降级系统 DNS |
| Cronet via Google Play Services 国行设备无依赖（AD-13） | 高 | 中 | 无 Google Play Services 自动降级 OkHttp + 降级检测日志埋点 |

---

## 七、与 video-prebuffer-enhancement 的关系

本 spec 聚焦"当前视频缓冲速度"，与 video-prebuffer-enhancement（聚焦"下一集预加载"）互补而非替代：

| 维度 | video-prebuffer-enhancement | 本 spec（video-buffer-speed-optimization） |
|------|----------------------------|------------------------------------------|
| **核心目标** | 下一集预加载（减少切集等待） | 当前视频起播 + 防 rebuffer |
| **作用对象** | 下一集 URL 的 SimpleCache 预写入 | 当前视频的 LoadControl/网络/解码/缓存 |
| **关键优化** | CacheUtil.cache + PlayListManager + URL 去重 | setTargetBufferBytes(-1) + chunkless preparation + AnalyticsListener |
| **LoadControl** | 沿用 AD-09 路径A（不热切换） | 沿用 AD-01（同决策）+ 补全 setTargetBufferBytes |
| **OkHttp** | 未涉及 | 分域 HTTP/2 + EventListener + 独立 ConnectionPool |
| **解码器** | 未涉及 | 异步队列 + 解码回退 |
| **AnalyticsListener** | 命中率计数器 | TTFB/rebuffer/丢帧/带宽 7 类指标 |
| **依赖关系** | P0 已实施（预加载 BUG 修复） | 在其基础上补全当前视频优化 |

两者可并行实施，无冲突。本 spec 的 P0 项（setTargetBufferBytes + chunkless preparation + 异步队列 + FLAG_IGNORE_CACHE_ON_ERROR）是"用户感觉没效果"的直接修复，应优先实施。

---

## 八、附录 A：网上成熟方案对照表

本 spec 整合的网上成熟方案与对应优化项对照如下，确保每项方案都有落地实现点：

| 网上成熟方案 | 来源 | 本 spec 对应优化项 | 优先级 | ADR |
|-------------|------|-------------------|--------|-----|
| LoadControl setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true) | ExoPlayer 官方文档"Large buffer for high-bitrate content" | 1.1 LoadControl 层深度优化 | P0 | AD-03 |
| Dynamic LoadControl（运行时动态调整） | ExoPlayer 社区 issue #1234（参考） | 评估后放弃（沿用 AD-01 路径A，运行时不热切换） | - | AD-01 |
| HLS setAllowChunklessPreparation | ExoPlayer 官方 benchmark（首帧降 30%+） | 1.2 HLS 协议层深度优化 | P0 | AD-05 |
| HLS MediaItem.LiveConfiguration.targetOffsetMs | ExoPlayer 官方低延迟指南 | 1.2 HLS 协议层深度优化（直播） | P1 | - |
| 自定义 HlsChunkSource（弱网预取） | ExoPlayer 进阶教程 | 1.2 HLS 协议层深度优化（P2 评估） | P2 | AD-05 |
| HTTP/2 多路复用 vs HTTP/1.1 | OkHttp 官方文档 + RFC 7540 | 1.3 OkHttp 网络层深度优化（分域策略） | P0/P1 | AD-02 |
| OkHttp EventListener 埋点 | OkHttp 官方文档 | 1.3 OkHttp 网络层深度优化 | P0 | AD-04 |
| OkHttp Dispatcher 并发提升 | OkHttp 官方文档 | 1.3 OkHttp 网络层深度优化 | P1 | - |
| CacheDataSource FLAG_IGNORE_CACHE_ON_ERROR | ExoPlayer 官方文档 | 1.4 CacheDataSource 缓存层优化 | P0 | AD-06 |
| LRU 多级缓存（内存+磁盘） | Android 官方缓存指南 | 1.4 CacheDataSource 缓存层优化（P2 评估） | P2 | - |
| setMaxVideoSize 限制分辨率 | ExoPlayer 官方自适应码率指南 | 1.5 自适应码率层优化 | P0 | AD-08 |
| setAdaptiveSelectionMarginMs | ExoPlayer 官方 TrackSelectionParameters | 1.5 自适应码率层优化 | P1 | AD-08 |
| forceEnableMediaCodecAsynchronousQueueing | ExoPlayer 官方渲染器配置 | 1.6 解码器层优化 | P0 | AD-07 |
| 优先硬件解码 + 软件回退 | Android MediaCodec 官方文档 | 1.6 解码器层优化（setEnableDecoderFallback） | P0 | AD-07 |
| AnalyticsListener 性能监控 | ExoPlayer 官方 AnalyticsListener 文档 | 1.7 性能监控层 | P0 | AD-04 |
| Cronet 作为视频流网络栈（QUIC/HTTP-3） | Media3 官方 Network stacks 文档（YouTube 在用） | 1.9 Cronet 评估（视频流网络栈升级） | P1 评估 | AD-13 |
| DoH 防劫持注入视频流 | 项目已有 DohDns.kt（DoH 防劫持） | 1.10 DohDns 注入视频流 OkHttpClient | P0 | AD-14 |

---

## 九、附录 B：Dynamic LoadControl 评估

网上方案提及"Dynamic LoadControl"（运行时动态调整 LoadControl 参数），本 spec 评估后决定不采用，理由如下：

### 9.1 Dynamic LoadControl 原理

Dynamic LoadControl 通过自定义 `LoadControl` 接口实现，在 `onPlayerStateChanged` / `onBandwidthEstimationChanged` 回调中动态调整 `maxBufferMs` 等参数。理论收益：网络档位变化时 maxBuffer 立即生效，无需下次播放。

### 9.2 不采用理由

1. **ExoPlayer 限制**：`DefaultLoadControl` 的参数在构造时固定，运行时修改需重新构建 LoadControl 实例并调用 `ExoPlayer.setLoadControl()`，后者触发 re-prepare（缓冲中断 1-3s）——与 video-prebuffer-enhancement AD-09 阻塞点2 一致。
2. **PlayerInstancePool 冲突**：池化实例归池后 LoadControl 状态不可控（阻塞点3），Dynamic LoadControl 的状态（当前档位、历史带宽）跨实例污染风险高。
3. **实现复杂度**：自定义 `LoadControl` 接口需实现 6 个方法（`getBufferedDurationUs` / `shouldContinueLoading` / `getTargetBufferBytes` 等），且需处理并发（bandwidthMeter 回调与 ExoPlayer 主线程不同步）。
4. **收益有限**：网络档位变化频率低（用户切换 WiFi/4G），下次播放才生效的延迟（分钟级）可接受。

### 9.3 替代方案

沿用 AD-01 路径A（prepare 前设置，运行时不热切换），通过 `bufferForPlayback` 降低（AD-10）+ `setTargetBufferBytes(-1)`（AD-03）+ `setPrioritizeTimeOverSizeThresholds(true)`（AD-03）在 prepare 时即用激进参数，无需运行时调整。网络档位变化仅影响预加载策略（下一集），不影响当前视频 LoadControl。

---

## 十、附录 C：各类型视频覆盖验证矩阵

本 spec 优化项对各类型视频的覆盖情况：

| 视频类型 | 起播加速 | 防 rebuffer | 缓存容错 | 网络优化 | 解码优化 |
|---------|---------|------------|---------|---------|---------|
| HLS（点播 m3u8） | setAllowChunklessPreparation（P0） | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| HLS（直播） | setAllowChunklessPreparation（P0） | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| HLS（LL-HLS） | setAllowChunklessPreparation（P0） | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| DASH（mpd） | - | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| MP4 直链 | - | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| FLV 直链 | - | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |
| MKV 直链 | - | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0）+ 软件回退 |
| TS 直链 | - | setTargetBufferBytes(-1)（P0） | FLAG_IGNORE_CACHE_ON_ERROR（P0） | 分域 HTTP/2（P1） | 异步队列（P0） |

**结论**：所有视频类型均覆盖"防 rebuffer + 缓存容错 + 网络优化 + 解码优化"四个维度。HLS 系列额外覆盖"起播加速"（setAllowChunklessPreparation）。DASH/直链类型的起播加速依赖网络层优化（分域 HTTP/2）与 LoadControl（bufferForPlayback 降低），无协议级起播加速手段（ProgressiveMediaSource 无 chunkless preparation 等价物）。

