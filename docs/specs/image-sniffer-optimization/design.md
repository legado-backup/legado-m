# 图片播放器前置嗅探能力优化 - 技术设计

> **版本**：v1
> **创建日期**：2026-07-27
> **状态**：待审查
> **参考文档**：
> - [调研报告](../../temp-analysis/image-sniffer-research-20260727.md)
> - [当前源码分析](../../temp-analysis/image-sniffer-current-analysis-20260727.md)
> - 视频嗅探架构：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`

---

## 一、架构设计

### 1.1 整体架构（三层降级链路）

```
ImageCanvasViewModel.loadArticleInternal()
  └─ ImageUrlExtractor.extractImageList(article, rssSource, ruleContent, ruleImage)
       │
       ├─ Layer 1: 静态解析（enhancedParseImageUrls）
       │    ├─ 用户规则优先（ruleContent + ruleImage 走 AnalyzeRule）
       │    ├─ 策略1: 纯 URL 列表 split（保留现有）
       │    ├─ 策略2: ruleImage 选择器（保留现有）
       │    ├─ 策略3: <img> 标签正则（保留现有，扩展懒加载属性）
       │    ├─ 策略3.5: <picture>/<source> 标签（新增）
       │    ├─ 策略3.6: CSS background-image（新增）
       │    ├─ 策略3.7: og:image Meta 标签（新增）
       │    ├─ 策略3.8: Script JSON 提取（新增）
       │    ├─ 策略3.9: JS 变量提取（新增）
       │    ├─ 策略4: 所有 http URL 正则 + 图片扩展名白/黑名单（增强）
       │    └─ 策略5: 单 URL 兜底（保留现有）
       │
       ├─ Layer 2: WebView 嗅探（extractWithWebView）
       │    ├─ BackstageWebView 构造（sourceRegex = 图片扩展名正则）
       │    ├─ IMAGE_SNIFF_JS 注入（5 路 hook）
       │    │    ├─ hook Image.src setter
       │    │    ├─ hook HTMLImageElement.src setter
       │    │    ├─ hook fetch / XHR
       │    │    ├─ hook IntersectionObserver
       │    │    └─ hook document.write
       │    ├─ shouldInterceptRequest 拦截 Content-Type: image/*
       │    └─ 6s 超时兜底
       │
       └─ Layer 3: 兜底返回（返回已捕获的图片 URL 列表）
```

### 1.2 核心组件

#### 1.2.1 新建 `ImageUrlExtractor.kt`

**位置**：`app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt`

**职责**：
1. 封装三层降级链路
2. 协调 Layer 1 静态解析 / Layer 2 WebView 嗅探 / Layer 3 兜底
3. 超时控制（总 12s + 分层超时）
4. 日志输出（tag: `AppLog.TAG_IMAGE_SNIFFER`）

**接口设计**：

```kotlin
object ImageUrlExtractor {
    private const val TAG = "ImageUrlExtractor"
    private const val TOTAL_TIMEOUT_MS = 12_000L
    private const val L1_STATIC_TIMEOUT_MS = 500L
    private const val L2_WEBVIEW_TIMEOUT_MS = 6_000L

    /**
     * 提取图片 URL 列表（三层降级链路）
     *
     * @param article RssArticle 文章对象
     * @param rssSource RssSource 订阅源（含 ruleContent/ruleImage/sourceUrl）
     * @param ruleContent 用户内容规则（可为空）
     * @param ruleImage 用户图片规则（可为空）
     * @return List<String> 图片 URL 列表（可能为空，不抛异常）
     */
    suspend fun extractImageList(
        article: RssArticle,
        rssSource: RssSource,
        ruleContent: String?,
        ruleImage: String?
    ): List<String>

    /**
     * Layer 1: 静态解析（增强版 parseImageUrls）
     *
     * 触发条件：总是先尝试 L1
     * 失败条件：返回图片数 < 3 时触发 L2
     */
    private suspend fun extractWithStatic(
        article: RssArticle,
        rssSource: RssSource,
        ruleContent: String?,
        ruleImage: String?
    ): List<String>

    /**
     * Layer 2: WebView 嗅探
     *
     * 触发条件：L1 返回 < 3 张图片
     * 实现方式：BackstageWebView 加载页面 + IMAGE_SNIFF_JS hook + shouldInterceptRequest 拦截
     * 超时：6s
     */
    private suspend fun extractWithWebView(
        article: RssArticle,
        rssSource: RssSource
    ): List<String>
}
```

#### 1.2.2 IMAGE_SNIFF_JS（参考 VIDEO_SNIFF_JS）

**位置**：`ImageUrlExtractor.kt` 内部常量

**Hook 设计**（5 路）：

```javascript
// 1. Hook Image.src setter
(function() {
    var originalSrc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
    Object.defineProperty(HTMLImageElement.prototype, 'src', {
        set: function(val) {
            if (val && typeof val === 'string' && val.match(/^https?:\/\//)) {
                window._imageSnifferUrls = window._imageSnifferUrls || [];
                if (window._imageSnifferUrls.indexOf(val) === -1) {
                    window._imageSnifferUrls.push(val);
                }
            }
            originalSrc.set.call(this, val);
        },
        get: function() { return originalSrc.get.call(this); }
    });
})();

// 2. Hook fetch
(function() {
    var originalFetch = window.fetch;
    window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input && input.url);
        if (url && url.match(/\.(jpg|jpeg|png|webp|gif|svg|avif|bmp)/i)) {
            window._imageSnifferUrls = window._imageSnifferUrls || [];
            if (window._imageSnifferUrls.indexOf(url) === -1) {
                window._imageSnifferUrls.push(url);
            }
        }
        return originalFetch.apply(this, arguments);
    };
})();

// 3. Hook XMLHttpRequest
(function() {
    var originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        if (url && url.match(/\.(jpg|jpeg|png|webp|gif|svg|avif|bmp)/i)) {
            window._imageSnifferUrls = window._imageSnifferUrls || [];
            if (window._imageSnifferUrls.indexOf(url) === -1) {
                window._imageSnifferUrls.push(url);
            }
        }
        return originalOpen.apply(this, arguments);
    };
})();

// 4. Hook IntersectionObserver（懒加载触发后回传 src）
(function() {
    var originalIO = window.IntersectionObserver;
    if (originalIO) {
        window.IntersectionObserver = function(callback, options) {
            var wrappedCallback = function(entries, observer) {
                entries.forEach(function(entry) {
                    if (entry.target && entry.target.tagName === 'IMG' && entry.target.src) {
                        window._imageSnifferUrls = window._imageSnifferUrls || [];
                        if (window._imageSnifferUrls.indexOf(entry.target.src) === -1) {
                            window._imageSnifferUrls.push(entry.target.src);
                        }
                    }
                });
                return callback(entries, observer);
            };
            return new originalIO(wrappedCallback, options);
        };
    }
})();

// 5. Hook document.write（捕获内联脚本中的图片）
(function() {
    var originalWrite = document.write;
    document.write = function(content) {
        if (content && typeof content === 'string') {
            var imgRegex = /<img[^>]+src\s*=\s*["']([^"']+)["']/gi;
            var match;
            while ((match = imgRegex.exec(content)) !== null) {
                if (match[1] && match[1].match(/^https?:\/\//)) {
                    window._imageSnifferUrls = window._imageSnifferUrls || [];
                    if (window._imageSnifferUrls.indexOf(match[1]) === -1) {
                        window._imageSnifferUrls.push(match[1]);
                    }
                }
            }
        }
        return originalWrite.apply(this, arguments);
    };
})();
```

#### 1.2.3 静态解析增强（parseImageUrls 升级）

**新增策略**（在现有策略3 和策略4 之间插入）：

```kotlin
/**
 * 策略3.5: <picture>/<source> 标签嗅探（P1-1）
 */
private fun parsePictureSource(body: String, baseUrl: String): List<String> {
    // 提取 <picture><source srcset="url1 480w, url2 800w"> 中的 srcset
    val sourceRegex = Regex(
        """<source[^>]+srcset\s*=\s*["']([^"']+)["']""",
        RegexOption.IGNORE_CASE
    )
    return sourceRegex.findAll(body)
        .flatMap { matchResult ->
            // srcset 按逗号分割，每段取第一个空格前的 URL
            matchResult.groupValues[1].split(",")
                .map { it.trim().split(" ")[0] }
                .filter { it.startsWith("http://") || it.startsWith("https://") }
        }
        .map { NetworkUtils.getAbsoluteURL(baseUrl, it) }
        .distinct()
        .toList()
}

/**
 * 策略3.6: CSS background-image 嗅探（P1-2）
 */
private fun parseBackgroundImage(body: String, baseUrl: String): List<String> {
    // 提取 background-image: url(...) / background: url(...)
    val bgRegex = Regex(
        """background(?:-image)?\s*:\s*url\(["']?([^"')]+)["']?\)""",
        RegexOption.IGNORE_CASE
    )
    return bgRegex.findAll(body)
        .map { it.groupValues[1].trim() }
        .filter { it.startsWith("http://") || it.startsWith("https://") || it.startsWith("/") }
        .map { NetworkUtils.getAbsoluteURL(baseUrl, it) }
        .filter { it.startsWith("http://") || it.startsWith("https://") }
        .distinct()
        .toList()
}

/**
 * 策略3.7: og:image Meta 标签嗅探（P1-4）
 */
private fun parseOgImage(body: String, baseUrl: String): List<String> {
    // 提取 <meta property="og:image" content="...">
    val metaRegex = Regex(
        """<meta[^>]+property\s*=\s*["']og:image(?:url)?["'][^>]+content\s*=\s*["']([^"']+)["']""",
        RegexOption.IGNORE_CASE
    )
    return metaRegex.findAll(body)
        .map { it.groupValues[1].trim() }
        .map { NetworkUtils.getAbsoluteURL(baseUrl, it) }
        .filter { it.startsWith("http://") || it.startsWith("https://") }
        .distinct()
        .toList()
}

/**
 * 策略3.8: Script JSON 提取（P1-5）
 *
 * 提取 <script> 标签内 JSON 中的图片 URL：
 * - {"image":"url"} / {"images":["url1","url2"]}
 * - {"image_url":"url"} / {"image_list":["url1","url2"]}
 * - {"@type":"ImageObject","url":"..."}
 */
private fun parseScriptJson(body: String, baseUrl: String): List<String> {
    // 提取 <script>...</script> 内容
    val scriptRegex = Regex("""<script[^>]*>([\s\S]*?)</script>""", RegexOption.IGNORE_CASE)
    val jsonUrlRegex = Regex(
        """"(?:image|images|image_url|image_list|url|@id)"\s*:\s*(?:"([^"]+)"|\[([^\]]+)\])""",
        RegexOption.IGNORE_CASE
    )
    return scriptRegex.findAll(body)
        .flatMap { scriptMatch ->
            jsonUrlRegex.findAll(scriptMatch.groupValues[1])
                .flatMap { jsonMatch ->
                    val singleUrl = jsonMatch.groupValues[1]
                    val urlArray = jsonMatch.groupValues[2]
                    if (singleUrl.isNotEmpty()) listOf(singleUrl)
                    else urlArray.split(",")
                        .map { it.trim().trim('"') }
                        .filter { it.isNotEmpty() }
                }
        }
        .map { it.trim() }
        .filter { it.startsWith("http://") || it.startsWith("https://") }
        .map { NetworkUtils.getAbsoluteURL(baseUrl, it) }
        .distinct()
        .toList()
}

/**
 * 策略3.9: JS 变量提取（P1-6）
 *
 * 提取 JS 变量赋值中的图片 URL：
 * - var images = ["url1","url2"]
 * - const imgs = ['url1','url2']
 * - let imageList = ["url1","url2"]
 */
private fun parseJsVariables(body: String, baseUrl: String): List<String> {
    val jsVarRegex = Regex(
        """(?:var|let|const)\s+\w*(?:image|img|pic|photo)s?\w*\s*=\s*\[([^\]]+)\]""",
        RegexOption.IGNORE_CASE
    )
    val urlRegex = Regex("""["']([^"']+)["']""")
    return jsVarRegex.findAll(body)
        .flatMap { varMatch ->
            urlRegex.findAll(varMatch.groupValues[1])
                .map { it.groupValues[1].trim() }
        }
        .filter { it.startsWith("http://") || it.startsWith("https://") }
        .map { NetworkUtils.getAbsoluteURL(baseUrl, it) }
        .distinct()
        .toList()
}

/**
 * 策略4 增强：图片扩展名白名单/黑名单（P1-7）
 */
private val IMAGE_EXTENSION_WHITELIST = setOf(
    "jpg", "jpeg", "png", "webp", "gif", "svg", "avif", "bmp"
)
private val URL_EXTENSION_BLACKLIST = setOf(
    "js", "css", "html", "htm", "json", "woff", "woff2", "ttf", "eot", "ico"
)

private fun filterImageUrls(urls: List<String>): List<String> {
    return urls.filter { url ->
        val ext = url.substringBefore("?").substringAfterLast(".").lowercase()
        when {
            ext in IMAGE_EXTENSION_WHITELIST -> true
            ext in URL_EXTENSION_BLACKLIST -> false
            else -> true // 无扩展名或未知扩展名，保留（Content-Type 校验交给 Glide）
        }
    }
}

/**
 * 策略3 增强：懒加载属性扩展（P1-8）
 */
private val LAZY_LOAD_ATTRS = listOf(
    "src", "data-src", "data-original", "data-lazy-src", "data-lazy",
    "realsrc", "data-srcset", "srcset",
    // 新增懒加载属性
    "data-url", "data-img", "data-lazy-srcset", "data-original-src",
    "data-echo", "data-img-src", "data-delay", "data-lazy"
)
```

### 1.3 数据流

#### 1.3.1 主流程

```
1. ImageCanvasViewModel.loadArticleInternal(articleIndex, isInitial)
2. 调用 ImageUrlExtractor.extractImageList(article, rssSource, ruleContent, ruleImage)
3. ImageUrlExtractor 内部：
   ├─ L1: extractWithStatic()
   │    ├─ Rss.getContentAwait(article, effectiveRule, rssSource)  // 获取 body
   │    └─ enhancedParseImageUrls(body, baseUrl, ruleImage, rssSource)
   │         ├─ 策略1-5（保留现有）
   │         └─ 策略3.5-3.9（新增）
   │
   ├─ if (L1.size < 3) L2: extractWithWebView()
   │    ├─ BackstageWebView 构造（sourceRegex = 图片扩展名正则）
   │    ├─ pageLoadUrl = article.link
   │    ├─ 注入 IMAGE_SNIFF_JS
   │    ├─ shouldInterceptRequest 拦截 image/* 资源
   │    ├─ 6s 超时
   │    └─ 收集 _imageSnifferUrls + shouldInterceptRequest 拦截结果
   │
   └─ L3: 兜底返回（L1 + L2 合并去重）
4. 返回 List<String> 给 ImageCanvasViewModel
5. ImageCanvasViewModel 转换为 ImageCanvasItem.ImageItem 列表
6. ImagePlay.appendItems(imageItems)
```

#### 1.3.2 错误降级

```
L1 失败（解析异常 / body 为空）→ 直接进入 L2
L2 失败（WebView 加载超时 / JS hook 异常）→ 返回 L1 已捕获的图片
L1 + L2 全失败 → 返回空列表（不抛异常，UI 显示"无图片"）
```

---

## 二、关键接口设计

### 2.1 ImageUrlExtractor 接口

```kotlin
object ImageUrlExtractor {
    /**
     * 提取图片 URL 列表（三层降级链路）
     *
     * @param article RssArticle 文章对象
     * @param rssSource RssSource 订阅源
     * @param ruleContent 用户内容规则（可为空）
     * @param ruleImage 用户图片规则（可为空）
     * @return List<String> 图片 URL 列表（可能为空，不抛异常）
     */
    suspend fun extractImageList(
        article: RssArticle,
        rssSource: RssSource,
        ruleContent: String?,
        ruleImage: String?
    ): List<String>
}
```

### 2.2 ImageCanvasViewModel 集成

```kotlin
// 修改前（ImageCanvasViewModel.kt:287-302）
val body = Rss.getContentAwait(article, effectiveRule, rssSource)
currentCoroutineContext().ensureActive()
val imageUrls = parseImageUrls(body, article.link ?: "", ruleImage, rssSource)

// 修改后
val imageUrls = ImageUrlExtractor.extractImageList(
    article = article,
    rssSource = rssSource,
    ruleContent = ruleContent,
    ruleImage = ruleImage
)
currentCoroutineContext().ensureActive()
```

### 2.3 AppLog tag 新增

```kotlin
// AppLog.kt 新增
const val TAG_IMAGE_SNIFFER = "ImageSniffer"
```

---

## 三、关键技术决策

### 3.1 为何不修改 Rss.getContentAwait

**决策**：不修改 `Rss.getContentAwait` 的核心逻辑

**理由**：
1. `Rss.getContentAwait` 是 Rss 模块的核心方法，修改影响面大（视频/文章/图片都依赖）
2. WebView 嗅探需要的是页面 URL（`article.link`），不是 ruleContent 解析结果
3. Layer 2 直接用 `article.link` 加载 WebView，绕过 ruleContent

### 3.2 为何复用 BackstageWebView 而非新建

**决策**：复用 `BackstageWebView`

**理由**：
1. BackstageWebView 已实现 `shouldInterceptRequest` + `sourceRegex` + `interceptAllRequests` + `videoSniffJs` 四参数能力
2. 图片嗅探只需替换 `sourceRegex`（图片扩展名正则）和 `videoSniffJs`（替换为 `IMAGE_SNIFF_JS`）
3. 避免重复造轮子，保持架构一致性

### 3.3 为何 L1 失败阈值是 < 3 张

**决策**：L1 返回 < 3 张图片时触发 L2

**理由**：
1. 1-2 张图片可能是页面 logo / icon / 占位图，不是正文图片
2. 3 张以上才算"正文图片列表"（图集站点通常 5-50 张）
3. 避免对单图站点（如博客封面）频繁触发 WebView 嗅探浪费资源

### 3.4 为何 WebView 超时是 6s

**决策**：L2 WebView 嗅探超时 6s

**理由**：
1. 对齐视频嗅探的 6s 分层超时（VideoUrlExtractor.kt:507）
2. 6s 足以覆盖页面加载 + JS hook 触发 + 懒加载 IntersectionObserver
3. 总超时 12s（L1 500ms + L2 6s + L3 5.5s）符合用户容忍度

### 3.5 为何不引入 jsoup 解析替代正则

**决策**：Phase A/B 不引入 jsoup 解析，Phase C 考虑

**理由**：
1. 现有正则方案对 80% 场景已足够（仅跨行/无引号场景失效）
2. jsoup 解析性能开销（DOM 树构建）高于正则
3. Phase A/B 优先解决 WebView 嗅探层（P0），Phase C 再优化正则精度

---

## 四、风险与缓解

### 4.1 风险1：WebView 内存泄漏

**风险**：BackstageWebView 未正确销毁导致内存泄漏

**缓解**：
1. 使用 `WeakReference` 持有 WebView
2. `onDestroy` 调用 `webview.destroy()` + `webview = null`
3. 协程取消时同步销毁 WebView
4. 添加内存监控日志（`AppLog.putDebugWithTag` + `level=WARN`）

### 4.2 风险2：JS hook 影响页面渲染

**风险**：IMAGE_SNIFF_JS hook `Image.src` / `fetch` / `XHR` 可能影响页面正常渲染

**缓解**：
1. Hook 函数保持原语义（仅记录 URL，不修改行为）
2. Hook 函数添加 try-catch（异常时不影响原逻辑）
3. 添加性能监控日志（页面加载耗时 + JS hook 耗时）

### 4.3 风险3：shouldInterceptRequest 误拦截

**风险**：拦截非图片资源（如 JS/CSS/字体）导致页面渲染失败

**缓解**：
1. `sourceRegex` 仅匹配图片扩展名（`.jpg/.jpeg/.png/.webp/.gif/.svg/.avif/.bmp`）
2. 拦截后不修改响应，仅记录 URL
3. `interceptAllRequests = false`（不拦截所有请求，仅记录）

### 4.4 风险4：用户规则场景下的兼容性

**风险**：用户写 ruleContent/ruleImage 时，新逻辑可能破坏现有行为

**缓解**：
1. L1 优先走用户规则（`ruleContent` + `ruleImage` 走 AnalyzeRule）
2. 用户规则返回 ≥ 3 张图片时不触发 L2
3. 用户规则失败时降级到 L2（增强用户体验）
4. 添加开关：`AppConfig.enableImageSniffer`（默认 true，用户可关闭）

### 4.5 风险5：协程取消未清理 WebView

**风险**：用户快速切换文章时，协程取消但 WebView 未销毁

**缓解**：
1. `extractWithWebView` 使用 `tryFinally`，无论成功/失败/取消都销毁 WebView
2. 协程取消时触发 `onCancel` 回调，销毁 WebView
3. 添加并发守卫：同一时间仅 1 个 WebView 嗅探实例（`Mutex`）

---

## 五、日志设计

### 5.1 关键日志点

```kotlin
// L1 静态解析
AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "L1 static parse: articleIndex=$articleIndex ruleContentLen=${ruleContent?.length ?: 0} ruleImageLen=${ruleImage?.length ?: 0} bodyLen=${body.length} resultCount=${urls.size}",
    level = AppLog.Level.INFO)

// L2 WebView 嗅探
AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "L2 webview sniff start: articleIndex=$articleIndex urlPath=${article.link?.take(2)}***",
    level = AppLog.Level.INFO)

AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "L2 webview sniff progress: intercepted=${interceptedUrls.size} hooked=${hookedUrls.size}",
    level = AppLog.Level.INFO)

AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "L2 webview sniff done: total=${allUrls.size} elapsed=${elapsedMs}ms",
    level = AppLog.Level.INFO)

// L3 兜底
AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "L3 fallback: L1=${l1Count} L2=${l2Count} merged=${mergedCount}",
    level = AppLog.Level.INFO)

// 错误降级
AppLog.putDebugWithTag(AppLog.TAG_IMAGE_SNIFFER,
    "extractImageList error: ${e::class.simpleName} msg=${e.message?.take(200)}",
    level = AppLog.Level.ERROR)
```

### 5.2 日志安全

- URL 用路径模式 `/path/{id}` 替代，不输出真实域名
- Cookie 用 `***` 替代，仅记录长度
- Referer 用 `***` 替代，仅记录是否注入成功
