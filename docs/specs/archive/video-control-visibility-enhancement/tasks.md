# Tasks: 视频播放器控件显隐与缓冲条优化

## F1: 缓冲进度条修复

- [x] 1.1 创建 `app/src/main/res/drawable/progress_buffer_color.xml` layer-list（background/secondaryProgress/progress 三层颜色）
- [x] 1.2 修改 `video_layout_controller.xml`：`bottom_progressbar` 高度 1.5dp→3dp，添加 `android:progressDrawable="@drawable/progress_buffer_color"`
- [x] 1.3 修改 `video_layout_controller_full.xml`：同上
- [x] 1.4 修改 `video_layout_floating.xml`：同上
- [x] 1.5 在 VideoFragment 中获取 `bottom_progressbar` 控件引用
- [x] 1.6 在进度监听器中调用 `getBufferedPercentage()` 更新 `secondaryProgress`
- [x] 1.7 编译验证 + L2 真机验证缓冲进度条可见

## F2: 控件显隐交互变更

- [x] 2.1 在 VideoFragment 添加 `autoHideHandler` + `autoHideRunnable` 成员变量
- [x] 2.2 添加 `scheduleAutoHide(delay: Long = 3000L)` 方法
- [x] 2.3 添加 `cancelAutoHide()` 方法
- [x] 2.4 修改 `onSingleTapConfirmed`：PURE→NORMAL 添加 `scheduleAutoHide()`，NORMAL→PURE 添加 `cancelAutoHide()`，FULLSCREEN 添加自动隐藏逻辑
- [x] 2.5 修改 `activatePlayer` 的 `onPrepared` 回调：添加 `scheduleAutoHide()` 启动自动隐藏
- [x] 2.6 修改 `handlePlayerTouchEvent` 双指滑动：添加 `cancelAutoHide()`
- [x] 2.7 修改 `onDestroyView`：添加 `cancelAutoHide()` 清理 Handler
- [x] 2.8 编译验证 + L2 真机验证控件显隐交互

## 验证

- [x] 3.1 编译 BUILD SUCCESSFUL 无错误无警告
- [x] 3.2 L1 验证：App 启动无崩溃
- [x] 3.3 L2 验证：使用 `ai_tests/scripts/l2_verify_video_player.py` 验证控件显隐场景
- [x] 3.4 L2 验证：缓冲进度条可见且持续更新
- [x] 3.5 updateLog.md 追加变更说明

## AOAdapt 日志

### F2 触摸事件不到达根因分析（2026-07-11）

**现象**：F2 实施后，点击视频画面 OnTouchListener 根本不触发，SwipeTest 入口日志完全不出现。

**排查过程**：
1. 读取 `fragment_video.xml` 确认 `controlsLayer` 的 `clickable=false`（排除 controlsLayer 拦截）
2. 读取 `VideoPlayer.kt` 发现 GSY 内部有独立的 `gestureDetector`（onSingleTapConfirmed 调用 onClickUiToggle，onLongPress 设置倍速）
3. 读取 `video_layout_controller.xml` 发现 `surface_container`（RelativeLayout，match_parent）是全屏视图
4. 反编译 GSY AAR（`gsyvideoplayer-java-11.3.0.aar`）的 `GSYVideoControlView.class` 字节码

**根因**：
- GSY 的 `GSYVideoControlView`（VideoPlayer 的祖父类）实现了 `View.OnTouchListener` 接口
- 在 `init()` 方法中（字节码 L617-626）对 `mTextureViewContainer`（即 `R.id.surface_container`，全屏 RelativeLayout）同时调用 `setOnClickListener(this)` 和 `setOnTouchListener(this)`
- `surface_container` 是 `playerView` 的子 View，`clickable=true` 且有 GSY 的 OnTouchListener，直接消费所有触摸事件
- 因此 `playerView` 的 OnTouchListener **永远不触发**

**修复方案**：
- 将 OnTouchListener 从 `_playerView` 改设到 `_playerView?.findViewById(R.id.surface_container)`（GSY 实际接收触摸的视图）
- 替换 GSY 的 OnTouchListener，由我们统一处理手势（单击切换+双指缩放+双指滑动+文章切换）
- 始终返回 `true` 消费事件，阻止 GSY 的 `onClick`（onClickBlank 回调）和 `surface_container.onTouchEvent` 触发
- 同步修改 `initGestureDetector`（L820）和 `reRegisterTouchListener`（L1052）两处

**副作用评估（可接受）**：
- GSY 的 `onTouch` 不再被调用，因此 GSY 内部 `gestureDetector`（long-press 倍速、double-tap seek、亮度/音量/进度滑动）被禁用
- R3 抖音风格设计不需要这些 GSY 传统手势，可接受
- `controlsLayer` 的按钮（ImageButton，clickable=true）仍在 `surface_container` 之上，正常接收触摸

**验证结果**：
- 编译通过 + L1 启动无崩溃
- L2 真机验证：单次点击 PURE→NORMAL→3秒后 autoHide→PURE ✅
- L2 真机验证：连续三次点击（PURE→NORMAL→schedule, NORMAL→PURE→cancel, PURE→NORMAL→schedule→autoHide）✅
- L2 真机验证：F1 缓冲进度更新同时正常工作 ✅

### F1 缓冲进度条验证（2026-07-11）

- L2 真机验证：缓冲进度从 7% 持续增长到 59%，`secondaryProgress` 正常更新 ✅
- 根因：GSY 框架只更新 `progress`（播放进度），不更新 `secondaryProgress`（缓冲进度），需手动调用 `VideoPlay.videoManager.bufferedPercentage` 更新
