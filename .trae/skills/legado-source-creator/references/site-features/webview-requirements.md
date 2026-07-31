# WebView 需求模式文档

> 基于 2026-06-20 BackstageWebView/JsExtensionsStub 改造 + 源 JSON 分析提取。

## WebView 需求检测机制

### 架构概览

```
JAR 仿真端                          Python 客户端
┌─────────────────────┐            ┌─────────────────────┐
│ BackstageWebView     │            │ WebViewHandler      │
│  .getStrResponse()   │            │  .render_url()      │
│  → 抛                │            │  .render_html()     │
│  WebViewRequired     │──needsWeb──│  .sniff_resource()  │
│  Exception           │  View=true │  (Selenium/Chrome)  │
│                     │            │                     │
│ JsExtensionsStub     │            │ batch_debug()       │
│  .webView()         │            │  检测 needsWebView   │
│  .webViewGetSource() │            │  → 调用 Handler     │
│  → 抛                │            │  → 渲染后 HTML 回传 │
│  WebViewRequired     │            │  → JAR analyze_rule  │
│  Exception           │            │                     │
│                     │            │                     │
│ startBrowserAwait()  │            │                     │
│  → 抛                │            │                     │
│  UserIntervention    │──needsUser──│                     │
│  Exception           │  =true     │                     │
└─────────────────────┘            └─────────────────────┘
```

## WebView 需求特征

### 1. URL 配置中的 webView 选项

**识别方式**：源 JSON 中 URL 字段包含 `webView:true` 选项

```json
"searchUrl": "https://example.com/search?q={{key}},{\"webView\":true}"
```

**处理方式**：AnalyzeUrl 检测到 `webView:true` → 走 BackstageWebView → 抛 WebViewRequiredException

### 2. JS 调用 webView/webViewGetSource

**识别方式**：ruleContent 中包含 `<js>` 标签且调用 `java.webView()` 或 `java.webViewGetSource()`

```json
"ruleContent": "<js>let videoUrl = java.webViewGetSource(null, baseUrl, null, \".*\\.m3u8.*\");result = videoUrl;</js>"
```

**处理方式**：JsExtensionsStub.webViewGetSource() → 抛 WebViewRequiredException(type="sniff")

### 3. shouldOverrideUrlLoading 配置

**识别方式**：源 JSON 中有 shouldOverrideUrlLoading 字段

```json
"shouldOverrideUrlLoading": "if (url.includes(\"/category/\")) {java.open(\"sort\",...);true}else false"
```

**处理方式**：JsExtensionsStub.webViewGetOverrideUrl() → 抛 WebViewRequiredException(type="overrideUrl")

### 4. ruleContent 包含完整 HTML 模板

**识别方式**：ruleContent 不是简单的选择器，而是完整的 HTML 页面 + JS

```json
"ruleContent": "<!DOCTYPE html><html>...<script>...</script></html>"
```

**处理方式**：需要 WebView 渲染 HTML 模板 → 标记 needsWebView

## WebViewRequest 类型

| type | 说明 | 对应方法 | Selenium 处理 |
|------|------|---------|--------------|
| load | 加载 URL 并执行 JS | render_url() | driver.get(url) + execute_script(js) |
| sniff | 嗅探资源 URL | sniff_resource() | 监听网络请求 + 匹配正则 |
| overrideUrl | URL 重写拦截 | render_url() | 加载页面 + 拦截导航 |
| login | 登录/验证码 | 不处理 | 标记 needsUserIntervention |

## 测试发现

### 本次测试（2026-06-20）

- 20 个源中**未检测到** needsWebView（因为网络连接先失败了）
- 但从源 JSON 分析，以下源有 WebView 需求特征：

| 源名称 | WebView 特征 | 需求类型 |
|--------|-------------|---------|
| 18AV-new | ruleContent 调用 webViewGetSource 嗅探 m3u8 | sniff |
| 秀人集v20 | ruleContent 包含完整 HTML 模板 + JS | load |
| 禁漫天堂 | ruleLink 使用 @js 替换 URL | 可能需 WebView |

### Selenium 可用性

- Selenium 4.45.0 已安装
- Chrome 浏览器需要单独安装
- Chrome 未安装时，needsWebView 的源标记为失败并提示

## 指导建议

### 创建需要 WebView 的源时

1. **URL 配置**：如果页面需要 JS 渲染，在 URL 中添加 `webView:true` 选项
2. **ruleContent**：如果需要嗅探视频地址，使用 `webViewGetSource(null, baseUrl, null, "正则")`
3. **sourceRegex**：嗅探资源时必须提供正则表达式（如 `.*\.m3u8.*`）
4. **测试流程**：先用 OkHttp 测试 → 检测到 needsWebView → 用 Playwright MCP 渲染 → 回传 JAR 解析

### 登录场景处理

1. **loginUrl**：设置登录页面 URL
2. **loginUi**：定义登录界面字段（用户名、密码等）
3. **loginCheckJs**：设置登录验证 JS
4. **enabledCookieJar**：启用 Cookie 保存
5. **测试时**：标记为 needsUserIntervention，建议用户在 Legado App 中手动登录
