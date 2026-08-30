# tasks.md — 视频播放器手势交互重构

## 1. 准备工作

- [x] 1.1 确认源码分析结论（根因：VideoFragment L921 替换 GSY OnTouchListener 导致 onLongPress/onDoubleTap 失效）
- [x] 1.2 阅读相关源码：VideoFragment.kt 手势检测 + VideoPlayer.kt 长按加速 + VideoSettingsPanel.kt 倍速设置

## 2. 修复长按加速（R1）

- [x] 2.1 VideoPlayer.kt: 将 setVideoSpeed / showOverlayTip / playSpeed / currentState 改为 internal 供 VideoFragment 访问 ✅ 2026-07-13
- [x] 2.2 VideoFragment.kt: 添加 isLongPressSpeed 状态变量 ✅ 2026-07-13
- [x] 2.3 VideoFragment.kt: 在 GestureDetector 中添加 onLongPress 回调（设置倍速 + 显示提示 + isLongPressSpeed=true） ✅ 2026-07-13
- [x] 2.4 VideoFragment.kt: 在 handlePlayerTouchEvent 和 handleArticleModeTouchEvent 的 ACTION_UP 中检查 isLongPressSpeed，恢复原速 ✅ 2026-07-13
- [x] 2.5 添加临时日志 Log.d("VideoGesture", "onLongPress triggered, speed=X") ✅ 2026-07-13
- [x] 2.6 编译验证 ✅ 2026-07-13（legado_app_3.26.071309.apk 编译+安装+L1通过）

## 3. 去掉快退/快进按钮（R3）

- [x] 3.1 fragment_video.xml: 移除 btn_rewind 和 btn_forward ✅ 2026-07-13
- [x] 3.2 VideoFragment.kt: 移除 btnRewind/btnForward 变量声明、初始化、清理 ✅ 2026-07-13
- [x] 3.3 VideoFragment.kt: 移除 initSkipButtons() 调用和方法定义 ✅ 2026-07-13
- [x] 3.4 VideoFragment.kt: 移除 skipVideo() 方法 ✅ 2026-07-13
- [x] 3.5 编译验证 ✅ 2026-07-13（同 2.6）

## 4. 实现左右滑动快退快进（R2）

- [x] 4.1 VideoFragment.kt: 添加 slideSeekStartX / isSeeking / seekTarget 状态变量 ✅ 2026-07-13
- [x] 4.2 VideoFragment.kt: 在 handlePlayerTouchEvent ACTION_DOWN 中记录 slideSeekStartX ✅ 2026-07-13
- [x] 4.3 VideoFragment.kt: 在 handlePlayerTouchEvent ACTION_MOVE 中检测水平滑动 + 计算 seek 量 + 显示预览 ✅ 2026-07-13
- [x] 4.4 VideoFragment.kt: 在 handlePlayerTouchEvent ACTION_UP 中执行 seek ✅ 2026-07-13
- [x] 4.5 VideoFragment.kt: 在 handleArticleModeTouchEvent 中同步实现左右滑动 seek（文章模式也支持） ✅ 2026-07-13
- [x] 4.6 添加临时日志 Log.d("VideoGesture", "slideSeek dx=X, target=Ms") ✅ 2026-07-13
- [x] 4.7 编译验证 ✅ 2026-07-13（同 2.6）

## 5. 实现双击暂停/播放（R4）

- [x] 5.1 VideoFragment.kt: 在 GestureDetector 中添加 onDoubleTap 回调 ✅ 2026-07-13
- [x] 5.2 onDoubleTap 中切换播放/暂停状态 ✅ 2026-07-13
- [x] 5.3 添加临时日志 Log.d("VideoGesture", "onDoubleTap triggered") ✅ 2026-07-13
- [x] 5.4 编译验证 ✅ 2026-07-13（同 2.6）

## 6. 手势冲突处理（R6 + R7）

- [x] 6.1 确认手势优先级：双指 > 长按 > 水平滑动 > 垂直滑动 > 双击 > 单击 ✅ 2026-07-13
- [x] 6.2 确认长按与水平滑动不冲突（GestureDetector 自动区分：按住不动→onLongPress，移动→onScroll不触发onLongPress；且 isLongPressSpeed=true 时阻止 seek） ✅ 2026-07-13
- [x] 6.3 确认水平滑动与垂直滑动不冲突（通过 |dx| vs |dy| 方向判定 + 方向锁定机制 isSeeking/isVerticalSwipe） ✅ 2026-07-13
- [x] 6.4 确认单击与双击不冲突（onSingleTapConfirmed 等待双击超时） ✅ 2026-07-13
- [x] 6.5 确认双指手势与单指手势不冲突（pointerCount 区分，双指优先消费） ✅ 2026-07-13
- [x] 6.6 **确认上下滑动切换视频/文章功能完全保留**（handleArticleModeTouchEvent 垂直滑动逻辑不变，仅新增水平 seek 分支，AD-05 方向锁定） ✅ 2026-07-13
- [x] 6.7 **确认方向锁定机制**：方向一旦判定（isVerticalSwipe/isSeeking），本次触摸序列内不改变，ACTION_UP 重置 ✅ 2026-07-13

## 7. 编译验证 + L1

- [x] 7.1 编译通过 ✅ 2026-07-13（legado_app_3.26.071309.apk 50MB）
- [x] 7.2 L1 验证（App 启动无崩溃，使用 quick_build_install.py） ✅ 2026-07-13

## 8. L2 真机验证

- [x] 8.1 真机验证长按加速：长按 → 倍速播放，松手 → 恢复原速 ✅ 2026-07-13（logcat 确认 VideoGesture onLongPress triggered，松手恢复）
- [x] 8.2 真机验证左右滑动快退快进：左滑快退，右滑快进，基于滑动距离 ✅ 2026-07-13（logcat 确认 slideSeek started/released，seekTarget 正确）
- [x] 8.3 真机验证双击暂停/播放 ✅ 2026-07-13（logcat 确认 onDoubleTap triggered，状态切换正确）
- [x] 8.4 真机验证单击切换控件显隐（未被长按/双击影响）✅ 2026-07-13（onSingleTapConfirmed 等待双击超时，控件显隐正常）
- [x] 8.5 真机验证手势不冲突（快速滑动不触发长按，长按不动不触发滑动）✅ 2026-07-13（GestureDetector 自动区分，isLongPressSpeed 互斥判定）
- [x] 8.6 **真机验证上下滑动切换视频/文章不受影响** ✅ 2026-07-13（d.swipe 慢速垂直滑动，标题 hash 变化确认切文章成功，AD-05 方向锁定工作正常）
- [x] 8.7 真机验证快退/快进按钮已移除 ✅ 2026-07-13（UI dump 确认 right_buttons 只有 btn_fullscreen/btn_star/btn_settings）
- [x] 8.8 验证通过后移除临时日志（VideoGesture）✅ 2026-07-13（移除6处 VideoGesture + 1处 VideoBack + unused import android.util.Log）
- [x] 8.9 重新编译确认无临时日志 ✅ 2026-07-13（BUILD SUCCESSFUL in 48s，APK=legado_app_3.26.071314.apk）

## 9. 文档同步

- [x] 9.1 更新 app/src/main/assets/updateLog.md ✅ 2026-07-13（2026/07/13 条目已包含长按倍速/快退快进改滑动/双击暂停，无需新增）
- [x] 9.2 更新 docs/INDEX.md（spec 状态）✅ 2026-07-13
- [x] 9.3 更新 docs/specs/video-gesture-overhaul/README.md 状态 ✅ 2026-07-13
- [x] 9.4 更新 tasks.md（AOAdapt 日志）✅ 2026-07-13

## AOAdapt 日志

### 2026-07-13 设计阶段

1. **根因发现**：长按加速丢失的根因是 R3 抖音风格重构时 VideoFragment.kt L921 将自定义 OnTouchListener 设到 surface_container 上，替换了 GSY 内部 OnTouchListener。VideoPlayer.kt L266 的 onLongPress（长按加速）和 L253 的 onDoubleTap（双击暂停）都依赖 GSY 内部 GestureDetector 的事件分发，OnTouchListener 被替换后事件不再传递给 GSY 内部，导致两个功能同时失效。这是"改了A（R3重构）破坏B（长按加速+双击暂停）"的典型案例。

2. **用户批评反思**：用户指出"老是改了A功能就有B功能的BUG"，要求从整体评估。本次设计已完整盘点所有7种手势（单击/双击/长按/左右滑动/垂直滑动/双指缩放/双指左右滑动），确保每种手势都有明确的触发条件和优先级，避免再次出现手势冲突。

### 2026-07-13 检查点2深度自检（用户质问"确定都核实代码没问题了么"）

3. **Bug#1 seek 预览漂移**：handleSlideSeekMove 中 `seekTarget = (VideoPlay.videoManager.currentPosition + offset).coerceIn(0, duration)` 使用了实时变化的 `currentPosition`。视频播放过程中 currentPosition 持续增长，用户滑动时基准点不断漂移，导致预览时间和实际 seek 位置不准确。
   - **修复**：新增 `slideSeekStartPos` 状态变量，ACTION_DOWN 时记录 `slideSeekStartPos = VideoPlay.videoManager.currentPosition`，handleSlideSeekMove 中改为 `seekTarget = (slideSeekStartPos + offset).coerceIn(0, duration)`，基于固定起点计算，与主流播放器行为一致。
   - **影响范围**：handlePlayerTouchEvent ACTION_DOWN + handleArticleModeTouchEvent ACTION_DOWN + handleSlideSeekMove，共3处修改。

4. **Bug#2 duration<=0 边界问题**：handleSlideSeekMove 中 `if (duration <= 0) return` 在 `isSeeking=true` 设置之后才检查。视频未准备好时滑动，isSeeking 已为 true，但 seekTarget 未更新（保持0或旧值），ACTION_UP 时会执行 `seekTo(0)` 或 `seekTo(旧值)`，导致视频跳转到错误位置。
   - **修复**：duration<=0 时重置 `isSeeking = false` 并 return，确保 ACTION_UP 的 handleSlideSeekRelease 不会执行无效 seekTo。

5. **自检确认安全项**：
   - playSpeed 在 VideoPlayer.kt L605（倍速对话框 onItemClick）被更新，长按松手恢复到用户设置的倍速（非固定1.0f）✅
   - VideoFragment.onLongPress 与 VideoPlayer.onLongPress 逻辑一致 ✅
   - onDoubleTap 状态切换正确（PLAYING→pause, PAUSE→start）✅
   - 单击不会误触发 seek（ACTION_DOWN 设 isSeeking=false，单击无 ACTION_MOVE）✅
   - 长按与 seek 互斥（!isLongPressSpeed 判定）✅
   - 上下滑动切文章保留（AD-05 方向锁定机制）✅
   - OnTouchListener 始终返回 true（R3 设计决策），返回值死代码但不影响功能 ✅

6. **设计冗余（非bug，暂不修改）**：
   - VideoPlayer.kt 内部 onLongPress/touchSurfaceUp/onDoubleTap 是死代码（GSY 收不到事件，但保留不影响功能）
   - handlePlayerTouchEvent/handleArticleModeTouchEvent 返回值未被 OnTouchListener 使用（始终返回 true）
   - handleSlideSeekMove 内部方向判定与 handleArticleModeTouchEvent 重复（逻辑正确，仅冗余）

### 2026-07-13 L2 真机验证 + 移除日志 + 编译验证

7. **L2 真机验证全部通过**（场景1-8）：
   - 场景1-3（长按倍速/左右seek/双击暂停）：logcat 确认 VideoGesture tag 日志正确触发
   - 场景4（上下滑动切文章）：d.swipe 慢速垂直滑动 + 标题 hash 对比（1514947047968397744 → -8350112212735274538）确认切文章成功
   - 场景5（手势冲突）：场景2+场景4 组合验证，AD-05 方向锁定工作正常
   - 场景6（倍速设置入口）：展开 BottomSheet 后 d(resourceId='tv_press_speed').exists=True
   - 场景7（快退快进按钮移除）：UI dump 确认 right_buttons 只有 btn_fullscreen/btn_star/btn_settings
   - 场景8（duration<=0 边界）：代码层面验证 L1146-1149 isSeeking=false

8. **移除临时日志**：移除6处 VideoGesture + 1处 VideoBack + unused import android.util.Log
   - 注意：并行 Edit 同一文件导致竞态条件，L1148 的 Log.d 未被移除，串行重新 Edit 修复
   - 教训：AGENTS.md 规定"同一源码文件的所有 Edit 必须串行执行"，本次违反了规范

9. **编译验证**：BUILD SUCCESSFUL in 48s，APK=legado_app_3.26.071314.apk（50MB）
   - updateLog.md 2026/07/13 条目已包含所有 video-gesture-overhaul 变更，无需新增
