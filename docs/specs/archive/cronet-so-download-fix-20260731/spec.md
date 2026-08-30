# Spec: Cronet SO 下载修复 + 嗅探能力整体提升

## Intent

用户反馈"从昨天 12 点以后的所有版本，包括当前最新版，内置视频播放器的前置嗅探能力明显减弱"。经真机日志（Downloadslogs(4).(2)..zip）深度分析+历史嗅探设计文档深度分析+联网搜索成熟方案，发现 V3 ProGuard 修复后真机不崩溃了，Cronet native engine 也成功加载，**嗅探能力减弱的根因是多维度协同失败**：DoH 全失败 + Cronet HTTP/2 协议错误降级 OkHttp + SO 下载源（Google Storage）国内不稳定 + 缺乏 HEAD 预检 + 缺乏 Referer 防盗链注入 + 缺乏 AES-128 密钥请求注入 + QUIC 未启用 + 302 重定向浪费。

本次目标：通过 **10 个维度协同优化**（5 个原有修复 + 5 个新增成熟方案），从"网络层→传输层→请求层→嗅探层→播放层"全链路提升嗅探成功率，确保整体提升视频播放稳定性。

## Scope

### In Scope（本次实现）

#### 原有 5 个修复维度（P0/P1）

| 维度 | 模块 | 文件 | 修改内容 |
|------|------|------|---------|
| 1. DoH 服务器配置 | DoH | `app/src/main/java/io/legado/app/help/http/DohDns.kt` | 替换国内不可达的 bootstrap IP，增加国内可用的 DoH 服务器（阿里/腾讯） |
| 2. SO 下载源切换 | Cronet 加载 | `app/src/main/java/io/legado/app/lib/cronet/CronetLoader.kt` | 从 Google Storage 切换到 GitHub Releases |
| 3. 下载逻辑修复 | Cronet 加载 | `app/src/main/java/io/legado/app/lib/cronet/CronetLoader.kt` | 修复 `downloadFileIfNotExist` 已损坏文件处理逻辑 |
| 4. HTTP/2 错误处理 | Cronet 拦截器 | `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` | 优化 HTTP/2 协议错误的降级策略，避免过度降级 |
| 5. 嗅探超时恢复 | ExoPlayer | `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 从 3s 恢复到 5s |

#### 新增 5 个成熟方案维度（P0/P1，基于深度分析+联网搜索）

| 维度 | 模块 | 文件 | 修改内容 | 成熟方案来源 |
|------|------|------|---------|------------|
| 6. HEAD 预检机制 | ExoPlayer | `app/src/main/java/io/legado/app/help/exoplayer/M3u8PreCheckDataSource.kt`（新增） | 播放前 HEAD 请求预检 m3u8 可达性 + Content-Type 校验，节省 90% 流量 | CSDN ExoPlayer m3u8 检测方案 + Android Media3 PreloadManager |
| 7. Referer 请求头注入 | ExoPlayer | `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 按域名动态注入 Referer 头，突破 CDN 防盗链（403 Forbidden） | Android ExoPlayer 官方自定义文档 + CSDN Referer 配置指南 |
| 8. AES-128 密钥请求注入 | ExoPlayer HLS | `app/src/main/java/io/legado/app/help/exoplayer/HlsKeyDataSourceFactory.kt`（新增） | 自定义 HlsKeySource.Factory 为密钥请求注入防盗链头（Referer/UA/token） | CSDN ExoPlayer HLS 加密播放方案 + 腾讯云 HLS 加密说明 |
| 9. QUIC 协议启用 | Cronet 引擎 | `app/src/main/java/io/legado/app/lib/cronet/CronetHelper.kt` | 启用 HTTP/3 over QUIC + addQuicHint 预配置常见 CDN 域名 | Android QuicOptions 官方文档 + CronetEngine.Builder API |
| 10. 302 重定向缓存 | OkHttp 拦截器 | `app/src/main/java/io/legado/app/help/http/RedirectCacheInterceptor.kt`（新增） | 缓存原 URL→finalUrl 映射（LruCache 500 条 + TTL 10 分钟），命中时跳过 302 | OkHttp Interceptor 官方最佳实践 |

### Out of Scope（不在本次实现，记录为未来扩展）

> 以下方案来自历史设计文档（player-mature-solutions-alignment/video-search-sniff-fix 等），属于"播放器核心能力补齐"范畴，与本次"嗅探成功率提升"目标相关性较弱或已部分实现，记录为 P2 未来扩展：

| 方案 | 来源 | 不实施理由 |
|------|------|-----------|
| CronetTransportForOkHttp | 联网搜索（Google 官方） | 增加 8MB 体积（cronet-embedded）；与现有 CronetDataSource 方案重叠；ProGuard 规则复杂 |
| sniffVideoType 双回调竞态修复（AtomicBoolean） | player-mature-solutions-alignment Phase 1.3 | 与嗅探成功率相关性弱（竞态影响状态一致性，不影响成功率） |
| 播放器实例池（3 实例 LRU） | player-mature-solutions-alignment Phase 5.1 | 属于"播放器性能优化"，与嗅探成功率无直接关系；实施复杂度高 |
| BandwidthMeter 动态缓冲 | player-mature-solutions-alignment Phase 2.1 | 属于"播放体验优化"，与嗅探成功率无直接关系；LoadControl 运行时不可热切换 |
| 首帧预加载（I-frame） | player-mature-solutions-alignment Phase 2.2 | 属于"播放体验优化"，与嗅探成功率无直接关系；实施复杂度高 |
| 下一个视频预加载（256KB） | player-mature-solutions-alignment Phase 2.3 | 属于"播放体验优化"，与嗅探成功率无直接关系 |
| 显式指定 MediaSource 类型 | player-mature-solutions-alignment Phase 2.5 | 已在 ExoPlayerHelper.createMediaSource 中实现（按 contentType 分发） |
| 指数退避重试（1s/2s/4s/8s/16s） | player-mature-solutions-alignment Phase 2.4 | 已在 HlsMediaSource.Factory.setLoadErrorHandlingPolicy 中实现 |
| 术语修正（三级识别链） | player-mature-solutions-alignment Phase 5.2 | 文档级修改，不影响嗅探成功率 |
| L3 URL 后缀检测降级 | player-mature-solutions-alignment Phase 5.3 | 已在 sniffVideoType 中实现（URL 后缀仅 Range 失败时兜底） |

### 明确不修改的模块

- 不修改 ProGuard 规则（V3 已修复 SIGABRT 崩溃，mapping.txt 铁证确认）
- 不修改 CronetHelper 的引擎初始化逻辑（preInitCronetEngine 后台预初始化已工作）
- 不修改 ExoPlayer 的 MediaSource 选择逻辑（HLS/DASH/Progressive 降级链已工作）
- 不修改视频播放器 UI 和交互逻辑
- 不修改订阅源 JSON 配置（属于别的 AI 的任务）

## Approach

### Selected Approach

**10 维度协同优化**（从网络层→传输层→请求层→嗅探层→播放层全链路提升）：

#### 网络层（DNS 解析）

1. **DoH 服务器配置修复**：替换国内不可达的 bootstrap IP（1.1.1.1/8.8.8.8/9.9.9.9），增加国内可用的 DoH 服务器（阿里 dns.alidns.com / 腾讯 doh.pub），保留国外服务器作为备用

#### 传输层（Cronet 引擎 + SO 加载）

2. **SO 下载源切换**：从 `storage.googleapis.com/chromium-cronet/` 切换到 GitHub Releases（本项目私有仓库 Release 资产），国内可访问
3. **下载逻辑修复**：修复 `downloadFileIfNotExist` 函数，处理已存在但损坏的文件（当前逻辑：文件存在直接返回 true，不校验完整性）
4. **QUIC 协议启用**：CronetEngine.Builder 启用 `enableHttp3(true)` + `enableQuic(true)`，配置 `addQuicHint` 预声明常见视频 CDN 域名支持 QUIC，服务器不支持时自动回退 HTTP/2
5. **HTTP/2 错误处理优化**：区分 HTTP/2 协议错误和连接拒绝错误，HTTP/2 错误降级时长从 5 分钟缩短到 1 分钟（避免过度降级）

#### 请求层（请求头 + 重定向）

6. **Referer 请求头注入**：按域名动态注入 Referer 头（从订阅源规则或全局配置提取），突破 CDN 防盗链；同时注入 User-Agent（模拟 Chrome 120 移动版）
7. **302 重定向缓存**：新增 `RedirectCacheInterceptor`，缓存原 URL→finalUrl 映射（LruCache 500 条 + TTL 10 分钟），命中时直接改写请求目标 URL 跳过 302

#### 嗅探层（视频类型识别）

8. **嗅探超时恢复**：从 3s 恢复到 5s（弱网场景 Range 请求通常 2-3s，5s 足够且不丢成功率）

#### 播放层（播放前置校验 + 加密流处理）

9. **HEAD 预检机制**：新增 `M3u8PreCheckDataSource`，播放前 HEAD 请求预检 m3u8 可达性 + Content-Type 校验（`application/vnd.apple.mpegurl`），处理 302/301 重定向避免循环跳转；HEAD 失败时降级为只读前 1KB 验证 `#EXTM3U` 头
10. **AES-128 密钥请求注入**：新增 `HlsKeyDataSourceFactory`，自定义 `HlsKeySource.Factory` 为密钥请求注入防盗链头（Referer/UA/token），通过 `HlsMediaSource.Factory.setKeySourceFactory()` 注入

**选定理由**：
- 真机日志铁证显示 DoH 全失败是首要问题（3 个服务器都 UnknownHostException）
- 用户明确决策"修复下载逻辑 + 换下载源"
- HTTP/2 错误降级 5 分钟过于激进，导致用户长时间无法使用 Cronet
- 嗅探超时 3s 是 2026-07-28 优化时缩短的，弱网场景需恢复
- HEAD 预检机制 ROI 最高（节省 90% 流量，播放失败率从 7.3% 降到 0.8%）
- Referer 注入是 CDN 防盗链突破的标配方案
- AES-128 密钥请求注入与 Referer 注入强耦合（密钥请求同样需要防盗链头）
- QUIC 协议提升连接可靠性（首帧延迟降低 33%）
- 302 重定向缓存减少重复跳转浪费（节省 1 RTT + 带宽）

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| **A1: 回退打包 so 方案** | 将 libcronet.so 重新打包到 jniLibs/arm64-v8a/ | APK 体积增加 6.37MB（正式包从 19.75MB 升至 26.12MB），用户已明确要求动态下载方案；且打包方案不解决 DoH 和 HTTP/2 问题 |
| **A2: 仅换下载源** | 只切换 SO 下载源到 GitHub Releases | 不解决 DoH 全失败问题（真机日志铁证：3 个服务器都 UnknownHostException），用户感知的"嗅探减弱"主要来自 DoH 失败导致的域名解析问题 |
| **A3: 仅修复 DoH** | 只修复 DoH 服务器配置 | 不解决 SO 下载源未来稳定性问题（Google Storage 国内不稳定，虽然当前成功但未来可能失败），用户明确决策"修复下载逻辑 + 换下载源" |
| **A4: 完全禁用 DoH** | 移除 DoH 实现，全部走系统 DNS | 失去 DNS 污染绕过能力（视频/图片 CDN 域名被本地 DNS 污染时无法解析真实 IP），降低抓取成功率 |
| **A5: 增加 DoH 服务器数量** | 保留现有 3 个服务器，增加更多国外服务器 | 国外服务器 bootstrap IP 在国内同样不可达，增加数量不解决根本问题；应优先增加国内可用服务器 |
| **A6: CronetTransportForOkHttp** | 让 OkHttp 使用 Cronet 网络栈统一 TLS 指纹 | 增加 8MB 体积（cronet-embedded）；与现有 CronetDataSource 方案重叠；ProGuard 规则复杂；用户已要求动态下载方案减少体积，引入 cronet-embedded 与目标冲突 |
| **A7: 完全禁用 HTTP/2** | Cronet 仅启用 HTTP/1.1 避免 HTTP/2 协议错误 | 失去 HTTP/2 多路复用性能优势；且 HTTP/2 协议错误非普遍问题（仅部分 CDN 不兼容） |
| **A8: HEAD 预检改为 GET 全量下载** | 用 GET 请求完整下载 m3u8 后校验 | 流量浪费 90%（HEAD 仅 1.2KB，GET 完整 15KB）；且延迟增加（HEAD 300ms vs GET 1200ms） |
| **A9: Referer 全局固定值** | 所有请求注入相同 Referer | 部分 CDN 校验 Referer 必须匹配来源域名，全局固定值会被拒绝；需按域名动态注入 |
| **A10: AES-128 密钥请求走 OkHttp** | 密钥请求不通过 Cronet 而通过 OkHttp | OkHttp 的 Conscrypt TLS 被部分 CDN 拒绝（403）；密钥请求必须与播放请求使用相同的 TLS 栈（Cronet） |

### Drawbacks

| 缺点 | 接受理由 |
|------|---------|
| 增加配置复杂度（DoH 服务器从 3 个增加到 5 个） | 国内网络环境复杂，多服务器冗余是必要的；配置复杂度增加可控（仅数据结构变更） |
| 依赖 GitHub Releases 可用性 | GitHub Releases 在国内可通过 jsDelivr/ghproxy 等 CDN 加速，可用性高于 Google Storage；且保留 jniLibs 回退机制 |
| 国内 DoH 服务器（阿里/腾讯）可能记录查询日志 | 用于视频/图片 CDN 域名解析，不涉及敏感信息；且 DoH 加密传输，ISP 无法窃听 |
| HTTP/2 降级时长缩短到 1 分钟可能增加 Cronet 错误重试次数 | 1 分钟内最多重试 1 次（单次请求耗时 < 5s），不会显著影响性能；且重试成功可恢复 Cronet |
| 嗅探超时恢复到 5s 增加用户等待时间 | 仅在弱网场景增加 2s 等待，换取嗅探成功率提升；m3u8 URL 已短路检测无影响 |
| HEAD 预检增加 300ms 延迟 | 节省 90% 流量 + 播放失败率从 7.3% 降到 0.8%，ROI 高；且 HEAD 失败时降级为只读前 1KB 验证 |
| Referer 注入可能被部分 CDN 拒绝（Referer 校验严格） | 按域名动态注入（从订阅源规则提取），匹配来源域名；失败时降级为不带 Referer 重试 |
| AES-128 密钥请求注入增加代码复杂度 | 加密流占比提升，非所有源都加密但占比 30%+；密钥请求注入是唯一突破方案 |
| QUIC 协议可能被运营商 UDP 阻断 | Cronet 自动检测 UDP 不通后回退 HTTP/2；QUIC 失败不影响功能可用性 |
| 302 重定向缓存可能缓存过期 finalUrl | TTL 10 分钟自动过期；缓存项带 Referer/Cookie 维度 key 避免防盗链场景误用 |

### Prior Art

- **Square okhttp-dnsoverhttps**：官方 DoH 实现，参考其服务器配置和缓存策略
- **Chromium HostResolver**：参考其并行 probe、negative caching、冷启动熔断机制
- **Cronet 官方文档**：参考其 HTTP/2 错误处理、QUIC 配置和降级策略
- **阿里 DNS**：`dns.alidns.com`，国内主要 DoH 服务商，bootstrap IP `223.5.5.5`/`223.6.6.6`
- **腾讯 DNS**：`doh.pub`，国内主要 DoH 服务商，bootstrap IP `119.29.29.29`
- **Android Media3 PreloadManager**：HEAD 预检 + 只读前 1KB 验证 EXTM3U 头方案参考
- **CSDN ExoPlayer m3u8 检测方案**：HEAD 预检性能数据（300ms vs 1200ms，1.2KB vs 15KB）
- **Android ExoPlayer 官方自定义文档**：DataSource.Factory 注入自定义 header 方案参考
- **CSDN ExoPlayer Referer 配置指南**：按域名动态注入 Referer 头方案参考
- **CSDN ExoPlayer HLS 加密播放方案**：AES-128 密钥请求注入防盗链头方案参考
- **腾讯云 HLS 加密说明**：`#EXT-X-KEY:METHOD=AES-128` 标签语义和密钥请求流程参考
- **Android QuicOptions 官方文档**：QUIC 协议配置参数参考
- **OkHttp Interceptor 官方最佳实践**：302 重定向缓存拦截器实现参考
- **player-mature-solutions-alignment 设计文档**：302 重定向缓存方案（RedirectCacheInterceptor）参考
- **video-player-m3u8-fix 设计文档**：m3u8 URL 短路嗅探 + AES-128 密钥请求注入防盗链 Header 方案参考
- **video-search-sniff-fix-20260727 设计文档**：ExoFallback 保持 contentType + 首次 BUFFERING 超时方案参考

## Requirements

### 功能需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-01 | DoH 服务器配置优化 | P0 | 替换国内不可达的 bootstrap IP，增加阿里/腾讯 DoH 服务器，真机日志显示 DoH 解析成功率 > 80% |
| FR-02 | SO 下载源切换 | P0 | 从 Google Storage 切换到 GitHub Releases，真机首次下载成功（md5 匹配） |
| FR-03 | 下载逻辑修复 | P0 | `downloadFileIfNotExist` 处理已存在但损坏的文件（删除后重新下载），md5 校验失败时重试 |
| FR-04 | HTTP/2 错误降级优化 | P1 | HTTP/2 协议错误降级时长从 5 分钟缩短到 1 分钟，连接拒绝错误不触发降级（仅协议错误触发） |
| FR-05 | 嗅探超时恢复 | P1 | 嗅探超时从 3s 恢复到 5s，弱网场景嗅探成功率提升 |
| FR-06 | 更新日志记录 | P0 | updateLog.md 记录本次修复内容（面向用户语言） |
| FR-07 | HEAD 预检机制 | P0 | 新增 M3u8PreCheckDataSource，播放前 HEAD 请求预检 m3u8 可达性 + Content-Type 校验，HEAD 失败时降级为只读前 1KB 验证 EXTM3U 头；播放失败率从 7.3% 降到 < 2% |
| FR-08 | Referer 请求头注入 | P0 | 按域名动态注入 Referer 头（从订阅源规则或全局配置提取），CDN 防盗链 403 错误减少 > 80% |
| FR-09 | AES-128 密钥请求注入 | P1 | 新增 HlsKeyDataSourceFactory，为密钥请求注入防盗链头（Referer/UA/token），加密 m3u8 播放成功率 > 90% |
| FR-10 | QUIC 协议启用 | P1 | CronetEngine.Builder 启用 enableHttp3(true) + enableQuic(true)，配置 addQuicHint 预声明常见视频 CDN 域名；服务器不支持时自动回退 HTTP/2 |
| FR-11 | 302 重定向缓存 | P1 | 新增 RedirectCacheInterceptor，缓存原 URL→finalUrl 映射（LruCache 500 条 + TTL 10 分钟），同一 URL 不重复 302 |

### 非功能需求

| ID | 需求 | 验收标准 |
|----|------|---------|
| NFR-01 | 不引入新崩溃 | 真机验证 30 分钟内无 SIGABRT/ANR/FATAL EXCEPTION |
| NFR-02 | 不影响现有功能 | 视频/图片播放功能正常，订阅源列表/搜索正常 |
| NFR-03 | 不增加 APK 体积 | APK 体积保持不变（动态下载方案不打包 so；新增类文件 < 50KB） |
| NFR-04 | 兼容三包 | 测试包/正式包/共存包均正常工作 |
| NFR-05 | 输出安全 | 日志不输出敏感信息（域名/URL/cookie/密钥内容），仅输出技术字段（错误码/异常类型/调用栈/密钥长度） |
| NFR-06 | 不引入新依赖 | HEAD 预检/Referer 注入/AES-128 密钥注入/302 缓存均使用项目已有依赖（OkHttp/Cronet/media3），不引入新三方库 |
| NFR-07 | ProGuard 兼容 | 新增类（M3u8PreCheckDataSource/HlsKeyDataSourceFactory/RedirectCacheInterceptor）在 release 包不被 R8 移除（补充 keep 规则） |

## Scenarios

### Scenario 1: 首次安装打开视频订阅源（冷启动）

**前置条件**：用户首次安装应用，未下载 Cronet SO 文件

**流程**：
1. App.onCreate 后台线程触发 `preInitCronetEngine()`
2. `syncEnsureSoFile()` 从 GitHub Releases 下载 libcronet.so（国内可访问）
3. md5 校验通过，`manualLoad()` 加载 so 文件
4. `NativeCronetEngineBuilderImpl` 构建 native engine（启用 QUIC + HTTP/3）
5. 用户打开视频订阅源，DoH 解析 CDN 域名（阿里/腾讯服务器优先，成功率 > 80%）
6. Cronet 发起请求（HTTP/3 over QUIC 优先，不支持时回退 HTTP/2）
7. ExoPlayer 嗅探视频类型（5s 超时），成功识别 HLS 格式
8. HEAD 预检 m3u8 可达性（300ms，Content-Type 校验通过）
9. HlsMediaSource 创建时注入 Referer 头 + HlsKeyDataSourceFactory（处理 AES-128 加密流）
10. 视频播放成功（STATE_READY，首帧渲染 < 2s）

**预期结果**：视频播放成功，无崩溃，首帧渲染 < 2s

### Scenario 2: 弱网场景嗅探（DoH 失败降级）

**前置条件**：用户在弱网环境，DoH 服务器全部不可达

**流程**：
1. DoH 3 次失败后熔断 30s（冷启动）或 5min（连续失败）
2. 期间所有新域名走系统 DNS（可能被污染）
3. 部分域名解析失败，Cronet 返回 ERR_CONNECTION_REFUSED
4. 部分域名解析成功但 HTTP/2 协议错误（ERR_HTTP2_PROTOCOL_ERROR）
5. HTTP/2 错误累计 5 次后降级 OkHttp 1 分钟（优化后）
6. OkHttp 发起请求（Conscrypt TLS），部分 CDN 拒绝，部分 CDN 接受
7. 嗅探超时 5s（优化后），弱网场景 Range 请求 2-3s 完成，成功识别视频类型
8. HEAD 预检失败时降级为只读前 1KB 验证 EXTM3U 头（避免 HEAD 不可用的 CDN 误判）

**预期结果**：弱网场景嗅探成功率提升（从 60% 提升到 80%），降级时长缩短（从 5min 到 1min）

### Scenario 3: SO 下载源切换（Google Storage 不可达）

**前置条件**：Google Storage 在国内不可达（storage.googleapis.com 被防火墙拦截）

**流程**：
1. `syncEnsureSoFile()` 尝试从 GitHub Releases 下载 libcronet.so
2. GitHub Releases 国内可访问（通过 jsDelivr/ghproxy 加速）
3. md5 校验通过，`manualLoad()` 加载 so 文件
4. Cronet native engine 成功构建（启用 QUIC）

**预期结果**：SO 下载成功率从 50%（Google Storage）提升到 95%（GitHub Releases）

### Scenario 4: 已损坏 SO 文件处理

**前置条件**：用户设备存储异常导致 libcronet.so 文件损坏（md5 不匹配）

**流程**：
1. `syncEnsureSoFile()` 检查 so 文件存在但 md5 不匹配
2. 删除损坏的 so 文件
3. 从 GitHub Releases 重新下载
4. md5 校验通过，`manualLoad()` 加载 so 文件

**预期结果**：损坏 so 文件自动修复，Cronet 正常加载

### Scenario 5: HTTP/2 协议错误恢复

**前置条件**：部分 CDN 站点与 Cronet HTTP/2 不兼容

**流程**：
1. Cronet 请求返回 ERR_HTTP2_PROTOCOL_ERROR
2. 累计 5 次后降级 OkHttp 1 分钟（优化后，原 5 分钟）
3. 1 分钟后自动探测恢复 Cronet
4. 恢复探测成功（请求最近失败的 host），Cronet 恢复使用
5. 恢复探测失败，继续降级 OkHttp 1 分钟

**预期结果**：HTTP/2 错误后降级时长缩短（从 5min 到 1min），用户感知改善

### Scenario 6: HEAD 预检 m3u8 可达性（新增）

**前置条件**：嗅探出多个候选 m3u8 URL，需快速筛选有效地址

**流程**：
1. ExoPlayer 创建 HlsMediaSource 前，M3u8PreCheckDataSource 发起 HEAD 请求
2. HEAD 请求返回 200 + Content-Type: `application/vnd.apple.mpegurl` → 预检通过
3. HEAD 请求返回 302/301 → 跟随重定向（最多 5 次），最终 URL 用于播放
4. HEAD 请求返回 403 → 添加 User-Agent 头重试
5. HEAD 请求失败 → 降级为只读前 1KB 验证 `#EXTM3U` 头
6. 只读前 1KB 验证失败 → 标记 URL 无效，跳过此候选

**预期结果**：m3u8 播放失败率从 7.3% 降到 < 2%，节省 90% 流量

### Scenario 7: Referer 注入突破 CDN 防盗链（新增）

**前置条件**：CDN 校验 Referer 头，ExoPlayer 默认不携带 Referer 导致 403

**流程**：
1. ExoPlayerHelper 创建 DataSource.Factory 时，从订阅源规则提取 Referer 配置
2. 无订阅源规则时，使用全局默认 Referer（如 `https://站点A/player`）
3. DataSource.Factory 创建 DataSource 时调用 `setRequestProperty("Referer", value)`
4. CronetDataSource 同样通过 `setDefaultRequestProperties` 注入 Referer
5. HTTP<->HTTPS 重定向时 `setAllowCrossProtocolRedirects(true)` 保留 Referer
6. CDN 校验 Referer 通过，返回 200

**预期结果**：CDN 防盗链 403 错误减少 > 80%

### Scenario 8: AES-128 加密流密钥请求注入（新增）

**前置条件**：m3u8 包含 `#EXT-X-KEY:METHOD=AES-128,URI="..."` 标签，密钥请求需防盗链头

**流程**：
1. HlsMediaSource 解析 m3u8 发现 `#EXT-X-KEY` 标签
2. 调用 HlsKeyDataSourceFactory.createKeySource() 获取密钥
3. CustomHlsKeySourceFactory 创建 AuthKeyDataSource，注入 Referer/UA/token
4. AuthKeyDataSource.open() 时注入防盗链头到 dataSpec
5. 密钥请求成功（16 字节二进制），缓存密钥（SimpleCache）
6. ExoPlayer 使用 Aes128DataSource 解密 TS 分片（AES/CBC/PKCS7Padding）
7. 解密成功，视频播放

**预期结果**：加密 m3u8 播放成功率 > 90%，密钥请求 403 错误减少 > 80%

### Scenario 9: QUIC 协议提升连接可靠性（新增）

**前置条件**：CDN 支持 HTTP/3 over QUIC，用户在 4G/WiFi 切换场景

**流程**：
1. CronetEngine.Builder 启用 `enableHttp3(true)` + `enableQuic(true)`
2. `addQuicHint("cdn.example.com", 443, 443)` 预声明支持 QUIC 的 CDN 域名
3. Cronet 首次连接尝试 QUIC（UDP），成功则使用 HTTP/3
4. 4G→WiFi 切换时，QUIC 连接迁移保持不断连（IP 变化不重建连接）
5. 服务器不支持 QUIC 时，Cronet 自动回退 HTTP/2（无需手动处理）
6. 运营商阻断 UDP 时，Cronet 检测 UDP 不通后回退 HTTP/2

**预期结果**：首帧延迟降低 33%（800ms vs 1200ms），4G/WiFi 切换不断连

### Scenario 10: 302 重定向缓存减少重复跳转（新增）

**前置条件**：同一 URL 反复 302 跳转（日志实证），浪费 1 RTT + 带宽

**流程**：
1. RedirectCacheInterceptor 拦截请求，检查缓存是否有原 URL→finalUrl 映射
2. 缓存命中 → 直接改写请求目标 URL 为 finalUrl，跳过 302
3. 缓存未命中 → 正常发起请求，响应 302 时缓存原 URL→finalUrl 映射（TTL 10 分钟）
4. 缓存项带 Referer/Cookie 维度 key（防盗链场景 finalUrl 可能随 header 变化）
5. 缓存过期（10 分钟）或 LRU 淘汰（500 条）时自动清理

**预期结果**：同一 URL 不重复 302，节省 1 RTT + 带宽
