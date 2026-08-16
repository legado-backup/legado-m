# L-B5 全部书签（AllBookmarkActivity）· 轻量设计文档

> **适用**：B5 全部书签为枝叶页，继承族文档 `pages/P2-reader.md`（S2 列表管理范式）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/bookmark/AllBookmarkActivity.kt`
- **所属族文档**：`pages/P2-reader.md`（继承 S2 列表范式）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.4F`；pages-inventory B5（task 待接线，12.16p 族内）

## 1. 继承声明
- 复用骨架：S2 列表管理（Room Flow 实时订阅 + 分组头）
- 复用组件（§3.4）：`GroupHeader`（分组头）、`AppDropdownMenu`（导出菜单）、L2 Dialog 族（长按编辑）
- 复用状态范式：`ViewModel + Flow`

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | 单书 | `flowAll` 全部书签 + 分组头 | 跨书全局书签 |
| 点击 | — | 查书跳读（书已删则弹 BookmarkDialog） | 差异：书删除兜底 |
| 长按 | — | BookmarkDialog（编辑/删除） | V9 私有弹窗待 L2 族收敛 |
| 导出 | — | 导出 MD | 差异功能点 |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `GroupHeader` | titleSmall Bold、行≥48dp | 分组头渲染 |
| `AppEditDialog`（L2 族） | L2 语义 Dialog | BookmarkDialog 收敛去向 |
| `AppDropdownMenu` | M3 DropdownMenu | 导出 MD 菜单 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 书签加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空全部书签占位 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）
- [ ] flowAll + 分组头实时渲染；点击查书跳读（书删兜底 BookmarkDialog）
- [ ] 长按 BookmarkDialog 编辑/删除；导出 MD 实现
- [ ] 三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 12.16p 族内），task 12.4F
