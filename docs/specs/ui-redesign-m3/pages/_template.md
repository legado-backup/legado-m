# 页面详细设计文档模板（_template · v2）

> **分档规则（2026-08-13 建立）**：
> - **完整 v2（本模板）**：骨架级样板页 / 已接线核心页 / 交互复杂或高风险页。约 15-20 页。
> - **轻量（_light-template.md）**：普通子页/枝叶页，继承族文档规格 + 只写差异点。其余页。
> - **N 不迁移页（内核/无 UI/可删）**：不做设计文档（pages-inventory 标 N 即覆盖）。
> 判断某页属哪档：查 ui-standards §10「分档规则」+ pages-inventory 优先级；拿不准就升一档用完整 v2。
>
> **每个页面（骨架级样板页）一份独立详细设计文档**，放本目录 `P{编号}-{页名}.md`。**主文档引用**：README「分页面设计文档」+ ui-standards §10「页面设计文档索引表」登记；**task 对应**：本文档每节标注对应 tasks.md 子任务号。另一 AI 开发本页时**只读本文档 + ui-standards §3.4 规格书**，禁止自行发明样式。
>
> 编写顺序：骨架归类 → 布局结构 → 组件选型（引用 §3.4 规格）→ 交互流程 → 状态管理 → 三态 → 验收标准 → task 对应。

## 0. 页面身份

- **页面名 / 文件锚点**：`Activity/Fragment 路径`
- **骨架归类**：S1 主框架 / S2 列表管理 / S3 表单编辑 / S4 详情阅读 / S5 全屏沉浸 / S6 弹窗透明
- **对应 task**：tasks.md `12.xx`（接线任务号）、`V-x`（真机验证任务号）、pages-inventory 行号
- **fork 借鉴来源**：forks-deep-dive §N

## 1. 设计意图（一段话）

> 本页核心目标 / 用户痛点解决 / 与旧页的差异点。**这是验收的「为什么」**。

## 2. 布局结构（文字框图 + 区块表）

```
┌─────────────────────────────────────┐
│ GlassTopAppBar 磨砂顶栏（§3.4 规格）  │ ← 返回/标题/搜索/菜单
├─────────────────────────────────────┤
│ ┌─ 区块 A ──────────────────────┐  │
│ │ 子组件（引用 §3.4 组件名+规格）  │  │
│ └─────────────────────────────────┘  │
└─────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 顶栏 | `GlassTopAppBar`（§3.4：surface α0.86，API31+ blur） | — | |
| 列表 | `LazyColumn` + `SettingsClickRow`（§3.4：h16 v12，bodyLarge） | VM StateFlow | |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `SettingsCard` | 圆角 **18dp**（非 12dp！）、标题 h16 v12、surfaceVariant、1dp elevation | 分组容器 |
| `BadgeDot` | error 底、10sp、count>99 显示 99+ | 未读角标 |

> ⚠️ 若某组件 §3.4 标 🔴（违例未修），本页**禁止直接引用**，改用已修组件或本页临时规避并登记。规格与代码冲突时以 §3.4 为准，并提交修复任务。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点击 X | | ✅ | |
| 长按 Y | `AppMenuSheet` 富操作 | ✅ | |
| 手势 Z | | | |

## 5. 状态管理（§4 范式）

- 数据源：`xxxViewModel` + `Room Flow` / `StateFlow`
- 受控组件：`data class State(...)` + `onXxx` 回调，state 全提升
- 列表：`collectAsStateWithLifecycle`；搜索词在 VM StateFlow
- **禁止**：`remember { AppConfig.* }` 帧固定；Fragment 散落 mutableStateOf

## 6. 三态（加载/空态/错误）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` / `CircularProgressIndicator` | |
| 空态 | `EmptyStatePlaceholder`（Icon+title+subtitle+action） | 文案必须 i18n |
| 错误 | `EmptyStatePlaceholder` 错误分支 / 重试 | |

## 7. i18n 与无障碍

- 新文案：`strings.xml`（zh+en）双语；禁硬编码中文
- 触控 ≥48dp；Icon contentDescription；颜色只用 colorScheme

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（区块齐全、无多无少）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致（圆角/间距/字号/色槽）
- [ ] 三态齐全；空态/错误态文案 i18n
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选，用于生成效果图）

```
Material 3 Android 阅读App 高保真UI设计稿，{页面}，低饱和护眼色系，
大量留白，卡片圆角18dp，按钮12dp，磨砂顶部栏，底部NavigationBar 4 Tab，
无花哨渐变，无高饱和撞色，小圆点未读角标，像素精度，中文界面
```

## 10. 变更记录

- YYYY-MM-DD：初始建立（关联 task 12.xx）
