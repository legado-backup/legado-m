# 5种网站类型规则构建策略

> 针对小说/漫画/音频/视频/论坛五种网站类型的规则构建策略。
> 通用语法参见 [../rule-syntax.md](../rule-syntax.md)，字段定义参见 [../booksource-schema.md](../booksource-schema.md)。
> 特殊场景（加密/登录/视频）详见 [../special-scenarios/_index.md](../special-scenarios/_index.md)。

## 一、小说站

**bookSourceType**: 0（文本）

### 典型 HTML 结构

```html
<!-- 列表页 -->
<div class="book-item">
  <a href="/book/123.html" class="title">书名</a>
  <span class="author">作者</span>
  <img src="/cover/123.jpg" class="cover">
</div>

<!-- 详情页 -->
<h1 class="book-title">书名</h1>
<span class="author">作者</span>
<div class="intro">简介...</div>

<!-- 目录页 -->
<ul class="chapter-list">
  <li><a href="/chapter/123/1.html">第一章</a></li>
</ul>

<!-- 正文页 -->
<div id="booktext">正文内容...</div>
```

### 常用选择器

| 字段 | 常用选择器 |
|------|-----------|
| bookList | `.book-item` 或 `div.result-item` |
| name | `a.title@text` 或 `h3 a@text` |
| bookUrl | `a.title@href` 或 `a@href` |
| author | `.author@text` 或 `span.author@text` |
| coverUrl | `img.cover@src` 或 `.book-img img@src` |
| chapterList | `ul.chapter-list li` 或 `dd` |
| chapterName | `a@text` |
| chapterUrl | `a@href` |
| content | `#booktext@html` 或 `div.content@html` |

### 常见陷阱

- **相对 URL 未拼接**：`a@href` 返回 `/book/123.html`，Legado 自动拼接 baseUrl，无需手动处理
- **正文用 @text 丢格式**：必须用 `@html` 保留段落和换行
- **目录默认反转**：Legado 默认 `reverse()` 目录列表，最新章节在前会变成在后；需保持原序用 `-` 前缀
- **广告混入正文**：用 `replaceRegex` 清洗，如 `##<script[\\s\\S]*?</script>##`

## 二、漫画站

**bookSourceType**: 2（图片）

### 图片 URL 提取

```javascript
// 常见模式1：img 标签 src
"content": "div.comic-images img@src"

// 常见模式2：data-src 懒加载
"content": "div.comic-images img@data-src"

// 常见模式3：JS 变量中存储图片列表
"content": "<js>var imgs = result.match(/var images = \\[([^\\]]+)\\]/);imgs[1]</js>"
```

### 防盗链处理

| 防盗链类型 | 处理方式 |
|-----------|----------|
| Referer 校验 | `header` 字段配置 `{"Referer":"https://site.com"}` |
| Cookie 校验 | `enabledCookieJar: true` |
| 图片 URL 加密 | `imageDecode` 字段写 JS 解密 |
| 图片 bytes 加密 | `imageDecode` 字段返回解密后的 bytes |

### 分页策略

```json
{
  "content": "div.comic-images img@src",
  "nextContentUrl": "a.next-page@href"
}
```

> 漫画站常见多页：一章漫画分多页加载，用 `nextContentUrl` 翻页拼接。

## 三、音频站

**bookSourceType**: 1（音频）

### 音频 URL 提取

```javascript
// 常见模式1：audio 标签
"content": "audio@src"

// 常见模式2：JS 变量中存储
"content": "<js>result.match(/var audioUrl = '([^']+)'/)[1]</js>"

// 常见模式3：API 返回 JSON
"content": "$.data.audioUrl"
```

### 播放列表解析

```json
{
  "ruleContent": {
    "content": "$.data.audioUrl",
    "title": "$.data.title"
  }
}
```

> 音频站常将章节作为"书"，每集音频作为"章节"。`chapterUrl` 指向单集，`content` 提取音频 URL。

## 四、视频站

**bookSourceType**: 4（视频）

### 视频 URL 提取

```javascript
// 常见模式1：m3u8 嗅探
"content": "<js>java.webViewGetSource(null, baseUrl, null, \".*\\.m3u8.*\")</js>"

// 常见模式2：API 返回播放地址
"content": "$.data.playUrl"

// 常见模式3：JS 解密
"content": "<js>var enc = result.match(/var video = '([^']+)'/)[1];java.decrypt(enc)</js>"
```

### 加密解密

| 加密类型 | 处理方式 | 参考文档 |
|----------|----------|----------|
| AES/DES | JS 调用 CryptoJS | [../special-scenarios/encryption.md](../special-scenarios/encryption.md) |
| Base64 变种 | JS 自定义解码 | [../troubleshooting/crypto-traps.md](../troubleshooting/crypto-traps.md) |
| URL 编码混淆 | JS `decodeURIComponent` | [../js-patterns/](../js-patterns/_index.md) |

### m3u8 解析

```json
{
  "ruleContent": {
    "content": "<js>java.webViewGetSource(null, baseUrl, null, \".*\\.m3u8.*\")</js>",
    "sourceRegex": ".*\\.m3u8.*"
  }
}
```

> 视频站通常需要 `@webjs:` 或 `webViewGetSource` 嗅探播放地址。详见 [../special-scenarios/video-audio.md](../special-scenarios/video-audio.md)。

## 五、论坛站

**bookSourceType**: 0（文本，帖子作为章节）

### 帖子结构

```html
<!-- 帖子列表 -->
<div class="thread-item">
  <a href="/thread/123" class="thread-title">帖子标题</a>
  <span class="author">楼主</span>
  <span class="replies">回复数</span>
</div>

<!-- 帖子内容 -->
<div class="post-content">
  <div class="post-floor">1楼</div>
  <div class="post-body">帖子正文...</div>
</div>
```

### 分页处理

```json
{
  "ruleToc": {
    "chapterList": "div.thread-item",
    "chapterName": "a.thread-title@text",
    "chapterUrl": "a.thread-title@href",
    "nextTocUrl": "a.next-page@href"
  },
  "ruleContent": {
    "content": "div.post-body@html",
    "nextContentUrl": "a.next-page@href"
  }
}
```

### 回复解析

```javascript
// 提取所有楼层内容（合并为一章）
"content": "div.post-body@html"

// 或用 %% 交错合并楼层和楼号
"content": "div.post-body@html%%div.post-floor@text"
```

### 常见陷阱

- **帖子分页 vs 章节分页**：论坛帖子本身分页（回复分页）用 `nextContentUrl`，帖子列表分页用 `nextTocUrl`
- **登录可见内容**：需配置 `loginUrl` + `loginUi`，详见 [../special-scenarios/login.md](../special-scenarios/login.md)
- **引用块混入正文**：用 `replaceRegex` 清洗，如 `##<blockquote[\\s\\S]*?</blockquote>##`
- **楼层广告**：用 `-` 前缀排除广告楼层，如 `-div.ad-post@html`

## 六、通用策略速查

| 网站类型 | 主解析方式 | 关键字段 | 特殊处理 |
|----------|-----------|----------|----------|
| 小说站 | CSS | content, chapterList | replaceRegex 清洗广告 |
| 漫画站 | CSS + JS | content(img@src), imageDecode | 防盗链 header |
| 音频站 | JSONPath/CSS | content(audio@src) | 章节即音频集 |
| 视频站 | WebView JS | content, sourceRegex | m3u8 嗅探 |
| 论坛站 | CSS | chapterList, nextContentUrl | 登录+清洗引用块 |
