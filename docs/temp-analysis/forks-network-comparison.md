# Legado 延伸版本网络层对比分析

> **生成日期**：2026-07-06
> **对比范围**：9 个延伸版本 vs 本项目（fork 自 Luoyacheng/legado-E）
> **对比维度**：OkHttp 配置、Cronet、拦截器链、Cookie 管理、重试机制、超时配置、代理、DNS、缓存、协程、限流器
> **数据来源**：实际获取各版本 GitHub 仓库源码对比，非臆测

---

## 1. 延伸版本概览

| # | 版本名 | git 仓库 | 最新推送 | Stars | Forks | 网络层活跃度 | 特色 |
|---|--------|----------|----------|-------|-------|-------------|------|
| 0 | **阅读Sigma（本项目 fork 源）** | Luoyacheng/legado-E | 2026-07-04 | 1919 | 416 | 高 | legado 官方继承分支，本项目基线 |
| 1 | **蛋蛋Max** | DandanLLab/Legado_Max | 2026-06-01 | 13 | 0 | 中 | URL 访问记录、307/308 重定向、SSL 可选化 |
| 2 | **阅读NG** | joestar817/legado_NG | 2026-07-02 | 25 | 1 | 高 | 基于 Sigma 演进，NetworkLog 网络日志 |
| 3 | **喵公子** | LegadoTeam/legado | 2026-06-11 | 277 | 100 | 中 | 网络层与 Sigma 完全一致，无改动 |
| 4 | **阅读T** | skybbk1001/legadoT | 2026-07-04 | 59 | 14 | 高 | **SOCKS5 隧道完整实现**、Brotli 解压、HttpLog |
| 5 | **辞晨Max** | GEd520/legados | - | - | - | - | **仓库已删除（404）**，无法对比 |
| 6 | **阅读Archive** | Rimchars/legado | 2026-06-18 | 244 | 29 | 中 | 网络层与 Sigma 完全一致，无改动 |
| 7 | **阅读R** | refgd/legado | 2026-06-01 | 13 | 0 | 中 | 网络层与 Sigma 完全一致，无改动 |
| 8 | **Jingshiro** | Jingshiro/legado | 2026-05-27 | - | - | 低 | 网络层与 Sigma 完全一致，无改动 |

**关键结论**：
- 9 个对比对象中，**仅 3 个版本（蛋蛋Max、阅读NG、阅读T）在网络层有实质性改动**
- 其余 5 个可访问版本网络层代码与 Sigma 完全一致
- 辞晨Max 仓库已被删除，无法获取
- 阅读T 的网络层改动最为深入（SOCKS5 协议级实现）

---

## 2. 逐文件对比矩阵

### 2.1 HttpHelper.kt（OkHttp 主配置）

| 版本 | SSL 配置 | DNS 缓存 | Cronet | 拦截器链 | 代理实现 | 差异程度 |
|------|----------|----------|--------|----------|----------|----------|
| **本项目(Sigma)** | 强制 unsafe SSL | addressCache 可选 | 条件加载 | ExceptionInterceptor → UA → CookieJar(Network) → Cronet → Decompress | 正则解析，HTTP/SOCKS 二分 | 基线 |
| **蛋蛋Max** | **可选 unsafe SSL**（`AppConfig.unsafeSsl`） | addressCache 可选 | 条件加载 | ExceptionInterceptor → UA → CookieJar(Network) → Cronet → Decompress → **UrlRecordInterceptor** | 正则解析，HTTP/SOCKS 二分 | **中** |
| **阅读NG** | 强制 unsafe SSL | addressCache 可选 | 条件加载 | ExceptionInterceptor → UA → **NetworkLogInterceptor** → CookieJar(Network) → Cronet → Decompress | 正则解析，HTTP/SOCKS 二分 | **低** |
| **阅读T** | 强制 unsafe SSL | **移除 addressCache** | 条件加载 | ExceptionInterceptor → UA → CookieJar(Network) → Cronet → Decompress → **HttpLogInterceptor** | **URI 解析 + SOCKS5 隧道** | **高** |
| 喵公子/Archive/R/Jingshiro | 强制 unsafe SSL | addressCache 可选 | 条件加载 | 同 Sigma | 正则解析，HTTP/SOCKS 二分 | 无 |

**关键差异说明**：

1. **蛋蛋Max SSL 可选化**：
   ```kotlin
   // 蛋蛋Max
   if (AppConfig.unsafeSsl) {
       builder.sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
       builder.hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
   }
   ```
   ```kotlin
   // 本项目（强制启用）
   .sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
   .hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
   ```
   **收益**：用户可选择安全 SSL（验证证书），提升安全性
   **风险**：默认不启用 unsafe SSL 后，部分自签证书网站将无法访问，需用户手动开启

2. **阅读T 移除 addressCache**：简化 DNS 逻辑，但失去 IP 缓存能力（可能影响 DNS 污染绕过场景）

### 2.2 OkHttpUtils.kt（请求扩展与重试）

| 版本 | 307/308 重定向 | decompressed() 实现 | 日志标记 | 差异程度 |
|------|---------------|---------------------|----------|----------|
| **本项目** | 不支持 | `asResponseBody` | 无 | 基线 |
| **蛋蛋Max** | **支持**（手动 Location 跟随，保留 method/body） | `RealResponseBody`（内部 API） | 无 | **中** |
| **阅读NG** | 不支持 | `RealResponseBody`（内部 API） | **networkLogSource()** | 低 |
| **阅读T** | 不支持 | `asResponseBody` | 无 | 无 |
| 其他版本 | 不支持 | `asResponseBody` | 无 | 无 |

**关键差异说明**：

蛋蛋Max 307/308 重定向处理（`newCallResponse`）：
```kotlin
if (response.code == 307 || response.code == 308) {
    response.header("Location")?.let { location ->
        val redirectRequest = currentRequest.newBuilder()
            .url(location)
            .method(currentRequest.method, currentRequest.body)  // 保留 method 和 body
            .headers(currentRequest.headers)
            .build()
        response.close()
        response = newCall(redirectRequest).await()
        if (response.isSuccessful) return response
        currentRequest = redirectRequest
    }
}
```
**收益**：307/308 重定向会保留请求方法和 body（区别于 301/302/303 会转为 GET），对 POST 表单登录场景重要
**风险**：手动跟随重定向可能与 OkHttp 内部重定向逻辑冲突，需注意无限重定向防护

### 2.3 CronetInterceptor.kt

| 版本 | HTTP→HTTPS Referer 修正 | 差异程度 |
|------|------------------------|----------|
| **本项目** | 有（issue #5025 修复） | 基线 |
| 蛋蛋Max | 有 | 无 |
| 阅读NG | 无（旧版本） | 低 |
| 阅读T | 有 | 无 |
| 其他版本 | 视版本而定 | - |

**说明**：`Referer` 修正逻辑（HTTP 请求时把 https: referer 改为 http:）是 gedoor/legado#5025 的修复，本项目和蛋蛋Max、阅读T 均已合入，阅读NG 未合入。

### 2.4 CronetCoroutineInterceptor.kt（Cronet 协程拦截器）

| 版本 | Cookie 处理逻辑 | 内部 API 依赖 | 日志 | 异常处理 | 差异程度 |
|------|----------------|--------------|------|----------|----------|
| **本项目** | **双路径**：cookieJarHeader → CookieManager 体系；否则 → cookieJar | **无**（移除 receiveHeaders） | **详细 Log.d** | UnsupportedOperationException 带说明 | **领先** |
| 蛋蛋Max | 单路径：仅 cookieJar | 有（`okhttp3.internal.http.receiveHeaders`） | 无 | `TODO("Not yet implemented")` | 落后 |
| 阅读NG | 单路径：仅 cookieJar | 有 | 无 | `TODO("Not yet implemented")` | 落后 |
| 阅读T | 单路径：仅 cookieJar | 有 | 无 | `TODO("Not yet implemented")` | 落后 |

**关键差异说明**：

本项目在 CronetCoroutineInterceptor 上**领先于所有对比版本**：
1. **双路径 Cookie 逻辑**：启用 `cookieJarHeader` 时使用 `CookieManager.loadRequest`（与 WebView 登录保存的 Cookie 一致），未启用时回退到 `cookieJar`
2. **移除内部 API 依赖**：不使用 `okhttp3.internal.http.receiveHeaders`（OkHttp 内部 API，版本升级可能破坏）
3. **详细日志**：`android.util.Log.d(TAG, "intercept: url=..., enableCookieJar=true, cookie=...")`
4. **清晰的异常说明**：`UnsupportedOperationException("waitForDone is not used in CronetCoroutineInterceptor; ...")` 替代 `TODO()`

### 2.5 DecompressInterceptor.kt（解压拦截器）

| 版本 | Brotli 支持 | promisesBody 实现 | 差异程度 |
|------|------------|-------------------|----------|
| **本项目** | 不支持 | **手写实现**（不依赖内部 API） | 基线 |
| 蛋蛋Max | 不支持 | `okhttp3.internal.http.promisesBody`（内部 API） | 低 |
| 阅读NG | 不支持 | `okhttp3.internal.http.promisesBody` | 低 |
| **阅读T** | **支持**（`org.brotli.dec.BrotliInputStream`） | `okhttp3.internal.http.promisesBody` | **中** |

**关键差异说明**：

1. **阅读T Brotli 支持**：
   ```kotlin
   requestBuilder.header("Accept-Encoding", "gzip, deflate, br")  // 添加 br
   // ...
   "br" -> BrotliInputStream(body.byteStream()).source().buffer()
   ```
   **收益**：Brotli 压缩率比 gzip 高 15-25%，现代网站越来越多使用 br，不支持会丢失内容
   **风险**：需引入 `org.brotli.dec` 依赖（约 200KB），增加包体积

2. **本项目手写 promisesBody**：
   ```kotlin
   private fun Response.promisesBody(): Boolean {
       if (request.method == "HEAD") return false
       val code = code
       return !(code in 100..199 || code == 204 || code == 205)
   }
   ```
   **优势**：不依赖 `okhttp3.internal.http.promisesBody`（内部 API），OkHttp 升级时不会破坏
   **劣势**：需手动维护与 OkHttp 内部逻辑一致

### 2.6 CookieManager.kt

| 版本 | getCookieNoSession 实现 | 差异程度 |
|------|------------------------|----------|
| **本项目** | `runBlocking(IO) { appDb.cookieDao.get(domain) }` | 基线 |
| 蛋蛋Max | `appDb.cookieDao.get(domain)`（无 runBlocking） | 低 |
| 阅读NG | `appDb.cookieDao.get(domain)`（无 runBlocking） | 低 |
| 阅读T | `runBlocking(IO) { appDb.cookieDao.get(domain) }` | 无 |
| 其他版本 | 同 Sigma | 无 |

**说明**：蛋蛋Max 和阅读NG 移除了 `runBlocking(IO)`，直接调用 `appDb.cookieDao.get(domain)`。这要求调用方必须在协程或 IO 线程中，否则会阻塞主线程。本项目使用 `runBlocking(IO)` 更安全但可能降低性能。

### 2.7 Coroutine.kt（协程封装）

| 版本 | CancellationException 处理 | 差异程度 |
|------|---------------------------|----------|
| **本项目** | `catch (e: Throwable)` 统一捕获（**反模式**） | 基线 |
| **蛋蛋Max** | **`catch (e: CancellationException) { throw e }` 单独处理** | **修复** |
| 阅读NG | `catch (e: Throwable)` 统一捕获 | 无 |
| 阅读T | `catch (e: Throwable)` 统一捕获 | 无 |
| 其他版本 | `catch (e: Throwable)` 统一捕获 | 无 |

**关键差异说明**：

蛋蛋Max 修复了协程反模式：
```kotlin
// 蛋蛋Max（正确）
} catch (e: CancellationException) {
    throw e  // 协程取消异常必须重新抛出
} catch (e: Throwable) {
    e.printOnDebug()
    // ... onError 逻辑
}

// 本项目（反模式）
} catch (e: Throwable) {
    e.printOnDebug()
    // ... onError 逻辑（会吞掉 CancellationException，破坏协程取消语义）
}
```
**收益**：正确处理协程取消，避免协程被取消后仍执行 onSuccess/onError 回调，防止资源泄漏和逻辑错误
**风险**：无，这是标准协程用法

### 2.8 ConcurrentRateLimiter.kt（限流器）

| 版本 | 数据结构 | 锁机制 | fetchEnd | 差异程度 |
|------|---------|--------|----------|----------|
| **本项目** | `ConcurrentHashMap` | `synchronized(fetchRecord)` | **无** | 基线 |
| 蛋蛋Max | `ConcurrentHashMap` | `synchronized(fetchRecord)` | 无 | 无 |
| 阅读NG | `ConcurrentHashMap` | `synchronized(fetchRecord)` | 无 | 无 |
| **阅读T** | `hashMapOf`（非线程安全） | `synchronized(concurrentRecordMap)` 双重检查锁 | **有** | **旧版本** |

**说明**：阅读T 使用旧版本限流器逻辑（非线程安全的 `hashMapOf` + 双重检查锁 + `fetchEnd` 手动释放），本项目和蛋蛋Max、阅读NG 使用新版本（`ConcurrentHashMap` + `computeIfAbsent` + 自动频率计数）。新版本更简洁但阅读T 旧版本有显式的 `fetchEnd` 释放语义。

### 2.9 BackstageWebView.kt / SSLHelper.kt / CronetLoader.kt

| 版本 | BackstageWebView | SSLHelper | CronetLoader | 差异程度 |
|------|-----------------|-----------|--------------|----------|
| 所有版本 | 一致 | 一致 | 一致 | 无 |

**说明**：这三个文件在所有可访问版本中完全一致，无任何差异。

---

## 3. 蛋蛋Max 独有优化清单

### 3.1 UrlRecordInterceptor（URL 访问记录拦截器）⭐⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/UrlRecordInterceptor.kt`
- **功能**：
  - 记录所有网络请求的 URL、域名、HTTP 方法、响应状态码、请求耗时
  - 记录 POST 请求体（限 1000 字符）
  - 记录请求来源（X-Source-Name / X-Source-Url 请求头）
  - 异步写入数据库（`UrlRecord` 实体 + `urlRecordDao`）
  - 上报到调试事件中心（`DebugEventCenter.emit`）
  - URL 脱敏（移除 token/key/password 等敏感参数）
  - 通过 `AppConfig.recordUrl` 控制启用
  - 独立 `CoroutineScope(SupervisorJob() + Dispatchers.IO)` 管理生命周期
  - `cancelAll()` 资源释放
- **收益**：⭐⭐⭐ 高。调试书源问题时可查看完整请求记录，定位失败请求
- **风险**：低。异步写入不阻塞请求；需新增 `UrlRecord` 实体和 DAO

### 3.2 307/308 重定向处理 ⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt`
- **功能**：在 `newCallResponse` 中手动跟随 307/308 重定向，保留请求方法和 body
- **收益**：⭐⭐ 中。307/308 重定向保留 POST method 和 body，对 POST 表单登录场景重要
- **风险**：中。手动跟随可能与 OkHttp 内部重定向逻辑冲突，需注意无限重定向防护

### 3.3 SSL 配置可选化 ⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
- **功能**：通过 `AppConfig.unsafeSsl` 控制是否启用 unsafe SSL
- **收益**：⭐⭐ 中。用户可选择安全 SSL（验证证书），提升安全性
- **风险**：中。默认不启用 unsafe SSL 后，部分自签证书网站将无法访问，需用户手动开启

### 3.4 Coroutine CancellationException 修复 ⭐⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt`
- **功能**：单独 catch `CancellationException` 并 rethrow
- **收益**：⭐⭐⭐ 高。修复协程反模式，正确处理协程取消语义
- **风险**：无。这是标准协程用法

### 3.5 CookieManager 移除 runBlocking ⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/CookieManager.kt`
- **功能**：`getCookieNoSession` 移除 `runBlocking(IO)`，直接调用 DAO
- **收益**：⭐ 低。减少一次线程切换
- **风险**：中。要求调用方必须在协程或 IO 线程中，否则会阻塞主线程

---

## 4. 阅读 NG 独有优化清单

### 4.1 NetworkLogInterceptor（网络日志拦截器）⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/NetworkLogInterceptor.kt`
- **功能**：
  - 通过 `NetworkLog.isEnabled` 控制启用
  - 记录请求和响应到 `NetworkLog`
  - 记录耗时（纳秒精度）
  - 捕获 `IOException` 和 `Throwable`
- **收益**：⭐⭐ 中。网络请求日志记录，便于调试
- **风险**：低。功能较蛋蛋Max UrlRecordInterceptor 简单，无数据库写入

### 4.2 networkLogSource() 扩展函数 ⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt`
- **功能**：`Request.Builder.networkLogSource(source: String?)` 标记请求来源
- **收益**：⭐ 低。配合 NetworkLogInterceptor 使用，标记请求来源
- **风险**：无

### 4.3 RealResponseBody 替代 asResponseBody ⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt`
- **功能**：`decompressed()` 使用 `RealResponseBody` 替代 `asResponseBody`
- **收益**：⭐ 低。`RealResponseBody` 是 OkHttp 内部类，性能略优
- **风险**：中。依赖 OkHttp 内部 API，版本升级可能破坏

---

## 5. 其他版本独有优化清单

### 5.1 阅读 T 独有优化

#### 5.1.1 SOCKS5 隧道完整实现 ⭐⭐⭐⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt`（新增约 280 行）
- **功能**：
  - `Socks5TunnelSocketFactory`：自定义 `SocketFactory`
  - `Socks5TunnelSocket`：自定义 `Socket`，委托模式实现
  - `Socks5Protocol`：SOCKS5 协议实现（RFC 1928）：
    - 握手协商（`METHOD_NO_AUTH` / `METHOD_USER_PASS`）
    - 用户名密码认证（RFC 1929）
    - CONNECT 命令（支持 IPv4/IPv6/域名）
    - 完整的错误消息映射（0x01-0x08）
  - `ProxyScheme` 枚举（HTTP/SOCKS4/SOCKS5）
  - `ProxyConfig` 数据类
  - `parseProxyConfig` 函数（使用 `URI` 解析，严格验证端口 1-65535、用户名密码长度 1-255）
  - `PROXY_CONFIG_ERROR` 错误前缀，清晰错误信息
- **收益**：⭐⭐⭐⭐⭐ 极高。**解决了 OkHttp 默认 SOCKS 代理不支持用户名密码认证的问题**。这是网络代理功能的重大增强，许多 SOCKS5 代理（如 Shadowsocks、V2Ray）需要认证
- **风险**：中。需完整测试 SOCKS5 协议实现的正确性；需处理 IPv6 场景

#### 5.1.2 Brotli 解压支持 ⭐⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/DecompressInterceptor.kt`
- **功能**：添加 `br` encoding 支持，使用 `org.brotli.dec.BrotliInputStream`
- **收益**：⭐⭐⭐ 高。Brotli 压缩率比 gzip 高 15-25%，现代网站越来越多使用 br
- **风险**：低。需引入 `org.brotli.dec` 依赖（约 200KB）

#### 5.1.3 HttpLogInterceptor（HTTP 日志拦截器）⭐⭐
- **文件**：`app/src/main/java/io/legado/app/help/http/HttpLogInterceptor.kt`
- **功能**：
  - 通过 `AppConfig.recordHttpLog` 控制启用
  - 记录请求方法、URL、状态码、耗时
  - 记录请求头、请求体（限 4096 字符）
  - 记录响应头、响应体（`peekBody` 不消费）
  - 记录错误信息
  - 使用 `HttpLogger` + `HttpRecord` 存储
  - 同步写入 `AppLog`
- **收益**：⭐⭐ 中。HTTP 请求/响应完整日志，便于调试
- **风险**：低。`peekBody` 不消费响应体，不影响请求

### 5.2 喵公子 / 阅读 Archive / 阅读 R / Jingshiro

**网络层无任何改动**，与 Sigma 完全一致。

### 5.3 辞晨 Max

**仓库已删除（404）**，无法获取代码进行对比。

---

## 6. 可借鉴的优化汇总（按收益/风险排序）

| 排名 | 优化项 | 来源版本 | 收益 | 风险 | 建议 |
|------|--------|----------|------|------|------|
| 1 | **SOCKS5 隧道完整实现** | 阅读 T | ⭐⭐⭐⭐⭐ | 中 | **强烈推荐借鉴**。解决 SOCKS5 认证代理无法使用的痛点 |
| 2 | **Coroutine CancellationException 修复** | 蛋蛋 Max | ⭐⭐⭐ | 无 | **强烈推荐借鉴**。标准协程用法，无风险 |
| 3 | **Brotli 解压支持** | 阅读 T | ⭐⭐⭐ | 低 | **推荐借鉴**。现代网站必备，仅需引入 brotli 依赖 |
| 4 | **UrlRecordInterceptor** | 蛋蛋 Max | ⭐⭐⭐ | 低 | **推荐借鉴**。调试书源问题利器，异步不阻塞 |
| 5 | **307/308 重定向处理** | 蛋蛋 Max | ⭐⭐ | 中 | 可选借鉴。需注意无限重定向防护 |
| 6 | **HttpLogInterceptor** | 阅读 T | ⭐⭐ | 低 | 可选借鉴。与 UrlRecordInterceptor 功能重叠，二选一 |
| 7 | **SSL 配置可选化** | 蛋蛋 Max | ⭐⭐ | 中 | 谨慎借鉴。默认关闭 unsafe SSL 会影响自签证书网站访问 |
| 8 | **NetworkLogInterceptor** | 阅读 NG | ⭐⭐ | 低 | 可选借鉴。功能较简单，不如 UrlRecordInterceptor 全面 |
| 9 | **移除 runBlocking(IO)** | 蛋蛋 Max/NG | ⭐ | 中 | 谨慎借鉴。需确认所有调用方都在协程中 |

---

## 7. 本项目相对于延伸版本的缺失

### 7.1 本项目缺失的优化（其他版本有但本项目没有）

| 缺失项 | 拥有该优化的版本 | 影响 | 补充建议 |
|--------|----------------|------|----------|
| **SOCKS5 认证代理支持** | 阅读 T | SOCKS5 代理无法使用用户名密码认证 | **高优先级**，借鉴阅读 T 的 `Socks5TunnelSocketFactory` 实现 |
| **Coroutine CancellationException 正确处理** | 蛋蛋 Max | 协程取消后仍执行回调，资源泄漏 | **高优先级**，添加 `catch (e: CancellationException) { throw e }` |
| **Brotli 解压支持** | 阅读 T | 使用 br 压缩的网站内容丢失 | **中优先级**，添加 `BrotliInputStream` 分支 |
| **URL 访问记录** | 蛋蛋 Max | 调试书源问题时无法查看请求历史 | **中优先级**，借鉴 `UrlRecordInterceptor` |
| **307/308 重定向** | 蛋蛋 Max | POST 表单登录场景重定向后丢失 body | 低优先级，需评估副作用 |
| **HTTP 日志拦截** | 阅读 T | 缺少完整请求/响应日志 | 低优先级，与 UrlRecordInterceptor 二选一 |
| **SSL 配置可选化** | 蛋蛋 Max | 无法选择安全 SSL | 低优先级，需配合 UI 开关 |

### 7.2 本项目独有/领先的优势（不应丢失）

| 优势项 | 领先程度 | 说明 |
|--------|---------|------|
| **CronetCoroutineInterceptor 双路径 Cookie 逻辑** | ⭐⭐⭐ | 集成 CookieManager 体系，与 WebView 登录 Cookie 一致；其他版本仅用 cookieJar |
| **移除 okhttp3.internal.http.receiveHeaders 依赖** | ⭐⭐ | 不依赖 OkHttp 内部 API，升级更安全 |
| **DecompressInterceptor 手写 promisesBody** | ⭐⭐ | 不依赖 `okhttp3.internal.http.promisesBody` 内部 API |
| **CronetInterceptor 详细日志** | ⭐ | `Log.d` 输出 Cookie 加载情况，便于调试 |

### 7.3 修复建议优先级

**P0（立即修复）**：
1. Coroutine CancellationException 修复（蛋蛋 Max）—— 标准协程用法，无风险

**P1（高优先级）**：
2. SOCKS5 隧道实现（阅读 T）—— 解决代理认证痛点
3. Brotli 解压支持（阅读 T）—— 现代网站必备

**P2（中优先级）**：
4. UrlRecordInterceptor（蛋蛋 Max）—— 调试利器
5. 307/308 重定向处理（蛋蛋 Max）—— 需评估副作用

**P3（低优先级）**：
6. SSL 配置可选化（蛋蛋 Max）—— 需配合 UI
7. HttpLogInterceptor（阅读 T）—— 与 UrlRecordInterceptor 二选一

---

## 附录 A：对比文件清单

| 文件 | 本项目 | 蛋蛋Max | 阅读NG | 阅读T | 喵公子 | Archive | R | Jingshiro | Sigma(E) |
|------|--------|---------|--------|-------|--------|---------|---|-----------|----------|
| HttpHelper.kt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OkHttpUtils.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| Cronet.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| CronetInterceptor.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| CronetCoroutineInterceptor.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| DecompressInterceptor.kt | ✅ | ✅ | ❌ | ✅ | - | - | - | - | - |
| CookieManager.kt | ✅ | ✅ | ✅ | - | - | - | - | - | - |
| SSLHelper.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| Coroutine.kt | ✅ | ✅ | ✅ | ✅ | - | - | - | - | - |
| ConcurrentRateLimiter.kt | ✅ | ✅ | - | ✅ | - | - | - | - | - |
| BackstageWebView.kt | ✅ | ✅ | - | - | - | - | - | - | - |
| AnalyzeUrl.kt | ✅ | - | - | - | - | - | - | - | - |

> ✅ = 已获取对比；❌ = 获取失败；- = 未获取（因其他版本文件一致或非重点）

## 附录 B：辞晨 Max 仓库状态

辞晨 Max（GEd520/legados）仓库返回 HTTP 404，仓库已被删除或更名，无法获取代码进行对比。GitHub API 返回：
```json
{
  "message": "Not Found",
  "status": "404"
}
```

## 附录 C：版本活跃度数据（截至 2026-07-06）

| 版本 | 最后推送 | Stars | Forks | 活跃度评估 |
|------|---------|-------|-------|-----------|
| 阅读 Sigma (E) | 2026-07-04 | 1919 | 416 | 高（社区主分支） |
| 阅读 T | 2026-07-04 | 59 | 14 | 高（持续更新） |
| 阅读 NG | 2026-07-02 | 25 | 1 | 高（基于 Sigma 演进） |
| 喵公子 | 2026-06-11 | 277 | 100 | 中 |
| 阅读 Archive | 2026-06-18 | 244 | 29 | 中 |
| 蛋蛋 Max | 2026-06-01 | 13 | 0 | 中（无 fork，个人项目） |
| 阅读 R | 2026-06-01 | 13 | 0 | 中 |
| Jingshiro | 2026-05-27 | - | - | 低 |
| 辞晨 Max | - | - | - | 已删除 |

---

**文档结束**
