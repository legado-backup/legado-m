# spec.md — 内置视频抓取能力增强

## Intent

增强订阅源（RssSource type=2）内置视频播放器的"自动抓取视频链接"能力，在现有静态 DOM 解析（`VideoUrlExtractor.extract`）失败后，新增"BackstageWebView 网络抓包拦截"降级层，使内置抓取能力**超越**用户手填 V1/V2 HTML 内容规则（核心是 `java.webViewGetSource` 网络抓包）的水平——本方案新增 shouldInterceptRequest 拦截 fetch/XHR（V2 模板没有）、5路 JS hook、多格式支持、Referer 自动注入，覆盖面更广。

**最终目的**（明确边界，避免过度承诺）：
1. **大部分场景（90%+ 非 DRM）**：ruleContent 为空时内置抓取已足够，用户无需手填 V1/V2 内容规则
2. **特殊场景仍需用户手填**（浏览器视频抓取的固有边界，V2 模板同样无法解决）：
   - DRM 加密站点：三类抓取逻辑均无效
   - 需要登录的站点：本方案不处理登录态（需源配置登录规则）
   - 需要 JS 逆向的站点：本方案不实现第三类"轻量 JS 逆向"
3. 替换掉底层兜底到 WebView HTML 模板的播放降级方式（抓取阶段就拿到真实 URL，不需要再用 WebView 播放）

**核心原理**（用户给出的浏览器视频抓取三类逻辑）：
1. DOM 解析（已实现）
2. 网络抓包拦截（**本 spec 实现**，含 shouldInterceptRequest + onLoadResource + JS hook + Performance API 四路监听）
3. 轻量 JS 逆向（未来增强，本 spec 不做）

## Scope

### In Scope（本 spec 修改范围）

| 文件 | 修改内容 |
|------|---------|
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 新增 `extractWithWebView(url, source, headerMap, delayTime)` 方法，封装 BackstageWebView 网络抓包调用 |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 改造 L304-325 else 分支：静态解析失败后调用 `extractWithWebView`，成功则播放，失败才回退文章链接 |

### Out of Scope（本 spec 不修改）

- ✅ `BackstageWebView.kt`（增强 SnifferWebClient：新增 shouldInterceptRequest 拦截 fetch/XHR + onPageStarted JS注入 + ReadVideoUrlsRunnable 读取 window.__videoUrls__，新增构造参数 interceptAllRequests + videoSniffJs）
- ❌ `hls_video_player_template.html`（播放降级模板，非抓取降级）
- ❌ `JsExtensions.kt` 的 `webViewGetSource`（VideoPlay 非 JS 上下文，直接构造 BackstageWebView）
- ❌ V1/V2 用户自定义内容规则处理逻辑（ruleContent 非空分支不动）
- ❌ ExoPlayer 播放逻辑（提取到 URL 后仍交给 ExoPlayer）

## Approach

### 三层抓取架构

```
第一层：DOM 解析（VideoUrlExtractor.extract 5种方法，已有，快速 <100ms）
├── 成功（size >= 1）→ 传给 ExoPlayer 播放
└── 失败（size == 0）→ 第二层
    第二层：网络抓包拦截（BackstageWebView + sourceRegex，新增，慢 3-15s）
    ├── 成功（返回 URL）→ 传给 ExoPlayer 播放
    └── 失败（超时/无匹配）→ 第三层
        第三层：回退文章链接 + 提示用户（保留原有兜底，必失败但有日志）
```

### 关键设计点

1. **直接构造 BackstageWebView**：VideoPlay 不是 JS 执行上下文，不通过 `JsExtensions.webViewGetSource` 调用，而是直接 `BackstageWebView(url=..., sourceRegex=..., headerMap=..., tag=..., delayTime=..., timeout=...).getStrResponse()`
2. **不是用 WebView 播放**：BackstageWebView 仅用于加载页面 + 拦截网络请求提取 URL，提取到 URL 后立即销毁，URL 传给 ExoPlayer 播放
3. **delayTime**：等待 JS 动态加载视频地址（默认 3000ms），让播放器 JS 有时间发起 m3u8 请求
4. **headerMap**：复用 `AnalyzeUrl(rssArticle.link, source=source).headerMap`，注入防盗链 Referer/User-Agent 等
5. **线程安全**：BackstageWebView 必须在后台线程调用，VideoPlay.kt L253 已在 `Coroutine.async(loadScope, IO)` 中，满足要求
6. **sourceRegex 优化**：匹配 m3u8/mp4/flv/ts 等主流视频格式，兼容带 query 参数（防盗链 token）的 URL
7. **超时控制**：BackstageWebView 默认 60s 太长，本 spec 缩短到 15s（视频抓取场景合理阈值）
8. **取消支持**：用户退出播放器时 `loadScope.coroutineContext.cancelChildren()` 已会取消协程，BackstageWebView 的 `suspendCancellableCoroutine` 会触发 `destroy()`

### 实现位置

- **VideoPlay.kt L304 else 分支改造**：
  ```kotlin
  else -> {
      // 第二层：网络抓包拦截降级
      AppLog.putInfo("R5静态解析未命中，启动网络抓包拦截: ${rssArticle.link}")
      val webViewUrl = VideoUrlExtractor.extractWithWebView(
          url = rssArticle.link,
          source = source,
          delayTime = 3000L,
          timeout = 15000L
      )
      if (webViewUrl != null) {
          // 网络抓包成功，走单 URL 播放流程
          AppLog.putInfo("R5网络抓包命中: $webViewUrl")
          // ... 构造 AnalyzeUrl + setUp + startPlayLogic
      } else {
          // 第三层：回退文章链接（原有逻辑）
          AppLog.putWarn("R5网络抓包未命中，回退文章链接: ${rssArticle.link}")
          // ... 原有 L307-324 逻辑
      }
  }
  ```

- **VideoUrlExtractor.kt 新增方法**：
  ```kotlin
  /**
   * 第二层抓取：BackstageWebView 网络抓包拦截
   * 加载文章页面，监听浏览器网络请求，正则匹配视频流 URL
   */
  suspend fun extractWithWebView(
      url: String,
      source: BaseSource?,
      delayTime: Long = 3000L,
      timeout: Long = 15000L
  ): String? {
      // 构造 AnalyzeUrl 获取 headerMap（防盗链 Referer 等）
      val analyzeUrl = AnalyzeUrl(url, source = source, ruleData = null)
      val headerMap = HashMap(analyzeUrl.headerMap)
      // 注入 Referer（模拟 WebView 行为）
      if (!headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
          headerMap["Referer"] = url
      }
      return runCatching {
          BackstageWebView(
              url = url,
              headerMap = headerMap,
              tag = source?.getKey(),
              sourceRegex = VIDEO_SOURCE_REGEX,
              delayTime = delayTime,
              timeout = timeout,
              interceptAllRequests = true,   // 启用 shouldInterceptRequest 拦截 fetch/XHR
              videoSniffJs = VIDEO_SNIFF_JS   // 注入 JS 覆写 fetch/XHR
          ).getStrResponse().body
      }.onFailure {
          AppLog.putWarn("R5网络抓包失败: ${url}", it)
      }.getOrNull()
  }
  
  companion object {
      // 视频流 URL 正则：参考 Fongmi/TV Sniffer.java 的 SNIFFER 正则
      // 匹配 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd + video/tos + rtmp，URL长度≥12
      val VIDEO_SOURCE_REGEX = """(?i).*(?:https?://[^\s]{12,}\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?.*)?|https?://.*?video/tos[^\s]*|rtmp:[^\s]+).*"""
  }
  ```

## Alternatives Considered

### 方案 A：直接降级到 WebView HTML 模板播放（否决）

- **思路**：静态解析失败后，直接用 `hls_video_player_template.html` 加载文章 URL 用 WebView 播放
- **否决原因**：用户明确反馈"最终目的是替换掉底层兜底到 WebView HTML 模板的方式"。WebView 播放体验差（无法用 ExoPlayer 的缓存/倍速/弹幕/进度记忆），且本 spec 的目标是"抓取降级"不是"播放降级"
- **保留关系**：`hls_video_player_template.html` 作为 ExoPlayer 播放失败后的最终降级保留（现有逻辑），本 spec 不动

### 方案 B：静态解析 + 网络抓包拦截双层（采纳）

- **思路**：第一层 DOM 解析（已有）失败后，第二层 BackstageWebView 网络抓包拦截（新增），第三层回退文章链接（保留）
- **采纳原因**：
  1. 复用已有 BackstageWebView 能力，无需新造轮子
  2. 与用户手填 V2 模板的 `java.webViewGetSource` 能力等价
  3. 抓取与播放职责分离，提取到 URL 后仍交给 ExoPlayer 播放
  4. 三层降级清晰，每层有日志可观测
- **代价**：WebView 抓取较慢（需加载页面 3-15s），但仅在网络抓包场景触发（静态解析失败时）

### 方案 C：全面重构含 JS 逆向（否决）

- **思路**：实现完整的浏览器视频抓取三类逻辑，包括第三类"轻量 JS 逆向"
- **否决原因**：
  1. 范围过大，JS 逆向需要解析播放器脚本逻辑，工作量大且站点适配性差
  2. 第二类"网络抓包拦截"已能覆盖 90%+ 非 DRM 场景，投入产出比低
  3. 本 spec 聚焦"补齐与用户手填 V2 模板同等能力"，JS 逆向留待未来增强

## Drawbacks

1. **性能开销**：BackstageWebView 抓取需要加载完整页面（3-15s），比静态解析（<100ms）慢 30-150 倍。但仅在网络抓包场景触发（静态解析失败时），且用户手填 V2 模板也是同样开销
2. **DRM 加密场景无效**：三类抓取逻辑对 DRM 加密视频均无效，需用户手填解密规则。本 spec 不解决 DRM 场景
3. **内存占用**：BackstageWebView 加载页面会占用额外内存（WebView 实例 + 页面资源），但抓取完成后立即 `destroy()` 释放
4. **站点兼容性**：部分站点检测 WebView UA 拒绝服务，需通过 headerMap 注入自定义 UA（已支持）
5. **超时风险**：15s 超时可能对部分慢站点不够，但已预留 `timeout` 参数可调

## Requirements

### R1：网络抓包拦截降级

**需求**：静态 DOM 解析失败后，调用 BackstageWebView 加载文章页面，监听浏览器网络请求，正则匹配视频流 URL。

**验收标准**：
- `VideoPlay.kt` L304 else 分支不再直接回退文章链接，而是先调用 `VideoUrlExtractor.extractWithWebView`
- `extractWithWebView` 返回非空 URL 时，走单 URL 播放流程（AnalyzeUrl + setUp + startPlayLogic）
- `extractWithWebView` 返回 null 时，才回退文章链接（原有逻辑）
- BackstageWebView 仅用于抓取，提取到 URL 后立即销毁，URL 传给 ExoPlayer 播放

### R2：sourceRegex 正则优化（基于 Fongmi/TV SNIFFER）

**需求**：参考业界成熟方案扩展正则匹配范围，覆盖主流流媒体格式 + 降低误匹配。

**验收标准**：
- 正则模式：`(?i).*(?:https?://[^\s]{12,}\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?.*)?|https?://.*?video/tos[^\s]*|rtmp:[^\s]+).*`（参考 Fongmi/TV Sniffer.java SNIFFER 正则）
- 格式覆盖：m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd + video/tos（抖音）+ rtmp（直播）
- URL 长度 ≥12 约束（`[^\s]{12,}`）过滤短 URL 误匹配
- 移除 .ts（避免 HLS 分片先于 m3u8 主playlist 被捕获，ExoPlayer 需 m3u8 主索引）
- isVideoFormat 多层判断：shouldInterceptRequest 内排除嵌套URL（url=http / v=http / .html）
- 大小写不敏感（`(?i)` 前缀）
- 兼容带防盗链 token 的 URL（如 `https://cdn.example.com/video.m3u8?token=xxx&expires=yyy`）
- 正则定义为 `VideoUrlExtractor.VIDEO_SOURCE_REGEX` 常量，便于后续调整

### R3：抓取日志可观测

**需求**：三层抓取每层命中/失败需记录 AppLog，便于用户排查。

**验收标准**：
- 第一层 DOM 解析：`extract()` 已有日志（VideoPlay.kt L306），保留
- 第二层网络抓包：
  - 启动时：`AppLog.putInfo("R5静态解析未命中，启动网络抓包拦截: {url}")`
  - 成功时：`AppLog.putInfo("R5网络抓包命中: {url}")`（URL 脱敏，只保留路径模式）
  - 失败时：`AppLog.putWarn("R5网络抓包失败: {url}", throwable)`
  - 超时时：`AppLog.putWarn("R5网络抓包超时: {url}")`
- 第三层回退：`AppLog.putWarn("R5网络抓包未命中，回退文章链接: {url}")`
- 日志安全：禁止输出完整 URL/视频域名/敏感字段，只保留路径模式（详见输出安全规范）

### R4：防盗链 Header 注入

**需求**：BackstageWebView 加载文章页面需注入 Referer/User-Agent 等防盗链 Header。

**验收标准**：
- `extractWithWebView` 内部构造 `AnalyzeUrl(url, source=source)` 获取 headerMap
- 若 headerMap 中无 Referer，自动注入 `Referer: {url}`（模拟 WebView 行为）
- headerMap 传递给 BackstageWebView 构造参数 `headerMap`
- User-Agent 复用 `AppConfig.userAgent`（BackstageWebView L168 已支持从 headerMap 读取 UA）

### R5：抓取超时与取消

**需求**：BackstageWebView 抓取超时缩短到合理阈值，支持用户退出播放器时取消。

**验收标准**：
- `extractWithWebView` 默认超时 15000ms（15s），可通过参数调整
- BackstageWebView 构造参数 `timeout = 15000L`
- 用户退出播放器时 `VideoPlay.stopLoading()` 调用 `loadScope.coroutineContext.cancelChildren()`，协程取消会触发 BackstageWebView 的 `suspendCancellableCoroutine.invokeOnCancellation` 执行 `destroy()`
- 超时/取消时不崩溃，返回 null 走第三层回退

## Scenarios

### S1：静态解析成功（不触发网络抓包）

**前置**：订阅源文章页面 HTML 包含 `<video src="https://cdn.example.com/v.mp4">`

**流程**：
1. VideoPlay.kt L265 `VideoUrlExtractor.extract(html, link)` 返回 `[https://cdn.example.com/v.mp4]`
2. size == 1，走单 URL 播放分支
3. 不触发第二层网络抓包

**预期**：ExoPlayer 正常播放，AppLog 无网络抓包日志

### S2：静态解析失败 + 网络抓包成功（核心场景）

**前置**：订阅源文章页面 HTML 无 video 标签，但 JS 动态加载 `https://cdn.example.com/index.m3u8`

**流程**：
1. VideoPlay.kt L265 `VideoUrlExtractor.extract(html, link)` 返回 `[]`（size == 0）
2. 进入 L304 else 分支
3. 调用 `VideoUrlExtractor.extractWithWebView(url=link, source=source, delayTime=3000)`
4. BackstageWebView 加载页面，3s 后 JS 发起 m3u8 请求
5. `SnifferWebClient.onLoadResource` 匹配 `.*\.m3u8.*`，返回 `https://cdn.example.com/index.m3u8`
6. 走单 URL 播放分支，ExoPlayer 播放

**预期**：
- AppLog: `R5静态解析未命中，启动网络抓包拦截: {url}`
- AppLog: `R5网络抓包命中: {url}`
- ExoPlayer 正常播放 m3u8

### S3：静态解析失败 + 网络抓包也失败（回退场景）

**前置**：订阅源文章页面是 DRM 加密视频，无任何可抓取的明文 URL

**流程**：
1. `VideoUrlExtractor.extract` 返回 `[]`
2. 进入 else 分支
3. 调用 `extractWithWebView`，15s 超时未匹配到视频 URL
4. 返回 null
5. 走第三层回退，用文章链接交给 ExoPlayer（必然失败，但有完整日志）

**预期**：
- AppLog: `R5静态解析未命中，启动网络抓包拦截: {url}`
- AppLog: `R5网络抓包超时: {url}`
- AppLog: `R5网络抓包未命中，回退文章链接: {url}`
- ExoPlayer 播放失败（UnrecognizedInputFormatException），触发 WebView 降级弹窗（现有逻辑）

### S4：用户退出播放器时取消抓包

**前置**：网络抓包进行中（已加载 2s），用户点击返回退出播放器

**流程**：
1. `extractWithWebView` 协程正在 `BackstageWebView.getStrResponse()` 挂起
2. 用户退出，`VideoPlay.releaseAllVideos()` → `stopLoading()` → `loadScope.coroutineContext.cancelChildren()`
3. 协程取消，`suspendCancellableCoroutine.invokeOnCancellation` 触发 `destroy()` 销毁 WebView
4. 不崩溃，播放器正常退出

**预期**：无崩溃，AppLog 无异常（取消是正常行为）

### S5：防盗链场景

**前置**：订阅源文章页面需要 Referer 才能加载，CDN 视频 URL 需要 Referer 才能播放

**流程**：
1. `extractWithWebView` 构造 `AnalyzeUrl(url, source=source)` 获取 headerMap（含源的 Referer 配置）
2. 若 headerMap 无 Referer，自动注入 `Referer: {url}`
3. BackstageWebView 加载页面时注入 headerMap，绕过防盗链
4. 抓取到 m3u8 URL 后，VideoPlay.kt 单 URL 分支再次构造 AnalyzeUrl 注入 Referer 给 ExoPlayer

**预期**：BackstageWebView 成功加载页面，ExoPlayer 成功播放（不 403/404）
