# 书架下拉刷新转圈不消失 + 书架顶栏标题字号不统一修复

> 状态：✅ 实施完成（2026-08-29 编译门禁+真机核验通过，待验收）

## 功能概述

用户反馈两个书架页面 UI 问题：

1. **下拉刷新转圈一直不消失**：书架页下拉触发刷新后，转圈指示器长时间滞留不收回。根因为动画复位与真实刷新完成完全脱钩（唯一复位点是 `delay(1000)` 盲定时），且复位协程挂在 Fragment 级 `lifecycleScope`，页面销毁/回收时协程被取消导致 `refreshing` 冻结在 true；叠加 material3 1.3.2 受控 `PullToRefreshBox` 已知指示器竞态。
2. **书架顶栏标题字号偏大且硬编码**：书架左上角标题 24sp，发现/订阅/我的等页面均为 20sp。字号在 `MainTopBarView.kt` 中按 Mode 硬编码（`if (mode == Mode.BOOKSHELF) 24f else 20f`），不走 `MaterialTheme.typography`，也不受 `TopBarConfig` 主题体系管理。

## 核心能力（修复目标）

- 书架下拉刷新动画复位挂钩真实刷新完成（MainViewModel 暴露 upToc 队列空闲状态），保留兜底超时
- 复位协程迁移至 `viewLifecycleOwner.lifecycleScope` + 单一 Job 管理，消除销毁冻结
- 全顶栏族标题排版归位 `titleLarge` 基线（20sp/Medium）：书架去 24sp 特判、ConfigTopBar（备份与恢复等设置子页）去 SemiBold 字重覆写、AppManagementScaffold（书源/订阅源/替换规则/订阅规则/书架分组 5 页）19sp/SemiBold → 20sp/Medium

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach（含替代方案与缺点）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：技术方案 / 架构决策（ADR Y-Statement）/ 数据流 / 文件变更 |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式）+ AOAdapt 日志 |

## 需求来源

用户 2026-08-29 反馈：书架下拉刷新转圈一直不消失；书架顶栏标题字号明显大于发现/订阅/我的页，疑似硬编码且未纳入主题体系。
