# L-C20 关于 / 阅读记录（About / ReadRecord）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：AboutActivity + AboutFragment + ReadRecordActivity（`ui/about/`，View，PreferenceFragmentCompat/RecyclerView）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2）
- **骨架归类**：S2 列表管理页（关于信息列表 + 阅读记录列表）
- **对应 task**：tasks.md `12.5C`；pages-inventory C20（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P4 §2）+ 统计卡 MetricGrid（阅读记录顶部总时长）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsClickRow`、`SettingsSearchBar`、`SettingsToggleRow`、`MetricGrid`、`AppDropdownMenu`、`AppTextDialog`、`ConfirmDialog`
- 复用状态范式：`ViewModel + StateFlow`（搜索实时过滤 + 排序持久化）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | About 静态 + ReadRecord Room（阅读时长） | 列表数据 |
| 布局结构 | About：公众号文字高亮；AboutFragment：开源贡献者/更新日志 MD Dialog/检查更新 giteeUpdate+UpdateDialog/发邮件/license/disclaimer/privacyPolicy MD/复制公众号/crashLog CrashLogsDialog/saveLog zip 打包/createHeapDump 堆转储；ReadRecord：搜索实时过滤 + 排序子菜单（书名/时长/最近，持久化） | — |
| 交互 | ReadRecord：menu_enable_record 开关；顶部总时长 + 清除确认；item 单击查书（存在跳读/不存在跳搜索）；行内删除单条 | — |
| 功能点 | 关于信息 + 更新检查 + 日志导出 + 阅读记录 | 对照 pages-inventory C20 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `MetricGrid` | MetricTile 12dp 圆角 | 阅读记录顶部总时长统计卡 |
| `AppTextDialog` | L2 文本弹窗 | 更新日志/MD 弹窗（license/disclaimer/privacyPolicy） |
| `ConfirmDialog` | L2 语义确认弹窗 | 清除阅读记录确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 阅读记录加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无记录空态 |
| 错误 | `EmptyStatePlaceholder` | 加载失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C20 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.5C / pages-inventory C20）
