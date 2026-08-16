# L-B8 书架管理（BookshelfManageActivity）· 轻量设计文档

> **适用**：B8 书架管理为枝叶页，继承族文档 `pages/P1-bookshelf.md`（S2 列表）+ `pages/P5-booksource.md`（S2 多选批量范式）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/manage/BookshelfManageActivity.kt`（430 行）
- **所属族文档**：`pages/P1-bookshelf.md` + `pages/P5-booksource.md`（继承 S2 多选批量范式）
- **骨架归类**：S2 列表管理页（多选批量）
- **对应 task**：tasks.md `12.41`；pages-inventory B8（task 待接线）；⚠️ 与 Compose 书架排序一致性需回归

## 1. 继承声明
- 复用骨架：S2 列表管理 + SelectActionBar 批量栏（P5 §2）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`（搜索）、`SelectActionBarCompose`（批量栏）、`SwipeActionContainer`（拖拽）、L2 Dialog 族（删除/换源）
- 复用状态范式：`ViewModel + StateFlow`；多选状态派生（isSelecting=selectedUrls）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 多选 | P1 无批量 | 进入即滑选多选 + ItemTouchCallback 拖拽（仅自定义排序） | 差异核心 |
| 搜索 | — | SearchView + 4 排序 | |
| 批量栏 | — | "移动到分组" | SelectActionBar |
| 选择菜单 | — | 删除带"删除原文件"CheckBox / 启用停用更新 / 加移分组 / 批量换源 SourcePickerDialog+WaitDialog / 清缓存 / 区间选 | 差异功能点 |
| 菜单 | — | 分组管理 / 详情开关 / 导出所用书源 / 分组切换 | |
| item 点击 | — | → BookInfoActivity | |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SelectActionBarCompose` | 受控批量栏 | 多选操作 |
| `SwipeActionContainer` | 左滑固定宽、error 删除/primary | 拖拽排序 |
| `SourcePickerDialog`→`AppSelectDialog` | L2 语义 Dialog | 批量换源收敛去向 |
| `AppWaitDialog`（L2 族） | L2 语义 Dialog | 换源 WaitDialog 去向 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 书柜加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空书柜占位 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；删除 CheckBox / 区间选文案无硬编码中文

## 6. 验收标准（轻量）
- [ ] 进入即滑选多选 + ItemTouchCallback 拖拽（仅自定义排序）
- [ ] 4 排序 / SelectActionBar"移动到分组" / 选择菜单（删除带原文件CheckBox/启停更新/加移分组/批量换源/清缓存/区间选）全实现
- [ ] 菜单（分组管理/详情开关/导出所用书源/分组切换）；item 点击→BookInfoActivity
- [ ] 与 Compose 书架排序一致性回归通过；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.41
