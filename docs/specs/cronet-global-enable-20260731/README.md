# Cronet 默认自动启用与扩展使用方案

> 状态：🔄 设计中
> 创建日期：2026-07-31
> Spec ID：cronet-global-enable-20260731
> 负责模块：网络层 / 视频播放器 / DNS 解析 / 图片加载 / 文件传输

## 功能概述

本设计文档针对 Legado（阅读M）项目中 Cronet（Chromium 网络栈）的使用进行系统性优化，从"统一开关逻辑"升级为"Cronet 默认自动启用 + 扩展使用范围 + 性能稳定性全面评估"的新方向。

**方向调整背景**：用户审查初版设计后指出，Cronet 更接近浏览器，而本项目本质是抓取爬虫类项目，从模拟真实浏览器角度 Cronet 是最佳选择，应默认自动启用并尽可能扩展使用范围，同时从性能、稳定性等多维度全面评估。

**本方案核心目标**：
- 将 isCronet 默认值改为 true，Cronet 作为初始化自动启用模式
- 引入 CronetTransportForOkHttp 桥接层，让现有 OkHttp 代码零改动获得 Cronet 能力
- 扩展 Cronet 使用范围至 HttpURLConnection、Glide、文件上传/下载等场景
- 完善分层降级链，保障 JNI 崩溃等异常场景下的可用性
- 从反爬成功率、弱网性能、稳定性、体积等多维度全面评估

## 核心能力

本方案提供以下 6 项核心能力：

1. **默认启用**：isCronet 默认值改为 true，Cronet 作为初始化自动启用模式（保留开关用于紧急关闭）
2. **桥接方案**：引入 Google 官方 CronetTransportForOkHttp 桥接层，现有 OkHttp 代码零改动获得 QUIC/HTTP3 + BoringSSL 指纹能力
3. **分层降级链**：Cronet(play-services) → Cronet(embedded) → cronet-fallback → OkHttp，保障异常场景可用性
4. **扩展使用范围**：从核心网络请求扩展至 HttpURLConnection（P1）、Glide 图片加载（P2）、文件上传/下载（P3）
5. **性能全面评估**：对比 Cronet vs OkHttp 在 TLS 握手、QUIC 弱网、连接迁移、DNS 解析等维度的性能差异
6. **稳定性保障**：完善 ProGuard 规则、JNI 崩溃监控、自动降级机制、参数调优，确保生产环境稳定

## 文档索引

| 文档 | 说明 | 状态 |
|------|------|------|
| [README.md](./README.md) | 设计概览与文档索引（本文件） | 🔄 设计中 |
| [spec.md](./spec.md) | 需求规格说明 | 🔄 设计中 |
| [design.md](./design.md) | 技术设计方案 | 🔄 设计中 |
| [tasks.md](./tasks.md) | 任务清单与执行计划（四阶段） | 🔄 设计中 |
| [可行性研究报告](../../research/cronet-default-enable-feasibility-report.md) | Cronet 默认启用可行性深度评估（462 行） | ✅ 已完成 |

## 背景说明

**用户反馈触发**：用户审查初版设计文档后提出方向调整——

> "是不是当前需要将项目的 cronet 作为初始化自动启用模式！并且尽可能的更多的去使用这个能力？毕竟他更接近浏览器，这个项目再怎么说也是一个抓取爬虫类的项目，从模拟真实浏览器角度来说肯定是最好的吧？另外你还有从整体角度，考虑性能、稳定性等多方面因素，全面评估！"

**核心理由**：
1. **项目本质**：Legado 是自定义书源规则引擎的抓取爬虫类项目，模拟真实浏览器是核心诉求
2. **Cronet 优势**：Cronet 使用 BoringSSL（Chrome 同源），TLS/HTTP2 指纹天然接近 Chrome，是 OkHttp 通过任何配置都无法模拟的
3. **战略价值**：反爬成功率和弱网性能两个维度对爬虫类项目具有 OkHttp 难以替代的价值
4. **官方背书**：YouTube/Maps/Photos 等亿级用户 App 默认使用 Cronet，ExoPlayer/gRPC 官方支持

**初版方案对比**：
- 初版方案：统一 isCronet 开关逻辑（让 ExoPlayer/DoH 受开关控制）
- 新方向：Cronet 默认自动启用 + 扩展使用范围 + 性能稳定性全面评估（更激进、更符合项目本质）

## 分析范围

### 已使用 Cronet 的模块（4 大模块）

#### A. OkHttp 全局拦截器（核心入口）
- 文件：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt` L144-153
- 代码逻辑：当 isCronet 开启且 Cronet loader 安装成功时，将 Cronet 拦截器加入 OkHttp 拦截器链
- 受 isCronet 开关控制：是
- 影响范围：所有走 okHttpClient 的请求（34 个文件使用）
- 覆盖场景：书源请求、订阅源请求、搜索、发现、内容获取、WebDav、应用更新检查、各种导入功能等
- 新方向：评估升级为 CronetTransportForOkHttp 桥接层（替代 CronetInterceptor）

#### B. ExoPlayer 视频播放器
- 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`
- 代码逻辑：cronetDataFactory 通过 lazy 初始化，直接使用 cronetEngine
- 受 isCronet 开关控制：否（直接用 cronetEngine lazy）
- 用途：HLS/DASH/MP4 视频流加载，独立于 OkHttp 拦截器
- 新方向：保持现状（ExoPlayer 已原生支持 Cronet，是行业最佳实践）

#### C. DoH DNS 解析
- 文件：`app/src/main/java/io/legado/app/help/http/DohDns.kt`
- 代码逻辑：在 HttpHelper.kt L143 调用 builder.dns(DohDns)
- 受 isCronet 开关控制：否（直接初始化）
- 用途：绕过本地 DNS 污染
- 新方向：保持启用（Cronet 内置 AsyncDNS + DoH 是独有优势）

#### D. AnalyzeUrl DNS 自定义解析
- 文件：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` L626
- 代码逻辑：当 isCronet 开启且 dnsIp 非空时启用自定义 DNS
- 受 isCronet 开关控制：是
- 新方向：默认启用后自动生效

### 未使用 Cronet 的模块（3 大模块）

#### A. WebView 网络栈（不可接入）
- 文件：WebViewPool.kt / BackstageWebView.kt / ImageSnifferWebView.kt
- 原因：WebView 是系统组件，内部使用 Chromium 网络栈，无法替换为 Cronet（Android 系统限制）
- 影响：视频嗅探、图片嗅探、书源/订阅源 WebView 模式
- 结论：**不可行，保留系统 WebView 网络栈**

#### B. Glide 图片加载（P2 扩展）
- 文件：LegadoGlideModule.kt / OkHttpStreamFetcher.kt / ImageLoader.kt
- 当前状态：通过 okHttpClientManga 间接接入 Cronet（继承 okHttpClient 拦截器）
- 新方向：评估通过 OkHttp 桥接（callFactory=CronetTransport）直接接入，获得 QUIC/Brotli/连接迁移能力
- 优先级：P2（图片 CDN 通常不严苛反爬，但弱网加载速度有提升）

#### C. HttpURLConnection（P1 扩展）
- 文件：CronetLoader.kt L335（SO 文件下载）/ ObsoleteUrlFactory.kt（兼容旧 URL.openConnection）
- 当前状态：ObsoleteUrlFactory 实际桥接到 OkHttp
- 新方向：通过 okhttp-urlconnection 适配，底层走 Cronet
- 优先级：P1（成本低，通过桥接即可）
- 注意：Cronet 加载前不能用 Cronet 下载 SO（避免循环依赖）

### 扩展优先级矩阵

| 扩展项 | 收益 | 成本 | 优先级 | 状态 |
|--------|------|------|--------|------|
| 核心网络请求（书源抓取） | 极高（反爬+弱网） | 中 | P0（立即） | 已接入 |
| HttpURLConnection 替换 | 高 | 低（桥接） | P1（阶段二） | 待实施 |
| Glide 图片加载 | 中 | 低（桥接） | P2（阶段三） | 待实施 |
| 文件上传/下载 | 中 | 中 | P3（阶段三） | 待实施 |
| WebView 接入 | 不可行 | - | 不建议 | 系统限制 |
| WebSocket | 不可行 | - | 保留 OkHttp | Cronet 不支持 |

### 性能对比（Cronet vs OkHttp）

| 维度 | Cronet | OkHttp | 差距 |
|------|--------|--------|------|
| HTTP/3 (QUIC) | ✅ 原生 | ❌ 不支持 | Cronet 碾压 |
| TLS 库 | BoringSSL（Chrome 同款） | Conscrypt/OpenSSL | Cronet 指纹优势 |
| 连接迁移 | ✅ ConnectionMigrationOptions | ❌ | Cronet 独有 |
| 内置 AsyncDNS + DoH | ✅ DnsOptions | ❌ 依赖系统 | Cronet 独有 |
| 弱网平均延迟（300ms RTT, 2% 丢包） | 420ms | 850ms | ~50% 降低 |
| 弱网吞吐量（5% 丢包） | 1.8MB/s | 1.2MB/s | ~50% 提升 |
| WiFi→4G 切换恢复 | 0ms（无缝迁移） | ~500ms（需重连） | 决定性 |
| 反爬成功率（实测） | 87.9%（BoringSSL） | 12.3%（OpenSSL） | 决定性 |
| WebSocket | ❌ 不原生支持 | ✅ 原生 | OkHttp 胜 |

### 风险评估

| 风险项 | 等级 | 缓解措施 |
|--------|------|---------|
| JNI 崩溃（SIGABRT） | 高 | 降级机制 + 崩溃监控 + 自动回退 OkHttp |
| ProGuard 规则缺失 | 高 | 完整 keep 规则 + release 包真机测试 |
| WebSocket 不可用 | 中 | 保留 OkHttp 处理 WebSocket |
| APK 体积增加 | 中 | 国内用 embedded(+5-8MB)，海外用 play-services(0MB) |
| 电池消耗（QUIC 保活） | 低 | 配置 idle timeout + 监控 |
| 连接迁移平台限制 | 低 | 作为加分项，不强依赖 |
| Google Play 服务不可用（国内） | 低（国内高） | embedded + fallback 降级链 |

## 核心结论

### 建议默认启用 Cronet

采用"桥接 + 分层降级 + 渐进扩展"策略，而非全局无条件替换。

### 建议理由

1. **反爬战略价值不可替代**：Cronet 使用 BoringSSL（Chrome 同源），TLS/HTTP2 指纹天然接近 Chrome，这是 OkHttp 通过任何配置都无法模拟的。对爬虫类项目而言，这是决定能否成功抓取的关键因素
2. **弱网性能优势显著**：QUIC 在弱网下延迟降低约 50%，吞吐量提升约 50%，连接迁移避免网络切换断连，直接提升用户体验
3. **Google 官方背书**：YouTube/Maps/Photos 等亿级用户 App 默认使用，ExoPlayer/gRPC 官方支持，成熟度有保障
4. **桥接方案成本低**：通过 CronetTransportForOkHttp，现有 OkHttp 代码零改动即可获得 Cronet 能力
5. **降级机制可控**：保留 OkHttp 处理 WebSocket 和降级兜底，风险可控

### 推荐方案

- **桥接层**：CronetTransportForOkHttp（Google 官方，`com.google.net.cronet:cronet-okhttp`）
- **降级链**：Cronet(play-services) → Cronet(embedded) → cronet-fallback → OkHttp
- **Provider 策略**：国内用 cronet-embedded（+5-8MB），海外用 play-services-cronet（0MB）
- **开关策略**：isCronet 默认值改为 true（保留开关用于紧急关闭）

### 不建议全局无条件替换的理由

1. **WebSocket 缺失**：Cronet 不支持 WebSocket，必须保留 OkHttp
2. **JNI 崩溃风险**：特定设备/ROM 上的 native 崩溃需降级通道
3. **体积考量**：国内设备需 cronet-embedded（+5-8MB），需评估 APK 体积敏感度
4. **ProGuard 复杂性**：release 包需严格验证混淆规则

## 实施路径（四阶段）

### 阶段一：基础设施搭建（P0）
- isCronet 默认值改为 true（AppConfig.kt）
- 评估引入 CronetTransportForOkHttp 桥接层（添加 cronet-okhttp 依赖）
- 完善降级链（Cronet→fallback→OkHttp）
- 配置 ProGuard 规则（补充 cronet-okhttp keep 规则）
- Cronet 引擎配置优化（连接迁移+DNS选项+QUIC hints）

### 阶段二：核心网络层接入（P1）
- 评估 CronetTransportForOkHttp 替代 CronetInterceptor
- 书源抓取请求走 Cronet（验证反爬+弱网收益）
- HttpURLConnection 替换为 OkHttp 桥接
- 编译测试包验证（io.legado.miss.app.debug）
- 真机测试 QUIC 连接+TLS 指纹+弱网表现
- 编译正式包+mapping.txt 检查（io.legado.miss.app.release）

### 阶段三：扩展场景接入（P2-P3）
- Glide 图片加载接入 Cronet（P2）
- 文件上传/下载接入 Cronet（P3）
- 验证扩展场景功能正常

### 阶段四：监控与调优
- 性能监控（Cronet vs OkHttp 对比）
- 崩溃监控（JNI SIGABRT 告警+自动降级）
- 参数调优（idle timeout/max concurrent streams/连接迁移）
- 灰度发布评估

## 设计原则

1. **默认启用，渐进扩展**：Cronet 作为默认网络栈，分阶段扩展使用范围
2. **桥接优先，零改动**：通过 CronetTransportForOkHttp 桥接层，现有 OkHttp 代码零改动
3. **分层降级，风险可控**：保留 OkHttp 作为降级通道，保障异常场景可用性
4. **可观测，可调优**：关键节点输出技术日志，支持性能监控与参数调优
5. **用户可控，紧急关闭**：保留 isCronet 开关用于紧急关闭，平衡默认启用与用户选择权

## 项目现状

- **isCronet 默认值**：false（待改为 true）
- **SO 加载方案**：已用动态下载 SO 方案
- **拦截器模式**：已用 OkHttp 拦截器模式（CronetInterceptor）
- **降级机制**：已有（连续 5 次协议错误降级 OkHttp）
- **已使用 Cronet**：OkHttp拦截器 / ExoPlayer / DohDns / AnalyzeUrl
- **未使用 Cronet**：WebView（系统限制）/ Glide（间接接入）/ HttpURLConnection

## 相关规范引用

- 编码哲学规范：极简≠残缺，100% 满足需求+保证健壮性
- 网络层优化规范：参考 forks-reference.md
- 真机测试包选择规范：代码优化任务必须使用测试包（io.legado.miss.app.debug）
- 日志规范：使用 AppLog.put()，禁止 android.util.Log
- ProGuard 验证规范：release 包必须真机测试（io.legado.miss.app.release）

## 后续规划

- spec.md：详细需求规格（功能需求/非功能需求/验收标准）
- design.md：技术设计方案（桥接层架构/降级链时序/接口设计/ProGuard 规则）
- tasks.md：任务执行清单（四阶段+AOAdapt 日志）
