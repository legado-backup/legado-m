# design.md - 网络性能与稳定性深度优化 + 延伸版本功能借鉴

> **状态**：🔄 设计中（第四版，基于 8 份深度分析文档整合）
> **创建日期**：2026-07-06
> **最新调整**：2026-07-06（整合优化点影响分析 + 缺失功能分析）

---

## 一、Technical Approach（技术方案）

### 1.1 总体架构

本次优化采用**保守修复 + 借鉴成熟实现 + 低风险优化 + 分阶段功能借鉴**策略，不改变现有网络层架构，仅针对识别出的明确 Bug 与低/中风险优化点精准修复，并分阶段借鉴延伸版本功能。**不改变主流版本共有的设计选择**（如不重试 IOException、保持 @Synchronized、保持同步版 Cronet 拦截器）。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    网络层架构（优化后）                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  应用层                                                                  │
│  ├── WebBook（双版本协程封装）                                            │
│  │   └── CancellationException 守卫（A1）                                │
│  ├── CacheBook（章节缓存）                                               │
│  │   ├── close() 加 @Synchronized（B4）                                  │
│  │   └── 保持 @Synchronized 不变（P2-5 不实施）                          │
│  ├── Coroutine（链式协程）                                               │
│  │   └── CancellationException 守卫（A1）                                │
│  └── MainViewModel                                                       │
│      └── waitUpTocBooks 改 ConcurrentLinkedQueue（B3）                   │
├─────────────────────────────────────────────────────────────────────────┤
│  网络客户端层                                                            │
│  ├── HttpHelper                                                         │
│  │   ├── ConnectionPool(50, 5min)（C3）                                 │
│  │   ├── proxyClientCache LRU 上限 20-30（A6）                          │
│  │   └── 保持不重试 IOException（P2-1 不实施）                           │
│  ├── OkHttpUtils                                                        │
│  │   └── 307/308 重定向保持 method+body（C2，借鉴蛋蛋Max）               │
│  ├── OkHttpExceptionInterceptor                                         │
│  │   └── CancellationException 透传（A4）                                │
│  ├── SSLHelper                                                          │
│  │   └── SSLContext "TLS" 替代 "SSL"（P0-6）                            │
│  ├── CookieStore                                                        │
│  │   └── 随机删除改 LRU 淘汰（A3，优先删 tracking Cookie）              │
│  └── Cronet                                                             │
│      ├── 保持同步版拦截器不变（P2-3 不实施）                             │
│      └── customIp LruCache(100)（C5）                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  协程封装层                                                              │
│  ├── Coroutine                                                          │
│  │   └── CancellationException 守卫（A1）                                │
│  ├── ConcurrentRateLimiter                                              │
│  │   ├── 保持 synchronized 不变（P2-4 不实施）                           │
│  │   └── concurrentRecordMap 删源清理（C4）                              │
│  ├── FlowExtensions                                                     │
│  │   └── mapParallelSafe CancellationException 守卫（A1）                │
│  └── BookSourceExtensions                                               │
│      └── mutexMap 改 ConcurrentHashMap（A2）                             │
├─────────────────────────────────────────────────────────────────────────┤
│  WebView 与图片加载层                                                    │
│  ├── WebViewPool（借鉴阅读Archive）                                      │
│  │   └── closed 标志 + isActiveWebView 引用相等检查（B6）                │
│  ├── BackstageWebView                                                   │
│  │   ├── 复用回调错乱修复（A7，借鉴阅读Archive）                         │
│  │   └── runBlocking 预查询+内存缓存（B1）                               │
│  ├── BottomWebViewDialog                                                │
│  │   └── runBlocking 优化内部逻辑（B2）                                  │
│  ├── BookHelp                                                           │
│  │   └── saveImage 互斥失效修复（B5，unlock 后 remove）                  │
│  └── Glide（LegadoGlideModule + OkHttpStreamFetcher）                   │
│      └── failUrl LruCache(200)（C4）                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  缓存与资源管理层                                                        │
│  ├── AnalyzeRule                                                        │
│  │   └── stringRuleCache LruCache(64)（C4）                              │
│  └── AnalyzeUrl                                                         │
│      └── customIp LruCache(100)（C5，与 P0-7 协同）                      │
├─────────────────────────────────────────────────────────────────────────┤
│  功能借鉴层（分阶段实施）                                                │
│  ├── P0：调试工具集 + 备份选择器 + Web 端备份管理（借鉴蛋蛋Max）         │
│  ├── P1：自动任务 + 高亮规则 + 调试日志面板 + 阅读热力图 + 书籍笔记      │
│  └── P2/P3：AI 框架 + MCP 服务 + Epub 渲染引擎等（长期）                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 P0 阶段技术方案（9 项低风险优化 + 3 项短平快功能借鉴）

#### 1.2.1 CancellationException 守卫（A1 + A4）

**文件**：`Coroutine.kt`、`WebBook.kt`、`FlowExtensions.kt`、`OkHttpExceptionInterceptor.kt`

```kotlin
// Coroutine.kt L182-190
} catch (e: CancellationException) {
    throw e  // 守卫：协程取消异常必须重新抛出
} catch (e: Throwable) {
    e.printOnDebug()
    // ... 原有逻辑
}

// WebBook.kt 5 处（L88, L159, L234, L331, L436）
} catch (throwable: Throwable) {
    if (throwable is CancellationException) throw throwable  // 守卫
    throw throwable
}

// FlowExtensions.kt L59-70 mapParallelSafe
} catch (e: CancellationException) {
    throw e  // 守卫
} catch (e: Throwable) {
    emit(Result.failure(e))
}

// OkHttpExceptionInterceptor.kt L13-17
} catch (e: CancellationException) {
    throw e  // 守卫：透传协程取消异常
} catch (e: IOException) {
    throw e
} catch (e: Throwable) {
    throw IOException(e)
}
```

#### 1.2.2 mutexMap 线程安全修复（A2）

**文件**：`BookSourceExtensions.kt` L27, L50

```kotlin
// L27
private val mutexMap by lazy { ConcurrentHashMap<String, Mutex>() }

// L50
val mutex = mutexMap.computeIfAbsent(bookSourceUrl) { Mutex() }
mutex.withLock { ... }
```

#### 1.2.3 MainViewModel poll() 线程安全修复（B3）

**文件**：`MainViewModel.kt` L55

```kotlin
// L55
private val waitUpTocBooks = ConcurrentLinkedQueue<String>()  // 线程安全
// L129-140 addToWaitUp 的 @Synchronized 保留（保护复合操作）
// L148 poll() 无需改动，ConcurrentLinkedQueue.poll() 线程安全
```

#### 1.2.4 CacheBook.close() 同步修复（B4）

**文件**：`CacheBook.kt` L116-121

```kotlin
@Synchronized
fun close() {
    cacheBookMap.forEach { it.value.stop() }
    cacheBookMap.clear()
    successDownloadSet.clear()
    errorDownloadMap.clear()
}
```

#### 1.2.5 BookHelp 互斥失效修复（B5）

**文件**：`BookHelp.kt` L261-262

```kotlin
// 优化前（互斥失效）
} finally {
    downloadImages.remove(src)  // L261 ← 在 unlock 前移除
    mutex.unlock()              // L262
}

// 优化后（正确顺序）
} finally {
    mutex.unlock()                  // 先 unlock
    downloadImages.remove(src)      // 后 remove
}
```

#### 1.2.6 WebViewPool 池化修复（B6，借鉴阅读Archive）

**文件**：`WebViewPool.kt` + `BackstageWebView.kt`

```kotlin
// WebViewPool / BackstageWebView 增加
private var closed = false

private fun isActiveWebView(webView: WebView? = null): Boolean {
    if (closed) return false
    val pooled = pooledWebView ?: return false
    return webView == null || pooled.realWebView === webView  // 引用相等
}

private fun destroy() {
    if (closed && pooledWebView == null) return
    closed = true
    callback = null
    mHandler.removeCallbacksAndMessages(null)
    pooledWebView?.let { WebViewPool.release(it) }
    pooledWebView = null
}

// EvalJsRunnable.run
override fun run() {
    mWebView.get()?.evaluateJavascript(jsStr) {
        if (isActiveWebView(mWebView.get())) {  // 引用相等检查
            handleResult(it)
        }
    }
}
```

#### 1.2.7 307/308 重定向处理（C2，借鉴蛋蛋Max）

**文件**：`OkHttpUtils.kt` L29-43

```kotlin
suspend fun OkHttpClient.newCallResponse(
    retry: Int = 0,
    builder: Request.Builder.() -> Unit
): Response {
    val requestBuilder = Request.Builder()
    requestBuilder.apply(builder)
    var response: Response? = null
    var currentRequest = requestBuilder.build()
    
    for (i in 0..retry) {
        response = newCall(currentRequest).await()
        
        if (response.isSuccessful) {
            return response
        }
        
        if (response.code == 307 || response.code == 308) {
            response.header("Location")?.let { location ->
                val redirectRequest = currentRequest.newBuilder()
                    .url(location)
                    .method(currentRequest.method, currentRequest.body)  // 保持 method+body
                    .headers(currentRequest.headers)
                    .build()
                response.close()
                response = newCall(redirectRequest).await()
                
                if (response.isSuccessful) {
                    return response
                }
                
                currentRequest = redirectRequest
            }
        }
    }
    
    return response!!
}
```

#### 1.2.8 SSLContext 协议修正（P0-6）

**文件**：`SSLHelper.kt` L57

```kotlin
// 优化前
val sslContext = SSLContext.getInstance("SSL")  // "SSL" 协议已废弃

// 优化后
val sslContext = SSLContext.getInstance("TLS")  // 使用 "TLS" 协议
```

#### 1.2.9 P0 功能借鉴（3 项短平快）

**F-P0-1 调试工具集**：新增 14 个文件（6 个工具 Activity + 工具类）
- 入口：`ui/main/MyFragment` 增加"调试工具"入口
- 工具：编码转换/HTTP 请求/curl 命令/ping/正则测试/时间戳转换

**F-P0-2 备份选择器**：新增备份预览功能
- 后端：`WebServer.kt` 增加 `/backupPreview` 接口
- 前端：`BackupManager.vue` 分类预览 + 可折叠详情

**F-P0-3 Web 端备份管理**：移植蛋蛋Max 4 个增量文件
- `src/views/BackupManager.vue`
- `src/router/backupRouter.ts`
- `src/pages/backup/{index.html,main.js}`
- 修改 `router/index.ts` + `views/BookShelf.vue` + `api/api.ts`

**F-P0-4 订阅源页面选择器**（借鉴蛋蛋Max，用户主动提及，约 50 行代码）：
- 基础设施已全部就绪（strings.xml 残留字符串 + Rss.getArticles 已支持 page + NumberPickerDialog 已存在 + RssSource.ruleNextPage 已存在）
- 仅需 UI 入口接入：修改 4 个文件
  - `app/src/main/res/menu/rss_articles.xml`：新增 `menu_page` 项（`showAsAction="always"`）
  - `RssArticlesViewModel.kt`：新增 `pageLiveData`/`initialSortUrl`/`skipPage()`/`loadArticles(rssSource, targetPage)` 重载
  - `RssArticlesFragment.kt`：新增 `getCurrentPage()`/`showPageMenu()`/`showPagePicker()`/`loadArticles(targetPage)` 重载
  - `RssSortActivity.kt`：新增 `menuPage`/`updatePageMenu()`/`currentArticlesFragment()` + 菜单回调接入
- 仅当 `RssSource.ruleNextPage` 不为空时显示菜单项（无此规则的源不受影响）

### 1.3 P1 阶段技术方案（8 项中风险优化 + 5 项中等难度功能借鉴）

#### 1.3.1 CookieStore LRU 淘汰（A3）

**文件**：`CookieStore.kt` L85-90

```kotlin
while (ck.length > 4096) {
    // 优先删除 tracking Cookie
    val removeKey = cookieMap.keys.firstOrNull { key ->
        key.startsWith("_ga") || key.startsWith("_gid") || key.startsWith("_gat") ||
        key.startsWith("Hm_lvt_") || key == "_hjid"
    } ?: cookieMap.entries.maxByOrNull { it.key.length }?.key  // 其次按 key 长度降序
    ?: break
    CookieManager.removeCookie(url, removeKey)
    cookieMap.remove(removeKey)
    ck = mapToCookie(cookieMap) ?: ""
}
```

#### 1.3.2 proxyClientCache LRU 上限（A6）

**文件**：`HttpHelper.kt` L25-27

```kotlin
private const val MAX_PROXY_CLIENT_CACHE_SIZE = 20

private val proxyClientCache = object : LinkedHashMap<String, OkHttpClient>(16, 0.75f, true) {
    override fun removeEldestEntry(eldest: Map.Entry<String, OkHttpClient>): Boolean {
        return size > MAX_PROXY_CLIENT_CACHE_SIZE
    }
}
private val proxyClientLock = Any()

fun getProxyClient(proxy: String? = null): OkHttpClient {
    if (proxy.isNullOrBlank()) return okHttpClient
    synchronized(proxyClientLock) {
        return proxyClientCache.getOrPut(proxy) { createProxyClient(proxy) }
    }
}
```

#### 1.3.3 BackstageWebView 复用回调错乱修复（A7）

**文件**：`BackstageWebView.kt` L243-247（与 B6 协同实施）

```kotlin
// 增加 closed 标志 + isActiveWebView 方法（同 B6）
// EvalJsRunnable.run 改为 isActiveWebView(mWebView.get()) 检查
```

#### 1.3.4 连接池调优（C3）

**文件**：`HttpHelper.kt` L51-127

```kotlin
val okHttpClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectionPool(ConnectionPool(50, 5, TimeUnit.MINUTES))  // 新增
        .connectTimeout(15, SECONDS)
        // ... 其他配置不变
        .build()
}
```

#### 1.3.5 customIp LRU 上限（C5）

**文件**：`AnalyzeUrl.kt` L773

```kotlin
private val customIp by lazy { LruCache<String, String>(100) }
// LruCache 自身线程安全，put 操作同步保护
customIp.put(urlNoQuery, dnsIp!!)
```

#### 1.3.6 BackstageWebView runBlocking 修复（B1）

**文件**：`BackstageWebView.kt` L118 + `SourceHelp.kt`

```kotlin
// SourceHelp.kt 新增
private val bookSourceCache = ConcurrentHashMap<String, BookSource>()

fun getCachedBookSource(key: String): BookSource? {
    return bookSourceCache[key]
}

fun loadBookSource(...) {
    // ... 现有逻辑
    bookSourceCache[key] = bookSource  // 同步写入缓存
}

// BackstageWebView.kt L118
tag?.let { key ->
    val source = SourceHelp.getCachedBookSource(key) ?: runBlocking(IO) { 
        appDb.bookSourceDao.getBookSource(key) 
    }
    source?.let { /* 配置 webView */ }
}
```

#### 1.3.7 BottomWebViewDialog runBlocking 优化（B2）

**文件**：`BottomWebViewDialog.kt` L819-821

```kotlin
// shouldInterceptRequest 必须 synchronous 返回，runBlocking 不可避免
// 简化说明：优化 runBlocking 内部逻辑 | 已知上限：每个主框架请求阻塞一次 | 升级路径：预加载 HTML 到内存
return runBlocking(IO) {
    getModifiedContentWithJs(url, request) ?: super.shouldInterceptRequest(view, request)
}
// getModifiedContentWithJs 内部改用同步 OkHttp 请求避免线程切换
```

#### 1.3.8 内存泄漏治理（C4）

```kotlin
// OkHttpStreamFetcher.kt - failUrl
private val failUrl = LruCache<String, Boolean>(200)

// ConcurrentRateLimiter.kt - concurrentRecordMap 删源清理
fun clearRecord(sourceUrl: String) {
    concurrentRecordMap.remove(sourceUrl)
}
// SourceHelp.kt 删源时调用
fun deleteSource(url: String) {
    // ... 现有逻辑
    ConcurrentRateLimiter.clearRecord(url)
}

// AnalyzeRule.kt - stringRuleCache
private val stringRuleCache = LruCache<String, String>(64)
```

#### 1.3.9 P1 功能借鉴（5 项中等难度）

**F-P1-1 自动任务系统**（借鉴阅读T，11 文件）：
- 新增 `data/entities/AutoTask.kt` + `data/dao/AutoTaskDao.kt`
- 新增 `service/AutoTaskService.kt`（AlarmManager 调度）
- 新增 `ui/autoTask/AutoTaskActivity.kt` 等 UI 文件
- 支持 Cron 表达式 + 书源更新/订阅源更新/书架备份等任务类型

**F-P1-2 高亮规则系统**（以阅读T 为主体 + 蛋蛋Max 补齐分组/预设/导入导出）：

> **设计决策**（基于三份子代理深度分析报告）：
> 1. **UI 来源**：以阅读T UI 为主体（StyleHost 接口解耦 + 数据驱动通道 + Activity 列表式管理 + 9 通道全暴露 + 批量转化闭环），补齐蛋蛋Max 的分组管理/预设规则/导入导出三项功能
> 2. **数据模型**：方案 A+ —— 保留现有 HighlightRule 字段不变（向后兼容），新增 `styleJson: String` 字段存储完整 HighlightStyle JSON。`toHighlightStyle()` 优先读 styleJson，没有则从旧字段映射
> 3. **实施顺序**：先底层后 UI（Phase 1-2 纯函数零风险 → Phase 3-6 渲染层集成 → Phase 7-8 UI 移植）
> 4. **不采用蛋蛋Max Span 方案**：HighlightStyleSpan 是空壳（updateDrawState 空实现），与当前项目 TextLine.draw 渲染流程不兼容，需额外 Span 解析层，收益为负

**架构总览（5 层）**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  UI 层（阅读T 为主 + 蛋蛋Max 补齐）                                       │
│  ├── HighlightRuleActivity（主入口，VMBaseActivity + RecyclerView）       │
│  │   └── HighlightRuleAdapter（列表，拖拽排序 + DiffUtil payload）        │
│  ├── HighlightRuleEditDialog（规则编辑全屏 Dialog，实现 StyleHost）        │
│  ├── HighlightStyleDialog（样式 BottomSheet，9 通道数据驱动 + 6 预设）     │
│  ├── HighlightActionMenu（手动高亮 Popup：样式/笔记/规则/复制/删除）      │
│  ├── HighlightRulePopup（规则高亮 Popup：编辑/停用）                      │
│  ├── HighlightNoteDialog（高亮备注编辑全屏 Dialog）                       │
│  ├── HighlightFragment（目录"标注"Tab）                                   │
│  ├── GroupManageDialog（蛋蛋Max 补齐：分组管理）                          │
│  ├── PresetRuleDialog（蛋蛋Max 补齐：预设规则管理）                       │
│  └── 导入导出 menu（蛋蛋Max 补齐：规则集备份迁移）                        │
├─────────────────────────────────────────────────────────────────────────┤
│  渲染层集成（修改现有文件，默认关闭策略）                                  │
│  ├── TextColumn.kt（加 highlightStyle 字段 + draw 插入 fill/style/emphasis）│
│  ├── TextLine.kt（加 drawHighlightRuns + styledColumnCount + checkFastDraw）│
│  ├── ContentTextView.kt（加 upHighlight + highlightPaint + click 分支）   │
│  └── ReadBookActivity.kt（加菜单项 + 高亮回调）                           │
├─────────────────────────────────────────────────────────────────────────┤
│  绘制层（新增，Android 依赖）                                             │
│  └── HighlightDraw.kt（Canvas 直绘：5 种下划线 + 删除线 + 方框 + 着重号） │
├─────────────────────────────────────────────────────────────────────────┤
│  匹配引擎（新增，纯函数零风险）                                           │
│  ├── HighlightRuleMatcher.kt（正则/字面量匹配 + 超时保护 3000ms）         │
│  ├── HighlightMatcher.kt（章内 pos → 每行每列样式映射）                   │
│  ├── HighlightTextBuilder.kt（文本重建，偏移对齐章内 pos）                │
│  └── HighlightGeometry.kt（波浪采样点 + 着重号圆点几何）                  │
├─────────────────────────────────────────────────────────────────────────┤
│  数据层（保留现有 + 新增样式系统）                                        │
│  ├── HighlightRule.kt（现有，保留字段 + 新增 styleJson 字段）             │
│  ├── HighlightRuleStore.kt（现有，SharedPreferences 存储）                │
│  ├── HighlightRuleGroupStore.kt（现有，分组存储）                         │
│  ├── HighlightStyle.kt（新增，9 通道样式数据类 + merge 语义）             │
│  ├── HighlightStyles.kt（新增，6 个预设样式）                             │
│  ├── HighlightColors.kt（新增，调色板 10 色）                             │
│  └── BookHighlight.kt（新增，手动高亮 Room 实体 + DAO）                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**数据模型设计（方案 A+）**：

```kotlin
// 现有 HighlightRule.kt 保留所有字段不变（向后兼容），新增 styleJson 字段
data class HighlightRule(
    // 现有字段（保留，向后兼容旧数据）
    var id: String = ...,
    var name: String = "",
    var pattern: String = "",
    var sampleText: String = "",
    var group: String = HighlightRuleGroupStore.DEFAULT_GROUP,
    var targetScope: Int = TARGET_ALL,
    var enabled: Boolean = true,
    var textColor: Int? = null,
    var underlineMode: Int = 0,        // 0=无, 1=实线, 2=虚线, 3=波浪, 4=双线, 5=SVG
    var underlineColor: Int? = null,
    var underlineWidth: Float = 1f,
    var underlineOffset: Float = 2f,
    var underlineSvgPath: String? = null,
    var bgImage: String? = null,
    var bgImageFit: Int = 0,
    var bgImageScale: Float = 1f,
    // 新增字段（存储完整 HighlightStyle JSON，9 通道）
    var styleJson: String? = null,
) {
    // 映射函数：优先读 styleJson，没有则从旧字段映射
    fun toHighlightStyle(): HighlightStyle {
        styleJson?.let { json ->
            runCatching {
                GSON.fromJsonObject<HighlightStyle>(json).getOrNull()
            }?.let { return it }
        }
        // 旧数据降级映射：textColor + underline 两个通道
        return HighlightStyle(
            textColor = textColor ?: 0,
            underline = underlineMode.takeIf { it != 0 }?.let { mode ->
                HighlightStyle.Underline(
                    kind = when (mode) {
                        1 -> HighlightStyle.Kind.SOLID
                        2 -> HighlightStyle.Kind.DASHED
                        3 -> HighlightStyle.Kind.WAVY
                        4 -> HighlightStyle.Kind.DOUBLE
                        5 -> HighlightStyle.Kind.SOLID  // SVG 降级为实线
                        else -> HighlightStyle.Kind.SOLID
                    },
                    color = underlineColor ?: 0
                )
            }
        )
    }
}

// 新增 HighlightStyle.kt（9 通道，借鉴阅读T）
data class HighlightStyle(
    val fill: Int = 0,                 // 背景填充（含 alpha；0=不填充）
    val textColor: Int = 0,            // 字体色（0=保持默认字色）
    val bold: Boolean = false,
    val italic: Boolean = false,
    val underline: Underline? = null,  // 下划线（5 种 kind）
    val strike: Deco? = null,          // 删除线
    val box: Deco? = null,             // 方框
    val emphasis: Deco? = null,        // 着重号（字下圆点）
    val fontPath: String = ""          // 自定义字体路径
) {
    data class Underline(val kind: Kind = Kind.SOLID, val color: Int = 0)
    data class Deco(val color: Int = 0)  // color==0 跟随字色
    enum class Kind { SOLID, WAVY, DASHED, DOTTED, DOUBLE }

    val isEmpty: Boolean get() = fill == 0 && textColor == 0 && !bold && !italic &&
        underline == null && strike == null && box == null && emphasis == null && fontPath.isEmpty()
    val needsPerColumnDraw: Boolean get() = bold || italic || underline != null ||
        strike != null || box != null || emphasis != null || fontPath.isNotEmpty()

    companion object {
        fun merge(base: HighlightStyle, other: HighlightStyle): HighlightStyle {
            // 按通道 last-wins 叠加，布尔通道取或，字符串通道 other 优先
            return HighlightStyle(
                fill = if (other.fill != 0) other.fill else base.fill,
                textColor = if (other.textColor != 0) other.textColor else base.textColor,
                bold = base.bold || other.bold,
                italic = base.italic || other.italic,
                underline = other.underline ?: base.underline,
                strike = other.strike ?: base.strike,
                box = other.box ?: base.box,
                emphasis = other.emphasis ?: base.emphasis,
                fontPath = other.fontPath.ifEmpty { base.fontPath }
            )
        }
    }
}
```

**匹配引擎设计（4 个纯函数文件，零 Android 依赖，JVM 可测）**：

```kotlin
// help/HighlightRuleMatcher.kt —— 正则/字面量匹配 + 超时保护
object HighlightRuleMatcher {
    data class Rule(val id: Long, val pattern: String, val isRegex: Boolean, val style: HighlightStyle, val timeoutMs: Long = 3000L)
    data class RuleMatch(val start: Int, val end: Int, val ruleId: Long, val style: HighlightStyle)

    fun match(text: String, rules: List<Rule>): List<RuleMatch> {
        if (text.isEmpty() || rules.isEmpty()) return emptyList()
        val results = mutableListOf<RuleMatch>()
        rules.forEach { rule ->
            if (rule.isRegex) matchRegex(text, rule, results) else matchLiteral(text, rule, results)
        }
        return results
    }
    // 字面量：indexOf 循环，不重叠
    // 正则：Regex.find 循环，零宽步进，超时 break，非法正则静默跳过
}

// help/HighlightMatcher.kt —— 章内 pos → 每行每列样式映射
object HighlightMatcher {
    data class Range(val start: Int, val end: Int, val style: HighlightStyle)
    data class LineSpec(val charSize: Int, val columnCharLengths: List<Int>, val isParagraphEnd: Boolean)

    fun resolve(pageBase: Int, lines: List<LineSpec>, ranges: List<Range>): List<List<HighlightStyle?>> {
        // 逐行逐列计算半开区间交集，多规则按列表序 merge
        // 位置口径：行内按 charData 长度累加，跨行按 charSize 推进，段末 +1（与 createBookmark 一致）
    }
}

// help/HighlightTextBuilder.kt —— 文本重建，偏移对齐章内 pos
object HighlightTextBuilder {
    data class LineInput(val columnTexts: String, val charSize: Int, val isParagraphEnd: Boolean)
    fun build(lines: List<LineInput>): String {
        // 逐行 append columnTexts，补齐到 charSize（用空格），段末 append '\n'
        // 保证字符串偏移 == 章内 pos，无需偏移映射表
    }
}

// help/HighlightGeometry.kt —— 波浪采样点 + 着重号圆点几何
object HighlightGeometry {
    fun wavePoints(x0: Float, x1: Float, baseY: Float, amplitude: Float, wavelength: Float, step: Float): FloatArray
    fun emphasisDots(starts: List<Float>, ends: List<Float>, cy: Float, r: Float): List<Pair<Float, Float>>
}
```

**绘制层设计（新增 HighlightDraw.kt，Android 依赖）**：

```kotlin
// ui/book/read/page/HighlightDraw.kt —— Canvas 直绘
object HighlightDraw {
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val dash = DashPathEffect(6.dp, 4.dp)
    private val dot = DashPathEffect(2.dp, 3.dp)
    private val wavePath = Path()

    // 保存/恢复 TextPaint 状态（bold/italic/fontPath）
    data class SavedTextStyle(val isFakeBoldText: Boolean, val textSkewX: Float, val typeface: Typeface?)
    fun applyTextStyle(paint: TextPaint, style: HighlightStyle): SavedTextStyle { ... }
    fun restoreTextStyle(paint: TextPaint, saved: SavedTextStyle) { ... }

    // 着重号：字下圆点
    fun drawEmphasis(canvas: Canvas, start: Float, end: Float, height: Float, color: Int) { ... }

    // 线类/方框装饰（5 种下划线 + 删除线 + 方框）
    fun drawRun(canvas: Canvas, x0: Float, x1: Float, baseline: Float, height: Float,
                underline: HighlightStyle.Underline?, strike: HighlightStyle.Deco?,
                box: HighlightStyle.Deco?, fallbackColor: Int) { ... }
}
```

**渲染层集成设计（修改 3 个现有文件，默认关闭策略）**：

```kotlin
// TextColumn.kt —— 加 highlightStyle 字段 + draw 插入
var highlightStyle: HighlightStyle? = null
    set(value) {
        if (field != value) {
            textLine.invalidate()
            textLine.styledColumnCount += if (value != null) 1 else -1  // 影响 checkFastDraw
        }
        field = value
    }

override fun draw(view, canvas) {
    val hs = highlightStyle
    // 1. 文字色：hs?.textColor != 0 优先
    // 2. 背景填充：hs?.fill != 0 → canvas.drawRect
    // 3. 文字样式：hs != null → HighlightDraw.applyTextStyle → drawText → restoreTextStyle
    // 4. 着重号：hs?.emphasis?.let { HighlightDraw.drawEmphasis(...) }
    // 5. 选中：canvas.drawRect(selectedPaint)  // 现有逻辑不变
}

// TextLine.kt —— 加 drawHighlightRuns + styledColumnCount + checkFastDraw
var styledColumnCount: Int = 0

fun drawTextLine(view, canvas) {
    if (checkFastDraw()) {
        fastDrawTextLine(view, canvas)  // 快速路径：只画 fill 背景，不画装饰
    } else {
        // 非快速路径：逐列 draw + drawHighlightRuns
        columns.forEach { it.draw(view, canvas) }
        drawHighlightRuns(view, canvas)
    }
}

private fun checkFastDraw(): Boolean {
    return styledColumnCount == 0  // 有装饰列时禁用快速路径
}

private fun drawHighlightRuns(view, canvas) {
    // 合并连续 underline/strike/box 相同的列，调 HighlightDraw.drawRun 一次性绘制
}

// ContentTextView.kt —— 加 upHighlight + highlightPaint + click 分支
private val highlightFillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
private var hasHighlightDrawn: Boolean = false

fun setContent(textPage: TextPage) {
    // 现有逻辑不变
    upHighlight()  // 追加调用
}

private fun upHighlight() {
    val rules = HighlightRuleStore.loadEnabled(context)
    if (rules.isEmpty() && ReadBook.highlightsOfChapter().isEmpty()) {
        // 无规则无手动高亮 → 清空所有 highlightStyle，走原路径
        textPage.lines.forEach { line ->
            line.columns.forEach { col -> (col as? TextColumn)?.highlightStyle = null }
        }
        hasHighlightDrawn = false
        return
    }
    // 有规则 → 构造 lineSpecs + ranges → HighlightMatcher.resolve → 写入 TextColumn.highlightStyle
    hasHighlightDrawn = true
}

// click 分支：highlightStyle != null → onHighlightClick / onHighlightRuleClick
```

**UI 层设计（阅读T 为主 + 蛋蛋Max 补齐，11+3 个 Kotlin 文件）**：

```kotlin
// 阅读T 主体（11 文件）
ui/highlight/HighlightRuleActivity.kt          // 主入口 Activity
ui/highlight/HighlightRuleAdapter.kt           // 列表 Adapter（拖拽排序 + DiffUtil）
ui/highlight/HighlightRuleViewModel.kt         // CRUD ViewModel
ui/highlight/edit/HighlightRuleEditDialog.kt   // 规则编辑全屏 Dialog（实现 StyleHost）
ui/book/read/HighlightStyleDialog.kt           // 样式 BottomSheet（9 通道数据驱动 + 6 预设）
ui/book/read/HighlightActionMenu.kt            // 手动高亮 Popup
ui/book/read/HighlightRulePopup.kt             // 规则高亮 Popup
ui/book/read/HighlightNoteDialog.kt            // 高亮备注编辑 Dialog
ui/book/toc/HighlightFragment.kt               // 目录"标注"Tab
ui/book/toc/HighlightAdapter.kt                // 标注列表 Adapter
ui/book/read/page/HighlightDraw.kt             // 绘制层（前述）

// 蛋蛋Max 补齐（3 文件）
ui/highlight/GroupManageDialog.kt              // 分组管理 Dialog
ui/highlight/PresetRuleDialog.kt               // 预设规则管理 Dialog
// 导入导出复用项目已有工具类，仅 menu 项

// 关键接口：StyleHost 双宿主复用（规则编辑 + 手动高亮编辑共用一套样式面板）
interface StyleHost {
    fun currentHighlightStyle(): HighlightStyle
    fun onHighlightStyleChanged(style: HighlightStyle)
    fun pickHighlightColor(dialogId: Int, initial: Int, withAlpha: Boolean)
    fun pickHighlightFont(current: String)
}
// 实现方一：HighlightRuleEditDialog
// 实现方二：ReadBookActivity（手动高亮编辑）
```

**文件清单（新增 22 文件 + 修改 5 文件）**：

| 类型 | 文件路径 | 来源 | 行数估算 |
|------|---------|------|---------|
| 新增 | `help/HighlightStyle.kt` | 阅读T | 52 |
| 新增 | `help/HighlightStyles.kt` | 阅读T | 17 |
| 新增 | `help/HighlightColors.kt` | 阅读T | 27 |
| 新增 | `help/HighlightRuleMatcher.kt` | 阅读T | 80 |
| 新增 | `help/HighlightMatcher.kt` | 阅读T | 70 |
| 新增 | `help/HighlightTextBuilder.kt` | 阅读T | 40 |
| 新增 | `help/HighlightGeometry.kt` | 阅读T | 35 |
| 新增 | `ui/book/read/page/HighlightDraw.kt` | 阅读T | 120 |
| 新增 | `data/entities/BookHighlight.kt` | 阅读T | 55 |
| 新增 | `data/dao/BookHighlightDao.kt` | 阅读T | 30 |
| 新增 | `ui/highlight/HighlightRuleActivity.kt` | 阅读T | 100 |
| 新增 | `ui/highlight/HighlightRuleAdapter.kt` | 阅读T | 144 |
| 新增 | `ui/highlight/HighlightRuleViewModel.kt` | 阅读T | 41 |
| 新增 | `ui/highlight/edit/HighlightRuleEditDialog.kt` | 阅读T | 251 |
| 新增 | `ui/book/read/HighlightStyleDialog.kt` | 阅读T | 234 |
| 新增 | `ui/book/read/HighlightActionMenu.kt` | 阅读T | 54 |
| 新增 | `ui/book/read/HighlightRulePopup.kt` | 阅读T | 37 |
| 新增 | `ui/book/read/HighlightNoteDialog.kt` | 阅读T | 55 |
| 新增 | `ui/book/toc/HighlightFragment.kt` | 阅读T | 103 |
| 新增 | `ui/book/toc/HighlightAdapter.kt` | 阅读T | 54 |
| 新增 | `ui/highlight/GroupManageDialog.kt` | 蛋蛋Max 补齐 | 200 |
| 新增 | `ui/highlight/PresetRuleDialog.kt` | 蛋蛋Max 补齐 | 150 |
| 新增 | 8 个布局文件 | 阅读T | 594 |
| 新增 | 1 个 menu + 26 行 strings | 阅读T | 35 |
| 修改 | `ui/book/read/config/HighlightRule.kt` | 现有+styleJson | +15 |
| 修改 | `ui/book/read/page/entities/column/TextColumn.kt` | 加字段+draw | +30 |
| 修改 | `ui/book/read/page/entities/TextLine.kt` | 加 drawHighlightRuns | +50 |
| 修改 | `ui/book/read/page/ContentTextView.kt` | 加 upHighlight | +80 |
| 修改 | `ui/book/read/ReadBookActivity.kt` | 加菜单+回调 | +40 |
| 修改 | `data/appdb/AppDatabase.kt` | v91→v92 Migration | +15 |
| **总计** | **22 新增 + 5 修改 + 8 布局 + 1 menu + 26 strings** | - | **~2700 行** |

**实施顺序（8 Phase，先底层后 UI）**：

| Phase | 内容 | 风险 | 验证 |
|-------|------|------|------|
| **1** | 复制 6 个纯函数文件（HighlightStyle/Styles/Colors/RuleMatcher/Matcher/TextBuilder/Geometry） | 🟢 零风险 | 编译通过 + JVM 单测 |
| **2** | 复制 HighlightDraw.kt + ChapterProvider 字体缓存 | 🟢 零风险 | 编译通过 |
| **3** | 修改 TextColumn（加 highlightStyle 字段 + draw 插入） | 🟡 低风险 | 编译通过 + 默认 null 不改变行为 |
| **4** | 修改 TextLine（加 drawHighlightRuns + styledColumnCount） | 🟡 低风险 | 编译通过 + styledColumnCount==0 走原路径 |
| **5** | 修改 ContentTextView（加 upHighlight + click 分支） | 🟡 低风险 | 编译通过 + 规则空时 upHighlight return |
| **6** | 新增 BookHighlight 实体 + DAO + AppDatabase v91→v92 Migration | 🟠 中风险 | 编译通过 + Migration 测试 |
| **7** | 移植 UI 11 文件（阅读T 主体） | 🟢 零风险 | 编译通过 + UI 可操作 |
| **8** | 补齐蛋蛋Max 3 文件（GroupManage/PresetRule/导入导出）+ ReadBookActivity 菜单接入 | 🟡 低风险 | 编译通过 + 端到端测试 |

**风险控制措施**：
1. 所有渲染层修改采用"默认关闭"策略（highlightStyle == null 时走原路径）
2. AppDatabase v91→v92 写 proper Migration（不用 fallbackToDestructiveMigration）
3. 位置口径必须与 createBookmark 一致（行内按 charData 长度累加，跨行按 charSize 推进，段末 +1）
4. 非法正则静默跳过（不抛异常），超时保护 3000ms 不可移除
5. 手动高亮压过规则高亮（ranges = ruleRanges + manualRanges，顺序不能反）
6. 标题行不画高亮（col.highlightStyle = if (line.isTitle) null else colors[li][ci]）
7. 快速路径兼容（styledColumnCount > 0 时禁用 fastDrawTextLine）
8. 自定义字体缓存命中与未命中两种情况都缓存
9. 每个 Phase 编译验证，确保不破坏现有功能
10. **完全不修改书源/订阅源/网络层相关代码**（零影响核心功能）

**F-P1-3 调试日志面板 + 浮球**（借鉴蛋蛋Max，13 文件）：
- 新增 `ui/debug/DebugFloatBall.kt`（Overlay 窗口）
- 新增 `ui/debug/DebugLogPanel.kt`（日志分类显示）
- 流程日志（请求/响应链路）

**F-P1-4 阅读热力图**（借鉴蛋蛋Max）：
- 按日期统计阅读时长
- 热力图可视化（GitHub 风格）

**F-P1-5 书籍想法/笔记系统**（借鉴 Jingshiro，8 文件）：
- 新增 `data/entities/BookThought.kt`
- 新增 `ui/thought/Thought*.kt`
- Markdown 生成 + Obsidian 集成导出

**F-P1-6 Cronet 网络引擎升级**（用户主动提供报告，独立任务，2 文件变更）：
- **架构现状**：项目采用"本地 jar API + 运行时动态下载 so"混合架构
  - Java API 层：`app/cronetlib/` 下 5 个 jar（由 `download.gradle` 下载）
  - Native so 层：**不打包进 APK**，运行时从 `storage.googleapis.com` 下载到 `appDir/cronet/`
  - 版本控制：`gradle.properties` 的 `CronetVersion`/`CronetMainVersion` + `assets/cronet.json`（各架构 so MD5）
- **升级方案**：复用项目内置自动化升级链，不引入新代码
  1. 修改 `gradle.properties`：`CronetVersion=149.0.7827.201` + `CronetMainVersion=149.0.0.0`
  2. 执行 `gradlew app:downloadCronet`（自动下载 5 个 jar + 4 架构 so + 重新生成 cronet.json）
  3. 检查 `CronetHelper.kt`/`CronetInterceptor.kt`/`CronetCoroutineInterceptor.kt` 使用的 API 是否有废弃（`ExperimentalCronetEngine`/`UrlRequest.Builder`/`UploadDataProvider` 等均为长期稳定 API，预期无废弃）
  4. 编译验证 + 真机回归测试（书源搜索/章节抓取/图片加载）
  5. 更新 `updateLog.md` 的 `## cronet版本:` 行
- **文件变更**：
  - `gradle.properties`：2 行版本号修改
  - `app/src/main/assets/cronet.json`：由 `downloadCronet` 任务自动重新生成
  - `app/cronetlib/*.jar`：由 `downloadCronet` 任务自动替换
  - `app/src/main/assets/updateLog.md`：cronet 版本号行同步
- **风险缓解**：
  - API 废弃风险低（`org.chromium.net.*` 稳定 API 向后兼容）
  - proguard 规则由 `cronet.sh` 自动同步
  - 真机回归测试覆盖书源/RSS 源/图片加载全流程
- **实施时机**：P1 主线优化（Task 19~27）完成后单独执行，Task 27 集成验证不含 Cronet 升级

**F-P1-7 打包压缩优化**（用户痛点，独立任务，1 文件变更）：
- **当前配置现状**（已启用项，无需改动）：
  - `release` buildType：`minifyEnabled true` + `shrinkResources true`（R8 代码压缩 + 资源压缩）
  - `abiFilters 'arm64-v8a', 'armeabi-v7a'`（仅打包主流架构，已减小 ~5MB）
  - `packaging.resources.excludes.add('META-INF/*')`（排除 META-INF 冗余）
  - Cronet so 运行时下载不打包进 APK
- **升级方案**：仅新增 `resConfigs` 一项配置
  1. `app/build.gradle` 的 `defaultConfig` 内新增 `resConfigs 'zh', 'zh-rHK', 'zh-rTW', 'en', 'es', 'es-rES', 'ja', 'ja-rJP', 'pt', 'pt-rBR', 'vi'`
  2. 编译 release APK 对比体积变化（预期减小 ~50-100KB）
  3. 真机回归测试：中/英/西/日/葡/越语言切换 + 资源引用无异常
- **文件变更**：
  - `app/build.gradle`：`defaultConfig` 内新增 1 行 `resConfigs` 配置（位于 `ndk.abiFilters` 之后）
- **风险缓解**：
  - 保留项目所有已翻译语言（项目 `values/`/`values-zh/`/`values-zh-rHK/`/`values-zh-rTW/`/`values-es-rES/`/`values-ja-rJP/`/`values-pt-rBR/`/`values-vi` 共 8 类），不移除任何项目翻译
  - 仅移除第三方库（Material Components/AppCompat 等）自带的其他语言资源（法/德/俄等）
  - 不影响 RTL 布局（布局资源与语言资源解耦）
- **不实施项及理由**：
  - R8 full mode：`android.enableR8.fullMode=true` 会破坏 Rhino JS 引擎 `RhinoWrapFactory`/`NativeBaseSource` 反射 + Gson `@Keep` 反序列化 + Hutool 加解密反射，风险高于收益
  - APP Bundle：项目主要面向国内用户，国内应用市场普遍不支持 AAB 分发
  - `splits.abi` 多 APK 分发：国内分发渠道普遍只接受单 APK
- **实施时机**：P1 主线优化（Task 19~27）完成后单独执行，可与 F-P1-6 并行

**F-P1-8 书源/订阅源分组文件夹布局**（用户需求，独立任务，8 文件变更）：
- **架构现状**：
  - 书源分组：`BookSource.bookSourceGroup: String?`（逗号分隔字符串，非独立分组表）
  - 订阅源分组：`RssSource.sourceGroup: String?`（同上）
  - 当前 UI：`BookSourceActivity`/`RssSourceActivity` 列表展示 + 菜单筛选 `group:<name>`
- **选定方案A（轻量改造）核心设计**：
  - **数据层**：复用现有 `bookSourceGroup`/`sourceGroup` 字符串字段，不新增分组表
  - **DAO 层**：新增 `flowGroups()` 方法，使用 `SELECT DISTINCT` 聚合查询分组列表
  - **UI 层**：新增"视图切换"按钮（列表视图/文件夹视图）+ 文件夹视图 Adapter + 文件夹卡片布局
  - **配置层**：`AppConfig` 新增 `sourceViewMode`/`rssViewMode` 字段持久化视图状态
- **文件变更**：
  - 新增 `app/src/main/java/io/legado/app/ui/book/source/SourceFolderAdapter.kt`：文件夹视图 Adapter
  - 新增 `app/src/main/java/io/legado/app/ui/rss/source/RssFolderAdapter.kt`：RSS 文件夹视图 Adapter
  - 新增 `app/src/main/res/layout/item_source_folder.xml`：书源文件夹卡片布局
  - 新增 `app/src/main/res/layout/item_rss_folder.xml`：RSS 文件夹卡片布局
  - 修改 `app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt`：新增 `flowGroups()` 方法
  - 修改 `app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt`：新增 `flowGroups()` 方法
  - 修改 `app/src/main/java/io/legado/app/ui/book/source/BookSourceActivity.kt`：新增视图切换按钮 + 文件夹视图 RecyclerView + 视图切换逻辑
  - 修改 `app/src/main/java/io/legado/app/ui/rss/source/RssSourceActivity.kt`：同上
  - 修改 `app/src/main/java/io/legado/app/ui/book/source/BookSourceViewModel.kt`：新增 `flowFolderGroups()` 方法
  - 修改 `app/src/main/java/io/legado/app/ui/rss/source/RssSourceViewModel.kt`：同上
  - 修改 `app/src/main/java/io/legado/app/help/config/AppConfig.kt`：新增 `sourceViewMode`/`rssViewMode` 配置项
  - 修改 `app/src/main/res/values/strings.xml`：新增"文件夹视图"/"列表视图"/"未分组"等字符串
- **风险缓解**：
  - 不改变数据模型，无数据库迁移风险
  - 视图切换不丢失选中状态和搜索关键字（共享 ViewModel 状态）
  - 文件夹视图与列表视图共用排序菜单（复用 `BookSourceSort`）
  - 未分组源单独显示"未分组"文件夹，避免视觉遗漏
- **实施时机**：P1 主线优化（Task 19~27）完成后单独执行，可与 F-P1-6/F-P1-7 并行

### 1.4 P2 阶段技术方案（评估后决定是否实施）

完成 P0/P1 后单独评估每个 P2 项，按收益/风险比排序实施。

**P2 优化点评估倾向**：
- P2-1 retry 重试 IOException：**倾向不实施**（生态设计选择）
- P2-2 Cronet 熔断器：评估（自实现需充分测试）
- P2-3 启用 Cronet 协程拦截器：评估（协程版有 runBlocking 需先修复）
- P2-4 限流器 Mutex 化：评估（锁结构变更风险高）
- P2-5 CacheBook 锁优化：评估（@Synchronized 是稳定选择）

**P2 功能借鉴**：
- F-P2-1 AI 聊天框架：22+15+8 文件，三大 AI Provider 统一接口
- F-P2-2 MCP 服务：7 文件，Legado 作为 MCP Server
- F-P2-3 主题包管理器

### 1.5 P3 阶段技术方案（暂缓实施）

> **5 项高风险优化可能导致部分书源不可用，强烈建议暂缓实施。**

| 编号 | 暂缓理由 |
|------|---------|
| A5 | 修复后传入自定义 TrustManager 不信任自签名证书，会导致 SSL 握手失败 → 书源不可用 |
| C1 | 阅读T 独有的协议级实现，改动面大，风险高 |
| C6 | 阅读T 独有，影响所有请求，需充分测试 |
| C7 | 默认不启用 unsafe SSL 后部分自签证书网站将无法访问 |
| C8 | 阅读NG 独有，影响所有请求，需充分测试 |

---

## 二、Architecture Decisions（架构决策 - ADR Y-Statement）

### AD-01: 重试策略选择 - 保持现状（不重试 IOException）

- **Context**: 当前 `OkHttpUtils.newCallResponse` 不重试 IOException，网络瞬时故障不可恢复。原方案提议捕获 IOException + 指数退避 + 最多 3 次重试。
- **Concern**: 如何在不偏离生态、不增加服务端压力的前提下处理瞬时故障？
- **Decision**: **保持现状**（不重试 IOException）。原方案的激进重试已被否决。
- **Goal**: 不偏离主流版本生态，不增加服务端压力，不引入回归
- **Tradeoff**: 接受网络瞬时故障不可恢复；用户可配置 retry；主流版本（喵公子/Sigma/阅读T/阅读NG）都有意不重试，是生态设计选择
- **Alternatives Considered**: A1. 激进重试（已否决 - 偏离生态）；A2. 引入 Resilience4j（已否决 - 引入新依赖）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-02: 锁结构选择 - 保持 @Synchronized 不变

- **Context**: `ConcurrentRateLimiter` 和 `CacheBook` 大量使用 `synchronized` / `@Synchronized`，在协程中阻塞线程。原方案提议用 Mutex 替代。
- **Concern**: 如何在保证稳定性的前提下处理锁结构？
- **Decision**: **保持 @Synchronized 不变**。原方案的 Mutex 化已被否决。
- **Goal**: 不引入并发 Bug，保持与主流版本一致
- **Tradeoff**: 接受协程线程被阻塞；主流版本都用 @Synchronized，稳定
- **Alternatives Considered**: A1. Mutex 替代 synchronized（已否决 - 非重入语义差异，风险高）；A2. AtomicReference + CAS（已否决 - 锁结构变更风险高）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-03: Cronet 拦截器版本选择 - 保持同步版不变

- **Context**: 当前启用 `CronetInterceptor`（同步版，`waitForDone` 阻塞线程），`CronetCoroutineInterceptor`（协程版）是死代码。原方案提议启用协程版。
- **Concern**: 如何在不引入回归的前提下处理 Cronet 拦截器？
- **Decision**: **保持同步版不变**。原方案的协程版切换已被否决。
- **Goal**: 不引入回归，Cronet 功能正常
- **Tradeoff**: 接受线程阻塞；协程版有 runBlocking 问题（L56, L78），需先修复再评估
- **Alternatives Considered**: A1. 启用协程版（已否决 - 有 runBlocking 问题，功能等价性需验证）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-04: 307/308 重定向处理 - 借鉴蛋蛋Max 实现

- **Context**: OkHttp 默认重定向可能将 POST 改为 GET，丢失 body。蛋蛋Max 已实现 307/308 重定向保持 method+body。
- **Concern**: 如何在不引入回归的前提下处理 307/308 重定向？
- **Decision**: 借鉴蛋蛋Max 的实现，在 `OkHttpUtils.newCallResponse` 中增加 307/308 状态码处理。
- **Goal**: 307/308 重定向保持 POST body，符合 RFC 7538 标准
- **Tradeoff**: 可能改变现有行为（部分书源可能依赖 OkHttp 默认重定向）；蛋蛋Max 已验证，风险低
- **Alternatives Considered**: A1. 不处理（已否决 - POST 重定向丢 body 是 Bug）；A2. 启用 OkHttp followRedirects(false) 手动处理所有重定向（已否决 - 改动过大）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-05: LRU 实现选择 - 复用标准库 LruCache

- **Context**: `proxyClientCache` / `customIp` / `failUrl` / `stringRuleCache` 均无上限，长跑后内存泄漏。
- **Concern**: 如何用最小代码量实现 LRU 上限？
- **Decision**: 优先使用 `android.util.LruCache`（已内置 LRU + 线程安全）；`proxyClientCache` 用 `LinkedHashMap` + `removeEldestEntry`（需同步包装）。
- **Goal**: 5 处内存泄漏全部修复，代码量增加 ≤ 50 行
- **Tradeoff**: LruCache 的 `sizeOf` 默认按条目数计算，如需按字节计算需重写（本次不需要）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-06: 连接池规模选择 - 50 连接 / 5 分钟

- **Context**: 默认 ConnectionPool 5 个空闲连接，书源场景下每源域名不同，连接复用率极低。
- **Concern**: 如何平衡内存占用与连接复用率？
- **Decision**: 配置 `ConnectionPool(50, 5, TimeUnit.MINUTES)`
- **Goal**: 连接复用率提升 200%+，内存占用增加 ≤ 200KB
- **Tradeoff**: 50 个空闲连接约 200KB 内存占用；部分书源可能仅访问一次，连接闲置 5 分钟后被回收
- **Status**: Accepted
- **Superseded-by**: 无

### AD-07: WebView 池化修复 - 借鉴阅读Archive closed 标志

- **Context**: WebViewPool 复用 WebView 后，旧 EvalJsRunnable 的回调可能误把新实例的结果当作自己的，导致数据串错。
- **Concern**: 如何在不改变 WebView 池化架构的前提下避免回调串错？
- **Decision**: 借鉴阅读Archive 的 closed 标志 + isActiveWebView 引用相等检查。
- **Goal**: 回调只处理当前活跃 WebView 的结果，避免数据串错
- **Tradeoff**: 引入 closed 标志后必须确保 destroy() 在所有场景下被调用一次；重入安全已保证
- **Alternatives Considered**: A1. 不修复（已否决 - 数据串错是 Bug）；A2. 重构 WebView 池为每请求独立实例（已否决 - 性能损失大）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-08: runBlocking 修复策略 - 预查询+内存缓存（B1）/ 优化内部逻辑（B2）

- **Context**: `BackstageWebView.load()` 和 `BottomWebViewDialog.shouldInterceptRequest` 都有 runBlocking 阻塞问题。
- **Concern**: 如何在不破坏现有 API 的前提下减少 runBlocking 阻塞？
- **Decision**: B1 采用预查询 + 内存缓存方案（改动小）；B2 仅优化 runBlocking 内部逻辑（shouldInterceptRequest 必须 synchronous）。
- **Goal**: B1 减少主线程阻塞；B2 减少线程切换
- **Tradeoff**: B1 首次访问仍需 runBlocking，仅缓解不彻底解决；B2 无法彻底修复（WebView API 固有限制）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-09: CookieStore LRU 淘汰策略 - 优先删除 tracking Cookie

- **Context**: `CookieStore.getCookie` 在 Cookie 超 4096 字节时随机删除 key，可能命中关键登录 Cookie。
- **Concern**: 如何在大 Cookie 场景下保护关键登录 Cookie？
- **Decision**: 优先删除 tracking Cookie（_ga/_gid/_gat/Hm_lvt_*/_hjid），其次按 key 长度降序删除。
- **Goal**: 大 Cookie 站点登录态保持
- **Tradeoff**: 不新增 lastAccessTime 字段，避免数据库迁移；tracking Cookie 列表需维护
- **Alternatives Considered**: A1. 完整 LRU（需新增 lastAccessTime 字段，数据库迁移风险高）；A2. FIFO（可能删除关键 Cookie）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-10: 功能借鉴分阶段实施策略

- **Context**: 25 个缺失功能，用户价值与借鉴难度差异大。
- **Concern**: 如何在不阻塞网络层优化的前提下推进功能借鉴？
- **Decision**: 分阶段实施：P0 短平快（3 项）→ P1 中等难度（5 项）→ P2 长期（3 项）→ P3 长期（2 项）。
- **Goal**: 短平快先做让用户可感知，长期功能后做避免改动面过大
- **Tradeoff**: P2/P3 功能借鉴需 3-6 个月；分阶段实施周期长
- **Alternatives Considered**: A1. 一次性实施所有功能借鉴（已否决 - 改动面过大，回归风险高）；A2. 不做功能借鉴（已否决 - 用户明确要求）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-11: P3 高风险优化暂缓实施

- **Context**: A5/C1/C6/C7/C8 五项高风险优化可能导致部分书源不可用。
- **Concern**: 如何在不影响书源可用性的前提下处理高风险优化？
- **Decision**: **暂缓实施**，5 项高风险优化全部列入 P3。
- **Goal**: 不影响书源可用性，稳定性优先
- **Tradeoff**: 部分性能/安全问题未解决；用户明确要求稳定性优先
- **Alternatives Considered**: A1. 实施 A5（已否决 - 自签名证书书源不可用）；A2. 实施 C7（已否决 - 默认不启用 unsafe SSL 后部分书源不可用）
- **Status**: Accepted
- **Superseded-by**: 无

---

## 三、Data Flow（数据流）

### 3.1 优化后网络请求流程

```
用户操作
  │
  ▼
WebBook.searchBookAwait() / getContentAwait() / ...
  │
  ▼
AnalyzeUrl.getStrResponseAwait()
  │
  ├─ B1: BackstageWebView.load() 预查询 SourceHelp.getCachedBookSource()
  │
  ▼
OkHttpUtils.newCallResponse(retry)
  │
  ├─ 不重试 IOException（保持现状，AD-01）
  ├─ C2: 307/308 重定向保持 method+body（借鉴蛋蛋Max）
  │
  ▼
okHttpClient.newCall(request).enqueue()
  │
  ▼
拦截器链（按顺序）
  │
  ├─ 1. OkHttpExceptionInterceptor
  │     └─ A4: CancellationException 透传守卫
  │
  ├─ 2. UA + Keep-Alive 注入
  │
  ├─ 3. CookieManager（NetworkInterceptor）
  │     └─ A3: 大 Cookie 场景优先删 tracking Cookie
  │
  ├─ 4. CronetInterceptor（同步版，保持现状，AD-03）
  │     │
  │     ├─ Cronet 加载成功 ──→ 走 Cronet
  │     │
  │     └─ Cronet 加载失败 ──→ 走 OkHttp（默认行为）
  │
  ├─ 5. DecompressInterceptor
  │
  ▼
服务器响应
  │
  ├─ 307/308 ──→ 保持 method+body，跟随 Location（C2）
  │
  ▼
Response 处理
  │
  ▼
Coroutine.executeInternal()
  │
  ├─ 成功 ──→ onSuccess 回调
  │
  └─ 异常 ──→ catch (e: CancellationException) throw e（A1 守卫）
              │
              ├─ errorReturn 已消费 ──→ onSuccess(errorReturn.value)
              │
              └─ 否则 ──→ onError 回调
```

### 3.2 优化后 WebView 请求流程（B6 + A7）

```
书源请求（useWebView=true）
  │
  ▼
BackstageWebView.load()
  │
  ├─ B1: 预查询 SourceHelp.getCachedBookSource(key)
  │     ├─ 缓存命中 ──→ 直接使用
  │     └─ 缓存未命中 ──→ runBlocking(IO) 查询数据库 + 写入缓存
  │
  ▼
WebViewPool.acquire()
  │
  ▼
WebView.evaluateJavascript(jsStr) {
  │
  ├─ B6/A7: isActiveWebView(webView) 引用相等检查
  │     ├─ 是当前活跃 WebView ──→ handleResult(it)
  │     └─ 非当前活跃 WebView ──→ 丢弃结果（避免数据串错）
  │
  ▼
destroy()
  │
  ├─ closed = true
  ├─ callback = null
  ├─ mHandler.removeCallbacksAndMessages(null)
  └─ WebViewPool.release(webView)
```

### 3.3 优化后图片加载流程（C4）

```
Glide.load(url)
  │
  ▼
OkHttpStreamFetcher.loadData()
  │
  ├─ failUrl.get(url)? ──→ 直接返回（C4 LruCache 上限 200）
  │
  ▼
okHttpClient.newCall(request).enqueue()
  │
  ▼
onResponse(response)
  │
  ▼
Glide 解码 Bitmap → 显示
  │
  ├─ 失败 ──→ failUrl.put(url, true)（C4 LruCache 上限 200）
  │
  └─ 成功 ──→ 显示图片
```

### 3.4 优化后多书并发下载流程（B4 + B5）

```
用户触发多书缓存
  │
  ▼
CacheBook.getOrCreate(book, bookSource)  ──── 保持 @Synchronized（AD-02）
  │
  ├─ cacheBookMap 已有 ──→ 返回现有 CacheBookModel
  │
  └─ 首次创建 ──→ @Synchronized 保护创建
                  │
                  ▼
              CacheBookModel(book, bookSource)
                │
                ▼
              startProcessJob(cachePool)
                │
                ▼
              download(chapter)  ──── 状态变更保持 @Synchronized（AD-02）
                │
                ├─ WebBook.getContentAwait()
                │
                ├─ 成功 ──→ onSuccess 回调
                │           └─ successDownloadSet.add()（@Synchronized 保护）
                │
                └─ 失败 ──→ onError 回调
                            errorDownloadMap.put()（@Synchronized 保护）

服务停止时
  │
  ▼
CacheBook.close()  ──── B4: @Synchronized 保护
  │
  ├─ cacheBookMap.forEach { it.value.stop() }
  ├─ cacheBookMap.clear()
  ├─ successDownloadSet.clear()
  └─ errorDownloadMap.clear()

图片下载（B5 修复）
  │
  ▼
BookHelp.saveImage(src)
  │
  ├─ synchronized(this) { downloadImages.getOrPut(src) { Mutex() } }
  ├─ mutex.lock()
  ├─ ... 下载图片
  └─ finally:
      ├─ mutex.unlock()           # 先 unlock（B5 修复）
      └─ downloadImages.remove(src)  # 后 remove（B5 修复）
```

---

## 四、File Changes（文件变更清单）

### 4.1 P0 阶段文件变更（9 项优化 + 3 项功能借鉴）

| 文件 | 变更类型 | 变更内容 | 行数估计 |
|------|----------|----------|----------|
| `app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt` | 修改 | L182-190 加 CancellationException 守卫（A1） | +2 |
| `app/src/main/java/io/legado/app/model/webBook/WebBook.kt` | 修改 | 5 处 catch 加 CancellationException 守卫（A1） | +5 |
| `app/src/main/java/io/legado/app/help/FlowExtensions.kt` | 修改 | mapParallelSafe 加 CancellationException 守卫（A1） | +2 |
| `app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt` | 修改 | catch 加 CancellationException 守卫（A4） | +2 |
| `app/src/main/java/io/legado/app/help/source/BookSourceExtensions.kt` | 修改 | mutexMap 改 ConcurrentHashMap + computeIfAbsent（A2） | +2 |
| `app/src/main/java/io/legado/app/ui/main/MainViewModel.kt` | 修改 | waitUpTocBooks 改 ConcurrentLinkedQueue（B3） | ±0 |
| `app/src/main/java/io/legado/app/model/CacheBook.kt` | 修改 | close() 加 @Synchronized（B4） | +1 |
| `app/src/main/java/io/legado/app/help/book/BookHelp.kt` | 修改 | saveImage finally 顺序调整（B5） | ±0 |
| `app/src/main/java/io/legado/app/help/webView/WebViewPool.kt` | 修改 | closed 标志 + isActiveWebView（B6） | +15 |
| `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` | 修改 | closed 标志 + isActiveWebView + EvalJsRunnable 修复（B6/A7） | +20 |
| `app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt` | 修改 | newCallResponse 增加 307/308 重定向处理（C2，借鉴蛋蛋Max） | +30 |
| `app/src/main/java/io/legado/app/help/http/SSLHelper.kt` | 修改 | "SSL" → "TLS"（P0-6） | ±0 |
| `app/src/main/java/io/legado/app/ui/debug/**` | 新增 | 调试工具集 14 个文件（F-P0-1，借鉴蛋蛋Max） | +800 |
| `app/src/main/java/io/legado/app/api/controller/BackupController.kt` | 新增 | 备份选择器后端（F-P0-2） | +100 |
| `modules/web/src/views/BackupManager.vue` | 新增 | Web 端备份管理（F-P0-3，借鉴蛋蛋Max） | +400 |
| `modules/web/src/router/backupRouter.ts` | 新增 | 备份路由（F-P0-3） | +15 |
| `modules/web/src/pages/backup/{index.html,main.js}` | 新增 | MPA 独立入口（F-P0-3） | +30 |
| `modules/web/src/router/index.ts` | 修改 | 集成 backupRoutes（F-P0-3） | +5 |
| `modules/web/src/views/BookShelf.vue` | 修改 | 增加"数据备份"入口按钮（F-P0-3） | +10 |
| `modules/web/src/api/api.ts` | 修改 | 新增 BackupItemInfo/BackupOverview 类型 + API（F-P0-3） | +30 |
| `app/src/main/res/menu/rss_articles.xml` | 修改 | 新增 menu_page 项（F-P0-4，借鉴蛋蛋Max） | +4 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt` | 修改 | 新增 pageLiveData/initialSortUrl/skipPage/loadArticles 重载（F-P0-4） | +20 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt` | 修改 | 新增 getCurrentPage/showPageMenu/showPagePicker/loadArticles 重载（F-P0-4） | +20 |
| `app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt` | 修改 | 新增 menuPage/updatePageMenu/currentArticlesFragment + 菜单回调（F-P0-4） | +15 |

### 4.2 P1 阶段文件变更（8 项优化 + 5 项功能借鉴）

| 文件 | 变更类型 | 变更内容 | 行数估计 |
|------|----------|----------|----------|
| `app/src/main/java/io/legado/app/help/http/CookieStore.kt` | 修改 | 随机删除改 LRU 淘汰（A3） | +15 |
| `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` | 修改 | proxyClientCache LRU（A6）+ ConnectionPool(50)（C3） | +25 |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` | 修改 | customIp 改 LruCache(100)（C5） | +3 |
| `app/src/main/java/io/legado/app/help/source/SourceHelp.kt` | 修改 | 新增 getCachedBookSource 内存缓存（B1） | +20 |
| `app/src/main/java/io/legado/app/ui/widget/dialog/BottomWebViewDialog.kt` | 修改 | runBlocking 内部逻辑优化（B2） | +10 |
| `app/src/main/java/io/legado/app/help/glide/OkHttpStreamFetcher.kt` | 修改 | failUrl 改 LruCache(200)（C4） | +3 |
| `app/src/main/java/io/legado/app/help/ConcurrentRateLimiter.kt` | 修改 | 新增 clearRecord 方法（C4） | +5 |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` | 修改 | stringRuleCache 改 LruCache(64)（C4） | +3 |
| `app/src/main/java/io/legado/app/data/entities/AutoTask.kt` | 新增 | 自动任务实体（F-P1-1，借鉴阅读T） | +50 |
| `app/src/main/java/io/legado/app/service/AutoTaskService.kt` | 新增 | AlarmManager 调度（F-P1-1） | +200 |
| `app/src/main/java/io/legado/app/ui/autoTask/**` | 新增 | 自动任务 UI 9 文件（F-P1-1） | +600 |
| `app/src/main/java/io/legado/app/data/entities/HighlightRule.kt` | 新增 | 高亮规则实体（F-P1-2，借鉴蛋蛋Max） | +60 |
| `app/src/main/java/io/legado/app/ui/book/read/HighlightRule*.kt` | 新增 | 高亮规则 UI 9 文件（F-P1-2） | +800 |
| `app/src/main/java/io/legado/app/ui/debug/DebugFloatBall*.kt` | 新增 | 调试浮球 + 日志面板 13 文件（F-P1-3，借鉴蛋蛋Max） | +700 |
| `app/src/main/java/io/legado/app/ui/book/read/ReadingHeatmap*.kt` | 新增 | 阅读热力图（F-P1-4） | +300 |
| `app/src/main/java/io/legado/app/data/entities/BookThought.kt` | 新增 | 书籍笔记实体（F-P1-5，借鉴 Jingshiro） | +50 |
| `app/src/main/java/io/legado/app/ui/thought/**` | 新增 | 书籍笔记 UI 7 文件（F-P1-5） | +500 |

### 4.3 测试文件变更

| 文件 | 变更类型 | 变更内容 |
|------|----------|----------|
| `app/src/test/java/io/legado/app/help/coroutine/CoroutineTest.kt` | 新增 | CancellationException 守卫测试（A1） |
| `app/src/test/java/io/legado/app/help/http/OkHttpUtilsTest.kt` | 新增 | 307/308 重定向测试（C2） |
| `app/src/test/java/io/legado/app/help/webView/WebViewPoolTest.kt` | 新增 | WebView 池化修复测试（B6） |
| `app/src/test/java/io/legado/app/help/http/CookieStoreTest.kt` | 新增 | LRU 淘汰测试（A3） |

### 4.4 文档变更

| 文件 | 变更内容 |
|------|----------|
| `docs/project-flow/architecture/network-layer.md` | 同步网络层架构变更（连接池配置、307/308 重定向） |
| `docs/project-flow/modules/service-layer.md` | 同步缓存定期清理变更 |
| `docs/project-flow/quick-reference.md` | 新增配置参数 |
| `docs/INDEX.md` | 更新 spec 状态 |
| `app/src/main/assets/updateLog.md` | 追加用户可感知的变更说明 |
| `AGENTS.md` | 同步延伸版本对比方法论子规范引用（已完成） |

---

## 五、风险与缓解

### 5.1 低风险项（P0）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| A1 CancellationException 守卫改变异常处理顺序 | 极低 | 低 | 仅在 catch 首行加判断，不改变其他逻辑 |
| A2 mutexMap 改 ConcurrentHashMap | 极低 | 低 | API 兼容，行为一致 |
| A4 OkHttpExceptionInterceptor 守卫 | 极低 | 低 | 仅影响取消异常传播 |
| B3 waitUpTocBooks 改 ConcurrentLinkedQueue | 极低 | 低 | API 兼容 |
| B4 close() 加 @Synchronized | 极低 | 低 | 与其他方法锁一致 |
| B5 saveImage finally 顺序调整 | 极低 | 低 | 修复互斥失效 |
| B6 WebViewPool closed 标志 | 低 | 中 | 借鉴阅读Archive 已验证；需充分测试 destroy() 调用时机 |
| C2 307/308 重定向处理 | 低 | 中 | 借鉴蛋蛋Max 已验证；RFC 7538 标准 |
| P0-6 SSLContext "SSL" → "TLS" | 极低 | 低 | TLS 是 SSL 的安全替代，行为兼容 |

### 5.2 中风险项（P1）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| A3 CookieStore LRU 淘汰可能删关键 Cookie | 中 | 中 | 优先删 tracking Cookie，充分测试 |
| A6 proxyClientCache LRU 上限 | 低 | 低 | 上限 20-30，避免影响正常用户 |
| A7 BackstageWebView 复用回调修复 | 低 | 中 | 与 B6 协同，借鉴阅读Archive |
| C3 连接池扩大到 50 增加内存 | 极低 | 低 | 200KB 内存占用可接受 |
| C5 customIp LruCache(100) | 极低 | 低 | 与 P0-7 协同，LruCache 自身线程安全 |
| B1 BackstageWebView runBlocking 预查询 | 低 | 中 | 首次访问仍需 runBlocking，仅缓解 |
| B2 BottomWebViewDialog runBlocking 优化 | 低 | 低 | 仅优化内部逻辑，不改变 runBlocking 本身 |
| C4 内存泄漏治理 | 极低 | 低 | 上限设置合理 |

### 5.3 回滚策略

- 每个修复点独立提交，便于单独回滚
- P0 / P1 阶段分别合并，P1 出问题可回滚至 P0 完成状态
- 保留原实现作为注释参考（仅关键变更点）

### 5.4 高风险项（P3 - 暂缓实施）

> 5 项高风险优化可能导致部分书源不可用，**强烈建议暂缓实施**。

| 风险项 | 暂缓理由 |
|--------|---------|
| A5 ObsoleteUrlFactory 自定义证书失效修复 | 修复后自签名证书书源不可用 |
| C1 SOCKS5 隧道完整实现 | 改动面大，风险高 |
| C6 HttpLogInterceptor | 影响所有请求，需充分测试 |
| C7 SSL 配置可选化 | 默认不启用 unsafe SSL 后部分书源不可用 |
| C8 NetworkLogInterceptor | 影响所有请求，需充分测试 |

---

## 六、调整记录

### 6.1 2026-07-06 第四版调整（基于 8 份深度分析文档整合）

**对比对象**：7 个可达延伸版本（蛋蛋Max/阅读NG/阅读T/阅读Archive/阅读R/Jingshiro/喵公子）

**对比结论**：
- 蛋蛋Max：307/308 重定向 + 调试工具集 + 备份管理 + 高亮规则 + 调试日志面板
- 阅读Archive：WebView 池化修复范式 + Epub 渲染引擎 + AI 框架
- 阅读NG：AI 聊天框架 + MCP 服务
- 阅读T：自动任务系统 + 高亮规则 + SOCKS5 隧道 + Brotli 解压
- Jingshiro：书籍想法/笔记系统
- 喵公子/阅读R：网络层与本项目完全一致

**新增项**：
- ✅ 整合 optimization-impact-analysis.md 结论（22 优化点按 9低/8中/5高风险分级）
- ✅ 整合 forks-missing-features.md 结论（25 缺失功能按 P0/P1/P2/P3 分阶段）
- ✅ AD-07 WebView 池化修复（借鉴阅读Archive closed 标志）
- ✅ AD-09 CookieStore LRU 淘汰策略（优先删 tracking Cookie）
- ✅ AD-10 功能借鉴分阶段实施策略
- ✅ AD-11 P3 高风险优化暂缓实施
- ✅ B1/B2 runBlocking 修复方案（预查询+内存缓存 / 优化内部逻辑）
- ✅ B3/B4/B5 新增 3 项低风险 Bug 修复
- ✅ P0 功能借鉴（3 项短平快）
- ✅ P1 功能借鉴（5 项中等难度）

**保留项**：
- ✅ AD-01 ~ AD-06（原 ADR 决策）
- ✅ AD-08 runBlocking 修复策略
- ✅ P0 全部 9 个低风险优化点
- ✅ P1 全部 8 个中风险优化点

**移除项**：
- ❌ 原方案的激进优化（retry 重试、CacheBook 锁优化、Cronet 熔断器、限流器 Mutex 化）
- ❌ 原方案的协程拦截器切换
