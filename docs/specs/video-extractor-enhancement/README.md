# 内置视频抓取能力增强（video-extractor-enhancement）

> **状态**：🔄 开发中（代码实施完成，编译+L1通过，待L2真机验证）
> **创建日期**：2026-07-13
> **前置 spec**：rss-video-player-enhancement（R5 已实施，本 spec 为 R5 的能力补强）
> **设计优化记录**（2026-07-13）：
> - 优化1：补全 `window.__videoUrls__` 读取逻辑（ReadVideoUrlsRunnable），原方案 VIDEO_SNIFF_JS 注入了 hook 但无读取逻辑
> - 优化2：delayTime 从 onPageFinished 开始计时（自适应慢站点）
> - 明确预期收益边界：90%+ 非 DRM 场景可替代用户内容规则，DRM/登录/JS 逆向仍需手填
> **实施调整记录**（2026-07-13，详见 tasks.md AOAdapt 日志）：
> - AOAdapt-1：JSON 解析库从 kotlinx.serialization.json.Json 改为项目统一的 GSON（项目未引入 kotlinx-serialization-json 库，编译报错后发现）
> - AOAdapt-2：else 分支成功路径变量命名统一为 playAnalyzeUrl（与单 URL 分支一致，提高可读性）

## 功能概述

针对订阅源（RssSource type=2）内置视频播放器的"自动抓取视频链接"能力进行增强，补齐用户反馈的"内置抓取效果不如用户手填 V1/V2 HTML 内容规则"的短板。

当前 `VideoUrlExtractor` 仅实现了浏览器视频抓取三类逻辑中的**第一类（DOM 解析）**，缺失**第二类（网络抓包拦截）**这一核心能力。当静态 DOM 解析失败时（`VideoPlay.kt` L304 else 分支），直接回退用文章页面 URL 交给 ExoPlayer，必然播放失败。用户为了规避该问题，被迫手填 V1/V2 HTML 模板（核心是 `java.webViewGetSource(null, baseUrl, null, ".*\\.m3u8.*")` 网络抓包能力）。

本 spec 通过在静态解析失败后增加"BackstageWebView 网络抓包拦截"降级层，使内置抓取能力达到与用户手填 V2 模板同等水平，最终目标是**替换掉用户输入内容规则**，以及**替换底层兜底到 WebView HTML 模板的播放降级方式**。

## 核心能力

| 编号 | 能力 | 核心问题 |
|------|------|---------|
| **R1** | 网络抓包拦截降级 | 静态 DOM 解析失败后直接回退文章 URL 必然播放失败；需调用 BackstageWebView 加载页面并拦截浏览器网络请求，正则匹配 m3u8/mp4/flv/ts 等视频流 URL |
| **R2** | sourceRegex 正则优化 | 当前正则仅匹配 m3u8/mp4，需扩展支持 flv/ts/ts 分片等主流流媒体格式，并兼容带 query 参数（防盗链 token）的 URL |
| **R3** | 抓取日志可观测 | 抓取三层（DOM/网络抓包/回退）每层命中/失败需记录 AppLog，便于用户排查"为什么没抓到"和后续规则优化 |
| **R4** | 防盗链 Header 注入 | BackstageWebView 加载文章页面需注入 Referer/User-Agent 等防盗链 Header，复用 AnalyzeUrl 构造的 headerMap |
| **R5** | 抓取超时与取消 | BackstageWebView 默认超时 60s 太长，视频抓取场景需缩短到合理阈值（15s），并支持用户退出播放器时取消抓取 |

## 根因分析

### 浏览器视频抓取三类逻辑（用户给出的核心原理）

1. **DOM 解析**：读取 HTML5 视频标签，捕获静态视频地址；监听 JS 异步接口回调，获取动态赋值的媒体地址
2. **网络抓包拦截**：监听浏览器全部网络请求，筛选视频/流媒体索引文件等媒体资源请求，精准提取真实 CDN 地址与分片地址，可绕过前端地址混淆、Blob 地址封装等伪装手段
3. **轻量 JS 逆向**：解析播放器脚本逻辑，还原流媒体分片完整链接

抓取失败仅存在于 DRM 加密场景。带时效 token、防盗链校验的视频，地址本身真实有效，不影响抓取成功率。

### 当前架构缺陷

| 层级 | 当前实现 | 缺陷 |
|------|---------|------|
| 第一层 DOM 解析 | `VideoUrlExtractor.extract()` 5 种方法 | ✅ 已实现，但仅覆盖静态 HTML |
| 第二层 网络抓包拦截 | ❌ 未实现 | `VideoUrlExtractor.kt` L20 注释明确"不实现 XHR/Fetch 拦截"；`VideoPlay.kt` L304 else 分支直接回退用文章链接 |
| 第三层 回退 | 用文章页面 URL 交给 ExoPlayer | ⚠️ 文章页面是 HTML 不是视频流，ExoPlayer 必然抛 `UnrecognizedInputFormatException` |

### V2.html 模板的核心能力（用户手填方案）

```html
<js>
java.webViewGetSource(null, baseUrl, null, ".*\\.m3u8.*")
</js>
```

- `BackstageWebView` 加载页面 + JS 执行 + 正则匹配网络请求中的 m3u8 地址
- 这是"网络抓包拦截"能力，不是"用 WebView 播放"
- 用户被迫手填此模板，是因为内置抓取缺失这一层

### BackstageWebView 已有实现（可直接复用）

- `JsExtensions.kt` L241-264：`webViewGetSource(html, url, js, sourceRegex, cacheFirst, delayTime)`
- `BackstageWebView.kt` L53-67：构造参数 `url/html/headerMap/tag/sourceRegex/javaScript/delayTime/cacheFirst/timeout`
- `BackstageWebView.kt` L357-369：`SnifferWebClient.onLoadResource` 中 sourceRegex 匹配 resUrl，匹配则返回 `StrResponse(url, resUrl)`
- 必须在后台线程调用（`JsExtensions.kt` L249-251 主线程检测）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach（含 Alternatives Considered + Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions（ADR Y-Statement）/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 9 个 Section 的任务清单 |

## 关键源码锚点

| 文件 | 角色 |
|------|------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 视频播放管理单例；**改造点 L304-325 else 分支**：静态解析失败后调用 BackstageWebView 网络抓包 |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 视频URL提取器；**新增 `extractWithWebView(url, source)` 方法**封装 BackstageWebView 调用 |
| `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` | 后台 WebView；**增强 SnifferWebClient**：新增 shouldInterceptRequest 拦截 fetch/XHR + onPageStarted JS注入 + ReadVideoUrlsRunnable 读取 window.__videoUrls__，新增构造参数 interceptAllRequests + videoSniffJs |
| `app/src/main/java/io/legado/app/help/JsExtensions.kt` | JS 扩展；L241-264 `webViewGetSource` 参考（不直接调用，VideoPlay 非 JS 上下文） |
| `app/src/main/assets/hls_video_player_template.html` | WebView 播放降级模板；**不修改**（本 spec 是抓取降级，不是播放降级） |

## 预期收益

1. **用户体验**：内置抓取成功率从"仅静态页面有效"提升到"覆盖 90%+ 非 DRM 场景"，大部分场景用户无需手填 V1/V2 模板
   - ✅ 非 DRM 站点：内置抓取比 V2 模板更强（shouldInterceptRequest 拦截 fetch/XHR + JS hook + 多格式 + Referer 注入），用户无需手填
   - ⚠️ DRM 加密站点：三类抓取逻辑均无效，用户需手填解密规则（浏览器视频抓取的固有边界）
   - ⚠️ 需要登录的站点：本方案不处理登录态，用户需在源配置登录规则（非内容规则）
   - ⚠️ 需要 JS 逆向的站点：本方案不实现第三类"轻量 JS 逆向"，用户需手填内容规则
2. **代码简化**：未来可移除 `hls_video_player_template.html` 兜底播放降级（本 spec 不做，留待下个 spec）
3. **可观测性**：三层抓取日志完整，便于定位"为什么这个源抓不到"
4. **架构清晰**：抓取（VideoUrlExtractor）与播放（ExoPlayer）职责分离，BackstageWebView 仅用于抓取不用于播放
5. **兜底保障**：三路监听（shouldInterceptRequest 实时 + onLoadResource 实时 + window.__videoUrls__ 延迟读取）+ Performance API 兜底，最大化抓取成功率

## 非目标

- ❌ 不实现第三类"轻量 JS 逆向"（范围过大，未来增强）
- ❌ 不修改 `hls_video_player_template.html`（那是播放降级，不是抓取降级）
- ❌ 不替换 ExoPlayer 为 WebView 播放（提取到 URL 后仍交给 ExoPlayer）
- ❌ 不修改 V1/V2 用户自定义内容规则的处理逻辑（仅增强 ruleContent 为空时的内置抓取）
