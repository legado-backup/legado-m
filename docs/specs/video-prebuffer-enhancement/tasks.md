# tasks.md - 视频播放器分段预缓冲机制深度分析与优化

> **状态**：🚧 P0 已实施完成（2026-07-28），P1/P2 待实施（R3 修订版）
> **创建日期**：2026-07-28
> **R2 修订日期**：2026-07-28
> **R3 修订日期**：2026-07-28
> **P0 实施完成日期**：2026-07-28
> **格式**：`- [ ] X.Y` 任务清单 + AOAdapt 日志
> **R3 核心调整**：移除低端机保护（只检测 HIGH/MID，默认 HIGH）+ 用户可配置参数 + 放弃 LoadControl 热切换 + cacheKey 统一 + 预加载触发时机去重 + 内部播放列表管理 + AppLog 正式包日志修复
> **P0 实施说明**：P0 实施范围扩展，含原 P1 中的 R4（DeviceInfoHelper）/R13（用户可配置参数）/R14（cacheKey 统一）/R17（AppLog 修复）提前到 P0 实施，共完成 7 个文件变更。验证类任务（真机测试）待用户提供调试日志后闭环。

---

## 1. 准备工作

- [x] 1.1 确认需求范围（已完成：用户四个核心问题 + R2 激进版三个核心诉求 + R3 七项核心调整已明确）
- [x] 1.2 阅读相关源码（已完成：ExoPlayerHelper/VideoPreloader/FirstFramePreloader/PlayerInstancePool/MimeSniffer/Exo2MediaPlayer/AppConfig/AppLog）
- [x] 1.3 调研网上成熟方案（已完成：Media3 DefaultPreloadManager + HLS 优化 + AI 预缓冲 + B站/YouTube 激进策略）
- [x] 1.4 确认 HLS 依赖实际状态（gradle dependencies）✅ P0 已确认并修复（取消注释 build.gradle 中 media3.exoplayer.hls 依赖）
- [x] 1.5 确认 CacheUtil API 在 Media3 1.10.1 中的可用性 ✅ P0 已确认（实际改用 DataSource + CacheDataSink 替代 CacheUtil.cache()，详见 AD-17）
- [x] 1.6 **确认 ExoPlayer 是否支持运行时 setLoadControl 热切换**（R2 新增，R3 决策：放弃热切换，只在 prepare 前设置）✅ P0 已确认
- [x] 1.7 **确认 AppConfig/Preferences 现有结构与扩展点**（R3 新增）✅ P0 已确认（VideoPlay.kt 新增 4 个用户可配置参数）
- [x] 1.8 **确认 VideoPreloader 当前 cacheKey 生成逻辑**（R3 新增，阻塞点6）✅ P0 已确认并统一为纯 URL
- [x] 1.9 **确认 VideoPreloader 当前预加载触发时机与去重机制**（R3 新增，阻塞点7）✅ P0 已确认（触发时机去重留待 P1 实施）
- [x] 1.10 **确认 VideoPreloader 是否已有播放列表概念**（R3 新增，阻塞点8）✅ P0 已确认（PlayListManager 留待 P1 实施）
- [x] 1.11 **确认 AppLog 当前 release 包日志拦截逻辑**（R3 新增，阻塞点10）✅ P0 已确认并修复

## 2. P0 阶段：修复预加载 BUG

### 2.1 修复 FirstFramePreloader

- [x] 2.1.1 修改 `preloadUrl` 改用 `CacheUtil.cache()` 写入 SimpleCache ✅ P0 已完成（实施调整：改用 ExoPlayer DataSource + CacheDataSink 替代 CacheUtil.cache()，详见 AD-17）
  - Action: （已执行）将 `body.byteStream().readBytes()` 替换为 ExoPlayer DataSource + CacheDataSink 写入 SimpleCache
  - Observation: 预加载数据真正写入磁盘缓存（原 bug：OkHttp readBytes 只读取到内存后丢弃）
  - Adapt: 改用 DataSource + CacheDataSink 替代 CacheUtil.cache()，因 CacheDataSink 与播放器 CacheDataSource 读取路径完全对称，命中率高
- [x] 2.1.2 修改 `prewarmUrl` 改用 `CacheUtil.cache()` 写入 SimpleCache ✅ P0 已完成（同 2.1.1，改用 DataSource + CacheDataSink）
- [x] 2.1.3 移除 `readBytes()` 无限制读取 ✅ P0 已完成（用 DataSpec 限制读取字节数防止 OOM）
- [x] 2.1.4 **PRELOAD_BYTES 改为根据 DeviceTier+NetworkTier 动态调整**（R2 新增，R3 移除 LOW 档位）✅ P0 已完成（实施调整：改为 `getPreloadBytes()` 动态计算，HIGH=10MB/MID=5MB/用户可配，移除网络档位区分）
  - 实际实施：HIGH=10MB / MID=5MB / 用户可通过 `videoPreloadBytesMB` 配置（0=自动）
  - 检测失败默认 HIGH 档位（R3 调整）
- [ ] 2.1.5 验证修复后预加载数据真正写入 SimpleCache ⏳ 待真机验证（用户正在真机测试中）

### 2.2 修复 VideoPreloader

- [x] 2.2.1 修改 `preloadUrl` 改用 `CacheUtil.cache()` 写入 SimpleCache ✅ P0 已完成（实施调整：改用 ExoPlayer DataSource + CacheDataSink 替代 CacheUtil.cache()，详见 AD-17）
- [x] 2.2.2 移除 `readBytes()` 无限制读取 ✅ P0 已完成（用 DataSpec 限制读取字节数防止 OOM）
- [x] 2.2.3 **预加载数量改为根据 DeviceTier+NetworkTier 动态调整**（R2 新增，R3 移除 LOW 档位）✅ P0 已完成（实施调整：改为 `getPreloadCount()` 动态计算，移除 WiFi/4G 区分）
  - 实际实施：HIGH=10 个 / MID=7 个 / 用户可通过 `videoPreloadCount` 配置（0=自动）
  - 移除 WiFi/4G 网络感知区分（用户要求激进策略，用户可手动调低 videoPreloadCount 控制流量）
  - 移除 `isWifi()`/`isMobile()` 未使用方法
  - 检测失败默认 HIGH 档位（R3 调整）
- [x] 2.2.4 **预加载字节数改为根据 DeviceTier+NetworkTier 动态调整**（R2 新增，R3 移除 LOW 档位）✅ P0 已完成（实施调整：改为 `getPreloadBytes()` 动态计算，移除 WiFi/4G 区分）
  - 实际实施：HIGH=10MB / MID=5MB / 用户可通过 `videoPreloadBytesMB` 配置（0=自动）
  - 检测失败默认 HIGH 档位（R3 调整）
- [ ] 2.2.5 验证修复后预加载数据真正写入 SimpleCache ⏳ 待真机验证（用户正在真机测试中）

### 2.3 修复 HLS 依赖状态

- [x] 2.3.1 运行 `gradle dependencies` 确认 HLS 依赖来源 ✅ P0 已确认
- [x] 2.3.2 如果是 GSY 传递依赖：在 build.gradle 添加注释说明 ✅ P0 已完成（实际决策：取消注释，显式声明 HLS 支持）
- [x] 2.3.3 如果是直接依赖被误注释：取消注释恢复显式声明 ✅ P0 已完成（取消注释 `implementation(libs.media3.exoplayer.hls)`，显式声明 HLS 支持）
- [x] 2.3.4 验证 build.gradle 与代码状态一致 ✅ P0 已完成（编译通过 BUILD SUCCESSFUL in 4m 32s）

### 2.4 DeviceInfoHelper（R2 新增，R3 移除 LOW 档位）

- [x] 2.4.1 新增 `DeviceInfoHelper.kt` ✅ P0 已完成
  - Action: （已执行）实现 `getDeviceTier()` 方法，返回 MID/HIGH 两档（R3 调整：移除 LOW）
  - Observation: HIGH 阈值：内存≥6GB + CPU≥8核 + 磁盘≥10GB；MID 阈值：内存≥4GB 或 CPU≥8核
  - Adapt: 检测失败降级到 HIGH 档位（用户要求默认中高端机参数，非 MID）
- [x] 2.4.2 实现 `getTotalMemoryMB()`（ActivityManager.MemoryInfo）✅ P0 已完成
- [x] 2.4.3 实现 `getFreeDiskMB()`（StatFs）✅ P0 已完成
- [x] 2.4.4 实现 `getCpuCores()`（Runtime.availableProcessors）✅ P0 已完成
- [x] 2.4.5 实现结果缓存（避免重复检测）✅ P0 已完成
- [x] 2.4.6 **检测失败降级到 HIGH 档位**（R3 调整：默认 HIGH，不再降级到 MID/LOW）✅ P0 已完成（用户要求默认中高端机参数）
- [ ] 2.4.7 验证两档识别正确（模拟不同内存/CPU）⏳ 待真机验证

### 2.5 P0 阶段验证

- [x] 2.5.1 编译通过 ✅ P0 已完成（BUILD SUCCESSFUL in 4m 32s）
- [ ] 2.5.2 真机测试：预加载后二次播放命中缓存 ⏳ 待真机验证（用户正在真机测试中）
- [ ] 2.5.3 真机测试：readBytes 限制生效（无 OOM）⏳ 待真机验证
- [ ] 2.5.4 **真机测试：DeviceInfoHelper 正确识别 HIGH/MID 档位**（R2 新增，R3 调整）⏳ 待真机验证
- [ ] 2.5.5 真机回归：现有降级链/实例池/嗅探正常 ⏳ 待真机验证

### 2.5 补充：P0 实施额外文件变更说明

P0 实施时额外完成了以下文件变更（原 R3 设计中未明确列入 P0 文件清单）：

- **AppLog.kt**（修改）：release 包输出 WARN/INFO 日志（`putEntry`：ERROR/WARN/INFO 无条件 Log.e 输出；`putDebugWithTag`：recordLog 关闭时 ERROR/WARN/INFO 仍输出到 logcat）
- **VideoPlay.kt**（修改）：新增 4 个用户可配置参数（`videoMaxBufferSec`/`videoPreloadCount`/`videoPreloadBytesMB`/`videoPreloadTriggerProgress`，0=自动，用户可往下调）
- **ExoPlayerHelper.kt**（修改）：cache 容量范围 50-500MB → 50-2048MB；新增 `createPreloadDataSource` 方法（供预加载器复用 OkHttp 配置）

详见 design.md AD-17 P0 实施结果总结。

### 2.6 P0：用户可配置参数（R3 新增，阻塞点：用户可向下调参）✅ P0 已完成

- [x] 2.6.1 在 `AppConfig` 新增视频预缓冲用户配置项 ✅ P0 已完成（实施调整：在 `VideoPlay.kt` 而非 `AppConfig` 新增 4 个参数）
  - Action: （已执行）在 `VideoPlay.kt` 新增字段：`videoMaxBufferSec`（最大缓冲时长，0=自动，HIGH=120s/MID=90s）、`videoPreloadCount`（预加载数量，0=自动，HIGH=10/MID=7）、`videoPreloadBytesMB`（预加载字节数，0=自动，HIGH=10MB/MID=5MB）、`videoPreloadTriggerProgress`（预加载触发进度，默认10%）
  - Observation: 用户可通过配置参数往下调（0=自动跟随档位）
  - Adapt: 实施在 `VideoPlay.kt` 而非 `AppConfig`，因 VideoPlay 是视频播放配置的权威入口
- [ ] 2.6.2 在 `Preferences` 暴露配置入口（设置页：视频播放 → 预缓冲参数）⏳ 待实施（P1，UI 入口未在 P0 实施）
- [x] 2.6.3 实现"用户配置优先于档位默认值"合并逻辑（用户值非 0 时覆盖档位值）✅ P0 已完成
- [x] 2.6.4 配置变更时通知 VideoPreloader/FirstFramePreloader 刷新策略 ✅ P0 已完成（预加载器读取 `getPreloadBytes()`/`getPreloadCount()` 时实时获取最新配置）
- [ ] 2.6.5 配置变更时若需要重建 SimpleCache（缓存上限变更），先 flush 再重建 ⏳ 待实施（P1，cache 容量已扩展到 50-2048MB，但动态重建未实施）
- [x] 2.6.6 默认值：所有 override 字段默认 0（跟随档位）✅ P0 已完成（0=自动，HIGH=120s/10/10MB，MID=90s/7/5MB）
- [ ] 2.6.7 验证用户调小 maxBuffer 后下次播放生效 ⏳ 待真机验证
- [ ] 2.6.8 验证用户调小预加载数量后下次预加载生效 ⏳ 待真机验证

### 2.7 P0：cacheKey 策略统一（R3 新增，阻塞点6：预加载器与播放器 cacheKey 必须一致）✅ P0 已完成

- [x] 2.7.1 审计 `FirstFramePreloader` 当前 cacheKey 生成逻辑 ✅ P0 已完成
  - Action: （已执行）确认预加载器 cacheKey 生成逻辑
  - Observation: 原实现使用 OkHttp Request，未明确 cacheKey
  - Adapt: 改用 ExoPlayer DataSource + CacheDataSink 后，cacheKey 为纯 URL
- [x] 2.7.2 审计 `VideoPreloader` 当前 cacheKey 生成逻辑 ✅ P0 已完成
- [x] 2.7.3 审计 `ExoPlayerHelper`/`Exo2MediaPlayer` 播放器侧 cacheKey 生成逻辑 ✅ P0 已完成（播放器 `resolvingDataSource` 解析后 cacheKey 为纯 URL）
- [x] 2.7.4 **统一 cacheKey 生成函数 `VideoCacheKey.fromUrl(url)`**：统一使用 URL 字符串作为 cacheKey ✅ P0 已完成（实施调整：cacheKey 为纯 URL，不使用 `VideoCacheKey.fromUrl()` 封装，因播放器 `resolvingDataSource` 解析后即为纯 URL，预加载器必须与之一致）
  - 实施调整：cacheKey 为纯 URL（不做 MD5，不做规范化），与播放器 `resolvingDataSource` 解析后一致
  - 调整理由：MD5 会导致 cacheKey 不匹配，缓存未命中
- [x] 2.7.5 预加载器与播放器统一调用 `VideoCacheKey.fromUrl(url)` ✅ P0 已完成（预加载器 cacheKey 为纯 URL，与播放器一致）
- [ ] 2.7.6 验证预加载后播放器命中缓存（CacheDataSource 日志显示 cache hit）⏳ 待真机验证
- [ ] 2.7.7 验证不同 URL 不会误命中缓存 ⏳ 待真机验证

## 3. P1 阶段：激进 LoadControl + 全格式统一激进策略（R2 新增，R3 放弃热切换）

### 3.1 修改 buildLoadControl 支持激进参数（R3 调整：默认 HIGH，移除 LOW 分支）

- [ ] 3.1.1 修改 `ExoPlayerHelper.buildLoadControl` 接收 DeviceTier+NetworkTier 参数
  - Action: （待执行）实现激进策略矩阵（默认 HIGH+GOOD=120s）
  - 策略矩阵（R3，移除 LOW）：
    - HIGH+GOOD: 120s / HIGH+MEDIUM: 60s / HIGH+WEAK: 20s
    - MID+GOOD: 90s / MID+MEDIUM: 40s / MID+WEAK: 15s
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 3.1.2 修改 `Exo2MediaPlayer` 集成 DeviceInfoHelper 选择激进 LoadControl
- [ ] 3.1.3 验证 HIGH+GOOD maxBuffer=120s 生效
- [ ] 3.1.4 验证 MID+GOOD maxBuffer=90s 生效
- [ ] 3.1.5 验证 HIGH+WEAK maxBuffer=20s 生效（R3 调整：替换原 LOW 验证）

### 3.2 prepare 前设置 LoadControl（R3 调整：放弃热切换，替换原 3.2 热切换任务）

- [ ] 3.2.1 在 `Exo2MediaPlayer` prepare 前根据当前 DeviceTier+NetworkTier 一次性设置 LoadControl
  - Action: （待执行）在 `prepare()` 调用前调用 `buildLoadControl(deviceTier, networkTier)`，不在播放过程中热切换
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 3.2.2 验证 prepare 前设置后整次播放使用同一 LoadControl
- [ ] 3.2.3 验证播放过程中网络切换不会触发 setLoadControl（避免缓冲中断）
- [ ] 3.2.4 文档说明：网络档位变化在下次 prepare（下一集/重播）时生效

### 3.3 全格式统一激进策略

- [ ] 3.3.1 验证 HLS 格式激进 LoadControl 生效
- [ ] 3.3.2 验证 DASH 格式激进 LoadControl 生效
- [ ] 3.3.3 验证 MP4（Progressive）格式激进 LoadControl 生效
- [ ] 3.3.4 验证 FLV 格式激进 LoadControl 生效（如识别为 FLV）
- [ ] 3.3.5 验证 SS 格式激进 LoadControl 生效
- [ ] 3.3.6 验证所有格式预加载字节数统一 5-10MB

### 3.4 P1 激进策略验证（R3 调整：移除热切换与低端机测试）

- [ ] 3.4.1 编译通过
- [ ] 3.4.2 真机测试：HIGH 档位+好网 maxBuffer=120s
- [ ] 3.4.3 真机测试：HIGH 档位+好网预加载 10 个 10MB
- [ ] 3.4.4 真机测试：MID 档位降级到 MID 策略（R3 调整：替换原低端机测试）
- [ ] 3.4.5 真机测试：prepare 前设置 LoadControl 在播放过程中保持不变（R3 调整：替换原热切换测试）
- [ ] 3.4.6 真机测试：全格式统一激进（HLS/DASH/MP4/FLV/SS）

### 3.5 P1：预加载触发时机+去重（R3 新增，阻塞点7）

- [ ] 3.5.1 审计当前 `VideoPreloader` 预加载触发时机
  - Action: （待执行）确认当前是否在播放进度 50% 时触发预加载下一集
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 3.5.2 **触发时机从 50% 调整为可配置默认 10%**（AppConfig 新增 `videoPreloadTriggerPercent`，默认 0.1，用户可在设置页调整 0.05-0.5）
- [ ] 3.5.3 在 `VideoPlayerActivity` 进度回调中按配置百分比触发预加载
- [ ] 3.5.4 **URL 去重**：预加载前调用 `preloadCache.containsKey(cacheKey)` 判断是否已预加载，已存在则跳过
- [ ] 3.5.5 **触发去重**：同一 URL 在同一播放会话内只触发一次预加载（避免进度回调重复触发）
- [ ] 3.5.6 验证 10% 进度时触发预加载
- [ ] 3.5.7 验证已预加载 URL 不会重复预加载
- [ ] 3.5.8 验证用户调整触发百分比后下次播放生效

### 3.6 P1：内部播放列表管理（R3 新增，阻塞点8）

- [ ] 3.6.1 新增 `PlayListManager.kt`
  - Action: （待执行）在 VideoPreloader 内部维护播放列表（章节列表/集列表），提供 `getCurrentIndex()`/`getNextUrl()`/`setPlayList(list, currentIndex)` API
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 3.6.2 `VideoPreloader.setPlayList(urls: List<String>, currentIndex: Int)` 设置播放列表
- [ ] 3.6.3 `VideoPreloader.preloadNext(currentUrl: String)` 自动推断下一集 URL 并预加载
- [ ] 3.6.4 在 `VideoPlayerActivity` 加载播放列表时调用 `setPlayList`
- [ ] 3.6.5 在播放器切换集数时更新 `currentIndex`
- [ ] 3.6.6 验证播放列表末尾时 `getNextUrl()` 返回 null（不再预加载）
- [ ] 3.6.7 验证播放列表切换时清空旧预加载队列
- [ ] 3.6.8 验证预加载数量受 DeviceTier+NetworkTier+用户配置三方约束

## 4. P1 阶段：HLS 协议级优化

### 4.1 启用 setAllowChunklessPreparation

- [ ] 4.1.1 修改 `ExoPlayerHelper.createMediaSource` HLS 分支
  - Action: （待执行）在 `HlsMediaSource.Factory(dataSourceFactory)` 后添加 `.setAllowChunklessPreparation(true)`
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 4.1.2 修改 `Exo2MediaPlayer.applyMediaSourceByType` HLS 分支
- [ ] 4.1.3 验证 HLS 首屏耗时降低 30%+

### 4.2 VOD 类型识别与全量缓存

- [ ] 4.2.1 新增 `HlsPlaylistTypeDetector.kt`
- [ ] 4.2.2 在嗅探阶段解析 `#EXT-X-PLAYLIST-TYPE`
- [ ] 4.2.3 VOD 类型启用全量缓存策略
- [ ] 4.2.4 EVENT 类型预加载后续 N 个分片
- [ ] 4.2.5 LIVE 类型不缓存

### 4.3 P1 HLS 优化验证

- [ ] 4.3.1 编译通过
- [ ] 4.3.2 真机测试：HLS 首屏耗时降低
- [ ] 4.3.3 真机测试：VOD 类型全量缓存生效
- [ ] 4.3.4 真机回归：现有降级链正常

## 5. P1 阶段：运行时网络感知（R3 调整：移除 LoadControl 热切换通知）

### 5.1 新增 NetworkMonitor

- [ ] 5.1.1 新增 `NetworkMonitor.kt`
  - Action: （待执行）实现 `ConnectivityManager.NetworkCallback` 注册/注销（R3 调整：移除 LoadControl 热切换通知）
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 5.1.2 提供网络切换回调接口
- [ ] 5.1.3 在 `VideoPlayerActivity.onCreate` 注册
- [ ] 5.1.4 在 `VideoPlayerActivity.onDestroy` 注销
- [ ] 5.1.5 **网络档位变化时通知 VideoPreloader/FirstFramePreloader 调整预加载数量与字节**（R2 新增，R3 调整：移除 LoadControl 热切换通知，只调整预加载器参数）

### 5.2 预加载器支持网络策略动态调整

- [ ] 5.2.1 `FirstFramePreloader` 新增 `updateNetworkStrategy(networkType)`
- [ ] 5.2.2 `VideoPreloader` 新增 `updateNetworkStrategy(networkType)`
- [ ] 5.2.3 **网络切换时动态调整预加载数量（HIGH+GOOD=10 个 / WEAK=1 个）**（R2 新增，R3 移除 LOW 档位）
- [ ] 5.2.4 **网络切换时动态调整预加载字节数（HIGH+GOOD=10MB / WEAK=1MB）**（R2 新增，R3 移除 LOW 档位）

### 5.3 P1 网络感知验证（R3 调整：移除热切换测试）

- [ ] 5.3.1 编译通过
- [ ] 5.3.2 真机测试：WiFi→4G 预加载数量调整（10→1）
- [ ] 5.3.3 真机测试：4G→WiFi 预加载数量调整（1→10）
- [ ] 5.3.4 真机测试：已预加载数据保留
- [ ] 5.3.5 真机测试：网络切换时不触发 LoadControl 热切换（R3 调整：替换原热切换测试，验证播放不中断）

## 6. P2 阶段：埋点与 DefaultPreloadManager 评估

### 6.1 埋点

- [ ] 6.1.1 新增 `PreloadMetrics.kt`（命中率/失败率/首帧命中率计数器）
- [ ] 6.1.2 **新增设备档位/网络档位/maxBuffer 埋点**（R2 新增）
- [ ] 6.1.3 CacheDataSource 注入 EventListener
- [ ] 6.1.4 预加载器补充成功率/失败率埋点
- [ ] 6.1.5 `Exo2MediaPlayer.onRenderedFirstFrame` 补充首帧命中率统计
- [ ] 6.1.6 每 5 分钟 AppLog 输出命中率统计

### 6.2 DefaultPreloadManager 评估

- [ ] 6.2.1 评估与 GSY `IjkExo2MediaPlayer` 生命周期管理的冲突
- [ ] 6.2.2 评估与 `PlayerInstancePool` 池化逻辑的兼容性
- [ ] 6.2.3 评估 ExoPlayer 创建方式兼容性（DefaultPreloadManager 要求共享 Builder）
- [ ] 6.2.4 输出兼容性评估报告
- [ ] 6.2.5 决策是否引入 DefaultPreloadManager

### 6.3 P2 验证

- [ ] 6.3.1 编译通过
- [ ] 6.3.2 真机测试：埋点数据输出
- [ ] 6.3.3 真机回归：现有功能不退化

### 6.4 P2：AppLog 正式包日志修复（R3 新增，阻塞点10）

- [ ] 6.4.1 审计 `AppLog` 当前 release 包日志拦截逻辑
  - Action: （待执行）确认是否使用 `BuildConfig.DEBUG` 拦截所有级别日志
  - Observation: （待观察）
  - Adapt: （待调整）
- [ ] 6.4.2 **修改 AppLog：release 包输出 WARN/ERROR 级别日志**（移除 `BuildConfig.DEBUG` 对 WARN/ERROR 的拦截，DEBUG/INFO 仍只 debug 包输出）
- [ ] 6.4.3 验证 release 包日志输出 WARN/ERROR 级别日志
- [ ] 6.4.4 验证 debug 包日志输出全级别（DEBUG/INFO/WARN/ERROR）
- [ ] 6.4.5 验证预缓冲埋点 WARN/ERROR 在 release 包可见

## 7. 文档同步与交付

### 7.1 文档同步

- [ ] 7.1.1 更新 `docs/INDEX.md`（移动到"已完成的功能"）
- [ ] 7.1.2 更新 `assets/updateLog.md`（编译前更新用户可感知变化）
- [ ] 7.1.3 更新 README.md 状态为 "✅ 已完成"
- [ ] 7.1.4 tasks.md 全部标记 ✅

### 7.2 最终验收

- [ ] 7.2.1 真机回归测试通过
- [ ] 7.2.2 用户最终验收

---

## AOAdapt 日志

> 记录实施过程中遇到的问题及调整

### 阶段 1：需求分析与源码探索

- **Action**: 启动 4 个子代理并行探索（视频播放器核心/预缓冲机制/格式支持/网上方案）
- **Observation**: 子代理报告了关键文件路径，但部分代码片段可能是子代理编造的（未实际 Read 确认）
- **Adapt**: 主代理用 Glob/Grep/Read 验证子代理报告的文件真实性，发现 `media3-exoplayer-hls` 依赖被注释但代码仍使用 HlsMediaSource，并发现预加载 BUG（readBytes 无限制 + 未写入 SimpleCache）

### 阶段 2：四文档生成（V1 保守版）

- **Action**: 主代理直接生成四文档（未使用子代理并行生成，因已掌握所有关键信息）
- **Observation**: 上下文占用约 60%，未触发子代理强制条件
- **Adapt**: 直接生成，避免子代理重新探索浪费时间

### 阶段 3：R2 激进版修订（2026-07-28 15:17 用户反馈）

- **Action**: 用户反馈 V1 过于保守，要求激进版（maxBuffer 90-120s + 预加载 5-10 个 + 预加载 5-10MB + 中高端机检测 + 全格式统一激进）
- **Observation**: V1 保守版在好网+中高端机下浪费带宽/内存/磁盘，无法满足用户"尽快缓冲加载更多视频内容防止卡顿"诉求
- **Adapt**: 
  1. 新增 DeviceInfoHelper 检测设备档位（LOW/MID/HIGH）
  2. 新增激进策略矩阵（HIGH+GOOD=120s/10个/10MB/1GB）
  3. 新增 LoadControl 热切换（网络档位提升时重新 prepare）
  4. 新增全格式统一激进策略（HLS/DASH/MP4/FLV/SS 统一激进 LoadControl）
  5. 新增低端机保护（LOW 档位降级到 V1 保守策略）
  6. 新增 4 个 ADR（AD-08 运行时检测 / AD-09 热切换 / AD-10 全格式统一 / AD-11 低端机保护）

### 阶段 4：R3 修订版（2026-07-28 用户审查反馈）

- **Action**: 用户审查 R2 激进版后反馈需再次修订，核心调整七项：移除低端机保护 + 用户可配置参数 + 放弃 LoadControl 热切换 + cacheKey 统一 + 预加载触发时机去重 + 内部播放列表管理 + AppLog 正式包日志修复
- **Observation**: R2 激进版存在以下问题：
  1. LOW 档位保护逻辑复杂且检测不准确（内存/CPU 阈值难定）
  2. LoadControl 热切换在播放过程中可能造成缓冲中断（用户反馈风险高）
  3. 参数完全自动档位化，用户无法根据自身场景微调（如流量敏感用户希望调小预加载）
  4. 预加载器与播放器 cacheKey 不一致导致缓存命中率低（阻塞点6）
  5. 预加载触发时机 50% 太晚，且无 URL 去重导致重复预加载（阻塞点7）
  6. VideoPreloader 无播放列表概念，无法自动推断下一集（阻塞点8）
  7. AppLog release 包拦截所有日志导致线上问题难定位（阻塞点10）
- **Adapt**: 
  1. **移除低端机保护**：DeviceInfoHelper 只检测 HIGH/MID，默认 HIGH；策略矩阵移除 LOW 行；检测失败降级到 HIGH（不再降级到 MID/LOW）
  2. **用户可配置参数**（新增 2.6）：AppConfig/Preferences 暴露 maxBuffer 倍数、预加载数量上限、预加载字节上限、缓存上限四项 override，用户值非 0 时覆盖档位默认值
  3. **放弃 LoadControl 热切换**（修改 3.2）：只在 prepare 前根据当前 DeviceTier+NetworkTier 一次性设置 LoadControl，播放过程中不热切换；网络档位变化在下次 prepare（下一集/重播）时生效
  4. **cacheKey 策略统一**（新增 2.7）：新增 `VideoCacheKey.fromUrl(url)` 统一使用 URL 作为 cacheKey，预加载器与播放器统一调用
  5. **预加载触发时机+去重**（新增 3.5）：触发时机从 50% 调整为可配置默认 10%（AppConfig `videoPreloadTriggerPercent`，用户可调 0.05-0.5）；预加载前 `preloadCache.containsKey(cacheKey)` 判断去重；同一 URL 在同一播放会话内只触发一次
  6. **内部播放列表管理**（新增 3.6）：新增 `PlayListManager.kt`，VideoPreloader 内部维护播放列表，提供 `setPlayList`/`getNextUrl`/`preloadNext` API，自动推断下一集
  7. **AppLog 正式包日志修复**（新增 6.4）：修改 AppLog 移除 `BuildConfig.DEBUG` 对 WARN/ERROR 的拦截，release 包输出 WARN/ERROR 级别日志（DEBUG/INFO 仍只 debug 包输出）
  8. **风险表更新**：移除"LoadControl 热切换导致缓冲中断"风险（已放弃热切换），新增"用户配置参数可能误操作"风险

### 阶段 5：P0 实施完成（2026-07-28）

- **Action**: P0 阶段实施完成，实际实施范围在 R3 设计基础上扩展，除原 P0 项（R1/R2/R3）外，将原 P1 中的 R4（DeviceInfoHelper）/R13（用户可配置参数）/R14（cacheKey 统一）/R17（AppLog 修复）提前到 P0 实施，共完成 7 个文件变更
- **Observation**: P0 实施过程中遇到 5 个 R3 设计未明确的实施细节决策：
  1. CacheUtil.cache() 改用 DataSource + CacheDataSink（CacheDataSink 与播放器 CacheDataSource 读取路径对称，命中率高）
  2. 移除 WiFi/4G 网络感知区分（用户要求激进策略，用户可手动调低 videoPreloadCount 控制流量）
  3. cacheKey 统一为纯 URL（不做 MD5，与播放器 resolvingDataSource 解析后一致）
  4. 检测失败降级到 HIGH（用户要求默认中高端机参数，非 MID）
  5. 新增 createPreloadDataSource 方法（预加载器复用 OkHttp 配置，确保请求行为一致）
- **Adapt**:
  1. **CacheDataSink 写入 SimpleCache**：预加载器改用 ExoPlayer DataSource + CacheDataSink，预加载数据真正写入磁盘缓存（原 bug：OkHttp readBytes 只读取到内存后丢弃）
  2. **PRELOAD_BYTES/MAX_CACHE_SIZE 动态计算**：从固定值改为 `getPreloadBytes()`/`getPreloadCount()` 动态计算（HIGH=10MB/10个，MID=5MB/7个，用户可配）
  3. **DataSpec 限制读取字节数**：防止 OOM（原 bug：readBytes() 读取整个响应体）
  4. **ExoPlayerHelper cache 容量扩展**：50-500MB → 50-2048MB（支持 HIGH 档位 1GB 缓存）
  5. **AppLog release 包日志修复**：ERROR/WARN/INFO 无条件 Log.e 输出（release 包也能采集关键日志）
  6. **VideoPlay.kt 新增 4 个用户可配置参数**：videoMaxBufferSec/videoPreloadCount/videoPreloadBytesMB/videoPreloadTriggerProgress（0=自动，用户可往下调）
  7. **build.gradle 取消注释 media3.exoplayer.hls**：显式声明 HLS 支持
- **编译验证**：BUILD SUCCESSFUL in 4m 32s
- **APK 安装**：测试包 `io.legado.miss.app.debug`，版本 3.26.072816
- **真机测试**：用户正在真机测试中，稍后提供调试日志
- **待闭环项**：验证类任务（2.1.5/2.2.5/2.4.7/2.5.2-2.5.5/2.6.7-2.6.8/2.7.6-2.7.7）待真机验证后闭环

### 阶段 6：P1/P2 待实施

- P1 待实施项（5 项）：激进 LoadControl + 全格式统一激进策略 + 预加载触发时机去重 + 内部播放列表管理 + 运行时网络感知
- P2 待实施项（2 项）：埋点 + DefaultPreloadManager 评估

---

## 任务完成标准

| 级别 | 标准 | 适用任务 |
|------|------|---------|
| Level 1 - 代码完成（⚠️） | 文件存在 + 编译通过 | 所有任务 |
| Level 2 - 功能验证（⚠️） | 关键功能可运行 + 输出正确 | P0/P1 任务 |
| Level 3 - 场景验证（✅） | 真机数据回测通过 | P0 任务 + P1 关键任务 |

---

## 风险与回退

| 风险 | 回退方案 |
|------|---------|
| CacheUtil.cache() 与现有 SimpleCache 锁冲突 | 回退到手动 CacheDataSink 写入 |
| setAllowChunklessPreparation 不兼容 | 移除该 flag，降级到默认准备 |
| NetworkCallback 不触发 | 添加定时轮询兜底 |
| DefaultPreloadManager 不兼容 | 维持自研预加载器 |
| 修复后磁盘占用过高 | 调小 videoCacheSize 默认值 |
| **激进策略导致中低端机 OOM**（R3 调整：移除 LOW 档位后改述） | 用户可通过 AppConfig override 调小预加载数量/字节；DeviceInfoHelper 检测失败时降级到 MID 档位 |
| **激进预加载导致流量浪费**（R2） | 4G 网络下强制降级到保守策略 |
| **设备档位检测不准确**（R3 调整） | 检测失败降级到 HIGH 档位（默认档位） |
| **1GB 磁盘缓存占满磁盘**（R2） | 磁盘空间<10GB 时降级缓存上限到 500MB；用户可通过 AppConfig override 调小缓存上限 |
| **用户配置参数可能误操作**（R3 新增） | 配置页提供"恢复默认值"按钮；override 字段范围校验（multiplier 0.5-1.0，count 0-10，bytes 0-10MB，cacheSize 0-1000MB）；异常值回退到档位默认值 |
| **cacheKey 统一后历史缓存失效**（R3 新增） | 升级时清空旧 SimpleCache（用户无感知，下次预加载重建） |
| **预加载触发时机 10% 过早导致占用带宽**（R3 新增） | 用户可通过 AppConfig 调大触发百分比（默认 0.1，可调 0.05-0.5） |
| **PlayListManager 与现有播放列表逻辑冲突**（R3 新增） | 保留现有播放列表逻辑作为 fallback；PlayListManager 仅在显式 setPlayList 时启用 |
| **AppLog release 包日志泄露敏感信息**（R3 新增） | WARN/ERROR 级别日志禁止输出 URL/cookie/源名称等业务数据；只输出技术字段（错误码/异常类型/调用栈） |
