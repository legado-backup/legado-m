# 视频播放器主题统一 — 任务清单

> 状态标记：⚠️ 代码完成（Level 1）｜✅ 功能验证（Level 2/3）
> 关联需求：[spec.md](./spec.md)｜设计：[design.md](./design.md)

## 1. 准备工作

- [x] 1.1 阅读播放器相关源码（VideoPlayer.kt / ChoiceSpeedDialog / ChoiceEpisodeDialog / 控制条布局）— 已完成（需求分析阶段）
- [x] 1.2 确认 ThemeStore / UiCorner 可用的主题属性清单 — 已完成
- [x] 1.3 确认主题刷新机制（EventBus.RECREATE + refreshThemeAppearanceIfChanged）— 已完成

## 2. 核心实现

### 2.1 播放器控制条主题化（FR-1 / AD-01）

- [x] 2.1.1 `VideoPlayer` 新增 `applyThemeColors()`：播放进度条 `progressTintList` = `ThemeStore.accentColor()`，缓冲进度条 = 主题色半透明
- [x] 2.1.2 控制条深色悬浮层保持（背景/文字不改），全屏控制条同步调用（startWindowFullscreen 新建实例同步 applyThemeColors + 退出全屏 resolveNormalVideoShow 兜底）
- [x] 2.1.3 在 init / RECREATE 分支 / onConfigurationChanged 时机触发 `applyThemeColors()`（VideoPlayerActivity observeLiveBus 订阅 EventBus.RECREATE + onConfigurationChanged + applyVideoThemeColors 全量刷新）

### 2.2 弹框主题化（FR-2 / AD-02）

- [x] 2.2.1 `ChoiceSpeedDialog`：show 前动态设容器背景 = `ThemeStore.backgroundColor()` + `UiCorner.panelRadius`；选中高亮改用 `ThemeStore.accentColor()`；列表项文字 = `textColorPrimary`
- [x] 2.2.2 `ChoiceEpisodeDialog`：同 2.2.1 动态设色；initialSelection 传给 SwitchVideoAdapter 做当前集高亮
- [x] 2.2.3 `showRatioDialog` / `showAudioTrackDialog`：原生 AlertDialog 改 `alert()` 扩展走项目主题

### 2.3 硬编码色清理（FR-3）

- [x] 2.3.1 activity_video_player.xml 旧模式功能区（#1A2B4A/#8AB4F8）— 用户决策：删除废弃区块（含配套代码引用清理）
- [x] 2.3.2 调试面板（#80000000/#FFFFFF）— 用户决策：删除废弃区块（含配套代码引用清理）

### 2.4 文案资源化（FR-4）

- [x] 2.4.1 strings.xml（en+zh）新增：video_speed / video_danmaku_off / video_danmaku_on / video_ratio / video_audio_track / video_episode_list / video_ratio_default / video_ratio_16_9 / video_ratio_4_3 / video_ratio_fill / video_speed_playing
- [x] 2.4.2 替换所有硬编码中文（VideoPlayer.kt / video_layout_controller*.xml / switch_episode_video_dialog.xml）

## 3. 验证

- [x] 3.1 编译门禁：`./gradlew assembleAppDebug` 通过（BUILD SUCCESSFUL，全部 up-to-date）
- [x] 3.2 静态核对：Grep 确认弹框面板无残留硬编码色（控制条 `#ffffff`/`#99/80-000000` 为 AD-01 保留的深色悬浮层白字）；作用域内硬编码中文已资源化
- [ ] 3.3 真机验证（L2）：日间/夜间模式进入播放器，弹框/控制条/进度条颜色正确 — ⏸️ 延后（用户 2026-08-24 选择"本轮静态收尾"，模拟器无视频书数据，待有视频源数据/真机时补做）
- [ ] 3.4 真机验证：播放中切换主题，进度条高亮/弹框颜色随主题刷新 — ⏸️ 延后（同上）
- [ ] 3.5 真机验证：全屏控制条 / 倍速弹框（分隔项/高亮/右侧滑出）/ 选集 / 画面比例 / 音轨交互不回归 — ⏸️ 延后（同上）

## 4. 交付同步

- [x] 4.1 更新 updateLog.md（基于 git diff 分析真实变更）
- [x] 4.2 更新 docs/INDEX.md（进行中 → 已完成）
- [x] 4.3 文档同步：检查 docs/project-flow/ 相关文档一致性（历史 spec douyin-style/rss-video-player-enhancement 为历史记录无需改动；本任务 design File Changes 已与 git diff 核对）
- [x] 4.4 tasks.md 标记完成级别 + 清理临时日志（Grep 确认 gsyVideo/VideoPlayerActivity 无 android.util.Log 残留）

## AOAdapt 日志

- 2026-08-24：video_seek_progress.xml / video_seek_thumb.xml 不存在，进度条用 bottom_progress_buffer.xml + 代码动态 tint（progressTintList/secondaryProgressTintList/thumbTintList）
- 2026-08-24：`alert(context, ...)` → `context.alert(...)` 接收者修正（AndroidDialogs 扩展的接收者是 Context）
- 2026-08-24：values/strings.xml 重复 video_ratio/video_audio_track 键导致资源合并失败，已去重
