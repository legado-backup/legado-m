# 视频播放器多线路多集状态残留修复

> 状态：**开发中**（设计完成 → 开发中）

## 功能概述

修复内置播放器（沉浸式 ViewPager2 与传统布局）在用户**主动退出后重新进入**新视频时，
左下角多线路/多集选择器残留**上一会话**线路/集数信息的问题。

## 变更点

- **`VideoPlay.initSource`**（新会话唯一入口）：开头统一重置
  `rssRoutes`/`rssEpisodes`/`rssRouteIndex`/`rssEpisodeIndex` 四个字段，
  由后续解析链路（`startPlay` 多线路分支 / 书源卷章映射 / R5 多 URL）按新视频数据重建。
- 沉浸式（`VideoFragment.initRouteSelector/initEpisodeSelector`）与
  传统布局（`VideoPlayerActivity.bindLegacyInfo`）共用 `VideoPlay` 单例数据源，
  单点修复两模式同受益。

## 不涉及

- 不改 UI 组件、不改书源/订阅源规则解析逻辑、不改数据流架构
- 不影响悬浮窗恢复（`isNew=false` 不经过 `initSource`）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求与场景 |
| [tasks.md](./tasks.md) | 任务清单 |
