# ExoPlayer 韧性优化 - 任务清单

> 状态：🔄 设计中（R2 修订：基于业界调研改为预嗅探+缓存+多级识别方案）
> 创建时间：2026-07-26

## 1. 准备工作

- [ ] 1.1 阅读相关源码：ExoPlayerHelper.kt / Exo2MediaPlayer.kt / VideoFragment.kt / AnalyzeUrl.kt
- [ ] 1.2 阅读 okHttpClient 配置（HttpHelper.kt 或等价位置），确认 Range 请求支持
- [ ] 1.3 阅读 EventBus.kt 现有事件常量结构
- [ ] 1.4 阅读 ResolvingDataSource 现有实现（ExoPlayerHelper.kt L127-149），确认无法修改 mimeType
- [ ] 1.5 阅读 ExoPlayer Extractor.sniff() 接口，确认内置嗅探能力

## 2. Layer 1：预嗅探机制（核心）

### 2.1 MimeSniffer 工具类

- [ ] 2.1.1 新增 `MimeSniffer.kt`：magic number 匹配工具类，输入 ByteArray，输出 mimeType 或 null
- [ ] 2.1.2 实现 magic number 表（参考 Chromium + Go 规范）：
  - mp4: `ftyp` at offset 4 → `MimeTypes.VIDEO_MP4`
  - m3u8: `#EXTM3U` at offset 0 (跳过 BOM `\xEF\xBB\xBF`) → `MimeTypes.APPLICATION_M3U8`
  - flv: `FLV\x01` at offset 0 → `"video/x-flv"`
  - ts: `\x47` 在前 1KB 中重复≥10次 → `MimeTypes.VIDEO_MP2T`
  - mkv/webm: `\x1A\x45\xDF\xA3` at offset 0 → `MimeTypes.VIDEO_MATROSKA`
  - mpd: `<?xml` + `<MPD` → `MimeTypes.APPLICATION_MPD`
- [ ] 2.1.3 单元测试 `MimeSniffer`：覆盖各格式 magic number 输入 + 边界情况（空数据、不完整数据、混合数据）

### 2.2 MimeSnifferCache 缓存

- [ ] 2.2.1 新增 `MimeSnifferCache.kt`：URL → mimeType LRU 缓存
- [ ] 2.2.2 实现 `android.util.LruCache<String, String>(100)`（参考项目内 customIp LruCache 模式）
- [ ] 2.2.3 实现 TTL 1 小时（用 `System.currentTimeMillis()` 记录写入时间，过期失效）
- [ ] 2.2.4 实现 key 规则：URL 去除 query 参数后的 path（避免 query 变化导致缓存失效）

### 2.3 sniffMimeType suspend 函数

- [ ] 2.3.1 在 `ExoPlayerHelper.kt` 新增 `suspend fun sniffMimeType(url: String, headers: Map<String, String>): String?`
- [ ] 2.3.2 流程实现：
  - L1: 查 MimeSnifferCache，命中直接返回
  - L2: 用 okHttpClient 发 `Range: bytes=0-1023` 请求（在 Dispatchers.IO 执行）
  - L3: 检查响应头 Content-Type，若有效（video/* 或 application/x-mpegURL）直接使用
  - L4: 读取响应 body 前 1KB，用 MimeSniffer 匹配 magic number
  - L5: 失败返回 null（不抛异常）
- [ ] 2.3.3 实现超时控制：3 秒超时（withTimeoutOrNull），避免阻塞 UI
- [ ] 2.3.4 实现结果缓存：嗅探成功后存入 MimeSnifferCache
- [ ] 2.3.5 实现日志：Tag=SniffingMime，记录 urlPath 前 40 字符 + 嗅探结果 + 耗时

### 2.4 createMediaItem 接入

- [ ] 2.4.1 修改 `ExoPlayerHelper.createMediaItem` 签名：新增 `sniffedMimeType: String? = null` 参数
- [ ] 2.4.2 实现优先级链：`sniffedMimeType > getMimeType(url) > null`
- [ ] 2.4.3 修改 createMediaItem 日志：增加 sniffedMimeType 字段（已有 mimeType 日志）
- [ ] 2.4.4 修改 `AnalyzeUrl.getMediaItem()`：改为 suspend 函数，先调 sniffMimeType 再 createMediaItem
- [ ] 2.4.5 修改 `Exo2MediaPlayer.kt#L148`：调用 createMediaItem 时传入 sniffedMimeType（从 sniffMimeType 协程获取）

### 2.5 编译验证

- [ ] 2.5.1 编译验证（确认无语法错误）
- [ ] 2.5.2 真机测试包验证：用动态 URL（如 `/play.php?id=xxx` 返回 mp4）测试嗅探生效

## 3. Layer 4：getMimeType else 兜底 BUG 修复（已临时修复，纳入规范）

- [ ] 3.1 确认 `ExoPlayerHelper.kt#L93` 已改为 `else -> null`（临时修复已完成）
- [ ] 3.2 补充注释说明：本次修复纳入 exoplayer-resilience OpenSpec 规范

## 4. Layer 2：自动 WebView 降级

- [ ] 4.1 在 `EventBus.kt` 新增常量 `VIDEO_FALLBACK_WEBVIEW = "videoFallbackWebview"`
- [ ] 4.2 修改 `Exo2MediaPlayer.onPlayerError`：区分可恢复 vs 不可恢复错误（不可恢复类型见 design.md AD-03）
- [ ] 4.3 在 `Exo2MediaPlayer.onPlayerError` 中：retryCount >= MAX_RETRY(3) + 不可恢复错误 → postEvent(VIDEO_FALLBACK_WEBVIEW, Triple<url, title, headers>)
- [ ] 4.4 修改 `VideoPlayerActivity.kt`：observeEvent(VIDEO_FALLBACK_WEBVIEW) → 找到当前 VideoFragment → 调用 switchToWebViewMode
- [ ] 4.5 修改 `VideoFragment.switchToWebViewMode`：增加 Toast 提示"ExoPlayer 多次失败，已切换到 WebView 模式"
- [ ] 4.6 增加日志：Tag=ExoFallback，记录失败次数 + 错误码 + URL path 前 40 字符
- [ ] 4.7 确保现有 `btnSwitchBack` 切回 ExoPlayer 时重置 retryCount=0
- [ ] 4.8 编译验证
- [ ] 4.9 真机测试包验证：构造一个 ExoPlayer 必失败的源（如非视频 URL），确认 3 次失败后自动切 WebView

## 5. 日志和调试

- [ ] 5.1 修改 `ExoPlayerHelper.createMediaItem` 日志：增加嗅探来源标识（已有 mimeType 日志）
- [ ] 5.2 嗅探日志独立 Tag=SniffingMime：记录 urlPath 前 40 字符 + 嗅探结果 + 耗时
- [ ] 5.3 自动降级日志 Tag=ExoFallback：记录失败次数 + 错误码 + URL path 前 40 字符

## 6. 文档同步

- [ ] 6.1 更新 `docs/project-flow/task-navigation.md`：增加 MimeSniffer / MimeSnifferCache / sniffMimeType 模块锚点
- [ ] 6.2 更新 `assets/updateLog.md`：基于 git diff 分析真实代码变更，面向用户描述"内置播放器韧性优化"
- [ ] 6.3 更新 `docs/INDEX.md`：将 exoplayer-resilience 从"设计中"移到"已完成"

## 7. 真机端到端测试

- [ ] 7.1 测试包编译安装：`python ai_tests/scripts/quick_build_install.py`（必须用测试包 `io.legado.miss.app.debug`）
- [ ] 7.2 L2 视频播放器验证：`python ai_tests/scripts/l2_verify_video_player.py`
- [ ] 7.3 场景1测试：动态 URL（无后缀）→ 预嗅探 → 正确播放 mp4
- [ ] 7.4 场景2测试：多类型混合源（m3u8+mp4+flv）→ 每个视频独立嗅探 → 全部正确播放
- [ ] 7.5 场景3测试：缓存命中（二次播放同一 URL）→ 0 延迟 + 正确 mimeType
- [ ] 7.6 场景4测试：构造 ExoPlayer 必失败源 → 3 次失败后自动切 WebView
- [ ] 7.7 场景5测试：可恢复错误（网络抖动）→ 重试成功，不触发降级
- [ ] 7.8 场景6测试：服务端 Content-Type 正确 → 跳过 magic number 检测，直接使用
- [ ] 7.9 回归测试：存量源播放不受影响（验证嗅探不破坏现有逻辑）
- [ ] 7.10 日志验证：logcat 中 SniffingMime / ExoFallback / createMediaItem 日志正常输出

## 8. 验收检查清单

- [ ] 8.1 预嗅探机制实现：MimeSniffer + MimeSnifferCache + sniffMimeType
- [ ] 8.2 5 级识别优先级链全部实现（缓存→Content-Type→magic number→URL后缀→默认推断）
- [ ] 8.3 自动 WebView 降级实现
- [ ] 8.4 getMimeType else 兜底 BUG 已修复
- [ ] 8.5 多类型混合源场景验证通过（用户反馈核心场景）
- [ ] 8.6 缓存命中场景验证通过（二次播放 0 延迟）
- [ ] 8.7 所有新增代码无调试日志残留（Grep 确认 0 残留）
- [ ] 8.8 updateLog.md 已更新（基于 git diff 分析，非文字合并）
- [ ] 8.9 文档同步完成（task-navigation / INDEX）
- [ ] 8.10 真机测试包全场景通过

## AOAdapt 日志模板（实施中按需填写）

```markdown
- [ ] X.Y [任务描述]
  - Action: [执行了什么操作]
  - Observation: [观察到了什么结果]
  - Adapt: [基于观察做了什么调整]
```

## 设计审查反馈记录

### R1（2026-07-26 用户审查反馈）

- **触发**：检查点1 用户审查设计方案
- **用户原话**："为什么要加字段，让原作者声明呢？声明只能声明一个，一个网站如果列表的视频是多种类型呢？声明个屁"
- **核心问题**：原方案 Layer 3 "源规则声明" 设计错误
- **修订**：去除 videoType 字段设计，改为纯运行时自动判断
- **影响**：删除 RssSource/AppDatabase/DatabaseMigrations/AnalyzeUrl 相关修改；新增"多类型混合源"场景测试

### R2（2026-07-26 用户审查反馈）

- **触发**：检查点1 R1 修订后用户再次审查，要求"深度分析+搜索成熟方案+重点解决嗅探能力"
- **用户原话**："在深度分析，并且去网上搜索查找成熟方案，重点解决嗅探能力呀"
- **核心问题**：R1 修订的 OkHttp 拦截器 + ThreadLocal 方案有跨线程丢失问题
- **调研发现**：
  1. ExoPlayer 内置 Extractor.sniff() 但需先选对 MediaSourceFactory
  2. ResolvingDataSource 能修改 URI 但不能修改 mimeType
  3. HttpDataSource.Factory 拦截无法修改 createMediaItem 时已固定的 mimeType
  4. OkHttp 原生支持 Range 请求
  5. Chromium 多级识别策略：Content-Type → URL 模式 → 内容特征 → 兜底
- **修订**：改用预嗅探 + 缓存 + 多级识别方案
  - 新增 MimeSniffer + MimeSnifferCache 两个独立组件
  - 新增 sniffMimeType suspend 函数（Range 请求 + magic number + 缓存）
  - createMediaItem 新增 sniffedMimeType 参数
  - 5 级识别优先级链
- **影响**：
  - 删除原 OkHttp 拦截器方案（SniffingMimeTypeInterceptor.kt 不再创建）
  - 删除 ThreadLocalMime.kt（不再需要）
  - 新增 MimeSniffer.kt + MimeSnifferCache.kt
  - AnalyzeUrl.getMediaItem() 改为 suspend 函数
  - Exo2MediaPlayer 调用 createMediaItem 需协程上下文
