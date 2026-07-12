# Spec：GSY 全屏按钮去重

## Intent

移除 GSY 视频播放器控制器布局中内置的右下角全屏按钮（`@+id/fullscreen`），因为项目已有自定义中部全屏按钮（`btn_fullscreen`）实现全屏切换功能，两个按钮功能完全重叠，造成 UI 冗余和用户困惑。

## Scope

### In Scope

- 隐藏 `video_layout_controller.xml` 中的 `@+id/fullscreen` ImageView（竖屏模式控制器布局）

### Out of Scope

- 不修改 `video_layout_controller_full.xml`（全屏模式布局，经确认无 fullscreen 按钮）
- 不修改 `fragment_video.xml` 的自定义 `btn_fullscreen`（已有功能保持不变）
- 不修改 `VideoPlayerActivity.kt` 的 `playerView.fullscreenButton.setOnClickListener` 代码（click listener 设到 gone view 上安全，保持不动避免引入风险）
- 不修改 GSY 基类源码

## Approach

### 选中方案：visibility=gone

在 `video_layout_controller.xml` L102-108 的 fullscreen ImageView 上添加 `android:visibility="gone"` 属性。

### Alternatives Considered

| 方案 | 描述 | 优点 | 缺点 | 决策 |
|------|------|------|------|------|
| A. 删除 ImageView 元素 | 从 XML 中完全删除 fullscreen ImageView | 彻底清除 | GSY 基类 `findViewById(R.id.fullscreen)` 返回 null，可能导致 NPE | ❌ 风险过高 |
| B. visibility=gone | 添加 `android:visibility="gone"` | 安全（view 仍存在，findViewById 正常返回）、最小改动 | view 对象仍占用少量内存 | ✅ 选中 |
| C. 代码动态隐藏 | 在 VideoPlayerActivity 中 `playerView.fullscreenButton.visibility = View.GONE` | 灵活 | 改动多、需确认 GSY 基类 init 时序 | ❌ 过度设计 |

### Drawbacks

1. **GSY 全屏按钮 click listener 仍设置但永不触发**：`VideoPlayerActivity.kt:900` 的 `playerView.fullscreenButton.setOnClickListener { toggleFullScreen() }` 仍会执行，但因 view 不可见，永远不会被点击。这是安全的行为，不影响功能。
2. **全屏模式下无 GSY 退出全屏按钮**：全屏模式布局 `video_layout_controller_full.xml` 本身就没有 fullscreen 按钮，用户通过系统返回键退出全屏（`onBackPressedDispatcher.addCallback` 处理），此行为不变。

## Requirements

### REQ-1：隐藏 GSY 内置全屏按钮

- REQ-1.1：`video_layout_controller.xml` 中的 fullscreen ImageView 添加 `android:visibility="gone"`
- REQ-1.2：编译通过，App 正常启动
- REQ-1.3：进入视频播放器后，GSY 底部控制栏右下角无全屏按钮
- REQ-1.4：自定义中部全屏按钮（btn_fullscreen）功能不受影响

## Scenarios

### Scenario-1：竖屏模式进入全屏

1. 用户从订阅源进入视频播放器（竖屏）
2. 点击屏幕显示控件
3. GSY 底部控制栏右下角**无全屏按钮**（已隐藏）
4. 用户点击自定义中部全屏按钮（btn_fullscreen）
5. 成功进入全屏（横屏）

### Scenario-2：全屏模式退出全屏

1. 用户在全屏模式（横屏）
2. 按系统返回键
3. 成功退出全屏回到竖屏（onBackPressedDispatcher.addCallback 处理）

### Scenario-3：GSY 控件功能不受影响

1. GSY 底部控制栏的其他按钮（播放/暂停、进度条、倍速、静音）功能正常
2. fullscreen 按钮虽隐藏但 GSY 基类 findViewById 正常返回，无 NPE
