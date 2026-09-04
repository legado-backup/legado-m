# 管理页样式统一与交互回归修复（ui-theme-governance-followup）

> 状态：✅ 设计完成（🔄 开发中）
> 创建：2026-09-03
> 前置：ui-theme-governance-polish（090318 包真机验证发现的问题，本 spec 为补充性全量排查修复）
> 类型：Bug 修复 + UI 统一 + 交互回归修复

## 功能概述

090318 真机走查暴露 5 类问题，四路探索已完成根因定位：

| # | 问题 | 根因（已实锤） |
|---|------|---------------|
| F1 | 发现页视频上滑误报"已是最后一个视频" | 并行 revert（450e60bf8）把 5 处 `VideoPlaylistHolder.set` 注入移出 master，消费链 `neighborOf`（VideoPlay.kt:434）仍在→队列永空必误报 |
| F2 | 书架下滑误触发刷新/上滑不到顶/切页才恢复 | PullToRefreshBox 无回顶条件+loading 条件分支致 LazyGrid 整体重组滚动归零+旧版 ViewPager 双轴无锁定+刷新期数据重排 |
| F3 | 发现页头部标签点击整体刷新+向下按钮透明闪烁 | MainTopBarView LayoutTransition APPEARING/DISAPPEARING 未禁用（alpha 副作用）+updateFilterBarsVisibility 非幂等+RoundedTagBarView notifyDataSetChanged 全量重绑 |
| F4 | 管理页透明度只有书源/订阅源管理生效+全透明灰蒙蒙 | decorView tint alpha 机制性无效（不透明 windowBackground 无下层可透出=灰蒙蒙）；主题/TopBar/BookInfo 等管理页 Compose 根层 `Surface(color=page)` 不透明全屏遮死 tint |
| F5 | TxtTocRule 等子页面顶栏白色遮罩+列表样式不统一 | 透明状态栏白带（windowBackground）与 primaryColor 顶栏断层；管理族 24 页仅 1 页接入 AppManagementScaffold（GlassTopAppBar 族 11/View TitleBar+Compose 9/View RecyclerView 4） |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach 三要素/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/ADR/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |
| [red-team-report.md](./red-team-report.md) | 五轮红队审查 |

## 状态流转

- 🔄 设计中（当前）
