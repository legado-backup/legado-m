# design.md - 视频播放器 m3u8 边下边播缓存

> **状态**：🔄 设计中
> **创建日期**：2026-07-08

---

## 一、Technical Approach（技术方案）

### 1.1 方案概述

复用 GSYVideoPlayer 内置的 `setUp(url, cache, cachePath, title)` cache 参数能力，将 `VideoPlay.startPlay` 中 4 处硬编码的 `false` 改为读取新增的 `VideoPlay.cachePlay` 配置属性（默认 `true`），并在 `SettingsDialog` 中提供开关。零新增依赖，零播放链路改动。

### 1.2 核心改动点

#### 1.2.1 `VideoPlay.kt` 新增 `cachePlay` 属性

在 `videoPrefs` 块内，紧邻 `autoPlay` 之后新增（仿照 `autoPlay` 写法）：

```kotlin
/**  边下边播缓存（所有 setUp 调用应使用本属性）  **/
var cachePlay
    get() = videoPrefs.getBoolean("cachePlay", true)
    set(value) {
        videoPrefs.edit { putBoolean("cachePlay", value) }
    }
```

**关键点**：
- 默认值 `true`（开启），符合主流视频 App 行为
- 注释中标注"所有 setUp 调用应使用本属性"，提示未来新增播放分支时使用（缓解 D3）
- 持久化到既有 `video_config` SharedPreferences，与 `autoPlay`/`startFull`/`longPressSpeed`/`fullBottomProgressBar` 同生命周期

#### 1.2.2 4 处 `setUp` 调用替换

| 行号 | 改动前 | 改动后 |
|------|--------|--------|
| L150 | `player.setUp(url, false, File(appCtx.externalCache, "exoplayer"), videoTitle)` | `player.setUp(url, cachePlay, File(appCtx.externalCache, "exoplayer"), videoTitle)` |
| L181-184 | `player.setUp(analyzeUrl.url, false, File(appCtx.externalCache, "exoplayer"), rssArticle.title)` | `player.setUp(analyzeUrl.url, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)` |
| L215 | `player.setUp(playUrl, false, File(appCtx.externalCache, "exoplayer"), rssArticle.title)` | `player.setUp(playUrl, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)` |
| L278 | `player.setUp(playUrl, false, File(appCtx.externalCache, "exoplayer"), chapter.title)` | `player.setUp(playUrl, cachePlay, File(appCtx.externalCache, "exoplayer"), chapter.title)` |

**说明**：4 处改动机械且一致，仅替换第二参数 `false` → `cachePlay`，其余参数（url/cachePath/title）完全不变。

#### 1.2.3 `SettingsDialog.kt` 新增开关绑定

仿照 `cbAutoPlay` 模式，在 `initData` 与 `initView` 中各加一行：

```kotlin
// initData()
binding.cbCachePlay.isChecked = VideoPlay.cachePlay

// initView()
binding.cbCachePlay.setOnCheckedChangeListener { _, isChecked ->
    VideoPlay.cachePlay = isChecked
}
```

#### 1.2.4 `dialog_video_settings.xml` 新增 CheckBox 行

在 `cb_full_bottom_progress` 所在 LinearLayout 之后、`tv_press_speed` 之前，插入同结构 LinearLayout：

```xml
<LinearLayout
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="horizontal"
    android:paddingTop="12dp"
    android:paddingBottom="12dp">

    <TextView
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_weight="1"
        android:text="@string/cache_play"
        android:textColor="@color/primaryText"
        android:textSize="16sp" />

    <CheckBox
        android:id="@+id/cb_cache_play"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:checked="true" />

</LinearLayout>
```

**说明**：`android:checked="true"` 与 `cachePlay` 默认值一致；实际显示状态由 `initData` 中 `binding.cbCachePlay.isChecked = VideoPlay.cachePlay` 覆盖，确保与持久化值同步。

#### 1.2.5 `strings.xml` 新增字符串

| 文件 | 新增 |
|------|------|
| `app/src/main/res/values/strings.xml` | `<string name="cache_play">边下边播</string>` |
| `app/src/main/res/values-en/strings.xml`（如有） | `<string name="cache_play">Cache while playing</string>` |

**说明**：若项目无 `values-en` 目录，仅添加默认 `values/strings.xml` 即可（中文为默认资源）。

### 1.3 不改动的部分

- `ExoVideoManager` / `VideoPlayer` / `FloatingPlayer` 内部任何代码
- GSYVideoPlayer 库代码与版本
- 缓存目录路径（`externalCache/exoplayer`）
- `videoPrefs` 的初始化逻辑
- `SettingsDialog` 既有 3 个开关（`cbAutoPlay`/`cbStartFull`/`cbFullBottomProgress`）与 `tvPressSpeed`

---

## 二、Architecture Decisions（ADR Y-Statement）

### ADR-1：采用"可配置开关 + 默认开启"而非"固定 true"

**Y-Statement**：

> In the context of Legado 视频播放器已支持 m3u8 但 cache 参数硬编码 false，facing 用户既有重复播放省流量的需求又有低存储设备节省空间的诉求，we decided to 将 cache 参数改为读取 `VideoPlay.cachePlay` 配置项并默认 true、同时提供 UI 开关，accepting 缓存目录会持续累积需用户主动关闭（D1）以及播放中修改不立即生效（D4），to achieve 主流用户默认获得边下边播收益、低存储用户可主动关闭的双赢。

**Context（上下文）**：
- GSYVideoPlayer `setUp(url, cache, cachePath, title)` 的 `cache` 参数已是现成开关
- 缓存目录 `externalCache/exoplayer` 已配置
- 项目已有 `videoPrefs` 配置体系与 `SettingsDialog` 开关模式
- 用户群体既有追剧省流量诉求，也有低存储设备用户

**Decision（决策）**：
- 新增 `cachePlay` 属性，默认 `true`
- 提供 `SettingsDialog` 开关，双向绑定
- 不引入自建 SimpleCache 缓存层

**Consequences（后果）**：
- 正面：主流用户开箱即用边下边播；低存储用户可关闭；零新增依赖；改动仅 4 文件
- 负面：缓存累积需用户感知（D1）；播放中改不生效（D4）；鉴权 Header 源可能缓存复用失败（D2）
- 缓解：开关默认开启但可关；注释提示未来分支使用 `cachePlay`（D3）

### ADR-2：复用 GSYVideoPlayer cache 参数而非自建 ExoPlayer SimpleCache

**Y-Statement**：

> In the context of 需为 m3u8 播放提供分片缓存，facing GSYVideoPlayer 已内置 cache 参数能力与自建 SimpleCache 两种路径，we decided to 复用 GSYVideoPlayer cache 参数，accepting 无法精细控制缓存大小上限与淘汰策略，to achieve 最小改动、零新增依赖、零回归风险，符合 AGENTS.md "能复用现有能力就不新增代码" 原则。

**Context**：
- 备选方案 B（自建 SimpleCache）可精细控制 LRU 与上限
- 但需深入 `ExoVideoManager` 内部，回归风险高
- 当前需求仅为"开启已有能力 + 可关闭"，不需要精细控制

**Decision**：复用 GSYVideoPlayer cache 参数。

**Consequences**：
- 正面：4 文件改动；零依赖；零播放链路改动
- 负面：缓存大小不可配置（GSY 内部淘汰策略不可控）
- 缓解：用户可关闭开关；系统清理缓存时一并清除

### ADR-3：`cachePlay` 默认 `true` 而非 `false`

**Y-Statement**：

> In the context of 需确定 cachePlay 默认值，facing 主流用户不知有此开关与低存储用户需保护两种考量，we decided to 默认 true，accepting 低存储设备升级后开始累积分片，to achieve 主流用户开箱即获边下边播收益，与 B 站/YouTube 等主流视频 App 行为一致。

**Context**：
- 备选方案 C（默认 false）保护低存储设备但使主流用户无感知
- 主流视频 App 边下边播默认开启
- Legado 用户追剧/复习是常见场景

**Decision**：默认 `true`。

**Consequences**：
- 正面：主流用户开箱即用；弱网拖动体验改善
- 负面：低存储设备升级后开始累积分片
- 缓解：可在 `updateLog.md` 中告知用户"可在视频设置中关闭边下边播"

---

## 三、Data Flow（数据流）

### 3.1 配置写入流（用户操作开关）

```
用户在 SettingsDialog 切换"边下边播"CheckBox
    ↓
cbCachePlay.setOnCheckedChangeListener 触发
    ↓
VideoPlay.cachePlay = isChecked  (setter)
    ↓
videoPrefs.edit { putBoolean("cachePlay", value) }
    ↓
SharedPreferences("video_config") 持久化写入
```

### 3.2 配置读取流（播放时应用）

```
用户触发播放 → VideoPlay.startPlay(player)
    ↓
（4 处分支之一）执行到 player.setUp(...) 调用
    ↓
读取 VideoPlay.cachePlay  (getter)
    ↓
videoPrefs.getBoolean("cachePlay", true)  →  返回 Boolean
    ↓
player.setUp(url, cachePlay值, File(appCtx.externalCache, "exoplayer"), title)
    ↓
GSYVideoPlayer 内部根据 cache 值决定是否启用分片缓存
    ↓
若 cachePlay=true：m3u8 分片缓存到 externalCache/exoplayer
若 cachePlay=false：不写入缓存，每次重新下载
```

### 3.3 配置初始化流（SettingsDialog 打开时）

```
SettingsDialog.onFragmentCreated → initData()
    ↓
binding.cbCachePlay.isChecked = VideoPlay.cachePlay  (getter 读取持久化值)
    ↓
CheckBox UI 显示与持久化值一致
```

### 3.4 数据流图

```
┌─────────────────┐     写入      ┌──────────────────────┐
│ SettingsDialog  │ ────────────→ │ VideoPlay.cachePlay  │
│ cbCachePlay     │               │ (var property)       │
└─────────────────┘               └──────────┬───────────┘
        ↑                                    │
        │ 读取(initData)                      │ 读取(getter)
        │                                    ↓
        │                          ┌──────────────────────┐
        └──────────────────────────│  player.setUp(url,   │
                                   │  cachePlay, ...)     │
                                   └──────────┬───────────┘
                                              │
                                              ↓
                                   ┌──────────────────────┐
                                   │ GSYVideoPlayer cache │
                                   │ externalCache/exoplayer │
                                   └──────────────────────┘
```

---

## 四、File Changes（文件变更清单）

| 文件 | 类型 | 改动 | 行数变化 |
|------|------|------|----------|
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 修改 | 新增 `cachePlay` 属性（5 行）+ 4 处 `setUp` 第二参数 `false`→`cachePlay` | +5 |
| `app/src/main/java/io/legado/app/ui/video/config/SettingsDialog.kt` | 修改 | `initData` 加 1 行 + `initView` 加 3 行（含 listener） | +4 |
| `app/src/main/res/layout/dialog_video_settings.xml` | 修改 | 新增 1 个 LinearLayout（含 TextView + CheckBox） | +16 |
| `app/src/main/res/values/strings.xml` | 修改 | 新增 `<string name="cache_play">边下边播</string>` | +1 |
| `app/src/main/res/values-en/strings.xml` | 修改（如有） | 新增 `<string name="cache_play">Cache while playing</string>` | +1 |
| `app/src/main/assets/updateLog.md` | 修改 | 顶部追加日期条目，告知用户新增边下边播开关 | +3 |

**总计**：5-6 个文件，约 +29-30 行。

### 4.1 不变文件清单（明确边界）

- `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` - 不变
- `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` - 不变
- `app/src/main/java/io/legado/app/help/gsyVideo/FloatingPlayer.kt` - 不变
- `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` - 不变
- `app/src/main/java/io/legado/app/ui/video/VideoPlayerViewModel.kt` - 不变
- `app/src/main/java/io/legado/app/ui/video/ChapterAdapter.kt` - 不变
- GSYVideoPlayer 库依赖 - 不变（不升级版本）
- ExoPlayer 库依赖 - 不变

### 4.2 同步更新清单

依据 AGENTS.md "版本交付同步" 规则，代码变更完成后需同步：

| 文件 | 同步内容 |
|------|----------|
| `app/src/main/assets/updateLog.md` | 顶部追加条目："视频播放新增边下边播开关（默认开启，可在视频设置中关闭）" |
| `docs/INDEX.md` | 更新本 spec 状态标记（设计中 → 已实施） |

---

## 五、风险与回归

### 5.1 回归风险分析

| 风险点 | 风险等级 | 分析 | 缓解 |
|--------|----------|------|------|
| 开启缓存后某些 m3u8 源播放失败 | 低 | GSYVideoPlayer cache 是成熟能力，未开启时也支持，开启仅多写文件 | 真机测试覆盖主流 m3u8 源 |
| 缓存目录写入权限问题 | 低 | `externalCache` 是应用私有外部缓存目录，无需权限 | 沿用既有目录，无新增 |
| 设置对话框 UI 错位 | 低 | 新增 LinearLayout 与既有 3 个开关结构完全一致 | 布局预览验证 |
| 老版本升级后行为变化 | 低 | 仅从"不缓存"变为"缓存"，不影响播放功能 | updateLog.md 告知 |

### 5.2 验证策略

1. **编译验证**：改动后 `./gradlew assembleDebug` 编译通过
2. **真机验证**：覆盖 spec.md 4.3 节 T1-T6 六个验收场景
3. **回归验证**：既有 3 个开关（autoPlay/startFull/fullBottomProgress）功能不受影响
4. **存储验证**：开启后 `externalCache/exoplayer` 出现分片文件；关闭后不再增长
