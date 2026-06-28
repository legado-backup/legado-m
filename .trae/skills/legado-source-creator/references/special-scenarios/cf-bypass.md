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
```json
{
    "loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);",
    "loginCheckJs": "var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;"
}
```

### 执行流程
1. 用户首次打开源 → 请求被CF拦截 → loginCheckJs检测到CF → 弹出SourceLoginDialog
2. 用户点击"登录" → 执行loginUrl → webView()加载页面 → CF JS Challenge自动通过 → Cookie保存到CookieStore
3. loginCheckJs再次检测 → 不含CF特征 → 返回result → 正常加载
4. 后续请求自动携带cf_clearance Cookie → 无需再次验证

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
- cf_clearance Cookie有效期通常数天到数周
- Cookie过期后loginCheckJs会再次检测到CF
- 用户需再次点击"登录"触发webView()

## 检测CF的方法

```javascript
// loginCheckJs中检测CF
var s = result.body();
if (s.indexOf('Just a moment') != -1) {
    // CF Challenge 检测到
    java.startBrowserAwait(source.sourceUrl, '通过Cloudflare验证');
}
result;
```

CF特征关键词：
- "Just a moment" — CF JS Challenge 标题
- "cf_chl_opt" — CF Challenge 选项变量
- "_cf_chl_rt_tk" — CF Challenge Token 参数
- "challenge-platform" — CF Challenge 脚本标识
- "Checking your browser" — CF 检测文案
