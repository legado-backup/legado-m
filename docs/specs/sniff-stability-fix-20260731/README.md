# 嗅探稳定性修复（sniff-stability-fix-20260731）

> 状态：🔄 设计中（V3 修订版）
> 创建日期：2026-07-31
> 修订日期：2026-07-31 16:18（V3：基于渗透式深度审计+主代理源码逐行核实）
> Spec ID：sniff-stability-fix-20260731
> 关联文档：[spec.md](./spec.md) / [design.md](./design.md) / [tasks.md](./tasks.md)
> 审计报告：[audit-report-v2-deep.md](./audit-report-v2-deep.md)（44个纰漏，V3已全部修复）

## V3 修订说明

V2 设计文档经渗透式深度审计（44个纰漏）+ 主代理源码逐行核实后，发现以下关键问题：

1. **FR-1 与现有 RedirectCacheInterceptor 重复**：源码核实发现 HttpHelper.kt L109 已注册独立拦截器 `RedirectCacheInterceptor`（LruCache 500条+TTL 10分钟+Referer/Cookie维度key），V2 的 FR-1 在 CronetInterceptor 内部新增302缓存会形成双重缓存。V3 改为"增强现有 RedirectCacheInterceptor"。
2. **FR-2 审计报告不准确**：源码 L208-212 已有 `ERR_CERT_`+`ERR_SSL_` 前缀匹配，但仅用于跳过 printOnDebug，**未用于降级计数豁免**。V3 真正修复是"在 isProtocolError 前增加证书错误分支 return"。
3. **FR-3 熔断期间清理无效**：源码 DohDns.kt L189 熔断检查优先于 L179 负缓存检查，V2 的 `clearNegativeCache()` 在熔断期间无效。V3 增加 `dohDisabledUntil = 0L`。
4. **FR-5 方案B技术不可行**：OkHttp 的 `Call.Factory` 是客户端级别配置，不能按请求切换。V3 删除方案B。
5. **FR-6 cronetEngineHealthy 死锁**：V2 初始化为 false，仅在 Cronet 成功后置 true，永远走 OkHttp。V3 移除该标志位。
6. **FR-6 RECOVERY_PROBE_INTERVAL_MS 影响4处**：源码核实 L96/L239/L261/L277 共4处使用，修改会影响所有降级时长。V3 新增独立常量 `RECOVERY_PROBE_CHECK_INTERVAL_MS`。
7. **新增 FR-7**：图片加载根因分析（Glide 配置/rateLimiter/ProgressResponseBody）。

## 背景与问题

用户真机测试反馈（2026-07-31 15:11）：
1. **嗅探能力有所下降**——内置视频播放器前置嗅探成功率降低
2. **列表图片加载能力下降**——RSS 订阅源列表封面加载变慢或失败

深度分析真机日志 + 源码核实后定位 **7 个根因**：

| # | 根因 | 影响 | 已实施修复 | V3 待实施修复 |
|---|------|------|-----------|-----------|
| R1 | DoH 全部服务器失败 | DNS 解析延迟 2-3 秒/请求 | P0-fix：国内 DoH 服务器置顶 + 冷启动 30s 熔断 + 异步预热 + 负缓存 + IDN 旁路 | 无（已充分） |
| R2 | Cronet 频繁降级 OkHttp | 丧失 TLS 指纹模拟能力，CDN 拒绝连接 | P1-2：HTTP/2 降级 1 分钟 + 连接拒绝不累计 + 震荡抑制 | **FR-6：降级策略优化（减少误降级）** |
| R3 | 302 重定向缓存仅一层 | 多层重定向（A→B→C）仍需 B→C 往返 | RedirectCacheInterceptor（现有，仅 Location 头） | **FR-1：增强现有 RedirectCacheInterceptor（多层重定向）** |
| R4 | 证书错误未豁免降级计数 | 源码已有前缀匹配跳过日志，但未跳过降级计数 | 部分（L208-212 跳过 printOnDebug） | **FR-2：证书错误降级 OkHttp 重试 + 不累计降级** |
| R5 | ERR_NAME_NOT_RESOLVED 累计降级 | DoH 失败导致 DNS 解析失败，被误判为 Cronet 协议错误 | 部分（连接拒绝不累计） | **FR-3：NAME_NOT_RESOLVED 不累计 + host级清理 DoH** |
| R6 | TLS 指纹问题 | Cronet 降级 OkHttp 后，OkHttp 用 Conscrypt TLS 被 CDN 拒绝 | 无 | **FR-5：评估 Cronet-OkHttp 桥接层（仅方案A，评估后推荐不实施）** |
| R7 | 图片加载下降（V3 新增） | Glide 配置/rateLimiter/ProgressResponseBody 影响 | 无 | **FR-7：图片加载根因分析** |

## V3 修复方案概要

### 已实施修复（P0-fix + P1-2 + SSLHelper + RedirectCacheInterceptor，无需重复实施）

**P0-fix（DohDns.kt）**：
- 国内 DoH 服务器置顶 + 冷启动首次失败立即熔断 30s + 异步预热探测恢复
- 负缓存 30s + IDN 旁路 + 回环/保留地址过滤

**P1-2（CronetInterceptor.kt）**：
- HTTP/2 协议错误降级 1 分钟 + 连接拒绝不累计降级 + 震荡抑制 + lastFailedHostHint

**SSLHelper.kt（已实施）**：
- `unsafeTrustManager` + `unsafeSSLSocketFactory` + `unsafeHostnameVerifier`
- HttpHelper.kt 的 okHttpClient 已配置信任所有证书
- **结论**：OkHttp 降级后证书错误应能自动绕过，FR-2 无需新增 TrustManager

**RedirectCacheInterceptor.kt（已实施，V3 增强）**：
- LruCache 500 条 + TTL 10 分钟 + Referer/Cookie 维度 key
- 命中改写 URL 跳过 302 往返
- **V3 增强点**：修改 L67-84 从 `response.request.url` 获取多层重定向最终URL（而非仅 Location 头）

### V3 待实施修复（本 Spec 重点）

**FR-1：增强现有 RedirectCacheInterceptor（V3 改进：多层重定向）**
- 不在 CronetInterceptor 内部新增302缓存（避免双重缓存）
- 修改 RedirectCacheInterceptor.kt L67-84，从 `response.request.url` 获取跟随所有重定向后的最终URL
- 命中缓存走 `chain.proceed(redirectedRequest)`，自动触发后续 CronetInterceptor（收到 finalUrl），自然走 Cronet 引擎保留 BoringSSL TLS 指纹
- 缓存容量：500 条；TTL：10 分钟（保持现有配置）

**FR-2：证书错误降级 OkHttp 重试（V3：前缀匹配+分支前置return）**
- 源码 L208-212 已有 `ERR_CERT_`+`ERR_SSL_` 前缀匹配跳过 printOnDebug
- **V3 真正修复**：在 isProtocolError 判定前增加证书错误分支，`return chain.proceed(original)` 走 OkHttp
- 不累计降级计数（证书错误是目标站点问题，非 Cronet 故障）
- 单独去重状态 `lastCertError`/`lastCertErrorTime`（不与协议错误共享）
- **注**：如果 OkHttp 重试仍然失败，说明是 TLS 指纹问题，日志输出明确标识

**FR-3：ERR_NAME_NOT_RESOLVED 不累计 Cronet 降级（V3：host级清理+清熔断）**
- 检测 ERR_NAME_NOT_RESOLVED 错误（DNS 解析失败）
- 不累计 Cronet 协议错误计数
- 触发 `DohDns.clearNegativeCache(hostname)` host级清理
- **V3 改进**：同时清 `dohDisabledUntil = 0L`（解决熔断期间清理无效问题）

**FR-5：Cronet-OkHttp 桥接层评估（V3：仅方案A，评估后推荐不实施）**
- 评估 `com.google.net.cronet:cronet-okhttp` 依赖
- **V3 删除方案B**：Call.Factory 是客户端级别配置，不能按请求切换
- **方案A影响清单**：OkHttp core 失效（缓存/重试/认证/网络拦截器/CookieJar）
- **评估结论**：推荐不实施（现有 CronetInterceptor 已获得完整 Cronet 能力，FR-1 V3 改进后缓存命中走 Cronet 保留 TLS 指纹）

**FR-6：Cronet 降级策略优化（V3：移除cronetEngineHealthy+独立常量）**
- **V3 移除 cronetEngineHealthy**：依赖现有 `engine == null` 检查，避免死锁
- **V3 独立常量**：新增 `RECOVERY_PROBE_CHECK_INTERVAL_MS = 3min` 仅用于恢复探测触发检查
- 保留 `RECOVERY_PROBE_INTERVAL_MS = 5min` 用于其他4处降级时长（L96/L239/L261/L277）
- 降级计数豁免清单扩展：HTTP/2 协议错误保持5次 + 连接拒绝不累计 + NAME_NOT_RESOLVED 不累计（FR-3） + 证书错误不累计（FR-2）

**FR-7：图片加载根因分析（V3 新增）**
- 图片加载通过 `okHttpClientManga` 接入 Cronet（newBuilder 继承 CronetInterceptor）
- 分析 `ProgressResponseBody` 进度回调开销
- 分析 `ReadManga.rateLimiter` 限流影响
- 分析 Glide 磁盘缓存配置
- **任务定义**：评估任务，非代码实施任务

## 影响范围

### 代码变更范围

| 文件 | 变更类型 | 影响功能 |
|------|---------|---------|
| `app/src/main/java/io/legado/app/help/http/RedirectCacheInterceptor.kt` | FR-1：增强多层重定向（修改 L67-84） | 302 重定向缓存 |
| `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` | FR-2/3/6：证书错误降级+NAME_NOT_RESOLVED处理+降级策略优化 | 所有走 Cronet 的网络请求 |
| `app/src/main/java/io/legado/app/help/http/DohDns.kt` | FR-3：新增 `clearNegativeCache(hostname)` host级清理 | DoH 负缓存清理 |

### 不影响范围

- ExoPlayer 视频播放（已通过 CronetDataSource 接入 Cronet）
- Glide 图片加载（已通过 okHttpClientManga 间接接入 Cronet）
- WebDav 文件传输（已通过 okHttpClient 接入 Cronet）
- SO 下载（CronetLoader.kt 保留 HttpURLConnection）
- 已实施的 P0-fix + P1-2 + SSLHelper + RedirectCacheInterceptor

## 验收标准

详见 [spec.md#验收标准](./spec.md#验收标准)

## 任务执行顺序

详见 [tasks.md](./tasks.md)

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| FR-1 增强后多层重定向缓存失效 | 中 | TTL 10 分钟 + 仅缓存 301/302/307/308 响应 + 单元测试覆盖 |
| FR-2 证书错误降级 OkHttp 仍失败 | 中 | 说明是 TLS 指纹问题，日志输出建议启用 FR-5 |
| FR-3 host级清理影响其他域名 | 低 | host级清理（非全清），不影响其他域名 |
| FR-6 恢复探测频率缩短导致震荡 | 低 | 仅缩短恢复探测触发检查，保持其他降级时长不变 |
| 真机测试环境差异 | 中 | 测试包+正式包双重验证 |
