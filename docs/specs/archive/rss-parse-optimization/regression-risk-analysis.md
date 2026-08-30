# RSS 解析优化设计文档 — 8 个优化点回归风险分析报告

> 基于源码逐行验证，评估每个优化点是否导致正常功能不可用。

## 合理性分析结论

8 个优化点中：
- **3 个低风险**：可直接实施（优化点 1/3/6）
- **3 个中风险**：调整后实施（优化点 2/5/7）
- **1 个高风险**：需重点验证线程安全（优化点 4）
- **1 个低风险但需优化**：预连接应改并行（优化点 8）

**核心发现**：设计文档在 2 个关键细节上与源码不符，已在下方标注。

---

## 逐项分析

### 优化点1：AnalyzeByRegex Pattern 缓存（第一批 2.1）

- **回归风险**：低
- **源码验证**：
  - `AnalyzeByRegex.kt` 是 `object`（单例），行 11、行 34 确认 `Pattern.compile(regs[vIndex])`
  - `Pattern` 是不可变对象，`Pattern.matcher()` 线程安全
  - `LruCache` 自带 `synchronized`，6 并发协程访问安全
- **风险描述**：无功能破坏风险。`getPattern()` 返回的 `Pattern` 与 `Pattern.compile()` 结果等价，`matcher()` 行为不变。LruCache 淘汰后重新编译结果一致。
- **边界条件**：空正则字符串会抛 `PatternSyntaxException`，但原代码同样会抛，行为一致。
- **验证结论**：实施安全，对照 `AnalyzeByRegex.kt` 行 7（object）、行 11/行 34（compile 点）。
- **建议**：实施

### 优化点2：RssArticle (origin,sort) 复合索引（第一批 4.1）

- **回归风险**：低（但有一个设计文档遗漏的细节）
- **源码验证**：
  - `RssArticle.kt` 行 10-13 确认主键 `(origin, link, sort)`，无 `@Index`
  - `RssArticleDao.kt` 行 19-26 `flowByOriginSort` 是 **JOIN 查询**（`rssArticles LEFT JOIN rssReadRecords`），WHERE 条件在 t1 上：`where t1.origin = :origin and t1.sort = :sort`
  - `AppDatabase.kt` 行 77 确认 `version = 93`
  - `DatabaseMigrations.kt` 行 23 确认最后是 `migration_92_93`，行 438 确认定义存在
- **风险描述**：
  1. 索引创建不破坏现有数据，`CREATE INDEX IF NOT EXISTS` 安全
  2. `fallbackToDestructiveMigration` 兜底（AppDatabase.kt 行 69，仅对 1-9 版本兜底，93→94 不在范围内，需确保 Migration 正确执行）
  3. **设计文档遗漏**：`fallbackToDestructiveMigrationFrom(false, 1, 2, 3, 4, 5, 6, 7, 8, 9)` 只对版本 1-9 兜底，**版本 93→94 的 Migration 失败不会触发兜底**，会抛 `IllegalStateException`。Migration 必须正确编写。
  4. 索引增加写入开销：RSS 文章写入频率低（每次刷新），可接受
- **边界条件**：JOIN 查询的索引利用——SQLite 优化器会决定是否使用索引，(origin, sort) 索引能加速 WHERE 条件过滤，但 JOIN 操作本身可能仍需全表扫描 rssReadRecords。
- **验证结论**：对照 `RssArticle.kt` 行 10-13、`RssArticleDao.kt` 行 19-26、`AppDatabase.kt` 行 69/77、`DatabaseMigrations.kt` 行 23/438。Migration 必须正确编写，无兜底。
- **建议**：实施，但需确保 Migration SQL 正确无误

### 优化点3：Semaphore 动态适配（第一批 5.5）

- **回归风险**：低
- **源码验证**：
  - `RssParserByRule.kt` 行 86：`val parseSemaphore = Semaphore(6)` — **这是 `parseXML` 方法内的局部变量，不是 companion object 字段！**
  - 设计文档说"移至 companion object 初始化时计算一次"——这意味着从局部变量改为全局字段
- **风险描述**：
  1. 当前每次调用 `parseXML` 都会创建新的 `Semaphore(6)`，改为全局字段后整个应用生命周期共享同一个 Semaphore
  2. **功能影响**：Semaphore 是限流器，从局部→全局共享不改变限流语义（同一时间只允许 N 个协程进入），只要 permits 数量合理
  3. `coerceIn(2, 8)` 限定范围安全：2 核设备用 2，8 核以上用 8
  4. **潜在问题**：如果改为全局 Semaphore，且 `parseXML` 可能被并发调用（不同 RSS 源同时刷新），两个源的解析会共享同一个 Semaphore，总并发度受限于 `coerceIn(2,8)`。原代码每个 parseXML 调用独立 Semaphore(6)，多源并发时总并发度更高。
- **边界条件**：多源并发刷新场景下，全局 Semaphore 会限制总并发度。但 Dispatchers.IO 线程池本身有上限（64 线程），且单源 20 项列表 × 6 并发已接近 IO 线程池容量。
- **验证结论**：对照 `RssParserByRule.kt` 行 86。设计文档未提及"局部变量→全局字段"的行为变化。
- **建议**：实施，但建议保留为局部变量（在 parseXML 内创建 `Semaphore(Runtime.getRuntime().availableProcessors().coerceIn(2, 8))`），避免多源并发时互相限制。或如改为全局字段，需评估多源并发场景。

### 优化点4：scriptCache/regexCache 全局共享（第二批 2.2+5.1）

- **回归风险**：中（核心风险点）
- **源码验证**：
  - `AnalyzeRule.kt` 行 82-83 确认 per-instance：`regexCache = hashMapOf<String, Regex?>()`、`scriptCache = hashMapOf<String, CompiledScript>()`
  - 行 84-85：`topScopeRef`（WeakReference<Scriptable>）、`evalJSCallCount` 确认 per-instance
  - 行 521-529：`compileRegexCache` 使用 `regexCache.getOrPutLimit(regex, 16) {...}`
  - 行 876-880：`compileScriptCache` 使用 `scriptCache.getOrPutLimit(jsStr, 16) {...}`
  - 行 859-865：`evalJS` 中 `topScopeRef` 和 `evalJSCallCount` 的使用逻辑——当 `evalJSCallCount++ > 16` 时设置 `topScopeRef = WeakReference(prototype)`
  - `getOrPutLimit` 是 `MutableMap<K,V>` 扩展（确认存在），`LruCache` 不是 `MutableMap` 子类
- **风险描述**：
  1. **线程安全**（高风险）：原 `hashMapOf` 非线程安全，但当前是 per-instance，每个协程独立实例不共享。提升为 companion 后，6 并发协程共享，**必须** `@Synchronized` 保护编译操作。如果遗漏同步，会导致 `ConcurrentModificationException` 或数据错乱。
  2. **getOrPutLimit 不兼容**（中风险）：需重写 `compileScriptCache`（行 876-880）和 `compileRegexCache`（行 521-529）方法体。设计文档已识别，提供重写方案。
  3. **CompiledScript 跨实例 eval 安全性**：Rhino `Context.enter()` 基于 ThreadLocal，每线程独立 Context，跨实例共享 CompiledScript 应安全。
  4. **topScopeRef 保持 per-instance**（正确）：行 859-865 的逻辑是"同一实例 JS 调用超过 16 次后缓存 topScope"，跨实例共享会破坏 JS 执行上下文。设计文档正确识别了这点。
  5. **evalJSCallCount 保持 per-instance**（正确）：行 862 `evalJSCallCount++` 是实例计数器，跨实例共享会导致计数错乱。
- **边界条件**：
  - 6 并发协程同时编译相同 JS：@Synchronized 保证只编译一次，其余等待
  - LruCache 淘汰：淘汰后重新编译，结果等价
  - 编译失败：`getOrCompileScript` 返回 null，`compileScriptCache` 原 `getOrPutLimit` 也会缓存 null，行为一致
- **验证结论**：对照 `AnalyzeRule.kt` 行 82-85（字段定义）、行 521-529/876-880（使用点）、行 859-865（topScopeRef 逻辑）。设计文档对 topScopeRef/evalJSCallCount 保持 per-instance 的决策正确。
- **建议**：调整后实施。关键点：①@Synchronized 必须覆盖编译操作；②getOrPutLimit 重写必须正确；③需 6 并发协程压力测试验证。

### 优化点5：HTTP 响应缓存（第二批 1.2）

- **回归风险**：中
- **源码验证**：
  - `HttpHelper.kt` 行 70-150：`okHttpClient` 确认无 `Cache` 配置
  - 行 105：`builder.addHeader("Cache-Control", "no-cache")` 确认！no-cache 会强制 OkHttp Cache 跳过命中
  - 行 152-170：`okHttpClientManga` 已用 `newBuilder()` 派生，证明派生客户端模式是项目已有实践
- **风险描述**：
  1. **no-cache 阻断**（已识别）：设计文档已识别此问题，新增 `rssOkHttpClient`（移除 no-cache）隔离影响
  2. **调用点改造**（中风险）：RSS 源请求链路需改用 `rssOkHttpClient`。如果改造不完整，部分请求仍走原 `okHttpClient`（带 no-cache），缓存不生效但**功能不回归**。
  3. **缓存时效性**：OkHttp 默认遵循 `Cache-Control: max-age`，仅缓存带头的响应。无 Cache-Control 头的响应不缓存，保持默认行为。
  4. **书源不受影响**（已识别）：书源请求走 `okHttpClient`（带 no-cache），OkHttp 遇到 no-cache 走网络，不命中缓存。
  5. **warmUpConnection 实现**：设计文档修正为 `execute().use { }`，正确（use 是 Closeable 扩展，确保 Response 自动关闭）
- **边界条件**：
  - 缓存目录磁盘满：OkHttp Cache 有 maxSize=50MB，LRU 自动淘汰
  - 并发缓存写入：OkHttp Cache 内部有锁保护
  - 缓存损坏：OkHttp 有缓存校验机制
- **验证结论**：对照 `HttpHelper.kt` 行 70-150（okHttpClient）、行 105（no-cache）、行 152-170（newBuilder 实践）。设计文档的隔离方案正确。
- **建议**：调整后实施。关键点：①RSS 源请求链路必须全部改用 rssOkHttpClient；②warmUpConnection 的 execute() 是同步调用，会阻塞线程，需在 IO 线程调用。

### 优化点6：解密缓存扩容（第三批 3.1）

- **回归风险**：低
- **源码验证**：
  - `ImageUtils.kt` 行 26-28：`LruCache<String, ByteArray>(2 * 1024 * 1024)` 确认 2MB
  - 行 27：**已有 `sizeOf` 覆写**！设计文档说"新增 sizeOf 覆写"是错误的
- **风险描述**：
  1. 仅增大 LruCache 上限，功能不变
  2. `coerceIn(4MB, 16MB)` 限定范围安全
  3. `maxMemory/32` 动态适配，低端设备内存压力可控
  4. **设计文档错误**：原代码已有 `sizeOf` 覆写（行 27），设计文档说"新增 sizeOf 覆写"是失误
- **边界条件**：
  - 低端设备 maxMemory 小 → 缓存小（maxMemory/32），内存压力可控
  - 极端情况 maxMemory < 128MB → maxMemory/32 < 4MB → coerceIn 下限 4MB 生效
- **验证结论**：对照 `ImageUtils.kt` 行 26-28。设计文档"新增 sizeOf"描述有误，实际已存在。
- **建议**：实施。注意设计文档修正：sizeOf 已存在，只需修改 LruCache 构造参数。

### 优化点7：getElement 走缓存（第三批 2.5）

- **回归风险**：中（存在 isRegex 实例状态传递的隐藏风险）
- **源码验证**：
  - `AnalyzeRule.kt` 行 534-540：`splitSourceRuleCacheString(ruleStr: String?)` 确认无 allInOne 参数
  - 行 545-588：`splitSourceRule(ruleStr: String?, allInOne: Boolean = false)` 确认
  - 行 382：`getElement` 调用 `splitSourceRule(ruleStr, true)` 确认 allInOne=true
  - 行 417：`getElements` 调用 `splitSourceRule(ruleStr, true)` 确认 allInOne=true
  - **关键发现**：行 551-556 `splitSourceRule` 内部有**实例状态副作用**：
    ```kotlin
    if (allInOne && ruleStr.startsWith(":")) {
        mMode = Mode.Regex
        isRegex = true       // ← 修改实例状态！
        start = 1
    } else if (isRegex) {    // ← 读取实例状态
        mMode = Mode.Regex
    }
    ```
- **风险描述**：
  1. **allInOne 缓存 key 区分**（已识别）：设计文档提出用 `"allInOne=$allInOne|$ruleStr"` 复合 key，正确
  2. **isRegex 实例状态传递风险**（设计文档未识别）：
     - 原代码：`getElements(ruleArticles)` 调用 `splitSourceRule(ruleStr, true)`，如果 ruleArticles 以 ":" 开头，会设置 `isRegex = true`
     - 后续 `getString(ruleTitle)` 调用 `splitSourceRuleCacheString(ruleStr)` → `splitSourceRule(ruleStr)`（allInOne=false），行 555 `else if (isRegex)` 读到 true，设置 mMode=Regex
     - **改用缓存后**：如果 `getElements` 命中缓存，`splitSourceRule` 不执行，`isRegex` 不被设置为 true。后续 `getString` 未命中缓存时，`isRegex` 仍为 false（默认值），mMode=Default 而非 Regex
     - **触发条件**：ruleArticles 以 ":" 开头（allInOne=true 场景），且后续 getString 未命中缓存
     - **影响范围**：RssParserByRule.kt 行 61 调用 `getElements(ruleArticles)`，行 139 等调用 `getString(ruleTitle/rulePubDate/...)`
  3. **实际影响评估**：大多数 RSS 源的 ruleArticles 不以 ":" 开头（通常用 CSS/XPath/JSON 规则），此风险触发概率低。但一旦触发，会导致后续所有 getString 解析模式错误（Default vs Regex）。
- **边界条件**：
  - 缓存命中时不执行 splitSourceRule 的副作用
  - 缓存未命中时执行 splitSourceRule，isRegex 正常设置
- **验证结论**：对照 `AnalyzeRule.kt` 行 534-540（缓存版本）、行 545-588（splitSourceRule）、行 551-556（isRegex 副作用）、行 382/417（调用点）。设计文档未识别 isRegex 风险。
- **建议**：调整后实施。修正方案：在 `splitSourceRuleCacheString` 命中缓存时，如果 `allInOne=true && ruleStr.startsWith(":")`，也需设置 `isRegex = true`。或更好：将 isRegex 逻辑从 splitSourceRule 中解耦（但属于重构）。

### 优化点8：预连接/DNS 预解析（第三批 1.4）

- **回归风险**：低（但有一个性能问题需优化）
- **源码验证**：
  - `Rss.kt` 行 35-81：`getArticlesAwait` 返回 `Pair<MutableList<RssArticle>, String?>`
  - 行 80：`return RssParserByRule.parseXML(...)` 是返回点
  - 设计文档说在 `getArticlesAwait` 中插入预连接逻辑
- **风险描述**：
  1. HEAD 请求 + `runCatching`，失败不影响列表显示
  2. 仅预连接前 3 篇，避免过度预连接
  3. **性能问题**：设计文档伪代码用 `forEach`（串行），3 个 HEAD 请求串行执行，每个可能 100-500ms，总计 300-1500ms 额外延迟。应改为 `async` 并行预连接。
  4. `warmUpConnection` 用同步 `execute()`，会阻塞调用线程。`getArticlesAwait` 是 suspend 函数，在协程中调用，阻塞 IO 线程可接受，但 3 个串行请求会累积延迟。
- **边界条件**：
  - article.link 为空/无效：`isNullOrBlank()` 检查 + `runCatching` 捕获
  - 预连接失败：连接池不保留该连接，不影响后续点击
  - 连接池满（50 个）：OkHttp 会自动回收最旧连接
- **验证结论**：对照 `Rss.kt` 行 35-81。设计文档插入点正确。
- **建议**：实施，但预连接应改为并行（`coroutineScope { articles.take(3).map { async { warmUpConnection(it) } }.awaitAll() }`），避免串行延迟累积。

---

## 总结

### 高风险优化点
- **优化点4（scriptCache/regexCache 全局共享）**：线程安全是核心风险。@Synchronized 必须正确覆盖编译操作，需 6 并发协程压力测试。如果同步实现有误，会导致 `ConcurrentModificationException` 或 JS 执行数据错乱。
  - **缓解措施**：实施后必须执行 S10/S11 场景测试（6 并发协程同时编译相同 JS/Regex）

### 中风险优化点
- **优化点2（RssArticle 索引）**：Migration 失败无兜底（`fallbackToDestructiveMigrationFrom` 只覆盖 1-9 版本），Migration SQL 必须正确
- **优化点5（HTTP 缓存）**：调用点改造需完整，warmUpConnection 同步 execute 需在 IO 线程
- **优化点7（getElement 走缓存）**：存在 isRegex 实例状态传递的隐藏风险（设计文档未识别），需在缓存命中时补充 isRegex 设置

### 低风险优化点（可直接实施）
- **优化点1（Pattern 缓存）**：LruCache + 不可变 Pattern，零回归风险
- **优化点3（Semaphore 动态适配）**：coerceIn(2,8) 安全，但建议保留局部变量
- **优化点6（解密缓存扩容）**：仅增大上限，sizeOf 已存在（设计文档描述有误）

### 建议调整的优化点
- **优化点3**：建议保留为局部变量（`parseXML` 内创建），避免多源并发时互相限制
- **优化点7**：需补充 isRegex 设置逻辑，否则 ruleArticles 以 ":" 开头的源会出现解析模式错误
- **优化点8**：预连接应改为并行 async，避免串行 300-1500ms 延迟

### 设计文档与源码不符之处
1. **优化点3**：设计文档说"移至 companion object"，但原代码 `Semaphore(6)` 是 `parseXML` 方法内的局部变量（RssParserByRule.kt 行 86），不是 companion 字段
2. **优化点6**：设计文档说"新增 sizeOf 覆写"，但原代码已有 `sizeOf` 覆写（ImageUtils.kt 行 27）
3. **优化点7**：设计文档未识别 isRegex 实例状态传递风险（AnalyzeRule.kt 行 551-556）

### 建议削减的优化点
- 无需削减的优化点。8 个优化点均合理，只需按上述建议调整实施细节。
