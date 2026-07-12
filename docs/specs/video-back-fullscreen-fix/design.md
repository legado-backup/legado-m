# design.md — 视频播放器返回按钮修复 + 全屏按钮迁移 + 真全屏优化

## Technical Approach

### B1 返回按钮修复

**根因分析**：

activity_video_player.xml 有两个 TitleBar：
- `title_bar`（legacyContainer 内，L36-39）
- `title_bar_new`（viewPagerContainer 内，L16-19）

TitleBar.kt L271-278 `attachToActivity()` 在 `onAttachedToWindow()` 时自动调用 `setSupportActionBar(toolbar)`。

时序冲突：
1. onCreate → setContentView → legacyContainer 默认可见 → `title_bar` attached → `attachToActivity()` → `setSupportActionBar(title_bar.toolbar)`
2. `switchToViewPagerMode()` → `legacyContainer.gone()` + `viewPagerContainer.visible()` → `title_bar_new` attached → `attachToActivity()` → `setSupportActionBar(title_bar_new.toolbar)`
3. `switchToViewPagerMode()` 继续 → `setSupportActionBar(binding.titleBarNew.toolbar)` [重复]

两个 TitleBar 都调用了 `setSupportActionBar`，且 `title_bar` 虽然 `legacyContainer.gone()` 但仍 attached（visibility=gone 不触发 detach）。可能导致 ActionBar 引用混乱，`onSupportNavigateUp()` 未被正确触发。

**修复方案**：

在 `switchToViewPagerMode()` 中，`setSupportActionBar` 之后直接调用 `setNavigationOnClickListener`：

```kotlin
setSupportActionBar(binding.titleBarNew.toolbar)
supportActionBar?.setDisplayHomeAsUpEnabled(true)
supportActionBar?.setDisplayShowTitleEnabled(false)
// B1 修复：直接绑定返回按钮点击事件，绕过 onSupportNavigateUp 机制
binding.titleBarNew.setNavigationOnClickListener {
    Log.d("VideoBack", "NavigationOnClickListener triggered")
    onBackPressedDispatcher.onBackPressed()
}
```

### U1 全屏按钮迁移

**布局变更**（fragment_video.xml）：

将 `btn_fullscreen` 从独立位置（L127-141，底部居中）移到 `right_buttons` 容器内（L145-207）：

```xml
<!-- right_buttons 内新增全屏按钮（放在快退按钮之前，作为第一个） -->
<ImageButton
    android:id="@+id/btn_fullscreen"
    android:layout_width="48dp"
    android:layout_height="48dp"
    android:layout_marginBottom="16dp"
    android:background="@drawable/bg_overlay_button"
    android:contentDescription="全屏"
    android:src="@drawable/ic_fullscreen"
    android:scaleType="centerInside"
    android:padding="12dp"
    android:tint="#FFFFFF" />
```

移除原独立位置的 `btn_fullscreen`（L125-141）。

**代码变更**（VideoFragment.kt）：

- `getOverlayControls()` 已包含 `rightButtons`，`btn_fullscreen` 作为其子控件自动随整体显隐
- `updateFullscreenButtonVisibility()`：移除"横屏视频一直显示"逻辑，改为仅根据视频宽高比决定是否在 rightButtons 内显示全屏按钮（竖屏视频隐藏，横屏视频显示）
- `applyState(FULLSCREEN)` 中移除 `btnFullscreen?.visible()` 的特殊处理（随 rightButtons 整体显隐）

### F1 真全屏

**伪全屏问题**：

`toggleFullScreen()` L816 `supportActionBar?.hide()` 只隐藏 ActionBar 的内容显示，但 TitleBar（AppBarLayout）作为 viewPagerContainer（LinearLayout）的子控件，仍然占据布局空间。ViewPager2 高度 = 屏幕高度 - TitleBar高度，playerView 无法铺满整个屏幕。

**修复方案**：

```kotlin
internal fun toggleFullScreen() {
    isFullScreen = !isFullScreen
    toggleSystemBar(!isFullScreen)
    if (isFullScreen) {
        if (useViewPagerMode) {
            requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
            binding.titleBarNew.gone()  // F1: gone() 释放布局空间（替代 supportActionBar?.hide()）
            currentFragment?.onFullScreenChanged(true)
        }
    } else {
        if (useViewPagerMode) {
            requestedOrientation = orientation
            binding.titleBarNew.visible()  // F1: 恢复 TitleBar
            supportActionBar?.show()
            currentFragment?.onFullScreenChanged(false)
        }
    }
}
```

## Architecture Decisions

### AD-01: 返回按钮用 setNavigationOnClickListener 替代 onSupportNavigateUp

- **Context**: activity_video_player.xml 有两个 TitleBar，attachToActivity() 时序冲突导致 onSupportNavigateUp 可能未被触发
- **Concern**: onSupportNavigateUp 依赖 setSupportActionBar → ActionBar → navigateUp 完整链路，中间任一环节断裂都导致不生效
- **Decision**: 在 switchToViewPagerMode() 中直接调用 binding.titleBarNew.setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
- **Goal**: 返回按钮点击 100% 可靠退出播放器
- **Tradeoff**: 绕过 ActionBar 机制，与项目其他 Activity 风格不一致，但 VideoPlayerActivity 是特殊场景，可靠性优先
- **Status**: Proposed

### AD-02: 全屏按钮移入 right_buttons 容器

- **Context**: 用户要求全屏按钮从底部居中移到右侧功能区，随整体隐藏/展示
- **Concern**: 当前 btn_fullscreen 独立于 right_buttons，有自己的显隐逻辑（横屏视频一直显示），与"随整体显隐"需求冲突
- **Decision**: 将 btn_fullscreen 移到 right_buttons LinearLayout 内作为第一个按钮，移除独立显隐逻辑
- **Goal**: 全屏按钮随右侧功能区整体显隐
- **Tradeoff**: 全屏态下全屏按钮也会3秒后隐藏（之前一直显示），但用户明确要求随整体显隐，单击可重新显示
- **Status**: Proposed

### AD-03: 全屏时 TitleBar 用 gone() 替代 ActionBar hide()

- **Context**: 当前 supportActionBar?.hide() 只隐藏 ActionBar 内容，TitleBar 仍占布局空间，playerView 无法铺满屏幕
- **Concern**: 伪全屏导致屏幕顶部有 TitleBar 高度的空白区域
- **Decision**: 全屏时 binding.titleBarNew.gone() 释放布局空间，退出全屏时 binding.titleBarNew.visible()
- **Goal**: playerView 铺满整个屏幕，实现真全屏
- **Tradeoff**: gone()/visible() 切换可能有闪烁，需真机验证；如闪烁明显可加动画缓解
- **Status**: Proposed

## Data Flow

### 返回按钮点击流程（修复后）

```
用户点击返回箭头
→ Toolbar.setNavigationOnClickListener 触发
→ onBackPressedDispatcher.onBackPressed()
→ onBackPressedDispatcher callback
→ if (isFullScreen) toggleFullScreen() else finish()
→ finish() → 订阅源模式清理状态 → super.finish()
```

### 全屏切换流程（修复后）

```
用户点击全屏按钮 / 双指拉伸
→ VideoPlayerActivity.toggleFullScreen()
→ isFullScreen = true
→ toggleSystemBar(false) 隐藏系统栏
→ binding.titleBarNew.gone() 释放布局空间
→ requestedOrientation = SENSOR_LANDSCAPE 旋转横屏
→ currentFragment.onFullScreenChanged(true)
→ VideoFragment 更新全屏态 + 控件显隐
→ playerView 铺满整个屏幕
```

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 修改 | B1: switchToViewPagerMode 加 setNavigationOnClickListener；F1: toggleFullScreen 改用 gone()/visible() |
| `app/src/main/res/layout/fragment_video.xml` | 修改 | U1: btn_fullscreen 从独立位置移到 right_buttons 内 |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | 修改 | U1: 移除 btn_fullscreen 独立显隐逻辑，updateFullscreenButtonVisibility 简化 |
| `app/src/main/assets/updateLog.md` | 修改 | 追加变更说明 |

## 验证策略

1. **临时日志验证**（P0 规则23）：
   - B1: Log.d("VideoBack", ...) 验证 setNavigationOnClickListener 触发
   - F1: Log.d("VideoFS", ...) 验证 TitleBar gone()/visible() 切换
   - 验证通过后移除临时日志

2. **L2 真机验证**：
   - 验证返回按钮点击能退出播放器
   - 验证全屏按钮在右侧功能区，随整体显隐
   - 验证全屏时 playerView 铺满整个屏幕
   - 使用 ai_tests/scripts/ 脚本辅助验证
