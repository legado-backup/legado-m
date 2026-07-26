# exoplayer-resilience 深度架构审查报告 v2

> 由3个子代理并行审查：嗅探+降级架构 / 并发安全+资源管理 / 错误处理+日志完整性
> 审查时间：2026-07-26 11:45
> 触发原因：用户批评"确定没架构设计问题了么？这么严重的设计问题竟然先让我发现"

## 一、问题汇总表

### P0 严重问题（6个，必须修复）

| ID | 维度 | 位置 | 问题摘要 |
|---|------|------|---------|
| P0-1 | 嗅探降级 | VideoFragment.kt:371-389 | retryExoPlayback 降级-切回循环风险，unrecoverableFailCount 重置导致死循环 |
| P0-2 | 嗅探缓存 | ExoPlayerHelper.kt:137 | null 缓存导致1小时内无法重试嗅探（临时网络失败也被缓存） |
| P0-3 | 并发安全 | Exo2MediaPlayer.kt:57,63 | release()未cancel scope/currentSniffJob，协程泄漏+已释放对象访问 |
| P0-4 | 线程安全 | VideoPlay.kt:141 | currentPlayHeaders 无@Volatile，跨线程可见性问题 |
| P0-5 | 协程取消 | ExoPlayerHelper.kt:148-178 | runCatching吞掉CancellationException，破坏结构化并发 |
| P0-6 | 输出安全 | Exo2MediaPlayer.kt:417 | 完整URL直接输出AppLog，违反output-safety规范（可能触发审查中断！） |

### P1 中等问题（10个）

| ID | 维度 | 位置 | 问题摘要 |
|---|------|------|---------|
| P1-1 | 嗅探接入 | AudioPlayService.kt:253 | 音频播放路径未接入嗅探，HLS音频流有隐患 |
| P1-2 | Cookie | WebViewVideoPlayer.kt:98-118 | WebView降级模式Cookie未通过CookieManager注入 |
| P1-3 | 协程竞态 | Exo2MediaPlayer.kt:188-196 | prepareAsyncInternal协程与release竞态，isActive检查后mInternalPlayer可能变null |
| P1-4 | OkHttp取消 | ExoPlayerHelper.kt:113,160 | withTimeoutOrNull不取消OkHttp同步execute()，网络请求泄漏 |
| P1-5 | Header覆盖 | ExoPlayerHelper.kt:375 | setDefaultHeaders全局单例覆盖，多播放器并发互相覆盖 |
| P1-6 | 失败日志 | ExoPlayerHelper.kt:161-174 | sniffWithRangeRequest 4个返回null分支无差异化日志 |
| P1-7 | 成功日志 | ExoPlayerHelper.kt:160-178 | Range请求成功路径无响应码/Content-Type/读取字节数 |
| P1-8 | 降级日志 | Exo2MediaPlayer.kt:346-360 | 降级触发日志缺url脱敏(path)、缺headerKeys |
| P1-9 | 入参防御 | ExoPlayerHelper.kt:54-80 | createMediaItem入参url为空无防御 |
| P1-10 | 入参防御 | ExoPlayerHelper.kt:54-80 | createMediaItem入参headers为null(Java调用方)会NPE |

### P2 轻微问题（10个，可选修复）

| ID | 维度 | 位置 | 问题摘要 |
|---|------|------|---------|
| P2-1 | 超时 | ExoPlayerHelper.kt:229 | 嗅探超时3秒影响首屏延迟（可接受，用户要求准确性>性能） |
| P2-2 | 缓存key | MimeSnifferCache.kt:14-22 | 完整URL作为key导致token类URL缓存失效（已知上限） |
| P2-3 | 锁冗余 | MimeSnifferCache.kt:55,73,82,89 | @Synchronized冗余（LruCache已线程安全） |
| P2-4 | 流关闭 | ExoPlayerHelper.kt:184-194 | readLimitedBytes异常路径未显式关闭stream（间接关闭无泄漏） |
| P2-5 | single-flight | ExoPlayerHelper.kt:99-141 | 多Fragment嗅探同一URL无去重（缓存击穿1次） |
| P2-6 | Content-Type日志 | ExoPlayerHelper.kt:224 | parseContentType未知类型返回null无日志 |
| P2-7 | L2/L3区分 | ExoPlayerHelper.kt:167-173 | sniffWithRangeRequest内L2/L3命中无区分日志 |
| P2-8 | ExoHeader日志 | ExoPlayerHelper.kt:311 | 用urlLen非sanitizeUrl |
| P2-9 | URL脱敏不统一 | Exo2MediaPlayer.kt:301,323,368 | 用takeLast(60)非sanitizeUrl |
| P2-10 | 空url防御 | ExoPlayerHelper.kt:99-141 | sniffMimeType入参url为空无早期return |

## 二、P0 严重问题详解

### P0-1：retryExoPlayback 降级-切回循环风险

**位置**：VideoFragment.kt:371-389 + Exo2MediaPlayer.kt:120

**问题描述**：
- 用户点击"切换回内置播放器"后，retryExoPlayback → activatePlayer → VideoPlay.startPlay → 新 Exo2MediaPlayer（unrecoverableFailCount 重置为 0）
- 若视频源本身不可恢复（3002/3004），需再次失败3次才降级，形成"降级→切回→降级→切回"循环
- 用户体验差：每次切回都要等3次失败

**根因分析**：
- retryExoPlayback 不区分"首次播放"和"降级后切回"，每次都重置 unrecoverableFailCount
- 给用户"切回有希望"的错觉，对不可恢复错误必然失败

**修复方案**：
```kotlin
// VideoFragment 增加 exoRetryCount 字段
private var exoRetryCount = 0

fun retryExoPlayback() {
    exoRetryCount++
    if (exoRetryCount >= 2) {
        // 弹窗提示用户该源在ExoPlayer模式下不可播放
        showDialog("该视频源在ExoPlayer模式下不可播放，建议使用WebView模式")
        return
    }
    activatePlayer()
}
// 切换视频/集数时重置 exoRetryCount
```

### P0-2：sniffMimeType null缓存导致1小时内无法重试嗅探

**位置**：ExoPlayerHelper.kt:137 + MimeSnifferCache.kt:30

**问题描述**：
- 嗅探失败（Range请求超时/网络抖动/服务端503）时缓存null
- 1小时内同一URL不再嗅探，直接走URL后缀+Extractor.sniff()兜底
- 若首次失败是临时网络问题，1小时内即使网络恢复也无法重试嗅探

**根因分析**：
- MimeSnifferCache 不区分"确实无法识别"（magic number不匹配）和"临时网络失败"（超时/503）
- sniffMimeType 把超时和503也当作"嗅探过但未识别"缓存null

**修复方案**：
```kotlin
// 区分缓存策略
sealed class SniffResult {
    object NetworkFailure : SniffResult()  // 不缓存
    object NotRecognized : SniffResult()   // 缓存null
    data class Success(val mime: String) : SniffResult()
}

// sniffWithRangeRequest 返回 SniffResult
// sniffMimeType 据此决定是否缓存
```

简化方案：网络失败不缓存，magic number不匹配才缓存null

### P0-3：Exo2MediaPlayer.release()未cancel scope/currentSniffJob

**位置**：Exo2MediaPlayer.kt:57（scope定义）+ :63（currentSniffJob定义）

**问题描述**：
- Exo2MediaPlayer 没有覆盖 release() 方法
- ExoPlayerManager.release() 调用 mediaPlayer.release() 时，仅执行父类 IjkExo2MediaPlayer.release()
- 不会 cancel scope，也不会 cancel currentSniffJob
- 时序危险：用户切换视频→启动sniffJob→用户立即退出Activity→release()→3秒内sniffJob完成→调用 mInternalPlayer?.setMediaItem（可能崩溃）
- 即使不崩溃，每次切换视频+退出都泄漏一个3秒协程

**修复方案**：
```kotlin
override fun release() {
    currentSniffJob?.cancel()
    scope.cancel()
    super.release()
}
```

### P0-4：VideoPlay.currentPlayHeaders 无@Volatile

**位置**：VideoPlay.kt:141

**问题描述**：
- `var currentPlayHeaders: Map<String, String>? = null` 无@Volatile、无锁保护
- 写：在 loadScope = CoroutineScope(SupervisorJob() + IO) 协程中赋值，至少8处
- 读：在主线程 VideoPlayerActivity.kt:1414 读取
- 跨线程读写无@Volatile，存在JMM可见性问题：主线程可能读到null或旧值
- 导致WebView降级时Header丢失

**修复方案**：
```kotlin
@Volatile
var currentPlayHeaders: Map<String, String>? = null
```

### P0-5：runCatching吞掉CancellationException

**位置**：ExoPlayerHelper.kt:148-178

**问题描述**：
- Kotlin runCatching 源码用 catch(e: Throwable) 捕获所有异常，包括 CancellationException
- sniffWithRangeRequest 被 withContext(Dispatchers.IO) 调用，运行在协程上下文中
- 外层 withTimeoutOrNull(SNIFF_TIMEOUT_MS) 超时会抛 CancellationException
- 该异常被 runCatching 吞掉，导致：
  1. 协程结构化取消失效
  2. 资源释放异常
  3. 日志误报"range request failed: CancellationException"
- 铁证：Kotlin官方文档明确警告"runCatching会吞CancellationException，不应在协程中使用"
- 项目记忆已有铁证："runCatching会吞CancellationException导致协程取消误报（必须重新抛出）"

**修复方案**：
```kotlin
return runCatching {
    ...
}.getOrElse {
    if (it is kotlinx.coroutines.CancellationException) {
        throw it  // 重新抛出，保留协程取消语义
    }
    AppLog.put("SniffingMime: range request failed: ${it.javaClass.simpleName}, urlPath=${sanitizeUrl(url)}")
    null
}
```

更优方案：改用显式 try/catch 只捕获 IOException

### P0-6：完整URL直接输出AppLog，违反输出安全规范

**位置**：Exo2MediaPlayer.kt:413-422

**问题描述**：
```kotlin
val errorInfo = buildString {
    appendLine("播放失败")
    appendLine("错误码: ${error.errorCode} (${error.errorCodeName})")
    appendLine("错误信息: ${error.message ?: "无"}")
    appendLine("播放地址: $currentUrl")  // ← 完整URL直接输出！
    appendLine("原因: ${error.cause?.toString() ?: "未知"}")
    ...
}
AppLog.put(errorInfo, error)
postEvent(EventBus.VIDEO_PLAY_ERROR, errorInfo)
```

- currentUrl 是完整视频URL（含协议+域名+path+query）
- 可能含：视频网站域名（违禁词）、防盗链token/sign参数（敏感字段）、用户id/sessionid参数（敏感字段）
- 直接输出违反 output-safety.md §七"完整URL→只保留路径模式"规范
- 该 errorInfo 同时通过 AppLog.put 持久化 + EventBus 广播到 UI，扩散面大
- **铁证**：同文件line 301/323/368 已用 currentUrl.takeLast(60) 脱敏，line 417 是遗漏点
- **这就是用户说"又触发违禁词主动中断了"的根本原因！**

**修复方案**：
```kotlin
appendLine("播放地址: ${sanitizeUrlForLog(currentUrl)}")
```
其中 sanitizeUrlForLog 提取path模式（如 /path/{id}），隐藏域名和query敏感参数。
需将 ExoPlayerHelper.sanitizeUrl 改为public或提取到工具类。

## 三、修复优先级建议

### 第一优先级（必须立即修复，影响生产稳定性+输出安全）
1. **P0-6**：完整URL输出AppLog（直接导致审查中断！）
2. **P0-5**：runCatching吞CancellationException（项目已有铁证）
3. **P0-3**：release()未cancel scope（协程泄漏+崩溃风险）
4. **P0-4**：currentPlayHeaders无@Volatile（跨线程可见性）

### 第二优先级（影响用户体验）
5. **P0-1**：retryExoPlayback降级-切回循环
6. **P0-2**：null缓存导致1小时内无法重试嗅探

### 第三优先级（P1中等问题，真机测试前修复）
7. P1-3：prepareAsyncInternal协程与release竞态
8. P1-4：withTimeoutOrNull不取消OkHttp同步请求
9. P1-6/7/8：日志增强（差异化失败日志+成功路径日志+降级日志）
10. P1-9/10：入参防御

### 第四优先级（P1功能性问题，后续迭代）
11. P1-1：音频播放路径嗅探接入
12. P1-2：WebView降级Cookie注入
13. P1-5：setDefaultHeaders全局覆盖

### 第五优先级（P2轻微问题，可选）
14. P2系列：日志统一性、缓存策略优化、防御性编程

## 四、审查范围

### 已审查文件
- ExoPlayerHelper.kt
- Exo2MediaPlayer.kt
- MimeSniffer.kt
- MimeSnifferCache.kt
- VideoPlayerActivity.kt
- VideoFragment.kt
- EventBus.kt
- VideoPlay.kt
- WebViewVideoPlayer.kt
- ExoPlayerManager.kt
- AnalyzeUrl.kt
- AudioPlayService.kt

### 审查方法
- Grep搜索技术字段（sniffMimeType/VIDEO_FALLBACK_WEBVIEW/switchToWebViewMode等）
- Read读取关键代码段
- 调用链追踪验证
- 协程并发分析
- 线程安全分析
- 异常处理路径分析
- 日志完整性检查
- 输出安全规范检查

## 五、关键发现总结

1. **P0-6是用户说"又触发违禁词主动中断了"的根本原因**：Exo2MediaPlayer.kt:417直接输出完整URL到AppLog，日志查看时触发违禁词审查
2. **P0-5违反项目已有铁证**：项目记忆明确记录"runCatching会吞CancellationException导致协程取消误报（必须重新抛出）"，但代码仍用runCatching
3. **P0-3是协程泄漏根源**：release()未cancel scope，每次切换视频+退出都泄漏3秒协程
4. **P0-4跨线程可见性问题**：currentPlayHeaders无@Volatile，WebView降级时Header可能丢失
5. **嗅探架构视频路径接入完整**，但音频路径未接入（设计取舍）
6. **降级架构事件链路完整**，但retryExoPlayback有循环风险

**建议**：优先修复P0-6（输出安全）+P0-5（协程取消）+P0-3（协程泄漏）+P0-4（线程安全），这4个问题直接影响生产稳定性和输出安全。
