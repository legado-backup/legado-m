# 视频播放失败修复 - 功能规格

> **创建时间**：2026-07-26 17:55
> **V2修订**：2026-07-26 18:40（基于源码深度分析，修正4个Bug根因+补充17个新遗漏Bug）
> **来源**：基于 `docs/temp-analysis/video-playback-failure-source-analysis-20260726.md` 源码深度分析汇总报告
> **日志证据**：`temp/logs/extracted_latest/logcat.txt`（5236KB，2026-07-26 17:23 下载）
> **状态**：设计阶段（V2）

---

## §1 项目背景

### 1.1 用户核心诉求

用户真机测试反馈："**好多视频订阅源使用的内置视频播放器，现在还是播放不了**"。

经深度分析 logcat 日志（3 个有效案例 + 8 个未进入播放阶段），确认**代码问题为主，源站问题为辅**。V1 文档原有 10 个 Bug，V2 通过源码深度分析（对照 VideoUrlExtractor.kt/ExoPlayerHelper.kt/Exo2MediaPlayer.kt/VideoPlayerActivity.kt 4个源码文件），修正 4 个 Bug 根因错误，新发现 17 个遗漏 Bug，共 **27 个 Bug** 需要修复。

### 1.2 测试场景

| 案例编号 | 时段 | 站点代号 | 路径模式 | 结果 |
|---------|------|---------|---------|------|
| 案例 1 | 17:20:25-17:20:33 | 站点G | /index.php/vod/play/id/{id}/sid/1/nid/ | ✅ 播放成功（重复初始化） |
| 案例 2 | 17:21:13-17:21:31 | 站点H | /vodplay/{id}-{r}-{e}.html | ✅ 播放成功（耗时 8.5 秒获取地址） |
| 案例 3 | 17:22:40-17:22:45 | 站点D | //mp43/{id}.mp4 | ❌ 用户 1.16 秒退出 |
| 未进入阶段 | 17:09-17:11 | 8 个实例 | — | ❌ 无 ExoPlayer Init 记录 |

---

## §2 核心问题

### 2.1 Bug 清单（27 个，按严重程度排序）

#### 🔴 P0 严重 Bug（直接影响播放成功率，9 个）

| 编号 | Bug 名称 | V2根因（源码验证） | 影响 |
|------|---------|-----------------|------|
| Bug-1 | 视频地址获取耗时过长 | **真正主因**：第一层MacCMS解析`analyzeUrl.getStrResponseAwait()`(VideoUrlExtractor.kt L468)无超时控制，AnalyzeUrl默认超时60s；R5 delayTime=3000ms是次要原因 | 用户感觉"播放不了"——实际是等待时间过长（8.5 秒+），用户等不及退出 |
| Bug-2 | 重复嗅探+重复setMediaSource | **真正根因**：prepareAsyncInternal未重置状态变量(currentSniffResult/fallbackTypes/currentFallbackIndex) + 旧协程未等待cancel + mInternalPlayer被覆盖 三者叠加 | 浪费网络请求+播放器状态被重置+降级链状态污染 |
| Bug-3 | 嗅探超时 3000ms 太短 + 协程取消不响应 | SNIFF_TIMEOUT_MS=3000L(ExoPlayerHelper.kt L515)；`okHttpClient.newCall(request).execute()`是阻塞调用不响应协程取消；L261-262的CancellationException catch是死代码 | 嗅探结果丢失，降级链走错路径 |
| Bug-7 | 降级链使用过期嗅探结果 | **根因修正**：不存在"主线程超时"逻辑；实际是"嗅探超时3秒返回UNKNOWN后降级链默认HLS优先(contentType=2)，与MP4直链(contentType=4)不匹配" | 案例 3 嗅探到 MP4 但降级链走 HLS，MP4 用 HLS MediaSource 解析必然失败 |
| Bug-11（新） | 3处硬编码调用导致T1.1/T1.2修改默认值无效 | VideoUrlExtractor.kt L489 + VideoPlay.kt L316/L427 硬编码 delayTime=3000L/timeout=10000L，只改默认值无效 | Bug-1修复方案失效 |
| Bug-12（新） | 第一层MacCMS解析无超时控制 | VideoUrlExtractor.kt L468 `analyzeUrl.getStrResponseAwait()` 无withTimeout包裹 | AnalyzeUrl默认超时60s，站点响应慢时第一层卡死60s |
| Bug-13（新） | 状态变量跨视频污染 | Exo2MediaPlayer.kt prepareAsyncInternal未重置currentSniffResult/fallbackTypes/currentFallbackIndex | 切换视频时旧嗅探结果/降级链状态残留，导致降级链走错路径 |
| Bug-14（新） | VideoPlay全局单例状态串扰 | VideoPlay.kt L62 `object VideoPlay : CoroutineScope by MainScope()` | 8个Activity实例快速切换时全局状态被最后一个Activity覆盖（Bug-6核心根因） |
| Bug-15（新） | 三层串行执行累计耗时超长 | VideoUrlExtractor.kt L450-500 extractVideoUrlForEpisode 无总超时 | 第一层(无超时60s) + 第三层(10s timeout) = 累计最长70s |

#### 🟠 P1 中等 Bug（影响问题定位和资源管理，15 个）

| 编号 | Bug 名称 | V2根因（源码验证） | 影响 |
|------|---------|-----------------|------|
| Bug-4 | ExoPlayer 错误未记录到 AppLog | onPlayerError 用 Log.d(Exo2MediaPlayer.kt L577) 而非 AppLog.put | 无法定位播放失败原因（错误码/异常类型丢失） |
| Bug-5 | ExoPlayer 生命周期与嗅探协程错位 | scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)(Exo2MediaPlayer.kt L61) 未在 Activity onDestroy 时 cancel；Exo2MediaPlayer自身没有release()方法，GSY release链路不感知协程作用域 | onDestroy 后 1.4 秒仍有 sniffVideoType success 日志（幽灵日志）+ 潜在内存泄漏 |
| Bug-6 | 17:09-17:11 时段 8 个视频未进入 ExoPlayer 阶段 | **核心根因**：VideoPlay全局object单例(L62)，8个Activity实例共享状态，快速切换时状态被最后一个Activity覆盖 | 用户感觉"好多视频播放不了" |
| Bug-8 | onPlayerError 未触发导致降级链无法启动 | isParsingError判断嵌套在isUnrecoverableError内部(Exo2MediaPlayer.kt L532)，UnrecognizedInputFormatException若errorCode不在4个之内则不触发降级 | ExoFallback 永远停留 #1/3，降级链设计形同虚设 |
| Bug-9 | BUFFERING 状态被 Release 中断 | 无onPlaybackStateChanged override，ExoPlayer还在BUFFERING就被Release | 没有 STATE_READY 日志确认是否真的进入播放 |
| Bug-16（新） | 第三层失败返回resolvedUrl可能是非视频流URL | VideoUrlExtractor.kt L494 `else { resolvedUrl }` + L498 `resolvedUrl` | 如果resolvedUrl是播放页URL，传给ExoPlayer会触发UnrecognizedInputFormatException |
| Bug-17（新） | extractVideoUrlForEpisode L496 catch未守卫CancellationException | VideoUrlExtractor.kt L496 `} catch (e: Exception) {` | 协程取消被吞，退出播放器时嗅探任务无法及时取消 |
| Bug-18（新） | 第一层L483 catch未守卫CancellationException | VideoUrlExtractor.kt L483 `} catch (e: Exception) {` | 同Bug-17 |
| Bug-19（新） | VideoPlay.kt L436兜底返回rssArticle.link | VideoPlay.kt L436 | P3-1降级嗅探失败时兜底返回文章链接（肯定非视频流URL），ExoPlayer必然加载失败 |
| Bug-20（新） | sniffVideoType与sniffMimeType重复嗅探 | ExoPlayerHelper.kt L151 sniffVideoType + L365 sniffMimeType | sniffVideoType不复用MimeSnifferCache，导致同一URL可能被嗅探两次 |
| Bug-21（新） | readLimitedBytes循环不响应协程取消 | ExoPlayerHelper.kt sniffWithRangeRequestR4 L470-480 | readLimitedBytes读取循环中无isActive检查，协程取消后仍继续读取 |
| Bug-22（新） | UnrecognizedInputFormatException不触发降级链 | Exo2MediaPlayer.kt L532 isParsingError嵌套在isUnrecoverableError内部 | UnrecognizedInputFormatException若errorCode不在4个之内则不触发降级（Bug-8补充） |
| Bug-23（新） | applyMediaSourceByType非suspend无法响应cancel | Exo2MediaPlayer.kt applyMediaSourceByType | scope.cancel无法中断非suspend函数，需配合isReleased标志位 |
| Bug-24（新） | mInternalPlayer重复创建未显式release旧实例 | Exo2MediaPlayer.kt prepareAsyncInternal | 重复Init时旧mInternalPlayer未release，资源泄漏 |
| Bug-25（新） | initSource协程未在Activity快速切换时及时取消 | VideoPlayerActivity.onActivityCreated L217-229 lifecycleScope.launch | lifecycleScope在onDestroy才取消（时机晚），快速切换时前一个initSource协程继续运行 |
| Bug-26（新） | onPause/onStop未暂停视频播放 | VideoPlayerActivity无onPause实现，onStop L1507-1512仅停止glideImageGetter | Activity切到后台时视频继续播放，消耗资源和音频焦点 |
| Bug-27（新） | T1.8改造点2位置错误 | VideoPlayerActivity不直接持有exo2MediaPlayer引用 | V1文档T1.8改造点2无法实施 |

#### 🟡 P2 低优先级 Bug（3 个）

| 编号 | Bug 名称 | V2根因（源码验证） | 影响 |
|------|---------|-----------------|------|
| Bug-10 | Glide 加载站点 favicon 失败 | 17:19:40 GlideException: Failed to load resource | 非视频问题，干扰日志分析 |
| Bug-28（新） | sniffVideoType未缓存嗅探结果+setDefaultHeaders非线程安全+死代码陷阱等8个P2/P3问题 | ExoPlayerHelper.kt 多个位置 | 间接影响，按需修复 |

### 2.2 数据统计

| 统计项 | V1数值 | V2数值 |
|--------|--------|--------|
| Bug 总数 | 10 | 27（修正4个+新增17个） |
| P0 严重 Bug | 4 | 9 |
| P1 中等 Bug | 4 | 15 |
| P2 低优先级 Bug | 2 | 3 |
| 修复方案需修正数 | — | 8（T1.1/T1.2/T1.4/T1.5/T1.8/T1.9/T2.1/T2.3） |
| 修复方案需重构数 | — | 1（T2.1） |

---

## §3 功能需求

### 3.1 核心功能需求

#### FR-1：缩短视频地址获取时间（解决 Bug-1 + Bug-11 + Bug-12 + Bug-15）

**需求**：视频地址获取时间从 8.5 秒降至 3 秒以内

**V2改造点**（修正V1方案）：
- **T1.1/T1.2修正**：抽取常量 `R5_DELAY_TIME=1000L` / `R5_TIMEOUT=6000L`，修改3处硬编码调用（VideoUrlExtractor.kt L489 + VideoPlay.kt L316/L427），只改默认值无效
- **T1.11新增**：用 `withTimeout(6000L) { analyzeUrl.getStrResponseAwait() }` 包裹第一层MacCMS解析（VideoUrlExtractor.kt L468）
- **T1.14新增**：为整个 extractVideoUrlForEpisode 添加总超时 `withTimeout(12000L)`

**验收标准**：
- ✅ MacCMS 模板源（站点G/H 类型）视频地址获取时间 < 3 秒
- ✅ DPlayer 播放器源（站点I 类型）视频地址获取时间 < 3 秒
- ✅ MP4 直链源（站点D 类型）视频地址获取时间 < 2 秒
- ✅ 第一层MacCMS解析超时6秒触发，不再卡死60秒
- ✅ 总超时12秒触发，不再累计70秒

#### FR-2：修复嗅探超时和协程取消问题（解决 Bug-3 + Bug-21）

**需求**：嗅探成功率从 60% 提升至 90%+，协程取消响应时间 < 100ms

**V2改造点**（补充V1方案）：
- **T1.3**：`SNIFF_TIMEOUT_MS` 从 3000ms 提升至 5000ms（保持）
- **T1.4补充**：在 `okHttpClient.newCall(request).execute().use {` 内部添加 isActive 检查 + 在 readLimitedBytes 循环中也检查 isActive + 补充 `kotlin.coroutines.coroutineContext` import
- **T1.6新增**：在 sniffWithRangeRequestR4 的 readLimitedBytes 循环中添加 isActive 检查

**验收标准**：
- ✅ 嗅探成功率 ≥ 90%（10 个测试案例中至少 9 个成功）
- ✅ 嗅探超时与成功时差 > 1000ms（不再临界）
- ✅ onDestroy 后 0 个 sniffVideoType 日志（无幽灵日志）
- ✅ readLimitedBytes 循环响应协程取消

#### FR-3：ExoPlayer 错误完整记录（解决 Bug-4 + Bug-9）

**需求**：播放失败可追溯率从 0% 提升至 100%

**V2改造点**（保持V1方案）：
- **T1.6**：`onPlayerError` 用 `AppLog.put` 替代 `Log.d`，包含错误码、异常类型、URL 路径
- **T1.7**：新增 `onPlaybackStateChanged` 日志（IDLE/BUFFERING/READY/ENDED）

**验收标准**：
- ✅ AppLog 文件中能看到 `ExoPlayer onPlayerError` 日志（如播放失败）
- ✅ AppLog 文件中能看到 `ExoPlayer state: BUFFERING→READY` 日志（如播放成功）

#### FR-4：嗅探协程生命周期管理（解决 Bug-5 + Bug-23 + Bug-27）

**需求**：Activity 销毁后立即取消所有嗅探协程

**V2改造点**（修正V1方案）：
- **T1.8修正**：
  - 改造点1（Exo2MediaPlayer.kt）：新增 `fun release() { currentSniffJob?.cancel(); scope.cancel(); isReleased = true; AppLog.put(...) }` + 新增 `private var isReleased = false` 标志位
  - 改造点2（VideoFragment.onDestroyView）：**修正位置**——在 VideoFragment.onDestroyView 中调用 `(currentPlayer as? Exo2MediaPlayer)?.release()`，而非在 VideoPlayerActivity.onDestroy 中调用（因为 Activity 不直接持有 exo2MediaPlayer 引用）
  - **T1.8增强**：在 applyMediaSourceByType 入口检查 `if (isReleased) return`，解决 scope.cancel 无法中断非suspend函数的问题
- **T1.9补充**：在 applyMediaSourceByType 内部也检查 isActive

**验收标准**：
- ✅ onDestroy 后 0 个 `sniffVideoType` 日志
- ✅ onDestroy 后 0 个 `ExoFallback` 日志
- ✅ applyMediaSourceByType 响应 isReleased 标志位
- ✅ 无 `JobCancellationException` 异常泄漏到 logcat

#### FR-5：重复初始化检测（解决 Bug-2 + Bug-13 + Bug-24）

**需求**：避免 prepareAsyncInternal 被重复调用导致的状态错乱

**V2改造点**（重构V1方案）：
- **T2.1重构**：将"1秒内防重"改为"同一URL+headers才跳过"，避免误伤合法场景（如用户快速切集）
- **T1.12新增**：prepareAsyncInternal 入口重置所有状态变量（currentSniffResult/fallbackTypes/currentFallbackIndex）
- **T1.13新增**：创建新 mInternalPlayer 实例前显式 release 旧实例

**验收标准**：
- ✅ 重复 Init 场景下，嗅探协程只启动 1 次
- ✅ 重复 Init 场景下，`setMediaSource` 只调用 1 次
- ✅ 切换视频时状态变量被重置
- ✅ 旧 mInternalPlayer 实例被显式 release

#### FR-6：降级链触发条件改造（解决 Bug-8 + Bug-22）

**需求**：降级链在 BUFFERING 超时或 onPlayerError 时触发，UnrecognizedInputFormatException 也触发降级

**V2改造点**（修正V1方案）：
- **T2.3修正**：BUFFERING 超时从 5 秒改为 12 秒，避免弱网误降级
- **T2.7新增**：将 isParsingError 独立判断，或在 isUnrecoverableError 中补充 UnrecognizedInputFormatException 的 errorCode

**验收标准**：
- ✅ BUFFERING 超时 12 秒后自动尝试下一个 MediaSource
- ✅ ExoFallback 能从 #1/3 推进到 #2/3、#3/3
- ✅ UnrecognizedInputFormatException 触发降级链

#### FR-7：修复降级链默认HLS优先问题（解决 Bug-7）

**需求**：降级链按嗅探结果排序，MP4直链优先 ProgressiveMediaSource

**V2改造点**（重构V1方案）：
- **T1.5重构**：废弃 MutableStateFlow 方案（过度设计），改为按嗅探结果排序降级链：
  - 嗅探结果为 MP4(contentType=4) 时：降级链为 [Progressive, HLS, DASH]
  - 嗅探结果为 HLS(contentType=2) 时：降级链为 [HLS, Progressive, DASH]
  - 嗅探结果为 UNKNOWN 时：降级链为 [HLS, DASH, Progressive]（保持原逻辑）

**验收标准**：
- ✅ 案例 3 类似场景（MP4 直链）降级链走 ProgressiveMediaSource 而非 HlsMediaSource
- ✅ 嗅探结果为 MP4 时第一个尝试的是 ProgressiveMediaSource

#### FR-8：VideoPlay 单例状态串扰修复（解决 Bug-6 + Bug-14）

**需求**：8个Activity实例快速切换时状态不被覆盖

**V2改造点**（新增）：
- **T1.13新增**：将 VideoPlay 状态改为 per-Activity 实例，或在 onActivityCreated 中保存状态快照
- **T2.8新增**：在 onPause 中主动取消 initSource 协程（保存 Job 引用）

**验收标准**：
- ✅ 8个Activity实例快速切换时，每个Activity的视频地址获取互不干扰
- ✅ initSource 协程在 onPause 时被取消

#### FR-9：第三层失败兜底修复（解决 Bug-16 + Bug-19）

**需求**：第三层失败时返回 null 或抛出异常，不返回非视频流URL

**V2改造点**（新增）：
- **T2.9新增**：VideoUrlExtractor.kt L494/L498 第三层失败时返回 null
- **T2.10新增**：VideoPlay.kt L436 兜底返回 null 或抛出异常

**验收标准**：
- ✅ 第三层失败时不返回非视频流URL
- ✅ ExoPlayer 不再加载非视频流URL触发 UnrecognizedInputFormatException

---

## §Phase 6 真机测试日志分析修复（2026-07-26 22:30 新增）

### 6.1 背景

用户 2026-07-26 22:30 真机测试后反馈："视频播放有所提升，但是出现过应用崩溃一次，并且之前好使的多线路多集播放现在好多都直接走兜底webview播放器了，但是其实webview播放器也是播放失败的"。

日志文件：`temp/logs/Downloadslogs(2).(1)..zip`，解压后含 11 个 appLog + 1 个 crash 文件 + logcat.txt。

### 6.2 新增 Bug 清单（2个）

#### Bug-29（P0）：ImageGalleryActivity Glide 销毁崩溃

**现象**：`crash-2026-07-26-21-52-34.log` 显示 `IllegalArgumentException: You cannot start a load for a destroyed activity`

**调用栈**：
```
IllegalArgumentException: You cannot start a load for a destroyed activity
  at Glide.with(Glide.java:577)
  at ImageGalleryActivity$initRecyclerView$5$1.onScrollStateChanged(ImageGalleryActivity.kt:259)
  at RecyclerView.dispatchOnScrollStateChanged(RecyclerView.java:5831)
  at RecyclerView.stopScroll(RecyclerView.java:3028)
  at RecyclerView.onDetachedFromWindow(RecyclerView.java:3531)
  at ActivityThread.handleDestroyActivity(ActivityThread.java:6916)
```

**根因**：ImageGalleryActivity.kt L256/L259 onScrollStateChanged 回调在 Activity 销毁过程中（onDetachedFromWindow→stopScroll→onScrollStateChanged）被触发，此时调用 Glide.with(activity) 抛异常。

**影响范围**：仅图片浏览器，与视频播放器无关，但属于 R4 改造同期发布的功能。

**修复方案**：onScrollStateChanged 入口增加 `if (isDestroyed || isFinishing) return` 守卫。

#### Bug-30（P0，回归 Bug）：VideoUrlExtractor 缺少 .m3u8 快速路径

**现象**：logcat 显示 11 次 .m3u8 URL 走完整 12 秒超时返回 null 触发 WebView 降级（WebView 也不支持 HLS 播放同样失败）。

**关键日志（脱敏）**：
```
extractVideoUrlForEpisode: resolvedUrlEq=true, isMacCms=false, urlEndsWithHtml=false
extractVideoUrlForEpisode timeout (12s), 返回null, path=/20260726/qClStzb4/index.m3u8
extractVideoUrlForEpisode 返回null, 触发WebView降级, path=/20260726/qClStzb4/index.m3u8
```

**回归证据**：用户反馈"之前好使的多线路多集播放现在好多都直接走兜底webview播放器了"。

**根因**：R4 T2.9 改造加入"超时返回 null"逻辑（避免非视频流URL传给 ExoPlayer），但 `extractVideoUrlForEpisode` 入口未补充"URL已是视频流"快速路径判断，导致已解析出的 .m3u8/.mpd/.mp4 等视频流 URL 走完整三层解析（MacCMS+DOM+WebView 抓包），12 秒超时返回 null 触发 WebView 降级。

**影响范围**：所有 .m3u8/.mpd/.mp4 等直接视频流 URL 的播放场景，包括多线路多集播放。

**修复方案**：`extractVideoUrlForEpisode` 入口新增 `isDirectVideoStreamUrl(url)` 判断，识别 .m3u8/.mpd/.mp4/.flv/.mkv/.webm 后缀直接返回 URL，跳过三层解析秒级交给 ExoPlayer 播放。

### 6.3 修复验证

- ✅ 编译验证通过（assembleDebug --rerun-tasks BUILD SUCCESSFUL in 4m 13s，77 tasks executed）
- ✅ 深度审查通过（并发安全+资源管理+边界场景+架构一致性4维度全部通过）
- ⏳ L2 真机测试验证待执行

### 6.4 关键设计决策

| 决策点 | 选项 | 决策结果 | 理由 |
|--------|------|---------|------|
| Bug-1 守卫条件 | isDestroyed / isFinishing / 两者都检查 | 两者都检查 | 双重保险，覆盖所有销毁场景 |
| Bug-2 快速路径位置 | 入口判断 / 第一层后判断 / MacCMS 后判断 | 入口判断 | 避免任何不必要的解析步骤，秒级返回 |
| isDirectVideoStreamUrl 后缀列表 | 仅 m3u8/mp4 / + mpd/flv/mkv/webm / + ts | + mpd/flv/mkv/webm，排除 ts | ts 是 HLS 分片不能单独播放 |
| Headers 注入流程 | extractVideoUrlForEpisode 注入 / VideoPlay 重新构造 | VideoPlay 重新构造 | 与 MacCMS 解析成功流程一致，保持架构一致性 |

#### FR-10：协程取消守卫（解决 Bug-17 + Bug-18）

**需求**：extractVideoUrlForEpisode 第一层和第三层 catch 守卫 CancellationException

**V2改造点**（新增）：
- **T2.11新增**：VideoUrlExtractor.kt L483 和 L496 添加 `catch (e: kotlinx.coroutines.CancellationException) { throw e }`

**验收标准**：
- ✅ 协程取消被正确传播，不被吞掉
- ✅ 退出播放器时嗅探任务被及时取消

#### FR-11：onPause/onStop 暂停视频播放（解决 Bug-26）

**需求**：Activity切到后台时暂停视频播放

**V2改造点**（新增）：
- **T2.12新增**：在 onStop 中调用 `currentFragment?.deactivatePlayer()` 或 `VideoPlay.onPause()`

**验收标准**：
- ✅ Activity切到后台时视频暂停
- ✅ 返回前台时视频恢复

#### FR-12：sniffVideoType 复用缓存（解决 Bug-20）

**需求**：sniffVideoType 复用 sniffMimeType 的缓存结果

**V2改造点**（新增）：
- **T2.13新增**：sniffVideoType 调用 sniffMimeType 获取缓存结果，避免重复嗅探

**验收标准**：
- ✅ 同一URL只嗅探一次

### 3.2 非功能需求

#### NFR-1：性能
- 嗅探协程取消响应时间 < 100ms
- AppLog 写入不阻塞主线程
- BUFFERING 超时检测不增加 CPU 占用

#### NFR-2：兼容性
- 不影响现有播放成功场景（如案例 1/2）
- 不影响音频播放路径
- 不影响 WebView 模式

#### NFR-3：可观测性
- 所有改造点必须有 AppLog 日志
- 日志包含 URL 路径（脱敏后）、耗时、错误码
- 日志格式统一（统一为 putInfo 级别，确保 release 包可见）

---

## §4 验收标准

### 4.1 功能验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 视频地址获取时间 | 真机测试 5 类源 | 平均 < 3 秒 |
| 嗅探成功率 | 真机测试 10 个案例 | ≥ 90% |
| 播放失败可追溯率 | AppLog 文件分析 | 100% |
| 降级链触发 | AppLog 文件分析 | ExoFallback 推进到 #2/3+ |
| 协程生命周期 | AppLog 文件分析 | 0 个幽灵日志 |
| 降级链正确率 | AppLog 文件分析 | MP4直链走Progressive |
| 状态变量重置 | AppLog 文件分析 | 切换视频时状态被重置 |
| VideoPlay单例 | 真机测试8实例快速切换 | 状态不串扰 |

### 4.2 真机测试场景

| 场景 | 站点类型 | 预期结果 |
|------|---------|---------|
| MacCMS 模板源 | 站点G/H 类型 | 视频地址获取 < 3 秒，播放成功 |
| DPlayer 播放器源 | 站点I 类型 | 视频地址获取 < 3 秒，播放成功 |
| 自定义播放页源 | 站点J 类型 | 视频地址获取 < 3 秒，播放成功 |
| MP4 直链源 | 站点D 类型 | 视频地址获取 < 2 秒，降级链走Progressive，播放成功 |
| 加密 HLS 源 | AES-128 类型 | 嗅探成功，播放成功 |
| 8实例快速切换 | 任意类型 | 状态不串扰，每个实例独立播放 |

### 4.3 验收节点

1. **编译验证**：测试包（`io.legado.miss.app.debug`）编译通过
2. **L1 验证**：应用启动无崩溃，ExoPlayer 初始化正常
3. **L2 验证**：真机测试 5 类源 + 8实例快速切换，收集 AppLog 验证所有改造点
4. **用户体感验证**：视频地址获取时间从 8.5 秒降至 3 秒以内

---

## §5 非目标

### 5.1 本次不修复的问题

| 问题 | 原因 |
|------|------|
| Bug-10 Glide 加载站点 favicon 失败 | 非视频问题，与本次播放失败无关，建议另立 spec |
| Bug-28 P2/P3 级问题（8个） | 间接影响，按需修复，不阻塞核心功能 |
| ruleContent 规则配置错误 | 源站问题，非代码问题，建议通过源优化解决 |
| 音频播放路径优化 | 用户未反馈音频问题，暂缓 |
| WebView 模式优化 | 本次聚焦 ExoPlayer 模式，WebView 模式另立 spec |

### 5.2 不引入的改造

- 不引入新的依赖库
- 不重构 ExoPlayer 整体架构
- 不修改 GSYVideoPlayer 库代码（仅修改 Exo2MediaPlayer.kt）
- 不修改订阅源规则引擎

---

## §6 假设与依赖

### 6.1 假设

1. 用户提供的 logcat 日志覆盖了主要测试场景
2. 3 个有效案例具有代表性（涵盖 MacCMS/DPlayer/MP4 直链三类源）
3. ExoPlayer media3 1.10.1 API 稳定，无破坏性变更
4. GSYVideoPlayer 库的 prepareAsyncInternal 调用逻辑可预测
5. VideoPlay 单例改造不影响其他模块（需验证）

### 6.2 依赖

1. **exoplayer-resilience spec**：本次修复基于 exoplayer-resilience 已实施的 sniffVideoType + 降级链架构
2. **player-review-and-optimization spec**：本次修复是 R4 增强计划的延续
3. **AppLog 模块**：所有日志改造依赖 AppLog.put 持久化机制
4. **CoroutineScope 模块**：协程生命周期管理依赖 kotlinx.coroutines

### 6.3 风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| VideoPlay 单例改造影响其他模块 | 中 | 高 | 需先搜索 VideoPlay 的所有调用点，评估影响范围 |
| BUFFERING 超时12秒导致用户感知延迟 | 中 | 中 | 配合 R5 delayTime 降低至 1000ms 抵消 |
| 协程取消响应不及时 | 低 | 低 | 在 sniffWithRangeRequestR4 中检查 isActive + readLimitedBytes 循环检查 |
| 重复初始化检测漏判 | 低 | 低 | 改为"同一URL+headers才跳过"，增加 callCount 日志便于排查 |
| 第一层超时6秒导致部分站点未加载完成 | 中 | 中 | 配合 WebView onLoadFinish 事件优化 |

---

## §7 关联文档

- **源码深度分析汇总报告**：[docs/temp-analysis/video-playback-failure-source-analysis-20260726.md](../../temp-analysis/video-playback-failure-source-analysis-20260726.md)
- **原分析报告**：[docs/temp-analysis/video-playback-failure-analysis-20260726.md](../../temp-analysis/video-playback-failure-analysis-20260726.md)
- **架构设计**：[design.md](./design.md)
- **任务清单**：[tasks.md](./tasks.md)
- **项目导航**：[README.md](./README.md)
- **前置 spec**：[../exoplayer-resilience/](../exoplayer-resilience/)
- **关联 spec**：[../player-review-and-optimization/](../player-review-and-optimization/)
