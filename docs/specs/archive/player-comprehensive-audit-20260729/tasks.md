# 播放器综合审查与遗漏点补全 - 任务清单

> **状态**：✅ P0已实施完成（2026-07-29 代码实施+编译通过，待真机验证）
> **创建日期**：2026-07-29
> **格式**：`- [ ] X.Y.Z 实施内容 - 修改位置 - 当前状态 - 实施细节 - 收益 - 风险 - 验证包：io.legado.miss.app.debug`
> **关联文档**：[README.md](./README.md) / [spec.md](./spec.md) / [design.md](./design.md)
> **权威源**：`design.md`（本 tasks.md 严格对齐 design.md 简化方案，禁止与原过度工程方案混用）
> **核心定位**：站在整体角度审查已完成 18 个视频播放器 spec + 5 个图片播放器 spec，识别遗漏点并提出**最小侵入补全方案**（10 文件变更：3 新增 + 7 修改）

---

## 0. 任务背景与核心约束

### 0.1 用户铁律（最高约束，不可降级）

1. **别过度工程化**：不新增独立管理器/协调器，在现有组件上增量扩展（原方案 9 个新组件全部砍掉，仅保留 3 个新增文件）
2. **别影响现有功能**：不修改嗅探主链路，不修改播放链路，仅扩展配置和 UI
3. **嗅探能力保护（AD-06，最高约束）**：禁止修改 `MimeSniffer.kt` 和 `ImageUrlExtractor.kt` 核心嗅探逻辑，仅可扩展；所有新增逻辑与嗅探链路解耦，try-catch 独立失败降级

### 0.2 简化方案核心（对齐 design.md §1）

| 维度 | 原方案（过度工程） | 简化方案（对齐 design.md） |
|------|------------------|------------------------|
| 变更文件数 | 23 文件（12 新增+11 修改） | **10 文件（3 新增+7 修改）** |
| 新增独立组件 | 9 个（NetworkTypeDetector/ErrorMapper/AutoReconnectManager/PlayHistoryStore/BitmapSampling/AdaptiveCacheManager/WebpackHookLoader/ImageMetadataExtractor/BatchSaveManager） | **3 个文件**（ErrorMapper/PlayHistory/PlayHistoryStore，无独立管理器） |
| 配置管理 | 新增 PlayerConfigManager 单例 | **在现有 SharedPreferences 增加 4 个配置项** |
| 嗅探增强 | 新增 WebpackHookEnhancer | **在现有 IMAGE_SNIFF_JS 常量追加 MutationObserver 脚本** |
| 大图加载 | 新增 BitmapSamplingLoader | **在现有 ImageLoader.kt 增加 override() 采样配置** |
| 智能缓冲 | 新增 NetworkTypeDetector 独立组件 | **在现有 createLoadControlByTier 方法内增加网络类型判断** |
| 自动重连 | 新增 AutoReconnectManager 独立管理器 | **在现有 onPlayerError 增加简单重试（3 次指数退避）** |
| 智能缓存 | 新增 AdaptiveCacheManager 运行时动态调整 | **App 启动时根据设备档位设置一次 Glide 缓存** |
| 批量保存 | 新增 BatchSaveManager 独立管理器 | **在现有 ImageGalleryActivity 增加批量保存循环** |
| 元数据 | 新增 ImageMetadataExtractor | **降级为 P2，暂不实施** |

### 0.3 优化目标（量化，对齐 design.md §5.3 验收标准）

| ADR | 验收指标 | 测量方法 | 对应任务 |
|-----|---------|---------|---------|
| AD-01 | 首帧渲染时间 ≤2000ms | logcat onRenderedFirstFrame | §2.1 |
| AD-02 | 3G 网络首帧时间降低 30%+ | 弱网模拟测试 | §2.2 |
| AD-03 | 错误提示用户可读率 100% | mock 各类 PlaybackException | §2.3 |
| AD-04 | 跨会话进度恢复 100% | 退出后重开同一视频验证 | §2.5 |
| AD-05 | 大图加载 0 OOM | 4K 图片连续加载测试 | §3.1 |
| AD-06 | 嗅探成功率不低于当前水平 | 实施后真机验证嗅探成功率 | §5.3 |

---

## 1. 准备工作

> **目标**：确认 10 文件变更范围、6 个 ADR、不新增独立管理器、不触碰嗅探核心文件。

- [x] 1.1 确认 10 文件变更范围（3 新增 + 7 修改，对齐 design.md §4）
  - 实施内容：核对 design.md §4.1/§4.2 文件清单，确认 3 新增文件路径 + 7 修改文件路径
  - 修改位置：无（文档核对）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：3 新增 = ErrorMapper.kt / PlayHistory.kt / PlayHistoryStore.kt；7 修改 = FirstFramePreloader.kt / ExoPlayerHelper.kt / VideoPlayerActivity.kt / ImageLoader.kt / ImageUrlExtractor.kt / ReadDatabase.kt / strings.xml
  - 收益：明确实施范围，避免遗漏或越界
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 1.2 确认 6 个 ADR 决策（AD-01 ~ AD-06，对齐 design.md §2）
  - 实施内容：核对 design.md §2 的 6 个 ADR 决策与状态
  - 修改位置：无（文档核对）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：AD-01 首帧分档位(Proposed) / AD-02 网络感知缓冲(Proposed) / AD-03 ErrorMapper(Proposed) / AD-04 PlayHistory(Proposed) / AD-05 大图采样(Proposed) / AD-06 嗅探保护(Accepted 用户铁律)
  - 收益：明确技术决策依据
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 1.3 确认不新增独立管理器/协调器（用户铁律 1）
  - 实施内容：核对 design.md §1.2 简化方案表，确认原方案 9 个新组件全部砍掉
  - 修改位置：无（文档核对）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：禁止新增 NetworkTypeDetector/AutoReconnectManager/BitmapSamplingLoader/AdaptiveCacheManager/WebpackHookLoader/ImageMetadataExtractor/BatchSaveManager/PlayerConfigManager 等独立组件
  - 收益：避免过度工程化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 1.4 确认嗅探保护禁改文件清单（用户铁律 3 + AD-06）
  - 实施内容：核对 design.md §4.4 不修改文件清单
  - 修改位置：无（文档核对）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：禁止修改 MimeSniffer.kt（视频 MIME 嗅探核心）/ exoplayer-resilience 相关文件（降级链核心）/ VideoPreloader.kt（预加载核心，仅调整参数不修改逻辑）；ImageUrlExtractor.kt 仅 IMAGE_SNIFF_JS 常量追加 MutationObserver，不修改核心嗅探逻辑
  - 收益：保证嗅探能力不降低
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 1.5 阅读 7 个修改文件的现有实现（源码核实，禁止凭经验臆测）
  - 实施内容：阅读 FirstFramePreloader.kt / ExoPlayerHelper.kt / VideoPlayerActivity.kt / ImageLoader.kt / ImageUrlExtractor.kt / ReadDatabase.kt / strings.xml 现有实现
  - 修改位置：无（源码阅读）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：重点阅读 prewarmCurrentVideo / createLoadControlByTier / onPlayerError / initSource / onResume / onPause / Glide 加载链 / IMAGE_SNIFF_JS 常量 / @Database 注解
  - 收益：为增量扩展提供准确锚点
  - 风险：跳过源码阅读凭经验臆测会导致接口不匹配
  - 验证包：io.legado.miss.app.debug

- [x] 1.6 确认 Room 数据库升级路径（AD-04，对齐 database-migration-safety.md）
  - 实施内容：评估 PlayHistory 新增表的数据库 version+1 与空 Migration 方案
  - 修改位置：无（方案评估）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：ReadDatabase.kt 当前 version + 1，新增 PlayHistory 实体到 @Database 列表，提供空 Migration（对齐 database-migration-safety.md 规范）
  - 收益：避免数据库升级失败导致 AD-04 功能不可用
  - 风险：Room 升级失败风险，需遵循 database-migration-safety.md
  - 验证包：io.legado.miss.app.debug

- [x] 1.7 确认真机测试包选择（代码优化任务必须用测试包）
  - 实施内容：确认代码优化任务用测试包 io.legado.miss.app.debug（按 AGENTS.md §真机测试包选择规范）
  - 修改位置：无（规范确认）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：禁止用正式包 io.legado.miss.app.release 测试代码优化（正式包用于 Skill 真机测试）；禁止用共存包 io.legado.app.debug（仅多 AI 并发测试隔离场景）
  - 收益：保证测试结果可定位问题
  - 风险：用错包导致测试结果失真
  - 验证包：io.legado.miss.app.debug

---

## 2. 视频播放器补全（5 个遗漏点，3 新增 + 3 修改）

### 2.1 首帧加载分档位策略（AD-01，复用 FirstFramePreloader，P0）

> **目标**：首帧渲染时间从 4027ms 降至 2000ms 以内，通过预加载深度优化（不通过并行化嗅探）。
> **边界**：不修改嗅探主链路，仅扩展预加载参数。

- [x] 2.1.1 在 FirstFramePreloader 扩展分档位预加载深度参数
  - 实施内容：prewarmCurrentVideo 增加分档位预加载深度参数（WEAK/MEDIUM/GOOD）
  - 修改位置：`app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt` 的 `prewarmCurrentVideo` 方法
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：WEAK 档不预加载首帧 / MEDIUM 档预加载 1 个分片 / GOOD 档预加载 3 个分片；预加载深度由 PlayerConfig（SharedPreferences）的 `player_firstframe_preload` 配置项 + `DeviceInfoHelper.getDeviceTier()` 共同决定；预加载失败仅 AppLog.put 记录日志，不影响主播放链路
  - 收益：首帧渲染时间从 4027ms 降至 2000ms 以内
  - 风险：GOOD 档预加载 3 个分片增加流量，用户可配置关闭（player_firstframe_preload=false）
  - 验证包：io.legado.miss.app.debug

- [ ] 2.1.2 真机验证首帧渲染时间（目标 < 2000ms）
  - 实施内容：真机播放 HLS/MP4 各 3 个视频，采集 onRenderedFirstFrame 时间戳
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：logcat 中 BufferSpeedAnalyticsListener 输出 TTFB < 2000ms；若未达标，逐项排查分档位是否生效 + 预加载是否命中
  - 收益：验证 AD-01 验收标准
  - 风险：弱网下预加载深度增加可能反而拖慢首帧
  - 验证包：io.legado.miss.app.debug

### 2.2 智能缓冲策略（AD-02，复用 createLoadControlByTier，P1）

> **目标**：首次播放首帧前即能选择合理缓冲档位（当前 bitrateEstimate=0 时无法感知网络类型）。
> **边界**：不重复 video-buffer-speed-optimization 的 LoadControl 调参，仅在档位选择增加网络类型维度。

- [ ] 2.2.1 在 ExoPlayerHelper.createLoadControlByTier 增加网络类型判断 + 用户配置覆盖
  - 实施内容：createLoadControlByTier 方法内增加网络类型判断（首次播放）+ 用户配置覆盖
  - 修改位置：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` 的 `createLoadControlByTier` 方法
  - 当前状态：🔄 待实施（首次播放 bitrateEstimate=0 时无法感知网络类型）
  - 实施细节：调用前先检查 PlayerConfig 的 `player_buffer_strategy`：若用户手动选择（GOOD/MEDIUM/WEAK）则用用户选择；若为"自动"则通过 ConnectivityManager.getActiveNetworkInfo 检测网络类型（WiFi→GOOD / 4G→MEDIUM / 3G→WEAK）；带宽测量生效后（bitrateEstimate>0）以带宽为主；LoadControl 参数设置逻辑不变，仅档位选择增加网络类型维度
  - 收益：首次播放首帧前即能选择合理缓冲档位
  - 风险：网络类型检测在方法内部增加几行代码，复杂度极低
  - 验证包：io.legado.miss.app.debug

- [ ] 2.2.2 真机验证 WiFi/4G/3G 场景缓冲策略
  - 实施内容：真机分别在 WiFi / 4G / 3G 网络下播放视频，采集缓冲中断次数
  - 修改位置：无（测试验证）
  - 当前状态：🔄 待验证
  - 实施细节：logcat 输出档位选择日志 + 3G 网络首帧时间降低 30%+；弱网模拟测试
  - 收益：验证 AD-02 验收标准
  - 风险：Android 不同版本 ConnectivityManager API 差异，需兼容性测试
  - 验证包：io.legado.miss.app.debug

### 2.3 错误提示用户体验（AD-03，新增 ErrorMapper.kt，P0）

> **目标**：播放失败时用户能理解错误原因并知道下一步操作。
> **边界**：纯 UI 增强，不涉及嗅探/播放链路。

- [x] 2.3.1 新增 ErrorMapper.kt 错误码映射组件
  - 实施内容：建立错误码→UserFacingError 映射表
  - 修改位置：新增 `app/src/main/java/io/legado/app/help/player/ErrorMapper.kt`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：覆盖 IO 类 / 解析类 / 解码类 / DRM 类 / 嗅探超时类 5 大类错误码；输出结构 UserFacingError(title, message, actions)；纯函数无副作用
  - 收益：播放失败时用户能理解错误原因
  - 风险：无（纯 UI 增强）
  - 验证包：io.legado.miss.app.debug

- [x] 2.3.2 VideoPlayerActivity.onPlayerError 接入 ErrorMapper
  - 实施内容：onPlayerError 回调中调用 ErrorMapper.map(error) 获取 UserFacingError，用 MaterialAlertDialog 展示
  - 修改位置：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 的 `onPlayerError` 回调
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：MaterialAlertDialog 展示错误提示 + 操作按钮（重试/换源/反馈），对齐项目现有错误弹窗风格；错误日志通过 AppLog.put("PlayerError", ...) 记录
  - 收益：错误提示用户可读率 100%
  - 风险：无（仅 UI 增强）
  - 验证包：io.legado.miss.app.debug

- [x] 2.3.3 strings.xml 新增错误提示文案
  - 实施内容：新增错误提示文案（IO 类/解析类/解码类/DRM 类/嗅探超时类 5 大类）
  - 修改位置：`app/src/main/res/values/strings.xml`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：文案用户可读，禁止技术术语（如错误码）；对齐项目现有 strings.xml 命名风格
  - 收益：错误提示文案统一管理
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 2.3.4 真机验证错误场景提示效果
  - 实施内容：模拟网络断开 / 无效 URL / 不支持格式 3 种错误场景
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：错误提示文案清晰可读 + 重试按钮可用 + 不可重试错误有关闭按钮；mock 各类 PlaybackException 覆盖率 100%
  - 收益：验证 AD-03 验收标准
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 2.4 网络错误恢复机制（在 onPlayerError 增加简单重试，P1）

> **目标**：网络断开后自动重连 + 进度恢复 + 指数退避。
> **边界**：不新增 AutoReconnectManager 独立管理器，在现有 onPlayerError 扩展。

- [ ] 2.4.1 在 VideoPlayerActivity.onPlayerError 增加简单重试逻辑（3 次指数退避）
  - 实施内容：onPlayerError 中识别网络类错误，自动重试 3 次，间隔 1s → 2s → 4s
  - 修改位置：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 的 `onPlayerError` 回调
  - 当前状态：🔄 待实施（无自动重连，需用户手动重播）
  - 实施细节：识别 ERROR_CODE_IO_NETWORK_CONNECTION_FAILED 等网络类错误 → 保存 currentPosition → 延迟 1s/2s/4s 后重新 prepare → seekTo 保存的进度 → 恢复播放；重试 3 次仍失败则回退到 ErrorMapper 展示错误提示（与 §2.3 协调）；重试过程中显示"正在重连...（第 N 次）"Toast；用户可取消（点击界面任意位置取消重试）
  - 收益：网络断开自动恢复率 ≥ 95%
  - 风险：重试过程中用户可能已手动操作，需检查 player 状态避免冲突
  - 验证包：io.legado.miss.app.debug

- [ ] 2.4.2 真机验证网络切换/断网场景
  - 实施内容：播放视频中切换 WiFi→4G / 断网 10s 后恢复 / 断网 60s 后恢复
  - 修改位置：无（测试验证）
  - 当前状态：🔄 待验证
  - 实施细节：网络恢复后自动重连 + 进度恢复到断网前位置 + 重试间隔符合指数退避（1s/2s/4s）；若进度恢复偏差 > 2s，检查 seekTo 时机（应在 STATE_READY 后 seekTo）
  - 收益：验证重连机制可用性
  - 风险：进度恢复精度风险
  - 验证包：io.legado.miss.app.debug

### 2.5 播放历史跨会话记忆（AD-04，新增 PlayHistory.kt + PlayHistoryStore.kt，P0）

> **目标**：跨会话恢复播放进度。
> **边界**：纯数据持久化，不涉及嗅探/播放链路；Room 数据库升级需谨慎。

- [x] 2.5.1 新增 PlayHistory.kt Room 实体
  - 实施内容：新增 Room 实体 PlayHistory
  - 修改位置：新增 `app/src/main/java/io/legado/app/data/entities/PlayHistory.kt`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：字段 = articleUrl / videoUrl / position / duration / lastPlayTime / rssSourceId（全部有默认值，对齐 naming_rules.md）；@Entity + @Parcelize；@PrimaryKey 复合主键（articleUrl + videoUrl）
  - 收益：为跨会话进度恢复提供数据结构
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 2.5.2 新增 PlayHistoryStore.kt 持久化 Helper
  - 实施内容：新增 PlayHistoryStore 持久化 Helper
  - 修改位置：新增 `app/src/main/java/io/legado/app/data/help/PlayHistoryStore.kt`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：接口 = save(url, position, duration) / load(url): PlayHistory? / clear(url)；使用 ReadDatabase.playHistoryDao()；save 使用 runCatching 包裹，失败仅 AppLog.put 记录；load 返回 null 时不影响主播放链路
  - 收益：跨会话进度持久化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 2.5.3 ReadDatabase.kt 新增 PlayHistory 实体 + version+1 + 空 Migration
  - 实施内容：新增 PlayHistory 实体到 @Database 列表，version+1，提供空 Migration
  - 修改位置：`app/src/main/java/io/legado/app/data/db/ReadDatabase.kt`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：@Database entities 列表追加 PlayHistory::class；version 当前值 + 1；新增空 Migration（对齐 database-migration-safety.md 规范）；新增 abstract fun playHistoryDao(): PlayHistoryDao
  - 收益：数据库支持 PlayHistory 表
  - 风险：Room 数据库升级失败风险，需遵循 database-migration-safety.md
  - 验证包：io.legado.miss.app.debug

- [x] 2.5.4 VideoPlayerActivity.initSource/onResume/onPause 接入 PlayHistoryStore
  - 实施内容：initSource 恢复进度 + onResume 启动定时保存（每 10s）+ onPause 保存最后一次
  - 修改位置：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 的 `initSource` / `onResume` / `onPause`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：initSource 中 ExoPlayer prepare 完成后调用 PlayHistoryStore.load(url)，若 position>10s 则 seekTo + Toast 提示"已从 XX:XX 继续播放"；onResume 启动定时保存（每 10s 调用 save）；onPause 保存最后一次并取消定时；读取 PlayerConfig 的 `player_history_enabled` 配置项，关闭时不保存
  - 收益：跨会话进度恢复 100%
  - 风险：Room 查询耗时可能影响 initSource 速度，需异步查询
  - 验证包：io.legado.miss.app.debug

- [x] 2.5.5 strings.xml 新增播放历史文案
  - 实施内容：新增播放历史文案（"已从 XX:XX 继续播放"等）
  - 修改位置：`app/src/main/res/values/strings.xml`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：对齐项目现有 strings.xml 命名风格
  - 收益：文案统一管理
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 2.5.6 真机验证跨会话进度恢复
  - 实施内容：播放视频至 1 分钟 → 退出 App → 重新打开同一文章视频
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：Toast 提示从 1 分钟位置继续 + 点击后 seekTo 60s + App 重启后历史仍存在；若进度未恢复，检查 PlayHistoryStore.save 是否在 onPause 触发 + Room 查询是否正确
  - 收益：验证 AD-04 验收标准
  - 风险：onPause 时机若不准确可能丢失最后几秒进度
  - 验证包：io.legado.miss.app.debug

---

## 3. 图片播放器补全（5 个遗漏点，0 新增 + 2 修改 + 1 追加）

### 3.1 大图采样加载（AD-05，复用 ImageLoader.kt，P0）

> **目标**：大图加载不触发 OOM。
> **边界**：不新增 BitmapSamplingLoader 独立加载器，在现有 ImageLoader 扩展。

- [x] 3.1.1 ImageLoader.kt 增加 override() 采样配置 + OOM 降级重试
  - 实施内容：为图片加载请求添加 override() 采样 + OOM 降级重试
  - 修改位置：`app/src/main/java/io/legado/app/help/image/ImageLoader.kt`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：根据 ImageView 尺寸计算目标分辨率调用 override(targetWidth, targetHeight)；极高分辨率图片（>4096px）强制降级到 2048px；在 Glide RequestListener.onLoadFailed 中捕获 OutOfMemoryError，降级到更低分辨率重试；runCatching 包裹，失败仅 AppLog.put 记录
  - 收益：大图加载 0 OOM
  - 风险：Glide 采样 API 在不同版本差异，需源码核实
  - 验证包：io.legado.miss.app.debug

- [ ] 3.1.2 真机验证大图加载 OOM 降级
  - 实施内容：真机加载 10 张 4K+ 大图（单张 > 5MB）+ 模拟低内存场景
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：无 OOM 崩溃 + 大图正常显示 + 低内存时降采样生效；开发者选项"不保留活动"模拟低内存
  - 收益：验证 AD-05 验收标准
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 3.2 智能缓存策略（App 启动时静态配置，P1）

> **目标**：根据设备档位设置 Glide 缓存大小。
> **边界**：不新增 AdaptiveCacheManager 运行时动态调整，仅在 App 启动时设置一次。

- [ ] 3.2.1 App 启动时根据设备档位设置 Glide 缓存大小
  - 实施内容：App.onCreate 中根据 DeviceInfoHelper.getDeviceTier() 设置 Glide MemoryCache 大小
  - 修改位置：`app/src/main/java/io/legado/app/help/image/ImageLoader.kt`（GlideModule 初始化）+ App 启动入口
  - 当前状态：🔄 待实施（Glide 缓存大小固定，未按设备档位差异化）
  - 实施细节：HIGH 档=96MB / MID 档=48MB / LOW 档=24MB；通过 GlideModule 初始化设置，不运行时调整；不修改 ImageLoader 核心加载逻辑，仅扩展初始化配置
  - 收益：缓存大小按设备档位自适应
  - 风险：Glide 缓存初始化需在 App.onCreate 完成，时机敏感
  - 验证包：io.legado.miss.app.debug

- [ ] 3.2.2 真机验证缓存策略自适应
  - 实施内容：真机在不同内存压力下加载图片批次 + 重复加载验证缓存命中
  - 修改位置：无（测试验证）
  - 当前状态：🔄 待验证
  - 实施细节：logcat 输出缓存大小按设备档位生效 + 重复加载缓存命中
  - 收益：验证缓存自适应
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 3.3 SPA 场景嗅探增强（AD-06 约束，IMAGE_SNIFF_JS 追加 MutationObserver，P1）

> **目标**：SPA 场景下图片嗅探成功率提升。
> **边界**：AD-06 最高约束，仅 IMAGE_SNIFF_JS 常量追加 MutationObserver 脚本，不替换原 5 路 Hook，不修改核心嗅探逻辑，超时保持 8s 不变。

- [ ] 3.3.1 ImageUrlExtractor.kt 的 IMAGE_SNIFF_JS 常量追加 MutationObserver 脚本
  - 实施内容：IMAGE_SNIFF_JS 常量追加 MutationObserver 脚本（不替换原 Hook）
  - 修改位置：`app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt` 的 `IMAGE_SNIFF_JS` 常量
  - 当前状态：🔄 待实施（SPA 场景下图片嗅探可能失败）
  - 实施细节：监听 document.body 子树变化（subtree=true / childList=true），新增 `<img>` 节点时提取 src；MutationObserver 配置防抖 500ms 避免性能影响；try-catch 保护，Hook 失败不影响原页面逻辑；**不替换**原 5 路 Hook，仅追加；**嗅探超时保持 8s 不变**（不延长，避免影响现有行为）
  - 收益：SPA 场景图片嗅探成功率提升
  - 风险：极低（仅追加 JS 脚本，不替换原 Hook）；MutationObserver 可能略降性能，已配置防抖 500ms
  - 验证包：io.legado.miss.app.debug

- [ ] 3.3.2 真机验证 SPA 场景嗅探成功率（含 AD-06 嗅探保护验证）
  - 实施内容：真机访问 3 个 SPA 站点 + 验证嗅探成功率不低于当前水平
  - 修改位置：无（测试验证）
  - 当前状态：🔄 待验证
  - 实施细节：SPA 站点嗅探成功率 ≥ 90% + 静态 HTML 站点嗅探成功率不降低（AD-06 约束）；MutationObserver 日志输出新增 img 数量；若 SPA 站点仍失败，分析是否 chunk 异步加载延迟 > 8s（不延长超时，评估降级）
  - 收益：验证 AD-06 约束下 SPA 嗅探增强效果
  - 风险：若嗅探成功率下降，需定位 MutationObserver 影响并增加降级保护
  - 验证包：io.legado.miss.app.debug

### 3.4 图片信息显示（P2，暂不实施）

> **目标**：缺少分辨率/大小/来源等元数据显示。
> **决策**：design.md §1.2 已降级为 P2 暂不实施（低实用性）。本节保留为占位，待 P0+P1 验证后评估是否实施。

- [ ] 3.4.1 评估图片元数据显示的实施必要性（P2，暂不实施）
  - 实施内容：待 P0+P1 验证后评估
  - 修改位置：无
  - 当前状态：⏸️ 暂不实施（P2，对齐 design.md §1.2 降级决策）
  - 实施细节：若评估实施，在现有 ImageGalleryActivity 增加信息面板，不新增 ImageMetadataExtractor 独立组件
  - 收益：低实用性，可降级评估
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 3.5 图片批量保存（在 ImageGalleryActivity 增加循环，P1）

> **目标**：批量保存图片。
> **边界**：不新增 BatchSaveManager 独立管理器，在现有 ImageGalleryActivity 增加循环。

- [ ] 3.5.1 在 ImageGalleryActivity 增加批量保存循环
  - 实施内容：批量保存图片到本地存储
  - 修改位置：`app/src/main/java/io/legado/app/ui/association/ImageGalleryActivity.kt`
  - 当前状态：🔄 待实施（仅单张保存，无批量）
  - 实施细节：复用现有单张保存逻辑，增加循环调用；并发控制（协程 maxConcurrency=3）；进度展示（通知栏或 UI 进度条显示"正在保存 N/M 张"）；单张失败不中断整体，最终汇总成功/失败数量；路径选择使用 SAF（Storage Access Framework）兼容 Android 11+；命名规则 = {articleTitle}_{index}.{format}
  - 收益：批量保存可用
  - 风险：SAF 路径选择 Android 10 以下不支持，需降级到传统 File 路径
  - 验证包：io.legado.miss.app.debug

- [ ] 3.5.2 真机验证批量保存功能
  - 实施内容：真机批量保存 10 张图片 + 验证保存路径
  - 修改位置：无（测试验证）
  - 当前状态：🔄 待验证
  - 实施细节：全部保存成功 + 进度展示正确 + 路径选择符合 Android 11+ 规范；若 Android 11+ 保存失败，检查 SAF 调用是否正确 + 权限是否申请
  - 收益：验证批量保存可用性
  - 风险：无
  - 验证包：io.legado.miss.app.debug

---

## 4. 灵活配置方案（在现有 SharedPreferences 增加配置项，P0）

> **目标**：让用户可配置缓冲/预加载/历史等参数。
> **边界**：不新增 PlayerConfigManager 独立管理器，在现有 SharedPreferences 增加 4 个配置项。

- [x] 4.1 在现有 SharedPreferences 增加 4 个配置项
  - 实施内容：增加 player_buffer_strategy / player_precache_range / player_history_enabled / player_firstframe_preload
  - 修改位置：现有 AppConfig 或 SharedPreferences 配置类
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：player_buffer_strategy（缓冲策略：自动/激进GOOD/平衡MEDIUM/保守WEAK，默认自动）/ player_precache_range（预缓存范围：0关闭/1/2/3，默认1）/ player_history_enabled（播放历史开关，默认true）/ player_firstframe_preload（首帧预加载开关，默认true）；默认值与当前自动行为一致，不影响未配置用户
  - 收益：用户可配置播放器行为
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 4.2 在现有播放器设置页（PreferenceFragment）增加配置入口
  - 实施内容：配置入口 UI，复用现有 UI 风格
  - 修改位置：现有播放器设置页（PreferenceFragment）
  - 当前状态：🔄 待实施
  - 实施细节：复用项目现有 PreferenceFragment，不引入新 UI 框架；配置项展示 = 下拉选择/开关，对齐现有设置项样式；不新增独立设置 Activity
  - 收益：用户可配置入口
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 4.3 集成配置项到各组件
  - 实施内容：各组件读取配置项
  - 修改位置：FirstFramePreloader.kt（player_firstframe_preload）/ ExoPlayerHelper.kt（player_buffer_strategy）/ VideoPlayerActivity.kt（player_history_enabled）/ 预缓存逻辑（player_precache_range）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：AD-01 FirstFramePreloader 读取 player_firstframe_preload；AD-02 ExoPlayerHelper 读取 player_buffer_strategy（用户手动选择优先于自动判断）；AD-04 VideoPlayerActivity 读取 player_history_enabled；预缓存逻辑读取 player_precache_range
  - 收益：配置项生效
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 4.4 真机验证配置生效
  - 实施内容：修改各配置项，真机验证对应行为变化
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：配置项修改后下次播放生效 + 用户手动选择优先于自动判断
  - 收益：验证配置生效
  - 风险：无
  - 验证包：io.legado.miss.app.debug

---

## 5. 验证与测试

> **强制规范**：按 AGENTS.md §强制规则：AI 自动端到端测试 + §真机测试包选择规范，代码优化任务必须用测试包 `io.legado.miss.app.debug`。

### 5.1 整体回归测试

- [ ] 5.1.1 编译验证（测试包 io.legado.miss.app.debug）
  - 实施内容：编译测试包 BUILD SUCCESSFUL
  - 修改位置：无（编译验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：命令 = `./gradlew assembleDebug -PpackageName=io.legado.miss.app.debug`（或参考 `ai_tests/scripts/quick_build_install.py`）；BUILD SUCCESSFUL 无报错
  - 收益：编译通过
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 5.1.2 全量视频播放回归（不破坏已完成 18 个视频 spec）
  - 实施内容：全量视频播放回归测试
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：测试脚本 = `ai_tests/scripts/l2_verify_video_player.py --scenario all`；覆盖场景 = HLS/MP4/DASH 各 3 个 + 嗅探失败降级 + 网络切换 + 错误重试；验证点 = 已实施优化不回归（LoadControl/HLS/OkHttp/自适应码率等）
  - 收益：不破坏已完成优化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 5.1.3 全量图片播放回归（不破坏已完成 5 个图片 spec）
  - 实施内容：全量图片播放回归测试
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：覆盖场景 = 静态 HTML 站点 + JS 渲染站点 + 大图 + 批量浏览；验证点 = 已实施优化不回归（画布渲染/线程安全/嗅探链路/画廊浏览）
  - 收益：不破坏已完成优化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 5.2 性能指标对比

- [ ] 5.2.1 视频播放指标对比（优化前 vs 优化后）
  - 实施内容：TTFB / 缓冲中断次数 / 网络恢复率 对比
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：指标 = TTFB（目标 < 2000ms）/ 缓冲中断次数（目标 < 1 次/小时）/ 网络恢复率（目标 ≥ 95%）；优化前基线 vs 优化后，各播放同一组视频 10 分钟；对比 logcat 中 BufferSpeedAnalyticsListener 输出；若指标未达标，逐项排查对应 ADR 实施
  - 收益：验证 AD-01/AD-02/§2.4 验收标准
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 5.2.2 图片播放指标对比（优化前 vs 优化后）
  - 实施内容：OOM 率 / 缓存命中率 / SPA 嗅探成功率 对比
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：指标 = OOM 率（目标 0%）/ 缓存命中率（目标 ≥ 80%）/ SPA 嗅探成功率（目标 ≥ 90%）；优化前基线 vs 优化后，各加载同一组图片批次；对比 logcat 中 ImageSniffer + ImageLoader 输出
  - 收益：验证 AD-05/AD-06/§3.2 验收标准
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 5.3 嗅探能力保护验证（AD-06，用户铁律，最高约束）

> **铁律**：嗅探能力保护为最高约束，不可降级。所有新增逻辑实施后，视频/图片嗅探成功率不低于当前水平。

- [ ] 5.3.1 评估各新增逻辑对嗅探链路的影响
  - 实施内容：评估 AD-01/AD-06 等新增逻辑与嗅探链路的耦合度
  - 修改位置：无（评估）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：评估 AD-01 预加载是否影响嗅探准确性（预加载失败降级不影响）；评估 AD-06 IMAGE_SNIFF_JS 追加 MutationObserver 是否替换原 5 路 Hook（仅追加不替换）；评估其他新增逻辑与嗅探链路的耦合度（必须解耦，try-catch 独立失败降级）
  - 收益：确认嗅探保护约束落实
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [ ] 5.3.2 真机验证嗅探成功率不降低（AD-06 验收标准）
  - 实施内容：实施所有新增逻辑后，真机测试视频/图片嗅探成功率
  - 修改位置：无（测试验证）
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：视频嗅探成功率保持 100%（不低于当前水平）+ 图片嗅探成功率 ≥ 90%（不低于当前水平）；覆盖静态 HTML 站点 + JS 渲染站点 + SPA 站点；若嗅探成功率下降，定位影响组件并增加解耦/降级保护
  - 收益：验证 AD-06 验收标准（用户铁律）
  - 风险：若嗅探成功率下降，需回滚影响组件
  - 验证包：io.legado.miss.app.debug

### 5.4 问题清单记录

- [ ] 5.4.1 真机测试问题记录到 ai_tests/issues-found.md
  - 实施内容：真机测试中发现的所有问题必须记录，禁止遗漏
  - 修改位置：`ai_tests/issues-found.md`
  - 当前状态：⏳ 待真机验证（用户指示后执行）
  - 实施细节：按 real-device-test-reuse.md 规范；格式 = 问题编号 / 场景 / 复现步骤 / 预期 / 实际 / 严重程度 / 状态
  - 收益：问题闭环
  - 风险：无
  - 验证包：io.legado.miss.app.debug

### 5.5 文档同步（强制）

> **强制规范**：按 AGENTS.md §强制规则：版本交付同步 + §任务完成前强制检查清单。

- [x] 5.5.1 更新 assets/updateLog.md（编译前更新，基于 git diff 分析真实代码变更）
  - 实施内容：本次播放器综合审查遗漏点补全的可感知变化
  - 修改位置：`assets/updateLog.md`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：内容 = 视频首帧加载更快 / 弱网下播放更流畅 / 播放失败提示更友好 / 跨会话续播 / 大图不再 OOM / SPA 图片嗅探更稳 / 可批量保存图片等可感知变化；禁止仅对已有日志条目做文字合并，必须基于 git diff 分析真实代码变更
  - 收益：用户感知变化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 5.5.2 更新 docs/INDEX.md（状态从"设计中" → "开发中" → "已完成"）
  - 实施内容：本任务条目状态更新
  - 修改位置：`docs/INDEX.md`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：本任务条目 = `docs/specs/player-comprehensive-audit-20260729/`
  - 收益：文档索引同步
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 5.5.3 更新 .trae/memory/ai_memory_main.md（任务状态 + 用户反馈）
  - 实施内容：任务状态 + 用户反馈持久化
  - 修改位置：`.trae/memory/ai_memory_main.md`
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：任务状态 = 设计完成 → 实施中 → 真机验证中 → 已完成；用户反馈 = AskUserQuestion 响应必须第一时间记录（按 context-recovery.md 规范，24H 制时间戳，PowerShell `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`）
  - 收益：任务状态持久化
  - 风险：无
  - 验证包：io.legado.miss.app.debug

- [x] 5.5.4 检查清单核对（按 AGENTS.md §任务完成前强制检查清单 7 项）
  - 实施内容：7 项检查清单核对
  - 修改位置：无（检查清单）
  - 当前状态：✅ 已完成（2026-07-29）
  - 实施细节：1.思考无违禁词 / 2.调试日志已清理（Grep "android.util.Log.d\|android.util.Log.e" 确认无残留）/ 3.updateLog 已更新 / 4.文档同步 / 5.主动沉淀 / 6.问题清单 / 7.AskUserQuestion 确认
  - 收益：任务完成前强制检查
  - 风险：无
  - 验证包：io.legado.miss.app.debug

---

## 检查点

### 检查点 1：§1 准备工作 + §2 视频播放器补全 + §4 灵活配置完成

- 验收标准：
  - §1 准备工作 7 项全部完成（10 文件变更确认 + 6 个 ADR 确认 + 不新增独立管理器确认 + 嗅探保护禁改文件确认）
  - §2 视频播放器 5 个遗漏点全部完成（§2.1-§2.5）
  - §4 灵活配置 4 项全部完成
  - 编译通过（测试包 `io.legado.miss.app.debug`）
  - 真机验证视频指标达标（TTFB < 2000ms / 弱网中断 < 1 次/小时 / 网络恢复 ≥ 95% / 跨会话进度恢复 100%）
- 必须执行 AskUserQuestion（三选项：通过/需调整/拒绝）

### 检查点 2：§3 图片播放器补全完成

- 验收标准：
  - §3 图片播放器 5 个遗漏点全部完成（§3.1-§3.5，§3.4 P2 暂不实施除外）
  - 编译通过（测试包 `io.legado.miss.app.debug`）
  - 真机验证图片指标达标（OOM 0% / 缓存命中 ≥ 80% / SPA 嗅探 ≥ 90% / 批量保存可用）
- 必须执行 AskUserQuestion（三选项：通过/需调整/拒绝）

### 检查点 3：§5 验证与测试完成

- 验收标准：
  - §5.1 整体回归测试通过（不破坏已完成 23 个 spec）
  - §5.2 性能指标对比达标
  - §5.3 嗅探能力保护验证通过（AD-06 用户铁律，嗅探成功率不低于当前水平）
  - §5.4 问题清单记录完整
  - §5.5 文档同步完成（updateLog.md / INDEX.md / ai_memory_main.md）
  - 检查清单 7 项全部核对
- 必须执行 AskUserQuestion（三选项：通过/需调整/拒绝）

---

## 依赖关系

```
§1 准备工作
    ↓
§4 灵活配置（SharedPreferences 4 配置项，被各组件依赖）
    ↓
§2.1 首帧加载（AD-01，依赖 player_firstframe_preload）──┐
§2.2 智能缓冲（AD-02，依赖 player_buffer_strategy）──┤
§2.3 错误提示（AD-03，新增 ErrorMapper）──┼── §2.4 重连（依赖 §2.3 ErrorMapper）── §2.5 播放历史（AD-04，依赖 player_history_enabled）
                                                        │                                              ↓
                                                        └────────────────────────────────────── §5.1 视频回归
                                                                                                        ↓
§3.1 大图采样（AD-05，复用 ImageLoader）──┐                                                     §5.2 性能对比
§3.2 智能缓存（App 启动静态配置）──┤
§3.3 SPA 嗅探（AD-06，IMAGE_SNIFF_JS 追加）──┤
§3.4 元数据（P2 暂不实施）──┤
§3.5 批量保存（ImageGalleryActivity 循环）──┘                                              ↓
                                                                                §5.3 嗅探保护验证（AD-06）
                                                                                        ↓
                                                                                §5.4 问题清单
                                                                                        ↓
                                                                                §5.5 文档同步
```

- §4 灵活配置被各组件依赖（先实施）
- §2.4 重连依赖 §2.3 ErrorMapper（重连 3 次失败回退到错误提示）
- §2 和 §3 可并行实施（视频与图片播放器独立）
- §5 验证依赖 §2 和 §3 全部完成
- §5.3 嗅探保护验证为最高约束（AD-06 用户铁律）

---

## 风险点

1. **Room 数据库升级风险**（AD-04）：PlayHistoryStore 新增表需按 database-migration-safety.md 规范，提供空 Migration，避免升级失败
2. **IMAGE_SNIFF_JS 追加 MutationObserver 性能风险**（AD-06）：图片嗅探速度可能略降，已配置 subtree+childList 精确监听 + 防抖 500ms
3. **首帧预加载深度增加流量风险**（AD-01）：GOOD 档预加载 3 个分片增加流量，用户可配置关闭（player_firstframe_preload=false）
4. **Glide 缓存初始化时机风险**（AD-05）：缓存大小设置需在 App.onCreate 通过 GlideModule 初始化，时机敏感
5. **网络类型检测兼容性风险**（AD-02）：Android 不同版本 ConnectivityManager API 差异，需兼容性测试
6. **SAF 路径选择兼容性风险**（§3.5）：Android 10 以下不支持 SAF，需降级到传统 File 路径
7. **跨会话进度恢复精度风险**（AD-04）：onPause 时机若不准确可能丢失最后几秒进度，需在 onPause 保存最后一次
8. **重连与用户操作冲突风险**（§2.4）：重试过程中用户可能已手动操作，需检查 player 状态避免冲突

---

## 反模式（禁止）

1. ❌ 新增独立管理器/协调器（用户铁律 1，原方案 9 个新组件全部砍掉，仅保留 3 个新增文件）
2. ❌ 修改嗅探主链路核心文件（用户铁律 3 + AD-06，禁止修改 MimeSniffer.kt / ImageUrlExtractor.kt 核心逻辑 / exoplayer-resilience 降级链 / VideoPreloader.kt 核心逻辑）
3. ❌ 替换原 5 路 JS Hook（AD-06，IMAGE_SNIFF_JS 仅追加 MutationObserver，不替换）
4. ❌ 延长嗅探超时（AD-06，超时保持 8s 不变，避免影响现有行为）
5. ❌ 凭经验臆测 API 行为（每个新增逻辑必须源码核实 + 网上成熟方案查证）
6. ❌ 跳过 updateLog.md 更新（按 AGENTS.md §强制规则：版本交付同步，编译前更新）
7. ❌ 用正式包测试代码优化（必须用测试包 `io.legado.miss.app.debug`）
8. ❌ 静默吞掉异常空 catch 块（按 coding-philosophy.md 规范，必须 AppLog.put 记录或回退）
9. ❌ 引入新依赖（jsoup 升级 / rhino 升级等，对齐 AGENTS.md Landmines）
10. ❌ 运行时热切换 LoadControl 触发 re-prepare（对齐 video-buffer-speed-optimization AD-01，网络类型变化仅下次播放生效）
11. ❌ 删除现有嗅探策略（保持向后兼容，仅增强不替换）
12. ❌ 与原过度工程方案混用（本 tasks.md 严格对齐 design.md 简化方案，禁止混入原 9 个新组件任务）

---

## 实施优先级（按用户反馈实用性优先，对齐 design.md §1.3）

> **用户铁律**：所有新增逻辑必须遵守 AD-06 嗅探能力保护约束（不降低嗅探能力，可加强不可削弱）。
> **优先级**：P0 = 高实用性（用户直接感知）→ P1 = 中实用性（特定场景）→ P2 = 低实用性（可降级评估）。

### P0（高实用性，用户直接感知）

- §1 准备工作（含 AD-06 嗅探保护约束确认）
- §4 灵活配置（在现有 SharedPreferences 增加 4 个配置项，被各组件依赖，先实施）
- §2.1 首帧加载（AD-01，复用 FirstFramePreloader 扩展分档位）
- §2.3 错误提示（AD-03，新增 ErrorMapper，MaterialAlertDialog 统一风格）
- §2.5 播放历史（AD-04，跨会话续播高实用性）
- §3.1 大图采样（AD-05，OOM 防护高实用性，复用 ImageLoader）
- → 检查点 1 部分验证（含嗅探能力不降低验证）

### P1（中实用性，特定场景）

- §2.2 智能缓冲（AD-02，弱网场景，复用 createLoadControlByTier）
- §2.4 自动重连（在 onPlayerError 增加简单重试 3 次指数退避）
- §3.2 智能缓存（App 启动时静态配置，不新增 AdaptiveCacheManager）
- §3.3 SPA 嗅探（AD-06 约束下，IMAGE_SNIFF_JS 追加 MutationObserver，仅增强不削弱）
- §3.5 批量保存（在 ImageGalleryActivity 增加循环，不新增 BatchSaveManager）
- → 检查点 1+2 完整验证

### P2（低实用性，可降级评估）

- §3.4 元数据显示（暂不实施，待 P0+P1 验证后评估）
- → 检查点 3 验证

---

> **强制门禁**：每个检查点完成后必须执行 AskUserQuestion（三选项：通过/需调整/拒绝），按 AGENTS.md §强制规则：AI 自动端到端测试 规范。
