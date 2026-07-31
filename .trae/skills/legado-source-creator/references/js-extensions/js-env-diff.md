# JS 执行环境差异集中化文档

> Legado 中存在多个 JS 执行入口，分属 **Rhino 1.8.1** 与 **WebView(V8)** 两类引擎，可用 API、绑定变量、返回值约束各不相同。创建/优化书源时必须区分环境，避免跨环境误用 API。
>
> 相关文档：
> - Rhino 语法兼容性见 `./rhino-compat-cheatsheet.md`
> - 陷阱详解见 `../troubleshooting/rhino-js-traps.md`
> - WebView 操作函数见 `./webview.md`

---

## 1. JS 执行环境清单

| # | 执行环境 | 引擎 | 入口字段 / 调用点 | 执行方式 | 典型用途 |
|---|---------|------|------------------|---------|---------|
| 1 | shouldOverrideUrlLoading | Rhino | `RssSource.shouldOverrideUrlLoading` / `BookSource.shouldOverrideUrlLoading` | `AnalyzeRule.evalJS` | WebView 加载 URL 前拦截，判断是否需登录/重定向 |
| 2 | injectJs | WebView(V8) | `RssSource.injectJs` / `BookSource.injectJs` | `WebView.evaluateJavascript` | 页面加载后注入 JS 修改 DOM/取数据 |
| 3 | loginCheckJs | Rhino | `RssSource.loginCheckJs` / `BookSource.loginCheckJs` / `HttpTTS.loginCheckJs` | `AnalyzeUrl.evalJS` | 登录态校验，决定是否需重新登录 |
| 4 | ruleArticles JS | Rhino | `RssSource.ruleArticles` 中的 `<js>` | `AnalyzeRule.evalJS` | RSS 源文章列表解析 |
| 5 | evalJS（规则引擎通用） | Rhino | `AnalyzeRule.evalJS(jsStr, result)` | `RhinoScriptEngine` | 所有规则字段中的 JS 表达式/脚本 |
| 6 | sortUrl / searchUrl `<js>` 标签 | Rhino | `source.sortUrl` / `source.searchUrl` 中的 `<js>...</js>` | `AnalyzeUrl.evalJS` | 动态生成分类 URL / 搜索 URL |
| 7 | ruleContent JS | Rhino | `RssSource.ruleContent` 中的 `<js>` | `AnalyzeRule.evalJS` | RSS 内容解析（视频URL/HTML） |
| 8 | startJs / preloadJs | WebView(V8) | `RssSource.startJs` / `RssSource.preloadJs` | `WebView.evaluateJavascript` | 首页加载前后注入 JS |

> **铁律**：所有 `AnalyzeRule.evalJS` / `AnalyzeUrl.evalJS` 走 Rhino 1.8.1；所有 `WebView.evaluateJavascript` 走 V8。两类引擎语法支持差异巨大，详见 §2。

---

## 2. Rhino vs WebView API 可用性对比表

| API / 变量 | Rhino 环境 | WebView 环境 | 说明 |
|-----------|-----------|-------------|------|
| `document` | ❌ | ✅ | DOM 操作（getElementById/querySelector 等） |
| `window` | ❌ | ✅ | 全局对象（window.location/window.open 等） |
| `localStorage` | ❌ | ✅ | 本地存储 |
| `sessionStorage` | ❌ | ✅ | 会话存储 |
| `XMLHttpRequest` / `fetch` | ❌ | ✅ | 浏览器原生网络请求 |
| `cookie`（变量） | ✅ `java.getCookie(tag)` | ✅ `document.cookie` | Cookie 访问，方式不同 |
| `cache`（变量） | ✅ | ❌ | CacheManager（仅 Rhino 绑定） |
| `java`（变量） | ✅ | ✅ | JsExtensions 对象（WebView 通过 `@JavascriptInterface` 注入） |
| `result`（变量） | ✅ | ❌ | 规则引擎上一阶段解析结果 |
| `source`（变量） | ✅ | ✅ | 源对象（WebView 通过注入提供） |
| `baseUrl`（变量） | ✅ | ❌ | 当前解析的基础 URL |
| `book`（变量） | ✅ | ❌ | 书籍对象（仅书源规则） |
| `chapter`（变量） | ✅ | ❌ | 章节对象 |
| `src`（变量） | ✅ | ❌ | 当前内容（章节正文/源码） |
| `JSON.parse` / `JSON.stringify` | ✅ | ✅ | 两环境均可用 |
| `Math` 对象 | ✅ | ✅ | 两环境均可用 |
| `Date` 对象 | ✅ | ✅ | 两环境均可用 |
| ES6 `let/const/箭头函数/模板字符串` | ❌ | ✅ | Rhino 1.8.1 不支持，V8 完整支持 |
| `Promise` / `async/await` | ❌ | ✅ | Rhino 无事件循环，V8 完整支持 |
| `String.includes/padStart/startsWith` | ❌ | ✅ | Rhino 不支持，需用 `indexOf` 替代 |
| `for...of` / `Map` / `Set` | ❌ | ✅ | Rhino 不支持 |
| 解构赋值 / 扩展运算符 | ❌ | ✅ | Rhino 不支持 |
| DOM 选择器 (`querySelector` 等) | ❌ | ✅ | 仅 WebView 有 DOM |

> **关键差异**：Rhino 环境**无 DOM/BOM**，所有 `document.xxx`、`window.xxx` 调用会报 ReferenceError。需在 WebView 环境中执行 DOM 操作，或用 `java.ajax()` 获取 HTML 后用规则解析。

---

## 3. 各执行环境绑定变量清单

> 以下绑定变量基于 `AnalyzeRule.evalJS` 源码（`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 第 836-851 行）实际确认。

### 3.1 evalJS 完整绑定变量（源码确认）

`AnalyzeRule.evalJS(jsStr, result)` 绑定以下全部变量：

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `java` | JsExtensions | JS 扩展函数集（ajax/connect/getCookie/...） |
| `cookie` | CookieStore | Cookie 读写（`cookie.getCookie(tag)`） |
| `cache` | CacheManager | 缓存读写（`cache.get(key)`/`cache.put(key,val)`） |
| `source` | BaseSource | 当前源对象 |
| `book` | Book | 书籍对象（仅书源场景，RSS 源为 null） |
| `result` | Any? | 上一阶段解析结果（由调用方传入） |
| `baseUrl` | String | 当前解析基础 URL |
| `chapter` | BookChapter? | 章节对象（仅章节解析场景） |
| `title` | String? | 章节标题（`chapter?.title`） |
| `src` | String | 当前内容（章节正文/源码/URL） |
| `nextChapterUrl` | String? | 下一章 URL |
| `rssArticle` | RssArticle? | RSS 文章对象（仅 RSS 源场景） |
| `fromBookInfo` | Boolean | 是否来自书籍信息解析 |

### 3.2 各场景实际可用变量（按调用上下文）

| 执行环境 | 引擎 | 绑定变量 | 备注 |
|---------|------|---------|------|
| shouldOverrideUrlLoading | Rhino | `java` + `url`（拦截的 URL） | WebView 加载前拦截，绑定变量较少 |
| injectJs | WebView(V8) | `java`（@JavascriptInterface 注入）+ 浏览器原生 API | 页面加载后注入，可用 DOM |
| loginCheckJs | Rhino | `java`/`cookie`/`baseUrl`/`source` + `result`(Response) | 必须返回 StrResponse |
| ruleArticles JS | Rhino | `java`/`result`/`baseUrl`/`source` | 必须返回 NativeArray（JS 数组） |
| ruleContent JS | Rhino | `java`/`result`/`baseUrl`/`source` + `rssArticle` | 必须返回字符串 |
| evalJS（通用） | Rhino | 见 §3.1 完整清单 | 绑定变量取决于调用方传入的 result |
| sortUrl `<js>` | Rhino | `java`/`cache`/`key`（搜索关键词） | 返回分类 URL 字符串 |
| searchUrl `<js>` | Rhino | `java`/`cache`/`key`（搜索关键词） | 返回搜索 URL 字符串 |
| startJs / preloadJs | WebView(V8) | `java` + 浏览器原生 API | 首页加载前后注入 |

> **注意**：§3.2 中的"绑定变量"列指该场景**主要使用**的变量。由于 loginCheckJs/ruleArticles/sortUrl 等底层均调用 `evalJS`，理论上 §3.1 的所有变量均可访问，但部分变量在该场景下为 null（如 loginCheckJs 场景下 `book` 通常为 null）。**建议仅使用该场景列出的变量**，避免依赖可能为 null 的变量。

---

## 4. 返回值类型约束

> ⚠️ 不同执行环境对 JS 返回值类型有严格约束，返回类型错误会导致解析失败。

| 执行环境 | 必须返回类型 | 错误返回的后果 | 示例 |
|---------|------------|--------------|------|
| loginCheckJs | `StrResponse`（字符串/Response） | 登录态判断失效，强转 `as Response` 抛 ClassCastException | `return result;`（result 是 Response） |
| ruleArticles JS | `NativeArray`（JS 数组） | 文章列表解析失败，`as List<*>` 抛异常 | `var arr = []; arr.push({...}); return arr;` |
| ruleContent JS | `String`（字符串） | 内容解析失败，视频URL/HTML 无法识别 | `return videoUrl;` |
| sortUrl `<js>` | `String`（URL 字符串） | 分类 URL 生成失败 | `return "https://example.com/list/1";` |
| searchUrl `<js>` | `String`（URL 字符串） | 搜索 URL 生成失败 | `return "https://example.com/search?q=" + key;` |
| shouldOverrideUrlLoading | `Boolean` / 字符串 | 拦截逻辑失效 | `return true;` 或 `return url;` |
| evalJS（通用） | `Any?`（无强制约束） | 取决于调用方如何使用返回值 | 视上下文而定 |

### 4.1 返回值类型陷阱

#### 陷阱1：ruleArticles 返回非数组

```javascript
// ❌ 错误：返回对象，不是数组
return { title: "xxx", url: "yyy" };

// ✅ 正确：返回数组，每个元素是文章对象
var arr = [];
arr.push({ title: "xxx", url: "yyy" });
return arr;
```

#### 陷阱2：loginCheckJs 返回非 StrResponse

```javascript
// ❌ 错误：返回布尔值，loginCheckJs 需要 Response 对象
return true;

// ✅ 正确：返回 result（即传入的 Response 对象），或修改后的 Response
return result;
```

#### 陷阱3：返回值是 Java 对象，未转换为 JS 原生类型

```javascript
// ❌ 错误：java.ajax() 返回 Java String，直接 return 可能类型识别异常
return java.ajax(url);

// ✅ 正确：转换为 JS 原生字符串
return String(java.ajax(url));
```

> 类型转换细节详见 `./rhino-compat-cheatsheet.md` §4 类型转换陷阱。

---

## 5. 环境选择决策指引

| 需求 | 推荐环境 | 原因 |
|------|---------|------|
| 需要 DOM 操作（querySelector 等） | WebView(V8) | Rhino 无 DOM |
| 需要发起 HTTP 请求获取数据 | Rhino（`java.ajax`） | WebView 难以同步获取 |
| 需要 Cookie 读取 | 两者均可 | Rhino 用 `cookie.getCookie`，WebView 用 `document.cookie` |
| 需要使用 ES6+ 语法 | WebView(V8) | Rhino 1.8.1 不支持 ES6+ |
| 需要访问 `result`/`book`/`chapter` 等规则变量 | Rhino | WebView 不绑定这些变量 |
| 需要修改页面 DOM（注入元素/样式） | WebView(V8)（injectJs） | Rhino 无法操作页面 |
| 需要拦截 URL 加载 | Rhino（shouldOverrideUrlLoading） | 在 WebView 加载前判断 |
| 需要缓存读写 | Rhino（`cache`） | WebView 无 CacheManager |

> **核心原则**：能用 Rhino 解决的优先用 Rhino（性能好、可同步）；必须操作 DOM 的才用 WebView。

---

## 6. 源码引用

| 内容 | 源码位置 |
|------|---------|
| evalJS 绑定变量 | `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` 第 836-851 行 |
| loginCheckJs 执行 | `app/src/main/java/io/legado/app/service/HttpReadAloudService.kt` 第 343 行（`analyzeUrl.evalJS(checkJs, it) as Response`） |
| WebView 注入 JS | `app/src/main/java/io/legado/app/help/image/ImageSnifferWebView.kt` 第 155 行（`evaluateJavascript`） |
| JsExtensions @JavascriptInterface 方法 | `app/src/main/java/io/legado/app/help/JsExtensions.kt`（共 46 个 @JavascriptInterface 方法） |
| Rhino 版本锁定 | 项目 `AGENTS.md` Landmines 章节（rhino 1.8.1 锁定） |
