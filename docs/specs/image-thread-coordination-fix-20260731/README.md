# 图片加载与视频切换线程协调修复

> **状态**: 🔄 部分实施（FR-2/3/4/5/6 已落地；FR-1 进度阈值、FR-7 待查补）
> **创建日期**: 2026-07-31
> **版本**: 2.0
> **负责人**: AI 开发
> **优先级**: P0（图片加载）+ P0（线程协调）
> **审查基线**: audit-report-v1.md（12 ERROR + 12 WARN 全部整改）

---

## 功能概述

针对用户测试 073121 正式包后反馈的两类核心问题进行系统性修复：

1. **图片加载问题**：图片画布（漫画/图集模式）快速滑动时图片显示空白，无法正常加载
2. **线程协调调度问题**：切换视频时可感知到线程协调调度异常，存在释放延迟、回调竞争、缓冲震荡等多重问题

本 spec 基于源码行号级根因分析（V2 已对 6 个源码文件逐行核实），提出 7 个功能需求（FR-1 ~ FR-7），覆盖图片层、播放器层、网络层三个层面的优化。

---

## 用户反馈原文

> "整体评估，视频嗅探能力可以了，但是图片还是不行，并且还有一个问题是，现在切换视频的时候明显能够感觉到线程的协调调度还是有点问题"

---

## 问题根因摘要（V2 源码核实结论）

### 图片加载根因
- **取消点遗漏**：`ImageCanvasAdapter` 存在**两处** `cancelPendingDownload()` 调用点（bind L495 + loadImage L600），同一流程连续两次取消，导致 Glide.downloadOnly 下载被频繁打断
- **onRecycled 不取消**：早期假设"onRecycled 取消下载"错误——`onRecycled` (L937-945) 只 `clear(photoView)` + 重置字段，**不调用** `cancelPendingDownload`
- **preloadAround 已有保护**：L326-340 已有 activity destroyed 检查（crash-2026-07-26 铁证），保持不变

### 线程协调根因
- **onDestroyView 无延迟机制**：`VideoFragment.onDestroyView` (L196-225) 中 L202 `releaseSniffResources` + L203 `releasePlayer` 是**同步连续调用**，无 Handler.post/postDelayed。早期"延迟 8-11 秒"的根因需重新分析（可能来自 super.reset() 或日志时间戳跨边界）
- **releaseSniffResources 无 player 引用**：L408-416 只做 `scope.cancel()` + `removeCallbacks` + `isReleased=true`，未停止 mInternalPlayer 渲染管线
- **方法名错误**：Media3 中 `onPlayerStateChanged` 已废弃，实际为 `onPlaybackStateChanged` (L993)
- **切换锚点错误**：VideoPlay.kt 无 `switchVideo` 函数，实际切换逻辑是 `switchToArticle` (L1126) + `playRssEpisode` (L1284)；字段是 `videoUrl` (L220) 非 `currentUrl`
- **rssArticle null 是正常流程**：L353-359 已有 BUG4 fix 静默日志，注释明确"正常滑动退出时 rssArticle 变 null 属正常流程"

### 网络层根因
- **prepare 前按档位构建已是现有行为**：`PlayerInstancePool.createLoadControl()` (L106-113) 已调用 `ExoPlayerHelper.getCurrentBandwidthTier()` + `createLoadControlByTier(tier, sharedAllocator)`；`acquire()` (L122-149) 在新建 ExoPlayer 时通过 `.setLoadControl(createLoadControl())` (L136) 设置 LoadControl——FR-5 不需要修改 PlayerInstancePool，只需新增"连续 3 次 TTFB>1000ms 强制降档"判断
- **LoadControl 不可运行时热切换**：ExoPlayerHelper.kt L86-88 注释明确"LoadControl 只能在 player 构建时设置，运行时不可热切换"
- **已有优化基线**：createLoadControlByTier (L137-174) 已实现 WEAK/MEDIUM/GOOD 三档；bandwidthMeter (L92-94) 已实时测量；TTFB 统计 (L1084-1130) 已完整实现（loadElapsed 变量可复用）
- **prioritizeTime 概念澄清**：`setPrioritizeTimeOverSizeThresholds(true)` (L147) 是"时间优先于字节，确保 maxBuffer 时长真正生效"，**不是**"快速起播"。控制起播的是 `bufferForPlayback` (L152/157/162 的 500ms/800ms/500ms)

---

## 核心能力（7 个 FR）

| FR | 优先级 | 模块 | 问题描述 | 修复方向（V3） |
|----|--------|------|---------|---------|
| FR-1 | P0 | 图片层 | 快速滑动时 bind L495 + loadImage L600 两处取消点频繁打断下载 | 节流 + 进度阈值 + 可见性优先级（同时覆盖两处取消点） |
| FR-2 | P0 | 播放器层 | releaseSniffResources 未停止 mInternalPlayer 渲染管线 | releaseSniffResources 同步 stop + setPlayWhenReady(false)（mInternalPlayer 是父类 protected 字段） |
| FR-3 | P1 | 播放器层 | scope cancelled 后仍触发回调 | isScopeCancelled 标志位，onPlaybackStateChanged/onPlayerError/首帧回调检查 |
| FR-4 | P1 | 播放器层 | 切换文章/集数时存在 cancel-prepare 竞争 | switchToArticle L1126 / playRssEpisode L1284 防抖（含 Job 引用前置修改） |
| FR-5 | P1 | 网络层 | 弱网下 BUFFERING→READY 循环 | 连续慢 TTFB 强制降档（复用现有 PlayerInstancePool.createLoadControl 档位构建逻辑） |
| FR-6 | P2 | 播放器层 | switchToArticle 异步加载期间 rssArticle 临时为 null | switchToArticle 状态保护（保留 startPlay 现有静默日志） |
| FR-7 | P2 | 图片层 | NullPointerException(monitor-enter) 并发异常 | 调用栈重新分析（object 单例 this 非 null，非空守卫无效） |

---

## 修复目标

### 图片加载目标
- 快速滑动时，已下载超过阈值的图片不再被取消，能完整写入磁盘缓存
- 滑动停止后 500ms 内，未复用的 ViewHolder 下载被有序取消
- "preloadAround skip: activity destroyed" 日志频次不上升（已有保护不变）
- "Cronet request canceled (normal)" 日志频次下降 ≥ 60%

### 线程协调目标
- releaseSniffResources 同步停止 mInternalPlayer 渲染管线（stop + setPlayWhenReady false）
- scope cancelled 后不再触发 first frame rendered（竞争消除）
- 切换文章/集数时无 cancel-prepare 竞争
- 连续 TTFB>1000ms 场景下，档位修正后 BUFFERING→READY 循环次数下降 ≥ 50%

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 功能概述、根因摘要、FR 列表、源码锚点（本文档） |
| [spec.md](./spec.md) | Intent / Scope / Approach / Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单（按阶段组织） |
| [audit-report-v1.md](./audit-report-v1.md) | V1 审查报告（12 ERROR + 12 WARN） |

---

## 源码核实锚点表（V2 真实路径，已逐行核实）

| 模块 | 文件 | 关键行号 | 核实内容 |
|------|------|---------|---------|
| 图片适配器 | `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` | L323-340 | preloadAround（已有 activity destroyed 检查） |
| | | L466 | bind() 入口 |
| | | L495 | bind() 内 cancelPendingDownload 调用点（第一处） |
| | | L549-554 | cancelPendingDownload 实现 |
| | | L599-606 | loadImage() 入口，L600 cancelPendingDownload 调用点（第二处） |
| | | L937-945 | onRecycled（只 clear photoView，不取消下载） |
| 媒体播放器 | `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | L125-139 | bufferingTimeoutHandler |
| | | L408-416 | releaseSniffResources（无 player 引用，只有 scope.cancel + removeCallbacks） |
| | | L454-467 | release()（调用 releaseSniffResources 双保险 + PlayerInstancePool.recycle） |
| | | L993 | onPlaybackStateChanged（不是 onPlayerStateChanged） |
| | | L1084 | loadStartTimeMs 字段（TTFB 统计已有） |
| | | L1090-1097 | onLoadStarted（记录 loadStartTimeMs） |
| | | L1105-1130 | onLoadCompleted（计算 TTFB，告警阈值 500ms） |
| LoadControl | `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | L86-88 | 注释：LoadControl 只能构建时设置，运行时不可热切换 |
| | | L92-94 | bandwidthMeter（DefaultBandwidthMeter 全局单例） |
| | | L99-103 | BandwidthTier 枚举（WEAK/MEDIUM/GOOD 三档） |
| | | L110-117 | getCurrentBandwidthTier |
| | | L137-174 | createLoadControlByTier（已有完整三档配置） |
| | | L145 | setTargetBufferBytes(-1) |
| | | L147 | setPrioritizeTimeOverSizeThresholds(true)（时间优先于字节） |
| | | L152/157/162 | bufferForPlayback = 500ms/800ms/500ms |
| 播放器池 | `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` | L106-113 | createLoadControl()（**已有档位构建**，调用 getCurrentBandwidthTier + createLoadControlByTier） |
| | | L122-149 | acquire()（L136 setLoadControl，**新建实例时设置 LoadControl**） |
| | | L167-193 | recycle()（同步执行 stop/clearMediaItems/clearVideoSurface 等） |
| 视频片段 | `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | L196-225 | onDestroyView（L202 releaseSniffResources + L203 releasePlayer 同步连续） |
| | | L333-335 | releasePlayer()（`_playerView?.currentPlayer?.release()`） |
| VideoPlay | `app/src/main/java/io/legado/app/model/VideoPlay.kt` | L220 | videoUrl 字段（不是 currentUrl） |
| | | L308-360 | startPlay()（L353-359 rssArticle null 是正常流程，已有 BUG4 fix 静默日志） |
| | | L1126-1167 | switchToArticle()（已有 source 匹配检查 L1141-1153） |
| | | L1284-1336 | playRssEpisode()（集数切换） |

### synchronized(this) 块真实位置（FR-7 参考排查——object 单例 this 非 null）

> **V3 重大修正**：AudioPlay/ImageProvider/ReadManga/CacheBook **都是 object 单例**（源码核实：`object AudioPlay` L40 / `object CacheBook` L42 / `object ImageProvider` L31 / `object ReadManga` L45），this 不可能为 null，"添加非空守卫"方案无效。FR-7 改为"调用栈重新分析 → 定位真实锁对象 → 根据锁对象类型决定修复方案"三步流程。

| 文件 | 行号 | 说明 |
|------|------|------|
| `app/src/main/java/io/legado/app/model/AudioPlay.kt` | L149, L157 | synchronized(this) 块（object 单例，this 非 null） |
| `app/src/main/java/io/legado/app/model/CacheBook.kt` | L383 | synchronized(this) 块（object 单例，this 非 null） |
| `app/src/main/java/io/legado/app/model/ImageProvider.kt` | L69 | synchronized(this) 块（object 单例，this 非 null） |
| `app/src/main/java/io/legado/app/model/ReadManga.kt` | L85, L107 | synchronized(this) 块（object 单例，this 非 null） |

> **注意**：ImagePlay.kt 只有 `@Synchronized` 注解（L56/66/84/110），无 `synchronized()` 块；@Synchronized 等价 `synchronized(this)`，this 同样不可能为 null。

---

## 风险与回滚

- **风险等级**：中（涉及图片加载核心路径 + ExoPlayer 释放时序）
- **回滚策略**：每个 FR 独立 commit，可通过 git revert 单独回滚
- **灰度验证**：P0 修复后必须真机测试包（`io.legado.miss.app.debug`）验证，禁止直接交付
- **回归检查**：必须对比原版 legado-E 行为，避免引入新的回归

---

## 后续规划

- 本 spec 完成后，需同步更新 `assets/updateLog.md`（基于 git diff 真实代码变更）
- 测试遵循 `ai_e2e_testing_workflow.md`，使用 `ai_tests/scripts/` 固定脚本
- 真机测试包选择遵循 `package-naming.md`（代码优化任务用 debug 包）

---

## V3修订记录（2026-07-31）

> **修订背景**：V2重构后交叉验证审查发现3个高优先级阻塞点，V3修复后直接进入实施阶段。

### 阻塞点1：FR-5方案描述修正

**问题**：文档说"prepare前按带宽档位构建LoadControl"，但源码核实发现这**已是现有行为**。

**源码核实结论**：
- `PlayerInstancePool.createLoadControl()` (L106-113) 已调用 `getCurrentBandwidthTier()` + `createLoadControlByTier(tier, sharedAllocator)`
- `PlayerInstancePool.acquire()` (L122-149) 在新建 ExoPlayer 时通过 `.setLoadControl(createLoadControl())` (L136) 设置 LoadControl

**修复**：FR-5重新定义为"连续慢TTFB强制降档"——不修改PlayerInstancePool（已有档位构建），只在`Exo2MediaPlayer.onLoadCompleted` (L1105) 中复用现有`loadElapsed`变量，新增`ttfbSlowCount`计数器，连续3次TTFB>1000ms时强制降一档（GOOD→MEDIUM / MEDIUM→WEAK）。

### 阻塞点2：FR-7重新定义

**问题**：文档说"为AudioPlay/ImageProvider/ReadManga/CacheBook的synchronized(this)块添加非空守卫"，但这些是object单例，this不可能为null。

**源码核实结论**：
- `object AudioPlay` (L40) / `object CacheBook` (L42) / `object ImageProvider` (L31) / `object ReadManga` (L45) 都是object单例
- object单例的this不可能为null，"添加非空守卫"方案毫无意义

**修复**：FR-7重新定义为"NullPointerException(monitor-enter)调用栈重新分析"——删除"添加非空守卫"方案，改为"Step1重新分析调用栈→Step2定位真实锁对象→Step3根据锁对象类型决定修复方案"三步流程。

### 阻塞点3：FR-4/FR-6补充Job引用前置修改

**问题**：switchToArticle L1137 / playRssEpisode L1294 的 Coroutine.async 未保存Job引用，"取消前一个异步任务"需先修改保存Job作为前置条件。

**源码核实结论**：
- `switchToArticle` L1137 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 未保存Job引用
- `playRssEpisode` L1294 的 `Coroutine.async(loadScope, IO) {...}.onError {...}` 同样未保存Job引用

**修复**：在FR-4和FR-6中新增前置修改说明——新增`switchArticleJob: Job?`和`playEpisodeJob: Job?`字段，Coroutine.async赋值给对应Job字段，切换前先`switchArticleJob?.cancel()` / `playEpisodeJob?.cancel()`取消前一个异步任务。FR-6补充预期行为说明：异步任务被取消后withContext(Main)中的startPlay不会执行（预期行为）。
