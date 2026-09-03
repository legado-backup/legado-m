# spec.md — UI 主题纳管与弹框交互优化

> 状态：🔄 设计中

## Intent

用户反馈 6 个 UI 问题，本质是**部分 UI 点位脱离主题取色基线**（P1/P3/P5/P6）与**弹框交互不符合预期**（P2/P3/P4）。本规格意图：

1. 让所有弹框/设置页组件严格遵循主题取色唯一基线（ThemeStore + AppDialogStyle），消灭离群取色点；
2. 优化登录弹框、主题编辑器的按钮布局与保存感知，对齐 archive 范式（三点菜单收纳）但保持自有风格；
3. 修复默认字号滑块位置与文字截断；
4. 修复沉浸顶栏开关失效；
5. 扩展主题体系：新增"管理页背景/组件透明度"设置，让管理页整体样式可调。

## Scope

### In Scope

- P1：`SourceFolderConfigDialog` 升序排列 Switch 主题化（换用既有 LegadoMiuixSwitch）；既有组件加可选 `stroke` 参数（默认 null 零影响）并迁移书架弹框 `BookshelfMiniSwitch`，**本期完成两弹框开关视觉统一**
- P2：`SourceLoginDialog` 底部按钮收纳（确定固定右下 + 3 按钮进三点菜单）；`AppDialogFrame` 增加标题栏 trailing 槽；**换源弹框（ChangeBookSourceDialog）三点菜单一并迁移至 titleTrailing 槽**
- P3：`ThemeEditorScreen` 取消/保存标准化 + 未保存拦截 + 取色纳管（chrome 区 + **SimpleColorPickerDialog 本期纳管**，预览画布豁免）
- P4：字号滑条 fallback 改 10f（偏左）+ 高度策略改自适应 + 截断点排查
- P5：`AppManagementScaffold` 沉浸顶栏开关语义修复
- P6：新增管理页透明度配置（PreferKey + ThemeConfig 设置项 + 消费链：Scaffold 5 页 + **非 Scaffold 管理族宿主根背景本期全部接入**）
- P6 扩展：**弹框域 Checkbox/RadioButton 三处离群（SingleChoiceDialog/ServersDialog/SettingsSelectableRow）本期取色修复**

### Out of Scope

- 不改动视频播放器、书源解析、数据库 schema
- 不重构 ThemeStore/主题引擎整体架构（只扩展纳管点位）
- 不改动 WebView 登录路径（仅 Compose 登录弹框）
- 不改动 `AppDialogFrame` 面板取色链结构（面板透明度已由既有 `AppConfig.dialogAlpha` 机制承担，本期复用不重复新增，防双 alpha 叠乘；本期对其唯一改动 = titleTrailing 槽扩展）
- 不引入新依赖

## Approach

### Selected Approach

以**现有 AppDialogStyle 取色基线为唯一权威源**做点位补齐：

1. **P1**：订阅布局弹框升序开关换用**既有** `LegadoMiuixSwitch`（`LegadoMiuixComponents.kt:281`，palette 契约）+ `style.toMiuixPalette()` 桥接；既有组件**加可选 `stroke: Color? = null` 参数**（默认 null 全既有调用点零感知）；书架弹框 `BookshelfMiniSwitch` 迁移至公共组件（传 `style.stroke`），**本期完成两弹框开关视觉统一**（新建同名组件会同包撞名，直接改函数体会外溢全 App 开关视觉——红队整改）。
2. **P2**：`AppDialogFrame` 增加可选 `titleTrailing` 槽（默认 null，向后兼容），登录弹框在槽内放 `MoreVert IconButton + AppDropdownMenu`（复用换源弹框范式），收纳"显示登录头/删除登录头/日志"3 个低频按钮，"确定"保留 actions 槽固定右下。
3. **P3**：主题编辑器底部自绘按钮行迁移到 `AppDialogFrame` 标准 actions 槽（取消/保存双按钮，按钮在 DialogFragment actions lambda 内实现）；ViewModel 增加 dirty 状态（**按日夜模式各自快照 + 编辑字段投影 `toDirtyComparable()` 剔除非编辑字段**——state 含 isNight/applySuccess/suggestions/extracting/wallpaperBitmap 非编辑字段且日夜双草稿，单一快照会误报）；编辑器 `isCancelable=false` 收敛关闭通道（返回键/取消按钮/保存成功三路径全走 dirty 检查，点弹框外部直接关闭被禁用）；`ComposeDialogFragment` 新增 `onBackIntercepted()` 默认 false 的开放钩子供返回键拦截；取色纳管分层处置（chrome 区替换 AppDialogStyle / **SimpleColorPickerDialog 本期纳管** / 预览画布豁免——文件头门禁注释明确的预览专用临时 scheme）。
4. **P4**：字号滑条与阴影滑条 fallback `12f` → `10f`（10=1.0x 标准倍率，滑块偏左落在合法离散点）；编辑器内容高度内层上限改为屏幕高度比例并与外层 520dp 取 min（内层不再先于外层裁切）；对截断元素逐个真机排查修复。
5. **P5**：`AppManagementScaffold` 顶栏背景决策链整合沉浸开关，三级化：TopBarConfig 显式自定义背景色（`resolveBackgroundColor` 兜底后值比较，自定义包 JSON 可为 null，禁止裸 `!= null` 或裸值比较）→ `immersiveManageBar` 开关（沉浸=融入背景）→ 默认主色；内容色 `contrastOn` 基于不透明基色决策（先于 alpha）；既有 REGULAR 壁纸 alpha 调制维度保留（与透明度在同一调制点应用，防"仅设壁纸"用户壁纸被遮死）；wallpaperFile/cornerRadius 的 isRegular 门控不变；保证 REGULAR 与非 REGULAR 全用户群开关均有效。
6. **P6**：新增 `PreferKey.manageBgAlpha`（0~100 整数，默认 100 不透明；**读取与写入双向 `coerceIn(0,100)`**——`Color.copy(alpha)` 超界抛异常，脏 pref 会使管理页全崩；**E-Ink 模式强制 fraction=1f** 白底黑字契约；单 key 不分日夜显式决策；`remember(themeVersion)` 单次读取防重组直读 prefs），ThemeConfigFragment 主题设置页复用既有 `SettingSliderSpec` 新增滑条（拖动中 draft+refreshSettings 实时回显，`onValueChangeFinished` 提交写入+RECREATE，拖动中不重建）；**消费链本期覆盖管理族全部宿主**：`AppManagementScaffold` 根 Column 显式背景绘制层 + 顶栏终色（透出层=windowBackground，alpha 统一在调制点应用一次）+ 非 Scaffold 管理族宿主（ThemeManageActivity/TopBarManageActivity 等）根背景接入；弹框面板透明度**复用既有 `AppConfig.dialogAlpha` 机制**（已存在，本期不重复新增，防双 alpha 叠乘）；`AppDialogFrame` 取色链结构不动。参考 archive 的透明度处理思路，但配置项命名、滑条档位、默认值按本项目风格自定。
7. **P6 扩展（无二期，全部本期）**：弹框域 Checkbox/RadioButton 三处离群取色修复（SingleChoiceDialog:78/ServersDialog:216/SettingsSelectableRow:94 → AppDialogStyle/palette 映射）；换源弹框三点菜单迁移至 titleTrailing 槽。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| P1 用 `SwitchDefaults.colors(...)` 映射主题色 | 可行但仍是 M3 Switch 直读 colorScheme 模式，且无法与项目主题化开关统一；既有 LegadoMiuixSwitch 已真机验证，复用零新增 |
| P1 新建独立 LegadoMiuixSwitch 组件文件 | 同包与既有组件撞名编译失败；改既有函数体外溢全 App 弹框开关视觉（红队 R1-P0-1） |
| P2 将 4 按钮全部收进三点菜单 | "确定"是主操作，收进菜单增加登录操作路径成本；保留固定右下符合弹框交互惯例 |
| P3 仅给自绘按钮加高亮样式 | 治标不治本：未保存拦截缺失问题仍在；且自绘按钮脱离 AppDialogFrame 标准骨架，属未纳管点位本身 |
| P3 单一 initialState 快照判定 dirty | state 含非编辑字段（isNight/applySuccess/suggestions/extracting）+日夜双草稿结构，零编辑会误报、保存后仍判脏（红队 R1-P0-3） |
| P4 字号滑条增加"跟随系统"档位 | 语义更准但改动滑条交互结构（steps/分段），超出本轮"滑块位置偏左"诉求；fallback 10f 最小改动达成目标 |
| P5 修改 App.kt 首装预设 | 只影响新装用户，存量用户开关仍死；必须在消费点修复才根治 |
| P5 用 `backgroundColor != null` 判定自定义 | 数据层 defaultConfig 恒填默认色（恒真陷阱）；且自定义包 JSON 可为 null（误判），必须 resolveBackgroundColor 兜底后值比较（红队 R1-P1-5） |
| P6 直接给所有页面全局加透明度 | 影响面不可控（书架/阅读页未在诉求内）；先收敛到管理页 Scaffold，验证效果后再评估扩展 |
| P6 让 AppDialogFrame 面板消费管理页透明度 | 全 App 82 调用点通用骨架，面板已消费全局 dialogAlpha，会误伤全部弹框且双 alpha 叠乘（审查 P0-1） |

### Drawbacks

- 既有 LegadoMiuixSwitch 双渲染路径（miuix/M3 fallback），开关视觉随设备存在固有差异，回归需双路径覆盖
- AppDialogFrame 加槽位是对公共骨架的扩展，需保证所有既有调用点零感知（默认参数向后兼容 + 6 类弹框抽验）
- 透明度设置涉及覆盖安装兼容（pref 新 key 有默认值 + coerceIn 防御，无迁移风险），但低透明度下对比度可能下降，属用户自选风格，默认 100 不透明保证基线体验；windowBackground 同色系时低透明度视觉差异可能微弱（S6 以可观测差异验收）
- 字号 fallback 改 10f 后，"跟随系统"的 null 语义在 UI 上不再直接可见（valueText 仍显示"跟随默认"文案，滑块位置与文案轻微错位），接受此简化（实际行为不变）

### Prior Art

- 项目内既有 `LegadoMiuixSwitch`（LegadoMiuixComponents.kt:281，palette 契约 + miuix/M3 双渲染路径）与 `AppDialogSwitchRow` 消费先例：P1 的直接复用对象
- 项目内 `BookshelfMiniSwitch`（BookshelfConfigDialog.kt:1002-1042）：自绘主题化开关参照（取色已合规，保持不动）
- 项目内 `ChangeBookSourceDialog.kt:414-476`：弹框内三点菜单 + AppDropdownMenu 收纳按钮的标准范式，P2 参考
- `TopBarConfig.withOpacity` + wallpaperAlpha：已有透明度应用机制，P6 消费链参考
- `AppConfig.dialogAlpha` coerceIn 双向防御范式 + E-Ink 强制不透明契约三先例：P6 防御与豁免参考
- archive（ui-redesign-m3 基线）：三点菜单收纳 + 弹框骨架规范，整体风格参考

## Requirements

### R1 主题取色纳管

1. **Switch 类全域清零**（用户裁决无二期）：全项目裸 `Switch(`（覆盖全限定名+短名 import）存量 11 处 = 9 处待修（弹框域 SourceFolderConfigDialog + 屏幕域 AutoTaskEditScreen/AiWorldBookManageScreen/SettingsSelectableRow/SettingsToggleRow/RegexTestScreen 共 8 处）+ 2 处合法豁免（组件内部 fallback/预览画布）——9 处全部本期修复——弹框域换用既有 LegadoMiuixSwitch（订阅布局 + 书架迁移统一视觉），屏幕域 palette 映射替换
2. 主题编辑器 chrome 区及 SimpleColorPickerDialog 所有组件颜色必须来自主题取色基线，Grep 排查口径：`MaterialTheme\.colorScheme|Color\(0x|Color\.(Red|White|Black|Gray|Yellow)` 于 `ui/config/theme/compose/`（colorScheme 直读为主要违规形态，约 38 行；**预览画布豁免**），命中区逐个替换为 AppDialogStyle 字段
3. 弹框域 Checkbox/RadioButton 三处离群（SingleChoiceDialog/ServersDialog/SettingsSelectableRow）本期取色修复，修复后 dialog 域无 colorScheme 直读离群点（SingleChoiceDialog 的 M3 AlertDialog 容器色为默认派生属登记豁免）

### R2 登录弹框交互

1. "确定"按钮固定于弹框右下（actions 槽），不参与横向滚动
2. "显示登录头/删除登录头/日志"3 按钮收进标题栏右侧三点菜单，菜单项带图标与标题
3. 弹框打开后默认态不得出现横向滚动条
4. 换源弹框（ChangeBookSourceDialog）内容区三点菜单同步迁移至 titleTrailing 槽，菜单项内容不变（功能等价）

### R3 主题编辑器保存感知

1. 底部提供标准"取消/保存"双按钮（AppDialogFrame actions 槽，DialogFragment 内实现），保存=应用并关闭
2. 存在未保存修改时（dirty，按日夜模式各自快照 + 编辑字段投影判定），返回键/取消按钮必须弹确认拦截；编辑器 `isCancelable=false`，点弹框外部不允许直接关闭（三退出通道全收敛）
3. 保存成功后关闭弹框并即时生效（applySuccess 复位防重复触发）

### R4 字号滑条与截断

1. 字号滑条 fallback 显示值为 10（滑块偏左），阴影滑条同步修复
2. 编辑器内容区高度自适应窗口，底部按钮行任何字号/屏幕下完整可见
3. 主题设置相关页面文字不得出现"显示一半"截断（真机逐项验证）

### R5 沉浸顶栏开关

1. `immersiveManageBar` 开关选中/不选中必须产生可感知的视觉差异（沉浸 vs 实色顶栏），REGULAR 与非 REGULAR 用户群均有效
2. 开关行为与 TopBarConfig 自定义配置兼容（显式自定义背景色优先），不破坏现有顶栏样式；REGULAR 壁纸 alpha 调制维度保留（"仅设壁纸"用户壁纸仍可见）

### R6 管理页透明度设置

1. 主题设置页新增"管理页背景透明度"滑条（0~100%，默认 100%），拖动实时回显（draft+refreshSettings），`onValueChangeFinished` 提交写入并触发重建
2. **管理族全部宿主**消费该透明度：`AppManagementScaffold`（顶栏终色 + 根背景绘制层，透出层为 windowBackground）+ 非 Scaffold 管理族宿主经 **BaseActivity 统一钩子**（`manageBackgroundAlphaEnabled()` + applyBackgroundTint 消费 fraction，单点覆盖 onCreate/RECREATE/onResume 三条刷新链路，豁免页宿主不丢 alpha）；弹框面板透明度复用既有 `AppConfig.dialogAlpha` 机制（UI 入口已存在，不新增，防叠乘）
3. 读取与写入双向 `coerceIn(0,100)`；E-Ink 模式强制不透明（fraction=1f）；覆盖安装后新 key 有默认值，脏值/无值均无崩溃风险

## Scenarios

### S1: 升序开关随主题变色
**Given** 用户在主题设置中选择了绿色主题色
**When** 打开订阅页布局设置弹框
**Then** "升序排列"开关选中态底色为绿色 accent，未选中态为 fieldSurface，与弹框内滑条/chip 颜色同源

### S2: 登录弹框免滑动
**Given** 用户从书籍详情页右上角三点菜单进入登录弹框
**When** 弹框展开
**Then** 底部仅"确定"按钮固定右下；标题栏右侧三点菜单展开可见"显示登录头/删除登录头/日志"三项，点击行为与原按钮一致

### S3: 未保存拦截
**Given** 用户在主题编辑器修改了主题色但未点保存
**When** 点"取消"或系统返回
**Then** 弹出"放弃修改？"确认框；确认后关闭且不落盘，取消后留在编辑器

### S4: 字号滑块偏左
**Given** 用户未自定义字号（null 语义）
**When** 打开主题编辑器
**Then** 字号滑条滑块位于 25% 偏左位置（10 档），数值区文案仍显示"跟随默认"（错位接受项）

### S5: 沉浸开关生效
**Given** 用户在管理页（如书源管理）
**When** 在主题设置中切换"沉浸顶栏"开关并返回
**Then** 选中时顶栏沉浸融入背景；不选中时顶栏实色，视觉差异明显；REGULAR+壁纸用户壁纸仍可见

### S6: 透明度调节
**Given** 用户在主题设置中拖动"管理页背景透明度"滑条至 60%（松手提交）
**When** 进入任意管理页及子页面（含非 Scaffold 管理族宿主）
**Then** 页面背景/顶栏呈 60% 不透明度，透出窗口背景层；文字与图标保持不透明可读；弹框面板走既有 dialogAlpha 机制不受本配置叠乘影响

### S7: 回归保护
**Given** 覆盖安装新包
**When** 打开书架布局弹框、换源弹框、登录弹框、主题编辑器
**Then** 全部正常打开无崩溃，既有设置项行为不变
