# RssSource 实体与解析流程

> 验证日期：2026-06-03
> 源码文件：`app/src/main/java/io/legado/app/data/entities/RssSource.kt`、`RssArticle.kt`、`BaseRssArticle.kt`
> 解析流程：`app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt`

## 1. RssSource 实体完整字段（44个）

> 源码：RssSource.kt
> Room表名：`rssSources`，索引：`sourceUrl`（非唯一）
> 实现：`Parcelable, BaseSource`

### 基本信息

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | sourceUrl | String | "" | 源URL（@PrimaryKey） |
| 2 | sourceName | String | "" | 名称 |
| 3 | sourceIcon | String | "" | 图标 |
| 4 | sourceGroup | String? | null | 分组 |
| 5 | sourceComment | String? | null | 注释 |
| 6 | enabled | Boolean | true | 是否启用 |
| 7 | variableComment | String? | null | 自定义变量说明 |
| 8 | type | Int | 0 | 类型：0=网页, 1=图片, 2=视频（@ColumnInfo defaultValue="0"） |

### 网络配置

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 9 | enabledCookieJar | Boolean? | true | 启用okhttp CookieJar自动保存每次请求的cookie（@ColumnInfo defaultValue="0"） |
| 10 | concurrentRate | String? | null | 并发率 |
| 11 | header | String? | null | 请求头 |
| 12 | loginUrl | String? | null | 登录地址 |
| 13 | loginUi | String? | null | 登录UI |
| 14 | loginCheckJs | String? | null | 登录检测js |
| 15 | searchUrl | String? | null | 搜索url |

### 规则

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 16 | sortUrl | String? | null | 分类Url |
| 17 | singleUrl | Boolean | false | 是否单url源 |
| 18 | articleStyle | Int | 0 | 列表样式,0,1,2,3,4（@ColumnInfo defaultValue="0"） |
| 19 | ruleArticles | String? | null | 列表规则 |
| 20 | ruleNextPage | String? | null | 下一页规则 |
| 21 | ruleTitle | String? | null | 标题规则 |
| 22 | rulePubDate | String? | null | 发布日期规则 |
| 23 | ruleDescription | String? | null | 描述规则 |
| 24 | ruleImage | String? | null | 图片规则 |
| 25 | ruleLink | String? | null | 链接规则 |
| 26 | ruleContent | String? | null | 正文规则 |
| 27 | contentWhitelist | String? | null | 正文url白名单 |
| 28 | contentBlacklist | String? | null | 正文url黑名单 |
| 29 | coverDecodeJs | String? | null | 封面解密js |

**与书源的关键区别**：
- 书源 `ruleSearch` 是嵌套对象：`{"bookList":"...", "name":"...", "author":"..."}`
- 订阅源规则字段全部是**扁平独立的 String?**：`ruleArticles`/`ruleTitle`/`ruleLink` 等都是 RssSource 实体的直接字段
- **绝对不能**写成 `{"ruleArticles": {"articleList":"...", "title":"..."}}`，这会导致 `SelectorParseException`

### WebView相关

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 30 | shouldOverrideUrlLoading | String? | null | 跳转url拦截，js返回true拦截，js变量url，可通过js打开url，比如调用阅读搜索、添加书架等，简化规则写法，不用webView js注入 |
| 31 | style | String? | null | webView样式 |
| 32 | enableJs | Boolean | true | 是否启用JS（@ColumnInfo defaultValue="1"） |
| 33 | loadWithBaseUrl | Boolean | true | 是否用baseUrl加载（@ColumnInfo defaultValue="1"） |
| 34 | injectJs | String? | null | 注入js |
| 35 | preloadJs | String? | null | 提前预注入js |
| 36 | startHtml | String? | null | web形式起始页 |
| 37 | startStyle | String? | null | 起始页样式 |
| 38 | startJs | String? | null | 起始页js |
| 39 | showWebLog | Boolean | false | 是否输出web网页日志（@ColumnInfo defaultValue="0"） |

### 缓存与其他

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 40 | jsLib | String? | null | js库（override BaseSource） |
| 41 | lastUpdateTime | Long | 0 | 最后更新时间，用于排序（@ColumnInfo defaultValue="0"） |
| 42 | customOrder | Int | 0 | 自定义排序（@ColumnInfo defaultValue="0"） |
| 43 | preload | Boolean | false | 是否启用预加载（@ColumnInfo defaultValue="0"） |
| 44 | cacheFirst | Boolean | false | 是否优先加载缓存（@ColumnInfo defaultValue="0"） |

### 修正记录

| 修正项 | 旧值 | 新值（源码实际值） |
|--------|------|-------------------|
| 字段总数 | 35 | 44 |
| sourceIcon 类型 | String? | String |
| enabledCookieJar 默认值 | false | true |
| enableJs 默认值 | false | true |
| loadWithBaseUrl 默认值 | false | true |
| singleUrl 默认值 | true | false |
| respondTime | 存在 | **已删除**（源码中不存在） |
| variable | 存在 | **已删除**（源码中不存在） |
| 新增16个字段 | - | variableComment, jsLib, coverDecodeJs, ruleNextPage, contentWhitelist, contentBlacklist, shouldOverrideUrlLoading, style, injectJs, preloadJs, startHtml, startStyle, startJs, showWebLog, preload, cacheFirst |

## 2. RssArticle 实体

> 源码：RssArticle.kt、BaseRssArticle.kt

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| origin | String | "" | 订阅源URL（联合主键） |
| sort | String | "" | 分类标识（联合主键） |
| title | String | "" | 文章标题 |
| order | Long | 0 | 排序权重 |
| link | String | "" | 文章链接（联合主键） |
| pubDate | String? | null | 发布日期 |
| description | String? | null | 描述 |
| content | String? | null | 正文内容 |
| image | String? | null | 封面图片URL |
| group | String | "默认分组" | 分组 |
| read | Boolean | false | 是否已读 |
| variable | String? | null | 规则变量JSON |
| type | Int | 0 | 类型：0=网页, 1=图片, 2=视频 |
| durPos | Int | 0 | 阅读进度 |

## 3. RssParserByRule 解析流程

> 源码：RssParserByRule.kt L38-140

```
parseXML(body)
  │
  ├─ setContent(body)                    // AnalyzeRule.setContent() 自动检测JSON
  │
  ├─ getElements(ruleArticles)           // 按Mode分发：CSS/JSONPath/XPath/JS
  │   → 返回 List<Any>                   // JSON模式时每个item是LinkedTreeMap
  │
  └─ 循环每个item:
      ├─ setContent(item)                // 对每个item重新设置content
      │   → 自动检测JSON → isJSON=true
      │
      ├─ getString(ruleTitle)            // JSON模式+无前缀 → JSONPath
      ├─ getString(ruleLink)             // 同上
      ├─ getString(ruleImage)            // 同上
      ├─ getString(ruleDescription)      // 同上
      ├─ getString(rulePubDate)          // 同上
      │
      └─ title为空则丢弃该item
```

### 关键行为

1. `setContent(body)` 时自动检测JSON（AnalyzeRule.kt L96-108）
2. `getElements(ruleArticles)` 返回 `List<Any>`，JSON模式下每个item是 `LinkedTreeMap`
3. 对每个item，`setContent(item)` 后用独立规则字段提取
4. JSON模式下无前缀规则走JSONPath（AnalyzeRule.kt L623）
5. `getString()` 对 `LinkedTreeMap` 有快捷键值访问（AnalyzeRule.kt L326-328）
6. `<js>` 规则中 `result` 是当前content，对LinkedTreeMap可用 `result.get('key')` 或 `result.key`

### ⚠️ ruleArticles 使用 `<js>` 规则时的关键限制

> 源码依据：AnalyzeRule.kt L429 + L436-437

**`getElements()` 对JS规则返回值直接 `as List<Any>` 强转！**

```kotlin
// AnalyzeRule.kt L429
Mode.Js -> evalJS(rule, result)
// L436-437
result?.let {
    return it as List<Any>   // ← 直接强转！String不能转List！
}
```

**规则**：
- ✅ JS规则必须返回JavaScript数组（Rhino的NativeArray实现了`java.util.List`）
- ❌ 不能返回 `JSON.stringify(array)` — 这是String，强转失败报 `ClassCastException`
- ❌ 不能返回 `'[]'` — 同样是String
- ✅ 返回空数组用 `result = []`，不用 `result = '[]'`

### ⚠️ NativeObject vs LinkedTreeMap 的字段规则差异

> 源码依据：AnalyzeRule.kt L302-354

当 `<js>` 规则返回JavaScript数组时，每个item是Rhino的 `NativeObject`（不是Gson的 `LinkedTreeMap`）。

`getString()` 对两种类型有不同处理：

| 类型 | 处理方式 | 规则写法 |
|------|----------|----------|
| `NativeObject` | L313-325: `result[sourceRule.rule]` 直接属性访问 | 纯属性名：`vod_name` |
| `LinkedTreeMap` | L326-328: `result[ruleList.first().rule]` 键值访问 | 纯属性名：`vod_name` |
| 其他（String等） | L330-353: 按mode分发（JSONPath/CSS/JS等） | `$.vod_name` 或 CSS选择器 |

**关键**：
- 当content是 `NativeObject` 时，`getString()` 走L313-325分支，**忽略mode**，直接用 `result[rule]` 访问属性
- `$.vod_name` 的rule是 `"$.vod_name"`（含前缀），在NativeObject上会查找属性 `"$.vod_name"` → 找不到！
- 所以对NativeObject，规则必须写纯属性名 `vod_name`，不能带 `$.` 前缀
- 或者用 `<js>` 规则：`<js>result.vod_name</js>`，在JS中直接用点语法访问

## 4. searchUrl 搜索流程源码分析

> 验证日期：2026-06-05
> 源码文件：RssSortActivity.kt、RssArticlesViewModel.kt、Rss.kt、AnalyzeUrl.kt

### 搜索入口与调用链

```
RssSortActivity.kt L271-298
  → 用户提交搜索 → start(context, null, source.sourceUrl, query)
  → RssSortActivity.kt L344-351
    → 搜索模式下，source.searchUrl 作为 sortUrl 传入 Fragment
  → RssArticlesViewModel.kt L36-58
    → loadArticles() → Rss.getArticles(viewModelScope, sortName, sortUrl=rssSource.searchUrl, rssSource, page, searchKey)
  → Rss.kt L35-81
    → AnalyzeUrl(sortUrl=searchUrl, page=page, key=key, baseUrl=rssSource.sourceUrl, source=rssSource)
    → getStrResponseAwait() → RssParserByRule.parseXML()
```

### 关键行为

1. **搜索结果复用列表规则**：搜索和分类走完全相同的 `Rss.getArticlesAwait()` → `RssParserByRule.parseXML()` 管线，使用同一套 ruleArticles/ruleTitle/ruleLink/ruleImage/rulePubDate/ruleDescription 规则
2. **searchUrl 支持 POST**：通过 AnalyzeUrl 的 UrlOption 解析，格式为 `URL,{"method":"POST","body":"..."}`
3. **`{{key}}` 和 `{{page}}` 模板变量**：在 AnalyzeUrl.replaceKeyPageJs() (L190-217) 中，`{{...}}` 内的内容作为 JS 表达式执行，JS 环境中 `key` 绑定为搜索关键字，`page` 绑定为页码
4. **POST body 编码**：当 body 不是 JSON/XML 且没有 Content-Type 头时，走 `analyzeFields()` 编码为 form 格式（L271-285）

### ⚠️ 搜索结果与列表页HTML结构可能不同

RssSource 的搜索结果复用 ruleArticles/ruleTitle/ruleLink 等规则，但搜索结果页的 HTML 结构可能与列表页不同：

| 差异点 | 列表页 | 搜索结果页 |
|--------|--------|-----------|
| tr3 类名 | `tr3 t_one` | `tr3 tac` |
| 标题链接 | `<a class="subject" href="read.php?tid=xxx">` | `<a href="read.php?tid=xxx">`（无class） |
| 图片容器 | `<a class="lazy-imgs" data-src="URL">` | `<img class="thumb-img lazyimg" data-src="URL">` |
| 置顶帖 | 有（需跳过） | 无 |

**兼容方案**：用 `||` 操作符，先尝试列表页选择器，失败则回退搜索结果选择器：
```
ruleLink: class.subject@href||tag.a.0@href
ruleTitle: class.subject@text||tag.a.0@text
ruleImage: class.lazy-imgs.0@data-src||tag.img.0@data-src
```

**ruleArticles 索引跳过问题**：列表页用 `class.tr3[!0:3]` 跳过置顶帖，但搜索结果页无置顶帖，`[!0:3]` 会误跳前3条正常结果。有 searchUrl 时建议去掉索引跳过。

## 5. loginCheckJs 执行环境源码分析

> 验证日期：2026-06-05
> 源码文件：Rss.kt L53-77、AnalyzeUrl.kt L364-388

### 执行环境

loginCheckJs 在 **Rhino JS 引擎**中执行，不是 WebView！

```kotlin
// Rss.kt L53-61
val checkJs = rssSource.loginCheckJs
val res = kotlin.runCatching {
    analyzeUrl.getStrResponseAwait().let {
        if (!checkJs.isNullOrBlank()) {
            analyzeUrl.evalJS(checkJs, it) as StrResponse  // ← 强转 StrResponse！
        } else {
            it
        }
    }
}
```

```kotlin
// AnalyzeUrl.kt L364-388
fun evalJS(jsStr: String, result: Any? = null): Any? {
    val bindings = buildScriptBindings { bindings ->
        bindings["java"] = this       // JsExtensions 实例
        bindings["baseUrl"] = baseUrl
        bindings["cookie"] = CookieStore
        bindings["cache"] = CacheManager
        bindings["page"] = page
        bindings["key"] = key
        bindings["source"] = source   // RssSource 对象
        bindings["result"] = result   // StrResponse 对象
    }
    return RhinoScriptEngine.eval(jsStr, scope, coroutineContext)
}
```

### 关键约束

1. **没有 `document`/`window` 对象**：Rhino 环境不是浏览器，`document.querySelector()` 等浏览器 API 不可用
2. **必须返回 StrResponse**：返回值被 `as StrResponse` 强转，返回布尔值/字符串会 ClassCastException
3. **`result` 是 StrResponse 对象**：通过 `result.body()` 获取页面 HTML 内容
4. **`source` 是 RssSource 对象**：可通过 `source.loginUrl` 获取登录 URL
5. **每次请求都执行**：loginCheckJs 在每次 getArticlesAwait() 时执行，不仅限于搜索

### 正确写法

```javascript
// 检查页面是否包含"退出"来判断登录状态
var s=result.body();
if(s.indexOf('退出')==-1){
  java.startBrowserAwait(source.loginUrl,'登录');
  result
}else{
  result
}
```

### ⚠️ loginUrl vs loginCheckJs 使用策略

| 场景 | 策略 | 原因 |
|------|------|------|
| 浏览和搜索都需要登录 | 设 loginUrl + loginCheckJs | loginCheckJs 自动检测并触发登录 |
| 仅搜索需登录，浏览不需要 | 只设 loginUrl，不设 loginCheckJs | loginCheckJs 每次请求都执行，浏览列表时也会弹登录窗 |
| 不需要登录 | 都不设 | — |
