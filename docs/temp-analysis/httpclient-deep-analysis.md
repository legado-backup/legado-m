# HttpClient 组件深度分析

> 分析对象：`app/src/main/java/io/legado/app/help/http/` 下 12 个核心文件
> 分析日期：2026-07-06
> 分析方法：源码逐行阅读 + 5 个延伸版本对比

---

## 一、HttpClient 组件全貌

### 1.1 架构关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OkHttp 客户端工厂                            │
│  HttpHelper.kt                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  okHttpClient    │  │ okHttpClientManga│  │ getProxyClient() │  │
│  │  (主单例)        │  │ (带进度+限流)    │  │ (代理缓存)       │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │ newBuilder()        │                     │             │
│           └─────────────────────┴─────────────────────┘             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ 拦截器链     │      │ Cookie 管理  │      │ SSL 管理     │
│              │      │              │      │              │
│ 应用拦截器:  │      │ CookieManager│      │ SSLHelper    │
│  - Exception │      │ CookieStore  │      │ (全信任)     │
│  - UA 注入   │      │ CookieJar(死)│      │              │
│  - Decompress│      │ 3级优先级    │      │              │
│  - Cronet    │      │ 双层模型     │      │              │
│ 网络拦截器:  │      │              │      │              │
│  - CookieJar │      │              │      │              │
└──────┬───────┘      └──────────────┘      └──────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  OkHttpUtils.kt (请求扩展)                                   │
│  - newCallResponse/newCallResponseBody/newCallStrResponse    │
│  - Call.await() (协程封装)                                   │
│  - ResponseBody.text() (编码检测)                            │
│  - Request.Builder 扩展 (get/postForm/postJson/postMultipart)│
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  兼容层                                                      │
│  - ObsoleteUrlFactory (HttpURLConnection → OkHttp 桥接)      │
│  - StrResponse (响应封装)                                    │
│  - RequestMethod (GET/POST/HEAD 枚举)                        │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 OkHttp 主配置全貌（HttpHelper.kt L51-127）

| 配置项 | 值 | 行号 | 评估 |
|--------|-----|------|------|
| connectTimeout | 15s | L59 | 合理 |
| writeTimeout | 15s | L60 | 合理 |
| readTimeout | 60s | L61 | 偏长但适配书源慢响应 |
| callTimeout | 60s | L62 | 与 readTimeout 相同，相当于无独立限制 |
| retryOnConnectionFailure | true | L65 | 合理 |
| followRedirects | true | L68-69 | 合理 |
| connectionSpecs | MODERN_TLS + COMPATIBLE_TLS + CLEARTEXT | L52-56 | 允许明文 HTTP，符合书源场景 |
| sslSocketFactory | unsafeSSLSocketFactory（全信任） | L64 | **安全风险** |
| hostnameVerifier | unsafeHostnameVerifier（全通过） | L66 | **安全风险** |
| cookieJar | 未启用（注释掉） | L63 | **死代码** |
| 连接池 | 默认（5 连接，5 分钟） | - | 未自定义 |
| Dispatcher 线程池 | 默认（最多 64 并发） | - | 仅改了 ThreadFactory |
| 缓存 | 未配置 | - | OkHttp HTTP 缓存未启用 |

### 1.3 拦截器链执行顺序

**应用拦截器（addInterceptor，按添加顺序执行）**：

| 顺序 | 拦截器 | 行号 | 职责 | 是否阻塞 |
|------|--------|------|------|----------|
| 1 | OkHttpExceptionInterceptor | L70 | Throwable → IOException 转换 | 否 |
| 2 | UA/Keep-Alive 注入拦截器 | L71-83 | 注入 UA、Keep-Alive、Cache-Control | 否 |
| 3 | Cronet 拦截器（条件） | L107-113 | Cronet 网络引擎 | 是（替代 OkHttp 网络） |
| 4 | DecompressInterceptor | L114 | gzip/deflate 透明解压 | 否 |

**网络拦截器（addNetworkInterceptor）**：

| 顺序 | 拦截器 | 行号 | 职责 |
|------|--------|------|------|
| 1 | CookieJar 网络拦截器 | L84-100 | 请求前注入 Cookie，响应后保存 Cookie |

> 注意：DecompressInterceptor 作为应用拦截器（L114 `addInterceptor`），不是网络拦截器。这意味着它**在** OkHttp 的 BridgeInterceptor 之前执行。OkHttp 的 BridgeInterceptor 会自动解压 gzip（如果它添加了 Accept-Encoding），但本拦截器自己添加 `Accept-Encoding: gzip, deflate`，可能与 OkHttp 自动行为产生冲突或重复解压。

### 1.4 Cookie 管理全貌

#### 三级优先级模型（CookieStore.kt + CookieManager.kt）

```
读取优先级（CookieManager.loadRequest → CookieStore.getCookie）:
┌─────────────────────────────────────────────────────┐
│ 1. 持久 Cookie (数据库 cookieDao)                    │  CookieStore.kt L76-92
│    └─ 缓存层: CacheManager 内存 "${domain}_cookie"   │  L135
│    └─ 持久层: appDb.cookieDao                        │  L140
│                                                      │
│ 2. 会话 Cookie (内存 "${domain}_session_cookie")     │  CookieManager.kt L83-85
│                                                      │
│ 3. 合并后超过 4096 字节 → 随机删除 key               │  CookieStore.kt L85-90 ⚠️
└─────────────────────────────────────────────────────┘

写入路径（CookieManager.saveResponse → saveCookiesFromHeaders）:
┌─────────────────────────────────────────────────────┐
│ Response → Cookie.parseAll → 拆分:                   │  CookieManager.kt L43-52
│   ├─ 非持久 (session) → "${domain}_session_cookie"   │  L47-48
│   └─ 持久 (persistent) → CookieStore.replaceCookie   │  L50-51
│        └─ CacheManager.putMemory + appDb.cookieDao   │  CookieStore.kt L36-38
└─────────────────────────────────────────────────────┘
```

#### 双层模型

| 层级 | 存储 | Key | 作用域 |
|------|------|-----|--------|
| 内存层 | CacheManager (LruCache) | `${domain}_cookie` / `${domain}_session_cookie` | 进程内 |
| 持久层 | Room (cookieDao) | domain | 跨进程重启 |
| WebView 层 | android.webkit.CookieManager | URL | WebView 内 |

### 1.5 SSL 策略全貌（SSLHelper.kt）

| 组件 | 实现 | 行号 | 风险 |
|------|------|------|------|
| unsafeTrustManager | checkServerTrusted 空实现 | L38-40 | 接受任意服务器证书 |
| unsafeSSLSocketFactory | SSLContext.getInstance("SSL") | L57 | **协议过时**，应使用 TLS |
| unsafeHostnameVerifier | 永远返回 true | L70 | 不校验主机名 |
| getSslSocketFactory（证书锁定） | TLS + 自定义 TrustManager | L119-145 | 正常实现，但项目中未使用 |

---

## 二、逐文件深度分析

### 2.1 HttpHelper.kt（191 行，OkHttp 主配置 + 代理缓存）

#### 完整实现逻辑

**模块结构**：
- `proxyClientCache`（L25-27）：顶层私有 `ConcurrentHashMap<String, OkHttpClient>`，缓存代理客户端
- `cookieJar`（L29-49）：顶层 `lazy` 属性，定义了 CookieJar 但**实际未启用**
- `okHttpClient`（L51-127）：顶层 `lazy` 属性，主客户端单例
- `okHttpClientManga`（L129-147）：顶层 `lazy` 属性，漫画客户端（带进度+限流）
- `getProxyClient(proxy)`（L152-191）：代理客户端工厂函数

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-01 | L29-49 + L63 | `cookieJar` 定义后未启用，`loadForRequest` 永远返回 `emptyList()`，`saveFromResponse` 写入的 `${domain}_cookieJar` key 全项目无读取方 | 死代码 |
| P-02 | L64-66 | 无条件启用 unsafe SSL，所有 HTTPS 请求都不校验证书 | 安全风险 |
| P-03 | L79-81 | 强制添加 `Connection: Keep-Alive` 头，对 HTTP/2 连接是非法头（HTTP/2 不允许此头） | 协议兼容 |
| P-04 | L80 | `Keep-Alive: 300` 是非标准头（标准是 `Keep-Alive: timeout=300`），多数服务器忽略 | 无效头 |
| P-05 | L114 | `DecompressInterceptor` 作为应用拦截器添加，在 Cronet 启用时会被 Cronet 短路（Cronet 拦截器在 L109 添加，先于 L114），导致 Cronet 路径下解压失效 | 设计选择 |
| P-06 | L25-27, L187 | `proxyClientCache` 永不清理，每个不同 proxy 字符串创建一个独立 OkHttpClient（含独立连接池、Dispatcher），恶意书源可通过大量不同 proxy 字符串导致 OOM | 内存泄漏 |
| P-07 | L159-161 | `r.findAll(proxy).first()` 当正则不匹配时抛 `NoSuchElementException`，未做 try-catch | 崩溃风险 |
| P-08 | L159 | 正则 `(http\|socks4\|socks5)://(.*):(\\d{2,5})(@.*@.*)?` 中 `(.*)` 贪婪匹配，对含 `@` 的密码会解析错误（如 `http://user:p@ss:1080@host:8080`） | 解析 Bug |
| P-09 | L101-106 | `AppConfig.addressCache` DNS 缓存无 TTL，IP 切换后无法感知，且自定义 DNS 只在 `addressCache.isNotEmpty()` 时启用，空时用系统 DNS | 设计选择 |
| P-10 | L115-126 | `executor.threadFactory` 在 `build()` 后修改，但 OkHttp 默认 Dispatcher 已用默认线程池创建了线程，threadFactory 替换对新线程生效但对已创建线程无效 | 时序问题 |
| P-11 | L131-145 | `okHttpClientManga` 通过 `interceptors.add(1, ...)` 修改拦截器列表。OkHttp `newBuilder()` 会拷贝 interceptors 列表（浅拷贝），所以不影响原 client，但若 `okHttpClientManga` 与 `okHttpClient` 共享同一连接池，连接复用正常 | 设计选择 |

#### 调用链
```
外部调用 okHttpClient → lazy 初始化 → 构建 Builder → 添加拦截器 → build()
                                                                            │
                                                              dispatcher.executorService
                                                              threadFactory 替换
```

### 2.2 OkHttpUtils.kt（198 行，请求扩展）

#### 完整实现逻辑

**核心扩展函数**：
- `newCallResponse(retry, builder)`（L29-43）：协程化请求 + 重试
- `newCallResponseBody`（L45-50）：直接返回 body
- `newCallStrResponse`（L52-59）：返回 StrResponse（含字符串 body）
- `Call.await()`（L61-77）：Call → 协程挂起，支持取消
- `ResponseBody.text(encode)`（L79-95）：智能编码检测（参数 → HTTP 头 → 内容嗅探）
- `ResponseBody.decompressed()`（L97-111）：zip 解压
- `Request.Builder` 扩展（L113-197）：get/postForm/postJson/postMultipart

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-12 | L36-42 | `newCallResponse` 重试循环中，`response.isSuccessful` 为 false 时**未调用 `response.close()`**，连接泄漏；最后一次失败返回的 response 由调用方关闭，但中间重试的 response 全部泄漏 | 资源泄漏 |
| P-13 | L57 | `it.body.text()` 中 `it.body` 可能为 null（204/205 响应或 HEAD 请求），`text()` 会 NPE | 空指针 |
| P-14 | L42 | `return response!!` 当 retry 为负数时（虽然默认 0），for 循环不执行，`response!!` 抛 NPE | 边界 Bug |
| P-15 | L79-95 | `text()` 调用 `bytes()` 一次性读全部到内存，大文件（如 epub）会 OOM | 内存风险 |
| L-01 | L88-89 | `contentType()?.charset()` 若 contentType 为 null 不报错（安全），逻辑正确 | - |
| L-02 | L93 | `EncodingDetect.getHtmlEncode` 内容嗅探基于 HTML meta 标签，对非 HTML 响应（如 JSON API）可能误判 | 设计选择 |
| P-16 | L102-110 | `decompressed()` 使用 `ZipInputStream`，但 `application/zip` MIME 类型检查过严，部分服务器用 `application/x-zip-compressed` 不会触发解压 | 兼容性 |

### 2.3 CookieManager.kt（172 行，Cookie 管理核心）

#### 完整实现逻辑

**核心方法**：
- `saveResponse(response: Response)`（L31-35）：从 OkHttp Response 提取 Cookie
- `saveResponse(response: Connection.Response)`（L37-41）：从 jsoup Response 提取 Cookie
- `saveCookiesFromHeaders(url, headers)`（L43-52）：统一保存逻辑，拆分会话/持久 Cookie
- `loadRequest(request)`（L57-77）：合并请求头 Cookie 与存储 Cookie
- `mergeCookies(vararg cookies)`（L98-101）：合并多个 Cookie 字符串
- `mergeCookiesToMap(vararg cookies)`（L103-109）：合并为 Map
- `removeCookie(url, key)`（L114-131）：删除单个 Cookie key
- `getCookieNoSession(url)`（L133-143）：仅获取持久 Cookie（含内存缓存层）
- `applyToWebView(url)`（L145-153）：同步 Cookie 到 WebView

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-17 | L140 | `runBlocking(IO) { appDb.cookieDao.get(domain) }` 在 `getCookieNoSession` 中同步阻塞，调用方可能是主线程（如 `loadRequest` 在网络拦截器中调用，但拦截器在 OkHttp Dispatcher 线程；然而 `getCookieNoSession` 也被 `removeCookie` L124、`replaceCookie` 调用，调用路径复杂），存在 ANR 风险 | ANR 风险 |
| P-18 | L103-109 | `mergeCookiesToMap` 使用 `reduce`，当 `cookies` 全为 null 时 `filterNotNull` 返回空列表，`reduce` 抛 `NoSuchElementException`（实际有 `filterNotNull` 但若结果为空会崩） | 崩溃风险 |
| P-19 | L66-77 | `loadRequest` 中 `kotlin.runCatching` 捕获异常后调用 `CookieStore.removeCookie(url)`，但 `url` 是完整 URL 而 `removeCookie` 期望完整 URL（L101-107），行为正确但会清除整个 domain 的所有 Cookie，过度清理 | 设计问题 |
| P-20 | L47-48 | `cookies.filter { !it.persistent }.getString()` 将非持久 Cookie 全部存入 `${domain}_session_cookie`，但未处理 `expires` / `max-age` 已过期的 Cookie（OkHttp Cookie.parseAll 不检查过期） | 过期 Cookie |
| L-03 | L155-160 | `getString()` 使用 `"; "` 分隔（带空格），但 `cookieToMap` 用 `semicolonRegex` 分隔且 `trim`，兼容 | - |
| P-21 | L98-101 | `mergeCookies` 返回 `CookieStore.mapToCookie(cookieMap)`，但若 cookieMap 为空返回 null，调用方 `loadRequest` L64 `?: return request` 处理了，正常 | - |

### 2.4 CookieStore.kt（145 行，Cookie 持久化）

#### 完整实现逻辑

**实现 `CookieManagerInterface` 接口**：
- `setCookie(url, cookie)`（L26-42）：保存到内存 + 数据库
- `setWebCookie(url, cookie)`（L44-56）：同步到 WebView
- `replaceCookie(url, cookie)`（L58-71）：合并旧 Cookie
- `getCookie(url)`（L76-92）：获取并合并持久 + 会话 Cookie
- `getKey(url, key)`（L94-99）：获取单个 key
- `removeCookie(url)`（L101-107）：删除整个 domain
- `cookieToMap(cookie)`（L109-127）：字符串 → Map
- `mapToCookie(cookieMap)`（L129-139）：Map → 字符串

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-22 | L85-90 | `cookieMap.keys.random()` 在 cookie 超过 4096 字节时**随机删除 key**，会删除关键登录态 Cookie（如 session_id），导致用户被强制登出。应该按 LRU 或 least-used 策略删除 | 严重 Bug |
| P-23 | L85-90 | `while (ck.length > 4096)` 循环中调用 `CookieManager.removeCookie(url, removeKey)`，每次都重新写数据库，性能差 | 性能 |
| P-24 | L86 | `cookieMap.keys.random()` 在 `ConcurrentHashMap` 之外的普通 `MutableMap` 上调用，但 `cookieToMap` 返回 `mutableMapOf`（非线程安全），多线程并发访问可能 `ConcurrentModificationException` | 并发风险 |
| P-25 | L33-35 | `setCookie` 添加了空值保护（注释说明是修复 onPageFinished 返回 null 覆盖问题），保护逻辑正确 | 已修复 |
| L-04 | L114 | `cookie.split(semicolonRegex).dropLastWhile { it.isEmpty() }.toTypedArray()` 中 `dropLastWhile` 处理末尾空字符串，但 `semicolonRegex` 定义未在此文件，依赖 AppPattern | - |
| P-26 | L141-143 | `clear()` 只调用 `appDb.cookieDao.deleteOkHttp()`，未清理 `CacheManager` 内存中的 Cookie，导致内存残留 | 不完整清理 |

### 2.5 SSLHelper.kt（194 行，SSL 信任管理）

#### 完整实现逻辑

**核心组件**：
- `unsafeTrustManager`（L27-49）：全信任 TrustManager，所有证书通过
- `unsafeTrustManagerExtensions`（L51-53）：X509TrustManagerExtensions 包装
- `unsafeSSLSocketFactory`（L55-63）：基于 `SSLContext.getInstance("SSL")` 的 SSLSocketFactory
- `unsafeHostnameVerifier`（L70）：永远返回 true
- `getSslSocketFactory(...)` 重载（L81-117）：支持单向/双向认证，但项目实际未使用
- `getSslSocketFactoryBase`（L119-145）：内部实现

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-27 | L57 | `SSLContext.getInstance("SSL")` 使用已过时的 "SSL" 协议（SSLv3 已不安全），应使用 "TLS" 或 "TLSv1.2" | 过时协议 |
| P-28 | L38-40 | `checkServerTrusted` 空实现，接受任意证书，MITM 风险 | 安全漏洞 |
| P-29 | L46-48 | `getAcceptedIssuers` 返回空数组，部分客户端库会拒绝连接 | 兼容性 |
| P-30 | L42-44 | 自定义 `checkServerTrusted(chain, authType, host)` 永远返回 `chain.toList()`，不做任何校验 | 安全漏洞 |
| P-31 | L131 | `getSslSocketFactoryBase` 使用 "TLS"（正确），但与 `unsafeSSLSocketFactory` 的 "SSL" 不一致，设计混乱 | 一致性 |

### 2.6 DecompressInterceptor.kt（56 行，解压拦截器）

#### 完整实现逻辑

**拦截逻辑**：
1. 检查请求是否已有 `Accept-Encoding` 或 `Range` 头（L19）
2. 若无，设置 `transparentDecompress = true` 并添加 `Accept-Encoding: gzip, deflate`（L20-22）
3. 执行请求（L24）
4. 若非透明解压 / 无 body / body 为空，直接返回（L27-29）
5. 根据 `Content-Encoding` 头解压：gzip → GZIPInputStream，deflate → InflaterInputStream（L31-36）
6. 移除 `Content-Encoding` 和 `Content-Length` 头，返回新 body（L38-42）

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-32 | L19 | 作为应用拦截器，与 OkHttp 内置 BridgeInterceptor 的自动 gzip 处理可能冲突。OkHttp BridgeInterceptor 在请求头无 Accept-Encoding 时会自动添加 `gzip` 并解压，本拦截器重复处理 | 重复解压风险 |
| P-33 | L34 | `Inflater(true)` 表示 `nowrap=true`，仅适用于 raw deflate（无 zlib 头），部分服务器返回 zlib 包装的 deflate 会解压失败 | 兼容性 |
| P-34 | L33 | `GZIPInputStream(body.byteStream())` 未显式关闭，依赖 ResponseBody 的 close，但若解压过程中抛异常，GZIPInputStream 不会关闭，资源泄漏 | 资源泄漏 |
| P-35 | L51-55 | `promisesBody()` 自定义实现替代 `okhttp3.internal.http.promisesBody`（内部 API），逻辑等价，但若 OkHttp 升级可能不同步 | 维护风险 |
| L-05 | L19 | 同时检查 `Range` 头，避免 Range 请求被解压（正确，因 Range 请求是分片） | - |

### 2.7 OkHttpExceptionInterceptor.kt（19 行，异常转换）

#### 完整实现逻辑

简单拦截器：捕获 `chain.proceed()` 抛出的非 IOException Throwable，包装为 IOException 重新抛出（L10-18）。

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-36 | L11-17 | 把所有 RuntimeException 和 Error 包装成 IOException，丢失异常类型信息，上层无法区分网络错误与代码 Bug（如 NPE） | 异常吞没 |
| P-37 | L13-14 | IOException 直接 rethrow，其他 Throwable 包装，但 `kotlinx.coroutines` 的 `CancellationException` 是 RuntimeException，会被包装为 IOException，破坏协程取消语义 | 协程 Bug |

### 2.8 OkhttpUncaughtExceptionHandler.kt（10 行，未捕获异常处理器）

#### 完整实现逻辑

实现 `Thread.UncaughtExceptionHandler`，将异常写入 `AppLog.put`（L7-9）。

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| L-06 | L8 | 仅记录日志，不终止线程，OkHttp Dispatcher 线程继续运行（这是合理的，避免单次异常杀死线程池） | 设计选择 |
| P-38 | L8 | `e.localizedMessage` 可能为 null，`AppLog.put` 内部需处理（实际 `put(msg, e)` 会拼接，但 msg 中含 null 字符串） | 轻微 |

### 2.9 ObsoleteUrlFactory.kt（1201 行，HttpURLConnection 兼容）

#### 完整实现逻辑

**核心职责**：将 OkHttp 包装为 `HttpURLConnection` API，供旧代码（如 jsoup）使用。

**模块结构**：
- `ObsoleteUrlFactory(client)`（L71-131）：工厂类，实现 `URLStreamHandlerFactory`
- `OkHttpURLConnection`（L132-576）：HttpURLConnection 实现，内部用 OkHttp Call
- `OutputStreamRequestBody`（L578-646）：请求体抽象基类
- `BufferedRequestBody`（L648-676）：缓冲请求体
- `StreamedRequestBody`（L678-697）：流式请求体
- `DelegatingHttpsURLConnection`（L699-961）：HttpsURLConnection 委托
- `OkHttpsURLConnection`（L963-997）：HTTPS 实现
- `UnexpectedException`（L999-1011）：Error/RuntimeException 包装
- `companion object`（L1013-1200）：工具方法

#### 关键逻辑

- `buildCall()`（L322-407）：构建 OkHttp Call，**清空原 client 的所有拦截器**（L376-377, L379-380），添加 `UnexpectedException.INTERCEPTOR` 和 `NetworkInterceptor`
- `NetworkInterceptor`（L535-575）：内部拦截器，用 `lock.wait()` 阻塞等待 `proceed()` 调用
- `getResponse(networkResponseOnError)`（L409-446）：用 `synchronized(lock)` + `lock.wait()` 同步等待异步结果

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-39 | L988-991 | `setSSLSocketFactory(sslSocketFactory)` 强制使用 `unsafeTrustManager`，即使调用方传入自定义 sslSocketFactory，证书验证仍全信任 → 安全漏洞 | 安全漏洞 |
| P-40 | L376-380 | `clientBuilder.interceptors().clear()` + `networkInterceptors().clear()` 清空原 client 的所有拦截器，导致 UA 注入、Decompress、Exception 拦截器全部失效 | 功能丢失 |
| P-41 | L161-173 | `connect()` 用 `lock.wait()` 无超时等待，若 `networkInterceptor.proceed()` 未被调用，永久阻塞 → 线程泄漏 | 死锁风险 |
| P-42 | L424-432 | `getResponse` 中 `lock.wait()` 无超时，网络异常时可能永久阻塞 | 死锁风险 |
| P-43 | L999-1011 | `UnexpectedException.INTERCEPTOR` 把 Error 和 RuntimeException 包装为 IOException（UnexpectedException），与 `OkHttpExceptionInterceptor` 重复包装 | 重复包装 |
| P-44 | L1176-1182 | `Any.wait()/notify()/notifyAll()` 通过 `(this as Object).wait()` 反射调用，绕过 Kotlin 平台限制，但可读性差 | 可维护性 |
| P-45 | L400 | `clientBuilder.dispatcher(Dispatcher(client.dispatcher.executorService))` 共享原 client 的 executorService，但创建新 Dispatcher，限制隔离但线程池共享，可能导致限流互相影响 | 设计选择 |
| L-07 | L381-397 | ObsoleteUrlFactory 自己实现了 CookieJar 网络拦截器（与 HttpHelper 重复），但未包含 UA 注入，行为不一致 | 一致性 |

### 2.10 StrResponse.kt（89 行，响应封装）

#### 完整实现逻辑

**数据类封装**：包装 OkHttp `Response` + 字符串 body + 错误 body + 调用次数。

**三个构造函数**：
1. `(rawResponse, body)`（L25-28）：正常响应
2. `(url, body)`（L30-43）：伪造响应（用于本地数据）
3. `(rawResponse, errorBody)`（L45-48）：错误响应

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| L-08 | L30-43 | 第二构造函数伪造 200 OK 响应，用于本地数据伪装为 HTTP 响应，设计合理 | - |
| P-46 | L31-35 | `Request.Builder().url(url).build()` 失败时 fallback 到 `http://localhost/`，可能掩盖 URL 解析错误 | 错误掩盖 |
| P-47 | L17-22 | `raw`、`body`、`errorBody` 均为 `var`（可变），但 setter 是 private，仍可能通过反射修改，不一致 | 设计选择 |

### 2.11 RequestMethod.kt（5 行，方法枚举）

#### 完整实现逻辑

简单枚举：`GET, POST, HEAD`（L3-5）。

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| P-48 | L3 | 枚举不全，缺少 `PUT`、`DELETE`、`OPTIONS`、`PATCH`，但 `ObsoleteUrlFactory.METHODS` 包含全部 8 种方法，不一致 | 一致性 |

### 2.12 CookieManagerInterface.kt（28 行，Cookie 接口）

#### 完整实现逻辑

定义 6 个方法：`setCookie`、`replaceCookie`、`getCookie`、`removeCookie`、`cookieToMap`、`mapToCookie`。

#### 问题识别

| 编号 | 行号 | 问题 | 类型 |
|------|------|------|------|
| L-09 | - | 接口定义清晰，`CookieStore` 实现完整 | - |

---

## 三、延伸版本对比

### 3.1 获取情况

| 版本 | 仓库 | HttpHelper.kt | OkHttpUtils.kt | 状态 |
|------|------|---------------|----------------|------|
| 蛋蛋Max | DandanLLab/Legado_Max | ✅ | ✅ | 完整对比 |
| 阅读NG | joestar817/legado_NG | ✅ | - | 部分对比 |
| 喵公子 | LegadoTeam/legado | ❌ | - | 获取失败 |
| 阅读T | skybbk1001/legadoT | ❌ | - | 获取失败 |
| 辞晨Max | GEd520/legados | ❌ | - | 获取失败 |
| 阅读Archive | Rimchars/legado | ✅ | - | 与本项目完全一致 |
| 阅读R | refgd/legado | ✅ | - | 与本项目完全一致 |
| Jingshiro | Jingshiro/legado | ✅ | - | 与本项目完全一致 |

### 3.2 HttpHelper.kt 差异对比

| 对比项 | 本项目 | 蛋蛋Max | 阅读NG | 阅读 Archive/R/Jingshiro |
|--------|--------|---------|--------|------|
| **SSL 启用策略** | 无条件启用 unsafe SSL（L64-66） | 条件启用：`if (AppConfig.unsafeSsl)`（L73-75） | 无条件启用（同本项目） | 同本项目 |
| **额外拦截器** | 无 | `UrlRecordInterceptor`（L77） | `NetworkLogInterceptor`（L72） | 无 |
| **拦截器顺序** | Exception → UA → Cronet → Decompress | Exception → UA → Cronet → Decompress → UrlRecord | Exception → UA → NetworkLog → Cronet → Decompress | 同本项目 |
| **OkHttpUtils 重试** | 简单重试（L36-42） | 支持 307/308 重定向手动处理（L17-32） | - | 同本项目 |
| **OkHttpUtils zip 解压** | `asResponseBody(null, -1)`（L110） | `RealResponseBody(null, -1, source)`（L39） | - | 同本项目 |

### 3.3 关键差异详解

#### 差异 1：SSL 条件启用（蛋蛋Max 独有）

**蛋蛋Max 实现**（HttpHelper.kt L73-75）：
```kotlin
if (AppConfig.unsafeSsl) {
    builder.sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
    builder.hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
}
```

**本项目**（HttpHelper.kt L64-66）：无条件启用。

**评估**：蛋蛋Max 的条件启用更安全，用户可按需开启 unsafe SSL。本项目无条件启用存在 MITM 风险，但对于书源场景（大量自签名证书站点）是务实选择。**建议借鉴**：默认开启，但提供关闭选项。

#### 差异 2：UrlRecordInterceptor（蛋蛋Max 独有）

**蛋蛋Max 实现**（HttpHelper.kt L77）：`builder.addInterceptor(UrlRecordInterceptor)`，记录请求 URL 用于书源调试。

**评估**：调试友好，但本项目的 `OkhttpUncaughtExceptionHandler` 已记录异常，且书源调试有独立工具。**可选借鉴**。

#### 差异 3：NetworkLogInterceptor（阅读NG 独有）

**阅读NG 实现**（HttpHelper.kt L72）：`addInterceptor(NetworkLogInterceptor)`，记录网络请求日志。

**评估**：与本项目 `OkhttpUncaughtExceptionHandler` 互补，但生产环境会泄漏隐私。**不建议借鉴**。

#### 差异 4：307/308 重定向手动处理（蛋蛋Max OkHttpUtils 独有）

**蛋蛋Max 实现**（OkHttpUtils.kt L17-32）：
```kotlin
if (response.code == 307 || response.code == 308) {
    response.header("Location")?.let { location ->
        val redirectRequest = currentRequest.newBuilder()
            .url(location)
            .method(currentRequest.method, currentRequest.body)
            .headers(currentRequest.headers)
            .build()
        response.close()  // 正确关闭
        response = newCall(redirectRequest).await()
        // ...
    }
}
```

**本项目**：依赖 OkHttp 默认重定向（`followRedirects(true)`），但 OkHttp 默认不跟随 307/308（仅跟随 301/302/303）。**本项目对 307/308 重定向处理缺失**。

**评估**：**强烈建议借鉴**。307/308 是 RFC 7538 标准，部分现代 API 使用，且蛋蛋Max 的实现正确关闭了旧 response（本项目 P-12 问题）。

#### 差异 5：RealResponseBody 替代 asResponseBody（蛋蛋Max OkHttpUtils）

**蛋蛋Max**（OkHttpUtils.kt L39）：`RealResponseBody(null, -1, source)`
**本项目**（OkHttpUtils.kt L110）：`source.asResponseBody(null, -1)`

**评估**：`RealResponseBody` 是 OkHttp 内部 API（`okhttp3.internal.http.RealResponseBody`），`asResponseBody` 是公开扩展函数。本项目使用公开 API 更稳定。**不建议借鉴**。

---

## 四、性能问题清单

| 编号 | 文件:行号 | 问题描述 | 严重程度 | 修复建议 |
|------|-----------|----------|----------|----------|
| PERF-01 | HttpHelper.kt:L25-27,L187 | `proxyClientCache` 永不清理，每个不同 proxy 创建独立 OkHttpClient（含独立连接池、Dispatcher），可被恶意书源利用导致 OOM | 高 | 添加 LRU 上限（如最多 10 个），超出时淘汰最旧的；或用 `WeakReference` |
| PERF-02 | CookieStore.kt:L85-90 | cookie 超 4096 时 `while` 循环每次调用 `removeCookie` 写数据库，性能差 | 中 | 改为先在内存中删除到 4096 以下，最后一次写数据库 |
| PERF-03 | CookieManager.kt:L140 | `runBlocking(IO) { appDb.cookieDao.get(domain) }` 同步阻塞查数据库，主线程调用会 ANR | 高 | 改为 `withContext(IO)` 挂起函数，或预加载到内存缓存 |
| PERF-04 | OkHttpUtils.kt:L36-42 | 重试循环中失败 response 未 close，连接泄漏 | 高 | 在 `if (!response.isSuccessful) response.close()` 后再重试 |
| PERF-05 | DecompressInterceptor.kt:L33 | `GZIPInputStream` 异常时未关闭，资源泄漏 | 中 | 用 `use { }` 包裹 |
| PERF-06 | HttpHelper.kt:L79-81 | 强制添加 `Connection: Keep-Alive` + `Cache-Control: no-cache`，对 HTTP/2 是非法头，且 no-cache 强制每次校验，降低缓存命中率 | 中 | HTTP/2 不添加 Connection 头；Cache-Control 改为 `max-age=0` |
| PERF-07 | ObsoleteUrlFactory.kt:L161-173,L424-432 | `lock.wait()` 无超时，异常时永久阻塞，线程泄漏 | 高 | 添加超时：`lock.wait(timeoutMillis)` |
| PERF-08 | HttpHelper.kt:L114 | DecompressInterceptor 作为应用拦截器，在 Cronet 启用时被短路，解压失效 | 中 | 改为网络拦截器，或放在 Cronet 拦截器之前 |
| PERF-09 | OkHttpUtils.kt:L79-95 | `text()` 用 `bytes()` 一次性读全部到内存，大文件 OOM | 中 | 添加 size 检查，超阈值用流式处理或抛异常 |
| PERF-10 | HttpHelper.kt:L115-126 | `executor.threadFactory` 在 `build()` 后修改，已创建线程不受影响 | 低 | 在 `build()` 前设置，或自定义 Dispatcher |

---

## 五、稳定性问题清单

| 编号 | 文件:行号 | 问题描述 | 严重程度 | 修复建议 |
|------|-----------|----------|----------|----------|
| STAB-01 | CookieStore.kt:L85-90 | cookie 超 4096 时 `cookieMap.keys.random()` 随机删除 key，可能删除登录态 Cookie 导致用户被强制登出 | 严重 | 按 LRU 或 last-access 时间删除；或按 key 长度优先删除长 key |
| STAB-02 | HttpHelper.kt:L159-161 | `r.findAll(proxy).first()` 正则不匹配时抛 `NoSuchElementException`，未捕获 | 高 | 用 `firstOrNull()` + 空检查 |
| STAB-03 | HttpHelper.kt:L159 | 正则 `(.*)` 贪婪匹配，含 `@` 的密码解析错误 | 高 | 改为非贪婪 `(.+?)` 或用更精确的正则 |
| STAB-04 | OkHttpUtils.kt:L57 | `it.body.text()` 中 `it.body` 可能为 null（204/HEAD），NPE | 高 | `it.body?.text() ?: ""` |
| STAB-05 | OkHttpUtils.kt:L42 | retry 为负数时 `response!!` 抛 NPE | 中 | `return response ?: throw IOException("...")` |
| STAB-06 | CookieManager.kt:L103-109 | `mergeCookiesToMap` 中 `reduce` 在空列表时抛 `NoSuchElementException` | 高 | 改为 `fold(mutableMapOf()) { acc, map -> ... }` |
| STAB-07 | OkHttpExceptionInterceptor.kt:L13-17 | `CancellationException`（RuntimeException 子类）被包装为 IOException，破坏协程取消语义 | 严重 | 显式 `if (e is CancellationException) throw e` |
| STAB-08 | ObsoleteUrlFactory.kt:L988-991 | `setSSLSocketFactory` 强制用 `unsafeTrustManager`，自定义证书失效 | 严重 | 从传入的 sslSocketFactory 提取 TrustManager，或抛异常禁止调用 |
| STAB-09 | ObsoleteUrlFactory.kt:L376-380 | `interceptors().clear()` 清空原 client 拦截器，UA/Decompress/Exception 全失效 | 高 | 不清空，仅追加 UnexpectedException.INTERCEPTOR |
| STAB-10 | CookieStore.kt:L114-127 | `cookieToMap` 返回非线程安全 `mutableMapOf`，多线程并发 `ConcurrentModificationException` | 中 | 改为 `ConcurrentHashMap` 或 `Collections.synchronizedMap` |
| STAB-11 | CookieStore.kt:L141-143 | `clear()` 只清数据库，不清 `CacheManager` 内存，残留 Cookie | 中 | 同时调用 `CacheManager.deleteMemory` 清理所有 `${domain}_cookie` 和 `${domain}_session_cookie` |
| STAB-12 | SSLHelper.kt:L57 | `SSLContext.getInstance("SSL")` 使用过时协议 | 中 | 改为 `"TLS"` 或 `"TLSv1.2"` |
| STAB-13 | HttpHelper.kt:L29-49 | `cookieJar` 定义后未启用（L63 注释），`saveFromResponse` 写入的 `${domain}_cookieJar` 无读取方，死代码 | 低 | 删除 `cookieJar` 定义，或启用并移除网络拦截器中的手动 Cookie 处理 |
| STAB-14 | ObsoleteUrlFactory.kt:L161-173 | `connect()` 中 `lock.wait()` 无超时，`networkInterceptor.proceed()` 未调用时永久阻塞 | 高 | 添加超时 + 中断检测 |
| STAB-15 | CookieManager.kt:L145-153 | `applyToWebView` 调用 `cookieManager.removeSessionCookies(null)` 清除所有会话 Cookie，但只设置当前 domain 的 Cookie，会丢失其他 domain 的 WebView 会话 | 中 | 只清除当前 domain 的 session Cookie（WebView API 限制无法精确清除，建议改为不调用 removeSessionCookies） |

---

## 六、可借鉴的延伸版本优化

### 6.1 强烈建议借鉴

#### 6.1.1 307/308 重定向手动处理（来源：蛋蛋Max）

**文件**：`OkHttpUtils.kt` `newCallResponse` 函数

**优化内容**：在重试循环中检测 307/308 状态码，手动跟随 Location 重定向，保留原 method 和 body。

**风险评估**：低。307/308 是 RFC 7538 标准，OkHttp 默认不跟随，手动处理符合规范。需注意：
1. 重定向次数限制（建议最多 5 次，防止循环）
2. 跨协议重定向（HTTP → HTTPS）需检查 Host 头
3. POST 重定向需保留 body（307/308 保留 method 和 body，与 301/302 不同）

**借鉴代码**：
```kotlin
if (response.code == 307 || response.code == 308) {
    response.header("Location")?.let { location ->
        val redirectRequest = currentRequest.newBuilder()
            .url(location)
            .method(currentRequest.method, currentRequest.body)
            .headers(currentRequest.headers)
            .build()
        response.close()  // 关键：关闭旧 response
        response = newCall(redirectRequest).await()
        if (response.isSuccessful) return response
        currentRequest = redirectRequest
    }
}
```

#### 6.1.2 SSL 条件启用（来源：蛋蛋Max）

**文件**：`HttpHelper.kt` `okHttpClient` 构建

**优化内容**：用 `AppConfig.unsafeSsl` 开关控制是否启用 unsafe SSL，默认开启但允许关闭。

**风险评估**：低。需要：
1. `AppConfig` 添加 `unsafeSsl` 字段（默认 true 保持兼容）
2. 设置界面添加开关
3. 关闭后部分自签名证书站点无法访问（需用户知晓）

**借鉴代码**：
```kotlin
if (AppConfig.unsafeSsl) {
    builder.sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
    builder.hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
}
```

### 6.2 可选借鉴

#### 6.2.1 UrlRecordInterceptor（来源：蛋蛋Max）

**用途**：记录请求 URL 用于书源调试。

**评估**：本项目已有 `OkhttpUncaughtExceptionHandler` 记录异常，且书源调试有 `debug-source.py` 等独立工具。若需增强调试能力可借鉴，否则无需。

#### 6.2.2 NetworkLogInterceptor（来源：阅读NG）

**用途**：记录所有网络请求日志。

**评估**：生产环境会泄漏隐私（如 Cookie、Authorization 头），仅在调试模式开启。本项目已有 `AppLog` 机制，可通过 `BuildConfig.DEBUG` 控制。**不建议默认开启**。

### 6.3 不建议借鉴

#### 6.3.1 RealResponseBody 替代 asResponseBody（蛋蛋Max）

**原因**：`RealResponseBody` 是 OkHttp 内部 API（`okhttp3.internal`），版本升级可能破坏。本项目使用公开扩展函数 `asResponseBody` 更稳定。

---

## 七、总结

### 7.1 整体评估

本项目 HttpClient 组件**功能完整**，覆盖了书源场景的核心需求（Cookie 管理、SSL 兼容、代理、解压、编码检测），但存在以下核心问题：

1. **安全性**：SSL 全信任无条件启用，ObsoleteUrlFactory 强制使用 unsafeTrustManager，存在 MITM 风险
2. **资源管理**：proxyClientCache 无限增长、重试 response 未关闭、GZIPInputStream 未关闭
3. **并发安全**：CookieStore 随机删除 cookie、cookieToMap 非线程安全、CancellationException 被吞
4. **协议兼容**：HTTP/2 非法头、307/308 重定向缺失、SSL 协议过时
5. **死代码**：cookieJar 定义未启用、unsafe cookieJar key 无读取方

### 7.2 优先修复建议

| 优先级 | 问题编号 | 修复内容 | 工作量 |
|--------|----------|----------|--------|
| P0 | STAB-01 | CookieStore 随机删除 cookie 改为 LRU | 0.5d |
| P0 | STAB-07 | CancellationException 透传 | 0.1d |
| P0 | STAB-08 | ObsoleteUrlFactory setSSLSocketFactory 修复 | 0.5d |
| P0 | PERF-01 | proxyClientCache LRU 上限 | 0.5d |
| P1 | PERF-04 | 重试 response 关闭 | 0.1d |
| P1 | STAB-02,03 | proxy 正则解析健壮性 | 0.5d |
| P1 | STAB-04,05 | OkHttpUtils 空指针修复 | 0.1d |
| P1 | STAB-06 | mergeCookiesToMap 空列表处理 | 0.1d |
| P2 | 借鉴 6.1.1 | 307/308 重定向支持 | 0.5d |
| P2 | 借鉴 6.1.2 | SSL 条件启用 | 1d（含 UI） |
| P2 | STAB-12 | SSL 协议升级 | 0.1d |
| P3 | STAB-13 | 删除死代码 cookieJar | 0.1d |

### 7.3 延伸版本对比结论

- **蛋蛋Max** 是最有价值的参考版本，提供了 2 个可借鉴优化（SSL 条件启用、307/308 重定向）
- **阅读NG** 仅多了 NetworkLogInterceptor，价值有限
- **阅读 Archive / 阅读 R / Jingshiro** 与本项目完全一致，无差异
- **喵公子 / 阅读T / 辞晨Max** 获取失败，无法对比

---

## 附录：文件清单与行号索引

| 文件 | 行数 | 关键行号 |
|------|------|----------|
| HttpHelper.kt | 191 | L25-27(proxyCache), L29-49(cookieJar死), L51-127(okHttpClient), L129-147(manga), L152-191(getProxyClient) |
| OkHttpUtils.kt | 198 | L29-43(newCallResponse), L61-77(await), L79-95(text), L97-111(decompressed) |
| CookieManager.kt | 172 | L31-52(save), L57-77(load), L98-109(merge), L133-143(getNoSession) |
| CookieStore.kt | 145 | L26-42(set), L76-92(get+random删除), L109-139(map转换) |
| SSLHelper.kt | 194 | L27-49(unsafeTrust), L55-63(unsafeSSL), L70(unsafeHostname) |
| DecompressInterceptor.kt | 56 | L14-43(intercept), L51-55(promisesBody) |
| OkHttpExceptionInterceptor.kt | 19 | L10-18(intercept) |
| OkhttpUncaughtExceptionHandler.kt | 10 | L7-9(uncaughtException) |
| ObsoleteUrlFactory.kt | 1201 | L322-407(buildCall), L988-991(setSSL漏洞), L161-173(connect死锁) |
| StrResponse.kt | 89 | L25-48(构造函数), L56-61(url) |
| RequestMethod.kt | 5 | L3-5(枚举) |
| CookieManagerInterface.kt | 28 | L3-27(接口) |
