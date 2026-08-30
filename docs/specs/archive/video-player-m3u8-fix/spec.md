# m3u8/HLS 视频播放优化

## URL 实证分析

对用户提供的 m3u8 URL 进行了实际 WebFetch，获取到完整清单内容：

### 清单结构
- 标准 HLS VOD，`#EXT-X-VERSION:3`
- **AES-128 加密**：`#EXT-X-KEY:METHOD=AES-128,URI="/ckey/{hash}.bin"`
  - 密钥 URI 是**相对路径**，ExoPlayer 解析为 `https://{m3u8域名}/ckey/{hash}.bin`
  - **密钥 URL 直接访问失败**（WebFetch 返回错误），说明密钥可能需要特定请求头/Referer/鉴权
- 11 个 TS 分片，位于**不同域名**（站点B），每个分片带 `md=` 鉴权参数
- `#EXT-X-ENDLIST` 表示 VOD（非直播）

### 关键发现：5 个根因

1. **P0：sniffVideoType Range 请求不必要且有害**
   - 当前对所有视频 URL 均执行 Range 嗅探（`bytes=0-8191`），m3u8 URL 完全不需要
   - 对 m3u8 发 Range 请求可能：消耗 CDN 一次性 token / 触发 CDN 限流 / 增加 500ms-3s 延迟
   - `.m3u8` 后缀即可 100% 确定是 HLS，Range 嗅探是纯浪费

2. **P0：AES-128 密钥请求缺少防盗链 Header**
   - m3u8 使用 AES-128 加密，ExoPlayer 需下载 `/ckey/{hash}.bin` 密钥文件
   - 当前 `applyMediaSourceByType` 创建 HlsMediaSource 时使用 `ExoPlayerHelper.resolvingDataSource`
   - `resolvingDataSource` 仅处理 SPLIT_TAG URL 的 Header 注入，HLS 内部请求（密钥+TS分片）**无任何 Header**
   - 如果密钥服务器需要 Referer/Cookie/UA 防盗链，密钥请求将 403 → ExoPlayer 无法解密 → 播放失败
   - **这是 AES-128 加密 m3u8 播放失败的最可能直接原因**

3. **P1：Cache-Control: max-age=86400 请求头干扰 CDN**
   - `okhttpDataFactory.setCacheControl(CacheControl.Builder().maxAge(1, TimeUnit.DAYS).build())`
   - 所有视频请求（m3u8 清单+密钥+TS分片）都携带 `Cache-Control: max-age=86400`
   - 部分 CDN 对客户端发送 Cache-Control 请求头返回异常响应或触发限流
   - 密钥请求被 Cache-Control 影响更严重（密钥应永不缓存）

4. **P2：HLS fallback 链冗余**
   - 降级链 `[HLS, HLS, DASH]`：第二个 HLS 完全相同必然失败；DASH 对 m3u8 无意义
   - 每次无效降级浪费 12-25 秒 BUFFERING 超时等待

5. **P2：HLS 分片加载重试策略不足**
   - 当前 `DefaultLoadErrorHandlingPolicy` 固定 3s 重试延迟，无上限
   - 网络抖动时 3s 可能不够恢复；CDN 永久失效时无上限重试导致无法降级

## Intent

m3u8 格式在线视频地址无法播放，根因是 AES-128 加密 m3u8 的密钥请求缺少防盗链 Header，加上不必要的 Range 嗅探和 Cache-Control 干扰。

## Scope

### IN

- m3u8/HLS 嗅探优化（短路嗅探）
- **HLS 内部请求（密钥+TS分片）Header 注入**（P0 修复）
- HLS MediaSource 创建增强
- HLS 分片加载容错（重试策略）
- 降级链优化（去重 + 合理降级顺序）
- okhttpDataFactory Cache-Control 请求头移除

### OUT

- 不修改 WebView 降级播放器逻辑
- 不修改书源规则引擎
- 不修改外部播放器逻辑

## Approach

### Selected Approach

5 项修复，按优先级排序：

**P0-1：m3u8 URL 短路嗅探**：URL 以 `.m3u8` 结尾时跳过 Range 嗅探，直接返回 `SniffResult(contentType=C.TYPE_HLS, mimeType=APPLICATION_M3U8)`。标准 m3u8 URL 无需 Range 嗅探，跳过可避免消耗 CDN token 和增加延迟。

**P0-2：HLS 内部请求 Header 注入**：在 `applyMediaSourceByType` 创建 HlsMediaSource 前，调用 `ExoPlayerHelper.setDefaultHeaders(currentHeaders)` 将防盗链 Header 注入 `okhttpDataFactory`。这样 ExoPlayer 下载 AES-128 密钥和 TS 分片时，所有 HTTP 请求都会携带 Referer/Cookie/UA。

**P1：移除 Cache-Control**：移除 `okhttpDataFactory` 的 `setCacheControl` 配置。视频缓存由 ExoPlayer SimpleCache 层处理，OkHttp HTTP 缓存对视频流无价值，且 Cache-Control 可能干扰 CDN 密钥请求。

**P2-1：fallback 去重**：将降级链从 `[HLS, HLS, DASH]` 改为 `[HLS, Progressive]`。第二次 HLS 无意义；DASH 对 m3u8 无降级价值。Progressive 降级可覆盖某些 CDN 的 .m3u8 URL 实际返回 mp4 流的场景。

**P2-2：分片重试**：HlsMediaSource 的 LoadErrorHandlingPolicy 采用指数退避（1s/2s/4s/8s/16s），最多重试 5 次后放弃。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 用 HlsMediaSource.Factory.setDefaultRequestProperties 注入 Header | media3 1.10.1 的 HlsMediaSource.Factory 无此 API，只能通过 DataSource.Factory 注入 |
| 为 HLS 创建独立 DataSource.Factory | 过度设计，okhttpDataFactory.setDefaultRequestProperties 已满足需求 |
| 用 IJKPlayer 替代 ExoPlayer | IJKPlayer 维护停滞，ExoPlayer 是官方推荐方案 |
| 仅依赖 WebView 降级 | 不解决根因，用户无法原生播放 |

### Drawbacks

- 短路嗅探可能跳过对非标 m3u8 的验证（如 .m3u8 后缀但实际是 HTML 错误页），但 ExoPlayer 内置 HLS 解析器会在 prepare 阶段检测 `#EXTM3U` 头，非标 m3u8 会快速失败进入降级链
- setDefaultHeaders 是全局设置，多播放器并发可能互相覆盖。当前场景为单播放器，可接受。升级路径：per-request Header 注入
- fallback 去重后只有 2 级降级（HLS→Progressive），DASH 降级被移除，但 DASH 场景已在 DASH 嗅探成功路径覆盖
- 移除 Cache-Control 可能降低缓存效率，但视频流本身已有 SimpleCache 缓存层

### Prior Art

- **ExoPlayer 官方 HLS 播放指南**：推荐 `setAllowChunklessPreparation(true)` + 自定义 LoadErrorHandlingPolicy
- **hls.js**：HLS 分片加载失败指数退避重试策略
- **抖音/快手**：m3u8 URL 直接短路到 HLS 源，不做 Range 嗅探
- **影视仓/CatVod**：HLS 内部请求复用原始页面的 Referer/Cookie

## Requirements

- **REQ-1**：URL 以 .m3u8 结尾时短路嗅探，直接创建 HlsMediaSource
- **REQ-2**：HLS 内部请求（AES-128 密钥+TS 分片）携带防盗链 Header（Referer/Cookie/UA）
- **REQ-3**：HLS fallback 链去重，改为 [HLS, Progressive]
- **REQ-4**：HLS 分片加载失败重试策略增强（指数退避 + 最大重试次数）
- **REQ-5**：移除 okhttpDataFactory 的 Cache-Control 请求头
- **REQ-6**：确保短路嗅探不影响动态 URL（play.php?format=m3u8）的嗅探路径

## Scenarios

### 场景1：AES-128 加密 m3u8（本问题的核心场景）

- **输入**：URL 以 `.m3u8` 结尾，清单含 `#EXT-X-KEY:METHOD=AES-128`
- **流程**：短路嗅探 → setDefaultHeaders 注入防盗链 Header → ExoPlayer 下载 m3u8 → 下载 AES-128 密钥（携带 Header）→ 解密 TS 分片 → 播放成功
- **预期**：密钥请求携带 Referer/Cookie 成功获取密钥，ExoPlayer 解密后播放

### 场景2：CDN 一次性 token m3u8 URL

- **输入**：URL 含一次性鉴权 token，以 `.m3u8` 结尾
- **流程**：短路嗅探（不消耗 token）→ 实际播放时 URL 有效 → 播放成功
- **预期**：避免嗅探请求消耗 token，播放请求使用有效 token 成功

### 场景3：动态 URL 返回 m3u8

- **输入**：动态 URL（如 `play.php?format=m3u8`），不以 `.m3u8` 结尾
- **流程**：走 Range 嗅探路径 → 响应头/内容识别为 HLS → 创建 HlsMediaSource → 播放成功
- **预期**：短路嗅探不影响动态 URL 的正常嗅探流程

### 场景4：非标 .m3u8（HTML 错误页）

- **输入**：URL 以 `.m3u8` 结尾，但实际返回 HTML 错误页
- **流程**：短路创建 HlsMediaSource → ExoPlayer 解析失败（缺少 `#EXTM3U` 头）→ 进入降级链 Progressive → 失败 → 降级 WebView
- **预期**：快速失败并降级，不卡在嗅探阶段

### 场景5：无加密 m3u8

- **输入**：URL 以 `.m3u8` 结尾，清单无 `#EXT-X-KEY`
- **流程**：短路嗅探 → ExoPlayer 下载 m3u8 → 直接下载 TS 分片 → 播放成功
- **预期**：跳过 Range 嗅探，减少延迟，播放流畅
