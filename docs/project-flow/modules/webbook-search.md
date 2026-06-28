# WebBook 搜索与网络书模块

> 网络书籍获取的核心模块——WebBook 单例处理所有网络书操作，SearchModel 负责多书源并发搜索调度。

---

## 搜索全链路流程图

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
sequenceDiagram
    participant UI as "用户界面"
    participant SM as "SearchModel<br/>搜索调度器"
    participant WB as "WebBook<br/>单书源搜索"
    participant AU as "AnalyzeUrl<br/>URL模板引擎"
    participant NET as "OkHttp<br/>网络层"
    participant BL as "BookList<br/>结果解析"
    participant DB as "Room数据库"

    UI->>SM: search(searchKey)
    activate SM

    SM->>SM: "1.分组书源<br/>按启用/分组/权重排序"
    SM->>SM: "2.检查缓存<br/>换页跳过已搜索书源"

    par 并发搜索 (N<=9线程)
        SM->>WB: searchBookAwait(source1, key, page)
        activate WB
        WB->>AU: getSearchUrl(key, page)
        AU-->>WB: "构建完整URL+Headers"
        WB->>NET: HTTP GET/POST
        NET-->>WB: "Response body"
        WB->>BL: analyzeBookList(body)
        BL->>BL: "规则解析 name/author/cover/..."
        BL-->>WB: "List<SearchBook>"
    WB-->>SM: "搜索结果列表"
    deactivate WB
    and
        SM->>WB: searchBookAwait(source2, key, page)
        activate WB
        WB->>NET: HTTP GET/POST
        NET-->>WB: Response
        WB->>BL: analyzeBookList
        BL-->>WB: "List<SearchBook>"
        WB-->>SM: "搜索结果列表"
        deactivate WB
    and
        SM->>WB: searchBookAwait(sourceN, key, page)
        activate WB
        WB->>NET: HTTP GET/POST
        NET-->>WB: Response
        WB->>BL: analyzeBookList
        BL-->>WB: "List<SearchBook>"
        WB-->>SM: "搜索结果列表"
        deactivate WB
    end

    SM->>SM: "3.四分类聚合去重<br/>精确>标签>包含>其他"

    SM->>DB: "4.更新搜索缓存"
    DB-->>SM: "缓存写入完成"

    SM-->>UI: "回调通知更新<br/>onSuccess/onError"
    deactivate SM
```

---

## 四分类去重流程图

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
flowchart TD
    ALL["所有书源的搜索结果<br/>List&lt;SearchBook&gt;"]

    ALL --> CAT1["第1类: 精确匹配<br/>name==searchKey<br/>author==searchKey"]
    ALL --> CAT2["第2类: 标签匹配<br/>kind?.contains(searchKey)==true"]
    ALL --> CAT3["第3类: 包含匹配<br/>name.contains(searchKey)<br/>author.contains(searchKey)"]
    ALL --> CAT4["第4类: 其他结果<br/>不匹配任何条件"]

    CAT1 --> DEDUP{"去重: 按 name+author<br/>HashSet 判重"}
    CAT2 --> DEDUP
    CAT3 --> DEDUP
    CAT4 --> DEDUP

    DEDUP --> MERGE["合并: cat1 + cat2 + cat3 + cat4<br/>按优先级排列"]
    MERGE --> UI["UI 显示搜索结果"]
```

---

## 1. 架构总览

```
用户搜索请求
    │
    ▼
SearchModel.search(searchKey)          ← 搜索调度器
    │
    ├─ 书源分组 (bookSourceParts)       ← 按启用/分组/权重排列
    │
    ├─ Flow + mapParallelSafe(N)       ← 固定并发数(N≤9)执行搜索
    │    │
    │    └─ WebBook.searchBookAwait()   ← 单书源搜索
    │         │
    │         ├─ AnalyzeUrl → 构建请求
    │         ├─ loginCheckJs → 登录检测
    │         ├─ checkRedirect → 重定向检测
    │         └─ BookList.analyzeBookList() → 解析结果
    │
    ├─ 四分类聚合去重 (mergeItems)      ← 精确 > 标签 > 包含 > 其他
    │
    └─ 回调通知 UI 更新
```

---

## 2. WebBook 双版本模式

[WebBook.kt:30](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L30)

每个功能提供两个版本：

```kotlin
// async 封装版 — ViewModel/UI 直接调用
fun searchBook(scope, source, key, page) { ... }

// 纯挂起版 — 其他 model 层内部调用
suspend fun searchBookAwait(scope, source, key, page) { ... }
```

| 功能 | async版 | await版 | 说明 |
|------|---------|---------|------|
| 搜索 | `searchBook()` | `searchBookAwait()` | 按关键词搜索 |
| 发现 | `exploreBook()` | `exploreBookAwait()` | 发现页浏览 |
| 详情 | `getBookInfo()` | `getBookInfoAwait()` | 获取书籍详情 |
| 目录 | `getChapterList()` | `getChapterListAwait()` | 获取章节列表 |
| 正文 | `getContent()` | `getContentAwait()` | 获取章节正文 |
| 精准搜索 | `preciseSearch()` | `preciseSearchAwait()` | 精确书名搜索 |

**核心约定**：
- 统一通过 `currentCoroutineContext()` 传递协程上下文
- `searchBookAwait` 系列使用 `CoroutineScope(SupervisorJob() + currentCoroutineContext())` 创建独立作用域
- 所有网络请求最终调用 `HttpHelper.getStrResponseAwait()`

---

## 3. 搜索完整链路

[WebBook.kt:49-107](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L49-L107)

### 3.1 searchBookAwait 流程

```
searchBookAwait(bookSource, key, page, filter):
  1. 检查 searchUrl 是否为空 → 空则抛异常
  2. 构建 RuleData(sourceUrl=searchUrl, baseUrl=bookSourceUrl, key, page)
  3. AnalyzeUrl → 模板变量注入 ({{key}}/{{page}})
  4. 发起 HTTP 请求 (OkHttp + Cronet)
  5. loginCheckJs → 登录状态检测JS（如果配置了loginUrl）
  6. checkRedirect → 重定向检测
  7. BookList.analyzeBookList(ruleSearch, html, baseUrl, source)
     → 使用搜索规则解析 HTML → 返回 List<SearchBook>
  8. 精确搜索过滤 (filter_):
     若 filter 中有 name 参数 → 仅保留 name 包含该关键词的结果
  9. 精准搜索提前终止 (shouldBreak):
     精确搜索结果命中 → 不再搜索后续书源
 10. 返回 SearchBook 列表
```

### 3.2 搜索页面支持

```
searchUrl 模板变量:
  {{key}}   → 搜索关键词
  {{page}}  → 页码（多页搜索时递增）

多页搜索:
  通过 page 参数控制，书源需支持分页参数
  或通过 ruleNextPage 规则提取"下一页"链接
```

---

## 4. SearchModel 并发调度

[SearchModel.kt:34](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt#L34)

### 4.1 核心状态

```kotlin
class SearchModel {
    var searchKey: String            // 当前搜索关键词
    var searchPage: Int = 0          // 当前页码
    var searchId: Long = 0           // 搜索会话ID（外部传入，0=取消）
    // searchId 由调用方传入，非 SearchModel 自行生成
    // searchId 变化 → 新搜索开始；searchId 不变 → searchPage 递增（换页）

    // 书源分组列表
    var bookSourceParts: List<BookSourcePart>

    // 搜索结果（四分类聚合后的最终结果）
    val searchBooks = arrayListOf<SearchBook>()

    // 并发控制
    var threadCount: Int             // 用户配置的并发数
    val MAX_THREAD = 9               // 硬上限
    var workingState = MutableStateFlow(true)  // 暂停/恢复控制
}
```

### 4.2 搜索流核心循环

[SearchModel.kt:52-114](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt#L52-L114)

```
search(searchKey):
  1. 初始化:
     - 判断关键词是否变化 (sameKey)
     - 若关键词变化 → 重置 page=0, 清空 searchBooks
     - searchId 由外部调用方传入（非 SearchModel 自行生成）
     - searchId 变化 → 新搜索开始；searchId 不变 → 换页

  2. 若 sameKey → 加载下一页 (page++)
     若 needMerge → 需要合并模式（搜索前不清空已有结果）

  3. 启动搜索流 (_search_flow):
     for 每个 BookSourcePart 中的每个 BookSource:
       ├─ await _wait_if_paused()         ← workingState 检查
       ├─ search_one_source(source)       ← 异步超时30s
       ├─ _release_html_data(items)       ← 释放 HTML 缓存
       ├─ _insert_search_results(items)   ← 写入 searchBook 表
       ├─ _merge_items(items, precision)  ← 四分类聚合去重
       └─ callback.on_search_success()    ← 通知 UI 更新
```

### 4.3 并发控制

```
并发策略:
  1. threadCount = min(用户配置, MAX_THREAD=9)
  2. 使用 flow{}.mapParallelSafe(threadCount){} 控制并发度
     - mapParallelSafe 基于 Channel 实现，非 Semaphore
     - 线程池: Executors.newFixedThreadPool(min(threadCount, AppConst.MAX_THREAD)).asCoroutineDispatcher()
  3. 每个书源超时 30000ms（硬编码）

暂停/恢复:
  - workingState = MutableStateFlow(true)
  - 每个书源搜索前检查 workingState
  - false 时阻塞等待，直到 resume() 设为 true

取消:
  - searchId = 0 → 所有协程检测到后自动返回
```

---

## 5. 四分类聚合去重

[SearchModel.kt:116-197](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt#L116-L197)

### 5.1 去重键

```
去重依据: 直接字符串相等（name + author）
具体规则: 对新旧书籍的 name 和 author 做直接字符串比较（pBook.name == nBook.name && pBook.author == nBook.author）
若同名同作者 → 视为同一本书，调用 pBook.addOrigin(nBook.origin) 合并书源列表
```

### 5.2 四分类排序

搜索结果按匹配质量分为四类：

```
优先级从高到低:
  1. 精确匹配 (equalData) — name == searchKey || author == searchKey
  2. 标签匹配 (tagsData)  — kind?.contains(searchKey) == true
  3. 包含匹配 (containsData) — name.contains(searchKey) || author.contains(searchKey)
  4. 其他 (otherData)      — 都不满足
```

当 `precision=True`（精确搜索）时，`otherData` 组被丢弃。

### 5.3 合并算法

```
_merge_items(newItems, precision):
  对每个 newItem:
    1. 在已有 searchBooks 中查找同名同作者的书
    2. 找到 → 更新 originList（合并书源列表）+ 保留最优条目
    3. 未找到 → 添加到对应分类列表

  最终排序: [精确匹配] + [标签匹配] + [包含匹配] + [其他]
  各类内部: 按 originList.size 降序（书源越多的排越前）
```

### 5.4 合并效果示例

```
搜索关键词："三体"

▼ 来自 A 书源的结果：
  { name: "三体", author: "刘慈欣", origin: "sourceA" }
  { name: "三体X", author: "宝树", origin: "sourceA" }

▼ 来自 B 书源的结果：
  { name: "三体", author: "刘慈欣", origin: "sourceB" }
  { name: "三体·死神永生", author: "刘慈欣", origin: "sourceB" }

▼ 合并后：
  equalData:     [{ name: "三体", author: "刘慈欣", origin: "sourceA,sourceB", origin_list: 2 }]
  containsData:  [{ name: "三体X", author: "宝树", origin: "sourceA", origin_list: 1 }]
                 [{ name: "三体·死神永生", author: "刘慈欣", origin: "sourceB", origin_list: 1 }]

▼ 排序（按 origin 数量降序）：
  [
    { name: "三体", origin: "sourceA,sourceB" },           # 2 个书源找到
    { name: "三体X", origin: "sourceA" },                   # 1 个书源
    { name: "三体·死神永生", origin: "sourceB" },           # 1 个书源
  ]
```

---

## 6. 其他核心操作

### 6.1 发现页 — exploreBookAwait

[WebBook.kt:124-175](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L124-L175)

```
与搜索的区别:
  - 使用 sourceUrl + exploreInfoMap（而非 searchUrl）
  - exploreInfoMap 从 BookSource.exploreInfoMapList 获取
  - 不传递 filter/shouldBreak 参数
  - 使用 ruleExplore 规则解析
```

### 6.2 书籍详情 — getBookInfoAwait

[WebBook.kt:192-252](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L192-L252)

```
流程:
  1. book.removeAllBookType() + addType(source.getBookType())
  2. 检查缓存的 infoHtml → 有则跳过网络请求直接解析
  3. 无缓存 → AnalyzeUrl(bookUrl, baseUrl=bookSourceUrl) → HTTP请求
  4. loginCheckJs 登录检测
  5. BookInfo.analyzeBookInfo(book, ruleBookInfo, html)
```

### 6.3 目录获取 — getChapterListAwait

[WebBook.kt:284-351](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L284-L351)

```
流程:
  1. 可选: runPreUpdateJs() — 更新前执行 JS
  2. 检查缓存的 tocHtml → 有则跳过网络请求
  3. 无缓存 → AnalyzeUrl(tocUrl, baseUrl=bookUrl) → HTTP请求
  4. BookChapterList.analyzeChapterList(book, ruleToc, html)
```

### 6.4 正文获取 — getContentAwait

[WebBook.kt:379-455](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L379-L455)

```
流程:
  1. AnalyzeUrl(chapter.url, baseUrl=baseUrl) → HTTP请求
  2. loginCheckJs 登录检测
  3. checkRedirect 重定向检测
  4. ruleContent 规则解析 HTML → 正文字符串
  5. ContentProcessor.getContent() → 七步管线处理
  6. 返回 BookContent(textList, ...)

分页支持:
  - 单页模式: ruleNextPage 不为空 → 顺序翻页获取
  - 多页并发: webJs 不为空 → 并发获取所有分页
```

### 6.5 精准搜索 — preciseSearch / preciseSearchAwait

[WebBook.kt:460-499](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L460-L499)

```
用途:
  导入书籍时自动匹配书源——按书名+作者精确匹配，找到即停

preciseSearch(scope, bookSourceParts, name, author):
  遍历 bookSourceParts 中的每个书源:
    1. source = part.getBookSource() ?: continue
    2. book = preciseSearchAwait(source, name, author).getOrNull()
    3. book != null → 返回 Pair(book, source)
  全部未命中 → 抛出 NoStackTraceException("没有搜索到<name>author")

preciseSearchAwait(bookSource, name, author):
  1. ensureActive() 检查协程活性
  2. searchBookAwait(bookSource, name,
       filter = { fName, fAuthor, _ -> fName == name && fAuthor == author },
       shouldBreak = { it > 0 })
     → filter: 仅保留书名+作者完全匹配的结果
     → shouldBreak: 命中即提前终止，不再搜索后续书源
  3. firstOrNull()?.toBook() → 转为 Book 对象
  4. 未找到 → 抛出 NoStackTraceException
  5. onFailure → ensureActive() 确保取消传播

返回值:
  - preciseSearch: Coroutine<Pair<Book, BookSource>>
  - preciseSearchAwait: Result<Book>

典型调用场景:
  - 书籍导入时自动匹配书源
  - 本地书籍关联在线书源
```

### 6.6 预更新 JS — runPreUpdateJs（内部方法）

[WebBook.kt:270-282](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L270-L282)

```
用途:
  getChapterListAwait 内部调用，在获取目录前执行书源配置的 preUpdateJs

runPreUpdateJs(bookSource, book, isFromBookInfo=false):
  1. 读取 bookSource.ruleToc?.preUpdateJs
  2. 若为空 → 跳过，返回 Result.success
  3. 非空 → AnalyzeRule(book, bookSource, true, isFromBookInfo)
       .setCoroutineContext(currentCoroutineContext())
       .evalJS(preUpdateJs)
  4. 失败 → AppLog.put("执行preUpdateJs规则失败") + ensureActive()

注意:
  - 非外部 API，由 getChapterListAwait 通过 runPerJs 参数控制是否执行
  - preUpdateJs 可修改 book 对象状态（如动态设置 tocUrl）
  - 执行失败不阻断目录获取流程，仅记录日志
```

---

## 7. BookList 搜索结果解析

[BookList.kt:35-151](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookList.kt#L35-L151)

```
analyzeBookList(ruleSearch, html, baseUrl, source):
  1. 用 ruleSearch.bookList 规则提取每个书籍条目
  2. 对每个条目依次提取: name/author/intro/kind/lastChapter/
     updateTime/bookUrl/coverUrl/wordCount
  3. 每个字段的提取规则独立，支持五种解析模式
  4. 返回 List<SearchBook>
```

---

## 8. 数据模型

### 8.1 Book / Chapter / SearchResult

```python
@dataclass
class Book:
    book_url: str                    # 书籍唯一 URL
    toc_url: str                     # 目录 URL
    origin: str                      # 书源 URL
    name: str                        # 书名
    author: str                      # 作者
    cover_url: str                   # 封面 URL
    intro: str                       # 简介
    kind: str                        # 分类
    word_count: str                  # 字数
    latest_chapter_title: str        # 最新章节标题

    # 运行时的状态字段
    info_html: str | None = None     # 缓存的信息页 HTML
    toc_html: str | None = None      # 缓存的目录页 HTML
    chapter_list: list[Chapter] | None = None

    def add_type(self, book_type: str):
        """标记书籍类型（来源于 bookSource.getBookType()）"""

    def remove_all_book_type(self):
        """清除所有书籍类型标记"""


@dataclass
class Chapter:
    url: str                         # 章节 URL（绝对或相对）
    title: str                       # 章节标题
    is_volume: bool = False          # 是否是一级卷标
    is_vip: bool = False             # 是否付费
    update_time: str | None = None   # 更新时间
    absolute_url: str = ""           # 绝对 URL（由 getAbsoluteURL() 计算）


@dataclass
class SearchResult:
    name: str
    author: str
    kind: str
    cover_url: str
    intro: str
    book_url: str
    latest_chapter_title: str
    word_count: str
    source: BookSource
```

### 8.2 BookSource 及规则结构

```python
@dataclass
class BookSource:
    book_source_url: str             # 书源 URL
    source_url: str                  # 发现页 URL (explore)
    search_url: str                  # 搜索 URL 模板
    login_check_js: str             # 登录检测 JS
    book_type: int                   # 书籍类型
    rule_search: SearchRule
    rule_explore: ExploreRule
    rule_book_info: BookInfoRule
    rule_toc: TocRule
    rule_content: ContentRule


@dataclass
class SearchRule:
    book_list: str; name: str; author: str; kind: str
    cover_url: str; intro: str; book_url: str
    last_chapter: str; word_count: str

@dataclass
class ExploreRule:
    book_list: str; name: str; author: str; kind: str
    cover_url: str; intro: str; book_url: str
    last_chapter: str; word_count: str

@dataclass
class BookInfoRule:
    init: str                        # 初始化 JS
    name: str; author: str; cover_url: str; intro: str
    kind: str; last_chapter: str; toc_url: str; word_count: str

@dataclass
class TocRule:
    pre_update_js: str              # 预更新 JS
    chapter_list: str; chapter_url: str; chapter_name: str
    is_volume: str; is_vip: str; update_time: str

@dataclass
class ContentRule:
    content: str                     # 正文规则
    web_js: str                      # 页面内嵌 JS
    source_regex: str                # 源正则
    next_content_url: str            # 下一页 URL 规则
    replace_regex: str              # 替换正则列表
    sub_content: str                # 副文本规则

@dataclass
class RuleData:
    source_url: str = ""
    base_url: str = ""
    key: str = ""
    page: int = 0
```

---

## 9. BookInfo 九字段解析

[BookInfo.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookInfo.kt)

```
analyzeBookInfo(book, ruleBookInfo, html, canRename=True):
  字段解析顺序（与 Legado 源码一致）:
    1. init (初始化 JS，在解析前执行)
    2. name
    3. author
    4. coverUrl
    5. intro
    6. kind
    7. lastChapter
    8. tocUrl
    9. wordCount

  canRename 参数:
    - True（默认）: 分析结果覆盖 Book 现有字段
    - False: 仅填充 Book 中为空的字段（不覆盖已有值）

  init JS 执行:
    1. 执行 rule.init JS
    2. JS 可能修改 DOM，重新获取 HTML
    3. 再用新 HTML 解析后续字段
```

---

## 10. BookChapterList 五字段提取

[BookChapterList.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookChapterList.kt)

```
analyzeChapterList(book, ruleToc, html):
  1. 执行 tocRule.preUpdateJs（若存在）
  2. 使用 tocRule.chapterList 规则提取章节元素列表
  3. 遍历每个元素提取:
     - chapterUrl（必须）
     - chapterName（必须）
     - isVolume（可选）
     - isVip（可选）
     - updateTime（可选）
  4. 调用 chapter.getAbsoluteURL() 将相对 URL 转为绝对 URL
```

---

## 11. BookContent 五步管线

[BookContent.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookContent.kt)

```
analyzeContent(html, ruleContent, chapter, book, source):
  处理步骤（按顺序）:
    1. content 规则提取正文
    2. nextContentUrl 分页处理
       - 串行模式: pageUrlCount（有限页数，串行请求）
       - 并行模式: pageUrl（无限制，并行请求）
    3. subContent 副文本处理
       - 歌词（LRC 格式）、弹幕、评论区/段评、脚注
       - 提取到的副文本追加到正文末尾
    4. replaceRegex 替换
       - 支持 $1、$2 等反向引用
       - 正则编译失败则跳过
    5. htmlFormatter + unescapeHtml
       - 移除 <script>、<style> 标签
       - 将 <br>、<p>、<div> 等块级标签转为换行
       - 保留 <a> 标签（提取 href + 文本）
       - 处理 <img> 标签（提取 src）
       - HTML 实体反转义
```

---

## 12. AnalyzeRule 概览

Legado 规则引擎的核心，所有字段提取最终收敛到此：

```
AnalyzeRule 支持规则类型（自动检测）:
  - @js: — JavaScript 表达式
  - CSS 选择器 — 如 div.title、.book-name a
  - XPath — 如 //div[@class='title']
  - JSONPath — 如 $.data.name
  - 正则 — 如 <title>(.*?)</title>

rule 前缀约定:
  - "@js:" → 执行 JavaScript
  - "//" 或 "/" → XPath
  - "$." → JSONPath
  - 其他 → CSS 选择器 / 正则自动检测

JS 执行环境注入对象:
  - book — 当前 Book 对象
  - bookSource — 当前 BookSource
  - java — 某些 Java API 的桥接
  - result — 当前的 HTML 文档
```

---

## 13. 异常处理策略

| 场景 | 异常类型 | 处理方式 |
|------|----------|----------|
| searchUrl 为空 | `NoStackTraceException` | 静默返回空列表 |
| 网络请求失败 | `IOException` | 上层捕获，显示网络错误 |
| 规则解析失败（单个字段） | `Exception` | 跳过该字段，继续解析 |
| 规则解析失败（整个条目） | `Exception` | 跳过该条目，继续处理其余 |
| 登录检测 JS 抛出 | `Exception` | 跳过登录检测，使用原始响应 |
| 分页请求失败 | `IOException` | 已获取的正文依然返回，缺失分页 |
| JS 执行异常 | `ScriptException` | 规则视为无效，返回空字符串 |

---

## 14. SearchModel 状态机

### 14.1 搜索生命周期

```
状态转换:
  IDLE → SEARCHING → FINISHED
                 ↘ CANCELLED
  SEARCHING ⇄ PAUSED (workingState 控制)

search(key, searchId):
  - 新搜索（searchId != mSearchId）: 重置所有状态，获取书源列表，初始化线程池
  - 继续搜索（searchId == mSearchId）: 页码 +1，复用已有线程池和书源列表

pause():   workingState = false → 阻塞搜索循环
resume():  workingState = true  → 恢复搜索循环
cancel():  close() + onSearchCancel()
close():   searchJob.cancel() + searchPool.close() + mSearchId = 0
```

### 14.2 CallBack 接口

```python
class CallBack(ABC):
    def get_search_scope(self) -> SearchScope: ...
    def on_search_start(self): ...
    def on_search_success(self, search_books: list[SearchBook]): ...
    def on_search_finish(self, is_empty: bool, has_more: bool): ...
    def on_search_cancel(self, exception: Exception = None): ...
```

### 14.3 SearchScope 搜索范围

```
SearchScope 枚举:
  - ALL (0):     搜索所有分组
  - CURRENT (1): 只搜索当前分组
  - MANUAL (2):  手动选择分组

BookSourcePart:
  - group: int = 0
  - book_sources: list[BookSource]
```

---

## 15. 搜索效率分析

### 15.1 并发控制参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 最大线程数 | 9 | `MAX_THREAD = 9`，硬编码上限 |
| 默认线程数 | `AppConfig.threadCount` | 用户可在设置中配置 |
| 书源超时 | 30 秒 | 每个书源独立超时，互不影响 |
| 暂停机制 | `MutableStateFlow(true)` | 挂起而非取消，可恢复 |

### 15.2 合并算法复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 四组分类 | O(N) | N = searchBooks 当前数量 |
| 新数据插入去重 | O(N·M) | M = newData 数量，每组内遍历查重 |
| 组内排序 | O(K·logK) | K = 每组元素数，按 origin 数量排序 |
| **整体** | O(N·M + K·logK) | 在合理范围内，N 通常 < 500 |

### 15.3 内存管理

- 每个搜索结果的 `releaseHtmlData()` 在入库后立即释放 HTML 字符串
- `searchBooks` 仅保留元数据（字段字符串），不保留原始 HTML
- 数据库中的 `searchBook` 表在每次新搜索前清空（或覆盖）

---

## 16. WebSocket 搜索结果推送

在 Python 后端重构中，SearchModel 的 CallBack 接口可通过 WebSocket 替代，实现实时搜索结果推送。

### 16.1 WebSocket 消息协议

```
消息类型:
  search_start:    { search_id, key, total_sources, page }
  search_progress: { search_id, source_url, source_name, results_count, completed, total }
  search_result:   { search_id, books: [SearchBookDTO], total_count }
  search_finish:   { search_id, is_empty, has_more }
  search_cancel:   { search_id, reason }

SearchBookDTO:
  name, author, kind, cover_url, intro, origin, origin_count,
  latest_chapter_title, word_count
```

### 16.2 前端消费示例（Vue3）

```typescript
interface SearchState {
  searchId: number
  key: string
  books: SearchBookDTO[]
  status: 'idle' | 'searching' | 'finished' | 'cancelled'
  progress: { completed: number; total: number }
  hasMore: boolean
}

// WebSocket onmessage 按 msg.type 分发:
// search_start   → 重置状态，显示搜索中
// search_result  → 增量更新结果列表
// search_progress → 更新进度
// search_finish  → 显示"搜索完成"状态
// search_cancel  → 显示取消状态
```

---

## 17. 完整调用链时序图

### 17.1 WebBook 核心操作时序图

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
sequenceDiagram
    participant C as Caller
    participant WB as WebBook
    participant AU as AnalyzeUrl
    participant HTTP as HttpHelper
    participant LC as LoginCheck
    participant RD as RedirectDetect
    participant P as Parser

    Note over C,P: 搜索流程 searchBookAwait
    C->>WB: searchBookAwait(bookSource, key)
    WB->>AU: AnalyzeUrl(searchUrl, key, page)
    AU-->>WB: requestConfig
    WB->>HTTP: getStrResponseAwait(config)
    HTTP-->>WB: response
    WB->>LC: loginCheckJs
    LC-->>WB: "response (可能重请求)"
    WB->>RD: checkRedirect
    RD-->>WB: log result
    WB->>P: BookList.analyzeBookList()
    P-->>WB: list[SearchResult]
    WB->>WB: filter by name
    WB->>WB: shouldBreak check
    WB-->>C: list[SearchResult]

    Note over C,P: 书籍信息流程 getBookInfoAwait
    C->>WB: getBookInfoAwait(book, source)
    WB->>WB: removeAllBookType + addType
    alt has infoHtml cache
        WB->>P: BookInfo.analyzeBookInfo(html)
    else
        WB->>AU: AnalyzeUrl(bookUrl)
        WB->>HTTP: getStrResponse
        WB->>LC: loginCheck
        WB->>P: BookInfo.analyzeBookInfo()
    end
    WB-->>C: Book

    Note over C,P: 正文流程 getContentAwait
    C->>WB: getContentAwait(chapter, book, source)
    alt content is empty
        WB-->>C: "chapter.absoluteUrl (音频)"
    else isVolume
        WB-->>C: "empty (卷标跳过)"
    else has tocHtml cache
        WB->>AU: AnalyzeUrl(url, body=tocHtml)
    else
        WB->>AU: AnalyzeUrl(chapterUrl, webJs, sourceRegex)
    end
    WB->>HTTP: getStrResponse
    WB->>LC: loginCheck
    WB->>P: BookContent.analyzeContent()
    P->>P: 1. content rule
    P->>P: 2. pagination
    P->>P: 3. subContent
    P->>P: 4. replaceRegex
    P->>P: 5. htmlFormatter + unescape
    P-->>WB: str
    WB-->>C: str
```

### 17.2 搜索并发时序图

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
sequenceDiagram
    participant U as "用户"
    participant UI as "搜索页面"
    participant WS as WebSocket
    participant SM as SearchModel
    participant WB as WebBook
    participant DB as "数据库"

    Note over U,DB: 新搜索流程
    U->>UI: "输入关键词，点击搜索"
    UI->>WS: connect & send { key }
    WS->>SM: search(key, searchId)

    SM->>SM: "重置状态，搜索ID递增"
    SM->>SM: "getBookSourceParts() 获取书源"
    SM->>SM: "initSearchPool() 创建线程池"

    Note over SM: 逐个发射书源，并行搜索

    par 书源1 (线程1)
        SM->>WB: searchBookAwait(source1, key)
        WB-->>SM: items1
    and 书源2 (线程2)
        SM->>WB: searchBookAwait(source2, key)
        WB-->>SM: items2
    and 书源3 (线程3)
        SM->>WB: searchBookAwait(source3, key)
        WB-->>SM: items3
    end

    Note over SM: threadCount=9, 每个书源30s超时

    SM->>SM: releaseHtmlData(items)
    SM->>DB: insertSearchResults(items)
    SM->>SM: mergeItems(items, precision)
    SM->>WS: { type: "search_result", books }
    WS->>UI: "增量更新搜索结果"

    Note over SM: 所有书源搜索完毕
    SM->>WS: { type: "search_finish", is_empty, has_more }
    WS->>UI: "搜索完成通知"
```

---

## 18. 关键配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| threadCount | 4 | 并发搜索线程数，最大9 |
| timeout | 30s | 单个书源搜索超时 |
| page 初始值 | 0 | 搜索起始页 |
| needMerge | false | 是否合并模式（追加结果不清空） |

---

## 19. 相关代码锚点

| 功能 | 文件 | 行号 |
|------|------|------|
| WebBook object 定义 | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L30 |
| searchBookAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L49-107 |
| exploreBookAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L124-175 |
| getBookInfoAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L192-252 |
| getChapterListAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L284-351 |
| getContentAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L379-455 |
| preciseSearch / preciseSearchAwait | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L460-499 |
| runPreUpdateJs | [WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) | L270-282 |
| SearchModel 类定义 | [SearchModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt) | L34 |
| 并发搜索核心 | [SearchModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt) | L52-114 |
| 四分类聚合去重 | [SearchModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/SearchModel.kt) | L116-197 |
| BookList 解析 | [BookList.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookList.kt) | L35-151 |
| BookInfo 解析 | [BookInfo.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookInfo.kt) | L1 |
| BookChapterList 解析 | [BookChapterList.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookChapterList.kt) | L1 |
| BookContent 解析 | [BookContent.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookContent.kt) | L1 |

---

## Python 重构参考

### P1. WebBook 单例入口

```python
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
import re
import json


class NoStackTraceException(Exception):
    """不需要堆栈跟踪的异常，用于空 searchUrl 等场景"""
    pass


class WebBook:
    """网书操作的单例入口"""

    # ============================================================
    # P1.1 搜索书籍 — searchBookAwait
    # ============================================================

    @staticmethod
    async def search_book_await(
        book_source: BookSource,
        key: str,
        page: int = 0,
        filter_: dict | None = None,
        should_break: Callable[[list[SearchResult]], bool] | None = None
    ) -> list[SearchResult]:
        if not book_source.search_url:
            raise NoStackTraceException("搜索源未配置搜索 URL")

        rule_data = RuleData(
            source_url=book_source.search_url,
            base_url=book_source.book_source_url,
            key=key, page=page
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)
        await _check_redirect(book_source, response)

        results = BookList.analyze_book_list(
            book_source.rule_search, response.html,
            book_source.book_source_url, book_source
        )

        if filter_:
            results = [r for r in results
                       if filter_.get("name", "") in r.name]  # 源码大小写敏感

        if should_break and should_break(results):
            return results

        return results

    # ============================================================
    # P1.2 发现书籍 — exploreBookAwait
    # ============================================================

    @staticmethod
    async def explore_book_await(
        book_source: BookSource,
        key: str, page: int = 0,
        explore_info_map: dict[str, str] = None
    ) -> list[SearchResult]:
        source_url = explore_info_map.get(key, "") if explore_info_map else ""
        if not source_url:
            return []

        rule_data = RuleData(
            source_url=source_url,
            base_url=book_source.source_url,
            key=key, page=page
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        results = BookList.analyze_book_list(
            book_source.rule_explore, response.html,
            book_source.source_url, book_source
        )
        return results

    # ============================================================
    # P1.3 获取书籍详细信息 — getBookInfoAwait
    # ============================================================

    @staticmethod
    async def get_book_info_await(book: Book, book_source: BookSource) -> Book:
        book.remove_all_book_type()
        book.add_type(book_source.book_type)

        if book.info_html:
            BookInfo.analyze_book_info(book, book_source.rule_book_info, book.info_html)
            return book

        rule_data = RuleData(
            source_url=book.book_url,
            base_url=book_source.book_source_url
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        BookInfo.analyze_book_info(book, book_source.rule_book_info, response.html)
        return book

    # ============================================================
    # P1.4 获取目录列表 — getChapterListAwait
    # ============================================================

    @staticmethod
    async def get_chapter_list_await(
        book: Book, book_source: BookSource,
        run_pre_update: bool = True
    ) -> list[Chapter]:
        if run_pre_update:
            await WebBook.run_pre_update_js(book, book_source)

        if book.toc_html:
            BookChapterList.analyze_chapter_list(book, book_source.rule_toc, book.toc_html)
            return book.chapter_list

        rule_data = RuleData(source_url=book.toc_url, base_url=book.book_url)
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        BookChapterList.analyze_chapter_list(book, book_source.rule_toc, response.html)
        return book.chapter_list

    # ============================================================
    # P1.5 获取章节正文 — getContentAwait
    # ============================================================

    @staticmethod
    async def get_content_await(
        chapter: Chapter, book: Book, book_source: BookSource
    ) -> str:
        content_rule = book_source.rule_content

        if not content_rule.content:
            return chapter.get_absolute_url()

        if chapter.is_volume and chapter.url.startswith(chapter.title):
            return ""

        body = book.toc_html if book.toc_html else None

        rule_data = RuleData(
            source_url=chapter.get_absolute_url(),
            base_url=book.toc_url,
            js_str=content_rule.web_js,
            source_regex=content_rule.source_regex
        )
        if body:
            rule_data.body = body

        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        content = BookContent.analyze_content(
            response.html, content_rule, chapter, book, book_source
        )
        return content

    # ============================================================
    # P1.6 精准搜索 — preciseSearchAwait
    # ============================================================

    @staticmethod
    async def precise_search_await(book_source: BookSource, key: str) -> Book | None:
        results = await WebBook.search_book_await(
            book_source, key,
            filter_={"name": key},
            should_break=lambda r: len(r) > 0
        )
        if not results:
            return None
        return results[0].to_book()

    # ============================================================
    # P1.7 内部方法 — 登录检测 / 重定向检测
    # ============================================================

    @staticmethod
    async def _login_check(book_source, response):
        login_js = book_source.login_check_js
        if not login_js:
            return response
        analyze_rule = AnalyzeRule(response, book_source)
        result = analyze_rule.eval_js(login_js)
        if result:
            login_response = await http_get(result)
            response = await http_get(response.original_url)
        return response

    @staticmethod
    async def _check_redirect(book_source, response):
        raw = response.raw
        prior = getattr(raw, "prior_response", None)
        if prior and prior.is_redirect:
            logger.debug("[WebBook] 书源 %s 发生重定向", book_source.book_source_url)
```

### P2. BookInfo 九字段解析

```python
class BookInfo:
    @staticmethod
    def analyze_book_info(book: Book, rule: BookInfoRule, html: str,
                          can_rename: bool = True) -> Book:
        # Step 1: 执行 init JS
        if rule.init:
            analyze_rule = AnalyzeRule(book, html)
            analyze_rule.eval_js(rule.init)
            html = analyze_rule.get_current_html()

        # Step 2: 提取各字段
        analyze_rule = AnalyzeRule(html, base_url=book.book_url)
        fields = {
            "name": rule.name, "author": rule.author,
            "cover_url": rule.cover_url, "intro": rule.intro,
            "kind": rule.kind, "latest_chapter_title": rule.last_chapter,
            "toc_url": rule.toc_url, "word_count": rule.word_count,
        }

        for field_name, rule_expr in fields.items():
            if not rule_expr:
                continue
            value = analyze_rule.extract_string(rule_expr)
            if can_rename:
                setattr(book, field_name, value)
            else:
                existing = getattr(book, field_name, None)
                if not existing:
                    setattr(book, field_name, value)
        return book
```

### P3. BookContent 五步管线

```python
class BookContent:
    @staticmethod
    def analyze_content(html, rule, chapter, book, book_source) -> str:
        # Step 1: content 规则提取正文
        content = _extract_content(html, rule.content, chapter.get_absolute_url())

        # Step 2: nextContentUrl 分页处理
        if rule.next_content_url:
            content = BookContent._process_pagination(content, rule, chapter, book, book_source)

        # Step 3: subContent 副文本处理
        if rule.sub_content:
            content = BookContent._process_sub_content(content, rule.sub_content, html)

        # Step 4: replaceRegex 替换
        if rule.replace_regex:
            content = BookContent._apply_replace_regex(content, rule.replace_regex)

        # Step 5: htmlFormatter + unescapeHtml
        content = _html_formatter(content)
        content = _unescape_html(content)

        return content.strip()

    @staticmethod
    def _process_pagination(base_content, rule, chapter, book, book_source) -> str:
        contents = [base_content]
        page_url = _get_next_page_url(html, rule.next_content_url)
        page_count = _get_page_count(rule)
        max_pages = page_count if page_count and page_count > 0 else 50

        for i in range(1, max_pages):
            next_url = _build_page_url(page_url, i)
            if not next_url:
                break
            page_html = _fetch_page_content(next_url, chapter, book, book_source)
            page_content = _extract_content(page_html, rule.content, next_url)
            if page_content:
                contents.append(page_content)
            elif not page_count:
                break
        return "\n".join(contents)

    @staticmethod
    def _process_sub_content(base_content, sub_rule, original_html) -> str:
        analyze_rule = AnalyzeRule(original_html)
        sub_text = analyze_rule.extract_string(sub_rule)
        if sub_text:
            return base_content + "\n\n" + sub_text
        return base_content

    @staticmethod
    def _apply_replace_regex(content, replace_rules) -> str:
        for rule_entry in replace_rules:
            pattern = rule_entry.get("pattern", "")
            replacement = rule_entry.get("replacement", "")
            if pattern:
                try:
                    content = re.sub(pattern, replacement, content)
                except re.error:
                    continue
        return content
```

### P4. SearchModel 并发调度

```python
class SearchModel:
    MAX_THREAD = 9

    async def search(self, key, search_id, precision=False, filter=None):
        if search_id != self.search_id:
            if self.search_key:
                await self.close()
            if not key:
                self.search_key = ""
                return
            self.search_key = key
            self.search_books.clear()
            self.book_source_parts = self.callback.get_search_scope().get_book_source_parts()
            if not self.book_source_parts:
                self._on_search_cancel(NoStackTraceException("书源列表为空"))
                return
            self.search_id = search_id
            self.search_page = 1
            self._init_search_pool()
        else:
            self.search_page += 1
        await self._start_search(precision, filter)

    async def _search_flow(self, precision, filter):
        self.callback.on_search_start()
        semaphore = asyncio.Semaphore(self.thread_count)

        async def search_one_source(bs):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self._search_source(bs, precision, filter), timeout=30.0)
                except asyncio.TimeoutError:
                    return []
                except Exception:
                    return []

        for bs_part in self.book_source_parts:
            for book_source in bs_part.book_sources:
                await self._wait_if_paused()
                items = await search_one_source(book_source)
                if items:
                    for item in items:
                        self._release_html_data(item)
                    await self._insert_search_results(items)
                    self._merge_items(items, precision)
                    self.callback.on_search_success(self.search_books)
                if self.search_id == 0:
                    return
        self._on_search_finish(not items, bool(items))

    def _merge_items(self, new_data, precision=False):
        key = self.search_key  # 注意：源码使用大小写敏感比较，不调用 .lower()
        equal_data, tags_data, contains_data, other_data = [], [], [], []

        for book in self.search_books:
            # 源码直接字符串比较（大小写敏感），不转小写
            if book.name == key or book.author == key:
                equal_data.append(book)
            elif book.kind and key in book.kind:
                tags_data.append(book)
            elif key in book.name or key in book.author:
                contains_data.append(book)
            else:
                other_data.append(book)

        def insert_with_dedup(target_group, new_book):
            for existing in target_group:
                # 源码使用直接字符串比较（大小写敏感），不转小写
                if existing.name == new_book.name and \
                   existing.author == new_book.author:
                    if new_book.origin not in existing.origins:
                        existing.origins.append(new_book.origin)
                    return
            target_group.append(new_book)

        for new_book in new_data:
            # 源码直接字符串比较（大小写敏感）
            if new_book.name == key or new_book.author == key:
                insert_with_dedup(equal_data, new_book)
            elif new_book.kind and key in new_book.kind:
                insert_with_dedup(tags_data, new_book)
            elif key in new_book.name or key in new_book.author:
                insert_with_dedup(contains_data, new_book)
            else:
                insert_with_dedup(other_data, new_book)

        for group in [equal_data, tags_data, contains_data, other_data]:
            group.sort(key=lambda x: len(x.origins), reverse=True)

        self.search_books.clear()
        self.search_books.extend(equal_data + tags_data + contains_data)
        if not precision:
            self.search_books.extend(other_data)

    async def pause(self):   self.working_state = False
    async def resume(self):  self.working_state = True
    async def cancel_search(self):
        await self.close()
        self._on_search_cancel()

    async def close(self):
        if self.search_job: self.search_job.cancel(); self.search_job = None
        if self.search_pool: self.search_pool.shutdown(wait=False); self.search_pool = None
        self.search_id = 0
```

### P5. 重构注意事项

1. **并发控制**：Legado 使用 `CoroutineScope(SupervisorJob() + ctx)` 管理协程生命周期，Python 重构可用 `asyncio.TaskGroup` + `asyncio.gather()`
2. **超时机制**：每个网络请求默认 30s 超时，分页请求单页超时不阻断整体
3. **缓存策略**：infoHtml / tocHtml 缓存当前会话有效；跨会话需要重新请求
4. **preUpdateJs 安全**：JS 执行环境必须沙箱化（Python 可用 `quickjs` 或 `pyexecjs`），禁止文件 IO 和网络访问
5. **正文分页**：Legado 的并行模式可能同时发起 10+ 并发的分页请求，重构时需限制最大并发数（推荐 ≤ 5）
6. **音频类型**：content 为空时返回 URL 而非 HTML，前端直接用于音频播放
7. **replaceRegex 性能**：正则替换列表可能很长（有的书源配置 50+ 条替换规则），应编译 pattern 后再执行替换
8. **toBook() 防丢失**：搜索结果 → Book 时，tocUrl 默认 = bookUrl，若 bookInfo 阶段有独立 tocUrl 会覆盖
9. **canRename 参数**：在 getBookInfoAwait 内部默认 canRename=true，外部调用时可控制是否覆盖已有字段
10. **checkRedirect 日志**：重定向仅记录调试日志，不影响业务流程，但过多的重定向提示可能意味着书源配置过时
