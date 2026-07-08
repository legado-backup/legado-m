# spec.md - 视频播放器 m3u8 边下边播缓存

> **状态**：🔄 设计中
> **创建日期**：2026-07-08

---

## 一、Intent（意图）

### 1.1 业务意图

Legado 视频播放器已支持 m3u8/HLS 协议播放，但 `VideoPlay.startPlay` 中 4 处 `player.setUp(url, cache, cachePath, title)` 调用的 `cache` 参数硬编码为 `false`，导致 GSYVideoPlayer 内置的边下边播分片缓存能力未被启用。用户每次重复播放同一剧集、或在进度条上拖动时，均需重新下载全部分片，浪费流量且弱网下体验差。

本次意图：将 `cache` 参数改为读取 `VideoPlay.cachePlay` 配置项（默认 `true` 开启），并提供用户可关闭的开关，让用户在需要节省存储空间时手动关闭。

### 1.2 衡量标准

| 指标 | 当前 | 目标 |
|------|------|------|
| `setUp` cache 参数 | 硬编码 `false`（4 处） | 读取 `VideoPlay.cachePlay`（4 处） |
| 边下边播开关 | 无 | 设置对话框新增，默认开启 |
| 配置持久化 | 无 | SharedPreferences（`video_config`） |
| 回归风险 | - | 极低，仅切换布尔参数 |

---

## 二、Scope（范围）

### 2.1 In Scope（本次实施）

| 编号 | 改动 | 文件 | 锚点 |
|------|------|------|------|
| S1 | 新增 `cachePlay` 属性 | `app/src/main/java/io/legado/app/model/VideoPlay.kt` | `videoPrefs` 块内（L62-88 区域） |
| S2 | 4 处 `setUp` 调用 `false` → `cachePlay` | `VideoPlay.kt` | L150 / L181 / L215 / L278 |
| S3 | 新增"边下边播"CheckBox 绑定 | `app/src/main/java/io/legado/app/ui/video/config/SettingsDialog.kt` | `initData` + `initView` |
| S4 | 新增 CheckBox 行 | `app/src/main/res/layout/dialog_video_settings.xml` | 末尾 `tv_press_speed` 之前 |
| S5 | 新增字符串资源 | `app/src/main/res/values/strings.xml`（含 `values-zh`/`values-en` 如有） | `cache_play` |

### 2.2 Out of Scope（本次不实施）

- **不**修改 `ExoVideoManager` / `VideoPlayer` / `FloatingPlayer` 内部播放逻辑
- **不**修改 `GSYVideoPlayer` 库代码或升级 GSY 版本
- **不**新增缓存清理入口（沿用既有 `externalCache/exoplayer` 目录，系统清理缓存时一并清除）
- **不**做缓存大小限制配置（GSYVideoPlayer 内部已管理缓存淘汰，本功能不引入额外限制）
- **不**做缓存命中率统计/日志埋点
- **不**修改 mpd/mp4 播放路径（cache 参数对非 HLS 协议同样生效，但本次不针对其单独处理）

---

## 三、Approach（方案）

### 3.1 主方案：复用 GSYVideoPlayer cache 参数 + videoPrefs 配置

#### 3.1.1 核心思路

GSYVideoPlayer 的 `setUp(url, cache, cachePath, title)` 第二参数 `cache` 已是现成的边下边播开关，且缓存目录 `cachePath` 已配置为 `externalCache/exoplayer`。无需引入任何新依赖，只需：

1. 在 `VideoPlay` 中仿照 `autoPlay` 模式新增 `cachePlay` 属性，读写 `videoPrefs.getBoolean("cachePlay", true)`
2. 将 4 处 `setUp` 调用的第二参数 `false` 替换为 `cachePlay`
3. 在 `SettingsDialog` 中仿照 `cbAutoPlay` 模式新增"边下边播"CheckBox
4. 在 `dialog_video_settings.xml` 中新增对应 CheckBox 行
5. 在 `strings.xml` 中新增 `cache_play` 字符串

#### 3.1.2 默认值选择

`cachePlay` 默认 `true`（开启）。理由：
- 主流视频 App（B 站、YouTube 等）边下边播默认开启
- Legado 用户重复播放同一剧集是常见场景（追剧、复习）
- 节省存储的诉求可通过关闭开关满足，无需默认关闭

### 3.2 Alternatives Considered（备选方案）

#### 备选方案 A：固定 `cache = true`，不提供开关

**做法**：直接将 4 处 `false` 改为 `true`，不新增配置项与 UI。

**优点**：
- 改动最小（仅 4 行）
- 不引入新字符串资源与 UI 元素

**否决理由**：
- 用户无法在存储空间紧张时关闭缓存，违反"用户可控"原则
- m3u8 分片缓存可能持续累积（GSY 内部虽有淘汰但用户不可见），低存储设备有风险
- 与项目现有"提供开关"风格不一致（`autoPlay`/`startFull`/`fullBottomProgressBar` 均提供开关）

#### 备选方案 B：使用 ExoPlayer SimpleCache 自建缓存层

**做法**：绕过 GSYVideoPlayer cache 参数，在 `ExoVideoManager` 内部注入 ExoPlayer `SimpleCache` + `CacheDataSource`，自建 HLS 分片缓存。

**优点**：
- 可精细控制缓存大小上限、淘汰策略（LRU）
- 可做缓存命中率统计

**否决理由**：
- 改动大，需深入 `ExoVideoManager` 内部，回归风险高
- 重复造轮子：GSYVideoPlayer 已提供 cache 能力
- 违反 AGENTS.md "能复用现有能力就不新增代码" 原则
- 当前需求仅为"开启已有能力 + 可关闭"，不需要精细控制

#### 备选方案 C：默认关闭，用户主动开启

**做法**：`cachePlay` 默认 `false`，与现状一致，仅提供开关让用户主动开启。

**否决理由**：
- 大多数用户不会主动翻设置，边下边播能力等于不可用
- 弱网拖动进度体验无法改善
- 与主流视频 App 默认行为相反

### 3.3 Drawbacks（ drawbacks ）

采用主方案需接受以下代价：

| 编号 | Drawback | 影响 | 缓解措施 |
|------|----------|------|----------|
| D1 | 开启缓存后 `externalCache/exoplayer` 目录会持续累积分片文件，占用存储 | 低存储设备可能告警 | 用户可关闭开关；系统清理缓存时一并清除；GSY 内部有淘汰机制 |
| D2 | 部分带鉴权 Header 的 m3u8 源，缓存分片可能因 Header 变化导致复用失败 | 极少数源缓存命中率低 | 不影响播放功能，仅退化为不缓存；与未开启本功能前行为一致 |
| D3 | 4 处 `setUp` 调用分散，未来新增播放分支需记得使用 `cachePlay` | 维护负担 | 在 `cachePlay` 属性注释中标注"所有 setUp 调用应使用本属性" |
| D4 | `cachePlay` 在播放过程中修改不会立即生效，需下次 `startPlay` 才应用 | 用户感知延迟 | 与 `autoPlay` 等配置行为一致，可接受 |

---

## 四、Requirements（需求清单）

### 4.1 功能需求

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| R1 | `VideoPlay.cachePlay` 属性 | 读写 `videoPrefs.getBoolean("cachePlay", true)`，默认 `true`，持久化到 `video_config` SharedPreferences |
| R2 | 4 处 `setUp` 调用使用 `cachePlay` | L150/L181/L215/L278 的第二参数由 `false` 改为 `cachePlay` |
| R3 | 设置对话框新增"边下边播"开关 | CheckBox 默认勾选，状态与 `VideoPlay.cachePlay` 双向绑定 |
| R4 | 字符串资源 | `strings.xml` 新增 `cache_play` = "边下边播"（中文）/ "Cache while playing"（英文，如有 values-en） |
| R5 | 开关即时持久化 | 用户切换开关后立即写入 SharedPreferences，无需额外保存按钮 |

### 4.2 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NF1 | 不引入新依赖 | 复用 GSYVideoPlayer 内置 cache 能力 |
| NF2 | 不改变播放链路 | 仅切换 `setUp` 第二参数，不触碰 `ExoVideoManager`/`VideoPlayer` 内部 |
| NF3 | 向后兼容 | 老版本升级后默认 `cachePlay=true`，行为变化仅为"开始有缓存"，不影响已有书源/订阅源播放 |
| NF4 | 遵循现有代码风格 | `cachePlay` 属性仿照 `autoPlay` 写法；CheckBox 仿照 `cbAutoPlay` 模式 |

### 4.3 验收测试

| 编号 | 场景 | 预期 |
|------|------|------|
| T1 | 首次安装/升级后播放 m3u8 | 边下边播开启，`externalCache/exoplayer` 出现分片文件 |
| T2 | 关闭开关后播放 m3u8 | 不写入新分片文件（已有文件不主动清除） |
| T3 | 关闭后重新开启 | 下次 `startPlay` 起生效，恢复缓存写入 |
| T4 | 播放 mp4 直链 | cache 参数同样生效（GSY 对非 HLS 也支持 cache） |
| T5 | 重复播放同一剧集 | 第二次播放命中本地缓存，流量消耗显著降低 |
| T6 | 弱网下拖动进度条 | 命中已缓存区间秒切，未缓存区间正常缓冲 |

---

## 五、Scenarios（使用场景）

### 场景 1：追剧用户重复观看

> 小明在追一部番剧，每集 24 分钟，m3u8 源。开启边下边播后，第一次播放下载并缓存分片；第二天重温同一集时，几乎不消耗流量即开始播放。

**价值**：节省流量，提升重复观看启动速度。

### 场景 2：弱网下拖动进度

> 小红在地铁弱网环境看视频，想跳过片头。开启边下边播后，已缓存区间内的拖动秒切；未缓存区间正常缓冲。未开启时每次拖动都需重新请求分片。

**价值**：弱网下进度拖动体验显著改善。

### 场景 3：低存储设备用户

> 老王的手机存储空间紧张，发现 `externalCache/exoplayer` 占用越来越大。打开视频设置，关闭"边下边播"开关，后续播放不再写入新分片。

**价值**：用户可主动控制存储占用。

### 场景 4：订阅源视频播放

> 用户通过 RSS 订阅源播放视频（`VideoPlay.startPlay` 的订阅源分支 L181/L215）。开关同样生效，与书籍章节播放行为一致。

**价值**：所有播放路径统一受控。

### 场景 5：单链接直播

> 用户从外部传入单链接播放（`singleUrl = true` 分支 L150）。开关同样生效。

**价值**：覆盖全部 4 处播放分支，无遗漏。
