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

### 淘汰边界（migration 判定）
- **继续使用**：既有 `lib/dialogs/`（`AndroidDialogs.kt` 提供 `Context/Fragment.alert(...)`、`progressDialog`、`AlertBuilder` 等）与 `base/BaseDialogFragment` 用于**存量 View 对话框**，在未迁移前保持可运行，属合理存量。
- **淘汰原则**：新写对话框一律优先 Compose 对话框族（`AppComposeDialogs` + `ComposeDialogFragment`）或 `ui/widget/components/` 对话框族（`AppConfirmDialog`/`AppEditDialog`/`SingleChoiceDialog`/`AppTextDialog`），不再新建基于 `/XML layout` 的 `BaseDialogFragment` 子类。
- **迁移落点**：`archive-ui-migration-202608` E1 弹框类（7.11aa~an2）将旧 XML 弹框逐项收敛到 Compose 对话框族；`lib/dialogs` 与 `BaseDialogFragment` 仅在对应页面未迁移时保留，随页面迁移逐步退役（非一刀切删除，避免编译/运行回归）。

## 五、层级小结

| 层级 | 用途 | 代表 |
|------|------|------|
| L1 底部弹层 | 富操作/表单/浮层 | `ui/widget/components/AppModalBottomSheet`、`AppMenuSheet` |
| L2 语义对话框族 | 确认/输入/选择/数字/文本 | `ui/widget/components/AppConfirmDialog/AppEditDialog/SingleChoiceDialog/AppTextDialog`、`ui/widget/compose/AppComposeDialogs` 族 |
| 窗口壳 | 对话框宿主/宽高档位/返回键/e-ink | `ComposeDialogFragment` + `AppDialogSize` |
| 旧壳（存量） | 尚未迁移的 XML 对话框 | `base/BaseDialogFragment` + `lib/dialogs/AlertBuilder` |