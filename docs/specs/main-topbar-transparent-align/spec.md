# spec.md — main-topbar-transparent-align

## Intent
恢复主界面四大 Tab（书架/发现/订阅/我的）头部透明沉浸能力，对齐 Archive 最新版（archive-ref/legado-08172114）的视觉行为：配置背景图时，状态栏+顶栏区域连续透出背景图；未配置背景图时保持现状实色。

## Scope
### In（本轮范围）
- 恢复 `MaterialValueHelper.kt` 中 `Context.backgroundColor` / `Fragment.backgroundColor` 的透明分支（P0）
- `BaseActivity` 窗口底色策略对齐：`initTheme` / `upBackgroundImage`（P1），保留本项目管理页 tint 钩子
- `Context.backgroundColor` 全部消费点回归盘点与验证
- 四 Tab 头部视觉真机验证（背景图 on/off × 昼夜主题）

### Out（本轮排除）
- 书架/订阅 overlay 覆盖式布局重构（双方行为一致，非根因）
- backdrop blur 毛玻璃激活（Archive 自身恒传 null，从未激活）
- `TopBarConfig` 透明度字段扩展、窗口层 `fullScreen()`/`setStatusBarColorAuto` 重写
- 播放器/阅读器沉浸页（手势红线不改造）
- 发现页 `topBarColorManaged` 托管链（本项目新增设计，已含 TRANSPARENT 分支，仅验证不改动）

## Approach

### Selected Approach
**恢复透明原语 + 着色策略对齐**（增量修复，不改架构）：
1. `MaterialValueHelper.kt`：恢复 Archive 版实现——`!EInk && ThemeConfig.hasUsableBgImage → Color.TRANSPARENT`，否则 `ThemeStore.backgroundColor`；`Fragment.backgroundColor` 恢复为委托 `context` 扩展。
2. `BaseActivity.kt`：`initTheme` 非管理页宿主路径对齐 Archive（清 decorView tint + fallback 实色）；`upBackgroundImage` 基类恢复三分支（无图→清 tint+实色 / 有图→清 tint 后挂图 / 异常→实色）。
3. 真机验证矩阵驱动收口，不通过则按排查清单逐层定位（decorView → 窗口背景层 → Fragment 根 → 顶栏）。

选型理由：唯一被证据（逐行 diff）支撑的分叉点；改动面最小；不引入新机制，纯粹"把删错的东西学回来"。

### Alternatives Considered
| 备选方案 | 否决理由 |
|---------|---------|
| 激活 backdrop blur + overlay 覆盖式布局 | Archive 自身所有宿主均 `setBackdropBlur(null)`，毛玻璃从未激活；该方案是对错误根因的猜测，成本高且引入穿帮风险 |
| 四 Tab 头部 Compose 化重写（GlassTopAppBar） | 违背 ui-standards 顶栏三基线门禁（主 Tab 基线为 MainTopBarView）；成本高，且不解决透明原语缺失 |
| 新增"强制透明"设置开关 | 治标不治本，绕过取色唯一基线（ui-standards 铁律 2），增加配置面 |

### Drawbacks
- **消费点语义变化**：`backgroundColor` 恢复透明分支后，配置背景图时所有消费点（MainTopBarView L430/L481、AppManagementScaffold L97/L157、AppSettingComponents L141/L143、BookCoverImage L386 等）从实色变透明，存在视觉回归风险。兜底：全量 Grep 盘点消费点清单 + E-Ink 强制不透明保留 + 真机回归矩阵。
- **无法 100% 预判用户全部视觉场景**：P0/P1 修复后若仍有页面头部不透明，兜底：tasks.md 内置逐层排查清单（decorView → 窗口背景层 → Fragment 根 → 顶栏），验证驱动收口。
- **接受理由**：对齐 Archive 是用户明确决策；Archive 同机制已在线上验证。

## Requirements

### Requirement: 透明原语恢复（R1）
配置背景图且非 E-Ink 模式时，`Context.backgroundColor` 与 `Fragment.backgroundColor` 返回 `Color.TRANSPARENT`。
#### Scenario: 配置背景图取色透明
- **WHEN** 用户在主题设置中配置了可用背景图，非 E-Ink 模式
- **THEN** `backgroundColor` 返回透明色，头部区域透出背景图

### Requirement: 无背景图行为不变（R2）
未配置背景图时，取色与现状一致。
#### Scenario: 无背景图取实色
- **WHEN** 未配置背景图
- **THEN** `backgroundColor` 返回 `ThemeStore.backgroundColor` 实色，头部视觉与修复前一致

### Requirement: E-Ink 强制不透明（R3）
E-Ink 模式下永远返回实色。
#### Scenario: E-Ink 兜底
- **WHEN** E-Ink 模式开启且配置了背景图
- **THEN** `backgroundColor` 仍返回实色（不透明）

### Requirement: 窗口底色策略对齐（R4）
`BaseActivity` 非管理页宿主路径：`initTheme` 清 decorView tint + fallback 实色；`upBackgroundImage` 有图清 tint 后挂图、无图恢复实色底。
#### Scenario: 带背景图 Activity 底色
- **WHEN** 非主界面的普通 Activity 配置背景图
- **THEN** decorView 无残留 tint，背景图为最终底色

### Requirement: 消费点视觉回归（R5）
透明原语恢复后，全部消费点在背景图 on/off 两形态下无异常视觉。
#### Scenario: 消费点回归
- **WHEN** 配置背景图后进入管理页/设置组件/书源封面等消费点页面
- **THEN** 无黑块/穿帮/对比度异常，行为与 Archive 一致

### Requirement: 四 Tab 头部透明（R6）
主界面四 Tab 在背景图模式下，状态栏+顶栏区域连续透出背景图。
#### Scenario: 四Tab头部沉浸
- **WHEN** 配置背景图，切换书架/发现/订阅/我的四个 Tab
- **THEN** 头部区域（含状态栏）无实色色带，透出背景图

## 验收口径
- R1-R6 全部 Scenario 通过真机 L2 验证（背景图 on/off × 昼夜 × E-Ink 抽查）
- 编译零错误、无新增调试日志残留
