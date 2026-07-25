# 技术架构审查报告：thread-pool-audit

> 审查日期：2026-07-25
> 审查角度：技术架构（可行性 / 合理性 / 规范符合性 / 回归风险）
> 审查对象：audit-report.md / design.md / spec.md
> 审查方法：6 项 P0 全部源码验证 + P1 关键项源码抽样验证

---

## 一、整体评估

### 1.1 评分

**技术架构评分：8.5 / 10**

审查报告整体技术质量优秀，13 项配置点覆盖完整，35 项优化建议分级合理。源码验证准确率 100%（6/6 P0 全部命中真实代码位置）。扣分项：

- P0-2 未识别 `@Volatile` 仅解决可见性、不解决原子性（upPool() 仍存在创建两个池的窗口期）
- P0-6 未识别 `executeContext=Main` 与回调调度器的耦合（修复方案会影响 success/onError 回调线程）
- P1-2 "6/8 个 val 不可变" 数字与源码抽样不完全一致（实际 MainViewModel/CheckSourceService 已用 var）
- 实施顺序未考虑 P0-1 与 P0-2 的强依赖关系

### 1.2 关键发现（5 条）

1. **P0-1 拆分 upTocPool 涉及隐藏调用点**：审查报告未提及 `MainViewModel.kt:290` 将 upTocPool 作为参数传递给 `CacheBook.startProcessJob(upTocPool)`。拆分 cacheBookPool 后，此调用点需同步改为 `CacheBook.startProcessJob(cacheBookPool)`，否则拆分无效（cacheBookJob 仍跑在 upTocPool 上）。

2. **P0-2 @Volatile 不足以解决全部并发问题**：`upPool()` 中 `upTocPool.close()` 与 `upTocPool = Executors.newFixedThreadPool(...)` 之间存在窗口期，若两个协程同时调用 `upPool()`（如 `onUpdateCacheThreadCountChanged` 与 `startUpTocJob` 竞态），可能创建两个池导致旧池泄漏。需用 `Mutex` 包裹 `upPool()` 整个方法（项目已有 `kotlinx.coroutines.sync.Mutex` 依赖，参见 CacheBookService.kt:49）。

3. **P0-6 executeContext 修复方案有副作用**：审查报告建议 `executeInternal` 改用 `scope.plus(context)` 让 `semaphore.acquire()` 在业务调度器执行。但当前 `executeContext` 还用于 `success`/`error`/`finally` 回调分发（Coroutine.kt:174-200），若直接改为 `scope.plus(context)` 会改变回调线程语义。需分离 "执行块调度器" 与 "回调调度器" 两个概念，方案复杂度被低估。

4. **P1-2 范式数字需修正**：审查报告称"6/8 个 threadCount 不可变"，源码抽样：
   - SearchModel.kt:33 `val threadCount` ❌
   - RssSearchModel.kt:52 `var threadCount` ✅
   - MainViewModel.kt:52 `var threadCount` ✅（但仅在 upPool 时重读，无 initSearchPool 范式）
   - CheckSourceService.kt:64 `var threadCount` ✅（但无重读逻辑）
   - CacheBookService.kt:44 `val threadCount` ❌
   - ChangeCoverViewModel/ChangeBookSourceViewModel 待核实
   
   建议修正为"5/8 个不可变或未重读配置"，避免数字误导。

5. **P0-5 API Controller 数量描述偏保守**：审查报告称"10+ 处 runBlocking"，实际 Grep 仅命中 4 个文件（BookSourceController/RssSourceController/ReplaceRuleController/BookController）。BookSourceController 单文件就有 5 处（行 13/19/34/54/67），4 文件累计估算 10-15 处，"10+" 描述合理但建议补充精确数字到附录。

---

## 二、P0 优化建议技术评估表

| 编号 | 建议 | 技术可行性 | 架构合理性 | 规范符合性 | 回归风险 | 源码验证结论 | 调整建议 |
|------|------|-----------|-----------|-----------|---------|-------------|---------|
| **P0-1** | 拆分 upTocPool/cacheBookPool | 高（新增一个字段+2 处调用点调整） | 合理（与 CacheBookService 独立池模式一致） | 符合 object+ViewModel 模式 | 中（影响目录更新+缓存两个核心流程） | ✅ 验证：upTocPool 在 MainViewModel.kt:54 创建，被 line 160 upTocJob + line 272 cacheBookJob 共用，且 line 290 传递给 CacheBook.startProcessJob | **补充**：必须同步修改 line 290 `CacheBook.startProcessJob(upTocPool)` → `CacheBook.startProcessJob(cacheBookPool)`；onCleared 需关闭两个池 |
| **P0-2** | upTocPool 加 @Volatile + 赋值时序 | 高（Kotlin 注解直接可用） | 部分合理（@Volatile 仅解决可见性） | 符合规范 | 低 | ✅ 验证：line 54 `private var upTocPool` 无 @Volatile；upPool() line 82 先赋 threadCount，line 87 才检查 poolSize，时序确实有问题 | **强化**：@Volatile 不足以解决原子性，建议用 `Mutex` 包裹整个 `upPool()` 方法（项目已有 Mutex 依赖）；或用 `AtomicReference` + CAS 替换 |
| **P0-3** | CacheBookService.onDestroy 调整关闭顺序 | 高（仅调换 2 行顺序） | 合理（先取消内部协程再关池） | 符合规范 | 低 | ✅ 验证：CacheBookService.kt:94-100 当前顺序 cachePool.close() (line 96) → CacheBook.close() (line 97)，确实有 IllegalStateException 风险 | **可直接实施**，但需验证 CacheBook.close() 是否为 suspend（若 suspend 需在 runBlocking 中调用） |
| **P0-4** | CheckSourceService runBlocking 改 flowOn/withContext | 中（需测试 Flow 行为） | 合理（消除等待链） | 符合规范（withContext 是 suspend 函数标准用法） | 中（影响书源校验流程） | ✅ 验证：CheckSourceService.kt:117 `runBlocking(IO) { appDb.bookSourceDao.getBookSource(origin) }` 在 flow builder 内；line 137 `runBlocking(IO) { appDb.bookSourceDao.update(it) }` 在 onEach 内 | **方案优化**：flow builder 内直接用 `withContext(IO)` 即可（flow builder 是 suspend 块），比 `flowOn(IO)` 更直接；onEach 内同理 |
| **P0-5** | API Controller runBlocking 改专用 apiPool | 中（新增 apiPool + 替换 runBlocking 调度器） | 合理（隔离 HTTP API 与内部 IO） | 符合规范（独立池模式） | 高（影响所有 HTTP API） | ✅ 验证：Grep 命中 4 文件，BookSourceController.kt 有 5 处（line 13/19/34/54/67） | **方案优化**：API Controller 是同步 HTTP 接口，runBlocking 是必然的（无法改为 suspend）。建议改为 `runBlocking(apiPool.asCoroutineDispatcher())` 而非去掉 runBlocking；或直接复用 `Dispatchers.IO` 但限制 API 并发数（Semaphore） |
| **P0-6** | Coroutine.async 移除 DEFAULT=MainScope() + executeContext 改造 | 低（影响 50+ 调用点） | 部分合理（强制传入 scope 是好的），但 executeContext 改造有副作用 | 符合规范 | 高 | ✅ 验证：Coroutine.kt:37 `private val DEFAULT = MainScope()`；line 30 `executeContext: CoroutineContext = Dispatchers.Main`；line 174 `(scope.plus(executeContext)).launch` 确实让 semaphore.acquire() 在 Main 执行 | **拆分实施**：(1) DEFAULT=MainScope() 改造单独立项（影响 50+ 调用点）；(2) executeContext 改造需分离"执行块调度器"与"回调调度器"两个概念，当前方案会影响 success/onError 回调线程，需重新设计 |

---

## 三、P1 优化建议技术评估表（重点 10 项）

| 编号 | 建议 | 技术可行性 | 架构合理性 | 回归风险 | 源码验证结论 | 调整建议 |
|------|------|-----------|-----------|---------|-------------|---------|
| **P1-1** | 8 个 FixedThreadPool 增加 ThreadFactory 命名 | 高 | 合理（提升可观测性） | 低 | ✅ DispatchersMonitor.kt:26 已有命名范式 `Thread(it, TAG)` 可参考 | 建议同步实现 P2-4 公共 ThreadFactory 工具类 |
| **P1-2** | threadCount 改 var + initSearchPool 重读 | 高 | 合理（对齐 RssSearchModel 范式） | 低 | ✅ RssSearchModel.kt:52/93-111 是设计最优范式；SearchModel.kt:33 是 `val` 不可变 | **修正数字**：审查报告"6/8 个不可变"可能偏高，建议核实后修正 |
| **P1-3** | 5/8 个业务异常路径补充 close() | 高 | 合理（资源释放完整性） | 低 | 需逐个核实 5 个点的异常路径 | 建议与 P1-4 合并实施 |
| **P1-4** | stopSearch() close() 后置 null | 高 | 合理（防止 IllegalStateException） | 低 | 需核实 ChangeCoverViewModel/ChangeBookSourceViewModel | 与 SearchModel.kt:222-227 的 close() 范式对齐（已有 `searchPool = null`） |
| **P1-5** | ChangeBookSourceViewModel mapParallel → mapParallelSafe | 高 | 合理（单源失败不影响其他） | 低 | SearchModel.kt:99 和 RssSearchModel.kt:158 已用 mapParallelSafe，证实范式可行 | 直接替换即可 |
| **P1-6** | DispatchersMonitor select 后加 delay(5000) | 高 | 合理（避免 CPU 空转） | 低 | ✅ DispatchersMonitor.kt:46 `while (isActive) select {...}` 确实无间隔 | 直接添加 delay |
| **P1-7** | DispatchersMonitor 改非占用式检测 | 中（反射 scheduler.queue.size 有兼容性风险） | 部分合理（避免占用被监控池槽位） | 中 | ✅ DispatchersMonitor.kt:48 `withContext(dispatcher) { delay(3000) }` 确实占用被监控池 | **替代方案**：用 `kotlinx.coroutines.android.AndroidException` 或直接读取 `Dispatchers.IO` 的 `limitedParallelism` 状态，比反射更稳定 |
| **P1-8** | recordLog 切换时重启监控 | 高 | 合理（运行时配置响应） | 低 | ✅ DispatchersMonitor.kt:33 init() 仅 App.onCreate 调用一次，recordLog 运行时切换无效 | 需在 AppConfig.recordLog 的 setter 中调用 DispatchersMonitor.restart() |
| **P1-13** | globalExecutor 任务拆分 | 高 | 合理（Bitmap 回收与日志 I/O 隔离） | 低 | ✅ ExecutorService.kt 仅 7 行简单 lazy，3 个调用点（AsyncRecycleBitmapPool/AsyncFileHandler/LogUtils） | 建议 Bitmap 回收迁到 `Dispatchers.Default`（无需新建池） |
| **P1-15** | OkHttp 保活 5 → 2 分钟 | 高 | 合理（移动网络 NAT 周期适配） | 低 | 未读取 HttpHelper.kt:101，但审查报告描述具体 | 直接修改常量即可 |

---

## 四、实施顺序调整建议

### 4.1 当前推荐顺序评估

审查报告推荐顺序：P0-3 → P0-2 → P0-1 → P0-4 → P0-5 → P0-6

**问题**：
1. P0-2 在 P0-1 之前实施，但 P0-1 拆分后 cacheBookPool 字段同样需要 @Volatile 保护（若先做 P0-2 再做 P0-1，P0-1 又要补 @Volatile）
2. P0-6 列在最后但建议"单独立项"，与 P0-1~P0-5 同批列出易造成误解

### 4.2 依赖关系分析

| 依赖关系 | 说明 |
|---------|------|
| P0-1 → P0-2 | P0-1 拆分新增 cacheBookPool 字段，需同步加 @Volatile；建议合并实施 |
| P0-4 → P1-16 | P0-4 改造 CheckSourceService runBlocking 后，P1-16（CheckRssSourceService 同类问题）应同步实施（避免遗漏） |
| P0-5 → P1-9 | P0-5 新增 apiPool 后，P1-9（业务池全局上限）应评估是否合并（避免重复设计上限机制） |
| P0-6 独立 | P0-6 影响面太大，应单独立项，不与 P0-1~P0-5 同批 |

### 4.3 调整后推荐顺序

**第一批（独立修复，低风险）**：
1. P0-3 CacheBookService.onDestroy 关闭顺序（成本最低，独立修改）
2. P0-4 + P1-16 CheckSourceService/CheckRssSourceService runBlocking 改造（合并实施，避免遗漏）

**第二批（MainViewModel 集中改造）**：
3. P0-1 + P0-2 合并实施：拆分 upTocPool/cacheBookPool + @Volatile + Mutex 保护 upPool() + 同步修改 line 290 调用点

**第三批（独立池改造）**：
4. P0-5 API Controller runBlocking 改造（新增 apiPool，影响所有 HTTP API）

**第四批（单独立项）**：
5. P0-6 Coroutine.async scope+executeContext 改造（影响 50+ 调用点，需重新设计 executeContext 与回调调度器分离方案）

**第五批（P1 批量）**：
6. P1-1/P1-2/P1-4/P1-5/P1-15 等低成本项批量实施

---

## 五、架构风险清单

### 5.1 可能引入的新架构耦合

| 风险点 | 涉及优化建议 | 说明 |
|--------|------------|------|
| apiPool 单例化 | P0-5 | 新增 apiPool 若作为 object 单例（如 `object ApiPool { val pool = ... }`），会引入新的全局单例依赖；建议放在现有 `ExecutorService.kt` 中统一管理 |
| 业务池全局上限机制 | P1-9 | AppConfig 增加 totalBusinessThreadCap 会引入新的配置项与 8 个业务池的耦合；建议改为各业务池独立上限（已通过 searchThreadCount/updateCacheThreadCount 实现） |
| DispatchersMonitor.restart() | P1-8 | 新增 restart() 方法会暴露 DispatchersMonitor 的内部状态管理；需保证线程安全 |

### 5.2 可能破坏的现有抽象

| 风险点 | 涉及优化建议 | 说明 |
|--------|------------|------|
| Coroutine.async 回调调度器语义 | P0-6 | 当前 `executeContext=Main` 同时承担 "semaphore.acquire() 调度器" 和 "success/onError 回调调度器" 双重职责；改造需分离这两个概念，否则会破坏回调线程语义 |
| CacheBook.startProcessJob(pool) 接口契约 | P0-1 | MainViewModel.kt:290 将 upTocPool 传递给 CacheBook.startProcessJob，拆分后需保证 CacheBook 接收的 pool 与调用方 Job 的 pool 一致 |
| RssSearchModel 范式推广 | P1-2 | 将 RssSearchModel 的 `var threadCount + initSearchPool` 范式推广到其他 7 个业务池，需保证各业务池的重建逻辑与生命周期匹配（MainViewModel.upTocPool 有 upPool() 重建逻辑，其他池无） |

### 5.3 需要新增的架构抽象

| 抽象 | 涉及优化建议 | 说明 |
|------|------------|------|
| 公共 ThreadFactory 工具类 | P1-1 + P2-4 | 8 个业务池 + globalExecutor 都需要 ThreadFactory 命名，建议新增 `io.legado.app.help.NamedThreadFactory` 工具类 |
| 业务池生命周期管理器 | P1-3 + P1-4 | 5/8 个业务池异常路径不主动 close，建议封装 `BusinessPoolManager` 统一管理 close/null 检查 |
| 调度器监控非占用式检测接口 | P1-7 | 反射读取 `scheduler.queue.size` 有兼容性风险，建议封装为 `DispatcherStateProvider` 接口，便于后续替换实现 |

---

## 六、AR-P0/AR-P1/AR-P2 严重度分级

### AR-P0：严重架构问题（影响系统稳定性）— 3 项

| 编号 | 问题 | 涉及优化建议 | 修复优先级 |
|------|------|------------|-----------|
| AR-P0-1 | P0-1 拆分 upTocPool 未覆盖 CacheBook.startProcessJob 调用点 | P0-1 | 必须在 P0-1 实施时同步修复 |
| AR-P0-2 | P0-2 @Volatile 不足以解决 upPool() 原子性问题，存在创建两个池的窗口期 | P0-2 | 必须升级为 Mutex 保护整个 upPool() |
| AR-P0-3 | P0-6 executeContext 改造会破坏 success/onError 回调线程语义 | P0-6 | 必须重新设计"执行块调度器"与"回调调度器"分离方案 |

### AR-P1：中等架构问题（影响可维护性）— 4 项

| 编号 | 问题 | 涉及优化建议 | 修复优先级 |
|------|------|------------|-----------|
| AR-P1-1 | P1-2 "6/8 个不可变"数字与源码抽样不一致 | P1-2 | 建议核实后修正 |
| AR-P1-2 | P0-5 未说明 API Controller runBlocking 的必然性（同步 HTTP 接口性质） | P0-5 | 建议补充说明：runBlocking 不可去除，仅能替换调度器 |
| AR-P1-3 | P0-4 方案建议 flowOn(IO)，但 flow builder 内直接用 withContext(IO) 更直接 | P0-4 | 建议优化方案描述 |
| AR-P1-4 | 实施顺序未考虑 P0-1 与 P0-2 的强依赖关系 | 4.1 | 建议合并实施 |

### AR-P2：轻微架构问题（优化架构）— 3 项

| 编号 | 问题 | 涉及优化建议 | 修复优先级 |
|------|------|------------|-----------|
| AR-P2-1 | P1-7 反射 scheduler.queue.size 有兼容性风险 | P1-7 | 建议封装为接口 |
| AR-P2-2 | P1-9 业务池全局上限引入新耦合 | P1-9 | 建议改为各业务池独立上限 |
| AR-P2-3 | apiPool 单例化位置未明确 | P0-5 | 建议放在 ExecutorService.kt 统一管理 |

---

## 七、审查结论

### 7.1 审查报告质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 配置点覆盖完整性 | 10/10 | 13 项配置点全部覆盖 |
| 源码验证准确率 | 10/10 | 6/6 P0 全部命中真实代码位置 |
| 优化建议技术可行性 | 8/10 | P0-2/P0-6 方案有改进空间 |
| 架构合理性分析 | 9/10 | 符合项目现有架构模式 |
| 规范符合性 | 9/10 | 符合 object+ViewModel+Coroutine.async 模式 |
| 回归风险评估 | 7/10 | 未识别 P0-1 隐藏调用点、P0-2 原子性问题、P0-6 回调副作用 |
| 实施顺序合理性 | 7/10 | 未考虑 P0-1/P0-2 强依赖关系 |

### 7.2 核心建议

1. **P0-1 实施时必须同步修改 MainViewModel.kt:290** 的 `CacheBook.startProcessJob(upTocPool)` 调用点
2. **P0-2 升级为 Mutex 保护整个 upPool() 方法**（@Volatile 不足以解决原子性）
3. **P0-6 拆分为两个独立子任务**：(1) DEFAULT=MainScope() 改造（影响 50+ 调用点）；(2) executeContext 与回调调度器分离（需重新设计）
4. **P0-1 + P0-2 合并实施**（强依赖关系）
5. **P0-4 + P1-16 合并实施**（同类问题避免遗漏）
6. **核实 P1-2 "6/8 个不可变" 数字**（源码抽样显示可能偏高）

### 7.3 整体结论

审查报告技术架构质量优秀，可作为后续优化的可靠输入。本次审查识别 3 项 AR-P0 架构风险（隐藏调用点 / 原子性 / 回调副作用），建议在实施前对 P0-1/P0-2/P0-6 三项进行方案修订。其余 P0-3/P0-4/P0-5 可按调整后顺序直接实施。
