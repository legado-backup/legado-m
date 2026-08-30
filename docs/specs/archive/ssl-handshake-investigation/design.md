# Design: SSL 握手失败根因排查（ADR Y-Statement）

## ADR: OkHttp 升级是否为 SSL 握手失败根因

### Context（上下文）

在订阅源登录真机测试中，`WebViewLoginFragment` 通过 `WebView.loadUrl()` 加载 `loginUrl` 时，chromium 网络栈报：

```
ssl_client_socket_impl.cc(996)] handshake failed; returned -1, SSL error code 1, net_error -101
```

用户要求从源码层核实：是否项目近期依赖升级（特别是 OkHttp 4.x→5.x）导致。

### Decision（决策）

**结论：OkHttp 升级不是根因，且本次不修改任何源码。**

依据四条源码证据链：

1. **SSL 配置全程未变**：HttpHelper.kt 自初始 commit 起使用 `MODERN_TLS + COMPATIBLE_TLS + CLEARTEXT`，所有 OkHttp 升级 commit 中均未修改此配置。
2. **SSLHelper.kt 未变更**：`SSLContext.getInstance("TLS")` 协议字符串未改。
3. **WebView 不走 OkHttp**：`WebViewLoginFragment.loadUrl()` 直接调用 `android.webkit.WebView.loadUrl()`，由系统 WebView 内部 chromium 网络栈（BoringSSL）完成 TLS 握手，logcat 中 `ssl_client_socket_impl.cc` 来自 chromium 印证此点。
4. **Cronet 仅拦截 OkHttp 链路**：`CronetInterceptor` 实现 `okhttp3.Interceptor`，通过 `addInterceptor` 注入 OkHttp，不影响 WebView。

### Consequences（后果）

#### 正面后果

- 避免误改 OkHttp/SSLHelper 引入新回归
- 明确调查边界，节省后续绕弯路
- 为"运行时网络问题"的进一步排查腾出方向

#### 负面后果

- 用户原本怀疑"升级导致"的假设被推翻，需重新解释真正根因
- 真正根因（GFW SNI 阻断 / 系统 WebView 过老 / 站点 CDN 配置）超出代码层处理范围

### Alternatives（备选方案）

参见 [spec.md §5 Alternatives Considered](./spec.md)，三个备选（升级 OkHttp / 注入自定义 SSL / 增加诊断日志）均被拒绝。

### Risks（风险）

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 调查遗漏其他升级的副作用 | 低 | 中 | 已审计 libs.versions.toml 全量升级时序 |
| WebView 在某些路径上间接走 OkHttp | 低 | 中 | 已审计 WebViewLoginFragment + CronetInterceptor，未发现此类链路 |
| Cronet 对 WebView 的潜在副作用未审计到 | 低 | 低 | 理论上不可能（Interceptor 仅作用于 OkHttp），可作后续验证 |

### Y-Statement 摘要

> 在 SSL 握手失败的排查场景下，我们选择"不修改源码"作为决策，因为它在保持稳定性与明确责任边界的同时，避免了误改带来的回归风险；我们接受用户假设被推翻的代价，换取更准确的根因定位方向（运行时网络层而非代码层）。

## 调查证据深度索引

### A. OkHttp 升级时序与 SSL 配置变更矩阵

| Commit | 日期 | OkHttp 变更 | HttpHelper.kt SSL 段变更 | SSLHelper.kt 变更 |
|--------|------|------------|----------------------|-------------------|
| 4c3935cf5 | 2026-06-28 | 5.3.2（初始） | — | — |
| 577b3bee | 2025-07-14 | 4.12.0→5.1.0 | 无（仅 `body!!`→`body`） | 无 |
| af01eb43 | 2025-10-13 | 5.1.0→5.2.1 | 无 | 无 |
| 2d4fabf0 | 2025-12-16 | 5.1.0→5.3.2 | 无 | 无 |
| 82ca7602 | 2026-07-05 | 5.3.2→5.4.0 | 无 | 无 |

### B. WebView 链路证据

`WebViewLoginFragment.loadUrl()`：

```kotlin
private fun loadUrl(source: BaseSource) {
    val loginUrl = source.loginUrl ?: return
    val absoluteUrl = NetworkUtils.getAbsoluteURL(source.getKey(), loginUrl)
    currentWebView?.loadUrl(absoluteUrl, viewModel.headerMap)
}
```

- 不调用 `okHttpClient`
- 不调用 `Cronet.interceptor`
- 直接进入系统 WebView 网络栈

### C. Cronet 拦截器注入位置

`HttpHelper.kt`：

```kotlin
if (AppConfig.isCronet) {
    if (Cronet.loader?.install() == true) {
        Cronet.interceptor?.let {
            builder.addInterceptor(it)  // 仅作用于 OkHttpClient
        }
    }
}
```

`CronetInterceptor` 实现 `okhttp3.Interceptor`，故只对 OkHttp 调用链生效。

### D. logcat 来源印证

`chromium: [ERROR:ssl_client_socket_impl.cc(996)]` 中：

- `chromium` tag = 系统 WebView 内部日志
- `ssl_client_socket_impl.cc` = chromium net 栈的 BoringSSL 实现
- 与 OkHttp 的 `okhttp3.internal.tls.*` 无关

## 进一步排查方向（不在本次范围）

1. 在 `WebViewLoginFragment.onReceivedSslError` 添加日志，区分证书错误 vs 协议错误
2. 对照测试：使用支持 TLS 1.3 的新版 WebView 设备是否复现
3. 通过代理（如本机 SOCKS5）测试是否绕过 SNI 阻断
4. 抓包（Charles/mitmproxy）确认 TLS ClientHello 是否到达服务端

## 补充证据（用户拒绝认可后深挖阶段）

### 实验设计：控制变量法

| 实验 | 控制变量 | 自变量 | 因变量 |
|------|---------|--------|--------|
| A：PC Python ssl | 同站点 | 客户端=PC Python | TLS 握手成功/失败 |
| C：模拟器 WebView | 同站点 | 客户端=模拟器 WebView | TLS 握手成功/失败 |

如果源站有问题 → A 和 C 应该都失败
如果客户端/网络有问题 → A 成功而 C 失败

### 实验 A 结果（[diag_ssl_pc.py](../../ai_tests/scripts/diag_ssl_pc.py)）

| 测试项 | 结果 |
|--------|------|
| 默认 TLS（系统选） | OK，TLSv1.3，TLS_AES_256_GCM_SHA384 |
| 强制 TLS 1.2 | OK，TLSv1.2，ECDHE-ECDSA-AES128-GCM-SHA256 |
| 强制 TLS 1.3 | OK，TLSv1.3，TLS_AES_256_GCM_SHA384 |

**结论**：源站 TLS 配置完全正常，支持 TLS 1.2 + 1.3。

### 实验 C 结果（[diag_ssl_emulator.py](../../ai_tests/scripts/diag_ssl_emulator.py)）

logcat 关键行（脱敏）：

```
T+0.000  CronetLoader: soName+:libcronet.149.0.7827.201.so
T+0.046  Legado: at io.legado.app.App.installGmsTlsProvider(App.kt:179)
T+0.046  AppLog: at io.legado.app.App.installGmsTlsProvider(App.kt:179)  ← ERROR
T+2.906  chromium: [ERROR:ssl_client_socket_impl.cc(996)] handshake failed; returned -1, SSL error code 1, net_error -101
```

**结论**：模拟器 WebView SSL 握手失败，`SSL_ERROR_SSL` + `ERR_CONNECTION_RESET`，启动 2 秒即失败。

### 排除另一嫌疑：installGmsTlsProvider

logcat 中 App.kt:179 ERROR 日志是审查的另一嫌疑点。源码审查：

```kotlin
private fun installGmsTlsProvider(context: Context) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) return  // API 29+ 不执行
    try {
        val gmsPackageName = "com.google.android.gms"
        val appInfo = packageManager.getApplicationInfo(gmsPackageName, 0)  // line 179
        // ... 安装 GMS Conscrypt 作为 JCE Provider
    } catch (e: Exception) {
        AppLog.put("App: init", e)  // ← ERROR 日志来源
    }
}
```

代码注释明确：**此方法仅为 OkHttp 启用 TLS 1.3**。

- 只影响 OkHttp 的 JCE Provider，不影响 WebView 的 BoringSSL
- MEmu 模拟器无 GMS → `NameNotFoundException` → 被 catch → 记录 ERROR
- 这是预期异常，与 WebView SSL 握手失败无因果关系

### 综合证据矩阵（排除式验证）

| 假设 | 实验/审计 | 结论 |
|------|----------|------|
| 源站 TLS 配置异常 | A：PC Python ssl | **排除**（TLSv1.3+1.2 均 OK） |
| OkHttp 升级误改 SSL | git diff 审计 | **排除**（HttpHelper/SSLHelper 全程未变） |
| OkHttp 升级间接影响 WebView | 源码链路审计 | **排除**（WebView 不走 OkHttp） |
| Cronet 拦截器影响 WebView | CronetInterceptor 实现 | **排除**（仅 okhttp3.Interceptor） |
| installGmsTlsProvider 影响 WebView | App.kt:173-194 审查 | **排除**（只影响 OkHttp JCE） |
| 模拟器 WebView 版本过老 | logcat 实测 | **支持**（Chrome 68，2 秒即失败） |
| GFW SNI/JA3 阻断 | logcat + PC 对照 | **支持**（PC 可访问但模拟器不能） |

### 最终决策（更新）

**依然不修改任何源码**。新增控制变量实验证据进一步确认：
- 源站 TLS 正常（PC 实验）
- OkHttp 升级无关（git diff + 链路审计）
- installGmsTlsProvider 无关（App.kt 审查）
- 真正根因在客户端层（WebView 68）或网络环境（SNI 阻断），均不属于项目源码问题
