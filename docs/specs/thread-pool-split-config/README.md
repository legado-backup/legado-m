# 书源线程池拆分与自定义配置

> 状态：🔄 设计中
> 创建日期：2026-07-25
> 功能代号：thread-pool-split-config

## 功能概述

当前 Legado 项目中书源搜索、更新、缓存等业务共用一个统一的线程数配置参数 `AppConfig.threadCount`（默认 32），导致用户无法针对不同业务场景分别调优并发数。本功能将线程池配置拆分为两个独立的可自定义配置项：

- **搜索线程数**（`searchThreadCount`）：控制书源/RSS 搜索、换源、换封面、漫画搜索、阅读页搜索、书架搜索、发现页探索、书源/RSS 源校验、JS 扩展并发等搜索类业务
- **更新和缓存线程数**（`updateCacheThreadCount`）：控制书籍目录更新、缓存下载、缓存正文下载、书籍并发处理、章节列表采集、正文内容采集、WebView 池容量等更新与缓存类业务

## 核心能力

1. **配置层拆分**：在 `AppConfig` 中新增 `searchThreadCount` 和 `updateCacheThreadCount` 两个独立配置项
2. **业务层归类**：将 30+ 处使用 `threadCount` 的业务点按场景归类到搜索类或更新+缓存类
3. **UI 层自定义**：在"其他设置"中新增两个独立的线程数配置入口（NumberPickerDialog）
4. **配置变更实时生效**：用户修改配置后通过 LiveEventBus 通知业务层重建线程池
5. **兼容性保障**：保留旧 `threadCount` 配置项作为备份/恢复兼容字段，老用户升级时自动迁移默认值

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（架构决策 ADR/数据流/文件变更） |
| [tasks.md](./tasks.md) | 任务清单（按 X.Y 格式编排） |

## 当前调研结论

### 现状（共用一个配置参数）

| 维度 | 现状 |
|------|------|
| 配置参数 | `AppConfig.threadCount`（唯一，默认 32） |
| 配置入口 | `OtherConfigFragment.kt` → `pref_config_other.xml` |
| 线程池实例 | 12+ 个独立创建的 `Executors.newFixedThreadPool` 实例（非共享） |
| 使用点数量 | 30+ 处直接引用 `AppConfig.threadCount` 或 `PreferKey.threadCount` |
| MAX_THREAD 硬上限 | 部分业务点仍保留 `min(threadCount, AppConst.MAX_THREAD)` 上限 |

### 改造目标

- 搜索类业务统一使用 `searchThreadCount`（无 MAX_THREAD 上限，由用户自负责）
- 更新+缓存类业务统一使用 `updateCacheThreadCount`
- 两个配置均可在"其他设置"中独立调整
- 配置变更后无需重启 App 即可生效（通过事件总线通知重建）

## 影响范围

- **配置层**：`AppConfig.kt`、`PreferKey.kt`、`BackupConfig.kt`
- **UI 层**：`OtherConfigFragment.kt`、`pref_config_other.xml`、`strings.xml`
- **业务层**：搜索类 11 个文件 + 更新+缓存类 7 个文件
- **事件总线**：`MainActivity.kt`、`MainViewModel.kt`
