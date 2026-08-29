# Spec：视频播放器体验五项修复

## Intent

解决用户在内置视频播放器中反馈的 5 个体验问题：本地视频误显下载按钮、滑动 seek 速度不可调、配置弹框透明且不符弹框规范、全屏标题位置不合理、全屏返回按钮偏大。目标是在不触碰手势体系与播放核心逻辑的前提下，完成 UI 层自适应与规范对齐。

## Scope

**做什么**：

- P1 本地播放时隐藏右侧下载按钮（`file://` 判定）
- P2 新增"滑动快进灵敏度"设置项（档位式），seek 计算乘灵敏度系数
- P3 `SettingsDialog` 弹框透明修复 + 对齐 `AppDialogFrame` 规范壳 + `VideoSettingsPanelContent` 取色同源治理
- P4 全屏时标题显示于左上角返回按钮右侧，左下角隐藏标题（保留线路/集数选择器）
- P5 全屏返回按钮图标净尺寸收敛 20dp（对齐 GlassTopAppBar R4 档）

**不做什么**：

- 不改手势体系（上下滑切视频 / 左右滑 seek / 长按倍速 / 双击暂停）
- 不改播放核心（ExoPlayer/WebView 双引擎、嗅探、边下边播 SimpleCache）
- 不动 BottomSheet 版设置面板（`VideoSettingsPanel`）的壳实现（仅共享内容组件取色随之统一）
- 不处理在线流播放时的下载按钮逻辑（保持现状显示）

## Approach

### Selected Approach

1. **P1**：`VideoFragment` 播放初始化处按 `VideoPlay.videoUrl.startsWith("file://")` 判定本地直连播放，隐藏 `btnDownload`；绑定统一入口 `bindViews` 后的初始化段处理，Activity 生命周期内 videoUrl 不变，无需动态切换。
2. **P2**：`VideoPlay` 新增 `seekSensitivity`（Int，存 5/7/10/15/20 → 实际倍率 0.5x/0.7x/1.0x/1.5x/2.0x，默认 10=1.0x），持久化 `video_config` prefs；`handleSlideSeekMove` 的 offset 计算乘以 `seekSensitivity / 10f`；设置 UI 加在 `VideoSettingsPanelContent` 播放设置区，复用 `SingleChoiceDialog` 模式。
3. **P3**：`SettingsDialog` 内容用 `AppDialogFrame`（`rememberAppDialogStyle()` + `themeUiPalette.cardColor` + `UiCorner.panelRadius`）包壳；`VideoSettingsPanelContent` 内部 `MaterialTheme.colorScheme.*` 取色替换为 `themeUiPalette` 同源取色（BottomSheet 版共享组件一并受益）；注意 `AppDialogFrame` 的滚动嵌套禁令（内容含滚动组件时参数化 `scrollable=false`）。
4. **P4**：`fragment_video.xml` 在 `btn_back_overlay` 右侧新增 `tv_title_fullscreen`（约束：start→btn_back_overlay end，top 与返回按钮对中）；抽取统一 `setTitle(text)` 方法同步双标题控件；`onFullScreenChanged` 切换显隐；三处标题赋值点（`updateVideoTitle` / 集数切换 / 初始化）统一走 `setTitle`。
5. **P5**：`btn_back_overlay` 的 `padding` 由 12dp 调整为 14dp（48dp 按钮 - 14dp×2 = 净 20dp），对齐 GlassTopAppBar 导航图标 20dp 档。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| P1 用 `VideoPlay.singleUrl` 标志判定本地播放 | `singleUrl=true` 也涵盖用户手动输入的在线直链（http），会误隐藏在线直链的下载按钮；`file://` scheme 判定更精准 |
| P2 固定改小默认 seek 比例（如全屏宽=半片长） | "太快/太慢"因人而异，且改变所有用户默认体验；档位化配置让用户自选，默认值保持现状不惊扰 |
| P2 用滑动条（Slider）调灵敏度 | 档位少（5 档）且离散，Slider 交互成本高于单选弹窗；项目现有播放器设置统一走 `SingleChoiceDialog` 模式 |
| P3 仅给 SettingsDialog window 设不透明背景色 | 违反 dialog-shell.md 规范（应走 AppDialogFrame 统一壳+取色同源），且内容 `colorScheme.*` 取色偏色问题依旧存在 |
| P3 重写一套视频专用弹框组件 | 重复造轮子；`AppDialogFrame` 已是规范标准实现，直接复用 |
| P4 用 ConstraintLayout 动态改 `tv_video_title` 约束实现移位 | 代码切换约束易碎、可读性差；新增独立全屏标题控件 + 统一 `setTitle` 同步更简单可控 |
| P5 缩小按钮本体尺寸（48dp→40dp） | 破坏右侧功能区 48dp 触控目标统一性（无障碍）；仅缩图标净尺寸即可解决"大/粗"观感 |

### Drawbacks

- **P2**：`seekSensitivity` 用 Int 存储乘以 `/10f` 换算倍率，0.7x 为非整十档位，需在选项文案中明确标注倍率含义；接受理由：避免浮点存储精度问题，与 `longPressSpeed`（存 30=3.0x）既有模式一致。
- **P3**：`VideoSettingsPanelContent` 是两壳共享组件，取色替换会同时影响 BottomSheet 版视觉——这是**预期内收益**（统一规范）但属于共享组件变更，需真机双入口回归验证。
- **P4**：新增 `tv_title_fullscreen` 控件产生双标题数据源，必须收敛到统一 `setTitle` 方法，否则未来新增赋值点可能漏同步；接受理由：控件级隔离比动态改约束更稳，`setTitle` 单点收敛可控。

### Prior Art

- GlassTopAppBar 导航图标 20dp 档（`bookshelf-refresh-and-title-fix R4`，同项目 precedent）
- `longPressSpeed`（Int 存 10 倍值）设置持久化模式（`VideoPlay.kt` L89-93）
- `SingleChoiceDialog` 在播放器类型选择中的应用（`VideoSettingsPanelContent.kt` L354-370）

## Requirements

### R1: 本地视频隐藏下载按钮

- R1.1 当 `VideoPlay.videoUrl` 以 `file://` 开头时，右侧 `btn_download` 隐藏（GONE）
- R1.2 在线播放（http/https）时下载按钮保持现状显示
- R1.3 隐藏判定在视图绑定后、播放开始前完成，不闪烁

### R2: 滑动快进灵敏度可配置

- R2.1 `VideoPlay` 新增 `seekSensitivity` 设置，持久化到 `video_config` SharedPreferences
- R2.2 档位：0.5x / 0.7x / 1.0x（默认）/ 1.5x / 2.0x；seek offset = 滑动比例 × 灵敏度 × 时长
- R2.3 设置入口：`VideoSettingsPanelContent` 播放设置区，点击弹 `SingleChoiceDialog` 选择
- R2.4 变更即时生效（下一段滑动手势即用新灵敏度），无需重启播放器
- R2.5 设置弹框（Dialog 壳）与 BottomSheet 壳两入口均可配置

### R3: 配置弹框规范对齐

- R3.1 `SettingsDialog` 弹框背景不透明，使用 `AppDialogFrame` 规范壳（cardColor 取色 + panelRadius 圆角）
- R3.2 `VideoSettingsPanelContent` 内部取色从 `MaterialTheme.colorScheme.*` 替换为 `themeUiPalette` 同源取色
- R3.3 遵守滚动嵌套禁令（AppDialogFrame 与内容滚动组件参数化隔离）
- R3.4 BottomSheet 版（播放器右侧设置按钮入口）视觉同步统一

### R4: 全屏标题移位

- R4.1 全屏态：标题显示于左上角返回按钮右侧（垂直居中对齐返回按钮），左下角标题隐藏
- R4.2 非全屏态：标题维持左下角现状
- R4.3 全屏标题参与 overlay controls 3 秒自动隐藏 + 单击重新显示（与返回按钮同组）
- R4.4 线路/集数选择器不受影响（全屏时保持左下角）
- R4.5 标题更新点统一收敛到单一 `setTitle` 方法，双控件同步

### R5: 全屏返回按钮尺寸对齐

- R5.1 `btn_back_overlay` 图标净尺寸收敛至 20dp（padding 14dp），对齐 GlassTopAppBar R4 档
- R5.2 按钮本体 48dp 触控目标与半透明背景保持不变

## Scenarios

### S1: 播放已下载视频

1. 用户进入"下载管理"，点击已完成视频播放
2. `videoUrl` 为 `file://` URI，播放器右侧下载按钮**不显示**
3. 全屏/收藏/设置按钮正常显示，播放正常

### S2: 在线订阅源视频播放

1. 用户从订阅源嗅探播放在线视频
2. 下载按钮正常显示，点击可发起下载

### S3: 调整滑动灵敏度

1. 用户打开设置弹框（右上角菜单"配置设置"或右侧设置按钮）
2. 进入"滑动快进灵敏度"，弹单选弹窗，默认选中 1.0x
3. 选择 0.5x，返回播放器，左右滑动 seek，滑动相同距离跳转进度减半
4. 退出播放器重进，灵敏度设置保持 0.5x

### S4: 全屏播放标题显示

1. 用户点击全屏按钮进入横屏全屏
2. 标题显示在左上角返回按钮右侧；左下角仅线路/集数选择器
3. 3 秒后随控件自动隐藏，单击屏幕重新显示
4. 退出全屏，标题恢复左下角显示

### S5: 配置弹框视觉

1. 用户点击右上角菜单 →"配置设置"
2. 弹框为不透明卡片（跟随主题 cardColor），圆角一致，文字清晰可读
3. 切换暗色/亮色主题，弹框配色跟随
4. 从右侧设置按钮打开 BottomSheet 面板，两入口视觉风格一致
