# 订阅源视频播放器增强（rss-video-player-enhancement）

> **状态**：🔄 检查点3 R5 需求追加（R1-R4 已实施完成，R5 待审核）
> **创建日期**：2026-07-10
> **前置 spec**：source-layout-detail-refinement（已完成）

## 功能概述

针对订阅源（RssSource type=2）内置视频播放器的 5 项增强需求，解决用户实际使用中发现的"多集无法选择""部分 m3u8 播放失败无提示""布局不如旧 WebView 方案丰富""日志异常""内容规则空时无法自动抓取视频链接"等问题。

## 核心能力

| 编号 | 需求 | 核心问题 |
|------|------|---------|
| **R1** | 多集选择播放 | 订阅源内置播放器只取单 URL，不支持多集；需扩展内容规则支持返回多集列表 |
| **R2** | m3u8 播放失败分析+调试日志 | 部分 m3u8 地址能播放部分不能，且无任何错误提示；需在播放页加调试日志显示失败原因 |
| **R3** | 学习旧订阅源布局样式 | 用户将提供旧 WebView 方案的订阅源内容规则，需学习其布局元素并移植到内置播放器 |
| **R4** | 使用日志异常分析优化 | 基于用户使用日志（temp\tmp\Downloadslogs.(2)..zip）深度分析异常并优化 |
| **R5** | 自动视频链接抓取 | ruleContent 为空且 type=2 时直接用文章 URL 播放必然失败；需自动从文章 HTML 抓取视频链接（正则+video标签+Meta+JS变量四种方法） |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |

## 关键源码锚点

| 文件 | 角色 |
|------|------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 视频播放管理单例，RssSource 分支只取单 URL；R5 集成点：ruleContent.isNullOrBlank() 分支 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | ExoPlayer 底层封装，无 onPlayerError 回调 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` | ExoPlayer 管理器，错误只记 AppLog |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 内置播放器 Activity，多集 UI 只对书源生效 |
| `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` | 订阅源阅读路由，type=2 走 VideoPlayerActivity |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | 订阅源实体，只有 type 字段无 videoType |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | **R5 新增**：视频URL提取器，四种方法综合提取去重 |
| `app/src/main/java/io/legado/app/model/rss/Rss.kt` | R5 复用模式参考：getContentAwait 获取文章 HTML |
