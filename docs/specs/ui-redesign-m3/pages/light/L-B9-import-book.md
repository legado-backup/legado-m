# L-B9 导入（ImportBook / BaseImportBook / RemoteBook）· 轻量设计文档

> **适用**：B9 导入为枝叶页，继承族文档 `pages/P1-bookshelf.md`（S2 列表）+ `pages/P8-overlays.md`（S6 弹窗/Dialog 族）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/import/ImportBookActivity.kt` + BaseImportBookActivity + RemoteBookActivity
- **所属族文档**：`pages/P1-bookshelf.md`（S2 列表）+ `pages/P8-overlays.md`（S6 弹窗族）
- **骨架归类**：S2 列表管理页（目录导航）
- **对应 task**：tasks.md `12.51`；pages-inventory B9（task 待接线）

## 1. 继承声明
- 复用骨架：S2 列表管理（目录导航列表）
- 复用组件（§3.4）：`GlassTopAppBar`、`AppDropdownMenu`（菜单）、L2 Dialog 族（ServersDialog/确认）
- 复用状态范式：`ViewModel + Flow`；菜单全 @string

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| Base | — | 首次 setBookStorage 强制选 SAF 目录；压缩包点击分发（单文件直导/多文件 selector/重导入确认）；startReadBook | 差异核心 |
| 本地 | — | 目录导航（nextDoc/tvGoBack/back）；菜单（选择文件夹/扫描子文件夹/导入文件名JS/排序）；"加入书架"/删除；文件点击 startRead | |
| 远程 | — | WebDav 目录浏览/服务器配置 ServersDialog/日志/帮助/排序；"加入书架"；startRead 未下载→showRemoteBookDownloadAlert；addToBookShelfAgain | |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppSelectDialog`（L2 族） | L2 语义 Dialog | 多文件 selector / ServersDialog 收敛去向 |
| `AppEditDialog`（L2 族） | L2 语义 Dialog | 导入文件名JS/服务器配置去向 |
| `AppDropdownMenu` | M3 DropdownMenu | 本地/远程菜单 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 文件列表加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空目录提示 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；SAF 引导/下载确认无硬编码中文

## 6. 验收标准（轻量）
- [ ] Base 首次 setBookStorage 强制选 SAF；压缩包点击分发（单/多/重导入确认）；startReadBook
- [ ] 本地目录导航 + 菜单（选择文件夹/扫描子文件夹/导入文件名JS/排序）+ 加入书架/删除 + 文件点击 startRead
- [ ] 远程 WebDav 目录浏览 + ServersDialog + showRemoteBookDownloadAlert
- [ ] 三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.51
