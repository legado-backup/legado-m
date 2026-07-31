# 视频缓冲速度优化 - 需求规格

> 状态：🔄 设计中（基于 ExoPlayer Media3 + OkHttp + CacheDataSource 七层深度调优 + DohDns 注入 + Cronet 评估）
> 创建时间：2026-07-28
> 最后修订：2026-07-28（修复审查发现的 9 项意淫 + 6 项与 design.md 矛盾 + 补充 Cronet/DohDns 评估）
> 任务来源：用户反馈"已实施 HLS 首次加载优化 + 扩大缓冲区 + OkHttp 连接池三项优化后效果不明显，视频仍卡顿"
> 关联项目：exoplayer-resilience（韧性）、player-review-and-optimization（深度优化）、video-m3u8-cache（缓存）、video-prebuffer-enhancement（预加载边界）
> 权威源：参数与架构决策以 [design.md](./design.md) 为权威源，本 spec 仅作需求意图与验证标准

## Intent（意图）

### 设计意图

聚焦当前播放视频的缓冲速度提升，解决"已实施三项优化仍卡顿"问题。已实施的三项优化（HLS 首次加载优化 + 扩大缓冲区 + OkHttp 连接池）属于浅层调参，未触及 ExoPlayer 缓冲链路的瓶颈点。本次设计深入到 LoadControl 策略、HLS ChunkSource 配置、OkHttp 超时与并发、CacheDataSource 容错、自适应码率限制、解码器异步队列、性能监控、DohDns 注入等 8 个层面，针对中高端机型采用激进策略，并提供用户可调档位。

### 痛点证据

| 症状 | 当前状态 | 用户影响 |
|------|---------|---------|
| 视频卡顿 | 已扩大 maxBuffer 30s→120s，无明显改善 | 播放中断，需等待缓冲 |
| 首帧加载慢 | HLS chunkless preparation 未实际启用（design.md L55 诚实承认） | 仍需数秒才能开始播放 |
| 弱网切换 | 无自适应码率限制 | 高码率无法降级，频繁卡顿 |
| 故障定位难 | 无性能监控埋点 | 无法区分网络/解码/缓冲问题 |
| DNS 污染 | 视频流 OkHttpClient 未注入 DohDns | 分片加载失败触发降级链 |

### 用户原话

> "已实施 HLS 首次加载优化 + 扩大缓冲区 + OkHttp 连接池，效果不明显，视频仍卡顿"

### 设计原则

1. **聚焦当前视频缓冲**：不预加载下一个视频（属于 video-prebuffer-enhancement 范畴）
2. **激进策略优先**：默认面向中高端机，弱设备用户可通过播放器设置降档
3. **统一策略覆盖全格式**：HLS/DASH/MP4/FLV 等共用激进缓冲策略
4. **可观测性先行**：所有优化必须有 AnalyticsListener 监控指标支撑验证
5. **与 design.md 一致**：参数与架构决策以 design.md 为权威源，禁止 spec.md 单方面新增参数
6. **复用已有基础设施**：DohDns、CronetHelper 等项目已有组件优先复用，避免重复造轮子

## Scope（范围）

### In Scope（本次实现）

1. **LoadControl 深度调优**：setTargetBufferBytes(-1) 禁用大小限制、setPrioritizeTimeOverSizeThresholds(true)、保留现有三档静态参数（与 design.md 1.1.3 一致，不热切换）
2. **HLS 低延迟深度优化**：setAllowChunklessPreparation(true)（实际未启用，需新增）、直播场景配置 MediaItem.LiveConfiguration.targetOffsetMs、自定义 LoadErrorHandlingPolicy 子类
3. **OkHttp 连接池深度优化**：EventListener 监听 DNS/连接/TLS 耗时、Dispatcher 并发控制、connectTimeout(10s)/readTimeout(15s)/writeTimeout(15s)（与 design.md + tasks.md 一致）
4. **CacheDataSource 优化**：FLAG_IGNORE_CACHE_ON_ERROR、FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH、LeastRecentlyUsedCacheEvictor、CacheDataSink fragment size 2MB
5. **自适应码率**：setMaxVideoSize(1920, 1080) 限制 1080p（与 design.md AD-08 一致）、setAdaptiveSelectionMarginMs(1500)、setMinDurationForQualityIncreaseMs(20000)、注入共享 bandwidthMeter
6. **解码器优化**：forceEnableMediaCodecAsynchronousQueueing()、setEnableDecoderFallback(true)、保留 DefaultMediaCodecSelector.DEFAULT（已优先硬解）
7. **性能监控**：AnalyticsListener 监控 TTFB/缓冲中断/丢帧率/带宽利用率
8. **DohDns 注入**：视频流 OkHttpClient 注入 DohDns（复用项目已有 DohDns.kt）
9. **Cronet 评估**：在 Alternatives Considered 中评估 Cronet via Google Play Services 方案

### Out of Scope（本次不做）

- **下一个视频预加载**：属于 `video-prebuffer-enhancement` 项目范畴
- **播放器架构重写**：保留 ExoPlayer + GSY 双引擎架构
- **DRM 解密**：当前业务无 DRM 视频，不引入
- **视频格式嗅探**：属于 `exoplayer-resilience` 项目
- **WebView 降级**：属于 `exoplayer-resilience` 项目
- **视频网站规则引擎**：CSS/JSONPath/XPath/JS 解析不在本次范围
- **LoadControl 运行时热切换**：已被 design.md AD-01 否决（路径 A，prepare 前设置，运行时不热切换）
- **自定义 HlsChunkSourceFactory**：过度工程，降级为 P2 评估（与 design.md AD-05 一致）
- **自定义 MediaCodecSelector**：DefaultMediaCodecSelector.DEFAULT 已优先硬解，无需自定义
- **Extractor 重写**：默认 Extractor 已优化良好，不修改

## Approach（技术方案）

### Selected Approach：七层激进调优 + DohDns 注入 + Cronet 评估

选定**LoadControl 静态调优 + HLS 低延迟 + OkHttp 监控 + Cache 容错 + 码率限制 + 异步解码 + 性能埋点 + DohDns 注入**的组合方案，理由如下：

**为什么不只用 LoadControl 静态调参？**
已实施的 `createLoadControlByTier(WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s)` 仅调整了 minBuffer/maxBuffer 两个静态参数，但 ExoPlayer 实际加载决策还受 targetBufferBytes、prioritizeTimeOverSizeThresholds 等多个因素影响。`setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)` 是修复"maxBuffer=120s 被 50MB 截断"根因的关键（design.md 1.8.2 第一根因）。

**为什么放弃 LoadControl 运行时热切换？**
design.md AD-01 + 附录 B 已明确否决 Dynamic LoadControl，理由：触发 re-prepare 中断 1-3s、PlayerInstancePool 池化冲突、实现复杂度高、收益有限。本 spec 沿用路径 A（prepare 前设置，运行时不热切换），与 video-prebuffer-enhancement AD-09 决策一致。

**为什么需要七层联合 + DohDns？**
视频卡顿的根因可能分布在以下任一层：

- **网络层**：DNS 慢/污染、连接复用率低、超时设置不合理 → OkHttp 层 + DohDns 注入
- **协议层**：HLS 分片加载慢、错误重试策略保守 → HLS 层
- **缓存层**：缓存读失败未降级、LRU 淘汰过激 → CacheDataSource 层
- **策略层**：缓冲大小限制、加载停止时机错误 → LoadControl 层
- **码率层**：高码率无降级、码率提升时机过激进 → AdaptiveTrackSelection 层
- **解码层**：MediaCodec 同步队列阻塞 → 解码器层
- **监控层**：无指标无法定位 → AnalyticsListener 层

任一层缺失都会导致整体效果不明显，这正是已实施三项优化"没效果"的根因。DohDns 注入是补齐网络层 DNS 污染防护的关键（项目已有 DohDns.kt，仅需 1 行注入视频流 OkHttpClient）。

### 方案分项

#### 1. LoadControl 静态调优（核心）

- 启用 `DefaultLoadControl.Builder().setTargetBufferBytes(-1)`：禁用默认 50MB 大小限制，让缓冲完全由 maxBuffer 时长控制（修复 design.md 1.8.2 第一根因）
- 启用 `setPrioritizeTimeOverSizeThresholds(true)`：达到时间阈值即停止加载，确保 maxBuffer=120s 真正生效
- 保留现有 `createLoadControlByTier` 三档静态参数（与 design.md 1.1.3 + 实际代码一致）：
  - WEAK: 5s/30s, bufferForPlayback=500ms
  - MEDIUM: 8s/90s, bufferForPlayback=800ms
  - GOOD: 8s/120s, bufferForPlayback=500ms
- **不实施运行时热切换**（路径 A，与 design.md AD-01 一致）

#### 2. HLS 低延迟优化（区分 VOD/LIVE）

- `setAllowChunklessPreparation(true)`：HLS 首帧耗时降 30%+（修复 design.md 1.8.3 第二根因，当前代码未启用）
- **直播场景（LIVE）**：配置 `MediaItem.LiveConfiguration.Builder().setTargetOffsetMs(2000).setMinOffsetMs(1000).setMaxOffsetMs(5000).setMinPlaybackSpeed(0.95f).setMaxPlaybackSpeed(1.05f)`
- **点播场景（VOD）**：不配置 LiveConfiguration（点播无直播时延概念，配置无意义）
- 自定义 `HlsLoadErrorPolicy extends DefaultLoadErrorHandlingPolicy`：重写 `getRetryDelayMsFor` 返回 3000ms（5xx 错误重试间隔 3 秒，避免雪崩）
- `setLowLatencyModeEnabled(true)`：仅对 LL-HLS 源启用（通过 m3u8 `#EXT-X-SERVER-CONTROL` 标签检测），避免对非 LL-HLS 源产生副作用

#### 3. OkHttp 监控与超时优化

- 新增 `OkHttpEventListener extends EventListener`：监听 `dnsStart/dnsEnd/connectStart/connectEnd/secureConnectStart/secureConnectEnd/responseBodyStart` 各阶段耗时
- `connectTimeout(10, TimeUnit.SECONDS)`：与 tasks.md §3.2 一致（删除原 spec 的 1s 激进超时，弱网必然超时）
- `readTimeout(15, TimeUnit.SECONDS)`：与 tasks.md §3.2 一致（删除原 spec 的 500ms 激进超时，弱网必然超时）
- `writeTimeout(15, TimeUnit.SECONDS)`：与 readTimeout 一致
- `callTimeout(30, TimeUnit.SECONDS)`：单次请求总超时 30 秒
- `Dispatcher.setMaxRequests(64)` + `setMaxRequestsPerHost(16)`：提升并发能力
- 独立 `ConnectionPool(10, 5min)`：与书源请求池隔离（design.md 1.3.3 P1）

#### 4. CacheDataSource 容错优化

- 启用 `CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR`：缓存读失败时降级到网络，不抛异常
- 启用 `CacheDataSource.FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`：缓存长度不匹配时忽略继续播放
- 使用 `LeastRecentlyUsedCacheEvictor`：LRU 淘汰策略（项目已用，保留）
- 缓存大小保留 `VideoPlay.videoCacheSize` 默认 100MB，范围 50-2048MB（与 design.md 1.4.1 一致，不强制 512MB）
- `CacheDataSink.Factory.setFragmentSize(2MB)`：HLS 小分片写入节省空间（design.md 1.4.3 P1）

#### 5. 自适应码率限制

- `TrackSelectionParameters.Builder().setMaxVideoSize(1920, 1080)`：限制最大 1080p（与 design.md AD-08 一致，删除原 spec 的 setMaxVideoSizeSd 720p）
- `setAdaptiveSelectionMarginMs(1500)`：码率切换留 1.5 秒缓冲
- `setMinDurationForQualityIncreaseMs(20000)`：码率提升需 20 秒稳定播放（避免抖动）
- 注入共享 `ExoPlayerHelper.bandwidthMeter`：确保 LoadControl 与 TrackSelector 基于同一带宽测量（design.md AD-12）
- **不配置 setViewportSize**：单独调用效果有限，需配合 setViewportOrientationSensitive，本次不引入（降级为 P2 评估）

#### 6. 解码器异步队列

- `DefaultRenderersFactory.forceEnableMediaCodecAsynchronousQueueing()`：启用 MediaCodec 异步模式（API 23+）
- `setEnableDecoderFallback(true)`：解码失败自动降级到备用解码器
- `setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)`：优先 ffmpeg 扩展（已配置，保留）
- **保留 DefaultMediaCodecSelector.DEFAULT**：已优先硬件解码（ExoPlayer 官方实现），不自定义 MediaCodecSelector
- WEAK 档位降级：deviceTier=WEAK 时不启用异步队列（避免低端机崩溃）

#### 7. 性能监控埋点

- 新增 `ExoPlayerAnalyticsListener implements AnalyticsListener`：
  - `onLoadStarted`：记录 TTFB 起始时间
  - `onLoadCompleted`：计算 TTFB、加载耗时、带宽
  - `onDroppedVideoFrames`：丢帧率
  - `onVideoInputFormatChanged`：码率切换次数
  - `onPlayerStateChanged`：缓冲状态变化次数
  - `onBandwidthEstimate`：带宽利用率
  - `onRenderedFirstFrame`：首帧耗时
- 关键指标阈值（分档）：
  - 好网（GOOD）：TTFB < 500ms、缓冲中断 < 1 次/小时、丢帧率 < 0.1%、带宽利用率 > 80%
  - 中网（MEDIUM）：TTFB < 1s、缓冲中断 < 3 次/小时、丢帧率 < 0.5%
  - 弱网（WEAK）：TTFB < 2s、缓冲中断 < 5 次/小时、丢帧率 < 1%

#### 8. DohDns 注入（新增，复用已有组件）

- 项目已有 `DohDns.kt`（DoH，DNS over HTTPS，防劫持+降时延），仅注入 HttpHelper 的书源 OkHttpClient
- 视频流 OkHttpClient 通过 `.dns(DohDns)` 注入，复用已有实现
- 视频流 DNS 污染/劫持会导致分片加载失败触发降级链，与缓冲速度直接相关（review-completeness.md 遗漏点 2）

#### 9. Cronet 评估（新增，仅评估不实施）

- 项目已有 `CronetHelper.kt` 启用 QUIC/HTTP-3/HTTP-2/Brotli/AsyncDNS，仅用于书源请求
- Media3 官方文档明确推荐 Cronet 用于流媒体，YouTube 在用
- 评估两种集成方式：
  - **Cronet via Google Play Services**：0 APK 体积增量，依赖 Google Play Services（部分国产机无）
  - **Cronet embedded**：1.5MB APK 体积增量，无外部依赖
- 本次仅评估，不实施（详见 Alternatives Considered 方案 7）

### Alternatives Considered（否决的替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 方案1：Dynamic LoadControl 运行时热切换 | 自定义 AdaptiveLoadControl 重写 shouldContinueLoading，根据实时带宽动态调整 | **已否决**（design.md AD-01 + 附录 B）。理由：触发 re-prepare 中断 1-3s、PlayerInstancePool 池化冲突、实现复杂度高、收益有限。本 spec 沿用路径 A（prepare 前设置，运行时不热切换） |
| 方案2：HTTP/2 多路复用强制启用 | OkHttp 强制启用 HTTP/2，单连接多路复用减少握手开销 | 部分视频 CDN 的 HTTP/2 实现有 bug（历史 22 次 StreamResetException），强制 HTTP_2 风险高。采用 design.md AD-02 分域策略：默认 HTTP/2，捕获 StreamResetException 后对该域名降级 HTTP_1_1 并缓存 1 小时 |
| 方案3：完全自定义 ChunkSource 替代默认 HlsMediaSource | 完全自定义 HLS 分片加载策略，调高 maxSegmentsToLoad 从 3 到 6 | **已否决为 P2 评估**（design.md AD-05）。理由：实现复杂度高（需重写 HlsMediaSource.Factory.setChunkSourceFactory），维护成本大。P0 先启用 setAllowChunklessPreparation，rebuffer 率仍 >5% 再评估 |
| 方案4：CacheUtil 主动预加载当前视频关键分片 | 用 CacheUtil.cache() 在 prepare 前预加载前 N 个分片 | 与"不预加载下一个视频"原则边界模糊，且预加载当前视频前几个分片会增加首帧延迟。改为通过 setTargetBufferBytes(-1) 让 ExoPlayer 自主决定加载深度 |
| 方案5：完全开放码率不限制 | 不调 setMaxVideoSize，让 ExoPlayer 按带宽自适应选最高码率 | 高码率会快速耗尽缓冲，弱网下加剧卡顿。限制 1080p（与 design.md AD-08 一致）是激进策略与稳定性的平衡，4K 设备用户可手动调高 |
| 方案6：MediaCodec 同步队列（保持现状） | 不启用 forceEnableMediaCodecAsynchronousQueueing | 同步模式在 4K/高码率场景会阻塞渲染线程，异步模式（API 23+）能提升 10-20% 解码吞吐。本次面向中高端机，minSdk=23，可启用 |
| 方案7：Cronet 替代 OkHttp 作为视频流 HttpDataSource | 用 Cronet 作为 HttpDataSource，复用项目已有 CronetHelper（QUIC/HTTP-3/Brotli） | **评估中，本次不实施**。Cronet via Google Play Services 0 体积增量但依赖 Google Play Services（部分国产机无）；Cronet embedded 1.5MB 体积增量。Cronet 的 QUIC 0-RTT 对弱网收益显著（YouTube 在用），可能比 OkHttp 调参更有效。本次先实施 OkHttp 七层调优 + DohDns 注入，验证收益后再评估 Cronet 集成（P2） |
| 方案8：自定义 Extractor 替代默认 | 重写 MP4/FLV Extractor | 维护成本极高，且 ExoPlayer 默认 Extractor 已优化良好。本次不修改 Extractor 层 |
| 方案9：FLAG_BLOCK_ON_CACHE_WRITE 启用 | 启用 CacheDataSource.FLAG_BLOCK_ON_CACHE_WRITE（缓存写入时不阻塞读取） | design.md 1.4.3 未提此 flag，且 FLAG_IGNORE_CACHE_ON_ERROR + FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH 已提供足够容错。本次不启用，避免引入未经评估的行为 |
| 方案10：setBackBuffer 启用 | 启用 setBackBuffer(30000, true) 保留 30 秒后向缓冲支持快速回看 | design.md + tasks.md 均未提及，spec.md 单方面新增无依据。retainBackBufferFromKeyframe=true 在某些场景可能导致内存占用增加。本次不启用，降级为 P2 评估 |
| 方案11：自定义 MediaCodecSelector 硬解优先 | 自定义 MediaCodecSelector 优先选择 OMX.qcom.* / OMX.Exynos.* 硬件解码器 | DefaultMediaCodecSelector.DEFAULT 已优先硬件解码（ExoPlayer 官方实现），自定义维护成本极高（需跟踪各厂商解码器命名变化）。本次不自定义 |
| 方案12：内存级 LruCache 叠加 | 叠加内存级 LruCache 缓存首帧数据 | design.md 1.4.3 已评估为 P2，OOM 风险高，需真机验证。本次不实施 |

### Drawbacks（选定方案的缺点）

1. **setTargetBufferBytes(-1) 可能导致中低端机 OOM**：解除内存上限后，高码率视频缓冲可能耗尽内存。**接受理由**：用户可调低 `videoMaxBufferSec` 间接限制内存 + DeviceTier 检测降级到 MEDIUM
2. **setMaxVideoSize(1080p) 限制最高清晰度**：4K 设备用户在好网下无法看 4K。**接受理由**：用户可通过 `videoMaxResolution` 手动调高，默认 1080p 是稳定性优先
3. **异步解码在低端机可能崩溃**：部分低端机 MediaCodec 异步模式实现有 bug。**接受理由**：通过 deviceTier 判断，WEAK 档位降级为同步模式 + DeviceCodecBlacklist 黑名单
4. **性能监控埋点有性能开销**：AnalyticsListener 频繁回调影响主线程。**接受理由**：使用 `AppLog.put`（已封装主线程调度），开销可控（<1% CPU）
5. **DohDns 注入增加 DNS 解析延迟**：DoH 通过 HTTPS 解析 DNS，比原生 DNS 慢。**接受理由**：DohDns 已在书源请求验证可用，视频流复用已有实现，防劫持收益大于解析延迟

### Prior Art（参考）

- Media3 ExoPlayer 官方文档：LoadControl 缓冲策略、Network stacks（Cronet/OkHttp 对比）、AnalyticsListener
- Media3 DefaultLoadControl 源码（androidx.media3.exoplayer.upstream）
- Google ExoPlayer 案例：低延迟 HLS 直播配置、chunkless preparation benchmark
- OkHttp 官方文档：EventListener 性能监控、Dispatcher 并发控制
- ExoPlayer 自适应码率调优官方文档
- 项目内 `CronetHelper.kt`（QUIC/HTTP-3/Brotli/AsyncDNS 已启用）
- 项目内 `DohDns.kt`（DoH 防劫持已实现）
- 项目内 `exoplayer-resilience` 项目（韧性优化基础）
- 项目内 `player-review-and-optimization` 项目（播放器深度优化分析）
- 项目内 `video-m3u8-cache` 项目（缓存基础）
- 项目内 `video-prebuffer-enhancement` 项目（预加载边界，AD-09 路径 A 决策）

## Requirements（需求）

### R1：LoadControl 必须启用 setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true)

- **R1.1** 修改 `ExoPlayerHelper.createLoadControlByTier`：所有档位 `setTargetBufferBytes(-1)`，禁用默认 50MB 大小限制
- **R1.2** 启用 `setPrioritizeTimeOverSizeThresholds(true)`：达到时间阈值即停止加载
- **R1.3** 保留现有三档 minBuffer/maxBuffer 静态参数（与 design.md 1.1.3 + 实际代码一致）：
  - WEAK: 5s/30s, bufferForPlayback=500ms, bufferForPlaybackAfterRebuffer=1s
  - MEDIUM: 8s/90s, bufferForPlayback=800ms, bufferForPlaybackAfterRebuffer=2s
  - GOOD: 8s/120s, bufferForPlayback=500ms, bufferForPlaybackAfterRebuffer=2s
- **R1.4** 调整 `bufferForPlayback`（与 design.md AD-10 一致）：GOOD 档 1s→500ms，MEDIUM 档 1s→800ms，WEAK 档保留 500ms
- **R1.5** 验证方法：grep "setTargetBufferBytes\|setPrioritizeTimeOverSizeThresholds" 确认所有档位启用

### R2：HLS 必须配置 setAllowChunklessPreparation + 直播场景 LiveConfiguration

- **R2.1** 在 `ExoPlayerHelper.createMediaSource` HLS 分支追加 `.setAllowChunklessPreparation(true)`（当前代码未启用，design.md L55 诚实承认）
- **R2.2** **直播场景（LIVE）**：配置 `MediaItem.LiveConfiguration.Builder().setTargetOffsetMs(2000).setMinOffsetMs(1000).setMaxOffsetMs(5000).setMinPlaybackSpeed(0.95f).setMaxPlaybackSpeed(1.05f)`
- **R2.3** **点播场景（VOD）**：不配置 LiveConfiguration（点播无直播时延概念，配置无意义）
- **R2.4** `setLowLatencyModeEnabled(true)`：仅对 LL-HLS 源启用（通过 m3u8 `#EXT-X-SERVER-CONTROL` 标签检测），避免对非 LL-HLS 源产生副作用
- **R2.5** 验证方法：grep "setAllowChunklessPreparation\|LiveConfiguration\|targetOffsetMs" 确认配置存在；确认 VOD 场景未配置 LiveConfiguration

### R3：OkHttp 必须配置 EventListener 监听各阶段耗时

- **R3.1** 新增 `OkHttpEventListener extends EventListener`：实现 dnsStart/dnsEnd/connectStart/connectEnd/secureConnectStart/secureConnectEnd/responseBodyStart 等回调
- **R3.2** 每个阶段记录耗时到 `AppLog.put("OkHttpStage", stageName + "=" + durationMs + "ms")`
- **R3.3** 在 `ExoPlayerHelper.getOkHttpClient` 中通过 `.eventListenerFactory()` 注入
- **R3.4** 单次请求各阶段耗时超阈值（DNS>200ms/Connect>500ms/TLS>500ms）时输出 WARN 日志
- **R3.5** 验证方法：logcat 过滤 "OkHttpStage" Tag，确认每个请求输出各阶段耗时

### R4：CacheDataSource 必须启用 FLAG_IGNORE_CACHE_ON_ERROR

- **R4.1** 在 `ExoPlayerHelper.buildCacheDataSource` 中启用 `CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR`
- **R4.2** 启用 `CacheDataSource.FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`：缓存长度不匹配时忽略继续播放
- **R4.3** 确认使用 `LeastRecentlyUsedCacheEvictor`（默认已用，需 grep 验证）
- **R4.4** 缓存大小保留 `VideoPlay.videoCacheSize` 默认 100MB，范围 50-2048MB（与 design.md 1.4.1 一致，不强制 512MB）
- **R4.5** `CacheDataSink.Factory.setFragmentSize(2MB)`：HLS 小分片写入节省空间（design.md 1.4.3 P1）
- **R4.6** 验证方法：grep "FLAG_IGNORE_CACHE_ON_ERROR\|FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH" 确认启用

### R5：自适应码率必须配置 setMaxVideoSize(1920, 1080) + setAdaptiveSelectionMarginMs(1500)

- **R5.1** 在 `ExoPlayerHelper.createTrackSelectionParameters` 中调用 `TrackSelectionParameters.Builder().setMaxVideoSize(1920, 1080)`（与 design.md AD-08 一致，删除原 spec 的 setMaxVideoSizeSd 720p）
- **R5.2** 配置 `setAdaptiveSelectionMarginMs(1500)`：码率切换留 1.5 秒缓冲
- **R5.3** 配置 `setMinDurationForQualityIncreaseMs(20000)`：码率提升需 20 秒稳定播放
- **R5.4** 注入共享 `ExoPlayerHelper.bandwidthMeter` 到 `DefaultTrackSelector`：确保 LoadControl 与 TrackSelector 基于同一带宽测量（design.md AD-12）
- **R5.5** **不配置 setViewportSize**：单独调用效果有限，需配合 setViewportOrientationSensitive，本次不引入（降级为 P2 评估）
- **R5.6** 验证方法：grep "setMaxVideoSize\|setAdaptiveSelectionMarginMs" 确认配置

### R6：解码器必须启用 forceEnableMediaCodecAsynchronousQueueing()

- **R6.1** 在 `ExoPlayerHelper.createRenderersFactory` 中调用 `DefaultRenderersFactory(context).forceEnableMediaCodecAsynchronousQueueing()`
- **R6.2** 配置 `setEnableDecoderFallback(true)`：解码失败自动降级到备用解码器
- **R6.3** 配置 `setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)`：优先 ffmpeg 扩展（已配置，保留）
- **R6.4** **保留 DefaultMediaCodecSelector.DEFAULT**：已优先硬件解码（ExoPlayer 官方实现），不自定义 MediaCodecSelector
- **R6.5** WEAK 档位降级：deviceTier=WEAK 时不启用异步队列（避免低端机崩溃）
- **R6.6** 验证方法：grep "forceEnableMediaCodecAsynchronousQueueing\|setEnableDecoderFallback" 确认启用

### R7：必须新增 AnalyticsListener 监控 TTFB/缓冲中断/丢帧率/带宽利用率

- **R7.1** 新增 `ExoPlayerAnalyticsListener.kt` 实现 `AnalyticsListener`
- **R7.2** 实现 `onLoadStarted`：记录 TTFB 起始时间到 Map
- **R7.3** 实现 `onLoadCompleted`：计算 TTFB = loadCompletedMs - loadStartedMs，输出到 AppLog
- **R7.4** 实现 `onDroppedVideoFrames`：累计丢帧数，计算丢帧率 = dropped / total
- **R7.5** 实现 `onVideoInputFormatChanged`：累计码率切换次数
- **R7.6** 实现 `onPlayerStateChanged`：累计 STATE_BUFFERING 出现次数（缓冲中断 = 次数 - 1）
- **R7.7** 实现 `onBandwidthEstimate`：记录带宽利用率 = 实际下载速度 / 估算带宽
- **R7.8** 实现 `onRenderedFirstFrame`：首帧耗时（从 prepare 到首帧渲染）
- **R7.9** 每分钟输出一次汇总日志：TTFB平均/最大、缓冲中断次数、丢帧率、码率切换次数
- **R7.10** 在 `Exo2MediaPlayer.prepare` 中通过 `player.addAnalyticsListener()` 注入
- **R7.11** 验证方法：logcat 过滤 "ExoAnalytics" Tag，确认每分钟输出汇总

### R8：OkHttp 超时必须与 design.md + tasks.md 一致

- **R8.1** `connectTimeout(10, TimeUnit.SECONDS)`：连接超时 10 秒（与 tasks.md §3.2 一致，删除原 spec 的 1s 激进超时）
- **R8.2** `readTimeout(15, TimeUnit.SECONDS)`：读取超时 15 秒（与 tasks.md §3.2 一致，删除原 spec 的 500ms 激进超时）
- **R8.3** `writeTimeout(15, TimeUnit.SECONDS)`：写入超时 15 秒（与 readTimeout 一致）
- **R8.4** `callTimeout(30, TimeUnit.SECONDS)`：单次请求总超时 30 秒（与 tasks.md §4.4 一致）
- **R8.5** 独立 `ConnectionPool(10, 5, TimeUnit.MINUTES)`：与书源请求池隔离（design.md 1.3.3 P1）
- **R8.6** 保留 `Protocol.HTTP_1_1` 作为降级方案，默认尝试 HTTP/2 分域策略（design.md AD-02）
- **R8.7** 验证方法：grep "connectTimeout\|readTimeout\|writeTimeout\|callTimeout" 确认配置

### R9：OkHttp Dispatcher 必须配置并发控制

- **R9.1** `Dispatcher.setMaxRequests(64)`：全局最大并发 64
- **R9.2** `Dispatcher.setMaxRequestsPerHost(16)`：单域名最大并发 16
- **R9.3** 验证方法：grep "setMaxRequests\|setMaxRequestsPerHost" 确认配置

### R10：LoadControl 不热切换声明（路径 A，与 design.md AD-01 一致）

- **R10.1** 沿用 design.md AD-01 + video-prebuffer-enhancement AD-09 路径 A：LoadControl 仅在 `prepareAsyncInternal` 入口（`PlayerInstancePool.acquire` → `createLoadControl`）设置一次
- **R10.2** **禁止运行时热切换**：不实现 AdaptiveLoadControl，不重写 shouldContinueLoading，不调用 `ExoPlayer.setLoadControl()`（避免 re-prepare 中断 1-3s + PlayerInstancePool 池化冲突）
- **R10.3** 网络档位变化仅影响预加载策略（下一集，属 video-prebuffer-enhancement 范畴），不影响当前视频 LoadControl
- **R10.4** 档位变化通过下次播放生效（分钟级延迟可接受，参考 design.md 附录 B 9.2）
- **R10.5** 验证方法：grep "AdaptiveLoadControl\|shouldContinueLoading" 确认无实现；grep "setLoadControl" 确认仅在 prepare 前调用

### R11：HLS 必须配置自定义 LoadErrorHandlingPolicy 子类

- **R11.1** 自定义 `HlsLoadErrorPolicy extends DefaultLoadErrorHandlingPolicy`：**重写 `getRetryDelayMsFor(loadErrorInfo)` 返回 3000ms**（删除原 spec 的"构造传入 3000"，DefaultLoadErrorHandlingPolicy 默认构造无参）
- **R11.2** 重写 `getRetryDelayMsFor`：5xx 错误重试 3 次后返回 C.TIME_UNSET（放弃）
- **R11.3** 在 `createAdaptiveMediaSource` 中通过 `.setLoadErrorHandlingPolicy()` 注入
- **R11.4** 验证方法：grep "HlsLoadErrorPolicy\|getRetryDelayMsFor\|setLoadErrorHandlingPolicy" 确认配置

### R12：HLS 自定义 ChunkSource 降级为 P2 评估（不实施）

- **R12.1** **本次不实施**自定义 HlsChunkSourceFactory（与 design.md AD-05 一致，过度工程）
- **R12.2** P0 先启用 `setAllowChunklessPreparation(true)` + LoadControl 优化，验证 rebuffer 率
- **R12.3** 若 P0 实施后 rebuffer 率仍 >5%，再评估自定义 ChunkSource（弱网预取 + 跳过 init 分片重复下载）
- **R12.4** 验证方法：本次无需验证；P2 评估时再补充

### R13：必须提供用户可调档位

- **R13.1** 在播放器设置页新增"缓冲策略"项，提供三档（与 design.md 1.1.3 + R1.3 一致）：
  - 省流（WEAK）：minBuffer 5s/maxBuffer 30s，关闭异步解码
  - 平衡（MEDIUM）：minBuffer 8s/maxBuffer 90s，启用异步解码
  - 激进（GOOD）：minBuffer 8s/maxBuffer 120s，启用所有激进策略
- **R13.2** 默认档位根据 `DeviceTier` 自动选择：GOOD 档默认（中高端机）
- **R13.3** 用户手动选择后保存到 SharedPreferences，覆盖默认
- **R13.4** 切换档位无需重启 App，下次播放生效（路径 A，与 R10 一致）
- **R13.5** 高级参数折叠：`videoMaxBufferSec` / `videoMinBufferSec` / `videoBufferForPlaybackMs` / `videoMaxResolution` 放入"高级设置"折叠区
- **R13.6** 验证方法：在播放器设置页操作三档切换，重新播放确认参数生效

### R14：必须清理调试日志

- **R14.1** 实施完成后 Grep "android.util.Log.d\|android.util.Log.e" 确认无残留
- **R14.2** 所有新增日志使用 `AppLog.put(tag, msg)` 而非 `Log.x`
- **R14.3** 验证方法：grep "android.util.Log" 在新增文件中无匹配

### R15：必须同步更新 updateLog.md

- **R15.1** 在 `assets/updateLog.md` 顶部新增条目：视频缓冲速度优化
- **R15.2** 用通俗语言描述用户可感知变化（如"视频播放更流畅"、"弱网下自动降级清晰度"）
- **R15.3** 不暴露内部技术术语（如 LoadControl、ChunkSource）
- **R15.4** 验证方法：读取 `assets/updateLog.md` 顶部确认新增条目存在

### R16：视频流 OkHttpClient 必须注入 DohDns（新增）

- **R16.1** 复用项目已有 `DohDns.kt`（DoH，DNS over HTTPS，防劫持+降时延）
- **R16.2** 在 `ExoPlayerHelper.getOkHttpClient` 中通过 `.dns(DohDns)` 注入视频流 OkHttpClient
- **R16.3** 视频流 DNS 污染/劫持会导致分片加载失败触发降级链，与缓冲速度直接相关（review-completeness.md 遗漏点 2）
- **R16.4** 验证方法：grep "DohDns" 在 `ExoPlayerHelper.kt` 中确认注入；logcat 过滤 DohDns 日志确认视频流 DNS 走 DoH

### R17：Cronet 评估（新增，仅评估不实施）

- **R17.1** 本次仅评估 Cronet 集成可行性，不实施代码改动
- **R17.2** 评估 Cronet via Google Play Services 方案：0 APK 体积增量，依赖 Google Play Services（部分国产机无）
- **R17.3** 评估 Cronet embedded 方案：1.5MB APK 体积增量，无外部依赖
- **R17.4** 评估 Cronet 对比 OkHttp 的弱网收益：QUIC 0-RTT、HTTP-3 多路复用、连接迁移（YouTube 在用）
- **R17.5** 评估结论记录到 design.md 后续 ADR（若 P0+P1 实施后 rebuffer 率仍高，再实施 Cronet 集成）
- **R17.6** 验证方法：本次无需验证；评估文档归档到 `docs/specs/video-buffer-speed-optimization/cronet-evaluation.md`

## Scenarios（场景）

### Scenario 1：好网播放 1080P HLS 点播视频（正常场景）

**前置条件**：deviceTier=GOOD，网络 WiFi 100Mbps，HLS 点播视频 1080P

**预期行为**：
1. 用户点击视频，500ms 内首帧显示（setAllowChunklessPreparation 生效）
2. 播放过程中无卡顿，maxBuffer 120s 在 30 秒内填满（setTargetBufferBytes(-1) 解除 50MB 截断）
3. AnalyticsListener 监控：TTFB < 500ms、缓冲中断 0 次、丢帧率 < 0.1%、带宽利用率 > 80%
4. OkHttp EventListener 监控：DNS < 50ms（DohDns 生效）、Connect < 100ms、TLS < 100ms

**验证方法**：logcat 过滤 "ExoAnalytics" 和 "OkHttpStage"，确认指标达标

### Scenario 2：中网播放 MP4 视频（正常场景）

**前置条件**：deviceTier=MEDIUM，网络 4G 10Mbps，MP4 视频 720P

**预期行为**：
1. 用户点击视频，1 秒内首帧显示
2. maxBuffer 90s 在 60 秒内填满
3. 自适应码率限制 1080p（setMaxVideoSize(1920, 1080)），实际选 720P
4. 缓冲中断 < 3 次/小时

**验证方法**：logcat 过滤 "ExoAnalytics"，确认 maxBuffer 填满时间 < 60s

### Scenario 3：弱网播放 DASH 视频（异常场景）

**前置条件**：deviceTier=GOOD，网络 3G 1Mbps，DASH 自适应码率视频

**预期行为**：
1. LoadControl 静态参数生效（GOOD 档 8s/120s），不热切换（路径 A）
2. 自适应码率从 1080P 降级到 480P（setMaxVideoSize 限制 + bandwidthMeter 共享注入）
3. 播放中缓冲中断 < 5 次/小时
4. 用户感知：清晰度下降但播放连续

**验证方法**：logcat 过滤 "ExoAnalytics" 确认码率切换日志 + LoadControl 档位日志

### Scenario 4：网络切换 WiFi→4G（异常场景）

**前置条件**：deviceTier=GOOD，播放中网络从 WiFi 切换到 4G

**预期行为**：
1. 短暂缓冲中断（< 2 秒）
2. OkHttp 连接池失效，新建连接
3. LoadControl 不热切换（路径 A），档位参数保持 GOOD（下次播放才可能变化）
4. 自适应码率从 1080P 降级到 720P
5. 播放恢复后无中断

**验证方法**：手动切换网络，观察播放器无崩溃 + logcat 确认连接重建

### Scenario 5：HLS 服务器返回 5xx 自动重试后降级（异常场景）

**前置条件**：deviceTier=GOOD，HLS 服务器返回 500 错误

**预期行为**：
1. HlsLoadErrorPolicy 触发重试，`getRetryDelayMsFor` 返回 3000ms
2. 重试 3 次后仍失败，返回 C.TIME_UNSET
3. ExoPlayer 触发 onPlayerError
4. exoplayer-resilience 项目接手，触发 WebView 降级
5. 用户感知：自动切换到 WebView 播放

**验证方法**：mock 服务器返回 500，确认重试 3 次后降级

### Scenario 6：缓存读失败降级（异常场景）

**前置条件**：deviceTier=GOOD，缓存文件损坏

**预期行为**：
1. CacheDataSource 读取缓存失败
2. FLAG_IGNORE_CACHE_ON_ERROR 生效，降级到网络读取
3. 播放不中断
4. 日志输出 WARN："Cache read failed, fallback to network"

**验证方法**：手动损坏缓存文件，确认播放无中断

### Scenario 7：低端机异步解码崩溃防护（异常场景）

**前置条件**：deviceTier=WEAK，低端机 MediaCodec 异步模式有 bug

**预期行为**：
1. ExoPlayerHelper 检测到 WEAK 档位
2. 不启用 forceEnableMediaCodecAsynchronousQueueing
3. 使用同步解码模式 + DefaultMediaCodecSelector.DEFAULT（已优先硬解）
4. 播放正常，无崩溃

**验证方法**：在 WEAK 档位设备上播放视频，确认无 MediaCodec 崩溃日志

### Scenario 8：用户手动切换缓冲档位（正常场景）

**前置条件**：deviceTier=GOOD，用户在播放器设置页切换档位

**预期行为**：
1. 用户进入播放器设置，看到"缓冲策略"项
2. 选择"省流"档位，SharedPreferences 保存
3. 下次播放视频时，使用 WEAK 档位参数（minBuffer 5s/maxBuffer 30s）
4. 不需要重启 App（路径 A，下次播放生效）

**验证方法**：操作三档切换，重新播放确认参数生效

### Scenario 9：AnalyticsListener 每分钟汇总输出（正常场景）

**前置条件**：deviceTier=GOOD，播放视频超过 1 分钟

**预期行为**：
1. 每分钟输出一次汇总日志到 AppLog（Tag=ExoAnalytics）
2. 汇总内容包括：TTFB 平均/最大、缓冲中断次数、丢帧率、码率切换次数、带宽利用率
3. 后台线程处理，不影响主线程

**验证方法**：logcat 过滤 "ExoAnalytics" 确认每分钟输出汇总

### Scenario 10：FLV 视频播放（统一策略覆盖全格式）

**前置条件**：deviceTier=GOOD，FLV 视频

**预期行为**：
1. ExoPlayer 通过 ProgressiveMediaSource 解析 FLV
2. LoadControl、OkHttp、CacheDataSource、自适应码率、解码器优化统一生效
3. 首帧 < 1 秒
4. 缓冲中断 < 1 次/小时

**验证方法**：播放 FLV 视频，确认与 HLS/MP4 体验一致

### Scenario 11：HLS 直播场景低延迟播放（直播场景）

**前置条件**：deviceTier=GOOD，HLS 直播流（m3u8 含 `#EXT-X-SERVER-CONTROL` 标签）

**预期行为**：
1. 检测到直播场景，配置 `MediaItem.LiveConfiguration.targetOffsetMs(2000)`
2. `setLowLatencyModeEnabled(true)` 生效（LL-HLS 源）
3. 直播时延约束 2 秒，`setMinPlaybackSpeed(0.95f)` / `setMaxPlaybackSpeed(1.05f)` 允许微调追上直播
4. 缓冲中断 < 3 次/小时

**验证方法**：播放 HLS 直播流，logcat 确认 LiveConfiguration 生效 + 低延迟模式启用

### Scenario 12：HLS 点播场景不配置 LiveConfiguration（点播场景）

**前置条件**：deviceTier=GOOD，HLS 点播流（m3u8 无 `#EXT-X-SERVER-CONTROL` 标签）

**预期行为**：
1. 检测到点播场景，不配置 LiveConfiguration（点播无直播时延概念）
2. `setLowLatencyModeEnabled` 不启用（非 LL-HLS 源）
3. setAllowChunklessPreparation(true) 生效，首帧降 30%+
4. 播放正常，无直播配置副作用

**验证方法**：播放 HLS 点播流，logcat 确认无 LiveConfiguration 配置 + chunkless preparation 启用

### Scenario 13：DohDns 防劫持场景（异常场景）

**前置条件**：deviceTier=GOOD，DNS 被污染/劫持的网络环境

**预期行为**：
1. 视频流 OkHttpClient 通过 `.dns(DohDns)` 注入
2. DNS 解析走 DoH（DNS over HTTPS），绕过本地 DNS 污染
3. 分片加载正常，不触发降级链
4. logcat 输出 DohDns 解析日志

**验证方法**：在 DNS 污染环境播放视频，确认分片加载正常 + DohDns 日志输出
