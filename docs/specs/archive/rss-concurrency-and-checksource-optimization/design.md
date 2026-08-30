# 技术设计：订阅源解析并发配置化 + 书源/订阅源校验去重优化

## 1. Technical Approach

### 1.1 需求一技术方案

#### 1.1.1 配置链路

```
pref_config_other.xml (UI声明)
  ↓ onPreferenceTreeClick
OtherConfigFragment (NumberPickerDialog)
  ↓ AppConfig.rssParseConcurrency = value
AppConfig (getPrefInt/putPrefInt)
  ↓ SharedPreferences 持久化
PreferKey.rssParseConcurrency (键名)
```

#### 1.1.2 解析并发读取链路

```
RssParserByRule.getArticlesAwait()
  ↓ rssSource.parseConcurrency.takeIf { it > 0 } ?: AppConfig.rssParseConcurrency
  ↓ Semaphore(动态值)
  ↓ async{}.awaitAll() 并行解析
```

#### 1.1.3 图片加载并发链路

```
App启动 → LegadoGlideModule.applyOptions()
  ↓ GlideBuilder.setSourceExecutor(GlideExecutor.newSourceExecutor(imageLoadConcurrency))
  ↓ Glide 初始化 ExecutorService (只执行一次)
  ↓ 后续所有图片加载使用此线程池
```

**阻塞点已确认**：
- AppConfig使用 `getPrefInt`/`putPrefInt` 模式（非 `intValue`）
- OtherConfigFragment使用 `PreferenceFragment` + XML偏好项（非 ViewBinding）
- PreferKey是 `object` 内常量
- GlideModule只在App启动时初始化一次

#### 1.1.4 GlideExecutor API验证（Glide 5.0.5）

**当前项目 Glide 版本**：5.0.5（gradle/libs.versions.toml L18，非 4.15.1）

Glide 5.x 中 `com.bumptech.glide.load.engine.executor.GlideExecutor` 类应仍存在，但 API 签名需实际编译验证（项目从未使用过此 API，Grep 全项目 `GlideExecutor` 零匹配）：

```kotlin
// 待验证 API（Glide 5.0.5）
GlideExecutor.newSourceExecutor(threadCount: Int): ExecutorService
GlideBuilder.setSourceExecutor(executor: ExecutorService): GlideBuilder
```

需在LegadoGlideModule中import:
```kotlin
import com.bumptech.glide.GlideExecutor
```

**降级方案**：如果 GlideExecutor API 在 5.x 不可用或签名变更，需求一降级为仅解析并发配置化，移除 F1.4/F1.5 图片加载并发配置。

**实施前必须**：先写最小验证代码编译测试 GlideExecutor API 在 5.0.5 的可用性（见 tasks.md 3.2）。验证通过则完整实施，验证失败则需求一降级。

### 1.2 需求二技术方案

#### 1.2.1 书源域名校验优化

**当前方案**（CheckSourceService.kt L161-172）：
```kotlin
private suspend fun isDomainReachable(domain: String): Boolean {
    val url = URI(domain.substringBefore("#"))
    val port = url.port.takeIf { it > 0 } ?: 80
    Socket().use { socket ->
        socket.connect(InetSocketAddress(url.host, port), 1600)
        true
    }
}
```
问题：直接从`source.bookSourceUrl`截取域名，不支持jslib/注释/#规避等复杂情况。

**优化方案**：
```kotlin
private suspend fun checkDomainReachable(source: BookSource): Boolean {
    return kotlin.runCatching {
        withTimeout(CheckSource.timeout) {
            val analyzeUrl = AnalyzeUrl(
                source.bookSourceUrl,
                source = source,
                ruleData = RuleData(),
                coroutineContext = currentCoroutineContext()
            )
            analyzeUrl.getStrResponseAwait()
            true
        }
    }.getOrDefault(false)
}
```

#### 1.2.2 订阅源校验Service架构

```
CheckRssSource (object, 配置)
  ↓ start(context, sources)
CheckRssSourceService (Service, 执行)
  ↓ check(ids)
  ↓ onEachParallel(threadCount)
  ↓ checkRssSource(source)
  ↓ withTimeout
  ↓ doCheckRssSource(source)
  ↓ 校验5维度 → 记录成功维度数
  ↓ 去重(如果启用)
  ↓ appDb.rssSourceDao.update(source)
```

#### 1.2.3 订阅源校验维度详细设计

**RssSource.kt 需新增方法**（参考 BookSource.kt L188-193 + L195-197 + L222-226）：

```kotlin
// RssSource.kt 新增（参考 BookSource.kt L188-193）
// 判断是否包含指定分组（weight计算器calculateRssWeightFromGroups依赖此方法）
// BLK-6修复：RssSource原本只有addGroup/removeGroup，缺少hasGroup
fun hasGroup(group: String): Boolean {
    sourceGroup?.splitNotBlank(AppPattern.splitGroupRegex)?.toHashSet()?.let {
        return it.indexOf(group) != -1
    }
    return false
}

// RssSource.kt 新增（参考 BookSource.kt L195-197 + L222-226）
// 移除校验产生的失效分组（含"失效"/"校验超时"/"重复源"）
fun removeInvalidGroups(): RssSource {
    val invalidGroups = sourceGroup?.splitNotBlank(AppPattern.splitGroupRegex)
        ?.filter { "失效" in it || it == "校验超时" || it == "重复源" }
        ?.joinToString() ?: ""
    if (invalidGroups.isNotEmpty()) {
        removeGroup(invalidGroups)
    }
    return this
}

// RssSource.kt 新增（参考 RssViewModel.kt L48-80 getSingleUrl 逻辑，扩展为返回分类列表）
// 需 import com.script.rhino.runScriptWithContext
// BLK-8修复：getSortList标记为suspend（runScriptWithContext是suspend函数，非suspend函数不能调用）
data class RssSort(val name: String, val url: String)

suspend fun getSortList(): List<RssSort> {
    if (sortUrl.isNullOrBlank()) return emptyList()
    var rawSortUrl = sortUrl!!
    // 1. 处理 JS 标签（<js></js> 或 @js:）
    if (rawSortUrl.startsWith("<js>", false) || rawSortUrl.startsWith("@js:", false)) {
        val jsStr = if (rawSortUrl.startsWith("@")) {
            rawSortUrl.substring(4)
        } else {
            rawSortUrl.substring(4, rawSortUrl.lastIndexOf("<"))
        }
        val result = runScriptWithContext { evalJS(jsStr)?.toString() }
        if (!result.isNullOrBlank()) {
            rawSortUrl = result
        }
    }
    // 2. 按 &&& 分隔多个分类项，每项用 :: 分隔名称和URL
    return rawSortUrl.split("&&&").mapNotNull { item ->
        val parts = item.split("::", limit = 2)
        if (parts.size == 2) RssSort(parts[0].trim(), parts[1].trim())
        else if (parts[0].isNotBlank()) RssSort(parts[0].trim(), parts[0].trim())
        else null
    }
}
```

**doCheckRssSource 实现**（返回 CheckResult，记录 realDomain 用于去重复用）：

```kotlin
private suspend fun doCheckRssSource(source: RssSource): CheckResult {
    var successCount = 0
    var realDomain: String? = null
    source.removeInvalidGroups()  // 需在RssSource.kt新增此方法（见上方新增方法说明）

    // 维度1: 域名可达性
    if (CheckRssSource.checkDomain) {
        val analyzeUrl = AnalyzeUrl(
            source.sourceUrl,
            source = source,
            ruleData = RuleData(),
            coroutineContext = currentCoroutineContext()
        )
        try {
            analyzeUrl.getStrResponseAwait()
            // 📌 关键：记录真实域名（复用AnalyzeUrl处理结果，供去重复用）
            realDomain = URI(analyzeUrl.url).host
            source.removeGroup("域名失效")
            successCount++
        } catch (e: Exception) {
            source.addGroup("域名失效")
        }
    }

    // 域名校验关闭或失败时，如启用去重则单独构造AnalyzeUrl提取域名（不发起请求）
    if (realDomain == null && CheckRssSource.enableDedup) {
        realDomain = kotlin.runCatching {
            val analyzeUrl = AnalyzeUrl(source.sourceUrl, source = source, ruleData = RuleData())
            URI(analyzeUrl.url).host
        }.getOrNull()
    }

    // 维度2: 列表解析
    var articles: MutableList<RssArticle>? = null
    if (CheckRssSource.checkArticles && !source.ruleArticles.isNullOrBlank()) {
        try {
            val (result, _) = Rss.getArticlesAwait(
                "", source.sortUrl ?: source.sourceUrl,
                source, 1
            )
            articles = result
            if (result.isNotEmpty()) {
                source.removeGroup("列表失效")
                successCount++
            } else {
                source.addGroup("列表失效")
            }
        } catch (e: Exception) {
            source.addGroup("列表失效")
        }
    }

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

    // 维度4: 分类
    if (CheckRssSource.checkSort && !source.sortUrl.isNullOrBlank()) {
        try {
            val sortList = source.getSortList()  // 需在RssSource.kt新增此方法（见上方新增方法说明）
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

    // 维度5: 正文（依赖列表校验成功，需先获取一篇文章）
    if (CheckRssSource.checkContent && !source.ruleContent.isNullOrBlank()) {
        try {
            // 复用维度2的列表结果（如果列表校验成功）
            val articleList = articles ?: Rss.getArticlesAwait(
                "", source.sortUrl ?: source.sourceUrl, source, 1
            ).first
            if (articleList.isNotEmpty()) {
                val firstArticle = articleList.first()
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

    return CheckResult(source, successCount, realDomain)
}
```

#### 1.2.4 去重算法（复用域名校验结果）

**核心原则**：域名去重依赖于域名校验，使用校验时AnalyzeUrl处理后的真实域名，不单独从sourceUrl截取。

```kotlin
// 校验结果数据结构
// ADJ-8 持久化策略：CheckResult 为运行时中间态数据，不单独持久化。
// 校验结果通过 source.addGroup/removeGroup（"域名失效"/"列表失效"等）写入 RssSource.sourceGroup 持久化。
// 去重标记通过 addGroup("重复源") 持久化。
// CheckResult 列表仅在内存中传递给 dedupSources，校验完成后释放。
data class CheckResult(
    val source: RssSource,
    val successCount: Int,      // 校验成功维度数
    val realDomain: String?     // 从AnalyzeUrl处理后的最终URL提取的host
)

// doCheckRssSource 实现见 1.2.3 节（返回 CheckResult）

// 去重时直接使用 CheckResult.realDomain
// ADJ-4 修复：去重串行执行（分组操作不需要并行），DB更新改为批量（不用 runBlocking）
private suspend fun dedupSources(results: List<CheckResult>) {
    if (!CheckRssSource.enableDedup) return

    // 1. 按真实域名分组（域名来自校验阶段的AnalyzeUrl处理结果）
    val byDomain = results.filter { !it.realDomain.isNullOrBlank() }
        .groupBy { it.realDomain!! }

    // 2. 每个域名内按type二次分组
    val toUpdate = mutableListOf<RssSource>()
    byDomain.forEach { (domain, list) ->
        val byType = list.groupBy { it.source.type }
        byType.forEach { (type, sameTypeList) ->
            if (sameTypeList.size > 1) {
                // 3. 按成功维度数降序排序
                val sorted = sameTypeList.sortedByDescending { it.successCount }
                // 4. 保留第1名，其余标记重复
                sorted.drop(1).forEach { result ->
                    result.source.addGroup("重复源")
                    toUpdate.add(result.source)
                }
            }
        }
    }

    // 5. 去重标记完成后，统一批量更新数据库（不用 runBlocking，直接在协程中执行）
    if (toUpdate.isNotEmpty()) {
        appDb.rssSourceDao.update(*toUpdate.toTypedArray())
    }
}
```

**与旧方案的区别**：
- 旧方案：去重时重新构造AnalyzeUrl（重复计算）
- 新方案：去重复用校验时记录的realDomain（一次性处理）
- 确保域名去重和域名校验使用**完全相同的AnalyzeUrl处理结果**

#### 1.2.5 域名提取的复杂性处理

AnalyzeUrl 处理链路：
```
sourceUrl (可能含jslib/注释/#/空格)
  ↓ AnalyzeUrl 构造函数
  ↓ 解析 <js></js> 标签 → 执行JS获取真实URL
  ↓ 解析注释入参
  ↓ 去除#后缀
  ↓ trim空格
  ↓ 最终URL (analyzeUrl.url)
  ↓ URI(finalUrl).host → 真实域名
```

**关键**：不修改AnalyzeUrl的任何处理逻辑，只调用它获取最终URL。

#### 1.2.6 domainCheckMode UI 详细设计

**源码核实**：CheckSourceConfig 继承 `BaseDialogFragment(R.layout.dialog_check_source_config)`，使用 ViewBinding（`DialogCheckSourceConfigBinding`），布局用 `FlexboxLayout` + `ThemeCheckBox` 横向排列（非 PreferenceFragment）。domainCheckMode 需在此对话框内新增选择控件。

**XML 布局修改**（`dialog_check_source_config.xml`，在 `check_domain` CheckBox 下方新增 RadioGroup）：

```xml
<!-- 在 FlexboxLayout 内 check_domain 之后插入 -->
<RadioGroup
    android:id="@+id/domain_check_mode_group"
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:orientation="horizontal"
    android:visibility="gone">

    <RadioButton
        android:id="@+id/rb_socket"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/domain_check_socket" />

    <RadioButton
        android:id="@+id/rb_analyze_url"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:checked="true"
        android:text="@string/domain_check_analyze_url" />
</RadioGroup>
```

**CheckSourceConfig.kt 交互逻辑**：

```kotlin
// onFragmentCreated 中新增
binding.checkDomain.onClick {
    // 原有逻辑...
    // 新增: RadioGroup 可见性跟随 checkDomain
    binding.domainCheckModeGroup.visibility =
        if (binding.checkDomain.isChecked) View.VISIBLE else View.GONE
}
// 初始化: 读取 CheckSource.domainCheckMode 设置选中项
when (CheckSource.domainCheckMode) {
    0 -> binding.rbSocket.isChecked = true
    else -> binding.rbAnalyzeUrl.isChecked = true
}
binding.domainCheckModeGroup.visibility =
    if (binding.checkDomain.isChecked) View.VISIBLE else View.GONE

// tvOk.onClick 保存时新增
CheckSource.domainCheckMode = when (binding.rbSocket.isChecked) { true -> 0; false -> 1 }
```

**CheckSource.kt 新增字段**：

```kotlin
// CheckSource.kt 新增（参考现有 var 声明模式）
var domainCheckMode = CacheManager.getInt("domainCheckMode") ?: 1  // 0=Socket, 1=AnalyzeUrl(默认)
```

**CheckSourceService.kt doCheckSource 分支逻辑**：

```kotlin
if (CheckSource.checkDomain) {
    val domain = source.bookSourceUrl
    if (!domain.startsWith("http", ignoreCase = true)) {
        throw NoStackTraceException("源地址不是http链接")
    } else {
        val reachable = when (CheckSource.domainCheckMode) {
            0 -> isDomainReachable(domain)        // Socket快速检测(保留原方法)
            else -> checkDomainReachable(source)   // AnalyzeUrl真实请求(新增方法)
        }
        if (reachable) {
            source.removeGroup("域名失效")
        } else {
            source.addGroup("域名失效")
            source.weight = 0
            throw NoStackTraceException("源地址不可访问")
        }
    }
}
```

**strings.xml 新增**：
- `domain_check_socket` = "Socket快速检测"
- `domain_check_analyze_url` = "解析规则真实请求"

### 1.3 需求三技术方案（权重算法回填）

#### 1.3.1 字段现状分析

**BookSource.weight（已有，基本废弃）**:
- `BookSource.kt` L80: `var weight: Int = 0`
- `BookSourceViewModel.kt` L223/L242: `BookSourceSort.Weight -> data.sortedBy { it.weight }`（排序功能已存在）
- 实际weight值一直为0（无自动回填机制，用户也不手动维护），导致排序功能形同虚设
- **无需新增字段**，校验后回填即可激活排序

**RssSource.weight（需新增）**:
- `RssSource.kt` 当前无weight字段
- 数据库迁移新增weight字段
- **合并迁移**：与parseConcurrency合并到同一个migration_94_95（一次迁移两个字段）

#### 1.3.2 权重计算器设计

新增 `SourceWeightCalculator.kt`（object单例，参考AppConfig模式）：

**关键设计决策**: 基于source分组状态计算weight（不新增Boolean变量，最小改动）
- doCheckSource现有代码用addGroup/removeGroup记录维度结果
- weight计算通过hasGroup反推各维度状态
- doCheckSource开头已有source.removeInvalidGroups()(L176)清除旧分组，校验前分组干净

```kotlin
// app/src/main/java/io/legado/app/model/SourceWeightCalculator.kt
object SourceWeightCalculator {
    // 书源维度分值（满分100）
    const val BOOK_DOMAIN_SCORE = 20      // 前置条件
    const val BOOK_SEARCH_SCORE = 20      // 核心搜索
    const val BOOK_DISCOVERY_SCORE = 15   // 辅助发现
    const val BOOK_INFO_SCORE = 15        // 详情页
    const val BOOK_CATEGORY_SCORE = 15    // 目录
    const val BOOK_CONTENT_SCORE = 15     // 正文

    // 订阅源维度分值（满分100）
    const val RSS_DOMAIN_SCORE = 20       // 前置条件
    const val RSS_ARTICLES_SCORE = 25     // 核心列表
    const val RSS_SEARCH_SCORE = 20      // 辅助搜索
    const val RSS_SORT_SCORE = 15        // 辅助分类
    const val RSS_CONTENT_SCORE = 20     // 正文

    /**
     * 基于BookSource分组状态计算权重（满分100）
     * 不需要修改doCheckSource结构，直接通过hasGroup反推各维度状态
     *
     * 分组名对照（来自CheckSourceService.kt源码核实）:
     * - 域名失效 (L189)
     * - 搜索失效 (L200) / 搜索链接规则为空 (L206)
     * - 发现失效 (L220) / 发现规则为空 (L215)
     * - 搜索目录失效 / 发现目录失效 (L269, bookType=搜索/发现)
     * - 搜索正文失效 / 发现正文失效 (L268, bookType=搜索/发现)
     * - 详情维度: checkBook成功完成=通过(失败throw中断不会执行到weight计算)
     *
     * @param source 校验后的BookSource（已包含addGroup/removeGroup状态）
     * @param domainCheckEnabled 是否启用域名校验
     */
    fun calculateBookWeightFromGroups(source: BookSource, domainCheckEnabled: Boolean): Int {
        // 域名前置条件: 校验开启且有"域名失效"分组→0分
        if (domainCheckEnabled && source.hasGroup("域名失效")) return 0

        var weight = 0
        // 域名: 校验关闭或无"域名失效"分组→满分
        if (!domainCheckEnabled || !source.hasGroup("域名失效")) weight += BOOK_DOMAIN_SCORE
        // 搜索: 无"搜索失效"且无"搜索链接规则为空"→满分
        if (!source.hasGroup("搜索失效") && !source.hasGroup("搜索链接规则为空")) weight += BOOK_SEARCH_SCORE
        // 发现: 无"发现失效"且无"发现规则为空"→满分
        if (!source.hasGroup("发现失效") && !source.hasGroup("发现规则为空")) weight += BOOK_DISCOVERY_SCORE
        // 详情: checkBook成功完成(失败throw中断)=通过→满分
        // (只要执行到weight计算，详情就是通过的)
        weight += BOOK_INFO_SCORE
        // 目录: 无"搜索目录失效"且无"发现目录失效"→满分
        if (!source.hasGroup("搜索目录失效") && !source.hasGroup("发现目录失效")) weight += BOOK_CATEGORY_SCORE
        // 正文: 无"搜索正文失效"且无"发现正文失效"→满分
        if (!source.hasGroup("搜索正文失效") && !source.hasGroup("发现正文失效")) weight += BOOK_CONTENT_SCORE
        return weight
    }

    /**
     * 基于RssSource分组状态计算权重（满分100）
     * 订阅源校验doCheckRssSource使用addGroup/removeGroup记录，同样基于分组状态反推
     *
     * 分组名对照（来自design.md 1.2.3节doCheckRssSource实现）:
     * - 域名失效 / 列表失效 / 搜索失效 / 分类失效 / 正文失效
     */
    fun calculateRssWeightFromGroups(source: RssSource, domainCheckEnabled: Boolean): Int {
        if (domainCheckEnabled && source.hasGroup("域名失效")) return 0

        var weight = 0
        if (!domainCheckEnabled || !source.hasGroup("域名失效")) weight += RSS_DOMAIN_SCORE
        if (!source.hasGroup("列表失效")) weight += RSS_ARTICLES_SCORE
        if (!source.hasGroup("搜索失效")) weight += RSS_SEARCH_SCORE
        if (!source.hasGroup("分类失效")) weight += RSS_SORT_SCORE
        if (!source.hasGroup("正文失效")) weight += RSS_CONTENT_SCORE
        return weight
    }
}
```

**校验关闭维度的处理**:
- 如果checkSearch=false，doCheckSource不校验搜索，不会addGroup("搜索失效")，weight计算时!hasGroup("搜索失效")=true→给满分
- 符合"校验关闭=满分(不扣分)"原则
- 各维度校验关闭时，该维度不addGroup，weight计算给满分

#### 1.3.3 回填集成点

**书源回填**（CheckSourceService.kt doCheckSource）:

基于分组状态回填，插入点两处:

1. **域名校验失败时**（L189-190 throw前）: 回填weight=0
```kotlin
// CheckSourceService.kt doCheckSource L186-191 修改
else if (isDomainReachable(domain)) {  // 或 AnalyzeUrl校验
    source.removeGroup("域名失效")
} else {
    source.addGroup("域名失效")
    source.weight = 0  // 📌 新增: 域名失败回填0分
    throw NoStackTraceException("源地址不可访问")
}
```

2. **所有维度校验完成后**（L227 getInvalidGroupNames前）: 基于分组状态计算weight
```kotlin
// CheckSourceService.kt doCheckSource L226-227 新增
// 📌 新增: 基于分组状态计算weight并回填
source.weight = SourceWeightCalculator.calculateBookWeightFromGroups(
    source, CheckSource.checkDomain
)
val finalCheckMessage = source.getInvalidGroupNames()
if (finalCheckMessage.isNotBlank()) {
    throw NoStackTraceException(finalCheckMessage)
}
```

**关键**: 不修改doCheckSource现有校验逻辑（addGroup/removeGroup顺序不变），仅在throw前和末尾新增weight回填，最小改动。

**订阅源回填**（CheckRssSourceService.kt doCheckRssSource末尾）:
- doCheckRssSource已在design.md 1.2.3节实现5维度校验（使用addGroup/removeGroup记录）
- 在return CheckResult前，基于分组状态计算weight

```kotlin
// CheckRssSourceService.kt doCheckRssSource 末尾（在 return CheckResult 前）
// 📌 新增: 基于分组状态计算weight并回填
source.weight = SourceWeightCalculator.calculateRssWeightFromGroups(
    source, CheckRssSource.checkDomain
)
return CheckResult(source, successCount, realDomain)
```

**域名失败时订阅源weight=0**:
- doCheckRssSource维度1域名校验失败时addGroup("域名失效")
- calculateRssWeightFromGroups检测到"域名失效"分组→返回0
- 无需单独在throw前回填（订阅源校验不throw中断，继续其他维度）

#### 1.3.4 数据库迁移（合并parseConcurrency + weight）

```kotlin
// DatabaseMigrations.kt migration_94_95（合并需求一parseConcurrency + 需求三weight）
private val migration_94_95 = object : Migration(94, 95) {
    override fun migrate(db: SupportSQLiteDatabase) {
        // 需求一：解析并发每源配置
        db.execSQL("ALTER TABLE rssSources ADD COLUMN parseConcurrency INTEGER NOT NULL DEFAULT 0")
        // 需求三：权重值回填
        db.execSQL("ALTER TABLE rssSources ADD COLUMN weight INTEGER NOT NULL DEFAULT 0")
    }
}
```

**注意**：BookSource已有weight字段，无需迁移；仅RssSource需新增weight字段。

#### 1.3.5 排序功能激活

- BookSource: `BookSourceSort.Weight` 排序已存在（BookSourceViewModel.kt L223/L242），回填weight后自动生效
- RssSource: 新增weight字段后，可选在RssSourceViewModel排序中新增Weight选项（非必须，用户可通过customOrder排序）

## 2. Architecture Decisions

### AD-01: 双参数分离（需求一）
- **Context**: 解析并发和图片加载并发资源维度不同
- **Concern**: 单参数无法同时满足CPU密集型和IO密集型场景
- **Decision**: 分离为 rssParseConcurrency(默认3) 和 imageLoadConcurrency(默认5)
- **Goal**: 分别优化CPU和IO资源使用
- **Tradeoff**: 两个配置项增加用户理解成本
- **Status**: Proposed

### AD-02: 域名校验走真实请求链路（需求二）
- **Context**: 源URL可能含jslib/注释/#规避等复杂内容
- **Concern**: Socket测试和正则截取都无法处理复杂URL
- **Decision**: 通过AnalyzeUrl发起真实请求校验域名可达性
- **Goal**: 校验准确性，支持源URL复杂性
- **Tradeoff**: 比Socket慢（但更准确）
- **Status**: Proposed

### AD-03: 多维度去重（需求二）
- **Context**: 同域名可能有多种类型源（网页/图片/视频）
- **Concern**: 按域名单维度去重会误删不同类型源
- **Decision**: 第一维度域名+第二维度type去重
- **Goal**: 精准去重，保留每种类型最优源
- **Tradeoff**: 去重逻辑复杂度增加
- **Status**: Proposed

### AD-04: 去重后处理用分组标记（需求二）
- **Context**: 去重后的源不能直接删除（用户可能需要）
- **Concern**: 直接删除不可逆
- **Decision**: addGroup("重复源") 标记，不删除
- **Goal**: 可逆操作，用户可手动恢复
- **Tradeoff**: 需要用户手动清理或筛选
- **Status**: Proposed

### AD-05: 权重算法回填（需求三）
- **Context**: BookSource.weight字段基本废弃（值一直为0），RssSource无weight字段
- **Concern**: 排序功能BookSourceSort.Weight存在但因weight=0形同虚设
- **Decision**: 校验时根据各维度通过情况计算权重值(满分100,域名不可达=0分)，回填source.weight
- **Goal**: 激活排序功能，量化源质量便于用户筛选
- **Tradeoff**: 校验回填会覆盖用户手动设置的weight值（实际都是0，可接受）
- **Status**: Proposed

### AD-06: 权重分值固定分配（需求三）
- **Context**: 各维度重要性不同（核心vs辅助）
- **Concern**: 均分权重无法体现维度重要性差异
- **Decision**: 固定分值分配（书源: 域名20+搜索20+发现15+信息15+目录15+正文15；订阅源: 域名20+列表25+搜索20+分类15+正文20）
- **Goal**: 核心功能权重高，辅助功能权重低
- **Tradeoff**: 不支持用户自定义分值（后续可扩展为配置项）
- **Status**: Proposed

### AD-07: 书源校验复用+优化 vs 订阅源校验新增（需求二）
- **Context**: 用户疑问"一键校验是新增还是复用?原有书源校验是否会被优化?"
- **Concern**: 需要明确书源校验和订阅源校验的复用关系
- **Decision**:
  - **书源校验**: 复用现有CheckSourceService.doCheckSource + 优化(域名校验Socket→AnalyzeUrl + 末尾weight回填)。不新增独立Service，用户执行"书源管理→校验所选"时自动获得优化。
  - **订阅源校验**: 全新新增(CheckRssSource + CheckRssSourceService + CheckRssSourceConfig)，因为订阅源原本无校验功能。
- **Goal**: 书源校验用户无需学习新功能，原有"校验所选"自动获得域名校验优化+权重回填；订阅源校验是全新功能。
- **Tradeoff**: 书源校验修改现有代码需谨慎不破坏现有逻辑(采用最小改动:仅域名校验方式切换+末尾weight回填)
- **Status**: Proposed

### AD-08: 基于分组状态计算weight（需求三）
- **Context**: doCheckSource现有代码用addGroup/removeGroup记录维度结果，无Boolean变量
- **Concern**: 新增Boolean变量需修改doCheckSource结构，改动大风险高
- **Decision**: 基于source分组状态(hasGroup)反推各维度结果计算weight，不修改doCheckSource校验逻辑
- **Goal**: 最小改动，不破坏现有校验流程
- **Tradeoff**: weight计算依赖分组名(字符串硬编码)，分组名变更需同步更新计算器
- **Status**: Proposed

## 3. Data Flow

### 3.1 需求一数据流

```
用户设置 → SharedPreferences → AppConfig属性 → RssParserByRule读取 → Semaphore动态值
                                                        ↓
                                        图片: AppConfig → LegadoGlideModule(启动时) → GlideExecutor
```

### 3.2 需求二数据流

```
用户选择源 → CheckRssSource.start()
  ↓
CheckRssSourceService.check(ids)
  ↓ onEachParallel
  ↓ checkRssSource(source) → doCheckRssSource(source) → 返回 CheckResult(source, successCount, realDomain)
  ↓ 收集所有 CheckResult: List<CheckResult>
  ↓ dedupSources(如果启用)
  ↓ 按realDomain分组 → 按type二次分组 → 排序 → 保留最优 → 其余addGroup("重复源")
  ↓ appDb.rssSourceDao.update(source)
```

**关键**：realDomain 在域名校验阶段通过 AnalyzeUrl 处理后获取，去重直接复用，不重新构造AnalyzeUrl。

### 3.3 需求三数据流（权重算法回填，基于分组状态）

```
校验各维度执行（需求二）→ addGroup/removeGroup 记录维度结果
  ↓ 校验完成（doCheckSource末尾或域名失败throw前）
  ↓ SourceWeightCalculator.calculateBookWeightFromGroups / calculateRssWeightFromGroups
  ↓   读取 source.hasGroup("域名失效") 等分组状态反推各维度结果
  ↓   域名失败(hasGroup("域名失效")且domainCheckEnabled)？是→weight=0 / 否→累加各通过维度分值
  ↓ 回填 source.weight
  ↓ appDb.xxxDao.update(source)
  ↓ 排序功能（BookSourceSort.Weight）读取weight值自动生效
```

**关键**：weight计算基于分组状态(hasGroup)反推，不新增Boolean变量，不修改doCheckSource校验逻辑（最小改动）。与去重逻辑并行（去重使用successCount，权重使用分组状态，互不干扰）。

## 4. File Changes

### 需求一文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/constant/PreferKey.kt` | 修改 | 新增2个常量 |
| `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | 修改 | 新增2个属性 |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 修改 | 新增parseConcurrency字段（+需求三weight字段） |
| `app/src/main/java/io/legado/app/data/appDb.kt` | 修改 | 数据库版本94→95（合并需求一+需求三迁移） |
| `app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 修改 | Semaphore动态值 |
| `app/src/main/java/io/legado/app/help/glide/LegadoGlideModule.kt` | 修改 | setSourceExecutor |
| `app/src/main/res/xml/pref_config_other.xml` | 修改 | 新增2个Preference项 |
| `app/src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt` | 修改 | 处理新配置项 |
| `app/src/main/res/values/strings.xml` | 修改 | 新增字符串资源 |

### 需求二文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/CheckSource.kt` | 修改 | 新增 domainCheckMode 字段 + putConfig 保存 |
| `app/src/main/java/io/legado/app/service/CheckSourceService.kt` | 修改 | 域名校验按 domainCheckMode 分支(Socket/AnalyzeUrl) + 新增 checkDomainReachable 方法 + 末尾weight回填(需求三) |
| `app/src/main/java/io/legado/app/ui/config/CheckSourceConfig.kt` | 修改 | 新增 domainCheckMode RadioGroup 交互逻辑与保存 |
| `app/src/main/res/layout/dialog_check_source_config.xml` | 修改 | 新增 domain_check_mode_group RadioGroup(含2个RadioButton) |
| `app/src/main/java/io/legado/app/model/CheckRssSource.kt` | 新增 | 订阅源校验配置对象 |
| `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 新增 | 订阅源校验Service(含weight回填,需求三) |
| `app/src/main/java/io/legado/app/ui/config/CheckRssSourceConfig.kt` | 新增 | 订阅源校验配置UI |
| `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt` | 修改 | 新增校验菜单项 |
| `app/src/main/res/menu/` | 修改 | 新增校验菜单 |
| `app/src/main/res/values/strings.xml` | 修改 | 新增字符串资源(domain_check_socket/domain_check_analyze_url等) |

### 需求三文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/SourceWeightCalculator.kt` | 新增 | 权重计算器（object，书源+订阅源双算法） |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 修改 | 新增weight字段（与parseConcurrency合并迁移） |
| `app/src/main/java/io/legado/app/data/DatabaseMigrations.kt` | 修改 | migration_94_95新增weight字段ALTER语句 |
| `app/src/main/java/io/legado/app/service/CheckSourceService.kt` | 修改 | doCheckSource末尾回填source.weight |
| `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 修改 | doCheckRssSource末尾回填source.weight |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` equal() | 修改 | equal()方法加入weight比较 |
