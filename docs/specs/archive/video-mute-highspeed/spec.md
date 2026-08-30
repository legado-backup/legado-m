# spec.md - 视频播放器优化：默认静音 + 高倍速支持

## Intent

用户反馈视频播放器在公共场合突然外放声音不便，且当前最高倍速 3X 不够用。需要：
1. 默认静音启动，用户可手动开启声音
2. 支持 5X/10X/15X 高倍速播放

## Scope

### In Scope
- VideoPlay.kt 新增 `muteOnStart` 配置（默认 true）
- VideoPlayer.kt 新增静音按钮 + 倍速列表扩展至 15X
- SettingsDialog 新增"默认静音"开关
- 播放器布局新增静音按钮 + 字符串资源

### Out of Scope
- 音量精细调节（滑块）——用户可用系统音量键
- 倍速自定义输入——只提供预设档位
- 15X 时的音频处理优化——高倍速音频失真是 ExoPlayer 限制

## Approach

### 主方案
1. **默认静音**：复用 `ExoPlayerManager.setNeedMute(Boolean)` 已有接口。VideoPlay.kt 新增 `muteOnStart` 属性（默认 true），在 `startPlay` 后调用。播放器界面新增静音按钮，点击切换。
2. **高倍速**：修改 `VideoPlayer.kt` 的倍速列表，增加 5.0f/10.0f/15.0f。ExoPlayer 的 `PlaybackParameters` 支持 float speed，无需修改底层。

### Alternatives Considered

- **A：仅在 SettingsDialog 新增静音开关（不在播放器界面加按钮）**
  - 优点：改动更少
  - 缺点：用户每次要退出播放器改设置，体验差
  - 否决原因：用户需要播放时一键切换

- **B：15X 时自动静音**
  - 优点：避免高倍速音频失真
  - 缺点：用户可能困惑为什么没声音
  - 否决原因：让用户自行决定，手动静音更直观

### Drawbacks

1. 15X 倍速时音频可能严重失真（ExoPlayer 音频处理限制，speed > 10 时效果差）
2. 默认静音可能导致用户误以为播放器坏了（需要明显的静音图标指示）
3. 倍速列表从 8 项增至 11 项，ChoiceSpeedDialog 可能需要滚动

## Requirements

### R1：默认静音
- R1.1 VideoPlay.kt 新增 `muteOnStart` 属性，默认 true
- R1.2 `startPlay` 后根据 `muteOnStart` 设置静音
- R1.3 播放器界面新增静音按钮，点击切换静音/非静音
- R1.4 SettingsDialog 新增"默认静音"开关
- R1.5 静音按钮图标根据当前状态切换（静音=ic_volume_off，非静音=ic_volume_up）

### R2：高倍速
- R2.1 倍速列表新增 5.0f / 10.0f / 15.0f
- R2.2 倍速切换时显示提示（如"15.0倍播放中"）
- R2.3 既有倍速（0.5X~3X）不受影响

### NF1：兼容性
- 不影响既有手势音量调节
- 不影响长按倍速功能

## Scenarios

### S1：首次播放视频（默认静音）
- 用户进入视频播放，默认静音，播放器界面显示静音图标
- 用户点击静音按钮，声音开启，图标变为 ic_volume_up

### S2：高倍速浏览
- 用户点击倍速按钮，弹出选择对话框
- 选择 15X，视频以 15 倍速播放，显示"15.0倍播放中"
- 倍速按钮文字显示"15.0X"

### S3：关闭默认静音
- 用户在视频设置中关闭"默认静音"开关
- 下次播放视频，声音默认开启

### S4：静音状态下切换倍速
- 静音状态下选择 5X，视频以 5 倍速静音播放
- 倍速切换不影响静音状态
