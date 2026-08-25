# design.md — 书架订阅标签样式统一

## Technical Approach

采用「顶栏组件复用」：书架风格 1 的分组切换从 Compose 内部 `ScrollableTabRow` 迁移到 `MainTopBarView` 顶栏标签体系，与订阅共用同一组件与取色，实现观感统一并补上「右侧向下按钮 + 多级标签」。

整体数据流（以当前 `flowByGroup` 单分组加载模型为基础）：

```
appDb.bookGroupDao.show ──► upGroup(bookGroups)
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
 topBar.setTitle(当前分组名)            topBar.setPrimaryItems(全部分组, 选中)
 titleSelect▾ 点击                                   ↑ primaryBar 点击
      │ onGroupSelected(id)                              │
      └──────────────► 切换 selectedGroupId ──► flowByGroup ──► currentBooks ──► Compose 列表
                              │
                              ▼
                 from books 提取 customTag 标签 ──► topBar.tagsBar.submitItems(书本标签+全部)
                              │ tagsBar 点击过滤
                              ▼
                  fragmentMap/currentBooks 按标签过滤
```

## Architecture Decisions

### AD-01: 书架分组切换改用顶栏组件而非 Compose Tab
- **Context**: 当前书架 style1 用 Compose `ScrollableTabRow` 渲染分组，订阅用 `RoundedTagBarView` 胶囊，二者观感不一致；`MainTopBarView` 与 Rimchars archive 完全一致，已内置 `titleSelect`/`primaryBar`/`tagsBar`/`filterToggleButton`。
- **Concern**: 书架缺失下拉分组、多级标签，且与订阅不统一。
- **Decision**: 移除 `BookshelfScreen` 的 `BookGroupTabs`，分组选择改由 `MainTopBarView` 顶栏驱动（`titleSelect` + `primaryBar` + `tagsBar`）。
- **Goal**: 与订阅观感统一，补齐下拉/多级标签能力，复用已验证组件。
- **Tradeoff**: 顶栏增高挤压内容区；分组标签视觉由指示条变成胶囊；取消 Compose 侧的分组动画。
- **Status**: Accepted

### AD-02: 不迁移 ViewPager 架构（保持单分组 flow 加载）
- **Context**: Rimchars archive 的书架 style1 用 `ViewPager` + `FragmentStatePagerAdapter` 一分组一 Fragment；当前 fork 已改为 `ComposeView` + 单一 ` contractors` Composable，`flowByGroup` 加载当前分组。
- **Concern**: 全量迁移 ViewPager 改动巨大、回归风险高。
- **Decision**: 保持当前 `ComposeView` + `flowByGroup` 架构，仅改分组切换的渲染载体。
- **Goal**: 以最小改动达成统一，降低回归风险。
- **Tradeoff**: 责掉 ViewPager 的左右滑动手势切换分组能力（当前 fork 本就不具备，非本次引入的损失）。
- **Status**: Accepted

### AD-03: 书本标签过滤复用 `BookTagHelper` 数据源
- **Context**: 书本标签由 `customTag` 存储，Rimchars 用 `BookTagHelper.parse` 提取并经 `AppConfig.bookshelfGroupTags` 缓存。
- **Concern**: `tagsBar` 需要第二级标签数据。
- **Decision**: 从当前分组书籍提取 `customTag` 标签形成 `tagsBar`，点击设置过滤条件（空串=全部）。
- **Goal**: 提供与订阅一致的多级标签交互。
- **Tradeoff**: 分组内无标签书时不显示标签项，仅「全部」占位；`tagsBar` 属顶栏 View 层，过滤需通过回调回写 Compose 列表状态。
- **Status**: Accepted

### AD-04: 分组胶囊条（primaryBar）仅在顶栏 regular 风格显示（用户确认取舍）
- **Context**: `MainTopBarView.updatePrimaryBarVisibility` 判断 `primaryBar.isVisible = isRegularStyle() && primaryBarRequested`；默认（非 regular）风格不显示横向分组胶囊。
- **Concern**: 书架在默认风格下看不到分组胶囊条，可能误以为功能缺失。
- **Decision**: 遵循该原生行为——默认风格仅通过标题下拉（titleSelect）换组；切到顶栏 regular 风格才显示横向分组胶囊。与订阅/archive 完全一致。
- **Goal**: 与订阅观感/行为相对齐，不引入非对齐改动。
- **Tradeoff**: 默认风格下书架分组切换只有下拉入口。
- **Status**: Accepted

### AD-05: 分组胶囊不支持长按编辑分组（用户确认取舍）
- **Context**: `RoundedTagBarView` 胶囊仅有 `setOnTagClickListener`，无长按回调；archive 的 `primaryBar` 同样无分组长按。
- **Concern**: 原 Compose `ScrollableTabRow` 分组长按可弹 `GroupEditDialog`，迁移后该入口将失效。
- **Decision**: 接受与 archive 一致——分组管理改走「更多菜单→分组管理」（`GroupManageDialog`），不额外给 `RoundedTagBarView` 增加长按能力。
- **Goal**: 避免改动共享组件影响订阅端，控制回归风险。
- **Tradeoff**: 丢失分组长按快捷编辑。
- **Status**: Accepted

## Data Flow

1. `upGroup(bookGroups)` → 若书组有变化：更新 `groupList`，刷新顶栏 `primaryBar`（`setPrimaryItems`）与 `titleSelect` 标题，`flowByGroup(selectedGroupId)` 加载书籍。
2. 顶栏交互：
   - `titleSelect` 点击 → `showGroupSwitchMenu()` 构造 `ModernActionPopup`（`✓` 标记选中）→ 选择 → `switchToGroup(id)`。
   - `primaryBar` 点击 → `switchToGroup(id)` → 更新 `selectedGroupId` + `AppConfig.saveTabPosition` + 重载书籍 + 刷新标题/书本标签。
   - `tagsBar` 点击 → 设置 `selectedBookTag`（空串=全部）→ 过滤当前分组书籍 → 重绘列表。
3. `TOPBAR/主题变更`（`TOP_BAR_CHANGED`）→ `MainTopBarView.applyTopBarStyle` 自动刷新分组/标签取色，无需 Compose 版本号驱动。

## File Changes

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfScreen.kt` | 删除 `BookGroupTabs` Composable 及 `topBarVersion` 相关入参/取色辅助（`readableTagColor` 若仅此处使用一并清理） |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfFragment1.kt` | 顶栏接线：`setMode(BOOKSHELF)`、动态标题、`titleSelect`→`showGroupSwitchMenu`、`setPrimaryItems`、`showTags`+`tagsBar.submitItems`、`filterToggleButton`；移除传给 `BookshelfScreen` 的分组 Tab 相关参数 |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt` | `initComposeTopBar()` 适配：支持动态分组标题与 `primaryBar`/`titleSelect`（bookshelf 场景）；新增分组标签渲染入口可复用 |
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | 仅验证对齐，若发现观感差异小修（默认不改） |
| `app/src/main/assets/updateLog.md` | 编译前同步新增功能说明 |

> `MainTopBarView`/`RoundedTagBarView` 与 archive 一致，本轮不改。

## Risks & Mitigations

- **顶栏增高挤压内容**：书架为 `LinearLayout` 顺排，顶栏增高自然下推 ComposeView，无需覆盖式补偿；真机确认观感。
- **`tagsBar` 过滤与 Compose 状态**：过滤通过更新 `currentBooks` 派生列表实现，确保与 `loading`/`error` 状态共存不闪。
- **结构变更**：`BOOKSHELF_STRUCTURE_CHANGED`/`BOOKSHELF_REFRESH` 事件需重建顶栏分组数据与书本标签，仿照 Rimchars 的 `rebuildBookshelfContent`/`renderBookTags`。