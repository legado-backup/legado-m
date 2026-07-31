# 嗅探稳定性增强（sniff-stability-enhance-20260731）技术设计文档

## 一、背景

**任务来源**：用户 2026-07-31 19:41 真机测试 sniff-result-pipeline-fix 正式包（legado_miss_app_3.26.073118.apk）后反馈"整体效果比之前好多了，但是我期望更好"。

**日志分析依据**：`docs/issues/user/temp/20260731/002/extracted_8/log_analysis_report.md` 深度分析 39 个 appLog 文件 + logcat.txt（覆盖 07:22~19:22 时段），识别出 9 个仍需优化的问题。

**核心问题统计**（来自日志分析报告第三章统计汇总）：

| 指标 | 数值 | 说明 |
|------|------|------|
| R5 嗅探启动 | 41 次 | 17 次重复（41% 浪费率） |
| ExoPlayer 取消 | 76 次 | 含重复嗅探导致的误取消 |
| DoH 失败 | 21 条 | server#1+#2 均不稳定 |
| favicon.ico 请求 | 137 次 | 无缓存，每次走网络 |
| ERR_HTTP2_PROTOCOL_ERROR | 3 次 | 视频流 h2 协议错误 |
| ERR_CERT_AUTHORITY_INVALID | ~10 次 | 证书不受信任 |
| Cronet 探测跳过日志 | 152 次 | 日志噪声 |
| StreamReset 重试失败 | 1 次 | 被 Activity 切换取消 |
| ExoPlayer 首帧延迟 | 701~5309ms | 方差 7.5 倍 |

**设计目标**：通过 9 个 FR（功能需求）系统化解决上述问题，将 R5 嗅探重复率从 41% 降至 5% 以下，消除视频流 HTTP/2 协议错误，减少无效网络请求。

---

## 二、Technical Approach（技术方案总述）

本设计采用**分层去重 + 协议降级 + 缓存复用 + 作用域隔离**四大策略，覆盖嗅探全链路：

### 策略一：分层去重（FR-1、FR-8）

针对 R5 嗅探 41% 重复率根因（同一 path 在 140ms~1s 内被重复触发 2-3 次），在 `VideoUrlExtractor` 层引入两道去重：

- **FR-1 进程级去重锁**：用 `ConcurrentHashMap<String, Deferred<String?>>` 记录进行中的 R5 嗅探，重复请求 `await` 复用结果，避免重复创建 WebView
- **FR-8 解析结果缓存**：对 `play.php` 类需重定向解析的 URL，缓存解析结果 5 分钟，避免重复三层降级解析

### 策略二：协议降级（FR-3、FR-5）

针对视频流 HTTP/2 协议错误（ERR_HTTP2_PROTOCOL_ERROR）和 StreamReset 重试被取消问题：

- **FR-3 视频流强制 HTTP/1.1**（E6 整改：三重覆盖）：在 `CronetInterceptor.intercept` 入口检测 path 后缀（.m3u8/.mp4/.ts/.flv/.mkv/.webm），视频流直接跳过 Cronet 走 OkHttp + HTTP/1.1；HttpHelper 新增 `videoStreamClient`（protocols=HTTP_1_1）；ExoPlayerHelper L417/L740 的 m3u8 预检查请求改用 videoStreamClient（ERR_HTTP2_PROTOCOL_ERROR 真实来源），规避 HTTP/2 协议错误
- **FR-5 移除 Call.cancel() 改用连接池清理**（E2 整改）：StreamReset 重试前移除 `chain.call().cancel()`（它会取消整个 Call 导致重试必然失败），改用 `connectionPool.evictAll()` 清理故障连接，重试时 Call 状态保持可用

### 策略三：缓存复用（FR-2、FR-4、FR-7）

针对重复网络请求和无效降级往返：

- **FR-2 DoH 健康检查**：启动时探测 2 个 DoH 服务器延迟，选择更优的为主；负缓存时长从 30s 降至 10s，减少污染时长
- **FR-4 favicon.ico 缓存**：内存 LruCache（4MB）+ 磁盘缓存（按域名，24h 过期）+ 并行请求合并，消除 137 次重复网络请求
- **FR-7 证书错误记忆**：对证书错误 host 缓存 5 分钟，期间直接走 OkHttp 不尝试 Cronet，减少无效降级往返

### 策略四：作用域隔离与日志治理（FR-6、FR-9）

- **FR-6 日志采样**：Cronet 探测跳过日志每 10 次输出 1 次汇总，从 152 条降至 ~15 条
- **FR-9 解析容错**（E4 整改）：`window.__videoUrls__` 的 `GSON.fromJsonArray` 失败时降级为正则提取（正则覆盖 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd 全格式，I2 整改），提升特定源嗅探成功率

### 设计原则

1. **最小侵入**：所有 FR 复用现有 object 单例和拦截器架构，不引入新框架
2. **降级安全**：所有缓存/去重失败时回退到原逻辑，不引入新故障路径
3. **日志脱敏**：所有日志遵循 output-safety 规范，host 用前 3 字符 + `***`，path 用前 20~30 字符
4. **协程规范**：遵守项目 `Coroutine.async{}.onError{}.onSuccess{}` 链式封装，CancellationException 守卫必须传播

---

## 三、Architecture Decisions（架构决策）

### AD-01: R5 嗅探去重锁用 ConcurrentHashMap+Deferred（E1 整改：位置修正）

- **Context**: R5 嗅探重复率 41%，同一 path 在 140ms~1s 内被重复触发 2-3 次，导致重复 WebView 创建 + ExoPlayer 误取消。VideoUrlExtractor 是 object 单例，`extractWithWebView`（R5 嗅探核心）是 suspend 函数，有 4 个调用方并发访问（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552）。
- **Concern**: 需要一种并发安全、可复用结果、不阻塞调用方的去重机制。备选方案有三种：互斥锁（Mutex）、Channel 通道、ConcurrentHashMap+Deferred。
- **Decision**: 采用 `ConcurrentHashMap<String, Deferred<String?>>` 方案，key=path（取 URL 的 path 部分作为去重维度），value=Deferred。重复请求直接 `await()` 复用结果，避免重复执行。**去重锁放在 `extractWithWebView` 方法入口**（覆盖全部 4 个调用路径），而非 `extractVideoUrlForEpisode`（仅覆盖 1/4 路径）。
- **Goal**: 将 R5 嗅探重复率从 41% 降至 5% 以下，消除重复 WebView 创建和 ExoPlayer 误取消。
- **Tradeoff**:
  - 接受：内存中维护一个 ConcurrentHashMap，单条目占用极小（path 字符串 + Deferred 引用）
  - 接受：I1 整改后改为 Deferred 完成后立即 remove + 单次定时清理兜底（不再每次 launch 60s 协程）
  - 放弃：互斥锁方案会阻塞后到的请求线程，无法复用结果；Channel 方案实现复杂度更高
- **Status**: Proposed
- **Superseded-by**: 无

### AD-02: 视频流强制 HTTP/1.1 三重覆盖方案（E3 整改：videoStreamClient 必须方案 + E6 整改：认知偏差修正）

- **Context**: 视频流请求出现 ERR_HTTP2_PROTOCOL_ERROR（InternalErrorCode=-337），发生在 206 Partial Content 分片加载时。日志铁证 3 次协议错误均发生在视频流 CDN 域名。**E6 整改认知偏差修正**：视频流播放主路径走 ExoPlayer DataSource（cacheDataSourceFactory → cronetDataFactory/okhttpDataFactory），okhttpDataFactory 已配置 HTTP/1.1（ExoPlayerHelper.kt:1013，P2-C 修复已存在），不经过 CronetInterceptor；日志中 ERR_HTTP2_PROTOCOL_ERROR（"回退到 OkHttp"来自 CronetInterceptor L324 isProtocolError 分支）真实来源是 ExoPlayerHelper L417/L740 的 m3u8 预检查等请求（走 okHttpClient + CronetInterceptor，HTTP/2），非播放主路径。
- **Concern**: 需要识别视频流请求并强制走 HTTP/1.1 规避协议错误。备选方案有三种：path 后缀判断、Content-Type 判断、域名白名单。
- **Decision**（E6 整改：三重覆盖 + 诊断先行）：
  1. 在 `CronetInterceptor.intercept` 入口用 path 后缀判断（.m3u8/.mp4/.ts/.flv/.mkv/.webm），命中则跳过 Cronet
  2. **E3 整改关键**：跳过 Cronet 不等于强制 HTTP/1.1（OkHttp 默认协商 HTTP/2），必须额外新建 `videoStreamClient`（`protocols=listOf(Protocol.HTTP_1_1)`）
  3. **E6 整改关键**：修改 ExoPlayerHelper.kt L417/L740 的 `okHttpClient.newCall` 请求（m3u8 预检查等）改用 `videoStreamClient`，这是 ERR_HTTP2_PROTOCOL_ERROR 的真实来源
  4. **E6 整改：诊断先行**：实施前先在 CronetInterceptor.isProtocolError 分支（L324）增加日志输出请求 path + 调用栈，确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源，再针对性修复
- **Goal**: 消除视频流 HTTP/2 协议错误，提升视频流加载稳定性。
- **Tradeoff**:
  - 接受：path 后缀判断可能漏判无后缀的视频流 URL（如带 query 参数 `/video?id=xxx`），但日志显示当前问题 URL 均有明确后缀
  - 接受：视频流不走 Cronet 丧失 QUIC/HTTP3 优势，但视频流场景稳定性优先于性能
  - 接受：独立 videoStreamClient 增加连接池开销（需修改 ExoPlayerHelper L417/L740 使用该 client）
  - 放弃：Content-Type 判断需要先发请求获取响应头，无法在请求前决策；域名白名单维护成本高且无法覆盖新 CDN 域名；拦截器内动态设置 protocols 不可行（protocols 是 OkHttpClient 级别配置，非请求级别）
- **Status**: Proposed
- **Superseded-by**: 无

### AD-03: favicon 缓存用 LruCache+磁盘缓存+请求合并

- **Context**: 19:00 会话 137 次 favicon.ico 请求，每次耗时 400-600ms，全部走 Cronet 网络，无任何缓存复用。
- **Concern**: favicon.ico 是高频低变资源，需要多级缓存避免重复网络请求。备选方案有三种：仅内存缓存、仅磁盘缓存、内存+磁盘+请求合并。
- **Decision**: 采用三级方案：内存 LruCache（maxSize=4MB）+ 磁盘缓存（按域名，24h 过期）+ 并行请求合并（ConcurrentHashMap<host, Deferred>）。
- **Goal**: 消除 137 次重复网络请求，favicon 加载从 400-600ms 降至 <10ms（内存命中）或 <50ms（磁盘命中）。
- **Tradeoff**:
  - 接受：内存占用 4MB（Bitmap LruCache），在低端设备上可能略增内存压力
  - 接受：磁盘缓存需管理过期清理，24h TTL 可能导致 favicon 更新延迟感知
  - 放弃：仅内存缓存重启后失效；仅磁盘缓存每次需 IO 读取延迟较高
- **Status**: Proposed
- **Superseded-by**: 无

### AD-04: StreamReset 重试移除 Call.cancel() 改用连接池清理（E2 整改：根因修正）

- **Context**: FR-3 StreamReset 重试机制触发后，重试在 3ms 内被 Canceled。**E2 整改根因修正**：日志时序铁证 6608（重试）→ 6609（Canceled）→ 6610（onPause），6609 在 6610 之前，证明 Canceled 不是 Activity 切换取消协程导致，而是 `StreamResetRetryInterceptor.kt:41` 的 `chain.call().cancel()` 设置了 Call 的 canceled 标志，导致后续 `chain.proceed(request)` 检查标志时抛出 `IOException("Canceled")`。
- **Concern**: 需要在不取消整个 Call 的前提下清理故障连接，让重试可正常执行。备选方案有三种：移除 cancel() 改用连接池清理、runBlocking+NonCancellable（无效，NonCancellable 只保护协程取消不保护 Call.cancel()）、不处理。
- **Decision**: 移除 `chain.call().cancel()`，改用 `io.legado.app.help.http.okHttpClient.connectionPool().evictAll()` 清理连接池（或按 host 清理），重试时 Call 状态保持可用，`chain.proceed(request)` 可正常执行。
- **Goal**: 提升 StreamReset 重试成功率从 0% 提升至 > 50%，消除"重试失败, error=Canceled"日志。
- **Tradeoff**:
  - 接受：`evictAll()` 会清理所有空闲连接，可能影响其他请求的连接复用（连接数多时有轻微开销）
  - 接受：升级路径为自定义 ConnectionPool 实现按 host 精确清理（当前实现简化）
  - 放弃：runBlocking+NonCancellable 方案完全无效（Canceled 是 OkHttp Call.cancel() 导致，非协程取消，NonCancellable 不保护 OkHttp Call 状态）；不处理方案无法解决重试失败问题
- **Status**: Proposed
- **Superseded-by**: 无

---

## 四、Data Flow（数据流说明）

### 数据流 1：R5 嗅探去重数据流（FR-1 + FR-8）

当用户点击 RSS 视频文章触发 `extractVideoUrlForEpisode(url, source, rssArticle)`，或 VideoPlay.kt L425/L520/L547 直接调用 `extractWithWebView` 时：

1. **URL 快速路径检查**（extractVideoUrlForEpisode 入口）：若 URL 已是视频流格式（.m3u8/.mp4 等后缀），直接返回 URL，不进入去重流程。
2. **play.php 预解析缓存检查（FR-8）**（extractVideoUrlForEpisode 入口）：以原始 URL 为 key 查询 `playerPageCache`，若命中且未过期（5 分钟内），直接返回缓存的视频流 URL，跳过整个三层解析。
3. **R5 去重锁检查（FR-1）**（**extractWithWebView 入口**，覆盖全部 4 个调用路径）：以 `java.net.URL(url).path` 提取 path 作为 key，查询 `r5InProgress`：
   - 命中：表示已有进行中的 R5 嗅探，直接 `await()` 复用结果，避免重复创建 WebView
   - 未命中：创建新的 `Deferred` 存入 map，执行内部嗅探逻辑（extractWithWebViewInternal），完成后从 map 中 remove
4. **单次定时清理兜底（I1 整改）**：首个未完成 Deferred 触发一次 60s 定时清理任务，避免高频场景创建大量清理协程；Deferred 完成后立即 remove 是主路径。
5. **解析成功后写入 FR-8 缓存**（extractVideoUrlForEpisode 出口）：若解析出的视频流 URL 与原始 URL 不同（说明是播放器页面 URL），写入 `playerPageCache` 供下次复用。

### 数据流 2：视频流网络请求降级数据流（FR-3 + FR-5 + FR-7）

当 OkHttp 发起视频流网络请求时，请求依次经过拦截器链：

1. **CronetInterceptor.intercept 入口检查**（按顺序执行）：
   - **FR-3 视频流检测**（第一优先）：提取 `original.url.encodedPath`，检查是否以 .m3u8/.mp4/.ts/.flv/.mkv/.webm 结尾。命中则直接 `chain.proceed(original)` 走 OkHttp（跳过 Cronet）。强制 HTTP/1.1 由 videoStreamClient 保证（见 FR-3 HttpHelper 代码片段）。**E6 整改**：ExoPlayerHelper L417/L740 的 m3u8 预检查请求（走 okHttpClient + CronetInterceptor，HTTP/2）是 ERR_HTTP2_PROTOCOL_ERROR 真实来源，需改用 videoStreamClient。
   - **FR-7 证书错误记忆检查**（W5 整改：在 FR-3 视频流检查之后、Cronet 执行之前）：查询 `certErrorCache[host]`，若存在且未过期（5 分钟内），直接走 OkHttp 不尝试 Cronet。
2. **若走 Cronet 且失败**：
   - 证书错误（ERR_CERT_/ERR_SSL_）：写入 `certErrorCache[host]=now+300000`，降级 OkHttp
   - HTTP/2 协议错误：累计降级计数，达阈值降级 OkHttp
3. **StreamResetRetryInterceptor 拦截**：
   - 捕获 StreamResetException
   - **FR-5 移除 Call.cancel() 改用连接池清理**（E2 整改）：移除 `chain.call().cancel()`（原 L41，它会取消整个 Call 导致重试必然失败），改用 `io.legado.app.help.http.okHttpClient.connectionPool().evictAll()` 清理故障连接，重试时 Call 状态保持可用，`chain.proceed(request)` 可正常执行

### 数据流 3：favicon.ico 请求缓存数据流（FR-4）

当 OkHttp 发起 favicon.ico 请求时：

1. **HttpHelper 拦截器入口检查**：检查 `request.url.encodedPath == "/favicon.ico"`，命中则进入 FaviconCache 流程。
2. **内存缓存查询**：以 host 为 key 查询 LruCache，命中直接构造 Response 返回（<10ms）。
3. **并行请求合并检查**：查询 `inProgressMap[host]`，若存在进行中的请求，`await()` 复用结果，避免并发重复请求。
4. **磁盘缓存查询**：检查磁盘缓存文件是否存在且未过期（24h），命中则读取并写入内存缓存返回（<50ms）。
5. **网络请求**：发起真实网络请求，成功后写入内存缓存 + 磁盘缓存，并通知所有等待中的 Deferred。

### 数据流 4：DoH 健康检查数据流（FR-2）

App 启动时 `App.onCreate` 后台调用 `DohDns.preheatDohServers()`：

1. **并行探测 2 个 DoH 服务器**：对每个 DoH 服务器发起探测请求（解析常见域名），记录延迟和成功率。
2. **写入健康状态**：更新 `dohHealthStatus[serverUrl] = HealthEntry(avgLatencyMs, successCount, failCount, lastCheckMs)`。
3. **选择最优服务器**：将平均延迟最低且成功率最高的服务器设为 `lastSuccessServer`，后续 `parallelLookup` 优先出发。
4. **运行时负缓存优化**：`NEGATIVE_CACHE_TTL_MS` 从 30s 降至 10s，DoH 失败的域名 10s 后即可重新尝试 DoH，减少污染时长。

### 数据流 5：Cronet 探测跳过日志采样数据流（FR-6）

当 Cronet 处于降级态且有非失败 host 请求到达时：

1. **原逻辑**：每次都输出 `AppLog.putDebug("Cronet 探测跳过非失败host...")`，152 次/会话。
2. **FR-6 采样逻辑**：`probeSkipCount.incrementAndGet()`，每 10 次输出 1 次汇总日志 `"Cronet 探测跳过非失败host (最近10次, host前3=xxx***)"`，日志量降至 ~15 条/会话。

---

## 五、File Changes（文件变更清单）

| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 修改 | FR-1（E1 整改）: 新增 `r5InProgress` ConcurrentHashMap + `r5CleanupScope` 协程作用域，**重命名原方法为 `extractWithWebViewInternal`，新增 `extractWithWebView` 作为去重入口**（覆盖 4 个调用路径）；I1 整改: 单次定时清理任务替代每次 launch 60s 协程；FR-8: 新增 `playerPageCache` + `PlayerPageCacheEntry` data class（保留在 extractVideoUrlForEpisode 入口） |
| `app/src/main/java/io/legado/app/help/http/DohDns.kt` | 修改 | FR-2: `NEGATIVE_CACHE_TTL_MS` 从 30_000L 改为 10_000L；新增 `dohHealthStatus` ConcurrentHashMap + `HealthEntry` data class + `preheatDohServers()` 公共方法 |
| `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` | 修改 | FR-3: intercept 入口新增 `isVideoStreamPath()` 检查，视频流跳过 Cronet；FR-6: 新增 `probeSkipCount` AtomicInteger，日志采样；FR-7: 新增 `certErrorCache` ConcurrentHashMap + 证书错误记忆逻辑 |
| `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` | 修改 | FR-3（E3 整改）: **必须**新增 `videoStreamClient`（protocols=HTTP_1_1），视频流请求发起方使用该 client；FR-4: 拦截器入口检查 `/favicon.ico`，命中走 FaviconCache |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 修改 | FR-3（E6 整改）: L417/L740 的 `okHttpClient.newCall(request).execute()`（m3u8 预检查等请求）改用 `HttpHelper.videoStreamClient`，强制 HTTP/1.1（视频流播放主路径 okhttpDataFactory 已 HTTP/1.1，此为 ERR_HTTP2_PROTOCOL_ERROR 真实来源） |
| `app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt` | 修改 | FR-5（E2 整改）: 移除 `chain.call().cancel()`（L41），改用 `io.legado.app.help.http.okHttpClient.connectionPool().evictAll()` 清理连接池，重试时 Call 状态保持可用 |
| `app/src/main/java/io/legado/app/help/http/FaviconCache.kt` | 新建 | FR-4（W4 整改）: object 单例，内存 LruCache（4MB）+ 磁盘缓存（按域名，24h）+ 并行请求合并（synchronized + host 级锁，同步方法不涉及 suspend） |
| `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` | 修改 | FR-9（E4 整改）: `ReadVideoUrlsRunnable` 的 `GSON.fromJsonArray` 失败时降级为正则提取（正则覆盖 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd 全格式，I2 整改） |
| `app/src/main/java/io/legado/app/App.kt`（或 Application 入口） | 修改 | FR-2: 在 `onCreate` 后台调用 `DohDns.preheatDohServers()` |

---

## 六、FR 详细设计

### FR-1（P0）: R5 嗅探去重锁

**文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`

**设计依据**：日志分析报告 P0-2 节，R5 嗅探重复率 41%，17 次多余启动，76 次 ExoPlayer scope cancelled。

**实现要点**（E1 整改：去重锁位置修正）：

1. VideoUrlExtractor 是 `object` 单例（非 class），直接在 object 内定义私有字段（无需 companion object）
2. **去重锁必须放在 `extractWithWebView` 方法入口**（不是 `extractVideoUrlForEpisode`），因为 `extractWithWebView` 有 4 个调用方（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552），`extractVideoUrlForEpisode` 只是其中之一。放在 `extractVideoUrlForEpisode` 层只能覆盖 1/4 路径，无法消除 41% 重复率
3. 将原 `extractWithWebView` 方法重命名为 `extractWithWebViewInternal`（私有），新增 `extractWithWebView` 作为去重入口，保留原签名以兼容 4 个调用方
4. FR-8 play.php 预解析缓存保留在 `extractVideoUrlForEpisode` 入口（URL 级别快速路径，与 R5 path 级别去重层级不同，互不冲突）
5. **I1 整改：60s 清理协程优化**——不再每次嗅探都 launch 一个 60s 协程（高频场景会创建 41 个协程），改为：Deferred 完成后立即 remove + 单次定时清理任务兜底

**关键代码片段**：

```kotlin
object VideoUrlExtractor {
    // FR-1: R5 嗅探去重锁（放在 extractWithWebView 层，覆盖全部 4 个调用路径）
    private val r5InProgress = ConcurrentHashMap<String, Deferred<String?>>()
    private val r5CleanupScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    // I1 整改：单次定时清理标志，避免每次嗅探都 launch 60s 协程
    @Volatile
    private var cleanupScheduled = false
    private const val R5_CLEANUP_DELAY_MS = 60_000L

    // FR-8: play.php 类 URL 预解析缓存（URL 级别，保留在 extractVideoUrlForEpisode 入口）
    private data class PlayerPageCacheEntry(val videoUrl: String, val timestamp: Long)
    private val playerPageCache = ConcurrentHashMap<String, PlayerPageCacheEntry>()
    private const val PLAYER_PAGE_CACHE_TTL_MS = 5 * 60 * 1000L

    /**
     * FR-8: play.php 预解析缓存入口（URL 级别快速路径）
     *
     * 不做 R5 去重，仅做 URL 级别缓存命中检查，未命中则调用 extractWithWebView
     */
    suspend fun extractVideoUrlForEpisode(
        url: String,
        source: BaseSource?,
        rssArticle: RssArticle?
    ): String? {
        if (url.isBlank()) return null
        // Bug-fix 2026-07-26: URL 已是视频流格式时直接返回
        if (isDirectVideoStreamUrl(url)) {
            AppLog.putInfo("extractVideoUrlForEpisode: URL已是视频流, 跳过去重, ${sanitizeUrl(url)}")
            return url
        }
        // FR-8: play.php 预解析缓存检查
        val cachedEntry = playerPageCache[url]
        if (cachedEntry != null && System.currentTimeMillis() - cachedEntry.timestamp < PLAYER_PAGE_CACHE_TTL_MS) {
            AppLog.putDebug("FR-8 预解析缓存命中, ${sanitizeUrl(url)}")
            return cachedEntry.videoUrl
        }
        // 调用 extractWithWebView（FR-1 去重锁在此方法内）
        val result = extractWithWebView(url, source)
        // FR-8: 解析成功且结果与原 URL 不同，写入预解析缓存
        if (result != null && result != url) {
            playerPageCache[url] = PlayerPageCacheEntry(result, System.currentTimeMillis())
        }
        return result
    }

    /**
     * FR-1: R5 嗅探去重入口（覆盖全部 4 个调用路径）
     *
     * 去重锁放在此方法入口，因为 extractWithWebView 有 4 个调用方：
     * - VideoPlay.kt L425（R5 单 URL 分支未命中时）
     * - VideoPlay.kt L520（多 URL 分支）
     * - VideoPlay.kt L547（WebView 降级分支）
     * - VideoUrlExtractor.kt L552（extractVideoUrlForEpisode 内部第三层）
     *
     * 同一 path 的 R5 嗅探请求复用结果，避免重复 WebView 创建
     * 已知上限：path 作为 key 可能在不同 host 间冲突（实际场景中 RSS 源 host 稳定，冲突概率低）
     * 升级路径：如需更精细去重可加入 host 维度
     */
    suspend fun extractWithWebView(
        url: String,
        source: BaseSource?,
        delayTime: Long = R5_DELAY_TIME,
        timeout: Long = R5_TIMEOUT
    ): String? {
        if (url.isBlank()) return null
        // FR-1: 提取 path 作为去重 key
        val path = try {
            java.net.URL(url).path ?: url
        } catch (e: Exception) {
            url
        }
        // 检查是否有进行中的 R5 嗅探
        r5InProgress[path]?.let { existing ->
            AppLog.putDebug("FR-1 R5嗅探去重命中, 复用结果, path=${path.take(20)}")
            return existing.await()
        }
        // 创建新的 Deferred 执行嗅探
        val deferred = r5CleanupScope.async {
            extractWithWebViewInternal(url, source, delayTime, timeout)
        }
        r5InProgress[path] = deferred
        // I1 整改：不再每次 launch 60s 协程，改为调度单次定时清理兜底
        scheduleR5CleanupOnce()
        return try {
            deferred.await()
        } finally {
            // Deferred 完成（正常或异常）后立即 remove，避免泄漏
            r5InProgress.remove(path)
        }
    }

    /**
     * I1 整改：单次定时清理兜底
     *
     * 只有首个未完成的 Deferred 会触发调度，后续调用复用已调度的清理任务
     * 避免高频场景（41 次/会话）创建 41 个 60s 协程
     */
    private fun scheduleR5CleanupOnce() {
        if (cleanupScheduled) return
        synchronized(this) {
            if (cleanupScheduled) return
            cleanupScheduled = true
            r5CleanupScope.launch {
                delay(R5_CLEANUP_DELAY_MS)
                // 60s 后清理所有未完成的 Deferred（极端情况兜底）
                r5InProgress.clear()
                cleanupScheduled = false
            }
        }
    }

    /**
     * 原 R5 嗅探逻辑（重命名为 Internal）
     */
    private suspend fun extractWithWebViewInternal(
        url: String,
        source: BaseSource?,
        delayTime: Long,
        timeout: Long
    ): String? {
        // 原 extractWithWebView 方法体不变（R5 嗅探核心逻辑迁移至此）
        // ...省略原嗅探逻辑（WebView 创建 + shouldInterceptRequest 抓包 + window.__videoUrls__ 读取）...
    }
}
```

**已知上限**：path 作为 key 可能在不同 host 间冲突（实际场景中 RSS 源 host 稳定，冲突概率低）；单次定时清理任务在 60s 窗口内可能清理掉仍在执行的嗅探（极端情况， Deferred 完成后立即 remove 已是主路径，定时清理仅兜底）。

---

### FR-2（P1）: DoH 负缓存时长优化 + 健康检查

**文件**：`app/src/main/java/io/legado/app/help/http/DohDns.kt`

**设计依据**：日志分析报告 P1-1 节，21 条 DoH 失败日志，1 次 DoH 被禁用 5 分钟，负缓存污染导致后续请求持续走系统 DNS。

**实现要点**：

1. `NEGATIVE_CACHE_TTL_MS` 从 `30_000L` 改为 `10_000L`（L104）
2. 新增 `dohHealthStatus` 记录每服务器健康状态
3. 新增 `preheatDohServers()` 公共方法供 App.onCreate 调用
4. 复用现有 `preheatScope` 协程作用域
5. **E7 整改：处理与已有 asyncPreheatDoh 的关系**：DohDns.kt 已有 `asyncPreheatDoh()` 方法（L259，冷启动失败后 30s 异步预热），新增 `preheatDohServers()` 需明确两者职责分工：
   - `preheatDohServers()`（新增）：App.onCreate 启动时主动探测，选择最优服务器为主（冷启动前预热）
   - `asyncPreheatDoh()`（已有）：冷启动场景首次 DoH 失败后，30s 后异步探测恢复
   - 两者不冲突：preheatDohServers 在 App 启动时执行，asyncPreheatDoh 仅在冷启动失败后触发
6. **E7 整改：修复 asyncPreheatDoh 探测域名**：将 DohDns.kt:262 的 `cloudflare-dns.com`（国外域名，国内可能不可达）改为 `www.baidu.com`（国内域名），与 preheatDohServers 统一探测域名

**关键代码片段**：

```kotlin
object DohDns : Dns {
    // FR-2: 负缓存时长从 30s 降至 10s，减少污染时长
    private const val NEGATIVE_CACHE_TTL_MS = 10_000L  // 原值 30_000L

    // FR-2: DoH 服务器健康状态
    data class HealthEntry(
        val avgLatencyMs: Long,
        val successCount: Int,
        val failCount: Int,
        val lastCheckMs: Long
    )
    private val dohHealthStatus = ConcurrentHashMap<String, HealthEntry>()

    /**
     * FR-2: DoH 服务器预热健康检查
     *
     * 在 App.onCreate 后台调用，并行探测 2 个 DoH 服务器延迟，
     * 选择更优的为主（写入 lastSuccessServer），提升冷启动 DNS 解析成功率
     *
     * 已知上限：探测请求增加少量启动网络流量（2 次 DoH 查询）
     * 升级路径：如需动态调整可改为定时周期探测
     */
    fun preheatDohServers() {
        preheatScope.launch {
            val probeHost = "www.baidu.com"  // W6 整改：国内域名探测，与 DoH 服务器（阿里+腾讯）实际使用场景一致
            val clients = kotlin.runCatching { dohClients }.getOrElse {
                AppLog.put("FR-2 preheatDohServers: dohClients init failed")
                return@launch
            }
            clients.forEachIndexed { idx, client ->
                val startMs = System.currentTimeMillis()
                val result = kotlin.runCatching { client.lookup(probeHost) }
                val elapsed = System.currentTimeMillis() - startMs
                val serverUrl = DOH_SERVERS[idx].url
                val healthEntry = if (result.isSuccess && result.getOrNull()?.isNotEmpty() == true) {
                    HealthEntry(elapsed, 1, 0, System.currentTimeMillis())
                } else {
                    HealthEntry(Long.MAX_VALUE, 0, 1, System.currentTimeMillis())
                }
                dohHealthStatus[serverUrl] = healthEntry
                AppLog.putDebug("FR-2 DoH server#${idx + 1} preheat: success=${result.isSuccess}, latency=${elapsed}ms")
            }
            // 选择延迟最低且成功的服务器为主
            val bestServer = dohHealthStatus.entries
                .filter { it.value.successCount > 0 }
                .minByOrNull { it.value.avgLatencyMs }
            if (bestServer != null) {
                val bestIdx = DOH_SERVERS.indexOfFirst { it.url == bestServer.key }
                if (bestIdx >= 0) {
                    lastSuccessServer.set(bestIdx)
                    AppLog.put("FR-2 DoH preheat selected server#${bestIdx + 1} as primary, latency=${bestServer.value.avgLatencyMs}ms")
                }
            }
        }
    }
}
```

**已知上限**：探测请求增加 2 次启动网络流量；健康状态仅启动时探测一次，运行时不再更新（如需动态调整可改为定时周期探测）。

---

### FR-3（P1）: 视频流强制 HTTP/1.1

**文件**：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` + `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` + `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

**设计依据**：日志分析报告 P1-2 节，3 次 ERR_HTTP2_PROTOCOL_ERROR（InternalErrorCode=-337），发生在 206 Partial Content 分片加载时。

**实现要点**（E3 整改：videoStreamClient 必须方案 + E6 整改：三重覆盖 + 诊断先行）：

1. 在 `CronetInterceptor.intercept` 入口检测 path 后缀
2. 视频流请求跳过 Cronet，走 OkHttp
3. **E3 整改关键**：跳过 Cronet 不等于强制 HTTP/1.1（OkHttp 默认协商 HTTP/2），**必须**在 HttpHelper 中新建 `videoStreamClient`（`protocols=listOf(Protocol.HTTP_1_1)`）
4. 拦截器内动态设置 protocols 不可行（protocols 是 OkHttpClient 级别配置，非请求级别）
5. **E6 整改关键**：修改 ExoPlayerHelper.kt L417/L740 的 `okHttpClient.newCall(request).execute()`（m3u8 预检查等请求）改用 `HttpHelper.videoStreamClient`，使其强制 HTTP/1.1。视频流播放主路径走 ExoPlayer DataSource（okhttpDataFactory 已 HTTP/1.1），但 m3u8 预检查等请求走 okHttpClient + CronetInterceptor（HTTP/2），是 ERR_HTTP2_PROTOCOL_ERROR 的真实来源
6. **E6 整改：诊断先行**：实施前先在 CronetInterceptor.isProtocolError 分支（L324）增加日志输出请求 path + 调用栈，确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源，再针对性修复

**关键代码片段**（CronetInterceptor.kt）：

```kotlin
class CronetInterceptor(private val cookieJar: CookieJar) : Interceptor {
    companion object {
        // FR-7: 证书错误记忆缓存
        private val certErrorCache = ConcurrentHashMap<String, Long>()
        private const val CERT_ERROR_CACHE_TTL_MS = 5 * 60 * 1000L  // 5 分钟

        /**
         * FR-3: 判断 path 是否为视频流
         *
         * 检测 .m3u8/.mp4/.ts/.flv/.mkv/.webm 后缀
         * 已知上限：无后缀的视频流 URL 会漏判（日志显示当前问题 URL 均有明确后缀）
         */
        private fun isVideoStreamPath(path: String): Boolean {
            val lower = path.lowercase().substringBefore("?").substringBefore("#")
            return lower.endsWith(".m3u8") || lower.endsWith(".mp4") ||
                lower.endsWith(".ts") || lower.endsWith(".flv") ||
                lower.endsWith(".mkv") || lower.endsWith(".webm")
        }
    }

    @Throws(IOException::class)
    override fun intercept(chain: Interceptor.Chain): Response {
        if (chain.call().isCanceled()) {
            throw IOException("Canceled")
        }
        val original: Request = chain.request()
        // FR-3: 视频流跳过 Cronet（强制 HTTP/1.1 由 videoStreamClient 保证，见 HttpHelper.kt）
        val path = original.url.encodedPath
        if (isVideoStreamPath(path)) {
            AppLog.putDebug("FR-3 视频流跳过Cronet, path=${path.take(30)}")
            return chain.proceed(original)
        }
        // FR-7: 证书错误记忆缓存检查（在 FR-3 视频流检查之后、Cronet 执行之前）
        val host = original.url.host
        val certCacheExpiry = certErrorCache[host]
        if (certCacheExpiry != null && System.currentTimeMillis() < certCacheExpiry) {
            AppLog.putDebug("FR-7 证书错误记忆命中, 跳过Cronet, host=${host.take(3)}***")
            return chain.proceed(original)
        }
        // ... 原 intercept 逻辑 ...
    }
}
```

**关键代码片段**（HttpHelper.kt，必须方案）：

```kotlin
// FR-3（E3 整改）: 视频流专用 OkHttpClient（强制 HTTP/1.1）
// 必须方案：跳过 Cronet 不等于强制 HTTP/1.1，OkHttp 默认协商 HTTP/2
// 已知上限：独立 client 增加连接池开销
// 升级路径：如需精确控制可改为自定义 ConnectionPool
val videoStreamClient: OkHttpClient by lazy {
    okHttpClient.newBuilder()
        .protocols(listOf(okhttp3.Protocol.HTTP_1_1))
        .build()
}

// 使用方（ExoPlayerHelper m3u8 预检查等请求，E6 整改）：
// 视频流请求发起时使用 HttpHelper.videoStreamClient 而非 okHttpClient
// 例如：videoStreamClient.newCall(request).execute()
```

**关键代码片段**（ExoPlayerHelper.kt，E6 整改：m3u8 预检查请求改用 videoStreamClient）：

```kotlin
// FR-3（E6 整改）: L417/L740 的 m3u8 预检查等请求改用 videoStreamClient（强制 HTTP/1.1）
// 视频流播放主路径走 ExoPlayer DataSource（okhttpDataFactory 已 HTTP/1.1），不经过 CronetInterceptor
// 但 m3u8 预检查等请求走 okHttpClient + CronetInterceptor（HTTP/2），是 ERR_HTTP2_PROTOCOL_ERROR 真实来源

// 原 L417 / L740 附近（m3u8 预检查请求）：
// val response = okHttpClient.newCall(request).execute()
// 改为：
val response = HttpHelper.videoStreamClient.newCall(request).execute()

// 已知上限：仅修改 L417/L740 两处已知的 m3u8 预检查请求，其他 okHttpClient.newCall 调用需实施时根据诊断日志确认是否需要同步修改
// 升级路径：如需全局统一，可让 okHttpClient 默认 protocols=HTTP_1_1（但影响非视频流请求的 HTTP/2 多路复用）
```

**实施前诊断步骤**（E6 整改：诊断先行）：

实施 FR-3 前，先在 CronetInterceptor.isProtocolError 分支（L324）增加诊断日志，确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源：

```kotlin
// 在 CronetInterceptor.kt L324 isProtocolError 分支增加诊断日志
if (isProtocolError(errMsg)) {
    // E6 诊断：输出请求 path + 调用栈，确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源
    AppLog.put("FR-3 诊断: ERR_HTTP2_PROTOCOL_ERROR, path=${original.url.encodedPath.take(30)}, stack=${Thread.currentThread().stackTrace.take(8).joinToString { it.toString() }}")
    // ... 原降级逻辑 ...
}
```

**已知上限**：path 后缀判断可能漏判无后缀的视频流 URL；独立 videoStreamClient 增加连接池开销（需修改 ExoPlayerHelper L417/L740 使用该 client）；E6 诊断日志需实施时先验证来源再针对性修复（若来源非 L417/L740 则需扩展修改范围）。

---

### FR-4（P1）: favicon.ico 缓存

**文件**：`app/src/main/java/io/legado/app/help/http/FaviconCache.kt`（新建）+ `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`

**设计依据**：日志分析报告 P1-3 节，19:00 会话 137 次 favicon.ico 请求，每次耗时 400-600ms。

**实现要点**（W4 整改：FaviconCache 改为同步方法避免 runBlocking）：

1. 新建 `FaviconCache.kt` object 单例
2. 内存 LruCache（maxSize=4MB）+ 磁盘缓存（按域名，24h 过期）+ 并行请求合并（synchronized + host 级锁）
3. **W4 整改关键**：`getFavicon` 改为同步方法（非 suspend），内部用 synchronized + host 级锁保证线程安全，不涉及协程，避免 runBlocking 阻塞 OkHttp 调度线程
4. 在 HttpHelper 拦截器中检查 path=/favicon.ico，命中直接调用同步方法（无需 runBlocking）

**关键代码片段**（FaviconCache.kt，W4 整改：同步方法）：

```kotlin
package io.legado.app.help.http

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.LruCache
import io.legado.app.constant.AppLog
import splitties.init.appCtx
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap

/**
 * FR-4: favicon.ico 多级缓存（W4 整改：同步方法，不涉及 suspend）
 *
 * 三级缓存：内存 LruCache（4MB）+ 磁盘缓存（按域名，24h）+ 并行请求合并（synchronized + host 级锁）
 *
 * 已知上限：内存占用 4MB | 磁盘缓存 24h TTL 可能延迟感知 favicon 更新 | synchronized 同一 host 请求串行化
 * 升级路径：如需即时更新可加入手动刷新接口；如需更高并发可改用 ReadWriteLock
 */
object FaviconCache {
    private const val MEMORY_CACHE_MAX_SIZE = 4 * 1024 * 1024L  // 4MB
    private const val DISK_CACHE_TTL_MS = 24 * 60 * 60 * 1000L  // 24h
    private const val DISK_CACHE_DIR = "favicon_cache"

    private val memoryCache = object : LruCache<String, Bitmap>(MEMORY_CACHE_MAX_SIZE.toInt()) {
        override fun sizeOf(key: String, value: Bitmap): Int = value.byteCount
    }

    // W4 整改：用 host 级锁替代 Deferred 实现并行请求合并（同步，不涉及协程）
    private val hostLocks = ConcurrentHashMap<String, Any>()

    private val diskCacheDir: File by lazy {
        File(appCtx.cacheDir, DISK_CACHE_DIR).apply { mkdirs() }
    }

    /**
     * 获取 favicon Bitmap（W4 整改：同步方法，非 suspend）
     *
     * @param host 域名
     * @param networkFetcher 网络请求回调（同步，返回 Bitmap 或 null）
     * 已知上限：同一 host 的并发请求会串行化（synchronized），但 favicon 请求低频可接受
     */
    fun getFavicon(host: String, networkFetcher: () -> Bitmap?): Bitmap? {
        if (host.isBlank()) return null
        // 1. 内存缓存命中（快速路径，无锁）
        memoryCache.get(host)?.let {
            AppLog.putDebug("FR-4 favicon 内存缓存命中, host=${host.take(3)}***")
            return it
        }
        // 2. 同步执行：磁盘查询 + 网络请求（用 host 级锁保证线程安全 + 请求合并）
        val lock = hostLocks.computeIfAbsent(host) { Any() }
        synchronized(lock) {
            // 双重检查：可能在等待锁期间其他线程已写入缓存
            memoryCache.get(host)?.let {
                AppLog.putDebug("FR-4 favicon 内存缓存命中(等待后), host=${host.take(3)}***")
                return it
            }
            // 磁盘缓存查询
            val diskBitmap = readFromDisk(host)
            if (diskBitmap != null) {
                memoryCache.put(host, diskBitmap)
                AppLog.putDebug("FR-4 favicon 磁盘缓存命中, host=${host.take(3)}***")
                return diskBitmap
            }
            // 网络请求
            val networkBitmap = networkFetcher()
            if (networkBitmap != null) {
                memoryCache.put(host, networkBitmap)
                writeToDisk(host, networkBitmap)
            }
            return networkBitmap
        }
    }

    private fun readFromDisk(host: String): Bitmap? {
        return try {
            val file = File(diskCacheDir, md5(host))
            if (!file.exists() || System.currentTimeMillis() - file.lastModified() > DISK_CACHE_TTL_MS) {
                return null
            }
            BitmapFactory.decodeFile(file.absolutePath)
        } catch (e: Exception) {
            null
        }
    }

    private fun writeToDisk(host: String, bitmap: Bitmap) {
        try {
            val file = File(diskCacheDir, md5(host))
            file.outputStream().use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
        } catch (e: Exception) {
            AppLog.putDebug("FR-4 favicon 磁盘缓存写入失败, host=${host.take(3)}***")
        }
    }

    private fun md5(input: String): String {
        val md = MessageDigest.getInstance("MD5")
        val bytes = md.digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
```

**关键代码片段**（HttpHelper.kt 拦截器入口，W4 整改：移除 runBlocking）：

```kotlin
// FR-4（W4 整改）: favicon.ico 缓存检查（同步调用，无需 runBlocking）
.addInterceptor { chain ->
    val request = chain.request()
    val path = request.url.encodedPath
    if (path == "/favicon.ico") {
        val host = request.url.host
        // W4 整改：直接调用同步方法，不再用 runBlocking 包裹
        val bitmap = FaviconCache.getFavicon(host) {
            // 执行真实网络请求获取 Bitmap（同步回调）
            val response = chain.proceed(request)
            response.body?.byteStream()?.use {
                android.graphics.BitmapFactory.decodeStream(it)
            }
        }
        // 若获取到 Bitmap，构造缓存 Response 返回
        if (bitmap != null) {
            // 构造 Response（省略具体实现，用 bitmap 转 ResponseBody）
        }
    }
    chain.proceed(request)
}
```

**已知上限**：内存占用 4MB；磁盘缓存 24h TTL 可能延迟感知 favicon 更新；同一 host 的并发请求会串行化（synchronized，favicon 请求低频可接受）。W4 整改后已移除 runBlocking 阻塞 OkHttp 调度线程的风险。

---

### FR-5（P2）: StreamReset 重试移除 Call.cancel() 改用连接池清理（E2 整改）

**文件**：`app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt`

**设计依据**（E2 整改根因修正）：日志分析报告 P2-1 节原归因为"Activity onPause 导致协程作用域取消"，但源码铁证日志时序 6608（重试）→ 6609（Canceled）→ 6610（onPause），6609 在 6610 之前，证明 Canceled 不是 Activity 切换导致。真实根因：`StreamResetRetryInterceptor.kt:41` 的 `chain.call().cancel()` 设置了 Call 的 canceled 标志，导致后续 `chain.proceed(request)`（L44）检查标志时抛出 `IOException("Canceled")`。NonCancellable 只保护协程取消，不保护 OkHttp `Call.cancel()`，原方案完全无效。

**实现要点**：

1. **移除 `chain.call().cancel()`**（原 L41）：它会取消整个 Call 导致重试必然失败
2. 改用 `io.legado.app.help.http.okHttpClient.connectionPool().evictAll()` 清理连接池（淘汰故障连接，不影响 Call 状态）
3. 重试时 Call 状态保持可用，`chain.proceed(request)` 可正常执行
4. 保留 `chain.connection()?.socket()?.close()` 清理当前 socket

**关键代码片段**：

```kotlin
@Keep
object StreamResetRetryInterceptor : Interceptor {
    private const val MAX_RETRY = 1

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        return try {
            chain.proceed(request)
        } catch (e: IOException) {
            if (isStreamResetException(e)) {
                val host = request.url.host
                AppLog.put("StreamReset 重试, host=${host.take(3)}***, error=${e.message?.take(60)}")
                // FR-5 整改：移除 chain.call().cancel()，它会取消整个 Call 导致重试必然失败
                // 改用连接池清理：淘汰该 host 的所有连接，不影响 Call 状态
                // E5 整改：chain.call().client() API 不可行（OkHttp 4.12.0 Call 接口无 client() 方法），
                // 改为直接引用 io.legado.app.help.http.okHttpClient（StreamResetRetryInterceptor 是 object 单例，可引用同模块 HttpHelper 全局 okHttpClient，HttpHelper.kt:75）
                try {
                    // 清理空闲连接（evictAll 会清理所有空闲连接）
                    // 已知上限：evictAll 影响其他请求的连接复用，连接数多时有轻微开销
                    // 升级路径：如需精确按 host 清理，需自定义 ConnectionPool
                    io.legado.app.help.http.okHttpClient.connectionPool().evictAll()
                } catch (ignore: Exception) {}
                chain.connection()?.socket()?.close()
                // 重试（Call 未被 cancel，可正常执行）
                return try {
                    chain.proceed(request)
                } catch (e2: IOException) {
                    AppLog.put("StreamReset 重试失败, host=${host.take(3)}***, error=${e2.message?.take(60)}")
                    throw e2
                }
            } else {
                throw e
            }
        }
    }
}
```

**已知上限**：`evictAll()` 会清理所有空闲连接，可能影响其他请求的连接复用（连接数多时有轻微开销）；升级路径为自定义 ConnectionPool 实现按 host 精确清理。原方案的 runBlocking 阻塞调度线程 + NonCancellable 无法外部取消风险已消除（方案重写后不再使用 runBlocking）。

---

### FR-6（P2）: Cronet 探测跳过日志采样

**文件**：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`（L189 附近）

**设计依据**：日志分析报告 P2-2 节，09:12 会话 152 次"探测跳过非失败host"日志，每次请求都判断 host 是否匹配 hintHost。

**实现要点**：

1. 新增 `probeSkipCount = AtomicInteger(0)`
2. 每 10 次跳过输出 1 次汇总日志
3. 改造 L189 的 `AppLog.putDebug("Cronet 探测跳过非失败host...")`

**关键代码片段**：

```kotlin
companion object {
    // FR-6: 探测跳过日志采样计数器
    private val probeSkipCount = java.util.concurrent.atomic.AtomicInteger(0)
    private const val PROBE_SKIP_LOG_INTERVAL = 10  // 每 10 次输出 1 次

    /**
     * FR-6: 探测跳过日志采样
     *
     * 每 10 次跳过输出 1 次汇总日志，减少日志噪声（原 152 次/会话 → ~15 次/会话）
     */
    private fun logProbeSkip(requestHost: String, hintHost: String) {
        val count = probeSkipCount.incrementAndGet()
        if (count % PROBE_SKIP_LOG_INTERVAL == 0) {
            AppLog.putDebug("FR-6 Cronet 探测跳过非失败host (最近${PROBE_SKIP_LOG_INTERVAL}次, host前3=${requestHost.take(3)}***, hintHost前3=${hintHost.take(3)}***)")
        }
    }
}

// 在 intercept 中原 L189 处替换：
// 原：AppLog.putDebug("Cronet 探测跳过非失败host: requestHost=${requestHost.take(3)}***, hintHost=${hint.take(3)}***")
// 新：
logProbeSkip(requestHost, hint)
```

**已知上限**：采样日志可能丢失单次异常详情（每 10 次只输出 1 次）；计数器无上限（Long 范围内不会溢出）。

---

### FR-7（P2）: 证书错误记忆缓存

**文件**：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`

**设计依据**：日志分析报告 P2-3 节，~10 次 ERR_CERT_AUTHORITY_INVALID，每次都尝试 Cronet 再降级 OkHttp，浪费往返。

**实现要点**（W5 整改：明确检查位置）：

1. 新增 `certErrorCache = ConcurrentHashMap<String, Long>()`，key=host，value=过期时间戳
2. **certErrorCache 检查位置在 FR-3 视频流检查之后、Cronet 执行之前**（intercept 方法开头，FR-3 视频流跳过逻辑之后）。命中直接走 OkHttp，不尝试 Cronet
3. 证书错误时写入 `certErrorCache[host]=now+300000`（5 分钟），写入位置在 catch 块的 isCertificateError 分支

**关键代码片段**：

```kotlin
companion object {
    // FR-7: 证书错误记忆缓存（key=host, value=过期时间戳）
    private val certErrorCache = ConcurrentHashMap<String, Long>()
    private const val CERT_ERROR_CACHE_TTL_MS = 5 * 60 * 1000L  // 5 分钟
}

@Throws(IOException::class)
override fun intercept(chain: Interceptor.Chain): Response {
    if (chain.call().isCanceled()) {
        throw IOException("Canceled")
    }
    val original: Request = chain.request()

    // FR-3: 视频流跳过 Cronet（见 FR-3 代码片段）
    val path = original.url.encodedPath
    if (isVideoStreamPath(path)) {
        return chain.proceed(original)
    }

    // FR-7（W5 整改）: 证书错误记忆缓存检查
    // 位置：在 FR-3 视频流检查之后、Cronet 执行之前（intercept 方法开头）
    val host = original.url.host
    val certCacheExpiry = certErrorCache[host]
    if (certCacheExpiry != null && System.currentTimeMillis() < certCacheExpiry) {
        AppLog.putDebug("FR-7 证书错误记忆命中, 跳过Cronet直接走OkHttp, host=${host.take(3)}***")
        return chain.proceed(original)
    }

    // ... 原降级检查 + Cronet 执行逻辑 ...

    // 在 catch 块的 isCertificateError 分支中写入缓存：
    // if (isCertificateError(errMsg)) {
    //     logCertError(errMsg)
    //     certErrorCache[host] = System.currentTimeMillis() + CERT_ERROR_CACHE_TTL_MS  // FR-7: 写入记忆缓存
    //     AppLog.putDebug("FR-7 证书错误写入记忆缓存, host=${host.take(3)}***, ttl=${CERT_ERROR_CACHE_TTL_MS / 60000}min")
    //     try { return chain.proceed(original) } catch (e2: Exception) { ... }
    // }
}
```

**已知上限**：5 分钟 TTL 内即使证书修复也不会重试 Cronet（可接受，证书更新频率低）；缓存仅内存，App 重启后失效。

---

### FR-8（P3）: play.php 类 URL 预解析

**文件**：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`

**设计依据**：日志分析报告 P3-1 节，首帧延迟方差 7.5 倍（701ms~5309ms），慢路径均为 /play.php + 加密 URL 重定向场景。

**实现要点**：

1. 新增 `playerPageCache = ConcurrentHashMap<String, PlayerPageCacheEntry>()`
2. 在 `extractVideoUrlForEpisode` 入口检查缓存（已整合到 FR-1 代码片段中）
3. 解析成功后写入缓存，TTL 5 分钟

**关键代码片段**（已整合到 FR-1 代码片段中，此处单独展示数据结构）：

```kotlin
object VideoUrlExtractor {
    // FR-8: play.php 类 URL 预解析缓存
    private data class PlayerPageCacheEntry(val videoUrl: String, val timestamp: Long)
    private val playerPageCache = ConcurrentHashMap<String, PlayerPageCacheEntry>()
    private const val PLAYER_PAGE_CACHE_TTL_MS = 5 * 60 * 1000L  // 5 分钟

    /**
     * FR-8: 清理预解析缓存（供外部调用，如用户手动刷新）
     */
    fun clearPlayerPageCache() {
        playerPageCache.clear()
        AppLog.putDebug("FR-8 play.php 预解析缓存已清空")
    }

    /**
     * FR-8: 清理过期缓存（可选的定期清理）
     */
    fun cleanExpiredPlayerPageCache() {
        val now = System.currentTimeMillis()
        val iterator = playerPageCache.entries.iterator()
        var removed = 0
        while (iterator.hasNext()) {
            val entry = iterator.next()
            if (now - entry.value.timestamp > PLAYER_PAGE_CACHE_TTL_MS) {
                iterator.remove()
                removed++
            }
        }
        if (removed > 0) {
            AppLog.putDebug("FR-8 清理过期预解析缓存, count=$removed")
        }
    }
}
```

**已知上限**：5 分钟 TTL 内播放器 URL 变更不会感知（视频流 URL 通常稳定，可接受）；缓存仅内存，App 重启失效。

---

### FR-9（P3）: window.__videoUrls__ 解析容错（E4 整改：代码与源码匹配 + I2 整改：正则覆盖全格式）

**文件**：`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`（R5 抓包 JS 解析部分，ReadVideoUrlsRunnable L462-492）

**设计依据**（E4 整改根因修正）：日志分析报告 P3-2 节，1 次 `R5网络抓包: 解析 window.__videoUrls__ 失败`。**E4 整改关键**：原设计文档用 `JSON.parse(videoUrlsStr)`（Kotlin 中无此 API，JS 才有），源码铁证 BackstageWebView.kt L475 实际用 `GSON.fromJsonArray<String>(result)` 解析。容错逻辑应基于 `GSON.fromJsonArray` 失败分支，而非臆造的 `JSON.parse`。

**实现要点**：

1. 基于 `GSON.fromJsonArray<String>(result)` 失败分支添加正则提取容错（不是 `JSON.parse`）
2. 正则覆盖所有 VIDEO_SOURCE_REGEX 支持的格式（m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd，I2 整改）

**关键代码片段**（BackstageWebView.kt ReadVideoUrlsRunnable，修改 L462-492）：

```kotlin
// FR-9（E4 整改）: 修改 BackstageWebView.kt ReadVideoUrlsRunnable
// 原 L475: val urls = GSON.fromJsonArray<String>(result).getOrNull()
// 改为容错分支：GSON 解析失败时正则提取
private inner class ReadVideoUrlsRunnable(
    webView: WebView,
    private val regex: String?
) : Runnable {
    private val mWebView: WeakReference<WebView> = WeakReference(webView)
    override fun run() {
        if (closed || callback == null) return
        mWebView.get()?.evaluateJavascript("JSON.stringify(window.__videoUrls__ || [])") { result ->
            if (closed || callback == null) return@evaluateJavascript
            if (result.isNullOrEmpty() || result == "null" || result == "[]") {
                AppLog.putInfo("R5网络抓包: window.__videoUrls__ 为空, 等待 shouldInterceptRequest 或超时")
                return@evaluateJavascript
            }
            // FR-9: 先用 GSON 解析（源码原有方式），失败时正则提取容错
            val urls = GSON.fromJsonArray<String>(result).getOrNull()
                ?: run {
                    AppLog.putWarn("R5网络抓包: GSON 解析 window.__videoUrls__ 失败, 尝试正则提取")
                    extractUrlsByRegex(result)
                }
            if (urls.isNullOrEmpty()) {
                AppLog.putWarn("R5网络抓包: window.__videoUrls__ 解析失败（GSON + 正则均失败）")
                return@evaluateJavascript
            }
            for (url in urls) {
                if (regex != null && url.matches(regex.toRegex())) {
                    AppLog.putInfo("R5网络抓包: window.__videoUrls__ 命中")
                    val response = StrResponse(this@BackstageWebView.url!!, url)
                    callback?.onResult(response)
                    destroy()
                    return@evaluateJavascript
                }
            }
            AppLog.putInfo("R5网络抓包: window.__videoUrls__ 有 ${urls.size} 个 URL 但无匹配")
        }
    }

    // FR-9（I2 整改）: 正则提取容错，覆盖 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd（与 VIDEO_SOURCE_REGEX 对齐）
    private fun extractUrlsByRegex(jsonStr: String): List<String> {
        val urlRegex = Regex(
            """https?://[^\s"'<>]+\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?[^\s"'<>]*)?""",
            RegexOption.IGNORE_CASE
        )
        return urlRegex.findAll(jsonStr).map { it.value }.toList()
    }
}
```

**已知上限**：正则提取可能抓到非视频流 URL（通过后续 VIDEO_SOURCE_REGEX 二次过滤缓解）；正则已覆盖所有 VIDEO_SOURCE_REGEX 支持的格式（I2 整改后，不再是只匹配 .m3u8）。

---

## 七、已知上限与升级路径汇总

| FR | 已知上限 | 升级路径 |
|----|---------|---------|
| FR-1 | path 作为 key 可能在不同 host 间冲突；单次定时清理任务在 60s 窗口内可能误清理仍在执行的嗅探（I1 整改后） | 加入 host 维度去重；改用 Mutex+Channel 实现 |
| FR-2 | 健康状态仅启动时探测一次；探测增加 2 次启动网络流量 | 改为定时周期探测；加入运行时失败率动态调整 |
| FR-3 | path 后缀判断漏判无后缀 URL；独立 videoStreamClient 增加连接池开销（E3 整改后为必须方案） | 改为 Content-Type 判断；自定义 ConnectionPool 精确控制 |
| FR-4 | 内存占用 4MB；磁盘 24h TTL 延迟感知更新；同一 host 并发请求串行化（W4 整改后已移除 runBlocking 风险） | 加入手动刷新接口；改用 ReadWriteLock 提升并发 |
| FR-5 | `evictAll()` 清理所有空闲连接影响其他请求连接复用 | 自定义 ConnectionPool 实现按 host 精确清理 |
| FR-6 | 采样日志丢失单次异常详情 | 按错误类型分别采样；加入异常详情独立日志 |
| FR-7 | 5 分钟 TTL 内证书修复不重试 Cronet；缓存仅内存 | 加入手动清除接口；持久化到磁盘 |
| FR-8 | 5 分钟 TTL 内 URL 变更不感知；缓存仅内存 | 加入手动刷新接口；按播放量动态调整 TTL |
| FR-9 | 正则提取可能抓到非视频流 URL（通过 VIDEO_SOURCE_REGEX 二次过滤缓解）；I2 整改后正则已覆盖全格式 | 加入 AST 解析提升精准度 |

---

## 八、风险与缓解

### 风险一：FR-1 去重锁可能导致首请求失败影响后续复用

- **场景**：首个 R5 嗅探请求因网络问题失败，复用该 Deferred 的后续请求都会拿到 null
- **缓解**：Deferred 失败时不缓存结果，后续请求会创建新的 Deferred 重试；60s 超时清理保证不会长时间持有失败结果

### 风险二：FR-5 连接池 evictAll 可能影响其他请求连接复用（E2 整改后新风险）

- **场景**：StreamReset 重试时调用 `connectionPool.evictAll()` 清理所有空闲连接，可能影响其他正在进行请求的连接复用，导致短暂性能下降
- **缓解**：StreamReset 重试频率低（日志显示 1 次/会话），evictAll 影响范围有限；空闲连接会被 OkHttp 自动重建；升级路径为自定义 ConnectionPool 按 host 精确清理

### 风险三：FR-3 视频流判断漏判导致 HTTP/2 协议错误持续

- **场景**：无后缀的视频流 URL（如 /video?id=xxx）走 Cronet 仍触发 ERR_HTTP2_PROTOCOL_ERROR
- **缓解**：日志显示当前问题 URL 均有明确后缀；漏判时会回退到原有 Cronet 降级逻辑，不影响功能可用性

### 风险四：FR-4 favicon 缓存内存占用过高

- **场景**：低端设备上 4MB LruCache 可能加剧内存压力
- **缓解**：LruCache 自动 LRU 淘汰；可按设备内存动态调整 maxSize（如 <2GB RAM 设备降至 2MB）

### 风险五：FR-2 DoH 健康检查探测时机不当

- **场景**：App onCreate 时网络未就绪，探测结果不准确
- **缓解**：探测在 preheatScope 后台协程执行，不阻塞 onCreate；探测失败时保持默认服务器顺序，不影响功能

---

## 九、验证方案

### 单元测试

- FR-1: 验证同一 path 并发调用返回同一结果；不同 path 不互相阻塞
- FR-8: 验证缓存命中/过期/清除逻辑
- FR-4: 验证内存/磁盘/网络三级缓存命中顺序
- FR-9: 验证 GSON.fromJsonArray 解析失败时正则提取正确性（E4 整改后基于 GSON）

### 真机测试（按项目规范使用测试包 `io.legado.miss.app.debug`）

- 复现日志分析报告场景，验证：
  - R5 嗅探重复率从 41% 降至 5% 以下（统计 appLog 中"FR-1 R5嗅探去重命中"次数）
  - favicon.ico 网络请求从 137 次降至 <10 次（首次加载 + 缓存过期后）
  - 视频流 ERR_HTTP2_PROTOCOL_ERROR 次数降为 0
  - Cronet 探测跳过日志从 152 次降至 ~15 次
  - StreamReset 重试成功率提升（无"重试失败, error=Canceled"日志）

### 日志验证点

- `FR-1 R5嗅探去重命中` 日志出现且次数合理
- `FR-3 视频流跳过Cronet` 日志出现在视频流请求路径（E3 整改后日志关键词变更）
- `FR-4 favicon 内存/磁盘缓存命中` 日志出现
- `FR-7 证书错误记忆命中` 日志出现
- `FR-8 预解析缓存命中` 日志出现

---

## 十、参考文档

- 日志分析报告：`docs/issues/user/temp/20260731/002/extracted_8/log_analysis_report.md`
- 上一版本设计（sniff-result-pipeline-fix）：`docs/specs/sniff-result-pipeline-fix/`
- 项目代码规范：`docs/project-rules/naming_rules.md`、`docs/project-rules/checkstyle_rules.md`
- 输出安全规范：`.trae/rules/output-safety.md`
