# 主Tab头部搜索入口统一（header-search-unify）

## 功能概述

统一书架 / 我的 / 订阅三个主 Tab 的头部搜索入口形态，以**订阅页为基准**：

- **订阅页（RssFragment）**：头部只显示搜索按钮（searchButton），点击后打开独立搜索页（RssSearchActivity）—— 已达标，本次不改动
- **书架页（BaseBookshelfFragment，style1+style2）**：regular 顶栏风格下头部显示一个 searchEntry 胶囊"搜索框"，但**未绑定任何点击事件（点击无响应）**，同时右侧已有可用的 searchButton（点击打开 SearchActivity 新页搜索）。本次移除无效 searchEntry 胶囊，仅保留 searchButton
- **我的页面（MyFragment）**：头部同样显示 searchEntry 胶囊 + searchButton，两者点击均**就地展开设置项搜索框**（view_search）。本次移除 searchEntry 胶囊，仅保留 searchButton 入口

## 核心能力

- 三个主 Tab 头部搜索入口形态统一：标题 + 搜索按钮（+ 其他动作图标），不再出现"点了没反应的搜索框"
- 书架搜索按钮 → 打开书籍搜索页（SearchActivity，新页面）
- 我的页面搜索按钮 → 打开**全屏设置搜索页**（SettingsSearchActivity，新页面，搜索框自动聚焦/实时过滤设置项）
- 主题零破坏：新搜索页复用 `LegadoTheme` + `MySettingsScreen` 既有主题体系，无孤儿样式

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：Technical Approach / ADR Y-Statement / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 实施任务清单（`- [ ] X.Y` 格式，含 AOAdapt 日志） |

## 状态标记

✅ 设计完成（2026-08-26 检查点1 通过：自审补 AD-05 状态刷新 + tasks 3.5/3.6 增补；发现页 searchEntry 为有效宿主默认不改）