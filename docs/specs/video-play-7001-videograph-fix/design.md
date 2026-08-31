# Design：修复内置视频播放器切视频 7001 渲染管线崩溃（media3 VideoGraph 回归）

> 设计日期：2026-08-31｜根因置信度：media3 1.10.1 源码逐行实证（sources jar 与项目依赖版本完全一致），非推测。

## 一、背景与问题

### 1.1 现象

内置视频播放器（抖音风格竖屏 + 合集场景）：第一个视频正常播放；上滑切到第二个/第三个视频时首帧渲染成功（约 2307ms）后立即崩 `ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED(7001)`。异常栈：`VideoFrameProcessingTaskExecutor` / `Presentation.createForWidthAndHeight(-1,-1)` / `VideoGraph GL`。用户真机 + 模拟器双确认。

### 1.2 根因链（四步闭环，全部源码行号实证）

#### 第 1 步：无条件空列表注入（临界提交 6bc9fd98f，2026-08-30 画质增强）

调用链（行号已逐一核实）：

```
VideoPlayer.onPrepared (help/gsyVideo/VideoPlayer.kt L322-338)
  → L337 post { ImageEnhanceController.applyEffectsToPlayer() }   ← 无条件调用
  → ImageEnhanceController.applyEffectsToPlayer (ui/video/ImageEnhanceController.kt L151-153)
  → VideoPlay.videoManager.applyImageEnhanceEffects()
  → ExoVideoManager.applyImageEnhanceEffects (help/gsyVideo/ExoVideoManager.kt L120-134)
  → L125-128 ImageEnhanceEffects.buildEffects(...)                ← enhanceEnabled=false 时返回 emptyList()
  → L129 player.setVideoEffects(effects)                          ← 空列表也是非 null 调用
```

现状代码（ExoVideoManager.kt L120-134，无任何空列表守卫）：

```kotlin
fun applyImageEnhanceEffects() {
    try {
        val exoManager = playerManager as? ExoPlayerManager ?: return
        val mediaPlayer = exoManager.getMediaPlayer() as? Exo2MediaPlayer ?: return
        val player = mediaPlayer.exoPlayerInstance ?: return
        val effects = ImageEnhanceEffects.buildEffects(
            VideoPlay.enhanceSharpenLevel,
            VideoPlay.enhanceDenoiseLevel
        )
        player.setVideoEffects(effects)     // ← L129：空列表也注入，激活 GL 管线
    } catch (t: Throwable) { ... }
}
```

> 注：L117 注释"档位全关时 setVideoEffects(空列表) 显式清空（K4 防池化实例跨会话残留）"——该设计在 media3 1.10.1 语义下适得其反：空列表 ≠ 关闭管线，**反而激活管线**（"空列表清空残留"是无效且有害的）。

#### 第 2 步：media3 1.10.1 的 GL 管线激活条件（唯一开关，终生不可逆）

`MediaCodecVideoRenderer.onEnabled()`（media3-exoplayer 1.10.1 源码 L935-943）：

```java
if (!hasSetVideoSink) {
  if (videoEffects != null && videoSink == null) {   // ← 空列表(emptyList)也非 null！
    PlaybackVideoGraphWrapper wrapper = createPlaybackVideoGraphWrapper(context, videoFrameReleaseControl);
    wrapper.setTotalVideoInputCount(1);
    videoSink = wrapper.getSink(0);                  // ← 渲染改走 VideoSink（GL 管线）
  }
  hasSetVideoSink = true;
}
```

关键语义（全文件 grep 实证）：
- `videoEffects` 仅由 `MSG_SET_VIDEO_EFFECTS`（`Player.setVideoEffects`）写入，**终生不回置 null**（无 `videoEffects = null` 路径）；
- `onReset()`（L1212-1222）只复位 `hasSetVideoSink=false`，**不销毁 videoSink/VideoGraph**——GL 管线（EGL 上下文、DefaultVideoFrameProcessor）跨 stop/prepare 存续；
- 唯一销毁路径 = `player.release()`（onRelease L1225-1230 → `videoSink.release()`）；
- 不调 `setVideoEffects` 时 renderer 走 **legacy 直渲路径**（`videoSink==null` 分支，onEnabled L954-961），VideoGraph 对象根本不创建。

#### 第 3 步：GSY 裸 Surface attach 注入负分辨率哨兵

- `Exo2MediaPlayer.prepareAsyncInternal`（L593）：`if (mSurface != null) mInternalPlayer.setVideoSurface(mSurface)`；
- `ExoPlayerManager.showDisplay`（L108-117）：每次 onPrepared 前后 attach 真 TextureView Surface。

`ExoPlayerImpl.setVideoSurface(Surface)`（L1479-1486）：裸 Surface 无尺寸信息 → `newSurfaceSize = C.LENGTH_UNSET(-1)` → `maybeNotifySurfaceSizeChanged(-1,-1)` → `MSG_SET_VIDEO_OUTPUT_RESOLUTION`。renderer 处理（L1274-1281）**只挡 0 不挡 -1**：

```java
if (outputResolution.getWidth() != 0 && outputResolution.getHeight() != 0) {  // -1 通过！
  this.outputResolution = outputResolution;
  if (videoSink != null) videoSink.setOutputSurfaceInfo(displaySurface, outputResolution);
}
```

#### 第 4 步：GL 管线内爆点

首帧到达 → `DefaultVideoFrameProcessor` 最终输出包装器 `FinalShaderProgramWrapper` → `createDefaultShaderProgram`（media3-effect L631-663）：

```java
matrixTransformationListBuilder.add(
    Presentation.createForWidthAndHeight(outputWidth, outputHeight, Presentation.LAYOUT_SCALE_TO_FIT)); // L643
```

`outputWidth/Height` 取自 `outputSurfaceInfo.width/height` = **-1/-1** → `checkArgument(width > 0)` 抛 IllegalArgumentException → 包装为 `VideoFrameProcessingException` → `PlaybackVideoGraphWrapper.onError` → renderer `createRendererException(..., ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED /* 7001 */)`。与用户异常栈逐项吻合。

#### 池复用放大器（PlayerInstancePool，ac5a0a8aa 2026-07-28）

`PlayerInstancePool.kt`（池大小 3 LRU）关键现状：
- `acquire`（L121-149）：池命中复用 / miss 新建；
- `recycle`（L167-193）：stop + clearMediaItems + clearVideoSurface + 参数重置后入池——**无任何 effects 污染检测**；
- `clear`（L199-210）：Activity onDestroy 全量释放。

时序还原：第 1 个视频 prepare 时 `videoEffects==null`（onPrepared 注入发生在 prepare 之后）→ legacy 直渲正常；onPrepared 注入 emptyList 后 `videoEffects` 被污染；切视频 recycle（stop → renderer onReset，`videoSink` 不销毁、`videoEffects` 仍非 null）→ acquire 复用同一实例 → 新视频 prepare → renderer 重新 enable → **此刻创建 GL 管线** → 首帧收 (-1,-1) 哨兵 → 崩溃。第 3 个视频同理。

**三要素缺一不崩**：只升级 media3 不崩（当时无人调用 setVideoEffects）；只加池不崩（videoEffects 恒 null）；只有"池复用 × 无条件 setVideoEffects(emptyList)"在 1.10.1 语义下相乘才崩。临界提交 = 6bc9fd98f（`git log -S "setVideoEffects"` 全仓仅命中 6bc9fd98f / 9ba0aac3d 两提交）。

#### 本次 openfix 排除声明

video-sniff-403-and-rss-classic-fix 改动（ExoPlayerHelper DoH/auth-retry、VideoPlay switchToken/buildPlayHeaders、M3u8PreCheckDataSource Rejected 语义、Exo2MediaPlayer HlsKeyDataSourceFactory）全在网络会话/数据层，不触碰 surface/effects/池/渲染管线创建路径，**明确排除**与 7001 的引入关系。其新增的 7001 缓解块（Exo2MediaPlayer.kt L835-870）有理论缺陷但不引入崩溃（见 1.3）。

### 1.3 现有 7001 重试无效的原因（Exo2MediaPlayer.kt L835-870 现状）

现状代码问题清单：

```kotlin
if (error.errorCode == 7001 && retryCount < MAX_RETRY) {
    retryCount++
    VideoPlay.enhanceEnabled = false          // 静默写 SharedPreferences，覆盖用户偏好
    ...
    runCatching {                             // L848-857：反射 setVideoEffects(emptyList)
        val m = exo.javaClass.getMethod("setVideoEffects", List::class.java)
        m.invoke(exo, emptyList<Any>())
    }
    ...
    mInternalPlayer?.let { player ->
        player.seekToDefaultPosition()        // L865-868：同实例重试
        player.prepare()
    }
    return
}
```

1. **反射清 effects 无效**：1.10.1 中 `videoEffects` 非 null 后，onEnabled 的 wrapper 创建条件只在 `hasSetVideoSink==false` 时判断；sink 建立后 message 13 只更新 effects 列表，**管线保持激活**——反射注入空列表不会拆除已建立的 GL graph，反而维持 GL 路径。
2. **同实例重试必败**：onPlayerError → `stopInternal(forceResetRenderers=true)` → renderer reset，但 `videoSink` 非 null → 重试 enable 复用同一 GL 管线；重试后的 setVideoSurface 再次注入 (-1,-1) 哨兵 → **必然复崩**，直到 retryCount 耗尽走降级。
3. **根因注释不准确**（L835-839）："根因：画质增强 effects 内容 / width=-1"表述与真实根因（空列表注入激活管线 + 哨兵直通，与 effects 内容无关）不符。

## 二、Technical Approach：A+B+C 三件套

### 2.1 方案 A：守卫零注入（结构性根除）

**文件**：`app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt`，`applyImageEnhanceEffects()`（L120-134）

在 `buildEffects` 之后、`setVideoEffects` 之前增加守卫：

```kotlin
val effects = ImageEnhanceEffects.buildEffects(
    VideoPlay.enhanceSharpenLevel,
    VideoPlay.enhanceDenoiseLevel
)
if (effects.isEmpty()) return   // ★ 新增：关闭增强/无档位时不调用 setVideoEffects（videoEffects 保持 null，永走 legacy 直渲）
player.setVideoEffects(effects)
PlayerInstancePool.markEffectsTainted(player)   // ★ 方案 B 配套：非空注入后标记污染
```

同步更新 L113-118 注释（K4"空列表清空残留"设计在 1.10.1 语义下无效且有害，改为"非空才注入"语义说明）。

- 对增强关闭用户：`setVideoEffects` 全生命周期零调用 → 全部实例永远 legacy 直渲 → **7001 结构性根除**。亮度/对比度/饱和度/色温本就走 View 层 `Paint(colorFilter)`（ImageEnhanceController.apply），不受影响。
- 对增强开启用户：非空才注入，注入语义不变（空列表注入本来也无视觉差异）。

### 2.2 方案 B：池污染隔离（tainted 标记 + 用完即毁）

**文件**：`app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt`

1. 新增状态与标记方法（与既有 `selectorMap` 同风格，`IdentityHashMap` 按引用相等）：

```kotlin
// 被 setVideoEffects(非空) 注入过的实例：media3 1.10.1 中 videoEffects 永不回 null、
// GL 管线伴随实例终生，禁止再入池复用（防池内污染放大 7001）
private val tainted = java.util.IdentityHashMap<ExoPlayer, Boolean>()

@Synchronized
fun markEffectsTainted(player: ExoPlayer) {
    tainted[player] = true
    AppLog.put("PlayerPool: instance tainted by videoEffects, will not be reused")
}
```

2. `recycle()`（L167-193）在 `runCatching` 状态重置成功后、LRU 入池前检查：

```kotlin
if (tainted.remove(player) == true) {
    selectorMap.remove(player)
    kotlin.runCatching { player.release() }
    AppLog.put("PlayerPool: tainted instance released instead of pooling")
    return
}
```

3. `clear()`（L199-210）同步 `tainted.clear()`（防表泄漏）。

收益：开过增强的实例用完即毁，池内永远只有零污染实例；下个视频 acquire 天然是新实例（`videoEffects==null`，legacy 路径）。

### 2.3 方案 C：7001 重建兜底（废弃实例 + 新实例重试）

**文件 1**：`PlayerInstancePool.kt` 新增 `discard`（recycle 的"只毁不重置"变体）：

```kotlin
@Synchronized
fun discard(player: ExoPlayer) {
    selectorMap.remove(player)
    tainted.remove(player)
    kotlin.runCatching { player.release() }
}
```

**文件 2**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`，`onPlayerError` 7001 分支（L835-870）整段重写：

```kotlin
if (error.errorCode == 7001 && retryCount < MAX_RETRY) {
    retryCount++
    VideoPlay.enhanceEnabled = false      // 保留既有降级语义（关闭增强防再次注入）
    VideoPlay.enhanceSharpenLevel = 0
    VideoPlay.enhanceDenoiseLevel = 0
    mInternalPlayer?.let { p ->
        detachFromPlayer(p)
        PlayerInstancePool.discard(p)     // ★ GL 管线随 release() 真正销毁（onRelease → videoSink.release()）
        mInternalPlayer = null
    }
    mInternalPlayer = PlayerInstancePool.acquire(Looper.myLooper()!!)
    mTrackSelector = PlayerInstancePool.trackSelectorOf(mInternalPlayer)
    mEventLogger = mTrackSelector?.let { EventLogger(it) }
    attachToPlayer(mInternalPlayer)
    if (mSurface != null) mInternalPlayer.setVideoSurface(mSurface)
    isScopeCancelled.set(false)
    isReleased = false
    // 按当前降级链位置重建 MediaSource 并重试（照抄 prepareAsyncInternal 既有初始化模式）
    applyMediaSourceByType(fallbackTypes.getOrElse(currentFallbackIndex) { C.TYPE_HLS }, currentUrl, currentHeaders)
    AppLog.put("ExoPlayer 7001: instance discarded & rebuilt, retry contentType=...")
    return
}
```

关键差异：
- **删除**反射清 effects 逻辑（L846-857，无效且有害）与同实例 seekTo+prepare 重试（L865-868，必败）；
- 新实例 `videoEffects==null` → 重试落 legacy 直渲路径，**必不再 7001**；
- 初始化模式（acquire → trackSelectorOf → EventLogger → attachToPlayer → setVideoSurface）完全照抄 `prepareAsyncInternal` 既有初始化路径，不发明新状态机；
- 重建 MediaSource 复用既有 `applyMediaSourceByType` + 降级链状态（currentFallbackIndex/fallbackTypes/currentUrl/currentHeaders，实施时按文件内实际字段名对齐）。

### 2.4 注释根因修正（随 C 一并落地）

- `Exo2MediaPlayer.kt` L835-839：重写为真实根因——"空列表 setVideoEffects 注入激活 GL VideoGraph 管线 × GSY 裸 Surface 负分辨率哨兵(-1,-1)直通 GL 管线（media3 1.10.1 onEnabled 仅判 videoEffects 非 null），与 effects 内容无关；修复 = A 守卫零注入 + B tainted 隔离 + C 重建实例"，并链接本 spec 目录。
- `VideoPlayer.kt` L336-337：注释补充"非空才注入"语义（A 守卫后 onPrepared 的 post 调用在增强关闭时为 no-op）。

## 三、Architecture Decisions（Y-Statement 六要素）

> 格式：在……背景下，面临……，我们决定……，以达到……，接受……代价，因为……。

### AD-01 守卫零注入（A）

- **In context of**：media3 1.10.1 中 `setVideoEffects` 空列表调用即永久激活 GL VideoGraph 管线，且该状态随实例终生不可逆。
- **Facing**：画质增强 feature 在 onPrepared 无条件注入 `setVideoEffects(emptyList())`（K4"清空残留"设计在 1.10.1 语义下适得其反），导致增强关闭的默认态用户也被打入 GL 管线。
- **Decided**：`applyImageEnhanceEffects` 增加 `effects.isEmpty() return` 守卫，增强关闭时绝不调用 `setVideoEffects`。
- **To achieve**：增强关闭用户 `videoEffects` 恒 null → 全部实例永走 legacy 直渲路径，GL 管线代码路径完全不进入，7001 结构性根除。
- **Accepting**：增强从开→关后，已激活实例的 GL 管线残留由 B（tainted 不入池）与 C（7001 重建）承接，本守卫不负责拆除已激活管线。
- **Because**：media3 1.10.1 唯一正确的"关闭"方式 = 从头到尾不调用 `setVideoEffects`（onEnabled L935-943 唯一开关 + 空 checkNotNull 语义，传 null NPE、clearVideoSurface 不销毁 VideoGraph 均已源码实证）。

### AD-02 池污染隔离（B）

- **In context of**：PlayerInstancePool（池大小 3 LRU）复用实例时 `videoEffects` 字段跨实例复用不重置，renderer 的 GL 状态跨 stop/prepare 存续。
- **Facing**：注入过 effects 的实例回收后再次被 acquire，第二次 onEnabled 必激活 GL 管线——池复用是 7001 必现的放大器。
- **Decided**：`PlayerInstancePool` 增加 `tainted` 标记，注入过 effects 的实例 recycle 时用完即毁不入池。
- **To achieve**：池内永远只有零污染实例，杜绝"污染实例反复复用、必现概率大增"的放大效应。
- **Accepting**：增强开启会话内切视频退化为"用完即毁"（每次 30-100ms 实例创建成本），池化收益在该会话内部分让渡；增强关闭会话池化收益完整保留。
- **Because**：media3 侧 `videoEffects` 私有 final 无任何合法回置途径（反射 hack 风险高，见 spec Alternatives），池侧隔离是唯一不侵入框架的污染控制点；与池既有"状态重置失败直接 release 不入池"的防污染先例（recycle onFailure 分支）风格一致。

### AD-03 7001 重建兜底（C）

- **In context of**：现有 7001 缓解块采用"反射清 effects + 同实例 seekTo+prepare 重试"，在 1.10.1 语义下必然复崩（sink 建立后反射更新 effects 不拆管线；重试 enable 复用同一 GL 管线且再次收 (-1,-1) 哨兵）。
- **Facing**：增强开启用户（非默认态）主动 setVideoEffects 仍走 VideoGraph，负分辨率哨兵 bug 对所有 GL 管线生效，7001 在增强开启态仍可能触发。
- **Decided**：7001 时 release 当前实例（GL 管线随 onRelease → videoSink.release() 真正销毁）+ acquire 新实例 + 重绑 + 按降级链重试，删除反射清 effects 与同实例重试。
- **To achieve**：重试必落新实例 legacy 直渲路径（videoEffects==null），把"必败重试"换成"必胜新实例"，保留崩溃后自动续播通道。
- **Accepting**：首帧短暂重载体验（重建实例 + 重新 prepare）；重试沿用 MAX_RETRY 预算与既有降级链。
- **Because**：1.10.1 中唯一真正的管线销毁动作是 `player.release()`（clearVideoSurface 只换 SurfaceInfo，VideoGraph/EGL 上下文原样存活——源码实证 L1342-1344/L433-439）；新建实例是唯一能保证 `videoEffects==null` 的途径。

### AD-04 不降级/不升级 media3

- **In context of**：media3 1.10.1 存在"裸 Surface 流程 × 负分辨率哨兵直通 GL 管线"的上游交互缺陷。
- **Facing**：修复方案选型中"回退 1.8.0"与"升级 1.13+"两个版本层选项。
- **Decided**：保持 media3 1.10.1 不动，纯项目代码 3 文件修复。
- **To achieve**：零依赖变更、零版本回归面，修复效果由 A 的结构性守卫保证而非依赖特定 media3 版本行为。
- **Accepting**：上游缺陷继续存在（建议另行向 androidx media 官方仓库提 issue，附分析报告 §2 证据），增强开启态 7001 风险由 C 兜底。
- **Because**：降级无证据支持根治（触发器是 setVideoEffects 调用链而非 1.10.1 独有行为；本仓库无 1.8.0 AAR 可验证其 onEnabled 语义；82ca76027 耦合 minSdk/Cronet 回退成本高）；升级 API 回归面广且上游是否已修需验证——两者均不可控，项目侧守卫方案可控且已实证。

## 四、Data Flow：切视频时 VideoGraph 生命周期（修复前 vs 修复后）

### 修复前（崩溃时序）

| 阶段 | 实例状态 | 结果 |
|------|---------|------|
| 第 1 个视频 prepare | 全新/干净实例：`videoEffects==null`（onPrepared 注入发生在 prepare 之后）、`videoSink==null` | **legacy 直渲**，正常播放；onPrepared 注入 emptyList 后 `videoEffects` 被污染 |
| 池 recycle（切视频） | `player.stop()`（recycle L170）→ renderer `onReset`：`hasSetVideoSink=false`，但 `videoSink`/VideoGraph **不销毁** | GL 管线存活 + `videoEffects` 仍非 null |
| 第 2 个视频 prepare（快速） | acquire 命中复用 → setVideoSurface（哨兵 -1,-1 入队）→ prepare → renderer 重新 enable → `videoEffects!=null && videoSink==null` → **此刻创建 GL 管线** | GL 路径激活 |
| GSY showDisplay attach 真 Surface | setVideoSurface → 哨兵 (-1,-1) → `videoSink.setOutputSurfaceInfo(surface, Size(-1,-1))` | 输出分辨率被污染为 -1,-1 |
| 第 2 个视频首帧 | GL 任务 → `Presentation.createForWidthAndHeight(-1,-1)` → 异常 → 7001 | **崩溃**（首帧渲染即触发，与"首帧成功后崩"观感一致） |

### 修复后（三道防线）

| 防线 | 生效位置 | 时序行为 |
|------|---------|---------|
| **A 守卫** | `applyImageEnhanceEffects` 入口 | 增强关闭：`buildEffects` 返回空 → 直接 return，`setVideoEffects` 零调用 → 实例 `videoEffects` 恒 null → 任何一次 onEnabled 均走 legacy 直渲，VideoGraph 对象**根本不创建** |
| **B tainted** | `applyImageEnhanceEffects`（非空注入后标记）→ `recycle` 入池前 | 增强开启：非空 effects 注入 → markEffectsTainted → 切视频 recycle 时 `tainted.remove==true` → release 不入池 → 下次 acquire miss 新建（`videoEffects==null`，legacy） |
| **C 重建** | `onPlayerError` 7001 分支 | 兜底：7001 发生（增强开启态残余风险）→ discard 当前实例（release 销毁 GL 管线）→ acquire 新实例 → 重绑 → 降级链重试 → 新实例 legacy 直渲成功 |

**不变式**：修复后任意时刻，池内与在用实例的 `videoEffects` 状态只有两种合法形态——①null（legacy 直渲，A 保证默认态恒如此）；②非 null 且已标记 tainted（B 保证其用完即毁、C 保证其崩溃即毁）。不存在"非 null 且复用"的第三形态 → 7001 触发条件在结构上被封锁。

## 五、File Changes

| 文件 | 改动 | 类型 | 风险 | 说明 |
|------|------|------|------|------|
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` | `applyImageEnhanceEffects`（L120-134）增加空列表守卫 + 非空注入后 markEffectsTainted + L113-118 注释更新 | Modify | **低** | 单点守卫，逻辑前置 return，不影响既有 try/catch 结构 |
| `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` | 新增 `tainted` 表 + `markEffectsTainted()` + `discard()`；`recycle()` 入池前 tainted 检查；`clear()` 同步清空 | Modify | **中** | 池逻辑变更，需保证 @Synchronized 一致性与表清理无泄漏；与既有"重置失败直接 release"先例同构 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | `onPlayerError` 7001 分支（L835-870）整段重写：删反射清 effects + 同实例重试，改重建实例 + 降级链重试；注释根因修正 | Modify | **中** | 错误恢复路径重写，初始化模式照抄 prepareAsyncInternal 既有路径，不引入新状态机；实施时按文件内实际字段名（fallbackTypes/currentFallbackIndex 等）对齐 |
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | L336-337 注释补充"非空才注入"语义 | Modify | **低**（可选） | 仅注释，随 A 落地一并修正，防止后续维护者误解注入时机 |

无新增文件、无依赖变更（build.gradle 不动）、无反射。

## 六、兼容性与回归风险

| 场景 | 行为 | 风险评估 |
|------|------|---------|
| 增强关闭（默认态，绝大多数用户） | `setVideoEffects` 零调用，全部实例 legacy 直渲 | 与"原来能播"的 3c8aa5c7b 及以前版本行为一致（当时 setVideoEffects 零调用点），**零回归** |
| 增强开启（锐化/降噪非 0） | 非空 effects 注入语义不变，效果生效；实例 tainted 用完即毁 | 功能保留；切换时实例重建成本 30-100ms/次（可接受）；若增强开启态触发 7001 由 C 重建兜底（首帧短暂重载） |
| 亮度/对比度/饱和度/色温（View 层滤镜） | 不涉及（走 `Paint(colorFilter)`，ImageEnhanceController.apply） | **不受影响** |
| 单视频正常播放（无切换） | A 守卫后与现状一致（增强关闭时注入本就发生在 prepare 后、不影响首帧前渲染路径） | **零回归** |
| 池化效率 | 增强关闭会话：完整保留（acquire hit 正常）；增强开启会话：切视频退化为新建 | 微降可接受（仅增强开启会话内），且换来池内零污染的正确性保证 |
| 音轨切换/倍速/后台回前台/WebView 降级链 | 不触碰（改动点均为 effects 注入与 7001 专属分支） | 零回归（L2 回归项确认） |
| 降级链共享 MAX_RETRY | C 沿用既有 retryCount 预算 | 与现状一致，非新增劣化 |

## 七、遗留事项（不在本任务范围）

1. 向 androidx media 官方仓库提 issue：renderer `MSG_SET_VIDEO_OUTPUT_RESOLUTION` 对负值/哨兵缺拦截（附分析报告 §2 证据）。
2. media3 升级跟踪：上游若修复负分辨率哨兵直通问题，可重新评估升级（届时 A/B/C 三件套依旧无害，A 仍是推荐实践）。
3. `ExoFallback` 降级链与 7001 分支的重试预算统筹（当前共享 MAX_RETRY，如需独立预算另行立项）。
