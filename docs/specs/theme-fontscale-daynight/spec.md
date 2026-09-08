# spec.md — 主题字体大小：默认值统一与日夜配置生效修复

## Intent
主题「字体大小」（fontScale）体系存在两类问题：夜间主题配置的字号从未生效（`fontScaleN` 键只写不读）；首次安装时内置主题字号为「跟随系统」而非用户期望的统一值 9（0.9 倍）。本规格旨在让日夜主题的字号配置各自真实生效，并按用户决策统一默认字号。

## Scope

### In Scope
- `AppContextWrapper` 全局字号读取的日夜感知修复（wrap() 与 getFontScale 公共入口）
- 顶栏尺寸联动调用点的日夜感知同步（MainTopBarView、TopBarConfig）
- 内置日/夜主题（ThemePackageManager.builtinEntry）的 fontScale 默认值调整（按 AD-02 决策）
- 首次安装字号种子写入方案（若 AD-02 选含种子的方案）
- 历史遗留默认主题资产处置（按 AD-03 决策）

### Out of Scope
- 阅读器字号体系（ReadBookConfig，独立配置）
- 书源编辑器字号（SettingsDialog.editFontScale，独立配置）
- ThemeStore 颜色体系、主题包管理器结构、RED 主题导入逻辑
- 主题字体（uiFontPath/titleFontPath）日夜生效问题（当前无证据失效，如有另行立项）

## Approach

### Selected Approach
**字号读取日夜感知**：`AppContextWrapper.wrap()` 内已有基于 `themeMode` 偏好的 nightBit 判定（不受 attachBaseContext 阶段 AppConfig 不可用限制），复用该判定推导 `isNight`，`getFontScale(context, isNight)` 按 `ThemeRuntimeKeys.fontScale(isNight)` 对应键读取。View 层调用点（MainTopBarView/TopBarConfig）从已修正的 `context.resources.configuration.uiMode` night bit 推导当前日夜态，保证与全局配置同源。落地理由：单源修复，所有消费点自动对齐；不引入新依赖；与现有 legacy 迁移（ThemeRuntimeKeys.migrateLegacyNightValues）兼容。

### Alternatives Considered
| 备选方案 | 否决理由 |
|---------|---------|
| 切换日夜时把对侧字号复制覆盖到当前键（单键方案） | 破坏日夜双配置独立性，与颜色/字体等其它主题属性的双键架构不一致；覆盖后用户切换回白天丢失原配置 |
| 各消费点自行读写偏好键 | 五个消费点重复实现，违背尺寸单源原则（bugfix-0908f 已确立 TopBar 与 View 顶栏同源约束），后续新增消费点易再漏 |
| 在 getFontScale 缓存日夜两值由调用方选择 | 缓存失效时机复杂（RECREATE/ThemeSync 多路径），增加状态不一致风险，收益为零 |

### Drawbacks
- **已知缺陷**：View 层从 `configuration.uiMode` 推导日夜态，若未来有页面绕过 `AppContextWrapper.wrap()` 创建 context，则 night bit 可能未修正 → 风险点：现有 BaseActivity/BaseDialogFragment 均经 wrap()，无绕过路径
- **已知缺陷**：修改 getFontScale 签名为必传 isNight 是破坏性变更，编译期可发现全部遗漏调用点（Kotlin 无默认参数设计，防静默漏改）→ 接受理由：编译期暴露优于运行期错值
- **兜底预案**：读取失败/键缺失时维持现有回退逻辑（值域 0.8~1.6 之外回落系统 fontScale），行为不劣于修复前

## Requirements

### Requirement: 夜间主题字号真实生效
切换到夜间主题后，全局字体缩放必须读取夜间字号键（`fontScaleN`）的配置值；夜间键无有效值时按现有规则回退（回落系统 fontScale）。

### Requirement: 白天主题字号行为不变
白天模式下读取 `fontScale` 键的行为与修复前完全一致，已有用户白天字号配置零迁移成本。

### Requirement: 顶栏尺寸与全局字号同源
MainTopBarView 顶栏按钮/图标尺寸、TopBarConfig 顶栏尺寸计算与全局字号使用同一日夜判定与同一读取入口（延续 bugfix-0908f 尺寸单源约束）。

### Requirement: 内置主题默认字号（AD-02 定稿 2A）
内置日间/夜间主题 `fontScale=9`（0.9 倍），应用内置主题后生效；磨砂玻璃套件资产内 fontScale 同步修正为 9（消除 100→clamp 16 缺陷）；未应用主题前保持跟随系统。

### Requirement: 历史资产移除与暗夜紫能力不回退（AD-03 定稿）
移除 themeConfig.json 及 DefaultData/LocalConfig/Restore 导入链；暗夜紫 Config 迁移为代码内置常量，首装夜间暗夜紫预设、可回切注册、外观套件 ensure 三处能力零回退。

### Requirement: 初始化预置主题体系（AD-04）
- 首次安装后主题列表含：内置日/夜主题、暗夜紫（日+夜）、磨砂玻璃晨/昏（日+夜）
- 暗夜紫日间版为夜间配色系推导的浅紫调，L2 真机验收
- 磨砂套件图片压缩（背景重采样 1080 宽、JPEG q≈80，套件 ≤1.2MB）后以 ASCII 文件名入 assets
- seeding 幂等（pref 标记 + localThemeExists 双保险），不自动套用磨砂套件，已删除套件的用户不被重复注入

## Scenarios

#### Scenario: 夜间主题应用独立字号后切换日夜
- **WHEN** 用户为夜间主题设置字体大小 9 并应用，随后在白天/夜间之间反复切换
- **THEN** 夜间模式下全局字号缩放为 0.9，白天模式为白天主题配置值（或系统值），两态互不串扰

#### Scenario: 夜间键无配置
- **WHEN** 夜间主题从未设置字体大小（fontScaleN 缺失或为 0）
- **THEN** 夜间模式全局字号回落系统 fontScale，与修复前白天键缺失行为一致，无崩溃无异常值

#### Scenario: 首次安装默认字号与预置主题
- **WHEN** 全新环境首次安装并进入应用
- **THEN** 夜间模式默认呈现暗夜紫主题套件（现有能力）；应用内置/预置主题后字号为 0.9 倍；主题列表含暗夜紫（日+夜）与磨砂玻璃晨/昏套件

#### Scenario: 老用户升级不被预置套件干扰
- **WHEN** 已删除磨砂套件或已自选其它主题的老用户覆盖安装升级
- **THEN** seeding 幂等不重复注入，当前主题与字号选择不变

#### Scenario: 顶栏尺寸联动日夜一致
- **WHEN** 夜间模式下字号为 0.9
- **THEN** 顶栏动作按钮容器/图标尺寸按 0.9 缩放，与标题 sp 缩放视觉同步

#### Scenario: 老用户升级
- **WHEN** 已有用户（白天/夜间键均可能有历史值）覆盖安装新版本
- **THEN** 白天与夜间字号均按各自已存配置生效，无跳变；legacy 迁移键（ThemeRuntimeKeys.migrateLegacyNightValues）行为不受影响
