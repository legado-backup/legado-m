# 视频播放器 m3u8 边下边播缓存

> **状态**：✅ 已实施（待真机验证）
> **创建日期**：2026-07-08
> **优先级**：P2（体验增强，非阻塞）
> **核心原则**：最小改动，复用现有 cache 参数与配置体系，默认开启可关闭

---

## 一、功能概述

当前 Legado 视频播放器基于 GSYVideoPlayer（底层 ExoVideoManager = ExoPlayer），已支持 m3u8/HLS 协议播放，但 `VideoPlay.startPlay` 中 4 处 `player.setUp(url, cache, cachePath, title)` 调用的 `cache` 参数被硬编码为 `false`，导致边下边播分片缓存未启用，用户每次播放同一剧集都需重新下载全部分片。

本功能将 `cache` 参数从硬编码 `false` 改为读取 `VideoPlay.cachePlay` 配置项（默认 `true` 开启），并在视频设置对话框中新增"边下边播"开关，允许用户在需要节省存储空间时手动关闭。

### 1.1 现状锚点

| 位置 | 现状 | 行号 |
|------|------|------|
| `VideoPlay.kt` `startPlay` 单链接分支 | `player.setUp(url, false, ...)` | L150 |
| `VideoPlay.kt` `startPlay` 订阅源无 ruleContent 分支 | `player.setUp(url, false, ...)` | L181 |
| `VideoPlay.kt` `startPlay` 订阅源有 ruleContent 分支 | `player.setUp(url, false, ...)` | L215 |
| `VideoPlay.kt` `startPlay` 书籍章节分支 | `player.setUp(url, false, ...)` | L278 |
| `VideoPlay.kt` `videoPrefs` | 已有配置体系（`VIDEO_PREF_NAME = "video_config"`） | L62-64 |
| `SettingsDialog.kt` | 已有 `cbAutoPlay`/`cbStartFull`/`cbFullBottomProgress` 开关模式 | L26-45 |
| 缓存目录 | `externalCache/exoplayer`（已配置但未启用） | L150 等 |

### 1.2 改动范围

共 4 个文件：

1. `VideoPlay.kt` - 新增 `cachePlay` 属性 + 4 处 `setUp` 调用 `false` 改 `cachePlay`
2. `SettingsDialog.kt` - 新增"边下边播"开关绑定
3. `dialog_video_settings.xml` - 新增 CheckBox 行
4. `strings.xml` - 新增字符串资源 `cache_play`

---

## 二、核心能力

| 能力 | 说明 |
|------|------|
| 边下边播默认开启 | m3u8/HLS 分片缓存到 `externalCache/exoplayer`，重复播放免重新下载 |
| 用户可关闭 | 设置对话框提供开关，关闭后节省存储空间 |
| 配置持久化 | 复用现有 `videoPrefs`（SharedPreferences），与 `autoPlay` 等配置同生命周期 |
| 协议兼容 | 不改变 ExoPlayer 对 m3u8/mp4/mpd 的解析逻辑，仅控制缓存开关 |

---

## 三、文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives Considered + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / Architecture Decisions（ADR Y-Statement）/ Data Flow / File Changes |
| [tasks.md](./tasks.md) | `- [ ] X.Y` 格式任务清单 + AOAdapt 日志 |

---

## 四、预期收益

| 维度 | 当前 | 优化后 |
|------|------|--------|
| m3u8 重复播放流量 | 每次全量下载 | 命中本地缓存，仅下载未缓存分片 |
| 弱网拖动进度体验 | 每次拖动重新请求 | 命中缓存秒切 |
| 用户控制力 | 无开关 | 可关闭以节省存储 |
| 回归风险 | - | 极低（仅改 cache 布尔参数，不改播放链路） |

---

## 五、风险与约束

- **不改变播放链路**：仅切换 `setUp` 第二个布尔参数，不触碰 `ExoVideoManager`/`VideoPlayer` 内部逻辑
- **不新增依赖**：复用 GSYVideoPlayer 内置缓存能力
- **存储可控**：用户可关闭开关；缓存目录沿用既有 `externalCache/exoplayer`
- **默认值选择**：默认 `true`（开启），与"边下边播"作为主流视频 App 默认行为一致
