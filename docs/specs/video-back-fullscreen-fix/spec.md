# spec.md — 视频播放器返回按钮修复 + 全屏按钮迁移 + 真全屏优化

## Intent

用户报告订阅源内置视频播放器的左上角返回按钮在**所有版本**（包括最新安装包）中都不生效，点击后无法退出播放器。同时用户要求：
1. 将全屏按钮从视频中下方移到右侧功能区，随右侧功能区整体隐藏/展示
2. 当前全屏是"伪全屏"（TitleBar 隐藏但仍占布局空间），希望做到真正的全屏

## Scope

### In Scope

1. **B1 返回按钮修复**：修复 TitleBar 返回箭头点击无响应的问题
2. **U1 全屏按钮迁移**：将 `btn_fullscreen` 从底部居中移到 `right_buttons` 容器内
3. **F1 真全屏**：全屏时 TitleBar 用 `gone()` 而非 `hide()` 释放布局空间，playerView 铺满整个屏幕

### Out of Scope

- GSY 旧模式（legacyContainer）的返回按钮修复（已废弃，ViewPager2 模式是唯一活跃模式）
- WebView 降级播放器的全屏逻辑（WebView 模板内自带全屏）
- 竖屏视频的全屏（竖屏视频不显示全屏按钮，仅横屏视频支持）

## Approach

### Selected Approach

**B1 返回按钮修复 — 直接绑定 setNavigationOnClickListener**

不依赖 `onSupportNavigateUp()` 的 ActionBar navigateUp 机制（当前已重写但疑似未生效），改为在 `switchToViewPagerMode()` 中直接调用 `binding.titleBarNew.setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }`。

理由：
- `onSupportNavigateUp()` 依赖 `setSupportActionBar` → ActionBar → navigateUp 的完整链路，中间任一环节断裂都会导致不生效
- `setNavigationOnClickListener` 直接在 Toolbar 上绑定点击事件，不依赖 ActionBar 机制，更可靠
- 同时加临时日志验证点击事件是否触发（P0 规则23）

**U1 全屏按钮迁移 — 移入 right_buttons 容器**

将 `btn_fullscreen` 从 fragment_video.xml 的独立位置（底部居中）移到 `right_buttons` LinearLayout 内（作为第5个按钮）。移除 `updateFullscreenButtonVisibility()` 中"横屏视频一直显示全屏按钮"的特殊逻辑，改为随 `right_buttons` 整体显隐。

**F1 真全屏 — TitleBar gone() 替代 ActionBar hide()**

将 `toggleFullScreen()` 中的 `supportActionBar?.hide()` 改为 `binding.titleBarNew.gone()`，让 TitleBar 释放布局空间，ViewPager2 扩展到屏幕顶部。退出全屏时 `binding.titleBarNew.visible()` + `supportActionBar?.show()`。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| B1-Alt1: 修复 onSupportNavigateUp 时序（确保 setSupportActionBar 只调用一次） | 时序问题涉及两个 TitleBar 的 attachToActivity 冲突，修复复杂且不稳定；setNavigationOnClickListener 更直接可靠 |
| B1-Alt2: 移除 title_bar（legacyContainer 中的 TitleBar） | legacyContainer 虽废弃但仍有代码引用，移除影响范围大，超出本次修复范围 |
| U1-Alt1: 全屏按钮保留在底部但随控件整体显隐 | 用户明确要求"放到右侧功能区去"，不只是显隐问题 |
| F1-Alt1: 使用 WindowInsetsController 的 setDecorFitsSystemWindows(false) | 可配合使用，但核心问题是 TitleBar 占空间，gone() 是最直接的解决方案 |
| F1-Alt2: 全屏时切换到独立的全屏 Activity | 架构改动过大，需重建播放状态，体验不连续 |

### Drawbacks

| 缺点 | 接受理由 |
|------|---------|
| setNavigationOnClickListener 绕过 ActionBar 机制，与项目其他 Activity 风格不一致 | VideoPlayerActivity 是特殊场景（沉浸式视频播放），可靠性优先于一致性 |
| 全屏按钮移到右侧后，竖屏视频不显示全屏按钮（之前也是这样） | 符合用户预期，竖屏视频不需要全屏 |
| TitleBar gone()/visible() 全屏切换可能有闪烁 | 可通过动画或 postDelayed 缓解，实际效果需真机验证 |
| 移除"横屏视频一直显示全屏按钮"后，全屏态下全屏按钮也会3秒后隐藏 | 用户明确要求"随右侧功能区整体隐藏或展示"，单击可重新显示 |

### Prior Art

- 项目其他 Activity（如 ReadBookActivity）使用 TitleBar 的 attachToActivity 机制，未报告返回按钮问题
- GSY VideoPlayer 库的 startWindowFullscreen 是旧模式的全屏方案（已弃用）

## Requirements

### REQ-1: 返回按钮修复（B1）

- **REQ-1.1**: 点击左上角返回箭头必须能退出播放器（非全屏态 finish()，全屏态先退出全屏再 finish()）
- **REQ-1.2**: 使用 `setNavigationOnClickListener` 直接绑定点击事件
- **REQ-1.3**: 加临时日志验证点击事件触发（Tag=VideoBack），验证通过后移除

### REQ-2: 全屏按钮迁移（U1）

- **REQ-2.1**: `btn_fullscreen` 从 fragment_video.xml 底部居中移到 `right_buttons` 容器内
- **REQ-2.2**: 全屏按钮随 `right_buttons` 整体显隐（3秒自动隐藏 + 单击重新显示）
- **REQ-2.3**: 移除 `updateFullscreenButtonVisibility()` 中"横屏视频一直显示全屏按钮"的特殊逻辑
- **REQ-2.4**: 全屏按钮图标仍根据全屏状态切换（ic_fullscreen / ic_fullscreen_exit）

### REQ-3: 真全屏（F1）

- **REQ-3.1**: 全屏时 TitleBar 使用 `gone()` 释放布局空间（替代 `supportActionBar?.hide()`）
- **REQ-3.2**: 全屏时 playerView 铺满整个屏幕（含原 TitleBar 区域）
- **REQ-3.3**: 全屏时状态栏和导航栏完全隐藏（toggleSystemBar 已实现）
- **REQ-3.4**: 退出全屏时 TitleBar 恢复显示（`visible()` + `supportActionBar?.show()`）
- **REQ-3.5**: 加临时日志验证全屏切换时 TitleBar 的 visibility 变化（Tag=VideoFS），验证通过后移除

## Scenarios

### Scenario 1: 返回按钮退出（非全屏）

```
用户从订阅源文章列表进入视频播放器
→ 视频开始播放（竖屏常态）
→ 用户点击左上角返回箭头
→ 播放器退出，返回文章列表
```

### Scenario 2: 返回按钮退出（全屏态）

```
用户在播放器中点击全屏按钮
→ 进入横屏全屏
→ 用户点击返回（系统返回键或全屏退出按钮）
→ 先退出全屏恢复竖屏
→ 再次点击返回
→ 退出播放器
```

### Scenario 3: 全屏按钮随功能区显隐

```
用户播放横屏视频
→ 右侧功能区显示（含全屏按钮）
→ 3秒后右侧功能区自动隐藏（全屏按钮一起隐藏）
→ 用户单击屏幕
→ 右侧功能区重新显示（含全屏按钮）
→ 用户点击全屏按钮
→ 进入全屏
```

### Scenario 4: 真全屏

```
用户点击全屏按钮
→ Activity 旋转横屏
→ TitleBar gone() 释放空间
→ 状态栏/导航栏隐藏
→ playerView 铺满整个屏幕
→ 用户看到视频占据全部屏幕区域，无黑边/无 TitleBar 残留
```
