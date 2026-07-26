# ExoPlayer 韧性优化 - 需求规格

> 状态：🔄 设计中（R2 修订：基于业界调研改为预嗅探+缓存+多级识别方案）
> 创建时间：2026-07-26
> 任务来源：用户反馈 3002 错误码 + "浏览器能播放但内置播放器报错"痛点

## Intent（意图）

解决内置视频播放器在视频网站规则千差万别场景下的播放失败问题。

### 痛点证据

| 错误码 | 场景 | 频次 | 用户体验 |
|--------|------|------|---------|
| 3002 PARSING_CONTAINER_MALFORMED | URL 不带后缀 + else 强制 m3u8 | 本次新发现 | 黑屏 + 错误弹窗 |
| 3003 UnrecognizedInputFormatException | SPLIT_TAG 拼接破坏 URL 后缀 | 已修（68次历史） | 黑屏 + 错误弹窗 |
| 416 Range Not Satisfiable | SimpleCache 与服务端 Range 冲突 | 已修 | 偶发卡顿 |
| HTTP/2 StreamResetException | CDN HTTP/2 实现有 bug | 已修（22次历史） | 黑屏 + 错误弹窗 |
| 浏览器可播放但 ExoPlayer 失败 | 防盗链/动态URL/非标HLS/多类型混合源 | 持续存在 | 用户抱怨"为什么浏览器能播，App 不能播" |

### 用户痛点原话
> "为什么点击直接浏览器访问这个视频链接地址，就没问题，内置视频播放器怎么这么多问题"

## Scope（范围）

### In Scope（本次实现）

1. **预嗅探机制**：在 prepare 之前用 Range 请求读取响应前 1KB，按 magic number 判断真实格式
2. **多级识别策略**：参考 Chromium，5 级兜底（缓存→Content-Type→magic number→URL后缀→默认推断）
3. **自动 WebView 降级**：ExoPlayer 失败次数累计达阈值 + 不可恢复错误时，自动调 `switchToWebViewMode`
4. **getMimeType 修复**：else 兜底强制返回 m3u8 → 返回 null（已临时修复，本次纳入正式规范）

### Out of Scope（本次不做）

- 不重写 ExoPlayer 核心库
- 不替换播放器框架（GSY → ExoPlayer3 已完成）
- 不修改视频缓存架构（SimpleCache 已优化）
- 不修改 Cronet/OkHttp 降级机制（已有阈值降级）
- 不修改视频网站规则引擎（CSS/JSONPath/XPath/JS）
- 不增加新的视频格式支持
- **不新增 RssSource.videoType 字段**（R1 否决：用户反馈"一个网站如果列表的视频是多种类型呢？声明个屁"）
- **不使用 OkHttp 拦截器 + ThreadLocal 方案**（R2 否决：ExoPlayer 在自己线程加载数据，ThreadLocal 跨线程会丢失）

## Approach（技术方案）

### Selected Approach：预嗅探 + 缓存 + 多级识别（参考 Chromium）

**5 级识别优先级链**：

1. **L1 - 缓存命中**：URL → mimeType LRU 缓存，二次播放直接命中（0 延迟）
2. **L2 - 服务端 Content-Type**：HTTP 响应头中的 Content-Type（若服务端返回正确）
3. **L3 - magic number 检测**：用 Range 请求读前 1KB，匹配 ftyp/EXTM3U/FLV 等 magic number
4. **L4 - URL 后缀检测**：现有 getMimeType 逻辑保留（已修复 else 兜底 BUG）
5. **L5 - 默认推断**：返回 null 让 ExoPlayer 用内置 Extractor.sniff() 尝试

### 调研依据

| 来源 | 关键发现 |
|------|---------|
| ExoPlayer 官方源码 | `Extractor` 接口实现 `sniff(extractorInput)` 方法读头部判断格式，但只在选定 MediaSourceFactory 后才触发 |
| setMimeType 作用 | 不是绕过嗅探，而是告诉 ExoPlayer 走哪个 MediaSourceFactory（HlsMediaSource / ProgressiveMediaSource） |
| Chromium 多级识别 | Content-Type → URL 模式 → 内容特征 → 兜底 |
| Go DetectContentType | 用 512 字节检测，完整 magic number 表 |
| OkHttpDataSource | 原生支持 Range 请求，可用 `Range: bytes=0-1023` 读前 1KB |

### Alternatives Considered（否决的替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 方案A：仅扩展 getMimeType 后缀表 | 增加 .avi/.mov/.wmv 等更多后缀 | 治标不治本，动态URL/无后缀场景仍漏判 |
| 方案B：完全用内容嗅探替代后缀检测 | 移除 getMimeType，全部走嗅探 | 增加每次请求 1KB 开销，且嗅探需先发请求，无法在 setMimeType 阶段生效 |
| 方案C：用 ExoPlayer 的 DefaultExtractorFactory 自动识别 | 不设 mimeType，让 ExoPlayer 自己试 | ExoPlayer 是严格匹配，不识别直接 3003，不友好 |
| 方案D：直接对接 WebView 作为默认播放器 | 完全放弃 ExoPlayer | 失去缓存加速/手势控制/倍速等 ExoPlayer 优势 |
| 方案E：让用户手动选择播放器 | UI 加"切换播放器"按钮 | 已有 `btnSwitchBack`，但用户希望自动降级不要手动切 |
| 方案F：源作者显式声明 videoType 字段 | RssSource 新增 videoType 字段 | R1 否决：一个源列表中视频可能是 m3u8+mp4 混合，单字段无法表达；让源作者声明是负担 |
| 方案G：OkHttp 拦截器 + ThreadLocal 嗅探 | 在 OkHttp 拦截器层嗅探 | R2 否决：ExoPlayer 在自己线程加载数据，ThreadLocal 跨线程会丢失 |
| 方案H：HttpDataSource.Factory 拦截 | 包装 OkHttpDataSource.Factory，在 open() 时 peek | 不能修改 MediaItem mimeType（createMediaItem 时已固定），只能用于错误后重试 |

### Drawbacks（选定方案的缺点）

1. **预嗅探增加首次播放延迟**：约 200-500ms（用 Range 请求 1KB），但通过缓存可避免二次嗅探
2. **自动降级会切换播放器**：用户感知"播放器闪烁"，需 UI 提示"已自动切换到 WebView 模式"
3. **预嗅探增加一次网络请求**：仅首次播放，二次命中缓存无开销
4. **预嗅探对 302 重定向需特殊处理**：需读最终响应而不是中间 302 响应

### Prior Art（参考）

- [ExoPlayer 官方文档：MediaItem mimeType 设置](https://developer.android.com/media/media3/exoplayer)
- [Chromium 内容嗅探规范](https://mimesniff.spec.whatwg.org/)
- [Go DetectContentType 算法](https://go.dev/src/net/http/sniff.go)
- 项目内 `getMimeType` P1-3 修复历史（SPLIT_TAG → setMimeType）

## Requirements（需求）

### R1：预嗅探机制（核心）

- **R1.1** 新增 `MimeSniffer.kt` 工具类：输入 ByteArray，输出 mimeType 或 null
- **R1.2** magic number 表（参考 Chromium + Go 规范）：
  - mp4: `ftyp` (offset 4)
  - m3u8: `#EXTM3U` (前 7 字节，跳过 BOM)
  - flv: `FLV\x01` (前 4 字节)
  - ts: `\x47` 重复出现 (前 1KB 中至少 10 个 0x47 字节)
  - mkv/webm: `\x1A\x45\xDF\xA3` (前 4 字节)
  - mpd: `<?xml` + `<MPD` (XML 头 + MPD 标签)
- **R1.3** 新增 `MimeSnifferCache.kt`：URL → mimeType LRU 缓存（上限 100，TTL 1小时）
- **R1.4** 预嗅探函数 `suspend fun sniffMimeType(url, headers): String?`：
  - 先查缓存，命中直接返回
  - 用 okHttpClient 发 `Range: bytes=0-1023` 请求
  - 读取响应 body 前 1KB
  - 用 MimeSniffer 匹配 magic number
  - 结果存入缓存
  - 失败返回 null（不抛异常）
- **R1.5** 修改 `AnalyzeUrl.getMediaItem()`：改为 suspend 函数，调用 sniffMimeType 后再 createMediaItem
- **R1.6** 修改 `ExoPlayerHelper.createMediaItem`：新增 `sniffedMimeType: String? = null` 参数，优先使用嗅探结果
- **R1.7** createMediaItem 优先级：sniffedMimeType > getMimeType(url) > null
- **R1.8** 日志：Tag=SniffingMime，记录 urlPath 前 40 字符 + 嗅探结果 + 耗时

### R2：自动 WebView 降级

- **R2.1** 在 `Exo2MediaPlayer.onPlayerError` 中累计失败次数（已有 retryCount，需区分可恢复 vs 不可恢复）
- **R2.2** 不可恢复错误类型：3002、3003、3004、ERROR_CODE_DECODER_INIT_FAILED、ERROR_CODE_DECODING_FAILED
- **R2.3** 失败次数 ≥3 + 不可恢复错误 → 通过 EventBus 发送 `VIDEO_FALLBACK_WEBVIEW` 事件（新增事件常量）
- **R2.4** `VideoPlayerActivity` 接收事件 → 调用 `VideoFragment.switchToWebViewMode`
- **R2.5** UI 提示："ExoPlayer 多次失败，已切换到 WebView 模式"
- **R2.6** 用户可点击 `btnSwitchBack` 切回 ExoPlayer 模式重试

### R3：getMimeType else 兜底 BUG 修复（已临时修复，纳入规范）

- **R3.1** L93 `else -> MimeTypes.APPLICATION_M3U8` → `else -> null`
- **R3.2** 注释说明修复原因和安全性（L57 已有判空）

### R4：日志和调试

- **R4.1** createMediaItem 日志增加嗅探来源标识（已有 mimeType 日志）
- **R4.2** 嗅探日志独立 Tag=SniffingMime
- **R4.3** 自动降级日志：Tag=ExoFallback，记录失败次数 + 错误码 + URL path 前 40 字符

## Scenarios（场景）

### Scenario 1：预嗅探覆盖 URL 后缀不可靠

```
URL: https://站点A/play.php?id=123 （实际返回 mp4 流，无 Content-Type）
↓
AnalyzeUrl.getMediaItem() 调用 sniffMimeType(url, headers)
↓
sniffMimeType 发 Range: bytes=0-1023 请求
↓
读取前 1KB → magic number "ftyp" → VIDEO_MP4
↓
缓存 url → VIDEO_MP4
↓
createMediaItem(url, headers, sniffedMimeType=VIDEO_MP4)
↓
setMimeType(VIDEO_MP4)
↓
ExoPlayer 正确解析 mp4 流
```

### Scenario 2：多类型混合源（用户反馈核心场景）

```
源 X 列表中:
  视频1 URL → sniffMimeType → "#EXTM3U" → APPLICATION_M3U8 → HlsMediaSource
  视频2 URL → sniffMimeType → "ftyp"     → VIDEO_MP4        → ProgressiveMediaSource
  视频3 URL → sniffMimeType → "FLV\x01"  → "video/x-flv"    → ProgressiveMediaSource

→ 每个视频独立嗅探,三种格式都能正确播放
```

### Scenario 3：缓存命中（二次播放）

```
二次播放同一 URL
↓
sniffMimeType 查缓存 → 命中 VIDEO_MP4
↓
直接返回 VIDEO_MP4 (0 网络请求,0 延迟)
↓
createMediaItem 使用缓存结果
```

### Scenario 4：自动 WebView 降级

```
ExoPlayer 播放失败 → errorCode=3002（不可恢复）
↓ retryCount=1
重试 seekToDefaultPosition + prepare
↓ 又失败 errorCode=3002
↓ retryCount=2
重试
↓ 又失败 errorCode=3002
↓ retryCount=3 ≥ MAX_RETRY
postEvent(VIDEO_FALLBACK_WEBVIEW, url + headers)
↓
VideoPlayerActivity 接收事件
↓
VideoFragment.switchToWebViewMode(url, title, headers)
↓
UI Toast: "ExoPlayer 多次失败，已切换到 WebView 模式"
```

### Scenario 5：嗅探失败回退

```
URL: https://站点B/redirect?url=xxx （302 重定向到实际视频地址）
↓
sniffMimeType 发 Range 请求 → 收到 302 响应（非视频内容）
↓
magic number 不匹配
↓
回退到 URL 后缀检测 → 不匹配
↓
回退到默认推断 → 返回 null
↓
ExoPlayer 用内置 Extractor.sniff() 尝试
```

### Scenario 6：可恢复错误不触发降级

```
ExoPlayer 播放失败 → errorCode=2001 IO_NETWORK_CONNECTION_FAILED（可恢复）
↓ retryCount=1
重试
↓ 成功
继续播放，不触发降级
```

### Scenario 7：服务端 Content-Type 正确（跳过嗅探）

```
URL: https://站点C/video.mp4 （服务端正确返回 Content-Type: video/mp4）
↓
sniffMimeType 先发 Range 请求 → 收到响应头 Content-Type: video/mp4
↓
直接使用服务端 Content-Type (跳过 magic number 检测)
↓
缓存 url → VIDEO_MP4
↓
createMediaItem 使用服务端返回的 MIME
```
