# 主Tab头部搜索入口形态统一与主题取色对齐（topbar-search-entry-align）

## 功能概述

解决用户反馈的"发现 / 书架 / 订阅三个主 Tab 头部搜索入口形态不一致，有的还显示搜索输入框外观"问题：

- **现状差异根因（深度审查修正）**：`header-search-unify`（2026-08-26）只统一了书架/我的；**发现页固定开胶囊**（Out of Scope 遗留）；**订阅页初始化已是纯按钮（L947），是 `selectSource()` L604 选中源后重开胶囊**（状态覆盖冲突）。胶囊视觉像输入框，实际点击均打开新搜索页，但视觉误导用户。
- **关键布局互斥（审查新发现）**：regular 风格下胶囊与 titleSelect（标题选择器）互斥——胶囊当前承担"源名 hint + 搜索入口 + 压制 titleSelect"三重角色，关胶囊后 titleSelect（源选择入口）自动回归，属功能增强。
- **主题设置影响（规范对齐修正）**：主题设置存在「搜索框背景色」配置项，View 侧（TopBarSearchStyle）消费它；**Compose 侧（SettingsSearchBar，14 处调用点）用 M3 surfaceVariant 不消费且属既有 M3 派生色违规**（color.md §五禁令）——方案 = 消费 `ThemeUiPalette.searchFieldBackgroundColor` 槽位（规范取色链：自定义 key → background_menu 兜底）+ alpha 对齐 View 口径 + **清除 surfaceVariant**。
- **前端 UI 规范缺口与矛盾**：无"头部搜索入口形态"统一规范；且 `frontend-ui-standards.md` §1.4 旧条款"Compose 用 surfaceVariant"与新禁令自相矛盾（B9），需一并修订。

## 核心能力

- 三个主 Tab 头部搜索入口形态统一：**标题（titleSelect）+ 搜索按钮（+ 其他动作图标）**，不再出现"带输入框外观的胶囊"
- 发现页搜索按钮 → SearchActivity（新页面，带当前源 searchScope）；titleSelect 源选择菜单回归
- 订阅页统一为纯按钮（✅ 用户已裁决 2026-08-28）
- 主题取色对齐：Compose 14 处搜索框消费 palette 槽位随「主题设置-搜索框背景色」联动（alpha 对齐 View 口径），**同时清除 surfaceVariant 既有 M3 派生色违规**
- 前端 UI 规范补充"头部搜索入口形态 + 取色双端一致"条款并修订 §1.4 矛盾条款，防回潮

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：Technical Approach / ADR Y-Statement / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 实施任务清单（`- [ ] X.Y` 格式，含 AOAdapt 日志） |

## 状态标记

✅ 实施完成（2026-08-29；两轮深度审查 + 检查点 1 通过，部件 A/B/C/D 全部实施；编译门禁 `compileAppDebugKotlin` **BUILD SUCCESSFUL**（按用户裁决等待 config-needs-restart-fix 会话编译完成后复验通过）；静态验证全过；§6 真机 L2 验证按用户裁决归后续会话）
