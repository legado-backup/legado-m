# 书源/订阅源架构差异分析与机制层互补优化

> 状态：🔄 开发中（V2 — 机制层互补，批次1：M6 SourceNetworkClient 实施中）
> 创建时间：2026-08-04
> 设计完成时间：2026-08-04 13:16:59（用户确认通过）
> V1 推翻原因：用户反馈"我要的不是添加字段，我要的是相互机制的互补，不期望相互添加字段"

## 功能概述

深入对比 Legado 项目中 BookSource（书源）与 RssSource（订阅源）的整体架构差异，识别双方各自独有的**机制层**优点，在**不影响现有主体功能、不增加实体字段、不需要数据库迁移**的前提下，抽取 6 个共享机制组件，让两类源共享同一套工程能力（并发/过滤/缓存/预连接/WebView/网络层），实现真正的机制互补。

## V1 vs V2 方案对比

| 维度 | V1（字段借鉴，已推翻） | V2（机制互补，选定） |
|------|----------------------|---------------------|
| 实体字段 | 增加 16 个字段 | **零字段增加** |
| 数据库迁移 | v89→v90 AutoMigration | **不需要迁移** |
| 代码复用 | 字段复制，逻辑仍分散 | 6 个共享组件，逻辑统一 |
| 维护成本 | 字段散落各处 | 机制集中在组件 |
| 可扩展性 | 新源类型需复制字段 | 新源类型直接调用组件 |
| 风险 | 字段类型/默认值/迁移 | 机制抽取可能影响现有调用（需测试） |

## 6 个共享机制组件

| 组件 | 机制互补点 | 利用现有字段 | 不增字段 |
|------|-----------|-------------|---------|
| **M1 SourceConcurrencyController** | 统一并发控制 | BookSource.concurrentRate / RssSource.parseConcurrency | ✅ |
| **M2 SourceContentFilter** | 统一正文URL过滤 | RssSource.contentWhitelist/contentBlacklist + AppConfig 全局 | ✅ |
| **M3 SourceCacheManager** | 统一缓存策略 | RssSource.preload/cacheFirst + AppConfig 全局 | ✅ |
| **M4 SourcePreconnectHelper** | 统一预连接 | 抽取 Rss.kt F-P1-F 实现复用 | ✅ |
| **M5 SourceWebViewController** | 统一WebView控制 | RssSource WebView 字段 + AppConfig 全局 | ✅ |
| **M6 SourceNetworkClient** | 统一网络请求 | 抽取 WebBook/Rss 重复的 loginCheckJs+checkRedirect 模式 | ✅ |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach（含 Alternatives Considered + Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions（ADR Y-Statement）/Data Flow/File Changes |
| [tasks.md](./tasks.md) | `- [ ] X.Y` 格式任务清单 + AOAdapt 日志 |

## 状态标记

🔄 开发中 — 批次1：M6 SourceNetworkClient 实施中（用户确认通过 2026-08-04 13:16:59）
