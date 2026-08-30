# design.md - 004 真机测试问题技术设计

> **根因修正说明**：本设计基于 spec.md v2（修正后），核心问题从"Activity 重建/BUFFERING timeout"修正为"首帧延迟 4808ms + AppLog 未输出 + DoH 冷启动失败"。

## 一、架构分析

### 1.1 视频播放首帧链路（冷启动场景）

```
用户点击视频
  ↓
VideoPlayerActivity.onActivityCreated
  ↓
VideoPlay.initSource (lifecycleScope.launch)
  ↓ (网络请求加载源信息)
switchToViewPagerMode + initView
  ↓
VideoFragment.activatePlayer
  ↓
Exo2MediaPlayer.prepareAsyncInternal
  ↓ (post Runnable)
PlayerInstancePool.acquire (获取 ExoPlayer 实例)
  ↓
sniffVideoType (异步协程 Range 请求)
  ↓ (DNS 解析 + HTTP 请求)
applyMediaSourceByType (HLS MediaSource)
  ↓
ExoPlayer.prepare
  ↓ (下载 m3u8 + 子 m3u8 + 首帧分片)
onRenderedFirstFrame (首帧渲染)
  ↓
STATE_READY (播放成功)
```

**冷启动延迟叠加点**：
1. `VideoPlay.initSource` 网络请求（源信息加载）：~1-2s
2. `sniffVideoType` DNS 解析 + Range 请求：~3s（DoH 失败期间）
3. `ExoPlayer.prepare` 子 m3u8 + 首帧分片下载：~1s
4. 合计：~5-6s（用户感知"卡住"）

### 1.2 DoH DNS 解析链路

```
DohDns.lookup(hostname)
  ↓
0. IDN 旁路（punycode 域名直接走系统 DNS）
  ↓
1. 成功缓存命中（5min TTL）→ 直接返回
  ↓
2. 负缓存命中（30s TTL）→ 走系统 DNS
  ↓
3. 熔断期检查（dohDisabledUntil）→ 走系统 DNS
  ↓
4. DoH 三服务器并行查询（3s 超时）
  ↓ (全部失败)
5. 写负缓存 30s + globalFailCount++
  ↓ (达阈值 3)
6. 熔断 5min + 走系统 DNS
```

**冷启动场景问题**：
- App 首次启动时 DoH 服务器可能不可达（网络未完全建立/防火墙阻断）
- 当前逻辑：3 次全服务器失败才熔断，每次 2-3s → 累计 6-9s 延迟
- 期间所有 DNS 查询都等待 DoH 失败后才走系统 DNS

### 1.3 AppLog 输出链路

```
AppLog.put(message) / AppLog.putDebugWithTag(tag, message)
  ↓
AppLog 检查初始化状态
  ↓ (未初始化则丢弃)
写入日志缓冲区
  ↓
定时刷盘到文件
```

**004 日志异常**：
- 18:48-19:16 期间（28 分钟）9 次 VideoPlayerActivity 启动，AppLog 完全无输出
- 19:16:47 起 AppLog 恢复输出
- 可能原因：09:39 崩溃后 App 进程残留但 AppLog 异常，或 logcat 缓冲区覆盖

## 二、修复方案

### 2.1 V-004-P0-1: 首帧渲染延迟优化

#### 2.1.1 DoH 冷启动优化

**目标**：冷启动场景首次 DoH 失败立即走系统 DNS，不等 3 次熔断

**修改文件**：`app/src/main/java/io/legado/app/help/http/DohDns.kt`

**方案**：新增 `coldStartMode` 标志位，App 启动后首次 DoH 失败立即熔断 30s（非 5min），并异步预热 DoH

```kotlin
// DohDns.kt 新增字段
@Volatile private var isColdStart = true
private const val COLD_START_DISABLE_MS = 30_000L  // 冷启动熔断 30s（非 5min）

// lookup 方法修改
override fun lookup(hostname: String): List<InetAddress> {
    // ... 现有逻辑 ...
    val result = parallelLookup(clients, hostname)
    if (result != null) {
        isColdStart = false  // 首次成功后退出冷启动模式
        // ... 现有成功逻辑 ...
    } else {
        negativeCachePut(key)
        if (isColdStart) {
            // 冷启动场景：首次失败立即熔断 30s（非 5min），异步预热 DoH
            dohDisabledUntil = System.currentTimeMillis() + COLD_START_DISABLE_MS
            globalFailCount.set(0)
            isColdStart = false
            AppLog.put("DohDns: cold start DoH failure, disable DoH ${COLD_START_DISABLE_MS / 1000}s, async preheat")
            asyncPreheatDoh()
        } else if (globalFailCount.incrementAndGet() >= GLOBAL_FAIL_THRESHOLD) {
            // ... 现有熔断逻辑 ...
        }
        return Dns.SYSTEM.lookup(hostname)
    }
}

// 新增：异步预热 DoH（不阻塞首帧）
private fun asyncPreheatDoh() {
    CoroutineScope(Dispatchers.IO + SupervisorJob()).launch {
        kotlinx.coroutines.delay(COLD_START_DISABLE_MS)
        kotlin.runCatching {
            // 预热常见域名
            DOH_SERVERS.forEach { server ->
                kotlin.runCatching { Dns.SYSTEM.lookup(server.url.toHttpUrl().host) }
            }
        }
        isColdStart = false
        AppLog.putDebug("DohDns: async preheat completed, DoH re-enabled")
    }
}
```

#### 2.1.2 嗅探前 DNS 预解析

**目标**：嗅探前异步预解析视频 URL 域名，避免嗅探时等待 DNS

**修改文件**：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

**方案**：新增 `preResolveDns(url)` 方法，在 `prepareAsyncInternal` 调用 `sniffVideoType` 前调用

```kotlin
// ExoPlayerHelper.kt 新增
fun preResolveDns(url: String) {
    val host = kotlin.runCatching { Uri.parse(url).host }.getOrNull() ?: return
    CoroutineScope(Dispatchers.IO + SupervisorJob()).launch {
        kotlin.runCatching { InetAddress.getAllByName(host) }
            .onSuccess { AppLog.putDebug("preResolveDns: success host=${host.take(2)}***") }
            .onFailure { AppLog.putDebug("preResolveDns: failed host=${host.take(2)}*** error=${it.javaClass.simpleName}") }
    }
}

// Exo2MediaPlayer.kt prepareAsyncInternal 修改
currentSniffJob = scope.launch {
    AppLog.put("ExoFallback: sniff job started, urlPath=${ExoPlayerHelper.sanitizeUrl(currentUrl)}")
    // V-004-P0-1: 嗅探前 DNS 预解析（不等待，异步预热系统 DNS 缓存）
    ExoPlayerHelper.preResolveDns(currentUrl)
    val sniff = ExoPlayerHelper.sniffVideoType(currentUrl, currentHeaders)
    // ... 现有逻辑 ...
}
```

#### 2.1.3 子 m3u8 预取（P2 延后）

**说明**：子 m3u8 预取涉及 HlsMediaSource 内部逻辑，media3 1.10.1 不支持自定义 HlsMediaSource.Factory 的子 m3u8 加载器，需升级 media3 或自定义 DataSource.Factory 拦截。本 spec 暂不实施，列为 P2 后续优化。

### 2.2 V-004-P0-2: AppLog 保障 + initSource 失败日志

#### 2.2.1 AppLog 初始化保障

**目标**：确保 AppLog 在任何状态下都能输出日志

**修改文件**：`app/src/main/java/io/legado/app/constant/AppLog.kt`

**方案**：AppLog.put 方法增加防御性兜底，确保日志缓冲区初始化

```kotlin
// AppLog.kt put 方法修改
fun put(message: String, throwable: Throwable? = null) {
    try {
        // V-004-P0-2: 防御性初始化检查
        if (!isInitialized) {
            ensureInitialized()
        }
        // ... 现有日志写入逻辑 ...
    } catch (e: Exception) {
        // 兜底：AppLog 本身失败不影响业务流程
        android.util.Log.e("AppLog", "AppLog.put failed: ${e.message}", e)
    }
}

// 新增：防御性初始化
private fun ensureInitialized() {
    kotlin.runCatching {
        // 重新初始化日志缓冲区
        if (logBuffer == null) {
            logBuffer = ConcurrentLinkedQueue<LogEntry>()
        }
        isInitialized = true
    }
}
```

#### 2.2.2 VideoPlay.initSource 失败日志

**目标**：initSource 失败时记录详细原因，不静默 finish

**修改文件**：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`

**方案**：onActivityCreated 中 initSource 失败时记录日志

```kotlin
// VideoPlayerActivity.kt onActivityCreated 修改
initSourceJob = lifecycleScope.launch {
    if (!VideoPlay.initSource(sourceKey, sourceType, bookUrl, record)) {
        // V-004-P0-2: initSource 失败记录详细日志（不静默 finish）
        AppLog.put(
            "VideoPlayerActivity initSource failed, " +
                "sourceKey=$sourceKey, sourceType=$sourceType, " +
                "bookUrl=${bookUrl?.take(20)}, record=${record?.take(20)}"
        )
        finish()
        return@launch
    }
    // ... 现有逻辑 ...
}
```

#### 2.2.3 Activity 快速切换保护

**目标**：用户快速切换视频时，避免 initSourceJob 被取消导致播放器未初始化

**说明**：当前 T2.8 修复在 onPause 时取消 initSourceJob 是正确的（防止资源泄漏），但快速切换场景下可能导致播放器未初始化。

**方案**：不改 T2.8 逻辑，但在 onActivityCreated 中增加日志，记录 initSource 耗时和结果

```kotlin
// VideoPlayerActivity.kt onActivityCreated 修改
initSourceJob = lifecycleScope.launch {
    val startTime = System.currentTimeMillis()
    if (!VideoPlay.initSource(sourceKey, sourceType, bookUrl, record)) {
        AppLog.put(
            "VideoPlayerActivity initSource failed (elapsed=${System.currentTimeMillis() - startTime}ms), " +
                "sourceKey=$sourceKey, sourceType=$sourceType"
        )
        finish()
        return@launch
    }
    AppLog.put("VideoPlayerActivity initSource success (elapsed=${System.currentTimeMillis() - startTime}ms)")
    // ... 现有逻辑 ...
}
```

### 2.3 V-004-P1-1: DoH 熔断阈值优化

**说明**：与 V-004-P0-1 的 DoH 冷启动优化合并实施，冷启动场景首次失败立即熔断 30s（非 5min），热启动场景保持 3 次熔断 5min。

### 2.4 V-004-P1-2: Cronet Request Canceled 日志降级

**目标**：Cronet Request Canceled 降级为 DEBUG 级别，不输出 ERROR 日志

**修改文件**：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`

**方案**：catch 块中识别 "Cronet Request Canceled" 消息，跳过 printOnDebug 和协议错误计数

```kotlin
// CronetInterceptor.kt catch 块修改
} catch (e: Exception) {
    cronetException = e
    val errMsg = e.message.toString()
    
    // V-004-P1-2: Request Canceled 是正常取消（用户切换/退出），降级为 DEBUG 日志
    val isCanceled = errMsg.contains("Canceled", true) || errMsg.contains("Cancelled", true)
    if (isCanceled) {
        AppLog.putDebug("Cronet request canceled (normal): ${errMsg.take(60)}")
        // 不调用 printOnDebug，不累计协议错误计数
        // 直接回退 OkHttp（chain.proceed 会再次检查 isCanceled 抛 IOException）
    } else {
        // ... 现有协议错误处理逻辑 ...
        if (!errMsg.contains("ERR_CERT_", true) && !errMsg.contains("ERR_SSL_", true)) {
            e.printOnDebug()
        }
        val isProtocolError = errMsg.contains("PROTOCOL_ERROR", true)
            // ... 现有协议错误判断 ...
        if (isProtocolError) {
            // ... 现有协议错误计数逻辑 ...
        }
    }
}
```

## 三、风险评估

### 3.1 DoH 冷启动优化风险

**风险**：冷启动场景 DoH 首次失败立即熔断 30s，可能导致 30s 内所有 DNS 查询走系统 DNS，DoH 优势丧失

**缓解**：
- 30s 后异步预热 DoH，预热成功后恢复 DoH
- 仅冷启动场景（isColdStart=true）触发，热启动场景保持 3 次熔断逻辑
- 系统 DNS 在国内可用（无污染场景），30s 短期熔断影响可接受

### 3.2 AppLog 防御性初始化风险

**风险**：重新初始化日志缓冲区可能导致日志丢失或重复

**缓解**：
- 仅在 isInitialized=false 时触发，正常场景不影响
- 使用 ConcurrentLinkedQueue 线程安全，避免并发问题
- 兜底 catch 确保不影响业务流程

### 3.3 Cronet Request Canceled 日志降级风险

**风险**：降级后可能漏掉真实的 Cronet 取消问题

**缓解**：
- 仍输出 DEBUG 级别日志（可通过日志级别过滤查看）
- 仅 "Canceled" 关键词匹配，其他错误（如 protocol error）保持 ERROR 级别

## 四、实施依赖

- 不依赖外部库升级
- 不依赖 media3 升级（子 m3u8 预取 P2 延后）
- 不依赖 AndroidManifest 修改
- 修改文件清单：
  1. `app/src/main/java/io/legado/app/help/http/DohDns.kt`
  2. `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`
  3. `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
  4. `app/src/main/java/io/legado/app/constant/AppLog.kt`
  5. `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`
  6. `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`

## 五、验证方案

### 5.1 编译验证
- `./gradlew assembleDebug` 编译通过

### 5.2 单元验证
- DohDns 冷启动熔断逻辑（mock DoH 失败，验证 30s 熔断）
- CronetInterceptor Request Canceled 日志级别（mock Canceled 异常，验证 DEBUG 输出）

### 5.3 真机验证
- 冷启动场景进入视频播放器，首帧渲染时间 ≤ 2s
- 快速切换 9 个视频，AppLog 持续输出
- 日志中无 `W System.err: Cronet Request Canceled` 噪音
- DoH 冷启动首次失败后 30s 熔断，异步预热成功后恢复

## 六、与 003 spec 的关系

- **003 spec**：V-P0-1 TrackSelector 崩溃 + I-P0-1/I-P0-2 图片防盗链（已实施）
- **004 spec**：首帧延迟 + AppLog 保障 + DoH 冷启动 + Cronet 日志噪音（本次实施）
- **004 spec 不重复 003 spec 的修复**：TrackSelector/BUFFERING timeout/降级链类型校验已在 003 spec 完成，004 日志验证未触发这些问题
