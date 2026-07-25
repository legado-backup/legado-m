# 搜索高级技巧

> 搜索规则（SearchRule）的高级写法，涵盖 Cookie 清理、重定向处理、编码转换、动态地址获取、分页和多列表等场景。
> 所有内容已通过 Legado 源码确认。

---

## 1. Cookie 清理解决搜索 30 秒超时

某些书源在搜索时会因旧 Cookie 导致服务端返回异常响应，触发 Legado 的 30 秒超时（SearchModel.kt L76-114）。解决方法是在搜索前清理该源的 Cookie。

### 方法一：在 loginCheckJs 中清理

```javascript
// loginCheckJs 字段
cookie.removeCookie(source.getKey());
```

`source.getKey()` 返回书源的 `bookSourceUrl`（即 BookSource.kt L34-35 定义的主键），作为 Cookie 存储的域名标识。

### 方法二：在搜索地址栏中清理

```
{{cookie.removeCookie(source.getKey())}}/search.html?searchkey={{key}}
```

模板引擎先执行 `cookie.removeCookie()`，清除旧 Cookie 后再发起搜索请求。`cookie` 变量是 JsExtensions 提供的 CookieManager 实例。

**适用场景**：搜索偶尔超时、搜索结果为空但手动浏览器可正常搜索。

---

## 2. 搜索重定向处理

部分网站搜索时会 302 重定向到结果页，直接 GET 可能拿不到正确内容。

### 用 java.post() 获取重定向地址

```javascript
// 获取 302 重定向的 Location 头
java.post('https://example.com/search', 'keyword=' + key + '&submit=', {}).header("Location")
```

### 模板写法

```
{{java.post('https://example.com/search','keyword='+key+'&submit=',{}).header("Location")}}
```

**原理**：`java.post()` 返回 Jsoup 的 `Connection.Response` 对象（不是 `StrResponse`），其 `.header("Location")` 方法可读取响应头中的重定向目标。Jsoup 的 `post()` 方法默认 `followRedirects=false`，因此可以直接拦截重定向获取 Location 头。

> **源码确认**：JsExtensions.kt L535，`fun post(urlStr: String, body: String, headers: Map<String, String>): Connection.Response`，返回类型是 Jsoup 的 `Connection.Response`，不是 `StrResponse`。

**适用场景**：搜索 URL 返回 302、搜索结果页 URL 与搜索 URL 不同。

---

## 3. 繁体字搜索编码处理

部分繁体网站（如台湾小说站）搜索关键词需转为繁体，且页面编码为 Big5。

### 简体转繁体

```javascript
key = java.s2t(key);
```

> **源码确认**：JsExtensions.kt L685，`s2t()` 方法调用 ChineseUtils.s2t() 实现简体转繁体。

### 指定 Big5 编码

```json
{
  "searchUrl": "/search.php?searchkey={{key}},{\"charset\":\"big5\"}"
}
```

> **注意**：`charset` 参数必须在 JSON 对象中，不能作为 URL 查询参数。详见 [encoding-guide.md](./encoding-guide.md)。

**完整示例**：

```
/search.php?searchkey={{java.s2t(key)}},{"charset":"big5"}
```

---

## 4. 搜索地址变动动态获取

部分网站的搜索表单 action 地址是动态生成的，不能硬编码。

### 用正则从首页提取

```
{{java.ajax(source.getKey()).match(/action="(.*?)"/)[1]}}?searchkey={{key}}
```

**流程**：
1. `java.ajax(source.getKey())` 获取书源首页 HTML
2. `.match(/action="(.*?)"/)[1]` 提取 form 标签的 action 属性值
3. 拼接搜索关键词参数

### 用 Jsoup 解析 form 标签

```javascript
var html = java.ajax(source.getKey());
var doc = org.jsoup.Jsoup.parse(html);
var action = doc.select("form").first().attr("action");
result = action + "?searchkey=" + key;
```

**适用场景**：搜索地址含动态 token、搜索表单 action 频繁变化。

---

## 5. 分页 URL 不同写法

搜索结果分页时，不同网站的 URL 规则各异。

### 三元表达式

```
https://example.com/search/{{page==1?"":page+".html"}}?key={{key}}
```

- 第一页：`https://example.com/search/?key=关键词`
- 第二页：`https://example.com/search/2.html?key=关键词`

### Legado 内置分页语法

```
https://example.com/search/<,/{{page}}.html>?key={{key}}
```

- `<,/{{page}}.html>` 是 Legado 的内置分页语法
- 逗号前为第一页（空），逗号后为后续页模板
- `{{page}}` 从 1 开始递增

### 第一页无页数

```
https://example.com/gudai/{{page==1?'':'index_'+page+'.html'}}
```

- 第一页：`https://example.com/gudai/`
- 第二页：`https://example.com/gudai/index_2.html`

---

## 6. 多个搜索列表处理

部分网站搜索结果页包含多个不同结构的列表区域（如热门推荐 + 搜索结果），需要精准提取。

### 用共通 class 名取交集

```
div.hot_sale
```

如果多个列表区域都使用 `hot_sale` 这个 class，CSS 选择器会自动合并所有匹配结果。

### 用 XPath 排除干扰区域

```
//div[@id="searchmain"]//div[not(@class="searchResult")]
```

- `not(@class="searchResult")` 排除 class 为 searchResult 的干扰 div
- XPath 的 `not()` 谓词比 CSS 的 `:not()` 更灵活，支持属性值匹配

### 用 JS 过滤合并

```javascript
var list1 = JSON.parse(java.ajax(url1));
var list2 = JSON.parse(java.ajax(url2));
result = list1.concat(list2);
```

**适用场景**：搜索结果分散在多个 div 区域、页面包含推荐内容干扰搜索结果。
