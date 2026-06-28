# 规则语法详解

> 五种解析方式的详细语法、组合规则、多页处理策略。

## 一、CSS 选择器（默认模式）

**引擎**: jsoup 1.16.2
**前缀**: 无（默认），也可显式用 `@CSS:`（大小写不敏感）

> ⚠️ **@CSS: 前缀剥离位置**：`AnalyzeRule.SourceRule` 检测到 `@CSS:` 前缀后设置 `mode=Default`，但**不剥离前缀**，rule 保留原始 ruleStr。前缀由 `AnalyzeByJSoup.SourceRule` 在内部剥离（`ruleStr.substring(5).trim()`）。

### 基本格式

```
CSS选择器[@属性关键字]
```

### 特殊属性关键字

| 关键字 | 含义 | 示例 |
|--------|------|------|
| `text` | 元素纯文本（默认） | `h1@text` 等价于 `h1` |
| `textNodes` | 直接文本节点（不含子元素文本） | `div@textNodes` |
| `ownText` | 仅元素自身文本 | `span@ownText` |
| `html` | innerHTML | `div.content@html` |
| `all` | outerHTML（含元素本身标签） | `div@all` |
| `属性名` | 提取指定属性 | `img@src`, `a@href`, `div@class` |

### 级联语法 `@`

```
外层选择器@内层选择器@...
```

示例：
```
div.card@h3.title@text     → 先选div.card → 再选h3.title → 取文本
div.card@a@href            → 先选div.card → 再选a → 取href
```

### 取反语法 `-`

```
-规则
```

示例：
```
-div.ad@text     → 排除所有div.ad后的文本
```

### 索引语法

传统格式：`规则.索引:起始:步长`
数组格式：`规则[-1, 3:-2:-10, 2]`

```
div.item@text.0:1:2    → 第0个起，步长2
div.item@text[-1]      → 最后一个
div.item@text[1,-1]    → 第2个和最后一个
div.item@text[2:5]     → 第2到第5个
```

---

## 二、JSONPath（`$.` 前缀）

**引擎**: json-path
**前缀**: `$.` (当前节点) / `$..` (递归)

> 注：`@.` 作为规则前缀在源码中不被支持（AnalyzeRule.kt L623 仅判断 `$.` 和 `$[`）。`@.` 仅在 JSONPath 过滤表达式内作为当前节点引用使用，如 `$.data[?(@.type=='novel')]`。

### 基本格式

```
$.路径表达式[@属性]
```

### 常用路径

| 路径 | 含义 |
|------|------|
| `$.data.*` | data下的所有直接子节点 |
| `$..name` | 递归搜索所有name字段 |
| `$.data[0].name` | 数组第一个元素的name |
| `$.data[?(@.type=='novel')]` | 过滤type==novel的元素 |
| `$.data[*].title` | 所有元素的title |
| `$.data[-1]` | 最后一个元素 |

### 与JS混合

```jsonpath
$.data[*].{$.name}
```
表示：对 data 的每个元素，用 JavaScript 计算 `$.name`。

---

## 三、XPath（`//` 或 `@xpath:` 前缀）

**引擎**: JsoupXpath
**前缀**: `//` 或 `@xpath:`

### 基本格式

```
//xpath表达式
```

### 常用速查

| XPath | 含义 |
|-------|------|
| `//h1/text()` | 所有h1的文本 |
| `//div[@class='content']//p` | class=content的div下所有p |
| `//a/@href` | 所有a的href属性 |
| `//li[position()>1]/a/text()` | 第2个起li>a的文本 |
| `contains(@class, 'title')` | class包含title的元素 |

---

## 四、正则表达式（`##` 或 `@regex:` 前缀）

**引擎**: Java Regex
**前缀**: `##` 或 `@regex:`

### 基本格式

```
##正则表达式##替换内容##分组序号
```

### 常用写法

```
##(\\d+)万字##$1          → 提取"123万字"中的"123"
##<img src="([^"]+)"      → 提取图片src
##[\\s\\S]*?正文([\\s\\S]*?)下一章 → 提取正文内容
```

**注意**: 如果前面有 CSS/XPath 规则，正则会作用于前一个规则的结果。

---

## 五、JavaScript（`@js:` 或 `<js>` 前缀）

**引擎**: Rhino 1.8.1（ES5 兼容）
**前缀**: `<js>代码</js>` 或 `@js:代码`

### 基本格式

```javascript
<js>
// 可直接使用 result 变量(上一个规则的结果)
// 可直接使用 baseUrl, book 等全局变量
result = result.replace(/广告/g, '');
result;
</js>
```

### 可用全局变量（书源执行上下文）

| 变量 | 类型 | 说明 |
|------|------|------|
| `result` | String | 上一条规则的结果 |
| `baseUrl` | String | 当前页面 URL |
| `book` | Book | 当前书籍对象 |
| `cookie` | String | Cookie 字符串 |
| `source` | BookSource | 当前书源对象 |
| `java` | Object | Java 互操作入口 |

---

## 五-B、WebView JS（`@webjs:` 前缀）

**引擎**: BackstageWebView（Android WebView 后台执行）
**前缀**: `@webjs:代码`（大小写不敏感，代码部分最少5个字符）

> 源码：`AppPattern.WebJS_PATTERN = @webjs:([\w\W]{5,})`
> 处理位置：`RuleAnalyzer.splitRule()` 中通过正则匹配，创建 `SourceRule(group(1), Mode.WebJs)`，前缀在匹配时已剥离。

### 基本格式

```
@webjs:JavaScript代码（至少5字符）
```

### 与 `@js:` 的区别

| 特性 | `@js:` | `@webjs:` |
|------|--------|-----------|
| 执行引擎 | Rhino (纯 Java) | Android WebView |
| DOM 环境 | ❌ 无 | ✅ 有完整浏览器 DOM |
| 适用场景 | 数据处理、加密解密 | 需要 DOM 渲染、执行页面 JS |
| 性能 | 快 | 较慢（需启动 WebView） |
| 代码长度限制 | 无 | 最少5字符 |

---

## 六、规则组合符详解

### `&&` — 合并去重

```
规则A&&规则B
```

结果 = 规则A结果 + 规则B结果（去重），拼接为 `\n` 分隔。

### `||` — 按序尝试

```
规则A||规则B||规则C
```

依次尝试 A、B、C，取第一个有结果的。（源码：AnalyzeByJSoup.kt L104-107，`if (!temp.isNullOrEmpty()) { results.add(temp); if (ruleAnalyzes.elementsType == "||") break }`）

典型用法：
```
span.author@text||p.author@text||div.writer@text
```

**⚠️ 搜索结果与列表页兼容场景**（RssSource 高频使用）：
当 RssSource 配置了 searchUrl 时，搜索结果复用 ruleArticles/ruleTitle/ruleLink 等规则。但搜索结果的 HTML 结构可能与列表页不同，此时用 `||` 兼容两种页面：
```
# 列表页标题链接有 class="subject"，搜索结果页标题链接无 class
ruleLink: class.subject@href||tag.a.0@href

# 列表页标题用 class="subject" 精确匹配，搜索结果页回退到第一个 a 标签
ruleTitle: class.subject@text||tag.a.0@text

# 列表页图片在 <a class="lazy-imgs"> 上，搜索结果页图片在 <img> 上
ruleImage: class.lazy-imgs.0@data-src||tag.img.0@data-src
```

### `%%` — 交错合并

```
规则A%%规则B
```

结果 = [A[0], B[0], A[1], B[1], ...]（三明治结构）

典型用法（搜索列表）：
```
div.item a@text%%div.item a@href
→ 书名1, URL1, 书名2, URL2, ...
```

### `##` — 正则提取

```
CSS规则##正则
```

先执行 CSS 规则，再对结果执行正则提取。

### `{$.rule}` — 内嵌 JSONPath

```jsonpath
$.data[*].{$.title%%.url}
```

在 JSONPath 路径中嵌入其他解析规则。

### `-` — 阻止默认反转

```
-规则
```

`-` 前缀**不是"取反"语法**，而是"阻止默认反转"的标记。

> **源码确认**：BookChapterList.kt L54-56 和 L124-126。Legado 默认会对目录/搜索列表执行 `reverse()` 反转（因为网页目录通常最新在前），`-` 前缀设置 `reverse=true` 来阻止这个默认反转，保持原始顺序。

### `+` — 保持默认顺序（阻止反转）

```
+规则
```

`+` 前缀仅剥离前缀，**不实现排序**。它显式标记"保持默认顺序"。

> **源码确认**：BookChapterList.kt L58-59 和 BookList.kt L94-96，`+` 前缀仅执行 `listRule.substring(1)` 剥离前缀，无任何排序操作。

### `-` — 阻止默认反转

```
-规则
```

`-` 前缀**不是"取反"语法**，而是"阻止默认反转"的标记。

> **源码确认**：BookChapterList.kt L54-56 和 L124-126。Legado 默认会对目录/搜索列表执行 `reverse()` 反转（因为网页目录通常最新在前），`-` 前缀设置 `reverse=true` 来阻止这个默认反转，保持原始顺序。

---

## 七、多页处理

### 正文多页

**顺序翻页**（默认）：
```json
{
  "content": "div.content@html",
  "nextContentUrl": "a.next-page@href"
}
```
引擎自动跟随 `nextContentUrl` 逐页获取，直到 `nextContentUrl` 为空。

**并发多页**（效率更高）：
- 通过 `webJs` 在 JS 中一次性获取所有页面 URL，并发请求。

### 目录多页

```json
{
  "chapterList": "ul.chapter > li",
  "nextTocUrl": "a.next@href"
}
```
与正文多页逻辑相同，`nextTocUrl` 非空时自动翻页。

### 搜索多页

SearchRule 的 `searchUrl` 中使用 `{{page}}` 即可：
```
/search?keyword={{key}}&page={{page}}
```

### 发现多页

ExploreRule 同理：
```
/category/top/{{page}}
```

---

## 八、规则优先级与执行顺序

1. **SourceRule** 解析 — 匹配 `@CSS:`, `@xpath:`, `@Json:`, `@webjs:`, `$.`, 前缀决定 Mode（AnalyzeRule.kt L601-634）
2. `@js:` / `<js></js>` — 在 `splitSourceRule()` 方法中通过 `JS_PATTERN` 正则匹配（AnalyzeRule.kt L545-555），不在 SourceRule.init 块中
3. 无前缀 → 默认 CSS 模式
3. `&&` / `||` → 按分割符拆分子规则，递归处理
4. `%%` → 交错合并
5. JS 子规则（`<js>` 或 `@js:`）→ 注入上下文后执行
6. WebJs 子规则（`@webjs:`）→ BackstageWebView 执行

### Mode 枚举（6 种）

| Mode | 值 | 触发条件 |
|------|-----|----------|
| `XPath` | 0 | `//` 或 `@XPath:` 开头 |
| `Json` | 1 | `$.` 或 `$[` 开头，或 `@Json:` 前缀 |
| `Default` | 2 | `@CSS:` 或 `@@` 前缀，或无前缀（CSS） |
| `Js` | 3 | `<js>` 或 `@js:` |
| `Regex` | 4 | `##` 或 `@regex:` 开头，或强制 mode=Regex |
| `WebJs` | 5 | `@webjs:` 前缀（代码≥5字符） |

---

## 九、Default 语法详解

> Default 语法是 Legado 原生简写语法，无前缀时自动使用。本质上是 CSS 选择器的扩展简写形式。

### 5 个关键字前缀

| 前缀 | 含义 | 示例 |
|------|------|------|
| `class.` | 按 class 名选择 | `class.book-item` → 选择 class 为 book-item 的元素 |
| `tag.` | 按标签名选择 | `tag.div` → 选择所有 div 元素 |
| `id.` | 按 id 选择 | `id.header` → 选择 id 为 header 的元素 |
| `text.` | 按文本内容选择 | `text.目录` → 选择文本为"目录"的元素 |
| `children` | 选择子元素 | `children` → 选择所有子元素 |

### 简写规则

| 完整写法 | 简写 | 说明 |
|----------|------|------|
| `class.名称` | `.名称` | class 前缀可省略为 `.` |
| `id.名称` | `#名称` | id 前缀可省略为 `#` |

示例：
```
class.title@text  →  .title@text
id.content@html   →  #content@html
```

### 位置索引

**旧式索引**（点号分隔）：
```
.0    → 第1个元素
.1    → 第2个元素
.-1   → 最后1个元素
```

**新式索引**（方括号，支持切片）：
```
[0:10]     → 第0到第9个元素
[-1:0]     → 倒序取所有元素
[!0:-1]    → 排除第0个，取到倒数第2个
```

### 属性选择器

| 选择器 | 含义 | 示例 |
|--------|------|------|
| `[^=]` | 属性以指定值开头 | `[class^=book]` |
| `[$=]` | 属性以指定值结尾 | `[property$=book_name]@content` |
| `[~=]` | 属性包含指定词 | `[class~=active]` |

示例：
```
meta[property$=book_name]@content    → 提取 property 以 book_name 结尾的 meta 标签的 content 属性
div[class^=chapter]@text             → 提取 class 以 chapter 开头的 div 文本
```

### @ 连接可用空格替代

```
class.xxx@li@a@text  =  .xxx li a@text
```

两者等价：空格替代 `@` 连接选择器，更接近标准 CSS 写法。

### 选择器优先级

从高到低：
```
#id  >  .class  >  tag  >  [attr=value]  >  :nth-child(2)
```

### @textNodes 提取类型

`@textNodes` 只提取元素的**直接文本节点**，不含子元素中的文本。

```
div@textNodes    → 只取 div 自身的文本，忽略子标签内的文本
div@text         → 取 div 及所有子元素的文本（递归）
```

典型场景：HTML 中文本与子标签混合时，只需外层文本。

### Default vs @CSS: 伪类选择器差异

两种模式都支持以下伪类选择器：

| 伪类 | 说明 |
|------|------|
| `:first-child` | 第一个子元素 |
| `:last-child` | 最后一个子元素 |
| `:nth-child(n)` | 第 n 个子元素 |
| `:contains(text)` | 包含指定文本的元素 |

> `@CSS:` 前缀由 `AnalyzeByJSoup` 内部剥离，Default 模式和 `@CSS:` 模式在伪类选择器上行为一致。

---

## 十、正则表达式三种用法

> 正则在 Legado 中有三种核心用法，均以 `##` 为标记。

### 格式1：删除匹配

```
规则##正则
```

`replacement` 默认为空字符串，即删除所有匹配内容。

示例：
```
div.content@html##<script[\\s\\S]*?</script>    → 删除所有 script 标签
div.content@text##广告文字                        → 删除"广告文字"
```

### 格式2：替换匹配

```
规则##正则##替换
```

全局替换：将所有匹配正则的内容替换为指定字符串。

示例：
```
div.content@text##老版本##新版本          → 将"老版本"全部替换为"新版本"
div.content@html##<br\\s*/?>##\n          → 将 br 标签替换为换行
```

### 格式3：捕获组提取

```
规则##正则(组)##$1
```

用括号捕获分组，`$1`/`$2`/... 引用对应分组。

示例：
```
div.info@text##(\\d+)万字##$1              → "123万字" → "123"
div.info@text##作者[：:](.+?)$##$1          → "作者：张三" → "张三"
```

### OnlyOne 模式（`###` 结尾）

```
规则##正则##替换###
```

三个 `#` 结尾表示**只替换第一个匹配**。

> ⚠️ **陷阱**：OnlyOne 模式下，如果正则**未匹配**，返回**空字符串**而非原始内容。这会导致内容意外丢失！

```javascript
// 陷阱示例
"hello world"##xyz##替换###    → 返回 ""（未匹配，内容丢失！）
"hello world"##hello##hi###    → 返回 "hi world"（只替换第一个）
```

**安全做法**：使用 OnlyOne 模式时，确保正则一定能匹配，或避免使用此模式。

### AllInOne 模式（`:` 开头）

```
:规则##正则##替换
```

- 只能在**列表规则**和**目录规则**中使用
- `allInOne=true` 时生效
- 先将列表所有结果拼接为一个字符串，再执行正则替换

> **源码确认**：实现在 `AnalyzeRule.splitSourceRule()` 方法中（L531-543），当 `allInOne=true` 且规则以 `:` 开头时，将模式设为 `Mode.Regex` 并剥离 `:` 前缀。源码注释："仅首字符为:时为AllInOne，其实:与伪类选择器冲突，建议改成?更合理"。

---

## 十一、变量系统完整说明

> Legado 规则引擎提供变量存取机制，用于跨规则、跨步骤传递数据。

### 非JS规则中的变量操作

| 语法 | 说明 | 示例 |
|------|------|------|
| `@put:{key:value}` | 存储变量 | `@put:{myKey:div.title@text}` |
| `@get:{key}` | 获取变量 | `@get:{myKey}` |

### JS规则中的变量操作

| 语法 | 说明 | 示例 |
|------|------|------|
| `java.put('key', value)` | 存储变量 | `java.put('myKey', result)` |
| `java.get('key')` | 获取变量 | `var x = java.get('myKey')` |

### 跨语法调用

| 语法 | 说明 | 示例 |
|------|------|------|
| `{{java.get("key")}}` | 在非JS位置调用java.get | `url + "?token=" + {{java.get("token")}}` |

> ⚠️ **关键陷阱**：JS 规则中**无法使用 `@get:{key}`**，必须用 `java.get('key')`。`@get` 只在非 JS 规则中有效。

### `@@` — 强制 Default 模式前缀

```
@@规则
```

`@@` 是**模式前缀**，强制将规则模式设为 `Mode.Default`（CSS/JSoup 模式），并剥离 `@@` 前缀。当规则内容可能被误判为 JSONPath（以 `$.` 开头）或 XPath（以 `/` 开头）时，用 `@@` 前缀强制按 CSS 选择器解析。

> ⚠️ **注意**：`@@` 不是"跨栏目取值"语法。源码依据：AnalyzeRule.kt L608-611，`@@` 仅设置 `mode = Mode.Default` 并 `substring(2)` 剥离前缀。

### `@put` 中规则类型差异

| 规则类型 | 是否需要引号 | 示例 |
|----------|-------------|------|
| JSONPath | **不需要** | `@put:{key:$.data.token}` |
| CSS/XPath/其他 | **需要** | `@put:{key:div.token@text}` |

JSONPath 在 `@put` 中可直接使用，其他规则类型需按各自语法书写。

---

## 十二、nextContentUrl 判断规则

> 正文分页时，`nextContentUrl` 的设置直接影响翻页行为。不同场景需要不同策略。

### 场景1：真下一章

```json
{
  "content": "div.content@html",
  "nextContentUrl": "a.next-chapter@href"
}
```

- 设置 `nextContentUrl` 指向下一页链接
- Legado 自动跟随该 URL 获取下一页内容并拼接
- 当 `nextContentUrl` 为空时停止翻页

### 场景2：同章分页

```json
{
  "content": "div.content@html"
}
```

- **留空 `nextContentUrl`**，不设置任何值
- Legado 自动处理同章节内的分页（通过 `nextPageUrl` 等机制）
- 适用于正文自然分页、无需手动指定下一页 URL 的情况

### 场景3：模糊按钮（URL对比法）

当"下一页"按钮可能指向下一章而非当前章的下一页时，需要判断章节号是否变化：

```javascript
<js>
var nextUrl = "a.next@href";  // 获取下一页URL
var currentChapter = baseUrl.match(/chapter(\d+)/);
var nextChapter = nextUrl.match(/chapter(\d+)/);
if (currentChapter && nextChapter && currentChapter[1] === nextChapter[1]) {
    result = nextUrl;  // 同章分页，继续
} else {
    result = "";  // 不同章节，停止
}
</js>
```

核心思路：对比当前 URL 和下一页 URL 中的章节号，章节号相同才继续翻页。

### select 下拉菜单分页

部分网站使用 `<select>` 下拉菜单实现分页：

```
select[name='pages'] option:not([selected])@value
```

- `select[name='pages']` 定位分页下拉菜单
- `option:not([selected])` 选择非当前页的选项
- `@value` 获取选项的 value 属性作为 URL

典型 HTML 结构：
```html
<select name="pages">
  <option value="/page/1" selected>第1页</option>
  <option value="/page/2">第2页</option>
  <option value="/page/3">第3页</option>
</select>
```