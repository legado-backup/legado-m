# 播放器综合审查与遗漏点补全 - 技术设计

> 状态：✅ P0已实施完成（2026-07-29 16:30 代码实施+编译通过，待真机验证；AD-01/03/04/05 Implemented，AD-02 P1暂未实施）
> 创建时间：2026-07-29
> 关联文档：[spec.md](./spec.md) | [tasks.md](./tasks.md) | [README.md](./README.md)
> 用户铁律：(1)别过度工程化-不新增独立管理器/协调器 (2)别影响现有功能-不修改嗅探/播放/图片加载主链路 (3)深入反省深入思考深入分析

---

## 1. Technical Approach（简化版技术方案）

### 1.1 整体思路（2026-07-29 14:24 深入反省后大幅简化）

> **用户铁律**（2026-07-29 14:24 反馈）：
> 1. **别过度工程化**：不新增独立管理器/协调器，在现有组件上增量扩展
> 2. **别影响现有功能**：不修改嗅探主链路，不修改播放链路，仅扩展配置和UI
> 3. **深入反省**：从23文件变更降到10文件（3新增+7修改）

本设计在已完成的 18 个视频播放器 spec + 5 个图片播放器 spec 基础上，针对综合审查识别的遗漏点提出**最小侵入补全方案**。方案遵循以下原则：

- **复用优先**：在现有 `ExoPlayerHelper`、`FirstFramePreloader`、`ImageUrlExtractor`、`ImageLoader` 等核心组件上增量扩展，**不新增独立管理器/协调器**
- **最小侵入**：总变更文件从原设计23个降到10个（3新增+7修改），每个修改点都是增量扩展不替换现有逻辑
- **嗅探保护**（用户铁律）：所有新增逻辑与嗅探链路解耦，嗅探失败不阻塞新增逻辑，新增逻辑失败不阻塞嗅探
- **不影响现有功能**：不修改 `MimeSniffer.kt`、`ImageUrlExtractor.kt` 核心嗅探逻辑，不修改 `exoplayer-resilience` 降级链，仅在现有组件上追加扩展

### 1.2 简化后的补全方案

| 遗漏点 | 原方案（过度工程） | 简化方案（复用现有组件） | 影响现有功能风险 |
|--------|------------------|----------------------|---------------|
| 视频首帧加载 | 新增ParallelSniffPreconnectCoordinator协调器（4路并行） | 在现有FirstFramePreloader上扩展分档位预加载参数 | 无（仅调整预加载深度） |
| 视频智能缓冲 | 新增NetworkTypeDetector独立组件 | 在现有createLoadControlByTier中增加网络类型判断 | 无（仅在prepare前增加判断） |
| 视频错误提示 | 新增ErrorMapper（保留，纯UI） | 新增ErrorMapper.kt（纯UI，不涉及嗅探/播放链路） | 无（仅UI增强） |
| 视频网络重连 | 新增AutoReconnectManager独立管理器 | 在现有onPlayerError中增加简单重试逻辑（3次指数退避） | 无（仅扩展错误处理回调） |
| 视频播放历史 | 新增PlayHistoryStore（保留，纯数据） | 新增PlayHistoryStore.kt+PlayHistory.kt（纯数据持久化） | 无（仅数据持久化） |
| 图片大图内存 | 新增BitmapSamplingLoader独立加载器 | 在现有ImageLoader.kt中增加override()采样配置 | 无（仅扩展Glide配置） |
| 图片智能缓存 | 新增AdaptiveCacheManager运行时动态调整 | 在App启动时根据设备档位设置一次Glide缓存 | 无（仅初始化时设置） |
| 图片SPA嗅探 | 新增WebpackHookEnhancer独立增强器 | 在现有IMAGE_SNIFF_JS常量追加MutationObserver脚本 | 极低（仅追加JS脚本，不替换原Hook） |
| 图片元数据 | 新增ImageMetadataExtractor | 降级为P2，暂不实施（低实用性） | 无 |
| 图片批量保存 | 新增BatchSaveManager独立管理器 | 在现有ImageGalleryActivity增加批量保存循环 | 无（仅UI层循环调用） |

### 1.3 灵活配置方案（简化版）

> 原方案新增PlayerConfigManager独立管理器 → 简化为在现有SharedPreferences增加配置项

在现有 `AppConfig` 或 `SharedPreferences` 中增加以下配置项：
- `player_buffer_strategy`：缓冲策略（自动/激进GOOD/平衡MEDIUM/保守WEAK，默认自动）
- `player_precache_range`：预缓存范围（0关闭/1/2/3，默认1）
- `player_history_enabled`：播放历史开关（true/false，默认true）
- `player_firstframe_preload`：首帧预加载开关（true/false，默认true）

配置入口：在现有播放器设置页（PreferenceFragment）增加配置项，复用现有UI风格。

---

## 2. Architecture Decisions（简化版，6个核心ADR）

### AD-01: 首帧加载分档位策略（在现有组件扩展，不新增协调器）

- **Context**: 当前首帧渲染时间约4027ms。`FirstFramePreloader` 已实现 64KB 预热（`prewarmCurrentVideo`）和 ±1 相邻视频预加载（`preloadFirstFrame`），但预加载深度固定，未按设备档位差异化。
- **Concern**: 原方案新增 `ParallelSniffPreconnectCoordinator` 协调器4路并行任务，过度工程化且可能影响嗅探主链路。
- **Decision**: 在现有 `FirstFramePreloader` 上扩展分档位预加载参数：WEAK档不预加载首帧、MEDIUM档预加载1个分片、GOOD档预加载3个分片。不新增协调器，不并行化嗅探（嗅探保持串行主链路不变）。预加载深度由 `PlayerConfig` 的 `player_firstframe_preload` 配置项控制。
- **Goal**: 首帧渲染时间从4027ms降至2000ms以内（通过预加载深度优化，不通过并行化）。
- **Tradeoff**: 不并行化嗅探意味着无法消除嗅探3s等待，但保证了嗅探主链路稳定性（用户铁律）。首帧优化通过预加载深度调整实现，收益小于并行化方案但风险极低。
- **Status**: Implemented（2026-07-29，FirstFramePreloader.kt L175-226 分档位WEAK=0/MEDIUM=1/GOOD=3，配置项playerFirstFramePreload/playerPrecacheRange已接入）
- **嗅探保护**: ✅ 不修改嗅探主链路，仅扩展预加载参数

### AD-02: 网络类型感知缓冲（在现有方法扩展，不新增独立组件）

- **Context**: `ExoPlayerHelper.createLoadControlByTier` 已有 `BandwidthTier`(WEAK/MEDIUM/GOOD) 按带宽分档。但首次播放时 `bitrateEstimate=0`（无历史数据），无法感知网络类型。
- **Concern**: 原方案新增 `NetworkTypeDetector` 独立组件，过度工程化。
- **Decision**: 在现有 `createLoadControlByTier` 方法中增加网络类型判断：首次播放（bitrateEstimate=0）时通过 `ConnectivityManager.getActiveNetworkInfo` 检测网络类型（WiFi→GOOD/4G→MEDIUM/3G→WEAK），带宽测量生效后以带宽为主。用户可通过配置项 `player_buffer_strategy` 手动覆盖。
- **Goal**: 首次播放首帧前即能选择合理缓冲档位。
- **Tradeoff**: 网络类型检测在方法内部增加几行代码，不新增独立组件，复杂度极低。
- **Status**: Proposed
- **嗅探保护**: ✅ 不涉及嗅探链路

### AD-03: 播放错误用户友好映射器（新增1个文件，纯UI）

- **Context**: `VideoPlayerActivity` 播放失败时直接展示 ExoPlayer 错误码，用户不可读。
- **Concern**: 用户不知道失败原因及如何处理。
- **Decision**: 新增 `ErrorMapper.kt`（放置 `app/src/main/java/io/legado/app/help/player/`），建立错误码→`UserFacingError` 映射表。`VideoPlayerActivity` 的 `onPlayerError` 回调中调用 `ErrorMapper.map(error)` 获取用户友好提示，用 MaterialAlertDialog 展示（对齐项目现有错误弹窗风格）。
- **Goal**: 播放失败时用户能理解错误原因并知道下一步操作。
- **Tradeoff**: 仅新增1个文件+修改1个回调，纯UI增强不涉及嗅探/播放链路。
- **Status**: Implemented（2026-07-29，ErrorMapper.kt已创建+VideoPlayerActivity L1484接入+strings.xml 12条文案）
- **嗅探保护**: ✅ 不涉及嗅探链路

### AD-04: 播放历史跨会话记忆（新增2个文件，纯数据）

- **Context**: 播放进度仅在 Activity 内存中，退出即丢失。
- **Concern**: 长视频中途退出后无法恢复进度。
- **Decision**: 新增 `PlayHistory.kt`（Room实体）+ `PlayHistoryStore.kt`（持久化Helper）。`VideoPlayerActivity` 每10s + onPause 时调用 `PlayHistoryStore.save()` 持久化进度；`initSource` 时调用 `PlayHistoryStore.load(url)` 恢复进度。数据库新增表，version+1（遵循 database-migration-safety.md）。
- **Goal**: 跨会话恢复播放进度。
- **Tradeoff**: 仅新增2个文件+修改VideoPlayerActivity几个生命周期回调，纯数据持久化不涉及嗅探/播放链路。Room数据库升级需谨慎（提供空Migration）。
- **Status**: Implemented（2026-07-29，PlayHistory.kt+PlayHistoryDao.kt+PlayHistoryStore.kt+AppDatabase v101+DatabaseMigrations migration_100_101+VideoPlayerActivity onPause保存/onResume定时保存/initSource恢复）
- **嗅探保护**: ✅ 不涉及嗅探链路

### AD-05: 大图采样加载（在现有ImageLoader扩展，不新增独立加载器）

- **Context**: Glide 默认全分辨率加载，大图可能 OOM。
- **Concern**: 原方案新增 `BitmapSamplingLoader` 独立加载器，过度工程化。
- **Decision**: 在现有 `ImageLoader.kt` 中为图片加载请求添加 `override()` 采样：根据 ImageView 尺寸计算目标分辨率，极高分辨率图片（>4096px）强制降级到2048px。在 Glide RequestListener.onLoadFailed 中捕获 OutOfMemoryError，降级到更低分辨率重试。App启动时根据设备档位设置一次 Glide 缓存大小（不运行时动态调整）。
- **Goal**: 大图加载不触发 OOM。
- **Tradeoff**: 仅在现有ImageLoader中增加几行配置代码，不新增独立加载器。
- **Status**: Implemented（2026-07-29，ImageLoader.kt L114-124 新增loadWithSampling方法，极高分辨率>4096强制降级到2048）
- **嗅探保护**: ✅ 不涉及嗅探链路

### AD-06: 嗅探能力保护约束（用户铁律，Accepted）

- **Context**: 用户2026-07-29 14:15+14:24 两次审查反馈明确要求"嗅探能力现在很棒了，不要降低"。
- **Concern**: 新增组件可能影响嗅探主链路。
- **Decision**: 确立"嗅探能力保护"为最高约束：(1) 禁止修改 `MimeSniffer.kt` 和 `ImageUrlExtractor.kt` 的核心嗅探逻辑，仅可扩展(2) 所有新增逻辑与嗅探链路解耦，try-catch独立失败降级(3) 图片SPA嗅探增强仅在现有 `IMAGE_SNIFF_JS` 常量追加 MutationObserver 脚本，不替换原5路Hook(4) 实施后真机验证嗅探成功率不低于当前水平。
- **Goal**: 确保所有新增逻辑实施后，视频/图片嗅探成功率不低于当前水平。
- **Tradeoff**: 无（保护性约束，不增加复杂度）。
- **Status**: Accepted（用户铁律，不可降级）

---

## 3. Data Flow（简化版）

### 3.1 视频首帧加载（AD-01，复用FirstFramePreloader）

`VideoPlayerActivity.initSource` 调用 `FirstFramePreloader.prewarmCurrentVideo(url)` 时，根据 `PlayerConfig.player_firstframe_preload` 和设备档位（`DeviceInfoHelper.getDeviceTier()`）选择预加载深度：WEAK档跳过预加载、MEDIUM档预加载1个分片、GOOD档预加载3个分片。预加载失败仅记录日志，不影响主播放链路。嗅探主链路（`ExoPlayerHelper.sniffVideoType`）保持不变。

### 3.2 智能缓冲（AD-02，复用createLoadControlByTier）

`ExoPlayerHelper.createLoadControlByTier` 调用前，先检查 `PlayerConfig.player_buffer_strategy`：若用户手动选择则用用户选择；若为"自动"则检测网络类型（WiFi→GOOD/4G→MEDIUM/3G→WEAK）。带宽测量生效后（bitrateEstimate>0）以带宽为主。LoadControl 参数设置逻辑不变，仅档位选择增加网络类型维度。

### 3.3 错误提示（AD-03，新增ErrorMapper）

ExoPlayer `onPlayerError(error)` 回调中调用 `ErrorMapper.map(error)` 获取 `UserFacingError(title, message, actions)`。用 MaterialAlertDialog 展示错误提示+操作按钮（重试/换源/反馈）。错误日志通过 `AppLog.put("PlayerError", ...)` 记录。

### 3.4 播放历史（AD-04，新增PlayHistoryStore+PlayHistory）

`VideoPlayerActivity.onResume` 启动定时保存（每10s）调用 `PlayHistoryStore.save(url, position, duration)`。`onPause` 保存最后一次并取消定时。`initSource` 中 ExoPlayer prepare 完成后调用 `PlayHistoryStore.load(url)`，若 position>10s 则 seekTo + Toast 提示"已从 XX:XX 继续播放"。

### 3.5 大图采样（AD-05，复用ImageLoader）

`ImageLoader` 加载图片时根据 ImageView 尺寸调用 `override(targetWidth, targetHeight)` 采样。极高分辨率图片（>4096px）降级到2048px。OOM 时 catch OutOfMemoryError 降级重试。App启动时根据设备档位设置 Glide MemoryCache 大小（HIGH=96MB/MID=48MB/LOW=24MB），不运行时调整。

### 3.6 图片SPA嗅探增强（AD-06约束下，在IMAGE_SNIFF_JS追加脚本）

`ImageUrlExtractor` 的 `IMAGE_SNIFF_JS` 常量追加 MutationObserver 脚本：监听 `document.body` 子树变化，新增 `<img>` 节点时提取 src。**不替换**原5路Hook，仅追加。嗅探超时保持8s不变（不延长，避免影响现有行为）。

---

## 4. File Changes（简化版，3新增+7修改=10文件）

### 4.1 新增文件（3个）

| 文件路径 | 说明 | 关联 ADR |
|---------|------|---------|
| `app/src/main/java/io/legado/app/help/player/ErrorMapper.kt` | 播放错误用户友好映射器（错误码→UserFacingError映射表） | AD-03 |
| `app/src/main/java/io/legado/app/data/entities/PlayHistory.kt` | 播放历史Room实体 | AD-04 |
| `app/src/main/java/io/legado/app/data/help/PlayHistoryStore.kt` | 播放历史持久化Helper | AD-04 |

### 4.2 修改文件（7个）

| 文件路径 | 修改内容 | 关联 ADR |
|---------|---------|---------|
| `app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt` | `prewarmCurrentVideo` 增加分档位预加载深度参数（WEAK/MEDIUM/GOOD） | AD-01 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | `createLoadControlByTier` 增加网络类型判断+用户配置覆盖 | AD-02 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | (1) `onPlayerError` 接入 ErrorMapper (2) `initSource`/`onResume`/`onPause` 接入 PlayHistoryStore (3) `onPlayerError` 增加简单重试逻辑(3次指数退避) | AD-03/04 |
| `app/src/main/java/io/legado/app/help/image/ImageLoader.kt` | (1) 增加 override() 采样配置 (2) OOM 降级重试 (3) App启动时设置Glide缓存大小 | AD-05 |
| `app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt` | `IMAGE_SNIFF_JS` 常量追加 MutationObserver 脚本（不替换原Hook） | AD-06 |
| `app/src/main/java/io/legado/app/data/db/ReadDatabase.kt` | 新增 PlayHistory 实体到 @Database 列表，version+1，空Migration | AD-04 |
| `app/src/main/res/values/strings.xml` | 新增错误提示文案+播放历史文案 | AD-03/04 |

### 4.3 变更文件汇总

| 类别 | 新增文件数 | 修改文件数 | 合计 |
|------|----------|----------|------|
| 视频播放器 | 2 | 3 | 5 |
| 图片播放器 | 0 | 2 | 2 |
| 数据层 | 1 | 1 | 2 |
| 资源文件 | 0 | 1 | 1 |
| **合计** | **3** | **7** | **10** |

> **对比原方案**：原方案23文件（12新增+11修改），简化后10文件（3新增+7修改），减少56%。

### 4.4 不修改文件（嗅探保护，AD-06约束）

以下核心文件**禁止修改**（用户铁律：不降低嗅探能力）：
- `MimeSniffer.kt`（视频MIME嗅探核心）
- `ImageSnifferWebView.kt`（图片嗅探WebView核心，仅扩展JS脚本不修改核心逻辑）
- `exoplayer-resilience` 相关文件（降级链核心）
- `VideoPreloader.kt`（预加载核心，仅调整参数不修改逻辑）

---

## 5. 约束与风险

### 5.1 技术约束

- **嗅探保护（用户铁律）**：禁止修改嗅探主链路核心文件，仅可扩展
- **Room数据库升级**：AD-04 新增 PlayHistory 表需 version+1，必须提供空 Migration（对齐 database-migration-safety.md）
- **Glide缓存初始化**：AD-05 的缓存大小设置需在 App.onCreate 通过 GlideModule 初始化，不运行时调整
- **最小侵入**：所有修改点都是增量扩展，不替换现有逻辑

### 5.2 已知风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Room数据库升级失败 | AD-04 播放历史功能不可用 | 提供空Migration + 遵循database-migration-safety.md |
| IMAGE_SNIFF_JS追加MutationObserver影响性能 | 图片嗅探速度可能略降 | MutationObserver配置subtree+childList精确监听+防抖500ms |
| 首帧预加载深度增加流量 | GOOD档预加载3个分片增加流量 | 用户可配置关闭（player_firstframe_preload=false） |

### 5.3 验收标准

| ADR | 验收指标 | 测量方法 |
|-----|---------|---------|
| AD-01 | 首帧渲染时间 ≤2000ms | logcat onRenderedFirstFrame |
| AD-02 | 3G网络首帧时间降低30%+ | 弱网模拟测试 |
| AD-03 | 错误提示用户可读率100% | mock各类PlaybackException |
| AD-04 | 跨会话进度恢复100% | 退出后重开同一视频验证 |
| AD-05 | 大图加载0 OOM | 4K图片连续加载测试 |
| AD-06 | 嗅探成功率不低于当前水平 | 实施后真机验证嗅探成功率 |
