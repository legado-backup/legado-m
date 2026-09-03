# README.md — video-playlist-continuity

> ⚠️ **书源侧方案已被 [video-booksource-align-rss](../video-booksource-align-rss/README.md) 取代（2026-09-03）**：
> 书源多集 ViewPager 多页+占位页+双索引镜像在实施中反复出错（直链地址不正确/标题错乱/占位页卡死），
> 用户裁决改为"书源视频单页化+列表驱动上滑+公共采集链"。本 spec 的 **VideoPlaylistHolder 列表注入机制
> （5 入口）与订阅源侧行为继续有效**；书源侧的 VideoPlaybackQueue 接入/占位页/多页分派已删除（组件文件保留）。

## 功能概述

视频播放行为统一化（用户裁决"行为一致性！统一！"）：无论视频书源还是视频订阅源——
- 多集：下滑 = 下一集
- 单集，或下滑到多集最后一集：**下滑 = 播放列表中的下一个视频**
- 上滑 = 上一集/上一个视频（订阅源文章模式天然支持；书源跨视频上滑回退本期不做）

## 核心能力

1. **列表注入**：所有"视频列表呈现入口"在点入播放器时把当前列表+当前索引注入播放器（书源：发现分类列表/搜索/全局搜索；订阅源分类列表/统一搜索已具备）
2. **书源跨视频续播**：播放器内最后一集下滑触发"加载列表下一个视频"（getChapterListAwait 即时加载目录 → 整体切换 → 播第一集），换源式切换（对齐既有线路切换重建模式）
3. **订阅源现状确认**：分类列表（RssArticlesFragment 已传列表+分页上下文）/统一搜索已具备连续性，本期不改动；收藏/历史单篇直达无列表上下文，保持单集行为（合理）
4. **预加载兜底**：延续 video-booksource-multiroute 的 initSource 即时加载修复（目录未就绪时同步加载）

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术方案/ADR/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |

## 状态标记

🔄 设计中
