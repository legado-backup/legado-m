# spec.md — 弹框遗留项 Compose 化：autoTask / urlrecord 旧 View 弹框迁移

## Intent

项目在 Archive 迁移后的 Compose UI 收尾阶段，仍有三个残留 View 实现弹框未接入 Compose 体系，分别对应迁移规格 7.11an、7.11an2 的遗留子项：

1. **自动任务日志弹框** `AutoTaskLogDialog`（`app/src/main/java/io/legado/app/ui/autoTask/AutoTaskLogDialog.kt`）：仍为 `BaseDialogFragment(R.layout.dialog_recycler_view)` + RecyclerView 列表，展示单条自动任务的最近运行时间 / 日志 / 错误 / 结果，提供清空菜单。
2. **自动任务导入弹框** `ImportAutoTaskDialog`（`app/src/main/java/io/legado/app/ui/autoTask/ImportAutoTaskDialog.kt`）：仍为 `BaseDialogFragment(R.layout.dialog_recycler_view)` + RecyclerView 列表，承载多来源解析、勾选 / 全选、逐条预览编辑、批量 upsert 导入的能力，绑定 `ImportAutoTaskViewModel`。
3. **urlrecord 页面内部旧弹框**（`app/src/main/java/io/legado/app/ui/urlrecord/UrlRecordActivity.kt`）：整页已 Compose（`UrlRecordScreen` 纯 Compose 壳层），但残留的两个 View 对话框仍走 `lib.dialogs.alert` / `lib.dialogs.selector`：
   - `showDetailDialog()`：历史记录详情 + 复制按钮。
   - `showFilterDialog()`：外层类别 selector + 内嵌 4 个值 selector（共 6 级嵌套）。

目标：三者统一迁移到 `ComposeDialogFragment` 基类 + Compose UI，复用已存在的 `AppDialogFrame` / `AppEditDialog` / `ComposeChoiceListDialog` / `ConfirmDialog` 等组件，功能等价、外观统一、移除旧 View 弹框残留，完成 7.11an / 7.11an2 收尾并在 migration-registry 回填状态。

## Scope

### In-Scope（本次实现）

1. **AutoTaskLogDialog Compose 化**：迁移为 `ComposeDialogFragment`（薄壳，无 ViewModel），工具栏标题 / 清空菜单 / 单条日志展示等价迁移。
2. **ImportAutoTaskDialog Compose 化**：迁移为 `ComposeDialogFragment`，保留并绑定 `ImportAutoTaskViewModel`；工具栏 + loading + 错误/空提示 + 底部全选/导入 + 列表行勾选/状态/打开编辑等价迁移。
3. **urlrecord 详情弹框 Compose 化**：`showDetailDialog()` 改为 Compose 详情弹框（含复制 URL 回调）。
4. **urlrecord 过滤弹框收敛**：`showFilterDialog()` 由「外层 selector + 内嵌 4 个 selector」收敛为单套 Compose 底部选择弹框（类别 / 值两级合一），保留四维过滤语义（域名 / 来源 / 方法 / 成功失败）+ 清除过滤。
5. **登记对齐**：更新 `docs/project-flow/ui-standards/migration-registry.md` 中 7.11an / 7.11an2 状态，同步 `docs/specs/` 规范索引与 `updateLog`。

### Out-of-Scope（本次不实现）

- **`dialog_recycler_view` 布局删除**：该布局仍有其它 View 弹框复用（`EffectiveReplacesDialog` / `ChangeRssArticleSourceDialog` / `AppLogDialog` / `ReadRecordDialog` / `ServersDialog` / `CrashLogsDialog` 等），本次仅迁移 autoTask 两个弹框，布局保留供其余复用者使用。
- **`ImportAutoTaskViewModel` 重构**：ViewModel 逻辑（解析 / 比对 / upsert）维持现状，不做状态范式重构。
- **`CodeDialog` / `WaitDialog` 重写**：维持原样复用，不纳入本 spec 迁移范围（见 AD-03）。
- **其它 7.11an / 7.11an2 未列项**（`TextListDialog`、`CheckRssSourceConfig`、video / image 旧弹框）不在本 spec 范围。
- 不引入新依赖、不改数据库 schema、不改 `UrlRecordActivity` 的数据加载 / DAO 查询 / 四维过滤状态字段语义。

## Approach

### Selected Approach：三项并行迁移 + 复用 Compose 弹框组件族

统一复用 `ComposeDialogFragment` 基类与既有 Compose 组件，按「复杂度」逐项迁移：

1. **AutoTaskLogDialog（最轻量）**：无回调、无数据写回，迁为 `ComposeDialogFragment` 薄壳。工具栏标题（`taskName` 空则 `getString(R.string.log)`）、清空菜单（`R.menu.app_log` 的 `menu_clear`）、单条日志展示（`time + message`）等价迁移。清空仍调 `AutoTask.update(taskId){ it.copy(lastLog=null,lastError=null,lastResult=null) }`，列表状态重置为「未运行」。顶部菜单收敛为界面内动作按钮以避免过度设计（菜单仅一项清空）。
2. **ImportAutoTaskDialog（中高复杂度）**：迁为 `ComposeDialogFragment`，保留 `viewModels<ImportAutoTaskViewModel>()` 绑定。工具栏标题 + rotateLoading 转 loading 态；错误/空提示到 `AppDialogFrame.message` 或内嵌提示文本；底部 `tvCancel`（关闭）/ `tvOk`（导入选中项，成功后 `parentFragmentManager.setFragmentResult(RESULT_KEY, bundleOf("refresh" to true))` 并关闭）/ `tvFooterLeft`（全选/取消全选 + `upSelectText()` 计数）；列表行 `cbSourceName` 勾选 + `tvSourceState`（新 / 更新 / 已存在）+ 行点击切换勾选 + `tvOpen` 打开 `CodeDialog` 单条编辑。ViewModel 的 `errorLiveData` / `successLiveData` 观察改为 Compose 受控状态渲染。
3. **urlrecord 详情弹框**：`showDetailDialog()` 用 `AppDialogFrame` 或 `ConfirmDialog` 承载详情文本 + 复制按钮回调（`sendToClip`）。
4. **urlrecord 过滤弹框**：新建单套 Compose 底部选择弹框 `UrlRecordFilterSheet`，第一级列表出「类别」、第二级出该类别下的「值」，两级合一在一套弹框内切换；`clearFilter` 收敛为顶部「清除过滤」动作。DAO 查询（`flowAllDomains` / `flowAllSourceNames` / `flowAllMethods`）仍留在 Activity 协程。

理由：`ComposeDialogFragment` 已提供主题 / 尺寸 / 墨水屏规范，复用 `AppDialogFrame` 等组件免重造轮子；三项按 risk 从低到高迁移，控制单次回归面；`dialog_recycler_view` 因其余复用者保留，防止误删破坏其它弹框。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 只迁移外观不改宿主（在 View 弹框外层套 Compose） | 保留 `BaseDialogFragment`，仅把内部 View 换 Compose | 弹框生命周期 / 尺寸 / 墨水屏行为仍走旧体系，无法接入 `ComposeDialogFragment` 规范；外观难与主题完全一致，收尾不彻底 |
| import 弹框把状态整个搬到 Compose（弃 ViewModel） | 用 `rememberSaveable` / screen state 承载解析与勾选状态 | `ImportAutoTaskViewModel` 已承载解析 / 比对 / upsert 业务，迁到 Compose 状态在配置变更下保真性差、改动面大；「ViewModel 保留、Compose 受控渲染」是成本更低的正解（见 AD-01） |
| urlrecord 过滤保留逐层 selector 原样样式 | 仅把 `lib.dialogs.selector` 换成 Compose 版逐层弹框 | 保留 6 级嵌套交互割裂；反正要 Compose 化，顺势收敛为两级合一体验更好（见 AD-02） |
| 删除 `dialog_recycler_view` 布局 | 迁移两个弹框后连布局一起删 | 该布局仍被约 8 个其它 View 弹框复用，删除会大面积破坏（见 Out-of-Scope） |

### Drawbacks

- **ImportAutoTaskDialog 交互最复杂**：勾选 / 全选计数 / 逐条编辑 / 导入确认并存，Compose 状态下需小心处理 `selectStatus` 与 `allTasks` 的联动，避免列表重排时索引错位。
- **ViewModel 的 LiveData → Compose 状态桥接**：`errorLiveData` / `successLiveData` 需转为观察式状态（`collectAsState` 或包装），需注意一次性事件（仅成功触发一次导入）与重复重组的边界。
- **过滤弹框两级合一**：从「逐层 selector」改「单弹框切换」是交互变化，需真机确认选择流不违反用户习惯；清除过滤入口需显式突出。
- **迁移后仍需保留布局文件**：`dialog_recycler_view` 继续存在于资源中（供其它复用者），短期资源与 Compose 并存不可避免。

接受上述缺点，换取「三个遗留弹框全部 Compose 化、接入统一规范、7.11an / 7.11an2 收尾」的确定性收益，且复用已验证组件、无新增依赖。

### Prior Art

- 弹框统一基类与组件族：`app/src/main/java/io/legado/app/ui/widget/compose/ComposeDialogFragment.kt`（`AppDialogSize` Confirm / Form / Management / Wide、`dialogGravity`、墨水屏支持）；`AppDialogFrame` / `rememberAppDialogStyle()`（内容块高度 ≤ 520.dp + imePadding）；`AppEditDialog`（多字段表单）；`ComposeChoiceListDialog`（单选列表弹框，可直接用于 selector 场景）；`ConfirmDialog`。
- 同规格族已完成迁移：`docs/specs/dialog-leftovers-compose/` 所在批次中，7.11ab 导入对话框族、7.11ac 各 config 弹框、7.11ae 等均采 `ComposeDialogFragment` + `setContent`（见 `docs/project-flow/ui-standards/migration-registry.md` E1 表）。
- urlrecord 页面 Compose 化壳层：`app/src/main/java/io/legado/app/ui/urlrecord/UrlRecordScreen.kt`（`LazyColumn` + `itemsIndexed(key={it.id})` + `HorizontalDivider`），本 spec 沿用其回调风格。

## Requirements

### 功能需求（FR）

- **FR-1** `AutoTaskLogDialog` 迁移为 `ComposeDialogFragment`，展示最近运行时间、日志 / 错误 / 结果文本（无则「未运行」占位），清空动作调用 `AutoTask.update` 重置三字段并刷新列表。
- **FR-2** `ImportAutoTaskDialog` 迁移为 `ComposeDialogFragment`，保留 `ImportAutoTaskViewModel` 绑定，工具栏 / loading / 错误与空提示 / 全选与导入 / 行勾选与状态 / 逐条打开编辑功能等价迁移。
- **FR-3** 导入成功后回调 `parentFragmentManager.setFragmentResult("auto_task_imported", bundleOf("refresh" to true))`；`finishOnDismiss=true` 时 `onDismiss` 仍执行 `activity?.finish()`。
- **FR-4** urlrecord 详情弹框 Compose 化：展示方法 / 状态 / 耗时 / 时间 / 域名 / URL / 来源标识，复制按钮回调调用 `sendToClip`。
- **FR-5** urlrecord 过滤弹框由 6 个嵌套 selector 收敛为单套 Compose 底部选择弹框（类别 / 值两级合一），四维过滤（域名 / 来源 / 方法 / 成功失败）+ 清除过滤语义保留。
- **FR-6** 四维过滤状态（`filterDomain` / `filterSourceName` / `filterMethod` / `filterSuccess`）语义不变，负责的查询回流逻辑不变。

### 非功能需求（NFR）

- **N1** 不引入新依赖、不改数据库 schema、不改 `UrlRecordActivity` DAO 查询 / 数据加载逻辑。
- **N2** 所有迁移弹框统一继承 `ComposeDialogFragment`，获得主题 / 尺寸 / 墨水屏规范一致行为。
- **N3** `dialog_recycler_view` 布局保留（其它复用者仍在用），不误删。
- **N4** 无残留调试日志（Grep `android.util.Log.d|Log.e` 0 残留）。
- **N5** `migration-registry.md`（7.11an / 7.11an2）与 `updateLog` 同步更新；每个弹框迁移后编译通过（`assembleAppDebug`）。

## Scenarios

### 正常场景

1. 用户查看自动任务日志：弹框显示最近运行时间与日志 / 错误 / 结果文本；点清空后日志置「未运行」，数据库字段被重置。
2. 用户从剪贴板复制的任务 JSON 导入：导入弹框解析出任务列表，为新任务勾选并点「导入全部选中」，成功后返回父页并触发刷新（`setFragmentResult`）。
3. 用户在导入列表点「打开」某条：弹出 `CodeDialog` 编辑该任务 JSON，保存后列表行更新。
4. 用户查看 URL 历史记录详情：详情弹框展示请求方法与各项元数据，点「复制 URL」复制到剪贴板。
5. 用户过滤历史记录：过滤弹框先选「类别」（域名 / 来源 / 方法 / 状态），再选该类别下的值 → 列表按新增过滤回流刷新；点「清除过滤」恢复全量。
6. 墨水瓶模式：迁移后弹框沿用 `ComposeDialogFragment` 墨水屏边框与去遮罩行为。

### 边界 / 异常场景

1. **日志为空 / 任务不存在**：任务无 `lastRunAt` / `lastLog` / `lastError` / `lastResult` 时显示「未运行」占位。
2. **导入来源非法**：`importSourceAwait` 的 `else` 分支抛 `NoStackTraceException(错格式)`时弹框显示错误提示并停止 loading（对应 ViewModel `errorLiveData`）。
3. **导入结果为空**：解析成功但无有效任务（`successLiveData` 值 `<=0`）时显示「格式错误」提示。
4. **urlrecord 过滤值列表为空**：某类别（如域名列表）无数据时，值级为空列表，应提示「无可用值」或禁用选择，不崩溃。
5. **^old 包覆盖安装**：迁移前的 `dialog_recycler_view` 绑定残留不存在（代码侧已改），无布局错绑崩溃。
6. **配置变更 / 重建**：导入弹框勾选状态重建后仍正确（走 ViewModel 状态，非 ephemeral Compose 状态）。