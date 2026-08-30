# Spec: SSL 握手失败根因排查

## 1. 需求陈述

针对 `WebViewLoginFragment` 加载 `loginUrl` 时出现的 `net_error -101 ERR_CONNECTION_RESET`，从源码层深入排查是否由项目依赖升级（特别是 OkHttp 4.x→5.x）导致，给出明确结论与证据链。

## 2. 范围

### 2.1 In Scope（调查范围）

- 检索 OkHttp 全部升级提交（4.12.0→5.1.0→5.2.1→5.3.2→5.4.0）
- 审计 `HttpHelper.kt`、`SSLHelper.kt`、`Cronet.kt`、`CronetInterceptor.kt`、`CronetLoader.kt`、`OkHttpUtils.kt` 的 SSL/TLS 配置变更历史
- 审计 `WebViewLoginFragment` 的网络请求链路（确认是否走 OkHttp）
- 审计 `libs.versions.toml` 全部依赖版本与升级时序
- 审计 `Cronet` 拦截器是否影响 WebView（确认仅拦截 OkHttp 请求）

### 2.2 Out of Scope（排除范围）

- 修复 SSL 握手失败问题本身（属于运行时环境/网络/GFW 问题，非源码问题）
- 修改任何源码文件（本次为纯调查任务）
- 替换系统 WebView 实现
- 调查书源业务数据

## 3. 验收标准

| # | 验收项 | 检查方法 |
|---|--------|---------|
| AC1 | 明确回答"是否升级导致" | 结论有源码证据链支撑 |
| AC2 | OkHttp 升级提交清单完整 | 覆盖 4.12.0→5.4.0 全路径 |
| AC3 | SSL 配置变更历史清晰 | HttpHelper/SSLHelper 的 git diff 可追溯 |
| AC4 | WebView 链路审计完整 | WebViewLoginFragment 调用链明确不走 OkHttp |
| AC5 | 真正根因有合理推断 | 给出"非升级导致"的替代解释 |

## 4. 调查证据链

### 4.1 OkHttp 升级时序（git log 全量证据）

| 提交 | 日期 | OkHttp 变更 | 性质 |
|------|------|-----------|------|
| 577b3bee | 2025-07-14 | 4.12.0 → 5.1.0 | **重大升级 4.x→5.x** |
| af01eb43 | 2025-10-13 | 5.1.0 → 5.2.1 | 小版本 |
| 2d4fabf0 | 2025-12-16 | 5.1.0 → 5.3.2 | 小版本 |
| 82ca7602 | 2026-07-05 | 5.3.2 → 5.4.0 | 最近一次升级 |

### 4.2 SSL/TLS 配置变更审计

#### HttpHelper.kt `okHttpClient` 构建（关键 SSL 段）

```kotlin
val specs = arrayListOf(
    ConnectionSpec.MODERN_TLS,
    ConnectionSpec.COMPATIBLE_TLS,
    ConnectionSpec.CLEARTEXT
)
// ...
.sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
.retryOnConnectionFailure(true)
.hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
.connectionSpecs(specs)
```

**git diff 证据**：
- `577b3bee`（4.x→5.x）对 HttpHelper.kt 的修改：仅 `response.body!!` → `response.body`（可空性适配），**未触碰 SSL 配置**
- `82ca7602`（5.3.2→5.4.0）对 HttpHelper.kt：**无修改**
- 所有 OkHttp 升级 commit 中均无 `ConnectionSpec`/`sslSocketFactory`/`hostnameVerifier` 字样的 diff

#### SSLHelper.kt

```kotlin
val unsafeSSLSocketFactory: SSLSocketFactory by lazy {
    val sslContext = SSLContext.getInstance("TLS")  // 不指定 1.2/1.3
    sslContext.init(null, arrayOf(unsafeTrustManager), SecureRandom())
    sslContext.socketFactory
}
```

**git diff 证据**：SSLHelper.kt 自初始 commit 起未变更 SSL 协议字符串。

#### 5.4.0 升级对内部 API 的实际影响

`82ca7602` 提交中，OkHttp 5.x 移除了部分 `okhttp3.internal.*` 内部 API，项目已做适配：

- `DecompressInterceptor.kt`：`okhttp3.internal.http.promisesBody` 移除 → 本地实现等价方法
- `OkHttpUtils.kt`：`RealResponseBody(null, -1, source)` 移除 → `source.asResponseBody(null, -1)`

**这些适配均不涉及 SSL 配置。**

### 4.3 WebView 登录链路审计（关键证据）

`WebViewLoginFragment.loadUrl()`：

```kotlin
private fun loadUrl(source: BaseSource) {
    val loginUrl = source.loginUrl ?: return
    val absoluteUrl = NetworkUtils.getAbsoluteURL(source.getKey(), loginUrl)
    currentWebView?.loadUrl(absoluteUrl, viewModel.headerMap)  // 直接调 WebView
}
```

- 调用的是 `android.webkit.WebView.loadUrl`，由系统 WebView 自带网络栈处理
- 不经过 `okHttpClient`、不经过 `Cronet.interceptor`、不经过 `DecompressInterceptor`
- SSL 握手由系统 WebView 内部的 chromium 网络栈（BoringSSL）完成
- logcat 中 `ssl_client_socket_impl.cc` 来自 chromium，印证此点

### 4.4 Cronet 拦截器范围审计

`CronetInterceptor` 实现 `okhttp3.Interceptor`，仅能拦截 OkHttp 链路：

```kotlin
class CronetInterceptor(...) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response { ... }
}
```

- `Cronet.interceptor` 通过 `builder.addInterceptor(it)` 加入 OkHttp
- **不会拦截 WebView 的请求**
- WebView 的 QUIC/HTTP3 由系统 WebView 自身处理

### 4.5 真正根因推断（非升级导致）

| 可疑根因 | 支持证据 | 反证/不确定性 |
|---------|---------|--------------|
| GFW 对 SNI 的 TLS 阻断 | IP 可达但 TLS 握手被 RST，典型 SNI 阻断特征 | 无法直接验证，需对比代理后表现 |
| 系统 WebView 版本过老 | Chrome 68（2018）不支持部分新 TLS 组合或证书套件 | 新设备 WebView 升级后是否可解 |
| 站点 CDN 配置变更 | 站点使用 CF，CF 可能调整 TLS 最低版本 | 项目无法干预 |

### 4.6 控制变量实验证据（深挖阶段，用户拒绝认可后补充）

用户质疑"确定是源站问题么"后，启动控制变量实验：

#### 实验 A：PC 端 Python ssl 模块测试（同站点，不同客户端栈）

脚本：`ai_tests/scripts/diag_ssl_pc.py`

| TLS 版本 | 握手结果 | cipher | issuer CN |
|---------|---------|--------|-----------|
| 默认（系统选） | OK | TLS_AES_256_GCM_SHA384 | (隐藏) |
| 强制 TLS 1.2 | OK | ECDHE-ECDSA-AES128-GCM-SHA256 | (隐藏) |
| 强制 TLS 1.3 | OK | TLS_AES_256_GCM_SHA384 | (隐藏) |

**结论**：PC 端能成功握手，**源站 TLS 配置完全正常**，支持 TLS 1.2 + 1.3。

#### 实验 C：模拟器 WebView 启动 + logcat 抓取（同设备，WebView 栈）

脚本：`ai_tests/scripts/diag_ssl_emulator.py`

操作：清空 logcat → ADB 启动 `SourceLoginActivity` → 等待 10 秒 → 抓取 logcat 过滤 SSL/chromium 关键字

**logcat 关键行**（脱敏后）：

```
22:34:09.835 D CronetLoader: soName+:libcronet.149.0.7827.201.so
22:34:09.835 D CronetLoader: soUrl:[URL]
22:34:09.881 I Legado: at io.legado.app.App.installGmsTlsProvider(App.kt:179)
22:34:09.881 E AppLog: at io.legado.app.App.installGmsTlsProvider(App.kt:179)
22:34:11.787 E chromium: [ERROR:ssl_client_socket_impl.cc(996)] handshake failed; returned -1, SSL error code 1, net_error -101
```

**关键发现**：
- 启动后约 2 秒（22:34:09 → 22:34:11.787）即 SSL 握手失败
- SSL error code 1 = `SSL_ERROR_SSL`（致命 SSL 错误）
- net_error -101 = `ERR_CONNECTION_RESET`（对端发送 RST）
- chromium 报错，不是 OkHttp 报错，**印证 WebView 用 chromium 网络栈**

#### 4.7 App.kt installGmsTlsProvider 审查（排除另一嫌疑）

logcat 中 `App.kt:179 installGmsTlsProvider` 的 ERROR 日志是审查的另一嫌疑点：

```kotlin
private fun installGmsTlsProvider(context: Context) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) return  // API 29+ 不执行
    try {
        val gmsPackageName = "com.google.android.gms"
        val appInfo = packageManager.getApplicationInfo(gmsPackageName, 0)  // line 179
        ...
        gms.classLoader.loadClass("com.google.android.gms.common.security.ProviderInstallerImpl")
            .getMethod("insertProvider", Context::class.java).invoke(null, gms)
    } catch (e: Exception) {
        AppLog.put("App: init", e)  // ← ERROR 日志来源
    }
}
```

注释明确说明：**此方法仅为 OkHttp 启用 TLS 1.3**（API<29 时）。

- 此方法只影响 OkHttp 的 JCE Provider，不影响 WebView 的 BoringSSL
- MEmu 模拟器无 GMS，`getApplicationInfo` 抛 `NameNotFoundException` → 被 catch → 记录 ERROR
- 这是预期异常，**与 WebView SSL 握手失败无因果关系**

#### 4.8 综合证据矩阵

| 假设 | 实验 | 结论 |
|------|------|------|
| 源站 TLS 配置异常 | A：PC Python ssl 测试 | **排除**（PC TLSv1.3+1.2 均 OK） |
| OkHttp 升级误改 SSL | git diff 审计 | **排除**（HttpHelper/SSLHelper 全程未变） |
| OkHttp 升级间接影响 WebView | 源码链路审计 | **排除**（WebView 不走 OkHttp） |
| Cronet 拦截器影响 WebView | CronetInterceptor 实现 | **排除**（仅实现 okhttp3.Interceptor） |
| installGmsTlsProvider 影响 WebView | App.kt:173-194 审查 | **排除**（只影响 OkHttp JCE，不影响 WebView BoringSSL） |
| 模拟器 WebView 版本过老 | logcat 实测 | **支持**（Chrome 68，启动 2 秒即 SSL_ERROR_SSL+RST） |
| GFW SNI 阻断 | logcat + PC对照 | **支持**（PC 可访问但模拟器不能，符合 SNI/JA3 阻断特征） |

## 5. Alternatives Considered（备选方案）

### Alt-1：升级 OkHttp 到更新版本以解决 SSL 问题

- **为何考虑**：OkHttp 5.x 默认 `MODERN_TLS` 可能更严格
- **为何拒绝**：
  1. WebView 不走 OkHttp，升级 OkHttp 对 WebView SSL 无影响
  2. 站点 SSL 配置若要求 TLS 1.3，问题应在 WebView 端，与 OkHttp 无关
  3. 已确认 HttpHelper.kt 的 SSL 配置未变更，不存在升级"误改"问题
- **结论**：拒绝

### Alt-2：在 WebView 中注入自定义 SSL 配置

- **为何考虑**：让 WebView 走 OkHttp 网络栈
- **为何拒绝**：
  1. 系统 WebView 不允许替换底层网络栈
  2. 改造为 OkHttp 抓取后渲染会破坏登录页 JS 交互（Cookie/重定向/JS 验证）
  3. 改动巨大且收益不明确
- **结论**：拒绝

### Alt-3：增加诊断日志区分根因

- **为何考虑**：当前无法区分"网络阻断"还是"协议不兼容"
- **为何拒绝（本次范围内）**：
  1. 超出"排查是否升级导致"的诉求
  2. 改源码属于另一个独立 spec
- **结论**：列为后续可选改进，本次不实施

## 6. Drawbacks（本次调查的局限）

1. **无法直接验证 GFW 阻断假设**：项目内无代理对照测试环境
2. **Chrome 68 WebView 与新 TLS 兼容性矩阵未实测**：需多版本 WebView 真机对照
3. **Cronet 是否在 WebView 路径有间接影响未深入审计**：理论无影响，但未做 cronet_source 链路追踪
4. **本次只排查"升级导致"，未覆盖"运行时配置导致"**：如 `AppConfig.isCronet` 在 WebView 路径上的副作用

## 7. 决策

**不修改任何源码**。本次调查结论：

- OkHttp 4.x→5.x 升级未修改 SSL/TLS 配置
- WebView 登录场景不走 OkHttp，OkHttp 升级与本次 SSL 握手失败无因果关系
- 真正根因需在网络层/系统 WebView 版本层进一步排查，与项目源码无关
