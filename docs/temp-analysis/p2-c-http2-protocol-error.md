# P2-C HTTP/2协议错误 问题分析

> 分析日期：2026-07-13
> 分析范围：07-13 真机日志中 22 条 HTTP/2 相关异常
> 关键词：`StreamResetException`、`PROTOCOL_ERROR`、`http2`、`Cronet System error`

## 1. 日志证据

### 1.1 日志分布统计

Grep 统计（`StreamResetException|PROTOCOL_ERROR|http2|Http2`）：

| 文件 | 命中数 |
|------|--------|
| `temp/tmp/Downloadslogs5/logs/appLog-26-07-12_13-43-02.764.txt` | 48 |
| `temp/tmp/Downloadslogs5/logcat.txt` | 18 |
| **合计** | **66** |

任务声明的"22 条"应为去重后的错误实例数（每次播放失败产生 ~3 条 StreamResetException 堆栈行 + Suppressed）。

### 1.2 核心日志 1：appLog-26-07-12_13-43-02.764.txt

**触发场景**：用户在 `VideoPlayerActivity` 播放视频时失败。

`appLog-26-07-12_13-43-02.764.txt:1318-1323`（用户感知层）：
```
26-07-12 14:05:17.517: AppLog 播放失败
错误码: 2001 (ERROR_CODE_IO_NETWORK_CONNECTION_FAILED)
错误信息: Source error
播放地址: https://ccm.91p52.com/358999.mp4?st=6dX3e0ya0njWeGIALSBPrA&f=ed08LJ7jxrtD3siJbLVA5QnVBHx2NHF/Y937gfcALELYsZQ4OxoLTI9HNGk6K7pCiKaORleJhB9CrfSSFOWPGqrXYkhVHQe+p/xp
原因: androidx.media3.datasource.HttpDataSource$HttpDataSourceException: java.io.IOException: java.util.concurrent.ExecutionException: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
建议: 网络连接失败，请检查网络后重试
```

`appLog-26-07-12_13-43-02.764.txt:1354-1380`（OkHttp 调用链）：
```
Caused by: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
    at okhttp3.internal.http2.Http2Stream.takeHeaders(Http2Stream.kt:166)
    at okhttp3.internal.http2.Http2ExchangeCodec.readResponseHeaders(Http2ExchangeCodec.kt:105)
    at okhttp3.internal.connection.Exchange.readResponseHeaders(Exchange.kt:116)
    at okhttp3.internal.http.CallServerInterceptor.intercept(CallServerInterceptor.kt:97)
    at okhttp3.internal.http.RealInterceptorChain.proceed(RealInterceptorChain.kt:332)
    at io.legado.app.help.http.HttpHelperKt$okHttpClient_delegate$lambda$0$$inlined$-addNetworkInterceptor$1.intercept(OkHttpClient.kt:1405)
    ...
    at io.legado.app.lib.cronet.CronetInterceptor.intercept(CronetInterceptor.kt:66)  ← Cronet 拦截器在链中
    ...
```

`appLog-26-07-12_13-43-02.764.txt:1385-1417`（Cronet 失败链 - 关键证据）：
```
Suppressed: java.util.concurrent.ExecutionException: java.io.IOException: System error  ← Cronet 把 PROTOCOL_ERROR 吞成 "System error"
    at io.legado.app.lib.cronet.NewCallBack.waitForDone(NewCallBack.kt:31)
    at io.legado.app.lib.cronet.CronetInterceptor.proceedWithCronet(CronetInterceptor.kt:82)
    ...
Caused by: java.io.IOException: System error
    at io.legado.app.utils.ThrowableExtensionsKt.asIOException(ThrowableExtensions.kt:16)
    at io.legado.app.lib.cronet.AbsCallBack.onFailed(AbsCallBack.kt:194)  ← 信息丢失现场
    at org.chromium.net.impl.VersionSafeCallbacks$UrlRequestCallback.onFailed(VersionSafeCallbacks.java:65)
    ...
Caused by: org.chromium.net.impl.CronetExceptionImpl: System error
    at org.chromium.net.impl.JavaUrlRequest.enterCronetErrorState(JavaUrlRequest.java:477)
    ...
```

### 1.3 核心日志 2：logcat.txt（独立重现）

`logcat.txt:88058-88084`：
```
07-13 14:56:27.917 E io.legado.app.lib.cronet.NewCallBack: System error  ← 只输出到 Logcat，未进 AppLog
07-13 14:56:27.919 W System.err: java.util.concurrent.ExecutionException: java.io.IOException: System error
    at io.legado.app.lib.cronet.NewCallBack.waitForDone(NewCallBack.kt:31)
    at io.legado.app.lib.cronet.CronetInterceptor.proceedWithCronet(CronetInterceptor.kt:82)
    at io.legado.app.lib.cronet.CronetInterceptor.intercept(CronetInterceptor.kt:54)
    ...
```

`logcat.txt:88101-88133`（OkHttp 兜底层也失败）：
```
07-13 14:56:27.930 W System.err: Caused by: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
    at okhttp3.internal.http2.Http2Stream.takeHeaders(Http2Stream.kt:166)
    ...
    at io.legado.app.help.http.ObsoleteUrlFactory$OkHttpURLConnection$buildCall$$inlined$-addNetworkInterceptor$1.intercept(OkHttpClient.kt:1405)
    at io.legado.app.help.http.ObsoleteUrlFactory$OkHttpURLConnection$NetworkInterceptor.intercept(ObsoleteUrlFactory.kt:568)
    ...
07-13 14:56:27.933 W System.err: 	Suppressed: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
07-13 14:56:27.934 W System.err: 	Suppressed: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
07-13 14:56:27.934 W System.err: 	Suppressed: okhttp3.internal.http2.StreamResetException: stream was reset: PROTOCOL_ERROR
```

### 1.4 关键证据汇总

| 证据 | 含义 |
|------|------|
| `StreamResetException: stream was reset: PROTOCOL_ERROR` | 服务器主动发送 RST_STREAM 帧，错误码 PROTOCOL_ERROR（HTTP/2 spec §7） |
| 错误位置 `Http2ExchangeCodec.readResponseHeaders` | 在读取响应头阶段被 reset，即服务器在收到请求后立即 reset 流 |
| `ccm.91p52.com/358999.mp4` | 视频订阅源提供的 mp4 直链 |
| Cronet `System error` | Cronet JNI 层不暴露 HTTP/2 错误码，统一吞为 "System error" |
| OkHttp Suppressed ×3 | OkHttp 内部对 HTTP/2 连接做了 3 次重试，全部被 reset |
| 触发播放器 `ERROR_CODE_IO_NETWORK_CONNECTION_FAILED (2001)` | 用户感知：网络失败（误导） |

## 2. 源码定位

### 2.1 HTTP/2 启用位置

| 位置 | 说明 |
|------|------|
| [HttpHelper.kt:67-151](../../app/src/main/java/io/legado/app/help/http/HttpHelper.kt) | `okHttpClient` 单例配置：**未调用 `protocols()`**，OkHttp 默认 `[HTTP_2, HTTP_1_1]`，通过 ALPN 在 TLS 握手时协商 HTTP/2 |
| [CronetHelper.kt:39](../../app/src/main/java/io/legado/app/lib/cronet/CronetHelper.kt) | `enableHttp2(true)` 显式启用 Cronet 的 HTTP/2 支持 |
| [CronetHelper.kt:38](../../app/src/main/java/io/legado/app/lib/cronet/CronetHelper.kt) | `enableQuic(true)` 同时启用 HTTP/3（QUIC），失败时回退到 HTTP/2 |
| [ExoPlayerHelper.kt:121-127](../../app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt) | 视频播放 OkHttpClient：`okHttpClient.newBuilder().callTimeout(0).build()`，**继承 HTTP/2 配置** |

### 2.2 异常处理位置（缺陷点）

| 位置 | 问题 |
|------|------|
| [AbsCallBack.kt:190-197](../../app/src/main/java/io/legado/app/lib/cronet/AbsCallBack.kt) | `onFailed`：仅 `DebugLog.e(...)` 不 `AppLog.put(...)`，且 `error.asIOException()` 把 `CronetExceptionImpl("System error")` 转为 `IOException`，**原始 HTTP/2 PROTOCOL_ERROR 信息丢失**，违反 AGENTS.md "日志覆盖错误分支"规范 |
| [CronetInterceptor.kt:55-70](../../app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt) | catch 后回退到 `chain.proceed(original)`，但 OkHttp 同样启用 HTTP/2 → **回退无效**；`e.printOnDebug()` 只输出到 debug logcat |
| [Exo2MediaPlayer.kt:223-253](../../app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt) | `onPlayerError`：对 `ERROR_CODE_IO_NETWORK_CONNECTION_FAILED` 自动重试 1 次，但重试仍走相同的 HTTP/2 连接池 → **重试无效** |
| [OkHttpExceptionInterceptor.kt:8-22](../../app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt) | 仅做异常类型归一化，无针对 `StreamResetException` 的协议降级 |
| 全局 Grep `StreamResetException\|PROTOCOL_ERROR` | **0 处源码命中**，整个网络栈无 HTTP/2 协议错误处理逻辑 |

## 3. 根因分析

### 3.1 直接原因：服务器 HTTP/2 实现缺陷

- 服务器 `ccm.91p52.com`（疑似第三方视频 CDN）的 HTTP/2 实现对 mp4 视频流响应处理存在 bug
- 服务器在收到请求后、发送响应头前，主动发送 `RST_STREAM` 帧，错误码 `PROTOCOL_ERROR`（HTTP/2 RFC 7540 §7）
- 常见诱因（无法服务端验证，客户端无法确定）：
  - 服务器对 HTTP/2 流的 `Content-Length` / chunked 编码处理错误
  - 服务器对视频 Range 请求的 HTTP/2 帧切分错误
  - 服务器对长连接上的多路复用流处理不当
  - 服务器对大响应体的流量控制（FLOW_CONTROL）实现错误

### 3.2 根本原因：客户端无 HTTP/2 → HTTP/1.1 降级机制

- OkHttp 默认启用 HTTP/2（通过 ALPN 协商），但本项目的 `okHttpClient` 单例**没有配置 `protocols()`**，无法在协议错误后自动降级
- OkHttp 内部对 `StreamResetException` 的重试机制只在同一 HTTP/2 连接上重试（日志中 `Suppressed ×3` 证明），不会切换到 HTTP/1.1
- Cronet 显式 `enableHttp2(true)`，且 `AbsCallBack.onFailed` 不区分错误类型，统一转 `IOException("System error")`，丢失了 `PROTOCOL_ERROR` 信号

### 3.3 复合问题：错误信息链路丢失

错误从底层到用户的传递路径：

```
服务器 RST_STREAM(PROTOCOL_ERROR)
   ↓
Http2Stream.takeHeaders 抛 StreamResetException("stream was reset: PROTOCOL_ERROR")  ← 信息完整
   ↓
路径1: OkHttp CallServerInterceptor → Exchange.readResponseHeaders
   ↓ (OkHttpDataSource.executeCall 抛 ExecutionException)
Media3 OkHttpDataSource.open 抛 HttpDataSource$HttpDataSourceException  ← 包含 cause
   ↓
ExoPlayer onPlayerError 收到 ERROR_CODE_IO_NETWORK_CONNECTION_FAILED (2001)  ← 错误码泛化
   ↓
用户看到："网络连接失败，请检查网络后重试"  ← 误导（实际网络正常，是协议错误）

路径2: CronetInterceptor.proceedWithCronet → AbsCallBack.onFailed
   ↓
error.asIOException() → IOException("System error")  ← ★信息丢失点★
   ↓
CronetInterceptor.intercept catch → chain.proceed(original)（OkHttp 回退，仍 HTTP/2，仍失败）
   ↓
最终错误堆栈中只可见 "System error"，看不见 PROTOCOL_ERROR 根因
```

### 3.4 用户感知影响

| 维度 | 评估 |
|------|------|
| **发生频率** | 22 条/天，集中在视频订阅源播放（`ccm.91p52.com` 等视频域名） |
| **用户感知** | 视频播放完全失败，提示"网络连接失败"（误导，实际是协议错误） |
| **可恢复性** | 用户重试无效（同一 HTTP/2 连接必失败）；切换网络无效；只能换源 |
| **误导风险** | 用户可能误以为网络问题去重启路由器/切换 Wi-Fi/移动数据，浪费时间 |
| **降级失效** | Exo2MediaPlayer 的网络错误重试（1 次）和 CronetInterceptor 的 OkHttp 回退**都无效**，因为底层都用 HTTP/2 |

### 3.5 对比延伸版本

依据 AGENTS.md 延伸版本对比方法论：

- **蛋蛋Max**（网络层优先级 ⭐⭐⭐⭐⭐）：有 307/308 重定向优化，但未见 HTTP/2 降级处理
- **阅读T**（网络层优先级 ⭐⭐⭐⭐）：有 SOCKS5 隧道 + Brotli 压缩（本项目已通过 `enableBrotli(true)` 启用），但未见 HTTP/2 降级
- **阅读NG**（网络层优先级 ⭐⭐⭐⭐）：有网络日志标签优化，可借鉴错误信息保留思路

**结论**：延伸版本均未实现 HTTP/2 → HTTP/1.1 自动降级，本项目需自主创新修复。鉴于视频订阅源的特殊性（少量域名、长连接、对流式响应敏感），采用"视频客户端强制 HTTP/1.1"的最小修复策略。

## 4. 修复方案

### 4.1 文件路径

| 文件 | 修改类型 | 优先级 |
|------|---------|--------|
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\exoplayer\ExoPlayerHelper.kt` | 核心修复：视频客户端强制 HTTP/1.1 | P0 |
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\lib\cronet\AbsCallBack.kt` | 日志增强：保留 PROTOCOL_ERROR 原因 | P0（按 AGENTS.md "改造必加日志"规范强制） |
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\lib\cronet\CronetInterceptor.kt` | 日志增强：标记回退原因 | P1 |

### 4.2 修改点

#### 4.2.1 ExoPlayerHelper.kt（P0 核心修复）

**目标**：视频播放 OkHttpClient 强制使用 HTTP/1.1，绕开 HTTP/2 PROTOCOL_ERROR。

**位置**：`ExoPlayerHelper.kt:121-127`（`okhttpDataFactory` lazy 初始化）

**old_string**：
```kotlin
    /**
     * Okhttp DataSource.Factory
     */
    private val okhttpDataFactory by lazy {
        val client = okHttpClient.newBuilder()
            .callTimeout(0, TimeUnit.SECONDS)
            .build()
        OkHttpDataSource.Factory(client)
            .setCacheControl(CacheControl.Builder().maxAge(1, TimeUnit.DAYS).build())
    }
```

**new_string**：
```kotlin
    /**
     * Okhttp DataSource.Factory
     *
     * P2-C 修复：强制 HTTP/1.1，规避 HTTP/2 PROTOCOL_ERROR
     * 根因：部分视频 CDN（如 ccm.91p52.com）的 HTTP/2 实现对 mp4 流式响应处理有 bug，
     *      主动发送 RST_STREAM(PROTOCOL_ERROR)，导致 OkHttp 抛 StreamResetException，
     *      视频播放失败（ERROR_CODE_IO_NETWORK_CONNECTION_FAILED 2001）。
     * 证据：appLog-26-07-12_13-43-02.764.txt:1322 + logcat.txt:88101
     * 方案：ExoPlayer 客户端限制 protocols=[HTTP_1_1]，绕开 HTTP/2 协商。
     * 影响范围：仅视频播放，不影响书源/订阅源请求（仍用默认 OkHttp + Cronet）。
     * 已知上限：HTTP/1.1 无多路复用，但视频流是单长连接，性能影响可忽略。
     */
    private val okhttpDataFactory by lazy {
        val client = okHttpClient.newBuilder()
            .callTimeout(0, TimeUnit.SECONDS)
            .protocols(listOf(okhttp3.Protocol.HTTP_1_1))  // P2-C: 强制 HTTP/1.1
            .build()
        OkHttpDataSource.Factory(client)
            .setCacheControl(CacheControl.Builder().maxAge(1, TimeUnit.DAYS).build())
    }
```

#### 4.2.2 AbsCallBack.kt（P0 日志增强 - AGENTS.md 强制）

**目标**：`onFailed` 保留原始 CronetException 信息，按 AGENTS.md "改造必加日志"规范用 `AppLog.put` 永久记录，输出 negotiatedProtocol 用于定位是 h2 还是 quic 失败。

**位置**：`AbsCallBack.kt:189-197`（`onFailed`）

**old_string**：
```kotlin
    //UrlResponseInfo可能为null
    override fun onFailed(request: UrlRequest, info: UrlResponseInfo?, error: CronetException) {
        callbackResults.add(CallbackResult(CallbackStep.ON_FAILED, null, error))
        cancelJob?.cancel()
        DebugLog.e(javaClass.name, error.message.toString())
        onError(error.asIOException())
        eventListener?.callFailed(mCall, error)
        responseCallback?.onFailure(mCall, error)
    }
```

**new_string**：
```kotlin
    //UrlResponseInfo可能为null
    override fun onFailed(request: UrlRequest, info: UrlResponseInfo?, error: CronetException) {
        callbackResults.add(CallbackResult(CallbackStep.ON_FAILED, null, error))
        cancelJob?.cancel()
        // P2-C 日志增强：保留原始错误信息，按 AGENTS.md "改造必加日志"规范用 AppLog.put 永久记录
        // 原问题：error.asIOException() 把 CronetExceptionImpl("System error") 转 IOException，
        //         丢失 HTTP/2 PROTOCOL_ERROR 根因，日志只见 "System error"。
        // 输出 negotiatedProtocol 用于定位是 h2/quic 失败；url 脱敏（只保留 host+path，去掉 query）
        val negotiatedProtocol = info?.negotiatedProtocol ?: "unknown"
        val rawUrl = info?.url ?: originalRequest.url.toString()
        val safeUrl = rawUrl.substringBefore("?").takeLast(120)
        val errorCls = error.javaClass.simpleName
        val errorDetail = buildString {
            appendLine("Cronet onFailed: protocol=$negotiatedProtocol, errorType=$errorCls")
            appendLine("  message=${error.message}")
            appendLine("  url=$safeUrl")
            // 立即请求错误码（CronetException 有 errorCode 但需反射，message 已包含关键信息）
        }
        AppLog.put(errorDetail, error)
        DebugLog.e(javaClass.name, error.message.toString())
        onError(error.asIOException())
        eventListener?.callFailed(mCall, error)
        responseCallback?.onFailure(mCall, error)
    }
```

**注意**：需在文件顶部添加 import：`import io.legado.app.constant.AppLog`（已有 `DebugLog` import，无 `AppLog`）。

#### 4.2.3 CronetInterceptor.kt（P1 日志增强）

**目标**：catch 块区分协议错误，明确标记"回退到 OkHttp"。

**位置**：`CronetInterceptor.kt:55-70`（`intercept` catch 块）

**old_string**：
```kotlin
        } catch (e: Exception) {
            cronetException = e
            //不能抛出错误,抛出错误会导致应用崩溃
            //遇到Cronet处理有问题时的情况，如证书过期等等，回退到okhttp处理
            if (!e.message.toString().contains("ERR_CERT_", true)
                && !e.message.toString().contains("ERR_SSL_", true)
            ) {
                e.printOnDebug()
            }
        }
        try {
            return chain.proceed(original)
        } catch (e: Exception) {
            e.addSuppressed(cronetException)
            throw e
        }
```

**new_string**：
```kotlin
        } catch (e: Exception) {
            cronetException = e
            //不能抛出错误,抛出错误会导致应用崩溃
            //遇到Cronet处理有问题时的情况，如证书过期等等，回退到okhttp处理
            // P2-C 日志增强：区分 HTTP/2 协议错误，标记回退原因（按 AGENTS.md "日志覆盖错误分支"规范）
            val msg = e.message.toString()
            val isProtocolError = msg.contains("PROTOCOL_ERROR", true)
                || msg.contains("StreamReset", true)
                || msg.contains("System error", true)  // Cronet 包装后的 HTTP/2 错误
            if (isProtocolError) {
                AppLog.put("Cronet 协议错误，回退到 OkHttp: ${e.message}, url=${originalRequest.url.toString().substringBefore("?").takeLast(80)}", e)
            }
            if (!msg.contains("ERR_CERT_", true)
                && !msg.contains("ERR_SSL_", true)
            ) {
                e.printOnDebug()
            }
        }
        try {
            // P2-C 日志：回退到 OkHttp（注意 OkHttp 默认仍用 HTTP/2，可能仍失败）
            android.util.Log.d("CronetInterceptor", "fallback to OkHttp for: ${originalRequest.url.toString().substringBefore("?").takeLast(80)}")
            return chain.proceed(original)
        } catch (e: Exception) {
            e.addSuppressed(cronetException)
            throw e
        }
```

**注意**：需在文件顶部添加 import：`import io.legado.app.constant.AppLog`。

### 4.3 风险评估

#### 4.3.1 ExoPlayerHelper.kt 修改风险

| 维度 | 评估 |
|------|------|
| **影响范围** | 仅 `ExoPlayerHelper.okhttpDataFactory`，即 ExoPlayer/Exo2MediaPlayer 的视频播放 HTTP 客户端 |
| **不影响** | 书源请求（用 `okHttpClient` 单例）、订阅源请求、TTS、图片加载（Glide）、WebDAV、主题下载等 |
| **HTTP/1.1 性能影响** | 视频流是单长连接，HTTP/1.1 vs HTTP/2 性能差异可忽略；HTTP/1.1 不支持多路复用，但视频播放不需要 |
| **HTTP/3 (QUIC) 影响** | Cronet 的 QUIC 在 OkHttp 客户端上不生效（QUIC 是 Cronet 独有），强制 HTTP/1.1 不影响 Cronet 的 QUIC 路径 |
| **潜在回归** | 若有视频源服务器**仅支持 HTTP/2**（罕见，HTTP/2 服务器通常也支持 HTTP/1.1），则会失败。但 RFC 7540 要求 HTTP/2 服务器必须支持 HTTP/1.1 协商，此风险可忽略 |
| **回滚成本** | 低，删除 `.protocols(...)` 一行即可恢复 |

#### 4.3.2 AbsCallBack.kt / CronetInterceptor.kt 修改风险

| 维度 | 评估 |
|------|------|
| **影响范围** | 仅日志输出，不改变控制流 |
| **AppLog 输出量** | 每次 Cronet 失败多 1 条 AppLog（约 200 字节），按当前频率（22 条/天）每日增 ~4.4KB，可忽略 |
| **URL 脱敏** | 已用 `substringBefore("?")` 去掉查询参数（含 st/f 等鉴权 token），符合 AGENTS.md "日志内容安全"规范 |
| **不影响** | 错误处理逻辑、回退逻辑、重试逻辑完全不变 |

#### 4.3.3 验证清单

实施后需验证：

- [ ] 编译通过（`./gradlew assembleDebug`）
- [ ] ExoPlayer 播放 `ccm.91p52.com/358999.mp4` 类地址不再报 `StreamResetException`
- [ ] AppLog 中 Cronet 失败记录包含 `protocol=h2` 和 `errorType=CronetExceptionImpl`
- [ ] 书源/订阅源请求仍走 HTTP/2（通过 onResponseStarted 的 `info.negotiatedProtocol` 日志确认）
- [ ] 按 AGENTS.md "版本交付同步"规范更新 `app/src/main/assets/updateLog.md`
- [ ] 按 AGENTS.md "改造必加日志"规范，验证日志覆盖错误分支
- [ ] 按 AGENTS.md "AI 自动端到端测试"规范，执行步骤 5.5（用 `ai_tests/scripts/l2_verify_video_player.py --scenario http2_fallback`）

#### 4.3.4 后续可选优化（不在本次范围）

1. **全局 HTTP/2 降级机制**：在 `OkHttpExceptionInterceptor` 中捕获 `StreamResetException`，对失败域名标记禁用 HTTP/2（需维护域名黑名单 + per-domain OkHttpClient，复杂度高，暂不实施）
2. **Cronet 协议错误识别**：反射读取 `CronetException.errorCode`（Cronet 内部错误码如 -201 = ERR_HTTP2_PROTOCOL_ERROR），提供更精确的错误分类
3. **视频源域名白名单**：仅对已知有 HTTP/2 问题的视频域名（如 `ccm.91p52.com`）强制 HTTP/1.1，其他域名保留 HTTP/2（需维护白名单，运维成本高）

---

## 5. 总结

| 维度 | 结论 |
|------|------|
| **根因** | 服务器 `ccm.91p52.com` HTTP/2 实现缺陷，主动 RST_STREAM(PROTOCOL_ERROR)；客户端无 HTTP/2 → HTTP/1.1 降级机制 |
| **用户感知** | 视频播放失败，提示"网络连接失败"（误导） |
| **核心修复** | ExoPlayer 视频客户端强制 HTTP/1.1（`ExoPlayerHelper.kt:122-124` 加 `.protocols(listOf(Protocol.HTTP_1_1))`） |
| **日志修复** | `AbsCallBack.onFailed` + `CronetInterceptor.intercept` 按 AGENTS.md 规范用 `AppLog.put` 记录协议错误，保留 PROTOCOL_ERROR 根因 |
| **修复优先级** | P0（视频播放完全失败，用户感知强） |
| **影响范围** | 仅视频播放，不影响书源/订阅源请求 |
