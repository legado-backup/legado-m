# tasks.md — UI 主题纳管与弹框交互优化

> 状态：🔄 设计中（红队 R1-R5 终审 GO-WITH-NOTES + 用户裁决"无二期"全量折入本期）
> 任务顺序强制，不可跳过中间任务；每项完成后标注完成级别（⚠️ 代码完成 / ⚠️ 功能验证 / ✅ 场景验证）
> 红队轮次：R1 执行模拟 / R2 稳定健壮 / R3 通用遗漏（并行）→ 整改 → R4 一致性 → 整改 → R5 终审 GO-WITH-NOTES → 用户裁决无二期（§2/§3/§4/§8 扩展）→ 新增内容红队 N1 事实核验 / N2 稳定回归（并行）→ 整改 → N3 一致性终审 GO-WITH-NOTES

## 1. 准备工作

- [ ] 1.1 阅读取色基线规范（docs/project-flow/ui-standards/architecture.md 取色唯一基线章节）并核对 AppDialogStyle 现有字段与 toMiuixPalette 桥
- [ ] 1.2 Read 既有 `LegadoMiuixSwitch`（LegadoMiuixComponents.kt:281-330，palette 契约+双渲染路径）与 AppDialogSwitchRow 消费先例；确认 stroke/compact 参数插入点（追加参数表末尾，21 处既有调用点均为命名传参安全）
- [ ] 1.3 Read AppComposeDialogs.kt AppDialogFrame 完整实现，确认 titleTrailing 槽插入点（标题行改 Row+weight 保留 Ellipsis）与调用点清单（82 处（含定义行）/74 文件）
- [ ] 1.4 TopBarConfig 新增 `Config.hasCustomBackground()`：`resolveBackgroundColor(this) != defaultBackgroundColor(isNightMode)`（**必须走 resolve 兜底**——自定义包 JSON 的 backgroundColor 可为 null；**禁止裸 `backgroundColor != null` 或裸值比较**——defaultConfig 恒填默认色恒真陷阱）
- [ ] 1.5 Grep 盘点管理族全部宿主**封闭清单**（AppManagementScaffold 5 页 + 非 Scaffold 管理页逐页列入/豁免+理由 + `recreateOnThemeChange` 真值列，裁决 ConfigActivity 是否纳入并书面记录），作为 7.4/7.5 验收基准；确认换源弹框（ChangeBookSourceDialog L414-477）三点迁移细节

## 2. P1 开关组件主题化（复用既有组件 + 视觉统一 + 全域清零）

- [ ] 2.1 既有 LegadoMiuixSwitch 新增可选参数：`stroke: Color? = null`（经 switchModifier 追加 `border(1.dp, if(checked) Transparent else stroke, RoundedCornerShape(50))`，仅未选中态，双渲染路径共用——miuix colors 无 stroke 槽不能走 colors 参数）+ `compact: Boolean = false`（38x22dp 轨道/16dp thumb 复现 mini 尺寸且关 shadow，规避 E-Ink 灰圈）；M3 fallback 分支同步；选中 thumb 用 palette.resolvedOnAccent 自适应黑白（**禁止外挂 toggleable**——内层 Switch 原生语义防双触发；默认值零影响）
- [ ] 2.2 SourceFolderConfigDialog 升序排列行换用既有 LegadoMiuixSwitch + `style.toMiuixPalette()` 桥接（替换裸 M3 Switch；先例 AppDialogSwitchRow；**禁止新建同名组件**）
- [ ] 2.3 BookshelfConfigDialog 私有 BookshelfMiniSwitch 迁移至公共组件（传 style.stroke + compact=true），删除私有实现（外层 Row clickable 保留 + 组件 onCheckedChange，双响应先例 AppDialogSwitchRow 在产）
- [ ] 2.4 验证：编译通过 + 真机 S1（订阅布局弹框开关随主题变色）+ 书架布局弹框开关回归（尺寸 38x22/无阴影/描边/双渲染路径）

## 3. P2 登录弹框按钮收纳 + 换源弹框迁移

- [ ] 3.1 AppDialogFrame 增加 `titleTrailing` 可选槽（默认 null 零影响；标题行改 `Row { Text(weight(1f), maxLines=2, ellipsis) + trailing }`）
- [ ] 3.2 SourceLoginDialog：显示登录头/删除登录头/日志 3 按钮迁移至三点菜单（MenuAction 数据驱动，图标 Visibility/Delete/Article 类，零新资源），actions 仅留"确定"
- [ ] 3.3 ChangeBookSourceDialog 内容区三点菜单迁移至 titleTrailing 槽（搜索行腾出空间，菜单 6 项内容不变）
- [ ] 3.4 验证：编译通过 + 模拟器打开登录弹框确认免滑动、三点菜单功能与原按钮等价、长标题不挤出 trailing 槽 + 换源弹框三点菜单功能等价（低屏高设备菜单 6 项完整可见）+ 全 App 抽验 3 个未改动弹框确认 titleTrailing 默认 null 零影响（Level 2）

## 4. P3 主题编辑器保存感知 + 取色纳管

- [ ] 4.1 ThemeEditorViewModel 增加 dirty 判定：`toDirtyComparable()` 投影（仅 9 色槽+name+wallpaperPath/Blur+4 滑杆，剔除 isNight/applySuccess/suggestions/extracting/wallpaperBitmap）+ `initialSnapshots: Map<Boolean, DirtySnapshot>` 按日夜模式快照（与 drafts 同构，首次进入模式时记录）+ apply 成功复位 applySuccess 并重建当前模式快照
- [ ] 4.2 ThemeEditorScreen 自绘按钮行迁移：按钮在 ThemeEditorDialogFragment 的 actions lambda 内实现（取消/保存，可访问 viewModel/dirty），删除自绘行
- [ ] 4.3 关闭通道收敛：ThemeEditorDialogFragment `isCancelable = false`（禁点外部直接关闭）→ `ComposeDialogFragment.onBackIntercepted()` 开放钩子（默认 false，handleDialogBack 接入 `if (!onBackIntercepted() && isCancelable)`，全调用点零影响）→ 编辑器覆写（dirty 时弹"放弃修改？"确认）→ 取消按钮链路同步走 dirty 检查
- [ ] 4.4 取色纳管分层：Grep `MaterialTheme\.colorScheme|Color\(0x|Color\.(Red|White|Black|Gray|Yellow)` 于 `ui/config/theme/compose/`（38 行命中）；**chrome 区**（按钮行/DayNightTabs/TabButton/SectionCard）与 **SimpleColorPickerDialog** 逐个替换 AppDialogStyle；**预览画布豁免**并在代码注释登记
- [ ] 4.5 验证：编译通过 + 真机场景 S3（改色→取消→拦截→确认放弃不落盘；返回键同拦截；点弹框外部不关闭；保存→即时生效且二次进入不误报 dirty）+ 取色器颜色选择功能正常

## 5. P4 字号滑条与高度自适应

- [ ] 5.1 字号滑条 fallback `12f`→`10f`（ThemeEditorScreen.kt:406），阴影滑条同步修（:392）；确认 valueText"跟随默认"文案行为（错位接受项）
- [ ] 5.2 EditorMaxContentHeight 固定 460dp 改为 `screenHeightDp*0.7f` 且 `coerceAtMost(520.dp)`（与外层上限取 min，内层不再先于外层裁切）
- [ ] 5.3 真机排查文字截断清单（含系统大字号）：SettingSpecScreen(60dp/72dp minHeight)、ThemeEditorScreen 固定高度区、NavigationBarManageActivity:1239(460dp)、AiProviderEditScreen:487(360dp)、ThemeManageActivity:2364-2631 预览卡、AppearanceKitActivity:634/651——逐项过，发现一处修一处
- [ ] 5.4 验证：编译通过 + 真机场景 S4（字号滑块 25% 偏左 + 阴影滑块同步确认偏左）+ 底部按钮行完整可见

## 6. P5 沉浸顶栏开关修复

- [ ] 6.1 AppManagementScaffold 顶栏决策链重写（L141-150）：三级基色（hasCustomBackground → immersiveManageBar → primaryColor）→ `contrastOn(基色)` 内容色（先于 alpha）→ 统一调制层**本期仅含 REGULAR 壁纸 wallpaperAlpha 调制（与现状行为等价重写）**；wallpaperFile/cornerRadius 的 isRegular 门控不变（fraction 合成属 P6，在 7.3 追加——依赖顺序：manageBgAlpha 属性 7.1 才创建）
- [ ] 6.2 ThemeConfigFragment 沉浸顶栏开关 summary 文案更新
- [ ] 6.3 验证：编译通过 + 真机场景 S5（5 个管理页：REGULAR 与非 REGULAR 用户群开关均产生视觉差异；TopBarConfig 自定义背景色配置不被破坏；REGULAR+壁纸用户壁纸仍可见）

## 7. P6 管理族透明度设置（全宿主）

- [ ] 7.1 PreferKey 新增 `manageBgAlpha`（单 key 不分日夜，注释声明决策）；AppConfig 新增 fraction 读取（默认 100，**get/set 双向 coerceIn(0,100)**，E-Ink 模式强制 1f）
- [ ] 7.2 ThemeConfigFragment 复用 `SettingSliderSpec` 新增"管理页背景透明度"滑条（0~100%；拖动中 draft+refreshSettings 实时回显防弹回；`onValueChangeFinished` 提交 `updateIntSetting` + `onSettingPreferenceChanged(PreferKey.manageBgAlpha)` 触发 RECREATE）
- [ ] 7.3 AppManagementScaffold 消费：在 6.1 调制层基础上**追加** fraction 乘法合成（`alpha = wallpaperFactor * fraction`，**禁止两次 copy 顺序赋值**——copy 为绝对赋值会覆盖壁纸调制，见 design P5 修正版公式）+ 根 Column 显式 `background(backgroundColor.copy(alpha=fraction))` 绘制层（透出层=windowBackground）+ `remember(themeVersion)` 单次读取；容忍同帧多次 recreate
- [ ] 7.4 管理族非 Scaffold 宿主接入（红队 N1-P1-3/N2-P1-4 整改后契约）：BaseActivity 新增 `protected open fun manageBackgroundAlphaEnabled(): Boolean = false`，`applyBackgroundTint` 内开启时改用 `backgroundColor.copy(alpha=fraction)`（统一读 AppConfig.manageBgAlphaFraction，E-Ink 强制 1f）——**单点覆盖 onCreate/RECREATE 豁免分支/onResume 三条刷新链路**（禁止逐页 onCreate 一次性接入，豁免页宿主会被 L116 无 alpha 基色覆写丢失）；按 1.5 封闭清单逐一 override true
- [ ] 7.5 验证：编译通过 + 真机场景 S6（拖动松手提交后**1.5 封闭清单内全部管理页及子页面**生效、可观测差异、可读性正常、弹框面板走既有 dialogAlpha 不受叠乘影响）+ 脏值防御（手工写 pref=150/-5 后全部管理页正常渲染）+ E-Ink 回归（无视觉变化）+ 豁免页宿主（recreateOnThemeChange=false）日夜切换后 alpha 不丢失 + 若 Scaffold 页无可观测差异则同任务内追加内容卡片级消费后复验（不遗留）

## 8. 取色离群全域清零（无二期，本期修复）

- [ ] 8.1 SingleChoiceDialog 裸 RadioButton + colorScheme 直读取色修复（L78/L87-100 → AppDialogStyle/palette 主题化取色；M3 AlertDialog 容器色为默认派生属登记豁免）
- [ ] 8.2 ServersDialog 裸 RadioButton 取色修复（L216；ServersRow L202-208 无 style 作用域，加参传入或行内调 rememberAppDialogStyle()）
- [ ] 8.3 SettingsSelectableRow 无参 CheckboxDefaults.colors() 取色修复（L94，取色来源用既有 rememberAppSettingPalette()；语义沿用 M3 内建不新增 stateDescription）
- [ ] 8.4 屏幕域裸 Switch 8 处清零（palette 映射替换）：AutoTaskEditScreen:127/144、AiWorldBookManageScreen:585/662/1015、SettingsSelectableRow:123、SettingsToggleRow:64（colorScheme 直读 SwitchDefaults）、RegexTestScreen:338
- [ ] 8.5 验证：编译通过 + Grep `\bSwitch\(` 全项目排除两处合法点（LegadoMiuixComponents.kt:312 fallback、ThemeEditorScreen.kt:737 预览画布）= 0 残留 + 真机抽验宿主（每组件 ≥2 个代表宿主，必含 VideoSettingsPanelContent、AiConfigFragment、AutoTask/TxtTocRule/DictRule 管理页）确认取色随主题 + 选中/未选中态对比度真机对照 + 功能（选择/勾选/开关）行为不变

## 9. 综合验证与收尾

- [ ] 9.1 覆盖安装回归：S7 全场景；AppDialogFrame 抽验清单（titleTrailing/actions 两形态）= 订阅布局/书架布局/换源/登录/主题编辑器/阅读更多设置/高亮编辑 7 类代表弹框（含 LegadoMiuixSwitch 双渲染路径——订阅布局弹框为 S1 直接视验点，不可省）+ 新增内容宿主四类（SingleChoiceDialog 族/ServersDialog/SettingsSelectableRow 三管理页/1.5 清单 View 管理族代表页）
- [ ] 9.2 静态检查：Grep `\bSwitch\(` 排除两处合法点 = 0 残留 / `MaterialTheme.colorScheme` 于 ThemeEditorScreen chrome 区+SimpleColorPickerDialog = 0 残留 / dialog 域无新增 colorScheme 直读离群 / 无临时日志残留（统一 tag 清零）
- [ ] 9.3 基于 git diff 更新 updateLog.md（编译前完成，追加在 `## cronet版本:` 之后）
- [ ] 9.4 文档同步：docs/project-flow/ui-standards/architecture.md（开关组件纳管口径+透明度消费链登记）、quick-reference.md（如结构有变）、docs/INDEX.md 状态流转
- [ ] 9.5 打测试包 `build-legado.bat` 并清理构建 daemon（stop-daemons.bat）

## 10. 红队审查轮次账本

- [x] R1 执行模拟对抗（4P0+8P1+6P2）→ 已整改落盘
- [x] R2 稳定健壮对抗（2P0+4P1+8P2）→ 已整改落盘
- [x] R3 通用遗漏对抗（1P0+4P1+3P2）→ 已整改落盘
- [x] R4 一致性矛盾对抗（1P0+3P1+5P2）→ 已整改落盘
- [x] R5 终审 GO-WITH-NOTES（8/8 抽查吻合、悬空项 0、3 注意点已顺手清零）
- [x] 用户裁决"无二期"（2026-09-03）→ 二期登记项全部折入本期（§2 视觉统一/§3 换源迁移/§4 取色器纳管/§7 全宿主消费/§8 Checkbox-RadioButton 清零），tasks 扩展后无遗留登记项
- [x] N1 新增内容执行模拟+事实核验（2P0+4P1+5P2）→ 已整改落盘
- [x] N2 新增内容稳定回归对抗（4P1+5P2）→ 已整改落盘
- [x] N3 新增内容一致性终审（GO-WITH-NOTES：5/5 整改落盘复核、7/7 源码抽查、3 注意点已清零、spec 补 R1.3/R2.4 闭合映射）

## AOAdapt 日志

（实施中遇到问题在此记录：Action → Observation → Adapt）
