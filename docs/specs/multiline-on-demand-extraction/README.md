# 多线路多集按需采集架构优化（multiline-on-demand-extraction）

> **状态**：🔄 开发中（核心源码改造已完成，待真机验收）
> **实施进度**：源码改造 9/10 完成（仅 SKILL references 陷阱文档待补充）
> **最后更新**：2026-07-24
> **创建日期**：2026-07-23
> **触发上下文**：用户在优化 MacCMS 模板视频订阅源过程中，发现 ruleContent JS 一次性采集所有线路所有集的播放页 URL（部分 JS 还尝试提取 m3u8），造成无端的网络请求和线程压力，且开发者编写复杂、出错率高。用户提出"按需采集"思路并要求用 OpenSpec 四文档规范深度分析。

## 功能概述

将 RSS 视频源（type=2）的多线路多集采集从"ruleContent JS 一次性全量采集"重构为"两阶段按需采集"架构：

- **第一阶段（ruleContent）**：只采集线路结构 + 集数列表 + 播放页 URL（不提取 m3u8）
- **第二阶段（playRssEpisode + VideoUrlExtractor）**：用户切换集数时按需采集真实视频流 URL（m3u8/mp4 等）

核心目标：让 ruleContent JS 编写更简单、加载更快，让内置播放器前置采集器（VideoUrlExtractor）承担视频流地址解析职责，职责分离后开发者只需关注"线路+集数"结构采集。

## 核心能力

| 编号 | 能力 | 核心问题 |
|------|------|---------|
| **R1** | 两阶段采集职责划分 | ruleContent 只返回播放页 URL 结构，m3u8 由播放器按需采集，消除 JS 内逐集请求播放页的性能损耗 |
| **R2** | 按需采集统一入口 | 在 VideoUrlExtractor 新增统一入口 `extractVideoUrlForEpisode`，整合 MacCMS 解析 + 网络抓包 + DOM 解析三层降级 |
| **R3** | playRssEpisode 降级采集扩展 | MacCMS 播放页解析失败时自动降级到 extractWithWebView 网络抓包，提升按需采集成功率 |
| **R4** | 已修改源码审查与简化 | 审查 switchToWebViewMode/retryExoPlayback/getOverlayControls/playRssEpisode 4 处修改，配合架构优化后评估是否可简化 |
| **R5** | Skill 文档规范更新 | 在 legado-source-creator SKILL.md 中明确多线路多集按需采集的标准写法，避免开发者继续编写全量采集 JS |

## 现状 vs 目标

| 维度 | 现状（治标） | 目标（治本） |
|------|------------|------------|
| ruleContent 职责 | 一次性返回所有线路所有集的 URL（含 m3u8 或播放页 URL） | 只返回线路+集数+播放页 URL，不提取 m3u8 |
| JS 执行耗时 | 多集时需逐集请求播放页 HTML（N 集 × M 线路个请求） | 只请求详情页一次，秒级返回线路+集数结构 |
| 开发者编写难度 | 需在 JS 里处理镜像站、player_aaaa、转义斜杠等 | 只需用 CSS/XPath/JS 提取线路 tab 和集数链接 |
| 视频流地址采集 | JS 内采集（部分）+ playRssEpisode MacCMS 解析（已修改） | 统一由 VideoUrlExtractor 按需采集（含 MacCMS + 网络抓包降级） |
| 失败降级 | ExoPlayer 报 3003 错误 → switchToWebViewMode 隐藏 UI | extractWithWebView 网络抓包兜底，提升采集成功率 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach（含 Alternatives Considered + Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions（ADR Y-Statement）/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 5 个 Section 的任务清单 + AOAdapt 日志 |

## 关键源码锚点

| 文件 | 角色 |
|------|------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | playRssEpisode 方法（按需采集入口） |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 视频URL提取器（采集能力核心） |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | RssSource 实体（ruleContent 字段） |
| `app/src/main/java/io/legado/app/data/entities/RssRoute.kt` | 线路实体 |
| `app/src/main/java/io/legado/app/data/entities/RssEpisode.kt` | 集数实体（含 url 字段） |
| `app/src/main/java/io/legado/app/model/rss/Rss.kt` | getContentAwait 方法（ruleContent 执行入口） |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | UI 交互（线路/集数切换回调） |
| `.trae/skills/legado-source-creator/SKILL.md` | Skill 文档（需更新多线路多集标准写法） |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/EditEntity.kt` | EditEntity ViewType 新增 textVideoOnly |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/EditAdapter.kt` | EditAdapter type 过滤逻辑 |
| `app/src/main/java/io/legado/app/data/DatabaseMigrations.kt` | migration_99_100 |

## 参考文档

- [tvbox-optimization 设计文档](../tvbox-optimization/design.md) - 影视仓 Spider 接口与两阶段架构参考
- [video-extractor-enhancement README](../video-extractor-enhancement/README.md) - VideoUrlExtractor 网络抓包能力增强（R5 已实施）
- [rss-video-player-enhancement](../rss-video-player-enhancement/) - RSS 视频播放器增强（前置 spec）

## 验证标准

- **Level 1 - 代码完成**：编译通过，VideoUrlExtractor.extractVideoUrlForEpisode 方法存在且非空壳
- **Level 2 - 功能验证**：ruleContent 只返回播放页 URL 时，用户切换集数能正确播放 m3u8
- **Level 3 - 场景验证**：MacCMS 模板站点（如奈飞中文网）真机回测通过，JS 规则简化后秒级返回线路+集数
