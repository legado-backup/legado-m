# L-D8 规则订阅（RuleSub）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P8-overlays.md`（S6 弹窗/透明窗族）+ `pages/P7-rss.md`（S2 列表管理），本文只写「继承 + 差异」。开发本页只读本文档 + P8 + P7 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RuleSubActivity（`ui/rss/subscription/`，View，规则订阅/分组）
- **所属族文档**：`pages/P8-overlays.md`（S6 弹窗族）+ `pages/P7-rss.md`（S2 列表）
- **骨架归类**：S2 列表管理页 + S6 弹窗/编辑
- **对应 task**：tasks.md `12.5F`；pages-inventory D8（优先级 P3）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理骨架（见 P7 §2）+ S6 三层弹窗体系（见 P8 §2：L1 Sheet / L2 Dialog 族 / L3 透明窗壳）
- 复用组件（§3.4）：`GlassTopAppBar`、`EmptyStatePlaceholder`、`ConfirmDialog`、`AppEditDialog`、`AppSelectDialog`
- 复用状态范式：ViewModel + Room Flow（ruleSubDao）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | ruleSubDao.flowAll + 空提示 | 独有 DAO |
| 路由 | 点击 openSubscription 按 type→ImportBookSourceDialog(0) / ImportRssSourceDialog(1) / ImportReplaceRuleDialog(2) | 智能分发 |
| 编辑 | 菜单（新增/条目编辑 DialogRuleSubEditBinding）：spType + 名称 + URL + autoUpdate + silentUpdate + interval **联动（interval=0 禁用两者 / 开自动更新默认 24h + URL 查重）** | 独有表单逻辑 |
| 功能点 | 删除；拖拽排序 upOrder | — |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空订阅列表 |
| `AppEditDialog` | EditField 列表 + 间距 8dp | 新增/编辑条目（替代 DialogRuleSubEditBinding） |
| `AppSelectDialog` | RadioButton primary 高亮 | 订阅类型 spType 选择 |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp、destructive 确认钮 error | 删除确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 订阅列表骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空订阅 + 空提示 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；表单输入触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 S2 骨架 + S6 弹窗族，无私有复制组件
- [ ] 功能点对照 pages-inventory D8 无遗漏（flowAll/type 分发/编辑联动 interval/URL 查重/删除/拖拽 upOrder）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-15：12.5F 交付——Compose 顶栏桥接（GlassTopAppBar + 添加按钮 + ConfirmDialog 删除确认），条目删除由私有 PopupMenu 收敛为 Compose ConfirmDialog，删除 source_sub_item/source_subscription 两个无引用菜单资源，RecyclerView 列表 + DialogRuleSubEditBinding 编辑表单（独有联动逻辑）内核保留；tasks.md 标记 ✅
- 2026-08-13：初始建立（关联 pages-inventory D8），task 12.5F
