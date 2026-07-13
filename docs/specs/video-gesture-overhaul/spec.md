# spec.md — 视频播放器手势交互重构

## Intent

修复订阅源内置视频播放器长按加速播放功能丢失的Bug，同时按用户需求重构手势交互：去掉快退/快进按钮改为左右滑动、长按倍速、倍率可配置。从整体评估所有手势交互，确保不出现"改了A破坏B"的回归。

## Scope

### In Scope

1. **修复长按加速**：长按屏幕任意位置 → 倍速播放（倍率由 `VideoPlay.longPressSpeed` 配置），松手恢复原速
2. **去掉快退/快进按钮**：移除 `btn_rewind` 和 `btn_forward`，改为左右滑动手势
3. **左右滑动快退快进**：基于滑动距离的连续seek（非固定60秒），与常规视频播放器一致
4. **长按左侧/右侧倍速播放**：长按屏幕左半或右半区域触发倍速
5. **倍率设置**：长按倍速倍率在功能区设置弹窗中可修改（已有功能保留）
6. **双击暂停/播放**：附带修复GSY onDoubleTap失效问题

### Out of Scope

- 竖屏/横屏全屏切换逻辑（保持现有双指缩放触发全屏）
- **上下滑动切换视频/文章功能（完全保留不变）**：现有 handleArticleModeTouchEvent 中的垂直滑动→ViewPager2 拦截切换文章逻辑保持原样，仅新增水平滑动 seek 分支，两者通过方向判定锁定互不干扰
- WebView降级播放模式的手势（WebView内部自行处理）
- 亮度/音量手势调节（GSY原有左半屏亮度/右半屏音量已被替换，本次不恢复）
- VideoPlayService悬浮窗的手势（独立组件，不影响）

## Approach

### Selected Approach

**统一手势管理**：在 VideoFragment 的 GestureDetector 中统一实现所有手势（onSingleTapConfirmed + onLongPress + onDoubleTap），辅以手动检测（左右滑动seek + 垂直滑动切文章 + 双指缩放全屏），不再依赖 GSY 内部手势。

理由：
- VideoFragment 已接管 `surface_container` 的 OnTouchListener，GSY 内部手势（onLongPress/onDoubleTap）永远收不到事件
- 在 VideoFragment 统一管理可确保所有手势不冲突，单一职责
- 可复用 VideoPlayer.kt 中已有的 `setVideoSpeed()` / `showOverlayTip()` / `playSpeed` 等方法

### Alternatives Considered

| 替代方案 | 描述 | 否决理由 |
|---------|------|---------|
| 恢复GSY内部手势+在GSY内添加自定义手势 | 把OnTouchListener还给GSY，在VideoPlayer.kt中实现所有手势 | GSY内部手势与VideoFragment控件显隐逻辑深度耦合，onClickUiToggle/onLongPress分散在两处难以维护；且VideoFragment的控件显隐（PURE/NORMAL/FULLSCREEN三态）需要GestureDetector回调，无法完全交给GSY |
| 桥接手势事件（VideoFragment转发给GSY） | VideoFragment收到事件后同时调用自己的GestureDetector和GSY的gestureDetector | 复杂度高，事件消费逻辑容易冲突（返回true/false的时机），且GSY内部还有亮度/音量/进度条手势会干扰 |
| 使用第三方手势库（如ScrollGesture） | 引入手势库统一管理 | 违反极简工程主义，增加依赖，且Android原生GestureDetector已足够 |

### Drawbacks

| 缺点 | 接受理由 |
|------|---------|
| 需迁移GSY内部的onLongPress/onDoubleTap逻辑到VideoFragment | 一次性迁移，后续维护更简单 |
| GSY原有亮度/音量手势不再生效 | 文章模式下已被替换，非文章模式下用户未要求恢复；可通过按钮设置音量 |
| onSingleTapConfirmed需等待长按超时（~300ms）确认 | 用户无感知，且避免误触发 |

### Prior Art

- 哔哩哔哩/腾讯视频/爱奇艺等主流播放器：单击显隐控件 + 双击暂停 + 长按倍速 + 左右滑动seek
- GSYVideoPlayer原始手势体系：onSingleTapConfirmed(onClickUiToggle) + onDoubleTap(touchDoubleUp) + onLongPress(倍速)

## Requirements

### R1: 长按加速播放（Bug修复）
- 长按屏幕任意位置（左半屏或右半屏）→ 设置播放倍速为 `VideoPlay.longPressSpeed / 10.0f`
- 显示Overlay提示 "${speed}倍速播放中"
- 松手（ACTION_UP）→ 恢复原速 `playSpeed` + 隐藏提示
- 仅在播放状态（CURRENT_STATE_PLAYING）下触发
- **约束**：不能影响单击切换控件显隐（GestureDetector自动区分onLongPress和onSingleTapConfirmed）

### R2: 左右滑动快退快进（新功能）
- 单指水平滑动 → 快退/快进
- seek量 = `(滑动距离 / 屏幕宽度) × 视频总时长`（常规视频播放器方式）
- 左滑（dx < 0）→ 快退，右滑（dx > 0）→ 快进
- 滑动过程中实时显示 seek 预览（当前位置 + 偏移量）
- 松手后执行 seek
- **约束**：与垂直滑动（文章切换）不冲突，通过判断 |dx| vs |dy| 方向区分
- **约束**：与长按不冲突，长按是按住不动，左右滑动是移动

### R3: 去掉快退/快进按钮
- 从 fragment_video.xml 移除 `btn_rewind` 和 `btn_forward`
- 从 VideoFragment.kt 移除 `btnRewind`/`btnForward` 变量、`initSkipButtons()` 方法、`skipVideo()` 方法
- 保留 `VideoPlay.videoSkipTime` 配置（设置面板中可能仍有引用，不删除配置项）

### R4: 双击暂停/播放（附带修复）
- 双击屏幕 → 切换播放/暂停状态
- 复用 GSY 的 `touchDoubleUp` 逻辑或直接调用 `playerView.clickStart`
- **约束**：与onSingleTapConfirmed不冲突（GestureDetector自动区分单击和双击）

### R5: 倍率设置（已有功能保留）
- VideoSettingsPanel.kt L266-280 已有 `longPressSpeed` 设置（NumberPickerDialog，范围5-60，对应0.5x-6.0x）
- 保留不变，确认与R1长按加速联动正确

### R6: 手势不冲突（整体保障）
- 单击 → onSingleTapConfirmed（等待长按超时确认）
- 长按 → onLongPress（GestureDetector默认500ms检测）
- 双击 → onDoubleTap（GestureDetector自动检测）
- 左右滑动 → ACTION_MOVE中检测水平滑动方向
- **垂直滑动（文章模式）→ ACTION_MOVE中检测垂直滑动方向，完全保留现有 handleArticleModeTouchEvent 逻辑**
- 双指缩放 → ScaleGestureDetector
- 双指左右滑动 → ACTION_POINTER_MOVE中检测
- **优先级**：双指 > 长按 > 滑动方向判定 > 双击 > 单击

### R7: 上下滑动切换视频/文章功能完全保留（用户重点关切）
- **现有 handleArticleModeTouchEvent 中的垂直滑动→ViewPager2 切换文章逻辑保持原样不变**
- **方向判定锁定机制**（确保水平seek与垂直切文章互不干扰）：
  1. ACTION_DOWN 记录起点 (startX, startY)
  2. ACTION_MOVE 首次方向判定：计算 dx=event.x-startX, dy=event.y-startY
  3. 如果 |dy| > |dx| 且 |dy| > 30px → 标记 isVerticalSwipe=true（锁定为垂直滑动，交给 ViewPager2）
  4. 如果 |dx| > |dy| 且 |dx| > 30px → 标记 isSeeking=true（锁定为水平滑动，执行 seek）
  5. **方向一旦判定，本次触摸序列内不再改变**（直到 ACTION_UP 重置）
- **非文章模式**（集数模式/单URL）：只有水平滑动 seek，无垂直滑动切换
- **文章模式**：水平滑动 seek 和垂直滑动切文章共存，通过方向判定锁定

## Scenarios

### S1: 单击切换控件显隐
- 前置：视频播放中，控件显示（NORMAL态）
- 操作：单指快速点击屏幕
- 预期：控件隐藏（PURE态），再次单击恢复显示

### S2: 长按倍速播放
- 前置：视频播放中
- 操作：单指按住屏幕不动（>500ms）
- 预期：倍速播放（如3.0x），屏幕显示"3.0倍速播放中"提示
- 操作：松手
- 预期：恢复原速，提示消失

### S3: 左滑快退
- 前置：视频播放中
- 操作：单指向左滑动
- 预期：进度后退，后退量基于滑动距离（滑动半屏≈后退视频时长的50%），显示进度预览
- 操作：松手
- 预期：跳转到预览位置

### S4: 右滑快进
- 前置：视频播放中
- 操作：单指向右滑动
- 预期：进度前进，前进量基于滑动距离，显示进度预览
- 操作：松手
- 预期：跳转到预览位置

### S5: 双击暂停/播放
- 前置：视频播放中
- 操作：双击屏幕
- 预期：暂停播放，再次双击恢复播放

### S6: 垂直滑动切换文章（文章模式）
- 前置：文章模式，多篇文章
- 操作：单指垂直向上/向下滑动
- 预期：切换到上/下一篇文章

### S7: 双指缩放全屏
- 前置：竖屏播放
- 操作：双指向外拉伸（scaleFactor > 1.2）
- 预期：切换到横屏全屏

### S8: 手势不冲突
- 前置：视频播放中
- 操作：快速左右滑动（非长按）
- 预期：触发快退快进，不触发长按倍速
- 操作：长按不动
- 预期：触发倍速播放，不触发左右滑动seek
