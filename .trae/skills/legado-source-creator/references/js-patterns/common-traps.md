# 常见陷阱

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析。
> 更详细的 JS/Rhino 陷阱见 [troubleshooting/rhino-js-traps.md](../troubleshooting/rhino-js-traps.md)。

## 1. Rhino引擎ES5限制

Legado 使用 Rhino 1.8.1，仅支持 ES5 语法。

**禁止使用的 ES6+ 语法**：

| ES6+ 语法 | ES5 替代写法 |
|-----------|-------------|
| `let x = 1` | `var x = 1` |
| `const x = 1` | `var x = 1` |
| `() => x` | `function() { return x; }` |
| `` `Hello ${name}` `` | `"Hello " + name` |
| `x ?? y` | `x != null ? x : y` |
| `for...of` | `for (var i = 0; i < arr.length; i++)` |

**常见报错**：`SyntaxError: missing ; before statement`（let/const）、`SyntaxError: invalid property id`（模板字符串）

## 2. result变量必须返回

JS 规则的最后一个表达式会作为 `result` 返回。如果末尾是赋值语句而非表达式，`result` 为 `undefined`。

```javascript
// ❌ 错误：result 为 undefined
var title = java.getString("$.title");
java.log(title);

// ✅ 正确：末尾有表达式
var title = java.getString("$.title");
java.log(title);
title;  // 或 result = title;
```

**loginCheckJs 陷阱**：如果 `loginCheckJs` 末尾没有返回 `result`，会触发 NPE 崩溃。必须末尾加 `;result`。

## 3. @js: vs \<js\>

| 语法 | 返回值 | 适用场景 |
|------|--------|---------|
| `@js:` | 只返回 JS 表达式的值 | 简单表达式、URL 处理 |
| `<js>...</js>` | 允许 JS 和 HTML 规则混合 | 复杂逻辑、需要多行代码 |

```javascript
// @js: 简单表达式
@js:baseUrl.replace("/book/", "/read/")

// <js> 多行代码
<js>
var url = result.match(/href="([^"]+)"/);
url ? url[1] : "";
</js>
```

## 4. java.put/get是进程内缓存

`java.put(key, val)` / `java.get(key)` 使用 `ConcurrentHashMap`，App 重启后数据丢失。

```javascript
// ❌ 不可靠：跨 App 重启无法持久化
java.put("token", token);

// ✅ 正确：在同一会话内传递变量
// searchUrl 中获取 token
java.put("token", result.match(/token=(\w+)/)[1]);
// ruleContent 中使用 token
var token = java.get("token");
```

## 5. webViewGetSource是异步的

`java.webView()` 需要等待页面加载完成，不能同步获取结果。

```javascript
// ❌ 错误：同步调用
var html = java.webView(url);

// ✅ 正确：在 webView 回调中处理
// Legado 内部会等待页面加载完成后执行 JS
java.webView(url, null, "document.querySelector('.content').innerHTML");
```

> **注意**：webView 规则无法在 OkHttp 中验证，需用真机或 Playwright MCP 验证。

## 6. JSON.stringify构造POST请求

使用 `java.ajax()` 发送 POST 请求时，必须包含 `method` 字段。

```javascript
// ❌ 错误：缺少 method 字段，会被当作 GET 请求
java.ajax(url + ",{" + JSON.stringify({body: data}) + "}");

// ✅ 正确：包含 method 字段
java.ajax(url + ",{\"method\":\"POST\",\"body\":\"" + encodeURIComponent(data) + "\"}");
```

## 7. 正则中的反斜杠

JS 字符串中反斜杠需要双重转义。

| 目标正则 | JS 字符串写法 | 说明 |
|---------|-------------|------|
| `\d+` | `"\\d+"` | 匹配数字 |
| `\s+` | `"\\s+"` | 匹配空白 |
| `\[` | `"\\["` | 匹配方括号 |
| `\n` | `"\\n"` | 匹配换行 |

```javascript
// ❌ 错误：\d 在 JS 字符串中被解释为转义
result.match(/\d+/);  // 这在 JS 正则字面量中可以
result.match("\\d+"); // ❌ 这匹配字面 "d+"

// ✅ 正确：双重转义
result.match(new RegExp("\\d+"));
// 或使用正则字面量
result.match(/\d+/);
```
