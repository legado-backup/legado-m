# spec.md — realdevice-test-fix-003-20260727

> 基于 003 日志深度分析（78700 行，17.5 小时，6 次 FATAL EXCEPTION）+ 002 图片 UX 要求

## 日志基本信息

| 项 | 值 |
|----|----|
| 时间范围 | 2026-07-26 21:52 ~ 2026-07-27 15:17（17.5 小时） |
| 设备 | Redmi 23078RKD5C / Android 16 / SDK 36 |
| 包名 | `io.legado.miss.app.debug`（测试包） |
| 版本 | v3.26.072709debug（**不含 Phase A/B 修复**） |
| 日志量 | ~78700 行（8 appLog + 1 logcat + 2 crash） |
| FATAL EXCEPTION | 6 次（5 TrackSelector + 1 Glide） |

## 1. P0 致命崩溃

### 1.1 V-003-P0-1：TrackSelector.init 重复初始化崩溃（×5）

**现象**：5 次 FATAL EXCEPTION，全部相同调用栈
- 异常：`IllegalStateException @ Preconditions.checkState`
- 调用栈：`TrackSelector.init(TrackSelector.java:145) ← ExoPlayerImplInternal.<init>:354 ← ExoPlayer$Builder.build:1302 ← PlayerInstancePool.acquire(PlayerInstancePool.kt:111) ← Exo2MediaPlayer.prepareAsyncInternal(Exo2MediaPlayer.kt:476)`

**根因**：
- 003 日志版本 v072709 不含 V-P0-1 修复（共享 TrackSelector 单例）
- 当前代码 V-P0-1 已修复（每实例独立 TrackSelector + selectorMap）
- 但需确认 prepareAsyncInternal 重入不会导致新问题（见 V-003-P0-2）

**修复方案**：V-P0-1 已修复，需打包验证

**验收标准**：无 TrackSelector.init IllegalStateException 崩溃

### 1.2 V-003-P0-2：prepareAsyncInternal 重入（新发现）

**现象**：`Exo2MediaPlayer.prepareAsyncInternal` 在 9~16ms 内被重入调用
- 09:38:48.863 prepareAsyncInternal callCount=1（第一次）
- 09:38:48.872 createLoadControl (1)
- 09:38:48.879 acquire miss (create new)
- 09:38:48.880 createLoadControl (2)（第二次！）
- 09:38:48.867 FATAL EXCEPTION

**根因**：
- R5 网络抓包命中后多次回调 prepareAsyncInternal
- prepareAsyncInternal 无重入保护（prepareAsyncCallCount 计数但不阻止重入）
- 重入导致 PlayerInstancePool.acquire 被调用两次，创建多个 ExoPlayer 实例竞争

**修复方案**：
- prepareAsyncInternal 入口添加重入保护（AtomicBoolean `isPreparing`）
- 第一次调用设置 isPreparing=true，完成后重置
- 重入时跳过并记录日志

**验收标准**：prepareAsyncInternal 不被重入；无重复 acquire/createLoadControl

### 1.3 I-003-P0-1：Glide destroyed activity 崩溃

**现象**：1 次 FATAL EXCEPTION
- 异常：`IllegalArgumentException: You cannot start a load for a destroyed activity`
- 调用栈：`Glide.with(Glide.java:577) ← ImageGalleryActivity$initRecyclerView$5$1.onScrollStateChanged(ImageGalleryActivity.kt:259) ← RecyclerView.onDetachedFromWindow ← handleDestroyActivity`

**根因**：
- Activity onDestroy → RecyclerView.dispatchDetachedFromWindow → stopScroll → setScrollState → onScrollStateChanged
- onScrollStateChanged 中调用 `Glide.with(activity)` / `preloadAround` → `Glide.with(context)`
- activity 已 isDestroyed=true，Glide.with 入口检查抛异常
- 缺失 isDestroyed/isFinishing 前置守卫

**修复方案**：
- `preloadAround` 入口添加 `isDestroyed/isFinishing` 守卫（context 强转 Activity 判断）
- onScrollStateChanged 回调入口添加 `isDestroyed/isFinishing` 守卫

**验收标准**：Activity 销毁后不触发 Glide 加载；无 IllegalArgumentException 崩溃

## 2. P1 功能缺陷

### 2.1 V-003-P1-1：BUFFERING 12s 超时降级必然 3003（降级链设计缺陷）

**现象**：3 次 BUFFERING 12s 超时 → 降级到 Progressive → 3003 错误
- 完整链路：HLS(contentType=2) BUFFERING 12s 超时 → ExoFallback switch to contentType=4(Progressive) → 21 个 Extractor 全部 sniff 失败(NoDeclaredBrand) → ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED(3003)
- 21 个 Extractor：FlvExtractor, FlacExtractor, WavExtractor, FragmentedMp4Extractor, Mp4Extractor, AmrExtractor, PsExtractor, OggExtractor, TsExtractor, MatroskaExtractor, AdtsExtractor, Ac3Extractor, Ac4Extractor, Mp3Extractor, AviExtractor, JpegExtractor, PngExtractor, WebpExtractor, BmpExtractor, HeifExtractor, AvifExtractor

**根因**：
- HLS 流（m3u8）降级到 Progressive 模式，ProgressiveMediaSource 用 BundledExtractorsAdapter 尝试 21 个 Extractor
- m3u8 是文本清单格式，不是容器格式，21 个 Extractor 都无法识别
- 降级策略缺陷：HLS 失败后应尝试 DASH 或直接 WebView 回退，而非 Progressive

**修复方案**：
- 修改 `buildFallbackTypes`：HLS 降级链改为 [HLS, DASH, WebView]（移除 Progressive）
- 或：HLS BUFFERING 超时时不降级到 Progressive，直接触发 WebView 回退
- DASH 降级链改为 [DASH, HLS, WebView]（移除 Progressive）
- 只有 UNKNOWN/直链类型才保留 Progressive 降级

**验收标准**：HLS 流 BUFFERING 超时不降级到 Progressive；无 21 Extractor 全失败场景

### 2.2 I-003-P1-2：URL 拼接 %0A Bug（图片 404 根因）

**现象**：33 次 404，路径含 `%0Ahttps://`（换行符+下一 URL 残留）
- `parseImageUrls strategy 1 (newline split)` 解析出的 URL 含换行符残留
- URL 形如 `https://站点B/i/2026/07/23/{id}.jpeg%0Ahttps://23img...`
- 换行符 `%0A` 导致服务器返回 404

**根因**：
- parseImageUrls 用换行符分割多 URL，但分割后未 trim 每个URL
- 换行符残留拼接到 URL 末尾，导致请求路径错误

**修复方案**：
- 找到 parseImageUrls strategy 1 (newline split) 实现
- 分割后对每个 URL 执行 `trim()` + 过滤空白 + 过滤含 `%0A`/`\n` 的残留
- 添加日志记录过滤前后的 URL 数量变化

**验收标准**：解析出的 URL 不含 `%0A`/换行符；404 次数显著下降

### 2.3 V-003-P1-3：videoFallbackWebview 事件未实际触发

**现象**：
- VideoPlayerActivity 注册了 videoFallbackWebview 观察者
- 但日志中未发现 post 事件
- 3003 错误后仅显示"建议: 视频流格式无法识别，可尝试使用 WebView 播放"提示文案

**根因分析**：
- 003 日志版本 v072709 不含 V-P1-2 末端兜底修复
- 当前代码 V-P1-2 已修复（末端解析失败 postEvent VIDEO_FALLBACK_WEBVIEW）
- 需打包验证末端兜底是否实际触发

**修复方案**：V-P1-2 已修复，需打包验证。如验证后仍不触发，排查 EventBus 事件传递链路

**验收标准**：3003 错误后自动 post VIDEO_FALLBACK_WEBVIEW 事件；WebView 回退实际触发

### 2.4 I-003-P1-3：图片播放器 UX 对齐（002 要求）

**现象**：用户反馈图片播放器缺少以下功能（002/bug.md 第 2 点）：
1. 缺少工具栏：右上角收藏 + 三点菜单（刷新/配置/浏览器打开原始详情页/日志）
2. 缺少占位底图：加载中无灰色底+图标占位，加载完成无 crossfade 替换
3. 缺少进度指示：不知道当前第几张/共几张，哪些加载成功/失败

**修复方案**：

#### 工具栏（对齐 VideoPlayerActivity）
- 右上角收藏按钮：复用 RssFavorites 逻辑，按当前文章 link 收藏
- 三点菜单：刷新（清 Glide 缓存重载）/ 配置（预留）/ 浏览器打开（openUrl）/ 查看日志（AppLogDialog）

#### 占位底图
- placeholder（灰色底+图标）→ crossfade 替换 → error 占位 + 点击重试

#### 进度指示
- 顶部 `第 X/共 Y 张` + ViewPager2 onPageSelected 联动
- 每图加载状态点（加载中黄/成功绿/失败红）

**验收标准**：菜单四项可用；占位→crossfade 无闪烁；进度联动准确；错误点击可重试

## 3. P2 体验优化

### 3.1 V-003-P2-1：LoadControl 重复创建

**现象**：每次 PlayerPool acquire 都创建新 LoadControl（tier=MEDIUM）
**修复方案**：按 tier 缓存 LoadControl 实例，复用而非每次创建
**验收标准**：acquire 时不重复创建 LoadControl

### 3.2 T-003-P2-1：ai_test 分析脚本

**修复方案**：新增 `ai_tests/scripts/analyze_player_stats.py`
- 统计：播放成功率/首帧 READY 率/3003 计数/图片 403 率/降级触发率/嗅探耗时
- 输入：logcat 日志；输出：JSON + 控制台摘要
**验收标准**：脚本可解析 logcat 输出统计报告

## 4. 统计数据（003 日志）

| 指标 | 数值 |
|------|------|
| 嗅探成功/失败 | 47/22（成功率 68.1%） |
| 播放成功/失败 | 37/22（成功率 62.7%） |
| 3003 错误 | 9 次 |
| 2004 错误 | 3 次 |
| 网络错误重试 | 10 次 |
| Cronet 降级/恢复 | 21/20 次 |
| DoH 全失败 | 40 次 |
| 图片 200/403/404 | 1519/40/33 |
| FATAL EXCEPTION | 6 次 |

## 5. 全局约束

1. 日志一律 `AppLog.put` + `sanitizeUrl` 脱敏
2. WebView 操作必在 UI 线程；runCatching 不吞 CancellationException
3. Glide 异步回调必须 `isDestroyed/isFinishing` 守卫
4. 每 Phase 完成后：编译验证 → updateLog.md 更新
5. 真机测试用测试包 `io.legado.miss.app.debug`
