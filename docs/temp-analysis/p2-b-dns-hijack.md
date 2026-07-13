# P2-B DNS劫持/UnknownHost 问题分析

> 分析日期：2026-07-13
> 数据来源：`temp/tmp/Downloadslogs5/`（logcat.txt 329条 + 4个appLog共14条）
> 源码版本：当前工作树

## 1. 日志证据

### 1.1 错误总数与分布

| 失败域名 | logcat.txt 匹配行数 | 失败类型 | 影响范围 |
|---------|-------------------|---------|---------|
| `fengmian.fhfhtutu.com` | 252 | 书源封面图片域名 | Glide 图片加载失败 |
| `img.siwazywimg2.com` | 96 | 书源图片资源域名 | Glide 图片加载失败 |
| `guce.mossjav.com` | appLog 中出现 | RSS 源域名 | RSS 内容获取失败 |
| **合计 "Unable to resolve host"** | **287 行** | — | — |

注：任务描述 329 条为 logcat.txt 全量统计（含重复堆栈帧），实际独立错误事件约 287 行。

### 1.2 错误类型分组与代表性样本

#### 类型 A：书源封面图片 DNS 失败（fengmian.fhfhtutu.com，252 行）

```
logcat.txt:13440  07-13 14:54:53.509 W System.err: Caused by: java.net.UnknownHostException: Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
logcat.txt:13477  07-13 14:54:53.511 E ImgDecrypt: onFailure: url=https://fengmian.fhfhtutu.com/upload/vod/2020/07/lyolkvebqwi.jpg, error=Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
logcat.txt:13481  07-13 14:54:53.522 W Glide: java.net.UnknownHostException(Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname)
logcat.txt:13568  07-13 14:54:53.738 W System.err: Caused by: java.net.UnknownHostException: Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
logcat.txt:21710  07-13 14:54:54.754 W System.err: Caused by: java.net.UnknownHostException: Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
logcat.txt:21813  07-13 14:54:54.755 E ImgDecrypt: onFailure: url=https://fengmian.fhfhtutu.com/upload/vod/2020/07/lyolkvebqwi.jpg, error=Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
logcat.txt:22003  07-13 14:54:54.807 W System.err: Caused by: java.net.UnknownHostException: Unable to resolve host "fengmian.fhfhtutu.com": No address associated with hostname
```

特征：同一域名在 1 秒内被反复解析（14:54:53~14:54:54），每次图片加载都触发独立 DNS 查询，无缓存无重试。

#### 类型 B：书源图片资源 DNS 失败（img.siwazywimg2.com，96 行）

```
logcat.txt:21907  07-13 14:54:54.790 W System.err: Caused by: java.net.UnknownHostException: Unable to resolve host "img.siwazywimg2.com": No address associated with hostname
logcat.txt:21948  07-13 14:54:54.802 W Glide: java.net.UnknownHostException(Unable to resolve host "img.siwazywimg2.com": No address associated with hostname)
logcat.txt:21952  07-13 14:54:54.802 W Glide: java.net.UnknownHostException(Unable to resolve host "img.siwazywimg2.com": No address associated with hostname)
logcat.txt:21956  07-13 14:54:54.802 W Glide: java.net.UnknownHostException(Unable to resolve host "img.siwazywimg2.com": No address associated with hostname)
logcat.txt:21958  07-13 14:54:54.802 W Glide: Cause (1 of 1): class java.net.UnknownHostException: Unable to resolve host "img.siwazywimg2.com": No address associated with hostname
```

#### 类型 C：RSS 源 DNS 失败（guce.mossjav.com，appLog）

```
logs/appLog-26-07-12_23-11-23.884.txt:428  26-07-12 23:13:31.450: AppLog rss获取内容失败
logs/appLog-26-07-12_23-11-23.884.txt:429  java.net.UnknownHostException: Unable to resolve host "guce.mossjav.com": No address associated with hostname
logs/appLog-26-07-12_23-11-23.884.txt:439  Caused by: java.net.UnknownHostException: Unable to resolve host "guce.mossjav.com": No address associated with hostname
logs/appLog-26-07-12_23-11-23.884.txt:506  Caused by: java.net.UnknownHostException: Unable to resolve host "guce.mossjav.com": No address associated with hostname
```

调用链：`Rss.getArticlesAwait` → `AnalyzeUrl.getStrResponseAwait` → `AnalyzeUrl.executeStrRequest` → `OkHttpUtils.newCallStrResponse` → `Dns.SYSTEM.lookup` 失败。

#### 类型 D：正常域名（对照组，未失败）

```
logcat.txt:13389  D CronetCookie: AnalyzeUrl.setCookie: domain=91cangku2119822.buzz  ← 主源正常
logs/appLog-26-07-12_14-46-07.609.txt:670  AppLog 91香蕉国产调试输出: 视频地址: https://video.sjpcdnsjp.top/...  ← 视频域名正常
```

主源 `91cangku2119822.buzz` 和视频域名 `video.sjpcdnsjp.top` 解析正常，**排除模拟器全局 DNS 故障**。

### 1.3 关键观察

- **无重试日志**：搜索 `network retry` 在 logcat.txt 中 0 匹配，证明 DNS 失败从未触发重试机制。
- **无降级日志**：图片加载失败后 Glide 直接放弃，无 DoH/备用 DNS 尝试。
- **错误被部分吞掉**：`OkhttpUncaughtExceptionHandler` 只记录 `localizedMessage`，丢失主机名上下文。

## 2. 源码定位

### 2.1 OkHttp DNS 配置位置

[`app/src/main/java/io/legado/app/help/http/HttpHelper.kt:122-127`](../../app/src/main/java/io/legado/app/help/http/HttpHelper.kt)

```kotlin
if (AppConfig.addressCache.isNotEmpty()) {
    builder.dns { hostname ->
        val cachedAddress = AppConfig.addressCache[hostname]
        cachedAddress ?: Dns.SYSTEM.lookup(hostname)
    }
}
```

问题：
1. **条件加载**：仅当用户手动配置了 `customHosts`（addressCache 非空）才启用自定义 DNS，否则用默认 `Dns.SYSTEM`。
2. **无重试**：`Dns.SYSTEM.lookup` 失败直接抛出，无任何重试。
3. **无 DoH**：不支持 DNS over HTTPS，无法绕过运营商 DNS 污染/劫持。
4. **无失败日志**：DNS 查询失败时不记录主机名，难以排查。
5. **无负缓存**：同一域名短时间内被反复解析（252 次），浪费资源。

### 2.2 异常处理位置

#### 2.2.1 OkHttpExceptionInterceptor（拦截器层）

[`app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt:11-21`](../../app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt)

```kotlin
override fun intercept(chain: Interceptor.Chain): Response {
    try {
        return chain.proceed(chain.request())
    } catch (e: IOException) {
        throw e  // UnknownHostException 直接抛出，无日志无特殊处理
    } catch (e: CancellationException) {
        throw e
    } catch (e: Throwable) {
        throw IOException(e)
    }
}
```

问题：`UnknownHostException` 被当作普通 IOException 重新抛出，**无日志、无主机名记录**。

#### 2.2.2 AnalyzeUrl.executeStrRequest（业务层重试）

[`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt:520-554`](../../app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt)

```kotlin
} catch (e: Exception) {
    val isNetworkError = e is java.net.SocketTimeoutException
        || e is java.net.SocketException
        || e is java.io.InterruptedIOException
        || (e.message?.contains("Connection reset", true) == true)
    if (isNetworkError && networkRetryCount < 1) {
        networkRetryCount++
        Log.d("AnalyzeUrl", "network retry: ...")
        kotlinx.coroutines.delay(1000)
        return executeStrRequest(jsStr, sourceRegex, useWebView, isTest)
    }
    // ...
    val errorCode = when (e) {
        is java.net.UnknownHostException -> -3   // 未找到域名
        // ...
    }
}
```

问题：
1. **重试不覆盖 DNS 失败**：`isNetworkError` 判断**不包含 `UnknownHostException`**，DNS 失败直接跳过重试。
2. **错误码仅在测试模式返回**：`isTest=true` 时返回错误码 -3，非测试模式直接 `throw e`（line 535-536）。
3. 日志中 `network retry` 0 匹配，证明重试机制从未针对 DNS 失败触发。

#### 2.2.3 OkhttpUncaughtExceptionHandler（线程未捕获异常）

[`app/src/main/java/io/legado/app/help/http/OkhttpUncaughtExceptionHandler.kt:7-9`](../../app/src/main/java/io/legado/app/help/http/OkhttpUncaughtExceptionHandler.kt)

```kotlin
override fun uncaughtException(t: Thread, e: Throwable) {
    AppLog.put("Okhttp Dispatcher中的线程执行出错\n${e.localizedMessage}", e)
}
```

问题：只记录 `localizedMessage`，未记录异常类名（`e.javaClass.simpleName`），难以区分 UnknownHostException 与其他 IOException。

#### 2.2.4 Call.await（协程封装层）

[`app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt:78-94`](../../app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt)

```kotlin
suspend fun Call.await(): Response = suspendCancellableCoroutine { block ->
    block.invokeOnCancellation { cancel() }
    enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            block.resumeWithException(e)  // 直接抛出，无日志
        }
        // ...
    })
}
```

问题：`onFailure` 直接 `resumeWithException(e)`，无日志、无重试。

### 2.3 addressCache 配置

[`app/src/main/java/io/legado/app/help/config/AppConfig.kt:145-158`](../../app/src/main/java/io/legado/app/help/config/AppConfig.kt)

```kotlin
private var _addressCache: Map<String, List<InetAddress>>? = null
val addressCache: Map<String, List<InetAddress>>
    get() = _addressCache ?: run {
        val cache = hostMap.mapNotNull { (host, ipValue) ->
            // 从 customHosts 解析 host→IP 映射
        }.toMap()
        _addressCache = cache
        cache
    }
```

说明：用户可在设置中手动配置 `customHosts`（host→IP 映射），相当于本地 hosts 文件。但默认为空，需用户手动填写，普通用户不会用。

## 3. 根因分析

### 3.1 DNS 失败场景判定

**结论：非模拟器 DNS 故障，是特定书源/RSS 源域名解析失败。**

| 判据 | 说明 |
|------|------|
| 主源 `91cangku2119822.buzz` 正常 | cookie 正常设置，内容正常加载（logcat.txt:13389） |
| 视频域名 `video.sjpcdnsjp.top` 正常 | 视频地址正常输出（appLog:670） |
| 仅 3 个子域名失败 | `fengmian.fhfhtutu.com`、`img.siwazywimg2.com`、`guce.mossjav.com` |
| 失败域名均为书源关联资源域名 | 封面图、内容图、RSS 源 |

**可能原因（按概率排序）**：
1. **域名已下线/失效**（最可能）：书源维护者未及时更新，`fhfhtutu.com`、`siwazywimg2.com` 可能已停止解析。
2. **DNS 污染/劫持**：运营商或 GFW 对特定域名返回 NXDOMAIN。
3. **域名仅特定地区可解析**：CDN 地域限制。

### 3.2 是否静默吞掉

| 调用路径 | 是否有日志 | 是否重试 | 是否降级 |
|---------|----------|---------|---------|
| RSS 源（AnalyzeUrl） | 是（AppLog "rss获取内容失败" + 完整堆栈） | 否 | 否 |
| 书源文本（AnalyzeUrl） | 否（非测试模式直接 throw） | 否 | 否 |
| 图片加载（Glide + ImgDecrypt） | 部分（ImgDecrypt 记录 onFailure，Glide 记录 W 级） | 否 | 否 |
| OkHttp Dispatcher 异常 | 部分（只记录 localizedMessage，丢失类名和主机名） | 否 | 否 |

**关键问题**：`AnalyzeUrl.kt:522-525` 的重试逻辑**故意排除了 UnknownHostException**，理由可能是"域名失效重试无意义"。但这导致**临时性 DNS 污染/抖动**（如运营商 DNS 超时）也无法恢复。

### 3.3 用户感知影响

| 场景 | 影响 | 严重度 |
|------|------|-------|
| 书架封面图 | 封面显示占位符或空白 | 中（视觉体验） |
| 书详情页封面 | 封面加载失败 | 中 |
| RSS 源阅读 | "rss获取内容失败"提示，内容无法加载 | 高（功能不可用） |
| 书源正文内容 | 不受影响（主源域名正常） | 无 |
| 视频播放 | 不受影响（视频域名正常） | 无 |

**核心影响**：图片加载失败（视觉降级）+ RSS 源不可用（功能降级），不影响主要阅读功能。

### 3.4 与延伸版本对比

| 版本 | DNS 优化 | 参考 |
|------|---------|------|
| 原版阅读 | 无自定义 DNS 重试 | — |
| 蛋蛋Max | 307/308 重定向优化（非 DNS） | 本项目已借鉴（OkHttpUtils.kt:43-57） |
| 阅读T | SOCKS5 隧道 + Brotli（非 DNS） | — |
| 阅读NG | 网络日志标签（可参考日志增强） | — |

**结论**：延伸版本均无 DNS 层面的优化，需本项目自主实现 DNS 容错。

## 4. 修复方案

### 4.1 文件路径

| 文件 | 修改类型 |
|------|---------|
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\http\HttpHelper.kt` | 自定义 DNS 增加重试 + 负缓存 + 日志 |
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\analyzeRule\AnalyzeUrl.kt` | 重试机制覆盖 UnknownHostException（限1次） |
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\http\OkHttpExceptionInterceptor.kt` | 识别并记录 UnknownHostException 主机名 |
| `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\http\OkhttpUncaughtExceptionHandler.kt` | 记录完整异常类名 + message |

### 4.2 修改点

#### 4.2.1 HttpHelper.kt — 自定义 DNS 增加重试 + 负缓存 + 日志

**old_string**（HttpHelper.kt:122-127）：
```kotlin
    if (AppConfig.addressCache.isNotEmpty()) {
        builder.dns { hostname ->
            val cachedAddress = AppConfig.addressCache[hostname]
            cachedAddress ?: Dns.SYSTEM.lookup(hostname)
        }
    }
```

**new_string**：
```kotlin
    // P2-B: 自定义 DNS 增加重试 + 负缓存 + 失败日志
    // 无论 addressCache 是否为空都启用，以获得重试和日志能力
    builder.dns(RetryableDns)
```

并在文件末尾（`getProxyClient` 函数之后）新增 `RetryableDns` 对象：

```kotlin
/**
 * P2-B: 带重试 + 负缓存的 DNS 实现
 *
 * 解决问题：
 * 1. 原实现无重试，DNS 抖动/污染时直接失败
 * 2. 同一失效域名被反复解析（日志显示 252 次），浪费资源
 * 3. 失败无日志，难以排查
 *
 * 策略：
 * - addressCache 命中 → 直接返回（用户手动配置的 hosts）
 * - Dns.SYSTEM 查询，最多重试 2 次，间隔 500ms
 * - 失败后负缓存 60 秒（避免短时间内反复查询同一失效域名）
 * - 失败时记录 WARN 日志（含主机名，便于排查）
 *
 * 已知限制：负缓存可能导致域名恢复后 60 秒内仍失败 | 升级路径：可加 DoH fallback
 */
object RetryableDns : Dns {
    private const val MAX_RETRY = 2
    private const val RETRY_DELAY_MS = 500L
    private const val NEGATIVE_CACHE_TTL_MS = 60_000L

    private val negativeCache = java.util.concurrent.ConcurrentHashMap<String, Long>()

    override fun lookup(hostname: String): List<InetAddress> {
        // 1. 用户配置的 addressCache 优先
        val cachedAddress = AppConfig.addressCache[hostname]
        if (cachedAddress.isNotEmpty()) {
            return cachedAddress
        }
        // 2. 负缓存检查（60秒内失败的域名直接抛出，避免反复查询）
        val expireAt = negativeCache[hostname]
        if (expireAt != null && System.currentTimeMillis() < expireAt) {
            throw java.net.UnknownHostException("hostname=$hostname (negative cached)")
        }
        // 3. 重试查询
        var lastError: java.net.UnknownHostException? = null
        for (attempt in 0..MAX_RETRY) {
            try {
                val result = Dns.SYSTEM.lookup(hostname)
                negativeCache.remove(hostname)  // 成功则清除负缓存
                return result
            } catch (e: java.net.UnknownHostException) {
                lastError = e
                if (attempt < MAX_RETRY) {
                    try {
                        Thread.sleep(RETRY_DELAY_MS)
                    } catch (_: InterruptedException) {
                        Thread.currentThread().interrupt()
                        throw e
                    }
                }
            }
        }
        // 4. 全部失败：写入负缓存 + 日志
        negativeCache[hostname] = System.currentTimeMillis() + NEGATIVE_CACHE_TTL_MS
        AppLog.put(
            "DNS解析失败 hostname=$hostname, 已重试${MAX_RETRY}次, 负缓存${NEGATIVE_CACHE_TTL_MS}ms",
            lastError
        )
        throw lastError!!
    }
}
```

需要在文件顶部补充 import：
```kotlin
import io.legado.app.constant.AppLog
import java.net.InetAddress
```

#### 4.2.2 AnalyzeUrl.kt — 重试机制覆盖 UnknownHostException（限1次）

**old_string**（AnalyzeUrl.kt:521-534）：
```kotlin
            // P2-3.1: 网络重试机制（Connection reset/Timeout 自动重试1次，间隔1秒）
            val isNetworkError = e is java.net.SocketTimeoutException
                || e is java.net.SocketException
                || e is java.io.InterruptedIOException
                || (e.message?.contains("Connection reset", true) == true)
            if (isNetworkError && networkRetryCount < 1) {
                networkRetryCount++
                Log.d("AnalyzeUrl", "network retry: path=${url.take(50)}, exception=${e.javaClass.simpleName}, retry=$networkRetryCount")
                kotlinx.coroutines.delay(1000)
                return executeStrRequest(jsStr, sourceRegex, useWebView, isTest)
            }
            if (isNetworkError) {
                Log.d("AnalyzeUrl", "network retry exhausted: path=${url.take(50)}, exception=${e.javaClass.simpleName}")
            }
```

**new_string**：
```kotlin
            // P2-3.1: 网络重试机制（Connection reset/Timeout 自动重试1次，间隔1秒）
            // P2-B: UnknownHostException 纳入重试（应对临时 DNS 抖动/污染，限1次）
            val isNetworkError = e is java.net.SocketTimeoutException
                || e is java.net.SocketException
                || e is java.io.InterruptedIOException
                || (e.message?.contains("Connection reset", true) == true)
            val isDnsError = e is java.net.UnknownHostException
            if ((isNetworkError || isDnsError) && networkRetryCount < 1) {
                networkRetryCount++
                Log.d("AnalyzeUrl", "network retry: path=${url.take(50)}, exception=${e.javaClass.simpleName}, retry=$networkRetryCount")
                kotlinx.coroutines.delay(1000)
                return executeStrRequest(jsStr, sourceRegex, useWebView, isTest)
            }
            if (isNetworkError || isDnsError) {
                Log.d("AnalyzeUrl", "network retry exhausted: path=${url.take(50)}, exception=${e.javaClass.simpleName}")
            }
```

#### 4.2.3 OkHttpExceptionInterceptor.kt — 识别并记录 UnknownHostException

**old_string**（OkHttpExceptionInterceptor.kt:11-21）：
```kotlin
    @Throws(IOException::class)
    override fun intercept(chain: Interceptor.Chain): Response {
        try {
            return chain.proceed(chain.request())
        } catch (e: IOException) {
            throw e
        } catch (e: CancellationException) {
            throw e  // 守卫：协程取消异常必须重新抛出，不能包装成 IOException
        } catch (e: Throwable) {
            throw IOException(e)
        }
    }
```

**new_string**：
```kotlin
    @Throws(IOException::class)
    override fun intercept(chain: Interceptor.Chain): Response {
        try {
            return chain.proceed(chain.request())
        } catch (e: java.net.UnknownHostException) {
            // P2-B: 记录 DNS 失败主机名，便于排查（RetryableDns 已处理重试和负缓存）
            AppLog.put("DNS解析失败 host=${chain.request().url.host}", e)
            throw e
        } catch (e: IOException) {
            throw e
        } catch (e: CancellationException) {
            throw e  // 守卫：协程取消异常必须重新抛出，不能包装成 IOException
        } catch (e: Throwable) {
            throw IOException(e)
        }
    }
```

需要在文件顶部补充 import：
```kotlin
import io.legado.app.constant.AppLog
```

#### 4.2.4 OkhttpUncaughtExceptionHandler.kt — 记录完整异常类名

**old_string**（OkhttpUncaughtExceptionHandler.kt:7-9）：
```kotlin
    override fun uncaughtException(t: Thread, e: Throwable) {
        AppLog.put("Okhttp Dispatcher中的线程执行出错\n${e.localizedMessage}", e)
    }
```

**new_string**：
```kotlin
    override fun uncaughtException(t: Thread, e: Throwable) {
        // P2-B: 记录异常类名，便于区分 UnknownHostException / SocketTimeoutException 等
        AppLog.put("Okhttp Dispatcher中的线程执行出错\n类型=${e.javaClass.simpleName}\n消息=${e.localizedMessage}", e)
    }
```

### 4.3 风险评估

| 修改点 | 风险 | 影响范围 | 缓解措施 |
|-------|------|---------|---------|
| **RetryableDns**（HttpHelper.kt） | 低 | 所有 OkHttp 请求（含书源/RSS/图片） | 重试仅在 2 次内、间隔 500ms，最坏增加 1 秒延迟；负缓存 60 秒可能延迟域名恢复 | 负缓存 TTL 设为 60 秒（可接受）；`addressCache` 优先级不变 |
| **AnalyzeUrl 重试覆盖 DNS**（AnalyzeUrl.kt） | 低 | 书源/RSS 文本请求 | DNS 失败重试 1 次增加 1 秒延迟 | 仅限 `networkRetryCount < 1`，不会无限重试 |
| **OkHttpExceptionInterceptor 日志**（OkHttpExceptionInterceptor.kt） | 极低 | 所有 OkHttp 请求 | 仅新增日志，不改控制流 | 日志量可控（DNS 失败已由 RetryableDns 负缓存限流） |
| **OkhttpUncaughtExceptionHandler 日志**（OkhttpUncaughtExceptionHandler.kt） | 极低 | OkHttp Dispatcher 线程 | 仅新增异常类名到日志 | 无 |

**兼容性**：
- `RetryableDns` 保持 `addressCache` 优先级，用户手动配置的 hosts 不受影响。
- 所有修改均为"增强容错 + 增加日志"，不改变原有成功路径行为。
- 不涉及数据库 schema、书源格式、UI 布局变更。

**回归测试要点**：
1. 正常书源加载不受影响（主源 `91cangku2119822.buzz` 应正常）。
2. DNS 失败时日志应出现 `DNS解析失败 host=xxx`（OkHttpExceptionInterceptor）和 `DNS解析失败 hostname=xxx, 已重试2次`（RetryableDns）。
3. 同一失效域名 60 秒内只查询 1 次（负缓存生效），日志中该域名的失败记录应大幅减少。
4. RSS 源（guce.mossjav.com）失败后应有重试日志 `network retry: ... exception=UnknownHostException`。

### 4.4 未实施的优化（建议后续 OpenSpec）

| 优化 | 说明 | 优先级 |
|------|------|-------|
| DoH (DNS over HTTPS) | 通过 HTTPS 查询 DNS（如 `https://dns.google/dns-query`），绕过运营商 DNS 污染/劫持 | 中（需用户可配置 DoH 服务器） |
| 多 DNS 服务器轮询 | 同时查询多个 DNS 服务器（如 8.8.8.8 + 114.114.114.114 + 系统 DNS），取首个成功结果 | 中（需自定义 Dns 接口） |
| 图片加载降级策略 | Glide 图片加载失败时，尝试通过书源代理或备用域名加载 | 低（需书源配置支持） |
| DNS 失败统计上报 | 统计各域名 DNS 失败次数，提示用户该域名可能失效 | 低（需 UI 展示） |

## 5. 总结

| 维度 | 结论 |
|------|------|
| **根因** | 非模拟器 DNS 故障，是特定书源/RSS 源的图片资源域名解析失败（`fengmian.fhfhtutu.com` 252次、`img.siwazywimg2.com` 96次、`guce.mossjav.com` RSS源），可能原因：域名下线/DNS污染/地域限制 |
| **代码问题** | 1) HttpHelper.kt 自定义 DNS 无重试无负缓存无日志；2) AnalyzeUrl.kt 重试机制故意排除 UnknownHostException；3) OkHttpExceptionInterceptor 对 DNS 失败无特殊处理；4) OkhttpUncaughtExceptionHandler 丢失异常类名 |
| **用户感知** | 封面图加载失败（视觉降级）+ RSS 源不可用（功能降级），不影响正文阅读和视频播放 |
| **修复点** | 4 处修改：RetryableDns（重试+负缓存+日志）、AnalyzeUrl 重试覆盖 DNS、OkHttpExceptionInterceptor DNS 日志、OkhttpUncaughtExceptionHandler 异常类名 |
| **风险评估** | 低风险，所有修改为增强容错+增加日志，不改变成功路径行为 |
