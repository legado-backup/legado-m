# 需求规格 - 线程池配置全面审查

## Intent（意图）

全面审查项目中所有线程池配置的合理性，识别资源浪费、泄漏风险、性能瓶颈，提出优化建议。

通过对 `app/src/main/java/io/legado/app/` 下所有线程池创建点与并发调度组件的系统性梳理，达成以下目标：

1. 盘点项目中所有线程池配置点（类型、大小、生命周期、用途）
2. 评估每个线程池配置的合理性，识别资源浪费与性能瓶颈
3. 识别资源泄漏风险（未关闭的线程池、未释放的连接）
4. 识别性能瓶颈（过小导致任务排队、过大导致 CPU 抖动与 OOM 风险）
5. 提出可执行的优化建议（含优先级），为后续线程池拆分与配置改造任务提供输入

## Scope（范围）

### In Scope（本次审查）

- 审查路径：`app/src/main/java/io/legado/app/` 下所有线程池配置
- 包含的审查对象：
  - `FixedThreadPool` 创建点（8 个业务创建点）
  - `Dispatchers.IO` 使用情况（20+ 处调用）
  - OkHttp 连接池配置（`ConnectionPool`）
  - 全局单线程池 `globalExecutor`（`ExecutorService.kt:6`）
  - `DispatchersMonitor` 监控逻辑
- 审查维度：线程池类型、线程数来源、命名规范、生命周期管理、关闭时机、与其他池的资源竞争

### Out of Scope（不在本次审查）

- 非线程池并发配置（锁、原子变量、Channel、Flow 背压等）
- 协程 `Coroutine.async` 链式封装本身的语义改造（仅审查其默认调度器选择）
- 业务逻辑层面的并发正确性（如临界区保护、数据竞争）
- 单元测试与运行时性能测试的编写（仅静态审查与架构分析）

## Approach（方案）

### Selected Approach（选定方案）

**静态代码审查 + 架构分析**

通过 Grep 搜索所有线程池创建点（`Executors.newFixedThreadPool`、`Executors.newSingleThreadExecutor`、`newFixedThreadPoolContext`、`ExecutorCoroutineDispatcher`、`ConnectionPool`、`Dispatchers.IO`、`DispatchersMonitor`），逐点分析每个线程池的：

1. **类型**：固定线程池 / 单线程池 / 缓存线程池 / 调度器 / 连接池
2. **大小**：线程数来源（常量、用户配置、`AppConfig` 字段、`min(..., MAX_THREAD)` 兜底）
3. **生命周期**：创建时机、关闭时机、是否随业务对象销毁而释放
4. **用途**：承载的业务场景（搜索、缓存、校验、监控等）
5. **风险点**：资源泄漏、性能瓶颈、与其它线程池的资源竞争

在逐点分析基础上进行架构层面的横向对比，识别共性问题（如多业务共用同一配置项、缺统一命名工厂、关闭时机不明确等），输出可执行的优化建议清单（按 P0/P1/P2 优先级标注）。

**选定理由**：
- 覆盖面广：可一次性盘点项目中所有线程池配置点，不依赖运行时场景
- 风险低：纯静态分析，不修改代码、不影响线上稳定性
- 输出可执行：直接为后续"线程池拆分与自定义配置"任务（详见 `thread-pool-split-config`）提供输入
- 与项目现状匹配：项目线程池配置点分散且数量有限（8 个 FixedThreadPool + 1 个 globalExecutor + 1 个连接池），静态审查可完整覆盖

### Alternatives Considered（备选方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 运行时性能分析 | 通过 Android Studio Profiler / Systrace / `dumpsys` 分析线程池运行时性能，采集 CPU 占用、线程阻塞、任务排队时长等指标 | 耗时长，无法覆盖所有业务场景；运行时指标受测试用例影响大，难以反映真实用户环境；本次任务目标是"配置合理性审查"而非"运行时性能评估"，静态审查已能识别架构层面问题 |
| 单元测试覆盖 | 编写单元测试验证每个线程池的行为（线程数、关闭时机、任务拒绝策略等） | 无法发现架构层面的不合理设计（如多业务共用同一配置项、缺统一命名工厂等）；测试编写成本高且覆盖面有限；单元测试更适合验证"改造后"的行为而非"改造前"的合理性 |

### Drawbacks（已知缺点）

1. **无法发现运行时资源竞争和死锁问题**：静态审查只能识别"配置层面的风险"，无法捕捉运行时多线程竞争导致的死锁、活锁、优先级反转等问题
   - **缓解措施**：在审查报告中标注"需运行时验证"的风险点，为后续运行时性能分析任务预留接口

2. **无法量化线程池实际负载**：静态审查无法知道每个线程池在真实业务中的实际并发度、任务排队时长、线程空闲率
   - **缓解措施**：结合业务场景推断负载特征（如搜索为突发高并发、缓存为持续中低并发），给出基于业务特征的合理性判断

3. **审查结论依赖代码可读性**：若线程池创建点分散或封装层次过深，可能遗漏部分配置点
   - **缓解措施**：使用多种 Grep 模式交叉验证（`Executors.new` / `ExecutorCoroutineDispatcher` / `ConnectionPool` / `Dispatchers.IO` / `DispatchersMonitor`），并对照 `README.md` 中已盘点的清单核对

## Requirements（需求）

### R1: 盘点所有线程池配置点

- **R1.1** 列出所有 `FixedThreadPool` 创建点（8 个），记录：文件位置、行号、线程数来源、用途、关闭时机
- **R1.2** 列出 `Dispatchers.IO` 的所有使用点（20+ 处），按业务场景归类（搜索、缓存、校验、网络、其他）
- **R1.3** 记录 OkHttp 连接池配置：`ConnectionPool(50, 5, MINUTES)` 的位置、参数含义、与其他网络组件的协同关系
- **R1.4** 记录 `globalExecutor`（`ExecutorService.kt:6`）的类型（`newSingleThreadExecutor`）、用途、生命周期
- **R1.5** 记录 `DispatchersMonitor` 的触发条件（`recordLog = true`）、监控开销、对主链路的影响

### R2: 评估每个线程池配置的合理性

- **R2.1** 评估线程数配置合理性：是否过大（OOM 风险）/ 过小（性能瓶颈）/ 是否有上限保护
- **R2.2** 评估线程池类型合理性：是否应使用 `FixedThreadPool` 而非 `CachedThreadPool`、是否应使用单线程池而非固定线程池
- **R2.3** 评估生命周期合理性：创建时机是否过早、关闭时机是否及时、是否随业务对象销毁而释放
- **R2.4** 评估命名规范：线程是否通过 `ThreadFactory` 命名，便于问题定位与日志排查

### R3: 识别资源泄漏风险

- **R3.1** 检查所有 `FixedThreadPool` 创建点是否在业务对象销毁时调用 `close()` / `shutdown()`
- **R3.2** 检查 `globalExecutor` 是否存在未关闭导致的常驻线程
- **R3.3** 检查 OkHttp 连接池的空闲连接回收策略是否合理（5 分钟超时是否过长/过短）
- **R3.4** 检查 `DispatchersMonitor` 在 `recordLog = false` 时是否仍有残留线程

### R4: 识别性能瓶颈

- **R4.1** 识别过小的线程池（如单线程池承载高并发业务）导致的任务排队瓶颈
- **R4.2** 识别过大的线程池（如无上限保护）导致的 CPU 抖动与 OOM 风险
- **R4.3** 识别多业务共用同一配置项导致的相互影响（如搜索与缓存共用 `threadCount`）
- **R4.4** 识别 `Dispatchers.IO` 默认 64 线程上限与业务实际需求的匹配度

### R5: 提出优化建议

- **R5.1** 针对每个识别的问题，给出具体的优化建议（含修改文件、修改内容、预期收益）
- **R5.2** 按优先级标注每条优化建议：P0（必须修复，存在稳定性风险）、P1（建议修复，存在性能/可维护性问题）、P2（可选优化，提升体验）
- **R5.3** 评估每条优化建议的实施成本与回归风险，为后续任务排期提供参考
- **R5.4** 将优化建议汇总为审查报告，输出到 `docs/specs/thread-pool-audit/` 目录下

## Scenarios（场景）

### Scenario 1: 审查 FixedThreadPool 创建点（8 个）

1. 通过 Grep 搜索 `Executors.newFixedThreadPool` 和 `newFixedThreadPoolContext` 定位所有创建点
2. 逐点核对：文件位置、行号、线程数来源、用途、关闭时机
3. 重点核对以下 8 个创建点：
   - `CheckSourceService.kt:66`（书源校验，searchThreadCount）
   - `CheckRssSourceService.kt:63`（订阅源校验，searchThreadCount）
   - `CacheBookService.kt:46`（缓存更新，updateCacheThreadCount）
   - `MainViewModel.kt:54`（缓存更新，updateCacheThreadCount，可重建）
   - `MainViewModel.kt:92`（缓存更新，updateCacheThreadCount，可重建）
   - `SearchModel.kt:59`（书籍搜索，searchThreadCount）
   - `RssSearchModel.kt:110`（订阅源搜索，searchThreadCount）
   - `ChangeCoverViewModel.kt:101`（换封面，searchThreadCount）
   - `ChangeBookSourceViewModel.kt:167`（换书源，searchThreadCount）
4. 输出每个创建点的审查结论（合理性 / 风险点 / 优化建议）

### Scenario 2: 审查 Dispatchers.IO 使用情况（20+ 处）

1. 通过 Grep 搜索 `Dispatchers.IO` 定位所有使用点
2. 按业务场景归类：搜索类、缓存类、校验类、网络类、其他
3. 评估每处使用的合理性：
   - 是否过度占用共享 IO 池（默认 64 线程上限）
   - 是否应改用独立线程池（如搜索类已使用独立 FixedThreadPool，但部分辅助逻辑仍用 `Dispatchers.IO`）
   - 是否存在主线程阻塞风险（`Dispatchers.IO` 内调用 `runBlocking` 等）
4. 输出 `Dispatchers.IO` 使用清单与优化建议

### Scenario 3: 审查 OkHttp 连接池配置

1. 定位 `ConnectionPool(50, 5, MINUTES)` 配置点（`HttpHelper.kt:101`）
2. 评估参数合理性：
   - 最大空闲连接数 50：与 FixedThreadPool 线程数的匹配度（搜索 32 + 缓存 16 + 校验 N 是否超过 50）
   - 空闲连接超时 5 分钟：是否过长（占用内存）或过短（频繁重建连接）
3. 评估与其他网络组件的协同：
   - 与 `WebViewPool` 的连接复用关系
   - 与 `CookieStore` 的会话保持关系
   - 与并发请求限流策略的配合
4. 输出连接池配置审查结论与优化建议

### Scenario 4: 审查 globalExecutor 单线程池

1. 定位 `globalExecutor`（`ExecutorService.kt:6`），确认类型为 `newSingleThreadExecutor`
2. 梳理 `globalExecutor` 承载的所有任务（通过 Grep 搜索 `globalExecutor.execute` / `globalExecutor.submit`）
3. 评估单线程瓶颈风险：
   - 是否存在高并发任务被单线程串行化执行
   - 是否存在长耗时任务阻塞后续任务
4. 评估与业务线程池的隔离性：
   - `globalExecutor` 与 `FixedThreadPool` 是否存在任务耦合
   - 是否应将部分任务迁移到业务线程池
5. 评估生命周期：`globalExecutor` 作为全局单例是否随 Application 销毁而释放
6. 输出 `globalExecutor` 审查结论与优化建议

### Scenario 5: 审查 DispatchersMonitor 监控逻辑

1. 定位 `DispatchersMonitor` 实现，确认触发条件为 `recordLog = true`
2. 评估监控开销：
   - 单线程监控调度器的资源占用
   - 监控日志写入对主链路的影响
   - `recordLog = false` 时是否完全无开销
3. 评估生产环境开关：
   - `recordLog` 默认值是否合理（生产环境应关闭）
   - 是否有用户可见的开关入口
   - 是否有自动关闭机制（如运行 N 分钟后自动关闭）
4. 评估对主链路的影响：
   - 监控逻辑是否会阻塞主线程
   - 监控日志是否会占用过多 IO 资源
5. 输出 `DispatchersMonitor` 审查结论与优化建议

## 审查发现摘要（项目线程池配置清单）

> 以下为审查前已盘点的项目线程池配置清单，作为审查工作的输入基线。

| # | 配置项 | 位置 | 类型 | 线程数来源 | 用途 |
|---|--------|------|------|-----------|------|
| 1 | `globalExecutor` | `ExecutorService.kt:6` | `newSingleThreadExecutor` | 1（固定） | 全局单线程任务执行器 |
| 2 | 书源校验池 | `CheckSourceService.kt:66` | `FixedThreadPool` | `searchThreadCount` | 书源批量校验 |
| 3 | 订阅源校验池 | `CheckRssSourceService.kt:63` | `FixedThreadPool` | `searchThreadCount` | 订阅源批量校验 |
| 4 | 缓存更新池 | `CacheBookService.kt:46` | `FixedThreadPool` | `updateCacheThreadCount` | 书籍缓存下载 |
| 5 | 缓存更新池（可重建） | `MainViewModel.kt:54` | `FixedThreadPool` | `updateCacheThreadCount` | 更新目录（upTocPool） |
| 6 | 缓存更新池（可重建） | `MainViewModel.kt:92` | `FixedThreadPool` | `updateCacheThreadCount` | 更新目录（upTocPool） |
| 7 | 书籍搜索池 | `SearchModel.kt:59` | `FixedThreadPool` | `searchThreadCount` | 书籍搜索 |
| 8 | 订阅源搜索池 | `RssSearchModel.kt:110` | `FixedThreadPool` | `searchThreadCount` | 订阅源搜索 |
| 9 | 换封面池 | `ChangeCoverViewModel.kt:101` | `FixedThreadPool` | `searchThreadCount` | 换封面并发拉取 |
| 10 | 换书源池 | `ChangeBookSourceViewModel.kt:167` | `FixedThreadPool` | `searchThreadCount` | 换书源并发拉取 |
| 11 | `Dispatchers.IO` | 20+ 处使用 | 协程 IO 调度器 | 默认 64 线程上限 | 各类 IO 密集型协程任务 |
| 12 | OkHttp 连接池 | `HttpHelper.kt:101` | `ConnectionPool` | `ConnectionPool(50, 5, MINUTES)` | HTTP 连接复用 |
| 13 | `DispatchersMonitor` | 协程监控组件 | 单线程监控调度器 | 1（固定） | 协程调度监控（仅 `recordLog = true` 时生效） |

**初步观察**：
- 8 个业务 `FixedThreadPool` 共用 2 个配置项（`searchThreadCount` / `updateCacheThreadCount`），多业务共用同一配置可能导致相互影响（详见 `thread-pool-split-config` 任务）
- `globalExecutor` 作为全局单线程池，承载的任务范围需重点审查是否存在瓶颈
- `Dispatchers.IO` 默认 64 线程上限与业务实际并发度的匹配度需评估
- OkHttp 连接池 50 个空闲连接与 `FixedThreadPool` 总线程数（搜索 32 + 缓存 16 + 校验 N）的匹配度需评估
- `DispatchersMonitor` 仅在 `recordLog = true` 时生效，生产环境开销需确认
