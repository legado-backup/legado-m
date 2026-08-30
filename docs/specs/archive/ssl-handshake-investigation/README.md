# SSL 握手失败根因排查（net_error -101 ERR_CONNECTION_RESET）

## 背景与触发

在订阅源登录链路真机测试中，`WebViewLoginFragment` 加载 `loginUrl` 时 logcat 出现：

```
chromium: [ERROR:ssl_client_socket_impl.cc(996)] handshake failed; returned -1, SSL error code 1, net_error -101
```

- net_error -101 = ERR_CONNECTION_RESET（对端在 TLS 握手期间发送 RST）
- 站点 IP 层可达（CF 边缘 IP，ping 延迟 181~242ms），排除 DNS 问题
- 模拟器 WebView 版本：Chrome 68.0.3440.70（2018 年版本，较老）

## 用户诉求

> /openspec 针对上面 ssl 握手失败的原因,深入排查源码，是不是升级导致的！！！！mdb

核心问题：**SSL 握手失败是否由依赖升级导致？**

## 调查结论摘要

| 维度 | 结论 | 证据 |
|------|------|------|
| OkHttp 升级 | **不是根因** | HttpHelper.kt 的 SSL 配置自 4.12.0→5.4.0 全程未变；WebView 不走 OkHttp |
| SSLHelper.kt | **未变更** | `SSLContext.getInstance("TLS")` 自初始 commit 起未改 |
| WebView 网络栈 | **不走 OkHttp/Cronet** | WebViewLoginFragment.loadUrl 直接调 `WebView.loadUrl`，由系统 WebView 自带网络栈处理 |
| **源站问题** | **已排除**（控制变量实验A） | PC 端 Python ssl 测试 TLSv1.3+TLSv1.2 均 OK，cipher 正常 |
| **installGmsTlsProvider** | **已排除**（App.kt 审查） | 该方法仅为 OkHttp 启用 TLS 1.3（API<29），不影响 WebView BoringSSL |
| 真正可疑点 | 系统 WebView + 网络环境 | Chrome 68 启动 2 秒即 SSL_ERROR_SSL+ERR_CONNECTION_RESET，符合 SNI 阻断特征 |

## 文档导航

- 需求/范围/验收标准：[spec.md](./spec.md)
- 设计决策（ADR Y-Statement）：[design.md](./design.md)
- 实施任务清单：[tasks.md](./tasks.md)

## 后续行动建议

1. **不修改源码**：本次排查结论是"非源码问题"，无需修改 OkHttp/SSLHelper
2. **可选改进方向**（不强制）：
   - 提示用户升级系统 WebView（如安装 Chrome/Lollipop 以上 WebView Provider）
   - 增加 SSL 握手失败的诊断日志（区分协议错误 vs 网络阻断）
   - 文档化"CF 站点 + 老版 WebView 可能被 SNI 阻断"已知限制
