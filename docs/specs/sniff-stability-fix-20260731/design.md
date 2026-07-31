# 嗅探稳定性修复 - 技术设计（V3 修订版）

> 状态：🔄 设计中（V3 修订版）
> 创建日期：2026-07-31
> 修订日期：2026-07-31 16:15（V3：基于渗透式深度审计+主代理源码逐行核实）
> Spec ID：sniff-stability-fix-20260731
> 关联文档：[README.md](./README.md) / [spec.md](./spec.md) / [tasks.md](./tasks.md)
> 审计报告：[audit-report-v2-deep.md](./audit-report-v2-deep.md)（44个纰漏，V3已全部修复）

## V3 修订要点（基于主代理源码逐行核实）

### 核实修正（审计报告不准确处）

1. **NEW-ERROR-2 修正**：审计报告称"Keep-Alive触发400 BadRequest"不完全准确。CronetInterceptor.kt L129注释"手动设置会导致400 BadRequest"是针对**Cronet引擎**，OkHttp core能正常处理Keep-Alive（HTTP/1.1标准头）。但缓存命中走OkHttp路径与正常Cronet路径不一致，仍应清理保持一致。
2. **NEW-ERROR-6/3 修正**：是**实施顺序问题**非逻辑错误。design.md伪代码顺序正确（FR-2在前），但未明确说明插入位置。V3明确：isCertificateError分支必须在isProtocolError/isHttp2ProtocolError判定之前插入并`return`。

### V3 核心改进

1. **FR-1 核心改进**：缓存命中后走 `proceedWithCronet` 而非 `chain.proceed`（保留Cronet BoringSSL TLS指纹，解决NEW-ERROR-9）
2. **FR-1 复用builder逻辑**：缓存命中分支复用L128-143的builder逻辑（含Keep-Alive/Accept-Encoding/Referer/Cookie处理，解决NEW-ERROR-2/12/13）
3. **FR-1 改用LruCache**：替代"超限全清"策略（解决NEW-ERROR-11），与现有RedirectCacheInterceptor一致（500条/10分钟）
4. **FR-2 前缀匹配**：`ERR_CERT_`+`ERR_SSL_`覆盖20+错误码（解决NEW-WARN-5），复用L208-209
5. **FR-2 分支前置return**：明确插入位置在isProtocolError之前，避免ERR_SSL_PROTOCOL_ERROR误判（解决NEW-ERROR-6）
6. **FR-2 单独去重状态**：`lastCertError`/`lastCertErrorTime`，不与协议错误共享（解决NEW-ERROR-14）
7. **FR-3 host级清理**：`clearNegativeCache(hostname)`精准清理（解决NEW-ERROR-4部分）+ 清`dohDisabledUntil`（解决熔断期间无效）
8. **FR-5 删除方案B**：Call.Factory是客户端级别不能按请求切换（解决NEW-ERROR-10）
9. **FR-6 移除cronetEngineHealthy**：依赖现有`engine==null`检查，避免死锁（解决ERROR-1）
10. **FR-6 独立常量**：新增`RECOVERY_PROBE_CHECK_INTERVAL_MS`仅用于恢复探测触发检查，不修改`RECOVERY_PROBE_INTERVAL_MS`（解决NEW-ERROR-5，影响L96/L239/L261/L277共4处）
11. **新增FR-7**：图片加载根因分析（解决MISS-1，Glide配置/rateLimiter/ProgressResponseBody）
12. **提供完整intercept()代码**：非伪代码，覆盖所有分支交互（解决NEW-WARN-7）
13. **FR-1 实施注意事项（V3.1补充）**：源码核实发现 HttpHelper.kt L109 已注册独立拦截器 `RedirectCacheInterceptor`（LruCache 500条+TTL 10分钟+Referer/Cookie维度key+命中改写URL跳过302），在 CronetInterceptor 之前执行。V3 的 FR-1 在 CronetInterceptor 内部新增302缓存会与之形成**双重缓存**。
    - **实施推荐方案**：增强现有 `RedirectCacheInterceptor`（修改 L67-84 从 `response.request.url` 获取多层重定向最终URL，而非仅 Location 头），不在 CronetInterceptor 内部新增缓存
    - **原因**：RedirectCacheInterceptor 命中缓存后走 `chain.proceed(redirectedRequest)`，会自动触发后续 CronetInterceptor 执行（收到 finalUrl），自然走 Cronet 引擎保留 BoringSSL TLS 指纹，与 V3 的"缓存命中走 proceedWithCronet"效果等价
    - **备选方案**：如保留 CronetInterceptor 内部缓存，需先移除 HttpHelper.kt L109 的 RedirectCacheInterceptor 注册，避免双重缓存
    - **design.md V3 保留 CronetInterceptor 内部缓存代码作为备选方案参考**

## 1. 架构设计（V3）

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OkHttp 请求链（V3 架构）                          │
│                                                                     │
│  Request → [CronetInterceptor] → [其他拦截器] → Response            │
│                │                                                    │
│                ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CronetInterceptor.intercept()  (V3 完整实现)                │  │
│  │                                                              │  │
│  │  1. isCanceled 检查                                          │  │
│  │  2. original = chain.request()                               │  │
│  │  3. 降级检查（degradedForSession）                            │  │
│  │     - FR-6 V3: 用独立常量 RECOVERY_PROBE_CHECK_INTERVAL_MS   │  │
│  │     - 降级期间仍查302缓存（命中走OkHttp，接受不恢复探测折中） │  │
│  │  4. FR-1 V3: 302缓存命中检查                                 │  │
│  │     - 命中 → buildRedirectedRequest(复用L128-143逻辑)        │  │
│  │     - 命中 → proceedWithCronet(保留TLS指纹, 非chain.proceed) │  │
│  │     - Cronet失败 → 回退chain.proceed走OkHttp                 │  │
│  │  5. Cronet引擎获取（现有engine==null检查, FR-6移除healthy）   │  │
│  │  6. 请求执行（builder头处理 + CookieManager + proceedWithCronet）│
│  │  7. 响应处理：                                                │  │
│  │     - FR-1 V3: 缓存多层重定向最终URL(response.request.url)   │  │
│  │     - 恢复探测成功计数（现有逻辑）                            │  │
│  │  8. 异常处理：                                                │  │
│  │     - Canceled → 跳过（现有逻辑）                            │  │
│  │     - FR-2: 证书错误(ERR_CERT_/ERR_SSL_) → 降级OkHttp+return │  │
│  │     - FR-3: NAME_NOT_RESOLVED → host级清理DoH+降级OkHttp+return│
│  │     - 协议错误 → 现有降级逻辑（不修改RECOVERY_PROBE_INTERVAL）│  │
│  │     - 其他错误 → 回退OkHttp（现有逻辑）                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [失败回退] → chain.proceed(original) 走 OkHttp                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责（V3）

| 模块 | 职责 | 变更类型 |
|------|------|---------|
| `CronetInterceptor` | Cronet请求执行+降级+302缓存+证书错误处理+NAME_NOT_RESOLVED处理 | 新增FR-1/2/3/6 |
| `RedirectCache`(内部) | 302重定向映射缓存管理（LruCache+多层重定向） | 新增 |
| `DohDns` | DoH解析+负缓存 | 新增`clearNegativeCache(hostname)`host级清理 |
| `SSLHelper`(已存在) | 信任所有证书 | 无需修改（FR-2复用） |
| `HttpHelper` | 全局OkHttp客户端配置 | FR-5评估（方案A完全替换） |
| `Glide配置`(FR-7新增) | 图片加载根因分析 | 新增评估 |

## 2. 数据结构设计（V3）

### 2.1 302重定向缓存（V3：LruCache+多层重定向+Referer维度）

```kotlin
/**
 * 302重定向缓存条目
 * @param finalUrl 最终URL（跟随所有重定向后的目标URL，非仅第一层）
 * @param timestamp 缓存写入时间戳
 */
private data class RedirectCacheEntry(
    val finalUrl: String,
    val timestamp: Long
)

/**
 * 302重定向缓存（LruCache + TTL，V3改进）
 *
 * V3改进点：
 * - 改用LruCache替代"超限全清"策略（与现有RedirectCacheInterceptor一致）
 * - 缓存键加Referer维度（防盗链场景finalUrl可能随Referer变化）
 * - 缓存命中走proceedWithCronet而非chain.proceed（保留TLS指纹）
 * - 使用response.request.url获取跟随所有重定向后的最终URL
 *
 * 设计要点：
 * - 缓存键：原始URL + Referer维度
 * - 缓存值：最终URL + 时间戳
 * - 容量：500条（与现有RedirectCacheInterceptor一致，V2的200条过小）
 * - TTL：10分钟（与现有RedirectCacheInterceptor一致，V2的5分钟过短）
 * - 线程安全：synchronized(cache)（与现有RedirectCacheInterceptor一致）
 */
companion object {
    // FR-1 V3: 缓存常量（与现有RedirectCacheInterceptor一致）
    private const val REDIRECT_CACHE_TTL_MS = 10 * 60 * 1000L  // 10分钟
    private const val REDIRECT_CACHE_MAX_SIZE = 500
    private val redirectCache = android.util.LruCache<String, RedirectCacheEntry>(REDIRECT_CACHE_MAX_SIZE)
    
    // FR-6 V3: 独立常量，仅用于恢复探测触发检查（不影响L96/L239/L261/L277的降级时长）
    private const val RECOVERY_PROBE_CHECK_INTERVAL_MS = 3 * 60 * 1000L  // 3分钟
    
    // FR-2 V3: 证书错误单独去重状态（不与协议错误共享lastLoggedError）
    @Volatile private var lastCertError: String? = null
    @Volatile private var lastCertErrorTime = 0L
}
```

### 2.2 证书错误判定（V3：前缀匹配）

```kotlin
/**
 * 证书错误判定（FR-2 V3：前缀匹配，覆盖20+错误码）
 *
 * V3改进：
 * - 前缀匹配ERR_CERT_+ERR_SSL_（复用CronetInterceptor.kt L208-209现有判断）
 * - 覆盖20+Chromium证书错误码（ERR_CERT_AUTHORITY_INVALID/ERR_CERT_COMMON_NAME_INVALID等）
 * - 覆盖SSL协议错误（ERR_SSL_PROTOCOL_ERROR/ERR_SSL_DECRYPT_ERROR等）
 *
 * 注意：此分支必须在isProtocolError/isHttp2ProtocolError判定之前插入并return
 * 原因：ERR_SSL_PROTOCOL_ERROR含PROTOCOL_ERROR会匹配isHttp2ProtocolError
 */
private fun isCertificateError(errorMsg: String): Boolean {
    return errorMsg.contains("ERR_CERT_", true)
        || errorMsg.contains("ERR_SSL_", true)
}
```

### 2.3 NAME_NOT_RESOLVED判定（保持不变）

```kotlin
private fun isNameNotResolvedError(errorMsg: String): Boolean {
    return errorMsg.contains("ERR_NAME_NOT_RESOLVED", true)
}
```

### 2.4 URL脱敏函数（V3新增，解决NEW-ERROR-7）

```kotlin
/**
 * URL脱敏（日志不输出完整URL，与DohDns.maskHost模式一致）
 * 仅保留协议+域名前2字符+路径模式，隐藏完整路径和查询参数
 */
private fun maskUrl(url: String): String {
    return try {
        val parsed = okhttp3.HttpUrl.parse(url) ?: return "***"
        val host = parsed.host
        val maskedHost = "${host.take(2)}***"
        "${parsed.scheme}://$maskedHost${parsed.encodedPath.take(20)}***"
    } catch (e: Exception) {
        "***"
    }
}
```

## 3. 完整 intercept() 代码（V3核心，非伪代码）

> 基于现有CronetInterceptor.kt L78-285完整重写，集成FR-1/2/3/6
> 保留所有现有降级机制（9+个），新增FR分支前置return避免干扰

```kotlin
@Throws(IOException::class)
override fun intercept(chain: Interceptor.Chain): Response {
    // 1. 取消检查（现有逻辑L79-81）
    if (chain.call().isCanceled()) {
        throw IOException("Canceled")
    }
    
    // 2. 获取原始请求（现有逻辑L82）
    val original: Request = chain.request()
    val originalUrl = original.url.toString()
    
    // 3. 降级检查 + 恢复探测（现有逻辑L85-111，FR-6 V3修改）
    var isRecoveryProbe = false
    if (degradedForSession) {
        val elapsed = System.currentTimeMillis() - degradedTimeMs
        val currentIntervalMs = if (lastRecoveryTimeMs > 0
            && (degradedTimeMs - lastRecoveryTimeMs) < UNSTABLE_RECOVERY_WINDOW_MS
        ) {
            EXTENDED_DEGRADE_INTERVAL_MS
        } else {
            // FR-6 V3: 用独立常量，不修改RECOVERY_PROBE_INTERVAL_MS
            // 原因：RECOVERY_PROBE_INTERVAL_MS被L96/L239/L261/L277共4处使用
            // 修改会影响所有非HTTP/2、非震荡的降级时长，弱网下加剧乒乓
            RECOVERY_PROBE_CHECK_INTERVAL_MS
        }
        if (elapsed < currentIntervalMs) {
            // FR-1 V3: 降级期间仍查302缓存（命中走OkHttp，接受不恢复探测的折中）
            val cachedRedirect = getValidRedirectCache(originalUrl, original.header("Referer"))
            if (cachedRedirect != null) {
                AppLog.putDebug("Cronet 302 cache hit (degraded): ${maskUrl(originalUrl)} -> ${maskUrl(cachedRedirect)}")
                val redirectedRequest = buildRedirectedRequest(original, cachedRedirect)
                return chain.proceed(redirectedRequest)  // 降级期间走OkHttp
            }
            return chain.proceed(original)
        }
        // BUG6-V2: 优先放行失败host的请求（现有逻辑L101-108）
        val requestHost = original.url.host
        val hint = lastFailedHostHint
        if (hint != null && requestHost != hint) {
            AppLog.putDebug("Cronet 探测跳过非失败host: requestHost=${requestHost.take(3)}***, hintHost=${hint.take(3)}***")
            return chain.proceed(original)
        }
        isRecoveryProbe = true
        AppLog.put("Cronet 降级满 ${currentIntervalMs / 60000} 分钟, 放行失败host请求探测恢复")
    }
    
    // 4. FR-1 V3: 302缓存命中检查（降级检查之后，Cronet引擎获取之前）
    // V3核心改进：缓存命中走proceedWithCronet而非chain.proceed（保留TLS指纹）
    val cachedRedirect = getValidRedirectCache(originalUrl, original.header("Referer"))
    if (cachedRedirect != null) {
        AppLog.putDebug("Cronet 302 cache hit: ${maskUrl(originalUrl)} -> ${maskUrl(cachedRedirect)}")
        // V3: 复用L128-143 builder逻辑（含Keep-Alive/Accept-Encoding/Referer/Cookie处理）
        val redirectedRequest = buildRedirectedRequest(original, cachedRedirect)
        // V3: 缓存命中仍走Cronet（保留BoringSSL TLS指纹，解决NEW-ERROR-9）
        val engine = try {
            if (!CronetLoader.install()) null
            else cronetEngine
        } catch (e: Throwable) {
            AppLog.put("getCronetEngine触发异常", e)
            null
        }
        if (engine == null) {
            // 引擎不可用，回退OkHttp
            return chain.proceed(redirectedRequest)
        }
        try {
            val response = proceedWithCronet(redirectedRequest, chain.call(), chain.readTimeoutMillis())!!
            return response
        } catch (e: Exception) {
            // 缓存命中但Cronet失败，回退OkHttp（保留现有异常处理逻辑）
            AppLog.put("Cronet 302 cache hit but Cronet failed, fallback OkHttp: ${e.message?.take(60)}")
            // 落入下方完整异常处理逻辑（复用cronetException机制）
            // 注意：此处不直接return，让异常落入下方catch块处理降级逻辑
            throw e
        }
    }
    
    // 5. Cronet引擎获取（现有逻辑L116-125，FR-6 V3移除cronetEngineHealthy检查）
    // FR-6 V3: 移除cronetEngineHealthy标志位，依赖现有engine==null检查
    // 原因：cronetEngineHealthy初始false+仅在Cronet成功后置true=死锁，永远走OkHttp
    val engine = try {
        if (!CronetLoader.install()) null
        else cronetEngine
    } catch (e: Throwable) {
        AppLog.put("getCronetEngine触发异常", e)
        null
    }
    if (engine == null) {
        return chain.proceed(original)
    }
    
    // 6. 请求执行（现有逻辑L127-155 + FR-1 V3缓存写入）
    val cronetException: Exception
    try {
        val builder: Request.Builder = original.newBuilder()
        // 移除Keep-Alive,手动设置会导致400 BadRequest（Cronet引擎）
        builder.removeHeader("Keep-Alive")
        builder.removeHeader("Accept-Encoding")
        
        // Referer协议降级处理（现有逻辑L133-141）
        if (!original.isHttps &&
            original.header("User-Agent")?.startsWith("Mozilla", true) == true
        ) {
            val referer = original.header("Referer")
            if (referer != null && referer.startsWith("https:", true)) {
                builder.header("Referer", "http" + referer.substring(5))
            }
        }
        
        var newReq = builder.build()
        
        // Cookie加载（现有逻辑L145-147）
        if (newReq.header(cookieJarHeader) != null) {
            newReq = CookieManager.loadRequest(newReq)
        }
        
        // 探测请求超时收紧（现有逻辑L149-154）
        val readTimeout = if (isRecoveryProbe) {
            minOf(chain.readTimeoutMillis(), RECOVERY_PROBE_TIMEOUT_MS)
        } else {
            chain.readTimeoutMillis()
        }
        val response = proceedWithCronet(newReq, chain.call(), readTimeout)!!
        
        // FR-1 V3: 缓存多层重定向的最终URL（使用response.request.url）
        val finalUrl = response.request.url.toString()
        if (originalUrl != finalUrl) {
            putRedirectCache(originalUrl, original.header("Referer"), finalUrl)
            AppLog.putDebug("Cronet redirect cached: ${maskUrl(originalUrl)} -> ${maskUrl(finalUrl)}")
        }
        
        // 恢复探测成功计数（现有逻辑L156-172）
        if (degradedForSession) {
            recoverySuccessCount++
            if (recoverySuccessCount >= RECOVERY_SUCCESS_THRESHOLD) {
                degradedForSession = false
                protocolErrorCount = 0
                recoverySuccessCount = 0
                lastRecoveryTimeMs = System.currentTimeMillis()
                lastFailedHostHint = null
                AppLog.put("Cronet 恢复探测连续成功 $RECOVERY_SUCCESS_THRESHOLD 次, 自动切回 Cronet")
            } else {
                degradedTimeMs = System.currentTimeMillis()
                AppLog.put("Cronet 恢复探测成功 $recoverySuccessCount/$RECOVERY_SUCCESS_THRESHOLD, 待再次确认")
            }
        }
        return response
    } catch (e: Exception) {
        cronetException = e
        val errMsg = e.message.toString()
        
        // Canceled处理（现有逻辑L183-193）
        val isCanceled = errMsg.contains("Canceled", true) || errMsg.contains("Cancelled", true)
        if (isCanceled) {
            AppLog.putDebug("Cronet request canceled (normal): ${errMsg.take(60)}")
            try {
                return chain.proceed(original)
            } catch (e2: Exception) {
                e2.addSuppressed(cronetException)
                throw e2
            }
        }
        
        // FR-2 V3: 证书错误降级（必须在isProtocolError/isHttp2ProtocolError之前插入并return）
        // 原因：ERR_SSL_PROTOCOL_ERROR含PROTOCOL_ERROR会匹配isHttp2ProtocolError导致误降级
        // V3改进：前缀匹配ERR_CERT_+ERR_SSL_覆盖20+错误码
        if (isCertificateError(errMsg)) {
            logCertError(errMsg)  // V3: 单独去重状态，不与协议错误共享
            try {
                return chain.proceed(original)  // OkHttp已配置信任所有证书
            } catch (e2: Exception) {
                // OkHttp也失败，说明是TLS指纹问题（非证书问题）
                AppLog.put("Cronet 证书错误降级 OkHttp 失败, 疑似 TLS 指纹问题, 建议启用 FR-5 桥接层: error=${e2.message?.take(80)}")
                e2.addSuppressed(cronetException)
                throw e2
            }
        }
        
        // FR-3 V3: NAME_NOT_RESOLVED不累计降级+host级清理DoH负缓存
        // V3改进：host级清理clearNegativeCache(hostname)+清dohDisabledUntil
        if (isNameNotResolvedError(errMsg)) {
            AppLog.put("Cronet NAME_NOT_RESOLVED (DoH failure, not Cronet issue): ${errMsg.take(80)}")
            // V3: host级清理（非全清），避免影响其他域名
            DohDns.clearNegativeCache(original.url.host)
            try {
                return chain.proceed(original)
            } catch (e2: Exception) {
                e2.addSuppressed(cronetException)
                throw e2
            }
        }
        
        // 协议错误判断（现有逻辑L196-201）
        val isProtocolError = errMsg.contains("PROTOCOL_ERROR", true)
            || errMsg.contains("StreamReset", true)
            || errMsg.contains("System error", true)
            || errMsg.contains("ERR_QUIC", true)
            || errMsg.contains("ERR_CONNECTION", true)
            || errMsg.contains("ERR_SOCKET", true)
        val isHttp2ProtocolError = errMsg.contains("ERR_HTTP2_PROTOCOL_ERROR", true)
            || errMsg.contains("PROTOCOL_ERROR", true)
        val isConnectionRefused = errMsg.contains("ERR_CONNECTION_REFUSED", true)
        
        // 证书错误已上面return，这里不会到达（保留现有L208-212注释）
        if (!errMsg.contains("ERR_CERT_", true)
            && !errMsg.contains("ERR_SSL_", true)
        ) {
            e.printOnDebug()
        }
        
        // P1-2: 连接拒绝不累计降级（现有逻辑L214-215）
        if (isConnectionRefused) {
            AppLog.putDebug("Cronet 连接拒绝(可能是DoH失败), 不累计降级: error=${errMsg.take(80)}")
        } else if (isProtocolError) {
            // 现有协议错误降级逻辑（L216-269，保持不变）
            val now = System.currentTimeMillis()
            val failedHost = original.url.host
            if (failedHost != lastFailedHostHint) {
                lastFailedHostHint = failedHost
            }
            val inStartupGrace = now - classLoadTimeMs < STARTUP_GRACE_MS
            if (inStartupGrace) {
                AppLog.put("Cronet 启动宽限期内协议错误, 不累计: error=${errMsg.take(80)}")
            } else {
                protocolErrorCount++
                if (errMsg != lastLoggedError || now - lastLoggedErrorTime > LOG_DEDUP_INTERVAL_MS) {
                    AppLog.put("Cronet 协议错误，回退到 OkHttp: error=${errMsg.take(80)} (累计 $protocolErrorCount 次)")
                    lastLoggedError = errMsg
                    lastLoggedErrorTime = now
                }
                if (degradedForSession) {
                    // FR-6 V3: 恢复探测失败用RECOVERY_PROBE_INTERVAL_MS（不修改）
                    val recoveryIntervalMs = if (isHttp2ProtocolError) HTTP2_PROTOCOL_ERROR_DEGRADE_INTERVAL_MS else RECOVERY_PROBE_INTERVAL_MS
                    degradedTimeMs = now
                    recoverySuccessCount = 0
                    AppLog.put("Cronet 恢复探测失败, 继续降级 OkHttp (${recoveryIntervalMs / 60000} 分钟后再探测, isHttp2=$isHttp2ProtocolError)")
                } else if (protocolErrorCount >= DEGRADE_THRESHOLD) {
                    degradedForSession = true
                    val now2 = System.currentTimeMillis()
                    val isUnstableRecovery = lastRecoveryTimeMs > 0 && (now2 - lastRecoveryTimeMs) < UNSTABLE_RECOVERY_WINDOW_MS
                    val intervalMs = when {
                        isUnstableRecovery -> {
                            AppLog.put("Cronet 恢复后 ${UNSTABLE_RECOVERY_WINDOW_MS / 1000} 秒内再次降级, 延长降级间隔到 ${EXTENDED_DEGRADE_INTERVAL_MS / 60000} 分钟 (震荡抑制)")
                            EXTENDED_DEGRADE_INTERVAL_MS
                        }
                        isHttp2ProtocolError -> {
                            AppLog.put("Cronet HTTP/2 协议错误达 $DEGRADE_THRESHOLD 次, 降级到 OkHttp (${HTTP2_PROTOCOL_ERROR_DEGRADE_INTERVAL_MS / 1000} 秒后自动探测恢复)")
                            HTTP2_PROTOCOL_ERROR_DEGRADE_INTERVAL_MS
                        }
                        else -> {
                            // FR-6 V3: 达阈值降级用RECOVERY_PROBE_INTERVAL_MS（不修改）
                            RECOVERY_PROBE_INTERVAL_MS
                        }
                    }
                    degradedTimeMs = now2
                    lastRecoveryTimeMs = 0
                    if (!isUnstableRecovery && !isHttp2ProtocolError) {
                        AppLog.put("Cronet 连续协议错误达 $DEGRADE_THRESHOLD 次, 降级到 OkHttp (${intervalMs / 60000} 分钟后自动探测恢复)")
                    }
                }
            }
        } else if (degradedForSession) {
            // 现有非协议错误降级计时刷新逻辑（L271-278，保持不变）
            // FR-2 V3: 证书错误已上面return，不会落入此分支刷新降级计时
            degradedTimeMs = System.currentTimeMillis()
            recoverySuccessCount = 0
            AppLog.put("Cronet 恢复探测失败(非协议错误), ${RECOVERY_PROBE_INTERVAL_MS / 60000} 分钟后再探测")
        }
    }
    // 回退OkHttp（现有逻辑L280-285）
    try {
        return chain.proceed(original)
    } catch (e: Exception) {
        e.addSuppressed(cronetException)
        throw e
    }
}

/**
 * FR-1 V3: 构造重定向请求（复用L128-143 builder逻辑）
 * 解决NEW-ERROR-2/12/13：缓存命中分支跳过Keep-Alive/Accept-Encoding/Referer/Cookie处理
 */
private fun buildRedirectedRequest(original: Request, redirectUrl: String): Request {
    val builder = original.newBuilder()
        .url(redirectUrl)
    // 复用L128-143头处理逻辑
    builder.removeHeader("Keep-Alive")
    builder.removeHeader("Accept-Encoding")
    // Referer协议降级处理
    if (!original.isHttps &&
        original.header("User-Agent")?.startsWith("Mozilla", true) == true
    ) {
        val referer = original.header("Referer")
        if (referer != null && referer.startsWith("https:", true)) {
            builder.header("Referer", "http" + referer.substring(5))
        }
    }
    var newReq = builder.build()
    // Cookie加载
    if (newReq.header(cookieJarHeader) != null) {
        newReq = CookieManager.loadRequest(newReq)
    }
    return newReq
}

/**
 * FR-1 V3: 获取有效的302缓存（LruCache + TTL + Referer维度）
 */
private fun getValidRedirectCache(originalUrl: String, referer: String?): String? {
    val cacheKey = buildRedirectCacheKey(originalUrl, referer)
    synchronized(redirectCache) {
        val entry = redirectCache.get(cacheKey) ?: return null
        val now = System.currentTimeMillis()
        if (now - entry.timestamp > REDIRECT_CACHE_TTL_MS) {
            redirectCache.remove(cacheKey)
            return null
        }
        return entry.finalUrl
    }
}

/**
 * FR-1 V3: 写入302缓存（LruCache自动淘汰，无需全清）
 */
private fun putRedirectCache(originalUrl: String, referer: String?, finalUrl: String) {
    val cacheKey = buildRedirectCacheKey(originalUrl, referer)
    synchronized(redirectCache) {
        redirectCache.put(cacheKey, RedirectCacheEntry(finalUrl, System.currentTimeMillis()))
    }
}

/**
 * FR-1 V3: 构建缓存键（URL + Referer维度）
 * 防盗链场景finalUrl可能随Referer变化
 */
private fun buildRedirectCacheKey(url: String, referer: String?): String {
    val refererKey = referer?.let { it.take(20) } ?: ""
    return "$url|referer=$refererKey"
}

/**
 * FR-2 V3: 证书错误日志去重（单独状态，不与协议错误共享）
 * 解决NEW-ERROR-14：复用lastLoggedError与协议错误共享去重状态导致失效
 */
private fun logCertError(errMsg: String) {
    val now = System.currentTimeMillis()
    val errorKey = "CERT_ERROR:${errMsg.take(50)}"
    if (errorKey != lastCertError || now - lastCertErrorTime > LOG_DEDUP_INTERVAL_MS) {
        AppLog.put("Cronet 证书错误, 降级 OkHttp (复用 SSLHelper 信任所有证书): error=${errMsg.take(80)} (不累计降级计数)")
        lastCertError = errorKey
        lastCertErrorTime = now
    }
}
```

## 4. FR-3 V3：DoH负缓存清理接口（host级）

```kotlin
// DohDns.kt 新增公开方法（V3：host级清理+清dohDisabledUntil）

/**
 * 清理指定host的DoH负缓存（FR-3 V3调用）
 *
 * V3改进：
 * - host级清理（非全清），避免影响其他域名
 * - 同时清dohDisabledUntil（解决NEW-ERROR-4：熔断期间清理负缓存无效）
 *
 * 注：Cronet有自己的AsyncDNS（CronetHelper.kt L185 options.put("AsyncDNS", ...)），
 * 不经过DohDns。但OkHttp降级路径用DohDns。NAME_NOT_RESOLVED说明Cronet AsyncDNS失败，
 * 清理DohDns负缓存+熔断状态以便OkHttp降级路径通过DoH重试。
 */
fun clearNegativeCache(hostname: String) {
    val key = cacheKey(hostname)
    negativeCache.remove(key)
    // V3: 同时清dohDisabledUntil，允许下次lookup重试DoH
    // 原因：DohDns.kt L189熔断检查优先于L179负缓存检查，仅清负缓存在熔断期间无效
    dohDisabledUntil = 0L
    AppLog.putDebug("DohDns: negative cache cleared for host=${maskHost(hostname)}, dohDisabledUntil reset")
}
```

## 5. FR-5 V3：Cronet-OkHttp桥接层评估（仅方案A）

### 5.1 方案A：完全替换为CronetTransport

```kotlin
// HttpHelper.kt 评估点（V3：仅保留方案A，删除方案B）

// 现有配置（保持不变）：
val okHttpClient = OkHttpClient.Builder()
    .sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
    .hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
    // ... 其他配置 ...
    .build()

// FR-5 方案A（如实施）：完全替换为CronetTransport
// val okHttpClient = OkHttpClient.Builder()
//     .callFactory(CronetTransport.newFactory(cronetEngine))
//     .sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
//     .hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
//     .build()
```

### 5.2 V3删除方案B的理由

**NEW-ERROR-10**：方案B"仅降级时切换到CronetTransport"技术不可行。

OkHttp的`Call.Factory`是客户端级别配置（`OkHttpClient.Builder.callFactory`），在客户端构建时固定，**不能按请求切换**。要实现按请求切换需要自定义`Call.Factory`根据降级状态选择，复杂度极高且破坏OkHttp设计。

### 5.3 方案A影响清单（OkHttp core失效）

如实施方案A，以下OkHttp core能力将失效：
1. **缓存失效**：OkHttp Cache（HttpHelper.kt L85 50MB磁盘缓存）不生效
2. **重试失效**：retryOnConnectionFailure不生效
3. **认证失效**：Authenticator不生效
4. **网络拦截器失效**：addNetworkInterceptor注册的拦截器不生效（HttpHelper.kt L123-139 CookieJar网络拦截器）
5. **Response字段缺失**：handshake/networkResponse/cacheResponse/sentRequestAtMillis/receivedResponseAtMillis为null

### 5.4 评估结论

**推荐：不实施方案A**。原因：
1. OkHttp core失效影响范围大（缓存/重试/认证/CookieJar全部失效）
2. 现有CronetInterceptor已通过`cronetEngine.newUrlRequestBuilder`获得完整Cronet能力（BoringSSL TLS指纹+QUIC+连接迁移）
3. FR-1 V3改进后缓存命中走proceedWithCronet，已解决TLS指纹问题
4. FR-6 V3降级策略优化减少误降级，Cronet保持启用率提升

## 6. FR-6 V3：降级策略优化（移除cronetEngineHealthy+独立常量）

### 6.1 V3移除cronetEngineHealthy

**ERROR-1**：cronetEngineHealthy标志位存在鸡生蛋逻辑死锁。

design.md V2将`cronetEngineHealthy`初始值设为`false`，`intercept()`开头检查`if (!cronetEngineHealthy) return chain.proceed(...)`直接走OkHttp；而`markCronetEngineHealthy()`仅在Cronet请求成功后调用。启用FR-6后Cronet完全失效。

**V3修复**：移除`cronetEngineHealthy`标志位，依赖现有`engine == null`检查（CronetInterceptor.kt L116-125）。现有逻辑已处理"引擎不可用"场景，无需冗余标志位。

### 6.2 V3独立常量RECOVERY_PROBE_CHECK_INTERVAL_MS

**NEW-ERROR-5**：修改RECOVERY_PROBE_INTERVAL_MS影响4处降级时长。

`RECOVERY_PROBE_INTERVAL_MS`被以下位置使用：
- L96：正常降级间隔（currentIntervalMs计算）
- L239：恢复探测失败后降级时长（非HTTP/2）
- L261：达阈值降级时长（非震荡非HTTP/2）
- L277：非协议错误降级时长日志

**V3修复**：新增独立常量`RECOVERY_PROBE_CHECK_INTERVAL_MS = 3 * 60 * 1000L`，仅用于L88恢复探测触发检查。不修改`RECOVERY_PROBE_INTERVAL_MS`，保持其他4处降级时长不变。

### 6.3 V3重命名：降级计数豁免清单扩展

FR-6 V3实际是"降级计数豁免清单扩展"，非"动态阈值"：
- HTTP/2协议错误：保持5次（已有1分钟降级）
- 连接拒绝：不累计（已实施）
- NAME_NOT_RESOLVED：不累计（FR-3）
- 证书错误：不累计（FR-2）
- 其他协议错误：保持5次

## 7. FR-7 V3新增：图片加载根因分析

### 7.1 背景

用户反馈"列表图片加载能力下降"，V2文档主要聚焦视频嗅探和TLS指纹，图片加载根因分析不足。

### 7.2 图片加载接入Cronet的路径

```
Glide → OkHttpStreamFetcher → okHttpClientManga → okHttpClient.newBuilder()
    → CronetInterceptor（application interceptor）
    → proceedWithCronet（Cronet BoringSSL TLS指纹）
```

**源码证据**：
- HttpHelper.kt L169：`okHttpClientManga = okHttpClient.newBuilder()`
- HttpHelper.kt L144-148：okHttpClient注册CronetInterceptor
- okHttpClientManga通过newBuilder()继承CronetInterceptor

### 7.3 图片加载下降的可能根因

| # | 根因 | 源码位置 | 影响 | 修复方向 |
|---|------|---------|------|---------|
| P1 | ReadManga.rateLimiter限制速率 | HttpHelper.kt L181 | 图片加载被限速 | 评估rateLimiter阈值是否过严 |
| P2 | ProgressResponseBody包装开销 | HttpHelper.kt L176 | 每个响应包装增加开销 | 评估是否对图片请求跳过ProgressResponseBody |
| P3 | Glide磁盘缓存策略 | Glide配置 | 与OkHttp 50MB缓存冲突 | 评估Glide磁盘缓存配置 |
| P4 | 图片URL 302重定向未缓存 | FR-1应解决 | 重复302往返延迟 | FR-1 V3已解决 |
| P5 | 图片CDN TLS指纹 | FR-5应解决 | CDN拒绝Conscrypt TLS | FR-1 V3缓存命中走Cronet已解决 |
| P6 | Glide生命周期管理 | ImageCanvasAdapter | Activity销毁后回调泄漏 | 已修复（isGlideUsable()守卫） |

### 7.4 FR-7任务定义

**需求描述**：深度分析图片加载下降根因，评估是否需要优化Glide配置/rateLimiter/ProgressResponseBody。

**输入**：真机日志（图片加载失败/慢的日志）+ Glide配置源码

**输出**：根因分析报告 + 优化建议（实施/不实施/部分实施）

**验收标准**：
- [ ] 真机日志分析图片加载失败/慢的场景
- [ ] rateLimiter阈值评估完成
- [ ] ProgressResponseBody开销评估完成
- [ ] Glide磁盘缓存配置评估完成
- [ ] 给出明确优化建议

## 8. 测试策略（V3补充）

### 8.1 单元测试（V3新增）

- 302缓存命中/未命中/过期/LruCache淘汰
- 多层重定向缓存（A→B→C缓存A→C）
- 缓存键Referer维度（不同Referer不同缓存条目）
- 证书错误判定（前缀匹配ERR_CERT_+ERR_SSL_覆盖20+错误码）
- NAME_NOT_RESOLVED判定
- buildRedirectedRequest头处理（Keep-Alive/Accept-Encoding/Referer/Cookie）
- maskUrl脱敏函数

### 8.2 集成测试

- 真机测试：访问多层重定向站点，验证缓存命中走Cronet（非OkHttp）
- 真机测试：访问自签名证书站点，验证OkHttp降级（复用SSLHelper）
- 真机测试：模拟DoH失败场景，验证NAME_NOT_RESOLVED处理+host级清理
- 真机测试：对比修复前后Cronet降级频率

### 8.3 回归测试（V3新增，解决NEW-WARN-16）

- 现有9+个降级机制回归测试
- FR-1/2/3/6不影响现有protocolErrorCount/degradedForSession核心逻辑
- 缓存命中走proceedWithCronet不影响Cronet引擎生命周期
- 证书错误分支前置return不干扰协议错误降级逻辑

### 8.4 性能测试（V3新增，解决NEW-WARN-17）

- 302缓存查询延迟（≤1ms，LruCache内存查询）
- 首帧延迟对比（修复前后）
- Cronet降级频率对比（修复前后）
- 图片加载失败率对比（修复前后）

### 8.5 多层重定向测试（V3新增，解决NEW-WARN-13）

- 单层重定向（A→B）：缓存A→B映射
- 多层重定向（A→B→C）：缓存A→C映射（非A→B）
- 缓存命中后走Cronet验证（非OkHttp）
- 缓存过期后重新发起302请求

## 9. 风险与缓解（V3更新）

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| FR-1缓存命中走Cronet失败 | 中 | 回退chain.proceed走OkHttp（已实现try-catch） |
| 302缓存过期导致请求错误 | 低 | TTL 10分钟+仅缓存重定向响应 |
| 302缓存并发写入竞态 | 低 | synchronized(cache)线程安全 |
| 证书错误降级OkHttp仍失败 | 中 | 说明是TLS指纹问题，日志输出建议启用FR-5 |
| DoH负缓存host级清理影响其他域名 | 低 | host级精准清理（非全清） |
| FR-6恢复探测频率缩短导致震荡 | 低 | 已有震荡抑制（30s内再次降级延长到15分钟） |
| FR-1缓存命中走proceedWithCronet增加Cronet负载 | 低 | LruCache命中率提升后Cronet请求减少 |

## 10. 与现有代码的兼容性（V3更新）

### 10.1 不破坏现有降级机制

- FR-1/2/3/6在现有降级机制基础上新增，不修改现有protocolErrorCount/degradedForSession核心逻辑
- FR-6 V3不修改RECOVERY_PROBE_INTERVAL_MS（保持L96/L239/L261/L277不变）
- 证书错误和NAME_NOT_RESOLVED明确不累计降级计数，避免误降级
- FR-2 V3分支前置return避免干扰协议错误降级逻辑

### 10.2 复用现有SSLHelper

- FR-2直接复用SSLHelper.unsafeTrustManager + unsafeSSLSocketFactory + unsafeHostnameVerifier
- 不新增TrustManager，避免重复实现
- HttpHelper.kt的okHttpClient配置保持不变

### 10.3 不影响已实施的P0-fix和P1-2

- P0-fix（DohDns国内服务器+冷启动熔断+异步预热）：保持不变
- P1-2（HTTP/2 1分钟降级+连接拒绝不累计+震荡抑制）：保持不变
- FR-3 V3新增clearNegativeCache(hostname)方法，不修改现有lookup逻辑

### 10.4 不影响其他模块

- ExoPlayer：通过CronetDataSource接入，不经过CronetInterceptor
- Glide：通过okHttpClientManga间接接入，受CronetInterceptor影响，FR-1/2/3/6是优化不影响现有功能
- WebDav：通过okHttpClient接入，同上

## 11. V2 vs V3 方案对比

| 方面 | V2方案 | V3方案 | 修订理由 |
|------|--------|--------|---------|
| FR-1缓存命中路径 | chain.proceed走OkHttp | proceedWithCronet走Cronet | 保留TLS指纹（NEW-ERROR-9） |
| FR-1缓存命中头处理 | 跳过L128-143 builder逻辑 | 复用buildRedirectedRequest | 解决NEW-ERROR-2/12/13 |
| FR-1缓存策略 | 超限全清 | LruCache自动淘汰 | 解决NEW-ERROR-11 |
| FR-1缓存键 | 仅URL | URL+Referer维度 | 防盗链感知 |
| FR-1缓存容量/TTL | 200条/5分钟 | 500条/10分钟 | 与现有RedirectCacheInterceptor一致 |
| FR-2错误码匹配 | 4个具体错误码 | 前缀匹配ERR_CERT_+ERR_SSL_ | 覆盖20+错误码（NEW-WARN-5） |
| FR-2分支位置 | 未明确 | isProtocolError之前return | 避免误判（NEW-ERROR-6） |
| FR-2去重状态 | 共享lastLoggedError | 单独lastCertError | 解决NEW-ERROR-14 |
| FR-3清理范围 | 全清negativeCache | host级清理 | 精准清理 |
| FR-3熔断状态 | 不清dohDisabledUntil | 清dohDisabledUntil | 解决NEW-ERROR-4 |
| FR-5方案B | 保留 | 删除 | 不可行（NEW-ERROR-10） |
| FR-6 cronetEngineHealthy | 新增（初始false） | 移除 | 死锁（ERROR-1） |
| FR-6恢复探测频率 | 修改RECOVERY_PROBE_INTERVAL_MS | 新增独立常量 | 影响4处降级时长（NEW-ERROR-5） |
| FR-7图片加载 | 无 | 新增根因分析 | 解决MISS-1 |
| intercept()代码 | 伪代码 | 完整代码 | 覆盖分支交互（NEW-WARN-7） |
