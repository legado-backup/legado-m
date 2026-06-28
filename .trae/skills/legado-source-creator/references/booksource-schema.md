# BookSource / RssSource 字段定义

> 基于 Legado 源码逐字段核对。字段名使用 **camelCase**。所有字段类型和默认值均来自源码实体类定义。

---

## 一、BookSource（书源）

源码位置：`app/src/main/java/io/legado/app/data/entities/BookSource.kt`

### 1.1 基本信息

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `bookSourceUrl` | String | "" | **主键**，网站首页 URL（不可重复） |
| 2 | `bookSourceName` | String | "" | 源名称 |
| 3 | `bookSourceGroup` | String? | null | 分组，多个分组用逗号分隔 |
| 4 | `bookSourceType` | Int | 0 | 类型：0=文本，1=音频，2=图片(漫画)，3=文件(下载站)，4=视频 |
| 5 | `bookUrlPattern` | String? | null | 详情页 URL 正则，匹配到的 URL 自动识别为书籍详情页 |
| 6 | `customOrder` | Int | 0 | 手动排序编号 |
| 7 | `enabled` | Boolean | true | 是否启用 |
| 8 | `enabledExplore` | Boolean | true | 是否启用发现 |
| 9 | `lastUpdateTime` | Long | 0 | 最后更新时间，用于排序 |
| 10 | `respondTime` | Long | 180000L | 响应时间(ms)，用于排序，默认180秒 |
| 11 | `weight` | Int | 0 | 智能排序权重 |
| 12 | `bookSourceComment` | String? | null | 注释说明 |
| 13 | `variableComment` | String? | null | 自定义变量说明 |

### 1.2 网络与登录

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 14 | `header` | String? | null | 自定义请求头，JSON 格式或 `@js:`/`<js>` 前缀的 JS 代码 |
| 15 | `enabledCookieJar` | Boolean? | true | 是否启用 OkHttp CookieJar 自动保存每次请求的 Cookie |
| 16 | `concurrentRate` | String? | null | 并发率控制。纯数字=延迟ms（如 `"500"` = 请求间隔500ms）；`count/duration` 格式=速率限制（如 `"3/1000"` = 1000ms 内最多3个请求） |
| 17 | `loginUrl` | String? | null | 登录地址。可以是纯 URL，也可以是 `@js:` 前缀的 JS 代码（执行 login 函数实现登录）或 `<js>...</js>` 包裹的 JS 代码 |
| 18 | `loginUi` | String? | null | 登录 UI 配置，JSON 格式（RowUi 数组），也可用 `@js:`/`<js>` 前缀动态生成 |
| 19 | `loginCheckJs` | String? | null | 登录状态检测 JS，返回 `$.ok` 表示已登录，`$.no` 表示未登录 |
| 20 | `coverDecodeJs` | String? | null | 封面图片解密 JS |
| 21 | `jsLib` | String? | null | JS 库，JSON 格式，可被规则中的 JS 代码引用 |

### 1.3 搜索与发现（顶层 URL 字段）

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 22 | `searchUrl` | String? | null | 搜索 URL 模板，支持 `{{key}}`/`{{page}}` 占位符，后缀 JSON 为 UrlOption |
| 23 | `exploreUrl` | String? | null | 发现 URL 模板，格式：`分类名::URL\n分类名::URL`，支持 `{{page}}` 占位符 |
| 24 | `exploreScreen` | String? | null | 发现筛选规则配置 |

### 1.4 规则组引用

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 25 | `ruleSearch` | SearchRule? | null | 搜索结果规则 |
| 26 | `ruleExplore` | ExploreRule? | null | 发现结果规则 |
| 27 | `ruleBookInfo` | BookInfoRule? | null | 书籍详情规则 |
| 28 | `ruleToc` | TocRule? | null | 目录规则 |
| 29 | `ruleContent` | ContentRule? | null | 正文规则 |
| 30 | `ruleReview` | ReviewRule? | null | 段评规则 |

### 1.5 扩展功能

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 31 | `eventListener` | Boolean | false | 是否监听事件来执行回调规则（配合 ContentRule.callBackJs 使用） |
| 32 | `customButton` | Boolean | false | 由书源控制的自定义按钮 |

---

### 1.6 SearchRule（搜索规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/SearchRule.kt`
继承 `BookListRule` 接口

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `checkKeyWord` | String? | null | 校验关键字，搜索时用此关键字替代用户输入进行测试 |
| 2 | `bookList` | String? | null | 搜索结果列表项规则（CSS/JSONPath/XPath/正则） |
| 3 | `name` | String? | null | 书名提取规则 |
| 4 | `author` | String? | null | 作者提取规则 |
| 5 | `intro` | String? | null | 简介提取规则 |
| 6 | `kind` | String? | null | 分类提取规则 |
| 7 | `lastChapter` | String? | null | 最新章节提取规则 |
| 8 | `updateTime` | String? | null | 更新时间提取规则 |
| 9 | `bookUrl` | String? | null | 详情页 URL 提取规则 |
| 10 | `coverUrl` | String? | null | 封面图 URL 提取规则 |
| 11 | `wordCount` | String? | null | 字数提取规则 |

### 1.7 ExploreRule（发现规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/ExploreRule.kt`
继承 `BookListRule` 接口，与 SearchRule 字段完全相同（无额外字段）

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `bookList` | String? | null | 发现结果列表项规则 |
| 2 | `name` | String? | null | 书名提取规则 |
| 3 | `author` | String? | null | 作者提取规则 |
| 4 | `intro` | String? | null | 简介提取规则 |
| 5 | `kind` | String? | null | 分类提取规则 |
| 6 | `lastChapter` | String? | null | 最新章节提取规则 |
| 7 | `updateTime` | String? | null | 更新时间提取规则 |
| 8 | `bookUrl` | String? | null | 详情页 URL 提取规则 |
| 9 | `coverUrl` | String? | null | 封面图 URL 提取规则 |
| 10 | `wordCount` | String? | null | 字数提取规则 |

> **注意**：`exploreUrl` 和 `exploreScreen` 是 BookSource 的顶层字段，不在 ExploreRule 内。`exploreKind`、`RowUi`、`FlexChildStyle` 是独立类/数据结构，不是 ExploreRule 的字段。

### 1.8 BookInfoRule（详情规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/BookInfoRule.kt`

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `init` | String? | null | 详情页初始化规则（如登录后获取 Cookie 等） |
| 2 | `name` | String? | null | 书名提取规则 |
| 3 | `author` | String? | null | 作者提取规则 |
| 4 | `intro` | String? | null | 简介提取规则 |
| 5 | `kind` | String? | null | 分类提取规则 |
| 6 | `lastChapter` | String? | null | 最新章节提取规则 |
| 7 | `updateTime` | String? | null | 更新时间提取规则 |
| 8 | `coverUrl` | String? | null | 封面图 URL 提取规则 |
| 9 | `tocUrl` | String? | null | 目录页 URL 提取规则（当目录与详情不在同一页时使用） |
| 10 | `wordCount` | String? | null | 字数提取规则 |
| 11 | `canReName` | String? | null | 是否允许重命名（有值则允许） |
| 12 | `downloadUrls` | String? | null | 下载链接提取规则（用于文件类型书源，bookSourceType=3） |

### 1.9 TocRule（目录规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/TocRule.kt`

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `preUpdateJs` | String? | null | 目录更新前执行的 JS 代码 |
| 2 | `chapterList` | String? | null | 章节列表项规则 |
| 3 | `chapterName` | String? | null | 章节名称提取规则 |
| 4 | `chapterUrl` | String? | null | 章节 URL 提取规则 |
| 5 | `formatJs` | String? | null | 章节列表格式化 JS，对章节列表处理后再返回 |
| 6 | `isVolume` | String? | null | 是否卷标规则（有值则标记为卷，跳过不获取正文） |
| 7 | `isVip` | String? | null | 是否 VIP 章节规则 |
| 8 | `isPay` | String? | null | 是否付费章节规则 |
| 9 | `updateTime` | String? | null | 更新时间提取规则 |
| 10 | `nextTocUrl` | String? | null | 下一页目录 URL 规则（多页目录翻页） |

### 1.10 ContentRule（正文规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/ContentRule.kt`

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `content` | String? | null | 正文内容提取规则（通常用 `@html` 保留格式） |
| 2 | `subContent` | String? | null | 副文规则，拼接在正文后面，也可用于获取歌词等 |
| 3 | `title` | String? | null | 正文页标题提取规则（有些网站只能在正文中获取标题） |
| 4 | `nextContentUrl` | String? | null | 下一页正文 URL 规则（多页正文翻页） |
| 5 | `webJs` | String? | null | 正文页加载完后执行的 JS |
| 6 | `sourceRegex` | String? | null | 正文来源正则匹配 |
| 7 | `replaceRegex` | String? | null | 替换规则，正则替换正文中的内容 |
| 8 | `imageStyle` | String? | null | 图片样式，默认大小居中，`FULL` 为最大宽度 |
| 9 | `imageDecode` | String? | null | 图片 bytes 二次解密 JS，返回解密后的 bytes |
| 10 | `payAction` | String? | null | 购买操作，JS 代码或包含 `{{js}}` 的 URL |
| 11 | `callBackJs` | String? | null | 监听到事件后执行的回调 JS 代码（需配合 BookSource.eventListener=true 使用） |

### 1.11 ReviewRule（段评规则）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/ReviewRule.kt`

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `reviewUrl` | String? | null | 段评 URL |
| 2 | `avatarRule` | String? | null | 段评发布者头像提取规则 |
| 3 | `contentRule` | String? | null | 段评内容提取规则 |
| 4 | `postTimeRule` | String? | null | 段评发布时间提取规则 |
| 5 | `reviewQuoteUrl` | String? | null | 获取段评回复 URL |
| 6 | `voteUpUrl` | String? | null | 点赞 URL |
| 7 | `voteDownUrl` | String? | null | 点踩 URL |
| 8 | `postReviewUrl` | String? | null | 发送回复 URL |
| 9 | `postQuoteUrl` | String? | null | 发送回复段评 URL |
| 10 | `deleteUrl` | String? | null | 删除段评 URL |

> **注意**：ReviewRule 的 TypeConverter 当前返回 null/"null"，表示此功能在数据库层面尚未完全启用，但实体定义已存在。

---

## 二、RssSource（订阅源）

源码位置：`app/src/main/java/io/legado/app/data/entities/RssSource.kt`

### 2.1 基本信息

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `sourceUrl` | String | "" | **主键**，源 URL（不可重复） |
| 2 | `sourceName` | String | "" | 源名称 |
| 3 | `sourceIcon` | String | "" | 图标 URL |
| 4 | `sourceGroup` | String? | null | 分组，多个分组用逗号分隔 |
| 5 | `sourceComment` | String? | null | 注释说明 |
| 6 | `enabled` | Boolean | true | 是否启用 |
| 7 | `variableComment` | String? | null | 自定义变量说明 |
| 8 | `customOrder` | Int | 0 | 手动排序编号 |
| 9 | `lastUpdateTime` | Long | 0 | 最后更新时间，用于排序 |
| 10 | `type` | Int | 0 | 类型：0=网页，1=图片，2=视频 |

### 2.2 网络与登录

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 11 | `header` | String? | null | 自定义请求头，JSON 格式或 `@js:`/`<js>` 前缀的 JS 代码 |
| 12 | `enabledCookieJar` | Boolean? | true | 是否启用 OkHttp CookieJar 自动保存每次请求的 Cookie |
| 13 | `concurrentRate` | String? | null | 并发率控制，格式同 BookSource |
| 14 | `loginUrl` | String? | null | 登录地址，格式同 BookSource |
| 15 | `loginUi` | String? | null | 登录 UI 配置，格式同 BookSource |
| 16 | `loginCheckJs` | String? | null | 登录状态检测 JS |
| 17 | `coverDecodeJs` | String? | null | 封面图片解密 JS |
| 18 | `jsLib` | String? | null | JS 库，JSON 格式 |

### 2.3 分类与搜索

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 19 | `sortUrl` | String? | null | 分类 URL，格式：`分类名::URL\n分类名::URL` |
| 20 | `searchUrl` | String? | null | 搜索 URL 模板，支持 `{{key}}`/`{{page}}` 占位符和 `@js:` 规则 |
| 21 | `singleUrl` | Boolean | false | 是否单 URL 源（不分页） |

### 2.4 列表规则

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 22 | `articleStyle` | Int | 0 | 列表样式：0-4 对应不同布局 |
| 23 | `ruleArticles` | String? | null | 文章列表项规则 |
| 24 | `ruleNextPage` | String? | null | 下一页规则 |
| 25 | `ruleTitle` | String? | null | 标题提取规则 |
| 26 | `rulePubDate` | String? | null | 发布日期提取规则 |
| 27 | `ruleDescription` | String? | null | 描述提取规则 |
| 28 | `ruleImage` | String? | null | 图片提取规则 |
| 29 | `ruleLink` | String? | null | 链接提取规则 |
| 30 | `ruleContent` | String? | null | 正文提取规则 |

### 2.5 内容过滤

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 31 | `contentWhitelist` | String? | null | 正文 URL 白名单，匹配的 URL 才在正文页加载 |
| 32 | `contentBlacklist` | String? | null | 正文 URL 黑名单，匹配的 URL 不在正文页加载 |

### 2.6 WebView 控制

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 33 | `shouldOverrideUrlLoading` | String? | null | 跳转 URL 拦截 JS，返回 true 拦截，JS 变量 `url` 可用，可调用阅读搜索/添加书架等 |
| 34 | `style` | String? | null | WebView 自定义样式 CSS |
| 35 | `enableJs` | Boolean | true | 是否启用 WebView JS |
| 36 | `loadWithBaseUrl` | Boolean | true | 使用 baseUrl 加载 |
| 37 | `injectJs` | String? | null | 注入 JS，页面加载时执行 |
| 38 | `preloadJs` | String? | null | 提前预注入 JS，在页面加载前执行 |
| 39 | `startHtml` | String? | null | Web 形式起始页 HTML |
| 40 | `startStyle` | String? | null | 起始页样式 CSS |
| 41 | `startJs` | String? | null | 起始页 JS |
| 42 | `showWebLog` | Boolean | false | 是否输出 WebView 网页日志 |

### 2.7 缓存与预加载

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 43 | `preload` | Boolean | false | 是否启用预加载 |
| 44 | `cacheFirst` | Boolean | false | 是否优先加载缓存 |

---

## 三、BookListRule 接口（SearchRule / ExploreRule 的公共字段）

源码位置：`app/src/main/java/io/legado/app/data/entities/rule/BookListRule.kt`

SearchRule 和 ExploreRule 均实现此接口，共享以下字段：

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `bookList` | String? | null | 列表项规则（CSS/JSONPath/XPath/正则） |
| 2 | `name` | String? | null | 书名提取规则 |
| 3 | `author` | String? | null | 作者提取规则 |
| 4 | `intro` | String? | null | 简介提取规则 |
| 5 | `kind` | String? | null | 分类提取规则 |
| 6 | `lastChapter` | String? | null | 最新章节提取规则 |
| 7 | `updateTime` | String? | null | 更新时间提取规则 |
| 8 | `bookUrl` | String? | null | 详情页 URL 提取规则 |
| 9 | `coverUrl` | String? | null | 封面图 URL 提取规则 |
| 10 | `wordCount` | String? | null | 字数提取规则 |

> SearchRule 在此基础上额外定义了 `checkKeyWord` 字段；ExploreRule 无额外字段。

---

## 四、BaseSource 接口（BookSource / RssSource 的公共字段）

源码位置：`app/src/main/java/io/legado/app/data/entities/BaseSource.kt`

BookSource 和 RssSource 均实现此接口，共享以下字段：

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | `concurrentRate` | String? | 并发率控制 |
| 2 | `loginUrl` | String? | 登录地址（纯 URL / `@js:` / `<js>...</js>`） |
| 3 | `loginUi` | String? | 登录 UI 配置 |
| 4 | `header` | String? | 自定义请求头 |
| 5 | `enabledCookieJar` | Boolean? | 启用 CookieJar |
| 6 | `jsLib` | String? | JS 库 |

---

## 五、修正记录

相较于旧版文档，本次修正内容如下：

### BookSource 顶层字段
- **新增**：`bookUrlPattern`（详情页 URL 正则）、`exploreScreen`（发现筛选规则）、`ruleReview`（段评规则）、`eventListener`（事件监听）、`customButton`（自定义按钮）
- **删除**：`loginStyle`（源码中不存在此字段）
- **修正**：`bookSourceType` 说明，3=文件(下载站)，4=视频（旧文档误写为 3=视频）
- **修正**：`jsLib` 从"进阶字段"移至"网络与登录"分组（属于 BaseSource 接口）
- **修正**：`searchUrl`、`exploreUrl` 标注为顶层字段而非规则组内字段

### SearchRule
- **新增**：`checkKeyWord`（校验关键字）、`updateTime`（更新时间）

### ExploreRule
- **删除**：`exploreKind`、`RowUi`、`FlexChildStyle`（这些是独立类/数据结构，不是 ExploreRule 的字段）
- **修正**：`exploreUrl` 不属于 ExploreRule，而是 BookSource 的顶层字段
- **说明**：ExploreRule 与 SearchRule 字段完全相同，无额外字段

### BookInfoRule
- **新增**：`updateTime`（更新时间）、`downloadUrls`（下载链接）

### TocRule
- **新增**：`preUpdateJs`（目录更新前 JS）、`formatJs`（章节列表格式化 JS）

### ContentRule
- **删除**：`titleRule`、`bookTitleRule`、`chapterTitle`、`contentType`、`customProcessor`（源码中均不存在）
- **新增**：`subContent`（副文规则）、`title`（正文页标题）、`imageDecode`（图片解密 JS）、`payAction`（购买操作）、`callBackJs`（事件回调 JS）

### ReviewRule
- **新增**：整个规则组（旧文档完全缺失），共 10 个字段

### RssSource
- **新增**：`contentWhitelist`、`contentBlacklist`、`shouldOverrideUrlLoading`、`style`、`injectJs`、`preloadJs`、`startHtml`、`startStyle`、`startJs`、`showWebLog`、`preload`、`cacheFirst`、`searchUrl`、`variableComment`、`jsLib`、`loginCheckJs`、`coverDecodeJs`
- **修正**：按源码字段顺序重新排列，分为基本信息/网络与登录/分类与搜索/列表规则/内容过滤/WebView控制/缓存与预加载 七组
