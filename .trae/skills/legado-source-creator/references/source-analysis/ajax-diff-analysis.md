# MockJsExtensions ajax() 差异分析文档

> 基于 Legado 源码 AnalyzeUrl.kt / HttpHelper.kt / CookieManager.kt / OkHttpUtils.kt 深度分析
> 分析日期：2026-06-12

## 1. ajax() 完整调用链

```
JsExtensions.ajax(url)
  └→ new AnalyzeUrl(urlStr, source=getSource(), callTimeout, coroutineContext)
       └→ initUrl()                        // URL模板解析三步曲
            ├→ analyzeJs()                  // 执行 @js: / <js></js>
            ├→ replaceKeyPageJs()           // 替换 {{page}}, @get:{}, <page1,page2>
            └→ analyzeUrl()                 // 解析 ,{...} 配置块
       └→ getStrResponse()
            └→ runBlocking { getStrResponseAwait() }
                 └→ ConcurrentRateLimiter.withLimit { executeStrRequest() }
                      ├→ setCookie()        // Cookie注入
                      ├→ [WebView路径] BackstageWebView.getStrResponse()
                      └→ [OkHttp路径]  getClient().newCallStrResponse()
```

## 2. 行为差异汇总

### 2.1 请求前处理（高影响差异）

| # | 行为 | Legado ajax() | MockJsExtensions ajax() | 差异影响 | 可信度影响 |
|---|------|--------------|------------------------|---------|-----------|
| 1 | Cookie自动注入 | 三层Cookie合并+CookieJar持久化 | OkHttp默认不携带 | **高**——登录后请求可能失败 | 中→低 |
| 2 | Header自动注入 | source.header+登录Header+UA+Keep-Alive | 不携带 | **高**——需要Header的请求可能失败 | 中→低 |
| 3 | URL模板解析 | 三阶段（JS→模板→配置块） | 不支持（调用方已替换） | 低——调用方已处理 | 无影响 |
| 4 | 相对URL转绝对 | 自动 | 不支持（调用方需传绝对URL） | 低 | 无影响 |
| 5 | 并发限流 | ConcurrentRateLimiter | 无 | 低——仿真环境单线程 | 无影响 |
| 6 | 代理配置 | header中proxy键自动提取 | 不支持 | 低——非典型场景 | 无影响 |
| 7 | DNS自定义 | dnsIp配置+Cronet联动 | 不支持 | 低——非典型场景 | 无影响 |

### 2.2 请求构建（中影响差异）

| # | 行为 | Legado ajax() | MockJsExtensions ajax() | 差异影响 | 可信度影响 |
|---|------|--------------|------------------------|---------|-----------|
| 8 | Body类型判断 | 自动判断JSON/XML/Form | 需调用方指定 | 中——调用方需正确指定 | 无影响 |
| 9 | Form编码 | 按charset编码+已编码检测 | OkHttp默认UTF-8 | 中——GBK站可能失败 | 无影响 |
| 10 | 重试 | retry配置自动重试 | 不支持 | 低——可手动重试 | 无影响 |
| 11 | SSL | 自动信任所有证书 | 需手动配置 | 低——大多数站不需要 | 无影响 |

### 2.3 请求执行（高影响差异）

| # | 行为 | Legado ajax() | MockJsExtensions ajax() | 差异影响 | 可信度影响 |
|---|------|--------------|------------------------|---------|-----------|
| 12 | WebView路径 | 支持（JS渲染/资源嗅探） | 抛UnsupportedOperationException | **高**——需WebView的站不可验证 | 不可验证 |
| 13 | Cronet | 可选启用 | 不支持 | 低——OkHttp足够 | 无影响 |

### 2.4 响应处理（中影响差异）

| # | 行为 | Legado ajax() | MockJsExtensions ajax() | 差异影响 | 可信度影响 |
|---|------|--------------|------------------------|---------|-----------|
| 14 | 编码检测 | 三级（指定>HTTP头>内容自动检测） | OkHttp默认UTF-8 | 中——GBK站可能乱码 | 无影响 |
| 15 | BOM处理 | 自动移除UTF-8 BOM | 无 | 低——少数站有BOM | 无影响 |
| 16 | bodyJs | 响应后JS二次处理 | 不支持 | 低——非典型场景 | 无影响 |
| 17 | Cookie保存 | 自动持久化到Room数据库 | 不保存 | 中——后续请求无Cookie | 中→低 |
| 18 | 重定向URL | StrResponse.url()自动获取最终URL | 需手动从Response获取 | 低 | 无影响 |

## 3. 可信度标注规则

基于以上差异分析，定义可信度标注规则：

| 规则特征 | 可信度 | 理由 |
|---------|--------|------|
| 不含 java.ajax() 的 JS | **高** | 不依赖网络请求差异 |
| 含 java.ajax() 但不含 Cookie/Header 依赖 | **中** | ajax() 基本行为一致，但编码可能有差异 |
| 含 java.ajax() 且依赖 Cookie/Header | **低** | Cookie/Header 不自动携带，登录后请求可能失败 |
| 含 java.webView() 或 webView:true | **不可验证** | 无法模拟 WebView 环境 |

## 4. MockJsExtensions 实现策略

### 4.1 ajax() 实现方案

```kotlin
fun ajax(url: String): String {
    // 1. 纯 OkHttp 同步请求
    val client = OkHttpClient.Builder()
        .followRedirects(true)
        .followSslRedirects(true)
        .build()
    val request = Request.Builder().url(url).build()
    val response = client.newCall(request).execute()
    return response.body?.string() ?: ""
}
```

### 4.2 已知限制和应对

| 限制 | 应对方式 |
|------|---------|
| Cookie不自动携带 | 在验证报告中标注可信度"低"，提示用户真机验证 |
| Header不自动携带 | 同上 |
| WebView不可用 | 抛异常，标注可信度"不可验证" |
| GBK编码 | 尝试检测Content-Type中的charset |
| Form编码 | 调用方需指定Content-Type |

### 4.3 未来改进方向（MVP4）

- 实现 CookieManager 模拟（ConcurrentHashMap 替代 Room 数据库）
- 实现 source.header 注入（传入 source 对象）
- 实现 charset 自动检测（参考 OkHttpUtils.text()）
