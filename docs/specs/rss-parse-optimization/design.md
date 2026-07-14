# 技术设计：订阅源解析全流程性能优化

## Technical Approach（技术方案）

### 三批次递进实施

```
第一批（低风险顺手做）   → 第二批（高收益中风险） → 第三批（中收益低风险）
2 项，每项独立验证       2 项，线程安全重点验证   2 项，补充优化
```

每批实施后编译验证 + 安装回归测试 + 更新 updateLog.md（遵循并发文件修改规范：每阶段结束都构建复验）。

> **可选优化清单**：5.5 Semaphore 动态适配 + 2.5 getElement 缓存 + 其他 13 项原可选优化，作为补充清单按需评估实施（详见末尾"可选优化方案"章节）。

---

## 第一批：低风险顺手做（2 项）

### 1.1 优化点 2.1：AnalyzeByRegex Pattern 编译缓存（P2，收益不可感知但风险极低）

**源码验证结论**：
- `AnalyzeByRegex.kt` 是 `object`（单例），但 `getElement`/`getElements` 每次调用 `Pattern.compile(regs[vIndex])`
- 行 11 和行 34 两处编译点，6 并发协程各自编译相同 Pattern
- `Pattern.compile()` 是 CPU 密集型操作（解析语法树 + 构建 NFA/DFA）

**修改点**：`AnalyzeByRegex.kt` object 内新增 Pattern LruCache

```kotlin
// 伪代码（object 单例内）
object AnalyzeByRegex {
    // 新增：Pattern 编译缓存（key=正则字符串，value=Pattern）
    // LruCache 上限 64 条，与 AnalyzeRule.regexCache 一致
    // LruCache 自带 synchronized 保护，线程安全
    private val patternCache = LruCache<String, Pattern>(64)

    // 新增：缓存获取 Pattern 的辅助函数
    private fun getPattern(regex: String): Pattern {
        patternCache.get(regex)?.let { return it }
        val pattern = Pattern.compile(regex)
        patternCache.put(regex, pattern)
        return pattern
    }

    // 修改：行 11 和行 34 的 Pattern.compile(regs[vIndex]) 改为 getPattern(regs[vIndex])
    // val resM = getPattern(regs[vIndex]).matcher(res)  // 替换原 Pattern.compile(...)
}
```

**关键点**：
- `LruCache` 自带 `synchronized` 保护，6 并发协程访问安全
- 缓存命中时直接返回 Pattern，未命中才 `Pattern.compile()`
- 上限 64 条，避免内存泄漏（Pattern 持有 NFA/DFA 结构）

**日志要求**（改造过程日志记录规范）：
- 首次编译时 `AppLog.put("AnalyzeByRegex", "Pattern 编译: $regex")`
- 缓存命中时可选择性记录（避免高频日志）

### 1.2 优化点 4.1：RssArticle (origin,sort) 复合索引（P1，特定场景受益 >1000 条）

**源码验证结论**：
- `RssArticle.kt:10-13`：`@Entity(tableName = "rssArticles", primaryKeys = ["origin", "link", "sort"])`
- 主键索引为 `(origin, link, sort)`，但 `RssArticleDao.flowByOriginSort` 查询条件是 `where origin = :origin and sort = :sort`，跳过 link
- SQLite 复合索引遵循最左前缀原则，查询 `(origin, sort)` 无法利用 `(origin, link, sort)` 索引（link 在中间断裂）
- 实际执行用 `origin` 前缀过滤后扫描，大文章量源（>1000 条）查询效率低

**修改点1**：`RssArticle.kt` 添加 @Index 注解

```kotlin
// 伪代码
@Entity(
    tableName = "rssArticles",
    primaryKeys = ["origin", "link", "sort"],
    // 新增：(origin, sort) 复合索引，优化 flowByOriginSort 查询
    indices = [
        Index(name = "idx_origin_sort", value = ["origin", "sort"])
    ]
)
data class RssArticle(
    // ... 原有字段保持不变
)
```

**修改点2**：AppDatabase 版本升级 + Migration

**源码验证结论**：
- `AppDatabase.kt:77`：当前 `version = 93`
- `DatabaseMigrations.kt:13-25`：migrations 数组当前最后一个是 `migration_92_93`
- 本次新增 Migration 命名为 `migration_93_94`，version 升级为 94

```kotlin
// 伪代码（AppDatabase.kt）
@Database(
    entities = [/* ... */, RssArticle::class],
    version = 94  // 原 93，本次 +1
)
abstract class AppDatabase : RoomDatabase() {
    // 新增 Migration（在 DatabaseMigrations.kt 中定义）
    // 命名遵循现有 migration_XX_YY 规范
    val migration_93_94 = object : Migration(93, 94) {
        override fun migrate(database: SupportSQLiteDatabase) {
            // 创建索引（Room 自动生成，但手动 Migration 更可控）
            database.execSQL("CREATE INDEX IF NOT EXISTS idx_origin_sort ON rssArticles(origin, sort)")
        }
    }
}
```

```kotlin
// 伪代码（DatabaseMigrations.kt）
object DatabaseMigrations {
    val migrations: Array<Migration> by lazy {
        arrayOf(
            // ... 原有 migrations
            migration_89_90, migration_90_91, migration_91_92, migration_92_93,
            migration_93_94  // 新增
        )
    }
    // 新增
    private val migration_93_94 = object : Migration(93, 94) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_origin_sort ON rssArticles(origin, sort)")
        }
    }
}
```

**关键点**：
- 当前版本 93 → 新版本 94，Migration 命名 `migration_93_94`（遵循 DatabaseMigrations.kt 现有命名规范）
- 需在 `DatabaseMigrations.kt` 的 migrations 数组末尾追加 `migration_93_94`
- 使用 `@Index` 注解 + Migration 双重保证
- `fallbackToDestructiveMigration` 兜底（极端情况重建表）
- 索引创建不破坏现有数据
- RSS 文章写入频率低（每次刷新），索引增加的写入开销可接受

**日志要求**：
- Migration 执行时 `AppLog.put("AppDatabase", "创建 idx_origin_sort 索引")`
- 索引创建失败时记录错误（`kotlin.runCatching` 捕获）

> **5.5 Semaphore 动态适配已移至可选优化**：详见末尾"可选优化方案"章节。原因：Semaphore 是 `parseXML` 方法内的局部变量（非 companion 字段），改造会改变多源并发行为，收益相对有限。

---

## 第二批：高收益中风险（2 项）

### 2.1 优化点 2.2 + 5.1：scriptCache/regexCache 全局共享

**源码验证结论**：
- `AnalyzeRule.kt:81-85`：
  - `stringRuleCache = LruCache<String, List<SourceRule>>(64)` — per-instance
  - `regexCache = hashMapOf<String, Regex?>(...)` — per-instance，非线程安全
  - `scriptCache = hashMapOf<String, CompiledScript>(...)` — per-instance，非线程安全
- `RssParserByRule.kt:92`：并行化后每个列表项创建独立 AnalyzeRule 实例
- 20 项列表 × 6 并发 = 同时存在最多 6 个 AnalyzeRule 实例，每个含 3 个 Map 结构
- `scriptCache`：同一源的 JS 规则在每个 item 实例中都要重新 `RhinoScriptEngine.compile()`
- `regexCache`：正则编译重复

**修改点**：`AnalyzeRule.kt` 提升 scriptCache/regexCache 为 companion object

```kotlin
// 伪代码
class AnalyzeRule() {
    // 保持 per-instance（含 putMap 等实例状态）
    private val stringRuleCache = LruCache<String, List<SourceRule>>(64)

    // 删除实例字段 regexCache 和 scriptCache

    companion object {
        // 新增：全局共享的 scriptCache（CompiledScript 无状态，跨实例共享安全）
        // LruCache 上限 32 条，带 synchronized 保护
        // ⚠️ Rhino 1.8.1 landmine：CompiledScript.eval() 跨实例安全（基于 ThreadLocal Context）
        private val globalScriptCache = LruCache<String, CompiledScript>(32)

        // 新增：全局共享的 regexCache
        // LruCache 上限 64 条，带 synchronized 保护
        private val globalRegexCache = LruCache<String, Regex?>(64)

        // 辅助函数：获取或编译 CompiledScript
        @Synchronized
        fun getOrCompileScript(script: String): CompiledScript? {
            globalScriptCache.get(script)?.let { return it }
            return kotlin.runCatching {
                RhinoScriptEngine.compile(script).also {
                    globalScriptCache.put(script, it)
                }
            }.getOrElse {
                AppLog.put("AnalyzeRule", "JS 编译失败: ${it.message}")
                null
            }
        }

        // 辅助函数：获取或编译 Regex
        @Synchronized
        fun getOrCompileRegex(pattern: String): Regex? {
            globalRegexCache.get(pattern)?.let { return it }
            val regex = kotlin.runCatching { Regex(pattern) }.getOrNull()
            globalRegexCache.put(pattern, regex)
            return regex
        }
    }

    // 修改：原 evalJS 内部 compileScriptCache 调用改为 getOrCompileScript
    // 原 splitRule 内部 regexCache 访问改为 getOrCompileRegex
}
```

**关键点**：
- `scriptCache` 和 `regexCache` 提升为 `companion object` 全局共享
- `stringRuleCache` 保持 per-instance（含 `putMap` 等实例状态，跨实例共享不安全）
- `LruCache` 自带 `synchronized` 保护，但编译操作用 `@Synchronized` 双重保护
- `CompiledScript` 跨实例 eval 安全（RhinoScriptEngine Context.enter() 基于 ThreadLocal）
- 异常用 `kotlin.runCatching` 捕获，失败返回 null，不中断解析

**⚠️ Rhino 1.8.1 landmine 注意**：
- rhino 1.8.1 锁定（API 24 以下缺 `Arrays.setAll`，不可升级）
- `CompiledScript.eval()` 内部调用 `Context.enter()`，基于 ThreadLocal 每线程独立 Context
- 跨实例共享 `CompiledScript` 安全，但每个线程的 Context 独立
- 验证方法：6 并发协程同时 evalJS 同一 CompiledScript，确认无并发崩溃

**⚠️ ReadBook 全局单例 landmine 注意**：
- AnalyzeRule 共享缓存需 `@Synchronized` 或 `ConcurrentHashMap` 保护
- `LruCache` 自带 `synchronized`，但编译操作（`RhinoScriptEngine.compile()`）非线程安全
- 用 `@Synchronized` 注解保证编译操作的原子性

**日志要求**：
- JS 编译时 `AppLog.put("AnalyzeRule", "JS 编译并缓存: script 长度=${script.length}")`
- 缓存命中时可选记录（避免高频）
- 编译失败时记录错误

### 2.2 优化点 1.2：HTTP 响应缓存

**源码验证结论**：
- `HttpHelper.kt:70-150`：`okHttpClient` 未配置 `Cache` 目录
- OkHttp 原生支持 HTTP 缓存（基于 Cache-Control/ETag），但当前无 `cache()` 调用
- RSS 源列表刷新时，同一 URL 短时间内重复请求走完整网络请求

**修改点**：`HttpHelper.kt` 配置 OkHttp Cache

```kotlin
// 伪代码
object HttpHelper {
    // 新增：缓存目录（应用缓存目录下 okhttp_cache/）
    private val cacheDir = File(appCtx.cacheDir, "okhttp_cache").apply { mkdirs() }

    // 修改：okHttpClient 配置 Cache（保留原有 no-cache 请求头，供书源使用）
    val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .cache(Cache(cacheDir, 50L * 1024 * 1024))  // 50MB 上限
            .connectionPool(ConnectionPool(50, 5, TimeUnit.MINUTES))  // 原有配置
            // ... 其他原有配置（含 no-cache 拦截器，保持书源行为不变）
            .build()
    }

    // 新增：RSS 源专用客户端（不带 no-cache 请求头，使 OkHttp Cache 可命中）
    // 隔离影响：仅 RSS 源请求使用此客户端，书源请求仍用 okHttpClient
    val rssOkHttpClient: OkHttpClient by lazy {
        okHttpClient.newBuilder()
            // 移除 no-cache 拦截器的影响：用新拦截器覆盖
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .removeHeader("Cache-Control")  // 移除 no-cache
                    .build()
                chain.proceed(request)
            }
            .build()
    }

    // 新增：预连接辅助函数（供第三批 1.4 使用）
    // ⚠️ 修正：原伪代码 execute().close() 有误——同步 execute() 阻塞线程，且 close() 不是 Call 方法
    // 改用 execute().use { } 确保 Response 自动关闭（use 是 Closeable 扩展）
    fun warmUpConnection(url: String) {
        kotlin.runCatching {
            val request = Request.Builder().url(url).head().build()
            okHttpClient.newCall(request).execute().use { response ->
                // 仅消费 Response 以触发 TCP/TLS 连接建立，body 不读取
                // use{} 确保 Response.body() 自动关闭，避免连接泄漏
            }
        }.onFailure {
            AppLog.put("HttpHelper", "预连接失败: ${it.message}")
        }
    }
}
```

**关键点**：
- Cache 目录位于 `appCtx.cacheDir/okhttp_cache/`，应用卸载时自动清理
- `maxSize=50MB`，LRU 自动淘汰
- 仅缓存带 `Cache-Control` 或 `ETag` 头的响应（OkHttp 默认行为）
- 预连接用 `HEAD` 请求，不下载 body，仅建立 TCP/TLS 连接
- 异常用 `kotlin.runCatching` 捕获，失败不影响列表显示

#### no-cache 请求头处理（阻塞问题修复）

**源码验证结论**：
- `HttpHelper.kt:95-107` 拦截器为所有请求添加 `builder.addHeader("Cache-Control", "no-cache")`（行 105）
- OkHttp Cache 遇到请求头 `Cache-Control: no-cache` 时，会强制走网络（跳过缓存命中），导致 S6 场景不可达成
- 原有 no-cache 行为对书源是合理的（书源内容时效性要求高，且书源不依赖 HTTP 缓存优化），不应改动

**方案A（推荐）：RSS 源专用 OkHttpClient**

```kotlin
// 伪代码（见上方 rssOkHttpClient）
// 通过 newBuilder() 继承 okHttpClient 的所有配置（Cache/ConnectionPool/拦截器等）
// 再追加一个拦截器移除 Cache-Control: no-cache 请求头
// RSS 源请求链路改用 rssOkHttpClient
```

**为什么不用方案B（修改原拦截器加条件判断）**：
- 方案B 需在拦截器内区分 RSS 源 vs 书源请求，侵入性大
- 方案B 改动原 okHttpClient 行为，影响书源（违反"不影响书源"约束）
- 方案A 通过 newBuilder() 隔离，书源完全无感知

**调用点改造**：
- RSS 源列表请求（`RssParserByRule` / `AnalyzeUrl.getStrResponseAwait` 的 RSS 路径）改用 `HttpHelper.rssOkHttpClient`
- 书源请求链路保持原 `HttpHelper.okHttpClient` 不变

**⚠️ 缓存时效性策略**：
- RSS 内容时效性要求高，但同一 URL 5 秒内重复请求可接受缓存
- OkHttp 默认遵循 `Cache-Control: max-age` 头
- 对于无 `Cache-Control` 头的响应，OkHttp 默认不缓存
- 可选：配置 `CacheControl.FORCE_CACHE` 或 `FORCE_NETWORK` 策略（本方案不采用，保持默认）

**日志要求**：
- 缓存命中时 `AppLog.put("HttpHelper", "缓存命中: $pathPattern")`（只记录路径模式，不输出完整 URL）
- 缓存未命中时可选记录

---

## 第三批：中收益低风险（2 项）

### 3.1 优化点 3.1：解密缓存扩容

**源码验证结论**：
- `ImageUtils.kt:26-28`：`private val decodeCache = object : LruCache<String, ByteArray>(2 * 1024 * 1024)`  // 2MB
- `ImageUtils.kt:27`：**`override fun sizeOf(key: String, value: ByteArray): Int = value.size` 已存在**（⚠️ 修正：原方案描述"新增 sizeOf"有误，实际源码已有此覆写）
- 2MB 上限对于多图列表偏小，单张缩略图 20-100KB，仅缓存 20-100 张
- 列表快速滚动时缓存命中率低，重复解密（含 evalJS）开销大

**修改点**：`ImageUtils.kt` **仅修改 LruCache 构造参数**（sizeOf 覆写已存在，无需新增）

```kotlin
// 伪代码
object ImageUtils {
    // 修改：LruCache 上限按 maxMemory/32 动态设置（构造参数从 2 * 1024 * 1024 改为动态值）
    // 最低 4MB，最高 16MB（coerceIn）
    // minSdk 23 设备 maxMemory 通常 192MB-512MB，/32 = 6MB-16MB
    // ⚠️ sizeOf 覆写已存在（行 27），保持不变
    private val decodeCache = object : LruCache<String, ByteArray>(
        (Runtime.getRuntime().maxMemory() / 32).toInt()
            .coerceIn(4 * 1024 * 1024, 16 * 1024 * 1024)
    ) {
        // 已存在（ImageUtils.kt:27），无需新增
        override fun sizeOf(key: String, value: ByteArray): Int {
            return value.size
        }
    }

    // ... 原有逻辑保持不变
}
```

**关键点**：
- 按 `Runtime.maxMemory()/32` 动态设置，低端设备内存压力可控
- `coerceIn(4MB, 16MB)` 限定范围，避免极端值
- **`sizeOf` 覆写已存在**（行 27），本方案只改构造参数，不新增 sizeOf
- 单张图片 20-100KB，16MB 可缓存 160-800 张

**日志要求**：
- 初始化时 `AppLog.put("ImageUtils", "解密缓存上限: ${decodeCache.size()} bytes")`

> **2.5 getElement 缓存已移至可选优化**：详见末尾"可选优化方案"章节。原因：splitSourceRuleCacheString 签名扩展 allInOne 参数后存在 isRegex 路径缓存 key 误命中风险，需单独评估。

### 3.2 优化点 1.4：预连接/DNS 预解析（async 并行）

**源码验证结论**：
- RSS 源列表加载时，每篇文章的 `link` 指向不同域名
- 用户点击文章时才发起 DNS 解析 + TCP 连接 + TLS 握手，首次加载延迟高

**修改点**：`Rss.kt` 列表解析完成后预连接前 3 篇文章域名（**async 并行执行**）

```kotlin
// 伪代码
object Rss {
    fun getArticlesAwait(rule: RssRule): Await<RssArticle> {
        return Coroutine.async {
            // ... 原有解析逻辑
            val articles = RssParserByRule.parseXML(/* ... */)

            // 新增：预连接前 3 篇文章的 link 域名
            // ⚠️ 修正：原方案用 forEach 串行执行，3 个 HEAD 请求串行累积 300-1500ms 延迟
            // 改为 async{}.awaitAll() 并行执行，3 个 HEAD 请求并行，总延迟 ≈ 单次最长延迟
            articles.take(3).map { article ->
                async {
                    kotlin.runCatching {
                        val link = article.link
                        if (!link.isNullOrBlank()) {
                            HttpHelper.warmUpConnection(link)
                        }
                    }.onFailure {
                        AppLog.put("Rss", "预连接失败: ${it.message}")
                    }
                }
            }.awaitAll()

            articles
        }
    }
}
```

**关键点**：
- 仅预连接前 3 篇文章，避免过度预连接浪费资源
- **使用 `async{}.awaitAll()` 并行执行**（3 个 HEAD 请求并行，避免 forEach 串行累积延迟）
- 使用 `HEAD` 请求（HttpHelper.warmUpConnection），不下载 body
- 连接池空闲超时 5 分钟自动回收（HttpHelper 原有配置）
- 异常用 `kotlin.runCatching` 捕获，失败不影响列表显示
- 字符串判空用 `isNullOrBlank()`

**日志要求**：
- 预连接触发时 `AppLog.put("Rss", "预连接: 第${index+1}篇")`（不输出 URL）
- 预连接失败时记录错误

---

## Architecture Decisions（架构决策）

### ADR-1：scriptCache/regexCache 提升为 companion object 全局共享

- **Context（上下文）**：
  - AnalyzeRule 是 per-instance 设计，每个列表项创建独立实例
  - `scriptCache`/`regexCache` 是实例字段，同一源的 JS/Regex 规则在每个 item 实例中重复编译
  - Rhino JS 编译是重操作（AST 解析 + 字节码生成），20 项列表重复编译 20 次
  - 6 并发协程同时编译相同 Pattern/CompiledScript，CPU 浪费严重
  - AnalyzeRule 实例创建开销大（3 个 Map 结构分配），增加 GC 压力

- **Decision（决策）**：
  - 将 `scriptCache` 和 `regexCache` 从实例字段提升为 `companion object` 级别全局缓存
  - `scriptCache` 改为 `LruCache<String, CompiledScript>`（上限 32 条，带同步）
  - `regexCache` 改为 `LruCache<String, Regex?>`（上限 64 条，带同步）
  - `stringRuleCache` 保持 per-instance（含 `putMap` 等实例状态，跨实例共享不安全）
  - **`topScopeRef`（行 84）、`evalJSCallCount`（行 85）保持 per-instance**：这两个是与 source/prototype 绑定的实例状态，topScopeRef 持有 WeakReference<Scriptable> 作为 JS 执行的顶层作用域，evalJSCallCount 记录单实例 JS 调用次数。跨实例共享会导致 JS 执行上下文污染和调用计数错乱，必须保持 per-instance
  - 编译操作用 `@Synchronized` 注解保证原子性

- **Consequences（后果）**：
  - ✅ 含 JS 源每项解析减少 2-10ms，20 项列表累积减少 40-200ms
  - ✅ 减少 AnalyzeRule 实例创建的 Map 分配开销，降低 30% GC 时间
  - ✅ `CompiledScript` 跨实例 eval 安全（RhinoScriptEngine Context.enter() 基于 ThreadLocal）
  - ✅ `topScopeRef`/`evalJSCallCount` 保持 per-instance，JS 执行上下文不跨实例污染
  - ⚠️ 需确保 `LruCache` 的 `synchronized` 保护足够（已验证，LruCache 自带同步）
  - ⚠️ Rhino 1.8.1 landmine：不可升级，但 `CompiledScript` 跨实例共享安全
  - ⚠️ ReadBook 全局单例 landmine：`@Synchronized` 保护编译操作
  - ⚠️ `getOrPutLimit`（MapExtensions.kt:21）是 `MutableMap<K,V>` 扩展，`LruCache` 不是 MutableMap 子类，`compileScriptCache`/`compileRegexCache` 方法体需重写（详见 File Changes 第5项）

### ADR-2：HTTP 响应缓存策略（仅缓存带 Cache-Control 头的响应）

- **Context（上下文）**：
  - RSS 源列表刷新时，同一 URL 短时间内重复请求走完整网络请求
  - OkHttp 原生支持 HTTP 缓存（基于 Cache-Control/ETag），但当前无 `cache()` 配置
  - RSS 内容时效性要求高，但同一 URL 5 秒内重复请求可接受缓存
  - 缓存目录需管理大小上限，避免低端设备磁盘压力

- **Decision（决策）**：
  - 在 `HttpHelper.okHttpClient` 配置 `Cache(directory, maxSize=50MB)`
  - 缓存目录位于 `appCtx.cacheDir/okhttp_cache/`
  - 保持 OkHttp 默认缓存策略：仅缓存带 `Cache-Control` 或 `ETag` 头的响应
  - 不强制配置 `FORCE_CACHE` 或 `FORCE_NETWORK`，保持灵活性

- **Consequences（后果）**：
  - ✅ 命中缓存时减少 200-2000ms（取决于网络延迟）
  - ✅ 降低流量消耗
  - ✅ 仅缓存带 Cache-Control 头的响应，避免缓存不可缓存的内容
  - ⚠️ 缓存目录占用磁盘空间（上限 50MB，LRU 自动淘汰）
  - ⚠️ 无 Cache-Control 头的响应不缓存（可接受，保持默认行为）
  - ⚠️ **需处理 no-cache 请求头**：`HttpHelper.kt:105` 拦截器为所有请求添加 `Cache-Control: no-cache`，会导致 OkHttp Cache 跳过命中。本方案通过新增 `rssOkHttpClient`（基于 `okHttpClient.newBuilder()` 追加拦截器移除 no-cache）隔离影响，RSS 源请求用专用客户端，书源请求保持原行为不变（详见 1.2 "no-cache 请求头处理"章节）

### ADR-3：Semaphore 动态适配 CPU 核心数（coerceIn(2,8)）— 已降为可选

> ⚠️ **本 ADR 已降为可选优化**。原因：源码核实发现 `Semaphore(6)` 是 `parseXML` 方法内的局部变量（非 companion 字段），改造会改变多源并发行为。如实施，**保留为局部变量**，不移至 companion object。

- **Context（上下文）**：
  - `RssParserByRule.kt:86`：`val parseSemaphore = Semaphore(6)` 是 `parseXML` 方法内的**局部变量**（⚠️ 修正：原描述误认为是 companion 字段）
  - 8 核设备未充分利用 CPU（6 < 8）
  - 2-4 核低端设备过度并发（6 > 核心数），上下文切换开销大
  - rss-image-decrypt-optimization 已验证 Semaphore 限流的有效性

- **Decision（决策）**（可选）：
  - `Semaphore(6)` 改为 `Semaphore(Runtime.getRuntime().availableProcessors().coerceIn(2, 8))`
  - **保留为 `parseXML` 方法内局部变量**，不移至 companion object（避免改变多源并发行为）
  - 下限 2（保证最低并行度），上限 8（避免过度并发）

- **Consequences（后果）**：
  - ✅ 低端设备（2-4 核）减少上下文切换开销
  - ✅ 高端设备（8 核）提升吞吐
  - ✅ 与 rss-image-decrypt-optimization 的并行化框架兼容
  - ⚠️ 不同设备行为不一致（可接受，适配设备性能是目标）
  - ⚠️ **改为局部变量后**：每次 `parseXML` 调用都会新建 Semaphore 实例（`availableProcessors()` 是 native 缓存值，开销可忽略）

### ADR-4：Pattern 缓存用 LruCache 而非 HashMap（防内存泄漏）

- **Context（上下文）**：
  - `AnalyzeByRegex` 每次调用 `Pattern.compile()` 重新编译
  - Pattern 对象持有编译后的 NFA/DFA 结构，缓存过多占用内存
  - 6 并发协程各自编译相同 Pattern，CPU 浪费
  - F-P1-C4 已将 `AnalyzeRule.stringRuleCache` 改为 `LruCache(64)` 修复无界 HashMap 内存泄漏

- **Decision（决策）**：
  - 在 `AnalyzeByRegex` object 内新增 `Pattern` LruCache（上限 64 条）
  - key=正则字符串，value=Pattern
  - `LruCache` 自带 `synchronized` 保护，6 并发协程访问安全
  - 与 `AnalyzeRule.regexCache` 模式一致（已验证 LruCache 方案）

- **Consequences（后果）**：
  - ✅ Regex 源每项解析减少 0.5-2ms，20 项列表累积减少 10-40ms
  - ✅ LruCache 上限 64 条，避免内存泄漏
  - ✅ `synchronized` 保护线程安全
  - ⚠️ 缓存淘汰时 Pattern 被 GC（可接受，重新编译开销可接受）

---

## Data Flow（数据流）

### 优化前：RSS 源列表解析流程

```
用户打开列表
    ↓
Rss.getArticlesAwait
    ↓
AnalyzeUrl.getStrResponseAwait（网络请求，无缓存）
    ↓
RssParserByRule.parseXML
    ↓
rssRules.map { rule → async { semaphore.withPermit {
    ↓
    新建 AnalyzeRule 实例（分配 3 个 Map）
    ↓
    analyzeRule.getString(ruleStr)
    ↓
    splitSourceRule（无缓存，每次正则匹配）
    ↓
    规则引擎分发：
    ├─ AnalyzeByRegex: Pattern.compile()（每次重新编译）
    ├─ AnalyzeByJSoup: element.select()（每次编译 CSS）
    ├─ AnalyzeByXPath: node.sel()（每次编译 XPath）
    └─ evalJS: RhinoScriptEngine.compile()（每次重新编译 JS）
    ↓
    返回解析结果
}}}.awaitAll()
    ↓
RssArticle 入库
    ↓
列表渲染（ImageUtils.decode 重复解密，2MB 缓存易满）
```

### 优化后：RSS 源列表解析流程

```
用户打开列表
    ↓
Rss.getArticlesAwait
    ↓
AnalyzeUrl.getStrResponseAwait
    ↓ HTTP 响应缓存命中？（第二批 1.2）
    ↓ 是 → 直接返回缓存响应（减少 200-2000ms）
    ↓ 否 → 走完整网络请求 → 缓存响应（带 Cache-Control 头时）
    ↓
RssParserByRule.parseXML
    ↓ Semaphore(6)（可选 5.5 未实施时维持原值；若实施则改为 coerceIn(2,8) 局部变量）
    ↓
rssRules.map { rule → async { semaphore.withPermit {
    ↓
    新建 AnalyzeRule 实例（仅分配 stringRuleCache，scriptCache/regexCache 全局共享）
    ↓
    analyzeRule.getString(ruleStr)
    ↓
    splitSourceRule（无缓存，每次正则匹配）（可选 2.5 未实施；若实施则走 splitSourceRuleCacheString）
    ↓
    规则引擎分发：
    ├─ AnalyzeByRegex: getPattern()（Pattern LruCache 命中？）（第一批 2.1）
    │   ├─ 命中 → 直接返回 Pattern
    │   └─ 未命中 → Pattern.compile() → 缓存
    ├─ AnalyzeByJSoup: element.select()（暂不优化，2.3 可选）
    ├─ AnalyzeByXPath: node.sel()（暂不优化，2.4 可选）
    └─ evalJS: getOrCompileScript()（scriptCache 命中？）（第二批 2.2）
        ├─ 命中 → 直接返回 CompiledScript
        └─ 未命中 → RhinoScriptEngine.compile() → 缓存（全局共享）
    ↓
    返回解析结果
}}}.awaitAll()
    ↓
RssArticle 入库（走 idx_origin_sort 索引查询）（第一批 4.1）
    ↓
列表渲染
    ↓ ImageUtils.decode 缓存命中？（第三批 3.1，扩容后 4-16MB）
    ↓ 是 → 直接返回解码图片
    ↓ 否 → 解密 → 缓存
    ↓
预连接前 3 篇文章域名（第三批 1.4，async 并行）
    ↓ HttpHelper.warmUpConnection（HEAD 请求，3 个并行 awaitAll）
```

### 关键性能提升点对比

| 阶段 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 网络请求 | 每次完整请求 | 命中缓存直接返回 | 200-2000ms |
| Pattern 编译 | 每项重新编译 | LruCache 命中 | 0.5-2ms/项 |
| JS 编译 | 每项重新编译 | 全局 scriptCache 命中 | 2-10ms/项 |
| 规则拆分（可选 2.5） | 每次正则匹配 | LruCache 命中（**可选，未实施则维持原状**） | 0.1-0.3ms/项 |
| DB 查询 | O(n) 扫描 | O(log n) 索引 | 50-200ms（大列表 >1000 条） |
| 图片解密 | 2MB 缓存易满 | 4-16MB 缓存 | 80% 解密调用 |
| 实例创建 | 3 个 Map/实例 | 1 个 Map/实例 | 30% GC 时间 |
| 预连接 | 点击时才 DNS+TCP+TLS | 列表加载后 async 并行预连接 | 300-1000ms（首次内容页） |

---

## File Changes（文件变更）

### 第一批

#### 1. AnalyzeByRegex.kt

- **路径**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByRegex.kt`
- **变更**：
  - 新增 `patternCache: LruCache<String, Pattern>(64)` 字段
  - 新增 `getPattern(regex: String): Pattern` 辅助函数
  - 行 11、行 34 的 `Pattern.compile(regs[vIndex])` 改为 `getPattern(regs[vIndex])`
- **风险**：低（LruCache 自带同步，object 单例全局共享安全）

#### 2. RssArticle.kt

- **路径**：`app/src/main/java/io/legado/app/data/entities/RssArticle.kt`
- **变更**：
  - `@Entity` 注解新增 `indices = [Index(name = "idx_origin_sort", value = ["origin", "sort"])]`
- **风险**：低（注解变更，Room 自动处理）

#### 3. AppDatabase.kt + DatabaseMigrations.kt

- **路径**：`app/src/main/java/io/legado/app/data/AppDatabase.kt` + `app/src/main/java/io/legado/app/data/DatabaseMigrations.kt`
- **变更**：
  - `AppDatabase.kt:77`：`version = 93` 改为 `version = 94`
  - `DatabaseMigrations.kt`：migrations 数组末尾追加 `migration_93_94`
  - `DatabaseMigrations.kt`：新增 `private val migration_93_94 = object : Migration(93, 94) { ... }`（执行 `CREATE INDEX IF NOT EXISTS idx_origin_sort ON rssArticles(origin, sort)`）
- **风险**：低（Room Migration 标准流程，版本号 93→94 明确）

#### 4. RssParserByRule.kt（已移至可选，本批不涉及）

> **5.5 Semaphore 动态适配已移至可选优化**：原第一批第 4 项移除。原因：Semaphore 是 `parseXML` 方法内局部变量，改造会改变多源并发行为。如实施可选优化，详见末尾"可选优化方案"章节。

### 第二批

#### 5. AnalyzeRule.kt

- **路径**：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt`
- **变更**：
  - 删除实例字段 `regexCache`（行 82）和 `scriptCache`（行 83）
  - **保持 per-instance**：`topScopeRef`（行 84，WeakReference<Scriptable>）、`evalJSCallCount`（行 85）—— 这两个是与 source/prototype 绑定的实例状态，跨实例共享会导致 JS 执行上下文污染，必须保持 per-instance
  - companion object 新增 `globalScriptCache: LruCache<String, CompiledScript>(32)`
  - companion object 新增 `globalRegexCache: LruCache<String, Regex?>(64)`
  - 新增 `getOrCompileScript(script: String): CompiledScript?`（@Synchronized）
  - 新增 `getOrCompileRegex(pattern: String): Regex?`（@Synchronized）
  - **重写 `compileScriptCache`（行 876-880）方法体**：
    - 原实现：`return scriptCache.getOrPutLimit(jsStr, 16) { RhinoScriptEngine.compile(jsStr) }`
    - ⚠️ `getOrPutLimit` 是 `MutableMap<K,V>` 扩展（MapExtensions.kt:21），`android.util.LruCache` 不是 MutableMap 子类，原代码在实例 `hashMapOf` 下可用，提升为 LruCache 后不兼容
    - 新实现：`return getOrCompileScript(jsStr) ?: throw NoStackTraceException("JS 编译失败")`（复用 companion 的 @Synchronized 方法）
  - **重写 `compileRegexCache`（行 521-529）方法体**：
    - 原实现：`return regexCache.getOrPutLimit(regex, 16) { try { regex.toRegex() } catch (e: Exception) { null } }`
    - ⚠️ 同样因 LruCache 不是 MutableMap 而 `getOrPutLimit` 不兼容
    - 新实现：`return getOrCompileRegex(regex)`（复用 companion 的 @Synchronized 方法）
  - `evalJS` 内部 `compileScriptCache` 调用保持不变（方法签名不变，仅方法体重写）
  - `splitRule` 内部 `compileRegexCache` 调用保持不变（方法签名不变，仅方法体重写）
- **风险**：中（线程安全需重点验证，@Synchronized 保护编译操作；getOrPutLimit 不兼容需方法体重写）

#### 6. HttpHelper.kt

- **路径**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
- **变更**：
  - 新增 `cacheDir` 字段（`File(appCtx.cacheDir, "okhttp_cache")`）
  - `okHttpClient` 配置 `.cache(Cache(cacheDir, 50L * 1024 * 1024))`（保留原有 no-cache 拦截器，书源行为不变）
  - 新增 `rssOkHttpClient` 字段（基于 `okHttpClient.newBuilder()` 追加拦截器移除 `Cache-Control: no-cache` 请求头，供 RSS 源请求使用）
  - 新增 `warmUpConnection(url: String)` 辅助函数（供第三批使用，用 `execute().use { }` 模式确保 Response 自动关闭）
- **风险**：中（缓存时效性策略 + no-cache 隔离需验证 RSS 源走 rssOkHttpClient、书源走 okHttpClient）

### 第三批

#### 7. ImageUtils.kt

- **路径**：`app/src/main/java/io/legado/app/utils/ImageUtils.kt`
- **变更**：
  - `decodeCache` 上限从 `2 * 1024 * 1024` 改为 `(Runtime.getRuntime().maxMemory() / 32).toInt().coerceIn(4 * 1024 * 1024, 16 * 1024 * 1024)`
  - **`sizeOf` 覆写已存在**（行 27，`override fun sizeOf(key: value:): Int = value.size`），**无需新增**（⚠️ 修正：原方案描述"新增 sizeOf"有误）
- **风险**：低（动态适配，coerceIn 限定范围；sizeOf 已存在无新增风险）

#### 8. AnalyzeRule.kt（已移至可选，本批不涉及）

> **2.5 getElement 缓存已移至可选优化**：原第三批第 8 项移除。原因：splitSourceRuleCacheString 签名扩展 allInOne 参数后存在 isRegex 路径缓存 key 误命中风险，需单独评估。如实施可选优化，详见末尾"可选优化方案"章节。

#### 9. Rss.kt

- **路径**：`app/src/main/java/io/legado/app/model/rss/Rss.kt`
- **变更**：
  - `getArticlesAwait` 列表解析完成后，新增预连接前 3 篇文章域名逻辑
  - 调用 `HttpHelper.warmUpConnection(article.link)`
  - **使用 `async{}.awaitAll()` 并行执行**（3 个 HEAD 请求并行，避免 forEach 串行累积延迟）
- **风险**：低（HEAD 请求，异常捕获不影响列表显示；async 并行需确保 Coroutine 上下文正确）

---

## Landmines 注意事项

> 以下 landmines 来自 AGENTS.md "Landmines 核心" 章节，本设计已规避，实施时需持续关注。

### 1. jsoup 1.16.2 锁定

- **影响**：2.3 CSS 选择器缓存方案需确认不触发 jsoup#2017 破坏性变更
- **本设计处理**：2.3 列入可选优化，暂不实施；待 jsoup 升级路径明确后再评估
- **验证方法**：如未来实施 2.3，需在 jsoup 1.16.2 上测试 `Evaluator` 缓存是否绑定 Document

### 2. rhino 1.8.1 锁定

- **影响**：2.2 scriptCache 共享需确认 `CompiledScript` 跨实例 eval 安全
- **本设计处理**：
  - `CompiledScript.eval()` 内部调用 `Context.enter()`，基于 ThreadLocal 每线程独立 Context
  - 跨实例共享 `CompiledScript` 安全（rss-image-decrypt-optimization 已验证 Rhino 并行安全）
  - 6 并发协程同时 evalJS 同一 CompiledScript，每线程独立 Context
- **验证方法**：第二批实施后，6 并发协程同时 evalJS 同一 CompiledScript，确认无并发崩溃

### 3. hutool 5.8.22 锁定

- **影响**：书源加解密依赖，不可升级
- **本设计处理**：本优化不涉及 hutool 升级，无影响

### 4. ReadBook 全局单例

- **影响**：AnalyzeRule 共享缓存需 `@Synchronized` 或 `ConcurrentHashMap` 保护
- **本设计处理**：
  - `globalScriptCache` 和 `globalRegexCache` 用 `LruCache`（自带 `synchronized`）
  - 编译操作（`RhinoScriptEngine.compile()`、`Regex()`）用 `@Synchronized` 注解保证原子性
  - `stringRuleCache` 保持 per-instance（含 `putMap` 等实例状态，跨实例共享不安全）
- **验证方法**：第二批实施后，6 并发协程同时编译相同 JS/Regex，确认无数据错乱

### 5. NoStackTraceException

- **影响**：所有业务异常继承此类，覆写 `fillInStackTrace()`
- **本设计处理**：异常用 `kotlin.runCatching` 捕获，错误用 `Coroutine.onError`，符合项目规范
- **验证方法**：编译验证无异常类型不匹配

### 6. Vue3 构建

- **影响**：vite build 后 sync.js 仅在 GitHub Actions 执行，本地需手动复制
- **本设计处理**：本优化不涉及前端变更，无影响

---

## 风险评估

### 按严重度排序的风险

| 风险 | 概率 | 影响 | 缓解措施 | 验证状态 |
|------|------|------|---------|---------|
| **scriptCache/regexCache 共享后线程不安全** | 中（若不强制） | 致命（崩溃/数据错乱） | LruCache 自带 synchronized + @Synchronized 保护编译操作 | ⚠️ 待源码验证 |
| **HTTP 缓存导致内容陈旧** | 低 | 中（用户体验） | 仅缓存带 Cache-Control 头的响应，OkHttp 默认遵循 max-age | ✅ 设计保证 |
| **RssArticle 索引迁移失败** | 低 | 中（数据丢失） | Room Migration + fallbackToDestructiveMigration 兜底 | ✅ 设计保证 |
| **解密缓存扩容导致 OOM** | 低 | 中（崩溃） | coerceIn(4MB, 16MB) 限定范围，按 maxMemory/32 动态设置 | ✅ 设计保证 |
| **Pattern LruCache 内存泄漏** | 低 | 低（内存占用） | LruCache 上限 64 条，LRU 自动淘汰 | ✅ 设计保证 |
| **Semaphore 动态值不稳定** | 低 | 低（行为不一致） | coerceIn(2,8) 限定范围 | ✅ 设计保证 |
| **预连接浪费流量** | 低 | 低（流量消耗） | 仅预连接前 3 篇，HEAD 请求，连接池 5 分钟回收 | ✅ 设计保证 |

### 已排除的风险

| 风险点 | 排除依据 |
|--------|---------|
| Rhino JS 引擎并发不安全 | RhinoScriptEngine Context.enter() 基于 ThreadLocal（rss-image-decrypt-optimization 已验证） |
| AnalyzeRule 有共享静态状态 | ⚠️ 修正：提升后 companion object 含可变 LruCache（globalScriptCache/globalRegexCache），但通过 `LruCache` 自带 `synchronized` + `@Synchronized` 编译方法双重保护线程安全；`topScopeRef`/`evalJSCallCount` 保持 per-instance 不共享 |
| OkHttpClient Cache 影响书源 | ⚠️ 修正：Cache 配置在 `okHttpClient` 上（书源共享），但书源请求带 `Cache-Control: no-cache` 请求头（HttpHelper.kt:105），OkHttp 遇到 no-cache 会跳过缓存命中走网络，故书源不受影响；RSS 源用专用 `rssOkHttpClient`（移除 no-cache）才命中缓存 |
| RssArticle 索引迁移失败 | Room 自动迁移 + fallbackToDestructiveMigration 兜底；Migration 版本号明确为 93→94 |
| Pattern LruCache 并发访问 | LruCache 自带 synchronized 保护 |

---

## 测试策略

### 单元测试

- **Pattern 缓存**：验证相同正则字符串命中缓存，不同正则字符串未命中
- **scriptCache 共享**：验证多实例共享同一 CompiledScript
- **HTTP 缓存**：验证带/不带 Cache-Control 头的响应缓存行为
- **解密缓存扩容**：验证 LruCache 上限按 maxMemory 动态设置

### 集成测试

- **Regex 源列表加载**：验证 Pattern 缓存命中，解析时间减少
- **JS 源列表加载**：验证 scriptCache 共享，JS 编译只发生一次
- **大列表源数据库查询**：验证 (origin,sort) 索引生效，查询效率提升
- **图片源列表滚动**：验证解密缓存命中率提升

### 回归测试

- **普通订阅源**：验证无 JS/Regex/图片解密的源不受影响
- **书源解析**：验证 Cache 配置不影响书源请求（书源走 okHttpClient 带 no-cache，不命中缓存）
- **RSS 源缓存命中**：验证 RSS 源走 rssOkHttpClient（移除 no-cache）后命中缓存
- **调试功能**：验证调试日志正常输出

---

## 审查修订记录

> 本章节记录根据审查报告修订的所有问题，按严重程度排序。

### 阻塞问题修复（2 项）

#### 阻塞1：HTTP 缓存方案被 `Cache-Control: no-cache` 请求头阻断

- **根因**：`HttpHelper.kt:105` 拦截器为所有请求添加 `builder.addHeader("Cache-Control", "no-cache")`，OkHttp Cache 遇到 no-cache 指令跳过缓存命中
- **修复位置**：
  - design.md 1.2 HTTP响应缓存方案：新增"no-cache 请求头处理"章节，方案A 新增 `rssOkHttpClient`（基于 `okHttpClient.newBuilder()` 移除 no-cache）
  - design.md ADR-2 Consequences：补充需处理 no-cache 请求头说明
  - design.md File Changes 第6项：补充 `rssOkHttpClient` 字段
  - design.md 已排除的风险表：修正 OkHttpClient Cache 影响书源条目
  - spec.md S6 场景：补充可达成性前提（使用不带 no-cache 的客户端）

#### 阻塞2：splitSourceRuleCacheString 签名不兼容 allInOne

- **根因**：`splitSourceRuleCacheString(ruleStr: String?)` 无 allInOne 参数（行 534-540），但 getElement(行382)/getElements(行417) 调用 `splitSourceRule(ruleStr, true)`（allInOne=true）
- **修复位置**：
  - design.md 3.2 节：伪代码改为 `splitSourceRuleCacheString(ruleStr: String?, allInOne: Boolean = false)`，内部调用 `splitSourceRule(ruleStr, allInOne)`，缓存 key 用复合形式区分语义
  - design.md 3.2 节：getElement/getElements 调用改为 `splitSourceRuleCacheString(ruleStr, true)`
  - design.md File Changes 第8项：明确签名扩展 + 调用点改造

### 失误修复（5 项）

#### 失误1：splitSourceRuleCacheString 签名描述错误

- **修复**：design.md 3.2 节源码验证结论修正为实际签名 `splitSourceRuleCacheString(ruleStr: String?)`（无 allInOne 参数）

#### 失误2：splitSourceRule 行号引用错误

- **修复**：design.md 3.2 节修正行号引用：`splitSourceRule` 在 545-588（非原描述的 559-580），`splitSourceRuleCacheString` 在 534-540

#### 失误3：getOrPutLimit 与 LruCache 不兼容

- **根因**：`MapExtensions.kt:21` `getOrPutLimit` 是 `MutableMap<K,V>` 扩展，`android.util.LruCache` 不是 MutableMap 子类
- **修复位置**：
  - design.md File Changes 第5项：补充 compileScriptCache/compileRegexCache 的 getOrPutLimit 调用需删除，改用 `get()?.let {} ?: compile().also { put() }` 模式
  - design.md ADR-1 Consequences：补充 getOrPutLimit 不兼容说明

#### 失误4：compileScriptCache/compileRegexCache 需同步修改

- **修复**：design.md File Changes 第5项明确列出 compileScriptCache（行 876-880）和 compileRegexCache（行 521-529）的方法体重写方案，复用 companion 的 @Synchronized 方法

#### 失误5：预连接方案 warmUpConnection 实现有误

- **根因**：`okHttpClient.newCall(request).execute().close()` 中同步 execute() 阻塞线程，.close() 不是 Call 方法
- **修复**：design.md 1.2 节 warmUpConnection 伪代码修正为 `okHttpClient.newCall(request).execute().use { response -> }`，use 是 Closeable 扩展确保 Response 自动关闭

### 缺失补充（6 项）

#### 缺失1：topScopeRef 保持 per-instance 说明

- **修复位置**：
  - design.md ADR-1 Decision：补充 topScopeRef(行84)、evalJSCallCount(行85) 保持 per-instance 说明（与 source/prototype 绑定的实例状态）
  - design.md ADR-1 Consequences：补充 ✅ topScopeRef/evalJSCallCount 保持 per-instance
  - design.md File Changes 第5项：明确列出保持 per-instance 的字段
  - design.md 已排除的风险表：修正 AnalyzeRule 有共享静态状态条目

#### 缺失2：测试场景补充

- **修复**：spec.md Scenarios 新增 S10（6 并发协程同时解析同一 JS 源，验证无并发崩溃/数据错乱）、S11（6 并发协程同时编译相同 JS/Regex，验证 @Synchronized 互斥生效）、S12（注入超过 LruCache 上限的规则，验证 LRU 淘汰行为正确）

#### 缺失3：Room Migration 具体版本号

- **修复**：design.md 第一批 1.2 节明确当前版本 93 → 新版本 94，Migration 命名 `migration_93_94`，需在 DatabaseMigrations.kt migrations 数组末尾追加
- design.md File Changes 第3项同步更新版本号 93→94

#### 缺失4：HTTP 缓存场景 S6 可达成性

- **修复**：spec.md S6 场景补充可达成性前提（使用不带 no-cache 的客户端）+ 隔离影响说明

#### 缺失5：design.md "已排除风险"表修正

- **修复**：design.md 已排除的风险表修正两条：
  - AnalyzeRule 有共享静态状态：补充提升后 companion object 含可变 LruCache 但通过双重 synchronized 保护
  - OkHttpClient Cache 影响书源：补充书源带 no-cache 请求头跳过缓存命中，RSS 源用专用客户端才命中

#### 缺失6：预连接方案修正

- **修复**：已合并到失误5，warmUpConnection 伪代码已修正

### 调整方案修订（用户批准，1 项综合调整）

> 2026-07-14：根据用户批准的调整方案，核心优化从 8 项减至 6 项，修正 3 处源码不符，调整收益定位。

#### 调整1：核心优化从 8 项减至 6 项（5.5 和 2.5 降为可选）

- **调整内容**：
  - 第一批：3 项 → 2 项（移除 5.5 Semaphore）
  - 第二批：2 项不变
  - 第三批：3 项 → 2 项（移除 2.5 getElement 缓存）
  - 新增"可选优化方案"章节：包含 5.5 Semaphore（保留为局部变量）+ 2.5 getElement 缓存（含 isRegex 风险说明）
- **修复位置**：
  - spec.md Scope 表：5.5、2.5 批次改为"可选"
  - spec.md 22 个优化点清单：5.5、2.5 移至可选区域，并补充风险说明
  - spec.md Approach 三批分组：第一批/第三批表格移除对应行
  - spec.md 新增"可选优化清单"章节（15 项，含 5.5 和 2.5）
  - spec.md R3/R7 章节标注为"可选"
  - spec.md S5 场景标注 Semaphore 部分依赖可选优化 5.5
  - spec.md Intent 第4条标注为可选
  - spec.md Drawbacks 表 Semaphore 行标注为可选
  - design.md 三批次递进实施文字调整为 2+2+2
  - design.md 第一批章节标题改为"低风险顺手做（2 项）"
  - design.md 第一批移除 1.3 优化点 5.5 Semaphore 章节
  - design.md 第三批章节标题改为"中收益低风险（2 项）"
  - design.md 第三批移除 3.2 优化点 2.5 getElement 缓存章节
  - design.md 新增"可选优化方案"章节（含 5.5 和 2.5 完整方案）
  - design.md ADR-3 标注为"已降为可选"
  - design.md File Changes 第一批第4项、第三批第8项标注"已移至可选"
  - design.md 数据流图调整 5.5/2.5 标注
  - design.md 关键性能提升点对比表：规则拆分行标注为可选

#### 调整2：修正 3 处源码不符

- **源码不符1：Semaphore 是局部变量**
  - 根因：`RssParserByRule.kt:86` 的 `Semaphore(6)` 是 `parseXML` 方法内的局部变量，不是 companion 字段
  - 修复：design.md ADR-3 Decision 改为"保留为 `parseXML` 方法内局部变量，不移至 companion object"；spec.md R3.1/R3.3 同步修正；可选优化方案中 5.5 明确"保留为局部变量"
- **源码不符2：sizeOf 覆写已存在**
  - 根因：`ImageUtils.kt:27` 已有 `override fun sizeOf(key: value:): Int = value.size`
  - 修复：design.md 3.1 节源码验证结论补充"sizeOf 已存在"；修改点改为"仅修改 LruCache 构造参数"；关键点明确"sizeOf 覆写已存在，本方案只改构造参数"；File Changes 第7项同步修正
- **源码不符3：预连接 forEach 改 async 并行**
  - 根因：原方案用 `forEach`（串行），3 个 HEAD 请求串行累积 300-1500ms 延迟
  - 修复：design.md 3.2 节（原 3.3）伪代码改为 `articles.take(3).map { async { ... } }.awaitAll()`；关键点补充"使用 async{}.awaitAll() 并行执行"；File Changes 第9项同步补充；spec.md R8.2 新增"async 并行执行"要求；数据流图预连接部分标注"async 并行"

#### 调整3：收益定位修正

- **2.1 Pattern 缓存**：P1 → P2（收益 10-40ms 不可感知，但保留第一批因风险极低可顺手做）
  - 修复位置：spec.md 优化点清单 2.1 优先级 P1→P2；spec.md Approach 第一批标题改为"低风险顺手做"；design.md 第一批章节标题同步；design.md 1.1 节标题补充"P2，收益不可感知但风险极低"
- **4.1 RssArticle 索引**：原标"立即受益"→ "特定场景受益（>1000 条）"（场景覆盖率 <10%）
  - 修复位置：spec.md 优化点清单 4.1 描述补充"特定场景受益：>1000 条"；spec.md Approach 第一批表格 4.1 收益列改为"特定场景受益"；design.md 1.2 节标题补充"P1，特定场景受益 >1000 条"；design.md 关键性能提升点对比表 DB 查询行节省列改为"50-200ms（大列表 >1000 条）"

---

## 可选优化方案（按需评估实施）

> 以下方案未列入三批实施，作为补充清单按需评估。实施前需单独评估收益与风险，并补充对应 spec/design 章节。本章节仅详细描述从三批移出的 5.5 Semaphore 和 2.5 getElement 缓存两项，其余 13 项见 spec.md 可选优化清单。

### 可选1：5.5 Semaphore 动态适配 CPU 核心数（保留为局部变量）

**源码验证结论**：
- `RssParserByRule.kt:86`：`val parseSemaphore = Semaphore(6)` 是 `parseXML` 方法内的**局部变量**（⚠️ 非 companion 字段）
- 8 核设备未充分利用 CPU（6 < 8），2-4 核低端设备过度并发（6 > 核心数）导致调度开销

**修改点**：`RssParserByRule.kt` `parseXML` 方法内 Semaphore 改为动态值（**保留为局部变量**）

```kotlin
// 伪代码
object RssParserByRule {
    fun parseXML(...) {
        // 修改：Semaphore 限流值动态适配 CPU 核心数
        // ⚠️ 保留为 parseXML 方法内局部变量，不移至 companion object
        // 原因：移至 companion 会改变多源并发行为（多个源共享同一 Semaphore 限流）
        val parseSemaphore = Semaphore(
            Runtime.getRuntime().availableProcessors().coerceIn(2, 8)
        )
        // ... 原有逻辑保持不变
    }
}
```

**关键点**：
- `coerceIn(2, 8)` 限定范围：2 核设备用 2，8 核及以上设备用 8
- **保留为局部变量**：每次 `parseXML` 调用新建 Semaphore 实例（`availableProcessors()` 是 native 缓存值，开销可忽略）
- **不移至 companion object**：避免改变多源并发行为（多个 RSS 源同时解析时，原行为是各自独立限流，移至 companion 会变成共享限流）
- 与 rss-image-decrypt-optimization 的并行化框架兼容

**风险评估**：
- ⚠️ **改变多源并发行为**：即使保留为局部变量，限流值从固定 6 变为动态 2-8，低端设备并发度降低，可能影响多源同时解析的吞吐
- ✅ 保留为局部变量则不影响多源隔离（每个源解析独立限流）

**日志要求**：
- `parseXML` 调用时 `AppLog.put("RssParserByRule", "Semaphore 限流值: ${availableProcessors().coerceIn(2,8)}")`

### 可选2：2.5 getElement 走缓存（含 isRegex 风险说明）

**源码验证结论**：
- `AnalyzeRule.kt:545-588`：`splitSourceRule(ruleStr: String?, allInOne: Boolean = false)` 每次用 `JS_PATTERN.matcher(ruleStr)` 和 `WebJS_PATTERN.matcher(ruleStr)` 遍历
- `splitSourceRuleCacheString`（行 534-540）有 LruCache 缓存，**但当前签名是 `splitSourceRuleCacheString(ruleStr: String?)`，无 allInOne 参数**，内部调用 `splitSourceRule(ruleStr)`（allInOne 默认 false）
- `getElement`（行 382）/`getElements`（行 417）当前调用 `splitSourceRule(ruleStr, true)`（allInOne=true），无法直接替换为现有 `splitSourceRuleCacheString`（会丢失 allInOne=true 语义）

**修改点**：`AnalyzeRule.kt` 改造 splitSourceRuleCacheString 签名 + getElement/getElements 改用缓存版本

```kotlin
// 伪代码
class AnalyzeRule {
    // 修改：splitSourceRuleCacheString 行 534-540 区域
    // ⚠️ 阻塞修复：原签名 splitSourceRuleCacheString(ruleStr: String?) 无 allInOne 参数
    // 改为带 allInOne 参数，内部调用 splitSourceRule(ruleStr, allInOne)
    private fun splitSourceRuleCacheString(ruleStr: String?, allInOne: Boolean = false): List<SourceRule> {
        if (ruleStr.isNullOrEmpty()) return emptyList()
        // ⚠️ allInOne 影响拆分结果，缓存 key 需区分 allInOne 语义
        // 用 "allInOne=$allInOne|$ruleStr" 作为 key，避免不同 allInOne 命中同一缓存
        val cacheKey = "allInOne=$allInOne|$ruleStr"
        return stringRuleCache.get(cacheKey) ?: splitSourceRule(ruleStr, allInOne).also {
            stringRuleCache.put(cacheKey, it)
        }
    }

    // 修改：getElement 行 382 区域
    // 原：val ruleList = splitSourceRule(ruleStr, true)
    // 改：走缓存版本，保持 allInOne=true 语义
    fun getElement(ruleStr: String): Any? {
        // ...
        val ruleList = splitSourceRuleCacheString(ruleStr, true)
        // ... 后续逻辑保持不变
    }

    // 修改：getElements 行 417 区域
    // 原：val ruleList = splitSourceRule(ruleStr, true)
    // 改：走缓存版本，保持 allInOne=true 语义
    fun getElements(ruleStr: String): List<Any> {
        // ...
        val ruleList = splitSourceRuleCacheString(ruleStr, true)
        // ... 后续逻辑保持不变
    }
}
```

**关键点**：
- `splitSourceRuleCacheString` 签名需扩展 `allInOne` 参数（阻塞修复），否则 getElement/getElements 调用会丢失 allInOne=true 语义
- 缓存 key 必须区分 `allInOne` 语义（用 `"allInOne=$allInOne|$ruleStr"` 复合 key），否则不同 allInOne 调用会命中错误缓存
- `splitSourceRule` 在行 545-588（非原描述的 559-580），`splitSourceRuleCacheString` 在行 534-540
- `stringRuleCache` 是 per-instance，每个 AnalyzeRule 实例独立缓存（与第二批 2.2 不冲突）

**⚠️ isRegex 路径风险说明**（降为可选的主要原因）：
- `splitSourceRule` 内部对 `isRegex` 类型规则有特殊处理路径（行 545-588 中的正则规则分支）
- 签名扩展 allInOne 后，缓存 key 用 `"allInOne=$allInOne|$ruleStr"` 复合形式，**理论上**能区分语义
- 但 `isRegex` 路径的拆分结果可能依赖运行时上下文（如 `source` 实例状态），缓存命中可能导致 isRegex 规则被错误复用
- **需单独评估**：实施前必须验证 isRegex 路径在 allInOne=true 和 allInOne=false 下的拆分结果是否完全确定（不依赖运行时状态）
- 验证方法：构造 isRegex 规则测试用例，分别在 allInOne=true/false 下调用 splitSourceRuleCacheString，确认结果一致性

**风险评估**：
- ⚠️ **isRegex 缓存 key 误命中**：若 isRegex 路径拆分结果依赖运行时上下文，缓存可能导致错误复用
- ⚠️ **allInOne 语义隔离**：复合 key 必须严格区分，否则 allInOne=true 调用会命中 allInOne=false 的缓存
- ✅ 签名扩展向后兼容（allInOne 默认 false 不影响其他调用点）

**日志要求**：
- 缓存命中时可选记录（避免高频）
- isRegex 路径缓存命中时强制记录（便于排查误命中问题）
