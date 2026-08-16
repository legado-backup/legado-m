# L-C12 源回收站（RecycleBin）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P5-booksource.md`（S2 列表）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P5 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RecycleBinActivity（`ui/source/recycle/`，View）
- **所属族文档**：`pages/P5-booksource.md`（继承 S2）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.59`；pages-inventory C12（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P5 §2：GlassTopAppBar + LazyColumn + 批量栏）
- 复用组件（§3.4）：`GlassTopAppBar`、`SelectActionBarCompose`、`SwipeActionContainer`、`EmptyStatePlaceholder`、`AppDropdownMenu`
- 复用状态范式：`ViewModel + StateFlow`（多选派生）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | `sourceRecycleBinDao.flowAll` | 回收站专用 DAO |
| 布局结构 | 列表；SelectActionBar 主按钮为**恢复**（族文档批量栏主按钮为启用/删除） | — |
| 交互 | 恢复冲突检测 hasConflict 覆盖确认；菜单（清空回收站/帮助）；选择模式删除选中；item 恢复/删除 | — |
| 功能点 | 回收站列表 + 恢复（冲突确认） + 清空 | 对照 pages-inventory C12 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `ConfirmDialog` | L2 语义确认弹窗 | 恢复冲突 hasConflict 覆盖确认 / 清空确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 回收站为空 |
| 错误 | `EmptyStatePlaceholder` | 加载失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P5 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C12 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.59 / pages-inventory C12）
