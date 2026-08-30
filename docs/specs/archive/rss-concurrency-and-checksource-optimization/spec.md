# 需求规格：订阅源解析并发配置化 + 书源/订阅源校验去重优化

> **修订说明（2026-07-15 v4）**：根据用户检查点1反馈新增需求三(权重算法回填)。利用废弃的weight字段，校验时根据各维度通过情况计算权重值(满分100,域名不可达=0分)并回填，使排序功能生效。其余修订同v3。

## 1. Intent（意图）

### 需求一：订阅源解析并发 + 图片加载并发配置化

将 `RssParserByRule.kt` 中硬编码的 `Semaphore(6)` 改为可配置项。同时支持图片加载线程数配置。支持全局默认值和每源独立配置。

### 需求二：书源校验优化 + 订阅源校验去重综合功能

1. **书源校验优化**：域名可达性校验从 Socket 测试改为走真实请求链路
2. **订阅源校验复刻**：为订阅源新增完整校验功能（列表/搜索/分类/正文）
3. **一键去重**：校验后按域名+类型多维度去重，保留维度成功多的源，重复源进回收站
4. **维度评估**：校验结果量化为成功维度数，辅助去重决策

### 需求三：权重算法回填（复用废弃weight字段）

利用当前基本废弃的 `weight` 字段（BookSource 已有但实际值一直为0；RssSource 需新增），校验时根据各维度通过情况计算权重值（满分100分，域名不可达直接0分），回填到 `source.weight`，使 `BookSourceSort.Weight` 排序功能真正生效。

## 2. Scope（范围）

### 需求一范围

| 功能点 | 说明 |
|--------|------|
| F1.1 解析并发全局配置 | AppConfig 新增 `rssParseConcurrency`（默认3） |
| F1.2 解析并发每源配置 | RssSource 新增 `parseConcurrency` 字段（0=使用全局） |
| F1.3 替换硬编码 | `RssParserByRule.kt` Semaphore(6) → 动态读取配置 |
| F1.4 图片加载并发配置 | AppConfig 新增 `imageLoadConcurrency`（默认5） |
| F1.5 Glide 线程池配置 | LegadoGlideModule 设置 `setSourceExecutor` |
| F1.6 配置UI | pref_config_other.xml 新增两个配置项 |
| F1.7 PreferKey注册 | PreferKey 新增两个常量 |

### 需求二范围

| 功能点 | 说明 |
|--------|------|
| F2.1 书源域名校验优化 | Socket测试改为通过AnalyzeUrl真实请求校验 |
| F2.2 订阅源校验Service | 新增 CheckRssSourceService（参考CheckSourceService） |
| F2.3 订阅源校验配置 | 新增 CheckRssSource 配置对象（参考CheckSource） |
| F2.4 订阅源校验配置UI | 新增 CheckRssSourceConfig 对话框 |
| F2.5 订阅源校验维度 | 列表/搜索/分类/正文 4维度校验 |
| F2.6 去重逻辑 | 按域名+类型多维度去重 |
| F2.7 去重后处理 | 重复源 addGroup("重复源") 进回收站 |
| F2.8 订阅源管理入口 | RssSourceActivity 新增"校验所选"菜单项 |
| F2.9 权重算法回填 | 校验后计算权重值(满分100,域名不可达=0)并回填source.weight字段 |

### 需求三范围

| 功能点 | 说明 |
|--------|------|
| F3.1 书源权重算法 | 6维度权重分配(域名20+搜索20+发现15+书籍信息15+目录15+正文15=100) |
| F3.2 订阅源权重算法 | 5维度权重分配(域名20+列表25+搜索20+分类15+正文20=100) |
| F3.3 域名前置条件 | 域名校验失败→weight=0(一票否决) |
| F3.4 RssSource新增weight字段 | 数据库迁移新增weight字段(与parseConcurrency合并到94→95迁移) |
| F3.5 权重回填时机 | CheckSourceService/CheckRssSourceService校验完成后立即回填 |
| F3.6 排序功能激活 | 回填后BookSourceSort.Weight排序自动生效 |

## 3. Approach（方案）

### 3.1 需求一 Selected Approach

**双参数分离方案**：解析并发（CPU密集型，默认3）与图片加载并发（IO密集型，默认5）独立配置。

**理由**：资源维度不同——解析是CPU密集型，图片加载是IO密集型，合并会导致一个参数无法同时满足两种场景。

### 3.1.1 Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 单参数合并 | 解析和图片共用一个并发数 | CPU vs IO 资源维度不同，无法兼顾 |
| 仅全局配置 | 不支持每源配置 | 复杂规则源需降低并发，简单源可提高 |
| 运行时动态修改Glide线程池 | 不重启App修改 | Glide只初始化一次，运行时无法修改Executor |

### 3.1.2 Drawbacks

- 图片并发修改需重启App生效（GlideModule只初始化一次）
- RssSource新增字段需数据库迁移（版本94→95）

### 3.2 需求二 Selected Approach

**校验+去重一体化方案**：

1. **域名校验改进**：不直接从sourceUrl截取域名，而是构造AnalyzeUrl发起真实请求，请求成功=域名可达
2. **订阅源校验维度**：基于RssSource字段设计4维度（列表/搜索/分类/正文）
3. **去重策略**：校验完成后，按域名+type分组，同组内按校验成功维度数排序，保留最优，其余addGroup("重复源")
4. **域名提取**：从AnalyzeUrl处理后的最终请求URL提取host（支持源URL含jslib/注释/#规避/空格等复杂情况）

### 3.2.1 Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| Socket测试域名 | 当前书源方案 | 不走解析规则层，无法处理源URL复杂性 |
| 从sourceUrl正则提取域名 | 简单截取 | 源URL可能含名称/jslib/注释/#规避，截取不准 |
| 校验和去重分两步 | 先校验再手动去重 | 用户体验差，需一键完成 |
| 按域名单维度去重 | 不区分类型 | 同域名不同类型(网页/图片/视频)需保留各自源 |

### 3.2.2 Drawbacks

- 域名校验走真实请求比Socket慢（但更准确）
- 去重逻辑可能误判（同域名不同子路径可能是不同源）
- 订阅源校验维度少于书源（无目录概念）

### 3.2.3 源URL复杂性处理（用户强调不能动的规则）

源URL可能包含：
- 名称文本（非URL）
- jslib执行（`<js></js>` 标签，JS内含真实URL）
- 注释入参（`<!-- -->` 内放参数）
- `#` 规避重复（URL末尾加#xxx）
- 前后空格

**处理方案**：不直接操作sourceUrl字段，而是通过 `AnalyzeUrl` 类的完整解析链路处理。AnalyzeUrl 已支持上述所有情况，校验时构造 AnalyzeUrl 发起请求即可。

### 3.3 需求三 Selected Approach

**权重算法回填方案**：校验时根据各维度通过情况计算权重值(满分100)，域名可达性作为前置条件(失败则总分0)，其他维度按权重分配分值，校验完成立即回填source.weight字段。

**权重分配**:

书源6维度（满分100）：
| 维度 | 分值 | 说明 |
|------|------|------|
| 域名可达性 | 20 | 前置条件，失败=总分0 |
| 搜索 | 20 | 核心搜索功能 |
| 发现 | 15 | 辅助发现 |
| 书籍信息 | 15 | 详情页 |
| 目录 | 15 | 阅读必需 |
| 正文 | 15 | 阅读核心 |

订阅源5维度（满分100）：
| 维度 | 分值 | 说明 |
|------|------|------|
| 域名可达性 | 20 | 前置条件，失败=总分0 |
| 列表 | 25 | 核心功能 |
| 搜索 | 20 | 辅助功能 |
| 分类 | 15 | 辅助功能 |
| 正文 | 20 | 阅读核心 |

**理由**：
- 域名可达性是硬性前置条件（网络不可联通源无法使用，直接0分）
- 搜索/正文是核心阅读功能，权重较高
- 发现/分类/书籍信息/目录是辅助功能，权重较低
- 用户强调"满分100分，网络不可联通直接0分"

### 3.3.1 Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 权重值用户手动配置 | 不自动计算 | 用户不会手动维护，weight字段废弃根因 |
| 权重值不回填只显示 | 仅UI展示 | 排序功能无法生效，weight字段仍废弃 |
| 域名失败不归零 | 域名失败仅扣域名分值 | 用户明确要求"网络不可联通直接0分" |
| 维度均分权重 | 每维度20分 | 核心功能(搜索/正文)和辅助功能(发现/分类)权重应区分 |

### 3.3.2 Drawbacks

- 校验回填会覆盖用户手动设置的weight值（但用户说基本废弃，实际都是0，可接受）
- 不同维度权重固定，不支持用户自定义分配（后续可扩展）

## 4. Requirements（需求）

### 4.1 需求一详细需求

#### R1.1 AppConfig 配置项

```kotlin
// AppConfig.kt 新增
var rssParseConcurrency: Int
    get() = appCtx.getPrefInt(PreferKey.rssParseConcurrency, 3)
    set(value) { appCtx.putPrefInt(PreferKey.rssParseConcurrency, value) }

var imageLoadConcurrency: Int
    get() = appCtx.getPrefInt(PreferKey.imageLoadConcurrency, 5)
    set(value) { appCtx.putPrefInt(PreferKey.imageLoadConcurrency, value) }
```

#### R1.2 PreferKey 注册

```kotlin
// PreferKey.kt 新增（object内常量）
const val rssParseConcurrency = "rssParseConcurrency"
const val imageLoadConcurrency = "imageLoadConcurrency"
```

#### R1.3 RssSource 新增字段

```kotlin
// RssSource.kt 新增
@ColumnInfo(defaultValue = "0")
var parseConcurrency: Int = 0  // 0=使用全局配置
```

数据库迁移：版本94→95，ALTER TABLE rssSources ADD COLUMN parseConcurrency INTEGER DEFAULT 0。

#### R1.4 RssParserByRule 修改

```kotlin
// RssParserByRule.kt L86 修改
// 旧: val parseSemaphore = Semaphore(6)
// 新:
val parseConcurrency = rssSource.parseConcurrency.takeIf { it > 0 }
    ?: AppConfig.rssParseConcurrency
val parseSemaphore = Semaphore(parseConcurrency)
```

#### R1.5 LegadoGlideModule 修改

```kotlin
// LegadoGlideModule.kt applyOptions 新增
override fun applyOptions(context: Context, builder: GlideBuilder) {
    // 现有代码...
    builder.setSourceExecutor(
        GlideExecutor.newSourceExecutor(
            AppConfig.imageLoadConcurrency
        )
    )
}
```

**注意**：GlideModule只在App启动时初始化一次，修改图片并发需重启App。UI需提示用户。

#### R1.6 配置UI

在 `pref_config_other.xml` 的"其他设置"分类中，`threadCount` 配置项后新增：

```xml
<io.legado.app.lib.prefs.Preference
    android:key="rssParseConcurrency"
    android:title="@string/rss_parse_concurrency_title"
    app:iconSpaceReserved="false" />

<io.legado.app.lib.prefs.Preference
    android:key="imageLoadConcurrency"
    android:title="@string/image_load_concurrency_title"
    app:iconSpaceReserved="false" />
```

OtherConfigFragment 处理：
- `onPreferenceTreeClick`: NumberPickerDialog 设置值
- `onSharedPreferenceChanged`: upPreferenceSummary 更新摘要
- `onCreatePreferences`: upPreferenceSummary 初始化摘要

### 4.2 需求二详细需求

#### R2.1 书源域名校验优化

```kotlin
// CheckSourceService.kt doCheckSource 修改
// 旧: isDomainReachable(domain) Socket测试
// 新: 通过 AnalyzeUrl 发起真实请求校验
if (CheckSource.checkDomain) {
    val analyzeUrl = AnalyzeUrl(
        source.bookSourceUrl,
        source = source,
        ruleData = RuleData(),
        coroutineContext = currentCoroutineContext()
    )
    try {
        analyzeUrl.getStrResponseAwait()
        source.removeGroup("域名失效")
    } catch (e: Exception) {
        source.addGroup("域名失效")
        throw NoStackTraceException("源地址不可访问")
    }
}
```

**注意**：`isDomainReachable` Socket方法保留但不再默认使用，作为快速检测可选方案。

**ADJ-3 配置项**：CheckSource 新增 `domainCheckMode`（Int，0=Socket快速检测, 1=AnalyzeUrl真实请求, 默认1）：
```kotlin
// CheckSource.kt 新增
var domainCheckMode = CacheManager.getInt("domainCheckMode") ?: 1
```
CheckSourceConfig UI 新增域名校验方式选择（Socket/AnalyzeUrl）。

**ADJ-5 默认值变更**：CheckSource.checkDomain 默认值从 `false` 改为 `true`（域名校验默认启用）。
对应 CheckSource.kt L19: `?: false` → `?: true`

#### R2.2 订阅源校验配置对象

```kotlin
// 新增 CheckRssSource.kt (object)
object CheckRssSource {
    var timeout = CacheManager.getLong("checkRssSourceTimeout") ?: 180000L
    var checkDomain = CacheManager.get("checkRssDomain")?.toBoolean() ?: true
    var checkArticles = CacheManager.get("checkRssArticles")?.toBoolean() ?: true
    var checkSearch = CacheManager.get("checkRssSearch")?.toBoolean() ?: true
    var checkSort = CacheManager.get("checkRssSort")?.toBoolean() ?: true
    var checkContent = CacheManager.get("checkRssContent")?.toBoolean() ?: true
    var wSourceComment = CacheManager.get("wRssSourceComment")?.toBoolean() ?: true
    // 去重配置
    var enableDedup = CacheManager.get("enableRssDedup")?.toBoolean() ?: false
    val summary get() = upSummary()
}
```

#### R2.3 订阅源校验Service

```kotlin
// 新增 CheckRssSourceService.kt
// 参考 CheckSourceService.kt 结构
class CheckRssSourceService : BaseService() {
    // check(ids) → onEachParallel → checkRssSource → doCheckRssSource
    // doCheckRssSource:
    //   1. checkDomain: AnalyzeUrl真实请求
    //   2. checkArticles: Rss.getArticlesAwait获取列表
    //   3. checkSearch: 如果有searchUrl，执行搜索
    //   4. checkSort: 如果有sortUrl，获取分类
    //   5. checkContent: ruleContent解析文章正文
    //   6. 去重: 按域名+type分组，保留维度成功多的
}
```

**ADJ-7 通知栏进度**：CheckRssSourceService 必须实现前台 Service + 通知栏进度（参考 CheckSourceService.kt L58-63）：
- 启动时 `startForeground` 显示"正在校验订阅源"
- 每完成一个源更新通知进度（current/total）
- 完成后通知"校验完成，成功X个，失败Y个，重复Z个"
- 长时间校验（5维度 × N个源）如果没有前台Service+通知，Android后台可能杀进程

#### R2.4 订阅源校验维度

| 维度 | 校验方法 | 成功条件 | 对应字段 |
|------|---------|---------|---------|
| 域名可达性 | AnalyzeUrl真实请求 | 请求成功无异常 | sourceUrl |
| 列表解析 | Rss.getArticlesAwait | 文章列表非空 | ruleArticles |
| 搜索 | Rss.getArticlesAwait(key) | 搜索结果非空 | searchUrl |
| 分类 | 解析sortUrl获取分类 | 分类列表非空 | sortUrl |
| 正文 | ruleContent解析 | 正文非空 | ruleContent |

#### R2.5 去重逻辑（复用域名校验结果）

**核心原则**：域名去重**依赖于域名校验**，使用校验时通过AnalyzeUrl处理后的真实域名，不单独从sourceUrl截取。

```kotlin
// 校验结果数据结构
data class CheckResult(
    val source: RssSource,
    val successCount: Int,      // 校验成功维度数
    val realDomain: String?     // 从AnalyzeUrl处理后的最终URL提取的host
)

// 去重流程
1. 校验时记录真实域名: doCheckRssSource 中, AnalyzeUrl处理sourceUrl → 获取最终URL → URI(url).host → 记录到CheckResult.realDomain
2. 收集所有 CheckResult: List<CheckResult>
3. 按realDomain分组: Map<String, List<CheckResult>>
   - realDomain 来自域名校验阶段的 AnalyzeUrl 处理结果
   - 如果域名校验关闭, 仍需构造AnalyzeUrl提取域名(不发起请求, 仅获取处理后的URL)
4. 每个域名组内按type二次分组: Map<Int, List<CheckResult>>
   - type: 0=网页, 1=图片, 2=视频
5. 每个子组内按successCount降序排序
6. 保留第1名（维度成功最多的），其余 addGroup("重复源")
7. 更新到数据库
```

**为什么不能单纯使用sourceUrl**：源URL填写格式多样化（含名称/jslib执行/注释入参/#规避/空格），直接截取域名无法达到去重目的。必须通过AnalyzeUrl的完整解析链路处理。

#### R2.6 订阅源管理入口

在 RssSourceActivity 菜单中新增"校验所选"项，触发 CheckRssSourceService。

### 4.3 需求三详细需求（权重算法回填）

#### R3.1 字段现状与新增

**BookSource（已有weight字段）**:
- `BookSource.kt` L80: `var weight: Int = 0`（注释"智能排序的权重"，实际值一直为0基本废弃）
- `BookSourceViewModel.kt` L223/L242: `BookSourceSort.Weight -> data.sortedBy { it.weight }`（排序功能已存在但weight=0导致排序无效）
- 无需新增字段，校验后回填即可激活排序

**RssSource（需新增weight字段）**:
- `RssSource.kt` 当前无weight字段
- 数据库迁移新增：`ALTER TABLE rssSources ADD COLUMN weight INTEGER NOT NULL DEFAULT 0`
- **合并迁移**：与 parseConcurrency 合并到同一个 migration_94_95（一条ALTER语句两个字段，或两条ALTER语句）

```kotlin
// DatabaseMigrations.kt migration_94_95（合并parseConcurrency + weight）
private val migration_94_95 = object : Migration(94, 95) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE rssSources ADD COLUMN parseConcurrency INTEGER NOT NULL DEFAULT 0")
        db.execSQL("ALTER TABLE rssSources ADD COLUMN weight INTEGER NOT NULL DEFAULT 0")
    }
}
```

#### R3.2 权重计算算法

**关键设计决策**: 基于source分组状态(hasGroup)计算weight，不修改doCheckSource结构（最小改动）

**设计理由**: doCheckSource现有代码用addGroup/removeGroup记录维度结果，无Boolean变量。新增Boolean变量需重构doCheckSource，改动大风险高。基于分组状态反推各维度结果，不破坏现有校验流程。

```kotlin
// 新增 SourceWeightCalculator.kt (object)
object SourceWeightCalculator {
    // 书源维度分值（满分100）
    const val BOOK_DOMAIN_SCORE = 20
    const val BOOK_SEARCH_SCORE = 20
    const val BOOK_DISCOVERY_SCORE = 15
    const val BOOK_INFO_SCORE = 15
    const val BOOK_CATEGORY_SCORE = 15
    const val BOOK_CONTENT_SCORE = 15
    // 订阅源维度分值（满分100）
    const val RSS_DOMAIN_SCORE = 20
    const val RSS_ARTICLES_SCORE = 25
    const val RSS_SEARCH_SCORE = 20
    const val RSS_SORT_SCORE = 15
    const val RSS_CONTENT_SCORE = 20

    /**
     * 基于BookSource分组状态计算权重（满分100）
     * 不需要修改doCheckSource结构，通过hasGroup反推各维度状态
     * 分组名对照（CheckSourceService.kt源码核实）:
     *   域名失效/搜索失效/搜索链接规则为空/发现失效/发现规则为空
     *   /搜索目录失效/发现目录失效/搜索正文失效/发现正文失效
     */
    fun calculateBookWeightFromGroups(source: BookSource, domainCheckEnabled: Boolean): Int {
        if (domainCheckEnabled && source.hasGroup("域名失效")) return 0
        var weight = 0
        if (!domainCheckEnabled || !source.hasGroup("域名失效")) weight += BOOK_DOMAIN_SCORE
        if (!source.hasGroup("搜索失效") && !source.hasGroup("搜索链接规则为空")) weight += BOOK_SEARCH_SCORE
        if (!source.hasGroup("发现失效") && !source.hasGroup("发现规则为空")) weight += BOOK_DISCOVERY_SCORE
        weight += BOOK_INFO_SCORE  // 详情: checkBook成功完成(失败throw)=通过
        if (!source.hasGroup("搜索目录失效") && !source.hasGroup("发现目录失效")) weight += BOOK_CATEGORY_SCORE
        if (!source.hasGroup("搜索正文失效") && !source.hasGroup("发现正文失效")) weight += BOOK_CONTENT_SCORE
        return weight
    }

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

**校验关闭维度的处理**: 校验关闭的维度不addGroup，weight计算时hasGroup返回false→给满分（不扣分）。符合"校验关闭=不扣分"原则。

**完整实现详见**: design.md 1.3.2节（含分组名源码行号对照）

#### R3.3 回填时机

**书源**：`CheckSourceService` 的 `doCheckSource` 两处插入点（最小改动，不修改现有校验逻辑）：
```kotlin
// 1. 域名校验失败时（L189-190 throw前）
source.addGroup("域名失效")
source.weight = 0  // 域名失败回填0分
throw NoStackTraceException("源地址不可访问")

// 2. 所有维度校验完成后（L227 getInvalidGroupNames前）
source.weight = SourceWeightCalculator.calculateBookWeightFromGroups(
    source, CheckSource.checkDomain
)
val finalCheckMessage = source.getInvalidGroupNames()
```

**订阅源**：`CheckRssSourceService` 的 `doCheckRssSource` 末尾（return CheckResult前）：
```kotlin
source.weight = SourceWeightCalculator.calculateRssWeightFromGroups(
    source, CheckRssSource.checkDomain
)
return CheckResult(source, successCount, realDomain)
```

#### R3.4 兼容性说明

- BookSource已有weight字段，回填后 `BookSourceSort.Weight` 排序自动生效（无需修改排序代码）
- RssSource新增weight字段后，可在 RssSourceViewModel 排序中新增 Weight 排序选项（可选，非必须）
- 校验回填会覆盖用户手动设置的weight值（用户说基本废弃实际都是0，可接受；若用户不想覆盖可不校验）

## 5. Scenarios（场景）

### 场景1：配置解析并发

用户进入"我的→其他设置"，看到"订阅源解析并发"配置项，点击弹出NumberPickerDialog（1-10），设置3。返回列表后立即生效。

### 场景2：配置图片加载并发

用户设置"图片加载并发"为5，提示"需重启App生效"。重启后Glide使用5线程加载图片。

### 场景3：校验订阅源

用户在订阅源管理界面选择多个源，点击"校验所选"。CheckRssSourceService启动，并行校验每个源的5个维度。校验完成后通知。

### 场景4：去重

校验完成后，如果启用去重：
1. 按域名分组
2. 每个域名内按type(网页/图片/视频)二次分组
3. 每个子组保留校验成功维度最多的源
4. 其余源addGroup("重复源")

### 场景5：源URL含复杂内容

源URL为 `搜索,<js>java_url + "?key=searchKey"</js> #规避重复`：
- 不直接截取域名
- 构造AnalyzeUrl，JS执行后得到真实URL
- 从真实URL提取host用于去重
- 真实请求校验域名可达性

### 场景6：权重算法回填

用户校验书源A（域名通过+搜索通过+正文通过，其他失败）：
- 域名(20) + 搜索(20) + 正文(15) = 55分
- 回填 source.weight = 55

用户校验书源B（域名失败）：
- 域名失败 → weight = 0（一票否决）

用户校验订阅源C（域名通过+列表通过+正文通过，搜索分类失败）：
- 域名(20) + 列表(25) + 正文(20) = 65分
- 回填 source.weight = 65

校验完成后用户选择按Weight排序，源A(55)排在源B(0)前面，源C(65)排在源A前面。
