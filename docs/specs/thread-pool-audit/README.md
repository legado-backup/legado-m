# 线程池配置全面审查

## 状态

🔄 开发中（审查报告已生成，等待用户审核检查点2）

## 功能概述

全面审查项目所有线程池配置的合理性，识别优化空间。针对项目中分散存在的线程池创建点（FixedThreadPool、SingleThreadExecutor）、Kotlin 协程调度器、OkHttp 连接池及监控组件进行系统性梳理，评估线程数量配置、命名规范、生命周期管理、资源竞争与泄漏风险，输出可执行的优化方案，确保线程资源在高并发场景下的稳定性与可控性。

## 核心能力

### 1. FixedThreadPool 创建点审查（8 个）

| # | 文件位置 | 线程数来源 | 用途 |
|---|---------|-----------|------|
| 1 | `CheckSourceService.kt:66` | searchThreadCount | 书源校验 |
| 2 | `CheckRssSourceService.kt:63` | searchThreadCount | 订阅源校验 |
| 3 | `CacheBookService.kt:46` | updateCacheThreadCount | 缓存更新 |
| 4 | `MainViewModel.kt:54` | updateCacheThreadCount | 缓存更新（可重建） |
| 5 | `MainViewModel.kt:92` | updateCacheThreadCount | 缓存更新（可重建） |
| 6 | `SearchModel.kt:59` | searchThreadCount | 书籍搜索 |
| 7 | `RssSearchModel.kt:110` | searchThreadCount | 订阅源搜索 |
| 8 | `ChangeCoverViewModel.kt:101` | searchThreadCount | 换封面 |
| 9 | `ChangeBookSourceViewModel.kt:167` | searchThreadCount | 换书源 |

审查维度：线程数动态配置合理性、池命名规范、关闭时机、与其他池的资源竞争。

### 2. Kotlin 协程调度器审查

- **Dispatchers.IO**：20+ 处使用，评估是否存在过度占用共享 IO 池的风险
- **Dispatchers.Main**：UI 线程调度，验证主线程阻塞风险
- **自定义 Coroutine.async**：默认使用 IO 调度器，审查 `onError` / `onSuccess` 链式封装的上下文切换

### 3. OkHttp 连接池审查

- **位置**：`HttpHelper.kt:101`
- **配置**：`ConnectionPool(50, 5, MINUTES)`（最大 50 个空闲连接，5 分钟超时）
- **审查点**：连接数与 FixedThreadPool 线程数的匹配度、空闲连接回收策略、与其他网络组件的协同

### 4. 全局单线程池审查

- **位置**：`ExecutorService.kt:6`（globalExecutor）
- **类型**：`newSingleThreadExecutor`
- **审查点**：单线程瓶颈风险、任务排队时长、与业务线程池的隔离性

### 5. DispatchersMonitor 审查

- **类型**：单线程监控调度器
- **触发条件**：仅 `recordLog = true` 时生效
- **审查点**：监控开销、生产环境开关、对主链路的影响

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格说明（审查目标、范围、验收标准） |
| [design.md](./design.md) | 设计方案（审查方法论、优化策略、实施步骤） |
| [tasks.md](./tasks.md) | 任务分解（审查清单、优化任务、验收用例） |
