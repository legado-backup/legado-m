# 书源视频对标订阅源——单页化+列表驱动上滑+公共采集链组件

> 状态：✅ 已实施（2026-09-03）｜真机验证：S1 直链起播/S2 上滑下一影片+下滑回退/S3 边界/S4 切线路 L0 直链/S5 订阅源文章滑动链通过；订阅源多线路多集链（Pipeline.playEpisode）经代码等价性核验，真机复验受源站分类加载失败阻塞

## 功能概述

书源视频播放架构重构：放弃"书源视频做多集 ViewPager 多页"的原方案，直接对标订阅源已验证稳定的播放模型——

- **单页播放**：书源视频页面退化为单页播放（1 页 = 当前影片），不再承载多集分页；
- **列表驱动上滑**：上滑 = 同列表下一个影片（由书源列表数据直接驱动），集数/线路切换只通过选集器与详情抽屉完成；
- **公共采集链组件**：抽取 `VideoPlaybackPipeline` 公共采集链组件，书源链与订阅源链共用同一套直链快速路径 / header 合并 / 嗅探兜底逻辑，根治双采集链漂移。

本 spec 同时根治三类反复出现的真机问题：双采集链漂移、双索引失步、书源自建播放队列卡死。

## 核心能力

1. **单页播放**：书源视频单页承载当前影片播放，1 页 = 1 影片，移除书源侧多集 ViewPager 分页模型；
2. **列表驱动上滑**：上滑手势 = 切换到同列表下一个影片，由数据列表直接驱动，不再依赖自建播放队列（VideoPlaybackQueue）与占位页；
3. **公共采集链**：抽取 VideoPlaybackPipeline 组件，统一直链快速路径、header 合并、嗅探兜底，书源/订阅源双链合一；
4. **标题单一权威**：影片/集数标题收敛为单一权威数据源，消除 composeTitle / tv_video_title / 详情抽屉三处数据源漂移；
5. **入口注入收敛**：书架/发现/搜索等列表入口的播放数据注入收敛为统一路径，替代 VideoPlaylistHolder 多入口分散注入。

## 设计背景

前置 spec `video-playlist-continuity` 实施后真机反复出问题，复盘定位 4 个架构病根：

1. **双采集链漂移**：书源链（VideoPlay.startPlayBookChapter → WebBook.getContent → 嗅探）与订阅源链（playRssEpisode → VideoUrlExtractor）并行实现，直链快速路径 / header 合并 / 嗅探兜底各自漂移（实锤：直链线路 m3u8 被 ruleContent 请求产出整段清单文本当 URL 播放失败；书源缺 directRouteIdx 直链优选）；
2. **双索引失步**：书源模式强行映射订阅源模型（rssRoutes / rssEpisodes），chapterInVolumeIndex 与 rssEpisodeIndex 镜像同步、标题三处数据源（composeTitle / tv_video_title / 详情抽屉）、事件链多个覆盖点 → 标题 / 详情 / 集数选中反复错乱；
3. **书源自建队列脆弱**：VideoPlaybackQueue 队列 + 占位页 + generation 守卫，上滑跨影片卡死 / 播放失败（generation 校验恒不匹配导致事件被静默丢弃，实锤）；
4. **入口注入分散**：书架 / 发现 / 搜索列表多处注入 VideoPlaylistHolder，覆盖不全导致部分入口上滑行为不一致。

**用户裁决（2026-09-03）**：书源视频不做多集 ViewPager 多页，直接对标订阅源已验证稳定的模型——书源视频单页播放（1 页 = 当前影片），集数切换只走选择器 / 详情抽屉，上滑 = 同列表下一个影片（列表驱动），抽公共采集链组件。

## 文档索引

- [spec.md](./spec.md) - 需求规格（Intent/Scope/Approach/Requirements/Scenarios）
- [design.md](./design.md) - 技术设计（ADR Y-Statement/Data Flow/File Changes）
- [tasks.md](./tasks.md) - 任务清单

## 关联 Spec

- [video-playlist-continuity](../video-playlist-continuity/README.md) - 前置 spec（书源侧方案由本 spec 取代，订阅源侧多集分页改造继续有效）
- [video-booksource-multiroute](../video-booksource-multiroute/README.md) - 前置 spec（多线路多集映射模型保留）
