# L-C6 词典规则（DictRule）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P5-booksource.md`（S2 列表）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P5 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：DictRuleActivity（`ui/dict/rule/`，View）
- **所属族文档**：`pages/P5-booksource.md`（继承 S2+S3）
- **骨架归类**：S2 列表管理页（列表）+ S3 表单编辑页（编辑全屏 Dialog）
- **对应 task**：tasks.md `12.55`；pages-inventory C6（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P5 §2）+ S3 表单编辑页（P10 §2 全屏编辑 + 未保存拦截）
- 复用组件（§3.4）：`GlassTopAppBar`、`SelectActionBarCompose`、`SwipeActionContainer`、`EmptyStatePlaceholder`、`SettingsCard`、`SettingsClickRow`、`AppDropdownMenu`
- 复用状态范式：`ViewModel + StateFlow`（多选派生 + 未保存拦截）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | DictRule Room DAO | 列表数据 |
| 布局结构 | 列表 + 滑选 + 拖拽；编辑为**全屏 Dialog 三字段** name/urlRule/showRule（带规则补全） | 非独立 Activity |
| 交互 | 菜单（添加/本地在线扫码导入/**导入默认**/帮助）；多选（启用停用/导出）；全屏编辑；dismiss 未保存拦截 | — |
| 功能点 | 词典规则列表 + 全屏编辑 + 导入默认 | 对照 pages-inventory C6 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsCard` | 卡 18dp | 编辑字段分组 |
| `KeyboardToolPop`（View 保留） | 编辑器补全条 | 规则字段补全（同 P10 红线） |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无规则空态 |
| 错误 | `EmptyStatePlaceholder` | 编辑校验失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P5 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C6 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.55 / pages-inventory C6）
