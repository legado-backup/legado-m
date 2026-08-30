# design.md — 视频播放器手势交互重构

## Technical Approach

### 整体策略：统一手势管理

在 VideoFragment 的 GestureDetector 中统一实现所有手势，辅以 ACTION_MOVE 手动检测（左右滑动seek + 垂直滑动切文章），不再依赖 GSY 内部手势。

### 手势交互体系（完整盘点）

| 手势 | 触发方式 | 实现位置 | 优先级 |
|------|---------|---------|--------|
| 单击 | 单指快速点击 | GestureDetector.onSingleTapConfirmed | 6（最低） |
| 双击 | 连续两次快速点击 | GestureDetector.onDoubleTap | 5 |
| 长按 | 单指按住不动>500ms | GestureDetector.onLongPress | 4 |
| 左右滑动 | 单指水平移动 | ACTION_MOVE 手动检测 | 3 |
| 垂直滑动(文章模式) | 单指垂直移动 | ACTION_MOVE 手动检测 | 2 |
| 双指缩放 | 双指拉伸 | ScaleGestureDetector | 1（最高） |
| 双指左右滑动 | 双指同方向水平移动 | ACTION_POINTER_MOVE 手动检测 | 1 |

### 1. 长按加速实现（R1）

```kotlin
// 状态变量
private var isLongPressSpeed = false

// GestureDetector 中添加
override fun onLongPress(e: MotionEvent) {
    val pv = _playerView ?: return
    if (pv.currentState == CURRENT_STATE_PLAYING) {  // 仅播放中触发
        val speed = VideoPlay.longPressSpeed / 10.0f
        pv.setVideoSpeed(speed)
        pv.showOverlayTip("${speed}倍速播放中")
        isLongPressSpeed = true
    }
}

// ACTION_UP 中添加
if (isLongPressSpeed) {
    isLongPressSpeed = false
    _playerView?.setVideoSpeed(_playerView?.playSpeed ?: 1.0f)
    _playerView?.showOverlayTip()  // 隐藏提示
}
```

**关键约束**：
- `setVideoSpeed` / `showOverlayTip` / `playSpeed` 需要对 VideoFragment 可见（VideoPlayer.kt 中需改为 internal 或添加 public 方法）
- GestureDetector 自动区分 onLongPress 和 onSingleTapConfirmed：用户按住不动500ms触发 onLongPress，快速点击触发 onSingleTapConfirmed

### 2. 左右滑动快退快进实现（R2）

```kotlin
// 状态变量
private var slideSeekStartX = 0f
private var isSeeking = false
private var seekTarget = 0L

// ACTION_DOWN 中记录起点
MotionEvent.ACTION_DOWN -> {
    slideSeekStartX = event.x
    isSeeking = false
}

// ACTION_MOVE 中检测水平滑动
MotionEvent.ACTION_MOVE -> {
    if (event.pointerCount == 1 && !isLongPressSpeed) {
        val dx = event.x - slideSeekStartX
        val dy = event.y - singleFingerStartY
        // 首次判定方向：水平滑动优先（非文章模式），或水平滑动且非垂直（文章模式）
        if (!isSeeking && kotlin.math.abs(dx) > 30f && kotlin.math.abs(dx) > kotlin.math.abs(dy)) {
            isSeeking = true
        }
        if (isSeeking) {
            val pv = _playerView ?: return
            val screenWidth = resources.displayMetrics.widthPixels
            val duration = VideoPlay.videoManager.duration
            if (duration > 0) {
                val ratio = dx / screenWidth  // -1.0 ~ 1.0
                val offset = (ratio * duration).toLong()
                seekTarget = (VideoPlay.videoManager.currentPosition + offset)
                    .coerceIn(0, duration)
                // 显示预览（每200ms更新一次，避免频繁刷新）
                val targetSec = seekTarget / 1000
                pv.showOverlayTip("→ ${formatTime(targetSec)}")
            }
        }
    }
}

// ACTION_UP 中执行 seek
if (isSeeking) {
    _playerView?.currentPlayer?.seekTo(seekTarget)
    isSeeking = false
    _playerView?.showOverlayTip()  // 隐藏提示
}
```

**关键约束**：
- 文章模式和非文章模式都需要实现
- 水平滑动判定阈值30px（避免误触发）
- seek量 = (dx / screenWidth) × duration（滑动全屏≈跳转视频总时长）
- 显示预览使用 showOverlayTip（复用现有方法）

### 3. 双击暂停/播放实现（R4）

```kotlin
// GestureDetector 中添加
override fun onDoubleTap(e: MotionEvent): Boolean {
    _playerView?.let { pv ->
        // 复用 GSY 的 clickStart 逻辑（切换播放/暂停）
        if (pv.currentState == CURRENT_STATE_PLAYING) {
            pv.onVideoPause()
        } else if (pv.currentState == CURRENT_STATE_PAUSE) {
            pv.startAfterPrepared()
        }
    }
    return true
}
```

### 4. 去掉快退/快进按钮（R3）

**fragment_video.xml**：移除 btn_rewind（L176-186）和 btn_forward（L214-224）

**VideoFragment.kt**：
- 移除变量声明：`btnRewind`（L104）、`btnForward`（L107）
- 移除初始化：`btnRewind = view.findViewById(...)`（L650）、`btnForward = view.findViewById(...)`（L653）
- 移除清理：`btnRewind = null`（L200）、`btnForward = null`（L203）
- 移除方法调用：`initSkipButtons()`（L679）
- 移除方法定义：`initSkipButtons()`（L840-847）、`skipVideo()`（L852-863）

## Architecture Decisions

### AD-01: 手势统一在 VideoFragment 中实现
- **Context**: VideoFragment 已接管 surface_container 的 OnTouchListener，GSY 内部手势永远收不到事件
- **Concern**: 长按加速和双击暂停功能丢失，需要在某处重新实现
- **Decision**: 在 VideoFragment 的 GestureDetector 中统一实现 onLongPress 和 onDoubleTap
- **Goal**: 所有手势集中管理，避免分散在 VideoFragment 和 VideoPlayer 两处
- **Tradeoff**: 需迁移 GSY 内部逻辑，但一次性迁移后维护更简单
- **Status**: Accepted

### AD-02: 左右滑动 seek 基于"滑动距离/屏幕宽度×视频总时长"
- **Context**: 用户要求"跟常规视频播放器一样"，非固定60秒
- **Concern**: 如何计算 seek 量
- **Decision**: seek量 = (dx / screenWidth) × duration
- **Goal**: 滑动全屏宽度≈跳转整个视频时长，与主流播放器一致
- **Tradeoff**: 长视频时滑动精度降低，但符合用户习惯
- **Status**: Accepted

### AD-03: 长按倍速通过 GestureDetector.onLongPress + ACTION_UP 配合
- **Context**: onLongPress 触发倍速，但松手恢复需要在 ACTION_UP 中处理
- **Concern**: GestureDetector 的 onLongPress 没有"松手"回调
- **Decision**: onLongPress 中设置 isLongPressSpeed=true + 倍速，ACTION_UP 中检查 isLongPressSpeed 恢复原速
- **Goal**: 完整的长按倍速体验（按下倍速→松手恢复）
- **Tradeoff**: 需手动管理 isLongPressSpeed 状态，但逻辑清晰
- **Status**: Accepted

### AD-04: 去掉快退快进按钮但保留 videoSkipTime 配置
- **Context**: 用户要求去掉按钮改为手势，但 VideoSettingsPanel 中有 videoSkipTime 设置项
- **Concern**: 是否同时移除 videoSkipTime 配置
- **Decision**: 保留 videoSkipTime 配置项（设置面板中不删除），仅移除按钮
- **Goal**: 避免破坏设置面板布局，配置项后续可复用
- **Tradeoff**: 配置项暂时无UI使用，但不影响功能
- **Status**: Accepted

### AD-05: 上下滑动切换视频/文章功能完全保留（用户重点关切）
- **Context**: 用户明确要求"别改完你上面，视频上下滑动切换的功能不好使了"，担心新增手势破坏现有上下滑动切换
- **Concern**: 新增左右滑动 seek 与现有上下滑动切文章可能冲突
- **Decision**: 现有 handleArticleModeTouchEvent 中的垂直滑动→ViewPager2 切换文章逻辑保持原样不变；新增水平滑动 seek 通过方向判定锁定机制与垂直滑动互不干扰
- **Goal**: 上下滑动切换视频/文章功能100%不受影响
- **Tradeoff**: 方向判定需等待首次 ACTION_MOVE 确定方向（约16ms），用户无感知
- **Status**: Accepted

## Data Flow

### 触摸事件流

```
用户触摸屏幕
  ↓
surface_container.setOnTouchListener (VideoFragment L922)
  ↓
isTouchOnControls(x, y)?
  ├─ yes → return false（让按钮处理）
  └─ no → 判断模式
      ├─ 文章模式 → handleArticleModeTouchEvent(event)
      └─ 非文章模式 → handlePlayerTouchEvent(event)
          ↓
          gestureDetector.onTouchEvent(event)
          ├─ onSingleTapConfirmed → 切换控件显隐
          ├─ onLongPress → 倍速播放 (isLongPressSpeed=true)
          └─ onDoubleTap → 暂停/播放切换
          ↓
          scaleGestureDetector.onTouchEvent(event)
          └─ onScaleEnd → 双指缩放触发全屏
          ↓
          ACTION_MOVE 手动检测（方向判定锁定机制）
          ├─ pointerCount>=2 → 双指左右滑动检测
          └─ pointerCount==1
              ├─ 已锁定垂直(isVerticalSwipe) → 交给 ViewPager2 切文章（保持原逻辑）
              ├─ 已锁定水平(isSeeking) → 持续 seek 预览
              └─ 未锁定 → 首次方向判定：
                  ├─ |dy|>|dx| 且 |dy|>30 (文章模式) → 锁定 isVerticalSwipe，交 ViewPager2
                  └─ |dx|>|dy| 且 |dx|>30 → 锁定 isSeeking，开始 seek 预览
          ↓
          ACTION_UP 处理（重置所有锁定标志）
          ├─ isLongPressSpeed → 恢复原速
          ├─ isSeeking → 执行 seek
          ├─ isVerticalSwipe → 无需处理（ViewPager2 已接管）
          └─ 否则 → GestureDetector 触发 onSingleTapConfirmed
          ↓
          return true（始终消费事件）
```

**方向锁定机制关键点**：
- 方向一旦判定（isVerticalSwipe 或 isSeeking），本次触摸序列内不再改变
- 只有 ACTION_UP 才重置锁定标志
- 这确保了上下滑动切文章和左右滑动 seek 互不干扰

## File Changes

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| fragment_video.xml | 删除 | 移除 btn_rewind（L176-186）和 btn_forward（L214-224） |
| VideoFragment.kt | 修改+删除 | 删除按钮相关代码；添加 onLongPress/onDoubleTap/左右滑动seek逻辑 |
| VideoPlayer.kt | 修改 | setVideoSpeed/showOverlayTip/playSpeed 改为 internal 供 VideoFragment 访问 |
| VideoSettingsPanel.kt | 不变 | longPressSpeed 设置保留 |
| updateLog.md | 新增 | 添加用户可感知的变更说明 |
