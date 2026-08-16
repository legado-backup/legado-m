---
name: compose-ui-engineering
description: "Use when 编写、审查或重构任何 Jetpack Compose UI 代码（@Composable / State / 组件 / 动画 / 性能 / UI 测试），或执行 Legado 项目 XML View→Compose 迁移（ui-redesign-m3 专项）。只要任务涉及 Compose 状态管理、重组性能、可复用组件设计、Modifier、动画 API、Compose 测试、或把现有 View 页面改造成 Compose，即使未明确说 Compose，也应在动手前先读本 skill。"
---

# Compose UI Engineering（Legado 项目 Compose 工程指导）

## Overview

Compose 是函数式 UI 描述：`@Composable` 函数会被运行时重复执行（重组）。绝大多数 Compose 工程问题不是"不会写 API"，而是四个判断出错：**状态归属（owner）、effect 生命周期、组件契约、性能主轴**。本 skill 提供一套决策框架，结合 Legado 的 ui-redesign-m3 迁移工作流使用。

本 skill 是**通用工程方法论**，不是项目设计规范的复读。涉及具体颜色/间距/组件目录/骨架/页面清单时，去读规范文档（见下文"项目文档"），这里只告诉你"何时读什么、为什么"。

## 核心原则

1. **每个 state 只有一个最低必要 owner**；命令式工作通过生命周期匹配的 effect API 执行，绝不放 composable 体内。
2. **可复用组件是"结构 + 槽位"**：组件拥有不变结构，调用者拥有放置（modifier）、内容（slot）、策略选择；能用 slot 就不用一堆 `title:String`+`Boolean` 参数。
3. **性能只处理被测量出的主轴**：先复现一个可感知的过渡取证据，分类重组轴/布局轴，再在轴起点做最小修正；不凭直觉加 stability wrapper。
4. **动画选最小 API**：能用 `animate*AsState` 不用 `Animatable`，能用 `AnimatedVisibility` 不用手写状态机。
5. **测试测最小 UI 契约**：plain state-driven composable + 回调捕获，不构造整个 ViewModel/组件图。
6. **先分类骨架，再写代码**：每个页面先归类 S1-S6 骨架，复用公共组件，最后填实施回执。

## 项目文档（权威规范，改造前必读）

| 文档 | 内容 | 何时读 |
|------|------|--------|
| `docs/specs/ui-redesign-m3/ui-standards.md` | 设计基石/骨架六类/组件目录/状态管理/检查清单/KPI | 任何 Compose 页改造前 |
| `docs/specs/ui-redesign-m3/pages-inventory.md` | 84 页功能点清单 | 定位要改造的页面时 |
| `docs/specs/ui-redesign-m3/tasks.md` | 任务进度 + 实施回执 | 改造完成后填回执 |
| `.trae/memory/ai_memory_main.md` | 项目记忆/已交付状态 | 开工前了解当前进度 |

**快速路径**：改造任何页面 → 先读 `ui-standards.md` §7 检查清单 + 目标页面对应骨架样板（S1-S6，见 ui-standards §2）→ 遵循本 skill 的工程决策 → 填回执。

## 决策框架

### 1. 状态管理（state owner）

给每块 UI 状态找一个"最低必要 owner"。规则：

| 情境 | Owner |
|------|-------|
| 单个 composable 读写简单 UI 状态 | 本地 `remember { mutableStateOf() }` |
| 兄弟/父级需要读它 | 提升（hoist）到最低公共祖先 |
| 多个关联 `remember` + 具名操作（clear/submit/openFilters）+ 派生 flag | 抽 plain state holder 类（`rememberXxxState()`） |
| 涉及仓库调用/持久化/业务规则/屏幕 UI 状态 | 屏幕级 state holder（`ViewModel` + Room Flow） |
| 屏幕同时做业务收集和布局 | 拆两层：state-holder composable 收集 → plain UI composable 只收不可变 state + 显式回调 |

必须遵守的项目约束：Legado 用 `Coroutine.async{}.onSuccess{}.onError{}` 链 + `xxxAwait()`，不用标准 launch+try/catch；Room Flow 用 `collectAsStateWithLifecycle`；Fragment 只做壳（XML 壳 + ComposeView 桥接）。

### 2. Effect（副作用）选择

Composable 体内只描述 UI。改变外部世界的工作放进生命周期匹配的 effect：

| 需求 | API |
|------|-----|
| 每次重组后发布 state 到非 Compose 代码 | `SideEffect` |
| 注册/注销监听、回调、资源 | `DisposableEffect(keys...)`（必须有 onDispose 清理） |
| 挂起/一次性/按 key 重启的工作 | `LaunchedEffect(keys...)` |
| 从点击等事件回调里启动挂起工作 | `rememberCoroutineScope()`（禁止 event flag 反模式） |
| Compose 快照读→Flow | `snapshotFlow{}` 放 `LaunchedEffect` 内 |

**key 规则**：key = effect 跟随的生命周期对象（userId/screenId/lifecycleOwner）。禁止用 `Unit` 掩盖变化的输入；禁止用宽泛对象（state/viewModel）当 key。长生命周期 effect 需最新回调用 `rememberUpdatedState`，但只在"不应重启但值要新鲜"时用；值变了应重启就把它当 key。

### 3. 组件设计（component contract）

可复用组件的 API 决策：**能 slot 就 slot，能用 modifier 就让调用者放位置**。

- 组件根接受 `modifier: Modifier = Modifier`。
- 调用者控制的、无约束的视觉区域用 slot：`xxxContent: @Composable () -> Unit`（可选则 `(@Composable () -> Unit)? = null`，null 表示"无此区域"，省空间）。
- 语义约束/设计系统/受限类型（如 `Switch(checked, onCheckedChange)`）保留 primitive 参数。
- 常见默认内容进 `XxxDefaults` 对象（如 `SettingsRowDefaults.Chevron()`）。
- slot 落在 Row/Column/Box 内时用对应 scope receiver（`RowScope.() -> Unit`）。
- 单次使用、无复用计划的组件**不要**发明 slots——primitive 参数 + 内联即可。

### 4. 性能（performance）

只处理被测量出的问题。流程：

1. 复现一个用户可感知的过渡，取证据（recomposition 次数 / compiler reports / profiler）。
2. 分类主轴：参数稳定性导致的重组 / State 读取时机 / 布局-组合回写。
3. 排除假线索：真实数据变化、正确性缺陷、预期内的重组。
4. 一次只改一个轴，重测。

关键知识：
- 重组数量要压的是"输入没变却重组"；输入真变了不许硬压。
- 帧率级 State 读（scroll/animation/gesture/layout/draw）用延迟读取（在 layout/draw 块读），不在组合里读。
- 禁止在组合体内 back-write snapshot state 重建派生数据；用 `remember(keys) { derived }`。

### 5. 动画（animations）

选最小 API：

| 问题 | API |
|------|-----|
| 子树显隐 | `AnimatedVisibility` |
| 单属性冲向目标 | `animate*AsState` |
| 多值同驱动 | `rememberTransition` |
| 尺寸平滑变化 | `Modifier.animateContentSize()` |
| 同一槽位换整棵组合树 | `AnimatedContent` / `Crossfade`（按 contentKey 视觉形状切） |
| 手势/逐帧驱动 | `Animatable` |

陷阱：`animateFloatAsState(alpha)` 只淡出不卸载；动画背景用 `Modifier.drawBehind { drawRect }`；导航自带转场勿重复 `AnimatedContent`；帧率动画值在 layout/draw 块延迟读取。

### 6. UI 测试

测最小契约：plain state composable + 回调捕获，不构造 ViewModel/仓库/导航。

- 文字存在/按钮使能 → semantics（`onNodeWithText` / `assertIsEnabled`）。
- 点击回调接线 → 捕获变量断言。
- 布局/间距/颜色/图片 → screenshot test（固定数据、冻结时钟、fake 图片加载器）。
- hover/press/focus 态 → 注入 `MutableInteractionSource` 并 `emit`，不用鼠标/触摸模拟。
- 语义断言优于 test tag；test tag 只用于无稳定文字节点。

## 迁移工作流（改造一个页面）

```
1. 定位页面：读 pages-inventory.md 找目标页功能点
2. 分类骨架：读 ui-standards.md §2 → 归类 S1-S6
3. 找样板：读 ui-standards.md §9 主干-支干-枝叶 → 该骨架首个样板页
4. 组件盘点：读 ui-standards.md §3 组件目录 → 能复用则复用，禁私有复制
5. 状态设计：按决策框架 §1-§2 定 owner 和 effect
6. 编写：遵循 §3-§5（组件契约/性能/动画）+ 设计规范（主题/色/间距/无障碍/i18n）
7. 测试：§6 + 真机功能点覆盖（ai_tests 框架）
8. 文档同步：pages-inventory/tasks/updateLog.md 更新
9. 填实施回执：ui-standards.md §3.3 模板贴 tasks.md
```

## 项目设计硬约束（防回归）

- 所有 Compose 页必须包 `LegadoTheme{}`（ThemeStore 5 核心色 → M3 scheme），**禁止 `Color(0x...)` 硬编码**（豁免需登记）。
- 圆角 token 4/8/12/16dp（卡 18dp/按钮 12dp 默认）；间距 4dp grid；触控 ≥48dp；页边距 16dp。
- 新文案进 strings.xml（en+zh 双语），禁硬编码中文。
- 阅读器正文保留原生 View，浮层用 Compose 壳-核分离。
- 新组件必须 camelCase+用途前缀+KDoc 设计来源（AD-xx 或 fork 来源）+ 登记组件目录。

## Common Mistakes

| 错误 | 修正 |
|------|------|
| composable 体内 `var x = ...`（无 remember） | `var x by remember { mutableStateOf() }` |
| 网络请求直接写在组合体 | 移到 ViewModel/state holder；UI 拥有的 keyed 工作才用 LaunchedEffect |
| `LaunchedEffect(Unit)` 捕获变化的 id | key 用 id，或确实不重启时用 rememberUpdatedState |
| `remember { mutableStateOf(list) }` 后 `.add(x)` 不重组 | 用 `mutableStateListOf` 或整体替换值 |
| 组件暴露 `title:String / icon:ImageVector? / 多个 display flag` | 改 slots（组件有复用场景时） |
| 动画背景色用 `background()` | `Modifier.drawBehind { drawRect }` |
| 点击触发 effect 用 event flag | 直接在 onClick 用 `rememberCoroutineScope()` |
| 凭直觉加 stability wrapper 压重组数 | 先测量，确认输入没变却重组 |
| 页面私有复制公共组件能力 | 复用 ui-standards §3 组件目录 |
| 硬编码颜色/中文文案 | LegadoTheme 色板 + strings.xml |

## 详细参考（按需读，勿一次全载入）

| 主题 | 文件 |
|------|------|
| 状态归属深潜（local/hoisting/state holder 决策） | `references/state-and-effects.md` |
| 组件 slot API 设计深潜 | `references/component-design.md` |
| 性能诊断与稳定性 | `references/performance.md` |
| 动画 API 全表与陷阱 | `references/animations.md` |
| UI 测试模式 | `references/testing.md` |
| 本项目 View→Compose 迁移适配 | `references/migration-workflow.md` |

## RED/GREEN 验证场景

- **RED**：改造列表页时未读 ui-standards，直接用 `Color(0xFF...)` 硬编码 + 私有复制组件。
- **GREEN**：先读规范 → 归类 S2 列表页骨架 → 复用 SettingsCard/SettingsClickRow → 状态用 state holder → 填实施回执。
- **Counterexample**：单次使用的小型屏幕私有 helper 无需发明 slots / 不强制拆 state-holder/UI 两层。
