# 网络层架构

> **核心问题**：App 如何发起 HTTP 请求？如何处理 SSL 证书？Cookie 如何管理？
> **答案**：OkHttp 3.x 单例 + 自定义 SSL(全信任) + 临时 CookieJar + Cronet 可选加速 + BackstageWebView(预加载) + 代理支持 + AnalyzeUrl 请求管线。

---

## 1. OkHttpClient 构建

**文件**：[HttpHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt)

### 核心配置

```kotlin
val okHttpClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(15, SECONDS)        // 连接超时15s
        .writeTimeout(15, SECONDS)          // 写超时15s
        .readTimeout(60, SECONDS)           // 读超时60s
        .callTimeout(60, SECONDS)           // 总超时60s
        .sslSocketFactory(unsafeSSLSocketFactory, unsafeTrustManager) // ⚠️ 忽略证书
        .hostnameVerifier(unsafeHostnameVerifier)                      // ⚠️ 忽略主机名
        .retryOnConnectionFailure(true)      // 连接失败自动重试
        .followRedirects(true)               // 跟随HTTP重定向
        .followSslRedirects(true)            // 跟随HTTPS重定向
        .connectionSpecs(MODERN_TLS + COMPATIBLE_TLS + CLEARTEXT)
        // ... 拦截器链（见下文）
}
```

### 拦截器链（按添加顺序）

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
sequenceDiagram
    participant C as Client
    participant R as RateLimiter
    participant Cookie as CookieInterceptor
    participant SSL as SSLHelper
    participant Server as Server
    C->>R: "1. 并发率检查"
    R->>Cookie: "2. 通过"
    Cookie->>SSL: "3. 注入Cookie/Header"
    SSL->>Server: "4. SSL握手+请求"
    Server-->>SSL: "5. 响应"
    SSL-->>Cookie: "6. 保存Cookie"
    Cookie-->>C: "7. 返回响应"
```

| 序号 | 拦截器 | 类型 | 功能 |
|------|--------|------|------|
| 1 | `OkHttpExceptionInterceptor` | Application | 包装 OkHttp 异常为自定义异常 |
| 2 | UA + Keep-Alive 注入 | Application | 自动添加 User-Agent / Keep-Alive / Cache-Control |
| 3 | `CookieManager` (条件) | Network | 仅当请求头含 `cookieJarHeader` 时启用 Cookie |
| 4 | `Cronet.interceptor` (条件) | Application | 若 `AppConfig.isCronet && Cronet.loader.install()` |
| 5 | `DecompressInterceptor` | Application | 自动解压 gzip/deflate/br 响应 |

### UA 注入逻辑

[HttpHelper.kt:L71-L83](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L71)

```
请求头 UA_NAME 处理:
├── 未设置 UA_NAME   → 添加默认 User-Agent (来自 AppConfig.userAgent)
├── UA_NAME == "null" → 移除 User-Agent (模拟空UA)
├── UA_NAME 已有值   → 保持不变 (书源自定义UA)
└── 始终添加 Keep-Alive: 300 / Connection: Keep-Alive / Cache-Control: no-cache
```

### 自定义 DNS 注入

[HttpHelper.kt:L101-L106](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L101)

```kotlin
if (AppConfig.addressCache.isNotEmpty()) {
    builder.dns { hostname ->
        AppConfig.addressCache[hostname] ?: Dns.SYSTEM.lookup(hostname)
    }
}
```

---

## 2. SSL 安全策略

**文件**：[SSLHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/SSLHelper.kt)

### 默认策略：全信任（⚠️ 不验证证书）

用于访问各种来源网站的灵活性，牺牲了传输安全性：

```kotlin
val unsafeTrustManager: X509TrustManager   // checkServerTrusted() 空实现
val unsafeSSLSocketFactory: SSLSocketFactory  // SSLContext("SSL")
val unsafeHostnameVerifier                    // 始终返回 true
```

### 可选：自定义证书验证

SSLHelper 同时提供多种证书验证方案：

| 方法 | 说明 |
|------|------|
| `getSslSocketFactory(trustManager)` | 单向认证：使用自定义 TrustManager |
| `getSslSocketFactory(*certificates)` | 单向认证：用指定证书验服务端 |
| `getSslSocketFactory(bksFile, password, *certificates)` | 双向认证：客户端BKS证书 + 服务端证书 |
| `getSslSocketFactory(bksFile, password, trustManager)` | 双向认证：客户端BKS证书 + 自定义TrustManager |

底层使用 `SSLContext("TLS")` + `KeyStore("BKS")` + `TrustManagerFactory` 标准流程。

---

## 3. Cookie 管理

### 三级优先级模型

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
flowchart TD
    A["请求需要Cookie"] --> B{"临时Cookie存在?"}
    B -->|"是"| C["使用临时Cookie"]
    B -->|"否"| D{"CookieJar有值?"}
    D -->|"是"| E["使用CookieJar"]
    D -->|"否"| F{"数据库有记录?"}
    F -->|"是"| G["从DB加载到CookieJar"]
    G --> E
    F -->|"否"| H["无Cookie可用"]
    C --> I["mergeCookies合并"]
    E --> I
```

```
临时 Cookie (headerMap["Cookie"])   → 最高优先级（手动指定）
CookieJar 自动 Cookie               → 中间优先级（自动管理）
cookies 表持久 Cookie               → 基础优先级（长期存储）
```

### 双层 Cookie 模型

```
请求级别 (临时)
├── CookieJar → saveFromResponse() 存入内存缓存
│   └── CacheManager.putMemory("${domain}_cookieJar", "k1=v1;k2=v2")
└── 默认不启用 CookieJar（okHttpClient 中注释掉 .cookieJar(cookieJar)）

数据库级别 (持久)
├── CookieStore (Room表)
│   └── cookieDao: CookieDao
└── CookieManager
    ├── loadRequest(request)      — 从 DB 加载匹配域名的 Cookie
    └── saveResponse(response)   — 保存响应 Cookie 到 DB
```

### 启用流程

```
书源启用 Cookie 选项
    → 网络拦截器检测到 cookieJarHeader 请求头
    → CookieManager.loadRequest() 从 DB 加载 Cookie 注入请求
    → CookieManager.saveResponse() 保存响应 Set-Cookie 到 DB
```

**注意**：默认 cookieJar 被注释掉 ([HttpHelper.kt:L63](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L63))，只有书源显式启用 Cookie 时才走数据库 Cookie 方案。


### mergeCookies 合并算法

临时 cookie 优先级更高（后者覆盖前者同名项）：

1. 解析 saved cookie 为 key=value 字典
2. 解析 temporary cookie，同名项覆盖
3. 拼接为 `k1=v1; k2=v2` 格式返回

### CookieStore 数据库 CRUD

```python
class CookieStore:
    # cookies 表中保存了 domain -> cookie_string 的映射

    def get_cookie(self, domain: str) -> str:
        cookie_record = db.query("cookies").filter_by(domain=domain).first()
        return cookie_record.cookie if cookie_record else ""

    def save_cookie(self, domain: str, cookie: str):
        existing = db.query("cookies").filter_by(domain=domain).first()
        if existing:
            existing.cookie = cookie
        else:
            db.insert("cookies", {"domain": domain, "cookie": cookie})
        db.commit()
```

---

## 4. Cronet 加速

**文件**：[Cronet.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/Cronet.kt)

Google Cronet（Chromium 网络栈），可选加速组件：

```kotlin
if (AppConfig.isCronet) {
    if (Cronet.loader?.install() == true) {
        Cronet.interceptor?.let { builder.addInterceptor(it) }
    }
}
```

- **开关**：`AppConfig.isCronet` 读取自 `PreferKey.cronet`
- **优势**：HTTP/2 多路复用、连接预取、QUIC 协议
- **注意**：需要设备支持，不支持时自动回退到 OkHttp

---

## 5. 代理支持

[HttpHelper.kt:L152-L191](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L152)

```kotlin
fun getProxyClient(proxy: String?): OkHttpClient {
    // proxy 格式: "http://host:port" 或 "socks5://host:port" 或 "socks5://host:port@user@pass"
    // 解析后创建独立 OkHttpClient（缓存复用）
}
```

- 支持 HTTP / SOCKS4 / SOCKS5 代理
- 支持代理认证 (`Proxy-Authorization` header)
- 代理客户端缓存到 `ConcurrentHashMap` 复用

---

## 6. 特殊客户端

### okHttpClientManga — 漫画下载客户端

[HttpHelper.kt:L129-L147](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L129)

基于 `okHttpClient` 添加额外拦截器：
- `ProgressResponseBody` — 下载进度回调（Glide ProgressManager）
- `ReadManga.rateLimiter` — 速率限制（防止漫画源封 IP）

### BackstageWebView — 后台 WebView 池

**文件**：[BackstageWebView.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/BackstageWebView.kt)

用于需要执行 JS 渲染的页面（如 Cloudflare 防护页面）：
- 后台 WebView 执行 JS → 获取渲染后的 HTML
- 解决了纯 OkHttp 无法执行 JS 的限制

### WebView 池化方案

```
WebViewPool 单例
├── webViews: Stack<PooledWebView>      # 空闲 WebView 栈
├── maxPoolSize: Int                     # 最大池大小
│
PooledWebView:
├── webView: BackstageWebView           # 实际无头 WebView
├── inUse: Boolean                      # 是否在用
│
BackstageWebView:
├── url: String?                        # 要访问的 URL
├── html: String?                       # 要载入的 HTML（非空则优先）
├── javaScript: String?                 # 执行 JS 取返回值
├── sourceRegex: String?                # 提取资源 URL 的正则
├── overrideUrlRegex: String?           # 监控 URL 跳转的正则
├── cacheFirst: Boolean                 # 优先使用缓存
├── delayTime: Long                     # 等待延迟
├── headerMap: Map<String, String>?     # 自定义请求头
└── tag: String?                        # 书源标识
```

> **重构方案**：使用 Playwright 的 Browser Context Pool。每个 context 保持独立的 cookie/header。`page.evaluate(js)` 返回结果。`page.wait_for_event('request', predicate)` + `sourceRegex` 用于资源监听。

---

### NetworkUtils — URL 处理核心

**文件**：[NetworkUtils.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/NetworkUtils.kt)

URL 操作是被调用最频繁的工具之一。**getAbsoluteURL** 在规则引擎、WebBook、RSS 中无处不在。

#### getAbsoluteURL — 5 种 URL 格式处理

```python
@staticmethod
def get_absolute_url(base_url: str, relative_url: str) -> str:
    """将相对/协议无关 URL 转为绝对 URL（核心方法）"""
    if not relative_url:
        return base_url
    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url
    # data: 和 file: 协议直接返回
    if ":" in relative_url.split("/")[0]:
        return relative_url
    if not base_url:
        return relative_url
    # //xxx 协议无关 → 拼 base_url 的 scheme
    if relative_url.startswith("//"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}:{relative_url}"
    # /xxx 绝对路径 → 拼 base_url 的 scheme + host
    if relative_url.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{relative_url}"
    # ../xxx 或 ./xxx 或 xxx 相对路径 → urljoin
    return urljoin(base_url, relative_url)
```

#### 其他 URL 工具方法

```python
@staticmethod
def get_base_url(url: str) -> str:
    """获取基础 URL（不包含路径和查询参数）"""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"

@staticmethod
def get_domain(url: str) -> str:
    """获取域名"""
    return urlparse(url).netloc

@staticmethod
def is_absolute(url: str) -> bool:
    """判断 URL 是否为绝对 URL"""
    return url.startswith("http://") or url.startswith("https://") or ":" in url.split("/")[0]

@staticmethod
def is_data_url(url: str) -> bool:
    """判断是否为 data: URI"""
    return url.startswith("data:")

@staticmethod
def encode_url(url: str, charset: str = "UTF-8") -> str:
    """URL 编码（支持指定字符集）"""
    return quote(url, safe=":/?#[]@!$&'()*+,;=-._~", encoding=charset)
```

### ObsoleteUrlFactory — Legacy 兼容

**文件**：[ObsoleteUrlFactory.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/ObsoleteUrlFactory.kt)

将 OkHttp 包装为 `java.net.HttpURLConnection`，兼容使用旧式 `URL.openConnection()` 的代码。

---

## 7. 网络层全景图

```
                          ┌─────────────────────┐
                          │    书源 / WebBook     │
                          │    (发起 HTTP 请求)    │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   getProxyClient()   │
                          │  (选择代理或直连)      │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            okHttpClient    okHttpClientManga   BackstageWebView
            (通用请求)       (漫画,带进度+限速)    (JS渲染页面)
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
  [拦截器1]     [拦截器2]     [拦截器3..]
  UA注入       Cookie管理     Cronet加速
  SSL忽略      DNS自定义     Decompress
                    │
                    ▼
            OkHttp Engine
            ├── 连接池复用
            ├── HTTP/2 (via Cronet)
            └── Gzip/Deflate/Br 解压
```

### OkHttp 线程池定制

[HttpHelper.kt:L115-L126](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L115)

```kotlin
// 自定义 Dispatcher 线程名和异常处理器
executor.threadFactory = ThreadFactory { runnable ->
    Thread(runnable, "OkHttp Dispatcher").apply {
        isDaemon = false
        uncaughtExceptionHandler = OkhttpUncaughtExceptionHandler
    }
}
```

**OkhttpUncaughtExceptionHandler**：捕获 OkHttp 线程池中的未处理异常，防止静默崩溃。

---

## 8. 其他网络相关组件

| 组件 | 文件 | 用途 |
|------|------|------|
| `OkHttpUtils` | `help/http/OkHttpUtils.kt` | OkHttp 扩展函数（请求构建/响应解析） |
| `StrResponse` | `help/http/StrResponse.kt` | 字符串响应封装（body + charset） |
| `RequestMethod` | `help/http/RequestMethod.kt` | HTTP 方法枚举 |
| `DecompressInterceptor` | `help/http/DecompressInterceptor.kt` | 响应解压拦截器 |
| `OkHttpExceptionInterceptor` | `help/http/OkHttpExceptionInterceptor.kt` | 异常转换拦截器 |


---

## 9. AnalyzeUrl 请求管线

**文件**：[AnalyzeUrl.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt)

AnalyzeUrl 是网络请求的核心调度类，负责将源配置中的 URL 字符串解析、构建、执行，并返回响应结果。整个流程覆盖：JS 预处理 → 变量替换 → 选项解析 → 并发控制 → Cookie 管理 → HTTP 执行 → 登录检测。

### 9.1 构造函数参数（15 个）

```kotlin
class AnalyzeUrl(
    mUrl: String?,          // URL 模板（含 {{key}}、@js: 等占位符）
    key: String?,           // 搜索关键词
    page: Int,              // 当前页码
    speakText: String?,     // TTS朗读文本
    speakSpeed: Int?,       // TTS朗读速度
    baseUrl: String = "",   // 基础 URL，用于拼接相对路径
    source: Source?,        // 书源对象
    ruleData: String?,      // 额外规则数据
    chapter: Chapter?,      // 章节对象
    readTimeout: Long?,     // 读取超时
    callTimeout: Long?,     // 调用超时
    coroutineContext: CoroutineContext?,  // 协程上下文
    headerMapF: Map<String, String>?,  // 外部传入的请求头
    hasLoginHeader: Boolean?,  // 是否包含登录头
    infoMap: MutableMap<String, String>?  // 信息映射
)
```

### 9.2 UrlOption 字段（15 个）

从 URL 尾部解析出的参数对象，格式：`URL,{method:"POST",headers:{...},body:"..."}`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | String | — | 实际 URL（去除选项部分） |
| `method` | String | "GET" | HTTP 方法（GET / POST / HEAD） |
| `charset` | String | "UTF-8" | 字符编码 |
| `headers` | Map | {} | 自定义请求头 |
| `body` | String | "" | POST body |
| `origin` | String | "" | 源URL |
| `retry` | Int | 0 | 重试次数 |
| `type` | Int | 0 | 类型标识 |
| `webView` | Any? | null | 是否使用 WebView |
| `webJs` | String | "" | WebView中执行的JS |
| `webViewDelayTime` | Int | 0 | WebView延迟时间(ms) |
| `dnsIp` | String | "" | 自定义DNS IP |
| `js` | String | "" | URL解析完参数后执行的JS |
| `bodyJs` | String | "" | 得到访问结果后执行的JS（HTTP 请求完成后、返回结果前执行，用于解密或转换响应内容） |
| `serverID` | String | "" | 服务器ID |

### 9.3 URL 初始化管线

```
URL 模板字符串
    │
    ▼
Step 1: analyzeJs()
    @js:code  → 执行JS替换
    <js>code</js> → 执行JS替换
    @result → 引用上一步结果
    │
    ▼
Step 2: replaceKeyPageJs()
    {{key}} / {{searchKey}} → URL编码后的关键词
    {{page}} → 页码数字
    <value1,value2,...> → 多页URL片段（尖括号语法）
    {{baseURL}} / {{sourceName}} 等 → 源信息
    │
    ▼
Step 3: analyzeUrl() — 解析 UrlOption
    URL,{method:"POST",headers:{...},body:"..."}
    提取：method/charset/headers/body/webView/...
    │
    ▼
Step 4: 构建最终 URL / Body
    GET → 拼接 query 参数
    POST → 构建 body（form/json/multipart）
```

### 9.4 JS 预处理 — analyzeJs()

| 语法 | 说明 |
|------|------|
| `@js:code` | 执行 code，替换整个 URL |
| `<js>code</js>` | 执行 code，替换标签部分 |
| `@result:` | 引用上一步 JS 执行结果 |

### 9.5 变量替换 — replaceKeyPageJs()

| 占位符 | 替换值 | 说明 |
|--------|--------|------|
| `{{key}}` / `{{searchKey}}` | `key`（URL 编码） | 搜索关键词 |
| `{{page}}` | `page`（页码数字） | 当前页码 |
| `<value1,value2,...>` | `values[page-1]`，超出取最后一个 | 多页 URL 构建，尖括号逗号分隔 |
| `{{baseURL}}` | `baseUrl` | 基础 URL |
| `{{sourceName}}` | `source.sourceName` | 源名称 |
| `{{sourceUrl}}` | `source.sourceUrl` | 源 URL |
| `{{sourceGroup}}` | `source.sourceGroup` | 源分组 |
| `{{speakText}}` | `speakText` | TTS 文本 |
| `{{ruleData}}` | `ruleData` | 额外规则数据 |
| `{{自定义}}` | `infoMap[key]` | 自定义变量映射 |

### 9.6 UrlOption 解析

从 URL 尾部解析选项，解析规则：
1. 从 URL 末尾向前查找不在 `{}``""` 内的逗号
2. 逗号后的部分作为 JSON 解析为 UrlOption
3. 逗号前的部分为实际 URL

### 9.7 GET URL 构建

- 相对路径：拼接 `baseUrl`
- `data:` 前缀：标记为 Data URI
- `@image=` 前缀：替换为 `http://`

### 9.8 POST Body 构建

- `@js:` 前缀的 body：执行 JS 后作为 body
- `bodyJs`：请求完成后执行的 JS（延迟执行）
- Content-Type 自动推断：`{` 开头 → `application/json`，否则 → `application/x-www-form-urlencoded`

---

## 10. 请求执行管线

### 10.1 getStrResponseAwait() 完整流程

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
flowchart TD
    A["getStrResponseAwait()"] --> B["并发率限制"]
    B --> C["Cookie设置"]
    C --> D{"使用WebView?"}
    D -->|"是"| E["BackstageWebView加载"]
    D -->|"否"| F["OkHttp执行请求"]
    E --> G{"登录检测"}
    F --> G
    G -->|"需登录"| H["执行loginCheckJs"]
    G -->|"已登录"| I["返回StrResponse"]
    H --> I
```

```
1. 并发率限制
   ConcurrentRateLimiter.withLimit()
   "10/1000" → 1000ms内最多10次
        │
        ▼
2. Cookie 设置
   CookieStore.getCookie(domain)
   + headerMap["Cookie"] (临时)
   + CookieJar 标记
        │
        ▼
3. Header 构建
   优先级：源 headerMap > 全局默认 > 方法特定
   自动推断 Content-Type / Origin / Referer / User-Agent
        │
        ▼
4. 选择请求方式
   webView=true? ──yes──→ WebView渲染
       │ no
       ▼
   OkHttp 直连
   ├── GET    → query参数
   ├── POST   → form/json/multipart
   └── HEAD   → 仅获取响应头
        │
        ▼
5. 错误处理
   SocketTimeoutException  → -2
   UnknownHostException    → -3
   ConnectException        → -4
   SocketException         → -5
   SSLException            → -6
   其他                    → -7
        │
        ▼
6. XML 自动补齐
   body以<开头且非<html → 加<?xml>
   当 Content-Type 为 XML 但响应体不以 `<?xml` 声明开头时，自动在响应体前补齐 `<?xml version="1.0" encoding="UTF-8"?>` 声明，修复部分书源返回的畸形 XML 响应。
        │
        ▼
7. 登录检测
   loginCheckJs != null → evalJS()
   response.code()==500 → 需登录
   请求失败 → errResponse再次检测
```

### 10.2 WebView/OkHttp 请求选择

| webView 值 | 结果 |
|------------|------|
| `null` | False（使用 OkHttp） |
| `"false"` | False |
| `false` | False |
| 其他任何值 | True（使用 WebView） |

### 10.3 POST Body 类型处理

| Content-Type | 处理方式 |
|-------------|---------|
| `application/x-www-form-urlencoded` | key=value&key=value form body |
| `application/json` | JSON body |
| `multipart/form-data` | Multipart 上传 |

### 10.3b HEAD 方法

`method=HEAD` 在 GET 和 POST 之外受支持，用于仅获取响应头而不下载响应体：
- 典型场景：检查 URL 可用性、获取 Content-Length / Content-Type 等元信息
- 在 UrlOption 中设置 `method:"HEAD"` 即可启用

### 10.4 登录检测

```
loginCheckJs 存在时：
├── 正常响应 → 执行 checkJs(response)
├── response.code() == 500 → 抛出 LoginException
└── 请求失败 → 用 errResponse 再次执行 checkJs
```

### 10.5 StrResponse 错误码

| 错误 | 码 | 说明 |
|------|-----|------|
| 正常响应 | 200 | HTTP 成功 |
| SocketTimeoutException | -2 | 连接超时 |
| UnknownHostException | -3 | DNS 解析失败 |
| ConnectException | -4 | 连接被拒绝 |
| SocketException | -5 | Socket 异常 |
| SSLException | -6 | SSL/TLS 错误 |
| 其他异常 | -7 | 未归类错误 |

---

## 11. 并发率限制器 — ConcurrentRateLimiter

**文件**：[ConcurrentRateLimiter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/analyzeRule/ConcurrentRateLimiter.kt)

控制对同一源的请求频率，防止被封 IP。

### 配置格式

| 格式 | 说明 |
|------|------|
| `"10/1000"` | 1000ms 内最多 10 次 |
| `"5"` | 1 秒内最多 5 次（默认分母 1000ms） |

### 滑动窗口算法（synchronized 线程安全）

```
1. nowTime = System.currentTimeMillis()
2. nextTime = record.time + record.interval
3. if nowTime >= nextTime:
       record.time = nowTime
       record.frequency = 0       // 时间窗口已过，重置
4. if record.frequency < record.access_limit:
       record.frequency++
       返回 0 (允许)
   else:
       返回 (nextTime - nowTime) (需等待的毫秒数)
```

### 全局记录表

- `ConcurrentHashMap<sourceKey, RateRecord>` 保证线程安全
- `RateRecord` 包含：time（上次重置时间戳）、interval（时间窗口 ms）、accessLimit（窗口内最大次数）、frequency（当前已用次数）

---

## 12. 关键设计要点

### Cookie 优先级

```
临时 Cookie (headerMap["Cookie"])   → 最高优先级（手动指定）
CookieJar 自动 Cookie               → 中间优先级（自动管理）
cookies 表持久 Cookie               → 基础优先级（长期存储）
```

### UrlOption.webView 多值匹配

| webView 值 | 结果 |
|------------|------|
| `null` | False |
| `"false"` | False |
| `false` | False |
| 其他任何值 | True |

### 并发率限制定时算法

```
算法（线程安全同步块）：
1. nowTime = System.currentTimeMillis()
2. nextTime = record.time + record.interval
3. if nowTime >= nextTime:
       record.time = nowTime
       record.frequency = 0
4. if record.frequency < record.access_limit:
       record.frequency++
       返回 0 (允许)
   else:
       返回 (nextTime - nowTime) (需等待的毫秒数)
```

---

## Python 重构参考

> 以下为 AnalyzeUrl 核心逻辑的 Python 伪代码，供重构参考。
