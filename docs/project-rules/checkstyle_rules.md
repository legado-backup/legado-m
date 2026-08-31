# 代码风格规范

> 基于 Legado 项目源码深度分析提取的项目特有代码风格，AI Agent 必须遵循。

---

## 协程模式 — 自定义 Coroutine 链式封装

项目**不使用**标准 `viewModelScope.launch + try/catch` 模式，而是自建链式协程封装 `io.legado.app.help.coroutine.Coroutine`：

### 双版本模式（强制）

每个异步操作必须提供两个版本：

```kotlin
// 版本1：返回 Coroutine<T>，使用链式回调
fun searchBook(scope: CoroutineScope, ...): Coroutine<ArrayList<SearchBook>> {
    return Coroutine.async(scope, context, start = start, executeContext = executeContext) {
        searchBookAwait(bookSource, key, page)
    }
}

// 版本2：suspend 函数，返回 T
suspend fun searchBookAwait(...): ArrayList<SearchBook> { ... }
```

### 链式回调用法

```kotlin
Coroutine.async {
    AppWebDav.getBookProgress(book)
}.onError {
    AppLog.put("拉取阅读进度失败", it)
}.onSuccess { progress ->
    // 处理逻辑
}
```

## 错误处理 — kotlin.runCatching

项目偏好使用 `kotlin.runCatching`（带 `kotlin.` 前缀）：

```kotlin
val res = kotlin.runCatching {
    analyzeUrl.getStrResponseAwait().let { ... }
}.getOrElse { throwable ->
    // 错误处理
}
```

**不要**省略 `kotlin.` 前缀，这是项目约定。

## 空安全模式

| 模式 | 用法 | 示例 |
|------|------|------|
| `isNullOrBlank()` | 字符串判空（非 isNullOrEmpty） | `if (searchUrl.isNullOrBlank())` |
| `let + return` | 空安全链式调用 | `ruleSearch?.let { return it }` |
| `Elvis + return` | 早返回 | `val book = book ?: return` |
| `!!` 非空断言 | 确定逻辑非空时 | `val book = book!!` |

## object 单例 — 核心架构模式

核心业务层几乎全部使用 `object` 声明：

```kotlin
object WebBook { ... }          // 网络书核心
object ReadBook : CoroutineScope by MainScope() { ... }  // 阅读核心
object AppConfig { ... }        // 全局配置
object AppConst { ... }         // 全局常量
```

**注意**：`object` 单例持有可变状态时，必须使用 `@Synchronized` 或 `Mutex` 保护并发访问。

## 数据实体 — data class + @Parcelize + @Entity

所有 Room 实体必须：
- 使用 `data class`
- 添加 `@Parcelize` 实现 Parcelable
- 添加 `@Entity` 注解
- **字段全部有默认值**

### 入缓存对象必须不可变或快照化（强制，2026-09-01 C0-F1 沉淀）

凡进入缓存（LruCache/ConcurrentHashMap 内存缓存等）的对象，要么自身不可变（`val` 字段），要么缓存"解析产物快照"而非可变定义对象——禁止缓存命中后原地改写字段（跨请求/重入/并发下产生半更新污染，铁证：AnalyzeRule SourceRule 可变字段缓存污染，legadoC ResolvedSourceRule 快照化为根因修复方案）。

```kotlin
// 反例：缓存对象可变 + 消费时原地改写 → 二次命中读到污染值
inner class SourceRule { internal var rule: String; internal var replaceRegex = ""
    fun makeUpRule(result: Any?) { rule = ...; replaceRegex = ... } }  // ❌ 原地写
// 正例：解析产物与定义分离，makeUpRule 返回不可变快照，缓存对象只读
internal data class ResolvedSourceRule(val rule: String, val replaceRegex: String = "", ...)
internal fun makeUpRule(result: Any?): ResolvedSourceRule { ... return ResolvedSourceRule(...) }  // ✅
```

```kotlin
@Parcelize
@TypeConverters(BookSource.Converters::class)
@Entity(tableName = "book_sources")
data class BookSource(
    @PrimaryKey var bookSourceUrl: String = "",
    var bookSourceName: String = "",
    // ...
) : Parcelable, BaseSource
```

## @IntDef 替代 enum

使用 `@IntDef` + 位运算而非 enum class（Android 性能优化）：

```kotlin
object BookType {
    const val video = 0b100
    const val text = 0b1000
    @Target(AnnotationTarget.VALUE_PARAMETER)
    @Retention(AnnotationRetention.SOURCE)
    @IntDef(flag = true, value = [video, text, audio, ...])
    annotation class Type
}
```

## 顶层属性 + by lazy

工具类使用顶层 `val` + `by lazy` 延迟初始化：

```kotlin
val cookieJar by lazy { object : CookieJar { ... } }
val okHttpClient: OkHttpClient by lazy { ... }
```

## synchronized 与 Mutex 并用

- 传统 `@Synchronized`：用于 Java 互操作和简单同步
- 协程 `Mutex`：用于协程内的互斥访问

```kotlin
@Synchronized
private fun addLoading(index: Int): Boolean { ... }

private val curChapterLoadingLock = Mutex()
// 使用时
curChapterLoadingLock.withLock { ... }
```

## Import 规则

- **显式 import**，禁止 star import
- **无自定义 import 别名**
- 扩展函数需从定义文件显式导入

## 注释语言

- 注释使用**中文**
- 公开方法用 KDoc
