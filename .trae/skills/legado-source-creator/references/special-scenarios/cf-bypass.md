# Cloudflare 绕过方案

## 概述
Cloudflare 是最常见的网站防护服务，Legado 订阅源/书源经常遇到 CF 保护。本文档基于 Legado 源码深度分析，提供三种 CF 验证类型的绕过方案。

## CF 验证类型与绕过策略

### 1. JS Challenge（5秒盾）
- 特征：页面显示 "Just a moment..."，自动执行JS后跳转
- 自动绕过：✅ `java.webView()` 可自动通过
- 原理：WebView是真实浏览器引擎，执行CF JS→设置cf_clearance Cookie→onPageFinished自动同步到CookieStore
- 源码依据：JsExtensions.kt L203-229（webView方法）+ BackstageWebView.kt L183-189（Cookie同步）

### 2. Managed Challenge (Turnstile)
- 特征：需要用户交互（点击/滑块）
- 自动绕过：❌ 无法自动通过
- 降级方案：`java.startBrowserAwait()` 弹浏览器让用户手动通过
- 原因：Turnstile检测自动化工具，需要真实用户交互

### 3. Interactive Challenge
- 特征：需要输入验证码
- 自动绕过：❌ 无法自动通过
- 降级方案：`java.startBrowserAwait()` 弹浏览器让用户手动通过

## 为什么纯Rhino JS无法破除CF盾

1. CF验证JS高度混淆且动态变化，无法在Rhino中模拟
2. CF验证JS依赖浏览器环境（DOM、BOM、Canvas、WebGL等），Rhino不具备这些API
3. CF验证JS可能检测浏览器指纹（navigator、screen、canvas hash等），Rhino环境无法伪造
4. 即使能模拟JS计算，也无法设置Cookie到OkHttp的CookieStore（Rhino没有Cookie操作API）

## 推荐源配置

### CF JS Challenge 网站配置

> ⚠️ **重要修正**（2026-07-17）：原推荐 `loginUrl: "@js:java.webView(null, source.sourceUrl, null, false);"` 已被源码验证为**错误**——[WebViewLoginFragment.loadUrl()](../../../../../app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt) 直接把 loginUrl 当 URL 加载，**不识别 `@js:` 形式**。`@js:` 形式仅在 SourceLoginDialog 中有效（且需 `loginUi` 非空才走该分支，详见陷阱#54）。

#### 正确配置（loginUrl 设为普通 URL）

```json
{
    "loginUrl": "https://example.com/",
    "loginCheckJs": "var s=result.body()+'';if(s.indexOf('Just a moment')!=-1 || s.indexOf('cf_chl_opt')!=-1){'CF_BLOCKED';}else{result;}"
}
```

> **字段说明**：
> - `loginUrl`：必须是**普通 URL 形式**（首页 URL），不可用 `@js:java.webView(...)` 形式
> - `loginCheckJs`：检测到 CF 时返回字符串 `'CF_BLOCKED'`（不直接弹浏览器，避免无限循环陷阱#57）；用户需手动点击"登录"按钮触发 WebView

#### 源码依据

| 字段 | 实际执行位置 | 源码路径 |
|------|------------|---------|
| `loginUrl` | `WebViewLoginFragment.loadUrl()` 直接加载 URL | [app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt](../../../../../app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt) |
| `loginCheckJs` | `AnalyzeUrl.evalJS()` 中执行 | app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt |
| Cookie 同步 | `BackstageWebView.onPageFinished()` 中 CookieManager → CookieStore | app/src/main/java/io/legado/app/help/http/BackstageWebView.kt |

### 执行流程（正确版）

1. 用户首次打开源 → 请求被 CF 拦截 → loginCheckJs 检测到 CF → 返回 `'CF_BLOCKED'` 标识
2. 用户在 SourceLoginDialog 中点击"登录"按钮 → 启动 SourceLoginActivity → WebViewLoginFragment.loadUrl(loginUrl) 加载首页 URL
3. WebView 是真实浏览器引擎 → 自动执行 CF JS Challenge → 通过后 cf_clearance Cookie 写入 CookieManager
4. `onPageFinished` 回调自动将 CookieManager 中的 Cookie 同步到 OkHttp 的 CookieStore
5. 用户关闭登录界面 → 后续请求自动携带 cf_clearance Cookie → 正常加载
6. cf_clearance Cookie 有效期内（数小时到数天）无需再次验证

## Cookie 双向共享机制

| 方向 | 机制 | 触发时机 |
|------|------|---------|
| WebView → OkHttp | CookieManager → CookieStore | onPageFinished 自动同步 |
| OkHttp → WebView | CookieStore → applyToWebView() | 需主动调用 |

源码依据：
- BackstageWebView.kt L183-189: onPageFinished中从CookieManager读取Cookie写入CookieStore
- CookieStore.kt: OkHttp的Cookie持久化存储

## 关键陷阱

### 1. loginUrl不会自动执行
- loginUrl只在SourceLoginDialog中用户点击"登录"时执行
- 不会在打开源时自动触发
- 用户首次使用需手动点击"登录"按钮

### 2. loginCheckJs必须返回StrResponse
- loginCheckJs的返回值被Rss.kt直接使用
- 必须返回result（StrResponse对象），不能返回String
- 末尾必须加 `result;` 或 `;result;`

### 3. webView()是同步阻塞操作
- 执行时间约5-10秒（CF JS Challenge耗时）
- 在IO线程执行不会ANR
- 不适合放在每次请求都执行的loginCheckJs中

### 4. CF Cookie过期
- cf_clearance Cookie有效期通常数小时到数周
- Cookie过期后loginCheckJs会再次检测到CF
- 用户需再次点击"登录"按钮触发 SourceLoginActivity 重新加载首页 URL

## 检测CF的方法

> ⚠️ **重要修正**（2026-07-17）：原推荐在 loginCheckJs 中直接调用 `java.startBrowserAwait()` 会导致**无限循环**（陷阱#57：loginCheckJs 每次请求都执行 → 弹浏览器 → 用户通过 → 下次请求又检测 → 再弹）。正确做法是 loginCheckJs 只返回标识字符串，由用户手动触发登录。

```javascript
// loginCheckJs 中检测 CF（正确版，避免无限循环）
var s = result.body() + '';
if (s.indexOf('Just a moment') != -1
    || s.indexOf('cf_chl_opt') != -1
    || s.indexOf('_cf_chl_rt_tk') != -1
    || s.indexOf('challenge-platform') != -1
    || s.indexOf('Checking your browser') != -1) {
    // CF Challenge 检测到，返回标识字符串
    // 用户需手动点击"登录"按钮触发 WebView 加载首页 URL
    'CF_BLOCKED';
} else {
    // 正常内容，返回 result（StrResponse 对象）
    result;
}
```

> **关键陷阱#57**：禁止在 loginCheckJs 中调用 `java.startBrowserAwait()`！loginCheckJs 每次请求都执行，弹浏览器后用户通过 CF → 下次请求又检测到 CF → 再弹浏览器 → 无限循环。CF 站应只检测并返回标识，由用户手动触发登录。

CF特征关键词：
- "Just a moment" — CF JS Challenge 标题
- "cf_chl_opt" — CF Challenge 选项变量
- "_cf_chl_rt_tk" — CF Challenge Token 参数
- "challenge-platform" — CF Challenge 脚本标识
- "Checking your browser" — CF 检测文案
