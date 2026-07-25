# 线程池配置全面审查设计文档

> 任务类型：架构审查（静态代码审查）
> 文档版本：v1.0
> 创建日期：2026-07-25
> 适用范围：Legado 项目全部线程池配置点

---

## 一、Technical Approach（技术方案）

### 1.1 审查方法

采用 **静态代码审查 + 架构分析** 方法，不依赖运行时埋点。

执行流程：
1. **技术字段搜索**：通过 Grep 搜索技术关键词（`Executors.newFixedThreadPool`、`Executors.newSingleThreadExecutor`、`ExecutorService`、`CoroutineScope`、`Dispatchers.IO`、`ConnectionPool`），定位所有线程池创建点
2. **逐点分析**：对每个配置点 Read 上下文，确认用途、大小、生命周期管理逻辑
3. **合理性评估**：从线程数、生命周期、共享/独立、关闭逻辑四个维度评估
4. **问题识别**：标记泄漏风险、过大配置、未显式关闭等问题
5. **优化建议**：输出可落地的优化建议清单（不直接改代码，留待后续任务实施）

### 1.2 审查发现的线程池配置清单（13 项）

| # | 文件 | 行号 | 类型 | 大小 | 用途 | 生命周期 |
|---|------|------|------|------|------|---------|
| 1 | ExecutorService.kt | 6 | SingleThread | 1 | globalExecutor 全局 | lazy 未关闭 |
| 2 | CheckSourceService.kt | 66 | Fixed | searchThreadCount(32) | 书源校验 | Service 销毁时关闭 |
| 3 | CheckRssSourceService.kt | 63 | Fixed | searchThreadCount(32) | RSS 源校验 | Service 销毁时关闭 |
| 4 | CacheBookService.kt | 46 | Fixed | updateCacheThreadCount(16) | 缓存下载 | Service 销毁时关闭 |
| 5 | MainViewModel.kt | 54/92 | Fixed | updateCacheThreadCount(16) | 目录更新 | 可重建（upPool） |
| 6 | SearchModel.kt | 59 | Fixed | searchThreadCount(32) | 书源搜索 | 搜索结束关闭 |
| 7 | RssSearchModel.kt | 110 | Fixed | searchThreadCount(32) | RSS 搜索 | 搜索结束关闭 |
| 8 | ChangeCoverViewModel.kt | 101 | Fixed | searchThreadCount(32) | 换封面 | ViewModel 销毁时关闭 |
| 9 | ChangeBookSourceViewModel.kt | 167 | Fixed | searchThreadCount(32) | 换源 | ViewModel 销毁时关闭 |
| 10 | DispatchersMonitor.kt | 26 | SingleThread | 1 | 调度器监控 | lazy 未关闭 |
| 11 | HttpHelper.kt | 101 | ConnectionPool | 50 连接 5 分钟 | OkHttp 连接 | 未显式关闭 |
| 12 | Coroutine.kt | - | Dispatchers.IO | 64（默认） | 自定义协程 | 共享系统 |
| 13 | 全项目 | - | Dispatchers.IO | 64（默认） | 20+ 处 IO 操作 | 共享系统 |

### 1.3 评估维度

| 维度 | 关注点 |
|------|--------|
| 线程数 | 是否过大导致内存/CPU 压力；是否过小导致吞吐瓶颈 |
| 生命周期 | 创建后是否正确关闭；是否存在泄漏路径 |
| 共享/独立 | 业务隔离性；不同业务是否复用同一池 |
| 关闭逻辑 | Service/ViewModel 销毁时是否触发 shutdown |

### 1.4 已识别的关键观察

- **独立 Fixed 池重复配置**：searchThreadCount(32) 在 5 个业务点重复创建临时池（条目 2/3/6/7/8/9），每次业务启动即 new 一个池
- **全局单例未关闭**：globalExecutor、DispatchersMonitor 均为 lazy 单例，进程级常驻（设计预期，但需文档化）
- **唯一显式重建**：upTocPool（条目 5）是 8 个 Fixed 池中唯一带重建逻辑的，其余仅依赖组件销毁
- **共享调度器**：Dispatchers.IO（64 线程）被 20+ 处复用，单点拥塞可能波及全局
- **连接池无显式关闭**：HttpHelper 的 OkHttp ConnectionPool 依赖 JVM 退出回收

---

## 二、Architecture Decisions（架构决策 - ADR Y-Statement）

### AD-01：审查方法选择

| 字段 | 内容 |
|------|------|
| **Context** | 需要全面审查线程池配置合理性，覆盖所有创建点 |
| **Concern** | 静态审查 vs 运行时分析的选择 |
| **Decision** | 采用静态代码审查 + 架构分析（Grep 搜索 + Read 分析） |
| **Goal** | 快速覆盖所有线程池配置点，识别架构层面问题（泄漏、过大、未关闭） |
| **Tradeoff** | 无法发现运行时资源竞争、死锁、实际峰值负载 |
| **Alternatives** | 运行时埋点 + Profiler 分析（成本高，覆盖慢）；单元测试压测（粒度过细） |
| **Status** | Accepted |

### AD-02：线程池大小默认值评估

| 字段 | 内容 |
|------|------|
| **Context** | searchThreadCount 默认 32，updateCacheThreadCount 默认 16，均为业务侧可调 |
| **Concern** | 默认值是否合理，是否过大导致资源竞争（尤其低端机型） |
| **Decision** | 审查后评估是否需要调整默认值，倾向保守默认 + 用户可调 |
| **Goal** | 平衡并发性能和资源消耗，避免低端机型 OOM/ANR |
| **Tradeoff** | 较大默认值提升并发吞吐但增加内存/CPU 压力；较小默认值安全但慢 |
| **Alternatives** | 按设备 CPU 核数动态计算（如 `Runtime.availableProcessors * 2`） |
| **Status** | Proposed |

### AD-03：线程池生命周期管理

| 字段 | 内容 |
|------|------|
| **Context** | 8 个 FixedThreadPool 中仅 upTocPool 有显式重建逻辑，其余依赖 Service/ViewModel 销毁 |
| **Concern** | 其他线程池是否有泄漏风险（尤其异步任务未完成即销毁） |
| **Decision** | 审查每个线程池的关闭逻辑，识别泄漏点，建议统一生命周期封装 |
| **Goal** | 确保所有线程池正确关闭，避免任务悬挂和线程泄漏 |
| **Tradeoff** | 显式关闭增加代码复杂度；统一封装引入抽象层 |
| **Alternatives** | 全部改用协程 + 结构化并发（CoroutineScope 自动取消） |
| **Status** | Proposed |

---

## 三、Data Flow（数据流）

描述线程池在业务流程中的使用链路（按业务场景划分）。

### 3.1 搜索流程

```
用户触发搜索
  → SearchModel 创建 searchPool（Fixed, 32）
  → 并发分发书源请求任务
  → 各书源独立请求并返回结果
  → 结果汇聚到 UI
  → 搜索结束调用 shutdown 关闭 searchPool
```

涉及配置点：条目 6（SearchModel.kt）、条目 12（Coroutine.kt 内部 IO 调度）

### 3.2 校验流程

```
用户触发书源/RSS 源校验
  → CheckSourceService / CheckRssSourceService 创建 searchCoroutine（Fixed, 32）
  → 并发校验各源可用性
  → 返回校验结果
  → Service 销毁（onDestroy）时关闭线程池
```

涉及配置点：条目 2（CheckSourceService.kt）、条目 3（CheckRssSourceService.kt）

### 3.3 缓存流程

```
用户触发缓存下载
  → CacheBookService 创建 cachePool（Fixed, 16）
  → 并发下载章节内容
  → 写入本地存储
  → Service 销毁时关闭线程池
```

涉及配置点：条目 4（CacheBookService.kt）

### 3.4 更新流程

```
书籍目录更新
  → MainViewModel 使用 upTocPool（Fixed, 16）
  → 并发请求书源目录
  → 结果回写到 UI
  → 支持重建（唯一带重建逻辑的池）
```

涉及配置点：条目 5（MainViewModel.kt）

### 3.5 IO 通用流程

```
任意 IO 操作（文件读写、数据库、网络）
  → Coroutine.async 默认调度到 Dispatchers.IO
  → 共享 64 线程系统调度器
  → 执行 IO 操作
  → 返回结果（无显式关闭，系统常驻）
```

涉及配置点：条目 12（Coroutine.kt）、条目 13（全项目 20+ 处）

### 3.6 全局后台流程

```
应用启动
  → globalExecutor（SingleThread, lazy）按需初始化
  → 承接全局低频后台任务
  → 常驻至进程退出（lazy 单例未显式关闭）
```

涉及配置点：条目 1（ExecutorService.kt）、条目 10（DispatchersMonitor.kt）

---

## 四、File Changes（文件变更）

本任务为**审查任务**，原则上不涉及代码变更，仅输出审查报告与优化建议。

如审查发现需优化的点，建议在后续独立任务中实施（避免审查与改造耦合）。初步识别的潜在优化点（待审查报告确认后立项）：

| 文件 | 潜在优化方向 | 风险等级 |
|------|------------|---------|
| ExecutorService.kt | globalExecutor 用途文档化；评估是否暴露关闭接口 | 低 |
| HttpHelper.kt | OkHttp ConnectionPool 大小评估；连接超时与 keep-alive 调优 | 低 |
| SearchModel.kt / RssSearchModel.kt | searchPool 复用 vs 每次新建评估；异常路径关闭完整性 | 中 |
| CheckSourceService.kt / CheckRssSourceService.kt | searchCoroutine 关闭时序与未完成任务处理 | 中 |
| CacheBookService.kt | cachePool 关闭时序与下载中断恢复 | 中 |
| MainViewModel.kt | upTocPool 重建逻辑抽象化复用 | 中 |
| ChangeCoverViewModel.kt / ChangeBookSourceViewModel.kt | ViewModel 销毁时关闭完整性验证 | 低 |
| DispatchersMonitor.kt | 监控线程生命周期文档化 | 低 |
| Coroutine.kt | 自定义协程封装是否需独立调度器评估 | 低 |

### 4.1 变更约束

- **不与审查耦合**：任何代码变更必须在审查报告交付后独立立项
- **遵循项目规范**：若实施优化，需遵守 `naming_rules.md`、`checkstyle_rules.md`、`architecture_rules.md`
- **真机验证**：若涉及线程数/调度器调整，必须按 `ai_e2e_testing_workflow.md` 执行真机测试
- **版本同步**：若产生代码变更，必须按 `version-delivery-sync.md` 更新 `assets/updateLog.md`

### 4.2 交付物

本任务交付物仅为 `design.md`（本文档）。后续将产出：
- 审查报告（含问题清单、严重度评级、修复建议）
- 优化任务拆解清单（如有）

---

## 五、验证标准

| 检查项 | 状态 |
|--------|------|
| 包含 Technical Approach 章节 | ✅ |
| 包含 Architecture Decisions（ADR Y-Statement）章节 | ✅ |
| 包含 Data Flow 章节 | ✅ |
| 包含 File Changes 章节 | ✅ |
| 13 项线程池配置清单完整记录 | ✅ |
| ADR 采用 Y-Statement 模板（Context/Concern/Decision/Goal/Tradeoff/Status） | ✅ |
| 无 ASCII 图表 | ✅ |
| 无违禁词（仅技术字段、文件名、行号、异常类型） | ✅ |
