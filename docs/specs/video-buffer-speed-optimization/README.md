# 视频播放器当前视频缓冲速度优化（video-buffer-speed-optimization）

> **状态**：🔄 设计中
> **创建日期**：2026-07-28
> **优先级**：P0（核心体验问题——用户反馈播放卡顿严重，已实施三项优化效果不明显）
> **核心原则**：聚焦当前播放视频缓冲速度（非下一视频预加载）+ 激进策略（默认中高端机，用户可往下调）+ 全格式统一激进 + 深度整合业界 7 大类成熟方案
> **与 [video-prebuffer-enhancement](../video-prebuffer-enhancement/README.md) 的关系**：互补不重叠。后者聚焦"下一视频预加载"，本 spec 聚焦"当前正在播放视频的缓冲速度"。
> **权威源声明**：本 README 基于 [design.md](./design.md)（权威源）+ [review-tech-feasibility.md](./review-tech-feasibility.md)（源码核实）修订，"已实施/待实施"状态严格对齐代码现状，参数与 design.md 一致。

---

## 一、功能概述

针对用户反馈"当前播放视频卡顿严重，已实施的三项优化（HLS 首次加载优化 + 扩大缓冲区 + OkHttp 连接池）效果不明显"的核心问题，进行源码级深度分析，回答用户 17:55 提出的核心质疑：**"当前优化内容是否会加强整个当前播放视频的缓冲速度呢？"**

### 1.1 用户核心诉求（必须满足）

| # | 诉求 | 说明 |
|---|------|------|
| 1 | **聚焦当前视频缓冲速度** | 不是"下一个视频预加载"，是"当前正在播放的视频"的缓冲速度 |
| 2 | **激进策略** | 默认中高端机参数，用户可往下调（与 video-prebuffer-enhancement R3 一致） |
| 3 | **结合网上成熟方案** | 深度调研并整合 7 大类业界成熟优化方案 |
| 4 | **覆盖各类型视频** | HLS/DASH/MP4/FLV 等统一激进策略，不偏废某一格式 |

### 1.2 与 video-prebuffer-enhancement 的边界划分

| 维度 | video-prebuffer-enhancement | **本 spec（video-buffer-speed-optimization）** |
|------|----------------------------|------------------------------------------------|
| **核心目标** | 下一视频预加载（FirstFramePreloader/VideoPreloader） | **当前播放视频的缓冲速度**（LoadControl/DataSource/解码器/网络层） |
| **作用阶段** | 切集前 / 播放进度达触发点时 | **播放中 / 首帧加载 / 缓冲恢复全程** |
| **核心组件** | FirstFramePreloader / VideoPreloader / PlayListManager | **LoadControl / MediaSource / OkHttp / RenderersFactory / Allocator** |
| **用户感知** | 切下一集时首帧更快 | **当前播放不卡顿、缓冲更激进、恢复更快** |
| **重叠点** | 共享 SimpleCache / cacheKey 策略 / OkHttp 配置 | 共享 SimpleCache / cacheKey 策略 / OkHttp 配置 |

> **关键区分**：本 spec 不研究"如何提前下载下一集"，而是研究"如何让当前正在播放的视频更激进地缓冲、更快地恢复卡顿、更高效地利用带宽"。

---

## 二、核心能力矩阵

> 本 spec 整合业界 7 大类成熟方案，按优先级分层。**所有项目均基于 design.md 源码核实，状态标记与代码现状严格对齐**（review-tech-feasibility.md 已验证）。

| 优先级 | 能力 | 业界方案类别 | 解决问题 | 实施状态 |
|--------|------|-------------|---------|---------|
| **P0** | **LoadControl 黄金参数公式激进化** | 1. ExoPlayer LoadControl | minBuffer/maxBuffer/bufferForPlayback 参数过保守导致缓冲不足 | 🔄 待实施（当前已分档 WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s，参数与 design.md 1.1.3 一致） |
| **P0** | **setTargetBufferBytes(-1) 禁用缓冲大小上限** | 1. ExoPlayer LoadControl | 默认缓冲大小限制（约 50MB）导致高码率视频缓冲不足 | 🔄 待实施 |
| **P0** | **setPrioritizeTimeOverSizeThresholds(true)** | 1. ExoPlayer LoadControl | 优先满足时间阈值而非大小阈值，避免大小阈值提前触发 | 🔄 待实施 |
| **P0** | **Allocator 缓冲段大小提升** | 1. ExoPlayer LoadControl | 当前 64KB 默认段大小在高码率场景下分配频繁 | 🔄 待实施（当前 C.DEFAULT_BUFFER_SEGMENT_SIZE，目标 256KB） |
| **P0** | **OkHttp 超时配置优化** | 3. OkHttp 连接池 | 当前未显式配置 connectTimeout/readTimeout | 🔄 待实施 |
| **P0** | **OkHttp Dispatcher 并发控制** | 3. OkHttp 连接池 | 默认 maxRequests=64/maxRequestsPerHost=5 可能限制 HLS 并发分片 | 🔄 待实施 |
| **P0** | **DohDns 注入防劫持** | 3. OkHttp 连接池 | 视频流 OkHttpClient 未注入 DohDns，DNS 易被劫持导致视频请求失败或被劫持到错误 IP | 🔄 待实施 |
| **P0** | **HLS setAllowChunklessPreparation** | 2. HLS 低延迟 | HLS 首帧需下载首个分片才能 preparation，首帧耗时高 | 🔄 待实施（当前 ExoPlayerHelper/Exo2MediaPlayer HLS 分支均未调用） |
| **P0** | **forceEnableMediaCodecAsynchronousQueueing** | 6. 解码器 | MediaCodec 同步队列在高帧率/高分辨率下成为瓶颈 | 🔄 待实施 |
| **P0** | **FLAG_IGNORE_CACHE_ON_ERROR** | 4. CacheDataSource | 缓存错误时未降级到网络，可能导致播放中断 | 🔄 待实施 |
| **P0** | **setMaxVideoSize(1920,1080) 限制分辨率** | 5. 自适应码率 | 4K 视频在 1080p 屏幕仍尝试解码 4K，浪费带宽与解码资源 | 🔄 待实施 |
| **P0** | **VideoAnalyticsListener + VideoEventListener 监控** | 7. 性能监控 | 缺乏首帧时间/丢帧率/带宽利用率指标，无法量化优化效果 | 🔄 待实施 |
| **P1** | **DefaultLoadErrorHandlingPolicy 自定义重试** | 2. HLS 低延迟 | 分段加载错误重试策略默认，可能过激进重试拖慢整体 | 🔄 待实施（重写 getRetryDelayMsFor 返回 3000ms，非构造传参） |
| **P1** | **OkHttp EventListener 性能监控** | 3. OkHttp 连接池 | 无法精准定位 DNS/连接/TLS 各阶段耗时 | 🔄 待实施 |
| **P1** | **HTTP/2 多路复用分域策略** | 3. OkHttp 连接池 | 当前强制 HTTP_1_1，需评估分域 HTTP/2 提升 HLS 并发 | 🔄 待评估（分域策略：默认 HTTP/2，StreamResetException 后降级 HTTP_1_1 缓存 1 小时） |
| **P1** | **Cronet 评估** | 3. OkHttp 连接池 | 评估 Cronet via Google Play Services 用于视频流，QUIC/HTTP3 多路复用 + 弱网抗性 + 0-RTT 连接恢复 | 🔄 待评估（需评估设备兼容性与 Google Play 依赖，部分国产设备无 GMS） |
| **P1** | **ConnectionPool 独立化** | 3. OkHttp 连接池 | 视频专用连接池(10,5min)不存在，当前继承书源 50 连接池 | 🔄 待实施（当前继承书源 50 连接池） |
| **P1** | **CacheDataSource FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH** | 4. CacheDataSource | 缓存分片长度不匹配时默认抛异常 | 🔄 待实施 |
| **P1** | **多级缓存（内存 + 磁盘）评估** | 4. CacheDataSource | 当前仅磁盘缓存，内存缓存可加速首帧 | 🔄 待评估（OOM 风险，限 10MB） |
| **P1** | **自适应码率参数调优** | 5. 自适应码率 | setAdaptiveSelectionMarginMs(1500)/setMinDurationForQualityIncreaseMs 未调优 | 🔄 待实施 |
| **P1** | **bandwidthMeter 共享注入** | 5. 自适应码率 | LoadControl 与 TrackSelector 带宽测量不一致 | 🔄 待实施 |
| **P1** | **bufferForPlayback 起播门槛激进化** | 1. ExoPlayer LoadControl | GOOD 档 1s 起播门槛偏高，中高端机可降至 500ms | 🔄 待实施 |
| **P1** | **CacheDataSink fragment size 2MB** | 4. CacheDataSource | DEFAULT_FRAGMENT_SIZE(5MB) 偏大，HLS 小分片浪费空间 | 🔄 待实施 |
| **P1** | **MediaItem.LiveConfiguration.targetOffsetMs** | 2. HLS 低延迟 | 直播 HLS 无目标偏移约束，缓冲行为不可控 | 🔄 待实施（VOD=0ms, LIVE=3000ms，与 design.md 1.2.3 一致） |
| **P1** | **setEnableDecoderFallback 硬解回退** | 6. 解码器 | 硬件解码失败默认不回退软件解码 | 🔄 待实施 |
| **P1** | **解码线程优先级提升** | 6. 解码器 | 未设置 THREAD_PRIORITY_URGENT_AUDIO | 🔄 待实施 |
| **P2** | **自定义 HlsChunkSource 低延迟分片选择** | 2. HLS 低延迟 | LL-HLS 分片选择策略默认，未自定义 | 🔄 待评估（复杂度高，P0 收益验证后 rebuffer 率仍 >5% 再实施） |
| **P2** | **CacheUtil 缓存预加载（当前视频）** | 4. CacheDataSource | 当前视频未利用 CacheUtil 预加载后续片段 | 🔄 待评估（与 prebuffer spec 边界需明确） |
| **P2** | **断点续传优化** | 4. CacheDataSource | 长视频断点续传体验未优化 | 🔄 待评估 |
| **P2** | **内存级 LruCache 叠加** | 4. CacheDataSource | 首帧仍需磁盘 IO，内存缓存可零 IO | 🔄 待评估（OOM 风险，限 10MB） |
| **P2** | **setLowLatencyModeEnabled（LL-HLS 检测后启用）** | 2. HLS 低延迟 | LL-HLS 源无法低延迟播放（影响面小，多数源非 LL-HLS） | 🔄 待评估（需 #EXT-X-SERVER-CONTROL 标签检测） |
| **P2** | **移除 setCacheControl(maxAge=1天)** | 3. OkHttp 连接池 | 此配置作用于 CDN 缓存，非 ExoPlayer SimpleCache，对当前视频缓冲无影响 | 🔄 待实施 |

---

## 三、现状锚点

> 以下为代码现状的位置和状态（已对照 design.md + review-tech-feasibility.md 源码核实），本 spec 基于此分析不足并新增优化。

| 位置 | 文件 | 现状 | 已实施内容 |
|------|------|------|-----------|
| LoadControl 分档 | [ExoPlayerHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt) | ✅ 已实施 | `createLoadControlByTier` 已分档：WEAK(5s/30s) / MEDIUM(8s/90s) / GOOD(8s/120s)（与 design.md 1.1.3 一致） |
| OkHttp 连接池 | [ExoPlayerHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt) | 🔄 待实施 | **当前继承书源 50 连接池**（HttpHelper.kt L101 ConnectionPool(50, 5min)），视频专用 ConnectionPool(10,5min) 不存在；已配置 `Protocol.HTTP_1_1` + `CacheControl.maxAge(1天)`（后者对缓冲无实际收益，P2 移除） |
| HLS LL-HLS | [Exo2MediaPlayer.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt) | 🔄 待实施 | **`setAllowChunklessPreparation(true)` + `setLowLatencyModeEnabled(true)` 均未调用**（ExoPlayerHelper.kt createMediaSource HLS 分支 + Exo2MediaPlayer.kt applyMediaSourceByType HLS 分支均无此调用，design.md L55/L214 已诚实承认） |
| buildFallbackTypes | [Exo2MediaPlayer.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt) | ✅ 已实施 | 嗅探失败 + 非视频 MIME 类型直接返回 `emptyList()` 触发 WebView 降级 |
| 共享 Allocator | [PlayerInstancePool.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt) | ✅ 已实施 | `sharedAllocator = DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` // 64KB 默认 |
| 缓冲进度条 | [VideoFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt) | ✅ 已实施 | `startBufferUpdate` 动态重获取 `bottomProgressbar` 引用 |
| 预加载器状态 | [VideoPlay.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt) | ✅ 已实施 | FirstFramePreloader/VideoPreloader 调用已注释（预加载禁用） |
| AdaptiveTrackSelection | [ExoPlayerHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt) | ✅ 已实施 | `AdaptiveTrackSelection.Factory(bandwidthMeter)` 已有 |
| DefaultRenderersFactory | [PlayerInstancePool.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt) | ✅ 已实施 | `setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)` 已有；**`setEnableDecoderFallback` 未调用**（P1 待实施） |
| **setTargetBufferBytes** | ExoPlayerHelper.kt | ❌ 未实施 | 未设置 `-1`，使用默认缓冲大小上限（约 50MB） |
| **setPrioritizeTimeOverSizeThresholds** | ExoPlayerHelper.kt | ❌ 未实施 | 未启用 |
| **OkHttp 超时配置** | ExoPlayerHelper.kt | ❌ 未实施 | 未显式配置 connectTimeout/readTimeout |
| **OkHttp Dispatcher** | ExoPlayerHelper.kt | ❌ 未实施 | 未配置 maxRequests/maxRequestsPerHost |
| **OkHttp EventListener** | ExoPlayerHelper.kt | ❌ 未实施 | 未监听 DNS/连接/TLS 各阶段耗时 |
| **DohDns 注入** | ExoPlayerHelper.kt | ❌ 未实施 | 视频 OkHttpClient 未注入 DohDns |
| **CacheDataSource FLAG** | ExoPlayerHelper.kt | ❌ 未实施 | 未设置 `FLAG_IGNORE_CACHE_ON_ERROR` |
| **AnalyticsListener** | Exo2MediaPlayer.kt | ❌ 未实施 | 已 addAnalyticsListener 但回调未覆盖缓冲速度关键指标 |
| **解码器异步队列** | PlayerInstancePool.kt | ❌ 未实施 | `forceEnableMediaCodecAsynchronousQueueing` 未启用 |
| **解码线程优先级** | PlayerInstancePool.kt | ❌ 未实施 | 未设置 `THREAD_PRIORITY_URGENT_AUDIO` |
| **setMaxVideoSize** | PlayerInstancePool.kt | ❌ 未实施 | 未限制最大视频分辨率 |

---

## 四、关键发现

### 4.1 已实施优化效果不明显的根因分析（用户必读）

用户反馈"已实施三项优化效果不明显"，经源码分析（design.md 1.8 + review-tech-feasibility.md 冲突清单），根因如下：

#### 发现-1：LoadControl 参数仍偏保守，缓冲上限被"大小阈值"提前触发

**现象**：已实施 `createLoadControlByTier` 分档（GOOD 档 maxBuffer=120s），但用户仍感卡顿。

**根因**：
- 未设置 `setTargetBufferBytes(-1)`，ExoPlayer 默认缓冲大小上限（约 50MB）在高码率视频（如 1080p 5Mbps）下仅能缓冲约 80 秒，**大小阈值可能先于时间阈值触发**，导致 maxBuffer=120s 实际无法达到
- 未设置 `setPrioritizeTimeOverSizeThresholds(true)`，大小阈值优先级高于时间阈值，高码率场景下缓冲时长被压缩
- `bufferForPlaybackMs`（GOOD 档 1s）偏高，中高端机可降至 500ms 加速首帧

**结论**：**参数分档已实施（WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s），但"大小阈值"这一隐藏限制未解除，导致时间阈值形同虚设**。

#### 发现-2：OkHttp 配置不完整，超时/并发/DNS 多项缺失

**现象**：当前 OkHttp 仅配置 `Protocol.HTTP_1_1` + `CacheControl.maxAge(1天)`，HLS 分片加载仍慢。

**根因**：
- **ConnectionPool(10,5min) 实际不存在**：视频专用连接池未配置，`okhttpClient` 通过 `newBuilder()` 派生，**继承书源 HttpHelper.kt 的 50 连接池**（design.md L83 已诚实承认）
- 未显式配置 `connectTimeout` / `readTimeout` / `writeTimeout`，OkHttp 默认 10s 连接超时但在慢速服务器上仍可能长时间阻塞
- 未配置 `Dispatcher` 的 `maxRequests` / `maxRequestsPerHost`，HLS 多分片并发可能受限（默认 maxRequestsPerHost=5）
- 强制 `Protocol.HTTP_1_1`，未评估 HTTP/2 多路复用对 HLS 并发分片加载的提升
- 未启用 `EventListener` 监听 DNS/连接/TLS 各阶段耗时，**无法精准定位是 DNS 慢、连接慢还是 TLS 握手慢**
- 未注入 `DohDns`，DNS 请求可能被运营商劫持到错误 IP，导致视频请求失败或被引导到错误服务器

**结论**：**OkHttp 配置不完整，"请求慢"的根因无法定位，且 DNS 劫持风险未防御**。

#### 发现-3：HLS LL-HLS 实际未启用，首帧加速红利完全缺失

**现象**：之前文档称 `setAllowChunklessPreparation(true) + setLowLatencyModeEnabled(true)` 已实施，但 HLS 首屏仍慢。

**根因**（review-tech-feasibility.md 冲突-1 已验证）：
- **`setAllowChunklessPreparation(true)` 实际未调用**：ExoPlayerHelper.kt createMediaSource HLS 分支 + Exo2MediaPlayer.kt applyMediaSourceByType HLS 分支均无此调用，design.md L55/L214 是唯一诚实承认的文档
- **`setLowLatencyModeEnabled(true)` 实际未调用**：同上，两处 HLS 分支均未启用
- HLS 默认需下载首个分片才能完成 preparation，首帧耗时高；启用 `setAllowChunklessPreparation(true)` 可仅解析 m3u8 清单即完成 preparation，首帧耗时降低 30%+（ExoPlayer 官方 benchmark）
- 未设置 `MediaItem.LiveConfiguration.targetOffsetMs`，LL-HLS 目标直播偏移未配置
- 未配置 `DefaultLoadErrorHandlingPolicy` 自定义重试（重写 `getRetryDelayMsFor` 返回 3000ms）

**结论**：**LL-HLS 开关实际未打开，之前文档"已实施"描述错误（已被 review-tech-feasibility.md 修正），LL-HLS 红利完全缺失**。

#### 发现-4：Allocator 缓冲段大小默认 64KB，高码率场景分配频繁

**现象**：`PlayerInstancePool.sharedAllocator = DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` 使用默认 64KB。

**根因**：
- 64KB 段大小在 1080p 5Mbps 视频下，每秒需分配约 10 个段，高码率场景下分配/释放频繁，增加 GC 压力
- 中高端机可提升至 256KB（`C.DEFAULT_BUFFER_SEGMENT_SIZE * 4`），减少分配次数

**结论**：**Allocator 段大小未针对视频场景调优**。

#### 发现-5：CacheDataSource 缺失错误降级，缓存异常导致播放中断

**现象**：未设置 `FLAG_IGNORE_CACHE_ON_ERROR` + `FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`。

**根因**：
- 当 SimpleCache 读取异常（如磁盘满、IO 错误）时，未降级到网络直接加载，可能导致播放中断
- 缓存分片长度与服务端 Content-Length 不匹配时默认抛异常

**结论**：**缓存错误未降级，单点故障导致整体播放中断**。

#### 发现-6：自适应码率参数未调优，弱网未降级

**现象**：已有 `AdaptiveTrackSelection.Factory(bandwidthMeter)`，但弱网仍高码率缓冲。

**根因**：
- 未调用 `setMaxVideoSize(1920, 1080)`（design.md AD-08 决策为 1080p，非 spec.md 的 720p），高码率 4K 视频在 1080p 屏幕仍尝试解码 4K
- 未设置 `setAdaptiveSelectionMarginMs(1500)`，自适应切换码率时无缓冲余量
- `bandwidthMeter` 未注入 `DefaultTrackSelector`，LoadControl 档位判断与 TrackSelector 码率选择基于不同带宽测量

**结论**：**自适应码率框架已有，但参数未调优，弱网体验未改善**。

#### 发现-7：解码器优化不完整，异步队列未启用

**现象**：已有 `setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)`，但解码仍可能成为瓶颈。

**根因**：
- 未启用 `forceEnableMediaCodecAsynchronousQueueing()`，MediaCodec 同步队列模式在高帧率/高分辨率下可能成为瓶颈
- 未启用 `setEnableDecoderFallback(true)`，硬件解码失败默认不回退软件解码
- 未设置解码线程优先级 `Process.THREAD_PRIORITY_URGENT_AUDIO`

**结论**：**解码器扩展渲染器已有，但异步队列/硬解回退/线程优先级未启用**。

#### 发现-8：缺乏性能监控埋点，无法量化优化效果

**现象**：`Exo2MediaPlayer` 已 `addAnalyticsListener` 但回调未覆盖缓冲速度关键指标。

**根因**：
- 缺乏首帧时间（TTFB）、缓冲中断次数、丢帧率、带宽利用率等关键指标
- 用户反馈"效果不明显"无法用数据验证，优化效果无法量化
- 目标指标（TTFB<500ms / 缓冲中断<1次/小时 / 丢帧率<0.1% / 带宽利用率>90%）无法度量

**结论**：**无监控即无优化，效果不明显因缺乏数据支撑**。

### 4.2 新发现的优化点（整合业界 7 大类方案）

基于业界 7 大类成熟方案，本 spec 新增以下优化点（详见核心能力矩阵）：

1. **ExoPlayer LoadControl 深度优化**：setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds + bufferForPlayback 降低 + 黄金参数公式
2. **HLS 低延迟深度优化**：setAllowChunklessPreparation（P0 必修）+ targetOffsetMs + DefaultLoadErrorHandlingPolicy + 自定义 ChunkSource（P2 评估）
3. **OkHttp 连接池深度优化**：超时配置 + Dispatcher 并发 + HTTP/2 分域策略 + EventListener 监控 + **ConnectionPool 独立化** + **DohDns 注入** + **Cronet 评估**
4. **CacheDataSource 优化**：FLAG_IGNORE_CACHE_ON_ERROR + FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH + fragment size 2MB + 多级缓存评估 + CacheUtil + 断点续传
5. **自适应码率**：setMaxVideoSize(1920,1080) + setAdaptiveSelectionMarginMs + bandwidthMeter 共享注入
6. **解码器优化**：forceEnableMediaCodecAsynchronousQueueing + setEnableDecoderFallback + 解码线程优先级
7. **性能监控**：VideoAnalyticsListener + VideoEventListener + TTFB/丢帧率/带宽利用率 7 类指标 + 目标 SLO

---

## 五、文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives Considered + Drawbacks）/ Requirements / Scenarios（⚠️ 注意：spec.md 与 design.md 存在 9 项矛盾，以 design.md 为权威源） |
| [design.md](./design.md) | Technical Approach / Architecture Decisions（ADR Y-Statement）/ Data Flow / File Changes（**权威源**，源码核实） |
| [tasks.md](./tasks.md) | `- [ ] X.Y` 格式任务清单 + AOAdapt 日志 |
| [review-tech-feasibility.md](./review-tech-feasibility.md) | 技术方案可行性审查报告（API 真实性 36 项核实 + 与现有代码冲突清单 9 项 + 意淫清单 9 项） |
| [review-completeness.md](./review-completeness.md) | 文档完整性审查报告（待生成） |

> **状态说明**：本 README.md 为设计阶段产物，已基于 review-tech-feasibility.md 修订"已实施"误描述并统一参数。spec.md / design.md / tasks.md 之间的矛盾以 design.md 为权威源。

---

## 六、预期收益

| 维度 | 优化前（当前） | 优化后（本 spec 实施） | 提升幅度 |
|------|---------------|----------------------|---------|
| **缓冲大小上限** | 默认约 50MB（高码率下仅 80s） | **setTargetBufferBytes(-1) 禁用上限，按时间阈值缓冲** | 高码率视频缓冲时长提升 50%+ |
| **缓冲阈值优先级** | 大小阈值优先（时间阈值形同虚设） | **setPrioritizeTimeOverSizeThresholds(true)，时间优先** | 高码率场景 maxBuffer 真正生效 |
| **MAX 缓冲时长（好网）** | 120s（GOOD 档已实施，但受大小阈值限制） | **120s 真正可达（解除大小阈值限制）** | 实际缓冲时长提升 50%+ |
| **MIN 缓冲时长** | WEAK 5s / MEDIUM 8s / GOOD 8s | **保留现有档位（与 design.md 1.1.3 一致）** | 档位参数不变，解除大小阈值限制 |
| **bufferForPlayback 起播门槛** | GOOD 档 1s | **GOOD 档 500ms（中高端机激进起播）** | 首帧延迟降 50% |
| **OkHttp 连接池** | 继承书源 50 连接池 | **视频专用 ConnectionPool(10, 5min) 独立化** | 视频与书源连接池隔离 |
| **OkHttp 连接超时** | 默认 10s（慢服务器阻塞） | **connectTimeout(10s) + readTimeout(15s) + writeTimeout(15s) 显式配置** | 慢请求不再无限阻塞 |
| **DNS 劫持防御** | 无 DohDns，DNS 易被劫持 | **视频 OkHttpClient 注入 DohDns 防劫持** | DNS 劫持风险消除 |
| **HLS 并发分片** | maxRequestsPerHost=5 默认 | **maxRequestsPerHost=20 提升 HLS 并发分片加载** | HLS 分片加载速度提升 |
| **HLS 首屏耗时** | setAllowChunklessPreparation 未启用 | **setAllowChunklessPreparation(true) + targetOffsetMs + 错误重试策略** | HLS 首屏降低 30%+ |
| **缓存错误降级** | 缓存异常导致播放中断 | **FLAG_IGNORE_CACHE_ON_ERROR + FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH 降级到网络** | 缓存异常不再中断播放 |
| **弱网码率降级** | 弱网仍高码率缓冲 | **setMaxVideoSize(1920,1080) 限制 + 自适应码率参数调优** | 带宽与解码资源节省 |
| **解码器异步队列** | 同步队列（高帧率瓶颈） | **forceEnableMediaCodecAsynchronousQueueing 启用** | 高帧率/高分辨率解码流畅度提升 |
| **硬解回退** | 硬解失败默认不回退 | **setEnableDecoderFallback(true) 回退软件解码** | 硬解失败不再直接报错 |
| **解码线程优先级** | 默认优先级 | **THREAD_PRIORITY_URGENT_AUDIO** | 音视频同步性提升 |
| **Allocator 段大小** | 64KB 默认（高码率分配频繁） | **256KB 提升（C.DEFAULT_BUFFER_SEGMENT_SIZE * 4）** | GC 压力降低 |
| **性能可观测性** | 无埋点（效果不明显无法验证） | **VideoAnalyticsListener + VideoEventListener + TTFB/丢帧率/带宽利用率 SLO** | 优化效果可量化 |
| **目标 SLO** | 无 | **TTFB<500ms / 缓冲中断<1次/小时 / 丢帧率<0.1% / 带宽利用率>90%** | 体验可度量 |
| **多格式统一** | HLS 已优化，其他格式未统一 | **HLS/DASH/MP4/FLV 统一激进缓冲策略** | 全格式体验一致 |

---

## 七、风险与约束

- **不破坏现有降级链**：Exo2MediaPlayer 的 HLS→DASH→Progressive 降级链已稳定，本 spec 不改动降级逻辑
- **不破坏实例池**：PlayerInstancePool 已修复 FATAL 崩溃，本 spec 不改动池化逻辑（Allocator 段大小调整需评估内存影响）
- **不引入大依赖**：所有优化均基于现有 Media3 1.10.1 + OkHttp，不引入新依赖（Cronet 评估若引入需单独评估 Google Play 依赖）
- **激进策略兜底**：默认中高端机参数，用户可通过 AppConfig/Preferences 往下调（与 video-prebuffer-enhancement R3 一致）
- **LoadControl 不热切换约束**：运行时网络变化不热切换 LoadControl，下次 prepare 生效（与 video-prebuffer-enhancement R3 路径 A 一致，design.md AD-01 决策）
- **HTTP/2 兼容性约束**：分域策略需捕获 StreamResetException 后降级 HTTP_1_1 并缓存 1 小时，避免一刀切
- **Cronet 设备兼容性约束**：Cronet via Google Play Services 依赖 GMS，部分国产设备无 GMS，需评估 fallback 到 OkHttp 的策略
- **DohDns 服务器可用性约束**：DohDns 依赖 DoH 服务器（如 Cloudflare/Google），需评估国内网络环境下 DoH 服务器可达性，必要时提供 fallback
- **多级缓存内存约束**：内存缓存需限制大小（10MB），避免 OOM，需评估设备内存档位
- **解码器异步队列兼容性约束**：部分旧设备 MediaCodec 异步队列模式可能崩溃，需 DeviceCodecBlacklist 黑名单兜底
- **硬解回退兼容性约束**：部分视频编码格式硬解不支持，需保留软解降级（setEnableDecoderFallback）
- **AnalyticsListener 性能约束**：埋点回调在播放线程，需避免耗时操作，仅记录指标不处理业务
- **Allocator 段大小内存约束**：提升段大小增加单实例内存占用，需结合 PlayerInstancePool 实例数评估总内存（3 实例池共享，总增量 <50MB）
- **与 video-prebuffer-enhancement 边界约束**：本 spec 不涉及预加载器（FirstFramePreloader/VideoPreloader），预加载相关优化归 video-prebuffer-enhancement

---

## 八、非目标

- ❌ 不研究"下一视频预加载"（归 video-prebuffer-enhancement）
- ❌ 不重写播放器架构（仍基于 GSYVideoPlayer + ExoPlayer）
- ❌ 不替换 ExoPlayer 为其他播放器（如 VLC/IjkPlayer）
- ❌ 不修改 Exo2MediaPlayer 的降级链与重试逻辑（已稳定）
- ❌ 不实施 LoadControl 运行时热切换（与 video-prebuffer-enhancement R3 一致，路径 A：prepare 前设置，design.md AD-01 决策）
- ❌ 不实施 AdaptiveLoadControl 自定义子类（design.md 附录 B 已评估并否决，触发 re-prepare 中断 + PlayerInstancePool 池化冲突）
- ❌ 不修改 PlayerInstancePool 的池化逻辑（Allocator 段大小调整除外）
- ❌ 不实现 DRM 内容解密
- ❌ 不实施 P3 AI 智能预缓冲（远期方向，本 spec 仅记录）
- ❌ 不修改 FirstFramePreloader / VideoPreloader（归 video-prebuffer-enhancement）
- ❌ 不修改 cacheKey 策略（已由 video-prebuffer-enhancement R3 统一）
- ❌ 不实施 spec.md R4.2 的 `FLAG_BLOCK_ON_CACHE`（API 不存在，Media3 1.x 实际为 `FLAG_BLOCK_ON_CACHE_WRITE`，design.md 1.4.3 未提此 flag）
- ❌ 不实施 spec.md R10 的 AdaptiveLoadControl 运行时热切换（与 design.md AD-01 矛盾，已被否决）

---

## 九、实施优先级说明

> 本 spec 优先级划分原则：**用户感知直接性 + 实施复杂度 + 风险等级**。优先级与 design.md 5.1 一致。

- **P0（核心体验，立即见效）**：
  - LoadControl 黄金参数（setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds）
  - HLS setAllowChunklessPreparation（**必修，之前误描述为已实施**）
  - forceEnableMediaCodecAsynchronousQueueing + setEnableDecoderFallback
  - FLAG_IGNORE_CACHE_ON_ERROR
  - setMaxVideoSize(1920,1080) + bandwidthMeter 共享注入
  - VideoAnalyticsListener + VideoEventListener 监控
  - OkHttp 超时配置 + Dispatcher 并发
  - **DohDns 注入防劫持**

- **P1（深度优化，需评估）**：
  - DefaultLoadErrorHandlingPolicy 自定义重试（重写 getRetryDelayMsFor）
  - OkHttp EventListener 性能监控
  - HTTP/2 多路复用分域策略
  - **Cronet 评估**（Google Play Services 依赖 + 设备兼容性）
  - **ConnectionPool 独立化**（视频专用 10,5min，与书源 50 连接池隔离）
  - CacheDataSource FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH + fragment size 2MB
  - 自适应码率参数调优（setAdaptiveSelectionMarginMs）
  - bufferForPlayback 起播门槛激进化（GOOD 档 500ms）
  - MediaItem.LiveConfiguration.targetOffsetMs（VOD=0ms, LIVE=3000ms）
  - 解码线程优先级提升
  - Allocator 段大小 256KB

- **P2（监控与远期）**：
  - 自定义 HlsChunkSource（弱网预取，P0 收益验证后 rebuffer 率仍 >5% 再实施）
  - 多级缓存（内存 LruCache 10MB）
  - setLowLatencyModeEnabled（LL-HLS 标签检测后启用）
  - CacheUtil 缓存预加载（与 prebuffer spec 边界需明确）
  - 断点续传优化
  - 移除 setCacheControl(maxAge=1天)（无实际收益）

---

## 十、后续行动

1. ✅ 生成 [spec.md](./spec.md)：详细 Intent / Scope / Approach / Requirements / Scenarios（⚠️ 已存在但与 design.md 存在 9 项矛盾，需后续修订对齐 design.md）
2. ✅ 生成 [design.md](./design.md)：Technical Approach / ADR 决策 / Data Flow / File Changes（**已生成，权威源**）
3. ✅ 生成 [tasks.md](./tasks.md)：可执行任务清单（已生成，与 design.md 基本对齐）
4. ✅ 生成 [review-tech-feasibility.md](./review-tech-feasibility.md)：技术方案可行性审查报告（已生成，36 项 API 核实 + 9 项冲突清单 + 9 项意淫清单）
5. ⏳ 生成 [review-completeness.md](./review-completeness.md)：文档完整性审查报告（待生成）
6. ⏳ 修订 spec.md：修复 9 项意淫 + 6 项文档矛盾，对齐 design.md（spec.md R10 AdaptiveLoadControl 热切换 / R4.2 FLAG_BLOCK_ON_CACHE / R1.3 LoadControl 档位 / R8 OkHttp 超时等）
7. ⏳ 实施前需用户确认：激进策略参数（bufferForPlayback GOOD 档 500ms）+ 是否启用 HTTP/2 分域策略 + 是否启用多级缓存 + 是否引入 Cronet 依赖
