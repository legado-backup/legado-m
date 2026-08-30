# 播放器综合审查与遗漏点补全 - 功能规格

> 状态：🔄 设计中（2026-07-29 14:48 大幅简化版，用户反馈：别过度工程化+别影响现有功能+嗅探能力保护）
> 创建时间：2026-07-29
> 任务背景：在完成 18 个视频播放器 spec + 5 个图片播放器 spec 后，从用户使用角度与抓取嗅探播放速度角度对内置播放器进行整体审查，识别遗漏点并提出补全方案。
> 关联项目：video-buffer-speed-optimization（缓冲优化）、video-prebuffer-enhancement（预加载）、exoplayer-resilience（韧性）、image-sniffer-optimization（图片嗅探）、image-gallery-activity（图片画廊）、player-mature-solutions-alignment（行业方案对齐）
> 权威源：技术方案细节以 design.md 为权威源，本 spec 仅作需求意图与验证标准。本 spec 已对齐 design.md 2026-07-29 14:24 大幅简化版。

## Intent（意图）

### 设计意图

本项目已完成两轮深度优化（视频 18 个 spec、图片 5 个 spec），覆盖了缓冲速度、嗅探提取、错误处理、手势交互、UI 界面、画布渲染、线程安全等核心维度。但站在整体角度审视后，发现仍存在 10 个关键遗漏点，这些遗漏点分布在三个层面：

- **性能体验层**：首帧渲染慢（视频 4027ms）、大图加载潜在 OOM 风险（图片）
- **健壮性层**：智能缓冲策略缺失、网络错误恢复不完善、SPA 嗅探能力不足
- **用户感知层**：错误提示不友好、播放历史无法跨会话恢复、图片保存功能不完善

本次 spec 旨在系统性补齐上述遗漏点，使播放器在"快速、稳定、可控、可恢复"四个维度达到成熟播放器标准。

### 简化版总思路（2026-07-29 14:48 对齐 design.md）

> **用户铁律**（2026-07-29 14:24 反馈，最高约束）：
> 1. **别过度工程化**：不新增独立管理器/协调器，在现有组件上增量扩展
> 2. **别影响现有功能**：不修改嗅探主链路，不修改播放链路，仅扩展配置和UI
> 3. **嗅探能力保护**（AD-06，不可降级）：禁止修改 MimeSniffer.kt 和 ImageUrlExtractor.kt 核心嗅探逻辑，仅可扩展

本 spec 从原方案 23 文件变更（12 新增+11 修改）简化为 10 文件变更（3 新增+7 修改），减少 56%。所有补全点均通过"复用现有组件 + 增量扩展"实现，不新增独立管理器/协调器/监听器。

### 痛点证据

| 类别 | 症状 | 当前状态 | 用户影响 |
|------|------|---------|---------|
| 视频-首帧 | 首帧渲染耗时约 4027ms | FirstFramePreloader 已存在但预加载深度固定未分档位 | 用户点击后等待感强，误以为应用卡死 |
| 视频-缓冲 | 固定三档静态参数 | LoadControl 仅 prepare 前设置一次，首次播放 bitrateEstimate=0 无法感知网络类型 | 弱网下仍频繁卡顿，强网下过度缓冲浪费流量 |
| 视频-错误提示 | 仅 Toast "播放失败" | 无错误码分类、无操作建议 | 用户不知道失败原因及如何处理 |
| 视频-恢复 | 网络断开后无自动重连 | 仅依赖 exoplayer-resilience 的降级链 | 短暂网络抖动直接降级到 WebView，体验割裂 |
| 视频-进度 | 跨会话进度无持久化 | 仅 Activity 内部记录 | 重新打开需从头播放，无法续播 |
| 图片-内存 | 大图直接全分辨率解码 | Glide 默认策略未做采样保护 | 高分辨率图片可能触发 OOM 崩溃 |
| 图片-缓存 | 固定内存配额 | Glide MemoryCache 默认 | 低内存设备缓存过多导致系统压力 |
| 图片-嗅探 | Webpack SPA 场景失败 | image-sniffer-optimization 已设计但未覆盖复杂场景 | 部分站点图片列表为空 |
| 图片-信息 | 无元数据显示 | 仅显示图片本身 | 用户无法了解分辨率/大小/来源 |
| 图片-保存 | 仅单张保存 | 无批量保存 | 用户保存效率低 |

### 设计原则

1. **补全而非重构**：在已有架构上增量补全，不推翻已完成的优化
2. **复用已有基础设施**：FirstFramePreloader、ExoPlayerHelper、ImageUrlExtractor、ImageLoader 等已有组件优先复用，**不新增独立管理器/协调器**
3. **用户可感知优先**：所有补全点必须能转化为用户可感知的体验提升
4. **跨档位适配**：所有视频优化必须支持 WEAK/MEDIUM/GOOD 三档位差异化策略
5. **与已有 spec 边界清晰**：不与 video-buffer-speed-optimization、image-sniffer-optimization 等已实施项目重叠
6. **可观测性先行**：性能类补全点必须配套监控指标支撑验证

### 用户反馈强化原则（2026-07-29 14:15 + 14:24 用户审查反馈）

> **铁律**：以下原则由用户审查设计方案时明确提出，优先级高于其他设计原则。

7. **嗅探能力保护（最高约束，AD-06，Accepted 不可降级）**：所有新增组件**不得降低**现有视频/图片嗅探能力。嗅探是播放器核心链路，仅可加强不可削弱。任何影响嗅探主链路的设计必须被否决或降级。
   - 禁止修改 `MimeSniffer.kt` 和 `ImageUrlExtractor.kt` 的核心嗅探逻辑，仅可扩展
   - AD-01 首帧优化：仅扩展预加载参数，不并行化嗅探（嗅探保持串行主链路不变）
   - AD-06 SPA 嗅探增强：仅在现有 `IMAGE_SNIFF_JS` 常量**追加** MutationObserver 脚本，**不替换**原 5 路 Hook，嗅探超时保持 8 秒不变
   - 所有新增逻辑与嗅探链路解耦：嗅探失败不阻塞新增逻辑，新增逻辑失败不阻塞嗅探
8. **用户角度预缓存加载**：站在用户使用角度设计预缓存策略，提升用户感知加载速度
   - 视频列表浏览时：预缓存当前±1视频的首帧数据（复用 FirstFramePreloader）
   - 图片浏览时：预缓存下一张图片（Glide 预加载）
   - 预缓存范围可配置（关闭/1个/2个/3个）
9. **灵活配置（简化版，不新增 PlayerConfigManager）**：让用户可配置缓冲/预加载/缓存等参数
   - **在现有 SharedPreferences（AppConfig）增加配置项**，不新增 PlayerConfigManager 统一管理器
   - 配置入口：现有播放器设置页（PreferenceFragment），复用现有 UI 风格
   - 配置项（4 个）：
     - `player_buffer_strategy`：缓冲策略（自动/激进GOOD/平衡MEDIUM/保守WEAK，默认自动）
     - `player_precache_range`：预缓存范围（0关闭/1/2/3，默认1）
     - `player_history_enabled`：播放历史开关（true/false，默认true）
     - `player_firstframe_preload`：首帧预加载开关（true/false，默认true）
   - 用户手动选择优先于自动判断
10. **界面统一风格美观**：所有新增UI符合现有设计风格
    - 错误面板：MaterialAlertDialog（对齐项目现有错误弹窗风格）
    - 配置页面：PreferenceFragment（对齐项目现有设置页风格）
    - 禁止引入新UI框架，所有新增UI必须复用项目现有组件
11. **实用性优先**：避免过度工程，每个功能从实用性角度考虑
    - 高实用性(P0)：首帧加载/智能缓冲/错误提示/播放历史/大图内存（用户直接感知）
    - 中实用性(P1)：自动重连/智能缓存/SPA嗅探/批量保存（特定场景）
    - 低实用性(P2)：图片元数据显示（**已降级为 P2，本次暂不实施**，低实用性）
    - 评估原则：功能必须解决真实用户痛点，不为技术而技术

## Scope（范围）

### In Scope（本次实现，10 文件变更：3 新增+7 修改）

**视频播放器补全（5 项，5 文件：2 新增+3 修改）**：
1. 首帧加载速度优化（AD-01）：在现有 `FirstFramePreloader` 上扩展分档位预加载深度参数，目标 2000ms 以内
2. 智能缓冲策略（AD-02）：在现有 `ExoPlayerHelper.createLoadControlByTier` 中增加网络类型判断（首次播放 bitrateEstimate=0 时），不新增独立组件
3. 错误提示用户体验（AD-03）：新增 `ErrorMapper.kt`（纯UI），错误码→UserFacingError 映射
4. 网络错误恢复机制：在现有 `onPlayerError` 中增加简单重试逻辑（3 次指数退避），不新增 NetworkRecoveryManager
5. 播放历史记录完善（AD-04）：新增 `PlayHistory.kt`（Room 实体）+ `PlayHistoryStore.kt`（持久化 Helper），纯数据持久化

**图片播放器补全（4 项，4 文件：0 新增+4 修改）**：
1. 大图加载内存优化（AD-05）：在现有 `ImageLoader.kt` 中增加 `override()` 采样配置 + OOM 降级重试
2. 智能缓存策略：App 启动时根据设备档位设置一次 Glide 缓存大小（不运行时动态调整），不新增 AdaptiveCacheManager
3. SPA 场景嗅探增强（AD-06 约束下）：在现有 `IMAGE_SNIFF_JS` 常量**追加** MutationObserver 脚本（不替换原 5 路 Hook），嗅探超时保持 8 秒不变
4. 图片保存功能完善：在现有 `ImageGalleryActivity` 增加批量保存循环，不新增 BatchSaveManager

**数据层与资源（1 文件新增+1 文件修改）**：
- 新增 `PlayHistory.kt` Room 实体
- 修改 `ReadDatabase.kt`（新增实体到 @Database 列表，version+1，空 Migration）
- 修改 `strings.xml`（新增错误提示文案+播放历史文案）

### Out of Scope（本次不做）

- **图片元信息显示（R9，已降级为 P2）**：低实用性，本次暂不实施，未来评估
- **视频缓冲七层调优**：属于 `video-buffer-speed-optimization` 项目范畴，本 spec 仅引用其参数
- **下一个视频预加载**：属于 `video-prebuffer-enhancement` 项目范畴
- **WebView 降级链**：属于 `exoplayer-resilience` 项目范畴，本 spec 仅在网络重试失败后转交
- **图片嗅探基础架构**：属于 `image-sniffer-optimization` 项目范畴，本 spec 仅扩展 SPA 场景覆盖
- **图片画廊 Activity 基础功能**：属于 `image-gallery-activity` 项目范畴，本 spec 仅新增批量保存功能
- **播放器架构重写**：保留 ExoPlayer + GSY 双引擎架构
- **DRM 解密**：当前业务无 DRM 内容
- **视频格式嗅探**：属于 `exoplayer-resilience` 项目
- **自定义 HlsChunkSource**：已被 design.md AD-05 否决为 P2 评估
- **Cronet 集成**：属于 `video-buffer-speed-optimization` R17 评估范畴
- **视频字幕增强**：当前业务无字幕需求
- **图片编辑功能**：裁剪/标注/滤镜不在本次范围
- **云端进度同步**：跨设备进度同步不在本次范围，仅本地持久化
- **SAF 路径选择+格式转换**：批量保存仅复用现有单张保存路径，不引入 SAF 与格式转换（避免过度工程化）

## Approach（技术方案）

### Selected Approach：分层补全 + 复用已有组件 + 档位差异化（简化版）

选定**"分层补全 + 复用现有组件 + 档位差异化"**的组合方案，由以下三个策略组成。**核心原则：不新增独立管理器/协调器，所有补全点在现有组件上增量扩展。**

**策略一：视频层以"网络感知 + 持久化 + 用户提示"为补全主线**

视频播放器遗漏点的根因集中在三个层面：

- **感知层缺失**：当前缓冲策略固定档位，首次播放时 `bitrateEstimate=0` 无法感知网络类型。补全方案在现有 `createLoadControlByTier` 方法中增加网络类型判断（WiFi→GOOD/4G→MEDIUM/3G→WEAK），不新增 NetworkCapabilityMonitor 独立组件
- **持久化层缺失**：播放进度仅在 Activity 内部记录，无 Room 持久化。补全 `PlayHistory.kt`（Room 实体）+ `PlayHistoryStore.kt`（持久化 Helper），跨会话可恢复
- **用户感知层缺失**：错误提示仅 Toast 无分类。补全 `ErrorMapper.kt`（纯 UI）错误码映射 + 操作建议面板

**策略二：图片层以"内存安全 + 嗅探增强"为补全主线**

图片播放器遗漏点的根因集中在两个层面（元信息层已降级 P2 暂不实施）：

- **内存安全层缺失**：Glide 默认全分辨率解码大图。补全方案在现有 `ImageLoader.kt` 中增加 `override()` 采样配置 + OOM 降级重试，App 启动时根据设备档位设置一次 Glide 缓存大小（不运行时动态调整），不新增 BitmapSamplingLoader/MemoryPressureMonitor/AdaptiveCacheManager 独立组件
- **嗅探覆盖层缺失**：image-sniffer-optimization 已设计 5 路 Hook，但未覆盖 Webpack chunk 动态加载场景。补全方案在现有 `IMAGE_SNIFF_JS` 常量**追加** MutationObserver 脚本（不替换原 Hook），不新增 WebpackHookEnhancer 独立增强器，嗅探超时保持 8 秒不变

**策略三：所有补全点复用已有组件（不新增独立管理器）**

- 复用 `FirstFramePreloader`：扩展分档位预加载深度参数，不新增 ParallelSniffPreconnectCoordinator
- 复用 `ExoPlayerHelper.createLoadControlByTier`：增加网络类型判断，不新增 NetworkTypeDetector
- 复用 `VideoPlayerActivity.onPlayerError`：增加简单重试逻辑，不新增 NetworkRecoveryManager
- 复用 `ImageLoader`：增加 override() 采样配置 + OOM 降级重试，不新增 BitmapSamplingLoader
- 复用 `ImageUrlExtractor.IMAGE_SNIFF_JS`：追加 MutationObserver 脚本，不新增 WebpackHookEnhancer
- 复用 `ImageGalleryActivity`：增加批量保存循环，不新增 BatchSaveManager
- 复用 `AppConfig`/`SharedPreferences`：增加 4 个配置项，不新增 PlayerConfigManager
- 复用 `DeviceTier`：所有视频补全点支持三档位差异化
- 复用 `AppLog.put`：所有新增日志使用统一日志通道
- 复用 Room 数据库：新增 `PlayHistory` 实体复用已有 ReadDatabase 实例

### 方案分项（对齐 design.md 简化版）

#### 1. 视频首帧加载速度优化（AD-01，复用 FirstFramePreloader）

- 在现有 `FirstFramePreloader` 上扩展分档位预加载深度参数：
  - WEAK 档：不预加载首帧（节省流量）
  - MEDIUM 档：预加载 1 个分片
  - GOOD 档：预加载 3 个分片
- 预加载深度由 `PlayerConfig.player_firstframe_preload` 配置项控制
- **不新增协调器，不并行化嗅探**（嗅探保持串行主链路不变，AD-06 约束）
- 目标：首帧渲染时间从 4027ms 降至 2000ms 以内（通过预加载深度优化，不通过并行化）
- 监控：通过 AnalyticsListener.onRenderedFirstFrame 记录首帧耗时

#### 2. 视频智能缓冲策略（AD-02，复用 createLoadControlByTier）

- 在现有 `ExoPlayerHelper.createLoadControlByTier` 方法中增加网络类型判断：
  - 首次播放（`bitrateEstimate=0`）时通过 `ConnectivityManager.getActiveNetworkInfo` 检测网络类型
  - WiFi→GOOD / 4G→MEDIUM / 3G→WEAK
  - 带宽测量生效后（`bitrateEstimate>0`）以带宽为主
- 用户可通过配置项 `player_buffer_strategy` 手动覆盖
- **不新增 NetworkCapabilityMonitor 独立组件**，仅在方法内部增加几行判断代码
- 档位变化通过下次播放生效（路径 A，不热切换，与 design.md AD-01 一致）

#### 3. 视频错误提示用户体验（AD-03，新增 ErrorMapper.kt 纯UI）

- 新增 `ErrorMapper.kt`（放置 `app/src/main/java/io/legado/app/help/player/`）：建立错误码→`UserFacingError` 映射表
- 错误分类（6 类）：
  - ERROR_CODE_IO_NETWORK_CONNECTION_FAILED → 网络错误
  - ERROR_CODE_IO_DNS_FAILED → DNS 错误
  - ERROR_CODE_DECODER_INIT_FAILED → 解码错误
  - ERROR_CODE_DRM_UNSUPPORTED → DRM 错误
  - ERROR_CODE_IO_INVALID_HTTP_CONTENT_TYPE → 源无效
  - 其他 → 未知错误
- 每类错误配套友好文案 + 操作建议：
  - 网络错误：提示"网络连接失败，请检查网络后重试" + [重试] [切换源]
  - DNS 错误：提示"域名解析失败，可能被劫持" + [切换源] [反馈]
  - 解码错误：提示"视频格式不支持解码" + [切换源] [反馈]
  - DRM 错误：提示"受版权保护内容，无法播放" + [关闭]
  - 源无效：提示"视频源已失效" + [切换源] [反馈]
  - 未知错误：提示"播放失败，请重试或反馈" + [重试] [反馈]
- `VideoPlayerActivity.onPlayerError` 回调中调用 `ErrorMapper.map(error)`，用 MaterialAlertDialog 展示
- **纯 UI 增强，不涉及嗅探/播放链路**

#### 4. 视频网络错误恢复机制（复用 onPlayerError，不新增 NetworkRecoveryManager）

- 在现有 `VideoPlayerActivity.onPlayerError` 中增加简单重试逻辑：
  - 网络相关错误（IO_NETWORK_CONNECTION_FAILED/IO_DNS_FAILED）自动重试
  - 最多 3 次，间隔 2/4/6 秒指数退避
  - 重试成功后 `seekTo` 上次位置恢复播放
  - 3 次重连失败后转交 exoplayer-resilience 降级链（WebView 降级）
- **不新增 NetworkRecoveryManager 独立管理器**，仅扩展错误处理回调
- 与 R5 播放历史联动：重连失败时仍保存进度

#### 5. 视频播放历史记录完善（AD-04，新增 PlayHistory.kt + PlayHistoryStore.kt 纯数据）

- 新增 `PlayHistory.kt`（Room 实体）：字段包含 url（主键）/progress/duration/lastPlayTime/sourceType
- 新增 `PlayHistoryStore.kt`（持久化 Helper）：save/load/cleanOldRecords（保留 30 天）
- `VideoPlayerActivity.onResume` 启动定时保存（每 10s）调用 `PlayHistoryStore.save(url, position, duration)`
- `onPause` 保存最后一次并取消定时
- `initSource` 中 ExoPlayer prepare 完成后调用 `PlayHistoryStore.load(url)`，若 position>10s 则 seekTo + Toast 提示"已从 XX:XX 继续播放"
- 数据库升级：新增表，version+1，提供空 Migration（遵循 database-migration-safety.md）
- **纯数据持久化，不涉及嗅探/播放链路**

#### 6. 图片大图加载内存优化（AD-05，复用 ImageLoader）

- 在现有 `ImageLoader.kt` 中为图片加载请求添加 `override()` 采样：
  - 根据 ImageView 尺寸计算目标分辨率
  - 极高分辨率图片（>4096px）强制降级到 2048px
- 在 Glide RequestListener.onLoadFailed 中捕获 OutOfMemoryError，降级到更低分辨率重试
- **不新增 BitmapSamplingLoader 独立加载器**，仅在现有 ImageLoader 中增加几行配置代码

#### 7. 图片智能缓存策略（复用 Glide 初始化，不新增 AdaptiveCacheManager）

- App 启动时根据设备档位设置一次 Glide 缓存大小（**不运行时动态调整**）：
  - HIGH 档设备：MemoryCache 96MB
  - MID 档设备：MemoryCache 48MB
  - LOW 档设备：MemoryCache 24MB
- 在 `App.onCreate` 通过 GlideModule 初始化
- **不新增 AdaptiveCacheManager 运行时动态调整组件**，避免缓存抖动
- 磁盘缓存保留默认 250MB InternalCache，不调整

#### 8. 图片 SPA 场景嗅探增强（AD-06 约束下，在 IMAGE_SNIFF_JS 追加脚本）

- 在 `ImageUrlExtractor` 的 `IMAGE_SNIFF_JS` 常量**追加** MutationObserver 脚本：
  - 监听 `document.body` 子树变化，新增 `<img>` 节点时提取 src
  - 配置 subtree+childList 精确监听 + 防抖 500ms
- **不替换**原 5 路 Hook，仅追加
- **嗅探超时保持 8 秒不变**（不延长至 15 秒，避免影响现有行为）
- **不新增 WebpackHookEnhancer 独立增强器**，不新增 fetch/XHR 拦截，不新增 webpackChunk 事件监听
- 与 image-sniffer-optimization 边界：本 spec 仅扩展 SPA 场景，不修改基础嗅探架构
- 嗅探完成后移除 MutationObserver 监听（避免内存泄漏）

#### 9. 图片信息显示（已降级为 P2，本次暂不实施）

- **降级理由**：低实用性，用户痛点不强烈，避免过度工程化
- **未来评估**：若用户反馈强烈，再在 P2 阶段实施
- 本次不新增 ImageGalleryActivity 长按手势、不新增 Glide RequestListener 元信息提取、不新增 BottomSheetDialog 元信息面板

#### 10. 图片保存功能完善（复用 ImageGalleryActivity，不新增 BatchSaveManager）

- 在现有 `ImageGalleryActivity` 增加批量保存循环：
  - 长按进入选择模式 → 多选 → 批量保存
  - 复用现有单张保存逻辑，循环调用
  - 保存进度通过 NotificationCompat 显示（"批量保存 X/Y"）
- **不新增 BatchSaveManager 独立管理器**，仅在 UI 层循环调用
- **不引入 SAF 路径选择**（避免过度工程化），保存到现有默认路径
- **不引入格式转换**（避免过度工程化），保留原始格式
- 与 I4（已降级 P2）联动取消

### Alternatives Considered（否决的替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| **原方案新增独立管理器（已否决，过度工程化）** | 新增 PlayerConfigManager/NetworkCapabilityMonitor/NetworkRecoveryManager/BitmapSamplingLoader/MemoryPressureMonitor/AdaptiveCacheManager/WebpackHookEnhancer/BatchSaveManager 等 8+ 个独立组件 | **已否决**（2026-07-29 14:24 用户反馈"别过度工程化"）。过度工程化，增加维护成本，且多个独立组件可能影响嗅探主链路。简化方案在现有组件上增量扩展，变更文件从 23 降到 10 |
| V1-Alt1：完全自定义首帧预加载链路 | 重写 FirstFramePreloader，自实现分片预加载 | 已有 FirstFramePreloader 组件，重写违反"复用已有组件"原则。本次仅扩展分档位策略 |
| V1-Alt2：首帧并行化嗅探 | 新增 ParallelSniffPreconnectCoordinator 4 路并行 | **已否决**（AD-06 嗅探保护）。并行化嗅探可能影响嗅探主链路稳定性。本次保持嗅探串行，仅优化预加载深度 |
| V2-Alt1：LoadControl 运行时热切换 | 实现 AdaptiveLoadControl 根据实时带宽动态调整 | **已否决**（design.md AD-01 + video-buffer-speed-optimization R10）。触发 re-prepare 中断 1-3s。本 spec 沿用路径 A，档位变化通过下次播放生效 |
| V2-Alt2：新增 NetworkCapabilityMonitor 独立组件 | 注册 ConnectivityManager.NetworkCallback 持续监听 | **已否决**（过度工程化）。简化方案在 createLoadControlByTier 方法内部增加网络类型判断即可，无需独立组件 |
| V3-Alt1：错误提示仅 Toast | 保持现状，仅优化 Toast 文案 | Toast 信息密度低，无法承载操作建议。必须用 Dialog 提供操作按钮 |
| V3-Alt2：自定义错误界面 Activity | 新增 ErrorActivity 全屏展示错误 | 过度工程，MaterialAlertDialog 已足够。本次不引入新 Activity |
| V4-Alt1：新增 NetworkRecoveryManager 独立管理器 | 与 NetworkCapabilityMonitor 共享 NetworkCallback | **已否决**（过度工程化）。简化方案在 onPlayerError 中增加简单重试逻辑即可 |
| V4-Alt2：网络断开立即降级 WebView | 不重连，直接转交 exoplayer-resilience | 短暂网络抖动直接降级 WebView 体验割裂。本次先重连 3 次再降级 |
| V5-Alt1：使用 SharedPreferences 存进度 | 用 SharedPreferences 存储播放进度 | 进度数据结构化（url+progress+duration+time），SharedPreferences 不适合结构化查询。使用 Room |
| V5-Alt2：云端进度同步 | 跨设备同步播放进度 | 本次仅本地持久化，云端同步不在 Scope。降级为未来 P2 评估 |
| I1-Alt1：新增 BitmapSamplingLoader 独立加载器 | 自实现 BitmapFactory 解码 | **已否决**（过度工程化）。简化方案在现有 ImageLoader 中增加 override() 采样配置即可 |
| I1-Alt2：新增 MemoryPressureMonitor 独立组件 | 实现 ComponentCallbacks2.onTrimMemory 监听 | **已否决**（过度工程化）。简化方案仅在 Glide RequestListener.onLoadFailed 中捕获 OOM 降级重试 |
| I1-Alt3：禁止加载超大图片 | >4096px 图片直接拒绝加载 | 用户体验差，应降级而非拒绝。本次降级到 2048px 解码 |
| I2-Alt1：新增 AdaptiveCacheManager 运行时动态调整 | 根据 availableMemory 动态调整 Glide MemoryCache 配额 | **已否决**（过度工程化+缓存抖动风险）。简化方案在 App 启动时根据设备档位设置一次，不运行时调整 |
| I2-Alt2：完全禁用 MemoryCache | 仅用磁盘缓存 | 内存缓存命中率影响滚动流畅度，禁用会导致列表滚动卡顿。本次按档位静态配置而非禁用 |
| I3-Alt1：完全重写图片嗅探引擎 | 弃用 ImageUrlExtractor，自实现嗅探 | image-sniffer-optimization 已设计基础架构，本次仅扩展 SPA 场景覆盖 |
| I3-Alt2：新增 fetch/XHR 拦截+webpackChunk 事件监听 | 拦截 fetch/XHR 响应捕获 Base64/JSON 图片 | **已否决**（过度工程化+AD-06 嗅探保护）。简化方案仅追加 MutationObserver 脚本，不替换原 5 路 Hook |
| I3-Alt3：嗅探超时延长至 15 秒 | SPA 场景首屏渲染较慢，延长超时 | **已否决**（避免影响现有行为）。嗅探超时保持 8 秒不变 |
| I4-Alt1：实施图片元信息显示 | 长按显示元信息面板 | **已降级为 P2**（低实用性）。本次暂不实施，未来评估 |
| I5-Alt1：新增 BatchSaveManager 独立管理器 | 独立管理批量保存流程 | **已否决**（过度工程化）。简化方案在现有 ImageGalleryActivity 增加批量保存循环即可 |
| I5-Alt2：引入 SAF 路径选择+格式转换 | 用 SAF 让用户选择目录，支持 WEBP/JPEG/PNG 转换 | **已否决**（过度工程化）。本次复用现有单张保存路径，不引入 SAF 与格式转换 |
| 通用-Alt1：合并所有补全点到现有 spec | 不新建 spec，直接修改已有 spec | 已有 18+5 个 spec 已实施完成，修改已完成 spec 破坏历史可追溯性。本次独立新建 spec |

### Drawbacks（简化方案的缺点）

1. **首帧优化收益受限**：不并行化嗅探意味着无法消除嗅探 3s 等待，首帧优化仅通过预加载深度调整实现，收益小于并行化方案。**接受理由**：保证了嗅探主链路稳定性（用户铁律 AD-06），风险极低
2. **网络类型检测仅在 prepare 前生效**：不持续监听 NetworkCallback，网络切换需下次播放才生效。**接受理由**：路径 A 决策避免热切换 re-prepare 中断，符合 design.md AD-01
3. **错误分类面板打断播放流程**：Dialog 会打断用户观看。**接受理由**：仅在播放失败时弹出，正常播放不受影响；用户可选择重试快速恢复
4. **网络重连可能延迟降级**：3 次指数退避重连最长 12 秒才降级 WebView。**接受理由**：用户可手动点击"切换源"立即降级，无需等待自动重连完成
5. **PlaybackHistory 增加数据库体积**：每 10 秒保存一次进度会增加数据库写入。**接受理由**：单条记录 <100 字节，30 天清理策略保证体积可控（<1MB）
6. **图片采样可能影响清晰度**：override() 采样会降低图片清晰度。**接受理由**：采样仅在 ImageView 尺寸小于原始分辨率时生效，全屏查看时通过 Glide thumbnail 替换为全分辨率
7. **Glide 缓存静态配置不动态调整**：App 启动时设置一次，运行时内存压力变化不调整。**接受理由**：避免运行时动态调整导致缓存抖动，静态配置已覆盖绝大多数场景
8. **IMAGE_SNIFF_JS 追加 MutationObserver 可能影响性能**：MutationObserver 监听 DOM 变化会增加 JS 执行开销。**接受理由**：配置 subtree+childList 精确监听 + 防抖 500ms，性能开销可控；嗅探完成后移除监听
9. **批量保存不提供路径选择**：用户无法选择保存目录。**接受理由**：避免引入 SAF 增加操作步骤，复用现有默认路径满足基本需求
10. **图片元信息功能缺失**：本次不实施 R9。**接受理由**：低实用性，用户痛点不强烈，避免过度工程化；未来 P2 阶段评估

### Prior Art（参考）

- ExoPlayer Media3 官方文档：AnalyticsListener、LoadControl、ConnectivityManager 集成
- Glide 官方文档：override() 采样、MemoryCache 配额配置、RequestListener、OOM 降级
- Android 官方文档：ConnectivityManager.getActiveNetworkInfo、GlideModule 初始化
- 项目内 `FirstFramePreloader.kt`（首帧预加载基础，AD-01 复用）
- 项目内 `ExoPlayerHelper.kt`（LoadControl 与 createLoadControlByTier，AD-02 复用）
- 项目内 `MimeSniffer.kt`（MIME 嗅探基础，AD-06 禁止修改）
- 项目内 `ImageUrlExtractor.kt`（图片 URL 提取基础，AD-06 仅扩展 IMAGE_SNIFF_JS）
- 项目内 `ImageLoader.kt`（Glide 图片加载封装，AD-05 复用）
- 项目内 `ImageGalleryActivity.kt`（图片画廊基础，批量保存复用）
- 项目内 `ReadDatabase.kt`（Room 数据库，AD-04 新增实体）
- 项目内 `exoplayer-resilience` 项目（韧性降级链基础，重连失败转交）
- 项目内 `video-buffer-speed-optimization` 项目（缓冲七层调优）
- 项目内 `video-prebuffer-enhancement` 项目（预加载边界，AD-09 路径 A 决策）
- 项目内 `image-sniffer-optimization` 项目（图片嗅探基础架构）
- 项目内 `image-gallery-activity` 项目（图片画廊基础功能）
- 项目内 `player-mature-solutions-alignment` 项目（行业成熟方案对齐）
- Room 官方文档：Entity 设计、Migration、DAO 查询
- Material Design 官方文档：MaterialAlertDialog、PreferenceFragment

## Requirements（需求）

### R1：视频首帧加载速度必须优化至 2000ms 以内（AD-01，复用 FirstFramePreloader）

- **R1.1** 在现有 `FirstFramePreloader` 上扩展分档位预加载深度参数（不新增协调器）：
  - WEAK 档：不预加载首帧（节省流量）
  - MEDIUM 档：预加载 1 个分片
  - GOOD 档：预加载 3 个分片
- **R1.2** 预加载深度由 `player_firstframe_preload` 配置项控制（true 时按档位预加载，false 时全部不预加载）
- **R1.3** 通过 AnalyticsListener.onRenderedFirstFrame 记录首帧耗时（依赖 video-buffer-speed-optimization R7）
- **R1.4** 嗅探主链路（`ExoPlayerHelper.sniffVideoType`）保持不变，**不并行化嗅探**（AD-06 约束）
- **R1.5** 验证标准：GOOD 档 WiFi 网络首帧 < 2000ms，WEAK 档 3G 网络首帧 < 3000ms
- **R1.6** 验证方法：logcat 过滤 "ExoAnalytics" Tag 的 onRenderedFirstFrame 输出

### R2：视频智能缓冲策略必须根据网络类型选择档位（AD-02，复用 createLoadControlByTier）

- **R2.1** 在现有 `ExoPlayerHelper.createLoadControlByTier` 方法中增加网络类型判断（不新增 NetworkCapabilityMonitor）：
  - 首次播放（`bitrateEstimate=0`）时通过 `ConnectivityManager.getActiveNetworkInfo` 检测网络类型
  - WiFi→GOOD / 4G→MEDIUM / 3G→WEAK
- **R2.2** 带宽测量生效后（`bitrateEstimate>0`）以带宽为主，网络类型仅作首次播放兜底
- **R2.3** 档位变化通过下次播放生效（路径 A，与 design.md AD-01 一致，不热切换）
- **R2.4** 用户可通过配置项 `player_buffer_strategy` 手动覆盖（自动/激进GOOD/平衡MEDIUM/保守WEAK，默认自动）
- **R2.5** 用户手动选择优先于自动判断
- **R2.6** 验证方法：切换 WiFi/4G/3G 网络，logcat 确认首次播放档位变化 + 下次播放参数生效

### R3：视频错误提示必须分类显示并提供操作建议（AD-03，新增 ErrorMapper.kt 纯UI）

- **R3.1** 新增 `ErrorMapper.kt`（放置 `app/src/main/java/io/legado/app/help/player/`）：将 ExoPlayer PlaybackException 分类为 6 类
  - ERROR_CODE_IO_NETWORK_CONNECTION_FAILED → 网络错误
  - ERROR_CODE_IO_DNS_FAILED → DNS 错误
  - ERROR_CODE_DECODER_INIT_FAILED → 解码错误
  - ERROR_CODE_DRM_UNSUPPORTED → DRM 错误
  - ERROR_CODE_IO_INVALID_HTTP_CONTENT_TYPE → 源无效
  - 其他 → 未知错误
- **R3.2** 每类错误配套友好文案（不暴露技术术语，如不显示 ERROR_CODE_xxx）
- **R3.3** 每类错误配套操作建议按钮：
  - 网络错误：[重试] [切换源]
  - DNS 错误：[切换源] [反馈]
  - 解码错误：[切换源] [反馈]
  - DRM 错误：[关闭]
  - 源无效：[切换源] [反馈]
  - 未知错误：[重试] [反馈]
- **R3.4** `VideoPlayerActivity.onPlayerError` 回调中调用 `ErrorMapper.map(error)` 获取 `UserFacingError(title, message, actions)`
- **R3.5** 错误面板使用 MaterialAlertDialog（项目已有依赖）
- **R3.6** 错误日志通过 `AppLog.put("PlayerError", ...)` 记录，包含错误码与分类
- **R3.7** 纯 UI 增强，不涉及嗅探/播放链路
- **R3.8** 验证方法：mock 各类 PlaybackException，确认对应错误面板与操作按钮

### R4：视频网络错误必须自动重连并恢复进度（复用 onPlayerError，不新增 NetworkRecoveryManager）

- **R4.1** 在现有 `VideoPlayerActivity.onPlayerError` 中增加简单重试逻辑（不新增 NetworkRecoveryManager）：
  - 网络相关错误（IO_NETWORK_CONNECTION_FAILED/IO_DNS_FAILED）自动重试
  - 最多 3 次，间隔 2/4/6 秒指数退避
- **R4.2** 重连成功后 `seekTo` 上次位置恢复播放
- **R4.3** 3 次重连失败后转交 exoplayer-resilience 降级链（WebView 降级）
- **R4.4** 重连过程中显示进度提示（"正在重连...第 X 次"）
- **R4.5** 与 R5 联动：网络恢复后即使重连失败也保存进度
- **R4.6** 验证方法：播放中关闭 WiFi/移动数据，确认自动重连 + 进度恢复

### R5：视频播放进度必须跨会话持久化（AD-04，新增 PlayHistory.kt + PlayHistoryStore.kt 纯数据）

- **R5.1** 新增 `PlayHistory.kt`（Room 实体）：字段包含 url（主键）/progress/duration/lastPlayTime/sourceType
- **R5.2** 新增 `PlayHistoryStore.kt`（持久化 Helper）：save/load/cleanOldRecords（保留 30 天）
- **R5.3** `VideoPlayerActivity.onResume` 启动定时保存（每 10s）调用 `PlayHistoryStore.save(url, position, duration)`
- **R5.4** `onPause` 保存最后一次并取消定时
- **R5.5** `initSource` 中 ExoPlayer prepare 完成后调用 `PlayHistoryStore.load(url)`，若 position>10s 则 seekTo + Toast 提示"已从 XX:XX 继续播放"
- **R5.6** 数据库升级：新增表，version+1，提供空 Migration（遵循 database-migration-safety.md）
- **R5.7** `cleanOldRecords` 在 App 启动时执行，清理 30 天前的记录
- **R5.8** 纯数据持久化，不涉及嗅探/播放链路
- **R5.9** 验证方法：播放视频 30 秒后退出 App，重新打开确认续播提示

### R6：图片大图加载必须采样解码并防 OOM（AD-05，复用 ImageLoader）

- **R6.1** 在现有 `ImageLoader.kt` 中为图片加载请求添加 `override()`：根据 ImageView 尺寸计算目标分辨率（不新增 BitmapSamplingLoader）
- **R6.2** 极高分辨率图片（>4096px）强制降级到 2048px 解码
- **R6.3** 在 Glide RequestListener.onLoadFailed 中捕获 OutOfMemoryError，降级到更低分辨率重试（不新增 MemoryPressureMonitor）
- **R6.4** 验证方法：加载 8000px 以上大图，确认无 OOM 崩溃 + 日志显示采样分辨率

### R7：图片智能缓存策略必须在 App 启动时按档位静态配置（不新增 AdaptiveCacheManager）

- **R7.1** App 启动时根据设备档位设置一次 Glide MemoryCache 大小（**不运行时动态调整**）：
  - HIGH 档设备：96MB
  - MID 档设备：48MB
  - LOW 档设备：24MB
- **R7.2** 在 `App.onCreate` 通过 GlideModule 初始化
- **R7.3** **不新增 AdaptiveCacheManager 运行时动态调整组件**，避免缓存抖动
- **R7.4** 磁盘缓存保留默认 250MB InternalCache，不调整
- **R7.5** 验证方法：在不同档位设备测试，确认 MemoryCache 配额正确 + 滚动流畅

### R8：图片 SPA 场景嗅探必须在 IMAGE_SNIFF_JS 追加 MutationObserver（AD-06 约束）

- **R8.1** 在 `ImageUrlExtractor` 的 `IMAGE_SNIFF_JS` 常量**追加** MutationObserver 脚本（不新增 WebpackHookEnhancer）
- **R8.2** MutationObserver 配置：监听 `document.body` 子树变化，新增 `<img>` 节点时提取 src，subtree+childList 精确监听 + 防抖 500ms
- **R8.3** **不替换**原 5 路 Hook，仅追加
- **R8.4** **嗅探超时保持 8 秒不变**（不延长至 15 秒，避免影响现有行为）
- **R8.5** **不新增** fetch/XHR 拦截，**不新增** webpackChunk 事件监听（避免过度工程化）
- **R8.6** 嗅探完成后移除 MutationObserver 监听（避免内存泄漏）
- **R8.7** 与 image-sniffer-optimization 边界：本 spec 仅扩展 SPA 场景，不修改基础嗅探架构
- **R8.8** AD-06 约束：禁止修改 `MimeSniffer.kt` 和 `ImageUrlExtractor.kt` 核心嗅探逻辑，仅可扩展 `IMAGE_SNIFF_JS` 常量
- **R8.9** 验证方法：在 Webpack SPA 站点测试，确认图片列表非空 + 日志显示 MutationObserver 嗅探来源

### R9：图片元信息显示（已降级为 P2，本次暂不实施）

- **R9.1** **降级理由**：低实用性，用户痛点不强烈，避免过度工程化
- **R9.2** **本次不实施**：不新增 ImageGalleryActivity 长按手势、不新增 Glide RequestListener 元信息提取、不新增 BottomSheetDialog 元信息面板
- **R9.3** **未来评估**：若用户反馈强烈，再在 P2 阶段实施
- **R9.4** 验证方法：N/A（本次不实施）

### R10：图片必须支持批量保存（复用 ImageGalleryActivity，不新增 BatchSaveManager）

- **R10.1** 在现有 `ImageGalleryActivity` 增加批量保存循环（不新增 BatchSaveManager）：
  - 长按进入选择模式 → 多选图片
  - 复用现有单张保存逻辑，循环调用
- **R10.2** 批量保存使用 Coroutine.async 后台执行（遵循项目协程规范）
- **R10.3** 保存进度通过 NotificationCompat 显示（标题"批量保存"+ 进度条 + 当前/总数）
- **R10.4** 保存完成通知点击跳转到保存目录
- **R10.5** 保存失败时通知显示失败原因 + 失败列表
- **R10.6** **不引入 SAF 路径选择**（避免过度工程化），保存到现有默认路径
- **R10.7** **不引入格式转换**（避免过度工程化），保留原始格式
- **R10.8** 验证方法：批量选择 5+ 张图片保存到默认目录，确认全部成功 + 通知显示进度

### R11：必须清理调试日志

- **R11.1** 实施完成后 Grep "android.util.Log.d|android.util.Log.e" 确认无残留
- **R11.2** 所有新增日志使用 `AppLog.put(tag, msg)` 而非 `Log.x`
- **R11.3** 验证方法：grep "android.util.Log" 在新增文件中无匹配

### R12：必须同步更新 updateLog.md

- **R12.1** 在 `assets/updateLog.md` 顶部新增条目：播放器综合审查与遗漏点补全
- **R12.2** 用通俗语言描述用户可感知变化（如"视频首帧加载更快"、"弱网自动调整缓冲"、"图片加载更稳定不崩溃"）
- **R12.3** 不暴露内部技术术语（如 LoadControl、MutationObserver、ErrorMapper）
- **R12.4** 验证方法：读取 `assets/updateLog.md` 顶部确认新增条目存在

## Scenarios（场景）

### Scenario 1：好网首帧快速加载（视频正常场景，AD-01）

**前置条件**：deviceTier=GOOD，网络 WiFi 100Mbps，HLS 点播视频 1080P，`player_firstframe_preload=true`

**预期行为**：
1. 用户点击视频，FirstFramePreloader 根据 GOOD 档预加载 3 个分片
2. 嗅探主链路保持串行不变（AD-06 约束，不并行化）
3. 首帧渲染 < 2000ms（从 4027ms 降至 2000ms 以内，通过预加载深度优化）
4. AnalyticsListener.onRenderedFirstFrame 记录首帧耗时
5. 用户感知：点击后立即开始播放，无等待感

**验证方法**：logcat 过滤 "ExoAnalytics" 的 onRenderedFirstFrame 输出，确认首帧 < 2000ms

### Scenario 2：弱网首帧降级加载（视频异常场景，AD-01）

**前置条件**：deviceTier=WEAK，网络 3G 1Mbps，HLS 点播视频，`player_firstframe_preload=true`

**预期行为**：
1. FirstFramePreloader 根据 WEAK 档不预加载首帧（节省流量）
2. 首帧渲染 < 3000ms（弱网放宽阈值）
3. 用户感知：稍有等待但可接受

**验证方法**：logcat 确认 WEAK 档未预加载 + 首帧 < 3000ms

### Scenario 3：首次播放根据网络类型选择档位（视频网络感知场景，AD-02）

**前置条件**：deviceTier=GOOD，首次播放（bitrateEstimate=0），网络 4G

**预期行为**：
1. `ExoPlayerHelper.createLoadControlByTier` 调用前检测网络类型（不新增独立组件）
2. `ConnectivityManager.getActiveNetworkInfo` 检测到 4G
3. 档位映射：4G→MEDIUM
4. LoadControl 参数使用 MEDIUM 档（minBuffer 8s/maxBuffer 90s）
5. 带宽测量生效后（bitrateEstimate>0）以带宽为主
6. 用户感知：弱网下首帧前即选择合理缓冲档位，减少卡顿

**验证方法**：首次播放时 logcat 确认网络类型检测日志 + MEDIUM 档参数生效

### Scenario 4：播放失败显示分类错误面板（视频异常场景，AD-03）

**前置条件**：deviceTier=GOOD，视频源 DNS 解析失败

**预期行为**：
1. ExoPlayer 抛出 PlaybackException（ERROR_CODE_IO_DNS_FAILED）
2. `VideoPlayerActivity.onPlayerError` 调用 `ErrorMapper.map(error)`
3. ErrorMapper 分类为"DNS 错误"，返回 `UserFacingError`
4. 显示 MaterialAlertDialog：
   - 标题："播放失败"
   - 内容："域名解析失败，可能被劫持"
   - 按钮：[切换源] [反馈]
5. 用户点击"切换源"切换到下一个源
6. 错误日志通过 AppLog.put 记录，包含错误码与分类

**验证方法**：mock DNS 失败，确认错误面板显示正确文案与按钮

### Scenario 5：网络错误自动重连恢复进度（视频异常场景，R4）

**前置条件**：deviceTier=GOOD，播放中网络断开 5 秒后恢复

**预期行为**：
1. `onPlayerError` 检测到网络相关错误（IO_NETWORK_CONNECTION_FAILED）
2. 暂停播放 + 记录当前位置（如 05:30）
3. 显示"正在重连...第 1 次"提示
4. 间隔 2 秒后自动重连
5. 重连成功后 seekTo(05:30) 恢复播放
6. 用户感知：短暂暂停后继续播放，无需手动操作

**验证方法**：播放中关闭 WiFi 5 秒后重新打开，确认自动重连 + 进度恢复

### Scenario 6：网络错误重连失败降级 WebView（视频异常场景，R4）

**前置条件**：deviceTier=GOOD，播放中网络断开 30 秒以上

**预期行为**：
1. `onPlayerError` 检测到网络相关错误
2. 暂停播放 + 记录当前位置
3. 自动重连 3 次（间隔 2/4/6 秒），均失败
4. 转交 exoplayer-resilience 降级链
5. 用户感知：自动切换到 WebView 播放
6. 进度保存到 PlayHistory（即使重连失败）

**验证方法**：播放中关闭网络 30 秒以上，确认 3 次重连后降级 WebView + 进度已保存

### Scenario 7：跨会话续播（视频正常场景，AD-04）

**前置条件**：deviceTier=GOOD，用户上次播放视频到 10:30 后退出 App

**预期行为**：
1. 用户重新打开 App，点击同一视频
2. `VideoPlayerActivity.initSource` 中 ExoPlayer prepare 完成后调用 `PlayHistoryStore.load(url)`
3. 发现历史记录（progress=10:30，> 10 秒）
4. seekTo(10:30) + Toast 提示"已从 10:30 继续播放"
5. 用户感知：无需从头播放，可从上次位置继续

**验证方法**：播放视频 30 秒后退出 App，重新打开确认续播提示

### Scenario 8：大图加载 OOM 防护（图片异常场景，AD-05）

**前置条件**：deviceTier=MEDIUM，加载 8000px x 6000px 大图

**预期行为**：
1. `ImageLoader` 检测到 ImageView 尺寸 < 8000px
2. 调用 `override()` 采样到目标分辨率（如 1920x1080）
3. 极高分辨率图片（>4096px）强制降级到 2048px
4. Glide 解码采样后分辨率，内存占用 < 50MB
5. 若发生 OOM，RequestListener.onLoadFailed 捕获 OutOfMemoryError，降级到更低分辨率重试
6. 用户感知：图片正常显示，无 OOM 崩溃

**验证方法**：加载 8000px 以上大图，确认无 OOM 崩溃 + 日志显示采样分辨率

### Scenario 9：App 启动按档位静态配置 Glide 缓存（图片缓存场景，R7）

**前置条件**：deviceTier=MID（中档设备）

**预期行为**：
1. App.onCreate 时 GlideModule 初始化
2. 根据设备档位设置 MemoryCache 大小：MID 档 → 48MB
3. **不运行时动态调整**（避免缓存抖动）
4. 磁盘缓存保留默认 250MB InternalCache
5. 用户感知：滚动流畅，无因缓存配额不当导致的卡顿

**验证方法**：在 MID 档设备测试，确认 MemoryCache 配额为 48MB + 滚动流畅

### Scenario 10：Webpack SPA 站点图片嗅探（图片正常场景，AD-06 约束）

**前置条件**：deviceTier=GOOD，访问 Webpack SPA 站点

**预期行为**：
1. `ImageUrlExtractor` 注入 `IMAGE_SNIFF_JS`（原 5 路 Hook + 追加的 MutationObserver）
2. MutationObserver 监听 `document.body` 子树变化，新增 `<img>` 节点时提取 src
3. 配置 subtree+childList 精确监听 + 防抖 500ms
4. **不替换**原 5 路 Hook，仅追加
5. **嗅探超时保持 8 秒不变**（不延长至 15 秒）
6. 嗅探完成后移除 MutationObserver 监听
7. 用户感知：图片列表非空，可正常浏览

**验证方法**：在 Webpack SPA 站点测试，确认图片列表非空 + 日志显示 MutationObserver 嗅探来源

### Scenario 11：批量保存图片到默认目录（图片正常场景，R10）

**前置条件**：deviceTier=GOOD，浏览图片画廊，用户选择 5 张图片

**预期行为**：
1. 用户长按进入选择模式
2. 选择 5 张图片
3. 点击"保存"按钮
4. `ImageGalleryActivity` 循环调用现有单张保存逻辑（不新增 BatchSaveManager）
5. 后台 Coroutine.async 执行批量保存
6. NotificationCompat 显示进度（"批量保存 3/5"）
7. 保存完成通知点击跳转到保存目录
8. **不弹出 SAF 路径选择**（保存到现有默认路径）
9. **不弹出格式转换选择**（保留原始格式）
10. 用户感知：5 张图片全部保存到默认目录

**验证方法**：批量选择 5 张图片保存，确认全部成功 + 通知显示进度

### Scenario 12：用户手动覆盖网络自动档位（视频正常场景，R2）

**前置条件**：deviceTier=GOOD，网络 4G（自动判断为 MEDIUM），用户手动选择 GOOD

**预期行为**：
1. 用户进入播放器设置页（PreferenceFragment）
2. 看到"缓冲策略"项，当前显示"自动（当前 MEDIUM）"
3. 用户手动选择"激进（GOOD）"
4. SharedPreferences（`player_buffer_strategy`）保存用户选择
5. 下次播放视频使用 GOOD 档参数（minBuffer 8s/maxBuffer 120s）
6. `createLoadControlByTier` 检测到用户手动选择，跳过网络类型自动判断
7. 用户可切换回"自动"恢复网络类型自动判断

**验证方法**：操作手动切换档位，重新播放确认参数生效 + 网络类型判断被跳过

### Scenario 13：配置项开关控制首帧预加载（视频配置场景，R1）

**前置条件**：deviceTier=GOOD，网络 WiFi，`player_firstframe_preload=false`

**预期行为**：
1. 用户进入播放器设置页，看到"首帧预加载"开关
2. 用户关闭开关（`player_firstframe_preload=false`）
3. SharedPreferences 保存配置
4. 下次播放视频时，FirstFramePreloader 检测到 `player_firstframe_preload=false`
5. 所有档位均不预加载首帧（即使 GOOD 档）
6. 用户感知：节省流量，但首帧加载稍慢

**验证方法**：关闭首帧预加载开关，播放视频确认 GOOD 档也不预加载
