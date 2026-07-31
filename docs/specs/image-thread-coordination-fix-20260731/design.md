# Design: 图片加载与视频切换线程协调修复

> **Spec ID**: image-thread-coordination-fix-20260731
> **状态**: 🔄 设计中（V2，基于源码逐行核实重构）
> **创建日期**: 2026-07-31
> **版本**: 2.0
> **审查基线**: audit-report-v1.md（12 ERROR + 12 WARN 全部整改）

---

## 1. Technical Approach（技术方案）

### 1.1 分层优化策略

本设计采用**三层精准修复**策略，每层独立优化、互不干扰：

```
┌─────────────────────────────────────────────────┐
│                  图片层（FR-1, FR-7）              │
│  ImageCanvasAdapter 两处取消点优化                │
│  + AudioPlay/ImageProvider/ReadManga/CacheBook 守卫 │
├─────────────────────────────────────────────────┤
│                  播放器层（FR-2, FR-3, FR-4, FR-6） │
│  Exo2MediaPlayer 释放时序 + 回调忽略              │
│  + switchToArticle/playRssEpisode 防抖            │
│  + switchToArticle 状态保护                       │
├─────────────────────────────────────────────────┤
│                  网络层（FR-5）                    │
│  prepare 前按带宽档位构建 LoadControl             │
│  （复用现有 createLoadControlByTier）             │
└─────────────────────────────────────────────────┘
```

### 1.2 设计原则

1. **精准修改**：只触碰必须触碰的部分，不"优化"相邻代码
2. **独立可回滚**：每个 FR 独立 commit，可单独 revert
3. **源码核实优先**：所有修改锚点基于源码行号核实（V2 已逐行核实 6 个文件）
4. **不破坏现有架构**：不引入新依赖，遵循 object 单例 + Coroutine 链式封装
5. **健壮性优先**：所有新增逻辑包含入参校验和异常捕获
6. **复用已有优化**：不重复实现已有的 TTFB 统计、带宽分档、LoadControl 构建

---

## 2. 已有优化基线（V2 新增，避免重复造轮子）

> **来源**：WARN-5 提示 .bak 目录已有 sniff-stability-enhance 修复历史。当前代码已有完整优化，本 spec 必须复用而非重复实现。

### 2.1 ExoPlayerHelper.kt 已有优化

| 优化项 | 位置 | 说明 |
|--------|------|------|
| bandwidthMeter | L92-94 | DefaultBandwidthMeter 全局单例，实时测量有效带宽 |
| BandwidthTier 枚举 | L99-103 | WEAK/MEDIUM/GOOD 三档 |
| getCurrentBandwidthTier | L110-117 | 按 bitrateEstimate 分档（<1Mbps WEAK / 1-5Mbps MEDIUM / ≥5Mbps GOOD） |
| createLoadControlByTier | L137-174 | 按档位构建 DefaultLoadControl |
| setTargetBufferBytes(-1) | L145 | 解除字节上限，让缓冲完全由 maxBuffer 时长控制 |
| setPrioritizeTimeOverSizeThresholds(true) | L147 | 时间优先于字节，确保 maxBuffer 时长真正生效（非"快速起播"） |
| bufferForPlayback | L152/157/162 | 500ms/800ms/500ms（控制起播速度） |
| LoadControl 不可热切换注释 | L86-88 | 明确"LoadControl 只能在 player 构建时设置，运行时不可热切换" |

### 2.2 Exo2MediaPlayer.kt 已有优化

| 优化项 | 位置 | 说明 |
|--------|------|------|
| loadStartTimeMs 字段 | L1084 | TTFB 统计起始时间戳 |
| onLoadStarted | L1090-1097 | 记录 loadStartTimeMs |
| onLoadCompleted | L1105-1130 | 计算 TTFB，告警阈值 500ms |
| onPlaybackStateChanged | L993 | 状态变化日志（不是 onPlayerStateChanged） |
| bufferingTimeoutHandler | L125-139 | BUFFERING 超时回调（首次 25s，后续 12s） |
| isReleased 标志位 | L78 | applyMediaSourceByType 入口检查（防止 setMediaItem） |
| releaseSniffResources | L408-416 | scope.cancel + removeCallbacks + isReleased=true |
| release | L454-467 | 双保险调用 releaseSniffResources + PlayerInstancePool.recycle |

### 2.3 PlayerInstancePool.kt 已有优化

| 优化项 | 位置 | 说明 |
|--------|------|------|
| recycle | L167-193 | 同步执行 stop/clearMediaItems/clearVideoSurface 等 |
| @Synchronized | L167 | recycle 方法线程安全 |
| clear | L199-210 | Activity onDestroy 清空池 |

### 2.4 ImageCanvasAdapter.kt 已有优化

| 优化项 | 位置 | 说明 |
|--------|------|------|
| preloadAround activity destroyed 检查 | L326-340 | crash-2026-07-26 铁证，保持不变 |
| isGlideUsable 守卫 | L541-544 | destroyed activity 跳过 Glide 调用 |
| cancelPendingDownload | L549-554 | 取消 downloadTarget + clear |
| onRecycled | L937-945 | 只 clear photoView + 重置字段，不取消下载 |

---

## 3. Architecture Decisions（架构决策 - ADR Y-Statement 模板）

### AD-01: 图片下载取消节流策略（V2 重构）

**Context（背景）**：
`ImageCanvasAdapter` 存在**两处** `cancelPendingDownload()` 调用点：
1. `bind()` (L466) 内 L495
2. `loadImage()` (L599) 入口 L600

同一流程连续两次取消，导致快速滑动时 Glide.downloadOnly 下载被频繁打断。

> **V2 修正**：早期假设"onRecycled 取消下载"错误。源码核实 `onRecycled` (L937-945) 只 clear photoView + 重置字段，**不调用** cancelPendingDownload。

**Decision（决策）**：
采用组合策略：取消节流 + 下载进度阈值 + preloadAround 节流 300ms + 可见性优先级（>2 屏才取消）。同时覆盖 bind L495 和 loadImage L600 两处取消点。

**Consequences（影响）**：
- 正向：图片能完整写入磁盘缓存，快速滑动后正常显示
- 负向：节流期间多占用带宽；进度阈值存在估算误差
- 风险：需确保节流期间并发连接数 ≤ 10

**Alternatives（备选）**：
- A1: 完全不取消（OOM 风险，已否决）
- A2: 替换 Fresco（改动过大，已否决）

**Why not alternatives**：
完全不取消会导致内存激增；替换库破坏架构锁定原则。组合策略在内存和体验间取得平衡。

---

### AD-02: ExoPlayer 同步 stop + 异步 release（V2 修正）

**Context（背景）**：
`releaseSniffResources` (L408-416) 只做 `scope.cancel()` + `removeCallbacks` + `isReleased=true`，**未同步停止 mInternalPlayer 渲染管线**，导致解码器/渲染器未立即断开。

> **V2 重大修正**：
> - `VideoFragment.onDestroyView` (L196-225) 中 L202 `releaseSniffResources` + L203 `releasePlayer` 是**同步连续调用**，无 Handler.post/postDelayed
> - 早期"延迟 8-11 秒"根因需重新分析。真实延迟来源假设：
>   - 假设 A：日志时间戳对比错误（scope cancelled 日志在 L415，recycled 日志在 PlayerInstancePool.recycle L192，两者可能跨 onDestroyView 边界）
>   - 假设 B：`super.reset()` 父类 IjkExo2MediaPlayer 的某些同步阻塞操作
>   - 假设 C：延迟来自 Activity.onDestroy 而非 Fragment.onDestroyView
>   - 假设 D：releaseSniffResources 在其他路径被提前调用
> - 需日志重新验证延迟来源后再定最终方案

**Decision（决策）**：
在 `releaseSniffResources` (L408-416) 中同步调用 `mInternalPlayer?.stop()` + `setPlayWhenReady(false)`，立即断开渲染管线和解码器。release() 保持异步（不在 releaseSniffResources 中调用）。

> **代码片段修正**：`mInternalPlayer` 是父类 IjkExo2MediaPlayer 的 protected 字段，子类可访问。早期代码片段 `player?.stop()` 中 `player` 变量未定义，修正为 `mInternalPlayer?.let { player -> ... }`。

**Consequences（影响）**：
- 正向：mInternalPlayer 渲染管线立即停止
- 负向：onDestroyView 主线程耗时增加（预计 < 5ms）
- 风险：stop() 在某些状态下可能触发 onPlaybackStateChanged 回调，需配合 FR-3 标志位

**Alternatives（备选）**：
- A3: 同步 release（主线程阻塞，可能 ANR，已否决）

**Why not alternatives**：
同步 release 会阻塞主线程导致 ANR 风险。同步 stop + 异步 release 兼顾及时性和安全性。

---

### AD-03: isScopeCancelled 标志位（V2 修正方法名）

**Context（背景）**：
scope cancelled 后 217ms 仍触发 first frame rendered，协程取消未同步传递到 ExoPlayer 实例。

**Decision（决策）**：
新增 `isScopeCancelled: AtomicBoolean` 标志位，releaseSniffResources 时 set(true)，所有 ExoPlayer 回调检查标志位，为 true 则直接 return。prepareAsync 成功后重置 set(false)。

> **V2 修正**：方法名 `onPlayerStateChanged` → `onPlaybackStateChanged` (L993)

> **职责差异说明**（回应 WARN-6）：
> - `isReleased` (L78)：用于 `applyMediaSourceByType` 入口检查（防止 setMediaItem）
> - `isScopeCancelled`（新增）：用于回调入口检查（防止 onPlaybackStateChanged/onPlayerError/首帧渲染触发业务逻辑）
> - 两者职责不同，不复用。`isReleased` 防止"写入"，`isScopeCancelled` 防止"回调"。

**Consequences（影响）**：
- 正向：消除取消后的回调竞争
- 负向：新增状态管理复杂度，需在多处检查
- 风险：标志位未正确重置会导致下次播放无回调（需确保 prepareAsync 后重置）

**Alternatives（备选）**：
- 复用 isReleased：职责重叠，已否决

**Why not alternatives**：
isReleased 用于入口检查（写入），isScopeCancelled 用于回调检查（读取），职责不同。

---

### AD-04: 切换文章/集数防抖（V2 重新定位锚点）

**Context（背景）**：
切换文章/集数时，旧播放的 cancel 与新播放的 prepareAsync 可能在 10ms 内连续触发，ExoPlayer 实例在 release 和 prepareAsync 之间状态不确定。

> **V2 重大修正**：
> - VideoPlay.kt **没有 switchVideo 函数**，也**没有 currentUrl 字段**
> - 实际切换逻辑：`switchToArticle` (L1126) + `playRssEpisode` (L1284)
> - 字段是 `videoUrl` (L220)，不是 `currentUrl`
> - switchToArticle 已有 source 匹配检查 (L1141-1153)

**Decision（决策）**：
在 `switchToArticle` (L1126) 和 `playRssEpisode` (L1284) 入口增加防抖检查，短时间内连续切换取消前一个异步任务，避免 cancel-prepare 竞争。

**Consequences（影响）**：
- 正向：消除切换时的 cancel-prepare 竞争
- 负向：需正确处理异步任务取消
- 风险：防抖期间记录最后一次切换意图

**Alternatives（备选）**：
- A5: 同 URL 直接 return（丢失 seekTo 意图，已否决）

**Why not alternatives**：
直接 return 会丢失用户意图。防抖 + 异步任务取消兼顾竞争消除和用户体验。

---

### AD-05: 连续慢 TTFB 强制降档（V3 重新定义——prepare 前按档位构建已是现有行为）

**Context（背景）**：
弱网下 TTFB>1000ms 时反复 BUFFERING→READY 循环（单 URL 29 秒内 7 次循环）。

> **V3 重大修正——prepare 前按档位构建已是现有行为**：
> - `PlayerInstancePool.createLoadControl()` (L106-113) **已经**调用 `ExoPlayerHelper.getCurrentBandwidthTier()` + `ExoPlayerHelper.createLoadControlByTier(tier, sharedAllocator)` 按带宽档位构建 LoadControl
> - `PlayerInstancePool.acquire(looper)` (L122-149) 在新建 ExoPlayer 时通过 `.setLoadControl(createLoadControl())` (L136) 设置 LoadControl
> - 即"prepare 前按带宽档位构建 LoadControl"**已是现有行为**，FR-5 不需要修改 PlayerInstancePool.createLoadControl
> - 早期"运行时动态切换 LoadControl"技术不可行（L86-88 注释明确"LoadControl 只能构建时设置"）
> - 早期"prioritizeTime=true 导致快速起播"概念错误：setPrioritizeTimeOverSizeThresholds(true) 是"时间优先于字节"，不是"快速起播"
> - 已有完整 TTFB 统计 (L1084-1130)：onLoadStarted L1090 记录 loadStartTimeMs + onLoadCompleted L1105 计算 loadElapsed 变量 + 告警阈值 500ms，不重复实现
> - 已有完整带宽分档策略 (L99-103/L110-117/L137-174)，不重复实现

**Decision（决策）**：
FR-5 真正需新增的只是"连续 3 次 TTFB>1000ms 强制降档"判断逻辑：
1. **不修改 PlayerInstancePool.createLoadControl**（L106-113 已有档位构建逻辑）
2. 在 `Exo2MediaPlayer.onLoadCompleted` (L1105-1130) 中复用现有 loadElapsed 变量（TTFB），新增 `ttfbSlowCount` 计数器
3. 连续 3 次 TTFB>1000ms 时调用 `getCurrentBandwidthTier()` 获取当前档位，若当前是 GOOD/MEDIUM 则强制降一档（GOOD→MEDIUM / MEDIUM→WEAK），记录到 `forceTier` 字段
4. 降档后下次 `prepareAsyncInternal` 时 `PlayerInstancePool.acquire` 会按新档位构建 LoadControl（**复用现有逻辑**，无需修改 acquire）
5. 网络恢复（连续 3 次 TTFB<500ms）后重置 `ttfbSlowCount`，清除 `forceTier`，下次 prepare 时恢复自动档位
6. 注意：acquire 命中池（reuse）时不会重新设置 LoadControl，只有新建实例时才用新档位；forceTier 降级后需 recycle 旧实例或等待池自然淘汰，确保下次 acquire 新建实例时使用新档位

**Consequences（影响）**：
- 正向：弱网下连续慢 TTFB 触发降档，下次 prepare 使用小 buffer 快起播
- 负向：档位修正延迟（下次 prepare 生效）；acquire 命中池时需额外 recycle
- 风险：频繁切换档位需设置最小间隔（建议 30 秒）

**Alternatives（备选）**：
- A4: 固定 prioritizeTime=false（牺牲 maxBuffer 时长有效性，已否决）
- A8: 运行时热切换（技术不可行，已否决）

**Why not alternatives**：
固定关闭时间优先牺牲好网体验；运行时热切换技术不可行。复用现有 PlayerInstancePool.createLoadControl 档位构建 + 新增 TTFB 降档判断是唯一可行方案。

---

## 4. Data Flow（数据流）

### 4.1 图片加载流程（FR-1 修复后，V2 重画）

```
用户快速滑动
    │
    ▼
RecyclerView.scroll
    │
    ▼
preloadAround (L323) ─── throttle 300ms ─── 避免取消5个+新发5个同时发生
    │
    ├─ 保持 L326-340 activity destroyed 检查不变
    │
    ▼
ViewHolder 复用 → bind() (L466)
    │
    ├─ 第一处取消点 L495 cancelPendingDownload
    │   │
    │   ├─ 检查1: 离视口距离 > 2屏? ── 否 ── 不取消，继续下载
    │   │                │
    │   │                是
    │   │                ▼
    │   ├─ 检查2: 下载进度 > 阈值? ── 是 ── 不取消，让请求完成
    │   │                │
    │   │                否
    │   │                ▼
    │   └─ 节流：短时间内不重复取消
    │
    ▼
loadImage() (L599) ─── 第二处取消点 L600 cancelPendingDownload
    │
    └─ 同样应用节流 + 进度阈值 + 可见性优先级检查
    │
    ▼
onRecycled (L937-945) ── 保持不变（只 clear photoView，不取消下载）
```

> **V2 修正**：删除"onRecycled 延迟 500ms 取消"分支（onRecycled 根本不取消下载）。改为 bind L495 + loadImage L600 两处取消点。

### 4.2 视频切换流程（FR-2, FR-3, FR-4 修复后，V2 重画）

```
用户切换文章/集数
    │
    ▼
switchToArticle (L1126) / playRssEpisode (L1284)
    │
    ├─ 防抖检查：短时间内连续切换取消前一个异步任务
    │
    ▼
releaseSniffResources (L408-416)
    │
    ├─ scope.cancel()
    ├─ isReleased = true
    ├─ isScopeCancelled.set(true)  ← FR-3 新增
    ├─ mInternalPlayer?.stop()     ← FR-2 新增（mInternalPlayer 是父类 protected 字段）
    ├─ mInternalPlayer?.setPlayWhenReady(false)  ← FR-2 新增
    └─ bufferingTimeoutHandler.removeCallbacks  ← 保持不变
    │
    ▼
ExoPlayer 回调 (onPlaybackStateChanged L993 等)
    │
    └─ 检查 isScopeCancelled ── true ── 直接 return（忽略回调）
    │
    ▼
releasePlayer (L203 → L333-335: _playerView?.currentPlayer?.release())
    │
    └─ Exo2MediaPlayer.release() (L454-467)
        ├─ releaseSniffResources() 双保险（被 isReleased 防重复跳过）
        ├─ mInternalPlayer?.let { detachFromPlayer + PlayerInstancePool.recycle + mInternalPlayer=null }
        └─ super.reset()
             │
             └─ PlayerInstancePool.recycle (L167-193, 同步: stop/clearMediaItems/clearVideoSurface)
    │
    ▼
prepareAsync(newUrl)
    │
    └─ isScopeCancelled.set(false)  ← FR-3 重置
    │
    ▼
正常播放
```

> **V2 修正**：
> - 删除"switchVideo(newUrl)"改为"switchToArticle / playRssEpisode"
> - 删除"player.stop()"改为"mInternalPlayer?.stop()"（mInternalPlayer 是父类 protected 字段）
> - onPlayerStateChanged → onPlaybackStateChanged
> - 补充 releasePlayer 调用链（releasePlayer → currentPlayer.release → Exo2MediaPlayer.release → PlayerInstancePool.recycle）

### 4.3 连续慢 TTFB 强制降档流程（FR-5 修复后，V3 重画——prepare 前按档位构建已是现有行为）

```
prepareAsyncInternal
    │
    ▼
PlayerInstancePool.acquire(looper)  ← 现有逻辑（L122-149，不修改）
    │
    ├─ 命中池（reuse）── 沿用原 LoadControl（不重新设置）
    │
    ├─ 未命中（新建）── createLoadControl()  ← 现有逻辑（L106-113，不修改）
    │                      │
    │                      ▼
    │                  getCurrentBandwidthTier()  ← 复用现有 L110-117
    │                  createLoadControlByTier(tier, sharedAllocator)  ← 复用现有 L137-174
    │                  .setLoadControl(...)  ← L136
    │
    ▼
播放过程中
    │
    ▼
onLoadCompleted (L1105) ── 复用现有 TTFB 统计（loadElapsed 变量）
    │
    ├─ loadElapsed = System.currentTimeMillis() - loadStartTimeMs  ← 现有逻辑 L1112
    │
    ▼
FR-5 新增判断：检查 forceTier 字段
    │
    ├─ forceTier != null ── 已强制降档，跳过降档判断
    │
    ├─ forceTier == null ── 统计连续 TTFB > 1000ms 次数（ttfbSlowCount）
    │                      │
    │                      ├─ 连续 3 次 ── getCurrentBandwidthTier() 获取当前档位
    │                      │              │
    │                      │              ├─ GOOD ── forceTier = MEDIUM（降一档）
    │                      │              ├─ MEDIUM ── forceTier = WEAK（降一档）
    │                      │              └─ WEAK ── 已最低，不降档
    │                      │              │
    │                      │              ▼
    │                      │          记录日志 + recycle 旧实例（确保下次 acquire 新建）
    │
    ▼
forceTier != null 时，统计连续 TTFB < 500ms 次数（ttfbFastCount）
    │
    └─ 连续 3 次 ── 清除 forceTier，重置 ttfbSlowCount/ttfbFastCount
            │
            ▼
        记录日志（恢复自动档位）
        │
        ▼
    最小切换间隔 30s（防止抖动）
```

> **V3 重大修正**：
> - "prepare 前按带宽档位构建 LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113 + acquire L136），不需要修改
> - FR-5 真正新增的只是 onLoadCompleted 中的 ttfbSlowCount 降档判断 + forceTier 字段
> - 删除"动态切换 LoadControl"（技术不可行）
> - 删除"prioritizeTime=false + minBuffer=1500ms"（概念错误）
> - 删除"新增 TTFB 统计"（L1084-1130 已完整，loadElapsed 变量可复用）
> - 改为复用现有 PlayerInstancePool.createLoadControl + acquire + createLoadControlByTier + getCurrentBandwidthTier + TTFB 统计

---

## 5. File Changes（文件变更清单，V2 真实路径）

### FR-1: 图片下载取消策略优化

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` | 修改 | L495 + L600 两处取消点优化、L323 preloadAround 节流 |

**详细变更**：
1. L495 bind() 中 cancelPendingDownload 调用点：增加节流 + 可见性优先级判断（离视口 > 2 屏才取消）+ 进度阈值检查
2. L600 loadImage() 中 cancelPendingDownload 调用点：同样应用节流 + 进度阈值 + 可见性优先级检查
3. L549-554 cancelPendingDownload 实现：增加进度阈值检查（> 阈值不取消）
4. L323 preloadAround：增加 throttle 300ms 机制
5. 保持 L326-340 activity destroyed 检查不变
6. 保持 L937-945 onRecycled 现有逻辑不变（不取消下载）
7. 新增字段：`private var preloadThrottleJob: Job? = null`（节流任务）
8. 新增字段：`private var downloadProgress: Float = 0f`（下载进度，通过拦截器估算）
9. 新增字段：`private var lastCancelTimeMs: Long = 0L`（节流时间戳）

> **V2 删除**：
> - "L937-945 onRecycled：改为延迟 500ms 取消"（onRecycled 根本不取消下载）
> - "pendingCancelJob: Job?（延迟取消任务）"（不再需要）

### FR-2: ExoPlayer 释放时序优化

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 修改 | L408-416 releaseSniffResources 增加 stop + setPlayWhenReady(false) |

**详细变更**（V2 代码片段修正）：
- L408-416 releaseSniffResources 中新增：
  ```kotlin
  // FR-2: 在 releaseSniffResources 中同步停止渲染管线
  // mInternalPlayer 是父类 IjkExo2MediaPlayer 的 protected 字段，子类可访问
  kotlin.runCatching {
      mInternalPlayer?.let { player ->
          player.stop()
          player.playWhenReady = false
      }
  }
  ```
- 保持 scope.cancel() + isReleased = true 不变
- 保持 L414 bufferingTimeoutHandler.removeCallbacks 现有清理逻辑不变

> **V2 修正**：早期代码片段 `player?.stop()` 中 `player` 变量未定义，修正为 `mInternalPlayer?.let { player -> ... }`

### FR-3: 取消后忽略 ExoPlayer 回调

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 修改 | 新增 isScopeCancelled 标志位，onPlaybackStateChanged/onPlayerError/首帧回调检查 |

**详细变更**（V2 方法名修正）：
1. 新增字段：`private val isScopeCancelled = AtomicBoolean(false)`
2. releaseSniffResources 中：`isScopeCancelled.set(true)`
3. prepareAsync 成功后：`isScopeCancelled.set(false)`
4. `onPlaybackStateChanged` (L993) 首行：`if (isScopeCancelled.get()) return`
5. `onPlayerError` (L711) 首行：`if (isScopeCancelled.get()) return`
6. 首帧渲染回调 `onRenderedFirstFrame` (L1044) 首行：`if (isScopeCancelled.get()) return`

> **V2 修正**：`onPlayerStateChanged` → `onPlaybackStateChanged` (L993)

### FR-4: 切换文章/集数防抖（V3 补充 Job 引用前置修改）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 修改 | 新增 switchArticleJob/playEpisodeJob 字段 + switchToArticle L1126 + playRssEpisode L1284 防抖检查 |

**详细变更**（V3 补充前置修改）：

**前置修改**（FR-4 和 FR-6 共享，必须先完成）：
1. 新增字段：`private var switchArticleJob: Job? = null`（switchToArticle 异步任务引用）
2. 新增字段：`private var playEpisodeJob: Job? = null`（playRssEpisode 异步任务引用）
3. `switchToArticle` L1137 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 赋值给 `switchArticleJob`
4. `playRssEpisode` L1294 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 赋值给 `playEpisodeJob`

> **源码核实**：switchToArticle L1137 / playRssEpisode L1294 的 Coroutine.async 当前**未保存 Job 引用**，"取消前一个异步任务"需先完成前置修改

**FR-4 变更**：
1. `switchToArticle` (L1126) 入口先 `switchArticleJob?.cancel()` 取消前一个异步任务
2. 然后再执行新的 `Coroutine.async`（赋值给 `switchArticleJob`）
3. `playRssEpisode` (L1284) 入口先 `playEpisodeJob?.cancel()` 取消前一个异步任务
4. 然后再执行新的 `Coroutine.async`（赋值给 `playEpisodeJob`）
5. 保持 switchToArticle L1141-1153 source 匹配检查不变
6. 防抖期间记录最后一次切换意图

> **V2 删除**：删除"switchVideo 增加 currentUrl == newUrl 判断"（switchVideo 不存在，currentUrl 字段不存在）
> **V3 补充**：新增前置修改（Coroutine.async 未保存 Job 引用）

### FR-5: 连续慢 TTFB 强制降档（V3 重新定义——不修改 PlayerInstancePool）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 修改 | onLoadCompleted (L1105) 新增 ttfbSlowCount 降档判断 + forceTier 字段 |
| `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` | **不修改** | createLoadControl (L106-113) + acquire (L122-149) 已有档位构建逻辑 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 复用 | 不修改，复用现有 createLoadControlByTier + getCurrentBandwidthTier |

**详细变更**（V3 重新定义——prepare 前按档位构建已是现有行为）：
1. **不修改 PlayerInstancePool.createLoadControl**（L106-113 已调用 getCurrentBandwidthTier + createLoadControlByTier）
2. **不修改 PlayerInstancePool.acquire**（L122-149 已通过 setLoadControl 设置，L136）
3. 在 `Exo2MediaPlayer.onLoadCompleted` (L1105-1130) 中复用现有 `loadElapsed` 变量（TTFB），新增档位修正判断：
   - 连续 3 次 TTFB>1000ms → 调用 getCurrentBandwidthTier 获取当前档位，GOOD→MEDIUM / MEDIUM→WEAK 降一档，记录到 forceTier
   - 连续 3 次 TTFB<500ms → 清除 forceTier，恢复自动档位
4. 新增字段：`private var ttfbSlowCount = 0`、`private var ttfbFastCount = 0`、`private var forceTier: BandwidthTier? = null`、`private var lastSwitchTime = 0L`
5. 降档后下次 prepareAsyncInternal 时 PlayerInstancePool.acquire 会按新档位构建 LoadControl（复用现有逻辑）
6. 注意：acquire 命中池（reuse）时不会重新设置 LoadControl，forceTier 降级后需 recycle 旧实例确保下次 acquire 新建
7. 最小切换间隔 30 秒（防抖动）

> **V3 重大修正**：
> - "prepare 前按带宽档位构建 LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113），不需要修改
> - "ExoPlayerHelper 新增 dynamicLoadControl 方法，支持运行时切换"（技术不可行）
> - "onLoadCompleted 中计算 TTFB"（L1084-1130 已完整实现，loadElapsed 变量可复用）

### FR-6: switchToArticle 状态保护（V3 补充 Job 引用前置修改）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 修改 | switchToArticle L1126 状态保护（依赖 FR-4 前置修改的 switchArticleJob 字段） |

**详细变更**（V3 补充前置修改）：

**前置修改**（与 FR-4 共享，见 FR-4 说明）：
1. 新增字段：`private var switchArticleJob: Job? = null`
2. `switchToArticle` L1137 的 Coroutine.async 赋值给 `switchArticleJob`

**FR-6 变更**：
1. switchToArticle 进入异步加载时设置 `isSwitchingArticle = true` 标志
2. 异步加载完成（startPlay 调用前）清除标志
3. 若异步加载期间用户再次触发切换，通过 `switchArticleJob?.cancel()` 取消前一个异步任务（依赖前置修改）
4. **预期行为**：异步任务被取消后，`withContext(Main)` 中的 `startPlay` 不会执行——这是预期行为（用户切换到新文章时，旧文章的加载应该被取消）
5. 保持 startPlay L353-359 rssArticle null 静默日志逻辑不变

> **V2 删除**：
> - "startPlay 中 rssArticle 为 null 时不 return"（正常流程）
> - "注册一次性回调监听文章加载完成"（引入副作用）
> - "显示 loading indicator"（不在本 FR 范围）
> - "超时 10 秒提示"（不在本 FR 范围）
> **V3 补充**：新增前置修改（依赖 FR-4 的 switchArticleJob 字段）

### FR-7: NullPointerException(monitor-enter) 调用栈重新分析（V3 重新定义）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| 待调用栈重新分析后确认 | 待确认 | Step 1 重新分析调用栈 → Step 2 定位真实锁对象 → Step 3 根据锁对象类型决定修复方案 |

**详细变更**（V3 重新定义——非空守卫方案无效）：

> **源码核实（V3 重大修正）**：AudioPlay/ImageProvider/ReadManga/CacheBook **都是 object 单例**（`object AudioPlay` L40 / `object CacheBook` L42 / `object ImageProvider` L31 / `object ReadManga` L45），this 不可能为 null，"添加非空守卫"方案无效。

**Step 1：重新分析调用栈**：
- 重新分析 logs(9) 中 NullPointerException(monitor-enter) 的完整调用栈
- 确认异常发生的真实位置（类名、方法名、行号）

**Step 2：定位真实锁对象**：
- 可能是 `synchronized(lockObject)` 中 lockObject 为 null（非 synchronized(this) 场景）
- 可能是 Java 字节码层面的 monitorenter 指令操作数栈为 null
- 可能是其他对象的字段在并发场景下被置 null

**Step 3：根据锁对象类型决定修复方案**：
- 若调用栈指向 `@Synchronized` 注解方法（等价 synchronized(this)），this 不可能为 null（object 单例），需分析其他原因（GC 残留引用、object 初始化未完成等）
- 若调用栈指向 `synchronized(lockObject)`，检查 lockObject 是否可能为 null，添加非空守卫或改为 `private val lock = Any()`
- 其他场景根据具体情况定制修复方案

**参考排查位置**（object 单例，this 非 null，仅作参考）：
- `app/src/main/java/io/legado/app/model/AudioPlay.kt` L149, L157 synchronized(this) 块
- `app/src/main/java/io/legado/app/model/CacheBook.kt` L383 synchronized(this) 块
- `app/src/main/java/io/legado/app/model/ImageProvider.kt` L69 synchronized(this) 块
- `app/src/main/java/io/legado/app/model/ReadManga.kt` L85, L107 synchronized(this) 块

> **V3 重大修正**：
> - "为 synchronized(this) 块添加非空守卫"方案无效（object 单例 this 不可能为 null），已删除
> - 改为"调用栈重新分析 → 定位真实锁对象 → 根据锁对象类型决定修复方案"三步流程

---

## 6. 状态管理设计

### 6.1 isScopeCancelled 标志位生命周期

```
创建 ExoPlayer ── isScopeCancelled = false
        │
        ▼
prepareAsync ── isScopeCancelled = false（重置）
        │
        ▼
正常播放 ── isScopeCancelled = false
        │
        ▼
releaseSniffResources ── isScopeCancelled = true（设置）
        │
        ▼
所有回调被忽略 ── isScopeCancelled = true
        │
        ▼
下次 prepareAsync ── isScopeCancelled = false（重置）
```

### 6.2 LoadControl 档位状态机（V3 重画——复用现有 PlayerInstancePool.createLoadControl）

```
                    连续3次TTFB>1000ms（forceTier降一档：GOOD→MEDIUM / MEDIUM→WEAK）
    AUTO（PlayerInstancePool.createLoadControl 按现有逻辑自动分档） ────────────── FORCE_DOWNGRADE
        ▲                                                  │
        │                                                  │
        └──── 连续3次TTFB<500ms（清除forceTier） ──────────┘
                  (间隔≥30s)
```

> **V3 重大修正**：
> - "prepare 前按带宽档位构建 LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113），AUTO 状态即现有逻辑
> - FR-5 新增的只是 forceTier 字段（FORCE_DOWNGRADE 状态），用于连续慢 TTFB 时强制降档
> - 删除"FAST_START/ROBUST_BUFFER 状态机"（prioritizeTime 概念错误）
> - 改为 AUTO/FORCE_DOWNGRADE 状态机（基于 forceTier 字段）

---

## 7. 错误处理设计

### 7.1 FR-1 错误处理
- 节流任务异常：runCatching 包裹，异常时 fallback 立即取消
- 进度阈值估算异常：runCatching 包裹，异常时按原逻辑取消

### 7.2 FR-2 错误处理
- mInternalPlayer.stop() 异常：runCatching 包裹（mInternalPlayer 可能为 null）
- setPlayWhenReady 异常：runCatching 包裹

### 7.3 FR-3 错误处理
- AtomicBoolean 线程安全，无需额外同步

### 7.4 FR-4 错误处理
- 防抖检查异常：runCatching 包裹，异常时按原逻辑执行完整流程
- Job 引用取消异常：runCatching 包裹 switchArticleJob?.cancel() / playEpisodeJob?.cancel()，异常时按原逻辑执行

### 7.5 FR-5 错误处理
- TTFB 计算（loadElapsed）异常：runCatching 包裹，异常时不切换档位（loadElapsed 已是现有逻辑，异常概率低）
- 档位修正（forceTier）异常：runCatching 包裹，异常时保持当前档位
- getCurrentBandwidthTier 异常：runCatching 包裹，异常时不降档

### 7.6 FR-6 错误处理
- 异步任务取消异常：runCatching 包裹 switchArticleJob?.cancel()，异常时按原逻辑执行

### 7.7 FR-7 错误处理
- 调用栈重新分析后根据锁对象类型决定错误处理方案（V3 重新定义，非空守卫方案已删除）

---

## 8. 测试设计

### 8.1 单元测试（如适用）
- FR-3 isScopeCancelled 标志位状态转换
- FR-4 switchToArticle/playRssEpisode 防抖逻辑
- FR-5 档位修正逻辑（连续 TTFB 计数）

### 8.2 真机测试（必须）
- 场景 1-8 按 spec.md 执行
- 使用 ai_tests/scripts/ 固定脚本
- 测试包：`io.legado.miss.app.debug`

### 8.3 日志验证
- "Cronet request canceled" 频次对比
- "preloadAround skip: activity destroyed" 频次不上升
- releaseSniffResources 后 mInternalPlayer 停止日志
- first frame rendered 在 cancelled 后出现次数
- BUFFERING→READY 循环次数对比
- NullPointerException(monitor-enter) 出现次数

---

## 9. 性能影响评估

| FR | 内存影响 | CPU 影响 | 网络影响 | 主线程影响 |
|----|---------|---------|---------|-----------|
| FR-1 | +少量（节流期间连接） | 可忽略 | +节流期间带宽占用 | 可忽略 |
| FR-2 | 可忽略 | 可忽略 | 可忽略 | +<5ms（stop 调用） |
| FR-3 | 可忽略 | 可忽略 | 可忽略 | 可忽略 |
| FR-4 | 可忽略 | 可忽略 | 可忽略 | 可忽略 |
| FR-5 | 可忽略 | 可忽略 | +弱网下小 buffer | 可忽略 |
| FR-6 | +少量（标志位） | 可忽略 | 可忽略 | 可忽略 |
| FR-7 | 可忽略 | 可忽略 | 可忽略 | 可忽略 |

**总体评估**：性能影响可接受，FR-2 的主线程增加耗时在 5ms 以内，不会导致 ANR。

---

## 10. 回滚策略

每个 FR 独立 commit，回滚策略：

| FR | 回滚方法 | 风险 |
|----|---------|------|
| FR-1 | git revert 单个 commit | 低（恢复原取消策略） |
| FR-2 | git revert 单个 commit | 低（恢复原释放时序） |
| FR-3 | git revert 单个 commit | 低（移除标志位） |
| FR-4 | git revert 单个 commit | 低（恢复原切换逻辑） |
| FR-5 | git revert 单个 commit | 低（恢复自动档位） |
| FR-6 | git revert 单个 commit | 低（移除状态保护） |
| FR-7 | git revert 单个 commit | 低（恢复原 synchronized） |

**回滚顺序**：按 FR 编号逆序回滚（FR-7 → FR-6 → ... → FR-1），避免依赖冲突。

---

## 11. 实施注意事项

1. **源码核实**：实施前必须再次 Read 确认源码行号（防止 master 分支已有变更）
2. **逐 FR 实施**：按 P0 → P1 → P2 顺序，每个 FR 完成后编译验证
3. **日志保留**：所有新增逻辑必须用 `AppLog.put()` 记录关键状态（符合 logging_rules.md）
4. **不引入 Timber**：遵循代码约束，日志用 `AppLog.put()`
5. **协程风格**：新增协程用 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装
6. **错误处理**：用 `kotlin.runCatching`（带 `kotlin.` 前缀）
7. **字符串判空**：用 `isNullOrBlank()`
8. **FR-1 修改锚点**：bind() L495 + loadImage() L600 两处取消点（不是 onRecycled）
9. **FR-2 代码片段**：mInternalPlayer（不是 player 变量）
10. **FR-3 方法名**：onPlaybackStateChanged（不是 onPlayerStateChanged）
11. **FR-4 锚点**：switchToArticle L1126 / playRssEpisode L1284（不是 switchVideo）
12. **FR-4 前置修改**：必须先新增 switchArticleJob/playEpisodeJob 字段并保存 Job 引用（源码核实 L1137/L1294 未保存 Job）
13. **FR-5 方案**：不修改 PlayerInstancePool.createLoadControl（已有档位构建），只在 onLoadCompleted 新增 ttfbSlowCount 降档判断
14. **FR-6 方案**：switchToArticle 状态保护（不是 startPlay 注册回调），依赖 FR-4 前置修改的 switchArticleJob 字段
15. **FR-7 排查**：调用栈重新分析 → 定位真实锁对象 → 根据锁对象类型决定修复方案（AudioPlay/ImageProvider/ReadManga/CacheBook 是 object 单例，this 非 null，非空守卫无效）
16. **FR-2 延迟根因**：实施前必须重新分析日志时间戳，确认延迟来源（super.reset() 或其他）

---

## V3修订记录（2026-07-31）

> **修订背景**：V2重构后交叉验证审查发现3个高优先级阻塞点，V3修复后直接进入实施阶段。

### 修订1：AD-05重新定义——FR-5连续慢TTFB强制降档

- **根因**：源码核实发现"prepare前按带宽档位构建LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113 + acquire L136）
- **修改内容**：
  - AD-05架构决策：重新定义，明确"不修改PlayerInstancePool.createLoadControl"，新增forceTier字段和ttfbSlowCount计数器
  - 4.3数据流：重画为"连续慢TTFB强制降档流程"，明确acquire命中池时不更新LoadControl，forceTier降级后需recycle旧实例
  - File Changes FR-5：PlayerInstancePool.kt标记为"不修改"，ExoPlayerHelper.kt标记为"复用"，只修改Exo2MediaPlayer.kt
  - 6.2状态机：改为AUTO/FORCE_DOWNGRADE状态机（基于forceTier字段）
  - 7.5错误处理：更新为loadElapsed复用 + forceTier异常处理
  - 11.实施注意事项：FR-5方案改为"不修改PlayerInstancePool.createLoadControl，只在onLoadCompleted新增ttfbSlowCount降档判断"

### 修订2：FR-7重新定义——调用栈重新分析

- **根因**：源码核实发现AudioPlay/ImageProvider/ReadManga/CacheBook都是object单例，this不可能为null，"添加非空守卫"方案无效
- **修改内容**：
  - File Changes FR-7：文件变更改为"待调用栈重新分析后确认"，详细变更改为三步流程（Step1重新分析调用栈→Step2定位真实锁对象→Step3根据锁对象类型决定修复方案）
  - 7.7错误处理：改为"调用栈重新分析后根据锁对象类型决定错误处理方案"
  - 11.实施注意事项：FR-7排查改为"调用栈重新分析→定位真实锁对象→根据锁对象类型决定修复方案"

### 修订3：FR-4/FR-6补充Job引用前置修改

- **根因**：源码核实发现switchToArticle L1137 / playRssEpisode L1294的Coroutine.async未保存Job引用
- **修改内容**：
  - File Changes FR-4：新增前置修改说明（switchArticleJob/playEpisodeJob字段），FR-4变更改为switchToArticle入口先switchArticleJob?.cancel()
  - File Changes FR-6：新增前置修改说明（依赖FR-4的switchArticleJob字段），FR-6变更补充预期行为（异步任务被取消后withContext(Main)中startPlay不执行）
  - 7.4错误处理：新增Job引用取消异常处理
  - 7.6错误处理：更新为switchArticleJob?.cancel()异常处理
  - 11.实施注意事项：新增FR-4前置修改注意事项
