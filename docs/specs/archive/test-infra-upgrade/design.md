# Design: 测试基础设施升级 - 端到端真机级调试能力

> 状态：⚠️ 代码实现完成，测试验证缺失（2026-06-18）
> 创建日期：2026-06-18
> 优先级：P0

## 1. Technical Approach（技术方案）

### 1.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Python 客户端层（升级）                            │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ debug-source.py  │  │rule_engine_client│  │ deep-verify.py   │  │
│  │ (新增:端到端调试) │  │  (扩展:流式日志) │  │ (deprecated)     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ stdin/stdout JSON 行协议（支持流式）
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              JVM 服务端 (RuleEngineServer.kt)（升级）                │
│                                                                     │
│  新增命令路由:                                                      │
│  ├─ analyzeUrl       - URL 解析（AnalyzeUrl 移植）                  │
│  ├─ debugBookSource  - 书源端到端调试（BookSourceDebugger）          │
│  └─ debugRssSource   - 订阅源端到端调试（RssSourceDebugger）         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              端到端调试器层（新增）                           │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                 │   │
│  │  │BookSourceDebugger│  │RssSourceDebugger │                 │   │
│  │  │ (search→detail→ │  │ (sort→content)   │                 │   │
│  │  │  toc→content)   │  │                  │                 │   │
│  │  └──────────────────┘  └──────────────────┘                 │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                 │   │
│  │  │  DebugLogger     │  │  AnalyzeUrl      │                 │   │
│  │  │ (真机级日志格式) │  │  (URL 解析移植)  │                 │   │
│  │  └──────────────────┘  └──────────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Mock 层（扩展）                                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │   │
│  │  │MockCookieStore│ │MockCacheManager│ │MockSource   │         │   │
│  │  │(二级域名Cookie)│ │(内存缓存)     │ │(header/cookie)│       │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘         │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │   │
│  │  │MockBook      │ │MockBookChapter│ │StrResponse   │         │   │
│  │  │(name/author/ │ │(title/url)   │ │(url+body+code)│        │   │
│  │  │ variableMap) │ │              │ │              │         │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              规则引擎层（复用 + 修复）                       │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │   │
│  │  │AnalyzeRule   │ │AnalyzeByJSoup│ │AnalyzeByXPath│         │   │
│  │  │(修复:注入13个│ │(复用)        │ │(复用)        │         │   │
│  │  │ 变量+NativeObj│ │              │ │              │         │   │
│  │  │ +put/get层级)│ │              │ │              │         │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘         │   │
│  │  ┌──────────────┐ ┌──────────────┐                          │   │
│  │  │RuleAnalyzer  │ │MinimalMockJs │                          │   │
│  │  │(复用)        │ │Extensions    │                          │   │
│  │  │              │ │(扩展:ajax+   │                          │   │
│  │  │              │ │cookie+加密)  │                          │   │
│  │  └──────────────┘ └──────────────┘                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ 对比参考（不修改）
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│           Legado 真机源码（参考，不修改）                            │
│  app/.../model/Debug.kt          - 调试流程参考                     │
│  app/.../model/analyzeRule/      - AnalyzeUrl/AnalyzeRule 参考      │
│  app/.../help/JsExtensions.kt    - Mock 扩展参考                    │
│  app/.../help/http/CookieStore.kt - Cookie 管理参考                 │
│  app/.../model/webBook/          - 执行链路参考                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 通信协议升级

#### 当前协议（请求-响应）

```
客户端 → 服务端：{"cmd": "evalJS", "code": "..."}
服务端 → 客户端：{"ok": true, "result": "..."}
```

#### 升级后协议（支持流式）

```
客户端 → 服务端：{"cmd": "debugBookSource", "sourceJson": "{...}", "key": "斗破"}

服务端 → 客户端（多行流式响应）：
  {"type": "log", "state": 1, "msg": "[00:00.001] ︾开始解析搜索页", "ts": "2026-06-18T10:00:00.001"}
  {"type": "log", "state": 10, "msg": "搜索页HTML", "html": "<html>...", "ts": "..."}
  {"type": "log", "state": 1, "msg": "[00:00.005] ┌获取书名", "ts": "..."}
  {"type": "log", "state": 1, "msg": "[00:00.006] └斗破苍穹", "ts": "..."}
  ...
  {"type": "result", "state": 1000, "success": true, "summary": {
    "searchCount": 20,
    "bookName": "斗破苍穹",
    "author": "天蚕土豆",
    "tocCount": 1500,
    "contentLength": 3200,
    "stages": ["search", "detail", "toc", "content"]
  }}
  
  或错误时：
  {"type": "error", "state": -1, "msg": "目录为空", "stackTrace": "...", "failedStage": "toc"}
```

**协议设计要点**：
- `type` 字段区分日志/结果/错误
- `state` 字段与真机 Debug.kt 一致（1/10/20/30/40/-1/1000）
- `html` 字段仅在 state=10/20/30/40 时存在
- `ts` 字段为 ISO 时间戳，便于客户端计算相对时间
- 流式响应以 `type=result` 或 `type=error` 结束

### 1.3 AnalyzeUrl 移植策略

从真机 `app/.../model/analyzeRule/AnalyzeUrl.kt`（957 行）提取核心逻辑，剥离 Android 依赖：

| 真机依赖 | 替换方案 |
|---------|---------|
| `CookieStore` | `MockCookieStore`（内存版） |
| `CacheManager` | `MockCacheManager`（内存版） |
| `BackstageWebView` | 抛 `UnsupportedOperationException` + 标记 unverifiable |
| `ConcurrentRateLimiter` | 移除限流（单进程不需要） |
| `OkHttp + CookieJar` | OkHttp（已有）+ 手动注入 Cookie |
| `source` (BaseSource) | `MockSource`（内存版） |
| `ruleData` (Book/RssArticle) | `MockBook` / `MockRssArticle` |
| `chapter` (BookChapter) | `MockBookChapter` |
| `Coroutine` | 改为同步阻塞（JVM 仿真器单线程） |

**保留的核心逻辑**：
- `initUrl()` 三步流水线
- `analyzeJs()` - `@js:`/`<js>` 标签求值
- `replaceKeyPageJs()` - `{{js}}`/`<page>` 替换
- `analyzeUrl()` - URL + JSON 选项解析
- `UrlOption` 数据类（14 个字段）
- `setCookie()` - Cookie 合并
- `executeStrRequest()` - HTTP 请求执行
- `evalJS()` - JS 求值 + 变量注入
- 错误码映射（-1 到 -7）

### 1.4 BookSourceDebugger 设计

参考真机 `Debug.kt:230-377` 的 searchDebug→infoDebug→tocDebug→contentDebug 链路：

```kotlin
class BookSourceDebugger(
    private val sourceJson: String,      // BookSource JSON
    private val key: String,             // 搜索关键词或阶段标识
    private val logger: DebugLogger,     // 日志输出器
    private val mockJs: MinimalMockJsExtensions  // 共享 Mock（含 Cookie/Cache）
) {
    private val mockSource = MockSource.fromJson(sourceJson)
    private val mockBook = MockBook()
    
    fun debug(): DebugResult {
        return when {
            key.isAbsUrl() -> debugInfo()           // 详情页调试
            key.contains("::") -> debugExplore()    // 发现页调试
            key.startsWith("++") -> debugToc()      // 目录页调试
            key.startsWith("--") -> debugContent()  // 正文页调试
            else -> debugSearch()                   // 搜索页调试（完整链路）
        }
    }
    
    private fun debugSearch(): DebugResult {
        logger.log("⇒开始搜索关键字:$key")
        logger.log("︾开始解析搜索页")
        
        // 1. 构造搜索 URL
        val analyzeUrl = AnalyzeUrl(
            mockSource.searchUrl, key=key, page=1, 
            source=mockSource, ruleData=mockBook
        )
        val response = analyzeUrl.getStrResponse()
        logger.log("≡获取成功:${response.url}", state=10, html=response.body)
        
        // 2. 解析搜索列表
        val analyzeRule = AnalyzeRule(mockJs, book=mockBook, source=mockSource)
        analyzeRule.setContent(response.body)
        analyzeRule.baseUrl = response.url
        
        val bookList = analyzeRule.getElements(mockSource.ruleSearch.bookList)
        logger.log("┌获取书籍列表")
        logger.log("└列表大小:${bookList.size}")
        
        // 3. 提取第一本书字段
        if (bookList.isEmpty()) {
            return logger.error("搜索结果为空")
        }
        
        val firstBook = bookList[0]
        analyzeRule.setContent(firstBook)
        
        val name = analyzeRule.getString(mockSource.ruleSearch.name)
        logger.log("┌获取书名"); logger.log("└$name")
        mockBook.name = name
        
        val author = analyzeRule.getString(mockSource.ruleSearch.author)
        logger.log("┌获取作者"); logger.log("└$author")
        mockBook.author = author
        
        val bookUrl = analyzeRule.getUrl(mockSource.ruleSearch.bookUrl)
        logger.log("┌获取详情页链接"); logger.log("└$bookUrl")
        mockBook.bookUrl = bookUrl
        
        logger.log("◇书籍总数:${bookList.size}")
        logger.log("︽搜索页解析完成")
        logger.log("")  // 空行
        
        // 4. 继续详情/目录/正文
        return debugInfo(bookUrl)
    }
    
    private fun debugInfo(bookUrl: String): DebugResult { /* ... */ }
    private fun debugToc(tocUrl: String): DebugResult { /* ... */ }
    private fun debugContent(chapterUrl: String): DebugResult { /* ... */ }
}
```

### 1.5 DebugLogger 设计

参考真机 `Debug.kt:33` 的 log 方法：

```kotlin
class DebugLogger(private val startTime: Long = System.currentTimeMillis()) {
    
    private val timeFormat = SimpleDateFormat("[mm:ss.SSS]", Locale.getDefault())
    
    fun log(
        msg: String = "",
        state: Int = 1,
        html: String? = null,
        showTime: Boolean = true
    ) {
        val ts = if (showTime) {
            val elapsed = System.currentTimeMillis() - startTime
            timeFormat.format(Date(elapsed))
        } else ""
        
        val line = buildString {
            if (showTime) append(ts).append(" ")
            append(msg)
        }
        
        // 输出为 JSON 行（流式协议）
        val response = JsonObject().apply {
            addProperty("type", "log")
            addProperty("state", state)
            addProperty("msg", line)
            if (html != null) addProperty("html", html)
            addProperty("ts", Instant.now().toString())
        }
        println(response.toString())
        System.out.flush()  // 立即刷新，确保实时性
    }
    
    fun error(msg: String, stackTrace: String? = null, failedStage: String? = null) {
        val response = JsonObject().apply {
            addProperty("type", "error")
            addProperty("state", -1)
            addProperty("msg", msg)
            if (stackTrace != null) addProperty("stackTrace", stackTrace)
            if (failedStage != null) addProperty("failedStage", failedStage)
        }
        println(response.toString())
        System.out.flush()
    }
    
    fun result(success: Boolean, summary: JsonObject) {
        val response = JsonObject().apply {
            addProperty("type", "result")
            addProperty("state", 1000)
            addProperty("success", success)
            add("summary", summary)
        }
        println(response.toString())
        System.out.flush()
    }
}
```

### 1.6 MockCookieStore 设计

参考真机 `app/.../help/http/CookieStore.kt`：

```kotlin
class MockCookieStore {
    private val cookieMap = ConcurrentHashMap<String, MutableMap<String, String>>()
    
    fun getCookie(url: String): String {
        val domain = NetworkUtils.getSubDomain(url)  // 二级域名
        return cookieMap[domain]?.entries?.joinToString("; ") { "${it.key}=${it.value}" } ?: ""
    }
    
    fun getCookie(url: String, key: String): String {
        val domain = NetworkUtils.getSubDomain(url)
        return cookieMap[domain]?.get(key) ?: ""
    }
    
    fun setCookie(url: String, cookie: String) {
        val domain = NetworkUtils.getSubDomain(url)
        val map = cookieMap.getOrPut(domain) { mutableMapOf() }
        // 解析 "key1=val1; key2=val2" 格式
        cookie.split(";").forEach { pair ->
            val idx = pair.indexOf("=")
            if (idx > 0) {
                map[pair.substring(0, idx).trim()] = pair.substring(idx + 1).trim()
            }
        }
    }
    
    fun removeCookie(url: String) {
        val domain = NetworkUtils.getSubDomain(url)
        cookieMap.remove(domain)
    }
}
```

### 1.7 AnalyzeRule 修复设计

#### 修复 1: evalJS 注入 13 个变量

```kotlin
// 修改前（当前 MVP4）
bindings["java"] = mockJs
bindings["result"] = result
bindings["baseUrl"] = baseUrl
bindings["src"] = content

// 修改后（对齐真机）
bindings["java"] = mockJs
bindings["cookie"] = mockCookieStore      // 新增
bindings["cache"] = mockCacheManager      // 新增
bindings["source"] = mockSource           // 新增
bindings["book"] = mockBook               // 新增
bindings["result"] = result
bindings["baseUrl"] = baseUrl
bindings["chapter"] = mockBookChapter     // 新增
bindings["title"] = mockBookChapter?.title  // 新增
bindings["src"] = content
bindings["nextChapterUrl"] = null         // 新增
bindings["rssArticle"] = null             // 新增
bindings["fromBookInfo"] = isFromBookInfo  // 新增
```

#### 修复 2: NativeObject/LinkedTreeMap 处理

```kotlin
// 在 getStringList/getString 中新增分支
when (result) {
    is NativeObject -> {
        // Rhino 原生对象，按键值访问
        val value = result.get(key)
        return listOf(value?.toString() ?: "")
    }
    is LinkedTreeMap<*, *> -> {
        // gson LinkedTreeMap，按键值访问
        val value = result[key]
        return listOf(value?.toString() ?: "")
    }
    // ... 原有分支
}
```

#### 修复 3: put/get 变量层级

```kotlin
fun put(key: String, value: String): String {
    mockBookChapter?.putVariable(key, value)      // 优先存到章节
        ?: mockBook?.putVariable(key, value)      // 其次存到书
        ?: mockSource?.put(key, value)            // 最后存到源
    return value
}

fun get(key: String): String {
    when (key) {
        "bookName" -> return mockBook?.name ?: ""
        "title" -> return mockBookChapter?.title ?: ""
    }
    return mockBookChapter?.getVariable(key)
        ?: mockBook?.getVariable(key)
        ?: mockSource?.get(key)
        ?: ""
}
```

## 2. Architecture Decisions（架构决策）

### AD-1: 改造现有 MVP4 而非新建 MVP5

**决策**：在现有 `tools/mvp1-build/` 项目中增量补充，不新建 MVP5 项目。

**理由**：
- MVP4 的核心解析器（AnalyzeRule/AnalyzeByJSoup/AnalyzeByXPath/RuleAnalyzer）已与真机高度一致，无需重写
- MinimalMockJsExtensions 是增量补充，不破坏现有架构
- AnalyzeUrl 可作为新增文件，不修改现有代码
- 遵循"懒原则" - 最少代码完成目标

**替代方案（已否决）**：新建 MVP5 项目 - 重复代码多、维护两套、不符合懒原则。

### AD-2: 同步阻塞而非协程

**决策**：JVM 服务端使用同步阻塞 HTTP 请求，不使用 Kotlin 协程。

**理由**：
- JVM 仿真器是单进程单线程，无需并发
- 同步代码更易调试和维护
- 真机的协程主要用于 UI 不阻塞，JVM 仿真器无 UI

**影响**：ajax/ajaxAll 改为同步实现；ajaxAll 串行执行（真机是并发）。

### AD-3: 流式协议而非批量响应

**决策**：端到端调试命令使用流式 JSON 行协议，而非批量响应。

**理由**：
- 端到端调试可能耗时 30 秒+，批量响应会导致客户端长时间无输出
- 流式输出允许客户端实时显示日志，便于定位失败阶段
- 与真机 Debug 的增量 callback 机制一致

**实现**：每条日志立即 `println` + `System.out.flush()`，客户端逐行读取。

### AD-4: 内存版 CookieStore 而非持久化

**决策**：CookieStore 使用内存版（ConcurrentHashMap），不持久化到数据库。

**理由**：
- JVM 仿真器是短生命周期进程（单次调试会话）
- 持久化需要引入 SQLite 依赖，增加复杂度
- 内存版已能满足"跨阶段 Cookie 持久化"需求

**影响**：JVM 服务端重启后 Cookie 丢失（可接受）。

### AD-5: 不仿真 BackstageWebView

**决策**：`webView()` / `startBrowserAwait()` / `getVerificationCode()` / WebJs 模式保持抛异常 + 标记 unverifiable。

**理由**：
- BackstageWebView 依赖 Android WebView 原生组件，JVM 无法仿真
- 强行仿真（如用 Jsoup 模拟）会导致行为与真机不一致，违背"行为一致"原则
- 明确标记 unverifiable 比"虚假通过"更诚实

**影响**：含 webView 的源规则标记为"需真机验证"，AI 不得声称"测试通过"。

### AD-6: AnalyzeUrl 从真机源码提取而非重写

**决策**：从 `app/.../model/analyzeRule/AnalyzeUrl.kt` 提取核心逻辑，剥离 Android 依赖。

**理由**：
- AnalyzeUrl 逻辑复杂（957 行），重写易引入 bug
- 真机源码已经过大量用户验证，行为可靠
- 提取 + 剥离依赖的方式可保留核心逻辑一致性

**剥离清单**：
- CookieStore → MockCookieStore
- CacheManager → MockCacheManager
- BackstageWebView → 抛异常
- ConcurrentRateLimiter → 移除
- Coroutine → 同步阻塞

### AD-7: 日志格式与真机完全一致

**决策**：DebugLogger 输出 `[mm:ss.SSS] ︾︽⇒┌└≡◇` 格式 + state 状态码，与真机 `Debug.kt` 完全一致。

**理由**：
- 便于客户端日志与真机日志直接对比
- 便于 AI 理解日志含义（与 references/ 文档一致）
- 符合"行为一致"原则

### AD-8: deep-verify.py 标记 deprecated 而非删除

**决策**：`deep-verify.py` 保留但标记 deprecated，全链路验证改调 `debug-source.py`。

**理由**：
- 保留向后兼容，不破坏现有工作流
- deprecated 标记提示用户迁移
- 删除可能导致已有脚本/文档引用失效

### AD-9: 单阶段调试支持

**决策**：debugBookSource 支持 key 格式区分调试阶段（`isAbsUrl`→详情、`++url`→目录、`--url`→正文）。

**理由**：
- 与真机 SourceEditor 的"调试搜索/调试详情/调试目录/调试正文"按钮一致
- 便于快速定位单阶段问题
- 减少全链路调试耗时

### AD-10: 变量持久化在 Mock 层

**决策**：`@put/@get` 和 `java.put/get` 变量存储在 MockBook/MockSource，而非 AnalyzeRule 实例。

**理由**：
- AnalyzeRule 实例每次创建会丢失变量
- MockBook/MockSource 在整个调试会话期间持久存在
- 与真机 `chapter → book → source` 层级一致

### AD-11: 错误码与真机一致

**决策**：HTTP 请求错误码使用真机 `AnalyzeUrl.kt:520` 的 -1 到 -7 映射。

**理由**：
- 便于客户端识别错误类型
- 与真机日志一致

**错误码**：
- -1: 超时（InterruptedIOException）
- -2: SocketTimeoutException
- -3: UnknownHostException
- -4: ConnectException
- -5: SocketException
- -6: SSLException
- -7: 其它

### AD-12: 不实现 Cronet / 代理 / DNS 自定义

**决策**：UrlOption 的 `dnsIp` / `proxy` / `serverID` / `webViewDelayTime` 字段解析但忽略。

**理由**：
- 这些字段在 JVM 仿真器中无意义
- 解析但忽略比抛异常更友好（不影响主流程）
- 符合"懒原则"

## 3. Data Flow（数据流）

### 3.1 端到端书源调试数据流

```
用户执行: python scripts/debug-source.py --source book.json --key "斗破"

1. Python 客户端启动
   ├─ 解析参数（source/key/stage）
   ├─ 读取 BookSource JSON
   └─ 启动 JVM 服务端（如未启动）

2. Python 客户端发送调试命令
   └─ stdin: {"cmd": "debugBookSource", "sourceJson": "{...}", "key": "斗破"}

3. JVM 服务端接收命令
   ├─ 解析 BookSource JSON → MockSource
   ├─ 创建 MockBook / MockBookChapter / MockCookieStore / MockCacheManager
   ├─ 创建 DebugLogger（startTime = now）
   └─ 创建 BookSourceDebugger

4. BookSourceDebugger.debugSearch()
   ├─ logger.log("⇒开始搜索关键字:斗破")
   ├─ logger.log("︾开始解析搜索页")
   ├─ AnalyzeUrl(searchUrl, key="斗破", page=1, source=mockSource)
   │    ├─ analyzeJs()      - 执行 @js: / <js>
   │    ├─ replaceKeyPageJs() - 替换 {{key}} / {{page}}
   │    └─ analyzeUrl()     - 解析 URL + JSON 选项
   ├─ analyzeUrl.getStrResponse()
   │    ├─ setCookie()      - 合并 MockCookieStore + header Cookie
   │    ├─ OkHttp newCallStrResponse (GET/POST)
   │    └─ 返回 StrResponse(url, body, code)
   ├─ logger.log("≡获取成功:${url}", state=10, html=body)
   ├─ AnalyzeRule(mockJs, book=mockBook, source=mockSource)
   │    ├─ setContent(body)
   │    ├─ baseUrl = url
   │    └─ getElements(ruleSearch.bookList) → bookList
   ├─ logger.log("┌获取书籍列表")
   ├─ logger.log("└列表大小:${bookList.size}")
   ├─ 遍历第一本书:
   │    ├─ getString(ruleSearch.name) → name
   │    ├─ logger.log("┌获取书名"); logger.log("└${name}")
   │    ├─ getString(ruleSearch.author) → author
   │    ├─ getString(ruleSearch.bookUrl) → bookUrl
   │    └─ mockBook.name/author/bookUrl = ...
   ├─ logger.log("◇书籍总数:${bookList.size}")
   ├─ logger.log("︽搜索页解析完成")
   └─ → debugInfo(bookUrl)

5. BookSourceDebugger.debugInfo(bookUrl)
   ├─ logger.log("⇒开始访问详情页:${bookUrl}")
   ├─ logger.log("︾开始解析详情页")
   ├─ AnalyzeUrl(bookUrl, source=mockSource, ruleData=mockBook)
   ├─ getStrResponse() → response
   ├─ logger.log("≡获取成功:${url}", state=20, html=body)
   ├─ AnalyzeRule(mockJs, book=mockBook, source=mockSource)
   │    ├─ setContent(body)
   │    ├─ 执行 ruleBookInfo.init（如有）→ java.put 变量存入 mockBook
   │    └─ 提取 name/author/intro/coverUrl/tocUrl 等
   ├─ logger.log("┌获取书名/作者/简介/封面链接/目录链接")
   ├─ logger.log("︽详情页解析完成")
   └─ → debugToc(tocUrl)

6. BookSourceDebugger.debugToc(tocUrl)
   ├─ logger.log("︾开始解析目录页")
   ├─ AnalyzeUrl(tocUrl, source=mockSource, ruleData=mockBook)
   ├─ getStrResponse() → response
   ├─ logger.log(state=30, html=body)
   ├─ AnalyzeRule.getElements(ruleToc.chapterList) → chapterList
   ├─ logger.log("┌获取目录列表"); logger.log("└列表大小:${chapterList.size}")
   ├─ 遍历章节:
   │    ├─ getString(ruleToc.chapterName) → title
   │    ├─ getUrl(ruleToc.chapterUrl) → url
   │    └─ 添加到 mockBook.chapters
   ├─ nextTocUrl? → 循环获取下一页
   ├─ logger.log("◇目录总数:${chapters.size}")
   ├─ logger.log("︽目录页解析完成")
   └─ → debugContent(chapters[0].url)

7. BookSourceDebugger.debugContent(chapterUrl)
   ├─ logger.log("︾开始解析正文页")
   ├─ AnalyzeUrl(chapterUrl, source=mockSource, ruleData=mockBook, chapter=mockBookChapter)
   ├─ getStrResponse() → response
   ├─ logger.log(state=40, html=body)
   ├─ AnalyzeRule.getString(ruleContent.content) → content
   ├─ replaceRegex? → 应用正则替换
   ├─ logger.log("┌获取章节名称"); logger.log("└${title}")
   ├─ logger.log("┌获取正文内容"); logger.log("└\n${content}")
   ├─ logger.log("︽正文页解析完成")
   └─ logger.result(success=true, summary={...})

8. Python 客户端接收流式日志
   ├─ 逐行读取 stdout
   ├─ 解析 JSON
   ├─ 实时打印日志（与真机格式一致）
   ├─ 收集 HTML 源码（state=10/20/30/40）
   └─ 收到 type=result 或 type=error 时结束

9. Python 客户端输出验证报告
   ├─ 4 阶段通过情况
   ├─ 失败阶段（如有）
   ├─ 不可仿真项（webView 等）
   └─ 可信度评估
```

## 4. File Changes（文件变更清单）

### 4.1 新增文件（9 个）

| 文件路径 | 行数估计 | 职责 |
|---------|---------|------|
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/AnalyzeUrl.kt` | ~600 | AnalyzeUrl 移植（从真机提取） |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockCookieStore.kt` | ~80 | 内存版 CookieStore |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockCacheManager.kt` | ~60 | 内存版 CacheManager |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockSource.kt` | ~120 | 内存版 BookSource/RssSource |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockBook.kt` | ~80 | 内存版 Book/BookChapter |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/DebugLogger.kt` | ~100 | 真机级调试日志输出器 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/BookSourceDebugger.kt` | ~400 | 端到端书源调试器 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/RssSourceDebugger.kt` | ~250 | 端到端订阅源调试器 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/StrResponse.kt` | ~40 | 真机 StrResponse 简化版 |
| `scripts/debug-source.py` | ~300 | 端到端调试脚本 |

### 4.2 修改文件（6 个）

| 文件路径 | 修改内容 | 行数变化 |
|---------|---------|---------|
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/RuleEngineServer.kt` | 新增 3 个命令路由（analyzeUrl/debugBookSource/debugRssSource） | +80 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MinimalMockJsExtensions.kt` | 扩展 ajax/connect/getCookie/setCookie/md5Encode16/sha1/sha256/HMac 等 | +150 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/AnalyzeRule.kt` | 修复 evalJS 注入 13 变量 + NativeObject/LinkedTreeMap + put/get 层级 | +60 |
| `tools/rule_engine_client.py` | 新增 analyze_url/debug_book_source/debug_rss_source 方法 + 流式日志回调 | +120 |
| `tools/jvm_helpers.py` | 可信度评估新增"端到端调试通过"判定 | +20 |
| `SKILL.md` | Phase 3 章节更新 + JVM 测试基础设施章节更新 | +50 |

### 4.3 标记 deprecated 文件（1 个）

| 文件路径 | 处理 |
|---------|------|
| `scripts/deep-verify.py` | 文件头部添加 deprecated 警告，全链路验证改调 debug-source.py |

### 4.4 总工作量估计

| 类型 | 文件数 | 行数估计 |
|------|--------|---------|
| 新增 Kotlin | 9 | ~1730 |
| 新增 Python | 1 | ~300 |
| 修改 Kotlin | 3 | ~290 |
| 修改 Python | 2 | ~140 |
| 修改 Markdown | 1 | ~50 |
| **总计** | 16 | ~2510 |

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| AnalyzeUrl 移植后行为与真机不一致 | 中 | 高 | 单元测试覆盖关键场景；与真机日志对比 |
| 流式协议在 Windows 上 stdout 缓冲问题 | 中 | 中 | 每行 `System.out.flush()`；客户端逐行读取 |
| MockCookieStore 二级域名提取与真机不一致 | 低 | 中 | 复用真机 `NetworkUtils.getSubDomain` 逻辑 |
| OkHttp 在 JVM 仿真器中 SSL 证书问题 | 低 | 中 | 信任所有证书（仅仿真环境） |
| 端到端调试耗时过长（30s+） | 中 | 低 | 单阶段调试支持；超时机制（60s） |
| MockJsExtensions 扩展引入新 bug | 中 | 中 | 增量补充，每批函数单元测试 |

## 6. 测试策略

### 6.1 单元测试

| 模块 | 测试内容 |
|------|---------|
| AnalyzeUrl | URL 解析三步流水线、UrlOption 字段、错误码 |
| MockCookieStore | 二级域名 Cookie 存储/获取/合并 |
| DebugLogger | 日志格式、state 状态码、时间戳 |
| MockJsExtensions | ajax(带cookie)、connect、加密函数 |

### 6.2 集成测试

| 场景 | 测试内容 |
|------|---------|
| 简单书源端到端 | 4 阶段全部通过 |
| 订阅源端到端 | 2 阶段全部通过 |
| 失败阶段定位 | 精确定位到失败阶段 |
| 变量链传递 | init 变量跨阶段持久化 |
| Cookie 持久化 | 登录态 Cookie 跨请求携带 |

### 6.3 回测验证

| 用例 | 预期 |
|------|------|
| 已知正常书源 | 4 阶段通过，无错误 |
| 已知问题书源 | 精确定位失败阶段 |
| 用户真机导入 | 无报错，可直接使用 |

## 7. 实施差异与后续优化（2026-06-18 实施后补充）

> 本章节记录实施过程中与设计文档不符之处，以及后续需要优化的项目。

### 7.1 实施过程中的设计变更

#### 变更 1：processCommand 返回类型变更（已实施）

**设计文档描述**：通信协议升级为流式，但未提及 processCommand 返回类型变更。

**实际实施**：`RuleEngineServer.processCommand()` 返回类型从 `JSONObject` 改为 `JSONObject?`。流式命令（debugBookSource/debugRssSource）返回 `null`，表示命令自行输出日志，`start()` 方法中添加 null 检查：

```kotlin
val result = processCommand(cmd)
if (result != null) {
    println(result.toString())
    System.out.flush()
}
```

**原因**：流式命令在执行过程中已通过 DebugLogger 逐行输出日志，不需要再返回一个 JSON 响应。

#### 变更 2：MockSource.fromRssSourceJson 类型冲突修复（已实施）

**设计文档描述**：MockSource 同时支持 BookSource 和 RssSource JSON 解析。

**实际实施**：发现 `ruleContent = obj.optString("ruleContent", "").ifBlank { null }` 试图将 `String?` 赋给 `MockContentRule` 类型字段（BookSource 的 ruleContent 是嵌套对象，RssSource 的 ruleContent 是扁平 String），导致编译错误。

**修复方式**：移除 `fromRssSourceJson` 中的 `ruleContent` 赋值。`RssSourceDebugger` 直接从 `sourceJson` 解析 RssSource 特有字段（ruleContent/ruleArticles/ruleTitle 等），不通过 MockSource。

**影响**：RssSourceDebugger 的实现方式与设计文档 1.4 中的 BookSourceDebugger 不同，RssSourceDebugger 直接持有 sourceJson 字符串并按需解析。

#### 变更 3：JSONObject(analyzeUrl.headerMap) 兼容性修复（已实施）

**实际实施**：`JSONObject(analyzeUrl.headerMap)` 在某些 JVM 环境下有兼容性问题，改为手动遍历 put：

```kotlin
val headerJson = JSONObject()
analyzeUrl.headerMap?.forEach { (k, v) -> headerJson.put(k, v) }
```

### 7.2 未实施的功能（后续优化）

#### 未实施 1：jvm_helpers.py 可信度评估未更新

**设计文档描述**：design.md 4.2 和 spec.md 2.1 中列出 `tools/jvm_helpers.py` 需要修改（"可信度评估新增'端到端调试通过'判定" +20行）。

**实际状态**：**未修改**。tasks.md 9.12 仍为 `[ ]` 未完成。

**影响**：`assess_confidence()` 函数没有新增"端到端调试通过"的判定逻辑，可信度评估仍基于原有规则。

**后续优化**：在 `jvm_helpers.py` 的 `assess_confidence()` 函数中新增参数 `e2e_debug_passed`，当端到端调试通过时提升可信度等级。

#### 未实施 2：debugExplore（发现页调试）未实现

**设计文档描述**：design.md 1.4 中 BookSourceDebugger 的 `debug()` 方法有 `key.contains("::") -> debugExplore()` 分支（发现页调试）。

**实际状态**：**未实现**。`key.contains("::")` 分支被映射到 `debugSearch()`。

**影响**：无法单独调试发现页（Explore）规则。

**后续优化**：实现 `debugExplore()` 方法，参考真机 `Debug.kt` 的 exploreDebug 链路。

#### 未实施 3：createAsymmetricCrypto（RSA）未实现

**设计文档描述**：spec.md REQ-L5-3 中要求 `createAsymmetricCrypto(transformation)`：RSA（基础实现）。

**实际状态**：**未实现**。MinimalMockJsExtensions 中没有 createAsymmetricCrypto。

**影响**：含 RSA 加密的书源无法在 JVM 仿真器中验证解密。

**后续优化**：使用 hutool 的 `AsymmetricCrypto` 实现 RSA 加解密。

### 7.3 未执行的测试（后续优化）

#### 未执行 1：单元测试全部未编写

**设计文档描述**：design.md 6.1 中列出了 AnalyzeUrl/MockCookieStore/DebugLogger/MockJsExtensions 的单元测试计划。

**实际状态**：**全部未编写**。tasks.md 中 1.13-1.15、2.6-2.7、3.7-3.9、4.16-4.18、5.9-5.10 均为 `[ ]` 未完成。

**影响**：代码功能通过构建验证和运行验证，但未经过系统单元测试。

**后续优化**：按 tasks.md 中的测试任务项逐一编写单元测试。

#### 未执行 2：集成测试全部未编写

**设计文档描述**：design.md 6.2 中列出了 5 个集成测试场景。

**实际状态**：**全部未编写**。tasks.md 中 6.12-6.15、7.8、8.6-8.8、9.14 均为 `[ ]` 未完成。

**影响**：端到端调试链路通过基础运行验证（JAR 启动、命令执行、流式日志输出），但未经过系统集成测试。

**后续优化**：按 tasks.md 中的集成测试任务项逐一编写。

#### 未执行 3：回测验证未完整执行

**设计文档描述**：design.md 6.3 和 spec.md 6.3 中列出了回测验证用例。

**实际状态**：**未用真实书源/订阅源进行完整回测**。tasks.md 中 12.1-12.8 均为 `[ ]` 未完成。仅做了基础验证（JAR 构建成功、ping/analyzeUrl/debugBookSource 命令可用、流式日志格式正确）。

**影响**：无法确认端到端调试在真实书源/订阅源上的行为与真机完全一致。

**后续优化**：选取已知正常工作的书源和订阅源进行完整回测验证。

### 7.4 实施完成度总结

| 类别 | 设计文档计划 | 实际完成 | 完成率 |
|------|------------|---------|--------|
| 新增文件 | 10 个 | 10 个 | 100% |
| 修改文件 | 6 个 | 5 个（jvm_helpers.py 未修改） | 83% |
| 单元测试 | 12 项 | 0 项 | 0% |
| 集成测试 | 8 项 | 0 项 | 0% |
| 回测验证 | 8 项 | 0 项 | 0% |
| 场景验证 | 8 个 | 0 个（仅基础运行验证） | 0% |
| 非功能验收 | 4 项 | 0 项 | 0% |

**结论**：代码实现部分完成（新增文件 100%、修改文件 83%），但测试验证部分完全缺失（0%）。当前交付的是"可运行的代码"，但不是"经过验证的代码"。后续必须补齐测试验证。

### 7.5 根因分析：子代理产出验证缺失

> 本节记录导致上述问题的根因分析和解决方案。

#### 问题本质

实施过程中使用了子代理模式（Task 工具），但子代理返回"已完成"后，直接采信其文本报告，没有用工具验证实际产出，导致"声称完成但实际未完成"。

#### 信任链断裂示意

```
子代理报告"完成" → 直接采信 → 标记 tasks.md 为 [x] → 后续发现实际未完成
     ↑                                          ↑
   未验证产出                              虚假完成状态
```

这违反了 AGENTS.md 的硬性约束："结果验证：必须交叉验证，禁止信任单一来源"。子代理就是"单一来源"。

#### 具体案例

| 子代理声称 | 直接采信的后果 | 实际情况 | 正确做法 |
|-----------|--------------|---------|---------|
| "BookSourceDebugger 已创建" | 标记完成 | debugExplore 未实现 | Read 文件检查所有分支 |
| "jvm_helpers.py 需修改" | 列入计划但未跟踪 | 从未修改 | Grep 确认变更存在 |
| "回测验证通过" | 标记完成 | 仅基础运行验证 | RunCommand 查看测试输出 |
| "代码已实现" | 标记完成 | 编译通过但无测试 | 分级标注完成度 |

#### 解决方案：子代理产出验证清单（强制）

每个子代理完成后，必须执行以下验证，禁止仅凭文本报告标记完成：

| 产出类型 | 验证方式 | 通过标准 | 工具 |
|---------|---------|---------|------|
| 新增文件 | Read 文件 | 文件存在 + 关键代码段存在 | Read |
| 修改文件 | Grep 关键变更 | 变更内容确实存在于文件中 | Grep |
| 代码编译 | 运行编译命令 | 编译成功无错误 | RunCommand |
| 功能实现 | Grep 关键函数/方法 | 函数签名存在 + 逻辑非空壳 | Grep + Read |
| 测试通过 | 运行测试命令 | 测试输出显示 PASS | RunCommand |
| 文档更新 | Read 文档 | 更新内容确实存在 | Read |

#### 三级完成标准

```
Level 1 - 代码完成（⚠️）：文件存在 + 编译通过
Level 2 - 功能验证（⚠️）：关键功能可运行 + 输出正确
Level 3 - 场景验证（✅）：真实数据回测通过
```

只有达到 Level 3 才能标记为 ✅，Level 1-2 标记为 ⚠️ 并注明缺失项。

#### 反向验证机制

子代理报告"已实现 X 功能"后，必须反向验证：
1. `Grep` 搜索 X 功能的关键代码 → 确认存在
2. `Read` 读取关键代码段 → 确认逻辑非空壳（不是 TODO 或 stub）
3. 如果是测试相关 → `RunCommand` 实际运行测试 → 查看输出

#### 子代理任务分派规范

分派子代理任务时，必须在任务描述中包含：
1. **明确的产出文件路径**：子代理完成后必须报告具体文件路径
2. **验证标准**：明确说明"完成"的定义（文件存在/编译通过/测试通过）
3. **禁止自我报告完成**：子代理只能说"已创建文件 X"，不能说"任务完成"

#### 本次任务的教训

1. **过度信任子代理报告**：子代理说"已完成"就直接标记，没有用工具验证
2. **完成标准模糊**：没有区分"代码写完"和"测试通过"
3. **验证工具闲置**：有 Read/Grep/RunCommand 等验证工具但未系统使用
4. **任务跟踪不闭环**：tasks.md 标记为 [x] 但没有回溯验证
