# JS 扩展函数参考 — 高级扩展

> 拆分自 js-extensions.md §十~十四。包含替换净化 JS 扩展、WebJs 扩展、全局上下文变量、重要约束、不存在的函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。

---

## 十、替换净化规则中的 JS 扩展（RegexJsExtensions）

> 在替换净化规则的 JS 中，`java` 对象是 `RegexJsExtensions` 实例，功能有限。

| 函数 | 签名 | 说明 |
|------|------|------|
| put | `put(key: String, value: String): String` | 保存变量到 RuleData |
| get | `get(key: String): String` | 读取变量，不存在返回空字符串 |
| log | `log(msg: Any?): Any?` | 输出调试日志 |
| logType | `logType(any: Any?)` | 输出对象类型 |
| t2s | `t2s(text: String): String` | 繁体转简体 |
| s2t | `s2t(text: String): String` | 简体转繁体 |

**注意**：RegexJsExtensions 实现的是 `JsEncodeUtils` 接口，因此也可使用 `md5Encode`、`md5Encode16`、`base64Encode`、`base64Decode`、`hexEncodeToString`、`hexDecodeToString`、`digestHex`、`HMacHex` 等加密编码方法。

---

## 十一、WebJs 扩展（WebJsExtensions，WebView 注入环境）

> 在 WebView 注入的 JS 环境中，`java` 对象是 `WebJsExtensions` 实例。
> 除继承 RssJsExtensions 的方法外，还提供以下异步方法（返回 Promise）。

| 异步函数 | 说明 |
|----------|------|
| `run(jsCode)` | 在 Rhino 环境执行 JS |
| `ajaxAwait(url, callTimeout?)` | 异步 HTTP 请求 |
| `connectAwait(urlStr, header?, callTimeout?)` | 异步获取完整响应 |
| `getAwait(urlStr, header, timeout?)` | 异步 GET |
| `headAwait(urlStr, header, timeout?)` | 异步 HEAD |
| `postAwait(urlStr, body, header, timeout?)` | 异步 POST |
| `webViewAwait(html?, url?, js?, cacheFirst?)` | 异步 WebView |
| `webViewGetSourceAwait(html?, url?, js?, sourceRegex, cacheFirst?, delayTime?)` | 异步获取资源 URL |
| `decryptStrAwait(transformation, key, iv?, data)` | 异步解密 |
| `encryptBase64Await(transformation, key, iv?, data)` | 异步加密（Base64） |
| `encryptHexAwait(transformation, key, iv?, data)` | 异步加密（Hex） |
| `createSignHexAwait(algorithm, publicKey, privateKey, data)` | 异步签名 |
| `downloadFileAwait(url)` | 异步下载文件 |
| `readTxtFileAwait(path)` | 异步读取文件 |
| `importScriptAwait(path)` | 异步导入脚本 |
| `getStringAwait(ruleStr, mContent?)` | 异步规则解析 |

**使用频率**：中（仅 WebView 注入环境）

---

## 十二、全局上下文变量

> 在 `evalJS` 执行的 JS 脚本中，以下变量自动注入到作用域。

| 变量 | 类型 | 说明 |
|------|------|------|
| `java` | JsExtensions | Java 互操作入口，调用所有扩展函数 |
| `result` | Any? | 上一个规则的结果 |
| `baseUrl` | String? | 当前页面 URL |
| `book` | Book? | 当前书籍对象 |
| `source` | BaseSource? | 当前书源对象 |
| `cookie` | CookieStore | Cookie 操作对象 |
| `cache` | CacheManager | 缓存操作对象 |
| `chapter` | BookChapter? | 当前章节对象 |
| `title` | String? | 当前章节标题 |
| `src` | Any? | 当前内容（与 setContent 的 content 相同） |
| `nextChapterUrl` | String? | 下一章 URL |
| `rssArticle` | RssArticle? | RSS 文章对象（RSS 上下文） |
| `fromBookInfo` | Boolean | 是否来自书籍详情页 |

---

## 十三、重要约束

1. **禁止 ES6+ 语法**：无箭头函数(`=>`)、无模板字符串、无 `let/const`、无 `Promise`、无解构赋值
2. **必须显式返回结果**：JS 规则最后一条语句的值作为返回值（或用 `return`）
3. **禁止阻塞主线程**：webView 等方法必须在后台线程调用
4. **JS 嵌套递归限制**：evalJS 调用深度受 `evalJSCallCount > 16` 限制
5. **文件路径安全**：所有文件操作限制在应用缓存目录内，禁止路径穿越
6. **CookieJar 联动**：源启用 `enabledCookieJar` 时，get/post/head 方法自动附加 Cookie 头
7. **速率限制**：get/post/head 方法受 `ConcurrentRateLimiter` 限制，防止高频请求

---

## 十四、不存在的函数（已删除/从未存在）

以下函数在当前源码中**不存在**，请勿使用：

| 函数 | 说明 |
|------|------|
| `java.aesEncrypt` | 不存在，请使用 `createSymmetricCrypto().encryptBase64()` |
| `java.aesDecrypt` | 不存在，请使用 `createSymmetricCrypto().decryptStr()` |
| `compressImage` | 不存在 |
| `decodeImage` | 不存在 |
| `getImageSize` | 不存在 |
| `python` | 不存在，Legado 不支持 Python 执行 |
| `java.setCookie` | 不存在，Cookie 通过 `CookieStore` 自动管理 |
| `java.putCache` | 不存在，请使用 `cache.put()` |
| `java.getCache` | 不存在，请使用 `cache.get()` |
| `java.hexEncode` | 不存在，请使用 `java.hexEncodeToString()` |
| `java.formatDate` | 不存在，请使用 `java.timeFormat()` 或 `java.timeFormatUTC()` |
