# 视频播放失败修复 - 项目导航

> **创建时间**：2026-07-26 18:05
> **V2修订**：2026-07-26 18:50（基于源码深度分析，修正4个Bug根因+补充17个新遗漏Bug+修正8项修复方案+重构1项修复方案）
> **状态**：V2源码深度分析完成，待用户审查
> **优先级**：P0（用户核心诉求）

---

## §1 项目简介

### 1.1 背景

用户真机测试反馈："**好多视频订阅源使用的内置视频播放器，现在还是播放不了**"。

V1 文档基于 logcat 日志分析（5236KB，3 个有效案例 + 8 个未进入播放阶段）创建，识别 10 个 Bug。V2 通过源码深度分析（对照 `VideoUrlExtractor.kt` / `ExoPlayerHelper.kt` / `Exo2MediaPlayer.kt` / `VideoPlayerActivity.kt` 4 个源码文件），**修正 4 个 Bug 根因错误**，**新发现 17 个遗漏 Bug**，共 **27 个 Bug** 需要修复，确认**代码问题为主，源站问题为辅**。

### 1.2 核心目标

| 指标 | 当前值 | V2目标值 | 提升幅度 | 修复来源 |
|------|--------|----------|----------|---------|
| 视频地址获取时间 | 8.5 秒 | < 3 秒 | -65% | P0修复：第一层超时+总超时+R5参数优化 |
| 嗅探成功率 | 60% | ≥ 90% | +30% | P1修复：协程取消响应+readLimitedBytes循环检查 |
| 播放失败可追溯率 | 0% | 100% | +100% | AppLog.put替代Log.d |
| 降级链正确率 | 0% | 100% | +100% | Bug-7修复：按嗅探结果排序降级链 |
| 状态变量污染率 | 100% | 0% | -100% | Bug-13修复：prepareAsyncInternal入口重置 |
| VideoPlay单例串扰 | 100% | 0% | -100% | Bug-14修复：per-Activity实例或状态快照 |
| 幽灵日志数量 | 多个 | 0 | -100% | T1.8修正+T1.9补充 |

### 1.3 预期收益

- **用户体验**：视频地址获取时间从 8.5 秒降至 3 秒以内，用户不再因等待过久而退出
- **播放成功率**：嗅探成功率提升至 90%+，降级链按嗅探结果正确排序
- **可观测性**：所有播放失败可追溯（AppLog.put 替代 Log.d），便于后续优化
- **资源管理**：Activity 销毁后立即取消嗅探协程，无幽灵日志和内存泄漏
- **降级链正确性**：MP4 直链走 ProgressiveMediaSource，不再误走 HlsMediaSource
- **状态隔离**：8 个 Activity 实例快速切换时状态不串扰

---

## §2 V2 修订摘要

### 2.1 V1 → V2 变更统计

| 维度 | V1 数值 | V2 数值 | 变更说明 |
|------|---------|---------|---------|
| Bug 总数 | 10 | 27 | 修正 4 个根因 + 新增 17 个 |
| P0 严重 Bug | 4 | 9 | +5（NEW-P0-1~5） |
| P1 中等 Bug | 4 | 15 | +11（NEW-P1-1~12，去重后） |
| P2 低优先级 Bug | 2 | 3 | +1（Bug-28 合并 8 个 P2/P3 问题） |
| 任务总数 | 24 | 38 | +14（Phase 1 +5 / Phase 2 +8 / Phase 4 +1） |
| 修复方案需修正数 | — | 8 | T1.1/T1.2/T1.4/T1.5/T1.8/T1.9/T2.1/T2.3 |
| 修复方案需重构数 | — | 1 | T2.1（1秒防重→同一URL+headers才跳过） |
| 功能需求数 | — | 12 | FR-1~FR-12 |

### 2.2 V2 关键发现

1. **V1 文档最大遗漏**：T1.1/T1.2 只改默认值无效（NEW-P0-1 / Bug-11），必须修改 3 处硬编码调用（`VideoUrlExtractor.kt` L489 + `VideoPlay.kt` L316/L427）
2. **Bug-1 真正主因**：第一层 MacCMS 解析 `analyzeUrl.getStrResponseAwait()`(L468) 无超时控制（NEW-P0-2 / Bug-12），而非 R5 网络抓包 delayTime
3. **Bug-6 核心根因**：`VideoPlay` 全局 `object` 单例（L62）状态串扰（NEW-P0-4 / Bug-14），8 个 Activity 共享状态
4. **Bug-7 根因错误**：不是"主线程超时"，是"降级链默认 HLS 优先（contentType=2）与 MP4 直链（contentType=4）不匹配"
5. **T1.8 改造点2 位置错误**：`VideoPlayerActivity` 不直接持有 `exo2MediaPlayer` 引用，应在 `VideoFragment.onDestroyView` 中调用 `release()`

### 2.3 V2 修复方案变更

| 任务 | V1 方案 | V2 修正 |
|------|---------|---------|
| T1.1/T1.2 | 改默认值 | 抽取常量 + 修改 3 处硬编码调用 |
| T1.4 | sniffWithRangeRequestR4 检查 isActive | 补充 readLimitedBytes 循环检查 + import 补充 |
| T1.5 | MutableStateFlow 实时更新 | 重构：按嗅探结果排序降级链（废弃 StateFlow） |
| T1.8 | Activity onDestroy 调用 release() | 修正位置：VideoFragment.onDestroyView + isReleased 标志位 |
| T1.9 | 嗅探协程检查 isActive | 补充：applyMediaSourceByType 内部也检查 |
| T2.1 | 1 秒内防重 | 重构：同一 URL+headers 才跳过 |
| T2.3 | BUFFERING 超时 5 秒 | 修正：12 秒（避免弱网误降级） |

---

## §3 文档导航

| 文档 | 内容 | V2状态 |
|------|------|--------|
| [spec.md](./spec.md) | 功能规格 + 27 个 Bug 清单 + 12 项功能需求（FR-1~FR-12）+ 验收标准 + 非目标 | ✅ V2完成 |
| [design.md](./design.md) | 架构设计 + Bug 详细分析 + 关键技术决策 + 修复方案 | ⏳ V2待更新 |
| [tasks.md](./tasks.md) | 分阶段任务清单（38 项）+ 验收节点 | ⏳ V2待更新 |
| [README.md](./README.md) | 项目导航 + 快速入口（本文档） | ✅ V2完成 |
| [源码深度分析汇总报告](../../temp-analysis/video-playback-failure-source-analysis-20260726.md) | 4 个源码文件深度分析 + Bug 根因验证 + 新遗漏点清单 | ✅ 完成 |
| [原分析报告](../../temp-analysis/video-playback-failure-analysis-20260726.md) | logcat 日志分析（V1 基础） | ✅ 完成 |

---

## §4 快速入口

### 4.1 实施入口

```bash
# 1. 编译测试包（代码优化任务必须用测试包）
gradlew assembleDebug

# 2. 安装到模拟器/真机
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 3. 启动应用
adb shell am start -n io.legado.miss.app.debug/io.legado.app.ui.MainActivity

# 4. 收集 AppLog
adb shell run-as io.legado.miss.app.debug cat /data/data/io.legado.miss.app.debug/files/appLog.txt > appLog.txt

# 5. 收集 logcat
adb logcat -d > logcat.txt
```

### 4.2 关键文件清单（V2 扩展）

| 文件 | 改造点 | 任务编号 |
|------|--------|---------|
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | R5 常量抽取 + 第一层超时 + 总超时 + 各阶段耗时日志 + 协程取消守卫 + 第三层兜底 | T1.1, T1.2, T1.10, T1.11, T1.14, T2.5, T2.9, T2.11 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | SNIFF_TIMEOUT_MS + isActive 检查 + readLimitedBytes 循环检查 + sniffVideoType 复用缓存 | T1.3, T1.4, T1.6, T2.13 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | 降级链排序 + 状态变量重置 + onPlayerError AppLog + onPlaybackStateChanged + release() + isReleased 标志位 + 重复 Init 检测 + BUFFERING 超时降级 + UnrecognizedInputFormatException 触发降级 | T1.5, T1.6, T1.7, T1.8, T1.9, T1.12, T1.13, T2.1, T2.2, T2.3, T2.4, T2.7 |
| `app/src/main/java/io/legado/app/ui/book/VideoPlayerActivity.kt` | initSource 协程取消 + onPause/onStop 暂停 | T2.8, T2.12 |
| `app/src/main/java/io/legado/app/data/entities/VideoPlay.kt` | 3 处硬编码调用修改 + 单例状态改造 + 兜底返回 null | T1.10, T1.13, T2.10 |
| `app/src/main/java/io/legado/app/ui/book/VideoFragment.kt` | onDestroyView 调用 release() | T1.8 改造点2 |

### 4.3 关键 Bug 清单（V2，27 个）

#### 🔴 P0 严重 Bug（9 个）

| Bug | 严重程度 | 影响 | 解决任务 |
|-----|---------|------|---------|
| Bug-1 视频地址获取耗时过长 | P0 | 用户等不及退出 | T1.1, T1.2, T1.10, T1.11, T1.14 |
| Bug-2 重复嗅探+重复 setMediaSource | P0 | 浪费请求+状态错乱 | T1.12, T1.13, T2.1, T2.2 |
| Bug-3 嗅探超时 3000ms 太短+协程取消不响应 | P0 | 嗅探结果丢失 | T1.3, T1.4, T1.6 |
| Bug-7 降级链使用过期嗅探结果 | P0 | MP4 走 HLS 必然失败 | T1.5 |
| Bug-11（新）3 处硬编码调用导致默认值修改无效 | P0 | Bug-1 修复方案失效 | T1.10 |
| Bug-12（新）第一层 MacCMS 解析无超时控制 | P0 | 第一层卡死 60s | T1.11 |
| Bug-13（新）状态变量跨视频污染 | P0 | 降级链走错路径 | T1.12 |
| Bug-14（新）VideoPlay 全局单例状态串扰 | P0 | 8 实例快速切换状态被覆盖 | T1.13, T2.8 |
| Bug-15（新）三层串行执行累计耗时超长 | P0 | 累计最长 70s | T1.14 |

#### 🟠 P1 中等 Bug（15 个）

| Bug | 严重程度 | 影响 | 解决任务 |
|-----|---------|------|---------|
| Bug-4 ExoPlayer 错误未记录 AppLog | P1 | 无法定位失败原因 | T1.6 |
| Bug-5 嗅探协程生命周期错位 | P1 | 幽灵日志+内存泄漏 | T1.8, T1.9, T2.4 |
| Bug-6 8 个视频未进入 ExoPlayer 阶段 | P1 | 用户感觉播放不了 | T1.13, T2.8 |
| Bug-8 onPlayerError 未触发降级链 | P1 | 降级链形同虚设 | T2.3, T2.7 |
| Bug-9 BUFFERING 状态被 Release 中断 | P1 | 用户退出即放弃 | T1.7, T2.3 |
| Bug-16（新）第三层失败返回非视频流 URL | P1 | ExoPlayer 加载失败 | T2.9 |
| Bug-17（新）L496 catch 未守卫 CancellationException | P1 | 协程取消被吞 | T2.11 |
| Bug-18（新）L483 catch 未守卫 CancellationException | P1 | 同 Bug-17 | T2.11 |
| Bug-19（新）VideoPlay.kt L436 兜底返回 rssArticle.link | P1 | ExoPlayer 必然加载失败 | T2.10 |
| Bug-20（新）sniffVideoType 与 sniffMimeType 重复嗅探 | P1 | 同一 URL 嗅探两次 | T2.13 |
| Bug-21（新）readLimitedBytes 循环不响应协程取消 | P1 | 协程取消后仍继续读取 | T1.6 |
| Bug-22（新）UnrecognizedInputFormatException 不触发降级链 | P1 | 降级链不启动 | T2.7 |
| Bug-23（新）applyMediaSourceByType 非 suspend 无法响应 cancel | P1 | scope.cancel 无效 | T1.8 增强 |
| Bug-24（新）mInternalPlayer 重复创建未显式 release 旧实例 | P1 | 资源泄漏 | T1.13 |
| Bug-25（新）initSource 协程未在快速切换时及时取消 | P1 | 前一个协程继续运行 | T2.8 |
| Bug-26（新）onPause/onStop 未暂停视频播放 | P1 | 后台继续播放 | T2.12 |
| Bug-27（新）T1.8 改造点2 位置错误 | P1 | V1 方案无法实施 | T1.8 修正 |

#### 🟡 P2 低优先级 Bug（3 个）

| Bug | 严重程度 | 影响 | 解决任务 |
|-----|---------|------|---------|
| Bug-10 Glide 加载站点 favicon 失败 | P2 | 干扰日志分析 | 不修复（另立 spec） |
| Bug-28（新）sniffVideoType 缓存+线程安全+死代码等 8 个 P2/P3 问题 | P2 | 间接影响 | 按需修复 |
| — | P2 | — | — |

---

## §5 阶段任务概览（V2，38 项）

### Phase 1：P0 核心改造（14 项，原 9 项 + 新增 5 项）

- **VideoUrlExtractor.kt（5 项）**：T1.1 R5 delayTime 降低 + T1.2 R5 timeout 降低 + T1.10 抽取常量修改 3 处硬编码（新）+ T1.11 第一层 withTimeout 包裹（新）+ T1.14 总超时 12 秒（新）
- **ExoPlayerHelper.kt（2 项）**：T1.3 SNIFF_TIMEOUT_MS 提升至 5000ms + T1.4 isActive 检查 + readLimitedBytes 循环检查
- **Exo2MediaPlayer.kt（6 项）**：T1.5 降级链按嗅探结果排序（重构）+ T1.6 onPlayerError AppLog + T1.7 onPlaybackStateChanged 日志 + T1.8 release()+isReleased 标志位（修正位置）+ T1.9 applyMediaSourceByType isActive 检查 + T1.12 状态变量重置（新）+ T1.13 旧 mInternalPlayer release（新）
- **VideoPlay.kt（1 项）**：T1.13 VideoPlay 单例状态改造（新，per-Activity 实例或状态快照）

### Phase 2：P1 增强改造（13 项，原 5 项 + 新增 8 项）

- **Exo2MediaPlayer.kt（5 项）**：T2.1 重复 Init 检测改造（重构：同一 URL+headers 才跳过）+ T2.2 prepareAsyncCallCount 日志 + T2.3 BUFFERING 超时 12 秒降级（修正）+ T2.4 嗅探协程生命周期日志 + T2.7 UnrecognizedInputFormatException 触发降级（新）
- **VideoUrlExtractor.kt（3 项）**：T2.5 各阶段耗时日志 + T2.9 第三层失败返回 null（新）+ T2.11 catch 守卫 CancellationException（新）
- **VideoPlay.kt（1 项）**：T2.10 兜底返回 null（新）
- **VideoPlayerActivity.kt（2 项）**：T2.8 onPause 取消 initSource 协程（新）+ T2.12 onStop 暂停视频（新）
- **ExoPlayerHelper.kt（1 项）**：T2.13 sniffVideoType 复用 sniffMimeType 缓存（新）
- **VideoFragment.kt（1 项）**：T1.8 改造点2 onDestroyView 调用 release()

### Phase 3：编译验证 + L1 验证（2 项，保持）

- 编译测试包（`io.legado.miss.app.debug`）
- L1 基础功能验证（无崩溃 + ExoPlayer 初始化正常）

### Phase 4：L2 真机测试（6 项，原 5 项 + 新增 8 实例快速切换测试）

- MacCMS 模板源（站点G/H 类型）
- DPlayer 播放器源（站点I 类型）
- 自定义播放页源（站点J 类型）
- MP4 直链源（站点D 类型，验证降级链走 Progressive）
- 加密 HLS 源（AES-128 类型）
- 8 实例快速切换测试（验证 VideoPlay 单例串扰修复，新增）

### Phase 5：文档同步 + 验收（3 项，保持）

- updateLog.md 更新（基于 git diff 真实代码变更）
- INDEX.md 同步
- AskUserQuestion 三选项验收

---

## §6 关联 Spec

| Spec | 关系 | 说明 |
|------|------|------|
| [exoplayer-resilience](../exoplayer-resilience/) | 前置 | 本次修复基于 exoplayer-resilience 已实施的 sniffVideoType + 降级链架构 |
| [player-review-and-optimization](../player-review-and-optimization/) | 关联 | 本次修复是 R4 增强计划的延续 |
| [image-gallery-activity](../image-gallery-activity/) | 暂缓 | 图片播放器优化待视频优化完成后再启动 |

---

## §7 分析报告溯源

### 7.1 V2 源码深度分析汇总报告

- **报告路径**：[docs/temp-analysis/video-playback-failure-source-analysis-20260726.md](../../temp-analysis/video-playback-failure-source-analysis-20260726.md)
- **分析对象**：`VideoUrlExtractor.kt` / `ExoPlayerHelper.kt` / `Exo2MediaPlayer.kt` / `VideoPlayerActivity.kt`
- **分析方式**：4 个并行子代理源码深度分析汇总
- **分析时间**：2026-07-26 18:30
- **核心产出**：10 个 Bug 根因验证 + 14 项修复方案验证 + 25 个新遗漏点清单（去重后）

### 7.2 V1 原分析报告

- **报告路径**：[docs/temp-analysis/video-playback-failure-analysis-20260726.md](../../temp-analysis/video-playback-failure-analysis-20260726.md)
- **日志来源**：`temp/logs/Downloadslogs(1).(3)..zip`（436KB，2026-07-26 17:23:32 下载）
- **解压路径**：`temp/logs/extracted_latest/logcat.txt`（5236KB）
- **分析时间**：2026-07-26 17:30

---

## §8 验收标准

### 8.1 功能验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 视频地址获取时间 | 真机测试 5 类源 | 平均 < 3 秒 |
| 嗅探成功率 | 真机测试 10 个案例 | ≥ 90% |
| 播放失败可追溯率 | AppLog 文件分析 | 100% |
| 降级链触发 | AppLog 文件分析 | ExoFallback 推进到 #2/3+ |
| 协程生命周期 | AppLog 文件分析 | 0 个幽灵日志 |
| 降级链正确率 | AppLog 文件分析 | MP4 直链走 Progressive |
| 状态变量重置 | AppLog 文件分析 | 切换视频时状态被重置 |
| VideoPlay 单例 | 真机测试 8 实例快速切换 | 状态不串扰 |

### 8.2 真机测试场景

| 场景 | 站点类型 | 预期结果 |
|------|---------|---------|
| MacCMS 模板源 | 站点G/H 类型 | 视频地址获取 < 3 秒，播放成功 |
| DPlayer 播放器源 | 站点I 类型 | 视频地址获取 < 3 秒，播放成功 |
| 自定义播放页源 | 站点J 类型 | 视频地址获取 < 3 秒，播放成功 |
| MP4 直链源 | 站点D 类型 | 视频地址获取 < 2 秒，降级链走 Progressive，播放成功 |
| 加密 HLS 源 | AES-128 类型 | 嗅探成功，播放成功 |
| 8 实例快速切换 | 任意类型 | 状态不串扰，每个实例独立播放 |

### 8.3 验收节点

1. **编译验证**：测试包（`io.legado.miss.app.debug`）编译通过
2. **L1 验证**：应用启动无崩溃，ExoPlayer 初始化正常
3. **L2 验证**：真机测试 5 类源 + 8 实例快速切换，收集 AppLog 验证所有改造点
4. **用户体感验证**：视频地址获取时间从 8.5 秒降至 3 秒以内

---

## §9 项目状态

| 阶段 | 状态 | 完成时间 |
|------|------|---------|
| V1 深度分析（logcat） | ✅ 完成 | 2026-07-26 17:30 |
| V1 Spec 设计 | ✅ 完成 | 2026-07-26 18:05 |
| V2 源码深度分析 | ✅ 完成 | 2026-07-26 18:30 |
| V2 spec.md 更新 | ✅ 完成 | 2026-07-26 18:40 |
| V2 README.md 更新 | ✅ 完成 | 2026-07-26 18:50 |
| V2 design.md 更新 | ⏳ 待实施 | — |
| V2 tasks.md 更新 | ⏳ 待实施 | — |
| V2 用户审查 | ⏳ 待审查 | — |
| Phase 1 P0 改造 | ⏳ 待实施 | — |
| Phase 2 P1 改造 | ⏳ 待实施 | — |
| Phase 3 编译+L1 | ⏳ 待实施 | — |
| Phase 4 L2 真机测试 | ⏳ 待实施 | — |
| Phase 5 文档同步+验收 | ⏳ 待实施 | — |

---

## §10 关键技术决策摘要（V2）

| 决策 | 选项 | V2决策结果 | 理由 |
|------|------|---------|------|
| SNIFF_TIMEOUT_MS | 3000/5000/8000ms | 5000ms | 实际嗅探 3362-3679ms，5000ms 提供缓冲 |
| 降级链触发 | 仅 onPlayerError / +BUFFERING 超时 | +BUFFERING 12 秒 | 5 秒太短导致弱网误降级 |
| 协程取消 | withTimeoutOrNull / +isActive / +Call.cancel | +isActive +Call.cancel +isReleased 标志位 | 三层保障资源释放（isReleased 解决非 suspend 函数无法响应 cancel） |
| currentSniffResult 共享 | 普通变量 / MutableStateFlow / 按嗅探结果排序 | 按嗅探结果排序降级链 | StateFlow 过度设计，核心问题是降级链默认 HLS 优先 |
| R5 delayTime | 1000/1500/2000ms | 1000ms | 足够 WebView 基础加载 |
| R5 timeout | 6000/8000/10000ms | 6000ms | 配合第一层 withTimeout(6000L) |
| 第一层超时 | 无 / 6 秒 / 10 秒 | 6 秒 | AnalyzeUrl 默认 60s 太长 |
| 总超时 | 无 / 12 秒 / 15 秒 | 12 秒 | 第一层(6s) + 第三层(6s) 累计 |
| 重复 Init 检测 | 1 秒防重 / 同一 URL+headers 才跳过 | 同一 URL+headers 才跳过 | 1 秒防重误伤合法场景（如用户快速切集） |
| T1.8 改造点2 位置 | VideoPlayerActivity.onDestroy / VideoFragment.onDestroyView | VideoFragment.onDestroyView | Activity 不直接持有 exo2MediaPlayer 引用 |
| VideoPlay 单例改造 | per-Activity 实例 / 状态快照 | 待 design.md 评估 | 需先搜索 VideoPlay 所有调用点 |

---

## §11 联系与反馈

- **用户反馈来源**：2026-07-26 17:49 用户指令
- **持久化位置**：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`
- **审查方式**：AskUserQuestion 三选项结构（通过 / 需调整 / 拒绝回退）
