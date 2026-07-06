# Legado 多线程组件深度分析

> 分析对象：`f:\myself\github\WeAgentChat\temp\legado`（fork 自 Luoyacheng/legado-E）
> 分析时间：2026-07-06
> 分析范围：协程封装、线程池、锁结构、并发集合、Dispatcher、runBlocking、CancellationException 处理
> 对比版本：蛋蛋Max (DandanLLab/Legado_Max)、阅读NG (joestar817/legado_NG)、阅读Archive (Rimchars/legado)；喵公子/阅读T/辞晨Max 因仓库不存在或网络失败跳过

---

## 一、多线程组件全貌

### 1.1 协程封装架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  Coroutine<T> (链式协程核心)                                  │
│  位置: help/coroutine/Coroutine.kt                            │
│  模式: async{}.onStart{}.onSuccess{}.onError{}.onFinally{}    │
│        .onCancel{}.timeout().onErrorReturn()                  │
│  双版本: xxx() 返回 Coroutine<T> + xxxAwait() 挂起函数         │
│  默认: scope=MainScope(), context=IO, executeContext=Main      │
└─────────────────────────────────────────────────────────────┘
       │
       ├─→ CompositeCoroutine (组合协程容器)
       │   位置: help/coroutine/CompositeCoroutine.kt
       │   实现: HashSet<Coroutine<*>> + synchronized(this)
       │   行为: remove() 自动 cancel; clear() 批量 cancel
       │
       ├─→ CoroutineContainer (接口)
       │   位置: help/coroutine/CoroutineContainer.kt
       │   方法: add/addAll/remove/delete/clear
       │
       ├─→ ActivelyCancelException (主动取消异常)
       │   位置: help/coroutine/ActivelyCancelException.kt
       │   特性: 继承 CancellationException, 覆写 fillInStackTrace()=空
       │   用途: 区分"主动 cancel"与"协程被取消"
       │
       └─→ FlowExtensions.kt (Flow 并行扩展)
           位置: utils/FlowExtensions.kt
           核心: onEachParallel / onEachParallelSafe / mapParallel
                 mapAsync / onEachAsync (基于 Semaphore+channelFlow)
```

### 1.2 线程池清单（全项目）

| # | 名称 | 类型 | 大小 | 位置 | 用途 |
|---|------|------|------|------|------|
| 1 | `globalExecutor` | `newSingleThreadExecutor` | 1 | `help/ExecutorService.kt:6` | 全局串行执行（ReadBook.saveRead、LogUtils、AudioPlay 等） |
| 2 | `upTocPool` | `newFixedThreadPool` | `min(threadCount, 9)` | `ui/main/MainViewModel.kt:54` | 目录更新 + 章节缓存（命名误导） |
| 3 | `cachePool` | `newFixedThreadPool` | `min(threadCount, 9)` | `service/CacheBookService.kt:46` | 离线缓存下载 |
| 4 | `searchCoroutine` | `newFixedThreadPool` | `min(threadCount, 9)` | `service/CheckSourceService.kt:61` | 书源校验 |
| 5 | SearchModel 池 | `newFixedThreadPool` | `min(threadCount, 9)` | `model/webBook/SearchModel.kt:49` | 书源搜索 |
| 6 | `searchPool` | `newFixedThreadPool` | `min(threadCount, 9)` | `ui/book/changesource/ChangeBookSourceViewModel.kt:168` | 换源搜索 |
| 7 | `searchPool` | `newFixedThreadPool` | `min(threadCount, 9)` | `ui/book/changecover/ChangeCoverViewModel.kt:102` | 换封面搜索 |
| 8 | ExportBookService 池 | `newFixedThreadPool` | `min(threadCount, 9)` | `service/ExportBookService.kt:288,529` | 书籍导出 |
| 9 | `DispatchersMonitor.dispatcher` | `newSingleThreadExecutor` | 1 | `help/DispatchersMonitor.kt:26` | 调度器超时监控 |
| 10 | `WebViewPool.cleanupScope` | `CoroutineScope(IO + SupervisorJob)` | - | `help/webView/WebViewPool.kt:43` | WebView 闲置清理 |

`AppConst.MAX_THREAD = 9`（`constant/AppConst.kt:25`），所有固定线程池上限 9。

### 1.3 锁结构清单（按类型分组）

#### @Synchronized / synchronized 块（120+ 处，按模块归类）

| 模块 | 文件 | 行号 | 用途 | 评估 |
|------|------|------|------|------|
| **协程容器** | `CompositeCoroutine.kt` | 28,39,64,75 | 保护 HashSet<Coroutine<*>> | 合理 |
| **缓存书籍** | `CacheBook.kt` | 49,66,209,214,219,224,229,238,251,258,268,282,288,294,305,405 | CacheBookModel 内部状态 | 部分冗余（见 3.2） |
| **缓存书籍** | `CacheBook.kt` | 382 | `downloadAwait` 中 onDownloadSet/waitDownloadSet 修改 | 合理但跨方法复合操作非原子 |
| **日志** | `AppLog.kt` | 16,37,53 | 保护 mLogs ArrayList | 全局锁瓶颈（见 5.3） |
| **意图数据** | `IntentData.kt` | 12,20,43 | 保护 ConcurrentHashMap | 冗余（见 5.4） |
| **TTS** | `TTS.kt` | 51,70 | TTS 状态 | 合理 |
| **本地书籍** | `EpubFile.kt` / `MobiFile.kt` / `PdfFile.kt` / `UmdFile.kt` / `TextFile.kt` | 多处 | 文件解析器单例状态 | 合理 |
| **下载服务** | `DownloadService.kt` | 89,130,143,165 | 下载任务队列 | 合理 |
| **朗读服务** | `BaseReadAloudService.kt:401` / `TTSReadAloudService.kt:50,63,85` | - | 朗读状态 | 合理 |
| **书源验证** | `SourceVerificationHelp.kt:32` | - | 验证状态 | 合理 |
| **生命周期** | `LifecycleHelp.kt:93,99` | - | 生命周期回调 | 合理 |
| **主界面** | `MainViewModel.kt:129,235` | - | waitUpTocBooks 操作 | 与 poll() 不一致（见 4.1） |
| **配置** | `ReadBookConfig.kt:70,127` | - | 配置读写 | 合理 |
| **书籍帮助** | `BookHelp.kt:230,275,280` | - | 图片下载/写入 | 部分瓶颈（见 5.5） |
| **适配器** | `ExploreAdapter.kt:531,540,549,558` / `MangaAdapter.kt:205,219` | - | 列表数据 | 合理 |
| **画布录制** | `CanvasRecorderLocked.kt:13` | - | ReentrantLock 包装 | 合理 |
| **对象池** | `ObjectPoolLocked.kt:5,10` | - | 对象池同步包装 | 合理 |
| **HTTP** | `ObsoleteUrlFactory.kt:161,411,423,441,520,527,539,548,569` | - | URL 连接工厂 | 合理（第三方代码） |
| **其他** | `FileUtils.kt:35` / `ConflateLiveData.kt:23` / `ACache.kt:57,756` / `BookshelfFragment1.kt:92` / `ReadRssViewModel.kt:284` / `VerticalSeekBar.kt:246,254,284,309` / `ImportBookActivity.kt:231,287,293` / `BiliDanmukuParser.kt:123` / `LargeBodyUploadProvider.kt:49` / `CronetLoader.kt:66,261` | - | 各类状态保护 | 多数合理 |
| **限流器** | `ConcurrentRateLimiter.kt:74` | - | `synchronized(fetchRecord)` 保护单条记录 | 合理 |
| **音频** | `AudioPlay.kt:149,157` / `ReadManga.kt:85,107` | - | 播放状态 | 合理 |

#### Mutex（kotlinx.coroutines.sync.Mutex，9 处）

| 文件 | 行号 | 字段 | 用途 | 评估 |
|------|------|------|------|------|
| `CacheBook.kt` | 47 | `mutex` | `startProcessJob` 串行化 | 合理 |
| `CacheBookService.kt` | 49 | `mutex` | 章节列表加载串行化 | 合理 |
| `HttpReadAloudService.kt` | 96 | `downloadTaskActiveLock` | 下载任务激活状态 | 合理 |
| `ReadBook.kt` | 80,81,82 | `prev/cur/nextChapterLoadingLock` | 三章加载互斥 | 合理（避免连续翻页时重复加载） |
| `Restore.kt` | 68 | `mutex` | 恢复操作串行化 | 合理 |
| `Backup.kt` | 63 | `mutex` | 备份操作串行化 | 合理 |
| `BookHelp.kt` | 62 | `downloadImages: ConcurrentHashMap<String, Mutex>` | 单图下载互斥 | 设计合理，但 remove 时机有问题（见 4.5） |
| `BookSourceExtensions.kt` | 27 | `mutexMap: hashMapOf<String, Mutex>` | **非线程安全容器** | **Bug**（见 4.2） |

#### ReentrantLock（java.util.concurrent.locks.ReentrantLock，2 处）

| 文件 | 行号 | 字段 | 用途 |
|------|------|------|------|
| `WebViewPool.kt` | 39 | `poolLock` | WebView 池 idlePool/inUsePool 互斥 |
| `CanvasRecorderLocked.kt` | 9,15 | `lock` | 画布录制器同步包装 |

### 1.4 并发集合清单（全项目）

| 类型 | 文件 | 行号 | 用途 |
|------|------|------|------|
| `ConcurrentHashMap` | `CacheBook.kt:44` | `cacheBookMap` | 书籍缓存模型表 |
| `ConcurrentHashMap` | `ConcurrentRateLimiter.kt:12` | `concurrentRecordMap` | 并发限流记录 |
| `ConcurrentHashMap` | `BookHelp.kt:62` | `downloadImages` | 图片下载 Mutex 表 |
| `ConcurrentHashMap` | `ContentProcessor.kt` | （略） | 替换规则缓存 |
| `ConcurrentHashMap` | `BookExtensions.kt:111` | - | Uri 缓存 |
| `ConcurrentHashMap` | `AnalyzeUrl.kt:773` | `customIp` | 自定义 IP |
| `ConcurrentHashMap` | `RuleUpdate.kt:22,23,24` | `cacheBookSourceMap/cacheRssSourceMap/cacheReplaceRuleMap` | 规则更新缓存 |
| `ConcurrentHashMap` | `ReadBook.kt:79` | `chapterLoadingJobs` | 章节加载任务表 |
| `ConcurrentHashMap` | `ReadBook.kt:93` | `downloadFailChapters` | 下载失败次数 |
| `ConcurrentHashMap` | `ProgressManager.kt:11` | `listenersMap` | Glide 进度监听 |
| `ConcurrentHashMap` | `GlideImageGetter.kt:46` | `cacheDrawable` | 图片 drawable 缓存 |
| `ConcurrentHashMap` | `IntentData.kt:7,10` | `bigData/activityDataKeys` | Activity 数据传递 |
| `ConcurrentHashMap` | `HttpHelper.kt:25` | `proxyClientCache` | 代理 OkHttpClient 缓存 |
| `ConcurrentHashMap` | `BookSourceExtensions.kt:28` | `exploreKindsMap` | 发现分类缓存 |
| `ConcurrentHashMap` | `ChangeBookSourceViewModel.kt:76,99` | `tocMap/bookMap` | 换源数据 |
| `ConcurrentHashMap` | `ChapterListAdapter.kt:32` | `displayTitleMap` | 章节标题缓存 |
| `ConcurrentHashMap` | `ExportBookService.kt:80,81` | `exportProgress/exportMsg` | 导出进度 |
| `ConcurrentHashMap` | `ExploreShowViewModel.kt:26` / `SearchViewModel.kt:26` | `bookshelf` | 书架判断 |
| `ConcurrentHashMap` | `ExploreAdapter.kt:79` | `sourceKinds` | 来源分类 |
| `ConcurrentHashMap` | `MainViewModel.kt:56,57` | `onUpTocBooks/eventListenerSource` | 目录更新跟踪 |
| `CopyOnWriteArrayList` | `RecyclerAdapter.kt:35` | `items` | 适配器数据 |
| `CopyOnWriteArrayList` | `ContentProcessor.kt:56,57` | `titleReplaceRules/contentReplaceRules` | 替换规则 |
| `CopyOnWriteArrayList` | `ReadBook.kt:77` | `loadingChapters` | 加载中章节 |
| `CopyOnWriteArraySet` | `ReadBook.kt:92` | `downloadedChapters` | 已下载章节 |
| `AtomicBoolean` | `AbsCallBack.kt:50` | `finished` | Cronet 回调完成标志 |
| `AtomicBoolean` | `AbsCallBack.kt:51` | `canceled` | Cronet 回调取消标志 |
| `AtomicInteger` | `ACache.kt:646` / `FileDocExtensions.kt:240` | `cacheCount/maxFinds` | 计数 |
| `AtomicLong` | `ACache.kt:645` | `cacheSize` | 缓存大小 |

### 1.5 调度策略（Dispatchers 使用）

| Dispatcher | 使用场景 | 评估 |
|------------|----------|------|
| `Dispatchers.IO` | 默认 IO 操作（Coroutine.async 默认 context、所有 runBlocking(IO)、withContext(IO)） | 主导，合理 |
| `Dispatchers.Main` | UI 回调（Coroutine 默认 executeContext、LiveEvent setValue、callBack?.upContent 等） | 合理 |
| `Dispatchers.Default` | CPU 密集（`CoverImageView.kt:129` 加载封面、`ChapterListFragment.kt`） | 少量使用，合理 |
| `Dispatchers.Unconfined` | 未发现使用 | - |
| 自定义线程池 | 见 1.2 表 | 隔离性好，但池数偏多（10 个） |

### 1.6 协程作用域清单

| 作用域 | 位置 | 类型 | 用途 |
|--------|------|------|------|
| `Coroutine.DEFAULT = MainScope()` | `Coroutine.kt:37` | `MainScope()` | 默认协程作用域（**泄漏风险**，见 4.6） |
| `ReadBook` | `ReadBook.kt:62` | `MainScope()` | 全局阅读状态 |
| `ReadManga` | `ReadManga.kt:45` | `MainScope()` | 全局漫画状态 |
| `AudioPlay` | `AudioPlay.kt:40` | `MainScope()` | 全局音频播放 |
| `VideoPlay` | `VideoPlay.kt:55` | `MainScope()` | 全局视频播放 |
| `ReadBook.downloadScope` | `ReadBook.kt:95` | `SupervisorJob() + IO` | 章节下载 |
| `ReadManga.downloadScope` | `ReadManga.kt:65` | `SupervisorJob() + IO` | 漫画下载 |
| `VideoPlay.loadScope` | `VideoPlay.kt:98` | `SupervisorJob() + IO` | 视频加载 |
| `WebViewPool.cleanupScope` | `WebViewPool.kt:43` | `SupervisorJob() + IO` | WebView 清理 |
| `viewModelScope` | 多处 ViewModel | AndroidX | ViewModel 生命周期绑定 |
| `lifecycleScope` | 多处 Service/Activity | AndroidX | 生命周期绑定 |
| `DispatchersMonitor.scope` | `DispatchersMonitor.kt:31` | 自定义单线程 dispatcher | 调度器监控 |

---

## 二、逐文件深度分析

### 2.1 Coroutine.kt（链式协程核心）

**位置**：`app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt`

#### 实现要点

- **构造**（L26-33）：`scope` + `context`（执行 block 的 dispatcher）+ `startOption` + `executeContext`（回调执行的 dispatcher）+ `semaphore` + `block`
- **默认值**：`scope=MainScope()`、`context=IO`、`executeContext=Main`
- **链式回调**：`onStart/onSuccess/onError/onFinally/onCancel` 各自保存 `Callback`/`VoidCallback`，在 `executeInternal` 中按序派发
- **派发逻辑**（L201-224）：`dispatchCallback` 检查 `scope.isActive` 后用 `withContext(callback.context)` 切换上下文
- **超时**（L226-239）：`withTimeout(timeMillis)` 包裹 block
- **取消**（L131-142）：`onCancel` 注册 `job.invokeOnCompletion`，仅在 `CancellationException && !ActivelyCancelException` 时触发
- **主动取消**（L145-160）：`cancel()` 调用 `job.cancel(cause)` 后，**用 `DEFAULT.launch(executeContext)` 启动新协程执行 cancel 回调**

#### 问题识别

| 编号 | 行号 | 问题 | 严重程度 |
|------|------|------|----------|
| C-1 | L182 | `catch (e: Throwable)` 未先 catch `CancellationException` 重新抛出，破坏协程取消语义 | **严重 Bug**（见 4.1） |
| C-2 | L150 | `cancel()` 内 `DEFAULT.launch(executeContext)` 启动无 scope 控制的协程，父 scope 取消时不会传播 | 中（泄漏风险） |
| C-3 | L174 | `(scope.plus(executeContext)).launch` 把 executeContext 加到 scope，导致 block 在 executeContext 而非 context 中执行起始/结束回调 | 设计选择（与文档"回调在 Main"一致） |
| C-4 | L233 | `withTimeout(timeMillis)` 抛 `TimeoutCancellationException` 是 CancellationException 子类，被 L182 的 `catch (e: Throwable)` 捕获后调用 `error?.let`，**超时变成 onError 而非取消** | **Bug**（被 C-1 掩盖） |
| C-5 | L191-197 | `finally` 中 `semaphore?.release()` 嵌套 try-finally，若 `dispatchVoidCallback` 抛异常，semaphore 仍会 release（合理），但若 `cancel()` 在 finally 期间触发，行为未定义 | 低 |
| C-6 | L37 | `DEFAULT = MainScope()` 是全局单例，无生命周期所有者，cancel 回调协程会泄漏到进程结束 | 中 |

### 2.2 CompositeCoroutine.kt

**位置**：`app/src/main/java/io/legado/app/help/coroutine/CompositeCoroutine.kt`

- 用 `HashSet<Coroutine<*>>` + `synchronized(this)` 管理
- `add/addAll/remove/delete/clear` 全部 `synchronized(this)`
- `clear()`（L73-83）先在锁内取出 set 引用并置 null，再在锁外逐个 `coroutine.cancel()` —— **正确**（避免持锁调用外部代码）
- `remove()`（L55-61）在锁外调用 `coroutine.cancel()` —— **正确**

无问题。

### 2.3 CoroutineContainer.kt

仅接口定义，无逻辑。

### 2.4 ActivelyCancelException.kt

- 继承 `kotlin.coroutines.cancellation.CancellationException`（注意：用的是 `kotlin.coroutines.cancellation` 而非 `kotlinx.coroutines.CancellationException`，两者在 JVM 上是同一类型）
- 覆写 `fillInStackTrace()` 返回 `this` 并置空 stackTrace —— 用于区分主动取消与协程取消

无问题。

### 2.5 FlowExtensions.kt

**位置**：`app/src/main/java/io/legado/app/utils/FlowExtensions.kt`

#### 实现要点

- `onEachParallel`（L26-34）：`flatMapMerge(concurrency) { flow { action(value); emit(value) } }.buffer(0)`
- `onEachParallelSafe`（L37-49）：在 action 外加 `try { } catch (e: Throwable) { currentCoroutineContext().ensureActive() }` —— **正确处理了 CancellationException**（ensureActive 会重新抛出）
- `mapParallel` / `mapParallelSafe` / `transformParallelSafe`：类似模式
- `mapAsync` / `mapAsyncIndexed` / `onEachAsync` / `onEachAsyncIndexed`（L110-194）：用 `Semaphore(concurrency) + channelFlow + async + await` 实现，**concurrency==1 时退化为 onEach/map**（优化）

#### 问题识别

| 编号 | 行号 | 问题 | 严重程度 |
|------|------|------|----------|
| F-1 | L29 | `onEachParallel` 用 `flatMapMerge`，**action 抛异常会传播到下游**，导致整个流取消 | 设计选择（故意的，`Safe` 版本才是容错） |
| F-2 | L44 | `onEachParallelSafe` 的 `catch (e: Throwable)` 后调 `ensureActive()`，但**仍 emit(value)**，即 action 失败也 emit | 设计选择（语义为"安全"=不崩溃，但调用方可能误以为失败不传播） |

### 2.6 ConcurrentRateLimiter.kt

**位置**：`app/src/main/java/io/legado/app/help/ConcurrentRateLimiter.kt`

#### 实现要点

- `concurrentRecordMap = ConcurrentHashMap<String, ConcurrentRecord>`（L12）
- `updateConcurrentRate`（L16-46）：用 `compute` 原子更新
- `fetchStart`（L55-98）：`computeIfAbsent` 创建记录；`synchronized(fetchRecord)` 保护单条记录的字段修改
- `getConcurrentRecord`（L103-111）：`while(true) { try { return fetchStart() } catch (ConcurrentException) { delay(e.waitTime) } }`
- `getConcurrentRecordBlocking`（L113-121）：用 `Thread.sleep` —— **阻塞线程，在协程上下文中危险**

#### 问题识别

| 编号 | 行号 | 问题 | 严重程度 |
|------|------|------|----------|
| RL-1 | L104 | `while(true)` 无退出条件，若 `ConcurrentException` 持续抛出（如 waitTime=0 或负数）会死循环 | 低（实际 waitTime 来自 nextTime-nowTime，应 >0） |
| RL-2 | L113 | `getConcurrentRecordBlocking` 用 `Thread.sleep`，若在协程中调用会阻塞调度器线程 | 中（应标记 `@ObsoleteCoroutinesApi` 或删除） |
| RL-3 | L74 | `synchronized(fetchRecord)` 锁的是 `ConcurrentRecord` 对象，若该对象被替换（`compute` 返回新对象），锁失效 | 低（compute 只在 `updateConcurrentRate` 中替换，且替换时其他线程已持有旧引用，旧引用的 synchronized 仍有效） |

### 2.7 CacheBook.kt（章节缓存，含锁结构）

**位置**：`app/src/main/java/io/legado/app/model/CacheBook.kt`

#### 实现要点

- `cacheBookMap = ConcurrentHashMap<String, CacheBookModel>`（L44）
- `mutex = Mutex()`（L47）用于 `startProcessJob` 串行化
- `workingState = MutableStateFlow(true)`（L46）
- `CacheBookModel` 内部用 `linkedSetOf<Int>` 等普通集合 + `@Synchronized` 保护
- `successDownloadSet = linkedSetOf<String>()` / `errorDownloadMap = hashMapOf<String, Int>()`（L190-191）是**普通集合**，被 `CacheBookModel` 内的 `@Synchronized` 方法访问

#### 问题识别

| 编号 | 行号 | 问题 | 严重程度 |
|------|------|------|----------|
| CB-1 | L49,67 | `@Synchronized getOrCreate` 操作 `ConcurrentHashMap`，重复加锁 | 性能（见 5.6） |
| CB-2 | L117 | `close()` 不是 `@Synchronized`，与 `@Synchronized` 方法并发可能 race（如 `cacheBookMap.forEach` 与 `addDownload` 的 `cacheBookMap[book.bookUrl] = this`） | **中 Bug** |
| CB-3 | L190-191 | `successDownloadSet`/`errorDownloadMap` 是普通 `linkedSetOf`/`hashMapOf`，虽被 `@Synchronized` 方法保护，但 `downloadSummary` getter（L157-160）**未加锁**访问 `errorDownloadMap` 和 `successDownloadSet` | **中 Bug**（与 `onSuccess`/`onPreError`/`onPostError` 并发时 ConcurrentModificationException） |
| CB-4 | L133 | `startProcessJob` 的 `flow { cacheBookMap.forEach { ... } }` 中 `workingState.first { it }`（L138）**在 forEach 内部调用**，每个 model 都会挂起等待 workingState=true，阻塞 forEach 迭代 | 设计选择（但低效） |
| CB-5 | L306 | `CacheBookModel.download` 是 `@Synchronized`，内部启动 `Coroutine.async` 后 return，**锁持有时间 = 启动协程时间**（含 `appDb.bookChapterDao.getChapter` 同步数据库查询） | 性能（数据库查询不应在锁内） |
| CB-6 | L382 | `downloadAwait` 的 `synchronized(this) { onDownloadSet.add; waitDownloadSet.remove }` 只保护 add/remove，**后续 `WebBook.getContentAwait` 不在锁内**，但 `onSuccess`/`onError` 是 `@Synchronized` —— 跨方法复合操作非原子 | 中 |
| CB-7 | L127-153 | `startProcessJob` 用 `mutex.withLock` 串行化整个流程，但内部 `flow { while(...) { cacheBookMap.forEach { emit(model) } } }` 的 emit 会挂起，**mutex 持有时间 = 整个缓存下载周期** | 设计选择（但 mutex 实际无意义，因为 `startProcessJob` 只被 `CacheBookService.download` 调用，已串行） |

---

## 三、项目全局多线程问题扫描

### 3.1 CancellationException 处理全貌

全项目 `catch (e: Throwable)` / `catch (e: Exception)` 共 181 处（89 个文件）。重点审查以下场景：

| 文件 | 行号 | 模式 | 评估 |
|------|------|------|------|
| `Coroutine.kt:182` | `catch (e: Throwable)` | **未先 catch CancellationException** | **Bug**（见 4.1） |
| `FlowExtensions.kt:44,66,80` | `catch (e: Throwable) { ensureActive() }` | 正确（ensureActive 重新抛出 CancellationException） |
| `CheckSourceService.kt:140` | `kotlin.runCatching { withTimeout(...) { doCheckSource } }` | 正确（runCatching 不捕获 CancellationException 的传播，但 onFailure 检查 `currentCoroutineContext().ensureActive()`） |
| `MainViewModel.kt:190` | `kotlin.runCatching { ... }.onFailure { currentCoroutineContext().ensureActive() }` | 正确 |
| `BookHelp.kt:256` | `catch (e: Exception) { currentCoroutineContext().ensureActive() ... }` | 正确 |
| `ReadBook.kt:608` | `catch (e: Exception) { AppLog.put(...) }` | **未检查 CancellationException** | 中（下载被取消时会记录错误日志） |
| `ReadBook.kt:766` | `onError { if (it is CancellationException) return@onError ... }` | 正确 |
| `ReadBook.kt:852` | `onFailure { if (it is CancellationException) return@onFailure ... }` | 正确 |
| `CacheBook.kt:392` | `catch (e: Exception) { if (e is CancellationException) { onCancel(...) } onError(...) }` | 正确 |
| `HttpReadAloudService.kt:288` | `kotlin.runCatching { runBlocking(...) { ... } }.onFailure { when (it) { is InterruptedException, is CancellationException -> Unit ... } }` | 正确（但 runBlocking 本身是反模式） |

### 3.2 锁结构全局问题

| 编号 | 文件:行号 | 问题 | 严重程度 |
|------|-----------|------|----------|
| L-1 | `BookSourceExtensions.kt:27,50` | `mutexMap: hashMapOf<String, Mutex>()` 是普通 HashMap，`mutexMap[bookSourceUrl] ?: Mutex().apply { mutexMap[bookSourceUrl] = this }` 非原子 | **Bug**（见 4.2） |
| L-2 | `MainViewModel.kt:129,235 vs 148` | `addToWaitUp` 是 `@Synchronized`，但 `waitUpTocBooks.poll()` 在 `flow { }` 中（L148）**无同步** | **Bug**（见 4.3） |
| L-3 | `CacheBook.kt:117` | `close()` 未加锁，与 `@Synchronized` 方法并发 race | 中（见 CB-2） |
| L-4 | `CacheBook.kt:157-160` | `downloadSummary` getter 未加锁访问 `errorDownloadMap`/`successDownloadSet` | 中（见 CB-3） |
| L-5 | `IntentData.kt:12,20,43` | `@Synchronized` 保护 `ConcurrentHashMap`，冗余 | 性能（见 5.4） |
| L-6 | `CacheBook.kt:49,67` | `@Synchronized getOrCreate` 保护 `ConcurrentHashMap`，冗余 | 性能（见 5.6） |
| L-7 | `BookHelp.kt:230` | `synchronized(this) { downloadImages.getOrPut(src) { Mutex() } }` 冗余（ConcurrentHashMap.getOrPut 本身原子） | 性能（见 5.7） |
| L-8 | `BookHelp.kt:275,280` | `@Synchronized writeImage/isImageExist` 全局锁，所有书籍图片写入串行 | 性能（见 5.5） |

### 3.3 runBlocking 全貌

全项目 `runBlocking` 调用 100+ 处，分类如下：

| 场景 | 文件 | 评估 |
|------|------|------|
| **API Controller**（HttpServer 路由处理） | `api/controller/*.kt`（BookController 13 处、BookSourceController 4 处、RssSourceController 5 处、ReplaceRuleController 4 处） | 合理（HTTP 请求处理同步返回，runBlocking 在 HttpServer 线程池中） |
| **HTTP 拦截器** | `lib/cronet/CronetCoroutineInterceptor.kt:56,78` | 合理（拦截器需同步返回） |
| **CookieManager** | `help/http/CookieManager.kt:140` | 合理（OkHttp 拦截器同步查询） |
| **JsExtensions**（书源 JS 调用） | `help/JsExtensions.kt:128,147,219,252,287` | 合理（JS 引擎同步执行） |
| **WebDav** | `help/AppWebDav.kt:58` / `lib/webdav/Authorization.kt:28` / `model/remote/RemoteBookWebDav.kt:27` | 合理（同步 API） |
| **书源/章节查询** | `help/book/BookExtensions.kt:244,250,263,302` / `help/book/ContentProcessor.kt:68,72,77,186` / `help/book/BookHelp.kt:136,192` | **性能问题**（见 5.8） |
| **CheckSourceService** | `service/CheckSourceService.kt:112,132` | **性能问题**（在 onEachParallel 协程中 runBlocking，见 5.9） |
| **AudioPlay** | `model/AudioPlay.kt:90,111,112,144,257` | **性能问题**（在 MainScope 协程中 runBlocking） |
| **HttpReadAloudService** | `service/HttpReadAloudService.kt:289` | **稳定性问题**（见 4.7） |
| **BackstageWebView** | `help/http/BackstageWebView.kt:118` | 中（在 WebView 回调中阻塞） |
| **CacheManager** | `help/CacheManager.kt:69,91,104,152` | 合理（同步缓存 API） |
| **DefaultData** | `help/DefaultData.kt:119,126,133,140` | 合理（启动时同步初始化） |
| **SharedJsScope** | `model/SharedJsScope.kt:54` | 合理（JS 引擎同步执行） |
| **BaseSource** | `data/entities/BaseSource.kt:295,309` | 中（实体方法中 runBlocking，反模式） |
| **ImportOldData** | `help/storage/ImportOldData.kt:105,111,118,127` | 合理（一次性数据迁移） |
| **ReadAloud** | `model/ReadAloud.kt:35` | 中（初始化时阻塞） |

### 3.4 协程调度 ANR 风险扫描

| 文件:行号 | 场景 | 风险 |
|-----------|------|------|
| `AudioPlay.kt:90,111,112,144,257` | `runBlocking(IO)` 在 `MainScope` 协程中 | **中**（主线程协程被阻塞，但 IO dispatcher 实际是线程池，不会 ANR，但会阻塞 Main 协程的其他 launch） |
| `BookHelp.kt:136,192` | `runBlocking(IO)` 在 `withContext(IO)` 内 | 低（已在 IO 线程） |
| `ContentProcessor.kt:68,72,77,186` | `runBlocking(IO)` 在 `CopyOnWriteArrayList` 的初始化块中 | 中（初始化阻塞调用线程） |
| `BookExtensions.kt:244,250,263,302` | `runBlocking(IO)` 在普通函数中 | 中（调用方可能误用） |
| `CheckSourceService.kt:112,132` | `runBlocking(IO)` 在 `onEachParallel(threadCount)` 协程中 | **高**（阻塞线程池线程，实际并发度降低） |

---

## 四、明确 Bug 清单

### 4.1 [严重 Bug] Coroutine.kt:182 未先 catch CancellationException

**文件**：`app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt:182`

**问题**：
```kotlin
} catch (e: Throwable) {
    e.printOnDebug()
    val consume: Boolean = errorReturn?.value?.let { value ->
        success?.let { dispatchCallback(this, value, it) }
        true
    } ?: false
    if (!consume) {
        error?.let { dispatchCallback(this, e, it) }
    }
}
```

`catch (e: Throwable)` 会捕获 `CancellationException`，导致：
1. **协程取消语义被破坏**：调用方 `job.cancel()` 后，block 抛出的 `CancellationException` 被这里捕获，调用 `error?.let { dispatchCallback(this, e, it) }`，即 onError 收到 CancellationException
2. **withTimeout 失效**：`executeBlock` 中的 `withTimeout(timeMillis)` 抛出 `TimeoutCancellationException`（是 CancellationException 子类），被这里捕获后变成 onError 而非取消
3. **ensureActive() 失效**：block 内的 `ensureActive()` 抛出的 CancellationException 被捕获，调用方无法感知取消

**对比延伸版本**：
- **蛋蛋Max**（DandanLLab/Legado_Max）：在 L162 增加 `catch (e: CancellationException) { throw e }` —— **已修复**
- **阅读NG**（joestar817/legado_NG）：未修复（与本项目相同）
- **阅读Archive**（Rimchars/legado）：未修复（与本项目相同）

**修复建议**：
```kotlin
} catch (e: CancellationException) {
    throw e
} catch (e: Throwable) {
    e.printOnDebug()
    ...
}
```

**严重程度**：严重。影响所有使用 `Coroutine.async` 的取消场景，包括 ReadBook 章节加载取消、CacheBook 下载取消、WebBook 搜索取消等。

### 4.2 [Bug] BookSourceExtensions.kt:27 非线程安全的 Mutex 容器

**文件**：`app/src/main/java/io/legado/app/help/source/BookSourceExtensions.kt:27,50`

**问题**：
```kotlin
private val mutexMap by lazy { hashMapOf<String, Mutex>() }  // L27 普通 HashMap

val mutex = mutexMap[bookSourceUrl] ?: Mutex().apply { mutexMap[bookSourceUrl] = this }  // L50 非原子
```

`hashMapOf` 是普通 `HashMap`，多线程并发 `get`/`put` 会导致：
1. HashMap 内部结构损坏（死循环、数据丢失）
2. 同一 `bookSourceUrl` 可能创建多个 Mutex，互斥失效

**修复建议**：
```kotlin
private val mutexMap by lazy { ConcurrentHashMap<String, Mutex>() }
// L50:
val mutex = mutexMap.computeIfAbsent(bookSourceUrl) { Mutex() }
```

**严重程度**：高。`exploreKinds()` 在书源探索、发现页加载时被多线程并发调用。

### 4.3 [Bug] MainViewModel.kt:148 waitUpTocBooks.poll() 无同步保护

**文件**：`app/src/main/java/io/legado/app/ui/main/MainViewModel.kt:129,148`

**问题**：
```kotlin
@Synchronized
private fun addToWaitUp(books: List<Book>, onlyUpdateRead: Boolean) {  // L129 加锁
    books.forEach { book ->
        ...
        waitUpTocBooks.add(book.bookUrl)  // LinkedList.add
    }
}

upTocJob = viewModelScope.launch(upTocPool) {
    flow {
        while (true) {
            emit(waitUpTocBooks.poll() ?: break)  // L148 无锁 poll
        }
    }.onEachParallel(threadCount) { ... }
}
```

`addToWaitUp` 用 `@Synchronized` 保护 `add`，但 `poll()` 在 flow 中无同步保护，两者并发时 `LinkedList` 的 `add` 和 `poll` 可能导致：
1. `ConcurrentModificationException`
2. 元素丢失

**修复建议**：用 `ConcurrentLinkedQueue<String>` 替代 `LinkedList<String>`，或把 `poll()` 也放进 `synchronized(this)` 块。

**严重程度**：中。书架刷新时可能丢失书籍更新。

### 4.4 [Bug] CacheBook.kt:157-160 downloadSummary 未加锁访问普通集合

**文件**：`app/src/main/java/io/legado/app/model/CacheBook.kt:157-160,190-191`

**问题**：
```kotlin
val successDownloadSet = linkedSetOf<String>()  // L190 普通集合
val errorDownloadMap = hashMapOf<String, Int>()  // L191 普通集合

@Synchronized private fun onSuccess(chapter: BookChapter) {
    successDownloadSet.add(...)  // 加锁
    errorDownloadMap.remove(...)  // 加锁
}

val downloadSummary: String
    get() {
        return "正在下载:${onDownloadCount}|等待中:${waitCount}|失败:${errorDownloadMap.count()}|成功:${successDownloadSet.size}"  // L157-160 未加锁
    }
```

`downloadSummary` getter 在 `CacheBookService.onCreate` 的 `lifecycleScope.launch { while (isActive) { delay(1000); notificationContent = CacheBook.downloadSummary; ... } }` 中被调用（每秒一次，主线程协程），而 `onSuccess`/`onPreError`/`onPostError` 在 IO 协程中执行 —— **并发读写普通集合，可能 ConcurrentModificationException**。

**修复建议**：
1. `successDownloadSet` 改为 `ConcurrentHashMap.newKeySet<String>()`
2. `errorDownloadMap` 改为 `ConcurrentHashMap<String, AtomicInteger>`
3. 或在 `downloadSummary` getter 加 `@Synchronized`

**严重程度**：中。崩溃风险。

### 4.5 [Bug] BookHelp.kt:261 downloadImages.remove(src) 时机不当

**文件**：`app/src/main/java/io/legado/app/help/book/BookHelp.kt:230-263`

**问题**：
```kotlin
val mutex = synchronized(this) {
    downloadImages.getOrPut(src) { Mutex() }
}
mutex.lock()
try {
    ...
} finally {
    downloadImages.remove(src)  // L261 在 unlock 前移除
    mutex.unlock()
}
```

如果协程 A 持有 mutex，协程 B 在 `downloadImages.getOrPut(src)` 时拿到**新的 Mutex**（因为 A 还没 remove 但 B 在 A remove 后才到？不，A 在 finally 中先 remove 再 unlock，B 在 A unlock 后才能 lock）。

实际场景：
1. A 持有 mutex（lock 成功）
2. B 调用 `getOrPut(src)`，拿到同一个 mutex
3. B 调用 `mutex.lock()`，阻塞
4. A 在 finally 中 `downloadImages.remove(src)` 然后 `mutex.unlock()`
5. B 获得锁，但此时 `downloadImages` 中已无 src
6. C 调用 `getOrPut(src)`，拿到**新的 Mutex**，C 调用 `mutex.lock()` 成功
7. B 和 C 同时执行 —— **互斥失效**

**修复建议**：把 `downloadImages.remove(src)` 移到 `mutex.unlock()` 之后，或干脆不移除（让 Mutex 自然 GC，但会内存泄漏）。更优方案是用 `computeIfAbsent` + 不 remove，定期清理。

**严重程度**：中。同一图片并发下载时可能重复下载（不会数据损坏，因为 `isImageExist` 二次检查）。

### 4.6 [Bug] Coroutine.kt:37 DEFAULT = MainScope() 无生命周期所有者

**文件**：`app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt:37,150`

**问题**：
- `DEFAULT = MainScope()` 是全局单例，进程级生命周期
- `cancel()` 方法（L150）在 `DEFAULT.launch(executeContext)` 中执行 cancel 回调
- 若调用方未持有 `Coroutine` 引用，cancel 回调协程会泄漏到进程结束

**修复建议**：`onCancel` 回调应通过 `job.invokeOnCompletion` 直接同步执行（不启动新协程），或让调用方传入 scope。

**严重程度**：中。泄漏量小（每次 cancel 一个协程），但长期运行可能累积。

### 4.7 [稳定性] HttpReadAloudService.kt:289 runBlocking 在 ExoPlayer 线程

**文件**：`app/src/main/java/io/legado/app/service/HttpReadAloudService.kt:289`

**问题**：
```kotlin
val upstreamFactory = DataSource.Factory {
    InputStreamDataSource {
        ...
        kotlin.runCatching {
            runBlocking(lifecycleScope.coroutineContext[Job]!!) {  // L289
                getSpeakStream(httpTts, speakText)
            }
        }.onFailure { ... }.getOrThrow()
    }
}
```

`runBlocking(lifecycleScope.coroutineContext[Job]!!)` 在 ExoPlayer 的加载线程中调用，**阻塞该线程**直到 `getSpeakStream` 完成。若 `getSpeakStream` 涉及网络请求（10s+），ExoPlayer 线程被阻塞，可能导致：
1. 播放器 ANR
2. ExoPlayer 内部调度混乱

**修复建议**：用 `runBlocking` 替代不可行（DataSource.Factory 必须同步返回），但应：
1. 给 `getSpeakStream` 加超时
2. 用独立的 `CoroutineScope` 而非 `lifecycleScope` 的 Job（避免 Service 销毁时 cancel 导致 InputStreamDataSource 异常）

**严重程度**：中。影响在线朗读体验。

### 4.8 [Bug] CacheBook.kt:117 close() 未加锁

**文件**：`app/src/main/java/io/legado/app/model/CacheBook.kt:116-121`

**问题**：
```kotlin
fun close() {  // 未加 @Synchronized
    cacheBookMap.forEach { it.value.stop() }  // stop() 是 @Synchronized
    cacheBookMap.clear()
    successDownloadSet.clear()  // 普通集合
    errorDownloadMap.clear()    // 普通集合
}
```

`close()` 与 `addDownload`（L238 @Synchronized）并发时：
- `addDownload` 可能向已被 `clear()` 的 `cacheBookMap` 添加
- `successDownloadSet.clear()` 与 `onSuccess` 的 `successDownloadSet.add()` 并发 —— ConcurrentModificationException

**修复建议**：`close()` 加 `@Synchronized`。

**严重程度**：中。

---

## 五、性能问题清单

### 5.1 [P-高] CheckSourceService.kt:112,132 runBlocking 在 onEachParallel 协程中

**文件**：`app/src/main/java/io/legado/app/service/CheckSourceService.kt:112,132`

**问题**：
```kotlin
flow {
    for (origin in ids) {
        runBlocking(IO) { appDb.bookSourceDao.getBookSource(origin) }?.let { emit(it) }  // L112
    }
}.onEachParallel(threadCount) {
    checkSource(it)
}.onEach {
    ...
    runBlocking(IO) { appDb.bookSourceDao.update(it) }  // L132
}
```

`onEachParallel(threadCount)` 用 `threadCount` 个并发，但每个并发内部又 `runBlocking(IO)` —— **占用线程池线程**，实际并发度 = `min(threadCount, IO线程池空闲线程数)`，且 `runBlocking` 切换 dispatcher 有开销。

**修复建议**：把 `runBlocking(IO) { ... }` 改为 `withContext(IO) { ... }`。

**严重程度**：高。书源校验是高频操作，影响用户体验。

### 5.2 [P-高] BookHelp.kt:275,280 @Synchronized 全局锁瓶颈

**文件**：`app/src/main/java/io/legado/app/help/book/BookHelp.kt:275,280`

**问题**：
```kotlin
@Synchronized
fun writeImage(book: Book, src: String, bytes: ByteArray) {
    getImage(book, src).createFileIfNotExist().writeBytes(bytes)
}

@Synchronized
fun isImageExist(book: Book, src: String): Boolean {
    return getImage(book, src).exists()
}
```

`@Synchronized` 锁的是 `BookHelp` 单例对象，**所有书籍的所有图片写入/存在检查全部串行**。漫画书下载时（`saveImages` 用 `onEachParallel(concurrency)`），实际并发度被这两个方法限制为 1。

**修复建议**：用 `synchronized(book.getFolderName().intern())` 按书籍锁，或用 `ConcurrentHashMap<String, Any>` 作为每本书的锁对象。

**严重程度**：高。漫画下载性能瓶颈。

### 5.3 [P-中] AppLog.kt:16,37,53 @Synchronized 全局日志锁

**文件**：`app/src/main/java/io/legado/app/constant/AppLog.kt:16,37,53`

**问题**：所有 `put/putNotSave/clear` 都是 `@Synchronized`，日志写入串行。在书源校验等高频日志场景下成为瓶颈。

**修复建议**：用 `ConcurrentLinkedQueue` 替代 `ArrayList`，或用单线程 executor（`globalExecutor`）异步写入。

**严重程度**：中。

### 5.4 [P-低] IntentData.kt:12,20,43 @Synchronized 保护 ConcurrentHashMap 冗余

**文件**：`app/src/main/java/io/legado/app/help/IntentData.kt:12,20,43`

**问题**：`bigData` 已是 `ConcurrentHashMap`，`@Synchronized` 保护其 `put/remove` 是冗余的。

**修复建议**：移除 `@Synchronized`，直接用 `ConcurrentHashMap` 的原子方法。

**严重程度**：低。

### 5.5 [P-中] BookHelp.kt:275,280 见 5.2

### 5.6 [P-低] CacheBook.kt:49,67 @Synchronized 保护 ConcurrentHashMap 冗余

**文件**：`app/src/main/java/io/legado/app/model/CacheBook.kt:49,67`

**问题**：`cacheBookMap` 是 `ConcurrentHashMap`，`@Synchronized getOrCreate` 重复加锁。

**但**：`getOrCreate` 内部是"检查-创建-放入"复合操作，`ConcurrentHashMap` 单方法不能保证原子性，**这里 @Synchronized 是必要的**。建议用 `computeIfAbsent` 替代。

**修复建议**：
```kotlin
fun getOrCreate(bookSource: BookSource, book: Book): CacheBookModel {
    updateBookSource(bookSource)
    return cacheBookMap.computeIfAbsent(book.bookUrl) {
        CacheBookModel(bookSource, book)
    }.apply {
        this.bookSource = bookSource
        this.book = book
    }
}
```

**严重程度**：低（但 `updateBookSource` 遍历整个 map，加锁是合理的）。

### 5.7 [P-低] BookHelp.kt:230 synchronized(this) 包裹 ConcurrentHashMap.getOrPut 冗余

**文件**：`app/src/main/java/io/legado/app/help/book/BookHelp.kt:230`

**问题**：
```kotlin
val mutex = synchronized(this) {
    downloadImages.getOrPut(src) { Mutex() }
}
```

`ConcurrentHashMap.getOrPut` 在 Kotlin 扩展函数中是 `get` + `putIfAbsent` 的组合，**不是原子的**（Kotlin 标准库的 `getOrPut` 对 `ConcurrentHashMap` 不原子）。所以这里的 `synchronized(this)` **不是冗余的**，但用 `computeIfAbsent` 更优雅。

**修复建议**：
```kotlin
val mutex = downloadImages.computeIfAbsent(src) { Mutex() }
```

**严重程度**：低。

### 5.8 [P-中] BookHelp.kt:136,192 runBlocking(IO) 在 withContext(IO) 内

**文件**：`app/src/main/java/io/legado/app/help/book/BookHelp.kt:136,192`

**问题**：
```kotlin
suspend fun clearInvalidCache() = withContext(IO) {
    ...
    appDb.bookDao.all.forEach {
        clearComicCache(it)  // L102
        ...
    }
}

private fun clearComicCache(book: Book) {  // 非 suspend
    ...
    val chapterList = runBlocking(IO) { appDb.bookChapterDao.getChapterList(...) }  // L136
    ...
}
```

`clearComicCache` 是非 suspend 函数，在 `withContext(IO)` 内调用，又 `runBlocking(IO)` —— **嵌套阻塞**。`runBlocking` 会创建新的事件循环，开销大。

**修复建议**：把 `clearComicCache` 改为 `suspend fun`，用 `withContext(IO)` 替代 `runBlocking(IO)`。

**严重程度**：中。

### 5.9 [P-高] 见 5.1 CheckSourceService runBlocking

### 5.10 [P-中] MainViewModel.kt:257 cacheBookJob 使用 upTocPool 命名误导

**文件**：`app/src/main/java/io/legado/app/ui/main/MainViewModel.kt:257`

**问题**：
```kotlin
cacheBookJob = viewModelScope.launch(upTocPool) {  // L257 用 upTocPool 跑缓存任务
    ...
    CacheBook.startProcessJob(upTocPool)
}
```

`upTocPool` 同时用于目录更新（`upTocJob`）和章节缓存（`cacheBookJob`），两者共享 9 个线程。目录更新和缓存下载是不同性质的任务，共享线程池可能导致相互阻塞。

**修复建议**：分离为 `upTocPool` 和 `cachePool`，或注释说明共享原因。

**严重程度**：中（设计选择，但命名误导）。

### 5.11 [P-中] CacheBookModel.download:306 @Synchronized 内查询数据库

**文件**：`app/src/main/java/io/legado/app/model/CacheBook.kt:306`

**问题**：
```kotlin
@Synchronized
fun download(scope: CoroutineScope, context: CoroutineContext) {
    ...
    val chapter = appDb.bookChapterDao.getChapter(book.bookUrl, chapterIndex) ?: let {  // L318 同步数据库查询
        ...
    }
    ...
    Coroutine.async(scope, context, executeContext = context) { ... }  // L335 启动协程
    ...
}
```

`@Synchronized` 持锁期间执行同步数据库查询 + 启动协程，**锁持有时间过长**。

**修复建议**：把数据库查询移出锁，仅用锁保护 `waitDownloadSet`/`onDownloadSet` 的修改。

**严重程度**：中。

---

## 六、稳定性问题清单

### 6.1 [S-严重] 见 4.1 Coroutine.kt:182 CancellationException 处理

### 6.2 [S-高] ReadBook.kt:63-83 核心状态字段无可见性保护

**文件**：`app/src/main/java/io/legado/app/model/ReadBook.kt:63-83`

**问题**：
```kotlin
object ReadBook : CoroutineScope by MainScope() {
    var book: Book? = null  // L63 无 @Volatile
    var chapterSize = 0     // L66
    var simulatedChapterSize = 0  // L67
    var durChapterIndex = 0  // L68
    var durChapterPos = 0    // L69
    var isLocalBook = true   // L70
    var chapterChanged = false  // L71
    var prevTextChapter: TextChapter? = null  // L72
    var curTextChapter: TextChapter? = null   // L73
    var nextTextChapter: TextChapter? = null  // L74
    var bookSource: BookSource? = null  // L75
    var msg: String? = null  // L76
    ...
}
```

这些字段在 `MainScope` 协程（主线程）、`downloadScope`（IO 线程）、`globalExecutor`（单线程）之间共享，**无 `@Volatile` 或同步保护**，可能因 JMM（Java Memory Model）可见性问题导致：
1. 一个协程更新 `durChapterIndex`，另一个协程读到旧值
2. `curTextChapter` 的引用更新对其他线程不可见

**实际影响**：因为大部分访问在 `MainScope` 协程中（主线程），问题不明显；但 `preDownload`（L931）在 `globalExecutor.execute` + `launch(IO)` 中访问 `durChapterIndex`、`chapterSize` 等，存在可见性风险。

**修复建议**：核心状态字段加 `@Volatile`，或统一在 Main 协程中读写。

**严重程度**：高（但实际触发概率低，因为大多在主线程）。

### 6.3 [S-中] ReadBook.kt:700,775 chapterLoadingJobs 复合操作非原子

**文件**：`app/src/main/java/io/legado/app/model/ReadBook.kt:700,775`

**问题**：
```kotlin
chapterLoadingJobs[chapter.index]?.cancel()  // L700
val job = Coroutine.async(...) { ... }       // L701-765
chapterLoadingJobs[chapter.index] = job      // L775
job.start()
```

`cancel` + `put` 是复合操作，虽用 `ConcurrentHashMap` 但不原子。若两个协程同时为同一 `chapter.index` 执行 `contentLoadFinish`，可能：
1. A cancel 了旧 job
2. B cancel 了 A 创建的 job
3. A put 自己的 job
4. B put 自己的 job
5. 最终 A 的 job 被 cancel 但仍在 map 中

**修复建议**：用 `synchronized(chapterLoadingJobs)` 或 `compute` 包裹整个复合操作。

**严重程度**：中（实际触发概率低，因为 `contentLoadFinish` 大多在主线程）。

### 6.4 [S-中] MainViewModel.kt:91 upTocPool.close() 取消正在执行的任务

**文件**：`app/src/main/java/io/legado/app/ui/main/MainViewModel.kt:81-93`

**问题**：
```kotlin
fun upPool() {
    ...
    if (poolSize == newPoolSize) return
    poolSize = newPoolSize
    upTocPool.close()  // L91 取消正在执行的协程
    upTocPool = Executors.newFixedThreadPool(poolSize).asCoroutineDispatcher()  // L92
}
```

`upTocPool.close()` 会关闭线程池，**正在执行的协程会被 cancel**。若用户在目录更新过程中更改线程数配置，正在更新的目录会被中断。

**修复建议**：等待当前任务完成再 close，或用 `ExecutorService.shutdown()` + `awaitTermination()`。

**严重程度**：中。

### 6.5 [S-中] ConcurrentRateLimiter.kt:113 getConcurrentRecordBlocking 死循环风险

**文件**：`app/src/main/java/io/legado/app/help/ConcurrentRateLimiter.kt:113-121`

**问题**：
```kotlin
fun getConcurrentRecordBlocking(): ConcurrentRecord? {
    while (true) {
        try {
            return fetchStart()
        } catch (e: ConcurrentException) {
            Thread.sleep(e.waitTime)  // 阻塞线程
        }
    }
}
```

`while(true)` 无退出条件，若 `ConcurrentException` 持续抛出（如 waitTime 计算异常为 0），会死循环 + Thread.sleep(0) 占用 CPU。

**修复建议**：增加最大重试次数或超时退出。

**严重程度**：中（实际触发概率低）。

### 6.6 [S-中] HttpReadAloudService.kt:289 见 4.7

### 6.7 [S-低] CacheBook.kt:127-153 startProcessJob mutex 持有时间过长

**文件**：`app/src/main/java/io/legado/app/model/CacheBook.kt:127-153`

**问题**：
```kotlin
suspend fun startProcessJob(context: CoroutineContext) = mutex.withLock {
    ...
    flow { while (...) { cacheBookMap.forEach { emit(model) } } }
        .onEachParallel(AppConfig.threadCount) { ... }
        .onCompletion { ... }
        .collect()  // L153 等待整个流完成
}
```

`mutex.withLock` 持有期间调用 `.collect()`，**锁持有时间 = 整个缓存下载周期**（可能数分钟）。虽然 `startProcessJob` 只被 `CacheBookService.download` 调用（已串行），但 mutex 实际无意义，且若被并发调用会长时间阻塞。

**修复建议**：移除 mutex（已串行），或改为非阻塞的"启动标志"检查。

**严重程度**：低。

### 6.8 [S-中] AudioPlay.kt:90,111,112,144,257 runBlocking 在 MainScope 协程中

**文件**：`app/src/main/java/io/legado/app/model/AudioPlay.kt:40,90,111,112,144,257`

**问题**：
```kotlin
object AudioPlay : CoroutineScope by MainScope() {  // L40 MainScope
    ...
    fun upData(...) {
        launch {  // Main 协程
            chapterSize = runBlocking(IO) { appDb.bookChapterDao.getChapterCount(book.bookUrl) }  // L90
        }
    }
}
```

`MainScope` 协程中 `runBlocking(IO)` 阻塞主线程协程的调度，但 `runBlocking` 内部切到 IO dispatcher，**主线程协程的其他 launch 会被阻塞**。

**修复建议**：改为 `withContext(IO) { ... }`。

**严重程度**：中。

---

## 七、延伸版本对比

### 7.1 Coroutine.kt 对比

| 版本 | CancellationException 处理 | 与本项目差异 |
|------|---------------------------|--------------|
| **本项目（legado-E fork）** | `catch (e: Throwable)` 直接捕获，**未保护** CancellationException | - |
| **蛋蛋Max**（DandanLLab/Legado_Max） | `catch (e: CancellationException) { throw e } catch (e: Throwable)` | **已修复**取消语义 |
| **阅读NG**（joestar817/legado_NG） | `catch (e: Throwable)` 直接捕获，**未保护** | 与本项目相同 |
| **阅读Archive**（Rimchars/legado） | `catch (e: Throwable)` 直接捕获，**未保护** | 与本项目相同 |
| **喵公子/阅读T/辞晨Max** | 仓库不存在或网络失败 | - |

### 7.2 ConcurrentRateLimiter.kt 对比

| 版本 | 实现差异 |
|------|----------|
| **本项目** | 与蛋蛋Max **完全相同**，无差异 |
| **蛋蛋Max** | 同本项目 |
| **阅读NG** | 未获取 |
| **阅读Archive** | 未获取 |

### 7.3 可借鉴的延伸版本优化

| 优化项 | 来源版本 | 借鉴价值 | 风险评估 |
|--------|----------|----------|----------|
| **Coroutine.kt 增加 `catch (e: CancellationException) { throw e }`** | 蛋蛋Max | **高**（修复取消语义、withTimeout 语义、ensureActive 语义） | 低（仅增加一个 catch 分支，不影响其他逻辑） |
| **Coroutine.kt 同步原版保持 `catch (e: Throwable)`** | 阅读NG / 阅读Archive | 无 | - |

---

## 八、修复优先级建议

### 8.1 P0（立即修复，影响核心功能）

1. **[4.1] Coroutine.kt:182** 增加 `catch (e: CancellationException) { throw e }` —— 修复协程取消语义，影响所有使用 `Coroutine.async` 的场景
   - 修复方式：参考蛋蛋Max 实现
   - 风险：极低
   - 影响范围：所有 `Coroutine.async` 调用（ReadBook 章节加载、CacheBook 下载、WebBook 搜索等）

2. **[4.2] BookSourceExtensions.kt:27** `hashMapOf` 改为 `ConcurrentHashMap`，`?: Mutex().apply { ... }` 改为 `computeIfAbsent`
   - 修复方式：`private val mutexMap by lazy { ConcurrentHashMap<String, Mutex>() }` + `mutexMap.computeIfAbsent(bookSourceUrl) { Mutex() }`
   - 风险：极低
   - 影响范围：书源发现页加载

### 8.2 P1（尽快修复，影响稳定性）

3. **[4.3] MainViewModel.kt:148** `waitUpTocBooks` 改为 `ConcurrentLinkedQueue`
   - 修复方式：`private val waitUpTocBooks = ConcurrentLinkedQueue<String>()`
   - 风险：低（`poll()`/`add()` API 兼容）
   - 影响范围：书架刷新

4. **[4.4] CacheBook.kt:190-191** `successDownloadSet`/`errorDownloadMap` 改为并发集合，或在 `downloadSummary` getter 加锁
   - 修复方式：`successDownloadSet = ConcurrentHashMap.newKeySet<String>()` + `errorDownloadMap = ConcurrentHashMap<String, AtomicInteger>()`
   - 风险：低
   - 影响范围：缓存下载进度显示

5. **[4.8] CacheBook.kt:117** `close()` 加 `@Synchronized`
   - 修复方式：`@Synchronized fun close() { ... }`
   - 风险：极低
   - 影响范围：缓存书籍关闭

6. **[4.5] BookHelp.kt:261** 调整 `downloadImages.remove(src)` 时机
   - 修复方式：移到 `mutex.unlock()` 之后
   - 风险：低
   - 影响范围：图片下载

### 8.3 P2（性能优化）

7. **[5.1] CheckSourceService.kt:112,132** `runBlocking(IO)` 改为 `withContext(IO)`
   - 风险：中（需改为 suspend）
   - 影响范围：书源校验

8. **[5.2] BookHelp.kt:275,280** `@Synchronized writeImage/isImageExist` 改为按书籍锁
   - 风险：中
   - 影响范围：漫画下载

9. **[5.8] BookHelp.kt:136,192** `runBlocking(IO)` 改为 `withContext(IO)`，`clearComicCache` 改为 suspend
   - 风险：低
   - 影响范围：缓存清理

10. **[6.8] AudioPlay.kt:90,111,112,144,257** `runBlocking(IO)` 改为 `withContext(IO)`
    - 风险：中（需改为 suspend）
    - 影响范围：音频播放

### 8.4 P3（设计改进）

11. **[6.2] ReadBook.kt:63-83** 核心状态字段加 `@Volatile`
12. **[6.3] ReadBook.kt:700,775** `chapterLoadingJobs` 复合操作加锁
13. **[6.4] MainViewModel.kt:91** `upTocPool.close()` 等待任务完成
14. **[4.6] Coroutine.kt:37** `DEFAULT = MainScope()` 改为可控 scope

---

## 九、附录

### 9.1 关键文件路径汇总

| 类别 | 文件绝对路径 |
|------|-------------|
| 协程核心 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\coroutine\Coroutine.kt` |
| 组合协程 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\coroutine\CompositeCoroutine.kt` |
| 协程容器 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\coroutine\CoroutineContainer.kt` |
| 取消异常 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\coroutine\ActivelyCancelException.kt` |
| Flow 扩展 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\utils\FlowExtensions.kt` |
| 限流器 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\ConcurrentRateLimiter.kt` |
| 章节缓存 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\CacheBook.kt` |
| 全局执行器 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\ExecutorService.kt` |
| 调度监控 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\DispatchersMonitor.kt` |
| 缓存服务 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\CacheBookService.kt` |
| 校验服务 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\CheckSourceService.kt` |
| 主界面 VM | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\main\MainViewModel.kt` |
| 书籍帮助 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\book\BookHelp.kt` |
| 书源扩展 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\source\BookSourceExtensions.kt` |
| WebView 池 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\webView\WebViewPool.kt` |
| 阅读模型 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\ReadBook.kt` |
| 在线朗读 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\HttpReadAloudService.kt` |
| 日志 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\constant\AppLog.kt` |
| 意图数据 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\IntentData.kt` |
| 常量 | `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\constant\AppConst.kt` |

### 9.2 统计数据

- **多线程相关文件**：协程封装 4 + 线程池使用 10 + 锁使用 40+ + 并发集合使用 25+ = **80+ 文件**
- **@Synchronized / synchronized 块**：120+ 处
- **Mutex 使用**：9 处
- **ReentrantLock 使用**：2 处
- **ConcurrentHashMap 使用**：20+ 处
- **CopyOnWriteArrayList / ArraySet 使用**：4 处
- **AtomicXxx 使用**：5 处
- **runBlocking 使用**：100+ 处（其中性能问题 20+ 处）
- **明确 Bug**：8 个（P0: 2, P1: 4, P2: 2）
- **性能问题**：11 个
- **稳定性问题**：8 个

### 9.3 延伸版本获取状态

| 版本 | 仓库 | Coroutine.kt | ConcurrentRateLimiter.kt |
|------|------|--------------|--------------------------|
| 蛋蛋Max | DandanLLab/Legado_Max | 成功（已修复 CancellationException） | 成功（与本项目相同） |
| 阅读NG | joestar817/legado_NG | 成功（未修复） | 未获取 |
| 阅读Archive | Rimchars/legado | 成功（未修复） | 未获取 |
| 喵公子 | LegadoTeam/legado | 失败（仓库不存在） | - |
| 阅读T | skybbk1001/legadoT | 失败（仓库不存在） | - |
| 辞晨Max | GEd520/legados | 失败（仓库不存在） | - |

---

**分析完毕。** 核心结论：本项目协程封装存在 **CancellationException 处理 Bug**（4.1），蛋蛋Max 已修复可借鉴；`BookSourceExtensions` 的 `mutexMap` 是明确的线程安全 Bug；`CacheBook` 的 `downloadSummary` 与普通集合并发访问有崩溃风险；`CheckSourceService` 在协程中 `runBlocking` 是性能瓶颈。
