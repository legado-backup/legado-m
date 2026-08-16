# L-B7 书籍信息编辑（BookInfoEditActivity）· 轻量设计文档

> **适用**：B7 书籍信息编辑为枝叶表单页，继承族文档 `pages/P3-bookinfo.md`（S4 详情）+ `pages/P10-booksource-edit.md`（S3 表单骨架）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/info/edit/BookInfoEditActivity.kt`
- **所属族文档**：`pages/P3-bookinfo.md` + `pages/P10-booksource-edit.md`（继承 S3 表单骨架）
- **骨架归类**：S3 表单/编辑器页
- **对应 task**：tasks.md `12.50`；pages-inventory B7（task 待接线）

## 1. 继承声明
- 复用骨架：S3 表单编辑（GlassTopAppBar + SettingsCard 分组字段 + 底部保存，P10 §2）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsCard`、`SettingsClickRow`/`AppEditDialog`（L2 族）
- 复用状态范式：`ViewModel + StateFlow`（P10 §3）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | BookInfo 读展示 | 编辑字段写回 | 差异：读→写 |
| 字段 | — | 书名/作者/类型（文本/音频/图片/视频）/封面URL/简介 | 表单字段 |
| 换封面 | — | 三途径：ChangeCoverDialog / 本地 selectCover / 刷新 tvRefreshCover | 差异功能点 |
| 保存 | — | `BookHelp.updateCacheFolder` | 差异副作用 |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog`（L2 族） | L2 语义 Dialog | ChangeCoverDialog 收敛去向 |
| `SettingsClickRow` | h16 v12、bodyLarge | 字段行 |
| `GlassTopAppBar` | surface 实底、titleMedium | 顶栏 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `LinearProgressIndicator` | 字段区顶部，初始化可省略 |
| 空态 | — | 不适用 |
| 错误 | `ThemedSnackbarHost` | 校验/保存失败提示 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；字段标签无硬编码中文（同 P10）

## 6. 验收标准（轻量）
- [ ] 改书名/作者/类型/封面URL/简介全部可编辑保存
- [ ] 换封面三途径（ChangeCoverDialog/本地 selectCover/刷新 tvRefreshCover）实现
- [ ] 保存调用 BookHelp.updateCacheFolder；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.50
