# 我的页头部统一（my-topbar-unify）

## 功能概述

将「我的」页（`MyFragment`）头部从传统 XML `TitleBar` 工具栏改造为与书架/订阅/发现三页同一套的 `MainTopBarView` 顶栏组件，使四个主 Tab 页头部观感完全一致，且「我的」页头部可被顶栏设置 / 主题设置 / 管理设置-样式管理（`TopBarConfig` + 主题 token + `TOP_BAR_CHANGED` 事件）全量管理（胶囊 / 圆角 / 壁纸 / 字号 / 搜索入口）。

**问题背景**：`MainActivity.refreshMainTopBars`（[MainActivity.kt#L697-L709](../../../app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L697-L709)）对 `MainTopBarView` 走 `refreshStyle()` 全量刷新，对 `TitleBar` 仅走 `refreshTopBarAppearance()`（只刷背景色）。因此「我的」页此前虽经 bugfix ③ 接入顶栏底色管理，但观感（胶囊标签 / 搜索入口 / 壁纸 / 圆角 / 字号）永远无法与其他三页一致——这就是"改了几遍不生效"的根因。

## 核心能力

1. **四页头部观感统一**：「我的」页改用 `MainTopBarView.Mode.MY`，与书架/订阅/发现同一组件、同一取色。
2. **主题全量管理**：顶栏设置变更（圆角/胶囊/壁纸/搜索入口/字号）经 `TOP_BAR_CHANGED` → `refreshMainTopBars` → `MainTopBarView.refreshStyle()` 自动刷新，无需逐属性适配。
3. **保留就地搜索**：「我的」页原有设置项就地过滤搜索（`view_search`）能力保留，改由顶栏搜索入口（`searchEntry`/`searchButton`）触发展开。

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求意图、范围、方案选型（含 Alternatives + Drawbacks）、需求清单、场景 |
| [design.md](./design.md) | 技术方案、ADR Y-Statement 决策记录、数据流、文件变更清单 |
| [tasks.md](./tasks.md) | 任务清单（X.Y 格式）+ AOAdapt 日志 |

## 状态标记

- 🔄 设计中（四文档已生成，等待用户审查）
