# 设计文档（image-canvas-3fix-20260728）

> design.md — 源码级设计与根因分析

## 0. 文档说明

本文档基于 008 日志包铁证 + 源码深度核实编写。所有修复方案均已对照源码行号验证可行性，并对原始修复方案有 2 处修正（见 README.md「重要说明」）。

---

## 1. Q1 根因分析与设计：加载图片仍滚动到最后一张

### 1.1 日志证据链

| 日志行 | 内容（脱敏） | 分析结论 |
|--------|-------------|---------|
| L106 | `observeNewItems: notifyItemRangeInserted startPos=0 itemCount=24` | 首次插入 24 项，触发 RecyclerView 布局 |
| L107 | 80ms 后 `Scroll: trigger loadNextArticle remaining=1 total=25 lastVisible=24` | 80ms 后 lastVisible=24（最后一张），说明所有 24 项布局在一屏内（高度为 0） |
| - | 无 isInitialScrollDone 日志 | scrollToPosition(0) 未生效或被后续布局/loadNextArticle 覆盖 |

### 1.2 根因分析

#### 根因 1：defaultHeight 设置可能未生效

**源码位置**：`ImageCanvasAdapter.kt` L241-265 onCreateViewHolder

**当前代码**（L249-253）：
```kotlin
val defaultHeight = (parent.resources.displayMetrics.heightPixels * 0.6).toInt()
binding.root.layoutParams = binding.root.layoutParams.apply {
    height = defaultHeight
}
```

**问题**：
- `binding.root.layoutParams` 在 inflate(parent, false) 后理论上非 null，但 `apply { height = defaultHeight }` 是修改原 layoutParams 对象，若 RecyclerView 的 LayoutManager 在后续布局中重新创建 layoutParams，此设置会被覆盖
- bind 方法 L457-460 也重置 defaultHeight，但同样使用 `itemView.layoutParams` 修改模式

**bind 方法当前代码**（L457-460）：
```kotlin
val defaultHeight = (itemView.resources.displayMetrics.heightPixels * 0.6).toInt()
val lp = itemView.layoutParams
lp.height = defaultHeight
itemView.layoutParams = lp
```

#### 根因 2：isInitialScrollDone 的 scrollToPosition(0) 时机错误

**源码位置**：`ImageGalleryActivity.kt` L692-714 observeNewItems

**当前代码**（L702-712）：
```kotlin
if (!isInitialScrollDone && startPos == 0 && itemCount > 0) {
    isInitialScrollDone = true
    binding.recyclerView.post {
        binding.recyclerView.scrollToPosition(0)
        AppLog.putDebugWithTag(...)
    }
}
```

**问题**：
- `post` 将任务投递到 UI 队列，但此时 RecyclerView 的布局可能尚未完成（notifyItemRangeInserted 后布局是异步的）
- scrollToPosition(0) 在布局完成前执行，会被后续布局过程覆盖（RecyclerView 会根据实际测量的 item 高度重新计算滚动位置）
- 日志中无 isInitialScrollDone 相关输出，说明此分支可能未进入或 post 任务被抢占

#### 根因 3：首次插入后自动触发 loadNextArticle 滚动覆盖

**日志证据**：L107 显示 80ms 后触发 loadNextArticle，loadNextArticle 会加载下一篇文章并插入，插入过程可能触发 RecyclerView 滚动到新插入位置

### 1.3 修复方案（源码级设计）

#### 修复 1：onCreateViewHolder 强制创建新 layoutParams

**修改位置**：`ImageCanvasAdapter.kt` L249-253

**修改前**：
```kotlin
val defaultHeight = (parent.resources.displayMetrics.heightPixels * 0.6).toInt()
binding.root.layoutParams = binding.root.layoutParams.apply {
    height = defaultHeight
}
```

**修改后**：
```kotlin
val defaultHeight = (parent.resources.displayMetrics.heightPixels * 0.6).toInt()
// 强制创建新 layoutParams，避免原 layoutParams 为 null 或被 LayoutManager 覆盖
binding.root.layoutParams = ViewGroup.LayoutParams(
    ViewGroup.LayoutParams.MATCH_PARENT,
    defaultHeight
)
```

**修改理由**：使用 `ViewGroup.LayoutParams(MATCH_PARENT, defaultHeight)` 创建新对象，确保高度设置不被 LayoutManager 重新创建的 layoutParams 覆盖。

#### 修复 2：observeNewItems 使用 OnGlobalLayoutListener 等待布局完成

**修改位置**：`ImageGalleryActivity.kt` L702-712

**修改前**：
```kotlin
if (!isInitialScrollDone && startPos == 0 && itemCount > 0) {
    isInitialScrollDone = true
    binding.recyclerView.post {
        binding.recyclerView.scrollToPosition(0)
        AppLog.putDebugWithTag(...)
    }
}
```

**修改后**：
```kotlin
if (!isInitialScrollDone && startPos == 0 && itemCount > 0) {
    isInitialScrollDone = true
    // 使用 OnGlobalLayoutListener 等待布局完成后执行 scrollToPosition(0)
    // 避免 post 在布局完成前执行被后续布局覆盖
    binding.recyclerView.viewTreeObserver.addOnGlobalLayoutListener(
        object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                binding.recyclerView.viewTreeObserver.removeOnGlobalLayoutListener(this)
                binding.recyclerView.scrollToPosition(0)
                AppLog.putDebugWithTag(
                    AppLog.TAG_IMAGE_CANVAS,
                    "observeNewItems: initial scroll to position 0 (after layout)",
                    level = AppLog.Level.INFO
                )
            }
        }
    )
}
```

**修改理由**：`OnGlobalLayoutListener` 在 RecyclerView 完成布局后回调，此时 scrollToPosition(0) 能正确定位到第一张图片且不会被布局过程覆盖。

#### 修复 3：首次插入时禁用 loadNextArticle 自动触发

**修改位置**：`ImageGalleryActivity.kt` onScrolled 中的 loadNextArticle 触发逻辑

**修改逻辑**：在 onScrolled 中判断 `isInitialScrollDone`，首次插入完成（isInitialScrollDone=true）前的滚动事件不触发 loadNextArticle。

**伪代码**：
```kotlin
override fun onScrolled(...) {
    // 首次插入未完成时禁用 loadNextArticle，避免滚动覆盖
    if (!isInitialScrollDone) {
        return
    }
    // ... 原有 loadNextArticle 触发逻辑
}
```

**修改理由**：首次插入 24 项后 80ms 触发的 loadNextArticle 会加载下一篇并插入，破坏初始滚动位置。禁用首次插入前的 loadNextArticle 确保初始滚动定位稳定。

### 1.4 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| OnGlobalLayoutListener 不触发导致 scrollToPosition 不执行 | 低 | RecyclerView 有数据时必然触发布局，listener 必然回调 |
| loadNextArticle 禁用导致无法加载下一篇 | 中 | 仅首次插入时禁用，isInitialScrollDone=true 后恢复正常 |
| ViewGroup.LayoutParams 类型与 LayoutManager 期望不符 | 低 | RecyclerView 默认 LayoutManager 使用 ViewGroup.LayoutParams 子类，兼容父类型 |

### 1.5 回退方案

若修复后 Q1 问题仍存在，回退方案：
1. 恢复 `binding.root.layoutParams.apply { height = defaultHeight }` 写法
2. 恢复 `binding.recyclerView.post { scrollToPosition(0) }` 写法
3. 在 onBindViewHolder 中显式调用 `holder.itemView.requestFocus()` 强制定位

---

## 2. Q2 根因分析与设计：只有一张图（L2 超时丢弃 51 张 URL）

### 2.1 日志证据链

| 日志行 | 内容（脱敏） | 分析结论 |
|--------|-------------|---------|
| L2480 | HTTP 429 限流 | 源站点限流，ruleContent 请求返回错误页面 |
| L2493 | `strategy 2 (ruleImage selector) success: count=1` | 策略2 从错误页面解析仅命中 1 张图 |
| L2553 | `sniffImageUrls timeout: collected=51` | L2 WebView 嗅探超时，但已收集 51 张 URL（sniffImageUrls 内部 L103 日志） |
| L2555 | `extractImageList done(L1+L2 merged): l1=1 l2=0 merged=1` | L2=0！sniffImageUrls 返回的 51 张 URL 被丢弃 |

### 2.2 根因分析

#### 根因 1：extractWithWebView 外层 withTimeoutOrNull 丢弃 sniffImageUrls 返回值（关键 bug）

**源码位置**：`ImageUrlExtractor.kt` L565-613 extractWithWebView

**当前代码**（L583-600）：
```kotlin
return webviewMutex.withLock {
    try {
        withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS) {  // 外层超时 6s
            ImageSnifferWebView(
                url = link,
                headerMap = headerMap,
                tag = rssSource.sourceUrl,
                timeout = L2_WEBVIEW_TIMEOUT_MS,  // 内部超时也是 6s
                delayTime = 1500L
            ).sniffImageUrls()
        } ?: run {
            AppLog.putDebugWithTag(..., "L2 webview sniff timeout(${L2_WEBVIEW_TIMEOUT_MS}ms)", ...)
            emptyList()  // 外层超时返回 emptyList！
        }
    } catch ...
}
```

**问题分析**：
- `sniffImageUrls()` 内部已有 `withTimeoutOrNull(timeout)` 超时机制（L78），超时后返回 `collectedUrls.toList()`（L106，即已收集的 51 张 URL）
- `extractWithWebView` 外层又包了一层 `withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS)`
- 两者超时时间相同（6s），当 sniffImageUrls 内部超时（6s 整）返回 51 张 URL 时，外层 withTimeoutOrNull 也到达 6s 阈值，**外层超时先生效**，直接返回 null → 转为 emptyList，丢弃 sniffImageUrls 的 51 张 URL
- 日志 L2553 是 sniffImageUrls 内部 L103 的超时日志（输出 collected=51），但 L2555 显示 l2=0，证明外层 withTimeoutOrNull 生效丢弃了返回值

#### 根因 2：策略2 命中后直接 return 未继续策略3

**源码位置**：`ImageUrlExtractor.kt` L274-281

**当前代码**：
```kotlin
if (imgUrls.isNotEmpty()) {
    AppLog.putDebugWithTag(..., "strategy 2 (ruleImage selector) success: count=${imgUrls.size}", ...)
    return filterImageUrls(imgUrls)  // 命中 1 张直接 return，未继续策略3
}
```

**问题**：HTTP 429 限流时 ruleContent 从错误页面解析，策略2 仅命中 1 张，但策略3（regex img tag）可能从其他来源提取更多 URL。策略2 命中数 < 3 时应继续策略3 合并结果。

### 2.3 修复方案（源码级设计）

#### 修复 1：extractWithWebView 移除外层 withTimeoutOrNull

**修改位置**：`ImageUrlExtractor.kt` L583-612

**修改前**：
```kotlin
return webviewMutex.withLock {
    try {
        withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS) {
            ImageSnifferWebView(...).sniffImageUrls()
        } ?: run {
            AppLog.putDebugWithTag(..., "L2 webview sniff timeout(${L2_WEBVIEW_TIMEOUT_MS}ms)", ...)
            emptyList()
        }
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        AppLog.putDebugWithTag(..., "L2 webview sniff error: ...", ...)
        emptyList()
    }
}
```

**修改后**：
```kotlin
return webviewMutex.withLock {
    try {
        // 移除外层 withTimeoutOrNull：sniffImageUrls 内部已有 withTimeoutOrNull 超时机制
        // 超时后返回已收集的 collectedUrls（非 emptyList），外层再包超时会丢弃此返回值
        ImageSnifferWebView(
            url = link,
            headerMap = headerMap,
            tag = rssSource.sourceUrl,
            timeout = L2_WEBVIEW_TIMEOUT_MS,
            delayTime = 1500L
        ).sniffImageUrls()
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        AppLog.putDebugWithTag(
            AppLog.TAG_IMAGE_SNIFF,
            "L2 webview sniff error: ${e::class.simpleName} msg=${e.message?.take(150)}",
            throwable = e,
            level = AppLog.Level.WARN
        )
        emptyList()
    }
}
```

**修改理由**：
- `sniffImageUrls()` 内部 L75-119 已有完整的 `withTimeoutOrNull(timeout)` + 超时返回 collectedUrls + 异常处理逻辑
- 外层 withTimeoutOrNull 多余且有害：超时时间相同导致外层先超时，丢弃 sniffImageUrls 返回的已收集 URL
- 移除外层 withTimeoutOrNull 后，sniffImageUrls 内部超时返回 collectedUrls（51 张）能正确传递给调用方
- 保留 try-catch 处理 sniffImageUrls 抛出的非超时异常

#### 修复 2：策略2 命中数 < 3 时继续策略3

**修改位置**：`ImageUrlExtractor.kt` L264-289

**修改前**（L274-281）：
```kotlin
if (imgUrls.isNotEmpty()) {
    AppLog.putDebugWithTag(..., "strategy 2 (ruleImage selector) success: count=${imgUrls.size}", ...)
    return filterImageUrls(imgUrls)
}
```

**修改后**：
```kotlin
if (imgUrls.isNotEmpty()) {
    AppLog.putDebugWithTag(
        AppLog.TAG_IMAGE_SNIFF,
        "strategy 2 (ruleImage selector) success: count=${imgUrls.size}",
        level = AppLog.Level.INFO
    )
    // 命中数 < 3 时不直接 return，继续执行策略3 合并结果（应对限流/错误页面解析不足）
    if (imgUrls.size >= 3) {
        return filterImageUrls(imgUrls)
    }
    // imgUrls.size < 3：保存当前结果，继续策略3 合并
    val strategy2Result = imgUrls
    // 继续执行策略3（不 return），最后合并
    // ... 策略3 代码块结束后合并 strategy2Result + regexUrls
}
```

**完整策略2+3 合并逻辑**（需调整策略3 代码块）：
```kotlin
// 策略2
var strategy2Result: List<String> = emptyList()
if (body.contains("<") && !ruleImage.isNullOrBlank()) {
    try {
        val analyzeRule = AnalyzeRule(null, rssSource)
        analyzeRule.setContent(body)
            .setBaseUrl(NetworkUtils.getAbsoluteURL(rssSource.sourceUrl, base))
        val imgUrls = (analyzeRule.getStringList(ruleImage) ?: emptyList())
            .map { NetworkUtils.getAbsoluteURL(base, it.trim()) }
            .filter { it.startsWith("http://") || it.startsWith("https://") }
            .distinct()
        if (imgUrls.isNotEmpty()) {
            AppLog.putDebugWithTag(
                AppLog.TAG_IMAGE_SNIFF,
                "strategy 2 (ruleImage selector) success: count=${imgUrls.size}",
                level = AppLog.Level.INFO
            )
            if (imgUrls.size >= 3) {
                return filterImageUrls(imgUrls)
            }
            strategy2Result = imgUrls  // < 3 张，保存继续策略3
        }
    } catch (e: Exception) {
        AppLog.putDebugWithTag(..., "strategy 2 (ruleImage selector) failed: ...", ...)
    }
}

// 策略3
if (body.contains("<img")) {
    val lazyAttrs = LAZY_LOAD_ATTRS.joinToString("|")
    val imgRegex = Regex("""<img[^>]+(?:$lazyAttrs)\s*=\s*["']([^"']+)["']""", RegexOption.IGNORE_CASE)
    val regexUrls = imgRegex.findAll(body)
        .map { ... }
        .filter { ... }
        .distinct()
        .toList()
    if (regexUrls.isNotEmpty()) {
        AppLog.putDebugWithTag(..., "strategy 3 (regex img tag) success: count=${regexUrls.size}", ...)
        // 合并策略2 + 策略3 结果
        val merged = (strategy2Result + regexUrls).distinct()
        return filterImageUrls(merged)
    }
}
// 策略3 未命中但策略2 有结果（< 3 张），返回策略2 结果
if (strategy2Result.isNotEmpty()) {
    return filterImageUrls(strategy2Result)
}
```

**修改理由**：
- HTTP 429 限流时策略2 仅命中 1 张，但策略3 可能从 <img> 标签提取更多 URL
- 命中数 < 3 视为"不足"，继续策略3 合并结果
- 命中数 ≥ 3 视为"充足"，直接 return（保持原逻辑，避免不必要的策略3 计算）
- 使用 distinct() 去重，避免策略2+3 重复 URL

### 2.4 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 移除外层 withTimeoutOrNull 后 L2 卡死 | 低 | sniffImageUrls 内部 withTimeoutOrNull 仍生效（6s 超时）+ destroy() 释放 WebView |
| 策略2+3 合并重复 URL | 低 | distinct() 去重 + filterImageUrls 过滤 |
| 策略2 < 3 阈值不合理 | 中 | 可后续调整为可配置阈值，当前 3 为经验值 |
| sniffImageUrls 抛出非 CancellationException 异常 | 低 | try-catch 兜底返回 emptyList |

### 2.5 回退方案

若修复后 Q2 问题仍存在，回退方案：
1. 恢复 extractWithWebView 外层 withTimeoutOrNull（但将外层超时设为 L2_WEBVIEW_TIMEOUT_MS + 2000ms 缓冲，避免外层先超时）
2. 恢复策略2 命中后直接 return 逻辑
3. 在 sniffImageUrls 内部增加 `getCollectedUrls()` 公共方法，extractWithWebView 超时后主动调用获取已收集 URL

---

## 3. Q3 根因分析与设计：无限刷牙（降级链循环）

### 3.1 日志证据链

| 日志行范围 | 现象（脱敏） | 分析结论 |
|-----------|-------------|---------|
| L2584-2696 | 同一 URL（/path/-205780509）反复触发 fallback-1→2→3→1→2→3→1... | 降级链计数器被重置，无限循环 |

### 3.2 根因分析

#### 根因：bind 无条件重置 retryCount + markPreheatReload 触发 notifyItemChanged

**源码位置 1**：`ImageCanvasAdapter.kt` L449-454 bind

**当前代码**：
```kotlin
fun bind(item: ImageCanvasItem.ImageItem, position: Int) {
    currentUrl = item.url
    currentPosition = position
    currentItem = item
    retryCount = 0  // L454 无条件重置降级链计数器
    // ... 后续代码
}
```

**源码位置 2**：`ImageCanvasAdapter.kt` L125-134 markPreheatReload

**当前代码**：
```kotlin
fun markPreheatReload(positions: Collection<Int>) {
    if (positions.isEmpty()) return
    preheatReloadPositions.addAll(positions)
    AppLog.putDebugWithTag(...)
    positions.forEach { notifyItemChanged(it) }  // 触发重新 bind
}
```

**源码位置 3**：`ImageCanvasAdapter.kt` L489 bind 内 isPreheatReload 计算

**当前代码**：
```kotlin
val isPreheatReload = preheatReloadPositions.remove(position)
val requestOptions = buildRequestOptions(
    sourceOrigin, effectiveReferer,
    skipMemory = isPreheatReload,
    bypassFailCache = isPreheatReload
)
```

**循环链路分析**：
1. 图片加载失败 → `triggerFallbackChain` 降级3 → `onWebViewFallback` 启动 WebView 预热
2. 预热完成 → `markPreheatReload(positions)` → `notifyItemChanged(it)`（L133）
3. `notifyItemChanged` 触发 RecyclerView 重新 bind 该 position
4. bind 方法 L454 `retryCount = 0` 无条件重置降级链计数器
5. bind 方法 L489 计算 `isPreheatReload = true`，使用 `skipMemory=true, bypassFailCache=true` 重新加载
6. 重新加载仍失败（防盗链/限流未解除）→ `triggerFallbackChain` 从 retryCount=0 开始降级1
7. 降级1→2→3→预热→markPreheatReload→notifyItemChanged→bind→retryCount=0→降级1... **无限循环**

**关键问题**：bind 方法 L454 在 L489 计算 isPreheatReload **之前**就无条件重置了 retryCount，导致预热重载场景的降级链计数器被错误重置。

### 3.3 修复方案（源码级设计）

#### 修复：bind 方法根据 isPreheatReload 决定是否重置 retryCount

**修改位置**：`ImageCanvasAdapter.kt` L450-495 bind

**修改前**（L450-495 关键部分）：
```kotlin
fun bind(item: ImageCanvasItem.ImageItem, position: Int) {
    currentUrl = item.url
    currentPosition = position
    currentItem = item
    retryCount = 0  // L454 无条件重置

    // AD-13: 重置为默认高度...
    val defaultHeight = ...
    // ... 重置高度、清空 Glide、复位视图

    val sourceOrigin = resolveSourceOrigin()
    val articleLink = resolveArticleLink(item.articleIndex)
    if (sourceOrigin == null && articleLink == null) {
        logHeadersMissing(position, item.articleIndex)
    }
    sourceHeaderMap = ImagePlay.rssSource?.getHeaderMap()
    val effectiveReferer = extractReferer(sourceHeaderMap) ?: articleLink

    // L489 isPreheatReload 计算在 retryCount 重置之后！
    val isPreheatReload = preheatReloadPositions.remove(position)
    val requestOptions = buildRequestOptions(
        sourceOrigin, effectiveReferer,
        skipMemory = isPreheatReload,
        bypassFailCache = isPreheatReload
    )
    loadImage(item.url, requestOptions, position)
    // ...
}
```

**修改后**：
```kotlin
fun bind(item: ImageCanvasItem.ImageItem, position: Int) {
    currentUrl = item.url
    currentPosition = position
    currentItem = item

    // 修复 Q3：将 isPreheatReload 计算前移，根据 isPreheatReload 决定是否重置 retryCount
    // 预热重载场景不重置 retryCount，避免降级链循环（fallback-1→2→3→1→2→3 无限循环）
    val isPreheatReload = preheatReloadPositions.remove(position)
    if (isPreheatReload) {
        // 预热重载：保留 retryCount，降级链续接（降级3 后仍失败则进入降级4，而非重置到降级1）
        AppLog.putDebugWithTag(
            AppLog.TAG_IMAGE_CANVAS,
            "bind: preheat reload, retryCount preserved=$retryCount position=$position",
            level = AppLog.Level.INFO
        )
    } else {
        // 正常绑定/复用：重置降级链计数器
        retryCount = 0
    }

    // AD-13: 重置为默认高度...
    val defaultHeight = (itemView.resources.displayMetrics.heightPixels * 0.6).toInt()
    val lp = itemView.layoutParams
    lp.height = defaultHeight
    itemView.layoutParams = lp

    // AD-13 + Phase 3.2: 清空旧图片 + 取消未完成下载 + 复位双视图
    if (isGlideUsable()) Glide.with(itemView.context).clear(binding.photoView)
    cancelPendingDownload()
    binding.ssivView.visibility = View.GONE
    binding.ssivView.recycle()
    binding.photoView.visibility = View.VISIBLE

    binding.photoView.transitionName = "shared_image_$position"

    val sourceOrigin = resolveSourceOrigin()
    val articleLink = resolveArticleLink(item.articleIndex)
    if (sourceOrigin == null && articleLink == null) {
        logHeadersMissing(position, item.articleIndex)
    }
    sourceHeaderMap = ImagePlay.rssSource?.getHeaderMap()
    val effectiveReferer = extractReferer(sourceHeaderMap) ?: articleLink

    // isPreheatReload 已在前方计算，此处直接使用
    val requestOptions = buildRequestOptions(
        sourceOrigin, effectiveReferer,
        skipMemory = isPreheatReload,
        bypassFailCache = isPreheatReload
    )
    loadImage(item.url, requestOptions, position)
    // ...
}
```

**修改理由**：
- 将 `isPreheatReload` 计算从 L489 前移到 L454 之前
- 预热重载场景（isPreheatReload=true）：保留 retryCount，降级链续接。降级3 预热后重载仍失败 → triggerFallbackChain 中 retryCount=3 → 进入 `else` 分支降级4（网页模式回退），而非重置到降级1
- 正常绑定/复用场景（isPreheatReload=false）：重置 retryCount=0，保持原有行为
- 新增日志记录预热重载场景的 retryCount 保留情况，便于验证

### 3.4 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 正常首次绑定场景 retryCount 未重置导致降级链异常 | 低 | isPreheatReload=false 时仍重置 retryCount=0，仅预热场景保留 |
| 预热后重载成功但 retryCount 保留影响下次复用 | 低 | ViewHolder 复用时（非预热）isPreheatReload=false，retryCount 重置 |
| 预热后重载仍失败进入降级4 网页模式，用户体验下降 | 中 | 降级4 是预期的最终兜底，优于无限循环 |
| isPreheatReload 计算前移影响后续代码逻辑 | 低 | isPreheatReload 仅用于 buildRequestOptions，前移不影响逻辑 |

### 3.5 回退方案

若修复后 Q3 问题仍存在，回退方案：
1. 恢复 L454 `retryCount = 0` 无条件重置
2. markPreheatReload 改为不触发 notifyItemChanged，直接调用 ViewHolder 的 loadImage 方法重试（需暴露 ViewHolder 引用）
3. 在 triggerFallbackChain 中增加同 URL 降级次数硬上限（如 5 次后强制进入降级4），避免无限循环

---

## 4. 整体风险评估

### 4.1 修复优先级

| 优先级 | 问题 | 修复难度 | 用户感知 |
|--------|------|---------|---------|
| P0 | Q3 无限降级循环 | 中 | 高（图片反复闪烁，影响阅读） |
| P0 | Q2 L2 超时丢弃 URL | 低 | 高（图片数量缺失 51/52） |
| P1 | Q1 滚动位置 | 中 | 中（需手动滚动，非功能性阻断） |

### 4.2 整体回退方案

若 3 个修复引入新问题，整体回退步骤：
1. git revert 修复 commit
2. 恢复 4 个源码文件到修复前状态
3. 重新编译测试包验证回退后行为

### 4.3 测试策略

| 测试类型 | 测试范围 | 测试方法 |
|---------|---------|---------|
| 单元测试 | enhancedParseImageUrls 策略2+3 合并逻辑 | Mock body + ruleContent，验证合并结果 |
| 真机测试 | 3 个问题的验收标准 | 使用测试包（io.legado.miss.app.debug） |
| 日志分析 | 日志行号对应的关键日志 | Grep 关键日志标签验证 |

---

## 5. 源码核实附录

### 5.1 核实的源码文件

| 文件 | 核实行段 | 核实结论 |
|------|---------|---------|
| `ImageCanvasAdapter.kt` | L120-135（markPreheatReload） | 确认 notifyItemChanged 触发 re-bind |
| `ImageCanvasAdapter.kt` | L241-265（onCreateViewHolder） | 确认 defaultHeight 使用 apply 修改模式 |
| `ImageCanvasAdapter.kt` | L447-501（bind） | 确认 L454 retryCount=0 无条件重置，L489 isPreheatReload 已存在 |
| `ImageCanvasAdapter.kt` | L777-860（triggerFallbackChain） | 确认 when retryCount 降级链逻辑 |
| `ImageGalleryActivity.kt` | L692-714（observeNewItems） | 确认 isInitialScrollDone 使用 post 而非 OnGlobalLayoutListener |
| `ImageUrlExtractor.kt` | L231-289（策略2） | 确认命中后直接 return filterImageUrls(imgUrls) |
| `ImageUrlExtractor.kt` | L291-316（策略3） | 确认策略3 独立 return |
| `ImageUrlExtractor.kt` | L565-613（extractWithWebView） | 确认外层 withTimeoutOrNull 超时返回 emptyList |
| `ImageSnifferWebView.kt` | L75-119（sniffImageUrls） | **确认内部已实现超时返回 collectedUrls（L100-107），无需修改** |
| `ImageSnifferWebView.kt` | L60（collectedUrls） | 确认 ConcurrentHashMap 线程安全收集 |

### 5.2 原始修复方案修正记录

| 修正项 | 原始方案 | 源码核实后修正 |
|--------|---------|---------------|
| Q2 修复1 | sniffImageUrls 改为超时返回已收集 URL | sniffImageUrls 内部已实现，改为 extractWithWebView 移除外层 withTimeoutOrNull |
| Q3 修复1 | 新增 isPreheatReload 参数 | isPreheatReload 已存在（L489），改为根据 isPreheatReload 决定是否重置 retryCount |
