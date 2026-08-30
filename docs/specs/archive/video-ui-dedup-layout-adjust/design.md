# Design：视频播放器 UI 去重与布局调整

## Technical Approach

### 整体策略

本 spec 属于 UI 层面的简单优化（删除控件 + 调整边距），不涉及架构变更。修改范围限定在2个文件：

1. **fragment_video.xml**：删除2个 ImageButton + 调整2处 marginBottom
2. **VideoFragment.kt**：删除变量声明/findViewById/点击事件/方法定义/onDestroyView 清理

### 修改前布局结构

```
fragment_video.xml
├── playerView (VideoPlayer, 铺满)
└── controlsLayer (ConstraintLayout, clickable=false)
    ├── left_bottom_container (LinearLayout, marginBottom=24dp)
    │   ├── tv_video_title
    │   ├── tv_route_selector
    │   └── rv_episodes
    ├── btn_fullscreen (ImageButton, marginBottom=24dp)
    └── right_buttons (LinearLayout, vertical)
        ├── btn_rewind (快退)
        ├── btn_mute (静音) ← 删除
        ├── btn_star (收藏)
        ├── btn_speed (倍速) ← 删除
        ├── btn_settings (设置)
        └── btn_forward (快进)
```

### 修改后布局结构

```
fragment_video.xml
├── playerView (VideoPlayer, 铺满)
└── controlsLayer (ConstraintLayout, clickable=false)
    ├── left_bottom_container (LinearLayout, marginBottom=56dp) ← 上移32dp
    │   ├── tv_video_title
    │   ├── tv_route_selector
    │   └── rv_episodes
    ├── btn_fullscreen (ImageButton, marginBottom=56dp) ← 上移32dp
    └── right_buttons (LinearLayout, vertical)
        ├── btn_rewind (快退)
        ├── btn_star (收藏)
        ├── btn_settings (设置)
        └── btn_forward (快进)
```

### marginBottom 计算依据

```
GSY 底部控件（layout_bottom）高度 = 50dp（layout_alignParentBottom="true"）
当前 left_bottom_container marginBottom = 24dp
重叠量 = 50dp - 24dp = 26dp

修复后 marginBottom = 56dp
  = 50dp（GSY 底部控件高度）
  + 6dp（间距）
上移量 = 56dp - 24dp = 32dp
```

## Architecture Decisions

### ADR-1：删除右侧静音/倍速 vs 删除 GSY 底部静音/倍速

**Context**：右侧功能区的静音(btn_mute)和倍速(btn_speed)与 GSY 底部控件(ivMute/playbackSpeed)功能重叠，需要去除一侧

**Decision**：删除右侧功能区的静音和倍速，保留 GSY 底部控件

**Y-Statement**：
- **Doing**：删除 fragment_video.xml 中 btn_mute 和 btn_speed，删除 VideoFragment.kt 中相关代码，用户通过 GSY 底部控件操作静音和倍速
- **For**：消除功能重叠，统一用户操作入口（GSY 底部控件），降低维护成本
- **Accepting**：右侧功能区按钮减少（6→4），updateMuteButtonState()/showSpeedMenu() 方法被移除

**Alternatives**：
- 删除 GSY 底部静音/倍速：需 override GSY 布局，修改 mBottomContainer 可见性逻辑复杂，且 F2-Bug3 刚修复 GSY 控件显隐问题，风险高
- 两侧都保留：功能重叠未解决，用户体验混乱

**Consequences**：
- 正面：代码简化，消除死代码，用户体验统一
- 负面：右侧功能区视觉变短（可接受，垂直居中自动适应）

### ADR-2：marginBottom 固定值 vs 动态调整

**Context**：left_bottom_container 需要上移避免遮挡 GSY 底部控件，但 GSY 底部控件在 PURE态（控件隐藏）时也隐藏

**Decision**：使用固定值 marginBottom=56dp

**Y-Statement**：
- **Doing**：left_bottom_container 和 btn_fullscreen 的 marginBottom 固定为 56dp
- **For**：简单实现，避免动态调整 marginBottom 的复杂度
- **Accepting**：控件隐藏时（PURE态）下方留 56dp 空白

**Alternatives**：
- 动态调整：根据控件显隐状态动态切换 marginBottom（24dp↔56dp），复杂度高
- 约束到 GSY mBottomContainer 上方：需访问 GSY 内部控件，耦合度高

**Consequences**：
- 正面：实现简单，布局稳定
- 负面：PURE态下方有空白（可接受，PURE态控件全部隐藏，用户不关注布局）

## Data Flow

### 修改前：静音功能数据流

```
用户点击 btn_mute
  → VideoFragment.btnMute.setOnClickListener
  → _playerView.toggleMute()
  → VideoPlayer.isMuted = !isMuted
  → getGSYVideoManager().player?.setNeedMute(isMuted)
  → updateMuteIcon() (VideoPlayer 内部)
  → VideoFragment.updateMuteButtonState()
  → btnMute.setImageResource(ic_volume_off/ic_volume_up)
```

### 修改后：静音功能数据流

```
用户点击 GSY 底部 ivMute
  → GSY 内部 onClickUiToggle / clickUiToggle
  → VideoPlayer.toggleMute()（如 GSY 绑定）
  → 或 GSY 内部静音处理
  → GSY 底部 ivMute 图标自动更新
```

> 注：GSY 底部 ivMute 的点击事件由 GSY 内部处理，我们的 VideoPlayer.toggleMute() 方法保留（供设置面板或其他地方调用），仅删除右侧 btn_mute 的调用入口。

### 修改前：倍速功能数据流

```
用户点击 btn_speed
  → VideoFragment.btnSpeed.setOnClickListener
  → showSpeedMenu(v)
  → PopupMenu 弹出倍速选择
  → pv.setSpeed(speed, true)
```

### 修改后：倍速功能数据流

```
用户点击 GSY 底部 playbackSpeed
  → GSY 内部倍速处理
  → GSY 弹出倍速选择菜单
  → 选择后 GSY 内部 setSpeed
```

## File Changes

### 文件1：fragment_video.xml

**路径**：`app/src/main/res/layout/fragment_video.xml`

**修改点**：

| 修改点 | 行号 | 操作 | 说明 |
|--------|------|------|------|
| 1 | L141-152 | 删除 | btn_mute ImageButton 整块 |
| 2 | L167-178 | 删除 | btn_speed ImageButton 整块 |
| 3 | L50 | 修改 | left_bottom_container marginBottom: 24dp → 56dp |
| 4 | L103 | 修改 | btn_fullscreen marginBottom: 24dp → 56dp |

### 文件2：VideoFragment.kt

**路径**：`app/src/main/java/io/legado/app/ui/video/VideoFragment.kt`

**修改点**：

| 修改点 | 行号 | 操作 | 说明 |
|--------|------|------|------|
| 1 | L97 | 删除 | `private var btnMute: ImageButton? = null` |
| 2 | L99 | 删除 | `private var btnSpeed: ImageButton? = null` |
| 3 | L182 | 删除 | `btnMute = null` |
| 4 | L184 | 删除 | `btnSpeed = null` |
| 5 | L546 | 删除 | `btnMute = view.findViewById(R.id.btn_mute)` |
| 6 | L548 | 删除 | `btnSpeed = view.findViewById(R.id.btn_speed)` |
| 7 | L572-578 | 删除 | btnMute 点击事件 + updateMuteButtonState() 调用 |
| 8 | L586-589 | 删除 | btnSpeed 点击事件 + showSpeedMenu() 调用 |
| 9 | L1007-1012 | 删除 | updateMuteButtonState() 方法 |
| 10 | L1079-1093 | 删除 | showSpeedMenu() 方法 |

### 文件3：updateLog.md

**路径**：`app/src/main/assets/updateLog.md`

**修改点**：顶部追加 2026/07/12 条目

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| GSY 底部 ivMute/playbackSpeed 不工作 | 低 | F2-Bug3 已修复 GSY 控件显隐，用户反馈确认 GSY 底部控件功能正常 |
| 删除代码后编译错误 | 低 | 仅删除完整的方法/变量/事件，不涉及交叉引用 |
| marginBottom=56dp 仍然遮挡 | 低 | GSY 底部控件高度 50dp，56dp 已留 6dp 间距 |
| updateMuteButtonState() 有其他调用点 | 无 | 已 Grep 确认仅 L573/L577 两处调用，均在 btnMute 相关代码内 |
| showSpeedMenu() 有其他调用点 | 无 | 已 Grep 确认仅 L588 一处调用，在 btnSpeed 点击事件内 |
