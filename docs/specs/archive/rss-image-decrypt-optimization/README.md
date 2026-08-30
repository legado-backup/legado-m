# 订阅源图片解密优化

## 功能概述

针对订阅源（RssSource）中 `ruleImage` 字段为 JS 脚本且内部执行图片解密的场景（典型代表：91大事件订阅源），修复调试日志输出导致软件崩溃的问题，并优化带解密图片的订阅源列表加载速度。

### 核心问题

| 编号 | 问题 | 严重度 | 用户影响 |
|------|------|--------|---------|
| P0 | 调试功能输出解密后 base64 图片数据导致软件崩溃 | 致命 | 调试功能不可用 |
| P1-1 | 带解密图片的订阅源列表加载明显变慢 | 体验差 | 20条目列表加载 4~40 秒 |
| P1-2 | data URI 无法被 Glide 磁盘缓存，列表刷新重新解密 | 性能 | 滚动/刷新卡顿 |

## 核心能力

### P0 调试输出截断防崩溃
- 对 `data:image/...;base64,...` 格式的 data URI 在调试输出前截断
- 调试日志函数入口加全局截断保护（>2000 字符自动截断）
- 防止 OOM / ANR / TransactionTooLargeException

### P1 列表加载提速
- **并行化**：RssParserByRule 的 for 循环改为 `async{}.awaitAll()` 并行执行
- **限流保护**：Semaphore(6) 限流，避免 AnalyzeRule 非线程安全 + 网络压力
- **实例隔离**：每个 item 创建独立 AnalyzeRule 实例
- **结果缓存**：JS 内部使用 CacheManager 缓存解密结果，跨会话复用

## 技术根因（源码分析结论）

### 调试崩溃根因
- `RssParserByRule.kt:128`：完整输出 data URI（70KB+）到调试日志
- `Debug.kt:33-71`：log 函数无截断保护，70KB 字符串原样传给 UI
- `RssSourceDebugAdapter.kt:37`：TextView 直接显示 70KB 字符串 → OOM/ANR

### 列表慢根因
- `RssParserByRule.kt:74`：for 循环串行执行
- JS 内 `OkHttpClient.newCall(req).execute()` 同步阻塞
- 单张图片 200ms~2s，20 条目列表 4~40 秒
- data URI 无法被 Glide 磁盘缓存，列表刷新重新解密

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（6 章节 + AOAdapt 日志） |

## 涉及文件

| 文件 | 变更类型 |
|------|---------|
| `app/src/main/java/io/legado/app/model/analyzeRule/RssParserByRule.kt` | 修改（截断+并行化） |
| `app/src/main/java/io/legado/app/help/Debug.kt` | 修改（全局截断） |
| `app/src/main/java/io/legado/app/AppLog.kt` | 修改（putEntry 截断） |
| 91大事件订阅源 JS（ruleImage 字段） | 修改（CacheManager 缓存） |

## 状态标记

🔄 **设计中** — 待用户审核四文档后进入实施阶段

## 相关规范

- [改造过程日志记录规范](../../../project-rules/logging-during-refactoring.md)
- [版本交付同步规范](../../../project-rules/version-delivery-sync.md)
- [命名规范](../../../project-rules/naming_rules.md)
