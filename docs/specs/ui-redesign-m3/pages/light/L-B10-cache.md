# L-B10 缓存管理（CacheActivity）· 轻量设计文档

> **适用**：B10 缓存管理为枝叶页，继承族文档 `pages/P2-reader.md`（S2 列表管理范式）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/cache/CacheActivity.kt`（665 行）
- **所属族文档**：`pages/P2-reader.md`（继承 S2 列表范式）
- **骨架归类**：S2 列表管理页（分组加载）
- **对应 task**：tasks.md `12.42`；pages-inventory B10（task 待接线）

## 1. 继承声明
- 复用骨架：S2 列表管理（Room Flow 分组订阅 + 4 排序）
- 复用组件（§3.4）：`GlassTopAppBar`、`AppDropdownMenu`（菜单）、`GroupHeader`（分组）、L2 Dialog 族（并发率/自定义导出）、`SwipeActionContainer`（item 长按下载菜单）
- 复用状态范式：`ViewModel + Flow`；事件驱动（EventBus）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | 单书 | `flowByGroup` + 4 排序分组加载 | 缓存分项 |
| 菜单 | — | 下载当前章起/全部/停止/导出全部/启用替换/自定义导出/导出WebDav/并行导出/导出类型 txt\|epub/缓存并发率 Dialog/日志/缓存分项统计 buildStorageBreakdown 逐项删除 | 差异功能点 |
| 自定义导出 | — | Dialog（全部或章节范围+验证/每卷章数/epub文件名JS实时解析） | 私有弹窗待 L2 族收敛 |
| 事件 | — | UP_DOWNLOAD/UP_DOWNLOAD_STATE/SAVE_CONTENT；ExportBookService 进度 | 差异 |
| item | — | 长按下载菜单 | |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppNumberPickerDialog`（L2 族） | L2 语义 Dialog | 缓存并发率 Dialog 收敛去向 |
| `AppSelectDialog`（L2 族） | L2 语义 Dialog | 自定义导出范围/类型去向 |
| `SwipeActionContainer` | 左滑固定宽、error 删除/primary | item 长按下载菜单 |
| `GroupHeader` | titleSmall Bold、行≥48dp | 分组头 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 分组加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | title 走 strings.xml i18n |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；导出类型/字符集/文件夹等选项无硬编码中文

## 6. 验收标准（轻量）
- [ ] 按分组加载（flowByGroup+4 排序）；菜单全功能实现（下载/停止/导出全部/启用替换/自定义导出/WebDav/并行导出/缓存并发率/缓存分项统计）
- [ ] 自定义导出 Dialog（全部或章节范围/每卷章数/epub文件名JS）实现
- [ ] ExportBookService 进度 + 事件（UP_DOWNLOAD/UP_DOWNLOAD_STATE/SAVE_CONTENT）；item 长按下载菜单
- [ ] 三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.42
