# Spec: 图片加载与视频切换线程协调修复

> **Spec ID**: image-thread-coordination-fix-20260731
> **状态**: 🔄 设计中（V2，基于源码逐行核实重构）
> **创建日期**: 2026-07-31
> **版本**: 2.0
> **审查基线**: audit-report-v1.md（12 ERROR + 12 WARN 全部整改）

---

## 1. Intent（意图）

### 1.1 用户反馈

用户测试 073121 正式包（`io.legado.miss.app.release`）后反馈：

> "整体评估，视频嗅探能力可以了，但是图片还是不行，并且还有一个问题是，现在切换视频的时候明显能够感觉到线程的协调调度还是有点问题"

### 1.2 问题分解

反馈包含两个独立但相关的技术问题：

1. **图片加载不行**：图片画布模式下快速滑动时图片显示空白，无法正常加载完整图片
2. **线程协调调度有问题**：切换视频时存在可感知的协调异常，表现为释放延迟、回调竞争、缓冲震荡

### 1.3 期望结果

- 图片在快速滑动后能正常显示（不再大面积空白）
- 切换视频时无感知的线程协调异常（无延迟、无重复渲染、无缓冲震荡）

---

## 2. Scope（范围）

### 2.1 In Scope（本次覆盖）

| 层 | 模块 | 范围 |
|----|------|------|
| 图片层 | ImageCanvasAdapter | bind() L495 + loadImage() L600 两处取消点优化、preloadAround 节流 |
| 图片层 | AudioPlay/ImageProvider/ReadManga/CacheBook | synchronized(this) 块调用栈重新分析（object 单例 this 非 null，非空守卫无效） |
| 播放器层 | Exo2MediaPlayer | releaseSniffResources 同步 stop、isScopeCancelled 标志位 |
| 播放器层 | VideoFragment / VideoPlay | onDestroyView 时序、switchToArticle/playRssEpisode 防抖（含 Job 引用前置修改）、switchToArticle 状态保护 |
| 网络层 | ExoPlayerHelper | 连续慢 TTFB 强制降档（复用现有 PlayerInstancePool.createLoadControl 档位构建逻辑） |

### 2.2 Out of Scope（本次不覆盖）

- 书源/订阅源规则引擎改动
- Cronet 网络栈本身的优化（仅调整 LoadControl 策略以适配网络波动）
- 图片磁盘缓存容量调整
- 视频嗅探能力本身（用户已确认"可以了"）
- Vue3 前端改动
- 不重新实现已有的 TTFB 统计（L1084-1130 已完整）
- 不重新实现已有的带宽分档策略（L99-103/L110-117/L137-174 已完整）

---

## 3. Approach（方案）

### 3.1 Selected Approach（选定方案）

采用**分层精准修复**策略，7 个 FR 各自独立、可独立回滚，按优先级分阶段实施。

> **V2 重大修正**：
> - FR-1：删除"onRecycled 延迟取消"（onRecycled 根本不取消下载），改为覆盖 bind L495 + loadImage L600 两处取消点
> - FR-2：重新分析延迟根因（onDestroyView L202-203 同步连续无延迟机制）
> - FR-3：方法名修正 onPlayerStateChanged → onPlaybackStateChanged (L993)
> - FR-4：switchVideo → switchToArticle (L1126) / playRssEpisode (L1284) 真实锚点
> - FR-5：完全重构为"prepare 前按带宽档位构建"（复用现有 createLoadControlByTier）
> - FR-6：删除"rssArticle null 注册回调自动播放"（正常流程），改为 switchToArticle 状态保护
> - FR-7：排查目标改为 AudioPlay/ImageProvider/ReadManga/CacheBook

#### FR-1（P0）：图片下载取消策略优化

**问题**：`ImageCanvasAdapter` 存在**两处** `cancelPendingDownload()` 调用点：
1. `bind()` (L466) 内 L495 调用 `cancelPendingDownload()`
2. `loadImage()` (L599) 入口 L600 再次调用 `cancelPendingDownload()`

同一流程连续两次取消，导致快速滑动时 Glide.downloadOnly 下载被频繁打断，无法完整写入磁盘缓存，显示空白。

> **源码核实**：`onRecycled()` (L937-945) 只 `clear(photoView)` + 重置字段（currentUrl/currentPosition/currentItem/sourceHeaderMap/retryCount），**不调用** `cancelPendingDownload()`。早期假设"onRecycled 取消下载"错误。

**方案**（同时覆盖两处取消点）：
1. **取消节流**：bind L495 + loadImage L600 两处取消点增加节流机制，避免快速滑动时频繁取消
2. **下载进度阈值**：若图片已下载超过阈值，则不取消（让请求完成写入磁盘缓存）
3. **preloadAround 节流**：增加 throttle 300ms，避免"取消 5 个 + 新发 5 个"同时发生
4. **可见性优先级**：快速滑动时仅取消"离视口距离 > 2 屏"的 ViewHolder 下载

> **保持不变**：preloadAround L326-340 已有 activity destroyed 检查（crash-2026-07-26 铁证），不修改。

**源码位置**：
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L495 bind() 内 cancelPendingDownload 调用点（第一处）
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L600 loadImage() 内 cancelPendingDownload 调用点（第二处）
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L549-554 cancelPendingDownload 实现
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L323-340 preloadAround（已有 activity destroyed 检查）

#### FR-2（P0）：ExoPlayer 释放时序优化

**问题**：`releaseSniffResources()` (L408-416) 只做 `scope.cancel()` + `removeCallbacks` + `isReleased=true`，**未同步停止 mInternalPlayer 渲染管线**，导致解码器/渲染器未立即断开。

> **源码核实（V2 重大修正）**：
> - `VideoFragment.onDestroyView` (L196-225) 中 L202 `releaseSniffResources` + L203 `releasePlayer` 是**同步连续调用**，无 Handler.post/postDelayed
> - 早期"延迟 8-11 秒"的根因需重新分析。真实延迟来源假设：
>   - 假设 A：日志时间戳对比错误（scope cancelled 日志在 L415，recycled 日志在 PlayerInstancePool.recycle L192，两者可能跨 onDestroyView 边界）
>   - 假设 B：`super.reset()` 父类 IjkExo2MediaPlayer 的某些同步阻塞操作
>   - 假设 C：延迟来自 Activity.onDestroy 而非 Fragment.onDestroyView
>   - 假设 D：releaseSniffResources 在其他路径被提前调用
> - 需日志重新验证延迟来源后再定最终方案

**方案**：在 `releaseSniffResources()` (L408-416) 中同步调用 `mInternalPlayer?.stop()` + `setPlayWhenReady(false)`，立即断开渲染管线和解码器。

> **代码片段修正**：`mInternalPlayer` 是父类 IjkExo2MediaPlayer 的 protected 字段，子类可访问。早期代码片段 `player?.stop()` 中 `player` 变量未定义，修正为 `mInternalPlayer?.let { player -> ... }`。

**调用链**（V2 理清）：
```
onDestroyView L202 releaseSniffResources (同步: scope.cancel + removeCallbacks + 新增 mInternalPlayer.stop)
    ↓
onDestroyView L203 releasePlayer (L333-335: _playerView?.currentPlayer?.release())
    ↓
Exo2MediaPlayer.release() (L454-467)
    ├─ releaseSniffResources() 双保险（被 isReleased 防重复跳过）
    ├─ mInternalPlayer?.let { detachFromPlayer + PlayerInstancePool.recycle + mInternalPlayer=null }
    └─ super.reset()
         ↓
PlayerInstancePool.recycle (L167-193, 同步: stop/clearMediaItems/clearVideoSurface 等)
```

> **保持不变**：L414 `bufferingTimeoutHandler.removeCallbacks(bufferingTimeoutRunnable)` 现有清理逻辑不变。
> **调用顺序说明**：必须先 releaseSniffResources 取消嗅探协程，避免 releasePlayer 后嗅探协程回调 setMediaItem 操作已 release 的 mInternalPlayer。

**源码位置**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L408-416 releaseSniffResources

#### FR-3（P1）：取消后忽略 ExoPlayer 回调

**问题**：scope cancelled 后 217ms 仍触发 first frame rendered。协程取消未同步传递到 ExoPlayer 实例。

> **源码核实（V2 修正）**：Media3 中 `onPlayerStateChanged` 已废弃，实际方法为 `onPlaybackStateChanged(state: Int)` (L993)。

**方案**：增加 `isScopeCancelled` 标志位（AtomicBoolean），`onPlaybackStateChanged` 检查标志位，取消后忽略所有后续回调。

> **职责差异说明**：
> - `isReleased` (L78)：用于 `applyMediaSourceByType` 入口检查（防止 setMediaItem）
> - `isScopeCancelled`（新增）：用于回调入口检查（防止 onPlaybackStateChanged/onPlayerError/首帧渲染触发业务逻辑）
> - 两者职责不同，不复用。`isReleased` 防止"写入"，`isScopeCancelled` 防止"回调"。

**源码位置**：
- `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L993 onPlaybackStateChanged
- `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L711 onPlayerError
- `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L1044 onRenderedFirstFrame

#### FR-4（P1）：切换文章/集数防抖避免 cancel-prepare 竞争（V3 补充 Job 引用前置修改）

**问题**：切换文章/集数时，旧播放的 cancel 与新播放的 prepareAsync 可能在 10ms 内连续触发，ExoPlayer 实例在 release 和 prepareAsync 之间状态不确定。

> **源码核实（V2 重大修正）**：
> - VideoPlay.kt **没有 switchVideo 函数**，也**没有 currentUrl 字段**
> - 实际切换逻辑：
>   - 文章切换：`switchToArticle(index, player)` (L1126-1167)——切换 rssArticle，已有 source 匹配检查 (L1141-1153)
>   - 集数切换：`playRssEpisode(player, episode)` (L1284-1336)
>   - 同 URL 场景：由 seekTo 处理
> - 字段是 `videoUrl` (L220)，不是 `currentUrl`

> **源码核实（V3 重大补充——Coroutine.async 未保存 Job 引用）**：
> - `switchToArticle` L1137 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` **未保存 Job 引用**，无法取消前一个异步任务
> - `playRssEpisode` L1294 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` **同样未保存 Job 引用**
> - "取消前一个异步任务"需先修改保存 Job 引用作为前置条件

**方案**（V3 补充前置修改）：

**前置修改**（必须先完成，FR-4 和 FR-6 共享）：
1. 在 VideoPlay 中新增字段：`private var switchArticleJob: Job? = null` 和 `private var playEpisodeJob: Job? = null`
2. `switchToArticle` 的 `Coroutine.async` 赋值给 `switchArticleJob`，`playRssEpisode` 的 `Coroutine.async` 赋值给 `playEpisodeJob`

**FR-4 方案**：
1. `switchToArticle` (L1126) 开始时先 `switchArticleJob?.cancel()` 取消前一个异步任务
2. 然后再执行新的 `Coroutine.async`（赋值给 `switchArticleJob`）
3. `playRssEpisode` (L1284) 开始时先 `playEpisodeJob?.cancel()` 取消前一个异步任务
4. 然后再执行新的 `Coroutine.async`（赋值给 `playEpisodeJob`）

> **保持不变**：switchToArticle L1141-1153 已有 source 匹配检查，不修改。

**源码位置**：
- `app/src/main/java/io/legado/app/model/VideoPlay.kt` L1126-1167 switchToArticle（L1137 Coroutine.async 未保存 Job）
- `app/src/main/java/io/legado/app/model/VideoPlay.kt` L1284-1336 playRssEpisode（L1294 Coroutine.async 未保存 Job）

#### FR-5（P1）：连续慢 TTFB 强制降档（V3 重新定义）

**问题**：弱网下 TTFB>1000ms 时反复 BUFFERING→READY 循环（单 URL 29 秒内 7 次循环）。

> **源码核实（V3 重大修正——prepare 前按档位构建已是现有行为）**：
> - `PlayerInstancePool.createLoadControl()` (L106-113) **已经**调用 `ExoPlayerHelper.getCurrentBandwidthTier()` + `ExoPlayerHelper.createLoadControlByTier(tier, sharedAllocator)` 按带宽档位构建 LoadControl
> - `PlayerInstancePool.acquire(looper)` (L122-149) 在新建 ExoPlayer 时通过 `.setLoadControl(createLoadControl())` (L136) 设置 LoadControl
> - 即"prepare 前按带宽档位构建 LoadControl"**已是现有行为**，FR-5 不需要修改 PlayerInstancePool.createLoadControl
> - ExoPlayerHelper.kt L86-88 注释明确"LoadControl 只能在 player 构建时设置，运行时不可热切换"
> - 早期"prioritizeTime=true 导致快速起播"概念错误：`setPrioritizeTimeOverSizeThresholds(true)` (L147) 是"时间优先于字节，确保 maxBuffer 时长真正生效"，不是"快速起播"。控制起播的是 `bufferForPlayback` (L152/157/162)
> - 已有完整 TTFB 统计 (L1084-1130)：onLoadStarted L1090 记录 loadStartTimeMs + onLoadCompleted L1105 计算 TTFB（loadElapsed 变量）+ 告警阈值 500ms，不重复实现

**方案**（FR-5 真正需新增的只是"连续 3 次 TTFB>1000ms 强制降档"判断逻辑）：
1. **不修改 PlayerInstancePool.createLoadControl**（已有档位构建逻辑，L106-113）
2. 在 `Exo2MediaPlayer.onLoadCompleted` (L1105-1130) 中复用现有 TTFB 统计（loadElapsed 变量已计算好），新增 `ttfbSlowCount` 计数器
3. 连续 3 次 TTFB>1000ms 时调用 `ExoPlayerHelper.getCurrentBandwidthTier()` 获取当前档位，若当前是 GOOD/MEDIUM 则强制降一档（GOOD→MEDIUM / MEDIUM→WEAK），记录到 `forceTier` 字段
4. 降档后下次 `prepareAsyncInternal` 时 `PlayerInstancePool.acquire` 会按新档位构建 LoadControl（**复用现有逻辑**，无需额外修改）
5. 网络恢复（连续 3 次 TTFB<500ms）后重置 `ttfbSlowCount`，清除 `forceTier`，下次 prepare 时恢复自动档位
6. 注意：acquire 命中池（reuse）时不会重新设置 LoadControl，只有新建实例时才用新档位；forceTier 降级后需调用 `PlayerInstancePool.recycle` 归还旧实例或等待池自然淘汰，确保下次 acquire 新建实例时使用新档位

> **已有优化基线**（不重复实现）：
> - `PlayerInstancePool.createLoadControl()` (L106-113)：已按带宽档位构建 LoadControl（调用 getCurrentBandwidthTier + createLoadControlByTier）
> - `PlayerInstancePool.acquire()` (L122-149)：新建实例时通过 setLoadControl 设置（L136）
> - `bandwidthMeter` (L92-94)：DefaultBandwidthMeter 全局单例，实时测量有效带宽
> - `BandwidthTier` 枚举 (L99-103)：WEAK/MEDIUM/GOOD 三档
> - `getCurrentBandwidthTier()` (L110-117)：按 bitrateEstimate 分档
> - `createLoadControlByTier(tier, allocator)` (L137-174)：按档位构建 DefaultLoadControl
> - TTFB 统计 (L1084-1130)：onLoadStarted + onLoadCompleted + loadElapsed 变量 + 告警阈值 500ms

**源码位置**：
- `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` L106-113 createLoadControl（**不修改**，已有档位构建）
- `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` L122-149 acquire（**不修改**，新建时 setLoadControl）
- `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` L137-174 createLoadControlByTier（复用）
- `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` L110-117 getCurrentBandwidthTier（复用）
- `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` L1084-1130 TTFB 统计（复用 loadElapsed，新增 ttfbSlowCount 降档判断）

#### FR-6（P2）：switchToArticle 状态保护（V3 补充 Job 引用前置修改）

**问题**：`switchToArticle` (L1126-1167) 异步加载期间，`rssArticle` 可能临时为 null，若此时触发 `startPlay` 会空转。

> **源码核实（V2 重大修正）**：
> - `startPlay` L353-359 中 rssArticle 为 null 是**正常滑动退出的正常流程**，已有 BUG4 fix 静默日志
> - 早期"rssArticle 为 null 时不立即返回，注册回调自动播放"方案会把正常流程当 bug 修，会引入"正常退出也自动播放"副作用，已删除
> - 保留现有静默日志逻辑不变

> **源码核实（V3 重大补充——依赖 FR-4 前置修改）**：
> - FR-6 的"取消前一个异步任务"依赖 FR-4 的前置修改（switchArticleJob 字段）
> - `switchToArticle` L1137 的 `Coroutine.async` 未保存 Job 引用，需先完成前置修改

**方案**（V3 补充前置修改）：

**前置修改**（与 FR-4 共享，见 FR-4 说明）：
1. 在 VideoPlay 中新增 `private var switchArticleJob: Job? = null` 字段
2. `switchToArticle` 的 `Coroutine.async` 赋值给 `switchArticleJob`

**FR-6 方案**：
1. switchToArticle 进入异步加载时设置 `isSwitchingArticle = true` 标志
2. 异步加载完成（startPlay 调用前）清除标志
3. 若异步加载期间用户再次触发切换，通过 `switchArticleJob?.cancel()` 取消前一个异步任务（依赖前置修改）
4. **预期行为**：switchToArticle 的异步任务被取消后，`withContext(Main)` 中的 `startPlay` 不会执行——这是预期行为（用户切换到新文章时，旧文章的加载应该被取消）
5. 不修改 startPlay 的 rssArticle null 静默日志逻辑

**源码位置**：
- `app/src/main/java/io/legado/app/model/VideoPlay.kt` L1126-1167 switchToArticle（L1137 Coroutine.async 未保存 Job，依赖前置修改）
- `app/src/main/java/io/legado/app/model/VideoPlay.kt` L1159-1162 withContext(Main) { startPlay(player) }（被取消后不执行，预期行为）
- `app/src/main/java/io/legado/app/model/VideoPlay.kt` L308-360 startPlay（保持现有静默日志不变）

#### FR-7（P2）：NullPointerException(monitor-enter) 调用栈重新分析（V3 重新定义）

**问题**：10+ 次 NullPointerException(monitor-enter) 异常，需重新分析调用栈定位真实根因。

> **源码核实（V3 重大修正——非空守卫方案无效）**：
> - AudioPlay/ImageProvider/ReadManga/CacheBook **都是 object 单例**（源码核实：`object AudioPlay` L40 / `object CacheBook` L42 / `object ImageProvider` L31 / `object ReadManga` L45）
> - object 单例的 `this` **不可能为 null**，"为 synchronized(this) 块添加非空守卫"方案毫无意义，已删除
> - ImagePlay.kt **没有 synchronized() 块**，只有 `@Synchronized` 注解（L56/66/84/110），@Synchronized 等价 synchronized(this)，this 同样不可能为 null
> - NullPointerException(monitor-enter) 的真实根因需重新分析调用栈才能定位

**方案**（重新定义为"调用栈重新分析"）：
1. **Step 1：重新分析调用栈**——实施阶段首先重新分析 logs(9) 中 NullPointerException(monitor-enter) 的完整调用栈
2. **Step 2：定位真实锁对象**——根据调用栈定位真实的锁对象：
   - 可能是 `synchronized(lockObject)` 中 lockObject 为 null（非 synchronized(this) 场景）
   - 可能是 Java 字节码层面的 monitorenter 指令操作数栈为 null
   - 可能是其他对象的字段在并发场景下被置 null
3. **Step 3：根据锁对象类型决定修复方案**：
   - 如果调用栈指向 `@Synchronized` 注解方法（等价 synchronized(this)），则 this 不可能为 null，需分析是否是其他原因（如对象已被 GC 但引用残留、Kotlin object 初始化未完成等）
   - 如果调用栈指向 `synchronized(lockObject)`，则检查 lockObject 是否可能为 null，添加非空守卫或改为 `private val lock = Any()`
   - 如果调用栈指向其他场景，根据具体情况定制修复方案

> **V3 删除**：
> - "为 AudioPlay/ImageProvider/ReadManga/CacheBook 的 synchronized(this) 块添加非空守卫"（object 单例 this 不可能为 null，方案无效）

**源码位置**（待调用栈重新分析后确认）：
- `app/src/main/java/io/legado/app/model/AudioPlay.kt` L149, L157 synchronized(this) 块（object 单例，this 非 null）
- `app/src/main/java/io/legado/app/model/CacheBook.kt` L383 synchronized(this) 块（object 单例，this 非 null）
- `app/src/main/java/io/legado/app/model/ImageProvider.kt` L69 synchronized(this) 块（object 单例，this 非 null）
- `app/src/main/java/io/legado/app/model/ReadManga.kt` L85, L107 synchronized(this) 块（object 单例，this 非 null）

### 3.2 Alternatives Considered（备选方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A1: 图片下载完全不取消 | bind()/loadImage() 时不再取消下载 | 会导致内存占用激增，ViewHolder 复用后旧下载仍持有引用，可能 OOM |
| A2: 图片用 Fresco 替换 Glide | 替换图片加载库 | 改动过大，破坏现有架构，jsoup/rhino 锁定原则下不宜引入新依赖 |
| A3: ExoPlayer 释放改为同步 release | releaseSniffResources 直接 release() | 同步 release 会阻塞 onDestroyView 主线程，可能 ANR |
| A4: LoadControl 固定 prioritizeTime=false | 永久关闭时间优先 | 牺牲正常网络下的 maxBuffer 时长有效性 |
| A5: 同 URL 切换直接 return | 完全忽略同 URL 切换 | 丢失用户 seekTo 意图，无法恢复播放位置 |
| A6: rssArticle 为 null 时 Toast 提示 | 仅提示用户重试 | 体验差（已从 toast 改为静默日志，BUG4 fix） |
| A7: synchronized 替换为 ReentrantLock | 全局替换锁实现 | 改动面过大，违反"精准修改"原则，且非空守卫已足够 |
| A8: LoadControl 运行时热切换 | dynamicLoadControl 方法 | 技术不可行，LoadControl 只能构建时设置（L86-88 注释） |

### 3.3 Drawbacks（已知缺点）

1. **FR-1 取消节流**：极端情况下会多占用带宽，但相比图片无法显示是可接受的折中
2. **FR-1 进度阈值**：Glide.downloadOnly 不暴露下载进度回调，需通过拦截器估算（存在误差）
3. **FR-2 同步 stop**：会增加 onDestroyView 主线程耗时（预计 < 5ms），但避免了渲染管线未及时断开的问题
4. **FR-3 isScopeCancelled**：新增标志位需在多处检查，增加了状态管理复杂度
5. **FR-5 档位修正延迟**：档位修正只在下次 prepare 生效，当前播放期间无法即时调整
6. **FR-6 switchToArticle 状态保护**：需正确处理异步加载取消，避免任务泄漏

---

## 4. Requirements（需求）

### FR-1: 图片下载取消策略优化（P0）

**需求描述**：快速滑动时图片下载不应被频繁取消，已下载超过阈值的图片应完成写入磁盘缓存。

**功能需求**：
- R-1.1: bind() L495 和 loadImage() L600 两处 cancelPendingDownload 调用点增加节流机制（同时覆盖两处）
- R-1.2: 若图片已下载超过阈值，则不取消（让请求完成写入磁盘缓存）
- R-1.3: preloadAround L323 增加 throttle 300ms，避免"取消 5 个 + 新发 5 个"同时发生
- R-1.4: 快速滑动时仅取消"离视口距离 > 2 屏"的 ViewHolder 下载
- R-1.5: 保持 preloadAround L326-340 activity destroyed 检查不变
- R-1.6: 保持 onRecycled L937-945 现有逻辑不变（不取消下载，只 clear photoView）

> **V2 删除**：R-1.1「onRecycled 时不立即取消，改为延迟 500ms 取消」已删除（onRecycled 根本不取消下载）

**非功能需求**：
- NFR-1.1: 不引入新的图片加载库依赖
- NFR-1.2: 不破坏现有 Glide.downloadOnly 磁盘缓存写入逻辑
- NFR-1.3: 内存占用不显著增加（节流期间下载连接数上限 ≤ 10）

**验收标准**：
- AC-1.1: 快速滑动后停止滑动，图片能在 1 秒内正常显示
- AC-1.2: "Cronet request canceled (normal)" 日志频次下降 ≥ 60%
- AC-1.3: "preloadAround skip: activity destroyed" 日志频次不上升（已有保护不变）
- AC-1.4: 无 OOM 发生（连续滑动 30 秒）
- AC-1.5: 节流期间最大并发连接数 ≤ 10

### FR-2: ExoPlayer 释放时序优化（P0）

**需求描述**：releaseSniffResources 应同步停止 mInternalPlayer 渲染管线，避免解码器/渲染器未及时断开。

**功能需求**：
- R-2.1: 在 releaseSniffResources() L408-416 中同步调用 `mInternalPlayer?.stop()`（runCatching 包裹）
- R-2.2: 在 releaseSniffResources() L408-416 中同步调用 `mInternalPlayer?.setPlayWhenReady(false)`（runCatching 包裹）
- R-2.3: 保持 scope.cancel() + isReleased=true 现有逻辑不变
- R-2.4: 保持 L414 bufferingTimeoutHandler.removeCallbacks 现有清理逻辑不变
- R-2.5: 不在 releaseSniffResources 中调用 release()（避免主线程阻塞）
- R-2.6: 实施前必须重新分析日志时间戳，确认延迟来源（super.reset() 或其他）

> **V2 修正**：代码片段 `player?.stop()` 中 `player` 变量未定义，修正为 `mInternalPlayer?.let { player -> player.stop(); player.playWhenReady = false }`

**验收标准**：
- AC-2.1: releaseSniffResources 后 mInternalPlayer 渲染管线立即停止（stop + setPlayWhenReady false）
- AC-2.2: onDestroyView 主线程耗时增加 < 10ms
- AC-2.3: 无 ANR 发生
- AC-2.4: 日志验证延迟来源（重新分析后确认）

### FR-3: 取消后忽略 ExoPlayer 回调（P1）

**需求描述**：scope cancelled 后 ExoPlayer 不应再触发 first frame rendered 和 STATE_READY 回调。

**功能需求**：
- R-3.1: 新增 `isScopeCancelled: AtomicBoolean` 标志位
- R-3.2: releaseSniffResources() 中设置 `isScopeCancelled.set(true)`
- R-3.3: `onPlaybackStateChanged` (L993) 检查 isScopeCancelled，为 true 则直接 return
- R-3.4: `onPlayerError` (L711) 检查 isScopeCancelled，为 true 则直接 return
- R-3.5: 首帧渲染回调 `onRenderedFirstFrame` (L1044) 检查 isScopeCancelled，为 true 则不渲染
- R-3.6: prepareAsync 成功后重置 `isScopeCancelled.set(false)`

> **V2 修正**：方法名 `onPlayerStateChanged` → `onPlaybackStateChanged` (L993)
> **职责说明**：isScopeCancelled 与 isReleased (L78) 职责不同——isReleased 防止 setMediaItem，isScopeCancelled 防止回调触发业务逻辑

**验收标准**：
- AC-3.1: scope cancelled 后不再出现 first frame rendered 日志
- AC-3.2: scope cancelled 后不再出现 STATE_READY 回调触发业务逻辑
- AC-3.3: prepareAsync 后标志位正确重置，下次播放回调正常

### FR-4: 切换文章/集数防抖（P1）

**需求描述**：切换文章/集数时，旧播放的 cancel 与新播放的 prepareAsync 竞争应被消除。

**功能需求**：
- R-4.0: **前置修改**——在 VideoPlay 中新增 `private var switchArticleJob: Job? = null` 和 `private var playEpisodeJob: Job? = null` 字段；switchToArticle 的 Coroutine.async 赋值给 switchArticleJob，playRssEpisode 的 Coroutine.async 赋值给 playEpisodeJob
- R-4.1: `switchToArticle` (L1126) 入口先 `switchArticleJob?.cancel()` 取消前一个异步任务，再执行新的 Coroutine.async
- R-4.2: `playRssEpisode` (L1284) 入口先 `playEpisodeJob?.cancel()` 取消前一个异步任务，再执行新的 Coroutine.async
- R-4.3: 保持 switchToArticle L1141-1153 source 匹配检查不变
- R-4.4: 防抖期间记录最后一次切换意图，异步加载完成后执行

> **V2 修正**：删除"switchVideo 时检查 currentUrl == newUrl"（switchVideo 不存在，currentUrl 字段不存在）。改为 switchToArticle L1126 / playRssEpisode L1284 真实锚点。
> **V3 补充**：新增 R-4.0 前置修改（Coroutine.async 未保存 Job 引用，源码核实 L1137/L1294）

**验收标准**：
- AC-4.1: 切换文章/集数时不再出现 cancel-prepare 10ms 内连续触发
- AC-4.2: 切换后播放位置正确恢复
- AC-4.3: 连续快速切换不导致任务泄漏

### FR-5: 连续慢 TTFB 强制降档（P1）

**需求描述**：连续 3 次 TTFB>1000ms 时强制降档，下次 prepare 使用降档后的档位构建 LoadControl（复用现有 PlayerInstancePool.createLoadControl 档位构建逻辑）。

**功能需求**：
- R-5.1: **不修改 PlayerInstancePool.createLoadControl**（L106-113 已有档位构建逻辑，调用 getCurrentBandwidthTier + createLoadControlByTier）
- R-5.2: 在 `Exo2MediaPlayer.onLoadCompleted` (L1105-1130) 中复用现有 loadElapsed 变量（TTFB），新增 `ttfbSlowCount` 计数器
- R-5.3: 连续 3 次 TTFB>1000ms 时调用 `getCurrentBandwidthTier()` 获取当前档位，若当前是 GOOD/MEDIUM 则强制降一档（GOOD→MEDIUM / MEDIUM→WEAK），记录到 `forceTier` 字段
- R-5.4: 降档后下次 `prepareAsyncInternal` 时 `PlayerInstancePool.acquire` 会按新档位构建 LoadControl（复用现有逻辑，不修改 acquire）
- R-5.5: 网络恢复（连续 3 次 TTFB<500ms）后重置 `ttfbSlowCount`，清除 `forceTier`，下次 prepare 时恢复自动档位
- R-5.6: 档位修正时记录日志

> **V3 重大修正**：
> - "prepare 前按带宽档位构建 LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113），不需要修改
> - "运行时动态切换 LoadControl"（技术不可行，L86-88 注释）
> - "新增 TTFB 统计"（L1084-1130 已完整实现，loadElapsed 变量可复用）
> - "prioritizeTime=true 导致快速起播"（概念错误，setPrioritizeTimeOverSizeThresholds 是时间优先于字节）

**验收标准**：
- AC-5.1: 连续 TTFB>1000ms 场景下，下次 prepare 使用降档后的档位，BUFFERING→READY 循环次数下降 ≥ 50%
- AC-5.2: 网络恢复后自动恢复自动档位
- AC-5.3: 档位修正时无 crash

### FR-6: switchToArticle 状态保护（P2）

**需求描述**：switchToArticle 异步加载期间的状态保护，避免异步加载期间 rssArticle 临时为 null 导致空转。

**功能需求**：
- R-6.0: **前置修改**（与 FR-4 共享）——在 VideoPlay 中新增 `private var switchArticleJob: Job? = null` 字段；switchToArticle 的 Coroutine.async 赋值给 switchArticleJob
- R-6.1: switchToArticle 进入异步加载时设置 `isSwitchingArticle = true` 标志
- R-6.2: 异步加载完成（startPlay 调用前）清除标志
- R-6.3: 若异步加载期间用户再次触发切换，通过 `switchArticleJob?.cancel()` 取消前一个异步任务（依赖 R-6.0 前置修改）
- R-6.4: 保持 startPlay L353-359 rssArticle null 静默日志逻辑不变
- R-6.5: **预期行为**：异步任务被取消后，withContext(Main) 中的 startPlay 不会执行（用户切换到新文章时，旧文章的加载应该被取消）

> **V2 删除**：
> - "rssArticle 为 null 时不立即返回，注册回调自动播放"（会把正常流程当 bug 修，引入副作用）
> - "显示 loading indicator"（不在本 FR 范围）
> - "超时 10 秒提示"（不在本 FR 范围）
> **V3 补充**：新增 R-6.0 前置修改（依赖 FR-4 的 switchArticleJob 字段）

**验收标准**：
- AC-6.1: switchToArticle 异步加载期间再次切换，前一个异步任务被取消
- AC-6.2: 无任务泄漏（连续切换 20 次无协程堆积）
- AC-6.3: startPlay 现有静默日志逻辑保持不变

### FR-7: NullPointerException(monitor-enter) 调用栈重新分析（P2）

**需求描述**：NullPointerException(monitor-enter) 异常应被消除，需重新分析调用栈定位真实根因。

**功能需求**：
- R-7.1: **Step 1**——重新分析 logs(9) 中 NullPointerException(monitor-enter) 的完整调用栈
- R-7.2: **Step 2**——根据调用栈定位真实锁对象（可能是 synchronized(lockObject) 中 lockObject 为 null，或 Java 字节码 monitorenter 指令操作数栈为 null，或其他场景）
- R-7.3: **Step 3**——根据锁对象类型决定修复方案：
  - 若调用栈指向 @Synchronized 注解方法（等价 synchronized(this)），this 不可能为 null（object 单例），需分析其他原因（GC 残留引用、object 初始化未完成等）
  - 若调用栈指向 synchronized(lockObject)，检查 lockObject 是否可能为 null，添加非空守卫或改为 `private val lock = Any()`
  - 其他场景根据具体情况定制修复方案
- R-7.4: 排查 AudioPlay.kt L149, L157 / CacheBook.kt L383 / ImageProvider.kt L69 / ReadManga.kt L85, L107 的 synchronized(this) 块（object 单例，this 非 null，仅作参考排查）

> **V3 重大修正**：
> - AudioPlay/ImageProvider/ReadManga/CacheBook 都是 object 单例（源码核实），this 不可能为 null
> - "为 synchronized(this) 块添加非空守卫"方案无效，已删除
> - 改为"调用栈重新分析 → 定位真实锁对象 → 根据锁对象类型决定修复方案"三步流程

**验收标准**：
- AC-7.1: 连续切换视频 20 次，无 NullPointerException(monitor-enter)
- AC-7.2: Activity 销毁重建过程中无并发异常

---

## 5. Scenarios（场景）

### 场景 1：快速滑动图片画布

**前置条件**：打开一本图片书（漫画/图集），进入图片画布模式

**操作**：快速滑动持续 10 秒后停止

**预期**：
- 滑动过程中下载不被频繁取消
- 停止滑动后，可见区域图片在 1 秒内正常显示
- 已下载超过阈值的图片能完整写入磁盘缓存，下次查看无需重新下载

### 场景 2：切换视频（不同文章）

**前置条件**：正在播放视频 A，切换到视频 B

**操作**：点击切换到视频 B

**预期**：
- releaseSniffResources 同步停止 mInternalPlayer 渲染管线
- 无 first frame rendered 在 cancelled 后触发
- 视频 B 正常起播

### 场景 3：切换视频（同文章不同集数）

**前置条件**：正在播放视频，切换到另一集

**操作**：点击切换集数

**预期**：
- playRssEpisode 防抖检查生效
- 无 cancel-prepare 10ms 内连续触发
- 切换后播放位置正确恢复

### 场景 4：连续快速切换文章

**前置条件**：正在播放视频，快速切换多个文章

**操作**：短时间内连续切换 3 个文章

**预期**：
- switchToArticle 防抖检查生效，取消前一个异步任务
- 只执行最后一次切换
- 无任务泄漏

### 场景 5：息屏恢复

**前置条件**：正在播放视频，息屏 30 秒后亮屏

**操作**：亮屏恢复

**预期**：
- ExoPlayer 正常恢复播放
- 无 isScopeCancelled 标志位残留导致无法恢复
- 无 NullPointerException

### 场景 6：弱网络环境播放

**前置条件**：TTFB 持续 > 1000ms

**操作**：播放视频

**预期**：
- 连续 3 次 TTFB>1000ms 后标记强制降档
- 下次 prepare 使用 WEAK 档位（小 buffer 快起播）
- BUFFERING→READY 循环次数下降 ≥ 50%
- 网络恢复后自动恢复自动档位

### 场景 7：switchToArticle 异步加载期间再次切换

**前置条件**：正在切换文章 A，异步加载未完成

**操作**：再次切换到文章 B

**预期**：
- 文章 A 的异步任务被取消
- 执行文章 B 的切换
- 无任务泄漏

### 场景 8：Activity 销毁重建

**前置条件**：正在播放视频，旋转屏幕或切换 Activity

**操作**：触发 Activity 销毁重建

**预期**：
- 无 NullPointerException(monitor-enter)
- 全局单例状态正确恢复
- 无并发同步异常

---

## 6. 约束与依赖

### 6.1 技术约束
- jsoup 1.16.2 锁定，不可升级
- rhino 1.8.1 锁定，不可升级
- hutool 5.8.22 锁定，不可升级
- ReadBook 全局单例多 Activity 共享，改状态需 @Synchronized 或 Mutex 保护
- ExoPlayer LoadControl 只能在 player 构建时设置，运行时不可热切换（ExoPlayerHelper.kt L86-88）

### 6.2 流程依赖
- 必须使用 ai_tests/scripts/ 固定脚本测试
- 必须使用测试包（`io.legado.miss.app.debug`）真机验证
- 完成后必须更新 assets/updateLog.md

### 6.3 回归检查
- 必须对比原版 legado-E 行为
- 必须验证与原版共存包（`io.legado.app.debug`）无冲突

---

## 7. 验收标准汇总

| FR | 关键验收指标 | 测量方法 |
|----|------------|---------|
| FR-1 | "Cronet request canceled" 下降 ≥ 60% | logcat 日志统计 |
| FR-1 | "preloadAround skip: activity destroyed" 不上升 | logcat 日志统计 |
| FR-1 | 节流期间并发连接数 ≤ 10 | 日志验证 |
| FR-2 | releaseSniffResources 后 mInternalPlayer 停止 | 日志验证 |
| FR-2 | onDestroyView 主线程耗时增加 < 10ms | 日志时间戳 |
| FR-3 | cancelled 后无 first frame rendered | logcat 日志验证 |
| FR-3 | prepareAsync 后标志位重置 | 日志验证 |
| FR-4 | 切换文章/集数无 cancel-prepare 竞争 | logcat 日志验证 |
| FR-5 | 连续慢 TTFB 强制降档后 BUFFERING→READY 循环下降 ≥ 50% | logcat 日志统计 |
| FR-5 | 网络恢复自动恢复自动档位 | 真机验证 |
| FR-6 | switchToArticle 异步任务取消无泄漏 | 日志验证 |
| FR-7 | 无 NullPointerException(monitor-enter) | logcat 日志验证 |

---

## V3修订记录（2026-07-31）

> **修订背景**：V2重构后交叉验证审查发现3个高优先级阻塞点，V3修复后直接进入实施阶段。

### 修订1：FR-5重新定义为"连续慢TTFB强制降档"

- **根因**：源码核实发现"prepare前按带宽档位构建LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113 + acquire L136）
- **修改内容**：
  - Scope部分：网络层范围改为"连续慢TTFB强制降档（复用现有PlayerInstancePool.createLoadControl档位构建逻辑）"
  - Approach部分：FR-5重新定义，明确"不修改PlayerInstancePool.createLoadControl"，只在onLoadCompleted新增ttfbSlowCount降档判断
  - Requirements部分：FR-5需求改为R-5.1（不修改PlayerInstancePool）+ R-5.2（复用loadElapsed）+ R-5.3（降档判断）+ R-5.4（acquire复用）+ R-5.5（恢复）+ R-5.6（日志）
  - 验收标准：AC-5.1改为"连续TTFB>1000ms场景下，下次prepare使用降档后的档位"

### 修订2：FR-7重新定义为"调用栈重新分析"

- **根因**：源码核实发现AudioPlay/ImageProvider/ReadManga/CacheBook都是object单例，this不可能为null，"添加非空守卫"方案无效
- **修改内容**：
  - Approach部分：FR-7重新定义，删除"添加非空守卫"方案，改为三步流程（重新分析调用栈→定位真实锁对象→根据锁对象类型决定修复方案）
  - Requirements部分：FR-7需求改为R-7.1（Step1重新分析调用栈）+ R-7.2（Step2定位真实锁对象）+ R-7.3（Step3决定修复方案）+ R-7.4（参考排查位置）
  - Scope部分：图片层范围改为"synchronized(this)块调用栈重新分析（object单例this非null，非空守卫无效）"

### 修订3：FR-4/FR-6补充Job引用前置修改

- **根因**：源码核实发现switchToArticle L1137 / playRssEpisode L1294的Coroutine.async未保存Job引用，"取消前一个异步任务"需先修改保存Job作为前置条件
- **修改内容**：
  - FR-4 Approach部分：新增前置修改说明（switchArticleJob/playEpisodeJob字段），FR-4方案改为switchToArticle开始时先switchArticleJob?.cancel()
  - FR-4 Requirements部分：新增R-4.0前置修改
  - FR-6 Approach部分：新增前置修改说明（依赖FR-4的switchArticleJob字段），FR-6方案补充预期行为（异步任务被取消后withContext(Main)中startPlay不执行）
  - FR-6 Requirements部分：新增R-6.0前置修改 + R-6.5预期行为
