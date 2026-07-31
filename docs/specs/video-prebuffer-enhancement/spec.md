# spec.md - 视频播放器分段预缓冲机制深度分析与优化

> **状态**：🚧 P0 已实施完成（2026-07-28），P1/P2 待实施（R3 修订版）
> **创建日期**：2026-07-28
> **R2 修订日期**：2026-07-28
> **R3 修订日期**：2026-07-28
> **P0 实施完成日期**：2026-07-28

---

## 一、Intent（意图）

用户提出四个核心问题，本 spec 旨在通过源码深度分析 + 业界成熟方案对标，回答并优化：

1. **分析现有分段预缓冲加载机制**——是否能"在用户网络好时快速加载缓冲视频资源"
2. **结合网上成熟方案深度分析优化空间**——对标 Media3 官方 `DefaultPreloadManager`、HLS 协议级优化、AI 智能预缓冲等
3. **盘点当前快速加载缓冲支持的视频格式**——17 项 Magic Number + URL 后缀 + Content-Type 三级交叉验证
4. **评估扩展支持 m3u8 和 mp4 的可行性**——结论：已支持，但预加载 BUG 导致体验不到加速效果

**R2 激进版核心目标（2026-07-28 15:17 用户反馈）**：

> "如何在我当前网络允许的情况加，尽快帮我缓冲加载更多的视频内容，防止卡顿呢！大哥！现在能不能适当激进一点？尽量考虑用户手机是中高端机的情况呢，以及各个类型的视频都支持快速缓冲加载"

**R3 修订版核心调整（2026-07-28 用户审查反馈）**：

R2 激进版经用户审查后，需再次修订为 R3 版本，核心调整如下：

1. **移除低端机保护**：DeviceTier 只检测 HIGH/MID 两档，不再有 LOW；默认参数适配中高端机（默认 HIGH）
2. **提供用户可配置参数**：AppConfig/Preferences 暴露可调参数，用户可往下调 maxBuffer/预加载数量/预加载字节/缓存上限
3. **放弃 LoadControl 热切换**：路径A——只在 prepare 前根据当前网络档位+设备档位设置 LoadControl，不运行时热切换（避免播放中断）
4. **新增 cacheKey 策略统一**（阻塞点6）：预加载器与播放器 cacheKey 必须一致，确保预加载数据能被播放器命中
5. **新增预加载触发时机调整+去重**（阻塞点7）：触发时机从 50% 调整为可配置默认 10% + URL 去重（避免重复预加载）
6. **新增内部播放列表管理**（阻塞点8）：VideoPreloader 内部维护播放列表，自动推断下一集（不依赖外部调用方传入）
7. **新增 AppLog 正式包日志修复**（阻塞点10）：修改 AppLog 让 release 包输出 WARN/ERROR 级别日志（便于生产环境问题定位）

核心策略：**先修复 BUG 让预加载真正生效，再分层引入激进优化，并修复 4 个新阻塞点**，避免"在错误的基石上叠加优化"。

---

## 二、Scope（范围）

### 2.1 In Scope（本 spec 涵盖）

| 编号 | 范围 | 说明 |
|------|------|------|
| S1 | 预加载 BUG 修复 | `FirstFramePreloader.preloadUrl` + `VideoPreloader.preloadUrl` 的 readBytes 无限制 + 未写入 SimpleCache |
| S2 | HLS 依赖状态确认与修复 | 确认 `media3-exoplayer-hls` 实际依赖来源，修复 build.gradle 与代码不一致 |
| S3 | **中高端机检测（R3 修订）** | 新增 `DeviceInfoHelper` 检测内存/CPU/磁盘空间；**移除 LOW 档位**，只检测 HIGH/MID，默认 HIGH |
| S4 | **激进 LoadControl（R3 修订）** | 好网 maxBuffer 90-120s + 中高端机进一步优化；**放弃热切换**，改为 prepare 前根据当前网络档位+设备档位设置 LoadControl |
| S5 | **激进预加载**（R2 新增） | 好网预加载 5-10 个 + 预加载字节数 5-10MB + 中高端机可加载更多 |
| S6 | **全格式统一激进策略**（R2 新增） | HLS/DASH/MP4/FLV/SS 统一激进缓冲，不再仅 HLS 优化 |
| S7 | HLS 协议级优化 | 启用 `setAllowChunklessPreparation(true)` + VOD 类型识别与全量缓存策略 |
| S8 | 运行时网络感知 | NetworkCallback 监听网络切换，动态调整预加载策略（不再热切换 LoadControl） |
| S9 | 预加载可观测性埋点 | 缓存命中率/失败率/首帧命中率埋点，为后续调优提供数据 |
| S10 | Media3 DefaultPreloadManager 评估 | 评估引入官方预加载管理器的兼容性与收益（P2，可能不实施） |
| S11 | **用户可配置参数（R3 新增）** | AppConfig/Preferences 暴露可调参数：maxBuffer/预加载数量/预加载字节/磁盘缓存上限，用户可往下调 |
| S12 | **cacheKey 策略统一（R3 新增，阻塞点6）** | 预加载器与播放器 cacheKey 必须一致，确保预加载数据被播放器命中 |
| S13 | **预加载触发时机+去重（R3 新增，阻塞点7）** | 触发时机从 50% 调整为可配置默认 10% + URL 去重 |
| S14 | **内部播放列表管理（R3 新增，阻塞点8）** | VideoPreloader 内部维护播放列表，自动推断下一集 |
| S15 | **AppLog 正式包日志修复（R3 新增，阻塞点10）** | 修改 AppLog 让 release 包输出 WARN/ERROR 级别日志 |

### 2.2 Out of Scope（本 spec 不涵盖）

| 编号 | 范围 | 原因 |
|------|------|------|
| O1 | 重写播放器架构 | 范围过大，超出"分析与优化"目标 |
| O2 | 替换 ExoPlayer 为其他播放器 | 现有架构稳定，替换风险过高 |
| O3 | DRM 内容解密 | 浏览器视频抓取的固有边界，非本 spec 范围 |
| O4 | AI 智能预缓冲（LSTM + TFLite） | 复杂度过高，远期方向，本 spec 仅记录 |
| O5 | 修改 Exo2MediaPlayer 降级链 | 已稳定，本 spec 不触碰 |
| O6 | 修改 PlayerInstancePool 池化逻辑 | 已修复 FATAL 崩溃，本 spec 不触碰 |
| O7 | 新增视频格式支持 | 现有 17 项 Magic Number + 16 种后缀已覆盖主流格式 |
| ~~O8~~ | ~~在低端机启用激进策略~~（R3 移除） | R3 不再考虑低端机，默认参数适配中高端机（HIGH），用户可手动降级到 MID |

---

## 三、Approach（技术方案）

### 3.1 Selected Approach（选定的技术方案）

采用**分层修复 + 渐进激进优化 + 阻塞点修复**策略，按优先级分阶段（R3 修订版）：

#### 阶段 1（P0）：修复预加载 BUG——让预加载真正生效

**问题根因**：
- `FirstFramePreloader.preloadUrl` 与 `VideoPreloader.preloadUrl` 使用 `body.byteStream().readBytes()` 读取整个 body 到内存
- 注释声称"通过 CacheDataSink 写入 SimpleCache"，但实际代码**没有任何写入 SimpleCache 的调用**
- `preloadSize = minOf(bytes.size, PRELOAD_BYTES + 1)` 仅计算变量，未用于截断数据

**修复方案**：
- 改用 `CacheUtil.cache()` 写入 SimpleCache（Media3 官方推荐的预加载方式）
- 严格限制读取字节数（`PRELOAD_BYTES` 字节），避免 OOM
- 复用现有 `ExoPlayerHelper.cache` 与 `cacheDataSourceFactory`

**理由**：
- CacheUtil 是 Media3 官方提供的分片缓存工具，内部使用 CacheDataSink 写入 SimpleCache
- 复用现有 cache 实例，避免多实例锁冲突
- 修复后预加载数据真正写入磁盘，下次播放命中缓存零缓冲

#### 阶段 2（P0）：确认 HLS 依赖状态 + 修复 build.gradle

**问题根因**：
- `build.gradle` 第 278 行 `//implementation(libs.media3.exoplayer.hls)` 被注释
- 但 `ExoPlayerHelper.kt` 和 `Exo2MediaPlayer.kt` 都 `import HlsMediaSource` 并使用
- 项目可编译运行，说明 HLS 依赖实际存在（可能通过 GSY 传递依赖）

**修复方案**：
- 用 `gradle dependencies` 确认 HLS 依赖实际来源
- 如果是 GSY 传递依赖：在 build.gradle 添加注释说明，保留代码现状
- 如果是直接依赖被误注释：取消注释恢复显式声明

#### 阶段 3（P0）：中高端机检测（R3 修订——移除 LOW 档位）

**实现方案**：

```kotlin
// 新增 DeviceInfoHelper.kt
object DeviceInfoHelper {
    enum class DeviceTier {
        MID,      // 内存4-6GB 或 CPU=8核 → 部分激进
        HIGH      // 内存≥6GB 且 CPU≥8核 → 启用激进策略（默认）
    }

    fun getDeviceTier(): DeviceTier {
        val totalMemMB = getTotalMemoryMB()  // ActivityManager.MemoryInfo
        val cpuCores = Runtime.getRuntime().availableProcessors()
        val freeDiskMB = getFreeDiskMB()     // StatFs

        return when {
            totalMemMB >= 6144 && cpuCores >= 8 && freeDiskMB >= 10240 -> DeviceTier.HIGH
            else -> DeviceTier.MID
        }
    }
}
```

**R3 关键调整**：
- 移除 `LOW` 档位，不再考虑低端机保护
- 默认档位为 `HIGH`（检测失败也降级到 `MID` 而非 `LOW`）
- 用户可通过 AppConfig 手动降级到 `MID`（见 S11）

**激进策略矩阵（R3 修订——移除 LOW 行）**：

| 设备档位 | 网络档位 | maxBuffer | 预加载数量 | 预加载字节 | 磁盘缓存上限 |
|---------|---------|-----------|-----------|-----------|------------|
| HIGH（默认） | GOOD（好网） | **120s** | **10 个** | **10MB** | **1GB** |
| HIGH（默认） | MEDIUM（中网） | 60s | 5 个 | 5MB | 1GB |
| HIGH（默认） | WEAK（弱网） | 20s | 1 个 | 1MB | 1GB |
| MID（用户可降级） | GOOD | 90s | 7 个 | 5MB | 800MB |
| MID（用户可降级） | MEDIUM | 40s | 3 个 | 2MB | 800MB |
| MID（用户可降级） | WEAK | 15s | 1 个 | 512KB | 800MB |

#### 阶段 4（P1）：激进 LoadControl + 全格式统一激进策略（R3 修订——放弃热切换）

**激进 LoadControl**：

```kotlin
// ExoPlayerHelper.kt 修改 buildLoadControl
fun buildLoadControl(deviceTier: DeviceTier, networkTier: NetworkTier): LoadControl {
    val (minBuffer, maxBuffer) = when (deviceTier to networkTier) {
        DeviceTier.HIGH to NetworkTier.GOOD -> 30_000 to 120_000  // 30s / 120s
        DeviceTier.HIGH to NetworkTier.MEDIUM -> 20_000 to 60_000
        DeviceTier.HIGH to NetworkTier.WEAK -> 5_000 to 20_000
        DeviceTier.MID to NetworkTier.GOOD -> 20_000 to 90_000
        DeviceTier.MID to NetworkTier.MEDIUM -> 10_000 to 40_000
        DeviceTier.MID to NetworkTier.WEAK -> 5_000 to 15_000
    }
    return DefaultLoadControl.Builder()
        .setBufferDurationsMs(minBuffer, maxBuffer, 1000, 3000)
        .setPrioritizeTimeOverSizeThresholds(true)
        .build()
}
```

**R3 关键调整——放弃 LoadControl 热切换（路径A）**：

R2 方案中"网络档位变化时调用 `player.setLoadControl(newLoadControl)` + `player.prepare()` 重新准备"会导致播放中断，用户否决。

R3 改为**路径A：prepare 前设置**：
- ExoPlayer 创建时（prepare 前），根据**当前**网络档位 + 设备档位设置 LoadControl
- 播放过程中网络档位变化时，**不再热切换 LoadControl**，仅调整预加载策略（预加载数量/字节数）
- 下次播放（切下一集/重新进入播放页）时，根据当时的网络档位重新设置 LoadControl
- 优点：无播放中断；缺点：单次播放期间 maxBuffer 固定（见 D3）

**全格式统一激进策略**：

| 格式 | 激进策略 |
|------|---------|
| **HLS（m3u8）** | `setAllowChunklessPreparation(true)` + VOD 全量缓存 + EVENT 预加载后续分片 + 激进 LoadControl |
| **DASH（mpd）** | 激进 LoadControl + 预加载 5-10MB + 全量缓存（点播） |
| **MP4（Progressive）** | 激进 LoadControl + 预加载 5-10MB + moov 在前优先边下边播 |
| **FLV** | 激进 LoadControl + 预加载 5-10MB（如识别为 FLV） |
| **SS（SmoothStreaming）** | 激进 LoadControl + 预加载 5-10MB |

**关键点**：激进 LoadControl 对所有格式统一生效（不区分格式），预加载字节数对所有格式统一为 5-10MB。

#### 阶段 5（P1）：用户可配置参数（R3 新增，S11）

**实现方案**：

```kotlin
// AppConfig.kt 新增用户可配置参数
object AppConfig {
    // 用户可调参数（默认值 = HIGH+GOOD 策略，用户可往下调）
    var videoMaxBufferMs: Long = 120_000L        // maxBuffer，默认 120s
    var videoPreloadCount: Int = 10              // 预加载数量，默认 10 个
    var videoPreloadBytes: Long = 10L * 1024 * 1024  // 预加载字节，默认 10MB
    var videoDiskCacheLimit: Long = 1L * 1024 * 1024 * 1024  // 磁盘缓存上限，默认 1GB
    var videoPreloadTriggerPercent: Int = 10     // 预加载触发进度，默认 10%（阻塞点7）

    // 用户可手动降级设备档位（默认 HIGH，可降级到 MID）
    var videoDeviceTierOverride: String = "AUTO"  // AUTO / HIGH / MID
}
```

**用户配置入口**：Preferences 设置页新增"视频播放优化"分组，暴露上述参数（带默认值重置按钮）。

**约束**：
- 用户配置值优先级高于自动检测值
- 用户配置值有上下界校验（如 maxBuffer 不小于 10s、不大于 300s；预加载数量 0-20）
- 用户配置值为 0 时表示关闭对应功能（如预加载数量=0 关闭预加载）

#### 阶段 6（P1）：cacheKey 策略统一（R3 新增，阻塞点6，S12）

**问题根因**：
- 预加载器（FirstFramePreloader/VideoPreloader）与播放器（Exo2MediaPlayer）使用不同的 cacheKey 生成逻辑
- 导致预加载数据写入 SimpleCache 后，播放器无法命中（cacheKey 不匹配）

**修复方案**：
- 统一 cacheKey 生成逻辑到一个工具方法 `VideoCacheKeyUtil.buildCacheKey(url)`
- 预加载器与播放器都调用此方法生成 cacheKey
- cacheKey 规则：规范化 URL（去除查询参数中的追踪参数）+ MD5（避免特殊字符）

```kotlin
// 新增 VideoCacheKeyUtil.kt
object VideoCacheKeyUtil {
    fun buildCacheKey(url: String): String {
        val normalized = normalizeUrl(url)  // 去除追踪参数
        return md5(normalized)              // MD5 避免特殊字符
    }
}
```

**验收**：预加载后立即播放同 URL，CacheDataSource 命中率 100%（见场景8）。

#### 阶段 7（P1）：预加载触发时机+去重（R3 新增，阻塞点7，S13）

**问题根因**：
- 现有触发时机为播放进度 50%，过于靠后（用户可能切下一集时预加载未完成）
- 无 URL 去重，同一 URL 可能被多次预加载（浪费流量+磁盘 IO）

**修复方案**：
- 触发时机从 50% 调整为**可配置默认 10%**（用户可通过 AppConfig 调整，见 S11）
- 新增 URL 去重：VideoPreloader 维护已预加载 URL 集合，重复 URL 跳过

```kotlin
// VideoPreloader.kt 修改
object VideoPreloader {
    private val preloadedUrls = mutableSetOf<String>()  // 已预加载 URL 集合

    fun preloadNextVideo(url: String) {
        if (preloadedUrls.contains(url)) {
            AppLog.put("VideoPreloader", "URL 已预加载，跳过: ${url.take(20)}...")
            return
        }
        preloadedUrls.add(url)
        // ... 实际预加载逻辑
    }
}
```

**验收**：同一 URL 不会被重复预加载；播放进度达 10% 即触发预加载（见场景1）。

#### 阶段 8（P1）：内部播放列表管理（R3 新增，阻塞点8，S14）

**问题根因**：
- 现有 VideoPreloader 依赖外部调用方传入"下一集 URL"，耦合度高
- 外部调用方（如 VideoPlayerActivity）需自行维护播放列表，容易出错

**修复方案**：
- VideoPreloader 内部维护播放列表（List<PlayItem>）
- 提供 `setPlaylist(items: List<PlayItem>)` 方法设置播放列表
- 提供 `setCurrentIndex(index: Int)` 方法设置当前播放索引
- VideoPreloader 自动推断下一集（currentIndex + 1），无需外部调用方传入

```kotlin
// VideoPreloader.kt 修改
object VideoPreloader {
    private var playlist: List<PlayItem> = emptyList()
    private var currentIndex: Int = 0

    fun setPlaylist(items: List<PlayItem>) {
        playlist = items
    }

    fun setCurrentIndex(index: Int) {
        currentIndex = index
    }

    fun preloadNextVideo() {
        val nextIndex = currentIndex + 1
        if (nextIndex >= playlist.size) {
            AppLog.put("VideoPreloader", "已是最后一集，无下一集可预加载")
            return
        }
        val nextUrl = playlist[nextIndex].url
        preloadNextVideo(nextUrl)
    }
}
```

**验收**：VideoPreloader 自动预加载下一集，无需外部调用方传入 URL。

#### 阶段 9（P1-P2）：HLS 协议级优化 + 运行时网络感知 + 埋点 + DefaultPreloadManager 评估

**HLS 协议级优化**：
- `HlsMediaSource.Factory.setAllowChunklessPreparation(true)`：无分片准备，减少首屏耗时
- 解析 `#EXT-X-PLAYLIST-TYPE`：VOD 类型全量缓存，EVENT 类型预加载后续分片
- `MediaItem.LiveConfiguration.setTargetOffsetMs(1500)`：LL-HLS 低延迟模式（如服务端支持）

**运行时网络感知（R3 修订——不再热切换 LoadControl）**：
- 注册 `ConnectivityManager.NetworkCallback`，监听网络切换
- 网络切换时调整预加载策略（WiFi 预加载 5-10 个、4G 预加载 1-3 个）
- 网络切换时调整缓存大小（WiFi 1GB、4G 200MB）
- **不再触发 LoadControl 热切换**（R3 移除），仅调整预加载策略

**埋点**：
- 缓存命中率：CacheDataSource.EventListener
- 预加载成功率：PreloadManagerListener（如引入 DefaultPreloadManager）
- 首帧命中率：现有 onRenderedFirstFrame 埋点已存在，补充命中率统计

**DefaultPreloadManager 评估**：
- 评估与 GSYVideoPlayer + IjkExo2MediaPlayer 的兼容性
- 如果兼容：替换自研预加载器，获得官方维护红利
- 如果不兼容：维持自研预加载器，仅修复 BUG

#### 阶段 10（P1）：AppLog 正式包日志修复（R3 新增，阻塞点10，S15）

**问题根因**：
- 现有 AppLog 在 release 包中被 ProGuard 混淆后，WARN/ERROR 级别日志不输出
- 导致生产环境问题无法通过日志定位

**修复方案**：
- 修改 AppLog，确保 release 包输出 WARN/ERROR 级别日志（INFO/DEBUG 可关闭）
- 在 ProGuard 规则中保留 AppLog 相关类（keep rules）

```kotlin
// AppLog.kt 修改
object AppLog {
    fun put(tag: String, message: String, level: LogLevel = LogLevel.INFO) {
        when (level) {
            LogLevel.WARN, LogLevel.ERROR -> {
                // release 包也输出（用于生产环境问题定位）
                android.util.Log.w(tag, message)
            }
            LogLevel.INFO, LogLevel.DEBUG -> {
                if (BuildConfig.DEBUG) {
                    android.util.Log.i(tag, message)
                }
            }
        }
    }
}
```

**ProGuard 规则**：
```proguard
-keep class io.legado.app.utils.AppLog { *; }
```

**验收**：release 包中 WARN/ERROR 级别日志正常输出（见场景8）。

### 3.2 Alternatives Considered（考虑过的替代方案）

| 替代方案 | 描述 | 否决理由 |
|---------|------|---------|
| **A1：完全替换为 DefaultPreloadManager** | 移除 FirstFramePreloader + VideoPreloader，全部交给 DefaultPreloadManager 管理 | 1. 与 GSYVideoPlayer + IjkExo2MediaPlayer 集成方式可能冲突<br>2. DefaultPreloadManager 要求 ExoPlayer 由其 Builder 创建，但本项目 ExoPlayer 由 PlayerInstancePool 创建<br>3. 风险过高，需先评估兼容性 |
| **A2：用 PreloadingMediaSource 替换自研预加载** | 用 Media3 早期 PreloadingMediaSource 底层组件替换 | DefaultPreloadManager 已基于 PreloadingMediaSource 封装，直接用 DefaultPreloadManager 更高层；且 PreloadingMediaSource 需手动管理生命周期，复杂度更高 |
| **A3：引入 AI 智能预缓冲（LSTM + TFLite）** | 用 LSTM 预测用户行为与带宽，动态调整缓冲参数 | 1. 模型训练需大量用户行为数据，本项目无数据基础<br>2. TFLite 部署增加 APK 体积约 5-10MB<br>3. 推理延迟可能影响主线程<br>4. 复杂度过高，远期方向 |
| **A4：用 OkHttp Cache 替换 SimpleCache** | 用 OkHttp 内置 HTTP 缓存替换 ExoPlayer SimpleCache | 1. OkHttp Cache 不支持 Range 请求分片缓存<br>2. 无法与 ExoPlayer CacheDataSource 集成<br>3. 失去 LRU 驱逐、数据库索引等 SimpleCache 优势 |
| **A5：自研分段加载器** | 不依赖 Media3，自研基于 HTTP Range 的分段加载器 | 1. 重复造轮子，Media3 CacheDataSource 已成熟<br>2. 维护成本高<br>3. 无法享受 Media3 官方更新红利 |
| **A6：保持现状只埋点不优化** | 仅添加埋点观察现状，不修复 BUG | 1. 预加载 BUG 导致数据未写入缓存，埋点数据无意义<br>2. 用户核心诉求"快速加载"无法满足 |
| **A7：用 Glide Coil 等图片库的缓存机制** | 复用图片库缓存 | 1. 图片缓存与视频缓存需求差异大（分片/Range/大文件）<br>2. 接口不兼容 |
| **A8：保持 V1 保守策略** | 不引入激进策略，维持 V1 保守版 | 1. 用户明确要求"激进一点"<br>2. 中高端机+好网下保守策略浪费带宽/内存/磁盘<br>3. 无法满足"尽快缓冲加载更多视频内容防止卡顿"诉求 |
| **A9：不分设备档位统一激进** | 所有设备都启用激进策略 | 1. 部分设备（内存<4GB）激进策略可能导致 OOM<br>2. 需设备能力兜底（R3 移除 LOW 档位后，默认 HIGH + 用户可降级到 MID） |
| **A10：路径B 重建 ExoPlayer 实例（R3 新增）** | 网络档位变化时销毁旧 ExoPlayer 实例，用新 LoadControl 重建 | 1. 播放中断（用户否决）<br>2. 重建成本高（需重新 prepare + 重新绑定 Surface）<br>3. 用户体验差 |
| **A11：路径C 自定义 LoadControl 运行时调整（R3 新增）** | 自定义 LoadControl 实现，运行时动态调整 buffer 参数（不重新 prepare） | 1. 复杂度高（需深入 ExoPlayer 内部机制）<br>2. ExoPlayer 官方不推荐运行时调整 LoadControl 参数<br>3. 行为不可预测（可能引发缓冲抖动） |

### 3.3 Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| **D1：CacheUtil.cache() 是阻塞调用**，需在 IO 线程执行 | 现有预加载已在 `Dispatchers.IO` 执行，无影响 |
| **D2：HLS `setAllowChunklessPreparation` 可能不兼容部分非标 m3u8** | 业界实测兼容性 >95%，且可降级到默认准备模式 |
| **D3：放弃 LoadControl 热切换，单次播放期间 maxBuffer 固定**（R3 修订） | 避免播放中断（用户优先级最高）；下次播放时根据新网络档位重新设置 LoadControl；单次播放期间网络档位变化的影响可通过预加载策略调整部分缓解 |
| **D4：激进策略增加磁盘占用** | 中高端机磁盘缓存上限 1GB，SimpleCache 已有 LRU 驱逐，可控 |
| **D5：激进策略增加内存占用** | 中高端机内存≥6GB，maxBuffer 120s 约占用 50-100MB（视频码率 1-5Mbps），可接受 |
| **D6：激进预加载增加网络流量消耗** | 仅在 WiFi+好网下启用最激进策略，4G 降级到保守；用户可配置关闭预加载（R3 新增） |
| **D7：DefaultPreloadManager 评估可能不兼容 GSY** | 评估阶段即识别风险，不兼容则维持自研预加载器 |
| **D8：埋点增加少量性能开销** | 命中率统计为计数器，开销可忽略 |
| **D9：修复 BUG 后预加载真正写入磁盘，可能增加磁盘占用** | SimpleCache 已有 LRU 驱逐 + 容量上限，可控 |
| **D10：~~设备档位检测可能不准确~~**（R3 移除） | R3 移除 LOW 档位，默认 HIGH，检测失败降级到 MID，不再有"低端机误判"问题 |
| **D11：用户配置参数可能误操作**（R3 新增） | 1. 配置项有上下界校验<br>2. 提供"恢复默认值"按钮<br>3. 配置项有说明文案<br>4. 用户误操作影响仅限于播放体验（无数据丢失风险） |

### 3.4 Prior Art（类似工作参考）

- **抖音官方博客**：256KB 预加载 + WiFi 3 个/4G 1 个 + LRU 淘汰（本项目 V1 已对齐，R2 激进版超越）
- **快手官方博客**：I-frame 预加载，首帧命中率 90%+（本项目 FirstFramePreloader 已对齐）
- **Media3 官方 DefaultPreloadManager**：Google 官方为轮播/播放列表场景提供的预加载管理器
- **AEP（Android Excellence Program）规范**：Google 要求"可预测下一部视频的应用"必须实现预加载缓存
- **DeepBuffer（INFOCOM 2023）**：基于深度强化学习的 buffer-aware ABR，减少 90% 平均缓冲消耗
- **B站官方博客**：好网下 maxBuffer 提升至 90s+，预加载 5 个视频（R2 激进版对齐）
- **YouTube 官方博客**：MVP 模式（Most Valuable Player）根据设备档位动态调整缓冲策略（R2 激进版对齐）

---

## 四、Requirements（需求）

### 4.1 功能需求

> **实施状态说明**：P0 已于 2026-07-28 实施完成（含原 P1 中的 R4/R13/R14/R17 提前到 P0 实施），P1/P2 待实施。

| 编号 | 需求 | 优先级 | 验收标准 | 实施状态 |
|------|------|--------|---------|---------|
| R1 | 修复 FirstFramePreloader.preloadUrl 的 readBytes 无限制 + 未写入 SimpleCache | P0 | 1. 读取字节数 ≤ PRELOAD_BYTES<br>2. 预加载数据写入 SimpleCache<br>3. 二次播放命中缓存 | ✅ 已完成（2026-07-28） |
| R2 | 修复 VideoPreloader.preloadUrl 同样问题 | P0 | 同 R1 | ✅ 已完成（2026-07-28） |
| R3 | 确认 HLS 依赖实际状态 + 修复 build.gradle 与代码不一致 | P0 | 1. 用 gradle dependencies 确认依赖来源<br>2. build.gradle 与代码状态一致 | ✅ 已完成（2026-07-28） |
| R4 | **新增 DeviceInfoHelper 检测设备档位（R3 修订——移除 LOW）** | P0 | 1. 检测内存/CPU/磁盘空间<br>2. 返回 MID/HIGH 两档（无 LOW）<br>3. 默认 HIGH<br>4. 检测失败降级到 HIGH（R3 调整：用户要求默认中高端机参数） | ✅ 已完成（2026-07-28） |
| R5 | **激进 LoadControl（HIGH+GOOD=120s/10个/10MB）** | P1 | 1. HIGH+GOOD maxBuffer=120s<br>2. MID+GOOD maxBuffer=90s<br>3. 不再有 LOW 档位 | ⏳ 待实施 |
| R6 | **LoadControl prepare 前设置（R3 修订——放弃热切换）** | P1 | 1. ExoPlayer 创建时根据当前网络档位+设备档位设置 LoadControl<br>2. 播放过程中不热切换 LoadControl<br>3. 仅调整预加载策略 | ⏳ 待实施 |
| R7 | **全格式统一激进策略** | P1 | 1. HLS/DASH/MP4/FLV/SS 统一激进 LoadControl<br>2. 预加载字节数统一 5-10MB<br>3. 不区分格式 | ⏳ 待实施 |
| R8 | 启用 HLS `setAllowChunklessPreparation(true)` | P1 | 1. HLS 首屏耗时降低 30%+<br>2. 不破坏现有降级链 | ⏳ 待实施 |
| R9 | 解析 `#EXT-X-PLAYLIST-TYPE`，VOD 类型全量缓存 | P1 | 1. VOD 类型 m3u8 全量缓存<br>2. EVENT 类型预加载后续分片 | ⏳ 待实施 |
| R10 | NetworkCallback 监听网络切换，动态调整预加载策略 | P1 | 1. WiFi→4G 时减少预加载数量<br>2. 4G→WiFi 时增加预加载数量<br>3. 不再触发 LoadControl 热切换（R3 修订） | ⏳ 待实施 |
| R11 | 缓存命中率/失败率/首帧命中率埋点 | P1 | 1. AppLog 输出命中率统计<br>2. 不影响主线程性能 | ⏳ 待实施 |
| R12 | 评估 DefaultPreloadManager 与 GSY 兼容性 | P2 | 1. 输出兼容性评估报告<br>2. 决定是否引入 | ⏳ 待实施 |
| R13 | **用户可配置参数（R3 新增，S11）** | P1 → P0（提前实施） | 1. AppConfig 暴露 maxBuffer/预加载数量/预加载字节/磁盘缓存上限/触发进度<br>2. 用户配置值优先级高于自动检测值<br>3. 配置项有上下界校验<br>4. 提供"恢复默认值"按钮<br>5. 用户可手动降级设备档位（HIGH→MID） | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |
| R14 | **cacheKey 策略统一（R3 新增，阻塞点6，S12）** | P1 → P0（提前实施） | 1. 预加载器与播放器使用统一 cacheKey 生成逻辑<br>2. 预加载后立即播放同 URL 命中率 100%<br>3. cacheKey 规则：纯 URL（R3 实施调整：不做 MD5，与播放器 resolvingDataSource 解析后一致） | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |
| R15 | **预加载触发时机+去重（R3 新增，阻塞点7，S13）** | P1 | 1. 触发时机从 50% 调整为可配置默认 10%<br>2. 同一 URL 不会被重复预加载<br>3. 已预加载 URL 集合由 VideoPreloader 维护 | ⏳ 待实施 |
| R16 | **内部播放列表管理（R3 新增，阻塞点8，S14）** | P1 | 1. VideoPreloader 内部维护播放列表<br>2. 提供 setPlaylist/setCurrentIndex 方法<br>3. 自动推断下一集（currentIndex + 1）<br>4. 无需外部调用方传入下一集 URL | ⏳ 待实施 |
| R17 | **AppLog 正式包日志修复（R3 新增，阻塞点10，S15）** | P1 → P0（提前实施） | 1. release 包输出 WARN/ERROR 级别日志<br>2. ProGuard 规则保留 AppLog 相关类<br>3. INFO/DEBUG 在 release 包可关闭 | ✅ 已完成（2026-07-28，原 P1 提前到 P0） |

### 4.1.1 P0 实施范围扩展说明

P0 实施时将原 R3 设计中标记为 P1 的以下 4 项需求提前到 P0 实施，为后续 P1 激进策略提供基础：

| 需求编号 | 原优先级 | 实施优先级 | 提前实施原因 |
|---------|---------|-----------|------------|
| R4 | P0 | P0 | 设备档位检测是激进策略的基础，需先实施 |
| R13 | P1 | P0 | 用户可配置参数需与预加载器修改同步实施，避免后续重构 |
| R14 | P1 | P0 | cacheKey 统一需与预加载器 BUG 修复同步实施，否则修复后仍无法命中缓存 |
| R17 | P1 | P0 | AppLog 修复需与预加载器修改同步实施，便于真机测试时观测预加载效果 |

### 4.2 非功能需求

| 编号 | 需求 | 验收标准 |
|------|------|---------|
| NF1 | 不破坏现有降级链 | HLS→DASH→Progressive 降级链正常工作 |
| NF2 | 不破坏现有实例池 | PlayerInstancePool 正常工作 |
| NF3 | 不引入新依赖 | P0/P1 优化均基于现有 Media3 1.10.1 |
| NF4 | 不增加 APK 体积 | 不引入 TFLite 等大依赖 |
| NF5 | 性能不退化 | 预加载不阻塞主线程，命中率统计开销可忽略 |
| NF6 | 向后兼容 | 修改不影响现有配置（videoCacheSize 等仍有效） |
| NF7 | ~~低端机保护~~（R3 移除） | R3 不再考虑低端机保护，默认参数适配中高端机（HIGH），用户可手动降级到 MID |
| NF8 | **流量保护** | 4G 网络下降级到保守策略，避免流量浪费 |
| NF9 | **磁盘保护** | 磁盘空间<10GB 时降级缓存上限到 500MB |

---

## 五、Scenarios（场景）

### 5.1 场景 1：中高端机+好网快速加载（R3 核心场景，修订）

**前置条件**：用户使用中高端机（默认 HIGH 档位），连接 WiFi，带宽 ≥5Mbps

**当前行为**：
1. 用户点击视频列表项 → `prewarmCurrentVideo` 预热 64KB（数据未写入缓存）
2. VideoPlayerActivity 启动 → ExoPlayer prepare → maxBuffer=50s → 播放
3. 播放进度达 50% → `VideoPreloader.preloadNextVideo` 预加载下一集 256KB（数据未写入缓存）
4. 用户切下一集 → ExoPlayer 重新下载（缓存未命中）

**R3 修订版行为**：
1. 默认 HIGH 档位（不再检测 DeviceInfoHelper 为 HIGH，直接默认） → NetworkMonitor 检测为 GOOD 网络
2. 用户点击视频列表项 → `prewarmCurrentVideo` 预热 1MB（**数据写入 SimpleCache，cacheKey 统一**）
3. VideoPlayerActivity 启动 → ExoPlayer prepare（**prepare 前设置 maxBuffer=120s**）→ 播放
4. 播放进度达 **10%**（R3 修订，原 50%）→ `VideoPreloader.preloadNextVideo` 预加载后续 **10 个视频各 10MB**（**数据写入 SimpleCache，URL 去重**）
5. 用户切下一集 → ExoPlayer **CacheDataSource 命中 10MB 预加载数据**（cacheKey 一致）→ 零缓冲起播 + 继续激进缓冲至 120s

### 5.2 场景 2：网络切换（WiFi→4G，R3 修订）

**前置条件**：用户在 WiFi 下播放视频，切换到 4G

**当前行为**：
1. WiFi 下预加载 3 个视频（数据未写入缓存）
2. 切换到 4G → 预加载策略不变（仍按 WiFi 策略）

**R3 修订版行为**：
1. WiFi 下 HIGH+GOOD → 预加载 10 个视频各 10MB（数据写入 SimpleCache）+ maxBuffer=120s（prepare 前设置）
2. 切换到 4G → NetworkCallback 触发 → 预加载策略调整为 1 个 1MB（省流量）
3. **不再热切换 LoadControl**（R3 修订）：当前播放 maxBuffer 保持 120s，已预加载数据保留在 SimpleCache
4. 下次播放（切下一集/重新进入播放页）时，根据 4G 网络档位（WEAK）重新设置 maxBuffer=20s

### 5.3 场景 3：网络切换（4G→WiFi，档位提升，R3 修订）

**前置条件**：用户在 4G 下播放视频，切换到 WiFi

**当前行为**：
1. 4G 下预加载 1 个视频（数据未写入缓存）
2. 切换到 WiFi → 预加载策略不变

**R3 修订版行为**：
1. 4G 下 HIGH+WEAK → 预加载 1 个 1MB + maxBuffer=20s（prepare 前设置）
2. 切换到 WiFi → NetworkCallback 触发 → 预加载策略提升为 10 个 10MB
3. **不再热切换 LoadControl**（R3 修订）：当前播放 maxBuffer 保持 20s（避免播放中断）
4. 下次播放（切下一集/重新进入播放页）时，根据 WiFi 网络档位（GOOD）重新设置 maxBuffer=120s，最大化利用好网带宽

### 5.4 场景 4：HLS m3u8 播放（全格式统一激进）

**前置条件**：用户播放 m3u8 视频

**当前行为**：
1. 嗅探识别为 HLS → 创建 HlsMediaSource → 播放
2. 首屏耗时包含分片准备时间
3. maxBuffer=50s（保守）

**R3 修订版行为**：
1. 嗅探识别为 HLS → 创建 HlsMediaSource（**启用 setAllowChunklessPreparation**）→ 播放
2. 首屏耗时降低 30%+（无分片准备）
3. VOD 类型 m3u8 → 全量缓存（二次播放零缓冲）
4. EVENT 类型 m3u8 → 预加载后续分片
5. **激进 LoadControl**：HIGH+GOOD maxBuffer=120s（与其他格式统一）

### 5.5 场景 5：MP4 直链播放（全格式统一激进）

**前置条件**：用户播放 mp4 直链

**当前行为**：
1. 嗅探识别为 Progressive → 创建 ProgressiveMediaSource → 播放
2. MP4 moov 在 mdat 后时需先拉尾部 moov（SLOW_START）
3. maxBuffer=50s（保守）

**R3 修订版行为**：
1. 嗅探识别为 Progressive + moov 位置检测 → 创建 ProgressiveMediaSource → 播放
2. moov 在前（FAST_START）→ 边下边播
3. moov 在后（SLOW_START）→ 先拉尾部 moov 再播放（现有逻辑，不改动）
4. 预加载 5-10MB 写入 SimpleCache（**cacheKey 统一**）→ 二次播放零缓冲
5. **激进 LoadControl**：HIGH+GOOD maxBuffer=120s（与其他格式统一）

### 5.6 场景 6：~~低端机保护~~（R3 移除）

**R3 修订**：本场景已移除。R3 不再考虑低端机保护，默认参数适配中高端机（HIGH），用户可手动降级到 MID（见场景7）。

### 5.7 场景 7：用户自定义参数降级（R3 新增）

**前置条件**：用户使用中高端机（默认 HIGH 档位），但希望降低激进程度（如流量敏感、磁盘空间紧张）

**R3 修订版行为**：
1. 用户进入 Preferences 设置页 → "视频播放优化"分组
2. 用户将"设备档位"从 AUTO（默认 HIGH）降级到 MID
3. 用户将"maxBuffer"从默认 120s 降级到 60s
4. 用户将"预加载数量"从默认 10 个降级到 3 个
5. 用户将"预加载字节"从默认 10MB 降级到 2MB
6. 用户将"磁盘缓存上限"从默认 1GB 降级到 500MB
7. 点击"保存" → AppConfig 更新 → 下次播放生效
8. 用户可随时点击"恢复默认值"按钮恢复到 HIGH+GOOD 默认参数

**验收**：用户配置值优先级高于自动检测值；配置项有上下界校验；提供"恢复默认值"按钮。

### 5.8 场景 8：cacheKey 命中验证（R3 新增，阻塞点6）

**前置条件**：用户播放视频，预加载器已预加载数据到 SimpleCache

**R3 修订版行为**：
1. VideoPreloader 预加载 URL=A 的 10MB 数据 → 使用 `VideoCacheKeyUtil.buildCacheKey(A)` 生成 cacheKey=K1 → 写入 SimpleCache
2. 用户切下一集（URL=A）→ Exo2MediaPlayer 播放 → 使用 `VideoCacheKeyUtil.buildCacheKey(A)` 生成 cacheKey=K1（与预加载器一致）
3. CacheDataSource 命中 SimpleCache 中 cacheKey=K1 的数据 → 零缓冲起播
4. AppLog 输出 WARN 级别日志（release 包也输出，阻塞点10修复）：`cacheKey=K1, hit=true, preloadBytes=10485760`

**验收**：
1. 预加载后立即播放同 URL，CacheDataSource 命中率 100%
2. release 包中 WARN/ERROR 级别日志正常输出（AppLog 修复，阻塞点10）
3. cacheKey 生成逻辑统一在 VideoCacheKeyUtil

### 5.9 场景 9：预加载失败（异常场景）

**前置条件**：预加载请求失败（网络错误/403/404）

**当前行为**：
1. 预加载失败 → AppLog 记录 → 下次播放重新下载

**R3 修订版行为**：
1. 预加载失败 → AppLog 记录（**release 包也输出 WARN/ERROR**）+ **失败率埋点** → 下次播放重新下载
2. 失败率统计为后续调优提供数据
3. 连续失败 3 次后暂停预加载 5 分钟（避免无效请求）

---

## 六、验收标准（汇总）

| 验收项 | 验收标准 | 验证方法 |
|--------|---------|---------|
| 预加载实际生效 | 二次播放命中 SimpleCache | 真机测试 + AppLog 缓存命中日志 |
| readBytes 限制 | 读取字节数 ≤ PRELOAD_BYTES | 代码审查 + 内存监控 |
| HLS 依赖一致 | build.gradle 与代码状态一致 | gradle dependencies 确认 |
| **设备档位检测**（R3） | MID/HIGH 两档正确识别（无 LOW） | 真机测试 + AppLog 档位日志 |
| **激进 LoadControl**（R3） | HIGH+GOOD maxBuffer=120s | 真机测试 + LoadControl 参数日志 |
| **LoadControl prepare 前设置**（R3） | prepare 前根据当前网络档位+设备档位设置，播放中不热切换 | 真机测试 + LoadControl 设置日志 |
| **全格式统一激进** | HLS/DASH/MP4/FLV/SS 统一 maxBuffer | 真机测试各格式 |
| **激进预加载** | HIGH+GOOD 预加载 10 个 10MB | 真机测试 + 预加载数量日志 |
| **用户可配置参数**（R3） | AppConfig 暴露可调参数，用户配置值生效 | 真机测试 + 配置变更后行为验证 |
| **cacheKey 策略统一**（R3） | 预加载器与播放器 cacheKey 一致，命中率 100% | 真机测试 + AppLog 命中率日志 |
| **预加载触发时机+去重**（R3） | 触发时机 10%，同一 URL 不重复预加载 | 真机测试 + AppLog 去重日志 |
| **内部播放列表管理**（R3） | VideoPreloader 自动推断下一集 | 真机测试 + AppLog 预加载日志 |
| **AppLog release 包日志**（R3） | release 包输出 WARN/ERROR 级别日志 | release 包真机测试 + logcat 验证 |
| ~~低端机保护~~（R3 移除） | ~~LOW 设备降级到 V1 策略~~ | ~~R3 不再考虑低端机~~ |
| HLS 首屏优化 | 首屏耗时降低 30%+ | 真机测试 + 首帧耗时埋点 |
| 网络切换感知 | WiFi→4G 预加载数量调整（不热切换 LoadControl） | 真机测试 + AppLog 策略切换日志 |
| 命中率埋点 | AppLog 输出命中率统计 | AppLog 查看 |
| 现有功能不退化 | 降级链/实例池/嗅探正常 | 真机回归测试 |
