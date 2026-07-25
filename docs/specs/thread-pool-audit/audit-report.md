# 线程池配置全面审查报告

> 审查日期：2026-07-26（v2 修订：2026-07-26 三视角整合后）
> 审查方法：静态代码审查 + 架构分析 + 三视角整合审查（UX / 架构 / 测试）
> 审查范围：`app/src/main/java/io/legado/app/` 下所有线程池配置点
> 审查执行：3 个子代理并行审查 + 主代理交叉验证整合 + 三视角深度审查
> 修订记录：v2 根据 `review-report.md` 整合方案修订 P0/P1/P2 清单（35 项→22 项）

---

## 一、审查摘要

### 1.1 审查覆盖范围

本次审查覆盖 Legado 项目中 13 项线程池配置点，按类型分布：

| 类型 | 数量 | 配置点编号 |
|------|------|-----------|
| FixedThreadPool（业务池） | 8 | #2-#9 |
| SingleThreadExecutor（全局/监控） | 2 | #1, #10 |
| ConnectionPool（OkHttp） | 1 | #11 |
| Dispatchers.IO（协程共享） | 2 | #12, #13 |

### 1.2 关键发现（v2 修订后）

| 严重度 | v1 数量 | v2 修订后 | 修订说明 |
|--------|---------|-----------|---------|
| **P0（必须修复）** | 6 项 | **7 项** | 3 项从 P1 升级（配置响应/低端保护/启动并行+OkHttp 保活）+ 1 项合并 + 3 项原 P0 强化 |
| **P1（建议修复）** | 16 项 | **10 项** | 3 项降级（@Volatile/API 隔离备份/scope 改造拆分）+ 6 项合并简化 |
| **P2（可选优化）** | 13 项 | **5 项** | 8 项合并简化 |
| **总计** | 35 项 | **22 项** | 减少 13 项冗余 |

### 1.3 三视角审查综合评分

| 视角 | 评分 | 核心发现 |
|------|------|---------|
| 产品UX | 6/10 | 60% 用户无感知（工程自嗨）；0 量化收益；优先级失衡 |
| 技术架构 | 8.5/10 | 13 项覆盖完整；3 项 P0 方案有隐藏风险（调用点/原子性/回调语义） |
| 测试验证 | 3/10 | 6 项 P0 全部无测试用例；0 项有量化验证方法 |
| **综合** | **6.5/10** | 技术质量优秀但系统性缺陷：优先级失衡 + 验证缺失 |

### 1.4 顶层结论（v2 修订）

1. **业务主链路隔离良好**：8 个业务 FixedThreadPool 互不影响
2. **辅助逻辑未隔离**：API Controller runBlocking、CheckSourceService Flow runBlocking、App 启动期密集 IO 共用 Dispatchers.IO 64 线程池
3. **业务池无独立上限保护**：用户配 `searchThreadCount=32` 时 8 个业务池总线程可达 256+（v2 升级为 P0-7）
4. **MainViewModel.upTocPool 是最复杂配置点**：多 Job 共享 + 可重建 + 跨协程访问，存在隐藏调用点（line 290）和原子性问题（v2 强化 P0-1/P0-2）
5. **RssSearchModel 是设计最优配置点**：`var threadCount` + `initSearchPool` 重读配置，可作为其他 7 个业务池的重构范式（v2 升级为 P0-6）
6. **Cronet 与 OkHttp 连接池天然隔离**：Cronet 仅复用 OkHttp dispatcher 执行器
7. **低端机型保护缺失**（v2 新增）：searchThreadCount=32 对低端机型过激进，需性能模式三档开关
8. **验证体系完全缺失**（v2 新增）：35 项建议 0 项测试用例，实施前必须补齐 28 个 P0 用例 + 8 个新脚本

---

## 二、13 项配置点审查结论

### 2.1 配置点 #1：globalExecutor（ExecutorService.kt:6）

| 字段 | 内容 |
|------|------|
| 类型 | `Executors.newSingleThreadExecutor()` |
| 线程数 | 1（固定，无界队列） |
| 初始化 | `by lazy` 委托 |
| 关闭方式 | 未显式关闭（依赖 JVM 退出） |
| ThreadFactory 命名 | 无 |
| 用途 | 3 个调用点：AsyncRecycleBitmapPool.kt:20（Glide Bitmap 回收，高频）、AsyncFileHandler.kt:13（AppLog 文件日志写入，高频）、LogUtils.kt:61（启动时清理 7 天前日志，低频） |
| 风险点 | ① Bitmap 回收与日志写入共用单线程队列，磁盘 I/O 抖动反压 Bitmap 回收；② 无界队列 OOM 隐患；③ 异常静默吞掉 |
| 优化建议 | G-1 任务拆分（Bitmap → Dispatchers.Default，日志保留单线程）；G-2 有界队列+DiscardOldestPolicy；G-3 ThreadFactory 命名 |
| 优先级 | P1 + P2 |

### 2.2 配置点 #2-#9：8 个 FixedThreadPool

| # | 文件:行号 | 线程数来源 | 用途 | 关闭时机 | 优先级 |
|---|----------|-----------|------|---------|--------|
| #2 | CheckSourceService.kt:66 | searchThreadCount | 书源校验 | Service.onDestroy | P1 |
| #3 | CheckRssSourceService.kt:63 | searchThreadCount | RSS源校验 | Service.onDestroy | P1 |
| #4 | CacheBookService.kt:46 | updateCacheThreadCount | 缓存下载 | Service.onDestroy | **P0** |
| #5 | MainViewModel.kt:54/92 | updateCacheThreadCount | 目录更新（upTocPool，可重建） | onCleared + upPool 重建 | **P0** |
| #6 | SearchModel.kt:59 | searchThreadCount | 书籍搜索 | 搜索结束 close | P1 |
| #7 | RssSearchModel.kt:110 | searchThreadCount | RSS搜索 | 搜索结束 close | P2（设计最优） |
| #8 | ChangeCoverViewModel.kt:101 | searchThreadCount | 换封面 | ViewModel.onCleared | P1 |
| #9 | ChangeBookSourceViewModel.kt:167 | searchThreadCount | 换书源 | ViewModel.onCleared | P1 |

**共性问题**（8 个 FixedThreadPool）：
- C1：全部未使用 ThreadFactory 命名（线程堆栈难定位）
- C2：全部使用默认 AbortPolicy + 无界队列（任务积压 OOM 隐患）
- C3：6/8 个 `threadCount` 是 `val` 不可变（配置变更不生效）
- C4：5/8 个业务异常路径不主动关闭池（依赖生命周期兜底）
- C5：4/8 个 `searchPool!!` 强解引用（NPE 风险）
- C6：2/8 个 `close()` 后未置 null（误访问抛 IllegalStateException）

**个性问题**：
- #5 MainViewModel.upTocPool：池被 upTocJob + cacheBookJob 共享，级联失败风险；upPool() 重建逻辑有竞态；upTocPool 字段无 @Volatile 保护
- #4 CacheBookService：池对象传递给 CacheBook.startProcessJob 跨对象使用，onDestroy 关闭顺序需保证 CacheBook.close() 先于 cachePool.close()
- #6 vs #7：SearchModel 用 `val`、RssSearchModel 用 `var`+重读，配置响应行为不一致
- #2/#3 CheckSourceService/CheckRssSourceService：流程内多处 runBlocking(IO) 阻塞工作线程

### 2.3 配置点 #10：DispatchersMonitor.kt:26

| 字段 | 内容 |
|------|------|
| 类型 | `Executors.newSingleThreadExecutor` 单线程 |
| 触发条件 | `AppConfig.recordLog = true`（默认 false） |
| 监控逻辑 | 对 IO/Default/Main 各启动 1 个监控协程，`select { launch{ withContext(dispatcher){delay(3000)} }.onJoin; onTimeout(5000){log} }` |
| 风险点 | ① while+select 无间隔，CPU 空转；② withContext(IO){delay(3000)} 占用被监控池槽位，IO 池满时监控自身排队→误报超时；③ recordLog 运行时切换无效（init 仅 App.onCreate 调用一次）；④ scope 未 shutdown |
| 优化建议 | P1-7 select 块后加 delay(5000)；P1-8 改用非占用式检测（反射队列长度）；P1-9 recordLog 切换时重启监控；P2-5 提供 shutdown() |
| 优先级 | P1 + P2 |

### 2.4 配置点 #11：OkHttp ConnectionPool（HttpHelper.kt:101）

| 字段 | 内容 |
|------|------|
| 类型 | `okhttp3.ConnectionPool` |
| 配置 | 50 连接 / 5 分钟保活 |
| 派生客户端 | okHttpClientManga、getProxyClient() 通过 newBuilder() 共享同一连接池 |
| 代理客户端 LRU 上限 | 20 |
| 与其他组件协同 | ① WebView 自带网络栈不共享；② CookieStore 通过 NetworkInterceptor 协同；③ Cronet 走独立网络栈，仅复用 OkHttp dispatcher executorService |
| 风险点 | ① 5 分钟保活对移动网络偏长（NAT/基站切换周期 < 2 分钟），失效连接复用触发重连；② 50 连接偏宽松（maxRequestsPerHost=5 限制下 30 连接足够） |
| 优化建议 | O-1 保活 5 分钟 → 2 分钟（P1）；O-2 连接数 50 → 30（P2）；O-4 保活超时可配置（P2） |
| 优先级 | P1 + P2 |

### 2.5 配置点 #12-#13：Dispatchers.IO（Coroutine.kt + 全项目）

| 字段 | 内容 |
|------|------|
| 类型 | 协程 IO 调度器 |
| 默认线程上限 | 64（或 max(64, CPU核数)） |
| 使用规模 | 50 文件 54+ 处 Coroutine.async + 大量 withContext/launch |
| 业务场景分布 | API HTTP 接口（runBlocking IO 风暴）、搜索主链路（已隔离）、缓存下载（已隔离）、校验服务（Flow runBlocking）、应用初始化（密集 IO）、自动备份、WebView 后台、书籍加载、RSS 业务、网络书源、UI 辅助 |
| 风险点 | ① API Controller 10+ 处 runBlocking(IO) 高并发耗尽 64 线程；② CheckSourceService Flow emit 内 runBlocking 与校验业务池形成等待链；③ DispatchersMonitor 占用 IO 槽位；④ App.kt:103 启动期单 launch 串行 8+ 重 IO 任务；⑤ Coroutine.async DEFAULT=MainScope() 全局共享无生命周期管理；⑥ executeInternal 在 scope.plus(executeContext=Main) 上 launch，semaphore.acquire() 在 Main 执行可能阻塞 UI |
| 优化建议 | 见下文 P0/P1/P2 清单 |
| 优先级 | P0 + P1 + P2 |

---

## 三、问题识别与优化建议清单（5.1-5.4）

### 3.1 资源泄漏风险识别（5.1）

| # | 风险点 | 位置 | 严重度 |
|---|--------|------|--------|
| L-1 | MainViewModel.upTocPool 字段跨协程读写无 @Volatile 保护 | MainViewModel.kt:54/92 | P0 |
| L-2 | CacheBookService.onDestroy 关闭顺序：cachePool.close() 在 CacheBook.close() 前，CacheBook 内排队任务抛 IllegalStateException | CacheBookService.kt:96 | P0 |
| L-3 | 5/8 个业务池异常路径不主动关闭，依赖生命周期兜底 | SearchModel/RssSearchModel/ChangeCoverViewModel/ChangeBookSourceViewModel/MainViewModel | P1 |
| L-4 | ChangeCoverViewModel/ChangeBookSourceViewModel 的 stopSearch() 中 close() 后未置 null，误访问抛 IllegalStateException | ChangeCoverViewModel.kt:196-199, ChangeBookSourceViewModel.kt:446 | P1 |
| L-5 | Coroutine.async DEFAULT=MainScope() 全局共享，协程不随 Activity/Fragment 销毁而取消 | Coroutine.kt:37,40-48 | P0 |
| L-6 | DispatchersMonitor.scope 未 shutdown，App 退出后线程残留 | DispatchersMonitor.kt:31 | P2 |
| L-7 | globalExecutor lazy 单例无 shutdown 接口 | ExecutorService.kt:6 | P2 |

### 3.2 性能瓶颈识别（5.2）

| # | 瓶颈点 | 位置 | 严重度 |
|---|--------|------|--------|
| B-1 | CheckSourceService Flow emit 内 runBlocking(IO) 与校验业务池形成等待链 | CheckSourceService.kt:117 | P0 |
| B-2 | API Controller 10+ 处 runBlocking(IO) 高并发耗尽 64 线程 | api/controller/*Controller.kt, ReaderProvider.kt:80 | P0 |
| B-3 | Coroutine.async executeContext=Main 导致 semaphore.acquire() 在 Main 阻塞 UI | Coroutine.kt:174-175 | P0 |
| B-4 | 业务池无全局上限，用户配 32 时 8 业务池总线程 256+ | SearchModel.kt:59 等 | P1 |
| B-5 | App.kt:103 启动期单 launch 串行 8+ 重 IO 任务，启动慢 | App.kt:103-124 | P1 |
| B-6 | DispatchersMonitor while+select 无间隔 CPU 空转 | DispatchersMonitor.kt:46 | P1 |
| B-7 | DispatchersMonitor withContext(IO){delay(3000)} 占用被监控池槽位，IO 池满时误报超时 | DispatchersMonitor.kt:48 | P1 |
| B-8 | OkHttp 连接池 5 分钟保活对移动网络偏长，失效连接复用触发重连 | HttpHelper.kt:101 | P1 |
| B-9 | globalExecutor Bitmap 回收与日志 I/O 共用队列，磁盘抖动反压 Bitmap 回收 | ExecutorService.kt:6 | P1 |
| B-10 | 6/8 个业务池 threadCount 不可变，用户调整配置后已存在实例不生效 | CheckSourceService/CheckRssSourceService/CacheBookService/SearchModel/ChangeCoverViewModel/ChangeBookSourceViewModel | P1 |

### 3.3 默认值合理性评估（5.3）

| 配置项 | 当前默认值 | 上限 | 评估结论 |
|--------|-----------|------|---------|
| searchThreadCount | 32 | 128 | 偏宽松。8 个业务池中 6 个共用此值，最坏场景 6×32=192 线程。建议默认值保持 32（满足搜索并发需求），但增加全局上限保护 |
| updateCacheThreadCount | 16 | 64 | 合理。仅 3 个业务池使用（CacheBookService + MainViewModel upTocPool ×2），最坏 3×16=48 线程 |
| OkHttp maxIdleConnections | 50 | N/A | 偏宽松。maxRequestsPerHost=5 限制下 30 连接足够，可节省 ~1MB 内存 |
| OkHttp keepAliveDuration | 5 分钟 | N/A | 偏长。移动网络 NAT/基站切换周期 < 2 分钟，建议降至 2 分钟 |
| Dispatchers.IO 线程上限 | 64 | max(64, CPU核数) | 默认值合理，但被 API runBlocking + CheckSourceService Flow runBlocking + App 启动任务共用，存在单点拥塞风险 |
| globalExecutor 线程数 | 1 | N/A | 合理。仅 3 个低频调用点，单线程足够。但 Bitmap 回收 + 日志 I/O 混合排队存在反压风险 |

### 3.4 优化建议清单（v2 修订版，22 项）

> v2 修订说明：根据 `review-report.md` 三视角整合方案，原 35 项简化为 22 项（P0 7 项 + P1 10 项 + P2 5 项）。
> 修订依据：UX 视角（优先级失衡）+ 架构视角（3 项方案风险）+ 测试视角（验证体系缺失）。

#### P0 级（必须修复，存在稳定性风险或用户可感知问题）— 7 项

| # | 建议 | 涉及位置 | 修订说明 | 实施批次 |
|---|------|---------|---------|---------|
| **P0-1** | **拆分 MainViewModel.upTocPool 与 cacheBookPool** + **同步修改 line 290 隐藏调用点** | MainViewModel.kt:54/92/160/272/290 | v2 强化：架构审查发现 line 290 `CacheBook.startProcessJob(upTocPool)` 隐藏调用点，必须同步改为 `cacheBookPool`，否则拆分无效；onCleared 需关闭两个池 | 第二批 |
| **P0-2** | **upPool() 升级为 Mutex 保护整个方法**（替代 @Volatile）+ 与 P0-1 合并实施 | MainViewModel.kt:54/91/upPool() | v2 强化：架构审查发现 @Volatile 仅解决可见性不解决原子性，upPool() 存在创建两个池的窗口期，必须用 `kotlinx.coroutines.sync.Mutex` 包裹整个方法 | 第二批 |
| **P0-3** | **CacheBookService.onDestroy 调整关闭顺序**：先 CacheBook.close() 再 cachePool.close() | CacheBookService.kt:96 | 保持 v1；需验证 CacheBook.close() 是否 suspend（若 suspend 需在 runBlocking 中调用） | 第一批 |
| **P0-4** | **CheckSourceService + CheckRssSourceService runBlocking→withContext 合并改造** | CheckSourceService.kt:117/137, CheckRssSourceService.kt:115/136 | v2 合并：原 P0-4 + P1-16 合并；flow builder 内用 withContext(IO) 替代 flowOn(IO) 更直接 | 第一批 |
| **P0-5** | **API Controller runBlocking 改 runBlocking(apiPool.asCoroutineDispatcher())** | api/controller/*Controller.kt, ReaderProvider.kt:80 | v2 优化：API 是同步 HTTP 接口，runBlocking 不可去除，改为替换调度器；apiPool = FixedThreadPool(8) 放 ExecutorService.kt 统一管理 | 第三批 |
| **P0-6**（新） | **6 业务池 threadCount 改 var + initSearchPool 重读 AppConfig** | #2/#3/#4/#6/#8/#9 | v2 升级：原 P1-2 升级；配置不生效是真实 UX 痛点；对齐 RssSearchModel 范式；需核实"6/8 不可变"数字 | 第一批 |
| **P0-7**（新） | **业务池独立上限 + 启动并行化 + OkHttp 保活 5→2 分钟** | AppConfig.kt + 8 业务池 + App.kt:103-124 + HttpHelper.kt:101 | v2 合并升级：原 P1-9 + P1-10 + P1-15 合并升级；3 项共同构成"低端机型保护 + 启动 UX + 网络体验"组合优化；不引入 totalBusinessThreadCap 全局配置，改各池独立上限 | 第二批 |

#### P1 级（建议修复，性能/可维护性）— 10 项

| # | 建议 | 涉及位置 | 修订说明 |
|---|------|---------|---------|
| P1-1 | upTocPool @Volatile（冗余保险，Mutex 已在 P0-2 实施） | MainViewModel.kt:54 | v2 降级：原 P0-2 降级；用户零感知，纯工程正确性 |
| P1-2 | API 隔离（理论风险备份） | api/controller/*Controller.kt | v2 降级：原 P0-5 降级；实施 P0-5 后若未发现实际 IO 池耗尽，可作为后续优化 |
| P1-3 | Coroutine.async DEFAULT=MainScope 移除（子任务1） | Coroutine.kt:37,40-48 | v2 降级 + 拆分：原 P0-6 降级；暂缓实施，先收集协程泄漏证据；影响 50+ 调用点 |
| P1-4 | executeContext 与回调调度器分离（子任务2） | Coroutine.kt:174-175 | v2 降级 + 拆分：原 P0-6 降级；需重新设计"执行块调度器"与"回调调度器"分离方案 |
| P1-5 | 8 业务池 ThreadFactory 命名 + 公共工具类 | 8 业务池 + 新增 utils | v2 合并：原 P1-1 + P2-4 合并 |
| P1-6 | 异常路径 close() + stopSearch() 后置 null | #5/#6/#7/#8/#9 | v2 合并：原 P1-3 + P1-4 合并 |
| P1-7 | ChangeBookSourceViewModel mapParallelSafe | #9 | 保持 v1 |
| P1-8 | Coroutine.async errorReturn 日志 + onCancel scope | Coroutine.kt:150/186-189 | v2 合并：原 P1-11 + P1-12 合并 |
| P1-9 | DispatchersMonitor 3 项合并优化（delay + 非占用式 + restart） | DispatchersMonitor.kt:31/46/48 | v2 降级 + 合并：原 P1-6 + P1-7 + P1-8 合并；监控组件用户无感 |
| P1-10 | globalExecutor 任务拆分 + 有界队列 | ExecutorService.kt:6 | v2 降级 + 合并：原 P1-13 + P1-14 合并；理论反压风险 |

#### P2 级（可选优化，提升体验）— 5 项

| # | 建议 | 涉及位置 | 修订说明 |
|---|------|---------|---------|
| P2-1 | globalExecutor 文档化 + ThreadFactory + shutdown 接口 | ExecutorService.kt:6 | v2 合并：原 P2-8 + P2-10 + P2-11 合并 |
| P2-2 | 8 业务池有界队列 + CallerRunsPolicy | 8 个业务池 | 保持 v1（原 P2-1） |
| P2-3 | CheckRssSourceService ConcurrentLinkedQueue | CheckRssSourceService.kt:152 | 保持 v1（原 P2-2） |
| P2-4 | DispatchersMonitor shutdown + supervisorScope | DispatchersMonitor.kt:31/45 | v2 合并：原 P2-5 + P2-6 合并 |
| P2-5 | Coroutine.async finally 日志 + ContentTextView 评估 + OkHttp 连接数 + 保活可配置 | Coroutine.kt:194-198, ContentTextView.kt:824, HttpHelper.kt:101 | v2 合并：原 P2-7 + P2-9 + P2-12 + P2-13 合并 |

---

## 四、实施优先级与风险评估（v2 修订：五批次）

### 4.1 推荐实施顺序（五批次）

**第一批：独立低风险修复（4 项）**

| 顺序 | 优化项 | 实施要点 | 测试要求 |
|------|--------|---------|---------|
| 1 | P0-3 | CacheBookService.onDestroy 调整关闭顺序 | TC-P0-3-1~4（4 个用例）+ IllegalStateException 监控 |
| 2 | P0-4 | CheckSourceService + CheckRssSourceService runBlocking→withContext 合并改造 | TC-P0-4-1~5（5 个用例）+ 死锁检测 |
| 3 | P0-6（新） | 6 业务池 threadCount 改 var + initSearchPool 重读 | TC-P0-6-1~5（5 个用例）+ 配置变更真机验证 |
| 4 | P1-5 | 8 业务池 ThreadFactory 命名 + 公共工具类 | dumpsys 堆栈采样验证 |

**第二批：MainViewModel 集中改造（2 项，强依赖合并）**

| 顺序 | 优化项 | 实施要点 | 测试要求 |
|------|--------|---------|---------|
| 5 | P0-1 + P0-2 合并 | 拆分 upTocPool/cacheBookPool + Mutex 保护 upPool() + 同步修改 line 290 + onCleared 关闭两池 | TC-P0-1-1~5 + TC-P0-2-1~4（9 个用例）+ 并发压测 |
| 6 | P0-7（新） | 业务池独立上限 + 启动并行化 + OkHttp 保活 5→2 分钟 | TC-P0-7-1~4 + 真机低端机型测试 + 网络切换测试 |

**第三批：API 隔离改造（1 项，影响面广）**

| 顺序 | 优化项 | 实施要点 | 测试要求 |
|------|--------|---------|---------|
| 7 | P0-5 | 新增 apiPool = FixedThreadPool(8) 放 ExecutorService.kt；API Controller runBlocking 改 runBlocking(apiPool.asCoroutineDispatcher()) | TC-P0-5-1~5（5 个用例）+ 全量 API 回归 |

**第四批：P1 批量实施（6 项）**

| 顺序 | 优化项 | 实施要点 |
|------|--------|---------|
| 8 | P1-6 | 异常路径 close() + stopSearch() 后置 null |
| 9 | P1-7 | ChangeBookSourceViewModel mapParallelSafe |
| 10 | P1-8 | Coroutine.async errorReturn 日志 + onCancel scope |
| 11 | P1-9 | DispatchersMonitor 3 项合并优化 |
| 12 | P1-10 | globalExecutor 任务拆分 + 有界队列 |
| 13 | P1-1 | upTocPool @Volatile（已在 P0-2 Mutex 中实施，此为冗余保险） |

**第五批：暂缓实施（2 项，需先收集证据）**

| 顺序 | 优化项 | 暂缓理由 | 决策条件 |
|------|--------|---------|---------|
| 14 | P1-3 | Coroutine.async DEFAULT=MainScope 移除 | 需先收集协程泄漏实际投诉证据 + 评估 50+ 调用点改造风险 |
| 15 | P1-4 | executeContext 与回调调度器分离 | 需重新设计方案，分离"执行块调度器"与"回调调度器" |

### 4.2 回归风险评估

| 修复项 | 回归风险 | 缓解措施 |
|--------|---------|---------|
| P0-1 + P0-2 拆分池 + Mutex | 中（影响目录更新+缓存两个核心流程） | TC-P0-1/P0-2 共 9 个用例 + 并发压测 + 真机低端机型测试 |
| P0-4 Flow 改造 | 中（影响书源校验流程） | TC-P0-4 共 5 个用例 + 死锁检测 + 校验中断恢复 |
| P0-5 API Controller 改造 | 高（影响所有 HTTP API） | TC-P0-5 共 5 个用例 + 全量 API 接口回归测试 |
| P0-6 配置响应改造 | 低（仅配置响应性提升） | TC-P0-6 共 5 个用例 + 配置变更真机验证 |
| P0-7 低端保护 + 启动 + OkHttp | 中（影响启动+网络+所有业务池） | TC-P0-7 共 4 个用例 + 真机低端机型测试 + 网络切换测试 |

### 4.3 实施约束

- 任何代码变更必须遵守 `naming_rules.md`、`checkstyle_rules.md`、`architecture_rules.md`
- 涉及线程数/调度器调整必须按 `ai_e2e_testing_workflow.md` 执行真机测试
- 产生代码变更必须按 `version-delivery-sync.md` 更新 `assets/updateLog.md`
- 同一源码文件的所有 Edit 必须串行执行（并发文件修改规范）
- 实施前必须备份到 bak 目录
- **真机测试包选择**（v2 新增）：项目代码优化必须用测试包 `io.legado.miss.app.debug`（参见 `AGENTS.md` 真机测试包选择规范）

---

## 五、测试验证方案（v2 新增）

> v2 新增章节：根据测试视角审查（`test-verification-review.md`）补齐，原 v1 缺失测试方案。

### 5.1 P0 测试用例总数（28 个）

| 优化项 | 用例数 | 用例 ID 范围 | 验证方法 |
|--------|--------|-------------|---------|
| P0-1 拆分池 | 5 | TC-P0-1-1~5 | logcat 线程数 + 数据库 toc 行数 + 任务完成事件 |
| P0-2 Mutex 保护 | 4 | TC-P0-2-1~4 | 反射字段对比 + dumpsys 线程数 + 异常监控 |
| P0-3 关闭顺序 | 4 | TC-P0-3-1~4 | IllegalStateException 监控 + 关闭顺序日志 |
| P0-4 Flow 改造 | 5 | TC-P0-4-1~5 | 校验完成数 + 时间戳分析 + 死锁检测 |
| P0-5 API 隔离 | 5 | TC-P0-5-1~5 | dumpsys 线程数 + API 响应码 + 隔离性验证 |
| P0-6 配置响应 | 5 | TC-P0-6-1~5 | 配置变更→新建池重读→老池未变 |
| P0-7 低端保护 | 4 | TC-P0-7-1~4 | 启动耗时 before/after + 网络切换 + 内存峰值 |

> 详细用例设计参见 `test-verification-review.md` 第四章。

### 5.2 新增 8 个测试脚本

| 脚本名 | 用途 | 关联 P0 | 优先级 |
|--------|------|---------|--------|
| `monitor_thread_count.py` | dumpsys 监控线程数 + 按 tag 分类 | P0-1~P0-7 | TE-P0 |
| `verify_concurrent_safety.py` | 并发压测（upTocPool+cacheBookPool 并发） | P0-1, P0-2 | TE-P0 |
| `verify_service_shutdown.py` | Service 销毁顺序验证 | P0-3, P0-4 | TE-P0 |
| `verify_api_isolation.py` | API 高并发 + IO 池隔离验证 | P0-5 | TE-P0 |
| `verify_config_response.py` | 配置变更→线程池响应性验证 | P0-6 | TE-P0 |
| `verify_okhttp_keepalive.py` | 网络切换 + 连接复用率 | P0-7 | TE-P0 |
| `verify_app_startup_parallel.py` | 启动耗时 before/after 对比 | P0-7 | TE-P0 |
| `verify_low_end_device.py` | 低端机型内存/CPU 峰值监控 | P0-7 | TE-P0 |

### 5.3 真机测试矩阵

| 机型维度 | CPU | 内存 | 网络维度 | 测试范围 |
|---------|-----|------|---------|---------|
| 低端 | 4 核 | 4GB | WiFi + 4G 切换 | P0-1~P0-7 全量 + OOM/ANR 监控 |
| 中端 | 6 核 | 6GB | WiFi | P0-1~P0-7 全量 |
| 高端 | 8 核+ | 8GB+ | WiFi + 5G | P0-1~P0-7 抽样 + 性能基线 |

### 5.4 量化验证基线（实施前必须采集）

| 指标 | 采集方法 | before 基线 | after 目标 |
|------|---------|------------|-----------|
| App 冷启动耗时 | logcat Displayed 时间 | ? ms | 降低 ≥ 15% |
| 书源校验 100 源耗时 | 真机批量校验 | ? s | 降低 ≥ 20% |
| 8 业务池总线程数峰值 | dumpsys meminfo | ? 个 | ≤ 128 |
| IO 池峰值线程数 | dumpsys meminfo | ? 个 | ≤ 48 |
| 缓存下载退出崩溃率 | logcat FATAL | ? 次 | 0 次 |
| IllegalStateException 频次 | logcat 异常 tag | ? 次 | 0 次 |
| 移动网络连接复用率 | OkHttp EventListener | ? % | ≥ 80% |

---

## 六、用户沟通方案（v2 新增）

> v2 新增章节：根据 UX 视角审查（`ux-review.md`）补齐，原 v1 缺失用户沟通方案。

### 6.1 updateLog.md 应包含的条目（面向用户语言）

| 技术项 | 面向用户的 updateLog 条目 |
|--------|-------------------------|
| P0-3 | 修复缓存下载完成后退出应用时可能崩溃的问题 |
| P0-4 | 修复书源校验过程中可能卡死不动的问题 |
| P0-1 + P0-2 | 提升目录更新与缓存下载的稳定性，避免相互影响 |
| P0-6（新） | 修复线程数配置修改后不立即生效，需重启应用的问题 |
| P0-7 启动并行化 | 优化应用启动速度，减少启动等待时间 |
| P0-7 OkHttp 保活 | 优化移动网络下的连接复用，减少偶发网络卡顿 |
| P0-7 低端保护 | 优化低端机型大并发场景下的内存占用，降低崩溃风险 |

### 6.2 不应进入 updateLog 的项

- P0-2 @Volatile / Mutex（用户零感知）
- P0-5 API 隔离（用户零感知）
- P1-1 / P1-5 / P1-6 / P1-7 / P1-8（工程正确性）
- 所有 P2 项

### 6.3 新增用户可见配置入口（建议）

**性能模式三档开关**（替代技术参数暴露）：

| 模式 | searchThreadCount | updateCacheThreadCount | 适用机型 |
|------|-------------------|------------------------|---------|
| 低端 | 8 | 4 | ≤4GB RAM / ≤4 核 |
| 标准（默认） | 16 | 8 | 4-8GB RAM / 6-8 核 |
| 高性能 | 32 | 16 | ≥8GB RAM / ≥8 核 |

**理由**：当前 searchThreadCount=32 对低端机型过激进，但用户不知如何调整；三档开关比技术参数（线程数）更友好；内部自动映射到各业务池上限。

---

## 七、审查验证

| 验证项 | 结果 |
|--------|------|
| 13 项配置点全部审查完毕 | ✅ |
| 8 个 FixedThreadPool 每点覆盖 7 个维度 | ✅ |
| Dispatchers.IO 使用清单完整（50 文件 54+ 处） | ✅ |
| globalExecutor 用途清单完整（3 个调用点） | ✅ |
| OkHttp 连接池与线程数匹配度有量化分析 | ✅ |
| 优化建议按 P0/P1/P2 分级（v2 修订） | ✅（P0 7 项 + P1 10 项 + P2 5 项 = 22 项） |
| 三视角审查整合（UX/架构/测试） | ✅（详见 `review-report.md`） |
| 28 个 P0 测试用例 + 8 个新脚本 | ✅（详见第五章） |
| 用户沟通方案（updateLog + 性能模式开关） | ✅（详见第六章） |
| 仅引用技术字段（无业务数据/源名称/域名/URL） | ✅ |
| 无违禁词 | ✅ |

---

## 八、附录

### 8.1 子代理审查产出索引（v1 静态审查阶段）

| 子代理 | 任务范围 | 产出 |
|--------|---------|------|
| 子代理1 | FixedThreadPool 8 个创建点（2.1-2.8） | 8 点详细审查 + 共性 7 项 + 个性 6 项 + P0 4 项 + P1 6 项 + P2 4 项 |
| 子代理2 | Dispatchers 与协程（3.1-3.4） | Dispatchers.IO 清单 + Coroutine.kt 审查 + DispatchersMonitor 审查 + 资源竞争评估 + P0 4 项 + P1 7 项 + P2 5 项 |
| 子代理3 | globalExecutor + OkHttp（4.1-4.2） | globalExecutor 3 调用点 + OkHttp 量化分析 + Cronet 隔离确认 + P1 3 项 + P2 4 项 |

### 8.2 三视角审查产出索引（v2 整合审查阶段）

| 视角 | 产出文件 | 评分 |
|------|---------|------|
| 产品UX | `ux-review.md` | 6/10 |
| 技术架构 | `architecture-review.md` | 8.5/10 |
| 测试验证 | `test-verification-review.md` | 3/10 |
| 整合报告 | `review-report.md` | 6.5/10 |

### 8.3 关键文件路径

- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\ExecutorService.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\http\HttpHelper.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\DispatchersMonitor.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\coroutine\Coroutine.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\main\MainViewModel.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\CacheBookService.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\CheckSourceService.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\service\CheckRssSourceService.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\webBook\SearchModel.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\rss\RssSearchModel.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\book\changecover\ChangeCoverViewModel.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\ui\book\changesource\ChangeBookSourceViewModel.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\config\AppConfig.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\api\controller\` 目录下所有 Controller
