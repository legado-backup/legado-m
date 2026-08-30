# 视频播放器上下滑动切换文章列表

> **状态**：🔄 设计中（待检查点1用户审查）
> **创建日期**：2026-07-11
> **所属项目**：Legado（阅读M）
> **前置 spec**：[douyin-style-video-player](../douyin-style-video-player/)（R3 抖音风格播放器）

## 功能概述

订阅源内置视频播放器支持**上下滑动切换文章列表**中的视频资源。用户在订阅源文章列表中点击视频文章进入播放器后，可通过上下滑动（ViewPager2 垂直滑动）切换到文章列表中上一个/下一个视频文章进行播放，无需返回列表重新选择。

## 核心能力

| 能力 | 说明 |
|------|------|
| **上下滑动切换文章** | ViewPager2 垂直滑动，每个 Fragment 对应一个 RssArticle（视频文章） |
| **集数选择器切换集数** | 文章内多集时，通过左下角集数选择器切换集数（不触发 ViewPager2 滑动） |
| **多线路支持** | 文章内多线路时，通过左下角线路选择器切换线路 |
| **向后兼容** | 从历史记录启动（无文章列表）→ 单 Fragment 旧逻辑；书源/单URL模式不受影响 |
| **异步加载** | 切换文章后异步加载该文章的视频信息（ruleContent/R5 自动抓取），加载完成通知 UI 更新 |

## 用户场景

```
用户浏览订阅源文章列表（含多个视频文章）
  → 点击某个视频文章
  → 进入内置视频播放器，播放该文章的视频
  → 上下滑动 → 切换到文章列表中上一个/下一个视频文章
  → 新文章视频自动加载播放
  → 文章内有多集时 → 左下角集数选择器切换集数
```

## 与 R3（douyin-style-video-player）的关系

| 维度 | R3（已完成） | 本 spec（新增） |
|------|-------------|----------------|
| **ViewPager2 数据源** | rssEpisodes（集数列表） | rssArticles（文章列表） |
| **上下滑动切换** | 切换集数 | 切换文章 |
| **集数切换方式** | ViewPager2 滑动 | 左下角集数选择器 |
| **每个 Fragment 对应** | 一集（RssEpisode） | 一篇文章（RssArticle） |

**关键变更**：R3 的 ViewPager2 基于 `rssEpisodes.size` 创建 Fragment（上下滑动切换集数）；本 spec 改为基于 `rssArticles.size` 创建 Fragment（上下滑动切换文章），集数切换改由左下角选择器承担。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |
