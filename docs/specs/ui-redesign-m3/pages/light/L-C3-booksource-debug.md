# L-C3 书源调试（BookSourceDebug）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P5-booksource.md`（S2 列表）与 `pages/P10-booksource-edit.md`（S3 表单）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P5/P10 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：BookSourceDebugActivity（`ui/book/source/debug/`，View）
- **所属族文档**：`pages/P5-booksource.md` + `pages/P10-booksource-edit.md`（继承 S3）
- **骨架归类**：S3 表单/调试页（调试搜索 + 流式输出）
- **对应 task**：tasks.md `12.45`；pages-inventory C3（优先级 P2）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S3 表单/调试页（P10 §2 顶栏/工具条范式）+ P5 搜索/菜单范式
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`AppDropdownMenu`、`AppTextDialog`（HTML 源码查看）
- 复用状态范式：`ViewModel + StateFlow`（observe{state,msg} 流式回传）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 调试会话（非列表/表单持久字段） | 流式输出 `observe{state,msg}` |
| 布局结构 | 搜索框 + 快捷前缀（++目录/--正文/text_my/xt/fx/info）+ 结果输出区；发现调试 initExploreKinds（标题::URL 长按 selector 切分类） | — |
| 交互 | 发现项长按切换分类；菜单（扫码/查看搜索/书籍/目录/正文 HTML 源码 TextDialog/刷新发现/帮助）；帮助面板焦点显隐 | — |
| 功能点 | 调试搜索/发现调试/HTML 源码查看/刷新发现 | 对照 pages-inventory C3 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppTextDialog` | L2 文本弹窗 | HTML 源码查看 |
| `SettingsSearchBar` | 搜索框受控 | 调试搜索 + 快捷前缀 |
| `SwipeActionContainer` | 左滑操作 | 发现项长按切分类的替代交互 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `LinearProgressIndicator` | 字段区顶部，初始化可省略 |
| 空态 | 不适用 | — |
| 错误 | `ThemedSnackbarHost` | 校验/保存失败提示 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档，快捷键文案资源化）

## 6. 验收标准（轻量）

- [ ] 复用 P5/P10 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C3 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.45 / pages-inventory C3）
