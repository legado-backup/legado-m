# 视频播放失败修复 - 任务清单

> **创建时间**：2026-07-26 18:02
> **V2修订**：2026-07-26 18:50（基于源码深度分析，修正8项V1任务+新增13项任务，共38项）
> **实施状态更新**：2026-07-26 23:30（Phase 1 + Phase 2 代码改造全部完成，待编译验证+真机测试）
> **状态**：Phase 1+2 已完成，Phase 3-5 待执行
> **执行顺序**：Phase 1（P0 改造）→ Phase 2（P1 改造）→ Phase 3（编译+L1 验证）→ Phase 4（L2 真机验证）→ Phase 5（文档同步+验收）

---

## §0 实施状态汇总（2026-07-26 23:30）

### 已完成任务（27项）

**Phase 1 P0 改造（14项全部完成）**：
- ✅ T1.1 R5 delayTime 默认值 3000ms→1000ms
- ✅ T1.2 R5 timeout 默认值 10000ms→6000ms
- ✅ T1.10 抽取 R5_DELAY_TIME/R5_TIMEOUT 常量+修改3处硬编码调用
- ✅ T1.11 第一层 MacCMS 解析 6 秒超时控制（withTimeoutOrNull）
- ✅ T1.14 extractVideoUrlForEpisode 12 秒总超时（withTimeoutOrNull）
- ✅ T1.3 SNIFF_TIMEOUT_MS 3000ms→5000ms
- ✅ T1.4 sniffWithRangeRequestR4 检查 isActive（含 import 补全）
- ✅ T1.5 按嗅探结果排序降级链（buildFallbackTypes 重构）
- ✅ T1.6 onPlayerError 用 AppLog.put 替代 Log.d
- ✅ T1.7 新增 onPlaybackStateChanged 日志
- ✅ T1.8 releaseSniffResources() + isReleased 标志位 + VideoFragment.onDestroyView 调用
- ✅ T1.9 applyMediaSourceByType 内部检查 isActive + isReleased
- ✅ T1.12 prepareAsyncInternal 状态变量重置
- ✅ T1.13 mInternalPlayer 显式 release 旧实例 + VideoPlay 状态快照（方案B）

**Phase 2 P1 改造（13项全部完成）**：
- ✅ T2.1 prepareAsyncInternal 重复初始化检测（prepareAsyncCallCount + lastPrepareUrl/headers）
- ✅ T2.2 prepareAsyncInternal 调用日志（callCount）
- ✅ T2.3 BUFFERING 12 秒超时触发 tryNextFallback（bufferingTimeoutHandler）
- ✅ T2.4 嗅探协程生命周期日志（started/cancelled/completed）
- ✅ T2.5 VideoUrlExtractor 各阶段耗时日志（putInfo 级别）
- ✅ T2.6 readLimitedBytes 循环 isActive 检查（suspend 函数改造）
- ✅ T2.7 isParsingError 独立判断
- ✅ T2.8 onPause 取消 initSource 协程（initSourceJob）
- ✅ T2.9 第三层失败返回 null（不返回非视频流URL）
- ✅ T2.10 VideoPlay 兜底返回 null（触发 WebView 降级）
- ✅ T2.11 CancellationException 守卫（重新抛出）
- ✅ T2.12 onStop 暂停视频播放（deactivatePlayer）
- ✅ T2.13 sniffVideoType 复用 MimeSnifferCache 缓存

### 待执行任务（11项）

**Phase 3 编译验证 + L1 验证（2项）**：
- ✅ T3.1 编译测试包（assembleDebug）BUILD SUCCESSFUL in 57s（2026-07-26 22:30）
- ⏳ T3.2 L1 验证（基础功能）

**Phase 4 L2 真机测试（7项）**：
- ⏳ T4.1-T4.7 真机测试（待 Phase 3 通过后执行）

**Phase 5 文档同步 + 验收（2项）**：
- ✅ T5.1 更新 assets/updateLog.md（2026/07/26 完整条目已添加，含视频嗅探/降级链/协程取消等）
- ✅ T5.2 同步 docs/INDEX.md（video-playback-failure-fix-20260726 状态已更新）
- ⏳ T5.3 AskUserQuestion 验收

### Phase 6 真机测试日志分析修复（2026-07-26 新增）

**用户反馈背景**：
- 用户 2026-07-26 22:30 真机测试后反馈："视频播放有所提升，但是出现过应用崩溃一次，并且之前好使的多线路多集播放现在好多都直接走兜底webview播放器了，但是其实webview播放器也是播放失败的"
- 日志文件：temp/logs/Downloadslogs(2).(1)..zip（解压到 extracted_r4_test/）

**Bug-fix-1 ImageGalleryActivity Glide 销毁崩溃**：
- 现象：crash-2026-07-26-21-52-34.log 显示 `IllegalArgumentException: You cannot start a load for a destroyed activity`
- 根因：ImageGalleryActivity.kt L256/L259 onScrollStateChanged 回调在 Activity 销毁过程中（onDetachedFromWindow→stopScroll→onScrollStateChanged）被触发，此时调用 Glide.with(activity) 抛异常
- 修复：增加 `if (isDestroyed || isFinishing) return` 守卫，销毁过程中跳过 Glide 调用
- 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

**Bug-fix-2 VideoUrlExtractor 缺少 .m3u8 快速路径导致回归**：
- 现象：logcat 显示 11 次 .m3u8 URL 走完整 12 秒超时返回 null 触发 WebView 降级（WebView 也不支持 HLS 播放同样失败）
- 关键日志（脱敏）：`extractVideoUrlForEpisode timeout (12s), 返回null, path=/20260726/qClStzb4/index.m3u8` → `extractVideoUrlForEpisode 返回null, 触发WebView降级`
- 根因：R4 T2.9 改造加入"超时返回 null"逻辑，但 extractVideoUrlForEpisode 入口未补充"URL已是视频流"快速路径判断，导致已解析出的 .m3u8/.mpd/.mp4 等视频流 URL 走完整三层解析（MacCMS+DOM+WebView 抓包）
- 回归证据：用户反馈"之前好使的多线路多集播放现在好多都直接走兜底webview播放器了"
- 修复：入口新增 `isDirectVideoStreamUrl(url)` 判断，识别 .m3u8/.mpd/.mp4/.flv/.mkv/.webm 后缀直接返回 URL，跳过三层解析秒级交给 ExoPlayer 播放
- 文件：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`

**Phase 6 编译验证**：
- ✅ T6.1 assembleDebug --rerun-tasks BUILD SUCCESSFUL in 4m 13s（77 tasks executed，2026-07-26 22:30+）

### 实施决策调整

**R4-T10 CustomHlsKeyManager 不可行（最终决策：删除文件）**：
- 原设计：新建 CustomHlsKeyManager.kt 实现 HlsKeyManager 接口
- 实施时发现：media3 1.10.1 中 HlsKeyManager 接口不存在（编译报错 Unresolved reference 'HlsKeyManager'），HlsMediaSource.Factory 也无公开 setKeyManager 方法
- 实际实施：通过 setDefaultHeaders 注入防盗链头到 okhttpDataFactory，ExoPlayer 内部自动用此 factory 获取密钥
- 2026-07-26 最终决策：删除 CustomHlsKeyManager.kt 文件（HlsKeyManager 接口不存在，文件无法编译）
- 详见：[R4-enhancement-plan.md §2.3.8](../../player-review-and-optimization/R4-enhancement-plan.md)

---

## §1 任务总览

| 阶段 | 任务数 | 优先级 | 描述 |
|------|--------|--------|------|
| Phase 1 | 14 | P0 | 核心代码改造（必须修复，原9项+新增5项） |
| Phase 2 | 13 | P1 | 增强改造（重要修复，原5项+新增8项） |
| Phase 3 | 2 | — | 编译验证 + L1 验证 |
| Phase 4 | 6 | — | L2 真机测试（5类源+8实例快速切换） |
| Phase 5 | 3 | — | 文档同步 + 验收 |
| **总计** | **38** | — | — |

### 1.1 V2修订说明

- **修正V1任务（8项）**：T1.1/T1.2（抽取常量+修改3处硬编码）/ T1.4（readLimitedBytes循环+import）/ T1.5（重构为按嗅探结果排序降级链）/ T1.8（改造点2移至VideoFragment.onDestroyView+isReleased标志位）/ T1.9（applyMediaSourceByType内部检查isActive）/ T2.1（重构为同一URL+headers才跳过）/ T2.3（BUFFERING超时5秒→12秒）/ T2.5（统一putInfo级别）
- **新增任务（13项）**：T1.10~T1.14（P0级5项）+ T2.6~T2.13（P1级8项）
- **Bug覆盖**：27个Bug（修正4个根因+新增17个）

---

## §2 Phase 1：P0 核心改造（必须修复，14项）

### 2.1 VideoUrlExtractor.kt 改造

#### T1.1：R5 delayTime 默认值从 3000ms 降至 1000ms（V2修正）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L178
- [ ] **改造点**（V2修正）：将 `delayTime = 3000L` 改为 `delayTime = 1000L`（基础默认值修改，配合 T1.10 抽取常量统一管理）
- [ ] **解决 Bug**：Bug-1
- [ ] **验收**：编译通过 + 日志中 `delayTime=1000` 出现
- [ ] **V2说明**：V1仅改默认值无效，必须配合 T1.10 修改3处硬编码调用

#### T1.2：R5 timeout 默认值从 10000ms 降至 6000ms（V2修正）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`
- [ ] **改造点**（V2修正）：将 `timeout = 10000L` 改为 `timeout = 6000L`（基础默认值修改，配合 T1.10 抽取常量统一管理）
- [ ] **解决 Bug**：Bug-1
- [ ] **验收**：编译通过 + 日志中 `timeout=6000` 出现
- [ ] **V2说明**：V1仅改默认值无效，必须配合 T1.10 修改3处硬编码调用

#### T1.10：抽取 R5_DELAY_TIME/R5_TIMEOUT 常量，修改3处硬编码调用（V2新增）

- [ ] **文件**：
  1. `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`（companion object 抽取常量 + L489 修改硬编码）
  2. `app/src/main/java/io/legado/app/ui/book/VideoPlay.kt` L316（修改硬编码）
  3. `app/src/main/java/io/legado/app/ui/book/VideoPlay.kt` L427（修改硬编码）
- [ ] **改造点**：
  1. 在 VideoUrlExtractor.kt companion object 抽取常量 `const val R5_DELAY_TIME = 1000L` / `const val R5_TIMEOUT = 6000L`
  2. 修改 VideoUrlExtractor.kt L489 硬编码 `delayTime = 3000L` / `timeout = 10000L` → 引用 `R5_DELAY_TIME` / `R5_TIMEOUT`
  3. 修改 VideoPlay.kt L316 硬编码 → 引用 `VideoUrlExtractor.R5_DELAY_TIME` / `VideoUrlExtractor.R5_TIMEOUT`
  4. 修改 VideoPlay.kt L427 硬编码 → 引用 `VideoUrlExtractor.R5_DELAY_TIME` / `VideoUrlExtractor.R5_TIMEOUT`
- [ ] **解决 Bug**：Bug-11（V2新增）
- [ ] **验收**：编译通过 + 3处调用统一引用常量 + grep 搜索 `delayTime = 3000L` / `timeout = 10000L` 在3个文件中无残留
- [ ] **依赖**：T1.1, T1.2（先改默认值，再统一抽取常量）

#### T1.11：第一层 MacCMS 解析超时控制（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L468
- [ ] **改造点**：用 `withTimeout(6000L) { analyzeUrl.getStrResponseAwait() }` 包裹第一层 MacCMS 解析
  ```kotlin
  // 改造前
  val response = analyzeUrl.getStrResponseAwait()
  // 改造后
  val response = withTimeout(6000L) { analyzeUrl.getStrResponseAwait() }
  ```
- [ ] **解决 Bug**：Bug-12（V2新增）+ Bug-1（真正主因）
- [ ] **验收**：第一层 MacCMS 解析超时 6 秒触发，不再卡死 60 秒 + AppLog 中出现 `MacCMS parse timeout (6s)` 日志

#### T1.14：extractVideoUrlForEpisode 总超时（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L450-500
- [ ] **改造点**：为整个 `extractVideoUrlForEpisode` 添加总超时 `withTimeout(12000L)`
  ```kotlin
  suspend fun extractVideoUrlForEpisode(...): String? = withTimeout(12000L) {
      // 原三层串行逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-15（V2新增）
- [ ] **验收**：总超时 12 秒触发，不再累计 70 秒 + AppLog 中出现 `extractVideoUrlForEpisode timeout (12s)` 日志

### 2.2 ExoPlayerHelper.kt 改造

#### T1.3：SNIFF_TIMEOUT_MS 从 3000ms 提升至 5000ms（保持）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` L515
- [ ] **改造点**：`private const val SNIFF_TIMEOUT_MS = 3000L` → `private const val SNIFF_TIMEOUT_MS = 5000L`
- [ ] **解决 Bug**：Bug-3
- [ ] **验收**：编译通过 + 嗅探超时与成功时差 > 1000ms
- [ ] **V2说明**：注意 sniffMimeType（L379）也共用此常量

#### T1.4：sniffWithRangeRequestR4 检查 isActive（V2补充）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`
- [ ] **改造点**（V2补充）：
  1. 在 `okHttpClient.newCall(request).execute().use { response ->` 内部添加 `if (!kotlin.coroutines.coroutineContext.isActive) { return@use SniffResult.UNKNOWN }`
  2. **V2补充**：在 readLimitedBytes 循环中也添加 isActive 检查（详见 T2.6）
  3. **V2补充**：在文件顶部添加 `import kotlin.coroutines.coroutineContext` 和 `import kotlinx.coroutines.isActive`
- [ ] **解决 Bug**：Bug-3（协程取消不响应）
- [ ] **验收**：编译通过 + onDestroy 后 0 个 sniffVideoType success 日志
- [ ] **V2说明**：execute() 本身无法中断，isActive 检查只能在其返回后生效

### 2.3 Exo2MediaPlayer.kt 改造

#### T1.5：按嗅探结果排序降级链（V2重构）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**（V2重构，废弃 MutableStateFlow 方案）：
  1. 废弃 V1 的 `MutableStateFlow` 方案（过度设计，未解决核心问题）
  2. 修改 `buildFallbackTypes` 按嗅探结果排序：
     ```kotlin
     private fun buildFallbackTypes(sniffResult: SniffResult): List<Int> {
         return when (sniffResult.contentType) {
             4 -> listOf(CT_PROGRESSIVE, CT_HLS, CT_DASH)   // MP4直链优先 Progressive
             2 -> listOf(CT_HLS, CT_PROGRESSIVE, CT_DASH)   // HLS 优先
             else -> listOf(CT_HLS, CT_DASH, CT_PROGRESSIVE) // UNKNOWN 保持原逻辑
         }
     }
     ```
  3. `applyMediaSourceByType` 使用排序后的降级链
- [ ] **解决 Bug**：Bug-7（V2根因修正：降级链默认HLS优先与MP4直链不匹配）
- [ ] **验收**：编译通过 + 案例 3 类似场景（MP4直链）降级链走 ProgressiveMediaSource
- [ ] **V2说明**：V1的MutableStateFlow方案废弃，真正问题是降级链默认HLS优先

#### T1.6：onPlayerError 用 AppLog.put 替代 Log.d（保持）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L577
- [ ] **改造点**：
  ```kotlin
  // 改造前
  Log.d("ExoPlayer", "onPlayerError: errorCode=${error.errorCode}, ...")
  // 改造后
  AppLog.put(
      "ExoPlayer onPlayerError: errorCode=${error.errorCode}(${error.errorCodeName}), " +
      "cause=${error.cause?.javaClass?.simpleName}: ${error.cause?.message}, " +
      "urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}",
      error
  )
  ```
- [ ] **解决 Bug**：Bug-4
- [ ] **验收**：AppLog 文件中能看到 `ExoPlayer onPlayerError` 日志

#### T1.7：新增 onPlaybackStateChanged 日志（保持）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**：新增 `onPlaybackStateChanged` override，输出 IDLE/BUFFERING/READY/ENDED 状态
- [ ] **解决 Bug**：Bug-4（增强）
- [ ] **验收**：AppLog 文件中能看到 `ExoPlayer state: BUFFERING→READY` 日志

#### T1.8：新增 release() 方法 + VideoFragment.onDestroyView 调用（V2修正）

- [ ] **文件 1**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点 1**：
  ```kotlin
  private var isReleased = false  // V2新增标志位

  fun release() {
      currentSniffJob?.cancel()
      scope.cancel()
      isReleased = true  // V2新增
      AppLog.put("ExoPlayer scope cancelled, isReleased=true")
  }
  ```
- [ ] **文件 2**：`app/src/main/java/io/legado/app/ui/book/VideoFragment.kt`（V2修正：从 VideoPlayerActivity.onDestroy 改为 VideoFragment.onDestroyView）
- [ ] **改造点 2**（V2修正位置）：在 `VideoFragment.onDestroyView` 中调用 `(currentPlayer as? Exo2MediaPlayer)?.release()`
- [ ] **增强点**（V2新增）：在 `applyMediaSourceByType` 入口检查 `if (isReleased) return`，解决 `scope.cancel` 无法中断非 suspend 函数的问题
- [ ] **解决 Bug**：Bug-5 + Bug-23（V2新增）+ Bug-27（V2新增）
- [ ] **验收**：onDestroy 后 0 个 sniffVideoType 日志 + 0 个 ExoFallback 日志 + applyMediaSourceByType 响应 isReleased 标志位 + 无 JobCancellationException 异常泄漏
- [ ] **V2说明**：VideoPlayerActivity 不直接持有 exo2MediaPlayer 引用，必须在 VideoFragment.onDestroyView 中调用

#### T1.9：嗅探协程 + applyMediaSourceByType 内部检查 isActive（V2补充）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**（V2补充）：
  1. 在 `currentSniffJob = scope.launch { ... }` 内部，sniffVideoType 返回后检查 `if (!isActive) { return@launch }`（L363 已存在）
  2. **V2补充**：在 `applyMediaSourceByType` 内部也检查 `if (!scope.isActive) { return }`，配合 isReleased 标志位
- [ ] **解决 Bug**：Bug-5（增强）
- [ ] **验收**：AppLog 中出现 `ExoFallback: sniff job cancelled` 日志（如 Activity 销毁时嗅探未完成）

#### T1.12：状态变量重置（V2新增，依赖 T1.5）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` `prepareAsyncInternal`
- [ ] **改造点**：在 `prepareAsyncInternal` 入口重置所有状态变量
  ```kotlin
  override fun prepareAsyncInternal() {
      // V2新增：重置状态变量
      currentSniffResult = SniffResult.UNKNOWN
      fallbackTypes = buildFallbackTypes(currentSniffResult)  // 依赖 T1.5 重构后的方法
      currentFallbackIndex = 0
      // ... 原逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-13（V2新增）
- [ ] **验收**：切换视频时状态变量被重置 + AppLog 中出现 `ExoPlayer state reset: currentSniffResult=UNKNOWN` 日志
- [ ] **依赖**：T1.5（状态变量重置基于降级链重构）

#### T1.13：mInternalPlayer 显式 release 旧实例 + VideoPlay 单例改造（V2新增）

- [ ] **文件 1**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` `prepareAsyncInternal`
- [ ] **改造点 1**：创建新 `mInternalPlayer` 实例前显式 release 旧实例
  ```kotlin
  override fun prepareAsyncInternal() {
      // V2新增：显式 release 旧实例
      mInternalPlayer?.release()
      mInternalPlayer = createNewPlayer()
      // ... 原逻辑
  }
  ```
- [ ] **文件 2**：`app/src/main/java/io/legado/app/ui/book/VideoPlay.kt` L62
- [ ] **改造点 2**：将 VideoPlay 状态改为 per-Activity 实例，或在 `onActivityCreated` 中保存状态快照
  ```kotlin
  // V2改造方案（择一）：
  // 方案A：将 object VideoPlay 改为 class，每个 Activity 持有独立实例
  // 方案B：在 onActivityCreated 中保存状态快照到 Activity 字段
  ```
- [ ] **解决 Bug**：Bug-14（V2新增）+ Bug-24（V2新增）+ Bug-6（核心根因）
- [ ] **验收**：旧 mInternalPlayer 实例被显式 release + 8个Activity实例快速切换时状态不被覆盖 + AppLog 中出现 `mInternalPlayer released old instance` 日志
- [ ] **风险**：VideoPlay 单例改造影响其他模块，需先搜索 VideoPlay 的所有调用点评估影响范围

---

## §3 Phase 2：P1 增强改造（重要修复，13项）

### 3.1 Exo2MediaPlayer.kt 增强

#### T2.1：prepareAsyncInternal 重复初始化检测（V2重构）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**（V2重构，废弃"1秒内防重"方案）：
  ```kotlin
  private var prepareAsyncCallCount = 0
  private var lastPrepareUrl: String? = null
  private var lastPrepareHeaders: Map<String, String>? = null

  override fun prepareAsyncInternal() {
      val now = System.currentTimeMillis()
      prepareAsyncCallCount++
      AppLog.put("ExoPlayer prepareAsyncInternal: callCount=$prepareAsyncCallCount, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")

      // V2重构：同一URL+headers才跳过，避免误伤合法场景（如用户快速切集）
      if (currentUrl == lastPrepareUrl && currentHeaders == lastPrepareHeaders
          && currentSniffJob?.isActive == true) {
          AppLog.put("ExoPlayer prepareAsyncInternal: skip duplicate call (same url+headers), ...")
          return
      }
      lastPrepareUrl = currentUrl
      lastPrepareHeaders = currentHeaders
      // ... 原逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-2
- [ ] **验收**：重复 Init 场景下嗅探协程只启动 1 次 + 用户快速切集不被误伤
- [ ] **V2说明**：V1的"1秒内防重"会误伤合法场景，改为"同一URL+headers才跳过"

#### T2.2：新增 prepareAsyncInternal 调用日志（保持）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**：在 `prepareAsyncInternal` 入口输出 `callCount` 日志
- [ ] **解决 Bug**：Bug-2（增强）
- [ ] **验收**：AppLog 中出现 `ExoPlayer prepareAsyncInternal: callCount=N` 日志

#### T2.3：新增 BUFFERING 超时 12 秒触发 tryNextFallback（V2修正）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**（V2修正：从 5 秒改为 12 秒）：
  ```kotlin
  private val bufferingTimeoutHandler = Handler(Looper.getMainLooper())
  private val bufferingTimeoutRunnable = Runnable {
      AppLog.put("ExoPlayer BUFFERING timeout (12s), trigger fallback, ...")  // V2修正：5s → 12s
      tryNextFallback()
  }

  override fun onPlaybackStateChanged(state: Int) {
      super.onPlaybackStateChanged(state)
      // ... 日志输出
      when (state) {
          Player.STATE_BUFFERING -> bufferingTimeoutHandler.postDelayed(bufferingTimeoutRunnable, 12000L)  // V2修正：5000L → 12000L
          Player.STATE_READY -> bufferingTimeoutHandler.removeCallbacks(bufferingTimeoutRunnable)
      }
  }
  ```
- [ ] **解决 Bug**：Bug-8 + Bug-9
- [ ] **验收**：BUFFERING 超 12 秒后自动尝试下一个 MediaSource + ExoFallback 推进到 #2/3+
- [ ] **V2说明**：5 秒太短，弱网误降级，改为 12 秒

#### T2.4：新增嗅探协程生命周期日志（保持）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
- [ ] **改造点**：在 `currentSniffJob = scope.launch { ... }` 中输出 started/cancelled/completed 日志
- [ ] **解决 Bug**：Bug-5（增强）
- [ ] **验收**：AppLog 中出现 `ExoFallback: sniff job started` / `sniff job cancelled` / `sniff job completed` 日志

#### T2.7：isParsingError 独立判断（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L532
- [ ] **改造点**：将 `isParsingError` 独立判断，或在 `isUnrecoverableError` 中补充 `UnrecognizedInputFormatException` 的 errorCode
  ```kotlin
  // V2改造方案（择一）：
  // 方案A：将 isParsingError 独立判断
  if (isParsingError(error)) {
      AppLog.put("ExoPlayer isParsingError, trigger fallback, ...")
      tryNextFallback()
      return
  }
  if (isUnrecoverableError(error)) { ... }

  // 方案B：在 isUnrecoverableError 中补充 errorCode
  private fun isUnrecoverableError(error: ExoPlaybackException): Boolean {
      // V2新增：补充 UnrecognizedInputFormatException 的 errorCode
      if (error.type == ExoPlaybackException.TYPE_SOURCE
          && error.cause is UnrecognizedInputFormatException) return false
      // ... 原逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-8（补充）+ Bug-22（V2新增）
- [ ] **验收**：UnrecognizedInputFormatException 触发降级链 + ExoFallback 能从 #1/3 推进到 #2/3、#3/3

### 3.2 VideoUrlExtractor.kt 增强

#### T2.5：新增 VideoUrlExtractor 各阶段耗时日志（V2补充）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`
- [ ] **改造点**（V2补充：统一为 putInfo 级别）：在 `extractPrecise` / R5 静态解析 / R5 网络抓包 各阶段添加 start/end 日志（含耗时），统一为 `putInfo` 级别确保 release 包可见
- [ ] **解决 Bug**：Bug-6（便于定位）
- [ ] **验收**：AppLog 中出现 `VideoUrlExtractor: extractPrecise start/end` / `R5 static parse start/end` / `R5 network sniff start/end` 日志
- [ ] **V2说明**：统一为 putInfo 级别，确保 release 包可见

#### T2.9：第三层失败返回 null（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L494/L498
- [ ] **改造点**：第三层失败时返回 null，不返回 `resolvedUrl`（可能是非视频流URL）
  ```kotlin
  // 改造前（L494）
  } else { resolvedUrl }
  // 改造后
  } else { null }

  // 改造前（L498）
  resolvedUrl
  // 改造后
  null
  ```
- [ ] **解决 Bug**：Bug-16（V2新增）
- [ ] **验收**：第三层失败时不返回非视频流URL + ExoPlayer 不再加载非视频流URL触发 UnrecognizedInputFormatException

#### T2.10：VideoPlay.kt L436 兜底返回 null（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/ui/book/VideoPlay.kt` L436
- [ ] **改造点**：兜底返回 null 或抛出异常，不返回 `rssArticle.link`（肯定非视频流URL）
  ```kotlin
  // 改造前
  rssArticle.link
  // 改造后
  null
  ```
- [ ] **解决 Bug**：Bug-19（V2新增）
- [ ] **验收**：P3-1 降级嗅探失败时返回 null + ExoPlayer 不再加载非视频流URL

#### T2.11：CancellationException 守卫（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L483 + L496
- [ ] **改造点**：在第一层和第三层 catch 守卫 CancellationException
  ```kotlin
  // 改造前
  } catch (e: Exception) { ... }
  // 改造后
  } catch (e: kotlinx.coroutines.CancellationException) {
      throw e  // V2新增：协程取消必须传播
  } catch (e: Exception) { ... }
  ```
- [ ] **解决 Bug**：Bug-17（V2新增）+ Bug-18（V2新增）
- [ ] **验收**：协程取消被正确传播，不被吞掉 + 退出播放器时嗅探任务被及时取消

### 3.3 ExoPlayerHelper.kt 增强

#### T2.6：readLimitedBytes 循环 isActive 检查（V2新增，依赖 T1.4）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` `sniffWithRangeRequestR4` L470-480
- [ ] **改造点**：在 `readLimitedBytes` 读取循环中添加 isActive 检查
  ```kotlin
  while (inputStream.read(buffer).also { bytesRead = it } != -1) {
      // V2新增：循环内检查 isActive
      if (!kotlin.coroutines.coroutineContext.isActive) {
          AppLog.put("sniffWithRangeRequestR4 cancelled in readLoop")
          break
      }
      // ... 原读取逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-21（V2新增）
- [ ] **验收**：readLimitedBytes 循环响应协程取消 + 协程取消后立即停止读取
- [ ] **依赖**：T1.4（isActive 检查基础设施）

#### T2.13：sniffVideoType 复用缓存（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` L151 `sniffVideoType`
- [ ] **改造点**：`sniffVideoType` 调用 `sniffMimeType` 获取缓存结果，避免重复嗅探
  ```kotlin
  suspend fun sniffVideoType(...): SniffResult {
      // V2新增：先查 MimeSnifferCache 缓存
      val cached = MimeSnifferCache.get(url)
      if (cached != null) {
          return mapMimeTypeToSniffResult(cached)
      }
      // 原嗅探逻辑
  }
  ```
- [ ] **解决 Bug**：Bug-20（V2新增）
- [ ] **验收**：同一URL只嗅探一次 + AppLog 中出现 `sniffVideoType cache hit` 日志

### 3.4 VideoPlayerActivity.kt 增强

#### T2.8：onPause 取消 initSource 协程（V2新增，依赖 T1.13）

- [ ] **文件**：`app/src/main/java/io/legado/app/ui/book/VideoPlayerActivity.kt` `onActivityCreated` L217-229
- [ ] **改造点**：
  1. 保存 `initSource` 协程的 Job 引用
  2. 在 `onPause` 中主动取消 `initSource` 协程
  ```kotlin
  private var initSourceJob: Job? = null  // V2新增

  override fun onActivityCreated(...) {
      initSourceJob = lifecycleScope.launch {  // V2修改：保存 Job 引用
          // ... 原 initSource 逻辑
      }
  }

  override fun onPause() {
      super.onPause()
      initSourceJob?.cancel()  // V2新增：onPause 时取消
      AppLog.put("VideoPlayerActivity onPause: initSourceJob cancelled")
  }
  ```
- [ ] **解决 Bug**：Bug-25（V2新增）
- [ ] **验收**：initSource 协程在 onPause 时被取消 + AppLog 中出现 `initSourceJob cancelled` 日志
- [ ] **依赖**：T1.13（VideoPlay 单例改造，确保 onPause 时协程能正确取消）

#### T2.12：onStop 暂停视频播放（V2新增）

- [ ] **文件**：`app/src/main/java/io/legado/app/ui/book/VideoPlayerActivity.kt` `onStop` L1507-1512
- [ ] **改造点**：在 `onStop` 中调用 `currentFragment?.deactivatePlayer()` 或 `VideoPlay.onPause()`
  ```kotlin
  override fun onStop() {
      super.onStop()
      // V2新增：暂停视频播放
      currentFragment?.deactivatePlayer()  // 或 VideoPlay.onPause()
      AppLog.put("VideoPlayerActivity onStop: video paused")
  }
  ```
- [ ] **解决 Bug**：Bug-26（V2新增）
- [ ] **验收**：Activity切到后台时视频暂停 + 返回前台时视频恢复

---

## §4 Phase 3：编译验证 + L1 验证

### T3.1：编译测试包

- [ ] **命令**：`gradlew assembleDebug`
- [ ] **验证**：APK 生成在 `app/build/outputs/apk/debug/app-debug.apk`
- [ ] **修复编译错误**：如有 import 缺失/语法错误，逐项修复
- [ ] **依赖**：Phase 1 + Phase 2 完成

### T3.2：L1 验证（基础功能）

- [ ] **命令**：`adb install -r app/build/outputs/apk/debug/app-debug.apk`
- [ ] **启动应用**：`adb shell am start -n io.legado.miss.app.debug/io.legado.app.ui.MainActivity`
- [ ] **验证无崩溃**：`adb logcat -d | grep -E "FATAL|AndroidRuntime"`
- [ ] **验证 ExoPlayer 初始化正常**：进入视频播放页面，无异常
- [ ] **依赖**：T3.1

---

## §5 Phase 4：L2 真机测试（5 类源 + 8实例快速切换，6项）

### T4.1：MacCMS 模板源测试

- [ ] **测试源**：站点G/H 类型
- [ ] **预期**：视频地址获取 < 3 秒，播放成功
- [ ] **日志验证**：
  - `ExoPlayer prepareAsyncInternal: callCount=1`
  - `ExoPlayer state: BUFFERING→READY`
  - `MacCMS parse start/end`（耗时 < 6 秒）
  - 视频地址获取时间 < 3 秒

### T4.2：DPlayer 播放器源测试

- [ ] **测试源**：站点I 类型
- [ ] **预期**：视频地址获取 < 3 秒，播放成功
- [ ] **日志验证**：
  - `ExoPlayer state: BUFFERING→READY`
  - 视频地址获取时间 < 3 秒

### T4.3：自定义播放页源测试

- [ ] **测试源**：站点J 类型
- [ ] **预期**：视频地址获取 < 3 秒，播放成功
- [ ] **日志验证**：
  - `ExoPlayer state: BUFFERING→READY`
  - 视频地址获取时间 < 3 秒

### T4.4：MP4 直链源测试

- [ ] **测试源**：站点D 类型
- [ ] **预期**：视频地址获取 < 2 秒，播放成功
- [ ] **日志验证**：
  - `sniffVideoType: success, contentType=4 (MP4)`
  - `ExoFallback: try contentType=4 (#1/3)` ← 验证 Bug-7 修复（降级链走 Progressive）
  - `ExoPlayer state: BUFFERING→READY`

### T4.5：加密 HLS 源测试

- [ ] **测试源**：AES-128 类型
- [ ] **预期**：嗅探成功，播放成功
- [ ] **日志验证**：
  - `sniffVideoType: success, contentType=2 (HLS)`
  - `ExoPlayer state: BUFFERING→READY`

### T4.6：8实例快速切换测试（V2新增）

- [ ] **测试场景**：8个Activity实例快速切换（任意类型源）
- [ ] **预期**：状态不串扰，每个实例独立播放
- [ ] **日志验证**：
  - 8个实例的 `ExoPlayer prepareAsyncInternal: callCount=N` 日志独立
  - 8个实例的视频地址获取互不干扰
  - 无 `mInternalPlayer released old instance` 异常日志
  - 无状态污染导致的播放失败

### T4.7：日志收集与验证

- [ ] **收集 AppLog**：
  ```bash
  adb shell run-as io.legado.miss.app.debug cat /data/data/io.legado.miss.app.debug/files/appLog.txt > appLog.txt
  ```
- [ ] **验证点清单**：
  - [ ] `ExoPlayer prepareAsyncInternal: callCount=N` 日志出现
  - [ ] `ExoPlayer state: BUFFERING→READY` 日志出现（播放成功）
  - [ ] `ExoPlayer onPlayerError` 日志出现（如播放失败）
  - [ ] `ExoFallback: sniff job cancelled` 日志出现（如 Activity 销毁）
  - [ ] `ExoFallback: try contentType=N (#M/3)` 推进到 #2/3+
  - [ ] `MacCMS parse timeout (6s)` 日志出现（如第一层超时）
  - [ ] `extractVideoUrlForEpisode timeout (12s)` 日志出现（如总超时）
  - [ ] `ExoPlayer state reset: currentSniffResult=UNKNOWN` 日志出现（切换视频时）
  - [ ] `mInternalPlayer released old instance` 日志出现（重复 Init 时）
  - [ ] `sniffVideoType cache hit` 日志出现（同URL缓存命中）
  - [ ] 0 个幽灵日志（onDestroy 后无 sniffVideoType 日志）
  - [ ] 视频地址获取时间 < 3 秒
  - [ ] 嗅探成功率 ≥ 90%
  - [ ] 8实例快速切换状态不串扰

---

## §6 Phase 5：文档同步 + 验收

### T5.1：更新 assets/updateLog.md

- [ ] **基于 git diff 分析真实代码变更**
- [ ] **三步流程**：代码分析 → 功能提炼 → 面向用户重写
- [ ] **新增条目**：视频播放失败修复（27 个 Bug 修复 + 13 项调试日志增强 + VideoPlay 单例改造）

### T5.2：同步 docs/INDEX.md

- [ ] **新增条目**：`video-playback-failure-fix-20260726`
- [ ] **状态**：实施中 → 已完成

### T5.3：AskUserQuestion 验收

- [ ] **提交四文档审查**
- [ ] **三选项结构**：通过 / 需调整 / 拒绝回退

---

## §7 任务依赖关系

```
Phase 1 (P0 改造, 14项)
  ├─ T1.1, T1.2 (VideoUrlExtractor 默认值) ← 独立
  ├─ T1.10 (抽取常量+修改3处硬编码) ← 依赖 T1.1, T1.2
  ├─ T1.11 (第一层 MacCMS 超时) ← 独立
  ├─ T1.14 (extractVideoUrlForEpisode 总超时) ← 独立
  ├─ T1.3, T1.4 (ExoPlayerHelper) ← 独立
  ├─ T1.5 (按嗅探结果排序降级链) ← 独立（Exo2MediaPlayer 改造起点）
  ├─ T1.6, T1.7 (Exo2MediaPlayer 日志) ← 独立
  ├─ T1.8 (release() + isReleased) ← 独立
  ├─ T1.9 (applyMediaSourceByType 检查 isActive) ← 独立
  ├─ T1.12 (状态变量重置) ← 依赖 T1.5（基于降级链重构）
  └─ T1.13 (mInternalPlayer release + VideoPlay 单例改造) ← 独立

Phase 2 (P1 改造, 13项)
  ├─ T2.1, T2.2, T2.3, T2.4 (Exo2MediaPlayer 增强) ← 需串行修改
  ├─ T2.7 (isParsingError 独立判断) ← 独立
  ├─ T2.5 (VideoUrlExtractor 耗时日志) ← 独立
  ├─ T2.9 (第三层失败返回 null) ← 独立
  ├─ T2.10 (VideoPlay L436 兜底返回 null) ← 独立
  ├─ T2.11 (CancellationException 守卫) ← 独立
  ├─ T2.6 (readLimitedBytes 循环 isActive) ← 依赖 T1.4
  ├─ T2.13 (sniffVideoType 复用缓存) ← 独立
  ├─ T2.8 (onPause 取消 initSource) ← 依赖 T1.13（VideoPlay 改造）
  └─ T2.12 (onStop 暂停视频) ← 独立

Phase 3 (编译+L1)
  ├─ T3.1 (编译) ← 依赖 Phase 1+2 完成
  └─ T3.2 (L1 验证) ← 依赖 T3.1

Phase 4 (L2 真机测试)
  ├─ T4.1-T4.5 (5类源测试) ← 依赖 T3.2
  ├─ T4.6 (8实例快速切换) ← 依赖 T3.2 + T1.13
  └─ T4.7 (日志收集) ← 依赖 T4.1-T4.6

Phase 5 (文档同步+验收)
  ├─ T5.1, T5.2 ← 依赖 Phase 4 通过
  └─ T5.3 ← 依赖 T5.1, T5.2
```

---

## §8 风险与回滚

### 8.1 风险点

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| VideoPlay 单例改造影响其他模块（T1.13） | 中 | 高 | 需先搜索 VideoPlay 的所有调用点，评估影响范围；可先采用方案B（状态快照）降低风险 |
| BUFFERING 超时12秒导致用户感知延迟（T2.3） | 中 | 中 | 配合 R5 delayTime 降低至 1000ms 抵消 |
| release() 方法遗漏调用（T1.8） | 低 | 中 | 在 VideoFragment.onDestroyView 强制调用 + isReleased 标志位兜底 |
| R5 delayTime 降低导致部分站点未加载完成（T1.1/T1.10） | 中 | 中 | 配合 WebView onLoadFinish 事件优化 |
| 第一层超时6秒导致部分站点未加载完成（T1.11） | 中 | 中 | 配合 WebView onLoadFinish 事件优化 |
| 协程取消响应不及时（T1.4/T2.6） | 低 | 低 | 在 sniffWithRangeRequestR4 中检查 isActive + readLimitedBytes 循环检查 |
| 重复初始化检测漏判（T2.1） | 低 | 低 | 改为"同一URL+headers才跳过"，增加 callCount 日志便于排查 |
| 抽取常量后3处调用遗漏（T1.10） | 低 | 低 | grep 搜索 `delayTime = 3000L` / `timeout = 10000L` 确认无残留 |
| 8实例快速切换测试场景构造困难（T4.6） | 中 | 低 | 可用 adb 脚本模拟快速点击切换 |

### 8.2 回滚方案

- **代码回滚**：使用 `git revert` 回滚本次所有修改
- **配置回滚**：恢复 `SNIFF_TIMEOUT_MS = 3000L` / `delayTime = 3000L` / `timeout = 10000L`
- **降级回滚**：保留 P0 改造，仅回滚 P1 改造（BUFFERING 超时检测 + isParsingError 独立判断）
- **VideoPlay 单例改造回滚**：若 T1.13 影响其他模块，可回滚为方案B（状态快照），保留 mInternalPlayer 显式 release 部分

---

## §9 验收节点

| 节点 | 验收内容 | 通过标准 |
|------|---------|---------|
| 节点 1 | Phase 1+2 编译通过 | 0 个编译错误 |
| 节点 2 | L1 验证 | 应用启动无崩溃，ExoPlayer 初始化正常 |
| 节点 3 | L2 验证（5 类源） | 嗅探成功率 ≥ 90%，视频地址获取 < 3 秒 |
| 节点 4 | 状态变量重置验收 | 切换视频时状态变量被重置（AppLog 出现 `ExoPlayer state reset` 日志） |
| 节点 5 | VideoPlay 单例验收 | 8实例快速切换状态不串扰 |
| 节点 6 | 降级链正确率验收 | MP4直链走Progressive（AppLog 出现 `ExoFallback: try contentType=4 (#1/3)`） |
| 节点 7 | 日志验证 | 所有改造点日志出现，0 个幽灵日志 |
| 节点 8 | 用户体感 | 视频地址获取时间从 8.5 秒降至 3 秒以内 |

---

## §10 关联文档

- **功能规格**：[spec.md](./spec.md)
- **架构设计**：[design.md](./design.md)
- **项目导航**：[README.md](./README.md)
- **源码深度分析汇总报告**：[docs/temp-analysis/video-playback-failure-source-analysis-20260726.md](../../temp-analysis/video-playback-failure-source-analysis-20260726.md)
- **原分析报告**：[docs/temp-analysis/video-playback-failure-analysis-20260726.md](../../temp-analysis/video-playback-failure-analysis-20260726.md)
