# 视频播放器多线路多集状态残留修复 — Spec

## Intent

消除内置播放器会话切换时多线路/多集数据的**跨会话残留**：
用户播放完多线路多集视频后主动退出，再进入无多线路多集（或另一多线路多集）视频时，
左下角选择器必须正确初始化为**新视频**的数据（无数据时隐藏），不再显示上一会话残留信息。

## Scope

- **in**：`VideoPlay` 单例会话状态字段的初始化时机；沉浸式与传统布局共用数据源的修复
- **out**：规则解析逻辑、UI 组件渲染、播放器内核

## Approach（精简）

**Selected Approach**：在 `VideoPlay.initSource`（所有 `isNew=true` 新会话的必经入口）
开头清空 `rssRoutes`/`rssEpisodes`/`rssRouteIndex`/`rssEpisodeIndex`，由既有解析链路按新视频重建。

落地理由：
- `initSource` 覆盖全部新会话入口（Activity 首次进入 / onNewIntent / Service 新播放），单点兜底
- 悬浮窗恢复（`isNew=false`）不经过 `initSource`，当前会话线路/集数状态不受影响
- 幂等：`resetForNewIntent`/`releaseAllVideos` 已清空，再清一次无副作用

**Alternatives Considered**：

| 方案 | 否决理由 |
|------|---------|
| 仅在 `finish()` 补清 | 遗漏系统回收/书源退出等路径；且 `initSource` 兜底后冗余 |
| `startPlay` 单 URL 分支清空 | 只覆盖单 URL 场景，R5 抓取失败/解析中窗口仍残留 |

**Drawbacks**：无。清空后解析完成前左下角短暂隐藏属正常加载过程，
`UP_VIDEO_INFO` 事件驱动 `updateEpisodeSelector` 会按新数据重新渲染。

## Requirements

### Requirement: 新会话初始化时重置线路/集数状态

- **WHEN** 用户以 `isNew=true` 方式进入播放器（`VideoPlay.initSource` 被调用）
- **THEN** `rssRoutes`/`rssEpisodes` 置 null，`rssRouteIndex`/`rssEpisodeIndex` 置 0

### Requirement: 多线路多集数据由新视频解析链路重建

- **WHEN** 新视频为多线路多集（订阅源 ruleRoutes/ruleEpisodes、ruleContent 多线路、
  R5 多 URL、书源卷章映射）
- **THEN** 解析完成后 `rssRoutes`/`rssEpisodes` 被新数据覆盖，左下角显示新线路/新集数

### Requirement: 无多线路多集的视频左下角选择器隐藏

- **WHEN** 新视频为单 URL / 无多线路多集规则，且清空后无解析链路填充
- **THEN** `rssRoutes`/`rssEpisodes` 保持 null，线路/集数选择器隐藏，仅显示标题

### Requirement: 悬浮窗恢复不清空当前会话状态

- **WHEN** 从悬浮窗恢复播放会话（`isNew=false`，不调用 `initSource`）
- **THEN** 当前会话 `rssRoutes`/`rssEpisodes` 保持原值，不受清空逻辑影响

## Scenarios

### Scenario: 多线路多集 → 退出 → 进入单 URL 视频

- **WHEN** 用户播放多线路多集视频 A 后主动退出，再进入单 URL 视频 B
- **THEN** 视频 B 左下角不再显示视频 A 的线路/集数，选择器隐藏

### Scenario: 多线路多集 → 退出 → 进入另一多线路多集视频

- **WHEN** 用户播放多线路多集视频 A 后主动退出，再进入多线路多集视频 C
- **THEN** 视频 C 左下角显示视频 C 自己的线路/集数（解析期间短暂隐藏，完成后刷新）

### Scenario: 传统布局同修复

- **WHEN** 用户以传统布局（legacy mode）播放多线路多集视频后退出，再进入无多线路多集视频
- **THEN** 信息区不显示上一会话残留的线路/集数列表
