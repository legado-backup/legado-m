# Tasks：修复内置视频播放器切视频 7001 渲染管线崩溃（media3 VideoGraph 回归）

> 状态：✅ 已完成（2026-08-31 17:2x，S1-S4 全过，用户验收"全过，收尾闭环"）｜关联 spec/design 同目录。

## 1 分析（✅ 已通过子代理完成，2026-08-31）

- [x] 1.1 media3 1.10.1 VideoGraph 管线机制源码逐行分析（onEnabled 唯一开关 / videoEffects 终生不回置 null / 负分辨率哨兵链路 / 禁用方法全评估）→ `docs/temp-analysis/media3-videograph-analysis-20260831.md`
- [x] 1.2 7001 回归根因闭环（git 提交时间线 / 三要素角色裁决 / 临界提交 6bc9fd98f 锁定 / 本次 openfix 影响排除 / javap 字节码交叉验证）→ `docs/temp-analysis/video-7001-regression-20260831.md`
- [x] 1.3 项目侧四个目标文件现状核实（ExoVideoManager L120-134 / PlayerInstancePool acquire L121-149、recycle L167-193、clear L199-210 / Exo2MediaPlayer 7001 分支 L835-870 / VideoPlayer.onPrepared L322-338）→ 本 design.md 第一章

## 2 实施

### 2.1 方案 A：守卫零注入（R-7001-1）

- [x] 2.1.1 `ExoVideoManager.applyImageEnhanceEffects()`（L120-134）：在 `buildEffects` 之后、`setVideoEffects` 之前增加 `if (effects.isEmpty()) return` 守卫
- [x] 2.1.2 非空 effects 注入成功后追加 `PlayerInstancePool.markEffectsTainted(player)`（依赖 2.2.1 先行或同批落地）【偏差：实施名 `markTainted`，Set 实现，功能等价】
- [x] 2.1.3 更新 L113-118 KDoc：删除"档位全关时 setVideoEffects(空列表) 显式清空（K4）"表述，改为"非空才注入（空列表调用会在 media3 1.10.1 激活 GL VideoGraph 管线，禁止）"
- [x] 2.1.4 `VideoPlayer.kt` L336-337 注释补充"非空才注入"语义说明（onPrepared 的 post 在增强关闭时为 no-op）

### 2.2 方案 B：池污染隔离（R-7001-2）

- [x] 2.2.1 `PlayerInstancePool` 新增 `tainted` 表（`IdentityHashMap<ExoPlayer, Boolean>`）+ `@Synchronized fun markEffectsTainted(player)`（AppLog：`PlayerPool: instance tainted by videoEffects, will not be reused`）【偏差：实施为 `mutableSetOf<ExoPlayer>` + `markTainted`，AppLog `markTainted (effects injected, never recycle)`，功能等价】
- [x] 2.2.2 `recycle()`（L167-193）：状态重置成功后、LRU 入池前检查 `tainted.remove(player) == true` → `selectorMap.remove` + release + AppLog（`tainted instance released instead of pooling`）+ return【偏差：AppLog 实为 `tainted instance recycle -> release directly (never re-pool)`，行为一致】
- [x] 2.2.3 `clear()`（L199-210）：同步 `tainted.clear()`（防表泄漏）
- [x] 2.2.4 新增 `@Synchronized fun discard(player)`：`selectorMap.remove` + `tainted.remove` + release（供 2.3 使用；与 recycle 的 onFailure 分支同构）【偏差：未单独新增 discard，7001 分支用 markTainted+recycle（tainted 即毁）等价路径替代，evict/clear 同步清理 tainted】

### 2.3 方案 C：7001 重建兜底（R-7001-3）

- [x] 2.3.1 `Exo2MediaPlayer.onPlayerError` 7001 分支（L835-870）整段重写：保留 `retryCount++` 与 enhance 三项关闭（既有降级语义）【偏差：首轮实施为同实例重试（与设计矛盾），本轮补齐为全量重建并新增 `MAX_7001_REBUILD=2` 防循环守卫，超限 `tryNextFallback` 降级链】
- [x] 2.3.2 删除反射清 effects 逻辑（L846-857，1.10.1 下无效且维持 GL 路径）
- [x] 2.3.3 删除同实例 `seekToDefaultPosition + prepare` 重试（L865-868，必败死循环）
- [x] 2.3.4 实现重建流程：detachFromPlayer → `PlayerInstancePool.discard(p)` → `mInternalPlayer = null` → `acquire(Looper)` → `trackSelectorOf` → `EventLogger` → `attachToPlayer` → `setVideoSurface`（mSurface 非空时）→ 重置 `isScopeCancelled`/`isReleased` → 按 `currentFallbackIndex` 经 `applyMediaSourceByType` 重建 MediaSource 重试（初始化模式照抄 prepareAsyncInternal，字段名按文件内实际对齐）【偏差：discard 用 markTainted+recycle 等价；markTainted 在 detach 前执行（防 recycle 状态检查先淘汰）】
- [x] 2.3.5 AppLog 输出重建记录（`ExoPlayer 7001: instance discarded & rebuilt, retry contentType=...`，URL 走 `ExoPlayerHelper.sanitizeUrl` 脱敏）【偏差：AppLog 实为 `视频渲染管线错误(7001): tainted旧实例+清池+acquire全新实例重建(#n)`，URL sanitizeUrl ✅】

### 2.4 注释根因修正（R-7001-6）

- [x] 2.4.1 `Exo2MediaPlayer.kt` 7001 分支注释（原 L835-839）重写为真实根因：空列表 setVideoEffects 注入激活 GL VideoGraph × GSY 裸 Surface 负分辨率哨兵(-1,-1) 直通（media3 1.10.1 onEnabled 仅判 videoEffects 非 null），与 effects 内容无关；修复 = A 守卫 + B tainted + C 重建（链接本 spec 目录）
- [x] 2.4.2 代码审查对照 design.md Data Flow 不变式（不存在"非 null 且复用"第三形态）确认注释与实现一致【2026-08-31 本轮复核：注释与全量重建实现已一致】

## 3 验证

- [x] 3.1 编译门禁（R-7001-5）：`./gradlew compileAppDebugKotlin` 通过 → `build-legado.bat` 测试包构建成功 → `stop-daemons.bat` 清场（强制门禁）【083112 轮：compile 通过+083116 整包 BUILD SUCCESS；2026-08-31 17:1x 全量重建补齐轮：compileAppDebugKotlin BUILD SUCCESSFUL 2m50s（GRADLE_USER_HOME=F:\gh），整包重打中】
- [x] 3.2 updateLog（编译前强制）：基于 `git diff` 逐文件对照真实变更更新 `app/src/main/assets/updateLog.md`（追加在 `## cronet版本:` 之后、已有条目之前；面向用户语言：修复部分场景切视频时播放器崩溃）【L19 已含渲染管线修复条目】
- [x] 3.3 L2 真机核心判据（S1）：增强关闭（默认态）连滑 ≥3 个视频（含合集切集）全部正常播放，无 7001、无黑屏、无重载循环；AppLog 池化日志正常、无 setVideoEffects 注入记录【2026-08-31 16:5x MEmu 实测：3 视频连播全过，logcat 0×7001、video2/video3 均 acquire hit(reuse) 正常播、无 markTainted（守卫生效预期）；用户确认"三个都能播，修复生效"】
- [x] 3.4 增强开启回归（S2/S3）：开启锐化/降噪连滑 ≥5 次不崩（若触发 7001 验证 C 分支 `instance discarded & rebuilt` 日志且自动续播成功）；tainted 日志验证（`tainted instance released instead of pooling`，后续 acquire 均 miss 新建）；效果可见 + 亮度/对比度/饱和度/色温滤镜不受影响【2026-08-31 17:1x MEmu 083117 实测：全过无崩溃，logcat 缓冲内 0×7000 族错误、HLS key 请求正常（AuthKeyDataSource key request success）；markTainted 未出现=本次测试未触发 GL 注入条件（守卫路径），以用户实测"全过"验收】
- [x] 3.5 Grep 检查（门禁）：`android.util.Log.d|android.util.Log.e` 无残留调试日志；本次改动仅 AppLog.put 且不含域名/URL 明文（URL 一律 sanitizeUrl 脱敏）【2026-08-31 复查 help/ 0 命中】
- [x] 3.6 文档同步：issues-found.md（若真机发现新问题）/ tasks / ai_memory_main 是否最新；单视频正常播放零回归（S4）确认后本 spec README 状态更新为 ✅ 已完成【2026-08-31 17:2x 全流转：tasks/README/INDEX/ai_memory_main ✅，用户验收"全过，收尾闭环"】

## AOAdapt 日志

> 任务完成后追加执行记录（模板），沉淀关键决策与偏差。

| 日期 | 阶段 | 执行摘要 | 偏差与决策 | 证据 |
|------|------|---------|-----------|------|
| 2026-08-31 15:0x | 2.1/2.2 | A 守卫+B tainted 池隔离落地（ExoVideoManager/PlayerInstancePool） | markTainted(Set) 替代设计 markEffectsTainted(IdentityHashMap)，功能等价 | compileAppDebugKotlin SUCCESS |
| 2026-08-31 15:3x | 2.3 | C 7001 分支重写（首轮：markTainted+clear+同实例 seekTo/prepare，删反射与死循环重试） | ⚠️ 首轮与 design 2.3.3/2.3.4 矛盾（仍为同实例重试），已登记 | Exo2MediaPlayer L845+ |
| 2026-08-31 16:27 | 3.1/3.2 | 083116 整包（并行主题会话代打）+updateLog L19 | — | dex 扫描 markTainted=3 命中 |
| 2026-08-31 16:5x | 3.3 | MEmu 装 083116，用户实测 3 视频连播全过；logcat 0×7001，video2/3 均 reuse 正常 | 用户裁决"你安装，我来测"→AI 装机常态化 | logcat AppLog 池化日志 |
| 2026-08-31 17:1x | 2.1.3/2.1.4/2.3 | 用户真机日志（083112）复核实锤旧包不含修复；补齐 2.1.3/2.1.4 注释；C 分支重写为 design 2.3.4 全量重建（acquire 全新实例+重绑+同类型重试+MAX_7001_REBUILD=2 防循环） | C 分支偏差修正；compileAppDebugKotlin BUILD SUCCESSFUL 2m50s（F:\gh） | Exo2MediaPlayer L855-909 |
