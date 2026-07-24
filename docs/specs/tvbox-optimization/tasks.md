# Tasks：TVBox 优化方案任务清单

> **状态**：🔄 设计中
> **创建日期**：2026-07-22
> **格式说明**：使用 `- [ ] X.Y` 复选框格式，按四个方向分组

## AOAdapt 日志格式

> 实施过程中每个任务需记录 AOAdapt 日志，格式如下：

```
[AOAdapt] Task X.Y
- Action: 执行的具体操作（如"引入 jupnp 依赖"、"实现 DlnaManager"）
- Observation: 观察到的结果/现象（如"构建通过"、"设备搜索成功"、编译错误信息）
- Adapt: 根据观察结果做的调整/适配（如"修正依赖版本"、"增加异常捕获"、"延后该任务"）
```

**记录要求**：
- 每个任务完成后记录一条 AOAdapt 日志
- Observation 需包含具体技术数据（编译结果/测试结果/性能数据）
- Adapt 需说明是否偏离原计划及原因
- 日志记录到 `issues-found.md` 或任务追踪系统中

## 1. 准备工作

- [ ] 1.1 对比分析影视仓 `PlayerEngine`/`PlayerEngineFactory`/`ExoPlayerEngine` 源码
- [ ] 1.2 对比分析影视仓 `Danmaku`/`DanmakuSetting`/`Track`/`TrackUtil` 源码
- [ ] 1.3 对比分析影视仓 `Sniffer`/`PreloadSetting` 源码
- [ ] 1.4 对比分析影视仓 catvod `Spider` 抽象 + QuickJS 集成
- [ ] 1.5 对比分析影视仓 `dlna/` 模块（jupnp 用法）
- [ ] 1.6 对比分析影视仓 `Nano.java` 本地服务器 API 设计
- [ ] 1.7 分析 legado 现有 `ExoPlayerHelper`/`VideoPlayer`/`DanmakuAdapter` 架构
- [ ] 1.8 分析 legado 现有 `HttpHelper`/`OkHttpUtils`/`Cronet` 网络层架构
- [ ] 1.9 分析 legado 现有 `HttpServer`/`WebSocketServer` 本地服务器架构
- [ ] 1.10 评估 APK 体积影响（MPV/QuickJS/jupnp 各项体积，计算增量比例）
- [ ] 1.11 评估 minSdk 23 兼容性：jupnp（API 21+ 兼容）、QuickJS（API 21+ 兼容）、MPV libmpv.so（需核实编译时 minSdk 版本与 ABI 兼容性）
- [ ] 1.12 调研 QuickJS/jupnp 最新版本与 Android 兼容性（是否有 quickjs-ng 等替代库）
- [ ] 1.13 调研 MPV so 库获取方式（从影视仓提取 / 自行编译 / 许可证兼容性评估）
- [ ] 1.14 编写技术调研报告，确认每个方向可行性

## 2. 播放器优化

### 2.1 双引擎架构

- [ ] 2.1.1 定义 `PlayerEngine` 接口（`help/player/PlayerEngine.kt`）
- [ ] 2.1.2 实现 `PlayerEngineFactory`（`help/player/PlayerEngineFactory.kt`）
- [ ] 2.1.3 重构 `ExoPlayerHelper` 为 `ExoPlayerEngineImpl`（实现 `PlayerEngine` 接口）
- [ ] 2.1.4 引入 MPV so 库（从影视仓提取 libmpv.so 到 jniLibs，AppConfig.isMpvEnabled 控制启用）
- [ ] 2.1.5 实现 `MpvEngine`（JNI 调用 libmpv）
- [ ] 2.1.6 实现硬解失败自动切换软解逻辑（捕获 `RendererException`）
- [ ] 2.1.7 实现引擎切换时位置保存与恢复（`seekTo` 恢复）
- [ ] 2.1.8 在 `VideoPlayer` 接入 `PlayerEngineFactory`
- [ ] 2.1.9 设置面板新增「硬解/软解」切换选项（`VideoSettingsPanel`）
- [ ] 2.1.10 编写双引擎切换单元测试

### 2.2 弹幕设置系统

- [ ] 2.2.1 新建 `DanmakuSetting`（透明度/字号/速度/区域/屏蔽规则）
- [ ] 2.2.2 在 `AppConfig` 新增弹幕设置持久化
- [ ] 2.2.3 改造 `DanmakuAdapter` 接入 `DanmakuSetting`
- [ ] 2.2.4 在 `VideoSettingsPanel` 新增弹幕设置 UI
- [ ] 2.2.5 实现弹幕设置实时预览

### 2.3 字幕与音轨管理

- [ ] 2.3.1 新建 `Track` 数据类（type/index/label/language）
- [ ] 2.3.2 新建 `TrackUtil`（getTracks/selectTrack/getCurrentTrack）
- [ ] 2.3.3 在 `PlayerEngine` 接口新增轨道管理方法
- [ ] 2.3.4 `ExoPlayerEngineImpl` 实现轨道管理（ExoPlayer TrackSelector）
- [ ] 2.3.5 `MpvEngine` 实现轨道管理（MPV track-list 属性）
- [ ] 2.3.6 在 `VideoSettingsPanel` 新增「音轨」「字幕」选择 UI

### 2.4 嗅探增强

- [ ] 2.4.1 增强 `VideoUrlExtractor` 支持 iframe 嵌套递归嗅探
- [ ] 2.4.2 新增加密 URL 识别（base64/JS 加密）
- [ ] 2.4.3 扩展视频 MIME 类型白名单
- [ ] 2.4.4 新增嗅探超时配置（默认 10s）
- [ ] 2.4.5 实现嗅探结果去重（同 URL 不同质量保留最优）

### 2.5 预加载策略

- [ ] 2.5.1 新建 `PreloadSetting`（enablePreloadNext/preloadBufferMs/maxPreloadCount/preloadOnWifiOnly）
- [ ] 2.5.2 在 `AppConfig` 新增预加载配置持久化
- [ ] 2.5.3 在 `VideoPlayService` 切集逻辑中接入预加载
- [ ] 2.5.4 实现预加载仅在 WiFi 下生效（网络类型判断）
- [ ] 2.5.5 在 `VideoSettingsPanel` 新增预加载设置 UI

### 2.6 播放器验证

- [ ] 2.6.1 真机测试：硬解失败视频可自动切换软解
- [ ] 2.6.2 真机测试：弹幕设置 5 项均生效
- [ ] 2.6.3 真机测试：多音轨/多字幕切换
- [ ] 2.6.4 真机测试：嗅探成功率较旧版提升 ≥20%
- [ ] 2.6.5 真机测试：下一集切换时间减少 ≥30%

## 3. 网络层优化

### 3.1 脚本引擎抽象

- [ ] 3.1.1 定义 `ScriptEngine` 接口（`help/script/ScriptEngine.kt`）
- [ ] 3.1.2 实现 `RhinoEngine`（包装现有 Rhino 调用）
- [ ] 3.1.3 改造 `AnalyzeRule` 的 JS 规则部分接入 `ScriptEngine`
- [ ] 3.1.4 实现引擎选择配置（全局/单源）
- [ ] 3.1.5 实现执行失败自动回退逻辑

### 3.2 QuickJS 引擎

- [ ] 3.2.1 引入 `quickjs-android` 依赖
- [ ] 3.2.2 实现 `QuickJsEngine : ScriptEngine`（JNI 调用）
- [ ] 3.2.3 实现 ES2017 语法支持验证
- [ ] 3.2.4 实现对象序列化（JSON 传递，无 Java 互操作）
- [ ] 3.2.5 兼容性测试：现有 Rhino 规则在 QuickJS 下执行
- [ ] 3.2.6 实现不兼容 API 自动回退 Rhino

### 3.3 反爬增强

- [ ] 3.3.1 新增 JS 加密解密算法支持（至少 3 种）
- [ ] 3.3.2 评估 NewPipeExtractor 引入可行性（参考影视仓）
- [ ] 3.3.3 增强 Cookie 管理（参考影视仓 CookieStore）

### 3.4 网络层验证

- [ ] 3.4.1 真机测试：QuickJS 下复杂规则解析速度 ≥ Rhino 2 倍
- [ ] 3.4.2 真机测试：QuickJS 不兼容时自动回退 Rhino
- [ ] 3.4.3 真机测试：单源引擎选择生效

## 4. DLNA 投屏

### 4.1 基础设施

- [ ] 4.1.1 引入 jupnp 依赖
- [ ] 4.1.2 实现 `DlnaManager`（管理 `UpnpService` 生命周期）
- [ ] 4.1.3 实现 `DlnaDevice` 数据类
- [ ] 4.1.4 在 `AppConfig` 新增 DLNA 开关配置
- [ ] 4.1.5 Android 权限声明（局域网访问权限）

### 4.2 DMC 控制器

- [ ] 4.2.1 实现 `DlnaSearchService`（M-SEARCH 组播 + 设备发现）
- [ ] 4.2.2 实现设备描述 XML 解析
- [ ] 4.2.3 实现 `DlnaController.cast(device, url)`（SetAVTransportURI + Play）
- [ ] 4.2.4 实现 `DlnaController.pause()`/`resume()`/`stop()`
- [ ] 4.2.5 实现 `DlnaController.seek(position)`
- [ ] 4.2.6 实现 `DlnaController.setVolume(volume)`
- [ ] 4.2.7 实现投屏状态查询（GetPositionInfo/GetTransportInfo）

### 4.3 DMR 渲染器（接收投屏）

- [ ] 4.3.1 实现 `DlnaRendererService`（注册 legado 为 DLNA 渲染设备）
- [ ] 4.3.2 接收 `SetAVTransportURI` 后启动 `VideoPlayService`
- [ ] 4.3.3 接收 `Play/Pause/Stop` 转发到播放器
- [ ] 4.3.4 上报当前状态到订阅者（事件订阅）

### 4.4 UI 集成

- [ ] 4.4.1 新建 `DlnaDeviceDialog`（设备列表 RecyclerView）
- [ ] 4.4.2 实现搜索中状态显示
- [ ] 4.4.3 实现投屏后切换为「控制面板」（播放/暂停/进度/音量/停止）
- [ ] 4.4.4 在 `VideoPlayerActivity` 顶部菜单新增「投屏」按钮
- [ ] 4.4.5 投屏状态指示器（图标显示当前是否投屏中）

### 4.5 DLNA 验证

- [ ] 4.5.1 真机测试：可搜索到局域网 DLNA 设备
- [ ] 4.5.2 真机测试：视频可投屏到至少 3 种电视品牌
- [ ] 4.5.3 真机测试：5 项控制（播放/暂停/进度/音量/停止）均生效
- [ ] 4.5.4 真机测试：DMR 接收外部投屏
- [ ] 4.5.5 真机测试：控制响应延迟 ≤ 500ms
- [ ] 4.5.6 边界测试：DLNA 设备不可达时的错误处理与用户提示
- [ ] 4.5.7 边界测试：投屏中 WiFi 断开后网络中断恢复（重连后可恢复控制或优雅退出）
- [ ] 4.5.8 边界测试：并发投屏控制（多个设备同时投屏时的冲突处理）

## 5. 本地服务器

### 5.1 播放控制 API

- [ ] 5.1.1 新建 `PlaybackController`（`api/controller/PlaybackController.kt`）
- [ ] 5.1.2 实现 `/play` 接口（播放指定视频）
- [ ] 5.1.3 实现 `/pause`/`/resume` 接口
- [ ] 5.1.4 实现 `/seek` 接口（参数：position）
- [ ] 5.1.5 实现 `/setVolume` 接口（参数：volume）
- [ ] 5.1.6 实现 `/playNext`/`/playPrev` 接口
- [ ] 5.1.7 实现 `PlaybackController` 与 `VideoPlayService` 通过 EventBus 通信
- [ ] 5.1.8 在 `HttpServer.serve` 中新增路由分发

### 5.2 远程搜索与状态 API

- [ ] 5.2.1 实现 `/search` 接口（参数：keyword）
- [ ] 5.2.2 实现 `/getSourceList` 接口
- [ ] 5.2.3 实现 `/getEpisodeList` 接口
- [ ] 5.2.4 实现 `/getPlayingInfo` 接口
- [ ] 5.2.5 实现 `/getQueue`/`/listQueue` 接口

### 5.3 WebSocket 状态推送

- [ ] 5.3.1 新建 `PlaybackWebSocket`（`web/socket/PlaybackWebSocket.kt`）
- [ ] 5.3.2 实现客户端连接订阅播放状态
- [ ] 5.3.3 实现状态变化推送 JSON（type/position/duration/state/title）
- [ ] 5.3.4 实现心跳保活（30 秒 ping）
- [ ] 5.3.5 在 `HttpServer` 重写 `openWebSocket` 方法路由

### 5.4 本地服务器验证

- [ ] 5.4.1 真机测试：浏览器可调用播放控制 API
- [ ] 5.4.2 真机测试：远程搜索接口可用
- [ ] 5.4.3 真机测试：WebSocket 状态推送延迟 ≤ 1 秒
- [ ] 5.4.4 真机测试：现有书源/书籍 CRUD 接口不受影响

### 5.5 HttpServer Controller 分发重构

> 对应 ADR-4：将 `HttpServer.serve` 从内联路由重构为 Controller 分发模式，避免路由膨胀。

- [ ] 5.5.1 定义 `Controller` 接口与路由分发机制（按路径前缀分发到对应 Controller）
- [ ] 5.5.2 将现有书源/书籍/RSS CRUD 路由迁移到对应 Controller（保持接口不变）
- [ ] 5.5.3 将新增的播放控制 API 路由纳入 Controller 分发体系
- [ ] 5.5.4 回归测试：现有所有 HTTP 接口行为不受影响

## 6. 集成验证

### 6.1 构建验证

- [ ] 6.1.1 默认构建通过（AppConfig 开关全部关闭，功能不启用）
- [ ] 6.1.2 开启全部 AppConfig 开关后构建通过（含 MPV/jupnp/QuickJS 依赖）
- [ ] 6.1.3 APK 体积测量（默认关闭 vs 全部开启对比，计算增量比例）

### 6.2 端到端测试

- [ ] 6.2.1 端到端：硬解失败 → 软解兜底 → 投屏到电视 → 浏览器远程控制
- [ ] 6.2.2 端到端：QuickJS 规则解析 → 播放 → 弹幕显示 → 字幕切换
- [ ] 6.2.3 端到端：DLNA 投屏 → 电视播放 → 手机控制 → 退出投屏
- [ ] 6.2.4 端到端：浏览器搜索 → 选择视频 → 远程播放 → 状态推送

### 6.3 性能与兼容性

- [ ] 6.3.1 性能：MPV 软解 CPU 占用 ≤ 40%
- [ ] 6.3.2 性能：QuickJS 规则解析速度 ≥ Rhino 2 倍
- [ ] 6.3.3 性能：jupnp 设备搜索 ≤ 5 秒发现设备
- [ ] 6.3.4 兼容性：minSdk 23 真机运行通过
- [ ] 6.3.5 兼容性：至少 5 种编码格式播放测试
- [ ] 6.3.6 兼容性：至少 3 种电视品牌 DLNA 投屏测试

### 6.4 文档与发布

- [ ] 6.4.1 更新 `assets/updateLog.md`（基于 git diff 分析真实变更）
- [ ] 6.4.2 更新 `AGENTS.md` 任务导航（新增模块代码锚点）
- [ ] 6.4.3 更新 `docs/project-flow/task-navigation.md`
- [ ] 6.4.4 编写用户使用说明（投屏/双引擎/弹幕设置）
- [ ] 6.4.5 更新 `docs/INDEX.md` 索引
- [ ] 6.4.6 真机测试问题闭环（`issues-found.md` 记录所有问题）

## 7. 收尾

- [ ] 7.1 全量真机回归测试（`run_e2e.py --tc all`）
- [ ] 7.2 调试日志清理（Grep `android.util.Log.d|android.util.Log.e` 确认无残留）
- [ ] 7.3 代码审查（`code-review` skill）
- [ ] 7.4 安全审查（`security-review` skill）
- [ ] 7.5 经验沉淀（写入 `basic-memory`）
- [ ] 7.6 项目记忆更新（`project_memory.md`）
