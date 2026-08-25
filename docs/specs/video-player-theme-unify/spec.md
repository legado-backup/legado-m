# 视频播放器主题统一 — 需求规格

> 关联设计文档：[design.md](./design.md)｜任务清单：[tasks.md](./tasks.md)

## Intent

内置视频播放器（GSYVideoPlayer）的 UI 是孤立的孤儿样式，主题设置完全管不到，弹框样式丑陋，与整体主题风格不搭。本规格旨在让播放器 UI 全面接入 ThemeStore 主题体系，消除硬编码颜色与硬编码中文。

## Scope

### 做（In Scope）

| 编号 | 内容 |
|------|------|
| S-1 | 播放器控制条（video_layout_controller.xml / full）主题化：进度条/缓冲/选中高亮用主题强调色 |
| S-2 | 倍速弹框（ChoiceSpeedDialog）动态设色 |
| S-3 | 选集弹框（ChoiceEpisodeDialog）动态设色 |
| S-4 | 画面比例/音轨原生 AlertDialog 接入项目主题 |
| S-5 | activity_video_player.xml 旧模式功能区 + 调试面板硬编码色清理 |
| S-6 | 硬编码中文文案迁移 strings.xml（en+zh 双语） |
| S-7 | 主题切换时 View 侧颜色刷新（EventBus.RECREATE / onConfigurationChanged 兜底） |

### 不做（Out of Scope）

| 编号 | 内容 | 理由 |
|------|------|------|
| O-1 | GSY 播放器核心逻辑（视频引擎/降级链/手势/自动隐藏状态机） | 零改动，防回归 |
| O-2 | 迁移 Compose | S5 View 内核红线 |
| O-3 | 弹幕功能颜色 | 用户配置项，非孤儿样式 |
| O-4 | 布局结构重构 | 仅颜色/圆角/文案主题化 |

## Approach

### Selected Approach：View 侧代码动态主题化（深色悬浮层 + 主题高亮）

1. **控制条**：保持深色半透明悬浮层（视频站标准，日夜间可读），进度条/缓冲/选中高亮动态取 `ThemeStore.accentColor()` / `primaryColor()`。
2. **弹框（倍速/选集）**：show 前用 `ThemeStore.backgroundColor()` / `textColorPrimary()` / `accentColor()` + `UiCorner.panelRadius` 动态设色，保留分隔项/右侧滑出/选中高亮特殊交互。
3. **画面比例/音轨**：AlertDialog 改用项目 `alert()` 扩展（`io.legado.app.lib.dialogs.alert`）自动应用项目主题。
4. **主题刷新**：BaseActivity 已订阅 `EventBus.RECREATE`（recreateOnThemeChange=false 时走 `refreshThemeAppearanceIfChanged()`），播放器控件新增 `applyThemeColors()`，在 RECREATE / onConfigurationChanged / 控件显示时调用。
5. **文案资源化**：硬编码中文 → strings.xml（en+zh）。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 迁移 ComposeDialog 家族 | 倍速弹框有分隔项/右侧滑出/选中高亮特殊交互，重写成本与回归风险高；S5 红线禁止迁移 |
| 纯静态资源主题化（XML 改 @color/xxx） | 播放器页面 `recreateOnThemeChange=false`，静态颜色不随主题刷新，只对首次进入有效 |
| 控制条完全跟随主题切换浅深色 | 视频画面背景下浅色悬浮层可读性风险高，与视频站标准交互不符 |

### Drawbacks

- 代码动态设色增加样板代码（相比静态资源）。
- 弹框背景/文字需在 show 前显式设置，遗漏会导致主题不生效。
- 需为播放器控件补充主题刷新入口（RECREATE 监听），增加少量复杂度。
- 控制条背景不随主题变化，主题感主要体现在高亮与弹框。

### Prior Art

- `AudioPlayActivity`（沉浸播放页 `recreateOnThemeChange=false` 范式）。
- `VideoSettingsPanel.onStart()`（动态设 sheet 背景 + 圆角）。
- `UiCorner.surfaceColor()` / `rounded()`（View 侧主题化工具）。
- `ChoiceSpeedDialog` 已部分主题化（`R.color.primary`/`primaryText`/`card_video_background`）。

## Requirements

### FR-1 控制条主题化

- [ ] FR-1.1 底部进度条播放进度用 `ThemeStore.accentColor()`
- [ ] FR-1.2 缓冲进度用主题色半透明
- [ ] FR-1.3 控制条文字/图标保持深色悬浮层高对比（可读性不降）
- [ ] FR-1.4 全屏控制条（video_layout_controller_full）与普通控制条一致

### FR-2 弹框主题化

- [ ] FR-2.1 倍速弹框背景 = `ThemeStore.backgroundColor()`，文字 = `textColorPrimary`，选中高亮 = `accentColor`
- [ ] FR-2.2 选集弹框同 FR-2.1
- [ ] FR-2.3 画面比例/音轨 AlertDialog 应用项目主题（走 `alert()` 扩展）

### FR-3 硬编码色清理

- [ ] FR-3.1 activity_video_player.xml 旧模式功能区（#1A2B4A / #8AB4F8）
- [ ] FR-3.2 调试面板（#80000000 / #FFFFFF）

### FR-4 文案资源化

- [ ] FR-4.1 倍速/关弹幕/开弹幕/画面比例/音轨/选集/默认/16:9/4:3/填充/倍播放中 → strings.xml（en+zh）

### FR-5 主题刷新

- [ ] FR-5.1 播放器控件提供 `applyThemeColors()`
- [ ] FR-5.2 主题切换（EventBus.RECREATE）/ onConfigurationChanged 时刷新 View 侧主题色

## Scenarios

### S-01 日间模式进入播放器

用户日间模式打开播放器 → 弹框为浅色主题背景 + 主题文字色；控制条为深色悬浮层 + 主题色进度条；全屏/普通一致。

### S-02 播放中切换主题

用户在播放中切换主题 → 页面不重建（recreateOnThemeChange=false），但进度条高亮/弹框颜色随主题刷新。

### S-03 倍速弹框

用户点倍速 → 弹框背景/文字/选中高亮与主题一致，分隔项/右侧滑出/高亮交互保留。

### S-04 画面比例/音轨

用户点画面比例/音轨 → 弹窗走项目主题样式，不再出现系统默认灰框。
