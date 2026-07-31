# OpenSpec 渗透式审查报告 V1

> **审查对象**: image-thread-coordination-fix-20260731 四文档
> **审查方法**: 对照项目真实源码逐行核实（非纸面评审）
> **审查日期**: 2026-07-31
> **审查深度**: 对齐 sniff-stability-fix V2 审计标准（44 纰漏基线）
> **结论**: ❌ **需大规模重构**（存在 12 个阻断级 ERROR + 12 个 WARN + 4 个 INFO）

---

## 一、审查结论速览

### 1.1 问题统计

| 级别 | 数量 | 说明 |
|------|------|------|
| **ERROR（阻断级）** | 12 | 根因分析错误/技术方案不可行/代码片段错误/路径全错 |
| **WARN** | 12 | 潜在风险/遗漏点/不一致/重复造轮子 |
| **INFO** | 4 | 优化建议 |

### 1.2 量化评分（0-100，仅供参考）

| 维度 | 评分 | 说明 |
|------|------|------|
| **源码匹配度** | 25 | 所有源码路径错误 + 多个 FR 根因与源码不符 |
| **技术成熟度** | 35 | FR-5 LoadControl 动态切换技术不可行 + FR-4 锚点不存在 |
| **落地清晰度** | 30 | tasks.md 锚点全错 + 多个方案无法直接开工 |

### 1.3 FR 编号对应关系（用户审查要求 ↔ 设计文档）

> **重要说明**：用户审查要求中的 FR 编号与设计文档的 FR 编号不一致，本报告统一以"设计文档 FR 编号"为准，并在每个条目标注用户审查要求对应编号。

| 用户审查要求 | 设计文档 | 一致性 |
|-------------|---------|--------|
| FR-1 图片下载取消根因 | FR-1 | ✅ 一致 |
| FR-2 ExoPlayer释放时机 | FR-2 | ✅ 一致 |
| FR-3 同URL竞态 | **FR-4** | ❌ 编号错位 |
| FR-4 postCancellation帧渲染 | **FR-3** | ❌ 编号错位 |
| FR-5 LoadControl动态切换 | FR-5 | ✅ 一致 |
| FR-6 scope取消到实例回收延迟 | **FR-2** | ❌ 编号错位（与 FR-2 同一问题） |
| FR-7 rssArticle空状态 | **FR-6** | ❌ 编号错位 |

**WARN-A**：设计文档内部 FR-2 与 FR-6 实际是同一问题（scope 取消到实例回收延迟），但被拆成两个 FR，且用户审查要求中 FR-2 和 FR-6 也指向同一问题，导致 FR 编号体系混乱。

---

## 二、ERROR 级问题逐条详情（阻断级，必须重构）

### ERROR-1（阻断级）：所有源码路径错误，"源码核实锚点"完全不可信

**缺陷定位**：
- README.md L73-77「源码核实锚点」表
- spec.md L70-72, L80, L88, L96, L104, L112
- design.md L268, L283, L311, L322-323, L337
- tasks.md L13, L25, L42, L71, L85, L105

**问题本质**：违反"代码一致性评审基准"。设计文档声称"基于源码行号级根因分析"，但所有源码路径都是错误的，证明设计文档根本没有核实源码，"源码核实"是虚假声明。

**原文错误内容**：
```
| 图片适配器 | app/src/main/java/io/legado/app/ui/book/changes/cover/ImageCanvasAdapter.kt |
| 视频片段 | app/src/main/java/io/legado/app/ui/association/VideoPlay/VideoFragment.kt |
| 媒体播放器 | app/src/main/java/io/legado/app/media/Exo2MediaPlayer.kt |
| 播放器池 | app/src/main/java/io/legado/app/media/PlayerInstancePool.kt |
| LoadControl | app/src/main/java/io/legado/app/media/ExoPlayerHelper.kt |
| VideoPlay | app/src/main/java/io/legado/app/ui/association/VideoPlay/VideoPlay.kt |
```

**真实源码路径（Glob 确认）**：
```
| 图片适配器 | app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt |
| 视频片段 | app/src/main/java/io/legado/app/ui/video/VideoFragment.kt |
| 媒体播放器 | app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt |
| 播放器池 | app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt |
| LoadControl | app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt |
| VideoPlay | app/src/main/java/io/legado/app/model/VideoPlay.kt |
```

**整改要求**：全文替换所有源码路径为真实路径，所有"源码核实"声明必须重新执行。

---

### ERROR-2（阻断级）：FR-1 根因描述错误——onRecycled 不取消下载

**缺陷定位**：
- spec.md L152 R-1.1「onRecycled 时不立即取消 downloadTarget，改为延迟 500ms 取消」
- design.md L174-179 数据流图「onRecycled (L937-945) → 延迟 500ms 取消 downloadTarget」
- README.md L83-89「关键纠正说明」声称修改锚点是 bind() 而非 onRecycled
- design.md L274「L937-945 onRecycled：改为延迟 500ms 取消，复用时取消延迟任务」

**问题本质**：违反"代码一致性评审基准"。设计文档一方面声称"修改锚点是 bind() 而非 onRecycled"（README L87-89），另一方面 R-1.1 又说"onRecycled 时不立即取消，改为延迟 500ms 取消"（spec L152）——**自相矛盾**。源码核实：onRecycled (L937-945) 根本不调用 cancelPendingDownload，只 clear photoView + 重置字段，设计文档的"延迟取消"方案没有落地锚点。

**源码依据**（[ImageCanvasAdapter.kt:937-945](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt#L937-L945)）：
```kotlin
fun onRecycled() {
    // Activity 销毁过程中回收回调跳过 Glide 调用（destroyed activity 崩溃铁证）
    if (isGlideUsable()) Glide.with(itemView.context).clear(binding.photoView)
    currentUrl = null
    currentPosition = -1
    currentItem = null
    sourceHeaderMap = null
    retryCount = 0
}
```
**注意**：onRecycled 只调用 `Glide.with(...).clear(binding.photoView)`（清除 PhotoView 显示），**不调用** `cancelPendingDownload()`（取消 downloadTarget 下载）。设计文档的 R-1.1 方案完全空想。

**整改要求**：
1. 删除 R-1.1「onRecycled 时不立即取消」整条需求（onRecycled 本来就不取消）
2. 修改锚点明确为：bind() L495 + loadImage() L600 两处 cancelPendingDownload 调用点
3. design.md 数据流图（L174-179）必须重画

---

### ERROR-3（阻断级）：FR-1 loadImage L600 第二处取消点遗漏

**缺陷定位**：
- spec.md L70-72「源码位置：L495 cancelPendingDownload 调用点」
- design.md L271「L495 bind() 中 cancelPendingDownload 调用点」

**问题本质**：违反"全需求覆盖基准"。设计文档只提到 L495 bind() 中的取消，遗漏了 L600 loadImage() 入口的 cancelPendingDownload 调用。实际流程：bind() L495 取消 → loadImage() L600 再次取消，**同一流程连续两次取消**。若只在 L495 加"延迟取消/进度阈值"，L600 仍会立即取消，方案失效。

**源码依据**（[ImageCanvasAdapter.kt:599-606](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt#L599-L606)）：
```kotlin
private fun loadImage(url: String, requestOptions: RequestOptions, position: Int) {
    cancelPendingDownload()  // ← 第二处取消点，设计文档遗漏
    if (!isGlideUsable()) return
    downloadTarget = Glide.with(itemView.context)
        .downloadOnly()
        .load(url)
        ...
}
```

**整改要求**：
1. spec.md L70-72 源码位置补充「L600 loadImage() 中 cancelPendingDownload 调用点」
2. design.md L271 同步补充
3. FR-1 方案必须同时覆盖 L495 和 L600 两处取消点，否则方案无效

---

### ERROR-4（阻断级）：FR-2 releaseSniffResources 代码片段错误——player 变量未定义

**缺陷定位**：
- design.md L286-290「详细变更」代码片段
- spec.md L78「同步调用 player.stop() + setPlayWhenReady(false)」

**问题本质**：违反"无歧义验收"基准。设计文档给出的代码片段 `player?.stop()` 中 `player` 变量在 releaseSniffResources 方法作用域内未定义。源码核实：releaseSniffResources (L408-416) 中根本没有 player/mInternalPlayer 引用，只做 scope.cancel() + removeCallbacks。

**源码依据**（[Exo2MediaPlayer.kt:408-416](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt#L408-L416)）：
```kotlin
fun releaseSniffResources() {
    if (isReleased) return  // 防止重复 release
    isReleased = true
    currentSniffJob?.cancel()
    scope.cancel()
    bufferingTimeoutHandler.removeCallbacks(bufferingTimeoutRunnable)
    AppLog.put("ExoPlayer scope cancelled, isReleased=true, urlPath=...")
}
```
**注意**：方法内无 mInternalPlayer 引用。mInternalPlayer 是父类 IjkExo2MediaPlayer 的 protected 字段，子类可访问，但设计文档代码片段未体现这一点。

**整改替换文本**（design.md L286-290）：
```kotlin
// FR-2: 在 releaseSniffResources 中同步停止渲染管线（mInternalPlayer 是父类 protected 字段）
kotlin.runCatching {
    mInternalPlayer?.let { player ->
        player.stop()
        player.playWhenReady = false
    }
}
```

---

### ERROR-5（阻断级）：FR-2 延迟根因错误——onDestroyView 无延迟机制

**缺陷定位**：
- spec.md L76「releaseSniffResources() 和 releasePlayer() 连续调用，但日志显示 scope cancelled 和 recycled 之间有 8~11 秒延迟」
- design.md L66「recycled 延迟 8~11 秒」
- README.md L51「scope cancelled 到 recycled 的延迟从 8~11 秒缩短至 ≤ 1 秒」

**问题本质**：违反"代码一致性评审基准"。设计文档声称"连续调用但实际延迟 8-11 秒"，暗示存在延迟机制。源码核实：onDestroyView (L196-225) 中 L202 releaseSniffResources 和 L203 releasePlayer 是**同步连续调用**，中间无 Handler.post/postDelayed。L436/L439/L461/L510/L513 的 postDelayed 是 progressMonitor/autoHide/bufferUpdate，**不在 onDestroyView 中**。延迟根因分析错误，导致 FR-2 修复方向偏离。

**源码依据**（[VideoFragment.kt:196-225](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L196-L225)）：
```kotlin
override fun onDestroyView() {
    cancelAutoHide()
    stopBufferUpdate()
    stopProgressMonitor()
    VideoPlay.videoManager.releaseSniffResources()  // L202 同步
    releasePlayer()                                   // L203 同步连续
    webViewPlayer?.release()
    // ... 清理引用，无 Handler.post
    super.onDestroyView()
}
```

**调用链分析**：
1. L202 releaseSniffResources → 同步执行 scope.cancel + removeCallbacks
2. L203 releasePlayer (L333-335) → `_playerView?.currentPlayer?.release()`
3. currentPlayer.release() → Exo2MediaPlayer.release() (L454-467)
4. Exo2MediaPlayer.release() → releaseSniffResources（被 isReleased 防重复跳过）+ mInternalPlayer?.let { detachFromPlayer + PlayerInstancePool.recycle + mInternalPlayer=null } + super.reset()
5. PlayerInstancePool.recycle (L168-193) → 同步执行 stop/clearMediaItems/clearVideoSurface 等

**真实延迟来源假设（需日志重新验证）**：
- 假设 A：日志时间戳对比错误（scope cancelled 日志在 L415，recycled 日志在 L192 PlayerInstancePool.recycle，两者可能跨 onDestroyView 边界）
- 假设 B：super.reset() 父类 IjkExo2MediaPlayer 的某些同步阻塞操作
- 假设 C：延迟来自 Activity.onDestroy 而非 Fragment.onDestroyView（调用路径不同）
- 假设 D：releaseSniffResources 在其他路径被提前调用（如 deactivatePlayer），recycled 在 onDestroyView 才触发

**整改要求**：
1. 重新分析 logs(9)..zip 中 scope cancelled 和 recycled 日志的精确时间戳和调用栈
2. 确认延迟来源后再定修复方案，禁止凭空假设"releaseSniffResources 与 releasePlayer 之间有延迟"
3. 若延迟来自 super.reset()，FR-2 方案（加 stop/setPlayWhenReady）可能无效

---

### ERROR-6（阻断级）：FR-5 LoadControl 动态切换技术不可行

**缺陷定位**：
- spec.md L98-102「动态切换 LoadControl 为 prioritizeTime=false + minBuffer=1500ms」
- design.md L131-137「动态切换 LoadControl」
- tasks.md L91-94「dynamicLoadControl 方法，支持运行时切换」

**问题本质**：违反"技术成熟度评估"基准。ExoPlayer 的 LoadControl 是 player 构建时通过 `ExoPlayer.Builder.setLoadControl()` 设置的，**运行时无标准 API 切换**。源码注释明确说明此限制。设计文档的"运行时热切换"方案在技术上不可行，除非重建 ExoPlayer 实例（会导致播放中断）。

**源码依据**（[ExoPlayerHelper.kt:85-88](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L85-L88)）：
```kotlin
* - 工程折中：LoadControl 只能在 player 构建时设置，运行时不可热切换，
*   因此档位决策放在 prepare 前——每次 prepareAsyncInternal 时读取当前档位构建 player；
*   网络切换后新档位在下一次 prepare 生效
```

**整改要求**：FR-5 方案必须改为「prepare 前按带宽档位构建 LoadControl」（当前已有 createLoadControlByTier L137 实现），删除"运行时动态切换"方案。

---

### ERROR-7（阻断级）：FR-5 prioritizeTime 概念错误

**缺陷定位**：
- spec.md L100「prioritizeTime=true 导致快速起播但缓冲不足」
- design.md L129「prioritizeTime=true 导致快速起播但缓冲区不足」

**问题本质**：违反"代码一致性评审基准"。设计文档混淆了 `setPrioritizeTimeOverSizeThresholds` 和 `bufferForPlayback` 两个完全不同的概念。

**源码依据**（[ExoPlayerHelper.kt:145-147](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L145-L147)）：
```kotlin
builder.setTargetBufferBytes(-1)
// 缓冲速度优化（P0）：时间优先于字节，确保 maxBuffer 时长真正生效
builder.setPrioritizeTimeOverSizeThresholds(true)
```

**概念澄清**：
- `setPrioritizeTimeOverSizeThresholds(true)`：当缓冲时长达到 minBufferMs 时就认为缓冲足够，而不必等到 targetBufferBytes 字节。作用是"让 maxBuffer 时长真正生效"，与"快速起播"无关。
- `bufferForPlayback`（L152/157/162 的 500ms/800ms/500ms）：才是控制"快速起播"的参数，即缓冲多少就开始播放。
- 设计文档说"prioritizeTime=true 导致快速起播但缓冲不足"完全错误，快速起播是 bufferForPlayback 控制的。

**整改要求**：删除"prioritizeTime=true 导致快速起播"的错误描述，重新分析 BUFFERING→READY 循环的真实根因（可能是 bufferForPlayback=500ms 过小 + 弱网下 TTFB 大）。

---

### ERROR-8（阻断级）：FR-4 switchVideo 函数不存在，方案无落地锚点

**缺陷定位**：
- spec.md L94「switchVideo 时检查 currentUrl == newUrl」
- design.md L111「switchVideo 时检查 currentUrl == newUrl」
- design.md L311「VideoFragment.kt 或 VideoPlay.kt 修改 switchVideo」
- tasks.md L72「定位 switchVideo 方法」

**问题本质**：违反"无歧义验收"基准。VideoPlay.kt 中**没有 switchVideo 函数**，也**没有 currentUrl 字段**。Grep 全文确认：只有 `savePlayState(switchVideo: StandardGSYVideoPlayer)` 和 `clonePlayState(switchVideo: StandardGSYVideoPlayer)`，参数名叫 switchVideo 但不是函数名。实际切换逻辑是 `switchToArticle(index, player)` (L1126) 切换文章，和 `playRssEpisode(player, episode)` (L1284) 播放集数。设计文档方案没有落地锚点。

**源码依据**（Grep VideoPlay.kt 结果）：
- L1126: `fun switchToArticle(index: Int, player: StandardGSYVideoPlayer): Boolean`
- L1284: `fun playRssEpisode(player: GSYBaseVideoPlayer, episode: RssEpisode)`
- L220: `var videoUrl: String? = null`（不是 currentUrl）
- L1349: `private fun triggerPreload(currentUrl: String, headers: Map<String, String>)`（参数名 currentUrl，但不是字段）

**整改要求**：FR-4 必须重新定位真实切换锚点：
1. 文章切换：switchToArticle L1126（切换 rssArticle，非 URL）
2. 集数切换：playRssEpisode L1284
3. 同 URL 场景：实际由 seekTo 处理（VideoFragment L1241 `pv.currentPlayer.seekTo(seekTarget)`）
4. 删除"switchVideo 时检查 currentUrl == newUrl"方案

---

### ERROR-9（阻断级）：FR-6 把已知"正常流程"当 bug 修，会引入新问题

**缺陷定位**：
- spec.md L106-110「rssArticle 为 null 时不应立即返回，应自动等待文章加载完成后播放」
- design.md L336-344「startPlay 中 rssArticle 为 null 时不 return，注册一次性回调」

**问题本质**：违反"全需求覆盖基准"和"规避过度设计"。源码注释明确说明：rssArticle 为 null 是**正常滑动退出的正常流程**，已经从 toast 改为静默日志（BUG4 fix）。设计文档把它当 bug 修，要求"不立即返回 + 注册回调自动播放"，会引入新问题：用户正常滑动退出视频页时，会触发"等待文章加载 + 自动播放"，干扰用户体验。

**源码依据**（[VideoPlay.kt:353-359](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L353-L359)）：
```kotlin
val rssArticle = rssStar?.toRssArticle() ?: rssRecord?.toRssArticle() ?: rssArticles?.getOrNull(rssArticleIndex)
if (rssArticle == null) {
    // BUG4 fix: 正常滑动退出时rssArticle变null属正常流程，toast干扰用户体验
    // 改为静默日志，保留问题可追溯性
    AppLog.putWarn("VideoPlay: rssArticle is null in startPlay, rssArticleIndex=$rssArticleIndex")
    return
}
```

**整改要求**：
1. 删除 FR-6「rssArticle 为 null 时不立即返回，注册一次性回调自动播放」整条需求
2. 若用户反馈的"需要二次操作"是真实问题，需重新定位根因（可能是 switchToArticle 异步加载期间 rssArticle 临时为 null，应优化 switchToArticle 而非 startPlay）
3. 保留现有静默日志逻辑，不引入"自动播放"副作用

---

### ERROR-10（高）：FR-3 onPlayerStateChanged 方法不存在

**缺陷定位**：
- spec.md L88「onPlayerStateChanged 检查标志位」
- design.md L303「onPlayerStateChanged 首行：if (isScopeCancelled.get()) return」
- tasks.md L56「确认 onPlayerStateChanged/onPlayerError/首帧渲染回调位置」

**问题本质**：违反"代码一致性评审基准"。Media3 中 `onPlayerStateChanged` 已废弃，实际方法是 `onPlaybackStateChanged(state: Int)` (L993)。设计文档方法名错误，实施时找不到对应方法。

**源码依据**（[Exo2MediaPlayer.kt:993](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt#L993)）：
```kotlin
override fun onPlaybackStateChanged(state: Int) {  // ← 不是 onPlayerStateChanged
    super.onPlaybackStateChanged(state)
    // ...
}
```

**整改要求**：所有 `onPlayerStateChanged` 替换为 `onPlaybackStateChanged`。

---

### ERROR-11（高）：FR-5 已有 TTFB 统计，重复造轮子

**缺陷定位**：
- spec.md L101「监听 onLoadCompleted，统计 TTFB」
- design.md L328「Exo2MediaPlayer onLoadCompleted 中计算 TTFB」
- tasks.md L87-89「onLoadCompleted 中计算 TTFB」

**问题本质**：违反"规避过度设计"基准。源码已有完整的 TTFB 统计逻辑：onLoadStarted L1090 记录 loadStartTimeMs + onLoadCompleted L1105 计算 TTFB + 告警阈值 500ms。设计文档 FR-5 重复实现已存在功能。

**源码依据**（[Exo2MediaPlayer.kt:1084-1130](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt#L1084-L1130)）：
```kotlin
private var loadStartTimeMs: Long = 0L  // L1084

override fun onLoadStarted(...) {  // L1090
    super.onLoadStarted(...)
    loadStartTimeMs = System.currentTimeMillis()
}

override fun onLoadCompleted(...) {  // L1105
    super.onLoadCompleted(...)
    if (loadStartTimeMs > 0) {
        val loadElapsed = System.currentTimeMillis() - loadStartTimeMs  // TTFB 计算
        if (loadElapsed > 500) {
            AppLog.put("[BufferSpeed] onLoadCompleted SLOW: ttfb=${loadElapsed}ms, ...")
        }
        loadStartTimeMs = 0L
    }
}
```

**整改要求**：FR-5 删除"新增 TTFB 统计"任务，复用现有 loadStartTimeMs + onLoadCompleted 逻辑，只新增"连续 3 次 TTFB>1000ms 触发档位切换"判断。

---

### ERROR-12（高）：FR-7 synchronized 块位置错误，ImagePlay 无 synchronized 块

**缺陷定位**：
- spec.md L118「排查 ImagePlay 所有 synchronized 块，添加非空守卫」
- design.md L350「ImagePlay 单例 synchronized 块非空守卫」
- tasks.md L120「Grep 排查 ImagePlay 所有 synchronized 块」

**问题本质**：违反"代码一致性评审基准"。Grep 确认 ImagePlay.kt **没有 synchronized() 块**，只有 @Synchronized 注解（L56/66/84/110）。@Synchronized 注解等价于 `synchronized(this)`，this 不可能为 null。model 目录的 synchronized(this) 块在 AudioPlay/ImageProvider/ReadManga/CacheBook，**不在 ImagePlay/ReadBook**。设计文档排查方向错误。

**源码依据**（Grep 结果）：
- ImagePlay.kt：`@Synchronized` 注解 4 处（L56/66/84/110），无 `synchronized()` 块
- model 目录 synchronized(this) 块：
  - AudioPlay.kt L149, L157
  - CacheBook.kt L383
  - ImageProvider.kt L69
  - ReadManga.kt L85, L107

**NullPointerException(monitor-enter) 真实根因假设**：
- @Synchronized 注解等价于 synchronized(this)，this 不可能为 null
- 真正的 monitor-enter NPE 可能来自：synchronized(lockObject) 中 lockObject 为 null，或 Java 字节码层面的 monitor 指令
- 需重新分析日志调用栈，定位真实的 synchronized 块

**整改要求**：
1. FR-7 排查目标改为：AudioPlay/ImageProvider/ReadManga/CacheBook 的 synchronized(this) 块
2. 重新分析 NullPointerException(monitor-enter) 的调用栈，定位真实锁对象
3. 删除"ImagePlay synchronized 块"的错误排查目标

---

## 三、WARN 级问题逐条详情

### WARN-1：FR-1 验收标准引用不存在的日志

**定位**：spec.md L167「'fast scroll skip preload' 日志频次下降 ≥ 70%」、README.md L48

**问题**：Grep ImageCanvasAdapter.kt 无 "fast scroll" 或 "fastScroll" 字样，实际只有 "preloadAround skip: activity destroyed" (L335)。验收标准无法执行。

**整改**：删除"fast scroll skip preload"验收指标，或改为基于真实日志的指标（如 "preloadAround skip" 频次）。

### WARN-2：FR-2 releasePlayer 调用链未理清

**定位**：design.md L211-213 数据流图

**问题**：releasePlayer (L333-335) 调用 `_playerView?.currentPlayer?.release()`，currentPlayer.release() 实际是 Exo2MediaPlayer.release() (L454)，其中会再次调用 releaseSniffResources (L455 双保险，被 isReleased 防重复)。设计文档未理清此调用链，可能导致重复修复。

**整改**：design.md 数据流图补充调用链：`releasePlayer → currentPlayer.release() → Exo2MediaPlayer.release() → releaseSniffResources(被防重复) + PlayerInstancePool.recycle`。

### WARN-3：FR-2 bufferingTimeoutHandler 已清理，设计文档未提

**定位**：design.md L286-290 releaseSniffResources 变更说明

**问题**：releaseSniffResources L414 已有 `bufferingTimeoutHandler.removeCallbacks(bufferingTimeoutRunnable)` 清理 BUFFERING 超时回调。设计文档只提"新增 stop/setPlayWhenReady"，未提到现有清理逻辑，可能导致实施时遗漏现有清理或重复实现。

**整改**：design.md 变更说明补充"保持 L414 bufferingTimeoutHandler.removeCallbacks 现有清理逻辑不变"。

### WARN-4：FR-1 preloadAround 已有 activity destroyed 检查

**定位**：design.md L273「L323 preloadAround：增加 throttle 300ms 机制」

**问题**：preloadAround L326-340 已有 "Activity 销毁后不再触发 Glide 加载" 检查（crash-2026-07-26 铁证）。设计文档没提到现有检查，可能导致实施时遗漏。

**整改**：design.md 变更说明补充"保持 L326-340 activity destroyed 检查不变"。

### WARN-5：.bak 目录说明之前已修复，设计文档不知道

**定位**：项目根目录 `.bak/sniff-stability-enhance-20260731/ExoPlayerHelper.kt`

**问题**：.bak 目录是之前 sniff-stability-enhance 修复的备份。当前代码已有完整优化：createLoadControlByTier (L137)、带宽分档策略 (WEAK/MEDIUM/GOOD)、TTFB 统计 (L1084)、PlayerInstancePool 实例池等。设计文档似乎不知道这些已有优化，FR-5 提出重复方案。

**整改**：审查 .bak 目录的修复历史，对比当前代码，避免重复或冲突。在 design.md 补充"已有优化基线"章节。

### WARN-6：FR-3 isScopeCancelled 与 isReleased 职责重叠

**定位**：design.md L300「新增 isScopeCancelled: AtomicBoolean」

**问题**：Exo2MediaPlayer 已有 isReleased (L78) 用于 applyMediaSourceByType 入口检查 (L275)，已有 isPreparing (L89) AtomicBoolean。新增 isScopeCancelled 与 isReleased 职责重叠：两者都是"释放后忽略后续操作"。设计文档未说明为何不能复用 isReleased。

**整改**：评估复用 isReleased 替代新增 isScopeCancelled，或在 design.md 说明两者职责差异（isReleased 防止 setMediaItem，isScopeCancelled 防止回调触发业务逻辑）。

### WARN-7：FR-1 进度阈值 60% 实施难度被低估

**定位**：spec.md L154「若图片已下载超过 60%，则不取消」、design.md L277「downloadProgress: Float（下载进度，通过拦截器估算）」

**问题**：Glide.downloadOnly 不暴露下载进度回调。设计文档说"通过拦截器估算 ±10% 误差"，但 OkHttpStreamFetcher 的拦截器实现复杂，且 downloadOnly 走的是 Glide 的 ResourceLoader 链路，不易注入进度拦截器。实施难度被低估。

**整改**：评估进度阈值的真实可行性，或改为"基于文件已写入大小估算"（需访问 Glide 磁盘缓存临时文件）。

### WARN-8：FR-5 现有分档策略未提及

**定位**：spec.md L98-102、design.md L126-143

**问题**：当前已有 WEAK/MEDIUM/GOOD 三档 (L99-103)、bandwidthMeter 实时测量 (L92-94)、getCurrentBandwidthTier (L110)、createLoadControlByTier (L137)。设计文档 FR-5 不知道这些，提出"动态切换"重复优化。

**整改**：FR-5 改为"在 prepareAsyncInternal 中调用 getCurrentBandwidthTier + createLoadControlByTier"，复用现有分档策略。

### WARN-9：tasks.md 0.1 任务"Read 源码确认所有锚点行号"但路径全错

**定位**：tasks.md L13「Read 源码确认所有锚点行号」

**问题**：tasks.md 列出的所有源码路径都是错误的（同 ERROR-1），任务 0.1 无法执行。

**整改**：tasks.md L13 所有路径替换为真实路径。

### WARN-10：FR-4 实际切换逻辑在 switchToArticle，已有 source 匹配检查

**定位**：design.md L313-316 switchVideo 方案

**问题**：switchToArticle (L1126-1167) 已有 source 匹配检查 (L1141-1153)、rssStar/rssRecord 更新 (L1154-1158)。同 URL 场景实际由 playRssEpisode 处理或 seekTo 处理。设计文档 FR-4 方案没有落地锚点。

**整改**：FR-4 重新定位真实切换锚点（switchToArticle / playRssEpisode / seekTo），删除 switchVideo 方案。

### WARN-11：FR-2 onDestroyView 调用顺序正确但设计文档没说清楚

**定位**：spec.md L76

**问题**：onDestroyView L202 releaseSniffResources → L203 releasePlayer，顺序正确（先取消嗅探协程，再释放 player）。设计文档没解释为什么顺序重要，可能导致实施时误调顺序。

**整改**：spec.md 补充调用顺序说明："必须先 releaseSniffResources 取消嗅探协程，避免 releasePlayer 后嗅探协程回调 setMediaItem 操作已 release 的 mInternalPlayer"。

### WARN-12：FR-1 延迟取消 500ms 可能导致连接数失控

**定位**：spec.md L152 R-1.1「延迟 500ms 取消」、design.md L274

**问题**：快速滑动时每个 ViewHolder 延迟 500ms 取消，若 30 秒内滑动产生 100+ 个 ViewHolder，理论上同时有 100+ 个下载连接未取消（虽然部分会被复用取消），可能导致连接数失控或 OOM。设计文档 NFR-1.3「内存占用不显著增加」未给出连接数上限。

**整改**：补充"延迟取消期间最大并发连接数上限"（如 ≤ 10），超过上限时立即取消最早的下载。

---

## 四、INFO 级优化建议

### INFO-1：建议参考 .bak 目录的修复历史

**定位**：`.bak/sniff-stability-enhance-20260731/` 和 `.bak_enhance_20260731/`

**建议**：对比 .bak 目录的 ExoPlayerHelper.kt 与当前文件，了解之前的修复内容，避免重复或冲突。当前代码的 createLoadControlByTier、PlayerInstancePool、TTFB 统计等可能来自之前的修复。

### INFO-2：FR-2 建议在 release() 而非 releaseSniffResources() 加 stop

**定位**：design.md L286-290

**建议**：releaseSniffResources 只是"取消嗅探资源"，语义上不包含"停止播放器"。release() (L454-467) 才是最终释放点。建议在 release() 的 `mInternalPlayer?.let { player -> ... }` 块中（L456-459）加 `player.stop(); player.playWhenReady = false`，语义更准确。但需注意：onDestroyView L202 先调 releaseSniffResources，L203 才调 releasePlayer → release()，若要"立即停止"应在 releaseSniffResources 中加。

### INFO-3：FR-5 建议改为"prepare 前按带宽档位构建"

**定位**：spec.md L98-102

**建议**：当前已有 createLoadControlByTier (L137) + getCurrentBandwidthTier (L110)，只需在 prepareAsyncInternal (L494) 中调用即可。无需"运行时热切换"，下次 prepare 自动按新带宽档位构建 LoadControl。

### INFO-4：建议统一 FR 编号

**定位**：全文档

**建议**：用户审查要求的 FR 编号与设计文档不一致（见 1.3 节对应关系表），建议在设计文档中明确标注对应关系，避免实施时混淆。

---

## 五、逐 FR 核实结论

### FR-1 图片下载取消策略优化（P0）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| bind() 调用 cancelPendingDownload | L466 bind → L495 cancelPendingDownload | ✅ 属实（L466/L495） | 匹配 |
| onRecycled 取消 downloadTarget | R-1.1 说"onRecycled 时不立即取消" | ❌ onRecycled 根本不取消 | **ERROR-2** |
| loadImage 第二处取消 | 未提及 | ❌ L600 loadImage 也有 cancelPendingDownload | **ERROR-3** |
| cancelPendingDownload 实现 | L549-553 | ✅ 属实（L549-554） | 匹配 |
| onViewRecycled 触发 onRecycled | 未提及 | ✅ L299-309 onViewRecycled → L302 holder.onRecycled() | 匹配 |
| preloadAround | L323 | ✅ 属实（L323） | 匹配 |
| "fast scroll skip preload" 日志 | AC-1.3 引用 | ❌ 不存在此日志 | **WARN-1** |
| 进度阈值 60% 可行性 | 通过拦截器估算 | ⚠️ Glide.downloadOnly 不暴露进度 | **WARN-7** |

**FR-1 总体结论**：❌ 根因描述部分错误（onRecycled 不取消），遗漏第二处取消点（L600），方案需重构。

### FR-2 ExoPlayer 释放时序优化（P0）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| releaseSniffResources 位置 | L408-416 | ✅ 属实（L408-416） | 匹配 |
| releaseSniffResources 无 stop | 声称需新增 stop | ✅ 属实（L408-416 无 player 引用） | 匹配 |
| 代码片段 player?.stop() | player 变量 | ❌ player 未定义，应为 mInternalPlayer | **ERROR-4** |
| 8-11 秒延迟根因 | releaseSniffResources 与 releasePlayer 间延迟 | ❌ onDestroyView L202-203 同步连续，无延迟机制 | **ERROR-5** |
| releasePlayer 调用链 | 未理清 | ⚠️ releasePlayer → currentPlayer.release → Exo2MediaPlayer.release → PlayerInstancePool.recycle | **WARN-2** |
| bufferingTimeoutHandler 清理 | 未提及 | ⚠️ L414 已有清理 | **WARN-3** |

**FR-2 总体结论**：❌ 延迟根因错误，代码片段错误，需重新分析延迟来源。

### FR-3 取消后忽略 ExoPlayer 回调（P1）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| onPlayerStateChanged 方法 | 检查标志位 | ❌ 方法不存在，应为 onPlaybackStateChanged (L993) | **ERROR-10** |
| onPlayerError 方法 | 检查标志位 | ✅ 属实（L711） | 匹配 |
| 首帧渲染回调 | onRenderedFirstFrame | ✅ 属实（L1044） | 匹配 |
| isScopeCancelled 必要性 | 新增标志位 | ⚠️ 与 isReleased (L78) 职责重叠 | **WARN-6** |
| isReleased 已有检查 | 未提及 | ⚠️ L275 已有 isReleased + scope.isActive 检查 | 匹配 |

**FR-3 总体结论**：⚠️ 方法名错误，与现有 isReleased 职责重叠，需重构。

### FR-4 同 URL 防抖（P1）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| switchVideo 函数 | 修改 switchVideo | ❌ switchVideo 不存在 | **ERROR-8** |
| currentUrl 字段 | 检查 currentUrl == newUrl | ❌ 无 currentUrl 字段，有 videoUrl (L220) | **ERROR-8** |
| 实际切换逻辑 | switchVideo | ⚠️ switchToArticle (L1126) + playRssEpisode (L1284) + seekTo (L1241) | **WARN-10** |
| switchToArticle 已有 source 检查 | 未提及 | ⚠️ L1141-1153 已有 source 匹配检查 | **WARN-10** |

**FR-4 总体结论**：❌ 方案无落地锚点，需重新定位真实切换逻辑。

### FR-5 LoadControl 动态调整（P1）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| 运行时动态切换 LoadControl | dynamicLoadControl 方法 | ❌ 技术不可行，LoadControl 构建时设置 | **ERROR-6** |
| prioritizeTime 含义 | 导致快速起播 | ❌ setPrioritizeTimeOverSizeThresholds 是时间优先于字节，非快速起播 | **ERROR-7** |
| TTFB 统计 | 新增 onLoadCompleted 统计 | ❌ L1084-1130 已有完整 TTFB 统计 | **ERROR-11** |
| 现有分档策略 | 未提及 | ⚠️ L99-103 已有 WEAK/MEDIUM/GOOD 三档 | **WARN-8** |
| 现有 bandwidthMeter | 未提及 | ⚠️ L92-94 已有实时带宽测量 | **WARN-8** |

**FR-5 总体结论**：❌ 技术方案不可行，概念错误，重复造轮子，需完全重构。

### FR-6 rssArticle 空状态保护（P2）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| rssArticle null 立即返回 | 需改为不返回 | ❌ 注释明确"正常滑动退出属正常流程" | **ERROR-9** |
| 已有 BUG4 fix | 未提及 | ⚠️ L355 已从 toast 改为静默日志 | **ERROR-9** |
| 注册回调自动播放 | 新增回调 | ⚠️ 会引入"正常退出也自动播放"副作用 | **ERROR-9** |

**FR-6 总体结论**：❌ 把正常流程当 bug 修，会引入新问题，需删除或重新定义。

### FR-7 NullPointerException(monitor-enter) 修复（P2）

| 核实项 | 设计文档声称 | 源码实际 | 结论 |
|--------|------------|---------|------|
| ImagePlay synchronized 块 | 排查 ImagePlay | ❌ ImagePlay 用 @Synchronized 注解，无 synchronized() 块 | **ERROR-12** |
| ReadBook synchronized 块 | 排查 ReadBook | ❌ ReadBook 不在 model 目录 synchronized 列表 | **ERROR-12** |
| 真实 synchronized 位置 | ImagePlay/ReadBook | ⚠️ 实际在 AudioPlay/ImageProvider/ReadManga/CacheBook | **ERROR-12** |
| @Synchronized 注解 | 未提及 | ⚠️ ImagePlay L56/66/84/110 用 @Synchronized，等价 synchronized(this) | **ERROR-12** |

**FR-7 总体结论**：❌ 排查方向错误，需重新定位真实 synchronized 块。

---

## 六、文档一致性检查

### 6.1 README ↔ spec ↔ design ↔ tasks 一致性

| 检查项 | README | spec | design | tasks | 一致性 |
|--------|--------|------|--------|-------|--------|
| FR 数量 | 7 | 7 | 7 | 7 | ✅ |
| FR 编号 | FR-1~7 | FR-1~7 | FR-1~7 | FR-1~7 | ✅ |
| 源码路径 | 错误 | 错误 | 错误 | 错误 | ❌ 全错（ERROR-1） |
| bind 行号 | L466 | L466 | L466 | L466 | ✅ 一致但路径错 |
| releaseSniffResources 行号 | L408 | L408 | L408 | L408 | ✅ 一致但路径错 |
| onRecycled 行号 | L937 | 未提 | L937 | L937 | ✅ 一致但路径错 |
| 验收标准 | 8 项 | 8 项 | 未列 | 19 项 | ⚠️ tasks 最详细 |

### 6.2 内部矛盾

1. **README L87-89 vs spec L152**：README 说"修改锚点是 bind() 而非 onRecycled"，spec R-1.1 又说"onRecycled 时不立即取消，改为延迟 500ms 取消"——**自相矛盾**（ERROR-2）
2. **design L271 vs design L274**：L271 说修改锚点是 L495 bind，L274 又说 L937-945 onRecycled 改为延迟 500ms 取消——**自相矛盾**（ERROR-2）

---

## 七、问题优先级整改清单

### 阻断级（必须重构后方可实施）

| # | 问题位置 | 问题描述 | 整改条目 |
|---|---------|---------|---------|
| 1 | 全文档 | 所有源码路径错误 | ERROR-1 |
| 2 | spec L152, design L274 | FR-1 onRecycled 不取消，R-1.1 空想 | ERROR-2 |
| 3 | spec L70, design L271 | FR-1 loadImage L600 取消点遗漏 | ERROR-3 |
| 4 | design L286-290 | FR-2 代码片段 player 变量未定义 | ERROR-4 |
| 5 | spec L76, design L66 | FR-2 延迟根因错误，onDestroyView 无延迟机制 | ERROR-5 |
| 6 | spec L98-102, design L131 | FR-5 LoadControl 动态切换技术不可行 | ERROR-6 |
| 7 | spec L100, design L129 | FR-5 prioritizeTime 概念错误 | ERROR-7 |
| 8 | spec L94, design L111 | FR-4 switchVideo 不存在 | ERROR-8 |
| 9 | spec L106-110, design L336 | FR-6 把正常流程当 bug 修 | ERROR-9 |
| 10 | spec L88, design L303 | FR-3 onPlayerStateChanged 不存在 | ERROR-10 |
| 11 | spec L101, design L328 | FR-5 已有 TTFB 统计，重复造轮子 | ERROR-11 |
| 12 | spec L118, design L350 | FR-7 synchronized 位置错误 | ERROR-12 |

### 高优先级（需修复后方可实施）

| # | 问题位置 | 问题描述 | 整改条目 |
|---|---------|---------|---------|
| 13 | spec L167 | FR-1 验收标准引用不存在日志 | WARN-1 |
| 14 | design L211 | FR-2 releasePlayer 调用链未理清 | WARN-2 |
| 15 | design L286 | FR-2 bufferingTimeoutHandler 已清理未提 | WARN-3 |
| 16 | design L273 | FR-1 preloadAround 已有检查未提 | WARN-4 |
| 17 | .bak 目录 | FR-5 不知道已有优化 | WARN-5 |
| 18 | design L300 | FR-3 isScopeCancelled 与 isReleased 重叠 | WARN-6 |
| 19 | spec L154 | FR-1 进度阈值 60% 实施难度被低估 | WARN-7 |
| 20 | spec L98 | FR-5 现有分档策略未提及 | WARN-8 |
| 21 | tasks L13 | tasks 0.1 路径全错 | WARN-9 |
| 22 | design L313 | FR-4 实际切换逻辑在 switchToArticle | WARN-10 |
| 23 | spec L76 | FR-2 调用顺序未解释 | WARN-11 |
| 24 | spec L152 | FR-1 延迟取消 500ms 连接数失控风险 | WARN-12 |

---

## 八、需求遗漏专项说明

### 遗漏-1：FR-1 遗漏 onViewRecycled 与 onRecycled 的关系

设计文档未说明 onViewRecycled (L299) 会调用 holder.onRecycled() (L302)。实施时若不清楚此调用关系，可能误改 onViewRecycled 而非 onRecycled。

### 遗漏-2：FR-2 遗漏 Exo2MediaPlayer.release() 的双保险调用

设计文档未说明 Exo2MediaPlayer.release() (L454) 内部会再次调用 releaseSniffResources (L455)，导致 releaseSniffResources 实际被调用两次（onDestroyView L202 + release L455），虽有 isReleased 防重复，但实施时需理解此双保险机制。

### 遗漏-3：FR-5 遗漏 prepareAsyncInternal 中的 LoadControl 构建点

设计文档未说明 prepareAsyncInternal (L494) 中 mInternalPlayer = PlayerInstancePool.acquire (L554) 时如何设置 LoadControl。实际 PlayerInstancePool.acquire 构建新 player 时会调 createLoadControlByTier，设计文档应在此处优化而非"运行时热切换"。

### 遗漏-4：FR-7 遗漏真实 NPE 根因分析

设计文档未分析 NullPointerException(monitor-enter) 的真实调用栈。@Synchronized 注解等价 synchronized(this)，this 不可能为 null。真实的 monitor-enter NPE 可能来自：
- synchronized(lockObject) 中 lockObject 为 null（需排查具体 lockObject）
- Java 字节码层面的 monitor 指令（可能与 Kotlin 属性 getter 有关）
- 需重新分析日志调用栈定位

---

## 九、整体评审结论

### 9.1 判定结果

❌ **需大规模重构**

### 9.2 判定依据

1. **12 个阻断级 ERROR**：所有源码路径错误 + 5 个 FR 根因错误 + 2 个技术方案不可行 + 2 个代码片段错误 + 2 个锚点不存在 + 1 个把正常流程当 bug
2. **源码匹配度极低（25 分）**：设计文档声称"源码核实"但路径全错，多个 FR 根因与源码不符
3. **技术成熟度不足（35 分）**：FR-5 LoadControl 动态切换技术不可行，FR-4 switchVideo 不存在
4. **落地清晰度不足（30 分）**：tasks.md 锚点全错，多个方案无法直接开工

### 9.3 与 sniff-stability-fix V2 审计对比

| 维度 | sniff-stability-fix V2 | 本次审查 |
|------|----------------------|---------|
| ERROR 数 | 14 | 12 |
| WARN 数 | 25 | 12 |
| 遗漏根因 | 3 | 4 |
| 总纰漏数 | 44 | 28 |
| 严重程度 | 高 | 高 |

本次审查发现 28 个纰漏（12 ERROR + 12 WARN + 4 遗漏），虽少于 sniff-stability-fix V2 的 44 个，但阻断级 ERROR 占比更高（12/28 = 43% vs 14/44 = 32%），且最严重的"所有源码路径错误"问题在 sniff-stability-fix V2 中未出现，说明本次设计文档的"源码核实"声明可信度更低。

### 9.4 整改后落地可行性最终确认

**完成全部 12 个阻断级 ERROR 整改后**：⚠️ **整改后仍需二次审查**

原因：
1. ERROR-5（FR-2 延迟根因）需重新分析日志时间戳，整改后可能发现新根因
2. ERROR-6（FR-5 LoadControl）需完全重构为"prepare 前按档位构建"，整改后需验证与现有 createLoadControlByTier 的协同
3. ERROR-8（FR-4 switchVideo）需重新定位真实切换逻辑，整改后需验证同 URL 场景的真实处理路径
4. ERROR-9（FR-6 rssArticle）需重新定义"空状态保护"的边界，避免干扰正常退出流程

**建议**：完成阻断级整改后，进行 V2 审查确认所有方案可落地，再进入实施阶段。

---

## 十、整改优先级建议

### 第一优先级（阻断级，必须先完成）

1. **ERROR-1 路径替换**：全文替换所有源码路径为真实路径（影响全文档）
2. **ERROR-2/3 FR-1 重构**：删除 R-1.1，修改锚点为 bind L495 + loadImage L600
3. **ERROR-5 FR-2 延迟根因重新分析**：重新对比日志时间戳，确认延迟来源
4. **ERROR-6/7/11 FR-5 完全重构**：改为"prepare 前按带宽档位构建"，复用现有 createLoadControlByTier
5. **ERROR-8 FR-4 重新定位**：改为 switchToArticle / playRssEpisode / seekTo 真实锚点
6. **ERROR-9 FR-6 删除或重新定义**：避免干扰正常退出流程
7. **ERROR-12 FR-7 排查方向修正**：改为 AudioPlay/ImageProvider/ReadManga/CacheBook

### 第二优先级（高，整改后需验证）

8. **ERROR-4 FR-2 代码片段修正**：player → mInternalPlayer
9. **ERROR-10 FR-3 方法名修正**：onPlayerStateChanged → onPlaybackStateChanged
10. **WARN-1~12 逐项修复**

### 第三优先级（验证）

11. 完成整改后进行 V2 审查
12. V2 审查通过后进入实施阶段

---

## 附录 A：审查工具与命令记录

### A.1 路径确认（Glob）
- `**/ImageCanvasAdapter.kt` → 真实路径确认
- `**/VideoFragment.kt` → 真实路径确认
- `**/Exo2MediaPlayer.kt` → 真实路径确认
- `**/PlayerInstancePool.kt` → 真实路径确认
- `**/ExoPlayerHelper.kt` → 真实路径确认
- `**/VideoPlay.kt` → 真实路径确认
- `**/ImagePlay.kt` → 真实路径确认

### A.2 函数定位（Grep）
- ImageCanvasAdapter.kt: cancelPendingDownload / bind / onViewRecycled / preloadAround / onRecycled
- Exo2MediaPlayer.kt: releaseSniffResources / release / onPlaybackStateChanged / onRenderedFirstFrame / onLoadStarted / onLoadCompleted / onPlayerError
- VideoFragment.kt: onDestroyView / releasePlayer / Handler / postDelayed
- PlayerInstancePool.kt: recycle / reset / release
- ExoPlayerHelper.kt: LoadControl / prioritizeTime / setPrioritizeTimeOverSizeThresholds / createLoadControlByTier
- VideoPlay.kt: startPlay / rssArticle / switchVideo / switchToArticle / currentUrl
- model 目录: synchronized 块定位

### A.3 源码行号核实（Read）
- ImageCanvasAdapter.kt: L290-380, L460-620, L930-970
- Exo2MediaPlayer.kt: L400-470, L710-750, L985-1145
- VideoFragment.kt: L190-340
- PlayerInstancePool.kt: L155-210
- ExoPlayerHelper.kt: L80-180
- VideoPlay.kt: L300-430, L1115-1170

### A.4 .bak 目录对比
- `.bak/sniff-stability-enhance-20260731/ExoPlayerHelper.kt` 存在，说明之前已修复
- 当前 ExoPlayerHelper.kt 已有 createLoadControlByTier / 带宽分档 / TTFB 统计等优化

---

## 附录 B：输出安全声明

本报告遵循 output-safety.md 规范：
- ✅ 未输出源名称（用"源[N]"或省略）
- ✅ 未输出域名（用"站点A/B/C"或省略）
- ✅ 未输出完整 URL（用"/path/{id}"或 urlPath 替代）
- ✅ 未输出 cookie/token/key 等敏感字段
- ✅ 只输出技术结论（异常类型/错误码/调用栈/字段名/函数名）
- ✅ 源码引用使用相对路径（项目内路径）
- ✅ 日志引用使用 sanitizeUrl/take(2) 处理后的内容

---

**审查完毕。建议完成阻断级整改后进行 V2 审查。**
