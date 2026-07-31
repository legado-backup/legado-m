# Tasks: 图片加载与视频切换线程协调修复

> **Spec ID**: image-thread-coordination-fix-20260731
> **状态**: 🔄 设计中（V2，基于源码逐行核实重构）
> **创建日期**: 2026-07-31
> **版本**: 2.0
> **审查基线**: audit-report-v1.md（12 ERROR + 12 WARN 全部整改）

---

## 任务清单

### 阶段 0: 准备

- [ ] 0.1 Read 源码确认所有锚点行号（V2 真实路径）：
  - `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`（L323-340, L466, L495, L549-554, L599-606, L937-945）
  - `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（L78, L125-139, L408-416, L454-467, L711, L993, L1044, L1084-1130）
  - `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`（L86-88, L92-94, L99-103, L110-117, L137-174）
  - `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt`（L106-113 createLoadControl 已有档位构建、L122-149 acquire L136 setLoadControl、L167-193 recycle）
  - `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt`（L196-225, L333-335）
  - `app/src/main/java/io/legado/app/model/VideoPlay.kt`（L220, L308-360, L1126-1167, L1284-1336）
- [ ] 0.2 Read logging-during-refactoring.md 确认日志记录规范
- [ ] 0.3 Read version-delivery-sync.md 确认更新日志规范
- [ ] 0.4 Read ai_e2e_testing_workflow.md 确认测试流程
- [ ] 0.5 确认当前分支为 master，创建备份分支（如需）
- [ ] 0.6 确认 ai_tests/venv/Scripts/python.exe 可用
- [ ] 0.7 确认模拟器/真机连接正常，测试包 `io.legado.miss.app.debug` 可安装
- [ ] 0.8 **FR-2 延迟根因预分析**：重新分析日志时间戳，确认 scope cancelled 到 recycled 的真实延迟来源（super.reset() 或其他），记录到 issues-found.md

### 阶段 1: P0 核心修复（FR-1, FR-2）

#### FR-1: 图片下载取消策略优化

- [ ] 1.1 Read `ImageCanvasAdapter.kt` 确认 L466 bind()、L495 cancelPendingDownload 调用（第一处）、L599-606 loadImage()、L600 cancelPendingDownload 调用（第二处）、L549-554 实现、L323-340 preloadAround、L937-945 onRecycled 当前代码
- [ ] 1.2 新增字段：`private var preloadThrottleJob: Job? = null`（节流任务）
- [ ] 1.3 新增字段：`private var downloadProgress: Float = 0f`（下载进度，通过拦截器估算）
- [ ] 1.4 新增字段：`private var lastCancelTimeMs: Long = 0L`（节流时间戳）
- [ ] 1.5 修改 L495 bind() 中 cancelPendingDownload 调用点（第一处）：增加节流 + 可见性优先级判断（离视口 > 2 屏才取消）+ 进度阈值检查
- [ ] 1.6 修改 L600 loadImage() 中 cancelPendingDownload 调用点（第二处）：同样应用节流 + 进度阈值 + 可见性优先级检查
- [ ] 1.7 修改 L549-554 cancelPendingDownload 实现：增加进度阈值检查（> 阈值不取消）
- [ ] 1.8 修改 L323 preloadAround：增加 throttle 300ms 机制
- [ ] 1.9 **保持 L326-340 activity destroyed 检查不变**（crash-2026-07-26 铁证）
- [ ] 1.10 **保持 L937-945 onRecycled 现有逻辑不变**（不取消下载，只 clear photoView）
- [ ] 1.11 新增下载进度拦截器（估算 Glide.downloadOnly 进度）
- [ ] 1.12 编译验证（gradlew assembleDebug）
- [ ] 1.13 真机测试：快速滑动图片画布 30 秒，验证图片正常显示
- [ ] 1.14 日志验证："Cronet request canceled" 下降 ≥ 60%，"preloadAround skip: activity destroyed" 不上升
- [ ] 1.15 验证：节流期间并发连接数 ≤ 10
- [ ] 1.16 无 OOM 发生（连续滑动 30 秒）
- [ ] 1.17 commit: `fix(image): FR-1 图片下载取消策略优化（覆盖 bind L495 + loadImage L600 两处取消点）`

> **V2 删除**：
> - "修改 L937-945 onRecycled：改为延迟 500ms 取消"（onRecycled 根本不取消下载）
> - "新增 pendingCancelJob: Job?"（不再需要延迟取消任务）

#### FR-2: ExoPlayer 释放时序优化

- [ ] 1.18 Read `Exo2MediaPlayer.kt` 确认 L408-416 releaseSniffResources、L454-467 release、L78 isReleased 当前代码
- [ ] 1.19 在 releaseSniffResources L408-416 中新增同步停止渲染管线（mInternalPlayer 是父类 protected 字段）：
  ```kotlin
  kotlin.runCatching {
      mInternalPlayer?.let { player ->
          player.stop()
          player.playWhenReady = false
      }
  }
  ```
- [ ] 1.20 保持 scope.cancel() + isReleased = true 不变
- [ ] 1.21 **保持 L414 bufferingTimeoutHandler.removeCallbacks 现有清理逻辑不变**
- [ ] 1.22 不在 releaseSniffResources 中调用 release()（避免主线程阻塞）
- [ ] 1.23 新增日志：AppLog.put("releaseSniffResources: mInternalPlayer stop + setPlayWhenReady(false) called")
- [ ] 1.24 编译验证（gradlew assembleDebug）
- [ ] 1.25 真机测试：切换视频 10 次，验证 releaseSniffResources 后 mInternalPlayer 停止
- [ ] 1.26 日志验证：onDestroyView 主线程耗时增加 < 10ms，无 ANR
- [ ] 1.27 日志验证：延迟来源（基于 0.8 预分析结果确认）
- [ ] 1.28 commit: `fix(video): FR-2 ExoPlayer 释放时序优化（mInternalPlayer 同步 stop）`

> **V2 修正**：
> - 代码片段 `player?.stop()` 中 `player` 变量未定义，修正为 `mInternalPlayer?.let { player -> ... }`
> - 删除"延迟 8-11 秒"描述（onDestroyView L202-203 同步连续无延迟机制，需重新分析）

### 阶段 2: P1 优化（FR-3, FR-4, FR-5）

#### FR-3: 取消后忽略 ExoPlayer 回调

- [ ] 2.1 Read `Exo2MediaPlayer.kt` 确认 L993 onPlaybackStateChanged（不是 onPlayerStateChanged）、L711 onPlayerError、L1044 onRenderedFirstFrame 位置
- [ ] 2.2 新增字段：`private val isScopeCancelled = AtomicBoolean(false)`
- [ ] 2.3 releaseSniffResources 中新增 `isScopeCancelled.set(true)`
- [ ] 2.4 prepareAsync 成功后新增 `isScopeCancelled.set(false)`
- [ ] 2.5 `onPlaybackStateChanged` (L993) 首行新增 `if (isScopeCancelled.get()) return`
- [ ] 2.6 `onPlayerError` (L711) 首行新增 `if (isScopeCancelled.get()) return`
- [ ] 2.7 首帧渲染回调 `onRenderedFirstFrame` (L1044) 首行新增 `if (isScopeCancelled.get()) return`
- [ ] 2.8 新增日志：AppLog.put("callback ignored due to scope cancelled")
- [ ] 2.9 编译验证（gradlew assembleDebug）
- [ ] 2.10 真机测试：切换视频 10 次，验证 cancelled 后无 first frame rendered
- [ ] 2.11 验证：prepareAsync 后标志位正确重置，下次播放回调正常
- [ ] 2.12 commit: `fix(video): FR-3 取消后忽略 ExoPlayer 回调（onPlaybackStateChanged 检查）`

> **V2 修正**：方法名 `onPlayerStateChanged` → `onPlaybackStateChanged` (L993)
> **职责说明**：isScopeCancelled 与 isReleased (L78) 职责不同——isReleased 防止 setMediaItem，isScopeCancelled 防止回调触发业务逻辑

#### FR-4: 切换文章/集数防抖（V3 补充 Job 引用前置修改）

**前置修改**（FR-4 和 FR-6 共享，必须先完成）：
- [ ] 2.13 Read `VideoPlay.kt` 确认 L1126-1167 switchToArticle、L1284-1336 playRssEpisode、L1137/L1294 Coroutine.async 当前代码（确认未保存 Job 引用）
- [ ] 2.14 确认 L220 videoUrl 字段（不是 currentUrl）
- [ ] 2.15 **新增字段**：`private var switchArticleJob: Job? = null`（switchToArticle 异步任务引用）
- [ ] 2.16 **新增字段**：`private var playEpisodeJob: Job? = null`（playRssEpisode 异步任务引用）
- [ ] 2.17 修改 `switchToArticle` L1137 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 赋值给 `switchArticleJob`
- [ ] 2.18 修改 `playRssEpisode` L1294 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 赋值给 `playEpisodeJob`
- [ ] 2.19 编译验证（gradlew assembleDebug）确认前置修改无误

**FR-4 防抖检查**：
- [ ] 2.20 `switchToArticle` (L1126) 入口先 `switchArticleJob?.cancel()` 取消前一个异步任务，再执行新的 Coroutine.async
- [ ] 2.21 `playRssEpisode` (L1284) 入口先 `playEpisodeJob?.cancel()` 取消前一个异步任务，再执行新的 Coroutine.async
- [ ] 2.22 防抖期间记录最后一次切换意图，异步加载完成后执行
- [ ] 2.23 **保持 switchToArticle L1141-1153 source 匹配检查不变**
- [ ] 2.24 防抖检查用 runCatching 包裹，异常时按原逻辑执行
- [ ] 2.25 新增日志：AppLog.put("switchToArticle: debounce, cancel previous async task")
- [ ] 2.26 编译验证（gradlew assembleDebug）
- [ ] 2.27 真机测试：连续快速切换文章 3 次，验证只执行最后一次
- [ ] 2.28 真机测试：切换集数 10 次，验证无 cancel-prepare 10ms 竞争
- [ ] 2.29 验证：连续切换 20 次无任务泄漏
- [ ] 2.30 commit: `fix(video): FR-4 切换文章/集数防抖（含 Job 引用前置修改）`

> **V2 删除**：删除"定位 switchVideo 方法"（switchVideo 不存在）、"确认 currentUrl 字段位置"（currentUrl 字段不存在）
> **V3 补充**：新增前置修改任务 2.15-2.19（Coroutine.async 未保存 Job 引用，源码核实 L1137/L1294）

#### FR-5: 连续慢 TTFB 强制降档（V3 重新定义——不修改 PlayerInstancePool）

- [ ] 2.31 Read `PlayerInstancePool.kt` 确认 L106-113 createLoadControl（已有档位构建逻辑）、L122-149 acquire（L136 setLoadControl）——**不修改**
- [ ] 2.32 Read `ExoPlayerHelper.kt` 确认 L137-174 createLoadControlByTier、L110-117 getCurrentBandwidthTier、L86-88 注释（LoadControl 不可热切换）——复用
- [ ] 2.33 Read `Exo2MediaPlayer.kt` 确认 L1084-1130 TTFB 统计（onLoadStarted L1090 + onLoadCompleted L1105 + loadElapsed 变量 L1112）已完整实现
- [ ] 2.34 **不修改 PlayerInstancePool.createLoadControl**（L106-113 已调用 getCurrentBandwidthTier + createLoadControlByTier）
- [ ] 2.35 **不修改 PlayerInstancePool.acquire**（L122-149 已通过 setLoadControl 设置，L136）
- [ ] 2.36 新增字段：`private var ttfbSlowCount = 0`、`private var ttfbFastCount = 0`、`private var forceTier: BandwidthTier? = null`、`private var lastSwitchTime = 0L`
- [ ] 2.37 在 onLoadCompleted (L1105) 中复用现有 `loadElapsed` 变量，新增降档判断：连续 3 次 TTFB>1000ms → 调用 getCurrentBandwidthTier 获取当前档位，GOOD→MEDIUM / MEDIUM→WEAK 降一档，记录到 forceTier
- [ ] 2.38 在 onLoadCompleted (L1105) 中新增恢复判断：连续 3 次 TTFB<500ms → 清除 forceTier，重置 ttfbSlowCount/ttfbFastCount
- [ ] 2.39 降档后下次 prepareAsyncInternal 时 PlayerInstancePool.acquire 会按新档位构建 LoadControl（复用现有逻辑，无需修改 acquire）
- [ ] 2.40 注意：acquire 命中池（reuse）时不会重新设置 LoadControl，forceTier 降级后需 recycle 旧实例确保下次 acquire 新建
- [ ] 2.41 最小切换间隔 30 秒（防抖动）
- [ ] 2.42 新增日志：AppLog.put("FR-5: forceTier=$forceTier, ttfbSlowCount=$ttfbSlowCount, ttfbFastCount=$ttfbFastCount")
- [ ] 2.43 编译验证（gradlew assembleDebug）
- [ ] 2.44 真机测试：弱网环境播放，验证连续 3 次 TTFB>1000ms 后 forceTier 降档，下次 prepare 使用降档后的档位，BUFFERING→READY 循环下降 ≥ 50%
- [ ] 2.45 真机测试：网络恢复后自动恢复自动档位
- [ ] 2.46 commit: `fix(video): FR-5 连续慢 TTFB 强制降档（复用现有 PlayerInstancePool.createLoadControl）`

> **V3 重大修正**：
> - "prepare 前按带宽档位构建 LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113），不需要修改
> - "ExoPlayerHelper 新增 dynamicLoadControl 方法，支持运行时切换"（技术不可行，L86-88 注释）
> - "onLoadCompleted 中计算 TTFB"（L1084-1130 已完整实现，loadElapsed 变量可复用）
> - "prioritizeTime=true 导致快速起播"（概念错误）

### 阶段 3: P2 修复（FR-6, FR-7）

#### FR-6: switchToArticle 状态保护（V3 补充 Job 引用前置修改）

**前置修改**（与 FR-4 共享，见 FR-4 任务 2.15-2.19，必须先完成）：
- [ ] 3.1 确认 FR-4 前置修改已完成：`switchArticleJob: Job?` 字段已新增，switchToArticle L1137 的 Coroutine.async 已赋值给 switchArticleJob
- [ ] 3.2 Read `VideoPlay.kt` 确认 L1126-1167 switchToArticle、L308-360 startPlay、L1159-1162 withContext(Main) { startPlay } 当前代码
- [ ] 3.3 确认 L353-359 rssArticle null 静默日志逻辑（BUG4 fix，保持不变）
- [ ] 3.4 新增字段：`private var isSwitchingArticle = false`（switchToArticle 状态标志）
- [ ] 3.5 switchToArticle 进入异步加载时设置 `isSwitchingArticle = true`
- [ ] 3.6 异步加载完成（startPlay 调用前）清除 `isSwitchingArticle = false`
- [ ] 3.7 若异步加载期间用户再次触发切换，通过 `switchArticleJob?.cancel()` 取消前一个异步任务（依赖前置修改）
- [ ] 3.8 **预期行为验证**：异步任务被取消后，withContext(Main) 中的 startPlay 不会执行（用户切换到新文章时，旧文章的加载应该被取消）
- [ ] 3.9 **保持 startPlay L353-359 rssArticle null 静默日志逻辑不变**
- [ ] 3.10 新增日志：AppLog.put("switchToArticle: state protected, cancel previous async")
- [ ] 3.11 编译验证（gradlew assembleDebug）
- [ ] 3.12 真机测试：switchToArticle 异步加载期间再次切换，验证前一个异步任务被取消
- [ ] 3.13 真机测试：连续切换 20 次无任务泄漏
- [ ] 3.14 commit: `fix(video): FR-6 switchToArticle 状态保护（异步任务取消）`

> **V2 删除**：
> - "startPlay 中 rssArticle 为 null 时不 return"（正常流程，会引入副作用）
> - "注册一次性回调监听文章加载完成"（引入副作用）
> - "显示 loading indicator"（不在本 FR 范围）
> - "超时 10 秒提示"（不在本 FR 范围）
> **V3 补充**：新增前置修改依赖（3.1）+ 预期行为验证（3.8）

#### FR-7: NullPointerException(monitor-enter) 调用栈重新分析（V3 重新定义）

**Step 1：重新分析调用栈**：
- [ ] 3.15 重新分析 logs(9) 中 NullPointerException(monitor-enter) 的完整调用栈，确认异常发生的真实位置（类名、方法名、行号）
- [ ] 3.16 Grep 排查 `app/src/main/java/io/legado/app/model/` 目录所有 synchronized(this) 块（搜索技术字段 `synchronized\(`），仅作参考
- [ ] 3.17 Read `AudioPlay.kt` 确认 L149, L157 synchronized(this) 块（object 单例，this 非 null，仅作参考）
- [ ] 3.18 Read `CacheBook.kt` 确认 L383 synchronized(this) 块（object 单例，this 非 null，仅作参考）
- [ ] 3.19 Read `ImageProvider.kt` 确认 L69 synchronized(this) 块（object 单例，this 非 null，仅作参考）
- [ ] 3.20 Read `ReadManga.kt` 确认 L85, L107 synchronized(this) 块（object 单例，this 非 null，仅作参考）

**Step 2：定位真实锁对象**：
- [ ] 3.21 根据调用栈定位真实锁对象：
  - 可能是 `synchronized(lockObject)` 中 lockObject 为 null（非 synchronized(this) 场景）
  - 可能是 Java 字节码层面的 monitorenter 指令操作数栈为 null
  - 可能是其他对象的字段在并发场景下被置 null

**Step 3：根据锁对象类型决定修复方案**：
- [ ] 3.22 根据锁对象类型实施修复：
  - 若调用栈指向 `@Synchronized` 注解方法（等价 synchronized(this)），this 不可能为 null（object 单例），需分析其他原因（GC 残留引用、object 初始化未完成等）
  - 若调用栈指向 `synchronized(lockObject)`，检查 lockObject 是否可能为 null，添加非空守卫或改为 `private val lock = Any()`
  - 其他场景根据具体情况定制修复方案
- [ ] 3.23 新增日志（根据修复方案决定日志内容）
- [ ] 3.24 编译验证（gradlew assembleDebug）
- [ ] 3.25 真机测试：连续切换视频 20 次，验证无 NullPointerException(monitor-enter)
- [ ] 3.26 真机测试：Activity 销毁重建过程验证无并发异常
- [ ] 3.27 commit: `fix(image): FR-7 NullPointerException(monitor-enter) 修复（调用栈重新分析）`

> **V3 重大修正**：
> - AudioPlay/ImageProvider/ReadManga/CacheBook 都是 object 单例（源码核实：`object AudioPlay` L40 / `object CacheBook` L42 / `object ImageProvider` L31 / `object ReadManga` L45），this 不可能为 null
> - "为 synchronized(this) 块添加非空守卫"方案无效，已删除
> - 改为"Step 1 重新分析调用栈 → Step 2 定位真实锁对象 → Step 3 根据锁对象类型决定修复方案"三步流程
> **说明**：ImagePlay.kt 只有 `@Synchronized` 注解（L56/66/84/110），无 `synchronized()` 块；@Synchronized 等价 `synchronized(this)`，this 同样不可能为 null。

### 阶段 4: 编译验证

- [ ] 4.1 全量编译（gradlew assembleDebug）
- [ ] 4.2 全量编译（gradlew assembleRelease）验证 release 包无误
- [ ] 4.3 lint 检查（gradlew lint）
- [ ] 4.4 确认无新增警告
- [ ] 4.5 确认无调试日志残留（Grep `android.util.Log.d|android.util.Log.e`，搜索技术字段）

### 阶段 5: 真机测试

- [ ] 5.1 安装测试包 `io.legado.miss.app.debug` 到模拟器/真机
- [ ] 5.2 执行场景 1：快速滑动图片画布（30 秒）→ 验证图片正常显示
- [ ] 5.3 执行场景 2：切换视频（不同文章）10 次 → 验证 releaseSniffResources 后 mInternalPlayer 停止
- [ ] 5.4 执行场景 3：切换视频（同文章不同集数）10 次 → 验证无竞争
- [ ] 5.5 执行场景 4：连续快速切换文章 3 次 → 验证只执行最后一次
- [ ] 5.6 执行场景 5：息屏恢复 → 验证正常恢复
- [ ] 5.7 执行场景 6：弱网络环境播放 → 验证 LoadControl 档位修正
- [ ] 5.8 执行场景 7：switchToArticle 异步加载期间再次切换 → 验证前一个异步任务被取消
- [ ] 5.9 执行场景 8：Activity 销毁重建 → 验证无 NPE
- [ ] 5.10 日志统计：所有验收指标达标（参考 spec.md 验收标准汇总）
- [ ] 5.11 记录问题到 issues-found.md（如有）
- [ ] 5.12 对比原版 legado-E 行为，确认无回归

### 阶段 6: 交付同步

- [ ] 6.1 基于 git diff 分析真实代码变更
- [ ] 6.2 更新 assets/updateLog.md（基于代码变更生成日志，禁止文字合并）
- [ ] 6.3 逐文件审计：对照变更文件列表确认每个变更有对应日志条目
- [ ] 6.4 面向用户语言描述可感知变化（不暴露内部技术术语）
- [ ] 6.5 更新 .trae/memory/ai_memory_main.md（任务状态、经验持久化）
- [ ] 6.6 更新 issues-found.md（如有问题）
- [ ] 6.7 检查文档同步：tasks.md / INDEX.md / project_memory 是否最新
- [ ] 6.8 主动沉淀：反思工作方法（spec-sedimentation-mechanism.md）

---

## 任务依赖关系

```
阶段0（准备）
    │
    ├─ 0.8 FR-2 延迟根因预分析（必须先完成）
    │
    ▼
阶段1（P0: FR-1, FR-2）── 必须完成才能进入阶段2
    │
    ▼
阶段2（P1: FR-3, FR-4, FR-5）── FR-3 依赖 FR-2（标志位配合）
    │                          ── FR-4, FR-5 独立
    ▼
阶段3（P2: FR-6, FR-7）── 独立
    │
    ▼
阶段4（编译验证）
    │
    ▼
阶段5（真机测试）
    │
    ▼
阶段6（交付同步）
```

**并行可能性**：
- FR-3 与 FR-4 可并行（不同文件）
- FR-5 与 FR-6 可并行（不同文件）
- FR-7 可与阶段 2 任何 FR 并行

---

## 备份要求

每个 FR 实施前必须备份关键文件：

| FR | 备份文件 | 备份路径 |
|----|---------|---------|
| FR-1 | ImageCanvasAdapter.kt | `.bak/image-thread-coordination-fix-20260731/ImageCanvasAdapter.kt` |
| FR-2 | Exo2MediaPlayer.kt | `.bak/image-thread-coordination-fix-20260731/Exo2MediaPlayer.kt` |
| FR-3 | Exo2MediaPlayer.kt | 同上（与 FR-2 同文件，合并备份） |
| FR-4 | VideoPlay.kt | `.bak/image-thread-coordination-fix-20260731/VideoPlay.kt` |
| FR-5 | Exo2MediaPlayer.kt（**不备份 PlayerInstancePool.kt**，不修改） | 同上（与 FR-2/FR-3 同文件，合并备份） |
| FR-6 | VideoPlay.kt | 同上（与 FR-4 同文件，合并备份） |
| FR-7 | 待调用栈重新分析后确认（参考：AudioPlay.kt / CacheBook.kt / ImageProvider.kt / ReadManga.kt） | `.bak/image-thread-coordination-fix-20260731/` |

---

## 验收检查清单

| # | 检查项 | 验证方法 |
|---|--------|---------|
| 1 | FR-1 图片快速滑动后正常显示 | 真机场景 1 |
| 2 | FR-1 "Cronet request canceled" 下降 ≥ 60% | 日志统计 |
| 3 | FR-1 "preloadAround skip: activity destroyed" 不上升 | 日志统计 |
| 4 | FR-1 节流期间并发连接数 ≤ 10 | 日志验证 |
| 5 | FR-2 releaseSniffResources 后 mInternalPlayer 停止 | 日志验证 |
| 6 | FR-2 onDestroyView 主线程耗时增加 < 10ms | 日志时间戳 |
| 7 | FR-2 无 ANR | 真机验证 |
| 8 | FR-3 cancelled 后无 first frame rendered | 日志验证 |
| 9 | FR-3 prepareAsync 后标志位重置 | 日志验证 |
| 10 | FR-4 切换文章/集数无 cancel-prepare 竞争 | 日志验证 |
| 11 | FR-4 连续切换无任务泄漏 | 日志验证 |
| 12 | FR-5 BUFFERING→READY 循环下降 ≥ 50% | 日志统计 |
| 13 | FR-5 网络恢复自动恢复自动档位 | 真机验证 |
| 14 | FR-6 switchToArticle 异步任务取消无泄漏 | 日志验证 |
| 15 | FR-7 无 NullPointerException(monitor-enter) | 日志验证 |
| 16 | 无调试日志残留 | Grep 验证 |
| 17 | updateLog.md 已更新 | 文件检查 |
| 18 | 无回归（对比原版） | 真机对比 |
| 19 | 思考过程无违禁词 | 自检 |
| 20 | 真机测试包正确（debug 包） | 包名验证 |
| 21 | 备份文件已创建 | 文件检查 |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| FR-1 进度阈值估算不准确 | 通过拦截器估算，误差可接受；异常时 fallback 立即取消 |
| FR-1 节流期间连接数失控 | 最大并发连接数上限 ≤ 10，超过上限时立即取消最早的下载 |
| FR-2 stop() 触发额外回调 | 配合 FR-3 标志位忽略回调 |
| FR-2 延迟根因未确认 | 0.8 预分析必须先完成，确认延迟来源后再实施 |
| FR-3 标志位未重置 | prepareAsync 成功后必须重置，增加日志监控 |
| FR-4 防抖期间丢失切换意图 | 记录最后一次切换意图，异步加载完成后执行 |
| FR-4 Job 引用未保存 | 前置修改 2.15-2.19 必须先完成，保存 switchArticleJob/playEpisodeJob |
| FR-5 档位修正延迟 | 档位修正只在下次 prepare 生效，当前播放期间无法即时调整 |
| FR-5 频繁切换档位抖动 | 最小切换间隔 30 秒 |
| FR-5 acquire 命中池不更新 LoadControl | forceTier 降级后需 recycle 旧实例确保下次 acquire 新建 |
| FR-6 异步任务取消异常 | runCatching 包裹 switchArticleJob?.cancel()，异常时按原逻辑执行 |
| FR-7 遗漏 synchronized 块 | Grep 全面排查 model 目录，搜索技术字段 `synchronized\(`（仅作参考） |
| FR-7 真实锁对象未定位 | Step 1 重新分析调用栈 → Step 2 定位真实锁对象 → Step 3 根据锁对象类型决定修复方案 |

---

## 完成标准

所有任务项标记为 `[x]`，且：
1. 所有 FR 的验收标准达标（参考 spec.md）
2. 真机测试无 crash、无 ANR、无回归
3. updateLog.md 已更新
4. 调试日志已清理
5. 文档同步完成
6. 经验已沉淀到 ai_memory_main.md
7. 备份文件已创建

---

## V3修订记录（2026-07-31）

> **修订背景**：V2重构后交叉验证审查发现3个高优先级阻塞点，V3修复后直接进入实施阶段。

### 修订1：FR-5任务更新——不修改PlayerInstancePool

- **根因**：源码核实发现"prepare前按带宽档位构建LoadControl"已是现有行为（PlayerInstancePool.createLoadControl L106-113 + acquire L136）
- **修改内容**：
  - 阶段0准备：0.1新增PlayerInstancePool.kt的L106-113 createLoadControl和L122-149 acquire读取
  - FR-5任务：2.31-2.46重新定义为"不修改PlayerInstancePool"，只修改Exo2MediaPlayer.onLoadCompleted新增ttfbSlowCount降档判断
  - 备份要求：FR-5备份文件标注"不备份PlayerInstancePool.kt，不修改"
  - 风险与缓解：新增"FR-5 acquire命中池不更新LoadControl"风险

### 修订2：FR-7任务更新——调用栈重新分析三步流程

- **根因**：源码核实发现AudioPlay/ImageProvider/ReadManga/CacheBook都是object单例，this不可能为null，"添加非空守卫"方案无效
- **修改内容**：
  - FR-7任务：3.15-3.27重新定义为三步流程（Step1重新分析调用栈→Step2定位真实锁对象→Step3根据锁对象类型决定修复方案）
  - 阶段3排查任务：AudioPlay/CacheBook/ImageProvider/ReadManga的synchronized(this)块标注"object单例，this非null，仅作参考"
  - 备份要求：FR-7备份文件改为"待调用栈重新分析后确认"
  - 风险与缓解：FR-7真实锁对象未定位的缓解措施改为三步流程

### 修订3：FR-4/FR-6任务补充Job引用前置修改

- **根因**：源码核实发现switchToArticle L1137 / playRssEpisode L1294的Coroutine.async未保存Job引用
- **修改内容**：
  - FR-4任务：2.13-2.30重新定义，新增前置修改任务2.15-2.19（switchArticleJob/playEpisodeJob字段+赋值），FR-4防抖检查改为2.20-2.30
  - FR-6任务：3.1-3.14重新定义，新增前置修改依赖3.1（确认FR-4前置修改已完成）+ 预期行为验证3.8
  - 风险与缓解：新增"FR-4 Job引用未保存"风险
