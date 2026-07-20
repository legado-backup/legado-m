# 订阅源统一搜索功能 (RSS Unified Search)

> **状态标记**：🔄 设计中
> **创建日期**：2026-07-20
> **功能代号**：rss-unified-search

## 功能概述

为订阅源（RSS源）添加统一的跨源搜索入口，类似书架顶部"搜索所有书源"的能力。用户在订阅源栏目（`RssFragment`）顶部搜索框输入关键词后，并发调用所有带 `searchUrl` 字段的订阅源进行搜索，将结果聚合去重后以列表形式展示。点击搜索结果可直接查看文章详情，并支持多源切换（同一文章来自多个订阅源时）。

## 核心能力

1. **跨源并发搜索**：并发调用所有启用的、带 `searchUrl` 的订阅源，复用书源搜索的线程池+超时+进度反馈机制
2. **结果聚合去重**：多源返回的相同文章按 `title + pubDate` 聚合，展示源数量（参考 `SearchBook.origins`）
3. **统一结果展示**：列表形式展示搜索结果，参考现有 `RssArticlesAdapter` 的展示样式
4. **详情页跳转**：点击搜索结果跳转 `ReadRss.readRss()`，按 type 分流到网页/图片/视频播放器
5. **多源切换换源**：详情页提供"换源"菜单，弹出 `ChangeRssArticleSourceDialog` 切换不同订阅源来源
6. **搜索历史**：记录用户搜索关键词（参考 `SearchKeyword` 表）
7. **搜索范围筛选**：支持按订阅源分组、类型筛选搜索范围（参考 `SearchScope`）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（架构/ADR决策/数据流/文件变更） |
| [tasks.md](./tasks.md) | 实施任务清单（按阶段分解） |

## 设计参考

本功能完整参考书架统一搜索图书功能（`SearchActivity` + `SearchViewModel` + `SearchModel`）的三层架构与并发调度机制，将"搜索所有书源"的能力平移到"搜索所有订阅源"。

## 关键技术决策

| 决策项 | 选定方案 | 备注 |
|--------|---------|------|
| 是否新建 Activity | ✅ 新建 `RssSearchActivity` | 模仿 `SearchActivity` |
| 数据模型 | ✅ 新建 `SearchRssArticle` 内存包装类 | 不持久化，避免污染 `rssArticles` 表 |
| 去重 Key | ✅ `title + pubDate` | 参考 `SearchBook` 的 `name + author` |
| 换源机制 | ✅ 新建 `ChangeRssArticleSourceDialog` | 参考 `ChangeBookSourceDialog` |
| 入口改造 | ✅ `RssFragment` 顶部搜索框 `onQueryTextSubmit` 跳转 | 保留 `onQueryTextChange` 按名称过滤 |
| 并发调度 | ✅ 复用 `Executors.newFixedThreadPool + mapParallelSafe` | 参考 `SearchModel` |
| 超时机制 | ✅ 30 秒（`withTimeout(30000L)`） | 对齐书源搜索 |
| 搜索历史 | ✅ 复用 `SearchKeyword` 表 + type 字段区分 | 避免新增表 |

## 状态时间线

- 2026-07-20 🔄 设计中：完成需求分析，生成四文档，等待用户审查设计方案
