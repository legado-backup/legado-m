# Spec：修复内置视频播放器切视频 7001 渲染管线崩溃（media3 VideoGraph 回归）

## Intent

- 彻底消除内置视频播放器在合集/上滑切视频场景下的 `ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED(7001)` 崩溃。
- 保持画质增强功能对开启用户完全可用（锐化/降噪 GL effects 语义不变，亮度/对比度/饱和度/色温 View 层滤镜不受影响）。
- 修复方式不引入依赖变更、不使用反射 hack、不升级/降级 media3。

## 背景一句话

画质增强 feature（提交 6bc9fd98f，2026-08-30）在 `VideoPlayer.onPrepared` 无条件 post 调用 `ImageEnhanceController.applyEffectsToPlayer()` → `ExoVideoManager.applyImageEnhanceEffects` 调用 `player.setVideoEffects(effects)`，而增强关闭时 `ImageEnhanceEffects.buildEffects` 返回 `emptyList()` → `setVideoEffects(emptyList())` 仍是**非 null 调用**，激活 media3 GL VideoGraph 管线；GSY 裸 Surface attach 发送 `(-1,-1)` 分辨率哨兵直通 GL 管线 → 首帧 `Presentation.createForWidthAndHeight(-1,-1)` 抛异常 → 7001。

## Scope

### In（范围内）

1. **A 守卫零注入**：`ExoVideoManager.applyImageEnhanceEffects` 开头增加 `if (effects.isEmpty()) return`——增强关闭时零注入，`videoEffects` 字段保持 null，渲染永走 legacy 直渲路径。
2. **B 池污染隔离**：`PlayerInstancePool` 增加 `tainted` 标记（注入过 effects 的实例），recycle 时用完即毁不入池，池内零污染。
3. **C 7001 重建兜底**：`Exo2MediaPlayer.onPlayerError` 7001 分支重写——删除无效的反射清 effects 与同实例 seekTo+prepare 重试，改为 release 当前实例 + acquire 新实例 + 重绑，按降级链重试（照抄 `prepareAsyncInternal` 既有初始化模式）。
4. **更新根因注释**：`Exo2MediaPlayer.kt` L835-839 的 7001 注释中"根因：画质增强 effects 内容 / width=-1"表述不准确，随 C 重写一并修正为真实根因（空列表注入激活 GL 管线 + 负分辨率哨兵直通）。
5. **osFlow（关键执行流记录）**：将"切视频时 VideoGraph 生命周期"修复前 vs 修复后的数据流固化到 [design.md](./design.md) Data Flow 章节，作为回归审查锚点。

### Out（范围外）

1. **不降级 media3**：无证据支持降级根治（触发器是 setVideoEffects 调用链而非 1.10.1 独有行为），且 82ca76027 耦合 minSdk/Cronet 等，回退成本高、回归面大。
2. **不升级 media3**：1.13+ API 变更回归面广，且上游是否修复负分辨率哨兵问题需验证。
3. **不重构 GSY surface 流程**：裸 Surface attach 是 GSY 框架既有行为，改造成本高且不解决"空列表激活管线"的结构性问题。
4. **不改画质增强功能本身**：`ImageEnhanceEffects` / `ImageEnhanceController` 的效果构建逻辑与 View 层滤镜不动。
5. 不向 androidx media 官方仓库提 issue（建议另行处理，见分析报告 §8）。

## Approach

### Selected：A+B+C 三件套

**理由**：根因是"无条件注入 setVideoEffects(emptyList) 激活 VideoGraph"。A 从源头断（增强关闭时 `videoEffects` 恒 null → GL 管线代码路径完全不进入，7001 结构性不可能）；B 断传播链（池内零污染，杜绝复用放大）；C 兜底覆盖增强开启态（崩溃时换新实例必落 legacy 路径，重试必胜）。三件套纯项目代码、3 文件、无依赖变更、无反射、无降级。

### Alternatives Considered

| 方案 | 裁决 | 理由 |
|------|------|------|
| 降级 media3（回 1.8.0） | ❌ 否决 | 无证据支持根治（崩溃触发器是 setVideoEffects 调用链，非 1.10.1 独有行为）；本仓库无 1.8.0 AAR 可本地反编译验证其 onEnabled 语义；82ca76027 同时耦合 minSdk/Cronet 升级，回退成本高、回归面大；且破坏 1.10 新特性。 |
| 升级 media3（1.13+） | ❌ 否决 | API 变更回归面广（需全面真机回归）；上游负分辨率哨兵直通 GL 管线是否已修需验证（属上游交互缺陷：GSY 裸 Surface 流程 × media3 哨兵无拦截），升级不可控。 |
| 自定义 VideoSink 透传 | ❌ 否决 | 1.10.1 已移除 `ExoPlayer.Builder.setVideoFrameProcessorFactory`；需覆写 `DefaultRenderersFactory.buildVideoRenderers`（无公开注入钩子，整段覆写）+ 自实现 VideoSink 全接口（onInputStreamChanged/queueInputFrame/render 与 VideoFrameReleaseControl 耦合），成本极高。 |
| 反射回置 videoEffects = null 的 hack | ❌ 否决 | `videoEffects` 是 renderer 私有 final 生命周期由 release 管理的字段；反射改字段绕过框架生命周期管理有未知风险；且 `setVideoEffects(null)` 会 NPE（handleMessage case 13 `checkNotNull`）。 |

### Drawbacks（代价与局限）

1. 增强关闭用户（默认态）获得结构性修复；增强开启用户若 7001 仍触发，靠 C 重建实例兜底——首帧有短暂重载体验（重建实例 + 重新 prepare）。
2. 池污染隔离（B）使"增强开启会话"内高频切换时实例重建频率略升（30-100ms/次创建成本，仅发生在增强开启会话内，增强关闭会话池化收益完整保留）。
3. C 重试沿用现有降级链预算（MAX_RETRY），与既有 403/网络重试共享重试计数，极端场景下可用重试次数减少（与现状一致，非新增劣化）。

### Prior Art（既有实证）

1. **media3 1.10.1 源码逐行实证**（sources jar 与项目依赖版本完全一致，非反编译推测）：
   - `MediaCodecVideoRenderer.onEnabled()` L935-943：仅当 `videoEffects != null && videoSink == null` 创建 PlaybackVideoGraphWrapper（GL 管线）；
   - `videoEffects` 字段经 `Player.setVideoEffects()` 写入后终生不回置 null（全文件无 `videoEffects = null` 路径），`onReset()` 只复位 `hasSetVideoSink`，唯一销毁是 `player.release()`（onRelease → `videoSink.release()`）；
   - `ExoPlayerImpl.setVideoSurface(Surface)` L1479-1486：裸 Surface → `C.LENGTH_UNSET=-1` 哨兵 → `MSG_SET_VIDEO_OUTPUT_RESOLUTION` 处理（renderer L1274-1281）只挡 0 不挡 -1 → `SurfaceInfo(surface,-1,-1)` 喂入 VideoGraph → `FinalShaderProgramWrapper` L643 `Presentation.createForWidthAndHeight(-1,-1)` 抛异常 → 7001。
2. **player setVideoEffects 生命周期**：`ExoPlayerImpl.setVideoEffects` L1407-1418 反射校验 `SingleInputVideoGraph$Factory` 后发送 MSG_SET_VIDEO_EFFECTS；message 13 走 `checkNotNull`，传 null 必 NPE。
3. **PlayerInstancePool 既有 LRU**（`PlayerInstancePool.kt`，池大小 3，acquire L121-149 / recycle L167-193 / clear L199-210）：池复用产生 `onReset→onEnabled` 循环 + `videoEffects` 字段跨实例复用残留，是放大器而非独立根因。
4. **git 提交时间线**：`git log -S "setVideoEffects"` 全仓仅命中 6bc9fd98f（画质增强引入）与 9ba0aac3d（开关治理）两提交——08-30 之前无任何代码调用 setVideoEffects；"原来能播"的最近正常版本 = 3c8aa5c7b 及以前。

## Requirements

> 编号规则：R-7001-N。每条附验证方式。

| # | 需求 | 验证方式 |
|---|------|---------|
| **R-7001-1** | **A 守卫零注入**：`ExoVideoManager.applyImageEnhanceEffects()` 在 `ImageEnhanceEffects.buildEffects(...)` 返回空列表时直接 `return`，绝不调用 `player.setVideoEffects(effects)`；非空时调用语义不变 | 增强关闭态 L2 真机连滑 3 视频全播放无 7001；AppLog 无 `ImageEnhance: setVideoEffects` 相关注入日志 |
| **R-7001-2** | **B tainted 隔离**：`PlayerInstancePool` 新增 `markEffectsTainted(player)` 标记方法；`recycle()` 对 tainted 实例跳过入池直接 release（用完即毁）；`clear()` 同步清空 tainted 表 | 增强开启→关闭切换后日志出现 `tainted instance released instead of pooling`，后续 acquire 均为 miss（新建） |
| **R-7001-3** | **C 重建兜底**：`Exo2MediaPlayer.onPlayerError` 7001 分支重写——删除反射清 effects 逻辑与同实例 seekTo+prepare 重试；改为 detach → `PlayerInstancePool` 丢弃当前实例（release）→ acquire 新实例 → 重绑 selector/logger/listener/surface → 重置 scope 标志 → 按当前降级链位置重建 MediaSource 重试 | 增强开启态若触发 7001：日志出现实例重建记录且自动续播成功，无死循环重试 |
| **R-7001-4** | **增强开启回归验证**：画质增强开启（锐化/降噪档位非 0）时效果链正常注入生效，亮度/对比度/饱和度/色温 View 层滤镜不受影响 | L2 真机开启增强播放，效果可见 + 播放正常 |
| **R-7001-5** | **编译门禁**：`./gradlew compileAppDebugKotlin` 通过 → `build-legado.bat` 测试包构建成功 → `stop-daemons.bat` 清场 | 构建成功退出码 0 |
| **R-7001-6** | **AOAdapt 根因注释修正**：`Exo2MediaPlayer.kt` 7001 分支注释更新为真实根因（空列表注入激活 GL 管线 × 负分辨率哨兵直通，与 effects 内容无关），同步修正 `VideoPlayer.kt` L336-337 注释中"效果链注入"语义描述（非空才注入） | 代码审查对照 design.md Data Flow 章节无矛盾表述 |

## Scenarios

### S1（核心）：增强关闭（默认态）连滑 3 视频全播放无 7001

**Given** 画质增强总开关关闭（enhanceEnabled=false，默认态），**When** 进入竖屏视频页连续上滑切换 ≥3 个视频（含合集切集），**Then** 每个视频均正常起播与播放，全程无 `ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED(7001)`、无黑屏、无重载循环；AppLog 中池化日志正常（acquire hit/miss），无 `setVideoEffects` 注入发生。

### S2：增强开启连滑不崩（C 兜底）

**Given** 画质增强开启（锐化或降噪档位非 0），**When** 连续上滑切换视频，**Then** 不发生不可恢复崩溃；若触发 7001，则 C 分支自动重建实例并按降级链重试成功续播（AppLog 出现重建记录），增强开关被安全关闭（既有降级语义）。

### S3：无 effects 实例不入池（B 生效）

**Given** 会话内曾开启增强（实例被 `setVideoEffects` 非空注入并标记 tainted），**When** 切换视频触发实例 recycle，**Then** tainted 实例直接 release 不入池（AppLog：`tainted instance released instead of pooling`），后续 acquire 为 miss 新建实例（`videoEffects==null`，走 legacy 路径）；`clear()` 时 tainted 表同步清空无泄漏。

### S4：正常单视频零回归

**Given** 单视频正常播放（无切集/无连滑），增强关闭，**When** 完整播放一个视频，**Then** 行为与修复前完全一致（`videoEffects==null` 恒走 legacy 直渲路径）；增强开启时单视频播放效果与修复前一致（非空 effects 注入语义不变）。

## Flow（关键执行流）

### 修复前（崩溃链）

```
VideoPlayer.onPrepared (L337 post)
  → ImageEnhanceController.applyEffectsToPlayer (ui/video/ImageEnhanceController.kt L151-153)
  → ExoVideoManager.applyImageEnhanceEffects (help/gsyVideo/ExoVideoManager.kt L120-134)
  → ImageEnhanceEffects.buildEffects → emptyList()（增强关闭时）
  → player.setVideoEffects(emptyList())           ← 非 null，renderer.videoEffects 永久非 null
  → [池复用第二次 onEnabled] 创建 GL VideoGraph
  → GSY 裸 Surface attach → setVideoSurface → 哨兵 Size(-1,-1)
  → renderer 只挡 0 不挡 -1 → SurfaceInfo(surface,-1,-1) 喂入 VideoGraph
  → 首帧 FinalShaderProgramWrapper L643 Presentation.createForWidthAndHeight(-1,-1)
  → VideoFrameProcessingException → 7001
```

### 修复后（A+B+C 三道防线）

```
A：effects.isEmpty() → return（videoEffects 恒 null → legacy 直渲，VideoGraph 不创建）
B：非空注入 → markEffectsTainted → recycle 时 release 不入池（池内零污染）
C：7001 → release 当前实例 → acquire 新实例（videoEffects=null）→ 重绑 → 降级链重试（必落 legacy 路径）
```

完整生命周期对比（修复前 vs 修复后）见 [design.md](./design.md) Data Flow 章节。
