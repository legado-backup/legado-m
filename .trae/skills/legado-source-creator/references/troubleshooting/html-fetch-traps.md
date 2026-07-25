# HTML 获取陷阱

> 基于实战经验总结的网站HTML获取失败的各种原因和解决方案。

## 1.1 WebFetch 无法获取原始 HTML 标签结构

**现象**：使用 WebFetch 获取网页内容后，返回的是纯文本渲染结果，所有 HTML 标签信息（class、id、属性）全部丢失。

**后果**：无法编写正确的 CSS 选择器，推测的选择器与真实结构可能完全不同。

**示例**：
- 推测：`ul.list > li` → 实际：`ul.ucontent > li`
- 推测：`img@src` → 实际：`input.h_d_pic@value`（封面URL在hidden input中）
- 推测：`a:nth-child(2)@text` → 实际：`div.ctitle > p@text`

**解决方案**：

| 工具 | 适用场景 | 命令示例 |
|------|----------|----------|
| **curl** | 静态 HTML 页面 | `curl -s -L "URL" \| sed -n '/<ul/,/<\/ul>/p'` |
| **Playwright** | JS 动态渲染页面 | `npx playwright install chromium` 后通过脚本获取 |
| **Puppeteer** | JS 动态渲染页面 | MCP 工具 `puppeteer_navigate` + `puppeteer_evaluate` |
| **WebFetch** | ❌ 仅获取纯文本概览 | 不适合分析 HTML 结构 |

## 1.2 封面图不在 img 标签中

**现象**：CSS 选择器 `img@src` 返回空值。

**常见替代位置**：
- CSS `background-image`：`div.cover` 的 `style="background-image:url('...')"` → 用正则提取
- Hidden input：`<input type="hidden" class="h_d_pic" value="URL">` → `input.h_d_pic@value`
- 自定义属性：`<div data-src="URL">` → `div@data-src`
- Video poster：`<video poster="URL">` → `video@poster`

## 1.3 视频地址在自定义属性中

**现象**：`video@src` 返回空值。

**常见替代位置**：
- 自定义属性：`<a playdata="m3u8_URL">` → `.playsource a@playdata`
- Data 属性：`<div data-url="m3u8_URL">` → `div@data-url`
- JS 变量：页面 JS 中 `var playurl = "m3u8_URL"` → 需用正则或 JS 提取

## 1.1c HTTP/2 协议错误 + CDN 白名单拦截（非 CF）

**现象**：curl/Playwright/httpx 所有工具均无法访问网站，返回 `HTTP/2 stream PROTOCOL_ERROR`、`Connection closed abruptly`、`NS_ERROR_NET_INTERRUPT` 等错误。

**根因**：网站 CDN/WAF 在 TLS/HTTP2 层面检测客户端指纹，拒绝非浏览器连接。这不是 Cloudflare，而是更底层的 CDN 白名单机制（如阿里云 CDN 域名白名单）。

**关键发现**：此类网站通常**对手机 UA + HTTP/1.1 更友好**，桌面 UA 或 HTTP/2 会被直接拒绝。

**解决方案**：

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1 | curl `--http1.1` + 手机 UA | 先用 HTTP/1.1 + 移动端 User-Agent 尝试 |
| 2 | Playwright `--disable-http2` + 手机 Context | 模拟移动浏览器，禁用 HTTP/2 |
| 3 | Wayback Machine 快照 | 如果直接访问仍失败，用 `web.archive.org/web/TIMESTAMP/URL` 获取历史快照分析结构 |
| 4 | Legado 中配置 | `header` 设置手机 UA + `enableJs:true` + 开启 Cronet |

**Playwright 手机模式示例**：
```python
browser = await p.chromium.launch(headless=True, args=['--disable-http2'])
context = await browser.new_context(
    user_agent='Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 ...',
    viewport={'width': 412, 'height': 915},
    is_mobile=True, has_touch=True,
)
```

**CDN 白名单拦截特征**：返回 HTML 包含"您的域名并未添加白名单导致无法访问"，需在 `loginCheckJs` 中检测此文本并触发 WebView 验证。

## 1.1d Vue3 SPA + Web Worker 图片加密站点

**现象**：网站是 Vue3 SPA，图片通过 Web Worker (PicWorker.js) 解密后显示为 `blob:` URL，`data-cover` 属性中的是加密图片 URL。

**分析要点**：
1. PicWorker.js 通常使用 sojson.v4 混淆，但可从中提取 AES 密钥
2. 图片加密模式常见为 AES/ECB/NoPadding
3. Legado 中使用 `coverDecodeJs` + `java.createSymmetricCrypto()` 解密

**coverDecodeJs 模板**（⚠️ 必须返回 ByteArray，不是 data URI 字符串）：
```javascript
// ✅ 正确：返回解密后的 ByteArray
java.createSymmetricCrypto('AES/ECB/NoPadding', 'KEY', null).decrypt(result)

// ❌ 错误：返回 data URI 字符串（Legado 期望 ByteArray）
// var b64 = java.base64Encode(dec); 'data:image/png;base64,' + b64
```

**源码依据**：`ImageUtils.kt:28-32` — `coverDecodeJs` 中 `result` 是 ByteArray，JS 返回值也必须是 ByteArray。

**iframe 嵌套播放器提取 m3u8**：视频播放器常嵌在 `<iframe>` 中，src 格式为 `player.html?url=m3u8_URL`，需用 JS 提取：
```javascript
var m = result.match(/url=([^&"]+)/);
m ? decodeURIComponent(m[1]) : ''
```

### 1.1e webView 参数需要实际验证（⚠️ 实战教训）

**我的错误**：根据 Playwright 测试结果（需要 `--disable-http2` + 手机 UA），推断 Legado 也需要 `{"webView":true}` 参数，在所有 URL 中都加了此参数。

**用户实际测试结果**：完全不需要 `{"webView":true}` 参数，网站在 Legado 中可以正常访问。

**根因**：
- Playwright 测试环境 ≠ Legado 实际环境
- Legado 的 OkHttp + Cronet + header 配置可能已经足够绕过反爬
- 理论推断不能替代实际测试

**教训**：
- webView 参数是**可选优化**，不是**必需配置**
- 生成订阅源后必须在 Legado 中实际测试，验证是否真的需要 webView

### 1.1f 不能用 BeautifulSoup 模拟 jsoup 选择器行为（⚠️ 源码验证教训）

**我的错误**：安装 `beautifulsoup4` + `lxml` 试图用 BeautifulSoup 模拟 jsoup 的 CSS 选择器行为，验证选择器是否正确。

**为什么这是错的**：

| 维度 | BeautifulSoup (Python) | jsoup (Java, Legado 使用) |
|------|----------------------|--------------------------|
| `:has()` 伪选择器 | ❌ 不支持 | ✅ 支持（1.14.1+） |
| `:not()` 复杂参数 | ❌ 仅支持简单选择器 | ✅ 支持 |
| Default 语法 `:` 分隔符 | 不存在此概念 | ✅ `:` 被当作索引分隔符（AnalyzeByJSoup.kt L491） |
| `@CSS:` 前缀 | 不存在此概念 | ✅ 绕过 Default 语法解析器 |
| `@text`/`@href` 后缀 | 不存在此概念 | ✅ Legado 提取后缀 |

**根因**：BeautifulSoup 是 Python 的 HTML 解析库，与 Legado 的 jsoup + Default 语法体系完全不同。用 BS4 "验证" 选择器等于用错误的尺子量尺寸。

**正确做法**：

| 验证目标 | 正确方法 |
|----------|----------|
| CSS 选择器是否被 jsoup 支持 | 直接读 Legado 源码 `AnalyzeByJSoup.kt`，理解 Default 语法解析流程 |
| 选择器是否被 Default 语法错误解析 | 读 `findIndexSet()` (L406-510) 和 `getElementsSingle()` (L303-322) |
| `@CSS:` 前缀是否需要 | 含 `:` 的伪类选择器（`:has()`/`:not()`/`:first-child` 等）**必须加** |
| 选择器是否匹配 HTML 元素 | 用 Python 正则模拟 jsoup 的 `select()` 结果（仅验证匹配数量） |

**教训**：
- **验证选择器行为的唯一可靠方式是读 Legado 源码**，不是用第三方库模拟
- **不要 pip install 第三方库来"模拟" jsoup** — 浪费时间且结果不可靠
- Python 正则可以用来**粗略验证**选择器匹配数量，但不能验证 Default 语法解析行为
- 如果 header + enableJs + enabledCookieJar 已经能正常访问，就不要加 webView
- webView 会增加加载时间，过度使用反而降低用户体验

**判断标准**：
| 测试结果 | 是否需要 webView |
|---------|----------------|
| OkHttp 直接访问成功 | ❌ 不需要 |
| OkHttp 失败，但 header/cookie 配置后成功 | ❌ 不需要 |
| 所有 HTTP 配置都失败，只有 WebView 能加载 | ✅ 需要 |
| 网站有复杂的 JS 渲染（SPA）| ✅ 可能需要（enableJs=true 也可能够） |

### 1.1g PJAX 网站：OkHttp 获取空壳 HTML，CSS 选择器匹配 0 元素（⚠️ 实战教训）

**现象**：
- OkHttp/Python requests 获取的 HTML 长度正常（如 76176 字符），看起来是完整页面
- 但 CSS 选择器（如 `article`、`article:has(h2.post-card-title)`）匹配 0 个元素
- HTML 中包含 `content404-wrapper` 等 404 相关 class
- 浏览器中页面正常显示，有文章列表

**根因**：网站使用 **PJAX**（pushState + AJAX）技术，页面内容通过 JS 动态加载。OkHttp 只能获取初始 HTML（空壳），真实内容需要 JS 执行后才能渲染到 DOM 中。

**诊断方法**：
1. 用 Python requests 获取 HTML，搜索目标选择器（如 `article`）的匹配数量
2. 如果匹配 0，搜索 `pjax`、`PJAX`、`pushState` 关键词
3. 检查 HTML 中是否有 `content404-wrapper`（说明返回的是 404 空壳）
4. 检查 HTML 中是否有 `encryptedData`（说明有加密配置数据）

**解决方案**（按优先级排列）：

| 方案 | 写法 | 优缺点 |
|------|------|--------|
| **方案1：`java.webView()` 按需调用** | `<js>var html=java.webView(null,url,'document.querySelector(".archive").innerHTML',true);...` | ✅ 只在 ruleArticles/ruleContent 中使用 WebView，其他步骤仍走 OkHttp，比 `{"webView":true}` 轻量 |
| **方案2：`{"webView":true}` 全局** | `sourceUrl,{"webView":true}` | ❌ 整个请求走 WebView，加载慢，用户反馈卡顿 |
| **方案3：`@webjs:` 前缀** | `@webjs:document.querySelectorAll('.article-item')` | ⚠️ 只在特定规则上使用 WebView 环境 |

**`java.webView()` 方案要点**：
- `java.webView(null, url, js, cacheFirst)` — 第 1 个参数为 null 表示访问 url，第 3 个参数是取返回值的 JS 语句，第 4 个参数启用缓存
- `cacheFirst=true` 可以加速重复访问
- 在 `ruleArticles` 中：用 `java.webView()` 获取渲染后的 HTML，再用 jsoup 解析
- 在 `ruleContent` 中：同样用 `java.webView()` 获取渲染后的正文内容
- `sortUrl` 必须使用**完整 URL**（如 `https://xxx/category/xxx/page/1/`），不能用相对路径（如 `/category/xxx/page/1/`），因为 `java.webView()` 需要完整 URL

**关键教训**：
- **不要假设 OkHttp 获取的 HTML 就是浏览器看到的 HTML** — 即使长度正常，内容也可能是空壳
- **Python requests 获取的 HTML ≠ 浏览器渲染后的 HTML** — requests 也不执行 JS
- **WebFetch 能获取渲染后的内容**，但不能用来验证 OkHttp 获取的内容是否完整
- **验证 OkHttp 获取内容是否完整的唯一方式**：用 Python requests 获取 HTML，搜索目标选择器的匹配数量

## 1.1h Accept-Encoding 头导致 OkHttp 响应乱码（⚠️ 实战教训）

**现象**：订阅源/书源配置了 `Accept-Encoding: gzip, deflate, br` 请求头后，OkHttp 返回的 HTML 内容全是乱码，CSS 选择器匹配 0 元素。

**根因**：OkHttp 默认自动添加 `Accept-Encoding: gzip` 并在收到 gzip 响应后自动解码。但手动设置 `Accept-Encoding` 头后：

1. **OkHttp 不再自动添加** `Accept-Encoding` 头，而是使用用户指定的值
2. 如果指定了 `br`（brotli 编码），OkHttp **没有内置 brotli 解码器**，无法解码响应
3. 服务器返回 brotli 编码的响应体，OkHttp 直接将压缩数据当作原始 HTML 传给解析器
4. 解析器收到的是乱码字节流，CSS 选择器自然匹配不到任何元素

**源码依据**：OkHttp 的 `BridgeInterceptor` 在用户未指定 `Accept-Encoding` 时自动添加 `gzip`，并在 `ResponseBody` 中自动解包 gzip。但用户手动指定后，`BridgeInterceptor` 不再干预，响应体直接透传。

**解决方案**：

```json
// ❌ 错误：手动设置 Accept-Encoding（含 br）
"header": "{\n\t\"Accept-Encoding\": \"gzip, deflate, br\"\n}"

// ✅ 正确：不要设置 Accept-Encoding，让 OkHttp 自动管理
"header": "{\n\t\"User-Agent\": \"...\",\n\t\"Accept-Language\": \"zh-CN,zh;q=0.9\"\n}"
```

**教训**：
- **永远不要手动设置 `Accept-Encoding` 头** — OkHttp 会自动处理 gzip 编解码
- **不要设置 `Connection: keep-alive`** — OkHttp 自动管理连接
- **不要设置 `Upgrade-Insecure-Requests`** — 这是浏览器行为，App 网络请求不需要
- 只设置对业务逻辑有意义的头（如 User-Agent、Cookie、Referer、Accept-Language）

**诊断方法**：
1. 检查 `sourceDebug` 日志：如果显示 `列表大小:0` 但 HTML 长度不为 0，可能是编码问题
2. 检查响应内容：如果包含大量不可读字符（乱码），大概率是 Accept-Encoding 导致的
3. 移除 Accept-Encoding 头后重新测试

## CF 保护网站获取方案

当 curl 直接获取被 CF 拦截时，使用 html_fetcher.py 回退链：

1. **Wayback Machine**：查询 CDX API 获取历史快照，清理注入代码
2. **CMS 样本库**：检测 CMS 类型，使用标准样本 HTML 验证选择器
3. **Google Cache**：查询缓存页面（可靠性已下降）
4. **Playwright**：浏览器自动化获取渲染后 HTML

### 使用方式
```bash
python tools/html_fetcher.py --url URL --json
```

### CF 绕过（Legado 运行时）
- JS Challenge：loginUrl 中 `java.webView()` 自动通过
- Turnstile：loginCheckJs 中 `java.startBrowserAwait()` 手动通过

### 1.2a Cloudflare 5秒盾：Playwright vs DrissionPage（⚠️ 实战教训）

**现象**：网站有CF 5秒盾，Playwright打开浏览器后用户手动点击验证也无法通过，一直循环验证。

**根因**：Playwright 通过 CDP（Chrome DevTools Protocol）控制浏览器，CF 能检测到以下自动化特征：
1. `navigator.webdriver = true`（即使注入stealth脚本也难以完全隐藏）
2. CDP 连接本身（`--remote-debugging-port`）
3. `Runtime.enable` 等 CDP 命令触发的检测

**解决方案**：使用 **DrissionPage** 替代 Playwright

| 工具 | CF检测结果 | 原因 |
|------|-----------|------|
| Playwright + stealth | ❌ 验证循环 | CDP协议被检测 |
| Playwright + channel="chrome" + stealth | ❌ 验证循环 | 仍走CDP |
| **DrissionPage** | ✅ 10秒通过 | 不走CDP，直接接管浏览器进程 |

**DrissionPage 关键代码**：
```python
from DrissionPage import ChromiumPage, ChromiumOptions

co = ChromiumOptions()
co.set_argument('--start-maximized')
co.set_argument('--disable-blink-features=AutomationControlled')
page = ChromiumPage(co)
page.get('https://example.com/')
# CF验证自动通过，无需手动点击
```

**Legado 中的 CF 盾处理**：
- `loginUrl`: `@js:java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');`
- `enabledCookieJar: true`：确保 CF Cookie（`cf_clearance`）被保存和传递
- `loginCheckJs`: **留空**！不要用 loginCheckJs 检测 CF，否则会无限循环（每次请求都触发检测→弹浏览器→通过→又检测→又弹）
- CF Cookie 有效期通常数小时到数天，过期后用户需重新登录

**CF 盾关键特征**：
- **首页验证**：CF盾必须在首页人工干预才能解除，子页面无法独立破盾
- **Cookie传递**：首页通过CF后，`cf_clearance` Cookie 会被保存，后续子页面请求自动携带
- **时效性**：`cf_clearance` 有过期时间，过期后需重新验证

### 1.2b 应用层搜索验证码（独立于CF盾）（⚠️ 实战教训）

**现象**：网站搜索功能有独立的图片验证码保护，与CF盾完全无关。即使CF验证通过，搜索仍被验证码拦截。

**案例**：1080zyk.com 搜索时返回"系统安全验证"页面，需输入图片验证码。

**验证码机制分析**：
1. 搜索请求（GET/POST）→ 服务端检测session中无搜索验证标记 → 返回验证码页面
2. 验证码图片：`/inc/common/code.php?a=search&s=随机数`
3. 验证接口：`/inc/ajax.php?ac=code_check&code=XXX&type=search` → 返回 `{"code":1}` 或 `{"code":0,"msg":"验证码错误"}`
4. 验证通过后：`location.reload()` 重新加载搜索结果
5. **关键**：验证码基于 PHPSESSID session，通过后后续搜索不再需要验证码

**Legado 中的解决方案**：

| 方案 | 实现方式 | 优缺点 |
|------|----------|--------|
| **loginUrl 组合验证** | loginUrl 提示用户同时过CF盾+搜索验证码 | ✅ 一次操作解决两个验证 |
| **Cookie传递** | enabledCookieJar:true + PHPSESSID自动保存 | ✅ 后续搜索自动携带验证状态 |
| **分类浏览替代** | sortUrl 分类浏览无需验证码 | ✅ 不需要搜索也能用 |

**loginUrl 组合验证写法**：
```
loginUrl: @js:java.startBrowserAwait(source.sourceUrl,'1.通过Cloudflare验证 2.点击分类后搜索 3.输入搜索验证码后关闭');
searchUrl: https://xxx/index.php?m=vod-search,{"method":"POST","body":"wd={{key}}&submit=search"}
enabledCookieJar: true
```

**关键要点**：
- loginUrl 的浏览器中，用户需要**先过CF盾，再过搜索验证码**
- 两步验证通过后，`cf_clearance` + `PHPSESSID` Cookie 都被保存
- 后续搜索请求自动携带这两个Cookie，不再需要验证
- **不要用 loginCheckJs** 检测验证码状态，会导致无限循环
