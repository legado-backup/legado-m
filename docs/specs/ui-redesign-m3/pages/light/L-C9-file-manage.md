# L-C9 文件管理（FileManage / HandleFile）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：FileManageActivity + HandleFileActivity（`ui/file/`，View）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2+S6）
- **骨架归类**：S2 列表管理页（文件列表）+ S6 弹窗/选择器（HandleFile）
- **对应 task**：tasks.md `12.56`；pages-inventory C9（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P4 §2）+ S6 弹窗体系（P8 §2 L2 Dialog 族/L3 透明窗壳）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`EmptyStatePlaceholder`、`AppEditDialog`（手动输入目录）
- 复用状态范式：`ViewModel + StateFlow`

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 文件系统（无 Room） | 路径导航 |
| 布局结构 | FileManage：路径导航条 PathAdapter（root+逐级跳）/文件列表（上级/文件夹/文件）/搜索过滤/长按删除/返回键回上级 | — |
| 交互 | HandleFile：mode 分发（DIR_SYS/DIR/FILE/EXPORT/IMAGE）；系统目录选择器/应用内 FilePickerDialog/**手动输入目录**（校验 isExternalStorage）/系统文件选择器/图片选择/**手动输入图片链接**；EXPORT 上传 URL 或存本地；统一 Intent 回传；存储权限 | — |
| 功能点 | 文件浏览 + 多模式选择回传 | 对照 pages-inventory C9 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog` | L2 字段输入弹窗 | 手动输入目录（isExternalStorage 校验）/手动输入图片链接 |
| `AppSelectDialog` | L2 选择弹窗 | 文件/图片选择（等价 FilePickerDialog） |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 目录加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空目录空态 |
| 错误 | `EmptyStatePlaceholder` | 存储权限拒绝/路径无效 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C9 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.56 / pages-inventory C9）
