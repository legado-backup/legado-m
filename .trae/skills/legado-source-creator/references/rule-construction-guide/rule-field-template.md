# 规则字段填写模板

> ruleSearch/ruleBookInfo/ruleToc/ruleContent 四个规则段的填写模板。
> 字段定义参见 [../booksource-schema.md](../booksource-schema.md)，语法参见 [../rule-syntax.md](../rule-syntax.md)。

## 一、ruleSearch（搜索规则）

### 必填字段

| 字段 | 说明 | CSS 示例 | JSONPath 示例 |
|------|------|----------|---------------|
| `bookList` | 搜索结果列表项 | `.book-item` 或 `div.result-list > div.item` | `$.data.list` |
| `name` | 书名 | `.title@text` 或 `h3 a@text` | `$.title` |
| `bookUrl` | 详情页 URL | `a.title@href` 或 `.book-info a@href` | `$.url` |

### 可选字段

| 字段 | 说明 | CSS 示例 | JSONPath 示例 |
|------|------|----------|---------------|
| `author` | 作者 | `.author@text` 或 `span.author@text` | `$.author` |
| `coverUrl` | 封面图 URL | `img.cover@src` 或 `.book-img img@src` | `$.cover` |
| `intro` | 简介 | `.intro@text` | `$.intro` |
| `kind` | 分类 | `.tag@text` | `$.category` |
| `lastChapter` | 最新章节 | `.latest@text` | `$.lastChapter` |
| `updateTime` | 更新时间 | `.update@text` | `$.updateTime` |
| `wordCount` | 字数 | `.words@text` | `$.wordCount` |
| `checkKeyWord` | 校验关键字 | `"斗破苍穹"` | 同左 |

## 二、ruleBookInfo（详情规则）

### 必填字段

| 字段 | 说明 | CSS 示例 | JSONPath 示例 |
|------|------|----------|---------------|
| `name` | 书名 | `h1.book-title@text` | `$.data.name` |
| `tocUrl` | 目录页 URL（与详情不同页时） | `a.catalog@href` | `$.tocUrl` |

> 若详情页和目录页是同一页，`tocUrl` 留空。

### 可选字段

| 字段 | 说明 | CSS 示例 |
|------|------|----------|
| `author` | 作者 | `span.author@text` |
| `coverUrl` | 封面 | `img.cover@src` |
| `intro` | 简介 | `div.intro@html` |
| `kind` | 分类 | `div.tags@text` |
| `lastChapter` | 最新章节 | `div.latest-chapter@text` |
| `updateTime` | 更新时间 | `span.update-time@text` |
| `wordCount` | 字数 | `span.word-count@text` |
| `init` | 初始化 JS | `<js>java.put('token', 'xxx')</js>` |
| `canReName` | 允许重命名 | `1`（有值即可） |
| `downloadUrls` | 下载链接（文件源） | `a.download@href` |

## 三、ruleToc（目录规则）

### 必填字段

| 字段 | 说明 | CSS 示例 | JSONPath 示例 |
|------|------|----------|---------------|
| `chapterList` | 章节列表项 | `ul.chapter-list li` 或 `dd a` | `$.data.chapters` |
| `chapterName` | 章节名 | `a@text` | `$.title` |
| `chapterUrl` | 章节 URL | `a@href` | `$.url` |

### 可选字段

| 字段 | 说明 | CSS 示例 |
|------|------|----------|
| `nextTocUrl` | 下一页目录 URL | `a.next-page@href` |
| `isVolume` | 是否卷标 | `.volume@text`（有值则标记为卷） |
| `isVip` | 是否 VIP | `.vip-icon@text` |
| `isPay` | 是否付费 | `.pay-icon@text` |
| `updateTime` | 更新时间 | `span.time@text` |
| `preUpdateJs` | 更新前 JS | `<js>// 预处理逻辑</js>` |
| `formatJs` | 列表格式化 JS | `<js>// 格式化章节列表</js>` |

## 四、ruleContent（正文规则）

### 必填字段

| 字段 | 说明 | CSS 示例 | JSONPath 示例 |
|------|------|----------|---------------|
| `content` | 正文内容 | `div.content@html` 或 `#booktext@html` | `$.data.content` |

### 可选字段

| 字段 | 说明 | CSS 示例 |
|------|------|----------|
| `nextContentUrl` | 下一页正文 URL | `a.next@href` |
| `title` | 正文页标题 | `h1.chapter-title@text` |
| `subContent` | 副文（歌词等） | `div.lyrics@html` |
| `replaceRegex` | 正文替换正则 | `##广告文字##` 或 `##<script[\\s\\S]*?</script>##` |
| `imageStyle` | 图片样式 | `FULL`（最大宽度） |
| `webJs` | 页面加载后 JS | `<js>// 滚动加载等</js>` |
| `sourceRegex` | 来源正则 | `.*\\.m3u8.*`（视频嗅探） |
| `imageDecode` | 图片解密 JS | `<js>// 解密 bytes</js>` |
| `payAction` | 购买操作 | `<js>// 购买逻辑</js>` |
| `callBackJs` | 事件回调 JS | `<js>// 回调逻辑</js>` |

## 五、常见错误填写模式

| 错误模式 | 错误写法 | 正确写法 | 原因 |
|----------|----------|----------|------|
| 标签名当 class | `div@text`（想取 class=div 的元素） | `.div@text` 或 `class.div@text` | `div` 是标签名不是 class |
| class 漏写前缀 | `content@text`（想取 class=content） | `.content@text` | 无前缀会被当标签名 |
| href 漏 @ | `a@href` 写成 `a href` | `a@href` | 属性提取必须用 `@` |
| JSONPath 漏 $ | `data.title` | `$.data.title` | JSONPath 必须以 `$.` 开头 |
| 正则未转义 | `##.jpg##` | `##\\.jpg##` | `.` 在正则中匹配任意字符 |
| JS 中用 @get | `<js>var x = @get:{key}</js>` | `<js>var x = java.get('key')</js>` | JS 中必须用 `java.get()` |
| OnlyOne 未匹配丢内容 | `##xyz##替换###` | `##xyz##替换`（不加 `###`） | OnlyOne 未匹配返回空字符串 |

## 六、字段间依赖关系

```
ruleSearch.bookUrl ──→ ruleBookInfo（详情页 URL 来源）
ruleBookInfo.tocUrl ──→ ruleToc（目录页 URL 来源，留空则用详情页）
ruleToc.chapterUrl ──→ ruleContent（正文页 URL 来源）
ruleContent.nextContentUrl ──→ 自身（多页正文翻页）
ruleToc.nextTocUrl ──→ 自身（多页目录翻页）
```

> **关键依赖**：`bookUrl` 必须返回有效 URL，否则后续所有阶段失败。`tocUrl` 留空时 Legado 默认使用详情页 URL 作为目录页。

## 七、字段填写检查清单

- [ ] `bookList` 返回的是列表项元素（多个），不是单个
- [ ] `bookUrl`/`chapterUrl` 返回的是 URL（相对路径会被自动拼接 baseUrl）
- [ ] `content` 用 `@html` 而非 `@text`（保留格式）
- [ ] URL 字段用 `@href`/`@src` 而非 `@text`
- [ ] JSONPath 字段以 `$.` 开头
- [ ] 正则中特殊字符已转义（`.[](){}*+?^$|`）
- [ ] JS 规则中变量用 `java.get()`/`java.put()` 而非 `@get`/`@put`
