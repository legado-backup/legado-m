# L-A5 书架抽象基类（BaseBookshelfFragment）· 轻量设计文档

> **适用**：A5 为书架 View 壳（S1 附属），继承族文档 `pages/P1-bookshelf.md`。本页因 Phase3 用户红线「保留 View 壳」，Compose 化时仅登记差异，不重构为 Compose。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/main/bookshelf/BaseBookshelfFragment.kt`
- **所属族文档**：`pages/P1-bookshelf.md`（继承 S2 书架范式）
- **骨架归类**：S1 附属（书架 View 壳）
- **对应 task**：tasks.md `12.16j`；pages-inventory A5
- **fork 借鉴来源**：—（View 壳，红线保留）

## 1. 继承声明
- 复用骨架：P1 书架 Grid/列表范式（Compose 书架已接线 BadgeDot/ShelfGridSkeleton/EmptyStatePlaceholder）
- 本壳承载：12 项菜单挂载 + configBookshelf 对话框 + 3 个 HandleFileContract + WaitDialog，**Phase3 红线全量保留为 View 壳**

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | Compose Flow | 壳层事件分发 | 菜单/对话框作用于 Compose 书架 |
| 布局结构 | Compose | 纯 View 壳，无独立 UI | 仅挂载菜单+对话框 |
| 功能点 | — | 12 菜单/HandleFileContract×3/configBookshelf/showAddBookByUrlAlert/importBookshelfAlert | 对照 pages-inventory A5 |
| 事件 | — | 变更发 `EventBus.BOOKSHELF_REFRESH/RECREATE/NOTIFY_MAIN` | 驱动 Compose 书架刷新 |

> configBookshelf（分组样式/排序/显示书名/未读/进度/更新时间/等待更新数/FastScroller 开关+间距）为**页面私有弹窗布局**（§7 第 6 步违例），受红线登记为保留例外，后续 L2 Dialog 族合并进 `AppSelectDialog` 体系。

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppWaitDialog`（L2 族） | L2 语义 Dialog | 现有 WaitDialog 收敛去向（待接线） |
| `AppSelectDialog`（L2 族） | L2 语义 Dialog | configBookshelf 合并去向（待接线） |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/空/错 | 由 Compose 书架（P1）承担 | 壳层无独立三态 |

## 5. i18n 与无障碍
- waitDialog `"添加中..."`×2 硬编码中文 → 入 §6.1 存量清零清单，随改造迁 strings.xml 双语

## 6. 验收标准（轻量）
- [ ] 12 菜单 + configBookshelf 对话框全量保留为 View 壳（红线）
- [ ] 3 个 HandleFileContract / WaitDialog / showAddBookByUrlAlert / importBookshelfAlert 不遗漏
- [ ] EventBus 变更事件正确驱动 Compose 书架刷新
- [ ] 硬编码中文清零；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 task 12.16j）
