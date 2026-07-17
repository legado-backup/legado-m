# Tasks: SSL 握手失败根因排查

> 本 spec 为纯调查任务，绝大多数 task 为只读分析，不修改源码。

## 1. 源码勘察

- [x] 1.1 读取 `app/build.gradle` 依赖列表，定位 okhttp / cronet / webkit
- [x] 1.2 读取 `gradle/libs.versions.toml`，确认全部版本号
- [x] 1.3 读取 `app/src/main/java/io/legado/app/help/http/SSLHelper.kt`
- [x] 1.4 读取 `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
- [x] 1.5 读取 `app/src/main/java/io/legado/app/help/http/Cronet.kt`
- [x] 1.6 读取 `app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt`
- [x] 1.7 读取 `app/src/main/java/io/legado/app/lib/cronet/CronetLoader.kt`
- [x] 1.8 读取 `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`
- [x] 1.9 读取 `app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt`（前序会话已读）

## 2. 升级历史审计

- [x] 2.1 `git log --all -p -S "okhttp = " -- gradle/libs.versions.toml`
- [x] 2.2 列出全部 OkHttp 升级提交：4.12.0→5.1.0→5.2.1→5.3.2→5.4.0
- [x] 2.3 `git show 577b3bee -- HttpHelper.kt`（4.x→5.x 关键升级）
- [x] 2.4 `git show 82ca7602 -- DecompressInterceptor.kt OkHttpUtils.kt`（最近升级）
- [x] 2.5 确认所有升级 commit 中无 `ConnectionSpec` / `sslSocketFactory` / `hostnameVerifier` / `SSLContext` 字样 diff

## 3. WebView 链路审计

- [x] 3.1 确认 `WebViewLoginFragment.loadUrl()` 调用 `android.webkit.WebView.loadUrl`
- [x] 3.2 确认 WebView 不经过 `okHttpClient`
- [x] 3.3 确认 `CronetInterceptor` 仅实现 `okhttp3.Interceptor`，对 WebView 无作用
- [x] 3.4 印证 logcat `ssl_client_socket_impl.cc` 来自 chromium net 栈

## 4. 结论与文档

- [x] 4.1 生成 `README.md`（背景+结论摘要+导航）
- [x] 4.2 生成 `spec.md`（需求+范围+验收+证据链+Alternatives+Drawbacks）
- [x] 4.3 生成 `design.md`（ADR Y-Statement）
- [x] 4.4 生成 `tasks.md`（本文件）
- [x] 4.5 更新 `docs/INDEX.md` 添加新 spec 条目
- [x] 4.6 检查点1：向用户汇报设计文档请其审查（用户拒绝要求深挖，已完成深挖补充）

## 5. 后续可选改进（不在本次实施范围）

- [ ] 5.1 在 `WebViewLoginFragment.onReceivedSslError` 添加诊断日志（区分证书/协议错误）
- [ ] 5.2 在 README 中添加"已知限制：CF 站点 + 老版 WebView 可能 SNI 阻断"
- [ ] 5.3 文档化"OkHttp 升级不影响 WebView SSL"避免后续误排查

## 6. 深挖阶段补充任务（用户拒绝认可后）

- [x] 6.1 创建 PC 端 TLS 诊断脚本 `ai_tests/scripts/diag_ssl_pc.py`
- [x] 6.2 实验 A：PC Python ssl 测试站点 TLS 握手（TLSv1.3+1.2 均 OK）
- [x] 6.3 创建模拟器 SSL 诊断脚本 `ai_tests/scripts/diag_ssl_emulator.py`
- [x] 6.4 实验 C：模拟器 WebView 启动 + logcat 抓取（chromium SSL_ERROR_SSL+ERR_CONNECTION_RESET）
- [x] 6.5 读取 `App.kt`，审查 `installGmsTlsProvider` 方法
- [x] 6.6 排除 installGmsTlsProvider 影响（仅影响 OkHttp JCE，不影响 WebView BoringSSL）
- [x] 6.7 补充 spec.md/design.md 实验证据
- [x] 6.8 综合证据矩阵：6 个假设 5 个排除，2 个根因支持

## 7. 验收清单（更新）

- [x] AC1 明确回答"是否升级导致" → 不是，源码证据链完整
- [x] AC2 OkHttp 升级提交清单完整 → 覆盖 4.12.0→5.4.0 全路径
- [x] AC3 SSL 配置变更历史清晰 → git diff 可追溯
- [x] AC4 WebView 链路审计完整 → 不走 OkHttp
- [x] AC5 真正根因有合理推断 → 网络/WebView 版本/CDN 配置
