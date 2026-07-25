# JS 扩展函数参考 — 网络请求

> 拆分自 js-extensions.md §一。Legado 书源 JS 环境中可调用的 HTTP 网络请求扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.ajax(url)`。

---

## 一、网络请求

### ajax(url) / ajax(url, callTimeout) — HTTP 请求，返回响应体字符串

```javascript
// 基本用法：url 支持 AnalyzeUrl 格式（可带 POST 参数、headers 等）
var body = java.ajax("https://example.com/api");
// 带超时（毫秒）
var body = java.ajax("https://example.com/api", 15000);
// url 为 List 时取第一个元素
var body = java.ajax(["https://example.com/api"]);
// 返回: String?（响应体文本，失败时返回 null）
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | Any (String/List) | 是 | 请求地址，支持 AnalyzeUrl 格式 |
| callTimeout | Long? | 否 | 超时时间（毫秒），默认 null |

**使用频率**：极高

---

### ajaxAll(urlList) / ajaxAll(urlList, skipRateLimit) — 并发请求多个 URL

```javascript
var responses = java.ajaxAll([
    "https://example.com/page1",
    "https://example.com/page2"
]);
// 返回: Array<StrResponse>，每个元素含 url 和 body 属性
for (var i = 0; i < responses.length; i++) {
    var body = responses[i].body;
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlList | Array\<String\> | 是 | URL 数组 |
| skipRateLimit | Boolean | 否 | 是否跳过速率限制，默认 false |

**使用频率**：中

---

### ajaxTestAll(urlList, timeout) / ajaxTestAll(urlList, timeout, skipRateLimit) — 并发测试请求

```javascript
var responses = java.ajaxTestAll(["url1", "url2"], 5000);
// 返回: Array<StrResponse>，用于测试连通性
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlList | Array\<String\> | 是 | URL 数组 |
| timeout | Int | 是 | 超时时间（毫秒） |
| skipRateLimit | Boolean | 否 | 是否跳过速率限制，默认 false |

**使用频率**：低

---

### connect(urlStr) / connect(urlStr, header) / connect(urlStr, header, callTimeout) — 获取完整响应对象

```javascript
var response = java.connect("https://example.com/api");
var response = java.connect("https://example.com/api", '{"Cookie":"sid=abc"}');
var response = java.connect("https://example.com/api", '{"Cookie":"sid=abc"}', 15000);
// 返回: StrResponse { url: String, body: String }
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlStr | String | 是 | 请求地址，支持 AnalyzeUrl 格式 |
| header | String | 否 | JSON 格式请求头，如 `'{"Cookie":"sid=abc"}'` |
| callTimeout | Long | 否 | 超时时间（毫秒） |

**使用频率**：高

---

### get(urlStr, headers) / get(urlStr, headers, timeout) — GET 请求（Jsoup，支持重定向拦截）

```javascript
var response = java.get("https://example.com/page", {"User-Agent": "Mozilla/5.0"});
var response = java.get("https://example.com/page", {"User-Agent": "Mozilla/5.0"}, 15000);
// 返回: Connection.Response，可调用 .body() / .headers() / .statusCode() 等
var body = response.body();
var location = response.header("Location"); // 获取重定向地址
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlStr | String | 是 | 请求地址 |
| headers | Map\<String, String\> | 是 | 请求头（必填，可传空 map `{}`） |
| timeout | Int | 否 | 超时时间（毫秒），默认 30000 |

**注意**：此方法使用 Jsoup 发送请求，`followRedirects=false`，适合拦截重定向。源启用了 CookieJar 时会自动附加 Cookie。

**使用频率**：高

---

### head(urlStr, headers) / head(urlStr, headers, timeout) — HEAD 请求（不返回 Body，更省流量）

```javascript
var response = java.head("https://example.com/file.zip", {});
var contentLength = response.header("Content-Length");
var location = response.header("Location");
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlStr | String | 是 | 请求地址 |
| headers | Map\<String, String\> | 是 | 请求头 |
| timeout | Int | 否 | 超时时间（毫秒），默认 30000 |

**使用频率**：低

---

### post(urlStr, body, headers) / post(urlStr, body, headers, timeout) — POST 请求（Jsoup）

```javascript
var response = java.post(
    "https://example.com/api",
    "key=value",
    {"Content-Type": "application/x-www-form-urlencoded"}
);
var body = response.body();
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| urlStr | String | 是 | 请求地址 |
| body | String | 是 | 请求体 |
| headers | Map\<String, String\> | 是 | 请求头（必填，可传空 map `{}`） |
| timeout | Int? | 否 | 超时时间（毫秒），默认 30000 |

**使用频率**：高
