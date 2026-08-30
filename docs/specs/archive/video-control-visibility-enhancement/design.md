# Design: 视频播放器控件显隐与缓冲条优化

## Technical Approach

### F1: 缓冲进度条修复

**当前问题**：
- `bottom_progressbar` 高度仅 1.5dp，太细看不见
- GSY 框架只更新 `progress`（播放进度），未更新 `secondaryProgress`（缓冲进度）
- `ExoPlayerManager.getBufferedPercentage()` 返回正确的缓冲百分比，但没有被用来更新 UI

**修复方案**：

1. **增大高度**：`video_layout_controller.xml` / `video_layout_controller_full.xml` / `video_layout_floating.xml` 中 `bottom_progressbar` 高度从 1.5dp 到 3dp

2. **添加缓冲进度颜色**：创建 `progress_buffer_color.xml` layer-list drawable，包含：
   - background：半透明黑
   - secondaryProgress：半透明白/灰（缓冲进度）
   - progress：主题色（播放进度）

3. **更新 secondaryProgress**：在 VideoFragment 的进度监听器中调用 `getBufferedPercentage()` 更新 `secondaryProgress`

**进度监听器位置**：
- VideoFragment 中已有进度监听逻辑（`startProgressMonitor` / `stopProgressMonitor`）
- 在进度更新回调中添加缓冲进度更新

### F2: 控件显隐交互变更

**当前实现**：
```kotlin
// VideoFragment.kt:L119
// 设计文档：控件显隐由单击切换，无自动隐藏逻辑（移除 autoHideRunnable）

// VideoFragment.kt:L680-L697 onSingleTapConfirmed
when (currentState) {
    PlayState.PURE -> switchState(PlayState.NORMAL)
    PlayState.NORMAL -> switchState(PlayState.PURE)
    PlayState.FULLSCREEN -> { ... }
}
```

**变更后实现**：

1. **添加自动隐藏 Handler**：
```kotlin
private val autoHideHandler = Handler(Looper.getMainLooper())
private val autoHideRunnable = Runnable {
    if (currentState == PlayState.NORMAL) {
        switchState(PlayState.PURE)
    } else if (currentState == PlayState.FULLSCREEN && controlsVisibleInFullscreen) {
        controlsVisibleInFullscreen = false
        hideControlsAnimated()
    }
}
private fun scheduleAutoHide(delay: Long = 3000L) {
    autoHideHandler.removeCallbacks(autoHideRunnable)
    autoHideHandler.postDelayed(autoHideRunnable, delay)
}
private fun cancelAutoHide() {
    autoHideHandler.removeCallbacks(autoHideRunnable)
}
```

2. **修改 onSingleTapConfirmed**：
```kotlin
when (currentState) {
    PlayState.PURE -> {
        switchState(PlayState.NORMAL)
        scheduleAutoHide()  // 显示后3秒自动隐藏
    }
    PlayState.NORMAL -> {
        switchState(PlayState.PURE)
        cancelAutoHide()  // 手动隐藏，取消计时
    }
    PlayState.FULLSCREEN -> {
        controlsVisibleInFullscreen = !controlsVisibleInFullscreen
        if (controlsVisibleInFullscreen) {
            showControlsAnimated()
            btnFullscreen?.visible()
            updateFullscreenButtonIcon(true)
            scheduleAutoHide()  // 显示后3秒自动隐藏
        } else {
            hideControlsAnimated()
            cancelAutoHide()  // 手动隐藏，取消计时
        }
    }
}
```

3. **进入播放器时启动自动隐藏**：
在 `activatePlayer()` 的 `onPrepared` 回调中：
```kotlin
override fun onPrepared(url: String?, vararg objects: Any?) {
    // ... 原有逻辑 ...
    // 进入播放器后显示控件 + 3秒自动隐藏
    if (currentState == PlayState.NORMAL) {
        scheduleAutoHide()
    }
}
```

4. **双指左右滑动隐藏**：
```kotlin
// handlePlayerTouchEvent 中双指左右滑动
if (dx1 > threshold && dx2 > threshold && (dx1 > 0) == (dx2 > 0)) {
    switchState(PlayState.PURE)
    cancelAutoHide()  // 取消自动隐藏计时
    isTwoFingerSwipe = false
}
```

5. **onDestroyView 清理**：
```kotlin
override fun onDestroyView() {
    cancelAutoHide()  // 清理 Handler
    // ... 原有清理逻辑 ...
}
```

## Architecture Decisions

### ADR-1: 缓冲进度条更新方式

**Context**：GSY 框架的 `bottom_progressbar` 只更新播放进度，不更新缓冲进度。需要在 VideoFragment 中手动更新 `secondaryProgress`。

**Decision**：在 VideoFragment 的进度监听器中通过 `pv.findViewById<ProgressBar>(R.id.bottom_progressbar)` 获取控件，调用 `secondaryProgress = player.bufferedPercentage` 更新。

**Consequences**：
- 正面：最小改动，复用 GSY 的 bottom_progressbar
- 负面：GSY 可能覆盖 secondaryProgress 设置（需验证时序）
- 风险：GSY 升级后 bottom_progressbar ID 可能变化

### ADR-2: 自动隐藏定时器实现

**Context**：需要实现 3 秒后自动隐藏控件的定时器。

**Decision**：使用 `Handler(Looper.getMainLooper())` + `postDelayed` + `Runnable`，在 `onDestroyView` 中 `removeCallbacks` 清理。

**Alternatives**：
- 协程 `delay(3000)` + `launch`：更 Kotlin 风格，但需要管理协程作用域
- `Timer` + `TimerTask`：过时方案

**Consequences**：
- 正面：简单可靠，与 GSY 框架风格一致
- 负面：Handler 需要手动清理防止内存泄漏
- 风险：低（在 onDestroyView 中清理即可）

### ADR-3: 自动隐藏延迟时间

**Context**：需要确定自动隐藏的延迟时间。

**Decision**：3 秒（3000ms），与 GSY 播放器自带播放条/倍速行为一致。

**Alternatives**：
- 2 秒：太快，用户来不及查看控件信息
- 5 秒：太慢，控件显示时间过长影响沉浸感

**Consequences**：
- 正面：与 GSY 行为一致，用户已有心智模型
- 负面：无
- 风险：无

## Data Flow

### F1: 缓冲进度更新流程

```
ExoPlayer 缓冲数据
  → Exo2MediaPlayer.bufferedPercentage (属性)
  → ExoPlayerManager.getBufferedPercentage() (方法)
  → VideoFragment 进度监听器调用
  → bottom_progressbar.secondaryProgress = bufferedPercentage
  → UI 显示缓冲进度条
```

### F2: 控件显隐流程

```
进入播放器 onPrepared
  → currentState = NORMAL (显示控件)
  → scheduleAutoHide(3000)
  → 3秒后 autoHideRunnable 触发
  → switchState(PURE) (隐藏控件)

用户单击屏幕
  → onSingleTapConfirmed
  → PURE → NORMAL: 显示控件 + scheduleAutoHide(3000)
  → NORMAL → PURE: 隐藏控件 + cancelAutoHide()

用户双指左右滑动
  → handlePlayerTouchEvent
  → switchState(PURE) + cancelAutoHide()

退出播放器 onDestroyView
  → cancelAutoHide() (清理 Handler)
```

## File Changes

| 文件 | 修改内容 |
|------|---------|
| `app/src/main/res/layout/video_layout_controller.xml` | `bottom_progressbar` 高度 1.5dp→3dp，添加 `progressDrawable` |
| `app/src/main/res/layout/video_layout_controller_full.xml` | 同上 |
| `app/src/main/res/layout/video_layout_floating.xml` | 同上 |
| `app/src/main/res/drawable/progress_buffer_color.xml` | 新建：layer-list 定义缓冲进度颜色 |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | F1: 进度监听器更新 secondaryProgress；F2: 添加 autoHideHandler/scheduleAutoHide/cancelAutoHide，修改 onSingleTapConfirmed，onPrepared 启动自动隐藏，onDestroyView 清理 |

### 详细修改点

#### VideoFragment.kt

1. **新增成员变量**（~L103 附近）：
   - `autoHideHandler: Handler`
   - `autoHideRunnable: Runnable`
   - `bottomProgressbar: ProgressBar?`（F1 用）

2. **新增方法**（~L350 附近）：
   - `scheduleAutoHide(delay: Long = 3000L)`
   - `cancelAutoHide()`

3. **修改 onSingleTapConfirmed**（~L680）：
   - PURE→NORMAL：添加 `scheduleAutoHide()`
   - NORMAL→PURE：添加 `cancelAutoHide()`
   - FULLSCREEN：添加 `scheduleAutoHide()` / `cancelAutoHide()`

4. **修改 activatePlayer 的 onPrepared**（~L175）：
   - 添加 `scheduleAutoHide()` 启动自动隐藏

5. **修改 handlePlayerTouchEvent 双指滑动**（~L770）：
   - 添加 `cancelAutoHide()`

6. **修改 onDestroyView**（~L143）：
   - 添加 `cancelAutoHide()` 清理 Handler

7. **F1: 进度监听器**：
   - 在进度更新回调中添加 `bottomProgressbar?.secondaryProgress = pv.getBufferedPercentage()`
