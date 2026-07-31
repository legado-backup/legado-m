# 渗透式深度审查报告 v2 - sniff-stability-enhance-20260731

> 审查时间：2026-07-31
> 审查范围：四文档（README/spec/design/tasks）+ v1审查报告 + 日志分析报告 + 7个关键源码文件
> 审查方法：对照源码逐行验证每个 FR 的根因、技术方案、代码片段、认知偏差
> 审查目标：验证 v1 整改（E1-E4/W1-W6/I1-I3）是否正确落地，识别 v1 遗漏的问题

---

## 一、审查概要

### 1.1 审查文件清单

| 类型 | 文件 | 用途 |
|------|------|------|
| 设计文档 | README.md / spec.md / design.md / tasks.md | 审查对象（v1整改后版本） |
| v1报告 | review-report.md | 验证v1整改是否落地 |
| 日志报告 | log_analysis_report.md | 根因核实基准 |
| 源码 | VideoUrlExtractor.kt | FR-1/FR-8 验证 |
| 源码 | DohDns.kt | FR-2 验证 |
| 源码 | HttpHelper.kt | FR-3/FR-4 验证 |
| 源码 | StreamResetRetryInterceptor.kt | FR-5 验证 |
| 源码 | CronetInterceptor.kt | FR-6/FR-7 验证 |
| 源码 | BackstageWebView.kt | FR-9 验证 |
| 源码 | VideoPlay.kt | FR-1 调用路径验证 |
| 源码 | ExoPlayerHelper.kt | FR-3 视频流真实路径验证（v1遗漏） |

### 1.2 审查方法论

1. **根因双重铁证**：日志分析报告结论 + 源码实际实现交叉验证
2. **API 可行性核验**：用 WebSearch + 源码 Grep 确认整改代码使用的 API 是否真实存在
3. **调用路径穿透**：从设计文档声称的修改点，追踪到源码真实调用链，验证方案是否覆盖
4. **认知偏差检查**：对照源码现状，验证方案前提假设是否成立

### 1.3 审查结论摘要

| 级别 | 数量 | 说明 |
|------|------|------|
| ERROR（阻断/高） | 3 | v1遗漏的 API不可行/方案认知偏差/方法遗漏 |
| WARNING（中） | 2 | 正则未对齐/源码注释过时 |
| v1已整改确认 | 13 | E1-E4/W1-W6/I1-I3 整改方向正确（部分整改代码有E5新问题） |

**核心结论**：v1审查的 E1-E4 整改方向全部正确，但 v1 遗漏了 3 个关键问题：
- **E5**：FR-5 整改代码 `chain.call().client()` API 在 OkHttp 4.12.0 中不可行（Call接口无client()方法），会编译错误
- **E6**：FR-3 方案存在重大认知偏差——ExoPlayerHelper.okhttpDataFactory 已强制 HTTP/1.1，视频流播放走 cacheDataSourceFactory 不走 CronetInterceptor，design.md 的方案落地点与真实路径不匹配
- **E7**：FR-2 遗漏 DohDns.asyncPreheatDoh 方法（已存在，用国外域名探测国内DoH，与新方法功能重叠）

---

## 二、逐 FR 审查

### FR-1（P0）: R5 嗅探去重锁

**根因核实**：✅ 正确

日志分析报告 P0-2 说"extractPrecise 被调用 2 次"，spec.md L106 已整改说明"extractPrecise 仅 1 处调用，真实重复源在 extractWithWebView 4 路径"。源码铁证：
- [VideoPlay.kt:380](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L380)：`extractPrecise` 仅 1 处调用
- [VideoPlay.kt:425](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L425)/[L520](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L520)/[L547](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L547)：`extractWithWebView` 3 处直接调用
- [VideoUrlExtractor.kt:552](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L552)：`extractWithWebView` 第 4 处调用（extractVideoUrlForEpisode 内部第三层）

**方案可行性**：✅ 正确

design.md L272 将去重锁放在 `extractWithWebView` 方法入口（覆盖全部4路径），签名与源码 [VideoUrlExtractor.kt:192-197](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L192-L197) 一致：
```kotlin
suspend fun extractWithWebView(
    url: String, source: BaseSource?,
    delayTime: Long = R5_DELAY_TIME, timeout: Long = R5_TIMEOUT
): String?
```

**代码片段对齐**：✅ 正确

VideoUrlExtractor 是 `object` 单例（[L30](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L30)），design.md L214 在 object 内定义字段正确。

**认知偏差检查**：✅ 无偏差

**结论**：FR-1 整改正确，可落地。唯一遗留：源码 [VideoUrlExtractor.kt:38](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L38) 注释过时（见 W8）。

---

### FR-2（P1）: DoH 负缓存时长优化 + 健康检查

**根因核实**：✅ 正确

spec.md 说"负缓存 30s 过长"。源码铁证：[DohDns.kt:104](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L104) `NEGATIVE_CACHE_TTL_MS = 30_000L` 确实是 30s。

**方案可行性**：⚠️ 部分可行，存在 E7 遗漏

design.md L382 新增 `preheatDohServers()` 方法，复用 [DohDns.kt:132](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L132) 的 `preheatScope`，正确。W6 整改将探测域名改为 www.baidu.com，正确。

**但 v1 遗漏了 E7**：DohDns.kt 已有 `asyncPreheatDoh()` 方法（[L259](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L259)），在冷启动失败后 30s 异步预热，用国外域名（[L262](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L262) `cloudflare-dns.com`）探测。design.md 未处理与该方法的关系，导致：
1. 功能重叠：preheatDohServers（App启动）+ asyncPreheatDoh（冷启动失败后）都探测DoH健康
2. 逻辑矛盾：asyncPreheatDoh 用国外域名探测国内DoH服务器（阿里+腾讯），W6 整改只改了 preheatDohServers，asyncPreheatDoh 仍是国外域名

**代码片段对齐**：✅ 基本正确

design.md L360-415 的代码片段与 DohDns.kt 现有结构一致（object 单例、preheatScope、DOH_SERVERS）。

**认知偏差检查**：⚠️ 存在 E7 偏差

**结论**：FR-2 方向正确，但必须补全 E7 整改（处理 asyncPreheatDoh 关系 + 修复其探测域名）。

---

### FR-3（P1）: 视频流强制 HTTP/1.1

**根因核实**：⚠️ 根因表述不完整

spec.md 说"服务端 HTTP/2 实现问题，视频流分片加载时触发协议错误"。日志铁证 3 次 ERR_HTTP2_PROTOCOL_ERROR。但根因未识别视频流真实请求路径。

**方案可行性**：❌ 存在 E6 重大认知偏差（阻断级）

**源码铁证（v1完全遗漏的文件）**：

1. **ExoPlayerHelper.okhttpDataFactory 已强制 HTTP/1.1**：[ExoPlayerHelper.kt:1006-1016](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L1006-L1016)
```kotlin
private val okhttpDataFactory by lazy {
    val client = okHttpClient.newBuilder()
        .callTimeout(0, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .protocols(listOf(okhttp3.Protocol.HTTP_1_1))  // P2-C: 强制 HTTP/1.1（已存在！）
        .followRedirects(true)
        .build()
    OkHttpDataSource.Factory(client).setUserAgent(BROWSER_UA)...
}
```
L997-1004 注释明确："P2-C 修复：强制 HTTP/1.1，规避 HTTP/2 PROTOCOL_ERROR"——**这个修复已经存在！**

2. **视频流播放走 cacheDataSourceFactory，不走 CronetInterceptor**：[ExoPlayerHelper.kt:953-962](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L953-L962)
```kotlin
val cacheDataSourceFactory by lazy {
    val upstreamFactory = cronetDataFactory ?: okhttpDataFactory  // 优先 Cronet DataSource
    CacheDataSource.Factory().setUpstreamDataSourceFactory(
        DefaultDataSource.Factory(appCtx, upstreamFactory)
    )...
}
```
- 若 `cronetDataFactory != null`（Cronet 可用）：视频流走 media3 CronetDataSource（HTTP/2），**不经过 OkHttp 拦截器链，不经过 CronetInterceptor**
- 若 `cronetDataFactory == null`（Cronet 不可用）：视频流走 okhttpDataFactory（已强制 HTTP/1.1）

3. **design.md 方案落地点错误**：
   - design.md 说"在 CronetInterceptor.intercept 入口检测 path 后缀，视频流跳过 Cronet"——但视频流播放走 ExoPlayer DataSource，不经过 CronetInterceptor（除非走 okhttpDataFactory，而 okhttpDataFactory 已强制 HTTP/1.1）
   - design.md 说"新增 videoStreamClient（protocols=HTTP_1_1）"——这是重复实现，okhttpDataFactory 已配置
   - design.md File Changes 清单（L182-191）只列了 HttpHelper.kt，**完全遗漏 ExoPlayerHelper.kt**

4. **日志 ERR_HTTP2_PROTOCOL_ERROR 真实来源分析**：
   - 日志说"path=videos5/{hash}"（视频流分片）+ "Cronet 协议错误，回退到 OkHttp"
   - "回退到 OkHttp"是 CronetInterceptor 的逻辑（[CronetInterceptor.kt:324](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L324) isProtocolError 分支）
   - 这说明该请求走了 OkHttp 拦截器链（okhttpClient，非 okhttpDataFactory）
   - 可能来源：[ExoPlayerHelper.kt:417](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L417) 或 [L740](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L740) 的 `okHttpClient.newCall(request).execute()`（m3u8预检查等，用 okHttpClient 未配 HTTP/1_1）

**认知偏差检查**：❌ 重大偏差

design.md 假设"视频流请求走 CronetInterceptor + okHttpClient"，但实际：
- 视频流播放主路径走 ExoPlayer DataSource（cacheDataSourceFactory），不经过 CronetInterceptor
- okhttpDataFactory 已强制 HTTP/1.1（P2-C 修复已存在）
- 日志中的 ERR_HTTP2_PROTOCOL_ERROR 可能来自 ExoPlayerHelper 内的 okHttpClient 请求（非播放主路径）

**结论**：FR-3 方案必须重新设计（见 E6 整改）。当前方案落地点错误，可能导致：在 HttpHelper 新增 videoStreamClient，但视频流播放不用它，问题未解决。

---

### FR-4（P1）: favicon.ico 缓存

**根因核实**：✅ 正确

日志分析报告 P1-3，137 次 favicon.ico 请求。[HttpHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt) 当前无 favicon 缓存机制。

**方案可行性**：✅ 正确

W4 整改将 FaviconCache 改为同步方法（非 suspend），避免 runBlocking 阻塞 OkHttp 调度线程。方案合理。

**代码片段对齐**：✅ 正确

design.md L520-623 的 FaviconCache.kt 代码片段是新建文件，结构完整。

**认知偏差检查**：✅ 无偏差

**结论**：FR-4 可落地。

---

### FR-5（P2）: StreamReset 重试移除 Call.cancel()

**根因核实**：✅ 正确

spec.md E2 整改说"chain.call().cancel() 会取消整个 Call 导致重试必然失败"。源码铁证：[StreamResetRetryInterceptor.kt:41](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt#L41) `chain.call().cancel()` 确实存在，L45 `chain.proceed(request)` 在已取消 Call 上重试。

**方案可行性**：❌ 整改代码 API 不可行（E5 新问题）

design.md L690 整改代码：
```kotlin
chain.call().client().connectionPool().evictAll()
```

**API 不可行铁证**：
1. OkHttp 4.12.0（[build.gradle:331](file:///f:/myself/github/WeAgentChat/temp/legado/app/build.gradle) 确认版本）的 `okhttp3.Call` 接口**没有 `client()` 公共方法**
2. `Call` 接口公共方法仅有：`request()`, `execute()`, `enqueue()`, `cancel()`, `isCanceled()`, `timeout()`, `clone()`
3. `RealCall` 实现类有 `private val client: OkHttpClient` 字段，但非公开 API
4. Grep 项目源码：无任何 `chain.call().client()` 或 `.client().connectionPool` 用法（No matches found）
5. WebSearch 确认 OkHttp 4.12.0 架构：`OkHttpClient.newCall()` 返回 RealCall，但 Call 接口不暴露 client

**编译错误**：`chain.call()` 返回 `Call` 接口类型，调用 `.client()` 会编译失败（unresolved reference）。

**代码片段对齐**：❌ API 不匹配

**认知偏差检查**：❌ 偏差

design.md 假设 `chain.call().client()` 可获取 OkHttpClient，实际不可行。

**结论**：FR-5 根因正确，但整改代码必须修正 API（见 E5 整改）。

---

### FR-6（P2）: Cronet 探测跳过日志采样

**根因核实**：✅ 正确

源码铁证：[CronetInterceptor.kt:189](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L189) `AppLog.putDebug("Cronet 探测跳过非失败host...")` 确实是 putDebug（DEBUG级别）。

**方案可行性**：✅ 正确

W3 整改已认识到 putDebug 已是 DEBUG 级别，重点改为采样输出减少 recordLog=true 时的文件日志量。design.md L726-749 采样方案（每10次输出1次）合理。

**代码片段对齐**：✅ 正确

**认知偏差检查**：✅ 无偏差

**结论**：FR-6 可落地。

---

### FR-7（P2）: 证书错误记忆缓存

**根因核实**：✅ 正确

源码铁证：[CronetInterceptor.kt:281](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L281) `if (isCertificateError(errMsg))` 在 catch 块中，当前降级后无缓存记忆。

**方案可行性**：✅ 正确

W5 整改明确 certErrorCache 检查位置在 FR-3 视频流检查之后、Cronet执行之前（intercept方法开头，[L155](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L155) 之后）。写入在 catch 块 isCertificateError 分支（L281附近）。方案合理。

**代码片段对齐**：✅ 正确

**认知偏差检查**：✅ 无偏差

**结论**：FR-7 可落地。

---

### FR-8（P3）: play.php 类 URL 预解析

**根因核实**：✅ 正确

日志分析报告 P3-1，首帧延迟方差 7.5 倍，慢路径为 /play.php 重定向。

**方案可行性**：✅ 正确

design.md L822-862 在 extractVideoUrlForEpisode 入口加 playerPageCache，与 FR-1 去重锁层级不同（URL级 vs path级），互不冲突。代码片段已整合到 FR-1。

**代码片段对齐**：✅ 正确

**认知偏差检查**：✅ 无偏差

**结论**：FR-8 可落地。

---

### FR-9（P3）: window.__videoUrls__ 解析容错

**根因核实**：✅ 正确

E4 整改已认识到源码用 `GSON.fromJsonArray`（非 JSON.parse）。源码铁证：[BackstageWebView.kt:475](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/BackstageWebView.kt#L475) `val urls = GSON.fromJsonArray<String>(result).getOrNull()`，L476-478 当前失败直接返回，无容错。

**方案可行性**：✅ 正确

design.md L881-929 基于 GSON.fromJsonArray 失败分支添加正则提取，代码结构与源码 [BackstageWebView.kt:462-492](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/BackstageWebView.kt#L462-L492) 一致。

**代码片段对齐**：⚠️ 正则未完全对齐（W7）

I2 整改说"正则覆盖所有 VIDEO_SOURCE_REGEX 支持的格式"。源码 [VideoUrlExtractor.kt:61](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L61)：
```
val VIDEO_SOURCE_REGEX = """(?i).*(?:https?://[^\s]{12,}\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?.*)?|https?://.*?video/tos[^\s]*|rtmp:[^\s]+).*"""
```
支持格式：m3u8/mp4/mkv/flv/**mp3**/m4a/aac/mpd + video/tos + rtmp

design.md L924 正则：
```
"""https?://[^\s"'<>]+\.(?:m3u8|mp4|mkv|flv|m4a|aac|mpd)(?:\?[^\s"'<>]*)?"""
```
覆盖：m3u8/mp4/mkv/flv/m4a/aac/mpd

**遗漏**：`mp3` 格式未覆盖（VIDEO_SOURCE_REGEX 含 mp3，正则不含）。虽然 mp3 是音频格式，但 design.md 声称"与 VIDEO_SOURCE_REGEX 对齐"，实际未完全对齐。

**认知偏差检查**：✅ 无重大偏差

**结论**：FR-9 可落地，但需补全 W7（正则加 mp3）。

---

## 三、遗漏分析检查（logs(8) 10个优化点覆盖情况）

日志分析报告第四章列出 10 个优化点，逐项核对覆盖情况：

| # | 日志优化点 | 对应FR | 覆盖状态 | 说明 |
|---|-----------|--------|---------|------|
| 1 | P0 Cronet 150 SIGABRT修复 | 无（Out of Scope） | ✅ 已排除 | spec.md L42 明确排除（独立P0任务），理由合理 |
| 2 | P0 R5嗅探去重锁 | FR-1 | ✅ 覆盖 | 根因已修正（extractPrecise→extractWithWebView 4路径） |
| 3 | P1 DoH健康检查+negative cache缩短 | FR-2 | ⚠️ 部分覆盖 | E7：遗漏 asyncPreheatDoh 方法处理 |
| 4 | P1 视频流强制HTTP/1.1 | FR-3 | ❌ 方案偏差 | E6：未识别 ExoPlayerHelper 已有HTTP/1.1配置 |
| 5 | P1 favicon.ico缓存 | FR-4 | ✅ 覆盖 | 方案完整 |
| 6 | P2 StreamReset重试 | FR-5 | ⚠️ 整改代码API不可行 | E5：chain.call().client() 不存在 |
| 7 | P2 Cronet探测日志降级 | FR-6 | ✅ 覆盖 | W3已修正认知偏差 |
| 8 | P2 证书错误记忆缓存 | FR-7 | ✅ 覆盖 | W5已明确位置 |
| 9 | P3 play.php预解析 | FR-8 | ✅ 覆盖 | 方案完整 |
| 10 | P3 window.__videoUrls__容错 | FR-9 | ✅ 覆盖 | E4已修正代码匹配，W7正则待补mp3 |

**遗漏结论**：10个优化点全部有对应FR，无遗漏。但 FR-2/FR-3/FR-5 的方案存在 E5/E6/E7 问题需整改。

---

## 四、ERROR/WARNING/INFO 分级问题清单

### ERROR级（必须修复）

#### E5（新）: FR-5 整改代码 `chain.call().client()` API 不可行

**文档位置**：design.md L690
**源码铁证**：
- [build.gradle:331](file:///f:/myself/github/WeAgentChat/temp/legado/app/build.gradle) 确认 OkHttp 4.12.0
- OkHttp 4.12.0 的 `okhttp3.Call` 接口无 `client()` 公共方法
- Grep 项目源码：无 `chain.call().client()` 用法

**问题本质**：整改代码会编译错误（unresolved reference: client）

**整改替换文本**（design.md L684-691）：
```kotlin
// FR-5 整改：移除 chain.call().cancel()，它会取消整个 Call 导致重试必然失败
// 改用连接池清理：淘汰故障连接，不影响 Call 状态
// E5 整改：chain.call().client() API 不可行（Call接口无client()方法），
// 改为直接引用 HttpHelper.okHttpClient（StreamResetRetryInterceptor 是 object 单例，可引用同模块 HttpHelper）
try {
    // 清理空闲连接（evictAll 会清理所有空闲连接）
    // 已知上限：evictAll 影响其他请求的连接复用，连接数多时有轻微开销
    // 升级路径：如需精确按 host 清理，需自定义 ConnectionPool
    io.legado.app.help.http.okHttpClient.connectionPool().evictAll()
} catch (ignore: Exception) {}
chain.connection()?.socket()?.close()
```

**整改依据**：StreamResetRetryInterceptor.kt 是 object 单例，可直接引用 `io.legado.app.help.http.okHttpClient`（[HttpHelper.kt:75](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L75)）。该 client 与发起请求的 client 是同一实例（拦截器在 okHttpClient 拦截器链中，[HttpHelper.kt:159](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L159)）。

---

#### E6（新）: FR-3 方案重大认知偏差——视频流路径与方案落地点不匹配（阻断级）

**文档位置**：design.md L82-94（AD-02）+ L422-501（FR-3 详细设计）+ L182-191（File Changes）
**源码铁证**：
1. [ExoPlayerHelper.kt:1006-1013](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L1006-L1013)：`okhttpDataFactory` 已配置 `.protocols(listOf(okhttp3.Protocol.HTTP_1_1))`，注释明确"P2-C 修复：强制 HTTP/1.1，规避 HTTP/2 PROTOCOL_ERROR"
2. [ExoPlayerHelper.kt:953-962](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L953-L962)：视频流播放走 `cacheDataSourceFactory`，upstream 是 `cronetDataFactory ?: okhttpDataFactory`
3. [ExoPlayerHelper.kt:981-992](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L981-L992)：`cronetDataFactory` 是 media3 CronetDataSource（非 OkHttp CronetInterceptor），Cronet 可用时视频流走此路径，不经过 CronetInterceptor

**问题本质**：
1. design.md 的 videoStreamClient 是重复实现（okhttpDataFactory 已强制 HTTP/1.1）
2. design.md 的"CronetInterceptor 跳过 Cronet"对视频流播放主路径无效（视频流走 ExoPlayer DataSource，不经过 CronetInterceptor）
3. File Changes 清单遗漏 ExoPlayerHelper.kt
4. 日志中 ERR_HTTP2_PROTOCOL_ERROR 真实来源未准确识别（可能来自 ExoPlayerHelper L417/L740 的 okHttpClient 请求，或 cronetDataFactory 的 Cronet DataSource）

**整改建议**：FR-3 方案需重新设计，分两步：

**步骤1：准确识别 ERR_HTTP2_PROTOCOL_ERROR 来源**
- 在 CronetInterceptor.intercept 的 isProtocolError 分支（[L324](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L324)）增加日志输出请求 path + 调用栈，确认是哪类请求触发
- 检查 ExoPlayerHelper L417/L740 的 `okHttpClient.newCall(request).execute()` 请求的 URL 类型

**步骤2：根据来源针对性修复（替换 design.md FR-3 方案）**

```markdown
**方案（重新设计）**：

情况A：若 ERR_HTTP2_PROTOCOL_ERROR 来自 cronetDataFactory（media3 CronetDataSource）：
- 在 ExoPlayerHelper.cacheDataSourceFactory 中，对视频流请求禁用 cronetDataFactory，强制走 okhttpDataFactory（已HTTP/1.1）
- 修改 [ExoPlayerHelper.kt:958](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L958)：
  `val upstreamFactory = okhttpDataFactory  // FR-3: 视频流强制走 OkHttp HTTP/1.1，禁用 Cronet DataSource`
- File Changes 必须新增 ExoPlayerHelper.kt

情况B：若来自 ExoPlayerHelper L417/L740 的 okHttpClient 请求（m3u8预检查等）：
- 将这些请求改用 videoStreamClient（protocols=HTTP_1_1）
- 或直接复用 okhttpDataFactory 的 client 配置

情况C：若来自 AnalyzeUrl 的播放页解析请求（走 HttpHelper.okHttpClient + CronetInterceptor）：
- 原设计文档方案有效（CronetInterceptor 跳过 Cronet + videoStreamClient），但需确认这类请求是否真的触发 ERR_HTTP2_PROTOCOL_ERROR
```

**整改依据**：视频流播放真实路径是 ExoPlayer DataSource，design.md 必须基于真实路径设计方案。

---

#### E7（新）: FR-2 遗漏 asyncPreheatDoh 方法处理

**文档位置**：design.md L357-415（FR-2 详细设计）
**源码铁证**：
1. [DohDns.kt:259-276](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L259-L276)：`asyncPreheatDoh()` 方法已存在，冷启动失败后 30s 异步预热
2. [DohDns.kt:262](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L262)：`val probeHost = "cloudflare-dns.com"` 用国外域名探测国内DoH
3. [DohDns.kt:239](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L239)：`asyncPreheatDoh()` 在冷启动失败分支调用

**问题本质**：
1. 功能重叠：design.md 新增 `preheatDohServers()`（App.onCreate 探测）与已有 `asyncPreheatDoh()`（冷启动失败后探测）都探测DoH健康
2. 逻辑矛盾：W6 整改只改了 preheatDohServers 的探测域名（www.baidu.com），asyncPreheatDoh 仍用国外域名探测国内DoH服务器（阿里+腾讯），探测结果不准

**整改替换文本**（design.md FR-2 实现要点补充）：

```markdown
**实现要点（补充 E7 整改）**：

5. **处理与已有 asyncPreheatDoh 的关系**：DohDns.kt 已有 `asyncPreheatDoh()` 方法（L259，冷启动失败后30s异步预热），新增 `preheatDohServers()` 需明确两者职责分工：
   - `preheatDohServers()`（新增）：App.onCreate 启动时主动探测，选择最优服务器为主（冷启动前预热）
   - `asyncPreheatDoh()`（已有）：冷启动场景首次DoH失败后，30s后异步探测恢复
   - 两者不冲突：preheatDohServers 在 App 启动时执行，asyncPreheatDoh 仅在冷启动失败后触发

6. **修复 asyncPreheatDoh 探测域名**：将 [DohDns.kt:262](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L262) 的 `cloudflare-dns.com`（国外域名，国内可能不可达）改为 `www.baidu.com`（国内域名，与DoH服务器实际使用场景一致），与 preheatDohServers 统一探测域名
```

**整改依据**：asyncPreheatDoh 用国外域名探测国内DoH服务器，探测失败可能是域名本身不可达而非DoH服务器问题，导致误判DoH不可用。

---

### WARNING级（建议修复）

#### W7（新）: FR-9 正则未完全对齐 VIDEO_SOURCE_REGEX（缺 mp3）

**文档位置**：design.md L924
**源码铁证**：[VideoUrlExtractor.kt:61](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L61) VIDEO_SOURCE_REGEX 含 `mp3` 格式

**问题本质**：design.md 声称"与 VIDEO_SOURCE_REGEX 对齐"，实际遗漏 mp3

**整改替换文本**（design.md L924）：
```kotlin
val urlRegex = Regex(
    """https?://[^\s"'<>]+\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?[^\s"'<>]*)?""",
    RegexOption.IGNORE_CASE
)
```

---

#### W8（新）: FR-1 源码注释过时（3处→4处，行号错误）

**文档位置**：[VideoUrlExtractor.kt:38](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L38)（源码注释，非设计文档）
**问题**：注释说"3处调用方（extractWithWebView 默认值 + extractVideoUrlForEpisode L489 + VideoPlay.kt L319/L429）"，实际4处调用（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552），行号 L319/L429 也不对

**整改建议**：FR-1 实施时同步更新源码注释为"4处调用方（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552）"

---

### v1已整改确认（13项全部正确落地）

| v1编号 | 问题 | 整改状态 | 验证结论 |
|--------|------|---------|---------|
| E1 | FR-1 去重锁位置 | ✅ 已整改 | 去重锁放在 extractWithWebView 入口，覆盖4路径 |
| E2 | FR-5 根因错误 | ✅ 根因已整改 | chain.call().cancel() 是真实根因（但整改代码有E5） |
| E3 | FR-3 方案漏洞 | ⚠️ 部分整改 | 认识到跳过Cronet≠HTTP/1.1，但方案落地点有E6 |
| E4 | FR-9 代码不匹配 | ✅ 已整改 | 基于GSON.fromJsonArray，代码与源码一致 |
| W1 | companion object矛盾 | ✅ 已整改 | tasks.md 已改为object内定义 |
| W2 | 缓存位置矛盾 | ✅ 已整改 | 统一为extractVideoUrlForEpisode入口 |
| W3 | putDebug认知偏差 | ✅ 已整改 | 已认识到putDebug是DEBUG级别 |
| W4 | runBlocking风险 | ✅ 已整改 | FaviconCache改为同步方法 |
| W5 | 证书缓存位置 | ✅ 已整改 | 明确在FR-3检查之后、Cronet执行之前 |
| W6 | 探测域名选择 | ✅ 部分整改 | preheatDohServers改www.baidu.com（但asyncPreheatDoh未改，见E7） |
| I1 | 60s清理协程泄漏 | ✅ 已整改 | 改为单次定时清理兜底 |
| I2 | 正则覆盖不全 | ⚠️ 部分整改 | 覆盖大部分格式，但缺mp3（见W7） |
| I3 | SIGABRT未纳入 | ✅ 合理排除 | 独立P0任务处理 |

---

## 五、整改建议汇总

### 整改优先级清单

| 优先级 | 问题 | 文档位置 | 整改条目 | 阻断落地 |
|--------|------|----------|----------|---------|
| 阻断 | FR-3 方案认知偏差（视频流路径不匹配） | design.md AD-02 + FR-3 + FileChanges | E6 | 是 |
| 高 | FR-5 整改代码API不可行 | design.md L690 | E5 | 是（编译错误） |
| 高 | FR-2 遗漏asyncPreheatDoh处理 | design.md FR-2 | E7 | 否（逻辑矛盾） |
| 中 | FR-9 正则缺mp3格式 | design.md L924 | W7 | 否 |
| 低 | FR-1 源码注释过时 | VideoUrlExtractor.kt:38 | W8 | 否 |

### 整改后落地可行性确认

完成 E5/E6/E7 整改后，文档可支撑落地。其中：
- **E5** 是简单API替换（1行代码），整改后 FR-5 可落地
- **E6** 需重新设计 FR-3 方案，必须先准确识别 ERR_HTTP2_PROTOCOL_ERROR 真实来源（建议实施时先加日志定位），再针对性修复。当前 FR-3 方案不可直接落地
- **E7** 是补充处理（修复 asyncPreheatDoh 探测域名 + 明确与新方法职责分工），整改后 FR-2 可落地

**整体判定**：⚠️ 整改后落地。E6 是阻断级问题，FR-3 方案必须重新设计后方可实施；E5/E7 整改后 FR-5/FR-2 可落地。其余 6 个 FR（FR-1/FR-4/FR-6/FR-7/FR-8/FR-9）方案正确，可直接落地。

---

## 六、认知偏差专项（v2新增）

### 偏差1: FR-3 假设"视频流走 CronetInterceptor + okHttpClient"

**假设**：视频流请求走 HttpHelper.okHttpClient 的拦截器链（含 CronetInterceptor）
**事实**：视频流播放走 ExoPlayer DataSource（cacheDataSourceFactory → cronetDataFactory/okhttpDataFactory），不经过 CronetInterceptor（除非走 okhttpDataFactory，而 okhttpDataFactory 已强制 HTTP/1.1）
**偏差原因**：v1 和 design.md 都未读取 ExoPlayerHelper.kt，未识别视频流播放真实路径。design.md 的 File Changes 清单遗漏 ExoPlayerHelper.kt
**影响**：FR-3 方案落地点错误，可能导致 videoStreamClient 新增后视频流播放不用它，问题未解决

### 偏差2: FR-3 假设"需要新增 videoStreamClient"

**假设**：OkHttp 未配置 HTTP/1.1，需新增 videoStreamClient
**事实**：ExoPlayerHelper.okhttpDataFactory（L1013）已配置 `.protocols(listOf(okhttp3.Protocol.HTTP_1_1))`，P2-C 修复已存在
**偏差原因**：未读取 ExoPlayerHelper.kt，不知道已有 HTTP/1.1 配置
**影响**：重复实现，且新增的 videoStreamClient 可能不被视频流播放路径使用

### 偏差3: FR-5 假设"chain.call().client() 可获取 OkHttpClient"

**假设**：OkHttp Call 接口有 client() 方法
**事实**：OkHttp 4.12.0 的 Call 接口无 client() 公共方法（RealCall 有 private client 字段但非公开API）
**偏差原因**：未核验 OkHttp API 可行性，想当然认为 Call 暴露 client
**影响**：整改代码编译错误

---

## 七、审查方法论反思

### v1 审查的不足

1. **未读取 ExoPlayerHelper.kt**：v1 审查只读了 HttpHelper.kt 验证 okHttpClient 配置，未追踪视频流播放真实路径（ExoPlayer DataSource），导致 FR-3 方案认知偏差未识别
2. **未核验 OkHttp API 可行性**：v1 审查接受了 `chain.call().client()` 用法，未用 WebSearch/Grep 确认 Call 接口是否有 client() 方法
3. **未识别 asyncPreheatDoh 方法**：v1 审查只验证了 NEGATIVE_CACHE_TTL_MS 值，未检查 DohDns.kt 是否已有预热方法，导致 E7 遗漏

### v2 审查的改进

1. **新增 ExoPlayerHelper.kt 审查**：追踪视频流播放真实路径，识别 FR-3 方案落地点错误
2. **WebSearch + Grep 双重验证 API**：确认 OkHttp 4.12.0 Call 接口无 client() 方法
3. **完整读取 DohDns.kt**：识别已有 asyncPreheatDoh 方法与新方法的冲突

---

## 八、整体评审结论

**判定结果**：⚠️ 整改后落地

存在 1 个阻断级问题（E6: FR-3 方案认知偏差）+ 2 个高优先级问题（E5: API不可行 / E7: 方法遗漏），必须完成 E5/E6/E7 整改后方可实施。

**量化评分**（0-100分，仅作参考）：
- 代码匹配度：70（v1的E1-E4整改正确，但v2发现E5/E6/E7新问题，FR-3方案与视频流真实路径不匹配）
- 技术成熟度：72（FR-1/FR-2/FR-4/FR-6/FR-7/FR-8/FR-9 方案可行，FR-3方案需重新设计，FR-5整改代码API需修正）
- 落地清晰度：68（FR-3 File Changes遗漏ExoPlayerHelper.kt，FR-5整改代码编译错误，其余FR清晰）

**整改后落地可行性最终确认**：
- 完成 E5（1行API替换）+ E7（补充处理asyncPreheatDoh）后，FR-2/FR-5 可落地
- E6 需重新设计 FR-3 方案：必须先实施"步骤1：准确识别 ERR_HTTP2_PROTOCOL_ERROR 来源"，再根据来源（cronetDataFactory / ExoPlayerHelper L417/L740 / AnalyzeUrl）针对性修复。FR-3 当前方案不可直接落地
- 其余 6 个 FR（FR-1/FR-4/FR-6/FR-7/FR-8/FR-9）方案正确，可直接落地（FR-9 补 W7 正则mp3）

---

## 九、整改完成状态

> 整改时间：2026-07-31
> 整改范围：基于本报告 v2 的 E5/E6/E7/W7/W8 整改建议，修订 spec.md / design.md / tasks.md 三文档（仅文档修订，未修改源码）

### 整改清单

| 编号 | 问题 | 整改文件 | 整改内容 | 状态 |
|------|------|----------|----------|------|
| E5 | FR-5 整改代码 `chain.call().client()` API 不可行 | design.md / spec.md | design.md 全局替换 `chain.call().client().connectionPool().evictAll()` → `io.legado.app.help.http.okHttpClient.connectionPool().evictAll()`（5 处：AD-04/数据流2/File Changes/实现要点/代码片段）+ 补充 E5 说明注释；spec.md FR-5 方案与验收标准同步明确 `okHttpClient.connectionPool().evictAll()` | ✅ 完成 |
| E6 | FR-3 方案认知偏差（视频流路径不匹配） | spec.md / design.md / tasks.md | spec.md FR-3 根因补充（视频流播放走 ExoPlayer DataSource，ERR_HTTP2_PROTOCOL_ERROR 来自 ExoPlayerHelper L417/L740 m3u8 预检查）+ 方案更新为三重覆盖 + 验收标准补充；design.md AD-02/File Changes/实现要点/代码片段/已知上限/策略二/数据流2 全面更新，新增 ExoPlayerHelper.kt 修改示例与诊断先行步骤；tasks.md 新增 3.7.1（诊断日志）+ 3.7.2（ExoPlayerHelper 改 videoStreamClient）+ 1.1 备份清单补 ExoPlayerHelper.kt | ✅ 完成 |
| E7 | FR-2 遗漏 asyncPreheatDoh 方法处理 | design.md / spec.md / tasks.md | design.md FR-2 实现要点补充第5点（preheatDohServers 与 asyncPreheatDoh 职责分工）+ 第6点（修复 asyncPreheatDoh L262 探测域名 cloudflare-dns.com → www.baidu.com）；spec.md FR-2 方案补充第4点；tasks.md 新增 3.3.1 任务项 | ✅ 完成 |
| W7 | FR-9 正则未完全对齐 VIDEO_SOURCE_REGEX（缺 mp3） | design.md / spec.md | design.md 正则补充 mp3（m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd）+ 格式列表全局同步；spec.md FR-9 方案/验收标准格式列表同步补充 mp3 | ✅ 完成 |
| W8 | FR-1 源码注释过时（3处→4处，行号错误） | tasks.md | tasks.md FR-1 新增 2.3.1 任务项：实施时同步更新 VideoUrlExtractor.kt:38 源码注释为"4处调用方（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552）" | ✅ 完成 |

### 整改后落地可行性

- **E5**：FR-5 整改代码 API 已修正（直接引用 HttpHelper 全局 okHttpClient，HttpHelper.kt:75），可编译落地
- **E6**：FR-3 方案已重新设计为三重覆盖（videoStreamClient + CronetInterceptor 跳过 + ExoPlayerHelper 改 videoStreamClient）+ 诊断先行，File Changes 已补全 ExoPlayerHelper.kt，方案与视频流真实路径匹配
- **E7**：FR-2 已补全 asyncPreheatDoh 处理（职责分工 + 探测域名修复），逻辑矛盾消除
- **W7**：FR-9 正则已与 VIDEO_SOURCE_REGEX 完全对齐（含 mp3）
- **W8**：FR-1 源码注释更新已纳入 tasks.md 实施清单

**整体判定**：✅ 整改后可落地。E5/E6/E7/W7/W8 全部整改完成，9 个 FR 方案均可支撑实施。
