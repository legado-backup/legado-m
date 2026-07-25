# CF 绕过源码分析

## 概述
Cloudflare 绕过方案基于 Legado 源码深度分析，确认 webView() 可自动通过 CF JS Challenge。

## 关键源码位置

### 1. JsExtensions.webView()
- 文件：`app/src/main/java/io/legado/app/help/JsExtensions.kt`
- 行号：L203-229
- 功能：在后台 WebView 中加载 URL，自动执行 JS，返回渲染后 HTML（String?）
- 关键行为：同步阻塞，在 IO 线程执行

### 2. BackstageWebView Cookie 同步
- 文件：`app/src/main/java/io/legado/app/web/BackstageWebView.kt`
- 行号：L183-189
- 功能：onPageFinished 中从 WebView CookieManager 读取 Cookie，写入 OkHttp CookieStore
- 关键行为：自动同步，无需手动操作

### 3. CookieStore
- 文件：`app/src/main/java/io/legado/app/help/http/CookieStore.kt`
- 功能：OkHttp 的 Cookie 持久化存储
- 关键行为：后续 OkHttp 请求自动从 CookieStore 读取 Cookie

### 4. loginCheckJs 执行
- 文件：`app/src/main/java/io/legado/app/model/rss/Rss.kt`
- 行号：L53-77
- 功能：每次请求前执行 loginCheckJs
- 关键约束：必须返回 StrResponse 对象

### 5. loginUrl 执行
- 文件：`app/src/main/java/io/legado/app/ui/dialog/SourceLoginDialog.kt`
- 功能：用户点击"登录"时执行 loginUrl
- 关键约束：不会自动执行，需用户手动触发

## CF 验证类型与绕过策略

| CF 验证类型 | 自动绕过 | 方案 | 源码依据 |
|------------|---------|------|---------|
| JS Challenge | ✅ | webView() 自动通过 | JsExtensions.webView + BackstageWebView Cookie同步 |
| Turnstile | ❌ | startBrowserAwait() 手动通过 | Turnstile检测自动化工具 |
| Interactive | ❌ | startBrowserAwait() 手动通过 | 需人工识别验证码 |
