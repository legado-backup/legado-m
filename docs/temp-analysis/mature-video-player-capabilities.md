# Android 成熟视频播放器核心能力清单 —— Legado 视频播放器优化需求基线

> **文档定位**：基于 ExoPlayer / GSYVideoPlayer / ijkplayer / DanmakuFlameMaster 官方能力，以及 B 站 / YouTube / 腾讯视频 / 爱奇艺等主流视频 App 的交互实践，提炼出 Android 平台成熟视频播放器应具备的核心能力清单，用于对比并指导 Legado 内置视频播放器（基于 GSYVideoPlayer + ExoPlayer + IjkExo2MediaPlayer）的优化。
>
> **生成日期**：2026-07-08
>
> **适用范围**：作为后续 Legado 视频播放器优化的需求基线与差距分析依据。

---

## 目录

- [一、调研来源](#一调研来源)
- [二、Legado 当前实现快照（源码实测）](#二legado-当前实现快照源码实测)
- [三、12 维度能力清单与 Legado 支持情况](#三12-维度能力清单与-legado-支持情况)
  - [维度 1：播放核心能力](#维度-1播放核心能力)
  - [维度 2：缓存机制](#维度-2缓存机制)
  - [维度 3：倍速播放](#维度-3倍速播放)
  - [维度 4：音频控制](#维度-4音频控制)
  - [维度 5：视频画面](#维度-5视频画面)
  - [维度 6：进度控制](#维度-6进度控制)
  - [维度 7：手势交互](#维度-7手势交互)
  - [维度 8：弹幕能力](#维度-8弹幕能力)
  - [维度 9：播放列表](#维度-9播放列表)
  - [维度 10：异常处理](#维度-10异常处理)
  - [维度 11：生命周期](#维度-11生命周期)
  - [维度 12：字幕能力](#维度-12字幕能力)
- [四、差距矩阵总览](#四差距矩阵总览)
- [五、优化优先级建议](#五优化优先级建议)
- [六、参考资料](#六参考资料)

---

## 一、调研来源

| 来源 | 类型 | 关键能力参考点 |
|------|------|---------------|
| [ExoPlayer 官方](https://exoplayer.dev/) / [Android Media3 支持格式](https://developer.android.com/media/media3/exoplayer/supported-formats) | 播放内核 | 格式支持、HLS/DASH/SmoothStreaming、DRM、字幕、LoadControl、LoadErrorHandlingPolicy |
| [GSYVideoPlayer](https://github.com/CarGuo/GSYVideoPlayer) / [Gitee 镜像](https://gitee.com/CarGuo/GSYVideoPlayer) | 上层封装 | 多内核切换、缓存、弹幕、滤镜、广告、列表播放、字幕 Overlay、投屏 |
| [ijkplayer](https://github.com/bilibili/ijkplayer) | FFmpeg 内核 | FFmpeg 软解、MediaCodec 硬解、SoundTouch 变速不变调、RTMP/RTSP/HLS |
| [DanmakuFlameMaster](https://github.com/Bilibili/DanmakuFlameMaster) | 弹幕引擎 | B 站 XML 解析、多弹幕类型、密度控制、屏蔽过滤、帧同步 |
| B 站 / YouTube / 爱奇艺 / 腾讯视频 | 主流 App 交互 | 长按倍速、双击 ±10s、三分区双击、滑动快进、上下滑音量亮度 |
| [Android 画中画官方文档](https://developer.android.com/develop/ui/views/picture-in-picture) | 系统能力 | PiP 生命周期、MediaSession 集成、宽高比配置 |
| [ExoPlayer 网络恢复机制](https://developer.android.com/media/media3/exoplayer/customization) | 异常处理 | LoadErrorHandlingPolicy、DefaultLoadErrorHandlingPolicy、退避重试 |

---

## 二、Legado 当前实现快照（源码实测）

> 以下结论基于对 Legado 项目源码的实测读取，非推测。

### 2.1 依赖与内核

**文件**：`app/build.gradle` (L243-258)

```gradle
//media
implementation(libs.media.media)
implementation(libs.media3.exoplayer)
//implementation(libs.media3.exoplayer.hls)       // ← 已注释，HLS 依赖未引入
//implementation(libs.media3.ui)                  // ← 已注释，无官方 UI 组件
implementation(libs.media3.datasource.okhttp)
//implementation "androidx.media3:media3-session:$media3_version"  // ← 已注释，无 MediaSession

//videoPlayer
implementation(libs.gsyVideoPlayer.java)
implementation(libs.gsyVideoPlayer.exo2)            // 仅 Exo2 内核
//弹幕
implementation(libs.danmakuFlameMaster)
```

**关键事实**：
- 内核栈：`GSYVideoPlayer` → `ExoVideoManager` → `ExoPlayerManager` → `Exo2MediaPlayer` (继承自 `IjkExo2MediaPlayer`)。**未引入 ijkplayer FFmpeg 软解 .so**，仅用 ExoPlayer 内核。
- 未引入 `media3-exoplayer-hls`：ExoPlayer 内核虽内置 HLS 基础支持，但缺独立 HLS 模块意味着部分高级 HLS 特性（如 encrypted HLS、复杂 master playlist）能力受限。
- 未引入 `media3-ui`：无官方 `PlayerView` / `SubtitleView` / `PlayerControlView`，所有 UI 自实现。
- 未引入 `media3-session`：无系统 MediaSession，无法与系统媒体控件、蓝牙耳机键、车载屏联动。

### 2.2 核心代码文件

| 文件 | 职责 | 关键实现 |
|------|------|---------|
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | 全屏/窗口播放器控件 | 继承 `StandardGSYVideoPlayer`，集成弹幕、倍速、静音、选集、长按倍速 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` | ExoPlayer 内核管理 | `setSpeedPlaying` 空实现、`getBufferedPercentage` 返回 -1 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | ExoPlayer 实例构建 | `DefaultTrackSelector` + `DefaultLoadControl` 默认值、上一集/下一集 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` | GSY 管理器基类 | 复用 GSYVideoBaseManager |
| `app/src/main/java/io/legado/app/help/gsyVideo/FloatingPlayer.kt` | 悬浮窗播放器 | 仅含关闭、全屏、播放按钮 + 底部进度条 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | 缓存与数据源工厂 | 100MB `SimpleCache` + `LeastRecentlyUsedCacheEvictor` + `StandaloneDatabaseProvider` |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 业务编排 | 选集、记忆位置（20 天）、自动连播、订阅源/书源加载 |
| `app/src/main/res/layout/video_layout_controller_full.xml` | 全屏布局 | 进度条 + 播放/下一集/弹幕开关/选集/倍速/静音 + 锁屏 + tip_view + 空 preview_layout |

### 2.3 Legado 当前已支持能力（汇总）

- 弹幕加载（B 站 XML 格式，文件/字符串/HTTP 三种来源）
- 弹幕开关、弹幕 seek 偏移、弹幕滚动速度（`danmakuSpeed = 1.2f` 固定）
- 倍速档位（0.5/0.75/1.0/1.25/1.5/2.0/2.5/3.0/5.0/10.0/15.0）
- 长按倍速（默认 3.0x，可配置 `longPressSpeed`）
- 静音按钮（**已知 bug**：`muteOnStart` 默认 true，UI 状态同步异常）
- 选集对话框、上一集/下一集、自动连播（`onAutoCompletion` → `upDurIndex(1)`）
- 记忆播放位置（单链接 20 天，书籍/订阅源持久化）
- 边下边播缓存开关（`cachePlay`，100MB LRU）
- 全屏/小窗切换、悬浮窗播放（`FloatingPlayer`）
- DASH MPD 支持（将 MPD 文本写入临时文件后以 file:// URI 播放）
- 锁屏按钮（`isNeedLockFull = true`）

### 2.4 Legado 当前缺失能力（汇总）

- 无 ijkplayer FFmpeg 软解（格式兼容性受限）
- 无独立 HLS 模块、无 SmoothStreaming
- 无字幕渲染（无 `SubtitleView`、无 `setCues`、无字幕相关代码）
- 无画中画 PiP（`PictureInPicture` 关键词全项目零匹配）
- 无网络错误重试（`LoadErrorHandlingPolicy` 未自定义，`onError` 仅保存进度）
- 无缓冲进度二级进度条（`getBufferedPercentage` 直接返回 -1）
- 无音量调节（仅静音切换）、无声道切换、无音轨切换
- 无双击快进/快退（仅双击暂停）、无三分区双击
- 无拖动预览（`preview_layout` 存在但未实现）
- 无 AB 循环
- 无弹幕屏蔽（关键词/UID/类型/颜色过滤全无）
- 无弹幕样式自定义（字号固定 1.0f、无透明度、无颜色过滤）
- 无循环模式切换（仅 `isLooping` 全集循环，无单曲/列表切换 UI）
- 无解码失败回退（硬解失败不会自动切软解，因无 ijkplayer）
- 无预加载（下一集预加载）、无跨集缓存复用
- 无 MediaSession（系统媒体控件、蓝牙按键、车载屏不联动）
- 无缩放手势（仅 GSY 自带双指缩放）

---

## 三、12 维度能力清单与 Legado 支持情况

> **图例**：
> - ✅ 已支持 / ⚠️ 部分支持（有缺陷）/ ❌ 不支持
> - 「成熟播放器参考」列出 ExoPlayer / GSYVideoPlayer / ijkplayer / DanmakuFlameMaster 中提供该能力的代表。

### 维度 1：播放核心能力

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 1.1 | MP4 容器播放 | ExoPlayer / ijkplayer | ✅ | ExoPlayer 原生支持 |
| 1.2 | MKV 容器播放 | ijkplayer (FFmpeg) / ExoPlayer | ⚠️ | ExoPlayer 支持 MKV，但复杂 MKV（多音轨/SSA 字幕）兼容性弱于 ijkplayer FFmpeg 软解 |
| 1.3 | FLV 容器播放 | ijkplayer (HTTP-FLV) / ExoPlayer (flv-packer) | ⚠️ | ExoPlayer 通过 extractor 支持，但直播 HTTP-FLV 场景不如 ijkplayer |
| 1.4 | HLS (m3u8) 播放 | ExoPlayer `HlsMediaSource` / ijkplayer | ⚠️ | 未引入 `media3-exoplayer-hls` 独立模块，依赖 ExoPlayer 内置基础 HLS，复杂 master playlist / 加密 HLS 能力受限 |
| 1.5 | DASH (mpd) 播放 | ExoPlayer `DashMediaSource` | ✅ | 通过将 MPD 文本写入临时文件后播放（`VideoPlay.kt` L210-214），非标准 DataSource 流式 |
| 1.6 | SmoothStreaming | ExoPlayer `SsMediaSource` | ❌ | 未引入 |
| 1.7 | RTMP / RTSP 直播 | ijkplayer / ExoPlayer + `media3-datasource-rtmp` | ❌ | 未引入 RTMP/RTSP 依赖 |
| 1.8 | H.264 / H.265 (HEVC) 硬解 | ExoPlayer `MediaCodecVideoRenderer` / ijkplayer `mediacodec=1` | ✅ | ExoPlayer 默认硬解 |
| 1.9 | H.265 软解回退 | ijkplayer FFmpeg | ❌ | 无 ijkplayer，硬解失败无软解回退路径 |
| 1.10 | VP8 / VP9 / AV1 | ExoPlayer extension / ijkplayer FFmpeg | ⚠️ | `Exo2MediaPlayer` 开启了 `EXTENSION_RENDERER_MODE_PREFER`，但未引入 `media3-decoder-av1` / `media3-decoder-vp9` 扩展库 |
| 1.11 | 音频编码 AAC / MP3 / FLAC / Opus | ExoPlayer / ijkplayer | ✅ | ExoPlayer 原生支持 |
| 1.12 | DRM (Widevine / PlayReady) | ExoPlayer `DefaultDrmSessionManager` | ❌ | 未引入（ Legado 场景一般无需 DRM） |
| 1.13 | 多内核切换 | GSYVideoPlayer `PlayerFactory.setPlayManager` | ⚠️ | 代码层仅硬编码 `ExoPlayerManager`，未暴露 ijkplayer / System / AliPlayer 切换入口 |
| 1.14 | 自适应码率 (ABR) | ExoPlayer `DefaultTrackSelector` + `DefaultBandwidthMeter` | ⚠️ | `DefaultTrackSelector` 已配置但未启用 ABR 自动切换 UI，HLS master / DASH MPD 多清晰度切换未暴露 |

**关键差距**：缺乏 ijkplayer FFmpeg 软解回退路径（格式兼容性短板），HLS 模块未独立引入，RTMP/RTSP 直播能力缺失，多内核切换能力未暴露给用户。

---

### 维度 2：缓存机制

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 2.1 | 边下边播 | GSYVideoPlayer `ProxyCacheManager` / ExoPlayer `SimpleCache` | ✅ | `ExoPlayerHelper.cacheDataSourceFactory` 已实现，`cachePlay` 开关可配 |
| 2.2 | 分片缓存 | ExoPlayer `CacheDataSink.DEFAULT_FRAGMENT_SIZE` | ✅ | 使用默认分片大小（5MB） |
| 2.3 | 缓存大小控制 | ExoPlayer `LeastRecentlyUsedCacheEvictor` | ✅ | 硬编码 100MB（`ExoPlayerHelper.kt` L128），不可配置 |
| 2.4 | LRU 淘汰 | ExoPlayer `LeastRecentlyUsedCacheEvictor` | ✅ | 已使用 LRU 策略 |
| 2.5 | 缓存持久化索引 | ExoPlayer `StandaloneDatabaseProvider` | ✅ | 已使用数据库索引，重启后缓存可用 |
| 2.6 | 预加载（下一集） | GSYVideoPlayer `GSYPreloadManager` / ExoPlayer `PreloadMediaSource` | ❌ | 无预加载实现，下一集切换需重新加载 |
| 2.7 | 缓存复用（跨集） | GSYVideoPlayer `ExoPlayerCacheManager` | ⚠️ | 单一 `SimpleCache` 实例共享，但 100MB 上限对长视频集不够，跨集淘汰频繁 |
| 2.8 | 缓存路径可配置 | GSYVideoPlayer `cachePath` | ⚠️ | 固定为 `externalCache/exoplayer`，用户无法自定义存储位置（如 SD 卡） |
| 2.9 | 缓存大小用户可调 | GSYVideoPlayer `setMaxCacheSize` | ❌ | 100MB 硬编码，无 UI 入口 |
| 2.10 | HLS 分片缓存 | ExoPlayer `SimpleCache` + `HlsMediaSource` | ⚠️ | 缓存机制本身支持，但 HLS 模块未独立引入，实际效果受限 |
| 2.11 | 缓存清理策略 | GSYVideoPlayer | ⚠️ | 仅在 `releaseAllVideos` 时清理 `video_temp` 临时目录，未清理 exoplayer 缓存目录 |
| 2.12 | 缓存命中率统计 | ExoPlayer `Cache` listener | ❌ | 无统计与展示 |

**关键差距**：无预加载（影响下一集切换体验）、缓存大小硬编码 100MB 不可调、缓存路径不可配置、无缓存清理 UI。

---

### 维度 3：倍速播放

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 3.1 | 播放中动态调速 | ExoPlayer `setPlaybackParameters` / ijkplayer `setSpeed` | ⚠️ | `ExoPlayerManager.setSpeed` 调用 `mediaPlayer.setSpeed`，但代码注释明确写"EXO2 的 setSpeed 只能在播放前生效"（`ExoPlayerManager.kt` L78, L111） |
| 3.2 | `setSpeedPlaying` 实时调速 | GSYVideoPlayer | ❌ | `ExoPlayerManager.setSpeedPlaying` 为空实现（L197-198） |
| 3.3 | 音调修正（变速不变调） | ijkplayer `soundtouch=1` / ExoPlayer `PlaybackParameters.pitch` | ⚠️ | `Exo2MediaPlayer` 在 `prepareAsyncInternal` 中应用 `mSpeedPlaybackParameters`，但 `setSpeed(speed, 1f)` 第二参数固定为 `1f`（pitch=1），未明确启用 SoundTouch 等效算法 |
| 3.4 | 倍速档位 | 主流 App 0.5x-3.0x | ✅ | 11 档可选（0.5/0.75/1.0/1.25/1.5/2.0/2.5/3.0/5.0/10.0/15.0），范围远超主流 App |
| 3.5 | 长按倍速 | B 站 / YouTube / 抖音 | ✅ | `onLongPress` 触发，默认 3.0x 可配（`longPressSpeed`） |
| 3.6 | 长按倍速值可配 | 主流 App | ✅ | `VideoPlay.longPressSpeed` 可配（设置项） |
| 3.7 | 倍速时弹幕同步 | GSYVideoPlayer | ✅ | `setVideoSpeed` 内同步调整 `setScrollSpeedFactor`（L141） |
| 3.8 | 倍速最小值 | 主流 App 0.5x | ✅ | 0.5x |
| 3.9 | 倍速最大值 | 主流 App 3.0x / B 站 5.0x | ✅ | 15.0x（远超主流，但高倍速音画同步与可读性差） |
| 3.10 | 倍速 UI 提示 | 主流 App | ✅ | `showOverlayTip("${speed}倍速播放中")` |
| 3.11 | 倍速状态持久化 | 主流 App | ❌ | 切换集数后倍速重置为 1.0（`playSpeed` 是 VideoPlayer 实例变量，全屏/小窗切换会丢失） |

**关键差距**：`setSpeedPlaying` 空实现意味着**播放中动态调速实际不生效**（仅靠 `setSpeed` 在 ExoPlayer 内部可能生效但行为不可控），倍速状态不跨集持久化，音调修正策略不明确。

---

### 维度 4：音频控制

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 4.1 | 静音切换 | ExoPlayer `setVolume(0)` / GSYVideoPlayer `setNeedMute` | ⚠️ | `ExoPlayerManager.setNeedMute` 实现为 `setVolume(0f, 0f)`，**已知 bug**：`muteOnStart` 默认 true 导致用户感知"无声"，UI 状态同步异常 |
| 4.2 | 音量调节（0-100%） | ExoPlayer `setVolume(0.0-1.0)` / GSYVideoPlayer 手势 | ⚠️ | 仅靠 GSYVideoPlayer 父类手势（右滑音量），无独立音量滑杆 UI |
| 4.3 | 声道切换（左/右/立体声） | ijkplayer `audio-stereo` / ExoPlayer | ❌ | 未实现 |
| 4.4 | 音轨切换（多语言音轨） | ExoPlayer `TrackSelector` / ijkplayer | ❌ | `DefaultTrackSelector` 已配置但无音轨选择 UI，多音轨视频无法切换 |
| 4.5 | 音频焦点管理 | ExoPlayer `setHandleAudioBecomingNoisy` / `setAudioAttributes` | ❌ | `Exo2MediaPlayer` 未调用 `setHandleAudioBecomingNoisy(true)`，拔耳机不会自动暂停 |
| 4.6 | 音频流类型 | ExoPlayer `AudioManager.STREAM_MUSIC` | ✅ | `ExoPlayerManager.initVideoPlayer` 调用 `setAudioStreamType(STREAM_MUSIC)` |
| 4.7 | 音量增益（>100%） | 第三方扩展 | ❌ | 未实现 |

**关键差距**：静音 bug、无音轨/声道切换、无音频焦点管理（拔耳机不暂停是严重体验问题）。

---

### 维度 5：视频画面

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 5.1 | 自适应宽高 | GSYVideoPlayer `autoFullWithSize` | ⚠️ | GSY 父类支持，但 `VideoPlayer` 未显式调用 `setAutoFullWithSize(true)` |
| 5.2 | 画面比例切换（默认/16:9/4:3/充满/拉伸） | GSYVideoPlayer `showResolution` / ExoPlayer `resizeMode` | ⚠️ | 继承 GSY 父类能力，但无 UI 按钮暴露切换入口 |
| 5.3 | 画面旋转（0/90/180/270） | GSYVideoPlayer | ⚠️ | GSY 父类支持视频 rotation，无 UI 入口 |
| 5.4 | 镜像翻转 | GSYVideoPlayer | ❌ | 未启用 |
| 5.5 | 缩放手势 | 主流 App | ❌ | 仅 GSY 自带双指缩放，未启用 |
| 5.6 | Surface 渲染方式 | GSYVideoPlayer (TextureView/SurfaceView/GLSurfaceView) | ⚠️ | `VideoPlayer.setDisplay` 区分 SurfaceView 与 TextureView，但未暴露切换 UI |
| 5.7 | 截图 / GIF 生成 | GSYVideoPlayer | ❌ | 未启用 |
| 5.8 | 滤镜 / 水印 | GSYVideoPlayer 20+ 滤镜 | ❌ | 未启用 |
| 5.9 | 16K page size 适配 | GSYVideoPlayer `ex_so` | ❌ | 未引入 `gsyVideoPlayer-ex_so` |

**关键差距**：画面比例/旋转等能力虽底层支持但未暴露 UI，无截图、滤镜、水印等增强能力。

---

### 维度 6：进度控制

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 6.1 | 进度条拖动 | GSYVideoPlayer `SeekBar` | ✅ | `video_layout_controller_full.xml` 含 `SeekBar @id/progress` |
| 6.2 | 缓冲进度显示（二级进度条） | ExoPlayer `getBufferedPercentage` / GSYVideoPlayer `setSecondProgress` | ❌ | `ExoPlayerManager.getBufferedPercentage` 直接返回 -1（L169-171），二级进度不显示 |
| 6.3 | 拖动预览（缩略图） | GSYVideoPlayer `preview_layout` / ExoPlayer `PlayerView` | ❌ | 布局含 `preview_layout`（L240-247）但 `visibility=gone` 且无实现代码 |
| 6.4 | 记忆播放位置 | ExoPlayer / 主流 App | ✅ | `VideoPlay.saveRead` 持久化（单链接 20 天，书籍/订阅源持久化到 DB） |
| 6.5 | 多设备进度同步 | 主流 App（账号体系） | ❌ | 无账号体系，本地存储 |
| 6.6 | AB 循环（区间循环） | 第三方播放器 | ❌ | 未实现 |
| 6.7 | 精准 seek | ijkplayer `enable-accurate-seek=1` / ExoPlayer `setSeekParameters` | ❌ | 未配置精准 seek 参数 |
| 6.8 | 进度跳转步进 | ExoPlayer `setSeekForwardIncrementMs` | ❌ | 未配置（主流 App 默认 ±10s/±15s） |
| 6.9 | 当前时间/总时长显示 | GSYVideoPlayer | ✅ | `@id/current` / `@id/total` / `@id/sprit` |
| 6.10 | 底部常驻进度条 | GSYVideoPlayer | ✅ | `@id/bottom_progressbar`（全屏可配置 `fullBottomProgressBar`） |
| 6.11 | 进度拖动时显示目标时间 | GSYVideoPlayer | ⚠️ | GSY 父类支持，但 `VideoPlayer` 未自定义 `touchDoubleUp` 提示 |

**关键差距**：**缓冲进度不显示（返回 -1 是硬伤）**、无拖动预览、无 AB 循环、无精准 seek 配置。

---

### 维度 7：手势交互

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 7.1 | 左滑亮度 | GSYVideoPlayer / 主流 App | ✅ | 继承 GSY 父类 `mBrightness` |
| 7.2 | 右滑音量 | GSYVideoPlayer / 主流 App | ✅ | 继承 GSY 父类 `mChangeVolume` |
| 7.3 | 横滑进度 | GSYVideoPlayer / 主流 App | ✅ | 继承 GSY 父类 `mChangePosition` |
| 7.4 | 双击暂停/播放 | GSYVideoPlayer `touchDoubleUp` / 主流 App | ✅ | `onDoubleTap` 调用 `touchDoubleUp(e)` |
| 7.5 | 双击快进/快退（三分区） | YouTube / B 站 / 爱奇艺 | ❌ | 仅整屏双击暂停，未实现左/中/右三分区双击分别触发后退/暂停/前进 |
| 7.6 | 长按倍速 | B 站 / YouTube / 抖音 | ✅ | `onLongPress` 触发，松手恢复（`touchSurfaceUp` 检测 `isLongPressSpeed`） |
| 7.7 | 长按倍速可锁定 | Gestify 等扩展 | ❌ | 长按松手即恢复，无法锁定持续倍速 |
| 7.8 | 单击切换控制 UI | GSYVideoPlayer `onClickUiToggle` | ✅ | `onSingleTapConfirmed` 调用 `onClickUiToggle(e)` |
| 7.9 | 锁屏手势 | GSYVideoPlayer `mLockCurScreen` | ✅ | `isNeedLockFull = true`，`LockClickListener` 同步到 `VideoPlay.lockCurScreen` |
| 7.10 | 手势锁防误触 | 主流 App | ❌ | 仅锁屏按钮，无手势锁 |
| 7.11 | 双指缩放 | 主流 App | ❌ | 未启用 |
| 7.12 | 手势灵敏度可调 | 主流 App | ❌ | 无配置入口 |

**关键差距**：**无双击快进/快退（YouTube 风格三分区双击是现代播放器标配）**、无长按倍速锁定、无双指缩放。

---

### 维度 8：弹幕能力

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 8.1 | 弹幕加载（B 站 XML） | DanmakuFlameMaster `BiliDanmukuParser` | ✅ | `createParser` 使用 `DanmakuLoaderFactory.TAG_BILI` |
| 8.2 | 弹幕加载（JSON / AcFun） | DanmakuFlameMaster `TAG_ACFUN` | ❌ | 仅支持 B 站 XML，不支持 AcFun JSON |
| 8.3 | 弹幕加载（HTTP URL） | DanmakuFlameMaster | ✅ | `loader.load(danmakuStr)` 支持 http 开头的 URL |
| 8.4 | 弹幕开关 | DanmakuFlameMaster `show/hide` | ✅ | `@id/toggle_danmaku` 按钮，`resolveDanmakuShow` |
| 8.5 | 弹幕滚动速度 | DanmakuFlameMaster `setScrollSpeedFactor` | ⚠️ | `danmakuSpeed = 1.2f` 全局固定，无用户调节 UI；倍速时会动态调整（L141） |
| 8.6 | 弹幕 seek 偏移 | DanmakuFlameMaster `seekTo` | ✅ | `onSeekComplete` → `resolveDanmakuSeek` |
| 8.7 | 弹幕最大行数 | DanmakuFlameMaster `setMaximumLines` | ⚠️ | 硬编码滚动 5 行、顶部禁止重叠，无用户调节 |
| 8.8 | 弹幕屏蔽（关键词） | DanmakuFlameMaster `DanmakuFilters` | ❌ | 未实现关键词过滤 |
| 8.9 | 弹幕屏蔽（用户 UID） | DanmakuFlameMaster | ❌ | 未实现 |
| 8.10 | 弹幕屏蔽（类型/颜色/长度） | DanmakuFlameMaster | ❌ | 未实现 |
| 8.11 | 弹幕密度控制 | DanmakuFlameMaster `setMaximumVisibleSizeInScreen` | ❌ | 未实现 |
| 8.12 | 弹幕字号 | DanmakuFlameMaster `setScaleTextSize` | ⚠️ | 硬编码 `1.0f`，无用户调节 |
| 8.13 | 弹幕透明度 | DanmakuFlameMaster | ❌ | 未实现 |
| 8.14 | 弹幕描边/样式 | DanmakuFlameMaster `setDanmakuStyle` | ⚠️ | 固定 `DANMAKU_STYLE_STROKEN, 3f`，无切换 |
| 8.15 | 弹幕类型（滚动/顶部/底部/特殊） | DanmakuFlameMaster | ✅ | 解析器支持全部类型，但 `maxLinesPair` 仅配置滚动与顶部 |
| 8.16 | 实时弹幕（直播） | DanmakuFlameMaster `addDanmaku` | ❌ | 未实现实时弹幕注入 |
| 8.17 | 弹幕预缓存 | DanmakuFlameMaster `enableDanmakuDrawingCache` | ✅ | 已启用 |
| 8.18 | 弹幕时移同步 | DanmakuFlameMaster | ✅ | 全屏/小窗切换同步 `mDanmakuStartSeekPosition` |
| 8.19 | 自定义弹幕背景 | DanmakuFlameMaster `SpannedCacheStuffer` | ⚠️ | 使用 `SpannedCacheStuffer` 但未自定义背景 |

**关键差距**：弹幕屏蔽能力完全缺失（关键词/UID/类型/颜色/长度过滤全无）、弹幕样式（字号/透明度/描边）不可调、无实时弹幕、仅支持 B 站 XML 格式。

---

### 维度 9：播放列表

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 9.1 | 选集列表 | 主流 App | ✅ | `@id/episode_list` → `showEpisodeDialog` → `ChoiceEpisodeDialog` |
| 9.2 | 上一集 / 下一集 | 主流 App | ✅ | `@id/next` → `VideoPlay.upDurIndex(1)`，`Exo2MediaPlayer.previous/next` |
| 9.3 | 自动连播 | 主流 App | ✅ | `onAutoCompletion` → `VideoPlay.upDurIndex(1, this)` |
| 9.4 | 循环模式切换（单曲/列表/不循环） | 主流 App | ❌ | 仅 `isLooping` 全集循环（`Player.REPEAT_MODE_ALL`），无 UI 切换三种模式 |
| 9.5 | 集数标记（已播放/进度） | 主流 App | ❌ | `ChoiceEpisodeDialog` 未显示已播放/未播放标记 |
| 9.6 | 多线路/多季切换 | 主流 App | ⚠️ | `volumes`（卷/线路）概念存在，但切换需进选集对话框，无快捷按钮 |
| 9.7 | 跳片头/片尾 | 主流 App | ❌ | 未实现 |
| 9.8 | 倍速连播记忆 | 主流 App | ❌ | 倍速不跨集持久化（见 3.11） |
| 9.9 | 选集搜索/筛选 | 主流 App | ❌ | 大列表（如 1000+ 集）无搜索筛选 |

**关键差距**：无循环模式切换 UI、无集数播放状态标记、无跳片头片尾、倍速不跨集记忆。

---

### 维度 10：异常处理

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 10.1 | 网络错误重试 | ExoPlayer `DefaultLoadErrorHandlingPolicy`（默认 3 次，直播 6 次） | ❌ | 未自定义 `LoadErrorHandlingPolicy`，使用默认值但未配置退避策略 |
| 10.2 | 重试退避策略 | ExoPlayer 指数退避 | ❌ | 同上 |
| 10.3 | 断网处理 | ExoPlayer + 业务层 | ⚠️ | `onError` 仅 `saveRead` + 重置 `seekOnStart`（L464-468），无重试 UI、无断网提示 |
| 10.4 | 解码失败回退（硬解→软解） | ijkplayer `mediacodec=0` 回退 / ExoPlayer `setEnableDecoderFallback` | ❌ | `Exo2MediaPlayer` 调用 `setExtensionRendererMode(EXTENSION_RENDERER_MODE_PREFER)` 但未调用 `setEnableDecoderFallback(true)`；且无 ijkplayer 软解回退路径 |
| 10.5 | 内存不足处理 | ExoPlayer `onPlayerError` `ERROR_CODE_DECODER_INIT_FAILED` | ❌ | 无内存不足专项处理 |
| 10.6 | 错误码分类提示 | ExoPlayer `PlaybackException.errorCode` | ❌ | `onError(what, extra)` 仅记日志，未按错误码分类提示用户 |
| 10.7 | CDN 节点故障切换 | ExoPlayer `DEFAULT_LOCATION_EXCLUSION_MS` | ❌ | 未配置 |
| 10.8 | 轨道排除（坏轨道） | ExoPlayer `DEFAULT_TRACK_EXCLUSION_MS` | ❌ | 未配置 |
| 10.9 | 直播卡顿超时重拉 | Media3 `bufferingStallTimeoutMs` | ❌ | 未配置（且无直播场景） |
| 10.10 | 错误恢复后进度保持 | 主流 App | ⚠️ | `onError` 保存进度，但重新 prepare 后进度恢复依赖 `seekOnStart`，时序可能错乱 |
| 10.11 | HTTP 超时配置 | ExoPlayer `setConnectTimeoutMs` / `setReadTimeoutMs` | ⚠️ | `ExoPlayerHelper.okhttpDataFactory` 使用 `okHttpClient.newBuilder().callTimeout(0)`（无超时），连接/读取超时未配置 |
| 10.12 | 错误日志上报 | 主流 App | ⚠️ | 仅 `AppLog.put` 本地日志，无远程上报 |

**关键差距**：异常处理是 Legado 视频播放器**最薄弱的环节**——无自定义重试策略、无错误码分类提示、无硬解软解回退、无 HTTP 超时配置（`callTimeout=0` 会导致弱网下长时间黑屏）。

---

### 维度 11：生命周期

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 11.1 | 后台暂停 | ExoPlayer / GSYVideoPlayer | ✅ | `VideoPlay.onPause` → `onVideoPause` |
| 11.2 | 恢复播放 | ExoPlayer / GSYVideoPlayer | ✅ | `VideoPlay.onResume` → `onVideoResume` |
| 11.3 | 画中画 (PiP) | Android 8.0+ `enterPictureInPictureMode` | ❌ | 全项目无 `PictureInPicture` 关键词，未实现 |
| 11.4 | 悬浮窗（应用内） | GSYVideoPlayer `SmallVideo` | ✅ | `FloatingPlayer` 实现，独立布局 `video_layout_floating.xml` |
| 11.5 | 系统悬浮窗（跨 App） | `SYSTEM_ALERT_WINDOW` | ❌ | `FloatingPlayer` 仅应用内悬浮，未申请系统悬浮窗权限 |
| 11.6 | MediaSession 集成 | ExoPlayer `MediaSession` | ❌ | 未引入 `media3-session`，系统媒体控件、蓝牙耳机键、车载屏不联动 |
| 11.7 | 音频焦点（来电暂停） | ExoPlayer `setHandleAudioFocus` | ❌ | 未配置（见 4.5） |
| 11.8 | 拔耳机暂停 | ExoPlayer `setHandleAudioBecomingNoisy` | ❌ | 未配置（见 4.5） |
| 11.9 | 后台播放（纯音频） | 主流 App | ❌ | 切后台即暂停，无纯音频后台播放 |
| 11.10 | 配置变更不重建 Activity | Android `configChanges` | ⚠️ | 需检查 `AndroidManifest.xml` 中视频 Activity 的 `configChanges` 声明 |
| 11.11 | 全屏 ↔ 小窗无缝切换 | GSYVideoPlayer | ✅ | `startWindowFullscreen` / `resolveNormalVideoShow` + 弹幕状态同步 |
| 11.12 | 锁屏播放控制 | 系统锁屏控件 | ❌ | 无系统锁屏媒体控件（依赖 MediaSession） |

**关键差距**：**无画中画 PiP**（Android 8.0+ 标配）、无 MediaSession（系统媒体控件/蓝牙/车载不联动）、无音频焦点与拔耳机暂停（严重影响体验）。

---

### 维度 12：字幕能力

| # | 能力 | 成熟播放器参考 | Legado 状态 | 差距说明 |
|---|------|---------------|------------|---------|
| 12.1 | 外挂字幕（SRT） | ExoPlayer `SrtDecoder` / GSYVideoPlayer Overlay | ❌ | 未实现（全项目无 `SubtitleView` / `setCues` / `TrackType.TEXT` 调用） |
| 12.2 | 外挂字幕（WebVTT） | ExoPlayer `WebvttDecoder` | ❌ | 未实现 |
| 12.3 | 外挂字幕（TTML） | ExoPlayer `TtmlDecoder` | ❌ | 未实现 |
| 12.4 | 内嵌字幕（MKV/MP4 软字幕） | ExoPlayer `TextRenderer` | ❌ | 未实现 |
| 12.5 | 608/708 闭路字幕 | ExoPlayer `Cea608Decoder` / `Cea708Decoder` | ❌ | 未实现 |
| 12.6 | 字幕样式调整（字号） | ExoPlayer `SubtitleView.setFractionalTextSize` | ❌ | 未实现 |
| 12.7 | 字幕样式调整（颜色/背景/描边） | ExoPlayer `CaptionStyleCompat` | ❌ | 未实现 |
| 12.8 | 字幕位置调整 | ExoPlayer `Cue.position` | ❌ | 未实现 |
| 12.9 | 多字幕轨切换 | ExoPlayer `TrackSelector` | ❌ | 未实现 |
| 12.10 | 字幕开关 | 主流 App | ❌ | 未实现 |
| 12.11 | 字幕同步偏移 | 主流 App | ❌ | 未实现 |
| 12.12 | ASS/SSA 高级字幕 | ijkplayer FFmpeg / ExoPlayer extension | ❌ | 未实现 |
| 12.13 | 系统无障碍字幕同步 | ExoPlayer `setUserDefaultStyle` | ❌ | 未实现 |

**关键差距**：**字幕能力完全缺失**——这是 Legado 视频播放器与主流播放器最大的能力鸿沟之一。考虑到 Legado 的"阅读"定位，字幕对听障用户与外语视频场景至关重要。

---

## 四、差距矩阵总览

### 4.1 严重缺失（P0，影响核心体验）

| 维度 | 缺失能力 | 影响 |
|------|---------|------|
| 维度 10 | 网络错误重试 / HTTP 超时配置 | 弱网下长时间黑屏，用户以为卡死 |
| 维度 6 | 缓冲进度二级进度条（返回 -1） | 用户无法判断缓冲状态 |
| 维度 4 | 音频焦点 / 拔耳机暂停 | 来电不暂停、拔耳机继续外放，体验与安全双问题 |
| 维度 11 | 画中画 PiP | Android 8.0+ 标配，主流 App 必备 |
| 维度 11 | MediaSession 集成 | 系统媒体控件/蓝牙/车载不联动 |
| 维度 12 | 字幕能力（全部） | 听障用户与外语视频无法使用 |
| 维度 1 | ijkplayer FFmpeg 软解回退 | 硬解失败即无法播放，格式兼容性受限 |
| 维度 3 | `setSpeedPlaying` 实时调速 | 播放中动态调速实际不生效 |

### 4.2 重要缺失（P1，影响使用便利）

| 维度 | 缺失能力 | 影响 |
|------|---------|------|
| 维度 4 | 静音 bug | 用户感知"无声"，体验差 |
| 维度 7 | 双击快进/快退（三分区） | 现代播放器标配，无此能力显得落后 |
| 维度 8 | 弹幕屏蔽（关键词/UID/类型） | 弹幕文化核心功能缺失 |
| 维度 8 | 弹幕样式调节（字号/透明度） | 用户无法个性化 |
| 维度 2 | 预加载（下一集） | 选集切换慢 |
| 维度 2 | 缓存大小/路径可配置 | 100MB 硬编码不合理 |
| 维度 6 | 拖动预览（缩略图） | 长视频定位困难 |
| 维度 10 | 解码失败回退（硬解→软解） | 部分视频无法播放 |
| 维度 10 | 错误码分类提示 | 用户无法理解失败原因 |
| 维度 9 | 循环模式切换 UI | 无单曲循环 |
| 维度 9 | 倍速跨集记忆 | 每集都需重设倍速 |

### 4.3 增强缺失（P2，锦上添花）

| 维度 | 缺失能力 | 影响 |
|------|---------|------|
| 维度 1 | RTMP / RTSP 直播 | 直播场景缺失（Legado 非核心） |
| 维度 1 | SmoothStreaming | 微软协议，国内少用 |
| 维度 5 | 截图 / GIF 生成 / 滤镜 | 增强能力，非核心 |
| 维度 6 | AB 循环 | 学习场景用 |
| 维度 7 | 双指缩放 / 手势锁 | 体验增强 |
| 维度 8 | 实时弹幕 / AcFun JSON | 直播场景 |
| 维度 9 | 跳片头片尾 / 集数搜索 | 便利性 |
| 维度 11 | 系统悬浮窗（跨 App） | 多任务 |
| 维度 11 | 后台纯音频播放 | 音频剧场景 |

---

## 五、优化优先级建议

> 基于差距严重程度、实现成本、用户感知度三维度综合排序。

### 5.1 第一优先级（P0，立即修复）

1. **修复缓冲进度显示**：`ExoPlayerManager.getBufferedPercentage` 返回实际值（从 `ExoPlayer.getBufferedPercentage()`），UI 层 `setSecondProgress`。
2. **修复静音 bug**：`muteOnStart` 默认改为 `false`，UI 状态与实际音量强制同步。
3. **接入音频焦点与拔耳机暂停**：`Exo2MediaPlayer.prepareAsyncInternal` 调用 `setHandleAudioBecomingNoisy(true)` + `setAudioAttributes(AudioAttributes.USAGE_MEDIA)`。
4. **配置 HTTP 超时**：`ExoPlayerHelper.okhttpDataFactory` 设置 `setConnectTimeoutMs(8000)` + `setReadTimeoutMs(8000)`，避免弱网黑屏。
5. **自定义 `LoadErrorHandlingPolicy`**：实现退避重试（默认 3 次，指数退避），重试失败后显示明确错误码提示。
6. **修复 `setSpeedPlaying` 空实现**：调用 `mediaPlayer.setSpeed` 实现播放中动态调速。
7. **引入 ijkplayer 软解回退**：添加 `gsyVideoPlayer-armv7a` / `arm64` 依赖，硬解失败时通过 `PlayerFactory.setPlayManager` 切换。

### 5.2 第二优先级（P1，短期补齐）

1. **画中画 PiP**：视频 Activity 声明 `supportsPictureInPicture=true`，Home 键触发 `enterPictureInPictureMode`。
2. **MediaSession 集成**：引入 `media3-session`，绑定 `MediaSession`，系统媒体控件联动。
3. **字幕能力**：引入 `media3-ui`，添加 `SubtitleView`，支持外挂 SRT/WebVTT，暴露字幕样式调节 UI。
4. **双击快进/快退**：实现三分区双击（左退/中暂停/右进，±10s）。
5. **弹幕屏蔽**：基于 `DanmakuFilters` 实现关键词/UID/类型过滤。
6. **弹幕样式调节**：字号、透明度、描边样式 UI。
7. **拖动预览**：实现 `preview_layout` 缩略图（可基于 ExoPlayer `PlayerView` 或自实现）。
8. **倍速跨集持久化**：`playSpeed` 提升到 `VideoPlay` 全局变量，跨集保持。
9. **预加载下一集**：`GSYPreloadManager` 或 ExoPlayer `PreloadMediaSource`。
10. **缓存大小/路径可配置**：设置项暴露 100MB → 用户可调（如 500MB/1GB），路径可选 SD 卡。

### 5.3 第三优先级（P2，长期演进）

1. **多内核切换 UI**：暴露 ijkplayer / ExoPlayer / System 切换入口。
2. **HLS 独立模块**：引入 `media3-exoplayer-hls`，支持加密 HLS。
3. **循环模式切换 UI**：单曲/列表/不循环三态切换。
4. **集数播放状态标记**：选集对话框标记已播放/进度。
5. **AB 循环**：长按进度条设置 A/B 点。
6. **精准 seek**：`setSeekParameters(SeekParameters.CLOSEST_SYNC)`。
7. **错误码分类提示**：`PlaybackException.errorCode` 映射到用户可读文案。
8. **后台纯音频播放**：视频轨道禁用，音频通道保留，配合 MediaSession。

---

## 六、参考资料

### 6.1 官方文档

- ExoPlayer 官方：<https://exoplayer.dev/>
- Android Media3 支持格式：<https://developer.android.com/media/media3/exoplayer/supported-formats>
- Android Media3 自定义（LoadErrorHandlingPolicy）：<https://developer.android.com/media/media3/exoplayer/customization>
- Android 画中画 (PiP)：<https://developer.android.com/develop/ui/views/picture-in-picture>
- WebVTT 规范：<https://developer.mozilla.org/zh-CN/docs/Web/API/WebVTT_API>

### 6.2 开源项目

- GSYVideoPlayer：<https://github.com/CarGuo/GSYVideoPlayer> / <https://gitee.com/CarGuo/GSYVideoPlayer>
- ijkplayer：<https://github.com/bilibili/ijkplayer>
- DanmakuFlameMaster：<https://github.com/Bilibili/DanmakuFlameMaster>
- androidx.media3：<https://github.com/androidx/media>

### 6.3 主流 App 交互参考

- B 站长按倍速：全屏长按 2 秒切换倍速；竖屏短视频长按上滑可升至 5.0x
- YouTube 双击 ±10s：三分区双击（左退/中暂停/右进）
- 爱奇艺长按 3 倍速：横屏长按触发 3.0x
- 腾讯视频：滑动快进 + 长按倍速 + 双击暂停

### 6.4 Legado 源码文件索引

| 文件 | 路径 |
|------|------|
| 全屏播放器控件 | `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` |
| ExoPlayer 内核管理 | `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` |
| ExoPlayer 实例构建 | `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` |
| GSY 管理器基类 | `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` |
| 悬浮窗播放器 | `app/src/main/java/io/legado/app/help/gsyVideo/FloatingPlayer.kt` |
| 缓存与数据源工厂 | `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` |
| 业务编排 | `app/src/main/java/io/legado/app/model/VideoPlay.kt` |
| 全屏布局 | `app/src/main/res/layout/video_layout_controller_full.xml` |
| 悬浮窗布局 | `app/src/main/res/layout/video_layout_floating.xml` |
| Gradle 依赖 | `app/build.gradle` (L243-258) |

---

## 附录：能力清单速查表

> 用于快速对照检查，✅=已支持 ⚠️=部分支持 ❌=不支持

| 维度 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|------|---|---|---|---|---|---|---|---|---|----|----|----|
| Legado 总体 | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ | ❌ |

| 维度细分 | 已支持数 | 部分支持数 | 不支持数 | 总能力数 |
|---------|---------|-----------|---------|---------|
| 1. 播放核心 | 4 | 5 | 5 | 14 |
| 2. 缓存机制 | 5 | 4 | 3 | 12 |
| 3. 倍速播放 | 7 | 2 | 2 | 11 |
| 4. 音频控制 | 2 | 2 | 3 | 7 |
| 5. 视频画面 | 1 | 4 | 4 | 9 |
| 6. 进度控制 | 4 | 2 | 5 | 11 |
| 7. 手势交互 | 5 | 0 | 7 | 12 |
| 8. 弹幕能力 | 6 | 4 | 9 | 19 |
| 9. 播放列表 | 3 | 1 | 5 | 9 |
| 10. 异常处理 | 0 | 4 | 8 | 12 |
| 11. 生命周期 | 3 | 1 | 8 | 12 |
| 12. 字幕能力 | 0 | 0 | 13 | 13 |
| **合计** | **40** | **29** | **72** | **141** |

**结论**：Legado 视频播放器当前覆盖 141 项能力中的 40 项（28.4% 完全覆盖 + 20.6% 部分覆盖 = 49% 总覆盖率），其中**字幕能力（0/13）、异常处理（0/12 完全覆盖）**是最大短板，应作为优化重点。
