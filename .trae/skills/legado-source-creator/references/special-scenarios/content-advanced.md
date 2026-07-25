# 详情页/正文高级技巧

> 详情页规则（BookInfoRule）和正文规则（ContentRule）的高级写法，涵盖 URL 拼接、去章节名、去重复、翻页断句、图片处理、漫画/听书源等场景。
> 所有内容已通过 Legado 源码确认。

---

## 1. URL 拼接六种方式

章节列表中的 URL 通常是相对路径，需要拼接为完整 URL。

### 方式一：`##^##` 在前面添加（正则锚点组合）

```
##^##https://whts.com
```

- `##` 是规则分隔符，`^` 是正则"行首"锚点，`##` 后为替换内容
- `result.replace(Regex("^"), "https://whts.com")` 等效于在结果前面添加
- 例：`/book/123.html` → `https://whts.com/book/123.html`

> **注意**：这不是专用语法，而是 `##` 分隔符 + 正则 `^` 锚点的组合效果。源码依据：AnalyzeRule.kt L762-773。

### 方式二：`##$##` 在后面添加（正则锚点组合）

```
##$##/sadly_1.html
```

- `$` 是正则"行尾"锚点，`result.replace(Regex("$"), "/sadly_1.html")` 等效于在结果后面添加
- 例：`https://example.com/book/123` → `https://example.com/book/123/sadly_1.html`

> **注意**：同上，是 `##` 分隔符 + 正则 `$` 锚点的组合效果。

### 方式三：JS 拼接

```
@js:'https://xxx.com'+result
```

- `result` 是当前规则匹配的结果
- 适合需要复杂逻辑的拼接

### 方式四：JS 替换域名

```
@js:result.replace('www.xxx','k.xxx')
```

- 替换域名用于切换 CDN 或移动端适配
- 例：`https://www.xxx.com/book/123` → `https://k.xxx.com/book/123`

### 方式五：`{{baseUrl}}` 使用当前页 URL

```
{{baseUrl}}
```

- `baseUrl` 是 AnalyzeUrl 解析时的当前页面 URL
- 适合目录与详情页共用同一 URL 的场景

### 方式六：`{{baseUrl}}` 当前页 URL + 路径拼接

```
{{baseUrl}}list.html
```

- `{{baseUrl}}` 代表当前页面的 URL（含域名和路径）
- 例：当前页为 `https://example.com/book/123/` → `https://example.com/book/123/list.html`

> **注意**：`{{$.}}` 不是合法语法，JS 绑定中没有定义 `$` 变量，会报 `ReferenceError`。正确写法是 `{{baseUrl}}`。

---

## 2. 正文去章节名五种写法

正文内容开头常包含章节名，需要通过替换规则去除。

### 写法一：最简写法

```
##{{chapter.title}}
```

- 直接用章节标题作为替换匹配
- `chapter` 是 Legado 内置变量，`.title` 对应当前章节名

### 写法二：使用全局对象

```
##{{book.durChapterTitle}}
```

- `book` 是全局 Book 对象，`durChapterTitle` 是当前阅读章节标题
- 适合在 JS 规则中使用

### 写法三：JS 中用 title 变量构建正则替换

```javascript
var title = chapter.title;
result = result.replace(new RegExp(title + '\\s*\\n*'), '');
```

### 写法四：JS 中用 book.durChapterTitle 构建模糊匹配正则

```javascript
var title = book.durChapterTitle;
// 容错：章节名中可能含空格或特殊字符
var escaped = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
result = result.replace(new RegExp(escaped + '[\\s\\S]*?\\n{2}'), '');
```

### 写法五：JS 中用 split+join 构建容错正则

```javascript
var title = book.durChapterTitle;
// 将章节名拆分为字符数组，中间插入 \s* 容错
var pattern = title.split('').join('\\s*');
result = result.replace(new RegExp(pattern), '');
```

**适用场景**：正文开头重复显示章节名、目录页标题与正文标题格式不同。

---

## 3. 正文去重复段落

部分网站正文存在连续重复段落，需要去重。

### 替换规则

```
##([^\n]+)\s*\n\s*\1##$1
```

**解析**：
- `([^\n]+)` 匹配一行内容（捕获组1）
- `\s*\n\s*` 匹配换行及前后空白
- `\1` 反向引用，匹配与捕获组1相同的内容（即重复行）
- `##$1` 替换为只保留一行

**适用场景**：正文每段重复出现两次、采集源数据异常导致段落重复。

---

## 4. 正文段落拼接（翻页断句修复）

部分网站分页时在段落中间断开，导致翻页后段落不完整。

### 替换规则

```
##(?<=[\u4e00-\u9fa5])\n(?=[\u4e00-\u9fa5])## 
```

**解析**：
- `(?<=[\u4e00-\u9fa5])` 正向后行断言：前一个字符是汉字
- `\n` 匹配换行符
- `(?=[\u4e00-\u9fa5])` 正向先行断言：后一个字符是汉字
- 替换为空格，将两行合并为一行

**原理**：正常段落结尾通常是句号等标点，如果上一行末尾是汉字且下一行开头也是汉字，说明是翻页断句，需要拼接。

**适用场景**：正文翻页处断句、段落被硬换行截断。

---

## 5. 正文图片修改 Headers

部分图片服务器需要特定的 Referer 或 User-Agent 才能访问，需要在图片 URL 中附加 headers。

### 写法

```javascript
var list = result.match(/data-original="[^"]+"/g);
var imgs = [];
for (var i = 0; i < list.length; i++) {
    var src = list[i].match(/data-original="([^"]+)"/)[1];
    var options = {"headers": {"User-Agent": "xxx", "Referrer": baseUrl}};
    imgs.push('<img src="' + src + ',' + JSON.stringify(options) + '">');
}
result = imgs.join('\n');
```

**关键点**：
- 图片 URL 后用逗号拼接 JSON 格式的 options 对象
- `Referrer`（注意拼写）是图片防盗链的关键 header
- Legado 的图片加载器会解析逗号后的 JSON 作为请求 headers

**适用场景**：图片 403 Forbidden、图片防盗链、图片需要特定 UA。

---

## 6. 漫画源正文

漫画源（bookSourceType=2）的正文规则与文字源不同，核心是图片列表。

### 图片懒加载处理

```
class.img@data-original##^##https:##data-original→src
```

- `data-original` 是懒加载属性名，需替换为 `src` 让 Legado 识别
- `##^##https:` 补全协议头（部分网站省略 `https:`）

### imageStyle 设置

```json
{
  "imageStyle": "FULL"
}
```

- `FULL`：图片全宽显示，适合漫画
- 其他值：`WIDE`（宽图）、`CENTER`（居中）、`CUSTOM`（自定义）

**适用场景**：漫画源图片懒加载、图片 URL 缺少协议头。

---

## 7. 听书源正文

听书源（bookSourceType=1）的正文规则返回音频 URL 列表。

### 正文规则

```
<js>result</js>
```

- 听书源正文规则通常只需返回原始内容
- Legado 会根据资源正则自动提取音频 URL

### 资源正则

```
.*\.(mp3|m4a).*
```

- 匹配所有 mp3 或 m4a 格式的音频 URL
- Legado 会用此正则从页面中嗅探音频资源

**适用场景**：有声小说、播客源。

---

## 8. 封面 URL 通过 ID 计算拼接

部分网站的封面图片路径由书籍 ID 计算得出。

### 提取 ID

```
a@href##.*/(\d+)/##$1
```

- 从链接中提取数字 ID
- 例：`/book/12345/` → `12345`

### JS 计算封面路径

```javascript
var id = result;  // 上一步提取的 ID
var dir = parseInt(id / 1000);
result = 'https://img.example.com/' + dir + '/' + id + '.jpg';
```

- `parseInt(id / 1000)` 计算千位目录
- 例：ID=12345 → dir=12 → `https://img.example.com/12/12345.jpg`

**适用场景**：封面 URL 含计算目录、封面路径有规律但非直接可获取。

---

## 9. onclick 属性章节 URL 处理

部分网站章节链接不是 `<a href>` 而是 `onclick` 事件，需要从中提取 URL。

### 提取 onclick 中的 URL

```
onclick##'([^']+)##$1###`
```

**解析**：
- `onclick` 属性选择器，获取 onclick 属性值
- `##'([^']+)` 第一个替换规则：匹配单引号内的内容（捕获组1）
- `##$1` 替换为捕获组1（即 URL）
- `###` 结束替换标记

**示例**：
- onclick 值：`javascript:openChapter('/read/123.html')`
- 提取结果：`/read/123.html`

**适用场景**：章节链接使用 JS 事件而非 href、页面使用前端路由。
