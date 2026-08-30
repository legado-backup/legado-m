# Tasks：视频播放器 UI 去重与布局调整

## 任务清单

### Phase 1：布局修改（fragment_video.xml）

- [x] 1.1 删除 btn_mute ImageButton（L141-152）
- [x] 1.2 删除 btn_speed ImageButton（L167-178）
- [x] 1.3 修改 left_bottom_container marginBottom：24dp → 56dp（L50）
- [x] 1.4 修改 btn_fullscreen marginBottom：24dp → 56dp（L103）

### Phase 2：代码清理（VideoFragment.kt）

- [x] 2.1 删除 btnMute 变量声明（L97）
- [x] 2.2 删除 btnSpeed 变量声明（L99）
- [x] 2.3 删除 onDestroyView 中 btnMute = null（L182）
- [x] 2.4 删除 onDestroyView 中 btnSpeed = null（L184）
- [x] 2.5 删除 btnMute findViewById（L546）
- [x] 2.6 删除 btnSpeed findViewById（L548）
- [x] 2.7 删除 btnMute 点击事件 + updateMuteButtonState() 调用（L572-578）
- [x] 2.8 删除 btnSpeed 点击事件 + showSpeedMenu() 调用（L586-589）
- [x] 2.9 删除 updateMuteButtonState() 方法（L1007-1012）
- [x] 2.10 删除 showSpeedMenu() 方法（L1079-1093）

### Phase 3：验证

- [x] 3.1 编译验证（BUILD SUCCESSFUL）✅ APK 071211 (50MB)
- [x] 3.2 L1 验证（App 正常启动到 MainActivity 无崩溃）✅
- [x] 3.3 L2 验证（右侧功能区仅4按钮 + 左下角不遮挡 GSY 底部控件）✅
  - 导入视频订阅源（奈飞中文网）→ 导航到视频播放器成功
  - btn_mute/btn_speed 已删除 ✅
  - 4个右侧按钮保留（btn_rewind/btn_star/btn_settings/btn_forward）✅
  - btn_fullscreen 底部中央 marginBottom 56dp 生效 ✅
  - left_bottom_container 底部左侧上移生效 ✅
  - 无崩溃日志 ✅
  - 注：control_visibility 场景因 SwipeTest 临时日志已在 Task #69 移除而未通过，属预期行为非回归
- [x] 3.4 updateLog.md 追加 2026/07/12 变更说明

### Phase 4：文档同步

- [x] 4.1 更新 tasks.md 标记完成
- [x] 4.2 更新 project_memory.md 记录完成
- [x] 4.3 更新 INDEX.md spec 状态标记为 ✅ 已完成

## AOAdapt 日志

> 记录实施过程中与设计文档不一致的地方，及分析决策。

### 实施记录（2026-07-12）

1. **Phase 1+2 代码修改**：严格按 design.md 的 File Changes 执行，7 个 Edit 串行完成（变量声明2处+onDestroyView 2处+findViewById 2处+点击事件2处+方法定义2处），Grep 确认 14 处引用全部清除无残留。
2. **PopupMenu import 保留**：删除 showSpeedMenu() 后检查 PopupMenu 是否仍被使用，确认 initRouteSelector/initEpisodeSelector 仍使用 PopupMenu（L603/L696），import 保留。
3. **updateLog.md 历史条目**：L13 旧条目提到"右侧竖直排列快退/静音/收藏/倍速/设置/快进按钮"，现已移除静音/倍速，但作为历史记录保持原样（L9 新条目已说明本次变更）。
4. **遗留后台任务清理**：编译前发现 6 个 2026-07-09 的旧 E2E 测试 job 仍在运行（run_e2e.py --tc F-P0-6，使用旧 APK 070913，大量失败），TaskStop 确认已非活动任务。
5. **L2 验证导航修复**：l2_verify_video_player.py 自动导航失败（脚本查找"订阅源"Tab 但实际 Tab 文字是"订阅"）。采用手动导航方案：uiautomator2 查找底部导航 → 点击"订阅" → 点击"奈飞中文网"订阅源 → 点击第一篇文章 → 成功进入 VideoPlayerActivity。然后用 --manual 模式验证。
6. **control_visibility 场景预期失败**：L2 验证 control_visibility 场景未通过，根因是 SwipeTest 临时日志已在 Task #69 移除，脚本依赖的 "F2 scheduleAutoHide"/"F2 autoHide触发" 日志不再存在。此为预期行为，非 UI 去重引入的回归。UI 去重的核心验证（按钮删除/保留/位置）全部通过。
