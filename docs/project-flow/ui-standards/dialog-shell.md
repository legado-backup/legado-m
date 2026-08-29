# §9.5 对话框壳（Dialog Shell）

> 本文档说明当前对话框体系的三种壳：Compose 对话框族、统一设置壳、以及旧 `base/BaseDialogFragment` 的淘汰边界。
> 关联任务：`archive-ui-migration-202608/tasks.md` E1（弹框）类迁移。

## 一、`ComposeDialogFragment` — Compose 对话框基类

**文件**：`app/src/main/java/io/legado/app/ui/widget/compose/ComposeDialogFragment.kt`

| 成员 | 说明 |
|------|------|
| 继承 | `DialogFragment` |
| `dialogTheme` | 默认 `R.style.Theme_Legado_ComposeDialog_Center`（e-ink 模式下 style 置 0） |
| `dialogWidth/dialogHeight` | 默认 `MATCH_PARENT/WRAP_CONTENT` |
| `dialogSize`（`AppDialogSize?`） | 由 `AppUiTokens.AppDialogSize` 决定宽度档位（Confirm/Form/Management/Wide），据此换算 `widthFraction` 与 `maxWidthDp` |
| `dialogGravity` | 默认 `Gravity.CENTER`，可覆盖为 TOP/BOTTOM |
| `dialogWindowAnimations` | 默认 `R.style.AnimDialogCenter` |
| 返回键处理 | 通过 `OnBackPressedCallback` + `setOnKeyListener` 走 `handleDialogBack()`（可取消则 dismissAllowingStateLoss） |
| e-ink 适配 | `isEInkMode` 时取消 dim、清动画、加对应方向边框 `bg_eink_border_bottom/top/dialog` |
| `show()` | 先 `beginTransaction().remove(this)` 再去重后再显示，并 try 兜底（失败打 LogUtils） |

### 用法
子类继承 `ComposeDialogFragment`，在 `onCreateDialog`/内容中放 ComposeView，并常用各 `Compose*Dialog.create()` 工厂 + `Fragment.showCompose*Dialog()` 便捷入口（见 `ComposeDialogAdapters.kt`）。宽高由档位自动换算，无需手动 `setLayout`。

## 二、`AppComposeDialogs` — Compose 对话框族总成

**文件**：`app/src/main/java/io/legado/app/ui/widget/compose/AppComposeDialogs.kt`

- **样式/框架**：`AppDialogStyle`（`rememberAppDialogStyle()` 记忆）、`AppDialogFrame`（对话框内容统一壳/背景图），辅助行组件 `AppDialogSwitchRow`/`AppDialogOptionGroup`/`AppDialogSliderRow`/`AppDialogSliderGrid`/`AppDialogSliderItem`。
- **对话框类**（均 `ComposeDialogFragment()` 子类）：
  - `ComposeTextInputDialog`（单文本输入/密码）
  - `ComposeSuggestionTextInputDialog`（建议补全文本）
  - `ComposeTextFormDialog`（多字段表单）
  - `ComposeNumberPickerDialog`（数字选择器）
  - `ComposeMultiChoiceDialog`（多选）
  - `ComposeConfirmDialog`（确认，支持 danger / neutral / messageInContent）
  - `ComposeSingleChoiceDialog`（单选）
  - `ComposeActionListDialog`（动作列表）
  - `ComposeFetchedModelDialog`（异步取数模型）
- **便捷入口**：`ComposeDialogAdapters.kt` 提供 `Fragment.showComposeConfirmDialog/showComposeActionListDialog/showComposeSingleChoiceDialog` 等，内部通过 `showDialogFragment(ComposeX.create(...))` 弹出。

> 另 `GroupManageComposeDialog.kt`（分组管理）、`ComposeChoiceListDialog.kt`（选择列表）同位于 `ui/widget/compose/`，分别供 E1 分组弹框与单选列表复用。

### AppDialogFrame 滚动嵌套契约（禁令，2026-08-28 铁证新增）

**崩溃模式**：`AppDialogFrame` 默认 `scrollContent = true`，content 外包 `Column(verticalScroll)`——外层自身有 `heightIn(max = 520.dp)` 有界，但它给**子项传无限高度**（verticalScroll 语义）。若 content 内再出现**无高度约束**的垂直滚动组件（`LazyColumn` / 根级自带 `.verticalScroll()` 的组件），内层收到 `maxHeight = Infinity` → `checkScrollableContainerConstraints` 抛 `IllegalStateException`，弹框一测量即闪退。

**铁证**：2026-08-28 高亮规则编辑（`HighlightRuleEditDialog` 内嵌 `HighlightStyleSheet`）与预设规则（`HighlightPresetRuleDialog` 内嵌无约束 `LazyColumn`）两处点开即闪退。

**二选一范式（混用 = 崩溃）**：

| 场景 | 范式 | 参考实现 |
|------|------|---------|
| 表单 + 面板混排，整体滚动 | 保持默认 `scrollContent = true`；content 内**禁止**任何自带滚动的组件。可复用滚动组件必须参数化：加 `scrollable: Boolean = true` 形参，被嵌入时传 `false` | `HighlightStyleSheet(scrollable = false)` |
| 列表为主体 | `scrollContent = false` + 内层 `LazyColumn` 必须 `heightIn(max = 420.dp)` 有界自滚 | `HighlightPresetRuleDialog`、AppComposeDialogs 内三个 LazyColumn 弹框 |

**可复用组件自保护红线**：根级 `verticalScroll` 必须参数化（scrollable 形参）**或** `heightIn(max=…)` 前置于 `.verticalScroll()` 之前（heightIn 会把传入的 Infinity 钳制为有界，任意宿主均不崩）；禁止「裸 `verticalScroll` 直连根 modifier 且无任何高度钳制」。判定口诀：**两个垂直滚动组件之间必须有有界高度隔离**（heightIn / weight / fillMaxHeight 固定界）。

## 三、`ComposeSettingFragment` — 统一设置壳（配置页声明式）

**文件**：`app/src/main/java/io/legado/app/ui/config/compose/ComposeSettingFragment.kt`

- `abstract class ComposeSettingFragment : Fragment(), SharedPreferences.OnSharedPreferenceChangeListener`。
- 抽象成员：
  - `@get:StringRes protected abstract val titleRes: Int`（标题资源）
  - `protected open val applyActivityTitle: Boolean = true`
  - `protected open val autoOpenTargetItem: Boolean = true`
  - `protected open val drawPanelImage: Boolean = true`
- 子类实现 `buildPageSpec(): SettingSpecPage`，`onCreateView` 返回 `ComposeView`（`DisposeOnViewTreeLifecycleDestroyed`），`setContent { LegadoComposeTheme { SettingSpecScreen(...) } }`。
- 提供 `scrollTargetKey` 锚点滚动、`refreshTick` 刷新节拍、Pref change 监听（`prefs.registerOnSharedPreferenceChangeListener(this)`），实现声明式设置页自动渲染 + 自动刷新。
- **用途**：配置页（ThemeConfig / CoverConfig / WelcomeConfig / BackupConfig / OtherConfig 等 E3 项）升级为 ComposeSettingFragment 声明式组件库的落点。

## 四、`base/BaseDialogFragment` — 旧壳的淘汰边界

**文件**：`app/src/main/java/io/legado/app/base/BaseDialogFragment.kt`

- `abstract class BaseDialogFragment(@LayoutRes layoutID: Int, adaptationSoftKeyboard: Boolean = false) : DialogFragment(layoutID)`。
- 职责：XML 布局对话框约束下的通用能力（`onDismissListener`、e-ink 边框 `applyEInk`、重力调整时机编排、软键盘适配标志）。

### 迁移判定（2026-08-27 ui-style-unify-deep-fix 更新）
- **旧壳全面退役（✅ 实施收口 2026-08-28）**：`base/BaseDialogFragment`（36 子类 + BasePrefDialogFragment 2）**不再视为"合理存量"**——评审撤销上轮 G6 存量判定，**全量入 ComposeDialogFragment 迁移队列并已实施完成**：35 个迁移（P0 高可见：Servers/EffectiveReplaces/AddToBookshelf/SourcePicker/换源双弹框/SourceLogin/ReadAloudConfig 等，含 8 个超大弹框专项重写；名单外 IconDialog/KeyboardAssistsConfig 亦已迁）+ 复杂定制型登记保留（tasks 2.3.4）；**收口门禁 = `ui/` 下 BaseDialogFragment/BasePrefDialogFragment 子类 grep=0**（2026-08-28 实测通过）。迁移范式 = `ComposeDialogFragment` + `AppDialogFrame` + `collectAsState`/`DisposableEffect`(LiveData)。
- **系统 AlertDialog（`alert{}` DSL 71 文件 162 处 + 内联 9 处）**：高频确认/选择/输入点 → `ComposeConfirmDialog`/`ComposeSingleChoiceDialog`/`ComposeTextInputDialog` 收敛（AppComposeDialogs.kt 已具备）。✅ **可转型已收口（2026-08-28）**：累计转换约 90 处（含 selector 单选与 TextInput）；剩余 alert import = 25 文件（实测），均为 customView/进度/协程引用等复杂型登记保留。
- **M3 @Composable 弹框 5 个**（AppConfirmDialog/AppEditDialog/AppTextDialog/SingleChoiceDialog/ConfirmDialog）：D3 对齐 `AppDialogStyle`（补面板背景图/圆角倍率/透明度）。✅ Import 系 3 对话框已迁（2026-08-27）。
- **散点 13 个**（raw Dialog/BottomSheet/ComponentDialog/AlertDialog+ViewBinding）：D4 迁移或登记。✅ 已完成（2026-08-27：纯展示型补取色/承载类实况随主题/复杂型登记保留）。
- **新写弹框一律**：`AppComposeDialogs` 工厂 + `ComposeDialogFragment`；**禁止**新建基于 XML layout 的 `BaseDialogFragment` 子类、禁止新建 `alert{}` DSL。

## 五、层级小结

| 层级 | 用途 | 代表 |
|------|------|------|
| L1 底部弹层 | 富操作/表单/浮层 | `ui/widget/components/AppModalBottomSheet`、`AppMenuSheet` |
| L2 语义对话框族 | 确认/输入/选择/数字/文本 | `ui/widget/components/AppConfirmDialog/AppEditDialog/SingleChoiceDialog/AppTextDialog`、`ui/widget/compose/AppComposeDialogs` 族 |
| 窗口壳 | 对话框宿主/宽高档位/返回键/e-ink | `ComposeDialogFragment` + `AppDialogSize` |
| 旧壳（存量） | 尚未迁移的 XML 对话框 | `base/BaseDialogFragment` + `lib/dialogs/AlertBuilder` |