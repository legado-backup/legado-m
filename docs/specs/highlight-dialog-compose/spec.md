# spec.md — Highlight 三弹框 Compose 化迁移

## Intent

archive 迁移后的 Compose UI 收尾工作中，`highlight/` 三弹框仍是遗留的 View 体系组件：

- `HighlightRuleEditDialog`（[highlight/edit/HighlightRuleEditDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/highlight/edit/HighlightRuleEditDialog.kt)）— 高复杂度（报告 A）
- `HighlightRuleGroupManageDialog`（[highlight/HighlightRuleGroupManageDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/highlight/HighlightRuleGroupManageDialog.kt)）— 中复杂度（报告 D）
- `HighlightPresetRuleDialog`（[highlight/HighlightPresetRuleDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/highlight/HighlightPresetRuleDialog.kt)）— 低中复杂度（报告 C）

三者均继承 `BaseDialogFragment` + ViewBinding + `dialog_highlight_*` XML 布局。项目已具备成熟的 Compose 弹框基础设施（`ComposeDialogFragment` 基类 + `AppDialogFrame` / `AppDialog` 归档等），用户明确要求**不留尾巴**，将这三弹框统一切换到 Compose 体系，消除 highlight 弹框的 View/Compose 双轨并存。

## Scope

### In-Scope（本次实现）

1. **`HighlightRuleEditDialog` Compose 化**（高复杂）：
   - 输入区：`etName`（规则名）、`etPattern`（匹配模式）、`cbUseRegex`（正则开关）、`etReplacement`（替换模板）、`cbDotAll`（点号匹配换行）。
   - 样式区：`btnStyle` 样式设置入口 + `tvStylePreview` 实时 Span 预览（固定文案渲染 `BackgroundColorSpan` / `ForegroundColorSpan` / `StyleSpan(BOLD|ITALIC)` / `UnderlineSpan` / `StrikethroughSpan`）。样式通道编辑在 Compose 内内联实现（或按 ADR 决策保留 `HighlightStyleDialog`）。
   - 动作区：`tvCancel` / `tvOk`。
   - 数据：`HighlightRuleStore.load/save`（SharedPreferences `PreferKey.highlightRuleItems`，JSON 数组，进程内 `@Volatile` 缓存，非 Room）；保存后回调 `ReadBook.upHighlightRules()`、`ReadBook.removeHighlight()`、`HighlightRuleActivity.refreshList()`（有实现条件由调用方处理）。
   - 实例化：`create(pattern,isRegex,style,sourceHighlightTime)` / `edit(id)`，`Bundle` 传参（`id: String`）。
2. **`HighlightRuleGroupManageDialog` Compose 化**（中复杂，直接对照 `GroupManageComposeDialog` 薄壳受控范例）：
   - 分组列表（`LazyColumn` 目标）+ 每行规则计数。
   - `tvAddGroup`（新增分组）、`llViewAll`（查看全部，回调 `onSelectGroup(null)`）。
   - 每行 `tvEdit` 重命名、`tvMore` PopupMenu（`R.menu.highlight_rule_group_item`：rename / export / delete）。
   - 空态 `tvEmptyMsg`、`tvAllCount` 规则总数。
   - 内部子弹框：新增/重命名输入框（校验空/重名）、删除确认（默认分组不可删，删除后批量改回 `DEFAULT_GROUP`）、PopupMenu 分组项菜单。
   - 数据：`HighlightRuleGroupStore`（SharedPreferences `highlightRuleGroups`，load 保证首元素为默认分组）/ `HighlightRuleStore`；导出用 `sendToClip(GSON.toJson(目标规则))`；重命名时规则批量 `rule.copy(group = newName)` 双 Store save。
   - 回调：构造注入 `onChanged:(oldGroup,newGroup)->Unit`、`onSelectGroup:(String?)->Unit`；新增/删除回调 `onChanged(group,null)`；重命名回调 `onChanged(source,newGroup)`；选择后 `onSelectGroup(group)` 并 `dismiss`。
3. **`HighlightPresetRuleDialog` Compose 化**（低中复杂）：
   - 预设规则列表（`HighlightRuleStore.defaultPresetRules` 内置预设 lazy 内存，含 `title` / `displayPattern()` / `HighlightRulePreview.build(item)` 预览）。
   - 每条 `ivAdd` 添加、`ivBack` 关闭。
   - 回调：构造 `defaultGroup: String?` + `onAddRule:(HighlightRule)->Unit`；添加回调 `onAddRule(item.copy(group = defaultGroup ?: DEFAULT_GROUP))` 后 `dismiss`。

### Out-of-Scope（本次不实现）

- **不改数据模型**：`HighlightRuleStore` / `HighlightRuleGroupStore` 的存储结构、SharedPreferences key、JSON 序列化格式不变。
- **不改既有功能语义**：不新增高亮规则能力（如新 Span 类型 / 波浪下划线等），仅等价迁移视角层。已知现状上限（underline 不区分波浪/虚线/点线；box / emphasis / fontPath 字体不预览）在本次内**按现状保留**（见 AD-04）。
- **不剥离第三方 ColorPicker**：内嵌子弹框如属直接映射到既有 Compose 子组件则替换；独立不可映射项（如第三方颜色选择器 jaredrummler）保留原有 Compose 化的子组件，不做重新造轮子。
- **不迁移其它 View 弹框**：仅本规格列明的三弹框；其余 highlight 相关 View 组件不在本次范围。
- **不落库**：延续非 Room 存储，不改为 Room。

## Approach

### Selected Approach：基于 `ComposeDialogFragment` 基类 + `AppDialogFrame` 容器统一迁移，按复杂度分批落地

复用已验证的 Compose 弹框体系，将三弹框一一改造成「继承 `ComposeDialogFragment` + Compose 内容」，布局尺寸 / 重力 / 动画尽可能收敛到基类配置，不再手写 `setLayout + BaseDialogFragment 二参`：

1. **基类收敛**：`ComposeDialogFragment` 已支持 `dialogWidth` / `dialogHeight` / `dialogSize: AppDialogSize?`（Confirm / Form / Management / Wide 档位）/ `dialogGravity`（默认 CENTER）/ `dialogWindowAnimations`，并保留 `setLayout` 兼容、墨水屏支持（`dialogTheme=0` + 去 dim + `FLAG_DIM_BEHIND`）。三弹框的 `MATCH_PARENT` 全屏 / `MATCH_PARENT x 0.85f + Gravity.BOTTOM` 由基类直径/重力配置表达。
2. **容器统一**：内容统一包 `AppDialogFrame(title, message, scrollContent, content, actions)` + `rememberAppDialogStyle()`（内容块高度上限 `520.dp` + `imePadding`）。
3. **三弹框落地方案**：
   - `HighlightPresetRuleDialog`（低中复杂）：直接迁移，`LazyColumn` 预设列表 + 每行 `ivAdd`，动作仅关闭。
   - `HighlightRuleGroupManageDialog`（中复杂）：直接对照 `GroupManageComposeDialog` 薄壳受控模式——`ComposeGroupManageDialogContent(groups, onAddGroup, onRenameGroup, onDeleteGroup, onDismiss)` + `LazyColumn(items, key={it})` + 内联编辑卡片（`OutlinedTextField` + `GroupManageTextField`，`heightIn(min=240.dp, max=420.dp)`）；分隔导出 / PopupMenu 项经既有菜单机制复现。
   - `HighlightRuleEditDialog`（高复杂）：内容分「基础字段」（`AppEditDialog` 单列多字段风格，输入区）+「样式通道区」（内联选择 + 预览）两块；`tvStylePreview` 预览描线在 Compose 内用 `AnnotatedString` 渲染（见 AD-04）。
4. **数据层零改动**：`HighlightRuleStore` / `HighlightRuleGroupStore` 读取与回调调用点复用，仅 UI 壳层替换。

理由：复用已交付的 Compose 弹框基础设施，避免再造一套弹框框架；薄壳受控模式与 `GroupManageComposeDialog` 范例一致，可快速对齐实现；按复杂度分批降低单次迁移回归面。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 保留 BaseDialogFragment + XML，仅更新兜底 | 维持 View 体系，仅改样式/修 bug | 与 Compose UI 收敛目标相悖；继续保有 View/Compose 双轨，遗留尾巴未除，用户明确不接受 |
| 完全新建独立 Compose 弹框组件（不复用 ComposeDialogFragment） | 从零写一套 highlight 专用弹框 | 与已交付的 `ComposeDialogFragment` / `AppDialogFrame` 双实现，观感难保证一致；重构面积大 |
| 弹框内容整体改用 Compose，但仍走 `BaseDialogFragment`（不自带基类尺寸/重力） | 保留旧基类只换内容 | 无法复用基类直径/重力/动画/墨水屏能力，仍需手写 `setLayout`，半吊子迁移 |
| `HighlightRuleEditDialog` 样式区继续内嵌 `HighlightStyleDialog`/`FontSelectDialog`/`ColorPickerDialog`，不做 Compose 内联 | 保留子弹框结构 | 详见 AD-03 权衡；若内联迁移收益低于成本则保留子弹框 |
| 引入自定义 Span 增强预览（区分波浪/虚线等） | 借迁移扩展预览能力 | 属功能新增，超本次收尾范围；与「等价迁移、不留新增负担」冲突，纳入后续评估 |

### Drawbacks

- **高复杂弹框成本高**：`HighlightRuleEditDialog` 含样式通道 + 多子弹框 + 实时预览，Compose 内重写工作量大于简单弹框，需谨慎处理状态提升与预览重绘。
- **子弹框嵌套链路复杂**：`HighlightStyleDialog`（`StyleHost` 接口）+ `FontSelectDialog` + `ColorPickerDialog` 三层嵌套，Compose 内联后调用链 / 回调映射（`dialogId + applyChannelColor`）需逐一核对，回归风险集中在样式区。
- **底部弹框行为差异**：`Gravity.BOTTOM + 0.85f 高` 与 `AppDialogFrame` 默认 CENTER 档位差异需通过 `dialogGravity` / `dialogSize` 显式配置，否则观感与现有行为不一致。
- **预览保真度有限**：`AnnotatedString` 内联渲染受限于 TextStyle 所能表达的 Span 类型，部分 Span（自定义画笔）无法 1:1 复刻（见 AD-04）。

接受上述缺点，换取 highlight 弹框彻底 Compose 化、消除双轨，并复用已交付基类与容器。

### Prior Art

- `ComposeDialogFragment` 基类：[app/src/main/java/io/legado/app/ui/widget/compose/ComposeDialogFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/compose/ComposeDialogFragment.kt)（`dialogTheme=Theme_Legado_ComposeDialog_Center`、`setStyle(STYLE_NO_TITLE)`、`dialogSize` 档位、墨水屏支持）。
- 配套容器：`AppDialogFrame` + `rememberAppDialogStyle()`（[AppComposeDialogs.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/compose/AppComposeDialogs.kt)，内容块高上限 `520.dp` + `imePadding`）。
- 薄壳受控范例：`GroupManageComposeDialog`（[app/src/main/java/io/legado/app/ui/widget/compose/GroupManageComposeDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/compose/GroupManageComposeDialog.kt)）。
- 通用表单弹框：`AppEditDialog`（[app/src/main/java/io/legado/app/ui/widget/components/AppEditDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/components/AppEditDialog.kt)）。
- 「我的」头部 Compose 收敛：`docs/specs/my-topbar-unify/`；archive 迁移大类：`docs/specs/archive-ui-migration-202608/`。

## Requirements

### 功能需求（FR）

- **FR-1** `HighlightRuleGroupManageDialog` 改为继承 `ComposeDialogFragment`，分组列表 `LazyColumn` 渲染，支持每组规则计数、新增、重命名、导出、删除、查看全部、空态与总数展示；行为与现有 XMLL 等价。
- **FR-2** `HighlightPresetRuleDialog` 改为继承 `ComposeDialogFragment`，`LazyColumn` 渲染 `defaultPresetRules` 预设列表（含标题 / `displayPattern()` 文案 / 预览描线），每条可添加到指定分组，行为等价。
- **FR-3** `HighlightRuleEditDialog` 改为继承 `ComposeDialogFragment`，基础字段（name / pattern / useRegex / replacement / dotAll）编辑与保存行为等价；样式通道区提供通道选择 + 预览，保存后触发既有刷新回调（`ReadBook.upHighlightRules()` / `removeHighlight()` / `HighlightRuleActivity.refreshList()`）。
- **FR-4** 三弹框的尺寸 / 重力 / 动画统一由 `ComposeDialogFragment` 基类配置表达（全屏 `MATCH_PARENT`、`0.85f + Gravity.BOTTOM`），不再手写 `setLayout`。
- **FR-5** 数据层与回调契约零改动：`HighlightRuleStore` / `HighlightRuleGroupStore` 存储结构、`onChanged` / `onSelectGroup` / `onAddRule` 回调、`Bundle` 传参（`id`）语义不变。
- **FR-6** 原 XML 布局与对应 databinding 类删除，无无主资源残留。

### 非功能需求（NFR）

- **N1** 不引入新第三方依赖；复用既存 Compose 组件与基类。
- **N2** 无残留调试日志（Grep `android.util.Log.d|e` 为 0）。
- **N3** updateLog 同步更新（编译前）。
- **N4** migration-registry 状态登记与 `tasks.md` 对齐（见 AD-05）。
- **N5** 迁移不改变既有业务逻辑（仅 UI 壳层替换）；已知现状上限（独立波浪线/盒子差异）按现状保留。

## Scenarios

### 正常场景

1. 用户打开阅读 → 长按选中 → 高亮菜单 → 编辑规则文本：弹出 Compose `HighlightRuleEditDialog`，输入名称 / 模式，切换正则 / 点号匹配，实时看到下方预览描线更新，保存后高亮规则在书内实时生效。
2. 用户进入「高亮规则管理」→ 分组列表：底部 Compose 分组管理弹框展示分组 + 计数，点添加弹内联输入，重命名 / 导出 / 删除经行内菜单，删除默认分组被拒绝并提示。
3. 用户点「查看全部」：回调 `onSelectGroup(null)`，弹框关闭，列表展示全部规则。
4. 用户进入阅读 → 添加高亮 → 选预设：弹出预设列表，点某条 `ivAdd`，调 `onAddRule` 后弹框关闭。

### 边界 / 异常场景

1. 新增 / 重命名分名为空或与现有重名：输入框就地校验并提示，不落库。
2. 删除非空分组：二次确认后删除，组内规则批量改回 `DEFAULT_GROUP`；默认分组不可删。
3. 覆盖安装（旧 View → 新版 Compose）：不再 inflate 已删除 XML 布局，无残留 ViewBinding 崩溃。
4. 夜间 / 日间主题切换：弹框背景 / 描线颜色随 `rememberAppDialogStyle()` 动态刷新。
5. 墨水屏设备：经基类 `dialogTheme=0` + 去 dim + `FLAG_DIM_BEHIND` 生效，无异常灰度渲染。
6. 规则名 / 模式输入超长或非法正则：`AppEditDialog` 校验兜底，行为与旧版等价（不额外破坏）。