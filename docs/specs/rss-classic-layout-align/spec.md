# spec.md — 经典订阅布局管理与书架对齐修复（rss-classic-layout-align）

## Intent

书架布局基线（[config-needs-restart-fix](../config-needs-restart-fix/README.md)：受控入参即时生效、margin 驱动间距、AppShapes.Chip 主题圆角、titleTypeface 字体、`BOOKSHELF_STRUCTURE_CHANGED` 结构重建事件）已建立，但经典订阅形态尚未对齐：文件夹视图 margin 失效、升降序/「更新时间」排序不可达、书名语义错位且跨页不刷新、源卡片视效脱节、弹框含摆设项与死代码。目标：经典订阅的布局配置即时生效、配置语义与书架统一、源卡片视效收敛到书架基线。

## Scope

### In（本次实现）

- **S1 文件夹 margin 参数化**：SourceFolderComposeGrid 新增 margin 参数，contentPadding/spacedBy 全 margin 驱动（调用方 RssFragment `initFolderComposeView` 传 `AppConfig.sourceMargin`）
- **S2 弹框补齐**：SourceFolderConfigDialog 排序数组补第 7 项「更新时间」+ 新增升降序切换（写 `rssSortAscending`）+ 新增「书名显示」入口（写 `showBookname`，K7 语义：隐藏0/显示1/遮罩2，订阅场景遮罩无意义可只给 显示/隐藏 两项但值对齐语义）+ 移除「列表/紧凑列表」2 个摆设项（保留 自动/Grid2-6）
- **S3 showBookname 修正**：SourceFolderComposeGrid.kt:87 判断方向改 `showBookname == 1` 显示；RssFragment 新增 `observeEvent(EventBus.BOOKSHELF_STRUCTURE_CHANGED)` → `applyView()+upFolderView()` 跨页刷新
- **S4 源卡片视效对齐**：item_rss.xml 圆角 12dp 改主题圆角（UiCorner.actionRadius 或等价，需读 FilletImageView API 确认 setter）、书名 tvName 补 titleTypeface + minLines=2（RssAdapter onBindViewHolder 或 XML）、去 item 自身 padding 16dp（间距单源由 GridSpacingItemDecoration margin 驱动）
- **S5 死代码清理**：删 applyFolderView 函数、upFolderView 中 folderAdapter 双写（FolderItem 数据类在 SourceFolderAdapter.kt 定义，被 ComposeGrid 引用，类本身不删）
- **真机 L2 验证** + 文档同步

### Out（明确不做）

- **封面比例 1:1 保留**：订阅源图标语义为 1:1（原版如此），不强制改书架 0.75（仅登记差异）
- **不做订阅专属完整布局弹框重构**：仅补齐缺失项/删摆设项，沿用现有弹框结构
- **不动 modern 形态**：新版订阅顶栏/标签/flow 流程零改动
- 不新增订阅列表（sourceLayout 0/1）实现：固定卡片为用户既定决策（RssFragment.kt:1059-1060）
- 不删 FolderItem 数据类（SourceFolderAdapter.kt 定义，ComposeGrid 仍引用）

## Approach

### Selected Approach

**「margin 单源驱动 + 配置写入口补齐 + 语义对齐书架」三线收敛，全量复用 config-needs-restart-fix 已建立的事件机制与视效基线。**

1. **S1 margin 参数化**：SourceFolderComposeGrid 新增 `margin: Int` 入参，`contentPadding`/`spacedBy` 全部由 margin 推导（写法对齐 BookshelfScreen.kt:279-285）；调用方 RssFragment `initFolderComposeView` 传 `AppConfig.sourceMargin`
2. **S2 弹框补齐**：排序数组补第 7 项「更新时间」（RssFragment.kt:1359 的 6→lastUpdateTime 分支已存在，仅需打通入口）；新增升降序切换写 `rssSortAscending`；新增「书名显示」入口（显示/隐藏 两项，值 1/0 对齐 K7 语义）；视图模式移除「列表/紧凑列表」
3. **S3 语义修正 + 跨页刷新**：SourceFolderComposeGrid.kt:87 判断改 `showBookname == 1`；RssFragment `observeEvent(EventBus.BOOKSHELF_STRUCTURE_CHANGED)` → `applyView()+upFolderView()`
4. **S4 视效对齐**：图标圆角 12dp 改主题圆角（UiCorner.actionRadius 或等价，实施前读 FilletImageView API 确认 setter）；tvName 补 titleTypeface + minLines=2（RssAdapter onBindViewHolder 或 XML 二选一，以改动面小者为准）；去 item 自身 padding 16dp，间距单源 GridSpacingItemDecoration margin
5. **S5 死代码清理**：删 applyFolderView（RssFragment.kt:1072-1080）、upFolderView 去 folderAdapter 双写
6. **L2 验证**：真机逐项验证即时生效 + 回归

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| SourceFolderComposeGrid 内直读 `AppConfig.sourceMargin`（remember 快照） | 重蹈 config-needs-restart-fix 根因：remember 快照非响应式，改配置需重启；受控入参才是书架已验证的基线写法 |
| 为订阅新增独立结构事件（如 RSS_STRUCTURE_CHANGED） | `BOOKSHELF_STRUCTURE_CHANGED` 已存在且语义就是「结构类偏好变更→重建」，复用即可跨页同步，新增事件徒增双轨复杂度 |
| 订阅封面比例同样改 0.75 对齐书架 | 订阅源图标语义为 1:1（原版如此），强行 0.75 会裁切图标；登记差异不强制改 |
| 保留「列表/紧凑列表」并补订阅列表实现 | RssFragment.kt:1059-1060 用户已决策固定卡片，补实现属扩大改动面（Out） |
| 修复 applyFolderView 并接入调用点 | View 版渲染为死代码（无调用点），接入无收益；直接清理，FolderItem 数据类因 ComposeGrid 引用而保留 |
| item padding 与 GridSpacingItemDecoration 双份叠加微调数值共存 | 两处间距源叠加是 P6 根因之一，必须单源化（margin 驱动），调数值属治标 |

### Drawbacks

- `BOOKSHELF_STRUCTURE_CHANGED` 观察方新增 RssFragment，事件触发时多一次 applyView+upFolderView 开销（结构类配置变更低频，可接受）
- showBookname 判断方向翻转（`!= 1` → `== 1`）影响存量用户：此前依赖错位语义的存量值表现会翻转，需真机确认存量值下的实际观感
- item padding 16dp 移除后若 GridSpacingItemDecoration margin 值偏小，观感可能偏挤，需真机对照书架微调
- 弹框选项增删涉及 UI 回归面（对话框项数变化、选中态索引偏移需同步）

### Prior Art

- 本项目 [config-needs-restart-fix](../config-needs-restart-fix/README.md)：书架受控入参即时生效、margin 驱动间距（BookshelfScreen.kt:279-285）、AppShapes.Chip 主题圆角、titleTypeface 字体、minLines=2、`BOOKSHELF_STRUCTURE_CHANGED` 结构重建事件——本 spec 全量复用该基线
- 书架 K7 修正（config-needs-restart-fix 附录 A）：showBookname 语义统一 隐藏0/显示1/遮罩2，订阅侧对齐此语义
- RssFragment.kt:1359 已实现 rssSort=6→lastUpdateTime 排序分支（后端就绪，仅缺 UI 入口）

## Requirements

1. **R1 margin 文件夹即时生效**：修改 margin 后，订阅文件夹视图 contentPadding 与卡片间距即时按 margin 驱动，硬编码 (12,8,12)/(12,16) 清除
2. **R2 升降序+更新时间排序可达**：弹框可选「更新时间」（第 7 项）与升降序切换，写入 `rssSort`/`rssSortAscending` 后 RssFragment 排序分支正确生效
3. **R3 showBookname 语义对齐+跨页刷新**：判断为 `showBookname == 1` 显示；书架侧书名偏好变化后订阅页经 `BOOKSHELF_STRUCTURE_CHANGED` 同步刷新；弹框提供「书名显示」入口（值 1/0 对齐 K7 语义）
4. **R4 源卡片视效对齐主题**：图标圆角用主题圆角（非 12dp 硬编码）、书名 titleTypeface + minLines=2、item 自身 padding 16dp 移除、间距单源 GridSpacingItemDecoration margin
5. **R5 摆设项清理**：弹框视图模式仅剩 自动/Grid2-6；applyFolderView 删除、upFolderView folderAdapter 双写移除，编译通过且 FolderItem 数据类保留
6. **R6 无硬编码色**：沿用 AppShapes/主题 token，不新增硬编码色值
7. **R7 回归不破坏**：modern 形态、文件夹交互（展开/收起/进入源）、书架既有行为零回归

## Scenarios

### 场景 A：margin 文件夹生效（主 P1）
1. 经典订阅文件夹视图
2. 修改 margin 配置（调大/调小/0 各验一次）
3. **期望**：文件夹网格 contentPadding 与卡片间距即时随 margin 变化
4. **现状**：固定 (12,8,12)/(12,16)，margin 配置无效

### 场景 B：升降序 + 更新时间排序（主 P2/P3）
1. 打开订阅布局弹框
2. 排序选「更新时间」并切换升降序
3. **期望**：源列表按 lastUpdateTime 排序且方向随切换翻转
4. **现状**：两项均不可达（排序无第 7 项 / 升降序无写入口）

### 场景 C：书名显示跨页同步（主 P4）
1. 弹框开「书名显示」（写 showBookname=1）→ 订阅卡片显示书名
2. 切到书架页修改书名偏好（触发 `BOOKSHELF_STRUCTURE_CHANGED`）→ 返回订阅页
3. **期望**：订阅页书名显示状态同步刷新；判断方向为 1=显示
4. **现状**：判断方向相反、弹框无入口、跨页不刷新

### 场景 D：源卡片字体圆角对齐（主 P6）
1. 订阅文件夹网格查看源卡片，与书架卡片对照
2. **期望**：图标圆角为主题圆角、书名 titleTypeface 字体且 minLines=2、间距无双份叠加
3. **现状**：radius=12dp 硬编码、12sp 默认字体单行、item padding 16dp 与 decoration margin 叠加

### 场景 E：弹框选项清理后回归（主 P5/P7 + R7）
1. 打开订阅布局弹框，遍历视图模式各项
2. **期望**：视图模式仅 自动/Grid2-6（无「列表/紧凑列表」摆设项），各项选择均有效；modern 形态与文件夹展开/收起/进入源交互正常
3. **现状**：含 2 个无效摆设项
