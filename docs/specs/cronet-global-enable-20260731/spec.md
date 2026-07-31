# Cronet 默认启用与扩展使用优化

**文档状态**: 🔄 设计中（方向调整 v2）
**创建日期**: 2026-07-31
**作者**: AI 辅助生成
**OpenSpec ID**: cronet-global-enable-20260731
**关联研究报告**: [cronet-default-enable-feasibility-report.md](../../research/cronet-default-enable-feasibility-report.md)

## Intent

本项目（Legado/阅读M）本质上是一个抓取爬虫类项目（自定义书源规则引擎），从"模拟真实浏览器"角度出发，Cronet（Chromium 网络栈，BoringSSL 同源 Chrome）在反爬 TLS/HTTP2 指纹和弱网性能两个维度对项目具有 OkHttp 难以替代的战略价值。

当前 Cronet 使用存在三个核心问题：
1. **默认未启用**：`isCronet` 默认值为 `false`，用户需手动开启，多数用户未享受到 Cronet 的反爬与弱网收益
2. **使用范围受限**：仅 OkHttp 拦截器/ExoPlayer/DohDns/AnalyzeUrl 接入，HttpURLConnection/Glide/文件上传下载仍走旧栈
3. **桥接方式可优化**：当前采用 `CronetInterceptor` 拦截器模式（源码核实：已用 cronetEngine 执行请求获得完整 Cronet 能力），`CronetTransportForOkHttp` 桥接层可作为可选优化提升 OkHttp 调度与 Cronet 集成度（非必须迁移）

本规格说明的目标（新方向）：
- 将 `isCronet` 默认值改为 `true`，Cronet 作为初始化自动启用模式
- 评估 `CronetTransportForOkHttp` 桥接层作为可选优化（源码核实：CronetInterceptor 已用 cronetEngine 执行请求，已获得完整 Cronet 能力，桥接层非必须迁移）
- 扩展 Cronet 使用范围至 HttpURLConnection / Glide / 文件上传下载
- 完善降级链（Cronet → fallback → OkHttp），保障稳定性
- 从性能、稳定性、反爬、体积、风险等多方面进行全面评估

## Scope

### In Scope

| # | 范围 | 说明 |
|---|------|------|
| 1 | `isCronet` 默认值改为 `true` | Cronet 作为初始化自动启用模式，保留开关用于紧急关闭 |
| 2 | 评估 `CronetTransportForOkHttp` 桥接层 | 作为可选优化提升 OkHttp 调度与 Cronet 集成度（CronetInterceptor 已获得完整 Cronet 能力，桥接层非必须迁移） |
| 3 | 扩展 HttpURLConnection 接入 Cronet | 通过 `okhttp-urlconnection` 适配，底层走 Cronet 桥接 |
| 4 | 扩展 Glide 图片加载接入 Cronet | 通过 `OkHttpUrlLoader` + Cronet 桥接注入 Glide |
| 5 | 扩展文件上传/下载接入 Cronet | 使用 Cronet `UploadDataProvider` 与流式 `onReadCompleted` |
| 6 | 完善降级链 | Cronet（动态 SO）→ cronet-fallback → OkHttp，含 JNI 崩溃自动降级 |
| 7 | 性能稳定性全面评估 | Cronet vs OkHttp 性能对比、风险评估、ProGuard 规则、监控指标 |

### Out of Scope

| # | 范围 | 原因 |
|---|------|------|
| 1 | WebView 接入 Cronet | Android 系统限制，WebView 内部使用自带 Chromium 网络栈，应用层无法注入 CronetEngine |
| 2 | WebSocket 接入 Cronet | Cronet 官方 API 不支持 WebSocket（`UrlRequest` 仅支持 HTTP/HTTPS 请求/响应模型），必须保留 OkHttp 处理 |
| 3 | Cronet 版本升级 | 当前 150.0.7871.128 已稳定运行，真机日志验证无 OOM/ANR，升级需全量回归 |
| 4 | 切换为 play-services-cronet | 国内设备普遍无 Google Play 服务，不可用；项目已采用动态下载 SO 方案，保持现状 |

## Approach

### Selected Approach

**方案名称**: 默认启用 + 桥接层评估 + 分层降级 + 渐进扩展

**方案要点**:
1. `isCronet` 默认值改为 `true`，App 启动后台预初始化 Cronet 引擎
2. 评估 `CronetTransportForOkHttp` 桥接层作为可选优化（CronetInterceptor 已获得完整 Cronet 能力，桥接层非必须迁移，主要提升 OkHttp 调度与 Cronet 集成度）
3. 完善降级链：Cronet（动态 SO）→ cronet-fallback → OkHttp，含 JNI 崩溃监控与自动降级
4. 渐进扩展使用范围：P0 核心网络请求（已接入）→ P1 HttpURLConnection → P2 Glide → P3 文件上传下载
5. 性能监控：Cronet vs OkHttp 连接成功率/延迟/TLS 握手耗时对比
6. 稳定性保障：ProGuard 规则补充 + JNI 崩溃监控 + release 包真机验证

**选择理由**:
- **反爬战略价值不可替代**: Cronet 使用 BoringSSL（Chrome 同源），TLS/HTTP2 指纹天然接近 Chrome，实测反爬成功率 87.9% vs OkHttp 12.3%，这是 OkHttp 通过任何配置都无法模拟的
- **弱网性能优势显著**: QUIC 在弱网下延迟降低约 50%，吞吐量提升约 50%，0-RTT 连接复用与连接迁移避免网络切换断连
- **Google 官方背书**: YouTube/Maps/Photos 等亿级用户 App 默认使用，ExoPlayer/gRPC 官方支持，成熟度有保障
- **桥接方案成本低**: 通过 `CronetTransportForOkHttp`，现有 OkHttp 代码零改动即可获得完整 Cronet 传输能力
- **降级机制可控**: 保留 OkHttp 处理 WebSocket 和降级兜底，JNI 崩溃可自动回退，风险可控

### Alternatives Considered

| 方案 | 描述 | 优点 | 缺点 | 决策 |
|------|------|------|------|------|
| **替代方案1** | 保持当前 `CronetInterceptor` 拦截器模式不改动 | 零架构改动，风险最低 | 1. 默认值仍为 false，多数用户未享受反爬收益<br>2. 扩展范围受限（HttpURLConnection/Glide/文件上传下载仍走旧栈）<br>3. 不评估桥接层集成度优化 | 否决（作为过渡保留） |
| **替代方案2** | 完全全局替换为 Cronet API，废弃 OkHttp | 架构统一，性能最大化 | 1. Cronet 不支持 WebSocket，需保留 OkHttp<br>2. 现有 OkHttp 生态代码量大，重写成本高<br>3. JNI 崩溃无降级通道<br>4. ProGuard 风险全量暴露 | 否决 |
| **替代方案3** | 引入 play-services-cronet（零体积方案） | APK 几乎零增量，平台自动更新 | 1. 国内设备普遍无 Google Play 服务，不可用<br>2. 依赖 GMS 初始化异步回调，复杂度高<br>3. 版本不可控 | 否决（国内场景不可用） |
| **选定方案** | 默认启用 + 桥接层评估 + 分层降级 + 渐进扩展 | 反爬/弱网收益最大化，代码零改动，降级可控 | APK 体积增加/ProGuard 复杂性/JNI 风险 | **采纳** |

### Drawbacks

选定方案的已知缺点:

1. **APK 体积增加**: 当前动态下载 SO 方案已缓解，但若评估引入 `cronet-okhttp` 桥接依赖会少量增加体积（cronet-okhttp 本身极小，约几十 KB）
2. **ProGuard 复杂性**: 需补充 `cronet-okhttp` 相关 keep 规则，release 包必须真机验证（项目已记录"Cronet 149+ ProGuard 规则缺失导致 release 包订阅源列表加载失败"铁证）
3. **JNI 崩溃风险**: Cronet 通过 JNI 调用 native 层（BoringSSL + QUIC 栈），特定设备/ROM 上可能触发 SIGABRT，需降级机制兜底
4. **桥接层评估成本**: `CronetTransportForOkHttp` 与当前 `CronetInterceptor` 的迁移需评估兼容性，可能存在拦截器链行为差异
5. **WebSocket 仍需 OkHttp**: Cronet 不支持 WebSocket，必须保留 OkHttp 处理 WebSocket 请求
6. **电池消耗**: QUIC 保活连接持续消耗电量，需配置 `idle_connection_timeout_seconds` 平衡
7. **测试覆盖成本**: 需在默认启用/手动关闭两种状态下分别真机验证，覆盖核心网络/视频/DNS/图片/文件传输

### Prior Art

- **Google 官方 Cronet 文档**: `CronetEngine.build()`、`CronetTransportForOkHttp` 桥接层用法
- **Google 官方推荐**: YouTube / Google App / Google Photos / Google Maps / ExoPlayer / gRPC Android 均默认使用 Cronet
- **ExoPlayer Cronet 集成**: 官方支持 Cronet/OkHttp/HttpEngine/默认四种网络栈，Google Play 服务不可用时回退到 DefaultHttpDataSource
- **CronetTransportForOkHttp**: Google 官方桥接库（`com.google.net.cronet:cronet-okhttp`），ExoPlayer/gRPC-Cronet 均采用类似桥接模式
- **反爬方案对比**: curl-impersonate / curl_cffi（BoringSSL）实测反爬成功率 87.9%，印证 BoringSSL 指纹优势
- **Legado 现有实现**: `CronetLoader` 动态下载 SO 方案 + `CronetInterceptor` 拦截器 + 连续 5 次协议错误降级 OkHttp

## Requirements

### REQ-01: isCronet 默认值改为 true
**优先级**: P0
**描述**: `AppConfig.isCronet` 默认值必须改为 `true`，Cronet 作为初始化自动启用模式。保留开关用于紧急关闭（如 JNI 崩溃频发时用户可手动关闭）。

**验收标准**:
- 首次安装 App，`isCronet` 默认为 `true`，Cronet 自动初始化
- 用户可在设置中手动关闭开关，关闭后回退到纯 OkHttp
- 开关状态变更后需重启应用生效（okHttpClient 是 lazy 单例，见 HttpHelper.kt L75 `by lazy`，开关变更不会触发重建）
- 已存在用户的 `isCronet` 偏好值不被覆盖（尊重用户既有选择）

### REQ-02: 评估 CronetTransportForOkHttp 桥接层作为可选优化
**优先级**: P1（降级，源码核实 CronetInterceptor 已获得完整 Cronet 能力）
**描述**: 评估 Google 官方 `CronetTransportForOkHttp` 桥接层作为可选优化（非必须迁移）。源码核实确认 CronetInterceptor 已通过 `proceedWithCronet` → `cronetEngine.newUrlRequestBuilder` 用 Cronet 引擎执行请求，已获得 BoringSSL TLS 指纹 + QUIC + 连接迁移等完整 Cronet 能力。桥接层的主要价值在于让 OkHttp 调度/重试/连接池与 Cronet 深度集成。

**验收标准**:
- 完成 `CronetInterceptor` vs `CronetTransportForOkHttp` 架构对比评估（两者均获得完整 Cronet 能力，桥接层集成度更高）
- 评估桥接层与现有拦截器链（RedirectCacheInterceptor 等）的兼容性
- 评估桥接层对 QUIC 连接迁移/原生 HTTP/3/0-RTT 的支持度
- 给出迁移建议（全量替换 / 渐进迁移 / 保留拦截器）

### REQ-03: 完善降级链（Cronet → fallback → OkHttp）
**优先级**: P0
**描述**: 完善分层降级链，保障 Cronet 不可用时自动回退到 OkHttp，含 JNI 崩溃监控与自动降级。

**验收标准**:
- 降级链：Cronet（动态 SO）→ cronet-fallback → OkHttp
- JNI 崩溃（SIGABRT）监控，崩溃频发时自动降级到 OkHttp
- 保留现有"连续 5 次协议错误降级 OkHttp"机制
- 降级事件记录到 `AppLog`，含降级原因（异常类型/错误码）
- 降级后 WebSocket 请求仍可走 OkHttp

### REQ-04: 扩展 HttpURLConnection 接入 Cronet
**优先级**: P1
**描述**: 通过 `okhttp-urlconnection` 适配，将 HttpURLConnection 底层传输替换为 Cronet 桥接，保持上层 API 不变。

**验收标准**:
- HttpURLConnection 调用底层走 Cronet 桥接（经 OkHttp 适配）
- 上层 API 不变，无代码改动成本
- 验证应用更新检查/WebDav/导入等使用 HttpURLConnection 的功能正常

### REQ-05: 扩展 Glide 图片加载接入 Cronet
**优先级**: P2
**描述**: 评估 Glide 直接接入 Cronet（通过 `OkHttpUrlLoader` + Cronet 桥接注入），替代当前通过 `okHttpClientManga` 间接接入的方式。

**验收标准**:
- Glide 通过 `OkHttpUrlLoader` 注入 OkHttpClient(callFactory=CronetTransport)
- 图片加载获得 QUIC/Brotli/连接迁移能力
- 评估图片 CDN 场景下 TLS 指纹优势（图片 CDN 通常反爬不严苛，收益主要为弱网加载速度）
- 不破坏现有图片加载功能

### REQ-06: 性能监控（Cronet vs OkHttp 对比）
**优先级**: P1
**描述**: 建立性能监控指标，对比 Cronet vs OkHttp 的连接成功率、延迟分布、TLS 握手耗时，为默认启用决策提供数据支撑。

**验收标准**:
- 记录 Cronet 与 OkHttp 的连接成功率对比
- 记录延迟分布（P50/P90/P99）
- 记录 TLS 握手耗时
- 记录协议协商结果（h3/h2/h1 占比）
- 指标可通过 `AppLog` 查看，不泄露敏感信息

### REQ-07: 稳定性保障（ProGuard 规则 + JNI 崩溃监控 + 自动降级）
**优先级**: P0
**描述**: 保障 Cronet 默认启用后的稳定性，包含 ProGuard 规则补充、JNI 崩溃监控、自动降级机制。

**验收标准**:
- 补充 `cronet-okhttp` 相关 ProGuard keep 规则
- release 包真机验证（按项目规范用正式包 `io.legado.miss.app.release`）
- JNI 崩溃（SIGABRT）监控与告警
- 崩溃频发时自动降级到 OkHttp
- release 包订阅源列表加载正常（铁证：Cronet 149+ ProGuard 规则缺失导致该问题）

## Scenarios

### Scenario 1: 首次启动 App，Cronet 自动初始化（后台预初始化）
**前置条件**: 用户首次安装 App，`isCronet` 默认值为 `true`

**主流程**:
1. App 启动，后台预初始化 CronetEngine（不阻塞主线程）
2. `CronetLoader.install` 动态下载/加载 SO 文件
3. 构建全局单例 CronetEngine（enableQuic + enableHttp2 + enableBrotli + 连接迁移 + DoH）
4. OkHttpClient 通过桥接层（或拦截器）接入 Cronet
5. 书源抓取请求走 Cronet，TLS 指纹接近 Chrome，绕过 CDN 检测

**预期结果**: 用户无感享受 Cronet 反爬与弱网收益，h3/h2 协议协商成功

### Scenario 2: Cronet 引擎初始化失败，降级到 OkHttp
**前置条件**: Cronet SO 文件损坏/加载失败/JNI 崩溃

**主流程**:
1. `CronetLoader.install` 调用
2. SO 加载失败或 JNI 崩溃，捕获异常
3. 记录完整异常堆栈（类型+消息+堆栈）到 `AppLog`
4. 降级链：尝试 cronet-fallback → 失败则回退 OkHttp
5. OkHttpClient 不添加 Cronet 桥接/拦截器，使用默认 OkHttp 栈
6. WebSocket 请求仍可走 OkHttp

**预期结果**: 应用功能正常，日志中可查看降级原因，用户无感知

### Scenario 3: 用户手动关闭 isCronet 开关，回退到纯 OkHttp
**前置条件**: 用户在设置中手动关闭 `isCronet` 开关（如遇到 Cronet 兼容性问题）

**主流程**:
1. 用户关闭 `isCronet`
2. OkHttp 不添加 Cronet 桥接/拦截器
3. ExoPlayer 不初始化 `cronetDataFactory`，回退默认 DataSource
4. DohDns 不启用，使用系统 DNS
5. AnalyzeUrl DNS 不使用 Cronet
6. HttpURLConnection/Glide 走 OkHttp 默认栈

**预期结果**: 所有网络请求走 OkHttp 默认栈，无 Cronet 调用，功能正常

### Scenario 4: 书源抓取请求走 Cronet，TLS 指纹绕过 CDN 检测
**前置条件**: `isCronet=true`，Cronet 引擎初始化成功，书源目标站点部署 CDN WAF 检测

**主流程**:
1. 书源规则引擎发起抓取请求
2. 请求经 OkHttp 桥接层路由到 Cronet
3. Cronet 使用 BoringSSL 进行 TLS 握手，ClientHello 指纹接近 Chrome
4. HTTP/2 帧参数（SETTINGS/窗口大小/伪头顺序）接近 Chrome
5. CDN WAF 无法识别为爬虫，请求成功
6. 弱网场景下 QUIC 连接迁移避免网络切换断连

**预期结果**: 抓取成功率显著提升（对标实测 87.9% vs OkHttp 12.3%），弱网下延迟降低约 50%

---

**文档状态**: 🔄 设计中（方向调整 v2）
**下一步**: 等待 design.md 完成 → 进入实施阶段
