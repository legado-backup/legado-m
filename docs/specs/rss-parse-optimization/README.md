# 订阅源（RSS源）解析全流程性能优化

## 功能概述

针对订阅源（RSS源）解析全流程进行系统性性能优化，覆盖网络请求层、规则引擎、图片加载、数据库、并发与内存五个维度，共识别 22 个优化点（5 个 P1 + 17 个 P2），通过分三批实施，提升列表加载速度、降低 CPU/GC 开销、优化内存占用。

### 核心问题

| 编号 | 维度 | 问题 | 优先级 | 用户影响 |
|------|------|------|--------|---------|
| 2.1 | 规则引擎 | AnalyzeByRegex 每次重新编译 Pattern | P1 | Regex 源每项解析浪费 0.5-2ms CPU |
| 2.2 | 规则引擎 | AnalyzeRule 缓存 per-instance 不共享 | P1 | 含 JS 源每项重复编译，浪费 2-10ms |
| 4.1 | 数据库 | RssArticle 缺少 (origin,sort) 复合索引 | P1 | 大列表源（>1000条）加载卡顿 |
| 1.2 | 网络层 | 无 HTTP 响应缓存 | P1 | 重复请求浪费 200-2000ms |
| 5.1 | 并发内存 | AnalyzeRule 实例创建开销大 | P1 | 列表解析增加 30% GC 时间 |

## 核心能力

### 五维度优化覆盖

| 维度 | 优化点数 | P1 数 | 关键优化 |
|------|---------|-------|---------|
| 网络请求层 | 4 | 1 | HTTP 响应缓存、预连接、getClient 缓存、AnalyzeUrl 复用 |
| 规则引擎 | 5 | 2 | Pattern 缓存、scriptCache/regexCache 全局共享、CSS/XPath 编译缓存 |
| 图片加载 | 3 | 0 | 解密缓存扩容、流式解密、双层缓存对齐 |
| 数据库 | 4 | 1 | (origin,sort) 索引、FTS 全文搜索、clearOld 事务、variableMap 优化 |
| 并发与内存 | 6 | 1 | 实例开销、bindings 复用、Semaphore 动态适配、日志开销 |

### 分三批实施策略

| 批次 | 优化点 | 收益/风险 | 实施项 |
|------|--------|----------|--------|
| 第一批 | 高收益低风险 | 收益高/风险低 | 2.1 Pattern 缓存 + 4.1 RssArticle 索引（2 项） |
| 第二批 | 高收益中风险 | 收益高/风险中 | 2.2+5.1 scriptCache/regexCache 全局共享 + 1.2 HTTP 响应缓存（2 项） |
| 第三批 | 中收益低风险 | 收益中/风险低 | 3.1 解密缓存扩容 + 1.4 预连接（2 项） |

## 技术根因（源码分析结论）

### 规则引擎瓶颈
- `AnalyzeByRegex.kt:11,34`：`Pattern.compile()` 每次调用都重新编译，6 并发协程各自编译相同 Pattern
- `AnalyzeRule.kt:81-85`：`scriptCache`/`regexCache`/`stringRuleCache` 都是 per-instance，每个列表项创建独立实例后 JS 重复编译
- `RssParserByRule.kt:92`：并行化后每个 item 创建独立 AnalyzeRule，6 个实例 × 3 个 Map 结构增加 GC 压力

### 数据库查询瓶颈
- `RssArticle.kt:10-13`：主键索引 `(origin, link, sort)`，但查询条件是 `(origin, sort)` 跳过 link，违反最左前缀原则
- 大文章量源（>1000 条）查询从 O(n) 退化，列表加载增加 50-200ms

### 网络请求重复
- `HttpHelper.kt:70-150`：`okHttpClient` 未配置 `Cache` 目录，同一 URL 重复请求走完整网络流程
- `Rss.kt:42-52`：`getArticlesAwait` 每次新建 `AnalyzeUrl`，重复执行 JS 与 header 解析

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Alternatives/Drawbacks/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR Y-Statement/Data Flow/File Changes/Landmines） |
| [tasks.md](./tasks.md) | 任务清单（三批分组 + 可选优化 + 验证 + 文档同步 + AOAdapt 日志） |

## 涉及文件

| 文件 | 变更类型 | 批次 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByRegex.kt` | 修改（Pattern 缓存） | 第一批 |
| `app/src/main/java/io/legado/app/data/entities/RssArticle.kt` | 修改（@Index 注解） | 第一批 |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` | 修改（scriptCache/regexCache 提升为 companion） | 第二批 |
| `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` | 修改（Cache 配置） | 第二批 |
| `app/src/main/java/io/legado/app/utils/ImageUtils.kt` | 修改（LruCache 扩容） | 第三批 |
| `app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt` | 修改（Migration） | 第一批 |
| `app/src/main/java/io/legado/app/data/AppDatabase.kt` | 修改（版本号+Migration） | 第一批 |
| `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 修改（预连接 async 并行） | 第三批 |

> 注：`RssParserByRule.kt`（Semaphore 动态适配）和 `AnalyzeRule.kt` 的 getElement 变更已降为可选优化，不列入核心实施文件。

## 状态标记

🔄 **设计中** — 待用户审核四文档后进入实施阶段

## 相关规范

- [改造过程日志记录规范](../../../project-rules/logging-during-refactoring.md)
- [版本交付同步规范](../../../project-rules/version-delivery-sync.md)
- [命名规范](../../../project-rules/naming_rules.md)
- [架构规范](../../../project-rules/architecture_rules.md)
- [异常规范](../../../project-rules/exception_rules.md)
- [延伸版本对比方法论](../../../project-rules/forks_comparison_methodology.md)
