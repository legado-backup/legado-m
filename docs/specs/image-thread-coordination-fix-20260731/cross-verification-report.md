# 独立交叉验证报告（第二轮审查）

> **审查对象**: image-thread-coordination-fix-20260731 V2 四文档
> **审查方法**: 独立读取源码核实（不信任文档声明），对照 6 个关键源码文件逐行验证
> **审查日期**: 2026-07-31
> **审查目的**: 与 openspec-document-auditor V1 审查结果对比，发现认知偏差/遗漏分析/技术可行性问题
> **审查结论**: ⚠️ **V2 已修复 V1 的 12 个 ERROR，但独立交叉验证发现 3 个新认知偏差 + 4 个新遗漏 + 2 个技术可行性待商榷点**

---

## 1. 交叉验证结论速览

### 1.1 独立核实统计

| 维度 | 独立核实项数 | 与文档一致 | 与文档不一致 | 新发现问题 |
|------|------------|----------|------------|----------|
| ImageCanvasAdapter.kt | 8 | 8 | 0 | 0 |
| Exo2MediaPlayer.kt | 12 | 11 | 1（FR-5 LoadControl 构建点描述偏差） | 1（遗漏 isPreparing） |
| ExoPlayerHelper.kt | 8 | 8 | 0 | 0 |
| PlayerInstancePool.kt | 3 | 1 | 2（FR-5 遗漏 createLoadControl 中间层 + recycle 已有 stop） | 2 |
| VideoFragment.kt | 3 | 3 | 0 | 0 |
| VideoPlay.kt | 6 | 6 | 0 | 1（switchToArticle 未保存 Job） |
| model 目录 synchronized | 6 | 6 | 0 | 1（this 不可能为 null） |

### 1.2 问题分级统计

| 级别 | 数量 | 说明 |
|------|------|------|
| **认知偏差（CV-BIAS）** | 3 | FR-5 LoadControl 构建点描述偏差 / FR-7 synchronized(this) 守卫无效 / FR-2 遗漏 recycle 已有 stop |
| **遗漏分析（CV-MISS）** | 4 | isPreparing CAS 守卫 / switchToArticle Job 未保存 / prepareAsyncInternal 重复初始化检测 / release 双保险强调不足 |
| **技术可行性待商榷（CV-FEAS）** | 2 | FR-5 核心方案已是现有行为 / FR-7 排查方向仍偏离 |
| **V1 ERROR 修复确认** | 12/12 | V1 的 12 个 ERROR 在 V2 中均已修正 |

### 1.3 整体判定

⚠️ **有条件可进入实施阶段**

- V1 的 12 个阻断级 ERROR 已全部修复（路径/方法名/锚点/概念错误均修正）
- 但 FR-5 和 FR-7 的方案描述仍存在认知偏差，实施前需修正方案描述（不需重构文档结构）
- FR-2/FR-3/FR-4/FR-6 方案可落地，但需补充遗漏的前置条件

---

## 2. 认知偏差发现

### CV-BIAS-1（高）：FR-5 LoadControl 构建点描述偏差——遗漏 PlayerInstancePool.createLoadControl() 中间层

**文档声明**（spec.md L180-184 / design.md L222-226 / tasks.md L124-125）：
> "在 prepareAsyncInternal 中调用 `getCurrentBandwidthTier()` + `createLoadControlByTier(tier)` 构建 LoadControl（复用现有逻辑）"

**源码实际**（独立核实）：

1. `Exo2MediaPlayer.kt` L540-542（prepareAsyncInternal 内）：
   ```kotlin
   if (mLoadControl == null) {
       mLoadControl = PlayerInstancePool.createLoadControl()
   }
   ```
   - 调用的是 `PlayerInstancePool.createLoadControl()`，**不是**直接调用 `ExoPlayerHelper.getCurrentBandwidthTier()` + `createLoadControlByTier()`
   - 且有 `if (mLoadControl == null)` 守护——一旦创建就复用，不会每次 prepare 都重建

2. `PlayerInstancePool.kt` L106-112（createLoadControl 实现）：
   ```kotlin
   fun createLoadControl(): DefaultLoadControl {
       val tier = ExoPlayerHelper.getCurrentBandwidthTier()
       AppLog.put("PlayerPool: createLoadControl (new instance), tier=$tier, ...")
       return ExoPlayerHelper.createLoadControlByTier(tier, sharedAllocator)
   }
   ```
   - **这里才真正调用了 getCurrentBandwidthTier + createLoadControlByTier**

3. `PlayerInstancePool.kt` L122-136（acquire 构建 ExoPlayer）：
   ```kotlin
   fun acquire(looper: Looper): ExoPlayer {
       ...
       .setLoadControl(createLoadControl())  // L136
       ...
   }
   ```
   - LoadControl 在 acquire 构建 ExoPlayer 时设置

**认知偏差本质**：
- 文档说"在 prepareAsyncInternal 中调用"，但实际调用链是 `prepareAsyncInternal → PlayerInstancePool.createLoadControl → ExoPlayerHelper.getCurrentBandwidthTier + createLoadControlByTier`
- 文档遗漏了 `PlayerInstancePool.createLoadControl()` 这个关键中间层
- 更重要的是：`prepareAsyncInternal` 中是 `if (mLoadControl == null)` 守护，意味着只有第一次 prepare（或 mLoadControl 被清空后）才会创建 LoadControl，后续 prepare 复用同一个 mLoadControl
- 但 ExoPlayer 实例是从池中 acquire 的，acquire 时会 `.setLoadControl(createLoadControl())`——所以每次 acquire 新 ExoPlayer 实例时，LoadControl 都是按当时带宽档位新建的

**影响**：
- FR-5 的核心方案"prepare 前按带宽档位构建 LoadControl（复用现有 createLoadControlByTier）"**已经是现有行为**（通过 acquire → createLoadControl 实现）
- 文档的方案描述会误导实施者直接在 prepareAsyncInternal 中调用，而忽略了 `if (mLoadControl == null)` 守护和 PlayerInstancePool 中间层
- FR-5 真正需要新增的只是"连续 3 次 TTFB>1000ms 标记强制降档"判断（这部分是新逻辑）

**整改建议**：
1. FR-5 方案描述修正为："复用现有 `PlayerInstancePool.acquire → createLoadControl → getCurrentBandwidthTier + createLoadControlByTier` 链路（已实现按带宽档位构建），新增'连续 3 次 TTFB>1000ms 标记强制降档'判断，在 acquire 时读取强制降档标记覆盖自动档位"
2. 明确说明：`prepareAsyncInternal` 中 `if (mLoadControl == null)` 守护意味着 mLoadControl 一旦创建就复用，但每次 acquire 新 ExoPlayer 实例时会重新构建 LoadControl
3. 强制降档标记的读取点应放在 `PlayerInstancePool.createLoadControl()` 中（L107-108 之间），而非 prepareAsyncInternal

---

### CV-BIAS-2（高）：FR-7 synchronized(this) 非空守卫无效——this 不可能为 null

**文档声明**（spec.md L396-401 / design.md L506-517 / tasks.md L172-175）：
> "为 AudioPlay/CacheBook/ImageProvider/ReadManga 的 synchronized(this) 块添加非空守卫或改为使用 `private val lock = Any()` 替代"
> R-7.6: "synchronized(this) 块前判断 this != null（理论上 this 不可能为 null，需排查是否为其他 lock 对象）"

**源码实际**（独立核实）：

1. Grep 确认 model 目录所有 synchronized 块均为 `synchronized(this)` 形式（6 处）：
   - AudioPlay.kt L149, L157（addLoading/removeLoading）
   - CacheBook.kt L383（downloadAwait）
   - ImageProvider.kt L69（onItemEvicted 回调）
   - ReadManga.kt L85, L107（upBook/upData）
   - **没有 `synchronized(其他字段)` 形式**

2. 类声明核实：
   - `ImageProvider.kt` L31: `object ImageProvider` —— object 单例
   - AudioPlay/CacheBook/ReadManga 同样是 object 单例
   - **object 单例的 this 永远不为 null**

**认知偏差本质**：
- `synchronized(this)` 中的 `this` 是对象实例引用，**理论上不可能为 null**
- 在 `synchronized(this)` 前加 `if (this != null)` 永远为 true，毫无意义
- 文档 R-7.6 已承认"理论上 this 不可能为 null"，但方案仍是"添加非空守卫"——自相矛盾
- 改为 `private val lock = Any()` 不会改变行为（lock 对象同样不可能为 null），只是换了个锁对象

**NullPointerException(monitor-enter) 真实根因假设**（V1 遗漏-4 已提及，V2 未解决）：
- monitor-enter NPE 不可能来自 `synchronized(this)`（this 不为 null）
- 真实根因可能是：
  - Java 字节码层面的 monitor 指令（可能与 Kotlin 属性 getter lazy 初始化有关）
  - 某个非 model 目录的 `synchronized(field)` 中 field 为 null
  - 或者是 `ConcurrentHashMap` 等容器的内部 monitor
- 需重新分析 NullPointerException 调用栈定位真实锁对象

**影响**：
- FR-7 的方案"添加非空守卫"对 `synchronized(this)` 完全无效
- 实施 FR-7 会浪费时间在无效的守卫上，真实 NPE 根因未解决

**整改建议**：
1. FR-7 方案修正为："重新分析 NullPointerException(monitor-enter) 调用栈，定位真实锁对象（不是 model 目录的 synchronized(this) 块）"
2. 删除"为 synchronized(this) 块添加非空守卫"的无效方案
3. 若调出栈定位到真实锁对象是某个字段，再针对性修复

---

### CV-BIAS-3（中）：FR-2 遗漏 PlayerInstancePool.recycle 已有 stop

**文档声明**（spec.md L96-98 / design.md L124-139）：
> "releaseSniffResources 未同步停止 mInternalPlayer 渲染管线，导致解码器/渲染器未立即断开"

**源码实际**（独立核实）：

1. `PlayerInstancePool.kt` L167-193（recycle 实现）：
   ```kotlin
   @Synchronized
   fun recycle(player: ExoPlayer) {
       kotlin.runCatching {
           player.stop()           // L170 ← 已有 stop！
           player.clearMediaItems()
           player.clearVideoSurface()
           ...
           player.playWhenReady = false  // L177 ← 已有 setPlayWhenReady(false)！
       }.onFailure { ... }
       ...
   }
   ```

2. `Exo2MediaPlayer.kt` L454-467（release 调用链）：
   ```kotlin
   override fun release() {
       releaseSniffResources()  // L455 双保险
       mInternalPlayer?.let { player ->
           detachFromPlayer(player)
           PlayerInstancePool.recycle(player)  // L458 → 内部已有 stop + setPlayWhenReady(false)
           mInternalPlayer = null
       }
       super.reset()
   }
   ```

**认知偏差本质**：
- 文档说"releaseSniffResources 未同步停止 mInternalPlayer"——这句话本身正确（L408-416 确实没有 stop）
- 但文档没提到 `PlayerInstancePool.recycle` L170/L177 已经有 `player.stop()` + `player.playWhenReady = false`
- recycle 是在 `release()` L458 调用，而 release 是在 `releasePlayer()` L334 → `_playerView?.currentPlayer?.release()` 触发
- 调用顺序：`onDestroyView L202 releaseSniffResources` → `L203 releasePlayer` → `Exo2MediaPlayer.release L454` → `PlayerInstancePool.recycle L167` → `player.stop() L170`

**影响**：
- FR-2 方案合理（让 stop 更早发生在 releaseSniffResources 中，而非等到 recycle），但文档没提到 recycle 已有 stop，可能让实施者误以为现有代码完全没有 stop
- 实际上 mInternalPlayer 的 stop 只是"延后"到 recycle 执行，并非"完全没有 stop"
- FR-2 的价值在于"提前 stop"（从 recycle 提前到 releaseSniffResources），减少 releaseSniffResources 到 recycle 之间的渲染管线活动窗口

**整改建议**：
1. design.md 补充说明："PlayerInstancePool.recycle L170 已有 player.stop() + L177 setPlayWhenReady(false)，但在 release() L458 才调用。FR-2 的价值是将 stop 提前到 releaseSniffResources（L202），减少 releaseSniffResources 到 recycle 之间的渲染管线活动窗口"
2. 避免实施者误以为现有代码完全没有 stop

---

## 3. 遗漏分析发现

### CV-MISS-1（中）：遗漏 isPreparing AtomicBoolean CAS 守卫

**源码实际**（Exo2MediaPlayer.kt L81-89）：
```kotlin
/**
 * V-003-P0-2: prepareAsyncInternal 重入保护
 * 根因：R5 网络抓包命中后可能多次回调 prepareAsyncInternal（003 日志 9~16ms 内重入），
 * 导致 PlayerInstancePool.acquire 被调用两次，创建多个 ExoPlayer 实例竞争 + TrackSelector 崩溃。
 * 方案：AtomicBoolean CAS 守卫，第一次进入设置 true，post Runnable 完成后重置 false。
 * 重入时跳过并记录日志。
 */
private val isPreparing = java.util.concurrent.atomic.AtomicBoolean(false)
```

**文档遗漏**：
- V2 四文档完全没提到 `isPreparing` (L89) 这个现有的重入保护机制
- FR-3 新增 `isScopeCancelled` 标志位，但没说明与 `isReleased` (L78) + `isPreparing` (L89) 的三重职责差异

**三个标志位职责差异**（应补充到文档）：
| 标志位 | 位置 | 职责 | 触发点 |
|--------|------|------|--------|
| `isReleased` | L78 | 防止 setMediaItem（applyMediaSourceByType 入口检查） | releaseSniffResources |
| `isPreparing` | L89 | 防止 prepareAsyncInternal 重入（CAS 守卫） | prepareAsyncInternal 入口 |
| `isScopeCancelled`（新增） | - | 防止回调触发业务逻辑 | releaseSniffResources |

**影响**：
- 实施者可能误以为只有 isReleased 一个现有标志位，新增 isScopeCancelled 时职责划分不清
- FR-4 的防抖与 isPreparing 的重入保护有部分功能重叠（都防止短时间内重复调用），文档未说明差异

**整改建议**：design.md AD-03 补充 isPreparing 的存在，说明三标志位职责差异

---

### CV-MISS-2（高）：遗漏 switchToArticle/playRssEpisode 的 Coroutine.async 未保存 Job 引用

**源码实际**：
- `VideoPlay.kt` L1137（switchToArticle 内）：
  ```kotlin
  Coroutine.async(loadScope, IO) {
      // 异步查询 rssStar/rssRecord + 加载视频信息
      ...
      withContext(Main) { startPlay(player) }
  }.onError { ... }
  ```
  **没有保存返回的 Job 引用**

- `VideoPlay.kt` L1294（playRssEpisode 内）：
  ```kotlin
  Coroutine.async(loadScope, IO) {
      ...
  }.onError { ... }
  ```
  **同样没有保存 Job 引用**

**文档遗漏**：
- FR-6 R-6.3 说"若异步加载期间用户再次触发切换，取消前一个异步任务"
- FR-4 R-4.1 说"switchToArticle 入口增加防抖检查，短时间内连续切换取消前一个异步任务"
- 但两个 FR 都没提到：**当前 switchToArticle/playRssEpisode 的 Coroutine.async 没有保存 Job 引用，无法直接 cancel**

**影响**：
- 实施 FR-4/FR-6 的"取消前一个异步任务"时，必须先修改 switchToArticle/playRssEpisode 保存 Job 引用（如 `private var switchArticleJob: Job? = null`）
- 这是前置修改，文档未提及，实施时可能遗漏导致无法取消

**整改建议**：
1. FR-4/FR-6 详细变更补充前置修改："新增字段 `private var switchArticleJob: Job? = null`，switchToArticle L1137 的 Coroutine.async 赋值给 switchArticleJob，入口检查 `switchArticleJob?.isActive == true` 时先 cancel"
2. playRssEpisode 同理新增 `private var playEpisodeJob: Job? = null`

---

### CV-MISS-3（中）：遗漏 prepareAsyncInternal 重复初始化检测

**源码实际**（Exo2MediaPlayer.kt L504-512）：
```kotlin
if (currentUrl == lastPrepareUrl && currentHeaders == lastPrepareHeaders
    && currentSniffJob?.isActive == true
) {
    AppLog.put("ExoPlayer prepareAsyncInternal: skip duplicate call (same url+headers, sniffJob active)")
    return@post
}
lastPrepareUrl = currentUrl
lastPrepareHeaders = currentHeaders
```

**文档遗漏**：
- prepareAsyncInternal 已有"同一 URL+headers 且嗅探协程仍活跃 → 跳过"的重复初始化检测
- 这与 FR-4 的防抖有部分功能重叠（都防止短时间内重复调用）
- 文档 FR-4 没提到这个现有检测机制

**影响**：
- 实施 FR-4 防抖时需注意与现有重复初始化检测的协同
- 对于"同 URL+headers"场景，现有检测已处理；FR-4 防抖主要针对"不同 URL 快速连续切换"场景

**整改建议**：FR-4 方案补充说明："prepareAsyncInternal L504-512 已有同 URL+headers 重复检测，FR-4 防抖针对不同 URL 快速连续切换场景"

---

### CV-MISS-4（低）：release() 双保险调用链强调不足

**源码实际**（Exo2MediaPlayer.kt L454-467）：
```kotlin
override fun release() {
    releaseSniffResources()  // L455 双保险（内部 isReleased 防重复跳过）
    mInternalPlayer?.let { player ->
        detachFromPlayer(player)
        PlayerInstancePool.recycle(player)
        mInternalPlayer = null
    }
    super.reset()
}
```

**文档现状**：
- design.md 4.2 数据流图提到了 `releaseSniffResources() 双保险（被 isReleased 防重复跳过）`
- 但 tasks.md 和 spec.md 没有强调这个双保险机制

**影响**：低。实施者读 design.md 可理解，但 spec.md/tasks.md 未提及可能导致理解不完整。

**整改建议**：spec.md FR-2 方案补充调用链说明

---

## 4. 技术可行性独立评估（逐 FR）

### FR-1: 图片下载取消策略优化（P0）—— ✅ 可行

| 评估项 | 独立核实结论 |
|--------|------------|
| bind L495 取消点 | ✅ 属实（L466 bind → L495 cancelPendingDownload） |
| loadImage L600 取消点 | ✅ 属实（L599 loadImage → L600 cancelPendingDownload） |
| onRecycled 不取消 | ✅ 属实（L937-945 只 clear photoView + 重置字段） |
| cancelPendingDownload 实现 | ✅ 属实（L549-554：clear downloadTarget + 置 null） |
| preloadAround activity destroyed 检查 | ✅ 属实（L326-340，crash-2026-07-26 铁证） |
| 进度阈值 60% 可行性 | ⚠️ Glide.downloadOnly 不暴露进度回调，需拦截器估算（文档 Drawbacks 已承认误差，诚实） |

**结论**：方案可行，两处取消点修改 + 节流 + 可见性优先级可落地。进度阈值需通过拦截器估算，存在 ±10% 误差，但文档已诚实承认。

---

### FR-2: ExoPlayer 释放时序优化（P0）—— ✅ 可行（需补充说明）

| 评估项 | 独立核实结论 |
|--------|------------|
| releaseSniffResources 无 stop | ✅ 属实（L408-416 只有 scope.cancel + removeCallbacks + isReleased） |
| mInternalPlayer 是父类 protected 字段 | ✅ 可访问（子类 Exo2MediaPlayer 可访问） |
| 代码片段 `mInternalPlayer?.let { player -> ... }` | ✅ 正确（V2 已修正 player 未定义错误） |
| onDestroyView 同步连续无延迟 | ✅ 属实（L202-203 同步连续） |
| recycle 已有 stop | ⚠️ 文档未提（见 CV-BIAS-3） |

**结论**：方案可行。在 releaseSniffResources 中加 `mInternalPlayer?.stop()` + `setPlayWhenReady(false)` 可立即断开渲染管线。需补充说明 recycle L170 已有 stop，FR-2 价值在于"提前 stop"。

---

### FR-3: 取消后忽略 ExoPlayer 回调（P1）—— ✅ 可行

| 评估项 | 独立核实结论 |
|--------|------------|
| onPlaybackStateChanged L993 | ✅ 属实（不是 onPlayerStateChanged） |
| onPlayerError L711 | ✅ 属实 |
| onRenderedFirstFrame L1044 | ✅ 属实 |
| isReleased L78 职责 | ✅ 用于 applyMediaSourceByType 入口检查 |
| isScopeCancelled 职责差异 | ✅ 与 isReleased 不重叠（防止回调 vs 防止写入） |
| isPreparing L89 遗漏 | ⚠️ 文档未提（见 CV-MISS-1） |

**结论**：方案可行。isScopeCancelled 与 isReleased 职责不同，不复用合理。需补充 isPreparing 的存在说明。

---

### FR-4: 切换文章/集数防抖（P1）—— ✅ 可行（需补充前置修改）

| 评估项 | 独立核实结论 |
|--------|------------|
| switchToArticle L1126 | ✅ 属实 |
| playRssEpisode L1284 | ✅ 属实 |
| switchToArticle 已有 source 匹配检查 | ✅ 属实（L1141-1153） |
| videoUrl 字段 L220 | ✅ 属实（不是 currentUrl） |
| Coroutine.async 未保存 Job | ❌ 文档未提（见 CV-MISS-2） |
| prepareAsyncInternal 重复检测 | ⚠️ 文档未提（见 CV-MISS-3） |

**结论**：方案可行，但需补充前置修改：switchToArticle/playRssEpisode 的 Coroutine.async 需保存 Job 引用才能实现取消。

---

### FR-5: LoadControl 按带宽档位构建（P1）—— ⚠️ 部分不可行/方案描述误导

| 评估项 | 独立核实结论 |
|--------|------------|
| LoadControl 不可热切换注释 L86-88 | ✅ 属实 |
| bandwidthMeter L92-94 | ✅ 属实 |
| BandwidthTier 枚举 L99-103 | ✅ 属实 |
| getCurrentBandwidthTier L110-117 | ✅ 属实 |
| createLoadControlByTier L137-174 | ✅ 属实 |
| setPrioritizeTimeOverSizeThresholds 概念 | ✅ V2 已修正（时间优先于字节，非快速起播） |
| bufferForPlayback 500ms/800ms/500ms | ✅ 属实（L152/157/162） |
| TTFB 统计 L1084-1130 | ✅ 属实（onLoadStarted L1090 + onLoadCompleted L1105） |
| **"在 prepareAsyncInternal 中调用"** | ❌ **描述偏差**（见 CV-BIAS-1） |
| **PlayerInstancePool.createLoadControl 中间层** | ❌ **遗漏** |

**结论**：⚠️ FR-5 的核心方案"prepare 前按带宽档位构建 LoadControl"**已经是现有行为**（通过 `PlayerInstancePool.acquire → createLoadControl → getCurrentBandwidthTier + createLoadControlByTier` 实现）。文档的方案描述"在 prepareAsyncInternal 中调用"会误导实施者。

FR-5 真正需要新增的只是：
1. "连续 3 次 TTFB>1000ms 标记强制降档"判断（新逻辑）
2. "连续 3 次 TTFB<500ms 清除强制降档标记"判断（新逻辑）
3. 强制降档标记的读取点应放在 `PlayerInstancePool.createLoadControl()` 中

**整改建议**：见 CV-BIAS-1 整改建议

---

### FR-6: switchToArticle 状态保护（P2）—— ✅ 可行（需补充前置修改）

| 评估项 | 独立核实结论 |
|--------|------------|
| switchToArticle L1126-1167 | ✅ 属实 |
| startPlay L308-360 rssArticle null 静默日志 | ✅ 属实（L353-359 BUG4 fix） |
| switchToArticle 异步加载 Coroutine.async | ✅ 属实（L1137） |
| Coroutine.async 未保存 Job | ❌ 文档未提（见 CV-MISS-2） |

**结论**：方案可行，但需补充前置修改：switchToArticle 的 Coroutine.async 需保存 Job 引用才能实现"取消前一个异步任务"。

---

### FR-7: NullPointerException(monitor-enter) 修复（P2）—— ❌ 排查方向仍偏离

| 评估项 | 独立核实结论 |
|--------|------------|
| ImagePlay 无 synchronized() 块 | ✅ V2 已修正（只有 @Synchronized 注解） |
| AudioPlay/ImageProvider/ReadManga/CacheBook 有 synchronized(this) | ✅ 属实（6 处） |
| **synchronized(this) 中 this 是否可能为 null** | ❌ **不可能**（object 单例，见 CV-BIAS-2） |
| **添加非空守卫是否有效** | ❌ **无效**（this != null 永远为 true） |

**结论**：❌ FR-7 的排查方向仍有问题。虽然 V2 修正了"ImagePlay → AudioPlay 等"的方向，但新方向"synchronized(this) 块添加非空守卫"仍然无效，因为 object 单例的 this 不可能为 null。

NullPointerException(monitor-enter) 的真实根因需重新分析调用栈定位，不应在 synchronized(this) 上浪费时间。

**整改建议**：见 CV-BIAS-2 整改建议

---

## 5. 文档一致性问题

### 5.1 四文档一致性检查

| 检查项 | README | spec | design | tasks | 一致性 |
|--------|--------|------|--------|-------|--------|
| FR 数量 | 7 | 7 | 7 | 7 | ✅ 一致 |
| FR 编号 | FR-1~7 | FR-1~7 | FR-1~7 | FR-1~7 | ✅ 一致 |
| 源码路径 | 真实路径 | 真实路径 | 真实路径 | 真实路径 | ✅ 一致（V2 已修正） |
| bind 行号 | L466/L495 | L466/L495 | L466/L495 | L466/L495 | ✅ 一致 |
| releaseSniffResources 行号 | L408-416 | L408-416 | L408-416 | L408-416 | ✅ 一致 |
| onRecycled 行号 | L937-945 | L937-945 | L937-945 | L937-945 | ✅ 一致 |
| onPlaybackStateChanged 行号 | L993 | L993 | L993 | L993 | ✅ 一致 |
| switchToArticle 行号 | L1126 | L1126 | L1126 | L1126 | ✅ 一致 |
| 验收标准 | 7 项 | 7 项 | 未列 | 21 项 | ⚠️ tasks 最详细（可接受） |

### 5.2 行号偏差检查

独立核实关键行号，与文档声明对比：

| 文档声明 | 独立核实 | 偏差 |
|---------|---------|------|
| preloadAround L323-340 | L323 函数定义，L326-340 activity destroyed 检查 | ✅ 无偏差 |
| bind L466 | L466 `fun bind(...)` | ✅ 无偏差 |
| cancelPendingDownload 第一处 L495 | L495 `cancelPendingDownload()` | ✅ 无偏差 |
| cancelPendingDownload 实现 L549-554 | L549-554 | ✅ 无偏差 |
| loadImage L599-606 | L599 `fun loadImage(...)`，L600 cancelPendingDownload | ✅ 无偏差 |
| onRecycled L937-945 | L937 `fun onRecycled()`，L945 `}` | ✅ 无偏差 |
| isReleased L78 | L78 `private var isReleased = false` | ✅ 无偏差 |
| bufferingTimeoutHandler L125-139 | L125 `private val bufferingTimeoutHandler`，L139 `}` | ✅ 无偏差 |
| releaseSniffResources L408-416 | L408 `fun releaseSniffResources()`，L416 `}` | ✅ 无偏差 |
| release L454-467 | L454 `override fun release()`，L467 `}` | ✅ 无偏差 |
| onPlaybackStateChanged L993 | L993 `override fun onPlaybackStateChanged(state: Int)` | ✅ 无偏差 |
| onPlayerError L711 | L711 `override fun onPlayerError(error: PlaybackException)` | ✅ 无偏差 |
| onRenderedFirstFrame L1044 | L1044 `override fun onRenderedFirstFrame()` | ✅ 无偏差 |
| loadStartTimeMs L1084 | L1084 `private var loadStartTimeMs: Long = 0L` | ✅ 无偏差 |
| onLoadStarted L1090-1097 | L1090 `override fun onLoadStarted(...)` | ✅ 无偏差 |
| onLoadCompleted L1105-1130 | L1105 `override fun onLoadCompleted(...)`，L1130 `}` | ✅ 无偏差 |
| bandwidthMeter L92-94 | L92-94 | ✅ 无偏差 |
| BandwidthTier L99-103 | L99-103 | ✅ 无偏差 |
| getCurrentBandwidthTier L110-117 | L110-117 | ✅ 无偏差 |
| createLoadControlByTier L137-174 | L137-174 | ✅ 无偏差 |
| PlayerInstancePool.recycle L167-193 | L167-193 | ✅ 无偏差 |
| VideoFragment.onDestroyView L196-225 | L195 `override fun onDestroyView()`，L224 `}` | ⚠️ 轻微偏差（L195 vs L196，可忽略） |
| releasePlayer L333-335 | L333 `fun releasePlayer()`，L335 `}` | ✅ 无偏差 |
| videoUrl L220 | L220 `var videoUrl: String? = null` | ✅ 无偏差 |
| startPlay L308-360 | L308 `fun startPlay(...)` | ✅ 无偏差 |
| switchToArticle L1126-1167 | L1126 `fun switchToArticle(...)`，L1167 `}` | ✅ 无偏差 |
| playRssEpisode L1284-1336 | L1284 `fun playRssEpisode(...)` | ✅ 无偏差 |
| AudioPlay synchronized L149/L157 | L149, L157 | ✅ 无偏差 |
| CacheBook synchronized L383 | L383 | ✅ 无偏差 |
| ImageProvider synchronized L69 | L69 | ✅ 无偏差 |
| ReadManga synchronized L85/L107 | L85, L107 | ✅ 无偏差 |

**一致性结论**：✅ 四文档高度一致，行号准确度极高（仅 onDestroyView 有 L195 vs L196 的 1 行偏差，可忽略）。

---

## 6. 与 V1 审查报告的对比（12 个 ERROR 是否修复）

### 6.1 V1 ERROR 修复确认表

| V1 ERROR | 描述 | V2 修复状态 | 独立核实 |
|---------|------|-----------|---------|
| ERROR-1 | 所有源码路径错误 | ✅ 已修复 | 路径全部正确（ImageCanvasAdapter/Exo2MediaPlayer/ExoPlayerHelper/PlayerInstancePool/VideoFragment/VideoPlay） |
| ERROR-2 | FR-1 onRecycled 不取消，R-1.1 空想 | ✅ 已修复 | V2 删除 R-1.1，改为覆盖 bind L495 + loadImage L600 两处取消点 |
| ERROR-3 | FR-1 loadImage L600 取消点遗漏 | ✅ 已修复 | V2 明确补充 L600 第二处取消点 |
| ERROR-4 | FR-2 代码片段 player 变量未定义 | ✅ 已修复 | V2 修正为 `mInternalPlayer?.let { player -> ... }` |
| ERROR-5 | FR-2 延迟根因错误，onDestroyView 无延迟机制 | ✅ 已修复 | V2 修正为"同步连续无延迟机制"，提出 4 个延迟来源假设需重新验证 |
| ERROR-6 | FR-5 LoadControl 动态切换技术不可行 | ✅ 已修复 | V2 删除"运行时热切换"，改为"prepare 前按带宽档位构建" |
| ERROR-7 | FR-5 prioritizeTime 概念错误 | ✅ 已修复 | V2 修正为"时间优先于字节，非快速起播" |
| ERROR-8 | FR-4 switchVideo 不存在 | ✅ 已修复 | V2 修正为 switchToArticle L1126 / playRssEpisode L1284 |
| ERROR-9 | FR-6 把正常流程当 bug 修 | ✅ 已修复 | V2 删除"注册回调自动播放"，改为 switchToArticle 状态保护 |
| ERROR-10 | FR-3 onPlayerStateChanged 不存在 | ✅ 已修复 | V2 修正为 onPlaybackStateChanged L993 |
| ERROR-11 | FR-5 已有 TTFB 统计，重复造轮子 | ✅ 已修复 | V2 明确"复用现有 L1084-1130，不重复实现" |
| ERROR-12 | FR-7 synchronized 位置错误 | ✅ 已修复 | V2 修正为 AudioPlay/ImageProvider/ReadManga/CacheBook |

### 6.2 V1 WARN 修复确认

| V1 WARN | 描述 | V2 修复状态 |
|---------|------|-----------|
| WARN-1 | 验收标准引用不存在的日志 | ✅ 已修复（改为 "preloadAround skip: activity destroyed"） |
| WARN-2 | releasePlayer 调用链未理清 | ✅ 已修复（design.md 4.2 补充调用链） |
| WARN-3 | bufferingTimeoutHandler 已清理未提 | ✅ 已修复（明确"保持 L414 现有清理不变"） |
| WARN-4 | preloadAround 已有 activity destroyed 检查 | ✅ 已修复（明确"保持 L326-340 不变"） |
| WARN-5 | .bak 目录已有优化，不知道 | ✅ 已修复（design.md 新增"已有优化基线"章节） |
| WARN-6 | isScopeCancelled 与 isReleased 职责重叠 | ✅ 已修复（说明职责差异） |
| WARN-7 | 进度阈值 60% 实施难度被低估 | ⚠️ 部分修复（文档承认误差，但未给出替代方案） |
| WARN-8 | 现有分档策略未提及 | ✅ 已修复（明确复用现有 L99-103/L110-117/L137-174） |
| WARN-9 | tasks 0.1 路径全错 | ✅ 已修复（路径全部正确） |
| WARN-10 | FR-4 实际切换逻辑在 switchToArticle | ✅ 已修复（锚点改为 switchToArticle/playRssEpisode） |
| WARN-11 | 调用顺序未解释 | ✅ 已修复（补充顺序说明） |
| WARN-12 | 延迟取消 500ms 连接数失控 | ✅ 已修复（V2 删除延迟取消，改为节流 + 连接数上限 ≤ 10） |

### 6.3 V1 遗漏修复确认

| V1 遗漏 | 描述 | V2 修复状态 |
|---------|------|-----------|
| 遗漏-1 | onViewRecycled 与 onRecycled 关系 | ⚠️ 仍未明确说明（但 V2 方案不修改 onRecycled，影响低） |
| 遗漏-2 | release() 双保险调用 | ✅ 已修复（design.md 4.2 提及） |
| 遗漏-3 | prepareAsyncInternal 中 LoadControl 构建点 | ❌ **仍未修复**（见 CV-BIAS-1，V2 仍遗漏 PlayerInstancePool.createLoadControl 中间层） |
| 遗漏-4 | 真实 NPE 根因分析 | ❌ **仍未修复**（见 CV-BIAS-2，V2 仍在 synchronized(this) 上做文章） |

**对比结论**：V2 修复了 V1 的 12 个 ERROR 和 12 个 WARN 中的 11 个，但 V1 的遗漏-3 和遗漏-4 在 V2 中仍未完全解决，演变为本次交叉验证的 CV-BIAS-1 和 CV-BIAS-2。

---

## 7. 整体结论

### 7.1 判定结果

⚠️ **有条件可进入实施阶段**

### 7.2 判定依据

**正向**：
1. V1 的 12 个阻断级 ERROR 已全部修复（路径/方法名/锚点/概念错误均修正）
2. V1 的 12 个 WARN 已修复 11 个
3. 四文档一致性高，行号准确度极高（30+ 行号独立核实，仅 1 行偏差）
4. FR-1/FR-2/FR-3/FR-4/FR-6 方案技术可行，可落地

**待解决**：
1. **CV-BIAS-1（FR-5）**：方案描述遗漏 PlayerInstancePool.createLoadControl() 中间层，"prepare 前按带宽档位构建"已是现有行为。需修正方案描述，明确真正需新增的只是"连续 3 次 TTFB>1000ms 强制降档"判断。
2. **CV-BIAS-2（FR-7）**：synchronized(this) 非空守卫无效，排查方向仍偏离。需重新分析调用栈定位真实锁对象。
3. **CV-MISS-2（FR-4/FR-6）**：switchToArticle/playRssEpisode 未保存 Job 引用，需补充前置修改。
4. **CV-MISS-1（FR-3）**：遗漏 isPreparing CAS 守卫，需补充三标志位职责差异说明。

### 7.3 实施前必须完成的修正

| 优先级 | 修正项 | 影响 FR |
|--------|--------|---------|
| 高 | CV-BIAS-1: FR-5 方案描述修正（明确 PlayerInstancePool.createLoadControl 中间层） | FR-5 |
| 高 | CV-BIAS-2: FR-7 方案修正（删除 synchronized(this) 非空守卫，改为重新分析调用栈） | FR-7 |
| 高 | CV-MISS-2: FR-4/FR-6 补充前置修改（保存 Job 引用） | FR-4, FR-6 |
| 中 | CV-BIAS-3: FR-2 补充说明 recycle 已有 stop | FR-2 |
| 中 | CV-MISS-1: FR-3 补充 isPreparing 说明 | FR-3 |
| 中 | CV-MISS-3: FR-4 补充 prepareAsyncInternal 重复检测说明 | FR-4 |
| 低 | CV-MISS-4: spec.md FR-2 补充 release 双保险说明 | FR-2 |

### 7.4 与 openspec-document-auditor V1 审查的对比

| 维度 | V1 审查 | 本次交叉验证 |
|------|---------|------------|
| 审查方法 | 对照源码逐行核实 | 独立读取源码核实（不信任文档声明） |
| ERROR 数 | 12 | 0（V2 已修复） |
| 新发现认知偏差 | - | 3（CV-BIAS-1/2/3） |
| 新发现遗漏 | 4 | 4（CV-MISS-1/2/3/4） |
| 视角差异 | 侧重"文档与源码是否匹配" | 侧重"方案是否可落地+是否有认知偏差" |

**交叉验证价值**：
- V1 审查发现了"文档与源码不匹配"的问题（路径/方法名/锚点错误），V2 已修复
- 本次交叉验证发现了 V1 未覆盖的新问题：
  - FR-5 的方案描述虽修正了"不可热切换"，但仍遗漏 PlayerInstancePool.createLoadControl() 中间层（CV-BIAS-1）
  - FR-7 的排查方向虽修正了"ImagePlay → AudioPlay 等"，但新方向"synchronized(this) 非空守卫"仍无效（CV-BIAS-2）
  - FR-4/FR-6 的方案虽修正了锚点，但遗漏了 Coroutine.async 未保存 Job 的前置修改（CV-MISS-2）
- 这些新问题是 V1 审查未发现的，因为 V1 侧重"文档与源码匹配度"，而本次交叉验证侧重"方案可落地性"

### 7.5 建议

1. **优先修正 CV-BIAS-1 和 CV-BIAS-2**（FR-5 和 FR-7 的方案描述/方向问题），这两个问题会导致实施时走弯路
2. **补充 CV-MISS-2 的前置修改**（FR-4/FR-6 保存 Job 引用），否则"取消前一个异步任务"无法实现
3. 修正完成后即可进入实施阶段，无需再次全量审查
4. FR-1/FR-2/FR-3 方案可立即进入实施（CV-BIAS-3/CV-MISS-1 是补充说明，不影响方案可行性）

---

## 附录 A：独立核实工具与命令记录

### A.1 源码读取（Read）
- ImageCanvasAdapter.kt: L320-350, L460-510, L540-610, L935-950
- Exo2MediaPlayer.kt: L75-90, L120-140, L400-470, L494-555, L705-720, L985-1000, L1040-1055, L1080-1135
- ExoPlayerHelper.kt: L80-180
- PlayerInstancePool.kt: L160-210
- VideoFragment.kt: L195-235, L330-345
- VideoPlay.kt: L215-230, L305-365, L1120-1170, L1280-1335
- AudioPlay.kt: L145-165
- CacheBook.kt: L380-395
- ImageProvider.kt: L65-80
- ReadManga.kt: L80-110

### A.2 Grep 搜索（技术字段）
- prepareAsyncInternal 定位
- createLoadControl/acquire/LoadControl 定位
- synchronized 块定位（model 目录）
- object/class 声明定位

### A.3 V1 审查报告对比
- 完整读取 audit-report-v1.md（12 ERROR + 12 WARN + 4 遗漏）

---

## 附录 B：输出安全声明

本报告遵循 output-safety.md 规范：
- ✅ 未输出源名称（用"源[N]"或省略）
- ✅ 未输出域名（用"站点A/B/C"或省略）
- ✅ 未输出完整 URL（用"/path/{id}"或 urlPath 替代）
- ✅ 未输出 cookie/token/key 等敏感字段
- ✅ 只输出技术结论（异常类型/错误码/调用栈/字段名/函数名/行号）
- ✅ 源码引用使用相对路径（项目内路径）
- ✅ 代码片段只包含技术结构（无业务数据字段）

---

**交叉验证完毕。建议修正 CV-BIAS-1/CV-BIAS-2/CV-MISS-2 后进入实施阶段。**
