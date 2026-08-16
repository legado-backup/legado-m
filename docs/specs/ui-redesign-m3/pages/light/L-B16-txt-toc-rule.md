# L-B16 txt 目录规则（TxtTocRuleActivity）· 轻量设计文档

> **轻量版**：本页继承族文档 `pages/P2-reader.md`（S2 列表族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P2-reader.md` + ui-standards §3.4 规格书。

## 0. 页面身份
- **页面名 / 文件锚点**：TxtTocRuleActivity（`ui/book/toc/rule/`，View，273 行）
- **所属族文档**：`pages/P2-reader.md`（继承 S2 列表族）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.54`；pages-inventory B16（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）
- 复用骨架：S2 列表管理页（P2 §2）+ 滑选多选 + 拖拽排序 + 批量操作栏
- 复用组件（§3.4）：`GlassTopAppBar`、`SelectActionBar`（批量删除）、`SwipeActionContainer`（长按删除/编辑）、`AppDropdownMenu`（选择菜单/顶栏菜单）、`AppTextDialog`（帮助/导入在线/二维码）
- 复用状态范式：`ViewModel + StateFlow`（规则列表 + 多选集 + 拖拽排序持久化）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | TxtTocRule 规则列表（Room） | — |
| 布局结构 | 规则列表 + 顶栏菜单 | — |
| 交互 | 滑选多选 + 拖拽排序；SelectActionBar 删除；选择菜单（启用停用/导出JSON）；顶栏菜单（添加 TxtTocRuleEditDialog/导入本地/在线导入/二维码导入/导入默认/帮助）；item 点击编辑/长按删除；置顶置底 | 导入族 + 置顶置底为私有交互 |
| 功能点 | 列表/多选/拖拽/选择菜单/顶栏菜单/点击编辑/长按删除/置顶置底 | 对照 pages-inventory B16 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SelectActionBar` | 批量操作栏（受控） | 多选删除 |
| `SwipeActionContainer` | 左滑操作容器 | 长按删除/编辑 |
| `AppDropdownMenu` | M3 DropdownMenu | 选择菜单/顶栏菜单 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 规则加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无规则 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）
- [ ] 复用 P2 骨架/组件，无私有复制组件
- [ ] 功能点对照 pages-inventory B16 无遗漏（列表/滑选多选/拖拽排序/SelectActionBar 删除/选择菜单/顶栏菜单/点击编辑/长按删除/置顶置底）
- [ ] 多选/拖拽排序持久化正确；三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 pages-inventory B16），task 12.54
