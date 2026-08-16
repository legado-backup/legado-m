# L-B4 高亮（HighlightFragment）· 轻量设计文档

> **适用**：B4 高亮为枝叶页，继承族文档 `pages/P2-reader.md`（S2 列表管理范式）。**当前未挂载**（F-P1-2 注释），真实入口在 HighlightRuleActivity；目录页 Tab 未接线（V14）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/toc/HighlightFragment.kt`（108 行）
- **所属族文档**：`pages/P2-reader.md`（继承 S2 列表范式 + S5 浮层蓝图）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.16p`；pages-inventory B3/B4

## 1. 继承声明
- 复用骨架：S2 列表管理（Room Flow 实时订阅）
- 复用组件（§3.4）：`GroupHeader`、L2 Dialog 族（长按编辑）、`ReaderBookSheet`（R2 高亮 Tab 收敛去向）
- 复用状态范式：`ViewModel + Flow`

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | ReadBook 单例 | `bookHighlightDao` 流 | 高亮专用 |
| 交互 | — | 点击跳章节；长按 HighlightNoteDialog（编辑/删除） | V9 私有弹窗待 L2 族收敛 |
| 挂载 | — | **当前未挂载（F-P1-2）**，真实入口在 HighlightRuleActivity；目录页 getCount()==2 不含高亮 | **V14 止血项** |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog`（L2 族） | L2 语义 Dialog | HighlightNoteDialog 收敛去向（V9 待接线） |
| `HighlightStyleDialog` | 色板+下划线 2 行 6 色 | 高亮样式（P8 §2） |
| `ReaderBookSheet`（🆕 待建） | 三 Tab | R2 高亮 Tab 收敛去向 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 高亮加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空高亮占位（V11） |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 硬编码中文待清（V6 含 HighlightFragment:77）；item_highlight.xml 硬编码色 #80FFF176 绕过 token 待修（V8）

## 6. 验收标准（轻量）
- [ ] **V14 已修**：高亮 Tab 接线，目录页 getCount() 含高亮，搜索分发含高亮分支
- [ ] bookHighlightDao 流 + 点击跳章节 + 长按 HighlightNoteDialog 实现
- [ ] 三态/i18n/色 token 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 task 12.16p）
