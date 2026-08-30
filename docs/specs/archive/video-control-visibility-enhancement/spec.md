# Spec: 视频播放器控件显隐与缓冲条优化

## Intent

用户在真机测试中发现两个问题：
1. **反馈1**：视频播放器缓冲条还是看不见，质疑视频播放是否真正走分片快速缓存
2. **反馈2**：右侧功能区和左下角名称/全屏按钮应改为"刚开始展示→默认过段时间隐藏→点击触发显示"，与 GSY 播放器自带播放条/倍速行为一致

### 排查结论

**分片缓存已生效**（源码验证）：
- `ExoPlayerHelper.kt:L96-L149` — `SimpleCache` + `CacheDataSource` 正确配置，LRU 淘汰策略，容量 50-500MB
- `Exo2MediaPlayer.kt:L114-L128` — Bug7修复后使用 `setMediaItem` 确保 SimpleCache 缓存正常工作
- HLS 分片下载 + SimpleCache 缓存读写均正常工作

**缓冲条看不见根因**：
- `video_layout_controller.xml:L112-L115` — `bottom_progressbar` 高度仅 **1.5dp**，太细看不见
- GSY 框架的 `bottom_progressbar` 只显示播放进度（primary progress），项目中**未调用 `setSecondaryProgress`** 显示缓冲进度
- `ExoPlayerManager.kt:L176-L181` — `getBufferedPercentage()` 正确返回缓冲百分比，但没有被用来更新 UI

**控件显隐当前实现**：
- `VideoFragment.kt:L119` — 注释"移除 autoHideRunnable"，当前无自动隐藏
- `VideoFragment.kt:L680-L697` — `onSingleTapConfirmed`：PURE↔NORMAL 单击切换
- 控件默认显示，单击切换显隐，无自动隐藏逻辑

## Scope

### In Scope

1. **F1: 缓冲进度条修复**
   - 在 VideoFragment 进度监听器中调用 `getBufferedPercentage()` 更新 `bottom_progressbar` 的 `secondaryProgress`
   - 增大 `bottom_progressbar` 高度从 1.5dp 到 3dp
   - 添加缓冲进度颜色（secondaryProgress 颜色）

2. **F2: 控件显隐交互变更**
   - 添加 `autoHideHandler` + `autoHideRunnable` 实现 3 秒自动隐藏
   - 进入播放器时显示控件（NORMAL 状态），3 秒后自动隐藏到 PURE 状态
   - 单击切换显隐：PURE→NORMAL（显示+重启计时），NORMAL→PURE（隐藏+取消计时）
   - 显示控件后重新启动 3 秒自动隐藏定时器
   - 保留双指左右滑动隐藏逻辑（作为快捷隐藏方式）

### Out of Scope

- 修改 GSY 框架内部缓冲进度更新逻辑（只在我们自己的 VideoFragment 中更新）
- 修改 SimpleCache 缓存配置（已验证生效，无需修改）
- 修改双指缩放触发全屏逻辑（保持不变）
- 修改文章模式上下滑动切换文章逻辑（保持不变）

## Approach

### F1: 缓冲进度条修复

**方案**：在 VideoFragment 的进度监听器中手动更新 `bottom_progressbar` 的 `secondaryProgress`

1. 通过 `pv.findViewById<ProgressBar>(R.id.bottom_progressbar)` 获取进度条控件
2. 在进度更新回调中调用 `player.bufferedPercentage` 获取缓冲百分比
3. 调用 `bottomProgressbar.secondaryProgress = bufferedPercentage` 更新缓冲进度
4. 增大高度从 1.5dp 到 3dp，添加缓冲进度颜色

**Alternatives Considered**：
- 方案B：在 fragment_video.xml 中添加独立的缓冲进度条控件 — 更灵活但增加布局复杂度
- 方案C：修改 GSY 框架内部逻辑 — 风险高，影响其他播放器实例

**选择方案A**：复用 GSY 的 `bottom_progressbar`，最小改动，直接绑定 `secondaryProgress`

**Drawbacks**：
- GSY 可能会覆盖我们的 `secondaryProgress` 设置（需验证时序）
- `bottom_progressbar` 是 GSY 内部控件，GSY 升级后可能 ID 变化

### F2: 控件显隐交互变更

**方案**：添加 autoHideHandler + autoHideRunnable 实现 3 秒自动隐藏

1. 添加 `autoHideHandler: Handler` 和 `autoHideRunnable: Runnable`
2. `scheduleAutoHide()` 方法：postDelayed 3 秒后切换到 PURE 状态
3. `cancelAutoHide()` 方法：removeCallbacks
4. 修改 `onSingleTapConfirmed`：
   - PURE → NORMAL：显示控件 + `scheduleAutoHide()`
   - NORMAL → PURE：隐藏控件 + `cancelAutoHide()`
5. 进入播放器时（`activatePlayer` 的 `onPrepared` 回调）：设置 NORMAL 状态 + `scheduleAutoHide()`
6. 保留双指左右滑动隐藏逻辑：触发 PURE + `cancelAutoHide()`

**Alternatives Considered**：
- 方案B：完全移除 PURE 状态，只保留 NORMAL + 自动隐藏 — 简化但失去纯净播放态
- 方案C：使用 GSY 自带的控件显隐机制 — GSY 的显隐机制不适用于自定义悬浮控件

**选择方案A**：保留 PURE/NORMAL 双状态 + 添加自动隐藏定时器，最小改动

**Drawbacks**：
- 自动隐藏可能在用户阅读控件信息时触发（如查看视频标题）— 3 秒应该足够
- Handler 可能导致内存泄漏（需在 onDestroyView 中清理）

## Requirements

### F1: 缓冲进度条修复

- **R1.1**：`bottom_progressbar` 高度从 1.5dp 增大到 3dp
- **R1.2**：`bottom_progressbar` 添加 secondaryProgress 颜色（与播放进度颜色区分）
- **R1.3**：在进度更新回调中调用 `getBufferedPercentage()` 更新 `secondaryProgress`
- **R1.4**：缓冲进度条在播放过程中持续更新（至少每秒一次）

### F2: 控件显隐交互变更

- **R2.1**：进入播放器后控件默认显示（NORMAL 状态）
- **R2.2**：3 秒后自动隐藏控件到 PURE 状态
- **R2.3**：PURE 状态单击 → 显示控件 + 重启 3 秒自动隐藏
- **R2.4**：NORMAL 状态单击 → 隐藏控件 + 取消自动隐藏
- **R2.5**：双指左右滑动 → 隐藏控件 + 取消自动隐藏（保留原逻辑）
- **R2.6**：onDestroyView 中清理 Handler（防止内存泄漏）
- **R2.7**：横屏全屏态（FULLSCREEN）也支持自动隐藏逻辑

## Scenarios

### Scenario 1: 用户进入视频播放器

1. 用户从订阅源文章列表点击文章
2. 视频播放器启动，控件默认显示（右侧功能区 + 左下角名称/全屏按钮）
3. 视频开始播放，缓冲进度条显示缓冲百分比
4. 3 秒后控件自动隐藏，进入纯净播放态
5. 缓冲进度条仍可见（不属于悬浮控件，是 GSY 底部进度条）

### Scenario 2: 用户单击屏幕

1. 控件隐藏状态（PURE）→ 单击 → 控件显示（NORMAL）+ 重启 3 秒计时
2. 3 秒后控件再次自动隐藏
3. 控件显示状态（NORMAL）→ 单击 → 控件隐藏（PURE）+ 取消计时

### Scenario 3: 用户双指左右滑动

1. 控件显示状态（NORMAL）→ 双指左右滑动 → 控件隐藏（PURE）+ 取消计时
2. 与原逻辑一致，作为快捷隐藏方式

### Scenario 4: 用户横屏全屏

1. 双指缩放触发全屏（FULLSCREEN 状态）
2. 控件显示（含全屏按钮）+ 3 秒自动隐藏
3. 单击切换显隐，显示后重启 3 秒计时

### Scenario 5: 用户退出播放器

1. onDestroyView 清理 Handler
2. 无内存泄漏
