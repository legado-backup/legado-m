# 嗅探结果管线修复（sniff-result-pipeline-fix-20260731）

## 功能概述

修复 V3 嗅探稳定性修复（sniff-stability-fix-20260731）后仍然存在的"嗅探能力下降"和"图片加载失败"问题。真机日志铁证显示：之前归因于"Cronet 降级导致 TLS 指纹被拒"的结论完全错误，真实根因是 **嗅探结果管线断裂** + **OkHttp HTTP/2 StreamReset 无容错**。

## 背景

### 问题现象

用户反馈 V3 修复后"整体感觉差强人意，太牵强了"，真机日志（`Downloadslogs(7).(2)..zip`）铁证显示：

| 时间点 | 事件 | 铁证行号 |
|--------|------|---------|
| 17:56:45.887 | R5 网络抓包启动，timeout=6000ms | logcat.txt L10231 |
| 17:56:45.907 | R5 抓包命中（工作线程），post 到 UI 线程执行 destroy | logcat.txt L10232 |
| 17:56:45.922 | extractVideoUrlForEpisode timeout(12s) 返回 null | logcat.txt L10233 |
| 17:56:45.923 | 触发 WebView 降级 | logcat.txt L10234 |
| 17:57:12.587 | StreamResetException: stream was reset: CANCEL | logcat.txt L13299 |
| 17:57:03.259 | SocketException: Connection reset | logcat.txt L13044 |

**核心矛盾**：R5 抓包命中（17:56:45.907）与 extractVideoUrlForEpisode 超时返回 null（17:56:45.922）仅相隔 **15ms**，抓包结果未回灌到调用方。

### 之前方案（sniff-degradation-fix-20260731）的错误前提

| 之前结论 | 真实情况 |
|---------|---------|
| Cronet 降级导致嗅探下降 | 搜索"协议错误/降级"等关键词 **No matches found**，Cronet 未降级 |
| 17:48-17:50 ERR_CONNECTION_CLOSED 累计 5 次触发降级 | logcat 中无 ERR_CONNECTION_CLOSED 日志 |
| OkHttp 的 Conscrypt TLS 被 CDN 拒绝 | 实际是 OkHttp HTTP/2 层 StreamResetException，与 TLS 指纹无关 |
| 嗅探成功率从 100% 降至 60% | 实际成功率 96.1%（74 次成功，3 次失败），但 3 次失败全部源于抓包结果回灌断裂 |

## 真实根因链（源码 + 日志双重铁证）

### 根因一：外层超时抢占内层超时（P0）

```
extractVideoUrlForEpisode（VideoUrlExtractor.kt L507）
  └─ withTimeoutOrNull(12000L)  ← 外层总超时 12s，抢占式取消
       ├─ 第一层 MacCMS 解析（withTimeoutOrNull(6000L)）
       └─ 第三层 R5 网络抓包（extractWithWebView → BackstageWebView.getStrResponse）
            └─ withTimeout(6000L)  ← 内层 R5 超时 6s
                 └─ suspendCancellableCoroutine
                      └─ shouldInterceptRequest（chromium 工作线程）
                           └─ callback.onResult(response) → block.resume(response)
                                ↑ 工作线程 resume 需要 Dispatcher 调度到 IO 线程
                                ↑ 调度延迟 1-15ms
                                ↑ 与外层 12s 超时窗口重叠
                                ↑ 外层超时先触发，取消整个协程树
```

**铁证**：R5 命中（17:56:45.907）→ 15ms 后外层超时（17:56:45.922）→ 返回 null → 触发 WebView 降级。

### 根因二：OkHttp HTTP/2 StreamReset 无容错（P1）

```
图片加载链：Glide → OkHttpStreamFetcher → okHttpClient.newCall(request)
  └─ OkHttpClient 默认启用 HTTP/2（未显式配置 protocols）
       └─ 服务端发送 RST_STREAM 帧
            └─ OkHttp 抛 StreamResetException
                 └─ OkHttpStreamFetcher.onFailure（L130-133）
                      └─ callback?.onLoadFailed(e)  ← 直接失败，无重试
                           └─ 失败 URL 写入 failUrl LruCache（L139）
                                └─ 后续同 URL 请求被短路（L64-67）
```

**铁证**：17:57:12.587/17:58:19.299 多次 StreamResetException，调用栈指向 `BitmapFactory.nativeDecodeStream`，证明图片解码链中断。

### 根因三：lastFailedHostHint 探测超时（P2）

```
CronetInterceptor.kt L170-177
  └─ if (degradedForSession)
       └─ if (elapsed < currentIntervalMs) return chain.proceed(original)  ← 降级期内走 OkHttp
       └─ if (hint != null && requestHost != hint)  ← 非失败 host 跳过探测
            └─ return chain.proceed(original)  ← 走 OkHttp
```

**问题**：若 `lastFailedHostHint` 对应 host 长时间无请求（如视频源已切换），探测永远不会触发，降级状态持续。

**铁证**：logcat 中 263 次"探测跳过非失败 host"日志，全部针对同一对 host（www***, 087***），10 秒内重复 15+ 次。

### 根因四：DoH 备用服务器全挂（P2）

```
DohDns.kt DOH_SERVERS（L58-66）
  ├─ server#1（阿里 DNS）→ 全部成功（30 条 parallel success）
  ├─ server#2（腾讯 DNS）→ UnknownHostException
  ├─ server#3（Cloudflare）→ UnknownHostException
  ├─ server#4（Google）→ UnknownHostException
  └─ server#5（Quad9）→ UnknownHostException
```

**铁证**：logcat L9954-9963 显示 server#2/3/4/5 全部 UnknownHostException，但因并行查询 server#1 成功就返回，整体 DoH 功能正常，但产生大量无效日志。

## 目标

1. **修复嗅探结果回灌**：R5 抓包命中后立即通知 extractVideoUrlForEpisode，消除外层超时抢占
2. **OkHttp HTTP/2 容错**：StreamResetException 时淘汰连接池连接并重试，避免图片加载链中断
3. **探测机制修正**：lastFailedHostHint 增加超时清除，避免探测永远不触发
4. **DoH 日志清理**：移除不可达的备用服务器，减少无效日志噪音
5. **提升嗅探成功率**：从 96.1% 提升到 99%+（消除 3 次误判失败）

## 非目标

- 不修改 Cronet 降级机制的核心逻辑（降级阈值/恢复探测间隔保持现状）
- 不修改 DoH 主服务器（阿里 DNS 工作正常）
- 不修改 Cronet SO 下载机制（已稳定工作）
- 不修改图片解码器（HWUI "unimplemented" 是系统层问题）
- 不重构整个嗅探架构（只修复结果管线断裂点）

## 修复方案摘要

| 编号 | 功能需求 | 优先级 | 影响范围 |
|------|---------|--------|---------|
| FR-1 | 移除 extractVideoUrlForEpisode 外层 withTimeoutOrNull 抢占 | P0 | VideoUrlExtractor.kt L507 单点 |
| FR-2 | R5 抓包命中后切 UI 线程同步 resume | P0 | BackstageWebView.kt L347-360 单点 |
| FR-3 | OkHttp HTTP/2 StreamReset 容错（淘汰连接+重试） | P1 | HttpHelper.kt + OkHttpStreamFetcher.kt |
| FR-4 | lastFailedHostHint 探测超时清除 | P2 | CronetInterceptor.kt L170-177 |
| FR-5 | DoH 备用服务器清理 | P2 | DohDns.kt DOH_SERVERS |

## 技术决策

### 为什么移除外层 withTimeoutOrNull（FR-1）？

- **抢占式取消是根因**：Kotlin 协程的 `withTimeoutOrNull` 是抢占式取消，会取消整个协程树，包括内层 `suspendCancellableCoroutine`。即使 R5 已命中并调用 `block.resume(response)`，只要协程恢复调度未完成，外层超时会优先触发取消。
- **内层超时已足够**：第一层 MacCMS 6s + 第三层 R5 6s = 12s 自然累加，无需外层兜底。
- **铁证**：R5 命中后 15ms 内被外层超时取消，返回 null 触发 WebView 降级。

### 为什么 R5 命中后切 UI 线程同步 resume（FR-2）？

- **工作线程 resume 调度延迟大**：`shouldInterceptRequest` 在 chromium 工作线程调用 `block.resume(response)`，需要 Dispatcher 调度到 IO 线程，调度延迟 1-15ms。
- **UI 线程 Handler 优先级高**：`mHandler.post { callback?.onResult(response); destroy() }` 将 resume 切到 UI 线程同步执行，调度延迟 <1ms。
- **铁证**：17:56:45.907 命中 → 17:56:45.922 超时，15ms 调度窗口与外层超时竞争失败。

### 为什么 StreamReset 需要淘汰连接+重试（FR-3）？

- **流重置不可重试但连接仍可用**：OkHttp `retryOnConnectionFailure(true)` 对 HTTP/2 流重置无效，连接池中的连接未被淘汰，下次请求复用同一连接仍失败。
- **Glide 无重试机制**：`OkHttpStreamFetcher.onFailure` 直接 `onLoadFailed`，失败 URL 写入 failUrl LruCache，后续同 URL 请求被短路。
- **铁证**：17:57:12.587/17:58:19.299 多次 StreamResetException，调用栈指向 `BitmapFactory.nativeDecodeStream`。

### 为什么 lastFailedHostHint 需要超时清除（FR-4）？

- **探测永远不触发**：若 `lastFailedHostHint` 对应 host 长时间无请求（如视频源已切换），探测永远不会触发，降级状态持续。
- **铁证**：263 次"探测跳过非失败 host"日志，全部针对同一对 host，10 秒内重复 15+ 次。

## 验收标准

1. 真机测试：R5 抓包命中后 extractVideoUrlForEpisode 不再返回 null（日志无"timeout (12s)"）
2. 真机测试：图片加载 StreamResetException 时有重试日志（"StreamReset 重试"）
3. 真机测试：Cronet 降级后 lastFailedHostHint 超时 5 分钟后清除（日志无"探测跳过非失败 host"持续超过 5 分钟）
4. 真机测试：DoH 日志无 server#2/3/4/5 的 UnknownHostException
5. 真机测试：嗅探成功率 ≥ 99%（消除 3 次误判失败）
6. 编译验证：测试包+正式包 BUILD SUCCESSFUL
7. mapping.txt 验证：关键类全部保留

## 相关文档

- [spec.md](./spec.md) - 需求规格
- [design.md](./design.md) - 技术设计
- [tasks.md](./tasks.md) - 任务清单
- V3 修复文档：[docs/specs/sniff-stability-fix-20260731/](../sniff-stability-fix-20260731/)
- 真机日志：`docs/issues/user/temp/20260731/002/extracted/logcat.txt`
