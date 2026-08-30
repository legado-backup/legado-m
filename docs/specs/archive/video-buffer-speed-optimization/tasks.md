# tasks.md - 视频缓冲速度激进优化（聚焦当前播放）

> **状态**：🔄 设计中（R2，对齐 design.md 权威源，已修复"已实施"误描述 + 统一参数 + 删除意淫任务 + 新增遗漏任务）
> **创建日期**：2026-07-28
> **格式**：`- [ ] X.Y` 任务清单 + AOAdapt 日志
> **核心定位**：聚焦当前视频缓冲速度（非下一个视频预加载），激进策略默认中高端机
> **关联规范**：`docs/specs/video-prebuffer-enhancement/`（预加载，独立任务，不混淆）
> **权威源**：`design.md`（本 tasks.md 对齐 design.md 的 ADR 决策与参数）

---

## 0. 任务背景与核心约束

### 0.1 用户核心诉求
1. **聚焦当前视频缓冲速度**：不是下一个视频预加载（预加载由 `video-prebuffer-enhancement` 独立处理）
2. **激进策略**：默认中高端机参数（HIGH 档位，检测失败也降级到 HIGH 而非 MID/LOW）
3. **结合网上成熟方案**：参考 Media3 官方推荐 + B站/YouTube 激进策略
4. **覆盖各类型视频**：HLS（m3u8）/ MP4 / DASH / TS / FLV / MKV

### 0.2 已实施代码状态（基于 design.md 源码核实，修复"已实施"误描述）
| 文件 | 实施状态 | 项 | 备注 |
|------|---------|------|------|
| `ExoPlayerHelper.kt` | ✅ 已实施 | `createLoadControlByTier`（WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s） | LoadControl 分档已就位（档位参数保留现有，对齐 design.md 1.1.3） |
| `ExoPlayerHelper.kt` | 🔄 待实施 | `setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)` | 当前默认 50MB 截断 maxBuffer，需补全（AD-03） |
| `ExoPlayerHelper.kt` | 🔄 待实施（当前继承书源 50 连接池） | 视频专用 `ConnectionPool(10, 5min)` | `HttpHelper.kt` L101 有 50 连接池用于书源，视频通过 newBuilder() 派生继承，无专用池（AD-02） |
| `ExoPlayerHelper.kt` | ✅ 已实施 | `CacheControl.maxAge(1天)` | 客户端缓存控制（AD-11 建议移除，作用对象是 CDN 非 SimpleCache） |
| `Exo2MediaPlayer.kt` | 🔄 待实施 | HLS `setAllowChunklessPreparation(true)` | **代码实测未调用**（HLS 分支仅 `HlsMediaSource.Factory(dataSourceFactory).createMediaSource`），design.md L55/L214 确认（AD-05） |
| `Exo2MediaPlayer.kt` | 🔄 待实施 | HLS `setLowLatencyModeEnabled(true)` | **代码实测未调用**，仅 LL-HLS 源启用（P2，对齐 design.md 1.2.3） |
| `PlayerInstancePool.kt` | ✅ 已实施 | `DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` | 64KB 对齐分配（AD-09 建议提升至 256KB） |
| `PlayerInstancePool.kt` | 🔄 待实施 | `forceEnableMediaCodecAsynchronousQueueing` + `setEnableDecoderFallback` | sharedRendererFactory 未启用（AD-07） |

### 0.3 优化目标（量化）
| 指标 | 当前基线（估） | 目标值 |
|------|--------------|--------|
| TTFB（首帧时间） | ~800ms-1.5s | <500ms |
| 缓冲中断次数 | 频繁 | <1次/小时 |
| 丢帧率 | 偶发卡顿 | <0.1% |
| 带宽利用率 | ~60-70% | >90% |

---

## 1. 准备工作

- [ ] 1.1 确认需求范围（用户四个核心诉求已明确：聚焦当前/激进策略/成熟方案/全格式覆盖）
- [ ] 1.2 阅读相关源码（ExoPlayerHelper.kt / Exo2MediaPlayer.kt / PlayerInstancePool.kt / VideoPlay.kt AppConfig 配置项）
- [ ] 1.3 验证已实施代码状态（LoadControl 分档已实施；setAllowChunklessPreparation / ConnectionPool 视频专用 / 异步队列 均未实施），确认与 design.md 一致
- [ ] 1.4 调研网上成熟方案（Media3 官方 DefaultLoadControl 文档 + ExoPlayer Buffering 策略 + B站/YouTube 激进策略）
- [ ] 1.5 评估 HTTP/2 分域策略风险（对齐 design.md AD-02：默认 HTTP/2，遇 StreamResetException 降级 HTTP_1_1 并缓存 1 小时，非一刀切）
- [ ] 1.6 确认 Media3 版本支持的目标 API（`setTargetBufferBytes` / `setPrioritizeTimeOverSizeThresholds` 需 Media3 1.x+，项目 1.10.1 满足）
- [ ] 1.7 确认 DeviceInfoHelper 当前档位划分（已就位 HIGH/MID 两档，本任务沿用）
- [ ] 1.8 确认 AppConfig 用户可配置参数扩展点（VideoPlay.kt 现有结构）

## 2. LoadControl 深度优化（P0）

> **目标**：当前 ExoPlayer 默认 LoadControl 仍以 size 限制优先，导致弱网时缓冲区提前停止填充。改为时间优先 + 无 size 上限，让缓冲区在弱网时填得更满。
> **档位参数**：统一为 WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s（保留现有，对齐 design.md 1.1.3 + 实际代码 ExoPlayerHelper.kt L133-L155）

- [ ] 2.1 启用 `setTargetBufferBytes(-1)`（不限制字节总量，仅以时间窗口控制）
  - 修改位置：`ExoPlayerHelper.kt#createLoadControlByTier`
  - 风险评估：内存占用上升，但中高端机内存≥6GB，可承受（AD-03）
- [ ] 2.2 启用 `setPrioritizeTimeOverSizeThresholds(true)`（时间缓冲优先于字节缓冲）
  - 修改位置：同上
  - 收益：弱网时不会因 size 达标就停止加载，确保时间窗持续填充
- [ ] 2.3 调整 `bufferForPlayback` 起播门槛（对齐 design.md AD-10）
  - WEAK：500ms（保留，弱网需首帧保护）
  - MEDIUM：1s → 800ms
  - GOOD：1s → 500ms（中高端机激进起播）
  - 修改位置：同上
- [ ] 2.4 验证 LoadControl 配置生效（logcat 打印实际参数）
  - Action: 在 `ExoPlayerHelper.kt#createLoadControlByTier` 末尾添加 `AppLog.put("[BufferSpeed] tier=HIGH targetBufferMs=12000 targetBufferBytes=-1 prioritizeTime=true")` 日志
  - Observation: 真机播放视频时 logcat 输出上述参数，确认 LoadControl 实际生效
  - Adapt: 若 logcat 显示 `targetBufferBytes` 仍为默认值（如 50MB），说明 API 调用未生效，需检查 Media3 版本兼容性
  - 验证包：`io.legado.miss.app.debug`（代码优化任务必须用测试包，按 AGENTS.md 规范）

> **已删除任务**：原 2.3 "评估 Dynamic LoadControl（AdaptiveLoadControl 运行时热切换）" 已被 design.md AD-01 否决（触发 re-prepare 中断 1-3s + PlayerInstancePool 池化冲突 + 实现复杂度高 + 收益有限），不实施。

## 3. HLS 协议深度优化（P0）

> **目标**：HLS 是用户最常播放的协议，当前 setAllowChunklessPreparation 未启用，首帧需下载首个分片才能 preparation。启用 chunkless preparation + 直播偏移配置 + 分段重试。

- [ ] 3.1 实施 `setAllowChunklessPreparation(true)` + `setLowLatencyModeEnabled(true)`（新增，对齐 design.md AD-05）
  - 修改位置：`ExoPlayerHelper.kt#createMediaSource` HLS 分支（L195-L220）+ `Exo2MediaPlayer.kt#applyMediaSourceByType` HLS 分支（L279-L285）两处
  - 当前状态：🔄 待实施（代码实测两处 HLS 分支均未调用，design.md L55/L214 确认）
  - 收益：仅解析 m3u8 清单即完成 preparation，首帧耗时降 30%+（ExoPlayer 官方 benchmark）
  - `setLowLatencyModeEnabled(true)` 仅对 LL-HLS 源启用（通过 m3u8 `#EXT-X-SERVER-CONTROL` 标签检测），避免对非 LL-HLS 源副作用
  - 兼容性：>95%（ExoPlayer 官方统计），对非标 m3u8 自动降级
- [ ] 3.2 配置 `MediaItem.LiveConfiguration.targetOffsetMs`（对齐 design.md 1.2.3）
  - 点播（VOD）：`targetOffsetMs = 0`（无需低延迟，优先稳定性）
  - 直播（LIVE）：`targetOffsetMs = 3000`（3 秒延迟，对齐 design.md 1.2.3，平衡缓冲与实时性）
  - 修改位置：`ExoPlayerHelper.kt#createMediaItem`，根据 URL 是否为 m3u8 + 是否含 `#EXT-X-MEDIA-SEQUENCE` 判断 VOD/LIVE
- [ ] 3.3 配置 `OkHttpDataSource` 超时（统一参数 10s/15s/15s）
  - `connectTimeout = 10s`（默认 8s 偏短，弱网下连接建立慢）
  - `readTimeout = 15s`（HLS 分段读取，容忍慢速 CDN）
  - `writeTimeout = 15s`（与 readTimeout 对齐）
  - 修改位置：`ExoPlayerHelper.kt` OkHttp DataSource 构造处
- [ ] 3.4 配置 `DefaultLoadErrorHandlingPolicy` 分段重试（修复 API 语义）
  - 实施方式：自定义 `HlsLoadErrorPolicy extends DefaultLoadErrorHandlingPolicy`，**重写 `getRetryDelayMsFor(loadErrorInfo)` 返回 3000ms**（非构造传参，审查报告 #7 确认默认构造无参）
  - 修改位置：`ExoPlayerHelper.kt#createHlsMediaSourceFactory` 中 `setLoadErrorHandlingPolicy(HlsLoadErrorPolicy())`
  - Action: 真机播放 HLS 视频时，模拟单段失败（断网 3 秒后恢复），观察是否自动重试不中断播放
  - Observation: 3 秒后自动重试失败分段，播放不中断
  - Adapt: 若重试后仍失败，检查 CDN 是否支持 Range 请求；若不支持，降级为整段重新加载
  - 验证包：`io.legado.miss.app.debug`

> **已删除任务**：原 3.3 "评估自定义 ChunkSource（HlsChunkSourceFactory maxSegmentsToLoad=6）" 已删除（过度工程，design.md AD-05 降级为 P2，`maxSegmentsToLoad` 是 HlsChunkSource 内部参数，自定义需深入 HLS 内部实现，维护成本极高；弱网下预取 6 个 segment 可能加剧带宽压力）。

## 4. OkHttp 网络层优化（P1）

> **目标**：当前继承书源 50 连接池 + 强制 HTTP/1.1 + 无监控，需配置视频专用连接池 + 分域 HTTP/2 策略 + EventListener 埋点 + DohDns 防劫持。

- [ ] 4.1 实施 HTTP/2 分域策略（对齐 design.md AD-02）
  - 默认尝试 HTTP/2，遇 `StreamResetException` 自动降级到 HTTP_1_1 并缓存该域名降级标记 1 小时
  - 实现：新增 `HttpProtocolInterceptor.kt`（OkHttp Interceptor），捕获 `StreamResetException` 后切换 protocols
  - 决策点：非一刀切 HTTP_1_1，恢复 HTTP/2 多路复用收益（HLS 多分片并发）
- [ ] 4.2 新增 `EventListener` 监听 DNS/连接/TLS 耗时
  - 修改位置：`ExoPlayerHelper.kt` OkHttpClient 构造处 `.eventListenerFactory(BufferSpeedEventListener())`
  - 新增 `BufferSpeedEventListener.kt`：记录 `dnsStart/dnsEnd/connectStart/connectEnd/tlsHandshakeStart/tlsHandshakeEnd`
  - AppLog Tag：`BufferSpeed`，输出格式：`dns=Xms connect=Xms tls=Xms`
- [ ] 4.3 调整 `Dispatcher` 并发参数（对齐 design.md 1.3.3）
  - `maxRequests = 64`（默认 64，已合理）
  - `maxRequestsPerHost = 20`（默认 5，HLS 多分段并发需提升到 20，对齐 design.md）
  - 修改位置：`ExoPlayerHelper.kt` OkHttpClient 构造处 `.dispatcher(Dispatcher().apply { ... })`
- [ ] 4.4 优化超时配置（统一参数 10s/15s/15s）
  - `connectTimeout = 10s` / `readTimeout = 15s` / `writeTimeout = 15s`（与 §3.3 对齐，删除 spec.md 的 1s/500ms 极激进超时）
  - `callTimeout = 30s`（整体请求超时，防止僵尸连接）
  - 修改位置：同上
- [ ] 4.5 配置视频专用 `ConnectionPool(10, 5min)`（新增，对齐 design.md AD-02）
  - 当前状态：🔄 待实施（当前继承书源 50 连接池，视频专用连接池不存在，design.md L83 确认）
  - 实施：视频专用 `OkHttpClient` 构造时 `.connectionPool(ConnectionPool(10, 5, TimeUnit.MINUTES))`
  - 收益：与书源请求池隔离，避免视频长连接占用书源连接配额
  - 修改位置：`ExoPlayerHelper.kt` okhttpDataFactory 构造处
- [ ] 4.6 注入 DohDns 防劫持（新增）
  - 实施：视频流 `OkHttpClient` 注入 `DohDns`（DoH over HTTPS），防止 ISP DNS 劫持视频域名
  - 修改位置：`ExoPlayerHelper.kt` OkHttpClient 构造处 `.dns(DohDns(...))`
  - 决策点：复用项目现有 DohDns 实现（若存在），否则评估引入
- [ ] 4.7 评估 Cronet via Google Play Services 用于视频流（新增）
  - 调研：Cronet（Chromium 网络栈）vs OkHttp 用于视频流，Cronet 优势在 QUIC/HTTP/3 + 更好的弱网表现
  - 决策点：评估 Cronet 依赖体积 + Google Play Services 可用性 + 与现有 OkHttpDataSource 兼容性，P2 评估后决定
  - 注意：release 包需验证 ProGuard 规则（参考 AGENTS.md §真机测试包选择规范 铁证：Cronet 149+ ProGuard 规则缺失）

## 5. CacheDataSource 优化（P1）

> **目标**：缓存读取失败时不应中断播放，应回退到网络；缓存淘汰策略需评估激进 vs 保守。

- [ ] 5.1 启用 `FLAG_IGNORE_CACHE_ON_ERROR` + `FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH`（对齐 design.md AD-06）
  - 修改位置：`ExoPlayerHelper.kt` CacheDataSource 构造处 `setFlags(CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR or CacheDataSource.FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH)`
  - 收益：缓存读取异常/长度不匹配时自动降级到网络，不中断播放
- [ ] 5.2 评估 `LeastRecentlyUsedCacheEvictor` vs `NoOpCacheEvictor`
  - LRU：自动淘汰最久未访问（默认推荐，项目已使用）
  - NoOp：永不淘汰（依赖外部清理，激进策略下可能爆磁盘）
  - 决策点：保留 LRU 默认，激进策略下用户可手动扩大 `maxCacheSize`
- [ ] 5.3 评估 `CacheDataSink.setFragmentSize(2MB)`（对齐 design.md 1.4.3）
  - 当前 `DEFAULT_FRAGMENT_SIZE`（5MB）偏大，HLS 小分片（2MB ts）写入浪费空间
  - 决策点：降至 2MB，P1 实施
- [ ] 5.4 评估多级缓存（内存+磁盘）
  - 调研：Media3 `CacheDataSink` + 内存 `ByteArrayDataSource` 二级缓存
  - 决策点：实施复杂度高 + OOM 风险，P2 评估，若 P0+P1 达标则不做
- [ ] 5.5 评估 `CacheUtil` 预加载（与 `video-prebuffer-enhancement` 协调）
  - 注意：本任务聚焦当前视频缓冲，预加载由 `video-prebuffer-enhancement` 独立处理
  - 决策点：仅评估缓存共享，不实施预加载逻辑

> **已删除任务**：spec.md R4.2 `FLAG_BLOCK_ON_CACHE` 已删除（API 不存在，审查报告 #26 确认 Media3 1.x 中实际为 `FLAG_BLOCK_ON_CACHE_WRITE`，design.md 1.4.3 未提此 flag，不实施）。

## 6. 自适应码率优化（P1）

> **目标**：默认自适应码率算法对带宽变化反应迟钝，需调参使其更快降级（保播放流畅）+ 更慢升级（避免抖动）。
> **分辨率限制**：统一为 `setMaxVideoSize(1920, 1080)` 限制 1080p（对齐 design.md AD-08，删除 setMaxVideoSizeSd 720p）

- [ ] 6.1 配置 `setMaxVideoSize(1920, 1080)`（限制 1080p，对齐 design.md AD-08）
  - 修改位置：`PlayerInstancePool.kt#createTrackSelector` 返回的 `DefaultTrackSelector`
  - 收益：限制无效高分辨率解码（4K 视频在 1080p 屏幕仍尝试解码 4K），节省带宽与解码资源
  - 用户可配置：`videoMaxResolution`（720p/1080p/1440p/4K），默认 1080p
- [ ] 6.2 注入共享 `bandwidthMeter`（对齐 design.md AD-12）
  - 修改位置：`PlayerInstancePool.kt#createTrackSelector` 改为 `DefaultTrackSelector(appCtx, ExoPlayerHelper.bandwidthMeter)`
  - 收益：LoadControl 档位判断与 TrackSelector 码率选择基于同一带宽测量，决策一致
- [ ] 6.3 配置 `setAdaptiveSelectionMarginMs(1500)`（1.5 秒缓冲余量触发自适应）
  - 收益：缓冲低于 1.5s 时主动降码率，避免等到缓冲耗尽才降
- [ ] 6.4 配置 `setMinDurationForQualityIncreaseMs(20000)`（20 秒稳定期才升码率）
  - 收益：避免带宽瞬时高峰触发升级后又降级抖动
- [ ] 6.5 配置 `setExceededBufferRatioToConsiderQualityIncrease(1.5f)`（缓冲需达 1.5 倍目标才升级）
  - 收益：升级前确保缓冲充足，升级后即使带宽下降也有缓冲垫
  - 注意：审查报告 #23 标注此 API 名称需在 Media3 1.10.1 源码核实，实施前确认

> **已删除任务**：spec.md R5.5 `setViewportSize` 未配合 `setViewportOrientationSensitive` 效果有限，降级为 P2 不实施。

## 7. 解码器优化（P2）

> **目标**：解码线程优先级与异步队列优化，降低解码延迟。P2 优先级，P0+P1 达标后视情况实施。

- [ ] 7.1 启用 `forceEnableMediaCodecAsynchronousQueueing(true)` + `setEnableDecoderFallback(true)`（对齐 design.md AD-07）
  - 修改位置：`PlayerInstancePool.kt#sharedRendererFactory`（L79-L83）
  - 当前状态：🔄 待实施（sharedRendererFactory 仅配置 EXTENSION_RENDERER_MODE_PREFER，未启用异步队列与解码回退）
  - 收益：异步队列释放解码器线程阻塞，降低主线程卡顿；硬件解码失败自动回退软件
  - 风险：部分老设备 MediaCodec 异步模式兼容性差，需版本判断（API ≥ 23，项目 minSdk=23 满足）+ 设备黑名单（如 Samsung S8）
  - 新增 `DeviceCodecBlacklist.kt`：已知问题设备黑名单检测
- [ ] 7.2 评估解码线程优先级
  - 调研：`Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO)`（-16）
  - 决策点：可能影响系统其他音频线程，P2 评估后决定

> **已删除任务**：原 7.2 "评估 `MediaCodecSelector` 优先硬件解码" 已删除（过度工程，`DefaultMediaCodecSelector.DEFAULT` 已优先硬件解码，自定义需跟踪各厂商解码器命名变化，维护成本极高，design.md AD-07 未提）。

## 8. 性能监控埋点（P1）

> **目标**：无监控无法验证优化效果，需新增 AnalyticsListener 采集关键指标。

- [ ] 8.1 新增 `AnalyticsListener` 监听（对齐 design.md AD-04）
  - 新增 `BufferSpeedAnalyticsListener.kt`（design.md 命名 `VideoAnalyticsListener.kt`）
  - 监听事件：`onPlaybackStateChanged` / `onDroppedFrames` / `onBandwidthSample` / `onLoadStarted` / `onLoadCompleted` / `onRenderedFirstFrame` / `onVideoFrameProcessingOffsetCount`
  - AppLog Tag：`BufferSpeed`，输出格式：`event=xxx url=path前40字符 耗时=Xms`
  - release 包 WARN/ERROR 始终输出（参考 video-prebuffer-enhancement AD-16）
- [ ] 8.2 采集 TTFB（首帧时间）< 500ms
  - 指标定义：`onLoadStarted` 到 `STATE_READY` 的时间差
  - 告警阈值：> 500ms 时输出 WARN 日志
- [ ] 8.3 采集缓冲中断次数 < 1次/小时
  - 指标定义：`STATE_READY → STATE_BUFFERING` 转换次数
  - 告警阈值：> 1次/小时时输出 WARN 日志
- [ ] 8.4 采集丢帧率 < 0.1%
  - 指标定义：`onDroppedFrames` 累计 droppedFrames / totalFrames
  - 告警阈值：> 0.1% 时输出 WARN 日志
- [ ] 8.5 采集带宽利用率 > 90%
  - 指标定义：实际加载字节 / 理论可用带宽（基于 `onBandwidthSample`）
  - 告警阈值：< 90% 时输出 INFO 日志（提示带宽未充分利用）

## 9. 用户可配置参数扩展（P1）

> **目标**：激进策略默认值可能不适合所有用户，提供参数让用户自行调整。

- [ ] 9.1 新增 `videoBufferTargetBytes` 参数（用户可配置 `targetBufferBytes`）
  - 默认值：`-1`（无限制，激进策略）
  - 用户可设：`0`（自动，按档位） / `-1`（无限制） / `>0`（具体字节数）
  - 修改位置：`VideoPlay.kt` AppConfig 配置项 + `ExoPlayerHelper.kt#createLoadControlByTier` 读取参数
- [ ] 9.2 新增 `videoHttpTimeoutSec` 参数（用户可配置 OkHttp 超时）
  - 默认值：`10`（10 秒，激进策略）
  - 用户可设：`5-30` 秒
  - 修改位置：同上
- [ ] 9.3 新增 `videoAdaptiveBitrateEnabled` 参数（用户可开关自适应码率）
  - 默认值：`true`（启用，激进策略）
  - 用户可设：`true/false`
  - 修改位置：同上
- [ ] 9.4 新增 `videoPerformanceMonitorEnabled` 参数（用户可开关性能监控）
  - 默认值：`true`（启用，便于问题定位）
  - 用户可设：`true/false`
  - 修改位置：同上
- [ ] 9.5 新增 `videoMaxResolution` 参数（用户可配置最大分辨率，对齐 design.md AD-08）
  - 默认值：`1080p`
  - 用户可设：`720p/1080p/1440p/4K`
  - 修改位置：同上
- [ ] 9.6 UI 入口：在视频播放设置页新增"缓冲速度优化"分组（参考 `video-prebuffer-enhancement` 的 UI 模式）

## 10. 验证与测试（强制）

> **强制规范**：按 AGENTS.md §强制规则：AI 自动端到端测试 + §真机测试包选择规范，代码优化任务必须用测试包 `io.legado.miss.app.debug`。

- [ ] 10.1 编译验证（测试包 `io.legado.miss.app.debug`）
  - 命令：`./gradlew assembleDebug -PpackageName=io.legado.miss.app.debug`（或参考 `ai_tests/scripts/quick_build_install.py`）
  - 验证：`BUILD SUCCESSFUL` 无报错
- [ ] 10.2 真机验证（中高端机，HLS/MP4/DASH 各播放 3 个视频）
  - 测试包：`io.legado.miss.app.debug`（强制，按 AGENTS.md §真机测试包选择规范）
  - 测试脚本：`ai_tests/scripts/l2_verify_video_player.py --scenario buffer_speed`
  - 视频类型：HLS（m3u8）/ MP4 / DASH 各 3 个，覆盖点播+直播
  - 时长：每个视频至少播放 5 分钟，观察缓冲中断次数
- [ ] 10.3 性能指标对比（优化前 vs 优化后 TTFB/缓冲中断/丢帧率）
  - Action: 优化前基线（LoadControl 分档已实施）vs 优化后（本任务全部完成），各播放同一组视频 10 分钟
  - Observation: 对比 logcat 中 BufferSpeedAnalyticsListener 输出的 TTFB/缓冲中断次数/丢帧率/带宽利用率
  - Adapt: 若优化后指标未达标（TTFB<500ms / 中断<1次/h / 丢帧<0.1% / 带宽>90%），逐项排查：LoadControl 是否生效 → HLS 配置 → OkHttp 超时 → 自适应码率
  - 验证包：`io.legado.miss.app.debug`
- [ ] 10.4 网络切换验证（WiFi → 4G → WiFi 不中断播放）
  - 测试场景：播放 HLS 视频中切换网络，观察是否自动重连不中断
  - 验证点：`HlsLoadErrorPolicy` 重写 `getRetryDelayMsFor` 返回 3000ms 生效，3 秒内自动重试
- [ ] 10.5 logcat 验证（LoadControl 实际参数 + AnalyticsListener 指标输出）
  - Grep 过滤：`adb logcat | grep -E "BufferSpeed|LoadControl"`（只输出技术信息，按 output-safety 规范）
  - 验证：LoadControl 参数（targetBufferBytes=-1, prioritizeTime=true）+ AnalyticsListener 指标（TTFB/中断/丢帧/带宽）均输出
- [ ] 10.6 问题清单记录（按 `real-device-test-reuse.md` 规范写入 `issues-found.md`）
  - 真机测试中发现的所有问题必须记录到 `ai_tests/issues-found.md`

## 11. 文档同步（强制）

> **强制规范**：按 AGENTS.md §强制规则：版本交付同步 + §任务完成前强制检查清单。

- [ ] 11.1 更新 `assets/updateLog.md`（**编译前更新**，基于 `git diff` 分析真实代码变更）
  - 内容：本次视频缓冲速度优化的可感知变化（如"播放视频更流畅，缓冲中断减少"）
  - 禁止：仅对已有日志条目做文字合并
- [ ] 11.2 更新 `docs/INDEX.md`（状态从"设计中" → "开发中" → "已完成"）
  - 本任务条目：`docs/specs/video-buffer-speed-optimization/`
- [ ] 11.3 更新 `docs/project-flow/architecture/rule-engine.md`（如涉及播放器架构变更）
  - 评估：本任务是否涉及规则引擎架构，若涉及则同步更新
- [ ] 11.4 更新 `.trae/memory/ai_memory_main.md`（任务状态 + 用户反馈）
  - 任务状态：设计完成 → 实施中 → 真机验证中 → 已完成
  - 用户反馈：AskUserQuestion 响应必须第一时间记录（按 context-recovery.md 规范，24H 制时间戳）
- [ ] 11.5 检查清单核对（按 AGENTS.md §任务完成前强制检查清单 7 项）
  - 1.思考无违禁词 / 2.调试日志已清理 / 3.updateLog 已更新 / 4.文档同步 / 5.主动沉淀 / 6.问题清单 / 7.AskUserQuestion 确认

---

## 附录 A：网上成熟方案参考（调研依据）

| 方案来源 | 关键策略 | 本任务采纳情况 |
|---------|---------|--------------|
| Media3 官方 DefaultLoadControl 文档 | `setTargetBufferBytes(-1)` + `setPrioritizeTimeOverSizeThresholds(true)` | §2.1 / §2.2 已采纳 |
| Media3 官方 HLS 配置文档 | `setAllowChunklessPreparation` + `setLowLatencyModeEnabled` + `targetOffsetMs` | §3.1 / §3.2 已采纳（🔄 待实施） |
| Media3 官方自适应码率文档 | `setMaxVideoSize(1920,1080)` + `setAdaptiveSelectionMarginMs` + `setMinDurationForQualityIncreaseMs` | §6.1-6.5 已采纳 |
| Media3 官方 AnalyticsListener 文档 | `onDroppedFrames` / `onBandwidthSample` / `onLoadStarted/Completed` | §8.1-8.5 已采纳 |
| ExoPlayer Buffering 策略（社区） | Dynamic LoadControl 基于带宽动态调整 | **已否决**（design.md AD-01，触发 re-prepare 中断） |
| B站播放器激进策略 | 优先流畅度（1080p 限制）+ 大缓冲 + 快速降级 | §6.1-6.5 已采纳 |
| YouTube 激进策略 | TTFB 监控 + 带宽利用率监控 + 自适应码率 | §8.2/8.5 已采纳 |
| OkHttp 官方 Dispatcher 文档 | `maxRequestsPerHost` 提升 HLS 多分段并发 | §4.3 已采纳 |
| OkHttp 官方 EventListener 文档 | DNS/连接/TLS 耗时监控 | §4.2 已采纳 |
| OkHttp 官方 ConnectionPool 文档 | 视频专用连接池与书源隔离 | §4.5 已采纳（🔄 待实施） |
| Media3 CacheDataSource 文档 | `FLAG_IGNORE_CACHE_ON_ERROR` 缓存失败回退网络 | §5.1 已采纳 |
| DoH (DNS over HTTPS) 方案 | DohDns 防劫持视频域名 | §4.6 已采纳（新增） |
| Cronet (Chromium 网络栈) | QUIC/HTTP/3 + 弱网表现 | §4.7 评估中（新增） |

## 附录 B：风险与回滚预案

| 风险 | 概率 | 影响 | 回滚预案 |
|------|------|------|---------|
| `setTargetBufferBytes(-1)` 导致内存暴涨 | 中 | 高（OOM） | 用户可配置 `videoBufferTargetBytes` 回退到具体值（如 100MB） |
| HTTP/2 队头阻塞 | 中 | 中（卡顿） | 分域策略自动降级 HTTP_1_1 + 1 小时缓存（AD-02） |
| 自适应码率过度降级（始终 1080p） | 低 | 低（清晰度下降） | 用户可配置 `videoMaxResolution=4K` |
| `forceEnableMediaCodecAsynchronousQueueing` 兼容性 | 中 | 中（解码失败） | API < 23 自动禁用 + 设备黑名单 + 软件解码回退（AD-07） |
| HLS `targetOffsetMs=0` 直播延迟过大 | 低 | 低（直播延迟 5-10s） | 仅 VOD 设 0ms，LIVE 设 3000ms |
| Dispatcher `maxRequestsPerHost=20` 过载 | 低 | 低（CDN 限流） | 降回默认 5 |
| `setAllowChunklessPreparation` 不兼容非标 m3u8 | 低 | 低（首帧无加速） | ExoPlayer 自动降级到默认 preparation |
| DohDns 解析失败 | 低 | 中（DNS 不可用） | 回退到系统 DNS |
| Cronet 依赖体积/兼容性 | 中 | 中（引入成本） | P2 评估，不实施则保留 OkHttp |

## 附录 C：与现有 spec 的边界划分

| 现有 spec | 边界 | 协调点 |
|----------|------|--------|
| `video-prebuffer-enhancement` | 预加载下一个视频 | §5.5 评估缓存共享，不实施预加载 |
| `exoplayer-resilience` | MIME 嗅探 + WebView 降级 | 不重叠，本任务假设 MIME 已识别 |
| `video-m3u8-cache` | m3u8 缓存机制 | §5.2 评估缓存淘汰策略，可能与本任务缓存共享 |
| `player-mature-solutions-alignment` | 播放器成熟方案对齐 | 参考 B站/YouTube 策略，本任务已采纳 |

---

## 实施顺序建议

1. **P0（必做）**：§2 LoadControl + §3 HLS 优化（含 setAllowChunklessPreparation 实施）→ §10.1-10.3 验证
2. **P1（推荐）**：§4 OkHttp（含 ConnectionPool 视频专用 + DohDns）+ §5 CacheDataSource + §6 自适应码率 + §8 性能监控 + §9 用户可配置 → §10.4-10.5 验证
3. **P2（可选）**：§7 解码器优化 + §4.7 Cronet 评估 → 视 P0+P1 效果决定是否实施

> **强制门禁**：每个 P 级阶段完成后必须执行 AskUserQuestion（三选项：通过/需调整/拒绝），按 AGENTS.md §强制规则：AI 自动端到端测试 规范。
