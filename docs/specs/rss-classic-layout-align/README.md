# 经典订阅布局管理与书架对齐修复（rss-classic-layout-align）

> 状态：✅ 已完成（2026-08-29 实施+编译门禁+真机验证收工，见项目记忆 rss-classic-layout-align 收工记录；状态补正于 2026-08-30，见 theme-rss-header-layout-sync F5）

## 功能概述

书架刚完成布局修复（[config-needs-restart-fix](../config-needs-restart-fix/README.md)）：布局配置受控入参即时生效、margin 驱动间距、封面 0.75、AppShapes.Chip 主题圆角、titleTypeface 字体、圆角卡片、`BOOKSHELF_STRUCTURE_CHANGED` 结构重建事件。本 spec 将经典订阅形态向该书架基线对齐，修掉以下 7 项已实核问题（子代理源码级核实，行号可信）：

| # | 问题 | 关键位置 |
|---|------|---------|
| P1 | `sourceMargin` 对订阅文件夹视图不生效：`contentPadding(12,8,12)+spacedBy(12,16)` 硬编码，书架已 margin 驱动（BookshelfScreen.kt:279/283-285） | [SourceFolderComposeGrid.kt:61-63](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderComposeGrid.kt#L61-L63) |
| P2 | `rssSortAscending` 升降序死配置：仅 PreferKey/AppConfig/RssFragment 三处引用，无 UI 写入口 | PreferKey.kt:310 / AppConfig.kt:2861-2865 / [RssFragment.kt:1362](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L1362) |
| P3 | rssSort=6「更新时间」排序不可达：弹框排序仅 6 项，RssFragment 已实现 6→lastUpdateTime 分支 | [SourceFolderConfigDialog.kt:252-259](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderConfigDialog.kt#L252-L259) / RssFragment.kt:1359 |
| P4 | showBookname 三重问题：①判断方向 `!= 1` 才显示，与书架 K7 修正后语义（1=显示）相反 ②订阅弹框无此配置入口 ③跨页不刷新（BOOKSHELF_STRUCTURE_CHANGED 仅书架两 Fragment 观察） | [SourceFolderComposeGrid.kt:87](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderComposeGrid.kt#L87) / 弹框 / RssFragment |
| P5 | 弹框「列表/紧凑列表」为摆设：sourceLayout 0/1 对订阅无列表实现（RssFragment.kt:1059-1060 用户决策固定卡片），仅 2-6 网格 + 0(自动) 有效 | SourceFolderConfigDialog.kt / RssFragment.kt:1059-1060 |
| P6 | item_rss.xml 视效与书架脱节：源图标 50x50 1:1 固定 radius=12dp 硬编码（书架 AppShapes.Chip 主题圆角）、书名 12sp 系统默认字体无 titleTypeface 无 minLines=2（书架有）、item 自身 padding 16dp 与 GridSpacingItemDecoration margin 双份叠加 | [item_rss.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/item_rss.xml) / RssAdapter |
| P7 | View 版文件夹渲染死代码：applyFolderView 无调用点，upFolderView 中 folderAdapter 双写数据浪费 | [RssFragment.kt:1072-1080](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L1072-L1080) |

> 另登记差异：订阅源图标语义为 1:1（原版如此），封面比例保持 1:1 不强制改书架 0.75。

## 核心能力

- **S1 文件夹 margin 参数化**：[SourceFolderComposeGrid](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderComposeGrid.kt) 新增 margin 参数（调用方 RssFragment `initFolderComposeView` 传 `AppConfig.sourceMargin`），contentPadding/spacedBy 全 margin 驱动（对齐 BookshelfScreen.kt:279-285 写法）
- **S2 订阅弹框补齐**：[SourceFolderConfigDialog](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderConfigDialog.kt) ①排序数组补第 7 项「更新时间」②新增升降序切换（写 `rssSortAscending`）③新增「书名显示」入口（写 `showBookname`，沿用书架 K7 语义 隐藏0/显示1/遮罩2——订阅场景遮罩无意义，可只给 显示/隐藏 两项但值对齐语义）④视图模式移除「列表/紧凑列表」2 个摆设项，保留 自动/Grid2-6
- **S3 showBookname 语义修正 + 跨页刷新**：SourceFolderComposeGrid.kt:87 判断改 `showBookname == 1` 显示；RssFragment 新增 `observeEvent(EventBus.BOOKSHELF_STRUCTURE_CHANGED)` → `applyView()+upFolderView()` 刷新（跨页同步书架侧书名偏好变化）
- **S4 源卡片视效对齐**：[item_rss.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/item_rss.xml) 圆角 12dp 改主题圆角（UiCorner.actionRadius 或等价，实施前读 FilletImageView API 确认 setter）、书名 tvName 补 titleTypeface + minLines=2（RssAdapter onBindViewHolder 或 XML）、去 item 自身 padding 16dp（间距单源由 GridSpacingItemDecoration margin 驱动）
- **S5 死代码清理**：删 applyFolderView 函数、upFolderView 中 folderAdapter 双写（FolderItem 数据类在 [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) 定义被 ComposeGrid 引用，类本身不删）
- **验证**：真机 L2 逐项验证 margin/排序/书名/视效即时生效，回归不破坏 modern 形态与文件夹交互

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach 含 Alternatives + Drawbacks / Requirements / Scenarios）

## 状态标记

- [x] 问题清单实核（P1-P7 子代理源码级核实，行号可信）
- [x] 修复方案设计（S1-S5）+ 双文档生成（README + spec）
- [ ] **检查点 1（二次审核）：用户审查本 spec**
- [ ] 修复实施
- [ ] 编译门禁
- [ ] 真机 L2 验证
- [ ] 用户验收 + 文档同步
