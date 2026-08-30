# 嗅探稳定性修复 - 规格说明（V3 修订版）

> 状态：🔄 设计中（V3 修订版）
> 创建日期：2026-07-31
> 修订日期：2026-07-31 16:18（V3：基于渗透式深度审计+主代理源码逐行核实）
> Spec ID：sniff-stability-fix-20260731
> 关联文档：[README.md](./README.md) / [design.md](./design.md) / [tasks.md](./tasks.md)
> 审计报告：[audit-report-v2-deep.md](./audit-report-v2-deep.md)（44个纰漏，V3已全部修复）

## 1. 功能需求

### FR-1：增强现有 RedirectCacheInterceptor（V3：多层重定向）

**需求描述**：修改现有 RedirectCacheInterceptor.kt L67-84，从 `response.request.url` 获取跟随所有重定向后的最终URL（而非仅 Location 头），支持多层重定向（A→B→C）缓存 A→C 映射。

**前提**：源码核实发现 HttpHelper.kt L109 已注册独立拦截器 `RedirectCacheInterceptor`（LruCache 500条+TTL 10分钟+Referer/Cookie维度key），V2 的 FR-1 在 CronetInterceptor 内部新增302缓存会形成双重缓存。V3 改为增强现有实现。

**输入**：
- 原始请求 URL（`Request.url.toString()`）
- Cronet 响应（跟随所有重定向后的最终响应）

**输出**：
- 命中缓存：直接用缓存的最终 URL 构造新请求
- 未命中缓存：正常发起请求，若发生重定向则缓存原始 URL → 最终 URL 映射

**规则**：
- 修改文件：`RedirectCacheInterceptor.kt`（不在 CronetInterceptor 内部新增缓存）
- 修改位置：L67-84 响应处理逻辑
- **V3 核心改进**：使用 `response.request.url` 获取跟随所有重定向后的最终 URL（非仅第一层 302 的 Location）
- 缓存键：原始 URL + Referer 维度 + Cookie 维度（前8字符）
- 缓存值：最终 URL + 过期时间戳
- 缓存容量：500 条（保持现有配置）
- TTL：10 分钟（保持现有配置）
- 仅缓存 HTTP 301/302/307/308 响应
- 原始 URL == 最终 URL 时不缓存（未发生重定向）
- 线程安全：synchronized(cache)（保持现有实现）

**验收标准**：
- [ ] 同一 URL 10 分钟内重复请求，第二次起不再发起 302 往返
- [ ] 多层重定向（A→B→C）缓存 A→C 映射，第二次请求 A 直接用 C
- [ ] 缓存过期后自动失效，重新发起 302 请求获取最新映射
- [ ] 多线程并发访问无竞态条件
- [ ] 日志输出缓存命中/未命中（DEBUG 级别，脱敏 URL）
- [ ] 不在 CronetInterceptor 内部新增302缓存（避免双重缓存）

### FR-2：证书错误降级 OkHttp 重试（V3：前缀匹配+分支前置return）

**需求描述**：在 CronetInterceptor.intercept() 的异常处理中，于 isProtocolError 判定前增加证书错误分支，return 走 OkHttp 重试，不累计降级计数。

**前提**：
- 源码 L208-212 已有 `ERR_CERT_`+`ERR_SSL_` 前缀匹配，但仅用于跳过 printOnDebug，**未用于降级计数豁免**
- 项目内 SSLHelper.kt 已实现 `unsafeTrustManager` + `unsafeSSLSocketFactory` + `unsafeHostnameVerifier`，HttpHelper.kt 的 okHttpClient 已配置信任所有证书

**输入**：
- Cronet 抛出的异常消息

**输出**：
- 证书错误：回退 OkHttp 重试（OkHttp 已信任所有证书，应能成功）
- 非证书错误：按现有降级逻辑处理

**规则**：
- **V3 真正修复**：在 isProtocolError/isHttp2ProtocolError 判定前增加证书错误分支
- 证书错误判定：`isCertificateError(errMsg)` 前缀匹配 `ERR_CERT_` + `ERR_SSL_`（覆盖20+错误码）
- 分支前置 return：`return chain.proceed(original)` 走 OkHttp（避免 ERR_SSL_PROTOCOL_ERROR 误匹配 isHttp2ProtocolError）
- 不累计 Cronet 协议错误计数（证书错误是目标站点问题，非 Cronet 故障）
- 单独去重状态：`lastCertError`/`lastCertErrorTime`（不与协议错误共享 lastLoggedError）
- 日志去重：60s 内相同错误消息只记一次
- 日志级别：WARN
- OkHttp 重试失败时抛出原始 OkHttp 异常，日志输出"OkHttp 降级失败，疑似 TLS 指纹问题"

**验收标准**：
- [ ] ERR_CERT_AUTHORITY_INVALID 错误触发 OkHttp 重试
- [ ] ERR_SSL_PROTOCOL_ERROR 错误触发 OkHttp 重试（不匹配 isHttp2ProtocolError）
- [ ] 证书错误不累计 protocolErrorCount
- [ ] 60s 内相同错误消息只记一次日志
- [ ] OkHttp 重试成功时返回正常响应（复用现有 SSLHelper 信任所有证书）
- [ ] OkHttp 重试失败时抛出 OkHttp 异常（非 Cronet 异常）
- [ ] 日志输出明确标识"证书错误降级 OkHttp"

### FR-3：ERR_NAME_NOT_RESOLVED 不累计 Cronet 降级（V3：host级清理+清熔断）

**需求描述**：检测 ERR_NAME_NOT_RESOLVED 错误，不累计 Cronet 协议错误计数，触发 DoH host级负缓存清理+清熔断状态。

**前提**：源码 DohDns.kt L189 熔断检查优先于 L179 负缓存检查，V2 的 `clearNegativeCache()` 在熔断期间无效。

**输入**：
- Cronet 抛出的异常消息

**输出**：
- NAME_NOT_RESOLVED 错误：不累计降级计数，触发 DoH host级清理+清熔断
- 其他错误：按现有降级逻辑处理

**规则**：
- NAME_NOT_RESOLVED 判定：异常消息包含 `ERR_NAME_NOT_RESOLVED`
- 不累计 protocolErrorCount（根因是 DoH 失败，OkHttp 也会失败）
- 触发 `DohDns.clearNegativeCache(hostname)` host级清理
- **V3 改进**：`clearNegativeCache(hostname)` 同时清 `dohDisabledUntil = 0L`（解决熔断期间清理无效问题）
- host级清理（非全清），避免影响其他域名
- 日志输出明确标识"DoH 失败导致，非 Cronet 问题"
- 日志级别：INFO

**验收标准**：
- [ ] ERR_NAME_NOT_RESOLVED 错误不累计 protocolErrorCount
- [ ] 触发 `DohDns.clearNegativeCache(hostname)` 调用
- [ ] `clearNegativeCache` 同时清 `dohDisabledUntil = 0L`
- [ ] host级清理不影响其他域名
- [ ] 日志输出明确标识"DoH 失败导致，非 Cronet 问题"
- [ ] 不影响其他错误的降级逻辑

### FR-5：Cronet-OkHttp 桥接层评估（V3：仅方案A，评估后推荐不实施）

**需求描述**：评估 `com.google.net.cronet:cronet-okhttp` 依赖方案A（完全替换为 CronetTransport），评估后给出实施建议。

**背景**：嗅探能力下降的核心是 Cronet 降级后 OkHttp 用 Conscrypt TLS 被 CDN 拒绝。V2 设计方案B"仅降级时切换"技术不可行（Call.Factory 是客户端级别配置不能按请求切换），V3 删除方案B。

**输入**：
- cronet-okhttp 依赖（Maven Central 坐标）
- 现有 cronetEngine 实例

**输出**：
- 评估报告：方案A影响清单 + 实施建议

**规则**：
- **V3 删除方案B**：Call.Factory 是客户端级别不能按请求切换
- 评估方案A：完全替换为 CronetTransport
- 方案A影响清单：OkHttp core 失效（缓存/重试/认证/网络拦截器/CookieJar/Response字段缺失）
- 评估兼容性：与现有 SSLHelper / CookieManager / 其他拦截器的兼容性
- 给出明确实施建议

**验收标准**：
- [ ] 方案A影响清单分析完成
- [ ] 与现有 CronetInterceptor 的集成度差异分析完成
- [ ] 代码改动量评估完成
- [ ] 兼容性评估完成
- [ ] 给出明确实施建议（推荐不实施）

**注**：FR-5 为评估任务，实施前需确认依赖可用性。V3 评估结论为推荐不实施。

### FR-6：Cronet 降级策略优化（V3：移除cronetEngineHealthy+独立常量）

**需求描述**：优化 Cronet 降级策略，减少误降级，让 Cronet 尽量保持启用，保留 BoringSSL TLS 指纹能力。

**输入**：
- 现有降级阈值（5 次）
- 现有恢复探测频率（5 分钟）
- Cronet 引擎初始化状态

**输出**：
- 移除 cronetEngineHealthy 标志位
- 新增独立常量 RECOVERY_PROBE_CHECK_INTERVAL_MS
- 降级计数豁免清单扩展

**规则**：
- **V3 移除 cronetEngineHealthy**：依赖现有 `engine == null` 检查，避免死锁
- **V3 独立常量**：新增 `RECOVERY_PROBE_CHECK_INTERVAL_MS = 3min` 仅用于恢复探测触发检查（L96）
- 保留 `RECOVERY_PROBE_INTERVAL_MS = 5min` 用于其他4处降级时长（L239/L261/L277 + 日志）
- 降级计数豁免清单扩展：
  - HTTP/2 协议错误：保持 5 次（已有 1 分钟降级）
  - 连接拒绝：不累计（已实施）
  - NAME_NOT_RESOLVED：不累计（FR-3）
  - 证书错误：不累计（FR-2）
  - 其他协议错误：保持 5 次

**验收标准**：
- [ ] cronetEngineHealthy 标志位移除
- [ ] RECOVERY_PROBE_CHECK_INTERVAL_MS 新增（仅用于恢复探测触发检查）
- [ ] RECOVERY_PROBE_INTERVAL_MS 保持不变（5分钟，用于其他4处降级时长）
- [ ] 降级计数豁免清单扩展（证书错误+NAME_NOT_RESOLVED 不累计）
- [ ] 日志输出降级策略调整信息

### FR-7：图片加载根因分析（V3 新增）

**需求描述**：分析图片加载能力下降的根因，评估 Glide 配置/rateLimiter/ProgressResponseBody 的影响。

**背景**：用户反馈列表图片加载能力下降。源码核实发现图片加载通过 `okHttpClientManga` 接入 Cronet（newBuilder 继承 CronetInterceptor）。

**输入**：
- 真机日志（图片加载失败/超时记录）
- Glide 配置源码
- ReadManga.rateLimiter 实现
- ProgressResponseBody 实现

**输出**：
- 图片加载下降根因分析报告
- 优化建议（如适用）

**规则**：
- 分析 `okHttpClientManga` 的两个特殊拦截器：
  - `ProgressResponseBody`：进度回调开销
  - `ReadManga.rateLimiter`：限流影响
- 分析 Glide 磁盘缓存配置
- 分析连接池配置（okHttpClient 50个空闲连接）
- 分析 Cronet 降级对图片加载的影响
- **任务定义**：评估任务，非代码实施任务

**验收标准**：
- [ ] 图片加载接入 Cronet 路径分析完成
- [ ] ProgressResponseBody 开销评估完成
- [ ] rateLimiter 限流影响评估完成
- [ ] Glide 磁盘缓存配置评估完成
- [ ] 图片加载下降根因分析报告完成
- [ ] 优化建议给出（如适用）

## 2. 非功能需求

### NFR-1：性能

- 302 缓存查询延迟 ≤ 1ms（LruCache 内存查询）
- 302 缓存写入不阻塞请求流程
- 证书错误检测不增加正常请求的处理时间（仅在异常路径执行）
- host级负缓存清理不阻塞请求流程

### NFR-2：稳定性

- 302 缓存并发访问无竞态条件（synchronized）
- 证书错误降级 OkHttp 不引入新的崩溃风险
- DoH host级负缓存清理不影响其他域名的解析
- 降级策略优化不引入新的崩溃风险

### NFR-3：兼容性

- 最低支持 Android API 21（项目 minSdk）
- 不引入新的依赖（FR-5 除外，需评估）
- 不影响现有 Cronet 降级机制
- 不影响现有 SSLHelper 信任所有证书的配置
- 不影响现有 RedirectCacheInterceptor 的其他功能

### NFR-4：可观测性

- 所有修复点输出技术日志（错误码/异常类型/调用栈，不含业务数据）
- 日志脱敏：URL 用路径模式，域名用代号
- 日志去重：相同错误 60s 内只记一次
- 证书错误单独去重状态（不与协议错误共享）

## 3. 验收标准

### 3.1 功能验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 302 缓存命中 | 真机测试：同一 URL 10 分钟内重复请求 | 第二次起无 302 往返，日志输出"RedirectCache: hit" |
| 多层重定向缓存 | 真机测试：多层重定向（A→B→C） | 缓存 A→C 映射，第二次请求 A 直接用 C |
| 证书错误降级 | 真机测试：访问自签名证书站点 | 自动降级 OkHttp（复用 SSLHelper），日志输出"cert error, fallback OkHttp" |
| ERR_SSL_PROTOCOL_ERROR 降级 | 真机测试：触发 ERR_SSL_PROTOCOL_ERROR | 自动降级 OkHttp（不匹配 isHttp2ProtocolError） |
| NAME_NOT_RESOLVED 处理 | 真机测试：模拟 DoH 失败场景 | 不累计降级计数，日志输出"DoH failure, not Cronet issue" |
| host级负缓存清理 | 真机测试：NAME_NOT_RESOLVED 后 | `clearNegativeCache(hostname)` + `dohDisabledUntil=0L` |
| Cronet-OkHttp 桥接层 | 代码评估 | 方案A影响清单+实施建议完成 |
| 降级策略优化 | 真机测试：对比修复前后 Cronet 降级频率 | 修复后降级频率 ≤ 修复前 |
| 嗅探成功率提升 | 真机测试：对比修复前后嗅探成功率 | 修复后嗅探成功率 ≥ 修复前 |
| 图片加载稳定性 | 真机测试：对比修复前后图片加载失败率 | 修复后失败率 ≤ 修复前 |
| 图片加载根因分析 | 代码评估 | FR-7 分析报告完成 |

### 3.2 性能验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 302 缓存查询延迟 | 代码分析 | ≤ 1ms（LruCache 内存查询） |
| 首帧延迟 | 真机测试：视频播放首帧时间 | 修复后首帧延迟 ≤ 修复前 |
| 图片加载延迟 | 真机测试：列表图片加载时间 | 修复后加载延迟 ≤ 修复前 |

### 3.3 稳定性验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 并发安全 | 代码审查 | synchronized 线程安全 |
| 无新增崩溃 | 真机测试：48 小时稳定性测试 | 无新增崩溃（SIGABRT/ANR/Exception） |
| 降级机制完整 | 代码审查 | 现有9+降级机制不受影响 |

### 3.4 兼容性验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| Android API 21 兼容 | 代码审查 | 无 API 21 不支持的 API |
| ProGuard 规则 | release 包真机测试 | 无 R8 移除导致的功能异常 |
| SSLHelper 兼容 | 代码审查 | 不影响现有信任所有证书的配置 |
| RedirectCacheInterceptor 兼容 | 代码审查 | 不影响现有302缓存功能（仅增强） |

## 4. 影响范围

### 4.1 代码变更

| 文件 | 变更类型 | 影响功能 |
|------|---------|---------|
| `app/src/main/java/io/legado/app/help/http/RedirectCacheInterceptor.kt` | FR-1：增强多层重定向（修改 L67-84） | 302 重定向缓存 |
| `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` | FR-2/3/6：证书错误降级+NAME_NOT_RESOLVED处理+降级策略优化 | 所有走 Cronet 的网络请求 |
| `app/src/main/java/io/legado/app/help/http/DohDns.kt` | FR-3：新增 `clearNegativeCache(hostname)` host级清理 | DoH 负缓存清理 |

### 4.2 不影响范围

- ExoPlayer 视频播放（已通过 CronetDataSource 接入 Cronet）
- Glide 图片加载（已通过 okHttpClientManga 间接接入 Cronet）
- WebDav 文件传输（已通过 okHttpClient 接入 Cronet）
- SO 下载（CronetLoader.kt 保留 HttpURLConnection）
- 已实施的 P0-fix（国内 DoH 服务器+冷启动熔断+异步预热）
- 已实施的 P1-2（HTTP/2 1 分钟降级+连接拒绝不累计+震荡抑制）
- 已实施的 SSLHelper（信任所有证书）
- 已实施的 RedirectCacheInterceptor（V3 仅增强，不破坏现有功能）

## 5. 依赖关系

### 5.1 前置依赖

- 已实施 P0-fix（DohDns.kt 国内 DoH 服务器优化）
- 已实施 P1-2（CronetInterceptor.kt HTTP/2 降级优化）
- 已实施 SSLHelper（信任所有证书）
- 已实施 RedirectCacheInterceptor（302 重定向缓存）
- cronet-global-enable-20260731 阶段二/三代码实施完成（Cronet 已默认启用）

### 5.2 后续依赖

- 无（本 Spec 为独立修复，不依赖其他未实施 Spec）

## 6. V2 vs V3 方案对比

| 方面 | V2 方案 | V3 方案 | 修订理由 |
|------|---------|---------|---------|
| FR-1 302 缓存 | 在 CronetInterceptor 内部新增302缓存 | 增强现有 RedirectCacheInterceptor | 源码核实发现现有实现，避免双重缓存 |
| FR-2 证书错误 | 新增前缀匹配 | 前缀匹配已有（L208-212），真正修复是分支前置return | 源码核实发现前缀匹配已存在但仅跳过日志 |
| FR-3 NAME_NOT_RESOLVED | clearNegativeCache() 全清 | host级清理+清 dohDisabledUntil | 源码核实熔断检查优先于负缓存检查 |
| FR-5 桥接层 | 方案A+方案B | 仅方案A，删除方案B | 方案B技术不可行（Call.Factory 客户端级别） |
| FR-6 降级策略 | cronetEngineHealthy+修改RECOVERY_PROBE_INTERVAL_MS | 移除cronetEngineHealthy+新增独立常量 | cronetEngineHealthy死锁+RECOVERY_PROBE_INTERVAL_MS影响4处 |
| FR-7（新增） | 无 | 图片加载根因分析 | 遗漏图片加载下降根因 |
| 核心收益 | 优化网络层稳定性 | **减少误降级+增强302缓存+图片加载分析** | 基于源码核实的精准修复 |
