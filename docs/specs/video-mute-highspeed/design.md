# design.md - 视频播放器优化：默认静音 + 高倍速支持

## Technical Approach

### 1. 默认静音配置（VideoPlay.kt）

在 `cachePlay` 属性之后新增：
```kotlin
/**  默认静音（播放时默认关闭声音）  **/
var muteOnStart
    get() = videoPrefs.getBoolean("muteOnStart", true)
    set(value) {
        videoPrefs.edit { putBoolean("muteOnStart", value) }
    }
```

### 2. startPlay 后设置静音（VideoPlay.kt）

在 `startPlay()` 的 4 处 `player.startPlayLogic()` 调用后，新增静音设置：
```kotlin
if (muteOnStart) {
    player.setNeedMute(true)
}
```

涉及 4 处（与 cachePlay 修改的 4 处 setUp 对应）：
- L156 单链接分支
- L190 订阅源无 ruleContent 分支
- L221 订阅源有 ruleContent 分支
- L284 书籍章节分支

### 3. 静音按钮 UI（VideoPlayer.kt + 布局）

**布局**：在 `video_layout_controller_full.xml` 和 `video_layout_controller.xml` 的控制栏中新增 ImageView：
```xml
<ImageView
    android:id="@+id/iv_mute"
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:padding="8dp"
    android:src="@drawable/ic_volume_off_24dp" />
```

**逻辑**（VideoPlayer.kt initView）：
```kotlin
private var isMuted = false  // 当前静音状态

// initView 中绑定
ivMute = findViewById(R.id.iv_mute)
isMuted = VideoPlay.muteOnStart
updateMuteIcon()

ivMute?.setOnClickListener {
    isMuted = !isMuted
    setNeedMute(isMuted)
    updateMuteIcon()
}

private fun updateMuteIcon() {
    ivMute?.setImageResource(
        if (isMuted) R.drawable.ic_volume_off_24dp
        else R.drawable.ic_volume_up_24dp
    )
}
```

注意：`setNeedMute` 是 GSYVideoPlayer 基类方法，最终调用 `ExoPlayerManager.setNeedMute()`。

### 4. 高倍速列表（VideoPlayer.kt L404）

```kotlin
// 修改前
choiceSpeedDialog.initList(
    listOf(0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f).reversed(), ...

// 修改后
choiceSpeedDialog.initList(
    listOf(0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f, 5.0f, 10.0f, 15.0f).reversed(), ...
```

### 5. SettingsDialog 新增开关

- `dialog_video_settings.xml`：在 `cb_cache_play` 之后新增 `cb_mute_on_start` 开关
- `strings.xml`：新增 `<string name="mute_on_start">默认静音</string>`
- `SettingsDialog.kt`：initData 绑定 `cbMuteOnStart.isChecked = VideoPlay.muteOnStart`，initView 绑定监听器

## Architecture Decisions

### ADR-1：静音按钮放在播放器界面

- **Context**：用户需要在播放时快速切换静音
- **Facing**：仅设置中切换太麻烦，每次要退出播放器
- **We decided**：在播放器控制界面新增静音按钮
- **And selected**：复用 GSYVideoPlayer 的 `setNeedMute` 接口
- **Accepting that**：需要在播放器布局中新增按钮
- **Because**：用户体验更好，一键切换
- **Neglecting**：仅设置中切换的方案

### ADR-2：15X 不自动静音

- **Context**：15X 时音频严重失真
- **Facing**：自动静音可能让用户困惑
- **We decided**：不自动静音，让用户自行决定
- **And selected**：保留音频（虽然失真）
- **Accepting that**：15X 时音频体验差
- **Because**：用户可能只需要视频画面，可手动静音
- **Neglecting**：自动静音方案

## Data Flow

```
用户播放视频
  → VideoPlay.startPlay()
  → player.setUp(url, cachePlay, cachePath, title)
  → if (muteOnStart) player.setNeedMute(true)  // 静音
  → player.startPlayLogic()

用户点击静音按钮
  → isMuted = !isMuted
  → setNeedMute(isMuted)
  → ExoPlayerManager.setNeedMute(isMuted)
  → mediaPlayer.setVolume(0f/1f)
  → updateMuteIcon()

用户点击倍速按钮
  → showSpeedDialog()
  → 选择 15X
  → setSpeed(15.0f, true)
  → ExoPlayerManager.setSpeed(15.0f, true)
  → Exo2MediaPlayer.setSpeed(15.0f, 1f)
  → PlaybackParameters(15.0f, 1f)
```

## File Changes

| 文件 | 改动 |
|------|------|
| VideoPlay.kt | 新增 `muteOnStart` 属性 + 4 处 startPlayLogic 后设置静音 |
| VideoPlayer.kt | 新增静音按钮逻辑 + 倍速列表扩展 + isMuted 状态 |
| video_layout_controller_full.xml | 新增静音 ImageView |
| video_layout_controller.xml | 新增静音 ImageView |
| dialog_video_settings.xml | 新增"默认静音"开关 |
| SettingsDialog.kt | 绑定 muteOnStart 开关 |
| strings.xml | 新增 mute_on_start 字符串 |

## 其他格式分片缓存分析结论

用户追问"m3u8 支持分片缓存，其他格式呢？"

经源码核实 [ExoPlayerHelper.kt:95-132](../../../app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L95)，ExoPlayer 使用 `CacheDataSource.Factory` + `SimpleCache`（100MB LRU），**不区分视频格式**：
- HLS (m3u8)：缓存 TS 分片
- DASH (mpd)：缓存音视频分片
- MP4/MKV/FLV：缓存 byte range（`CacheDataSink.DEFAULT_FRAGMENT_SIZE` = 5MB 分片）

**结论：当前 `cachePlay=true` 修改已对所有视频格式生效，无需额外开发。**
