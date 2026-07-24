# Spec：TVBox 优化方案（借鉴影视仓优化 legado）

> **状态**：🔄 设计中
> **创建日期**：2026-07-22

## Intent（意图）

legado 当前视频播放能力相对薄弱：仅有 ExoPlayer 单引擎、弹幕功能残缺、无字幕管理、无 DLNA 投屏、本地服务器 API 有限。而影视仓（FongMi/TV）作为成熟的影视聚合播放器，在上述方向有经过验证的架构设计。

**为什么要优化？**

1. **播放体验差距**：legado 用户遇到硬解失败的视频无法播放（无双引擎降级），弹幕/字幕体验不完整
2. **网络能力局限**：legado 仅有 Rhino JS 引擎（ES5.1 + 无 JIT），部分复杂规则解析慢，规则覆盖面受限
3. **投屏缺失**：legado 完全没有 DLNA 投屏能力，用户无法投屏到电视
4. **本地 API 受限**：现有 `HttpServer` 仅支持书源/书籍 CRUD，不支持播放控制、远程搜索等

**优化目标**：在不改变 legado 阅读器核心定位的前提下，通过借鉴影视仓的成熟设计，补齐上述四方面短板，提升视频/影视类 RSS 源的播放体验。

## Scope（范围）

### 1. 播放器优化

**做什么**：
- 引入 MPV 软解引擎，与现有 ExoPlayer 形成「硬解优先 + 软解兜底」双引擎架构
- 完善 DanmakuSetting 弹幕设置系统（透明度/字号/速度/显示区域/屏蔽规则）
- 新增字幕轨道管理（Track + TrackUtil，支持多音轨/多字幕切换）
- 增强 VideoUrlExtractor 嗅探能力（智能识别视频 URL、支持 iframe 嵌套）
- 引入 PreloadSetting 预加载策略（预加载下一集、预加载缓冲区大小可配）

**不做什么**：
- 不重写 GSYVideoPlayer（保留现有播放器作为宿主）
- 不引入外部弹幕源（仅支持规则配置的弹幕 URL）
- 不实现视频下载（已在其他模块处理）

### 2. 网络层优化

**做什么**：
- 引入 QuickJS 引擎作为 Rhino 的补充（性能更好，部分场景替代）
- 抽象 `Spider` 接口（参考 catvod），统一不同脚本引擎的调用方式
- 增强反爬能力（JS 加密解密算法支持）

**不做什么**：
- 不替换现有 Rhino 引擎（保持向后兼容）
- 不引入 catvod 完整框架（仅借鉴 Spider 抽象设计）
- 不改变 OkHttp + Cronet 主网络栈
- 不嵌入 Python 解释器（Chaquopy 商用授权问题，见 Out of Scope）

### 3. DLNA 投屏

**做什么**：
- 引入 jupnp 库，实现完整 DLNA 投屏能力
- 支持 DMC（控制器）角色：搜索设备、选择设备、投屏控制（播放/暂停/进度/音量）
- 支持 DMR（渲染器）角色：legado 作为渲染器接收外部投屏
- 集成到视频播放界面（投屏按钮、设备列表对话框）

**不做什么**：
- 不实现 DMS（媒体服务器）角色（legado 不作为媒体库对外提供内容）
- 不实现 DLNA 直播推流
- 不支持非 DLNA 协议（如 AirPlay/Google Cast）

### 4. 本地服务器

**做什么**：
- 扩展 `HttpServer` API，新增播放控制类接口（play/pause/seek/setVolume）
- 新增远程搜索接口（search/getSourceList/getEpisodeList）
- 新增设备状态接口（getPlayingInfo/getQueue/listQueue）
- 支持 WebSocket 推送播放状态变化（参考影视仓 `Nano.java`）

**不做什么**：
- 不替换 NanoHTTPD（保留现有实现）
- 不实现完整的 Web 播放器 UI（仅提供 API）
- 不改变现有书源/书籍 CRUD 接口

### 与现有视频播放器 spec 的关系

> 本 spec 与项目已有的视频播放器相关 spec 是**扩展关系而非替代关系**。

| 现有 spec | 关系 | 说明 |
|-----------|------|------|
| `douyin-style-video-player` | 扩展 | 本 spec 不改变其 UI 交互（抖音风格上下滑动），仅优化底层播放器引擎能力（双引擎/弹幕/字幕） |
| `video-article-swipe-switch` | 扩展 | 本 spec 不改变其滑动切换逻辑，仅提供 PlayerEngine 接口供其调用 |
| `video-control-visibility-enhancement` | 扩展 | 本 spec 不改变其控制栏显隐逻辑，PlayerEngine 接口的状态查询方法可供其使用 |

**原则**：现有 spec 的 UI 交互保持不变，本 spec 仅优化底层引擎能力（PlayerEngine 接口抽象、双引擎切换、DLNA 投屏、本地服务器 API 扩展）。现有 spec 中的播放器调用代码可逐步迁移到 PlayerEngine 接口，但不强制一次性迁移。

### Out of Scope（不在本次范围内）

- **Python 嵌入**：因 Chaquopy 商用授权问题（开源项目商用需付费授权），Python 嵌入方向暂不实施。如未来有合适的开源 Python 嵌入方案，可重新评估。
- **AirPlay/Google Cast 协议**：仅支持 DLNA 协议，不支持其他投屏协议
- **DMS（媒体服务器）角色**：legado 不作为媒体库对外提供内容
- **完整 Web 播放器 UI**：本地服务器仅提供 API，不实现 Web 端播放器界面
- **视频下载**：已在其他模块处理

## Approach（方案）

### Selected Approach（选定方案）

采用「渐进式四方向并行」方案：
- 每个方向独立成模块，可独立实施和验证
- 优先实施成本低、收益高的方向（建议顺序：PlayerEngine 接口抽象（前置）→ DLNA + 本地服务器（并行）→ 播放器完整优化 → 网络层）
- 每个方向完成后单独发版验证，避免大爆炸式集成

**实施顺序调整说明**：
- 原"DLNA → 本地服务器 → 播放器 → 网络层"顺序未考虑方向间依赖关系
- 调整后：先实施 PlayerEngine 接口抽象（作为 DLNA 和本地服务器的前置任务），再并行实施 DLNA + 本地服务器（用户价值最高），最后实施播放器完整优化和网络层
- QuickJS/网络层优化独立于其他方向，可随时穿插实施

**方向间依赖关系**：
1. 本地服务器播放控制 API → 依赖播放器引擎抽象（PlayerEngine 接口）
2. DLNA 投屏控制 → 依赖播放器状态查询（PlayerEngine 接口）
3. QuickJS/网络层优化 → 独立（不依赖其他方向）
- 详见 design.md「方向间依赖关系」图

**核心设计原则**：
1. **接口抽象优先**：借鉴影视仓的 `PlayerEngine`/`Spider`/`Device` 抽象，先定义接口再实现
2. **配置驱动**：新增能力通过 `AppConfig` 开关控制，默认关闭，用户按需开启（替代原 productFlavors 隔离方案，避免与现有 `flavorDimensions = ['mode']` 冲突）
3. **向后兼容**：所有现有接口和行为保持不变，新增能力不破坏旧规则
4. **可回退**：所有新功能通过 AppConfig 开关控制，功能异常时用户可随时关闭回退到原有行为

### Alternatives Considered（备选方案）

| 方案 | 描述 | 优点 | 缺点 | 决策 |
|------|------|------|------|------|
| A. 完整移植影视仓架构 | 直接移植 catvod + 双引擎 + DLNA 全套 | 功能最完整 | APK 体积爆炸（+30MB）、维护成本高、偏离阅读器定位 | ❌ 否决 |
| B. 仅优化播放器 | 只做双引擎 + 弹幕字幕，不做 DLNA/网络层 | 实施成本低 | 用户投屏需求无法满足、网络能力短板仍在 | ❌ 否决 |
| C. Fork 影视仓播放模块 | 提取影视仓 player/ 模块作为独立 library 复用 | 代码复用率高 | 影视仓 player 与 catvod 强耦合、Java 21 vs legado Kotlin 不兼容 | ❌ 否决 |
| D. 渐进式四方向并行（选定） | 四方向独立实施、接口抽象、配置驱动 | 灵活、风险可控、可按需取舍 | 整体周期长、需要良好的接口设计 | ✅ 采纳 |
| E. 等待社区贡献 | 不主动开发，等待社区 PR | 零成本 | 不可控、无法保证时间表 | ❌ 否决 |

### Drawbacks（缺点）

1. **APK 体积增加**：MPV（~8MB）+ jupnp（~3MB）+ QuickJS（~2MB）= 预计 +13MB。当前 legado debug APK 约 60-70MB，增量比例约 18-22%，需通过 AppConfig 开关控制功能启用，用户按需开启。
2. **维护复杂度上升**：双引擎/多脚本引擎增加 Bug 排查难度，需完善的引擎切换日志
3. **DLNA 兼容性**：不同电视设备 DLNA 实现差异大，需要大量真机测试
4. **接口设计前置成本**：`PlayerEngine`/`Spider`/`Device` 抽象需要充分调研，设计不当会导致后续返工
5. **MPV so 库维护成本**：从影视仓提取的 libmpv.so 需跟随上游 mpv 版本更新，存在维护负担

### Prior Art（影视仓参考）

| 模块 | 影视仓实现 | legado 对应现状 | 借鉴点 |
|------|-----------|----------------|--------|
| 播放器引擎 | `PlayerEngine` 接口 + `PlayerEngineFactory` 工厂 + `ExoPlayerEngine` 实现 | `ExoPlayerHelper` 单实现 | 接口抽象 + 工厂模式 |
| 弹幕系统 | `Danmaku` bean + `DanmakuSetting` 完整设置 | `DanmakuAdapter` + `BiliDanmukuParser` 仅解析 | 设置系统补全 |
| 字幕管理 | `Track` + `TrackUtil` 多轨道 | 无 | 完整新建 |
| 嗅探 | `Sniffer` 智能嗅探 | `VideoUrlExtractor` 基础嗅探 | 增强 iframe/加密识别 |
| 预加载 | `PreloadSetting` 完整策略 | `VideoPlay.kt` 简单配置 | 策略补全 |
| 爬虫框架 | catvod `Spider` 抽象 | 自定义规则引擎 + Rhino | Spider 接口抽象 |
| 脚本引擎 | QuickJS | Rhino JS | 多引擎补充 |
| DLNA | jupnp 完整实现 | 无 | 完整新建 |
| 本地服务器 | `Nano.java` 远程控制 API | `HttpServer.kt` CRUD API | 播放控制 API 扩展 |

## Requirements（需求）

### 播放器优化需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| P-001 | 引入 MPV 软解引擎作为 ExoPlayer 兜底 | P0 | 硬解失败时自动切换软解，播放成功 |
| P-002 | 定义 `PlayerEngine` 接口，ExoPlayer/MPV 均实现该接口 | P0 | 工厂可创建两种引擎实例 |
| P-003 | 用户可手动切换硬解/软解模式 | P1 | 设置面板提供切换选项，立即生效 |
| P-004 | 完善 DanmakuSetting（透明度/字号/速度/区域/屏蔽） | P1 | 5 项设置均生效，实时预览 |
| P-005 | 新增字幕轨道管理（多音轨/多字幕切换） | P1 | 支持切换至少 2 条音轨/字幕 |
| P-006 | 增强 VideoUrlExtractor 嗅探（iframe/加密识别） | P2 | 嗅探成功率较旧版提升 ≥20% |
| P-007 | 引入 PreloadSetting（预加载下一集/缓冲区可配） | P2 | 下一集切换时间减少 ≥30% |

### 网络层优化需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| N-001 | 引入 QuickJS 引擎，与 Rhino 并存 | P0 | 书源规则可在 QuickJS 下执行 |
| N-002 | 抽象 `Spider` 接口，统一脚本引擎调用 | P0 | Rhino/QuickJS 实现同一接口 |
| N-003 | 用户可选择脚本引擎（全局/单源） | P1 | 设置面板 + 单源配置均可选 |
| N-004 | 增强反爬（JS 加密解密算法） | P2 | 新增至少 3 种解密算法支持 |

### DLNA 投屏需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| D-001 | 引入 jupnp 库，实现 DLNA DMC（控制器） | P0 | 可搜索到局域网 DLNA 设备 |
| D-002 | 支持投屏播放（推送 URL 到设备） | P0 | 视频可在电视上播放 |
| D-003 | 支持投屏控制（播放/暂停/进度/音量/停止） | P0 | 5 项控制均生效 |
| D-004 | 实现 DMR（渲染器），legado 接收外部投屏 | P1 | 其他设备可投屏到 legado |
| D-005 | 投屏 UI 集成（投屏按钮/设备列表对话框） | P1 | 视频界面有投屏入口 |

### 本地服务器需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| S-001 | 扩展 HttpServer，新增播放控制 API | P0 | play/pause/seek/setVolume 接口可用 |
| S-002 | 新增远程搜索 API | P1 | search/getSourceList/getEpisodeList 可用 |
| S-003 | 新增设备状态 API | P1 | getPlayingInfo/getQueue/listQueue 可用 |
| S-004 | 支持 WebSocket 推送播放状态 | P2 | 状态变化 1 秒内推送 |

## Scenarios（使用场景）

### 场景 1：播放器优化 - 硬解失败兜底

**用户故事**：用户播放一个 MKV 格式的视频，ExoPlayer 硬解失败（设备不支持该编码），传统情况下视频无法播放。

**优化后流程**：
1. 用户点击播放，ExoPlayer 尝试硬解
2. 硬解失败抛出 `RendererException`
3. `PlayerEngineFactory` 自动切换到 MPV 软解引擎
4. MPV 软解播放成功，界面显示「已切换软解」提示
5. 用户可在设置中手动锁定软解模式

**验收**：硬解失败的视频可正常播放，切换过程对用户透明。

### 场景 2：网络层优化 - QuickJS 加速规则执行

**用户故事**：某 RSS 源使用复杂 JS 规则解析列表，Rhino 执行慢（单页解析 3 秒），用户体验差。

**优化后流程**：
1. 用户在源编辑界面将脚本引擎切换为 QuickJS
2. 重新加载列表，QuickJS 执行相同规则
3. 解析时间降至 800ms，速度提升 3 倍以上
4. 若 QuickJS 不兼容某 API，自动回退 Rhino 并提示

**验收**：QuickJS 下解析速度 ≥ Rhino 2 倍，不兼容时自动回退。

### 场景 3：DLNA 投屏 - 投屏到电视

**用户故事**：用户在手机上播放视频，希望投屏到客厅电视大屏观看。

**优化后流程**：
1. 用户在视频界面点击「投屏」按钮
2. 弹出设备列表对话框，自动搜索局域网 DLNA 设备
3. 用户选择电视设备，视频在电视上播放
4. 手机变为遥控器，可控制播放/暂停/进度/音量
5. 退出投屏时电视停止播放，手机恢复本地播放

**验收**：可投屏到至少 3 种主流电视品牌，控制响应延迟 ≤ 500ms。

### 场景 4：本地服务器 - 远程控制播放

**用户故事**：用户在电脑浏览器打开 legado 本地服务器，希望远程控制手机上的视频播放（如翻到下一集）。

**优化后流程**：
1. 用户在电脑浏览器访问 `http://手机IP:1122`
2. 调用 `/getPlayingInfo` 获取当前播放信息
3. 调用 `/playNext` 切换到下一集
4. WebSocket 实时推送播放进度到浏览器
5. 浏览器显示当前播放状态

**验收**：浏览器可远程控制播放，状态推送延迟 ≤ 1 秒。
