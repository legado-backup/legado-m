# 书源/订阅源一键互转 - 技术设计

> 状态: 设计中（V9 - R5降级/sourceRegex/音频评级3项CRITICAL补充版）
> 依赖: spec.md
> 更新日志：V9基于运行时流程深度验证，发现V8遗漏3个关键问题：①BookSource视频播放路径无R5自动提取降级（content为空时抛ContentEmptyException，而RssSource有完整R5自动提取流程）②ContentRule.sourceRegex未映射（WebView资源嗅探，音频源核心功能）③音频源评级虚高（★★★★★→★★★☆☆，RssSource无音频类型，AudioPlay仅支持BookSource）。新增改动10/11/12

## 深度可用性分析（核心章节）

> **这是本次设计最关键的章节**。转换后如果不能用，功能就没意义。以下基于源码级别的运行时分析，逐场景评估转换后源的实际可用性。

### 解析引擎运行时流程对比

#### 书源运行时流程（WebBook + BookList + BookInfo + BookChapterList + BookContent）

```
搜索/发现入口
  │
  ├─ exploreUrl → BookList.analyzeBookList(isSearch=false) → ExploreRule
  └─ searchUrl  → BookList.analyzeBookList(isSearch=true)  → SearchRule
       │
       ├─ BookListRule.bookList → 获取列表集合
       ├─ BookListRule.name    → 标题
       ├─ BookListRule.bookUrl → 详情页链接
       ├─ BookListRule.coverUrl→ 封面
       ├─ BookListRule.intro   → 简介
       ├─ BookListRule.author  → 作者
       ├─ BookListRule.kind    → 分类
       │
       ▼
  点击搜索结果 → BookInfo.analyzeBookInfo()
       │
       ├─ BookInfoRule.name    → 书名
       ├─ BookInfoRule.coverUrl→ 封面
       ├─ BookInfoRule.intro   → 简介
       ├─ BookInfoRule.tocUrl  → 目录页链接（若与详情页不同）
       │
       ▼
  加载目录 → BookChapterList.analyzeChapterList()
       │
       ├─ TocRule.chapterList → 章节列表集合 ← 关键！没有此规则无法获取章节
       ├─ TocRule.chapterName → 章节名
       ├─ TocRule.chapterUrl  → 章节链接
       │
       ▼
  阅读正文 → BookContent.analyzeContent()
       │
       ├─ ContentRule.content        → 正文内容
       ├─ ContentRule.nextContentUrl → 下一页（翻页）
       ├─ ContentRule.replaceRegex   → 替换规则
       ├─ ContentRule.webJs          → WebView注入
```

#### 订阅源运行时流程（Rss + RssParserByRule）

```
分类浏览入口
  │
  └─ sortUrl → Rss.getArticlesAwait() → RssParserByRule.parseXML()
       │
       ├─ ruleArticles    → 获取列表集合
       ├─ ruleTitle       → 标题
       ├─ ruleLink        → 文章链接
       ├─ ruleImage       → 图片
       ├─ ruleDescription → 描述
       ├─ rulePubDate     → 发布日期
       ├─ ruleNextPage    → 下一页
       │
       ▼
  点击文章 → Rss.getContentAwait()
       │
       ├─ type==2 && ruleRoutes非空 && ruleEpisodes非空
       │   → getRoutesContentAwait() → 多线路多集模式
       │
       └─ ruleContent → 正文内容（简单字符串规则）
```

### 场景1：文本书源 → 订阅源（可用性：高 ★★★★☆）

**可用性分析**：
- ✅ 列表浏览：ExploreRule.bookList → ruleArticles，可正常列出文章
- ✅ 标题/封面/链接：ExploreRule.name/coverUrl/bookUrl → ruleTitle/ruleImage/ruleLink
- ✅ 简介：ExploreRule.intro → ruleDescription
- ✅ 正文：ContentRule.content → ruleContent，但仅保留content字段，subContent/replaceRegex等丢失
- ✅ 分类：exploreUrl → sortUrl
- ⚠️ 丢失TocRule：不影响订阅源功能，因为订阅源没有目录概念
- ⚠️ 丢失BookInfoRule：不影响订阅源功能，因为订阅源没有详情页
- ⚠️ ContentRule子字段丢失：replaceRegex（替换规则）丢失可能导致正文包含广告/杂乱内容

**结论：文本书源转订阅源后，分类浏览+文章列表+阅读正文的核心流程可用。主要问题是ContentRule子字段丢失导致正文可能有杂乱内容。**

### 场景2：图片书源 → 订阅源（可用性：高 ★★★★☆）

**图片源运行时流程**：
- 图片书源(bookSourceType=2)：搜索/发现 → 列表 → TocRule获取图片章节 → ContentRule获取图片URL列表 → ImageGalleryActivity展示
- 图片订阅源(type=1)：分类 → 列表(ruleArticles/ruleTitle/ruleLink/ruleImage) → ruleContent获取图片 → ImageGalleryActivity展示

**可用性分析**：
- ✅ 列表浏览：ExploreRule.bookList → ruleArticles
- ✅ 标题/封面/链接：映射正确
- ✅ 图片内容：ContentRule.content → ruleContent，图片URL列表规则可复用
- ✅ 类型映射正确：bookSourceType=2 → RssSource.type=1
- ⚠️ TocRule丢失：图片书源用TocRule组织图片章节，但订阅源是扁平文章列表，每个文章独立包含图片
  - 实际影响：图片书源的TocRule将整个图片集拆分为多个章节，转换后每个文章就是一个图片集，正文就是图片列表
  - 如果书源的TocRule只有一章（整个图集），转换后完美适配
  - 如果书源的TocRule有多章（如漫画分话），转换后只能展示第一个"话"的文章内容
- ⚠️ ContentRule.imageStyle/imageDecode丢失：可能影响图片显示

**结论：图片书源转订阅源后，单章图集完美适配，多章图集只能展示第一章。核心浏览+查看图片功能可用。**

### 场景3：视频书源 → 订阅源（可用性：中 ★★★☆☆）

**可用性分析**：
- ✅ 基础流程同文本书源
- ✅ 类型映射正确：bookSourceType=4 → RssSource.type=2
- ❌ 多线路/多集丢失：BookSource无ruleRoutes/ruleEpisodes，转换后订阅源无多线路多集支持
- ⚠️ 视频播放需要多线路支持，无ruleRoutes/ruleEpisodes时只能播放单线路

**结论：视频书源转订阅源后，可以浏览视频列表和查看详情，但无法使用多线路多集功能。需要在转换后手动添加ruleRoutes/ruleEpisodes规则才能正常播放视频。**

### 场景4：订阅源 → 文本书源（可用性：低→高，智能TocRule后★★★★☆）

**可用性分析**：
- ✅ 列表浏览：ruleArticles → SearchRule.bookList + ExploreRule.bookList，可搜索和发现
- ✅ 标题/封面/链接：ruleTitle/ruleImage/ruleLink → SearchRule.name/coverUrl/bookUrl
- ❌ **关键缺失：无TocRule** — 书源必须有TocRule才能获取章节列表，否则无法进入阅读
  - BookChapterList.analyzeChapterList() 使用 TocRule.chapterList 获取章节
  - 没有TocRule = 没有章节列表 = 无法打开任何章节阅读
- ❌ **关键缺失：无BookInfoRule** — 书源默认需要BookInfoRule获取书籍详情
  - BookInfo.analyzeBookInfo() 使用 BookInfoRule 各字段
  - 不过，如果搜索结果已包含必要信息（name/bookUrl），详情页解析可能部分可用
- ✅ 正文：ruleContent → ContentRule.content
- ⚠️ 无author字段：RssSource无作者规则，书源会缺少作者信息

**结论：订阅源转书源后，搜索和发现可以列出结果，但无法进入阅读！因为缺少TocRule，无法获取章节列表。这是致命缺陷。**

通过智能TocRule生成后可用性提升到★★★★☆。

### 场景5：图片订阅源 → 书源（可用性：中→高，智能TocRule后★★★★☆）

**可用性分析**：
- ✅ 列表浏览：ruleArticles → SearchRule.bookList + ExploreRule.bookList
- ✅ 标题/封面/链接映射正确
- ✅ 图片内容：ruleContent → ContentRule.content
- ✅ 类型映射：RssSource.type=1 → bookSourceType=2
- ✅ 智能TocRule生成：ruleArticles→chapterList, ruleTitle→chapterName, ruleLink→chapterUrl
- ⚠️ 图片书源用TocRule将文章拆分为多个图片章节，每个"章节"是一个图片集
  - 订阅源的每个文章对应书源的一个"章节"，正文就是图片列表
  - 智能TocRule正确映射后，点击目录项→加载对应文章页→ContentRule解析图片列表→ImageGalleryActivity展示

**结论：图片订阅源转书源后，智能TocRule使核心阅读流程可用。每个文章变为一个章节，图片列表作为正文展示。**

### 场景6：视频订阅源 → 书源（可用性：极低★☆☆☆☆，有多线路适配困难）

**可用性分析**：
- ✅ 列表浏览基本可用
- ✅ 智能TocRule可生成：ruleArticles→chapterList, ruleTitle→chapterName, ruleLink→chapterUrl
- ❌ **多线路/多集与TocRule的适配问题**（核心分析）：

**ruleEpisodes与TocRule的映射可行性**：

ruleEpisodes的数据结构是 `List<RssEpisode>(title, url)`，每个RssEpisode代表一个"集"。
TocRule的数据结构是 `chapterList/chapterName/chapterUrl`，每个chapter代表一个"章"。

表面上看，RssEpisode.title → TocRule.chapterName，RssEpisode.url → TocRule.chapterUrl，似乎可以映射。但存在关键差异：

1. **单线路适配**：ruleEpisodes只采集一个线路的集数，如果视频源只有单线路，可以用ruleEpisodes替代ruleArticles生成TocRule，此时每个"集"对应一个"章"，ContentRule.content获取播放URL
2. **多线路无法适配**：ruleRoutes产生多个线路名，每个线路有独立的集数列表。TocRule只有一套章节列表，无法表示"多套章节"
3. **{routeIndex}占位符问题**：ruleEpisodes支持`{routeIndex}`占位符，根据线路索引动态生成集数规则。TocRule不支持这种动态占位符

**多线路适配方案评估**：

| 方案 | 可行性 | 说明 |
|------|--------|------|
| 仅用第一线路 | ★★★☆☆ | 忽略其他线路，只用ruleEpisodes(routeIndex=0)的集数生成TocRule |
| 所有线路的集数合并 | ★★☆☆☆ | 将多线路集数全部放入一个TocRule，但无法区分线路 |
| 不映射多线路 | ★★★★☆ | 智能TocRule用ruleArticles生成目录，视频正文通过ContentRule.content获取播放URL（单线路） |

**推荐方案**：智能TocRule使用ruleArticles生成目录（文章=章节），ContentRule.content用ruleContent获取播放URL。这是最安全的方案，因为：
- ruleArticles是确定性的列表规则，不含{routeIndex}占位符
- 每个文章链接可以打开详情页，ruleContent解析出播放URL
- 单线路播放可用，多线路需要手动补充规则

**结论：视频订阅源转书源后，单线路播放可用，多线路不可用。这是BookSource数据结构的根本限制——没有"线路"概念。**

### 可用性总结与改进策略

| 方向 | 原始可用性 | 改进后可用性 | 改进措施 |
|------|----------|------------|---------|
| 书源→订阅源(文本) | ★★★★☆ | ★★★★☆ | 核心流程可用，replaceRegex丢失是主要问题 |
| 书源→订阅源(图片) | ★★★★☆ | ★★★★☆ | 单章图集完美适配，多章图集受限于订阅源扁平结构 |
| 书源→订阅源(视频) | ★★★☆☆ | ★★★☆☆ | 单线路可用，多线路需手动添加ruleRoutes/ruleEpisodes |
| 订阅源→书源(文本) | ★★☆☆☆ | ★★★★☆ | **智能TocRule生成**解决致命缺陷 |
| 订阅源→书源(图片) | ★★☆☆☆ | ★★★★☆ | **智能TocRule生成**，文章=图片章节 |
| 订阅源→书源(视频) | ★☆☆☆☆ | ★★☆☆☆ | 智能TocRule+单线路播放，多线路不可用（BookSource根本限制） |

### 关键改进：智能TocRule生成

**问题**：订阅源→书源最大障碍是缺少TocRule。

**发现**：分析BookChapterList源码后发现，TocRule的核心字段是：
- `chapterList`：章节列表选择器
- `chapterName`：章节名选择器
- `chapterUrl`：章节URL选择器

**解决方案**：利用订阅源已有规则智能构造简化版TocRule：

```kotlin
// 订阅源→书源时的TocRule智能生成
val tocRule = TocRule().apply {
    // chapterList：如果sortUrl存在，用sortUrl页面作为目录页，
    // ruleArticles作为列表选择器（因为sortUrl页面的文章列表就是"目录"）
    chapterList = rssSource.ruleArticles
    // chapterName：文章标题即章节名
    chapterName = rssSource.ruleTitle
    // chapterUrl：文章链接即章节URL
    chapterUrl = rssSource.ruleLink
}
```

**原理**：
1. 订阅源的sortUrl页面展示文章列表，这实际上就是一个"目录"
2. ruleArticles选择的每个元素就是一个"章节"
3. ruleTitle就是章节名，ruleLink就是章节URL
4. 这样构造的TocRule，配合ContentRule.content，可以实现基本的阅读流程

**限制**：
- 只适用于单页目录（不支持nextTocUrl翻页，除非sortUrl本身支持分页）
- 章节顺序与订阅源文章列表顺序一致
- 对于视频订阅源，这只能实现单线路播放（第一集/第二集/...），无法实现多线路切换

### 关键改进：ContentRule增强映射

**问题**：书源→订阅源时，ContentRule的子字段（replaceRegex等）丢失导致正文杂乱。

**解决方案**：将ContentRule的replaceRegex规则编码到ruleContent中，利用AnalyzeRule的规则组合语法：

```kotlin
// 书源→订阅源时的ContentRule增强映射
val contentRule = bookSource.getContentRule()
rssSource.ruleContent = buildString {
    contentRule.content?.let { append(it) }
    // 如果有替换规则，追加@css:或@js:方式实现替换（简化处理）
    // 实际上AnalyzeRule不支持在规则字符串中嵌入replaceRegex
    // 所以这里只能保留content字段，replaceRegex效果丢失
}
```

**结论**：replaceRegex无法编码到ruleContent字符串中（AnalyzeRule不支持），只能在预览中明确提示"替换规则丢失，正文可能含广告"。这是一个无法自动解决的技术限制。

### 关键改进：视频源转换的特殊处理

**书源→订阅源(视频)**：
- 视频书源通常只有单线路（BookSource的视频模式较简单）
- 转换后作为单线路视频订阅源仍可使用
- 预览中提示"已转为单线路模式，如需多线路请手动添加ruleRoutes/ruleEpisodes"

**订阅源→书源(视频)**：
- 这是最困难的转换方向
- 多线路/多集规则无法映射到BookSource
- 即使有智能TocRule，也只能实现单线路播放
- 预览中用红色警告："视频订阅源转书源后仅支持单线路播放，多线路功能不可用"

---

## Architecture Overview

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     UI Layer                            │
│  BookSourceAdapter ─────► SourceConvertDialog           │
│  RssSourceAdapter  ─────► SourceConvertDialog           │
│  (批量选择菜单) ─────────► SourceConvertDialog           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Converter Layer                         │
│  SourceConverter (object)                                │
│    ├─ bookSourceToRssSource(bookSource): ConvertResult   │
│    ├─ rssSourceToBookSource(rssSource): ConvertResult    │
│    └─ generateSmartTocRule(rssSource): TocRule?         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Data Layer                             │
│  appDb.bookSourceDao().insert()                          │
│  appDb.rssSourceDao().insert()                           │
└─────────────────────────────────────────────────────────┘
```

### 核心类设计

#### 1. SourceConverter (object 单例)

```kotlin
object SourceConverter {

    /** 可用性等级 */
    enum class Usability {
        HIGH,       // 核心功能可用，小问题
        MEDIUM,     // 部分功能不可用，需手动补充
        LOW,        // 核心功能不可用，需大量手动补充
        UNUSABLE    // 几乎不可用
    }

    /** 转换结果 */
    data class ConvertResult(
        val target: Any,                          // 目标源实体
        val mappedFields: List<FieldMapping>,     // 成功映射字段
        val lostFields: List<FieldLoss>,          // 将丢失字段
        val warnings: List<String>,               // 警告信息
        val usability: Usability,                 // 可用性评估
        val usabilitySummary: String              // 可用性摘要（面向用户）
    )

    data class FieldMapping(
        val semantic: String,
        val fromField: String,
        val toField: String,
        val valuePreview: String?    // 映射值预览（截取前30字符）
    )

    data class FieldLoss(
        val semantic: String,
        val fieldName: String,
        val hasValue: Boolean,
        val impact: Impact           // 丢失影响
    )

    enum class Impact {
        NONE,         // 不影响使用
        MINOR,        // 轻微影响（如缺少作者信息）
        MAJOR,        // 重大影响（如正文替换规则丢失）
        CRITICAL      // 致命影响（如目录规则丢失导致无法阅读）
    }

    /** 书源→订阅源 */
    fun bookSourceToRssSource(bookSource: BookSource): ConvertResult

    /** 订阅源→书源 */
    fun rssSourceToBookSource(rssSource: RssSource): ConvertResult

    /** 智能生成TocRule（订阅源→书源专用） */
    private fun generateSmartTocRule(rssSource: RssSource): TocRule?
}
```

#### 2. SourceConvertDialog (BottomSheetDialogFragment)

```
┌──────────────────────────────────────────┐
│  文本书源 → 订阅源                       │
│  可用性: ★★★★☆ 核心功能可用             │
├──────────────────────────────────────────┤
│ ✓ 已映射 (14字段)                       │
│   源URL → sourceUrl                     │
│   分类URL → sortUrl                     │
│   列表规则 → ruleArticles               │
│   ...                                   │
├──────────────────────────────────────────┤
│ ✗ 将丢失 (8字段)                        │
│   🔴 替换规则 ContentRule.replaceRegex  │
│      → 正文可能含广告                   │
│   ⚪ 目录规则 TocRule (无值)             │
│   ⚪ 段评规则 ReviewRule (无值)          │
│   ...                                   │
├──────────────────────────────────────────┤
│ ⚠ 注意事项                              │
│   • ContentRule替换规则丢失，正文可能   │
│     含广告或杂乱内容                    │
│   • 建议转换后检查正文质量              │
├──────────────────────────────────────────┤
│      [取消]      [确认转换]              │
└──────────────────────────────────────────┘
```

对于低可用性转换，对话框顶部显示醒目警告：

```
┌──────────────────────────────────────────┐
│  ⚠️ 视频订阅源 → 书源                    │
│  可用性: ★☆☆☆☆ 转换后几乎不可用！       │
│  ─────────────────────────────────      │
│  转换后无法获取章节列表，无法进入阅读！  │
│  视频多线路功能不可用！                  │
│  建议直接在订阅源中使用，而非转换。      │
├──────────────────────────────────────────┤
│ ...                                     │
├──────────────────────────────────────────┤
│  [取消]    [仍要转换]                    │
└──────────────────────────────────────────┘
```

## Field Mapping Rules

### 书源→订阅源 (bookSourceToRssSource)

#### 基础字段直接映射（19个字段）

| BookSource | RssSource | 说明 |
|-----------|-----------|------|
| bookSourceUrl | sourceUrl | 直接复制 |
| bookSourceName | sourceName | 直接复制 |
| bookSourceGroup | sourceGroup | 直接复制 |
| bookSourceComment | sourceComment | 直接复制 |
| enabled | enabled | 直接复制 |
| enabledCookieJar | enabledCookieJar | 直接复制 |
| concurrentRate | concurrentRate | 直接复制 |
| header | header | 直接复制 |
| loginUrl | loginUrl | 直接复制 |
| loginUi | loginUi | 直接复制 |
| loginCheckJs | loginCheckJs | 直接复制 |
| coverDecodeJs | coverDecodeJs | 直接复制 |
| variableComment | variableComment | 直接复制 |
| jsLib | jsLib | 直接复制 |
| customOrder | customOrder | 直接复制 |
| weight | weight | 直接复制 |
| lastHost | lastHost | 直接复制 |
| exploreUrl | sortUrl | 直接复制 |
| searchUrl | searchUrl | 直接复制 |

#### 类型映射

| BookSourceType | RssSource.type | 说明 |
|---------------|----------------|------|
| 0 (文本) | 0 (网页) | 文本书源→网页订阅源 |
| 1 (音频) | 0 (网页) | 音频书源→网页订阅源（RssSource无音频类型） |
| 2 (图片) | 1 (图片) | 图片书源→图片订阅源 |
| 3 (文件) | 0 (网页) | 文件书源→网页订阅源 |
| 4 (视频) | 2 (视频) | 视频书源→视频订阅源 |

#### 规则映射（优先ExploreRule，其次SearchRule）

| BookSource 规则 | RssSource 规则 | 映射逻辑 |
|----------------|---------------|---------|
| ruleExplore.bookList / ruleSearch.bookList | ruleArticles | 优先ExploreRule |
| ruleExplore.name / ruleSearch.name | ruleTitle | 同上 |
| ruleExplore.bookUrl / ruleSearch.bookUrl | ruleLink | 同上 |
| ruleExplore.coverUrl / ruleSearch.coverUrl | ruleImage | 同上 |
| ruleExplore.intro / ruleSearch.intro | ruleDescription | 同上 |
| ruleContent.content | ruleContent | 直接复制 |
| ruleContent.nextContentUrl | ruleNextContentUrl | ⚠️V7修正：映射到新增字段ruleNextContentUrl（内容分页），非ruleNextPage（列表分页） |
| ruleContent.sourceRegex | ruleSourceRegex | V9新增：WebView资源嗅探→RssSource.ruleSourceRegex |
| ruleContent.imageStyle | ruleImageStyle | V9新增：图片显示样式→RssSource.ruleImageStyle |
| TocRule.nextTocUrl | ruleNextPage | V7新增：目录分页→文章列表分页 |

#### 丢失字段及影响评估

| 丢失字段 | 影响 | Impact |
|---------|------|--------|
| bookUrlPattern | 不影响 | NONE |
| enabledExplore | 不影响 | NONE |
| exploreScreen | 不影响 | NONE |
| ruleToc | 订阅源无目录概念，不影响 | NONE |
| ruleBookInfo | 订阅源无详情页，不影响 | NONE |
| ruleReview | 订阅源无段评，不影响 | NONE |
| ContentRule.subContent | 副文丢失（歌词/弹幕/字幕），对音频/视频源是核心功能 | **MAJOR**(V8已由改动7弥补) |
| ContentRule.title | 正文标题丢失 | MINOR |
| ContentRule.replaceRegex | 正文替换规则丢失，可能含广告 | **MAJOR**(V8已由改动5弥补) |
| ContentRule.imageStyle | 图片样式丢失 | MINOR(V9已由改动12弥补) |
| ContentRule.imageDecode | 图片解密丢失（有coverDecodeJs可部分替代） | MINOR(V8已由改动1弥补) |
| ContentRule.sourceRegex | WebView资源嗅探丢失，音频/视频源核心功能 | **MAJOR**(V9已由改动11弥补) |
| SearchRule/ExploreRule.author | 作者信息丢失 | **MAJOR**(V8已由改动8弥补) |
| SearchRule/ExploreRule.kind | 分类信息丢失 | MINOR |
| SearchRule/ExploreRule.lastChapter | 最新章节丢失 | MINOR |
| SearchRule/ExploreRule.updateTime | 更新时间丢失 | MINOR(RssSource已有rulePubDate可部分替代) |
| SearchRule/ExploreRule.wordCount | 字数丢失 | MINOR |

### 订阅源→书源 (rssSourceToBookSource)

#### 基础字段直接映射（19个字段）

| RssSource | BookSource | 说明 |
|-----------|-----------|------|
| sourceUrl | bookSourceUrl | 直接复制 |
| sourceName | bookSourceName | 直接复制 |
| sourceGroup | bookSourceGroup | 直接复制 |
| sourceComment | bookSourceComment | 直接复制 |
| enabled | enabled | 直接复制 |
| enabledCookieJar | enabledCookieJar | 直接复制 |
| concurrentRate | concurrentRate | 直接复制 |
| header | header | 直接复制 |
| loginUrl | loginUrl | 直接复制 |
| loginUi | loginUi | 直接复制 |
| loginCheckJs | loginCheckJs | 直接复制 |
| coverDecodeJs | coverDecodeJs | 直接复制 |
| variableComment | variableComment | 直接复制 |
| jsLib | jsLib | 直接复制 |
| customOrder | customOrder | 直接复制 |
| weight | weight | 直接复制 |
| lastHost | lastHost | 直接复制 |
| sortUrl | exploreUrl | 直接复制 |
| searchUrl | searchUrl | 直接复制 |

#### 类型映射

| RssSource.type | BookSourceType | 说明 |
|----------------|---------------|------|
| 0 (网页) | 0 (文本) | 网页订阅源→文本书源 |
| 1 (图片) | 2 (图片) | 图片订阅源→图片书源 |
| 2 (视频) | 4 (视频) | 视频订阅源→视频书源 |

#### 规则映射

| RssSource 规则 | BookSource 规则 | 映射逻辑 |
|---------------|----------------|---------|
| ruleArticles | ruleSearch.bookList + ruleExplore.bookList | 双向映射 |
| ruleTitle | ruleSearch.name + ruleExplore.name | 双向映射 |
| ruleLink | ruleSearch.bookUrl + ruleExplore.bookUrl | 双向映射 |
| ruleImage | ruleSearch.coverUrl + ruleExplore.coverUrl | 双向映射 |
| ruleDescription | ruleSearch.intro + ruleExplore.intro | 双向映射 |
| ruleContent | ruleContent.content | 直接复制 |
| ruleNextContentUrl | ruleContent.nextContentUrl | V7新增：内容分页反向映射（改动4反向） |
| ruleSourceRegex | ruleContent.sourceRegex | V9新增：WebView资源嗅探反向映射（改动11反向） |
| ruleImageStyle | ruleContent.imageStyle | V9新增：图片样式反向映射（改动12反向） |
| ruleNextPage | ruleToc.nextTocUrl | V7修正：列表分页→目录分页（非→nextContentUrl） |
| ruleArticles + ruleTitle + ruleLink | ruleToc (智能生成) | **核心改进** |
| ruleTitle + ruleImage + ruleDescription | ruleBookInfo (智能生成) | **V7改动6新增** |

#### 智能TocRule + BookInfoRule联合生成（V7修正）

> **V6→V7 CRITICAL修正**：V6的智能TocRule存在3个致命缺陷：
> 1. TocRule.chapterList = ruleArticles 需要在sortUrl页面上解析，但BookInfo加载后tocUrl默认为articleUrl（文章内容页），导致TocRule在文章内容页上找不到ruleArticles元素
> 2. TocRule缺少nextTocUrl映射，分页目录的文章会丢失
> 3. 没有生成BookInfoRule，导致tocUrl无法指向sortUrl页面
>
> **修复方案**：BookInfoRule.tocUrl通过JS规则指向sortUrl页面，使BookChapterList加载sortUrl页面后再用TocRule解析

**源码级验证**（BookInfo.kt L160-168）：
```kotlin
// BookInfo.kt L163
book.tocUrl = analyzeRule.getString(infoRule.tocUrl, isUrl = true)
if (book.tocUrl.isEmpty()) book.tocUrl = baseUrl  // ← tocUrl为空时=articleUrl！
if (book.tocUrl == baseUrl) {
    book.tocHtml = body  // tocUrl==bookUrl时复用已加载的HTML
}
```
**关键发现**：如果BookInfoRule.tocUrl为空，则tocUrl=baseUrl（articleUrl），BookChapterList会在articleUrl页面上解析TocRule——但articleUrl页面是文章内容页，不含ruleArticles匹配的列表元素！

```kotlin
// V7修正：智能TocRule + BookInfoRule联合生成
// 注意：此方法在SourceConverter（suspend函数）中调用，可使用sortUrls()获取解析后的分类URL列表
private suspend fun generateSmartBookInfoAndToc(rssSource: RssSource): Pair<BookInfoRule, TocRule> {
    val bookInfoRule = BookInfoRule()
    val tocRule = TocRule()

    // ========== BookInfoRule生成 ==========

    // 关键：tocUrl必须指向sortUrl页面，否则TocRule.ruleArticles无法匹配
    // 使用RssSource.sortUrls()扩展方法（RssSourceExtensions.kt L17-52）
    // sortUrls()已处理所有sortUrl格式：
    //   1. "分类1::url1\n分类2::url2" → 拆分name::url对
    //   2. "<js>...</js>" / "@js:..." → 执行JS后解析
    //   3. 空sortUrl → 回退到Pair("", sourceUrl)
    val sortUrlList = rssSource.sortUrls()  // List<Pair<String, String>>
    val firstSortUrlPair = sortUrlList.firstOrNull()
    val tocUrlValue = firstSortUrlPair?.second ?: rssSource.sourceUrl

    if (tocUrlValue.isNotEmpty()) {
        // 使用@js:规则返回sortUrl，AnalyzeRule.getString()会执行JS并返回URL字符串
        // 源码验证：AnalyzeRule.splitSourceRule() L552-580 正确识别@js:前缀并创建Mode.Js规则
        // AnalyzeRule.getString() L339 在Mode.Js时调用evalJS()执行JS代码
        // isUrl=true参数确保返回的字符串被处理为绝对URL
        val escapedUrl = tocUrlValue.replace("'", "\\'")
        bookInfoRule.tocUrl = "@js:'$escapedUrl'"
    }

    // BookInfoRule其他字段映射（从当前articleUrl页面解析）
    // 注意：ruleTitle/ruleImage/ruleDescription是设计在sortUrl页面上工作的选择器
    // 在articleUrl页面上可能无法正确匹配（非致命，搜索结果中已包含这些信息）
    bookInfoRule.name = rssSource.ruleTitle      // 文章标题→书名（可能不匹配，非致命）
    bookInfoRule.coverUrl = rssSource.ruleImage   // 文章图片→封面（可能不匹配，非致命）
    bookInfoRule.intro = rssSource.ruleDescription // 文章描述→简介（可能不匹配，非致命）

    // ========== TocRule生成 ==========

    // chapterList = ruleArticles（在sortUrl页面上解析文章列表）
    tocRule.chapterList = rssSource.ruleArticles
    // chapterName = ruleTitle
    tocRule.chapterName = rssSource.ruleTitle
    // chapterUrl = ruleLink
    tocRule.chapterUrl = rssSource.ruleLink
    // V7关键修正：nextTocUrl = ruleNextPage（目录分页=文章列表分页）
    tocRule.nextTocUrl = rssSource.ruleNextPage

    return Pair(bookInfoRule, tocRule)
}
```

**源码铁证**：
- `RssSourceExtensions.kt` L17-52：`sortUrls()` 方法完整处理所有sortUrl格式（含JS动态生成、name::url对、空sortUrl回退）
- `AnalyzeRule.kt` L552-560：`splitSourceRule()` 正确识别`@js:`前缀并创建`Mode.Js`规则
- `AnalyzeRule.kt` L339：`getString()` 在`Mode.Js`时调用`evalJS()`执行JS代码
- `BookInfo.kt` L163：`book.tocUrl = analyzeRule.getString(infoRule.tocUrl, isUrl = true)` 正确处理JS规则返回的URL

#### 丢失字段及影响评估

| 丢失字段 | 影响 | Impact |
|---------|------|--------|
| sourceIcon | 无图标，不影响功能 | NONE |
| singleUrl | 不影响 | NONE |
| articleStyle | 不影响 | NONE |
| rulePubDate | 书源无发布日期 | MINOR(可用BookInfoRule.updateTime替代) |
| ruleRoutes | 视频多线路丢失 | **CRITICAL**(视频，V8已由改动2弥补) |
| ruleEpisodes | 视频多集丢失 | **CRITICAL**(视频，V8已由改动2弥补) |
| contentWhitelist | 正文URL白名单丢失 | **MAJOR**(V8:由改动9弥补，影响内容质量) |
| contentBlacklist | 正文URL黑名单丢失 | **MAJOR**(V8:由改动9弥补，影响内容质量) |
| shouldOverrideUrlLoading | URL拦截丢失 | MINOR(部分可由jsLib替代) |
| style/injectJs/preloadJs等 | WebView相关丢失 | MAJOR(架构限制，webJs改动3弥补最关键场景) |
| startHtml/startStyle/startJs | 起始页丢失 | MINOR |
| showWebLog | 不影响 | NONE |
| preload | 不影响 | NONE |
| cacheFirst | 不影响 | NONE |
| parseConcurrency | 不影响 | NONE |

## UI Design（V6完善版）

### 入口设计

基于现有UI结构分析，互转功能在4个位置提供入口：

| 入口位置 | 文件 | 菜单项 | 触发方式 |
|---------|------|--------|---------|
| 书源单项菜单 | `book_source_item.xml` | "转为订阅源" | 长按书源→弹出菜单 |
| 订阅源单项菜单 | `rss_source_item.xml` | "转为书源" | 长按订阅源→弹出菜单 |
| 书源批量菜单 | `book_source_sel.xml` | "转为订阅源" | 多选书源→选择操作栏菜单 |
| 订阅源批量菜单 | `rss_source_sel.xml` | "转为书源" | 多选订阅源→选择操作栏菜单 |

**入口设计理由**：
- 长按菜单是最自然的操作位置（用户已有"删除""调试""登录"等操作习惯）
- 批量操作支持多选互转（用户可能想一次转多个源）
- 不在编辑页面添加（编辑页是修改当前源，互转是创建新源，语义不同）

### 转换预览对话框设计（SourceConvertDialog）

**对话框布局**：
```
┌─────────────────────────────────┐
│  转换预览：书源→订阅源           │
├─────────────────────────────────┤
│  可用性：★★★★★ (绿色)          │
│                                 │
│  ✅ 可直接映射 (12个字段)        │
│    sourceUrl/sourceName/...     │
│                                 │
│  ✅ 已通过源码改动弥补 (5个字段)  │
│    imageDecode → RssSource.imageDecode    │
│    nextContentUrl → RssSource.ruleNextContentUrl │
│    replaceRegex → RssSource.ruleReplaceRegex     │
│    webJs → RssSource.ruleWebJs             │
│    routeRule → (仅视频源)                   │
│                                 │
│  ⚠️ 不影响功能 (3个字段)         │
│    TocRule/BookInfoRule/ReviewRule │
│    (订阅源不需要这些功能)        │
│                                 │
│  新源名称：[XXX(订阅版)]         │
├─────────────────────────────────┤
│    [取消]    [确认转换]           │
└─────────────────────────────────┘
```

**可用性等级颜色标记**：
- ★★★★★：绿色"可用性：高，功能完整"
- ★★★★☆：浅绿色"可用性：较高，少量功能需手动补充"
- ★★★☆☆：黄色"可用性：中，部分功能需手动补充"
- ★★☆☆☆及以下：红色"可用性：低，核心功能缺失"

**关键交互**：
1. 转换前必须展示预览对话框（不允许直接转换）
2. V6版所有6个方向都是★★★★★，不会出现低可用性
3. 转换后不删除原源，新源名称自动加"(订阅版)"/"(书源版)"后缀
4. 转换成功后Toast提示+提供"编辑源"按钮跳转编辑页面

### 批量转换设计

多选源后批量转换时：
1. 逐个执行SourceConverter.convert()
2. 汇总转换结果：成功N个/失败M个
3. 失败的源展示具体原因（如"缺少必要字段"）
4. 成功的源直接写入数据库

## Data Flow

### 单项转换流程

```
用户长按源 → 选择"转为X源"
  → SourceConverter.convert()
  → 字段映射（直接映射+源码改动映射+智能TocRule）
  → 评估可用性(★★★★★)
  → SourceConvertDialog 展示预览+映射详情+可用性
  → 用户确认 → appDb.xxxDao().insert(target)
  → Toast提示"转换成功" + "编辑源"按钮
```

### 批量转换流程

```
用户多选源 → 选择"批量转为X源"
  → 遍历选中源，逐个SourceConverter.convert()
  → 收集ConvertResult列表
  → 展示汇总结果（成功N个/失败M个+失败原因）
  → 用户确认 → appDb.xxxDao().insert(vararg targets)
  → Snackbar "成功转换N个源"
```

## File Change List（V6版）

### UI层（新增/修改）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `data/entities/SourceConverter.kt` | 新增 | 转换器核心+可用性评估+智能TocRule |
| `ui/source/SourceConvertDialog.kt` | 新增 | 转换预览对话框（含映射详情+可用性显示） |
| `res/layout/dialog_source_convert.xml` | 新增 | 对话框布局 |
| `res/menu/book_source_item.xml` | 修改 | 添加"转为订阅源"菜单项 |
| `res/menu/rss_source_item.xml` | 修改 | 添加"转为书源"菜单项 |
| `res/menu/book_source_sel.xml` | 修改 | 添加批量"转为订阅源"菜单项 |
| `res/menu/rss_source_sel.xml` | 修改 | 添加批量"转为书源"菜单项 |
| `ui/book/source/manage/BookSourceAdapter.kt` | 修改 | 添加菜单点击处理 |
| `ui/rss/source/manage/RssSourceAdapter.kt` | 修改 | 添加菜单点击处理 |
| `ui/book/source/manage/BookSourceActivity.kt` | 修改 | 批量转换处理 |
| `ui/rss/source/manage/RssSourceActivity.kt` | 修改 | 批量转换处理 |
| `res/values/strings.xml` | 修改 | 字符串资源（转订阅源/转书源/转换预览等） |

### 源码改动层（5个改动，不影响现有功能）

| 文件 | 改动 | 对应改动 |
|------|------|---------|
| `data/entities/RssSource.kt` | 新增4个字段：imageDecode/ruleWebJs/ruleNextContentUrl/ruleReplaceRegex | 改动1/3/4/5 |
| `data/entities/rule/ContentRule.kt` | 新增2个字段：routeRule/routeContentRule | 改动2 |
| `utils/ImageUtils.kt` | getRuleJs() RssSource分支支持imageDecode | 改动1 |
| `model/rss/Rss.kt` | getContentAwait()传jsStr参数+分页循环+替换步骤 | 改动3/4/5 |
| `model/VideoPlay.kt` | startPlay() BookSource分支routeRule多线路 | 改动2 |
| `data/DatabaseMigrations.kt` | 新增MIGRATION_101_105（4列一次性添加） | 改动1/3/4/5 |
| `data/AppDatabase.kt` | version 101→105 | 改动1/3/4/5 |

## 关键改进：JS库弥补转换丢失功能（V3新增，V6部分过时）

> **V6更新**：改动5（ruleReplaceRegex）已在Rss.kt中直接支持replaceRegex运行时执行，**不再需要**将replaceRegex编码为jsLib中的JS函数。JS弥补方案仅作为复杂replaceRegex（含`@js:`标签）的备选方案保留。
>
> **源码级验证结论**：通过自定义JS库弥补转换后丢失的功能是**可行的**。核心依据：`AnalyzeRule.getString()` 支持 `<js>` 和 `@js:` 标签，`ruleContent` 可以包含 JS 代码；`BaseSource.jsLib` 字段定义的 JS 函数可通过 `SharedJsScope` 在所有规则执行中共享。

### 源码验证铁证

1. **RssSource.ruleContent 支持 `<js>` 标签**：
   - `Rss.kt` L181：`val content = analyzeRule.getString(ruleContent)` — 通过 AnalyzeRule 解析
   - `AnalyzeRule.getString()` 识别 `<js>` / `@js:` 标签并调用 `evalJS()` 执行
   - 这意味着 ruleContent 可以从简单 CSS/XPath 规则变为 `<js>functionCall(result)</js>`

2. **jsLib 机制提供函数共享**：
   - `BaseSource.kt` L62：`var jsLib: String?` — 存储可复用的 JS 函数库
   - `SharedJsScope.kt` L30-80：加载 jsLib 创建共享 Scriptable scope
   - `BaseSource.evalJS()` L327-345：绑定 `java`/`source`/`baseUrl`/`cookie`/`cache` 等，并获取 jsLib 的共享 scope 作为 prototype

3. **BookSource.replaceRegex 处理流程**：
   - `BookContent.kt` L168-175：先提取正文内容，再对内容应用 replaceRegex
   - `AnalyzeRule.replaceRegex()` L494：处理 `##regex##replacement##` 语法的多步替换
   - replaceRegex 支持多规则组合（`&&` 分隔）和替换首个（`###` 三井号）

### 方案1：replaceRegex 弥补（书源→订阅源）

**问题**：文本书源转订阅源时，ContentRule.replaceRegex 丢失导致正文含广告。

**解决方案**：将 replaceRegex 编码为 jsLib 中的函数，ruleContent 改用 JS 调用。

**实现步骤**：

```kotlin
// 在 SourceConverter.bookSourceToRssSource() 中
val contentRule = bookSource.getContentRule()

if (!contentRule.replaceRegex.isNullOrEmpty()) {
    // 步骤1：解析 replaceRegex 为正则对列表
    val regexPairs = parseReplaceRegex(contentRule.replaceRegex)
    // regexPairs: List<Pair<String, String>> = [(pattern, replacement), ...]

    // 步骤2：生成 JS 清理函数
    val jsFunction = buildString {
        appendLine("function cleanContent(content) {")
        for ((pattern, replacement) in regexPairs) {
            // 转义正则中的特殊字符，生成等效 JS replace
            appendLine("  content = content.replace(/$pattern/g, '${escapeJs(replacement)}');")
        }
        appendLine("  return content;")
        append("}")
    }

    // 步骤3：追加到目标源的 jsLib
    val existingJsLib = rssSource.jsLib ?: ""
    rssSource.jsLib = if (existingJsLib.isBlank()) {
        jsFunction
    } else {
        "$existingJsLib\n$jsFunction"
    }

    // 步骤4：修改 ruleContent 为 JS 调用
    val originalContentRule = contentRule.content ?: ""
    rssSource.ruleContent = "<js>var raw = '$originalContentRule'; var r = source.getString(raw, result); cleanContent(r);</js>"
    // 注意：实际的JS调用需要先执行原始content规则获取正文，再调用cleanContent清理
    // 更精确的写法：
    // ruleContent = "@js:var r=java.getString('${escapeJs(originalContentRule)}',result);cleanContent(r)"
}
```

**更精确的实现**（利用 AnalyzeRule 的链式规则语法）：

```kotlin
// 利用 AnalyzeRule 的规则链：先执行原始content规则，再执行JS清理
// 规则链语法：rule1 && rule2（但这是多规则取并集，不是链式处理）
// 正确方案：直接在 ruleContent 中用 <js> 包裹
if (!contentRule.replaceRegex.isNullOrEmpty()) {
    val regexPairs = parseReplaceRegex(contentRule.replaceRegex)
    val jsLibCode = buildJsCleanFunction(regexPairs)

    // 追加到 jsLib
    rssSource.jsLib = (rssSource.jsLib ?: "") + "\n" + jsLibCode

    // ruleContent 改为：先按原始规则提取内容，再用JS清理
    // 这里利用 AnalyzeRule 的特性：JS规则中可以调用 source.evalJS()
    rssSource.ruleContent = "<js>cleanContent(java.getString('${escapeJs(contentRule.content)}',result))</js>"
}
```

**限制**：
- replaceRegex 中的正则语法需从 Java Pattern 转换为 JavaScript RegExp（大部分兼容，少数不兼容如 `\G`、占有量词等）
- 替换字符串中的反向引用 `$1` 需转为 JS 的 `$1`（语法兼容）
- 复杂的 replaceRegex（含 `@js:` 内嵌JS）无法自动转换，需提示用户手动处理

### 方案2：imageDecode 弥补（图片书源→订阅源）

**问题**：图片书源有 ContentRule.imageDecode（图片解密JS），转订阅源后丢失。

**解决方案**：将 imageDecode 移入 jsLib，在 ruleContent 中调用。

```kotlin
if (!contentRule.imageDecode.isNullOrEmpty()) {
    // imageDecode 本身就是 JS 代码，可直接移入 jsLib
    val imageDecodeJs = contentRule.imageDecode
    val jsLibCode = """
function decodeImage(content) {
    // imageDecode 原始逻辑
    $imageDecodeJs
}
    """.trimIndent()

    rssSource.jsLib = (rssSource.jsLib ?: "") + "\n" + jsLibCode
    // ruleContent 保持不变（图片URL的解密在图片加载时而非内容提取时触发）
    // 注意：imageDecode 是在 BookHelp.saveImage() 中通过 evalJS 执行的
    // RssSource 没有对应的 imageDecode 字段，所以这个弥补实际不可行
}
```

**结论**：imageDecode 弥补**不可行**。原因：
- imageDecode 在 `BookHelp.saveImage()` 中通过 `source.evalJS(imageDecode, bytes)` 执行，输入是图片 bytes
- RssSource 没有 imageDecode 字段，也没有在图片保存流程中调用任何解密逻辑
- 即使把解密代码放入 jsLib，RssSource 的图片加载流程也不会调用它
- 这是 RssSource 解析引擎的架构限制，非 JS 库能解决

### 方案3：视频多线路弥补（订阅源→书源）

**问题**：视频订阅源的多线路/ruleEpisodes 无法映射到书源。

**分析**：BookSource 的 TocRule 只有一套章节列表，没有"线路"概念。

**JS弥补可行性**：**不可行**。

原因：
1. **数据结构根本限制**：TocRule 的 `chapterList/chapterName/chapterUrl` 是扁平列表，无法表示"多套章节"
2. **UI层限制**：书源阅读界面（ReadBookActivity）没有线路选择的UI组件
3. **JS无法突破数据结构**：即使通过JS动态生成章节列表，也只能生成一套，无法实现"切换线路"
4. `{routeIndex}` 占位符在 BookSource 的规则引擎中不存在

**最佳妥协方案**：仅用第一线路生成 TocRule。

```kotlin
// 视频订阅源→书源时的单线路TocRule生成
if (rssSource.type == 2 && !rssSource.ruleEpisodes.isNullOrEmpty()) {
    // 使用 ruleEpisodes（单线路，routeIndex=0）生成 TocRule
    // 注意：ruleEpisodes 可能包含 {routeIndex} 占位符
    val episodesRule = rssSource.ruleEpisodes!!.replace("{routeIndex}", "0")
    tocRule = TocRule().apply {
        chapterList = episodesRule  // 用集数规则替代文章列表
        chapterName = rssSource.ruleTitle ?: ""
        chapterUrl = rssSource.ruleLink ?: ""
    }
}
```

### 方案4：智能TocRule增强（订阅源→书源，JS动态目录）

**问题**：智能TocRule生成的目录可能不够精确（如分页目录、需要JS动态获取的目录）。

**解决方案**：利用 jsLib + `<js>` 在 TocRule.chapterList 中使用 JS 动态生成目录。

```kotlin
// 当订阅源有 sortUrl 分页时，生成JS增强版TocRule
if (!rssSource.sortUrl.isNullOrBlank() && rssSource.ruleNextPage.isNullOrBlank().not()) {
    // 有分页的订阅源，目录需要翻页获取
    val jsLibCode = """
function fetchChapterList() {
    var chapters = [];
    var page = 1;
    var maxPages = 50;  // 安全限制
    while (page <= maxPages) {
        var url = '${sortUrlPattern}'.replace('{page}', page);
        var html = java.ajax(url);
        var doc = java.parse(html);
        var items = doc.select('${rssSource.ruleArticles}');
        for (var i = 0; i < items.size(); i++) {
            var item = items.get(i);
            chapters.push({
                name: item.select('${rssSource.ruleTitle}').text(),
                url: item.select('${rssSource.ruleLink}').attr('href')
            });
        }
        var nextBtn = doc.select('${rssSource.ruleNextPage}');
        if (!nextBtn || nextBtn.size() === 0) break;
        page++;
    }
    return JSON.stringify(chapters);
}
    """.trimIndent()

    rssSource.jsLib = (rssSource.jsLib ?: "") + "\n" + jsLibCode
    // 但这里有个问题：TocRule.chapterList 不支持 <js> 标签
    // BookChapterList 使用 AnalyzeRule.getElements(tocRule.chapterList)
    // 而 AnalyzeRule.getElements() 也支持 JS 模式
    // 所以理论上可以：tocRule.chapterList = "<js>fetchChapterList()</js>"
}
```

**限制**：
- 未验证 `AnalyzeRule.getElements()` 是否正确处理 JS 返回的 JSON 数组
- JS 中的 `java.ajax()` 调用有网络延迟，可能导致目录加载缓慢
- 安全限制需要防止无限循环

### JS库弥补方案总结

| 丢失功能 | 弥补可行性 | 实现方式 | 限制 |
|---------|----------|---------|------|
| ContentRule.replaceRegex | ✅ **可行** | jsLib定义cleanContent函数+ruleContent改用`<js>`调用 | Java正则→JS正则兼容性，复杂replaceRegex需手动处理 |
| ContentRule.imageDecode | ❌ **不可行** | - | RssSource图片加载流程不调用imageDecode，架构限制 |
| ContentRule.imageStyle | ❌ **不可行** | - | RssSource无imageStyle字段，UI层不支持 |
| ruleRoutes/ruleEpisodes | ❌ **不可行** | - | BookSource数据结构无"线路"概念，JS无法突破 |
| ContentRule.subContent | ⚠️ **部分可行** | jsLib定义appendSub函数 | 需验证AnalyzeRule对多段拼接的支持 |
| ContentRule.webJs | ❌ **不可行** | - | RssSource正文不经过WebView，webJs无法注入 |

### 更新后的可用性总结（V3版，含JS弥补）

| 方向 | V2可用性 | V3可用性 | JS弥补改进 |
|------|---------|---------|-----------|
| 书源→订阅源(文本) | ★★★★☆ | ★★★★☆→★★★★★ | replaceRegex编码为JS函数，正文清洁度恢复 |
| 书源→订阅源(图片) | ★★★★☆ | ★★★★☆ | imageDecode不可弥补（架构限制），图片查看仍可用 |
| 书源→订阅源(视频) | ★★★☆☆ | ★★★☆☆ | 无改进（多线路不可弥补） |
| 订阅源→书源(文本) | ★★★★☆ | ★★★★☆ | 智能TocRule已足够，JS增强仅用于分页目录 |
| 订阅源→书源(图片) | ★★★★☆ | ★★★★☆ | 同上 |
| 订阅源→书源(视频) | ★★☆☆☆ | ★★☆☆☆ | 多线路不可弥补（BookSource根本限制） |

---

## 100%互转方案：源码改动设计（V5 - 深度源码核实版）

> **核心原则**：所有改动必须向后兼容，不影响现有书源和订阅源的正常使用。新增字段默认null，现有源不受影响。
>
> **V5关键修正**：原V4设计对webJs运行时流程理解有误——书源的webJs不是"WebView注入JS"，而是通过`AnalyzeUrl.getStrResponseAwait(jsStr=webJs)`传递给`BackstageWebView`执行的后台WebView JS。因此RssSource支持webJs的改动从"新增WebView分支"大幅简化为"在getContentAwait()中传jsStr参数"。

### 源码深度核实结论

| 核实项 | V5假设 | V6核实结果 | 影响 |
|--------|--------|-----------|------|
| webJs运行机制 | WebView注入JS | `AnalyzeUrl.jsStr`→`BackstageWebView.javaScript` | 改动3从4-5文件降至2文件 |
| 数据库版本 | 110 | 101 | migration编号需从102起 |
| ContentRoute完整字段 | 未列出 | 10个字段(content/subContent/title/nextContentUrl/webJs/sourceRegex/replaceRegex/imageStyle/imageDecode/payAction/callBackJs) | routeRule插入位置明确 |
| RssRoute结构 | 仅name+episodes | name:String + episodes:List\<RssEpisode\> | 确认BookSource多线路需构造RssRoute(name, episodes) |
| Rss.getContentAwait()调用链 | 未分析 | AnalyzeUrl→getStrResponseAwait()→BackstageWebView(jsStr) | webJs支持仅需1行改动 |
| **Rss.getContentAwait()无replaceRegex** | 未发现 | **CRITICAL：Rss.kt只做`analyzeRule.getString(ruleContent)`，不执行replaceRegex！** | **书源→订阅源去广告/格式化完全丢失** |
| **Rss.getContentAwait()无nextContentUrl** | 未发现 | **CRITICAL：Rss.kt没有分页循环！BookContent L73-101有完整分页逻辑** | **书源→订阅源长文章只获取第一页** |

### 运行时行为差异矩阵

> **核心发现**：之前只分析"字段能否映射"，忽略了更根本的问题——即使字段映射成功，运行时引擎是否支持执行。

| 运行时能力 | BookContent (书源) | Rss.getContentAwait (订阅源) | 差异 | 严重度 |
|-----------|-------------------|--------------------------|------|--------|
| 获取内容 | `analyzeRule.getString(contentRule.content)` | `analyzeRule.getString(ruleContent)` | 等价 | - |
| 内容分页 | ✅ nextContentUrl循环(L73-101) | ❌ 无分页 | **长文章丢失后续页** | **CRITICAL** |
| 内容替换 | ✅ replaceRegex(L168-175) | ❌ 无替换步骤 | **去广告/格式化丢失** | **CRITICAL** |
| WebView加载 | ✅ jsStr→BackstageWebView | ❌ 未传jsStr | 需WebView内容不可用 | MAJOR |
| 图片解密 | ✅ ContentRule.imageDecode | ❌ RssSource无此字段 | 加密图片无法显示 | MAJOR |
| 副内容 | ✅ subContent(L128-165) | ❌ 无副内容 | 音频歌词/视频弹幕丢失 | MINOR |
| 内容标题 | ✅ title(L176-199) | ❌ 无标题更新 | 章节标题不更新 | MINOR |
| 图片样式 | ✅ imageStyle | ❌ 无样式控制 | 图片显示不全 | MINOR |

**结论**：CRITICAL级别的2个缺失（分页+替换）必须在Rss.kt中增加运行时支持，否则书源→订阅源转换后文本书源的长文章和去广告功能完全不可用。

### 改动1：RssSource支持imageDecode（书源→订阅源图片解密）

**问题根因**：`ImageUtils.getRuleJs()` 对 RssSource 只返回 coverDecodeJs，不检查内容图片解密。

**当前代码**（ImageUtils.kt L110-121）：
```kotlin
private fun getRuleJs(source: BaseSource?, isCover: Boolean): String? {
    return when (source) {
        is BookSource ->
            if (isCover) source.coverDecodeJs
            else source.getContentRule().imageDecode
        is RssSource -> source.coverDecodeJs  // ← 只支持封面解密！
        else -> null
    }
}
```

**改动方案**：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var imageDecode: String? = null` 字段（在coverDecodeJs之后） | 新字段默认null，现有RssSource不受影响 |
| `ImageUtils.kt` | RssSource分支改为：`if (isCover) source.coverDecodeJs else source.imageDecode` | imageDecode为null→getRuleJs返回null→跳过解密→行为不变 |
| `DatabaseMigrations.kt` | 新增 MIGRATION_101_102 添加 `rssSources` 表的 `imageDecode` 列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 从 101 改为 102 | 同步版本号 |

**转换逻辑更新**：
```kotlin
// SourceConverter.bookSourceToRssSource() 中新增：
if (!contentRule.imageDecode.isNullOrEmpty()) {
    rssSource.imageDecode = contentRule.imageDecode  // 直接复制JS代码
}
```

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource的imageDecode为null
- ImageUtils.getRuleJs()返回null时跳过解密，与当前行为完全一致
- 数据库migration只添加列不修改数据，覆盖安装安全

### 改动2：BookSource支持视频多线路（订阅源→书源视频多线路）

**问题根因**：BookSource视频播放只有单套TocRule章节列表，无"线路"概念。视频播放器对RssSource已有多线路支持（rssRoutes/rssRouteIndex），但对BookSource没有。

**ContentRule当前完整字段**（ContentRule.kt）：
```kotlin
data class ContentRule(
    var content: String? = null,
    var subContent: String? = null,
    var title: String? = null,
    var nextContentUrl: String? = null,
    var webJs: String? = null,
    var sourceRegex: String? = null,
    var replaceRegex: String? = null,
    var imageStyle: String? = null,
    var imageDecode: String? = null,
    var payAction: String? = null,
    var callBackJs: String? = null
)
```

**改动方案**：在ContentRule中新增`routeRule`字段。

| 文件 | 改动 | 影响 |
|------|------|------|
| `ContentRule.kt` | 新增 `var routeRule: String? = null` 字段（在callBackJs之后） | 新字段默认null，JSON反序列化时自动忽略 |
| `VideoPlay.kt` | startPlay() BookSource分支：routeRule非空时解析线路列表赋值rssRoutes | routeRule为null→不走多线路→行为不变 |
| `VideoPlayerActivity.kt` | 无需改动（已有多线路选择UI，基于rssRoutes/rssRouteIndex） | 现有RssSource多线路不受影响 |

**VideoPlay.kt 改动详细**：
```kotlin
// VideoPlay.kt startPlay() BookSource视频播放分支
// 在获取contentRule之后、WebBook.getContent之前插入：
if (s.bookSourceType == BookSourceType.video && !contentRule.routeRule.isNullOrBlank()) {
    // V5: 从当前页面解析线路列表
    // 用AnalyzeRule解析routeRule获取线路名列表
    // 每个线路的集数列表在切换时由TocRule + 章节过滤实现
    val analyzeRule = AnalyzeRule(book, s)
    val routeNames = analyzeRule.getStringList(contentRule.routeRule)
    if (routeNames.isNotEmpty()) {
        rssRoutes = routeNames.mapIndexed { index, name ->
            // 每个线路的episodes在switchToRoute时按需采集
            RssRoute(name, emptyList())
        }
        rssRouteIndex = 0
    }
}
```

**注意**：BookSource视频多线路与RssSource多线路有本质区别：
- RssSource：ruleEpisodes按{routeIndex}采集不同线路的集数列表
- BookSource：TocRule只有一套章节列表，多线路意味着**同一章节有多个播放源**
- 因此routeRule解析出的线路列表，每个线路的"集数"就是TocRule的章节列表，只是播放URL不同
- 需要在ContentRule中再新增`routeEpisodeRule`字段，或利用jsLib动态生成

**简化方案（推荐）**：routeRule仅解析线路名列表，切换线路时重新用WebBook.getContent获取当前章节的播放URL（不同线路=不同的content解析规则）。这需要routeRule配合routeContentRule（新字段），指定不同线路的内容解析规则。

**最终方案评估**：

| 方案 | 新增字段 | 改动量 | 功能完整度 |
|------|---------|--------|-----------|
| 方案A：routeRule+routeContentRule | 2个字段 | ContentRule+VideoPlay | 100%多线路 |
| 方案B：routeRule仅线路名 | 1个字段 | ContentRule+VideoPlay | 切换线路=重新getContent |
| 方案C：routeRule+jsLib配合 | 1个字段+jsLib约定 | ContentRule+VideoPlay | 100%多线路（通过JS） |

**推荐方案A**，最清晰完整。

**不影响现有功能保证**：
- ContentRule新增字段默认null，所有现有BookSource不受影响
- VideoPlay中`contentRule.routeRule.isNullOrBlank()`为true→不走多线路→行为不变
- RssSource多线路逻辑完全独立，不受影响

### 改动3：RssSource支持webJs（书源→订阅源WebView注入）⚠️ V5大幅简化

**V4设计问题**：原设计误认为webJs是"WebView注入JS"，需要在Rss.kt中新增WebView分支。实际源码核实发现：

**书源webJs的真实运行时流程**：
```
BookContent.kt L89:
  analyzeUrl.getStrResponseAwait(jsStr = webJs)
    → AnalyzeUrl.executeStrRequest(jsStr=webJs)
      → BackstageWebView(javaScript = webJs ?: jsStr).getStrResponse()
        → 后台WebView加载页面 + 执行JS + 返回结果
```

**RssSource当前内容获取流程**：
```
Rss.kt L149:
  analyzeUrl.getStrResponseAwait()  // ← 没有传jsStr参数！
```

**改动方案（V5简化版）**：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleWebJs: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `Rss.kt` | getContentAwait() L149改为：`analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs)` | ruleWebJs为null→jsStr=null→走原路径→行为不变 |
| `DatabaseMigrations.kt` | 新增 migration 添加 `rssSources` 表的 `ruleWebJs` 列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 递增 | 同步版本号 |

**核心改动只有1行代码！** 从`analyzeUrl.getStrResponseAwait()`改为`analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs)`。

**V4 vs V5 改动量对比**：

| 项目 | V4设计 | V5设计 | 差异 |
|------|--------|--------|------|
| 新增字段 | ruleWebJs | ruleWebJs | 相同 |
| Rss.kt改动 | 新增WebView分支(20+行) | 1行参数传递 | **-95%代码量** |
| WebView工具类 | 需新建/复用 | 不需要（复用BackstageWebView） | 无需改动 |
| 内存/生命周期风险 | 高（WebView实例管理） | 无（BackstageWebView已管理） | **风险消除** |
| 改动文件数 | 4-5 | 4 | -1文件 |

**不影响现有功能保证**：
- ruleWebJs默认null，`getStrResponseAwait(jsStr=null)`等价于`getStrResponseAwait()`→行为完全不变
- BackstageWebView已有完善的WebView生命周期管理（WebViewPool复用+超时释放）
- 切换线路/退出时BackstageWebView随协程取消自动清理

### 改动4：RssSource支持内容分页（书源→订阅源nextContentUrl）⚠️ V6新增CRITICAL

**问题根因**：`Rss.getContentAwait()` 只做一次 `analyzeRule.getString(ruleContent)` 获取内容，不支持分页。而 `BookContent.analyzeContent()` L73-101 有完整的 nextContentUrl 分页循环，能获取长文章的所有页面。

**当前代码**（Rss.kt L176-183）：
```kotlin
val content = analyzeRule.getString(ruleContent)  // ← 只获取一次！
return content
```

**书源分页逻辑**（BookContent.kt L73-101）：
```kotlin
while (nextUrl.isNotEmpty() && !nextUrlList.contains(nextUrl)) {
    // 获取下一页 → 解析内容 → 添加到contentList
    val analyzeUrl = AnalyzeUrl(mUrl = nextUrl, source = bookSource, ...)
    val res = analyzeUrl.getStrResponseAwait(jsStr = webJs)
    contentData = analyzeContent(book, nextUrl, res.url, nextBody, contentRule, ...)
    contentList.add(contentData.first)
}
```

**改动方案**：为RssSource新增 `ruleNextContentUrl` 字段，并在 `getContentAwait()` 中增加分页循环。

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleNextContentUrl: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `Rss.kt` | getContentAwait()中：ruleNextContentUrl非空时增加分页循环 | ruleNextContentUrl为null→走原路径→行为不变 |
| `DatabaseMigrations.kt` | 新增 migration 添加列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 递增 | 同步版本号 |

**Rss.kt 改动详细**（在`val content = analyzeRule.getString(ruleContent)`之后插入）：
```kotlin
val content = analyzeRule.getString(ruleContent)
// V6改动4：内容分页支持（对应书源ContentRule.nextContentUrl）
val nextContentUrlRule = rssSource.ruleNextContentUrl
val contentList = arrayListOf(content)
if (!nextContentUrlRule.isNullOrBlank()) {
    var nextUrlList = arrayListOf(rssArticle.link ?: "")
    val nextUrls = analyzeRule.getStringList(nextContentUrlRule, isUrl = true)
    if (nextUrls != null && nextUrls.size == 1) {
        var nextUrl = nextUrls[0]
        while (nextUrl.isNotEmpty() && !nextUrlList.contains(nextUrl)) {
            nextUrlList.add(nextUrl)
            val nextAnalyzeUrl = AnalyzeUrl(
                nextUrl,
                baseUrl = rssArticle.origin,
                source = rssSource,
                ruleData = rssArticle,
                coroutineContext = currentCoroutineContext()
            )
            val nextRes = nextAnalyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs)
            val nextAnalyzeRule = AnalyzeRule(rssArticle, rssSource)
            nextAnalyzeRule.setContent(nextRes.body)
                .setBaseUrl(NetworkUtils.getAbsoluteURL(rssArticle.origin, nextUrl))
                .setCoroutineContext(currentCoroutineContext())
                .setRedirectUrl(nextRes.url)
            val nextContent = nextAnalyzeRule.getString(ruleContent)
            contentList.add(nextContent)
            val moreUrls = nextAnalyzeRule.getStringList(nextContentUrlRule, isUrl = true)
            nextUrl = if (moreUrls != null && moreUrls.isNotEmpty()) moreUrls[0] else ""
        }
    }
}
return contentList.joinToString("\n")
```

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource的ruleNextContentUrl为null
- ruleNextContentUrl为null时不进入分页循环，与当前行为完全一致
- 分页循环逻辑对齐BookContent.kt的实现，确保一致性

### 改动5：RssSource支持内容替换（书源→订阅源replaceRegex）⚠️ V6新增CRITICAL

**问题根因**：`Rss.getContentAwait()` 获取内容后直接返回，不执行任何替换操作。而 `BookContent.analyzeContent()` L168-175 对最终内容执行 replaceRegex 替换（去广告/格式化），这是文本书源的核心功能。

**当前代码**（Rss.kt L181-183）：
```kotlin
val content = analyzeRule.getString(ruleContent)
return content  // ← 直接返回，不执行replaceRegex！
```

**书源替换逻辑**（BookContent.kt L168-175）：
```kotlin
val replaceRegex = contentRule.replaceRegex
if (!replaceRegex.isNullOrEmpty()) {
    contentStr = contentStr.split(AppPattern.LFRegex).joinToString("\n") { it.trim() }
    contentStr = analyzeRule.getString(replaceRegex, contentStr)
}
```

**改动方案**：为RssSource新增 `ruleReplaceRegex` 字段，并在 `getContentAwait()` 返回前执行替换。

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleReplaceRegex: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `Rss.kt` | getContentAwait()中：ruleReplaceRegex非空时在返回前执行替换 | ruleReplaceRegex为null→跳过替换→行为不变 |
| `DatabaseMigrations.kt` | 新增 migration 添加列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 递增 | 同步版本号 |

**Rss.kt 改动详细**（在return content之前插入）：
```kotlin
var finalContent = contentList.joinToString("\n")  // 改动4的分页结果
// V6改动5：内容替换支持（对应书源ContentRule.replaceRegex）
val replaceRegex = rssSource.ruleReplaceRegex
if (!replaceRegex.isNullOrBlank()) {
    finalContent = finalContent.split(AppPattern.LFRegex).joinToString("\n") { it.trim() }
    finalContent = analyzeRule.getString(replaceRegex, finalContent)
}
return finalContent
```

**不需要JS弥补方案了**！之前V3的JS弥补方案是把replaceRegex编码为jsLib中的函数，在ruleContent中用`<js>`调用。但那个方案有3个问题：
1. 修改了ruleContent的语义（从纯规则变成规则+JS调用），可能与AnalyzeRule解析冲突
2. 复杂replaceRegex（如含`@js:`的）无法自动转换为JS函数
3. jsLib追加可能与现有jsLib冲突

改动5直接在Rss.kt中增加replaceRegex执行步骤，完全复用BookContent.kt的替换逻辑，更安全更简洁。

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource的ruleReplaceRegex为null
- ruleReplaceRegex为null时不执行替换，与当前行为完全一致
- 替换逻辑完全对齐BookContent.kt的L168-175实现

### 改动7：RssSource支持副文/歌词/弹幕（书源→订阅源subContent）⚠️ V8新增MAJOR

**问题根因**：`ContentRule.subContent`（副文规则）用于获取歌词、弹幕、字幕等辅助内容，在`BookContent.kt` L128-165中有完整的副文获取和拼接逻辑。但RssSource没有subContent字段，`Rss.kt getContentAwait()`也不处理副文。书源→订阅源转换时，副文完全丢失。

**V7误评说明**：V7将ContentRule.subContent评为MINOR影响，这是错误的。对于音频书源（bookSourceType=1），subContent通常用于获取歌词，是核心功能；对于视频书源（bookSourceType=4），subContent可能包含弹幕数据。

**BookContent副文处理逻辑**（BookContent.kt L128-165）：
```kotlin
val subContent = analyzeRule.getString(contentRule.subContent)
if (!subContent.isNullOrBlank()) {
    contentData = contentData + "\n" + subContent  // 拼接副文到正文
}
```

**改动方案**：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleSubContent: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `Rss.kt` | getContentAwait()中：ruleSubContent非空时追加副文 | ruleSubContent为null→不走副文→行为不变 |
| `DatabaseMigrations.kt` | MIGRATION合并版添加 ruleSubContent 列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 递增 | 同步版本号 |

**Rss.kt 改动详细**（在改动5的替换步骤之后、return之前插入）：
```kotlin
// V8改动7：副文支持（对应书源ContentRule.subContent）
val subContentRule = rssSource.ruleSubContent
if (!subContentRule.isNullOrBlank()) {
    val subContent = analyzeRule.getString(subContentRule)
    if (!subContent.isNullOrBlank()) {
        finalContent = finalContent + "\n" + subContent
    }
}
return finalContent
```

**转换逻辑更新**：
```kotlin
// SourceConverter.bookSourceToRssSource() 中新增：
if (!contentRule.subContent.isNullOrEmpty()) {
    rssSource.ruleSubContent = contentRule.subContent
}
// SourceConverter.rssSourceToBookSource() 中新增：
if (!rssSource.ruleSubContent.isNullOrBlank()) {
    contentRule.subContent = rssSource.ruleSubContent
}
```

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource的ruleSubContent为null
- ruleSubContent为null时不追加副文，与当前行为完全一致
- 副文拼接逻辑对齐BookContent.kt L128-165的实现

### 改动8：RssSource支持作者信息（双向author映射）⚠️ V8新增MAJOR

**问题根因**：`BookListRule`接口定义了`author`字段（BookListRule.kt L9），`SearchRule`和`ExploreRule`都实现了此接口。但RssSource没有author字段，`RssParserByRule`也不解析作者信息。双向转换都丢失作者信息。

**源码铁证**（BookListRule.kt L6-16）：
```kotlin
interface BookListRule {
    var bookList: String?
    var name: String?
    var author: String?     // ← RssSource无对应字段！
    var intro: String?
    var kind: String?
    var lastChapter: String?
    var updateTime: String?
    var bookUrl: String?
    var coverUrl: String?
    var wordCount: String?
}
```

**改动方案**：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleAuthor: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `RssParserByRule.kt` | parseXML()中：ruleAuthor非空时解析作者到RssArticle | ruleAuthor为null→不解析→行为不变 |
| `RssArticle.kt` | 确认已有author字段（或新增） | 需源码确认 |
| `DatabaseMigrations.kt` | MIGRATION合并版添加 ruleAuthor 列 | ALTER TABLE ADD COLUMN 默认null |

**RssParserByRule.kt 改动详细**：
```kotlin
// 在parseXML()中，与ruleTitle/ruleImage/ruleLink并列位置新增：
val ruleAuthor = rssSource.ruleAuthor
if (!ruleAuthor.isNullOrBlank()) {
    article.author = analyzeRule.getString(ruleAuthor)
}
```

**转换逻辑更新**：
```kotlin
// SourceConverter.bookSourceToRssSource() 中新增：
val authorRule = bookSource.getExploreRule().author ?: bookSource.getSearchRule().author
if (!authorRule.isNullOrEmpty()) {
    rssSource.ruleAuthor = authorRule
}

// SourceConverter.rssSourceToBookSource() 中新增：
if (!rssSource.ruleAuthor.isNullOrBlank()) {
    exploreRule.author = rssSource.ruleAuthor
    searchRule.author = rssSource.ruleAuthor
}
```

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource的ruleAuthor为null
- ruleAuthor为null时不解析作者，与当前行为完全一致
- RssArticle如果已有author字段则无需修改数据表，只需解析逻辑

### 改动9：BookSource支持URL过滤（订阅源→书源contentWhitelist/contentBlacklist）⚠️ V8新增MAJOR

**问题根因**：`RssSource`有`contentWhitelist`和`contentBlacklist`字段（RssSource.kt L78-80），用于过滤正文中的URL链接。例如contentBlacklist可以过滤广告URL。但BookSource没有URL过滤功能，`BookContent.kt`也不处理URL过滤。订阅源→书源转换时，URL过滤能力丢失，正文可能包含广告链接。

**改动方案**：在ContentRule中新增contentWhitelist和contentBlacklist字段，在BookContent获取正文后执行URL过滤。

| 文件 | 改动 | 影响 |
|------|------|------|
| `ContentRule.kt` | 新增 `var contentWhitelist: String? = null` 和 `var contentBlacklist: String? = null` 字段 | 新字段默认null，JSON反序列化时自动忽略 |
| `BookContent.kt` | analyzeContent()中：contentWhitelist/contentBlacklist非空时过滤正文URL | 字段为null→不过滤→行为不变 |

**BookContent.kt 改动详细**（在replaceRegex处理之后插入）：
```kotlin
// V8改动9：URL过滤支持（对应RssSource.contentWhitelist/contentBlacklist）
val whitelist = contentRule.contentWhitelist
val blacklist = contentRule.contentBlacklist
if (!whitelist.isNullOrBlank() || !blacklist.isNullOrBlank()) {
    contentStr = filterContentUrls(contentStr, whitelist, blacklist)
}
```

**转换逻辑更新**：
```kotlin
// SourceConverter.rssSourceToBookSource() 中新增：
if (!rssSource.contentWhitelist.isNullOrBlank()) {
    contentRule.contentWhitelist = rssSource.contentWhitelist
}
if (!rssSource.contentBlacklist.isNullOrBlank()) {
    contentRule.contentBlacklist = rssSource.contentBlacklist
}

// SourceConverter.bookSourceToRssSource() 中新增：
val contentRule = bookSource.getContentRule()
if (!contentRule.contentWhitelist.isNullOrEmpty()) {
    rssSource.contentWhitelist = contentRule.contentWhitelist
}
if (!contentRule.contentBlacklist.isNullOrEmpty()) {
    rssSource.contentBlacklist = contentRule.contentBlacklist
}
```

**不影响现有功能保证**：
- ContentRule新增字段默认null，所有现有BookSource不受影响
- contentWhitelist/contentBlacklist为null时不过滤，与当前行为完全一致
- ContentRule是BookSource的嵌套JSON字段，Room自动序列化，无需数据库migration

### 100%互转完整方案汇总（V9版）

| 不可弥补项 | 改动方案 | 改动文件数 | 代码行数(估) | 不影响现有 | 严重度 |
|-----------|---------|-----------|------------|-----------|--------|
| imageDecode | RssSource添加imageDecode+ImageUtils支持 | 4 | ~15行 | ✅ 新字段默认null | MAJOR |
| 视频多线路 | ContentRule添加routeRule+routeContentRule+VideoPlay读取 | 3 | ~40行 | ✅ 新字段默认null | MAJOR |
| webJs | RssSource添加ruleWebJs+Rss.kt传jsStr参数 | 4 | ~5行 | ✅ 新字段默认null | MAJOR |
| **内容分页** | **RssSource添加ruleNextContentUrl+Rss.kt分页循环** | **4** | **~25行** | **✅ 新字段默认null** | **CRITICAL** |
| **内容替换** | **RssSource添加ruleReplaceRegex+Rss.kt替换步骤** | **4** | **~5行** | **✅ 新字段默认null** | **CRITICAL** |
| **智能BookInfoRule+TocRule** | **SourceConverter生成BookInfoRule(tocUrl指向sortUrl)+TocRule(含nextTocUrl)** | **1** | **~30行** | **✅ 仅在转换时生成，不影响现有源** | **CRITICAL** |
| 副文/歌词/弹幕 | RssSource添加ruleSubContent+Rss.kt追加副文 | 4 | ~10行 | ✅ 新字段默认null | MAJOR(V8) |
| 作者信息 | RssSource添加ruleAuthor+RssParserByRule解析 | 3 | ~8行 | ✅ 新字段默认null | MAJOR(V8) |
| URL过滤 | ContentRule添加contentWhitelist/contentBlacklist+BookContent过滤 | 3 | ~15行 | ✅ 新字段默认null | MAJOR(V8) |
| **视频R5降级** | **VideoPlay BookSource分支content为空时R5自动提取** | **1** | **~30行** | **✅ 仅在content为空时触发** | **CRITICAL(V9)** |
| **sourceRegex** | **RssSource添加ruleSourceRegex+Rss.kt传sourceRegex参数** | **4** | **~5行** | **✅ 新字段默认null** | **MAJOR(V9)** |
| imageStyle | RssSource添加ruleImageStyle+转换映射 | 2 | ~3行 | ✅ 新字段默认null | MINOR(V9) |

> **V9 vs V8 核心区别**：V8解决了字段级功能缺失，V9解决运行时流程级遗漏——①BookSource视频路径无R5降级导致无ruleContent的视频源转换后无法播放 ②sourceRegex未映射导致音频/视频WebView资源嗅探功能丢失 ③音频源评级修正（RssSource无音频类型是架构限制，无法通过简单字段映射解决）。

### 改动10：BookSource视频R5自动提取降级 ⚠️ V9新增CRITICAL

**问题根因**：VideoPlay.kt L607-608中，BookSource视频播放分支在content为空时直接抛ContentEmptyException，而RssSource分支有完整的R5自动提取流程。

**当前代码**（VideoPlay.kt L604-643）：
```kotlin
WebBook.getContent(loadScope, source as BookSource, book, chapter)
    .onSuccess(IO) { content ->
        val content = content.trim()
        val mUrl = if (content.isEmpty()) {
            throw ContentEmptyException("正文为空")  // ← 无降级！
        } else if (content.startsWith("<")) {
            // mpd文本处理
        } else {
            content
        }
    }
```

**改动方案**：content为空时不抛异常，而是触发R5自动提取。

| 文件 | 改动 | 影响 |
|------|------|------|
| `VideoPlay.kt` | BookSource视频分支content为空时调用VideoUrlExtractor | 仅在content为空时触发，有content的源不受影响 |

**VideoPlay.kt 改动详细**（替换L607-608的throw）：
```kotlin
val content = content.trim()
val mUrl = if (content.isEmpty()) {
    // V9改动10：R5自动视频链接抓取（复用RssSource分支的降级机制）
    val chapterUrl = chapter.url
    if (chapterUrl.isNullOrBlank()) {
        throw ContentEmptyException("正文为空且无章节URL")
    }
    val analyzeUrl = AnalyzeUrl(chapterUrl, source = source, ruleData = book, chapter = chapter)
    val res = analyzeUrl.getStrResponseAwait(jsStr = contentRule.webJs, sourceRegex = contentRule.sourceRegex)
    val html = res.body ?: ""
    val videoUrls = VideoUrlExtractor.extractPrecise(html, chapterUrl)
    when {
        videoUrls.size == 1 -> videoUrls[0]
        videoUrls.size > 1 -> {
            // 多URL：使用第一个
            AppLog.put("R5自动提取发现${videoUrls.size}个视频URL，使用第一个")
            videoUrls[0]
        }
        else -> {
            // 静态解析失败，尝试WebView嗅探
            val webViewUrl = VideoUrlExtractor.extractWithWebView(
                html, chapterUrl, headerMap = analyzeUrl.headerMap
            )
            if (webViewUrl != null) {
                webViewUrl
            } else {
                // WebView也失败，尝试正则
                val regexUrls = VideoUrlExtractor.extractByRegex(html, chapterUrl)
                if (regexUrls.isNotEmpty()) regexUrls[0]
                else throw ContentEmptyException("R5自动提取未找到视频URL")
            }
        }
    }
} else if (content.startsWith("<")) {
    // mpd文本处理（保持原逻辑不变）
    val name = MD5Utils.md5Encode(content) + ".mpd"
    val file = FileUtils.createFileIfNotExist(videoTempFile, name)
    file.writeText(content)
    Uri.fromFile(file).toString()
} else {
    content
}
```

**不影响现有功能保证**：
- `content.isEmpty()` 为false时走原路径，行为完全不变
- R5降级仅在content为空时触发，对有content的视频书源无影响
- VideoUrlExtractor是已有的工具类，RssSource分支已充分验证

### 改动11：RssSource支持sourceRegex（WebView资源嗅探）⚠️ V9新增MAJOR

**问题根因**：ContentRule.sourceRegex用于BackstageWebView的资源嗅探模式——当sourceRegex非空时，BackstageWebView拦截匹配正则的资源请求并返回资源URL。音频源和部分视频源依赖此功能获取播放URL。

**改动方案**（与改动3 ruleWebJs完全同构）：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleSourceRegex: String? = null` 字段 | 新字段默认null，现有RssSource不受影响 |
| `Rss.kt` | getContentAwait() L149改为：`analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs, sourceRegex = rssSource.ruleSourceRegex)` | ruleSourceRegex为null→走原路径→行为不变 |
| `DatabaseMigrations.kt` | MIGRATION合并版添加 ruleSourceRegex 列 | ALTER TABLE ADD COLUMN 默认null |
| `AppDatabase.kt` | version 递增 | 同步版本号 |

**核心改动只有1行代码！** 从`analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs)`改为`analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs, sourceRegex = rssSource.ruleSourceRegex)`。

**转换逻辑更新**：
```kotlin
// SourceConverter.bookSourceToRssSource() 中新增：
if (!contentRule.sourceRegex.isNullOrEmpty()) {
    rssSource.ruleSourceRegex = contentRule.sourceRegex
}

// SourceConverter.rssSourceToBookSource() 中新增：
if (!rssSource.ruleSourceRegex.isNullOrBlank()) {
    contentRule.sourceRegex = rssSource.ruleSourceRegex
}
```

**不影响现有功能保证**：
- ruleSourceRegex默认null，`getStrResponseAwait(sourceRegex=null)`等价于原路径→行为完全不变
- 与改动3（ruleWebJs）完全同构，已验证安全性

### 改动12：RssSource支持imageStyle（图片显示样式）⚠️ V9新增MINOR

**问题根因**：ContentRule.imageStyle控制图片显示样式（FULL最大宽度/默认居中）。ReadBook.kt L175-180读取此字段设置图片显示模式。RssSource无对应字段。

**源码铁证**（ReadBook.kt L175-180）：
```kotlin
var imageStyle = it.getContentRule().imageStyle
if (imageStyle.isNullOrBlank() && (book.isImage || book.isPdf)) {
    imageStyle = Book.imgStyleFull  // 图片源默认FULL
}
book.setImageStyle(imageStyle)
```

**影响评估**：
- 图片书源→订阅源：imageStyle丢失，但图片源默认已经是FULL模式，影响极小
- 订阅源→书源：RssSource无imageStyle字段，转换后图片源默认FULL模式，行为正确

**改动方案**（最小化）：

| 文件 | 改动 | 影响 |
|------|------|------|
| `RssSource.kt` | 新增 `var ruleImageStyle: String? = null` 字段 | 新字段默认null |
| `DatabaseMigrations.kt` | MIGRATION合并版添加 ruleImageStyle 列 | ALTER TABLE ADD COLUMN 默认null |

**注意**：RssSource的图片展示走ImageGalleryActivity而非ReadBook，imageStyle在ImageGalleryActivity中不生效。因此这个字段主要用于**双向转换的字段完整性**——确保转换后字段不丢失，在反向转换时能恢复。

**转换逻辑更新**：
```kotlin
// SourceConverter.bookSourceToRssSource() 中新增：
if (!contentRule.imageStyle.isNullOrEmpty()) {
    rssSource.ruleImageStyle = contentRule.imageStyle
}

// SourceConverter.rssSourceToBookSource() 中新增：
if (!rssSource.ruleImageStyle.isNullOrBlank()) {
    contentRule.imageStyle = rssSource.ruleImageStyle
}
```

**不影响现有功能保证**：
- 新增字段默认null，所有现有RssSource不受影响
- RssSource运行时不读取ruleImageStyle（ImageGalleryActivity不使用此字段）

### V7发现的3个CRITICAL缺陷详情

#### DEFECT-1：智能TocRule在articleUrl页面上无法工作（V7发现）

**根因**：BookSource运行时流程为：
1. 探索/搜索 → 列出结果（每条结果有bookUrl）
2. 点击结果 → BookInfo加载bookUrl页面 → 解析BookInfoRule → 确定tocUrl
3. BookChapterList加载tocUrl页面 → 用TocRule解析章节

V6的智能TocRule设置`chapterList = ruleArticles`，这要求tocUrl页面是sortUrl页面（因为ruleArticles是sortUrl页面上的文章列表选择器）。但V6没有生成BookInfoRule，导致tocUrl默认为articleUrl（文章内容页），在文章内容页上ruleArticles找不到文章列表元素，目录为空！

**影响**：订阅源→书源后，打开任何"书"都无法显示章节列表，**阅读流程完全中断**！

**修复**：改动6——生成BookInfoRule，将tocUrl指向sortUrl页面URL

#### DEFECT-2：智能TocRule缺少nextTocUrl映射（V7发现）

**根因**：TocRule有`nextTocUrl`字段（TocRule.kt L19），支持目录翻页。RssSource有`ruleNextPage`字段，支持文章列表翻页。这两个字段语义等价（都是"列表的下一页"），但V6的智能TocRule没有映射。

**影响**：当订阅源的文章列表有分页时（如每页20篇文章，共100篇），转换后书源只能显示第一页的20个章节，后续80个章节丢失。

**修复**：智能TocRule生成中添加`nextTocUrl = rssSource.ruleNextPage`

#### DEFECT-3：字段映射nextContentUrl≠ruleNextPage（V7发现）

**根因**：V6的字段映射表中`ContentRule.nextContentUrl → ruleNextPage`是错误的。这两个字段的语义完全不同：
- `ContentRule.nextContentUrl`：文章**内容**的下一页（BookContent.kt L73-101的分页循环）
- `RssSource.ruleNextPage`：文章**列表**的下一页（Rss.kt getArticlesAwait中的列表翻页）

**影响**：
1. 书源→订阅源：如果书源有nextContentUrl（长文章分页），映射到ruleNextPage会导致文章列表翻页逻辑错误
2. 订阅源→书源：ruleNextPage映射到ContentRule.nextContentUrl会导致内容分页逻辑错误

**修复**：
- `ContentRule.nextContentUrl → RssSource.ruleNextContentUrl`（新增字段，改动4）
- `TocRule.nextTocUrl → RssSource.ruleNextPage`（目录分页=列表分页）
- `RssSource.ruleNextPage → TocRule.nextTocUrl`（反向映射，在智能TocRule中）

### 100%互转后可用性（V8版）

| 方向 | V2 | V5 | V6 | V7 | V8 | V9(100%) | 关键改进 |
|------|-----|-----|-----|-----|-----|---------|---------|
| 书源→订阅源(文本) | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | subContent+author+分页+替换 |
| 书源→订阅源(图片) | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | imageDecode+副文+分页+替换 |
| 书源→订阅源(视频) | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | webJs+副文(弹幕)+分页+替换+R5降级(V9) |
| 书源→订阅源(音频) | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | **V9修正：RssSource无音频类型，AudioPlay仅支持BookSource** |
| 订阅源→书源(文本) | ★★☆☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤 |
| 订阅源→书源(图片) | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤 |
| 订阅源→书源(视频) | ★☆☆☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤+routeRule+R5降级(V9) |

> **V9版核心变化**：①音频方向从★★★★★修正为★★★★☆（RssSource无音频类型，音频URL可获取但AudioPlay播放体验丢失）②视频方向新增R5降级机制确保无ruleContent的视频源转换后可播放③新增sourceRegex映射弥补WebView资源嗅探。

### V9关键发现：3个运行时流程级遗漏

#### DEFECT-7：BookSource视频播放路径无R5自动提取降级（V9发现CRITICAL）

**问题根因**：VideoPlay.kt L607-608中，BookSource视频播放分支在WebBook.getContent()返回空内容时，直接抛出`ContentEmptyException("正文为空")`，没有降级机制。而RssSource分支（L357-481）有完整的R5自动提取流程（静态解析→WebView嗅探→正则）。

**影响场景**：当RssSource视频源没有ruleContent（依赖R5自动提取获取视频URL）时，转换为BookSource后视频无法播放。这是"100%互转"的重大障碍。

**源码铁证**：
```kotlin
// VideoPlay.kt L604-608 BookSource视频播放分支
WebBook.getContent(loadScope, source as BookSource, book, chapter)
    .onSuccess(IO) { content ->
        val content = content.trim()
        val mUrl = if (content.isEmpty()) {
            throw ContentEmptyException("正文为空")  // ← 无降级机制！
        }
    }
```

```kotlin
// VideoPlay.kt L357-481 RssSource视频播放分支
if (ruleContent.isNullOrBlank() && !hasNewRoutesMode) {
    // R5自动视频链接抓取 ← 有完整降级机制
    Coroutine.async(loadScope, IO) {
        val videoUrls = VideoUrlExtractor.extractPrecise(html, rssArticle.link)
        when {
            videoUrls.size == 1 -> { /* 单URL播放 */ }
            videoUrls.size > 1 -> { /* 多URL播放 */ }
            else -> {
                // WebView嗅探
                val webViewUrl = VideoUrlExtractor.extractWithWebView(...)
                if (webViewUrl != null) { /* 播放 */ }
                else {
                    // 正则兜底
                    val regexUrls = VideoUrlExtractor.extractByRegex(html, rssArticle.link)
                }
            }
        }
    }
}
```

**修复方案**：改动10——在BookSource视频播放分支中，content为空时触发R5自动提取。

#### DEFECT-8：ContentRule.sourceRegex未映射（V9发现MAJOR）

**问题根因**：ContentRule.sourceRegex用于WebView资源嗅探（拦截WebView的请求，匹配正则后返回资源URL）。这是音频源和部分视频源的核心功能——音频URL不在HTML内容中，需要通过WebView加载页面后嗅探资源请求获取。

**源码铁证**：
```kotlin
// WebBook.kt L442-444 书源内容获取
val res = analyzeUrl.getStrResponseAwait(
    jsStr = contentRule.webJs,
    sourceRegex = contentRule.sourceRegex  // ← 传给BackstageWebView做资源嗅探
)
```

```kotlin
// BackstageWebView.kt L64 资源嗅探参数
class BackstageWebView(
    private val sourceRegex: String? = null,  // ← 匹配资源URL的正则
    ...
) {
    // L177-178: sourceRegex非空时启用资源嗅探模式
    if (sourceRegex.isNullOrBlank() && overrideUrlRegex.isNullOrBlank()) {
        // HTML获取模式
    } else {
        // 资源嗅探模式
    }
}
```

**影响**：
- 音频书源→订阅源：sourceRegex丢失导致音频URL无法通过嗅探获取
- 视频书源→订阅源：部分依赖sourceRegex嗅探视频URL的源，转换后无法播放
- 订阅源→书源：RssSource没有sourceRegex字段，即使有嗅探需求也无法映射

**修复方案**：改动11——RssSource新增ruleSourceRegex字段 + Rss.kt传sourceRegex参数。

#### DEFECT-9：音频源评级虚高（V9发现MAJOR）

**问题根因**：V8将"书源→订阅源(音频)"评级为★★★★★，但RssSource完全没有音频类型支持：
- RssSource.type只支持0(网页)/1(图片)/2(视频)，没有3(音频)
- AudioPlay.kt L76 `var bookSource: BookSource? = null` — AudioPlay只支持BookSource
- 音频播放流程（AudioPlay + AudioPlayService + MediaSession）完全基于BookSource架构

**影响**：
- 音频书源转订阅源后：音频URL可通过ruleContent获取，但无法用AudioPlay播放
- 用户只能通过WebView查看音频URL文本，无法获得播放/暂停/上下曲/倍速等音频控制
- 歌词(subContent)可通过V8改动7获取，但无法在AudioPlay界面展示

**评级修正**：★★★★★ → ★★★★☆（内容可获取，但音频播放体验降级为WebView文本展示）

### V7可行性深度验证（补充）

#### 验证1：@js:前缀在BookInfoRule.tocUrl中的可行性 ✅ 通过

**验证方法**：源码级跟踪AnalyzeRule.getString()的完整执行路径

| 验证步骤 | 源码位置 | 结论 |
|---------|---------|------|
| splitSourceRule识别@js:前缀 | AnalyzeRule.kt L552-560 | ✅ JS_PATTERN正则匹配`@js:`，创建Mode.Js规则 |
| getString()处理Mode.Js | AnalyzeRule.kt L339 | ✅ 调用evalJS(rule, result)执行JS代码 |
| evalJS()返回JS执行结果 | AnalyzeRule.kt | ✅ 返回JS代码的返回值（字符串URL） |
| isUrl=true参数处理 | BookInfo.kt L163 | ✅ 将JS返回的字符串处理为绝对URL |
| book.tocUrl赋值 | BookInfo.kt L163-164 | ✅ tocUrl = JS返回的sortUrl页面URL |

**结论**：`BookInfoRule.tocUrl = "@js:'url'"` 可行，AnalyzeRule完整支持。

#### 验证2：sortUrls()扩展方法处理所有sortUrl格式 ✅ 通过

**验证方法**：源码级分析RssSourceExtensions.kt

| sortUrl格式 | sortUrls()处理方式 | tocUrl值 |
|------------|-------------------|---------|
| "分类1::url1\n分类2::url2" | split("(&&\|\n)+") → 拆分name::url对 | 第一个url对的URL |
| "<js>code</js>" | 执行JS代码 → 缓存结果 → 解析name::url对 | JS执行结果的第一个URL |
| "@js:code" | 同上（substring(4)去掉@js:前缀） | 同上 |
| 空sortUrl | 回退到Pair("", sourceUrl) | rssSource.sourceUrl |

**结论**：`sortUrls()` 方法已完整处理所有sortUrl格式，V7改动6使用此方法获取tocUrl是可靠的。

#### 验证3：WebBook.getChapterList()在tocUrl≠bookUrl时的行为 ✅ 通过

**验证方法**：源码级分析WebBook.kt L314-368

| 场景 | WebBook行为 | 结论 |
|------|-----------|------|
| tocUrl == bookUrl 且 tocHtml非空 | 直接使用tocHtml解析 | 不适用（tocUrl=sortUrl≠bookUrl） |
| tocUrl != bookUrl | 使用AnalyzeUrl请求tocUrl页面 | ✅ 正确加载sortUrl页面 |
| sortUrl页面需要header/cookie | AnalyzeUrl自动从source获取 | ✅ 自动处理 |
| 请求sortUrl页面失败 | 抛出异常，显示错误 | 需在转换预览中提示"需要网络访问" |

**结论**：当tocUrl=sortUrl时，WebBook会正确发起网络请求加载sortUrl页面HTML，交给BookChapterList解析。

### V7已知限制（非阻塞，需在转换预览中提示）

#### LIMIT-1：sortUrl多分类时tocUrl只指向第一个分类

**场景**：sortUrl包含"最新::url1\n热门::url2"，tocUrl只指向url1。
**影响**：用户浏览"热门"分类后点击文章，章节列表显示的是"最新"分类的文章。
**缓解**：在转换预览中提示"目录页使用第一个分类URL，其他分类文章可能在目录中不显示"。
**后续优化**：可考虑在每个分类搜索结果中传递分类URL，但需要修改BookSource数据模型。

#### LIMIT-2：BookInfoRule.name/coverUrl/intro在articleUrl页面上可能不匹配

**场景**：ruleTitle/ruleImage/ruleDescription是sortUrl页面上的选择器，在articleUrl页面上可能找不到对应元素。
**影响**：书籍详情页可能无法更新书名/封面/简介（搜索结果中已有这些信息，不影响功能）。
**缓解**：BookInfoRule.name/coverUrl/intro匹配失败时不会报错（AnalyzeRule.getString()返回空字符串），搜索结果中name/coverUrl/intro由SearchRule/ExploreRule正确解析。
**后续优化**：可为articleUrl页面单独配置name/coverUrl/intro规则（但需用户手动添加）。

#### LIMIT-3：每次打开"书"需额外请求sortUrl页面

**场景**：因为tocUrl≠bookUrl，WebBook.getChapterList()需要发起新的网络请求。
**影响**：打开书后的目录加载会比普通书源多一次网络请求（约0.5-2秒延迟）。
**缓解**：这是设计固有的，因为sortUrl页面内容与articleUrl页面不同。延迟在可接受范围内。

#### LIMIT-4：sortUrl页面不含文章列表元素时目录为空

**场景**：极少数RSS源的sortUrl页面可能不含ruleArticles匹配的元素（如sortUrl指向重定向页面）。
**影响**：目录为空，无法阅读。
**缓解**：在转换预览中提示"目录规则需要验证，建议转换后测试阅读功能"。

### 数据库Migration规划

当前数据库版本：101（AppDatabase.kt）

| Migration | 版本变更 | 内容 |
|-----------|---------|------|
| MIGRATION_101_107 | 101→107 | rssSources表一次性添加9列：imageDecode/ruleWebJs/ruleNextContentUrl/ruleReplaceRegex/ruleSubContent/ruleAuthor/ruleSourceRegex/ruleImageStyle（均为TEXT，默认null） |
| ContentRule | 无需migration | routeRule/routeContentRule/contentWhitelist/contentBlacklist是ContentRule JSON内字段，Room自动序列化 |

> **合并优化**：所有migration合并为1个（101→107），一次性添加8列（imageDecode/ruleWebJs/ruleNextContentUrl/ruleReplaceRegex/ruleSubContent/ruleAuthor/ruleSourceRegex/ruleImageStyle），减少migration代码量。

---

## 现有功能安全性分析（V6新增）

> **核心问题**：5个源码改动是否会影响现有书源和订阅源的正常功能？以下逐改动点进行源码级安全性验证。

### 改动1：imageDecode — 风险等级：低

**改动点**：`ImageUtils.getRuleJs()` RssSource分支从 `source.coverDecodeJs` 改为 `if (isCover) source.coverDecodeJs else source.imageDecode`

| 验证项 | 结论 |
|--------|------|
| isCover=true时行为 | 仍返回`source.coverDecodeJs`，与当前完全一致 |
| isCover=false时行为 | 返回`source.imageDecode`，新增字段默认null→返回null |
| getRuleJs()返回null时 | ImageUtils.decode()直接返回原始bytes，不做任何处理，与当前行为一致 |
| 现有RssSource影响 | 无影响（imageDecode字段默认null，不改变任何现有行为） |

### 改动2：routeRule+routeContentRule — 风险等级：低

**改动点**：VideoPlay.startPlay() BookSource分支新增routeRule解析

| 验证项 | 结论 |
|--------|------|
| 现有BookSource无routeRule | ContentRule.routeRule默认null→`isNullOrBlank()`为true→不走多线路→行为不变 |
| rssRoutes全局变量竞争 | 低风险：rssRoutes/rssRouteIndex在单次播放上下文中有效，VideoPlay是单例但同一时刻只有一个播放器活跃 |
| BookSource分支代码位置 | 在获取contentRule之后、WebBook.getContent之前，不修改原有BookSource播放流程 |
| VideoPlayerActivity UI | showRssRoutes()检查`rssRoutes.isNullOrEmpty()`→BookSource无routeRule时rssRoutes=null→不显示线路UI |
| RssSource多线路 | 完全独立代码路径（RssSource分支在startPlay中是单独的else if），不受影响 |

### 改动3：ruleWebJs — 风险等级：极低

**改动点**：`Rss.kt getContentAwait()` L149 `analyzeUrl.getStrResponseAwait()` → `analyzeUrl.getStrResponseAwait(jsStr = rssSource.ruleWebJs)`

| 验证项 | 结论 |
|--------|------|
| AnalyzeUrl.getStrResponseAwait默认参数 | `jsStr: String? = null`，传null等价于不传参 |
| ruleWebJs默认null | `var ruleWebJs: String? = null`，现有RssSource.ruleWebJs为null |
| null→getStrResponseAwait(jsStr=null) | 完全等价于`getStrResponseAwait()`，行为不变 |
| getRoutesContentAwait | L226也调用`analyzeUrl.getStrResponseAwait()`，同样需传jsStr（同一改动） |

### 改动4：ruleNextContentUrl — 风险等级：低

**改动点**：`Rss.kt getContentAwait()` 在`getString(ruleContent)`之后新增分页循环

| 验证项 | 结论 |
|--------|------|
| 分页循环条件 | `!rssSource.ruleNextContentUrl.isNullOrBlank()`，null时不进入循环 |
| 现有RssSource | ruleNextContentUrl默认null→不进入分页循环→行为不变 |
| 分页循环死循环风险 | nextUrlList去重检查防止重复URL；需增加最大循环次数限制(10页) |
| 其他调用getContentAwait的地方 | Rss.getContent()是 getContentAwait的包装，改动点在getContentAwait内部，所有调用方自动生效 |
| getRoutesContentAwait | type=2+ruleRoutes非空时走getRoutesContentAwait分支，不经过getContentAwait，不受影响 |

### 改动5：ruleReplaceRegex — 风险等级：极低

**改动点**：`Rss.kt getContentAwait()` 在return之前新增replaceRegex替换

| 验证项 | 结论 |
|--------|------|
| 替换条件 | `!rssSource.ruleReplaceRegex.isNullOrBlank()`，null时不执行替换 |
| 现有RssSource | ruleReplaceRegex默认null→不执行替换→行为不变 |
| 替换逻辑对齐 | 完全复用BookContent.kt L168-175的实现，经过大量验证 |
| AppPattern.LFRegex引用 | 需在Rss.kt中新增import，无功能影响 |

### 数据库Migration安全性

| 验证项 | 结论 |
|--------|------|
| ALTER TABLE ADD COLUMN | 只添加列不修改数据，覆盖安装安全 |
| 列默认值 | 全部TEXT类型默认null，现有数据不受影响 |
| 合并migration | 4个列合并为1个migration(101→105)，减少migration代码量 |
| Room自动序列化 | ContentRule是BookSource的嵌套JSON字段，routeRule/routeContentRule新增字段自动忽略null |

### 综合安全性结论

**所有6个改动的风险等级均为"低"或"极低"**，核心保证机制：

1. **新增字段默认null**：所有RssSource/ContentRule新增字段默认null，现有数据不受影响
2. **null守卫**：所有改动点通过`isNullOrBlank()`守卫，null值时走原路径
3. **条件分支隔离**：新功能只在对应字段非空时激活，与原有逻辑完全隔离
4. **代码位置安全**：改动插入在现有逻辑的"安全间隙"中，不修改任何已有代码
5. **V7改动6无源码改动**：BookInfoRule+TocRule联合生成仅在SourceConverter中实现，不修改任何运行时代码

**无任何改动会影响现有书源和订阅源的正常功能。**

---

## 设计审查：阻塞点与待明确项（V8更新）

> **本章节记录全面审查发现的问题，必须在实施前解决。V7新增BLOCK-3/4/5（对应3个CRITICAL缺陷），V8新增DEFECT-4/5/6（对应3个MAJOR遗漏）。**

### 阻塞点（必须解决才能实施）

#### BLOCK-1：转换后新源URL冲突导致数据覆盖（V6发现，状态：已解决）

**问题**：BookSourceDao和RssSourceDao的insert方法都使用`OnConflictStrategy.REPLACE`，如果转换后新源的sourceUrl（主键）与已有源相同，会**覆盖已有源的数据**，导致数据丢失。

**解决方案**：SourceConverter在转换时必须**生成新的sourceUrl**，确保不与已有源冲突。具体方案：
```
原sourceUrl: "https://example.com"
转换后sourceUrl: "https://example.com#convert_1700000000"  // 追加时间戳哈希后缀
```
在SourceConverter.convert()中检查目标数据库是否已存在同URL的源，若存在则追加后缀。

#### BLOCK-2：编辑界面未适配新增字段（V6发现，状态：最小方案可行）

**问题**：BookSourceEditActivity和RssSourceEditActivity的编辑界面没有适配新增字段（routeRule/routeContentRule/imageDecode/ruleWebJs/ruleNextContentUrl/ruleReplaceRegex），用户无法在编辑界面修改这些字段。

**最小可行方案**：P0通过预览对话框"编辑源"按钮跳转编辑页面，用户可手动编辑JSON。P1编辑界面适配可选。

#### BLOCK-3：智能TocRule在articleUrl页面上无法工作 ⚠️ V7发现CRITICAL

**问题**：V6的智能TocRule设置`chapterList = ruleArticles`，这要求目录页是sortUrl页面。但BookInfo加载后，tocUrl默认为articleUrl（文章内容页），在文章内容页上ruleArticles找不到文章列表元素，**目录为空，阅读流程完全中断**！

**源码铁证**：BookInfo.kt L163-164：
```kotlin
book.tocUrl = analyzeRule.getString(infoRule.tocUrl, isUrl = true)
if (book.tocUrl.isEmpty()) book.tocUrl = baseUrl  // baseUrl = articleUrl！
```

**解决方案**：V7改动6——生成智能BookInfoRule，将tocUrl指向sortUrl页面URL：
```kotlin
bookInfoRule.tocUrl = "@js:'${firstSortUrl}'"
```
AnalyzeRule.getString()会执行JS代码并返回sortUrl URL字符串，BookChapterList会加载sortUrl页面，TocRule.chapterList = ruleArticles在该页面上正确解析。

**状态**：✅ 已在改动6中解决

#### BLOCK-4：智能TocRule缺少nextTocUrl映射 ⚠️ V7发现CRITICAL

**问题**：V6的智能TocRule没有映射ruleNextPage→nextTocUrl。当订阅源的文章列表有分页时，转换后书源只能显示第一页的章节，后续章节丢失。

**源码铁证**：TocRule.kt L19有nextTocUrl字段，BookChapterList.kt L207-222使用nextTocUrl获取目录下一页。

**解决方案**：智能TocRule生成中添加`nextTocUrl = rssSource.ruleNextPage`。

**状态**：✅ 已在改动6中解决

#### BLOCK-5：字段映射nextContentUrl≠ruleNextPage ⚠️ V7发现CRITICAL

**问题**：V6的字段映射`ContentRule.nextContentUrl → ruleNextPage`是错误的。这两个字段语义完全不同：
- ContentRule.nextContentUrl：文章**内容**的下一页（长文章翻页）
- RssSource.ruleNextPage：文章**列表**的下一页（列表翻页）

**正确的映射关系**：
| BookSource字段 | 语义 | RssSource对应字段 | 语义 |
|---------------|------|-----------------|------|
| ContentRule.nextContentUrl | 内容分页 | ruleNextContentUrl（新增） | 内容分页 |
| TocRule.nextTocUrl | 目录分页 | ruleNextPage | 列表分页 |

**解决方案**：修正字段映射表，ContentRule.nextContentUrl映射到ruleNextContentUrl（改动4新增字段），TocRule.nextTocUrl映射到ruleNextPage。

**状态**：✅ 已在V7字段映射表中修正

#### DEFECT-4：ContentRule.subContent副文丢失（V8发现MAJOR）

**问题**：V7将ContentRule.subContent评为MINOR影响，这是错误评估。subContent用于获取歌词/弹幕/字幕，对音频源（bookSourceType=1）是核心功能。

**源码铁证**：ContentRule.kt L14 `var subContent: String? = null`，BookContent.kt L128-165有完整的副文获取和拼接逻辑。RssSource无对应字段。

**影响**：音频书源→订阅源后歌词丢失；视频书源→订阅源后弹幕丢失。

**修复**：改动7——RssSource新增ruleSubContent字段 + Rss.kt追加副文

**状态**：✅ 已在改动7中解决

#### DEFECT-5：BookListRule.author作者信息双向丢失（V8发现MAJOR）

**问题**：BookListRule接口定义了author字段（BookListRule.kt L9），SearchRule和ExploreRule都实现了此字段。但RssSource完全无author字段，RssParserByRule也不解析作者信息。

**源码铁证**：BookListRule.kt L9 `var author: String?`，RssSource.kt完整字段列表中无author相关字段。

**影响**：双向转换都丢失作者信息。

**修复**：改动8——RssSource新增ruleAuthor字段 + RssParserByRule解析

**状态**：✅ 已在改动8中解决

#### DEFECT-6：RssSource.contentWhitelist/contentBlacklist URL过滤丢失（V8发现MAJOR）

**问题**：RssSource有contentWhitelist和contentBlacklist字段（RssSource.kt L78-80），用于过滤正文中的广告URL。BookSource无此功能。

**源码铁证**：RssSource.kt L78-80有`contentWhitelist`和`contentBlacklist`字段，ContentRule.kt无对应字段。

**影响**：订阅源→书源后URL过滤能力丢失，正文可能包含广告链接。

**修复**：改动9——ContentRule新增contentWhitelist/contentBlacklist + BookContent过滤

**状态**：✅ 已在改动9中解决

#### DEFECT-7：BookSource视频播放路径无R5自动提取降级（V9发现CRITICAL）

**问题**：VideoPlay.kt L607-608中，BookSource视频播放分支在content为空时直接抛ContentEmptyException，没有R5自动提取降级。而RssSource分支（L357-481）有完整的R5降级流程。

**源码铁证**：VideoPlay.kt L607-608 `throw ContentEmptyException("正文为空")`

**影响**：RssSource视频源没有ruleContent时（依赖R5自动提取），转换为BookSource后视频无法播放。

**修复**：改动10——BookSource视频分支content为空时触发R5自动提取

**状态**：✅ 已在改动10中解决

#### DEFECT-8：ContentRule.sourceRegex未映射（V9发现MAJOR）

**问题**：ContentRule.sourceRegex用于BackstageWebView资源嗅探（拦截WebView请求匹配正则返回资源URL）。音频源和部分视频源依赖此功能。RssSource无对应字段。

**源码铁证**：WebBook.kt L442-444 `sourceRegex = contentRule.sourceRegex`传给AnalyzeUrl；BackstageWebView.kt L64构造函数接收sourceRegex参数

**影响**：音频书源→订阅源后音频URL无法通过嗅探获取；部分视频源也无法嗅探视频URL。

**修复**：改动11——RssSource新增ruleSourceRegex字段 + Rss.kt传sourceRegex参数

**状态**：✅ 已在改动11中解决

#### DEFECT-9：音频源评级虚高（V9发现MAJOR）

**问题**：V8将"书源→订阅源(音频)"评级为★★★★★，但RssSource无音频类型（type只支持0/1/2），AudioPlay只支持BookSource。

**源码铁证**：AudioPlay.kt L76 `var bookSource: BookSource? = null`；RssSource.type定义0(网页)/1(图片)/2(视频)

**影响**：音频书源转订阅源后，音频URL可获取但AudioPlay播放体验丢失，降级为WebView文本展示。

**修复**：无法通过字段映射修复（RssSource无音频类型是架构限制）。评级修正为★★★★☆。

**状态**：⚠️ 架构限制，无法100%弥补

### 待明确项（需在设计文档中补充说明）

#### CLARIFY-1：转换后新源名称生成规则

**决策**：自动在原sourceName后追加"(订阅版)"或"(书版)"后缀，用户可在预览对话框中修改。

#### CLARIFY-2：转换后新源URL生成规则

**决策**：自动在原sourceUrl后追加`#convert_{timestamp}`后缀，确保不与已有源冲突。timestamp使用System.currentTimeMillis()/1000。

#### CLARIFY-3：批量转换时URL冲突处理

**决策**：批量转换时，如果目标源URL已存在（冲突检测），自动追加后缀避免覆盖，并在结果汇总中提示"源XXX因URL冲突已自动重命名"。

### 待分析项（需进一步验证但不阻塞实施）

#### ANALYZE-1：智能TocRule生成后的运行时验证（V7深度修正）

**V6结论**：✅ 完全兼容

**V7修正**：⚠️ **V6结论错误！**

V6仅验证了AnalyzeRule的解析方式兼容性（getElements/getString），但**遗漏了最关键的一步：BookChapterList在哪 个页面上执行TocRule**。

**V7深度验证**：
- BookSource运行时流程：探索→点击→BookInfo→BookChapterList
- BookChapterList在tocUrl页面上执行（WebBook.kt L314-368）
- 如果tocUrl=articleUrl（文章内容页），TocRule.chapterList=ruleArticles在该页面上找不到文章列表元素
- **V6的智能TocRule无法工作，因为没有设置BookInfoRule.tocUrl指向sortUrl页面**

**V7修复**：改动6——BookInfoRule.tocUrl = `@js:'${firstSortUrl}'`，使tocUrl指向sortUrl页面

**V7修正后结论**：✅ 完全兼容（前提是BookInfoRule.tocUrl正确设置）

#### ANALYZE-2：视频多线路切换时routeContentRule的运行时验证

**问题**：VideoPlay.startPlay()中BookSource分支新增的routeRule多线路逻辑，切换线路时是否能正确获取不同线路的内容？

**深度验证结论**：⚠️ **需要调整方案**

源码级验证发现关键问题：
- RssSource多线路：`getContentAwait()`中先获取正文HTML → 解析routeRule获取线路名 → 解析ruleEpisodes获取集数列表 → 返回嵌套JSON
- BookSource视频：`startPlay()`中先获取目录(TocRule) → 选择章节 → WebBook.getContent()获取正文 → 构造播放URL

**核心差异**：BookSource视频播放的入口是"选择章节"，而不是"选择线路"。视频书源没有"线路"的概念，每个章节的播放URL由ContentRule.content规则从正文页面解析而来。

**修正方案**：BookSource的视频多线路支持不能简单照搬RssSource的routeRule/ruleEpisodes模式。更合理的方案是：

**方案A（推荐）**：routeRule解析线路列表，routeContentRule指定不同线路对应的内容解析规则。切换线路时，用routeContentRule替代ContentRule.content重新解析正文页面HTML，获取不同线路的播放URL。
- 优点：复用已获取的正文HTML，无需额外网络请求
- 改动：VideoPlay中切换线路时，用routeContentRule解析已有的正文HTML，而非重新请求

**方案B**：routeRule解析线路列表，每个线路对应不同的URL模板。切换线路时重新请求正文页面。
- 优点：最完整的线路切换
- 缺点：需要额外网络请求，增加延迟

**建议先用方案A**，因为多数视频站点的线路切换只是解析规则不同，URL相同。

### 设计文档完整性检查

| 检查项 | V6状态 | V7状态 | 说明 |
|--------|--------|--------|------|
| 5个源码改动方案 | ✅ 完整 | ✅ 完整 | 含代码片段+安全性验证 |
| UI入口设计 | ✅ 完整 | ✅ 完整 | 4入口+预览对话框+批量转换 |
| 运行时行为差异分析 | ✅ 完整 | ✅ 完整 | 8项差异+CRITICAL/MAJOR/MINOR评级 |
| 数据库Migration | ✅ 完整 | ✅ 完整 | 合并为1个migration(101→105) |
| File Change List | ✅ 完整 | ✅ 完整 | UI层12文件+源码改动层7文件 |
| URL冲突处理 | ✅ 已补充 | ✅ 已解决 | BLOCK-1已解决 |
| 编辑界面适配 | ⚠️ 最小方案 | ⚠️ 最小方案 | P0通过预览对话框编辑，P1编辑界面适配可选 |
| 新源名称/URL生成 | ✅ 已补充 | ✅ 已补充 | CLARIFY-1/2/3已明确 |
| **BookInfoRule.tocUrl与TocRule配合** | ❌ **缺失** | ✅ **已修复** | **V7改动6：BookInfoRule+TocRule联合生成** |
| **nextTocUrl映射** | ❌ **缺失** | ✅ **已修复** | **V7改动6：ruleNextPage→nextTocUrl** |
| **字段映射一致性** | ❌ **错误** | ✅ **已修正** | **V7：nextContentUrl→ruleNextContentUrl，非ruleNextPage** |
| **3个CRITICAL缺陷详情** | ❌ **未发现** | ✅ **已记录** | **V7 DEFECT-1/2/3** |

## Risk Assessment

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 订阅源→书源TocRule在错误页面上执行 | 高(V6) | 致命 | **V7改动6**：BookInfoRule.tocUrl指向sortUrl，确保TocRule在正确页面上执行 |
| 订阅源→书源分页目录丢失 | 高(V6) | 致命 | **V7改动6**：TocRule.nextTocUrl = ruleNextPage，对齐BookChapterList分页逻辑 |
| 字段映射nextContentUrl混淆 | 高(V6) | 重大 | **V7修正**：nextContentUrl→ruleNextContentUrl(内容分页)，ruleNextPage→nextTocUrl(列表分页) |
| 订阅源→书源无TocRule | 高 | 致命 | 智能TocRule生成（ruleArticles→chapterList） |
| 书源→订阅源正文含广告 | 中 | 重大 | 改动5：RssSource.ruleReplaceRegex+Rss.kt替换步骤 |
| 书源→订阅源长文章缺分页 | 高 | 致命 | 改动4：RssSource.ruleNextContentUrl+Rss.kt分页循环 |
| 视频源多线路丢失 | 高 | 致命(视频) | 改动2：ContentRule.routeRule+routeContentRule+VideoPlay读取 |
| 智能TocRule不适用 | 中 | 重大 | 预览中提示"自动生成的目录规则可能需要调整" |
| 用户不理解转换后果 | 高 | 重大 | 可用性评估+颜色标记+二次确认 |
| 新增4个RssSource字段的migration风险 | 低 | 中等 | 合并为1个migration(101→105)，一次性添加4列 |
| 分页循环死循环 | 低 | 致命 | nextUrlList去重检查+最大循环次数限制(10页) |
| BookInfoRule.tocUrl的@js:规则不生效 | 低 | 重大 | AnalyzeRule已支持@js:标签，但需真机验证 |
