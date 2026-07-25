# 书源/订阅源类型选择陷阱

> 书源/订阅源类型选择和配置字段导致的运行时错误。

## 4.1 RssSource 搜索功能

> ⚠️ **RssSource 支持搜索！** 通过 `searchUrl` 字段配置，与 BookSource 的 searchUrl 语法完全一致。

**关键区别**：
- **BookSource**：搜索在"搜索"页面，5 组规则（Search/Explore/BookInfo/Toc/Content）
- **RssSource**：搜索在"分类"页面，规则字段为 ruleArticles/ruleTitle/ruleLink/ruleImage/ruleContent

**选择建议**：
- 视频/图片站需要搜索 + 浏览列表 → **RssSource**
- 小说/文章站需要章节目录 → **BookSource**（bookSourceType=0/1/2/3）
- 简单 RSS 订阅无搜索需求 → **RssSource**（type=0，仅 sortUrl）

## 4.2 RssSource type 字段选择（⚠️ 高频陷阱）

**现象**：ruleContent 拼装了自定义 HTML 播放器，但视频无法播放或页面显示异常。

**原因**：RssSource 的 `type` 字段决定了 Legado 如何渲染 ruleContent 的返回值：

| type | 渲染方式 | ruleContent 应返回 |
|------|----------|-------------------|
| 0 | WebView 渲染 HTML | 完整的 HTML 字符串（自定义播放器、图文混排等） |
| 1 | 图片查看器 | 图片 URL 列表 |
| 2 | 内置视频播放器 | **纯视频 URL**（.mp4、.m3u8 链接） |

**关键决策**：
- **ruleContent 拼装 HTML → type=0**（WebView 渲染自定义页面）
- **ruleContent 直接返回视频 URL → type=2**（内置播放器播放）
- ❌ **常见错误**：ruleContent 拼装了 HLS 播放器 HTML，但 type=2，Legado 把 HTML 字符串当作视频 URL 传给内置播放器，导致播放失败
- ✅ **正确做法**：自定义 HTML 播放器用 type=0，让 WebView 渲染

**示例**：
```json
// ❌ 错误：ruleContent 返回 HTML 播放器，但 type=2
{
  "type": 2,
  "ruleContent": "@js:var h='<!DOCTYPE html>...<video>...';h;"
}

// ✅ 正确：ruleContent 返回 HTML 播放器，用 type=0 让 WebView 渲染
{
  "type": 0,
  "ruleContent": "@js:var h='<!DOCTYPE html>...<video>...';h;"
}

// ✅ 正确：ruleContent 直接返回 m3u8 URL，用 type=2 内置播放器
{
  "type": 2,
  "ruleContent": "@js:var m=result.match(/video_url:'([^']+)'/);m?m[1]:'';"
}
```

### 4.2.1 实战案例：91短视频 HLS.js 播放器（⚠️ type 选择教训）

**我的错误**：生成订阅源时用了 `type: 2`，ruleContent 只提取 m3u8 URL，以为 Legado 内置播放器能直接播放。

**用户优化**：改为 `type: 0`，ruleContent 返回完整的 HLS.js 播放器 HTML（~20000字符），包含：
- 视频进度条、缓冲进度显示
- 快进/快退按钮（30s/1m/3m）
- 倍速播放选择（1x/3x/5x/10x/15x）
- 全屏按钮、上一集/下一集切换
- 视频源选择下拉框
- 完整的 CSS 样式和 HLS.js 初始化逻辑

**教训**：
- 视频订阅源的核心价值是**用户体验**，不能只提取 URL
- 自定义播放器界面必须用 `type: 0`，让 WebView 渲染 HTML
- `type: 2` 仅适用于 ruleContent **直接返回纯视频 URL** 的场景

**HLS.js 播放器模板参考**：见 `js-patterns/hls-player.md`

## 4.3 视频源选择

**现象**：视频网站通常每个视频只有一个播放地址，不需要章节目录。

**解决方案**：目录规则使用 `"-"` 表示无目录：
```json
{
  "ruleToc": {
    "chapterList": "-",
    "chapterName": ".title@text",
    "chapterUrl": ""
  }
}
```

## 4.4 loginCheckJs 必须始终返回 StrResponse（⚠️ 高频 NPE 陷阱）

**现象**：导入订阅源后，加载文章列表立即崩溃：
```
java.lang.NullPointerException: null cannot be cast to non-null type io.legado.app.help.http.StrResponse
```

**根因**：`loginCheckJs` 的 JS 代码在某些分支没有返回值（返回 `undefined`），Kotlin 将 `undefined` 强转为 `StrResponse` 时 NPE。

**源码依据**：`Rss.kt:54-61` — `analyzeUrl.evalJS(checkJs, it) as StrResponse`，`evalJS` 返回 JS 表达式的值，如果 JS 没有显式返回，则为 `null`。

**错误写法**：
```javascript
// ❌ if 条件不满足时返回 undefined → NPE
var src=result.body();if(src.includes('验证')){java.startBrowserAwait(...)}

// ❌ 使用 document.querySelector（WebView API，Rhino 中不可用！）
document.querySelector('a[href*="logout"]')!=null
```

**正确写法**：
```javascript
// ✅ 末尾加 ;result 确保始终返回 StrResponse
var src=result.body();if(src.includes('验证')){java.startBrowserAwait(...)};result

// ✅ 通过 result.body() 检查页面内容（Rhino 环境）
var s=result.body();if(s.indexOf('退出')==-1){java.startBrowserAwait(source.loginUrl,'登录');result}else{result}
```

**⚠️ loginCheckJs 在 Rhino 引擎中执行，不是 WebView！** 没有 `document`/`window` 对象，不能用 `document.querySelector()` 等浏览器 API。只能通过 `result.body()` 获取页面 HTML 内容来检查登录状态。

**可用的变量**（源码：AnalyzeUrl.kt L364-388）：
- `result` — StrResponse 对象，`result.body()` 获取页面 HTML
- `source` — RssSource/BookSource 对象，`source.loginUrl` 获取登录 URL
- `java` — JsExtensions 实例
- `cookie` — CookieStore
- `cache` — CacheManager
- `baseUrl` — 基础 URL
- `key` — 搜索关键字
- `page` — 页码

**规则**：**所有 loginCheckJs 必须以 `;result` 结尾**，确保无论哪个分支都返回原始 StrResponse 对象。

## 4.5 反爬网站必须用 `{"webView":true}` 强制 WebView 加载（⚠️ 关键）

**现象**：网站在浏览器中正常访问，但 Legado 加载文章列表/搜索时返回空或报错。

**根因**：网站有 TLS 指纹检测或 HTTP/2 协议限制，OkHttp 请求被拒绝。`RssSource.enableJs=true` 只影响 WebView 的 JS 执行设置，**不影响** `AnalyzeUrl.getStrResponseAwait()` 的请求方式。默认仍使用 OkHttp。

**源码依据**：`AnalyzeUrl.kt:445` — `if (this.useWebView && useWebView)` 才会使用 `BackstageWebView`。`useWebView` 来自 URL option 的 `webView` 字段，与 `RssSource.enableJs` 无关。

**解决方案**：在 sourceUrl、sortUrl、searchUrl 中添加 `,{"webView":true}` 选项：

```json
{
  "sourceUrl": "https://example.com/,{\"webView\":true}",
  "sortUrl": "最新::/,{\"webView\":true}\n热门::/hot,{\"webView\":true}",
  "searchUrl": "/search?q={{key}},{\"webView\":true}"
}
```

**判断标准**：如果 curl 桌面 UA 无法访问但手机 UA 可以，或 Playwright 需要 `--disable-http2` 才能访问，就必须加 `{"webView":true}`。

## 4.6 RssSource 搜索功能（⚠️ 必须配置）

**现象**：订阅源没有搜索功能，用户无法按关键词查找。

**根因**：遗漏了 `searchUrl` 字段。RssSource 支持 `searchUrl`，搜索结果复用 `ruleArticles`/`ruleTitle`/`ruleLink` 等规则。

**规则**：**除非原网站确实不支持搜索，否则必须配置 searchUrl**。

```json
{
  "searchUrl": "/search?wd={{key}},{\"webView\":true}",
  "ruleArticles": "div.module-item",
  "ruleTitle": "a.module-item-title@text",
  "ruleLink": "div.module-item-pic a@href"
}
```

### ⚠️ 搜索结果与列表页HTML结构可能不同（高频陷阱！）

> **这是本次实战踩坑的最重要教训！** 很多论坛/网站的搜索结果页 HTML 结构与列表页不同，直接复用列表页规则会导致搜索结果为空或数据错乱。

**典型差异**：

| 差异点 | 列表页 | 搜索结果页 |
|--------|--------|-----------|
| 列表项类名 | `tr3 t_one` | `tr3 tac` |
| 标题链接 | `<a class="subject" href="...">` | `<a href="...">`（无class） |
| 图片容器 | `<a class="lazy-imgs" data-src="URL">` | `<img class="thumb-img" data-src="URL">` |
| 置顶帖 | 有（需跳过） | 无 |
| 日期格式 | `<span style="...">` | `<span class="meta-date">` |

**兼容方案**：用 `||` 操作符，先尝试列表页选择器，失败则回退搜索结果选择器：

```json
{
  "ruleArticles": "class.tr3",
  "ruleLink": "class.subject@href||tag.a.0@href",
  "ruleTitle": "class.subject@text||tag.a.0@text",
  "ruleImage": "class.lazy-imgs.0@data-src||tag.img.0@data-src"
}
```

**⚠️ ruleArticles 索引跳过问题**：如果列表页用 `class.tr3[!0:3]` 跳过置顶帖，搜索结果页无置顶帖，`[!0:3]` 会误跳前3条正常结果。有 searchUrl 时建议去掉索引跳过。

**⚠️ searchUrl 分页问题**：当 `ruleNextPage="page"` 时，Legado 将 `nextUrl=sortUrl`（源码：RssParserByRule.kt L58-59）。如果 searchUrl 的 body 中没有 `page={{page}}` 参数，搜索结果无法翻页。POST 搜索的正确写法：

```json
{
  "searchUrl": "/search.php,{\"method\":\"POST\",\"body\":\"step=2&keyword={{key}}&page={{page}}\"}",
  "ruleNextPage": "page"
}
```

**⚠️ 搜索需登录时的策略**：

| 场景 | 策略 | 原因 |
|------|------|------|
| 浏览和搜索都需要登录 | 设 loginUrl + loginCheckJs | loginCheckJs 自动检测并触发登录 |
| 仅搜索需登录，浏览不需要 | 只设 loginUrl，不设 loginCheckJs | loginCheckJs 每次请求都执行，浏览列表时也会弹登录窗 |
| 不需要登录 | 都不设 | — |

**⚠️ 搜索验证强制步骤**（禁止跳过！）：

1. **分析搜索表单**：用 Playwright/curl 获取搜索页面 HTML，分析 `<form>` 的 action、method 和 `<input>` 参数名
2. **确认参数名**：不同论坛系统参数名不同（PHPWind 用 `keyword`，Discuz 用 `srchtxt`），必须分析实际表单，不能按论坛类型臆测
3. **验证搜索是否需要登录**：用 Playwright 分别在登录和未登录状态下执行搜索，对比结果
4. **验证搜索结果HTML结构**：对比搜索结果页和列表页的 HTML 结构，确认规则兼容性
5. **验证分页**：确认 searchUrl 中是否包含 `{{page}}` 参数

## loginCheckJs 返回值陷阱

### 陷阱：loginCheckJs 返回 String 而非 StrResponse

**现象**：loginCheckJs 中调用 `java.ajax()` 后直接返回，导致 Legado 崩溃。

**原因**：loginCheckJs 必须返回 StrResponse 对象（即 `result`），`java.ajax()` 返回 String。

**正确写法**：
```javascript
var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;
```

**错误写法**：
```javascript
var s=result.body();if(s.indexOf('Just a moment')!=-1){return java.ajax(source.sourceUrl);}  // ❌ ajax()返回String
```

**修复**：末尾始终加 `result;`，确保返回 StrResponse 对象。

## 4.7 搜索验证码处理（⚠️ 实战教训）

**现象**：搜索时返回"系统安全验证"页面，需要输入图片验证码才能搜索。

**案例**：1080zyk.com 搜索时触发图片验证码保护（`/inc/common/code.php?a=search`），与CF盾完全独立。

**验证码机制**：
1. 搜索请求 → 服务端检测session中无搜索验证标记 → 返回验证码页面
2. 验证码图片：`/inc/common/code.php?a=search&s=随机数`
3. 验证接口：`/inc/ajax.php?ac=code_check&code=XXX&type=search`
4. 验证通过后：`location.reload()` 重新加载搜索结果
5. **关键**：验证码基于PHPSESSID session，通过后后续搜索不再需要验证码

**Legado解决方案**：

```json
{
  "loginUrl": "@js:java.startBrowserAwait(source.sourceUrl,'1.通过Cloudflare验证 2.搜索任意关键词 3.输入搜索验证码后关闭');",
  "loginCheckJs": "@js:if(result&&result.indexOf('系统安全验证')!=-1){java.startBrowserAwait(source.sourceUrl,'搜索验证码过期，请重新输入验证码后关闭');}",
  "searchUrl": "https://xxx/index.php?m=vod-search,{\"method\":\"POST\",\"body\":\"wd={{key}}&submit=search\"}",
  "enabledCookieJar": true
}
```

**流程**：
1. **首次使用**：loginUrl让用户同时过CF盾+搜索验证码，两步验证Cookie都保存
2. **搜索时验证码过期**：loginCheckJs检测到"系统安全验证"→弹浏览器让用户重新输入
3. **Cookie传递**：enabledCookieJar:true确保PHPSESSID自动传递

**注意**：
- loginCheckJs检测的是搜索结果页面内容，**不能检测CF盾**（会无限循环）
- 验证码基于session，通过后Cookie自动传递，后续搜索不需要验证码

## 4.8 ruleContent不要嵌入HTML模板（⚠️ 高频陷阱）

**现象**：ruleContent嵌入了完整的HTML+JS播放器模板，导致：
1. JSON格式不合法 → Legado提示"不受支持"
2. Rhino语法错误 → `在语句前面缺少";"`
3. 正则表达式转义混乱

**根因**：
- HTML模板中的`</script>`需要特殊处理（`</'+'script>`）
- 模板中的正则表达式`replace(/'/g,"\\'")`，`/'/g`在Rhino中解析失败
- 多层嵌套转义（JSON→JS→HTML→JS）极易出错

**解决方案**：ruleContent只返回数据，不嵌入HTML模板：

```javascript
// 只返回视频URL列表（名称$URL格式，每行一个）
<js>
var doc=org.jsoup.JSoup.parse(result);
var items=doc.select('.playlist li a');
var urls=[];var names=[];
for(var i=0;i<items.size();i++){
  var item=items.get(i);
  var cb=item.select('input[type=checkbox]').first();
  if(cb){
    var v=cb.attr('value')+'';
    var label=(item.text()+'').replace(/\s+/g,'');
    if(v.indexOf('$')!=-1){
      var parts=v.split('$');
      if(parts.length>1){names.push(parts[0]||label);urls.push(parts[1]);}
    }else if(v.indexOf('http')==0||v.indexOf('.m3u8')!=-1){
      names.push(label);urls.push(v);
    }
  }
}
var resultStr='';
for(var j=0;j<urls.length;j++){
  if(j>0){resultStr=resultStr+'\n';}
  resultStr=resultStr+names[j]+'$'+urls[j];
}
result=resultStr;
</js>
```

Legado的内置播放器会自动处理m3u8链接，无需自定义HTML播放器。

## 4.9 shouldOverrideUrlLoading 仅绑定 java 和 url（⚠️ 高频陷阱）

> 验证日期：2026-07-20
> 源码依据：ReadRssActivity.kt L749-770

**现象**：shouldOverrideUrlLoading 中使用了 `cookie`、`baseUrl`、`source` 等变量，运行时报 `ReferenceError` 或 JS 不执行。

**根因**：shouldOverrideUrlLoading 的 JS 绑定**仅有 `java` 和 `url` 两个变量**，与 loginCheckJs 的完整绑定不同。

**可用变量对比**：

| 变量 | loginCheckJs | shouldOverrideUrlLoading | injectJs |
|------|-------------|--------------------------|----------|
| java | ✅ JsExtensions | ✅ RssJsExtensions | ❌ |
| url | ❌ | ✅ 当前跳转URL | ❌ |
| result | ✅ StrResponse | ❌ | ❌ |
| cookie | ✅ CookieStore | ❌ | ❌ |
| cache | ✅ CacheManager | ❌ | ❌ |
| baseUrl | ✅ | ❌ | ❌ |
| source | ✅ | ❌ | ❌ |
| document | ❌ | ❌ | ✅ (WebView) |
| window | ❌ | ❌ | ✅ (WebView) |

**正确写法**：
```javascript
// ✅ 仅使用 java 和 url
if(url.indexOf('/category/')>-1){java.open('sort',url);true}else{false}
```

**另外**：shouldOverrideUrlLoading 不经过 AnalyzeUrl，`{{}}` 模板语法不会被处理！

## 4.10 header 中 Accept-Encoding 导致 OkHttp 响应乱码（⚠️ 高频陷阱）

> 验证日期：2026-07-20
> 详见 [html-fetch-traps.md §1.1h](html-fetch-traps.md)

**现象**：配置了 `Accept-Encoding: gzip, deflate, br` 后，OkHttp 返回乱码，CSS 选择器匹配 0 元素。

**根因**：OkHttp 没有 brotli 解码器，手动指定 `br` 后响应体直接透传压缩数据。

**规则**：**永远不要在 header 中设置 `Accept-Encoding`、`Connection`、`Upgrade-Insecure-Requests`**。OkHttp 自动管理这些头。

## 4.11 CookieStore 过期值覆盖 header Cookie（⚠️ "时好时不好"陷阱）

> 验证日期：2026-07-20
> 源码依据：CookieManager.kt L57-77、L103-109

**现象**：header 中预置了正确的 Cookie，但列表加载时好时不好——有时正常返回数据，有时返回验证页面。

**根因**：`CookieManager.loadRequest()` 合并 header Cookie 和 CookieStore Cookie 时，**CookieStore 的值覆盖 header 的值**（`acc.apply { putAll(cookieMap) }`）。如果 CookieStore 中存有旧/过期的 Cookie，合并后正确值被覆盖。

**解决方案**：在 loginCheckJs 中先清除再重设：
```javascript
var src=result.body();
if(src&&src.indexOf('VERIFICATION_KEYWORD')>-1){
  cookie.removeCookie(baseUrl);  // 先清除过期值！
  cookie.setCookie(baseUrl,'CORRECT_VALUE');
}
result
```

## 4.12 Rhino正则不能含单引号（⚠️ 语法陷阱）

**现象**：Rhino报错 `在语句前面缺少 ";" (#1)`

**根因**：正则表达式字面量中包含单引号，Rhino无法正确解析：
```javascript
urlStr.replace(/'/g, "\\'")  // ❌ Rhino解析失败
```

Rhino遇到 `/'/g` 时，把 `/'` 误解析为除法运算符 `/` 后跟字符串开始 `'`。

**解决方案**：
```javascript
// 方案1：用new RegExp构造函数
urlStr.replace(new RegExp("'", "g"), "\\'")  // ✅

// 方案2：避免在Rhino代码中使用含单引号的正则
// 如果只是转义单引号，可以用split+join替代
urlStr.split("'").join("\\'")  // ✅
```
