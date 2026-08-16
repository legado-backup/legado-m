# L-B3 书签（BookmarkFragment）· 轻量设计文档

> **适用**：B3 书签为枝叶页，继承族文档 `pages/P2-reader.md`（S2 列表管理范式）。真实入口在目录页 TocActivity 的 Tab 内。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/toc/BookmarkFragment.kt`
- **所属族文档**：`pages/P2-reader.md`（继承 S2 列表范式 + S5 浮层蓝图）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.16p`；pages-inventory B3

## 1. 继承声明
- 复用骨架：S2 列表管理（Room Flow 实时订阅）
- 复用组件（§3.4）：`SettingsSearchBar`（搜索驱动）、`GroupHeader`（分组）、`AppModalBottomSheet`/L2 Dialog 族（长按编辑）
- 复用状态范式：`ViewModel + Flow`；搜索由 TocActivity 驱动

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | ReadBook 单例 | `flowByBook/flowSearch` 实时列表 | 书签专用 |
| 定位 | — | 自动滚动定位当前章书签 | 点击跳转 |
| 长按 | — | BookmarkDialog（编辑/删除） | V9 私有弹窗待 L2 族收敛 |
| 搜索 | — | 由 TocActivity 驱动（无独立搜索栏） | 差异点：搜索词来自父页 |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog`（L2 族） | L2 语义 Dialog | BookmarkDialog 编辑收敛去向（V9 待接线） |
| `AppSelectDialog`（L2 族） | L2 语义 Dialog | 删除确认去向（V9 待接线） |
| `ReaderBookSheet`（🆕 待建） | 三 Tab | R2 书签 Tab 收敛去向 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 书签加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空书签占位（V11） |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 硬编码中文待清（V6 含 BookmarkFragment:64）；触控/语义随族文档标准

## 6. 验收标准（轻量）
- [ ] flowByBook/flowSearch 实时列表 + 自动滚动定位 + 点击跳转无遗漏
- [ ] 长按 BookmarkDialog 编辑/删除实现；搜索由 TocActivity 驱动正常
- [ ] 三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 task 12.16p）
