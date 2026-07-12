# Spec：视频播放器 UI 去重与布局调整

## Intent

订阅源内置视频播放器（type=2）的右侧自定义功能区与 GSY 底部原始控件存在功能重叠（静音、倍速），且左下角名称区域因 marginBottom 不足遮挡 GSY 底部播放条。本 spec 旨在消除功能重叠、调整布局避免遮挡，提升用户体验。

## Scope

### In Scope

1. **删除右侧功能区静音按钮（btn_mute）**
   - 删除 fragment_video.xml 中的 btn_mute ImageButton
   - 删除 VideoFragment.kt 中 btnMute 变量声明、findViewById、点击事件、updateMuteButtonState() 方法、onDestroyView 清理
   - 用户通过 GSY 底部 ivMute 实现静音切换

2. **删除右侧功能区倍速按钮（btn_speed）**
   - 删除 fragment_video.xml 中的 btn_speed ImageButton
   - 删除 VideoFragment.kt 中 btnSpeed 变量声明、findViewById、点击事件、showSpeedMenu() 方法、onDestroyView 清理
   - 用户通过 GSY 底部 playbackSpeed 实现倍速切换

3. **左下角名称区域上移**
   - fragment_video.xml 中 left_bottom_container 的 marginBottom：24dp → 56dp
   - 避免遮挡 GSY 底部控件（高 50dp）+ 留 6dp 间距

4. **全屏按钮同步上移**
   - fragment_video.xml 中 btn_fullscreen 的 marginBottom：24dp → 56dp
   - 保持与 left_bottom_container 底部对齐

### Out of Scope

- **设置面板的"静音开机启动(muteOnStart)"和"长按倍速(longPressSpeed)"设置项**：这些是预设置（非实时切换），与 GSY 底部控件的实时切换不重叠，保留
- **右侧功能区剩余4按钮（快退/收藏/设置/快进）**：不与 GSY 底部控件重叠，保留
- **GSY 底部控件的样式/功能调整**：不修改 GSY 原生控件
- **控件显隐逻辑调整**：F2-Bug3 修复的 gsyControlsVisible 标志 + override changeUiTo* 逻辑保持不变

## Approach

### 核心方案：删除重叠按钮 + 调整 marginBottom

**布局修改**（fragment_video.xml）：
1. 删除 btn_mute 的 ImageButton（L141-152）
2. 删除 btn_speed 的 ImageButton（L167-178）
3. left_bottom_container marginBottom：24dp → 56dp
4. btn_fullscreen marginBottom：24dp → 56dp

**代码修改**（VideoFragment.kt）：
1. 删除 btnMute/btnSpeed 变量声明（L97, L99）
2. 删除 btnMute/btnSpeed findViewById（L546, L548）
3. 删除 btnMute 点击事件 + updateMuteButtonState() 调用（L572-578）
4. 删除 btnSpeed 点击事件 + showSpeedMenu() 调用（L586-589）
5. 删除 updateMuteButtonState() 方法（L1007-1012）
6. 删除 showSpeedMenu() 方法（L1079-1093）
7. 删除 onDestroyView 中 btnMute/btnSpeed 清理（L182, L184）

### Alternatives Considered

**方案A：删除右侧静音+倍速（本方案，推荐）**
- 优点：消除重叠，用户通过 GSY 底部控件操作，体验统一
- 缺点：右侧功能区按钮减少（6→4），但功能无损失

**方案B：删除 GSY 底部静音+倍速，保留右侧**
- 优点：右侧功能区按钮不变
- 缺点：需 override GSY 布局，修改 mBottomContainer 可见性逻辑复杂；GSY 底部进度条仍需保留，无法整体隐藏
- 否决原因：修改 GSY 原生控件风险高，且 F2-Bug3 刚修复了 GSY 控件显隐问题

**方案C：两侧都保留，仅调整布局**
- 优点：不删除任何功能
- 缺点：功能重叠未解决，用户体验仍混乱
- 否决原因：用户明确要求"去掉右侧功能区的这两个功能"

### Drawbacks

1. **右侧功能区按钮减少**：6按钮→4按钮，视觉上右侧功能区变短，但因垂直居中（gravity=center_horizontal + constraintTop/Bottom）自动适应，不影响布局
2. **updateMuteButtonState() 移除后，静音状态图标不再实时更新**：用户通过 GSY 底部 ivMute 查看静音状态，GSY 内部自动管理图标，无需我们同步
3. **marginBottom 固定值不适应控件显隐**：控件隐藏时（PURE态）GSY 底部控件也隐藏，此时 left_bottom_container 下方留 56dp 空白。但这是可接受的折中，避免动态调整 marginBottom 的复杂度

## Requirements

### REQ-1：功能去重

- REQ-1.1：删除 fragment_video.xml 中 btn_mute ImageButton
- REQ-1.2：删除 fragment_video.xml 中 btn_speed ImageButton
- REQ-1.3：删除 VideoFragment.kt 中 btnMute 相关所有代码（变量/findViewById/点击事件/方法）
- REQ-1.4：删除 VideoFragment.kt 中 btnSpeed 相关所有代码（变量/findViewById/点击事件/方法）
- REQ-1.5：确保 GSY 底部 ivMute 和 playbackSpeed 功能正常（F2-Bug3 修复的 gsyControlsVisible 标志保持不变）

### REQ-2：布局调整

- REQ-2.1：left_bottom_container marginBottom 从 24dp 改为 56dp
- REQ-2.2：btn_fullscreen marginBottom 从 24dp 改为 56dp
- REQ-2.3：确保上移后不遮挡视频画面关键区域（上移 32dp 在可接受范围）

### REQ-3：代码清理

- REQ-3.1：移除 updateMuteButtonState() 方法（确认无其他调用点）
- REQ-3.2：移除 showSpeedMenu() 方法（确认无其他调用点）
- REQ-3.3：移除 onDestroyView 中 btnMute = null 和 btnSpeed = null

### REQ-4：验证

- REQ-4.1：编译通过（BUILD SUCCESSFUL）
- REQ-4.2：L1 验证（App 正常启动到 MainActivity 无崩溃）
- REQ-4.3：L2 验证（右侧功能区仅4按钮 + 左下角不遮挡 GSY 底部控件）
- REQ-4.4：updateLog.md 追加变更说明

## Scenarios

### Scenario 1：用户打开内置视频播放器

**前置条件**：订阅源 type=2，ruleContent 返回视频 URL

**操作**：用户点击文章进入视频播放器

**预期**：
- 视频播放器启动，控件显示（NORMAL态）
- 右侧功能区显示4个按钮：快退 / 收藏 / 设置 / 快进（无静音、无倍速）
- 左下角显示标题/线路/集数，不遮挡 GSY 底部播放条
- GSY 底部显示进度条/时间/静音/倍速/设置

### Scenario 2：用户使用静音功能

**前置条件**：视频正在播放

**操作**：用户点击 GSY 底部的静音按钮(ivMute)

**预期**：
- GSY 底部 ivMute 图标切换为静音状态
- 视频静音播放
- 右侧功能区无静音按钮（已删除）

### Scenario 3：用户使用倍速功能

**前置条件**：视频正在播放

**操作**：用户点击 GSY 底部的倍速按钮(playbackSpeed)

**预期**：
- GSY 弹出倍速选择菜单
- 选择倍速后视频按新倍速播放
- 右侧功能区无倍速按钮（已删除）

### Scenario 4：控件自动隐藏后单击显示

**前置条件**：视频正在播放，控件已自动隐藏（PURE态）

**操作**：用户单击屏幕

**预期**：
- 控件显示（NORMAL态）
- 右侧功能区4按钮 + 左下角名称 + GSY 底部控件全部显示
- 左下角名称不遮挡 GSY 底部控件

### Scenario 5：横屏视频全屏按钮

**前置条件**：横屏视频播放

**操作**：用户查看全屏按钮位置

**预期**：
- 全屏按钮在屏幕底部居中显示
- 全屏按钮 marginBottom=56dp，不遮挡 GSY 底部控件
