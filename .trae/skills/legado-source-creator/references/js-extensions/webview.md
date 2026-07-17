# JS 扩展函数参考 — WebView 操作

> 拆分自 js-extensions.md §二。Legado 书源 JS 环境中可调用的 WebView 浏览器操作扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.webView(null, url, js)`。

---

## 二、WebView 操作

### webView(html, url, js) / webView(html, url, js, cacheFirst) — 使用 WebView 加载页面

```javascript
// 加载 URL 并执行 JS 获取结果
var html = java.webView(null, "https://example.com/spa-page", "document.body.innerHTML");
// 加载 HTML 片段
var result = java.webView("<html>...</html>", "https://example.com", "document.title");
// 启用缓存加速
var html = java.webView(null, "https://example.com/page", "document.body.innerHTML", true);
// 返回: String（js 执行结果，js 为空则返回整个页面源码）
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| html | String | 否 | 直接载入的 HTML，为空则访问 url |
| url | String | 否 | 页面 URL（html 中有相对路径资源时需传入） |
| js | String | 否 | 取返回值的 JS 语句，为空则返回整个源码 |
| cacheFirst | Boolean | 否 | 优先使用缓存，默认 false |

**注意**：必须在后台线程调用，禁止主线程调用。

**使用频率**：高

---

### webViewGetSource(html, url, js, sourceRegex) / webViewGetSource(..., cacheFirst) / webViewGetSource(..., cacheFirst, delayTime) — 使用 WebView 获取资源 URL

```javascript
var videoUrl = java.webViewGetSource(
    null, "https://example.com/video-page", null, ".*\\.m3u8.*"
);
var videoUrl = java.webViewGetSource(
    null, "https://example.com/video-page", null, ".*\\.m3u8.*", true, 2000
);
// 返回: String（匹配 sourceRegex 的资源 URL）
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| html | String | 否 | 直接载入的 HTML |
| url | String | 否 | 页面 URL |
| js | String | 否 | 预执行的 JS |
| sourceRegex | String | 是 | 资源 URL 匹配正则 |
| cacheFirst | Boolean | 否 | 优先使用缓存，默认 false |
| delayTime | Long | 否 | 延迟时间（毫秒），默认 0 |

**使用频率**：中

---

### webViewGetOverrideUrl(html, url, js, overrideUrlRegex) / webViewGetOverrideUrl(..., cacheFirst) / webViewGetOverrideUrl(..., cacheFirst, delayTime) — 使用 WebView 获取跳转 URL

```javascript
var redirectUrl = java.webViewGetOverrideUrl(
    null, "https://example.com/page", null, ".*download.*"
);
var redirectUrl = java.webViewGetOverrideUrl(
    null, "https://example.com/page", null, ".*download.*", true, 3000
);
// 返回: String（匹配 overrideUrlRegex 的跳转 URL）
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| html | String | 否 | 直接载入的 HTML |
| url | String | 否 | 页面 URL |
| js | String | 否 | 预执行的 JS |
| overrideUrlRegex | String | 是 | 跳转 URL 匹配正则 |
| cacheFirst | Boolean | 否 | 优先使用缓存，默认 false |
| delayTime | Long | 否 | 延迟时间（毫秒），默认 0 |

**使用频率**：中

---

### startBrowser(url, title) / startBrowser(url, title, html) — 打开内置浏览器

```javascript
java.startBrowser("https://example.com/login", "登录页面");
java.startBrowser("https://example.com/login", "登录页面", "<html>...</html>");
// 无返回值，打开浏览器让用户手动交互
```

**使用频率**：低

---

## 三、webView 启用方式与高级用法

### 四种 webView 启用方式

在书源规则中启用 WebView 加载页面，有以下四种写法：

#### 方式一：直接添加

```
https://xx?s={{key}},{"webView":true}
```

- 在 URL 后的 JSON 参数对象中添加 `"webView":true`
- 最常用的启用方式

#### 方式二：正则替换

```
规则##$##,{"webView":true}
```

- `##$##` 在规则结果末尾追加 JSON 参数
- 适合规则结果已经是完整 URL 的情况

#### 方式三：JS 拼接

```
规则@js:result+',{"webView":true}'
```

- 在 JS 中拼接 JSON 参数字符串
- 适合需要条件判断的场景

#### 方式四：`{{}}` 模板拼接

```
{{@@tag.a@href}},{"webView":true}
```

- `{{@@tag.a@href}}` 提取链接后拼接 JSON 参数
- 模板语法与 JSON 参数直接拼接

---

### webJs 返回值限制

**webJs 必须返回非空值**，否则 Legado 会反复重试。

| 行为 | 说明 |
|------|------|
| 返回空值 | Legado 重试执行 webJs，最多 30 次 |
| 超时 | 约 29 秒后超时退出 |
| 返回非空值 | 正常返回结果 |

> **源码确认**：BackstageWebView.kt L249-278，循环执行 webJs，返回 null 时继续重试，最多 30 次。

**避坑建议**：
- webJs 中避免返回空字符串或 null
- 使用 `document.querySelector()` 时注意可能返回 null
- 建议加默认值：`document.querySelector('.content') ? document.querySelector('.content').innerHTML : document.body.innerHTML`

---

### sourceRegex 嗅探完整流程

sourceRegex（资源正则）用于从 WebView 加载的页面中嗅探特定资源 URL，典型流程如下：

```
章节链接 + webView → 浏览器嗅探 → 资源正则 → 正文
```

**详细步骤**：

1. **章节链接启用 webView**：在目录规则中，章节 URL 添加 `{"webView":true}`
2. **浏览器加载页面**：Legado 使用内置 WebView 加载章节页面
3. **嗅探网络请求**：WebView 加载过程中，Legado 监听所有网络请求
4. **资源正则匹配**：用 `sourceRegex`（如 `.*\.m3u8.*`）匹配嗅探到的 URL
5. **返回匹配结果**：第一个匹配的资源 URL 作为正文内容

**配置示例**：

```json
{
  "ruleContent": "<js>result</js>",
  "sourceRegex": ".*\\.(m3u8|mp4).*"
}
```

**适用场景**：视频源嗅探 m3u8/mp4 地址、音频源嗅探 mp3/m4a 地址、加密资源动态加载。

---

### startBrowserAwait(url, title) / startBrowserAwait(url, title, refetchAfterSuccess) / startBrowserAwait(url, title, refetchAfterSuccess, html) — 打开浏览器并等待结果

```javascript
var response = java.startBrowserAwait("https://example.com/verify", "验证");
var response = java.startBrowserAwait("https://example.com/verify", "验证", true);
// 返回: StrResponse { url: String, body: String }
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | String | 是 | 要打开的链接 |
| title | String | 是 | 浏览器页面标题 |
| refetchAfterSuccess | Boolean | 否 | 验证成功后是否重新获取，默认 true |
| html | String | 否 | 预加载的 HTML |

**使用频率**：低

---

### getVerificationCode(imageUrl) — 获取验证码输入

```javascript
var code = java.getVerificationCode("https://example.com/captcha.jpg");
// 弹出验证码图片对话框，返回用户输入的验证码字符串
```

**使用频率**：中（搜索验证码场景常用）

### 搜索验证码自动处理（⚠️ 实战模式）

当网站搜索功能有图片验证码保护时，可在searchUrl中用`java.getVerificationCode()`自动处理：

```javascript
// searchUrl中的JS代码（ES5语法）
<js>
var u=baseUrl+'index.php?m=vod-search';
var ck=java.getCookie(u);
var html=java.ajax(u)+'';
var doc=org.jsoup.Jsoup.parse(html);
var imgSrc=doc.select('.ldg_verify').attr('src')+'';
if(imgSrc){
  var imgUrl=baseUrl+imgSrc+Math.random();
  var code=java.getVerificationCode(imgUrl);
  var checkUrl=baseUrl+'/inc/ajax.php?ac=code_check&code='+code+'&type=search&rnd='+Math.random();
  java.ajax(checkUrl+','+JSON.stringify({"Cookie":ck}));
}
result=u+','+JSON.stringify({
  "method":"POST",
  "body":"wd={{key}}&submit=search",
  "headers":{"Cookie":ck,"Content-Type":"application/x-www-form-urlencoded"}
});
</js>
```

**流程**：
1. 访问搜索页 → 获取验证码图片URL
2. `java.getVerificationCode(imgUrl)` 弹出验证码图片让用户输入
3. 提交验证码到验证接口（`/inc/ajax.php?ac=code_check`）
4. 返回搜索URL（含Cookie），Legado自动请求搜索结果

**关键**：
- 验证码基于PHPSESSID session，通过后Cookie自动传递
- `java.getCookie(u)` 获取当前Cookie用于后续请求
- searchUrl的JS代码必须**返回搜索URL**，不能在JS中直接执行搜索

## CF 绕过用法

webView() 可自动通过 Cloudflare JS Challenge（5秒盾），因为 WebView 是真实浏览器引擎，会执行 CF 的验证 JS。

> ⚠️ **重要修正**（2026-07-17）：原推荐的 `loginUrl: "@js:java.webView(null, source.sourceUrl, null, false);"` 已被源码验证为**错误**——[WebViewLoginFragment.loadUrl()](../../../../../../app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt) 直接把 loginUrl 当 URL 加载，**不识别 `@js:` 形式**。`@js:` 形式仅在 SourceLoginDialog 中有效（且需 `loginUi` 非空才走该分支）。

### 正确用法（不通过 loginUrl 触发）

CF 绕过的正确流程：

1. `loginUrl` 设为**普通首页 URL**（如 `https://example.com/`）
2. `loginCheckJs` 检测到 CF 时返回 `'CF_BLOCKED'` 标识（不调 `java.startBrowserAwait()`，避免陷阱#57 无限循环）
3. 用户手动点击"登录"按钮 → SourceLoginActivity → WebViewLoginFragment.loadUrl(loginUrl) 加载首页
4. WebView 自动执行 CF JS Challenge → Cookie 写入 CookieManager → onPageFinished 同步到 CookieStore

### webView() 方法的其他用途（非 loginUrl）

webView() 方法本身可用于在 JS 规则中获取**渲染后的 HTML**（如 PJAX 站点空壳 HTML，陷阱#50），此时返回值为渲染后的 HTML 字符串。

### 执行流程（用户手动触发）
1. 用户点击"登录"按钮 → WebView 加载 loginUrl（普通 URL）
2. WebView 自动执行 CF JS Challenge → CF 验证通过
3. cf_clearance Cookie → CookieManager → CookieStore（onPageFinished 自动同步）
4. 后续 OkHttp 请求自动携带 Cookie

### 注意事项
- webView() 是同步阻塞操作（5-10秒），不适合放在 loginCheckJs 中
- 仅能自动通过 JS Challenge，Turnstile/Interactive 需用户手动操作
- **loginUrl 中禁止使用 `@js:java.webView(...)` 形式**（源码锚定：WebViewLoginFragment.loadUrl 不识别 @js: 形式）
