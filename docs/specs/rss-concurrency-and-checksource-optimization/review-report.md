# OpenSpec 设计文档审查报告

> 审查对象：`docs/specs/rss-concurrency-and-checksource-optimization/` 四文件
> 审查日期：2026-07-15
> 审查方法：设计文档 vs 真实源码穿透核验（30+ 源码文件/函数/字段逐一验证）

---

## 一、逐条整改明细（按 阻断 > 需调整 > 通过 排序）

### 【阻断级 BLK-1】parseSortUrl() 方法不存在，分类校验维度无法实现

- **缺陷定位**：design.md L171 `val sortList = source.parseSortUrl()  // 需确认方法`
- **问题本质**：RssSource 类中**不存在** `parseSortUrl()` 方法。Grep 全项目搜索 `fun parseSortUrl|parseSortUrl` 零匹配。sortUrl 解析逻辑分散在 [RssViewModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssViewModel.kt) L48-80 的 `getSingleUrl()` 中，仅做简单 `split("::")[1]`，不支持 `&&&` 多分类分隔，也不返回分类列表。
- **落地风险**：编译失败（方法不存在）；即使注释掉也导致分类校验维度形同虚设。
- **整改替换文本**（新增 RssSource 扩展函数或成员方法）：

```kotlin
// 在 RssSource.kt 中新增方法（参考 RssViewModel.getSingleUrl 的解析逻辑，扩展为返回分类列表）
data class RssSort(val name: String, val url: String)

fun getSortList(): List<RssSort> {
    if (sortUrl.isNullOrBlank()) return emptyList()
    val rawSortUrl = sortUrl!!
    // 1. 处理 JS 标签（<js></js> 或 @js:）
    val resolvedUrl = when {
        rawSortUrl.startsWith("<js>", false) || rawSortUrl.startsWith("@js:", false) -> {
            val jsStr = if (rawSortUrl.startsWith("@")) {
                rawSortUrl.substring(4)
            } else {
                rawSortUrl.substring(4, rawSortUrl.lastIndexOf("<"))
            }
            runScriptWithContext { evalJS(jsStr)?.toString() } ?: rawSortUrl
        }
        else -> rawSortUrl
    }
    // 2. 按 &&& 分隔多个分类项
    return resolvedUrl.split("&&&").mapNotNull { item ->
        val parts = item.split("::", limit = 2)
        if (parts.size == 2) RssSort(parts[0].trim(), parts[1].trim())
        else if (parts[0].isNotBlank()) RssSort(parts[0].trim(), parts[0].trim())
        else null
    }
}
```

design.md L169-181 维度4分类校验替换为：
```kotlin
// 维度4: 分类
if (CheckRssSource.checkSort && !source.sortUrl.isNullOrBlank()) {
    try {
        val sortList = source.getSortList()
        if (sortList.isNotEmpty()) {
            source.removeGroup("分类失效")
            successCount++
        } else {
            source.addGroup("分类失效")
        }
    } catch (e: Exception) {
        source.addGroup("分类失效")
    }
}
```

- **整改依据**：[RssViewModel.kt:L48-80](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssViewModel.kt#L48-80) 现有 sortUrl 解析逻辑；[RssSource.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt) 无此方法

---

### 【阻断级 BLK-2】RssSource 缺少 removeInvalidGroups()/removeErrorComment() 方法

- **缺陷定位**：design.md L112 `source.removeInvalidGroups()`
- **问题本质**：`removeInvalidGroups()` 和 `removeErrorComment()` 仅存在于 [BookSource.kt:L195-199](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BookSource.kt#L195-199)，**RssSource 类和 BaseSource 接口中均不存在**。设计文档在 CheckRssSourceService 中对 RssSource 调用此方法会导致编译失败。
- **落地风险**：编译失败；RssSource 校验前无法清理旧的失效标记。
- **整改替换文本**（在 RssSource.kt 中新增）：

```kotlin
// RssSource.kt 新增（参考 BookSource.kt L195-199 的实现）
fun removeInvalidGroups(): RssSource {
    sourceGroup?.let {
        val validGroups = splitNotBlank(AppPattern.splitGroupRegex)
            .filter { group -> group !in invalidGroupNames }
        sourceGroup = if (validGroups.isEmpty()) null else TextUtils.join(",", validGroups)
    }
    return this
}

private val invalidGroupNames = setOf("域名失效", "列表失效", "搜索失效", "分类失效", "正文失效", "重复源")

fun removeErrorComment(): RssSource {
    // RssSource 无 errorComment 字段，此方法可为空实现或移除
    return this
}
```

design.md L112 替换为：`source.removeInvalidGroups()`（确保方法已新增）或移除 `removeErrorComment()` 调用（RssSource 无此字段）。

- **整改依据**：[BookSource.kt:L195](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BookSource.kt#L195) removeInvalidGroups 仅在 BookSource；[BaseSource.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BaseSource.kt) 接口无此方法

---

### 【阻断级 BLK-3】Glide 版本错误（设计文档写 4.15.1，实际 5.0.5）

- **缺陷定位**：design.md L46 `Glide 4.15.1 API`；spec.md 无版本声明
- **问题本质**：[libs.versions.toml:L18](file:///f:/myself/github/WeAgentChat/temp/legado/gradle/libs.versions.toml) `glide = "5.0.5"`。Glide 5.x 相比 4.x 有重大架构变更（模块系统、KSP 支持等）。设计文档基于错误版本编写 API 验证结论，`GlideExecutor.newSourceExecutor(threadCount: Int)` 和 `GlideBuilder.setSourceExecutor()` 在 5.x 中的可用性和签名未经验证。Grep 全项目搜索 `GlideExecutor` 零匹配——项目从未使用过此 API。
- **落地风险**：API 可能不存在或签名变更；编译失败风险高；Glide 5.x 的 `AppGlideModule` 使用方式可能已变。
- **整改替换文本**：

design.md L43-54 替换为：
```markdown
#### 1.1.4 GlideExecutor API 验证（Glide 5.0.5）

**当前项目 Glide 版本**：5.0.5（gradle/libs.versions.toml L18）

Glide 5.x 中 `com.bumptech.glide.load.engine.executor.GlideExecutor` 类仍存在（javadoc 确认）。
但 API 签名需实际编译验证，设计阶段无法 100% 确认以下调用可用：

```kotlin
// 待验证 API（Glide 5.0.5）
GlideExecutor.newSourceExecutor(threadCount: Int): ExecutorService
GlideBuilder.setSourceExecutor(executor: ExecutorService): GlideBuilder
```

**降级方案**：如果 GlideExecutor API 在 5.x 不可用或签名变更，改用标准 Java 线程池：
```kotlin
// 降级方案：直接使用 ExecutorService
override fun applyOptions(context: Context, builder: GlideBuilder) {
    // 现有代码...
    val executor = java.util.concurrent.Executors.newFixedThreadPool(AppConfig.imageLoadConcurrency)
    // 注意：GlideBuilder.setSourceExecutor 可能只接受 GlideExecutor 类型
    // 如不可用，则放弃图片并发配置化，仅保留解析并发配置化（需求一降级）
}
```

**实施前必须**：先写最小验证代码编译测试 GlideExecutor API 在 5.0.5 的可用性。
```

tasks.md 3.2 替换为：
```markdown
- [ ] 3.2 【阻断验证】编译测试 GlideExecutor.newSourceExecutor(threadCount: Int) 在 Glide 5.0.5 可用性
  - 验证通过：按设计实施 setSourceExecutor
  - 验证失败：需求一降级，仅保留解析并发配置化，移除图片加载并发配置（F1.4/F1.5）
```

- **整改依据**：[libs.versions.toml:L18](file:///f:/myself/github/WeAgentChat/temp/legado/gradle/libs.versions.toml) glide=5.0.5；Grep `GlideExecutor` 全项目零匹配

---

### 【需调整 ADJ-1】RssSource.equal() 方法未同步新增字段

- **缺陷定位**：[RssSource.kt:L137-175](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt#L137-175) equal() 方法
- **问题本质**：新增 `parseConcurrency` 字段后，`equal()` 方法未加入比较。RssSourceEditActivity 保存时会用 equal() 判断是否有变更，未包含 parseConcurrency 会导致编辑该字段后"无变更"不保存。tasks.md 2.4 标注"可选低优先级"是错误的——必须修改。
- **整改替换文本**：

RssSource.kt equal() 方法 L174 前新增：
```kotlin
                && equal(searchUrl, source.searchUrl)
                && parseConcurrency == source.parseConcurrency  // 新增
```

tasks.md 2.4 替换为：
```markdown
- [ ] 2.4 RssSourceEditActivity 编辑界面新增 parseConcurrency 配置项（**必须**，非可选）
      同时更新 RssSource.equal() 方法加入 parseConcurrency 比较
```

- **整改依据**：[RssSource.kt:L137-175](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt#L137-175) equal() 逐字段比较

---

### 【需调整 ADJ-2】数据库迁移写法不明确，缺少三处必改点

- **缺陷定位**：spec.md R1.3 `版本94→95，ALTER TABLE`；tasks.md 2.2
- **问题本质**：设计文档只写了 SQL 语句，未明确三处必改：① AppDatabase.kt version 94→95；② DatabaseMigrations.kt 新增 migration_94_95；③ DatabaseMigrations.kt migrations 数组追加。项目从 89→90 起全部使用手动 Migration（非 AutoMigration）。
- **整改替换文本**：

tasks.md 2.2 替换为：
```markdown
- [ ] 2.2 数据库迁移 94→95（三处必改）：
  - (a) AppDatabase.kt L77: `version = 94` → `version = 95`
  - (b) DatabaseMigrations.kt 新增:
    ```kotlin
    private val migration_94_95 = object : Migration(94, 95) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL("ALTER TABLE rssSources ADD COLUMN parseConcurrency INTEGER NOT NULL DEFAULT 0")
        }
    }
    ```
  - (c) DatabaseMigrations.kt migrations 数组追加 `migration_94_95`
  - (d) AppDatabase.kt autoMigrations 注释区新增: `// rss-concurrency: 94→95 使用手动 Migration，新增 parseConcurrency 字段`
```

- **整改依据**：[AppDatabase.kt:L77](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt#L77) version=94；[DatabaseMigrations.kt:L24-25](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/DatabaseMigrations.kt#L24) migrations 数组

---

### 【需调整 ADJ-3】domainCheckMode 配置文档内部不一致

- **缺陷定位**：tasks.md 6.1 `domainCheckMode 配置（0=Socket, 1=AnalyzeUrl, 默认1）`；spec.md/design.md 无此配置
- **问题本质**：tasks.md 提出了 domainCheckMode 配置项，但 spec.md R2.1 和 design.md 1.2.1 只说"改为 AnalyzeUrl"，未定义 domainCheckMode 字段。文档内部不一致，执行者无法判断是否需要保留 Socket 方式。
- **整改替换文本**：

spec.md R2.1 末尾补充：
```markdown
**配置项**：CheckSource 新增 `domainCheckMode`（Int，0=Socket快速检测, 1=AnalyzeUrl真实请求, 默认1）：
```kotlin
// CheckSource.kt 新增
var domainCheckMode = CacheManager.getInt("domainCheckMode") ?: 1
```
CheckSourceConfig UI 新增域名校验方式选择（Socket/AnalyzeUrl）。
```

design.md 1.2.1 补充 domainCheckMode 分支逻辑说明。

- **整改依据**：[CheckSource.kt:L19](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/CheckSource.kt#L19) checkDomain 默认 false；tasks.md 6.1 与 spec/design 不一致

---

### 【需调整 ADJ-4】去重逻辑并发安全风险

- **缺陷定位**：design.md L247-269 dedupSources 方法
- **问题本质**：`dedupSources` 在 `onEachParallel` 并行校验完成后执行，但内部用 `runBlocking(IO) { appDb.rssSourceDao.update(result.source) }` 更新数据库。`result.source` 在并行校验阶段被 `addGroup`/`removeGroup` 修改 sourceGroup 字段——这些修改发生在不同协程中，sourceGroup 是 String? 非 volatile，存在可见性问题。此外 `runBlocking` 在协程中是反模式。
- **整改替换文本**：

design.md L262-265 替换为：
```kotlin
                sorted.drop(1).forEach { result ->
                    result.source.addGroup("重复源")
                }
// 去重标记完成后，统一在协程中批量更新数据库（不用 runBlocking）
val toUpdate = sorted.drop(1).map { it.source }
appDb.rssSourceDao.update(*toUpdate.toTypedArray())
```

并在 doCheckRssSource 说明中补充：sourceGroup 修改必须在单一线程内完成或使用 Mutex 保护。建议去重阶段串行执行（非并行），因为去重是分组操作不需要并行。

- **整改依据**：[FlowExtensions.kt:L27](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/FlowExtensions.kt#L27) onEachParallel 并行执行；RssSource.sourceGroup 非 volatile

---

### 【需调整 ADJ-5】CheckSource.checkDomain 默认值问题

- **缺陷定位**：[CheckSource.kt:L19](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/CheckSource.kt#L19)
- **问题本质**：当前 `checkDomain` 默认 `false`（L19 `?: false`）。设计文档 R2.1 说"域名校验改为 AnalyzeUrl"，但未说明是否将 checkDomain 默认改为 true。如果保持 false，则域名校验默认不执行，改进无意义。
- **整改替换文本**：

spec.md R2.1 补充：
```markdown
**默认值变更**：CheckSource.checkDomain 默认值从 `false` 改为 `true`（域名校验默认启用）。
对应 CheckSource.kt L19: `?: false` → `?: true`
```

- **整改依据**：[CheckSource.kt:L19](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/CheckSource.kt#L19)

---

### 【需调整 ADJ-6】searchUrl 校验方式语义不匹配

- **缺陷定位**：design.md L151-166 维度3搜索校验
- **问题本质**：设计文档用 `Rss.getArticlesAwait("测试", source.searchUrl!!, source, 1, key = "测试")` 校验搜索。但 `getArticlesAwait` 的第二个参数是 `sortUrl`（分类URL），传入 `searchUrl` 格式可能不匹配——searchUrl 通常含 `searchKey` 占位符，AnalyzeUrl 构造时需要 key 参数填充。Rss.kt L47-55 显示 getArticlesAwait 内部会构造 `AnalyzeUrl(sortUrl, page=page, key=key, ...)`，key 参数会替换占位符。但 sortName 参数传 "测试" 语义不对（sortName 是分类显示名）。
- **整改替换文本**：

design.md L151-166 维度3替换为：
```kotlin
    // 维度3: 搜索
    if (CheckRssSource.checkSearch && !source.searchUrl.isNullOrBlank()) {
        try {
            // searchUrl 含搜索关键词占位符，通过 key 参数填充
            val (searchResults, _) = Rss.getArticlesAwait(
                sortName = "",  // 搜索无分类名，传空
                sortUrl = source.searchUrl!!,
                rssSource = source,
                page = 1,
                key = "测试"  // 搜索关键词，替换 searchUrl 中的占位符
            )
            if (searchResults.isNotEmpty()) {
                source.removeGroup("搜索失效")
                successCount++
            } else {
                source.addGroup("搜索失效")
            }
        } catch (e: Exception) {
            source.addGroup("搜索失效")
        }
    }
```

- **整改依据**：[Rss.kt:L39-56](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt#L39-56) getArticlesAwait 签名与 AnalyzeUrl 构造

---

### 【需调整 ADJ-7】CheckRssSourceService 缺少通知栏进度设计

- **缺陷定位**：spec.md R2.3 / design.md 1.2.2
- **问题本质**：CheckSourceService 有完整的通知栏进度显示（notificationMsg、前台Service）。设计文档说"参考 CheckSourceService"但未明确 CheckRssSourceService 是否需要通知栏进度。长时间校验（5维度 × N个源）如果没有前台Service+通知，Android 后台可能杀进程。
- **整改替换文本**：

spec.md R2.3 补充：
```markdown
**通知栏进度**：CheckRssSourceService 必须实现前台 Service + 通知栏进度（参考 CheckSourceService）：
- 启动时 startForeground 显示"正在校验订阅源"
- 每完成一个源更新通知进度（current/total）
- 完成后通知"校验完成，成功X个，失败Y个，重复Z个"
```

- **整改依据**：[CheckSourceService.kt:L58-63](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/service/CheckSourceService.kt#L58-63) 前台Service+通知

---

### 【需调整 ADJ-8】CheckResult 数据结构未说明持久化策略

- **缺陷定位**：design.md L199-203 CheckResult 数据类
- **问题本质**：CheckResult 是运行时数据类，但设计文档未说明是否需要持久化。如果校验过程中App崩溃，校验结果丢失。CheckSourceService 的校验结果通过 source.addGroup/removeGroup 持久化到 RssSource 数据库。CheckResult 仅用于去重的中间态。
- **整改替换文本**：

design.md L199-203 补充：
```markdown
**持久化策略**：CheckResult 为运行时中间态数据，不单独持久化。
校验结果通过 source.addGroup/removeGroup（"域名失效"/"列表失效"等）写入 RssSource.sourceGroup 持久化。
去重标记通过 addGroup("重复源") 持久化。
CheckResult 列表仅在内存中传递给 dedupSources，校验完成后释放。
```

- **整改依据**：[CheckSource.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/CheckSource.kt) 书源校验结果通过 sourceGroup 持久化

---

### 【需调整 ADJ-9】正文校验维度实现为空，缺少完整逻辑

- **缺陷定位**：design.md L183-187 维度5正文校验
- **问题本质**：设计文档只写了注释 `// 需要先获取一篇文章，再解析正文` 和 `// 正文校验依赖列表校验成功`，没有实现。这是5维度之一，不能留空。
- **整改替换文本**：

design.md L183-190 替换为：
```kotlin
    // 维度5: 正文（依赖列表校验成功，需先获取一篇文章）
    if (CheckRssSource.checkContent && !source.ruleContent.isNullOrBlank()) {
        try {
            // 复用维度2的列表结果（如果列表校验成功）
            val (articles, _) = Rss.getArticlesAwait(
                "", source.sortUrl ?: source.sourceUrl, source, 1
            )
            if (articles.isNotEmpty()) {
                val firstArticle = articles.first()
                val articleUrl = firstArticle.link ?: firstArticle.origin
                val analyzeUrl = AnalyzeUrl(
                    articleUrl, source = source, ruleData = RuleData(),
                    coroutineContext = currentCoroutineContext()
                )
                val response = analyzeUrl.getStrResponseAwait()
                val analyzeRule = AnalyzeRule(response.body, source)
                analyzeRule.setBaseUrl(articleUrl)
                val content = analyzeRule.getString(source.ruleContent!!)
                if (!content.isNullOrBlank()) {
                    source.removeGroup("正文失效")
                    successCount++
                } else {
                    source.addGroup("正文失效")
                }
            } else {
                source.addGroup("正文失效")  // 列表为空无法校验正文
            }
        } catch (e: Exception) {
            source.addGroup("正文失效")
        }
    }
```

- **整改依据**：[RssSource.kt:L72](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt#L72) ruleContent 字段

---

## 二、代码一致性评审详情

| # | 偏差位置 | 文档表述 | 代码实际 | 影响 | 修正条目 |
|---|---------|---------|---------|------|---------|
| 1 | design.md L171 parseSortUrl | `source.parseSortUrl()` | 方法不存在 | 阻断 | BLK-1 |
| 2 | design.md L112 removeInvalidGroups | `source.removeInvalidGroups()` | RssSource 无此方法 | 阻断 | BLK-2 |
| 3 | design.md L46 Glide版本 | "4.15.1" | 5.0.5 | 阻断 | BLK-3 |
| 4 | RssSource.kt equal() | 未提及更新 | 逐字段比较，缺新字段 | 高 | ADJ-1 |
| 5 | tasks.md 2.2 迁移 | "ALTER TABLE" | 需改3处文件 | 高 | ADJ-2 |
| 6 | tasks.md 6.1 vs spec.md | domainCheckMode | spec未定义 | 中 | ADJ-3 |
| 7 | design.md L262 dedupSources | runBlocking更新DB | 并发不安全 | 高 | ADJ-4 |
| 8 | CheckSource.kt L19 | checkDomain默认false | 设计未说明改默认值 | 中 | ADJ-5 |
| 9 | design.md L151 搜索校验 | sortName传"测试" | 语义不匹配 | 中 | ADJ-6 |
| 10 | spec.md R2.3 Service | 未提通知栏 | CheckSource有通知 | 中 | ADJ-7 |
| 11 | design.md L199 CheckResult | 未说明持久化 | 仅运行时 | 低 | ADJ-8 |
| 12 | design.md L183 正文校验 | 空实现 | 需完整逻辑 | 高 | ADJ-9 |
| 13 | AppConfig.kt 属性写法 | getter/setter型 | 有先例(L183等) | 通过 | - |
| 14 | AnalyzeUrl.url | 公开url属性 | L102 var url (private set) | 通过 | - |
| 15 | Rss.getArticlesAwait | 签名匹配 | L39 确认 | 通过 | - |

---

## 三、技术成熟度与落地风险评估

### 核心技术链路可行性结论

| 链路 | 可行性 | 风险 |
|------|--------|------|
| 需求一-解析并发配置化 | 可行 | 低（AppConfig/PreferKey/RssParserByRule 模式均已验证） |
| 需求一-图片加载并发配置化 | **待验证** | 高（Glide 5.0.5 GlideExecutor API 未验证，需编译测试） |
| 需求二-书源域名校验优化 | 可行 | 中（AnalyzeUrl 构造正确，但性能比Socket慢需超时控制） |
| 需求二-订阅源校验5维度 | **需补全** | 高（分类维度方法缺失+正文维度空实现） |
| 需求二-多维度去重 | 可行（需修复并发） | 中（realDomain复用AnalyzeUrl.url可行，但去重并发需串行化） |

### 关键依赖清单及可用状态

| 依赖 | 版本 | 状态 | 说明 |
|------|------|------|------|
| AnalyzeUrl.url | - | 可用 | L102 private set，可读 |
| AnalyzeUrl.getStrResponseAwait | - | 可用 | L421 |
| Rss.getArticlesAwait | - | 可用 | L39 |
| RuleData() | - | 可用 | RuleData.kt L5 |
| onEachParallel | - | 可用 | FlowExtensions.kt L27 |
| GlideExecutor | 5.0.5 | **待验证** | 项目从未使用，API签名未确认 |
| RssSource.getSortList() | - | **需新增** | parseSortUrl 不存在 |
| RssSource.removeInvalidGroups() | - | **需新增** | 仅 BookSource 有 |

### 过度设计/设计不足识别

- **设计不足**：正文校验维度空实现（ADJ-9）；sortUrl解析方法缺失（BLK-1）；通知栏进度缺失（ADJ-7）
- **过度设计**：无显著过度设计

---

## 四、多维度评审汇总表

| 维度 | 合规项 | 问题项 | 判定依据 |
|------|--------|--------|---------|
| 1.代码一致性 | 13项通过 | 3阻断+6需调整 | parseSortUrl/removeInvalidGroups/Glide版本 |
| 2.技术成熟度 | 解析并发链路成熟 | 图片并发待验证 | Glide 5.0.5 API未验证(BLK-3) |
| 3.落地可执行性 | AppConfig/UI模式清晰 | 正文校验空实现+迁移不明确 | ADJ-2/ADJ-9 |
| 4.OpenSpec规范 | 四文件结构完整 | tasks与spec不一致 | domainCheckMode(ADJ-3) |
| 5.全需求覆盖 | 需求覆盖完整 | 正文维度未实现 | ADJ-9 |
| 6.完备性与严谨性 | 去重算法设计合理 | 并发安全+通知缺失 | ADJ-4/ADJ-7 |

---

## 五、问题优先级整改清单

| 优先级 | 编号 | 位置 | 问题 | 整改 |
|--------|------|------|------|------|
| 阻断 | BLK-1 | design.md L171 | parseSortUrl不存在 | BLK-1 |
| 阻断 | BLK-2 | design.md L112 | removeInvalidGroups不存在 | BLK-2 |
| 阻断 | BLK-3 | design.md L46 | Glide版本错误4.15.1→5.0.5 | BLK-3 |
| 高 | ADJ-1 | RssSource.kt L137 | equal()未含新字段 | ADJ-1 |
| 高 | ADJ-2 | tasks.md 2.2 | 迁移三处必改未明确 | ADJ-2 |
| 高 | ADJ-4 | design.md L262 | 去重并发不安全 | ADJ-4 |
| 高 | ADJ-9 | design.md L183 | 正文校验空实现 | ADJ-9 |
| 中 | ADJ-3 | tasks.md 6.1 | domainCheckMode不一致 | ADJ-3 |
| 中 | ADJ-5 | CheckSource L19 | checkDomain默认值 | ADJ-5 |
| 中 | ADJ-6 | design.md L151 | 搜索校验语义 | ADJ-6 |
| 中 | ADJ-7 | spec.md R2.3 | 通知栏进度缺失 | ADJ-7 |
| 低 | ADJ-8 | design.md L199 | CheckResult持久化 | ADJ-8 |

---

## 六、需求遗漏专项说明

| 遗漏项 | 影响范围 | 补充内容 |
|--------|---------|---------|
| RssSource.equal() 更新 | 源编辑保存失效 | ADJ-1 |
| 正文校验完整实现 | 5维度变4维度 | ADJ-9 |
| sortUrl分类解析方法 | 分类维度无法实现 | BLK-1 |
| 通知栏进度设计 | 后台校验被杀进程 | ADJ-7 |
| Glide API编译验证 | 图片并发可能不可用 | BLK-3 |
| RssSourceEditActivity UI | 每源并发配置无法编辑 | ADJ-1(tasks 2.4) |

---

## 七、整体评审结论与量化评分

### 判定结果：整改后落地

存在 3 个阻断级问题（方法不存在×2 + 版本错误×1）和 6 个需调整问题。完成上述全部整改后方可实施。

### 量化评分（0-100）

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码匹配度 | 72 | 3处方法/版本与源码不符，其余15项匹配 |
| 技术成熟度 | 68 | Glide API待验证，正文校验空实现 |
| 落地清晰度 | 75 | 大部分链路清晰，迁移/通知/并发需补全 |

---

## 八、整改后落地可行性最终确认

完成 BLK-1~3 + ADJ-1~9 全部整改后，该文档**可支撑落地**，但有一项前置验证必须先执行：

**前置验证（BLK-3）**：编译测试 `GlideExecutor.newSourceExecutor(threadCount: Int)` 在 Glide 5.0.5 的可用性。
- 验证通过：需求一完整实施（解析并发+图片并发）。
- 验证失败：需求一降级为仅解析并发配置化，移除 F1.4/F1.5 图片加载并发。

其余整改项均为确定性的代码补充，无未知技术风险。执行人员凭整改后的文档即可完成全部工作，无需额外设计。
