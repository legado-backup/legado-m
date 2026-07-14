# 订阅源（RSS源）解析全流程性能优化深度分析

> 分析日期：2026-07-14
> 分析范围：网络请求层 / 规则引擎 / 图片加载 / 数据库 / 并发与内存
> 约束：仅技术分析，不含任何源名称/域名/URL

---

## 概述

RSS 源解析全流程为：`Rss.getArticlesAwait` → `AnalyzeUrl.getStrResponseAwait`（网络请求）→ `RssParserByRule.parseXML`（规则解析）→ 列表项并行解析 → `RssArticle` 入库 → 列表渲染（含图片加载）。

已完成的优化（基线）：
- P1-1：`RssParserByRule` 列表项并行化（`Semaphore(6)` + `async{}.awaitAll()`）
- P1-2：`ImageUtils` 解密结果 `LruCache(2MB)` 缓存
- F-P1-C4：`AnalyzeRule.stringRuleCache` 改 `LruCache(64)` 修复无界 HashMap 内存泄漏
- `HttpHelper` 连接池调优（50 连接）、代理客户端 LRU 缓存、`RetryableDns`（重试+负缓存）
- `RssArticleDao.flowByOriginSort` 去掉 content/description 大字段避免 CursorWindow 溢出

---

## 维度1：网络请求层

### 1.1 AnalyzeUrl 每次请求新建实例（P2）

**文件**：`app/src/main/java/io/legado/app/model/rss/Rss.kt` 行 42-52、行 100-107

**问题**：`getArticlesAwait` 和 `getContentAwait` 每次都 `new AnalyzeUrl(...)`，`AnalyzeUrl.init` 块（行 130-145）执行 URL 解析、JS 执行（`analyzeJs`）、headerMap 构建等操作。对于同一源的分页请求，headerMap 解析逻辑重复执行。

**预估收益**：单次请求减少 1-3ms（JS 执行 + header 解析），分页累积明显。

**实施风险**：低。`AnalyzeUrl` 是一次性使用设计，改为池化需评估状态隔离。

### 1.2 无 HTTP 响应缓存（P1）

**文件**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt` 行 70-150

**问题**：`okHttpClient` 未配置 `Cache` 目录。OkHttp 原生支持 HTTP 缓存（基于 Cache-Control/ETag），但当前配置中无 `cache()` 调用。RSS 源列表刷新时，同一 URL 短时间内重复请求（如用户下拉刷新、切换分类回来）都走完整网络请求。

**预估收益**：命中缓存时减少 200-2000ms（取决于网络延迟），降低流量消耗。

**实施风险**：中。RSS 内容时效性要求高，需设置合理的 max-age 或仅缓存带 Cache-Control 头的响应；缓存目录需管理大小上限。

### 1.3 getClient() 频繁 newBuilder().build()（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` 行 617-641

**问题**：当 `readTimeout`/`callTimeout`/`dnsIp` 非空时，每次调用 `getClient()` 都执行 `client.newBuilder().run{...}.build()`。虽然 `newBuilder()` 共享连接池，但 `build()` 会创建新的 OkHttpClient 实例（含新的 Dispatcher），高频请求时有轻微 GC 压力。

**预估收益**：减少对象分配，单次节省 <0.5ms，主要降低 GC 频率。

**实施风险**：低。可按 `(readTimeout, callTimeout, dnsIp)` 做 LRU 缓存，类似 `proxyClientCache` 模式。

### 1.4 无预连接/DNS 预解析（P2）

**文件**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt`

**问题**：RSS 源列表加载时，每篇文章的 `link` 指向不同域名。用户点击文章时才发起 DNS 解析 + TCP 连接 + TLS 握手，首次加载延迟高。无预连接机制。

**预估收益**：减少首次内容页加载 300-1000ms（DNS+TCP+TLS）。

**实施风险**：低。可在列表解析完成后，对前 N 篇文章的 link 域名做 `okHttpClient` 预连接（`ConnectionPool` 预热）。

---

## 维度2：规则引擎

### 2.1 🔴 AnalyzeByRegex 每次重新编译 Pattern（P1）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByRegex.kt` 行 11、行 34

**问题**：
```kotlin
val resM = Pattern.compile(regs[vIndex]).matcher(res)  // 行11
val resM = Pattern.compile(regs[vIndex]).matcher(res)  // 行34
```
`AnalyzeByRegex` 是 `object`（单例），但 `getElement`/`getElements` 每次调用都 `Pattern.compile()`。正则编译是 CPU 密集型操作（解析语法树 + 构建 NFA/DFA），同一个正则表达式在解析每篇文章时都会重新编译。

RSS 列表并行解析 6 项时，若规则模式为 Regex，6 个协程各自编译相同 Pattern，CPU 浪费严重。

**预估收益**：Regex 模式源每项解析减少 0.5-2ms（取决于正则复杂度），20 项列表累积减少 10-40ms。

**实施风险**：低。在 `AnalyzeByRegex` object 内添加 `Pattern` LRU 缓存（key=正则字符串，value=Pattern），与 `AnalyzeRule.regexCache` 模式一致。

### 2.2 🔴 AnalyzeRule 缓存 per-instance 不共享（P1）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 行 81-85

**问题**：
```kotlin
private val stringRuleCache = LruCache<String, List<SourceRule>>(64)  // 行81
private val regexCache = hashMapOf<String, Regex?>(...)               // 行82
private val scriptCache = hashMapOf<String, CompiledScript>(...)      // 行83
```
三个缓存都是 `AnalyzeRule` 实例字段（per-instance）。`RssParserByRule.parseXML` 行 92 为每个列表项创建独立 `AnalyzeRule` 实例（硬性前提1：非线程安全），导致：
- `scriptCache`：同一源的 JS 规则（如 `<js>...</js>`）在每个 item 实例中都要重新 `RhinoScriptEngine.compile()`。Rhino JS 编译是重操作（AST 解析 + 字节码生成），20 项列表重复编译 20 次。
- `regexCache`：正则编译重复。
- `stringRuleCache`：规则拆分重复。

**注意**：`splitSourceRule` 在 `RssParserByRule` 行 75-79 循环外执行，传入的是 `List<SourceRule>`，所以规则拆分本身不重复。但 `evalJS` 内部的 `compileScriptCache`（行 877）是 per-item 的。

**预估收益**：含 JS 的源每项解析减少 2-10ms（Rhino 编译开销），20 项列表累积减少 40-200ms。

**实施风险**：中。改为全局/源级共享缓存需评估：
1. `scriptCache` 的 key 是 JS 字符串，跨实例共享安全（CompiledScript 无状态）
2. `regexCache` 的 key 是正则字符串，跨实例共享安全
3. 但需加并发保护（当前 `hashMapOf` 非线程安全，per-instance 时单线程访问安全，共享后需改 `ConcurrentHashMap` 或加锁）

**建议方案**：将 `scriptCache` 和 `regexCache` 提升为 `companion object` 级别的全局缓存（带 LRU 上限），`stringRuleCache` 保持 per-instance（含 `putMap` 等实例状态）。

### 2.3 AnalyzeByJSoup 无 CSS 选择器编译缓存（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByJSoup.kt` 行 79、行 87-97

**问题**：
```kotlin
val sourceRule = SourceRule(ruleStr)                        // 行79 每次新建
val ruleAnalyzes = RuleAnalyzer(sourceRule.elementsRule)    // 行87 每次新建
element.select(ruleStrX.take(lastIndex))                    // 行97 jsoup select 每次编译 CSS 选择器
```
`getStringList` 每次调用都创建 `SourceRule` 和 `RuleAnalyzer`，且 `element.select()` 内部每次编译 CSS 选择器（jsoup 的 `QueryParser.parse`）。同一规则在解析每篇文章的每个字段时重复编译。

**预估收益**：Default 模式源每字段解析减少 0.1-0.5ms，累积效果取决于字段数量和列表大小。

**实施风险**：中。jsoup 的 `select()` 内部缓存需 jsoup 支持，当前版本（1.16.2 锁定）可能不提供。可在 `AnalyzeByJSoup` 层缓存 `Evaluator`（jsoup 选择器编译结果），但需评估 Evaluator 是否绑定 Document。

### 2.4 AnalyzeByXPath 无 XPath 编译缓存（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByXPath.kt` 行 57-58、行 95-96

**问题**：`getElements`/`getStringList` 每次都 `new RuleAnalyzer(xPath)` + `splitRule`，且 `node.sel(xPath)`（行 46）/ `doc.selN(xPath)`（行 48）底层每次编译 XPath 表达式。JXDocument 的 XPath 解析无缓存。

**预估收益**：XPath 模式源每项解析减少 0.2-1ms。

**实施风险**：中。XPath 编译结果（`JXExpression`）是否可跨 Document 复用需验证。

### 2.5 splitSourceRule 重复正则匹配（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 行 559-580

**问题**：`splitSourceRule` 每次用 `JS_PATTERN.matcher(ruleStr)` 和 `WebJS_PATTERN.matcher(ruleStr)` 遍历。虽然 `splitSourceRuleCacheString`（行 534-540）有 LruCache 缓存，但 `getElement`/`getElements`（行 382、行 417）调用的是 `splitSourceRule`（无缓存版本），不走缓存。

**预估收益**：getElements 路径每项减少 0.1-0.3ms。

**实施风险**：低。让 `getElement`/`getElements` 也走 `splitSourceRuleCacheString`（需确认 `allInOne` 参数的语义差异）。

---

## 维度3：图片加载

### 3.1 解密缓存 2MB 上限偏小（P2）

**文件**：`app/src/main/java/io/legado/app/utils/ImageUtils.kt` 行 26-28

**问题**：
```kotlin
private val decodeCache = object : LruCache<String, ByteArray>(2 * 1024 * 1024)  // 2MB
```
2MB 上限对于多图列表（如图片类 RSS 源）偏小。单张缩略图 20-100KB，2MB 仅缓存 20-100 张。列表快速滚动时缓存命中率低，重复解密（含 evalJS）开销大。

**预估收益**：提升至 8-16MB，图片类源列表滚动减少 80% 解密调用（evalJS 每次约 5-20ms）。

**实施风险**：低。增加内存占用 6-14MB，需评估低端设备（minSdk 23）内存压力。可按 `Runtime.maxMemory()` 动态设置上限（如 maxMemory/32）。

### 3.2 decode(InputStream) 全量读取到内存（P2）

**文件**：`app/src/main/java/io/legado/app/utils/ImageUtils.kt` 行 85-87

**问题**：
```kotlin
val bytes = inputStream.readBytes()  // 行86 全量读取
val decoded = decode(src, bytes, ...)
```
`decode(InputStream)` 先 `readBytes()` 将整个流读入内存，再复用 `decode(ByteArray)`。对于大图（如高清封面 1-5MB），峰值内存 = 原始数据 + 解密后数据，叠加 LruCache 缓存，内存峰值高。

**预估收益**：降低图片解码峰值内存 30-50%。

**实施风险**：中。流式解密需重构 evalJS 接口（当前传 ByteArray），改动较大。

### 3.3 无图片下载磁盘缓存复用验证（P2）

**文件**：`app/src/main/java/io/legado/app/utils/ImageUtils.kt`

**问题**：`decode` 的 `src` 参数（图片路径）作为缓存 key。但 Glide/Coil 的磁盘缓存 key 可能包含完整 URL + headers，与 `src` 不一致，导致磁盘缓存命中但解密缓存未命中（或反之），两层缓存不对齐。

**预估收益**：减少不对齐导致的重复解密。

**实施风险**：低。需确认图片加载框架的缓存 key 生成逻辑，对齐两层缓存 key。

---

## 维度4：数据库

### 4.1 🔴 RssArticle 缺少 (origin, sort) 复合索引（P1）

**文件**：`app/src/main/java/io/legado/app/data/entities/RssArticle.kt` 行 10-13

**问题**：
```kotlin
@Entity(
    tableName = "rssArticles",
    primaryKeys = ["origin", "link", "sort"]  // 复合主键：origin, link, sort
)
```
主键索引为 `(origin, link, sort)`。但 `RssArticleDao.flowByOriginSort`（行 19-26）查询条件是 `where origin = :origin and sort = :sort`，**跳过了 link**。SQLite 复合索引遵循最左前缀原则，查询 `(origin, sort)` 无法利用 `(origin, link, sort)` 索引（link 在中间断裂）。

实际执行时 SQLite 会用 `origin` 前缀过滤，再扫描所有匹配 `origin` 的行筛选 `sort`。当某源积累大量文章时（数千条），查询效率低。

**预估收益**：大文章量源（>1000 条）列表加载从 O(n) 降至 O(log n)，减少 50-200ms。

**实施风险**：低。添加 `@Index(name = "idx_origin_sort", value = ["origin", "sort"])` 注解，Room 自动迁移建索引。需编写 Migration 或启用 fallbackToDestructiveMigration。

### 4.2 RssSourceDao 搜索用 LIKE 无 FTS（P2）

**文件**：`app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt` 行 36-44、行 71-80

**问题**：多个搜索查询用 `like '%' || :key || '%'`，前置通配符导致全表扫描。当 RSS 源数量多（数百个）时搜索延迟明显。

**预估收益**：FTS 全文搜索将搜索从 O(n) 降至 O(log n)，数百源搜索减少 10-50ms。

**实施风险**：中。引入 FTS4/FTS5 虚拟表需建表迁移 + 触发器同步，改动较大。源数量通常 <1000，收益有限，优先级低。

### 4.3 clearOld 批量删除无事务（P2）

**文件**：`app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt` 行 34-35

**问题**：
```kotlin
@Query("delete from rssArticles where origin = :origin and sort = :sort and `order` < :order")
fun clearOld(origin: String, sort: String, order: Long)
```
`clearOld` 删除旧文章，可能涉及大量行。单条 DELETE 在 SQLite 中是隐式事务，大量删除时 WAL 日志膨胀，且与并发的 `insert`/`flowByOriginSort` 竞争锁。

**预估收益**：减少锁竞争导致的列表加载卡顿。

**实施风险**：低。可在调用方用 `@Transaction` 包装 `clearOld` + `insert` 批量操作。

### 4.4 variableMap 重复 GSON 解析（P2）

**文件**：`app/src/main/java/io/legado/app/data/entities/RssArticle.kt` 行 46-48

**问题**：
```kotlin
override val variableMap: HashMap<String, String> by lazy {
    GSON.fromJsonObject<HashMap<String, String>>(variable).getOrNull() ?: hashMapOf()
}
```
`variableMap` 用 `lazy` 首次访问时 GSON 解析。但 `variable` 字段更新后（如 `put` 操作），`lazy` 不会重新解析，返回旧值。且每次新实例都会重新解析（lazy 是 per-instance）。

**预估收益**：减少重复 GSON 解析开销。

**实施风险**：低。当前行为可能依赖 lazy 的单次解析特性，改动需评估业务逻辑。

---

## 维度5：并发与内存

### 5.1 🔴 AnalyzeRule 实例创建开销大（P1）

**文件**：`app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` 行 92-95

**问题**：并行化后每个列表项创建独立 `AnalyzeRule` 实例（行 92），每个实例初始化：
- `LruCache(64)` stringRuleCache（行 81）：分配 LinkedHashMap 数组
- `hashMapOf` regexCache（行 82）：分配 HashMap
- `hashMapOf` scriptCache（行 83）：分配 HashMap
- `WeakReference` topScopeRef（行 84）

20 项列表 × 6 并发 = 同时存在最多 6 个 AnalyzeRule 实例，每个含 3 个 Map 结构。GC 压力主要来自实例创建/回收，而非 Map 内容。

**预估收益**：结合 2.2 的全局缓存方案，实例可共享 `scriptCache`/`regexCache`，减少 Map 分配和 JS 重复编译。预计减少 30% GC 时间。

**实施风险**：中。需确保共享缓存的线程安全（改 `ConcurrentHashMap` 或 `LruCache` 自带同步）。

### 5.2 evalJS bindings 每次创建新对象（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 行 844-858

**问题**：
```kotlin
val bindings = buildScriptBindings { bindings ->
    bindings["java"] = this
    bindings["cookie"] = CookieStore
    // ... 12 个变量绑定
}
```
`evalJS` 每次调用都创建新的 `ScriptBindings` 对象并设置 12 个变量。RSS 列表项解析中，若规则含 `{{js}}` 或 `<js>`，每项每字段都调用 `evalJS`，bindings 创建开销累积。

**预估收益**：减少对象分配，单次节省 <0.1ms，累积效果取决于 JS 调用频率。

**实施风险**：中。bindings 复用需确保上一次执行的状态不泄漏到下次（clear + rebind）。

### 5.3 evalJSCallCount 非线程安全（P2）

**文件**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 行 85、行 862

**问题**：
```kotlin
private var evalJSCallCount = 0  // 行85 非 volatile 非 atomic
if (evalJSCallCount++ > 16) {    // 行862 非原子读-改-写
    topScopeRef = WeakReference(prototype)
}
```
`evalJSCallCount` 是普通 `Int`，`++` 操作非原子。`RssParserByRule` 并行化后每个 item 用独立 `AnalyzeRule` 实例（规避了并发问题），但如果未来改为共享实例，此处会有竞态条件。

**当前状态**：因 per-instance 设计，当前无实际并发问题。但属于潜在隐患。

**预估收益**：无直接性能收益，消除潜在并发 bug。

**实施风险**：低。改 `AtomicInteger` 即可，但当前 per-instance 下非必要。

### 5.4 大 HTML body 在多实例间传递（P2）

**文件**：`app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` 行 53、行 137

**问题**：`parseXML` 行 53 设置 `analyzeRule.setContent(body)`，body 是完整 HTML 字符串（可能 100KB-1MB）。并行化后每个 item 的 `AnalyzeRule` 调用 `setContent(item)`（行 137），item 是从 body 中提取的子节点。但外层 `analyzeRule`（行 51）和每个 `itemRule`（行 92）都引用了相关数据结构。

jsoup 的 `Element` 是树节点引用，子节点共享父文档的字符串数据，不会复制。但 `content.toString()` 调用（如 `AnalyzeByJSoup.parse` 行 37 `Jsoup.parse(doc.toString())`）会触发字符串序列化，产生大字符串临时对象。

**预估收益**：减少大字符串复制，降低 GC 压力。

**实施风险**：中。需识别 `toString()` 调用路径，改为直接传递 `Element`/`Document` 对象避免序列化。

### 5.5 Semaphore(6) 固定值未适配 CPU 核心数（P2）

**文件**：`app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` 行 86

**问题**：
```kotlin
val parseSemaphore = Semaphore(6)
```
并行限流硬编码为 6。在 8 核设备上未充分利用 CPU，在 2-4 核低端设备上可能过度并发导致调度开销。

**预估收益**：低端设备减少上下文切换开销，高端设备提升吞吐。

**实施风险**：低。改为 `Runtime.getRuntime().availableProcessors().coerceIn(2, 8)` 动态适配。

### 5.6 Debug.log 在并行块内频繁调用（P2）

**文件**：`app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` 行 85、行 114、行 138-165

**问题**：`getItem` 内有大量 `Debug.log` 调用（行 138-165 每个字段 2 条日志）。并行化后 6 个协程同时输出日志，`Debug.log` 内部若有同步操作（如写入列表/文件）会成为瓶颈。

**预估收益**：减少日志开销，预计每项减少 0.5-1ms。

**实施风险**：低。确认 `Debug.log` 是否有同步开销，若有可改为批量/异步日志。

---

## 优化优先级汇总表

| 优先级 | 编号 | 优化点 | 文件 | 预估收益 | 实施风险 |
|--------|------|--------|------|----------|----------|
| **P1** | 2.1 | AnalyzeByRegex Pattern 编译缓存 | AnalyzeByRegex.kt:11,34 | Regex源每项减少0.5-2ms | 低 |
| **P1** | 2.2 | AnalyzeRule scriptCache/regexCache 全局共享 | AnalyzeRule.kt:81-85 | 含JS源每项减少2-10ms | 中 |
| **P1** | 4.1 | RssArticle 添加 (origin,sort) 索引 | RssArticle.kt:10-13 | 大列表减少50-200ms | 低 |
| **P1** | 1.2 | HTTP 响应缓存（Cache目录） | HttpHelper.kt:70-150 | 命中时减少200-2000ms | 中 |
| **P1** | 5.1 | AnalyzeRule 实例开销（结合2.2） | RssParserByRule.kt:92 | 减少30% GC时间 | 中 |
| **P2** | 1.1 | AnalyzeUrl 实例复用 | Rss.kt:42-52 | 单次减少1-3ms | 低 |
| **P2** | 1.3 | getClient() LRU 缓存 | AnalyzeUrl.kt:617-641 | 降低GC频率 | 低 |
| **P2** | 1.4 | 预连接/DNS预解析 | HttpHelper.kt | 首次减少300-1000ms | 低 |
| **P2** | 2.3 | CSS选择器编译缓存 | AnalyzeByJSoup.kt:79,97 | 每字段减少0.1-0.5ms | 中 |
| **P2** | 2.4 | XPath编译缓存 | AnalyzeByXPath.kt:57-58 | 每项减少0.2-1ms | 中 |
| **P2** | 2.5 | getElement/getElements 走缓存 | AnalyzeRule.kt:382,417 | 每项减少0.1-0.3ms | 低 |
| **P2** | 3.1 | 解密缓存上限提升 | ImageUtils.kt:26 | 图片源减少80%解密 | 低 |
| **P2** | 3.2 | decode(InputStream) 流式优化 | ImageUtils.kt:85-87 | 降低峰值内存30-50% | 中 |
| **P2** | 3.3 | 两层缓存key对齐 | ImageUtils.kt | 减少不对齐重复解密 | 低 |
| **P2** | 4.2 | FTS全文搜索 | RssSourceDao.kt:36-44 | 搜索减少10-50ms | 中 |
| **P2** | 4.3 | clearOld 事务包装 | RssArticleDao.kt:34 | 减少锁竞争卡顿 | 低 |
| **P2** | 4.4 | variableMap 解析优化 | RssArticle.kt:46-48 | 减少GSON解析 | 低 |
| **P2** | 5.2 | evalJS bindings 复用 | AnalyzeRule.kt:844-858 | 减少对象分配 | 中 |
| **P2** | 5.3 | evalJSCallCount 原子化 | AnalyzeRule.kt:85 | 消除并发隐患 | 低 |
| **P2** | 5.4 | 大body避免toString序列化 | RssParserByRule.kt:53 | 降低GC压力 | 中 |
| **P2** | 5.5 | Semaphore 动态适配CPU | RssParserByRule.kt:86 | 适配设备性能 | 低 |
| **P2** | 5.6 | Debug.log 并行开销 | RssParserByRule.kt:138-165 | 每项减少0.5-1ms | 低 |

---

## 实施建议（按收益/风险排序）

### 第一批（高收益低风险）
1. **2.1 AnalyzeByRegex Pattern 缓存** — object 内加 `LruCache<String, Pattern>`，改动最小，Regex 源立即受益
2. **4.1 RssArticle 索引** — 加 `@Index` 注解 + Migration，大列表源立即受益
3. **5.5 Semaphore 动态适配** — 一行改动，适配所有设备

### 第二批（高收益中风险）
4. **2.2 + 5.1 scriptCache/regexCache 全局共享** — 提升为 companion object 级缓存，改 `ConcurrentHashMap`，含 JS 源大幅受益
5. **1.2 HTTP 响应缓存** — 配置 OkHttp Cache 目录，需管理缓存大小和时效策略

### 第三批（中收益低风险）
6. **3.1 解密缓存扩容** — 调整 LruCache 上限，按 maxMemory 动态设置
7. **2.5 getElement 走缓存** — 让 getElements 也用 `splitSourceRuleCacheString`
8. **1.4 预连接** — 列表解析后预热前 N 篇文章域名连接

---

## 注意事项

1. **jsoup 1.16.2 锁定**（AGENTS.md landmine）：2.3 的 CSS 选择器缓存方案需确认不触发 jsoup#2017 破坏性变更
2. **rhino 1.8.1 锁定**（AGENTS.md landmine）：2.2 的 scriptCache 共享需确认 `CompiledScript` 跨实例 eval 安全
3. **ReadBook 全局单例**（AGENTS.md landmine）：`AnalyzeRule` 共享缓存需加 `@Synchronized` 或 `ConcurrentHashMap` 保护
4. **并发文件修改规范**：源码修改由主 Agent 串行执行，本分析仅为建议不涉及代码变更
