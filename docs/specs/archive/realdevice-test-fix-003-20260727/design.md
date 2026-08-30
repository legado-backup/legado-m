# design.md — realdevice-test-fix-003-20260727

> 基于 003 日志深度分析（8 个新发现问题）的技术设计方案

## 1. V-003-P0-2：prepareAsyncInternal 重入保护

### 根因锚点
- `Exo2MediaPlayer.kt:476` prepareAsyncInternal 被 R5 网络抓包多次回调重入
- 9~16ms 内重入导致 PlayerInstancePool.acquire 被调用两次

### 修复方案
```kotlin
// Exo2MediaPlayer.kt 新增字段
private val isPreparing = java.util.concurrent.atomic.AtomicBoolean(false)

// prepareAsyncInternal 入口
override fun prepareAsyncInternal() {
    // V-003-P0-2: 重入保护——R5 网络抓包命中后可能多次回调，第一次执行后续跳过
    if (!isPreparing.compareAndSet(false, true)) {
        AppLog.put("ExoFallback: prepareAsyncInternal reentrant skip, callCount=$prepareAsyncCallCount")
        return
    }
    try {
        // ... 原有逻辑
    } finally {
        isPreparing.set(false)
    }
}
```

### 验证
prepareAsyncInternal 不被重入；无重复 acquire/createLoadControl

---

## 2. I-003-P0-1：Glide destroyed activity 守卫

### 根因锚点
- `ImageCanvasAdapter.kt:317` preloadAround `Glide.with(context)`
- `ImageGalleryActivity.kt:259` onScrollStateChanged 触发链

### 修复方案
```kotlin
// ImageCanvasAdapter.preloadAround 入口
fun preloadAround(centerPosition: Int, range: Int = 1) {
    val recyclerView = recyclerViewRef?.get() ?: return
    val context = recyclerView.context
    // I-003-P0-1: Activity 销毁后不再触发 Glide 加载
    if (context is android.app.Activity) {
        if (context.isDestroyed || context.isFinishing) {
            AppLog.putDebugWithTag(AppLog.TAG_IMAGE_CANVAS, "preloadAround skip: activity destroyed")
            return
        }
    }
    // ... 原有逻辑
}
```

### 验证
Activity 销毁后快速滑动不崩溃；无 IllegalArgumentException

---

## 3. V-003-P1-1：BUFFERING 降级链设计缺陷修复

### 根因锚点
- `Exo2MediaPlayer.kt:187-205` buildFallbackTypes
- HLS 降级链 [HLS, Progressive, DASH] → Progressive 对 HLS 流必然 3003

### 根因分析
- HLS 流（m3u8 文本清单）降级到 Progressive（contentType=4）
- ProgressiveMediaSource 用 21 个 Extractor 嗅探，全部失败（NoDeclaredBrand）
- m3u8 不是容器格式，Extractor 无法识别

### 修复方案
修改 `buildFallbackTypes`：清单类型降级链移除 Progressive，改为 [清单类型, 另一清单类型, 直接 WebView]

```kotlin
private fun buildFallbackTypes(sniff: ExoPlayerHelper.SniffResult): List<Int> {
    return when (sniff.contentType) {
        C.TYPE_HLS -> listOf(C.TYPE_HLS, C.TYPE_DASH)  // 移除 Progressive
        C.TYPE_DASH -> listOf(C.TYPE_DASH, C.TYPE_HLS)  // 移除 Progressive
        C.TYPE_SS -> listOf(C.TYPE_SS, C.TYPE_HLS, C.TYPE_DASH)  // 移除 Progressive
        C.TYPE_OTHER -> listOf(C.TYPE_OTHER, C.TYPE_HLS, C.TYPE_DASH)  // 直链保留 Progressive
        else -> {
            // UNKNOWN 按后缀启发式（V-P1-1 逻辑不变）
            when (ExoPlayerHelper.guessTypeByUrl(currentUrl)) {
                C.TYPE_OTHER -> listOf(C.TYPE_OTHER, C.TYPE_HLS, C.TYPE_DASH)
                C.TYPE_DASH -> listOf(C.TYPE_DASH, C.TYPE_HLS)
                C.TYPE_SS -> listOf(C.TYPE_SS, C.TYPE_HLS, C.TYPE_DASH)
                else -> listOf(C.TYPE_HLS, C.TYPE_DASH)  // 移除 Progressive
            }
        }
    }
}
```

### 设计理由
- HLS/DASH/SS 都是清单格式，互相降级有合理性（某些服务器清单格式标注错误）
- Progressive 只对直链（mp4/mkv 等）有效，对清单格式必然失败
- 清单类型降级耗尽后直接触发 WebView 回退（V-P1-2 末端兜底已有）

### 验证
HLS 流 BUFFERING 超时不降级到 Progressive；无 21 Extractor 全失败；末端触发 WebView 回退

---

## 4. I-003-P1-2：URL 拼接 %0A Bug 修复

### 根因锚点
- `parseImageUrls strategy 1 (newline split)` — 换行符分割后未 trim

### 修复方案
找到 parseImageUrls 实现，分割后对每个 URL 执行 trim + 过滤：

```kotlin
// parseImageUrls newline split 分支
urls.split("\n", "\r\n", "\r")
    .map { it.trim() }  // 去除首尾空白和换行符
    .filter { it.isNotBlank() && !it.contains("%0A") && !it.contains("\n") }  // 过滤残留
    .also { 
        if (it.size != rawCount) {
            AppLog.putDebugWithTag(TAG, "parseImageUrls: filtered %0A residue, raw=$rawCount clean=${it.size}")
        }
    }
```

### 验证
解析出的 URL 不含 %0A/换行符；404 次数显著下降

---

## 5. I-003-P1-3：图片播放器 UX 对齐

### 5.1 工具栏
- `activity_image_gallery.xml` 添加 Toolbar
- `R.menu.image_gallery`（收藏 + 三点菜单：刷新/配置/浏览器打开/日志）
- `ImageGalleryActivity.kt` onCreateOptionsMenu/onOptionsItemSelected
- 收藏复用 RssFavorites；刷新清 Glide 缓存 + notifyItemRangeChanged；浏览器 openUrl；日志 AppLogDialog

### 5.2 占位底图
- `ImageCanvasAdapter` RequestOptions `.placeholder(R.drawable.image_placeholder).error(R.drawable.image_error_placeholder).transition(withCrossFade(300))`
- ViewHolder 错误占位点击重试

### 5.3 进度指示
- 顶部 `第 X/共 Y 张` 文本 + ViewPager2 onPageSelected 联动
- ViewHolder 加载状态点（加载中黄/成功绿/失败红）

### 验证
菜单四项可用；占位→crossfade 无闪烁；进度联动准确；错误点击可重试

---

## 6. V-003-P2-1：LoadControl 重复创建

### 根因锚点
- `PlayerInstancePool.kt:97` createLoadControl 每次 acquire 调用

### 修复方案
按 tier 缓存 LoadControl 实例：
```kotlin
private val loadControlCache = java.util.concurrent.ConcurrentHashMap<String, DefaultLoadControl>()

fun createLoadControl(): DefaultLoadControl {
    val tier = ExoPlayerHelper.getCurrentBandwidthTier()
    return loadControlCache.computeIfAbsent(tier.name) {
        AppLog.put("PlayerPool: createLoadControl (new), tier=$tier")
        ExoPlayerHelper.createLoadControlByTier(tier, sharedAllocator)
    }
}
```

### 验证
acquire 时不重复创建 LoadControl（日志验证 "create new" 只出现一次/tier）

---

## 7. T-003-P2-1：ai_test 分析脚本

### 设计
`ai_tests/scripts/analyze_player_stats.py`：Grep 过滤 + 统计计数
- 视频：sniffVideoType/ERROR_CODE/ExoFallback/VIDEO_FALLBACK_WEBVIEW
- 图片：ImageLoad/403/ImageFallback/triggerFallbackReload
- 网络：DohDns/IDN bypass/Cronet 降级

### 验证
脚本可解析 logcat 输出统计报告

---

## 8. 全局约束

1. 日志一律 `AppLog.put` + `sanitizeUrl` 脱敏
2. WebView 操作必在 UI 线程；runCatching 不吞 CancellationException
3. Glide 异步回调必须 `isDestroyed/isFinishing` 守卫
4. 协程用项目 `Coroutine.async{}...onError{}` 链式封装风格
5. 每 Phase 完成后：编译验证 → updateLog.md 基于 git diff 更新
6. 真机测试用测试包 `io.legado.miss.app.debug`
