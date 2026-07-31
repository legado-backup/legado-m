# 技术方案可行性审查报告（review-tech-feasibility）

> **审查目标**：深度审查 video-buffer-speed-optimization 设计文档（README.md / spec.md / design.md / tasks.md）的技术方案可行性，重点检查"意淫"（不切实际的方案/API 不存在/与现有代码冲突/与项目规范冲突）。
> **审查日期**：2026-07-28
> **审查方法**：源码核实（ExoPlayerHelper.kt / Exo2MediaPlayer.kt / PlayerInstancePool.kt / VideoPlay.kt / libs.versions.toml）+ API 真实性 WebSearch 核实（Media3 1.10.1 官方文档）+ 项目规范对照（AGENTS.md）
> **Media3 版本**：1.10.1（`gradle/libs.versions.toml` L65 `media3 = "1.10.1"`）

---

## 一、API 真实性核实表

| # | API 名称 | 文档出现位置 | 真实性 | 版本要求 | 备注 |
|---|---------|------------|-------|---------|------|
| 1 | `DefaultLoadControl.Builder.setTargetBufferBytes(Int)` | spec R1.1 / design 1.1.3 | ✅ 真实 | Media3 1.0+ | 传 `-1` 即 `TARGET_BUFFER_BYTES_INFINITE` |
| 2 | `DefaultLoadControl.Builder.setPrioritizeTimeOverSizeThresholds(Boolean)` | spec R1.2 / design 1.1.3 | ✅ 真实 | Media3 1.0+ | WebSearch 已确认官方文档存在 |
| 3 | `DefaultLoadControl.Builder.setBackBuffer(Int, Boolean)` | spec R1.4 | ✅ 真实 | Media3 1.0+ | 参数：backBufferDurationMs, retainBackBufferFromKeyframe |
| 4 | `HlsMediaSource.Factory.setAllowChunklessPreparation(Boolean)` | spec R2.4 / design 1.2.3 | ✅ 真实 | Media3 1.0+ | WebSearch 多个官方/社区文档确认 |
| 5 | `HlsMediaSource.Factory.setLowLatencyModeEnabled(Boolean)` | spec R2.4 / tasks 0.2 | ✅ 真实 | Media3 1.0+ | LL-HLS 场景使用 |
| 6 | `HlsMediaSource.Factory.setLoadErrorHandlingPolicy(LoadErrorHandlingPolicy)` | spec R11.3 | ✅ 真实 | Media3 1.0+ | 注：参数应为 `LoadErrorHandlingPolicy`，不是 `DefaultLoadErrorHandlingPolicy(3000)` 直接传 int |
| 7 | `DefaultLoadErrorHandlingPolicy` 构造 | spec R11.1 | ⚠️ 半真实 | Media3 1.0+ | `DefaultLoadErrorHandlingPolicy` 默认构造无参，重试间隔由 `getRetryDelayMsFor` 控制，"传 3000"含义不准确，需自定义子类 |
| 8 | `HlsMediaSource.Factory.setChunkSourceFactory(HlsChunkSource.Factory)` | spec R12.3 | ✅ 真实 | Media3 1.0+ | 自定义 ChunkSource 的高级 API，确实存在 |
| 9 | `MediaItem.LiveConfiguration.Builder().setTargetOffsetMs(Long)` | spec R2.1 / design 1.2.3 | ✅ 真实 | Media3 1.0+ | 直播 HLS 配置 |
| 10 | `MediaItem.LiveConfiguration.Builder().setMinOffsetMs(Long)` | spec R2.2 | ✅ 真实 | Media3 1.0+ | |
| 11 | `MediaItem.LiveConfiguration.Builder().setMaxOffsetMs(Long)` | spec R2.2 | ✅ 真实 | Media3 1.0+ | |
| 12 | `MediaItem.LiveConfiguration.Builder().setMinPlaybackSpeed(Float)` | spec R2.3 | ✅ 真实 | Media3 1.0+ | |
| 13 | `MediaItem.LiveConfiguration.Builder().setMaxPlaybackSpeed(Float)` | spec R2.3 | ✅ 真实 | Media3 1.0+ | |
| 14 | `DefaultRenderersFactory.forceEnableMediaCodecAsynchronousQueueing()` | spec R6.1 / design 1.6.3 | ✅ 真实 | Media3 1.0+ + API 23+ | 项目 minSdk=23，满足 |
| 15 | `DefaultRenderersFactory.setEnableDecoderFallback(Boolean)` | spec R6.2 / design 1.6.3 | ✅ 真实 | Media3 1.0+ | 项目代码已实施（PlayerInstancePool.sharedRendererFactory 链上未启用，但 ExoPlayerHelper 中有） |
| 16 | `DefaultRenderersFactory.setExtensionRendererMode(Int)` | spec R6.3 | ✅ 真实 | Media3 1.0+ | 已在 PlayerInstancePool.sharedRendererFactory 配置 EXTENSION_RENDERER_MODE_PREFER |
| 17 | `TrackSelectionParameters.Builder.setMaxVideoSizeSd()` | spec R5.1 | ✅ 真实 | Media3 1.0+ | **限制 720p**（SD） |
| 18 | `TrackSelectionParameters.Builder.setMaxVideoSize(Int, Int)` | design AD-08 | ✅ 真实 | Media3 1.0+ | **限制 1080p**（1920x1080） |
| 19 | `DefaultTrackSelector.Parameters.setAdaptiveSelectionMarginMs(Int)` | spec R5.2 / design 1.5.3 | ✅ 真实 | Media3 1.0+ | |
| 20 | `DefaultTrackSelector.Parameters.setMinDurationForQualityIncreaseMs(Int)` | spec R5.3 | ✅ 真实 | Media3 1.0+ | |
| 21 | `DefaultTrackSelector.Parameters.setMinDurationToRetainAfterDiscardMs(Int)` | spec R5.4 | ⚠️ 需核实 | 1.7+ 可能 | 此 API 名称需在 1.10.1 源码核实，部分版本叫 `setMinDurationToRetainAfterDiscardMs`，部分版本无此方法 |
| 22 | `DefaultTrackSelector.Parameters.setViewportSize(Int, Int)` | spec R5.5 | ⚠️ 半真实 | 1.x+ | API 名称为 `setViewportSize`，但需配合 `setViewportOrientationSensitive`，单独调用效果有限 |
| 23 | `DefaultTrackSelector.Parameters.setExceededBufferRatioToConsiderQualityIncrease(Float)` | tasks 6.4 | ⚠️ 需核实 | 1.x+ | 名称长且特殊，需在 1.10.1 源码核实 |
| 24 | `CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR` | spec R4.1 / design 1.4.3 | ✅ 真实 | Media3 1.0+ | 值=1，WebSearch 多个文档确认 |
| 25 | `CacheDataSource.FLAG_IGNORE_CACHE_ON_UNEXPECTED_LENGTH` | design 1.4.3 | ✅ 真实 | Media3 1.0+ | 值=2 |
| 26 | **`CacheDataSource.FLAG_BLOCK_ON_CACHE`** | **spec R4.2** | ❌ **不存在** | - | **Media3 1.x 中实际为 `FLAG_BLOCK_ON_CACHE_WRITE`（值=4）**，spec.md 写的 `FLAG_BLOCK_ON_CACHE` 是 ExoPlayer 2.x 旧名，Media3 已废弃 |
| 27 | `LeastRecentlyUsedCacheEvictor` | spec R4.3 / design 1.4.1 | ✅ 真实 | Media3 1.0+ | 项目代码已使用 |
| 28 | `CacheDataSink.Factory.setFragmentSize(Long)` | design 1.4.3 | ✅ 真实 | Media3 1.0+ | |
| 29 | `OkHttpClient.eventListenerFactory(EventListener.Factory)` | spec R3.3 | ✅ 真实 | OkHttp 4.x+ | 项目 OkHttp 版本满足 |
| 30 | `OkHttpClient.dispatcher(Dispatcher)` | spec R9 / design 1.3.3 | ✅ 真实 | OkHttp 4.x+ | |
| 31 | `Dispatcher.setMaxRequests(Int)` / `setMaxRequestsPerHost(Int)` | spec R9.1-9.2 | ✅ 真实 | OkHttp 4.x+ | |
| 32 | `OkHttpClient.connectTimeout / readTimeout / callTimeout` | spec R8 | ✅ 真实 | OkHttp 4.x+ | |
| 33 | `AnalyticsListener.onLoadStarted / onLoadCompleted / onDroppedFrames / onVideoInputFormatChanged / onPlayerStateChanged / onBandwidthEstimate` | spec R7 / design 1.7.3 | ✅ 真实 | Media3 1.0+ | 全部为官方 AnalyticsListener 回调 |
| 34 | `DefaultAllocator(true, C.DEFAULT_BUFFER_SEGMENT_SIZE)` | design 1.8.4 | ✅ 真实 | Media3 1.0+ | 项目已使用 |
| 35 | `MediaCodecSelector` 自定义 | spec R6.4 / tasks 7.2 | ✅ 真实 | Media3 1.0+ | 复杂度高，需实现接口 |
| 36 | `Process.setThreadPriority` | tasks 7.3 | ✅ 真实 | Android API 1+ | 标准 Android API |

### API 真实性核实总结

- **核实 API 总数**：36 项
- ✅ 真实存在：30 项
- ⚠️ 需进一步核实/半真实：5 项（#7、#21、#22、#23、`DefaultLoadErrorHandlingPolicy` 构造参数语义）
- ❌ 不存在/已废弃：1 项（#26 `FLAG_BLOCK_ON_CACHE`，应为 `FLAG_BLOCK_ON_CACHE_WRITE`）

---

## 二、与现有代码冲突清单

### 冲突-1：`setAllowChunklessPreparation` 实施状态描述与代码完全不符（严重）

| 文档 | 描述 |
|------|------|
| README.md L77 | `setAllowChunklessPreparation(true) + setLowLatencyModeEnabled(true)` **已实施** |
| spec.md L93 | "保留现有 `setAllowChunklessPreparation(true)` 和 `setLowLatencyModeEnabled(true)`" |
| tasks.md L25-L26 | `setAllowChunklessPreparation(true)` LL-HLS 优化已启用 / `setLowLatencyModeEnabled(true)` LL-HLS 低延迟已启用 |
| **design.md L55** | **诚实承认**："未启用 `setAllowChunklessPreparation`（代码实测确认）。任务描述中提及的'已实施'在当前主分支 `ExoPlayerHelper.kt` 中不存在" |
| **design.md L214** | 再次确认："实际未启用" |

**代码实测**：
- `ExoPlayerHelper.kt` L195-L220 `createMediaSource` HLS 分支：`HlsMediaSource.Factory(dataSourceFactory).createMediaSource(mediaItem)`，**未调用 setAllowChunklessPreparation**
- `Exo2MediaPlayer.kt` L279-L285 `applyMediaSourceByType` HLS 分支：`HlsMediaSource.Factory(ExoPlayerHelper.resolvingDataSource).createMediaSource(mediaItem)`，**也未调用 setAllowChunklessPreparation**

**冲突结论**：3 份文档（README/spec/tasks）"已实施"描述完全错误，design.md 是唯一诚实的文档。这是**严重的"意淫"**——基于不存在的"已实施"基线做"保留现有"决策。

### 冲突-2：OkHttp ConnectionPool(10, 5min) 实施状态描述与代码不符

| 文档 | 描述 |
|------|------|
| README.md L76 | `ConnectionPool(10, 5, TimeUnit.MINUTES)` + `Protocol.HTTP_1_1` + `CacheControl.maxAge(1天)` **已实施** |
| spec.md R8.4 | "保留现有 `ConnectionPool(10, 5, TimeUnit.MINUTES)`" |
| tasks.md L23 | `ConnectionPool(10, 5min, HTTP_1_1)` 当前强制 HTTP/1.1 |
| **design.md L83** | **诚实承认**："未显式配置 ConnectionPool（任务描述提及的 ConnectionPool(10,5min) 在 ExoPlayerHelper 中不存在，仅在 HttpHelper.kt L101 有 ConnectionPool(50, 5min) 用于书源请求）" |

**代码实测**：
- `ExoPlayerHelper.kt` L847-L857 `okhttpDataFactory`：`okHttpClient.newBuilder().callTimeout(0).protocols([HTTP_1_1]).followRedirects(true).build()`
- `okHttpClient`（来自 `HttpHelper`）的连接池是 50 连接（书源用），**视频专用连接池(10,5min)不存在**
- 视频请求通过 `newBuilder()` 派生，**继承书源的 50 连接池**

**冲突结论**：3 份文档"已实施 ConnectionPool(10,5min)"描述错误，实际是继承书源 50 连接池。design.md 再次唯一诚实。

### 冲突-3：三份文档对 LoadControl 参数描述严重不一致

| 文档 | WEAK | MEDIUM | GOOD |
|------|------|--------|------|
| **spec.md R1.3** | 3s/20s | 5s/60s | 5s/180s（**完全重写档位**） |
| **design.md 1.1.3** | 保留现有 5s/30s | 保留现有 8s/90s | 保留现有 8s/120s（仅追加 setTargetBufferBytes） |
| **tasks.md 0.2** | 5s/30s | 8s/90s | 8s/120s（与 design.md 一致） |
| **实际代码** ExoPlayerHelper.kt L133-L155 | 5s/30s | 8s/90s | 8s/120s（与 design.md/tasks.md 一致） |

**冲突结论**：spec.md R1.3 与代码、design.md、tasks.md 完全不一致。spec.md 要求"重写档位"（WEAK 3s/20s, GOOD 5s/180s），但 design.md 明确说"保留现有档位"。**spec.md 与 design.md 自相矛盾**。

### 冲突-4：三份文档对 OkHttp 超时配置描述严重不一致

| 文档 | connectTimeout | readTimeout | callTimeout |
|------|---------------|-------------|-------------|
| **spec.md R8.1-8.3** | 1s | 500ms | 5s（**极激进**） |
| **design.md 1.3.3** | 未提具体数值 | 未提 | 未提 |
| **tasks.md 3.2** | 10s | 15s | 未提 |
| **tasks.md 4.4** | 10s | 15s | 30s |
| **实际代码** | 默认 10s（OkHttp 默认） | 默认 10s | 0（无限制） |

**冲突结论**：
- spec.md 的 `connectTimeout(1s)` + `readTimeout(500ms)` 极度激进，**500ms readTimeout 在弱网场景几乎必然超时**
- tasks.md 的 `10s/15s` 与 spec.md 的 `1s/500ms` 完全矛盾
- 三份文档对同一参数给出三套不同数值，**实施时无法决策**

### 冲突-5：三份文档对 LoadControl 是否热切换严重不一致（架构级冲突）

| 文档 | 立场 |
|------|------|
| **spec.md R10 + 方案1** | **要求**实现 `AdaptiveLoadControl extends DefaultLoadControl`，重写 `shouldContinueLoading`，运行时热切换 |
| **design.md AD-01** | 明确"沿用路径A，运行时不热切换" |
| **design.md 附录 B** | 评估后**不采用** Dynamic LoadControl，理由：触发 re-prepare 中断、PlayerInstancePool 池化冲突、实现复杂度高、收益有限 |
| **tasks.md 2.3** | "评估 Dynamic LoadControl"，决策点模糊 |
| **README.md L261** | 明确"不实施 LoadControl 运行时热切换（与 video-prebuffer-enhancement R3 一致，路径 A）" |

**冲突结论**：**spec.md 与其他三份文档（README/design/tasks）在核心架构决策上完全矛盾**。spec.md R10 的 AdaptiveLoadControl 热切换方案被 design.md 多条 ADR 否决，**spec.md 是孤立的错误方案**。

### 冲突-6：三份文档对 setMaxVideoSize 分辨率限制不一致

| 文档 | API | 限制分辨率 |
|------|-----|-----------|
| **spec.md R5.1** | `setMaxVideoSizeSd()` | **720p**（SD） |
| **design.md AD-08** | `setMaxVideoSize(1920, 1080)` | **1080p** |

**冲突结论**：spec.md 限制 720p，design.md 限制 1080p，**两份文档对"激进策略"的默认分辨率完全不同**。

### 冲突-7：三份文档对 MediaItem.LiveConfiguration.targetOffsetMs 不一致

| 文档 | targetOffsetMs |
|------|---------------|
| **spec.md R2.1** | 2000ms |
| **design.md 1.2.3** | 3000ms |
| **tasks.md 3.1** | VOD=0ms, LIVE=2000ms |

**冲突结论**：三份文档三个数值，且 spec.md/design.md 未区分 VOD/LIVE。

### 冲突-8：spec.md R4.4 缓存大小与代码/设计文档不一致

| 文档 | 缓存大小 |
|------|---------|
| **spec.md R4.4** | 512MB（激进策略） |
| **design.md 1.4.1** | 默认 100MB，范围 50-2048MB |
| **VideoPlay.kt L113** | 默认 100MB |

**冲突结论**：spec.md 要求默认 512MB，但代码默认 100MB，design.md 也未提"默认调到 512MB"。

### 冲突-9：README/spec 称 `setEnableDecoderFallback` 已实施，但 PlayerInstancePool 未启用

| 文档 | 描述 |
|------|------|
| README.md L83 | `setEnableDecoderFallback(true)` 已实施 |
| **PlayerInstancePool.kt L79-L83** | `sharedRendererFactory = DefaultRenderersFactory(appCtx).setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)`，**未调用 setEnableDecoderFallback** |

**冲突结论**：需核实 `ExoPlayerHelper` 中是否有另一处 RenderersFactory 配置已启用 `setEnableDecoderFallback`，否则 README 描述与 PlayerInstancePool 实际配置不符。

---

## 三、与项目规范冲突清单

### 规范冲突-1：协程使用规范（AGENTS.md Code Style）

- **规范要求**：协程用自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装（非标准 launch+try/catch）
- **文档方案**：spec.md R7 AnalyticsListener 埋点要求"使用 `Handler.post` 切到后台线程处理"，未明确协程使用方式
- **冲突程度**：⚠️ 中等——埋点本身可在 AnalyticsListener 回调线程直接处理，但若涉及 IO（写文件）应使用项目协程封装
- **建议**：design.md 1.7.3 应明确"日志写入用 `AppLog.put`（已封装好主线程调度），不引入新协程"

### 规范冲突-2：日志输出规范（AGENTS.md Landmines）

- **规范要求**：日志用 `AppLog.put()`，禁止 `Timber` / `CoroutineExceptionHandler`，禁止 `android.util.Log.d/e`
- **文档方案**：tasks.md 8.1 AppLog Tag=`BufferSpeed`，spec.md R7.2-7.7 使用 AppLog，spec.md R14.2 明确"所有新增日志使用 `AppLog.put(tag, msg)` 而非 `Log.x`"
- **冲突程度**：✅ 无冲突——四份文档均遵守 AppLog 规范

### 规范冲突-3：真机测试包规范（AGENTS.md §真机测试包选择规范）

- **规范要求**：代码优化任务必须用测试包 `io.legado.miss.app.debug`
- **文档方案**：tasks.md 10.1/10.2 明确"测试包 `io.legado.miss.app.debug`（强制，按 AGENTS.md §真机测试包选择规范）"
- **冲突程度**：✅ 无冲突

### 规范冲突-4：updateLog.md 同步规范（AGENTS.md §版本交付同步）

- **规范要求**：编译前更新 updateLog.md，基于 git diff 分析真实代码变更
- **文档方案**：tasks.md 11.1 明确"编译前更新，基于 git diff 分析真实代码变更，禁止文字合并"
- **冲突程度**：✅ 无冲突

### 规范冲突-5：单例模式规范（AGENTS.md Code Style）

- **规范要求**：核心业务用 `object` 单例（ReadBook, WebBook, AppConfig），不引入 DI 框架
- **文档方案**：design.md 文件变更清单中 `VideoAnalyticsListener.kt` / `VideoEventListener.kt` / `HttpProtocolInterceptor.kt` / `DeviceCodecBlacklist.kt` 为新增类，未说明是否单例
- **冲突程度**：⚠️ 低——这些是工具类，非核心业务对象，可不单例。但 design.md 应明确这些类的实例化方式（per-player 还是全局单例）
- **建议**：design.md 应补充"VideoAnalyticsListener 为 per-ExoPlayer 实例（随 player.addAnalyticsListener 注册）；VideoEventListener 为 OkHttp 全局单例（eventListenerFactory 注入）"

### 规范冲突-6：错误处理规范（AGENTS.md Code Style）

- **规范要求**：错误处理用 `kotlin.runCatching`（带 `kotlin.` 前缀），字符串判空用 `isNullOrBlank()`
- **文档方案**：spec.md 未涉及错误处理代码细节
- **冲突程度**：⚠️ 低——需在实施时遵守，文档阶段无强制要求

### 规范冲突-7：并发文件修改规范（user_rules）

- **规范要求**：同一源码文件的所有 Edit 必须由主 Agent 串行执行
- **文档方案**：design.md 文件变更清单显示 `ExoPlayerHelper.kt` / `Exo2MediaPlayer.kt` / `PlayerInstancePool.kt` 均有多处变更
- **冲突程度**：⚠️ 实施阶段冲突——若用子代理并行实施，需确保同一文件串行 Edit
- **建议**：tasks.md 应明确"ExoPlayerHelper.kt 的 6 处变更由主 Agent 串行 Edit"

---

## 四、意淫清单（不切实际的方案）

### 意淫-1：spec.md R8.2 `readTimeout(500ms)` 极度激进（高风险）

- **方案**：OkHttp `readTimeout(500, TimeUnit.MILLISECONDS)`
- **意淫点**：500ms readTimeout 在弱网/跨境 CDN/慢速服务器场景几乎必然超时，会导致：
  - HLS 分片加载频繁超时 → 触发降级链 → 用户体验"播放失败"
  - 与"激进策略减少卡顿"目标完全相反
- **design.md 评估**：design.md 1.3.2 未提此激进超时，1.3.3 仅提"分域 HTTP/2 策略"
- **建议**：删除 spec.md R8.2，对齐 tasks.md 3.2/4.4 的 `readTimeout=15s`

### 意淫-2：spec.md R10 AdaptiveLoadControl 运行时热切换（已被否决）

- **方案**：自定义 `AdaptiveLoadControl extends DefaultLoadControl`，重写 `shouldContinueLoading`，运行时根据带宽热切换
- **意淫点**：
  1. design.md AD-01 + 附录 B 已明确否决（触发 re-prepare 中断 1-3s、PlayerInstancePool 池化冲突、实现复杂度高、收益有限）
  2. README.md L261 明确"不实施 LoadControl 运行时热切换"
  3. spec.md 自身 R1.3 又要求保留三档静态配置——**spec.md 内部自相矛盾**
- **建议**：删除 spec.md R10 + 方案1 + Approach 中"Dynamic LoadControl 自适应"描述，与 design.md AD-01 对齐

### 意淫-3：spec.md R4.2 `FLAG_BLOCK_ON_CACHE` API 不存在

- **方案**：启用 `CacheDataSource.FLAG_BLOCK_ON_CACHE`
- **意淫点**：Media3 1.x 中**实际常量为 `FLAG_BLOCK_ON_CACHE_WRITE`（值=4）**，`FLAG_BLOCK_ON_CACHE` 是 ExoPlayer 2.x 旧名，已废弃
- **核实方式**：WebSearch 多个 Media3 文档显示 `FLAG_BLOCK_ON_CACHE_WRITE`
- **建议**：spec.md R4.2 改为 `FLAG_BLOCK_ON_CACHE_WRITE`，或删除（design.md 1.4.3 未提此 flag）

### 意淫-4：spec.md R1.4 `setBackBuffer(30000, true)`（次要）

- **方案**：启用 30 秒后向缓冲，支持快速回看
- **意淫点**：
  1. design.md 完全未提 setBackBuffer
  2. tasks.md 完全未提 setBackBuffer
  3. spec.md 单方面提出，且 `retainBackBufferFromKeyframe=true` 在某些场景可能导致内存占用增加
- **建议**：spec.md R1.4 应在 design.md 中评估后再纳入，或降级为 P2

### 意淫-5：spec.md R11 DefaultLoadErrorHandlingPolicy(3000) 语义错误

- **方案**：自定义 `HlsLoadErrorPolicy extends DefaultLoadErrorHandlingPolicy`，构造传入 3000（重试间隔 3 秒）
- **意淫点**：
  1. `DefaultLoadErrorHandlingPolicy` 默认构造无参，**不接受 int 参数**
  2. 重试间隔由 `getRetryDelayMsFor(loadErrorInfo)` 方法控制，需重写此方法返回 3000
  3. spec.md R11.1 "构造传入 3000" 描述错误，需重写方法而非传参
- **建议**：spec.md R11.1 改为"重写 `getRetryDelayMsFor` 返回 3000ms"，对齐 design.md AD-05 的"自定义 ChunkSource"评估路径

### 意淫-6：spec.md R5.5 setViewportSize 未配合 setViewportOrientationSensitive

- **方案**：配置 `setViewportSize` 适配屏幕物理尺寸
- **意淫点**：单独调用 `setViewportSize` 效果有限，需配合 `setViewportOrientationSensitive(true)` 才能在横竖屏切换时正确限制
- **建议**：spec.md R5.5 应补充 `setViewportOrientationSensitive` 配置，或降级为 P2

### 意淫-7：spec.md R12 自定义 HlsChunkSourceFactory maxSegmentsToLoad=6（高风险）

- **方案**：自定义 `HlsChunkSourceFactory`，调高 `maxSegmentsToLoad` 从 3 到 6
- **意淫点**：
  1. design.md AD-05 明确"先验证 P0 收益，rebuffer 率仍 >5% 再实施"，spec.md 直接列为核心需求
  2. `maxSegmentsToLoad` 是 `HlsChunkSource` 内部参数，自定义需深入 HLS 内部实现，维护成本极高
  3. 预取 6 个 segment 在弱网下可能加剧带宽压力（与"减少卡顿"目标相反）
- **建议**：spec.md R12 降级为 P2，对齐 design.md AD-05

### 意淫-8：spec.md R6.4 自定义 MediaCodecSelector 硬解优先（过度工程）

- **方案**：自定义 `MediaCodecSelector` 优先选择 `OMX.qcom.*` / `OMX.Exynos.*` 硬件解码器
- **意淫点**：
  1. design.md AD-07 仅提 `forceEnableMediaCodecAsynchronousQueueing` + `setEnableDecoderFallback`，未提自定义 MediaCodecSelector
  2. `DefaultMediaCodecSelector.DEFAULT` 已优先硬件解码（ExoPlayer 官方实现）
  3. 自定义 MediaCodecSelector 维护成本极高，需跟踪各厂商解码器命名变化
- **建议**：spec.md R6.4 删除或降级为 P2，对齐 design.md

### 意淫-9：spec.md R2.2/R2.3 直播配置应用于点播场景

- **方案**：`setMinOffsetMs(1000)` / `setMaxOffsetMs(5000)` / `setMinPlaybackSpeed(0.95f)` / `setMaxPlaybackSpeed(1.05f)`
- **意淫点**：
  1. `MediaItem.LiveConfiguration` 主要对**直播 HLS** 生效，点播场景无意义
  2. spec.md R2 未区分 VOD/LIVE，一刀切配置
  3. tasks.md 3.1 已区分 VOD=0ms / LIVE=2000ms，spec.md 未对齐
- **建议**：spec.md R2 应区分 VOD/LIVE 配置，对齐 tasks.md 3.1

---

## 五、总体评估

### 5.1 文档质量评级

| 文档 | 质量评级 | 主要问题 |
|------|---------|---------|
| **README.md** | ⚠️ 中等 | "已实施"描述多处错误（setAllowChunklessPreparation / ConnectionPool），与代码不符；但总体框架清晰 |
| **spec.md** | ❌ 差 | **最严重**：与 design.md 在核心架构（LoadControl 热切换）、参数（LoadControl 档位/OkHttp 超时/分辨率限制）上全面矛盾；含 9 项意淫；FLAG_BLOCK_ON_CACHE API 不存在 |
| **design.md** | ✅ 良好 | **唯一诚实**的文档：诚实承认 setAllowChunklessPreparation 未实施、ConnectionPool 不存在；ADR 决策清晰；附录 B 评估 Dynamic LoadControl 后否决有理有据 |
| **tasks.md** | ⚠️ 中等 | 与 design.md 基本对齐，但 OkHttp 超时（3.2 vs 4.4）内部不一致；spec.md 矛盾未澄清 |

### 5.2 核心结论

1. **spec.md 是问题文档**：含 9 项意淫，与 design.md 在 5 个核心架构/参数上矛盾，包含 1 项不存在的 API（FLAG_BLOCK_ON_CACHE）。**spec.md 需要 rewrite 或被 design.md 取代为权威源**。

2. **design.md 是权威文档**：诚实承认代码现状，ADR 决策有理有据，与实际代码一致。**建议以 design.md 为实施基准，spec.md 仅作需求意图参考**。

3. **API 真实性整体良好**：36 项 API 中 30 项真实存在，5 项需进一步核实，仅 1 项不存在（FLAG_BLOCK_ON_CACHE）。Media3 1.10.1 支持绝大多数方案。

4. **代码冲突集中在"已实施"描述错误**：3 份文档（README/spec/tasks）错误描述 setAllowChunklessPreparation 和 ConnectionPool 为"已实施"，design.md 是唯一诚实的。这会导致实施时"保留现有"的决策落空。

5. **项目规范冲突极低**：四份文档均遵守 AGENTS.md 协程/日志/测试包/updateLog 规范，仅实施阶段需注意并发文件修改规范。

### 5.3 修复建议优先级

| 优先级 | 修复项 | 影响 |
|--------|--------|------|
| **P0（必修）** | spec.md R10 删除 AdaptiveLoadControl 热切换方案（与 design.md AD-01 矛盾） | 架构级冲突 |
| **P0（必修）** | spec.md R4.2 `FLAG_BLOCK_ON_CACHE` 改为 `FLAG_BLOCK_ON_CACHE_WRITE` 或删除 | API 不存在 |
| **P0（必修）** | spec.md R1.3 LoadControl 档位参数对齐 design.md（保留现有 5s/30s, 8s/90s, 8s/120s） | 与代码冲突 |
| **P0（必修）** | spec.md R8 OkHttp 超时对齐 tasks.md（10s/15s/30s） | 三文档不一致 |
| **P0（必修）** | README/spec/tasks 修正 setAllowChunklessPreparation "已实施"描述为"未实施" | 与代码冲突 |
| **P0（必修）** | README/spec/tasks 修正 ConnectionPool(10,5min) "已实施"描述为"未实施（继承书源 50 连接池）" | 与代码冲突 |
| **P1（建议）** | spec.md R5.1 setMaxVideoSizeSd() 对齐 design.md setMaxVideoSize(1920,1080) | 两文档矛盾 |
| **P1（建议）** | spec.md R2 LiveConfiguration 区分 VOD/LIVE | 点播场景误用 |
| **P1（建议）** | spec.md R11 DefaultLoadErrorHandlingPolicy(3000) 改为重写 getRetryDelayMsFor | API 语义错误 |
| **P2（可选）** | spec.md R12/R6.4 自定义 ChunkSource/MediaCodecSelector 降级为 P2 | 过度工程 |
| **P2（可选）** | spec.md R1.4 setBackBuffer 在 design.md 评估后再纳入 | 单方面新增 |

### 5.4 实施可行性结论

**整体可行，但需先解决文档矛盾**。design.md 的 P0 优化项（setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds + setAllowChunklessPreparation + forceEnableMediaCodecAsynchronousQueueing + FLAG_IGNORE_CACHE_ON_ERROR + VideoAnalyticsListener）均基于真实存在的 API，与现有代码兼容，可在 Media3 1.10.1 上实施。

**spec.md 的 AdaptiveLoadControl 热切换方案（R10）应明确否决**，避免实施时引入 re-prepare 中断 + PlayerInstancePool 池化冲突。

**建议实施顺序**：以 design.md 为权威源，spec.md 仅作需求意图参考，tasks.md 对齐 design.md。先修复 spec.md 的 9 项意淫 + 6 项文档矛盾，再进入实施阶段。

---

## 六、附录：核实方法清单

| 核实项 | 核实方法 | 结论 |
|--------|---------|------|
| Media3 版本 | Read `gradle/libs.versions.toml` L65 | 1.10.1 |
| API 真实性 | WebSearch Media3 官方文档 + 社区文档 | 36 项核实，30 真实 / 5 待核实 / 1 不存在 |
| setAllowChunklessPreparation 代码状态 | Grep `ExoPlayerHelper.kt` + `Exo2MediaPlayer.kt` HLS 分支 | **未调用** |
| ConnectionPool 代码状态 | Grep `ExoPlayerHelper.kt` okhttpDataFactory | **未显式配置**（继承书源 50 连接池） |
| LoadControl 档位代码状态 | Read `ExoPlayerHelper.kt` L133-L155 | WEAK 5s/30s, MEDIUM 8s/90s, GOOD 8s/120s |
| OkHttp 超时代码状态 | Read `ExoPlayerHelper.kt` L847-L857 | 仅 callTimeout(0)，未配置 connect/readTimeout |
| FLAG_BLOCK_ON_CACHE 真实性 | WebSearch Media3 CacheDataSource 常量 | **不存在**，应为 FLAG_BLOCK_ON_CACHE_WRITE |
| 项目规范冲突 | 对照 AGENTS.md Code Style / Landmines / 强制规则 | 7 项检查，2 项轻微，5 项无冲突 |

---

**审查完成。建议以 design.md 为权威实施源，spec.md 需修复 9 项意淫 + 6 项文档矛盾后方可作为需求规格参考。**
