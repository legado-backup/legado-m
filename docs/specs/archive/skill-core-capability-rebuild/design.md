# Design: Skill 核心能力重建

## 统一设计理念

### 理念 1：JAR=核心服务，Python=客户端（核心理念）

JAR 仿真服务端必须实现开源阅读核心服务功能，Python 客户端必须实现开源阅读客户端功能。

**落地原则**：
- JAR 实现：WebBook（书源管理）+ Rss（订阅源管理）+ Debug（调试）+ CheckSource（校验）
- Python 实现：调用 JAR + WebView 渲染 + 用户交互 + 经验管理 + 报告生成
- 通信协议：stdin/stdout JSON 行协议（保持现有）
- 禁止 Python 重复实现 JAR 已有能力

### 理念 2：异步高性能（解决卡顿根因）

JAR 仿真服务端必须从"同步阻塞"进化为"异步高性能"。

**落地原则**（基于源码核实，2026-06-20）：
- 同步 execute → 异步 enqueue + suspendCancellableCoroutine（OkHttpUtils.kt:52 确认存在同步 execute）
- JS 编译缓存上限从 16 提升到 64（AnalyzeRule.kt:862 确认 `getOrPutLimit(jsStr, 16)`，真机也是16，提升到64是优化而非对齐）
- ajax 超时从 30 秒降低到 15 秒+可配置（JsExtensionsStub.kt:76 确认 timeout=30000）
- JsExtensionsStub 单例化（当前是普通 class，非 object，确认存在。仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机中 AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层）
- OkHttp 连接池复用（OkHttpUtils.kt 确认无连接池配置）

**已核实不存在的伪问题**（设计文档原描述错误，已删除）：
- ~~runBlocking 阻塞~~：BookSourceDebugger.kt/RssSourceDebugger.kt 实际无 runBlocking，是同步 try-catch
- ~~30 秒 OkHttp 超时~~：OkHttpUtils.kt 无超时配置，30 秒在 JsExtensionsStub.ajax 方法中

### 理念 3：保真度优先（补全 38 个 Stub）

JAR 仿真服务端保真度从 89% 提升到 95%+。

**落地原则**（基于源码核实，2026-06-20）：
- 优先补全高频方法
- 修复 ajax 委托走 Jsoup.connect（JsExtensionsStub.kt:64/67 确认）
- 修复 evalJS 上下文注入不完整（RuleEngineServer.kt:134 方法定义，L137-145 上下文注入，确认 source=null, baseUrl=""）
- 修复 CacheManagerStub 无 LRU（CacheManagerStub.kt:18 确认 ConcurrentHashMap 无淘汰）
- 补全 base64Decode flags 支持（JsExtensionsStub.kt:512 确认 flags 简化处理）

**已核实不存在的伪问题**（设计文档原描述错误，已删除）：
- ~~getSubDomain 不剥离 www~~：NetworkUtilsStub.kt:192 已剥离 www 前缀
- ~~TextUtils.isEmpty 替换为 isNullOrBlank~~：AnalyzeRule.kt 已使用 isNullOrEmpty

### 理念 4：Python 客户端工程化

Python 客户端从"1236 行上帝脚本"进化为"工程化包结构"。

**落地原则**：
- 虚拟环境管理：requirements.txt + venv 激活脚本
- 包结构：legado_client/ 包 + __init__.py + 模块化
- 层级设计：客户端层/分析层/经验层/工具层
- 类型注解：全量 type hints
- 拆分 debug-source.py：1236 行 → 多个模块

### 理念 5：孤儿模块真正集成

4 个代码完整但未被 import 的"孤儿模块"必须真正集成到 debug-source.py。

**落地原则**（基于源码核实，2026-06-20）：
- confidence_evaluator.py（112行）：完整实现可信度评分逻辑，但未被 import
- user_interaction_handler.py（140行）：完整实现 4 种错误场景处理+自检代码，但未被 import
- source_navigation.py（84行）：完整实现错误→源码映射+自检代码，但未被 import
- parse_strategy_selector.py（131行）：完整实现解析策略选择+自检代码，但未被 import
- **核实结论**：这 4 个脚本不是"空架子"（有完整实现），而是"孤儿模块"（无人调用）
- **修复方案**：在 debug-source.py 中 import 并调用这 4 个模块

### 理念 6：经验知识闭环

经验知识层必须实现自动检索/写入/冲突解决。

**落地原则**：
- 测试前自动检索相似案例
- 测试后自动写入新经验
- 经验去重+质量评估
- 经验冲突解决

### 理念 7：禁止懒原则

所有任务必须真正实现，禁止 YAGNI 跳过核心功能。

**落地原则**：
- 每个任务必须有源码行号引用+验证方法
- 验收标准必须可执行
- 修复 6 项虚假完成项

---

## 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                    经验知识层（理解大脑）                                │
│  references/ + basic-memory + experience_manager.py                    │
│  自动检索 → 自动写入 → 冲突解决 → 质量评估                               │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕
┌──────────────────────────────────────────────────────────────────────┐
│                    Python 客户端层（测试双手）                            │
│  legado_client/ 包结构                                                  │
│  ├── client/    （RuleEngineClient + WebViewHandler + UserInteraction） │
│  ├── analyzer/  （ErrorDiagnoser + HtmlStructureAnalyzer + Confidence）  │
│  ├── experience/（ExperienceManager + ConflictResolver）                │
│  └── utils/     （Config + Logger + FileUtils）                          │
│  debug-source.py（入口脚本，< 200 行）                                    │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ stdin/stdout JSON
┌──────────────────────────────────────────────────────────────────────┐
│                    JAR 仿真服务端层（核心能力底座）                        │
│  legado-jvm.jar（单 JAR，非 4 个）                                       │
│  ├── RuleEngineServer（通信协议+命令分发）                                │
│  ├── WebBookDebugger（书源管理：搜索/发现/详情/目录/正文）                  │
│  ├── RssSourceDebugger（订阅源管理：列表/内容/singleUrl）                  │
│  ├── CheckSourceDebugger（校验：域名→搜索→发现→详情→目录→正文）            │
│  ├── AnalyzeUrl + AnalyzeRule（规则引擎核心）                             │
│  ├── JsExtensionsStub（JS 扩展函数，86 完整+38 补全）                      │
│  └── CacheManager + CookieStore + NetworkUtils（基础设施）               │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ 仅在 JAR 无法覆盖时回查
┌──────────────────────────────────────────────────────────────────────┐
│                    开源阅读源码层（最后兜底保障）                           │
│  app/src/main/java/io/legado/app/                                       │
│  WebBook.kt + Rss.kt + Debug.kt + CheckSource.kt + JsExtensions.kt     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 方向 1：JAR 仿真服务端架构重构（P0）

### 1.1 问题根因（4 大卡顿根因，基于源码核实 2026-06-20）

> **核实说明**：原设计文档列 6 大根因，经源码核实后删除 2 个伪问题（runBlocking、30秒OkHttp超时），保留 4 个真实问题。

#### 根因 1：同步 execute 替代异步 enqueue

**源码位置**：OkHttpUtils.kt:52（`suspend fun Call.await(): Response = execute()`，已核实无连接池配置、无超时配置，使用 OkHttpClient 默认值）

**真机行为**（WebBook.kt）：
```kotlin
// 真机使用 Coroutine.async{}...onSuccess{}链式封装
Coroutine.async {
    // 异步执行
}.onSuccess { result ->
    // 成功回调
}.onError { error ->
    // 错误回调
}
```

**仿真器行为**（OkHttpUtils.kt:52，已核实）：
```kotlin
// 注释确认："用同步 execute() 代替异步 enqueue + suspendCancellableCoroutine"
suspend fun Call.await(): Response {
    return execute()  // 同步阻塞
}
```

**修复方案**：
```kotlin
// 修复后：使用 suspendCancellableCoroutine + enqueue
suspend fun Call.await(): Response = suspendCancellableCoroutine { cont ->
    enqueue(object : Callback {
        override fun onResponse(call: Call, response: Response) {
            cont.resume(response)
        }
        override fun onFailure(call: Call, e: IOException) {
            cont.resumeWithException(e)
        }
    })
}
```

#### 根因 2：JS 编译缓存上限 16

**源码位置**：AnalyzeRule.kt:81（`private val scriptCache = hashMapOf<String, CompiledScript>()`）+ 第862行（`getOrPutLimit(jsStr, 16)`）

**真机行为**：scriptCache 上限 16（AnalyzeRule.kt:862 确认，真机也是16）
**仿真器行为**：scriptCache 上限 16（与真机一致，但16偏小导致频繁编译）

**修复方案**（优化提升，非对齐真机）：
```kotlin
// 修复后：提升到 64（真机也是16，但16偏小影响性能，提升到64是优化）
private val scriptCache = LinkedHashMap<String, Script>(64, 0.75f, true)
```

#### 根因 3：JsExtensionsStub 每次创建新实例

> **第三轮深度核实更正**（2026-06-20）：真机中**不存在 JsExtensionsStub**。AnalyzeRule 和 AnalyzeUrl 直接 `implements JsExtensions`（AnalyzeRule.kt:57, AnalyzeUrl.kt:81），通过 override 实现抽象方法。JsExtensionsStub 是仿真器中的 Stub 实现，由仿真器的 AnalyzeRule/AnalyzeUrl 内部创建。

**源码位置**：
- JsExtensionsStub.kt:48（`class JsExtensionsStub(...)` 是普通类，非 object）
- 仿真器中 JsExtensionsStub 由 AnalyzeRule/AnalyzeUrl 内部创建（非 BookSourceDebugger/RssSourceDebugger 直接创建）

**真机行为**：AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层
**仿真器行为**：JsExtensionsStub 是普通 class，每次 AnalyzeRule/AnalyzeUrl 初始化时创建新实例

**修复方案**：
```kotlin
// 修复后：单例化（需处理 source/ruleData 参数注入）
object JsExtensionsStub : JsExtensionsInterface {
    @Volatile var source: Any? = null
    @Volatile var ruleData: RuleDataInterface = RuleData()
    // 单例实现
}

// AnalyzeRule/AnalyzeUrl 中使用单例引用
val jsExtensions = JsExtensionsStub  // 单例引用
JsExtensionsStub.source = source     // 注入 source
JsExtensionsStub.ruleData = ruleData // 注入 ruleData
```

#### 根因 4：无 OkHttp 连接池复用

**源码位置**：OkHttpUtils.kt（已核实，无连接池配置）

**真机行为**：连接池保持 5 个连接
**仿真器行为**：每次请求新建连接

**修复方案**：
```kotlin
// 修复后：配置连接池
val connectionPool = ConnectionPool(5, 5, TimeUnit.MINUTES)
val okHttpClient = OkHttpClient.Builder()
    .connectionPool(connectionPool)
    .build()
```

### 1.2 修复方案汇总

| 根因 | 文件 | 修改行号 | 修改内容 |
|------|------|---------|---------|
| 同步 execute | OkHttpUtils.kt | 52 | 改为 enqueue + suspendCancellableCoroutine |
| JS 编译缓存 | AnalyzeRule.kt | 81/862 | 上限从 16 提升到 64（优化提升，非对齐真机） |
| Stub 实例化 | JsExtensionsStub.kt | 48 | class → object（仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机无 Stub 层） |
| 连接池 | OkHttpUtils.kt | - | 配置连接池 |

### 1.3 性能预期

| 指标 | 当前 | 目标 |
|------|------|------|
| 单源调试响应时间 | 30 秒+ | < 10 秒 |
| JS 编译次数 | 频繁 | 缓存命中 80%+ |
| 连接建立次数 | 每次新建 | 复用 5 个连接 |
| 内存占用 | 无限增长 | 软引用+手动清理 |

---

## 方向 2：JAR 仿真服务端保真度提升（P0）

> **核实说明**：原设计文档列 11 个修复项，经源码核实后删除 2 个已修复问题（getSubDomain、TextUtils.isEmpty），修正 2 个描述错误（evalJS、CacheManagerStub），保留 7 个真实问题。

### 2.1 evalJS 上下文注入修复

**源码位置**：RuleEngineServer.kt:134（evalJS 方法定义），L137-145（上下文注入）

**真机行为**（第三轮深度核实，2026-06-20）：

真机有 3 个 evalJS 实现，注入变量各不相同：

| 实现位置 | 注入变量数 | 注入变量列表 |
|---------|----------|------------|
| AnalyzeRule.kt:828 | **13个** | java/cookie/cache/source/book/result/baseUrl/chapter/title/src/nextChapterUrl/rssArticle/fromBookInfo |
| AnalyzeUrl.kt:364 | **12个** | java/baseUrl/cookie/cache/page/key/speakText/speakSpeed/book/source/result/infoMap |
| BaseSource.kt:325 | **5个** | java/source/baseUrl/cookie/cache |

**仿真器行为**（已核实，存在严重保真度缺陷）：
```kotlin
// RuleEngineServer.kt:134 方法定义，L137-145 仅注入 5 个变量：
bindings["java"] = JsExtensionsStub(null, RuleData())  // 缺陷1: source 参数为 null
bindings["cookie"] = CookieStoreStub
bindings["cache"] = CacheManagerStub
bindings["baseUrl"] = ""  // 缺陷2: baseUrl 为空字符串
bindings["result"] = contextVar  // 仅 result 有值
```

**仿真器缺失的关键变量**（JS 脚本中使用会报错或返回 undefined）：

| 缺失变量 | 真机注入位置 | 影响 |
|---------|------------|------|
| `source` | AnalyzeRule/AnalyzeUrl/BaseSource | JS 无法调用 source.login()、source.bookSourceUrl 等 |
| `book` | AnalyzeRule/AnalyzeUrl | JS 无法访问 book.title、book.author 等 |
| `chapter` | AnalyzeRule | JS 无法访问 chapter.url、chapter.title 等 |
| `title` | AnalyzeRule | JS 无法获取章节标题 |
| `src` | AnalyzeRule | JS 无法获取原始内容 |
| `nextChapterUrl` | AnalyzeRule | JS 无法获取下一章 URL |
| `rssArticle` | AnalyzeRule | JS 无法访问 RSS 文章信息 |
| `page` | AnalyzeUrl | JS 无法获取页码 |
| `key` | AnalyzeUrl | JS 无法获取搜索关键词 |
| `infoMap` | AnalyzeUrl | JS 无法访问信息映射 |

**修复方案**（分两阶段）：

**阶段1**（最小修复，解决 source 和 baseUrl）：
```kotlin
fun evalJS(js: String, source: BaseSource, result: Any?): Any? {
    val bindings = SimpleBindings()
    bindings["java"] = JsExtensionsStub(source, RuleData())  // 修复: 传入真实 source
    bindings["source"] = source
    bindings["baseUrl"] = source.bookSourceUrl  // 修复: 传入真实 baseUrl
    bindings["cookie"] = CookieStoreStub
    bindings["cache"] = CacheManagerStub
    bindings["result"] = result
    return scriptEngine.eval(js, bindings)
}
```

**阶段2**（完整修复，对齐 AnalyzeRule.evalJS 的 13 个变量）：
```kotlin
fun evalJS(js: String, source: BaseSource, result: Any?, book: BaseBook? = null,
           chapter: BookChapter? = null, baseUrl: String = "",
           content: Any? = null, nextChapterUrl: String? = null,
           rssArticle: RssArticle? = null, isFromBookInfo: Boolean = false): Any? {
    val bindings = SimpleBindings()
    bindings["java"] = JsExtensionsStub(source, RuleData())
    bindings["source"] = source
    bindings["baseUrl"] = baseUrl.ifBlank { source.bookSourceUrl }
    bindings["cookie"] = CookieStoreStub
    bindings["cache"] = CacheManagerStub
    bindings["result"] = result
    bindings["book"] = book
    bindings["chapter"] = chapter
    bindings["title"] = chapter?.title
    bindings["src"] = content
    bindings["nextChapterUrl"] = nextChapterUrl
    bindings["rssArticle"] = rssArticle
    bindings["fromBookInfo"] = isFromBookInfo
    return scriptEngine.eval(js, bindings)
}
```

### 2.2 ajax 委托修复

**源码位置**：JsExtensionsStub.kt:64/67（已核实，第66行是注释）

**真机行为**：走 AnalyzeUrl 自身（支持 URL 模板/Cookie/请求体编码）
**仿真器行为**：走 JsExtensionsStub.ajax（Jsoup.connect 简化请求）

**修复方案**：
```kotlin
// 修复后：AnalyzeUrl override ajax 方法
class AnalyzeUrl {
    fun ajax(url: String): String {
        // 委托 AnalyzeUrl 自身构造请求，而非走 JsExtensionsStub.ajax
        val analyzeUrl = AnalyzeUrl(url, source = source, baseUrl = baseUrl)
        return analyzeUrl.getStrResponse()
    }
}
```

### 2.3 aesEncodeToString 评估

**源码位置**：JsExtensionsStub.kt:874（已核实，第872行是注释）

**真机行为**：调用 decryptStr（真机 bug）
**仿真器行为**：调用 encrypt（修复了 bug）

**修复方案**：保持与真机一致（调用 decryptStr），记录为已知限制

### 2.4 HTTP 方法补全

**源码位置**：OkHttpUtils.kt（已核实）

**真机行为**：cookieJarHeader/限流/SSL/ensureActive/AnalyzeUrl
**仿真器行为**：全部走 Jsoup.connect

**修复方案**：补全 HTTP 方法支持（cookieJar/限流/SSL）

### 2.5 BaseSource 方法补全

**源码位置**：BaseSource.kt（真机文件名是 BaseSource.kt，非 BaseSourceInterface.kt；仿真器中为 BaseSourceInterface.kt）

**真机行为**：`interface BaseSource : JsExtensions`（第33行），继承 JsExtensions+JsEncodeUtils 合计约 150+ 方法（非 77+）
**仿真器行为**：仅 7 属性+3 方法

**修复方案**：补全 source.login/evalJS 等高频方法

### 2.6 base64Decode flags 补全

**源码位置**：JsExtensionsStub.kt:512（已核实，第511行是注释）

**真机行为**：支持 URL_SAFE/CRLF/NO_PADDING/NO_WRAP
**仿真器行为**：仅处理 flag 8

**修复方案**：
```kotlin
// 修复后：补全 flags 支持
fun base64Decode(str: String, flags: Int): String {
    val decodeFlags = when {
        flags and 8 != 0 -> Base64.URL_SAFE
        flags and 1 != 0 -> Base64.NO_PADDING
        flags and 2 != 0 -> Base64.NO_WRAP
        flags and 4 != 0 -> Base64.CRLF
        else -> Base64.DEFAULT
    }
    return String(Base64.decode(str, decodeFlags))
}
```

### 2.7 CacheManagerStub LRU 修复

**源码位置**：CacheManagerStub.kt:18（已核实）

**真机行为**：LruCache(50M)，queryTTFMap 为 LruCache 上限 4
**仿真器行为**：无限 ConcurrentHashMap（已核实，第18行 `ConcurrentHashMap<String, Any>()`），无 LRU 淘汰

**第三轮深度核实补充**（2026-06-20）：CacheManagerStub 实际使用 5 个 ConcurrentHashMap：

| 字段 | 行号 | 仿真器类型 | 真机对应 | 差异 |
|------|------|----------|---------|------|
| memoryCache | L18 | ConcurrentHashMap<String, Any> | memoryLruCache | 无 LRU 淘汰 |
| diskCache | L21 | ConcurrentHashMap<String, PersistentEntry> | appDb.cacheDao | 无持久化 |
| byteArrayCache | L24 | ConcurrentHashMap<String, ByteArray> | ACache.getAsBinary | 无 LRU 淘汰 |
| fileCache | L27 | ConcurrentHashMap<String, String> | ACache.getAsString | 无 LRU 淘汰 |
| queryTTFMap | L30 | ConcurrentHashMap<String, QueryTTF> | **LruCache 上限 4** | **无上限，差异最大** |

**修复方案**（注意：CacheManagerStub 已是 object 单例，只需添加 LRU）：
```kotlin
// 修复后：添加软引用（保持 object 单例）
object CacheManagerStub : CacheManagerInterface {
    private val cache = ConcurrentHashMap<String, SoftReference<Any>>()
    // 修复 queryTTFMap：对齐真机 LruCache 上限 4
    private val queryTTFMap = object : LinkedHashMap<String, QueryTTF>(4, 0.75f, true) {
        override fun removeEldestEntry(eldest: Map.Entry<String, QueryTTF>): Boolean {
            return size > 4  // 真机上限 4
        }
    }

    fun get(key: String): Any? {
        return cache[key]?.get()
    }

    fun put(key: String, value: Any) {
        cache[key] = SoftReference(value)
    }
}
```

### 2.8 androidId 修复

**源码位置**：JsExtensionsStub.kt:748（已核实，第747行是注释）

**真机行为**：从 AppConst.androidId 读取
**仿真器行为**：返回"000000000000000"

**修复方案**：可配置的 androidId（从环境变量或配置文件读取）

### 2.9 高频 Stub 方法补全

**38 个 Stub 方法补全优先级**（基于 JsExtensionsStub.kt 源码核实）：

| 优先级 | 方法 | 真机行为 | 仿真器当前行为 | 修复方案 |
|--------|------|---------|--------------|---------|
| P0 | ajax | AnalyzeUrl 自身 | Jsoup.connect（:64/67） | AnalyzeUrl override |
| P0 | connect | AnalyzeUrl 自身 | Jsoup.connect（:114/116/119） | AnalyzeUrl override |
| P0 | get/post/head | OkHttp 完整 | 移除限流和CookieJar（:133/137） | OkHttp 补全 |
| P0 | base64Decode | 完整 flags | flags 简化（:512） | 补全 flags |
| P0 | getCookie | CookieStore 持久化 | CookieStoreStub 内存（:294/297） | 持久化 |
| P0 | cacheFile | CacheManager 持久化 | CacheManagerStub 内存（:317/320） | 持久化 |
| P0 | importScript | 文件读取 | Jsoup.connect（:308） | 文件读取实现 |
| P0 | queryTTF | TTF 解析 | CacheManagerStub（:623） | TTF 解析实现 |
| P0 | replaceFont | 字体替换 | toCharArray（:668/697） | toStringArray 抽取 |
| P1 | readTxtFile | EncodingDetect | 固定 UTF-8（:389） | EncodingDetect 抽取 |
| P1 | unArchiveFile | ArchiveUtils | 返回空（:417） | ArchiveUtils 抽取 |
| P1 | htmlFormat | HtmlFormatter | 返回原始（:600） | HtmlFormatter 抽取 |
| P1 | t2s/s2t | ChineseUtils | 返回原始（:605/609） | ChineseUtils 抽取 |
| P1 | toNumChapter | AppPattern | 返回原始（:708） | AppPattern 抽取 |
| P1 | getReadBookConfig | ReadBookConfig | 返回空JSON（:768） | 配置文件读取 |
| P1 | getThemeMode | AppConfig | 返回默认值（:777） | 配置文件读取 |

### 2.10 不可用方法异常类型（第三轮深度核实，2026-06-20）

**8 个不可用方法**（纯 UI 交互，仿真器无法实现）抛出 **3 种异常类型**（非仅 UnsupportedOperationException）：

| 异常类型 | 方法 | 行号 | 说明 |
|---------|------|------|------|
| **WebViewRequiredException** | webView(html,url,js,cacheFirst) | L179 | 需要 WebView 渲染 |
| **WebViewRequiredException** | webViewGetSource(...,delayTime) | L201 | 需要 WebView 获取源码 |
| **WebViewRequiredException** | webViewGetOverrideUrl(...,delayTime) | L230 | 需要 WebView 拦截 URL |
| **UnsupportedOperationException** | openVideoPlayer(url,title,isFloat) | L256 | 需要 Android 视频播放器 |
| **UnsupportedOperationException** | openUrl(url,mimeType) | L761 | 需要 Android Intent |
| **UserInterventionException** | startBrowser(url,title,html) | L263 | 需要用户手动操作浏览器 |
| **UserInterventionException** | startBrowserAwait(...,html) | L277 | 需要用户手动操作浏览器 |
| **UserInterventionException** | getVerificationCode(imageUrl) | L285 | 需要用户手动输入验证码 |

**设计含义**：
- `WebViewRequiredException`（3个）：需要 WebView 支持（方向 4 已规划 Selenium 回退）
- `UserInterventionException`（3个）：需要用户手动干预（Python 客户端方向 6 已规划交互处理）
- `UnsupportedOperationException`（2个）：纯 Android 功能，无法仿真

---

## 方向 3：Python 客户端工程化重构（P0）

### 3.1 虚拟环境管理

**创建文件**：
- `scripts/requirements.txt`：声明所有依赖
- `scripts/setup_venv.bat`：Windows 虚拟环境激活脚本
- `scripts/setup_venv.sh`：Linux 虚拟环境激活脚本
- `scripts/.gitignore`：忽略 venv/

**requirements.txt 内容**：
```
requests>=2.28.0
selenium>=4.0.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
psutil>=5.9.0
```

**setup_venv.bat 内容**：
```batch
@echo off
echo Creating virtual environment...
python -m venv venv
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt
echo Virtual environment setup complete.
```

### 3.2 包结构设计

**目标结构**：
```
.trae/skills/legado-source-creator/scripts/
├── legado_client/               # Python 包
│   ├── __init__.py              # 包初始化
│   ├── client/                  # 客户端层
│   │   ├── __init__.py
│   │   ├── rule_engine_client.py    # JAR 通信客户端
│   │   ├── webview_handler.py       # WebView 渲染
│   │   └── user_interaction.py      # 用户交互
│   ├── analyzer/                # 分析层
│   │   ├── __init__.py
│   │   ├── error_diagnoser.py       # 错误诊断
│   │   ├── html_structure.py        # HTML 结构分析
│   │   ├── confidence_evaluator.py  # 可信度评估
│   │   └── parse_strategy.py        # 解析策略选择
│   ├── experience/              # 经验层
│   │   ├── __init__.py
│   │   ├── experience_manager.py    # 经验管理
│   │   └── conflict_resolver.py     # 冲突解决
│   └── utils/                   # 工具层
│       ├── __init__.py
│       ├── config.py                # 配置管理
│       ├── logger.py                # 日志
│       └── file_utils.py            # 文件工具
├── debug-source.py              # 入口脚本（< 200 行）
├── requirements.txt
└── setup_venv.bat
```

### 3.3 拆分 debug-source.py

**当前状态**：1236 行上帝脚本，17 个 try/except ImportError 块，12 处 json.loads（已核实）

**拆分原则**：
- debug-source.py：仅处理命令行参数解析+调用 legado_client（< 200 行）
- client/rule_engine_client.py：JAR 通信逻辑
- analyzer/error_diagnoser.py：错误诊断逻辑
- analyzer/html_structure.py：HTML 结构分析逻辑
- experience/experience_manager.py：经验管理逻辑

**拆分后的 debug-source.py 结构**：
```python
#!/usr/bin/env python3
"""Legado 书源/订阅源调试入口脚本"""

import argparse
import sys
from legado_client.client.rule_engine_client import RuleEngineClient
from legado_client.analyzer.error_diagnoser import ErrorDiagnoser
from legado_client.experience.experience_manager import ExperienceManager

def main():
    parser = argparse.ArgumentParser(description="Legado 书源/订阅源调试")
    parser.add_argument("--source", required=True, help="书源/订阅源 JSON 文件")
    parser.add_argument("--output", help="输出报告 JSON 文件")
    parser.add_argument("--timeout", type=int, default=15, help="JVM 调试超时（秒）")
    args = parser.parse_args()

    # 解析源 JSON（只解析一次）
    source_obj = load_source(args.source)

    # 调用 legado_client 包
    client = RuleEngineClient(timeout=args.timeout)
    result = client.debug_book_source(source_obj)

    # 错误诊断
    if not result.success:
        diagnoser = ErrorDiagnoser()
        diagnosis = diagnoser.diagnose(result.error)
        result.error_diagnosis = diagnosis

    # 经验管理
    exp_manager = ExperienceManager()
    exp_manager.write_experience(result)

    # 输出报告
    if args.output:
        export_report(result, args.output)

if __name__ == "__main__":
    main()
```

### 3.4 类型注解

**全量 type hints**（Python 3.8+）：
```python
from typing import Optional, List, Dict, Any

class RuleEngineClient:
    def __init__(self, jar_path: str, timeout: int = 15) -> None:
        self.jar_path: str = jar_path
        self.timeout: int = timeout
        self.process: Optional[subprocess.Popen] = None

    def debug_book_source(self, source: Dict[str, Any]) -> DebugResult:
        ...
```

### 3.5 JSON 去重

**当前问题**：12 处 json.loads(source_json) 重复解析（已核实）

**修复方案**：main() 入口解析一次 source_obj，后续传递对象
```python
def main():
    # 只解析一次
    source_obj = json.loads(source_json)
    # 后续传递对象
    result = client.debug_book_source(source_obj)
```

---

## 方向 4：4 个孤儿模块真正集成（P0）

> **核实说明**：原设计文档称这4个脚本为"空架子"，经源码核实后确认它们都是完整实现，只是未被任何代码 import（孤儿模块）。修复方案从"实现逻辑"改为"import 集成"。

### 4.1 confidence_evaluator.py 集成

**当前状态**（已核实，112行）：完整实现可信度评分逻辑，有类常量 RULE_TYPE_CONFIDENCE（4种规则类型评分）和 FIDELITY_PENALTY（4种保真度扣减），但未被 debug-source.py import

**集成方案**：
```python
# debug-source.py 新增 import
from confidence_evaluator import evaluate_confidence

# 调试完成后调用
confidence = evaluate_confidence(source_json, test_result)
result["confidence"] = confidence
```

### 4.2 user_interaction_handler.py 集成

**当前状态**（已核实，140行）：完整实现 4 种错误场景处理（url_unreachable/login_required/captcha/cf_protection）+ 自检代码，但未被 debug-source.py import

**集成方案**：
```python
# debug-source.py 新增 import
from user_interaction_handler import create_interaction_request

# 错误处理时调用
if needs_user_intervention:
    interaction = create_interaction_request(source_json, error_type, error_msg)
```

### 4.3 source_navigation.py 集成

**当前状态**（已核实，84行）：完整实现错误→源码映射（6种错误类型）+ 自检代码，但未被 debug-source.py import

**集成方案**：
```python
# debug-source.py 新增 import
from source_navigation import navigate_to_source

# 错误诊断时调用
if error_type:
    navigation = navigate_to_source(error_type)
```

### 4.4 parse_strategy_selector.py 集成

**当前状态**（已核实，131行）：完整实现解析策略选择（决策树+HTML推断）+ 自检代码，但未被 debug-source.py import

**集成方案**：
```python
# debug-source.py 新增 import
from parse_strategy_selector import select_parse_strategy

# 规则构建时调用
strategy = select_parse_strategy(site_analysis)
```

---

## 方向 5：JAR 仿真服务端核心功能完善（P1）

> **核实说明**：原设计文档列 5 个完善项，经源码核实后删除 3 个已修复问题（state码、singleUrl、相对路径），修正 1 个描述错误（state码语义），保留 2 个真实缺失。
>
> **第三轮深度核实更正**（2026-06-20）：
> - **state码语义对齐是伪问题**：真机 Debug.kt 也使用 10/20/30/40！state=10 在 BookList.kt:54/RssParserByRule.kt:37（列表页HTML），state=20 在 BookInfo.kt:40/Rss.kt:135（详情页HTML），state=30 在 BookChapterList.kt:49（目录页HTML），state=40 在 BookContent.kt:52（正文页HTML）。仿真端使用 10/20/30/40 **与真机一致**，无需修改。
> - **Debug.kt 实际有 7 个 state 码**（非 3 个）：1（默认）、-1（错误）、1000（完成）、10（列表页HTML）、20（详情页HTML）、30（目录页HTML）、40（正文页HTML）。

### 5.1 CheckSource 校验流程

**真机源码**：CheckSource.kt（74行，已核实）— 配置管理入口，实际校验逻辑在 CheckSourceService 中

**仿真器现状**：无 CheckSource 对应实现，不支持批量校验和配置管理

**修复方案**：新增 CheckSourceDebugger.kt
```kotlin
class CheckSourceDebugger {
    fun check(source: BookSource): CheckResult {
        val result = CheckResult()
        // 域名检查
        result.domain = checkDomain(source)
        // 搜索检查
        result.search = checkSearch(source)
        // 发现检查
        result.explore = checkExplore(source)
        // 详情检查
        result.detail = checkDetail(source)
        // 目录检查
        result.toc = checkToc(source)
        // 正文检查
        result.content = checkContent(source)
        return result
    }
}
```

### 5.2 state 码语义对齐（已核实：伪问题，无需修改）

> **第三轮深度核实更正**（2026-06-20）：经源码逐行核实，**state码语义对齐是伪问题**。

**真机源码**：Debug.kt（382行）实际有 **7 个 state 码**（非 3 个）：

| state值 | 含义 | 真机使用位置 |
|---------|------|-------------|
| `1` | 默认日志 | Debug.kt:40（默认参数） |
| `-1` | 错误 | Debug.kt 多处（onError 回调） |
| `1000` | 完成 | Debug.kt 多处（解析完成/跳过） |
| `10` | 列表页HTML | **BookList.kt:54, RssParserByRule.kt:37** |
| `20` | 详情页HTML | **BookInfo.kt:40, Rss.kt:135** |
| `30` | 目录页HTML | **BookChapterList.kt:49** |
| `40` | 正文页HTML | **BookContent.kt:52** |

**仿真器现状**（已核实，**与真机一致**）：
- BookSourceDebugger.kt 使用 `10`（搜索页HTML）、`20`（详情页HTML）、`30`（目录页HTML）、`40`（正文页HTML）— **与真机 BookList/BookInfo/BookChapterList/BookContent 一致**
- RssSourceDebugger.kt 使用 `1`（请求URL日志）、`10`（列表页HTML）、`40`（内容页HTML）— **与真机 RssParserByRule/Rss 一致**

**结论**：仿真端 state 码 **已与真机一致**，无需修改。原设计文档错误描述为"真机只用1/-1/1000"是因为只看了 Debug.kt 的 log 方法默认参数，遗漏了 BookList/BookInfo/BookChapterList/BookContent 中使用的 10/20/30/40。

**已核实不需要修复的问题**（原设计文档错误描述）：
- ~~state 码未实现~~：BookSourceDebugger.kt:140/239/360/465 已实现 state 码
- ~~singleUrl 有 bug~~：RssSourceDebugger.kt:373 已用 `rssSource.sourceUrl`（非 `searchUrl`）
- ~~baseUrl 未传~~：搜索阶段第121行、详情阶段第220行已传 `bookSourceUrl`
- ~~相对路径未拼接~~：BookSourceDebugger.kt 中无 toAbsoluteUrl 调用（该方法仅在 RssSourceDebugger.kt:471-475），但 AnalyzeUrl 内部自动处理相对路径拼接
- ~~HtmlStructureAnalyzer 未集成~~：第158/265/375/483行已集成
- ~~nextContentUrl 分页未实现~~：第489-515行已实现
- ~~replaceRegex 未实现~~：第520-529行已实现

---

## 方向 6：经验知识体系完善（P1）

### 6.1 basic-memory 集成

**当前问题**：完全未集成，违反 AGENTS.md 强制规则

**修复方案**：experience_manager.py 输出经验数据到 JSON 文件，AI agent 外层通过 MCP 写入
```python
# legado_client/experience/experience_manager.py
class ExperienceManager:
    def write_experience(self, test_result: Dict[str, Any]) -> None:
        """输出经验数据到 JSON 文件"""
        experience = {
            "error_type": test_result.get("error_type"),
            "fix_solution": test_result.get("fix_solution"),
            "test_result": test_result.get("success"),
            "source_url": test_result.get("source_url"),
            "date": datetime.now().isoformat()
        }
        # 输出到 pending JSON 文件
        pending_file = Path("output/experience-pending.json")
        with open(pending_file, "a", encoding="utf-8") as f:
            json.dump(experience, f, ensure_ascii=False)
            f.write("\n")
        # AI agent 外层通过 MCP 写入 basic-memory
```

### 6.2 经验自动检索

**修复方案**：测试前用 pathlib.Path.rglob 搜索相似案例
```python
def search_experience(self, source_url: str) -> List[Dict[str, Any]]:
    """搜索相似案例"""
    results = []
    # 用 pathlib.Path.rglob 搜索 references/troubleshooting/
    troubleshooting_dir = Path("references/troubleshooting/")
    for md_file in troubleshooting_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if source_url in content:
            results.append({"file": str(md_file), "content": content})
    return results
```

### 6.3 经验自动写入

**修复方案**：测试通过后输出到 output/experience-pending.json
```python
def write_experience(self, test_result: Dict[str, Any]) -> None:
    experience = {
        "error_type": test_result.get("error_type"),
        "fix_solution": test_result.get("fix_solution"),
        "test_result": test_result.get("success"),
        "source_url": test_result.get("source_url"),
        "date": datetime.now().isoformat()
    }
    pending_file = Path("output/experience-pending.json")
    with open(pending_file, "a", encoding="utf-8") as f:
        json.dump(experience, f, ensure_ascii=False)
        f.write("\n")
```

### 6.4 经验冲突解决

**修复方案**：置信度评分+时效性+优先级规则
```python
# legado_client/experience/conflict_resolver.py
class ConflictResolver:
    def resolve_conflict(self, exp1: Dict[str, Any], exp2: Dict[str, Any]) -> Dict[str, Any]:
        """解决经验冲突"""
        def _score(exp: Dict[str, Any]) -> float:
            confidence = exp.get("confidence", 0.5)
            date_str = exp.get("date", "")
            coverage = exp.get("coverage", 0.5)
            recency = 0.8 if date_str else 0.3
            return confidence * 0.5 + recency * 0.3 + coverage * 0.2
        return exp1 if _score(exp1) >= _score(exp2) else exp2
```

---

## 方向 7：设计文档与实际代码一致性（P1）

### 7.1 修复 JSON 去重虚假完成

**当前问题**：tasks.md 标记完成但实际 12 处 json.loads（已核实）
**修复方案**：真正实现 JSON 去重（main() 入口解析一次）

### 7.2 修复 --timeout 参数虚假完成

**当前问题**：tasks.md 标记完成但实际不存在
**修复方案**：真正实现 --timeout 参数

### 7.3 修复 STAGE_NAMES 虚假完成

**当前问题**：tasks.md 标记完成但仍用整数键
**修复方案**：统一为字符串键

### 7.4 修复 CacheManagerStub 虚假完成

**当前问题**（已核实）：CacheManagerStub 已是 object 单例，但使用无限 ConcurrentHashMap（第18行），无 LRU 淘汰
**修复方案**：添加软引用或手动清理（保持 object 单例）

### 7.5 修复 evalJS 虚假完成

**当前问题**（已核实）：RuleEngineServer.kt:134 方法定义，L137-145 已注入 java/cookie/cache/baseUrl，但存在 2 个缺陷：source 参数为 null、baseUrl 为空字符串
**修复方案**：传入真实 source 和 baseUrl（方向 2.1）

### 7.6 修复 4 个孤儿模块虚假完成

**当前问题**（已核实）：4 个脚本（confidence_evaluator/user_interaction_handler/source_navigation/parse_strategy_selector）都是完整实现，但未被 debug-source.py import
**修复方案**：在 debug-source.py 中添加 import 和调用（方向 4）

### 7.7 mock 数字更新

**当前问题**：说~40 个已实现，实际 132 个
**修复方案**：与 JsExtensionsStub.kt 实际代码同步

### 7.8 MVP 命名统一

**当前问题**：SKILL.md 说 MVP4，实际无 mvp4.jar
**修复方案**：统一为 legado-jvm

### 7.9 版本锁同步

**当前问题**：jvm-infrastructure.md 说 okhttp4.12.0，build.gradle.kts 用 5.3.2
**修复方案**：文档与代码同步

---

## 架构决策

### AD-1：JAR 单 JAR 架构（非 4 个）

**决策**：保持单 JAR 架构（legado-jvm.jar），不分拆为 4 个

**原因**：
- 用户质疑"为什么分成了四个 jar，为什么不直接使用一个呢？"
- 子代理 3 确认当前只有 1 个 JAR（非 4 个）
- 单 JAR 简化部署和维护

**影响**：所有功能在单 JAR 中实现

### AD-2：Python 包结构采用 legado_client/

**决策**：采用 legado_client/ 包结构，而非扁平结构

**原因**：
- 用户批评"现在的 python 客户端完全不是工程化的设计理念"
- 包结构提供清晰的层级设计
- 便于维护和扩展

**影响**：需要重构 debug-source.py

### AD-3：basic-memory 通过 JSON 文件+MCP 写入

**决策**：Python 脚本输出经验数据到 JSON 文件，AI agent 外层通过 MCP 写入 basic-memory

**原因**：
- basic-memory 是 MCP 服务器，不是 CLI 命令行工具
- Python 脚本无法直接调用 MCP 或 CLI

**影响**：需要 AI agent 外层配合

### AD-4：JsExtensionsStub 单例化

**决策**：JsExtensionsStub 单例化，避免每次创建新实例

**原因**：
- ~~真机 JsExtensions 是单例~~ **更正**：真机中 AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层
- 仿真器中每次创建新 JsExtensionsStub 实例浪费资源
- 仿真器中 JsExtensionsStub 由 AnalyzeRule/AnalyzeUrl 内部创建（非 BookSourceDebugger/RssSourceDebugger 直接创建）

**影响**：需要修改仿真器中 AnalyzeRule 和 AnalyzeUrl 的 JsExtensionsStub 引用方式

### AD-5：OkHttp 异步化改造

**决策**：OkHttp 从同步 execute 改为异步 enqueue + suspend 函数

**原因**：
- 同步 execute 阻塞主线程
- 异步 enqueue 提高性能

**影响**：需要修改 OkHttpUtils.kt

### AD-6：虚拟环境管理

**决策**：创建 requirements.txt + venv 激活脚本

**原因**：
- 用户批评"完全不去使用虚拟化环境管理依赖"
- 虚拟环境避免依赖冲突

**影响**：需要创建 requirements.txt 和 setup_venv.bat

### AD-7：禁止懒原则

**决策**：所有任务必须真正实现，禁止 YAGNI 跳过核心功能

**原因**：
- 用户明确要求"禁止懒原则"
- 大量通过懒原则简化任务导致孤儿模块（代码完整但未被 import）

**影响**：每个任务必须有源码行号引用+验证方法

### AD-8：CheckSource 校验流程

**决策**：新增 CheckSourceDebugger.kt，实现校验流程

**原因**：
- 真机有 CheckSource.kt 校验流程
- 仿真器无 CheckSource

**影响**：需要新增 CheckSourceDebugger.kt

### AD-9：state 码语义对齐（已核实：伪问题，取消）

**决策**：~~统一仿真端 state 码为真机 Debug.kt 语义（1/-1/1000）~~ **取消此决策**

**原因**（基于第三轮源码深度核实，2026-06-20）：
- ~~真机 Debug.kt 只使用 3 个 state 值~~ **错误**：真机实际有 7 个 state 码（1/-1/1000/10/20/30/40）
- state=10/20/30/40 在真机 BookList.kt:54/BookInfo.kt:40/BookChapterList.kt:49/BookContent.kt:52 中使用
- 仿真端使用 10/20/30/40 **与真机一致**，无需修改

**影响**：~~需要修改 BookSourceDebugger 和 RssSourceDebugger 的 state 码值~~ **无需修改**

### AD-10：4 个孤儿模块集成（非空架子实现）

**决策**：4 个脚本在 debug-source.py 中 import 并调用

**原因**（基于源码核实，2026-06-20）：
- 原设计文档称这 4 个脚本为"空架子"
- 经核实，4 个脚本都是完整实现（confidence_evaluator.py 112行、user_interaction_handler.py 140行、source_navigation.py 84行、parse_strategy_selector.py 131行）
- 3 个脚本有自检代码，1 个无自检代码
- 问题是"未被 import"（孤儿模块），不是"未实现"（空架子）

**影响**：只需在 debug-source.py 中添加 import 和调用，不需要重写逻辑

### AD-15：setVariable/getVariable 签名对齐（2026-06-21）

**决策**：在 BaseSourceInterface 中添加与真机一致的单参数 `setVariable(variable: String?)` 和无参数 `getVariable(): String` 方法，保留现有双参数方法作为额外兼容

**原因**（基于 skill 闭环测试验证，2026-06-21）：
- 仿真端 `BaseSourceInterface.kt:74-85` 使用双参数签名 `setVariable(key: String, value: String?)` 和 `getVariable(key: String): String`
- 真机 `BaseSource.kt:242-269` 使用单参数 `setVariable(variable: String?)` 和无参数 `getVariable(): String`
- JS 代码 `source.setVariable("value")` 和 `source.getVariable()` 在仿真端调用失败（签名不匹配）
- 影响约 5-10% 的书源使用 source.setVariable/getVariable
- 对应差距：simulation-gap-report.md GAP-13（P0，已修复）

**修复方案**：
```kotlin
// 与真机一致的单参数/无参数方法
fun setVariable(variable: String?) {
    if (variable != null) {
        CacheManagerStub.put("sourceVariable_${getKey()}", variable, 0)
    } else {
        CacheManagerStub.delete("sourceVariable_${getKey()}")
    }
}

fun getVariable(): String {
    return CacheManagerStub.get("sourceVariable_${getKey()}") ?: ""
}

// 保留现有双参数方法作为额外兼容（真机通过 put(key,value)/get(key) 实现 key-value 存储）
fun setVariable(key: String, value: String?): Boolean { ... }
fun getVariable(key: String): String { ... }
```

**影响**：需要修改 BaseSourceInterface.kt，添加 2 个新方法

### AD-16：源类型检测优先级（2026-06-21）

**决策**：修复源类型检测逻辑，确保书源和订阅源类型识别正确

**原因**（基于 skill 闭环测试验证，2026-06-21）：
- skill 闭环测试中发现源类型检测存在 bug，导致书源/订阅源类型识别错误
- 源类型检测是调试流程的入口，类型识别错误会导致后续调试流程走错分支
- 此 bug 为 P0 级别，直接影响调试流程正确性

**修复方案**：修正源类型检测逻辑，确保根据源 JSON 结构正确识别为书源（BookSource）或订阅源（RssSource）

**影响**：需要修改源类型检测相关代码

> **仿真差距报告**：本次 skill 闭环测试验证的完整差距分析详见 [simulation-gap-report.md](./simulation-gap-report.md)，综合仿真保真度约 72%

---

## 数据流

### 数据流 1：书源调试全流程

```
用户输入书源 JSON
    ↓
debug-source.py 解析参数（只解析一次）
    ↓
legado_client.client.RuleEngineClient 调用 JAR
    ↓
JAR RuleEngineServer 接收命令
    ↓
BookSourceDebugger.debug() 执行调试
    ├── 搜索阶段（当前state=10，修复后state=1）→ AnalyzeUrl + AnalyzeRule
    ├── 详情阶段（当前state=20，修复后state=1）→ AnalyzeUrl + AnalyzeRule
    ├── 目录阶段（当前state=30，修复后state=1）→ AnalyzeUrl + AnalyzeRule
    └── 正文阶段（当前state=40，修复后state=1）→ AnalyzeUrl + AnalyzeRule
    ↓
返回 DebugResult（state=1000 或 state=-1）
    ↓
legado_client.analyzer.ErrorDiagnoser 错误诊断
    ↓
legado_client.analyzer.ConfidenceEvaluator 可信度评估
    ↓
legado_client.experience.ExperienceManager 经验写入
    ↓
输出报告（--output report.json）
```

### 数据流 2：经验知识闭环

```
测试前
    ↓
ExperienceManager.search_experience() 搜索相似案例
    ├── 正常：pathlib.Path.rglob 搜索 references/troubleshooting/
    └── 降级：basic-memory 不可用时输出警告
    ↓
返回相似案例列表
    ↓
AI 根据相似案例生成/修复书源
    ↓
测试书源
    ↓
测试通过后
    ↓
ExperienceManager.write_experience() 输出经验数据
    ├── 正常：输出到 output/experience-pending.json
    └── 降级：写入 references/troubleshooting/auto/
    ↓
AI agent 外层通过 MCP 写入 basic-memory
```

### 数据流 3：CheckSource 校验流程

```
用户输入书源 JSON + --check 参数
    ↓
RuleEngineClient 调用 JAR check 命令
    ↓
CheckSourceDebugger.check() 执行校验
    ├── 域名检查 → addGroup
    ├── 搜索检查 → addGroup
    ├── 发现检查 → addGroup
    ├── 详情检查 → addGroup
    ├── 目录检查 → addGroup
    └── 正文检查 → addGroup
    ↓
返回 CheckResult（标记失效分组）
    ↓
输出校验报告
```

---

## 文件变更清单

### 新增文件

| 文件 | 方向 | 内容 |
|------|------|------|
| scripts/requirements.txt | 方向 3 | Python 依赖声明 |
| scripts/setup_venv.bat | 方向 3 | Windows 虚拟环境激活脚本 |
| scripts/setup_venv.sh | 方向 3 | Linux 虚拟环境激活脚本 |
| scripts/legado_client/__init__.py | 方向 3 | 包初始化 |
| scripts/legado_client/client/__init__.py | 方向 3 | 客户端层初始化 |
| scripts/legado_client/client/rule_engine_client.py | 方向 3 | JAR 通信客户端 |
| scripts/legado_client/client/webview_handler.py | 方向 3 | WebView 渲染 |
| scripts/legado_client/client/user_interaction.py | 方向 4 | 用户交互 |
| scripts/legado_client/analyzer/__init__.py | 方向 3 | 分析层初始化 |
| scripts/legado_client/analyzer/error_diagnoser.py | 方向 3 | 错误诊断 |
| scripts/legado_client/analyzer/html_structure.py | 方向 3 | HTML 结构分析 |
| scripts/legado_client/analyzer/confidence_evaluator.py | 方向 4 | 可信度评估 |
| scripts/legado_client/analyzer/parse_strategy.py | 方向 4 | 解析策略选择 |
| scripts/legado_client/analyzer/source_navigation.py | 方向 4 | 源码导航 |
| scripts/legado_client/experience/__init__.py | 方向 3 | 经验层初始化 |
| scripts/legado_client/experience/experience_manager.py | 方向 6 | 经验管理 |
| scripts/legado_client/experience/conflict_resolver.py | 方向 6 | 冲突解决 |
| scripts/legado_client/utils/__init__.py | 方向 3 | 工具层初始化 |
| scripts/legado_client/utils/config.py | 方向 3 | 配置管理 |
| scripts/legado_client/utils/logger.py | 方向 3 | 日志 |
| scripts/legado_client/utils/file_utils.py | 方向 3 | 文件工具 |
| tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/CheckSourceDebugger.kt | 方向 5 | CheckSource 校验 |

### 修改文件

| 文件 | 方向 | 修改内容 |
|------|------|---------|
| ~~tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/BookSourceDebugger.kt~~ | ~~方向 5~~ | ~~state 码语义对齐~~ **已核实：伪问题，无需修改** |
| ~~tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/RssSourceDebugger.kt~~ | ~~方向 5~~ | ~~state 码语义对齐~~ **已核实：伪问题，无需修改** |
| tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/RuleEngineServer.kt | 方向 2 | evalJS 上下文修复（source=null→真实source, baseUrl=""→真实baseUrl） |
| tools/legado-jvm/src/main/kotlin/io/legado/app/help/JsExtensionsStub.kt | 方向 1,2 | 单例化（class→object，仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机无 Stub 层）+ 38 个 Stub 补全 |
| tools/legado-jvm/src/main/kotlin/io/legado/app/model/analyzeRule/AnalyzeRule.kt | 方向 1 | scriptCache 上限从 16 提升到 64（第862行）+ JsExtensionsStub 单例引用 |
| tools/legado-jvm/src/main/kotlin/io/legado/app/help/CacheManagerStub.kt | 方向 2 | 添加软引用 LRU（保持 object 单例） |
| tools/legado-jvm/src/main/kotlin/io/legado/app/help/http/OkHttpUtils.kt | 方向 1 | 异步 enqueue + 连接池 |
| tools/legado-jvm/src/main/kotlin/io/legado/app/model/analyzeRule/AnalyzeUrl.kt | 方向 2 | ajax override + JsExtensionsStub 单例引用 |
| scripts/debug-source.py | 方向 3,4 | 拆分为入口脚本+import legado_client + 集成4个孤儿模块 |
| .trae/skills/legado-source-creator/SKILL.md | 方向 7 | mock 数字+MVP 命名+版本锁 |
| .trae/skills/legado-source-creator/references/troubleshooting/mock-unimplemented-functions.md | 方向 7 | mock 数字更新 |
| .trae/skills/legado-source-creator/references/jvm-infrastructure.md | 方向 7 | 版本锁同步 |

**已核实不需要修改的文件**（原设计文档错误描述）：
- ~~NetworkUtilsStub.kt~~：getSubDomain 已剥离 www 前缀，无需修改

> **注意**：AnalyzeRule.kt 原列在此处（"已使用 isNullOrEmpty，无需修改"），但经深度核实发现需要修改：scriptCache 上限从 16 提升到 64（第862行）+ JsExtensionsStub 单例引用。已移至上方修改文件清单。

### 删除文件

无（本次不删除文件，仅重构）
