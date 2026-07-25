# JS 扩展函数参考 — 规则解析（AnalyzeRule 方法）

> 拆分自 js-extensions.md §三。Legado 书源 JS 环境中可调用的 AnalyzeRule 规则解析扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 对象调用（AnalyzeRule 实现了 JsExtensions 接口）。

---

## 三、规则解析（AnalyzeRule 方法）

> 这些方法来自 AnalyzeRule 类，在 JS 中通过 `java` 对象调用（AnalyzeRule 实现了 JsExtensions 接口）。
> 在 RssJsExtensions 和 WebJsExtensions 环境中也可直接使用。

### setContent(content) / setContent(content, baseUrl) — 设置待解析的内容

```javascript
var rule = java.setContent(html, "https://example.com");
// 返回: AnalyzeRule 对象（可链式调用）
var result = java.setContent(html).getString("//div[@class='title']");
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | Any | 是 | 待解析内容（HTML/JSON/String），不可为 null |
| baseUrl | String | 否 | 基准 URL，用于相对路径解析 |

**使用频率**：高

---

### getString(ruleStr) / getString(ruleStr, mContent) / getString(ruleStr, mContent, isUrl) / getString(ruleStr, unescape) — 用规则获取文本

```javascript
var title = java.getString("//h1/text()");
var title = java.getString("$.data.title", jsonData);
var url = java.getString("div.content a@href", null, true); // isUrl=true 自动补全
var text = java.getString("div.content", false); // unescape=false 不反转义 HTML 实体
// 返回: String
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ruleStr | String | 是 | 解析规则（CSS/XPath/JSONPath/JS/正则） |
| mContent | Any | 否 | 待解析内容，默认使用 setContent 设置的内容 |
| isUrl | Boolean | 否 | 是否作为 URL 处理（自动补全相对路径），默认 false |
| unescape | Boolean | 否 | 是否反转义 HTML 实体，默认 true |

**使用频率**：极高

---

### getStringList(ruleStr) / getStringList(ruleStr, mContent) / getStringList(ruleStr, mContent, isUrl) — 用规则获取文本列表

```javascript
var chapters = java.getStringList("//div[@class='list']/a/@href");
var chapters = java.getStringList("$.chapters[*].url", jsonData);
// 返回: List<String>?
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ruleStr | String | 是 | 解析规则 |
| mContent | Any | 否 | 待解析内容 |
| isUrl | Boolean | 否 | 是否作为 URL 处理，默认 false |

**使用频率**：高

---

### getElement(ruleStr) — 用规则获取单个元素

```javascript
var element = java.getElement("div.content");
// 返回: Any?（元素对象）
```

**使用频率**：低

---

### getElements(ruleStr) — 用规则获取元素列表

```javascript
var elements = java.getElements("div.chapter-list a");
// 返回: List<Any>
for (var i = 0; i < elements.length; i++) {
    var el = elements[i];
}
```

**使用频率**：高

---

### setBaseUrl(baseUrl) — 设置基准 URL

```javascript
java.setBaseUrl("https://example.com");
// 返回: AnalyzeRule 对象
```

**使用频率**：低

---

### setRedirectUrl(url) — 设置重定向 URL

```javascript
java.setRedirectUrl("https://example.com/redirect");
// 返回: URL?
```

**使用频率**：低
