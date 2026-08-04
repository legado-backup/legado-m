# P0 核心 Bug 修复（第一轮）

> **状态**：✅ 实施完成（代码 38/49 勾选；余 E2E 自动化测试 3.3-3.8 与交付 5.x 待跑）
> **创建日期**：2026-07-09
> **关联审查报告**：[yesterday-changes-deep-audit/audit-report.md](../yesterday-changes-deep-audit/audit-report.md)
> **修复范围**：P0 核心 bug 4 项（M-01/M-02 + F-01 + V-01 + C-01）

---

## 功能概述

修复 2026-07-08 改动中发现的 4 项 P0 核心 bug，这些 bug 直接影响核心功能可用性。修复后须通过 E2E 自动化测试（MEmu 模拟器）验证。

## P0 Bug 清单

| 编号 | 严重度 | 问题 | 影响 |
|------|--------|------|------|
| **M-01** | 🔴高 | BookSource compact/grid 选择模式失效 | 紧凑/网格模式下无法批量操作 |
| **M-02** | 🔴高 | RssSource compact/grid 选择模式失效 | 同上 |
| **F-01** | 🔴高 | 搜索框回填 "group:$group"（Bug 9） | 用户输入名称后归类信息丢失 |
| **V-01** | 🔴高 | 视频换集强制重新静音 | 每次换集都要重新取消静音 |
| **C-01** | 🔴高 | sourceSort 配置项耦合 | 书源和订阅源排序互相串扰 |

## 修复策略

### M-01/M-02：给 compact/grid adapter 添加 selection 机制
- 给 BookSourceAdapterCompact/Grid、RssSourceAdapterCompact/Grid 添加 selected 集合 + selectAll + revertSelection + selection 属性 + dragSelectCallback
- Activity 内 `adapter` 引用改为 `currentAdapter()` 动态获取（根据 AppConfig.sourceLayout 返回当前显示的 adapter）
- 注：P2 的 M-10 会提取 BaseSourceAdapter 基类统一这些逻辑，P0 先保证功能可用

### F-01：引入 currentFilter 解耦 searchView
- RssFragment/ExploreFragment 添加 currentFilter 字段（group: String?）
- onFolderClick 设置 currentFilter.group，不回填 searchView
- upRssFlowJob 用 currentFilter + searchKey 组合查询（启用 DAO 已有的 flowGroupSearchExact/flowByTypeSearch）

### V-01：onPrepared 用 isMuted 而非 muteOnStart
- VideoPlayer.kt onPrepared 改为 `setNeedMute(isMuted)`，跟随用户当前静音状态
- initView 中 isMuted 初始化保持 `isMuted = VideoPlay.muteOnStart`（仅首次播放应用 muteOnStart）

### C-01：拆分 sourceSort 为 bookSourceSort + rssSort
- PreferKey/AppConfig 中 sourceSort 改为 bookSourceSort（书源专用）
- 启用已有的 rssSort/rssSortAscending（订阅源专用，C-05 死代码激活）
- BookSourceActivity 菜单用 bookSourceSort，RssSourceActivity 菜单用 rssSort

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/ADR/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |

## 验证标准

- [ ] 编译通过（`./gradlew assembleRelease`）
- [ ] E2E 测试通过（MEmu 模拟器安装 APK + 跑用例 + 日志无 FATAL EXCEPTION）
- [ ] 4 项 P0 bug 场景手动验证通过
