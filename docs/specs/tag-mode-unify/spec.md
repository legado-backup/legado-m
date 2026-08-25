# spec.md — 书架订阅标签样式统一

## Intent

书架与订阅的分类/分组标签目前用两套截然不同的 UI（书架 Compose `ScrollableTabRow`；订阅 `RoundedTagBarView` 胶囊），观感不一致、书架缺失「右侧向下按钮 + 多级标签」能力。本需求将两处标签样式统一到 Rimchars archive 的 `MainTopBarView` 顶栏标签模式，让书架获得与订阅一致的分组下拉、胶囊标签、书本标签过滤。

**本次三大铁律（用户明确要求）**：
1. **一套**：书架与订阅在代码里共用**同一套**标签体系 —— 即 `MainTopBarView` 内置的 `RoundedTagBarView`（`primaryBar`/`tagsBar`/`titleSelect`/`filterToggleButton`），彻底废弃书架的 Compose `ScrollableTabRow`。
2. **可管理**：标签样式严格受「顶栏设置 / 主题设置 / 管理设置-样式管理」控制（`TopBarConfig` + 主题 token + `AppShapes`/`UiCorner`），不写死任何颜色形状。
3. **保留 Compose**：保持现有 `ComposeView` 书籍列表架构，**不照搬** Archive 的 `View+ViewPager` 骨架，仅把分组切换渲染载体从 Compose Tab 迁移到 View 层顶栏。

## Scope

### In-Scope（本次实现）
1. **书架 style1**：移除 Compose 分组 `ScrollableTabRow`（`BookGroupTabs`），改用 `MainTopBarView` 顶栏标签模式：
   - `titleSelect`（当前分组名 + 向下箭头）→ 点击弹出分组切换菜单（`ModernActionPopup`）。
   - `primaryBar` → 全部分组胶囊标签，点击切换分组。
   - `tagsBar` → 当前分组书本标签（第二级），点击按标签过滤。
   - `filterToggleButton`（右侧向下按钮）→ 展开/收起多级标签栏（regular 风格）。
2. **订阅**：保持现有 `titleSelect` + `primaryBar` + `tagsBar` 模式不变，验证样式与书架一致即可（本需求不另改订阅，除非发现不一致需一并对齐）。
3. **样式一致性**：书架与订阅使用同一 `RoundedTagBarView` 组件与取色逻辑，观感统一。

### Out-of-Scope（本次不实现）
- 书源管理、排行、发现页等其他页面的标签改造。
- 书架数据模型增加父级分组（`BookGroup` 保持扁平，无层级）。
- Rss 旧式（non-modern）订阅顶栏改造。
- 标签管理页（`BookshelfTagManageActivity`）改动。

## Approach

### Selected Approach：顶栏组件复用 —— 轻量改造书架，复用 `MainTopBarView` 既有标签体系

保持当前书架架构（`ComposeView` 内容 + `flowByGroup` 单分组加载）不变，只改动分组切换的**渲染载体**：

1. `BookshelfScreen` 删除 `BookGroupTabs`（`ScrollableTabRow`）及其 `topBarVersion` 驱动逻辑。
2. `BookshelfFragment1` 接线顶栏：
   - `topBar.setMode(BOOKSHELF)`、`setTitle(当前分组名)`，`titleSelect` 可点击。
   - `showGroupSwitchMenu()`：`titleSelect` 点击 → `ModernActionPopup` 列出全部分组（选中项前缀 `✓`）。
   - `topBar.setPrimaryItems(groups, currentIndex)`：`primaryBar` 胶囊分组，点击 → `onGroupSelected`。
   - `topBar.showTags(true)` + `topBar.tagsBar.submitItems(bookTags)`：书本标签第二级，点击 → 过滤。
   - 顶栏 `filterToggleButton` 保留，regular 风格下展开/收起 tags。
3. `BaseBookshelfFragment.initComposeTopBar` 适配：标题改为动态分组名，暴露/保留 `titleSelect` 与 `primaryBar` 能力。

理由：Rimchars archive（订阅当前实现）已证明这套顶栏标签模式可用且观感统一；当前 fork 的 `MainTopBarView` 与 Rimchars 完全一致（含 `titleSelect`/`primaryBar`/`tagsBar`/`filterToggleButton`），只是书架 Fragment 未启用。书架直接启用同一套标签组件后，**书架与订阅天然同源一套**，观感体感与 archive 完全一致，且颜色/圆角/胶囊全部读取 `TopBarConfig` + 主题 token，被「顶栏设置/主题设置/管理设置」统一管理。改动量小、回归风险低。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 全量迁移 Rimchars ViewPager 架构 | 将 style1 改为 `ViewPager` + `FragmentStatePagerAdapter`，一分组一 Fragment | 改动面巨大，丢失当前 `flowByGroup` 单流加载优化，回归风险高；与「最小改动达成统一」目标不符 |
| 仅对现有 `ScrollableTabRow` 做样式美化 | 保留 Compose Tab，只改颜色/形状 | 无法增加「右侧向下按钮」「多级标签」，达不到用户诉求，也不解决与订阅不一致 |
| 新建一套全局 Compose 标签组件替换两处 | 抽统一 Compose 组件 | 订阅已用 View 层 `RoundedTagBarView` 且观感达标，再造 Compose 组件会引入双实现、放大工作量 |

### Drawbacks

- 书架顶栏高度增加（标题行 + `primaryBar` + `tagsBar`），挤压内容可视区；需借助现有 `MainTopBarView` 高度感知在内容侧做合理布局（书架为 `LinearLayout` 顺排，顶栏增高会自然下推内容，无需覆盖式换算）。
- 书本标签过滤依赖书籍 `customTag` 数据；无标签的分组 `tagsBar` 仅显示「全部」占位（对齐 Rimchars）。
- 取消 `ScrollableTabRow` 后，分组切换动画/指示器样式由顶栏胶囊替代，视觉行为改变（目标即如此）。
- 顶栏设置（`TopBarConfig`）在书架分组标签的重组依赖需要跟随 `TOP_BAR_CHANGED` 事件刷新（原 Compose 用 `topBarVersion`，现改由 View 层 `applyTopBarStyle` 自动处理，逻辑更简单）。

接受上述缺点：换取与订阅一致的观感、下拉/多级标签能力，且复用已验证组件降低风险。

### Prior Art

- Rimchars archive：`temp/forks-comparison/Rimchars_legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style1/BookshelfFragment1.kt` —— 顶栏 `titleSelect`+`primaryBar`+`tagsBar` 模式（已调研，本次直接对齐）。
- 本项目订阅现代形态：`app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` `initModernRssView()` —— 已用同一套顶栏组件，作为统一目标样式。

## Requirements

### 功能需求（FR）
- **FR-1** 书架 style1 分组切换不再使用 Compose `ScrollableTabRow`，改用顶栏 `primaryBar` 胶囊标签。
- **FR-2** 书架顶栏标题显示当前分组名并带向下箭头（`titleSelect`），点击弹出全部分组菜单（`ModernActionPopup`），支持切换任意分组，当前组标 `✓`。
- **FR-3** 书架 `tagsBar` 展示当前分组的书本标签（`BookTagHelper` 解析 `customTag`），点击按标签过滤当前分组书籍，「全部」回退全量。
- **FR-4** 书架与订阅标签观感一致（同一 `RoundedTagBarView` + `TopBarConfig` 取色）。
- **FR-5** regular 风格下右侧向下按钮（`filterToggleButton`）可展开/收起多级标签栏。

### 非功能需求（NFR）
- **N1** 不引入新依赖，不改数据库 schema。
- **N2** 沿用现有协程/状态管理模式（Compose 内容 + View 层顶栏）。
- **N3** 无残留调试日志；编译通过；书架/订阅关键交互真机验证。
- **N4** updateLog 同步更新（编译前）。

## Scenarios

### 正常场景
1. 用户进入书架 style1：顶栏显示「当前分组 ▾」，下方为分组胶囊标签，另有一行书本标签（或「全部」）。
2. 点击任一胶囊分组 → 该书架切换为该分组书籍，标题同步更新。
3. 点击标题 ▾ → 弹出全部分组菜单（选中项勾选）→ 选择分组跳转。
4. 点击书本标签 → 仅显示含该标签的书；点「全部」→ 显示全量。
5. 订阅页保持相同标签观感，两页视觉统一。

### 边界/异常场景
1. 仅 1 个分组：`primaryBar` 仅一项，行为正常（对齐 Rimchars）。
2. 分组无任何标签：`tagsBar` 仅「全部」占位，过滤无副作用。
3. 分组列表变化/结构变更（`BOOKSHELF_STRUCTURE_CHANGED`）：重建顶栏分组数据与选中态。
4. 顶栏设置/主题变更（`TOP_BAR_CHANGED`）：View 层 `applyTopBarStyle` 自动刷新取色。
5. `customTag` 非法/含分隔符异常：解析兜底，不崩溃。