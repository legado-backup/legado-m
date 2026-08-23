# §9.1 组件目录

> 本节列出项目当前的 Compose 组件资产。分两部分：
> - **主干组件库**：`app/src/main/java/io/legado/app/ui/widget/components/`（抽象度较高、可供各页复用的受控组件）
> - **运行期骨架/对话框组件**：`app/src/main/java/io/legado/app/ui/widget/compose/`（脚手架、管理壳、对话框族、主题桥接等）
>
> 清单由 Glob 读取实际文件生成，用途为文件内核心函数的「一句话用途」。

## 一、增强组件目录 `ui/widget/components/`

通用受控组件库（部分为 archive-ui-migration E4「特色统一外观」的落点）。

| 文件 | 核心 Composable / 入口 | 一句话用途 |
|------|----------------------|-----------|
| `SettingsSection.kt` | `SettingsSection` | 设置页分组标题区 |
| `SettingsCard.kt` | `SettingsCard` | 设置分组卡片容器 |
| `SettingsClickRow.kt` | `SettingsClickRow` | 可点击设置行（列表项入口） |
| `SettingsToggleRow.kt` | `SettingsToggleRow` | 带开关的设置行 |
| `SettingsSelectableRow.kt` | `SettingsSelectableRow` | 可选中的设置行（多选场景） |
| `SettingsSearchBar.kt` | `SettingsSearchBar` | 搜索框（S2 各列表页搜索入口统一组件） |
| `RowIcon.kt` | `RowIcon` | 行内图标（被 ClickRow/ToggleRow 内部复用） |
| `ListCard.kt` | `ListCard` | 通用列表卡片容器 |
| `GroupHeader.kt` | `GroupHeader` | 分组可折叠列表头（箭头 + 组名 + 启用数/总数徽标 + 更多菜单） |
| `MetricGrid.kt` | `MetricGrid` | 「我的」页统计卡网格（成就/统计） |
| `BadgeDot.kt` | `BadgeDot` | 角标圆点（书架/导航计数角标） |
| `TagChip.kt` | `TagChip` | 标签 Chip（筛选/分类标签） |
| `EmptyStatePlaceholder.kt` | `EmptyStatePlaceholder` | 空态占位（标题/副标题 + 可选 CTA） |
| `ShelfGridSkeleton.kt` | `ShelfGridSkeleton` / `ShelfListSkeleton` | 书架加载骨架屏（网格 / 列表两种形态） |
| `GlassTopAppBar.kt` | `GlassTopAppBar` | 磨砂顶栏（返回 + 标题 + 动作） |
| `PillNavigationBar.kt` | `PillNavigationBar` | 胶囊式底部导航（S1 主导航壳） |
| `AppModalBottomSheet.kt` | `AppModalBottomSheet` | 通用模态底部弹层（S6/L1） |
| `AppMenuSheet.kt` | `AppMenuSheet` | 长按条目的底部富操作菜单（菜单族） |
| `AppDropdownMenu.kt` | `AppDropdownMenu` | 封装 M3 DropdownMenu 的下拉菜单（菜单族） |
| `MenuLayer.kt` | `MenuLayer` | 菜单浮层封装 |
| `ConfirmDialog.kt` | `ConfirmDialog` | M3 AlertDialog 确认对话框（destructive 支持） |
| `AppConfirmDialog.kt` | `AppConfirmDialog` | 统一确认对话框（对话框族） |
| `SingleChoiceDialog.kt` | `SingleChoiceDialog` | 单选对话框 |
| `AppEditDialog.kt` | `AppEditDialog` | 多字段文本输入对话框（OutlinedTextField 列表，`onConfirm(List<String>)`） |
| `AppTextDialog.kt` | `AppTextDialog` | 纯文本 / Markdown 展示对话框（内置 MarkdownView） |
| `AppShapes.kt` | — | 组件级圆角形状定义 |
| `ThemeSpec.kt` | `ThemeSpec` | 主题规格数据类（toM3Scheme 映射入口） |
| `ColorPickerSheet.kt` | `ColorPickerSheet` | 取色器底部弹层 |
| `ReadMenuSlider.kt` | `ReadMenuSlider` | 阅读菜单滑块（阅读器浮层组件） |
| `ModernActionPopup.kt` | `ModernActionPopup` | 现代浮出操作菜单（AndroidView 弹出，供管理壳复用） |
| `VerticalScrollbar.kt` | `VerticalScrollbar` | 垂直滚动条指示 |
| `BookTocBookmarkSheet.kt` | `BookTocBookmarkSheet` | 目录/书签双 Tab 底部弹层（阅读器浮层雏形） |
| `ImportSourceSheet.kt` | `ImportSourceSheet` | 导入源底部弹层 |
| `HighlightStyleSheet.kt` | `HighlightStyleSheet` | 高亮样式底部弹层 |
| `ConfirmDialog`（见上） | — | — |

> 注：部分组件（`VerticalScrollbar`、`SwipeActionContainer`、`SummaryCard`、`ThemedSnackbarHost`、`ListLayoutMenu` 等）为归档设计阶段登记组件，以实际存在文件数为准，具体接线状态见 `migration-registry.md`。

## 二、运行期骨架/对话框组件 `ui/widget/compose/`

含脚手架、统一设置壳、管理壳、对话框族与主题桥接。文档相关文件：

| 文件 | 核心类 / 函数 | 一句话用途 |
|------|--------------|-----------|
| `AppManagementScaffold.kt` | `AppManagementScaffold` / `AppManagementAction` / `AppManagementListRow` / `AppManagementLazyColumn` / `AppManagementCard` | 管理页通用骨架：顶栏 + 内容 + 底部批量操作栏（详见 page-skeleton.md） |
| `AppSettingComponents.kt` | `AppSettingPalette` / `AppManagementPalette` / `rememberAppSettingPalette` / `rememberAppManagementPalette` / `AppSettingSectionTitle` | 设置/管理调色板与分级脚手架组件（详见 page-skeleton.md） |
| `AppComposeDialogs.kt` | `ComposeDialogFragment` 族（对话框 8+ 类）+ `AppDialogStyle` / `AppDialogFrame` 等 | Compose 对话框全集（详见 dialog-shell.md） |
| `ComposeDialogFragment.kt` | `ComposeDialogFragment` | Compose 对话框基类（居中/顶部/底部、宽档位、返回键、墨水屏） |
| `ComposeDialogAdapters.kt` | `showComposeConfirmDialog` / `showComposeActionListDialog` / `showComposeSingleChoiceDialog` 等 | Compose 对话框的 Fragment 便捷入口扩展 |
| `ComposeChoiceListDialog.kt` | `ComposeChoiceListDialog` | 选择列表对话框 |
| `GroupManageComposeDialog.kt` | `GroupManageComposeDialog` | 分组管理对话框（E1 分组弹框落点，复用本件） |
| `AppPackageManageComponents.kt` | 包管理相关组件 | 在线导入 / 包管理对话框组件（E1 相关） |
| `LegadoComposeTheme.kt` | `LegadoComposeTheme` | Compose 全局主题桥接（toM3Scheme） |
| `AppUiTokens.kt` | `AppDialogSize`（Confirm/Form/Management/Wide）+ `AppListSpacing`（Compact/Normal/Section） | 对话框宽度档位与星级间距 Token |
| `ComposeFastScroller.kt` | `ComposeLazyListFastScroller` | Lazy 列表快速滚动条 |
| `ComposeViewOwners.kt` | — | Compose 视图 Owner 辅助 |
| `ComposeThemeImageLayer.kt` / `ComposeImageRelease.kt` | — | 主题背景图绘制 / 图片资源释放 |
| `SnapListUpdates.kt` | — | 列表增量更新工具 |
| `BookCoverImage.kt` | `BookCoverImage` | 封面图 Compose 包装 |
| `RuleEditComposeComponents.kt` | — | 规则编辑 Compose 组件 |
| `LegadoMiuixComponents.kt` | `LegadoMiuixPalette` / `LegadoMiuixCard` / `LegadoMiuixSwitch` / `LegadoMiuixActionButton` | 内部统一外观组件集 |
| `SearchBookPreviewOverlay.kt` / `SearchBookListItem.kt` | — | 搜索书预览浮层 / 搜索结果列表项 |

## 三、骨架 `ui/widget/components/` 与 `ui/widget/compose/` 的分工

- **`components/`**：抽象度高的**受控**可复用组件，强调「复用 + 接线」，面向通用场景（设置行、空态、骨架、菜单、对话框等）。
- **`compose/`**：含**运行期骨架**（管理壳、设置壳）与**对话框族**（ComposeDialogFragment 及其子类），与主题/调色板桥接更紧密，部分为 Archive 对齐迁移（E4）的具体落点。