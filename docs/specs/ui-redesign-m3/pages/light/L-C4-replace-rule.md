# L-C4 替换净化（ReplaceRule）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P5-booksource.md`（S2 列表）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P5 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：ReplaceRuleActivity + ReplaceEditActivity（`ui/replace/`，View）
- **所属族文档**：`pages/P5-booksource.md`（继承 S2+S3）
- **骨架归类**：S2 列表管理页（列表）+ S3 表单编辑页（编辑）
- **对应 task**：tasks.md `12.46`；pages-inventory C4（优先级 P2）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P5 §2：GlassTopAppBar + 搜索 + LazyColumn + 批量栏）+ S3 表单页（P10 §2：字段分组 + KeyboardToolPop）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`SelectActionBarCompose`、`SwipeActionContainer`、`EmptyStatePlaceholder`、`SettingsCard`、`SettingsClickRow`、`AppDropdownMenu`
- 复用状态范式：`ViewModel + StateFlow`（多选 `isSelecting = selectedUrls.isNotEmpty()` 派生）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | ReplaceRule Room DAO；onDestroy 全局刷新 `ContentProcessor.upReplaceRules` | 列表数据 |
| 布局结构 | 列表页搜索（enabled/disabled/no_group/group:xxx）；编辑页字段 name/group/**pattern**/cb_use_regex/replacement/scope_title/scope_content/scope/excludeScope/timeout(3000) | — |
| 交互 | 菜单（添加/分组管理/启用停用筛选/删除选中/在线/本地/扫码导入/帮助）；多选（启用停用/置顶置底/导出JSON）；拖拽排序滑选；编辑页菜单（全屏编辑/保存/复制粘贴）+ KeyboardToolPop + 正则帮助 | — |
| 功能点 | 替换规则列表 + 编辑（正则净化） | 对照 pages-inventory C4 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog` | L2 字段输入弹窗 | 字段编辑（非 pattern 的简单字段） |
| `SettingsToggleRow` | h16 v12 开关行 | cb_use_regex |
| `KeyboardToolPop`（View 保留） | 编辑器补全条 | pattern/replacement 编辑（同 P10 红线） |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无规则空态 |
| 错误 | `EmptyStatePlaceholder` | 搜索/校验失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P5 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C4 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.46 / pages-inventory C4）
