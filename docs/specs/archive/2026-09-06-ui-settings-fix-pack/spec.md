# Spec: ui-settings-fix-pack（UI 设置体验修复包）

> 状态：设计中 ｜ 路径：扩展路径（三需求合并，分三任务组）
> 创建：2026-09-06 ｜ 依赖源码锚点均已核验（2026-09-06 工作区）

## Intent

修复三项 UI 设置体验问题：
1. **主界面底栏搜索框显隐**：隐藏开关已存在但入口过深（仅 底栏管理→编辑→搜索，且仅 floating 模式显示），用户无法发现。补齐显性入口。
2. **字号放大后组件截断**：全局字号缩放（fontScale，范围 8~16 即 0.8x~1.6x）放大后，大量固定高度组件文字显示一半。排查并修复适配缺陷。
3. **取色器回退**：3c8aa5c7b（archive-ui 迁移）误删优化版取色链路（SettingsColorRow + ColorPickerSheet 调用方），主题编辑页回退为简版 SimpleColorPickerDialog。恢复优化版接入。

## Scope

### In Scope
- 主界面底栏搜索框（`searchButtonContainer`，floating 模式悬浮搜索按钮）显隐入口扩展
- fontScale 放大（≥1.4x）场景下固定高度组件的文字截断排查与修复
- `ColorPickerSheet`（优化版取色器，已存在零调用）接入 `ThemeEditorScreen`，替换私有 `SimpleColorPickerDialog`
- 相关 strings 资源补充

### Out of Scope
- 阅读界面底栏（ReadMenu）按钮显隐（底栏按钮管理已支持删除搜索按钮，功能无缺陷）
- 阅读正文字号体系（textSize 默认 20，独立机制，无缺陷）
- 字号缩放范围调整（当前 8~16 已符合用户预期）
- sidebar 模式搜索入口改造

## Approach

### Selected Approach

**F1 搜索框显隐**：保留现有 `floatingBottomBarHideSearch` 配置与生效链不动，扩展显性入口：
- 底栏管理编辑对话框：既有"搜索：显示/禁用"开关保留于 floating 分支不动
- 我的设置页（OtherConfig 界面设置区）：新增"主界面底栏搜索框"快捷开关条目；当激活自定义底栏套装（非默认套装）时隐藏该条目（套装配置为权威源，避免静默回滚），summary 标注"悬浮底栏模式下生效"
理由：零迁移成本、复用既有生效链（`MainActivity.isFloatingSearchHidden()`），改动集中在 UI 入口层。

**F2 字号截断修复**：采用"实测定位 + 逐点修复"策略：
1. 模拟器设 fontScale=16（1.6x），走查核心页面（书架/发现/订阅/我的/阅读菜单/主题设置/常用弹窗），记录文字截断点清单
2. 静态扫描辅助定位（固定 `height(xxx.dp)` + 文本子组件的 Compose 模式）
3. 逐点修复：固定高度改 `heightIn(min=)` 或自适应高度；必要时行高/内边距微调
4. 回归 1.0x 确认无样式劣化
理由：截断点是经验性缺陷，实测清单是唯一可靠的修复依据，避免盲目全局重构。

**F3 取色器恢复**：将 `ThemeEditorScreen` 私有 `SimpleColorPickerDialog`（L813）替换为 `ColorPickerSheet`：
- `ColorPickerSheet` API（title: String / initialColor: Int / onConfirm: (Int) / onDismiss）与现调用点适配成本低
- 扩展 `ColorPickerSheet` 增加可选"跟随默认"支持（`allowFollowDefault: Boolean = false` + `onFollowDefault: () -> Unit`），对齐现有 `allowFollowDefault` 语义（可选槽位清除颜色恢复默认）
- 行组件不恢复 `SettingsColorRow`：`ThemeEditorScreen` 的 `ColorPaletteSection` 行已含色块预览（L258），恢复会造成重复组件
理由：最小改动恢复优化体验，孤儿代码 `ColorPickerSheet` 直接复活，不引入新组件。

### Alternatives Considered

| 备选方案 | 否决理由 |
|---------|---------|
| F1: 恢复 SettingsColorRow 并重构 ColorPaletteSection 行组件 | 行组件功能重复（现组件已有色块预览），仅弹窗体验存在差距；恢复整链改动面大且引入两套行组件维护负担 |
| F1: standard 模式下也显示悬浮搜索按钮并支持隐藏 | standard 模式搜索入口被布局设计移除是有意为之（底栏导航 6 项 + 无悬浮层），强行恢复破坏 standard 模式简洁语义 |
| F2: 全局把固定 height 批量改为 heightIn | 盲目批量改动会破坏刻意固定高度的非文本组件（图标、分隔条、色块），必须逐点确认文本容器 |
| F2: 限制 fontScale 上限至 1.3x 规避截断 | 与用户已确认的 8~16 范围冲突，治标不治本 |
| F3: 在 SimpleColorPickerDialog 上迭代加色板/滑块 | 简版缺预置色板 + HSL 滑块 + 活预览，迭代等于重写 ColorPickerSheet，不如直接复用现成优化版 |

### Drawbacks

| 缺陷/风险 | 接受理由 | 兜底预案 |
|-----------|---------|---------|
| F1: standard 模式下"搜索"开关无生效点（布局本身不显示搜索按钮） | 开关仅 floating 模式可隐藏搜索，standard 分支展示开关会造成困惑 → **调整：standard 分支不显示开关，仅保留 floating 分支现有开关；显性化靠"我的设置页快捷开关"** | 快捷开关 summary 文案标注"悬浮底栏模式生效" |
| F2: 截断点清单依赖实测，可能遗漏低频页面 | 核心高频页面全覆盖（≥8 页面），低频页面随反馈修复 | 用户反馈驱动增量修复，机制不变 |
| F2: 部分截断根因是第三方组件（Miuix/Dialog 内部固定尺寸），单点修复可能不可行 | 可行时修，不可行时登记为已知限制 | 组件级 workaround（外层容器放大/局部 fontScale 覆写） |
| F3: ColorPickerSheet 未经大规模使用验证（曾上线后被迁移删除，非质量原因下线） | 原 ThemeConfigScreen 时期已实际服役；接入后 L2 真机验证 | 保留 SimpleColorPickerDialog 代码一个迭代期，异常时可快速回切 |

## Requirements

### Requirement: 主界面底栏搜索框显隐入口（F1）
用户可从"我的设置页"直接切换主界面底栏（floating 悬浮模式）搜索框的显示/隐藏；底栏管理编辑对话框内既有开关保留。
- 配置项沿用 `AppConfig.floatingBottomBarHideSearch`（PreferKey.floatingBottomBarHideSearch），不新增 pref
- 生效链不变：`MainActivity.isFloatingSearchHidden()`（L723）/ `MainTopBarView.isFloatingSearchHidden()`（L264）
- 开关切换后主界面底栏即时刷新（无需重启）
- 仅 floating 模式生效；sidebar/standard 模式下开关条目仍可见但 summary 标注生效范围

#### Scenario: 设置页隐藏搜索框
- **WHEN** 用户在"我的 → 设置 → 界面设置"关闭"主界面底栏搜索框"开关，当前为 floating 模式
- **THEN** 返回主界面后底栏右侧悬浮搜索按钮消失，其余底栏控件布局正常（搜索图标相关约束不残留）

#### Scenario: 设置页恢复搜索框
- **WHEN** 用户打开该开关
- **THEN** 悬浮搜索按钮恢复显示，点击搜索功能正常

#### Scenario: 非 floating 模式
- **WHEN** 底栏为 standard 或 sidebar 模式
- **THEN** 该开关不改变任何可见布局（standard 本就不显示悬浮搜索按钮），summary 明确提示仅悬浮底栏模式生效

#### Scenario: 底栏管理既有开关一致性
- **WHEN** 用户在底栏管理 → 编辑 → 搜索开关切换后，再查看我的设置页快捷开关
- **THEN** 默认套装下两处开关状态一致（默认套装经 currentSignature/defaultEntry 往返同步同一 pref）
- **AND** 激活自定义底栏套装时，我的设置页不显示该快捷开关（套装配置为权威源，底栏管理内配置以套装编辑为准）

### Requirement: 字号放大组件适配（F2）
fontScale 处于 1.4x~1.6x 时，核心页面与常用弹窗的文本组件不得出现文字截断（显示一半/省略丢失关键信息）；1.0x 默认缩放无任何样式劣化。
- 修复对象以实测截断点清单为准（书架/发现/订阅/我的/阅读菜单/主题设置/高频弹窗）
- 修复手段：文本容器固定高度改最小高度约束（`heightIn(min=)`）或自适应；禁止盲目批量替换
- 每处修复必须同时验证 1.0x 无回归

#### Scenario: 1.6x 走查无截断
- **WHEN** 字号缩放设为 16（1.6x），走查 F2 清单页面
- **THEN** 清单内组件文字完整显示，无"显示一半"现象

#### Scenario: 1.0x 无回归
- **WHEN** 字号缩放恢复默认（1.0x）
- **THEN** 修复点样式与修复前一致（高度、对齐、留白无可见变化）

### Requirement: 主题编辑页恢复优化版取色器（F3）
主题编辑（ThemeEditorScreen）颜色槽位点击后弹出 `ColorPickerSheet`（预置色板 + HSL 三滑块 + 活预览），替换简版 `SimpleColorPickerDialog`。
- 可选槽位（`isOptionalSlot`）保留"跟随默认"能力
- 确认回调返回 ARGB hex（与现有 `updateColor(slot, hex)` 对接）
- 取消/关闭不落任何 pref

#### Scenario: 固定槽位取色
- **WHEN** 用户点击非可选色槽（如主题色）
- **THEN** 弹出优化版取色器（预置色板 + HSL 滑块可见），选色确认后槽位色值更新，预览区同步刷新

#### Scenario: 可选槽位跟随默认
- **WHEN** 用户点击可选槽位（当前为跟随默认状态）并取色确认
- **THEN** 颜色写入该槽位；后续可通过"跟随默认"操作清除（`clearOptionalColor` 语义保留）

#### Scenario: 取消不生效
- **WHEN** 用户打开取色器后取消/点外部关闭
- **THEN** 槽位色值不变，无 pref 写入

## 边界条件

- F1: pref key 缺失 → `getPrefBoolean` 默认 false 兜底；该 key 无类型脏值写入点（既有写入链均为 boolean）
- F1: 自定义底栏套装激活 → 设置页开关条目隐藏（套装 applyCurrentBottomConfig 会覆写 pref，避免静默回滚）
- F1: 开关快速连点 → 无动画竞态风险（isVisible 布尔渲染，幂等）
- F2: fontScale 越界脏值 → `AppContextWrapper` 已有 0.8~1.6 校验兜底（L58）
- F2: 低端机放大后性能 → 仅改布局约束不引入测量开销
- F3: `initialColor` 传入 null/非法 hex → 沿用现 `parseHexOrNull` 兜底 Gray
- F3: HSL 滑块快速拖动 → Compose state 驱动，无竞态
- F3: ColorPickerSheet 在 ThemeEditorDialogFragment（Dialog 宿主）内弹出 → 有生产先例（ChangeBookSourceDialog 内 AppMenuSheet 同容器），实施时验证 back 键先关 sheet、点外关闭不落 pref
