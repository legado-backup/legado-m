# 需求规格（sniff-result-pipeline-fix-20260731）

## 功能需求

### FR-1: 移除 extractVideoUrlForEpisode 外层 withTimeoutOrNull 抢占（P0）

**需求描述**：移除 `extractVideoUrlForEpisode` 的外层 `withTimeoutOrNull(12000L)`，让内层各层超时自然累加，避免抢占式取消导致 R5 抓包命中结果丢失。

**现状问题**：
- 文件：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` L507
- 外层 `withTimeoutOrNull(12000L)` 是抢占式取消，会取消整个协程树
- 第一层 MacCMS 6s + 第三层 R5 6s = 12s，外层超时与内层超时窗口重叠
- R5 命中后 `block.resume(response)` 在工作线程调用，需 Dispatcher 调度到 IO 线程（1-15ms 延迟）
- 调度期间外层超时先触发，取消整个协程树，命中结果丢失

**真机日志铁证**：
- 17:56:45.887 R5 网络抓包启动（logcat.txt L10231）
- 17:56:45.907 R5 抓包命中（工作线程）（logcat.txt L10232）
- 17:56:45.922 extractVideoUrlForEpisode timeout(12s) 返回 null（logcat.txt L10233）
- 17:56:45.923 触发 WebView 降级（logcat.txt L10234）
- 命中与超时间隔仅 15ms

**修复方案**：
- 移除 L507 的 `withTimeoutOrNull(12000L) { ... } ?: run { ... }` 包裹
- 保留内层各层超时：第一层 MacCMS 6s（L522）+ 第三层 R5 6s（默认 R5_TIMEOUT）
- 保留 L570 的超时日志（改为第三层失败日志，不再有"12s 总超时"概念）
- 保留 CancellationException 守卫（L541-543, L559-561）

**验收标准**：
- 源码中 `extractVideoUrlForEpisode` 不再包含 `withTimeoutOrNull(12000L)`
- 真机日志中不出现"extractVideoUrlForEpisode timeout (12s), 返回null"
- 真机日志中 R5 抓包命中后立即出现"第三层网络抓包成功"

### FR-2: R5 抓包命中后切 UI 线程同步 resume（P0）

**需求描述**：在 `BackstageWebView.shouldInterceptRequest` 中，命中后切到 UI 线程同步调用 `callback?.onResult(response)`，减少协程 resume 调度延迟。

**现状问题**：
- 文件：`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` L332-364
- `shouldInterceptRequest` 在 chromium 工作线程调用（chromium 设计）
- L350 `callback?.onResult(response)` → `block.resume(response)` 在工作线程调用
- 协程 resume 需要 Dispatcher 调度到 IO 线程，调度延迟 1-15ms
- 调度期间外层超时可能先触发（配合 FR-1 后此问题缓解，但仍需优化）

**真机日志铁证**：
- 17:56:45.907 "R5网络抓包命中(工作线程), post到UI线程执行destroy"（logcat.txt L10232）
- 当前 destroy 已切 UI 线程，但 `callback?.onResult(response)` 仍在工作线程

**修复方案**：
- L350 `callback?.onResult(response)` 改为切 UI 线程同步执行
- 复用现有 `mHandler.post { }` 机制，将 `callback?.onResult(response)` 与 `destroy()` 合并到同一个 UI 线程 post
- 保留 `onLoadResource` 路径（L408-419）不变（已在 UI 线程）

**验收标准**：
- 源码中 `shouldInterceptRequest` 的 `callback?.onResult(response)` 在 `mHandler.post { }` 内执行
- 真机日志中"R5网络抓包命中(工作线程)"改为"R5网络抓包命中(切UI线程)"或类似描述
- 真机测试中 R5 命中后 5ms 内出现"第三层网络抓包成功"

### FR-3: OkHttp HTTP/2 StreamReset 容错（P1）

**需求描述**：OkHttp HTTP/2 层的 `StreamResetException` 发生时，淘汰连接池中该 host 的连接并重试一次，避免图片加载链中断。

**现状问题**：
- 文件：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt` L75-167
- OkHttpClient 未显式配置 `.protocols()`，默认启用 HTTP/2
- `retryOnConnectionFailure(true)` 对 HTTP/2 流重置无效（流重置不可重试，连接仍可用）
- 连接池中的连接未被淘汰，下次请求复用同一连接仍失败
- `OkHttpStreamFetcher.onFailure`（L130-132）直接 `onLoadFailed`，无重试
- 失败 URL 写入 `failUrl` LruCache（L139），后续同 URL 请求被短路（L64-67）

**真机日志铁证**：
- 17:57:12.587 `okhttp3.internal.http2.StreamResetException: stream was reset: CANCEL`（logcat.txt L13299）
- 调用栈指向 `BitmapFactory.nativeDecodeStream`（图片解码链中断）
- 17:58:19.299 再次出现 StreamResetException（logcat.txt L20640）

**修复方案**：
- 在 `okHttpClient` 中新增 Interceptor，捕获 `StreamResetException`
- 命中后调用 `chain.call().cancel()` 淘汰当前连接 + `connectionPool.evictAll()` 清理该 host 连接
- 重试一次原请求（标记 `response.priorResponse` 避免无限重试）
- 在 `OkHttpStreamFetcher.onFailure` 中识别 `StreamResetException`，不写入 `failUrl`（避免后续短路）

**验收标准**：
- 源码中 `okHttpClient` 配置含 StreamReset 容错 Interceptor
- 源码中 `OkHttpStreamFetcher.onFailure` 识别 `StreamResetException` 不写入 `failUrl`
- 真机日志中 StreamResetException 后出现"StreamReset 重试"日志
- 真机测试中图片加载 StreamResetException 后重试成功

### FR-4: lastFailedHostHint 探测超时清除（P2）

**需求描述**：`lastFailedHostHint` 增加超时清除机制，避免 `lastFailedHostHint` 对应 host 长时间无请求时探测永远不触发。

**现状问题**：
- 文件：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` L81, L170-177
- `lastFailedHostHint` 在协议错误时赋值（L313-316），恢复成功后清除（L233）
- 若 `lastFailedHostHint` 对应 host 长时间无请求（如视频源已切换），探测永远不会触发
- 降级状态持续，所有非失败 host 的请求走 OkHttp

**真机日志铁证**：
- 263 次"探测跳过非失败 host"日志（子代理报告）
- 全部针对同一对 host（www***, 087***）
- 10 秒内重复 15+ 次

**修复方案**：
- 新增 `lastFailedHostHintTimeMs` 记录 `lastFailedHostHint` 赋值时间戳
- 新增常量 `HINT_TIMEOUT_MS = 5 * 60 * 1000L`（5 分钟超时）
- 在 L170-177 检查前判断：`if (hint != null && now - lastFailedHostHintTimeMs > HINT_TIMEOUT_MS)` 则清除 hint
- 清除后允许任意 host 探测

**验收标准**：
- 源码中新增 `lastFailedHostHintTimeMs` 和 `HINT_TIMEOUT_MS` 常量
- 真机日志中"探测跳过非失败 host"不超过 5 分钟持续
- 真机测试中 `lastFailedHostHint` 超时 5 分钟后清除

### FR-5: DoH 备用服务器清理（P2）

**需求描述**：移除 DoH 配置中不可达的备用服务器，减少无效日志噪音。

**现状问题**：
- 文件：`app/src/main/java/io/legado/app/help/http/DohDns.kt` L58-66
- server#1（阿里 DNS）全部成功
- server#2（腾讯 DNS）UnknownHostException
- server#3（Cloudflare）UnknownHostException
- server#4（Google）UnknownHostException
- server#5（Quad9）UnknownHostException
- 并行查询 server#1 成功就返回，整体功能正常，但产生大量无效日志

**真机日志铁证**：
- 17:56:36.197-200 server#2/3/4/5 全部 UnknownHostException（logcat.txt L9954-9963）
- 17:56:41.031-036 server#2/3/4/5 全部 UnknownHostException（logcat.txt L10151-10154）
- 17:56:49.150-159 server#2/3/4/5 全部 UnknownHostException（logcat.txt L10345-10347）

**修复方案**：
- 移除 server#3（Cloudflare）、server#4（Google）、server#5（Quad9）
- 保留 server#1（阿里 DNS）和 server#2（腾讯 DNS）作为国内双保险
- 调整 `parallelLookup` 的 `clients.size` 相关逻辑（容量适配）

**验收标准**：
- 源码中 `DOH_SERVERS` 只保留 2 个服务器（阿里 + 腾讯）
- 真机日志中不出现 server#3/4/5 的 UnknownHostException
- 真机测试中 DoH 解析成功率 ≥ 99%（server#1 失败时 server#2 兜底）

## 非功能需求

### NFR-1: 性能

- `extractVideoUrlForEpisode` 移除外层超时后，总耗时不超过 12s（第一层 6s + 第三层 6s 自然累加）
- StreamReset 容错 Interceptor 不增加正常请求开销（只在异常路径触发）
- `lastFailedHostHint` 超时检查不增加额外开销（只读取时间戳对比）

### NFR-2: 兼容性

- 不影响现有 Cronet 降级机制（降级阈值/恢复探测间隔保持现状）
- 不影响 `extractVideoUrlForEpisode` 的调用方（返回值类型不变，仍是 `String?`）
- 不影响 `OkHttpStreamFetcher` 的失败 URL 缓存机制（只对 StreamResetException 例外）
- 不影响 DoH 主服务器（阿里 DNS 工作正常）

### NFR-3: 可观测性

- 保留现有日志格式（"extractVideoUrlForEpisode: ..."）
- 新增日志：StreamReset 重试时输出"StreamReset 重试, host=***"
- 新增日志：`lastFailedHostHint` 超时清除时输出"hint 超时清除, 放行任意 host 探测"
- 修改日志：R5 命中后从"工作线程"改为"切UI线程"

### NFR-4: 安全

- 日志只输出技术结论，不输出源名称/域名/URL/cookie
- host 前缀只保留前 3 字符 + `***`（如 `www***`）
- URL 用 `sanitizeUrl()` 脱敏

## 约束条件

1. **不修改 Cronet 降级机制核心逻辑**：降级阈值/恢复探测间隔/震荡抑制保持现状
2. **不修改 Cronet SO 下载机制**：已稳定工作
3. **不修改图片解码器**：HWUI "unimplemented" 是系统层问题
4. **不重构整个嗅探架构**：只修复结果管线断裂点
5. **保持现有 CancellationException 守卫**：L541-543, L559-561 的 CancellationException 传播必须保留
6. **输出安全**：日志只输出技术结论，不输出源名称/域名/URL/cookie

## 验收标准汇总

| 编号 | 验收项 | 验证方法 |
|------|--------|---------|
| AC-1 | `extractVideoUrlForEpisode` 不含 `withTimeoutOrNull(12000L)` | 源码审查 |
| AC-2 | 真机日志无"extractVideoUrlForEpisode timeout (12s)" | 真机测试 |
| AC-3 | `shouldInterceptRequest` 的 `callback?.onResult` 在 `mHandler.post` 内 | 源码审查 |
| AC-4 | 真机日志 R5 命中后 5ms 内出现"第三层网络抓包成功" | 真机测试 |
| AC-5 | `okHttpClient` 含 StreamReset 容错 Interceptor | 源码审查 |
| AC-6 | `OkHttpStreamFetcher.onFailure` 识别 StreamReset 不写入 failUrl | 源码审查 |
| AC-7 | 真机日志 StreamResetException 后出现"StreamReset 重试" | 真机测试 |
| AC-8 | `lastFailedHostHintTimeMs` 和 `HINT_TIMEOUT_MS` 新增 | 源码审查 |
| AC-9 | 真机日志"探测跳过非失败 host"不超过 5 分钟持续 | 真机测试 |
| AC-10 | `DOH_SERVERS` 只保留 2 个服务器 | 源码审查 |
| AC-11 | 真机日志无 server#3/4/5 的 UnknownHostException | 真机测试 |
| AC-12 | 嗅探成功率 ≥ 99% | 真机测试统计 |
| AC-13 | 测试包+正式包 BUILD SUCCESSFUL | 编译验证 |
| AC-14 | mapping.txt 关键类全部保留 | mapping.txt 审查 |
