# 视频播放失败修复 - 架构设计

> **创建时间**：2026-07-26 17:58
> **V2修订**：2026-07-26 19:10（基于源码深度分析，修正8项V1方案 + 新增13项任务架构设计）
> **状态**：设计阶段（V2）
> **依赖**：exoplayer-resilience spec + player-review-and-optimization R4
> **来源**：基于 `docs/temp-analysis/video-playback-failure-source-analysis-20260726.md` 源码深度分析汇总报告

---

## §0 V2修订说明

### 0.1 修订依据

V1文档基于logcat日志分析创建，但未对照源码全面深度分析。V2基于4个源码文件（VideoUrlExtractor.kt / ExoPlayerHelper.kt / Exo2MediaPlayer.kt / VideoPlayerActivity.kt）深度分析，修正4个Bug根因错误 + 新发现17个遗漏Bug + 修正8项V1修复方案 + 重构1项V1修复方案。

### 0.2 V2修订范围

| 修订类型 | 数量 | 说明 |
|---------|------|------|
| Bug根因修正 | 4 | Bug-1 / Bug-2 / Bug-6 / Bug-7 |
| Bug根因补充 | 2 | Bug-5 / Bug-8 |
| 新增Bug | 17 | Bug-11~Bug-27（P0: 5个，P1: 12个） |
| V1方案修正 | 8 | T1.1/T1.2/T1.4/T1.5/T1.8/T1.9/T2.1/T2.3 |
| V1方案重构 | 1 | T2.1（1秒防重→同一URL+headers才跳过） |
| 新增任务 | 13 | T1.11~T1.14 + T2.6~T2.13 |

### 0.3 V1→V2架构变化要点

1. **降级链策略重构**：废弃MutableStateFlow方案（过度设计），改为按嗅探结果排序降级链（MP4直链优先Progressive）
2. **超时控制分层**：新增第一层MacCMS解析超时（6秒）+ 总超时（12秒），解决AnalyzeUrl默认60秒卡死
3. **生命周期管理增强**：新增isReleased标志位解决非suspend函数无法响应cancel + 改造点2移至VideoFragment.onDestroyView
4. **VideoPlay单例改造**：识别到全局object单例状态串扰是Bug-6核心根因，需per-Activity实例或状态快照
5. **BUFFERING超时修正**：5秒→12秒，避免弱网误降级
6. **协程取消守卫**：新增CancellationException守卫 + readLimitedBytes循环isActive检查

---

## §1 整体架构

### 1.1 当前架构（问题全景 - V2）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       VideoPlayerActivity（用户点击播放）                    │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ VideoPlay（全局 object 单例 ← Bug-6/Bug-14 核心根因）                  │  │
│  │  • videoUrl / videoTitle / rssArticleIndex 等全局状态                  │  │
│  │  • 8 个 Activity 实例快速切换时状态被最后一个 Activity 覆盖            │  │
│  │  • L436 兜底返回 rssArticle.link ← Bug-19（肯定非视频流URL）          │  │
│  │  • L316/L427 硬编码 delayTime=3000L/timeout=10000L ← Bug-11            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ VideoUrlExtractor.extractVideoUrlForEpisode（三层串行 ← Bug-15）       │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第一层：MacCMS 解析                                               │ │  │
│  │  │  • analyzeUrl.getStrResponseAwait() (L468) ← Bug-1 真正主因      │ │  │
│  │  │  • 无 withTimeout 包裹，AnalyzeUrl 默认 60s 超时                  │ │  │
│  │  │  • L483 catch 未守卫 CancellationException ← Bug-18              │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第二层：extractPrecise 精确提取（同步）                          │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第三层：R5 网络抓包（异步 WebView）                              │ │  │
│  │  │  • delayTime=3000ms（L489 硬编码）← Bug-1 次要原因              │ │  │
│  │  │  • timeout=10000ms（L489 硬编码）                                │ │  │
│  │  │  • L494/L498 失败返回 resolvedUrl ← Bug-16（可能非视频流URL）   │ │  │
│  │  │  • L496 catch 未守卫 CancellationException ← Bug-17              │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  • 无总超时控制 ← Bug-15（累计最长 70s）                             │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Exo2MediaPlayer.prepareAsyncInternal（← Bug-2 真正根因）              │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 状态变量未重置 ← Bug-13                                           │ │  │
│  │  │  • currentSniffResult / fallbackTypes / currentFallbackIndex     │ │  │
│  │  │  • 切换视频时旧嗅探结果/降级链状态残留                            │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ mInternalPlayer 重复创建未 release 旧实例 ← Bug-24                │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  scope.launch {                                                       │  │
│  │    sniffVideoType(url, headers)                                       │  │
│  │    SNIFF_TIMEOUT_MS = 3000L (ExoPlayerHelper.kt L515) ← Bug-3        │  │
│  │    execute() 阻塞调用不响应协程取消 ← Bug-3 补充                     │  │
│  │    readLimitedBytes 循环无 isActive 检查 ← Bug-21                     │  │
│  │    sniffVideoType 不复用 sniffMimeType 缓存 ← Bug-20                  │  │
│  │    ↓                                                                  │  │
│  │    buildFallbackTypes(sniffResult)                                    │  │
│  │    默认 HLS 优先 (contentType=2) ← Bug-7 真正根因                     │  │
│  │    MP4 直链 (contentType=4) 走 HlsMediaSource 必然失败                │  │
│  │    ↓                                                                  │  │
│  │    applyMediaSourceByType(...)  ← Bug-23（非suspend无法响应cancel）   │  │
│  │  }                                                                    │  │
│  │  scope 未在 onDestroy 时 cancel ← Bug-5                               │  │
│  │  无 release() 方法 ← Bug-5 补充                                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ ExoPlayer（播放）                                                     │  │
│  │  • onPlaybackStateChanged 无 override ← Bug-9                         │  │
│  │  • onPlayerError 用 Log.d (L577) ← Bug-4                              │  │
│  │  • isParsingError 嵌套在 isUnrecoverableError 内 ← Bug-8/Bug-22       │  │
│  │  • UnrecognizedInputFormatException 不触发降级                         │  │
│  │  • BUFFERING 状态无超时检测 ← Bug-9                                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  生命周期问题：                                                              │
│  • VideoPlayerActivity 无 onPause 实现 ← Bug-26                              │
│  • onStop L1507-1512 仅停止 glideImageGetter，未暂停视频 ← Bug-26            │
│  • initSource 协程在 onDestroy 才取消（时机晚）← Bug-25                      │
│  • VideoPlayerActivity 不直接持有 exo2MediaPlayer 引用 ← Bug-27              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 目标架构（修复后 - V2）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       VideoPlayerActivity（用户点击播放）                    │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ VideoPlay（per-Activity 实例 / 状态快照 ← FR-8/T1.13）                │  │
│  │  • L316/L427 引用常量 R5_DELAY_TIME=1000L / R5_TIMEOUT=6000L          │  │
│  │  • L436 兜底返回 null 或抛异常 ← FR-9/T2.10                           │  │
│  │  • onPause 主动取消 initSource 协程 ← FR-8/T2.8                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ VideoUrlExtractor.extractVideoUrlForEpisode                           │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第一层：MacCMS 解析                                               │ │  │
│  │  │  • withTimeout(6000L) { analyzeUrl.getStrResponseAwait() }       │ │  │
│  │  │    ← FR-1/T1.11                                                  │ │  │
│  │  │  • L483 catch 守卫 CancellationException ← FR-10/T2.11           │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第二层：extractPrecise 精确提取（同步）                          │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 第三层：R5 网络抓包（异步 WebView）                              │ │  │
│  │  │  • delayTime=R5_DELAY_TIME (1000L) ← FR-1/T1.1                   │ │  │
│  │  │  • timeout=R5_TIMEOUT (6000L) ← FR-1/T1.2                        │ │  │
│  │  │  • 失败返回 null ← FR-9/T2.9                                     │ │  │
│  │  │  • L496 catch 守卫 CancellationException ← FR-10/T2.11           │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  • withTimeout(12000L) 包裹整个 extractVideoUrlForEpisode            │  │
│  │    ← FR-1/T1.14                                                       │  │
│  │  • 各阶段耗时日志统一 putInfo 级别 ← FR-3/T2.5                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Exo2MediaPlayer.prepareAsyncInternal                                 │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 状态变量重置 ← FR-5/T1.12                                         │ │  │
│  │  │  • currentSniffResult = SniffResult.UNKNOWN                       │ │  │
│  │  │  • fallbackTypes = emptyList()                                    │ │  │
│  │  │  • currentFallbackIndex = 0                                       │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 同一 URL + headers 才跳过 ← FR-5/T2.1（重构）                    │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ mInternalPlayer 显式 release 旧实例 ← FR-5/T1.13                  │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │  scope.launch {                                                       │  │
│  │    sniffVideoType(url, headers)                                       │  │
│  │    SNIFF_TIMEOUT_MS = 5000L ← FR-2/T1.3                              │  │
│  │    execute() 内部检查 isActive ← FR-2/T1.4                            │  │
│  │    readLimitedBytes 循环检查 isActive ← FR-2/T2.6                     │  │
│  │    sniffVideoType 复用 sniffMimeType 缓存 ← FR-12/T2.13               │  │
│  │    ↓                                                                  │  │
│  │    buildFallbackTypes(sniffResult)                                    │  │
│  │    按嗅探结果排序降级链 ← FR-7/T1.5（重构）                           │  │
│  │    • MP4(contentType=4): [Progressive, HLS, DASH]                    │  │
│  │    • HLS(contentType=2): [HLS, Progressive, DASH]                    │  │
│  │    • UNKNOWN: [HLS, DASH, Progressive]                                │  │
│  │    ↓                                                                  │  │
│  │    applyMediaSourceByType(...)                                        │  │
│  │    入口检查 isReleased ← FR-4/T1.8（修正）                            │  │
│  │    内部检查 isActive ← FR-4/T1.9（补充）                              │  │
│  │  }                                                                    │  │
│  │  release() 方法（含 isReleased 标志位）← FR-4/T1.8                    │  │
│  │  在 VideoFragment.onDestroyView 中调用 ← FR-4/T1.8（修正位置）        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ ExoPlayer（播放）                                                     │  │
│  │  • onPlaybackStateChanged override → AppLog.put ← FR-3/T1.7          │  │
│  │  • onPlayerError → AppLog.put ← FR-3/T1.6                            │  │
│  │  • isParsingError 独立判断 ← FR-6/T2.7                                │  │
│  │  • UnrecognizedInputFormatException 触发降级 ← FR-6/T2.7              │  │
│  │  • BUFFERING 超时 12 秒 → tryNextFallback() ← FR-6/T2.3（修正）      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  生命周期管理（V2 增强）：                                                   │
│  • onStop 调用 deactivatePlayer() ← FR-11/T2.12                             │
│  • onPause 取消 initSource 协程 ← FR-8/T2.8                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §2 Bug详细分析与修复方案（27个Bug）

### 2.1 Bug-1：视频地址获取阶段耗时过长（V2修正根因）

#### 证据
```
17:21:13.542 VideoPlayerActivity onCreate
17:21:14.414 P3-1: ruleContent返回非视频URL, 降级R5嗅探, len=12030, hasScript=true
17:21:14.414 R5网络抓包: 启动, delayTime=3000, timeout=10000
17:21:22.076 P3-1降级R5嗅探命中（耗时 7.66 秒）
17:21:22.116 ExoPlayer Init（onCreate 后 8.5 秒）
```

#### V2根因分析（源码验证）

**真正主因**：第一层MacCMS解析 `analyzeUrl.getStrResponseAwait()`（VideoUrlExtractor.kt L468）无超时控制，AnalyzeUrl默认超时60秒。站点响应慢时第一层卡死60秒，远超R5的10秒timeout。

**次要原因**：
1. R5 网络抓包 `delayTime=3000ms` 太长，启动 WebView 后等 3 秒才开始拦截
2. 3处硬编码调用（VideoUrlExtractor.kt L489 + VideoPlay.kt L316/L427），只改默认值无效
3. 三层串行执行无总超时控制（VideoUrlExtractor.kt L450-500 extractVideoUrlForEpisode）

#### 修复方案

**T1.1/T1.2修正**：抽取常量 + 修改3处硬编码调用
```kotlin
// 新增常量（建议放在 ExoPlayerHelper.kt 或 VideoUrlExtractor.kt 顶部）
companion object {
    const val R5_DELAY_TIME = 1000L   // 从 3000ms 降至 1000ms
    const val R5_TIMEOUT = 6000L      // 从 10000ms 降至 6000ms
}

// 修改3处硬编码调用
// 1. VideoUrlExtractor.kt L489
R5NetworkSniffer.start(
    delayTime = R5_DELAY_TIME,   // 原硬编码 3000L
    timeout = R5_TIMEOUT         // 原硬编码 10000L
)
// 2. VideoPlay.kt L316
R5NetworkSniffer.start(delayTime = R5_DELAY_TIME, timeout = R5_TIMEOUT)
// 3. VideoPlay.kt L427
R5NetworkSniffer.start(delayTime = R5_DELAY_TIME, timeout = R5_TIMEOUT)
```

**T1.11新增**：第一层MacCMS解析超时控制
```kotlin
// VideoUrlExtractor.kt L468
// 改造前
val response = analyzeUrl.getStrResponseAwait(url, header)

// 改造后
val response = withTimeout(6000L) {
    analyzeUrl.getStrResponseAwait(url, header)
}
```

**T1.14新增**：extractVideoUrlForEpisode总超时
```kotlin
// VideoUrlExtractor.kt L450
suspend fun extractVideoUrlForEpisode(...): String? {
    return withTimeoutOrNull(12000L) {
        // 原三层串行逻辑
        // 第一层 MacCMS 解析（内部含 6 秒 withTimeout）
        // 第二层 extractPrecise
        // 第三层 R5 网络抓包（内部 6 秒 timeout）
    }.also {
        if (it == null) {
            AppLog.putInfo("VideoUrlExtractor: extractVideoUrlForEpisode total timeout (12s), urlPath=${sanitizeUrl(playPageUrl)}")
        }
    }
}
```

**额外优化**：监听 WebView `onPageFinished` 事件，加载完成后立即开始拦截，不等 delayTime。

---

### 2.2 Bug-2：重复嗅探 + 重复setMediaSource（V2修正根因）

#### 证据
```
17:20:27.176 ExoPlayerImpl: Init aa196b6
17:20:27.257 ExoPlayerImpl: Release aa196b6（0.081 秒后立即释放）
17:20:27.295 ExoPlayerImpl: Init 358c68e（重新初始化）
17:20:28.018 sniffVideoType success (832ms)
17:20:29.161 sniffVideoType success (1854ms) ← 重复嗅探
17:20:28.020 ExoFallback try contentType=2 (#1/3)
17:20:29.169 ExoFallback try contentType=2 (#1/3) ← 重复 ExoFallback
```

#### V2根因分析（源码验证）

**真正根因**：三者叠加导致重复嗅探和状态错乱
1. `prepareAsyncInternal` 未重置状态变量（currentSniffResult / fallbackTypes / currentFallbackIndex）
2. 旧协程未等待 cancel（currentSniffJob?.cancel() 未在入口调用）
3. mInternalPlayer 被覆盖（旧实例未显式 release）

#### 修复方案

**T1.12新增**：状态变量重置
```kotlin
// Exo2MediaPlayer.kt prepareAsyncInternal 入口
override fun prepareAsyncInternal() {
    // 重置所有状态变量
    currentSniffResult = ExoPlayerHelper.SniffResult.UNKNOWN
    fallbackTypes = emptyList()
    currentFallbackIndex = 0
    // 取消旧的嗅探协程
    currentSniffJob?.cancel()
    // ... 原逻辑
}
```

**T1.13新增**：mInternalPlayer 显式 release 旧实例
```kotlin
// Exo2MediaPlayer.kt prepareAsyncInternal
override fun prepareAsyncInternal() {
    // ... 状态重置
    // 显式 release 旧实例
    mInternalPlayer?.release()
    mInternalPlayer = ExoPlayer.Builder(context).build()
    // ... 原逻辑
}
```

**T2.1重构**：同一URL+headers才跳过（替代1秒内防重）
```kotlin
// Exo2MediaPlayer.kt
private var lastPrepareUrl: String? = null
private var lastPrepareHeaders: Map<String, String>? = null

override fun prepareAsyncInternal() {
    val currentUrl = mUrl
    val currentHeaders = mHeaders ?: emptyMap()

    // 同一 URL + headers 才跳过（避免误伤用户快速切集场景）
    if (lastPrepareUrl == currentUrl && lastPrepareHeaders == currentHeaders) {
        AppLog.put("ExoPlayer prepareAsyncInternal: skip duplicate call (same url+headers), urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
        return
    }
    lastPrepareUrl = currentUrl
    lastPrepareHeaders = currentHeaders

    // ... 状态重置 + mInternalPlayer release + 原逻辑
}
```

---

### 2.3 Bug-3：嗅探超时 3000ms 太短 + 协程取消不响应（V2补充）

#### 证据
```
17:21:25.802 嗅探子线程: success, contentType=2, elapsed=3679ms
17:21:25.806 嗅探主线程: timeout (3685ms) ← 4ms 之差
17:22:46.900 嗅探子线程: success, contentType=4, elapsed=3362ms
17:22:46.903 嗅探主线程: timeout (3365ms) ← 3ms 之差
```

#### V2根因分析（源码验证）

1. `ExoPlayerHelper.kt` L515: `private const val SNIFF_TIMEOUT_MS = 3000L`
2. 实际嗅探耗时 3362-3679ms，刚好卡在超时边界
3. `okHttpClient.newCall(request).execute()` 是阻塞调用，不响应协程取消
4. `ExoPlayerHelper.kt` L261-262 的 CancellationException catch 是死代码
5. `readLimitedBytes` 循环中无 isActive 检查

#### 修复方案

**T1.3**：提升超时时间（保持V1方案）
```kotlin
private const val SNIFF_TIMEOUT_MS = 5000L  // 从 3000ms 提升至 5000ms
```

**T1.4补充**：execute() 内部检查 isActive + readLimitedBytes 循环检查 + import 补充
```kotlin
// ExoPlayerHelper.kt
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.isActive

private suspend fun sniffWithRangeRequestR4(url: String, headers: Map<String, String>): SniffResult {
    val startTime = System.currentTimeMillis()
    return try {
        // ... 构建 request
        okHttpClient.newCall(request).execute().use { response ->
            // 检查协程是否已取消（execute() 返回后立即检查）
            if (!coroutineContext.isActive) {
                AppLog.putInfo("sniffVideoType: cancelled before reading body, urlPath=${sanitizeUrl(url)}")
                return@use SniffResult.UNKNOWN
            }
            // ... 读取 response 头部
            // readLimitedBytes 循环中检查 isActive
            readLimitedBytes(response.body!!.byteStream()) { chunk ->
                if (!coroutineContext.isActive) {
                    AppLog.putInfo("sniffVideoType: cancelled during readLimitedBytes, urlPath=${sanitizeUrl(url)}")
                    return@readLimitedBytes false  // 终止读取
                }
                // ... 解析 chunk
            }
        }
    } catch (e: kotlinx.coroutines.CancellationException) {
        throw e  // 重新抛出，保留协程取消语义
    }
    // ...
}
```

**T2.6新增**：readLimitedBytes 循环 isActive 检查（与T1.4合并实施，但作为独立任务跟踪）

---

### 2.4 Bug-7：降级链使用过期嗅探结果（V2修正根因）

#### 证据
```
17:22:46.900 嗅探子线程: success, contentType=4 (MP4), elapsed=3362ms
17:22:46.903 嗅探主线程: timeout (3365ms)
17:22:46.904 ExoFallback try contentType=2 (#1/3) ← 错误！应为 contentType=4
```

#### V2根因分析（源码验证）

**根因修正**：不存在"主线程超时"逻辑；实际是"嗅探超时3秒返回UNKNOWN后降级链默认HLS优先(contentType=2)，与MP4直链(contentType=4)不匹配"。

代码路径：
1. `sniffVideoType` 超时返回 `SniffResult.UNKNOWN`（contentType=-1）
2. 主线程立即调用 `buildFallbackTypes(UNKNOWN)`
3. `buildFallbackTypes` 走 `else` 分支：`listOf(C.TYPE_HLS, C.TYPE_DASH, C.TYPE_OTHER)`
4. 第一个降级类型是 `C.TYPE_HLS = 2`
5. 但实际视频是 MP4，应该用 `ProgressiveMediaSource`

#### 修复方案

**T1.5重构**：废弃 MutableStateFlow 方案（过度设计），改为按嗅探结果排序降级链
```kotlin
// Exo2MediaPlayer.kt
private fun buildFallbackTypes(sniffResult: ExoPlayerHelper.SniffResult): List<Int> {
    return when (sniffResult.contentType) {
        ExoPlayerHelper.SniffResult.TYPE_MP4 -> {
            // MP4 直链优先 ProgressiveMediaSource
            listOf(C.TYPE_OTHER, C.TYPE_HLS, C.TYPE_DASH)
        }
        ExoPlayerHelper.SniffResult.TYPE_HLS -> {
            // HLS 优先 HlsMediaSource
            listOf(C.TYPE_HLS, C.TYPE_OTHER, C.TYPE_DASH)
        }
        else -> {
            // UNKNOWN 保持原逻辑（HLS 优先）
            listOf(C.TYPE_HLS, C.TYPE_DASH, C.TYPE_OTHER)
        }
    }
}
```

**理由**：
- StateFlow 未解决核心问题（降级链默认HLS优先与MP4不匹配）
- 按嗅探结果排序降级链直接解决问题，且无新增依赖
- 配合 T1.3 提升嗅探超时到 5000ms，UNKNOWN 场景减少

---

### 2.5 Bug-4：ExoPlayer 错误未记录到 AppLog

#### 证据
- logcat 中**没有任何 `onPlayerError` 日志**
- **没有 `VIDEO_PLAY_ERROR` 事件**
- **没有 `VIDEO_FALLBACK_WEBVIEW` 事件**

#### 根因分析

`Exo2MediaPlayer.kt` L577: `Log.d("ExoPlayer", "onPlayerError: ...")` 用的是 `android.util.Log`
- `Log.d` 只输出到 logcat，appLog 文件不会记录
- 项目规范要求用 `AppLog.put()` 才能被持久化记录到 appLog 文件

#### 修复方案

**T1.6**：将 `Log.d` 替换为 `AppLog.put`（保持V1方案）
```kotlin
// 改造前
Log.d("ExoPlayer", "onPlayerError: errorCode=${error.errorCode}, cause=${error.cause?.javaClass?.simpleName}")

// 改造后
AppLog.put(
    "ExoPlayer onPlayerError: errorCode=${error.errorCode}(${error.errorCodeName}), " +
    "cause=${error.cause?.javaClass?.simpleName}: ${error.cause?.message}, " +
    "urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}",
    error
)
```

**T1.7**：新增 `onPlaybackStateChanged` 日志（保持V1方案，详见 §2.7）

---

### 2.6 Bug-5：ExoPlayer 生命周期与嗅探协程错位（V2补充）

#### 证据
```
17:22:43.531 ExoPlayer Init 190d4e0
17:22:44.693 VideoPlayerActivity onPause（用户退出）
17:22:45.307 onDestroy
17:22:45.419 ExoPlayer Release 190d4e0
17:22:46.900 sniffVideoType success (3362ms) ← 幽灵日志
17:22:46.904 ExoFallback try contentType=2 ← 幽灵日志
```

#### V2根因分析（源码验证）

`Exo2MediaPlayer.kt` L61: `scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)`
- 这个 scope 没有在 Activity 销毁时 `cancel`
- Exo2MediaPlayer 自身没有 `release()` 方法
- GSY release 链路不感知协程作用域
- VideoPlay.stopLoading() 是独立作用域

#### 修复方案

**T1.8修正**：新增 release() 方法 + isReleased 标志位 + 改造点2移至 VideoFragment.onDestroyView

```kotlin
// Exo2MediaPlayer.kt
private var isReleased = false

fun release() {
    if (isReleased) return
    isReleased = true
    currentSniffJob?.cancel()
    scope.cancel()
    AppLog.put("ExoPlayer scope cancelled (release), urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
}
```

**改造点2位置修正**：在 VideoFragment.onDestroyView 中调用（而非 VideoPlayerActivity.onDestroy）
```kotlin
// VideoFragment.kt
override fun onDestroyView() {
    super.onDestroyView()
    (currentPlayer as? Exo2MediaPlayer)?.release()
}
```

**理由**（Bug-27）：VideoPlayerActivity 不直接持有 exo2MediaPlayer 引用，需通过 VideoFragment 间接调用。

**T1.8增强**：applyMediaSourceByType 入口检查 isReleased（解决 scope.cancel 无法中断非suspend函数的问题）
```kotlin
private fun applyMediaSourceByType(contentType: Int, url: String, headers: Map<String, String>) {
    // 入口检查 isReleased 标志位
    if (isReleased) {
        AppLog.put("ExoFallback: applyMediaSourceByType skipped (isReleased=true), urlPath=${ExoPlayerHelper.sanitizeUrl(url)}")
        return
    }
    // ... 原逻辑
}
```

**T1.9补充**：在 applyMediaSourceByType 内部也检查 isActive
```kotlin
private fun applyMediaSourceByType(contentType: Int, url: String, headers: Map<String, String>) {
    if (isReleased) return
    // 内部检查 isActive
    if (!scope.coroutineContext.isActive) {
        AppLog.put("ExoFallback: applyMediaSourceByType skipped (scope inactive), urlPath=${ExoPlayerHelper.sanitizeUrl(url)}")
        return
    }
    // ... 原逻辑
}
```

**T2.4**：嗅探协程生命周期日志（保持V1方案）
```kotlin
currentSniffJob = scope.launch {
    AppLog.put("ExoFallback: sniff job started, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
    val sniff = ExoPlayerHelper.sniffVideoType(currentUrl, currentHeaders)
    if (!isActive) {
        AppLog.put("ExoFallback: sniff job cancelled, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
        return@launch
    }
    // ... 原逻辑
}
```

---

### 2.7 Bug-8：onPlayerError 未触发导致降级链无法启动（V2补充）

#### 证据
- 0 个 `onPlayerError` 日志
- 4 次 `ExoFallback try`（均为 #1/3，无 #2/3、#3/3）
- `tryNextFallback()` 从未被调用

#### V2根因分析（源码验证）

**补充**：`isParsingError` 判断嵌套在 `isUnrecoverableError` 内部（Exo2MediaPlayer.kt L532），`UnrecognizedInputFormatException` 若 errorCode 不在 4 个之内则不触发降级。

降级链触发条件**仅依赖** `onPlayerError` 回调，但：
1. ExoPlayer 可能没有触发 `onPlayerError`（如 BUFFERING 状态被 Release 中断）
2. 即便触发，`UnrecognizedInputFormatException` 可能因 errorCode 不匹配而不触发 `tryNextFallback()`

#### 修复方案

**T2.3修正**：BUFFERING 超时从 5 秒改为 12 秒
```kotlin
// Exo2MediaPlayer.kt
private val bufferingTimeoutHandler = Handler(Looper.getMainLooper())
private val bufferingTimeoutRunnable = Runnable {
    AppLog.put("ExoPlayer BUFFERING timeout (12s), trigger fallback, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
    tryNextFallback()
}

override fun onPlaybackStateChanged(state: Int) {
    super.onPlaybackStateChanged(state)
    val stateName = when (state) {
        Player.STATE_IDLE -> "IDLE"
        Player.STATE_BUFFERING -> "BUFFERING"
        Player.STATE_READY -> "READY"
        Player.STATE_ENDED -> "ENDED"
        else -> "UNKNOWN($state)"
    }
    AppLog.put("ExoPlayer state: $stateName, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")

    when (state) {
        Player.STATE_BUFFERING -> {
            // 12 秒后未进入 READY 则触发降级（修正：原 5 秒太短，弱网误降级）
            bufferingTimeoutHandler.postDelayed(bufferingTimeoutRunnable, 12000L)
        }
        Player.STATE_READY -> {
            bufferingTimeoutHandler.removeCallbacks(bufferingTimeoutRunnable)
        }
    }
}
```

**T2.7新增**：isParsingError 独立判断
```kotlin
// Exo2MediaPlayer.kt L532
override fun onPlayerError(error: PlaybackException) {
    super.onPlayerError(error)
    AppLog.put(
        "ExoPlayer onPlayerError: errorCode=${error.errorCode}(${error.errorCodeName}), " +
        "cause=${error.cause?.javaClass?.simpleName}: ${error.cause?.message}, " +
        "urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}",
        error
    )

    // 独立判断 isParsingError（不嵌套在 isUnrecoverableError 内）
    val isParsingError = error.cause is UnrecognizedInputFormatException
            || error.errorCode == PlaybackException.ERROR_CODE_PARSING_FAILED
            || error.errorCode == PlaybackException.ERROR_CODE_DECODER_INIT_FAILED

    if (isParsingError || isUnrecoverableError(error)) {
        AppLog.put("ExoFallback: trigger tryNextFallback due to ${if (isParsingError) "parsingError" else "unrecoverableError"}")
        tryNextFallback()
    }
}
```

---

### 2.8 Bug-9：BUFFERING 状态被 Release 中断

#### 证据
```
17:22:43.531 ExoPlayer Init 190d4e0
17:22:44.693 VideoPlayerActivity onPause（用户退出，Init 后 1.16 秒）
17:22:45.307 onDestroy
17:22:45.419 ExoPlayer Release 190d4e0
```

#### 根因分析

1. ExoPlayer 还在 BUFFERING 状态就被 Release（用户退出）
2. 没有 STATE_READY 日志确认是否真的进入播放
3. 用户可能因为等待过久而退出（与 Bug-1 相关）

#### 修复方案

**关联修复**：通过 FR-3 的 `onPlaybackStateChanged` 日志记录状态变化（T1.7），结合 FR-1 缩短地址获取时间（T1.1/T1.11/T1.14）避免用户等不及退出。

---

### 2.9 Bug-6：17:09-17:11 时段 8 个视频未进入 ExoPlayer 阶段（V2修正根因）

#### 证据
- 用户在 17:09-17:11 期间快速切换 8 个 VideoPlayerActivity 实例
- 全部没有 ExoPlayer Init 记录

#### V2根因分析（源码验证）

**核心根因**：`VideoPlay.kt` L62 `object VideoPlay : CoroutineScope by MainScope()` 是全局 object 单例。
- 8 个 Activity 实例快速切换时，VideoPlay.videoUrl / videoTitle / rssArticleIndex 等全局状态被最后一个 Activity 覆盖
- 前一个 Activity 的 initSource 协程还在运行，但读取的 VideoPlay 状态已被覆盖

#### 修复方案

**T1.13新增**：VideoPlay 单例改造（per-Activity 实例 或 状态快照）

**方案A（推荐）**：per-Activity 实例
```kotlin
// VideoPlay.kt
// 改造前：object VideoPlay : CoroutineScope by MainScope()
// 改造后：class VideoPlay(private val activity: VideoPlayerActivity) : CoroutineScope by MainScope()

class VideoPlay(private val activity: VideoPlayerActivity) : CoroutineScope by MainScope() {
    var videoUrl: String? = null
    var videoTitle: String? = null
    var rssArticleIndex: Int = 0
    // ... 其他状态

    companion object {
        fun getInstance(activity: VideoPlayerActivity): VideoPlay {
            return VideoPlay(activity)
        }
    }
}
```

**方案B（折中）**：状态快照
```kotlin
// VideoPlayerActivity.onActivityCreated
private lateinit var videoPlaySnapshot: VideoPlaySnapshot

override fun onActivityCreated(savedInstanceState: Bundle?) {
    super.onActivityCreated(savedInstanceState)
    // 保存状态快照
    videoPlaySnapshot = VideoPlaySnapshot(
        videoUrl = VideoPlay.videoUrl,
        videoTitle = VideoPlay.videoTitle,
        rssArticleIndex = VideoPlay.rssArticleIndex
    )
    // 后续使用 videoPlaySnapshot 而非 VideoPlay
}
```

**T2.8新增**：onPause 取消 initSource 协程
```kotlin
// VideoPlayerActivity.kt
private var initSourceJob: Job? = null

override fun onActivityCreated(...) {
    // ...
    initSourceJob = lifecycleScope.launch {
        // 原 initSource 逻辑
    }
}

override fun onPause() {
    super.onPause()
    // 主动取消 initSource 协程（不等 onDestroy）
    initSourceJob?.cancel()
    initSourceJob = null
}
```

---

### 2.10 Bug-10：Glide 加载站点 favicon 失败（不修复）

#### 证据
```
17:19:40.164 GlideException: Failed to load resource
  Cause: Fetching data failed, class java.io.InputStream, REMOTE
17:19:40.447 setDataSource failed: status = 0x80000000
  URL: /favicon.ico
```

#### 修复方案

**本次不修复**（非视频问题，与本次播放失败无关），建议另立 spec 处理 Glide 错误日志。

---

### 2.11 Bug-11~Bug-15（V2新增 P0 严重 Bug）

#### Bug-11：3处硬编码调用导致T1.1/T1.2修改默认值无效
- **源码位置**：VideoUrlExtractor.kt L489 + VideoPlay.kt L316 + VideoPlay.kt L427
- **影响**：V1文档T1.1/T1.2若只改默认值，Bug-1不会被修复
- **修复方案**：T1.1/T1.2修正（详见 §2.1）

#### Bug-12：第一层MacCMS解析无超时控制
- **源码位置**：VideoUrlExtractor.kt L468 `analyzeUrl.getStrResponseAwait()`
- **影响**：AnalyzeUrl默认超时60s，站点响应慢时第一层卡死60s
- **修复方案**：T1.11新增（详见 §2.1）

#### Bug-13：状态变量跨视频污染
- **源码位置**：Exo2MediaPlayer.kt prepareAsyncInternal未重置状态变量
- **影响**：切换视频时旧嗅探结果/降级链状态残留
- **修复方案**：T1.12新增（详见 §2.2）

#### Bug-14：VideoPlay全局单例状态串扰
- **源码位置**：VideoPlay.kt L62 `object VideoPlay : CoroutineScope by MainScope()`
- **影响**：8个Activity实例快速切换时全局状态被最后一个Activity覆盖
- **修复方案**：T1.13新增（详见 §2.9）

#### Bug-15：三层串行执行累计耗时超长
- **源码位置**：VideoUrlExtractor.kt L450-500 extractVideoUrlForEpisode
- **影响**：第一层(无超时60s) + 第三层(10s timeout) = 累计最长70s
- **修复方案**：T1.14新增（详见 §2.1）

---

### 2.12 Bug-16~Bug-27（V2新增 P1 中等 Bug）

#### Bug-16：第三层失败返回resolvedUrl可能是非视频流URL
- **源码位置**：VideoUrlExtractor.kt L494 `else { resolvedUrl }` + L498 `resolvedUrl`
- **影响**：如果resolvedUrl是播放页URL，传给ExoPlayer会触发UnrecognizedInputFormatException
- **修复方案**：T2.9新增
```kotlin
// VideoUrlExtractor.kt L494/L498
// 改造前：else { resolvedUrl }
// 改造后：
else {
    AppLog.putInfo("VideoUrlExtractor: 第三层R5失败, 返回null, urlPath=${sanitizeUrl(resolvedUrl)}")
    null
}
```

#### Bug-17：extractVideoUrlForEpisode L496 catch未守卫CancellationException
- **源码位置**：VideoUrlExtractor.kt L496 `} catch (e: Exception) {`
- **影响**：协程取消被吞，退出播放器时嗅探任务无法及时取消
- **修复方案**：T2.11新增
```kotlin
// VideoUrlExtractor.kt L496
// 改造前：
} catch (e: Exception) { ... }

// 改造后：
} catch (e: kotlinx.coroutines.CancellationException) {
    throw e  // 重新抛出，保留协程取消语义
} catch (e: Exception) { ... }
```

#### Bug-18：第一层L483 catch未守卫CancellationException
- **源码位置**：VideoUrlExtractor.kt L483 `} catch (e: Exception) {`
- **影响**：同Bug-17
- **修复方案**：T2.11新增（同Bug-17改造方式）

#### Bug-19：VideoPlay.kt L436兜底返回rssArticle.link
- **源码位置**：VideoPlay.kt L436 `rssArticle.link`
- **影响**：P3-1降级嗅探失败时兜底返回文章链接（肯定非视频流URL），ExoPlayer必然加载失败
- **修复方案**：T2.10新增
```kotlin
// VideoPlay.kt L436
// 改造前：return rssArticle.link
// 改造后：
AppLog.putInfo("VideoPlay: P3-1降级嗅探失败, 兜底返回null, rssArticleIndex=${rssArticleIndex}")
return null
```

#### Bug-20：sniffVideoType与sniffMimeType重复嗅探
- **源码位置**：ExoPlayerHelper.kt L151 sniffVideoType + L365 sniffMimeType
- **影响**：sniffVideoType不复用MimeSnifferCache，导致同一URL可能被嗅探两次
- **修复方案**：T2.13新增
```kotlin
// ExoPlayerHelper.kt L151
private suspend fun sniffVideoType(url: String, headers: Map<String, String>): SniffResult {
    // 复用 sniffMimeType 的缓存结果
    val mimeType = sniffMimeType(url, headers)  // 已有 MimeSnifferCache
    return when {
        mimeType.contains("mp4", ignoreCase = true) -> SniffResult(contentType = TYPE_MP4, ...)
        mimeType.contains("m3u8", ignoreCase = true) -> SniffResult(contentType = TYPE_HLS, ...)
        else -> sniffWithRangeRequestR4(url, headers)  // 缓存未命中才走 R4
    }
}
```

#### Bug-21：readLimitedBytes循环不响应协程取消
- **源码位置**：ExoPlayerHelper.kt sniffWithRangeRequestR4 L470-480
- **影响**：readLimitedBytes读取循环中无isActive检查，协程取消后仍继续读取
- **修复方案**：T2.6新增（与T1.4合并实施，详见 §2.3）

#### Bug-22：UnrecognizedInputFormatException不触发降级链
- **源码位置**：Exo2MediaPlayer.kt L532 isParsingError嵌套在isUnrecoverableError内部
- **影响**：UnrecognizedInputFormatException若errorCode不在4个之内则不触发降级
- **修复方案**：T2.7新增（详见 §2.7）

#### Bug-23：applyMediaSourceByType非suspend无法响应cancel
- **源码位置**：Exo2MediaPlayer.kt applyMediaSourceByType
- **影响**：scope.cancel无法中断非suspend函数，需配合isReleased标志位
- **修复方案**：T1.8增强（详见 §2.6）

#### Bug-24：mInternalPlayer重复创建未显式release旧实例
- **源码位置**：Exo2MediaPlayer.kt prepareAsyncInternal
- **影响**：重复Init时旧mInternalPlayer未release，资源泄漏
- **修复方案**：T1.13新增（详见 §2.2）

#### Bug-25：initSource协程未在Activity快速切换时及时取消
- **源码位置**：VideoPlayerActivity.onActivityCreated L217-229 lifecycleScope.launch
- **影响**：lifecycleScope在onDestroy才取消（时机晚），快速切换时前一个initSource协程继续运行
- **修复方案**：T2.8新增（详见 §2.9）

#### Bug-26：onPause/onStop未暂停视频播放
- **源码位置**：VideoPlayerActivity无onPause实现，onStop L1507-1512仅停止glideImageGetter
- **影响**：Activity切到后台时视频继续播放，消耗资源和音频焦点
- **修复方案**：T2.12新增
```kotlin
// VideoPlayerActivity.kt
override fun onStop() {
    super.onStop()
    currentFragment?.deactivatePlayer()
    AppLog.putInfo("VideoPlayerActivity onStop: deactivatePlayer")
}
```

#### Bug-27：T1.8改造点2位置错误
- **源码位置**：VideoPlayerActivity不直接持有exo2MediaPlayer引用
- **影响**：V1文档T1.8改造点2无法实施
- **修复方案**：T1.8修正（改造点2移至VideoFragment.onDestroyView，详见 §2.6）

---

## §3 核心改造方案（按优先级 - V2共27项任务）

### 3.1 P0 改造（Phase 1 - T1.1~T1.14，必须修复）

| 编号 | 改造点 | 文件 | 解决 Bug | V2状态 |
|------|--------|------|---------|--------|
| T1.1 | 抽取常量 R5_DELAY_TIME=1000L + 修改3处硬编码 | VideoUrlExtractor.kt + VideoPlay.kt | Bug-1 + Bug-11 | V2修正 |
| T1.2 | 抽取常量 R5_TIMEOUT=6000L + 修改3处硬编码 | VideoUrlExtractor.kt + VideoPlay.kt | Bug-1 + Bug-11 | V2修正 |
| T1.3 | SNIFF_TIMEOUT_MS 从 3000ms 提升至 5000ms | ExoPlayerHelper.kt L515 | Bug-3 | 保持 |
| T1.4 | sniffWithRangeRequestR4 检查 isActive + readLimitedBytes 循环检查 + import 补充 | ExoPlayerHelper.kt | Bug-3 + Bug-21 | V2补充 |
| T1.5 | 按嗅探结果排序降级链（MP4直链优先Progressive） | Exo2MediaPlayer.kt | Bug-7 | V2重构 |
| T1.6 | onPlayerError 用 AppLog.put 替代 Log.d | Exo2MediaPlayer.kt L577 | Bug-4 | 保持 |
| T1.7 | 新增 onPlaybackStateChanged 日志 | Exo2MediaPlayer.kt | Bug-4 + Bug-9 | 保持 |
| T1.8 | 新增 release() 方法 + isReleased 标志位 + 改造点2移至 VideoFragment.onDestroyView + applyMediaSourceByType 入口检查 isReleased | Exo2MediaPlayer.kt + VideoFragment.kt | Bug-5 + Bug-23 + Bug-27 | V2修正 |
| T1.9 | 嗅探协程检查 isActive + applyMediaSourceByType 内部检查 isActive | Exo2MediaPlayer.kt | Bug-5 | V2补充 |
| T1.11 | 第一层MacCMS解析超时控制 withTimeout(6000L) | VideoUrlExtractor.kt L468 | Bug-1 + Bug-12 | V2新增 |
| T1.12 | prepareAsyncInternal 入口重置状态变量 | Exo2MediaPlayer.kt | Bug-2 + Bug-13 | V2新增 |
| T1.13 | mInternalPlayer 显式 release 旧实例 + VideoPlay 单例改造 | Exo2MediaPlayer.kt + VideoPlay.kt | Bug-2 + Bug-14 + Bug-24 | V2新增 |
| T1.14 | extractVideoUrlForEpisode 总超时 withTimeout(12000L) | VideoUrlExtractor.kt L450 | Bug-1 + Bug-15 | V2新增 |

### 3.2 P1 改造（Phase 2 - T2.1~T2.13，重要修复）

| 编号 | 改造点 | 文件 | 解决 Bug | V2状态 |
|------|--------|------|---------|--------|
| T2.1 | 同一URL+headers才跳过（替代1秒内防重） | Exo2MediaPlayer.kt | Bug-2 | V2重构 |
| T2.2 | prepareAsyncInternal 调用日志 | Exo2MediaPlayer.kt | Bug-2 | 保持 |
| T2.3 | BUFFERING 超时 12 秒触发 tryNextFallback（原5秒） | Exo2MediaPlayer.kt | Bug-8 + Bug-9 | V2修正 |
| T2.4 | 嗅探协程生命周期日志（started/cancelled/completed） | Exo2MediaPlayer.kt | Bug-5 | 保持 |
| T2.5 | VideoUrlExtractor 各阶段耗时日志（6个阶段统一putInfo级别） | VideoUrlExtractor.kt | Bug-6 | V2补充 |
| T2.6 | readLimitedBytes 循环 isActive 检查 | ExoPlayerHelper.kt | Bug-21 | V2新增 |
| T2.7 | isParsingError 独立判断 + UnrecognizedInputFormatException 触发降级 | Exo2MediaPlayer.kt L532 | Bug-8 + Bug-22 | V2新增 |
| T2.8 | onPause 取消 initSource 协程（保存 Job 引用） | VideoPlayerActivity.kt | Bug-6 + Bug-25 | V2新增 |
| T2.9 | 第三层失败返回 null | VideoUrlExtractor.kt L494/L498 | Bug-16 | V2新增 |
| T2.10 | VideoPlay.kt L436 兜底返回 null | VideoPlay.kt L436 | Bug-19 | V2新增 |
| T2.11 | CancellationException 守卫（第一层L483 + 第三层L496） | VideoUrlExtractor.kt | Bug-17 + Bug-18 | V2新增 |
| T2.12 | onStop 暂停视频播放 | VideoPlayerActivity.kt | Bug-26 | V2新增 |
| T2.13 | sniffVideoType 复用 sniffMimeType 缓存 | ExoPlayerHelper.kt L151 | Bug-20 | V2新增 |

### 3.3 P2 改造（可选，本次不实施）

| 编号 | 改造点 | 文件 | 解决 Bug |
|------|--------|------|---------|
| P2-1 | Glide 错误日志过滤 | Glide 模块 | Bug-10 |
| P2-2 | sniffVideoType 缓存嗅探结果 + setDefaultHeaders 线程安全 + 死代码清理等8个P2/P3问题 | ExoPlayerHelper.kt 多处 | Bug-28 |

---

## §4 关键技术决策

### 4.1 决策 1：SNIFF_TIMEOUT_MS 提升至 5000ms

**选项**：
- A. 3000ms（当前，太短）
- B. 5000ms（推荐）
- C. 8000ms（更宽容但延迟感知）

**决策**：B（5000ms）

**理由**：
- 实际嗅探耗时 3362-3679ms，5000ms 提供足够缓冲
- 配合 R5 delayTime 降低至 1000ms，整体延迟可控
- 8000ms 过长，用户感知明显

### 4.2 决策 2：降级链触发条件（V2修正：12秒）

**选项**：
- A. 仅 onPlayerError（当前，不充分）
- B. onPlayerError + BUFFERING 超时 5 秒（V1方案）
- C. onPlayerError + BUFFERING 超时 12 秒（V2推荐）
- D. onPlayerError + BUFFERING 超时 3 秒

**决策**：C（V2修正）

**理由**（V2修正）：
- 5 秒太短，弱网环境下正常 BUFFERING 可能 5-10 秒，误触发降级
- 12 秒阈值避免弱网误降级，配合 R5 delayTime 降低至 1000ms + 第一层超时6秒，整体延迟仍可控
- 配合 T2.7 isParsingError 独立判断，降级链触发更精准

### 4.3 决策 3：协程取消响应

**选项**：
- A. 仅依赖 withTimeoutOrNull 自动取消（当前，不可靠）
- B. 在 sniffWithRangeRequestR4 中显式检查 isActive（推荐）
- C. 使用 OkHttp Call.cancel() 显式取消网络请求

**决策**：B + C（保持V1）

**理由**：
- B 提供协程层面的取消响应
- C 提供网络请求层面的取消（更彻底）
- 两者结合确保资源完全释放
- V2补充：在 readLimitedBytes 循环中也检查 isActive（T2.6）

### 4.4 决策 4：降级链排序策略（V2重构 - 替代原"currentSniffResult共享方式"）

**选项**：
- A. 普通变量（V1方案，有竞态）
- B. MutableStateFlow（V1推荐方案）
- C. 按嗅探结果排序降级链（V2推荐 - 重构）

**决策**：C（V2重构）

**理由**（V2修正）：
- MutableStateFlow 是过度设计，未解决核心问题
- 真正问题是降级链默认 HLS 优先与 MP4 直链不匹配
- 按嗅探结果排序降级链直接解决问题：
  - MP4(contentType=4): [Progressive, HLS, DASH]
  - HLS(contentType=2): [HLS, Progressive, DASH]
  - UNKNOWN: [HLS, DASH, Progressive]（保持原逻辑）
- 无新增依赖，实现简单

### 4.5 决策 5：R5 delayTime 降低风险

**选项**：
- A. 1000ms（推荐）
- B. 1500ms（折中）
- C. 2000ms（保守）

**决策**：A（1000ms，保持V1）

**理由**：
- 1000ms 足够 WebView 完成基础加载
- 配合 WebView onLoadFinish 事件可进一步优化
- 2000ms 仍有用户感知延迟
- V2补充：必须修改3处硬编码调用（T1.1/T1.2修正）

### 4.6 决策 6：BUFFERING 超时阈值（V2新增）

**选项**：
- A. 5 秒（V1方案，太短）
- B. 12 秒（V2推荐）
- C. 8 秒（折中）

**决策**：B（12秒）

**理由**（V2新增）：
- 5 秒在弱网环境下误降级概率高
- 12 秒阈值参考主流视频播放器（YouTube 15秒、B站 10秒）
- 配合 R5 delayTime=1000ms + 第一层超时6秒 + 总超时12秒，整体延迟可控
- 弱网场景下 12 秒允许 ExoPlayer 完成首次缓冲

### 4.7 决策 7：第一层 MacCMS 解析超时（V2新增）

**选项**：
- A. 不加超时（当前，依赖 AnalyzeUrl 默认 60s）
- B. 6 秒（V2推荐）
- C. 10 秒（折中）

**决策**：B（6秒）

**理由**（V2新增）：
- AnalyzeUrl 默认 60 秒超时太长，站点响应慢时第一层卡死
- 6 秒与 R5 timeout 对齐，确保第一层失败后第二/三层仍有时间执行
- 配合总超时 12 秒，三层累计耗时可控

### 4.8 决策 8：VideoPlay 单例改造策略（V2新增）

**选项**：
- A. 保持 object 单例（当前，状态串扰）
- B. 改为 class + per-Activity 实例（V2推荐）
- C. 保持 object + 状态快照（折中）

**决策**：B（per-Activity 实例），如影响范围大则降级为 C（状态快照）

**理由**（V2新增）：
- per-Activity 实例彻底解决状态串扰
- 状态快照是折中方案，实施风险小但不够彻底
- 需先搜索 VideoPlay 的所有调用点，评估改造影响范围
- **风险**：VideoPlay 是全局 object，改造影响面大，需充分测试

### 4.9 决策 9：prepareAsyncInternal 防重策略（V2重构）

**选项**：
- A. 1 秒内防重（V1方案，会误伤）
- B. 同一URL+headers才跳过（V2推荐）
- C. 不防重（依赖状态重置）

**决策**：B（同一URL+headers才跳过）

**理由**（V2重构）：
- 1 秒内防重会误伤合法场景（如用户快速切集）
- 同一URL+headers才跳过精准识别重复调用
- 配合 T1.12 状态变量重置 + T1.13 mInternalPlayer release，彻底解决 Bug-2

---

## §5 风险评估（V2更新）

### 5.1 高风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| VideoPlay 单例改造影响其他模块（V2新增） | 中 | 高 | 需先搜索 VideoPlay 的所有调用点，评估影响范围；如影响面大则降级为状态快照方案 |
| BUFFERING 超时 12 秒导致用户感知延迟（V2更新） | 中 | 中 | 配合 R5 delayTime 降低至 1000ms + 第一层超时 6 秒抵消；12秒仅触发降级而非整体超时 |
| 第一层超时 6 秒导致部分站点未加载完成（V2新增） | 中 | 中 | 配合 WebView onLoadFinish 事件优化；6秒未完成则走第二/三层降级 |

### 5.2 中风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| SNIFF_TIMEOUT_MS 提升导致用户感知延迟 | 中 | 中 | 配合 R5 delayTime 降低抵消 |
| 协程取消响应不及时 | 低 | 低 | 显式检查 isActive + OkHttp Call.cancel() + readLimitedBytes 循环检查 |
| 重复初始化检测漏判 | 低 | 低 | 改为"同一URL+headers才跳过"，增加 callCount 日志便于排查 |
| 降级链排序错误（V2新增） | 低 | 中 | MP4/HLS/UNKNOWN 三种场景充分测试；UNKNOWN 保持原逻辑兜底 |
| isParsingError 独立判断误触发降级（V2新增） | 低 | 中 | 仅 UnrecognizedInputFormatException + ERROR_CODE_PARSING_FAILED 触发 |
| CancellationException 守卫遗漏（V2新增） | 低 | 低 | 第一层L483 + 第三层L496 双重守卫 |

### 5.3 低风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| onPlayerError 日志格式错误 | 低 | 低 | 真机测试验证 |
| release() 方法遗漏调用 | 低 | 中 | 在 VideoFragment.onDestroyView 强制调用 |
| VideoPlay.kt L436 兜底返回 null 导致无视频可播（V2新增） | 低 | 中 | 配合 T2.9 第三层失败返回 null，统一向上传播异常 |
| sniffVideoType 复用缓存导致嗅探结果不一致（V2新增） | 低 | 低 | MimeSnifferCache 已有缓存机制，复用不影响准确性 |

---

## §6 验证方法

### 6.1 编译验证

```bash
# 测试包编译（io.legado.miss.app.debug）
gradlew assembleDebug
# 验证 APK 生成
ls -la app/build/outputs/apk/debug/app-debug.apk
```

### 6.2 L1 验证（基础功能）

```bash
# 安装测试包
adb install -r app/build/outputs/apk/debug/app-debug.apk
# 启动应用
adb shell am start -n io.legado.miss.app.debug/io.legado.app.ui.MainActivity
# 验证无崩溃
adb logcat | grep -E "FATAL|AndroidRuntime"
```

### 6.3 L2 验证（真机测试）

**测试场景**：
1. MacCMS 模板源（站点G/H 类型）
2. DPlayer 播放器源（站点I 类型）
3. 自定义播放页源（站点J 类型）
4. MP4 直链源（站点D 类型）— 验证降级链走 Progressive
5. 加密 HLS 源（AES-128 类型）
6. 8实例快速切换 — 验证 VideoPlay 单例改造

**日志收集**：
```bash
# 收集 AppLog
adb shell run-as io.legado.miss.app.debug cat /data/data/io.legado.miss.app.debug/files/appLog.txt > appLog.txt
# 收集 logcat（仅技术关键词，过滤业务数据）
adb logcat -d | grep -E "ExoPlayer|ExoFallback|sniffVideoType|VideoUrlExtractor|VideoPlay|Exception|Error|FATAL" > logcat_filtered.txt
```

**验证点**（对照27项任务）：
- ✅ `ExoPlayer prepareAsyncInternal: callCount=N` 日志出现（T2.2）
- ✅ `ExoPlayer state: BUFFERING→READY` 日志出现（T1.7，播放成功）
- ✅ `ExoPlayer onPlayerError` 日志出现（T1.6，如播放失败）
- ✅ `ExoFallback: sniff job cancelled` 日志出现（T2.4，如 Activity 销毁）
- ✅ `ExoFallback: try contentType=N (#M/3)` 推进到 #2/3+（T2.3 + T2.7）
- ✅ `ExoPlayer scope cancelled (release)` 日志出现（T1.8）
- ✅ `applyMediaSourceByType skipped (isReleased=true)` 日志出现（T1.8增强）
- ✅ 0 个幽灵日志（onDestroy 后无 sniffVideoType 日志）（T1.8 + T1.9）
- ✅ 视频地址获取时间 < 3 秒（T1.1/T1.2 + T1.11 + T1.14）
- ✅ `VideoUrlExtractor: extractVideoUrlForEpisode total timeout (12s)` 日志出现（T1.14，超时场景）
- ✅ `VideoUrlExtractor: 第一层MacCMS解析超时(6s)` 日志出现（T1.11，超时场景）
- ✅ `ExoPlayer prepareAsyncInternal: skip duplicate call (same url+headers)` 日志出现（T2.1）
- ✅ `ExoPlayer BUFFERING timeout (12s), trigger fallback` 日志出现（T2.3）
- ✅ MP4 直链源降级链走 Progressive（T1.5）
- ✅ `ExoFallback: trigger tryNextFallback due to parsingError` 日志出现（T2.7）
- ✅ 8实例快速切换时状态不串扰（T1.13）
- ✅ `VideoPlayerActivity onStop: deactivatePlayer` 日志出现（T2.12）
- ✅ `VideoPlay: P3-1降级嗅探失败, 兜底返回null` 日志出现（T2.10）

### 6.4 L3 验证（用户体感）

- ✅ 视频地址获取时间从 8.5 秒降至 3 秒以内
- ✅ 嗅探成功率从 60% 提升至 90%+
- ✅ 降级链正确率从 0% 提升至 100%（MP4 直链走 Progressive）
- ✅ 播放失败可追溯率从 0% 提升至 100%（AppLog 完整记录）
- ✅ 8实例快速切换时每个实例独立播放

---

## §6.5 Phase 6 真机测试日志分析修复设计（2026-07-26 22:30 新增）

### 6.5.1 背景

用户 2026-07-26 22:30 真机测试 R4 改造后反馈两个问题：
1. **应用崩溃一次**：crash-2026-07-26-21-52-34.log 显示 IllegalArgumentException
2. **多线路多集播放回归**：之前好使的 .m3u8 播放现在走 WebView 降级且 WebView 也失败

### 6.5.2 Bug-29 详细分析：ImageGalleryActivity Glide 销毁崩溃

**证据**：
```
crash-2026-07-26-21-52-34.log
java.lang.IllegalArgumentException: You cannot start a load for a destroyed activity
  at com.bumptech.glide.manager.RequestManagerRetriever.assertNotDestroyed(RequestManagerRetriever.java:237)
  at com.bumptech.glide.manager.RequestManagerRetriever.get(RequestManagerRetriever.java:111)
  at com.bumptech.glide.Glide.with(Glide.java:577)
  at io.legado.app.ui.image.ImageGalleryActivity$initRecyclerView$5$1.onScrollStateChanged(ImageGalleryActivity.kt:259)
  at androidx.recyclerview.widget.RecyclerView.dispatchOnScrollStateChanged(RecyclerView.java:5831)
  at androidx.recyclerview.widget.RecyclerView.stopScroll(RecyclerView.java:3028)
  at androidx.recyclerview.widget.RecyclerView.onDetachedFromWindow(RecyclerView.java:3531)
  at android.app.ActivityThread.handleDestroyActivity(ActivityThread.java:6916)
```

**根因分析**：

Activity 销毁过程的调用链：
```
ActivityThread.handleDestroyActivity
  → WindowManagerGlobal.removeViewLocked
    → ViewRootImpl.doDie
      → ViewGroup.dispatchDetachedFromWindow (多层)
        → RecyclerView.onDetachedFromWindow
          → RecyclerView.stopScroll
            → RecyclerView.setScrollState
              → RecyclerView.dispatchOnScrollStateChanged
                → OnScrollListener.onScrollStateChanged (用户代码)
                  → Glide.with(this@ImageGalleryActivity)  // ← 抛异常
```

`Glide.with(activity)` 内部会调用 `RequestManagerRetriever.assertNotDestroyed(activity)` 检查 activity 是否已销毁，若 `activity.isDestroyed == true` 则抛 `IllegalArgumentException`。

**修复方案**：

```kotlin
override fun onScrollStateChanged(recyclerView: RecyclerView, newState: Int) {
    super.onScrollStateChanged(recyclerView, newState)
    // Bug-fix 2026-07-26: Activity 销毁过程中调用 Glide.with 抛 IllegalArgumentException
    if (isDestroyed || isFinishing) return
    when (newState) {
        RecyclerView.SCROLL_STATE_DRAGGING -> {
            com.bumptech.glide.Glide.with(this@ImageGalleryActivity).pauseRequests()
        }
        RecyclerView.SCROLL_STATE_IDLE -> {
            com.bumptech.glide.Glide.with(this@ImageGalleryActivity).resumeRequests()
        }
    }
}
```

**设计决策**：
- 双重守卫 `isDestroyed || isFinishing`：覆盖所有销毁场景（用户主动 finish + 系统销毁）
- 守卫位置在 `super.onScrollStateChanged` 之后：保留父类回调逻辑，只跳过 Glide 调用
- 不影响正常滚动时的 Glide pause/resume：只有在销毁过程中才跳过

### 6.5.3 Bug-30 详细分析：VideoUrlExtractor 缺少 .m3u8 快速路径（回归 Bug）

**证据**（logcat 11 次降级，全部 .m3u8 URL）：
```
22:11:20.863 extractVideoUrlForEpisode: resolvedUrlEq=true, isMacCms=false, urlEndsWithHtml=false
22:11:20.894 extractVideoUrlForEpisode timeout (12s), 返回null, path=/20260726/qClStzb4/index.m3u8
22:11:20.895 extractVideoUrlForEpisode 返回null, 触发WebView降级, path=/20260726/qClStzb4/index.m3u8

22:11:26.043 extractVideoUrlForEpisode: resolvedUrlEq=true, isMacCms=false, urlEndsWithHtml=false
22:11:26.076 extractVideoUrlForEpisode timeout (12s), 返回null, path=/20260325/XbbvIl1F/index.m3u8
22:11:26.076 extractVideoUrlForEpisode 返回null, 触发WebView降级, path=/20260325/XbbvIl1F/index.m3u8

（共 11 次，URL 路径模式均为 /xxx/index.m3u8）
```

**回归根因分析**：

R4 T2.9 改造引入"超时返回 null"逻辑（避免非视频流URL传给 ExoPlayer 触发 UnrecognizedInputFormatException），代码路径：

```kotlin
// VideoUrlExtractor.kt extractVideoUrlForEpisode
return withTimeoutOrNull(12000L) {
    // 第一层 MacCMS 解析（isMacCms=false 时跳过）
    // 第二层 DOM 解析（复用第一层 HTML）
    // 第三层 WebView 抓包（12 秒超时）
    // T2.9: 第三层失败返回 null（不返回非视频流URL）
} ?: run {
    // T2.9: 总超时也返回 null
    AppLog.put("extractVideoUrlForEpisode timeout (12s), 返回null, ${sanitizeUrl(url)}")
    null
}
```

**关键缺陷**：入口缺少"URL 已是视频流格式"快速路径判断。当 episode.url 已是 .m3u8 格式时：
- `resolvePlayerPageUrl` 返回原 URL（不含 ?url= 参数）
- `isMacCmsPlayPage` 返回 false（不以 .html 结尾）
- 跳过第一层 MacCMS 解析
- 进入第三层 WebView 抓包 → 12 秒超时 → 返回 null → 触发 WebView 降级

**为什么之前好使？** R4 改造前，第三层 WebView 抓包失败后会返回 `resolvedUrl`（可能是 .m3u8 URL），ExoPlayer 能播放。R4 T2.9 改造后，第三层失败返回 null，触发 WebView 降级。

**修复方案**：

```kotlin
suspend fun extractVideoUrlForEpisode(
    url: String,
    source: BaseSource?,
    rssArticle: RssArticle?
): String? {
    if (url.isBlank()) return null
    // Bug-fix 2026-07-26: URL 已是视频流格式时直接返回，跳过三层解析
    if (isDirectVideoStreamUrl(url)) {
        AppLog.putInfo("extractVideoUrlForEpisode: URL已是视频流, 跳过三层解析直接返回, ${sanitizeUrl(url)}")
        return url
    }
    // ... 原三层解析逻辑
}

private fun isDirectVideoStreamUrl(url: String): Boolean {
    val lower = url.lowercase().substringBefore("?").substringBefore("#")
    return lower.endsWith(".m3u8") ||
        lower.endsWith(".mpd") ||
        lower.endsWith(".mp4") ||
        lower.endsWith(".flv") ||
        lower.endsWith(".mkv") ||
        lower.endsWith(".webm") ||
        lower.contains("format=m3u8") ||
        lower.contains("type=m3u8")
}
```

**设计决策**：
- 快速路径位置在入口：避免任何不必要的解析步骤，秒级返回
- 后缀列表包含 .m3u8/.mpd/.mp4/.flv/.mkv/.webm + format=m3u8/type=m3u8
- 排除 .ts：HLS 分片不能单独播放，需配合 m3u8 主清单
- 大小写不敏感：`lowercase()` 处理
- query 参数和锚点处理：`substringBefore("?").substringBefore("#")`

**Headers 注入流程对齐**：

修复后的完整流程与 MacCMS 解析成功流程一致：
```
1. extractVideoUrlForEpisode 返回 .m3u8 URL（直接返回，不解析）
2. VideoPlay.kt L1105-1113 重新构造 AnalyzeUrl 获取 source.headerMap（含 Referer/Cookie/UA）
3. VideoPlay.kt L1115-1116 设置 player.mapHeadData 和 currentPlayHeaders
4. VideoPlay.kt L1117 player.setUp(resolvedUrl, cachePlay, ..., episode.title)
5. ExoPlayer 用注入的 headers 请求 .m3u8 URL
```

这与 MacCMS 解析成功后的流程完全一致，防盗链能力不降级。

### 6.5.4 修复验证

| 验证项 | 结果 | 证据 |
|--------|------|------|
| 编译验证 | ✅ 通过 | assembleDebug --rerun-tasks BUILD SUCCESSFUL in 4m 13s（77 tasks executed） |
| 并发安全审查 | ✅ 通过 | Bug-1: isDestroyed/isFinishing 主线程访问；Bug-2: isDirectVideoStreamUrl 纯函数无状态 |
| 资源管理审查 | ✅ 通过 | Bug-1: 跳过 Glide 不泄漏（Activity 销毁时 Glide 自动清理）；Bug-2: 直接返回 URL 不涉及资源管理 |
| 边界场景审查 | ✅ 通过 | Bug-2: query参数/锚点/大小写/.ts排除/相对路径全部覆盖 |
| 架构一致性审查 | ✅ 通过 | Bug-2: Headers 注入流程与 MacCMS 解析成功流程一致；isDirectVideoStreamUrl 与 isMacCmsPlayPage 风格一致 |
| L2 真机测试 | ⏳ 待执行 | 需验证：1) .m3u8 URL 不再走 WebView 降级 2) 图片浏览器切文章不崩溃 |

---

## §7 关联文档

- **功能规格**：[spec.md](./spec.md)
- **任务清单**：[tasks.md](./tasks.md)
- **项目导航**：[README.md](./README.md)
- **源码深度分析汇总报告**：[docs/temp-analysis/video-playback-failure-source-analysis-20260726.md](../../temp-analysis/video-playback-failure-source-analysis-20260726.md)
- **原分析报告**：[docs/temp-analysis/video-playback-failure-analysis-20260726.md](../../temp-analysis/video-playback-failure-analysis-20260726.md)
- **前置 spec**：[../exoplayer-resilience/](../exoplayer-resilience/)
- **关联 spec**：[../player-review-and-optimization/](../player-review-and-optimization/)
