# Legado 图片类型订阅源（type=1）内容规则加载图片的完整链路分析

> 生成时间：2026-07-21
> 核心问题：type=1 图片类型的订阅源，ruleContent 如何获取并加载图片

---

## 一、图片类型订阅源的图片加载完整链路

### 1.1 列表阶段：缩略图加载

```
RssParserByRule.parseXML()
  → rssSource.ruleImage 提取列表项图片URL
  → NetworkUtils.getAbsoluteURL() 转绝对URL
  → RssArticle.image = 绝对URL
  → 列表Adapter用 Glide/ImageLoader 加载 RssArticle.image 显示缩略图
```

**适配字段**：`ruleImage`（列表项图片URL提取规则，支持 CSS/XPath/JSONPath/正则/JS 五种解析方式）

### 1.2 点击阅读阶段：大图加载

核心路由逻辑在 [ReadRss.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt)：

```
ReadRss.readRss(fragment, rssArticle, rssSource)
  → val type = rssArticle.type
  → if (type == 0) → ReadRssActivity（WebView渲染）
  → if (type == 2) → VideoPlayerActivity（视频播放）
  → if (type == 1) → readNoHtml() → 以下详细链路
```

### 1.3 type=1 图片大图加载详细链路

```
readNoHtml(fragment, rssArticle, rssSource, type=1)
  │
  ├─ 情况A：ruleContent 为空
  │   → PhotoDialog(rssArticle.link)
  │   → 直接用文章链接作为图片URL
  │   → Glide加载图片显示在PhotoView
  │
  └─ 情况B：ruleContent 非空
      → Rss.getContent(rssArticle, ruleContent, rssSource)
        → AnalyzeUrl(rssArticle.link) 构建请求URL
          → 请求文章详情页HTML
          → loginCheckJs 检测/处理登录态
        → AnalyzeRule(rssArticle, rssSource)
          → setContent(res.body) 设置HTML内容
          → getString(ruleContent) 用规则提取图片URL
        → 返回 body（图片URL字符串）
      → NetworkUtils.getAbsoluteURL(rssArticle.link, body) 转绝对URL
      → PhotoDialog(url)
      → Glide加载图片显示在PhotoView
```

### 1.4 关键结论

**图片类型订阅源（type=1）只支持单张图片查看，不支持相册/多图浏览。**

图片URL的来源取决于 `ruleContent` 是否配置：
- **无 ruleContent**：直接用 `rssArticle.link`（文章链接本身就是图片直链）
- **有 ruleContent**：先请求文章详情页，用 `ruleContent` 规则从HTML中提取图片URL

## 二、ruleContent 在图片类型订阅源中的适配方式

### 2.1 ruleContent 的本质

`ruleContent` 是一个**字符串类型的解析规则**（不是嵌套对象），支持5种解析方式：

| 解析方式 | 前缀 | 示例 | 适用场景 |
|---------|------|------|---------|
| CSS选择器 | `@css:` | `@css:img.src` | 标准HTML页面提取图片src |
| XPath | `//` | `//img/@src` | XML/HTML结构化提取 |
| JSONPath | `$.` | `$.data.image_url` | JSON API 返回图片URL |
| 正则 | `##` | `img src="([^"]+)"##$1` | 非标准结构提取 |
| JS | `@js:` 或 `<js>` | `@js:result.match(/src="([^"]+)"/)[1]` | 复杂逻辑提取 |

### 2.2 与 BookSource 的 ContentRule 对比

| 维度 | BookSource ContentRule | RssSource ruleContent |
|------|----------------------|----------------------|
| 数据结构 | 嵌套对象（ContentRule） | 扁平字符串 |
| 图片URL提取 | `ContentRule.content` | `ruleContent` 整体 |
| 图片样式控制 | `ContentRule.imageStyle` | **无** |
| 图片解密 | `ContentRule.imageDecode` | `coverDecodeJs`（共用） |
| URL替换 | `ContentRule.replaceRegex` | **无** |
| 副内容 | `ContentRule.subContent` | **无** |
| 下一页 | `ContentRule.nextContentUrl` | **无**（RssSource用ruleNextPage在列表层翻页） |

### 2.3 RssSource 图片加载的局限

1. **只返回单个URL字符串**：`analyzeRule.getString(ruleContent)` 只提取一个值，而 BookSource 的 `ContentRule.content` 配合 `nextContentUrl` 可以返回多个图片URL的分页内容
2. **无 imageStyle**：不能控制图片全屏/居中显示方式
3. **无 imageDecode**：正文图片解密与封面解密共用 `coverDecodeJs`，无法区分
4. **无多图支持**：PhotoDialog 只加载一张图片，无法做相册浏览

## 三、coverDecodeJs 在图片加载中的作用

### 3.1 触发时机

`coverDecodeJs` 在 Glide 加载图片时通过 `ImageUtils` 触发：

```
PhotoDialog
  → ImageLoader.load(context, src)
    → Glide 自定义 ModelLoader
      → OkHttpModelLoader（网络请求）
        → ImageUtils.decode() 拦截字节流
          → isKnownImageFormat() 检测是否已知图片格式
            → 已知格式 → 跳过解密
            → 未知格式 → 执行 coverDecodeJs 解密
```

### 3.2 RssSource vs BookSource 的解密差异

```kotlin
// ImageUtils.kt:110-120
private fun getRuleJs(source: BaseSource?, isCover: Boolean): String? {
    return when (source) {
        is BookSource ->
            if (isCover) source.coverDecodeJs      // 封面用 coverDecodeJs
            else source.getContentRule().imageDecode  // 正文用 imageDecode
        is RssSource -> source.coverDecodeJs         // 封面和正文都用 coverDecodeJs
        else -> null
    }
}
```

**结论**：对于 RssSource，`isCover` 参数被忽略，封面和正文图片解密都使用 `coverDecodeJs`。如果某个源封面和正文需要不同的解密逻辑，RssSource 无法支持。

## 四、图片类型订阅源配置示例

### 4.1 图片直链源（无 ruleContent）

```json
{
  "sourceUrl": "https://example.com/feed",
  "sourceName": "图片源A",
  "type": 1,
  "ruleArticles": "css selector for items",
  "ruleTitle": "css selector for title",
  "ruleImage": "css selector for thumbnail",
  "ruleLink": "css selector for image direct URL",
  "ruleContent": null
}
```

- 点击后直接用 `ruleLink` 提取的URL作为图片URL
- PhotoDialog 加载该URL显示大图

### 4.2 需要解析详情页的图片源（有 ruleContent）

```json
{
  "sourceUrl": "https://example.com/feed",
  "sourceName": "图片源B",
  "type": 1,
  "ruleArticles": "css selector for items",
  "ruleTitle": "css selector for title",
  "ruleImage": "css selector for thumbnail",
  "ruleLink": "css selector for detail page URL",
  "ruleContent": "@css:.main-image img@src"
}
```

- 点击后先用 `ruleLink` 获取详情页URL
- 请求详情页HTML
- 用 `ruleContent` 从HTML提取图片URL
- PhotoDialog 加载该URL显示大图

### 4.3 需要解密的图片源

```json
{
  "sourceUrl": "https://example.com/feed",
  "type": 1,
  "coverDecodeJs": "java.perform('javax.crypto.Cipher', 'getInstance', 'AES/ECB/PKCS5Padding').call('init', 1, key).call('doFinal', result)",
  "ruleContent": "@css:img.encrypted@src"
}
```

- 加载图片时自动通过 `coverDecodeJs` 解密
- 但封面缩略图和正文大图使用相同解密逻辑

## 五、源码关键文件索引

| 文件 | 关键行 | 说明 |
|------|--------|------|
| [ReadRss.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt) | L84 type判断, L164-189 readNoHtml | 图片源阅读路由 |
| [Rss.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt) | L117-166 getContentAwait | 详情页请求+ruleContent提取 |
| [RssParserByRule.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt) | L79 ruleImage, L160-169 image赋值 | 列表缩略图提取 |
| [PhotoDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/dialog/PhotoDialog.kt) | L43-71 图片加载 | 大图显示（Glide+解密） |
| [ImageUtils.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/ImageUtils.kt) | L106-121 getRuleJs | 图片解密路由 |
| [RssSource.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/RssSource.kt) | L47 coverDecodeJs, L68 ruleImage, L72 ruleContent | 实体定义 |
