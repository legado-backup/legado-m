# Cronet 默认启用可行性研究报告

> 面向 Android 爬虫/抓取类项目（自定义书源规则引擎场景）的技术评估
> 研究日期：2026-07-31 | 只含技术结论，不含业务数据

---

## 一、执行摘要

本研究针对"是否应将 Cronet 作为初始化自动启用模式（默认开启）并尽可能扩展使用范围"这一问题，从性能、反爬、可行性、扩展性、风险、行业实践六个维度展开深度调研。结论如下：

**核心建议：建议默认启用 Cronet，但采用"分层降级 + 渐进扩展"策略，而非全局无条件替换。** 理由是 Cronet 在反爬 TLS 指纹和弱网性能两个维度对爬虫类项目具有 OkHttp 难以替代的战略价值；但其 JNI/ProGuard 复杂性、WebSocket 缺失、体积开销要求必须保留 OkHttp 作为降级通道。推荐采用 Google 官方的 `play-services-cronet`（零体积）+ `cronet-embedded`（自带 SO）双 Provider 方案，通过 `CronetTransportForOkHttp` 桥接层让现有 OkHttp 代码无感获得 Cronet 能力。

---

## 二、Cronet vs OkHttp 性能对比

### 2.1 协议栈能力矩阵

| 能力 | Cronet | OkHttp | 差距 |
|------|--------|--------|------|
| HTTP/1.1 | ✅ | ✅ | 持平 |
| HTTP/2 | ✅ 原生 | ✅ 原生 | 持平 |
| HTTP/3 (QUIC) | ✅ 原生 | ❌ 不支持 | Cronet 碾压 |
| TLS 库 | BoringSSL（Chrome 同款） | Conscrypt/OpenSSL | Cronet 指纹优势 |
| Brotli 压缩 | ✅ 原生 | ✅ 需配置 | 持平 |
| 连接迁移 | ✅ ConnectionMigrationOptions | ❌ | Cronet 独有 |
| 内置 AsyncDNS + DoH | ✅ DnsOptions | ❌ 依赖系统 | Cronet 独有 |
| 请求优先级 | ✅ | ❌ | Cronet 独有 |
| 磁盘/内存缓存 | ✅ 原生 | ✅ 需 Cache 组件 | 持平 |
| WebSocket | ❌ 不原生支持 | ✅ 原生 | OkHttp 胜 |

### 2.2 TLS 握手性能

- **Cronet（BoringSSL）**：与 Chrome 浏览器同源，TLS 1.3 握手 1-RTT，0-RTT 复用后首包零延迟。
- **OkHttp（Conscrypt）**：基于 OpenSSL 分支，TLS 1.3 支持，但握手扩展顺序与 Chrome 不同。
- 差距：在握手阶段两者耗时接近，但 Cronet 的 0-RTT 机制在连接复用场景下可将 TTFB 压缩至 20-50ms 量级。

### 2.3 HTTP/3 (QUIC) 的核心优势（多源印证）

根据 Google 官方文档与多个 benchmark 实测：

| 场景 | HTTP/2 (TCP) | HTTP/3 (QUIC) | 提升幅度 |
|------|-------------|---------------|---------|
| 强网连接建立 | 300ms | 0ms（0-RTT 复用） | 决定性 |
| 弱网平均延迟（300ms RTT, 2% 丢包） | 850ms | 420ms | ~50% |
| 弱网吞吐量（5% 丢包） | 1.2MB/s | 1.8MB/s | ~50% |
| WiFi→4G 切换恢复 | ~500ms（需重连） | 0ms（无缝迁移） | 决定性 |
| 首字节时间 TTFB | 2-3 RTT | 0.5 RTT（0-RTT） | 显著 |

QUIC 优势的技术根源：
1. **0-RTT 连接**：复用先前会话密钥，首包零延迟
2. **多路复用无队头阻塞**：每个 stream 独立滑动窗口，单流丢包不阻塞其他流
3. **连接迁移**：通过 Connection ID 维持网络切换时的会话连续性（Android 平台 java 层注册系统通知支持，iOS/native 库支持有限）
4. **改进拥塞控制**：内置 BBR v2 / CUBIC，弱网表现更优

### 2.4 连接复用与 DNS

- **Cronet 连接池**：原生支持 HTTP/2 多路复用，单 TCP 连接承载多请求；QUIC 连接迁移避免重建。
- **DNS**：Cronet 内置 AsyncDNS（异步 DNS 解析）+ DoH（DNS over HTTPS），可绕过系统 DNS 劫持/污染，对爬虫场景的域名解析稳定性有实质提升。OkHttp 依赖系统 DNS（可通过 doh-jansb 实现 DoH，但非原生）。

### 2.5 体积对比

| 方案 | APK 增量 | 说明 |
|------|---------|------|
| cronet-embedded | ~5-8MB | 自带完整 SO（所有 ABI 合计约 6.37MB，单 ABI 约 3MB） |
| play-services-cronet | ~0MB | 从 Google Play 服务动态加载，不占 APK 体积 |
| OkHttp | ~100KB | 轻量 |
| cronet-fallback | 较小 | Java 实现的降级版，性能较差 |

---

## 三、Cronet 在反爬/反检测场景的战略优势

> 本节是爬虫类项目选择 Cronet 的**最核心理由**。

### 3.1 TLS 指纹（JA3/JA4）原理

JA3/JA4 是基于 TLS 握手 ClientHello 报文生成的客户端身份指纹，不依赖易伪造的 IP/UA/Cookie，可精准识别客户端类型。主流 WAF（Cloudflare、阿里云 ESA、华为云 WAF 等）已普遍部署 JA3/JA4 检测。

**关键差异**：

| 客户端 | TLS 库 | JA3/JA4 指纹 | WAF 识别难度 |
|--------|--------|-------------|-------------|
| Chrome | BoringSSL | 真实 Chrome 指纹 | 无法识别 |
| Cronet | BoringSSL（Chrome 同源） | 接近 Chrome | 难以识别 |
| OkHttp | Conscrypt/OpenSSL | 爬虫特征指纹 | 容易识别 |
| Python requests | OpenSSL | 已知爬虫指纹 | 容易识别 |
| Java HttpClient | OpenSSL/JSSE | 爬虫指纹 | 容易识别 |

### 3.2 OkHttp 在反检测场景的致命劣势

OkHttp（Conscrypt）的 ClientHello 有以下硬伤，使其在 TLS 握手阶段就被 WAF 识别为非浏览器：
1. cipher_suites 顺序固定、精简，缺少浏览器常用的 CHACHA20、AES-GCM 混合排列
2. ALPN 扩展缺失或只声明 http/1.1，而 Chrome 默认携带 h2,http/1.1
3. supported_groups（椭圆曲线）只列 secp256r1，缺 x25519 等现代曲线
4. 缺少 key_share 扩展（TLS 1.3 必需）或格式不符合 BoringSSL 行为
5. JA3 指纹长期稳定，已被 WAF 数据库标记为脚本特征

### 3.3 HTTP/2 指纹（AKAMAI 指纹）

即使 TLS 指纹匹配，HTTP/2 层仍会暴露。JA4H 及 HTTP/2 指纹检测以下信号：

| 信号 | Chrome | OkHttp/curl |
|------|--------|-------------|
| SETTINGS 帧数量 | 4 | 5 |
| INITIAL_WINDOW_SIZE | 6,291,456 | 65,535（默认） |
| Header table size | 65,536 | 4,096 |
| Pseudo-header 顺序 | :method :authority :scheme :path | :method :path :scheme :authority |
| PRIORITY 帧 | 无（Chrome 已移除） | 有 |
| WINDOW_UPDATE（连接级） | +15,663,105 | +32MB |

Cronet 由于与 Chrome 同源，其 HTTP/2 帧参数天然接近 Chrome，这是 OkHttp 无法通过配置模拟的。

### 3.4 实测数据印证（同 IP 同场景）

- curl_cffi（使用 BoringSSL 模拟 Chrome）：对受 Cloudflare 保护的端点成功率 **87.9%**
- Python requests（OpenSSL）：同一 IP 成功率仅 **12.3%**

> 结论：TLS 库的选择（BoringSSL vs OpenSSL）是决定反爬成功率的关键因素。Cronet 天然使用 BoringSSL，对爬虫类项目具有不可替代的价值。

---

## 四、Cronet 默认启用的可行性分析

### 4.1 行业实践（Google 官方背书）

Google 官方明确推荐使用 Cronet，以下主流 App 均默认使用 Cronet 处理网络请求：
- YouTube
- Google App（搜索）
- Google Photos
- Google Maps - Navigation & Transit
- ExoPlayer（媒体播放器，直接支持 Cronet 作为网络栈）
- gRPC Android（官方推荐 Cronet 传输，OkHttp 为默认）

Google 官方原文："Cronet 是最常用以支持 HTTP/3 的 Android 网络库"，"建议以最新 SDK 版本为目标平台的应用使用 Cronet，因为它提供了更强大的网络堆栈"。

### 4.2 SDK 体积解决方案

**推荐方案：play-services-cronet（动态加载）**
- 依赖：`com.google.android.gms:play-services-cronet:18.1.0` + `org.chromium.net:cronet-api`
- 体积：APK 几乎零增量（SO 由 Google Play 服务提供）
- 更新：平台自动推送最新版本和安全修复
- 前提：设备需安装 Google Play 服务（Android 6.0+ / API 23+）
- 初始化：需调用 `CronetProviderInstaller.installProvider(context)` 异步安装 Provider

**备选方案：cronet-embedded（自带 SO）**
- 适用：Google Play 服务未广泛普及的市场（如国内设备），或需精确控制 Cronet 版本
- 体积：APK 增加约 5-8MB（单 ABI 约 3MB，全 ABI 约 6.37MB）
- 优点：不依赖 Google Play 服务，版本可控
- 缺点：体积大，需自行管理 SO 版本与安全更新

**国内场景建议**：由于国内设备普遍无 Google Play 服务，建议采用 `cronet-embedded` 作为主 Provider，`cronet-fallback` + OkHttp 作为降级。

### 4.3 动态下载 SO 的可靠性

- play-services-cronet 的 `CronetProviderInstaller.installProvider()` 返回 `Task`，异步执行，需处理成功/失败回调
- 失败场景：设备无 Google Play 服务、版本过低、网络不可用
- 失败处理：回退到 `cronet-embedded`（若集成）或 `cronet-fallback`（Java 实现，性能较差）或 OkHttp
- 可靠性：在有 Google Play 服务的设备上可靠性高；国内设备不可用

### 4.4 JNI 稳定性（Cronet 150+）

- Cronet 通过 JNI 调用 native 层（BoringSSL + QUIC 栈）
- JNI 注册机制：Cronet 使用 `RegisterNatives` 方式注册 native 方法（非 `Java_*` 命名约定）
- ProGuard/R8 风险：若 R8 混淆了被 native 层通过反射调用的 Java 类/方法，会触发 `UnsatisfiedLinkError` 或 `NoSuchMethodError`
- 必需 ProGuard 规则：
  ```
  -keep class org.chromium.** { *; }
  -keepclassmembers class * { native <methods>; }
  ```
- 铁证：项目已记录"Cronet 149+ ProGuard 规则缺失导致 release 包订阅源列表加载失败"

### 4.5 降级机制的必要性

**必须保留 OkHttp 作为降级通道**，原因：
1. Cronet JNI 崩溃（SIGABRT）在特定设备/ROM 上不可控
2. Cronet 不支持 WebSocket（需 OkHttp 兜底）
3. Google Play 服务不可用时需回退
4. 部分 HTTPS 场景（自签名证书、特殊 TLS 配置）OkHttp 兼容性更好

推荐降级链：`Cronet (play-services)` → `Cronet (embedded)` → `cronet-fallback` → `OkHttp`

---

## 五、Cronet 扩展使用范围的方案

### 5.1 WebView 接入 Cronet

**结论：Android 系统限制，无法直接让 App 内 WebView 使用 Cronet。**

- WebView 有独立的网络栈（基于 Chromium net，但由系统 WebView 实现，非应用层可控）
- 应用层无法注入 CronetEngine 到 WebView
- Android 9 (Pie) 起，系统 WebView 已默认支持 QUIC，但与应用层 Cronet 是独立实例
- 替代方案：如需 WebView + Cronet 能力，需自行用 Cronet 拉取 HTML 后注入 WebView（`loadDataWithBaseURL`），但会丢失 WebView 的 JS 执行、Cookie 管理等能力

### 5.2 Glide 图片加载接入 Cronet

**结论：可通过 OkHttp 桥接间接接入，但收益有限，优先级低。**

- Glide 默认使用 HttpURLConnection，可替换为 OkHttp（`OkHttpUrlLoader`）
- 接入路径：Glide → OkHttp（`callFactory` 设为 `CronetTransport.newFactory(cronetEngine)`）→ Cronet
- 即：`Glide.with(ctx).load(url)` → OkHttpClient(callFactory=CronetTransport) → Cronet 引擎
- 收益：图片加载获得 QUIC/Brotli/连接迁移能力
- 评估：图片加载场景下，TLS 指纹优势不明显（图片 CDN 通常不严苛反爬），但弱网加载速度有提升
- 建议：作为第二阶段扩展，优先级低于核心网络请求

### 5.3 HttpURLConnection 替换

**结论：建议替换，但通过 OkHttp 桥接而非直接重写。**

- 直接用 Cronet API 重写所有 HttpURLConnection 调用成本高（回调模型差异大）
- 推荐路径：HttpURLConnection → OkHttp（`okhttp-urlconnection` 适配）→ Cronet（CronetTransport）
- 即保持上层 API 不变，底层传输层替换

### 5.4 WebSocket 支持

**结论：Cronet 不原生支持 WebSocket，必须保留 OkHttp 处理 WebSocket。**

- Cronet 官方 API 无 WebSocket 客户端（`UrlRequest` 仅支持 HTTP/HTTPS 请求/响应模型）
- 行业实践：Cronet 的 WebSocket 连接池依赖 TCP 连接池，但 cronet 网络库未完整实现 WebSocket 协议
- 方案：WebSocket 请求继续走 OkHttp（OkHttp 原生支持 WebSocket，且可通过 `Interceptor` 注入 Cronet 处理 HTTP 降级）

### 5.5 文件上传/下载

**结论：Cronet 有优势，建议接入。**

- 上传：Cronet 提供 `UploadDataProvider` 流式上传，支持大文件分块，内存占用低
- 下载：Cronet 的 `UrlRequest.Callback.onReadCompleted()` 支持流式读取（ByteBuffer），适合大文件下载
- 优势：QUIC 的连接迁移使移动网络下的大文件下载更稳定（WiFi→4G 不中断）
- 建议：作为第三阶段扩展

### 5.6 扩展优先级矩阵

| 扩展项 | 收益 | 成本 | 优先级 |
|--------|------|------|--------|
| 核心网络请求（书源抓取） | 极高（反爬+弱网） | 中 | P0（立即） |
| HttpURLConnection 替换 | 高 | 低（桥接） | P1（第一阶段） |
| Glide 图片加载 | 中 | 低（桥接） | P2（第二阶段） |
| 文件上传/下载 | 中 | 中 | P3（第三阶段） |
| WebView 接入 | 不可行 | - | 不建议 |
| WebSocket | 不可行 | - | 保留 OkHttp |

---

## 六、Cronet 已知问题和风险

### 6.1 JNI 崩溃风险（SIGABRT）

- **现象**：native 层 `abort()` 触发 SIGABRT，进程终止
- **常见原因**：
  - ProGuard/R8 混淆了 native 层反射调用的 Java 类
  - native 层访问 NULL 指针、数组越界、错误线程使用 JNIEnv
  - Cronet SO 版本与 API 版本不匹配
- **预防**：完整 ProGuard 规则 + 崩溃监控 + 降级机制
- **铁证**：项目已记录 Cronet 149+ JNI 注册机制问题

### 6.2 ProGuard 规则复杂性

- Cronet 依赖较复杂的 keep 规则（保留 `org.chromium.**` 全包 + native 方法 + 反射调用类）
- R8 优化可能移除"看似无用"的 Cronet 内部类，导致运行时 `ClassNotFoundException`
- Android 14 引入的 `java.lang.ClassValue` 变化曾导致 ProGuard 误删 `computeValue` 方法（Google 官方记录）
- **建议**：release 包必须真机测试（项目规范已要求：Skill 真机测试用正式包验证 ProGuard）

### 6.3 SO 文件版本管理

- `cronet-embedded` 需手动锁定版本（如 `113.5672.61`）
- 版本更新需验证：JNI 兼容性、ProGuard 规则、新 API
- 多 ABI 管理：`armeabi-v7a`、`arm64-v8a`、`x86`、`x86_64` 四套 SO，可用 ABI splits 按需打包
- **建议**：锁定版本，升级前做全量回归测试

### 6.4 内存占用

- Cronet 引擎实例（CronetEngine）占用固定内存（native 层）
- QUIC 连接初始多消耗约 **3MB**（加密上下文开销）
- 长连接场景内存增长曲线较平稳（优于频繁重建 TCP 连接）
- **建议**：全局单例 CronetEngine（官方推荐只创建一个实例），避免多实例内存膨胀

### 6.5 电池消耗（QUIC 保活）

- QUIC 保活连接会持续消耗电量
- 实测：QUIC 在视频加载场景将耗时从 1.8s 降到 1.2s，但需持续监控电池消耗
- **建议**：配置 `idle_connection_timeout_seconds`（如 30s），避免空闲连接长期保活；根据业务场景调优，避免过度设计

### 6.6 连接迁移的平台限制

- Android：java 层注册系统通知，"打折扣"支持连接迁移
- iOS：实测 QUIC 切网后重新握手，未实现连接迁移
- 服务端：需支持连接迁移（非所有 QUIC 服务器支持）
- **结论**：连接迁移是加分项，不能作为强依赖

---

## 七、成熟方案参考

### 7.1 Google 官方方案（推荐）

| 方案 | 依赖 | 适用场景 | 体积 |
|------|------|---------|------|
| play-services-cronet | `com.google.android.gms:play-services-cronet:18.1.0` | 有 Google Play 服务的设备 | ~0MB |
| cronet-embedded | `org.chromium.net:cronet-embedded` | 无 Google Play 服务（国内） | ~5-8MB |
| cronet-fallback | `org.chromium.net:cronet-fallback` | 降级兜底 | 较小 |
| cronet-api | `org.chromium.net:cronet-api` | API 接口（必需） | 极小 |

### 7.2 CronetTransportForOkHttp（Google 官方桥接，强烈推荐）

- 依赖：`com.google.net.cronet:cronet-okhttp`
- 作用：让 OkHttp/Retrofit 无感使用 Cronet 作为传输层
- 核心代码：
  ```kotlin
  val cronetEngine = CronetEngine.Builder(context).build()
  val okHttpClient = OkHttpClient.Builder()
      .callFactory(CronetTransport.newFactory(cronetEngine))
      .build()
  ```
- 优势：**现有 OkHttp 代码零改动**即可获得 QUIC/HTTP3 + 连接迁移 + BoringSSL 指纹能力
- 生态：ExoPlayer、gRPC-Cronet 均采用类似桥接模式

### 7.3 ExoPlayer 的 Cronet 集成（行业最佳实践参考）

ExoPlayer 官方支持四种网络栈：HttpEngine（API 34+，内部用 Cronet）、Cronet、OkHttp、Android 默认。

ExoPlayer 的 Cronet 集成策略值得借鉴：
1. 支持 Google Play 服务 Cronet（推荐）+ 嵌入式 Cronet + 回退三种实现
2. 通过 `CronetDataSource.Factory` 注入
3. Google Play 服务不可用时回退到 `DefaultHttpDataSource`（Android 内置网络栈）

### 7.4 行业反爬方案对比

| 方案 | TLS 库 | 反爬成功率 | 适用平台 |
|------|--------|-----------|---------|
| Cronet（BoringSSL） | BoringSSL | 高（接近 Chrome） | Android/iOS |
| curl-impersonate / curl_cffi | BoringSSL | 87.9%（实测） | 跨平台 |
| OkHttp（Conscrypt） | OpenSSL 分支 | 低（易被识别） | Android |
| Python requests | OpenSSL | 12.3%（实测） | 跨平台 |

---

## 八、最终建议

### 8.1 总体结论

**建议：默认启用 Cronet，采用"桥接 + 分层降级 + 渐进扩展"策略。**

### 8.2 建议理由

1. **反爬战略价值不可替代**：Cronet 使用 BoringSSL（Chrome 同源），TLS/HTTP2 指纹天然接近 Chrome，这是 OkHttp 通过任何配置都无法模拟的。对爬虫类项目而言，这是决定能否成功抓取的关键因素。
2. **弱网性能优势显著**：QUIC 在弱网下延迟降低约 50%，吞吐量提升约 50%，连接迁移避免网络切换断连，直接提升用户体验。
3. **Google 官方背书**：YouTube/Maps/Photos 等亿级用户 App 默认使用，ExoPlayer/gRPC 官方支持，成熟度有保障。
4. **桥接方案成本低**：通过 `CronetTransportForOkHttp`，现有 OkHttp 代码零改动即可获得 Cronet 能力。
5. **降级机制可控**：保留 OkHttp 处理 WebSocket 和降级兜底，风险可控。

### 8.3 不建议全局无条件替换的理由

1. **WebSocket 缺失**：Cronet 不支持 WebSocket，必须保留 OkHttp
2. **JNI 崩溃风险**：特定设备/ROM 上的 native 崩溃需降级通道
3. **体积考量**：国内设备需 cronet-embedded（+5-8MB），需评估 APK 体积敏感度
4. **ProGuard 复杂性**：release 包需严格验证混淆规则

---

## 九、实施路径（分四阶段）

### 阶段一：基础设施搭建（P0）

1. **引入依赖**：
   - `play-services-cronet:18.1.0`（有 GMS 设备）
   - `cronet-embedded`（无 GMS 设备，国内必备）
   - `cronet-api`（API 接口）
   - `cronet-okhttp`（CronetTransportForOkHttp 桥接）
2. **封装 Cronet 引擎管理器**：
   - 全局单例 `CronetEngine`（官方推荐只创建一个实例）
   - 配置：`enableQuic(true)` + `enableHttp2(true)` + `enableBrotli(true)` + `setConnectionMigrationOptions(...)` + `setDnsOptions(...)`
   - Provider 安装：`CronetProviderInstaller.installProvider()` 异步初始化
3. **实现降级链**：Cronet(play-services) → Cronet(embedded) → cronet-fallback → OkHttp
4. **配置 ProGuard 规则**：
   ```
   -keep class org.chromium.** { *; }
   -keep class com.google.net.cronet.** { *; }
   -keepclassmembers class * { native <methods>; }
   ```
5. **将 isCronet 开关默认值改为 true**（保留开关用于紧急关闭）

### 阶段二：核心网络层接入（P1）

1. **OkHttp 桥接**：将核心 OkHttpClient 的 `callFactory` 设为 `CronetTransport.newFactory(cronetEngine)`
2. **书源抓取请求**：所有书源规则引擎的网络请求走 Cronet（反爬 + 弱网收益最大）
3. **HttpURLConnection 替换**：通过 `okhttp-urlconnection` 适配，底层走 Cronet
4. **真机测试**（按项目规范用测试包 `io.legado.miss.app.debug`）：
   - 验证 QUIC 连接（`adb logcat -s Cronet*,Quic*`）
   - 验证 TLS 指纹（对比 OkHttp 的抓取成功率）
   - 验证弱网表现（模拟器限速）
   - 验证 release 包 ProGuard（用正式包 `io.legado.miss.app.release`）

### 阶段三：扩展场景接入（P2-P3）

1. **Glide 图片加载**（P2）：注入 OkHttpClient(callFactory=CronetTransport) 到 Glide
2. **文件上传/下载**（P3）：使用 Cronet 的 `UploadDataProvider` 和流式 `onReadCompleted`

### 阶段四：监控与调优

1. **性能监控**：对比 Cronet vs OkHttp 的连接成功率、延迟分布、TLS 握手耗时
2. **崩溃监控**：JNI 崩溃（SIGABRT）告警 + 自动降级到 OkHttp
3. **参数调优**：
   - `idle_connection_timeout_seconds`（平衡保活与电量）
   - `max_concurrent_streams`（根据设备性能）
   - 连接迁移开关（`enableDefaultNetworkMigration`）
4. **灰度发布**：按用户比例开启 Cronet，监控关键指标后全量

---

## 十、风险评估总结

| 风险项 | 等级 | 缓解措施 |
|--------|------|---------|
| JNI 崩溃（SIGABRT） | 高 | 降级机制 + 崩溃监控 + 自动回退 OkHttp |
| ProGuard 规则缺失 | 高 | 完整 keep 规则 + release 包真机测试 |
| WebSocket 不可用 | 中 | 保留 OkHttp 处理 WebSocket |
| APK 体积增加 | 中 | 国内用 embedded(+5-8MB)，海外用 play-services(0MB) |
| 电池消耗 | 低 | 配置 idle timeout + 监控 |
| 连接迁移平台限制 | 低 | 作为加分项，不强依赖 |
| Google Play 服务不可用 | 低（国内高） | embedded + fallback 降级链 |

---

## 附录：关键技术参数速查

### CronetEngine.Builder 推荐配置

```kotlin
val cronetEngine = CronetEngine.Builder(context)
    .enableQuic(true)                              // 启用 HTTP/3
    .enableHttp2(true)                             // 启用 HTTP/2
    .enableBrotli(true)                            // 启用 Brotli 压缩
    .enableHttpCache(CronetEngine.Builder.HTTP_CACHE_DISK, 10L * 1024 * 1024)  // 10MB 磁盘缓存
    .setStoragePath(cacheDir.absolutePath)         // 存储路径
    .setConnectionMigrationOptions(
        ConnectionMigrationOptions.Builder()
            .enableDefaultNetworkMigration(true)   // 默认网络迁移
            .enablePathDegradationMigration(true)  // 路径降级迁移
            .build()
    )
    .setDnsOptions(
        DnsOptions.Builder()
            .enableBuiltInDnsResolver(true)        // 内置异步 DNS
            .enablePreconnect(true)                // DNS 预连接
            .build()
    )
    .build()
```

### 依赖版本（截至 2026-07）

- `com.google.android.gms:play-services-cronet:18.1.0`
- `org.chromium.net:cronet-embedded`（锁定版本，如 113.5672.61）
- `org.chromium.net:cronet-api`（与 embedded 版本一致）
- `com.google.net.cronet:cronet-okhttp`（最新稳定版）

---

*报告完*
