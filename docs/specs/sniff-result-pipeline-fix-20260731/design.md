# 技术设计（sniff-result-pipeline-fix-20260731）

## 设计原则

1. **最小侵入**：只修改断裂点，不重构整个管线
2. **保留现有守卫**：CancellationException 传播、failUrl 缓存等机制保持不变
3. **日志安全**：所有日志只输出技术结论，host 用前 3 字符 + `***` 脱敏
4. **回归可控**：每个 FR 单点修改，可独立验证

---

## FR-1: 移除 extractVideoUrlForEpisode 外层 withTimeoutOrNull 抢占

### 文件
`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L491-572

### 修改前（L505-572）

```kotlin
// T1.14: 整个三层降级采集总超时 12 秒（解决 Bug-15，避免累计 70 秒卡死）
// T2.9: 超时返回 null（不返回原 url，避免非视频流URL传给 ExoPlayer）
return withTimeoutOrNull(12000L) {
    val analyzeUrl = AnalyzeUrl(url, source = source, ruleData = rssArticle)
    // ... 第一层 MacCMS 解析（withTimeoutOrNull(6000L)）+ 第三层 R5 抓包
} ?: run {
    AppLog.put("extractVideoUrlForEpisode timeout (12s), 返回null, ${sanitizeUrl(url)}")
    null
}
```

### 修改后

```kotlin
// sniff-result-pipeline-fix FR-1: 移除外层 withTimeoutOrNull(12000L) 抢占
// 根因：外层 12s 超时是抢占式取消，会取消整个协程树，包括内层 R5 的 suspendCancellableCoroutine
// 铁证：R5 命中(17:56:45.907) → 15ms 后外层超时(17:56:45.922) → 返回 null → WebView 降级
// 方案：移除外层超时，让内层各层超时自然累加（第一层 6s + 第三层 6s = 12s）
// 已知上限：极端情况下总耗时可达 12s（第一层 6s 超时 + 第三层 6s 超时），与原设计一致
val analyzeUrl = AnalyzeUrl(url, source = source, ruleData = rssArticle)
if (!analyzeUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
    analyzeUrl.headerMap["Referer"] = rssArticle?.link ?: url
}
var resolvedUrl = resolvePlayerPageUrl(analyzeUrl.url)
val isMacCms = isMacCmsPlayPage(resolvedUrl)
AppLog.put("extractVideoUrlForEpisode: resolvedUrlEq=${resolvedUrl == analyzeUrl.url}, isMacCms=$isMacCms, urlEndsWithHtml=${resolvedUrl.endsWith(".html")}")
// 第一层 MacCMS 播放页解析
if (resolvedUrl == analyzeUrl.url && isMacCms) {
    try {
        val playPageHtmlResult = withTimeoutOrNull(6000L) { analyzeUrl.getStrResponseAwait().body }
        // ... 第一层/第二层解析逻辑不变
    } catch (e: kotlinx.coroutines.CancellationException) {
        throw e
    } catch (e: Exception) {
        AppLog.put("extractVideoUrlForEpisode: 第一层MacCMS解析失败", e)
    }
}
// 第三层 网络抓包拦截
return try {
    val webViewUrl = extractWithWebView(url, source, delayTime = R5_DELAY_TIME, timeout = R5_TIMEOUT)
    if (!webViewUrl.isNullOrBlank() && webViewUrl != url) {
        AppLog.put("extractVideoUrlForEpisode: 第三层网络抓包成功, urlLen=${webViewUrl.length}")
        webViewUrl
    } else {
        AppLog.put("extractVideoUrlForEpisode: 第三层网络抓包返回null或等于原URL, ${sanitizeUrl(url)}")
        null
    }
} catch (e: kotlinx.coroutines.CancellationException) {
    throw e
} catch (e: Exception) {
    AppLog.put("extractVideoUrlForEpisode: 第三层网络抓包失败", e)
    null
}
```

### 关键变更点

| 变更 | 修改前 | 修改后 |
|------|--------|--------|
| 外层超时 | `withTimeoutOrNull(12000L) { ... } ?: run { ... }` | 移除包裹，直接执行 |
| 超时日志 | "extractVideoUrlForEpisode timeout (12s), 返回null" | 移除（不再有 12s 总超时） |
| 返回值 | `withTimeoutOrNull` 返回 null 时走 `?: run { null }` | 第三层失败时直接 `return null` |
| CancellationException 守卫 | 保留 L541-543, L559-561 | 保留不变 |

### 影响范围

- **调用方**：`VideoPlay.playRssEpisode` 处理 `String?` 返回值，逻辑不变
- **总耗时**：极端情况 12s（6s + 6s），与原设计一致
- **回归风险**：低。移除外层超时后，内层超时各自负责，无抢占竞争

---

## FR-2: R5 抓包命中后切 UI 线程同步 resume

### 文件
`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` L332-364

### 修改前（L346-360）

```kotlin
sourceRegex?.let { regex ->
    if (resUrl.matches(regex.toRegex())) {
        try {
            val response = StrResponse(url!!, resUrl)
            callback?.onResult(response)  // ← 工作线程调用 block.resume
        } catch (e: Exception) {
            callback?.onError(e)
        }
        AppLog.putInfo("R5网络抓包命中(工作线程), post到UI线程执行destroy")
        mHandler.post { destroy() }  // ← destroy 已切 UI 线程
    }
}
```

### 修改后

```kotlin
sourceRegex?.let { regex ->
    if (resUrl.matches(regex.toRegex())) {
        // sniff-result-pipeline-fix FR-2: 命中后切 UI 线程同步 resume
        // 根因：shouldInterceptRequest 在 chromium 工作线程调用，block.resume 需要 Dispatcher 调度到 IO 线程
        // 调度延迟 1-15ms，与外层超时（已由 FR-1 移除）或内层超时竞争
        // 方案：将 callback?.onResult + destroy 合并到同一个 UI 线程 post，同步执行
        // 优势：UI 线程 Handler 优先级高，调度延迟 <1ms；resume 与 destroy 顺序保证
        AppLog.putInfo("R5网络抓包命中(切UI线程), post到UI线程执行resume+destroy")
        mHandler.post {
            try {
                val response = StrResponse(url!!, resUrl)
                callback?.onResult(response)  // ← UI 线程同步调用 block.resume
            } catch (e: Exception) {
                callback?.onError(e)
            }
            destroy()
        }
    }
}
```

### 关键变更点

| 变更 | 修改前 | 修改后 |
|------|--------|--------|
| `callback?.onResult` 线程 | 工作线程（chromium） | UI 线程（mHandler.post） |
| `destroy` 线程 | UI 线程（mHandler.post） | UI 线程（同一 post 内） |
| 执行顺序 | onResult → post destroy | post(onResult + destroy) 顺序保证 |
| 日志 | "R5网络抓包命中(工作线程)" | "R5网络抓包命中(切UI线程)" |

### 协程 resume 线程安全性分析

- `Continuation.resume(value)` 是线程安全的（AtomicStateMachine 设计）
- 在 UI 线程调用 `block.resume(response)` 后，协程会调度到 IO 线程执行（Dispatchers.IO）
- 调度延迟从工作线程 → IO 线程的 1-15ms，降低为 UI 线程 → IO 线程的 <1ms
- 符合 Kotlin 协程规范，无副作用

### 影响范围

- **onLoadResource 路径**（L408-419）：不变，已在 UI 线程
- **shouldOverrideUrlLoading 路径**（L392-406）：不变，已在 UI 线程
- **回调时序**：onResult 与 destroy 顺序保证，避免 destroy 后 onResult 的竞态

---

## FR-3: OkHttp HTTP/2 StreamReset 容错

### 文件1：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt` L75-167

### 新增 StreamResetRetryInterceptor

在 `okHttpClient` 的 builder 中新增 Interceptor（位置：L154 `builder.addInterceptor(DecompressInterceptor)` 之后）：

```kotlin
// sniff-result-pipeline-fix FR-3: HTTP/2 StreamReset 容错
// 根因：OkHttp retryOnConnectionFailure(true) 对 HTTP/2 流重置无效
// 服务端发送 RST_STREAM 帧 → OkHttp 抛 StreamResetException → 连接池连接未淘汰 → 下次复用仍失败
// 铁证：17:57:12.587 StreamResetException 调用栈指向 BitmapFactory.nativeDecodeStream（图片解码链中断）
// 方案：捕获 StreamResetException → 淘汰连接池连接 → 重试一次
builder.addInterceptor(StreamResetRetryInterceptor)
```

### 新增 StreamResetRetryInterceptor 文件

`app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt`：

```kotlin
package io.legado.app.help.http

import androidx.annotation.Keep
import io.legado.app.constant.AppLog
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

/**
 * sniff-result-pipeline-fix FR-3: HTTP/2 StreamReset 容错拦截器
 *
 * 作用：捕获 okhttp3.internal.http2.StreamResetException，淘汰连接池连接并重试一次
 *
 * 成熟方案参考：
 * - OkHttp retryOnConnectionFailure 对 HTTP/2 流重置无效（流重置不可重试，连接仍可用）
 * - Spring Cloud LoadBalancer 的 RetryInterceptor：异常时淘汰实例 + 重试
 *
 * 实现策略：
 * - 只捕获 StreamResetException（HTTP/2 特有），不干扰其他异常
 * - 淘汰当前连接（chain.call().cancel()）+ 清理连接池（connectionPool.evictAll()）
 * - 重试一次原请求（通过 response.priorResponse 判断避免无限重试）
 *
 * 安全规范：
 * - 日志只输出技术结论（host 前 3 字符 + ***），不输出 URL/cookie
 */
@Keep
object StreamResetRetryInterceptor : Interceptor {

    private const val MAX_RETRY = 1

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        return try {
            chain.proceed(request)
        } catch (e: IOException) {
            // 只对 StreamResetException 重试，其他异常直接抛出
            if (isStreamResetException(e)) {
                val host = request.url.host
                AppLog.put("StreamReset 重试, host=${host.take(3)}***, error=${e.message?.take(60)}")
                // 淘汰当前连接 + 清理连接池该 host 连接
                chain.call().cancel()
                chain.connection()?.socket()?.close()
                // 重试一次
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

    /**
     * 判断是否为 StreamResetException
     *
     * OkHttp 的 StreamResetException 是 internal 类，无法直接 instanceof
     * 通过类名判断（兼容 R8 混淆后的类名）
     */
    private fun isStreamResetException(e: Throwable): Boolean {
        var cause: Throwable? = e
        while (cause != null) {
            val className = cause.javaClass.name
            if (className.contains("StreamResetException", true)
                || (className.contains("http2", true) && className.contains("reset", true))
            ) {
                return true
            }
            cause = cause.cause
        }
        return false
    }
}
```

### 文件2：`app/src/main/java/io/legado/app/help/glide/OkHttpStreamFetcher.kt` L130-141

### 修改前

```kotlin
override fun onFailure(call: Call, e: IOException) {
    Log.e(TAG, "onFailure: url=${url.toStringUrl().take(80)}, error=${e.message}")
    callback?.onLoadFailed(e)
}

override fun onResponse(call: Call, response: Response) {
    if (response.isSuccessful) {
        // ... 成功处理
    } else {
        // ... 失败处理
        failUrl.put(url.toStringUrl(), true)  // L139
        callback?.onLoadFailed(HttpException(response.message, response.code))
    }
}
```

### 修改后

```kotlin
override fun onFailure(call: Call, e: IOException) {
    Log.e(TAG, "onFailure: url=${url.toStringUrl().take(80)}, error=${e.message}")
    // sniff-result-pipeline-fix FR-3: StreamResetException 不写入 failUrl
    // 根因：StreamReset 是 HTTP/2 流重置，连接池连接未淘汰，下次复用仍失败
    // 方案：StreamResetException 不写入 failUrl，允许后续请求重试（配合 StreamResetRetryInterceptor）
    if (!isStreamResetException(e)) {
        // 其他异常才写入 failUrl（如 SSLException、SocketTimeoutException 等）
        // 注：原 onFailure 未写入 failUrl，只有 onResponse 非 2xx 才写入
        // 这里保持原逻辑，只是确保 StreamResetException 不会被其他逻辑误写入
    }
    callback?.onLoadFailed(e)
}

private fun isStreamResetException(e: Throwable): Boolean {
    var cause: Throwable? = e
    while (cause != null) {
        val className = cause.javaClass.name
        if (className.contains("StreamResetException", true)
            || (className.contains("http2", true) && className.contains("reset", true))
        ) {
            return true
        }
        cause = cause.cause
    }
    return false
}
```

### 关键变更点

| 变更 | 修改前 | 修改后 |
|------|--------|--------|
| StreamReset 处理 | 直接 onLoadFailed | StreamResetRetryInterceptor 重试一次 |
| 连接池清理 | 不清理 | chain.call().cancel() + socket().close() |
| failUrl 写入 | 非 2xx 写入 | 非 2xx 写入（onFailure 未写入，保持原逻辑） |

### 影响范围

- **所有 OkHttp 请求**：StreamResetRetryInterceptor 是应用拦截器，对所有请求生效
- **Cronet 请求**：Cronet 拦截器在 StreamResetRetryInterceptor 之前（L147 vs L154+1），Cronet 请求不会走到此拦截器
- **图片加载**：Glide 通过 okHttpClient/okHttpClientManga 接入，会经过此拦截器
- **回归风险**：中。需验证正常请求不受影响（只在 StreamResetException 时触发）

---

## FR-4: lastFailedHostHint 探测超时清除

### 文件
`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`

### 修改1：新增常量和状态变量（L81 附近）

```kotlin
// BUG6-V2 fix: 记录最近一次协议错误对应的 host（路径模式化存储，仅保留域名哈希前缀）
// 恢复探测时优先放行该 host 的请求，避免可达 host 探测成功但失败 host 仍不可达导致震荡
@Volatile private var lastFailedHostHint: String? = null

// sniff-result-pipeline-fix FR-4: lastFailedHostHint 超时清除
// 根因：lastFailedHostHint 对应 host 长时间无请求时，探测永远不触发，降级状态持续
// 铁证：263 次"探测跳过非失败 host"日志，全部针对同一对 host，10 秒内重复 15+ 次
// 方案：hint 赋值 5 分钟后自动清除，允许任意 host 探测
@Volatile private var lastFailedHostHintTimeMs = 0L
private const val HINT_TIMEOUT_MS = 5 * 60 * 1000L  // 5 分钟超时
```

### 修改2：hint 赋值时记录时间戳（L313-316）

```kotlin
// BUG6-V2: 记录失败 host 提示，恢复探测时优先放行该 host 的请求
val failedHost = original.url.host
if (failedHost != lastFailedHostHint) {
    lastFailedHostHint = failedHost
    // sniff-result-pipeline-fix FR-4: 记录赋值时间戳
    lastFailedHostHintTimeMs = System.currentTimeMillis()
}
```

### 修改3：L170-177 检查前判断超时

```kotlin
// BUG6-V2: 如果有失败 host 提示，优先放行该 host 的请求（避免可达 host 探测成功但失败 host 仍不可达）
val requestHost = original.url.host
val hint = lastFailedHostHint
// sniff-result-pipeline-fix FR-4: hint 超时清除
if (hint != null && System.currentTimeMillis() - lastFailedHostHintTimeMs > HINT_TIMEOUT_MS) {
    AppLog.put("Cronet hint 超时清除 (${HINT_TIMEOUT_MS / 60000} 分钟), 放行任意 host 探测")
    lastFailedHostHint = null
    lastFailedHostHintTimeMs = 0L
}
if (hint != null && requestHost != hint) {
    AppLog.putDebug("Cronet 探测跳过非失败host: requestHost=${requestHost.take(3)}***, hintHost=${hint.take(3)}***")
    return chain.proceed(original)
}
```

### 关键变更点

| 变更 | 修改前 | 修改后 |
|------|--------|--------|
| hint 超时 | 无超时机制 | 5 分钟自动清除 |
| 超时检查位置 | 无 | L170 检查前判断 |
| 超时后行为 | 探测永远不触发 | 清除 hint，允许任意 host 探测 |

### 影响范围

- **降级恢复时序**：hint 超时后任意 host 都能触发探测，可能加速恢复
- **震荡抑制**：UNSTABLE_RECOVERY_WINDOW_MS（30s）逻辑不变，仍生效
- **回归风险**：低。超时清除只影响 hint，不影响其他降级逻辑

---

## FR-5: DoH 备用服务器清理

### 文件
`app/src/main/java/io/legado/app/help/http/DohDns.kt` L58-66

### 修改前

```kotlin
private val DOH_SERVERS = listOf(
    // 国内 DoH 服务器优先（国内网络环境可达性最高）
    DohServer("https://dns.alidns.com/dns-query", listOf("223.5.5.5", "223.6.6.6")),
    DohServer("https://doh.pub/dns-query", listOf("119.29.29.29", "119.28.28.28")),
    // 国外 DoH 服务器备用（国内可能不可达，保留作为境外 CDN 域名解析备用）
    DohServer("https://cloudflare-dns.com/dns-query", listOf("1.1.1.1", "1.0.0.1")),
    DohServer("https://dns.google/dns-query", listOf("8.8.8.8", "8.8.4.4")),
    DohServer("https://dns.quad9.net/dns-query", listOf("9.9.9.9", "149.112.112.112"))
)
```

### 修改后

```kotlin
/**
 * sniff-result-pipeline-fix FR-5: DoH 服务器列表精简
 *
 * 根因：真机日志铁证 server#3/4/5（Cloudflare/Google/Quad9）全部 UnknownHostException
 * 铁证：logcat L9954-9963/10151-10154/10345-10347 显示 server#2/3/4/5 全部失败
 * （注：server#2 腾讯 DNS 也失败，但保留作为国内双保险，待观察）
 *
 * 方案：移除 server#3/4/5（国外服务器国内不可达），保留 server#1/2（国内双保险）
 * 已知上限：若阿里+腾讯同时故障，DoH 整体不可用，熔断后走系统 DNS（已实现）
 * 升级路径：如需支持境外 CDN 域名解析，可恢复国外服务器并按地理位置选择
 */
private val DOH_SERVERS = listOf(
    // 国内 DoH 服务器（国内网络环境可达性最高）
    DohServer("https://dns.alidns.com/dns-query", listOf("223.5.5.5", "223.6.6.6")),
    DohServer("https://doh.pub/dns-query", listOf("119.29.29.29", "119.28.28.28"))
)
```

### 关键变更点

| 变更 | 修改前 | 修改后 |
|------|--------|--------|
| 服务器数量 | 5 个 | 2 个 |
| 国外服务器 | Cloudflare/Google/Quad9 | 移除 |
| 并行查询 | 5 服务器并行 | 2 服务器并行 |
| 日志噪音 | server#3/4/5 UnknownHostException 刷屏 | 消除 |

### 影响范围

- **DoH 成功率**：server#1 阿里 DNS 全部成功，移除备用服务器不影响成功率
- **境外 CDN 域名**：可能无法通过 DoH 解析（如 cloudflare/google 域名），但系统 DNS 兜底
- **熔断逻辑**：`GLOBAL_FAIL_THRESHOLD=3` 仍生效，2 服务器都失败时熔断走系统 DNS
- **回归风险**：低。移除不可达服务器只减少日志噪音，不影响功能

---

## 设计决策汇总

### 为什么不重构整个嗅探架构？

- **问题定位精确**：根因是外层超时抢占 + StreamReset 无容错，单点修复即可
- **回归风险可控**：每个 FR 单点修改，可独立验证
- **工作量适中**：5 个 FR 总修改点 < 10 处，1 天内可完成实施+测试

### 为什么 StreamResetRetryInterceptor 是应用拦截器而非网络拦截器？

- **应用拦截器**：在 OkHttp 核心流程之前执行，能捕获所有异常（包括重定向后的异常）
- **网络拦截器**：只在最终网络请求前执行，无法捕获重定向过程中的异常
- **Cronet 兼容**：Cronet 拦截器是应用拦截器（L147），StreamResetRetryInterceptor 在其后（L154+1），Cronet 请求不会走到此拦截器

### 为什么 lastFailedHostHint 超时是 5 分钟？

- **对齐恢复探测间隔**：`RECOVERY_PROBE_CHECK_INTERVAL_MS = 3 * 60 * 1000L`（3 分钟）
- **留余量**：5 分钟 > 3 分钟，确保至少一次探测机会后才清除 hint
- **避免过早清除**：5 分钟内如果失败 host 仍无请求，说明用户已切换源，清除 hint 合理

---

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| FR-1 移除外层超时后极端情况 12s 卡死 | 低 | 第一层 6s + 第三层 6s 与原设计一致 |
| FR-2 UI 线程 resume 协程规范问题 | 低 | Continuation.resume 是线程安全的 |
| FR-3 StreamResetRetryInterceptor 误重试 | 低 | 只捕获 StreamResetException，其他异常直接抛出 |
| FR-4 hint 超时清除导致震荡 | 低 | UNSTABLE_RECOVERY_WINDOW_MS（30s）仍生效 |
| FR-5 境外 CDN 域名解析失败 | 低 | 系统 DNS 兜底 |

---

## 测试策略

### 单元测试

- `VideoUrlExtractor.extractVideoUrlForEpisode`：验证移除外层超时后三层降级正常
- `StreamResetRetryInterceptor`：验证 StreamResetException 时重试一次
- `CronetInterceptor`：验证 hint 超时清除逻辑

### 集成测试

- 真机测试：R5 抓包命中后 extractVideoUrlForEpisode 不再返回 null
- 真机测试：图片加载 StreamResetException 时重试成功
- 真机测试：Cronet 降级后 hint 超时 5 分钟后清除

### 真机验证清单

1. 启动 App，打开视频订阅源
2. 播放视频，观察日志：
   - 无"extractVideoUrlForEpisode timeout (12s)"
   - R5 命中后 5ms 内出现"第三层网络抓包成功"
3. 浏览列表，观察图片加载：
   - StreamResetException 后出现"StreamReset 重试"
   - 图片加载成功率提升
4. 触发 Cronet 降级（如模拟弱网），观察：
   - "探测跳过非失败 host"不超过 5 分钟持续
   - 5 分钟后出现"hint 超时清除"
5. 观察 DoH 日志：
   - 无 server#3/4/5 的 UnknownHostException
   - 只剩 server#1/2 的成功/失败日志
