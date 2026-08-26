# tasks.md — Highlight 三弹框 Compose 化迁移

> 分阶段落地：准备 → 核心实现（按复杂度 HL 高 / MD 中 / LO 低中）→ 验证 → 收尾。按复杂度分批，前序编译通过再进下一批。

## 1. 准备阶段

- [ ] 1.1 核对 `ComposeDialogFragment` 基类能力（`dialogWidth`/`dialogHeight`/`dialogSize`/`dialogGravity`/`dialogWindowAnimations`/墨水屏分支），确认非标准档位承载（全屏、`0.85f + Gravity.BOTTOM`）
- [ ] 1.2 核对 `AppDialogFrame` + `rememberAppDialogStyle()` 容器用法（内容块高上限 `520.dp` + `imePadding`）
- [ ] 1.3 研究 `GroupManageComposeDialog` 薄壳受控范例，提取复用 API（`ComposeGroupManageDialogContent(...)` 签名、内联编辑卡片 `GroupManageTextField`）
- [ ] 1.4 通读三弹框源文件，确认 `HighlightRuleStore` / `HighlightRuleGroupStore` 存储接口、回调契约、`Bundle` 传参（`id`）
- [ ] 1.5 盘点内嵌子弹框（`HighlightStyleDialog`/`FontSelectDialog`/`ColorPickerDialog`）的调用点与 `StyleHost` / `applyChannelColor` 通道映射

## 2. 核心实现

### 2.1 HighlightPresetRuleDialog（LO 低中复杂）

- [x] 2.1.1 改为 `ComposeDialogFragment`，`dialogGravity = Gravity.BOTTOM` + 底部高度档
- [x] 2.1.2 `LazyColumn` 渲染 `defaultPresetRules`，每行：标题 + `displayPattern()` 文案 + `HighlightRulePreview.build(item)` 预览描线 + 添加图标
- [x] 2.1.3 添加回调 `onAddRule(item.copy(group = defaultGroup ?: DEFAULT_GROUP))` → `dismiss()`；关闭动作接入
- [x] 2.1.4 编译通过（compileAppDebugKotlin）

### 2.2 HighlightsRuleGroupManageDialog（MD 中复杂）

- [x] 2.2.1 改为薄壳受控模式，改 `ComposeDialogFragment`，`dialogGravity = Gravity.BOTTOM` + 底部高度档
- [x] 2.2.2 内容复用 `ComposeGroupManageDialogContent(groups, onAddGroup, onRenameGroup, onDeleteGroup, onDismiss)`，`LazyColumn(items, key={it})` + 每行计数
- [x] 2.2.3 新增/重命名内联编辑卡片（校验空/重名），删除确认子弹框（默认分组禁删，删除后规则批量改回 `DEFAULT_GROUP`）
- [x] 2.2.4 PopupMenu 复现 `R.menu.highlight_rule_group_item`（rename / export / delete）；导出走 `sendToClip(GSON.toJson(目标规则))`
- [x] 2.2.5 接线 `onChanged(group,null)`（增/删）、`onChanged(source,newGroup)`（重命名）、`onSelectGroup(group)`（选中后 dismiss）
- [x] 2.2.6 编译通过（compileAppDebugKotlin）

### 2.3 HighlightRuleEditDialog（HL 高复杂）

- [x] 2.3.1 改为 `ComposeDialogFragment`，全屏尺寸档位
- [x] 2.3.2 基础字段区：name / pattern / useRegex(`Switch`) / replacement / dotAll(`Switch`)，受控状态
- [x] 2.3.3 样式通道区（按 AD-03）：fill / textColor / bold / italic / underline / strike / fontPath 内联选择，映射 `HighlightRule.styleJson` 通道
- [x] 2.3.4 预览（按 AD-04）：固定文案 `AnnotatedString` 渲染 `Background`/`Foreground`/`StyleSpan(BOLD|ITALIC)`/`Underline`/`Strikethrough`，随样式通道变更实时刷新；保持原局限
- [x] 2.3.5 内嵌子弹框处置：字体/取色通道转 Compose 子弹框，`applyChannelColor`/`StyleHost` 通道映射重写、衔接 `dialogId`
- [x] 2.3.6 `tvOk` 保存：`HighlightRuleStore.save` + `ReadBook.upHighlightRules()` / `ReadBook.removeHighlight()` / `HighlightRuleActivity.refreshList()`（存在性调用）
- [x] 2.3.7 `create(...)`/`edit(id)` 实例化与 `Bundle` 传参（`id`）保留
- [x] 2.3.8 编译通过（compileAppDebugKotlin）

## 3. 验证阶段

- [x] 3.1 资源清理：删除 5 个 XML 布局（dialog_highlight_rule_edit / dialog_highlight_rule_group_manage / dialog_highlight_preset_rule / item_highlight_rule_group / item_highlight_preset_add）+ 1 个 menu（highlight_rule_group_item），确认对应 ViewBinding 类不再引用
- [ ] 3.2 全量编译：`./gradlew assembleAppDebug`（BUILD SUCCESS）
- [ ] 3.3 覆盖安装/启动无崩：不 inflate 已删布局，无 ViewBinding 残留崩溃
- [ ] 3.4 分组管理真机回归：新增/重命名/导出/删除（含默认分组禁删、批量改分组）、查看全部、空态与总数
- [ ] 3.5 预设弹框真机回归：预设列表渲染、预览描线、添加回调与分组归属
- [ ] 3.6 Edit 弹框真机回归：字段编辑、正则/点号开关、样式通道切换预览实时刷新、保存触发书内高亮刷新，夜/日主题切换、墨水屏无异常
- [ ] 3.7 残留日志确认：Grep `android.util.Log.d|e` 为 0

## 4. 收尾阶段

- [ ] 4.1 migration-registry 新增三弹框条目，状态与 2.x 勾选对齐
- [ ] 4.2 `app/src/main/assets/updateLog.md` 追加三弹框 Compose 化条目（编译前）
- [ ] 4.3 `docs/INDEX.md` 登记本 spec
- [ ] 4.4 构建后清理构建 daemon（`stop-daemons.bat`）

## AOAdapt 日志

- 实施阶段记录：遇到问题按 `Action → Observation → Adapt` 追加。

  - 模板：
    ```
    ### AoA: <问题简述>
    - Action: 采取的行动
    - Observation: 观察到的结果
    - Adapt: 调整后的下一步
    ```