# 视频播放器分段预缓冲机制深度分析与优化（video-prebuffer-enhancement）

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **状态**：🚧 P0 已实施完成（2026-07-28），P1/P2 待实施（R3 修订版——基于 R2 激进版审查反馈，移除低端机保护 + 用户可配置 + 放弃热切换 + 4 个新阻塞点修复）
> **创建日期**：2026-07-28
> **R2 修订日期**：2026-07-28
> **R3 修订日期**：2026-07-28
> **P0 实施完成日期**：2026-07-28
> **优先级**：P1（体验增强 + Bug 修复）
> **核心原则**：源码深度分析 + 业界成熟方案对标 + **激进缓冲策略（默认 HIGH 档位，用户可往下调）** + 最小改动优先修复 BUG，再分层引入优化 + **预加载器与播放器 cacheKey 统一 + 触发时机去重 + 内部播放列表管理**

---

## 一、功能概述

针对 Legado 视频播放器现有的"分段预缓冲加载机制"进行源码级深度分析，回答用户四个核心问题：

1. **当前机制能否在用户网络好时快速加载缓冲视频资源？**——已实现带宽档位感知（弱/中/好三档），但存在预加载未写入缓存的严重 BUG，实际无加速效果
2. **结合网上成熟方案还有哪些优化空间？**——Media3 `DefaultPreloadManager` 官方主推方案未引入；HLS 协议级优化（`setAllowChunklessPreparation`）未启用；运行时网络热切换缺失
3. **当前快速加载缓冲支持哪些视频格式？**——17 项 Magic Number + 16 种 URL 后缀 + Content-Type 三级交叉验证识别；HLS/DASH/SS/Progressive 四类 MediaSource 分发
4. **能否支持更多格式，尤其是 m3u8 和 mp4？**——m3u8 和 mp4 已支持；HLS 依赖在 build.gradle 中被注释但代码仍 import 使用（状态待确认）

### 1.1 R3 核心诉求（2026-07-28 R3 修订）

R2 激进版经用户审查后反馈需再次修订。R3 核心调整：**移除低端机保护**、**提供用户可配置参数**、**放弃 LoadControl 热切换**、**4 个新阻塞点修复**。

| 维度 | V1 保守版 | R2 激进版 | **R3 修订版** |
|------|----------|----------|--------------|
| **低端机保护** | 无 | 新增（内存<4GB/CPU<8核 降级） | **移除**（只检测 HIGH/MID 两档，默认按 HIGH，不再有 LOW） |
| **用户可配置参数** | 无 | 无 | **新增**：AppConfig/Preferences，用户可往下调 maxBuffer/预加载数量/预加载字节/缓存上限 |
| **LoadControl 热切换** | 不支持 | 新增（运行时动态提升） | **放弃**（路径 A：只在 prepare 前根据网络档位+设备档位设置，不运行时热切换） |
| **cacheKey 策略统一** | 无 | 无 | **新增**（阻塞点6：预加载器与播放器 cacheKey 必须一致） |
| **预加载触发时机+去重** | 50% 触发，无去重 | 50% 触发，无去重 | **新增**（阻塞点7：触发时机可配置默认 10% + URL 去重） |
| **内部播放列表管理** | 外部传入 | 外部传入 | **新增**（阻塞点8：VideoPreloader 内部维护播放列表，自动推断下一集） |
| **AppLog release 日志** | 无 | 无 | **新增**（阻塞点10：修改 AppLog 让 release 包输出 WARN/ERROR 级别） |
| **缓冲时长（好网）** | maxBuffer=50s | maxBuffer=90-120s | **maxBuffer=120s**（HIGH+GOOD，用户可下调） |
| **预加载数量（好网）** | 3 个 | 5-10 个 | **10 个**（HIGH+GOOD，用户可下调） |
| **预加载字节数** | 256KB/1MB | 5-10MB | **10MB**（HIGH+GOOD，用户可下调） |
| **磁盘缓存上限** | 50-500MB | 800MB-1GB | **1GB**（HIGH 默认，用户可下调） |

### 1.2 R3 核心策略矩阵（移除 LOW 档位，默认 HIGH）

> **核心变化**：DeviceTier 只检测 HIGH/MID 两档，不再有 LOW；默认按 HIGH 档位参数，用户可通过配置参数往下调。

| 设备档位 | 网络档位 | maxBuffer | 预加载数量 | 预加载字节 | 磁盘缓存上限 |
|----------|----------|-----------|-----------|-----------|-------------|
| **HIGH（默认）** | GOOD（好网） | 120s | 10 个 | 10MB | 1GB |
| HIGH（默认） | MEDIUM（中网） | 60s | 5 个 | 5MB | 1GB |
| HIGH（默认） | WEAK（弱网） | 20s | 1 个 | 1MB | 1GB |
| **MID（用户可降级）** | GOOD | 90s | 7 个 | 5MB | 800MB |
| MID（用户可降级） | MEDIUM | 40s | 3 个 | 2MB | 800MB |
| MID（用户可降级） | WEAK | 15s | 1 个 | 512KB | 800MB |

注：不再有 LOW 档位；默认按 HIGH 档位参数；用户可通过 AppConfig/Preferences 往下调 maxBuffer/预加载数量/预加载字节/缓存上限。

### 1.3 现状锚点

| 位置 | 文件 | 现状 |
|------|------|------|
| 首帧预加载 | [FirstFramePreloader.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt) | 已实现 1MB 预加载 + 64KB 预热 + LRU（10 个）+ 延迟 30s 清理 |
| 下一集预加载 | [VideoPreloader.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/VideoPreloader.kt) | 已实现 256KB 预加载 + WiFi 3 个/4G 1 个 LRU |
| 带宽感知 | [ExoPlayerHelper.kt#L88-L153](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L88-L153) | 已实现 DefaultBandwidthMeter + 三档 LoadControl（弱网 5s/15s、中网 10s/30s、好网 15s/50s） |
| 实例池 | [PlayerInstancePool.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt) | 已实现 3 实例 LRU + 共享 Allocator + 每实例独立 TrackSelector |
| 磁盘缓存 | [ExoPlayerHelper.kt#L816-L903](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L816-L903) | 已实现 SimpleCache + LRU + CacheDataSourceFactory（50-500MB 可配置） |
| 格式嗅探 | [MimeSniffer.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/MimeSniffer.kt) | 已实现 17 项 Magic Number + 主动 Probe（m3u8/mpd/moov） |
| 嗅探缓存 | [MimeSnifferCache.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/MimeSnifferCache.kt) | 已实现 URL→mimeType LRU（100 个，1 小时 TTL） |
| MediaSource 分发 | [ExoPlayerHelper.kt#L193-L218](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L193-L218) | 已实现按 contentType 分发 HLS/DASH/SS/Progressive |
| 播放器核心 | [Exo2MediaPlayer.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt) | 已实现降级链 + 5 次指数退避重试 + BUFFERING 超时降级 + WebView 兜底 |
| HLS 依赖 | [build.gradle#L278](file:///f:/myself/github/WeAgentChat/temp/legado/app/build.gradle#L278) | `//implementation(libs.media3.exoplayer.hls)` 被注释，但代码仍使用 HlsMediaSource |
| 设备能力检测 | 无 | **R3 调整**：DeviceInfoHelper 只检测 HIGH/MID 两档（不再有 LOW） |

### 1.4 关键发现（用户必读）

#### 发现-1：预加载机制存在严重 BUG（预加载实际无效）

`FirstFramePreloader.preloadUrl` 与 `VideoPreloader.preloadUrl` 均存在两个独立 BUG：

**BUG-A：`readBytes()` 未限制字节数，可能下载整个视频文件导致 OOM**

```kotlin
// FirstFramePreloader.kt L186
val bytes = body.byteStream().readBytes()  // 读取整个 body 到内存！
val preloadSize = minOf(bytes.size, PRELOAD_BYTES + 1)  // 仅计算 preloadSize，未用于截断
```

**BUG-B：预加载数据未写入 SimpleCache（预加载完全无效）**

注释声称"通过 CacheDataSink 写入 SimpleCache"，但实际代码只读取到内存后立即丢弃，**没有任何写入 SimpleCache 的调用**。下次播放时 CacheDataSource 不会命中，预加载完全无效。

#### 发现-2：HLS 依赖状态矛盾

`build.gradle` 第 278 行 `//implementation(libs.media3.exoplayer.hls)` 被注释，但 `ExoPlayerHelper.kt` 和 `Exo2MediaPlayer.kt` 都 `import androidx.media3.exoplayer.hls.HlsMediaSource` 并使用 `HlsMediaSource.Factory(...)`。

可能原因：
- GSYVideoPlayer 库传递依赖了 media3-exoplayer-hls（最可能）
- 项目当前编译失败（不太可能，因为项目可运行）
- 注释是后来加的，代码未同步更新

需在实施阶段确认 HLS 依赖实际状态。

#### 发现-3：用户问题"是否支持 m3u8 和 mp4"的回答

**结论：m3u8 和 mp4 已经支持**。用户可能不知道已支持，原因是预加载 BUG 导致体验不到加速效果，误以为不支持。

#### 发现-4：R3 深度分析发现的 7 个新阻塞点（2026-07-28 R3 修订）

R2 激进版审查后，深度分析发现 7 个新的技术阻塞点（阻塞点 4-10），R3 针对性修复 4 个、放弃 2 个、远期搁置 1 个：

**阻塞点 4：低端机保护策略冲突（R3 决策：移除）**
R2 新增的"内存<4GB/CPU<8核 降级到保守策略"在实际设备分布中覆盖率低，且低端机用户占比小，维护 LOW 档位增加复杂度。R3 移除 LOW 档位，DeviceTier 只检测 HIGH/MID 两档，默认按 HIGH 档位参数，用户可通过配置参数往下调。

**阻塞点 5：LoadControl 热切换限制（R3 决策：放弃，路径 A）**
ExoPlayer 限制 LoadControl 只能在 player 构建时设置，运行时热切换需重新 prepare，会导致短暂缓冲中断，体验反而下降。R3 放弃热切换，采用路径 A：只在 prepare 前根据当前网络档位 + 设备档位设置 LoadControl，运行时网络变化不热切换（下次 prepare 生效）。

**阻塞点 6：cacheKey 策略不统一（R3 决策：修复）**
预加载器（FirstFramePreloader/VideoPreloader）与播放器（Exo2MediaPlayer）使用的 cacheKey 不一致，导致预加载数据写入 SimpleCache 后，播放器读取时无法命中。R3 统一 cacheKey 生成策略：以规范化 URL（去除查询参数中无意义部分）为 cacheKey，预加载器与播放器共享同一 cacheKey 生成函数。

**阻塞点 7：预加载触发时机+去重缺失（R3 决策：修复）**
当前预加载触发时机为播放进度 50%，过于滞后；且同一 URL 可能被多次触发预加载（切集/手动触发/网络恢复），浪费带宽。R3 调整：触发时机可配置，默认 10%；新增 URL 去重（同一 URL 在预加载队列中只存在一份）。

**阻塞点 8：内部播放列表管理缺失（R3 决策：修复）**
当前 VideoPreloader 依赖外部传入下一集 URL，无法自动推断连续剧下一集。R3 让 VideoPreloader 内部维护播放列表（章节列表 + 当前播放位置），自动推断下一集 URL，无需外部每次调用时传入。

**阻塞点 9：Media3 DefaultPreloadManager 兼容性（R3 决策：远期搁置）**
Media3 `DefaultPreloadManager` 与现有 GSYVideoPlayer + IjkExo2MediaPlayer 的集成方式可能冲突，且需要较大改造。R3 暂不引入，保留 P2 远期方向。

**阻塞点 10：AppLog release 包日志缺失（R3 决策：修复）**
AppLog 在 release 包中默认不输出日志，导致生产环境无法通过日志排查预加载/缓冲问题。R3 修改 AppLog，让 release 包输出 WARN/ERROR 级别日志（INFO/DEBUG 仍不输出），便于生产问题定位。

---

## 二、核心能力

本 spec 聚焦多类优化，按优先级分层（R3 修订版）：

| 优先级 | 能力 | 解决问题 | 实施状态 |
|--------|------|---------|---------|
| **P0** | 修复预加载 BUG（数据未写入 SimpleCache + readBytes 无限制） | 预加载实际无效 → 修复后真正加速 | ✅ 已完成（2026-07-28） |
| **P0** | 确认 HLS 依赖实际状态 + 修复 build.gradle 与代码不一致 | 避免依赖被误删导致编译失败 | ✅ 已完成（2026-07-28） |
| **P0** | **cacheKey 策略统一**（阻塞点6） | 预加载器与播放器 cacheKey 一致，缓存命中率提升 | ✅ 已完成（2026-07-28） |
| **P0** | **AppLog release 包日志修复**（阻塞点10） | 生产环境可输出 WARN/ERROR 日志，便于排查 | ✅ 已完成（2026-07-28） |
| **P0（提前实施）** | **设备档位检测**（HIGH/MID 两档，默认 HIGH） | 为激进策略提供设备能力基础，移除低端机保护 | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |
| **P0（提前实施）** | **用户可配置参数**（AppConfig/Preferences） | 用户可往下调 maxBuffer/预加载数量/预加载字节/缓存上限 | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |
| **P0（提前实施）** | **ExoPlayerHelper cache 容量扩展 + createPreloadDataSource** | cache 容量从 50-500MB 扩展到 50-2048MB，支持 HIGH 档位 1GB 缓存 | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |
| **P1** | **激进 LoadControl**（好网 maxBuffer 120s，prepare 前设置，不热切换） | 最大化利用好网带宽，降低卡顿概率 | ⏳ 待实施 |
| **P1** | **激进预加载**（好网预加载 10 个 + 预加载字节数 10MB） | 确保切下一集时已缓存部分正片 | ⏳ 待实施 |
| **P1** | **预加载触发时机+去重**（阻塞点7：默认 10% 触发 + URL 去重） | 提前触发预加载 + 避免重复预加载浪费带宽 | ⏳ 待实施 |
| **P1** | **内部播放列表管理**（阻塞点8：VideoPreloader 自动推断下一集） | 自动预加载下一集，无需外部每次传入 URL | ⏳ 待实施 |
| **P1** | 启用 HLS 协议级优化（`setAllowChunklessPreparation`） | HLS 首屏耗时降低 30%+ | ⏳ 待实施 |
| **P1** | 网络切换运行时感知（NetworkCallback 动态调整预加载策略，**不热切换 LoadControl**） | 网络切换时预加载策略立即生效（LoadControl 下次 prepare 生效） | ⏳ 待实施 |
| **P1** | **全格式统一激进策略**（HLS/DASH/MP4/FLV/SS 统一激进缓冲） | 各类型视频都支持快速缓冲加载 | ⏳ 待实施 |
| **P2** | 引入 Media3 `DefaultPreloadManager`（官方主推，**远期搁置**） | 替换自研预加载器，获得官方维护红利 | ⏳ 待实施 |
| **P2** | 缓存命中率/失败率/首帧命中率埋点 | 为后续调优提供数据支撑 | ⏳ 待实施 |
| **P3** | AI 智能预缓冲（LSTM + TFLite，远期方向） | 首帧时间降 33%、卡顿降 50%（业界数据） | ⏳ 远期方向 |

---

## 三、文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives Considered + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / Architecture Decisions（ADR Y-Statement）/ Data Flow / File Changes |
| [tasks.md](./tasks.md) | `- [ ] X.Y` 格式任务清单 + AOAdapt 日志 |

---

## 四、预期收益（R3 修订版）

| 维度 | 当前 | V1 保守版 | R2 激进版 | **R3 修订版** |
|------|------|----------|----------|--------------|
| 预加载实际效果 | 完全无效（数据未写入缓存） | 真正写入 SimpleCache | 真正写入 SimpleCache + 5-10MB | 真正写入 SimpleCache + **10MB + cacheKey 统一命中** |
| 预加载内存安全 | OOM 风险（readBytes 无限制） | 严格限制读取字节数 | 严格限制 + 中高端机更多 | 严格限制 + **HIGH 默认档位** |
| **好网缓冲时长** | maxBuffer=50s | maxBuffer=50s | maxBuffer=90-120s | **maxBuffer=120s**（HIGH+GOOD，用户可下调） |
| **预加载数量（WiFi）** | 3 个 | 3 个 | 5-10 个 | **10 个**（HIGH+GOOD，用户可下调） |
| **预加载字节数** | 256KB/1MB | 256KB/1MB | 5-10MB | **10MB**（HIGH+GOOD，用户可下调） |
| **磁盘缓存上限** | 50-500MB | 50-500MB | 800MB-1GB | **1GB**（HIGH 默认，用户可下调） |
| **cacheKey 命中率** | 不一致（预加载无效） | 不一致 | 不一致 | **统一 cacheKey，命中率提升**（阻塞点6） |
| **预加载去重** | 无（可能重复预加载） | 无 | 无 | **URL 去重，避免浪费带宽**（阻塞点7） |
| **预加载触发时机** | 50% 触发 | 50% 触发 | 50% 触发 | **默认 10% 触发，可配置**（阻塞点7） |
| **播放列表管理** | 外部传入下一集 | 外部传入 | 外部传入 | **内部维护播放列表，自动推断下一集**（阻塞点8） |
| **用户可配置参数** | 无 | 无 | 无 | **AppConfig/Preferences 可往下调** |
| **release 包日志** | 无日志 | 无日志 | 无日志 | **WARN/ERROR 级别日志输出**（阻塞点10） |
| HLS 首屏耗时 | 未启用 chunkless preparation | 降低 30%+ | 降低 30%+ | 降低 30%+ |
| 网络切换响应 | 仅 prepare 前分档 | 运行时 NetworkCallback | 运行时 NetworkCallback + 热切换 | 运行时 NetworkCallback（**不热切换 LoadControl**，下次 prepare 生效） |
| 预加载可观测性 | 仅成功/失败日志 | 命中率/失败率/首帧命中率埋点 | 命中率/失败率/首帧命中率埋点 | 命中率/失败率/首帧命中率埋点 + **release 包 WARN/ERROR 日志** |
| 多格式支持 | HLS/DASH/SS/Progressive 已支持 | 维持，并启用 HLS 优化 | 全格式统一激进缓冲 | 全格式统一激进缓冲 |
| **设备档位** | 无 | 无 | HIGH/MID/LOW 三档 | **HIGH/MID 两档（默认 HIGH，移除 LOW）** |
| **低端机保护** | 无 | 无 | 内存<4GB/CPU<8核 降级 | **移除**（用户可通过配置参数往下调） |

---

## 五、R3 阻塞点汇总表

> R3 共识别 10 个阻塞点，7 个修复（YES）、2 个放弃（NO）、1 个远期搁置（NO）。

| # | 阻塞点 | 来源 | R3 决策 | 说明 |
|---|--------|------|---------|------|
| 1 | 预加载数据未写入 SimpleCache | V1 发现 | ✅ YES | P0 修复，预加载真正写入缓存 |
| 2 | readBytes 无限制导致 OOM | V1 发现 | ✅ YES | P0 修复，严格限制读取字节数 |
| 3 | HLS 依赖状态矛盾 | V1 发现 | ✅ YES | P0 修复，确认依赖实际状态 |
| 4 | 低端机保护策略冲突 | R2 新增 | ❌ NO | **移除 LOW 档位**，只检测 HIGH/MID，默认 HIGH，用户可下调 |
| 5 | LoadControl 热切换限制 | R2 新增 | ❌ NO | **放弃热切换**，路径 A：prepare 前设置，运行时不热切换 |
| 6 | cacheKey 策略不统一 | R3 新增 | ✅ YES | P0 修复，预加载器与播放器 cacheKey 统一 |
| 7 | 预加载触发时机+去重缺失 | R3 新增 | ✅ YES | P1 修复，默认 10% 触发 + URL 去重 |
| 8 | 内部播放列表管理缺失 | R3 新增 | ✅ YES | P1 修复，VideoPreloader 内部维护播放列表 |
| 9 | Media3 DefaultPreloadManager 兼容性 | R2 新增 | ❌ NO | **远期搁置**，P2 保留方向，R3 不实施 |
| 10 | AppLog release 包日志缺失 | R3 新增 | ✅ YES | P0 修复，release 包输出 WARN/ERROR 级别 |

---

## 六、风险与约束

- **不破坏现有降级链**：Exo2MediaPlayer 的 HLS→DASH→Progressive 降级链已稳定，本 spec 不改动
- **不引入大依赖**：P0/P1 优化均基于现有 Media3 1.10.1，不引入新依赖
- **不破坏实例池**：PlayerInstancePool 已修复 FATAL 崩溃，本 spec 不改动池化逻辑
- **用户可配置兜底**：默认 HIGH 档位参数，用户可通过 AppConfig/Preferences 往下调，避免激进策略在用户感知不佳时无法调整
- **网络能力兜底**：网络降档时立即降级预加载策略（LoadControl 下次 prepare 生效，不热切换）
- **cacheKey 一致性约束**：预加载器与播放器必须共享同一 cacheKey 生成函数，否则预加载无效
- **预加载去重约束**：同一 URL 在预加载队列中只存在一份，避免重复预加载
- **播放列表管理约束**：VideoPreloader 内部维护播放列表，需处理章节列表为空/单集/末尾的情况
- **LoadControl 不热切换约束**：运行时网络变化不热切换 LoadControl，下次 prepare 生效（接受网络变化后当前播放不立即调整 maxBuffer）
- **release 包日志约束**：AppLog 仅输出 WARN/ERROR 级别，INFO/DEBUG 仍不输出，避免日志过多
- **P2 DefaultPreloadManager 远期搁置**：与现有 GSYVideoPlayer + IjkExo2MediaPlayer 的集成方式可能冲突，R3 不实施
- **AI 预缓冲（P3）暂不实施**：复杂度过高，TFLite 模型训练与部署超出当前范围

---

## 七、非目标

- ❌ 不重写播放器架构（仍基于 GSYVideoPlayer + ExoPlayer）
- ❌ 不替换 ExoPlayer 为其他播放器（如 VLC/IjkPlayer）
- ❌ 不实现 DRM 内容解密
- ❌ 不实现 P3 AI 智能预缓冲（远期方向，本 spec 仅记录）
- ❌ 不修改 Exo2MediaPlayer 的降级链与重试逻辑（已稳定）
- ❌ 不实施 LoadControl 运行时热切换（R3 放弃，路径 A：prepare 前设置）
- ❌ 不实施低端机保护（R3 移除 LOW 档位，用户可通过配置参数往下调）
- ❌ 不在 R3 引入 Media3 DefaultPreloadManager（P2 远期搁置）

---

## 八、实施状态（P0 已完成，2026-07-28）

### 8.1 P0 实施范围说明

P0 实施范围在 R3 设计基础上扩展，除原 P0 项（预加载 BUG 修复 + HLS 依赖修复 + cacheKey 统一 + AppLog 修复）外，将原 P1 中的 **设备档位检测**、**用户可配置参数**、**ExoPlayerHelper cache 容量扩展** 三项提前到 P0 实施，为后续 P1 激进策略提供基础。

### 8.2 P0 已完成的 7 个文件变更

| # | 文件 | 变更类型 | 关键改动点 |
|---|------|---------|-----------|
| 1 | `DeviceInfoHelper.kt`（新增） | 新增 | 设备档位检测 HIGH/MID 两档（默认 HIGH）；HIGH 阈值：内存≥6GB + CPU≥8核 + 磁盘≥10GB；MID 阈值：内存≥4GB 或 CPU≥8核；检测失败降级到 HIGH（用户要求默认中高端机参数） |
| 2 | `AppLog.kt`（修改） | 修改 | release 包输出 WARN/INFO 日志；`putEntry`：ERROR/WARN/INFO 级别无条件 Log.e 输出（release 包也能采集关键日志）；`putDebugWithTag`：recordLog 关闭时 ERROR/WARN/INFO 仍输出到 logcat |
| 3 | `VideoPlay.kt`（修改） | 修改 | 新增 4 个用户可配置参数：`videoMaxBufferSec`（最大缓冲时长，0=自动，HIGH=120s/MID=90s）、`videoPreloadCount`（预加载数量，0=自动，HIGH=10/MID=7）、`videoPreloadBytesMB`（预加载字节数，0=自动，HIGH=10MB/MID=5MB）、`videoPreloadTriggerProgress`（预加载触发进度，默认10%）；用户可往下调 |
| 4 | `ExoPlayerHelper.kt`（修改） | 修改 | cache 容量范围从 50-500MB 调整为 50-2048MB（支持 HIGH 档位 1GB 缓存）；新增 `createPreloadDataSource` 方法（供预加载器复用 OkHttp 配置，确保请求行为一致） |
| 5 | `FirstFramePreloader.kt`（修改） | 修改 | `prewarmUrl`/`preloadUrl` 从 OkHttp Request + readBytes 改为 ExoPlayer DataSource + CacheDataSink；预加载数据现在真正写入 SimpleCache（原 bug：只读取后丢弃，播放时仍需重新下载）；`PRELOAD_BYTES` 从固定 1MB 改为 `getPreloadBytes()` 动态计算（HIGH=10MB/MID=5MB/用户可配）；`MAX_CACHE_SIZE` 从固定 10 改为 `getPreloadCount()` 动态计算；用 DataSpec 限制读取字节数防止 OOM；cacheKey 为纯 URL（与播放器 resolvingDataSource 解析后一致） |
| 6 | `VideoPreloader.kt`（修改） | 修改 | `preloadUrl` 从 OkHttp Request + readBytes 改为 ExoPlayer DataSource + CacheDataSink；预加载数据现在真正写入 SimpleCache；`PRELOAD_BYTES` 从固定 256KB 改为 `getPreloadBytes()` 动态计算；移除 WiFi/4G 网络感知区分（用户要求激进策略，用户可手动调低 videoPreloadCount 控制流量）；`MAX_CACHE_SIZE` 从 WiFi 3/4G 1 改为 `getPreloadCount()` 动态计算；移除 `isWifi()`/`isMobile()` 未使用方法 |
| 7 | `build.gradle`（修改） | 修改 | 取消注释 `media3.exoplayer.hls` 依赖，显式声明 HLS 支持 |

### 8.3 P0 验证状态

| 验证项 | 状态 | 说明 |
|--------|------|------|
| 编译通过 | ✅ | BUILD SUCCESSFUL in 4m 32s |
| APK 安装 | ✅ | 测试包 `io.legado.miss.app.debug`，版本 3.26.072816 |
| 真机测试 | 🔄 进行中 | 用户正在真机测试中，稍后提供调试日志 |
| 预加载写入 SimpleCache | ⏳ 待真机验证 | 代码层面已修复，待真机 logcat 验证 cache hit |
| readBytes 限制 | ⏳ 待真机验证 | 已用 DataSpec 限制，待真机内存监控验证 |
| cacheKey 命中率 | ⏳ 待真机验证 | cacheKey 统一为纯 URL，待真机验证命中率 |
| release 包日志 | ⏳ 待真机验证 | AppLog 已修改，待 release 包验证 WARN/ERROR 输出 |

### 8.4 P0 实施关键决策（详见 design.md AD-17）

1. **CacheDataSink 写入 SimpleCache**：预加载器改用 ExoPlayer DataSource + CacheDataSink，预加载数据真正写入磁盘缓存（原 bug：OkHttp readBytes 只读取到内存后丢弃）
2. **移除 WiFi/4G 网络感知区分**：用户要求激进策略，统一使用 `getPreloadCount()` 动态计算（HIGH=10/MID=7/用户可配），用户可手动调低 `videoPreloadCount` 控制流量
3. **cacheKey 统一为纯 URL**：与播放器 `resolvingDataSource` 解析后一致，避免 cacheKey 不匹配导致缓存未命中
4. **检测失败降级到 HIGH**：用户要求默认中高端机参数，检测失败时降级到 HIGH 档位（非 MID）
5. **createPreloadDataSource 复用 OkHttp 配置**：预加载器与播放器共享同一 OkHttp DataSource 配置，确保请求行为一致

### 8.5 P1 待实施项（5 项）

1. 激进 LoadControl（默认 HIGH 档位参数 120s maxBuffer，prepare 前设置，不热切换）
2. 全格式统一激进策略 + HLS 优化（setAllowChunklessPreparation）
3. 预加载触发时机调整（默认10%）+ URL 去重
4. 内部播放列表管理（PlayListManager）
5. 运行时网络感知（NetworkCallback，仅调整预加载策略，不热切换 LoadControl）

### 8.6 P2 待实施项（2 项）

1. 埋点（命中率/设备档位/网络档位/maxBuffer）
2. DefaultPreloadManager 评估
