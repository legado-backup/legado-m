# L-C5 高亮规则（HighlightRule）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P5-booksource.md`（S2 列表）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P5 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：HighlightRuleActivity（`ui/highlight/`，View）
- **所属族文档**：`pages/P5-booksource.md`（继承 S2）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.47`；pages-inventory C5（优先级 P2）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P5 §2：GlassTopAppBar + LazyColumn + 拖拽排序 + 批量栏）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`SelectActionBarCompose`、`SwipeActionContainer`、`AppDropdownMenu`
- 复用状态范式：`ViewModel + StateFlow`（多选派生）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | **SharedPreferences（HighlightRuleStore 非 Room）**；onDestroy 同步 `ReadBook.upHighlightRules` | 与族文档 Room 不同，轻量存储 |
| 布局结构 | 列表 + 拖拽排序 | — |
| 交互 | 菜单（添加/分组管理/预设 HighlightPresetRuleDialog/恢复默认 MERGE\|OVERWRITE 双确认/导入剪贴板JSON去重/导出）；item 编辑删除置顶置底开关 | — |
| 功能点 | 高亮规则列表 + 预设 + 恢复默认双确认 + 剪贴板导入去重 | 对照 pages-inventory C5 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog` | L2 字段输入弹窗 | 编辑规则 |
| `ConfirmDialog` | L2 语义确认弹窗 | 恢复默认 MERGE\|OVERWRITE 双确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无规则空态，title 走 strings.xml |
| 错误 | `EmptyStatePlaceholder` | 导入失败提示 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P5 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C5 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.47 / pages-inventory C5）
